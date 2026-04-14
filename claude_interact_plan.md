# Voice + LLM Interaction Plan

## Problem

The current voice command system uses regex keyword matching to intercept commands before the LLM. This breaks when users speak naturally:
- "execute around 10k USD worth" → not matched (expects exact "execute")
- "can you buy me 50 shares of NVDA" → not matched
- "what did risk say about this?" → goes to LLM but LLM has no context of what risk said

Three fundamental issues:
1. **Regex interception is brittle** — natural speech doesn't match exact patterns
2. **LLM has no tools** — it can't actually do anything, just talk
3. **LLM has no context** — it doesn't know what the other roles said or what's on screen

## Solution: LLM Function Calling

Replace regex interception with **OpenAI function calling (tools)**. The Trader LLM gets a set of defined functions it can call. When the user says "execute around 10k of NVDA," the LLM decides to call `execute_trade(symbol="NVDA", shares=50)` — no regex needed.

### Architecture

```
User speaks: "buy me about 10k worth of NVDA"
     ↓
Agora transcribes → POST /api/agora/chat/completions
     ↓
Our endpoint builds context:
  - Current symbol & recommendation
  - Role analysis summaries
  - Portfolio state
  - Available tools
     ↓
Forward to OpenAI with tools defined
     ↓
OpenAI returns: tool_call: approve_and_execute(symbol="NVDA", shares=52)
     ↓
Our endpoint executes the function
     ↓
Returns spoken response: "Approved and executing BUY NVDA, 52 shares at $192."
     ↓
Also publishes SSE events → UI updates
```

### Defined Functions (Tools)

