#!/usr/bin/env python3
"""Confirmed one-hour MACD crossover alerts for eight US-listed tickers.

Data source: Yahoo Finance chart endpoint (unofficial; may be delayed/rate-limited).
Notifications: Telegram Bot API.
No third-party Python packages are required.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TICKERS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "MRNA")
STATE_FILE = "data/last_signals.json"
CANDLE_SECONDS = 60 * 60
LOOKBACK_DAYS = 60
MADRID = ZoneInfo("Europe/Madrid")
USER_AGENT = "Mozilla/5.0 (compatible; MACDAlerts/1.0)"


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def get_completed_hourly_bars(symbol: str) -> list[tuple[int, float]]:
    """Return hourly bars only after their full one-hour interval has elapsed."""
    now = int(time.time())
    query = urllib.parse.urlencode({
        "period1": now - LOOKBACK_DAYS * 24 * 60 * 60,
        "period2": now,
        "interval": "60m",
        "includePrePost": "false",
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
    payload = get_json(url)
    chart = payload.get("chart", {})
    results = chart.get("result") or []
    if not results:
        raise RuntimeError(f"Yahoo Finance no devolvió datos para {symbol}: {chart.get('error')}")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []

    bars: list[tuple[int, float]] = []
    for timestamp, close in zip(timestamps, closes):
        timestamp = int(timestamp)
        if close is not None and timestamp + CANDLE_SECONDS <= now:
            bars.append((timestamp, float(close)))

    bars.sort(key=lambda item: item[0])
    if len(bars) < 40:
        raise RuntimeError(f"Histórico insuficiente para {symbol}: {len(bars)} velas cerradas")
    return bars


def ema(values: list[float], period: int) -> list[float | None]:
    """EMA seeded with the SMA of the first period values."""
    if len(values) < period:
        raise ValueError("No hay suficientes datos para calcular la EMA")

    output: list[float | None] = [None] * (period - 1)
    current = sum(values[:period]) / period
    output.append(current)
    alpha = 2.0 / (period + 1.0)

    for value in values[period:]:
        current = alpha * value + (1.0 - alpha) * current
        output.append(current)
    return output


def calculate_macd(closes: list[float]) -> tuple[list[float | None], list[float | None]]:
    """Standard MACD: EMA(12) - EMA(26), with EMA(9) signal line."""
    fast = ema(closes, 12)
    slow = ema(closes, 26)

    macd: list[float | None] = [
        (fast_value - slow_value)
        if fast_value is not None and slow_value is not None
        else None
        for fast_value, slow_value in zip(fast, slow)
    ]

    first_valid = next(index for index, value in enumerate(macd) if value is not None)
    signal_values = ema([value for value in macd[first_valid:] if value is not None], 9)
    signal = [None] * first_valid + signal_values
    return macd, signal


def load_state() -> dict[str, int]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
        return {symbol: int(timestamp) for symbol, timestamp in raw.items()}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError(f"El archivo de estado está dañado: {error}") from error


def save_state(state: dict[str, int]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    temporary_file = STATE_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")
    os.replace(temporary_file, STATE_FILE)


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "Faltan los secretos TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID en GitHub."
        )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        # Do not print the request URL: it contains the private bot token.
        raise RuntimeError(f"No se pudo contactar con Telegram: {type(error).__name__}") from None

    if not result.get("ok"):
        raise RuntimeError("Telegram rechazó el mensaje. Revisa el token y el chat ID.")


def split_message(message: str, limit: int = 3500) -> list[str]:
    if len(message) <= limit:
        return [message]
    chunks: list[str] = []
    current = ""
    for block in message.split("\n\n"):
        candidate = block if not current else current + "\n\n" + block
        if len(candidate) > limit and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def format_alert(symbol: str, direction: str, candle_timestamp: int,
                 close_price: float, macd_value: float, signal_value: float) -> str:
    candle_start = datetime.fromtimestamp(candle_timestamp, tz=timezone.utc).astimezone(MADRID)
    return (
        f"{direction} — {symbol}\n"
        f"MACD: {macd_value:.4f} | Señal: {signal_value:.4f}\n"
        f"Inicio de la vela: {candle_start:%d/%m/%Y %H:%M} (hora de Madrid)\n"
        f"Cierre: {close_price:.2f} USD"
    )


def main() -> int:
    old_state = load_state()
    new_state = dict(old_state)
    alerts: list[str] = []
    errors: list[str] = []

    for symbol in TICKERS:
        try:
            bars = get_completed_hourly_bars(symbol)
            timestamps = [timestamp for timestamp, _ in bars]
            closes = [close for _, close in bars]
            macd, signal = calculate_macd(closes)
            latest_timestamp = timestamps[-1]

            if symbol not in old_state:
                # First run establishes a baseline; it does not send old signals.
                new_state[symbol] = latest_timestamp
                print(f"{symbol}: referencia inicial guardada, sin alertas históricas.")
                continue

            last_processed = old_state[symbol]
            if last_processed < timestamps[0]:
                # The saved point is older than the available history window.
                new_state[symbol] = latest_timestamp
                print(f"{symbol}: histórico anterior no disponible; nueva referencia guardada.")
                continue

            new_indices = [
                index for index, timestamp in enumerate(timestamps)
                if timestamp > last_processed
            ]

            for index in new_indices:
                if index == 0 or macd[index - 1] is None or signal[index - 1] is None:
                    continue
                if macd[index] is None or signal[index] is None:
                    continue

                previous_macd = macd[index - 1]
                previous_signal = signal[index - 1]
                current_macd = macd[index]
                current_signal = signal[index]

                if previous_macd <= previous_signal and current_macd > current_signal:
                    alerts.append(format_alert(
                        symbol, "🟢 COMPRA", timestamps[index], closes[index],
                        current_macd, current_signal
                    ))
                elif previous_macd >= previous_signal and current_macd < current_signal:
                    alerts.append(format_alert(
                        symbol, "🔴 VENTA", timestamps[index], closes[index],
                        current_macd, current_signal
                    ))

            if new_indices:
                new_state[symbol] = timestamps[new_indices[-1]]
                print(f"{symbol}: revisadas {len(new_indices)} vela(s) nueva(s).")
            else:
                print(f"{symbol}: no hay velas nuevas cerradas.")

        except Exception as error:
            errors.append(f"{symbol}: {error}")
            print(f"ERROR {symbol}: {error}", file=sys.stderr)

    # Send first. If Telegram fails, do not advance the state, so the alert is retried.
    if alerts:
        message = "📈 ALERTAS MACD — TEMPORALIDAD 1H\n\n" + "\n\n".join(alerts)
        for chunk in split_message(message):
            send_telegram(chunk)
        print(f"Telegram: enviadas {len(alerts)} señal(es).")
    else:
        print("No hay cruces MACD nuevos.")

    # Persist successfully checked symbols even if another symbol had a data error.
    save_state(new_state)

    if errors:
        print("Algunos símbolos no se pudieron consultar: " + " | ".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR FATAL: {error}", file=sys.stderr)
        raise SystemExit(1)
