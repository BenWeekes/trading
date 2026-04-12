from __future__ import annotations

from ..config import get_settings


class AlpacaAdapter:
    async def submit_paper_order(self, recommendation: dict) -> dict:
        settings = get_settings()
        return {
            "paper": True,
            "mode": settings.app_mode,
            "symbol": recommendation["symbol"],
            "direction": recommendation.get("direction"),
            "submitted": True,
        }
