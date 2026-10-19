"""Unit tests for Stage 33-34 16-scenario 7-Card 4:5 visual benchmark report."""

from pathlib import Path
import tempfile
import unittest

from lab.protocol_v02_sovereign_cbdc_bench import run_protocol_v02_sovereign_cbdc_benchmark


class ProtocolV02SovereignCBDCBenchTests(unittest.TestCase):
    def test_benchmark_generates_16_scenarios_and_7_card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "protocol-v02-cbdc-bench"
            summary = run_protocol_v02_sovereign_cbdc_benchmark(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 1)
            self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(summary["reverse_order_consistency_pct"], 100.0)

            json_path = out_dir / "report.json"
            html_path = out_dir / "index.html"
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path.exists())
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_text)
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', html_text)


if __name__ == "__main__":
    unittest.main()