```json
[
  {
    "name": "navigate_to_symbol",
    "description": "Switch the active view to a specific stock ticker. Use when user says 'show me', 'switch to', 'what about', etc.",
    "parameters": {
      "symbol": { "type": "string", "description": "Stock ticker e.g. NVDA, AAPL" }
    }
  },
  {
    "name": "approve_and_execute",
    "description": "Approve and immediately execute a trade. Use when user says 'buy', 'execute', 'go ahead', 'do it', 'approve and execute'. Calculate shares from dollar amount if user specifies dollars.",
    "parameters": {
      "symbol": { "type": "string", "description": "Stock ticker. Use current symbol if not specified." },
      "shares": { "type": "number", "description": "Number of shares. Calculate from dollar amount / entry price if user says a dollar amount." },
      "notes": { "type": "string", "description": "Optional notes for the approval record." }
    }
  },
  {
    "name": "approve_only",
    "description": "Approve a recommendation without executing. Use when user says 'approve' without 'execute'.",
    "parameters": {
      "symbol": { "type": "string" },
      "shares": { "type": "number" }
    }
  },
  {
    "name": "reject_recommendation",
    "description": "Reject the current recommendation. Use when user says 'reject', 'pass', 'skip', 'no thanks'.",
    "parameters": {
      "symbol": { "type": "string" },
      "reason": { "type": "string", "description": "Brief reason for rejection." }
    }
  },
  {
    "name": "sell_position",
    "description": "Sell/close an open position. Use when user says 'sell', 'close', 'exit', 'take profit', 'cut losses'.",
    "parameters": {
      "symbol": { "type": "string" },
      "shares": { "type": "number", "description": "Shares to sell. Use all shares if user says 'all' or 'everything'." }
    }
  },
  {
    "name": "get_portfolio_status",
    "description": "Get portfolio summary. Use when user asks about overall status, P&L, positions, cash.",
    "parameters": {}
  },
  {
    "name": "get_recommendation_detail",
    "description": "Get full detail on a recommendation including what all roles said. Use when user asks 'what did research say', 'what's the risk view', 'show me the analysis'.",
    "parameters": {
      "symbol": { "type": "string" }
    }
  },
  {
    "name": "scan_earnings",
    "description": "Run an earnings scan. Use when user says 'scan', 'find opportunities', 'what's new'.",
    "parameters": {}
  },
  {
    "name": "change_position_size",
    "description": "Change the number of shares for approval. Use when user says 'make it 100 shares', 'reduce to 50', 'increase size'.",
    "parameters": {
      "symbol": { "type": "string" },
      "shares": { "type": "number" }
    }
  },
  {
    "name": "confirm_action",
    "description": "User confirms a pending action. Use when user says 'confirm', 'yes', 'go ahead', 'do it' after a confirmation prompt.",
    "parameters": {}
  },
  {
    "name": "cancel_action",
    "description": "User cancels a pending action. Use when user says 'cancel', 'no', 'wait', 'stop' after a confirmation prompt.",
    "parameters": {}
  },

  // ── UI Navigation & Control ──

  {
    "name": "show_events_tab",
    "description": "Switch the left panel to the Events tab. Use when user says 'show events', 'show news', 'what happened today'.",
    "parameters": {}
  },
  {
    "name": "show_recommendations_tab",
    "description": "Switch the left panel to the Recommendations tab. Use when user says 'show recommendations', 'show recs', 'what trades are pending'.",
    "parameters": {}
  },
  {
    "name": "open_settings",
    "description": "Open the strategy settings panel. Use when user says 'open settings', 'show settings', 'change settings', 'configure'.",
    "parameters": {}
  },
  {
    "name": "close_settings",
    "description": "Close the strategy settings panel. Use when user says 'close settings', 'done with settings'.",
    "parameters": {}
  },
  {
    "name": "open_help",
    "description": "Open the help panel. Use when user says 'help', 'show help', 'how does this work', 'what can you do'.",
    "parameters": {}
  },
  {
    "name": "close_help",
    "description": "Close the help panel. Use when user says 'close help', 'got it', 'done'.",
    "parameters": {}
  },
  {
    "name": "update_setting",
    "description": "Change a strategy setting. Use when user says 'change conviction threshold to 8', 'set risk per trade to 2 percent', 'increase max positions to 20'.",
    "parameters": {
      "key": { "type": "string", "description": "Setting key e.g. min_conviction_to_trade, risk_per_trade_pct, max_positions, min_surprise_pct" },
      "value": { "type": "string", "description": "New value as string." }
    }
  },
  {
    "name": "ask_role",
    "description": "Ask a specific role a question in the desk chat. Use when user says 'ask research about...', 'what does risk think about...', 'get quant's view on...'.",
    "parameters": {
      "role": { "type": "string", "enum": ["research", "risk", "quant_pricing", "trader"], "description": "Which role to ask." },
      "question": { "type": "string", "description": "The question to send." }
    }
  },
  {
    "name": "filter_chat_by_role",
    "description": "Filter the desk chat to show only one role's messages. Use when user says 'show me only risk messages', 'filter to research', 'show all messages'.",
    "parameters": {
      "role": { "type": "string", "description": "Role name to filter by, or 'all' to show everything." }
    }
  },
  {
    "name": "start_voice_call",
    "description": "Start the trader avatar voice call. Use when user says 'start call', 'connect avatar'. Usually already active if user is speaking.",
    "parameters": {}
  },
  {
    "name": "end_voice_call",
    "description": "End the trader avatar voice call. Use when user says 'end call', 'disconnect', 'hang up', 'goodbye'.",
    "parameters": {}
  },
  {
    "name": "mute_microphone",
    "description": "Mute or unmute the user's microphone. Use when user says 'mute', 'unmute', 'toggle mute'.",
    "parameters": {
      "muted": { "type": "boolean", "description": "True to mute, false to unmute." }
    }
  }
]
```

### Full UI Control Summary

Every UI action is a function call. The user never needs to touch the mouse:

