from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from ..config import get_settings


class FMPClient:
    base_url = "https://financialmodelingprep.com/stable"

    async def _get(self, endpoint: str, params: dict | None = None):
        settings = get_settings()
        if not settings.fmp_api_key:
            return None
        query = dict(params or {})
        query["apikey"] = settings.fmp_api_key
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=query)
            response.raise_for_status()
            return response.json()

    async def earnings_calendar(self) -> list[dict]:
        today = datetime.utcnow().date()
        payload = await self._get(
            "earnings-calendar",
            {"from": (today - timedelta(days=3)).isoformat(), "to": (today + timedelta(days=1)).isoformat()},
        )
        return payload or []

    async def quote(self, symbol: str) -> dict:
        payload = await self._get("quote", {"symbol": symbol})
        if isinstance(payload, list):
            return payload[0] if payload else {}
        return payload or {}

    async def news(self, symbol: str, limit: int = 5) -> list[dict]:
        payload = await self._get("news/stock-latest", {"symbol": symbol, "limit": limit})
        return payload or []

    async def price_target(self, symbol: str) -> dict:
        payload = await self._get("price-target-consensus", {"symbol": symbol})
        if isinstance(payload, list):
            return payload[0] if payload else {}
        return payload or {}
