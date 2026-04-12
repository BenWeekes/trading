from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import get_recommendation, list_recommendations, upsert_recommendation
from ..roles import Orchestrator
from ..services.agora_bridge import trader_avatar_bridge


router = APIRouter(prefix="/api", tags=["agora"])
orchestrator = Orchestrator()
registered_agents: dict[str, dict] = {}


@router.get("/trader/avatar/status")
async def trader_avatar_status(recommendation_id: str | None = Query(default=None)):
    return trader_avatar_bridge.session_status(recommendation_id)


@router.post("/trader/avatar/start")
async def trader_avatar_start(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    if not recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id is required")
    if not get_recommendation(recommendation_id):
        raise HTTPException(status_code=404, detail="Recommendation not found")
    try:
        return await trader_avatar_bridge.start(recommendation_id, channel=payload.get("channel"))
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/trader/avatar/speak")
async def trader_avatar_speak(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    text = payload.get("text")
    if not recommendation_id or not text:
        raise HTTPException(status_code=400, detail="recommendation_id and text are required")
    try:
        return await trader_avatar_bridge.speak(
            recommendation_id,
            text,
            priority=payload.get("priority", "APPEND"),
        )
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/trader/avatar/stop")
async def trader_avatar_stop(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    if not recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id is required")
    try:
        return await trader_avatar_bridge.stop(recommendation_id)
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/agora/chat/completions")
async def agora_chat_completions(payload: dict):
    messages = payload.get("messages") or []
    if not messages:
        raise HTTPException(status_code=400, detail="messages are required")
    context = payload.get("context") or {}
    recommendation = _resolve_recommendation(context)
    latest_user_message = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    if not latest_user_message:
        raise HTTPException(status_code=400, detail="A user message is required")
    message_text = _content_to_text(latest_user_message.get("content"))
    role_response = await orchestrator.route_group_chat(recommendation["id"], message_text)
    content = role_response["message_text"]
    if payload.get("stream"):
        return StreamingResponse(_stream_chat_completion(content), media_type="text/event-stream")
    return {
        "id": new_id("chatcmpl"),
        "object": "chat.completion",
        "created": int(__import__("time").time()),
        "model": payload.get("model") or "trader-proxy-v1",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


@router.post("/agora/register-agent")
async def register_agent(payload: dict):
    agent_id = payload.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    registered_agents[agent_id] = payload
    return {"ok": True, "registered": True, "agent_id": agent_id}


@router.post("/agora/unregister-agent")
async def unregister_agent(payload: dict):
    agent_id = payload.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    existed = registered_agents.pop(agent_id, None) is not None
    return {"ok": True, "unregistered": existed, "agent_id": agent_id}


def _resolve_recommendation(context: dict) -> dict:
    recommendation_id = context.get("recommendation_id")
    if recommendation_id:
        recommendation = get_recommendation(recommendation_id)
        if recommendation:
            return recommendation
        raise HTTPException(status_code=404, detail="Recommendation not found")
    symbol = context.get("symbol")
    if symbol:
        for recommendation in list_recommendations(limit=50):
            if recommendation["symbol"] == symbol:
                return recommendation
        raise HTTPException(status_code=404, detail="No recommendation exists for that symbol")
    latest = list_recommendations(limit=1)
    if latest:
        return latest[0]
    raise HTTPException(status_code=400, detail="No recommendation context is available")


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "input_text"}:
                parts.append(str(item.get("text", "")))
        return " ".join(part for part in parts if part).strip()
    return str(content or "")


async def _stream_chat_completion(content: str) -> AsyncGenerator[bytes, None]:
    chunk = {
        "id": new_id("chatcmpl"),
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": "trader-proxy-v1",
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(chunk)}\n\n".encode()
    done = {
        "id": new_id("chatcmpl"),
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": "trader-proxy-v1",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done)}\n\n".encode()
    yield b"data: [DONE]\n\n"
