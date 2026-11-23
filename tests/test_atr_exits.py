import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atr_exits import atr_levels, calculate_atr


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

    def test_invalid_atr_rejected(self):
        with self.assertRaises(ValueError):
            atr_levels(100, "BUY", 0)


if __name__ == "__main__":
    unittest.main()
