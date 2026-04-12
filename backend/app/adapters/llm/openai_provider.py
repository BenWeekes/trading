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


def _is_responses_model(model: str) -> bool:
    """gpt-5+ models use the Responses API, older models use Chat Completions."""
    for prefix in ("gpt-5", "gpt-6", "gpt-7"):
        if model.startswith(prefix):
            return True
    return False


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
        user_text = _build_user_text(prompt, context)

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            if _is_responses_model(selected_model):
                data = await _call_responses_api(client, headers, selected_model, system_text, user_text, role, schema)
            else:
                data = await _call_chat_api(client, headers, selected_model, system_text, user_text, role, schema)

        return data


def _build_user_text(prompt: str, context: dict) -> str:
    parts = []
    if context.get("symbol"):
        parts.append(f"Symbol: {context['symbol']}")
    if context.get("event"):
        ev = context["event"]
        parts.append(f"Event: {ev.get('headline', '')} ({ev.get('type', '')})")
    if context.get("role_outputs"):
        for r, output in context["role_outputs"].items():
            parts.append(f"{r} says: {json.dumps(output, default=str)[:500]}")
    if context.get("user_message"):
        parts.append(f"User message: {context['user_message']}")
    if context.get("question_from_trader"):
        parts.append(f"Trader asks you: {context['question_from_trader']}")
    context_block = "\n".join(parts) if parts else ""
    return f"{context_block}\n\n{prompt}".strip()


async def _call_responses_api(client, headers, model, system_text, user_text, role, schema) -> LLMResponse:
    """For gpt-5+ models using /v1/responses."""
    payload = {
        "model": model,
        "instructions": system_text,
        "input": user_text,
        "max_output_tokens": 200,
    }
    if schema:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": f"{role}_response",
                "schema": schema,
                "strict": True,
            }
        }

    resp = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    output_text = data.get("output_text", "") or ""
    # Try to find text in output array if output_text is empty
    if not output_text and isinstance(data.get("output"), list):
        for item in data["output"]:
            if isinstance(item, dict) and item.get("type") == "message":
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        output_text = content.get("text", "")
                        break

    structured, narrative = _parse_output(output_text, role)
    usage = data.get("usage", {})

    return LLMResponse(
        text=narrative,
        structured_payload=structured,
        provider="openai",
        model=model,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        cost_usd=0.0,
    )


async def _call_chat_api(client, headers, model, system_text, user_text, role, schema) -> LLMResponse:
    """For gpt-4.x and older models using /v1/chat/completions."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 200,
        "temperature": 0.7,
    }
    if schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": f"{role}_response", "schema": schema, "strict": True},
        }

    resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    structured, narrative = _parse_output(content, role)
    usage = data.get("usage", {})

    return LLMResponse(
        text=narrative,
        structured_payload=structured,
        provider="openai",
        model=model,
        input_tokens=int(usage.get("prompt_tokens", 0)),
        output_tokens=int(usage.get("completion_tokens", 0)),
        cost_usd=0.0,
    )


def _parse_output(text: str, role: str) -> tuple[dict, str]:
    """Parse LLM output into structured payload and narrative text."""
    if not text:
        return {}, f"{role} had no response."

    # Try JSON first
    if text.strip().startswith("{"):
        try:
            payload = json.loads(text)
            narrative = (
                payload.pop("message_text", None)
                or payload.pop("narrative", None)
                or payload.pop("thesis_summary", None)
                or payload.pop("text", None)
                or text[:300]
            )
            return payload, narrative
        except json.JSONDecodeError:
            pass

    # Plain text response
    return {}, text
