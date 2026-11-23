#!/usr/bin/env python3
"""Select assets using development data only, then evaluate the frozen universe OOS."""
from __future__ import annotations
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import macd_alerts
from atr_research import simulate_atr, split_indices
from backtest import crossover_events, load_snapshot_bars, summarize
from portfolio_sim import USD_EQUITY_SYMBOLS, simulate_portfolio
from strategy_filters import filter_events

FILTER_MODE = "ema_adx"
STOP_ATR = 1.5
TARGET_ATR = 5.0
SELECTION_COST_PCT = 0.20
MIN_DEV_TRADES = 12
MIN_POSITIVE_DEV_FOLDS = 2
MAX_SELECTED_ASSETS = 10
MAX_DEVELOPMENT_DRAWDOWN_PCT = 20.0


def asset_is_eligible(stats: dict, positive_folds: int) -> bool:
    pf = stats.get("profit_factor")
    pf_ok = (isinstance(pf, (int, float)) and math.isfinite(pf) and pf >= 1.0) or pf == "INF"
    avg = stats.get("average_net_return_pct")
    return (stats.get("trades", 0) >= MIN_DEV_TRADES and pf_ok
            and isinstance(avg, (int, float)) and avg > 0
            and positive_folds >= MIN_POSITIVE_DEV_FOLDS)


def dev_asset_report(symbol: str, bars: list[dict], dev_end: int) -> dict:
    edges = [0, round(dev_end / 3), round(2 * dev_end / 3), dev_end]
    fold_stats = {}
    all_trades = []
    for fold_no in range(1, 4):
        start, end = edges[fold_no - 1], edges[fold_no]
        prefix = bars[:end]
        events = filter_events(prefix, crossover_events(prefix), FILTER_MODE)
        events = [(i, side) for i, side in events if start <= i < end - 1]
        trades = simulate_atr(symbol, prefix, events, SELECTION_COST_PCT, STOP_ATR, TARGET_ATR)
        for trade in trades:
            trade["development_fold"] = fold_no
        all_trades.extend(trades)
        fold_stats[str(fold_no)] = summarize(trades)
    stats = summarize(all_trades)
    positive_folds = sum(
        1 for item in fold_stats.values()
        if isinstance(item.get("average_net_return_pct"), (int, float))
        and item["average_net_return_pct"] > 0
    )
    return {
        "statistics": stats,
        "folds": fold_stats,
        "positive_folds": positive_folds,
        "eligible": asset_is_eligible(stats, positive_folds),
    }


