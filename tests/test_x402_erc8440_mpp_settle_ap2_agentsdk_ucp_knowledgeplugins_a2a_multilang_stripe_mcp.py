"""Unit tests for Stage 400-339 (512 repositories, 512 zero-overlap PRs, 15,494 cumulative PRs)."""

from __future__ import annotations

import unittest

from lab.x402_erc8440_mpp_settle_ap2_agentsdk_ucp_knowledgeplugins_a2a_multilang_stripe_mcp_bench import REPORT_DIR, run_stage401_benchmark, write_stage401_reports
from lab.x402_erc8440_mpp_settle_ap2_agentsdk_ucp_knowledgeplugins_a2a_multilang_stripe_mcp_guards import (
    STAGE400_ALL_PRS,
    STAGE400_PR_GROUPS,
    STAGE400_SCENARIO_MAP,
    STAGE400_UNIQUE_REPOS,
    evaluate_stage400_guard,
)


class TestStage346And347(unittest.TestCase):
    def test_stage400_pr_inventory_and_512_repo_milestone(self) -> None:
        self.assertEqual(len(STAGE400_PR_GROUPS), 16)
        self.assertEqual(len(STAGE400_ALL_PRS), 512)
        self.assertEqual(len(STAGE400_UNIQUE_REPOS), 512)
        keys = {f"{p['repo']}#{p['number']}" for p in STAGE400_ALL_PRS}
        self.assertEqual(len(keys), 512)

    def test_stage400_clean_and_adversarial_guards(self) -> None:
        for gid, _, _, _ in STAGE400_SCENARIO_MAP:
            ok = evaluate_stage400_guard(gid, {"signature_bound": True, "schema_valid": True})
            self.assertTrue(ok["accepted"])
            self.assertEqual(ok["action"], "Act automatically")

            bad = evaluate_stage400_guard(
                gid,
                {
                    "signature_bound": False,
                    "replay_detected": True,
                    "stripe_Legacy_api_key_after_2026_10_31": True,
                },
            )
            self.assertFalse(bad["accepted"])
            self.assertEqual(bad["action"], "Send to a human")

    def test_stage401_benchmark_summary_invariants(self) -> None:
        summary = run_stage401_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["total_prs_covered"], 512)
        self.assertEqual(summary["unique_repos_covered"], 512)
        self.assertEqual(summary["cumulative_zero_overlap_prs"], 15494)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["adversarial_intercept_rate_pct"], 100.0)
        self.assertEqual(summary["max_perturbation_delta_pts"], 0.0)

    def test_stage401_bilingual_7card_reports_written(self) -> None:
        summary = write_stage401_reports()
        self.assertEqual(summary["unique_repos_covered"], 512)
        for fname in ("report.json", "index.html", "index.en.html"):
            path = REPORT_DIR / fname
            self.assertTrue(path.exists(), f"Missing {path}")
        zh_html = (REPORT_DIR / "index.html").read_text(encoding="utf-8")
        en_html = (REPORT_DIR / "index.en.html").read_text(encoding="utf-8")
        for idx in range(1, 8):
            self.assertIn(f'id="card-{idx}"', zh_html)
            self.assertIn(f'id="card-{idx}"', en_html)
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


if __name__ == "__main__":
    unittest.main()
