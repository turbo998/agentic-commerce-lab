from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_batch_total_claimed_mcp_mismatch_ucp_lodging_vat_mcp_provenance_bench import (
    run_stage133_benchmark,
)


class Stage133BenchmarkTests(unittest.TestCase):
    def test_stage133_benchmark_generates_16_scenarios_and_bilingual_7card_deck(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage133-report"
            report = run_stage133_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(
                [s["scenario_id"] for s in report["scenarios"]],
                [f"TC-{i:02d}" for i in range(1, 17)],
            )
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("Content-Security-Policy", en_html)


if __name__ == "__main__":
    unittest.main()
