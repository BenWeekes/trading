# Trading Plan Codex

Last updated: 2026-04-11

## App Summary

The app should evolve from the current PEAD paper-trading dashboard into a trader workstation for event-driven and research-assisted trading.

It should also work as an educational and demonstration platform that helps explain how different roles inside an investment bank, hedge fund, or trading desk think about the same market situation from different angles.

Version 1 should still support the existing PEAD flow:
- ingest earnings, news, quotes, and portfolio state
- surface actionable candidates
- let AI roles discuss what matters
- have a trader role turn that discussion into a concrete recommendation
- require explicit user approval before any order is sent
- show open trades, pending recommendations, and a full audit trail

The longer-term direction should be broader than PEAD. The same workstation can later support:
- earnings drift and post-event continuation
- analyst revision and price-target change trades
- news and catalyst-driven setups
- macro and rates-aware overlays
- portfolio/risk overlays across multiple active ideas
- semi-systematic discretionary trading where AI roles structure the decision but the human still approves execution

The target user experience is:
- a live event feed for news, pricing, earnings, and internal alerts
- separate mini-chat panels for `research`, `risk`, `quant_pricing`, and `trader`
- a shared rolling summary of what the system believes right now
- a recommendation panel with entry, sizing, invalidation, target, confidence, and rationale
- an approval gate before execution
- open positions and recommendation history visible in the same screen

The operating model should be:
- single-user first
- paper trading first
- secure login required once the app is published online
- separate context and AI session per role
- flexible enough to use different AI models for different roles
- cheap enough to run routinely without wasting tokens on every event
- explainable enough to teach role-based thinking to a human observer or student

## Product Direction

This should not be built as "three AI labels on a stock card." It should be built as a stateful decision system with four role views:

- `research`: explains narrative, earnings quality, guidance, catalysts, management tone, and why the market may still be underreacting
- `risk`: challenges the thesis, flags event risk, liquidity, crowding, macro sensitivity, earnings blackout issues, and portfolio overlap
- `quant_pricing`: frames price response, gap context, volatility, target/stop logic, expected move, and tactical levels
- `trader`: synthesizes the other roles into a proposed trade and discusses it with the user before requesting approval

The key architectural rule is to keep chat separate from structured outputs. Each role should produce:
- human-readable discussion text
- structured fields the trader and UI can consume

This should also be a good-looking workstation, not just a functional dashboard. The UI should prioritize:
- clarity of current market context
- visibility into role disagreement
- clean recommendation and approval flow
- dense but readable information layout
- a simple mental model for what is happening now, what is proposed, and what is already live

The product should support two modes of value at the same time:
- operational mode: help make better paper-trading and eventually live-trading decisions
- educational/demo mode: make each role legible, interactive, and interesting enough for teaching and presentation purposes

The educational/demo mode should use the same underlying role system, UI, and data objects as the live trading mode. It should rely on mock or replayed events and more explanatory prompts, not on a separate throwaway architecture.

## Strategy Scope and Priority

The platform should support multiple strategies over time, using the same role-based workflow. The roles change their reasoning context by strategy, but the user experience stays consistent.

### Priority 1: PEAD and earnings extensions

This remains the best first strategy family because it extends the current working system and offers high value from AI interpretation.

Include:
- classic PEAD
- beat quality analysis
- guidance change detection
- catalyst and risk extraction
- conference call and transcript interpretation
- estimate revision momentum
- surprise streak or SUE-chain style tracking

Why first:
- strongest continuity with the current app
- direct path from current paper trading into richer decision support
- strong LLM fit for press releases, transcripts, and management language

### Priority 2: sentiment and news overlay

Use this as an overlay on existing strategies before treating it as a standalone trading engine.

Include:
- company news sentiment shifts
- analyst tone changes
- narrative and theme detection
- "why is it moving?" event framing

Why next:
- improves event feed usefulness
- helps the role system explain moves in plain English
- likely useful across multiple strategy types

### Priority 3: macro and sector context

Add a top-down context layer that influences risk and trader recommendations.

Include:
- risk-on / risk-off regime
- rates and inflation context
- sector rotation signals
- Fed and macro-language interpretation

Why next:
- useful across all strategy families
- relatively low-cost data additions
- especially valuable for the `risk` and `trader` roles

### Priority 4: event-driven strategies

Add these after the workstation and data model are stable.

Include:
- activist filings
- merger and acquisition situations
- material 8-K events
- spin-offs and index changes
- regulatory catalysts

Why later:
- high value, but requires more new data plumbing and event-specific logic

### Lower priority: pure technical/momentum and options

These should remain on the roadmap, but not drive the first workstation build.

Reason:
- pure technical strategies provide less differentiated value from LLM roles
- options add significant execution and risk complexity
- both can fit later once the workstation and trade lifecycle are proven

## Recommended Open-Source Projects

These are the strongest building blocks for the app as it expands beyond PEAD.

### 1. Custom orchestration first, LangGraph later if needed

Start with a custom orchestration layer built around explicit Python services and parallel async role execution.

Why it fits:
- the initial workflow is predictable: event -> research/risk/quant in parallel -> trader synthesis -> approval
- easier to debug than introducing a graph framework on day 1
- lower dependency and conceptual overhead for the MVP
- keeps the orchestration logic legible while the workflow is still stabilizing

Adopt LangGraph later only if:
- the workflow becomes materially more branching or stateful
- multiple resumable subflows become hard to manage manually
- orchestration complexity clearly exceeds a clean custom service layer

Primary source:
- https://github.com/langchain-ai/langgraph

### 2. Direct data adapters first, OpenBB later if it earns its place

Start with direct adapters for the providers you actually use: `FMP`, `Alpaca`, later `Polygon`, `FRED`, and `EDGAR`.

Why it fits:
- avoids unnecessary abstraction in the MVP
- easier to understand cost, latency, and failure behavior per provider
- keeps the system honest about which upstreams it truly depends on

OpenBB remains worth tracking for later research workflows, but it should not be a required dependency for the first build.

Primary sources:
- https://docs.openbb.co/
- https://docs.openbb.co/platform/data_models

### 3. Qlib for quant research and model evaluation

Use Microsoft Qlib as the research and evaluation layer for future strategy expansion. It is stronger for quant research workflows than for the live workstation itself.

Why it fits:
- built for AI-oriented quantitative research
- covers data processing, model training, backtesting, portfolio optimization, and order-execution research
- useful once the app moves from single-strategy PEAD into multi-strategy signal research

