"""Unit tests for Stage 88 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_guard import (
    validate_acp_extensions_jsonpath_and_enhanced_checkout_guard,
    validate_tau2_multilingual_judge_and_submission_metrics_guard,
    validate_ucp_identity_oauth_and_webhook_header_guard,
    validate_x402_eip712_domain_and_base_passthrough_guard,
)


class Stage88GuardTests(unittest.TestCase):
    def test_ucp_identity_oauth_and_webhook_header_valid(self) -> None:
        payload = {
            "identity_linking": {
                "config": {
                    "capabilities": {
                        "dev.ucp.shopping.checkout": {"auth_required": False},
                        "dev.ucp.shopping.order": {"auth_required": True},
                    }
                },
                "negotiation_pruned_by_identity_linking": False,
                "requested_scopes": [
                    "dev.ucp.shopping.checkout",
                    "dev.ucp.shopping.order:read",
                ],
                "discovery": {
                    "rfc8414_status": 404,
                    "fell_back_to_oidc": True,
                    "oidc_status": 200,
                },
                "oauth_security": {
                    "pkce_method": "S256",
                    "expected_issuer": "https://auth.merchant.example",
                    "received_issuer": "https://auth.merchant.example",
                    "registered_redirect_uri": "https://agent.example/cb",
                    "request_redirect_uri": "https://agent.example/cb",
                    "scopes_supported": [
                        "dev.ucp.shopping.checkout",
                        "dev.ucp.shopping.order:read",
                    ],
                },
                "auth_gate_check": {
                    "auth_required": True,
                    "has_buyer_identity_token": False,
                    "error_code": "identity_required",
                },
            },
            "variant": {
                "id": "var_01",
                "options": [{"name": "Color", "value": "Obsidian"}],
            },
            "order_webhook": {
                "headers": {
                    "event_id": "evt_01",
                    "created_time": "2026-10-20T12:00:00Z",
                },
                "body": {"id": "ord_01", "status": "confirmed"},
            },
            "get_order_response_headers": {
                "Signature": "sig1=:abc:",
                "Signature-Input": 'sig1=("@status" "content-digest")',
                "Content-Digest": "sha-256=:xyz:",
            },
        }
        res = validate_ucp_identity_oauth_and_webhook_header_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_identity_oauth_and_webhook_header_blocks_violations(self) -> None:
        payload = {
            "identity_linking": {
                "config": {
                    "capabilities": {
                        "ucp:scopes:checkout_session": {"auth_required": True}
                    }
                },
                "negotiation_pruned_by_identity_linking": True,
                "requested_scopes": ["ucp:scopes:checkout_session"],
                "discovery": {
                    "rfc8414_status": 500,
                    "fell_back_to_oidc": True,
                    "aborted": False,
                },
                "oauth_security": {
                    "pkce_method": "plain",
                    "expected_issuer": "https://auth.merchant.example",
                    "received_issuer": "https://auth.merchant.example/",
                    "registered_redirect_uri": "https://agent.example/cb",
                    "request_redirect_uri": "https://agent.example/cb/extra",
                    "scopes_supported": ["dev.ucp.shopping.checkout"],
                },
            },
            "variant": {
                "id": "var_01",
                "selected_options": [{"name": "Color", "value": "Obsidian"}],
            },
            "order_webhook": {
                "headers": {},
                "body": {
                    "id": "ord_01",
                    "event_id": "evt_inline",
                    "created_time": "2026-10-20T12:00:00Z",
                },
            },
            "get_order_response_headers": {},
        }
        res = validate_ucp_identity_oauth_and_webhook_header_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "UCP_CAPABILITY_NEGOTIATION_PRUNED_BY_IDENTITY_LINKING", res["violations"]
        )
        self.assertIn("UCP_RFC8414_NON_404_ILLEGAL_OIDC_FALLBACK:500", res["violations"])
        self.assertIn("UCP_ISSUER_BYTE_FOR_BYTE_MISMATCH", res["violations"])
        self.assertIn(
            "UCP_VARIANT_LEGACY_SELECTED_OPTIONS_FORBIDDEN", res["violations"]
        )
        self.assertIn("UCP_WEBHOOK_DANGLING_BODY_FIELDS_FORBIDDEN", res["violations"])

    def test_acp_extensions_jsonpath_and_enhanced_checkout_valid(self) -> None:
        payload = {
            "capabilities": {
                "extensions": [
                    {
                        "name": "discount",
                        "extends": [
                            "$.CheckoutSessionCreateRequest.discounts",
                            "$.CheckoutSessionUpdateRequest.discounts",
                            "$.CheckoutSession.discounts",
                        ],
                    }
                ]
            },
            "discounts": {
                "applied": [
                    {
                        "id": "di_1",
                        "amount": 4000,
                        "method": "each",
                        "priority": 1,
                        "allocations": [
                            {"path": "$.line_items[0]", "amount": 3000},
                            {"path": "$.line_items[1]", "amount": 1000},
                        ],
                    },
                    {
                        "id": "di_2",
                        "amount": 500,
                        "method": "across",
                        "priority": 2,
                    },
                ]
            },
            "checkout_timestamp": "2026-10-20T12:00:00Z",
            "shipping_region": "CA",
            "buyer": {
                "tax_exemption": {
                    "certificate_id": "cert_01",
                    "certificate_type": "resale",
                    "exempt_regions": ["CA", "NY"],
                    "expires_at": "2027-12-31T00:00:00Z",
                }
            },
            "line_items": [
                {
                    "id": "li_100",
                    "item": {"id": "item_100"},
                    "quantity": 2,
                    "availability_status": "in_stock",
                    "available_quantity": 10,
                    "max_quantity_per_order": 5,
                    "tax_exempt": True,
                },
                {
                    "id": "li_101",
                    "item": {"id": "item_101"},
                    "quantity": 1,
                    "parent_id": "li_100",
                    "availability_status": "in_stock",
                    "available_quantity": 5,
                },
            ],
        }
        res = validate_acp_extensions_jsonpath_and_enhanced_checkout_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_extensions_jsonpath_and_enhanced_checkout_blocks_violations(
        self,
    ) -> None:
        payload = {
            "capabilities": {
                "extensions": [
                    {
                        "name": "discount",
                        "extends": ["checkout.request"],
                    }
                ]
            },
            "discounts": {
                "applied": [
                    {
                        "id": "di_1",
                        "amount": 4000,
                        "method": "each",
                        "priority": 1,
                        "allocations": [{"path": "$.line_items[0]", "amount": 1000}],
                    },
                    {
                        "id": "di_2",
                        "amount": 500,
                        "method": "across",
                        "priority": 1,
                    },
                ]
            },
            "checkout_timestamp": "2026-10-20T12:00:00Z",
            "shipping_region": "TX",
            "buyer": {
                "tax_exemption": {
                    "certificate_id": "cert_01",
                    "certificate_type": "resale",
                    "exempt_regions": ["CA"],
                    "expires_at": "2025-12-31T00:00:00Z",
                }
            },
            "line_items": [
                {
                    "id": "li_100",
                    "item": {"id": "item_100", "quantity": 2},
                    "quantity": 12,
                    "parent_id": "li_missing",
                    "availability_status": "in_stock",
                    "available_quantity": 5,
                    "max_quantity_per_order": 10,
                    "tax_exempt": True,
                }
            ],
        }
        res = validate_acp_extensions_jsonpath_and_enhanced_checkout_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "ACP_EXTENSION_INVALID_JSONPATH:checkout.request", res["violations"]
        )
        self.assertIn("ACP_DISCOUNT_DUPLICATE_STACKING_PRIORITY", res["violations"])
        self.assertIn("ACP_LINE_ITEM_REF_MUST_ONLY_CONTAIN_ID:0", res["violations"])
        self.assertIn("ACP_TAX_EXEMPTION_CERTIFICATE_EXPIRED", res["violations"])
        self.assertIn("ACP_TAX_EXEMPTION_REGION_NOT_COVERED:TX", res["violations"])

    def test_x402_eip712_domain_and_base_passthrough_valid(self) -> None:
        payload = {
            "accepted": {
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "extra": {"name": "USDC", "version": "2"},
            },
            "eip712_domain": {
                "name": "USDC",
                "version": "2",
                "chainId": 84532,
                "verifyingContract": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            },
            "authorization": {
                "from": "0x857b06519E91e3A54538791bDbb0E22373e36b66",
            },
            "recovered_signer": "0x857b06519E91e3A54538791bDbb0E22373e36b66",
            "base_scheme_invocation": {
                "network": "eip155:8453",
                "scheme": "exact",
                "role": "facilitator",
            },
        }
        res = validate_x402_eip712_domain_and_base_passthrough_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_x402_eip712_domain_and_base_passthrough_blocks_violations(self) -> None:
        payload = {
            "accepted": {
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "extra": {"name": "USDC", "version": "2"},
            },
            "eip712_domain": {
                "name": "USD Coin",
                "version": "1",
                "chainId": 8453,
                "verifyingContract": "0x0000000000000000000000000000000000000001",
            },
            "authorization": {
                "from": "0x857b06519E91e3A54538791bDbb0E22373e36b66",
            },
            "recovered_signer": "0x1111111111111111111111111111111111111111",
            "base_scheme_invocation": {
                "network": "eip155:137",
                "scheme": "auth-capture",
                "role": "facilitator",
            },
        }
        res = validate_x402_eip712_domain_and_base_passthrough_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "X402_EIP712_DOMAIN_NAME_MISMATCH:USD Coin!=USDC", res["violations"]
        )
        self.assertIn(
            "X402_BASE_SCHEME_OFF_BASE_NETWORK_REJECTED:eip155:137", res["violations"]
        )
        self.assertIn(
            "X402_BASE_AUTH_CAPTURE_CLIENT_ONLY:facilitator", res["violations"]
        )

    def test_tau2_multilingual_judge_and_submission_metrics_valid(self) -> None:
        payload = {
            "multilingual_eval": {
                "language": "hi",
                "script": "Deva",
                "llm_communicate_judge_param": None,
                "force_env_var": False,
                "judge_activated": True,
                "justification": "[llm_judge] Agent conveyed flight number in Romanized Hindi.",
                "nl_prompt_has_lang_hint": True,
                "pack_persona_in_regular_sampling_pool": False,
            },
            "submission_validation": {
                "declared_domains": ["airline", "retail", "telecom"],
                "trajectory_domains": ["airline", "retail", "telecom"],
                "declared_pass_k": {"pass^1": 0.75, "pass^4": 0.52},
                "recomputed_pass_k": {"pass^1": 0.75, "pass^4": 0.52},
                "declared_cost": 14.25,
                "recomputed_cost": 14.25,
            },
        }
        res = validate_tau2_multilingual_judge_and_submission_metrics_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_multilingual_judge_and_submission_metrics_blocks_violations(
        self,
    ) -> None:
        payload = {
            "multilingual_eval": {
                "language": "hi",
                "script": "Deva",
                "llm_communicate_judge_param": None,
                "force_env_var": False,
                "judge_activated": False,
                "justification": "Substring not found",
                "nl_prompt_has_lang_hint": False,
                "pack_persona_in_regular_sampling_pool": True,
            },
            "submission_validation": {
                "declared_domains": ["airline", "retail"],
                "trajectory_domains": ["airline"],
                "declared_pass_k": {"pass^1": 0.85},
                "recomputed_pass_k": {"pass^1": 0.70},
                "declared_cost": 10.0,
                "recomputed_cost": 18.5,
            },
        }
        res = validate_tau2_multilingual_judge_and_submission_metrics_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "TAU2_COMMUNICATE_JUDGE_ACTIVATION_MISMATCH:False!=True", res["violations"]
        )
        self.assertIn(
            "TAU2_MULTILINGUAL_PERSONA_LEAKED_TO_REGULAR_POOL", res["violations"]
        )
        self.assertIn("TAU2_SUBMISSION_MISSING_DOMAIN_RESULTS", res["violations"])
        self.assertIn("TAU2_SUBMISSION_PASS_K_METRIC_MISMATCH:pass^1", res["violations"])
        self.assertIn("TAU2_SUBMISSION_COST_METRIC_MISMATCH", res["violations"])


if __name__ == "__main__":
    unittest.main()
