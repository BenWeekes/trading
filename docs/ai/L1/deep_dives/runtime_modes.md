# Runtime Modes

## When to Read This

Read this when changing local vs cloud assumptions, mock vs live data behavior, or paper vs future live execution behavior.

## Modes in practice

- `EVENT_MODE=mock`: easiest local development mode
- `DEMO_MODE=true`: UI-friendly local demo mode
- `APP_MODE=paper`: required trading mode today

## Current truth

The product is still paper-first. Live trading is not the default path.

## Local expectations

- SQLite is fine
- mock/random events should drive the workstation
- Agora is optional

## Future cloud expectations

- persistent relational DB
- secure auth
- durable audit history
- same business logic, different infrastructure shape