Use it for:
- validating whether PEAD sub-signals actually improve outcomes
- researching analyst-revision, factor, or hybrid event signals
- offline ranking models and scorecards for idea quality

Primary source:
- https://github.com/microsoft/qlib

### 4. LEAN or NautilusTrader for future production-grade execution research

Do not make this the first integration. The current app already talks to Alpaca directly, which is fine for early paper trading. But if the system grows into a more serious multi-strategy platform, a dedicated trading engine becomes attractive.

LEAN is the safer default recommendation for breadth and ecosystem.
NautilusTrader is attractive if low-latency, event-driven architecture, and production-style trading workflows become more important later.

Use one of them later for:
- richer backtesting/live parity
- brokerage abstraction
- execution/risk modeling beyond simple bracket orders

Primary sources:
- LEAN: https://github.com/QuantConnect/Lean
- LEAN docs: https://www.quantconnect.com/docs/v2/lean-engine
- NautilusTrader: https://nautilustrader.io/open-source/

### 5. FinGPT as an optional finance-specific research component

FinGPT is worth treating as optional and experimental, not as the core model layer.

Why it fits:
- useful for finance-specific prompt patterns, sentiment tasks, and domain experiments
- helpful if you want to compare a finance-tuned open model against general-purpose frontier models

Why it should not be the default brain:
- finance-specific open models are useful, but current workstation quality will depend more on orchestration, grounding, and structured outputs than on swapping in a finance-branded model
- for high-stakes recommendation quality, strong general reasoning models will usually be the better primary system

Primary source:
- https://github.com/AI4Finance-Foundation/FinGPT

### 6. EdgarTools for SEC and filing workflows

Use EdgarTools once the app expands into event-driven and deeper fundamental workflows.

Why it fits:
- provides structured access to SEC filings and XBRL data
- useful for 8-K, 10-Q, 10-K, and activist/event-driven workflows
- helpful for earnings-quality and filing-based research expansion

Use it for:
- activist stake monitoring
- material event analysis
- filing-driven risk review
- earnings-quality and accrual-oriented analysis

Primary source:
- https://github.com/dgunning/edgartools

## Recommended AI Model Stack

The app should use a tiered model strategy rather than a single model everywhere.

Each role should have its own context window, chat history, and model assignment. Roles should not share one monolithic AI session.

Recommended role/session design:
- `research`: own prompt, own memory, own evidence set
- `risk`: own prompt, own memory, own portfolio and risk context
- `quant_pricing`: own prompt, own memory, own pricing and market context
- `trader`: own prompt, own memory, sees summarized outputs from the other roles

This gives cleaner specialization, lowers prompt bloat, and makes it easier to mix models by role.

The orchestration layer should support a per-role configuration that includes:
- model
- prompt version
- tool permissions
- escalation policy
- cost budget

### Primary reasoning model

Use a frontier reasoning model for the `trader` role and for any final synthesis that can affect recommendations.

Recommended options:
- OpenAI GPT-5.2 as a primary general reasoning model
- Anthropic Claude Sonnet 4 or Opus 4.1 as strong alternatives for deep synthesis and long-context analysis

Why:
- the trader role is the highest-consequence reasoning step
- this role has to synthesize conflicting inputs from research, risk, quant pricing, portfolio state, and user discussion
- this is where you want the strongest reasoning and the cleanest structured output

Primary sources:
- OpenAI models: https://platform.openai.com/docs/models
- OpenAI latest-model guide: https://platform.openai.com/docs/guides/latest-model
- Anthropic models overview: https://docs.anthropic.com/en/docs/about-claude/models/all-models

### Fast/cheap role-update model

Use a smaller, cheaper model for frequent event classification and role drafts.

Recommended options:
- OpenAI GPT-5 mini
- a fast Claude tier such as Haiku for lightweight role updates
- optionally an open-weight local model later for low-cost background tagging

Use it for:
- headline triage
- event classification
- extracting structured fields from press releases or articles
- drafting first-pass role notes before escalation to the main reasoning model

Suggested role routing:
- `research`: smaller model by default, escalate on transcripts or complex filings
- `risk`: smaller or mid-tier model for routine checks, stronger model when portfolio context is complex
- `quant_pricing`: often deterministic code plus a light model layer for explanation
- `trader`: strongest model by default because this is the user-facing recommendation layer

Primary sources:
- OpenAI models: https://platform.openai.com/docs/models
- Anthropic model docs: https://docs.anthropic.com/en/docs/about-claude/models/all-models

### Embeddings and retrieval

Use embeddings for retrieval across:
- prior recommendations
- historical role discussions
- earnings excerpts
- internal notes and playbooks

Recommended options:
- OpenAI `text-embedding-3-large` or `text-embedding-3-small`
- optional local embedding models later if data residency or cost becomes more important

Primary source:
- https://platform.openai.com/docs/models

### Open-weight model track

Keep an open-weight path in the architecture even if the first production-quality build uses hosted frontier models.

Recommended options to watch:
- OpenAI `gpt-oss-20b` / `gpt-oss-120b`
- Qwen-family open models for lower-cost local experimentation
- finance-specific open models only as secondary experiments

Why:
- lowers future vendor lock-in
- useful for local background labeling and non-critical batch work
- creates an upgrade path for private or on-device workflows

Primary sources:
- OpenAI models: https://platform.openai.com/docs/models
- Qwen model docs: https://huggingface.co/docs/transformers/en/model_doc/qwen3

## Recommended System Shape

### Data and event layer

Short term:
- keep the existing FMP and Alpaca integrations running
- add an internal event model for `news`, `price`, `earnings`, `position_change`, and `recommendation_update`

Medium term:
- broaden direct provider coverage as needed
- add a shared internal data abstraction only when multiple providers actually create duplication

Recommended data expansion:
- `FMP` for current earnings, quotes, and basic fundamentals/news
- `Polygon` later for stronger real-time streaming and options data
- `FRED` for macro indicators and regime context
- `SEC EDGAR` via EdgarTools for filing-driven workflows
- optionally `Benzinga` later if higher-grade trading news proves worth the cost

The event system should also support:
- live market events
- mock events for demos and education
- replayed historical event sequences for testing workflows

### Agent and workflow layer

Use a custom orchestration service to manage:
- role execution
- role-to-role querying
- user approval state
- retries and escalation
- recommendation lifecycle updates

Keep the orchestration boundary explicit so LangGraph or another workflow framework can be introduced later if complexity justifies it.

Use Model Context Protocol only if it materially helps tool modularity later.

Primary source:
- https://docs.anthropic.com/en/docs/mcp

### UI layer

