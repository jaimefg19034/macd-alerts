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
- SAN.MC — Banco Santander (Bolsa de Madrid)
- EURUSD=X — EUR/USD
- EURGBP=X — EUR/GBP

## Qué hace

- GitHub Actions comprueba si hay nuevas velas de una hora cada cinco minutos.
- Solo analiza velas que ya han terminado.
- Calcula MACD estándar: EMA 12 menos EMA 26, y línea de señal EMA 9.
- Envía una alerta a Telegram si, al cierre de una vela, MACD cruza por encima o por debajo de la línea de señal.
- En Santander muestra el precio en EUR; en EUR/USD y EUR/GBP muestra la cotización con cinco decimales.
- Guarda qué velas ha procesado para evitar repetir señales.
- No compra ni vende acciones: solo envía avisos.

La primera ejecución guarda una referencia inicial y no manda señales históricas.

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
