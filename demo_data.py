#!/usr/bin/env python3
"""
Generate demo data for the dashboard so it looks populated
on first launch. Run once, then start the dashboard.

Usage:
    python3 demo_data.py          # populate with sample trades
    python3 demo_data.py --clear  # remove demo data
"""

import os
import csv
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRADE_LOG = os.path.join(BASE_DIR, "phase1", "trade_log.csv")
EARNINGS_LOG = os.path.join(BASE_DIR, "phase1", "earnings_log.csv")

TRADE_FIELDS = [
    "trade_id", "symbol", "entry_date", "entry_price", "shares",
    "target_price", "stop_price", "surprise_pct", "exit_date",
    "exit_price", "exit_reason", "pnl_dollars", "pnl_percent",
    "order_id", "notes",
]

EARNINGS_FIELDS = [
    "symbol", "date", "actual_eps", "estimated_eps",
    "surprise_pct", "revenue", "revenue_estimated",
    "fmp_updated", "query_timestamp",
]

DEMO_TRADES = [
    {
        "trade_id": "AATF-001", "symbol": "NVDA",
        "entry_date": "2026-03-10T09:30:00", "entry_price": "142.50",
        "shares": "27.78", "target_price": "156.75", "stop_price": "135.38",
        "surprise_pct": "12.4",
        "exit_date": "2026-03-18T15:45:00", "exit_price": "156.75",
        "exit_reason": "target", "pnl_dollars": "395.80", "pnl_percent": "10.00",
        "order_id": "demo-001", "notes": "DEMO — Clean hit on target",
    },
    {
        "trade_id": "AATF-002", "symbol": "AAPL",
        "entry_date": "2026-03-12T09:30:00", "entry_price": "228.00",
        "shares": "17.54", "target_price": "250.80", "stop_price": "216.60",
        "surprise_pct": "8.7",
        "exit_date": "2026-03-19T09:31:00", "exit_price": "216.60",
        "exit_reason": "stop", "pnl_dollars": "-199.95", "pnl_percent": "-5.00",
        "order_id": "demo-002", "notes": "DEMO — Stopped out on broad selloff",
    },
    {
        "trade_id": "AATF-003", "symbol": "META",
        "entry_date": "2026-03-15T09:30:00", "entry_price": "612.00",
        "shares": "6.54", "target_price": "673.20", "stop_price": "581.40",
        "surprise_pct": "15.2",
        "exit_date": "2026-03-24T15:55:00", "exit_price": "673.20",
        "exit_reason": "target", "pnl_dollars": "400.05", "pnl_percent": "10.00",
        "order_id": "demo-003", "notes": "DEMO — Strong PEAD, revenue-driven beat",
    },
    {
        "trade_id": "AATF-004", "symbol": "AMD",
        "entry_date": "2026-03-18T09:30:00", "entry_price": "118.50",
        "shares": "33.76", "target_price": "130.35", "stop_price": "112.58",
        "surprise_pct": "6.1",
        "exit_date": "2026-04-01T15:59:00", "exit_price": "119.20",
        "exit_reason": "time", "pnl_dollars": "23.63", "pnl_percent": "0.59",
        "order_id": "demo-004", "notes": "DEMO — Time stop day 20, slight gain",
    },
    {
        "trade_id": "AATF-005", "symbol": "MSFT",
        "entry_date": "2026-03-20T09:30:00", "entry_price": "445.00",
        "shares": "8.99", "target_price": "489.50", "stop_price": "422.75",
        "surprise_pct": "9.3",
        "exit_date": "2026-03-28T11:20:00", "exit_price": "489.50",
        "exit_reason": "target", "pnl_dollars": "400.06", "pnl_percent": "10.00",
        "order_id": "demo-005", "notes": "DEMO — Guidance raised, strong drift",
    },
    {
        "trade_id": "AATF-006", "symbol": "PLTR",
        "entry_date": "2026-03-25T09:30:00", "entry_price": "87.00",
        "shares": "45.98", "target_price": "95.70", "stop_price": "82.65",
        "surprise_pct": "18.5",
        "exit_date": "", "exit_price": "",
        "exit_reason": "", "pnl_dollars": "", "pnl_percent": "",
        "order_id": "demo-006", "notes": "DEMO — Currently open",
    },
    {
        "trade_id": "AATF-007", "symbol": "CRM",
        "entry_date": "2026-03-27T09:30:00", "entry_price": "310.00",
        "shares": "12.90", "target_price": "341.00", "stop_price": "294.50",
        "surprise_pct": "7.8",
        "exit_date": "", "exit_price": "",
        "exit_reason": "", "pnl_dollars": "", "pnl_percent": "",
        "order_id": "demo-007", "notes": "DEMO — Currently open",
    },
]

