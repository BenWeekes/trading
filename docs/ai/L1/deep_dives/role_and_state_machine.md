# Role and State Machine

## When to Read This

Read this when changing orchestration, role message routing, recommendation states, approval flow, or execute behavior.

## Roles

- `research`
- `risk`
- `quant_pricing`
- `trader`

Each role has its own backend thread/state. The UI may show one shared conversation, but the backend still tracks per-role history.

## Group chat routing

- `@role message` routes directly to that role
- plain messages default to `trader`
- trader can issue visible follow-up questions to other roles
- user-directed messages should appear in the same timeline

## Recommendation lifecycle

Typical path:

```text
observing
-> under_discussion
-> draft_recommendation
-> awaiting_user_feedback
-> awaiting_user_approval
-> approved
-> submitted
-> filled
```

## Critical rules

- `awaiting_user_feedback` is the discussion phase
- `awaiting_user_approval` is the explicit approval phase
- `execute` is invalid unless status is already `approved`

## Implementation anchor files

- [backend/app/services/state_machine.py](/Users/benwekes/work/trading/backend/app/services/state_machine.py)
- [backend/app/roles/orchestrator.py](/Users/benwekes/work/trading/backend/app/roles/orchestrator.py)
- [backend/app/routes/recommendations.py](/Users/benwekes/work/trading/backend/app/routes/recommendations.py)
