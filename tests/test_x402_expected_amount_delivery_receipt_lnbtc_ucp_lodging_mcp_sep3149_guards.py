"""Unit tests for Stage 230 deterministic protocol guards (PR-01..PR-16 · 230-Stage Milestone!)."""

from __future__ import annotations

import hashlib
import unittest

from lab.x402_expected_amount_delivery_receipt_lnbtc_ucp_lodging_mcp_sep3149_guards import (
    _canonical_jcs,
    evaluate_mcp_apps_webmcp_screenshot_and_peer_line_guard,
    evaluate_mcp_conformance_sep1932_dpop_discovery_and_proof_guard,
    evaluate_mcp_conformance_sep3415_events_suite_guard,
    evaluate_mcp_java_sdk_param_header_flush_roots_guard,
    evaluate_mcp_kotlin_sdk_flow_stdio_cancel_sse_guard,
    evaluate_mcp_php_sdk_reconnect_close_and_finder_guard,
    evaluate_mcp_registry_http_auth_and_sigstore_installer_guard,
    evaluate_mcp_registry_repo_id_and_argument_validator_guard,
    evaluate_mcp_ruby_sdk_listen_auth_and_notify_rescue_guard,
    evaluate_mcp_sep3149_cimd_and_sep2633_mcp_json_guard,
    evaluate_mcp_swift_sdk_data_url_and_heartbeat_guard,
    evaluate_ucp_guest_order_credentials_and_mcp_signing_guard,
    evaluate_ucp_lodging_schedule_cart_continue_price_treatment_guard,
    evaluate_x402_delivery_receipt_and_offer_vector_guard,
    evaluate_x402_expected_amount_and_pinned_recipient_guard,
    evaluate_x402_lnbtc_and_atto_exact_guard,
)


