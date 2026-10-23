"""Unit tests for Stage 175 benchmark suite (`lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench.py`)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench import (
    run_benchmark,
)


class TestStage175Bench(unittest.TestCase):
    def test_stage_175_benchmark_and_7card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = run_benchmark(out)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["perturbation_consistent"], 16)
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertEqual(zh_html.count('<section class="card">'), 7)
            self.assertEqual(en_html.count('<section class="card">'), 7)


if __name__ == "__main__":
    unittest.main()
