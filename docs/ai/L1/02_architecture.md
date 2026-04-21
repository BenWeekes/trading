# 02 Architecture

> System design at a glance: components, data flow, responsibilities, and boundaries.

## System shape

```text
Next.js workstation (port 3000)
  -> FastAPI backend (port 8000)
      -> SQLite (data/aatf.db)
      -> LLM providers (OpenAI GPT-5.1 / mock)
      -> Alpaca (paper trading)
      -> FMP (earnings, quotes, news)
      -> optional Agora trader avatar (port 8082)
```

## Main product rule

The backend is the system of record. The frontend is a view layer.

## Core components

Frontend:
- inbox tabs (earnings / AI recommendations / news — 3 tabs)
- news reader (centre column, opens on news item click, replaces trade panel while active)
- trade panel (summary + buy controls + prices)
- desk chat (group chat with @role routing and filters)
- avatar panel (Agora RTC video/audio)
- portfolio (positions with sell/cover controls)
- settings panel (strategy configuration modal)
- toast notifications

Backend:
- routes (events, recommendations, trades, settings, avatar, subjects)
- role orchestration (parallel analysis, trader synthesis, inter-role queries, subject chat)
- role classes (research, risk, quant_pricing, trader) with own sessions
- LLM provider abstraction (OpenAI Responses API / Chat API / mock)
- state machine (12 recommendation states)
- position sizing (conviction-based scaling)
- Alpaca adapter (bracket orders, position close)
- event bus (SSE broadcasting)
- strategy settings (persisted defaults from operator spec)
- discussion subjects (generic discussion thread for any event, recommendation, or position)

## Main flow

1. Scan finds earnings events, creates recommendations.
2. Analysis runs in background — 3 roles analyse in parallel.
3. Trader queries roles, extracts direction + conviction from response.
4. Position size calculated based on conviction (7=75%, 8-9=100%, 10=125%).
5. Recommendation moves to `awaiting_user_feedback`.
6. Human discusses with roles, clicks Ready for Approval.
7. Recommendation moves to `awaiting_user_approval`.
8. Human approves with editable share count, or rejects.
9. Execute submits to Alpaca (or paper fallback).
10. SELL/COVER finds and closes existing positions.

## Important architectural decisions

- Group chat is shared, `@role` routing is directed 1-to-1
- Approval and execution are separate auditable steps
- PASS recommendations filtered from UI, shown as badge on events
- Background analysis via asyncio.create_task — scan returns immediately
- LLM responses parsed for JSON even when truncated (regex fallback)
- Conviction below threshold produces zero shares (won't trade)
- Settings panel backed by operator spec defaults
- `discussion_subject` is the single source of truth for all chat — typed and voice messages both persist against it
- Recommendations are execution objects; discussion subjects are conversation objects — they are linked but separate
- Frontend tracks `activeSubject` (not `activeRec`) as primary state; centre panel renders based on `subject_type`
- Voice replies are persisted to DB before SSE fires — SSE is real-time delivery only, not history

## Agora integration

- Backend starts agent via two-phase flow (tokens then connect)
- Frontend joins RTC channel directly with agora-rtc-sdk-ng
- Avatar video plays into container div via track.play()
- Mute/unmute toggles local audio track
- Chat/completions proxy routes through orchestrator

## Related Deep Dives

- [role_and_state_machine](deep_dives/role_and_state_machine.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
