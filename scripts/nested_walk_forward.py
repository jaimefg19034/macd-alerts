#!/usr/bin/env python3
"""Nested walk-forward ATR research: fit only on the past, test on the next fold."""
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
from atr_research import STOP_GRID, TARGET_GRID, simulate_atr, split_indices
from backtest import crossover_events, load_snapshot_bars, summarize
from portfolio_sim import simulate_portfolio
from strategy_filters import filter_events

FILTER_MODE = "ema_adx"
SELECTION_COST = 0.20
MIN_TRAIN_TRADES = 60
BASELINE = (1.5, 5.0)


def choose_parameters(training_trades: list[dict]) -> tuple[float, float, dict]:
    """Choose one fixed pair using training trades only."""
    candidates = []
    for stop in STOP_GRID:
        for target in TARGET_GRID:
            trades = [t for t in training_trades if t["stop_atr"] == stop and t["target_atr"] == target]
            stats = summarize(trades)
            pf, avg = stats["profit_factor"], stats["average_net_return_pct"]
            eligible = len(trades) >= MIN_TRAIN_TRADES and isinstance(pf, (int, float)) and math.isfinite(pf)
            score = math.log(max(float(pf), 1e-9)) + float(avg or 0) / 100 if eligible else None
            candidates.append({"stop_atr": stop, "target_atr": target, **stats,
                               "eligible": eligible, "score": score})
    eligible = [c for c in candidates if c["eligible"]]
    if not eligible:
        return BASELINE[0], BASELINE[1], {"fallback": True, "candidates": candidates}
    best = max(eligible, key=lambda c: (c["score"], c["profit_factor"], c["average_net_return_pct"]))
    return best["stop_atr"], best["target_atr"], {"fallback": False, "selected": best, "candidates": candidates}


def events_in_range(bars: list[dict], start: int, end: int) -> list[tuple[int, str]]:
    events = filter_events(bars, crossover_events(bars), FILTER_MODE)
    return [(i, side) for i, side in events if start <= i < end - 1]


