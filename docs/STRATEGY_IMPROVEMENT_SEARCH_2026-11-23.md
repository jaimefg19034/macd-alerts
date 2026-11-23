# Estrategia: búsqueda de mejoras frente a la configuración original

Fecha: 23-11-2026  
Workflow: [Strategy improvement search](https://github.com/jaimefg19034/macd-alerts/actions/runs/45271671364)  
Artefacto con snapshot y resultados: [strategy-improvement-search](https://github.com/jaimefg19034/macd-alerts/actions/runs/45271671364/artifacts/14866185967)

## Regla de aceptación

La configuración original no se sustituye salvo que un candidato supere la rentabilidad OOS de la referencia tanto con costes estimados de 0,10% como de 0,20% por operación (ida y vuelta), y que el drawdown máximo MTM al 0,20% no empeore más de 2 puntos porcentuales. El candidato se selecciona exclusivamente con el primer 50% de datos; la segunda mitad se mantiene como OOS y se divide en cuatro bloques cronológicos.

## Primera búsqueda

Se evaluaron 48 combinaciones: tres filtros (`ema200`, `ema_adx`, `ema_adx_rsi`), cuatro stops ATR (1,0; 1,5; 2,0; 2,5) y cuatro objetivos ATR (2; 3; 4; 5). Coste de desarrollo: 0,20%.

Mejor configuración en desarrollo:
- Filtro: EMA200
- Stop: 1,5 ATR
- Objetivo: 5 ATR
- Operaciones en desarrollo: 951
- Win rate: 24,71%
- Retorno neto medio por operación: 0,05764%
- Profit factor: 1,0506

La configuración original que se usó como referencia en la misma muestra OOS es EMA200 + ADX14, stop 1,5 ATR y objetivo 5 ATR.

## Resultado OOS en la misma captura

Rentabilidad de cartera con capital inicial de 10.000 USD, riesgo teórico del 0,5% por operación y exposición bruta máxima del 100%. El universo de cartera incluye únicamente acciones estadounidenses denominadas en USD; SAN.MC y los pares FX se excluyen de la simulación de cartera.

| Coste ida y vuelta | Original EMA200+ADX | Candidato EMA200 | Diferencia |
|---|---:|---:|---:|
| 0,10% | **+29,1542%** | +20,3639% | -8,7903 pp |
| 0,20% | **+18,6055%** | +9,6231% | -8,9824 pp |
| 0,30% | Resultado no destacado | -0,1420% | — |

Drawdown máximo MTM al 0,20%:
- Original: 14,0303%
- Candidato: 19,4929% (+5,4626 puntos porcentuales)

El candidato no supera la rentabilidad de referencia a ninguno de los dos costes principales y además aumenta el drawdown más de lo permitido. **Rechazado.**

## Decisión

Se conserva la configuración original: universo de 17 activos, filtro EMA200 + ADX14, stop 1,5 ATR y objetivo 5 ATR. No se modifica la estrategia operativa, los avisos de Telegram ni el paper trading.

Nota importante: en la comparación histórica anterior, la configuración original obtuvo +33,77% al coste de 0,10% y +22,60% al 0,20%. Esta nueva ejecución utiliza una captura horaria reciente distinta; por ello, su referencia correcta para comparar candidatos dentro de esta búsqueda es +29,1542% / +18,6055%, no las cifras del snapshot anterior. No deben mezclarse periodos distintos.

## Limitaciones

Es una búsqueda exploratoria, no evidencia de rentabilidad futura. El candidato se elige entre 48 combinaciones y puede estar sobreajustado al bloque de desarrollo. El bloque OOS es un único tramo histórico; hace falta validación walk-forward adicional y paper trading prospectivo antes de considerar cualquier cambio. Los costes son supuestos y la simulación simplifica gaps, disponibilidad de cortos, financiación y drawdown intrabar.
