# 04 Conventions

> Repo-specific rules that should stay stable across changes.

## Product conventions

- The UI is a workstation, not a stock-card dashboard.
- One active symbol or recommendation context is primary at a time.
- `@role` in desk chat means directed 1-to-1 routing.
- Plain desk-chat messages default to `trader`.

## Role conventions

- `research`, `risk`, `quant_pricing` are text-first.
- `trader` is the synthesis role and optional voice/avatar role.
- Each role keeps its own thread/state in the backend even if the UI shows one shared chat.

## Recommendation conventions

- Recommendations must contain both:
  - price fields: `entry_price`, `stop_price`, `target_price`
  - reasoning fields: `entry_logic`, `stop_logic`, `target_logic`
- `PASS` is a valid recommendation outcome.

## State-machine conventions

- Approval and execution are separate.
- New syntheses should land in `awaiting_user_feedback`.
- Only after explicit ready/approval movement should they reach `awaiting_user_approval`.
- `execute` must fail unless the recommendation is already `approved`.

## Implementation conventions

- Backend remains the system of record.
- Avoid hidden side effects in resolver/helper functions.
- Do not auto-create durable recommendation records from vague voice input unless explicitly intended.
- Prefer targeted state updates or debounced reloads over refetching everything on every SSE event.

## Editing conventions

- Keep ASCII by default.
- Use small patches.
- Preserve unrelated user changes.
- Add comments only when they clarify non-obvious logic.

## Related Deep Dives

- [role_and_state_machine](deep_dives/role_and_state_machine.md)
