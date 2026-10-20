"""Unit tests for Stage 91 16-scenario bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_bench import (
    evaluate_benchmark,
    write_benchmark_reports,
)


class TestUcpEcpContextAcpRecurringAddressX402CoopTau2A2aBench(unittest.TestCase):
    def test_evaluate_benchmark_16_scenarios(self) -> None:
        summary = evaluate_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["classic_3tier_pass_rate_pct"], 25.0)
        self.assertEqual(summary["reversal_consistent_count"], 16)
        self.assertEqual(summary["reversal_consistency_pct"], 100.0)

    def test_write_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage91"
            summary = write_benchmark_reports(out_dir)
            self.assertEqual(summary["ai_native_passed"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("EC-16", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("EC-16", en_html)


if __name__ == "__main__":
    unittest.main()
