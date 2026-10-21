"""Unit tests for Stage 127 16-scenario bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_delivery_receipt_ingress_id_ucp_registries_headers_stripe_idempotency_mcp_ext_bench import (
    run_stage127_benchmark,
)


class TestStage127Bench(unittest.TestCase):
    def test_stage127_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_stage127_benchmark(output_dir=out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["passed_scenarios"], 16)
            self.assertEqual(report["pass_rate_pct"], 100.0)
            self.assertEqual(report["perturbation_consistency_pct"], 100.0)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("DR-01", zh_html)
            self.assertIn("DR-16", en_html)


if __name__ == "__main__":
    unittest.main()
