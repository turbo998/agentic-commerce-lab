"""Unit tests for Stage 196 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.x402_upto_erc3009_stellar_casper_body_limit_ucp_idp_mcp_atsa_signing_guard import (
    REQUIRED_EIP712_DOMAIN_FIELDS,
    REQUIRED_OPERATOR_TYPE_MAPS,
    SEP2752_REQUIRED_COMPONENTS,
    STELLAR_TESTNET_UPTO_PROXY,
    UPTO_ERC3009_PROXY_ADDRESS,
    compute_upto_erc3009_nonce,
    validate_mcp_ai_invocation_atsa_risk_and_http_signing_guard,
    validate_ucp_identity_linking_accelerated_idp_guard,
    validate_x402_sdk_regression_and_upto_erc3009_guard,
    validate_x402_stellar_upto_casper_exact_and_limits_guard,
)


class Stage196GuardTest(unittest.TestCase):
    def _valid_operator_maps(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return {
            name: {"EIP712Domain": REQUIRED_EIP712_DOMAIN_FIELDS}
            for name in REQUIRED_OPERATOR_TYPE_MAPS
        }

    def test_x402_sdk_regression_and_upto_erc3009_guard(self) -> None:
        pay_to = "0x1111111111111111111111111111111111111111"
        settler = "0x2222222222222222222222222222222222222222"
        salt = "0xabcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        nonce = compute_upto_erc3009_nonce(pay_to, settler, salt)

        ok = validate_x402_sdk_regression_and_upto_erc3009_guard(
            operator_type_maps=self._valid_operator_maps(),
            v2_network="algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
            refund_amount_atomic=250_000,
            has_refunded_event=True,
            proxy_address=UPTO_ERC3009_PROXY_ADDRESS,
            signed_max_amount=1_000_000,
            actual_settle_amount=650_000,
            pay_to=pay_to,
            bound_settler=settler,
            caller_settler=settler,
            salt_hex=salt,
            signed_nonce=nonce,
            nonce_already_used=False,
            is_fee_on_transfer_or_rebasing=False,
            proxy_pre_existing_donated_balance=500,
            proxy_post_settle_balance=500,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.metadata["refunded_to_payer"], 350_000)

        bad_nonce = validate_x402_sdk_regression_and_upto_erc3009_guard(
            operator_type_maps=self._valid_operator_maps(),
            v2_network="eip155:8453",
            refund_amount_atomic=250_000,
            has_refunded_event=True,
            proxy_address=UPTO_ERC3009_PROXY_ADDRESS,
            signed_max_amount=1_000_000,
            actual_settle_amount=650_000,
            pay_to="0x9999999999999999999999999999999999999999",
            bound_settler=settler,
            caller_settler=settler,
            salt_hex=salt,
            signed_nonce=nonce,
            nonce_already_used=False,
            is_fee_on_transfer_or_rebasing=False,
            proxy_pre_existing_donated_balance=0,
            proxy_post_settle_balance=0,
        )
        self.assertFalse(bad_nonce.allowed)
        self.assertEqual(bad_nonce.decision_code, "X402_UPTO_ERC3009_NONCE_COMMITMENT_MISMATCH")

    def test_x402_stellar_upto_casper_exact_and_limits_guard(self) -> None:
        ok = validate_x402_stellar_upto_casper_exact_and_limits_guard(
            stellar_network="stellar:testnet",
            stellar_proxy_contract=STELLAR_TESTNET_UPTO_PROXY,
            are_fees_sponsored=True,
            max_timeout_seconds=300,
            ledger_close_seconds=5,
            current_ledger=100_000,
            allowance_expiration_ledger=100_060,
            signature_expiration_ledger=100_060,
            simulated_root_function="settle_upto",
            simulated_source_account="GBM7Q4MDPBB4QOYUKRZIOO2PZDIZIO4YX44AKFJNZPR3SDP6EKC7BNLM",
            facilitator_address="GBM7Q4MDPBB4QOYUKRZIOO2PZDIZIO4YX44AKFJNZPR3SDP6EKC7BNLM",
            casper_network="casper:casper",
            casper_scheme="exact",
            casper_key_algorithm="secp256k1",
            casper_secp256k1_low_s=True,
            casper_valid_after=1_700_000_000,
            casper_valid_before=1_700_000_300,
            casper_now=1_700_000_120,
            facilitator_endpoint_kind="control_plane",
            facilitator_response_bytes=512 * 1024,
            mcp_phase="recovery_retry",
            mcp_configured_max_timeout_seconds=600,
            caller_deadline_seconds=120,
            derived_attempt_timeout_seconds=90,
        )
        self.assertTrue(ok.allowed)

        bad_body = validate_x402_stellar_upto_casper_exact_and_limits_guard(
            stellar_network="stellar:testnet",
            stellar_proxy_contract=STELLAR_TESTNET_UPTO_PROXY,
            are_fees_sponsored=True,
            max_timeout_seconds=300,
            ledger_close_seconds=5,
            current_ledger=100_000,
            allowance_expiration_ledger=100_060,
            signature_expiration_ledger=100_060,
            simulated_root_function="settle_upto",
            simulated_source_account="GBM7Q4MDPBB4QOYUKRZIOO2PZDIZIO4YX44AKFJNZPR3SDP6EKC7BNLM",
            facilitator_address="GBM7Q4MDPBB4QOYUKRZIOO2PZDIZIO4YX44AKFJNZPR3SDP6EKC7BNLM",
            casper_network="casper:casper",
            casper_scheme="exact",
            casper_key_algorithm="ed25519",
            casper_secp256k1_low_s=True,
            casper_valid_after=1_700_000_000,
            casper_valid_before=1_700_000_300,
            casper_now=1_700_000_120,
            facilitator_endpoint_kind="control_plane",
            facilitator_response_bytes=2 * 1024 * 1024,
            mcp_phase="recovery_retry",
            mcp_configured_max_timeout_seconds=600,
            caller_deadline_seconds=120,
            derived_attempt_timeout_seconds=90,
        )
        self.assertFalse(bad_body.allowed)
        self.assertEqual(bad_body.decision_code, "X402_FACILITATOR_RESPONSE_BODY_TOO_LARGE")

    def test_ucp_identity_linking_accelerated_idp_guard(self) -> None:
        ok = validate_ucp_identity_linking_accelerated_idp_guard(
            has_initial_idp_pkce_connection=True,
            requested_flow="accelerated_idp",
            authenticated_platform_user_id="usr_alice_01",
            subject_token_user_id="usr_alice_01",
            subject_token_scopes=("openid", "email", "profile"),
            business_required_claims=("email", "email_verified"),
            claim_to_required_scope_map={"email": "email", "email_verified": "email"},
            consent_model="platform_level",
            platform_consent_covers_business=True,
            per_business_interactive_consent_granted=False,
            issued_token_type="urn:ietf:params:oauth:token-type:jwt",
            jwt_grant_aud="https://merchant.example/oauth/token",
            jwt_grant_jti="jti_99887766",
        )
        self.assertTrue(ok.allowed)

        cross_user = validate_ucp_identity_linking_accelerated_idp_guard(
            has_initial_idp_pkce_connection=True,
            requested_flow="accelerated_idp",
            authenticated_platform_user_id="usr_alice_01",
            subject_token_user_id="usr_bob_02",
            subject_token_scopes=("openid", "email"),
            business_required_claims=("email",),
            claim_to_required_scope_map={"email": "email"},
            consent_model="platform_level",
            platform_consent_covers_business=True,
            per_business_interactive_consent_granted=False,
            issued_token_type="urn:ietf:params:oauth:token-type:jwt",
            jwt_grant_aud="https://merchant.example/oauth/token",
            jwt_grant_jti="jti_99887766",
        )
        self.assertFalse(cross_user.allowed)
        self.assertEqual(cross_user.decision_code, "UCP_IDP_SUBJECT_TOKEN_CROSS_USER_MISMATCH")

    def test_mcp_ai_invocation_atsa_risk_and_http_signing_guard(self) -> None:
        ok = validate_mcp_ai_invocation_atsa_risk_and_http_signing_guard(
            request_ai_invocation_meta={
                "invocationReason": "User requested portfolio rebalance check",
                "model": "gemini-4-argon",
                "userIntent": "Check USDC balance",
                "turnId": "turn_20261023_01",
            },
            response_ai_invocation_meta={"turnId": "turn_20261023_01"},
            used_ai_invocation_for_authz=False,
            sad_document={
                "v": 1,
                "id": "mcp.treasury.example",
                "publisher": "Contoso Treasury",
                "version": "1.2.0",
                "clearance": "confidential",
                "capabilities": ["mcp-server"],
                "signerKeyId": "root-key-2026-q4",
                "signature": "MEUCIQDa9f...",
                "netAllowedHosts": ["mcp.treasury.example"],
            },
            pinned_trust_root_keys=("root-key-2026-q4",),
            mcp_endpoint_host="mcp.treasury.example",
            tool_allowlist_scope="check_balance list_accounts",
            requested_tool="check_balance",
            co_loaded_server_tools=("send_wire",),
            schema_changed_since_list=False,
            admission_record={"clearance_decision": "admitted", "outcome": "allowed"},
            tool_annotations={
                "readOnlyHint": True,
                "riskLevel": "low",
                "category": "read",
                "blastRadius": "item",
                "reversibility": "auto",
                "approvalRecommendation": "none",
                "minTrustLevel": 1,
            },
            signed_components=SEP2752_REQUIRED_COMPONENTS,
            signature_params={
                "keyid": "thumbprint_ed25519_01",
                "tag": "client-instance-01",
                "nonce": "nonce_unique_01",
                "created": 1_700_000_000,
            },
            jwk_thumbprint="thumbprint_ed25519_01",
            seen_tag_nonces=(),
            now_epoch=1_700_000_050,
        )
        self.assertTrue(ok.allowed)

        bad_alg = validate_mcp_ai_invocation_atsa_risk_and_http_signing_guard(
            request_ai_invocation_meta={"turnId": "turn_20261023_01"},
            response_ai_invocation_meta={"turnId": "turn_20261023_01"},
            used_ai_invocation_for_authz=False,
            sad_document={
                "v": 1,
                "id": "mcp.treasury.example",
                "publisher": "Contoso Treasury",
                "version": "1.2.0",
                "clearance": "confidential",
                "capabilities": ["mcp-server"],
                "signerKeyId": "root-key-2026-q4",
                "signature": "MEUCIQDa9f...",
            },
            pinned_trust_root_keys=("root-key-2026-q4",),
            mcp_endpoint_host="mcp.treasury.example",
            tool_allowlist_scope="check_balance list_accounts",
            requested_tool="check_balance",
            co_loaded_server_tools=(),
            schema_changed_since_list=False,
            admission_record={"clearance_decision": "admitted", "outcome": "allowed"},
            tool_annotations={
                "readOnlyHint": True,
                "riskLevel": "low",
                "category": "read",
                "blastRadius": "item",
                "reversibility": "auto",
                "approvalRecommendation": "none",
                "minTrustLevel": 1,
            },
            signed_components=SEP2752_REQUIRED_COMPONENTS,
            signature_params={
                "alg": "ed25519",
                "keyid": "thumbprint_ed25519_01",
                "tag": "client-instance-01",
                "nonce": "nonce_unique_01",
                "created": 1_700_000_000,
            },
            jwk_thumbprint="thumbprint_ed25519_01",
            seen_tag_nonces=(),
            now_epoch=1_700_000_050,
        )
        self.assertFalse(bad_alg.allowed)
        self.assertEqual(bad_alg.decision_code, "MCP_SEP2752_ALG_PARAMETER_PROHIBITED")


if __name__ == "__main__":
    unittest.main()
