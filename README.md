# AI Trading Platform

Multi-role AI trading workstation with four desk roles that analyse market events, deliberate, and present trade recommendations for human approval.

## How It Works

Four AI roles each have their own context and session, backed by GPT-5.1 (configurable per role):

| Role | Job | Example |
|------|-----|---------|
| **Research** | Fundamental thesis, beat quality, guidance | "Revenue-driven beat, guidance raised. Confidence 0.8." |
| **Risk** | Challenge the thesis, flag portfolio risk, sizing | "Gap reversal risk. Reduce to 0.75 standard size." |
| **Quant Pricing** | Price levels, entry/stop/target, vol regime | "Fair value 118. Entry 108-110, stop 104, target 116-120." |
| **Trader** | Synthesise all roles, make the call | "BUY NVDA. Conviction 8/10. Entry 892, target 982, stop 847." |

The flow:
1. Event arrives (earnings, news, price move) or you click **Random Event**
2. Research, Risk, and Quant analyse in parallel
3. Trader queries the other roles and synthesises a recommendation
4. You discuss with any role via `@role` mentions in the desk chat
5. You approve (with editable share count) or reject
6. Approved trades execute as paper orders

## Screenshot Layout

```
┌─────────────┬──────────────────┬──────────────────┐
│  INBOX      │  TRADE PANEL     │  AVATAR          │
│             │  + summary       │  + Start/Mute/End│
│  Events tab │  + buy controls  │                  │
│  Recs tab   │                  │  PORTFOLIO       │
│             │  DESK CHAT       │  + positions     │
│             │  + @role routing  │  + sell controls │
│             │  + role filters  │                  │
└─────────────┴──────────────────┴──────────────────┘
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/BenWeekes/trading.git
cd trading

# 2. Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY at minimum

# 3. Backend
cd backend
python3 -m venv ../.venv
../.venv/bin/pip install './[dev]'
../.venv/bin/uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 5. Open http://localhost:3000
# Click "Random Event" to start
```

## One-Command Local Stack

To start or repair the full local stack, including the Cloudflare tunnel used by Agora ConvoAI:

```bash
make stack-restart
```

That command will:
- restart the trading backend on `8000`
- restart the frontend on `3000`
- restart the Agora sample backend on `8082`
- restart the avatar client on `8084`
- start a fresh `cloudflared` quick tunnel to `http://localhost:8000`
- rewrite `agora-agent-samples/simple-backend/.env` so `VIDEO_LLM_URL` points at the current tunnel
- verify:
  - `http://localhost:3000`
  - `http://localhost:8000/api/status`
  - `http://localhost:8082/health`
  - `http://localhost:8084`
  - tunneled `POST /api/agora/chat/completions`

Use these commands afterward:

```bash
make stack-check
make stack-down
```

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...          # GPT-5.1 (or any OpenAI model)
OPENAI_MODEL=gpt-5.1           # gpt-5.x uses Responses API, gpt-4.x uses Chat API

# Market data (for real scans)
FMP_API_KEY=...                 # Financial Modeling Prep

# Broker (for paper trading)
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Optional: Agora avatar
AGORA_ENABLED=true
AGORA_BACKEND_URL=http://localhost:8082
AGORA_PROFILE=VIDEO
```

## Desk Chat

Type in the chat box at the centre of the workstation:

- `@research what's the thesis?` — routes to Research only
- `@risk what could go wrong?` — routes to Risk only
- `@quant_pricing where do I enter?` — routes to Quant only
- `@trader should I buy this?` — routes to Trader
- `what do you think?` — defaults to Trader
- Type `@` to see a role picker with keyboard navigation (arrow keys + Enter)

Filter buttons in the chat header let you view one role's messages at a time.

## Trade Actions

| Action | Meaning |
|--------|---------|
| **BUY** | Open or add to a long position |
| **SELL** | Reduce or close a long position |
| **SHORT** | Open or add to a short position |
| **COVER** | Reduce or close a short position |
| **PASS** | No trade — best action is to wait |

