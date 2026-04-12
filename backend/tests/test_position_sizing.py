from app.services.position_sizing import calculate_position


def test_position_sizing_has_expected_fields():
    result = calculate_position(100.0, 100000.0)
    assert result["entry_price"] == 100.0
    assert result["stop_price"] < result["entry_price"]
    assert result["target_price"] > result["entry_price"]
    assert result["position_size_shares"] > 0