class Stage230GuardsTest(unittest.TestCase):
    def test_pr01_to_pr08_positive_and_negative_guards(self) -> None:
        r1 = evaluate_x402_expected_amount_and_pinned_recipient_guard(
            quote_key="GET:https://api.example.com/v1/Alpha",
            offered_amount_atomic="10000",
            max_amount_per_payment_atomic=1_000_000,
            expected_amount_mode="first-accepted",
            explicit_expected_atomic=None,
            first_accepted_ledger={"GET:https://api.example.com/v1/Alpha": 10000},
            expected_amount_tolerance=1.05,
            offered_network="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            offered_pay_to="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            offered_asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            expected_network="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            expected_pay_to="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            expected_asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        )
        self.assertTrue(r1.passed)
        r1_bad = evaluate_x402_expected_amount_and_pinned_recipient_guard(
            quote_key="GET:https://api.example.com/v1/Alpha",
            offered_amount_atomic="2000",
            max_amount_per_payment_atomic=1_000_000,
            expected_amount_mode="first-accepted",
            explicit_expected_atomic=None,
            first_accepted_ledger={"GET:https://api.example.com/v1/Alpha": 10000},
            expected_amount_tolerance=1.05,
            offered_network="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            offered_pay_to="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            offered_asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            expected_network="solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
            expected_pay_to="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            expected_asset="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        )
        self.assertFalse(r1_bad.passed)

        payload = {"requestHash": "r1", "responseDigest": "d1"}
        rid = hashlib.sha256(_canonical_jcs(payload).encode("utf-8")).hexdigest()
        r2 = evaluate_x402_delivery_receipt_and_offer_vector_guard(
            receipt_payload=payload,
            claimed_receipt_id=rid,
            signed_octets=f"x402-delivery-receipt/1\n{rid}",
            delivery_mode="reference",
            payment_response_member_bytes=400,
            session_sig_alg="Ed25519",
            session_sig_valid=True,
            archival_sig_alg="ML-DSA-65",
            archival_sig_valid=True,
            key_directory_epoch_chained=True,
            offer_jws_segments=3,
            offer_jws_alg="EdDSA",
        )
        self.assertTrue(r2.passed)
        r2_bad = evaluate_x402_delivery_receipt_and_offer_vector_guard(
            receipt_payload=payload,
            claimed_receipt_id=rid,
            signed_octets=f"x402-delivery-receipt/1\n{rid}",
            delivery_mode="reference",
            payment_response_member_bytes=400,
            session_sig_alg="Ed25519",
            session_sig_valid=True,
            archival_sig_alg="ML-DSA-65",
            archival_sig_valid=True,
            key_directory_epoch_chained=True,
            offer_jws_segments=3,
            offer_jws_alg="HS256",
        )
        self.assertFalse(r2_bad.passed)

        preimage = "22" * 32
        phash = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()
        r3 = evaluate_x402_lnbtc_and_atto_exact_guard(
            binding_profile="http:1",
            binding_source="server_live_request",
            body_hashed_from_raw_bytes=True,
            is_paid_retry=True,
            reused_accepted_invoice=True,
            preimage_hex=preimage,
            expected_payment_hash_hex=phash,
            consumed_payment_hashes=set(),
            atto_network="atto:live",
            atto_amount_str="1000",
            atto_tx_type="SEND",
            atto_pow_and_sig_valid=True,
            atto_sender_frontier_competing=False,
        )
        self.assertTrue(r3.passed)
        r3_bad = evaluate_x402_lnbtc_and_atto_exact_guard(
            binding_profile="http:1",
            binding_source="client_echo",
            body_hashed_from_raw_bytes=True,
            is_paid_retry=True,
            reused_accepted_invoice=False,
            preimage_hex=preimage,
            expected_payment_hash_hex=phash,
            consumed_payment_hashes=set(),
            atto_network="atto:live",
            atto_amount_str="1000",
            atto_tx_type="SEND",
            atto_pow_and_sig_valid=True,
            atto_sender_frontier_competing=False,
        )
        self.assertFalse(r3_bad.passed)

        r4 = evaluate_ucp_lodging_schedule_cart_continue_price_treatment_guard(
            cancellation_schedule=[{"id": "free", "starts_at": 10, "ends_at": 20}],
            evaluation_epoch=15,
            selected_tier_id="free",
            cart_continue_url="https://shop.example.com/cart?id=1",
            cart_purchasable=True,
            continue_url_preserves_items=True,
            continue_url_has_remediation_fallback=True,
            price_treatment_tax_inclusion="included",
            allof_node_has_properties_key=False,
            allof_top_level_required=["day", "opens", "closes"],
            projected_required=["day", "opens", "closes"],
        )
        self.assertTrue(r4.passed)
        r4_bad = evaluate_ucp_lodging_schedule_cart_continue_price_treatment_guard(
            cancellation_schedule=[{"id": "free", "starts_at": 10, "ends_at": 20}],
            evaluation_epoch=15,
            selected_tier_id="free",
            cart_continue_url="https://shop.example.com/cart?id=1",
            cart_purchasable=True,
            continue_url_preserves_items=True,
            continue_url_has_remediation_fallback=True,
            price_treatment_tax_inclusion="included",
            allof_node_has_properties_key=False,
            allof_top_level_required=["day", "opens", "closes"],
            projected_required=[],
        )
        self.assertFalse(r4_bad.passed)

        r5 = evaluate_mcp_sep3149_cimd_and_sep2633_mcp_json_guard(
            cimd_metadata={"token_endpoint_auth_methods_supported": ["private_key_jwt"]},
            as_supported_auth_methods=["private_key_jwt"],
            mcp_json_config={"mcpServers": {"s1": {"type": "http"}}},
        )
        self.assertTrue(r5.passed)
        r5_bad = evaluate_mcp_sep3149_cimd_and_sep2633_mcp_json_guard(
            cimd_metadata={"token_endpoint_auth_method": "private_key_jwt"},
            as_supported_auth_methods=["private_key_jwt"],
            mcp_json_config={"mcpServers": {"s1": {"type": "http"}}},
        )
        self.assertFalse(r5_bad.passed)

        r6 = evaluate_mcp_java_sdk_param_header_flush_roots_guard(
            registered_tool_names=["t1"],
            header_marked_params={"Tenant": "acme"},
            http_mcp_param_headers={"Mcp-Param-Tenant": "acme"},
            idle_get_headers_flushed_immediately=True,
            client_initialized=False,
            client_supports_roots=False,
            server_called_list_roots=True,
            threw_illegal_state_before_session=True,
        )
        self.assertTrue(r6.passed)
        r6_bad = evaluate_mcp_java_sdk_param_header_flush_roots_guard(
            registered_tool_names=["t1"],
            header_marked_params={"Tenant": "acme"},
            http_mcp_param_headers={"Mcp-Param-Tenant": "evil"},
            idle_get_headers_flushed_immediately=True,
            client_initialized=False,
            client_supports_roots=False,
            server_called_list_roots=True,
            threw_illegal_state_before_session=True,
        )
        self.assertFalse(r6_bad.passed)

        r7 = evaluate_mcp_kotlin_sdk_flow_stdio_cancel_sse_guard(
            requests_sent_before_flow_collect=0,
            pages_fetched_lazily_one_by_one=True,
            handler_threw_cancellation=True,
            transport_scope_active=True,
            stdio_read_loop_kept_running=True,
            sse_transport_marked_deprecated_sep2596=True,
        )
        self.assertTrue(r7.passed)
        r7_bad = evaluate_mcp_kotlin_sdk_flow_stdio_cancel_sse_guard(
            requests_sent_before_flow_collect=0,
            pages_fetched_lazily_one_by_one=True,
            handler_threw_cancellation=True,
            transport_scope_active=True,
            stdio_read_loop_kept_running=False,
            sse_transport_marked_deprecated_sep2596=True,
        )
        self.assertFalse(r7_bad.passed)

        r8 = evaluate_mcp_swift_sdk_data_url_and_heartbeat_guard(
            data_url="data:text/plain,hello;base64,world",
            expected_is_base64=False,
            expected_decoded_bytes=b"hello;base64,world",
            heartbeat_post_backoff_states=["disconnected", "cancelled"],
        )
        self.assertTrue(r8.passed)
        r8_bad = evaluate_mcp_swift_sdk_data_url_and_heartbeat_guard(
            data_url="data:application/octet-stream,%FG",
            expected_is_base64=False,
            expected_decoded_bytes=b"\xff",
            heartbeat_post_backoff_states=["disconnected"],
        )
        self.assertFalse(r8_bad.passed)

    def test_pr09_to_pr16_positive_and_negative_guards(self) -> None:
        r9 = evaluate_mcp_ruby_sdk_listen_auth_and_notify_rescue_guard(
            requested_resource_uris=["file:///a"],
            allowed_resource_uris={"file:///a"},
            consulted_resources_subscribe_handler=True,
            notify_transport_failed=True,
            used_public_configuration_exception_reporter=True,
            leaked_no_method_error_to_tool_caller=False,
        )
        self.assertTrue(r9.passed)
        r9_bad = evaluate_mcp_ruby_sdk_listen_auth_and_notify_rescue_guard(
            requested_resource_uris=["file:///secret"],
            allowed_resource_uris={"file:///a"},
            consulted_resources_subscribe_handler=False,
            notify_transport_failed=True,
            used_public_configuration_exception_reporter=False,
            leaked_no_method_error_to_tool_caller=True,
        )
        self.assertFalse(r9_bad.passed)

        r10 = evaluate_mcp_php_sdk_reconnect_close_and_finder_guard(
            previous_transport_closed_on_reconnect=True,
            replacement_transport_closed_on_disconnect=True,
            file_discovery_configured=True,
            custom_discoverer_used=False,
            symfony_finder_installed=False,
            failed_fast_at_server_build=True,
        )
        self.assertTrue(r10.passed)
        r10_bad = evaluate_mcp_php_sdk_reconnect_close_and_finder_guard(
            previous_transport_closed_on_reconnect=False,
            replacement_transport_closed_on_disconnect=True,
            file_discovery_configured=True,
            custom_discoverer_used=False,
            symfony_finder_installed=False,
            failed_fast_at_server_build=False,
        )
        self.assertFalse(r10_bad.passed)

        r11 = evaluate_mcp_apps_webmcp_screenshot_and_peer_line_guard(
            view_tools_exposed_via_model_context=True,
            relay_is_same_origin_sandbox_proxy=True,
            map_server_exposes_get_screenshot=True,
            host_mcp_sdk_major=1,
            selected_ext_apps_major=1,
        )
        self.assertTrue(r11.passed)
        r11_bad = evaluate_mcp_apps_webmcp_screenshot_and_peer_line_guard(
            view_tools_exposed_via_model_context=True,
            relay_is_same_origin_sandbox_proxy=True,
            map_server_exposes_get_screenshot=False,
            host_mcp_sdk_major=1,
            selected_ext_apps_major=2,
        )
        self.assertFalse(r11_bad.passed)

        r12 = evaluate_mcp_conformance_sep1932_dpop_discovery_and_proof_guard(
            www_authenticate_schemes=["DPoP"],
            prm_dpop_algs_supported=["ES256"],
            token_request_has_dpop_proof=True,
            proof_iat_skew_seconds=2,
            max_iat_skew_seconds=60,
            retried_on_use_dpop_nonce=True,
        )
        self.assertTrue(r12.passed)
        r12_bad = evaluate_mcp_conformance_sep1932_dpop_discovery_and_proof_guard(
            www_authenticate_schemes=["Bearer"],
            prm_dpop_algs_supported=[],
            token_request_has_dpop_proof=False,
            proof_iat_skew_seconds=200,
            max_iat_skew_seconds=60,
            retried_on_use_dpop_nonce=False,
        )
        self.assertFalse(r12_bad.passed)

        r13 = evaluate_mcp_conformance_sep3415_events_suite_guard(
            events_list_supported=True,
            subscription_listen_mcp_name_header_valid=True,
            negative_controls_rejected_count=150,
            duplicate_event_id_deduplicated=True,
            cursor_resume_replayed_missed_events=True,
        )
        self.assertTrue(r13.passed)
        r13_bad = evaluate_mcp_conformance_sep3415_events_suite_guard(
            events_list_supported=True,
            subscription_listen_mcp_name_header_valid=False,
            negative_controls_rejected_count=10,
            duplicate_event_id_deduplicated=False,
            cursor_resume_replayed_missed_events=False,
        )
        self.assertFalse(r13_bad.passed)

        r14 = evaluate_mcp_registry_http_auth_and_sigstore_installer_guard(
            http_status=200,
            accept_header="text/plain",
            user_agent="mcp-registry/1.0",
            proof_body_bytes=256,
            elapsed_seconds=0.8,
            installer_version_tag="v1.8.1",
            cosign_verify_blob_passed=True,
            extracted_before_verify=False,
        )
        self.assertTrue(r14.passed)
        r14_bad = evaluate_mcp_registry_http_auth_and_sigstore_installer_guard(
            http_status=302,
            accept_header="text/plain",
            user_agent="mcp-registry/1.0",
            proof_body_bytes=256,
            elapsed_seconds=0.8,
            installer_version_tag="latest",
            cosign_verify_blob_passed=False,
            extracted_before_verify=True,
        )
        self.assertFalse(r14_bad.passed)

        r15 = evaluate_mcp_registry_repo_id_and_argument_validator_guard(
            repository_block={"url": "https://github.com/a/b", "id": "R_123"},
            arguments=[{"type": "positional", "value": "src"}],
        )
        self.assertTrue(r15.passed)
        r15_bad = evaluate_mcp_registry_repo_id_and_argument_validator_guard(
            repository_block={"url": "https://github.com/a/b"},
            arguments=[{"type": "positional"}],
        )
        self.assertFalse(r15_bad.passed)

        r16 = evaluate_ucp_guest_order_credentials_and_mcp_signing_guard(
            token_scoped_order_id="ord_1",
            requested_order_id="ord_1",
            token_scopes=["order:read"],
            order_claimed_by_account=True,
            guest_token_revoked=True,
            mcp_order_message_signed=True,
            mcp_signature_verified=True,
            mcp_payload_digest_matches=True,
        )
        self.assertTrue(r16.passed)
        r16_bad = evaluate_ucp_guest_order_credentials_and_mcp_signing_guard(
            token_scoped_order_id="ord_1",
            requested_order_id="ord_2",
            token_scopes=["order:read"],
            order_claimed_by_account=True,
            guest_token_revoked=False,
            mcp_order_message_signed=False,
            mcp_signature_verified=False,
            mcp_payload_digest_matches=False,
        )
        self.assertFalse(r16_bad.passed)


if __name__ == "__main__":
    unittest.main()
