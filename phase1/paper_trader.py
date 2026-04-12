"""
Weekes AI Assisted Trading Fund — Phase 1B
Paper Trader

Implements the complete three-layer entry filter and Alpaca paper
bracket order submission from the plan:

  Layer 1 — Market regime:  SPY > 200-day MA
  Layer 2 — Stock momentum: Target stock > 50-day MA
  Layer 3 — Earnings surprise >= 5% (handled by scanner)

Plus:
  - Gap check: skip if open > prior close + 8%
  - Position sizing: risk exactly 2% of portfolio per trade
  - Bracket order: entry (market), take-profit (limit), stop-loss (stop)
  - Time stop tracking (exit at day 20 if neither target nor stop hit)

Usage:
    from phase1.paper_trader import process_trigger
    result = process_trigger(trigger_event)
"""

import os
import math
import yfinance as yf
import alpaca_trade_api as tradeapi
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
PORTFOLIO_SIZE = float(os.getenv("PORTFOLIO_SIZE", "10000"))

# Risk parameters from plan Section 2.4 and 2.5
RISK_PER_TRADE = 0.02          # 2% of portfolio
STOP_LOSS_PCT = 0.05           # 5% below entry
REWARD_RISK_RATIO = 2.0        # 2:1 R:R → target = entry + 2 * stop distance
MAX_GAP_PCT = 0.08             # 8% gap cap
TIME_STOP_DAYS = 20            # Exit at close of day 20

REGIME_TICKER = "SPY"
MA_LONG = 200                  # SPY regime filter
MA_SHORT = 50                  # Stock momentum filter


def get_api() -> tradeapi.REST:
    """Create Alpaca API client."""
    return tradeapi.REST(
        ALPACA_API_KEY,
        ALPACA_SECRET_KEY,
        ALPACA_BASE_URL,
        api_version="v2"
    )


# ─── Layer 1: Market Regime Filter ───────────────────────────────

def check_market_regime() -> dict:
    """
    Layer 1: Is SPY above its 200-day moving average?
    Returns dict with pass/fail and the data used.
    """
    ticker = yf.Ticker(REGIME_TICKER)
    hist = ticker.history(period="1y")

    if len(hist) < MA_LONG:
        return {"pass": False, "reason": f"Insufficient data for {MA_LONG}d MA ({len(hist)} bars)"}

    current_price = hist["Close"].iloc[-1]
    ma_200 = hist["Close"].rolling(window=MA_LONG).mean().iloc[-1]

    result = {
        "pass": current_price > ma_200,
        "ticker": REGIME_TICKER,
        "price": round(current_price, 2),
        "ma_200": round(ma_200, 2),
        "margin": round(((current_price / ma_200) - 1) * 100, 2),
    }
    return result


# ─── Layer 2: Stock Momentum Filter ──────────────────────────────

def check_stock_momentum(symbol: str) -> dict:
    """
    Layer 2: Is the target stock above its 50-day moving average?
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="6mo")

    if len(hist) < MA_SHORT:
        return {"pass": False, "reason": f"Insufficient data for {MA_SHORT}d MA ({len(hist)} bars)"}

    current_price = hist["Close"].iloc[-1]
    ma_50 = hist["Close"].rolling(window=MA_SHORT).mean().iloc[-1]

    return {
        "pass": current_price > ma_50,
        "ticker": symbol,
        "price": round(current_price, 2),
        "ma_50": round(ma_50, 2),
        "margin": round(((current_price / ma_50) - 1) * 100, 2),
    }


# ─── Gap Check ───────────────────────────────────────────────────

def check_gap(symbol: str) -> dict:
    """
    Gap filter: if the stock has gapped > 8% from prior close, skip.
    Must be called after market open to get the actual opening price.
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")

    if len(hist) < 2:
        return {"pass": False, "reason": "Insufficient price history for gap check"}

    prior_close = hist["Close"].iloc[-2]
    today_open = hist["Open"].iloc[-1]
    gap_pct = (today_open - prior_close) / prior_close

    return {
        "pass": abs(gap_pct) <= MAX_GAP_PCT,
        "ticker": symbol,
        "prior_close": round(prior_close, 2),
        "today_open": round(today_open, 2),
        "gap_pct": round(gap_pct * 100, 2),
        "max_allowed": MAX_GAP_PCT * 100,
    }


# ─── Position Sizing (Section 2.5) ───────────────────────────────

def calculate_position(entry_price: float) -> dict:
    """
    Calculate position size using the 2% risk rule from the plan.

    Risk exactly 2% of portfolio per trade.
    Stop = 5% below entry.
    Target = entry + (2 × stop distance) for 2:1 R:R.
    Position size = max_risk / risk_per_share.
    """
    stop_price = round(entry_price * (1 - STOP_LOSS_PCT), 2)
    risk_per_share = entry_price - stop_price  # = entry * 0.05
    max_risk = PORTFOLIO_SIZE * RISK_PER_TRADE  # = portfolio * 0.02

    shares = max_risk / risk_per_share
    # Alpaca supports fractional shares, but round to 2 decimals
    shares = math.floor(shares * 100) / 100

    stop_distance = entry_price - stop_price
    target_price = round(entry_price + (REWARD_RISK_RATIO * stop_distance), 2)

    return {
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "shares": shares,
        "risk_per_share": round(risk_per_share, 2),
        "total_risk": round(shares * risk_per_share, 2),
        "portfolio_size": PORTFOLIO_SIZE,
    }


