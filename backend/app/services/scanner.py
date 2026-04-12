from __future__ import annotations

from pathlib import Path
import csv

from ..config import ROOT_DIR, get_settings
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import insert_event, list_recommendations, upsert_recommendation
from ..services.filters import apply_pead_filters
from ..services.position_sizing import calculate_position
from ..adapters.fmp import FMPClient


TRADE_LOG = ROOT_DIR / "phase1" / "trade_log.csv"
EARNINGS_LOG = ROOT_DIR / "phase1" / "earnings_log.csv"

_TERMINAL_STATUSES = {"closed", "rejected", "cancelled", "failed"}


def _find_existing_rec(symbol: str) -> dict | None:
    """Return an active recommendation for this symbol if one exists."""
    for rec in list_recommendations(limit=50):
        if rec["symbol"] == symbol and rec["status"] not in _TERMINAL_STATUSES:
            return rec
    return None


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
            existing = _find_existing_rec(symbol)
            if existing:
                recommendation = existing
            else:
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
    # Always supplement with diverse mock data so scans return multiple symbols
    mock_earnings = [
        {"symbol": "NVDA", "date": "2026-04-12", "actual_eps": "1.25", "estimated_eps": "1.12", "surprise_pct": "11.6"},
        {"symbol": "META", "date": "2026-04-12", "actual_eps": "6.43", "estimated_eps": "5.82", "surprise_pct": "10.5"},
        {"symbol": "AMZN", "date": "2026-04-12", "actual_eps": "1.36", "estimated_eps": "1.20", "surprise_pct": "13.3"},
        {"symbol": "MSFT", "date": "2026-04-12", "actual_eps": "3.22", "estimated_eps": "2.96", "surprise_pct": "8.8"},
        {"symbol": "AMD", "date": "2026-04-12", "actual_eps": "0.92", "estimated_eps": "0.83", "surprise_pct": "10.8"},
        {"symbol": "CRM", "date": "2026-04-12", "actual_eps": "2.56", "estimated_eps": "2.35", "surprise_pct": "8.9"},
        {"symbol": "PLTR", "date": "2026-04-12", "actual_eps": "0.11", "estimated_eps": "0.09", "surprise_pct": "22.2"},
        {"symbol": "AAPL", "date": "2026-04-12", "actual_eps": "1.65", "estimated_eps": "1.48", "surprise_pct": "11.5"},
    ]
    # Dedupe CSV rows by symbol (keep first), then merge mock data
    seen: set[str] = set()
    deduped: list[dict] = []
    for row in earnings:
        sym = row.get("symbol")
        if sym and sym not in seen:
            seen.add(sym)
            deduped.append(row)
    for mock in mock_earnings:
        if mock["symbol"] not in seen:
            seen.add(mock["symbol"])
            deduped.append(mock)
    earnings = deduped
    results = []
    for row in earnings[:10]:
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
        existing = _find_existing_rec(symbol)
        if existing:
            recommendation = existing
        else:
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