| Voice Command | Tool Called | UI Effect |
|---------------|-----------|-----------|
| "Show me NVDA" | `navigate_to_symbol(NVDA)` | Switches active stock, loads context |
| "Show events" | `show_events_tab()` | Left panel → Events tab |
| "Show recommendations" | `show_recommendations_tab()` | Left panel → Recs tab |
| "Open settings" | `open_settings()` | Settings modal opens |
| "Close settings" | `close_settings()` | Settings modal closes |
| "Set conviction threshold to 8" | `update_setting(min_conviction_to_trade, 8)` | Changes setting |
| "Open help" | `open_help()` | Help modal opens |
| "Close help" | `close_help()` | Help modal closes |
| "Buy 50 shares of NVDA" | `approve_and_execute(NVDA, 50)` | Confirmation prompt, then trade |
| "Confirm" | `confirm_action()` | Executes pending trade |
| "Cancel" | `cancel_action()` | Cancels pending action |
| "Sell all PLTR" | `sell_position(PLTR, all)` | Confirmation prompt, then close |
| "What did research say?" | `get_recommendation_detail(NVDA)` | Speaks role analysis |
| "How's the portfolio?" | `get_portfolio_status()` | Speaks cash, P&L, positions |
| "Ask risk about sector exposure" | `ask_role(risk, sector exposure?)` | Posts to desk chat, speaks response |
| "Filter chat to research only" | `filter_chat_by_role(research)` | Chat filter applied |
| "Show all messages" | `filter_chat_by_role(all)` | Chat filter cleared |
| "Scan for opportunities" | `scan_earnings()` | Runs scan, speaks results |
| "Reduce to 30 shares" | `change_position_size(NVDA, 30)` | Updates share count in trade panel |
| "Reject this" | `reject_recommendation(NVDA, not convinced)` | Rejects rec |
| "End call" | `end_voice_call()` | Disconnects avatar |
| "Mute" | `mute_microphone(true)` | Mutes mic |

### Frontend SSE Handler for UI Commands

All UI control tools publish a `voice_command` SSE event with the action. The frontend handles each:

```typescript
// In the SSE handler
if (type === "voice_command") {
  switch (p.action) {
    case "navigate":       setActiveRec(findRec(p.symbol)); break;
    case "switch_tab":     setActiveTab(p.tab); break;
    case "open_settings":  setSettingsOpen(true); break;
    case "close_settings": setSettingsOpen(false); break;
    case "open_help":      setHelpOpen(true); break;
    case "close_help":     setHelpOpen(false); break;
    case "filter_chat":    setChatFilter(p.role); break;
    case "mute":           agoraToggleMute(); break;
    case "end_call":       agoraLeave(); break;
    // ... trade actions handled as before
  }
}
```

### Implementation Complexity

This is straightforward because:
1. **All the backend actions already exist** — approve, execute, sell, scan, settings CRUD, portfolio query are all working API endpoints
2. **All the UI state is already in React** — settingsOpen, helpOpen, activeTab, chatFilter are all existing state variables
3. **SSE handler already exists** — just add more cases
4. The only new code is:
   - Tool definitions (JSON schema, ~200 lines)
   - Tool executor (switch/case mapping tool names to existing functions, ~150 lines)
   - SSE cases for UI commands (~30 lines)
   - Context builder for Agent Update API (~100 lines)
   - Confirmation state management (~50 lines)

### Context Injection

When the `/api/agora/chat/completions` endpoint receives a request, it builds a rich system prompt with current state:

```
You are the Head Trader on a trading desk. You have these tools to control the trading platform.

CURRENT STATE:
- Active symbol: NVDA
- Recommendation: BUY, conviction 8/10
- Entry: $192.50, Stop: $183, Target: $212
- Status: awaiting_user_feedback
- Shares suggested: 52 (~$10,010)

ROLE ANALYSIS SUMMARY:
- Research: Revenue-driven beat, guidance raised. Confidence 0.86.
- Risk: Top risks: gap reversal, sector crowding. Size 0.75x. Accept with tight stops.
- Quant: Fair value $210. Signal STRONG. Entry 188-195, stop 183, target 208-220.

PORTFOLIO:
- Cash: $89,500
- 1 open position: PLTR BUY 200sh @ $25.30, P&L +$140
- Portfolio value: $95,200

PENDING RECOMMENDATIONS:
- NVDA: BUY 8/10 (awaiting feedback)
- PLTR: already holding

Use tools to take actions. Always confirm what you're doing before executing.
Keep spoken responses under 40 words.
```

