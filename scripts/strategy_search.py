#!/usr/bin/env python3
"""Search filter/ATR variants on development data; compare one frozen winner to the original on OOS."""
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
from atr_research import simulate_atr, split_indices, rank_candidate
from backtest import crossover_events, load_snapshot_bars, summarize
from portfolio_sim import simulate_portfolio
from strategy_filters import filter_events

FILTERS = ("ema200", "ema_adx", "ema_adx_rsi")
STOPS = (1.0, 1.5, 2.0, 2.5)
TARGETS = (2.0, 3.0, 4.0, 5.0)
BASELINE = {"filter_mode": "ema_adx", "stop_atr": 1.5, "target_atr": 5.0}
DEV_COST = 0.20


def events_for(bars: list[dict], mode: str, start: int, end: int) -> list[tuple[int, str]]:
    events = filter_events(bars, crossover_events(bars), mode)
    return [(i, side) for i, side in events if start <= i < end - 1]


def run_dev(data: dict[str, list[dict]], mode: str, stop: float, target: float) -> list[dict]:
    trades = []
    for symbol, bars in data.items():
        dev_end, _ = split_indices(len(bars))
        prefix = bars[:dev_end]
        events = events_for(prefix, mode, 0, dev_end)
        trades.extend(simulate_atr(symbol, prefix, events, DEV_COST, stop, target))
    return trades


def evaluate_oos(data: dict[str, list[dict]], mode: str, stop: float,
                 target: float, costs: list[float]) -> dict:
    result = {}
    for cost in costs:
        pooled = []
        fold_reports = {}
        for fold_no in range(1, 5):
            fold_trades = []
            for symbol, bars in data.items():
                _, folds = split_indices(len(bars))
                start, end = folds[fold_no - 1]
                prefix = bars[:end]
                events = events_for(prefix, mode, start, end)
                trades = simulate_atr(symbol, prefix, events, cost, stop, target)
                for trade in trades:
                    trade["walk_forward_fold"] = fold_no
                fold_trades.extend(trades)
            pooled.extend(fold_trades)
            fold_reports[str(fold_no)] = {
                "statistics": summarize(fold_trades),
                "portfolio": simulate_portfolio(fold_trades, bars_by_symbol=data),
            }
        result[f"cost_{cost:.2f}"] = {
            "statistics": summarize(pooled),
            "portfolio": simulate_portfolio(pooled, bars_by_symbol=data),
            "folds": fold_reports,
        }
    return result


def is_strict_improvement(candidate: dict, baseline: dict) -> tuple[bool, list[str]]:
    reasons = []
    for cost in ("cost_0.10", "cost_0.20"):
        c = candidate[cost]["portfolio"]["mtm_return_pct"]
        b = baseline[cost]["portfolio"]["mtm_return_pct"]
        if c <= b:
            reasons.append(f"{cost}: candidato {c:.4f}% no supera baseline {b:.4f}%")
    cdd = candidate["cost_0.20"]["portfolio"]["max_mtm_drawdown_pct"]
    bdd = baseline["cost_0.20"]["portfolio"]["max_mtm_drawdown_pct"]
    if cdd > bdd + 2.0:
        reasons.append(f"drawdown al 0,20% empeora más de 2 puntos: {cdd:.4f}% vs {bdd:.4f}%")
    return not reasons, reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--costs", nargs="*", type=float, default=[0.10, 0.20, 0.30])
    parser.add_argument("--output", default=str(ROOT / "reports" / "strategy_search" / "summary.json"))
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
    if len(data) < 10:
        raise RuntimeError(f"Insufficient usable symbols ({len(data)}): {errors}")

    candidates = []
    for mode in FILTERS:
        for stop in STOPS:
            for target in TARGETS:
                dev_trades = run_dev(data, mode, stop, target)
                ranked = rank_candidate(dev_trades)
                candidates.append({
                    "filter_mode": mode, "stop_atr": stop, "target_atr": target,
                    **ranked,
                })
    eligible = [c for c in candidates if c["eligible"]]
    if not eligible:
        raise RuntimeError("No candidate met the minimum development sample requirement")
    winner = max(eligible, key=lambda c: (
        c["selection_score"], c["profit_factor"], c["average_net_return_pct"]
    ))
    winner_config = {k: winner[k] for k in ("filter_mode", "stop_atr", "target_atr")}

    baseline_oos = evaluate_oos(data, BASELINE["filter_mode"], BASELINE["stop_atr"], BASELINE["target_atr"], args.costs)
    winner_oos = evaluate_oos(data, winner_config["filter_mode"], winner_config["stop_atr"], winner_config["target_atr"], args.costs)
    accepted, rejection_reasons = is_strict_improvement(winner_oos, baseline_oos)

    output = {
        "method": "48 filter/ATR combinations ranked on first 50% development data only; one winner frozen and compared with fixed original configuration on the later 50% OOS block, four chronological folds.",
        "universe": sorted(data),
        "data_errors": errors,
        "development_cost_pct": DEV_COST,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "development_winner": {
            "configuration": winner_config,
            "statistics": {k: winner[k] for k in ("trades", "win_rate_pct", "average_net_return_pct", "profit_factor", "selection_score")},
        },
        "original_baseline_configuration": BASELINE,
        "baseline_oos": baseline_oos,
        "winner_oos": winner_oos,
        "acceptance_rule": "Candidate must beat original baseline MTM return at both 0.10% and 0.20% round-trip costs; drawdown at 0.20% may not worsen by more than 2 percentage points.",
        "accepted_for_further_validation": accepted,
        "rejection_reasons": rejection_reasons,
        "all_development_candidates": sorted(candidates, key=lambda c: c["selection_score"] if c["selection_score"] is not None else -math.inf, reverse=True),
        "limitations": [
            "All parameter and filter selection is confined to the first half; OOS is not used for selection.",
            "The original strategy and candidate are compared on the same newly downloaded immutable hourly snapshot.",
            "The development winner is selected from 48 combinations and may still be overfit to development data.",
            "OOS is a single historical holdout, not proof of future profitability; a candidate accepted here would still require forward paper trading.",
            "Costs are hypothetical round-trip assumptions; short availability, borrow, financing, gaps and intrabar portfolio drawdown are simplified.",
        ],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "development_winner": output["development_winner"],
        "baseline_oos": {k: v["portfolio"] for k, v in baseline_oos.items()},
        "winner_oos": {k: v["portfolio"] for k, v in winner_oos.items()},
        "accepted_for_further_validation": accepted,
        "rejection_reasons": rejection_reasons,
        "data_errors": errors,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
