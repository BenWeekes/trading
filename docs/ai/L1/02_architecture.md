# 02 Architecture

> System design at a glance: components, data flow, responsibilities, and boundaries.

## System shape

```text
Next.js workstation
  -> FastAPI backend
      -> SQLite/local data layer
      -> role orchestration
      -> provider adapters
      -> paper execution flow
      -> SSE updates
      -> optional Agora trader bridge
```

## Main product rule

The backend is the system of record.

Agora is optional and only used for the `trader` avatar/voice layer. Supporting roles remain text-first.

## Core components

Frontend:
- event feed
- desk chat
- shared summary
- recommendation card
- open positions
- trader avatar panel

Backend:
- routes
- orchestration
- role classes
- provider adapters
- state machine
- repositories/database
- event bus

## Main flow

1. Event enters system.
2. Recommendation context exists or is selected.
3. `research`, `risk`, and `quant_pricing` analyse in parallel.
4. `trader` queries roles when needed.
5. Recommendation moves to `awaiting_user_feedback`.
6. Human or trader marks it ready.
7. Recommendation moves to `awaiting_user_approval`.
8. Human approves or rejects.
9. Only approved recommendations can be executed.

## Important architectural decisions

- Group chat is shared, but `@role` routing is directed 1-to-1.
- User messages are stored in the same timeline as role messages.
- Approval and execution are separate routes and separate auditable events.
- Recommendation objects carry both numeric levels and reasoning fields.
- Voice turns should converge on the same recommendation/timeline state as typed turns.

## Agora integration boundary

The main backend exposes:
- avatar start/stop/speak routes
- an Agora-compatible `/chat/completions` proxy endpoint

The current UI embeds the trader avatar via the configured Agora client URL.

## Related Deep Dives

- [role_and_state_machine](deep_dives/role_and_state_machine.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
