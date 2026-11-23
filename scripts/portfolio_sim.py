"""Event-driven, unleveraged USD-equity portfolio simulation for research."""
from __future__ import annotations
from datetime import datetime

USD_EQUITY_SYMBOLS = {
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "MRNA", "OCGN", "AMD", "AVGO", "MU", "JPM", "XOM",
}


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def simulate_portfolio(trades: list[dict], initial_equity: float = 10_000.0,
                       risk_pct: float = 0.5, max_exposure_pct: float = 100.0) -> dict:
    """Size trades by stop risk, cap aggregate gross exposure, process exits before entries.

    Only USD-denominated US equities are included. Simulated returns already
    include each trade's estimated round-trip cost. Equity changes on exits.
    """
    if initial_equity <= 0 or not 0 < risk_pct <= 100 or not 0 < max_exposure_pct <= 100:
        raise ValueError("Invalid equity, risk_pct or exposure cap")
    included = [t for t in trades if t.get("symbol") in USD_EQUITY_SYMBOLS]
    events: dict[datetime, dict[str, list[dict]]] = {}
    invalid = 0
    for trade in included:
        try:
            entry_time = _timestamp(trade["entry_timestamp_utc"])
            exit_time = _timestamp(trade["exit_timestamp_utc"])
            entry = float(trade["entry_price"])
            stop = float(trade["stop_price"])
            net_return = float(trade["net_return_pct"])
            if entry <= 0 or stop <= 0 or exit_time < entry_time:
                raise ValueError("invalid trade values")
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        events.setdefault(entry_time, {"entries": [], "exits": []})["entries"].append(trade)
        events.setdefault(exit_time, {"entries": [], "exits": []})["exits"].append(trade)

    equity = initial_equity
    active: dict[str, dict] = {}
    curve = [{"timestamp_utc": None, "equity": round(equity, 2), "exposure": 0.0}]
    skipped_capacity = 0
    closed = 0
    peak = equity
    max_drawdown_pct = 0.0

    for timestamp in sorted(events):
        group = events[timestamp]
        # Close first at a shared timestamp, releasing capacity before new entries.
        for trade in sorted(group["exits"], key=lambda x: x["trade_id"]):
            item = active.pop(trade["trade_id"], None)
            if item is None:
                continue
            equity += item["notional"] * float(trade["net_return_pct"]) / 100.0
            closed += 1
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0)

        candidates = []
        for trade in sorted(group["entries"], key=lambda x: (x["symbol"], x["trade_id"])):
            if trade["trade_id"] in active:
                continue
            entry = float(trade["entry_price"])
            stop = float(trade["stop_price"])
            stop_distance_pct = abs(entry - stop) / entry * 100.0
            if stop_distance_pct <= 0:
                invalid += 1
                continue
            desired = (equity * risk_pct / 100.0) / (stop_distance_pct / 100.0)
            candidates.append((trade, desired))
        current_exposure = sum(x["notional"] for x in active.values())
        capacity = max(0.0, equity * max_exposure_pct / 100.0 - current_exposure)
        desired_total = sum(x[1] for x in candidates)
        scale = min(1.0, capacity / desired_total) if desired_total > 0 else 0.0
        for trade, desired in candidates:
            notional = desired * scale
            if notional <= 0:
                skipped_capacity += 1
                continue
            active[trade["trade_id"]] = {"notional": notional, "symbol": trade["symbol"]}
        exposure = sum(x["notional"] for x in active.values())
        curve.append({"timestamp_utc": timestamp.isoformat(), "equity": round(equity, 2),
                      "exposure": round(exposure, 2)})

    peak = max(peak, equity)
    max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0 if peak else 0.0)
    return {
        "base_currency": "USD",
        "universe": "USD-denominated US equities only; FX and SAN.MC excluded",
        "initial_equity": round(initial_equity, 2),
        "final_realized_equity": round(equity, 2),
        "realized_return_pct": round((equity / initial_equity - 1) * 100, 4),
        "risk_per_trade_pct_of_equity": risk_pct,
        "max_gross_exposure_pct_of_equity": max_exposure_pct,
        "closed_trades": closed,
        "open_positions_at_sample_end": len(active),
        "skipped_for_capacity": skipped_capacity,
        "invalid_trades": invalid,
        "max_realized_drawdown_pct": round(max_drawdown_pct, 4),
        "equity_curve": curve,
        "limitations": [
            "Realized equity curve updates only when trades close; unrealized mark-to-market drawdown is not included.",
            "Short trades assume theoretical availability and collateral; borrow, financing and margin rules are not modelled.",
            "No FX conversion: EUR-denominated SAN.MC and EURUSD/EURGBP are excluded.",
            "Risk sizing assumes the recorded stop price is executable; gaps can exceed planned risk.",
            "Initial equity and risk percentage are research assumptions, not user account settings."
        ]
    }
