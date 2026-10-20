"""Unit tests for Stage 86 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_guard import (
    build_erc8021_suffix,
    validate_acp_rejected_discount_and_message_resolution_guard,
    validate_tau2_buffered_audio_drain_and_hospitality_guard,
    validate_ucp_attribute_inheritance_and_message_path_guard,
    validate_x402_no_wallet_and_erc8021_builder_code_guard,
)


class Stage86GuardTests(unittest.TestCase):
    def test_ucp_attribute_inheritance_and_message_path_valid(self) -> None:
        payload = {
            "product_attributes": [
                {
                    "name": "Display size",
                    "key": "display_size",
                    "value": "6.3 inches",
                    "numeric_value": 6.3,
                    "unit": "inches",
                },
                {
                    "name": "Weight",
                    "key": "weight",
                    "value": "174 g",
                    "numeric_value": 174,
                    "unit": "g",
                },
            ],
            "variant_attributes": [
                {
                    "name": "Weight",
                    "key": "weight",
                    "value": "178 g",
                    "numeric_value": 178,
                    "unit": "g",
                },
                {
                    "name": "Storage",
                    "key": "storage_capacity",
                    "value": "256 GB",
                    "numeric_value": 256,
                    "unit": "GB",
                },
            ],
            "merged_variant_attributes": [
                {
                    "name": "Display size",
                    "key": "display_size",
                    "value": "6.3 inches",
                    "numeric_value": 6.3,
                    "unit": "inches",
                },
                {
                    "name": "Weight",
                    "key": "weight",
                    "value": "178 g",
                    "numeric_value": 178,
                    "unit": "g",
                },
                {
                    "name": "Storage",
                    "key": "storage_capacity",
                    "value": "256 GB",
                    "numeric_value": 256,
                    "unit": "GB",
                },
            ],
            "messages": [
                {
                    "type": "error",
                    "code": "invalid_phone",
                    "severity": "recoverable",
                    "path": "$.buyer.phone_number",
                    "content": "Phone number format is invalid",
                }
            ],
            "agent_recovery_action": {
                "targeted_field_path": "$.buyer.phone_number",
                "auto_retry_update_checkout": True,
            },
        }
        res = validate_ucp_attribute_inheritance_and_message_path_guard(payload)
        self.assertTrue(res["allowed"])

    def test_ucp_attribute_override_failure_and_legacy_items_path_blocked(self) -> None:
        payload = {
            "product_attributes": [
                {"name": "Weight", "key": "weight", "value": "174 g"}
            ],
            "variant_attributes": [
                {"name": "Weight", "key": "weight", "value": "178 g"}
            ],
            "merged_variant_attributes": [
                {"name": "Weight", "key": "weight", "value": "174 g"}
            ],
            "messages": [
                {
                    "type": "error",
                    "code": "out_of_stock",
                    "severity": "unrecoverable",
                    "path": "$.items[1]",
                    "content": "Out of stock",
                }
            ],
            "agent_recovery_action": {
                "auto_retry_update_checkout": True,
            },
        }
        res = validate_ucp_attribute_inheritance_and_message_path_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ucp_attribute_override_mismatch:key:weight", res["violations"])
        self.assertIn("message_0_legacy_items_jsonpath_forbidden", res["violations"])
        self.assertIn("unrecoverable_error_auto_retry_forbidden", res["violations"])

    def test_acp_rejected_discount_and_message_resolution_valid(self) -> None:
        payload = {
            "http_status": 200,
            "has_checkout_session": True,
            "discounts": {
                "applied": [
                    {
                        "id": "disc_1",
                        "code": "SAVE10",
                        "amount": 1000,
                        "allocations": [
                            {"path": "$.line_items[0]", "amount": 600},
                            {"path": "$.line_items[1]", "amount": 400},
                        ],
                    }
                ],
                "rejected": [
                    {
                        "code": "EXPIRED50",
                        "reason": "discount_code_expired",
                        "message": "Expired on Dec 1",
                    }
                ],
            },
            "messages": [
                {
                    "type": "warning",
                    "code": "discount_code_expired",
                    "resolution": "recoverable",
                    "param": "$.discounts.codes[1]",
                }
            ],
            "agent_auto_retry_or_place_order": True,
        }
        res = validate_acp_rejected_discount_and_message_resolution_guard(payload)
        self.assertTrue(res["allowed"])

    def test_acp_rejected_discount_and_buyer_review_bypass_blocked(self) -> None:
        payload = {
            "http_status": 200,
            "has_checkout_session": True,
            "top_level_error": {"type": "invalid_request", "code": "bad"},
            "discounts": {
                "applied": [
                    {
                        "id": "disc_1",
                        "code": "SAVE10",
                        "amount": 1000,
                        "allocations": [{"path": "$.line_items[0]", "amount": 500}],
                    }
                ],
                "rejected": [
                    {
                        "code": "BADCODE",
                        "reason": "invented_reason_code",
                    }
                ],
            },
            "messages": [
                {
                    "type": "error",
                    "code": "policy_gate",
                    "resolution": "requires_buyer_review",
                }
            ],
            "agent_auto_retry_or_place_order": True,
        }
        res = validate_acp_rejected_discount_and_message_resolution_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("acp_2xx_response_cannot_use_top_level_protocol_error", res["violations"])
        self.assertIn("applied_discount_0_allocation_sum_mismatch", res["violations"])
        self.assertIn("rejected_discount_0_invalid_error_code", res["violations"])
        self.assertIn(
            "acp_message_0_requires_buyer_review_blocks_autonomous_retry_or_order",
            res["violations"],
        )

    def test_x402_no_wallet_and_erc8021_builder_code_valid(self) -> None:
        base_calldata = "0xe3ee160e0000000000000000"
        suffix = build_erc8021_suffix("base_agent_01")
        payload = {
            "payment_requirements": {
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "network": "eip155:8453",
                "amount": "5000",
            },
            "no_wallet_extension": {
                "info": {
                    "anyWalletWorks": True,
                    "requires": {
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "network": "eip155:8453",
                        "amount": "5000",
                        "signing": "eip3009",
                    },
                    "freeAlternative": "https://api.example.com/preview",
                    "wallets": [
                        {
                            "name": "example-wallet",
                            "docs": "https://example.com/skill.md",
                            "install": "npx -y example-wallet",
                            "selfInstallable": True,
                            "custodial": False,
                        }
                    ],
                }
            },
            "client_context": {
                "has_signer": True,
                "asset_balance": 1000,
                "attempt_wallet_install": False,
                "auto_execute_wallet_install": False,
                "echoed_no_wallet_in_payment_payload": False,
            },
            "erc8021_settlement": {
                "builder_code": "base_agent_01",
                "base_calldata": base_calldata,
                "tx_data": f"{base_calldata}{suffix}",
            },
        }
        res = validate_x402_no_wallet_and_erc8021_builder_code_guard(payload)
        self.assertTrue(res["allowed"])

    def test_x402_no_wallet_auto_exec_and_erc8021_mismatch_blocked(self) -> None:
        payload = {
            "payment_requirements": {
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "network": "eip155:8453",
                "amount": "5000",
            },
            "no_wallet_extension": {
                "info": {
                    "anyWalletWorks": True,
                    "requires": {
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "network": "eip155:8453",
                        "amount": "999999",
                    },
                    "wallets": [
                        {
                            "name": "bad-wallet",
                            "docs": "http://insecure.example.com",
                        }
                    ],
                }
            },
            "client_context": {
                "has_signer": True,
                "asset_balance": 1000,
                "attempt_wallet_install": True,
                "auto_execute_wallet_install": True,
                "echoed_no_wallet_in_payment_payload": True,
            },
            "erc8021_settlement": {
                "builder_code": "base_agent_01",
                "base_calldata": "0xe3ee160e",
                "tx_data": "0xe3ee160edeadbeef",
            },
        }
        res = validate_x402_no_wallet_and_erc8021_builder_code_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "x402_no_wallet_requires_amount_mismatch_with_payment_requirements",
            res["violations"],
        )
        self.assertIn("x402_no_wallet_untrusted_install_auto_exec_forbidden", res["violations"])
        self.assertIn("erc8021_calldata_suffix_mismatch", res["violations"])

    def test_tau2_buffered_audio_drain_and_hospitality_valid(self) -> None:
        payload = {
            "full_duplex_finalize": {
                "buffered_audio_bytes_before_finalize": 4800,
                "ticks_count": 12,
                "drained_into_last_tick": True,
                "buffer_cleared_after_finalize": True,
                "last_tick_contains_speech": True,
            },
            "hospitality_turn": {
                "tool_calls_in_turn": 1,
                "has_guest_reply_in_same_turn": False,
                "operation": "cancel_reservation",
                "confirmation_number_verified": True,
                "guest_name_matches_reservation": True,
                "num_guests_including_children": 2,
                "room_capacity": 2,
                "num_rooms_requested": 1,
                "rate_plan_id": "RP_FLEX",
                "days_before_arrival": 1,
                "total_price_eur": 420,
                "first_night_price_eur": 140,
                "quoted_refund_eur": 280,
                "guest_confirmed_refund_before_cancel": True,
            },
        }
        res = validate_tau2_buffered_audio_drain_and_hospitality_guard(payload)
        self.assertTrue(res["allowed"])

    def test_tau2_undrained_audio_and_hospitality_saver_date_change_blocked(self) -> None:
        payload = {
            "full_duplex_finalize": {
                "buffered_audio_bytes_before_finalize": 4800,
                "ticks_count": 12,
                "drained_into_last_tick": False,
                "buffer_cleared_after_finalize": False,
                "last_tick_contains_speech": False,
            },
            "hospitality_turn": {
                "tool_calls_in_turn": 1,
                "has_guest_reply_in_same_turn": True,
                "operation": "modify_dates",
                "confirmation_number_verified": False,
                "guest_name_matches_reservation": True,
                "num_guests_including_children": 3,
                "room_capacity": 2,
                "num_rooms_requested": 5,
                "transferred_to_human_agents": False,
                "rate_plan_id": "RP_SAVER",
                "cancel_and_rebook_workaround_for_saver": True,
            },
        }
        res = validate_tau2_buffered_audio_drain_and_hospitality_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("tau2_buffered_agent_audio_not_drained_to_final_tick", res["violations"])
        self.assertIn("tau2_hospitality_saver_rate_date_change_forbidden", res["violations"])
        self.assertIn("tau2_hospitality_group_booking_over_4_rooms_requires_transfer", res["violations"])


if __name__ == "__main__":
    unittest.main()
