import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backtest import load_snapshot_bars
from data_snapshot import filename_for_symbol


class DataSnapshotTests(unittest.TestCase):
    def test_filename_is_stable_and_safe(self):
        self.assertEqual(filename_for_symbol("EURUSD=X"), "EURUSD%3DX.json")

    def test_load_snapshot_bars(self):
        bars = [{"timestamp": 1000, "open": 1.0, "high": 1.1,
                 "low": 0.9, "close": 1.05, "volume": 10}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AAPL.json").write_text(json.dumps({"symbol": "AAPL", "bars": bars}))
            (root / "manifest.json").write_text(json.dumps({
                "symbols": {"AAPL": {"file": "AAPL.json", "bar_count": 1}}
            }))
            self.assertEqual(load_snapshot_bars(root, "AAPL"), bars)

    def test_missing_symbol_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(json.dumps({"symbols": {}}))
            with self.assertRaises(FileNotFoundError):
                load_snapshot_bars(root, "AAPL")


if __name__ == "__main__":
    unittest.main()
