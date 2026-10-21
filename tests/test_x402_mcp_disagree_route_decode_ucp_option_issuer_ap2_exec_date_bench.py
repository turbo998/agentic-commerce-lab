import tempfile
import unittest
from pathlib import Path

from lab.x402_mcp_disagree_route_decode_ucp_option_issuer_ap2_exec_date_bench import (
    run_benchmark,
)


class TestStage143Benchmark(unittest.TestCase):
    def test_stage143_benchmark_generates_16_passed_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(output_dir=out_dir)
            self.assertEqual(report["summary"]["total"], 16)
            self.assertEqual(report["summary"]["passed"], 16)
            self.assertEqual(report["summary"]["pass_rate_pct"], 100.0)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("MD-01", zh_html)
            self.assertIn("MD-16", en_html)


if __name__ == "__main__":
    unittest.main()
