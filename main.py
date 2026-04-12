#!/usr/bin/env python3
"""
Weekes AI Assisted Trading Fund — Phase 1 Daily Runner

This is the script you run every morning before 9:30 AM ET.
It ties together the full Phase 1 pipeline:

  1. Scan FMP for recent earnings surprises on the watchlist
  2. For each qualifying surprise (>= 5%):
     a. Run the 3-layer filter (SPY regime, stock momentum, gap check)
     b. Calculate position size (2% risk rule)
     c. Submit bracket order to Alpaca paper account
  3. Log everything to trade_log.csv
  4. Check open positions for time stops (day 20)
  5. Print summary

Usage:
    cd weekes-investments
    python main.py                  # normal daily run
    python main.py --check-only     # run filters without placing orders
    python main.py --summary        # just show trade log summary

Morning routine (from plan Section 11):
    Run before 9:30 AM ET → review triggers → approve or skip → monitor open positions
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase1.earnings_scanner import scan_earnings, log_earnings_event
from phase1.paper_trader import run_filters, process_trigger, get_api
from phase1.trade_logger import log_entry, check_time_stops, print_summary, get_open_positions


def daily_scan(check_only: bool = False):
    """
    Full daily pipeline.

    Args:
        check_only: if True, run filters but don't submit orders
    """
    print("=" * 60)
    print(f"  Weekes AATF — Daily Scanner")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (local)")
    print(f"  Mode: {'CHECK ONLY' if check_only else 'LIVE PAPER TRADING'}")
    print("=" * 60)

    # Step 1: Scan for earnings surprises
    # Look back 2 days to catch after-hours reports
    triggers = scan_earnings(lookback_days=2, lookahead_days=0)

    # Log all earnings events for data quality tracking
    for t in triggers:
        log_earnings_event(t)

    if not triggers:
        print("\n[RESULT] No qualifying earnings surprises. Nothing to trade today.")
    else:
        print(f"\n{'='*60}")
        print(f"  {len(triggers)} TRIGGER(S) FOUND — Running filters...")
        print(f"{'='*60}")

        orders_placed = 0

        for trigger in triggers:
            symbol = trigger["symbol"]
            surprise = trigger["surprise_pct"]

            print(f"\n--- {symbol} (surprise: {surprise:+.2f}%) ---")

            if check_only:
                # Just run filters, don't place orders
                result = run_filters(symbol)
                if result["pass"]:
                    print(f"  → Would place order for {symbol} (check-only mode)")
                continue

            # Full pipeline: filter → size → order
            order = process_trigger(trigger)
            if order:
                trade_id = log_entry(order)
                orders_placed += 1
                print(f"  → Trade {trade_id} opened")
            else:
                print(f"  → {symbol} filtered out, no order placed")

        if not check_only:
            print(f"\n[RESULT] {orders_placed} order(s) placed out of {len(triggers)} trigger(s)")

    # Step 2: Check open positions
    print(f"\n{'='*60}")
    print(f"  OPEN POSITIONS")
    print(f"{'='*60}")

    open_pos = get_open_positions()
    if not open_pos:
        print("  No open positions.")
    else:
        print(f"  {len(open_pos)} open position(s):")
        for pos in open_pos:
            print(f"    {pos['trade_id']} | {pos['symbol']} | Entry: ${pos['entry_price']} | "
                  f"Target: ${pos['target_price']} | Stop: ${pos['stop_price']}")

    # Step 3: Check time stops
    expired = check_time_stops()
    if expired:
        print(f"\n  ⚠ {len(expired)} position(s) past 20-day time stop — manual close required:")
        for t in expired:
            print(f"    → {t['trade_id']} {t['symbol']}")

    # Step 4: Summary
    print_summary()


def check_alpaca_connection():
    """Verify Alpaca paper account is connected."""
    try:
        api = get_api()
        account = api.get_account()
        print(f"\n[ALPACA] Connected to paper account")
        print(f"  Cash:           ${float(account.cash):,.2f}")
        print(f"  Portfolio value: ${float(account.portfolio_value):,.2f}")
        print(f"  Buying power:   ${float(account.buying_power):,.2f}")
        print(f"  Status:         {account.status}")
        return True
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to Alpaca: {e}")
        print("  Check your ALPACA_API_KEY and ALPACA_SECRET_KEY in .env")
        print("  Sign up: https://app.alpaca.markets/signup")
        return False


def main():
    parser = argparse.ArgumentParser(description="Weekes AATF — Phase 1 Daily Runner")
    parser.add_argument("--check-only", action="store_true",
                        help="Run filters but don't place orders")
    parser.add_argument("--summary", action="store_true",
                        help="Just show trade log summary")
    parser.add_argument("--test-connection", action="store_true",
                        help="Test Alpaca API connection")

    args = parser.parse_args()

    if args.summary:
        print_summary()
        open_pos = get_open_positions()
        if open_pos:
            print(f"\nOpen positions:")
            check_time_stops()
        return

    if args.test_connection:
        check_alpaca_connection()
        return

    # Verify API keys are set before running
    from dotenv import load_dotenv
    load_dotenv()

    fmp_key = os.getenv("FMP_API_KEY", "")
    alpaca_key = os.getenv("ALPACA_API_KEY", "")

    if not fmp_key or fmp_key == "your_fmp_api_key_here":
        print("[ERROR] FMP_API_KEY not configured.")
        print("  1. Sign up free: https://site.financialmodelingprep.com/register")
        print("  2. Copy .env.example to .env")
        print("  3. Paste your FMP API key")
        return

    if not args.check_only:
        if not alpaca_key or alpaca_key == "your_alpaca_api_key_here":
            print("[ERROR] ALPACA_API_KEY not configured.")
            print("  1. Sign up: https://app.alpaca.markets/signup")
            print("  2. Go to Paper Trading > API Keys")
            print("  3. Paste your keys in .env")
            print("\n  (Use --check-only to run filters without Alpaca)")
            return

        if not check_alpaca_connection():
            return

    daily_scan(check_only=args.check_only)


if __name__ == "__main__":
    main()