The main screen should be a workstation, not a card list.

Recommended layout:
- left column: incoming events and watchlist context
- center column: shared group chat, directed role discussion, and shared summary
- right column: embedded trader avatar, trader recommendation, approval controls, open positions, and pending ideas

### Execution layer

Keep human approval mandatory.

Execution should only happen after a recommendation object moves through:
- `draft`
- `awaiting_user_approval`
- `approved`
- `submitted`
- `filled` or `failed`

This approval workflow is more important than adding more agent autonomy.

### Local dev and cloud prod

The system should be designed to run in two modes from the beginning:
- local development on your machine
- cloud deployment for production once published

That means the app should avoid hard-wiring local file state, single-process assumptions, or UI logic that depends on one machine session.

Recommended environment split:

Local development:
- run the app with local services and local credentials
- use paper trading only
- allow mocked or replayed event streams for UI development
- keep fast startup and minimal operational overhead

Cloud production:
- deploy the same app shape behind authentication
- use managed storage for state, audit trail, and recommendation history
- keep approval and execution flows durable across restarts
- support secure secret management and role/user access controls

Recommended architectural rule:
- keep business logic portable across environments
- isolate environment-specific concerns behind configuration

In practice this means:
- configuration via environment variables
- adapter interfaces for market data, execution, and storage
- persistent state in a real database rather than only CSV or in-memory state
- real-time updates via a transport that works both locally and in cloud environments

Recommended storage split:
- local dev can use SQLite for simplicity
- cloud prod should use Postgres or another managed relational database

Recommended deployment split:
- local dev can run as a single app stack
- cloud prod should allow frontend, backend, worker, and scheduler concerns to be separated if needed

Recommended real-time pattern:
- use a standard API plus websocket or SSE updates for event feeds and role/recommendation changes
- keep the event model identical in local and cloud modes

This requirement also strengthens the case for:
- a proper recommendation state machine
- durable role/recommendation history
- explicit execution records
- modular data and broker adapters

The main planning consequence is that the next version should be built as a real application platform, not as a single-script local dashboard, even if the first release still runs comfortably on one machine.

## Build Order

### Phase A: trader workstation foundation

Build first:
- event feed
- role panels
- structured recommendation object
- approval state machine
- open trades panel
- recommendation history/audit trail

Do not build first:
- autonomous trading
- model fine-tuning
- cloud deployment
- many strategy types at once

### Phase B: PEAD-plus intelligence

Add:
- earnings press-release extraction
- guidance change detection
- catalyst/risk extraction
- trader synthesis over those fields

This preserves the current PEAD edge while making the interface much more useful.

### Phase C: broader strategy expansion

Add:
- analyst revisions
- economic calendar and macro events
- position overlap/risk budgeting
- cross-idea ranking
- offline research loops with Qlib

### Phase D: event-driven and publication hardening

Add:
- filing and event-driven strategy support
- secure login for the published app
- stronger role and user audit trail
- production deployment and monitoring
- alerts and notification workflows

## Recommended Decisions

These are the concrete decisions I would make now.

1. Keep the current Python dashboard alive as the seed product, but stop thinking of the next phase as "add three AI classifiers."
2. Build the next version around a workstation UX with role-based state, not around stock cards.
3. Use custom orchestration first; only adopt LangGraph later if workflow complexity clearly warrants it.
4. Use direct provider adapters first; consider OpenBB later if it meaningfully reduces integration duplication.
5. Keep the app single-user at first, but design for secure login when it is published online.
6. Give each role its own context, chat history, and model assignment.
7. Use a top-tier general reasoning model for trader synthesis and approval-facing outputs.
8. Use smaller models for cheap event triage and role drafts.
9. Keep the system paper-trading first and only move to real money after validation.
10. Optimize for a UI that is both visually strong and operationally easy to understand.
11. Expand strategy coverage gradually, starting with PEAD and earnings extensions.
12. Treat FinGPT and finance-specific open models as experimental sidecars, not the core recommendation engine.
13. Delay migration to LEAN or NautilusTrader until the workstation and decision model are stable.

## Recommended Technical Stack

If the goal is to support both local development and cloud production cleanly, this is the stack I would recommend.

### Frontend

Recommended:
- Next.js with React and TypeScript
- a component system that supports a dense workstation UI without fighting the layout
- websocket or SSE client support for live updates

Why:
- strong local developer experience
- straightforward cloud deployment path
- good fit for a rich multi-panel interface
- can handle authenticated app flows later without changing frameworks

The frontend should own:
- event feed rendering
- role chat panels
- recommendation and approval UI
- open trades and history views
- local UI state and optimistic interaction behavior

### Backend API

Recommended:
- Python backend using FastAPI

Why:
- strong fit with the current Python-based trading codebase
- good ergonomics for data APIs, typed schemas, and async endpoints
- easy to integrate with provider adapters, execution logic, and a custom orchestration layer

The backend should own:
- event ingestion APIs
- recommendation and approval APIs
- position and portfolio APIs
- auth/session integration later
- orchestration entrypoints for role workflows

### Agent and worker layer

Recommended:
- Python worker processes for role orchestration and event processing
- custom orchestration services first
- a queue or job system if background processing becomes meaningful

Why:
- keeps longer-running analysis away from the request/response API path
- makes cloud deployment more reliable
- easier to scale event processing separately from the UI

Early on, this can still run in one local process group.
Later, it can separate into:
- web app
- API
- background worker
- scheduler/event poller

### Database

Recommended:
- SQLite for local development
- Postgres for cloud production

Core tables or collections should cover:
- incoming events
- role messages
- shared summaries
- recommendations
- approval records
- executions
- open and closed trades
- model runs and audit metadata

Why:
- you need durable state, not just CSVs
- recommendations and approvals are workflow records, not transient UI data
- Postgres gives a clean production path without changing the data model too much

Single-user now does not change this recommendation. Even with one user, durable workflow state matters because trade recommendations, approvals, and executions must survive restarts and be auditable.

### Real-time updates

Recommended:
- start with server-sent events or websockets

Use for:
- incoming market/news events
- role message updates
- recommendation status changes
- execution and position changes

Why:
- the workstation should feel alive
- polling alone will make the multi-role UX feel laggy and fragmented

### Storage and secrets

Recommended:
- environment variables for local secrets
- managed secrets in cloud production
- object storage only if later needed for transcripts, PDFs, or archived artifacts

### Deployment path

Recommended first production shape:
- Next.js frontend
- FastAPI backend
- Python worker
- Postgres
- one cloud host or platform that can run these pieces with managed secrets and networking

