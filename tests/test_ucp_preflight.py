"""Local compatibility is not discovery trust, customer consent or a payment result."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import patch

from lab.ucp_preflight import (
    INSTRUMENTS, POLICY_CHECKED_ON, REVIEWED_HANDLER_VERSION, REVIEWED_UCP_VERSION, STRIPE_HANDLER,
    HandlerMetadata, UCPOrderWebhookDelivery, assess, converge_ucp_order_webhooks,
    decode_ucp_item_id_token, encode_ucp_item_id_token, evaluate_ucp_mandate_admission,
    evaluate_ucp_return_policy, main, resolve_ucp_effective_consent,
    select_ucp_identity_authorization_server, validate_and_merge_ucp_buyer_consent,
    validate_ucp_continue_to, validate_ucp_permalink_request,
    verify_ucp_checkout_escalation_contract, verify_ucp_discovery_response_status,
    verify_ucp_permalink_redirect, verify_ucp_signing_gate,
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
                    self.assertEqual(report["policy_checked_on"], POLICY_CHECKED_ON.isoformat())
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

    def test_ucp_permalink_redirect_requires_303_no_store_and_no_referrer(self) -> None:
        valid_headers = {
            "Location": "https://merchant.example/checkout/sessions/cs_123",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        }
        ok = verify_ucp_permalink_redirect(303, valid_headers)
        self.assertTrue(ok.accepted)
        self.assertEqual(ok.reason, "ok_permalink_303_no_store_no_referrer")

        # Missing Cache-Control and Referrer-Policy (the exact #913 doc bug in 5 examples)
        incomplete = verify_ucp_permalink_redirect(
            303, {"Location": "https://merchant.example/checkout/sessions/cs_123"}
        )
        self.assertFalse(incomplete.accepted)
        self.assertEqual(incomplete.reason, "missing_mandated_permalink_headers")
        self.assertEqual(incomplete.missing_headers, ("cache-control", "referrer-policy"))

        # Wrong status code (e.g. 302 Found instead of 303 See Other)
        wrong_status = verify_ucp_permalink_redirect(302, valid_headers)
        self.assertFalse(wrong_status.accepted)
        self.assertEqual(wrong_status.reason, "permalink_redirect_requires_303")

        # Cacheable redirect or leaking Referrer-Policy rejected
        cacheable = verify_ucp_permalink_redirect(
            303, {**valid_headers, "Cache-Control": "private, max-age=60"}
        )
        self.assertFalse(cacheable.accepted)
        self.assertEqual(cacheable.reason, "cache_control_must_include_no_store")

        leaking_ref = verify_ucp_permalink_redirect(
            303, {**valid_headers, "Referrer-Policy": "origin-when-cross-origin"}
        )
        self.assertFalse(leaking_ref.accepted)
        self.assertEqual(leaking_ref.reason, "referrer_policy_must_be_no_referrer")

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

    def test_ucp_multi_entry_identity_authorization_server_selection(self) -> None:
        # Custom vanity domain fails RFC 8414 §3.3 exact issuer match, but second entry succeeds (#891)
        prm = {
            "resource": "https://www.merchant.example.com",
            "authorization_servers": [
                "https://account.merchant.example.com",
                "https://auth.provider.example/authentication/12345",
            ],
            "bearer_methods_supported": ["header"],
        }
        metadata_by_entry = {
            "https://account.merchant.example.com": {
                "issuer": "https://auth.provider.example/authentication/12345",
            },
            "https://auth.provider.example/authentication/12345": {
                "issuer": "https://auth.provider.example/authentication/12345",
            },
        }
        res = select_ucp_identity_authorization_server(
            protected_resource_metadata=prm,
            expected_resource="https://www.merchant.example.com",
            oauth_metadata_by_entry=metadata_by_entry,
            usable_client_issuers={"https://auth.provider.example/authentication/12345"},
        )
        self.assertEqual(res.selected_issuer, "https://auth.provider.example/authentication/12345")
        self.assertEqual(res.reason, "selected")
        self.assertEqual(
            res.discarded_entries,
            (("https://account.merchant.example.com", "issuer_mismatch"),),
        )

        # If no entry passes both RFC 8414 §3.3 and usable client identity, discovery fails cleanly
        none_ok = select_ucp_identity_authorization_server(
            protected_resource_metadata=prm,
            expected_resource="https://www.merchant.example.com",
            oauth_metadata_by_entry=metadata_by_entry,
            usable_client_issuers=set(),
        )
        self.assertIsNone(none_ok.selected_issuer)
        self.assertEqual(none_ok.reason, "no_valid_authorization_server")

    def test_ucp_mandate_liveness_evaluated_once_at_admission(self) -> None:
        # Valid at admission (evaluated_at <= mandate_exp) -> settles even if wall clock passes mandate_exp
        admitted = evaluate_ucp_mandate_admission(
            reference="ap2_mandate_sha256_abc",
            checkout_id="chk_100",
            mandate_exp=1700000100,
            evaluated_at=1700000090,
            settlement_completed_at=1700000150,
        )
        self.assertTrue(admitted.admitted)
        self.assertEqual(admitted.checkout_status, "completed")
        self.assertIsNone(admitted.error_code)
        self.assertEqual(admitted.admission_evidence["result"], "admitted")

        # Expired at admission (evaluated_at > mandate_exp) -> canceled with mandate_expired
        expired = evaluate_ucp_mandate_admission(
            reference="ap2_mandate_sha256_abc",
            checkout_id="chk_101",
            mandate_exp=1700000100,
            evaluated_at=1700000101,
        )
        self.assertFalse(expired.admitted)
        self.assertEqual(expired.checkout_status, "canceled")
        self.assertEqual(expired.error_code, "mandate_expired")
        self.assertEqual(expired.admission_evidence["result"], "expired_at_admission")

    def test_ucp_permalink_input_validation_item_tokens_and_continue_to(self) -> None:
        # Raw vs ~base64url item ID token encoding/decoding (permalink.md #Item ID Token)
        self.assertEqual(encode_ucp_item_id_token("sku_123-A.1"), "sku_123-A.1")
        uri_token = encode_ucp_item_id_token("gid://shop/ProductVariant/42")
        self.assertTrue(uri_token.startswith("~"))
        self.assertEqual(decode_ucp_item_id_token(uri_token), "gid://shop/ProductVariant/42")
        with self.assertRaisesRegex(ValueError, "percent_encoded_item_token_forbidden"):
            decode_ucp_item_id_token("sku%2F42")
        with self.assertRaisesRegex(ValueError, "non_canonical_tilde_base64url"):
            decode_ucp_item_id_token("~c2t1=")

        # 5-step continue_to validation (permalink.md #Destination Preference)
        dest_ok, fallback_ok = validate_ucp_continue_to("/cart?promo=SAVE10", default_destination="/checkout")
        self.assertEqual((dest_ok, fallback_ok), ("/cart?promo=SAVE10", False))
        for unsafe in (
            "//evil.example/phish",
            "https://evil.example/phish",
            "/%2f/evil.example",
            "/\\evil.example",
            "/cart\r\nSet-Cookie: session=evil",
        ):
            dest_fb, used_fb = validate_ucp_continue_to(unsafe, default_destination="/checkout")
            self.assertEqual((dest_fb, used_fb), ("/checkout", True))

        # Valid permalink request with compact path authority over line_items/0/quantity
        valid = validate_ucp_permalink_request(
            f"https://merchant.example/buy/sku_1:2,{uri_token}:1"
            "?buyer/email=jane%40example.com&line_items/0/quantity=99&line_items/0/selling_plan=monthly"
            "&continue_to=/cart&utm_source=agent",
            configured_endpoint="https://merchant.example/buy",
        )
        self.assertTrue(valid.accepted)
        self.assertEqual(
            valid.resolved_line_items,
            (
                {"item": {"id": "sku_1"}, "quantity": 2},
                {"item": {"id": "gid://shop/ProductVariant/42"}, "quantity": 1},
            ),
        )
        # Compact path quantity (2) stays authoritative over query parameter (99)
        self.assertEqual(valid.applied_ucp_fields["/line_items/0/quantity"], "2")
        self.assertEqual(valid.applied_ucp_fields["/line_items/0/selling_plan"], "monthly")
        self.assertEqual(valid.non_ucp_params, {"utm_source": "agent"})
        self.assertEqual(valid.resolved_continue_to, "/cart")

        # Canonical JSON Pointer collision (`buyer/email` and `/buyer/email`) rejected
        collision = validate_ucp_permalink_request(
            "https://merchant.example/buy/sku_1:1?buyer/email=a@example.com&/buyer/email=b@example.com",
            configured_endpoint="https://merchant.example/buy",
        )
        self.assertFalse(collision.accepted)
        self.assertEqual(collision.reason, "duplicate_ucp_pointer_collision")

        # Server-owned fields (`totals`, `status`, `order`) rejected
        server_owned = validate_ucp_permalink_request(
            "https://merchant.example/buy/sku_1:1?totals/0/amount=0",
            configured_endpoint="https://merchant.example/buy",
        )
        self.assertFalse(server_owned.accepted)
        self.assertEqual(server_owned.reason, "server_owned_field_forbidden")

        # Forbidden credentials / mandates / tokens in permalink URL rejected
        secret_leak = validate_ucp_permalink_request(
            "https://merchant.example/buy/sku_1:1?shared_payment_granted_token=spt_test_123",
            configured_endpoint="https://merchant.example/buy",
        )
        self.assertFalse(secret_leak.accepted)
        self.assertEqual(secret_leak.reason, "forbidden_secret_or_credential_in_permalink")

    def test_ucp_buyer_consent_carve_out_segment_override_and_missing_data_gate(self) -> None:
        advertised = {
            "dev.ucp.consent.analytics": {
                "granted": True,
                "source": "business",
                "description": "Measure site usage",
            },
            "dev.ucp.consent.marketing": {
                "granted": False,
                "source": "business",
                "description": "Promotional messages",
                "segments": {
                    "dev.ucp.consent.marketing.email": {"granted": False, "source": "business"},
                    "dev.ucp.consent.marketing.sms": {"granted": False, "source": "business"},
                },
            },
        }
        # 1. Platform submits buyer-stated SMS marketing opt-in + analytics opt-out
        submitted = {
            "dev.ucp.consent.analytics": {"granted": False, "source": "platform"},
            "dev.ucp.consent.marketing": {
                "granted": False,
                "source": "business",
                "segments": {
                    "dev.ucp.consent.marketing.email": {"granted": False, "source": "business"},
                    "dev.ucp.consent.marketing.sms": {"granted": True, "source": "platform"},
                },
            },
            "vendor.unknown.unadvertised": {"granted": True, "source": "platform"},
        }
        create_res = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=None,
            submitted_consent=submitted,
            operation="create",
            buyer_stated_keys={"dev.ucp.consent.analytics", "dev.ucp.consent.marketing.sms"},
            buyer_info={"email": "jane@example.com"},
        )
        self.assertTrue(create_res.accepted)
        self.assertEqual(create_res.reason, "verified_with_warnings")
        self.assertEqual(
            create_res.missing_dependency_codes,
            ("dev.ucp.consent.marketing.sms->$.buyer.phone_number",),
        )
        self.assertNotIn("vendor.unknown.unadvertised", create_res.effective_consent)

        # Segment overrides parent purpose (Normative Rule 4)
        self.assertFalse(
            resolve_ucp_effective_consent(
                create_res.effective_consent, purpose="dev.ucp.consent.marketing"
            )
        )
        self.assertTrue(
            resolve_ucp_effective_consent(
                create_res.effective_consent,
                purpose="dev.ucp.consent.marketing",
                segment="dev.ucp.consent.marketing.sms",
            )
        )

        # 2. Full-replacement carve-out (#660): omitting consent on update retains prior consent
        update_omitted = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=create_res.effective_consent,
            submitted_consent=None,
            operation="update",
            buyer_info={"email": "jane@example.com"},
        )
        self.assertTrue(update_omitted.accepted)
        self.assertEqual(update_omitted.effective_consent, create_res.effective_consent)

        # 3. Complete checkout is blocked while SMS consent is granted without phone_number
        complete_blocked = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=create_res.effective_consent,
            submitted_consent=None,
            operation="complete",
            buyer_info={"email": "jane@example.com"},
        )
        self.assertFalse(complete_blocked.accepted)
        self.assertEqual(complete_blocked.reason, "missing_consent_data_blocks_complete")

        # Providing buyer.phone_number unblocks completion
        complete_ok = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=create_res.effective_consent,
            submitted_consent=None,
            operation="complete",
            buyer_info={"email": "jane@example.com", "phone_number": "+14155550199"},
        )
        self.assertTrue(complete_ok.accepted)
        self.assertEqual(complete_ok.reason, "verified")

        # 4. Partial map (omitting an advertised key) or unauthored mutation is rejected
        partial = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=None,
            submitted_consent={"dev.ucp.consent.analytics": {"granted": True, "source": "business"}},
            operation="update",
        )
        self.assertFalse(partial.accepted)
        self.assertIn("missing_advertised_purpose", partial.reason)

        unauthored = validate_and_merge_ucp_buyer_consent(
            advertised_consent=advertised,
            prior_consent=None,
            submitted_consent=submitted,
            operation="update",
            buyer_stated_keys=set(),  # No buyer preference recorded for this business
        )
        self.assertFalse(unauthored.accepted)
        self.assertIn("unauthored_consent_mutation", unauthored.reason)

    def test_ucp_checkout_escalation_and_return_policy_contracts(self) -> None:
        # Checkout requires_escalation requires HTTPS continue_url (checkout/index.md & PR #912)
        self.assertFalse(
            verify_ucp_checkout_escalation_contract(
                {"status": "requires_escalation"}, direction="response"
            ).accepted
        )
        self.assertFalse(
            verify_ucp_checkout_escalation_contract(
                {"status": "requires_escalation", "continue_url": "http://merchant.example/esc"},
                direction="response",
            ).accepted
        )
        self.assertTrue(
            verify_ucp_checkout_escalation_contract(
                {"status": "requires_escalation", "continue_url": "https://merchant.example/esc"},
                direction="response",
            ).accepted
        )
        self.assertFalse(
            verify_ucp_checkout_escalation_contract(
                {"continue_url": "https://merchant.example/esc"}, direction="request"
            ).accepted
        )

        # Return policy (#966): platform date math forbidden, omitted eligibility != unlimited
        no_math = evaluate_ucp_return_policy(
            {
                "type": "dev.ucp.shopping.policy.return",
                "eligibility": {"type": "window", "duration": "P30D", "anchor": "delivered"},
            },
            platform_computed_expires_at="2026-11-17T00:00:00Z",
        )
        self.assertFalse(no_math.valid_schema)
        self.assertEqual(no_math.reason, "platform_date_math_forbidden")

        omitted_elig = evaluate_ucp_return_policy(
            {"type": "dev.ucp.shopping.policy.return", "description": "See store terms"}
        )
        self.assertTrue(omitted_elig.valid_schema)
        self.assertEqual(omitted_elig.eligibility_status, "unstructured_or_unknown_no_inference")

        # Window expiry is a minimum floor, not a prohibition ceiling
        lapsed = evaluate_ucp_return_policy(
            {
                "type": "dev.ucp.shopping.policy.return",
                "eligibility": {
                    "type": "window",
                    "duration": "P30D",
                    "anchor": "purchased",
                    "expires_at": "2026-10-10T00:00:00Z",
                },
                "fees": [
                    {"type": "dev.ucp.shopping.fee.restocking", "basis_points": 1500, "max_amount": 2500},
                ],
            },
            now_iso="2026-10-18T00:00:00Z",
        )
        self.assertTrue(lapsed.valid_schema)
        self.assertEqual(lapsed.eligibility_status, "window_floor_lapsed_not_prohibited")

        # Fee validation: amount + basis_points mutually exclusive; not_accepted forbids fees
        bad_fee = evaluate_ucp_return_policy(
            {
                "type": "dev.ucp.shopping.policy.return",
                "eligibility": {"type": "window", "duration": "P30D", "anchor": "delivered"},
                "fees": [{"type": "dev.ucp.shopping.fee.restocking", "amount": 500, "basis_points": 1000}],
            }
        )
        self.assertFalse(bad_fee.valid_schema)
        self.assertEqual(bad_fee.reason, "fee_amount_and_basis_points_mutually_exclusive")

        bad_not_accepted = evaluate_ucp_return_policy(
            {
                "type": "dev.ucp.shopping.policy.return",
                "eligibility": {"type": "not_accepted"},
                "supported_resolutions": ["refund"],
            }
        )
        self.assertFalse(bad_not_accepted.valid_schema)
        self.assertEqual(
            bad_not_accepted.reason, "resolutions_methods_fees_forbidden_on_not_accepted"
        )


if __name__ == "__main__":
    unittest.main()

