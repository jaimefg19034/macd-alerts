# Fase 7 — Validación walk-forward

El workflow descarga hasta 700 días de velas horarias cuando Yahoo Finance las proporciona y guarda una captura única e inmutable. Todas las variantes del backtest y las cuatro ventanas walk-forward reutilizan exactamente esos mismos datos. Para cada activo:
- El primer 50% del histórico se reserva como periodo inicial de desarrollo y calentamiento de indicadores.
- El 50% restante se divide en cuatro ventanas cronológicas consecutivas fuera de muestra.
- Se evalúa la regla fija MACD 12/26/9 + filtro EMA200/ADX14/RSI14 + salidas ATR(14), stop 1,5 ATR y objetivo 3 ATR.
- Se repite el cálculo con costes totales supuestos del 0,10%, 0,20% y 0,30%.

No se optimizan parámetros en este proceso: se comprueba si la hipótesis fija mantiene resultados en periodos posteriores. Cada ventana se simula por separado y las posiciones se cierran al final de cada ventana, evitando arrastrar una posición de una ventana a otra.

El informe incluye resultados por cada ventana fuera de muestra, operaciones, tasa de acierto, retorno medio, profit factor, comparación con una referencia buy-and-hold equiponderada y mediana de rentabilidades por acción USD y una simulación de cartera con riesgo nominal del 0,5% y exposición máxima del 100%, limitada a acciones estadounidenses en USD. La curva incluye equity realizado y mark-to-market a cierres horarios, pérdidas/ganancias latentes, exposición y drawdown no realizado; para posiciones abiertas descuenta el coste estimado completo de liquidación.

Limitaciones: Yahoo puede no entregar los 700 días completos; costes son supuestos; drawdown intrabar no disponible (el mark-to-market usa cierres horarios); posiciones cortas teóricas; sin préstamo, financiación ni reglas de margen. La evaluación no demuestra rentabilidad futura y no activa la estrategia en Telegram ni en paper trading.
