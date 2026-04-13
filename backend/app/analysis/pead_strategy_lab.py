from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date

from .pead_proxy_backtest import (
    WATCHLIST,
    FMPHistoricalClient,
    _calculate_position,
    _find_next_trading_day_index,
    _iso_to_date,
    _moving_average,
    _prepare_bars,
    _revenue_surprise_pct,
    _simulate_long_exit,
    _surprise_pct,
    subtract_months,
)
from ..config import get_settings


@dataclass(frozen=True)
class StrategyVariant:
    name: str
    min_surprise_pct: float
    stop_loss_pct: float
    reward_risk_ratio: float
    max_gap_pct: float
    max_hold_days: int
    require_momentum: bool = True
    require_regime: bool = True
    min_revenue_surprise_pct: float = 0.0
    require_revenue_beat: bool = False
    require_positive_day1_close: bool = False
    require_close_above_prev_close: bool = False
    top_n_per_month: int = 0
    score_weight_revenue: float = 0.5


@dataclass
class VariantMonthResult:
    month_end: str
    entries: int
    total_pnl_dollars: float
    avg_trade_pnl_pct: float
    win_rate_pct: float


@dataclass
class VariantSummary:
    name: str
    profitable_months: int
    losing_months: int
    flat_months: int
    total_months: int
    total_entries: int
    total_pnl_dollars: float
    avg_monthly_pnl_dollars: float
    avg_trade_pnl_pct: float
    win_rate_pct: float
    months: list[VariantMonthResult]


DEFAULT_VARIANTS = [
    StrategyVariant("baseline_20d_5_10", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20),
    StrategyVariant("faster_10d_5_10", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10),
    StrategyVariant("faster_5d_5_10", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=5),
    StrategyVariant("higher_surprise_8pct", min_surprise_pct=8.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20),
    StrategyVariant("higher_surprise_10pct", min_surprise_pct=10.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20),
    StrategyVariant("tighter_stop_3_6", min_surprise_pct=5.0, stop_loss_pct=0.03, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20),
    StrategyVariant("wider_stop_7_14", min_surprise_pct=5.0, stop_loss_pct=0.07, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20),
    StrategyVariant("tighter_gap_4pct", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=4.0, max_hold_days=20),
    StrategyVariant("no_momentum_filter", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=20, require_momentum=False),
    StrategyVariant("revenue_beat_top1_10d", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10, require_momentum=False, require_revenue_beat=True, top_n_per_month=1),
    StrategyVariant("revenue_beat_day1_top1", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10, require_momentum=False, require_revenue_beat=True, require_positive_day1_close=True, require_close_above_prev_close=True, top_n_per_month=1),
    StrategyVariant("high_eps_rev_top1", min_surprise_pct=10.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10, require_momentum=False, min_revenue_surprise_pct=3.0, require_revenue_beat=True, top_n_per_month=1),
    StrategyVariant("high_eps_rev_top2", min_surprise_pct=8.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10, require_momentum=False, min_revenue_surprise_pct=2.0, require_revenue_beat=True, top_n_per_month=2),
    StrategyVariant("day1_confirm_top1", min_surprise_pct=5.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=5, require_momentum=False, require_positive_day1_close=True, require_close_above_prev_close=True, top_n_per_month=1),
    # Best broader-search candidate so far: fewer, higher-quality events with revenue confirmation.
    StrategyVariant("quality_eps10_rev1_top2_10d", min_surprise_pct=10.0, stop_loss_pct=0.05, reward_risk_ratio=2.0, max_gap_pct=8.0, max_hold_days=10, require_momentum=False, min_revenue_surprise_pct=1.0, require_revenue_beat=True, top_n_per_month=2),
]


@dataclass
class CandidateTrade:
    pnl_dollars: float
    pnl_pct: float
    score: float


def _month_ends(start_month_end: date, end_month_end: date) -> list[date]:
    months: list[date] = []
    current = start_month_end
    while current <= end_month_end:
        months.append(current)
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        current = date(year, month, current.day)
    return months


