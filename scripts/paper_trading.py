#!/usr/bin/env python3
"""Hourly paper-trading ledger driven by completed MACD candles; never sends real orders."""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import macd_alerts  # noqa: E402
from backtest import crossover_events  # noqa: E402

STATE_FILE = ROOT / "data" / "paper_state.json"
TRADES_FILE = ROOT / "data" / "paper_trades.csv"
COST_PCT = 0.10
TRADE_FIELDS = [
    "trade_id", "strategy_id", "strategy_version", "symbol", "direction",
    "signal_timestamp_utc", "entry_timestamp_utc", "entry_price",
    "exit_timestamp_utc", "exit_price", "exit_reason",
    "gross_return_pct", "estimated_round_trip_cost_pct", "net_return_pct",
    "bars_held",
]


def iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def empty_state() -> dict:
    return {"state_version": 1, "last_processed": {}, "positions": {}}


def load_state() -> dict:
    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
        if not isinstance(state, dict):
            raise ValueError("se esperaba un objeto JSON")
        state.setdefault("last_processed", {})
        state.setdefault("positions", {})
        state.setdefault("state_version", 1)
        return state
    except FileNotFoundError:
        return empty_state()
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError(f"El estado de paper trading está dañado: {error}") from error


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")
    os.replace(temporary, STATE_FILE)


def load_trades() -> list[dict]:
    try:
        with TRADES_FILE.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))
    except FileNotFoundError:
        return []


def save_trades(trades: list[dict]) -> None:
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = TRADES_FILE.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TRADE_FIELDS)
        writer.writeheader()
        writer.writerows(trades)
    os.replace(temporary, TRADES_FILE)


def process_symbol_bars(symbol: str, bars: list[dict],
                        events: list[tuple[int, str]],
                        state: dict, trades: list[dict],
                        cost_pct: float = COST_PCT) -> int:
    """Process only unseen signal candles that have a following completed bar.

    First run establishes a clean baseline at the penultimate candle. It does not
    create historical paper trades. Later runs fill at the next candle's open.
    """
    if cost_pct < 0:
        raise ValueError("cost_pct no puede ser negativo")
    if len(bars) < 2:
        return 0

    last_processed = state.setdefault("last_processed", {})
    positions = state.setdefault("positions", {})
    cursor = last_processed.get(symbol)
    if cursor is None:
        last_processed[symbol] = int(bars[-2]["timestamp"])
        print(f"{symbol}: línea base inicializada; sin operaciones históricas.")
        return 0

    known_trade_ids = {trade.get("trade_id") for trade in trades}
    created = 0
    for signal_index, direction in events:
        if signal_index + 1 >= len(bars):
            continue
        signal_timestamp = int(bars[signal_index]["timestamp"])
        if signal_timestamp <= int(cursor):
            continue

        execution_index = signal_index + 1
        execution_bar = bars[execution_index]
        execution_price = float(execution_bar["open"])
        position = positions.get(symbol)

        if position is not None and position["direction"] != direction:
            entry_price = float(position["entry_price"])
            if entry_price > 0 and execution_price > 0:
                old_direction = position["direction"]
                gross = (
                    (execution_price / entry_price - 1.0) * 100.0
                    if old_direction == "BUY"
                    else (entry_price / execution_price - 1.0) * 100.0
                )
                trade_id = (
                    f"{macd_alerts.STRATEGY_ID}:{symbol}:"
                    f"{old_direction}:{position['entry_timestamp']}"
                )
                if trade_id not in known_trade_ids:
                    trades.append({
                        "trade_id": trade_id,
                        "strategy_id": macd_alerts.STRATEGY_ID,
                        "strategy_version": macd_alerts.STRATEGY_VERSION,
                        "symbol": symbol,
                        "direction": old_direction,
                        "signal_timestamp_utc": iso_utc(int(position["signal_timestamp"])),
                        "entry_timestamp_utc": iso_utc(int(position["entry_timestamp"])),
                        "entry_price": f"{entry_price:.10f}",
                        "exit_timestamp_utc": iso_utc(int(execution_bar["timestamp"])),
                        "exit_price": f"{execution_price:.10f}",
                        "exit_reason": "OPPOSITE_MACD_CROSS",
                        "gross_return_pct": f"{gross:.6f}",
                        "estimated_round_trip_cost_pct": f"{cost_pct:.6f}",
                        "net_return_pct": f"{gross - cost_pct:.6f}",
                        "bars_held": execution_index - int(position["entry_index"]),
                    })
                    known_trade_ids.add(trade_id)
                    created += 1
            positions.pop(symbol, None)

        if symbol not in positions:
            positions[symbol] = {
                "direction": direction,
                "signal_timestamp": signal_timestamp + 3600,
                "entry_timestamp": int(execution_bar["timestamp"]),
                "entry_price": execution_price,
                "entry_index": execution_index,
            }

    # Only advance through candles whose next bar is available for execution.
    last_processed[symbol] = max(
        int(cursor), int(bars[-2]["timestamp"])
    )
    return created


def main() -> int:
    state = load_state()
    trades = load_trades()
    errors = []
    closed_count = 0

    for symbol in macd_alerts.TICKERS:
        try:
            bars = macd_alerts.get_hourly_bars(symbol)
            events = crossover_events(bars)
            closed_count += process_symbol_bars(symbol, bars, events, state, trades)
            position = state["positions"].get(symbol)
            status = "posición " + position["direction"] if position else "sin posición"
            print(f"{symbol}: {status}")
        except Exception as error:
            errors.append(f"{symbol}: {type(error).__name__}: {error}")
            print(f"ERROR {symbol}: {error}", file=sys.stderr)
        time.sleep(0.35)

    # Persist state and ledger together in the workflow's single git commit.
    save_state(state)
    save_trades(trades)
    open_positions = len(state["positions"])
    print(
        f"Paper trading: {closed_count} operación(es) cerrada(s) en esta ejecución; "
        f"{open_positions} posición(es) abierta(s); {len(trades)} operaciones cerradas acumuladas."
    )
    if errors:
        print("Algunos símbolos no se pudieron actualizar: " + " | ".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
