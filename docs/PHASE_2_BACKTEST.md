# Fase 2 — Backtester inicial

## Qué simula

- MACD 12/26/9 en velas 1H completadas, con la misma función de cálculo que las alertas.
- La señal solo se conoce al cierre de su vela.
- La entrada se ejecuta en la apertura de la siguiente vela disponible, para evitar asumir que se consigue el cierre que generó la señal.
- Una posición se cierra y se invierte en la siguiente apertura disponible después de un cruce MACD contrario.
- Si queda una posición abierta al final de la muestra, se marca al último cierre y se identifica como `END_OF_DATA`.
- Se descuenta un coste total configurable por operación cerrada. El valor inicial del 0,10% es una hipótesis, no una tarifa verificada.

## Cómo ejecutarlo

En GitHub: **Actions → MACD historical backtest → Run workflow**. Se puede cambiar el coste estimado; por ejemplo, `0.10` significa 0,10% ida y vuelta.

El informe se descarga desde el artefacto `macd-backtest-report` de esa ejecución:
- `summary.json`: datos, resultados por símbolo, muestra y limitaciones.
- `trades.csv`: detalle de cada operación simulada.

## Limitaciones deliberadas de esta primera versión

1. El proveedor Yahoo Finance es público y no oficial; el histórico intradía disponible puede ser corto y tener huecos.
2. No se deben interpretar los resultados como prueba de rentabilidad. La muestra debe crecer y validarse fuera de muestra.
3. Las posiciones SELL se modelan como cortos teóricos; no se incluyen préstamo de acciones, disponibilidad de títulos ni costes de financiación.
4. Las estadísticas agrupadas no son una simulación de cartera: todavía no modelan capital, tamaño de posición, operaciones solapadas ni exposición correlacionada.
5. El coste fijo no sustituye spreads, comisiones y deslizamiento específicos de cada activo.
6. No hay stops ni take profits en el baseline. Se estudiarán como variantes separadas, sin contaminar la comparación.

No modifica el flujo de alertas ni envía órdenes reales.
