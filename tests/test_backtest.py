import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backtest.py"
SPEC = importlib.util.spec_from_file_location("backtest", MODULE_PATH)
backtest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backtest)


def bars():
    return [
        {"timestamp": 1000 + i * 3600, "open": 10.0 + i, "high": 11.0 + i,
         "low": 9.0 + i, "close": 10.0 + i, "volume": 100}
        for i in range(6)
    ]


class BacktestExecutionTests(unittest.TestCase):
    def test_entry_occurs_on_next_bar_not_signal_close(self):
        trades = backtest.simulate_trades("TEST", bars(), [(1, "BUY"), (3, "SELL")], 0.10)
        self.assertEqual(len(trades), 2)
        self.assertEqual(float(trades[0]["entry_price"]), 12.0)
        self.assertEqual(trades[0]["exit_reason"], "OPPOSITE_MACD_CROSS")
        self.assertEqual(float(trades[0]["exit_price"]), 14.0)
        self.assertAlmostEqual(float(trades[0]["net_return_pct"]), (14 / 12 - 1) * 100 - 0.10, places=6)

    def test_open_trade_is_closed_at_last_close_and_flagged(self):
        trades = backtest.simulate_trades("TEST", bars(), [(1, "BUY")], 0.10)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["exit_reason"], "END_OF_DATA")
        self.assertEqual(float(trades[0]["entry_price"]), 12.0)
        self.assertEqual(float(trades[0]["exit_price"]), 15.0)

    def test_same_direction_signal_does_not_duplicate_position(self):
        trades = backtest.simulate_trades("TEST", bars(), [(1, "BUY"), (2, "BUY")], 0.10)
        self.assertEqual(len(trades), 1)

    def test_negative_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            backtest.simulate_trades("TEST", bars(), [], -0.1)

    def test_summary_handles_empty_sample(self):
        result = backtest.summarize([])
        self.assertEqual(result["trades"], 0)
        self.assertIsNone(result["win_rate_pct"])


if __name__ == "__main__":
    unittest.main()