def _load_cached_history(symbols: list[str], start_date: date, end_date: date) -> tuple[dict, dict]:
    settings = get_settings()
    if not settings.fmp_api_key:
        raise RuntimeError("FMP_API_KEY is required")
    preload_start = start_date.fromordinal(start_date.toordinal() - 320)
    client = FMPHistoricalClient(settings.fmp_api_key)
    try:
        price_cache = {}
        earnings_cache = {}
        for symbol in [*symbols, "SPY"]:
            price_cache[symbol] = _prepare_bars(client.prices(symbol, preload_start, end_date))
        for symbol in symbols:
            earnings_cache[symbol] = client.earnings(symbol)
        return price_cache, earnings_cache
    finally:
        client.close()


def evaluate_variant(
    variant: StrategyVariant,
    *,
    monthly_end_dates: list[date],
    months_back: int,
    entry_window_days: int,
    portfolio_size: float,
    symbols: list[str] | None = None,
    price_cache: dict | None = None,
    earnings_cache: dict | None = None,
) -> VariantSummary:
    watchlist = symbols or WATCHLIST
    if price_cache is None or earnings_cache is None:
        overall_start = subtract_months(monthly_end_dates[0], months_back)
        overall_end = monthly_end_dates[-1]
        price_cache, earnings_cache = _load_cached_history(watchlist, overall_start, overall_end)
    spy_bars, spy_by_date = price_cache["SPY"]

    month_results: list[VariantMonthResult] = []
    all_trade_pcts: list[float] = []
    total_entries = 0
    total_pnl = 0.0
    total_wins = 0

    for month_end in monthly_end_dates:
        start_date = subtract_months(month_end, months_back)
        entry_cutoff = start_date.fromordinal(start_date.toordinal() + entry_window_days)
        candidates: list[CandidateTrade] = []

        for symbol in watchlist:
            bars, _ = price_cache[symbol]
            for event in earnings_cache[symbol]:
                event_date_raw = event.get("date")
                if not event_date_raw:
                    continue
                earnings_date = _iso_to_date(str(event_date_raw))
                if not (start_date <= earnings_date < entry_cutoff):
                    continue
                surprise = _surprise_pct(event)
                if surprise is None or surprise < variant.min_surprise_pct:
                    continue
                revenue_surprise = _revenue_surprise_pct(event)
                if variant.require_revenue_beat and (revenue_surprise is None or revenue_surprise <= 0):
                    continue
                if revenue_surprise is not None and revenue_surprise < variant.min_revenue_surprise_pct:
                    continue

                entry_idx = _find_next_trading_day_index(bars, earnings_date)
                if entry_idx is None or entry_idx == 0:
                    continue
                entry_bar = bars[entry_idx]
                prev_bar = bars[entry_idx - 1]
                entry_day = entry_bar["date"]
                if entry_day > month_end:
                    continue
                day1_close_up = entry_bar["close"] > entry_bar["open"]
                close_above_prev = entry_bar["close"] > prev_bar["close"]
                if variant.require_positive_day1_close and not day1_close_up:
                    continue
                if variant.require_close_above_prev_close and not close_above_prev:
                    continue

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
                gap_pass = abs(gap_pct) <= variant.max_gap_pct

                if variant.require_regime and not regime_pass:
                    continue
                if variant.require_momentum and not momentum_pass:
                    continue
                if not gap_pass:
                    continue

                position = _calculate_position(
                    entry_bar["open"],
                    portfolio_size,
                    get_settings().risk_per_trade,
                    variant.stop_loss_pct,
                    variant.reward_risk_ratio,
                )
                exit_idx, exit_price, _ = _simulate_long_exit(
                    bars,
                    entry_idx,
                    position["stop_price"],
                    position["target_price"],
                    variant.max_hold_days,
                )
                pnl_dollars = round((exit_price - position["entry_price"]) * position["shares"], 2)
                pnl_pct = round(((exit_price - position["entry_price"]) / position["entry_price"]) * 100, 2)
                score = surprise + ((revenue_surprise or 0.0) * variant.score_weight_revenue)
                if day1_close_up:
                    score += 1.0
                if close_above_prev:
                    score += 1.0
                candidates.append(
                    CandidateTrade(
                        pnl_dollars=pnl_dollars,
                        pnl_pct=pnl_pct,
                        score=score,
                    )
                )

        selected = sorted(candidates, key=lambda item: item.score, reverse=True)
        if variant.top_n_per_month > 0:
            selected = selected[: variant.top_n_per_month]
        month_trade_pcts = [trade.pnl_pct for trade in selected]
        month_pnl = round(sum(trade.pnl_dollars for trade in selected), 2)
        month_entries = len(selected)
        month_wins = sum(1 for trade in selected if trade.pnl_dollars > 0)

        total_entries += month_entries
        total_pnl += month_pnl
        total_wins += month_wins
        all_trade_pcts.extend(month_trade_pcts)
        month_results.append(
            VariantMonthResult(
                month_end=month_end.isoformat(),
                entries=month_entries,
                total_pnl_dollars=round(month_pnl, 2),
                avg_trade_pnl_pct=round(sum(month_trade_pcts) / len(month_trade_pcts), 2) if month_trade_pcts else 0.0,
                win_rate_pct=round((month_wins / month_entries) * 100, 2) if month_entries else 0.0,
            )
        )

    profitable = sum(1 for result in month_results if result.total_pnl_dollars > 0)
    losing = sum(1 for result in month_results if result.total_pnl_dollars < 0)
    flat = len(month_results) - profitable - losing
    return VariantSummary(
        name=variant.name,
        profitable_months=profitable,
        losing_months=losing,
        flat_months=flat,
        total_months=len(month_results),
        total_entries=total_entries,
        total_pnl_dollars=round(total_pnl, 2),
        avg_monthly_pnl_dollars=round(total_pnl / len(month_results), 2) if month_results else 0.0,
        avg_trade_pnl_pct=round(sum(all_trade_pcts) / len(all_trade_pcts), 2) if all_trade_pcts else 0.0,
        win_rate_pct=round((total_wins / total_entries) * 100, 2) if total_entries else 0.0,
        months=month_results,
    )


