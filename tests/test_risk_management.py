import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "risk_management.py"
SPEC = importlib.util.spec_from_file_location("risk_management", PATH)
risk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(risk)


class RiskManagementTests(unittest.TestCase):
    def test_equity_and_fx_parameters(self):
        self.assertEqual(risk.risk_parameters("AAPL"), (1.5, 3.0))
        self.assertEqual(risk.risk_parameters("EURUSD=X"), (0.25, 0.5))

    def test_long_and_short_levels(self):
        self.assertEqual(risk.levels(100, "BUY", 1.5, 3), (98.5, 103))
        self.assertEqual(risk.levels(100, "SELL", 1.5, 3), (101.5, 97))

    def test_stop_wins_if_both_levels_touched(self):
        bar = {"open": 100, "high": 104, "low": 98}
        self.assertEqual(risk.check_exit(bar, "BUY", 98.5, 103), ("STOP_LOSS", 98.5))

    def test_gap_executes_at_open(self):
        bar = {"open": 97, "high": 99, "low": 96}
        self.assertEqual(risk.check_exit(bar, "BUY", 98.5, 103), ("STOP_LOSS_GAP", 97))

    def test_leverage_amplifies_both_directions(self):
        self.assertAlmostEqual(risk.leverage_sensitivity(0.25, 10), 2.5)
        self.assertAlmostEqual(risk.leverage_sensitivity(-0.25, 30), -7.5)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            risk.levels(100, "BUY", 0, 2)
        with self.assertRaises(ValueError):
            risk.leverage_sensitivity(1, 0)


if __name__ == "__main__":
    unittest.main()