### Context Reset on Symbol Change

When the user says "show me AAPL" or navigates to a different stock:
1. Call `navigate_to_symbol(symbol="AAPL")`
2. Update the system prompt with AAPL's recommendation, role analysis, and position data
3. The conversation history stays (Agora manages it), but the context block updates

This means the Trader LLM always knows what's on screen and what the other roles said — without needing to call them in real time.

### Role Messages in Context

When a recommendation is loaded, inject the latest role messages as a summary:

```
RESEARCH on NVDA (2 min ago):
"Revenue-driven beat with raised guidance. Catalyst: datacenter AI demand. Risk: supply constraints. Confidence 0.86."

RISK on NVDA (2 min ago):
"Top risks: gap reversal, sector crowding. Size 0.75x. Accept with tight stops."

QUANT on NVDA (2 min ago):
"Fair value $210. Signal STRONG. Entry 188-195, stop 183, target 208-220."

TRADER RECOMMENDATION:
"BUY NVDA. Conviction 8/10. Entry 192, target 212, stop 183."
```

This gives the voice trader full awareness of the desk discussion without re-running the roles.

### Implementation Steps

1. **Define tool schemas** as OpenAI function definitions
2. **Build tool executor** — maps function names to backend actions (approve, execute, sell, navigate, etc.)
3. **Build context builder** — assembles current state, role summaries, portfolio into a system prompt
4. **Update `/api/agora/chat/completions`** — inject tools + context into the OpenAI call, handle tool_call responses
5. **Handle tool results** — execute the action, publish SSE events, return spoken confirmation
6. **Remove regex voice commands** — the LLM handles all intent detection now
7. **Test with streaming** — Agora expects streaming responses, tool calls need to work within that

### What This Enables

- "Buy me about 10k worth of NVDA" → LLM calculates shares, calls approve_and_execute
- "What did risk say?" → LLM reads from context, no tool call needed
- "Show me META and tell me what you think" → navigate + speak from context
- "Sell half my PLTR" → LLM calculates half of 200 = 100, calls sell_position
- "How's the portfolio doing?" → calls get_portfolio_status, speaks summary
- "Scan for new opportunities" → calls scan_earnings
- "Reduce the size to 30 shares" → calls change_position_size
- Any natural phrasing works — the LLM interprets intent, not regex

### Streaming + Tool Calls

Agora expects SSE streaming. When the LLM returns a tool_call instead of text:
1. Execute the tool
2. Feed the result back to the LLM as a tool_result message
3. The LLM generates a spoken response ("Done. Bought 52 shares of NVDA at $192.")
4. Stream that response back to Agora

This is a two-turn LLM call: first call returns tool_call, second call (with tool result) returns the spoken response.

### Resolved Decisions

1. **Verbal confirmation required** before executing trades. LLM says "I'm about to buy 52 shares of NVDA at $192. Say confirm to proceed." Then executes on confirmation.
2. **Agora handles TTS** — we don't control voice model, just the text content. TTS vendor/voice is set in the Agora backend .env profile.
3. **Full role messages in context** — not just summaries. The Trader LLM should see exactly what Research, Risk, and Quant said.

### Agent Update API — Mid-Call Context Injection

Instead of stuffing all context into every LLM request, use the **Agora Agent Update API** to push context updates to the running agent. This is the same pattern used in the Shen.AI recipe for injecting camera vitals into the LLM prompt.

**Endpoint:** `POST /api/conversational-ai-agent/v2/projects/{APP_ID}/agents/{agent_id}/update`

**When to push updates:**
- User navigates to a new stock → push that stock's role analysis + recommendation
- Role analysis completes in background → push updated analysis
- Trade executes → push updated portfolio state
- Position closed/opened → push updated positions

