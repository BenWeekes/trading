from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.main import app
from app.db.helpers import new_id, utcnow_iso
from app.db.repositories import insert_event, list_role_messages, upsert_recommendation
from app.services.voice_tools import set_active_context


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
    assert payload["recommendation"]["status"] in ("observing", "under_discussion", "awaiting_user_feedback", "awaiting_user_approval")


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


def test_agora_chat_persists_voice_user_and_trader_messages(monkeypatch):
    recommendation = seed_recommendation("MSFT", status="awaiting_user_feedback", direction="BUY")
    session_id = "voice-test-session"
    set_active_context(session_id, recommendation["id"])

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output_text": "I still like MSFT here. Buy the suggested size.", "output": []}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.routes.agora.httpx.AsyncClient", FakeAsyncClient)

    response = client.post(
        "/api/agora/chat/completions",
        json={
            "channel": session_id,
            "messages": [
                {"role": "user", "content": "What do you think about MSFT after this move?"},
            ],
        },
    )

    assert response.status_code == 200
    timeline = list_role_messages(recommendation_id=recommendation["id"])
    assert any(
        msg["sender"] == "user"
        and msg["role"] == "trader"
        and msg["structured_payload"].get("type") == "voice_user_message"
        and msg.get("discussion_subject_id")
        and "MSFT after this move" in msg["message_text"]
        for msg in timeline
    )
    assert any(
        msg["sender"] == "role:trader"
        and msg["role"] == "trader"
        and msg["structured_payload"].get("type") == "voice_response"
        and msg.get("discussion_subject_id")
        and "I still like MSFT here" in msg["message_text"]
        for msg in timeline
    )


def test_subject_resolve_for_recommendation():
    recommendation = seed_recommendation("NFLX", status="awaiting_user_feedback", direction="BUY")
    response = client.post("/api/subjects/resolve", json={"recommendation_id": recommendation["id"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"]["subject_type"] == "recommendation"
    assert payload["subject"]["recommendation_id"] == recommendation["id"]
    assert payload["recommendation"]["id"] == recommendation["id"]


def test_subject_resolve_for_event_with_linked_recommendation():
    recommendation = seed_recommendation("AMD", status="awaiting_user_feedback", direction="BUY")
    event = {
        "id": new_id("evt"),
        "type": "news",
        "symbol": "AMD",
        "headline": "AMD rises on new product cycle",
        "body_excerpt": "Event for subject resolution test.",
        "source": "Unit Test",
        "importance": 3,
        "linked_recommendation_ids": [recommendation["id"]],
        "timestamp": utcnow_iso(),
    }
    insert_event(event)
    response = client.post(
        "/api/subjects/resolve",
        json={"event_id": event["id"], "linked_recommendation_id": recommendation["id"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"]["subject_type"] == "news"
    assert payload["subject"]["event_id"] == event["id"]
    assert payload["subject"]["recommendation_id"] == recommendation["id"]
    assert payload["event"]["id"] == event["id"]
