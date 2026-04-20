# 03 Code Map

> Directory map, key modules, and the fastest paths to the important code.

## Top-level map

```text
backend/                 FastAPI app, orchestration, DB, tests
frontend/                Next.js workstation UI
agora-agent-samples/     Local Agora sample/reference stack (do not modify)
data/                    SQLite DB and local data (gitignored)
docs/ai/                 AI-facing progressive disclosure docs
```

## Backend key files

- `backend/app/main.py`: app assembly, router registration, CORS, lifespan
- `backend/app/config.py`: settings/env parsing (pydantic-settings)
- `backend/app/database.py`: SQLite schema (all CREATE TABLE statements)
- `backend/app/db/repositories.py`: DB CRUD layer
- `backend/app/roles/orchestrator.py`: core role workflow — parallel analysis, trader synthesis, inter-role querying, direction/conviction extraction
- `backend/app/roles/base.py`: BaseRole class — provider selection, session management
- `backend/app/roles/prompts/`: system prompts per role (versioned .md files)
- `backend/app/routes/recommendations.py`: recommendation lifecycle — approve, reject, ready, execute (with SELL/COVER position management)
- `backend/app/routes/scanner.py`: scan and random-event entry points (background analysis)
- `backend/app/routes/trades.py`: sell/close endpoint with long/short P&L
- `backend/app/routes/strategy_settings.py`: settings CRUD with operator spec defaults
- `backend/app/routes/agora.py`: trader avatar + Agora-compatible proxy routes
- `backend/app/services/state_machine.py`: allowed state transitions
- `backend/app/services/position_sizing.py`: conviction-based position sizing
- `backend/app/services/agora_bridge.py`: two-phase Agora agent start
- `backend/app/adapters/alpaca.py`: Alpaca paper/live trading (bracket orders, close positions)
- `backend/app/adapters/llm/openai_provider.py`: GPT-5.x Responses API + GPT-4.x Chat API, JSON stripping
- `backend/app/adapters/llm/mock.py`: mock LLM for tests

## Frontend key files

- `frontend/src/app/page.tsx`: main workstation — 3 columns, SSE, all handlers
- `frontend/src/components/layout/Header.tsx`: header with settings button (no scan button — auto-scan on load)
- `frontend/src/components/layout/InboxTabs.tsx`: left column — 3 tabs: Earnings / AI / News
- `frontend/src/components/roles/GroupChat.tsx`: desk chat — @mentions, keyboard nav, role filters
- `frontend/src/components/trades/TradePanel.tsx`: centre top — summary + buy controls + price levels
- `frontend/src/components/trades/AvatarAndPositions.tsx`: right column — Agora RTC avatar + portfolio with sell/cover
- `frontend/src/components/shared/SettingsPanel.tsx`: strategy settings modal
- `frontend/src/components/shared/Toast.tsx`: toast notification system
- `frontend/src/hooks/useAgoraAvatar.ts`: Agora RTC join/leave/mute
- `frontend/src/hooks/useSSE.ts`: SSE subscription hook
- `frontend/src/lib/api.ts`: API client
- `frontend/src/lib/types.ts`: TypeScript types

## Tests

- `backend/tests/test_state_machine.py`: state transition validation
- `backend/tests/test_position_sizing.py`: position calculation
- `backend/tests/test_conviction_sizing.py`: conviction multiplier + scaled sizing
- `backend/tests/test_settings.py`: strategy settings CRUD + defaults
- `backend/tests/test_sell_endpoint.py`: trade creation, close, long/short P&L
- `backend/tests/test_orchestrator.py`: role analysis flow, group chat routing
- `backend/tests/test_routes.py`: API endpoints, approval flow, settings

## Related Deep Dives

- [api_contracts](deep_dives/api_contracts.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
- [role_and_state_machine](deep_dives/role_and_state_machine.md)
