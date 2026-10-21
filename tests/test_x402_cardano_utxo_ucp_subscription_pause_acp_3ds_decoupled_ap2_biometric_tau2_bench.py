"""Unit test for Stage 165 16-scenario (CD-01..CD-16) 7-Card 4:5 benchmark report."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from lab.x402_cardano_utxo_ucp_subscription_pause_acp_3ds_decoupled_ap2_biometric_tau2_bench import (
    run_benchmark,
)


class Stage165BenchTest(unittest.TestCase):
    def test_stage165_benchmark_16_scenarios_and_bilingual_7card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistent_count"], 16)
            self.assertEqual(
                [s["scenario_id"] for s in report["scenarios"]],
                [f"CD-{i:02d}" for i in range(1, 17)],
            )
            for fname in ("report.json", "index.html", "index.en.html"):
                self.assertTrue((out_dir / fname).exists(), fname)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f'id="card-{k}"', zh_html)
                self.assertIn(f'id="card-{k}"', en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


if __name__ == "__main__":
    unittest.main()
