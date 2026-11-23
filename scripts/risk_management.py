"""Conservative stop/target rules shared by research modules."""
from __future__ import annotations

EQUITY_STOP_PCT = 1.50
EQUITY_TARGET_PCT = 3.00
FX_STOP_PCT = 0.25
FX_TARGET_PCT = 0.50
FX_SYMBOLS = {"EURUSD=X", "EURGBP=X"}


def risk_parameters(symbol: str) -> tuple[float, float]:
    """Return price-distance percentages, not account-equity risk percentages."""
    return (FX_STOP_PCT, FX_TARGET_PCT) if symbol in FX_SYMBOLS else (EQUITY_STOP_PCT, EQUITY_TARGET_PCT)


def levels(entry_price: float, direction: str, stop_pct: float, target_pct: float) -> tuple[float, float]:
    if entry_price <= 0 or direction not in {"BUY", "SELL"}:
        raise ValueError("Precio de entrada o dirección inválidos")
    if not (0 < stop_pct < 100 and 0 < target_pct < 100):
        raise ValueError("Stop y objetivo deben estar entre 0 y 100")
    if direction == "BUY":
        return entry_price * (1 - stop_pct / 100), entry_price * (1 + target_pct / 100)
    return entry_price * (1 + stop_pct / 100), entry_price * (1 - target_pct / 100)


def check_exit(bar: dict, direction: str, stop_price: float, target_price: float) -> tuple[str, float] | None:
    """Check one OHLC bar. Gaps fill at open; ambiguous stop+target bars assume stop first."""
    op, hi, lo = (float(bar[k]) for k in ("open", "high", "low"))
    if direction == "BUY":
        if op <= stop_price:
            return "STOP_LOSS_GAP", op
        if op >= target_price:
            return "TAKE_PROFIT_GAP", op
        hit_stop, hit_target = lo <= stop_price, hi >= target_price
    else:
        if op >= stop_price:
            return "STOP_LOSS_GAP", op
        if op <= target_price:
            return "TAKE_PROFIT_GAP", op
        hit_stop, hit_target = hi >= stop_price, lo <= target_price
    if hit_stop:
        return "STOP_LOSS", stop_price
    if hit_target:
        return "TAKE_PROFIT", target_price
    return None


def leverage_sensitivity(price_return_pct: float, leverage: float) -> float:
    """Illustrative return on posted margin before costs/margin close-out."""
    if leverage < 1:
        raise ValueError("El apalancamiento debe ser >= 1")
    return price_return_pct * leverage
