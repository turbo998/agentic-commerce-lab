"""Unit tests for Stage 225 (225-Stage Milestone!) 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_conformance_js_sdk_mcp_csharp_kotlin_swift_bench import run_benchmark


class TestStage225Benchmark(unittest.TestCase):
    def test_benchmark_generates_16_of_16_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage225"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_passed"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)


if __name__ == "__main__":
    unittest.main()
