from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMResponse:
    text: str
    structured_payload: dict = field(default_factory=dict)
    provider: str = "mock"
    model: str = "mock-v1"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        role: str,
        prompt: str,
        context: dict,
        model: str | None = None,
        schema: dict | None = None,
    ) -> LLMResponse: ...
