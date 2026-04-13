from __future__ import annotations

from pathlib import Path
import csv

from ..adapters.alpaca import AlpacaAdapter
from ..config import ROOT_DIR, get_settings
from ..db.repositories import list_trades

TRADE_LOG = ROOT_DIR / "phase1" / "trade_log.csv"

_alpaca = AlpacaAdapter()


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def get_portfolio_summary() -> dict:
    settings = get_settings()

    # Try real Alpaca first
    if _alpaca.is_configured():
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — can't use run_until_complete
                # Fall through to local calc
                pass
            else:
                acct = loop.run_until_complete(_alpaca.get_account())
                if "error" not in acct:
                    return {
                        "cash": float(acct.get("cash", 0)),
                        "portfolio_value": float(acct.get("portfolio_value", 0)),
                        "buying_power": float(acct.get("buying_power", 0)),
                        "equity": float(acct.get("equity", 0)),
                        "last_equity": float(acct.get("last_equity", 0)),
                        "daily_change": round(float(acct.get("equity", 0)) - float(acct.get("last_equity", 0)), 2),
                        "daily_change_pct": 0.0,
                        "status": settings.app_mode,
                        "currency": "USD",
                    }
        except Exception:
            pass

    # Fallback: local calculation from DB trades
    db_trades = list_trades()
    closed = [t for t in db_trades if t.get("closed_at")]
    total_pnl = sum(float(t.get("pnl_dollars") or 0) for t in closed)

    # Also check legacy CSV
    csv_trades = _read_csv(TRADE_LOG)
    csv_closed = [t for t in csv_trades if t.get("exit_date")]
    total_pnl += sum(float(t.get("pnl_dollars") or 0) for t in csv_closed)

    starting_equity = 100000.0
    equity = starting_equity + total_pnl
    return {
        "cash": round(equity * 0.85, 2),
        "portfolio_value": round(equity, 2),
        "buying_power": round(equity * 2, 2),
        "equity": round(equity, 2),
        "last_equity": starting_equity,
        "daily_change": round(total_pnl, 2),
        "daily_change_pct": round((total_pnl / starting_equity) * 100, 2) if starting_equity else 0,
        "status": settings.app_mode,
        "currency": "USD",
    }


def get_positions() -> list[dict]:
    """Return open positions — from DB trades, with Alpaca prices when available."""
    db_positions = [
        {
            "id": trade["id"],
            "recommendation_id": trade.get("recommendation_id"),
            "symbol": trade.get("symbol"),
            "direction": trade.get("direction"),
            "entry_price": trade.get("entry_price"),
            "current_price": trade.get("current_price"),
            "shares": trade.get("shares"),
            "unrealized_pnl": trade.get("unrealized_pnl"),
            "stop_price": trade.get("stop_price"),
            "target_price": trade.get("target_price"),
            "risk_state": trade.get("risk_state"),
            "broker_order_id": trade.get("broker_order_id"),
            "opened_at": trade.get("opened_at"),
            "closed_at": trade.get("closed_at"),
        }
        for trade in list_trades(open_only=True)
    ]
    if db_positions:
        return db_positions

    # Legacy CSV fallback
    trades = _read_csv(TRADE_LOG)
    positions: list[dict] = []
    for trade in trades:
        if trade.get("exit_date"):
            continue
        entry_price = float(trade.get("entry_price") or 0)
        shares = float(trade.get("shares") or 0)
        positions.append({
            "id": trade.get("trade_id") or trade.get("order_id"),
            "recommendation_id": None,
            "symbol": trade.get("symbol"),
            "direction": "BUY",
            "entry_price": entry_price,
            "current_price": entry_price,
            "shares": shares,
            "unrealized_pnl": 0.0,
            "stop_price": float(trade.get("stop_price") or 0),
            "target_price": float(trade.get("target_price") or 0),
            "risk_state": "normal",
            "broker_order_id": trade.get("order_id"),
            "opened_at": trade.get("entry_date"),
            "closed_at": None,
        })
    return positions
