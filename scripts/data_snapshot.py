#!/usr/bin/env python3
"""Download one immutable hourly OHLCV snapshot for comparable research runs."""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import macd_alerts

DEFAULT_LOOKBACK_DAYS = 700


def filename_for_symbol(symbol: str) -> str:
    return quote(symbol, safe="") + ".json"


def create_snapshot(symbols: list[str], lookback_days: int, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": macd_alerts.DATA_SOURCE,
        "interval": "60m",
        "lookback_days_requested": lookback_days,
        "symbols": {},
        "errors": {},
    }
    for symbol in symbols:
        try:
            bars = macd_alerts.get_hourly_bars(symbol, lookback_days=lookback_days)
            filename = filename_for_symbol(symbol)
            (output_dir / filename).write_text(
                json.dumps({"symbol": symbol, "bars": bars}, separators=(",", ":")),
                encoding="utf-8",
            )
            manifest["symbols"][symbol] = {
                "file": filename,
                "bar_count": len(bars),
                "first_timestamp": int(bars[0]["timestamp"]),
                "last_timestamp": int(bars[-1]["timestamp"]),
            }
            print(f"{symbol}: {len(bars)} velas guardadas en {filename}")
        except Exception as exc:
            manifest["errors"][symbol] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR {symbol}: {manifest['errors'][symbol]}", file=sys.stderr)
        time.sleep(0.35)

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*", default=list(macd_alerts.TICKERS))
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--output-dir", default=str(ROOT / "reports" / "data_snapshot"))
    args = parser.parse_args()
    if args.lookback_days < 30:
        parser.error("lookback-days must be at least 30")
    manifest = create_snapshot(args.symbols, args.lookback_days, Path(args.output_dir))
    print(f"Snapshot: {len(manifest['symbols'])} activos; errores: {len(manifest['errors'])}")
    return 1 if not manifest["symbols"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
