"""Unit tests for Stage 183 16-scenario (`DS-01..DS-16`) benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_bench import (
    run_benchmark,
)


class TestStage183Bench(unittest.TestCase):
    def test_benchmark_16_of_16_and_7_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = run_benchmark(out)
            self.assertEqual(report["summary"]["total_scenarios"], 16)
            self.assertEqual(report["summary"]["passed_scenarios"], 16)
            self.assertEqual(report["summary"]["pass_rate_pct"], 100.0)
            self.assertEqual(report["summary"]["perturbation_drift_pts"], 0.0)

            for fname in ("report.json", "index.html", "index.en.html"):
                self.assertTrue((out / fname).exists(), fname)

            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)


if __name__ == "__main__":
    unittest.main()
