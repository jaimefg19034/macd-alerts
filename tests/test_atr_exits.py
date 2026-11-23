import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atr_exits import atr_levels, calculate_atr
from backtest import simulate_trades


class ATRExitTests(unittest.TestCase):
    def test_atr_warmup_and_wilder_update(self):
        bars = [
            {"high": 11, "low": 9, "close": 10},
            {"high": 12, "low": 10, "close": 11},
            {"high": 13, "low": 11, "close": 12},
            {"high": 14, "low": 12, "close": 13},
        ]
        values = calculate_atr(bars, 2)
        self.assertIsNone(values[0])
        self.assertIsNone(values[1])
        self.assertAlmostEqual(values[2], 2.0)
        self.assertAlmostEqual(values[3], 2.0)

    def test_atr_levels_long_and_short(self):
        self.assertEqual(atr_levels(100, "BUY", 2), (97.0, 106.0))
        self.assertEqual(atr_levels(100, "SELL", 2), (103.0, 94.0))


    def test_backtest_uses_signal_candle_atr_and_checks_after_entry(self):
        bars = [
            {"timestamp": 1000 + i * 3600, "open": 100, "high": 101,
             "low": 99, "close": 100, "volume": 100}
            for i in range(17)
        ]
        # ATR(14) is 2.0 at signal candle 14; entry is candle 15.
        bars[16]["high"] = 107
        trades = simulate_trades("AAPL", bars, [(14, "BUY")], 0.0, "atr")
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["exit_reason"], "TAKE_PROFIT")
        self.assertAlmostEqual(float(trades[0]["stop_price"]), 97.0)
        self.assertAlmostEqual(float(trades[0]["target_price"]), 106.0)

    def test_invalid_atr_rejected(self):
        with self.assertRaises(ValueError):
            atr_levels(100, "BUY", 0)


if __name__ == "__main__":
    unittest.main()
