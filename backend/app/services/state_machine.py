from __future__ import annotations

from ..models.recommendations import RecommendationStatus


ALLOWED_TRANSITIONS: dict[RecommendationStatus, set[RecommendationStatus]] = {
    "observing": {"under_discussion", "cancelled"},
    "under_discussion": {"draft_recommendation", "awaiting_user_feedback", "cancelled"},
    "draft_recommendation": {"awaiting_user_feedback", "awaiting_user_approval", "cancelled"},
    "awaiting_user_feedback": {"draft_recommendation", "awaiting_user_approval", "cancelled"},
    "awaiting_user_approval": {"approved", "rejected", "draft_recommendation"},
    "approved": {"submitted", "cancelled"},
    "rejected": set(),
    "submitted": {"partially_filled", "filled", "failed", "cancelled"},
    "partially_filled": {"filled", "closed", "failed"},
    "filled": {"closed"},
    "closed": set(),
    "cancelled": set(),
    "failed": {"draft_recommendation", "cancelled"},
}


def ensure_transition(current: RecommendationStatus, target: RecommendationStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid recommendation transition: {current} -> {target}")
