from __future__ import annotations

from pathlib import Path
import csv

from ..config import ROOT_DIR, get_settings
from ..db.repositories import list_trades


TRADE_LOG = ROOT_DIR / "phase1" / "trade_log.csv"


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def get_portfolio_summary() -> dict:
    settings = get_settings()
    trades = _read_csv(TRADE_LOG)
    closed = [trade for trade in trades if trade.get("exit_date")]
    total_pnl = sum(float(trade.get("pnl_dollars") or 0) for trade in closed)
    starting_equity = 100000.0
    equity = starting_equity + total_pnl
    return {
        "cash": round(equity * 0.85, 2),
        "portfolio_value": round(equity, 2),
        "buying_power": round(equity * 2, 2),
        "equity": round(equity, 2),
        "last_equity": starting_equity,
        "daily_change": 0.0,
        "daily_change_pct": 0.0,
        "status": settings.app_mode,
        "currency": "USD",
    }


def get_positions() -> list[dict]:
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

    trades = _read_csv(TRADE_LOG)
    positions: list[dict] = []
    for trade in trades:
        if trade.get("exit_date"):
            continue
        entry_price = float(trade.get("entry_price") or 0)
        shares = float(trade.get("shares") or 0)
        positions.append(
            {
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
            }
        )
    return positions
