# Fase 7 — Validación walk-forward

El workflow descarga hasta 700 días de velas horarias cuando Yahoo Finance las proporciona y guarda una captura única e inmutable. Todas las variantes del backtest y las cuatro ventanas walk-forward reutilizan exactamente esos mismos datos. Para cada activo:
- El primer 50% del histórico se reserva como periodo inicial de desarrollo y calentamiento de indicadores.
- El 50% restante se divide en cuatro ventanas cronológicas consecutivas fuera de muestra.
- Se evalúa la regla fija MACD 12/26/9 + filtro EMA200/ADX14/RSI14 + salidas ATR(14), stop 1,5 ATR y objetivo 3 ATR.
- Se repite el cálculo con costes totales supuestos del 0,10%, 0,20% y 0,30%.

No se optimizan parámetros en este proceso: se comprueba si la hipótesis fija mantiene resultados en periodos posteriores. Cada ventana se simula por separado y las posiciones se cierran al final de cada ventana, evitando arrastrar una posición de una ventana a otra.

El informe incluye resultados por cada ventana fuera de muestra, operaciones, tasa de acierto, retorno medio, profit factor, comparación con una referencia buy-and-hold equiponderada y mediana de rentabilidades por acción USD y una simulación de cartera con riesgo nominal del 0,5% y exposición máxima del 100%, limitada a acciones estadounidenses en USD. La curva incluye equity realizado y mark-to-market a cierres horarios, pérdidas/ganancias latentes, exposición y drawdown no realizado; para posiciones abiertas descuenta el coste estimado completo de liquidación.

Limitaciones: Yahoo puede no entregar los 700 días completos; costes son supuestos; drawdown intrabar no disponible (el mark-to-market usa cierres horarios); posiciones cortas teóricas; sin préstamo, financiación ni reglas de margen. La evaluación no demuestra rentabilidad futura y no activa la estrategia en Telegram ni en paper trading.

## Comparación walk-forward de filtros (23-11-2026)

Se añadió una comparación de los tres filtros sobre una única captura común de datos, con salidas ATR(14), stop 1,5 ATR / objetivo 3 ATR, cuatro ventanas fuera de muestra y costes supuestos por operación completa.

Resultados agregados de las operaciones fuera de muestra:

| Filtro | Operaciones | Acierto | Retorno medio neto/operación | Profit factor |
|---|---:|---:|---:|---:|
| EMA200 | 1.196 | 36,79% | 0,1114% | 1,1124 |
| EMA200 + ADX | 778 | 37,79% | 0,16811% | 1,1537 |
| EMA200 + ADX + RSI | 648 | 37,35% | 0,1954% | 1,1769 |

Simulación de cartera (capital inicial 10.000 USD, riesgo nominal 0,5% por operación, exposición máxima 100%, solo acciones estadounidenses denominadas en USD):

| Filtro | Coste 0,10% | Coste 0,20% | Coste 0,30% | Drawdown MTM al 0,10% |
|---|---:|---:|---:|---:|
| EMA200 | +25,23% | +9,08% | -4,99% | 19,30% |
| EMA200 + ADX | +21,89% | +8,35% | -3,68% | 13,84% |
| EMA200 + ADX + RSI | +17,64% | +5,72% | -4,98% | 12,94% |

Retorno de cartera por ventana al coste supuesto del 0,10%:

| Filtro | Ventana 1 | Ventana 2 | Ventana 3 | Ventana 4 |
|---|---:|---:|---:|---:|
| EMA200 | +11,73% | +18,65% | -11,78% | +7,08% |
| EMA200 + ADX | +2,01% | +15,19% | -6,49% | +10,93% |
| EMA200 + ADX + RSI | -0,06% | +13,17% | -5,02% | +9,51% |

Lectura: añadir ADX reduce el drawdown respecto a EMA200 en esta muestra y mejora el profit factor, aunque reduce el retorno total. Añadir RSI reduce aún más la frecuencia y el drawdown, y eleva el profit factor, pero también reduce la rentabilidad de cartera. Ningún filtro es positivo en las cuatro ventanas. Todos los escenarios dejan de ser rentables en torno al coste supuesto del 0,30%, con diferencias pequeñas entre filtros. Por tanto, EMA200 + ADX es una hipótesis prometedora para seguir estudiando la relación rentabilidad/drawdown, no una estrategia validada ni una configuración que deba activarse en producción.

Los costes son escenarios hipotéticos uniformes, no tarifas verificadas de un bróker. El drawdown mark-to-market se calcula con cierres horarios, no con todos los movimientos intrabar. La simulación no incluye dividendos, préstamo de acciones, financiación ni conversiones de divisa.

## Análisis preliminar por activo (coste supuesto 0,10%)

