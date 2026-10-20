"""Unit tests for Stage 74 protocol and benchmark guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_guard import (
    compute_ap2_jcs_cart_mandate_hash,
    verify_acp_mandatory_idempotency_wellknown_discovery_sale_and_schema_alignment,
    verify_ap2_jcs_cart_hash_sdjwt_hops_execution_window_and_x402_stream_accepts,
    verify_tau2_gemini_8khz_telephony_goaway_reconnect_nonblocking_duplex_and_empty_turn_retry,
    verify_ucp_lodging_booking_token_binding_location_spatial_and_constraint_path,
)


class TestStage74Guards(unittest.TestCase):
    def _valid_ucp_payload(self) -> dict:
        return {
            "lodging_booking": {
                "guests": [
                    {"id": "gst_01", "first_name": "Jane", "last_name": "Doe"},
                    {"id": "gst_02", "first_name": "Mary", "last_name": "Doe"},
                ],
                "stays": [
                    {
                        "id": "stay_deluxe_king__rp_flexible",
                        "accommodation_type": {"id": "acc_deluxe_king"},
                        "rate_plan": {"id": "rp_flexible_breakfast"},
                        "stay_dates": {"start_date": "2026-07-15", "end_date": "2026-07-21"},
                        "guest_assignments": [
                            {"guest_id": "gst_01", "role": "primary_guest"},
                            {"guest_id": "gst_02", "role": "additional_guest"},
                        ],
                    }
                ],
                "policies": [
                    {
                        "type": "dev.ucp.lodging.policy.cancellation",
                        "refundability": "partially_refundable",
                        "description": {
                            "plain": "Cancel before July 10 for full refund; 1-night fee thereafter."
                        },
                        "url": "https://hotel.example.com/policies/cancellation",
                    }
                ],
            },
            "token_binding_check": {
                "mint_binding": {
                    "type": "dev.ucp.lodging.booking",
                    "id": "bkg_99281",
                    "vendor_hint": "ignored_open_member",
                },
                "burn_binding": {
                    "type": "dev.ucp.lodging.booking",
                    "id": "bkg_99281",
                },
                "minted_participant_id": "urn:ucp:participant:hotel_mor_01",
                "caller_is_target_business": True,
                "burn_identity": None,
            },
            "location_discovery": {
                "is_lookup": True,
                "request": {
                    "distance": {"lat": 37.7749, "lng": -122.4194, "radius_m": 5000},
                    "filters": {"items": ["item_1", "item_2"]},
                },
                "candidate_available_items": ["item_1", "item_2", "item_3"],
                "returned_locations": [
                    {
                        "id": "loc_sf_01",
                        "inputs": ["loc_sf_01"],
                        "amenities": {
                            "dev.ucp.amenity.shopping.curbside_pickup": {
                                "description": "Curbside pickup"
                            }
                        },
                    }
                ],
            },
            "request_constraint": {
                "path": "$.payment.instruments[?@.id=='pi_1'].amount",
                "inner_operators": [{"lte": 50000}],
                "anyOf": [{"eq": 25000}, {"eq": 50000}],
            },
        }

    def test_ucp_lodging_token_binding_location_and_constraint_valid(self) -> None:
        res = verify_ucp_lodging_booking_token_binding_location_spatial_and_constraint_path(
            self._valid_ucp_payload()
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["reasons"], [])
        self.assertEqual(res["guest_pool_count"], 2)

    def test_ucp_rejects_invalid_lodging_coupled_token_binding_and_legacy_location(self) -> None:
        bad = self._valid_ucp_payload()
        bad["lodging_booking"]["policies"][0]["refundability"] = "free_cancel"
        bad["token_binding_check"]["mint_binding"]["identity"] = "coupled_inside_binding"
        bad["location_discovery"]["request"]["filters"]["geo"] = {"radius": 10}
        bad["request_constraint"]["inner_operators"] = [{"path": "$.bad.inner", "eq": 1}]
        res = verify_ucp_lodging_booking_token_binding_location_spatial_and_constraint_path(bad)
        self.assertFalse(res["allowed"])
        self.assertIn("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid", res["reasons"])
        self.assertIn("ucp_token_binding_coupled_to_participant_identity_or_invalid_shape", res["reasons"])
        self.assertIn("ucp_location_spatial_filter_or_amenity_description_violation", res["reasons"])
        self.assertIn("ucp_request_constraint_inner_path_or_empty_anyof", res["reasons"])

    def _valid_acp_payload(self) -> dict:
        return {
            "post_idempotency": {
                "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
                "in_flight": False,
                "prior_payload_hash": "sha256:abc123",
                "current_payload_hash": "sha256:abc123",
                "is_cached_replay": True,
                "response_headers": {"Idempotent-Replayed": "true"},
            },
            "well_known_acp": {
                "requires_auth": False,
                "protocol_version": "2026-04-17",
                "api_base_url": "https://api.merchant.example.com/acp",
                "transports": ["rest", "mcp"],
                "currencies": ["USD", "EUR"],
                "locales": ["en-US"],
            },
            "discounts": {"codes": ["SUMMER20"], "applied": [], "rejected": []},
            "authentication_metadata": {
                "flow_preference": {"frictionless": {"type": "low_risk"}}
            },
            "sales": [{"id": "sale_flash_01", "name": "Summer Flash"}],
            "line_items": [
                {
                    "id": "li_01",
                    "amount": 8000,
                    "sale": {"sale_id": "sale_flash_01", "compare_at_amount": 10000},
                }
            ],
            "messages": [
                {"type": "info", "content_type": "plain", "content": "Express shipping selected"}
            ],
            "refunds": [{"id": "ref_01", "amount": 100}],
            "delegate_payment": {"risk_signals": [], "card": {"iin": "41111122"}},
        }

    def test_acp_idempotency_wellknown_sale_and_schema_valid(self) -> None:
        res = verify_acp_mandatory_idempotency_wellknown_discovery_sale_and_schema_alignment(
            self._valid_acp_payload()
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["http_status"], 200)

    def test_acp_rejects_idempotency_conflict_string_refund_and_bad_message_fields(self) -> None:
        bad = self._valid_acp_payload()
        bad["post_idempotency"]["current_payload_hash"] = "sha256:different"
        bad["well_known_acp"]["requires_auth"] = True
        bad["discounts"] = {"codes": [], "applied": []}  # missing rejected[]
        bad["messages"] = [{"id": "m1", "message": "wrong schema", "display_context": "banner"}]
        bad["refunds"] = [{"id": "ref_01", "amount": "1.00"}]
        res = verify_acp_mandatory_idempotency_wellknown_discovery_sale_and_schema_alignment(bad)
        self.assertFalse(res["allowed"])
        self.assertEqual(res["http_status"], 422)
        self.assertEqual(res["error_code"], "idempotency_conflict")
        self.assertIn("acp_post_idempotency_conflict_rejected", res["reasons"])
        self.assertIn("acp_well_known_discovery_document_invalid", res["reasons"])
        self.assertIn("acp_discount_rejected_or_sale_extension_invalid", res["reasons"])
        self.assertIn("acp_message_refund_iin_or_risk_signals_schema_mismatch", res["reasons"])

    def _valid_ap2_x402_payload(self) -> dict:
        cart = {
            "id": "cart_mandate_74",
            "merchant_id": "merch_01",
            "total_minor": 12500,
            "optional_note": None,
        }
        return {
            "cart_mandate": cart,
            "payment_mandate_contents": {
                "cart_mandate_id": "cart_mandate_74",
                "cart_mandate_hash": compute_ap2_jcs_cart_mandate_hash(cart),
            },
            "kb_sdjwt_hops": [
                {
                    "is_terminal": False,
                    "aud": "https://router.agent.example",
                    "nonce": "n_hop_1",
                    "expected_aud": "https://router.agent.example",
                    "expected_nonce": "n_hop_1",
                },
                {
                    "is_terminal": True,
                    "aud": "https://psp.merchant.example",
                    "nonce": "n_hop_2",
                    "expected_aud": "https://psp.merchant.example",
                    "expected_nonce": "n_hop_2",
                },
            ],
            "execution_window": {
                "not_before": "2026-10-20T00:00:00Z",
                "not_after": "2026-10-21T00:00:00Z",
                "execution_date": None,
                "verifier_utc_now": "2026-10-20T12:00:00Z",
            },
            "budget_check": {
                "budget_max_major": 200.0,
                "amount_range_max_minor": 15000,
                "total_spend_minor": 12500,
                "payment_amount_minor": 12500,
            },
            "x402_client": {
                "body_is_readable_stream": True,
                "request_cloned_before_unpaid_probe": True,
                "throw_on_unknown_accepts_entry": False,
                "supported_networks": ["eip155:8453"],
                "accepts": [
                    {"network": "eip155:137", "asset": "JPYC"},
                    {"network": "eip155:8453", "asset": "USDC"},
                ],
                "signer": {"address": "0x1111111111111111111111111111111111111111"},
                "eip712_domain": {
                    "name": "USD Coin",
                    "version": "2",
                    "chainId": 8453,
                    "verifyingContract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                },
            },
        }

    def test_ap2_jcs_sdjwt_execution_window_and_x402_valid(self) -> None:
        res = verify_ap2_jcs_cart_hash_sdjwt_hops_execution_window_and_x402_stream_accepts(
            self._valid_ap2_x402_payload()
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["selected_payable_network"], "eip155:8453")

    def test_ap2_and_x402_reject_tampered_jcs_unbound_hop_expired_window_and_uncloned_stream(self) -> None:
        bad = self._valid_ap2_x402_payload()
        bad["payment_mandate_contents"]["cart_mandate_hash"] = "deadbeef"
        bad["kb_sdjwt_hops"][1]["expected_aud"] = None  # terminal hop without expected_aud (#326)
        bad["execution_window"]["verifier_utc_now"] = "2026-10-22T00:00:00Z"
        bad["budget_check"]["total_spend_minor"] = 25000  # exceeds $200.00 (20000 cents)
        bad["x402_client"]["request_cloned_before_unpaid_probe"] = False
        res = verify_ap2_jcs_cart_hash_sdjwt_hops_execution_window_and_x402_stream_accepts(bad)
        self.assertFalse(res["allowed"])
        self.assertIn("ap2_jcs_cart_mandate_hash_mismatch", res["reasons"])
        self.assertIn("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound", res["reasons"])
        self.assertIn("ap2_immediate_payment_outside_execution_window", res["reasons"])
        self.assertIn("ap2_budget_major_vs_minor_unit_overflow", res["reasons"])
        self.assertIn("x402_stream_body_accepts_or_signer_address_violation", res["reasons"])

    def _valid_tau2_payload(self) -> dict:
        return {
            "gemini_live_config": {
                "input_sample_rate_hz": 8000,
                "client_side_ratecv_upsampling": False,
                "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                "context_compression_sliding_window": True,
                "transcription_language_codes": ["en-US"],
            },
            "goaway_watchdog": {
                "goaway_received": True,
                "server_went_silent": True,
                "deadline_checked_on_silent_stream": True,
                "reconnected_before_drop": True,
            },
            "full_duplex_runtime": {
                "nonblocking_user_generation": True,
                "text_only_llm_history": True,
                "duplicate_user_init": False,
            },
            "user_simulator_turn": {
                "initial_empty_completion": True,
                "retried_with_stop_reminder": True,
                "crashed_as_infrastructure_error": False,
            },
        }

    def test_tau2_gemini_8khz_goaway_duplex_and_empty_turn_retry_valid(self) -> None:
        res = verify_tau2_gemini_8khz_telephony_goaway_reconnect_nonblocking_duplex_and_empty_turn_retry(
            self._valid_tau2_payload()
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["input_sample_rate_hz"], 8000)

    def test_tau2_rejects_16khz_upsampling_missed_goaway_and_unretried_empty_turn(self) -> None:
        bad = self._valid_tau2_payload()
        bad["gemini_live_config"]["input_sample_rate_hz"] = 16000
        bad["goaway_watchdog"]["deadline_checked_on_silent_stream"] = False
        bad["full_duplex_runtime"]["nonblocking_user_generation"] = False
        bad["user_simulator_turn"]["crashed_as_infrastructure_error"] = True
        res = verify_tau2_gemini_8khz_telephony_goaway_reconnect_nonblocking_duplex_and_empty_turn_retry(
            bad
        )
        self.assertFalse(res["allowed"])
        self.assertIn("tau2_gemini_telephony_8khz_or_sliding_window_misconfigured", res["reasons"])
        self.assertIn("tau2_gemini_goaway_silent_server_missed_reconnect", res["reasons"])
        self.assertIn("tau2_full_duplex_tick_blocked_or_duplicate_user_init", res["reasons"])
        self.assertIn("tau2_empty_user_simulator_completion_unretried_crash", res["reasons"])


if __name__ == "__main__":
    unittest.main()
