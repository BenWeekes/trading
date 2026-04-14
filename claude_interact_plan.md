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
                      → /api/recs/{id}/approve + /api/recs/{id}/execute
                      → backend computes shares from $10k / live price
                          ↓
                    Result fed back to LLM
                          ↓
                    LLM speaks confirmation → Agora → TTS → user
```

Context pushed to the running agent via **Agora Agent Update API** on navigation, analysis completion, trade execution, and position changes.

## Tool Definitions

### Trading Actions

All actions use `recommendation_id` or `trade_id` (from context), never symbol alone. Backend computes exact shares — LLM expresses intent only.

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `approve_and_execute` | "buy", "execute", "go ahead", "do it" | `recommendation_id`, `sizing_intent` (suggested/full/half/custom_dollars/custom_shares), `amount?` |
| `approve_only` | "approve but don't execute yet" | `recommendation_id`, `sizing_intent`, `amount?` |
| `reject_recommendation` | "reject", "pass", "skip", "no thanks" | `recommendation_id`, `reason` |
| `sell_position` | "sell", "close", "exit", "take profit" | `trade_id`, `sizing_intent` (all/half/custom_shares/custom_dollars), `amount?` |
| `change_position_size` | "make it 100 shares", "reduce size" | `recommendation_id`, `sizing_intent`, `amount?` |
| `confirm_action` | "confirm", "yes" (after confirmation prompt) | — |
| `cancel_action` | "cancel", "no", "wait" (after confirmation prompt) | — |

**Sizing intent** resolved by backend:
- `suggested` → conviction-scaled from recommendation
- `full` → max per risk settings
- `half` → 50% of suggested
- `custom_dollars` → amount / live_price, capped by risk
- `custom_shares` → exact, capped by risk

**Confirmation required** for all trade actions. LLM says "About to buy 52 shares of NVDA at $192, roughly $10k. Confirm?" then waits.

### Navigation & Info

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `navigate_to_symbol` | "show me NVDA", "switch to", "what about" | `symbol` |
| `get_portfolio_status` | "status", "how are we doing", "cash?" | — |
| `get_recommendation_detail` | "what did research say", "what's the risk view" | `symbol` |
| `scan_earnings` | "scan", "find opportunities" | — |
| `ask_role` | "ask research about...", "what does risk think" | `role`, `question` |

### UI Control

| Tool | Triggers On | Parameters |
|------|-------------|-----------|
| `show_events_tab` | "show events", "show news" | — |
| `show_recommendations_tab` | "show recs", "what trades pending" | — |
| `open_settings` | "open settings", "configure" | — |
| `close_settings` | "close settings" | — |
| `open_help` | "help", "how does this work" | — |
| `close_help` | "close help", "got it" | — |
| `update_setting` | "change conviction to 8", "set risk to 2%" | `key`, `value` |
| `filter_chat_by_role` | "show only risk messages", "show all" | `role` (or "all") |
| `end_voice_call` | "end call", "hang up", "goodbye" | — |
| `mute_microphone` | "mute", "unmute" | `muted` (bool) |

## Context via Agent Update API

**Endpoint:** `POST /api/conversational-ai-agent/v2/projects/{APP_ID}/agents/{agent_id}/update`

**Pushed on:** symbol navigation, analysis completion, trade execution, position changes.

**Content:** Active recommendation_id, recommendation state, latest 1 message per role (with timestamp), portfolio summary, available actions.

**Symbol change rule:** Full context reset — new system prompt + clear agent conversation history. Prevents "do it" from attaching to the wrong stock.

**Freshness rule:** Latest 1 message per role per recommendation, timestamped. Background analysis updates push new Agent Update immediately.

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

1. Build `trading_tools` module for server-custom-llm (tool schemas + handlers that call our backend API)
2. Build context builder in our backend (assembles state for Agent Update payloads)
3. Add Agent Update API client to agora_bridge.py
4. Lift InboxTabs + GroupChat state to page level
5. **Phase A:** Deploy read-only tools, test navigation + info + UI control
6. **Phase B:** Deploy trade action tools with confirmation flow
7. Push context on navigation + state changes via Agent Update
8. **Phase C:** Disable regex fallback behind flag
9. End-to-end test: full voice-operated session from scan to trade to exit
