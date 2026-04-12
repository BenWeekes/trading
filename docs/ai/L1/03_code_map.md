# 03 Code Map

> Directory map, key modules, and the fastest paths to the important code.

## Top-level map

```text
backend/                 FastAPI app, orchestration, DB, tests
frontend/                Next.js workstation UI
agora-agent-samples/     Local Agora sample/reference stack
data/                    SQLite DB and local data
docs/ai/                 AI-facing progressive disclosure docs
```

## Backend key files

- [backend/app/main.py](/Users/benwekes/work/trading/backend/app/main.py): app assembly and router registration
- [backend/app/config.py](/Users/benwekes/work/trading/backend/app/config.py): settings/env parsing
- [backend/app/database.py](/Users/benwekes/work/trading/backend/app/database.py): SQLite schema
- [backend/app/db/repositories.py](/Users/benwekes/work/trading/backend/app/db/repositories.py): DB CRUD layer
- [backend/app/roles/orchestrator.py](/Users/benwekes/work/trading/backend/app/roles/orchestrator.py): core workflow logic
- [backend/app/routes/recommendations.py](/Users/benwekes/work/trading/backend/app/routes/recommendations.py): recommendation lifecycle routes
- [backend/app/routes/scanner.py](/Users/benwekes/work/trading/backend/app/routes/scanner.py): scan and random-event entry points
- [backend/app/routes/agora.py](/Users/benwekes/work/trading/backend/app/routes/agora.py): trader avatar + Agora-compatible proxy routes
- [backend/app/services/state_machine.py](/Users/benwekes/work/trading/backend/app/services/state_machine.py): allowed state transitions
- [backend/app/services/agora_bridge.py](/Users/benwekes/work/trading/backend/app/services/agora_bridge.py): bridge to local Agora sample backend

## Frontend key files

- [frontend/src/app/page.tsx](/Users/benwekes/work/trading/frontend/src/app/page.tsx): main workstation screen
- [frontend/src/lib/api.ts](/Users/benwekes/work/trading/frontend/src/lib/api.ts): API client
- [frontend/src/lib/types.ts](/Users/benwekes/work/trading/frontend/src/lib/types.ts): UI-facing types
- [frontend/src/components/roles/GroupChat.tsx](/Users/benwekes/work/trading/frontend/src/components/roles/GroupChat.tsx): desk conversation UI
- [frontend/src/components/roles/SharedSummary.tsx](/Users/benwekes/work/trading/frontend/src/components/roles/SharedSummary.tsx): summary panel
- [frontend/src/components/trades/RecommendationCard.tsx](/Users/benwekes/work/trading/frontend/src/components/trades/RecommendationCard.tsx): recommendation + action buttons
- [frontend/src/components/trades/TraderAvatarPanel.tsx](/Users/benwekes/work/trading/frontend/src/components/trades/TraderAvatarPanel.tsx): embedded trader avatar panel
- [frontend/src/components/trades/OpenPositions.tsx](/Users/benwekes/work/trading/frontend/src/components/trades/OpenPositions.tsx): open positions panel
- [frontend/src/hooks/useSSE.ts](/Users/benwekes/work/trading/frontend/src/hooks/useSSE.ts): SSE subscription hook

## Tests

- [backend/tests/test_orchestrator.py](/Users/benwekes/work/trading/backend/tests/test_orchestrator.py)
- [backend/tests/test_routes.py](/Users/benwekes/work/trading/backend/tests/test_routes.py)
- [backend/tests/test_state_machine.py](/Users/benwekes/work/trading/backend/tests/test_state_machine.py)
- [backend/tests/test_position_sizing.py](/Users/benwekes/work/trading/backend/tests/test_position_sizing.py)

## Related Deep Dives

- [api_contracts](deep_dives/api_contracts.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