PASS events show in the Events tab with a badge. They are filtered out of the Recommendations tab.

## Recommendation States

`observing` → `under_discussion` → `draft_recommendation` → `awaiting_user_feedback` → `awaiting_user_approval` → `approved` → `submitted` → `filled` → `closed`

- Approve/Reject buttons appear from `awaiting_user_feedback` onward
- Execute button appears only after approval
- Share count is editable before approval

## Trader Avatar (Optional)

The right column includes an Agora-powered trader avatar that speaks recommendations aloud.

Requirements:
- Agora simple-backend running on port 8082 with valid credentials
- `AGORA_ENABLED=true` in `.env`
- Avatar vendor configured in Agora backend (HeyGen, Anam, or Akool)

Controls: **Start Call** (connects RTC + starts agent), **Mute/Unmute** mic, **End Call**.

## Architecture

| Layer | Tech | Purpose |
|-------|------|---------|
| Frontend | Next.js + React + TypeScript | 3-column workstation UI |
| Backend | FastAPI (Python) | API, role orchestration, SSE, state machine |
| LLM | OpenAI GPT-5.1 (configurable per role) | All role analysis and chat |
| Database | SQLite | Events, recommendations, role messages, trades, costs |
| Broker | Alpaca | Paper trading execution |
| Data | FMP | Earnings, quotes, news |
| Avatar | Agora RTC | Optional voice/video trader avatar |

Each role has its own:
- System prompt (`backend/app/roles/prompts/{role}_v1.md`)
- Conversation thread (per recommendation)
- Model config (provider, model, temperature, token budget)
- Cost tracking

## API Routes

### Core
- `POST /api/scan` — Run PEAD earnings scan
- `POST /api/demo/random-event` — Generate a demo event with full role analysis
- `GET /api/events` — List events
- `GET /api/recs` — List recommendations
- `GET /api/recs/{id}` — Recommendation detail + summary + timeline
- `POST /api/recs/{id}/discuss` — Send chat message (supports @role routing)
- `POST /api/recs/{id}/approve` — Approve (accepts `{ shares }`)
- `POST /api/recs/{id}/execute` — Execute approved recommendation
- `POST /api/recs/{id}/reject` — Reject with reason
- `POST /api/trades/{id}/sell` — Sell/close position (full or partial)
- `GET /api/positions` — Open positions
- `GET /api/portfolio` — Portfolio summary
- `GET /api/stream` — SSE event stream

### Avatar
- `POST /api/trader/avatar/start` — Start Agora agent session
- `POST /api/trader/avatar/stop` — End session
- `GET /api/trader/avatar/status` — Session status

## Testing

```bash
cd backend && ../.venv/bin/python -m pytest     # Backend tests
cd frontend && npm run build                     # Frontend build check
```

## Project Structure

```
trading/
├── backend/
│   ├── app/
│   │   ├── adapters/llm/       # LLM provider abstraction (OpenAI, mock)
│   │   ├── roles/              # Role system + orchestrator
│   │   │   └── prompts/        # System prompts per role (versioned)
│   │   ├── routes/             # FastAPI endpoints
│   │   ├── services/           # Scanner, filters, state machine, event bus
│   │   ├── db/                 # SQLite repositories
│   │   └── models/             # Pydantic models
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── layout/         # Header, InboxTabs
│       │   ├── roles/          # GroupChat
│       │   └── trades/         # TradePanel, AvatarAndPositions
│       ├── hooks/              # useSSE, useAgoraAvatar
│       └── lib/                # API client, types
├── data/                       # SQLite DB + mock scenarios
├── trading_plan_claude.md      # Comprehensive build plan
├── trading_plan_codex.md       # Product/architecture plan
└── claude_implement.md         # Implementation log
```

## Planning Docs

- `trading_plan_claude.md` — Full build specification (1900 lines): strategies, role schemas, state machine, DB schema, API spec, SSE format, cost estimate, migration plan
- `trading_plan_codex.md` — Product direction, MVP scope, UX design, build sequence
- `claude_implement.md` — Session-by-session implementation log with git commits
