"""Unit tests for Stage 290 guards and Stage 291 16-scenario 7-Card 4:5 benchmark (512 zero-overlap PRs across 70 repos)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_solana_mpp_externalid_ap2_credo_ucp_split_visa_mpp_a2a_stripe_mcp_bench import (
    run_stage295_benchmark,
    write_stage291_reports,
)
from lab.x402_solana_mpp_externalid_ap2_credo_ucp_split_visa_mpp_a2a_stripe_mcp_guards import (
    STAGE294_PR_GROUPS,
    STAGE294_SCENARIOS,
    default_attack_And_remediated_payloads,
    evaluate_stage294_scenario,
)


class TestStage294And291GuardsAndBenchmark(unittest.TestCase):
    def test_stage294_pr_groups_cover_512_zero_overlap_prs_across_70_repos(self) -> None:
        self.assertEqual(len(STAGE294_PR_GROUPS), 16)
        all_refs = []
        for gid, refs in STAGE294_PR_GROUPS.items():
            self.assertEqual(len(refs), 32, f"{gid} should have 32 PRs")
            all_refs.extend(refs)
        self.assertEqual(len(all_refs), 512)
        self.assertEqual(len(set(all_refs)), 512)
        repos = {r.split("#")[0] for r in all_refs}
        self.assertEqual(len(repos), 70)

    def test_stage294_all_16_scenarios_block_attacks_and_pass_remediated(self) -> None:
        payloads = default_attack_And_remediated_payloads()
        self.assertEqual(len(STAGE294_SCENARIOS), 16)
        for spec in STAGE294_SCENARIOS:
            sid = spec["id"]
            atk = evaluate_stage294_scenario(sid, payloads[sid]["attack"])
            rem = evaluate_stage294_scenario(sid, payloads[sid]["remediated"])
            self.assertFalse(atk.allowed, f"{sid} attack should be blocked")
            self.assertEqual(atk.decision_code, spec["violation_code"])
            self.assertTrue(rem.allowed, f"{sid} remediated should pass")
            self.assertEqual(len(rem.pr_refs), 32)

    def test_stage295_benchmark_summary_metrics(self) -> None:
        summary = run_stage295_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["attack_blocked"], 16)
        self.assertEqual(summary["remediated_passed"], 16)
        self.assertEqual(summary["perturbation_stable"], 16)
        self.assertEqual(summary["unique_pr_count"], 512)
        self.assertEqual(summary["unique_repo_count"], 70)
        self.assertGreaterEqual(summary["speedup_factor"], 3.5)

    def test_stage295_bilingual_7card_html_and_json_generation(self) -> None:
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
            self.assertEqual(summary["unique_pr_count"], 512)


if __name__ == "__main__":
    unittest.main()
