from app.analysis.pead_strategy_lab import StrategyVariant


def test_strategy_variant_fields():
    variant = StrategyVariant(
        name="test",
        min_surprise_pct=8.0,
        stop_loss_pct=0.03,
        reward_risk_ratio=2.0,
        max_gap_pct=4.0,
        max_hold_days=10,
        require_momentum=False,
        require_revenue_beat=True,
        top_n_per_month=1,
    )
    assert variant.name == "test"
    assert variant.min_surprise_pct == 8.0
    assert variant.max_hold_days == 10
    assert variant.require_momentum is False
    assert variant.require_revenue_beat is True
    assert variant.top_n_per_month == 1
