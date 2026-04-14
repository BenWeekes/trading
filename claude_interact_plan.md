# Voice Interaction Plan

## Problem

Regex command matching fails with natural speech ("execute around 10k worth" doesn't match "execute"). The LLM has no tools to act with and no awareness of what other roles said.

## Solution

Use **OpenAI function calling via server-custom-llm** (which already supports tool definitions, streaming accumulation, multi-pass execution). Build a `trading_tools` module that registers our functions.

## Architecture

```
User speaks → Agora → server-custom-llm (trading_tools module)
                          ↓
                    OpenAI with tools + context
                          ↓
                    tool_call: approve_and_execute(rec_id, "custom_dollars", 10000)
                          ↓
                    trading_tools calls our backend API
                      → /api/recs/{id}/ready + /approve + /execute
                      → backend enforces state machine at each step
                      → backend computes shares from $10k / live price
                          ↓
                    Result fed back to LLM
                          ↓
                    LLM speaks confirmation → Agora → TTS → user
```

Context pushed to the running agent via **Agora Agent Update API** on navigation, analysis completion, trade execution, and position changes.

## Tool Definitions

### Trading Actions

All actions use `recommendation_id` or `trade_id` (from context), never symbol alone. Backend computes exact shares — LLM expresses intent only. **All tools call existing backend API endpoints which enforce the recommendation state machine** — the tool layer cannot bypass state transitions.

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `approve_and_execute` | "buy", "execute", "go ahead", "do it" | `recommendation_id`, `sizing_intent`, `amount?` |
| `approve_only` | "approve but don't execute yet" | `recommendation_id`, `sizing_intent`, `amount?` |
| `reject_recommendation` | "reject", "pass", "skip", "no thanks" | `recommendation_id`, `reason` |
| `sell_position` | "sell", "close", "exit", "take profit" | `trade_id`, `sizing_intent`, `amount?` |
| `change_position_size` | "make it 100 shares", "reduce size" | `recommendation_id`, `sizing_intent`, `amount?` |
| `confirm_action` | "confirm", "yes" (after confirmation prompt) | — |
| `cancel_action` | "cancel", "no", "wait" (after confirmation prompt) | — |

**Sizing intent** (resolved by backend, not LLM):
- `suggested` → conviction-scaled from recommendation
- `full` → max per risk settings
- `half` → 50% of suggested
- `custom_dollars` → amount / live_price, capped by risk
- `custom_shares` → exact, capped by risk

**State machine enforcement:** `approve_and_execute` calls `/ready` → `/approve` → `/execute` in sequence. If the rec is in `observing` or `under_discussion`, the backend rejects. The tool returns the error and the LLM tells the user "That recommendation isn't ready for approval yet."

**Active context validation:** Every action tool must check that its `recommendation_id` matches the current `active_recommendation_id` from context. If stale (user navigated away), reject with "Context has changed — you're now looking at {new_symbol}." This is enforced in the tool executor, not by the LLM.

### Confirmation Flow

**Pending action model:** In-memory dict keyed by `agent_session_id` (dev-only — production must use Redis or DB-backed session state for multi-process/restart safety):
```python
pending_voice_actions = {
    "session_abc": {
        "action": "approve_and_execute",
        "recommendation_id": "rec_123",
        "sizing_intent": "custom_dollars",
        "amount": 10000,
        "resolved_shares": 52,
        "resolved_price": 192.50,
        "created_at": "2026-04-14T12:00:00Z",
        "ttl_seconds": 30
    }
}
```
- TTL: 30 seconds. Expires silently — LLM says "That timed out, say it again if you still want to."
- `confirm_action` checks session has a pending action, validates it hasn't expired, executes once, then deletes it.
- Duplicate confirms rejected — action deleted after first execution.

### Navigation & Info

All recommendation-scoped tools use `recommendation_id`, not symbol. `navigate_to_symbol` is the only tool that takes a raw symbol — it resolves to the active recommendation.

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `navigate_to_symbol` | "show me NVDA", "switch to", "what about" | `symbol` |
| `get_portfolio_status` | "status", "how are we doing", "cash?" | — |
| `get_recommendation_detail` | "what did research say", "what's the risk view" | `recommendation_id` |
| `scan_earnings` | "scan", "find opportunities" | — |
| `ask_role` | "ask research about...", "what does risk think" | `role`, `recommendation_id`, `question` |

### UI Control

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `show_events_tab` | "show events", "show news" | — |
| `show_recommendations_tab` | "show recs", "what trades pending" | — |
| `open_settings` | "open settings", "configure" | — |
| `close_settings` | "close settings" | — |
| `open_help` | "help", "how does this work" | — |
| `close_help` | "close help", "got it" | — |
| `update_setting` | "change conviction to 8" | `key`, `value` |
| `filter_chat_by_role` | "show only risk messages", "show all" | `role` (or "all") |
| `end_voice_call` | "end call", "hang up", "goodbye" | — |
| `mute_microphone` | "mute", "unmute" | `muted` (bool) |

**`update_setting` constraints:**
- Allowlist of voice-safe settings: `min_conviction_to_trade`, `min_surprise_pct`, `max_positions`, `target_hold_days`
- Risk-affecting settings (`risk_per_trade_pct`, `stop_fixed_pct`, `max_gross_exposure_pct`) require verbal confirmation before applying
- Invalid keys or out-of-range values rejected by backend with error message
- LLM speaks back what was changed: "Set minimum conviction to 8 out of 10."

## Context via Agent Update API

**Endpoint:** `POST /api/conversational-ai-agent/v2/projects/{APP_ID}/agents/{agent_id}/update`

**Pushed on:** symbol navigation, analysis completion, trade execution, position changes.

**Content:** Active `recommendation_id`, recommendation state + direction + conviction, latest 1 message per role (with timestamp), portfolio summary, available actions for current state.

**Symbol change:** Push new context via Agent Update. Do NOT restart agent or clear history — `max_history: 32` handles natural rolloff. The context block always has the current `recommendation_id`, and all action tools validate against it. Old conversation about a different stock becomes irrelevant as new context overwrites.

**Freshness:** Latest 1 message per role per recommendation, timestamped. Background analysis updates push new Agent Update immediately if it's the active symbol.

## Frontend Changes Required

Lift internal state to page level for voice control:
- `InboxTabs`: accept `activeTab` + `onTabChange` props (currently internal useState)
- `GroupChat`: accept `roleFilter` + `onRoleFilterChange` props (currently internal useState)
- `page.tsx`: add `activeTab`, `chatRoleFilter` state, handle `voice_command` SSE events

## Migration Stages

**Phase A:** Read-only tools + regex fallback. Ship: navigate, tabs, help, settings, portfolio status, recommendation detail. Regex still handles trades.

**Phase B:** Trade action tools with confirmation. Ship: approve, execute, sell, reject, size change. Regex remains as fallback.

**Phase C:** Disable regex behind feature flag. All intent via LLM tools.

## Implementation Steps

1. Build `trading_tools` module for server-custom-llm (tool schemas + handlers calling our backend API)
2. Build context builder in our backend (assembles state for Agent Update payloads)
3. Add Agent Update API client to agora_bridge.py
4. Lift InboxTabs + GroupChat state to page level
5. **Phase A:** Deploy read-only tools, test navigation + info + UI control
6. **Phase B:** Deploy trade action tools with confirmation flow + pending action model
7. Push context on navigation + state changes via Agent Update
8. **Phase C:** Disable regex fallback behind flag
9. End-to-end test: full voice-operated session from scan to trade to exit
