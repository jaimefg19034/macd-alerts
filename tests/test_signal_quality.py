import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from signal_quality import assess_signal


class SignalQualityTests(unittest.TestCase):
    def test_strong_aligned_buy_is_very_good(self):
        result = assess_signal("BUY", 110, 100, 30, 60, 0.2, 0.4)
        self.assertEqual(result["grade"], "MUY BUENA")
        self.assertEqual(result["score"], 6.0)

    def test_mixed_conditions_are_normal_or_risky(self):
        result = assess_signal("BUY", 95, 100, 12, 48, 0.4, 0.2)
        self.assertEqual(result["grade"], "ARRIESGADA")
        self.assertTrue(result["risks"])

    def test_extreme_rsi_reduces_buy_score(self):
        moderate = assess_signal("BUY", 110, 100, 25, 60, 0.1, 0.2)
        extreme = assess_signal("BUY", 110, 100, 25, 80, 0.1, 0.2)
        self.assertLess(extreme["score"], moderate["score"])
        self.assertTrue(any("RSI muy alto" in x for x in extreme["risks"]))

    def test_invalid_direction_rejected(self):
        with self.assertRaises(ValueError):
            assess_signal("HOLD", 100, 100, 25, 50, 0, 1)


if __name__ == "__main__":
    unittest.main()
