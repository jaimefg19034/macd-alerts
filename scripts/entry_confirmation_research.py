#!/usr/bin/env python3
"""Compare causal entry-confirmation filters against the fixed EMA200+ADX, ATR 1.5/5 baseline."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))
import macd_alerts
from atr_research import simulate_atr, split_indices
from backtest import crossover_events, load_snapshot_bars, summarize
from atr_exits import calculate_atr
from portfolio_sim import simulate_portfolio
from strategy_filters import filter_events

BASELINE=(1.5,5.0)
BASE_FILTER="ema_adx"

def confirmed_events(bars, mode):
    """All confirmation values are computed at or before the completed signal candle."""
    raw=filter_events(bars,crossover_events(bars),BASE_FILTER)
    if mode=="baseline": return raw
    closes=[float(x["close"]) for x in bars]
    macd, signal=macd_alerts.calculate_macd(closes)
    hist=[None if m is None or s is None else m-s for m,s in zip(macd,signal)]
    rsi=macd_alerts.calculate_rsi(closes,14)
    ema=macd_alerts.ema(closes,200)
    kept=[]
    for i,side in raw:
        if i<1: continue
        h0,h1=hist[i-1],hist[i]
        if mode in ("histogram","histogram_rsi"):
            if h0 is None or h1 is None: continue
            if side=="BUY" and not (h1>h0): continue
            if side=="SELL" and not (h1<h0): continue
        if mode in ("rsi50","histogram_rsi"):
            r=rsi[i]
            if r is None or (side=="BUY" and r<=50) or (side=="SELL" and r>=50): continue
        if mode=="ema_slope":
            if i<20 or ema[i] is None or ema[i-20] is None: continue
            if side=="BUY" and ema[i]<=ema[i-20]: continue
            if side=="SELL" and ema[i]>=ema[i-20]: continue
        kept.append((i,side))
    return kept

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir",required=True)
    p.add_argument("--costs",nargs="*",type=float,default=[.10,.20,.30])
    p.add_argument("--output",default=str(ROOT/"reports"/"entry_confirmation"/"summary.json"))
    a=p.parse_args()
    if not a.costs or any(x<0 for x in a.costs): p.error("Costs must be non-negative")
    data,errors={},{}
    for sym in macd_alerts.TICKERS:
        try:
            bars=load_snapshot_bars(a.data_dir,sym)
            if len(bars)<300: raise ValueError("Fewer than 300 bars")
            data[sym]=bars
        except Exception as e: errors[sym]=f"{type(e).__name__}: {e}"
        time.sleep(.1)
    if not data: raise RuntimeError("No usable symbols")
    modes=("baseline","histogram","rsi50","ema_slope","histogram_rsi")
    split={s:split_indices(len(b))[1] for s,b in data.items()}
    output={"method":"Same immutable hourly snapshot, same 17-symbol universe, EMA200+ADX baseline filter, fixed ATR 1.5/5 exits; four chronological OOS folds. Confirmation evaluated only at signal close; no parameter fitting.","baseline_filter":BASE_FILTER,"baseline_atr":{"stop":1.5,"target":5.0},"candidate_filters":{"histogram":"BUY: MACD histogram increases vs prior closed candle; SELL: decreases","rsi50":"BUY RSI14>50; SELL RSI14<50","ema_slope":"EMA200 slope over previous 20 closed candles aligned with side","histogram_rsi":"Both histogram and RSI50 confirmations"},"data_errors":errors,"scenarios":{},"folds":{},"limitations":["New snapshot results are not directly comparable with historical +33.77%.","Hypothetical costs, fills and short availability; no live trading.","Each fold is simulated independently; portfolio simulator assumes 0.5% stop risk and 100% max exposure as research conventions."]}
    for mode in modes: output["folds"][mode]={}
    for cost in a.costs:
        all_trades={m:[] for m in modes}
        for f in range(4):
            fold_report={}
            for sym,bars in data.items():
                start,end=split[sym][f]
                prefix=bars[:end]
                for mode in modes:
                    ev=[(i,d) for i,d in confirmed_events(prefix,mode) if start<=i<end-1]
                    trades=simulate_atr(sym,prefix,ev,cost,*BASELINE)
                    for t in trades: t["walk_forward_fold"]=f+1
                    all_trades[mode].extend(trades)
            for mode in modes:
                rows=[t for t in all_trades[mode] if t["walk_forward_fold"]==f+1]
                fold_report[mode]={"statistics":summarize(rows),"portfolio":simulate_portfolio(rows,bars_by_symbol=data)}
                output["folds"][mode][str(f+1)]={"cost":cost,"portfolio_return_pct":fold_report[mode]["portfolio"]["mtm_return_pct"],"max_drawdown_pct":fold_report[mode]["portfolio"]["max_mtm_drawdown_pct"],"trades":len(rows)}
            output["scenarios"][f"cost_{cost:.2f}"]={}
            for mode in modes:
                rows=all_trades[mode]
                output["scenarios"][f"cost_{cost:.2f}"][mode]={"statistics":summarize(rows),"portfolio":simulate_portfolio(rows,bars_by_symbol=data),"fold_returns":{str(f+1):output["folds"][mode][str(f+1)]["portfolio_return_pct"] for f in range(4)}}
        print(f"Completed cost {cost:.2f}")
    target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:{m:v["portfolio"] for m,v in rows.items()} for k,rows in output["scenarios"].items()},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
