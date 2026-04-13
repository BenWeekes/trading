from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.main import app
from app.db.helpers import new_id, utcnow_iso
from app.db.repositories import upsert_recommendation


client = TestClient(app)


def seed_recommendation(symbol: str = "NVDA", status: str = "observing", direction: Optional[str] = None) -> dict:
    recommendation = {
        "id": new_id("rec"),
        "symbol": symbol,
        "direction": direction,
        "status": status,
        "strategy_type": "TEST",
        "thesis": f"{symbol} seeded for route test.",
        "entry_price": 100.0,
        "entry_logic": "seeded entry",
        "stop_price": 95.0,
        "stop_logic": "seeded stop",
        "target_price": 110.0,
        "target_logic": "seeded target",
        "position_size_shares": 10.0,
        "position_size_dollars": 1000.0,
        "time_horizon": "test",
        "conviction": 7,
        "supporting_roles": [],
        "blocking_risks": [],
        "created_at": utcnow_iso(),
        "updated_at": utcnow_iso(),
    }
    upsert_recommendation(recommendation)
    return recommendation


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_random_event_returns_event_and_recommendation():
    response = client.post("/api/demo/random-event")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event"]["symbol"]
    assert payload["recommendation"]["id"]
    # analysis runs in background — rec may be observing or under_discussion
    # analysis may complete instantly with mock provider, or be in progress
    assert payload["recommendation"]["status"] in ("observing", "under_discussion", "awaiting_user_feedback")


def test_avatar_status_route():
    response = client.get("/api/trader/avatar/status")
    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload


def test_execute_requires_approval():
    recommendation = seed_recommendation("META")
    response = client.post(f"/api/recs/{recommendation['id']}/execute")
    assert response.status_code == 400
    assert "approved" in response.json()["detail"]


def test_approve_requires_awaiting_approval_state():
    recommendation = seed_recommendation("AAPL", status="awaiting_user_feedback", direction="BUY")
    response = client.post(f"/api/recs/{recommendation['id']}/approve", json={"shares": 10})
    assert response.status_code == 400
    assert "Ready" in response.json()["detail"]


def test_ready_then_approve_flow():
    recommendation = seed_recommendation("TSLA", status="awaiting_user_feedback", direction="BUY")
    # Step 1: ready
    r1 = client.post(f"/api/recs/{recommendation['id']}/ready")
    assert r1.status_code == 200
    assert r1.json()["status"] == "awaiting_user_approval"
    # Step 2: approve
    r2 = client.post(f"/api/recs/{recommendation['id']}/approve", json={"shares": 5})
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"


def test_reject_from_feedback():
    recommendation = seed_recommendation("GOOG", status="awaiting_user_feedback", direction="SHORT")
    response = client.post(f"/api/recs/{recommendation['id']}/reject", json={"reason": "not convinced"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_settings_get():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert "groups" in data
    assert "min_conviction_to_trade" in data["settings"]
    assert "strategies_enabled" in data["settings"]


def test_settings_patch():
    response = client.patch("/api/settings", json={"min_conviction_to_trade": "8"})
    assert response.status_code == 200
    assert response.json()["updated"]["min_conviction_to_trade"] == "8"
