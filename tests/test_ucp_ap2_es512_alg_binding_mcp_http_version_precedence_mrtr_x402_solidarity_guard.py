"""Unit tests for Stage 184 guardrails."""

from __future__ import annotations

import hashlib
import json
import unittest

from lab.ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_guard import (
    RFC6962_EIGHT_LEAF_REFERENCE_ROOT,
    compute_mcp_tool_jcs_digest,
    compute_rfc6962_merkle_root,
    evaluate_mcp_http_precedence_mrtr_tool_pin_guard,
    evaluate_ucp_ap2_es512_signature_scope_guard,
    evaluate_x402_solidarity_extension_guard,
)


class Stage184GuardTests(unittest.TestCase):
    def test_ucp_ap2_es512_signature_scope_guard(self) -> None:
        keys = [
            {"kid": "ap2-es512-2026", "kty": "EC", "crv": "P-521", "alg": "ES512"},
            {"kid": "http-es256-2026", "kty": "EC", "crv": "P-256", "alg": "ES256"},
        ]
        ok = evaluate_ucp_ap2_es512_signature_scope_guard(
            jws_header_alg="ES512",
            jws_header_kid="ap2-es512-2026",
            verifier_allowed_algorithms=("ES256", "ES384", "ES512"),
            published_keys=keys,
            raw_signature_bytes_len=132,
            is_asn1_der_encoded=False,
            http_candidate_kids=("ap2-es512-2026", "http-es256-2026"),
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.bound_alg, "ES512")
        self.assertEqual(ok.http_signature_verified_kid, "http-es256-2026")

        wrong_curve = evaluate_ucp_ap2_es512_signature_scope_guard(
            jws_header_alg="ES512",
            jws_header_kid="http-es256-2026",
            verifier_allowed_algorithms=("ES256", "ES384", "ES512"),
            published_keys=keys,
            raw_signature_bytes_len=132,
            is_asn1_der_encoded=False,
            http_candidate_kids=("http-es256-2026",),
        )
        self.assertFalse(wrong_curve.allowed)
        self.assertEqual(wrong_curve.reason_code, "ucp_ap2_jws_alg_curve_or_jwk_alg_mismatch")

        der_sig = evaluate_ucp_ap2_es512_signature_scope_guard(
            jws_header_alg="ES512",
            jws_header_kid="ap2-es512-2026",
            verifier_allowed_algorithms=("ES256", "ES384", "ES512"),
            published_keys=keys,
            raw_signature_bytes_len=139,
            is_asn1_der_encoded=True,
            http_candidate_kids=("http-es256-2026",),
        )
        self.assertFalse(der_sig.allowed)
        self.assertEqual(der_sig.reason_code, "ucp_ap2_jws_signature_der_or_length_invalid")

    def test_mcp_http_precedence_mrtr_and_tool_pin_guard(self) -> None:
        tool_def = {
            "name": "complete_checkout",
            "description": "Finalize checkout session",
            "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}},
            "_meta": {"transient": True},
        }
        pin = compute_mcp_tool_jcs_digest(tool_def)
        ok = evaluate_mcp_http_precedence_mrtr_tool_pin_guard(
            mcp_protocol_version_header="2026-07-28",
            body_meta_protocol_version="2026-07-28",
            server_supported_versions=("2026-07-28",),
            has_mcp_method_header=True,
            has_mcp_name_header=True,
            mrtr_method="com.example/approval",
            client_advertised_namespaces=("com.example",),
            origin_request_id="req_101",
            resume_request_id="req_101",
            approval_outcome="approved",
            decided_by="approver:alice",
            tool_definition=tool_def,
            pinned_tool_jcs_digest=pin,
        )
        self.assertTrue(ok.allowed)

        # #3449: unsupported version WITHOUT Mcp-Method must return -32022 (version-first), not -32020
        unsupported_ver = evaluate_mcp_http_precedence_mrtr_tool_pin_guard(
            mcp_protocol_version_header="2025-11-25",
            body_meta_protocol_version=None,
            server_supported_versions=("2026-07-28",),
            has_mcp_method_header=False,
            has_mcp_name_header=False,
            mrtr_method="elicitation/create",
            client_advertised_namespaces=(),
            origin_request_id="req_101",
            resume_request_id="req_101",
            approval_outcome="approved",
            decided_by="approver:alice",
            tool_definition=tool_def,
            pinned_tool_jcs_digest=pin,
        )
        self.assertFalse(unsupported_ver.allowed)
        self.assertEqual(unsupported_ver.http_jsonrpc_error_code, -32022)
        self.assertEqual(unsupported_ver.reason_code, "mcp_http_unsupported_version_precedence_32022")

        # #3449 exception: header != _meta returns -32020
        mismatch = evaluate_mcp_http_precedence_mrtr_tool_pin_guard(
            mcp_protocol_version_header="2026-07-28",
            body_meta_protocol_version="v999.0.0",
            server_supported_versions=("2026-07-28",),
            has_mcp_method_header=True,
            has_mcp_name_header=True,
            mrtr_method="elicitation/create",
            client_advertised_namespaces=(),
            origin_request_id="req_101",
            resume_request_id="req_101",
            approval_outcome="approved",
            decided_by="approver:alice",
            tool_definition=tool_def,
            pinned_tool_jcs_digest=pin,
        )
        self.assertFalse(mismatch.allowed)
        self.assertEqual(mismatch.http_jsonrpc_error_code, -32020)

    def test_x402_solidarity_extension_and_rfc6962_merkle(self) -> None:
        # Verify official RFC 6962 8-leaf reference vector from PR #419
        ref_leaves = [
            b"",
            bytes.fromhex("00"),
            bytes.fromhex("10"),
            bytes.fromhex("2021"),
            bytes.fromhex("3031"),
            bytes.fromhex("40414243"),
            bytes.fromhex("5051525354555657"),
            bytes.fromhex("606162636465666768696a6b6c6d6e6f"),
        ]
        self.assertEqual(compute_rfc6962_merkle_root(ref_leaves), RFC6962_EIGHT_LEAF_REFERENCE_ROOT)

        policy_doc = {
            "cap": "5000000",
            "currency": "USDC",
            "fund": "eip155:8453:0x1111111111111111111111111111111111111111",
            "owner": "0xabc",
            "rate": "0.001",
            "receipts": "monthly",
            "since": "2026-10-21T09:12:00Z",
            "version": 1,
        }
        policy_hash = "sha256:" + hashlib.sha256(
            json.dumps(policy_doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        ok = evaluate_x402_solidarity_extension_guard(
            purchase_amount_atomic=48_000_000,
            purchase_valid=True,
            facilitator_supports_solidarity=True,
            rate_str="0.001",
            share_amount_atomic=48_000,
            monthly_accumulated_atomic=100_000,
            monthly_cap_atomic=5_000_000,
            fund_caip10="eip155:8453:0x1111111111111111111111111111111111111111",
            allowlisted_funds=("eip155:8453:0x1111111111111111111111111111111111111111",),
            policy_doc=policy_doc,
            claimed_policy_hash=policy_hash,
            period="2026-10",
            auth_to_fund_valid=True,
            payment_id="pay_01",
            facilitator_id="fac.example",
            merkle_leaves_override=ref_leaves,
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.purchase_settled)
        self.assertEqual(ok.solidarity_status, "recorded")
        self.assertEqual(ok.rfc6962_merkle_root, RFC6962_EIGHT_LEAF_REFERENCE_ROOT)

        # Over-rate share is skipped without blocking the main purchase
        over_rate = evaluate_x402_solidarity_extension_guard(
            purchase_amount_atomic=48_000_000,
            purchase_valid=True,
            facilitator_supports_solidarity=True,
            rate_str="0.025",
            share_amount_atomic=1_200_000,
            monthly_accumulated_atomic=100_000,
            monthly_cap_atomic=5_000_000,
            fund_caip10="eip155:8453:0x1111111111111111111111111111111111111111",
            allowlisted_funds=("eip155:8453:0x1111111111111111111111111111111111111111",),
            policy_doc=policy_doc,
            claimed_policy_hash=policy_hash,
            period="2026-10",
            auth_to_fund_valid=True,
            payment_id="pay_02",
            facilitator_id="fac.example",
        )
        self.assertTrue(over_rate.allowed)
        self.assertTrue(over_rate.purchase_settled)
        self.assertEqual(over_rate.solidarity_status, "skipped")
        self.assertEqual(over_rate.solidarity_skip_reason, "over-rate")


if __name__ == "__main__":
    unittest.main()
