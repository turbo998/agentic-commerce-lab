"""Unit test for Stage 151 16-scenario (RL-01..RL-16) bilingual 7-Card benchmark."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.x402_replay_lnbtc_ucp_digital_dest_acp_seller_ap2_trust_tau2_bench import run_benchmark


class Stage151BenchmarkTests(unittest.TestCase):
    def test_stage151_benchmark_generates_16_scenario_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage151-bench"
            summary = run_benchmark(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["perturbation_consistent_count"], 16)

            data = json.loads(Path(summary["report_json"]).read_text(encoding="utf-8"))
            self.assertEqual(len(data["scenarios"]), 16)
            self.assertEqual(data["scenarios"][0]["id"], "RL-01")
            self.assertEqual(data["scenarios"][-1]["id"], "RL-16")

            zh_html = Path(summary["report_html_zh"]).read_text(encoding="utf-8")
            en_html = Path(summary["report_html_en"]).read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)


if __name__ == "__main__":
    unittest.main()
