#!/usr/bin/env python3
"""Chronological out-of-sample walk-forward evaluation; no parameter fitting."""
from __future__ import annotations
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import macd_alerts
from backtest import BACKTEST_LOOKBACK_DAYS, crossover_events, simulate_trades, summarize
from portfolio_sim import USD_EQUITY_SYMBOLS, simulate_portfolio
from strategy_filters import filter_events

DEFAULT_COSTS = (0.10, 0.20, 0.30)


def split_walk_forward(n_bars: int, warmup_fraction: float = 0.50,
                       n_folds: int = 4) -> list[tuple[int, int]]:
    if n_bars < 20 or not 0 < warmup_fraction < 1 or n_folds < 1:
        raise ValueError("Invalid walk-forward split parameters")
    first_test = int(n_bars * warmup_fraction)
    if n_bars - first_test < n_folds:
        raise ValueError("Not enough bars for requested folds")
    boundaries = [first_test + round((n_bars - first_test) * i / n_folds)
                  for i in range(n_folds + 1)]
    return [(boundaries[i], boundaries[i + 1]) for i in range(n_folds)]


def evaluate_symbol(symbol: str, bars: list[dict], filter_mode: str,
                    cost_pct: float, n_folds: int = 4) -> tuple[list[dict], list[dict]]:
    folds = split_walk_forward(len(bars), n_folds=n_folds)
    fold_summaries = []
    all_trades = []
    for fold_number, (start, end) in enumerate(folds, start=1):
        prefix = bars[:end]
        raw_events = crossover_events(prefix)
        accepted = filter_events(prefix, raw_events, filter_mode)
        test_events = [(idx, side) for idx, side in accepted if start <= idx < end - 1]
        trades = simulate_trades(symbol, prefix, test_events, cost_pct, "atr")
        for trade in trades:
            trade["walk_forward_fold"] = fold_number
        all_trades.extend(trades)
        fold_summaries.append({
            "fold": fold_number,
            "test_start_utc": macd_alerts.datetime.fromtimestamp(
                bars[start]["timestamp"], tz=macd_alerts.timezone.utc
            ).isoformat(),
            "test_end_utc": macd_alerts.datetime.fromtimestamp(
                bars[end - 1]["timestamp"], tz=macd_alerts.timezone.utc
            ).isoformat(),
            "test_bars": end - start,
            "signals_accepted": len(test_events),
            **summarize(trades),
        })
    return fold_summaries, all_trades



def buy_hold_benchmark(data: dict[str, list[dict]]) -> dict:
    """Equal-weight buy-and-hold benchmark over each symbol's OOS half."""
    per_symbol = {}
    returns = []
    for symbol, bars in data.items():
        if symbol not in USD_EQUITY_SYMBOLS or len(bars) < 2:
            continue
        start = int(len(bars) * 0.50)
        entry = float(bars[start]["open"])
        exit_price = float(bars[-1]["close"])
        if entry <= 0:
            continue
        value = (exit_price / entry - 1.0) * 100.0
        per_symbol[symbol] = round(value, 4)
        returns.append(value)
    average = sum(returns) / len(returns) if returns else None
    return {
        "method": "equal-weight buy-and-hold of USD US equities from OOS start to final close",
        "symbols": per_symbol,
        "equal_weight_return_pct": None if average is None else round(average, 4),
        "median_symbol_return_pct": None if not returns else round(statistics.median(returns), 4),
        "mean_excluding_best_symbol_pct": (None if len(returns) < 2 else round(sum(sorted(returns)[:-1]) / (len(returns) - 1), 4)),
        "initial_10000_final_value": None if average is None else round(10000 * (1 + average / 100), 2),
        "note": "Excludes dividends, benchmark costs and currency effects; static equal-weight terminal comparison, not a daily rebalanced curve."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*", default=list(macd_alerts.TICKERS))
    parser.add_argument("--filter-mode", choices=("ema200", "ema_adx", "ema_adx_rsi"),
                        default="ema_adx_rsi")
    parser.add_argument("--costs", nargs="*", type=float, default=list(DEFAULT_COSTS))
    parser.add_argument("--output", default=str(ROOT / "reports" / "walk_forward" / "summary.json"))
    args = parser.parse_args()

    if not args.costs or any(cost < 0 for cost in args.costs):
        parser.error("Costs must be non-negative and include at least one value")

    data, errors = {}, {}
    for symbol in args.symbols:
        try:
            bars = macd_alerts.get_hourly_bars(symbol, lookback_days=BACKTEST_LOOKBACK_DAYS)
            if len(bars) < 300:
                raise RuntimeError(f"Only {len(bars)} hourly bars; need at least 300")
            data[symbol] = bars
            print(f"{symbol}: downloaded {len(bars)} completed 1H bars")
        except Exception as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR {symbol}: {errors[symbol]}", file=sys.stderr)
        time.sleep(0.35)

    output = {
        "method": "first 50% warm-up/development; next 50% split into four chronological out-of-sample folds",
        "lookback_days_requested": BACKTEST_LOOKBACK_DAYS,
        "filter_mode": args.filter_mode,
        "exit_mode": "ATR(14), stop 1.5x ATR / target 3x ATR",
        "cost_scenarios_round_trip_pct": args.costs,
        "symbols": {},
        "scenarios": {},
        "buy_and_hold_benchmark": buy_hold_benchmark(data),
        "errors": errors,
        "limitations": [
            "No parameter optimization is performed; this is chronological out-of-sample evaluation of fixed rules.",
            "Each fold is simulated independently and positions are closed at the fold boundary.",
            "Yahoo Finance hourly history may be shorter than requested, incomplete or rate-limited.",
            "Costs are scenarios, not verified broker execution costs.",
            "Portfolio aggregation includes only USD-denominated US equities; FX and SAN.MC are excluded.",
            "Portfolio drawdown is realized only and excludes mark-to-market drawdown.",
            "Short trades, borrow, financing, margin and gap risk remain simplified."
        ]
    }

    for cost in args.costs:
        combined, fold_totals = [], []
        for symbol, bars in data.items():
            folds, trades = evaluate_symbol(symbol, bars, args.filter_mode, cost)
            combined.extend(trades)
            output["symbols"].setdefault(symbol, {})[f"cost_{cost:.2f}"] = {
                "bars": len(bars), "folds": folds, **summarize(trades)
            }
            for item in folds:
                fold_totals.append(item)
        by_fold = {}
        for fold_number in range(1, 5):
            fold_trades = [trade for trade in combined
                           if trade.get("walk_forward_fold") == fold_number]
            by_fold[str(fold_number)] = {
                "pooled_oos_statistics": summarize(fold_trades),
                "portfolio_simulation": simulate_portfolio(fold_trades),
            }
        output["scenarios"][f"cost_{cost:.2f}"] = {
            "pooled_oos_statistics": summarize(combined),
            "portfolio_simulation": simulate_portfolio(combined),
            "out_of_sample_folds": by_fold,
            "trade_count": len(combined),
        }

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["scenarios"], indent=2, ensure_ascii=False))
    print(f"Walk-forward report: {target}")
    return 1 if errors and not data else 0


if __name__ == "__main__":
    raise SystemExit(main())
