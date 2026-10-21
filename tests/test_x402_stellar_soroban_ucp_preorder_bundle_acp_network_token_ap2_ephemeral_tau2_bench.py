"""Unit test for Stage 167 16-scenario (ST-01..ST-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import pathlib
import unittest

from lab.x402_stellar_soroban_ucp_preorder_bundle_acp_network_token_ap2_ephemeral_tau2_bench import run_benchmark


class Stage167BenchTest(unittest.TestCase):
    def test_stage167_benchmark_generates_16_scenario_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp) / "stage167-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistency_pct"], 100.0)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 17):
                sid = f"ST-{idx:02d}"
                self.assertIn(sid, zh_html)
                self.assertIn(sid, en_html)


if __name__ == "__main__":
    unittest.main()
