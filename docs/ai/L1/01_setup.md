# 01 Setup

> Environment setup, quick commands, env vars, and local run instructions.

## Prerequisites

- Python `>= 3.9`
- Node.js `>= 18`
- npm
- optional: local Agora sample stack if using trader avatar voice

## Core local setup

```bash
cp .env.example .env
cd backend && python3 -m venv ../.venv && ../.venv/bin/pip install './[dev]'
cd frontend && npm install
```

If npm TLS fails locally:

```bash
cd frontend && npm install --strict-ssl=false
```

## Run commands

Backend:

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Main app URL:

```text
http://localhost:3000
```

## Test commands

Backend:

```bash
cd backend
../.venv/bin/python -m pytest
```

Frontend build:

```bash
cd frontend
npm run build
```

## Important env vars

Root `.env` drives the main trading app.

Core:
- `APP_MODE`
- `EVENT_MODE`
- `DEMO_MODE`
- `DATABASE_URL`
- `BACKEND_PORT`
- `FRONTEND_PORT`

Providers:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `FMP_API_KEY`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `ALPACA_BASE_URL`

Optional trader avatar:
- `AGORA_ENABLED`
- `AGORA_BACKEND_URL`
- `AGORA_AVATAR_CLIENT_URL`
- `AGORA_PROFILE`

## Optional Agora setup

The repo includes `agora-agent-samples/` as a local reference/integration workspace.

For the trader avatar path you need:
- Agora backend sample running
- Agora avatar client sample running
- valid Agora + avatar vendor credentials in the sample env

## Common local expectations

- `EVENT_MODE=mock` is the easiest starting mode.
- `Random Event` is the fastest way to exercise the full workstation.
- backend tests and frontend build should both pass before calling a change stable.

## Related Deep Dives

- [runtime_modes](deep_dives/runtime_modes.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
