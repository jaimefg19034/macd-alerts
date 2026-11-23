"""Event-driven, unleveraged USD-equity portfolio simulation for research."""
from __future__ import annotations
from datetime import datetime

USD_EQUITY_SYMBOLS = {
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "MRNA", "OCGN", "AMD", "AVGO", "MU", "JPM", "XOM",
}


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _trade_return(entry: float, mark: float, direction: str) -> float:
    if entry <= 0 or mark <= 0:
        return 0.0
    return (mark / entry - 1.0) * 100.0 if direction == "BUY" else (entry / mark - 1.0) * 100.0


def simulate_portfolio(trades: list[dict], initial_equity: float = 10_000.0,
                       risk_pct: float = 0.5, max_exposure_pct: float = 100.0,
                       bars_by_symbol: dict[str, list[dict]] | None = None) -> dict:
    """Size trades by stop risk and calculate both realized and close-to-close MTM equity.

    Only USD-denominated US equities are included. Net trade returns include
    estimated round-trip costs. MTM assumes the full estimated round-trip cost
    would be paid to liquidate each open position, a conservative convention.
    """
    if initial_equity <= 0 or not 0 < risk_pct <= 100 or not 0 < max_exposure_pct <= 100:
        raise ValueError("Invalid equity, risk_pct or exposure cap")
    included = [t for t in trades if t.get("symbol") in USD_EQUITY_SYMBOLS]
    events: dict[datetime, dict[str, list]] = {}
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
        events.setdefault(entry_time, {"entries": [], "exits": [], "marks": []})["entries"].append(trade)
        events.setdefault(exit_time, {"entries": [], "exits": [], "marks": []})["exits"].append(trade)

    # Hourly candle timestamps identify candle opens; its close becomes known one hour later.
    if bars_by_symbol:
        first = min(events) if events else None
        last = max(events) if events else None
        for symbol, bars in bars_by_symbol.items():
            if symbol not in USD_EQUITY_SYMBOLS:
                continue
            for bar in bars:
                try:
                    mark_time = datetime.fromtimestamp(int(bar["timestamp"]) + 3600, tz=first.tzinfo if first else None)
                    price = float(bar["close"])
                    if price <= 0 or (first and mark_time < first) or (last and mark_time > last):
                        continue
                    events.setdefault(mark_time, {"entries": [], "exits": [], "marks": []})["marks"].append((symbol, price))
                except (KeyError, TypeError, ValueError, OSError):
                    continue

    cash = initial_equity
    active: dict[str, dict] = {}
    latest_marks: dict[str, float] = {}
    curve = [{"timestamp_utc": None, "realized_equity": round(cash, 2),
              "equity_mtm": round(cash, 2), "gross_exposure": 0.0,
              "unrealized_pnl_after_estimated_liquidation_cost": 0.0}]
    skipped_capacity = 0
    closed = 0
    peak_realized = peak_mtm = initial_equity
    max_realized_dd = max_mtm_dd = 0.0

    def marked_equity() -> tuple[float, float, float]:
        unrealized = 0.0
        exposure = 0.0
        for item in active.values():
            exposure += item["notional"]
            mark = latest_marks.get(item["symbol"], item["entry_price"])
            gross_pct = _trade_return(item["entry_price"], mark, item["direction"])
            # Use the complete round-trip estimate while a position is open.
            net_pct = gross_pct - item["estimated_round_trip_cost_pct"]
            unrealized += item["notional"] * net_pct / 100.0
        return cash + unrealized, unrealized, exposure

    for timestamp in sorted(events):
        group = events[timestamp]
        for symbol, price in group["marks"]:
            latest_marks[symbol] = price

        # Close first at a shared timestamp, releasing capacity before new entries.
        for trade in sorted(group["exits"], key=lambda x: x["trade_id"]):
            item = active.pop(trade["trade_id"], None)
            if item is None:
                continue
            cash += item["notional"] * float(trade["net_return_pct"]) / 100.0
            closed += 1

        equity_now, _, _ = marked_equity()
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
            desired = (max(0.0, equity_now) * risk_pct / 100.0) / (stop_distance_pct / 100.0)
            candidates.append((trade, desired))
        current_exposure = sum(x["notional"] for x in active.values())
        capacity = max(0.0, max(0.0, equity_now) * max_exposure_pct / 100.0 - current_exposure)
        desired_total = sum(x[1] for x in candidates)
        scale = min(1.0, capacity / desired_total) if desired_total > 0 else 0.0
        for trade, desired in candidates:
            notional = desired * scale
            if notional <= 0:
                skipped_capacity += 1
                continue
            active[trade["trade_id"]] = {
                "notional": notional, "symbol": trade["symbol"],
                "direction": trade.get("direction", "BUY"),
                "entry_price": float(trade["entry_price"]),
                "estimated_round_trip_cost_pct": float(trade.get("estimated_round_trip_cost_pct", 0.0)),
            }

        equity_mtm, unrealized, exposure = marked_equity()
        peak_realized = max(peak_realized, cash)
        peak_mtm = max(peak_mtm, equity_mtm)
        if peak_realized > 0:
            max_realized_dd = max(max_realized_dd, (peak_realized - cash) / peak_realized * 100.0)
        if peak_mtm > 0:
            max_mtm_dd = max(max_mtm_dd, (peak_mtm - equity_mtm) / peak_mtm * 100.0)
        curve.append({
            "timestamp_utc": timestamp.isoformat(),
            "realized_equity": round(cash, 2),
            "equity_mtm": round(equity_mtm, 2),
            "gross_exposure": round(exposure, 2),
            "unrealized_pnl_after_estimated_liquidation_cost": round(unrealized, 2),
        })

    final_mtm, final_unrealized, final_exposure = marked_equity()
    return {
        "base_currency": "USD",
        "universe": "USD-denominated US equities only; FX and SAN.MC excluded",
        "initial_equity": round(initial_equity, 2),
        "final_realized_equity": round(cash, 2),
        "realized_return_pct": round((cash / initial_equity - 1) * 100.0, 4),
        "final_equity_mtm": round(final_mtm, 2),
        "mtm_return_pct": round((final_mtm / initial_equity - 1) * 100.0, 4),
        "final_unrealized_pnl_after_estimated_liquidation_cost": round(final_unrealized, 2),
        "final_gross_exposure": round(final_exposure, 2),
        "risk_per_trade_pct_of_equity": risk_pct,
        "max_gross_exposure_pct_of_equity": max_exposure_pct,
        "closed_trades": closed,
        "open_positions_at_sample_end": len(active),
        "skipped_for_capacity": skipped_capacity,
        "invalid_trades": invalid,
        "max_realized_drawdown_pct": round(max_realized_dd, 4),
        "max_mtm_drawdown_pct": round(max_mtm_dd, 4),
        "equity_curve": curve,
        "limitations": [
            "MTM uses hourly candle closes; intrabar portfolio drawdown is not captured.",
            "Open positions are marked using the latest available close and the full estimated round-trip cost.",
            "Short trades assume theoretical availability; borrow, financing and margin rules are not modelled.",
            "No FX conversion: EUR-denominated SAN.MC and EURUSD/EURGBP are excluded.",
            "Risk sizing assumes the recorded stop price is executable; gaps can exceed planned risk.",
            "Initial equity and risk percentage are research assumptions, not user account settings."
        ]
    }
