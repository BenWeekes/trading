"""Voice tool definitions and executor for LLM function calling."""
from __future__ import annotations

import time
from typing import Any

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    get_all_strategy_settings,
    get_recommendation,
    get_summary,
    list_events,
    list_recommendations,
    list_trades,
    set_strategy_setting,
)
from ..services.event_bus import event_bus
from ..services.portfolio import get_portfolio_summary, get_positions

# ── Pending confirmation state (dev-only, prod needs Redis/DB) ──

_pending_actions: dict[str, dict] = {}
_CONFIRM_TTL = 30
_last_list_context: dict[str, dict] = {}


def _set_pending(session_id: str, action: dict) -> None:
    action["created_at"] = time.time()
    _pending_actions[session_id] = action


def _get_pending(session_id: str) -> dict | None:
    p = _pending_actions.get(session_id)
    if not p:
        return None
    if time.time() - p["created_at"] > _CONFIRM_TTL:
        _pending_actions.pop(session_id, None)
        return None
    return p


def _pop_pending(session_id: str) -> dict | None:
    p = _get_pending(session_id)
    if p:
        _pending_actions.pop(session_id, None)
    return p


def has_pending_action(session_id: str) -> bool:
    return _get_pending(session_id) is not None


def _set_last_list(session_id: str, kind: str, items: list[dict]) -> None:
    _last_list_context[session_id] = {
        "kind": kind,
        "items": items,
        "created_at": time.time(),
    }


def _get_last_list(session_id: str) -> dict | None:
    value = _last_list_context.get(session_id)
    if not value:
        return None
    if time.time() - value.get("created_at", 0) > 120:
        _last_list_context.pop(session_id, None)
        return None
    return value


