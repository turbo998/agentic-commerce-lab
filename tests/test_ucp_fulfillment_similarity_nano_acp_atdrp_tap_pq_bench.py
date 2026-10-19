"""Unit tests for Stage 49 16-scenario benchmark & 7-Card 4:5 visual report."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from lab.ucp_fulfillment_similarity_nano_acp_atdrp_tap_pq_bench import (
    run_ucp_fulfillment_similarity_nano_acp_atdrp_tap_pq_benchmark,
    write_benchmark_artifacts,
)


class Stage49FulfillmentSimilarityNanoACPATDRPTAPPQBenchTest(unittest.TestCase):
    def test_16_scenarios_pass_rate_and_perturbation_stability(self) -> None:
        report = run_ucp_fulfillment_similarity_nano_acp_atdrp_tap_pq_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["perturbation_stability_pct"], 100.0)

    def test_specific_scenario_decision_codes(self) -> None:
        report = run_ucp_fulfillment_similarity_nano_acp_atdrp_tap_pq_benchmark()
        by_id = {s["scenario_id"]: s for s in report["scenarios"]}
        self.assertEqual(
            by_id["FN-01"]["ai_native_decision_code"],
            "ALL_7_STAGE47_48_PROTOCOL_GUARDS_ADMITTED",
        )
        self.assertEqual(
            by_id["FN-02"]["ai_native_decision_code"],
            "CUSTOM_SYNONYM_FOR_WELL_KNOWN_FULFILLMENT_EVENT_BLOCKED",
        )
        self.assertEqual(
            by_id["FN-06"]["ai_native_decision_code"],
            "ALL_ANCHORS_DROPPED_FALLBACK_SEARCH_FORBIDDEN",
        )
        self.assertEqual(
            by_id["FN-07"]["ai_native_decision_code"],
            "NANO_CLIENT_SUBMITTED_BINDING_OVERRIDE_BLOCKED",
        )
        self.assertEqual(
            by_id["FN-10"]["ai_native_decision_code"],
            "SENSITIVE_CREDENTIAL_FIELD_ECHOED_OUTSIDE_DETOKENIZE_BLOCKED",
        )
        self.assertEqual(
            by_id["FN-13"]["ai_native_decision_code"],
            "ATDRP_INSTRUCTION_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN",
        )
        self.assertEqual(
            by_id["FN-16"]["ai_native_decision_code"],
            "VISA_TAP_HYBRID_PQ_DUAL_LEG_OR_LENGTH_BLOCKED",
        )

    def test_write_7card_html_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_benchmark_artifacts(Path(tmp))
            html_text = Path(out["report_html"]).read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", html_text)
            self.assertIn("1 / 7", html_text)
            self.assertIn("7 / 7", html_text)
            self.assertIn("FN-16", html_text)


if __name__ == "__main__":
    unittest.main()
