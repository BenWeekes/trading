"""Market Pulse — fast-polling gainers/losers/most-active for a live market view.

Polls 3 endpoints every 3 seconds = 60 calls/min (20% of 300 budget).
Returns ~100-120 unique stocks with price, change, volume.
"""
from __future__ import annotations

import asyncio
import time

from ..adapters.fmp import FMPClient
from ..services.event_bus import event_bus

_fmp = FMPClient()
_pulse_data: dict[str, dict] = {}  # symbol → latest data
_pulse_running = False
_pulse_calls = 0
_pulse_start = 0.0
_pulse_lock: asyncio.Lock | None = None
_last_refresh = 0.0


def _ensure_lock() -> asyncio.Lock:
    global _pulse_lock
    if _pulse_lock is None:
        _pulse_lock = asyncio.Lock()
    return _pulse_lock


def get_pulse_data() -> dict:
    """Return all market pulse data sorted by absolute change."""
    stocks = sorted(_pulse_data.values(), key=lambda s: abs(s.get("change_pct", 0)), reverse=True)
    elapsed = time.time() - _pulse_start if _pulse_start else 0
    return {
        "stocks": stocks,
        "count": len(stocks),
        "calls": _pulse_calls,
        "running_seconds": round(elapsed),
        "calls_per_min": round(_pulse_calls / (elapsed / 60), 1) if elapsed > 60 else _pulse_calls,
    }


async def _refresh_once() -> None:
    global _pulse_calls, _pulse_start, _last_refresh
    if not _pulse_start:
        _pulse_start = time.time()

    for name, method in [("gainers", _fmp.biggest_gainers), ("losers", _fmp.biggest_losers), ("active", _fmp.most_active)]:
        try:
            data = await method()
            _pulse_calls += 1
            if not data:
                continue

            for stock in data:
                symbol = stock.get("symbol")
                if not symbol:
                    continue
                price = stock.get("price", 0)
                change_pct = round(stock.get("changesPercentage", 0), 2)

                old = _pulse_data.get(symbol, {})
                old_price = old.get("price", 0)

                if old_price and price > old_price:
                    direction = "up"
                elif old_price and price < old_price:
                    direction = "down"
                else:
                    direction = "same"

                _pulse_data[symbol] = {
                    "symbol": symbol,
                    "name": (stock.get("name") or "")[:25],
                    "price": price,
                    "change": round(stock.get("change", 0), 2),
                    "change_pct": change_pct,
                    "volume": stock.get("volume"),
                    "direction": direction,
                    "category": name,
                    "updated": time.time(),
                }
        except Exception as e:
            print(f"[pulse] {name} error: {e}")

    _last_refresh = time.time()


async def ensure_pulse_data(max_age_seconds: float = 15.0) -> None:
    if _pulse_data and (time.time() - _last_refresh) <= max_age_seconds:
        return
    lock = _ensure_lock()
    async with lock:
        if _pulse_data and (time.time() - _last_refresh) <= max_age_seconds:
            return
        await _refresh_once()


async def run_pulse():
    """Background loop — polls gainers/losers/active every 3 seconds."""
    global _pulse_running, _pulse_calls, _pulse_start
    _pulse_running = True
    _pulse_calls = 0
    _pulse_start = time.time()

    print("[pulse] starting market pulse (3s interval, 3 endpoints)")

    while True:
        try:
            await _refresh_once()

            # Publish SSE with full update
            await event_bus.publish("market_pulse", {
                "count": len(_pulse_data),
                "top_gainers": [s["symbol"] for s in sorted(_pulse_data.values(), key=lambda x: x.get("change_pct", 0), reverse=True)[:5]],
                "top_losers": [s["symbol"] for s in sorted(_pulse_data.values(), key=lambda x: x.get("change_pct", 0))[:5]],
            })

        except asyncio.CancelledError:
            print("[pulse] cancelled")
            break
        except Exception as e:
            print(f"[pulse] error: {e}")

        await asyncio.sleep(3)
