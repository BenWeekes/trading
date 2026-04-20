from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import init_db
from .db.helpers import utcnow_iso
from .db.repositories import get_role_config, upsert_role_config
from .routes import agora, config, events, recommendations, roles, scanner, strategy_settings, subjects, trades


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


async def _market_pulse_loop():
    """Background market pulse — fast polling gainers/losers/active."""
    from .services.market_pulse import run_pulse
    await asyncio.sleep(3)
    await run_pulse()


async def _market_poller_loop():
    """Background market data polling."""
    from .services.market_poller import run_poller
    await asyncio.sleep(5)
    await run_poller()


async def _exit_check_loop():
    """Background loop: check exits every 60 seconds, independent of browser.

    NOTE: this runs in-process. If the app restarts or runs multiple workers,
    exits may be delayed or duplicated. For production, replace with an external
    scheduler (cron, celery, or cloud task queue).
    """
    from .services.exit_manager import check_exits
    await asyncio.sleep(10)  # wait for startup
    print("[exit-manager] background exit checker started (60s interval)")
    while True:
        try:
            closed = await check_exits()
            if closed:
                for c in closed:
                    print(f"[exit-manager] auto-exit {c['symbol']}: {c['reason']} pnl={c['pnl']}")
        except asyncio.CancelledError:
            print("[exit-manager] background loop cancelled")
            break
        except Exception as exc:
            print(f"[exit-manager] error: {exc}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_role_configs()
    exit_task = asyncio.create_task(_exit_check_loop())
    poller_task = asyncio.create_task(_market_poller_loop())
    pulse_task = asyncio.create_task(_market_pulse_loop())
    yield
    exit_task.cancel()
    poller_task.cancel()
    pulse_task.cancel()


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
app.include_router(subjects.router)
app.include_router(scanner.router)
app.include_router(roles.router)
app.include_router(recommendations.router)
app.include_router(trades.router)
app.include_router(config.router)
app.include_router(strategy_settings.router)
app.include_router(agora.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": type(exc).__name__},
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/")
async def root():
    return {"app": settings.app_name, "status": "ok"}
