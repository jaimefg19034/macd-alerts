#!/usr/bin/env python3
"""Ten-minute confirmed intrabar one-hour MACD crossover alerts for shares and FX pairs.

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

TICKERS = (
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "MRNA", "OCGN",
    "SAN.MC",       # Banco Santander, cotizado en Madrid
    "EURUSD=X",     # EUR/USD
    "EURGBP=X",     # EUR/GBP
)
SYMBOL_INFO = {
    "SAN.MC": ("Banco Santander", "EUR", 3),
    "EURUSD=X": ("EUR/USD", "USD", 5),
    "EURGBP=X": ("EUR/GBP", "GBP", 5),
    "OCGN": ("Ocugen", "USD", 4),
}
PENDING_STATE_FILE = "data/pending_crosses.json"
CONFIRMATION_SECONDS = 10 * 60
CANDLE_SECONDS = 60 * 60
LOOKBACK_DAYS = 60
MADRID = ZoneInfo("Europe/Madrid")
USER_AGENT = "Mozilla/5.0 (compatible; MACDAlerts/1.0)"


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def get_hourly_bars(symbol: str) -> list[tuple[int, float]]:
    """Return hourly bars including the currently forming one-hour candle."""
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
        if close is not None and timestamp <= now:
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


def load_pending_state() -> dict:
    try:
        with open(PENDING_STATE_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise ValueError("se esperaba un objeto JSON")
        return raw
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError(f"El archivo de cruces pendientes está dañado: {error}") from error


def save_pending_state(state: dict) -> None:
    os.makedirs(os.path.dirname(PENDING_STATE_FILE), exist_ok=True)
    temporary_file = PENDING_STATE_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, sort_keys=True)
        file.write("\n")
    os.replace(temporary_file, PENDING_STATE_FILE)


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
    display_name, currency, precision = SYMBOL_INFO.get(symbol, (symbol, "USD", 2))
    return (
        f"{direction} — {display_name}\n"
        f"MACD: {macd_value:.4f} | Señal: {signal_value:.4f}\n"
        f"Vela 1H iniciada: {candle_start:%d/%m/%Y %H:%M} (hora de Madrid)\n"
        f"Precio al confirmar: {close_price:.{precision}f} {currency}\n"
        f"Confirmación: cruce mantenido durante 10 minutos"
    )


def nth_weekday(year: int, month: int, weekday: int, n: int):
    """Return the date of the nth weekday (Monday=0) in a month."""
    from datetime import date, timedelta
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int):
    """Return the date of the last weekday (Monday=0) in a month."""
    from datetime import date, timedelta
    from calendar import monthrange
    last = date(year, month, monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def easter_sunday(year: int):
    """Gregorian Easter date."""
    from datetime import date
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def observed_fixed_holiday(year: int, month: int, day: int):
    from datetime import date, timedelta
    holiday = date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def us_market_holidays(year: int) -> set:
    """Main NYSE full-day holidays (excluding exceptional one-off closures)."""
    from datetime import timedelta
    easter = easter_sunday(year)
    return {
        observed_fixed_holiday(year, 1, 1),
        nth_weekday(year, 1, 0, 3),       # Martin Luther King Jr. Day
        nth_weekday(year, 2, 0, 3),       # Presidents Day
        easter - timedelta(days=2),       # Good Friday
        last_weekday(year, 5, 0),         # Memorial Day
        observed_fixed_holiday(year, 6, 19),  # Juneteenth
        observed_fixed_holiday(year, 7, 4),   # Independence Day
        nth_weekday(year, 9, 0, 1),       # Labor Day
        nth_weekday(year, 11, 3, 4),      # Thanksgiving
        observed_fixed_holiday(year, 12, 25),
    }


def market_is_open(symbol: str) -> bool:
    """Check the normal trading session for each exchange/FX market."""
    now_utc = datetime.now(timezone.utc)

    if symbol in ("EURUSD=X", "EURGBP=X"):
        # FX normally trades from Sunday 17:00 to Friday 17:00 New York time.
        ny = now_utc.astimezone(ZoneInfo("America/New_York"))
        if ny.weekday() == 5:
            return False
        if ny.weekday() == 6:
            return ny.hour >= 17
        if ny.weekday() == 4:
            return ny.hour < 17
        return True

    if symbol == "SAN.MC":
        # Madrid Stock Exchange continuous session: 09:00-17:30 local time.
        madrid_now = now_utc.astimezone(MADRID)
        return (
            madrid_now.weekday() < 5
            and (madrid_now.hour, madrid_now.minute) >= (9, 0)
            and (madrid_now.hour, madrid_now.minute) < (17, 30)
        )

    # US-listed shares: regular NYSE/Nasdaq session, 09:30-16:00 New York.
    ny = now_utc.astimezone(ZoneInfo("America/New_York"))
    if ny.weekday() >= 5 or ny.date() in us_market_holidays(ny.year):
        return False
    return (
        (ny.hour, ny.minute) >= (9, 30)
        and (ny.hour, ny.minute) < (16, 0)
    )


def main() -> int:
    old_pending = load_pending_state()
    new_pending = dict(old_pending)
    last_sent = dict(old_pending.get("_last_sent", {}))
    alerts: list[str] = []
    errors: list[str] = []
    now = int(time.time())

    for symbol in TICKERS:
        if not market_is_open(symbol):
            new_pending.pop(symbol, None)
            print(f"{symbol}: mercado cerrado; se omite la consulta.")
            continue
        try:
            bars = get_hourly_bars(symbol)
            timestamps = [timestamp for timestamp, _ in bars]
            closes = [close for _, close in bars]
            macd, signal = calculate_macd(closes)

            if len(timestamps) < 2 or macd[-2] is None or signal[-2] is None:
                print(f"{symbol}: histórico insuficiente para calcular el cruce.")
                continue
            if macd[-1] is None or signal[-1] is None:
                print(f"{symbol}: MACD actual no disponible.")
                continue

            previous_relation = (
                1 if macd[-2] > signal[-2]
                else -1 if macd[-2] < signal[-2]
                else 0
            )
            current_relation = (
                1 if macd[-1] > signal[-1]
                else -1 if macd[-1] < signal[-1]
                else 0
            )

            fresh_direction = None
            if previous_relation <= 0 and current_relation > 0:
                fresh_direction = "BUY"
            elif previous_relation >= 0 and current_relation < 0:
                fresh_direction = "SELL"

            pending = new_pending.get(symbol)
            if pending:
                pending_direction = pending.get("direction")
                expected_relation = 1 if pending_direction == "BUY" else -1
                if current_relation == expected_relation:
                    elapsed = now - int(pending.get("started_at", now))
                    if elapsed >= CONFIRMATION_SECONDS:
                        candle_timestamp = int(pending.get("candle_timestamp", timestamps[-1]))
                        alert_key = f"{pending_direction}:{candle_timestamp}"
                        if last_sent.get(symbol) != alert_key:
                            direction_text = "🟢 COMPRA" if pending_direction == "BUY" else "🔴 VENTA"
                            alerts.append(format_alert(
                                symbol, direction_text, timestamps[-1], closes[-1],
                                float(macd[-1]), float(signal[-1])
                            ))
                            last_sent[symbol] = alert_key
                            print(f"{symbol}: cruce {pending_direction} confirmado tras {elapsed // 60} min.")
                        else:
                            print(f"{symbol}: esta señal ya se había enviado.")
                        new_pending.pop(symbol, None)
                    else:
                        remaining = CONFIRMATION_SECONDS - elapsed
                        print(f"{symbol}: cruce {pending_direction} sigue activo; faltan {remaining // 60} min aprox.")
                else:
                    new_pending.pop(symbol, None)
                    print(f"{symbol}: cruce pendiente cancelado; ya no se mantiene.")

            if not new_pending.get(symbol) and fresh_direction:
                alert_key = f"{fresh_direction}:{timestamps[-1]}"
                if last_sent.get(symbol) != alert_key:
                    new_pending[symbol] = {
                        "direction": fresh_direction,
                        "started_at": now,
                        "candle_timestamp": timestamps[-1],
                    }
                    print(f"{symbol}: nuevo cruce {fresh_direction}; empieza la confirmación de 10 min.")
            elif not new_pending.get(symbol):
                print(f"{symbol}: sin nuevo cruce intravela que iniciar.")

        except Exception as error:
            errors.append(f"{symbol}: {error}")
            print(f"ERROR {symbol}: {error}", file=sys.stderr)

    # Send first. If Telegram fails, the previous pending state remains and the alert is retried.
    if alerts:
        message = "📈 ALERTAS MACD — 1H / CONFIRMACIÓN 10 MIN\n\n" + "\n\n".join(alerts)
        for chunk in split_message(message):
            send_telegram(chunk)
        print(f"Telegram: enviadas {len(alerts)} señal(es).")
    else:
        print("No hay cruces confirmados nuevos.")

    new_pending["_last_sent"] = last_sent
    save_pending_state(new_pending)

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
