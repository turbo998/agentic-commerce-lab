"""Unit tests for Stage 139 16-scenario benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_escaped_path_caip2_pending_ucp_fees_order_currency_mcp_audit_streaming_bench import (
    run_benchmark,
)


class Stage139BenchTests(unittest.TestCase):
    def test_stage139_benchmark_generates_16_scenario_bilingual_7card_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            summary = run_benchmark(out)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["perturbation_consistent_count"], 16)
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "index.en.html").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("EP-16", zh_html)


if __name__ == "__main__":
    unittest.main()
