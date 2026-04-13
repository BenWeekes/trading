from __future__ import annotations

import httpx

from ..config import get_settings


class AlpacaAdapter:
    """Alpaca paper trading adapter using REST API."""

    def _headers(self) -> dict:
        s = get_settings()
        return {
            "APCA-API-KEY-ID": s.alpaca_api_key,
            "APCA-API-SECRET-KEY": s.alpaca_secret_key,
            "Content-Type": "application/json",
        }

    def _base(self) -> str:
        return get_settings().alpaca_base_url.rstrip("/")

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.alpaca_api_key and s.alpaca_secret_key)

    async def get_account(self) -> dict:
        if not self.is_configured():
            return {"error": "alpaca not configured"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self._base()}/v2/account", headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def get_positions(self) -> list[dict]:
        if not self.is_configured():
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self._base()}/v2/positions", headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def submit_order(self, *, symbol: str, qty: float, side: str, order_type: str = "market",
                           time_in_force: str = "day", take_profit: float | None = None,
                           stop_loss: float | None = None) -> dict:
        """Submit a paper order to Alpaca. Supports bracket orders."""
        if not self.is_configured():
            return {"error": "alpaca not configured", "paper_fallback": True}

        body: dict = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }

        # Bracket order if both targets provided
        if take_profit and stop_loss:
            body["order_class"] = "bracket"
            body["take_profit"] = {"limit_price": str(take_profit)}
            body["stop_loss"] = {"stop_price": str(stop_loss)}

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self._base()}/v2/orders", headers=self._headers(), json=body)
            r.raise_for_status()
            return r.json()

    async def close_position(self, symbol: str, qty: float | None = None) -> dict:
        """Close or reduce a position."""
        if not self.is_configured():
            return {"error": "alpaca not configured", "paper_fallback": True}

        url = f"{self._base()}/v2/positions/{symbol}"
        params = {}
        if qty:
            params["qty"] = str(qty)

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.delete(url, headers=self._headers(), params=params)
            r.raise_for_status()
            return r.json()
