import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from portfolio_sim import simulate_portfolio


def trade(symbol, trade_id, ret):
    return {
        "symbol": symbol, "trade_id": trade_id,
        "entry_timestamp_utc": "2026-01-01T10:00:00+00:00",
        "exit_timestamp_utc": "2026-01-01T12:00:00+00:00",
        "entry_price": "100", "stop_price": "99",
        "net_return_pct": str(ret),
    }


class PortfolioSimulationTests(unittest.TestCase):
    def test_risk_sizing_and_exposure_cap(self):
        trades = [trade("AAPL", "a", 3), trade("MSFT", "b", 3), trade("NVDA", "c", -1)]
        result = simulate_portfolio(trades, initial_equity=10000, risk_pct=0.5,
                                    max_exposure_pct=100)
        self.assertEqual(result["closed_trades"], 3)
        self.assertEqual(result["open_positions_at_sample_end"], 0)
        self.assertAlmostEqual(result["final_realized_equity"], 10166.67, places=2)
        self.assertEqual(result["max_gross_exposure_pct_of_equity"], 100)

    def test_non_usd_assets_are_excluded(self):
        result = simulate_portfolio([trade("EURUSD=X", "fx", 2), trade("SAN.MC", "san", 2)])
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["final_realized_equity"], 10000)

    def test_invalid_settings_rejected(self):
        with self.assertRaises(ValueError):
            simulate_portfolio([], risk_pct=0)


if __name__ == "__main__":
    unittest.main()
