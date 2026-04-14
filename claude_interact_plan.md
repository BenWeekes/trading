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
  }
]
```

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

### Open Questions

1. Should the Trader LLM use the same model as the text Trader role (gpt-5.1) or a faster model for voice responsiveness?
2. Should tool calls require verbal confirmation ("I'm about to buy 52 shares of NVDA at $192. Confirm?") before executing?
3. Should the context include the full role message text or just structured summaries?
4. Max context size — how many role messages to include before truncating?
