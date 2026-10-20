"""Unit tests for Stage 89 (`IO-01..IO-16`) bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_bench import (
    build_scenarios,
    run_benchmark,
)


class TestStage89IdentityOauthAcpExtX402Eip712Tau2MultilingualBench(unittest.TestCase):
    def test_scenarios_count_and_ids(self) -> None:
        scenarios = build_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertEqual(
            [s["scenario_id"] for s in scenarios],
            [f"IO-{i:02d}" for i in range(1, 17)],
        )

    def test_run_benchmark_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage89-report"
            report = run_benchmark(output_dir=out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate"], 100.0)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["classic_3tier_pass_rate"], 25.0)
            self.assertEqual(report["reversal_consistent"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7 · HANDS-ON", zh_html)
            self.assertIn("7 / 7 · MY TAKE", zh_html)
            self.assertIn("content=\"default-src 'none'; style-src 'unsafe-inline'\"", zh_html)
            self.assertIn("1 / 7 · HANDS-ON", en_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)
            self.assertIn("content=\"default-src 'none'; style-src 'unsafe-inline'\"", en_html)


if __name__ == "__main__":
    unittest.main()
