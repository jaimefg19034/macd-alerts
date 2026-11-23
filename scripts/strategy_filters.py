"""Research-only filters for MACD crossover candidates."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import macd_alerts


FILTER_MODES = ("none", "ema200", "ema_adx", "ema_adx_rsi")


def calculate_adx(bars: list[dict], period: int = 14) -> list[float | None]:
    """Wilder ADX computed only from current and earlier OHLC bars."""
    if period < 2:
        raise ValueError("ADX period must be >= 2")
    n = len(bars)
    output: list[float | None] = [None] * n
    if n <= 2 * period - 1:
        return output

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        high = float(bars[i]["high"])
        low = float(bars[i]["low"])
        prev_high = float(bars[i - 1]["high"])
        prev_low = float(bars[i - 1]["low"])
        prev_close = float(bars[i - 1]["close"])
        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0.0
        tr[i] = max(high - low, abs(high - prev_close), abs(low - prev_close))

    smooth_tr = sum(tr[1:period + 1])
    smooth_plus = sum(plus_dm[1:period + 1])
    smooth_minus = sum(minus_dm[1:period + 1])
    dx: list[float | None] = [None] * n

    def dx_value(tr_value: float, plus_value: float, minus_value: float) -> float:
        if tr_value <= 0:
            return 0.0
        plus_di = 100.0 * plus_value / tr_value
        minus_di = 100.0 * minus_value / tr_value
        total = plus_di + minus_di
        return 0.0 if total <= 0 else 100.0 * abs(plus_di - minus_di) / total

    dx[period] = dx_value(smooth_tr, smooth_plus, smooth_minus)
    for i in range(period + 1, n):
        smooth_tr = smooth_tr - smooth_tr / period + tr[i]
        smooth_plus = smooth_plus - smooth_plus / period + plus_dm[i]
        smooth_minus = smooth_minus - smooth_minus / period + minus_dm[i]
        dx[i] = dx_value(smooth_tr, smooth_plus, smooth_minus)

    first_adx_index = 2 * period - 1
    first_values = [float(dx[i]) for i in range(period, first_adx_index + 1) if dx[i] is not None]
    if len(first_values) != period:
        return output
    output[first_adx_index] = sum(first_values) / period
    for i in range(first_adx_index + 1, n):
        output[i] = ((float(output[i - 1]) * (period - 1)) + float(dx[i])) / period
    return output


def filter_events(bars: list[dict], events: list[tuple[int, str]],
                  mode: str = "none", adx_min: float = 20.0) -> list[tuple[int, str]]:
    """Filter crossover events using data available at the signal candle close."""
    if mode not in FILTER_MODES:
        raise ValueError(f"Unknown filter mode: {mode}")
    if adx_min < 0 or adx_min > 100:
        raise ValueError("adx_min must be between 0 and 100")
    if mode == "none":
        return list(events)

    closes = [float(bar["close"]) for bar in bars]
    ema200 = macd_alerts.ema(closes, 200) if len(closes) >= 200 else [None] * len(bars)
    adx = calculate_adx(bars, 14) if mode in {"ema_adx", "ema_adx_rsi"} else [None] * len(bars)
    rsi = macd_alerts.calculate_rsi(closes, 14) if mode == "ema_adx_rsi" and len(closes) > 14 else [None] * len(bars)

    accepted = []
    for index, direction in events:
        if index < 0 or index >= len(bars):
            continue
        trend = ema200[index]
        close = closes[index]
        if trend is None:
            continue
        if direction == "BUY" and close <= trend:
            continue
        if direction == "SELL" and close >= trend:
            continue
        if mode in {"ema_adx", "ema_adx_rsi"}:
            strength = adx[index]
            if strength is None or strength < adx_min:
                continue
        if mode == "ema_adx_rsi":
            momentum = rsi[index]
            if momentum is None:
                continue
            if direction == "BUY" and momentum <= 50:
                continue
            if direction == "SELL" and momentum >= 50:
                continue
        accepted.append((index, direction))
    return accepted