def run_strategy_lab(
    *,
    start_month_end: date,
    end_month_end: date,
    months_back: int,
    entry_window_days: int,
    portfolio_size: float,
    variants: list[StrategyVariant] | None = None,
    symbols: list[str] | None = None,
) -> list[VariantSummary]:
    monthly_end_dates = _month_ends(start_month_end, end_month_end)
    watchlist = symbols or WATCHLIST
    overall_start = subtract_months(monthly_end_dates[0], months_back)
    overall_end = monthly_end_dates[-1]
    price_cache, earnings_cache = _load_cached_history(watchlist, overall_start, overall_end)
    return [
        evaluate_variant(
            variant,
            monthly_end_dates=monthly_end_dates,
            months_back=months_back,
            entry_window_days=entry_window_days,
            portfolio_size=portfolio_size,
            symbols=watchlist,
            price_cache=price_cache,
            earnings_cache=earnings_cache,
        )
        for variant in (variants or DEFAULT_VARIANTS)
    ]


def _print_report(results: list[VariantSummary]) -> None:
    ranked = sorted(results, key=lambda item: (item.total_pnl_dollars, item.profitable_months, -item.losing_months), reverse=True)
    print(json.dumps([asdict(result) for result in ranked], indent=2))
    print()
    print("Leaderboard")
    for result in ranked:
        print(
            f"{result.name:20} pnl={result.total_pnl_dollars:+8.2f} "
            f"profitable={result.profitable_months:2d} losing={result.losing_months:2d} "
            f"entries={result.total_entries:2d} win_rate={result.win_rate_pct:5.1f}% "
            f"avg_trade={result.avg_trade_pnl_pct:+5.2f}%"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare PEAD proxy strategy variants over a monthly sweep.")
    parser.add_argument("--start-month-end", type=str, default="2024-05-13")
    parser.add_argument("--end-month-end", type=str, default=date.today().isoformat())
    parser.add_argument("--months-back", type=int, default=4)
    parser.add_argument("--entry-window-days", type=int, default=31)
    parser.add_argument("--portfolio-size", type=float, default=10000.0)
    parser.add_argument("--symbols", type=str, default=",".join(WATCHLIST))
    args = parser.parse_args()

    results = run_strategy_lab(
        start_month_end=_iso_to_date(args.start_month_end),
        end_month_end=_iso_to_date(args.end_month_end),
        months_back=args.months_back,
        entry_window_days=args.entry_window_days,
        portfolio_size=args.portfolio_size,
        symbols=[value.strip().upper() for value in args.symbols.split(",") if value.strip()],
    )
    _print_report(results)


if __name__ == "__main__":
    main()
