"""Voice command parser — intercepts spoken commands before they reach the LLM."""
from __future__ import annotations

import re

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    get_recommendation,
    list_recommendations,
    list_trades,
)
from ..services.event_bus import event_bus
from ..services.portfolio import get_portfolio_summary


class VoiceCommandResult:
    def __init__(self, handled: bool, response: str = "", sse_event: dict | None = None):
        self.handled = handled
        self.response = response
        self.sse_event = sse_event


# Ticker pattern — 1-5 uppercase letters
_TICKER = r"([A-Z]{1,5})"
_TICKER_LOOSE = r"([A-Za-z]{1,5})"


async def parse_voice_command(text: str, current_rec_id: str | None = None) -> VoiceCommandResult:
    """Parse a voice command. Returns handled=True if it was a command, False to pass to LLM."""
    clean = text.strip()
    lower = clean.lower()

    # ── Navigation commands ──
    m = re.match(r"(?:show me|switch to|go to|open)\s+" + _TICKER_LOOSE, clean, re.IGNORECASE)
    if m:
        return await _navigate_to_symbol(m.group(1).upper())

    if lower in ("show events", "events tab", "show news"):
        return _tab_command("events", "Showing events tab.")

    if lower in ("show recommendations", "recommendations tab", "show recs"):
        return _tab_command("recs", "Showing recommendations tab.")

    if lower in ("show positions", "show portfolio", "positions tab"):
        return _tab_command("positions", "Showing portfolio.")

    # ── Action commands ──
    m = re.match(r"approve\s+" + _TICKER_LOOSE, clean, re.IGNORECASE)
    if m:
        return await _approve_command(m.group(1).upper())

    if lower in ("approve", "approve this", "approve it"):
        return await _approve_command(None, current_rec_id)

    m = re.match(r"reject\s+" + _TICKER_LOOSE, clean, re.IGNORECASE)
    if m:
        return await _reject_command(m.group(1).upper())

    if lower in ("reject", "reject this", "reject it"):
        return await _reject_command(None, current_rec_id)

    if lower in ("execute", "execute this", "execute it", "go ahead"):
        return await _execute_command(current_rec_id)

    m = re.match(r"execute\s+" + _TICKER_LOOSE, clean, re.IGNORECASE)
    if m:
        return await _execute_command(None, m.group(1).upper())

    m = re.match(r"(?:sell|close)\s+" + _TICKER_LOOSE, clean, re.IGNORECASE)
    if m:
        return await _sell_command(m.group(1).upper())

    # ── Info commands ──
    if lower in ("status", "what's the status", "whats the status", "portfolio status", "how are we doing"):
        return await _status_command()

    if lower in ("help", "what can you do", "what commands", "voice commands"):
        return _help_command()

    # Not a command — pass to LLM
    return VoiceCommandResult(handled=False)


async def _navigate_to_symbol(symbol: str) -> VoiceCommandResult:
    rec = _find_rec_by_symbol(symbol)
    if not rec:
        return VoiceCommandResult(True, f"No recommendation found for {symbol}.")

    direction = rec.get("direction") or "under review"
    conviction = rec.get("conviction") or "unknown"
    thesis = rec.get("thesis") or ""
    short_thesis = thesis[:100] if thesis else "No thesis yet."

    await event_bus.publish("voice_command", {
        "action": "navigate", "symbol": symbol, "recommendation_id": rec["id"],
    })

    return VoiceCommandResult(
        True,
        f"Switching to {symbol}. {direction}, conviction {conviction} out of 10. {short_thesis}",
        {"action": "navigate", "symbol": symbol, "recommendation_id": rec["id"]},
    )


def _tab_command(tab: str, response: str) -> VoiceCommandResult:
    return VoiceCommandResult(True, response, {"action": "switch_tab", "tab": tab})


async def _approve_command(symbol: str | None = None, rec_id: str | None = None) -> VoiceCommandResult:
    rec = _resolve_rec(symbol, rec_id)
    if not rec:
        return VoiceCommandResult(True, f"No recommendation to approve{' for ' + symbol if symbol else ''}.")

    from ..routes.recommendations import approve as approve_route
    from ..services.state_machine import ensure_transition

    status = rec["status"]
    if status not in ("awaiting_user_feedback", "awaiting_user_approval"):
        return VoiceCommandResult(True, f"{rec['symbol']} is in {status.replace('_', ' ')} state, not ready for approval.")

    # Move to approval if in feedback
    if status == "awaiting_user_feedback":
        from ..db.repositories import upsert_recommendation
        ensure_transition(status, "awaiting_user_approval")
        rec["status"] = "awaiting_user_approval"
        rec["updated_at"] = utcnow_iso()
        upsert_recommendation(rec)

    ensure_transition(rec["status"], "approved")
    from ..db.repositories import upsert_recommendation, insert_approval
    rec["status"] = "approved"
    rec["updated_at"] = utcnow_iso()
    upsert_recommendation(rec)
    insert_approval({
        "id": new_id("approval"), "recommendation_id": rec["id"],
        "status": "approved", "reviewer_notes": "Voice approved",
        "requested_at": rec["updated_at"], "approved_at": rec["updated_at"], "rejected_at": None,
    })
    await event_bus.publish("recommendation_update", rec)

    shares = rec.get("position_size_shares") or "unknown"
    return VoiceCommandResult(
        True,
        f"Approved {rec.get('direction', '')} {rec['symbol']}, {shares} shares.",
        {"action": "approve", "symbol": rec["symbol"], "recommendation_id": rec["id"]},
    )


