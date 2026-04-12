from __future__ import annotations

import json

import httpx

from ...config import get_settings
from .base import LLMResponse


class OpenAIProvider:
    base_url = "https://api.openai.com/v1/responses"

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
        system_text = context.get("system_prompt") or f"You are the {role} role in a trading workstation."
        user_text = json.dumps({"prompt": prompt, "context": context}, default=str)

        payload: dict = {
            "model": selected_model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
            ],
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        output_text = data.get("output_text", "")
        structured_payload: dict = {}
        if output_text:
            try:
                structured_payload = json.loads(output_text)
            except json.JSONDecodeError:
                structured_payload = {"text": output_text}

        usage = data.get("usage", {})
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)

        narrative = structured_payload.get("message_text") if isinstance(structured_payload, dict) else None
        if not narrative:
            narrative = output_text if output_text and not output_text.startswith("{") else f"{role} responded."

        if isinstance(structured_payload, dict) and "message_text" in structured_payload:
            structured_payload = {k: v for k, v in structured_payload.items() if k != "message_text"}

        return LLMResponse(
            text=narrative,
            structured_payload=structured_payload if isinstance(structured_payload, dict) else {"text": output_text},
            provider="openai",
            model=selected_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