**Payload:**
```json
{
  "system_messages": [
    {
      "role": "system",
      "content": "[Trading Desk Context Update]\n\nACTIVE SYMBOL: NVDA\n\nRECOMMENDATION: BUY, conviction 8/10\nEntry: $192, Stop: $183, Target: $212\nStatus: awaiting_user_feedback\nShares: 52 (~$10,010)\n\nRESEARCH: Revenue-driven beat with raised guidance...\nRISK: Gap reversal risk, sector crowding. Size 0.75x...\nQUANT: Fair value $210. Signal STRONG. Entry 188-195...\n\nPORTFOLIO: Cash $89,500, 1 position (PLTR +$140), Total $95,200"
    }
  ]
}
```

**Implementation flow:**
```
1. User clicks on NVDA in Events tab
   → Frontend calls API to switch active rec
   → Backend loads NVDA context (rec + role messages + portfolio)
   → Backend calls Agora Agent Update API with new system prompt
   → Next voice turn has full NVDA context

2. Background analysis completes for META
   → Backend publishes SSE (already done)
   → If META is the active symbol, also push Agent Update

3. User says "approve and execute"
   → LLM calls approve_and_execute tool
   → Backend executes, updates portfolio
   → Backend pushes Agent Update with new portfolio state
   → LLM confirms: "Done. Bought 52 shares at $192. Cash now $79,500."
```

**Required:** The running agent_id must be stored (already in our AvatarSession). The APP_ID and auth credentials come from the Agora backend config.

### Implementation Steps (Updated)

1. **Define tool schemas** as OpenAI function definitions
2. **Build tool executor** — maps function names to backend actions
3. **Build context builder** — assembles current state, full role messages, portfolio
4. **Add Agent Update API client** to agora_bridge.py
5. **Update `/api/agora/chat/completions`** — inject tools into the OpenAI call, handle tool_call responses with two-turn flow
6. **Push context on navigation** — when active stock changes, call Agent Update
7. **Push context on state changes** — analysis complete, trade executed, position closed
8. **Remove regex voice commands** — LLM handles all intent via tools
9. **Add confirmation flow** — tool calls for trades return "confirm?" before executing
10. **Test streaming + tool calls** — ensure Agora SSE format works with two-turn tool flow

---

## Codex Review — Accepted Changes

### 1. Use IDs not symbols for action tools — ACCEPTED

All action tools (`approve_and_execute`, `sell_position`, `reject_recommendation`, `change_position_size`) must use `recommendation_id` or `trade_id` as the execution identity, not symbol. Multiple recs/positions for the same ticker is a real scenario.

**How it works:** The LLM still references symbols in natural language ("buy NVDA"). The context block includes the active `recommendation_id`. The tool executor resolves symbol → active recommendation_id from context. If ambiguous, the LLM asks which one.

**Updated tool parameters:**
```json
{
  "name": "approve_and_execute",
  "parameters": {
    "recommendation_id": { "type": "string", "description": "From context. Use active recommendation_id." },
    "amount_dollars": { "type": "number", "description": "Approximate dollar amount. Backend calculates exact shares." },
    "notes": { "type": "string" }
  }
}
```

### 2. Reset conversation on symbol change — ACCEPTED

When navigating to a new stock:
1. Push new context via Agent Update API (already planned)
2. **Also reset the agent conversation history** — clear message history so "do it" or "sell half" can't attach to the previous symbol
3. The context block includes `active_recommendation_id` — all action tools must match this ID or be rejected

**Rule:** Every action tool response includes the `recommendation_id` it acted on. If it doesn't match the current active ID, the backend rejects with "Recommendation has changed. Please confirm the current symbol."

### 3. Backend computes shares, not LLM — ACCEPTED

The LLM expresses **intent** ("about $10k", "half my position", "full size"), not exact share counts. The backend resolves intent to shares using:
- Live market price from FMP
- Risk settings (risk_per_trade_pct, conviction multiplier)
- Current position size (for "sell half")
- Portfolio cash (for "about $10k")

**Updated tool parameters:**
```json
{
  "name": "approve_and_execute",
  "parameters": {
    "recommendation_id": { "type": "string" },
    "sizing_intent": { "type": "string", "enum": ["suggested", "full", "half", "quarter", "custom_dollars", "custom_shares"] },
    "amount": { "type": "number", "description": "Dollar amount or share count depending on sizing_intent. Only needed for custom_dollars or custom_shares." },
    "notes": { "type": "string" }
  }
}
```

