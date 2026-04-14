from __future__ import annotations

from ..config import get_settings
from ..db.repositories import list_trades

STARTING_EQUITY = 100000.0


def get_portfolio_summary() -> dict:
    settings = get_settings()

    all_trades = list_trades()
    closed_trades = [t for t in all_trades if t.get("closed_at")]
    open_trades = [t for t in all_trades if not t.get("closed_at")]

    realised_pnl = sum(float(t.get("pnl_dollars") or 0) for t in closed_trades)
    unrealised_pnl = sum(float(t.get("unrealized_pnl") or 0) for t in open_trades)
    cash_in_positions = sum(
        float(t.get("entry_price") or 0) * float(t.get("shares") or 0)
        for t in open_trades
    )

    cash = STARTING_EQUITY + realised_pnl - cash_in_positions
    equity = cash + cash_in_positions + unrealised_pnl

    return {
        "cash": round(cash, 2),
        "portfolio_value": round(equity, 2),
        "buying_power": round(cash * 2, 2),
        "equity": round(equity, 2),
        "last_equity": STARTING_EQUITY,
        "daily_change": round(realised_pnl + unrealised_pnl, 2),
        "daily_change_pct": round(((equity - STARTING_EQUITY) / STARTING_EQUITY) * 100, 2),
        "status": settings.app_mode,
        "currency": "USD",
        "open_positions": len(open_trades),
        "realised_pnl": round(realised_pnl, 2),
        "unrealised_pnl": round(unrealised_pnl, 2),
        "cash_in_positions": round(cash_in_positions, 2),
    }


def get_positions() -> list[dict]:
    return [
        {
            "id": t["id"],
            "recommendation_id": t.get("recommendation_id"),
            "symbol": t.get("symbol"),
            "direction": t.get("direction"),
            "entry_price": t.get("entry_price"),
            "current_price": t.get("current_price"),
            "shares": t.get("shares"),
            "unrealized_pnl": t.get("unrealized_pnl"),
            "stop_price": t.get("stop_price"),
            "target_price": t.get("target_price"),
            "risk_state": t.get("risk_state"),
            "broker_order_id": t.get("broker_order_id"),
            "opened_at": t.get("opened_at"),
            "closed_at": t.get("closed_at"),
        }
        for t in list_trades(open_only=True)
    ]
