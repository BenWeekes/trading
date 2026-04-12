from __future__ import annotations

from pathlib import Path
import csv

from ..config import ROOT_DIR, get_settings
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import insert_event, upsert_recommendation
from ..services.filters import apply_pead_filters
from ..services.position_sizing import calculate_position
from ..adapters.fmp import FMPClient


TRADE_LOG = ROOT_DIR / "phase1" / "trade_log.csv"
EARNINGS_LOG = ROOT_DIR / "phase1" / "earnings_log.csv"


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


async def run_scan() -> dict:
    settings = get_settings()
    fmp = FMPClient()
    if settings.event_mode == "mock" or not settings.fmp_api_key:
        return await _scan_from_logs_or_mock()
    try:
        events = await fmp.earnings_calendar()
        if not events:
            return await _scan_from_logs_or_mock()
        results = []
        spy = await fmp.quote("SPY")
        for event in events:
            symbol = event.get("symbol")
            actual = event.get("epsActual")
            estimate = event.get("epsEstimated")
            if not symbol or actual is None or estimate in (None, 0):
                continue
            surprise_pct = round(((actual - estimate) / abs(estimate)) * 100, 2)
            if surprise_pct < settings.min_surprise_pct:
                continue
            quote = await fmp.quote(symbol)
            if not quote:
                continue
            if float(quote.get("marketCap") or 0) < settings.min_market_cap:
                continue
            filters = apply_pead_filters(quote, spy)
            price = float(quote.get("open") or quote.get("price") or 0)
            sizing = calculate_position(price, 100000.0) if price else {}
            event_record = {
                "id": new_id("evt"),
                "type": "earnings",
                "symbol": symbol,
                "headline": f"{symbol} EPS surprise {surprise_pct:+.2f}%",
                "body_excerpt": "Imported from FMP earnings calendar.",
                "source": "FMP",
                "timestamp": utcnow_iso(),
                "importance": 4 if surprise_pct >= 10 else 3,
                "linked_recommendation_ids": [],
            }
            insert_event(event_record)
            recommendation = {
                "id": new_id("rec"),
                "symbol": symbol,
                "direction": None,
                "status": "observing",
                "strategy_type": "PEAD",
                "thesis": f"Earnings surprise of {surprise_pct:+.2f}% detected.",
                "entry_price": sizing.get("entry_price"),
                "entry_logic": sizing.get("entry_logic"),
                "stop_price": sizing.get("stop_price"),
                "stop_logic": sizing.get("stop_logic"),
                "target_price": sizing.get("target_price"),
                "target_logic": sizing.get("target_logic"),
                "position_size_shares": sizing.get("position_size_shares"),
                "position_size_dollars": sizing.get("position_size_dollars"),
                "time_horizon": "1-60 days",
                "conviction": None,
                "supporting_roles": [],
                "blocking_risks": [filters["blocked_by"]] if filters.get("blocked_by") else [],
                "created_at": utcnow_iso(),
                "updated_at": utcnow_iso(),
            }
            upsert_recommendation(recommendation)
            results.append({"event": event_record, "recommendation": recommendation, "filters": filters})
        return {"results": results}
    except Exception:
        return await _scan_from_logs_or_mock()


async def _scan_from_logs_or_mock() -> dict:
    earnings = _read_csv(EARNINGS_LOG)
    if not earnings:
        earnings = [
            {
                "symbol": "NVDA",
                "date": "2026-04-11",
                "actual_eps": "1.25",
                "estimated_eps": "1.12",
                "surprise_pct": "11.6",
            },
            {
                "symbol": "AAPL",
                "date": "2026-04-11",
                "actual_eps": "1.55",
                "estimated_eps": "1.48",
                "surprise_pct": "4.7",
            },
        ]
    results = []
    for row in earnings[:5]:
        symbol = row.get("symbol")
        surprise_pct = float(row.get("surprise_pct") or 0)
        if surprise_pct < get_settings().min_surprise_pct:
            continue
        event_record = {
            "id": new_id("evt"),
            "type": "earnings",
            "symbol": symbol,
            "headline": f"{symbol} EPS surprise {surprise_pct:+.2f}%",
            "body_excerpt": "Local mock/log-derived event.",
            "source": "Local",
            "timestamp": utcnow_iso(),
            "importance": 4,
            "linked_recommendation_ids": [],
        }
        insert_event(event_record)
        sizing = calculate_position(100.0 + surprise_pct, 100000.0)
        recommendation = {
            "id": new_id("rec"),
            "symbol": symbol,
            "direction": None,
            "status": "observing",
            "strategy_type": "PEAD",
            "thesis": f"{symbol} qualified for post-earnings role review.",
            "entry_price": sizing.get("entry_price"),
            "entry_logic": sizing.get("entry_logic"),
            "stop_price": sizing.get("stop_price"),
            "stop_logic": sizing.get("stop_logic"),
            "target_price": sizing.get("target_price"),
            "target_logic": sizing.get("target_logic"),
            "position_size_shares": sizing.get("position_size_shares"),
            "position_size_dollars": sizing.get("position_size_dollars"),
            "time_horizon": "1-60 days",
            "conviction": None,
            "supporting_roles": [],
            "blocking_risks": [],
            "created_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
        }
        upsert_recommendation(recommendation)
        results.append({"event": event_record, "recommendation": recommendation, "filters": {"filters_passed": True}})
    return {"results": results}
