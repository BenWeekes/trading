# Weekes AATF — Trading Platform Plan

## Last updated: 2026-04-11 (v6 — final, build-ready)

---

## 1. What This App Is

**Weekes AI Assisted Trading Fund (AATF)** is a multi-role AI trading workstation where specialised AI roles — Research, Quant Pricing, Risk, and Trader — each maintain their own context and session, analyse market events, deliberate, and present trade recommendations to a human operator for final approval before execution.

This is not "three AI labels on a stock card." It is a stateful decision system with four role views, a live event feed, and an explicit approval workflow. The AI roles structure the decision; the human approves execution.

### Two Use Cases, One Platform

**1. Live Trading Workstation** — The primary use case. AI roles analyse real market events, produce trade recommendations, and the human approves execution against Alpaca (paper or live).

**2. Educational Tool & Demo** — The same interface teaches how an investment bank or hedge fund trading desk operates. Each role is a visible, interactive character that explains its thinking in plain language. Users (including Ben's kids) can:
- Chat with any role to understand what it does and why
- Watch the Trader role quiz the other roles in real-time
- See how a trade idea flows from raw event → analysis → debate → recommendation → approval
- Use mock events to simulate realistic scenarios without real market data
- Learn the vocabulary: what does "risk-adjusted return" mean? Ask the Risk role.

The educational mode uses the exact same role system, UI, and data objects as the live system — it's not a separate "learning mode," it's the real thing with mock data and more conversational role prompts.

### Core Loop

```
Market Events (earnings, news, price moves, filings)
        │
        ▼
┌─────────────────────────────────────────────┐
│  AI Roles analyse in parallel (own sessions)│
│    Research  → narrative, thesis, catalysts  │
│    Quant     → pricing, levels, expected move│
│    Risk      → portfolio impact, flags       │
│                                             │
│  Shared Summary updates                     │
│                                             │
│  Trader role synthesises all three          │
│    → queries roles for clarification        │
│    → produces trade recommendation          │
│    → discusses with user before approval    │
└─────────────────────────────────────────────┘
        │
        ▼
  Human reviews recommendation + role discussions
        │
        ▼
  Approve / Reject / Discuss further
        │
        ▼
  Bracket order → Alpaca (paper or live)
```

### Design Principles

1. **Human in the loop.** AI recommends, human decides. No autonomous execution.
2. **Paper first.** Every strategy runs paper for 30+ trades minimum before real money.
3. **Cheap to run.** Use the cheapest model that meets each role's quality bar. Cache aggressively. Pre-filter before applying AI.
4. **Extensible.** The role system works for any strategy or product — only the data context and system prompts change. The architecture should support equities, options, crypto, and macro without structural changes.
5. **Looks good and easy to understand.** The UI should feel like a professional trading desk, not a developer tool. Dense but readable.
6. **Transparent AI.** Every role shows its reasoning. Role disagreement and deliberation should be visible, not hidden behind one final answer.
7. **Each role is independent.** Own context, own session, own model choice, own cost budget. Roles can be backed by different AI models and swapped independently.
8. **Educational clarity.** The system should make each role's perspective understandable enough to teach how a professional investment process works.
9. **Measurable AI operations.** Track model usage, token counts, and cost per role and per recommendation.
10. **Durable state and auditability.** Recommendations, approvals, and executions are records, not temporary UI state. Everything survives restarts.
11. **Local first, cloud ready.** Runs on Mac Mini for development. Deploy behind secure login when ready for production. Business logic is portable across environments.
12. **LLM-provider agnostic.** The system is not locked to one AI provider. Each role can use Anthropic, OpenAI, or any provider that supports structured output. Swap models without changing business logic.
13. **Never discard reasoning history.** Role discussion, recommendation evolution, and approval timestamps are kept permanently. They matter for trust, debugging, teaching, and post-trade review.

### MVP Scope

The first build should be a focused, publishable MVP, not an everything-platform.

**In scope for MVP:**
- Single-user workstation
- Paper trading only
- PEAD and earnings-extension workflows
- Event feed for earnings, news, pricing, and internal recommendation updates
- Watchlist and active symbols
- Four role panels with direct human chat
- Trader querying other roles before updating a recommendation
- Shared summary panel
- Structured recommendation object with full approval workflow
- Support for both entry decisions (new trades) and position management (close, add, reduce existing)
- Action set: `BUY | SELL | SHORT | COVER | PASS`
- Open positions panel
- Recommendation history and execution history
- Local development mode
- Cloud-ready architecture
- Mock and replay event modes for demos and teaching
- Inline explanations / tooltips for trading terminology

**Explicitly out of scope for MVP:**
- Autonomous execution
- Live capital deployment
- Options trading
- Multi-user collaboration
- Full broker abstraction beyond Alpaca
- Multiple strategies at once (PEAD only for MVP)
- Sophisticated portfolio optimisation
- On-device open-weight inference as a required component
- Full historical backtesting platform
- Secure login (add when publishing online)

**MVP success criteria:**
- Can ingest or simulate market events
- All four roles can analyse and discuss a symbol
- Produces a clear trader recommendation with visible influences from all roles
- Human can discuss with any role and approve or reject
- Tracks open paper trades and recommendation history
- Operates cheaply enough for regular use (~$1-2/day)
- Looks professional enough to demo to another person without apology

### What Not To Do

Anti-patterns to avoid in the next version:
- Keeping all logic in a single Python script
- Building the workstation as server-rendered HTML plus ad hoc JavaScript
- Putting long-running agent workflows inside API request handlers
- Coupling recommendation state to in-memory objects or CSV files
- Overcommitting to a heavyweight trading engine before the workstation UX is proven
- Making the educational/demo mode feel gimmicky or separate from the real product
- Excessive prose in role responses — visible disagreement summaries beat verbose chat

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Too much model usage cost if event triage is not strict | Pre-filter before expensive calls. Cost budgets per role per day and per recommendation. |
| Role chats becoming repetitive rather than useful | Clear structured output contracts. Roles must produce new information, not restate. |
| Overbuilding orchestration before the workstation UX is proven | Start with custom orchestration. Don't add LangGraph until workflow genuinely needs it. |
| UI becoming cluttered with too many simultaneous ideas | One active symbol in focus. Pending ideas as a compact queue, not expanded cards. |
| Educational features making the app feel unserious | Same architecture for live and demo. Demo is a config toggle, not a separate mode. |
| Role outputs too verbose or generic | System prompts enforce conciseness. Structured output fields force specificity. |

---

## 2. Trading Strategies

The platform is designed to support multiple strategies and products over time. Each strategy plugs into the same role pipeline — the roles get different context depending on the strategy.

### Strategy 1: PEAD — Post-Earnings Announcement Drift (Current, to be refactored)

Stocks that beat earnings estimates tend to drift in the surprise direction for 30-60 days. The current `dashboard_server.py` has working scan/filter/order logic that will be refactored into the new backend as clean, testable services.

**Current logic to preserve (refactored):**
- Earnings calendar scan via FMP `/stable/` endpoints
- EPS surprise calculation: `(actual - estimate) / abs(estimate) * 100`
- Minimum surprise threshold: 5%
- Minimum market cap: $1B
- 3-layer filter: SPY > 200d MA (regime), stock > 50d MA (momentum), gap < 8%
- Position sizing: 2% risk per trade, 5% stop-loss, 2:1 reward/risk
- Bracket orders to Alpaca: market buy + take-profit + stop-loss

**What changes:**
- Logic moves from monolithic handler functions into service classes
- Filters become composable and configurable per strategy
- Position sizing becomes a shared service used by Risk role
- Results feed into the role pipeline instead of directly rendering HTML cards

- **Data needed:** Earnings calendar, EPS estimates vs actuals, quotes, moving averages
- **AI value-add:** Classify beat quality (revenue-driven vs one-off), parse guidance language
- **Holding period:** 1-60 days

### Strategy 2: Earnings Extensions

Building on PEAD with richer signals:

- **Earnings Momentum (SUE Chains):** Consecutive surprise direction predicts next quarter. Track 2-3 quarter chains.
- **Estimate Revision Momentum:** Accelerating upward analyst revisions over 30/60/90 days.
- **Earnings Quality / Accruals:** Cash-flow-backed earnings vs accrual-heavy. Sloan accrual anomaly.
- **Conference Call Analysis:** Management tone shifts, hedging language, specificity of guidance vs prior quarters.
- **Data needed:** Earnings estimates history, SEC filings (XBRL), earnings call transcripts
- **AI value-add:** Strongest category — parsing transcripts, comparing language across quarters
- **Holding period:** 1-90 days
- **Priority:** High — directly extends current infrastructure

### Strategy 3: Event-Driven

- **M&A / Merger Arbitrage:** AI assesses deal completion probability from regulatory language.
- **Activist Investor Campaigns:** Monitor 13D filings (>5% stakes).
- **FDA / Regulatory Catalysts:** AI parses 100+ page briefing documents.
- **Index Rebalancing:** Predictable passive fund flows on S&P 500, Russell changes.
- **Spin-offs:** Forced selling by index funds, analyst undercoverage.
- **Data needed:** SEC EDGAR (13D/13G, 8-K, S-4), FDA calendar, index announcements
- **Holding period:** Days to months
- **Priority:** Medium

### Strategy 4: Sentiment Analysis

- **News Sentiment Shifts:** The *change* in sentiment matters more than the level.
- **Analyst Revision Tone:** Text analysis for conviction and hedging.
- **Earnings Call Tone:** Loughran-McDonald lexicon plus LLM analysis.
- **Macro Narrative Detection:** Identify emerging themes across transcripts.
- **Data needed:** News APIs (Benzinga, FMP), analyst reports, Google Trends
- **Holding period:** Hours to weeks
- **Priority:** Medium — overlay on other strategies

### Strategy 5: Macro / Sector Rotation

- **Business Cycle Rotation:** Yield curve, ISM, unemployment claims.
- **Rate Regime Rotation:** Fed policy signals.
- **Risk-On / Risk-Off:** VIX, credit spreads, yield curve.
- **Fed Language Parsing:** FOMC minutes analysis.
- **Data needed:** FRED (free), sector ETF prices, FOMC minutes, VIX
- **Holding period:** Weeks to months
- **Priority:** Medium — low data cost

### Strategy 6: Technical / Momentum

- **Cross-Sectional Momentum:** Buy top decile of 12-1 month returns.
- **Trend Following:** Long if above moving average, flat otherwise.
- **Mean Reversion:** Trade stocks >2 standard deviations from 20-day mean.
- **Data needed:** Price/volume data (already have)
- **AI value-add:** Weakest category for LLMs. Traditional ML more appropriate.
- **Priority:** Lower

### Strategy 7: Options (Future)

- **Earnings Volatility:** Buy/sell straddles around earnings.
- **Volatility Risk Premium:** Sell options to harvest implied-vs-realised gap.
- **Unusual Flow Detection:** Monitor unusual options volume.
- **Data needed:** Options chains (Polygon options, Tradier)
- **Priority:** Later — requires separate risk framework

### Strategy Priority

| Priority | Strategy | Why |
|----------|----------|-----|
| 1 (Now) | PEAD + Earnings Extensions | Extends existing infra, highest marginal value |
| 2 (Near) | Sentiment Overlay | LLM-native, filters existing signals |
| 3 (Near) | Macro / Sector Rotation | Free data (FRED), top-down context |
| 4 (Medium) | Event-Driven | New data pipelines, high AI value-add |
| 5 (Medium) | Technical / Momentum | Cheap data, low LLM value-add |
| 6 (Later) | Options | High complexity, separate risk framework |

---

## 3. AI Model Stack

### Core Principle: Each Role Has Its Own Session, Any Provider

Each AI role maintains its own context, conversation history, and can be backed by a different model from any provider. This means:

- Roles can be independently upgraded, swapped, or tuned
- A cheap model handles high-volume work while an expensive model handles high-stakes synthesis
- Role sessions persist across a recommendation lifecycle
- Roles don't share a single prompt/context — each sees only what's relevant to its job
- A role can use Claude today and GPT tomorrow without changing business logic

### LLM Provider Abstraction

All AI calls go through a provider-agnostic interface:

```python
class LLMProvider(Protocol):
    """Any LLM that supports structured output."""

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send messages and get a response with optional tool_use."""
        ...

class LLMResponse:
    text: str                          # human-readable message
    tool_calls: list[ToolCall] | None  # structured output via tool_use / function_calling
    model: str                         # actual model used
    input_tokens: int
    output_tokens: int
    cost_usd: float                    # calculated from token counts + model pricing
```

Concrete implementations:

```python
class AnthropicProvider(LLMProvider):
    """Claude models via anthropic SDK. Uses tool_use for structured output."""
    ...

class OpenAIProvider(LLMProvider):
    """GPT models via openai SDK. Uses function_calling for structured output."""
    ...

class LocalProvider(LLMProvider):
    """Local models via ollama or similar. For cheap background tasks."""
    ...
```

### Model Tiering (Keep It Cheap)

| Tier | Use Case | Example Models | Estimated Cost |
|------|----------|---------------|----------------|
| **Fast/Cheap** | Event classification, headline triage, first-pass scoring | Claude Haiku, GPT-4o-mini | ~$0.001/call |
| **Standard** | Research, Quant, Risk role analysis | Claude Sonnet, GPT-4o | ~$0.01-0.03/call |
| **Premium** | Trader synthesis, complex filing analysis | Claude Opus, GPT-4.5, o3 | ~$0.10-0.15/call |

Default: **Standard tier for all four roles.** Escalate per role when needed.

### Per-Role Model Routing

| Role | Default Tier | Escalate To | Escalation Trigger |
|------|-------------|-------------|-------------------|
| **Research** | Standard | Premium | Long earnings transcripts, complex multi-quarter comparisons, 10-K analysis |
| **Quant Pricing** | Fast + code | Standard | Unusual vol regime or conflicting signals needing explanation. Core pricing is deterministic code. |
| **Risk** | Standard | Premium | Cross-position correlation, complex regime-sensitive decisions |
| **Trader** | Standard | Premium | High-conviction (>7/10), strong role disagreement, user-facing discussion, user explicitly asks for deeper analysis |

### Per-Role Configuration

```python
class RoleConfig(BaseModel):
    role_name: str              # "research", "quant_pricing", "risk", "trader"
    provider: str               # "anthropic", "openai", "local"
    default_model: str          # "claude-sonnet-4-6", "gpt-4o", etc.
    escalation_model: str       # model for escalation triggers
    system_prompt_version: str  # versioned prompt for A/B testing
    demo_prompt_version: str    # explanatory prompt for educational mode
    tool_permissions: list[str] # which data tools this role can call
    temperature: float          # 0.0-1.0 (Risk may want lower for consistency)
    cost_budget_per_day: float  # max daily spend (alert threshold)
    cost_budget_per_rec: float  # max spend per single recommendation analysis
    max_tokens_per_call: int    # output token limit
```

### Cost Management

- **Pre-filter before AI:** Scan 500 earnings events with simple rules, send only 5-10 qualifying candidates to AI roles.
- **Cache aggressively:** An earnings transcript doesn't change. A role's analysis doesn't need re-running unless new data arrives.
- **Batch off-hours:** Non-urgent analysis runs in batches, not real-time.
- **Use prompt caching:** Anthropic and OpenAI both support prompt caching for repeated system prompts.
- **Monitor spend:** Track cost per recommendation, per role, per day. Alert if daily spend exceeds threshold.

### Structured Output

Each role uses structured output (tool_use on Anthropic, function_calling on OpenAI) to return JSON alongside human-readable discussion:

```
Role Call → LLM with tool/function schema
         → Returns: message text (for chat panel)
                  + structured_payload (for UI, Trader, audit)
```

### Embeddings and Retrieval (Phase 3+)

Add vector search for prior recommendations, historical role discussions, earnings transcript excerpts, and user playbooks. Use OpenAI `text-embedding-3-small` or a local model. Not needed for Phase 2.

---

## 4. Role System Design

### Role Definitions

Each role has: a system prompt, a structured output contract, a chat interface, and its own persistent session per recommendation.

#### Research

**Perspective:** Fundamental analyst. Explains why the market may be underreacting.

**Inputs:** Earnings data, news, transcripts, analyst estimates, SEC filings

**Structured Output:**
```json
{
  "thesis_summary": "string",
  "beat_quality": "REVENUE_DRIVEN | MARGIN_EXPANSION | ONE_OFF | ACCOUNTING",
  "guidance_change": "RAISED | MAINTAINED | LOWERED | NOT_PROVIDED",
  "catalysts": ["string"],
  "counterpoints": ["string"],
  "confidence": 0.0-1.0
}
```

**System Prompt Guidelines:**
- Identity: "You are the Research Analyst on a trading desk."
- Job: Evaluate the fundamental case. Is this earnings beat real and sustainable? What's the narrative?
- Must always provide counterpoints, not just the bull case.
- In demo mode: explain financial terminology when first used, speak at a high-school comprehension level, relate concepts to everyday analogies.

#### Quant Pricing

**Perspective:** Technical/quantitative analyst. Frames the trade in price terms.

**Inputs:** Quotes, moving averages, volume, options implied move, analyst price targets, historical patterns

**Structured Output:**
```json
{
  "fair_value_estimate": 0.0,
  "signal_strength": "STRONG | MODERATE | WEAK",
  "entry_zone": { "low": 0.0, "high": 0.0 },
  "stop_level": 0.0,
  "target_zone": { "low": 0.0, "high": 0.0 },
  "expected_move_pct": 0.0,
  "volatility_regime": "LOW | NORMAL | ELEVATED | EXTREME",
  "tactical_notes": "string"
}
```

**System Prompt Guidelines:**
- Identity: "You are the Quantitative Pricing Analyst."
- Job: Frame the trade in numbers. Where do we enter, where do we exit, what's the expected move?
- Must reference specific price levels and why they matter (support, resistance, moving averages).
- Core calculations (position sizing, stop/target math) are done in code, not by the LLM. The LLM explains and contextualises.
- In demo mode: explain what moving averages, support/resistance, and volatility mean.

#### Risk

**Perspective:** Devil's advocate. Challenges the thesis, flags what could go wrong.

**Inputs:** Current portfolio positions, sector exposure, correlation, macro state, earnings blackout calendar

**Structured Output:**
```json
{
  "top_risks": ["string"],
  "portfolio_overlap": { "sector_pct": 0.0, "correlated_positions": ["string"] },
  "position_size_recommendation": 0.0,
  "max_portfolio_risk_pct": 0.0,
  "event_blackout_flag": false,
  "liquidity_concerns": "string | null",
  "reject_recommendation": false,
  "reject_reason": "string | null"
}
```

**System Prompt Guidelines:**
- Identity: "You are the Risk Manager on the desk."
- Job: Find reasons NOT to do this trade. Challenge the thesis. Flag portfolio-level issues.
- Must always identify at least one risk, even for strong trades.
- If `reject_recommendation` is true, must provide a clear `reject_reason`.
- In demo mode: explain why risk management exists, why good ideas get rejected, what "position sizing" means.

#### Trader

**Perspective:** The lead decision-maker. Synthesises all roles into an actionable recommendation. The Trader is the "main character."

**Inputs:** All three other roles' structured outputs + their discussion text + raw market data

**Capabilities beyond other roles:**
- Can **query any other role** mid-analysis
- Can **request updated analysis** from a role if new information arrives
- Can **flag disagreements** between roles and explain which side it's taking and why
- Discusses the recommendation with the human, answering questions about any role's input

**Structured Output:**
```json
{
  "action": "BUY | SELL | SHORT | COVER | PASS",
  "conviction": 1-10,
  "symbol": "string",
  "entry_price": 0.0,
  "entry_logic": "string",
  "stop_price": 0.0,
  "stop_logic": "string",
  "target_price": 0.0,
  "target_logic": "string",
  "position_size_shares": 0,
  "position_size_dollars": 0.0,
  "time_horizon": "string",
  "thesis": "string",
  "must_have_conditions": ["string"],
  "invalidation_conditions": ["string"],
  "dissent_notes": "string | null",
  "questions_for_user": ["string"],
  "role_queries": [
    { "to_role": "string", "question": "string", "response_summary": "string" }
  ]
}
```

**Action Set:**
- `BUY` — Open or add to a long position
- `SELL` — Reduce or close an existing long position
- `SHORT` — Open or add to a short position
- `COVER` — Reduce or close an existing short position
- `PASS` — Take no action. This is a real recommendation, not a failure. It means the system reviewed the idea and the best action is no action. Reasons: setup not attractive, risks outweigh return, signal too weak, portfolio already exposed, or "interesting but not tradeable right now."

The recommendation system supports both **entry decisions** (new trades) and **management decisions** (existing positions — close, add to, reduce). A role analysis can trigger for an event on a symbol you already hold.

**System Prompt Guidelines:**
- Identity: "You are the Head Trader. You make the final call."
- Job: Synthesise Research, Quant, and Risk into one recommendation. Resolve disagreements. Present to the human.
- Must reference what each role said and why you agree or disagree.
- If roles disagree, explain the disagreement and your reasoning for siding with one.
- Always include `invalidation_conditions` — what would make this trade wrong?
- In demo mode: narrate the decision-making process step by step. Explain why you're asking other roles specific questions.

### Role Interaction Patterns

**1. Human ↔ Any Role (direct chat)**
The human can chat with any role at any time via its chat widget.

**2. Trader ↔ Other Roles (inter-role querying)**
The Trader actively questions the other roles. These queries are visible in the UI:

```
Trader → Research: "Your confidence is 0.7 on beat quality. What would
                    move that to 0.9 or drop it below 0.5?"
Research → Trader: "If the 10-Q shows revenue came from a single large
                    contract, confidence drops to 0.4. If the call shows
                    management raising guidance on those lines, it's 0.9."
Trader → Risk:    "Research is cautious. Does that change your size rec?"
Risk → Trader:    "Yes — reduce from 2% to 1% risk until confirmed."
```

These exchanges are stored as RoleMessages and visible in each role's chat panel.

**3. Human ↔ Trader (recommendation discussion)**
After the Trader builds its recommendation, the human discusses it. The Trader adjusts based on the conversation.

### Role Flow

1. Event arrives (earnings surprise, news, price alert)
2. Research, Quant, and Risk analyse **in parallel** (own sessions, own contexts)
3. Shared Summary updates with key findings from all three
4. Trader receives all three structured outputs + discussion text
5. Trader **queries other roles** for clarification or to resolve disagreements (visible in UI)
6. Trader produces recommendation OR asks the human clarifying questions
7. Human can chat with any role directly at any point
8. Trader updates recommendation based on discussion
9. Recommendation enters `awaiting_user_approval`
10. User approves → order submitted

---

## 5. Recommendation State Machine

```
┌────────────┐
│  observing │ ← event detected, roles not yet triggered
└─────┬──────┘
      │ roles triggered
      ▼
┌─────────────────┐
│ under_discussion │ ← roles analysing, trader may query other roles
└─────┬───────────┘
      │ trader produces draft
      ▼
┌──────────────────────┐
│ draft_recommendation │ ← trader has a proposal, may have questions for user
└─────┬────────────────┘
      │ trader presents to user
      ▼
┌──────────────────────────┐
│ awaiting_user_feedback   │ ← user discussing with trader, asking follow-ups
└─────┬────────────────────┘
      │ trader formally requests approval
      ▼
┌──────────────────────────┐
│ awaiting_user_approval   │ ← final rec, Approve/Reject buttons visible
└─────┬──────────┬─────────┘
      │          │
   approve     reject
      │          │
      ▼          ▼
┌───────────┐  ┌──────────┐
│ approved  │  │ rejected │
└─────┬─────┘  └──────────┘
      │ order submitted
      ▼
┌───────────┐
│ submitted │
└─────┬─────┘
      │
      ├─── partial fill ──▶ ┌────────────────┐
      │                     │ partially_filled│
      │                     └───────┬────────┘
      │                             │
      ▼                             ▼
┌──────────┐
│  filled  │ ← open trade
└─────┬────┘
      │ exit (target, stop, manual, time)
      ▼
┌──────────┐
│  closed  │
└──────────┘

Side states: cancelled, failed
```

`awaiting_user_feedback` vs `awaiting_user_approval`: Approve/Reject buttons only appear in the approval state. During feedback, the recommendation may still change.

Every state transition is timestamped and stored.

---

## 6. Core Data Objects

### IncomingEvent

```
id, type, symbol, headline, body_excerpt, source,
timestamp, importance (1-5), linked_recommendation_ids
```

Types: `earnings`, `news`, `price_alert`, `macro`, `position_change`, `recommendation_update`, `internal_alert`

### RoleThread

```
id, role, symbol, recommendation_id, created_at
```

One thread per role per recommendation.

### RoleMessage

```
id, role_thread_id, role, sender (user | role:research | role:risk | role:quant_pricing | role:trader),
symbol, recommendation_id,
message_text, structured_payload (JSON), stance, confidence,
provider, model_used, input_tokens, output_tokens, cost_usd, timestamp
```

`symbol` and `recommendation_id` denormalised for easy querying. `provider` tracks which LLM provider was used.

### SharedSummary

```
id, recommendation_id, summary_text,
bull_case, bear_case, key_disagreement,
last_updated, generated_by_model
```

### TradeRecommendation

```
id, symbol, direction, status,
strategy_type,
thesis,
entry_price, entry_logic,
stop_price, stop_logic,
target_price, target_logic,
position_size_shares, position_size_dollars,
time_horizon, conviction (1-10),
supporting_roles, blocking_risks,
created_at, updated_at
```

`_logic` fields capture *why* the level was chosen, not just the number.

### ApprovalRecord

```
id, recommendation_id, status (approved | rejected),
reviewer_notes, requested_at,
approved_at, rejected_at
```

### OpenTrade

```
id, recommendation_id, symbol, direction,
entry_price, current_price, size, unrealized_pnl,
stop_price, target_price, risk_state,
broker_order_id, opened_at
```

### ExecutionRecord

```
id, recommendation_id, trade_id, order_type,
submitted_at, filled_at, fill_price, fill_qty,
broker_order_id, broker_response, status
```

---

## 7. Workstation UI

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  Portfolio: $100,234  │  Daily: +$127  │  Paper Mode     │
├────────────┬─────────────────────┬───────────────────────┤
│  EVENT     │  AI ROLES           │  TRADE DESK           │
│  FEED      │                     │                       │
│            │  ┌ Shared Summary ┐ │  ┌ Recommendation ──┐ │
│  Filters:  │  │ Bull / Bear /  │ │  │ BUY NVDA          │ │
│  [earnings]│  │ Disagreement   │ │  │ Conviction: 8/10  │ │
│  [news]    │  └────────────────┘ │  │ Entry: $892       │ │
│  [pricing] │                     │  │  "gap fill, VWAP" │ │
│  [macro]   │  ┌── Research ────┐ │  │ Stop: $847        │ │
│            │  │ chat + struct  │ │  │  "below pre-earn" │ │
│  14:02     │  │ [type here]   │ │  │ Target: $982      │ │
│  NVDA +8%  │  └────────────────┘ │  │  "analyst consens"│ │
│  ★★★★☆    │  ┌── Quant ──────┐ │  │                   │ │
│            │  │ chat + struct  │ │  │ [Approve] [Reject]│ │
│  14:01     │  │ [type here]   │ │  └───────────────────┘ │
│  Fed mins  │  └────────────────┘ │                       │
│  ★★★☆☆    │  ┌── Risk ───────┐ │  ┌ Open Positions ───┐ │
│            │  │ chat + struct  │ │  │ AAPL  +2.3%  $340│ │
│  13:58     │  │ [type here]   │ │  │ MSFT  -0.4%  $420│ │
│  SPY high  │  └────────────────┘ │  └───────────────────┘ │
│  ★★☆☆☆    │  ┌── Trader ─────┐ │                       │
│            │  │ chat + struct  │ │  ┌ Pending Ideas ────┐ │
│            │  │ [type here]   │ │  │ AMD  under_disc.  │ │
│            │  └────────────────┘ │  │ CRM  draft_rec.   │ │
│            │                     │  └───────────────────┘ │
│            │                     │  ┌ Recent History ───┐ │
│            │                     │  │ PLTR  rejected     │ │
│            │                     │  │ GOOGL closed +4.2% │ │
│            │                     │  └───────────────────┘ │
└────────────┴─────────────────────┴───────────────────────┘
```

**Left column** → "What just happened?"
**Centre column** → "What do the roles think?"
**Right column** → "What action is proposed or currently live?"

### Key UX Decisions

- **One symbol in focus** in centre column. Clicking an event or recommendation switches focus. Fast switching via event feed or pending ideas.
- **Role panels are collapsible.** Expand to chat, collapse to see summary one-liner. Easy to scan even collapsed.
- **Shared Summary** above role panels. Bull case, bear case, key disagreement in 2-3 sentences.
- **Event feed + watchlist** in left column. Active symbols with latest price and alert status alongside the event stream. Filters by type and importance (1-5 stars).
- **Recommendation card reads like a concise trade memo**, not a blob of text. Entry/stop/target with `_logic` reasoning visible. Approve/Reject buttons only appear in `awaiting_user_approval` state.
- **Disagreement and uncertainty are first-class UI elements.** Highlighted in the shared summary and visible as badges on role panels when roles disagree.
- **Open Positions** shows live P&L from Alpaca with links back to the recommendation.
- **Inline terminology tooltips.** Key trading terms have hover explanations so the app works for learners without cluttering the UI. Examples: `COVER` → "reduces or closes a short position", `Conviction` → "how strong the trader's recommendation is", `Expected Move` → "the market's implied near-term price range", `Event Blackout` → "period where opening new trades may be restricted by risk rules".
- **Demo mode requires no explanation from the operator.** A learner should be able to sit down and follow a scenario without being told how the app works.

### Frontend Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js + React + TypeScript | Rich multi-panel UI, Ben knows it, clean cloud path |
| Styling | Tailwind CSS | Fast iteration, dark theme, responsive, dense layouts |
| Real-time | SSE (server-sent events) | Simpler than WebSockets for event feeds |
| State | React Query (TanStack Query) | Server state caching, optimistic updates, refetch on focus |
| Charts | TradingView lightweight-charts | P&L curves, mini price charts in position cards |

### Mock and Replay Event System

Three event modes, all feeding the same pipeline:

**Live** — Real market data from FMP/Polygon/Alpaca.
**Mock** — Synthetic events from pre-built scenario JSON files. No external APIs needed.
**Replay** — Historical event sequences played back at original or accelerated speed.

Toggle via config: `EVENT_MODE=live|mock|replay`

---

## 8. Technical Architecture

### System Shape

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Next.js    │────▶│  FastAPI Backend  │────▶│  LLM Providers  │
│  Frontend   │◀────│                  │◀────│  (Anthropic,     │
│  (React/TS) │ SSE │  /api/events     │     │   OpenAI, local) │
└─────────────┘     │  /api/roles      │     └─────────────────┘
                    │  /api/recs       │
                    │  /api/trades     │     ┌─────────────────┐
                    │  /api/portfolio  │────▶│  Alpaca         │
                    │  /api/approve    │◀────│  (broker)       │
                    │  /api/stream     │     └─────────────────┘
                    │  /api/config     │
                    │                  │     ┌─────────────────┐
                    │  Services:       │────▶│  FMP / Polygon  │
                    │  - scanner       │◀────│  (market data)  │
                    │  - roles         │     └─────────────────┘
                    │  - state machine │
                    │  - event bus     │
                    └────────┬─────────┘
                             │
                      ┌──────┴──────┐
                      │   SQLite    │
                      └─────────────┘
```

### Backend: FastAPI (Python)

Async Python backend with typed models:

- Async endpoints for non-blocking calls to LLMs, FMP, Alpaca
- SSE via `sse-starlette` for real-time event streaming to frontend
- Pydantic models matching the data objects in section 6
- Clean separation: routes → services → data layer → adapters

### Database: SQLite

SQLite for all environments until cloud deployment needs Postgres.

Core tables: `events`, `role_threads`, `role_messages`, `shared_summaries`, `recommendations`, `approval_records`, `trades`, `executions`, `role_configs`, `cost_log`, `watchlist`

### Role Orchestration: Custom

```python
async def analyse_candidate(candidate: Candidate, portfolio: Portfolio):
    # Phase 1: Three roles analyse in parallel
    research, quant, risk = await asyncio.gather(
        research_role.analyse(candidate),
        quant_role.analyse(candidate),
        risk_role.analyse(candidate, portfolio),
    )

    # Phase 2: Shared summary
    summary = await generate_summary(research, quant, risk)

    # Phase 3: Trader synthesises — can query roles
    recommendation = await trader_role.synthesise(
        candidate, research, quant, risk, summary,
        query_role=lambda role, q: role.respond(q),
    )

    return recommendation
```

Why not LangGraph: our workflow is a predictable pipeline. Migrate if it grows complex.

### Authentication (Cloud)

- NextAuth.js (OAuth, magic links, credentials)
- JWT tokens passed to FastAPI
- API endpoints open when local, auth-required when deployed

---

## 9. Project Directory Structure

```
trading/
├── frontend/                     # Next.js app
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   ├── public/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── layout.tsx        # root layout, dark theme, fonts
│   │   │   ├── page.tsx          # main workstation page
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx          # portfolio value, daily P&L, mode badge
│   │   │   │   └── ThreeColumnLayout.tsx
│   │   │   ├── events/
│   │   │   │   ├── EventFeed.tsx       # left column
│   │   │   │   ├── EventCard.tsx       # single event item
│   │   │   │   └── EventFilters.tsx    # type + importance filters
│   │   │   ├── roles/
│   │   │   │   ├── RolePanel.tsx       # collapsible role chat panel
│   │   │   │   ├── RoleChatMessage.tsx # single message (user, role, inter-role)
│   │   │   │   ├── RoleChatInput.tsx   # message input box
│   │   │   │   ├── RoleStructuredOutput.tsx  # formatted structured payload
│   │   │   │   └── SharedSummary.tsx   # bull/bear/disagreement card
│   │   │   ├── trades/
│   │   │   │   ├── RecommendationCard.tsx    # right column main card
│   │   │   │   ├── ApprovalControls.tsx      # approve/reject/discuss buttons
│   │   │   │   ├── OpenPositions.tsx         # live P&L table
│   │   │   │   ├── PendingIdeas.tsx          # pending recommendations queue
│   │   │   │   └── RecentHistory.tsx         # closed/rejected history
│   │   │   └── shared/
│   │   │       ├── Badge.tsx
│   │   │       ├── PnlValue.tsx        # green/red formatted P&L
│   │   │       └── MiniChart.tsx       # TradingView lightweight-charts wrapper
│   │   ├── hooks/
│   │   │   ├── useSSE.ts              # SSE connection hook
│   │   │   ├── useRoleChat.ts         # send/receive messages for a role
│   │   │   ├── useRecommendation.ts   # current recommendation state
│   │   │   └── usePortfolio.ts        # portfolio/positions polling
│   │   ├── lib/
│   │   │   ├── api.ts                 # fetch wrappers for backend endpoints
│   │   │   ├── types.ts              # TypeScript types matching backend models
│   │   │   └── format.ts             # currency, percentage, date formatters
│   │   └── config/
│   │       └── constants.ts           # API base URL, SSE URL, polling intervals
│   └── .env.local                     # NEXT_PUBLIC_API_URL=http://localhost:8000
│
├── backend/                      # FastAPI app
│   ├── pyproject.toml            # dependencies, project config
│   ├── alembic.ini               # DB migrations config
│   ├── alembic/
│   │   └── versions/             # migration scripts
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app creation, CORS, lifespan
│   │   ├── config.py             # Settings from env vars (pydantic-settings)
│   │   ├── database.py           # SQLite connection, session management
│   │   ├── models/               # Pydantic models (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── events.py         # IncomingEvent
│   │   │   ├── roles.py          # RoleMessage, RoleThread, SharedSummary
│   │   │   ├── recommendations.py # TradeRecommendation, ApprovalRecord
│   │   │   ├── trades.py         # OpenTrade, ExecutionRecord
│   │   │   └── config.py         # RoleConfig, AppConfig
│   │   ├── db/                   # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── tables.py         # SQLAlchemy/raw SQL table definitions
│   │   │   ├── events_repo.py
│   │   │   ├── roles_repo.py
│   │   │   ├── recommendations_repo.py
│   │   │   └── trades_repo.py
│   │   ├── services/             # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── scanner.py        # PEAD scanner (refactored from dashboard_server.py)
│   │   │   ├── filters.py        # 3-layer filter + future composable filters
│   │   │   ├── position_sizing.py # risk-based position calculator
│   │   │   ├── state_machine.py  # recommendation lifecycle transitions
│   │   │   ├── event_bus.py      # internal event routing + SSE broadcasting
│   │   │   ├── mock_events.py    # mock/replay event generation
│   │   │   └── portfolio.py      # portfolio state from Alpaca
│   │   ├── roles/                # AI role system
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # BaseRole class — session, history, tool_use
│   │   │   ├── research.py       # Research role
│   │   │   ├── quant_pricing.py  # Quant Pricing role
│   │   │   ├── risk.py           # Risk role
│   │   │   ├── trader.py         # Trader role (with inter-role querying)
│   │   │   ├── orchestrator.py   # Parallel role execution + trader synthesis
│   │   │   └── prompts/          # System prompt templates (versioned)
│   │   │       ├── research_v1.md
│   │   │       ├── research_demo_v1.md
│   │   │       ├── quant_pricing_v1.md
│   │   │       ├── quant_pricing_demo_v1.md
│   │   │       ├── risk_v1.md
│   │   │       ├── risk_demo_v1.md
│   │   │       ├── trader_v1.md
│   │   │       └── trader_demo_v1.md
│   │   ├── adapters/             # External service adapters
│   │   │   ├── __init__.py
│   │   │   ├── llm/              # LLM provider abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py       # LLMProvider protocol
│   │   │   │   ├── anthropic.py  # Claude implementation
│   │   │   │   ├── openai.py     # GPT implementation
│   │   │   │   └── registry.py   # get_provider(name) factory
│   │   │   ├── fmp.py            # FMP market data adapter
│   │   │   ├── alpaca.py         # Alpaca broker adapter
│   │   │   ├── polygon.py        # Polygon.io adapter (Phase 2B)
│   │   │   ├── fred.py           # FRED macro data adapter (Phase 3)
│   │   │   └── edgar.py          # SEC EDGAR adapter (Phase 3)
│   │   └── routes/               # FastAPI route handlers
│   │       ├── __init__.py
│   │       ├── events.py         # GET /api/events, GET /api/stream (SSE)
│   │       ├── roles.py          # POST /api/roles/{name}/analyse, /chat, GET /history
│   │       ├── recommendations.py # GET /api/recs, POST /api/recs/{id}/approve, /reject
│   │       ├── trades.py         # GET /api/trades, GET /api/portfolio, GET /api/positions
│   │       ├── scanner.py        # POST /api/scan (trigger PEAD scan)
│   │       └── config.py         # GET/PUT /api/config/roles (role config management)
│   └── tests/
│       ├── conftest.py
│       ├── test_scanner.py
│       ├── test_filters.py
│       ├── test_state_machine.py
│       ├── test_position_sizing.py
│       ├── test_roles.py
│       └── test_routes.py
│
├── data/                         # Runtime data (gitignored)
│   ├── aatf.db                   # SQLite database
│   └── mock_scenarios/           # Mock event JSON files
│       ├── earnings_beat.json
│       ├── risk_veto.json
│       ├── guidance_downgrade.json
│       ├── macro_shift.json
│       └── disagreement.json
│
├── .env                          # API keys (gitignored)
├── .env.example                  # Template with all required vars
├── .gitignore
├── docker-compose.yml            # Optional: run frontend + backend together
├── Makefile                      # dev, test, lint, migrate commands
├── README.md
├── CLAUDE_CODE_HANDOFF.md        # Legacy reference
├── trading_plan_claude.md        # This plan
└── trading_plan_codex.md         # Codex plan (reference)
```

---

## 10. Backend API Specification

### Events

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/events` | List events. Query params: `?type=earnings&symbol=NVDA&importance_min=3&limit=50&offset=0` |
| `GET` | `/api/events/{id}` | Get single event |
| `GET` | `/api/stream` | SSE stream of real-time events (see SSE spec below) |
| `POST` | `/api/scan` | Trigger PEAD earnings scan. Returns list of candidates created. |
| `POST` | `/api/events/mock` | Inject a mock event (demo mode). Body: event JSON or scenario name. |
| `POST` | `/api/events/replay` | Start replaying a historical scenario. Body: `{ "scenario": "earnings_beat", "speed": 2.0 }` |

### Roles

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/roles/{name}/analyse` | Trigger role analysis for a candidate. Body: `{ "recommendation_id": "..." }`. Returns RoleMessage with structured_payload. |
| `POST` | `/api/roles/{name}/chat` | Send a message to a role. Body: `{ "recommendation_id": "...", "message": "..." }`. Returns RoleMessage. |
| `GET` | `/api/roles/{name}/history` | Get message history. Query: `?recommendation_id=...&limit=50` |
| `GET` | `/api/roles/config` | Get all role configs |
| `PUT` | `/api/roles/{name}/config` | Update a role's config (model, prompt version, etc.) |

### Recommendations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/recs` | List recommendations. Query: `?status=awaiting_user_approval&symbol=NVDA&limit=20` |
| `GET` | `/api/recs/{id}` | Get single recommendation with all role threads, messages, summary |
| `GET` | `/api/recs/{id}/timeline` | Full recommendation lifecycle as ordered timeline (for "show the discussion" view) |
| `POST` | `/api/recs/{id}/approve` | Approve recommendation. Body: `{ "notes": "..." }`. Moves to `approved` state. |
| `POST` | `/api/recs/{id}/reject` | Reject recommendation. Body: `{ "notes": "...", "reason": "..." }` |
| `POST` | `/api/recs/{id}/discuss` | Send message to Trader about this rec. Body: `{ "message": "..." }` |
| `POST` | `/api/recs/{id}/refresh` | Re-run role analysis with latest data. Useful after new events arrive. |
| `POST` | `/api/recs/{id}/execute` | Submit order to broker. Only callable when status is `approved`. Separated from approve so approval and execution are distinct auditable steps. |

### Portfolio & Trades

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/portfolio` | Alpaca account summary (cash, equity, buying power, daily P&L) |
| `GET` | `/api/positions` | Open positions from Alpaca with unrealised P&L |
| `GET` | `/api/trades` | Trade history with stats (win rate, avg win/loss, total P&L) |
| `GET` | `/api/trades/{id}` | Single trade detail with linked recommendation |

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/status` | Health check: Alpaca connected, LLM providers reachable, DB OK, mode |
| `GET` | `/api/config` | Current app config (event mode, active strategy, cost tracking summary) |
| `PATCH` | `/api/config` | Partial update app config (event mode toggle, role settings, etc.) |
| `GET` | `/api/costs` | Cost tracking: spend by role, by day, by recommendation |
| `GET` | `/api/health` | System health: LLM providers reachable, broker connected, DB OK |

---

## 11. SSE Event Format

The `/api/stream` endpoint pushes events to the frontend as Server-Sent Events:

```
event: market_event
data: {"id":"evt_123","type":"earnings","symbol":"NVDA","headline":"NVDA beats by 8%","importance":4,"timestamp":"..."}

event: role_message
data: {"role":"research","recommendation_id":"rec_456","sender":"role:research","message_text":"Beat is revenue-driven...","structured_payload":{...}}

event: role_query
data: {"from_role":"trader","to_role":"risk","question":"Does sector overlap concern apply here?","recommendation_id":"rec_456"}

event: recommendation_update
data: {"id":"rec_456","status":"draft_recommendation","symbol":"NVDA","conviction":8}

event: summary_update
data: {"recommendation_id":"rec_456","bull_case":"...","bear_case":"...","key_disagreement":"..."}

event: position_update
data: {"symbol":"AAPL","current_price":341.20,"unrealized_pnl":234.50,"unrealized_plpc":2.3}

event: cost_alert
data: {"role":"research","daily_total_usd":1.45,"budget_usd":5.00,"message":"Research role at 29% of daily budget"}

event: system
data: {"type":"scan_started"} | {"type":"scan_complete","candidates_found":3}
```

Frontend subscribes on mount, reconnects on disconnect with exponential backoff.

---

## 12. Database Schema

```sql
-- Events
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,            -- earnings, news, price_alert, macro, ...
    symbol TEXT,
    headline TEXT NOT NULL,
    body_excerpt TEXT,
    source TEXT,
    importance INTEGER DEFAULT 3,  -- 1-5
    linked_recommendation_ids TEXT, -- JSON array
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_events_symbol ON events(symbol);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);

-- Role Threads
CREATE TABLE role_threads (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,            -- research, quant_pricing, risk, trader
    symbol TEXT NOT NULL,
    recommendation_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);
CREATE INDEX idx_threads_rec ON role_threads(recommendation_id);

-- Role Messages
CREATE TABLE role_messages (
    id TEXT PRIMARY KEY,
    role_thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    sender TEXT NOT NULL,          -- user, role:research, role:trader, etc.
    symbol TEXT,
    recommendation_id TEXT,
    message_text TEXT NOT NULL,
    structured_payload TEXT,       -- JSON
    stance TEXT,                   -- bullish, bearish, neutral, cautious
    confidence REAL,               -- 0.0-1.0
    provider TEXT,                 -- anthropic, openai, local
    model_used TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (role_thread_id) REFERENCES role_threads(id)
);
CREATE INDEX idx_messages_thread ON role_messages(role_thread_id);
CREATE INDEX idx_messages_rec ON role_messages(recommendation_id);
CREATE INDEX idx_messages_symbol ON role_messages(symbol);

-- Shared Summaries
CREATE TABLE shared_summaries (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    summary_text TEXT,
    bull_case TEXT,
    bear_case TEXT,
    key_disagreement TEXT,
    generated_by_model TEXT,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

-- Recommendations
CREATE TABLE recommendations (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    direction TEXT,                -- BUY, SELL, SHORT, COVER, PASS
    status TEXT NOT NULL DEFAULT 'observing',
    strategy_type TEXT NOT NULL,   -- PEAD, EVENT, SENTIMENT, ...
    thesis TEXT,
    entry_price REAL,
    entry_logic TEXT,
    stop_price REAL,
    stop_logic TEXT,
    target_price REAL,
    target_logic TEXT,
    position_size_shares REAL,
    position_size_dollars REAL,
    time_horizon TEXT,
    conviction INTEGER,            -- 1-10
    supporting_roles TEXT,         -- JSON array
    blocking_risks TEXT,           -- JSON array
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_recs_status ON recommendations(status);
CREATE INDEX idx_recs_symbol ON recommendations(symbol);

-- Approval Records
CREATE TABLE approval_records (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    status TEXT NOT NULL,          -- approved, rejected
    reviewer_notes TEXT,
    requested_at TEXT NOT NULL,
    approved_at TEXT,
    rejected_at TEXT,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

-- Trades
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL,
    current_price REAL,
    shares REAL,
    unrealized_pnl REAL,
    stop_price REAL,
    target_price REAL,
    exit_price REAL,
    exit_reason TEXT,              -- target, stop, manual, time
    pnl_dollars REAL,
    pnl_percent REAL,
    risk_state TEXT,               -- normal, at_stop, at_target, closed
    broker_order_id TEXT,
    opened_at TEXT,
    closed_at TEXT,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_open ON trades(closed_at) WHERE closed_at IS NULL;

-- Execution Records
CREATE TABLE executions (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    trade_id TEXT,
    order_type TEXT,               -- market, limit, bracket
    submitted_at TEXT NOT NULL,
    filled_at TEXT,
    fill_price REAL,
    fill_qty REAL,
    broker_order_id TEXT,
    broker_response TEXT,          -- JSON
    status TEXT NOT NULL,          -- submitted, filled, partially_filled, cancelled, failed
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- Role Configs
CREATE TABLE role_configs (
    role_name TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'anthropic',
    default_model TEXT NOT NULL,
    escalation_model TEXT,
    system_prompt_version TEXT NOT NULL DEFAULT 'v1',
    demo_prompt_version TEXT NOT NULL DEFAULT 'demo_v1',
    tool_permissions TEXT,         -- JSON array
    temperature REAL DEFAULT 0.7,  -- lower for Risk (consistency), higher for Research (creativity)
    cost_budget_per_day REAL DEFAULT 5.0,
    cost_budget_per_rec REAL DEFAULT 1.0,  -- max per single recommendation
    max_tokens_per_call INTEGER DEFAULT 4096,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cost Tracking
CREATE TABLE cost_log (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    recommendation_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_costs_role ON cost_log(role);
CREATE INDEX idx_costs_date ON cost_log(timestamp);

-- Watchlist
CREATE TABLE watchlist (
    symbol TEXT PRIMARY KEY,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    notes TEXT
);
```

### Future Tables (Post-MVP)

These will be added as features require them:
- `daily_metrics` — aggregated daily P&L, win rate, cost
- `replay_scenarios` — stored replay event sequences
- `saved_views` — user-saved UI configurations
- `auth_sessions` — when secure login is added

### Security Rules

These rules apply to the API layer:
1. No execution route (`/api/recs/{id}/execute`) is callable without the recommendation being in `approved` status.
2. Live trading requires an explicit environment flag (`APP_MODE=live`) and separate broker credentials.
3. All role outputs that influence execution are stored with full audit history (prompt version, model used, timestamps).
4. Role outputs are advisory — treated as AI analysis, never as trusted external facts.
5. When deployed with auth, all API endpoints require valid JWT. Approval and execution routes require additional confirmation.

---

## 13. Environment & Configuration

### `.env.example`

```bash
# ─── App Mode ────────────────────────────────────
APP_MODE=paper                     # paper | live
EVENT_MODE=live                    # live | mock | replay
DEMO_MODE=false                    # true = use demo system prompts

# ─── LLM Providers ──────────────────────────────
# At least one required. Roles can use different providers.
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# ─── Market Data ─────────────────────────────────
FMP_API_KEY=...
POLYGON_API_KEY=...                # Optional, Phase 2B+
FRED_API_KEY=...                   # Optional, Phase 3+

# ─── Broker ──────────────────────────────────────
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # paper | live URL

# ─── Strategy Defaults ───────────────────────────
MIN_SURPRISE_PCT=5.0
MIN_MARKET_CAP=1000000000
RISK_PER_TRADE=0.02
STOP_LOSS_PCT=0.05
REWARD_RISK_RATIO=2.0
MAX_GAP_PCT=0.08

# ─── Cost Guardrails ────────────────────────────
DAILY_COST_ALERT_USD=10.0          # Alert if total daily LLM spend exceeds this
PER_ROLE_COST_ALERT_USD=5.0        # Alert if single role exceeds this per day

# ─── Database ────────────────────────────────────
DATABASE_URL=sqlite:///data/aatf.db
# For cloud: DATABASE_URL=postgresql://user:pass@host/aatf

# ─── Server ──────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=3000
CORS_ORIGINS=http://localhost:3000
```

### `backend/app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    app_mode: str = "paper"
    event_mode: str = "live"
    demo_mode: bool = False

    # LLM Providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Market Data
    fmp_api_key: str = ""
    polygon_api_key: str = ""
    fred_api_key: str = ""

    # Broker
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Strategy
    min_surprise_pct: float = 5.0
    min_market_cap: int = 1_000_000_000
    risk_per_trade: float = 0.02
    stop_loss_pct: float = 0.05
    reward_risk_ratio: float = 2.0
    max_gap_pct: float = 0.08

    # Cost
    daily_cost_alert_usd: float = 10.0
    per_role_cost_alert_usd: float = 5.0

    # Database
    database_url: str = "sqlite:///data/aatf.db"

    # Server
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
```

---

## 14. Error Handling & Failure Modes

### LLM Provider Failures

| Failure | Handling |
|---------|----------|
| Provider timeout (>30s) | Retry once. If still fails, mark role analysis as `error` with message. Other roles continue. Trader works with available inputs. |
| Rate limit (429) | Exponential backoff (1s, 2s, 4s). Max 3 retries. If exhausted, fall back to escalation model if different provider, else mark as error. |
| Provider down | SSE pushes `system` event with provider status. Role panels show "Provider unavailable" badge. Trader can still work with partial data. |
| Malformed structured output | Log raw response. Retry once with explicit instruction. If still malformed, use text response only (no structured payload). |
| Context too long | Truncate oldest messages in role history, keeping system prompt + latest 5 exchanges + current analysis. Log truncation. |
| Cost budget exceeded | Alert via SSE. Don't hard-stop — alert only. User decides whether to pause. |

### Broker Failures

| Failure | Handling |
|---------|----------|
| Alpaca unreachable | Portfolio/positions show "Last updated: {time}" with stale badge. Orders queue locally, retry when connection restored. |
| Order rejected | ExecutionRecord status = `failed` with broker_response. Recommendation stays in `approved` state. User notified via SSE. |
| Partial fill | Trade created with actual fill qty. ExecutionRecord shows partial. Recommendation status = `partially_filled`. |

### Market Data Failures

| Failure | Handling |
|---------|----------|
| FMP rate limit | Queue requests, process sequentially with delays. Cache aggressively (quotes: 1 min, earnings: 1 hour, news: 5 min). |
| FMP down | Use cached data with staleness indicator. Scanner shows "Data from {time}" badge. |
| Missing data for a symbol | Skip symbol in scan, log. Don't fail the entire scan. |

### General

- All errors logged with context (which role, which recommendation, which provider).
- SSE pushes error events so the UI can show non-blocking alerts.
- No silent failures — every error is visible somewhere (logs, UI, or both).

---

## 15. Testing Strategy

### Backend Tests

```
tests/
├── test_scanner.py          # PEAD scan logic, filter application
├── test_filters.py          # Each filter in isolation, composability
├── test_state_machine.py    # Every state transition, invalid transitions rejected
├── test_position_sizing.py  # Position calc matches expected values
├── test_roles.py            # Role produces valid structured output (mocked LLM)
├── test_orchestrator.py     # Parallel execution, trader synthesis flow
├── test_routes.py           # API endpoints return correct shapes
├── test_llm_providers.py    # Provider abstraction works for both Anthropic/OpenAI
└── conftest.py              # Fixtures: test DB, mock LLM provider, mock events
```

**Key testing approach:**
- **Mock LLM provider** for unit tests — returns canned structured output so tests are fast, free, and deterministic.
- **Real LLM integration tests** (marked `@pytest.mark.integration`, run manually) — verify actual provider calls work.
- **State machine tests** — every valid transition works, every invalid transition raises. This is the most critical test suite.
- **Scanner tests** — use recorded FMP responses (JSON fixtures) to test scan logic without hitting APIs.
- **Route tests** — FastAPI `TestClient` for endpoint contract testing.

### Human Workflow Tests

The app should be tested against realistic end-to-end flows, not just isolated APIs:

1. **New entry flow:** Earnings event → 3 roles analyse → Trader synthesises → user discusses → approves → paper order submitted → position appears
2. **Conflict resolution flow:** Roles disagree → Trader queries Risk → revised recommendation → user discusses → approves with modified size
3. **Human challenges role:** User chats with Risk → Risk updates analysis → Trader recommendation changes in response
4. **Position management flow:** Event on existing holding → roles analyse impact → Trader recommends SELL/COVER/add → user approves
5. **PASS flow:** Event analysed → Trader recommends PASS with reasoning → user agrees → recommendation closed, audit trail complete
6. **Demo flow:** Mock scenario loaded → replay runs → roles analyse → learner chats with roles → full lifecycle visible

These flows can be automated using mock events + mock LLM provider for CI, or run manually with real LLMs for quality review.

### Frontend Tests

- Component tests with React Testing Library for critical components (RecommendationCard, ApprovalControls, RolePanel).
- No E2E tests initially — manual testing with mock events is sufficient for a single-user app.

### Testing with Mock Events

The mock event system doubles as a testing tool:
- Run the full pipeline with mock events to verify the complete flow without real APIs.
- Pre-built scenarios (earnings beat, risk veto, etc.) serve as integration test cases.
- Cached role responses for each scenario enable deterministic testing.

### Strategy Validation (Pre-Live)

Before any live money:
- Minimum 30 paper trades per strategy
- Review recommendation quality and outcome attribution
- Verify that role outputs are informative, not just verbose
- Track whether the Trader role meaningfully improves over raw signal cards
- Separately review long-entry, long-exit, short-entry, and short-cover recommendation quality

---

## 16. Cost Estimate

### Monthly Spend (Paper Trading, Active Use)

Assumptions: ~5 candidates/day analysed by roles, ~20 human chat messages/day, 22 trading days/month.

| Item | Unit Cost | Monthly Volume | Monthly Cost |
|------|----------|---------------|-------------|
| **Research role** (Sonnet) | ~$0.02/call | 110 analyses + 50 chats | ~$3.20 |
| **Quant role** (Haiku + code) | ~$0.002/call | 110 analyses + 20 chats | ~$0.26 |
| **Risk role** (Sonnet) | ~$0.02/call | 110 analyses + 30 chats | ~$2.80 |
| **Trader role** (Sonnet) | ~$0.03/call | 110 syntheses + 100 chats | ~$6.30 |
| **Shared summaries** (Haiku) | ~$0.001/call | 110 | ~$0.11 |
| **Event triage** (Haiku) | ~$0.001/call | 500 events/day × 22 | ~$11.00 |
| **Inter-role queries** (Sonnet) | ~$0.02/call | ~2 per rec × 110 | ~$4.40 |
| **FMP API** | Current plan | — | Current plan |
| **Polygon.io** | $0-29/mo | — | $0-29 |
| **Total LLM** | | | **~$28/month** |
| **Total with data** | | | **~$30-60/month** |

With prompt caching (system prompts repeated across calls), actual LLM cost could be 30-50% lower.

### Cost Optimisation Levers

- Switch Trader to Haiku for simple PASS decisions (most candidates)
- Increase pre-filter strictness to reduce candidates reaching AI roles
- Cache role analysis and skip re-analysis if no new data
- Run event triage only during market hours
- Use local models for event classification once pipeline is proven

---

## 17. Migration Plan

### What Gets Scrapped

- `dashboard_server.py` — replaced entirely by FastAPI backend
- `dashboard/index.html` — replaced by Next.js frontend
- `phase1/` scripts — already unused by the server, can archive
- `main.py` — replaced by scanner service
- `demo_data.py` — replaced by mock event system
- `Start Dashboard.command`, `Run Scanner.command` — replaced by Makefile

### What Gets Preserved (Refactored)

From `dashboard_server.py`, extract into new service files:

| Current Function | New Location | Changes |
|-----------------|-------------|---------|
| `fmp_earnings_calendar()`, `fmp_quote()`, `fmp_stock_news()`, `fmp_price_target()` | `backend/app/adapters/fmp.py` | Async, typed returns, proper error handling |
| `alpaca_get()`, `alpaca_post()`, `get_alpaca_account()`, `get_alpaca_positions()` | `backend/app/adapters/alpaca.py` | Use `alpaca-py` SDK instead of raw urllib |
| `api_scan_now()` (earnings scan + filter logic) | `backend/app/services/scanner.py` | Break into scan → filter → enrich steps |
| 3-layer filter logic (regime, momentum, gap) | `backend/app/services/filters.py` | Composable filter classes |
| `calculate_position()` | `backend/app/services/position_sizing.py` | Shared service, used by Risk role too |
| `api_accept_trade()` / `api_reject_trade()` | `backend/app/services/state_machine.py` + `routes/recommendations.py` | Full state machine, not just accept/reject |
| CSV read/write helpers | Removed | SQLite replaces CSV |
| `FOCUS_LIST`, strategy params | `backend/app/config.py` + `.env` | Config-driven |

### What Gets Archived

Move to `archive/` directory (not deleted, just out of the way):
- `dashboard_server.py`
- `dashboard/`
- `phase1/`
- `main.py`
- `demo_data.py`
- `requirements.txt`
- `*.command` files
- `SETUP.md`

### Migration Steps

1. Create `frontend/` and `backend/` directories
2. Set up FastAPI app with config loading from `.env`
3. Create SQLite schema
4. Port FMP adapter (async, typed)
5. Port Alpaca adapter (using alpaca-py SDK)
6. Port scanner service (refactored into scan → filter → enrich)
7. Port position sizing service
8. Implement state machine
9. Implement role system (base class, four roles, orchestrator)
10. Implement LLM provider abstraction (Anthropic first, OpenAI second)
11. Implement API routes
12. Implement SSE event stream
13. Set up Next.js app
14. Build three-column layout
15. Build event feed component
16. Build role chat panels
17. Build recommendation card + approval controls
18. Build open positions panel
19. Connect frontend to backend via API + SSE
20. Build mock event system
21. Test full flow with mock events
22. Test full flow with real FMP/Alpaca data
23. Archive old files

---

## 18. Build Order

### Milestone 1: Foundation

**Goal:** Backend scaffolding, database, adapters, and core services. No UI yet.

Build:
- FastAPI app structure (config, database, models)
- SQLite schema with all tables
- LLM provider abstraction (Anthropic + OpenAI implementations)
- FMP adapter (async, refactored from current `dashboard_server.py`)
- Alpaca adapter (using `alpaca-py` SDK)
- Scanner service (refactored PEAD scan → filter → enrich pipeline)
- Filter service (composable, configurable)
- Position sizing service
- Recommendation state machine with all transitions
- Basic API routes for: scan, portfolio, positions, trades
- Tests for scanner, filters, state machine, position sizing

**Done when:** `POST /api/scan` returns candidates, `GET /api/portfolio` returns Alpaca data, state machine tests pass.

### Milestone 2: Workstation Shell

**Goal:** Three-column UI connected to backend. No AI roles yet — static/mock data in role panels.

Build:
- Next.js project with Tailwind dark theme
- Three-column layout (EventFeed + Watchlist | RolePanels + SharedSummary | TradeDeck)
- Event feed with type/importance filters
- Role panel shells (collapsible, chat input, placeholder messages)
- Recommendation card with entry/stop/target + `_logic` reasoning
- Approval controls (Approve/Reject/Discuss, state-aware visibility)
- Open positions with live P&L from Alpaca
- Pending ideas queue and recent history
- SSE connection with auto-reconnect
- Watchlist panel with active symbols
- Inline terminology tooltips for trading terms
- Dark theme, dense but readable

**Done when:** Full layout renders, event feed shows data from `/api/events`, positions show from Alpaca, recommendation card displays correctly for each state.

### Milestone 3: Role Workflow

**Goal:** Four AI roles producing real analysis, Trader querying other roles, full approval flow.

Build:
- Role system (BaseRole class, four role implementations, system prompts)
- Orchestrator (parallel Research + Quant + Risk → Trader synthesis with inter-role querying)
- API routes: `/api/roles/{name}/analyse`, `/api/roles/{name}/chat`, `/api/roles/{name}/history`
- Shared summary generation
- Cost tracking per role, per recommendation, per day
- SSE events for role messages, queries, recommendation updates
- Connect role panels to real API
- Recommendation card shows full Trader output
- "Show the discussion" timeline view

**Done when:** A scan triggers role analysis, Trader produces a recommendation, user can chat with any role, approve/reject works end-to-end, paper order hits Alpaca.

### Milestone 4: PEAD-Plus Intelligence

**Goal:** Richer signals for the Research role. Better recommendations.

Build:
- Earnings call transcript ingestion
- Guidance change detection
- Catalyst/risk extraction
- Beat quality analysis
- SUE chain tracking
- Estimate revision momentum scoring
- All surfaced as context to Research role

**Done when:** Research role references transcript content and guidance changes in its analysis. Recommendations are noticeably more informed.

### Milestone 5: Demo and Replay

**Goal:** Educational mode is presentation-ready.

Build:
- Mock event generator with 5 pre-built scenarios
- Replay mode (historical event sequences at variable speed)
- Demo system prompts (more explanatory, teaches as it analyses)
- `POST /api/events/mock` and `POST /api/events/replay` endpoints
- Mode toggle in UI (Live / Demo)
- Demo role badges/descriptions for learners
- Pre-cached role responses for common scenarios (cost savings)

**Done when:** A non-trader can load a demo scenario, watch roles analyse, chat with them, and understand what happened — without being told how the app works.

### Milestone 6: Production Hardening

**Goal:** Ready to publish online with secure access.

Build:
- NextAuth.js authentication
- HTTPS, server-side auth checks on approval/execution routes
- Deploy to Fly.io / Railway (Next.js + FastAPI + Postgres)
- Monitoring and error alerting
- Model-cost dashboards
- Circuit breaker (halt on 15% drawdown)
- Email/SMS alerts on new recommendations

**Done when:** App is live at a URL, login required, paper trading works through the public interface.

### Milestone 7: Multi-Strategy Expansion

**Goal:** Strategies beyond PEAD.

Build:
- Polygon.io adapter (real-time streaming)
- FRED adapter (macro indicators)
- EdgarTools adapter (SEC filings)
- Sentiment overlay strategy
- Macro/sector rotation strategy
- Strategy selector in UI
- Embeddings + retrieval for historical recommendations
- VectorBT / Qlib integration for backtesting
- 30+ paper trades per strategy before live

---

## 19. Educational / Demo Mode

### How It Works

Same app, config toggle (`DEMO_MODE=true`, `EVENT_MODE=mock`), not a separate product.

| Aspect | Live | Demo |
|--------|------|------|
| Market data | Real APIs | Mock or replay events |
| Execution | Real Alpaca orders | Simulated fills |
| Role prompts | Concise, professional | Conversational, explains terminology |
| Trader queries | Focused on quality | Narrates why it's asking each question |
| Cost | Full LLM cost | Same, or cheaper models + cached responses |

### Pre-Built Scenarios

1. **"The Earnings Beat"** — Teaches: earnings surprises, how roles evaluate differently
2. **"The Risk Veto"** — Teaches: risk management, sector concentration
3. **"The Guidance Downgrade"** — Teaches: earnings vs guidance, misleading headlines
4. **"The Macro Shift"** — Teaches: Fed impact, sector rotation
5. **"The Disagreement"** — Teaches: handling conflicting inputs, conviction scoring

### "Show the Discussion" Timeline

When a recommendation is selected, render the full lifecycle as a readable narrative:
1. Triggering event → 2. Each role's analysis → 3. Trader's queries → 4. Draft recommendation → 5. User discussion → 6. Final decision

### What Each Role Teaches

| Role | Real-World Equivalent | Teaches |
|------|----------------------|---------|
| Research | Equity research analyst | Earnings, thesis construction, fundamental analysis |
| Quant Pricing | Quantitative analyst | Price levels, volatility, expected moves |
| Risk | Risk management | Position sizing, portfolio construction, why good ideas get rejected |
| Trader | Portfolio manager | Decision synthesis, conviction, when to act vs pass |

### Replay Mode

Play back real historical sessions as interactive case studies:
- "It's March 31st, 2026. NKE reports +20.7% EPS surprise. What happens?"
- Pause at any point to chat with roles
- Compare your decision against what actually happened

---

## 20. Python Dependencies

### Phase 2A

```
# Backend core
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.0
pydantic-settings>=2.0
python-dotenv>=1.0
aiosqlite>=0.20
alembic>=1.13                # DB migrations

# LLM providers
anthropic>=0.40
openai>=1.50

# Broker
alpaca-py>=0.30

# SSE
sse-starlette>=2.0

# Testing
pytest>=8.0
pytest-asyncio>=0.24
httpx>=0.27                  # FastAPI TestClient
```

### Phase 3

```
fredapi>=0.5
edgartools>=2.0
polygon>=1.0
```

### Phase 4

```
vectorbt>=0.26
# qlib has heavy deps, install in venv
```

---

## 21. API Keys Required

```
# Phase 2A (at least one LLM provider required)
ANTHROPIC_API_KEY            # Claude models
OPENAI_API_KEY               # GPT models (optional if using Anthropic)

# Phase 2A (already have)
FMP_API_KEY
ALPACA_API_KEY
ALPACA_SECRET_KEY

# Phase 2B+
POLYGON_API_KEY              # Real-time streaming (free tier available)

# Phase 3+
FRED_API_KEY                 # Free, request from FRED website
```

---

## 22. Open-Source Projects

### Use Now

| Project | Purpose |
|---------|---------|
| **FastAPI** | Backend framework |
| **anthropic** SDK | Claude API calls |
| **openai** SDK | GPT API calls |
| **alpaca-py** | Broker SDK |
| **TradingView lightweight-charts** | Frontend price charts |
| **React Query (TanStack)** | Frontend server state |

### Study / Reference

| Project | Purpose |
|---------|---------|
| **TradingAgents** (~49k stars) | Agent prompt designs, role architecture patterns |
| **CrewAI** (~48.6k stars) | Agent orchestration (adopt if custom outgrows) |
| **LangGraph** (~28.9k stars) | Workflow patterns (adopt if complexity warrants) |
| **FinGPT** (~19k stars) | Financial NLP fine-tuning experiments |

### Use Later

| Project | When |
|---------|------|
| **Qlib** | Phase 4 — strategy validation |
| **VectorBT** | Phase 4 — rapid backtesting |
| **EdgarTools** | Phase 3 — SEC filings |
| **LEAN** | Phase 5+ — production trading engine (only if needed) |

---

## 23. Makefile

```makefile
.PHONY: dev dev-frontend dev-backend test lint migrate seed-mock db-reset

# Start both frontend and backend
dev:
	make dev-backend & make dev-frontend

dev-frontend:
	cd frontend && npm run dev

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

# Tests
test:
	cd backend && pytest -v

test-integration:
	cd backend && pytest -v -m integration

# Database
migrate:
	cd backend && alembic upgrade head

db-reset:
	rm -f data/aatf.db && make migrate && make seed-mock

seed-mock:
	cd backend && python -m app.services.mock_events --seed

# Lint
lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint
```

---

## Sources

- Current system: `/Users/benwekes/work/trading/CLAUDE_CODE_HANDOFF.md`
- TradingAgents: https://github.com/TauricResearch/TradingAgents
- CrewAI: https://github.com/crewAIInc/crewAI
- LangGraph: https://github.com/langchain-ai/langgraph
- Qlib: https://github.com/microsoft/qlib
- FinGPT: https://github.com/AI4Finance-Foundation/FinGPT
- FinRL: https://github.com/AI4Finance-Foundation/FinRL
- LEAN: https://github.com/QuantConnect/Lean
- EdgarTools: https://github.com/dgunning/edgartools
- Anthropic API: https://docs.anthropic.com/en/docs/about-claude/models/all-models
- Anthropic tool_use: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- OpenAI API: https://platform.openai.com/docs/models
- OpenAI function_calling: https://platform.openai.com/docs/guides/function-calling
- Polygon.io: https://polygon.io/docs
- FRED: https://fred.stlouisfed.org/docs/api/fred/
- Benzinga: https://www.benzinga.com/apis/data/
- Loughran-McDonald Sentiment: https://sraf.nd.edu
- TradingView lightweight-charts: https://github.com/nicola-nicola/react-lightweight-charts
