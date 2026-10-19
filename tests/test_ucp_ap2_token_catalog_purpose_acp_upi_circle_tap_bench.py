from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.ucp_ap2_token_catalog_purpose_acp_upi_circle_tap_bench import run_stage53_benchmark


class UCPAP2TokenCatalogPurposeACPUPICircleTAPBenchTests(unittest.TestCase):
    def test_stage53_benchmark_generates_16_scenarios_and_7card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_stage53_benchmark(tmp)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 1)

            report_data = json.loads(Path(summary["report_json"]).read_text(encoding="utf-8"))
            self.assertEqual(report_data["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(report_data["classic_3tier_pass_rate_pct"], 6.2)
            self.assertEqual(len(report_data["scenarios"]), 16)

            html_text = Path(summary["report_html"]).read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', html_text)
            self.assertIn("Content-Security-Policy", html_text)

    def test_stage53_all_four_protocol_clusters_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_stage53_benchmark(tmp)
            report_data = json.loads(Path(summary["report_json"]).read_text(encoding="utf-8"))
            ids = [s["scenario_id"] for s in report_data["scenarios"]]
            self.assertEqual(ids[0], "TI-01")
            self.assertEqual(ids[-1], "TI-16")


if __name__ == "__main__":
    unittest.main()
