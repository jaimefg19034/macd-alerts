#!/usr/bin/env python3
"""Development-only ATR grid selection followed by untouched chronological OOS tests."""
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
from atr_exits import calculate_atr, atr_levels
from backtest import BACKTEST_LOOKBACK_DAYS, crossover_events, load_snapshot_bars, summarize
from portfolio_sim import USD_EQUITY_SYMBOLS, simulate_portfolio
from risk_management import check_exit
from strategy_filters import filter_events

STOP_GRID = (1.0, 1.5, 2.0, 2.5)
TARGET_GRID = (2.0, 3.0, 4.0, 5.0)
DEVELOPMENT_COST_PCT = 0.20
MIN_DEVELOPMENT_TRADES = 100


def split_indices(n: int, folds: int = 4) -> tuple[int, list[tuple[int, int]]]:
    if n < 40:
        raise ValueError("Not enough bars")
    split = int(n * 0.50)
    edges = [split + round((n - split) * i / folds) for i in range(folds + 1)]
    return split, [(edges[i], edges[i + 1]) for i in range(folds)]


def simulate_atr(symbol: str, bars: list[dict], events: list[tuple[int, str]],
                 cost_pct: float, stop_multiple: float, target_multiple: float) -> list[dict]:
    """Same conservative fill convention as backtest.simulate_trades, with variable ATR multiples."""
    if cost_pct < 0 or stop_multiple <= 0 or target_multiple <= 0:
        raise ValueError("Invalid cost or ATR multiples")
    atrs = calculate_atr(bars, 14)
    event_map = {i + 1: side for i, side in events if i + 1 < len(bars)}
    position = None
    trades = []

    def close(idx: int, price: float, reason: str) -> None:
        nonlocal position
        p = position
        if p is None:
            return
        entry = p["entry_price"]
        gross = ((price / entry - 1) * 100 if p["direction"] == "BUY"
                 else (entry / price - 1) * 100)
        trades.append({
            "trade_id": f"atr-research:{symbol}:{p['direction']}:{p['entry_timestamp']}",
            "symbol": symbol, "direction": p["direction"],
            "signal_timestamp_utc": macd_alerts.datetime.fromtimestamp(
                p["signal_timestamp"], tz=macd_alerts.timezone.utc).isoformat(),
            "entry_timestamp_utc": macd_alerts.datetime.fromtimestamp(
                p["entry_timestamp"], tz=macd_alerts.timezone.utc).isoformat(),
            "entry_price": f"{entry:.10f}",
            "exit_timestamp_utc": macd_alerts.datetime.fromtimestamp(
                int(bars[idx]["timestamp"]) + (3600 if reason == "END_OF_DATA" else 0),
                tz=macd_alerts.timezone.utc).isoformat(),
            "exit_price": f"{price:.10f}", "exit_reason": reason,
            "stop_price": f"{p['stop_price']:.10f}",
            "target_price": f"{p['target_price']:.10f}",
            "gross_return_pct": f"{gross:.6f}",
            "estimated_round_trip_cost_pct": f"{cost_pct:.6f}",
            "net_return_pct": f"{gross-cost_pct:.6f}",
            "bars_held": idx-p["entry_index"]+1,
        })
        position = None

    for idx in range(1, len(bars)):
        side = event_map.get(idx)
        op = float(bars[idx]["open"])
        if side:
            if position and position["direction"] != side:
                close(idx, op, "OPPOSITE_MACD_CROSS")
            if position is None:
                signal_atr = atrs[idx-1]
                if signal_atr is not None and signal_atr > 0:
                    stop, target = atr_levels(op, side, signal_atr, stop_multiple, target_multiple)
                    position = {
                        "direction": side, "entry_price": op,
                        "signal_timestamp": int(bars[idx-1]["timestamp"])+3600,
                        "entry_timestamp": int(bars[idx]["timestamp"]),
                        "entry_index": idx, "stop_price": stop, "target_price": target,
                    }
        if position and position["entry_index"] < idx:
            hit = check_exit(bars[idx], position["direction"],
                             position["stop_price"], position["target_price"])
            if hit:
                close(idx, hit[1], hit[0])
    if position:
        last = len(bars)-1
        close(last, float(bars[last]["close"]), "END_OF_DATA")
    return trades


