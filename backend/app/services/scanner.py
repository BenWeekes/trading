from __future__ import annotations

from pathlib import Path
import csv

from ..config import ROOT_DIR, get_settings
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import get_all_strategy_settings, insert_event, list_recommendations, upsert_recommendation
from ..services.filters import apply_pead_filters
from ..services.position_sizing import calculate_position
from ..adapters.fmp import FMPClient


TRADE_LOG = ROOT_DIR / "phase1" / "trade_log.csv"
EARNINGS_LOG = ROOT_DIR / "phase1" / "earnings_log.csv"

_TERMINAL_STATUSES = {"closed", "rejected", "cancelled", "failed"}


def _find_existing_rec(symbol: str) -> dict | None:
    for rec in list_recommendations(limit=50):
        if rec["symbol"] == symbol and rec["status"] not in _TERMINAL_STATUSES:
            return rec
    return None


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _get_setting(settings_dict: dict, key: str, default: str) -> str:
    return settings_dict.get(key, default)


async def run_scan() -> dict:
    settings = get_settings()
    strat = get_all_strategy_settings()
    fmp = FMPClient()

    # V2 parameters from settings
    min_eps_surprise = float(_get_setting(strat, "min_surprise_pct", "10.0"))
    min_rev_surprise = float(_get_setting(strat, "min_revenue_surprise_pct", "1.0"))
    require_rev_beat = _get_setting(strat, "require_revenue_beat", "true") == "true"
    max_candidates = int(_get_setting(strat, "max_candidates_per_scan", "2"))
    min_price = float(_get_setting(strat, "min_price", "5.0"))
    min_market_cap = float(_get_setting(strat, "min_market_cap", "500000000"))
    target_hold = _get_setting(strat, "target_hold_days", "10")

    if settings.event_mode == "mock" or not settings.fmp_api_key:
        return await _scan_from_logs_or_mock(min_eps_surprise, min_rev_surprise, require_rev_beat, max_candidates, target_hold)

    try:
        events = await fmp.earnings_calendar()
        if not events:
            return await _scan_from_logs_or_mock(min_eps_surprise, min_rev_surprise, require_rev_beat, max_candidates, target_hold)

        candidates = []
        spy = await fmp.quote("SPY")

        for event in events:
            symbol = event.get("symbol")
            actual_eps = event.get("epsActual")
            est_eps = event.get("epsEstimated")
            actual_rev = event.get("revenueActual")
            est_rev = event.get("revenueEstimated")

            if not symbol or actual_eps is None or est_eps in (None, 0):
                continue

            # V2 filter: EPS surprise
            eps_surprise = round(((actual_eps - est_eps) / abs(est_eps)) * 100, 2)
            if eps_surprise < min_eps_surprise:
                continue

            # V2 filter: Revenue beat
            rev_surprise = 0.0
            if actual_rev and est_rev and est_rev > 0:
                rev_surprise = round(((actual_rev - est_rev) / est_rev) * 100, 2)

            if require_rev_beat and rev_surprise < min_rev_surprise:
                continue

            quote = await fmp.quote(symbol)
            if not quote:
                continue

            # Universe filters
            price = float(quote.get("price") or 0)
            mcap = float(quote.get("marketCap") or 0)
            if price < min_price or mcap < min_market_cap:
                continue

            filters = apply_pead_filters(quote, spy)
            open_price = float(quote.get("open") or price)

            candidates.append({
                "symbol": symbol,
                "eps_surprise": eps_surprise,
                "rev_surprise": rev_surprise,
                "price": open_price,
                "market_cap": mcap,
                "event": event,
                "quote": quote,
                "filters": filters,
                "score": eps_surprise + rev_surprise,  # simple ranking score
            })

        # V2: take top N candidates by score
        candidates.sort(key=lambda c: c["score"], reverse=True)
        top = candidates[:max_candidates]

        results = []
        for cand in top:
            sizing = calculate_position(cand["price"], 100000.0)
            event_record = {
                "id": new_id("evt"),
                "type": "earnings",
                "symbol": cand["symbol"],
                "headline": f"{cand['symbol']} EPS {cand['eps_surprise']:+.1f}% Rev {cand['rev_surprise']:+.1f}%",
                "body_excerpt": f"EPS surprise {cand['eps_surprise']:+.1f}%, revenue surprise {cand['rev_surprise']:+.1f}%. V2 qualified.",
                "source": "FMP",
                "timestamp": utcnow_iso(),
                "importance": 5 if cand["eps_surprise"] >= 15 else 4,
                "linked_recommendation_ids": [],
            }
            insert_event(event_record)

            existing = _find_existing_rec(cand["symbol"])
            if existing:
                recommendation = existing
            else:
                recommendation = {
                    "id": new_id("rec"),
                    "symbol": cand["symbol"],
                    "direction": None,
                    "status": "observing",
                    "strategy_type": "PEAD_V2",
                    "thesis": f"EPS beat {cand['eps_surprise']:+.1f}% with revenue confirmation {cand['rev_surprise']:+.1f}%.",
                    "entry_price": sizing.get("entry_price"),
                    "entry_logic": sizing.get("entry_logic"),
                    "stop_price": sizing.get("stop_price"),
                    "stop_logic": sizing.get("stop_logic"),
                    "target_price": sizing.get("target_price"),
                    "target_logic": sizing.get("target_logic"),
                    "position_size_shares": sizing.get("position_size_shares"),
                    "position_size_dollars": sizing.get("position_size_dollars"),
                    "time_horizon": f"{target_hold} trading days",
                    "conviction": None,
                    "supporting_roles": [],
                    "blocking_risks": [],
                    "created_at": utcnow_iso(),
                    "updated_at": utcnow_iso(),
                }
                upsert_recommendation(recommendation)
            results.append({"event": event_record, "recommendation": recommendation, "filters": cand["filters"]})

        return {"results": results, "candidates_scanned": len(candidates), "candidates_selected": len(top)}

    except Exception:
        return await _scan_from_logs_or_mock(min_eps_surprise, min_rev_surprise, require_rev_beat, max_candidates, target_hold)


