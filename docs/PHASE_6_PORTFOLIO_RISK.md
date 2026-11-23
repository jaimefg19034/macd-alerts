# Fase 6 — Simulación de cartera y dimensionamiento por riesgo

## Objetivo

Evitar interpretar la suma de rentabilidades de operaciones aisladas como si fuera el rendimiento de una cuenta real. Esta simulación asigna capital, limita exposición simultánea y calcula una curva de capital realizada.

## Configuración experimental inicial

- Capital inicial de referencia: 10.000 USD.
- Riesgo nominal por operación: 0,5% del capital vigente.
- Exposición bruta máxima: 100% del capital (sin apalancamiento).
- Tamaño teórico: presupuesto de riesgo dividido por la distancia porcentual entre entrada y stop.
- Si varias señales entran en la misma hora, el capital disponible se reparte proporcionalmente entre ellas.
- Las salidas se procesan antes que las entradas que ocurran en el mismo timestamp.
- El resultado neto de cada trade ya resta el coste estimado usado por el backtester.

## Universo

La primera versión solo agrega acciones estadounidenses denominadas en USD. Excluye SAN.MC y los pares EURUSD/EURGBP para no mezclar divisas sin conversión histórica. No se extrapola este resultado a una cartera multimoneda.

## Limitaciones

La curva se actualiza al cerrar operaciones, por lo que el drawdown es realizado y no incluye valoración intradía de posiciones abiertas. Las posiciones cortas son teóricas; no se modelan préstamo de acciones, financiación ni reglas de margen. Un gap puede superar la pérdida prevista por el stop. Capital y riesgo son supuestos de investigación, no parámetros de una cuenta personal.

La simulación es solo para investigación y paper trading. No envía órdenes ni cambia las alertas Telegram.
