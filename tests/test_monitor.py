import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from scripts.daily_monitor import MAX_BYTES, digest, fetch, main, observe, report


class MonitorTests(unittest.TestCase):
    sources = [{"id": "official", "url": "https://example.com/docs"}]

    def test_whitespace_and_scripts_do_not_change_digest(self):
        self.assertEqual(
            digest(b"<p>Hello world</p><script>old()</script>", "text/html"),
            digest(b"<p>Hello   world</p><script>new()</script>", "text/html"),
        )

    def test_visible_changes_are_detected(self):
        self.assertNotEqual(digest(b"old", "text/plain"), digest(b"new", "text/plain"))

    def test_empty_content_fails(self):
        with self.assertRaises(ValueError):
            digest(b"<script>ignored()</script>", "text/html")

    def test_new_unchanged_and_changed(self):
        for baseline, status in (
            ({}, "new_baseline"), ({"official": "new"}, "unchanged"), ({"official": "old"}, "changed")
        ):
            with self.subTest(status=status):
                observations, state = observe(self.sources, baseline, lambda _: "new")
                self.assertEqual(observations[0]["status"], status)
                self.assertEqual(state["official"], "new")
                self.assertIn("not verified releases", report("2026-10-10", self.sources, observations))

    def test_errors_preserve_baseline_and_redact_details(self):
        for error in (
            URLError("sensitive response text"),
            HTTPError("https://example.com", 403, "private", {}, None),
            TimeoutError("private"),
        ):
            def fail(_):
                raise error
            with self.subTest(error=error):
                observations, state = observe(self.sources, {"official": "old"}, fail)
                self.assertEqual(state, {"official": "old"})
                self.assertEqual(observations[0]["status"], "error")
                self.assertNotIn("private", str(observations))
                self.assertNotIn("sensitive", str(observations))

    def test_insecure_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            fetch({"url": "http://example.com"})

    def test_oversized_response_and_insecure_redirect_are_rejected(self):
        for url, body in (
            ("https://example.com", b"x" * (MAX_BYTES + 1)),
            ("http://example.com", b"hello"),
        ):
            with self.subTest(url=url), patch("scripts.daily_monitor.urlopen") as opener:
                response = opener.return_value.__enter__.return_value
                response.url = url
                response.read.return_value = body
                with self.assertRaises(ValueError):
                    fetch({"url": "https://example.com"})

    def test_cli_preserves_failed_observations_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources.json"
            state = root / "state.json"
            output = root / "observations"
            sources.write_text(json.dumps(self.sources), encoding="utf-8")
            state.write_text('{"official": "accepted"}', encoding="utf-8")
            args = [
                "monitor", "--sources", str(sources), "--state", str(state),
                "--output", str(output), "--date", "2026-10-10",
            ]
            with patch("sys.argv", args), patch(
                "scripts.daily_monitor.urlopen", side_effect=URLError("private")
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            observations = json.loads((output / "2026-10-10.json").read_text())
            self.assertEqual(observations[0]["status"], "error")
            self.assertEqual(json.loads(state.read_text()), {"official": "accepted"})
            self.assertTrue((output / "2026-10-10.md").is_file())

    def test_source_registry(self):
        sources = json.loads(Path("research/sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len({source["id"] for source in sources}), len(sources))
        for source in sources:
            with self.subTest(source=source["id"]):
                self.assertTrue(source["url"].startswith("https://"))
                self.assertTrue(source.get("monitor_url", source["url"]).startswith("https://"))
                self.assertIn(source["kind"], {"announcement", "documentation", "reference_code", "specification"})


if __name__ == "__main__":
    unittest.main()
