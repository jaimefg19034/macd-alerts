#!/usr/bin/env python3
"""Independent MACD 1H historical backtester. Never sends orders or Telegram messages."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import macd_alerts  # noqa: E402

STRATEGY_ID = macd_alerts.STRATEGY_ID
STRATEGY_VERSION = macd_alerts.STRATEGY_VERSION
DATA_SOURCE = macd_alerts.DATA_SOURCE
DEFAULT_COST_PCT = 0.10


def iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def crossover_events(bars: list[dict]) -> list[tuple[int, str]]:
    closes = [float(bar["close"]) for bar in bars]
    macd, signal = macd_alerts.calculate_macd(closes)
    events = []
    for index in range(1, len(bars) - 1):
        if None in (macd[index - 1], signal[index - 1], macd[index], signal[index]):
            continue
        previous = macd[index - 1] - signal[index - 1]
        current = macd[index] - signal[index]
        if previous <= 0 and current > 0:
            events.append((index, "BUY"))
        elif previous >= 0 and current < 0:
            events.append((index, "SELL"))
    return events


def simulate_trades(symbol: str, bars: list[dict],
                    events: list[tuple[int, str]],
                    cost_pct: float = DEFAULT_COST_PCT,
                    risk_mode: str = "macd") -> list[dict]:
    """Simulate MACD-only or fixed SL/TP exits using completed OHLC bars.

    Entry/reversal fills occur at the next bar open. Stops/targets are checked
    only on bars after entry. If both are touched in one bar, stop wins.
    """
    from risk_management import check_exit, levels, risk_parameters

    if cost_pct < 0:
        raise ValueError("cost_pct no puede ser negativo")
    if risk_mode not in {"macd", "fixed"}:
        raise ValueError("risk_mode debe ser 'macd' o 'fixed'")
    event_by_execution = {index + 1: direction for index, direction in events
                          if index + 1 < len(bars)}
    trades: list[dict] = []
    position = None

    def close_position(exit_index: int, exit_price: float, reason: str) -> None:
        nonlocal position
        if position is None:
            return
        entry = position["entry_price"]
        direction = position["direction"]
        if entry <= 0 or exit_price <= 0:
            position = None
            return
        gross = ((exit_price / entry - 1.0) * 100.0 if direction == "BUY"
                 else (entry / exit_price - 1.0) * 100.0)
        trades.append({
            "trade_id": f"{STRATEGY_ID}:{symbol}:{position['direction']}:{position['entry_timestamp']}",
            "symbol": symbol,
            "direction": direction,
            "signal_timestamp_utc": iso_utc(position["signal_timestamp"]),
            "entry_timestamp_utc": iso_utc(position["entry_timestamp"]),
            "entry_price": f"{entry:.10f}",
            "exit_timestamp_utc": iso_utc(int(bars[exit_index]["timestamp"])),
            "exit_price": f"{exit_price:.10f}",
            "exit_reason": reason,
            "stop_price": "" if position.get("stop_price") is None else f"{position['stop_price']:.10f}",
            "target_price": "" if position.get("target_price") is None else f"{position['target_price']:.10f}",
            "gross_return_pct": f"{gross:.6f}",
            "estimated_round_trip_cost_pct": f"{cost_pct:.6f}",
            "net_return_pct": f"{gross - cost_pct:.6f}",
            "bars_held": exit_index - position["entry_index"] + 1,
        })
        position = None

    for execution_index in range(1, len(bars)):
        execution_price = float(bars[execution_index]["open"])
        direction = event_by_execution.get(execution_index)

        # A crossover is executed at this bar's open before its intrabar range.
        if direction:
            if position is not None and position["direction"] != direction:
                close_position(execution_index, execution_price, "OPPOSITE_MACD_CROSS")
            if position is None:
                stop_price = target_price = None
                if risk_mode == "fixed":
                    stop_pct, target_pct = risk_parameters(symbol)
                    stop_price, target_price = levels(execution_price, direction, stop_pct, target_pct)
                position = {
                    "direction": direction,
                    "signal_timestamp": int(bars[execution_index - 1]["timestamp"]) + 3600,
                    "entry_timestamp": int(bars[execution_index]["timestamp"]),
                    "entry_price": execution_price,
                    "entry_index": execution_index,
                    "stop_price": stop_price,
                    "target_price": target_price,
                }

        # Never use the entry candle's earlier high/low to stop out a new fill.
        if position is not None and position["entry_index"] < execution_index and risk_mode == "fixed":
            result = check_exit(bars[execution_index], position["direction"],
                                position["stop_price"], position["target_price"])
            if result:
                reason, fill_price = result
                close_position(execution_index, fill_price, reason)

    if position is not None and bars:
        last_index = len(bars) - 1
        close_position(last_index, float(bars[last_index]["close"]), "END_OF_DATA")
    return trades


def summarize(trades: list[dict]) -> dict:
    returns = [float(trade["net_return_pct"]) for trade in trades]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    return {
        "trades": len(returns),
        "win_rate_pct": round(len(wins) / len(returns) * 100.0, 2) if returns else None,
        "average_net_return_pct": round(sum(returns) / len(returns), 5) if returns else None,
        "profit_factor": round(gross_wins / gross_losses, 4) if gross_losses else (None if not wins else "INF"),
        "total_net_return_pct_simple_sum": round(sum(returns), 5) if returns else None,
        "positive_trades": len(wins),
        "negative_trades": len(losses),
        "breakeven_trades": len(returns) - len(wins) - len(losses),
    }


def run_backtest(symbols: list[str], cost_pct: float = DEFAULT_COST_PCT, risk_mode: str = "macd") -> tuple[dict, list[dict]]:
    all_trades: list[dict] = []
    per_symbol = {}
    errors = {}
    for symbol in symbols:
        try:
            bars = macd_alerts.get_hourly_bars(symbol)
            events = crossover_events(bars)
            trades = simulate_trades(symbol, bars, events, cost_pct, risk_mode)
            all_trades.extend(trades)
            per_symbol[symbol] = {
                "bars": len(bars),
                "signals": len(events),
                **summarize(trades),
                "first_bar_utc": iso_utc(int(bars[0]["timestamp"])),
                "last_bar_utc": iso_utc(int(bars[-1]["timestamp"])),
            }
            print(f"{symbol}: {len(bars)} velas, {len(events)} cruces, {len(trades)} operaciones")
        except Exception as error:
            errors[symbol] = f"{type(error).__name__}: {error}"
            print(f"ERROR {symbol}: {errors[symbol]}", file=sys.stderr)
        time.sleep(0.35)

    summary = {
        "strategy_id": STRATEGY_ID,
        "strategy_version": STRATEGY_VERSION,
        "timeframe": "1h",
        "data_source": DATA_SOURCE,
        "entry_rule": "Next available candle open after completed-candle MACD crossover",
        "risk_mode": risk_mode,
        "exit_rule": ("Fixed SL/TP checked on subsequent OHLC bars; opposite crossover at next open; final position marked to last close" if risk_mode == "fixed" else "Next available candle open after opposite MACD crossover; final open trade marked to last close"),
        "cost_assumption_round_trip_pct": cost_pct,
        "symbols": per_symbol,
        "pooled_trade_statistics": summarize(all_trades),
        "errors": errors,
        "limitations": [
            "Yahoo Finance public chart endpoint is unofficial and may be delayed, incomplete or rate-limited.",
            "Intraday history availability is limited; this run uses the bars returned by the provider, not a multi-year institutional dataset.",
            "A flat cost assumption is not a verified broker spread, commission or slippage quote.",
            "Fixed SL/TP are price distances: equities 1.5%/3.0%; FX 0.25%/0.50%. Same-bar stop/target ambiguity assumes stop first.",
            "SELL trades are theoretical short exposures; borrow costs, locate availability and margin are not modelled.",
            "Pooled statistics are not a portfolio equity curve: overlapping trades, capital allocation and correlated exposure are not modelled.",
            "An open trade at the end of the sample is marked to the last close and flagged END_OF_DATA."
        ],
    }
    return summary, all_trades


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*", default=list(macd_alerts.TICKERS))
    parser.add_argument("--cost-pct", type=float, default=DEFAULT_COST_PCT,
                        help="estimated total entry+exit costs in percent (default: 0.10)")
    parser.add_argument("--risk-mode", choices=("macd", "fixed"), default="macd", help="macd baseline or fixed stop/target variant")
    parser.add_argument("--output-dir", default=str(ROOT / "reports" / "backtest"))
    args = parser.parse_args()

    summary, trades = run_backtest(args.symbols, args.cost_pct, args.risk_mode)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)
        file.write("\n")
    fields = [
        "trade_id", "symbol", "direction", "signal_timestamp_utc",
        "entry_timestamp_utc", "entry_price", "exit_timestamp_utc", "exit_price",
        "exit_reason", "stop_price", "target_price", "gross_return_pct", "estimated_round_trip_cost_pct",
        "net_return_pct", "bars_held",
    ]
    with (output_dir / "trades.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trades)
    print(json.dumps(summary["pooled_trade_statistics"], ensure_ascii=False, indent=2))
    print(f"Informes guardados en: {output_dir}")
    return 1 if summary["errors"] and not trades else 0


if __name__ == "__main__":
    raise SystemExit(main())
