# Weekes AATF — Claude Code Handoff Document
## Last updated: 2026-04-01

---

## PROJECT OVERVIEW

**Weekes AI Assisted Trading Fund (AATF)** — A PEAD (Post-Earnings Announcement Drift) paper trading system running on Ben's Mac Mini.

**Location on Mac Mini:** `/Users/benwekes/work/trading`

**What it does:** Scans for earnings surprises across all US stocks (≥$1B market cap), applies 3-layer filters, shows candidates on a web dashboard with news/quant data, and lets the user Accept or Reject trades which submit bracket orders to Alpaca paper trading.

---

## CURRENT STATUS (Phase 1 — COMPLETE & RUNNING)

### What's Working
- **Dashboard server** (`dashboard_server.py`) — Zero-dependency Python server using only stdlib (http.server, urllib.request). Runs on port 5050.
- **FMP API** — Connected via new `/stable/` endpoints (v3 endpoints were deprecated Aug 2025). Earnings calendar, quotes, news, price targets all working.
- **Alpaca API** — Connected to paper trading account. $100,000 paper cash. Status: ACTIVE.
- **Full market scan** — Scans ALL stocks reporting earnings (not just a watchlist), filtered to ≥$1B market cap.
- **3-layer filter** — SPY > 200d MA, stock > 50d MA, gap < 8%. Shows pass/fail on each.
- **Trade candidates panel** — Cards with Accept/Reject (or Override & Buy for filtered-out stocks), showing EPS surprise, filter results, quant data, analyst price targets, and recent news.
- **Bracket orders** — Accept submits market buy + take-profit + stop-loss to Alpaca.
- **CSV trade logging** — Every trade logged to `phase1/trade_log.csv`.
- **First real candidate found:** NKE (Nike) +20.7% EPS surprise on 2026-03-31. Correctly filtered out (all 3 layers failed).

### How to Start
Double-click `Start Dashboard.command` in Finder, or from Terminal:
```bash
cd /Users/benwekes/work/trading
python3 dashboard_server.py
# Open http://localhost:5050
```

### How to Stop
Ctrl+C in the Terminal window, or close the Terminal window.

---

## FILE STRUCTURE

```
weekes-investments/
├── .env                      # API keys (FMP, Alpaca) — DO NOT COMMIT
├── dashboard_server.py       # THE MAIN FILE — zero-dep server, all logic
├── dashboard/
│   └── index.html            # Dark-themed trading dashboard UI
├── phase1/
│   ├── trade_log.csv         # Trade history
│   ├── earnings_log.csv      # Earnings events scanned
│   ├── pending_candidates.json # Current scan candidates
│   ├── earnings_scanner.py   # Original scanner (uses requests — NOT USED by server)
│   ├── paper_trader.py       # Original trader (uses alpaca_trade_api — NOT USED by server)
│   └── trade_logger.py       # CSV logging helper
├── main.py                   # Original daily runner script
├── demo_data.py              # Generates fake data for testing
├── requirements.txt          # pip deps (for phase1/ scripts, NOT needed for dashboard)
├── Start Dashboard.command   # Double-click to start server
├── Run Scanner.command       # Double-click to run scanner
└── SETUP.md                  # Original setup instructions
```

**IMPORTANT:** `dashboard_server.py` is self-contained. It does NOT import from `phase1/` modules. All API calls use `urllib.request` (stdlib). No pip packages needed.

---

## KEY TECHNICAL DETAILS

### API Endpoints (FMP — new stable API)
FMP deprecated their `/api/v3/` endpoints after Aug 2025. We use `/stable/`:
- Earnings calendar: `https://financialmodelingprep.com/stable/earnings-calendar?from=...&to=...&apikey=...`
- Quote: `https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=...`
- News: `https://financialmodelingprep.com/stable/news/stock-latest?symbol=...&limit=5&apikey=...`
- Price targets: `https://financialmodelingprep.com/stable/price-target-consensus?symbol=...&apikey=...`
- Analyst estimates: may not exist at `/stable/` path — handled gracefully

### API Endpoints (Alpaca — paper trading REST)
- Base: `https://paper-api.alpaca.markets/v2/`
- Auth headers: `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`
- Account: GET `/v2/account`
- Positions: GET `/v2/positions`
- Orders: POST `/v2/orders` (bracket orders with take_profit + stop_loss)

