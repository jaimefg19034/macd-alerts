# Fase 1 — Auditoría y especificación de datos

Fecha de auditoría: 2026-11-23

## Objetivo

Construir una base de datos fiable para investigar la estrategia MACD 1H y, más adelante, alimentar un backtester y un motor de paper trading. En esta fase no se cambian las reglas de entrada ni se envían órdenes reales.

## Estado observado en el repositorio

- Script principal: `scripts/macd_alerts.py`.
- Universo actual: 17 símbolos (9 acciones iniciales incluyendo OCGN, SAN.MC, EURUSD=X, EURGBP=X, AMD, AVGO, MU, JPM y XOM).
- Regla actual del código: MACD estándar 12/26/9 sobre velas de 1 hora COMPLETADAS.
- El programa calcula RSI 14 y registra señales BUY/SELL al cierre de la vela de señal.
- Archivos existentes: `data/signal_history.csv`, `data/signal_stats.csv` y `data/pending_crosses.json`.
- El histórico consultado en esta auditoría contenía 15 señales. Es una muestra demasiado pequeña para afirmar que existe ventaja estadística.

## Hallazgo corregido

El código anterior podía etiquetar como resultado de 24 horas una cotización tomada 53 o 71 horas después, por cierres de mercado o fines de semana. Ahora solo registra un resultado si encuentra un cierre dentro de la hora posterior al horizonte solicitado. Si no existe una observación suficientemente cercana, deja el resultado vacío. Es preferible tener un dato ausente que uno mal etiquetado.

## Convenciones actuales de evaluación

- Entrada de referencia: cierre de la vela 1H que genera la señal.
- Horizontes: 1, 4 y 24 horas de tiempo transcurrido.
- BUY: retorno porcentual del precio futuro frente al precio de entrada.
- SELL: retorno inverso, antes de costes.
- Coste actual de referencia: 0,10% ida y vuelta, fijo y provisional.
- El sistema no ejecuta operaciones reales.

Estas convenciones deben conservarse como baseline para que los cambios futuros puedan compararse de forma justa. El coste fijo no debe interpretarse como estimación exacta para cada activo.

## Limitaciones conocidas que no se deben ocultar

1. El precio de entrada al cierre de la vela es una convención de investigación; una ejecución real o simulada después de recibir una alerta puede obtener un precio distinto.
2. Los retornos por señal no equivalen a una curva de capital de cartera: puede haber operaciones simultáneas y exposición solapada.
3. El drawdown de las estadísticas actuales es una secuencia de retornos de señales, no un drawdown de cartera con asignación de capital.
4. La fuente de precios es el endpoint público no oficial de Yahoo Finance; puede tener retrasos, huecos, límites o cambios.
5. Las señales de acciones tecnológicas pueden estar correlacionadas; 17 símbolos no equivalen a 17 fuentes independientes de riesgo.
6. Las métricas actuales son exploratorias. No justifican operar con dinero real.

## Esquema mínimo que debe conservar cada señal

- Identidad: símbolo, dirección, timestamp UTC de la vela, timestamp local legible.
- Versión: nombre/versión de estrategia y fuente de datos.
- Entrada: precio de referencia y convención de entrada.
- Contexto: MACD, línea de señal, histograma y RSI 14.
- Resultados: retorno bruto/neto, precio de salida, hora real de observación y horas transcurridas para cada horizonte.
- Calidad del dato: horizonte válido o ausente; nunca sustituir una observación tardía como si fuera puntual.

## Próximas extensiones de Fase 1

1. Versionar explícitamente la estrategia y las convenciones de entrada/costes.
2. Añadir OHLCV y características calculadas en el momento de la señal, sin introducir todavía filtros en las entradas.
3. Separar el registro de señales del libro de operaciones simuladas.
4. Crear un ledger de paper trading con identificador único, entrada simulada, salida, costes, tamaño, P&L y estado.
5. Añadir pruebas automáticas para evitar duplicados, datos ausentes, velas incompletas y horizontes mal medidos.

## Regla de investigación

No optimizar parámetros sobre toda la muestra. Se mantendrá una estrategia baseline, se registrarán las modificaciones por versión y las mejoras se evaluarán en periodos que no se hayan utilizado para ajustarlas. Cualquier coste, spread, slippage o regla de ejecución debe quedar explícito.