def run_oos(data: dict[str, list[dict]], symbols: list[str], costs: list[float]) -> dict:
    pooled_by_cost = {}
    for cost in costs:
        all_trades = []
        folds_report = {}
        for fold_no in range(1, 5):
            fold_trades = []
            for symbol in symbols:
                bars = data[symbol]
                _, folds = split_indices(len(bars))
                start, end = folds[fold_no - 1]
                prefix = bars[:end]
                events = filter_events(prefix, crossover_events(prefix), FILTER_MODE)
                events = [(i, side) for i, side in events if start <= i < end - 1]
                trades = simulate_atr(symbol, prefix, events, cost, STOP_ATR, TARGET_ATR)
                for trade in trades:
                    trade["walk_forward_fold"] = fold_no
                fold_trades.extend(trades)
            all_trades.extend(fold_trades)
            folds_report[str(fold_no)] = {
                "statistics": summarize(fold_trades),
                "portfolio": simulate_portfolio(fold_trades, bars_by_symbol=data),
            }
        by_symbol = {
            symbol: summarize([t for t in all_trades if t["symbol"] == symbol])
            for symbol in symbols
        }
        pooled_by_cost[f"cost_{cost:.2f}"] = {
            "statistics": summarize(all_trades),
            "portfolio": simulate_portfolio(all_trades, bars_by_symbol=data),
            "by_symbol": by_symbol,
            "folds": folds_report,
        }
    return pooled_by_cost


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--costs", nargs="*", type=float, default=[0.10, 0.20, 0.30])
    parser.add_argument("--output", default=str(ROOT / "reports" / "asset_selection" / "summary.json"))
    args = parser.parse_args()
    data, errors = {}, {}
    for symbol in macd_alerts.TICKERS:
        try:
            bars = load_snapshot_bars(args.data_dir, symbol)
            if len(bars) < 300:
                raise ValueError(f"Only {len(bars)} bars")
            data[symbol] = bars
        except Exception as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"
        time.sleep(0.1)
    if not data:
        raise RuntimeError("No usable symbols in snapshot")

    development = {}
    selected, excluded = [], []
    for symbol, bars in data.items():
        dev_end, _ = split_indices(len(bars))
        report = dev_asset_report(symbol, bars, dev_end)
        development[symbol] = report
        (selected if report["eligible"] else excluded).append(symbol)

    # Keep all assets if the development screen would otherwise leave fewer than three.
    fallback = len(selected) < 3
    if fallback:
        selected = sorted(data)
    else:
        selected.sort()
    excluded = sorted(set(data) - set(selected))

    # Rank assets using development data only and test top-K portfolios.
    dev_trades_by_symbol = {}
    dev_bars_by_symbol = {}
    for symbol, bars in data.items():
        dev_end, _ = split_indices(len(bars))
        prefix = bars[:dev_end]
        dev_bars_by_symbol[symbol] = prefix
        events = filter_events(prefix, crossover_events(prefix), FILTER_MODE)
        events = [(i, side) for i, side in events if i < dev_end - 1]
        dev_trades_by_symbol[symbol] = simulate_atr(symbol, prefix, events, SELECTION_COST_PCT, STOP_ATR, TARGET_ATR)
    eligible_ranked = sorted([s for s in data if development[s]["eligible"]],
        key=lambda s: (development[s]["statistics"]["average_net_return_pct"],
                       development[s]["positive_folds"], development[s]["statistics"]["trades"]), reverse=True)
    candidate_portfolios = []
    for size in range(3, min(MAX_SELECTED_ASSETS, len(eligible_ranked)) + 1):
        symbols = sorted(eligible_ranked[:size])
        trades = [t for symbol in symbols for t in dev_trades_by_symbol[symbol]]
        sim = simulate_portfolio(trades, bars_by_symbol={s: dev_bars_by_symbol[s] for s in symbols})
        candidate_portfolios.append({"symbols": symbols, "development_mtm_return_pct": sim["mtm_return_pct"],
            "development_max_mtm_drawdown_pct": sim["max_mtm_drawdown_pct"],
            "development_trades": sim["closed_trades"], "development_profit_factor": summarize(trades)["profit_factor"]})
    if candidate_portfolios:
        safe = [x for x in candidate_portfolios if x["development_max_mtm_drawdown_pct"] <= MAX_DEVELOPMENT_DRAWDOWN_PCT]
        pool = safe or candidate_portfolios
        best_candidate = max(pool, key=lambda x: (x["development_mtm_return_pct"], -x["development_max_mtm_drawdown_pct"]))
        best_selected = best_candidate["symbols"]
    else:
        best_candidate, best_selected = None, sorted(data)
    output = {
        "method": "Per-asset universe selection using only the first 50% development block, split into three chronological subwindows; frozen selected universe tested on the later 50% OOS block.",
        "strategy": {"filter": FILTER_MODE, "stop_atr": STOP_ATR, "target_atr": TARGET_ATR},
        "selection": {
            "cost_pct": SELECTION_COST_PCT,
            "minimum_development_trades": MIN_DEV_TRADES,
            "minimum_positive_development_subfolds": MIN_POSITIVE_DEV_FOLDS,
            "selected_symbols": selected,
            "excluded_symbols": excluded,
            "fallback_keep_all_because_fewer_than_three_selected": fallback,
            "per_symbol_development": development,
        },
        "profit_prioritized_development_selection": {
            "ranking": "Assets ranked by average net trade return among those passing the development consistency screen; top-K chosen by highest development portfolio MTM return subject to 20% development drawdown ceiling.",
            "maximum_assets": MAX_SELECTED_ASSETS,
            "maximum_development_drawdown_pct": MAX_DEVELOPMENT_DRAWDOWN_PCT,
            "ranked_eligible_symbols": eligible_ranked,
            "candidate_portfolios": candidate_portfolios,
            "selected_symbols": best_selected,
            "selected_candidate": best_candidate,
        },
        "full_universe_oos": run_oos(data, sorted(data), args.costs),
        "consistency_selected_universe_oos": run_oos(data, selected, args.costs),
        "profit_prioritized_selected_universe_oos": run_oos(data, best_selected, args.costs),
        "data_errors": errors,
        "limitations": [
            "Asset eligibility is a heuristic based on one development block and may overfit; OOS results are evaluation only and do not alter selection.",
            "The strategy/filter/ATR settings are fixed research assumptions, not independently re-optimized in this experiment.",
            "Portfolio simulation includes USD equities only; FX and SAN.MC remain excluded from the USD portfolio for currency reasons.",
            "Costs are hypothetical round-trip scenarios; Yahoo hourly history can be incomplete.",
            "Hourly-close MTM omits intrabar portfolio drawdown, dividends, short borrow and financing.",
            "This research does not change Telegram alerts or automatic paper trading."
        ],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected": selected, "excluded": excluded, "fallback": fallback,
        "full_universe": {k: v["portfolio"]["mtm_return_pct"] for k, v in output["full_universe_oos"].items()},
        "selected_universe": {k: v["portfolio"]["mtm_return_pct"] for k, v in output["selected_universe_oos"].items()},
        "errors": errors,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
