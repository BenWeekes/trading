"""Market data poller — background loop pulling FMP data on intervals.

Budget: 300 calls/min. Typical usage: ~15-30 calls/min (5-10%).
Worst case (15 positions, 5 recs): ~72 calls/min (24%).

Tested endpoints on starter plan:
- quote (individual): works
- batch-quote: 402 (premium only)
- news/stock-latest: works
- news/general-latest: works
- biggest-gainers/losers/most-actives: work
- earnings-calendar: works
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime

from ..adapters.fmp import FMPClient
from ..config import get_settings
from ..db.helpers import new_id
from ..db.repositories import insert_event, list_recommendations, list_trades, update_trade
from ..services.event_bus import event_bus

_fmp = FMPClient()

def _get_watched_symbols() -> list[str]:
    """Symbols we actually care about: positions + recommendations + SPY."""
    symbols = {"SPY"}  # always track regime
    for t in list_trades(open_only=True):
        if t.get("symbol"):
            symbols.add(t["symbol"])
    for r in list_recommendations(limit=20):
        if r.get("symbol") and r["status"] not in ("closed", "rejected", "cancelled"):
            symbols.add(r["symbol"])
    return list(symbols)

# Track API call count for monitoring
_call_count = 0
_call_count_reset = time.time()
_last_poll_summary: dict = {}
_ticker_prices: dict[str, dict] = {}  # cache of latest prices


def get_poll_stats() -> dict:
    elapsed = time.time() - _call_count_reset
    return {
        "total_calls": _call_count,
        "elapsed_minutes": round(elapsed / 60, 1),
        "calls_per_minute": round(_call_count / (elapsed / 60), 1) if elapsed > 60 else _call_count,
        "budget_pct": round((_call_count / (elapsed / 60)) / 300 * 100, 1) if elapsed > 60 else 0,
        "last_poll": _last_poll_summary,
    }


async def _safe_call(coro, label: str):
    """Call FMP and track count. Returns result or None on error."""
    global _call_count
    try:
        result = await coro
        _call_count += 1
        return result
    except Exception as e:
        print(f"[poller] {label} error: {e}")
        return None


async def poll_ticker_batch(batch: list[str]):
    """Poll watched symbols. Updates prices + position P&L."""
    positions = list_trades(open_only=True)
    position_map = {}
    for t in positions:
        position_map.setdefault(t["symbol"], []).append(t)

    for symbol in batch:
        quote = await _safe_call(_fmp.quote(symbol), f"quote:{symbol}")
        if not quote or not quote.get("price"):
            continue
        price = float(quote["price"])
        prev = float(quote.get("previousClose") or price)
        change = round(price - prev, 2)
        change_pct = round(quote.get("changesPercentage", 0), 2)
        volume = quote.get("volume")

        old = _ticker_prices.get(symbol, {})
        _ticker_prices[symbol] = {
            "price": price, "change": change, "change_pct": change_pct,
            "volume": volume, "prev_close": prev,
            "day_high": quote.get("dayHigh"), "day_low": quote.get("dayLow"),
        }

        # Update P&L on open positions
        for t in position_map.get(symbol, []):
            entry = float(t.get("entry_price") or price)
            shares = float(t.get("shares") or 0)
            direction = (t.get("direction") or "BUY").upper()
            pnl = (price - entry) * shares if direction != "SHORT" else (entry - price) * shares
            update_trade(t["id"], current_price=price, unrealized_pnl=round(pnl, 2))

        await event_bus.publish("price_update", {
            "symbol": symbol,
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "prev_price": old.get("price"),
        })


def get_ticker_prices() -> dict:
    """Return all cached ticker prices."""
    return dict(_ticker_prices)




async def poll_stock_news():
    """Every 2 min — latest stock news across all markets."""
    news = await _safe_call(_fmp.news("", limit=10), "stock-news")
    if not news:
        return
    for n in news[:5]:
        event = {
            "id": new_id("evt"),
            "type": "news",
            "symbol": n.get("symbol"),
            "headline": n.get("title", "")[:120],
            "body_excerpt": (n.get("text") or "")[:200],
            "source": n.get("site") or n.get("source"),
            "timestamp": n.get("publishedDate") or datetime.utcnow().isoformat(),
            "importance": 3,
            "linked_recommendation_ids": [],
        }
        try:
            insert_event(event)
        except Exception:
            pass  # duplicate
        await event_bus.publish("market_event", event)


async def poll_general_news():
    """Every 5 min — general market news."""
    raw = await _safe_call(_fmp._get("news/general-latest", {"limit": 5}), "general-news")
    if not raw or not isinstance(raw, list):
        return
    for n in raw[:3]:
        event = {
            "id": new_id("evt"),
            "type": "macro",
            "symbol": None,
            "headline": n.get("title", "")[:120],
            "body_excerpt": "",
            "source": n.get("site") or n.get("source"),
            "timestamp": n.get("publishedDate") or datetime.utcnow().isoformat(),
            "importance": 2,
            "linked_recommendation_ids": [],
        }
        try:
            insert_event(event)
        except Exception:
            pass
        await event_bus.publish("market_event", event)


async def poll_market_movers():
    """Every 5 min — gainers, losers, most active."""
    for name, method in [("gainers", _fmp.biggest_gainers), ("losers", _fmp.biggest_losers), ("most_active", _fmp.most_active)]:
        data = await _safe_call(method(), name)
        if not data:
            continue
        # Only publish top 3 as events
        for d in data[:3]:
            symbol = d.get("symbol")
            change = round(d.get("changesPercentage", 0), 2)
            if abs(change) < 5:  # only notable moves
                continue
            event = {
                "id": new_id("evt"),
                "type": "price_alert",
                "symbol": symbol,
                "headline": f"{symbol} {'up' if change > 0 else 'down'} {abs(change):.1f}% — top {name.replace('_', ' ')}",
                "body_excerpt": f"Price: ${d.get('price', 0):.2f}",
                "source": "FMP",
                "timestamp": datetime.utcnow().isoformat(),
                "importance": 4 if abs(change) > 10 else 3,
                "linked_recommendation_ids": [],
            }
            try:
                insert_event(event)
            except Exception:
                pass
            await event_bus.publish("market_event", event)


async def poll_upcoming_earnings():
    """Every 30 min — earnings in next 7 days."""
    earnings = await _safe_call(_fmp.upcoming_earnings(days_ahead=7), "earnings")
    if not earnings:
        return
    # Only care about stocks we hold or have recommendations for
    watched = set()
    for t in list_trades(open_only=True):
        if t.get("symbol"):
            watched.add(t["symbol"])
    for r in list_recommendations(limit=20):
        if r.get("symbol"):
            watched.add(r["symbol"])

    for e in earnings:
        if e.get("symbol") in watched:
            event = {
                "id": new_id("evt"),
                "type": "earnings",
                "symbol": e["symbol"],
                "headline": f"{e['symbol']} reports earnings on {e.get('date', '?')}",
                "body_excerpt": f"EPS est: {e.get('epsEstimated', '?')}",
                "source": "FMP Calendar",
                "timestamp": datetime.utcnow().isoformat(),
                "importance": 5,
                "linked_recommendation_ids": [],
            }
            try:
                insert_event(event)
            except Exception:
                pass
            await event_bus.publish("market_event", event)


# ── Background loop ──

async def poll_all() -> dict:
    """One-shot poll of all data sources. Used by /api/poll-market endpoint."""
    watched = _get_watched_symbols()
    if watched:
        await poll_ticker_batch(watched)
    await poll_stock_news()
    await poll_general_news()
    await poll_market_movers()
    await poll_upcoming_earnings()
    return get_poll_stats()


async def run_poller():
    """Main polling loop. Runs indefinitely with staggered intervals."""
    global _last_poll_summary, _call_count, _call_count_reset

    settings = get_settings()
    if not settings.fmp_api_key:
        print("[poller] FMP_API_KEY not set — poller disabled")
        return

    print("[poller] starting market data poller — watching positions + recommendations + SPY")
    _call_count = 0
    _call_count_reset = time.time()

    tick = 0

    while True:
        try:
            cycle_start = time.time()
            tick += 1

            # Every 15s — quote all watched symbols (positions + recs + SPY)
            watched = _get_watched_symbols()
            if watched:
                await poll_ticker_batch(watched)

            # Every 2 min (tick 8) — stock news
            if tick % 8 == 0:
                await poll_stock_news()

            # Every 5 min (tick 20) — general news + market movers
            if tick % 20 == 0:
                await poll_general_news()
                await poll_market_movers()

            # Every 30 min (tick 120) — upcoming earnings
            if tick % 120 == 0:
                await poll_upcoming_earnings()

            elapsed = time.time() - cycle_start
            total_elapsed = time.time() - _call_count_reset
            rate = _call_count / (total_elapsed / 60) if total_elapsed > 60 else _call_count

            _last_poll_summary = {
                "tick": tick,
                "cycle_ms": round(elapsed * 1000),
                "total_calls": _call_count,
                "minutes_running": round(total_elapsed / 60, 1),
                "calls_per_min": round(rate, 1),
                "budget_pct": round(rate / 300 * 100, 1),
            }

            if tick % 20 == 0:  # log every 5 min
                print(f"[poller] tick={tick} calls={_call_count} rate={rate:.0f}/min ({rate/300*100:.1f}% budget)")

        except asyncio.CancelledError:
            print("[poller] cancelled")
            break
        except Exception as e:
            print(f"[poller] error: {e}")

        await asyncio.sleep(15)  # base tick = 15 seconds
