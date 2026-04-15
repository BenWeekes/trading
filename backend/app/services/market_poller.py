"""Market data poller — pulls FMP data on intervals and logs what's available.

Tested against FMP starter plan (300 calls/min):
- batch-quote: NOT available (402)
- individual quotes: work (1 call per symbol)
- news/stock-latest: works (with or without symbol)
- news/general-latest: works
- biggest-gainers/losers: work
- most-actives: works
- earnings-calendar: works

Strategy: use individual quotes for positions/watchlist, bulk endpoints for discovery.
"""
from __future__ import annotations

import asyncio
import time

from ..adapters.fmp import FMPClient
from ..config import get_settings


async def poll_all() -> dict:
    """Poll all available FMP data sources. Returns a summary of what was fetched."""
    fmp = FMPClient()
    settings = get_settings()
    if not settings.fmp_api_key:
        return {"error": "FMP_API_KEY not configured"}

    results = {}
    total_calls = 0
    start = time.time()

    # 1. Individual quotes for key symbols (1 call each, but can run in parallel)
    watchlist = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "AMD", "PLTR", "SPY", "QQQ", "NKE"]
    try:
        quotes_raw = await asyncio.gather(*[fmp.quote(s) for s in watchlist], return_exceptions=True)
        quotes = [q for q in quotes_raw if isinstance(q, dict) and q.get("symbol")]
        results["quotes"] = {
            "count": len(quotes),
            "calls_used": len(watchlist),
            "data": {q["symbol"]: {
                "price": q.get("price"),
                "change_pct": round(q.get("changesPercentage", 0), 2),
                "volume": q.get("volume"),
                "day_high": q.get("dayHigh"),
                "day_low": q.get("dayLow"),
                "prev_close": q.get("previousClose"),
                "market_cap": q.get("marketCap"),
            } for q in quotes},
        }
        total_calls += len(watchlist)
        print(f"[poller] quotes: {len(quotes)}/{len(watchlist)} symbols ({len(watchlist)} calls)")
    except Exception as e:
        results["quotes"] = {"error": str(e)}
        print(f"[poller] quotes FAILED: {e}")

    # 2. Stock news — latest across market
    try:
        news = await fmp.news("", limit=20)  # empty symbol = all
        if not news:
            news = []
            # Try without symbol param
            raw = await fmp._get("news/stock-latest", {"limit": 20})
            if isinstance(raw, list):
                news = raw
        results["stock_news"] = {
            "count": len(news),
            "data": [{
                "title": n.get("title", "")[:100],
                "symbol": n.get("symbol"),
                "source": n.get("site") or n.get("source"),
                "date": (n.get("publishedDate") or "")[:19],
                "url": n.get("url"),
            } for n in news[:10]],
        }
        total_calls += 1
        print(f"[poller] stock_news: {len(news)} articles")
    except Exception as e:
        results["stock_news"] = {"error": str(e)}
        print(f"[poller] stock_news FAILED: {e}")

    # 3. General news
    try:
        raw = await fmp._get("news/general-latest", {"limit": 10})
        gnews = raw if isinstance(raw, list) else []
        results["general_news"] = {
            "count": len(gnews),
            "data": [{
                "title": n.get("title", "")[:100],
                "source": n.get("site") or n.get("source"),
                "date": (n.get("publishedDate") or "")[:19],
            } for n in gnews[:5]],
        }
        total_calls += 1
        print(f"[poller] general_news: {len(gnews)} articles")
    except Exception as e:
        results["general_news"] = {"error": str(e)}
        print(f"[poller] general_news FAILED: {e}")

    # 4. Market movers (1 call each, no symbols needed)
    for name, method in [("gainers", fmp.biggest_gainers), ("losers", fmp.biggest_losers), ("most_active", fmp.most_active)]:
        try:
            data = await method()
            results[name] = {
                "count": len(data),
                "data": [{
                    "symbol": d.get("symbol"),
                    "name": (d.get("name") or "")[:30],
                    "price": d.get("price"),
                    "change_pct": round(d.get("changesPercentage", 0), 2),
                    "volume": d.get("volume"),
                } for d in data[:10]],
            }
            total_calls += 1
            print(f"[poller] {name}: {len(data)} stocks")
        except Exception as e:
            results[name] = {"error": str(e)}
            print(f"[poller] {name} FAILED: {e}")

    # 5. Upcoming earnings (next 14 days)
    try:
        earnings = await fmp.upcoming_earnings(days_ahead=14)
        # Filter to >$500M market cap symbols we care about
        results["upcoming_earnings"] = {
            "count": len(earnings),
            "data": [{
                "symbol": e.get("symbol"),
                "date": e.get("date"),
                "eps_estimated": e.get("epsEstimated"),
                "revenue_estimated": e.get("revenueEstimated"),
            } for e in earnings[:15]],
        }
        total_calls += 1
        print(f"[poller] upcoming_earnings: {len(earnings)} events")
    except Exception as e:
        results["upcoming_earnings"] = {"error": str(e)}
        print(f"[poller] upcoming_earnings FAILED: {e}")

    elapsed = time.time() - start
    summary = {
        "total_api_calls": total_calls,
        "elapsed_seconds": round(elapsed, 2),
        "calls_per_minute_rate": round(total_calls / (elapsed / 60), 1) if elapsed > 0 else 0,
        "budget_300_per_min": f"{total_calls}/300 used ({total_calls/300*100:.1f}%)",
        "results": results,
    }
    print(f"\n[poller] DONE: {total_calls} calls in {elapsed:.1f}s")
    return summary


if __name__ == "__main__":
    import json
    result = asyncio.run(poll_all())
    print("\n" + json.dumps(result, indent=2, default=str))
