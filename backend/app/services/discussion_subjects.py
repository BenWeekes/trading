from __future__ import annotations

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    find_discussion_subject,
    get_event,
    get_recommendation,
    get_trade,
    upsert_discussion_subject,
)


def ensure_recommendation_subject(recommendation_id: str) -> dict | None:
    recommendation = get_recommendation(recommendation_id)
    if not recommendation:
        return None
    existing = find_discussion_subject(
        subject_type="recommendation",
        recommendation_id=recommendation_id,
        symbol=recommendation.get("symbol"),
    )
    if existing:
        return existing
    now = utcnow_iso()
    subject = {
        "id": new_id("subj"),
        "subject_type": "recommendation",
        "symbol": recommendation.get("symbol"),
        "event_id": None,
        "recommendation_id": recommendation_id,
        "trade_id": None,
        "headline": f"{recommendation['symbol']} recommendation",
        "summary": recommendation.get("thesis"),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    upsert_discussion_subject(subject)
    return subject


def ensure_event_subject(event_id: str, recommendation_id: str | None = None) -> dict | None:
    event = get_event(event_id)
    if not event:
        return None
    existing = find_discussion_subject(
        subject_type=event["type"],
        event_id=event_id,
        recommendation_id=recommendation_id,
        symbol=event.get("symbol"),
    )
    if existing:
        return existing
    now = utcnow_iso()
    subject = {
        "id": new_id("subj"),
        "subject_type": event["type"],
        "symbol": event.get("symbol"),
        "event_id": event_id,
        "recommendation_id": recommendation_id,
        "trade_id": None,
        "headline": event.get("headline"),
        "summary": event.get("body_excerpt"),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    upsert_discussion_subject(subject)
    return subject


def ensure_position_subject(trade_id: str) -> dict | None:
    trade = get_trade(trade_id)
    if not trade:
        return None
    existing = find_discussion_subject(
        subject_type="position",
        trade_id=trade_id,
        recommendation_id=trade.get("recommendation_id"),
        symbol=trade.get("symbol"),
    )
    if existing:
        return existing
    now = utcnow_iso()
    subject = {
        "id": new_id("subj"),
        "subject_type": "position",
        "symbol": trade.get("symbol"),
        "event_id": None,
        "recommendation_id": trade.get("recommendation_id"),
        "trade_id": trade_id,
        "headline": f"{trade.get('symbol')} position",
        "summary": f"{trade.get('direction', '')} {trade.get('shares', 0)} shares",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    upsert_discussion_subject(subject)
    return subject