The backend maps:
- `"suggested"` → uses conviction-scaled position from recommendation
- `"full"` → max size per risk settings
- `"half"` → 50% of suggested
- `"custom_dollars"` → amount / live_price, capped by risk limits
- `"custom_shares"` → exact shares, capped by risk limits

### 4. Lift internal component state for voice control — ACCEPTED

InboxTabs tab state and GroupChat role filter state must be lifted to the page level and passed as props. This is real work (~30 min), not just "add SSE cases."

**Changes needed:**
- `InboxTabs`: accept `activeTab` + `onTabChange` props instead of internal useState
- `GroupChat`: accept `roleFilter` + `onRoleFilterChange` props instead of internal useState  
- `page.tsx`: add `activeTab` and `chatRoleFilter` state, pass down + handle in SSE

### 5. Role message freshness rules — ACCEPTED (simplified)

**Rule: latest 1 message per role per recommendation, with timestamp.**

When building context for Agent Update:
- For each role (research, risk, quant_pricing, trader): include the most recent `message_text` for the active recommendation
- Include the timestamp so the LLM knows how fresh it is
- If analysis updates mid-call (background scan completes), push new Agent Update immediately
- If active recommendation changes, full context reset (see #2)

**Not doing:** Version numbering, conflict resolution between multiple analysis passes, or complex staleness rules. Keep it simple — latest message wins, timestamp for awareness.

### 6. Staged migration from regex to tool-calling — ACCEPTED

**Phase A:** Keep regex fallback. Add tool-calling for read-only/navigation tools only (navigate, show tabs, open help/settings, portfolio status, recommendation detail). Regex still handles trade actions.

**Phase B:** Add tool-calling for trade actions (approve, execute, sell, reject) with confirmation flow. Regex remains as fallback for unrecognized intents.

**Phase C:** Remove regex parsing. All intent handled by LLM tools. Regex module stays in codebase but is disabled behind a feature flag.

**Updated implementation steps:**
1. Define tool schemas
2. Build tool executor
3. Build context builder + Agent Update client
4. **Phase A:** Ship read-only tools (navigate, UI control, info queries)
5. **Phase B:** Ship trade action tools with confirmation
6. Lift component state for voice-controlled tabs/filters
7. Push context on navigation + state changes
8. **Phase C:** Disable regex fallback behind flag
9. Test streaming + tool calls end-to-end

---

## Codex Points Not Accepted

### None rejected outright

All 6 points were valid and accepted. The only adjustment was simplifying #5 (role message freshness) — Codex suggested versioning rules, but "latest message per role with timestamp" is sufficient for this stage. If we find stale context is a real problem in testing, we add versioning then.

---

## Architecture Update: server-custom-llm

The Agora `server-custom-llm` project already has full tool calling support:
- Accepts tool definitions in requests
- Accumulates streaming tool_call fragments
- Executes tools server-side with multi-pass loop (up to 5 rounds)
- Extensible tool registry via modules

**Our approach:** Build a `trading_tools` module for server-custom-llm that:
1. Registers all trading tool definitions (navigate, approve, sell, etc.)
2. Each tool handler calls our trading backend API endpoints
3. Context injected via Agent Update API, not per-request stuffing
4. server-custom-llm handles the streaming + tool execution loop — we don't need to build that

**Flow:**
```
User speaks → Agora → server-custom-llm (with trading_tools module)
                          ↓
                    OpenAI with tools defined
                          ↓
                    tool_call: approve_and_execute(rec_id, "custom_dollars", 10000)
                          ↓
                    trading_tools module:
                      → calls backend /api/recs/{id}/approve
                      → backend computes shares from $10k / live price
                      → calls backend /api/recs/{id}/execute
                      → returns: "Approved BUY NVDA 52 shares at $192.50"
                          ↓
                    LLM speaks: "I've approved buying 52 shares of NVDA at $192.50.
                                 That's about $10,010. Cash is now $79,490."
```
