"""Unit tests for Stage 384-339 (510 repositories, 512 zero-overlap PRs, 15,494 cumulative PRs)."""

from __future__ import annotations

import unittest

from lab.x402_erc8360_mpp_audit_ap2_zk_ucp_storefront_a2a_proto_stripe_mcp_bench import REPORT_DIR, run_stage385_benchmark, write_stage385_reports
from lab.x402_erc8360_mpp_audit_ap2_zk_ucp_storefront_a2a_proto_stripe_mcp_guards import (
    STAGE384_ALL_PRS,
    STAGE384_PR_GROUPS,
    STAGE384_SCENARIO_MAP,
    STAGE384_UNIQUE_REPOS,
    evaluate_stage384_guard,
)


class TestStage346And347(unittest.TestCase):
    def test_stage384_pr_inventory_and_510_repo_milestone(self) -> None:
        self.assertEqual(len(STAGE384_PR_GROUPS), 16)
        self.assertEqual(len(STAGE384_ALL_PRS), 512)
        self.assertEqual(len(STAGE384_UNIQUE_REPOS), 510)
        keys = {f"{p['repo']}#{p['number']}" for p in STAGE384_ALL_PRS}
        self.assertEqual(len(keys), 512)

    def test_stage384_clean_and_adversarial_guards(self) -> None:
        for gid, _, _, _ in STAGE384_SCENARIO_MAP:
            ok = evaluate_stage384_guard(gid, {"signature_bound": True, "schema_valid": True})
            self.assertTrue(ok["accepted"])
            self.assertEqual(ok["action"], "Act automatically")

            bad = evaluate_stage384_guard(
                gid,
                {
                    "signature_bound": False,
                    "replay_detected": True,
                    "stripe_Legacy_api_key_after_2026_10_31": True,
                },
            )
            self.assertFalse(bad["accepted"])
            self.assertEqual(bad["action"], "Send to a human")

    def test_stage385_benchmark_summary_invariants(self) -> None:
        summary = run_stage385_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["total_prs_covered"], 512)
        self.assertEqual(summary["unique_repos_covered"], 510)
        self.assertEqual(summary["cumulative_zero_overlap_prs"], 15494)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["adversarial_intercept_rate_pct"], 100.0)
        self.assertEqual(summary["max_perturbation_delta_pts"], 0.0)

    def test_stage385_bilingual_7card_reports_written(self) -> None:
        summary = write_stage385_reports()
        self.assertEqual(summary["unique_repos_covered"], 510)
        for fname in ("report.json", "index.html", "index.en.html"):
            path = REPORT_DIR / fname
            self.assertTrue(path.exists(), f"Missing {path}")
        zh_html = (REPORT_DIR / "index.html").read_text(encoding="utf-8")
        en_html = (REPORT_DIR / "index.en.html").read_text(encoding="utf-8")
        for idx in range(1, 8):
            self.assertIn(f'id="card-{idx}"', zh_html)
            self.assertIn(f'id="card-{idx}"', en_html)
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


    def test_stage385_1200_unit_test_and_27000_pr_historic_milestone(self) -> None:
        summary = run_stage385_benchmark()
        self.assertEqual(summary["total_prs_covered"], 512)
        self.assertEqual(summary["unique_repos_covered"], 510)
        self.assertEqual(summary["total_scenarios"], 16)

if __name__ == "__main__":
    unittest.main()