def collect_training(data: dict[str, list[dict]], start_by_symbol: dict[str, int]) -> list[dict]:
    trades = []
    for symbol, bars in data.items():
        start = start_by_symbol[symbol]
        prefix = bars[:start]
        events = events_in_range(prefix, 0, len(prefix))
        for stop in STOP_GRID:
            for target in TARGET_GRID:
                rows = simulate_atr(symbol, prefix, events, SELECTION_COST, stop, target)
                for row in rows:
                    row["stop_atr"] = stop
                    row["target_atr"] = target
                trades.extend(rows)
    return trades


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--costs", nargs="*", type=float, default=[0.10, 0.20, 0.30])
    parser.add_argument("--output", default=str(ROOT / "reports" / "nested_walk_forward" / "summary.json"))
    args = parser.parse_args()
    if not args.costs or any(c < 0 for c in args.costs):
        parser.error("Costs must be non-negative and include at least one value")

    data, errors = {}, {}
    for symbol in macd_alerts.TICKERS:
        try:
            bars = load_snapshot_bars(args.data_dir, symbol)
            if len(bars) < 300:
                raise ValueError("Fewer than 300 hourly bars")
            data[symbol] = bars
        except Exception as exc:
            errors[symbol] = f"{type(exc).__name__}: {exc}"
        time.sleep(0.1)
    if not data:
        raise RuntimeError("No usable symbols in snapshot")

    split_map = {s: split_indices(len(bars))[1] for s, bars in data.items()}
    output = {
        "method": "Four chronological OOS folds. For each fold, ATR stop/target are selected using only the bars strictly before that fold; the selected pair and fixed 1.5/5.0 baseline are then tested on the same next-fold data.",
        "filter": FILTER_MODE, "selection_cost_pct": SELECTION_COST,
        "candidate_grid": {"stop_atr": list(STOP_GRID), "target_atr": list(TARGET_GRID)},
        "minimum_training_trades": MIN_TRAIN_TRADES,
        "baseline": {"stop_atr": BASELINE[0], "target_atr": BASELINE[1]},
        "cost_scenarios": {}, "data_errors": errors,
        "limitations": [
            "This is a research simulation, not a live-trading recommendation.",
            "The parameter grid and selection score can still overfit each training window.",
            "Each symbol has its own timestamp coverage; portfolio results aggregate available bars.",
            "Costs are hypothetical round-trip assumptions; fills, gaps, borrow and financing are simplified.",
            "The baseline is the historical +33.77% configuration, but this new nested evaluation uses a new common snapshot and is not directly comparable to that historical headline."
        ]
    }

    fold_details = {}
    for fold_no in range(1, 5):
        starts = {s: split_map[s][fold_no - 1][0] for s in data}
        ends = {s: split_map[s][fold_no - 1][1] for s in data}
        training = collect_training(data, starts)
        stop, target, selection = choose_parameters(training)
        fold_details[str(fold_no)] = {
            "selected": {"stop_atr": stop, "target_atr": target},
            "training_selection": selection,
            "test_periods": {}
        }
        for cost in args.costs:
            baseline_trades, adaptive_trades = [], []
            for symbol, bars in data.items():
                start, end = split_map[symbol][fold_no - 1]
                prefix = bars[:end]
                test_events = events_in_range(prefix, start, end)
                for label, pair, bucket in (
                    ("baseline", BASELINE, baseline_trades),
                    ("nested_selected", (stop, target), adaptive_trades),
                ):
                    rows = simulate_atr(symbol, prefix, test_events, cost, pair[0], pair[1])
                    for row in rows:
                        row["walk_forward_fold"] = fold_no
                        bucket.append(row)
            fold_details[str(fold_no)]["test_periods"][f"cost_{cost:.2f}"] = {
                "baseline": {"statistics": summarize(baseline_trades),
                             "portfolio": simulate_portfolio(baseline_trades, bars_by_symbol=data)},
                "nested_selected": {"statistics": summarize(adaptive_trades),
                                    "portfolio": simulate_portfolio(adaptive_trades, bars_by_symbol=data)}
            }

    for cost in args.costs:
        baseline_all, adaptive_all = [], []
        by_fold = {}
        for fold_no in range(1, 5):
            section = fold_details[str(fold_no)]["test_periods"][f"cost_{cost:.2f}"]
            # Re-run the deterministic fold simulation to retain complete trade ledgers for pooled portfolio stats.
            starts = {s: split_map[s][fold_no - 1][0] for s in data}
            ends = {s: split_map[s][fold_no - 1][1] for s in data}
            stop = fold_details[str(fold_no)]["selected"]["stop_atr"]
            target = fold_details[str(fold_no)]["selected"]["target_atr"]
            btr, atr = [], []
            for symbol, bars in data.items():
                start, end = split_map[symbol][fold_no - 1]
                prefix = bars[:end]
                events = events_in_range(prefix, start, end)
                btr.extend(simulate_atr(symbol, prefix, events, cost, *BASELINE))
                atr.extend(simulate_atr(symbol, prefix, events, cost, stop, target))
            baseline_all.extend(btr)
            adaptive_all.extend(atr)
            by_fold[str(fold_no)] = {
                "baseline_return_pct": section["baseline"]["portfolio"]["mtm_return_pct"],
                "nested_selected_return_pct": section["nested_selected"]["portfolio"]["mtm_return_pct"]
            }
        output["cost_scenarios"][f"cost_{cost:.2f}"] = {
            "baseline": {"statistics": summarize(baseline_all),
                         "portfolio": simulate_portfolio(baseline_all, bars_by_symbol=data)},
            "nested_selected": {"statistics": summarize(adaptive_all),
                                "portfolio": simulate_portfolio(adaptive_all, bars_by_symbol=data)},
            "fold_returns": by_fold
        }
    output["folds"] = fold_details
    target_path = Path(args.output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for cost, result in output["cost_scenarios"].items():
        print(cost, json.dumps({
            "baseline": result["baseline"]["portfolio"],
            "nested_selected": result["nested_selected"]["portfolio"],
            "fold_returns": result["fold_returns"]
        }))
    print(f"Report: {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