Possible cloud targets later:
- Fly.io
- Railway
- Render
- a more custom AWS/GCP setup if the system becomes materially more complex

### Why this stack is the best fit now

This stack preserves the strengths of the current system:
- Python for trading logic, data integration, and orchestration

It also fixes the current structural limitations:
- better UI foundation than a static HTML dashboard
- durable state instead of CSV-centric workflow state
- clean local-to-cloud portability
- a practical path to real-time updates and role-based interaction
- room for a polished, modern workstation-style interface

### What not to do

I would avoid these choices for the next version:
- keeping all logic in a single Python script
- building the workstation as mostly server-rendered HTML plus ad hoc JavaScript
- putting long-running agent workflows directly inside the frontend
- coupling core recommendation state to in-memory objects or CSV files
- overcommitting to a heavyweight trading engine before the workstation UX is proven

## MVP Scope

The first build should be a focused, publishable MVP, not an everything-platform.

### In scope for MVP

- single-user workstation
- paper trading only
- PEAD and earnings-extension workflows
- event feed for earnings, news, pricing, and internal recommendation updates
- four role panels: `research`, `risk`, `quant_pricing`, `trader`
- direct human chat with each role
- trader ability to question other roles before updating a recommendation
- shared summary panel
- structured recommendation object with approval workflow
- open positions panel
- recommendation history and execution history
- action support for opening, reducing, closing, and shorting positions in paper mode
- local development mode
- cloud-ready architecture
- secure login for the published version, even if local dev starts without full auth
- mock and replay event modes for demos and teaching

### Explicitly out of scope for MVP

- autonomous execution
- live capital deployment
- options trading
- multi-user collaboration
- full broker abstraction
- dozens of strategies at once
- sophisticated portfolio optimization
- on-device open-weight inference as a required component
- full historical backtesting platform integrated into the main app

### MVP success criteria

The MVP is successful if it can:
- ingest or simulate market events
- let all four roles analyse and discuss a symbol
- produce a clear trader recommendation with visible influences
- let the human discuss and approve or reject
- track open paper trades and recommendation history
- operate cheaply enough for regular use
- function well enough visually to demo to another person without apology

## System Components

The system should be split into a few clear components.

### 1. Frontend workstation

Responsibilities:
- render the event feed
- show role chat panels and shared summary
- show recommendation, approval, and position state
- manage active symbol focus
- support mock/demo mode toggles

Recommended runtime:
- Next.js app

### 2. Backend API

Responsibilities:
- serve portfolio, position, recommendation, role, and event APIs
- accept user chat inputs
- accept approval and rejection actions
- provide real-time event and state streams
- expose health and admin endpoints

Recommended runtime:
- FastAPI

### 3. Orchestration worker

Responsibilities:
- trigger role analyses
- maintain recommendation workflow state
- invoke models according to role config
- update shared summaries
- request execution after approval

Recommended runtime:
- Python worker process using explicit orchestration services

### 4. Event ingestion layer

Responsibilities:
- poll or receive upstream market/news/earnings inputs
- normalize inputs into `IncomingEvent`
- support mock and replay events

### 5. Execution adapter

Responsibilities:
- submit paper orders
- read account and position state
- persist broker responses
- later support live mode behind explicit configuration

### 6. Storage layer

Responsibilities:
- persist role threads and messages
- persist recommendations and approvals
- persist executions and open trades
- persist event stream history
- persist cost and model telemetry

## Backend API Plan

These are the logical endpoints the app should support. Final naming can change, but the capabilities should not.

### Events

- `GET /api/events`
- `POST /api/events/mock`
- `POST /api/events/replay`
- `GET /api/events/stream`

Purpose:
- list filtered events
- inject demo events
- replay historical scenarios
- stream live updates to the frontend

### Roles

- `GET /api/roles`
- `GET /api/roles/{role}/threads`
- `GET /api/roles/{role}/threads/{thread_id}`
- `POST /api/roles/{role}/chat`
- `POST /api/roles/{role}/analyze`

Purpose:
- inspect role configuration
- load role histories
- chat directly with a role
- trigger analysis for a symbol or recommendation

### Summaries and recommendations

- `GET /api/recommendations`
- `GET /api/recommendations/{id}`
- `POST /api/recommendations/{id}/refresh`
- `POST /api/recommendations/{id}/approve`
- `POST /api/recommendations/{id}/execute`
- `POST /api/recommendations/{id}/reject`
- `GET /api/summaries/{recommendation_id}`

Purpose:
- manage the full recommendation lifecycle
- support user approval and rejection
- keep approval and execution as separate auditable actions
- expose the current synthesized state

### Portfolio and execution

- `GET /api/portfolio`
- `GET /api/positions`
- `GET /api/executions`
- `POST /api/execution/submit/{recommendation_id}`

Purpose:
- show live account and position state
- track order/execution history
- allow execution only after approval

### Settings and admin

- `GET /api/settings`
- `PATCH /api/settings`
- `GET /api/health`
- `GET /api/model-usage`

Purpose:
- configure paper/live mode, model routing, and feature flags
- inspect system health
- track cost and model behavior

## Persistence Plan

The database schema should be centered on workflow records.

### Recommended primary tables

- `incoming_events`
- `role_threads`
- `role_messages`
- `shared_summaries`
- `trade_recommendations`
- `approval_records`
- `open_trades`
- `execution_records`
- `model_usage_records`
- `user_settings`
- `strategy_configs`

### Recommended derived or support tables later

- `daily_metrics`
- `replay_scenarios`
- `watchlists`
- `saved_views`
- `auth_sessions`

### Data-retention principle

Do not discard reasoning history by default. Role discussion, recommendation evolution, and approval timestamps are important for:
- trust
- debugging
- teaching
- post-trade review

## Auth and Security Plan

The app is single-user first, but the published version should still have real auth.

### Local development

- simple local auth can be optional at first
- secrets via environment variables
- paper trading only

### Published version

- secure login required
- encrypted secrets management
- HTTPS only
- server-side authorization checks on recommendation approval and execution routes
- audit records for approvals and executions

### Security rules

- no execution route should be callable without an approved recommendation
- live trading should require an explicit environment flag and separate credentials
- prompt inputs that can affect execution should be stored in audit history
- role outputs should be treated as advisory, not as trusted external facts

## Real-Time and Eventing Plan

The app should feel live.

### Recommended approach

- standard REST APIs for reads and commands
- SSE or websockets for real-time updates

### Streamed update types

- new event arrived
- role message created
- shared summary updated
- recommendation status changed
- approval recorded
- execution updated
- position updated

