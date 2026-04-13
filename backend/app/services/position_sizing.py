from __future__ import annotations

import math

from ..config import get_settings


def conviction_multiplier(conviction: int | None) -> float:
    """Scale position size by conviction. Higher conviction = bigger trade.

    10/10 → 1.25x (max confidence bonus)
     9/10 → 1.0x  (full standard size)
     8/10 → 1.0x  (full standard size)
     7/10 → 0.75x (decent but not strong)
     6/10 → 0.5x  (marginal)
     5/10 → 0.25x (minimum viable)
    <5    → 0.0   (don't trade — too low conviction)
    """
    if conviction is None:
        return 0.5  # unknown conviction = half size
    if conviction >= 10:
        return 1.25
    if conviction >= 8:
        return 1.0
    if conviction >= 7:
        return 0.75
    if conviction >= 6:
        return 0.5
    if conviction >= 5:
        return 0.25
    return 0.0  # below 5 = don't trade


def calculate_position(entry_price: float, portfolio_size: float, conviction: int | None = None) -> dict:
    settings = get_settings()
    stop_price = round(entry_price * (1 - settings.stop_loss_pct), 2)
    risk_per_share = max(entry_price - stop_price, 0.01)
    max_risk = portfolio_size * settings.risk_per_trade
    base_shares = math.floor((max_risk / risk_per_share) * 100) / 100

    # Apply conviction scaling
    multiplier = conviction_multiplier(conviction)
    shares = math.floor(base_shares * multiplier * 100) / 100

    target_price = round(
        entry_price + (settings.reward_risk_ratio * (entry_price - stop_price)),
        2,
    )

    size_note = f"{multiplier:.0%} of standard size" if multiplier != 1.0 else "full standard size"
    if conviction is not None:
        size_note = f"Conviction {conviction}/10 → {size_note}"

    return {
        "entry_price": round(entry_price, 2),
        "entry_logic": "Current market/open price used as entry reference.",
        "stop_price": stop_price,
        "stop_logic": f"{settings.stop_loss_pct:.0%} stop from entry based on portfolio risk rules.",
        "target_price": target_price,
        "target_logic": f"{settings.reward_risk_ratio:.1f}:1 reward-to-risk target.",
        "position_size_shares": shares,
        "position_size_dollars": round(shares * entry_price, 2),
        "conviction_multiplier": multiplier,
        "size_note": size_note,
    }
