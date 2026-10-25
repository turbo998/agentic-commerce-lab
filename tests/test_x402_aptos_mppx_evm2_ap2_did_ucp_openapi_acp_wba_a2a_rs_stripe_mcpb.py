"""Unit tests for Stage 290 guards and Stage 291 16-scenario 7-Card 4:5 benchmark (480 zero-overlap PRs across 60 repos)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_aptos_mppx_evm2_ap2_did_ucp_openapi_acp_wba_a2a_rs_stripe_mcpb_bench import (
    run_stage291_benchmark,
    write_stage291_reports,
)
from lab.x402_aptos_mppx_evm2_ap2_did_ucp_openapi_acp_wba_a2a_rs_stripe_mcpb_guards import (
    STAGE290_PR_GROUPS,
    STAGE290_SCENARIOS,
    default_attack_And_remediated_payloads,
    evaluate_stage290_scenario,
)


class TestStage290And291GuardsAndBenchmark(unittest.TestCase):
    def test_stage290_pr_groups_cover_480_zero_overlap_prs_across_60_repos(self) -> None:
        self.assertEqual(len(STAGE290_PR_GROUPS), 16)
        all_refs = []
        for gid, refs in STAGE290_PR_GROUPS.items():
            self.assertEqual(len(refs), 30, f"{gid} should have 30 PRs")
            all_refs.extend(refs)
        self.assertEqual(len(all_refs), 480)
        self.assertEqual(len(set(all_refs)), 480)
        repos = {r.split("#")[0] for r in all_refs}
        self.assertEqual(len(repos), 60)

    def test_stage290_all_16_scenarios_block_attacks_and_pass_remediated(self) -> None:
        payloads = default_attack_And_remediated_payloads()
        self.assertEqual(len(STAGE290_SCENARIOS), 16)
        for spec in STAGE290_SCENARIOS:
            sid = spec["id"]
            atk = evaluate_stage290_scenario(sid, payloads[sid]["attack"])
            rem = evaluate_stage290_scenario(sid, payloads[sid]["remediated"])
            self.assertFalse(atk.allowed, f"{sid} attack should be blocked")
            self.assertEqual(atk.decision_code, spec["violation_code"])
            self.assertTrue(rem.allowed, f"{sid} remediated should pass")
            self.assertEqual(len(rem.pr_refs), 30)

    def test_stage291_benchmark_summary_metrics(self) -> None:
        summary = run_stage291_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["attack_blocked"], 16)
        self.assertEqual(summary["remediated_passed"], 16)
        self.assertEqual(summary["perturbation_stable"], 16)
        self.assertEqual(summary["unique_pr_count"], 480)
        self.assertEqual(summary["unique_repo_count"], 60)
        self.assertGreaterEqual(summary["speedup_factor"], 3.5)

    def test_stage291_bilingual_7card_html_and_json_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage291-bench"
            summary = write_stage291_reports(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f"{k} / 7", zh_html)
                self.assertIn(f"{k} / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertEqual(summary["unique_pr_count"], 480)


if __name__ == "__main__":
    unittest.main()