def rank_candidate(trades: list[dict]) -> dict:
    stats = summarize(trades)
    pf = stats["profit_factor"]
    avg = stats["average_net_return_pct"]
    # Avoid selecting configurations with no losing trades or too few observations.
    valid = len(trades) >= MIN_DEVELOPMENT_TRADES and isinstance(pf, (int, float)) and math.isfinite(pf)
    return {**stats, "eligible": valid,
            "selection_score": round(math.log(max(float(pf), 1e-9)) + float(avg or 0) / 100, 8)
            if valid else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filter-mode", choices=("ema200", "ema_adx", "ema_adx_rsi"), default="ema_adx")
    parser.add_argument("--costs", nargs="*", type=float, default=[0.10, 0.20, 0.30])
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default=str(ROOT / "reports" / "atr_research" / "summary.json"))
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

    splits = {s: split_indices(len(b)) for s, b in data.items()}
    dev_candidates = []
    for stop in STOP_GRID:
        for target in TARGET_GRID:
            all_dev = []
            for symbol, bars in data.items():
                dev_end, _ = splits[symbol]
                prefix = bars[:dev_end]
                events = filter_events(prefix, crossover_events(prefix), args.filter_mode)
                events = [(i, side) for i, side in events if i < dev_end-1]
                all_dev.extend(simulate_atr(symbol, prefix, events, DEVELOPMENT_COST_PCT, stop, target))
            dev_candidates.append({
                "stop_atr": stop, "target_atr": target,
                **rank_candidate(all_dev),
            })
    eligible = [x for x in dev_candidates if x["eligible"]]
    fallback = not eligible
    if eligible:
        selected = max(eligible, key=lambda x: (x["selection_score"], x["profit_factor"],
                                                x["average_net_return_pct"]))
    else:
        selected = next(x for x in dev_candidates if x["stop_atr"] == 1.5 and x["target_atr"] == 3.0)

    output = {
        "method": "ATR grid selected using development half only; selected fixed configuration evaluated on four later OOS folds",
        "selection_cost_pct": DEVELOPMENT_COST_PCT,
        "filter_mode": args.filter_mode,
        "candidate_grid": {"stop_atr": list(STOP_GRID), "target_atr": list(TARGET_GRID)},
        "minimum_development_trades": MIN_DEVELOPMENT_TRADES,
        "development_candidates": dev_candidates,
        "selected_configuration": {"stop_atr": selected["stop_atr"], "target_atr": selected["target_atr"]},
        "used_default_fallback": fallback,
        "oos": {}, "errors": errors,
        "limitations": [
            "The development period is used for parameter selection and is not an independent performance estimate.",
            "The four OOS folds are not used to select or change parameters.",
            "The candidate grid and selection score are research choices and may still overfit the development sample.",
            "Costs are hypothetical round-trip scenarios, not verified broker quotes.",
            "Each fold is independently simulated and open positions are marked at its final close.",
            "Yahoo hourly history may be incomplete; short trades, financing and intrabar portfolio risk are simplified."
        ]
    }
    for cost in args.costs:
        pooled, fold_report = [], {}
        for fold_no in range(1, 5):
            fold_trades = []
            for symbol, bars in data.items():
                _, folds = splits[symbol]
                start, end = folds[fold_no-1]
                prefix = bars[:end]
                events = filter_events(prefix, crossover_events(prefix), args.filter_mode)
                events = [(i, side) for i, side in events if start <= i < end-1]
                trades = simulate_atr(symbol, prefix, events, cost,
                                      selected["stop_atr"], selected["target_atr"])
                for trade in trades:
                    trade["walk_forward_fold"] = fold_no
                fold_trades.extend(trades)
            pooled.extend(fold_trades)
            fold_report[str(fold_no)] = {
                "statistics": summarize(fold_trades),
                "portfolio": simulate_portfolio(fold_trades, bars_by_symbol=data),
            }
        output["oos"][f"cost_{cost:.2f}"] = {
            "statistics": summarize(pooled),
            "portfolio": simulate_portfolio(pooled, bars_by_symbol=data),
            "folds": fold_report,
        }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"selected": output["selected_configuration"], "fallback": fallback,
                      "oos": output["oos"], "errors": errors}, indent=2))
    return 1 if errors and not data else 0


if __name__ == "__main__":
    raise SystemExit(main())
