"""Unit tests for Stage 194 protocol security guards."""

from __future__ import annotations

import unittest

from lab.ucp_ap2_merchant_auth_declared_fields_x402_caip2_bazaar_bond_mcp_lang_guard import (
    validate_mcp_language_negotiation_type_constraints_and_client_config,
    validate_ucp_ap2_merchant_auth_and_declared_fields,
    validate_x402_caip2_bazaar_opaque_origin_and_namespace_patterns,
    validate_x402_correctness_dispute_bonded_verdict,
)


class Stage194GuardTests(unittest.TestCase):
    def test_ucp_ap2_merchant_auth_and_declared_fields(self) -> None:
        config = {
            "com.example.gift_message": {
                "type": "object",
                "required": ["text"],
                "properties": {"text": {"type": "string", "maxLength": 80}},
                "additionalProperties": False,
            },
            "com.example.engraving": {
                "type": "object",
                "required": ["monogram"],
                "properties": {"monogram": {"type": "string", "maxLength": 8}},
                "additionalProperties": False,
            },
        }
        ok = validate_ucp_ap2_merchant_auth_and_declared_fields(
            operation="update",
            direction="response",
            ap2_active=True,
            ap2_payload={"merchant_authorization": "eyJhbGciOiJFZERTQSJ9..c2lnbmF0dXJl"},
            checkout_status="ready_for_complete",
            config=config,
            checkout_required_declared_fields=["com.example.gift_message"],
            checkout_declared_fields={"com.example.gift_message": {"text": "Happy Birthday!"}},
            line_items=[
                {
                    "id": "li_1",
                    "required_declared_fields": ["com.example.engraving"],
                    "declared_fields": {"com.example.engraving": {"monogram": "QC"}},
                }
            ],
        )
        self.assertTrue(ok.allowed)

        missing_ap2 = validate_ucp_ap2_merchant_auth_and_declared_fields(
            operation="update",
            direction="response",
            ap2_active=True,
            ap2_payload={},
        )
        self.assertFalse(missing_ap2.allowed)
        self.assertEqual(missing_ap2.reason, "missing_ap2_merchant_authorization_in_response")

        complete_with_declared = validate_ucp_ap2_merchant_auth_and_declared_fields(
            operation="complete",
            direction="request",
            ap2_active=False,
            checkout_declared_fields={"com.example.gift_message": {"text": "No"}},
        )
        self.assertFalse(complete_with_declared.allowed)
        self.assertEqual(
            complete_with_declared.reason,
            "declared_fields_must_be_omitted_on_complete",
        )

        deferred_bad_payment = validate_ucp_ap2_merchant_auth_and_declared_fields(
            operation="complete",
            direction="request",
            ap2_active=False,
            fully_deferred_payment_term=True,
            payment={"selected_term_id": "net_30"},
        )
        self.assertFalse(deferred_bad_payment.allowed)
        self.assertEqual(
            deferred_bad_payment.reason,
            "deferred_payment_term_requires_empty_payment_object_on_complete",
        )

    def test_x402_caip2_bazaar_and_namespace_patterns(self) -> None:
        ok = validate_x402_caip2_bazaar_opaque_origin_and_namespace_patterns(
            x402_version=2,
            network="eip155:84532",
            resource_url="mcp://tool/financial_analysis?session=abc#frag",
            reported_canonical_url="mcp://tool/financial_analysis",
            registered_networks=["stellar:testnet", "stellar:futurenet", "eip155:8453"],
            derived_namespace_patterns={"stellar": "stellar:*", "eip155": "eip155:*"},
            accepts_entries=[
                {"x402Version": 2, "network": "invalid", "scheme": "exact"},
                {"x402Version": 2, "network": "eip155:84532", "scheme": "exact"},
            ],
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.details["compatible_accepts_count"], 1)

        bad_net = validate_x402_caip2_bazaar_opaque_origin_and_namespace_patterns(
            x402_version=2,
            network="a:b",
            resource_url="mcp://tool/x",
            reported_canonical_url="mcp://tool/x",
        )
        self.assertFalse(bad_net.allowed)
        self.assertEqual(bad_net.reason, "malformed_v2_caip2_network")

        null_canon = validate_x402_caip2_bazaar_opaque_origin_and_namespace_patterns(
            x402_version=2,
            network="eip155:84532",
            resource_url="mcp://tool/financial_analysis?session=abc",
            reported_canonical_url="null/financial_analysis",
        )
        self.assertFalse(null_canon.allowed)
        self.assertEqual(
            null_canon.reason,
            "bazaar_opaque_origin_null_or_unstripped_canonical_url",
        )

    def test_x402_correctness_dispute_bonded_verdict(self) -> None:
        ok = validate_x402_correctness_dispute_bonded_verdict(
            verdict="CONFIRMED",
            resolver_id="stillos-notary",
            resolver_version="2026.10.1",
            criterion_id="ground-truth-schema-v1",
            evidence_digest="sha256:11223344",
            re_evaluation_procedure="notary verify --criterion ground-truth-schema-v1",
            signature_verified=True,
            independent_criterion_re_evaluated=True,
            claimed_correctness_verified=True,
            slash_requested=False,
            adjudicator_id="adj_notary_1",
            payer_id="buyer_1",
            payee_id="merchant_1",
            operation="POST /mcp/tool/quote",
            receipt_digest="sha256:99887766",
            bound_only_by_payment_identifier=False,
            live_onchain_balance=100.0,
            reserved_against_open_verdicts=20.0,
            per_verdict_max=10.0,
            outstanding_unslashed_obligations=4,
            unpaid_or_overdue_slash_obligations=0.0,
            payout_sla_committed=True,
            presented_as_guaranteed_payout=True,
        )
        self.assertTrue(ok.allowed)

        sig_only = validate_x402_correctness_dispute_bonded_verdict(
            verdict="CONFIRMED",
            resolver_id="stillos-notary",
            resolver_version="2026.10.1",
            criterion_id="ground-truth-schema-v1",
            evidence_digest="sha256:11223344",
            re_evaluation_procedure="notary verify",
            signature_verified=True,
            independent_criterion_re_evaluated=False,
            claimed_correctness_verified=True,
            slash_requested=False,
            adjudicator_id="adj_notary_1",
            payer_id="buyer_1",
            payee_id="merchant_1",
            operation="POST /mcp/tool/quote",
            receipt_digest="sha256:99887766",
            bound_only_by_payment_identifier=False,
            live_onchain_balance=100.0,
            reserved_against_open_verdicts=20.0,
            per_verdict_max=10.0,
            outstanding_unslashed_obligations=4,
            unpaid_or_overdue_slash_obligations=0.0,
            payout_sla_committed=True,
            presented_as_guaranteed_payout=False,
        )
        self.assertFalse(sig_only.allowed)
        self.assertEqual(sig_only.reason, "signature_only_claimed_as_correctness_verification")

    def test_mcp_language_negotiation_type_constraints_and_client_config(self) -> None:
        ok = validate_mcp_language_negotiation_type_constraints_and_client_config(
            request_meta={"io.modelcontextprotocol/acceptLanguage": "fr-CA,fr;q=0.9,en;q=0.5"},
            http_accept_language_headers=["fr-CA,fr;q=0.9,en;q=0.5"],
            response_meta={"io.modelcontextprotocol/contentLanguage": "fr-CA"},
            http_content_language_header="fr-CA",
            schema_check={
                "icon_src": "https://example.com/icon.png",
                "root_uri": "file:///workspace/project",
                "elicit_url": "https://mcp.example.com/ui/set_api_key",
                "elicitation_id": "api-key-elicitation-1",
                "identifier": "checkout_complete",
                "cursor": "eyJwYWdlIjoyfQ==",
                "ttl_ms": 60000,
            },
            mcp_json_config={
                "mcpServers": {
                    "github": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github@0.6.2"],
                        "env": {"GITHUB_PAT": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"},
                    }
                }
            },
        )
        self.assertTrue(ok.allowed)

        mismatch = validate_mcp_language_negotiation_type_constraints_and_client_config(
            request_meta={"io.modelcontextprotocol/acceptLanguage": "en-US,en;q=0.9"},
            http_accept_language_headers=["en-us, en;q=0.900"],
        )
        self.assertFalse(mismatch.allowed)
        self.assertEqual(mismatch.reason, "mcp_accept_language_header_mismatch_minus_32020")


if __name__ == "__main__":
    unittest.main()
