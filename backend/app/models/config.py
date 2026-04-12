from __future__ import annotations

from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    role_name: str
    provider: str = "mock"
    default_model: str
    escalation_model: str | None = None
    system_prompt_version: str = "v1"
    demo_prompt_version: str = "demo_v1"
    tool_permissions: list[str] = Field(default_factory=list)
    cost_budget_per_day: float = 5.0
    max_tokens_per_call: int = 4096


class AppConfig(BaseModel):
    app_mode: str
    event_mode: str
    demo_mode: bool
    backend_port: int
    frontend_port: int
