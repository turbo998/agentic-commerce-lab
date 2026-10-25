"""Unit tests for Stage 247 16-scenario 7-Card 4:5 visual benchmark runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.mcp_inspector_oauth_ssrf_load_swift_ruby_php_kotlin_bench import run_benchmark


class TestStage247InspectorAndMultiSdkBenchmark(unittest.TestCase):
    def test_benchmark_16_scenarios_all_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage247-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate"], 1.0)
            self.assertEqual(report["classic_3tier_passed"], 3)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())

    def test_7card_html_csp_and_bilingual_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage247-html"
            run_benchmark(out_dir)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            saved = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved["scenarios"]), 16)
            for doc in (zh_html, en_html):
                self.assertIn(
                    "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                    doc,
                )
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7 ·", doc)


if __name__ == "__main__":
    unittest.main()
