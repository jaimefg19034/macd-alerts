import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import macd_alerts


class TelegramQualityMessageTests(unittest.TestCase):
    def test_alert_includes_grade_and_explanation(self):
        quality = {
            "grade": "BUENA", "score": 4.5, "max_score": 6.0,
            "reasons": ["precio alineado con EMA200"],
            "risks": ["RSI alto"],
        }
        message = macd_alerts.format_alert(
            "AAPL", "🟢 COMPRA", 1_700_000_000, 190.0, 1.2, 1.0, 62.0, quality
        )
        self.assertIn("Calidad técnica: BUENA (4.5/6)", message)
        self.assertIn("precio alineado con EMA200", message)
        self.assertIn("Riesgos: RSI alto", message)
        self.assertIn("Confirmación: cierre de vela 1H", message)


if __name__ == "__main__":
    unittest.main()