El resultado agregado oculta diferencias fuertes entre símbolos. En la variante EMA200 + ADX + RSI, los mejores retornos medios netos por operación fueron MRNA (+1,4178%, 32 operaciones), NVDA (+0,8891%, 33), MU (+0,7790%, 39), AVGO (+0,5697%, 27) y GOOGL (+0,4866%, 42). Entre los peores: TSLA (-0,8868%, 39), SAN.MC (-0,2510%, 37), EURGBP=X (-0,0963%, 72), EURUSD=X (-0,0950%, 79) y META (-0,0449%, 39).

Esto no justifica excluir o seleccionar activos todavía: MRNA puede dominar resultados con una muestra relativamente pequeña y sus movimientos extremos pueden no repetirse. Además, la cartera simulada no incluye FX ni SAN.MC por diferencias de divisa, aunque sus operaciones sí aparecen en las estadísticas agrupadas. El siguiente estudio debe medir consistencia por activo y por ventana, no solo el retorno medio agregado, y separar universos de acciones y FX antes de compararlos.


## Optimización ATR con separación desarrollo/OOS (23-11-2026)

Se añadió un experimento independiente en `scripts/atr_research.py`. La selección se realiza únicamente con el primer 50% del histórico, usando el filtro EMA200 + ADX y un coste supuesto del 0,20% por operación completa. Se compararon 16 combinaciones predefinidas: stop de 1,0 / 1,5 / 2,0 / 2,5 ATR y objetivo de 2,0 / 3,0 / 4,0 / 5,0 ATR. Solo se admiten configuraciones con al menos 100 operaciones de desarrollo y profit factor finito.

La combinación seleccionada fue **stop 1,5 ATR / objetivo 5,0 ATR** (665 operaciones de desarrollo, acierto 24,96%, PF 1,0383 y retorno neto medio +0,0440% por operación al coste supuesto del 0,20%). La selección no significa que sea una configuración rentable: el margen estadístico del periodo de desarrollo es reducido.

Con esos parámetros congelados, se evaluó el 50% posterior en cuatro ventanas cronológicas. Resultados OOS agrupados:

| Coste supuesto | Operaciones | Acierto | Retorno neto medio | Profit factor | Retorno cartera MTM | DD máximo MTM |
|---|---:|---:|---:|---:|---:|---:|
| 0,10% | 704 | 26,85% | +0,3233% | 1,2509 | +33,77% | 13,14% |
| 0,20% | 704 | 26,85% | +0,2233% | 1,1640 | +22,60% | 14,32% |
| 0,30% | 704 | 25,85% | +0,1233% | 1,0859 | +12,39% | 15,47% |

Rentabilidad MTM de cartera por ventana:

| Coste | Ventana 1 | Ventana 2 | Ventana 3 | Ventana 4 |
|---|---:|---:|---:|---:|
| 0,10% | +0,60% | +19,96% | +7,90% | +2,73% |
| 0,20% | -1,98% | +17,94% | +5,66% | +0,37% |
| 0,30% | -4,49% | +15,96% | +3,47% | -1,93% |

Lectura: esta combinación mejora los resultados agregados de la hipótesis ATR 1,5/3,0 previamente estudiada en esta misma muestra, pero la ventaja no es uniforme: la primera ventana empeora con costes altos y la cuarta apenas supera cero al 0,20% y cae al 0,30%. La tasa de acierto es baja; el resultado depende de que las operaciones ganadoras compensen muchas pérdidas. No debemos interpretar el +33,77% como una previsión ni como rentabilidad esperable.

**Importante:** esta prueba utiliza el mismo histórico que se había usado en análisis anteriores, aunque la mitad OOS no se utilizó para escoger la combinación. La búsqueda de 16 configuraciones sobre el periodo de desarrollo puede generar sobreajuste; hace falta validación walk-forward anidada o un nuevo periodo futuro no utilizado, además de costes reales del bróker. La simulación de cartera sigue limitada a acciones USD y a cierres horarios; no incluye intrabar, dividendos, préstamo/financiación ni conversión de divisas. La variante 1,5/5,0 queda solo como hipótesis de investigación: no se ha activado en Telegram ni en paper trading.


Limitación metodológica adicional: aunque los múltiplos ATR (1,5/5,0) se eligieron solo con el periodo de desarrollo, el filtro EMA200 + ADX se había destacado tras revisar una comparación OOS anterior hecha sobre esta misma captura. Por eso, las cifras OOS de esta variante no constituyen una validación completamente independiente de toda la combinación. Para conseguirla habría que fijar filtro y salidas antes de descargar un nuevo bloque de datos futuro, sin volver a ajustar nada durante ese bloque.