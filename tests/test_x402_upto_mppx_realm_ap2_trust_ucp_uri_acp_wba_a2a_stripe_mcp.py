"""Unit tests for Stage 288-289 guards and 16-scenario 7-Card 4:5 bilingual benchmark."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from lab.x402_upto_mppx_realm_ap2_trust_ucp_uri_acp_wba_a2a_stripe_mcp_bench import (
    STAGE289_SCENARIOS,
    run_stage289_benchmark,
    write_stage289_reports,
)
from lab.x402_upto_mppx_realm_ap2_trust_ucp_uri_acp_wba_a2a_stripe_mcp_guards import (
    STAGE288_PR_GROUPS,
    evaluate_stage288_scenario,
)


class TestStage288And289GuardsAndBenchmark(unittest.TestCase):
    def test_stage288_pr_groups_cover_448_zero_overlap_prs_across_54_repos(self) -> None:
        self.assertEqual(len(STAGE288_PR_GROUPS), 16)
        seen: set[str] = set()
        repos: set[str] = set()
        for gid, refs in STAGE288_PR_GROUPS.items():
            self.assertEqual(len(refs), 28, f"{gid} should have 28 PRs")
            for ref in refs:
                norm = ref.lower()
                self.assertNotIn(norm, seen, f"Duplicate PR within Stage 288: {ref}")
                seen.add(norm)
                repos.add(norm.split("#")[0])
        self.assertEqual(len(seen), 448)
        self.assertEqual(len(repos), 54)

        # Verify zero overlap against all earlier guard modules in lab/
        pr_pat = re.compile(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)")
        other_prs: set[str] = set()
        for p in Path("lab").glob("*guards.py"):
            if p.name == "x402_upto_mppx_realm_ap2_trust_ucp_uri_acp_wba_a2a_stripe_mcp_guards.py":
                continue
            txt = p.read_text(encoding="utf-8")
            for m in pr_pat.finditer(txt):
                other_prs.add(f"{m.group(1).lower()}#{int(m.group(2))}")
        overlap = seen.intersection(other_prs)
        self.assertEqual(len(overlap), 0, f"Unexpected overlap with earlier stages: {overlap}")

    def test_stage288_all_16_scenarios_block_attacks_and_pass_remediated(self) -> None:
        for spec in STAGE289_SCENARIOS:
            atk = evaluate_stage288_scenario(spec.scenario_id, spec.attack_payload)
            rem = evaluate_stage288_scenario(spec.scenario_id, spec.remediated_payload)
            pert = evaluate_stage288_scenario(spec.scenario_id, spec.perturbed_attack_payload)
            self.assertFalse(atk.passed, f"{spec.scenario_id} attack should be blocked")
            self.assertTrue(rem.passed, f"{spec.scenario_id} remediated should pass")
            self.assertFalse(pert.passed, f"{spec.scenario_id} perturbed attack should be blocked")
            self.assertEqual(len(atk.covered_prs), 28)

    def test_stage289_benchmark_summary_metrics(self) -> None:
        summary = run_stage289_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["total_primary_source_prs"], 448)
        self.assertEqual(summary["unique_upstream_repositories"], 54)
        self.assertEqual(summary["attack_blocked_count"], 16)
        self.assertEqual(summary["remediated_passed_count"], 16)
        self.assertEqual(summary["perturbation_stable_count"], 16)
        self.assertGreater(summary["latency_speedup_x"], 3.5)

    def test_stage289_bilingual_7card_html_and_json_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_stage289_reports(tmp)
            self.assertEqual(summary["attack_block_rate_pct"], 100.0)
            zh_html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            en_html = (Path(tmp) / "index.en.html").read_text(encoding="utf-8")
            for doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", doc)
                self.assertEqual(doc.count('class="card"'), 7)
                self.assertIn("1 / 7", doc)
                self.assertIn("7 / 7", doc)


if __name__ == "__main__":
    unittest.main()
