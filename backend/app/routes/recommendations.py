from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    get_recommendation,
    get_summary,
    insert_approval,
    insert_execution,
    insert_trade,
    list_approvals,
    list_recommendations,
    upsert_recommendation,
)
from ..roles import Orchestrator
from ..services.event_bus import event_bus
from ..services.state_machine import ensure_transition


router = APIRouter(prefix="/api/recs", tags=["recommendations"])
orchestrator = Orchestrator()


@router.get("")
async def recommendations(status: str | None = Query(default=None), limit: int = 20):
    return {"recommendations": list_recommendations(limit=limit, status=status)}


@router.get("/{recommendation_id}")
async def recommendation_detail(recommendation_id: str):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {
        "recommendation": recommendation,
        "summary": get_summary(recommendation_id),
        "timeline": orchestrator.timeline(recommendation_id),
        "approvals": list_approvals(recommendation_id),
    }


@router.get("/{recommendation_id}/timeline")
async def recommendation_timeline(recommendation_id: str):
    return {"timeline": orchestrator.timeline(recommendation_id)}


@router.post("/{recommendation_id}/refresh")
async def recommendation_refresh(recommendation_id: str):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    ensure_transition(recommendation["status"], "awaiting_user_feedback")
    recommendation["status"] = "awaiting_user_feedback"
    recommendation["updated_at"] = utcnow_iso()
    upsert_recommendation(recommendation)
    await event_bus.publish("recommendation_update", recommendation)
    return recommendation


@router.post("/{recommendation_id}/discuss")
async def discuss(recommendation_id: str, payload: dict):
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    return await orchestrator.route_group_chat(recommendation_id, message)


@router.post("/{recommendation_id}/approve")
async def approve(recommendation_id: str, payload: dict):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    ensure_transition(recommendation["status"], "approved")
    now = utcnow_iso()
    recommendation["status"] = "approved"
    recommendation["updated_at"] = now
    upsert_recommendation(recommendation)
    insert_approval(
        {
            "id": new_id("approval"),
            "recommendation_id": recommendation_id,
            "status": "approved",
            "reviewer_notes": payload.get("notes"),
            "requested_at": now,
            "approved_at": now,
            "rejected_at": None,
        }
    )
    await event_bus.publish("recommendation_update", recommendation)
    return recommendation


@router.post("/{recommendation_id}/ready")
async def mark_ready_for_approval(recommendation_id: str):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    ensure_transition(recommendation["status"], "awaiting_user_approval")
    recommendation["status"] = "awaiting_user_approval"
    recommendation["updated_at"] = utcnow_iso()
    upsert_recommendation(recommendation)
    await event_bus.publish("recommendation_update", recommendation)
    return recommendation


@router.post("/{recommendation_id}/reject")
async def reject(recommendation_id: str, payload: dict):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    ensure_transition(recommendation["status"], "rejected")
    now = utcnow_iso()
    recommendation["status"] = "rejected"
    recommendation["updated_at"] = now
    upsert_recommendation(recommendation)
    insert_approval(
        {
            "id": new_id("approval"),
            "recommendation_id": recommendation_id,
            "status": "rejected",
            "reviewer_notes": payload.get("notes") or payload.get("reason"),
            "requested_at": now,
            "approved_at": None,
            "rejected_at": now,
        }
    )
    await event_bus.publish("recommendation_update", recommendation)
    return recommendation


@router.post("/{recommendation_id}/execute")
async def execute(recommendation_id: str):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if recommendation["status"] != "approved":
        raise HTTPException(status_code=400, detail="Recommendation must be approved before execution")
    if recommendation.get("direction") == "PASS":
        raise HTTPException(status_code=400, detail="PASS recommendations cannot be executed")
    ensure_transition(recommendation["status"], "submitted")
    now = utcnow_iso()
    recommendation["status"] = "submitted"
    recommendation["updated_at"] = now
    upsert_recommendation(recommendation)

    trade_id = new_id("trade")
    insert_trade(
        {
            "id": trade_id,
            "recommendation_id": recommendation_id,
            "symbol": recommendation["symbol"],
            "direction": recommendation.get("direction") or "PASS",
            "entry_price": recommendation.get("entry_price"),
            "current_price": recommendation.get("entry_price"),
            "shares": recommendation.get("position_size_shares"),
            "unrealized_pnl": 0.0,
            "stop_price": recommendation.get("stop_price"),
            "target_price": recommendation.get("target_price"),
            "exit_price": None,
            "exit_reason": None,
            "pnl_dollars": None,
            "pnl_percent": None,
            "risk_state": "normal",
            "broker_order_id": new_id("broker"),
            "opened_at": now,
            "closed_at": None,
        }
    )
    insert_execution(
        {
            "id": new_id("exec"),
            "recommendation_id": recommendation_id,
            "trade_id": trade_id,
            "order_type": "paper",
            "submitted_at": now,
            "filled_at": now,
            "fill_price": recommendation.get("entry_price"),
            "fill_qty": recommendation.get("position_size_shares"),
            "broker_order_id": new_id("broker"),
            "broker_response": {"paper": True},
            "status": "filled",
        }
    )

    ensure_transition(recommendation["status"], "filled")
    recommendation["status"] = "filled"
    recommendation["updated_at"] = utcnow_iso()
    upsert_recommendation(recommendation)
    await event_bus.publish("recommendation_update", recommendation)
    await event_bus.publish(
        "position_update",
        {
            "symbol": recommendation["symbol"],
            "current_price": recommendation.get("entry_price"),
            "unrealized_pnl": 0.0,
            "direction": recommendation.get("direction"),
        },
    )
    return {"recommendation": recommendation, "trade_id": trade_id}
