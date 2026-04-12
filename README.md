# Weekes AATF

AI-assisted trading workstation for paper trading, role-based market discussion, and trader-led recommendations.

The current build is a local-first React + FastAPI app with:
- a live-style event feed
- a shared desk chat with `@research`, `@risk`, `@quant_pricing`, and `@trader`
- trader-led role questioning
- explicit recommendation states
- separate approval and execution
- paper-trade views
- an optional embedded trader avatar panel backed by Agora

This is not a generic chatbot. The product shape is a trader workstation:
- left: market and internal events
- center: role discussion and summary
- right: trader recommendation, avatar, approvals, and open trades

## Human Overview

The app models four desk roles:
- `research`: narrative, catalysts, thesis quality
- `risk`: position sizing, overlap, event risk, veto conditions
- `quant_pricing`: levels, entry zones, target/stop structure
- `trader`: synthesizes the others and discusses the trade with you

The intended flow is:
1. A new event arrives or is generated locally.
2. `research`, `risk`, and `quant_pricing` analyse it.
3. The `trader` questions the other roles when needed.
4. A recommendation is created.
5. You discuss it with the trader.
6. The recommendation moves to approval.
7. You approve or reject.
8. Only approved recommendations can be executed in paper mode.

The chat model is:
- `@role some question` is a directed 1-to-1 message
- plain messages default to `@trader`
- the desk timeline shows user messages, trader-to-role questions, and role replies

## Current Architecture

### Frontend

- `frontend/`: Next.js workstation UI
- `frontend/src/app/page.tsx`: main 3-column desk screen
- `frontend/src/components/events/`: event feed
- `frontend/src/components/roles/`: desk chat and summary
- `frontend/src/components/trades/`: recommendation card, positions, trader avatar panel

### Backend

- `backend/`: FastAPI backend
- SQLite persistence for local development
- SSE updates for desk state changes
- role orchestration layer
- direct LLM provider adapter support
- paper execution flow with approval gating

### Optional Agora Integration

The main backend also exposes trader-avatar support:
- avatar session start / stop / speak routes
- an Agora-compatible `/chat/completions`-style proxy for trader voice turns

Important architectural rule:
- only the `trader` is voice/avatar-first
- supporting roles remain text-first
- the trading backend remains the system of record

## Repository Layout

```text
trading/
├── backend/                    # FastAPI backend
├── frontend/                   # Next.js workstation UI
├── data/                       # SQLite DB and local data
├── agora-agent-samples/        # Local Agora sample/reference repo
├── trading_plan_codex.md       # Main product/build plan
├── trading_plan_claude.md      # Secondary planning reference
├── .env.example                # Local env template
├── Makefile                    # Basic local commands
└── README.md                   # This file
```

## Requirements

### Core app

- Python `>= 3.9`
- Node.js `>= 18`
- npm

### Optional avatar path

If you want the trader avatar working locally as well:
- Agora backend sample under `agora-agent-samples/simple-backend`
- Agora avatar client sample under `agora-agent-samples/react-video-client-avatar`
- valid Agora + avatar vendor credentials

## Environment

Copy the root env template:

```bash
cp .env.example .env
```

Minimum useful local settings:

```dotenv
APP_MODE=paper
EVENT_MODE=mock
DEMO_MODE=true

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.2

FMP_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

DATABASE_URL=sqlite:///data/aatf.db
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

Optional Agora-related root env vars used by the trading app:

```dotenv
AGORA_ENABLED=true
AGORA_BACKEND_URL=http://localhost:8082
AGORA_AVATAR_CLIENT_URL=http://localhost:8084
AGORA_PROFILE=VIDEO
```

## Build and Run

### 1. Install backend dependencies

```bash
cd backend
python3 -m venv ../.venv
../.venv/bin/pip install './[dev]'
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
```

If your machine has local TLS issues with npm, you may need:

```bash
npm install --strict-ssl=false
```

### 3. Start the backend

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm run dev
```

### 5. Open the app

```text
http://localhost:3000
```

## Local Usage

### Fastest demo flow

1. Open the workstation.
2. Click `Random Event`.
3. Watch the desk discussion populate.
4. Use the desk chat:
   - `@risk what worries you here?`
   - `@research what is the core catalyst?`
   - `what do you think?` -> goes to trader
