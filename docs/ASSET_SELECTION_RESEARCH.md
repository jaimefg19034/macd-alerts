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


## Primera ejecución y resultados (23-11-2026)

El workflow terminó correctamente: [ejecución de GitHub Actions](https://github.com/jaimefg19034/macd-alerts/actions/runs/45266192426). Se descargó una única captura de datos para los 17 símbolos; la selección se hizo sobre el primer 50% y la evaluación sobre el 50% posterior.

**Universo seleccionado en desarrollo:** AMD, AVGO, GOOGL, JPM, META, MSFT y NVDA.

**Apartados por el filtro de desarrollo:** AAPL, AMZN, EURGBP=X, EURUSD=X, MRNA, MU, OCGN, SAN.MC, TSLA y XOM.

| Métrica OOS | Universo completo | Universo seleccionado |
|---|---:|---:|
| Operaciones al coste 0,20% | 443 | 247 |
| Acierto | 27,07% | 29,46% |
| Profit factor | 1,1678 | 1,2533 |
| Retorno cartera MTM al 0,20% | +24,41% | +19,96% |
| Drawdown MTM al 0,20% | 13,56% | 9,37% |

| Coste supuesto | Universo completo | Universo seleccionado |
|---|---:|---:|
| 0,10% | +35,64% | +28,35% |
| 0,20% | +24,41% | +19,96% |
| 0,30% | +14,12% | +12,13% |

Retorno MTM por ventana al coste principal del 0,20%:

| Ventana | Universo completo | Universo seleccionado |
|---|---:|---:|
| 1 | -1,41% | -5,01% |
| 2 | +17,94% | +14,12% |
| 3 | +5,82% | +2,58% |
| 4 | +1,10% | +7,88% |

**Conclusión:** la selección mejora la calidad estadística de las operaciones y reduce el drawdown, pero baja la rentabilidad acumulada OOS del +24,41% al +19,96%. Por tanto, no es una mejora en rentabilidad absoluta ni alcanza el objetivo de +40%. Es una cartera más selectiva y con menor drawdown en esta muestra, pero sigue teniendo una primera ventana negativa. No sería correcto afirmar que ya hemos encontrado la selección definitiva.

El filtro apartó MRNA y MU por resultados inconsistentes o negativos en desarrollo, aunque ambos habían aparecido fuertes en pruebas anteriores. TSLA no superó el requisito de consistencia entre subventanas. FX y SAN.MC tampoco superaron el filtro y, además, no forman parte de la cartera USD simulada. Los activos apartados quedan excluidos de esta variante de investigación, no borrados del proyecto.

**Decisión de alcance:** la lista de siete activos queda como universo candidato de la variante de investigación. No se ha cambiado la lista de símbolos de los avisos de Telegram ni el paper trading automático: antes de trasladar una exclusión a esos sistemas necesitamos más de un bloque temporal y seguimiento prospectivo. El resultado completo y la captura exacta están en el artefacto `development-only-asset-selection` de la ejecución enlazada arriba.
