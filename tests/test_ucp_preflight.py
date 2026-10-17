"""Local compatibility is not discovery trust, customer consent or a payment result."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import patch

from lab.ucp_preflight import (
    INSTRUMENTS, REVIEWED_HANDLER_VERSION, REVIEWED_UCP_VERSION, STRIPE_HANDLER,
    HandlerMetadata, UCPOrderWebhookDelivery, assess, converge_ucp_order_webhooks,
    main, verify_ucp_discovery_response_status, verify_ucp_signing_gate,
)


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = HandlerMetadata(
            REVIEWED_UCP_VERSION, STRIPE_HANDLER, REVIEWED_HANDLER_VERSION,
            "sandbox", tuple(sorted(INSTRUMENTS)),
        )

    def test_card_requires_matching_environment_and_confirmed_relationship(self) -> None:
        for environment in ("sandbox", "production"):
            for relationship in ("confirmed", "missing", "unknown"):
                with self.subTest(environment=environment, relationship=relationship):
                    business = replace(self.profile, environment=environment)
                    result = assess(self.profile, business, instrument="card", relationship=relationship)
                    candidate = environment == "sandbox" and relationship == "confirmed"
                    self.assertEqual(result.status == "candidate_unverified", candidate)
                    self.assertEqual(result.credential_path == "card_tokenize_to_spt", candidate)
                    self.assertFalse(result.payment_authorized)
                    if environment == "production":
                        self.assertIn("card_tokenize_environment_mismatch", result.reasons)
                    if relationship != "confirmed":
                        self.assertIn("card_tokenize_commerce_relationship_unconfirmed", result.reasons)

    def test_apple_pay_does_not_inherit_card_tokenization_requirements(self) -> None:
        business = replace(self.profile, environment="production")
        result = assess(self.profile, business, instrument="apple_pay", relationship="unknown")
        self.assertEqual(result.status, "candidate_unverified")
        self.assertEqual(result.credential_path, "apple_pay_direct_to_complete")
        self.assertEqual(result.provider_verification, "not_performed")
        self.assertFalse(result.payment_authorized)

    def test_link_and_google_pay_advertisements_never_imply_stripe_completion(self) -> None:
        for instrument, reason in [
            ("link", "link_instrument_not_accepted_by_current_complete"),
            ("google_pay", "google_pay_requires_separately_reviewed_com_google_pay_handler"),
        ]:
            with self.subTest(instrument=instrument):
                result = assess(self.profile, self.profile, instrument=instrument, relationship="confirmed")
                self.assertEqual(result.status, "blocked")
                self.assertEqual(result.reasons, (reason,))
                self.assertIsNone(result.credential_path)
                self.assertFalse(result.payment_authorized)

    def test_missing_instrument_on_either_side_is_blocked(self) -> None:
        for platform, business in [
            (replace(self.profile, instruments=()), self.profile),
            (self.profile, replace(self.profile, instruments=("apple_pay",))),
        ]:
            result = assess(platform, business, instrument="card", relationship="confirmed")
            self.assertIn("instrument_not_advertised_by_both", result.reasons)
            self.assertEqual(result.status, "blocked")

    def test_version_mismatch_and_equal_unreviewed_versions_are_blocked(self) -> None:
        for field, value, mismatch, unreviewed in [
            ("ucp_version", "2026-07-01", "ucp_version_mismatch", "ucp_version_not_reviewed_locally"),
            ("handler_version", "2026-07-01", "handler_version_mismatch", "handler_version_not_reviewed_locally"),
        ]:
            with self.subTest(field=field):
                changed = replace(self.profile, **{field: value})
                result = assess(self.profile, changed, instrument="card", relationship="confirmed")
                self.assertIn(mismatch, result.reasons)
                self.assertIn(unreviewed, result.reasons)
                result = assess(changed, changed, instrument="card", relationship="confirmed")
                self.assertEqual(result.reasons, (unreviewed,))
                self.assertEqual(result.status, "blocked")

    def test_google_handler_is_not_silently_routed_or_certified(self) -> None:
        google = replace(self.profile, handler_name="com.google.pay")
        result = assess(self.profile, google, instrument="google_pay", relationship="confirmed")
        self.assertIn("handler_name_mismatch", result.reasons)
        self.assertIn("handler_not_reviewed_locally", result.reasons)
        result = assess(google, google, instrument="google_pay", relationship="confirmed")
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.credential_path)

    def test_invalid_metadata_and_moving_versions_are_explicit_errors(self) -> None:
        for field, value in [
            ("ucp_version", "latest"), ("handler_version", "main"),
            ("handler_version", "2026-02-30"), ("ucp_version", "2026-4-8"),
            ("ucp_version", True), ("environment", "live"), ("environment", []),
            ("handler_name", "https://example.com"), ("handler_name", None),
            ("instruments", ["card"]), ("instruments", ("card", "card")),
            ("instruments", ("unknown",)), ("instruments", ([],)),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                replace(self.profile, **{field: value})
        for instrument, relationship in [("unknown", "confirmed"), (True, "confirmed"), ("card", None)]:
            with self.subTest(instrument=instrument, relationship=relationship), self.assertRaises(ValueError):
                assess(self.profile, self.profile, instrument=instrument, relationship=relationship)
        with self.assertRaises(ValueError):
            assess(None, self.profile, instrument="card", relationship="confirmed")

    def test_cli_blocked_candidate_and_invalid_exit_codes_are_honest(self) -> None:
        for args, code, status in [
            ([], 1, "blocked"),
            (["--instrument", "card", "--relationship", "confirmed"], 0, "candidate_unverified"),
            (["--instrument", "apple_pay"], 0, "candidate_unverified"),
            (["--business-ucp-version", "2026-07-01"], 1, "blocked"),
            (["--business-handler-version", "latest"], 2, "invalid_metadata"),
        ]:
            with self.subTest(args=args):
                output, errors = io.StringIO(), io.StringIO()
                with patch("sys.argv", ["preflight", *args]), redirect_stdout(output), redirect_stderr(errors):
                    self.assertEqual(main(), code)
                if code == 2:
                    self.assertEqual(output.getvalue(), "")
                    self.assertEqual(json.loads(errors.getvalue())["status"], status)
                else:
                    self.assertEqual(errors.getvalue(), "")
                    report = json.loads(output.getvalue())
                    self.assertEqual(report["decision"]["status"], status)
                    self.assertFalse(report["real_payments"])
                    self.assertFalse(report["decision"]["payment_authorized"])
                    self.assertEqual(report["decision"]["provider_verification"], "not_performed")
                    self.assertEqual(report["policy_checked_on"], "2026-10-13")
                    self.assertEqual(len(report["remaining_checks"]), 4)

    def test_ucp_signing_gate_requires_webhook_and_agent_headers_when_present(self) -> None:
        # Checkout REST request with UCP-Agent and Idempotency-Key (#795)
        checkout_headers = frozenset({
            "content-digest", "content-type", "ucp-agent", "signature-agent", "idempotency-key"
        })
        omitted_agent = verify_ucp_signing_gate(
            has_query=False,
            has_body=True,
            present_headers=checkout_headers,
            covered_components=(
                "@method", "@authority", "@path", "content-digest",
                "content-type", "signature-agent", "idempotency-key",
            ),
        )
        self.assertFalse(omitted_agent.accepted)
        self.assertEqual(omitted_agent.reason, "closed_sign_if_present_violation")
        self.assertEqual(omitted_agent.missing_components, ("ucp-agent",))

        # Order webhook must cover webhook-id and webhook-timestamp (#659)
        webhook_headers = frozenset({
            "content-digest", "content-type", "webhook-id", "webhook-timestamp", "signature-agent"
        })
        omitted_webhook_headers = verify_ucp_signing_gate(
            has_query=False,
            has_body=True,
            present_headers=webhook_headers,
            covered_components=(
                "@method", "@authority", "@path", "content-digest", "content-type", "signature-agent"
            ),
        )
        self.assertFalse(omitted_webhook_headers.accepted)
        self.assertEqual(omitted_webhook_headers.missing_components, ("webhook-id", "webhook-timestamp"))

        valid_webhook = verify_ucp_signing_gate(
            has_query=False,
            has_body=True,
            present_headers=webhook_headers,
            covered_components=(
                "@method", "@authority", "@path", "content-digest", "content-type",
                "signature-agent", "webhook-id", "webhook-timestamp",
            ),
        )
        self.assertTrue(valid_webhook.accepted)

    def test_ucp_discovery_status_allows_conditional_304_and_forbids_redirects(self) -> None:
        self.assertTrue(verify_ucp_discovery_response_status(200).accepted)
        self.assertTrue(
            verify_ucp_discovery_response_status(
                304, conditional_request=True, has_cached_entry=True
            ).accepted
        )
        self.assertFalse(
            verify_ucp_discovery_response_status(
                304, conditional_request=False, has_cached_entry=True
            ).accepted
        )
        for redirect_code in (301, 302, 303, 307, 308):
            with self.subTest(redirect_code=redirect_code):
                dec = verify_ucp_discovery_response_status(redirect_code)
                self.assertFalse(dec.accepted)
                self.assertEqual(dec.reason, "redirect_forbidden")

    def test_ucp_order_webhooks_deduplicate_retries_and_converge_out_of_order(self) -> None:
        headers = frozenset({"content-digest", "content-type", "webhook-id", "webhook-timestamp"})
        covered = (
            "@method", "@authority", "@path", "content-digest",
            "content-type", "webhook-id", "webhook-timestamp",
        )
        # Delivered out-of-order (T2 arrives before T1), plus valid retry of T1,
        # plus mutated-timestamp retry of T2, plus unsigned webhook T3
        d_t2 = UCPOrderWebhookDelivery(
            webhook_id="wh_evt_2",
            webhook_timestamp="2026-10-16T08:10:00Z",
            order_id="ord_900",
            order_state={"status": "shipped", "tracking": "1Z999"},
            present_headers=headers,
            covered_components=covered,
        )
        d_t1 = UCPOrderWebhookDelivery(
            webhook_id="wh_evt_1",
            webhook_timestamp="2026-10-16T08:00:00Z",
            order_id="ord_900",
            order_state={"status": "processing", "tracking": None},
            present_headers=headers,
            covered_components=covered,
        )
        d_t1_retry = UCPOrderWebhookDelivery(
            webhook_id="wh_evt_1",
            webhook_timestamp="2026-10-16T08:00:00Z",
            order_id="ord_900",
            order_state={"status": "processing", "tracking": None},
            present_headers=headers,
            covered_components=covered,
        )
        d_t2_mutated_retry = UCPOrderWebhookDelivery(
            webhook_id="wh_evt_2",
            webhook_timestamp="2026-10-16T08:15:00Z",
            order_id="ord_900",
            order_state={"status": "shipped", "tracking": "1Z999"},
            present_headers=headers,
            covered_components=covered,
        )
        d_t3_unsigned = UCPOrderWebhookDelivery(
            webhook_id="wh_evt_3",
            webhook_timestamp="2026-10-16T08:20:00Z",
            order_id="ord_900",
            order_state={"status": "cancelled", "tracking": None},
            present_headers=headers,
            covered_components=("@method", "@authority", "@path", "content-digest", "content-type"),
        )
        result = converge_ucp_order_webhooks(
            [d_t2, d_t1, d_t1_retry, d_t2_mutated_retry, d_t3_unsigned]
        )
        self.assertEqual(result.applied_webhook_ids, ("wh_evt_1", "wh_evt_2"))
        self.assertEqual(result.deduplicated_retry_ids, ("wh_evt_1",))
        self.assertEqual(
            result.rejected_deliveries,
            (
                ("wh_evt_2", "webhook_timestamp_mutated_on_retry"),
                ("wh_evt_3", "closed_sign_if_present_violation"),
            ),
        )
        self.assertEqual(result.converged_order_state, {"status": "shipped", "tracking": "1Z999"})


if __name__ == "__main__":
    unittest.main()
