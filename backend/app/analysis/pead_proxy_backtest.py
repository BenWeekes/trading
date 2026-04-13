from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings

WATCHLIST = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "AMD", "PLTR", "CRM"]


@dataclass
class BacktestTrade:
    symbol: str
    earnings_date: str
    entry_date: str
    exit_date: str
    surprise_pct: float
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    shares: float
    gross_entry_dollars: float
    pnl_dollars: float
    pnl_pct: float
    exit_reason: str
    regime_pass: bool
    momentum_pass: bool
    gap_pass: bool
    gap_pct: float


@dataclass
class BacktestSummary:
    start_date: str
    entry_cutoff_date: str
    end_date: str
    total_events_checked: int
    total_entries: int
    wins: int
    losses: int
    win_rate_pct: float
    total_pnl_dollars: float
    avg_trade_pnl_pct: float
    median_trade_pnl_pct: float
    total_gross_deployed: float
    total_return_on_gross_pct: float


class FMPHistoricalClient:
    base_url = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
        settings = get_settings()
        self.cache_dir = settings.sqlite_path.parent / "fmp_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, endpoint: str, params: dict[str, Any]) -> Path:
        normalized = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True, default=str)
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, endpoint: str, **params: Any) -> Any:
        cache_path = self._cache_path(endpoint, params)
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        response = self.client.get(
            f"{self.base_url}/{endpoint}",
            params={**params, "apikey": self.api_key},
        )
        response.raise_for_status()
        payload = response.json()
        cache_path.write_text(json.dumps(payload))
        return payload

    def earnings(self, symbol: str) -> list[dict]:
        payload = self.get("earnings", symbol=symbol)
        return payload if isinstance(payload, list) else []

    def prices(self, symbol: str, start: date, end: date) -> list[dict]:
        payload = self.get(
            "historical-price-eod/full",
            symbol=symbol,
            **{"from": start.isoformat(), "to": end.isoformat()},
        )
        return payload if isinstance(payload, list) else []

    def close(self) -> None:
        self.client.close()


