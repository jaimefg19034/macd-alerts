# Fase 4 — Filtros de calidad de señal (investigación)

## Objetivo

Probar si los filtros reducen cruces MACD de baja calidad sin asumir que menos operaciones significa mejor rendimiento. Ningún filtro se incorpora a las alertas Telegram ni al paper trading hasta demostrar una mejora robusta.

## Variantes

- none: MACD 12/26/9 sin filtro.
- ema200: BUY solo si el cierre de la vela de señal está por encima de EMA200; SELL solo si está por debajo.
- ema_adx: EMA200 más ADX(14) >= 20.
- ema_adx_rsi: EMA200 + ADX(14) >= 20 + RSI(14) > 50 para BUY o < 50 para SELL.

Los indicadores se calculan con la vela de señal y datos anteriores, sin usar velas futuras. EMA200/ADX tienen periodo de calentamiento; las señales sin indicador disponible se descartan en las variantes filtradas.

## Comparación

El workflow genera:
- macd_only/: MACD sin SL/TP ni filtros (baseline original).
- fixed_sl_tp/: MACD con stop/objetivo fijo, sin filtro.
- fixed_sl_tp_<filtro>/: misma gestión de riesgo y filtro elegido.

El filtro se puede elegir en Actions → MACD historical backtest → Run workflow. Para aislar el efecto de un filtro, comparar siempre fixed_sl_tp/ con fixed_sl_tp_<filtro>/ de la misma ejecución, no solo con el baseline MACD.

## Criterios para aceptar una mejora

1. Comparar con el mismo periodo, universo, costes y reglas de ejecución.
2. Revisar retorno neto, profit factor, drawdown, número de operaciones y rendimiento por activo/dirección; no seleccionar solo por win rate.
3. Exigir una muestra suficiente y validación cronológica fuera de muestra (walk-forward).
4. Comprobar sensibilidad a costes, huecos, deslizamiento y cambios de parámetros.
5. Evitar optimizar y evaluar sobre el mismo periodo. Los filtros actuales son hipótesis, no recomendaciones ni prueba de ventaja.

El paper trading y Telegram siguen con MACD original. Esta fase solo investiga filtros en el backtester.