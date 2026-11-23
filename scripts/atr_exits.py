"""Volatility-adaptive ATR exits for research backtests only."""
from __future__ import annotations

def calculate_atr(bars: list[dict], period: int = 14) -> list[float | None]:
    """Wilder ATR using only current and preceding OHLC bars."""
    if period < 1:
        raise ValueError("ATR period must be >= 1")
    out: list[float | None] = [None] * len(bars)
    if len(bars) <= period:
        return out
    tr = [0.0] * len(bars)
    for i in range(1, len(bars)):
        high, low = float(bars[i]["high"]), float(bars[i]["low"])
        prev_close = float(bars[i - 1]["close"])
        tr[i] = max(high - low, abs(high - prev_close), abs(low - prev_close))
    value = sum(tr[1:period + 1]) / period
    out[period] = value
    for i in range(period + 1, len(bars)):
        value = (value * (period - 1) + tr[i]) / period
        out[i] = value
    return out

def atr_levels(entry_price: float, direction: str, atr: float,
               stop_multiple: float = 1.5, target_multiple: float = 3.0) -> tuple[float, float]:
    """Absolute stop/target prices using ATR known at the signal close."""
    if entry_price <= 0 or atr <= 0 or direction not in {"BUY", "SELL"}:
        raise ValueError("Entry, ATR or direction invalid")
    if stop_multiple <= 0 or target_multiple <= 0:
        raise ValueError("ATR multiples must be positive")
    stop_distance, target_distance = atr * stop_multiple, atr * target_multiple
    if direction == "BUY":
        return entry_price - stop_distance, entry_price + target_distance
    return entry_price + stop_distance, entry_price - target_distance
