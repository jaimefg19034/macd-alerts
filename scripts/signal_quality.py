"""Transparent, rule-based signal confluence labels; not win probabilities."""
from __future__ import annotations


def assess_signal(direction: str, close: float, ema200: float | None,
                  adx14: float | None, rsi14: float,
                  macd_hist_previous: float, macd_hist_current: float) -> dict:
    if direction not in {"BUY", "SELL"}:
        raise ValueError("direction must be BUY or SELL")
    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    trend_aligned = ema200 is not None and (
        (direction == "BUY" and close > ema200) or
        (direction == "SELL" and close < ema200)
    )
    if trend_aligned:
        score += 2.0
        reasons.append("precio alineado con EMA200")
    elif ema200 is not None:
        risks.append("precio contra la tendencia EMA200")
    else:
        risks.append("EMA200 aún no disponible")

    if adx14 is not None and adx14 >= 25:
        score += 1.5
        reasons.append(f"tendencia con fuerza (ADX {adx14:.1f})")
    elif adx14 is not None and adx14 >= 20:
        score += 1.0
        reasons.append(f"fuerza aceptable (ADX {adx14:.1f})")
    elif adx14 is not None and adx14 < 15:
        risks.append(f"tendencia débil (ADX {adx14:.1f})")
        score -= 1.0
    else:
        risks.append("fuerza de tendencia insuficiente")

    if direction == "BUY":
        if 55 <= rsi14 <= 68:
            score += 1.5
            reasons.append(f"momentum comprador equilibrado (RSI {rsi14:.1f})")
        elif 50 < rsi14 < 55 or 68 < rsi14 < 70:
            score += 0.75
            reasons.append(f"momentum comprador moderado (RSI {rsi14:.1f})")
        elif rsi14 >= 75:
            score -= 1.5
            risks.append(f"RSI muy alto; posible movimiento extendido ({rsi14:.1f})")
        elif rsi14 >= 70:
            score -= 0.75
            risks.append(f"RSI alto ({rsi14:.1f})")
        else:
            risks.append(f"RSI no confirma momentum comprador ({rsi14:.1f})")
    else:
        if 32 <= rsi14 <= 45:
            score += 1.5
            reasons.append(f"momentum vendedor equilibrado (RSI {rsi14:.1f})")
        elif 30 < rsi14 < 32 or 45 < rsi14 < 50:
            score += 0.75
            reasons.append(f"momentum vendedor moderado (RSI {rsi14:.1f})")
        elif rsi14 <= 25:
            score -= 1.5
            risks.append(f"RSI muy bajo; posible movimiento extendido ({rsi14:.1f})")
        elif rsi14 <= 30:
            score -= 0.75
            risks.append(f"RSI bajo ({rsi14:.1f})")
        else:
            risks.append(f"RSI no confirma momentum vendedor ({rsi14:.1f})")

    histogram_expanding = (
        macd_hist_current > macd_hist_previous if direction == "BUY"
        else macd_hist_current < macd_hist_previous
    )
    if histogram_expanding:
        score += 1.0
        reasons.append("histograma MACD ganando impulso")
    else:
        risks.append("histograma MACD perdiendo impulso")

    score = round(max(0.0, min(6.0, score)), 1)
    if score >= 5.0 and not risks:
        grade = "MUY BUENA"
    elif score >= 3.5:
        grade = "BUENA"
    elif score >= 2.0:
        grade = "NORMAL"
    else:
        grade = "ARRIESGADA"

    return {
        "grade": grade,
        "score": score,
        "max_score": 6.0,
        "reasons": reasons,
        "risks": risks,
    }
