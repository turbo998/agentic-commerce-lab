"""Unit tests for Stage 76 deterministic guard module."""

from __future__ import annotations

import hashlib
import json
import unittest

from lab.ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_guard import (
    verify_acp_post_purchase_order_lifecycle_resolution_intervention_and_version_negotiation,
    verify_ap2_sdjwt_delegation_chain_pef_attestation_and_x402_bazaar_facilitator_guard,
    verify_tau2_voice_role_flip_qwen_nested_tools_usage_cost_and_parallel_lease_guard,
    verify_ucp_payment_terms_deterministic_hours_policies_and_media_variants,
)


def _jcs_sha256(obj: object) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestStage76Guard(unittest.TestCase):
    def test_ucp_payment_terms_hours_policies_and_media_valid(self) -> None:
        payload = {
            "payment": {
                "selected_term_id": "net_30",
                "previous_selected_term_id": "net_15",
                "business_repriced_or_changed_term": True,
                "terms": [
                    {
                        "id": "net_30",
                        "schedules": [
                            {
                                "amount": 50000,
                                "description": "Due 30 days after invoice",
                                "due_at": "2026-11-20T00:00:00Z",
                            }
                        ],
                    }
                ],
                "instruments": [{"id": "inst_1", "amount": 50000}],
            },
            "location": {
                "timezone": "America/New_York",
                "hours": [
                    {"day": "tuesday", "opens": "09:00", "closes": "12:00"},
                    {"day": "tuesday", "opens": "13:00", "closes": "21:00"},
                ],
                "exceptions": [
                    {
                        "title": "Thanksgiving",
                        "valid_from": "2026-11-26",
                        "valid_through": "2026-11-26",
                    }
                ],
            },
            "location_filters": {"hours": {"open_at": "2026-10-20T17:00:00Z"}},
            "policies": [
                {
                    "type": "dev.ucp.shopping.policy.refund",
                    "description": {"plain": "Engraved items are final sale."},
                    "applies_to": ["$.line_items[1]"],
                    "final_sale": True,
                }
            ],
            "messages": [
                {"type": "warning", "code": "payment_term_changed"},
                {
                    "type": "warning",
                    "code": "dev.ucp.shopping.policy.refund",
                    "path": "$.line_items[1]",
                    "presentation": "disclosure",
                },
            ],
            "fulfillment_request": {
                "methods": [{"type": "pickup", "selected_destination_id": "store_nyc_1"}]
            },
            "media": [
                {
                    "type": "video",
                    "url": "https://cdn.example.com/product.mp4",
                    "duration": 18,
                    "sources": [
                        {
                            "url": "https://cdn.example.com/product.m3u8",
                            "mime_type": "application/vnd.apple.mpegurl",
                        }
                    ],
                }
            ],
        }
        res = verify_ucp_payment_terms_deterministic_hours_policies_and_media_variants(
            payload
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_payment_terms_hours_policies_and_media_violations(self) -> None:
        payload = {
            "payment": {
                "selected_term_id": "installment_3x",
                "previous_selected_term_id": "net_15",
                "business_repriced_or_changed_term": True,
                "split_payments": True,
                "terms": [
                    {
                        "id": "installment_3x",
                        "is_subscription": True,
                        "schedules": [
                            {"totals": [{"amount": 1000}], "description": ""},
                            {"amount": 1000, "description": "Second installment"},
                        ],
                    }
                ],
                "instruments": [{"id": "inst_1", "term_refs": ["installment_3x"]}],
            },
            "location": {
                "hours": [{"day": "tuesday", "open": "00:00", "close": "00:00"}],
                "exceptions": [
                    {
                        "from": "2026-11-26",
                        "through": "2026-11-27",
                        "valid_from": "2026-11-26",
                        "valid_through": "2026-11-27",
                        "opens": "09:00",
                    },
                    {
                        "valid_from": "2026-11-27",
                        "valid_through": "2026-11-28",
                    },
                ],
            },
            "location_filters": {"hours": {"open_now": True, "open_at": "2026-10-20T17:00:00"}},
            "policies": [
                {
                    "type": "dev.ucp.shopping.policy.refund",
                    "description": {"plain": "Final sale"},
                    "applies_to": ["$.line_items[0]"],
                    "final_sale": True,
                    "window": {"days": 30},
                }
            ],
            "messages": [],
            "fulfillment_request": {
                "methods": [
                    {
                        "type": "pickup",
                        "destinations": [{"id": "store_1"}],
                        "auto_selected_from_context_location": True,
                    }
                ]
            },
            "media": [
                {
                    "type": "external_video",
                    "url": "https://player.example.com/embed/1",
                    "sources": [{"url": "https://cdn.example.com/raw.mp4", "mime_type": "invalid"}],
                }
            ],
        }
        res = verify_ucp_payment_terms_deterministic_hours_policies_and_media_variants(
            payload
        )
        self.assertFalse(res["allowed"])
        for expected in (
            "UCP_DEPRECATED_INSTRUMENT_TERM_REFS_FORBIDDEN",
            "UCP_SUBSCRIPTION_IN_PAYMENT_TERMS_FORBIDDEN:installment_3x",
            "UCP_PAYMENT_SCHEDULE_TOTALS_ARRAY_FORBIDDEN:installment_3x:0",
            "UCP_MULTI_SCHEDULE_TERM_SPLIT_PAYMENT_COMPOSITION_FORBIDDEN",
            "UCP_PAYMENT_TERM_CHANGED_WARNING_REQUIRED",
            "UCP_LOCATION_IANA_TIMEZONE_REQUIRED",
            "UCP_HOURS_LEGACY_OPEN_CLOSE_KEYS_FORBIDDEN:0",
            "UCP_EXCEPTION_HOURS_OVERLAP_FORBIDDEN:1",
            "UCP_IMPLICIT_OPEN_NOW_FILTER_FORBIDDEN",
            "UCP_REFUND_POLICY_WINDOW_XOR_FINAL_SALE:0",
            "UCP_POLICY_DISCLOSURE_WARNING_MISSING:$.line_items[0]",
            "UCP_NON_SHIPPING_REQUEST_DESTINATIONS_AUTHORSHIP_FORBIDDEN:0:pickup",
            "UCP_CONTEXT_LOCATION_AUTO_DESTINATION_SELECTION_FORBIDDEN:0",
            "UCP_EXTERNAL_VIDEO_DIRECT_SOURCES_FORBIDDEN:0",
        ):
            self.assertIn(expected, res["violations"])

    def test_acp_order_lifecycle_resolution_and_version_negotiation_valid(self) -> None:
        payload = {
            "order": {
                "id": "ord_123",
                "line_items": [
                    {"id": "li_shoes", "quantity": {"ordered": 3, "shipped": 3}},
                    {"id": "li_shirts", "quantity": {"ordered": 2, "shipped": 0}},
                ],
                "fulfillments": [
                    {
                        "id": "ful_1",
                        "type": "shipping",
                        "line_items": [{"id": "li_shoes", "quantity": 3}],
                    }
                ],
                "adjustments": [{"id": "adj_1", "type": "refund", "amount": 2500}],
            },
            "messages": [
                {
                    "type": "error",
                    "code": "intervention_required",
                    "resolution": "requires_buyer_review",
                    "failure_context": "capability_mismatch",
                },
                {
                    "type": "error",
                    "code": "requires_3ds",
                    "resolution": "requires_buyer_input",
                    "failure_context": "missing_authentication_result_on_complete",
                },
            ],
            "http_error": {
                "type": "invalid_request",
                "code": "unsupported_api_version",
                "supported_versions": ["2026-01-30", "2025-09-29"],
            },
            "session_transition": {
                "updated_fulfillment_option_id": "fulfillment_option_456",
                "updated_fulfillment_cost_minor": 500,
                "updated_total_minor": 830,
                "terminal_fulfillment_option_id": "fulfillment_option_456",
                "terminal_fulfillment_cost_minor": 500,
                "terminal_total_minor": 830,
            },
        }
        res = verify_acp_post_purchase_order_lifecycle_resolution_intervention_and_version_negotiation(
            payload
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_acp_order_lifecycle_resolution_and_version_negotiation_violations(self) -> None:
        payload = {
            "order": {
                "line_items": [{"id": "li_shoes", "quantity": {"ordered": 2, "shipped": 3}}],
                "fulfillments": [
                    {
                        "id": "ful_1",
                        "type": "drone",
                        "line_items": [{"id": "unknown", "quantity": 1}],
                    }
                ],
                "adjustments": [{"id": "adj_1", "type": "cashback", "amount": 12.5}],
            },
            "messages": [
                {
                    "type": "error",
                    "code": "requires_3ds",
                    "resolution": "auto_fix",
                    "failure_context": "capability_mismatch",
                    "supported_versions": ["2026-01-30"],
                }
            ],
            "http_error": {
                "type": "invalid_request",
                "code": "unsupported_api_version",
                "supported_versions": [],
            },
            "session_transition": {
                "updated_fulfillment_option_id": "fulfillment_option_456",
                "updated_fulfillment_cost_minor": 500,
                "updated_total_minor": 830,
                "terminal_fulfillment_option_id": "fulfillment_option_123",
                "terminal_fulfillment_cost_minor": 100,
                "terminal_total_minor": 430,
            },
        }
        res = verify_acp_post_purchase_order_lifecycle_resolution_intervention_and_version_negotiation(
            payload
        )
        self.assertFalse(res["allowed"])
        for expected in (
            "ACP_ORDER_LINE_ITEM_QUANTITY_INVALID:0",
            "ACP_ORDER_FULFILLMENT_TYPE_INVALID:0:drone",
            "ACP_ORDER_ADJUSTMENT_TYPE_INVALID:0:cashback",
            "ACP_ORDER_ADJUSTMENT_MINOR_AMOUNT_INVALID:0",
            "ACP_MESSAGE_RESOLUTION_INVALID:0:auto_fix",
            "ACP_CAPABILITY_MISMATCH_REQUIRES_INTERVENTION_REQUIRED_CODE:0",
            "ACP_TOP_LEVEL_ERROR_FIELD_ON_SESSION_MESSAGE:0",
            "ACP_VERSION_ERROR_SUPPORTED_VERSIONS_REQUIRED",
            "ACP_SESSION_TERMINAL_FULFILLMENT_TOTAL_DRIFT",
        ):
            self.assertIn(expected, res["violations"])

    def test_ap2_sdjwt_chain_pef_and_x402_bazaar_facilitator_valid(self) -> None:
        inner_receipt = {
            "mandate_ref": "sha256:abc123",
            "compliance_verdict": "ALLOW",
            "settlement_result": "SETTLED",
            "composite_trust_verdict": "TRUSTED",
        }
        receipt_hash = _jcs_sha256(inner_receipt)
        pef_without_id = {
            "claim_type": "payment_settlement",
            "receipt": inner_receipt,
            "receipt_hash": receipt_hash,
        }
        frame_id = _jcs_sha256(pef_without_id)
        payload = {
            "sd_jwt_chain": "eyJ_hop0~disc0_a~disc0_b~~eyJ_hop1~disc1_a~eyJ_kb_final",
            "decoder_split_single_tilde_first": False,
            "session_state_entries": [{"serialized_via_model_dump": True}],
            "payment_evidence_frame": {
                **pef_without_id,
                "frame_id": frame_id,
                "signature": "sig_rfc9421",
            },
            "session_spend_cap_minor": 100000,
            "session_cumulative_spend_minor": 40000,
            "requested_payment_minor": 25000,
            "x402": {
                "bazaar_discovery": {
                    "ajv_formats_registered": True,
                    "resource_uri": "https://api.merchant.example/v1/search",
                    "updated_at": "2026-10-20T12:00:00Z",
                },
                "facilitator_url": "https://x402.org/facilitator",
                "network": "eip155:84532",
                "usdc_asset": {
                    "address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                    "decimals": 6,
                    "transfer_method": "EIP-3009",
                },
                "counterparty_attestation": {
                    "issuer_did": "did:web:attestseal.org",
                    "merchant_did": "did:web:merchant.example",
                    "ed25519_signature_verified": True,
                    "contains_subjective_judgment_field": False,
                },
            },
        }
        res = verify_ap2_sdjwt_delegation_chain_pef_attestation_and_x402_bazaar_facilitator_guard(
            payload
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["decoded_hops_count"], 2)

    def test_ap2_sdjwt_chain_pef_and_x402_bazaar_facilitator_violations(self) -> None:
        payload = {
            "sd_jwt_chain": "eyJ_hop0~disc0~~eyJ_hop1~disc1~eyJ_kb",
            "decoder_split_single_tilde_first": True,
            "session_state_entries": [{"stored_as_raw_pydantic_instance": True}],
            "payment_evidence_frame": {
                "claim_type": "unknown_event",
                "receipt": {
                    "compliance_verdict": "MAYBE",
                    "settlement_result": "FAILED",
                    "composite_trust_verdict": "UNKNOWN",
                },
                "receipt_hash": "sha256:bad",
                "frame_id": "sha256:bad",
            },
            "session_spend_cap_minor": 50000,
            "session_cumulative_spend_minor": 40000,
            "requested_payment_minor": 20000,
            "x402": {
                "bazaar_discovery": {
                    "ajv_formats_registered": False,
                    "resource_uri": "not-a-uri",
                    "updated_at": "not-a-date",
                },
                "facilitator_url": "https://x402.org/facilitator",
                "network": "eip155:8453",
                "usdc_asset": {
                    "address": "0xdeadbeef",
                    "decimals": 18,
                    "transfer_method": "Permit2",
                },
                "counterparty_attestation": {
                    "issuer_did": "did:web:merchant.example",
                    "merchant_did": "did:web:merchant.example",
                    "ed25519_signature_verified": False,
                    "contains_subjective_judgment_field": True,
                },
            },
        }
        res = verify_ap2_sdjwt_delegation_chain_pef_attestation_and_x402_bazaar_facilitator_guard(
            payload
        )
        self.assertFalse(res["allowed"])
        for expected in (
            "AP2_SDJWT_CHAIN_SINGLE_TILDE_SPLIT_CORRUPTION",
            "AP2_SESSION_STATE_UNSERIALIZED_PYDANTIC_MODEL:0",
            "AP2_PEF_CLAIM_TYPE_INVALID:unknown_event",
            "AP2_PEF_RECEIPT_HASH_MISMATCH",
            "AP2_PEF_FRAME_ID_MISMATCH",
            "AP2_AGENT_SPEND_CAP_EXCEEDED_402",
            "X402_BAZAAR_AJV_FORMATS_UNREGISTERED",
            "X402_PUBLIC_FACILITATOR_MAINNET_MISMATCH:eip155:8453",
            "X402_REGISTERED_STABLECOIN_CONFIG_MISMATCH:eip155:8453",
            "X402_SELF_ASSERTED_COUNTERPARTY_ATTESTATION_FORBIDDEN",
            "X402_FACT_ATTESTATION_SUBJECTIVE_JUDGMENT_FORBIDDEN",
        ):
            self.assertIn(expected, res["violations"])

    def test_tau2_voice_role_flip_qwen_tools_usage_and_parallel_lease_valid(self) -> None:
        payload = {
            "flipped_role_turns": [
                {"role": "user", "content": "   ", "tool_calls": [], "retained_after_flip": False},
                {"role": "assistant", "content": "Checking your order.", "tool_calls": []},
                {"role": "assistant", "content": "", "tool_calls": [{"name": "get_order"}]},
            ],
            "audio_native_provider": "qwen",
            "cli_realtime_generation_override": None,
            "effective_realtime_generation": False,
            "qwen_session_config": {
                "model": "qwen3.5-omni-plus-realtime",
                "voice": "Tina",
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "lookup_order", "parameters": {"type": "object"}},
                    }
                ],
                "turn_detection": {"type": "server_vad"},
            },
            "usage_records": [
                {"accounting_mode": "delta", "scope": "turn_1", "tokens": 120, "pricing_status": "verified", "cost_usd": 0.012},
                {"accounting_mode": "cumulative", "scope": "nova_session", "tokens": 300, "pricing_status": "unverified", "cost_usd": None},
                {"accounting_mode": "cumulative", "scope": "nova_session", "tokens": 450, "pricing_status": "unverified", "cost_usd": None},
            ],
            "requested_concurrency": 5,
            "parallel_work_queue": {
                "worker_writes_checkpoint_directly": False,
                "expired_lease_requeued_above_max_retries": False,
            },
            "voice_submission": {
                "track": "standard",
                "modified_benchmark_prompts_or_tools": False,
                "trained_on_taubench_eval_data": False,
                "contains_unsanitized_reviewer_notes": False,
            },
        }
        res = verify_tau2_voice_role_flip_qwen_nested_tools_usage_cost_and_parallel_lease_guard(
            payload
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["retained_turns_count"], 2)
        self.assertEqual(res["normalized_total_tokens"], 570)

    def test_tau2_voice_role_flip_qwen_tools_usage_and_parallel_lease_violations(self) -> None:
        payload = {
            "flipped_role_turns": [
                {"role": "user", "content": " \n ", "tool_calls": [], "retained_after_flip": True}
            ],
            "audio_native_provider": "qwen",
            "cli_realtime_generation_override": None,
            "effective_realtime_generation": True,
            "qwen_session_config": {
                "model": "qwen3-omni-flash-realtime",
                "voice": "Cherry",
                "tool_choice": "auto",
                "tools": [{"type": "function", "name": "flattened_tool"}],
                "turn_detection": {"type": "server_vad", "prefix_padding_ms": 300},
            },
            "usage_records": [
                {
                    "accounting_mode": "cumulative",
                    "scope": "nova_session",
                    "tokens": 300,
                    "aggregated_by_summing_running_totals": True,
                    "pricing_status": "unknown_model",
                    "cost_usd": 0.0,
                }
            ],
            "requested_concurrency": 20,
            "explicit_provider_limit_override": False,
            "parallel_work_queue": {
                "worker_writes_checkpoint_directly": True,
                "expired_lease_requeued_above_max_retries": True,
            },
            "voice_submission": {
                "track": "standard",
                "modified_benchmark_prompts_or_tools": True,
                "contains_unsanitized_reviewer_notes": True,
            },
        }
        res = verify_tau2_voice_role_flip_qwen_nested_tools_usage_cost_and_parallel_lease_guard(
            payload
        )
        self.assertFalse(res["allowed"])
        for expected in (
            "TAU2_VOICE_ROLE_FLIP_WHITESPACE_TURN_LEAKED:0",
            "TAU2_REALTIME_USER_GENERATION_RESOLUTION_MISMATCH",
            "TAU2_QWEN_FLASH_MODEL_TOOL_CALLING_UNSUPPORTED",
            "TAU2_QWEN_FLATTENED_TOOL_SCHEMA_FORBIDDEN:0",
            "TAU2_QWEN_UNSUPPORTED_TOOL_CHOICE_PARAM_FORBIDDEN",
            "TAU2_QWEN_VAD_PREFIX_PADDING_MS_FORBIDDEN",
            "TAU2_CUMULATIVE_USAGE_DOUBLE_COUNTED:0",
            "TAU2_UNKNOWN_MODEL_SILENT_ZERO_COST_FORBIDDEN:0",
            "TAU2_VOICE_PROVIDER_CONCURRENCY_CAP_EXCEEDED:qwen:20>5",
            "TAU2_PARALLEL_WORKER_DIRECT_CHECKPOINT_WRITE_FORBIDDEN",
            "TAU2_PARALLEL_LEASE_RETRY_CAP_EXCEEDED",
            "TAU2_VOICE_STANDARD_TRACK_BOUNDARY_VIOLATION",
            "TAU2_ELICITATION_RAW_REVIEWER_EXPORT_LEAK",
        ):
            self.assertIn(expected, res["violations"])


if __name__ == "__main__":
    unittest.main()
