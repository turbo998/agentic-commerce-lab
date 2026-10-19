"""Unit tests for Stage 48 ACP ATDRP-0.1 dispute resolution, delegate signature, deep links, and Visa TAP PQ guards."""

from __future__ import annotations

import unittest

from lab.acp_atdrp_dispute_signature_deep_links_visa_tap_pq_guard import (
    evaluate_acp_atdrp_dispute_resolution_guard,
    evaluate_acp_delegate_signature_mcp_idempotency_and_deep_links_guard,
    evaluate_visa_tap_rfc9421_and_hybrid_pq_did_guard,
)


class Stage48ACPATDRPAndVisaTAPPQGuardTest(unittest.TestCase):
    def test_acp_atdrp_dispute_resolution_guard(self) -> None:
        valid = evaluate_acp_atdrp_dispute_resolution_guard(
            {
                "prohibited_screened": True,
                "drafted_by": "atdrp-rule-engine-v0.1",
                "signer": {
                    "name": "Elena Vance",
                    "natural_person": True,
                },
                "seal": {
                    "verify_url": "https://disputes.example.org/atdrp/seals/seal_901",
                },
                "require_all_evidence_admissible": True,
                "evidence_artifacts": (
                    {
                        "digest_ok": True,
                        "rfc3161_verified": True,
                        "producer_present": True,
                        "producer_trusted": True,
                        "self_asserted_only": False,
                        "key_unresolved": False,
                        "no_record": False,
                    },
                ),
                "require_valid_authorization_chain": True,
                "authorization_chain": {
                    "payment_mandate_transaction_id": "chk_hash_001",
                    "checkout_hash": "chk_hash_001",
                    "checkout_receipt_reference": "chk_hash_001",
                    "payment_receipt_reference": "chk_hash_001",
                    "payment_receipt_transaction_id": "tx_settle_001",
                    "ledger_settlement_tx_id": "tx_settle_001",
                },
                "order_gross_minor": 10000,
                "order_level_adjustments_minor": 1000,
                "disputed_lines": (
                    {
                        "line_id": "line_excess",
                        "gross_settled_minor": 6000,
                        "direct_adjustments_minor": 0,
                        "authorized_max_minor": 4500,
                        "mandate_present": True,
                        "proposed_disposition": "partial_overturn",
                        "proposed_overturn_minor": 1500,
                    },
                    {
                        "line_id": "line_instruction_conflict",
                        "gross_settled_minor": 4000,
                        "direct_adjustments_minor": 0,
                        "authorized_max_minor": 4000,
                        "mandate_present": True,
                        "instruction_conflicts_with_cart": True,
                        "proposed_disposition": "uphold",
                        "proposed_overturn_minor": 0,
                    },
                ),
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(valid.decision_code, "ACP_ATDRP_DISPUTE_RESOLUTION_VERIFIED")
        self.assertEqual(valid.total_overturned_minor, 1500)
        self.assertTrue(valid.agent_platform_finding_recorded)

        # Reject inadmissible evidence (missing RFC 3161 timestamp), role-only signer, and reversing merchant charge on instruction conflict
        invalid = evaluate_acp_atdrp_dispute_resolution_guard(
            {
                "prohibited_screened": False,
                "drafted_by": "atdrp-rule-engine-v0.1",
                "signer": {
                    "name": "Dispute Desk",
                    "natural_person": False,
                },
                "seal": {
                    "verify_url": "https://disputes.example.org/atdrp/seals/seal_902",
                },
                "require_all_evidence_admissible": True,
                "evidence_artifacts": (
                    {
                        "digest_ok": True,
                        "rfc3161_verified": False,
                        "producer_present": True,
                        "producer_trusted": True,
                    },
                ),
                "disputed_lines": (
                    {
                        "line_id": "line_1",
                        "gross_settled_minor": 4000,
                        "direct_adjustments_minor": 0,
                        "authorized_max_minor": 4000,
                        "instruction_conflicts_with_cart": True,
                        "merchant_charge_reversed_on_instruction_conflict": True,
                    },
                ),
            }
        )
        self.assertFalse(invalid.admitted)
        self.assertEqual(invalid.decision_code, "ATDRP_INADMISSIBLE_EVIDENCE_ARTIFACT_BLOCKED")

    def test_acp_delegate_signature_mcp_idempotency_and_deep_links_guard(self) -> None:
        valid = evaluate_acp_delegate_signature_mcp_idempotency_and_deep_links_guard(
            {
                "endpoint": "/agentic_commerce/delegate_payment",
                "headers": {
                    "Signature": "sig1=:MEUCIQD...:",
                    "Timestamp": "2026-10-19T18:00:00Z",
                },
                "signature_verified": True,
                "timestamp_skew_seconds": 12,
                "delegate_authentication_session": {
                    "status": "challenge_required",
                    "authentication_result": None,
                },
                "mcp_tool_call": {
                    "tool_name": "complete_checkout",
                    "meta": {"idempotency_key": "idem_mcp_9001"},
                },
                "session_context": {
                    "ip_address": "203.0.113.10",
                    "device": {"timezone": "America/Los_Angeles"},
                },
                "registered_app_schemes": ("merchantapp",),
                "app_links": {
                    "ios_url": "merchantapp://checkout/cs_123",
                    "universal_url": "https://shop.example.com/app/checkout/cs_123",
                },
                "deep_link_cancelled_or_failed": True,
                "fell_back_to_embedded_web_checkout": True,
                "checkout_session_aborted_on_deep_link_cancel": False,
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(
            valid.decision_code,
            "ACP_DELEGATE_SIGNATURE_MCP_IDEMPOTENCY_AND_DEEP_LINKS_VERIFIED",
        )

        # Reject missing Signature/Timestamp, missing MCP idempotency_key, risk_signals inside session_context, and unregistered app_links scheme
        invalid = evaluate_acp_delegate_signature_mcp_idempotency_and_deep_links_guard(
            {
                "endpoint": "/agentic_commerce/delegate_payment",
                "headers": {"Signature": ""},
                "mcp_tool_call": {
                    "tool_name": "complete_checkout",
                    "meta": {},
                },
                "session_context": {
                    "risk_signals": [{"type": "jarvis", "score": 90}],
                    "device": {"timezone": "UTC+8"},
                },
                "registered_app_schemes": ("merchantapp",),
                "app_links": {
                    "ios_url": "https://shop.example.com/not-custom-scheme",
                },
            }
        )
        self.assertFalse(invalid.admitted)
        self.assertEqual(invalid.decision_code, "ACP_DELEGATE_SIGNATURE_OR_TIMESTAMP_HEADER_BLOCKED")

    def test_visa_tap_rfc9421_and_hybrid_pq_did_guard(self) -> None:
        valid_sig_base = (
            '"@authority": merchant.example.com\n'
            '"@path": /checkout\n'
            '"@signature-params": ("@authority" "@path");created=1760900000;keyid="did:web:registry.example.com#agent-pq-1";alg="ed25519-ml-dsa-65";expires=1760900300;nonce="nonce_pq_01";tag="agent-browser-auth"'
        )
        valid = evaluate_visa_tap_rfc9421_and_hybrid_pq_did_guard(
            {
                "signature_base": valid_sig_base,
                "covered_components": ("@authority", "@path"),
                "created": 1760900000,
                "expires": 1760900300,
                "alg": "ed25519-ml-dsa-65",
                "key_type": "HybridEd25519MLDSA65",
                "nonce": "nonce_pq_01",
                "seen_nonces": ("nonce_old",),
                "recorded_nonce_before_crypto_verify": False,
                "crypto_signature_valid": True,
                "keyid": "did:web:registry.example.com#agent-pq-1",
                "did_registry_configured": True,
                "registered_did_methods": ("did:web", "did:tenzro"),
                "did_verification_method_found": True,
                "oqs_runtime_available": True,
                "signature_byte_length": 3373,
                "mldsa65_public_key_byte_length": 1952,
                "ed25519_leg_valid": True,
                "mldsa65_leg_valid": True,
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(valid.decision_code, "VISA_TAP_RFC9421_AND_HYBRID_PQ_DID_VERIFIED")
        self.assertEqual(valid.http_status, 200)

        # Single-leg forgery or wrong byte length on Hybrid PQ signature must be blocked with 401
        single_leg_forgery = evaluate_visa_tap_rfc9421_and_hybrid_pq_did_guard(
            {
                "signature_base": valid_sig_base,
                "covered_components": ("@authority", "@path"),
                "created": 1760900000,
                "expires": 1760900300,
                "alg": "ed25519-ml-dsa-65",
                "key_type": "HybridEd25519MLDSA65",
                "nonce": "nonce_pq_02",
                "seen_nonces": (),
                "keyid": "did:web:registry.example.com#agent-pq-1",
                "did_registry_configured": True,
                "registered_did_methods": ("did:web",),
                "oqs_runtime_available": True,
                "signature_byte_length": 3373,
                "mldsa65_public_key_byte_length": 1952,
                "ed25519_leg_valid": True,
                "mldsa65_leg_valid": False,
            }
        )
        self.assertFalse(single_leg_forgery.admitted)
        self.assertEqual(
            single_leg_forgery.decision_code,
            "VISA_TAP_HYBRID_PQ_DUAL_LEG_OR_LENGTH_BLOCKED",
        )
        self.assertEqual(single_leg_forgery.http_status, 401)

        # Missing PQ runtime must fail closed with HTTP 503
        no_pq_runtime = evaluate_visa_tap_rfc9421_and_hybrid_pq_did_guard(
            {
                "signature_base": valid_sig_base,
                "covered_components": ("@authority", "@path"),
                "created": 1760900000,
                "expires": 1760900300,
                "alg": "ed25519-ml-dsa-65",
                "key_type": "HybridEd25519MLDSA65",
                "nonce": "nonce_pq_03",
                "seen_nonces": (),
                "keyid": "did:web:registry.example.com#agent-pq-1",
                "did_registry_configured": True,
                "registered_did_methods": ("did:web",),
                "oqs_runtime_available": False,
            }
        )
        self.assertFalse(no_pq_runtime.admitted)
        self.assertEqual(
            no_pq_runtime.decision_code,
            "VISA_TAP_HYBRID_PQ_RUNTIME_UNAVAILABLE_FAIL_CLOSED_503",
        )
        self.assertEqual(no_pq_runtime.http_status, 503)


if __name__ == "__main__":
    unittest.main()
