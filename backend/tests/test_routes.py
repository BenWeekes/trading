from fastapi.testclient import TestClient

from app.main import app
from app.db.helpers import new_id, utcnow_iso
from app.db.repositories import upsert_recommendation


client = TestClient(app)


def seed_recommendation(symbol: str = "NVDA") -> dict:
    recommendation = {
        "id": new_id("rec"),
        "symbol": symbol,
        "direction": None,
        "status": "observing",
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
        "conviction": 5,
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


def test_random_event_flow():
    response = client.post("/api/demo/random-event")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event"]["symbol"]
    assert payload["recommendation"]["status"] == "awaiting_user_feedback"


def test_avatar_status_route():
    response = client.get("/api/trader/avatar/status")
    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload
    assert "client_url" in payload


def test_agora_chat_completions_route():
    recommendation = seed_recommendation("AMD")
    response = client.post(
        "/api/agora/chat/completions",
        json={
            "model": "trader-proxy-v1",
            "messages": [{"role": "user", "content": "@trader what do you think about this setup?"}],
            "context": {"recommendation_id": recommendation["id"], "symbol": "AMD"},
            "stream": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["choices"][0]["message"]["content"]


def test_agora_chat_requires_existing_recommendation_or_symbol_match():
    response = client.post(
        "/api/agora/chat/completions",
        json={
            "model": "trader-proxy-v1",
            "messages": [{"role": "user", "content": "@trader what do you think?"}],
            "context": {"symbol": "NOPE"},
            "stream": False,
        },
    )
    assert response.status_code == 404


def test_execute_requires_approval():
    recommendation = seed_recommendation("META")
    response = client.post(f"/api/recs/{recommendation['id']}/execute")
    assert response.status_code == 400
    assert "approved" in response.json()["detail"]


def test_ready_route_moves_feedback_to_approval():
    event_payload = client.post("/api/demo/random-event").json()
    recommendation_id = event_payload["recommendation"]["id"]
    response = client.post(f"/api/recs/{recommendation_id}/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_user_approval"
