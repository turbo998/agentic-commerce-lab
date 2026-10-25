"""Unit tests for Stage 233 7-Card 4:5 benchmark suite (880-Test Milestone)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_evm_exact_neo_offer_receipt_v2_ucp_py_sdk_conformance_mcp_sdks_bench import (
    run_benchmark,
)


class Stage233BenchmarkTest(unittest.TestCase):
    """Verify Stage 233 16-scenario benchmark report and CSP-locked 7-Card HTML."""

    def test_run_benchmark_produces_16_of_16_pass_and_perturbation_invariance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["stage"], "Stage 233")
            self.assertEqual(report["milestone"], "880-Test Milestone")
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistent_count"], 16)
            self.assertTrue((out_dir / "report.json").exists())

    def test_bilingual_html_decks_contain_7_cards_and_strict_csp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            run_benchmark(out_dir)
            for name in ("index.html", "index.en.html"):
                text = (out_dir / name).read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", text)
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', text)


if __name__ == "__main__":
    unittest.main()
