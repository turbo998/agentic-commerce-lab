"""Unit tests for Stage 251 UCP Schema, JS SDK, Python SDK, and Conformance 7-Card Benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_schema_strict_allof_js_py_sdk_conformance_bench import (
    run_ucp_schema_strict_allof_js_py_sdk_conformance_benchmark,
)


class TestUcpSchemaStrictAllofJsPySdkConformanceBench(unittest.TestCase):
    def test_benchmark_16_scenarios_and_perturbation_invariance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_ucp_schema_strict_allof_js_py_sdk_conformance_benchmark(tmp)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(report["perturbation_consistent_count"], 16)
            self.assertEqual(report["perturbation_consistency_pct"], 100.0)

    def test_benchmark_renders_csp_compliant_bilingual_7_card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_ucp_schema_strict_allof_js_py_sdk_conformance_benchmark(tmp)
            zh_html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            en_html = (Path(tmp) / "index.en.html").read_text(encoding="utf-8")
            for doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", doc)
                self.assertIn("1 / 7", doc)
                self.assertIn("7 / 7", doc)
                self.assertIn("PR-01", doc)
                self.assertIn("PR-16", doc)


if __name__ == "__main__":
    unittest.main()
