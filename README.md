# MACD Alerts

Alertas de cruces MACD en velas de **1 hora** para:

- AAPL
- MSFT
- NVDA
- AMZN
- GOOGL
- META
- TSLA
- MRNA
- OCGN — Ocugen
- SAN.MC — Banco Santander (Bolsa de Madrid)
- EURUSD=X — EUR/USD
- EURGBP=X — EUR/GBP
- AMD — Advanced Micro Devices
- AVGO — Broadcom
- MU — Micron Technology
- JPM — JPMorgan Chase
- XOM — Exxon Mobil

## Qué hace

- GitHub Actions comprueba el mercado cada cinco minutos.
- La estrategia actualmente utiliza velas 1H COMPLETADAS; no es una señal intravela ni una confirmación de 10 minutos.
- Calcula MACD estándar (12, 26, 9) y RSI 14.
- Envía una alerta a Telegram cuando MACD cruza la línea de señal al cierre de la vela.
- Registra las señales BUY/SELL en `data/signal_history.csv`.
- Calcula resultados exploratorios a 1, 4 y 24 horas cuando existe un precio suficientemente cercano al horizonte.
- Genera estadísticas agregadas en `data/signal_stats.csv`.
- No envía órdenes reales. El paper trading simulado funciona en un workflow independiente, con ledger en `data/paper_trades.csv` y estado en `data/paper_state.json`.

## Configuración necesaria: Telegram

Esta es la única configuración privada que falta para recibir avisos.

### 1. Crear un bot

1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot`.
3. Sigue los pasos y copia el token que te entregue.
4. Abre el chat con tu nuevo bot y pulsa **Start**.

No publiques ni compartas el token.

### 2. Obtener tu chat ID

1. Con el bot ya iniciado, abre en tu navegador esta dirección, sustituyendo `TU_TOKEN` por el token de BotFather:
   `https://api.telegram.org/botTU_TOKEN/getUpdates`
2. En la respuesta, localiza `"chat":{"id": ...}`. El número es tu chat ID.
3. No compartas públicamente esa respuesta porque contiene información del bot.

### 3. Guardar los secretos en GitHub

En este repositorio entra en:

**Settings → Secrets and variables → Actions → New repository secret**

Crea estos dos secretos, exactamente con estos nombres:

| Nombre | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token de BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat ID |

No pegues esos valores en archivos del repositorio ni en el chat.

### 4. Activar y probar

1. Abre la pestaña **Actions** del repositorio.
2. Si GitHub muestra un aviso para habilitar Actions, acéptalo.
3. Selecciona **MACD hourly alerts**.
4. Pulsa **Run workflow → Run workflow** para hacer la primera comprobación manual.

Después, la comprobación queda programada automáticamente cada cinco minutos.

## Datos y limitaciones

- El sistema usa el endpoint público de gráficos de Yahoo Finance. No requiere una clave de API, pero es una fuente no oficial: puede retrasarse, limitar peticiones o cambiar.
- GitHub Actions tampoco garantiza que una ejecución programada empiece exactamente en el minuto previsto. Comprueba cada cinco minutos y avisa cuando detecta una vela horaria ya cerrada.
- Los resultados pueden diferir de TradingView si su indicador, proveedor de datos, sesión o configuración no coinciden.
- MACD 12/26/9 es una señal técnica, no una garantía ni una recomendación de inversión.


## Investigación cuantitativa

Consulta [docs/PHASE_1_AUDIT.md](docs/PHASE_1_AUDIT.md) para la auditoría de datos, [docs/PHASE_2_BACKTEST.md](docs/PHASE_2_BACKTEST.md) para el backtester y [docs/PAPER_TRADING.md](docs/PAPER_TRADING.md) para el ledger de paper trading. El backtester genera un informe descargable; el paper trading se ejecuta en un workflow independiente y no envía órdenes reales ni mensajes de Telegram.

**Importante:** las estadísticas actuales son preliminares y no demuestran rentabilidad. El coste ida y vuelta del 0,10% es una hipótesis fija, no una cotización real de comisiones y spread.
