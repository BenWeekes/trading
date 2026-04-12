"""
Weekes AI Assisted Trading Fund — Phase 1C
Trade Logger

Logs every trade to a CSV spreadsheet matching the plan's requirements:
  - Entry date, symbol, entry price, target, stop
  - Exit date, exit price, P&L
  - Exit reason (target/stop/time)
  - Earnings surprise % that triggered the trade

Also tracks open positions and checks for time stops (day 20).

Usage:
    from phase1.trade_logger import log_entry, log_exit, get_open_positions
"""

import os
import csv
from datetime import datetime, timedelta

TRADE_LOG_PATH = os.path.join(os.path.dirname(__file__), "trade_log.csv")

FIELDNAMES = [
    "trade_id",
    "symbol",
    "entry_date",
    "entry_price",
    "shares",
    "target_price",
    "stop_price",
    "surprise_pct",
    "exit_date",
    "exit_price",
    "exit_reason",
    "pnl_dollars",
    "pnl_percent",
    "order_id",
    "notes",
]


def _ensure_file():
    """Create the CSV with headers if it doesn't exist."""
    if not os.path.exists(TRADE_LOG_PATH):
        with open(TRADE_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def _next_trade_id() -> str:
    """Generate next trade ID like AATF-001, AATF-002, etc."""
    _ensure_file()
    count = 0
    with open(TRADE_LOG_PATH, "r") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            count += 1
    return f"AATF-{count + 1:03d}"


def log_entry(order: dict) -> str:
    """
    Log a new trade entry. Call this after the bracket order is submitted.

    Args:
        order: dict from paper_trader.submit_bracket_order()

    Returns:
        trade_id for tracking
    """
    _ensure_file()
    trade_id = _next_trade_id()

    row = {
        "trade_id": trade_id,
        "symbol": order["symbol"],
        "entry_date": order.get("submitted_at", datetime.utcnow().isoformat()),
        "entry_price": order["entry_price"],
        "shares": order["shares"],
        "target_price": order["target_price"],
        "stop_price": order["stop_price"],
        "surprise_pct": order.get("surprise_pct", ""),
        "exit_date": "",
        "exit_price": "",
        "exit_reason": "",
        "pnl_dollars": "",
        "pnl_percent": "",
        "order_id": order.get("order_id", ""),
        "notes": "",
    }

    with open(TRADE_LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)

    print(f"  [LOG] Trade {trade_id} logged: {order['symbol']} @ ${order['entry_price']}")
    return trade_id


def log_exit(trade_id: str, exit_price: float, exit_reason: str, notes: str = ""):
    """
    Update an existing trade with exit information.

    Args:
        trade_id: e.g. "AATF-001"
        exit_price: actual exit price
        exit_reason: "target", "stop", or "time"
        notes: optional notes
    """
    _ensure_file()
    rows = []
    updated = False

    with open(TRADE_LOG_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["trade_id"] == trade_id and not row["exit_date"]:
                entry_price = float(row["entry_price"])
                shares = float(row["shares"])
                pnl_dollars = round((exit_price - entry_price) * shares, 2)
                pnl_percent = round(((exit_price - entry_price) / entry_price) * 100, 2)

                row["exit_date"] = datetime.utcnow().isoformat()
                row["exit_price"] = exit_price
                row["exit_reason"] = exit_reason
                row["pnl_dollars"] = pnl_dollars
                row["pnl_percent"] = pnl_percent
                row["notes"] = notes
                updated = True

                print(f"  [LOG] Trade {trade_id} closed: {exit_reason} @ ${exit_price} | P&L: ${pnl_dollars} ({pnl_percent}%)")

            rows.append(row)

    if updated:
        with open(TRADE_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
    else:
        print(f"  [WARN] Trade {trade_id} not found or already closed.")


def get_open_positions() -> list[dict]:
    """Return all trades that have no exit date."""
    _ensure_file()
    open_trades = []
    with open(TRADE_LOG_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["exit_date"]:
                open_trades.append(row)
    return open_trades


def check_time_stops() -> list[dict]:
    """
    Check all open positions for the 20-day time stop.
    Returns list of trades that have exceeded the time limit.
    """
    open_trades = get_open_positions()
    expired = []

    for trade in open_trades:
        entry_date = datetime.fromisoformat(trade["entry_date"])
        days_open = (datetime.utcnow() - entry_date).days

        if days_open >= TIME_STOP_DAYS:
            print(f"  [TIME STOP] {trade['trade_id']} {trade['symbol']} open for {days_open} days (limit: {TIME_STOP_DAYS})")
            expired.append(trade)
        else:
            print(f"  [OPEN] {trade['trade_id']} {trade['symbol']} — day {days_open}/{TIME_STOP_DAYS}")

    return expired


TIME_STOP_DAYS = 20


def print_summary():
    """Print a summary of the trade log."""
    _ensure_file()
    trades = []
    with open(TRADE_LOG_PATH, "r") as f:
        reader = csv.DictReader(f)
        trades = list(reader)

    total = len(trades)
    closed = [t for t in trades if t["exit_date"]]
    open_t = [t for t in trades if not t["exit_date"]]

    print(f"\n{'='*50}")
    print(f"  TRADE LOG SUMMARY")
    print(f"{'='*50}")
    print(f"  Total trades:  {total}")
    print(f"  Open:          {len(open_t)}")
    print(f"  Closed:        {len(closed)}")

    if len(closed) >= 20:
        # Only calculate stats with enough data (plan says 20 minimum for indicative)
        wins = [t for t in closed if float(t["pnl_dollars"]) > 0]
        losses = [t for t in closed if float(t["pnl_dollars"]) <= 0]
        win_rate = len(wins) / len(closed) * 100

        total_pnl = sum(float(t["pnl_dollars"]) for t in closed)
        avg_win = sum(float(t["pnl_dollars"]) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(float(t["pnl_dollars"]) for t in losses) / len(losses) if losses else 0
        profit_factor = abs(sum(float(t["pnl_dollars"]) for t in wins)) / abs(sum(float(t["pnl_dollars"]) for t in losses)) if losses else float("inf")

        print(f"\n  Win rate:      {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"  Total P&L:     ${total_pnl:,.2f}")
        print(f"  Avg win:       ${avg_win:,.2f}")
        print(f"  Avg loss:      ${avg_loss:,.2f}")
        print(f"  Profit factor: {profit_factor:.2f}")

        if len(closed) < 50:
            print(f"\n  ⚠ Only {len(closed)} trades. Plan requires 50+ for meaningful stats.")
    elif closed:
        total_pnl = sum(float(t["pnl_dollars"]) for t in closed)
        print(f"  Running P&L:   ${total_pnl:,.2f}")
        print(f"\n  ⚠ Only {len(closed)} closed trades. Stats suppressed until 20+ (plan Section 6.1).")
    else:
        print(f"\n  No closed trades yet.")


if __name__ == "__main__":
    print_summary()
    print("\nOpen positions:")
    check_time_stops()
