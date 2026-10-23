"""Unit tests for Stage 190 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.x402_eoa_high_s_upto_sim_tron_exact_svm_seal_callback_mcp_requirements_meta_guard import (
    PINNED_TRON_PERMIT2_PROXY_COMMIT,
    PINNED_TRON_PERMIT2_PROXY_MAINNET_SHA256,
    PINNED_TRON_PERMIT2_PROXY_RUNTIME_BYTES,
    SECP256K1_HALF_N,
    validate_evm_signature_upto_and_hook_guard,
    validate_mcp_requirements_and_meta_forwarding_guard,
    validate_svm_seal_callback_recovery_guard,
    validate_tron_exact_binding_guard,
)


class TestStage190Guardrails(unittest.TestCase):
    def test_evm_high_s_eoa_vs_smart_wallet_and_yparity_and_upto_sim_and_hook(self) -> None:
        # Plain EOA with high-s is rejected (PR #3912)
        eoa_high_s = validate_evm_signature_upto_and_hook_guard(
            signature_len=65,
            s_value=SECP256K1_HALF_N + 1,
            payer_code_len=0,
            raw_recovery_byte=27,
            permitted_amount=1000,
            settlement_amount=300,
            payer_balance=500,
        )
        self.assertFalse(eoa_high_s.allowed)
        self.assertEqual(eoa_high_s.reason, "invalid_exact_evm_non_canonical_signature")

        # Deployed ERC-1271 smart wallet (payer_code_len > 0) with 65-byte high-s is allowed (PR #3912)
        smart_wallet_high_s = validate_evm_signature_upto_and_hook_guard(
            signature_len=65,
            s_value=SECP256K1_HALF_N + 1,
            payer_code_len=128,
            raw_recovery_byte=27,
            permitted_amount=1000,
            settlement_amount=300,
            payer_balance=500,
        )
        self.assertTrue(smart_wallet_high_s.allowed)

        # KMS raw yParity 0 -> normalized to 27, and upto settles 300 when balance=500 < permitted=1000 (PRs #3583, #3769)
        kms_upto = validate_evm_signature_upto_and_hook_guard(
            signature_len=65,
            s_value=SECP256K1_HALF_N,
            payer_code_len=0,
            raw_recovery_byte=0,
            permitted_amount=1000,
            settlement_amount=300,
            payer_balance=500,
        )
        self.assertTrue(kms_upto.allowed)
        self.assertEqual(kms_upto.normalized_v, 27)
        self.assertEqual(kms_upto.simulated_amount, 300)

        # Zero settlement amount skips simulation even if balance is 0 (PR #3769)
        zero_settle = validate_evm_signature_upto_and_hook_guard(
            signature_len=65,
            s_value=SECP256K1_HALF_N,
            payer_code_len=0,
            raw_recovery_byte=1,
            permitted_amount=1000,
            settlement_amount=0,
            payer_balance=0,
        )
        self.assertTrue(zero_settle.allowed)
        self.assertEqual(zero_settle.normalized_v, 28)
        self.assertEqual(zero_settle.simulated_amount, 0)

        # Gate hook exception fails closed with fixed client error and no internal leak (PR #3702)
        hook_fail = validate_evm_signature_upto_and_hook_guard(
            signature_len=65,
            s_value=100,
            payer_code_len=0,
            raw_recovery_byte=27,
            permitted_amount=1000,
            settlement_amount=300,
            payer_balance=1000,
            gate_hook_threw=True,
            gate_hook_exception_detail="postgres://internal-db:5432 timeout",
            exposed_client_error_message="extension hook failed",
        )
        self.assertFalse(hook_fail.allowed)
        self.assertEqual(hook_fail.reason, "extension_hook_error")
        self.assertEqual(hook_fail.client_error_message, "extension hook failed")

    def test_tron_exact_binding_guard(self) -> None:
        # Valid TRON Nile Permit2 binding at verify stage (includes B) and settle stage (B=0)
        verify_ok = validate_tron_exact_binding_guard(
            network="tron:3448148188",
            provided_tip712_chain_id=3448148188 & 0xFFFFFFFF,
            tron_payload_hex="41a614f803b6fd780986a42c78ec9c7f77e6ded13c",
            provided_tip712_address="0xa614f803b6fd780986a42c78ec9c7f77e6ded13c",
            transfer_method="permit2",
            proxy_commit=PINNED_TRON_PERMIT2_PROXY_COMMIT,
            proxy_runtime_bytes=PINNED_TRON_PERMIT2_PROXY_RUNTIME_BYTES,
            proxy_runtime_sha256=PINNED_TRON_PERMIT2_PROXY_MAINNET_SHA256,
            stage="verify",
            now_seconds=1000,
            expiry_seconds=1040,
            settlement_S=12,
            business_B=20,
            safety_M=6,
        )
        self.assertTrue(verify_ok.allowed)
        self.assertEqual(verify_ok.required_min_expiry, 1038)

        # Hex CAIP-2 network ID rejected
        hex_net = validate_tron_exact_binding_guard(
            network="tron:0xcd8690dc",
            provided_tip712_chain_id=3448148188,
            tron_payload_hex="41a614f803b6fd780986a42c78ec9c7f77e6ded13c",
            provided_tip712_address="0xa614f803b6fd780986a42c78ec9c7f77e6ded13c",
            transfer_method="tip3009",
        )
        self.assertFalse(hex_net.allowed)
        self.assertEqual(hex_net.reason, "invalid_tron_caip2_network")

    def test_svm_seal_and_refund_callback_recovery_guard(self) -> None:
        # First attempt fails callback -> returns settlement_pending after durable save
        pending = validate_svm_seal_callback_recovery_guard(
            intent="refund",
            deposit_amount=10_000,
            already_claimed_amount=500,
            cumulative_amount=3_000,
            durable_result_present=False,
            durable_paid_to_receiver_present=True,
            already_recorded=False,
            in_flight_pass_active=False,
            callback_fails_first_attempt=True,
            retry_after_failure=False,
        )
        self.assertFalse(pending.allowed)
        self.assertEqual(pending.reason, "settlement_pending")
        self.assertEqual(pending.response_amount, "7000")
        self.assertEqual(pending.callback_amount, "2500")

        # Retry recovers from durable result without rebroadcasting and passes paidToReceiver=2500
        recovered = validate_svm_seal_callback_recovery_guard(
            intent="refund",
            deposit_amount=10_000,
            already_claimed_amount=500,
            cumulative_amount=3_000,
            durable_result_present=True,
            durable_paid_to_receiver_present=True,
            already_recorded=False,
            in_flight_pass_active=False,
            callback_fails_first_attempt=True,
            retry_after_failure=True,
        )
        self.assertTrue(recovered.allowed)
        self.assertEqual(recovered.broadcast_count, 1)
        self.assertEqual(recovered.callback_invocations, 2)
        self.assertEqual(recovered.response_amount, "7000")
        self.assertEqual(recovered.callback_amount, "2500")
        self.assertTrue(recovered.recorded_marker_set)

    def test_mcp_sep2487_requirements_and_sep2028_meta_forwarding_guard(self) -> None:
        # Valid traceparent in _meta -> clear-and-use-meta clears stale existing tracestate
        # Unknown requirement while known requirements are satisfied -> client_may_filter_tool is False
        ok = validate_mcp_requirements_and_meta_forwarding_guard(
            declared_requirements=["auth:oauth2", "custom:unknown_cap"],
            server_satisfied_requirements=["auth:oauth2", "custom:unknown_cap"],
            client_known_requirements={"auth:oauth2": True},
            meta_fields={
                "traceparent": "00-e796ccb939d95b7c54d523095a9bd3b4-e515588135c1c901-01",
                "tenant_id": "secret-tenant-99",
            },
            existing_outbound_headers={
                "traceparent": "00-11111111111111111111111111111111-2222222222222222-01",
                "tracestate": "vendor=old",
                "baggage": "env=prod",
            },
        )
        self.assertTrue(ok.allowed)
        self.assertFalse(ok.client_may_filter_tool)
        self.assertEqual(
            ok.forwarded_headers["traceparent"],
            "00-e796ccb939d95b7c54d523095a9bd3b4-e515588135c1c901-01",
        )
        self.assertNotIn("tracestate", ok.forwarded_headers)
        self.assertEqual(ok.forwarded_headers["baggage"], "env=prod")
        self.assertNotIn("tenant_id", ok.forwarded_headers)

        # Malformed traceparent in _meta -> dropped at step 2 -> required traceparent missing at step 3
        # -> group skipped, preserving existing traceparent + tracestate!
        malformed_tp = validate_mcp_requirements_and_meta_forwarding_guard(
            declared_requirements=["auth:oauth2"],
            server_satisfied_requirements=["auth:oauth2"],
            client_known_requirements={"auth:oauth2": True},
            meta_fields={
                "traceparent": "malformed-traceparent",
                "tracestate": "vendor=attacker",
            },
            existing_outbound_headers={
                "traceparent": "00-11111111111111111111111111111111-2222222222222222-01",
                "tracestate": "vendor=existing",
            },
        )
        self.assertTrue(malformed_tp.allowed)
        self.assertTrue(malformed_tp.client_may_filter_tool)
        self.assertEqual(
            malformed_tp.forwarded_headers["traceparent"],
            "00-11111111111111111111111111111111-2222222222222222-01",
        )
        self.assertEqual(malformed_tp.forwarded_headers["tracestate"], "vendor=existing")


if __name__ == "__main__":
    unittest.main()
