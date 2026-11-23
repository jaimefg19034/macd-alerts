# Paper trading automático — SL/TP fijos prospectivos

## Funcionamiento

- Se ejecuta por GitHub Actions una vez por hora, a los cinco minutos de cada hora.
- Utiliza MACD 12/26/9 en velas 1H completadas.
- La primera ejecución establece una línea base y **no crea operaciones históricas**.
- Entrada simulada: apertura de la siguiente vela horaria disponible tras la señal confirmada.
- Cada posición incorpora stop-loss y take-profit desde su precio de entrada:
  - Acciones/otros símbolos no FX: stop 1,50%; objetivo 3,00%.
  - Forex (EURUSD=X, EURGBP=X): stop 0,25%; objetivo 0,50%.
- Los porcentajes son distancias del precio, no riesgo sobre el capital de la cuenta.
- Se comprueban máximos y mínimos OHLC de cada vela cerrada posterior a la entrada.
- Si stop y objetivo aparecen tocados dentro de la misma vela y no hay datos inferiores, se supone que se ejecutó primero el stop.
- Si el mercado abre más allá del stop, se simula la salida al precio de apertura, no al precio teórico del stop.
- Un cruce MACD contrario cierra y revierte en la apertura de la siguiente vela disponible, siempre que la posición siga abierta.
- Cada operación cerrada se guarda en data/paper_trades.csv; las posiciones y cursores en data/paper_state.json.
- Coste provisional: 0,10% ida y vuelta. No es una cotización verificada y requiere calibración específica, especialmente para Forex.

## Importante

- No envía órdenes reales ni mensajes de Telegram. Las alertas actuales de Telegram siguen funcionando por separado y sin cambios.
- La vela de entrada no se usa para comprobar SL/TP: su máximo/mínimo no permite conocer la secuencia intravela respecto al fill simulado.
- Las posiciones SELL son cortos teóricos; no se modelan préstamo, financiación ni disponibilidad de acciones.
- Todavía no existe asignación de capital, tamaño por riesgo, límites de exposición ni curva de cartera. Este ledger no equivale a la rentabilidad de una cuenta.
- Los escenarios de apalancamiento no se aplican al paper trading. Se estudiarán aparte como sensibilidad hipotética, incluyendo sus limitaciones de margen y financiación.
- El sistema empieza desde la línea base guardada; no reconstruye operaciones históricas.
- Los resultados dependen de la calidad, disponibilidad y retraso de Yahoo Finance.
