"""Unit test for Stage 227 16-scenario 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_schema_openapi_mcp_apps_auth_conformance_ruby_php_bench import (
    run_stage227_benchmark,
)


class TestStage227Benchmark(unittest.TestCase):
    def test_benchmark_generates_16_of_16_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage227"
            report = run_stage227_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_passed"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("7 / 7 · MY TAKE", zh_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)


if __name__ == "__main__":
    unittest.main()
