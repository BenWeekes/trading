from __future__ import annotations

import math

from ..config import get_settings


def calculate_position(entry_price: float, portfolio_size: float) -> dict:
    settings = get_settings()
    stop_price = round(entry_price * (1 - settings.stop_loss_pct), 2)
    risk_per_share = max(entry_price - stop_price, 0.01)
    max_risk = portfolio_size * settings.risk_per_trade
    shares = math.floor((max_risk / risk_per_share) * 100) / 100
    target_price = round(
        entry_price + (settings.reward_risk_ratio * (entry_price - stop_price)),
        2,
    )
    return {
        "entry_price": round(entry_price, 2),
        "entry_logic": "Current market/open price used as entry reference.",
        "stop_price": stop_price,
        "stop_logic": f"{settings.stop_loss_pct:.0%} stop from entry based on portfolio risk rules.",
        "target_price": target_price,
        "target_logic": f"{settings.reward_risk_ratio:.1f}:1 reward-to-risk target.",
        "position_size_shares": shares,
        "position_size_dollars": round(shares * entry_price, 2),
    }
