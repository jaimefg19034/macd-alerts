# Fase 5 — Salidas adaptadas a volatilidad con ATR

## Hipótesis

Los stops fijos en porcentaje pueden ser demasiado estrechos en activos volátiles y demasiado amplios en activos tranquilos. ATR(14) permite expresar el stop en unidades del rango típico reciente del activo.

## Variante experimental

- Indicador: ATR de Wilder, periodo 14.
- Stop: 1,5 × ATR.
- Objetivo: 3 × ATR.
- Relación nominal beneficio/riesgo: 2:1.
- El ATR se toma de la vela de señal ya cerrada; la entrada se simula en la apertura de la vela siguiente. No se usa el máximo, mínimo ni cierre de la vela de entrada para calcular el ATR.
- Las salidas se comprueban desde la vela posterior a la entrada. Si stop y objetivo aparecen tocados en la misma vela, se asume stop primero. Los gaps se ejecutan al precio de apertura.

## Comparaciones automáticas

Cada ejecución del workflow compara:
1. MACD original.
2. MACD + SL/TP fijo.
3. MACD + SL/TP fijo + filtro elegido.
4. MACD + ATR(14), stop 1,5 ATR y objetivo 3 ATR.
5. MACD + ATR(14) + el mismo filtro elegido.

Los resultados se guardan en artefactos independientes. Además, la variante ATR + filtro se somete a escenarios de coste total del 0,10%, 0,20% y 0,30% por operación completa. El ATR no se activa en Telegram ni en paper trading.

## Cómo decidir

No elegir una variante solo por win rate o por el mayor beneficio histórico. Comparar retorno neto, profit factor, expectancy, drawdown, número de operaciones, duración, resultados por símbolo y dirección, y sensibilidad a costes. Repetir en periodos cronológicos no usados para diseñar la hipótesis.

Los datos intradía de Yahoo disponibles en este proyecto cubren una ventana corta; por tanto, cualquier resultado será exploratorio y no evidencia de rentabilidad futura. El coste fijo del 0,10% sigue siendo una hipótesis, no un coste de ejecución verificado. La estrategia no debe pasar a ejecución real por un buen backtest.