def _dedupe_recommendations_by_symbol(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        symbol = item.get("symbol")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        out.append(item)
    return out


# ── Active context tracking ──

_active_context: dict[str, str] = {}  # session_id → recommendation_id


def set_active_context(session_id: str, recommendation_id: str) -> None:
    _active_context[session_id] = recommendation_id


def get_active_rec_id(session_id: str) -> str | None:
    return _active_context.get(session_id)


def _validate_active_context(session_id: str, recommendation_id: str) -> str | None:
    """Return error string if rec_id doesn't match active context, else None."""
    active = get_active_rec_id(session_id)
    if active and active != recommendation_id:
        rec = get_recommendation(active)
        symbol = rec["symbol"] if rec else "unknown"
        return f"Context has changed — you're now looking at {symbol}. Please confirm the current symbol."
    return None


# ── Tool definitions (OpenAI function calling format) ──

TOOL_DEFINITIONS = [
    # Trading actions
    {
        "type": "function",
        "function": {
            "name": "approve_and_execute",
            "description": "Approve and execute a trade. Call this tool immediately when user wants to buy or execute — the tool itself will ask for confirmation. Do NOT ask in text first, just call this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendation_id": {"type": "string", "description": "From current context."},
                    "sizing_intent": {"type": "string", "enum": ["suggested", "full", "half", "custom_dollars", "custom_shares"]},
                    "amount": {"type": "number", "description": "Only for custom_dollars or custom_shares."},
                },
                "required": ["recommendation_id", "sizing_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_recommendation",
            "description": "Reject the current recommendation. Use when user says reject, pass, skip, no thanks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendation_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["recommendation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell_position",
            "description": "Sell or close an open position. Call this tool immediately — it handles confirmation. Do NOT ask in text first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {"type": "string", "description": "From portfolio context."},
                    "sizing_intent": {"type": "string", "enum": ["all", "half", "custom_shares", "custom_dollars"]},
                    "amount": {"type": "number"},
                },
                "required": ["trade_id", "sizing_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_action",
            "description": "Confirm a pending action after the confirmation prompt. Use when user says confirm, yes, go ahead, do it.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_action",
            "description": "Cancel a pending action. Use when user says cancel, no, wait, stop.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # Navigation
    {
        "type": "function",
        "function": {
            "name": "navigate_to_symbol",
            "description": "Switch active view to a stock. Use when user says show me, switch to, what about.",
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. NVDA"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_status",
            "description": "Get portfolio summary. Use when user asks about status, P&L, cash, positions.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendation_detail",
            "description": "Get what all roles said about a recommendation.",
            "parameters": {
                "type": "object",
                "properties": {"recommendation_id": {"type": "string"}},
                "required": ["recommendation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recommendations",
            "description": "List all current recommendations with their status. Use when user asks 'what recommendations do we have', 'what trades are pending', 'what are we looking at'.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_inbox_items",
            "description": "List the items available in a UI list. Use when user asks what is in earnings, AI recommendations, news, or positions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab": {"type": "string", "enum": ["earnings", "ai", "news", "positions"]},
                    "limit": {"type": "number"},
                },
                "required": ["tab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_role",
            "description": "Ask Research, Risk, or Quant Pricing a question about the current recommendation. Use when the user asks you to ask another role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["research", "risk", "quant_pricing"]},
                    "question": {"type": "string"},
                    "recommendation_id": {"type": "string", "description": "Optional; defaults to active recommendation."},
                },
                "required": ["role", "question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_earnings",
            "description": "Run an earnings scan. Use when user says scan, find opportunities, what's new.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # UI Control
    {
        "type": "function",
        "function": {
            "name": "ui_control",
            "description": "Control the UI. Use for: show earnings, show ai, show news (left tabs), open/close settings, open/close help, filter chat by role, mute, end call.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["show_earnings", "show_ai", "show_news", "open_settings", "close_settings",
                                 "open_help", "close_help", "filter_chat", "end_call", "mute", "unmute", "scroll_down", "scroll_up"],
                    },
                    "value": {"type": "string", "description": "For filter_chat: role name or 'all'."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_setting",
            "description": "Change a strategy setting. Only these are voice-safe: min_conviction_to_trade, min_surprise_pct, max_positions, target_hold_days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "enum": ["min_conviction_to_trade", "min_surprise_pct", "max_positions", "target_hold_days"]},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
]


# ── Tool executor ──

async def execute_tool(name: str, args: dict, session_id: str) -> str:
    """Execute a tool call and return the result as a string for the LLM."""
    try:
        if name == "navigate_to_symbol":
            return await _exec_navigate(args, session_id)
        elif name == "approve_and_execute":
            return await _exec_approve_execute(args, session_id)
        elif name == "reject_recommendation":
            return await _exec_reject(args, session_id)
        elif name == "sell_position":
            return await _exec_sell(args, session_id)
        elif name == "confirm_action":
            return await _exec_confirm(session_id)
        elif name == "cancel_action":
            return await _exec_cancel(session_id)
        elif name == "get_portfolio_status":
            return _exec_portfolio()
        elif name == "get_recommendation_detail":
            return _exec_rec_detail(args)
        elif name == "list_recommendations":
            return _exec_list_recs(session_id)
        elif name == "list_inbox_items":
            return _exec_list_inbox_items(args, session_id)
        elif name == "ask_role":
            return await _exec_ask_role(args, session_id)
        elif name == "scan_earnings":
            return await _exec_scan()
        elif name == "ui_control":
            return await _exec_ui(args)
        elif name == "update_setting":
            return _exec_setting(args)
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error: {e}"


async def _exec_navigate(args: dict, session_id: str) -> str:
    symbol = args.get("symbol", "").upper()
    recs = list_recommendations(limit=50)
    rec = next((r for r in recs if r["symbol"] == symbol), None)
    if rec:
        set_active_context(session_id, rec["id"])
        await event_bus.publish("voice_command", {"action": "navigate", "symbol": symbol, "recommendation_id": rec["id"]})
        direction = rec.get("direction") or "under review"
        conviction = rec.get("conviction") or "pending"
        return f"Switched to {symbol}. {direction}, conviction {conviction}/10. Status: {rec['status'].replace('_',' ')}."

    events = list_events(limit=100)
    news = next((e for e in events if e.get("symbol") == symbol and e.get("type") not in {"earnings", "price_alert"}), None)
    if news:
        await event_bus.publish("voice_command", {"action": "open_event", "event_id": news["id"], "tab": "news", "symbol": symbol})
        return f"Opened the latest news item for {symbol}: {news.get('headline','')[:120]}"

    earnings = next((e for e in events if e.get("symbol") == symbol and e.get("type") == "earnings"), None)
    if earnings:
        await event_bus.publish("voice_command", {"action": "open_event", "event_id": earnings["id"], "tab": "earnings", "symbol": symbol})
        return f"Opened the latest earnings event for {symbol}: {earnings.get('headline','')[:120]}"

    return f"No recommendation, news, or earnings item found for {symbol}."


async def _exec_approve_execute(args: dict, session_id: str) -> str:
    rec_id = args.get("recommendation_id") or get_active_rec_id(session_id)
    if not rec_id:
        return "No active recommendation. Navigate to a stock first."
    ctx_err = _validate_active_context(session_id, rec_id)
    if ctx_err:
        return ctx_err
    rec = get_recommendation(rec_id)
    if not rec:
        return "Recommendation not found."

    # Resolve shares
    sizing = args.get("sizing_intent", "suggested")
    amount = args.get("amount")
    entry = float(rec.get("entry_price") or 0)
    suggested = float(rec.get("position_size_shares") or 0)

    if sizing == "suggested":
        shares = suggested
    elif sizing == "full":
        shares = suggested * 1.25
    elif sizing == "half":
        shares = suggested * 0.5
    elif sizing == "custom_dollars" and amount and entry:
        shares = round(amount / entry, 2)
    elif sizing == "custom_shares" and amount:
        shares = amount
    else:
        shares = suggested

    shares = round(shares, 2)
    cost = round(shares * entry, 2) if entry else 0

    _set_pending(session_id, {
        "action": "approve_and_execute",
        "recommendation_id": rec_id,
        "symbol": rec["symbol"],
        "shares": shares,
        "entry_price": entry,
        "cost": cost,
    })
    return f"About to {rec.get('direction','BUY')} {shares:.0f} shares of {rec['symbol']} at ${entry:.2f}, roughly ${cost:,.0f}. Say confirm to proceed."


async def _exec_reject(args: dict, session_id: str) -> str:
    rec_id = args.get("recommendation_id") or get_active_rec_id(session_id)
    if not rec_id:
        return "No active recommendation."
    ctx_err = _validate_active_context(session_id, rec_id)
    if ctx_err:
        return ctx_err

    import httpx
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"http://localhost:8000/api/recs/{rec_id}/reject", json={"reason": args.get("reason", "Voice rejected")})
    if r.status_code == 200:
        rec = get_recommendation(rec_id)
        await event_bus.publish("voice_command", {"action": "reject", "recommendation_id": rec_id, "symbol": rec.get("symbol") if rec else ""})
        return f"Rejected {rec['symbol'] if rec else 'recommendation'}."
    return f"Reject failed: {r.text[:100]}"


async def _exec_sell(args: dict, session_id: str) -> str:
    trade_id = args.get("trade_id")
    if not trade_id:
        return "No trade_id specified."
    trade = next((t for t in list_trades(open_only=True) if t["id"] == trade_id), None)
    if not trade:
        return "Open trade not found."

    total = float(trade.get("shares") or 0)
    sizing = args.get("sizing_intent", "all")
    amount = args.get("amount")

    if sizing == "all":
        shares = total
    elif sizing == "half":
        shares = round(total / 2, 2)
    elif sizing == "custom_shares" and amount:
        shares = min(amount, total)
    elif sizing == "custom_dollars" and amount:
        price = float(trade.get("current_price") or trade.get("entry_price") or 1)
        shares = min(round(amount / price, 2), total)
    else:
        shares = total

    _set_pending(session_id, {
        "action": "sell",
        "trade_id": trade_id,
        "symbol": trade["symbol"],
        "shares": shares,
    })
    direction = trade.get("direction", "BUY")
    exit_word = "cover" if direction == "SHORT" else "sell"
    return f"About to {exit_word} {shares:.0f} shares of {trade['symbol']}. Say confirm to proceed."


async def _exec_confirm(session_id: str) -> str:
    pending = _get_pending(session_id)
    if not pending:
        return "Nothing pending to confirm. It may have timed out."

    import httpx

    if pending["action"] == "approve_and_execute":
        rec_id = pending["recommendation_id"]
        ctx_err = _validate_active_context(session_id, rec_id)
        if ctx_err:
            return ctx_err
        shares = pending["shares"]
        async with httpx.AsyncClient(timeout=30) as c:
            # Ready → Approve → Execute
            await c.post(f"http://localhost:8000/api/recs/{rec_id}/ready")
            r = await c.post(f"http://localhost:8000/api/recs/{rec_id}/approve", json={"shares": shares})
            if r.status_code != 200:
                return f"Approve failed: {r.json().get('detail', r.text[:80])}"
            r = await c.post(f"http://localhost:8000/api/recs/{rec_id}/execute")
            if r.status_code != 200:
                return f"Execute failed: {r.json().get('detail', r.text[:80])}"
        _pop_pending(session_id)
        await event_bus.publish("voice_command", {"action": "execute", "recommendation_id": rec_id, "symbol": pending["symbol"]})
        return f"Done. Executed {pending['symbol']}, {shares:.0f} shares at ${pending['entry_price']:.2f}."

    elif pending["action"] == "sell":
        trade_id = pending["trade_id"]
        shares = pending["shares"]
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(f"http://localhost:8000/api/trades/{trade_id}/sell", json={"shares": shares})
        if r.status_code == 200:
            _pop_pending(session_id)
            result = r.json()
            pnl = result.get("pnl", 0)
            await event_bus.publish("voice_command", {"action": "sell", "trade_id": trade_id, "symbol": pending["symbol"]})
            return f"Sold {shares:.0f} shares of {pending['symbol']}. P&L ${pnl:+.2f}."
        return f"Sell failed: {r.text[:80]}"

    return "Unknown pending action."


async def _exec_cancel(session_id: str) -> str:
    pending = _pop_pending(session_id)
    if pending:
        return f"Cancelled {pending['action']} for {pending.get('symbol', 'unknown')}."
    return "Nothing was pending."


def _exec_portfolio() -> str:
    p = get_portfolio_summary()
    positions = get_positions()
    pos_text = ", ".join(f"{t['symbol']} {t.get('direction','')} {t.get('shares',0):.0f}sh" for t in positions[:5])
    return (
        f"Portfolio ${p['portfolio_value']:,.0f}, cash ${p['cash']:,.0f}, "
        f"P&L ${p['daily_change']:+,.0f} ({p['daily_change_pct']:+.1f}%). "
        f"{len(positions)} position{'s' if len(positions)!=1 else ''}"
        f"{': ' + pos_text if pos_text else ''}."
    )


def _exec_rec_detail(args: dict) -> str:
    rec_id = args.get("recommendation_id")
    if not rec_id:
        return "No recommendation_id."
    rec = get_recommendation(rec_id)
    if not rec:
        return "Recommendation not found."
    summary = get_summary(rec_id)
    parts = [f"{rec['symbol']} — {rec.get('direction','pending')}, conviction {rec.get('conviction','?')}/10."]
    if summary:
        if summary.get("bull_case"):
            parts.append(f"Bull: {summary['bull_case'][:100]}")
        if summary.get("bear_case"):
            parts.append(f"Bear: {summary['bear_case'][:100]}")
    return " ".join(parts)


def _exec_list_recs(session_id: str) -> str:
    recs = _dedupe_recommendations_by_symbol(list_recommendations(limit=20))
    if not recs:
        return "No recommendations. Say 'scan' to find earnings opportunities."
    lines = []
    last_items: list[dict] = []
    for r in recs:
        direction = r.get("direction") or "pending"
        conviction = r.get("conviction") or "?"
        status = r["status"].replace("_", " ")
        lines.append(f"{r['symbol']}: {direction}, conviction {conviction}/10, {status}")
        last_items.append({"type": "recommendation", "symbol": r["symbol"], "recommendation_id": r["id"]})
    _set_last_list(session_id, "ai", last_items[:5])
    return f"{len(recs)} recommendation{'s' if len(recs)!=1 else ''}: " + ". ".join(lines[:5])


def _exec_list_inbox_items(args: dict, session_id: str) -> str:
    tab = args.get("tab", "")
    try:
        limit = max(1, min(int(args.get("limit") or 5), 10))
    except Exception:
        limit = 5

    if tab == "ai":
        return _exec_list_recs(session_id)
    if tab == "positions":
        positions = get_positions()
        if not positions:
            return "No open positions."
        lines = []
        last_items: list[dict] = []
        for p in positions[:limit]:
            lines.append(f"{p['symbol']} {p.get('direction','')} {float(p.get('shares') or 0):.0f} shares, P&L ${float(p.get('unrealized_pnl') or 0):+.0f}")
            last_items.append({"type": "position", "symbol": p["symbol"], "trade_id": p["id"]})
        _set_last_list(session_id, "positions", last_items)
        return f"{len(positions)} position{'s' if len(positions)!=1 else ''}: " + ". ".join(lines)

    events = list_events(limit=100)
    if tab == "earnings":
        rows = [e for e in events if e.get("type") == "earnings"][:limit]
    elif tab == "news":
        rows = [e for e in events if e.get("type") not in {"earnings", "price_alert"}][:limit]
    else:
        rows = []
    if not rows:
        return f"No {tab} items right now."
    parts = []
    last_items: list[dict] = []
    for e in rows:
        label = e.get("symbol") or e.get("type") or "item"
        parts.append(f"{label}: {e.get('headline','')[:90]}")
        last_items.append({"type": tab[:-1] if tab.endswith("s") else tab, "symbol": e.get("symbol"), "event_id": e["id"]})
    _set_last_list(session_id, tab, last_items)
    return f"{len(rows)} {tab} item{'s' if len(rows)!=1 else ''}: " + ". ".join(parts)


async def _exec_ask_role(args: dict, session_id: str) -> str:
    rec_id = args.get("recommendation_id") or get_active_rec_id(session_id)
    role = args.get("role")
    question = (args.get("question") or "").strip()
    if not rec_id:
        return "No active recommendation. Navigate to a stock first."
    if not role or not question:
        return "Role and question are required."
    ctx_err = _validate_active_context(session_id, rec_id)
    if ctx_err:
        return ctx_err
    import httpx
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"http://localhost:8000/api/recs/{rec_id}/discuss", json={"message": f"@{role} {question}"})
    if r.status_code != 200:
        return f"Couldn't ask {role}: {r.text[:100]}"
    data = r.json()
    answer = (data.get("message_text") or "").strip()
    symbol = (get_recommendation(rec_id) or {}).get("symbol", "")
    return f"{role.replace('_',' ').title()} on {symbol}: {answer[:220]}"


async def _exec_scan() -> str:
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("http://localhost:8000/api/scan")
    if r.status_code == 200:
        data = r.json()
        count = len(data.get("results", []))
        await event_bus.publish("voice_command", {"action": "scan_complete", "count": count})
        return f"Scan complete. {count} candidate{'s' if count!=1 else ''} found. Analysis running in background."
    return "Scan failed."


async def _exec_ui(args: dict) -> str:
    action = args.get("action", "")
    value = args.get("value", "")
    await event_bus.publish("voice_command", {"action": action, "value": value})
    labels = {
        "show_earnings": "Showing earnings tab.",
        "show_ai": "Showing AI recommendations tab.",
        "show_news": "Showing news tab.",
        "open_settings": "Opening settings.",
        "close_settings": "Settings closed.",
        "open_help": "Opening help.",
        "close_help": "Help closed.",
        "scroll_down": "Scrolling down.",
        "scroll_up": "Scrolling up.",
        "filter_chat": f"Filtering chat to {value or 'all'}.",
        "end_call": "Ending call. Goodbye.",
        "mute": "Muted.",
        "unmute": "Unmuted.",
    }
    return labels.get(action, f"UI action: {action}")


def _exec_setting(args: dict) -> str:
    key = args.get("key", "")
    value = args.get("value", "")
    SAFE_KEYS = {"min_conviction_to_trade", "min_surprise_pct", "max_positions", "target_hold_days"}
    if key not in SAFE_KEYS:
        return f"Cannot change {key} by voice. Safe settings: {', '.join(SAFE_KEYS)}."
    set_strategy_setting(key, value)
    label = key.replace("_", " ")
    return f"Set {label} to {value}."


# ── Context builder ──

def build_voice_context(session_id: str) -> str:
    """Build the system prompt context block for the voice trader."""
    rec_id = get_active_rec_id(session_id)
    rec = get_recommendation(rec_id) if rec_id else None
    portfolio = get_portfolio_summary()
    positions = get_positions()
    summary = get_summary(rec_id) if rec_id else None

    parts = [
        "You are the Head Trader on Trading Desk AI. You lead a desk with three AI roles:",
        "- Research: analyses earnings quality, guidance, catalysts, counterpoints",
        "- Risk: challenges thesis, flags portfolio risk, recommends position sizing",
        "- Quant Pricing: sets entry zones, stop levels, target prices, volatility regime",
        "",
        "STRATEGY: PEAD V2 — post-earnings announcement drift. Scans run automatically every 30 min. EPS surprise >=10%, revenue beat required, top 2 candidates per scan, 10 trading day hold, conviction-based sizing.",
        "",
        "APP LAYOUT the user sees:",
        "- Left column has 3 tabs: Earnings (clickable, loads AI analysis), AI (recommendations to approve/reject), News (read-only headlines, clickable to read in centre)",
        "- Centre: trade summary + avatar (you) at top, desk chat below. When user reads news, it replaces the summary and chat switches to news discussion.",
        "- Right column: market lists with tabs — Open (positions), All (all tracked), Gainers, Losers, Active. Prices update live.",
        "- Header: Settings, Help buttons. Portfolio/Cash/P&L display.",
        "- Data flows in automatically — earnings scan, news, market movers. No manual scan button needed.",
        "",
        "RULES: Keep responses under 40 words. Use tools for ALL actions. Confirm before trades. When user asks about news, you may already have context from a system message. When asked about recommendations, use the list_recommendations tool. When user asks what is visible in a tab, use list_inbox_items. When user asks you to ask Quant, Risk, or Research something, use ask_role.",
    ]

    # All recommendations
    all_recs = list_recommendations(limit=20)
    actionable = [r for r in all_recs if r.get("direction") and r.get("direction") != "PASS"]
    if actionable:
        parts.append(f"\nALL RECOMMENDATIONS ({len(actionable)}):")
        for r in actionable[:5]:
            parts.append(f"  {r['symbol']}: {r.get('direction','?')} conviction {r.get('conviction','?')}/10, {r['status'].replace('_',' ')} (id: {r['id']})")
    elif all_recs:
        parts.append(f"\n{len(all_recs)} recommendations scanned but none actionable (all PASS or pending).")
    else:
        parts.append("\nNo recommendations yet. User should say 'scan' to find opportunities.")

    if rec:
        parts.append(f"\nACTIVE FOCUS: {rec['symbol']} — {rec.get('direction','pending')}, conviction {rec.get('conviction','?')}/10")
        parts.append(f"recommendation_id: {rec['id']}")
        parts.append(f"Status: {rec['status']}")
        if rec.get("entry_price"):
            parts.append(f"Entry: ${rec['entry_price']}, Stop: ${rec.get('stop_price','?')}, Target: ${rec.get('target_price','?')}")
        if rec.get("position_size_shares"):
            parts.append(f"Suggested shares: {rec['position_size_shares']}")
        if summary:
            if summary.get("bull_case"):
                parts.append(f"Research (bull): {summary['bull_case'][:150]}")
            if summary.get("bear_case"):
                parts.append(f"Risk (bear): {summary['bear_case'][:150]}")

    parts.append(f"\nPORTFOLIO: ${portfolio['portfolio_value']:,.0f} total, ${portfolio['cash']:,.0f} cash")
    if positions:
        for p in positions[:5]:
            parts.append(f"  Position: {p.get('direction','')} {p['symbol']} {p.get('shares',0):.0f}sh, P&L ${float(p.get('unrealized_pnl',0)):+.0f} (trade_id: {p['id']})")
    else:
        parts.append("  No open positions.")

    pending = _get_pending(session_id)
    if pending:
        parts.append(
            f"\nPENDING CONFIRMATION: {pending['action']} {pending.get('symbol','')} {pending.get('shares',0):.0f} shares. "
            "If the user says confirm/yes/go ahead/do it/proceed, call confirm_action immediately. "
            "Do not call approve_and_execute again while an action is pending. "
            "If the user says cancel/no/stop, call cancel_action."
        )

    return "\n".join(parts)


async def maybe_handle_direct_pending_intent(session_id: str, text: str) -> str | None:
    if not has_pending_action(session_id):
        return None
    lower = (text or "").strip().lower()
    confirm_words = {
        "confirm", "yes", "yes please", "yeah", "yep", "go ahead", "do it", "proceed",
        "execute it", "buy it", "sell it", "ok", "okay",
    }
    cancel_words = {"cancel", "no", "no thanks", "stop", "wait", "never mind", "don't"}
    if lower in confirm_words:
        return await _exec_confirm(session_id)
    if lower in cancel_words:
        return await _exec_cancel(session_id)
    return None


async def maybe_handle_direct_open_intent(session_id: str, text: str) -> str | None:
    lower = (text or "").strip().lower()
    open_words = {
        "look at it", "can we look at it", "discuss it", "can we discuss it",
        "open it", "select it", "show it", "let's discuss it", "lets discuss it",
        "the first one", "open the first one", "show the first one",
    }
    if lower not in open_words:
        return None
    ctx = _get_last_list(session_id)
    if not ctx:
        return None
    items = ctx.get("items") or []
    if not items:
        return None
    first = items[0]
    if first.get("recommendation_id"):
        return await _exec_navigate({"symbol": first.get("symbol", "")}, session_id)
    if first.get("event_id"):
        symbol = first.get("symbol") or ""
        await event_bus.publish("voice_command", {"action": "open_event", "event_id": first["event_id"], "tab": "news" if ctx.get("kind") == "news" else "earnings", "symbol": symbol})
        return f"Opened {symbol or 'that item'}."
    if first.get("trade_id"):
        return f"I can discuss {first.get('symbol','that position')}. Ask me whether to sell or hold it."
    return None
