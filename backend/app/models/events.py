from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "earnings",
    "news",
    "price_alert",
    "macro",
    "position_change",
    "recommendation_update",
    "internal_alert",
]


class IncomingEvent(BaseModel):
    id: str
    type: EventType
    symbol: str | None = None
    headline: str
    body_excerpt: str | None = None
    source: str | None = None
    timestamp: datetime
    importance: int = Field(default=3, ge=1, le=5)
    linked_recommendation_ids: list[str] = Field(default_factory=list)
