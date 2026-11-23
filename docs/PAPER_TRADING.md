# Paper trading automático — versión inicial

## Funcionamiento

- Se ejecuta por GitHub Actions una vez por hora, a los cinco minutos de cada hora.
- Utiliza el mismo MACD 12/26/9 y las velas 1H completadas que el backtester.
- La primera ejecución establece una línea base y **no crea operaciones históricas**.
- Solo procesa señales nuevas desde esa línea base.
- Entrada simulada: apertura de la siguiente vela horaria disponible tras la vela que generó la señal.
- Cierre simulado: apertura de la siguiente vela disponible tras un cruce contrario.
- Una señal contraria cierra la posición actual y abre la posición en sentido contrario.
- Cada operación cerrada se guarda en `data/paper_trades.csv`; las posiciones abiertas y los cursores se guardan en `data/paper_state.json`.
- Coste provisional: 0,10% ida y vuelta por operación, configurable en el código.

## Importante

- No envía órdenes reales ni mensajes de Telegram.
- Para mantener consistencia con el backtest, el fill de la siguiente apertura puede registrarse con retraso: la siguiente vela debe estar disponible y cerrada para verificar el dato OHLCV.
- Las posiciones SELL son cortos teóricos; no se modelan préstamo, financiación ni disponibilidad de acciones.
- Todavía no existe asignación de capital ni límites de cartera. El ledger mide operaciones individuales, no rentabilidad de una cuenta.
- El primer arranque no reconstruye operaciones pasadas. Empieza desde la línea base para que las estadísticas paper sean prospectivas.
- Los resultados son simulados y dependen de la calidad y retraso de Yahoo Finance.

Este módulo está separado del workflow de alertas. No cambia las notificaciones Telegram.
