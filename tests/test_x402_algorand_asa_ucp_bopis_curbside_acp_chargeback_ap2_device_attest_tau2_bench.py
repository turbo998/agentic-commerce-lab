"""Unit test for Stage 163 16-scenario (`AR-01..AR-16`) 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_algorand_asa_ucp_bopis_curbside_acp_chargeback_ap2_device_attest_tau2_bench import (
    write_Save_artifacts,
)


class Stage163BenchTests(unittest.TestCase):
    def test_generate_stage163_benchmark_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = write_Save_artifacts(out_dir)
            totals = report["totals"]
            self.assertEqual(totals["scenarios_total"], 16)
            self.assertEqual(totals["ai_native_passed"], 16)
            self.assertEqual(totals["classic_3tier_passed"], 0)
            self.assertEqual(totals["perturbation_consistent"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("AR-01", zh_html)
            self.assertIn("AR-16", en_html)


if __name__ == "__main__":
    unittest.main()
