"""Unit tests for Stage 211 (210-Stage Milestone!) 16-scenario 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_catalog_3ds2_acp_x402_ap2_sedi_x402_stellar_bazaar_mcp_tau2_bench import (
    run_benchmark,
)


class Stage211BenchTests(unittest.TestCase):
    def test_stage_211_benchmark_generates_16_scenarios_and_7_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_invariant_count"], 16)

            for fname in ("report.json", "index.html", "index.en.html"):
                fpath = out_dir / fname
                self.assertTrue(fpath.exists(), f"missing {fname}")

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                for idx in range(1, 8):
                    self.assertIn(f'data-card="{idx}"', html)
                for sc_num in range(1, 17):
                    self.assertIn(f"PR-{sc_num:02d}", html)


if __name__ == "__main__":
    unittest.main()
