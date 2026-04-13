# 06 Interfaces

> API contracts, SSE event types, key object shapes, and boundaries between subsystems.

## Main routes

Events and scans:
- `GET /api/events`
- `POST /api/scan` — triggers background analysis, returns immediately
- `POST /api/events/mock`
- `POST /api/events/replay`

Recommendations:
- `GET /api/recs`
- `GET /api/recs/{id}` — includes summary + timeline
- `GET /api/recs/{id}/timeline`
- `POST /api/recs/{id}/discuss` — group chat with @role routing
- `POST /api/recs/{id}/ready` — move from feedback to approval state
- `POST /api/recs/{id}/approve` — accepts `{ shares }`, rejects from feedback state
- `POST /api/recs/{id}/execute` — BUY/SHORT open new positions, SELL/COVER close existing
- `POST /api/recs/{id}/reject`
- `POST /api/recs/{id}/refresh`

Portfolio and trades:
- `GET /api/positions`
- `GET /api/portfolio` — tries Alpaca first, falls back to local calc
- `GET /api/trades`
- `POST /api/trades/{id}/sell` — full or partial close with direction-aware P&L

Strategy settings:
- `GET /api/settings` — all settings merged with operator spec defaults
- `PATCH /api/settings` — update one or more settings

Trader avatar / Agora:
- `GET /api/trader/avatar/status`
- `POST /api/trader/avatar/start` — two-phase: tokens then agent
- `POST /api/trader/avatar/speak`
- `POST /api/trader/avatar/stop`
- `POST /api/agora/chat/completions` — Agora-compatible proxy

System:
- `GET /api/status`
- `GET /api/config`
- `GET /api/costs`

## SSE event types

- `market_event` — new event from scan or demo
- `role_message` — role analysis or chat response
- `role_query` — trader querying another role
- `summary_update` — shared summary changed
- `recommendation_update` — status or direction changed
- `position_update` — trade opened/closed
- `cost_alert` — cost budget threshold
- `system` — scan status, analysis errors

## Key object shapes

`Recommendation`
- `id`, `symbol`, `direction`, `status`, `strategy_type`
- `thesis`, `conviction`
- `entry_price`, `entry_logic`, `stop_price`, `stop_logic`, `target_price`, `target_logic`
- `position_size_shares`, `position_size_dollars`

`RoleMessage`
- `id`, `role`, `sender`, `symbol`, `recommendation_id`
- `message_text`, `structured_payload`
- `provider`, `model_used`, `input_tokens`, `output_tokens`, `cost_usd`

`Position / Trade`
- `id`, `symbol`, `direction`, `entry_price`, `current_price`, `shares`
- `unrealized_pnl`, `stop_price`, `target_price`, `risk_state`
- `broker_order_id`

`TraderAvatarSession`
- `channel`, `agent_id`, `appid`, `token`, `uid`, `agent_uid`

## Interface rules

- `execute` rejects recommendations not in `approved` state
- `approve` rejects recommendations in `awaiting_user_feedback` — must call `ready` first
- `reject` works from both `awaiting_user_feedback` and `awaiting_user_approval`
- SELL/COVER execute closes existing positions, BUY/SHORT opens new ones
- Sell endpoint calculates P&L based on direction (longs: exit-entry, shorts: entry-exit)
- Conviction below `min_conviction_to_trade` setting produces zero shares
- Settings persist to `strategy_settings` SQLite table, merged with defaults

## Related Deep Dives

- [api_contracts](deep_dives/api_contracts.md)
- [role_and_state_machine](deep_dives/role_and_state_machine.md)
