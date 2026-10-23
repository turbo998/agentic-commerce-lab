"""Unit tests for Stage 207 16-scenario 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_fulfillment_events_constraints_acp_attribution_ttl_x402_pod_ata_mcp_tau2_bench import (
    run_benchmark,
)


class Stage207BenchTest(unittest.TestCase):
    def test_stage_207_benchmark_generates_16_scenarios_and_csp_locked_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = run_benchmark(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["perturbation_consistent"], 16)

            for fname in ("index.html", "index.en.html", "report.json"):
                self.assertTrue((out_dir / fname).exists(), f"Missing {fname}")

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for doc in (zh_html, en_html):
                self.assertIn(
                    "default-src 'none'; style-src 'unsafe-inline'",
                    doc,
                )
                for idx in range(1, 8):
                    self.assertIn(f"<span>{idx} / 7</span>", doc)


if __name__ == "__main__":
    unittest.main()
