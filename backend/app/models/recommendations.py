from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RecommendationStatus = Literal[
    "observing",
    "under_discussion",
    "draft_recommendation",
    "awaiting_user_feedback",
    "awaiting_user_approval",
    "approved",
    "rejected",
    "submitted",
    "partially_filled",
    "filled",
    "closed",
    "cancelled",
    "failed",
]


ActionType = Literal["BUY", "SELL", "SHORT", "COVER", "PASS"]


class TradeRecommendation(BaseModel):
    id: str
    symbol: str
    direction: ActionType | None = None
    status: RecommendationStatus = "observing"
    strategy_type: str = "PEAD"
    thesis: str | None = None
    entry_price: float | None = None
    entry_logic: str | None = None
    stop_price: float | None = None
    stop_logic: str | None = None
    target_price: float | None = None
    target_logic: str | None = None
    position_size_shares: float | None = None
    position_size_dollars: float | None = None
    time_horizon: str | None = None
    conviction: int | None = Field(default=None, ge=1, le=10)
    supporting_roles: list[str] = Field(default_factory=list)
    blocking_risks: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApprovalRecord(BaseModel):
    id: str
    recommendation_id: str
    status: Literal["approved", "rejected"]
    reviewer_notes: str | None = None
    requested_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
