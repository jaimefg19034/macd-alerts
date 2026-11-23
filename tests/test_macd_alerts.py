import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "macd_alerts.py"
SPEC = importlib.util.spec_from_file_location("macd_alerts", MODULE_PATH)
macd_alerts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(macd_alerts)


class IndicatorTests(unittest.TestCase):
    def test_ema_uses_sma_seed(self):
        result = macd_alerts.ema([1, 2, 3, 4], 3)
        self.assertEqual(result[:2], [None, None])
        self.assertAlmostEqual(result[2], 2.0)
        self.assertAlmostEqual(result[3], 3.0)

    def test_rsi_is_bounded(self):
        values = macd_alerts.calculate_rsi([float(x) for x in range(20)], 14)
        self.assertTrue(all(value is None or 0 <= value <= 100 for value in values))
        self.assertEqual(values[-1], 100.0)

    def test_macd_and_signal_have_same_length(self):
        closes = [100 + i * 0.2 for i in range(80)]
        macd, signal = macd_alerts.calculate_macd(closes)
        self.assertEqual(len(macd), len(closes))
        self.assertEqual(len(signal), len(closes))
        self.assertIsNotNone(macd[-1])
        self.assertIsNotNone(signal[-1])


class SignalRecordTests(unittest.TestCase):
    def setUp(self):
        self.bar = {
            "timestamp": 1_000_000,
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 12345,
        }

    def test_signal_has_stable_unique_identifier_and_snapshot(self):
        history = []
        macd_alerts.record_signal(history, "AAPL", "BUY", self.bar, 103.0, 55.0, 1.2, 1.0)
        row = history[0]
        expected = f"{macd_alerts.STRATEGY_ID}:AAPL:BUY:1000000"
        self.assertEqual(row["signal_id"], expected)
        self.assertEqual(row["strategy_version"], macd_alerts.STRATEGY_VERSION)
        self.assertEqual(float(row["candle_high"]), 105.0)
        self.assertEqual(row["candle_volume"], "12345")

    def test_signal_identifier_changes_with_direction_or_candle(self):
        history = []
        macd_alerts.record_signal(history, "AAPL", "BUY", self.bar, 103.0, 55.0, 1.2, 1.0)
        other = dict(self.bar, timestamp=1_003_600)
        macd_alerts.record_signal(history, "AAPL", "SELL", other, 103.0, 45.0, 0.8, 1.0)
        self.assertNotEqual(history[0]["signal_id"], history[1]["signal_id"])

    def test_recording_same_signal_twice_is_idempotent(self):
        history = []
        for _ in range(2):
            macd_alerts.record_signal(
                history, "AAPL", "BUY", self.bar, 103.0, 55.0, 1.2, 1.0
            )
        self.assertEqual(len(history), 1)


class OutcomeTests(unittest.TestCase):
    def make_row(self, direction="BUY"):
        return {
            "symbol": "TEST",
            "direction": direction,
            "candle_timestamp": "100000",
            "entry_price": "100",
            "return_1h_pct": "",
            "return_4h_pct": "",
            "return_24h_pct": "",
        }

    def test_buy_and_sell_returns_are_directional(self):
        buy = self.make_row("BUY")
        sell = self.make_row("SELL")
        bars = [
            {"timestamp": 103600, "close": 110.0},
            {"timestamp": 114400, "close": 90.0},
        ]
        macd_alerts.update_signal_outcomes([buy, sell], "TEST", bars)
        self.assertAlmostEqual(float(buy["return_1h_pct"]), 10.0)
        self.assertAlmostEqual(float(sell["return_1h_pct"]), (100.0 / 110.0 - 1.0) * 100.0, places=6)
        self.assertAlmostEqual(float(buy["net_return_1h_pct"]), 9.9)

    def test_late_weekend_like_observation_is_not_mislabelled(self):
        row = self.make_row()
        # Target for 24h is 190000; this close is 53h after entry close.
        bars = [{"timestamp": 290800, "close": 105.0}]
        macd_alerts.update_signal_outcomes([row], "TEST", bars)
        self.assertEqual(row["return_24h_pct"], "")

    def test_missing_future_data_stays_blank(self):
        row = self.make_row()
        macd_alerts.update_signal_outcomes([row], "TEST", [])
        self.assertEqual(row["return_1h_pct"], "")


if __name__ == "__main__":
    unittest.main()