DEMO_EARNINGS = [
    {"symbol": "NVDA", "date": "2026-03-09", "actual_eps": "0.89", "estimated_eps": "0.79",
     "surprise_pct": "12.66", "revenue": "39400000000", "revenue_estimated": "38100000000",
     "fmp_updated": "2026-03-09", "query_timestamp": "2026-03-10T06:00:00"},
    {"symbol": "AAPL", "date": "2026-03-11", "actual_eps": "2.45", "estimated_eps": "2.25",
     "surprise_pct": "8.89", "revenue": "124000000000", "revenue_estimated": "121000000000",
     "fmp_updated": "2026-03-11", "query_timestamp": "2026-03-12T06:00:00"},
    {"symbol": "META", "date": "2026-03-14", "actual_eps": "6.80", "estimated_eps": "5.90",
     "surprise_pct": "15.25", "revenue": "45200000000", "revenue_estimated": "43100000000",
     "fmp_updated": "2026-03-14", "query_timestamp": "2026-03-15T06:00:00"},
    {"symbol": "AMD", "date": "2026-03-17", "actual_eps": "1.12", "estimated_eps": "1.06",
     "surprise_pct": "5.66", "revenue": "7800000000", "revenue_estimated": "7600000000",
     "fmp_updated": "2026-03-17", "query_timestamp": "2026-03-18T06:00:00"},
    {"symbol": "MSFT", "date": "2026-03-19", "actual_eps": "3.42", "estimated_eps": "3.13",
     "surprise_pct": "9.27", "revenue": "69800000000", "revenue_estimated": "67200000000",
     "fmp_updated": "2026-03-19", "query_timestamp": "2026-03-20T06:00:00"},
    {"symbol": "PLTR", "date": "2026-03-24", "actual_eps": "0.13", "estimated_eps": "0.11",
     "surprise_pct": "18.18", "revenue": "890000000", "revenue_estimated": "840000000",
     "fmp_updated": "2026-03-24", "query_timestamp": "2026-03-25T06:00:00"},
    {"symbol": "CRM", "date": "2026-03-26", "actual_eps": "2.78", "estimated_eps": "2.58",
     "surprise_pct": "7.75", "revenue": "10200000000", "revenue_estimated": "9900000000",
     "fmp_updated": "2026-03-26", "query_timestamp": "2026-03-27T06:00:00"},
    {"symbol": "GOOGL", "date": "2026-03-28", "actual_eps": "2.15", "estimated_eps": "2.08",
     "surprise_pct": "3.37", "revenue": "96500000000", "revenue_estimated": "95100000000",
     "fmp_updated": "2026-03-28", "query_timestamp": "2026-03-29T06:00:00"},
    {"symbol": "AMZN", "date": "2026-03-30", "actual_eps": "1.48", "estimated_eps": "1.39",
     "surprise_pct": "6.47", "revenue": "178000000000", "revenue_estimated": "175000000000",
     "fmp_updated": "2026-03-30", "query_timestamp": "2026-03-31T06:00:00"},
]


def write_demo():
    """Write demo data to CSV files."""
    os.makedirs(os.path.join(BASE_DIR, "phase1"), exist_ok=True)

    with open(TRADE_LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRADE_FIELDS)
        w.writeheader()
        w.writerows(DEMO_TRADES)
    print(f"  Wrote {len(DEMO_TRADES)} demo trades to trade_log.csv")

    with open(EARNINGS_LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EARNINGS_FIELDS)
        w.writeheader()
        w.writerows(DEMO_EARNINGS)
    print(f"  Wrote {len(DEMO_EARNINGS)} demo earnings events to earnings_log.csv")


def clear_demo():
    """Remove demo data files."""
    for path in [TRADE_LOG, EARNINGS_LOG]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  Removed {os.path.basename(path)}")


if __name__ == "__main__":
    if "--clear" in sys.argv:
        print("Clearing demo data...")
        clear_demo()
    else:
        print("Writing demo data for dashboard preview...")
        write_demo()
        print("\nDone! Start the dashboard:")
        print("  python3 dashboard_server.py")
        print("  Open http://localhost:5050")
        print("\nTo remove demo data later:")
        print("  python3 demo_data.py --clear")
