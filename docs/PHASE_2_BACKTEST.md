# Fase 2 — Backtester y comparación de gestión del riesgo

## Variantes comparadas

El workflow ejecuta dos simulaciones sobre el mismo histórico y las mismas señales:

1. macd_only: MACD 12/26/9; cierre/reversión en la siguiente apertura tras un cruce contrario.
2. fixed_sl_tp: misma entrada y señales, con stop-loss y take-profit fijos:
   - Acciones/otros símbolos no FX: 1,50% / 3,00%.
   - Forex (EURUSD=X, EURGBP=X): 0,25% / 0,50%.

## Convenciones de ejecución

- Solo se usan velas 1H completadas.
- La señal se confirma al cierre de su vela; entrada en la apertura de la siguiente vela.
- SL/TP se comprueban desde la vela posterior a la entrada, no en la vela de entrada.
- Si stop y objetivo se tocan en una misma vela, se asume stop primero (criterio conservador).
- Si la apertura salta más allá del stop, el fill simulado es la apertura.
- Un cruce contrario cierra/revierte en la siguiente apertura disponible si la posición sigue abierta.
- Una posición final abierta se marca al último cierre y se identifica como END_OF_DATA.
- Coste total configurable; 0,10% es una hipótesis provisional, no una tarifa verificada.

## Ejecución y resultados

En GitHub: **Actions → MACD historical backtest → Run workflow**. El workflow crea dos carpetas dentro del artefacto macd-backtest-report:
- macd_only/: baseline original.
- fixed_sl_tp/: variante con gestión del riesgo fija.

Cada carpeta contiene summary.json y trades.csv. Compara ambas variantes con idéntico coste y periodo.

## Limitaciones

1. Yahoo Finance es un proveedor público no oficial; el histórico intradía puede ser corto, retrasado o incompleto.
2. Una muestra corta no demuestra rentabilidad ni robustez. Hace falta validación cronológica fuera de muestra y más histórico.
3. SELL son cortos teóricos; no se incluyen préstamo, financiación ni disponibilidad de acciones.
4. Estadísticas agrupadas no son una simulación de cartera: faltan capital, tamaño de posición, operaciones simultáneas, exposición y correlaciones.
5. El coste plano no representa spreads, comisiones y deslizamiento específicos.
6. Las velas OHLC no revelan el orden intravela; la regla stop-primero reduce optimismo, pero no sustituye datos de menor intervalo.

No modifica las alertas Telegram ni envía órdenes reales.