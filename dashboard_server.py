#!/usr/bin/env python3
"""
Weekes AI Assisted Trading Fund — Dashboard Server

ZERO-DEPENDENCY Python web server. Uses only the standard library.
No pip, no Flask, no requests, no yfinance needed.

All external API calls use urllib.request (built into Python).
  - FMP API → earnings, quotes, news, analyst data
  - Alpaca REST API → account, positions, orders

Usage:
    cd weekes-investments
    python3 dashboard_server.py
    # Open http://localhost:5050
"""

import os
import sys
import csv
import json
import math
import ssl
import traceback
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── Load .env manually ──────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_env(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

load_env(os.path.join(BASE_DIR, ".env"))

# ─── Config ───────────────────────────────────────────────────────

TRADE_LOG = os.path.join(BASE_DIR, "phase1", "trade_log.csv")
EARNINGS_LOG = os.path.join(BASE_DIR, "phase1", "earnings_log.csv")
CANDIDATES_FILE = os.path.join(BASE_DIR, "phase1", "pending_candidates.json")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
PORTFOLIO_SIZE = float(os.environ.get("PORTFOLIO_SIZE", "10000"))
PORT = 5050

# Strategy parameters
FOCUS_LIST = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "AMD", "PLTR", "CRM"]
MIN_SURPRISE_PCT = 5.0
MIN_MARKET_CAP = 1_000_000_000  # $1B minimum market cap to avoid illiquid micro-caps
RISK_PER_TRADE = 0.02
STOP_LOSS_PCT = 0.05
REWARD_RISK_RATIO = 2.0
MAX_GAP_PCT = 0.08
SCAN_ALL_STOCKS = True  # When True, scan every earnings event (not just focus list)

# SSL context for HTTPS calls
SSL_CTX = ssl.create_default_context()


# ─── HTTP Helpers (stdlib only) ───────────────────────────────────

def http_get(url, headers=None, timeout=15):
    """GET request using urllib. Returns parsed JSON or None."""
    try:
        req = Request(url, headers=headers or {})
        with urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [HTTP GET ERROR] {url[:80]}... → {e}")
        return None


def http_post(url, data, headers=None, timeout=15):
    """POST request using urllib. Returns parsed JSON or None."""
    try:
        body = json.dumps(data).encode("utf-8")
        hdrs = {"Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        req = Request(url, data=body, headers=hdrs, method="POST")
        with urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [HTTP POST ERROR] {url[:80]}... → {e}")
        return None


# ─── FMP API (stdlib) — using NEW /stable/ endpoints ─────────────

def fmp_get(endpoint, params=None):
    """Call FMP stable API endpoint. Adds API key automatically."""
    p = params or {}
    p["apikey"] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}?{urlencode(p)}"
    return http_get(url)


def fmp_earnings_calendar(from_date, to_date):
    return fmp_get("earnings-calendar", {"from": from_date, "to": to_date}) or []


def fmp_quote(symbol):
    """Get real-time quote for a symbol via /stable/quote?symbol=..."""
    data = fmp_get("quote", {"symbol": symbol})
    if isinstance(data, list):
        return data[0] if data else {}
    return data if data else {}


def fmp_stock_news(symbol, limit=5):
    return fmp_get("news/stock-latest", {"symbol": symbol, "limit": limit}) or []


def fmp_price_target(symbol):
    data = fmp_get("price-target-consensus", {"symbol": symbol})
    if isinstance(data, list):
        return data[0] if data else {}
    return data if data else {}


def fmp_analyst_estimates(symbol):
    """Try stable analyst-estimates; returns empty dict if unavailable."""
    data = fmp_get("analyst-estimates", {"symbol": symbol, "limit": 1})
    if isinstance(data, list):
        return data[0] if data else {}
    return data if data else {}


# ─── Alpaca API (stdlib) ──────────────────────────────────────────

def alpaca_headers():
    return {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    }


def alpaca_get(path):
    url = f"{ALPACA_BASE_URL}/v2/{path}"
    return http_get(url, headers=alpaca_headers())


def alpaca_post(path, data):
    url = f"{ALPACA_BASE_URL}/v2/{path}"
    hdrs = alpaca_headers()
    hdrs["Content-Type"] = "application/json"
    return http_post(url, data, headers=hdrs)


