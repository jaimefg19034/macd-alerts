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