### Replay mode

Replay mode should let you feed a historical sequence of events into the workstation at accelerated or step-through speed. This is useful for:
- demos
- teaching
- UI testing
- role prompt evaluation

## Model and Prompt Operations

The app should treat prompts and model routing as configurable system assets.

### Per-role config fields

- `role_name`
- `model_provider`
- `model_name`
- `system_prompt_version`
- `temperature`
- `max_tokens`
- `tools_enabled`
- `escalation_model`
- `cost_budget_daily`
- `cost_budget_per_recommendation`

### Prompt management

- version prompts explicitly
- keep role prompts in source-controlled files
- track which prompt version produced each role message and recommendation

### Escalation policy

Default:
- cheap or mid-tier role model first
- escalate only when event importance, context length, or disagreement justifies it

Escalation triggers may include:
- long transcript or filing
- strong disagreement between roles
- high-importance event
- user explicitly asks for deeper analysis

## UX and Design Direction

The workstation should look intentional and premium, not like an internal admin tool.

### Visual direction

- dark, high-contrast trading-desk layout is acceptable, but avoid generic dark dashboard styling
- make each role visually distinct without turning the screen into a toy
- use typography, spacing, and hierarchy to make the decision flow obvious
- highlight disagreement and uncertainty as first-class UI elements

### Interaction principles

- one active symbol in focus in the center workspace
- fast switching between symbols via event feed and pending ideas
- every role panel should be easy to scan even when collapsed
- recommendation card should read like a concise trade memo, not a blob of text
- teaching/demo mode should require almost no explanation from the operator
- key trading terms and actions should have inline explanations or tooltips

### Demo mode behavior

- allow mock events to be injected from the UI
- allow replay scenarios to be loaded
- prefer more explanatory role responses
- optionally show lightweight role badges or descriptions so learners understand the desk structure

### Terminology UX

The app should assume that some users will not know trading jargon.

Recommended behavior:
- show tooltips or inline definitions for key terms
- explain role-specific language in plain English
- keep explanations short enough not to clutter the workstation

Examples:
- `COVER`: reduces or closes a short position
- `SHORT`: sells borrowed shares to profit if the price falls
- `Conviction`: how strong the trader's recommendation is
- `Expected Move`: the market's implied near-term price range
- `Event Blackout`: a period where opening a new trade may be restricted by risk rules

## Testing and Validation Plan

The build should be tested as a workflow system, not just as isolated APIs.

### Coverage targets

The implementation should set explicit minimum coverage targets.

Recommended targets:
- backend overall line coverage: at least `85%`
- backend critical workflow modules: at least `95%`
- frontend component and interaction coverage for critical workstation flows: at least `70%`
- recommendation state-machine module: `100%` transition-path coverage for allowed and rejected transitions

Critical backend modules for the `95%` target:
- recommendation state machine
- approval and execution guards
- role orchestration and trader-query routing
- broker paper-execution adapter
- event replay and mock-event injection

Coverage targets are not a substitute for scenario tests, but they are a useful floor.

### Core test categories

- event normalization tests
- recommendation state-machine tests
- approval gate tests
- broker adapter tests
- role payload schema validation tests
- real-time update tests
- database persistence tests
- replay-mode tests

### Human workflow tests

The app should be tested against realistic flows:
- new earnings event -> recommendation -> approval -> paper execution
- conflicting role outputs -> trader follow-up -> revised recommendation
- user chats with risk role -> trader recommendation changes
- replay scenario used as teaching/demo flow

### Frontend integration tests

The frontend should have lightweight but real interaction coverage for the workstation.

Minimum required frontend integration tests:
- event selection updates the active symbol context
- group chat sends `@role` messages to the correct backend route
- recommendation panel reflects status changes from SSE updates
- approve and execute controls respect state gating
- open positions panel updates after a paper execution event
- tooltip and terminology help render for action labels like `SHORT` and `COVER`

### Strategy validation

Before any live money:
- minimum paper trade count by strategy
- review recommendation quality and outcome attribution
- verify that role outputs are informative, not just verbose
- track whether the trader role meaningfully improves over raw signal cards
- separately review long-entry, long-exit, short-entry, and short-cover recommendation quality

### Paper execution release gate

No build should be treated as ready for serious paper-trading use unless all of the following are true:
- backend test suite passes
- frontend integration tests pass
- coverage thresholds are met
- approval-gate tests confirm execution cannot bypass approval
- replay-mode scenario tests pass for at least one end-to-end recommendation workflow
- mock-event tests confirm the workstation can demonstrate the full role-discussion flow without live APIs

## Build Sequence

This is the recommended implementation order once building starts.

### Milestone 1: foundation

- scaffold frontend, backend, worker, and database
- define schemas and state machine
- migrate current PEAD candidate and trade data into new core objects where useful
- stand up paper portfolio and positions views

Done when:
- the backend starts cleanly
- the database schema is created successfully
- `POST /api/scan` can produce candidate/recommendation records
- `GET /api/portfolio` and `GET /api/positions` return paper account data
- state-machine tests pass
- backend coverage is at least `80%` with critical workflow modules at or above `90%`

### Milestone 2: workstation shell

- build 3-column UI
- event feed
- role widgets
- recommendation panel
- open trades panel
- history panel

Done when:
- the main workstation renders end to end
- selecting an event changes the active symbol context
- recommendation, open positions, and history panels are visible and populated from API data
- frontend integration tests cover the main workstation shell interactions

### Milestone 3: role workflow

- implement per-role sessions
- direct role chat
- trader synthesis
- shared summary generation
- recommendation approval flow

Done when:
- each role can be chatted with directly
- trader-led inter-role questioning works
- recommendations move correctly through discussion and approval states
- the timeline/show-discussion view is usable
- role-routing, state-machine, and approval-gate tests meet the critical-path coverage threshold

### Milestone 4: PEAD-plus intelligence

- press-release extraction
- guidance detection
- catalyst/risk extraction
- transcript support
- richer trader recommendations

Done when:
- research output includes beat quality, guidance, catalysts, and counterpoints
- trader recommendations visibly use the enriched research context
- the workflow remains cheap enough for routine paper use

### Milestone 5: demo and replay

- mock event injection
- replay scenarios
- educational prompt variants
- presentation-ready polish

Done when:
- mock scenarios can drive the full workstation
- replay mode works without real APIs
- non-expert users can follow the role discussion flow without explanation

### Milestone 6: production hardening

- secure auth for published version
- deployment pipeline
- monitoring
- model-cost tracking
- alerts and failure handling

