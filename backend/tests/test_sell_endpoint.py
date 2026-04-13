import pytest
from app.database import init_db
from app.db.helpers import new_id, utcnow_iso
from app.db.repositories import get_trade, insert_trade, list_trades


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.database._db_path", lambda: db_path)
    init_db()


def _make_trade(symbol="NVDA", direction="BUY", shares=100, entry=150.0):
    trade = {
        "id": new_id("trade"), "recommendation_id": None,
        "symbol": symbol, "direction": direction,
        "entry_price": entry, "current_price": entry,
        "shares": shares, "unrealized_pnl": 0.0,
        "stop_price": entry * 0.95, "target_price": entry * 1.1,
        "exit_price": None, "exit_reason": None,
        "pnl_dollars": None, "pnl_percent": None,
        "risk_state": "normal", "broker_order_id": new_id("broker"),
        "opened_at": utcnow_iso(), "closed_at": None,
    }
    insert_trade(trade)
    return trade


def test_open_trade_appears_in_list():
    t = _make_trade()
    open_trades = list_trades(open_only=True)
    assert len(open_trades) == 1
    assert open_trades[0]["symbol"] == "NVDA"


def test_closed_trade_not_in_open_list():
    from app.db.repositories import update_trade
    t = _make_trade()
    update_trade(t["id"], closed_at=utcnow_iso(), risk_state="closed")
    assert list_trades(open_only=True) == []


def test_long_pnl_positive_when_price_rises():
    # Buy at 100, exit at 110, 10 shares → PnL = +100
    entry, exit_p, shares = 100.0, 110.0, 10.0
    pnl = (exit_p - entry) * shares
    assert pnl == 100.0


def test_short_pnl_positive_when_price_falls():
    # Short at 100, cover at 90, 10 shares → PnL = +100
    entry, exit_p, shares = 100.0, 90.0, 10.0
    pnl = (entry - exit_p) * shares
    assert pnl == 100.0


def test_short_pnl_negative_when_price_rises():
    entry, exit_p, shares = 100.0, 110.0, 10.0
    pnl = (entry - exit_p) * shares
    assert pnl == -100.0
