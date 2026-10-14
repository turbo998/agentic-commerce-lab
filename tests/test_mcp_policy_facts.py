"""Synthetic document regressions; no credentials, network or payment authority."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from scripts.source_monitor import (
    Source, fingerprint, main, mcp_policy_facts, observe, previous_policy_facts,
)

# Only the short, publicly documented notice grammar is exercised, not a page copy.
NOTICE = (
    "> #### Update API key authentication by 31 October 2026\n>\n"
    "> Beginning 31 October 2026, Stripe MCP no longer accepts full-access secret keys "
    "or restricted API keys without the Agent tag. Before then, replace these keys with "
    "newly created Agent Keys or reconnect with OAuth. Requests using an unsupported key "
    "receive a `401` response with an OAuth discovery challenge.\n\n"
    "## Tools\nSynthetic unrelated content.\n"
).encode()


class PolicyFactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Source(
            "stripe-mcp", "https://docs.stripe.com/mcp", "https://docs.stripe.com/mcp.md"
        )
        self.response = MagicMock()
        self.response.geturl.return_value = self.source.monitor_url
        self.response.read.return_value = NOTICE
        self.response.headers.get.return_value = "text/markdown"
        self.response.__enter__.return_value = self.response

    def test_selected_facts_do_not_invent_cutoff_time_or_live_access(self) -> None:
        facts = mcp_policy_facts(NOTICE)
        self.assertEqual(facts["deadline"], "2026-10-31")
        self.assertEqual(facts["rejection_http_status"], 401)
        self.assertTrue(facts["full_access_secret_rejected"])
        self.assertTrue(facts["restricted_without_agent_tag_rejected"])
        self.assertTrue(facts["replacement_oauth"])
        self.assertTrue(facts["replacement_agent_key"])
        self.assertTrue(facts["oauth_discovery_challenge"])
        self.assertIsNone(facts["cutoff_time"])
        self.assertIsNone(facts["cutoff_timezone"])
        self.assertNotIn("account_verification", facts)

    def test_whitespace_quote_and_unrelated_edits_keep_selected_facts(self) -> None:
        plain = NOTICE.replace(b"> ", b"").replace(b">\n", b"\n")
        changed = plain.replace(b"Before then,", b"\nBefore   then,").replace(
            b"Synthetic unrelated content.", b"Changed tool guidance."
        )
        self.assertNotEqual(fingerprint(NOTICE, "text/markdown"), fingerprint(changed, "text/markdown"))
        self.assertEqual(mcp_policy_facts(NOTICE), mcp_policy_facts(changed))

    def test_missing_duplicate_and_code_only_notice_require_review(self) -> None:
        for body in [
            b"# No notice\n", NOTICE + NOTICE,
            b"```markdown\n" + NOTICE + b"```\n",
            b"````markdown\n```\n" + NOTICE + b"````\n",
            b"~~~markdown\n```nested\n" + NOTICE + b"~~~\n",
        ]:
            with self.subTest(body_length=len(body)), self.assertRaises(ValueError):
                mcp_policy_facts(body)

    def test_conflicting_and_invalid_dates_require_review(self) -> None:
        for body in [
            NOTICE.replace(b"Beginning 31 October", b"Beginning 30 October"),
            NOTICE.replace(b"31 October", b"32 October"),
            NOTICE.replace(b"31 October", b"31 Unknownmonth"),
        ]:
            with self.subTest(body_length=len(body)), self.assertRaises(ValueError):
                mcp_policy_facts(body)

    def test_changed_policy_wording_is_unknown_not_old_fact_fallback(self) -> None:
        for original, replacement in [
            (b"no longer accepts", b"accepts"),
            (b"`401`", b"`403`"),
            (b"without the Agent tag", b"with the Agent tag"),
            (b"OAuth discovery challenge", b"a new challenge"),
            (b"discovery challenge.", b"discovery challenge. Cutoff is at midnight UTC."),
        ]:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                mcp_policy_facts(NOTICE.replace(original, replacement))

    def test_changed_hash_with_unchanged_facts(self) -> None:
        facts = mcp_policy_facts(NOTICE)
        with patch("scripts.source_monitor.urlopen", return_value=self.response):
            result = observe(self.source, "different-hash", facts)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.change, "changed")
        self.assertEqual(result.policy_change, "unchanged")
        self.assertIsNone(result.policy_error)

    def test_first_fact_baseline_and_changed_deadline(self) -> None:
        with patch("scripts.source_monitor.urlopen", return_value=self.response):
            baseline = observe(self.source, None)
            self.response.read.return_value = NOTICE.replace(b"31 October", b"30 October")
            changed = observe(self.source, baseline.sha256, baseline.policy_facts)
        self.assertEqual(baseline.policy_change, "baseline")
        self.assertEqual(changed.policy_change, "changed")
        self.assertEqual(changed.policy_facts["deadline"], "2026-10-30")

    def test_fetch_and_parse_failures_do_not_claim_unchanged(self) -> None:
        with patch("scripts.source_monitor.urlopen", side_effect=URLError("synthetic offline")):
            failed = observe(self.source, "previous-hash", mcp_policy_facts(NOTICE))
        self.assertEqual(failed.status, "error")
        self.assertIsNone(failed.policy_facts)
        self.assertNotEqual(failed.policy_change, "unchanged")
        self.response.read.return_value = b"# Missing auth notice\n"
        with patch("scripts.source_monitor.urlopen", return_value=self.response):
            failed = observe(self.source, "previous-hash", mcp_policy_facts(NOTICE))
        self.assertEqual(failed.status, "ok")
        self.assertEqual(failed.policy_change, "unknown")
        self.assertIsNone(failed.policy_facts)
        self.assertIn("notice", failed.policy_error)

    def test_redirected_html_is_not_treated_as_reviewed_markdown(self) -> None:
        self.response.geturl.return_value = "https://docs.stripe.com/mcp"
        with patch("scripts.source_monitor.urlopen", return_value=self.response):
            result = observe(self.source, None)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.policy_change, "unknown")
        self.assertIn("Markdown URL", result.policy_error)

    def test_previous_facts_skip_today_errors_and_legacy_reports(self) -> None:
        facts = mcp_policy_facts(NOTICE)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                ("2026-10-10", {"policy_facts": facts}),
                ("2026-10-11", {}),
                ("2026-10-12", {"policy_facts": facts, "status": "error"}),
                ("2026-10-13", {"policy_error": "needs review", "policy_facts": None}),
                ("2026-10-14", {"policy_facts": {**facts, "deadline": "2026-10-30"}}),
            ]
            for day, fields in rows:
                item = {"id": "stripe-mcp", "status": "ok", **fields}
                (root / f"{day}-sources.json").write_text(
                    json.dumps({"observations": [item]}), encoding="utf-8"
                )
            self.assertEqual(previous_policy_facts(root, before_date="2026-10-14"), facts)
            self.assertIsNone(previous_policy_facts(root, before_date="2026-10-10"))

    def test_main_records_policy_parse_error_and_returns_nonzero(self) -> None:
        self.response.read.return_value = b"# Synthetic missing notice\n"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("sys.argv", ["monitor", "--output-dir", str(root)]),
                patch("scripts.source_monitor.load_sources", return_value=[self.source]),
                patch("scripts.source_monitor.urlopen", return_value=self.response),
                self.assertLogs(level="INFO"),
            ):
                self.assertEqual(main(), 1)
            report = json.loads(next(root.glob("*-sources.json")).read_text(encoding="utf-8"))
            item = report["observations"][0]
            self.assertEqual(item["status"], "ok")
            self.assertEqual(item["policy_change"], "unknown")
            self.assertIsNotNone(item["policy_error"])
            self.assertIsNone(item["policy_facts"])
            self.assertNotIn("Synthetic missing notice", json.dumps(report))
            self.assertFalse(list(root.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
