import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atr_research import split_indices, simulate_atr, rank_candidate


class ATRResearchTests(unittest.TestCase):
    def test_split_reserves_first_half_for_development(self):
        dev, folds = split_indices(1000)
        self.assertEqual(dev, 500)
        self.assertEqual(folds[0][0], 500)
        self.assertEqual(folds[-1][1], 1000)

    def test_variable_atr_multiples_are_applied(self):
        bars = []
        for i in range(40):
            p = 100.0
            bars.append({"timestamp": 1000+i*3600, "open": p, "high": p+1,
                         "low": p-1, "close": p, "volume": 100})
        # The entry follows the signal candle; a narrow stop is hit on the next candle.
        bars[16]["low"] = 95.0
        trades = simulate_atr("AAPL", bars, [(14, "BUY")], 0.0, 1.0, 2.0)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(float(trades[0]["stop_price"]), 98.0)

    def test_candidates_below_minimum_sample_are_ineligible(self):
        result = rank_candidate([])
        self.assertFalse(result["eligible"])
        self.assertIsNone(result["selection_score"])


if __name__ == "__main__":
    unittest.main()
