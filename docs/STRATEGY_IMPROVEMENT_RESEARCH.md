# Investigación de mejora de rentabilidad: búsqueda 1 (23-11-2026)

## Regla de decisión

La configuración original solo se sustituirá si una candidata supera su rentabilidad de cartera mark-to-market en los dos escenarios principales de costes (0,10% y 0,20% por operación) sobre la misma captura horaria, y no aumenta el drawdown máximo al 0,20% en más de 2 puntos porcentuales. Si no cumple todos los criterios, no se adopta.

La búsqueda usa exclusivamente el primer 50% del histórico para elegir una configuración. La segunda mitad queda reservada para la comparación OOS en cuatro ventanas cronológicas.

## Configuración de referencia

- Universo: los 17 símbolos actuales.
- MACD 12/26/9.
- Filtro EMA200 + ADX14 >= 20.
- Stop: 1,5 ATR(14).
- Objetivo: 5 ATR(14).
- Entrada en la apertura de la siguiente vela horaria tras el cruce confirmado.
- Costes estimados round-trip: 0,10%, 0,20% y 0,30%.
- Cartera simulada: riesgo del 0,5% de equity por operación, exposición bruta máxima del 100%.

El resultado histórico anterior (+33,77% al 0,10% y +22,60% al 0,20%) se conserva como referencia histórica, pero la comparación de esta búsqueda utiliza una captura nueva común para evitar mezclar periodos.

## Método de búsqueda

Se probaron 48 combinaciones en el bloque de desarrollo:
- Filtros: EMA200; EMA200 + ADX14 >= 20; EMA200 + ADX14 >= 20 + RSI direccional.
- Stop: 1,0 / 1,5 / 2,0 / 2,5 ATR.
- Objetivo: 2 / 3 / 4 / 5 ATR.

La selección se hizo con datos del desarrollo y coste supuesto del 0,20%. El candidato mejor clasificado por el criterio de desarrollo fue EMA200 simple, stop 1,5 ATR y objetivo 5 ATR (951 operaciones de desarrollo; win rate 24,71%; PF 1,0506).

## Comparación OOS sobre la misma captura

Captura: 23-11-2026 21:38 UTC, Yahoo Finance Chart API (no oficial), intervalo 1h, 17 símbolos, histórico solicitado de 700 días. No hubo errores de descarga.

| Métrica OOS | Referencia EMA+ADX, 1,5/5 ATR | Candidato EMA200, 1,5/5 ATR |
|---|---:|---:|
| Operaciones | 689 | 1.026 |
| Acierto | 27,00% | 26,80% |
| Profit factor al coste 0,10% | 1,2678 | 1,1740 |
| Rentabilidad MTM al coste 0,10% | **+29,1542%** | +20,3639% |
| Drawdown MTM al coste 0,10% | 12,8471% | 17,5521% |
| Profit factor al coste 0,20% | 1,1790 | 1,0841 |
| Rentabilidad MTM al coste 0,20% | **+18,6055%** | +9,6231% |
| Drawdown MTM al coste 0,20% | **14,0303%** | 19,4929% |
| Rentabilidad MTM al coste 0,30% | +8,9297% | -0,1420% |
| Drawdown MTM al coste 0,30% | 15,1945% | 21,3853% |

### Rentabilidad por ventanas OOS al coste del 0,20%

| Ventana | Referencia | Candidato |
|---|---:|---:|
| 1 | -2,652% | +2,540% |
| 2 | +20,177% | +17,052% |
| 3 | +1,055% | -1,163% |
| 4 | +0,323% | -7,594% |

## Decisión

**Candidato rechazado. No se modifica la estrategia.**

El candidato seleccionado en desarrollo no supera la referencia en ninguno de los dos costes principales. Al 0,20%, la rentabilidad cae de +18,61% a +9,62% y el drawdown sube de 14,03% a 19,49%. También termina negativo al coste del 0,30% y su cuarta ventana OOS es especialmente débil.

Por tanto, se conserva la configuración original de 17 activos con EMA200 + ADX, stop 1,5 ATR y objetivo 5 ATR. No se cambian alertas de Telegram ni paper trading.

## Reproducibilidad

- [GitHub Actions: búsqueda completa](https://github.com/jaimefg19034/macd-alerts/actions/runs/45271671364)
- Artefacto: `strategy-improvement-search`, incluye informe y captura OHLCV exacta.
- Commit del experimento: `186f4b459fa61be5e6967c3c5c2ba3b7e42aaff2`.

## Limitaciones

Es un backtest horario, no una promesa de rentabilidad. El proveedor de datos es no oficial; costes son supuestos; se simplifican gaps, disponibilidad/coste de cortos y riesgo intrabar. Aunque el bloque OOS no intervino en la selección, un único periodo histórico no demuestra que la ventaja persista en el futuro. Cualquier candidata que superase esta prueba tendría que validarse después en paper trading prospectivo antes de tocar los avisos operativos.