def subtract_months(value: date, months: int) -> date:
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(value.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def _iso_to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _prepare_bars(rows: list[dict]) -> tuple[list[dict], dict[date, int]]:
    cleaned: list[dict] = []
    for row in rows:
        bar_date = _iso_to_date(str(row["date"]))
        cleaned.append(
            {
                "date": bar_date,
                "open": float(row.get("open") or 0.0),
                "high": float(row.get("high") or 0.0),
                "low": float(row.get("low") or 0.0),
                "close": float(row.get("close") or 0.0),
                "volume": float(row.get("volume") or 0.0),
            }
        )
    cleaned.sort(key=lambda bar: bar["date"])
    by_date = {bar["date"]: idx for idx, bar in enumerate(cleaned)}
    return cleaned, by_date


def _find_next_trading_day_index(bars: list[dict], earnings_date: date) -> int | None:
    for idx, bar in enumerate(bars):
        if bar["date"] > earnings_date:
            return idx
    return None


def _moving_average(bars: list[dict], idx: int, window: int) -> float | None:
    if idx + 1 < window:
        return None
    closes = [bar["close"] for bar in bars[idx - window + 1 : idx + 1]]
    return sum(closes) / window


def _surprise_pct(event: dict) -> float | None:
    actual = event.get("epsActual")
    estimated = event.get("epsEstimated")
    if actual is None or estimated in (None, 0):
        return None
    return ((float(actual) - float(estimated)) / abs(float(estimated))) * 100


def _revenue_surprise_pct(event: dict) -> float | None:
    actual = event.get("revenueActual")
    estimated = event.get("revenueEstimated")
    if actual is None or estimated in (None, 0):
        return None
    return ((float(actual) - float(estimated)) / abs(float(estimated))) * 100


def _calculate_position(entry_price: float, portfolio_size: float, risk_per_trade: float, stop_loss_pct: float, reward_risk_ratio: float) -> dict:
    stop_price = round(entry_price * (1 - stop_loss_pct), 2)
    risk_per_share = max(entry_price - stop_price, 0.01)
    max_risk = portfolio_size * risk_per_trade
    shares = math.floor((max_risk / risk_per_share) * 100) / 100
    target_price = round(entry_price + (reward_risk_ratio * (entry_price - stop_price)), 2)
    return {
        "entry_price": round(entry_price, 2),
        "stop_price": stop_price,
        "target_price": target_price,
        "shares": shares,
        "gross_entry_dollars": round(shares * entry_price, 2),
    }


def _simulate_long_exit(bars: list[dict], entry_idx: int, stop_price: float, target_price: float, max_hold_days: int) -> tuple[int, float, str]:
    final_idx = min(len(bars) - 1, entry_idx + max_hold_days - 1)
    for idx in range(entry_idx, final_idx + 1):
        bar = bars[idx]
        hit_stop = bar["low"] <= stop_price if stop_price else False
        hit_target = bar["high"] >= target_price if target_price else False
        # Conservative same-day assumption: if both touched, assume stop first.
        if hit_stop:
            return idx, stop_price, "stop"
        if hit_target:
            return idx, target_price, "target"
    return final_idx, bars[final_idx]["close"], "time_stop"


def run_proxy_backtest(
    *,
    end_date: date,
    months_back: int,
    entry_window_days: int,
    portfolio_size: float,
    max_hold_days: int,
    symbols: list[str] | None = None,
) -> tuple[BacktestSummary, list[BacktestTrade]]:
    settings = get_settings()
    api_key = settings.fmp_api_key
    if not api_key:
        raise RuntimeError("FMP_API_KEY is required")

    watchlist = symbols or WATCHLIST
    start_date = subtract_months(end_date, months_back)
    entry_cutoff = start_date.fromordinal(start_date.toordinal() + entry_window_days)
    preload_start = start_date.fromordinal(start_date.toordinal() - 320)

    client = FMPHistoricalClient(api_key)
    try:
        symbol_bars: dict[str, tuple[list[dict], dict[date, int]]] = {}
        for symbol in [*watchlist, "SPY"]:
            rows = client.prices(symbol, preload_start, end_date)
            if not rows:
                raise RuntimeError(f"No historical prices returned for {symbol}")
            symbol_bars[symbol] = _prepare_bars(rows)

        spy_bars, spy_by_date = symbol_bars["SPY"]

        trades: list[BacktestTrade] = []
        total_events_checked = 0

        for symbol in watchlist:
            bars, _ = symbol_bars[symbol]
            earnings_rows = client.earnings(symbol)
            for event in earnings_rows:
                event_date_raw = event.get("date")
                if not event_date_raw:
                    continue
                earnings_date = _iso_to_date(str(event_date_raw))
                if not (start_date <= earnings_date < entry_cutoff):
                    continue
                surprise = _surprise_pct(event)
                if surprise is None:
                    continue
                total_events_checked += 1
                if surprise < settings.min_surprise_pct:
                    continue

                entry_idx = _find_next_trading_day_index(bars, earnings_date)
                if entry_idx is None or entry_idx == 0:
                    continue
                entry_bar = bars[entry_idx]
                prev_bar = bars[entry_idx - 1]

                entry_day = entry_bar["date"]
                spy_idx = spy_by_date.get(entry_day)
                if spy_idx is None:
                    continue

                regime_ma = _moving_average(spy_bars, spy_idx, 200)
                symbol_ma = _moving_average(bars, entry_idx, 50)
                if regime_ma is None or symbol_ma is None:
                    continue

                regime_pass = spy_bars[spy_idx]["close"] > regime_ma
                momentum_pass = entry_bar["close"] > symbol_ma
                gap_pct = ((entry_bar["open"] - prev_bar["close"]) / prev_bar["close"]) * 100 if prev_bar["close"] else 0.0
                gap_pass = abs(gap_pct) <= (settings.max_gap_pct * 100)

                if not (regime_pass and momentum_pass and gap_pass):
                    continue

                position = _calculate_position(
                    entry_bar["open"],
                    portfolio_size,
                    settings.risk_per_trade,
                    settings.stop_loss_pct,
                    settings.reward_risk_ratio,
                )
                exit_idx, exit_price, exit_reason = _simulate_long_exit(
                    bars,
                    entry_idx,
                    position["stop_price"],
                    position["target_price"],
                    max_hold_days,
                )
                pnl_dollars = round((exit_price - position["entry_price"]) * position["shares"], 2)
                pnl_pct = round(((exit_price - position["entry_price"]) / position["entry_price"]) * 100, 2)
                trades.append(
                    BacktestTrade(
                        symbol=symbol,
                        earnings_date=earnings_date.isoformat(),
                        entry_date=entry_day.isoformat(),
                        exit_date=bars[exit_idx]["date"].isoformat(),
                        surprise_pct=round(surprise, 2),
                        entry_price=position["entry_price"],
                        exit_price=round(exit_price, 2),
                        stop_price=position["stop_price"],
                        target_price=position["target_price"],
                        shares=position["shares"],
                        gross_entry_dollars=position["gross_entry_dollars"],
                        pnl_dollars=pnl_dollars,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason,
                        regime_pass=regime_pass,
                        momentum_pass=momentum_pass,
                        gap_pass=gap_pass,
                        gap_pct=round(gap_pct, 2),
                    )
                )

        trades.sort(key=lambda trade: trade.entry_date)
        pnl_pcts = sorted(trade.pnl_pct for trade in trades)
        median = pnl_pcts[len(pnl_pcts) // 2] if pnl_pcts else 0.0
        wins = sum(1 for trade in trades if trade.pnl_dollars > 0)
        total_pnl = round(sum(trade.pnl_dollars for trade in trades), 2)
        total_gross = round(sum(trade.gross_entry_dollars for trade in trades), 2)
        summary = BacktestSummary(
            start_date=start_date.isoformat(),
            entry_cutoff_date=entry_cutoff.isoformat(),
            end_date=end_date.isoformat(),
            total_events_checked=total_events_checked,
            total_entries=len(trades),
            wins=wins,
            losses=max(len(trades) - wins, 0),
            win_rate_pct=round((wins / len(trades)) * 100, 2) if trades else 0.0,
            total_pnl_dollars=total_pnl,
            avg_trade_pnl_pct=round(sum(trade.pnl_pct for trade in trades) / len(trades), 2) if trades else 0.0,
            median_trade_pnl_pct=round(median, 2),
            total_gross_deployed=total_gross,
            total_return_on_gross_pct=round((total_pnl / total_gross) * 100, 2) if total_gross else 0.0,
        )
        return summary, trades
    finally:
        client.close()


def _print_report(summary: BacktestSummary, trades: list[BacktestTrade]) -> None:
    print(json.dumps(asdict(summary), indent=2))
    print()
    for trade in trades:
        print(
            f"{trade.entry_date} {trade.symbol:5} "
            f"earnings={trade.earnings_date} surprise={trade.surprise_pct:>6.2f}% "
            f"entry={trade.entry_price:>8.2f} exit={trade.exit_price:>8.2f} "
            f"pnl={trade.pnl_dollars:>9.2f} ({trade.pnl_pct:>6.2f}%) "
            f"reason={trade.exit_reason}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a PEAD proxy backtest from FMP historical earnings and prices.")
    parser.add_argument("--months-back", type=int, default=4, help="Total backtest window counted back from --end-date.")
    parser.add_argument("--entry-window-days", type=int, default=31, help="Only open new positions during the first N days of the backtest window.")
    parser.add_argument("--portfolio-size", type=float, default=float(os.getenv("PORTFOLIO_SIZE", "10000")), help="Portfolio size for sizing/PnL calculations.")
    parser.add_argument("--max-hold-days", type=int, default=20, help="Maximum holding period in trading days.")
    parser.add_argument("--end-date", type=str, default=date.today().isoformat(), help="Backtest end date in YYYY-MM-DD format.")
    parser.add_argument("--symbols", type=str, default=",".join(WATCHLIST), help="Comma-separated ticker list.")
    args = parser.parse_args()

    end_date = _iso_to_date(args.end_date)
    symbols = [value.strip().upper() for value in args.symbols.split(",") if value.strip()]
    summary, trades = run_proxy_backtest(
        end_date=end_date,
        months_back=args.months_back,
        entry_window_days=args.entry_window_days,
        portfolio_size=args.portfolio_size,
        max_hold_days=args.max_hold_days,
        symbols=symbols,
    )
    _print_report(summary, trades)


if __name__ == "__main__":
    main()
