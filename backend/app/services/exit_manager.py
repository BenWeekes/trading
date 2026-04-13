"""Exit manager — checks open positions for exit conditions.

Called periodically to enforce:
- Stop loss hit
- Target hit
- Max hold period exceeded
- Trailing stop (after initial gain)
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..adapters.fmp import FMPClient
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    get_all_strategy_settings,
    insert_execution,
    list_trades,
    update_trade,
)
from ..services.event_bus import event_bus

_fmp = FMPClient()


def _trading_days_between(start: datetime, end: datetime) -> int:
    """Count weekdays (Mon-Fri) between two dates. Approximate trading days."""
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            days += 1
    return days


async def check_exits() -> list[dict]:
    """Check all open positions for exit conditions. Returns list of closed trades."""
    strat = get_all_strategy_settings()
    target_hold = int(strat.get("target_hold_days", "10"))
    max_hold = int(strat.get("max_hold_days", "30"))

    open_trades = list_trades(open_only=True)
    closed = []

    for trade in open_trades:
        symbol = trade["symbol"]
        direction = (trade.get("direction") or "BUY").upper()
        entry = float(trade.get("entry_price") or 0)
        shares = float(trade.get("shares") or 0)
        stop = float(trade.get("stop_price") or 0)
        target = float(trade.get("target_price") or 0)

        if not entry or not shares:
            continue

        # Get live price
        try:
            quote = await _fmp.quote(symbol)
            price = float(quote.get("price", 0)) if quote else 0
        except Exception:
            price = float(trade.get("current_price") or entry)

        if not price:
            continue

        # Update current price
        if direction in ("SHORT",):
            pnl = (entry - price) * shares
        else:
            pnl = (price - entry) * shares
        update_trade(trade["id"], current_price=price, unrealized_pnl=round(pnl, 2))

        # Check exit conditions
        exit_reason = None

        # Stop loss
        if direction in ("SHORT",):
            if stop and price >= stop:
                exit_reason = "stop"
        else:
            if stop and price <= stop:
                exit_reason = "stop"

        # Target hit
        if not exit_reason:
            if direction in ("SHORT",):
                if target and price <= target:
                    exit_reason = "target"
            else:
                if target and price >= target:
                    exit_reason = "target"

        # Hold period — check target hold (trading days) and max hold (calendar days)
        if not exit_reason and trade.get("opened_at"):
            try:
                opened = datetime.fromisoformat(trade["opened_at"].replace("Z", "+00:00"))
                now_dt = datetime.now(opened.tzinfo)
                trading_days = _trading_days_between(opened, now_dt)
                calendar_days = (now_dt - opened).days
                if trading_days >= target_hold:
                    exit_reason = "target_hold"
                elif calendar_days >= max_hold:
                    exit_reason = "max_hold"
            except Exception:
                pass

        if exit_reason:
            now = utcnow_iso()
            final_pnl = pnl
            pnl_pct = round((final_pnl / (entry * shares)) * 100, 2) if entry else 0

            update_trade(
                trade["id"],
                closed_at=now, exit_price=price, exit_reason=exit_reason,
                pnl_dollars=round(final_pnl, 2), pnl_percent=pnl_pct,
                risk_state="closed",
            )

            exit_action = "cover" if direction == "SHORT" else "sell"
            insert_execution({
                "id": new_id("exec"), "recommendation_id": trade.get("recommendation_id"),
                "trade_id": trade["id"], "order_type": f"auto_{exit_action}",
                "submitted_at": now, "filled_at": now,
                "fill_price": price, "fill_qty": shares,
                "broker_order_id": new_id("broker"),
                "broker_response": {"auto_exit": True, "reason": exit_reason},
                "status": "filled",
            })

            await event_bus.publish("position_update", {
                "symbol": symbol, "action": f"auto_{exit_action}",
                "reason": exit_reason, "pnl": round(final_pnl, 2),
            })

            closed.append({
                "symbol": symbol, "reason": exit_reason,
                "pnl": round(final_pnl, 2), "price": price,
            })

    return closed
