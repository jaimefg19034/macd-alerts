# Investigación de selección de activos

## Método

Este experimento estudia si conviene reducir el universo de activos sin mirar el resultado fuera de muestra para tomar la decisión.

- Estrategia fija de investigación: MACD 12/26/9, filtro EMA200 + ADX14, stop 1,5 ATR y objetivo 5 ATR.
- Solo el primer 50% de cada histórico se utiliza para seleccionar activos.
- El bloque de desarrollo se divide en tres subventanas cronológicas. Un activo se conserva si tiene al menos 12 operaciones, retorno medio neto positivo al coste supuesto del 0,20%, profit factor de al menos 1 y retorno medio positivo en al menos dos de las tres subventanas.
- Si menos de tres activos superan el filtro, el experimento conserva el universo completo para evitar construir una cartera demasiado concentrada.
- La lista se congela y se evalúa en el 50% posterior, dividido en cuatro ventanas walk-forward. Se comparan el universo completo y el universo seleccionado con costes supuestos del 0,10%, 0,20% y 0,30%.

## Interpretación y límites

El filtro por activo es una regla heurística, no una prueba de que el activo vaya a seguir funcionando. Las muestras por símbolo pueden ser pequeñas y las rentabilidades pasadas no garantizan resultados futuros. La evaluación OOS no se utiliza para volver a seleccionar activos. Se informa de retorno, drawdown, operaciones, profit factor y resultados por ventana para evitar elegir solo por retorno acumulado.

La simulación de cartera está limitada a acciones estadounidenses en USD; FX y SAN.MC aparecen en estadísticas de operaciones, pero no se mezclan en una cartera USD sin conversión de divisa. Los costes son escenarios supuestos, no tarifas verificadas. El mark-to-market usa cierres horarios y no captura el drawdown intrabar.

**Este experimento es solo de investigación. No modifica la lista de Telegram, los avisos, el paper trading ni ejecuta órdenes reales.**