### Dashboard Server Endpoints
- `GET /api/portfolio` — Alpaca account summary
- `GET /api/positions` — Open positions
- `GET /api/trades` — Trade history from CSV
- `GET /api/scanner` — Earnings events log
- `GET /api/status` — System health check
- `GET /api/candidates` — Load saved candidates
- `GET /api/scan` — Run full earnings scan (hits FMP, takes ~5-15s)
- `POST /api/accept` — Accept trade, submit bracket order to Alpaca
- `POST /api/reject` — Reject candidate with reason

### Strategy Parameters (in dashboard_server.py)
```python
FOCUS_LIST = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "AMD", "PLTR", "CRM"]
MIN_SURPRISE_PCT = 5.0          # EPS beat must be ≥5%
MIN_MARKET_CAP = 1_000_000_000  # $1B minimum
RISK_PER_TRADE = 0.02           # 2% of portfolio per trade
STOP_LOSS_PCT = 0.05            # 5% stop-loss
REWARD_RISK_RATIO = 2.0         # 2:1 reward-to-risk
MAX_GAP_PCT = 0.08              # Skip if gap > 8%
SCAN_ALL_STOCKS = True          # Scan every earnings event, not just focus list
```

### Known Issues / Gotchas
- The `+900% Total Return` shown on dashboard is a display bug — it's because `PORTFOLIO_SIZE=10000` in .env but Alpaca paper account has $100,000. Need to either update .env to 100000 or fix the calculation.
- `phase1/` Python scripts use `requests`, `yfinance`, `alpaca_trade_api` — these may not be pip-installed. The dashboard server doesn't need them.
- Xcode command line tools ARE installed now, so `pip3 install` works.
- FMP free tier has rate limits — scanning 50+ stocks can be slow. SPY quote is cached per scan to reduce calls.

---

## PHASE 2 PLAN: AI Analysis Layer (NEXT)

### Goal
Add AI agents that read earnings press releases and provide three classifications per candidate, displayed on the dashboard card alongside the existing quant data.

### Three AI Classifications
1. **Beat Quality Classifier** — Read the earnings press release and classify as:
   - `REVENUE_DRIVEN` (strongest signal for PEAD)
   - `MARGIN_EXPANSION`
   - `ONE_OFF`
   - `ACCOUNTING`
   Output a brief justification.

2. **Guidance Change Detector** — Read management commentary and classify as:
   - `RAISED` (bullish — strongest drift)
   - `MAINTAINED`
   - `LOWERED`
   - `NOT_PROVIDED`

3. **Risk/Catalyst Extractor** — Identify:
   - Single most important near-term catalyst (bullish)
   - Single most important near-term risk (bearish)
   Within 30-day window.

### Implementation Approach
- Option A: Use TradingAgents (open-source multi-agent LLM framework) — `git clone` + pip install
- Option B: Direct Claude API calls with structured prompts for each classifier
- Option C: Use Anthropic's tool_use to call Claude with earnings text and get structured JSON back

### Phase 2 Rules
- AI outputs are **displayed but don't block trades** initially
- Continue paper trading with baseline rules
- After 30+ completed trades: analyze if AI classifications correlate with outcomes
- If `REVENUE_DRIVEN + RAISED` guidance trades outperform, add as optional filter
- Milestone: 30+ paper trades with AI output logged, correlation analysis done

---

## PHASE 3 PLAN: Full Dashboard + Risk Controls

- Deploy dashboard to cloud (Fly.io) with authentication
- Circuit breaker: halt trading if drawdown exceeds 15%
- Earnings blackout: no new entries within 48h of existing position's next earnings
- Agent performance tracker: win rate by AI classification type
- Email/SMS alerts when new qualifying triggers fire

---

## PHASE 4 PLAN: Live Capital (Post-validation)

- Only after Phase 3 out-of-sample validation passes
- Keep human approval mandatory on every trade
- Run paper + live in parallel to compare fill quality
- Scale position size only after 60+ live trades confirm results

---

## ORIGINAL PLAN DOCUMENT
The full 19-page implementation plan is at:
`/Users/benwekes/work/trading/` (uploaded as PDF earlier, may be in uploads folder)

---

## QUICK START FOR CLAUDE CODE

```bash
cd ~/work/trading
# Read this file first:
cat CLAUDE_CODE_HANDOFF.md
# The main server file:
cat dashboard_server.py
# Start the server:
python3 dashboard_server.py
# Test the scan:
curl http://localhost:5050/api/scan | python3 -m json.tool
# Test Alpaca connection:
curl http://localhost:5050/api/status | python3 -m json.tool
```
