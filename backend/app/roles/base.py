from __future__ import annotations

from ..adapters.llm import get_provider
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import create_role_thread, get_role_config, get_role_thread, insert_cost, insert_role_message


class BaseRole:
    role_name = "base"
    response_schema: dict | None = None

    async def ensure_thread(self, symbol: str, recommendation_id: str) -> dict:
        existing = get_role_thread(self.role_name, recommendation_id)
        if existing:
            return existing
        thread = {
            "id": new_id("thread"),
            "role": self.role_name,
            "symbol": symbol,
            "recommendation_id": recommendation_id,
            "created_at": utcnow_iso(),
        }
        create_role_thread(thread)
        return thread

    def _config(self) -> dict:
        from ..config import get_settings
        settings = get_settings()
        default_provider = "openai" if settings.openai_api_key else "mock"
        default_model = settings.openai_model if settings.openai_api_key else "mock-v1"
        return get_role_config(self.role_name) or {
            "role_name": self.role_name,
            "provider": default_provider,
            "default_model": default_model,
            "escalation_model": None,
            "tool_permissions": [],
            "cost_budget_per_day": 5.0,
            "max_tokens_per_call": 4096,
        }

    async def respond(self, *, symbol: str, recommendation_id: str, prompt: str, context: dict, sender: str) -> dict:
        thread = await self.ensure_thread(symbol, recommendation_id)
        config = self._config()
        provider = get_provider(config["provider"])
        result = await provider.complete(
            role=self.role_name,
            prompt=prompt,
            context=context,
            model=config["default_model"],
            schema=self.response_schema,
        )
        message = {
            "id": new_id("msg"),
            "role_thread_id": thread["id"],
            "role": self.role_name,
            "sender": sender,
            "symbol": symbol,
            "recommendation_id": recommendation_id,
            "message_text": result.text,
            "structured_payload": result.structured_payload,
            "stance": context.get("stance"),
            "confidence": result.structured_payload.get("confidence"),
            "provider": result.provider,
            "model_used": result.model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": result.cost_usd,
            "timestamp": utcnow_iso(),
        }
        insert_role_message(message)
        insert_cost(
            {
                "id": new_id("cost"),
                "role": self.role_name,
                "recommendation_id": recommendation_id,
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
                "timestamp": message["timestamp"],
            }
        )
        return message