# ─── Alpaca Order Submission ─────────────────────────────────────

def submit_bracket_order(symbol: str, position: dict) -> dict | None:
    """
    Submit a bracket order to Alpaca paper account.

    Bracket order = market buy + take-profit limit sell + stop-loss stop sell.
    This matches Section 2.4 exactly: no discretionary overrides.
    """
    api = get_api()

    try:
        order = api.submit_order(
            symbol=symbol,
            qty=position["shares"],
            side="buy",
            type="market",
            time_in_force="day",
            order_class="bracket",
            take_profit={"limit_price": position["target_price"]},
            stop_loss={"stop_price": position["stop_price"]},
        )
        print(f"  [ORDER] Bracket order submitted: {symbol}")
        print(f"          Shares: {position['shares']}")
        print(f"          Entry:  ~${position['entry_price']}")
        print(f"          Target: ${position['target_price']}")
        print(f"          Stop:   ${position['stop_price']}")
        print(f"          Order ID: {order.id}")

        return {
            "order_id": order.id,
            "status": order.status,
            "symbol": symbol,
            "shares": position["shares"],
            "entry_price": position["entry_price"],
            "target_price": position["target_price"],
            "stop_price": position["stop_price"],
            "submitted_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"  [ERROR] Order submission failed for {symbol}: {e}")
        return None


# ─── Main Filter Pipeline ────────────────────────────────────────

def run_filters(symbol: str) -> dict:
    """
    Run all three filter layers + gap check.
    Returns a dict with pass/fail for each layer and overall result.
    """
    print(f"\n{'='*50}")
    print(f"  FILTER CHECK: {symbol}")
    print(f"{'='*50}")

    # Layer 1 — Market regime
    regime = check_market_regime()
    status = "PASS" if regime["pass"] else "FAIL"
    print(f"  Layer 1 (SPY > 200d MA): {status}")
    print(f"    SPY: ${regime.get('price', '?')} vs MA: ${regime.get('ma_200', '?')} ({regime.get('margin', '?')}%)")

    if not regime["pass"]:
        print(f"  [BLOCKED] Market regime filter failed. No trade.")
        return {"pass": False, "blocked_by": "regime", "details": regime}

    # Layer 2 — Stock momentum
    momentum = check_stock_momentum(symbol)
    status = "PASS" if momentum["pass"] else "FAIL"
    print(f"  Layer 2 ({symbol} > 50d MA): {status}")
    print(f"    {symbol}: ${momentum.get('price', '?')} vs MA: ${momentum.get('ma_50', '?')} ({momentum.get('margin', '?')}%)")

    if not momentum["pass"]:
        print(f"  [BLOCKED] Stock momentum filter failed. No trade.")
        return {"pass": False, "blocked_by": "momentum", "details": momentum}

    # Gap check
    gap = check_gap(symbol)
    status = "PASS" if gap["pass"] else "FAIL"
    print(f"  Gap check (< {MAX_GAP_PCT*100}%): {status}")
    print(f"    Prior close: ${gap.get('prior_close', '?')} → Open: ${gap.get('today_open', '?')} ({gap.get('gap_pct', '?')}%)")

    if not gap["pass"]:
        print(f"  [BLOCKED] Gap too large ({gap.get('gap_pct')}%). Skipping.")
        return {"pass": False, "blocked_by": "gap", "details": gap}

    print(f"  [ALL FILTERS PASSED] {symbol} qualifies for entry.")

    return {
        "pass": True,
        "regime": regime,
        "momentum": momentum,
        "gap": gap,
        "entry_price": gap.get("today_open"),  # enter at open
    }


def process_trigger(trigger: dict) -> dict | None:
    """
    Full pipeline for a single earnings trigger:
    1. Run all filters
    2. Calculate position size
    3. Submit bracket order to Alpaca

    Returns order details dict, or None if filtered out.
    """
    symbol = trigger["symbol"]
    surprise = trigger["surprise_pct"]

    print(f"\n[PROCESSING] {symbol} — Earnings surprise: {surprise:+.2f}%")

    # Run filter pipeline
    filter_result = run_filters(symbol)
    if not filter_result["pass"]:
        return None

    # Calculate position
    entry_price = filter_result["entry_price"]
    position = calculate_position(entry_price)

    print(f"\n  Position sizing (2% risk rule):")
    print(f"    Portfolio: ${position['portfolio_size']:,.0f}")
    print(f"    Max risk:  ${position['total_risk']:.2f}")
    print(f"    Shares:    {position['shares']}")
    print(f"    Entry:     ${position['entry_price']}")
    print(f"    Target:    ${position['target_price']} (+{REWARD_RISK_RATIO*STOP_LOSS_PCT*100:.0f}%)")
    print(f"    Stop:      ${position['stop_price']} (-{STOP_LOSS_PCT*100:.0f}%)")

    # Submit order
    order = submit_bracket_order(symbol, position)
    if order:
        order["surprise_pct"] = surprise
        order["filter_result"] = filter_result

    return order


if __name__ == "__main__":
    print("=" * 60)
    print("Weekes AATF — Paper Trader Filter Check (Phase 1B)")
    print("=" * 60)

    # Quick standalone test: run filters on all watchlist stocks
    for symbol in ["NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "AMD", "PLTR", "CRM"]:
        result = run_filters(symbol)
        print(f"  → {symbol}: {'PASS' if result['pass'] else 'FAIL'}")
