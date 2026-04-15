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

    # ── Single symbol ──

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

    async def earnings_calendar(self) -> list[dict]:
        today = datetime.utcnow().date()
        payload = await self._get(
            "earnings-calendar",
            {"from": (today - timedelta(days=3)).isoformat(), "to": (today + timedelta(days=1)).isoformat()},
        )
        return payload or []

    # ── Batch / Bulk (1 call, many results) ──

    async def batch_quote(self, symbols: list[str]) -> list[dict]:
        """Get quotes for multiple symbols in a single API call."""
        if not symbols:
            return []
        payload = await self._get("batch-quote", {"symbol": ",".join(symbols)})
        return payload if isinstance(payload, list) else []

    async def market_news(self, limit: int = 20) -> list[dict]:
        """Get latest stock news across all stocks (no symbol filter)."""
        payload = await self._get("stock-news", {"limit": limit})
        return payload if isinstance(payload, list) else []

    async def general_news(self, limit: int = 10) -> list[dict]:
        """Get general market news."""
        payload = await self._get("general-news", {"limit": limit})
        return payload if isinstance(payload, list) else []

    async def biggest_gainers(self) -> list[dict]:
        """Top gaining stocks today — 1 call, no symbol needed."""
        payload = await self._get("biggest-gainers")
        return payload if isinstance(payload, list) else []

    async def biggest_losers(self) -> list[dict]:
        """Top losing stocks today — 1 call, no symbol needed."""
        payload = await self._get("biggest-losers")
        return payload if isinstance(payload, list) else []

    async def most_active(self) -> list[dict]:
        """Most actively traded stocks — 1 call, no symbol needed."""
        payload = await self._get("most-actives")
        return payload if isinstance(payload, list) else []

    async def stock_screener(self, **filters) -> list[dict]:
        """Screener — filter by market cap, price, volume, sector, etc."""
        payload = await self._get("search-company-screener", filters)
        return payload if isinstance(payload, list) else []

    async def upcoming_earnings(self, days_ahead: int = 7) -> list[dict]:
        """Earnings calendar looking forward."""
        today = datetime.utcnow().date()
        payload = await self._get(
            "earnings-calendar",
            {"from": today.isoformat(), "to": (today + timedelta(days=days_ahead)).isoformat()},
        )
        return payload or []
