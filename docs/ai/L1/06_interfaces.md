# 06 Interfaces

> API contracts, SSE event types, key object shapes, and boundaries between subsystems.

## Main routes

Events and scans:
- `GET /api/events`
- `POST /api/scan`
- `POST /api/demo/random-event`

Recommendations:
- `GET /api/recs`
- `GET /api/recs/{id}`
- `POST /api/recs/{id}/discuss`
- `POST /api/recs/{id}/ready`
- `POST /api/recs/{id}/approve`
- `POST /api/recs/{id}/execute`
- `POST /api/recs/{id}/reject`

Portfolio:
- `GET /api/positions`
- `GET /api/portfolio`

Trader avatar / Agora:
- `GET /api/trader/avatar/status`
- `POST /api/trader/avatar/start`
- `POST /api/trader/avatar/speak`
- `POST /api/trader/avatar/stop`
- `POST /api/agora/chat/completions`

## SSE event types

- `market_event`
- `role_message`
- `role_query`
- `summary_update`
- `recommendation_update`
- `position_update`
- `cost_alert`
- `system`

## Important object shapes

`Recommendation`
- `id`
- `symbol`
- `direction`
- `status`
- `thesis`
- `entry_price`
- `entry_logic`
- `stop_price`
- `stop_logic`
- `target_price`
- `target_logic`
- `conviction`

`RoleMessage`
- `id`
- `role`
- `sender`
- `message_text`
- `structured_payload`
- `provider`
- `model_used`
- `input_tokens`
- `output_tokens`
- `cost_usd`
- `timestamp`

`TraderAvatarStatus`
- `enabled`
- `backend_url`
- `client_url`
- `profile`
- optional `session`

## Interface rules

- `execute` must reject recommendations that are not already `approved`.
- Agora proxy endpoint should resolve to an existing recommendation context, not silently create durable recs.
- Group chat routing semantics belong in orchestration, not in the frontend alone.

## Related Deep Dives

- [api_contracts](deep_dives/api_contracts.md)
- [role_and_state_machine](deep_dives/role_and_state_machine.md)
