from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..db.repositories import list_costs


router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def config():
    settings = get_settings()
    return {
        "app_mode": settings.app_mode,
        "event_mode": settings.event_mode,
        "demo_mode": settings.demo_mode,
        "backend_port": settings.backend_port,
        "frontend_port": settings.frontend_port,
        "agora": {
            "enabled": settings.agora_enabled,
            "backend_url": settings.agora_backend_url,
            "client_url": settings.agora_avatar_client_url,
            "profile": settings.agora_profile,
        },
    }


@router.put("/config")
async def update_config(payload: dict):
    return {"updated": payload}


@router.get("/status")
async def status():
    settings = get_settings()
    return {
        "ok": True,
        "mode": settings.app_mode,
        "event_mode": settings.event_mode,
        "demo_mode": settings.demo_mode,
        "providers": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "fmp": bool(settings.fmp_api_key),
            "alpaca": bool(settings.alpaca_api_key and settings.alpaca_secret_key),
            "agora": settings.agora_enabled,
        },
    }


@router.get("/costs")
async def costs():
    return {"costs": list_costs()}
