"""
Weekes AI Assisted Trading Fund — Phase 1A
Earnings Scanner

Fetches the FMP earnings calendar daily for the 10-stock watchlist.
For each earnings event: retrieves actual EPS, consensus estimate,
calculates surprise %, and validates data quality.

Usage:
    from phase1.earnings_scanner import scan_earnings
    triggers = scan_earnings()  # returns list of qualifying surprises
"""

import os
import csv
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# 10-stock watchlist from the plan (SPY is regime-check only, not traded)
WATCHLIST = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "AMD", "PLTR", "CRM"]
REGIME_TICKER = "SPY"

# Minimum earnings surprise to qualify (Section 2.2, Layer 3)
MIN_SURPRISE_PCT = 5.0


def fetch_earnings_calendar(from_date: str, to_date: str) -> list[dict]:
    """
    Fetch earnings calendar from FMP for a date range.
    Returns raw list of earnings events.
    """
    url = f"{FMP_BASE}/earning_calendar"
    params = {"from": from_date, "to": to_date, "apikey": FMP_API_KEY}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_earnings_surprise(symbol: str) -> list[dict]:
    """
    Fetch historical earnings surprises for a specific symbol.
    Returns list sorted by date descending (most recent first).
    """
    url = f"{FMP_BASE}/earnings-surprises/{symbol}"
    params = {"apikey": FMP_API_KEY}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def calculate_surprise(actual: float, estimate: float) -> float | None:
    """
    Calculate earnings surprise percentage.
    Returns None if estimate is zero or missing (avoids division errors).
    """
    if estimate is None or estimate == 0:
        return None
    return ((actual - estimate) / abs(estimate)) * 100


def validate_event(event: dict) -> dict | None:
    """
    Validate a single earnings event for data quality.
    Returns enriched event dict or None if data is bad.

    Checks:
    - Symbol is in our watchlist
    - Both actual and estimate EPS exist
    - Timestamps are present
    """
    symbol = event.get("symbol", "")
    if symbol not in WATCHLIST:
        return None

    actual = event.get("eps")
    estimate = event.get("epsEstimated")

    if actual is None or estimate is None:
        print(f"  [SKIP] {symbol}: missing EPS data (actual={actual}, estimate={estimate})")
        return None

    surprise_pct = calculate_surprise(actual, estimate)
    if surprise_pct is None:
        print(f"  [SKIP] {symbol}: cannot calculate surprise (estimate=0)")
        return None

    return {
        "symbol": symbol,
        "date": event.get("date", ""),
        "actual_eps": actual,
        "estimated_eps": estimate,
        "surprise_pct": round(surprise_pct, 2),
        "revenue": event.get("revenue"),
        "revenue_estimated": event.get("revenueEstimated"),
        "fmp_updated": event.get("updatedFromDate", ""),
        "query_timestamp": datetime.utcnow().isoformat(),
    }


def scan_earnings(lookback_days: int = 1, lookahead_days: int = 0) -> list[dict]:
    """
    Main scanner function. Checks the FMP earnings calendar for recent
    earnings events on watchlist stocks.

    Args:
        lookback_days: how many days back to search (default 1 = yesterday + today)
        lookahead_days: how many days forward to search (default 0 = today)

    Returns:
        List of qualifying earnings events (surprise >= 5%)
    """
    today = datetime.utcnow().date()
    from_date = (today - timedelta(days=lookback_days)).isoformat()
    to_date = (today + timedelta(days=lookahead_days)).isoformat()

    print(f"[SCANNER] Fetching earnings calendar: {from_date} to {to_date}")
    raw_events = fetch_earnings_calendar(from_date, to_date)
    print(f"[SCANNER] Found {len(raw_events)} total earnings events")

    triggers = []
    for event in raw_events:
        validated = validate_event(event)
        if validated is None:
            continue

        surprise = validated["surprise_pct"]
        symbol = validated["symbol"]

        if surprise >= MIN_SURPRISE_PCT:
            print(f"  [TRIGGER] {symbol}: surprise = {surprise:+.2f}% (QUALIFIES)")
            triggers.append(validated)
        else:
            print(f"  [INFO] {symbol}: surprise = {surprise:+.2f}% (below {MIN_SURPRISE_PCT}% threshold)")

    print(f"[SCANNER] {len(triggers)} qualifying trigger(s) found")
    return triggers


def log_earnings_event(event: dict, log_path: str = "phase1/earnings_log.csv"):
    """
    Log every earnings event to CSV for data quality tracking.
    Columns: symbol, report_date, actual_eps, estimated_eps, surprise_pct, query_timestamp
    """
    file_exists = os.path.exists(log_path)
    fieldnames = [
        "symbol", "date", "actual_eps", "estimated_eps",
        "surprise_pct", "revenue", "revenue_estimated",
        "fmp_updated", "query_timestamp"
    ]

    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(event)


if __name__ == "__main__":
    print("=" * 60)
    print("Weekes AATF — Earnings Scanner (Phase 1A)")
    print("=" * 60)

    if not FMP_API_KEY or FMP_API_KEY == "your_fmp_api_key_here":
        print("\n[ERROR] FMP_API_KEY not set. Copy .env.example to .env and add your key.")
        print("  Sign up free: https://site.financialmodelingprep.com/register")
        exit(1)

    # Scan last 2 days to catch after-hours reports from yesterday
    triggers = scan_earnings(lookback_days=2, lookahead_days=0)

    # Log all events
    for t in triggers:
        log_earnings_event(t)

    if triggers:
        print(f"\n{len(triggers)} trigger(s) ready for filter check.")
    else:
        print("\nNo qualifying earnings surprises found. Nothing to do today.")
