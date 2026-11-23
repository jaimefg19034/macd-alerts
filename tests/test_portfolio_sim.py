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

    def test_mark_to_market_drawdown_includes_open_loss(self):
        from datetime import datetime, timezone
        def ts(hour):
            return int(datetime(2026, 1, 1, hour, tzinfo=timezone.utc).timestamp())
        trade_data = trade("AAPL", "mtm", 3)
        trade_data["estimated_round_trip_cost_pct"] = "0.10"
        bars = [
            {"timestamp": ts(9), "close": 100},
            {"timestamp": ts(10), "close": 98},
            {"timestamp": ts(11), "close": 99},
        ]
        result = simulate_portfolio([trade_data], bars_by_symbol={"AAPL": bars})
        self.assertGreater(result["max_mtm_drawdown_pct"], 2.0)
        self.assertGreater(result["max_mtm_drawdown_pct"],
                           result["max_realized_drawdown_pct"])
        self.assertEqual(result["open_positions_at_sample_end"], 0)
        self.assertAlmostEqual(result["final_realized_equity"], 10300.0, places=2)


if __name__ == "__main__":
    unittest.main()
