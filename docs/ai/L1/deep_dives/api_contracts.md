# API Contracts

## When to Read This

Read this when changing backend route schemas, frontend API consumption, SSE payloads, or trader-avatar proxy behavior.

## Main contract families

- event/scan
- recommendation lifecycle
- role chat
- portfolio/trades
- SSE stream
- trader avatar / Agora proxy

## Sensitive contracts

### Recommendation lifecycle

- `POST /api/recs/{id}/ready`
- `POST /api/recs/{id}/approve`
- `POST /api/recs/{id}/execute`

These must stay behaviorally distinct.

### Agora-compatible proxy

`POST /api/agora/chat/completions` is an adapter for trader voice turns. It should behave like a compatibility surface, not a separate business-logic engine.

## Data-object rule

Recommendation objects should include:
- levels: `entry_price`, `stop_price`, `target_price`
- reasoning: `entry_logic`, `stop_logic`, `target_logic`

## SSE rule

SSE payloads should be useful enough for targeted UI updates. Broad refetches should be a fallback, not the only strategy.