5. If the recommendation is in `awaiting_user_feedback`, either:
   - discuss with the trader, or
   - click `Ready for Approval`
6. Click `Approve`
7. Click `Execute`

### Desk chat semantics

- `@research ...` routes only to research
- `@risk ...` routes only to risk
- `@quant_pricing ...` routes only to quant pricing
- `@trader ...` routes only to trader
- no prefix means trader by default

### Recommendation states you will see

- `observing`
- `under_discussion`
- `draft_recommendation`
- `awaiting_user_feedback`
- `awaiting_user_approval`
- `approved`
- `submitted`
- `filled`

### Trade action meanings

- `BUY`: open or add to a long
- `SELL`: reduce or close a long
- `SHORT`: open or add to a short
- `COVER`: reduce or close a short
- `PASS`: no trade

## Testing

### Backend tests

```bash
cd backend
../.venv/bin/python -m pytest
```

Current verified status during this round of work:
- backend tests passed locally

### Frontend production build

```bash
cd frontend
npm run build
```

Current verified status during this round of work:
- frontend production build passed locally

## What Is Implemented

### Working now

- mock/demo event generation
- event -> role analysis -> trader recommendation flow
- separate approval and execution routes
- desk chat with directed `@role` routing
- recommendation timeline and summary
- paper positions view
- optional trader avatar panel in the workstation
- optional Agora-compatible trader proxy endpoint in the main backend

### Not fully complete yet

- full frontend integration-test suite
- full live market-data hardening
- robust cost accounting
- production auth
- fully native in-app Agora SDK embed instead of relying on the sample client URL for the avatar panel

## API Shape

Main backend routes in active use:

- `POST /api/scan`
- `POST /api/demo/random-event`
- `GET /api/events`
- `GET /api/recs`
- `GET /api/recs/{id}`
- `POST /api/recs/{id}/discuss`
- `POST /api/recs/{id}/ready`
- `POST /api/recs/{id}/approve`
- `POST /api/recs/{id}/execute`
- `POST /api/recs/{id}/reject`
- `GET /api/positions`
- `GET /api/portfolio`
- `GET /api/stream`

Trader avatar / Agora routes:

- `GET /api/trader/avatar/status`
- `POST /api/trader/avatar/start`
- `POST /api/trader/avatar/speak`
- `POST /api/trader/avatar/stop`
- `POST /api/agora/chat/completions`

## Trader Avatar Notes

The trader avatar is currently treated as an optional integrated capability.

That means:
- the trading app can run without Agora
- the desk workflow is still usable without voice
- if Agora is configured and running, the trader avatar can be started from the main workstation
- the backend can push trader speech via `/speak`

The local reference/sample stack lives under:
- `agora-agent-samples/simple-backend`
- `agora-agent-samples/react-video-client-avatar`

## Known Gaps

This repo is buildable and testable locally, but not yet at the “finished product” level.

Main remaining gaps:
- end-to-end browser test coverage
- stronger SSE state updates without broad refetches everywhere
- more sophisticated trader follow-up routing heuristics
- better frontend state management as the workstation grows
- clearer separation between mock/demo and live data behaviors

## Planning Docs

- [trading_plan_codex.md](/Users/benwekes/work/trading/trading_plan_codex.md): main implementation plan
- [trading_plan_claude.md](/Users/benwekes/work/trading/trading_plan_claude.md): secondary planning/reference doc

## AI Docs Still Needed

For human readers, this README should be enough to get started.

For AI/coding-agent workflows, the repo still needs dedicated AI-facing docs. The most useful additions would be:

1. `AGENT.md`
   - repo overview
   - architecture rules
   - where not to put code
   - how the role system works
   - how approval/execution state must behave
   - local run/test commands

2. `docs/ai/backend.md`
   - route map
   - orchestration flow
   - database tables
   - SSE event contracts
   - Agora integration points

3. `docs/ai/frontend.md`
   - workstation layout rules
   - desk chat semantics
   - key components and state flow
   - avatar panel integration notes

4. `docs/ai/testing.md`
   - required critical-path tests
   - paper-execution release gate
   - mock vs live testing rules

If you want, next I can write those AI-facing docs as well so the repo is easier for future agents to modify safely.
