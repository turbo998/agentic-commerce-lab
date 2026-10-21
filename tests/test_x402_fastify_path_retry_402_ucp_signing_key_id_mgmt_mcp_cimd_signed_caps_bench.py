"""Unit test for Stage 137 16-scenario (FP-01..FP-16) bilingual 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_fastify_path_retry_402_ucp_signing_key_id_mgmt_mcp_cimd_signed_caps_bench import (
    run_stage137_benchmark,
)


class Stage137BenchTest(unittest.TestCase):
    """Verify Stage 137 benchmark scenarios and bilingual 7-Card 4:5 HTML output."""

    def test_stage137_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage137"
            report = run_stage137_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["scenarios"][0]["scenario_id"], "FP-01")
            self.assertEqual(report["scenarios"][-1]["scenario_id"], "FP-16")

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)


if __name__ == "__main__":
    unittest.main()
