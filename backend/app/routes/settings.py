from __future__ import annotations

from fastapi import APIRouter

from ..db.repositories import get_all_strategy_settings, set_strategy_setting


router = APIRouter(prefix="/api/settings", tags=["settings"])

# Defaults from operator spec — used when no DB value exists
DEFAULTS: dict[str, str] = {
    # Strategy selection
    "strategies_enabled": "PEAD",

    # Universe filters
    "min_price": "5.0",
    "min_avg_daily_volume": "5000000",
    "min_market_cap": "500000000",
    "exclude_etfs": "true",
    "exclude_adrs": "true",
    "exclude_spacs": "true",
    "exclude_biotech_binary": "true",

    # PEAD entry conditions
    "min_surprise_pct": "5.0",
    "min_volume_ratio": "2.0",
    "require_positive_guidance": "true",
    "require_no_negative_news": "true",

    # Position sizing & risk
    "risk_per_trade_pct": "1.0",
    "max_positions": "15",
    "max_sector_exposure_pct": "30",
    "max_gross_exposure_pct": "100",
    "stop_type": "atr",
    "stop_atr_multiplier": "2.0",
    "stop_fixed_pct": "5.0",

    # Conviction thresholds
    "min_conviction_to_trade": "7",
    "conviction_10_multiplier": "1.25",
    "conviction_8_9_multiplier": "1.0",
    "conviction_7_multiplier": "0.75",

    # Hold period
    "target_hold_days": "12",
    "max_hold_days": "30",
    "exit_before_next_earnings": "true",

    # Execution
    "order_type": "limit",
    "avoid_first_minutes": "5",
    "stagger_in_poor_liquidity": "true",

    # Regime
    "pause_on_high_vol_regime": "true",
    "regime_indicator": "spy_above_200d",

    # Scoring weights (PEAD)
    "weight_surprise_magnitude": "0.25",
    "weight_guidance_tone": "0.20",
    "weight_mgmt_confidence": "0.15",
    "weight_analyst_revisions": "0.10",
    "weight_volume_confirmation": "0.15",
    "weight_regime": "0.10",
    "weight_news_penalty": "0.05",
}

# Group definitions for the frontend panel
GROUPS = [
    {
        "id": "strategies",
        "label": "Strategies",
        "keys": ["strategies_enabled"],
    },
    {
        "id": "universe",
        "label": "Universe Filters",
        "keys": ["min_price", "min_avg_daily_volume", "min_market_cap",
                 "exclude_etfs", "exclude_adrs", "exclude_spacs", "exclude_biotech_binary"],
    },
    {
        "id": "pead_entry",
        "label": "PEAD Entry Conditions",
        "keys": ["min_surprise_pct", "min_volume_ratio", "require_positive_guidance", "require_no_negative_news"],
    },
    {
        "id": "risk",
        "label": "Risk & Position Sizing",
        "keys": ["risk_per_trade_pct", "max_positions", "max_sector_exposure_pct",
                 "max_gross_exposure_pct", "stop_type", "stop_atr_multiplier", "stop_fixed_pct"],
    },
    {
        "id": "conviction",
        "label": "Conviction Scaling",
        "keys": ["min_conviction_to_trade", "conviction_10_multiplier",
                 "conviction_8_9_multiplier", "conviction_7_multiplier"],
    },
    {
        "id": "holding",
        "label": "Hold Period & Exits",
        "keys": ["target_hold_days", "max_hold_days", "exit_before_next_earnings"],
    },
    {
        "id": "execution",
        "label": "Execution",
        "keys": ["order_type", "avoid_first_minutes", "stagger_in_poor_liquidity"],
    },
    {
        "id": "regime",
        "label": "Regime Gating",
        "keys": ["pause_on_high_vol_regime", "regime_indicator"],
    },
    {
        "id": "scoring",
        "label": "PEAD Scoring Weights",
        "keys": ["weight_surprise_magnitude", "weight_guidance_tone", "weight_mgmt_confidence",
                 "weight_analyst_revisions", "weight_volume_confirmation", "weight_regime", "weight_news_penalty"],
    },
]


@router.get("")
async def get_settings():
    """Return all strategy settings merged with defaults."""
    saved = get_all_strategy_settings()
    merged = {k: saved.get(k, v) for k, v in DEFAULTS.items()}
    return {"settings": merged, "groups": GROUPS}


@router.patch("")
async def update_settings(payload: dict):
    """Update one or more strategy settings."""
    updated = {}
    for key, value in payload.items():
        if key in DEFAULTS:
            set_strategy_setting(key, str(value))
            updated[key] = str(value)
    return {"updated": updated}
