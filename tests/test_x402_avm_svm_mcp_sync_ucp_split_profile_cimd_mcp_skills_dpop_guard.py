"""Unit tests for Stage 172 deterministic protocol & benchmark guardrails (2026-10-23 part 2)."""

from __future__ import annotations

import unittest

from lab.x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_guard import (
    validate_mcp_skills_primitive_dpop_and_async_approval_guard,
    validate_ucp_split_payment_profile_cimd_and_mcp_binding_guard,
    validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard,
)


class TestStage172Guards(unittest.TestCase):
    def test_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(self) -> None:
        ok = validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(
            {
                "avm_network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
                "evm_verify_lookup": {
                    "rpc_transport_failed": True,
                    "reported_error": "invalid_exact_evm_failed_to_verify_signature",
                },
                "svm_batch_proof": {
                    "proof_format": "readable",
                    "all_peers_support_readable": True,
                    "signed_bytes_match_expected": True,
                },
                "python_mcp_sync_client": {
                    "auto_payment": False,
                    "on_payment_requested_approved": False,
                    "returned_unpaid_402_without_raising": False,
                },
                "bazaar_resource_input": {
                    "method": "POST",
                    "has_body_type": True,
                    "derived_from_probe_method": False,
                },
            }
        )
        self.assertTrue(ok.allowed)

        # Legacy 44-char Algorand genesis hash rejected (PR #3894)
        bad_avm = validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(
            {"avm_network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73kti31q3Hc98="}
        )
        self.assertFalse(bad_avm.allowed)
        self.assertEqual(bad_avm.decision_code, "X402_AVM_LEGACY_GENESIS_HASH_EXCEEDS_CAIP2")

        # EVM lookup failure misreported as bad signature (PR #3886)
        bad_evm = validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(
            {
                "evm_verify_lookup": {
                    "rpc_transport_failed": True,
                    "reported_error": "invalid_permit2_signature",
                }
            }
        )
        self.assertFalse(bad_evm.allowed)
        self.assertEqual(
            bad_evm.decision_code,
            "X402_EVM_LOOKUP_FAILURE_MISREPORTED_AS_BAD_SIGNATURE",
        )

        # Python sync MCP client returning unpaid 402 without raising (PR #3907)
        bad_mcp = validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(
            {
                "python_mcp_sync_client": {
                    "auto_payment": False,
                    "returned_unpaid_402_without_raising": True,
                }
            }
        )
        self.assertFalse(bad_mcp.allowed)
        self.assertEqual(
            bad_mcp.decision_code,
            "X402_MCP_SYNC_UNPAID_402_SILENT_RETURN_FORBIDDEN",
        )

    def test_ucp_split_payment_profile_cimd_and_mcp_binding_guard(self) -> None:
        ok = validate_ucp_split_payment_profile_cimd_and_mcp_binding_guard(
            {
                "split_payment_profile": {
                    "capabilities_is_object_map": True,
                    "schema_url": "https://ucp.dev/schemas/shopping/split_payment.json",
                    "pinned_version": "2026-06-25",
                },
                "identity_linking_client": {
                    "uses_cimd_https_client_id": True,
                    "presumed_static_client_secret": False,
                },
                "mcp_checkout_order_binding": {
                    "aligned_with_cart_mcp_envelope": True,
                },
            }
        )
        self.assertTrue(ok.allowed)

        bad_prof = validate_ucp_split_payment_profile_cimd_and_mcp_binding_guard(
            {"split_payment_profile": {"capabilities_is_object_map": False}}
        )
        self.assertFalse(bad_prof.allowed)
        self.assertEqual(bad_prof.decision_code, "UCP_PROFILE_CAPABILITIES_MUST_BE_OBJECT_MAP")

    def test_mcp_skills_primitive_dpop_and_async_approval_guard(self) -> None:
        ok = validate_mcp_skills_primitive_dpop_and_async_approval_guard(
            {
                "mcp_skill_primitive": {
                    "skill_manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb924",
                    "undeclared_tool_escalation": False,
                },
                "mcp_dpop_proof": {
                    "ath_matches_access_token": True,
                    "htu_matches_mcp_endpoint": True,
                    "jti_replayed": False,
                },
                "mcp_async_approval": {
                    "consequential_tool": True,
                    "approval_status": "approved",
                },
            }
        )
        self.assertTrue(ok.allowed)

        bad_dpop = validate_mcp_skills_primitive_dpop_and_async_approval_guard(
            {"mcp_dpop_proof": {"jti_replayed": True}}
        )
        self.assertFalse(bad_dpop.allowed)
        self.assertEqual(bad_dpop.decision_code, "MCP_DPOP_SENDER_CONSTRAINT_VIOLATION")


if __name__ == "__main__":
    unittest.main()
