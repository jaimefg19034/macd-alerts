import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paper_trading.py"
SPEC = importlib.util.spec_from_file_location("paper_trading", MODULE_PATH)
paper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paper)


def sample_bars():
    return [
        {"timestamp": 1000 + i * 3600, "open": 10.0 + i, "high": 10.1 + i,
         "low": 9.9 + i, "close": 10.0 + i, "volume": 100}
        for i in range(6)
    ]


class PaperTradingTests(unittest.TestCase):
    def test_first_run_sets_baseline_without_backfilling(self):
        state = paper.empty_state()
        trades = []
        created = paper.process_symbol_bars("TEST", sample_bars(), [(1, "BUY")], state, trades)
        self.assertEqual(created, 0)
        self.assertEqual(trades, [])
        self.assertEqual(state["last_processed"]["TEST"], 1000 + 4 * 3600)
        self.assertNotIn("TEST", state["positions"])

    def test_opposite_cross_closes_position_and_opens_reverse(self):
        bars = sample_bars()[:5]
        state = {
            "last_processed": {"TEST": 1000},
            "positions": {},
        }
        trades = []
        created = paper.process_symbol_bars(
            "TEST", bars, [(1, "BUY"), (3, "SELL")], state, trades, 0.10
        )
        self.assertEqual(created, 1)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["direction"], "BUY")
        self.assertEqual(float(trades[0]["entry_price"]), 12.0)
        self.assertEqual(float(trades[0]["exit_price"]), 13.0)
        self.assertEqual(state["positions"]["TEST"]["direction"], "SELL")

    def test_reprocessing_same_candles_does_not_duplicate_trade(self):
        bars = sample_bars()
        state = {"last_processed": {"TEST": 1000}, "positions": {}}
        trades = []
        events = [(1, "BUY"), (3, "SELL")]
        paper.process_symbol_bars("TEST", bars, events, state, trades)
        count = len(trades)
        paper.process_symbol_bars("TEST", bars, events, state, trades)
        self.assertEqual(len(trades), count)

    def test_negative_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            paper.process_symbol_bars("TEST", sample_bars(), [], paper.empty_state(), [], -1)


    def test_fixed_stop_closes_paper_position_on_later_bar(self):
        bars = [
            {"timestamp": 1000, "open": 100, "high": 100.2, "low": 99.8, "close": 100},
            {"timestamp": 4600, "open": 100, "high": 100.2, "low": 99.8, "close": 100},
            {"timestamp": 8200, "open": 100, "high": 100.2, "low": 99.8, "close": 100},
            {"timestamp": 11800, "open": 99, "high": 100, "low": 98, "close": 99},
            {"timestamp": 15400, "open": 99, "high": 99.2, "low": 98.8, "close": 99},
        ]
        state = {"last_processed": {"AAPL": 1000},
                 "last_bar_processed": {"AAPL": 4600}, "positions": {}}
        trades = []
        created = paper.process_symbol_bars("AAPL", bars, [(1, "BUY")], state, trades, 0.10)
        self.assertEqual(created, 1)
        self.assertEqual(trades[0]["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(float(trades[0]["entry_price"]), 100.0)
        self.assertAlmostEqual(float(trades[0]["exit_price"]), 98.5)
        self.assertNotIn("AAPL", state["positions"])

    def test_paper_position_stores_fixed_levels(self):
        bars = sample_bars()[:3]
        state = {"last_processed": {"AAPL": 1000},
                 "last_bar_processed": {"AAPL": 1000}, "positions": {}}
        paper.process_symbol_bars("AAPL", bars, [(1, "BUY")], state, [])
        position = state["positions"]["AAPL"]
        self.assertAlmostEqual(position["stop_price"], 11.82)
        self.assertAlmostEqual(position["target_price"], 12.36)


if __name__ == "__main__":
    unittest.main()
