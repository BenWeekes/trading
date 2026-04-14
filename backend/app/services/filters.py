from __future__ import annotations

from ..config import get_settings
from ..db.repositories import get_all_strategy_settings


def apply_pead_filters(quote: dict, spy_quote: dict) -> dict:
    """Apply PEAD filters. Returns filter results with per-filter pass/fail.

    PEAD V2 uses regime + gap only (no momentum).
    Legacy PEAD uses regime + momentum + gap.
    """
    settings = get_settings()
    strat = get_all_strategy_settings()

    price = float(quote.get("price") or 0)
    ma50 = float(quote.get("priceAvg50") or 0)
    spy_price = float(spy_quote.get("price") or 0)
    spy_ma200 = float(spy_quote.get("priceAvg200") or 0)
    prev_close = float(quote.get("previousClose") or 0)
    today_open = float(quote.get("open") or price)

    regime_pass = bool(spy_price and spy_ma200 and spy_price > spy_ma200)
    momentum_pass = bool(price and ma50 and price > ma50)
    gap_pct = (((today_open - prev_close) / prev_close) * 100) if prev_close else 0.0
    gap_pass = abs(gap_pct) <= (settings.max_gap_pct * 100)

    # V2 strategy: regime + gap only, no momentum
    # Legacy: regime + momentum + gap
    strategy = strat.get("strategies_enabled", "PEAD")
    if "V2" in strategy.upper():
        all_pass = regime_pass and gap_pass
    else:
        all_pass = regime_pass and momentum_pass and gap_pass

    blocked_by = None
    if not regime_pass:
        blocked_by = "regime"
    elif not all_pass and not momentum_pass and "V2" not in strategy.upper():
        blocked_by = "momentum"
    elif not gap_pass:
        blocked_by = "gap"

    return {
        "filters_passed": all_pass,
        "blocked_by": blocked_by,
        "strategy": strategy,
        "regime": {"pass": regime_pass, "price": spy_price, "ma_200": spy_ma200},
        "momentum": {"pass": momentum_pass, "price": price, "ma_50": ma50, "enforced": "V2" not in strategy.upper()},
        "gap": {"pass": gap_pass, "prior_close": prev_close, "today_open": today_open, "gap_pct": round(gap_pct, 2)},
    }
