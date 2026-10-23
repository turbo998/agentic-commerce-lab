"""Unit tests for Stage 223 16-scenario 7-Card 4:5 visual benchmark report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.mcp_inspector_registry_go_rust_csharp_java_bench import (
    DEFAULT_OUTPUT_DIR,
    write_stage_223_report,
)


class TestMcpInspectorRegistryGoRustCsharpJavaBench(unittest.TestCase):
    def test_stage_223_benchmark_and_7_card_html_generation(self) -> None:
        report = write_stage_223_report(DEFAULT_OUTPUT_DIR)
        self.assertEqual(report["stage"], 223)
        self.assertEqual(report["guard_stage"], 222)
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["passed_scenarios"], 16)
        self.assertEqual(report["failed_scenarios"], 0)
        self.assertEqual(report["pass_rate_pct"], 100.0)
        self.assertTrue(report["batch_all_passed"])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            write_stage_223_report(tmp_dir)
            zh_html = (tmp_dir / "index.html").read_text(encoding="utf-8")
            en_html = (tmp_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)


if __name__ == "__main__":
    unittest.main()
