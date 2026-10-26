"""Unit tests for Stage 340-339 (290 repositories, 512 zero-overlap PRs, 15,494 cumulative PRs)."""

from __future__ import annotations

import unittest

from lab.x402_eip8141_mpp_bench_ap2_uvlock_ucp_freeze_a2a_task_stripe_mcp_bench import REPORT_DIR, run_stage341_benchmark, write_stage341_reports
from lab.x402_eip8141_mpp_bench_ap2_uvlock_ucp_freeze_a2a_task_stripe_mcp_guards import (
    STAGE340_ALL_PRS,
    STAGE340_PR_GROUPS,
    STAGE340_SCENARIO_MAP,
    STAGE340_UNIQUE_REPOS,
    evaluate_stage340_guard,
)


class TestStage340And341(unittest.TestCase):
    def test_stage340_pr_inventory_and_290_repo_milestone(self) -> None:
        self.assertEqual(len(STAGE340_PR_GROUPS), 16)
        self.assertEqual(len(STAGE340_ALL_PRS), 512)
        self.assertEqual(len(STAGE340_UNIQUE_REPOS), 290)
        keys = {f"{p['repo']}#{p['number']}" for p in STAGE340_ALL_PRS}
        self.assertEqual(len(keys), 512)

    def test_stage340_clean_and_adversarial_guards(self) -> None:
        for gid, _, _, _ in STAGE340_SCENARIO_MAP:
            ok = evaluate_stage340_guard(gid, {"signature_bound": True, "schema_valid": True})
            self.assertTrue(ok["accepted"])
            self.assertEqual(ok["action"], "Act automatically")

            bad = evaluate_stage340_guard(
                gid,
                {
                    "signature_bound": False,
                    "replay_detected": True,
                    "stripe_Legacy_api_key_after_2026_10_31": True,
                },
            )
            self.assertFalse(bad["accepted"])
            self.assertEqual(bad["action"], "Send to a human")

    def test_stage341_benchmark_summary_invariants(self) -> None:
        summary = run_stage341_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["total_prs_covered"], 512)
        self.assertEqual(summary["unique_repos_covered"], 290)
        self.assertEqual(summary["cumulative_zero_overlap_prs"], 15494)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["adversarial_intercept_rate_pct"], 100.0)
        self.assertEqual(summary["max_perturbation_delta_pts"], 0.0)

    def test_stage341_bilingual_7card_reports_written(self) -> None:
        summary = write_stage341_reports()
        self.assertEqual(summary["unique_repos_covered"], 290)
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