def get_alpaca_account():
    try:
        acct = alpaca_get("account")
        if not acct:
            return {"error": "No response from Alpaca"}
        return {
            "cash": float(acct["cash"]),
            "portfolio_value": float(acct["portfolio_value"]),
            "buying_power": float(acct["buying_power"]),
            "equity": float(acct["equity"]),
            "last_equity": float(acct["last_equity"]),
            "status": acct["status"],
            "currency": acct.get("currency", "USD"),
            "daily_change": round(float(acct["equity"]) - float(acct["last_equity"]), 2),
            "daily_change_pct": round(
                ((float(acct["equity"]) - float(acct["last_equity"])) / float(acct["last_equity"])) * 100, 2
            ) if float(acct["last_equity"]) > 0 else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def get_alpaca_positions():
    try:
        positions = alpaca_get("positions") or []
        return [{
            "symbol": p["symbol"],
            "qty": float(p["qty"]),
            "avg_entry": float(p["avg_entry_price"]),
            "current_price": float(p["current_price"]),
            "market_value": float(p["market_value"]),
            "unrealized_pl": float(p["unrealized_pl"]),
            "unrealized_plpc": round(float(p["unrealized_plpc"]) * 100, 2),
            "side": p["side"],
        } for p in positions]
    except Exception:
        return []


# ─── CSV Helpers ──────────────────────────────────────────────────

def read_csv_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def append_csv(path, row, fieldnames):
    exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


# ─── Candidate Storage ────────────────────────────────────────────

def save_candidates(candidates):
    with open(CANDIDATES_FILE, "w") as f:
        json.dump(candidates, f, indent=2)


def load_candidates():
    if not os.path.exists(CANDIDATES_FILE):
        return []
    with open(CANDIDATES_FILE) as f:
        return json.load(f)


# ─── Position Sizing ─────────────────────────────────────────────

def calculate_position(entry_price):
    stop_price = round(entry_price * (1 - STOP_LOSS_PCT), 2)
    risk_per_share = entry_price - stop_price
    max_risk = PORTFOLIO_SIZE * RISK_PER_TRADE
    shares = math.floor((max_risk / risk_per_share) * 100) / 100
    target_price = round(entry_price + (REWARD_RISK_RATIO * (entry_price - stop_price)), 2)
    return {
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "shares": shares,
        "total_risk": round(shares * risk_per_share, 2),
    }


# ═══════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

def api_portfolio():
    account = get_alpaca_account()
    return {
        "account": account,
        "initial_capital": PORTFOLIO_SIZE,
        "total_return": round(
            ((account.get("portfolio_value", PORTFOLIO_SIZE) - PORTFOLIO_SIZE) / PORTFOLIO_SIZE) * 100, 2
        ) if account and "error" not in account else 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


def api_positions():
    alpaca_positions = get_alpaca_positions()
    trades = read_csv_file(TRADE_LOG)
    open_trades = [t for t in trades if not t.get("exit_date")]
    return {
        "alpaca_positions": alpaca_positions,
        "open_trades": open_trades,
        "count": len(alpaca_positions),
    }


def api_trades():
    trades = read_csv_file(TRADE_LOG)
    closed = [t for t in trades if t.get("exit_date")]
    total_pnl = sum(float(t.get("pnl_dollars", 0) or 0) for t in closed)
    wins = [t for t in closed if float(t.get("pnl_dollars", 0) or 0) > 0]
    losses = [t for t in closed if float(t.get("pnl_dollars", 0) or 0) <= 0]
    return {
        "trades": list(reversed(trades)),
        "stats": {
            "total_trades": len(trades), "open": len(trades) - len(closed),
            "closed": len(closed), "wins": len(wins), "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(sum(float(t["pnl_dollars"]) for t in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(float(t["pnl_dollars"]) for t in losses) / len(losses), 2) if losses else 0,
        },
    }


def api_scanner():
    events = read_csv_file(EARNINGS_LOG)
    return {"earnings_events": list(reversed(events))[:50], "total_logged": len(events)}


def api_status():
    def file_status(path):
        if not os.path.exists(path):
            return {"exists": False, "modified": None, "rows": 0}
        return {"exists": True, "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(), "rows": len(read_csv_file(path))}
    account = get_alpaca_account()
    return {
        "alpaca_connected": account is not None and "error" not in account,
        "alpaca_status": account.get("status", "unknown") if account else "disconnected",
        "trade_log": file_status(TRADE_LOG),
        "earnings_log": file_status(EARNINGS_LOG),
        "server_time": datetime.utcnow().isoformat(),
        "mode": "paper",
        "focus_list": FOCUS_LIST,
        "scan_mode": "all stocks (≥$1B market cap)" if SCAN_ALL_STOCKS else "focus list only",
    }


def api_candidates():
    return {"candidates": load_candidates()}


# ─── SCAN NOW — fully stdlib ─────────────────────────────────────

def api_scan_now():
    """
    Scan FMP for earnings surprises, run filters using FMP quote data,
    enrich with news + analyst data. All using urllib — no pip packages.
    """
    print("\n[SCAN] Starting earnings scan...")
    results = []
    errors = []
    api_scan_now._spy_cache = None  # fresh SPY quote each scan

    try:
        today = datetime.utcnow().date()
        from_date = (today - timedelta(days=3)).isoformat()
        to_date = (today + timedelta(days=1)).isoformat()

        print(f"[SCAN] Fetching FMP earnings: {from_date} to {to_date}")
        all_events = fmp_earnings_calendar(from_date, to_date)
        print(f"[SCAN] Got {len(all_events)} total events")

        # Filter: either scan all stocks or just focus list
        if SCAN_ALL_STOCKS:
            scan_events = [e for e in all_events if e.get("symbol")]
            print(f"[SCAN] Scanning ALL {len(scan_events)} events (full market mode)")
        else:
            scan_events = [e for e in all_events if e.get("symbol") in FOCUS_LIST]
            print(f"[SCAN] {len(scan_events)} on focus list")

        for event in scan_events:
            symbol = event.get("symbol", "")
            actual = event.get("epsActual")       # stable API field name
            estimate = event.get("epsEstimated")

            if actual is None or estimate is None or estimate == 0:
                print(f"  [SKIP] {symbol}: missing EPS data")
                continue

            surprise_pct = round(((actual - estimate) / abs(estimate)) * 100, 2)
            print(f"  [INFO] {symbol}: surprise = {surprise_pct:+.2f}%")

            # Log earnings event
            append_csv(EARNINGS_LOG, {
                "symbol": symbol, "date": event.get("date", ""),
                "actual_eps": actual, "estimated_eps": estimate,
                "surprise_pct": surprise_pct,
                "revenue": event.get("revenueActual"), "revenue_estimated": event.get("revenueEstimated"),
                "fmp_updated": event.get("lastUpdated", ""),
                "query_timestamp": datetime.utcnow().isoformat(),
            }, ["symbol","date","actual_eps","estimated_eps","surprise_pct","revenue","revenue_estimated","fmp_updated","query_timestamp"])

            if surprise_pct < MIN_SURPRISE_PCT:
                print(f"  [SKIP] {symbol}: below {MIN_SURPRISE_PCT}% threshold")
                continue

            is_focus = symbol in FOCUS_LIST
            print(f"  [TRIGGER] {symbol}: qualifies! Running filters...{'  ⭐ FOCUS' if is_focus else ''}")

            # ── Get quote for filter checks (cache SPY) ──
            quote = fmp_quote(symbol)
            if not hasattr(api_scan_now, '_spy_cache') or api_scan_now._spy_cache is None:
                api_scan_now._spy_cache = fmp_quote("SPY")
            spy_quote = api_scan_now._spy_cache

            if not quote or not spy_quote:
                errors.append(f"{symbol}: could not fetch quote data")
                continue

            # ── Market cap filter (skip micro-caps) ──
            mcap = quote.get("marketCap", 0) or 0
            if mcap < MIN_MARKET_CAP:
                print(f"    [SKIP] {symbol}: market cap ${mcap:,.0f} below ${MIN_MARKET_CAP:,.0f}")
                continue

            price = quote.get("price", 0)
            ma50 = quote.get("priceAvg50", 0)
            ma200_spy = spy_quote.get("priceAvg200", 0)
            spy_price = spy_quote.get("price", 0)
            prev_close = quote.get("previousClose", 0)
            today_open = quote.get("open", price)

            # ── Layer 1: SPY > 200d MA ──
            regime_pass = spy_price > ma200_spy if (spy_price and ma200_spy) else False
            regime = {"pass": regime_pass, "price": spy_price, "ma_200": ma200_spy,
                      "margin": round(((spy_price / ma200_spy) - 1) * 100, 2) if ma200_spy else 0}

            # ── Layer 2: Stock > 50d MA ──
            momentum_pass = price > ma50 if (price and ma50) else False
            momentum = {"pass": momentum_pass, "price": price, "ma_50": ma50,
                        "margin": round(((price / ma50) - 1) * 100, 2) if ma50 else 0}

            # ── Gap check ──
            gap_pct = round(((today_open - prev_close) / prev_close) * 100, 2) if prev_close else 0
            gap_pass = abs(gap_pct) <= (MAX_GAP_PCT * 100)
            gap = {"pass": gap_pass, "prior_close": prev_close, "today_open": today_open, "gap_pct": gap_pct}

            all_pass = regime_pass and momentum_pass and gap_pass
            blocked_by = None
            if not regime_pass: blocked_by = "regime"
            elif not momentum_pass: blocked_by = "momentum"
            elif not gap_pass: blocked_by = "gap"

            print(f"    Regime: {'PASS' if regime_pass else 'FAIL'} | Momentum: {'PASS' if momentum_pass else 'FAIL'} | Gap: {'PASS' if gap_pass else 'FAIL'}")

            # ── Build candidate ──
            candidate = {
                "id": f"{symbol}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "symbol": symbol,
                "surprise_pct": surprise_pct,
                "actual_eps": actual,
                "estimated_eps": estimate,
                "earnings_date": event.get("date", ""),
                "market_cap": mcap,
                "is_focus": is_focus,
                "filters_passed": all_pass,
                "blocked_by": blocked_by,
                "scanned_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "regime": regime,
                "momentum": momentum,
                "gap": gap,
            }

            # Position sizing if passed
            if all_pass and today_open > 0:
                pos = calculate_position(today_open)
                candidate.update({
                    "entry_price": pos["entry_price"],
                    "target_price": pos["target_price"],
                    "stop_price": pos["stop_price"],
                    "shares": pos["shares"],
                    "total_risk": pos["total_risk"],
                })

            # ── Enrich with news + quant ──
            research = {"quote": {}, "news": [], "price_target": {}, "analyst": {}}

            # Quote data
            research["quote"] = {
                "price": quote.get("price"),
                "change_pct": round(quote.get("changePercentage", 0), 2),
                "volume": quote.get("volume"),
                "avg_volume": quote.get("avgVolume"),   # may be None in stable API
                "volume_ratio": round(quote.get("volume", 0) / quote.get("avgVolume", 1), 2) if quote.get("avgVolume") else None,
                "market_cap": quote.get("marketCap"),
                "pe": quote.get("pe"),
                "eps": quote.get("eps"),
                "day_high": quote.get("dayHigh"),
                "day_low": quote.get("dayLow"),
                "year_high": quote.get("yearHigh"),
                "year_low": quote.get("yearLow"),
                "fifty_day_ma": quote.get("priceAvg50"),
                "two_hundred_day_ma": quote.get("priceAvg200"),
            }

            # News (stable API may use 'source' instead of 'site')
            news_data = fmp_stock_news(symbol, 5)
            research["news"] = [{
                "title": n.get("title", ""),
                "source": n.get("site", n.get("source", "")),
                "date": (n.get("publishedDate", "") or "")[:10],
                "url": n.get("url", ""),
                "snippet": (n.get("text", "")[:200] + "...") if n.get("text") else "",
            } for n in news_data[:5]]

            # Price target
            pt = fmp_price_target(symbol)
            if pt:
                research["price_target"] = {
                    "target_high": pt.get("targetHigh"),
                    "target_low": pt.get("targetLow"),
                    "target_consensus": pt.get("targetConsensus"),
                    "target_median": pt.get("targetMedian"),
                }

            # Analyst estimates
            ae = fmp_analyst_estimates(symbol)
            if ae:
                research["analyst"] = {
                    "estimated_eps_avg": ae.get("estimatedEpsAvg"),
                    "estimated_eps_high": ae.get("estimatedEpsHigh"),
                    "estimated_eps_low": ae.get("estimatedEpsLow"),
                    "number_analysts_estimated_eps": ae.get("numberAnalystsEstimatedEps"),
                }

            candidate["research"] = research
            results.append(candidate)
            print(f"    Candidate built with {len(research['news'])} news items")

        # Save candidates
        existing = load_candidates()
        existing_symbols = {c["symbol"] for c in results}
        kept = [c for c in existing if c["symbol"] not in existing_symbols or c["status"] != "pending"]
        save_candidates(kept + results)

    except Exception as e:
        print(f"[SCAN ERROR] {e}")
        traceback.print_exc()
        return {"error": str(e), "traceback": traceback.format_exc(), "candidates": results}

    print(f"[SCAN] Done. {len(results)} candidate(s) found.\n")
    return {
        "candidates": results,
        "scan_time": datetime.utcnow().isoformat(),
        "triggers_found": len(results),
        "errors": errors,
    }


# ─── Accept / Reject ─────────────────────────────────────────────

def api_accept_trade(data):
    candidate_id = data.get("candidate_id")
    candidates = load_candidates()
    target = next((c for c in candidates if c["id"] == candidate_id), None)

    if not target:
        return {"error": f"Candidate {candidate_id} not found"}

    override = not target.get("filters_passed")
    if override:
        print(f"[ORDER] ⚠️  OVERRIDE: {target['symbol']} did not pass filters — user chose to buy anyway")
        # Calculate position sizing for overridden trades if not already set
        price = target.get("entry_price") or target.get("research", {}).get("quote", {}).get("price", 0)
        if price and not target.get("entry_price"):
            pos = calculate_position(price)
            target.update({
                "entry_price": pos["entry_price"],
                "target_price": pos["target_price"],
                "stop_price": pos["stop_price"],
                "shares": pos["shares"],
                "total_risk": pos["total_risk"],
            })

    # Submit bracket order to Alpaca via REST API
    order_data = {
        "symbol": target["symbol"],
        "qty": str(target["shares"]),
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
        "order_class": "bracket",
        "take_profit": {"limit_price": str(target["target_price"])},
        "stop_loss": {"stop_price": str(target["stop_price"])},
    }

    print(f"[ORDER] Submitting bracket order for {target['symbol']}...")
    order = alpaca_post("orders", order_data)

    if not order:
        return {"error": "Alpaca order submission failed — check API keys and connection"}

    if "id" not in order:
        return {"error": f"Alpaca error: {order.get('message', json.dumps(order))}"}

    # Log trade
    trade_count = len(read_csv_file(TRADE_LOG))
    trade_id = f"AATF-{trade_count + 1:03d}"

    append_csv(TRADE_LOG, {
        "trade_id": trade_id,
        "symbol": target["symbol"],
        "entry_date": datetime.utcnow().isoformat(),
        "entry_price": target["entry_price"],
        "shares": target["shares"],
        "target_price": target["target_price"],
        "stop_price": target["stop_price"],
        "surprise_pct": target["surprise_pct"],
        "exit_date": "", "exit_price": "", "exit_reason": "",
        "pnl_dollars": "", "pnl_percent": "",
        "order_id": order["id"],
        "notes": "OVERRIDE — filters not passed" if override else "",
    }, ["trade_id","symbol","entry_date","entry_price","shares","target_price","stop_price",
        "surprise_pct","exit_date","exit_price","exit_reason","pnl_dollars","pnl_percent","order_id","notes"])

    target["status"] = "accepted"
    target["trade_id"] = trade_id
    target["order_id"] = order["id"]
    save_candidates(candidates)

    print(f"[ORDER] Trade {trade_id} submitted. Order ID: {order['id']}")
    return {"success": True, "trade_id": trade_id, "order_id": order["id"]}


def api_reject_trade(data):
    candidate_id = data.get("candidate_id")
    reason = data.get("reason", "Manual rejection")
    candidates = load_candidates()
    for c in candidates:
        if c["id"] == candidate_id:
            c["status"] = "rejected"
            c["reject_reason"] = reason
            c["rejected_at"] = datetime.utcnow().isoformat()
            save_candidates(candidates)
            return {"success": True, "symbol": c["symbol"], "reason": reason}
    return {"error": f"Candidate {candidate_id} not found"}


# ═══════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════

API_ROUTES = {
    "/api/portfolio":  api_portfolio,
    "/api/positions":  api_positions,
    "/api/trades":     api_trades,
    "/api/scanner":    api_scanner,
    "/api/status":     api_status,
    "/api/candidates": api_candidates,
    "/api/scan":       api_scan_now,
}

POST_ROUTES = {
    "/api/accept": api_accept_trade,
    "/api/reject": api_reject_trade,
}


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in API_ROUTES:
            try:
                self._send_json(API_ROUTES[path]())
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path in POST_ROUTES:
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw)
                self._send_json(POST_ROUTES[path](data))
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)
            return
        if path in API_ROUTES:
            try:
                self._send_json(API_ROUTES[path]())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return
        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"  [{ts}] {args[0]}\n")


# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Weekes AATF — Dashboard Server")
    print(f"  http://localhost:{PORT}")
    print("=" * 60)
    print(f"  FMP key:      {'set' if FMP_API_KEY else 'MISSING'}")
    print(f"  Alpaca key:   {'set' if ALPACA_API_KEY else 'MISSING'}")
    print(f"  Trade log:    {TRADE_LOG}")
    print(f"  Dashboard:    {DASHBOARD_DIR}")
    print()

    try:
        server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
        print(f"  Server running on port {PORT}. Press Ctrl+C to stop.\n")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()
