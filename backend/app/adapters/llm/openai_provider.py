from __future__ import annotations

import json
from pathlib import Path

import httpx

from ...config import get_settings
from .base import LLMResponse

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "roles" / "prompts"


def _load_system_prompt(role: str) -> str:
    path = PROMPTS_DIR / f"{role}_v1.md"
    if path.exists():
        return path.read_text().strip()
    return f"You are the {role} role on an AI trading desk. Be concise and specific."


class OpenAIProvider:

    async def complete(
        self,
        *,
        role: str,
        prompt: str,
        context: dict,
        model: str | None = None,
        schema: dict | None = None,
    ) -> LLMResponse:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        selected_model = model or settings.openai_model
        system_text = context.get("system_prompt") or _load_system_prompt(role)

        # Build user message with context
        context_parts = []
        if context.get("symbol"):
            context_parts.append(f"Symbol: {context['symbol']}")
        if context.get("event"):
            ev = context["event"]
            context_parts.append(f"Event: {ev.get('headline', '')} ({ev.get('type', '')})")
        if context.get("role_outputs"):
            for r, output in context["role_outputs"].items():
                context_parts.append(f"{r} says: {json.dumps(output, default=str)[:500]}")
        if context.get("user_message"):
            context_parts.append(f"User message: {context['user_message']}")
        if context.get("question_from_trader"):
            context_parts.append(f"Trader asks you: {context['question_from_trader']}")

        context_block = "\n".join(context_parts) if context_parts else ""
        user_text = f"{context_block}\n\n{prompt}".strip()

        # Use chat completions API (standard, works with all models)
        payload: dict = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{role}_response",
                    "schema": schema,
                    "strict": True,
                },
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract response
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Try to parse structured JSON from content
        structured_payload: dict = {}
        narrative = content
        if content.strip().startswith("{"):
            try:
                structured_payload = json.loads(content)
                # If structured, extract narrative from a known field
                narrative = (
                    structured_payload.pop("message_text", None)
                    or structured_payload.pop("narrative", None)
                    or structured_payload.pop("thesis_summary", None)
                    or structured_payload.pop("text", None)
                    or content[:200]
                )
            except json.JSONDecodeError:
                pass

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            text=narrative,
            structured_payload=structured_payload,
            provider="openai",
            model=selected_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
