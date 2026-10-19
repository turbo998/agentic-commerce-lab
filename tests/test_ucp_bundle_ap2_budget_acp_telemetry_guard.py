"""Unit tests for Stage 41 UCP Bundle Line Items (#976), UCP-AP2 Tokenize Mandate (#916),
Google AP2 ISO 4217 Budget & ISO 8601 Execution-Date (#368/#377/#378) + Dispute Resolver (#352),
and UCP Catalog Search Purpose (#902) / ACP Delegate Telemetry & Deep Link Guards (#238/#285/#287/#237).
"""

from __future__ import annotations

import unittest

from lab.ucp_bundle_ap2_budget_acp_telemetry_guard import (
    evaluate_ap2_iso4217_budget_execution_and_dispute_guard,
    evaluate_ucp_ap2_credential_provider_tokenization_guard,
    evaluate_ucp_bundle_cart_and_deferred_terms_guard,
    evaluate_ucp_catalog_purpose_and_acp_delegate_telemetry_guard,
)


class TestUCPBundleAP2BudgetACPTelemetryGuard(unittest.TestCase):
    def test_ucp_bundle_nested_line_items_and_double_count_guard(self) -> None:
        bundle_items = (
            {
                "id": "li_kit",
                "parent_id": None,
                "subtotal_minor": 5300,
                "items_discount_minor": -500,
                "total_minor": 4800,
            },
            {
                "id": "li_mug",
                "parent_id": "li_kit",
                "subtotal_minor": 2000,
                "items_discount_minor": -200,
                "total_minor": 1800,
            },
            {
                "id": "li_beans",
                "parent_id": "li_kit",
                "subtotal_minor": 3500,
                "items_discount_minor": 0,
                "total_minor": 3500,
            },
        )
        ok = evaluate_ucp_bundle_cart_and_deferred_terms_guard(
            line_items=bundle_items,
            reported_checkout_subtotal_minor=5300,
            reported_checkout_items_discount_minor=-500,
            is_update_request=True,
            business_rejected_echoed_components=False,
            is_deferred_payment_complete=True,
            complete_payment_object={},
            complete_includes_selected_term_id=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.decision_code, "UCP_BUNDLE_LINE_ITEMS_AND_CART_CHECKOUT_VERIFIED")
        self.assertEqual(ok.parent_line_ids, ("li_kit",))
        self.assertEqual(ok.ignored_echoed_component_ids, ("li_mug", "li_beans"))

        # Double-counting components in checkout subtotal is blocked
        double_counted = evaluate_ucp_bundle_cart_and_deferred_terms_guard(
            line_items=bundle_items,
            reported_checkout_subtotal_minor=10600,
            reported_checkout_items_discount_minor=-700,
            is_update_request=False,
            business_rejected_echoed_components=False,
        )
        self.assertFalse(double_counted.admitted)
        self.assertEqual(
            double_counted.decision_code,
            "BUNDLE_COMPONENTS_DOUBLE_COUNTED_IN_CHECKOUT_TOTALS_BLOCKED",
        )

    def test_ucp_ap2_credential_provider_tokenization_guard(self) -> None:
        ok = evaluate_ucp_ap2_credential_provider_tokenization_guard(
            ap2_negotiated=True,
            credential_type="ap2_payment_mandate",
            payment_mandate_present=True,
            payment_mandate_signature_valid=True,
            payment_mandate_expired=False,
            payment_mandate_transaction_id="sha256_chk_abc123",
            checkout_jwt_hash="sha256_chk_abc123",
            binding_checkout_id="chk_abc123",
            target_checkout_id="chk_abc123",
            complete_instrument_has_mandate_derived_token=True,
            mandate_embedded_directly_as_reversible_token=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.decision_code, "UCP_AP2_CREDENTIAL_PROVIDER_TOKEN_ISSUED")

        # Mismatched checkout_jwt_hash blocked at issuance
        mismatch = evaluate_ucp_ap2_credential_provider_tokenization_guard(
            ap2_negotiated=True,
            credential_type="ap2_payment_mandate",
            payment_mandate_present=True,
            payment_mandate_signature_valid=True,
            payment_mandate_expired=False,
            payment_mandate_transaction_id="sha256_chk_OTHER",
            checkout_jwt_hash="sha256_chk_abc123",
            binding_checkout_id="chk_abc123",
            target_checkout_id="chk_abc123",
            complete_instrument_has_mandate_derived_token=True,
            mandate_embedded_directly_as_reversible_token=False,
        )
        self.assertFalse(mismatch.admitted)
        self.assertEqual(
            mismatch.decision_code,
            "AP2_MANDATE_CHECKOUT_JWT_CORRELATION_MISMATCH_AT_TOKENIZE",
        )

    def test_ap2_iso4217_budget_iso8601_window_and_dispute_resolver(self) -> None:
        # 0.29 USD exact boundary (where binary float int(0.29 * 100) == 28 failed previously)
        ok_usd = evaluate_ap2_iso4217_budget_execution_and_dispute_guard(
            budget_max_major=0.29,
            currency="USD",
            spend_amount_minor=29,
            execution_date_str="2026-03-31",
            not_before_str="2026-03-31T00:00:00Z",
            not_after_str="2026-04-30T23:59:59Z",
            checkout_mandate_hash="chk_hash_01",
            payment_mandate_transaction_id="chk_hash_01",
            receipt_reference="chk_hash_01",
            ordered_units=4,
            fulfilled_units=1,
            unit_price_minor=2500,
            delivery_deadline_passed=True,
        )
        self.assertTrue(ok_usd.admitted)
        self.assertEqual(ok_usd.budget_cap_minor, 29)
        self.assertEqual(ok_usd.overturned_amount_minor, 7500)

        # JPY zero-decimal currency: max=1000 JPY must reject 100,000 JPY
        jpy_over = evaluate_ap2_iso4217_budget_execution_and_dispute_guard(
            budget_max_major=1000,
            currency="JPY",
            spend_amount_minor=100_000,
            execution_date_str="2026-04-15T12:00:00Z",
            not_before_str="2026-03-31T00:00:00Z",
            not_after_str="2026-04-30T23:59:59Z",
            checkout_mandate_hash="chk_hash_01",
            payment_mandate_transaction_id="chk_hash_01",
            receipt_reference="chk_hash_01",
            ordered_units=1,
            fulfilled_units=1,
            unit_price_minor=1000,
            delivery_deadline_passed=False,
        )
        self.assertFalse(jpy_over.admitted)
        self.assertEqual(jpy_over.decision_code, "AP2_BUDGET_ISO4217_MINOR_UNIT_CAP_EXCEEDED")

        # Offset instant after window ("2026-04-30T23:59:59-09:00" == 2026-05-01T08:59:59Z) rejected
        tz_after = evaluate_ap2_iso4217_budget_execution_and_dispute_guard(
            budget_max_major=100.0,
            currency="USD",
            spend_amount_minor=5000,
            execution_date_str="2026-04-30T23:59:59-09:00",
            not_before_str="2026-03-31T00:00:00Z",
            not_after_str="2026-04-30T23:59:59Z",
            checkout_mandate_hash="chk_hash_01",
            payment_mandate_transaction_id="chk_hash_01",
            receipt_reference="chk_hash_01",
            ordered_units=1,
            fulfilled_units=1,
            unit_price_minor=5000,
            delivery_deadline_passed=False,
        )
        self.assertFalse(tz_after.admitted)
        self.assertEqual(
            tz_after.decision_code,
            "AP2_EXECUTION_DATE_OUTSIDE_ISO8601_WINDOW_BLOCKED",
        )

    def test_ucp_catalog_purpose_and_acp_delegate_telemetry_guard(self) -> None:
        candidates = (
            {"product_id": "prod_anchor", "variant_id": "var_anchor_1", "included_in_response": "false"},
            {"product_id": "prod_sub", "variant_id": "var_sub_1", "included_in_response": "true"},
        )
        ok = evaluate_ucp_catalog_purpose_and_acp_delegate_telemetry_guard(
            search_purpose="swap",
            reference_ids=("var_anchor_1",),
            has_query_or_filters=True,
            candidate_results=candidates,
            acp_endpoint="delegate_payment",
            signature_header_present=True,
            timestamp_header_present=True,
            complete_checkout_uses_legacy_risk_signals_for_telemetry=False,
            merchant_registered_scheme="merchant-shoe",
            product_url="https://merchant.example.com/products/prod_sub",
            app_links=({"platform": "chatgpt", "uri": "merchant-shoe://checkout/prod_sub"},),
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.resolved_target_uri, "merchant-shoe://checkout/prod_sub")

        # Scheme squatting blocked
        squat = evaluate_ucp_catalog_purpose_and_acp_delegate_telemetry_guard(
            search_purpose="swap",
            reference_ids=("var_anchor_1",),
            has_query_or_filters=True,
            candidate_results=candidates,
            acp_endpoint="delegate_payment",
            signature_header_present=True,
            timestamp_header_present=True,
            complete_checkout_uses_legacy_risk_signals_for_telemetry=False,
            merchant_registered_scheme="merchant-shoe",
            product_url="https://merchant.example.com/products/prod_sub",
            app_links=({"platform": "chatgpt", "uri": "other-brand://checkout/prod_sub"},),
        )
        self.assertFalse(squat.admitted)
        self.assertEqual(
            squat.decision_code,
            "ACP_APP_LINK_UNREGISTERED_SCHEME_SQUATTING_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
