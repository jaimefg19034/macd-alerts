# Phase 3 — Risk policy for research and paper trading

## Purpose

Define a transparent first set of stop-loss/take-profit hypotheses before integrating them into the backtester and the prospective paper ledger. These are experimental assumptions, not evidence of profitability or live-trading instructions.

## Initial price-distance rules

| Instrument group | Stop-loss distance | Take-profit distance | Reward/risk |
|---|---:|---:|---:|
| Equities | 1.50% | 3.00% | 2:1 |
| FX pairs (symbols ending in =X) | 0.25% | 0.50% | 2:1 |

Distances are measured from simulated entry price. They are NOT percentages of account equity. Position sizing and portfolio risk limits must be calculated separately.

## Execution rules to implement

1. Entry remains at the next available 1-hour candle open after a completed-candle MACD signal.
2. Stops and targets are checked against subsequent candle OHLC values.
3. If both stop and target are touched in the same hourly candle and lower-timeframe data is unavailable, assume the stop was hit first (conservative ambiguity rule).
4. Gaps through a stop execute at the candle open, not at the stop price.
5. A stop/target exit takes precedence over a later opposite MACD signal if it occurs first.
6. Deduct costs separately. Current 0.10% round-trip cost is only a provisional backtest assumption and is not a verified spread/commission estimate. FX costs must be calibrated separately before results are treated as meaningful.
7. Preserve the existing completed-candle signal convention and avoid lookahead.

## Leverage research policy

- The paper system must not route real orders, connect to a broker, or enable live leverage.
- Report leverage as a separate sensitivity analysis only: 1x, 5x, 10x and 30x hypothetical notional exposure.
- For every scenario, show equity drawdown and loss amplification, and flag that margin close-out, financing, spread widening and slippage are not fully modelled unless explicitly added.
- Do not select 30x as a default. The unleveraged 1x results remain the primary strategy comparison.
- A smaller FX stop is not a reason to increase leverage. Risk per trade must be controlled by position sizing, not by choosing a large leverage multiple.

## Validation requirements

Compare the initial rules with:
- MACD-only exits (baseline);
- fixed stop/target rules above;
- volatility-normalized ATR exits as a later independent experiment.

Use chronological out-of-sample evaluation and report trade count, expectancy, profit factor, maximum drawdown, exposure, turnover, and costs. Do not tune on the final holdout sample.

## Current implementation status

This document records the agreed research assumptions only. The current paper ledger still uses opposite-MACD exits; the stop/target rules and leverage sensitivity report are NOT active until their code, tests, and workflow integration are completed and verified.
