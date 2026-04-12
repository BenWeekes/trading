from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..db.repositories import get_recommendation, list_recommendations
from ..db.helpers import new_id, utcnow_iso
from ..roles import Orchestrator
from ..services.event_bus import event_bus
from ..services.position_sizing import calculate_position
from ..services.portfolio import get_portfolio_summary
from ..services.scanner import run_scan
import random


router = APIRouter(prefix="/api", tags=["scanner"])
orchestrator = Orchestrator()

# Track background analysis tasks
_analysis_tasks: list[asyncio.Task] = []


async def _analyze_in_background(recommendation: dict, event: dict, portfolio: dict) -> None:
    """Run role analysis for a single stock in the background."""
    try:
        await orchestrator.analyze_event(recommendation, event, portfolio)
    except Exception as exc:
        print(f"[scan] background analysis failed for {recommendation.get('symbol')}: {exc}")
        await event_bus.publish("system", {"type": "analysis_error", "symbol": recommendation.get("symbol"), "error": str(exc)})


@router.post("/scan")
async def scan():
    result = await run_scan()
    portfolio = get_portfolio_summary()

    # Publish events immediately so they appear in the UI
    for item in result["results"]:
        await event_bus.publish("market_event", item["event"])

    # Launch analysis for each stock in the background — don't block the response
    for item in result["results"]:
        rec = item["recommendation"]
        if rec["status"] in ("observing",):
            task = asyncio.create_task(_analyze_in_background(rec, item["event"], portfolio))
            _analysis_tasks.append(task)
            # Clean up finished tasks
            _analysis_tasks[:] = [t for t in _analysis_tasks if not t.done()]

    return {
        "results": [{"event": item["event"], "recommendation": item["recommendation"], "filters": item["filters"]} for item in result["results"]],
        "analysis": "running in background — results will appear via SSE as each stock completes",
    }


@router.post("/roles/{role}/analyze")
async def analyze_role(role: str, payload: dict):
    recommendation_id = payload.get("recommendation_id")
    if not recommendation_id:
        raise HTTPException(status_code=400, detail="recommendation_id is required")
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    message = await orchestrator.user_chat(role, recommendation_id, payload.get("message") or f"Analyze {recommendation['symbol']}")
    return message


@router.get("/candidates")
async def candidates():
    return {"recommendations": list_recommendations(limit=50)}


@router.post("/demo/random-event")
async def random_event_flow():
    symbol = random.choice(["NVDA", "AAPL", "MSFT", "META", "AMD", "PLTR", "CRM"])
    event_type = random.choice(["earnings", "news", "price_alert"])
    headlines = {
        "earnings": [
            f"{symbol} beats EPS by {random.randint(5,25)}% on strong revenue",
            f"{symbol} misses estimates, lowers guidance",
            f"{symbol} reports in-line quarter but raises full-year outlook",
        ],
        "news": [
            f"{symbol} announces major partnership deal",
            f"Analyst upgrades {symbol} to outperform with new price target",
            f"{symbol} faces regulatory scrutiny, shares volatile",
        ],
        "price_alert": [
            f"{symbol} surges {random.randint(3,12)}% on heavy volume",
            f"{symbol} breaks below 50-day moving average",
            f"{symbol} hits new 52-week high on momentum",
        ],
    }
    event = {
        "id": new_id("evt"),
        "type": event_type,
        "symbol": symbol,
        "headline": random.choice(headlines[event_type]),
        "body_excerpt": f"Demo {event_type.replace('_', ' ')} event for testing the AI trading desk.",
        "source": "Demo",
        "timestamp": utcnow_iso(),
        "importance": random.randint(3, 5),
        "linked_recommendation_ids": [],
    }

    # Check if we already have a recommendation for this symbol — reuse it
    from ..db.repositories import insert_event, list_recommendations, upsert_recommendation

    existing_rec = next((r for r in list_recommendations(limit=50) if r["symbol"] == symbol and r["status"] not in ("closed", "rejected", "cancelled")), None)

    if existing_rec:
        recommendation = existing_rec
    else:
        sizing = calculate_position(100 + random.randint(0, 40), 100000.0)
        recommendation = {
            "id": new_id("rec"),
            "symbol": symbol,
            "direction": None,
            "status": "observing",
            "strategy_type": "DEMO",
            "thesis": None,
            "entry_price": sizing.get("entry_price"),
            "entry_logic": sizing.get("entry_logic"),
            "stop_price": sizing.get("stop_price"),
            "stop_logic": sizing.get("stop_logic"),
            "target_price": sizing.get("target_price"),
            "target_logic": sizing.get("target_logic"),
            "position_size_shares": sizing.get("position_size_shares"),
            "position_size_dollars": sizing.get("position_size_dollars"),
            "time_horizon": "demo",
            "conviction": None,
            "supporting_roles": [],
            "blocking_risks": [],
            "created_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
        }
        upsert_recommendation(recommendation)

    insert_event(event)
    await event_bus.publish("market_event", event)

    # Run analysis in background so the UI gets the event immediately
    if recommendation["status"] in ("observing", "under_discussion"):
        task = asyncio.create_task(_analyze_in_background(recommendation, event, get_portfolio_summary()))
        _analysis_tasks.append(task)
        _analysis_tasks[:] = [t for t in _analysis_tasks if not t.done()]

    return {"event": event, "recommendation": recommendation}