Done when:
- the published app requires secure login
- failures surface clearly in logs and UI
- cost tracking and alerts are active
- deploy and rollback steps are documented and repeatable

### Milestone 7: broader strategy expansion

- sentiment overlay
- macro context
- event-driven workflows
- deeper research integrations

Done when:
- at least one non-PEAD strategy family is operational in the same workstation
- strategy context is visible in recommendations
- the role system remains understandable despite the broader scope

## Project Structure

The build should use a clear split between frontend, backend, and runtime data.

```text
trading/
├── frontend/
│   ├── src/app/
│   ├── src/components/
│   │   ├── layout/
│   │   ├── events/
│   │   ├── roles/
│   │   ├── trades/
│   │   └── shared/
│   ├── src/hooks/
│   ├── src/lib/
│   └── src/config/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── db/
│   │   ├── services/
│   │   ├── roles/
│   │   │   └── prompts/
│   │   ├── adapters/
│   │   │   └── llm/
│   │   └── routes/
│   └── tests/
├── data/
│   ├── aatf.db
│   └── mock_scenarios/
├── .env
├── .env.example
├── Makefile
├── trading_plan_codex.md
└── trading_plan_claude.md
```

## Concrete API Surface

These are the concrete routes to implement first.

### Events

- `GET /api/events`
- `GET /api/events/{id}`
- `GET /api/stream`
- `POST /api/scan`
- `POST /api/events/mock`
- `POST /api/events/replay`

### Roles

- `POST /api/roles/{name}/analyse`
- `POST /api/roles/{name}/chat`
- `GET /api/roles/{name}/history`
- `GET /api/roles/config`
- `PUT /api/roles/{name}/config`

### Recommendations

- `GET /api/recs`
- `GET /api/recs/{id}`
- `GET /api/recs/{id}/timeline`
- `POST /api/recs/{id}/approve`
- `POST /api/recs/{id}/execute`
- `POST /api/recs/{id}/reject`
- `POST /api/recs/{id}/discuss`

### Portfolio and trades

- `GET /api/portfolio`
- `GET /api/positions`
- `GET /api/trades`
- `GET /api/trades/{id}`

### System

- `GET /api/status`
- `GET /api/config`
- `PUT /api/config`
- `GET /api/costs`

## SSE Event Contract

Use SSE first for live updates because it is simpler than websockets for this workstation.

Core event types:
- `market_event`
- `role_message`
- `role_query`
- `summary_update`
- `recommendation_update`
- `position_update`
- `cost_alert`
- `system`

Representative payloads:

```text
event: market_event
data: {"id":"evt_123","type":"earnings","symbol":"NVDA","headline":"NVDA beats by 8%","importance":4}

event: role_query
data: {"from_role":"trader","to_role":"risk","question":"Does sector overlap matter here?","recommendation_id":"rec_456"}

event: recommendation_update
data: {"id":"rec_456","status":"draft_recommendation","symbol":"NVDA","action":"BUY","conviction":8}
```

## Database Schema Baseline

These tables should exist in the first real schema.

### Core tables

- `events`
- `role_threads`
- `role_messages`
- `shared_summaries`
- `recommendations`
- `approval_records`
- `trades`
- `executions`
- `role_configs`
- `cost_log`

### Required SQL baseline

```sql
CREATE TABLE recommendations (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    direction TEXT,
    status TEXT NOT NULL DEFAULT 'observing',
    strategy_type TEXT NOT NULL,
    thesis TEXT,
    entry_price REAL,
    entry_logic TEXT,
    stop_price REAL,
    stop_logic TEXT,
    target_price REAL,
    target_logic TEXT,
    position_size_shares REAL,
    position_size_dollars REAL,
    conviction INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE role_messages (
    id TEXT PRIMARY KEY,
    role_thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    sender TEXT NOT NULL,
    symbol TEXT,
    recommendation_id TEXT,
    message_text TEXT NOT NULL,
    structured_payload TEXT,
    stance TEXT,
    confidence REAL,
    provider TEXT,
    model_used TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
```

This baseline is required, not merely illustrative. The implementation can extend it, but should not omit these audit and reasoning fields.

## Environment and Config Baseline

The project should include an `.env.example` with at least:

