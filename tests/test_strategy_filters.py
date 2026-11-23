import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "strategy_filters.py"
SPEC = importlib.util.spec_from_file_location("strategy_filters", MODULE_PATH)
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)


def rising_bars(n=240):
    return [
        {"timestamp": 1000 + i * 3600, "open": 100 + i, "high": 101 + i,
         "low": 99 + i, "close": 100.5 + i, "volume": 1000}
        for i in range(n)
    ]


class StrategyFilterTests(unittest.TestCase):
    def test_adx_detects_persistent_trend(self):
        values = filters.calculate_adx(rising_bars(), 14)
        self.assertIsNone(values[26])
        self.assertIsNotNone(values[27])
        self.assertGreater(values[-1], 90)

    def test_ema200_keeps_long_in_uptrend(self):
        bars = rising_bars()
        self.assertEqual(filters.filter_events(bars, [(220, "BUY")], "ema200"), [(220, "BUY")])
        self.assertEqual(filters.filter_events(bars, [(220, "SELL")], "ema200"), [])

    def test_none_mode_preserves_all_events(self):
        events = [(10, "BUY"), (20, "SELL")]
        self.assertEqual(filters.filter_events(rising_bars(), events, "none"), events)

    def test_combined_filter_accepts_aligned_trend_and_momentum(self):
        bars = rising_bars()
        self.assertEqual(filters.filter_events(
            bars, [(220, "BUY")], "ema_adx_rsi", 20
        ), [(220, "BUY")])

    def test_invalid_filter_mode_rejected(self):
        with self.assertRaises(ValueError):
            filters.filter_events(rising_bars(), [], "magical")

    def test_invalid_adx_threshold_rejected(self):
        with self.assertRaises(ValueError):
            filters.filter_events(rising_bars(), [], "ema_adx", 101)


if __name__ == "__main__":
    unittest.main()
