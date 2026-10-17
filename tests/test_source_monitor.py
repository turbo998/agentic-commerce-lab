"""Offline tests for source provenance and visible fetch failures."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from scripts.source_monitor import (
    MAX_BYTES, Observation, Source, fingerprint, load_sources, main, observe,
    previous_hashes, validate_url,
)


class MonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Source("stripe", "https://docs.stripe.com/mcp", "https://docs.stripe.com/mcp.md")

    def test_normalization_excludes_scripts_and_styles(self) -> None:
        self.assertEqual(
            fingerprint(b"<p>Example  text</p><script>random()</script>", "text/html"),
            fingerprint(b"<style>new-css</style><p>Example text</p>", "text/html"),
        )
        self.assertNotEqual(fingerprint(b"old", "text/plain"), fingerprint(b"new", "text/plain"))
        with self.assertRaises(ValueError):
            fingerprint(b"<script>only-script</script>", "text/html")

    def test_failure_is_not_unchanged(self) -> None:
        with patch("scripts.source_monitor.urlopen", side_effect=URLError("offline")):
            observation = observe(self.source, "old-hash")
        self.assertEqual(observation.status, "error")
        self.assertEqual(observation.change, "unknown")
        self.assertIsNone(observation.sha256)
        self.assertIn("offline", observation.error)

    def test_baseline_unchanged_and_changed(self) -> None:
        response = MagicMock()
        response.geturl.return_value = self.source.monitor_url
        response.read.return_value = b"source text"
        response.headers.get.return_value = "text/plain"
        response.__enter__.return_value = response
        digest = fingerprint(b"source text", "text/plain")
        with patch("scripts.source_monitor.urlopen", return_value=response):
            self.assertEqual(observe(self.source, None).change, "baseline")
            self.assertEqual(observe(self.source, digest).change, "unchanged")
            self.assertEqual(observe(self.source, "older").change, "changed")
            response.read.return_value = b"x" * (MAX_BYTES + 1)
            self.assertEqual(observe(self.source, digest).status, "error")

    def test_registry_and_url_validation(self) -> None:
        validate_url("https://learn.microsoft.com/en-us/azure/well-architected/ai/application-design")
        for url in [
            "http://docs.stripe.com/mcp", "https://docs.stripe.com.evil.example",
            "https://user:secret@docs.stripe.com/mcp", "https://127.0.0.1/",
            "https://docs.stripe.com:8080/",
            "https://learn.microsoft.com.evil.example/",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps({"sources": [
                {"id": "duplicate", "url": self.source.url},
                {"id": "duplicate", "url": self.source.url},
            ]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_sources(path)

    def test_failed_day_retains_previous_success(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for date, status, digest in [
                ("2026-10-09", "ok", "previous"), ("2026-10-10", "error", None)
            ]:
                (root / f"{date}-sources.json").write_text(json.dumps({"observations": [
                    {"id": "stripe", "status": status, "sha256": digest}
                ]}), encoding="utf-8")
            self.assertEqual(previous_hashes(root), {"stripe": "previous"})
            self.assertEqual(previous_hashes(root, before_date="2026-10-09"), {})
            self.assertEqual(previous_hashes(root, before_date="2026-10-10"), {"stripe": "previous"})

    def test_checked_registry_loads(self) -> None:
        sources = load_sources(Path("research") / "sources.json")
        self.assertGreaterEqual(len(sources), 10)

    def test_generated_example_expiry_changes_hash_not_product_claim(self) -> None:
        first = fingerprint(b'{"expires_at": 1794406247}', "text/plain")
        second = fingerprint(b'{"expires_at": 1794406248}', "text/plain")
        self.assertNotEqual(first, second)

    def test_main_records_failure_and_returns_nonzero(self) -> None:
        failure = Observation(
            self.source.id, self.source.url, self.source.monitor_url,
            "error", None, "unknown", "URLError: offline",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = ["monitor", "--output-dir", str(root)]
            with (
                patch("sys.argv", arguments),
                patch("scripts.source_monitor.load_sources", return_value=[self.source]),
                patch("scripts.source_monitor.observe", return_value=failure),
                self.assertLogs(level="INFO"),
            ):
                self.assertEqual(main(), 1)
            reports = list(root.glob("*-sources.json"))
            self.assertEqual(len(reports), 1)
            report = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertTrue(report["checked_at"].endswith("+08:00"))
            self.assertEqual(report["observations"][0]["change"], "unknown")
            self.assertFalse(list(root.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
