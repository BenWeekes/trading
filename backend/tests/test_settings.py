import pytest
from app.database import init_db
from app.db.repositories import get_all_strategy_settings, get_strategy_setting, set_strategy_setting
from app.routes.strategy_settings import DEFAULTS


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.database._db_path", lambda: db_path)
    init_db()


def test_defaults_returned_when_empty():
    result = get_all_strategy_settings()
    assert result == {}  # no saved settings yet


def test_set_and_get_setting():
    set_strategy_setting("min_conviction_to_trade", "8")
    assert get_strategy_setting("min_conviction_to_trade") == "8"


def test_set_overwrites():
    set_strategy_setting("risk_per_trade_pct", "1.0")
    set_strategy_setting("risk_per_trade_pct", "0.5")
    assert get_strategy_setting("risk_per_trade_pct") == "0.5"


def test_defaults_has_expected_keys():
    assert "min_surprise_pct" in DEFAULTS
    assert "min_conviction_to_trade" in DEFAULTS
    assert "strategies_enabled" in DEFAULTS
    assert "max_positions" in DEFAULTS
    assert "weight_surprise_magnitude" in DEFAULTS


def test_all_scoring_weights_sum_to_one():
    weights = [float(v) for k, v in DEFAULTS.items() if k.startswith("weight_")]
    assert abs(sum(weights) - 1.0) < 0.01, f"scoring weights sum to {sum(weights)}, expected 1.0"
