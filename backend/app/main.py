from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .db.helpers import utcnow_iso
from .db.repositories import get_role_config, upsert_role_config
from .routes import agora, config, events, recommendations, roles, scanner, trades


def seed_role_configs() -> None:
    provider = "openai" if settings.openai_api_key else "mock"
    default_model = settings.openai_model if settings.openai_api_key else "mock-v1"
    defaults = {
        "research": {"provider": provider, "default_model": default_model},
        "risk": {"provider": provider, "default_model": default_model},
        "quant_pricing": {"provider": provider, "default_model": default_model},
        "trader": {"provider": provider, "default_model": default_model},
    }
    for role_name, values in defaults.items():
        existing = get_role_config(role_name)
        if existing and not (settings.openai_api_key and existing.get("provider") == "mock"):
            continue
        upsert_role_config(
            {
                "role_name": role_name,
                "provider": values["provider"],
                "default_model": values["default_model"],
                "escalation_model": None,
                "system_prompt_version": "v1",
                "demo_prompt_version": "demo_v1",
                "tool_permissions": ["events", "recommendations", "portfolio"],
                "cost_budget_per_day": 5.0,
                "max_tokens_per_call": 4096,
                "updated_at": utcnow_iso(),
            }
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_role_configs()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(scanner.router)
app.include_router(roles.router)
app.include_router(recommendations.router)
app.include_router(trades.router)
app.include_router(config.router)
app.include_router(agora.router)


@app.get("/")
async def root():
    return {"app": settings.app_name, "status": "ok"}
