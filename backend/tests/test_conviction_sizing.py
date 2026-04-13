from app.services.position_sizing import calculate_position, conviction_multiplier


def test_conviction_10_gets_bonus():
    assert conviction_multiplier(10) == 1.25


def test_conviction_8_9_gets_full_size():
    assert conviction_multiplier(8) == 1.0
    assert conviction_multiplier(9) == 1.0


def test_conviction_7_gets_reduced():
    assert conviction_multiplier(7) == 0.75


def test_conviction_below_7_gets_zero():
    assert conviction_multiplier(6) == 0.0
    assert conviction_multiplier(3) == 0.0
    assert conviction_multiplier(1) == 0.0


def test_conviction_none_gets_reduced():
    assert conviction_multiplier(None) == 0.75


def test_position_sizing_scales_with_conviction():
    full = calculate_position(100.0, 100000.0, conviction=8)
    reduced = calculate_position(100.0, 100000.0, conviction=7)
    assert reduced["position_size_shares"] < full["position_size_shares"]
    assert reduced["position_size_shares"] == pytest.approx(full["position_size_shares"] * 0.75, rel=0.05)


def test_conviction_below_threshold_zero_shares():
    result = calculate_position(100.0, 100000.0, conviction=5)
    assert result["position_size_shares"] == 0


def test_high_conviction_larger_than_standard():
    standard = calculate_position(100.0, 100000.0, conviction=8)
    boosted = calculate_position(100.0, 100000.0, conviction=10)
    assert boosted["position_size_shares"] > standard["position_size_shares"]


def test_size_note_included():
    result = calculate_position(100.0, 100000.0, conviction=7)
    assert "75%" in result["size_note"]
    assert "Conviction 7/10" in result["size_note"]


import pytest
