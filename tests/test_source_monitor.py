"""Offline tests for source provenance and visible fetch failures."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from scripts.source_monitor import (
    MAX_BYTES, Observation, Source, fingerprint, load_sources, main, observe,
    previous_hashes, previous_source_facts, spt_connect_marker_check, spt_country_list_check,
    spt_parser_version_check, stripe_spt_connect_facts, summarize_cross_source_checks,
    index_cross_source_statuses,
    partition_cross_source_checks,
    summarize_gate_health,
    stripe_spt_facts, validate_url,
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
        with patch("scripts.source_monitor.urlopen", return_value=response) as mocked_open:
            self.assertEqual(observe(self.source, None).change, "baseline")
            req_sent = mocked_open.call_args[0][0]
            self.assertEqual(req_sent.get_header("Accept-language"), "en-US,en;q=0.9")
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
        first_spt = fingerprint(
            b'{"expires_at": 1794406247}', "text/plain", source_id="stripe-spt",
        )
        second_spt = fingerprint(
            b'{"expires_at": 1794406248}', "text/plain", source_id="stripe-spt",
        )
        self.assertEqual(first_spt, second_spt)

    def test_observe_stripe_spt_ignores_dynamic_expiry_noise(self) -> None:
        source = Source(
            "stripe-spt",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller",
        )
        response = MagicMock()
        response.geturl.return_value = source.monitor_url
        response.headers.get.return_value = "text/markdown"
        response.__enter__.return_value = response
        first = b'{"expires_at": 1794406247, "status": "active"}'
        second = b'{"expires_at": 1794406248, "status": "active"}'
        with patch("scripts.source_monitor.urlopen", return_value=response):
            response.read.return_value = first
            baseline = observe(source, None)
        self.assertEqual(baseline.status, "ok")
        self.assertEqual(baseline.change, "baseline")
        with patch("scripts.source_monitor.urlopen", return_value=response):
            response.read.return_value = second
            followup = observe(source, baseline.sha256)
        self.assertEqual(followup.status, "ok")
        self.assertEqual(followup.change, "unchanged")

    def test_stripe_spt_facts_extract_stable_contract_fields(self) -> None:
        body = (
            "# Shared payment tokens\n\n"
            "SPTs are available to agents, customers, and sellers in the US, Canada, and select European countries.\n\n"
            "### View all supported countries\n\n"
            "- AT\n- CA\n- US\n\n"
            "Use Stripe-Version: 2026-09-30.preview for these endpoints.\n"
            "The recurring_interval field controls recurring shared grants.\n"
            "setup_future_usage and payment_method_options[card][setup_future_usage] are not allowed with shared payment tokens.\n"
            "Listen for shared_payment.granted_token.deactivated webhook events.\n"
        ).encode("utf-8")
        facts = stripe_spt_facts(body)
        self.assertEqual(facts["parser_version"], "stripe-spt-facts-v1")
        self.assertEqual(facts["api_version"], "2026-09-30.preview")
        self.assertEqual(facts["supported_country_count"], 3)
        self.assertEqual(len(facts["supported_country_codes_sha256"]), 64)
        self.assertTrue(facts["has_recurring_interval"])
        self.assertTrue(facts["forbids_setup_future_usage"])
        self.assertTrue(facts["has_deactivated_webhook_event"])

    def test_stripe_spt_facts_require_version_and_countries(self) -> None:
        with self.assertRaises(ValueError):
            stripe_spt_facts(b"# Shared payment tokens\nStripe-Version: 2026-09-30.preview\n")
        with self.assertRaises(ValueError):
            stripe_spt_facts(
                b"# Shared payment tokens\n### View all supported countries\n- US\n"
            )
        with self.assertRaises(ValueError):
            stripe_spt_facts(
                b"# Shared payment tokens\nStripe-Version: 2026-09-30.preview\n"
                b"Stripe-Version: 2026-10-28.preview\n### View all supported countries\n- US\n"
            )

    def test_stripe_spt_connect_facts_extracts_connect_contract_markers(self) -> None:
        body = (
            "# Shared payment tokens\n\n"
            "### View all supported countries\n\n"
            "- CA\n- US\n\n"
            "# Connect platforms\n\n"
            "The network ID maps to seller_details[network_business_profile].\n"
            "Pass payment_method_data[shared_payment_granted_token] in PaymentIntent create.\n"
            "Use the Stripe-Account header for connected-account retrieval.\n"
            "- **Direct charge**: ...\n"
            "- **Destination charge**: ...\n"
            "- **Separate charges and transfers**: ...\n"
        ).encode("utf-8")
        facts = stripe_spt_connect_facts(body)
        self.assertEqual(facts["parser_version"], "stripe-spt-connect-facts-v1")
        self.assertEqual(facts["supported_country_count"], 2)
        self.assertEqual(len(facts["supported_country_codes_sha256"]), 64)
        self.assertTrue(facts["has_connect_platforms_section"])
        self.assertTrue(facts["has_network_business_profile"])
        self.assertTrue(facts["has_shared_payment_granted_token"])
        self.assertTrue(facts["has_stripe_account_header"])
        self.assertTrue(facts["covers_direct_destination_separate_charges"])

    def test_stripe_spt_connect_facts_require_countries(self) -> None:
        with self.assertRaises(ValueError):
            stripe_spt_connect_facts(
                b"# Shared payment tokens\n# Connect platforms\nNo country block.\n"
            )

    def test_observe_stripe_spt_connect_extracts_policy_facts(self) -> None:
        source = Source(
            "stripe-spt-connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=connect",
        )
        response = MagicMock()
        response.geturl.return_value = source.monitor_url
        response.headers.get.return_value = "text/markdown"
        response.__enter__.return_value = response
        response.read.return_value = (
            "# Shared payment tokens\n\n"
            "### View all supported countries\n\n- CA\n- US\n\n"
            "# Connect platforms\n\n"
            "seller_details[network_business_profile]\n"
            "payment_method_data[shared_payment_granted_token]\n"
            "Stripe-Account\n"
            "Direct charge\nDestination charge\nSeparate charges and transfers\n"
        ).encode("utf-8")
        with patch("scripts.source_monitor.urlopen", return_value=response):
            baseline = observe(source, None)
        self.assertEqual(baseline.status, "ok")
        self.assertEqual(baseline.policy_change, "baseline")
        self.assertIsNone(baseline.policy_error)
        self.assertEqual(
            baseline.policy_facts["parser_version"], "stripe-spt-connect-facts-v1",
        )

    def test_previous_source_facts_matches_source_and_parser(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                ("2026-10-10", {"id": "stripe-spt", "status": "ok",
                                "policy_facts": {"parser_version": "stripe-spt-facts-v1", "api_version": "2026-09-30.preview"}}),
                ("2026-10-11", {"id": "stripe-spt", "status": "ok",
                                "policy_facts": {"parser_version": "other-parser-v1", "api_version": "x"}}),
                ("2026-10-12", {"id": "stripe-spt", "status": "ok",
                                "policy_error": "needs review", "policy_facts": None}),
                ("2026-10-13", {"id": "stripe-mcp", "status": "ok",
                                "policy_facts": {"parser_version": "stripe-mcp-auth-notice-v1"}}),
            ]
            for day, item in rows:
                (root / f"{day}-sources.json").write_text(
                    json.dumps({"observations": [item]}), encoding="utf-8"
                )
            facts = previous_source_facts(
                root, before_date="2026-10-14",
                source_id="stripe-spt", parser_version="stripe-spt-facts-v1",
            )
            self.assertEqual(facts["api_version"], "2026-09-30.preview")
            self.assertIsNone(previous_source_facts(
                root, before_date="2026-10-10",
                source_id="stripe-spt", parser_version="stripe-spt-facts-v1",
            ))

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
            self.assertEqual(report["cross_source_checks"][0]["status"], "unavailable")
            self.assertEqual(
                report["cross_source_statuses"]["stripe-spt-country-list-parity"], "unavailable"
            )
            self.assertIn(
                "stripe-spt-country-list-parity",
                report["cross_source_partitions"]["unavailable"],
            )
            self.assertIn("cross_source_summary", report)
            self.assertEqual(report["cross_source_summary"]["mismatch"], 0)
            self.assertIn("gate_health", report)
            self.assertEqual(report["gate_health"]["observation_errors"], 1)
            self.assertIn("observation_errors", report["gate_health"]["blocking_reasons"])
            self.assertTrue(report["gate_health"]["blocking"])
            self.assertFalse(list(root.glob("*.tmp")))

    def test_main_returns_nonzero_on_cross_source_mismatch(self) -> None:
        seller = Source(
            "stripe-spt",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller",
        )
        connect = Source(
            "stripe-spt-connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=connect",
        )
        seller_observation = Observation(
            seller.id, seller.url, seller.monitor_url, "ok", "seller-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "aaa",
            },
            policy_change="unchanged",
        )
        connect_observation = Observation(
            connect.id, connect.url, connect.monitor_url, "ok", "connect-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-connect-facts-v1",
                "supported_country_count": 33,
                "supported_country_codes_sha256": "bbb",
            },
            policy_change="unchanged",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("sys.argv", ["monitor", "--output-dir", str(root)]),
                patch("scripts.source_monitor.load_sources", return_value=[seller, connect]),
                patch("scripts.source_monitor.observe", side_effect=[seller_observation, connect_observation]),
                self.assertLogs(level="INFO"),
            ):
                self.assertEqual(main(), 1)
            report = json.loads(next(root.glob("*-sources.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["cross_source_checks"][0]["status"], "mismatch")
            self.assertEqual(
                report["cross_source_statuses"]["stripe-spt-country-list-parity"], "mismatch"
            )
            self.assertIn(
                "stripe-spt-country-list-parity",
                report["cross_source_partitions"]["mismatch"],
            )

    def test_spt_country_list_check_consistent(self) -> None:
        seller = Observation(
            "stripe-spt", "seller-url", "seller-fetch", "ok", "seller-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "abc",
            },
        )
        connect = Observation(
            "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-connect-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "abc",
            },
        )
        check = spt_country_list_check([seller, connect])
        self.assertEqual(check["check_id"], "stripe-spt-country-list-parity")
        self.assertEqual(check["status"], "consistent")
        self.assertEqual(check["supported_country_count"], 34)

    def test_spt_country_list_check_mismatch_and_unavailable(self) -> None:
        mismatch = spt_country_list_check([
            Observation(
                "stripe-spt", "seller-url", "seller-fetch", "ok", "seller-hash", "unchanged",
                policy_facts={
                    "supported_country_count": 34,
                    "supported_country_codes_sha256": "aaa",
                },
            ),
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
                policy_facts={
                    "supported_country_count": 33,
                    "supported_country_codes_sha256": "bbb",
                },
            ),
        ])
        self.assertEqual(mismatch["status"], "mismatch")
        unavailable = spt_country_list_check([
            Observation("stripe-spt", "seller-url", "seller-fetch", "error", None, "unknown", "offline"),
        ])
        self.assertEqual(unavailable["status"], "unavailable")

    def test_spt_connect_marker_check_consistent_mismatch_and_unavailable(self) -> None:
        consistent = spt_connect_marker_check([
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
                policy_facts={
                    "has_connect_platforms_section": True,
                    "has_network_business_profile": True,
                    "has_shared_payment_granted_token": True,
                    "has_stripe_account_header": True,
                    "covers_direct_destination_separate_charges": True,
                },
            )
        ])
        self.assertEqual(consistent["status"], "consistent")
        mismatch = spt_connect_marker_check([
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
                policy_facts={
                    "has_connect_platforms_section": True,
                    "has_network_business_profile": False,
                    "has_shared_payment_granted_token": True,
                    "has_stripe_account_header": True,
                    "covers_direct_destination_separate_charges": True,
                },
            )
        ])
        self.assertEqual(mismatch["status"], "mismatch")
        self.assertIn("has_network_business_profile", mismatch["missing_markers"])
        unavailable = spt_connect_marker_check([
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "error",
                None, "unknown", "offline",
            )
        ])
        self.assertEqual(unavailable["status"], "unavailable")

    def test_main_returns_nonzero_on_connect_marker_mismatch(self) -> None:
        seller = Source(
            "stripe-spt",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller",
        )
        connect = Source(
            "stripe-spt-connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=connect",
        )
        seller_observation = Observation(
            seller.id, seller.url, seller.monitor_url, "ok", "seller-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "same",
            },
            policy_change="unchanged",
        )
        connect_observation = Observation(
            connect.id, connect.url, connect.monitor_url, "ok", "connect-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-connect-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "same",
                "has_connect_platforms_section": True,
                "has_network_business_profile": False,
                "has_shared_payment_granted_token": True,
                "has_stripe_account_header": True,
                "covers_direct_destination_separate_charges": True,
            },
            policy_change="unchanged",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("sys.argv", ["monitor", "--output-dir", str(root)]),
                patch("scripts.source_monitor.load_sources", return_value=[seller, connect]),
                patch("scripts.source_monitor.observe", side_effect=[seller_observation, connect_observation]),
                self.assertLogs(level="INFO"),
            ):
                self.assertEqual(main(), 1)
            report = json.loads(next(root.glob("*-sources.json")).read_text(encoding="utf-8"))
            marker_check = next(
                check for check in report["cross_source_checks"]
                if check["check_id"] == "stripe-spt-connect-required-markers"
            )
            self.assertEqual(marker_check["status"], "mismatch")

    def test_spt_parser_version_check_consistent_mismatch_and_unavailable(self) -> None:
        consistent = spt_parser_version_check([
            Observation(
                "stripe-spt", "seller-url", "seller-fetch", "ok", "seller-hash", "unchanged",
                policy_facts={"parser_version": "stripe-spt-facts-v1"},
            ),
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
                policy_facts={"parser_version": "stripe-spt-connect-facts-v1"},
            ),
        ])
        self.assertEqual(consistent["status"], "consistent")
        mismatch = spt_parser_version_check([
            Observation(
                "stripe-spt", "seller-url", "seller-fetch", "ok", "seller-hash", "unchanged",
                policy_facts={"parser_version": "stripe-spt-facts-v2"},
            ),
            Observation(
                "stripe-spt-connect", "connect-url", "connect-fetch", "ok", "connect-hash", "unchanged",
                policy_facts={"parser_version": "stripe-spt-connect-facts-v1"},
            ),
        ])
        self.assertEqual(mismatch["status"], "mismatch")
        self.assertEqual(mismatch["actual"]["stripe-spt"], "stripe-spt-facts-v2")
        unavailable = spt_parser_version_check([
            Observation("stripe-spt", "seller-url", "seller-fetch", "error", None, "unknown", "offline"),
        ])
        self.assertEqual(unavailable["status"], "unavailable")

    def test_main_returns_nonzero_on_parser_version_mismatch(self) -> None:
        seller = Source(
            "stripe-spt",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller",
        )
        connect = Source(
            "stripe-spt-connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=connect",
            "https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=connect",
        )
        seller_observation = Observation(
            seller.id, seller.url, seller.monitor_url, "ok", "seller-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-facts-v2",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "same",
            },
            policy_change="unchanged",
        )
        connect_observation = Observation(
            connect.id, connect.url, connect.monitor_url, "ok", "connect-hash", "unchanged",
            policy_facts={
                "parser_version": "stripe-spt-connect-facts-v1",
                "supported_country_count": 34,
                "supported_country_codes_sha256": "same",
                "has_connect_platforms_section": True,
                "has_network_business_profile": True,
                "has_shared_payment_granted_token": True,
                "has_stripe_account_header": True,
                "covers_direct_destination_separate_charges": True,
            },
            policy_change="unchanged",
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch("sys.argv", ["monitor", "--output-dir", str(root)]),
                patch("scripts.source_monitor.load_sources", return_value=[seller, connect]),
                patch("scripts.source_monitor.observe", side_effect=[seller_observation, connect_observation]),
                self.assertLogs(level="INFO"),
            ):
                self.assertEqual(main(), 1)
            report = json.loads(next(root.glob("*-sources.json")).read_text(encoding="utf-8"))
            parser_check = next(
                check for check in report["cross_source_checks"]
                if check["check_id"] == "stripe-spt-parser-version-parity"
            )
            self.assertEqual(parser_check["status"], "mismatch")
            self.assertGreaterEqual(report["cross_source_summary"]["mismatch"], 1)
            self.assertGreaterEqual(report["gate_health"]["cross_source_mismatch"], 1)
            self.assertIn("cross_source_mismatch", report["gate_health"]["blocking_reasons"])
            self.assertTrue(report["gate_health"]["blocking"])

    def test_summarize_cross_source_checks_counts_and_blocking(self) -> None:
        summary = summarize_cross_source_checks([
            {"check_id": "a", "status": "consistent"},
            {"check_id": "b", "status": "mismatch"},
            {"check_id": "c", "status": "unavailable"},
            {"check_id": "d", "status": "consistent"},
            {"check_id": "e", "status": "unknown"},
        ])
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["consistent"], 2)
        self.assertEqual(summary["mismatch"], 1)
        self.assertEqual(summary["unavailable"], 1)
        self.assertTrue(summary["blocking"])

    def test_index_cross_source_statuses_returns_stable_map(self) -> None:
        statuses = index_cross_source_statuses([
            {"check_id": "a", "status": "consistent"},
            {"check_id": "b", "status": "mismatch"},
            {"check_id": "c", "status": "unavailable", "reason": "missing"},
            {"check_id": "d"},
            {"status": "consistent"},
            "invalid",
        ])
        self.assertEqual(
            statuses,
            {"a": "consistent", "b": "mismatch", "c": "unavailable"},
        )

    def test_partition_cross_source_checks_groups_check_ids(self) -> None:
        partitions = partition_cross_source_checks([
            {"check_id": "a", "status": "consistent"},
            {"check_id": "b", "status": "mismatch"},
            {"check_id": "c", "status": "unavailable"},
            {"check_id": "d", "status": "mismatch"},
            {"check_id": "e", "status": "unknown"},
            {"status": "consistent"},
            "invalid",
        ])
        self.assertEqual(partitions["consistent"], ["a"])
        self.assertEqual(partitions["mismatch"], ["b", "d"])
        self.assertEqual(partitions["unavailable"], ["c"])

    def test_summarize_gate_health_counts_and_blocking(self) -> None:
        observations = [
            Observation("a", "u", "fu", "ok", "sha", "unchanged"),
            Observation("b", "u", "fu", "error", None, "unknown", "offline"),
            Observation("c", "u", "fu", "ok", "sha", "changed", policy_error="facts unavailable"),
        ]
        gate_health = summarize_gate_health(
            observations,
            {"total": 3, "consistent": 2, "mismatch": 0, "unavailable": 1, "blocking": False},
        )
        self.assertEqual(gate_health["observation_errors"], 1)
        self.assertEqual(gate_health["policy_errors"], 1)
        self.assertEqual(gate_health["cross_source_mismatch"], 0)
        self.assertEqual(
            gate_health["blocking_reasons"], ["observation_errors", "policy_errors"]
        )
        self.assertTrue(gate_health["blocking"])


if __name__ == "__main__":
    unittest.main()
