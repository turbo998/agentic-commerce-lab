"""Unit tests for Stage 608 guards and Stage 609 7-Card 4:5 benchmark report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_erc9250_mpp_geminicloudmcp_ap2_llmpipeline_ucp_datafluxpy_a2a_gcpdiag_stripe_mcp_bench import (
    render_stage609_cards_html,
    run_stage609_benchmark,
    write_stage609_artifacts,
)
from lab.x402_erc9250_mpp_geminicloudmcp_ap2_llmpipeline_ucp_datafluxpy_a2a_gcpdiag_stripe_mcp_guards import (
    STAGE608_ALL_PRS,
    STAGE608_PR_GROUPS,
    STAGE608_PR_REFS,
    STAGE608_SCENARIO_MAP,
    STAGE608_UNIQUE_REPOS,
    evaluate_stage608_guard,
)


class TestStage560And545(unittest.TestCase):
    def test_stage608_pr_inventory_and_zero_overlap_within_stage(self) -> None:
        self.assertEqual(len(STAGE608_PR_GROUPS), 16)
        self.assertEqual(len(STAGE608_ALL_PRS), 512)
        self.assertEqual(len(STAGE608_PR_REFS), 512)
        self.assertEqual(len(set(STAGE608_PR_REFS)), 512)
        self.assertEqual(len(STAGE608_UNIQUE_REPOS), 512)
        for gid, prs in STAGE608_PR_GROUPS.items():
            self.assertEqual(len(prs), 32, f"{gid} must have 32 PRs")

    def test_stage608_guard_evaluation_and_adversarial_escalation(self) -> None:
        clean = evaluate_stage608_guard("PR-01", {"signature_bound": True})
        self.assertTrue(clean["accepted"])
        self.assertEqual(clean["action"], "Act automatically")
        self.assertEqual(clean["pr_count"], 32)
        self.assertEqual(clean["repo_count"], 32)

        single_fault = evaluate_stage608_guard("PR-09", {"replay_detected": True})
        self.assertFalse(single_fault["accepted"])
        self.assertEqual(single_fault["action"], "Confirm")

        dual_fault = evaluate_stage608_guard(
            "PR-15",
            {
                "signature_bound": False,
                "stripe_Legacy_api_key_after_2026_10_31": True,
            },
        )
        self.assertFalse(dual_fault["accepted"])
        self.assertEqual(dual_fault["action"], "Send to a human")

    def test_stage609_benchmark_and_option_reversal_invariance(self) -> None:
        summary = run_stage609_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["total_prs"], 512)
        self.assertEqual(summary["unique_prs"], 512)
        self.assertEqual(summary["unique_repos"], 512)
        self.assertEqual(summary["max_perturbation_delta_pts"], 0.0)
        self.assertEqual(len(STAGE608_SCENARIO_MAP), 16)

    def test_stage609_seven_card_html_and_artifacts(self) -> None:
        summary = run_stage609_benchmark()
        zh_html = render_stage609_cards_html(summary, lang="zh")
        en_html = render_stage609_cards_html(summary, lang="en")
        for idx in range(1, 8):
            self.assertIn(f'id="card-{idx}"', zh_html)
            self.assertIn(f"{idx} / 7", zh_html)
            self.assertIn(f'id="card-{idx}"', en_html)
            self.assertIn(f"{idx} / 7", en_html)
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_stage609_artifacts(Path(tmp))
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["zh_html"].exists())
            self.assertTrue(paths["en_html"].exists())


if __name__ == "__main__":
    unittest.main()
