from app.analysis.pead_proxy_backtest import _revenue_surprise_pct, _simulate_long_exit


def test_simulate_long_exit_hits_target_before_time_stop():
    bars = [
        {"date": None, "open": 100.0, "high": 103.0, "low": 99.0, "close": 102.0},
        {"date": None, "open": 102.0, "high": 111.0, "low": 101.0, "close": 110.0},
    ]
    exit_idx, exit_price, exit_reason = _simulate_long_exit(bars, entry_idx=0, stop_price=95.0, target_price=110.0, max_hold_days=20)
    assert exit_idx == 1
    assert exit_price == 110.0
    assert exit_reason == "target"


def test_simulate_long_exit_uses_conservative_same_day_stop_when_both_hit():
    bars = [
        {"date": None, "open": 100.0, "high": 111.0, "low": 94.0, "close": 105.0},
    ]
    exit_idx, exit_price, exit_reason = _simulate_long_exit(bars, entry_idx=0, stop_price=95.0, target_price=110.0, max_hold_days=20)
    assert exit_idx == 0
    assert exit_price == 95.0
    assert exit_reason == "stop"


def test_simulate_long_exit_falls_back_to_time_stop_close():
    bars = [
        {"date": None, "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": None, "open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0},
        {"date": None, "open": 102.0, "high": 103.0, "low": 101.0, "close": 101.5},
    ]
    exit_idx, exit_price, exit_reason = _simulate_long_exit(bars, entry_idx=0, stop_price=95.0, target_price=110.0, max_hold_days=3)
    assert exit_idx == 2
    assert exit_price == 101.5
    assert exit_reason == "time_stop"


def test_revenue_surprise_pct_computes_percentage():
    value = _revenue_surprise_pct({"revenueActual": 110.0, "revenueEstimated": 100.0})
    assert value == 10.0
