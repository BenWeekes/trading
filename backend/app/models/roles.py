from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RoleThread(BaseModel):
    id: str
    role: str
    symbol: str
    recommendation_id: str | None = None
    created_at: datetime


class RoleMessage(BaseModel):
    id: str
    role_thread_id: str
    role: str
    sender: str
    symbol: str | None = None
    recommendation_id: str | None = None
    message_text: str
    stance: str | None = None
    confidence: float | None = None
    structured_payload: dict = Field(default_factory=dict)
    provider: str | None = None
    model_used: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: datetime


class SharedSummary(BaseModel):
    id: str
    recommendation_id: str
    summary_text: str | None = None
    bull_case: str | None = None
    bear_case: str | None = None
    key_disagreement: str | None = None
    generated_by_model: str | None = None
    last_updated: datetime
