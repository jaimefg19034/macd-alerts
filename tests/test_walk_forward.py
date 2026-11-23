import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from walk_forward import buy_hold_benchmark, split_walk_forward


class WalkForwardSplitTests(unittest.TestCase):
    def test_four_chronological_folds_cover_out_of_sample_half(self):
        folds = split_walk_forward(1000)
        self.assertEqual(len(folds), 4)
        self.assertEqual(folds[0][0], 500)
        self.assertEqual(folds[-1][1], 1000)
        for left, right in zip(folds, folds[1:]):
            self.assertEqual(left[1], right[0])
        self.assertTrue(all(start < end for start, end in folds))

    def test_buy_hold_benchmark_uses_usd_equities_only(self):
        bars = [
            {"open": 100, "close": 100},
            {"open": 100, "close": 101},
            {"open": 100, "close": 105},
            {"open": 110, "close": 110},
        ]
        result = buy_hold_benchmark({"AAPL": bars, "SAN.MC": bars})
        self.assertEqual(result["symbols"], {"AAPL": 10.0})
        self.assertEqual(result["equal_weight_return_pct"], 10.0)

    def test_invalid_splits_rejected(self):
        with self.assertRaises(ValueError):
            split_walk_forward(10)
        with self.assertRaises(ValueError):
            split_walk_forward(100, warmup_fraction=1.0)


if __name__ == "__main__":
    unittest.main()
