"""Unit tests for Stage 186 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_return_policy_purchase_options_ap2_dispute_resolver_revocation_mcp_task_log_guard import (
    evaluate_ap2_post_transaction_dispute_and_open_mandate_revocation,
    evaluate_mcp_task_log_and_oauth_resource_fallback,
    evaluate_ucp_purchase_options_and_subscription_split,
    evaluate_ucp_return_policy,
)


class TestStage186Guardrails(unittest.TestCase):
    def test_ucp_return_policy_pr634_rules(self) -> None:
        # 1. Valid multi-channel return policy (free in_store/kiosk, capped 15% restocking + $5 shipping + $1 eco by_mail)
        policy = {
            "type": "dev.ucp.shopping.policy.return",
            "eligibility": {
                "type": "window",
                "duration": "P30D",
                "anchor": "delivered",
                "expires_at": "2026-04-01T18:00:00Z",
            },
            "supported_resolutions": ["original_payment_method", "store_credit"],
            "methods": ["in_store", "kiosk", "by_mail"],
            "fees": [
                {
                    "type": "dev.ucp.shopping.fee.restocking",
                    "basis_points": 1500,
                    "max_amount": 5000,
                    "display_text": "15% restocking fee on opened items",
                },
                {"methods": ["in_store", "kiosk"], "amount": 0},
                {
                    "type": "dev.ucp.shopping.fee.return_shipping",
                    "methods": ["by_mail"],
                    "amount": 500,
                },
                {
                    "type": "com.example.fee.eco",
                    "methods": ["by_mail"],
                    "amount": 100,
                    "display_text": "Eco packaging fee",
                },
            ],
        }
        in_store = evaluate_ucp_return_policy(policy, query_channel="in_store")
        self.assertTrue(in_store.allowed)
        self.assertTrue(in_store.channel_free)
        self.assertEqual(in_store.estimated_max_fee_minor, 0)

        by_mail = evaluate_ucp_return_policy(
            policy, query_channel="by_mail", returned_units=3, unit_paid_minor=20000
        )
        self.assertTrue(by_mail.allowed)
        self.assertFalse(by_mail.channel_free)
        # 3 * min(3000, 5000) + 500 + 100 = 9600
        self.assertEqual(by_mail.estimated_max_fee_minor, 9600)

        # 2. IKEA field note: documentary "proof_of_purchase" is NOT a valid temporal anchor
        ikea_bad = {
            "type": "dev.ucp.shopping.policy.return",
            "eligibility": {
                "type": "window",
                "duration": "P180D",
                "anchor": "proof_of_purchase",
            },
        }
        res_ikea = evaluate_ucp_return_policy(ikea_bad)
        self.assertFalse(res_ikea.allowed)
        self.assertEqual(
            res_ikea.reason_code, "ucp_return_policy_missing_or_documentary_anchor"
        )

        # 3. Elapsed window != non-returnability (Bombas 30d refund / 60d store credit)
        res_elapsed = evaluate_ucp_return_policy(
            policy, platform_claims_non_returnable=True
        )
        self.assertFalse(res_elapsed.allowed)
        self.assertEqual(
            res_elapsed.reason_code, "ucp_return_policy_false_non_returnable_inference"
        )

        # 4. `not_accepted` carrying `fees` or `methods` is rejected
        bad_final_sale = {
            "type": "dev.ucp.shopping.policy.return",
            "eligibility": {"type": "not_accepted"},
            "methods": ["in_store"],
        }
        res_final = evaluate_ucp_return_policy(bad_final_sale)
        self.assertFalse(res_final.allowed)
        self.assertEqual(
            res_final.reason_code,
            "ucp_return_policy_not_accepted_carries_return_terms",
        )

        # 5. Omitted `fees` claimed as free returns is rejected
        omitted_fees_pol = {
            "type": "dev.ucp.shopping.policy.return",
            "eligibility": {"type": "unlimited"},
        }
        res_omitted_free = evaluate_ucp_return_policy(
            omitted_fees_pol, platform_claims_free_returns=True
        )
        self.assertFalse(res_omitted_free.allowed)
        self.assertEqual(
            res_omitted_free.reason_code,
            "ucp_return_policy_omitted_fees_claimed_as_free",
        )

    def test_ucp_purchase_options_and_subscription_split_pr890(self) -> None:
        options = [
            {"id": "po_once", "title": "One-time purchase", "price": 1000},
            {
                "id": "po_monthly",
                "title": "Subscribe & save 15%",
                "price": 850,
                "list_price": 1000,
                "schedules": [
                    {
                        "description": {"plain": "$8.50 every month starting Nov 23"},
                        "totals": [{"type": "total", "amount": 850}],
                        "starts_at": "2026-11-23T00:00:00Z",
                    }
                ],
            },
        ]
        policies = [
            {
                "type": "dev.ucp.shopping.policy.subscription",
                "applies_to": ["li_1"],
                "description": {"plain": "Renews monthly until cancelled."},
            }
        ]
        messages = [
            {
                "type": "warning",
                "presentation": "disclosure",
                "code": "dev.ucp.shopping.policy.subscription",
                "path": "$.line_items[0].li_1",
                "content": "$8.50 today, then $8.50/month starting Nov 23. Cancel anytime.",
            }
        ]
        # Valid split payment with gift card (`immediate`) + open-ended card (retained even if it contributes 0 today)
        valid = evaluate_ucp_purchase_options_and_subscription_split(
            catalog_purchase_options=options,
            line_id="li_1",
            selected_purchase_option_id="po_monthly",
            policies=policies,
            messages=messages,
            split_payments_active=True,
            submitted_instruments=[
                {
                    "id": "inst_gc",
                    "type": "gift_card",
                    "schedule_type": "immediate",
                    "amount": 850,
                },
                {"id": "inst_card", "type": "card"},
            ],
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.retained_instrument_ids, ("inst_card",))

        # No retained recurring instrument (only immediate gift card submitted) -> payment_failed
        no_retained = evaluate_ucp_purchase_options_and_subscription_split(
            catalog_purchase_options=options,
            line_id="li_1",
            selected_purchase_option_id="po_monthly",
            policies=policies,
            messages=messages,
            split_payments_active=True,
            submitted_instruments=[
                {
                    "id": "inst_gc",
                    "type": "gift_card",
                    "schedule_type": "immediate",
                    "amount": 850,
                }
            ],
        )
        self.assertFalse(no_retained.allowed)
        self.assertEqual(
            no_retained.reason_code,
            "ucp_purchase_options_no_retained_recurring_instrument",
        )

        # Default option cannot carry `schedules` when a one-time option is also listed
        bad_default = evaluate_ucp_purchase_options_and_subscription_split(
            catalog_purchase_options=list(reversed(options)),
            line_id="li_1",
            selected_purchase_option_id="po_once",
        )
        self.assertFalse(bad_default.allowed)
        self.assertEqual(
            bad_default.reason_code,
            "ucp_purchase_options_default_must_be_onetime_when_present",
        )

    def test_ap2_dispute_resolver_pr352_and_revocation_issue386(self) -> None:
        base_record = {
            "dispute_id": "dsp_01J9X0",
            "policy_version": "ATDRP-0.1",
            "claimant": "payer",
            "checkout_hash": "u8Y2_checkout_hash",
            "payment_mandate": {
                "vct": "mandate.payment.1",
                "transaction_id": "u8Y2_checkout_hash",
                "payee": {"id": "merchant_42", "name": "Example Merchant"},
                "payment_amount": {"currency": "USD", "amount": 10000},
                "iat": 1760000000,
                "exp": 1760086400,
            },
            "checkout_receipt": {
                "status": "Success",
                "reference": "u8Y2_checkout_hash",
                "order_id": "ord_001",
            },
            "payment_receipt": {
                "status": "Success",
                "reference": "u8Y2_checkout_hash",
                "payment_id": "pay_001",
                "iat": 1760000020,
            },
            "order": {
                "id": "ord_001",
                "status": "processing",
                "estimated_delivery": {
                    "earliest": "2025-10-14",
                    "latest": "2025-10-16",
                },
                "line_items": [
                    {
                        "id": "line_item_456",
                        "quantity": {"ordered": 4, "current": 4, "fulfilled": 1},
                        "total": 10000,
                    }
                ],
                "adjustments": [],
            },
        }
        # Exact PR #352 reference outcome: 3 of 4 unfulfilled -> overturn 7500 minor units, fee paid by merchant
        res = evaluate_ap2_post_transaction_dispute_and_open_mandate_revocation(
            base_record, now_date_iso="2025-10-24"
        )
        self.assertTrue(res.eligible)
        self.assertEqual(res.outcome, "overturn")
        self.assertEqual(res.overturn_amount_minor, 7500)
        self.assertEqual(res.fee_paid_by, "merchant")

        # Tampered transaction_id -> authorization_chain_broken -> route to network fraud process
        tampered = dict(base_record)
        tampered["payment_mandate"] = dict(
            base_record["payment_mandate"], transaction_id="wrong_hash"
        )
        res_broken = evaluate_ap2_post_transaction_dispute_and_open_mandate_revocation(
            tampered, now_date_iso="2025-10-24"
        )
        self.assertFalse(res_broken.eligible)
        self.assertEqual(
            res_broken.reason_code, "ap2_dispute_authorization_chain_broken"
        )
        self.assertEqual(res_broken.route, "network fraud process")

        # Issue #386: revoked open mandate cnf key -> receipt_status == "revoked"
        res_revoked = evaluate_ap2_post_transaction_dispute_and_open_mandate_revocation(
            base_record,
            open_mandate={
                "iat": 1760000000,
                "exp": 1760086400,
                "status_list_index": 42,
            },
            status_list_revoked_indices=[42],
        )
        self.assertFalse(res_revoked.eligible)
        self.assertEqual(
            res_revoked.reason_code, "ap2_open_mandate_cnf_authority_revoked"
        )
        self.assertEqual(res_revoked.receipt_status, "revoked")

    def test_mcp_task_log_issue3237_and_oauth_issue1614(self) -> None:
        records = [
            {"seq": 1, "kind": "log", "text": "step 1"},
            {"seq": 2, "kind": "artifact", "uri": "screenshot://1"},
            {"seq": 3, "kind": "com.vendor.computer_use/click", "x": 120, "y": 340},
        ]
        ok = evaluate_mcp_task_log_and_oauth_resource_fallback(
            task_id="tsk_01",
            resource_uri="task-log://tsk_01",
            log_records=records,
            last_seen_seq=1,
            as_supports_rfc8707_resource_param=False,
            requested_scope_audiences=["api://mcp.merchant.example"],
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.resumed_sequences, (2, 3))

        # Multi-audience scope fallback when RFC 8707 resource is omitted -> blocked
        multi_aud = evaluate_mcp_task_log_and_oauth_resource_fallback(
            task_id="tsk_01",
            resource_uri="task-log://tsk_01",
            log_records=records,
            as_supports_rfc8707_resource_param=False,
            requested_scope_audiences=[
                "api://mcp.merchant.example",
                "api://other.service.example",
            ],
        )
        self.assertFalse(multi_aud.allowed)
        self.assertEqual(
            multi_aud.reason_code,
            "mcp_oauth_multi_audience_scope_fallback_forbidden",
        )


if __name__ == "__main__":
    unittest.main()
