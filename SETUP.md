# Weekes AI Assisted Trading Fund — Phase 1 Setup

## Step 1: Create API Accounts

You need two free accounts:

### FMP (Financial Modeling Prep)
1. Go to https://site.financialmodelingprep.com/register
2. Sign up for a free account
3. Copy your API key from the dashboard

### Alpaca (Paper Trading)
1. Go to https://app.alpaca.markets/signup
2. Sign up and verify your email
3. Switch to **Paper Trading** (toggle in top nav)
4. Go to **API Keys** and generate a new key pair
5. Copy both the API Key ID and the Secret Key

## Step 2: Configure Environment

```bash
cd weekes-investments
cp .env.example .env
```

Open `.env` in a text editor and paste in your keys:
```
FMP_API_KEY=abc123...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
```

## Step 3: Install Python Dependencies

```bash
# Make sure you have Python 3.11+
python3 --version

# Install dependencies
pip3 install -r requirements.txt
```

## Step 4: Test Your Connection

```bash
# Test Alpaca connection
python3 main.py --test-connection

# Run filters without placing orders
python3 main.py --check-only
```

## Step 5: Daily Morning Routine

Run before 9:30 AM ET each trading day:

```bash
cd weekes-investments
python3 main.py
```

This will:
1. Scan FMP for earnings surprises on the watchlist
2. Run all three filter layers on qualifying stocks
3. Calculate position sizes and submit bracket orders
4. Log everything to `phase1/trade_log.csv`
5. Check open positions for time stops

### Useful commands

```bash
python3 main.py                  # full daily run
python3 main.py --check-only     # filters only, no orders
python3 main.py --summary        # view trade log stats
python3 main.py --test-connection # verify Alpaca is working
```

## Step 6: Launch the Dashboard

```bash
# (Optional) Load demo data to see the dashboard populated:
python3 demo_data.py

# Start the dashboard server:
python3 dashboard_server.py

# Open in your browser:
# http://localhost:5050
```

The dashboard auto-refreshes every 60 seconds and shows live data from Alpaca
plus your trade/earnings CSV logs. To remove demo data later:

```bash
python3 demo_data.py --clear
```

## File Structure

```
weekes-investments/
├── main.py                    # Daily runner — start here
├── dashboard_server.py        # Flask dashboard server (port 5050)
├── demo_data.py               # Generate/clear demo data
├── dashboard/
│   └── index.html             # Dashboard UI (dark trading theme)
├── phase1/
│   ├── earnings_scanner.py    # FMP earnings fetch + surprise calc
│   ├── paper_trader.py        # 3-layer filter + Alpaca orders
│   ├── trade_logger.py        # CSV trade log + time stop checks
│   ├── trade_log.csv          # Created on first trade (auto)
│   └── earnings_log.csv       # Created on first scan (auto)
├── .env                       # Your API keys (never commit)
├── .env.example               # Template
├── .gitignore
└── requirements.txt
```

## Watchlist

NVDA, AAPL, MSFT, META, AMZN, GOOGL, AMD, PLTR, CRM

SPY is used for the market regime check (Layer 1) but is not traded.

## Rules (from the plan — do not change mid-test)

- **Entry**: Open of first regular session after earnings, all 3 filters green, gap < 8%
- **Stop-loss**: 5% below entry (hard stop, not adjusted)
- **Take-profit**: Entry + 2× stop distance (2:1 R:R)
- **Time stop**: Close at day 20 if neither target nor stop hit
- **Position size**: Risk 2% of $10,000 portfolio per trade
- **No discretionary overrides**: Rules execute as set
