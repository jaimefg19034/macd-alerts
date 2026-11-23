import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from asset_selection_research import asset_is_eligible


class AssetSelectionTests(unittest.TestCase):
    def test_requires_minimum_trade_count(self):
        self.assertFalse(asset_is_eligible({
            "trades": 11, "profit_factor": 1.4, "average_net_return_pct": 0.2
        }, 3))

    def test_requires_positive_average_and_two_positive_folds(self):
        base = {"trades": 20, "profit_factor": 1.2, "average_net_return_pct": 0.1}
        self.assertFalse(asset_is_eligible(base, 1))
        self.assertFalse(asset_is_eligible({**base, "average_net_return_pct": -0.1}, 3))

    def test_accepts_consistent_positive_asset(self):
        self.assertTrue(asset_is_eligible({
            "trades": 20, "profit_factor": 1.1, "average_net_return_pct": 0.05
        }, 2))

    def test_infinite_pf_is_not_automatically_rejected(self):
        self.assertTrue(asset_is_eligible({
            "trades": 20, "profit_factor": "INF", "average_net_return_pct": 0.05
        }, 2))


if __name__ == "__main__":
    unittest.main()
