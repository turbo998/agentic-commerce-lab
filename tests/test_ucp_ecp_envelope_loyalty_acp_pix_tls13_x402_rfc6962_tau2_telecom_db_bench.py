"""Unit tests for Stage 107 16-scenario (`EP-01..EP-16`) bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_bench import (
    run_benchmark,
)


class TestStage107Bench(unittest.TestCase):
    def test_stage_107_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["reversal_invariance_passed"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", zh_html)
            self.assertIn("EP-01", zh_html)
            self.assertIn("EP-16", en_html)
            self.assertEqual(zh_html.count('class="card"'), 7)
            self.assertEqual(en_html.count('class="card"'), 7)

    def test_stage_107_default_output_artifacts_exist(self) -> None:
        report = run_benchmark()
        self.assertEqual(report["ai_native_pass_rate"], 1.0)
        base = Path(
            "reports/agentic-commerce-ucp-ecp-envelope-loyalty-acp-pix-tls13-x402-rfc6962-tau2-telecom-db-bench"
        )
        self.assertTrue((base / "report.json").exists())
        self.assertTrue((base / "index.html").exists())
        self.assertTrue((base / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
