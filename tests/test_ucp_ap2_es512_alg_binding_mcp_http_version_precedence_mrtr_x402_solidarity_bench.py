"""Unit tests for Stage 185 16-scenario (`ES-01..ES-16`) benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_bench import (
    run_benchmark,
)


class Stage185BenchTests(unittest.TestCase):
    def test_stage185_benchmark_16_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage185"
            summary = run_benchmark(output_dir=out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())
            html_zh = (out_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_zh)
            self.assertIn("ES-16", html_zh)


if __name__ == "__main__":
    unittest.main()
