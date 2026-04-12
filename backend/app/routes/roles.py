from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..db.repositories import get_role_config, list_role_configs, list_role_messages, list_role_threads, upsert_role_config
from ..db.helpers import utcnow_iso
from .deps import get_orchestrator


router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("")
async def roles_index():
    return {"roles": ["research", "risk", "quant_pricing", "trader"]}


@router.get("/config")
async def role_configs():
    return {"configs": list_role_configs()}


@router.put("/{name}/config")
async def update_role_config(name: str, payload: dict):
    existing = get_role_config(name) or {"role_name": name}
    existing.update(payload)
    existing["role_name"] = name
    existing["updated_at"] = utcnow_iso()
    upsert_role_config(existing)
    return existing


@router.get("/{name}/threads")
async def role_threads(name: str, recommendation_id: str | None = None):
    return {"threads": list_role_threads(role=name, recommendation_id=recommendation_id)}


@router.get("/{name}/threads/{thread_id}")
async def role_thread(name: str, thread_id: str):
    messages = list_role_messages(role=name, thread_id=thread_id)
    return {"messages": messages}


@router.get("/{name}/history")
async def role_history(name: str, recommendation_id: str):
    return {"messages": list_role_messages(role=name, recommendation_id=recommendation_id)}


@router.post("/{name}/chat")
async def role_chat(name: str, payload: dict):
    recommendation_id = payload.get("recommendation_id")
    message = payload.get("message")
    if not recommendation_id or not message:
        raise HTTPException(status_code=400, detail="recommendation_id and message are required")
    orchestrator = get_orchestrator()
    return await orchestrator.user_chat(name, recommendation_id, message)