async def _reject_command(symbol: str | None = None, rec_id: str | None = None) -> VoiceCommandResult:
    rec = _resolve_rec(symbol, rec_id)
    if not rec:
        return VoiceCommandResult(True, f"No recommendation to reject{' for ' + symbol if symbol else ''}.")

    from ..services.state_machine import ensure_transition
    from ..db.repositories import upsert_recommendation, insert_approval

    status = rec["status"]
    if status == "awaiting_user_feedback":
        rec["status"] = "awaiting_user_approval"
    if rec["status"] != "awaiting_user_approval":
        return VoiceCommandResult(True, f"{rec['symbol']} is not in a rejectable state.")

    ensure_transition(rec["status"], "rejected")
    rec["status"] = "rejected"
    rec["updated_at"] = utcnow_iso()
    upsert_recommendation(rec)
    insert_approval({
        "id": new_id("approval"), "recommendation_id": rec["id"],
        "status": "rejected", "reviewer_notes": "Voice rejected",
        "requested_at": rec["updated_at"], "approved_at": None, "rejected_at": rec["updated_at"],
    })
    await event_bus.publish("recommendation_update", rec)

    return VoiceCommandResult(True, f"Rejected {rec['symbol']}.", {"action": "reject", "symbol": rec["symbol"]})


async def _execute_command(rec_id: str | None = None, symbol: str | None = None) -> VoiceCommandResult:
    rec = _resolve_rec(symbol, rec_id)
    if not rec:
        return VoiceCommandResult(True, "No approved recommendation to execute.")
    if rec["status"] != "approved":
        return VoiceCommandResult(True, f"{rec['symbol']} is {rec['status'].replace('_', ' ')}, not approved yet.")

    await event_bus.publish("voice_command", {"action": "execute", "recommendation_id": rec["id"], "symbol": rec["symbol"]})
    return VoiceCommandResult(
        True,
        f"Executing {rec.get('direction', '')} {rec['symbol']}. Check the trade desk for confirmation.",
        {"action": "execute", "symbol": rec["symbol"], "recommendation_id": rec["id"]},
    )


async def _sell_command(symbol: str) -> VoiceCommandResult:
    trades = list_trades(open_only=True)
    trade = next((t for t in trades if t["symbol"] == symbol), None)
    if not trade:
        return VoiceCommandResult(True, f"No open position in {symbol} to sell.")

    await event_bus.publish("voice_command", {"action": "sell", "symbol": symbol, "trade_id": trade["id"]})
    shares = trade.get("shares", "unknown")
    return VoiceCommandResult(
        True,
        f"Selling {shares} shares of {symbol}. Confirm on the trade desk.",
        {"action": "sell", "symbol": symbol, "trade_id": trade["id"]},
    )


async def _status_command() -> VoiceCommandResult:
    portfolio = get_portfolio_summary()
    positions = list_trades(open_only=True)
    recs = list_recommendations(limit=50)
    pending = [r for r in recs if r["status"] in ("awaiting_user_feedback", "awaiting_user_approval")]

    value = portfolio.get("portfolio_value", 0)
    pnl = portfolio.get("daily_change", 0)
    return VoiceCommandResult(
        True,
        f"Portfolio value ${value:,.0f}, daily change ${pnl:+,.0f}. "
        f"{len(positions)} open position{'s' if len(positions) != 1 else ''}, "
        f"{len(pending)} pending recommendation{'s' if len(pending) != 1 else ''}.",
    )


def _help_command() -> VoiceCommandResult:
    return VoiceCommandResult(True,
        "You can say: show me NVDA, approve, reject, execute, sell NVDA, "
        "show events, show recommendations, show positions, status, or ask any trading question."
    )


def _find_rec_by_symbol(symbol: str) -> dict | None:
    for rec in list_recommendations(limit=50):
        if rec["symbol"] == symbol:
            return rec
    return None


def _resolve_rec(symbol: str | None, rec_id: str | None) -> dict | None:
    if rec_id:
        rec = get_recommendation(rec_id)
        if rec:
            return rec
    if symbol:
        return _find_rec_by_symbol(symbol)
    return None