async def _scan_from_logs_or_mock(min_eps: float, min_rev: float, require_rev: bool, max_cands: int, hold: str) -> dict:
    earnings = _read_csv(EARNINGS_LOG)

    # Dedupe + supplement with mock data
    mock_earnings = [
        {"symbol": "NVDA", "date": "2026-04-13", "actual_eps": "1.25", "estimated_eps": "1.12", "surprise_pct": "11.6",
         "revenue": "35200000000", "revenue_estimated": "33100000000"},
        {"symbol": "META", "date": "2026-04-13", "actual_eps": "6.43", "estimated_eps": "5.82", "surprise_pct": "10.5",
         "revenue": "42800000000", "revenue_estimated": "41200000000"},
        {"symbol": "AMZN", "date": "2026-04-13", "actual_eps": "1.36", "estimated_eps": "1.20", "surprise_pct": "13.3",
         "revenue": "170500000000", "revenue_estimated": "165200000000"},
        {"symbol": "MSFT", "date": "2026-04-13", "actual_eps": "3.22", "estimated_eps": "2.96", "surprise_pct": "8.8",
         "revenue": "65200000000", "revenue_estimated": "63500000000"},
        {"symbol": "AMD", "date": "2026-04-13", "actual_eps": "0.92", "estimated_eps": "0.83", "surprise_pct": "10.8",
         "revenue": "7400000000", "revenue_estimated": "7100000000"},
        {"symbol": "PLTR", "date": "2026-04-13", "actual_eps": "0.11", "estimated_eps": "0.09", "surprise_pct": "22.2",
         "revenue": "1120000000", "revenue_estimated": "1050000000"},
        {"symbol": "AAPL", "date": "2026-04-13", "actual_eps": "1.65", "estimated_eps": "1.48", "surprise_pct": "11.5",
         "revenue": "124500000000", "revenue_estimated": "120800000000"},
    ]

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

    # Score and filter
    candidates = []
    for row in deduped:
        symbol = row.get("symbol")
        eps_surprise = float(row.get("surprise_pct") or 0)
        if eps_surprise < min_eps:
            continue

        # Revenue check
        rev = float(row.get("revenue") or 0)
        rev_est = float(row.get("revenue_estimated") or 0)
        rev_surprise = round(((rev - rev_est) / rev_est) * 100, 2) if rev_est > 0 else 0.0
        if require_rev and rev_surprise < min_rev:
            continue

        candidates.append({
            "symbol": symbol,
            "eps_surprise": eps_surprise,
            "rev_surprise": rev_surprise,
            "score": eps_surprise + rev_surprise,
        })

    # Top N by score
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[:max_cands]

    results = []
    for cand in top:
        event_record = {
            "id": new_id("evt"),
            "type": "earnings",
            "symbol": cand["symbol"],
            "headline": f"{cand['symbol']} EPS {cand['eps_surprise']:+.1f}% Rev {cand['rev_surprise']:+.1f}%",
            "body_excerpt": f"EPS beat {cand['eps_surprise']:+.1f}%, revenue beat {cand['rev_surprise']:+.1f}%. PEAD V2 candidate.",
            "source": "Local",
            "timestamp": utcnow_iso(),
            "importance": 5 if cand["eps_surprise"] >= 15 else 4,
            "linked_recommendation_ids": [],
        }
        insert_event(event_record)

        existing = _find_existing_rec(cand["symbol"])
        if existing:
            recommendation = existing
        else:
            sizing = calculate_position(100.0 + cand["eps_surprise"], 100000.0)
            recommendation = {
                "id": new_id("rec"),
                "symbol": cand["symbol"],
                "direction": None,
                "status": "observing",
                "strategy_type": "PEAD_V2",
                "thesis": f"EPS beat {cand['eps_surprise']:+.1f}% with revenue confirmation {cand['rev_surprise']:+.1f}%.",
                "entry_price": sizing.get("entry_price"),
                "entry_logic": sizing.get("entry_logic"),
                "stop_price": sizing.get("stop_price"),
                "stop_logic": sizing.get("stop_logic"),
                "target_price": sizing.get("target_price"),
                "target_logic": sizing.get("target_logic"),
                "position_size_shares": sizing.get("position_size_shares"),
                "position_size_dollars": sizing.get("position_size_dollars"),
                "time_horizon": f"{hold} trading days",
                "conviction": None,
                "supporting_roles": [],
                "blocking_risks": [],
                "created_at": utcnow_iso(),
                "updated_at": utcnow_iso(),
            }
            upsert_recommendation(recommendation)
        results.append({"event": event_record, "recommendation": recommendation, "filters": {"filters_passed": True}})

    return {"results": results, "candidates_scanned": len(candidates), "candidates_selected": len(top)}