```bash
APP_MODE=paper
EVENT_MODE=live
DEMO_MODE=false

ANTHROPIC_API_KEY=
OPENAI_API_KEY=

FMP_API_KEY=
POLYGON_API_KEY=
FRED_API_KEY=

ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

DATABASE_URL=sqlite:///data/aatf.db
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

## Failure Handling Requirements

These are not optional.

### LLM failures

- retry transient timeouts once
- back off on rate limits
- surface provider failure in the UI
- keep partial-role workflows usable if one role fails
- log malformed structured output and retry once

### Broker failures

- persist rejected orders as failed executions
- never silently drop approval or execution events
- preserve the recommendation state if submission fails

### Data failures

- use cached data with staleness indicators where appropriate
- skip bad symbols rather than failing whole scans
- log upstream provider failure explicitly

## Testing Baseline

These test groups should exist in the first implementation:

- `test_scanner.py`
- `test_filters.py`
- `test_state_machine.py`
- `test_position_sizing.py`
- `test_roles.py`
- `test_orchestrator.py`
- `test_routes.py`
- `test_llm_providers.py`
- `test_replay_mode.py`
- `test_mock_events.py`
- `test_execution_guards.py`
- `test_sse_stream.py`
- `frontend/src/test/workstation.integration.test.tsx`
- `frontend/src/test/group_chat.integration.test.tsx`
- `frontend/src/test/recommendation_panel.integration.test.tsx`

The minimum critical guarantees are:
- state transitions are enforced
- approval gates cannot be bypassed
- role structured outputs validate
- scanner and filters remain deterministic under fixtures
- SSE updates are reflected correctly in the workstation
- mock and replay modes remain usable for demo and teaching

## Cost Baseline

The build should include real cost tracking from the start.

Track:
- spend by role
- spend by recommendation
- daily total spend
- token counts by provider and model

Working target for normal paper-trading use:
- low tens of dollars per month, not hundreds

Representative monthly expectation for normal paper-trading use:
- total LLM spend around `$20-$40/month`
- `research` and `risk` are likely the main recurring analysis cost
- `trader` is likely the highest-cost per-call role
- `quant_pricing` should stay relatively cheap because core pricing logic should be deterministic where possible
- aggressive caching and strict pre-filtering should keep routine usage below the upper end of that range

The implementation should expose cost data in:
- `GET /api/costs`
- per-message metadata
- role configuration budgets

## Migration Rules

The current monolithic dashboard should be treated as source material, not as the target architecture.

Refactor and preserve:
- PEAD scan logic
- filter logic
- position sizing logic
- Alpaca integration behavior
- FMP integration behavior

Replace:
- single-file server architecture
- HTML-card-based UI flow
- CSV-based workflow state

The migration should happen in this order:
1. preserve core trading logic in new backend services
2. stand up the new data model and state machine
3. build the workstation UI around the new API
4. retire or archive the old dashboard only after workflow parity exists

## Risks and Tradeoffs

### Main risks

- too much model usage cost if event triage is not strict
- role chats becoming repetitive rather than useful
- overbuilding orchestration before the workstation UX is proven
- UI becoming cluttered if too many simultaneous ideas are shown
- educational/demo features making the app feel gimmicky if not handled carefully

### Mitigations

- strict pre-filtering before expensive model calls
- clear structured output contracts
- one active symbol in focus
- visible disagreement summaries instead of excessive prose
- replay mode using the same architecture rather than special-case demo code

## Resolved Decisions

These decisions are settled and should be treated as constraints for the implementation.

1. The product is paper-trading first, including the first published version.
2. The UI should look professional and desk-like rather than playful.
3. Roles should be named by their actual desk function rather than by fictional personas.
4. Role-to-role questioning is led by the `trader` role:
   - automatically on important new events
   - when the human asks the trader something that requires cross-role discussion
5. v1 supports a practical paper-trading action set:
   - `BUY | SELL | SHORT | COVER | PASS`
6. v1 includes inline explanations for trading actions and key terminology.

## Clarification on PASS

`PASS` means: do not take a trade.

In practice, the `trader` role can conclude:
- the setup is not attractive enough
- the risks outweigh the expected return
- the signal quality is too weak or conflicting
- the event matters, but not in a way that justifies action right now

So `PASS` is a real recommendation state, not a failure. It means the system reviewed the idea and decided the best action is no action.

For v1, `PASS` is useful because it lets the trader role explicitly say:
- "interesting event, but not tradeable"
- "wait for better price confirmation"
- "portfolio already has too much similar exposure"
- "research is positive, but risk objects"

That is often better than forcing every reviewed event into a buy or sell decision.

## Workstation UX and State Model

This section defines the next planning layer after the product summary: the actual screen shape, the major UI objects, and the workflow states.

### Screen layout

The main interface should be a three-column trading workstation.

Left column:
- live incoming events feed
- watchlist and active symbols
- quick filters for `earnings`, `news`, `pricing`, `macro`, and `internal`

Center column:
- one primary group chat for the active symbol or recommendation
- directed role discussion inside that group chat via `@research`, `@risk`, `@quant_pricing`, and `@trader`
- shared rolling summary panel above or between the role panels
- current symbol or recommendation context visible at all times

Right column:
- embedded `trader` avatar and voice panel
- current trader recommendation card
- approval controls
- open trades panel
- pending recommendations queue
- recent execution and decision history

The left column answers "what just happened?"
The center column answers "what do the roles think?"
The right column answers "what action is being proposed or currently live?"

The center and right columns should also support a clear "show the discussion" experience so a learner can follow how the final recommendation was formed.

### Group chat semantics

The workstation should use one shared desk conversation for the active symbol or recommendation context.

Recommended message-routing rules:
- messages prefixed with `@role` are directed 1-to-1 to that role
- a directed message should not trigger every role to reply
- messages without an explicit `@role` should route to `@trader` by default
- the `trader` role can then answer directly or query other roles as needed
- trader-to-role follow-up questions should be visible in the same shared conversation timeline

This preserves the feel of a visible desk conversation without causing every actor to respond to every message.

### Core UI objects

The UI should be built around explicit objects, not loosely formatted chat text.

Recommended core objects:
- `IncomingEvent`
- `RoleThread`
- `RoleMessage`
- `SharedSummary`
- `TradeRecommendation`
- `ApprovalRequest`
- `OpenTrade`
- `ExecutionRecord`

### Suggested object shapes

`IncomingEvent`
- `id`
- `type`
- `symbol`
- `headline`
- `body_excerpt`
- `source`
- `timestamp`
- `importance`
- `linked_recommendation_ids`

`RoleMessage`
- `id`
- `role_thread_id`
- `role`
- `sender`
- `symbol`
- `recommendation_id`
- `message_text`
- `stance`
- `confidence`
- `structured_payload`
- `provider`
- `model_used`
- `input_tokens`
- `output_tokens`
- `cost_usd`
- `timestamp`

`RoleThread`
- `id`
- `role`
- `symbol`
- `recommendation_id`
- `created_at`

`SharedSummary`
- `id`
- `recommendation_id`
- `summary_text`
- `bull_case`
- `bear_case`
- `key_disagreement`
- `last_updated`
- `generated_by_model`

`TradeRecommendation`
- `id`
- `symbol`
- `direction`
- `thesis`
- `strategy_type`
- `entry_price`
- `entry_logic`
- `target_price`
- `target_logic`
- `stop_price`
- `stop_logic`
- `position_size`
- `time_horizon`
- `supporting_roles`
- `blocking_risks`
- `status`
- `confidence`
- `created_at`
- `updated_at`

`ApprovalRequest`
- `id`
- `recommendation_id`
- `approval_status`
- `requested_at`
- `reviewer_notes`
- `approved_at`
- `rejected_at`

`OpenTrade`
- `id`
- `symbol`
- `direction`
- `entry_price`
- `current_price`
- `size`
- `unrealized_pnl`
- `linked_recommendation_id`
- `risk_state`
- `opened_at`

### Role design

Each role should have its own conversation state and structured output contract, even if the primary UI presents discussion in one shared desk chat.

Each role should also have:
- its own conversation and session state
- its own scoped memory
- its own prompt and tool access policy
- its own default model, with escalation rules if needed

The user should be able to chat directly with each role by using `@role` in the group chat.
The `trader` role should also be able to question the other roles before issuing or updating a recommendation.

### Trader avatar and voice architecture

The `trader` role should be the only voice/avatar role in v1.

Recommended architecture:
- `research`, `risk`, and `quant_pricing` use direct backend LLM calls and remain text-first
- `trader` is represented in the UI by an embedded Agora avatar panel
- the trader avatar should live inside the main workstation, not in a separate standalone app
- the main backend remains the system of record for events, role messages, summaries, recommendations, approvals, trades, and costs
- the same backend should also expose an Agora-compatible custom-LLM endpoint for trader voice turns

Recommended interaction modes:
- typed desk workflow: the backend generates trader messages and can call Agora `/speak` so the trader avatar speaks visible trader outputs
- spoken trader workflow: the user speaks to the trader through Agora ConvoAI, and the trader voice turn is resolved by the same backend orchestration used for typed discussion

Architectural rule:
- Agora is the conversation and avatar layer for the `trader`, not the system of record for the trading app
- typed and spoken trader interactions should converge on the same recommendation state, group chat timeline, and approval workflow

`research` structured output:
- thesis summary
- beat quality
- guidance change
- earnings or news interpretation
- catalyst list
- counterpoints
- confidence

`risk` structured output:
- top risks
- portfolio overlap
- position size recommendation
- max portfolio risk
- event blackout issues
- liquidity and gap concerns
- reasons to reject or reduce size

`quant_pricing` structured output:
- fair value estimate
- signal strength
- expected move context
- entry zone
- stop level
- target zone
- volatility notes
- tactical execution notes

`trader` structured output:
- final recommendation
- conviction
- size proposal
- must-have conditions
- conditions that invalidate the trade
- dissent notes
- questions for the user
- approval request state

Recommended v1 action set:
- `BUY`
- `SELL`
- `SHORT`
- `COVER`
- `PASS`

Meaning:
- `BUY`: open or add to a long position
- `SELL`: reduce or close an existing long position
- `SHORT`: open or add to a short position
- `COVER`: reduce or close an existing short position
- `PASS`: take no action

Recommended interaction behavior:
- `research`, `risk`, and `quant_pricing` can each respond to the human in their own widget
- the human can inspect and challenge each role independently
- the `trader` can reference, quote, or interrogate the other roles' structured outputs and latest reasoning
- the human can then chat with the `trader` about the combined influences before approving or rejecting the trade

Recommended first model policy:
- `research`: cheaper model first, escalate for long transcripts and complex narrative analysis
- `risk`: cheaper or mid-tier model first, escalate for cross-position and regime-sensitive decisions
- `quant_pricing`: prefer deterministic calculations plus lighter model explanation
- `trader`: strongest available reasoning model

### State machine

Recommendations should move through a strict lifecycle.

Suggested states:
- `observing`
- `under_discussion`
- `draft_recommendation`
- `awaiting_user_feedback`
- `awaiting_user_approval`
- `approved`
- `rejected`
- `submitted`
- `partially_filled`
- `filled`
- `closed`
- `cancelled`
- `failed`

This state machine is the backbone for:
- UI visibility
- role behavior
- audit trail
- execution safety

### Event flow

The recommended interaction flow is:

1. A new market or company event arrives.
2. The event is attached to a symbol or existing recommendation context.
3. `research`, `risk`, and `quant_pricing` produce role messages and structured outputs.
4. The `trader` can query or challenge the other roles if their outputs conflict or need clarification.
5. The shared summary updates.
6. The `trader` role proposes a recommendation or updates an existing one.
7. The user can discuss the recommendation with the `trader` role and also inspect the other roles directly.
8. The recommendation enters `awaiting_user_approval`.
9. Only after explicit approval can the order be submitted.
10. Execution updates flow back into open trades and recommendation history.

The recommendation system should support both:
- entry decisions for new opportunities
- management decisions for existing positions

Approval and execution should remain distinct auditable steps:
- `approve` means the human authorizes the recommendation
- `execute` means the system actually submits the broker order

### First-version UX constraints

To keep the first workstation version focused:
- one primary symbol context in focus at a time; selecting an event or recommendation should switch the center workspace to that symbol
- no autonomous execution
- no hidden role actions that materially change trade state without showing the user
- all recommendation changes should be visible in history
- every execution should link back to a recommendation and approval record
- secure login can wait until the published version, but auth should be part of the architecture plan
- visual clarity matters; the interface should feel like a trading workstation, not an internal admin panel
- role interactions should be visible enough that the app can function as a compelling demo and teaching tool

### Why this matters

Without an explicit screen/state model, the app will likely collapse back into candidate cards with scattered AI comments. This section is intended to prevent that by making the workstation interaction model concrete before implementation starts.

## Design Principles

1. Human in the loop. AI recommends, you decide.
2. Paper first. Every strategy should prove itself in paper trading before live capital is considered.
3. Single-user first. Optimize the product for one operator now, but keep the published version secure behind login.
4. Separate role identities. Each role has its own context, memory, and possibly its own model.
5. Transparent AI. Role reasoning and dissent should be visible, not hidden behind one final answer.
6. Strategy-agnostic workflow. The workstation should support many strategy types without changing the core interaction model.
7. Cost-aware intelligence. Use smaller models for triage and heavier models only where better reasoning materially matters.
8. Good-looking and understandable UI. The interface should be visually strong, dense with useful information, and easy to follow.
9. Educational clarity. The system should make each role's perspective understandable enough to teach how a professional investment process works.
10. Measurable AI operations. Track model usage, token counts, and cost per role and recommendation so the system stays cheap and debuggable.
11. Durable state and auditability. Recommendations, approvals, and executions are records, not temporary UI state.
12. Local-to-cloud portability. Local development and published production should share the same core application model.

## Sources

Official or primary sources reviewed for this plan:

- Current handoff: `/Users/benwekes/work/trading/CLAUDE_CODE_HANDOFF.md`
- Claude plan reviewed: `/Users/benwekes/work/trading/trading_plan_claude.md`
- LangGraph: https://github.com/langchain-ai/langgraph
- OpenBB docs: https://docs.openbb.co/
- OpenBB data models: https://docs.openbb.co/platform/data_models
- OpenBB orchestrator mode: https://docs.openbb.co/workspace/analysts/ai-features/orchestrator-mode
- Qlib: https://github.com/microsoft/qlib
- EdgarTools: https://github.com/dgunning/edgartools
- LEAN repo: https://github.com/QuantConnect/Lean
- LEAN docs: https://www.quantconnect.com/docs/v2/lean-engine
- NautilusTrader: https://nautilustrader.io/open-source/
- FinGPT: https://github.com/AI4Finance-Foundation/FinGPT
- OpenAI model docs: https://platform.openai.com/docs/models
- OpenAI latest-model guide: https://platform.openai.com/docs/guides/latest-model
- Anthropic model docs: https://docs.anthropic.com/en/docs/about-claude/models/all-models
- Anthropic MCP docs: https://docs.anthropic.com/en/docs/mcp
- Qwen docs: https://huggingface.co/docs/transformers/en/model_doc/qwen3
