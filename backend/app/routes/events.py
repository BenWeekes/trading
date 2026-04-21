from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ..db.repositories import get_event, insert_event, list_events
from ..services.event_bus import event_bus
from ..services.mock_events import demo_scenarios
import random
from ..db.helpers import new_id, utcnow_iso


router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def events(limit: int = Query(default=100, le=500), type: str | None = None):
    return {"events": list_events(limit=limit, event_type=type)}


@router.get("/events/{event_id}")
async def event_detail(event_id: str):
    return get_event(event_id)


@router.post("/events/mock")
async def create_mock_events():
    events = demo_scenarios()
    for event in events:
        insert_event(event)
        await event_bus.publish("market_event", event)
    return {"events": events}


@router.post("/events/replay")
async def replay_mock_events():
    events = demo_scenarios()
    for event in events:
        await event_bus.publish("market_event", event)
    return {"replayed": len(events)}


@router.post("/events/random")
async def random_event():
    symbols = ["NVDA", "AAPL", "MSFT", "META", "AMD", "PLTR", "CRM"]
    event_type = random.choice(["earnings", "news", "price_alert"])
    symbol = random.choice(symbols)
    templates = {
        "earnings": f"{symbol} posts surprise earnings result and updates outlook",
        "news": f"{symbol} moves on product, analyst, or sector news flow",
        "price_alert": f"{symbol} sees abrupt intraday move on unusual volume",
    }
    event = {
        "id": new_id("evt"),
        "type": event_type,
        "symbol": symbol,
        "headline": templates[event_type],
        "body_excerpt": "Random demo event generated for local testing.",
        "source": "Demo Generator",
        "timestamp": utcnow_iso(),
        "importance": random.randint(2, 5),
        "linked_recommendation_ids": [],
    }
    insert_event(event)
    await event_bus.publish("market_event", event)
    return {"event": event}


@router.get("/stream")
async def stream():
    async def generator():
        async for message in event_bus.subscribe():
            yield message

    return StreamingResponse(generator(), media_type="text/event-stream")
