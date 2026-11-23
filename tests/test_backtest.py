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


    def test_fixed_long_stop_uses_equity_distance(self):
        sample = [
            {"timestamp": 1000, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 4600, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 8200, "open": 100, "high": 101, "low": 98, "close": 99},
            {"timestamp": 11800, "open": 99, "high": 100, "low": 98, "close": 99},
        ]
        trades = backtest.simulate_trades("AAPL", sample, [(0, "BUY")], 0.10, "fixed")
        self.assertEqual(trades[0]["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(float(trades[0]["exit_price"]), 98.5)
        self.assertAlmostEqual(float(trades[0]["target_price"]), 103.0)

    def test_fixed_fx_target_uses_fx_distance(self):
        sample = [
            {"timestamp": 1000, "open": 1.0, "high": 1.001, "low": .999, "close": 1.0},
            {"timestamp": 4600, "open": 1.0, "high": 1.001, "low": .999, "close": 1.0},
            {"timestamp": 8200, "open": 1.0, "high": 1.006, "low": .999, "close": 1.005},
            {"timestamp": 11800, "open": 1.005, "high": 1.006, "low": 1.004, "close": 1.005},
        ]
        trades = backtest.simulate_trades("EURUSD=X", sample, [(0, "BUY")], 0.0, "fixed")
        self.assertEqual(trades[0]["exit_reason"], "TAKE_PROFIT")
        self.assertAlmostEqual(float(trades[0]["exit_price"]), 1.005)

    def test_fixed_short_stop_and_gap_fill(self):
        sample = [
            {"timestamp": 1000, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 4600, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 8200, "open": 103, "high": 104, "low": 102, "close": 103},
            {"timestamp": 11800, "open": 103, "high": 104, "low": 102, "close": 103},
        ]
        trades = backtest.simulate_trades("AAPL", sample, [(0, "SELL")], 0.0, "fixed")
        self.assertEqual(trades[0]["exit_reason"], "STOP_LOSS_GAP")
        self.assertEqual(float(trades[0]["exit_price"]), 103.0)

    def test_stop_wins_when_stop_and_target_hit_same_bar(self):
        sample = [
            {"timestamp": 1000, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 4600, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 8200, "open": 100, "high": 104, "low": 98, "close": 101},
            {"timestamp": 11800, "open": 101, "high": 102, "low": 100, "close": 101},
        ]
        trades = backtest.simulate_trades("AAPL", sample, [(0, "BUY")], 0.0, "fixed")
        self.assertEqual(trades[0]["exit_reason"], "STOP_LOSS")
        self.assertEqual(float(trades[0]["exit_price"]), 98.5)

    def test_macd_baseline_has_no_stop_or_target(self):
        sample = [
            {"timestamp": 1000, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 4600, "open": 100, "high": 101, "low": 99, "close": 100},
            {"timestamp": 8200, "open": 100, "high": 110, "low": 90, "close": 100},
            {"timestamp": 11800, "open": 100, "high": 101, "low": 99, "close": 100},
        ]
        trades = backtest.simulate_trades("AAPL", sample, [(0, "BUY")], 0.0, "macd")
        self.assertEqual(trades[0]["exit_reason"], "END_OF_DATA")


if __name__ == "__main__":
    unittest.main()
