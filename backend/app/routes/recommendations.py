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
    list_trades,
    update_trade,
    upsert_recommendation,
)
from ..adapters.alpaca import AlpacaAdapter
from ..roles import Orchestrator
from ..services.event_bus import event_bus
from ..services.state_machine import ensure_transition

alpaca = AlpacaAdapter()


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
    # Approve only from awaiting_user_approval — user must click Ready first
    if recommendation["status"] == "awaiting_user_feedback":
        raise HTTPException(status_code=400, detail="Recommendation is still in feedback. Click 'Ready for Approval' first.")
    ensure_transition(recommendation["status"], "approved")
    now = utcnow_iso()
    recommendation["status"] = "approved"
    recommendation["updated_at"] = now
    # Apply user-edited shares if provided
    if payload.get("shares"):
        recommendation["position_size_shares"] = float(payload["shares"])
        if recommendation.get("entry_price"):
            recommendation["position_size_dollars"] = float(payload["shares"]) * float(recommendation["entry_price"])
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
    # Allow reject from both feedback and approval states
    if recommendation["status"] not in ("awaiting_user_feedback", "awaiting_user_approval"):
        ensure_transition(recommendation["status"], "rejected")  # will raise if invalid
    if recommendation["status"] == "awaiting_user_feedback":
        # Skip to approval then reject
        recommendation["status"] = "awaiting_user_approval"
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


def _find_open_trade(symbol: str, direction_hint: str) -> dict | None:
    """Find an open trade to close for SELL/COVER actions."""
    open_trades = list_trades(open_only=True)
    for t in open_trades:
        if t["symbol"] != symbol:
            continue
        td = (t.get("direction") or "").upper()
        # SELL closes a long (BUY), COVER closes a short (SHORT)
        if direction_hint == "SELL" and td in ("BUY", "LONG"):
            return t
        if direction_hint == "COVER" and td in ("SHORT",):
            return t
    return None


@router.post("/{recommendation_id}/execute")
async def execute(recommendation_id: str):
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if recommendation["status"] != "approved":
        raise HTTPException(status_code=400, detail="Recommendation must be approved before execution")
    direction = (recommendation.get("direction") or "PASS").upper()
    if direction == "PASS":
        raise HTTPException(status_code=400, detail="PASS recommendations cannot be executed")

    ensure_transition(recommendation["status"], "submitted")
    now = utcnow_iso()
    recommendation["status"] = "submitted"
    recommendation["updated_at"] = now
    upsert_recommendation(recommendation)

    shares = recommendation.get("position_size_shares") or 0
    exec_price = recommendation.get("entry_price") or 0

    if direction in ("SELL", "COVER"):
        # Close or reduce an existing position
        existing = _find_open_trade(recommendation["symbol"], direction)
        if existing:
            existing_shares = float(existing.get("shares") or 0)
            close_shares = min(float(shares), existing_shares) if shares else existing_shares
            entry_price = float(existing.get("entry_price") or 0)
            existing_dir = (existing.get("direction") or "").upper()

            if existing_dir in ("SHORT",):
                pnl = (entry_price - exec_price) * close_shares
            else:
                pnl = (exec_price - entry_price) * close_shares

            if close_shares >= existing_shares:
                update_trade(existing["id"], closed_at=now, exit_price=exec_price, exit_reason="recommendation",
                             pnl_dollars=round(pnl, 2),
                             pnl_percent=round((pnl / (entry_price * existing_shares)) * 100, 2) if entry_price else 0,
                             risk_state="closed")
            else:
                update_trade(existing["id"], shares=existing_shares - close_shares)

            trade_id = existing["id"]
            action_label = "cover" if direction == "COVER" else "sell"
            insert_execution({
                "id": new_id("exec"), "recommendation_id": recommendation_id, "trade_id": trade_id,
                "order_type": f"paper_{action_label}", "submitted_at": now, "filled_at": now,
                "fill_price": exec_price, "fill_qty": close_shares,
                "broker_order_id": new_id("broker"),
                "broker_response": {"paper": True, "action": action_label, "direction": direction},
                "status": "filled",
            })
        else:
            raise HTTPException(status_code=400, detail=f"No open position to {direction.lower()} for {recommendation['symbol']}")
    else:
        # BUY or SHORT — open a new position
        # Try Alpaca first, fall back to paper simulation
        broker_order_id = new_id("broker")
        broker_response: dict = {"paper": True, "action": direction.lower()}

        if alpaca.is_configured():
            try:
                side = "buy" if direction == "BUY" else "sell"  # Alpaca: sell = short
                order = await alpaca.submit_order(
                    symbol=recommendation["symbol"],
                    qty=shares,
                    side=side,
                    take_profit=recommendation.get("target_price"),
                    stop_loss=recommendation.get("stop_price"),
                )
                broker_order_id = order.get("id", broker_order_id)
                broker_response = order
                # Use fill price from order if available
                if order.get("filled_avg_price"):
                    exec_price = float(order["filled_avg_price"])
            except Exception as exc:
                broker_response = {"error": str(exc), "paper_fallback": True}

        trade_id = new_id("trade")
        insert_trade({
            "id": trade_id, "recommendation_id": recommendation_id,
            "symbol": recommendation["symbol"], "direction": direction,
            "entry_price": exec_price, "current_price": exec_price,
            "shares": shares, "unrealized_pnl": 0.0,
            "stop_price": recommendation.get("stop_price"),
            "target_price": recommendation.get("target_price"),
            "exit_price": None, "exit_reason": None,
            "pnl_dollars": None, "pnl_percent": None,
            "risk_state": "normal", "broker_order_id": broker_order_id,
            "opened_at": now, "closed_at": None,
        })
        insert_execution({
            "id": new_id("exec"), "recommendation_id": recommendation_id, "trade_id": trade_id,
            "order_type": f"paper_{direction.lower()}", "submitted_at": now, "filled_at": now,
            "fill_price": exec_price, "fill_qty": shares,
            "broker_order_id": broker_order_id,
            "broker_response": broker_response,
            "status": "filled",
        })

    ensure_transition(recommendation["status"], "filled")
    recommendation["status"] = "filled"
    recommendation["updated_at"] = utcnow_iso()
    upsert_recommendation(recommendation)
    await event_bus.publish("recommendation_update", recommendation)
    await event_bus.publish("position_update", {
        "symbol": recommendation["symbol"], "action": direction.lower(),
        "direction": direction,
    })
    return {"recommendation": recommendation, "trade_id": trade_id}
