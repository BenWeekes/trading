from __future__ import annotations

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


@router.post("/scan")
async def scan():
    result = await run_scan()
    enriched = []
    portfolio = get_portfolio_summary()
    for item in result["results"]:
        event = item["event"]
        recommendation = item["recommendation"]
        await event_bus.publish("market_event", event)
        analyzed = await orchestrator.analyze_event(recommendation, event, portfolio)
        enriched.append({"event": event, "recommendation": analyzed, "filters": item["filters"]})
    return {"results": enriched}


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

    # Only run full analysis if the rec is in an analysable state
    if recommendation["status"] in ("observing", "under_discussion"):
        analyzed = await orchestrator.analyze_event(recommendation, event, get_portfolio_summary())
        return {"event": event, "recommendation": analyzed}

    return {"event": event, "recommendation": recommendation}
