"""Unit tests for Stage 342-339 (300 repositories, 512 zero-overlap PRs, 15,494 cumulative PRs)."""

from __future__ import annotations

import unittest

from lab.x402_caip217_mpp_warden_ap2_ledger_ucp_appliesto_a2a_interceptor_stripe_mcp_bench import REPORT_DIR, run_stage343_benchmark, write_stage343_reports
from lab.x402_caip217_mpp_warden_ap2_ledger_ucp_appliesto_a2a_interceptor_stripe_mcp_guards import (
    STAGE342_ALL_PRS,
    STAGE342_PR_GROUPS,
    STAGE342_SCENARIO_MAP,
    STAGE342_UNIQUE_REPOS,
    evaluate_stage342_guard,
)


class TestStage342And343(unittest.TestCase):
    def test_stage342_pr_inventory_and_300_repo_milestone(self) -> None:
        self.assertEqual(len(STAGE342_PR_GROUPS), 16)
        self.assertEqual(len(STAGE342_ALL_PRS), 512)
        self.assertEqual(len(STAGE342_UNIQUE_REPOS), 300)
        keys = {f"{p['repo']}#{p['number']}" for p in STAGE342_ALL_PRS}
        self.assertEqual(len(keys), 512)

    def test_stage342_clean_and_adversarial_guards(self) -> None:
        for gid, _, _, _ in STAGE342_SCENARIO_MAP:
            ok = evaluate_stage342_guard(gid, {"signature_bound": True, "schema_valid": True})
            self.assertTrue(ok["accepted"])
            self.assertEqual(ok["action"], "Act automatically")

            bad = evaluate_stage342_guard(
                gid,
                {
                    "signature_bound": False,
                    "replay_detected": True,
                    "stripe_Legacy_api_key_after_2026_10_31": True,
                },
            )
            self.assertFalse(bad["accepted"])
            self.assertEqual(bad["action"], "Send to a human")

    def test_stage343_benchmark_summary_invariants(self) -> None:
        summary = run_stage343_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["total_prs_covered"], 512)
        self.assertEqual(summary["unique_repos_covered"], 300)
        self.assertEqual(summary["cumulative_zero_overlap_prs"], 15494)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["adversarial_intercept_rate_pct"], 100.0)
        self.assertEqual(summary["max_perturbation_delta_pts"], 0.0)

    def test_stage343_bilingual_7card_reports_written(self) -> None:
        summary = write_stage343_reports()
        self.assertEqual(summary["unique_repos_covered"], 300)
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
