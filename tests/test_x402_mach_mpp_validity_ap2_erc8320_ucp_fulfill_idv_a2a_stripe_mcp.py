"""Unit tests for Stage 306 guards and Stage 307 16-scenario 7-Card 4:5 benchmark (512 zero-overlap PRs across 120 repos)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_mach_mpp_validity_ap2_erc8320_ucp_fulfill_idv_a2a_stripe_mcp_bench import (
    run_stage307_benchmark,
    write_stage307_reports,
)
from lab.x402_mach_mpp_validity_ap2_erc8320_ucp_fulfill_idv_a2a_stripe_mcp_guards import (
    STAGE306_PR_GROUPS,
    STAGE306_SCENARIOS,
    default_attack_and_remediated_payloads,
    evaluate_stage306_scenario,
)


class TestStage306And307GuardsAndBenchmark(unittest.TestCase):
    def test_stage306_pr_groups_cover_512_zero_overlap_prs_across_120_repos(self) -> None:
        self.assertEqual(len(STAGE306_PR_GROUPS), 16)
        all_refs = []
        for gid, refs in STAGE306_PR_GROUPS.items():
            self.assertEqual(len(refs), 32, f"{gid} should have 32 PRs")
            all_refs.extend(refs)
        self.assertEqual(len(all_refs), 512)
        self.assertEqual(len(set(all_refs)), 512)
        repos = {r.split("#")[0] for r in all_refs}
        self.assertEqual(len(repos), 120)

    def test_stage306_all_16_scenarios_block_attacks_and_pass_remediated(self) -> None:
        payloads = default_attack_and_remediated_payloads()
        self.assertEqual(len(STAGE306_SCENARIOS), 16)
        for spec in STAGE306_SCENARIOS:
            sid = spec["id"]
            atk = evaluate_stage306_scenario(sid, payloads[sid]["attack"])
            rem = evaluate_stage306_scenario(sid, payloads[sid]["remediated"])
            self.assertFalse(atk.allowed, f"{sid} attack should be blocked")
            self.assertEqual(atk.decision_code, spec["violation_code"])
            self.assertTrue(rem.allowed, f"{sid} remediated should pass")
            self.assertEqual(len(rem.pr_refs), 32)

    def test_stage307_benchmark_summary_metrics(self) -> None:
        summary = run_stage307_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["attack_blocked"], 16)
        self.assertEqual(summary["remediated_passed"], 16)
        self.assertEqual(summary["perturbation_stable"], 16)
        self.assertEqual(summary["unique_pr_count"], 512)
        self.assertEqual(summary["unique_repo_count"], 120)
        self.assertEqual(summary["cumulative_unique_prs"], 7302)
        self.assertGreaterEqual(summary["speedup_factor"], 3.5)

    def test_stage307_bilingual_7card_html_and_json_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage307-bench"
            summary = write_stage307_reports(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f"{k} / 7", zh_html)
                self.assertIn(f"{k} / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertEqual(summary["unique_pr_count"], 512)


if __name__ == "__main__":
    unittest.main()
