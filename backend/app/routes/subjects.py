from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db.repositories import (
    get_discussion_subject,
    get_event,
    get_recommendation,
    get_summary,
    get_trade,
    list_discussion_subjects,
    list_role_messages,
)
from ..roles import Orchestrator
from ..services.discussion_subjects import (
    ensure_event_subject,
    ensure_position_subject,
    ensure_recommendation_subject,
)


router = APIRouter(prefix="/api/subjects", tags=["subjects"])
orchestrator = Orchestrator()


@router.get("")
async def subjects(limit: int = Query(default=50, le=200), subject_type: str | None = None):
    return {"subjects": list_discussion_subjects(limit=limit, subject_type=subject_type)}


@router.post("/resolve")
async def resolve_subject(payload: dict):
    recommendation_id = payload.get("recommendation_id")
    event_id = payload.get("event_id")
    trade_id = payload.get("trade_id")

    subject = None
    if recommendation_id:
        subject = ensure_recommendation_subject(recommendation_id)
    elif event_id:
        linked_recommendation_id = payload.get("linked_recommendation_id")
        subject = ensure_event_subject(event_id, recommendation_id=linked_recommendation_id)
    elif trade_id:
        subject = ensure_position_subject(trade_id)
    else:
        raise HTTPException(status_code=400, detail="recommendation_id, event_id, or trade_id is required")

    if not subject:
        raise HTTPException(status_code=404, detail="Subject could not be resolved")
    return await subject_detail(subject["id"])


@router.get("/{subject_id}")
async def subject_detail(subject_id: str):
    subject = get_discussion_subject(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Discussion subject not found")

    recommendation = get_recommendation(subject["recommendation_id"]) if subject.get("recommendation_id") else None
    event = get_event(subject["event_id"]) if subject.get("event_id") else None
    trade = get_trade(subject["trade_id"]) if subject.get("trade_id") else None
    summary = get_summary(subject["recommendation_id"]) if subject.get("recommendation_id") else None

    timeline = []
    if subject.get("recommendation_id"):
        timeline = list_role_messages(recommendation_id=subject["recommendation_id"])
    else:
        timeline = list_role_messages(discussion_subject_id=subject["id"])

    return {
        "subject": subject,
        "recommendation": recommendation,
        "event": event,
        "trade": trade,
        "summary": summary,
        "timeline": timeline,
    }


@router.post("/{subject_id}/discuss")
async def discuss_subject(subject_id: str, payload: dict):
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    subject = get_discussion_subject(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Discussion subject not found")
    return await orchestrator.subject_chat(subject_id, message)
