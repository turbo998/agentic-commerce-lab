"""Unit tests for Stage 36 UCP Declarative A2UI / MCP Apps Isolation (`#899`),
Time-Bound Quote Extension (`#930`), Offer Decision-Integrity Provenance (`#918`),
Reverse-DNS `declared_fields` (`#915`), and Split-Payment Credential Echo Guard (`#893`).
"""

from __future__ import annotations

import hashlib
import json
import unittest

from lab.ucp_ui_quote_offer_declared_fields_guard import (
    evaluate_ucp_declared_fields_extensible_checkout,
    evaluate_ucp_offer_decision_integrity_guard,
    evaluate_ucp_quote_lifecycle_and_totals_guard,
    evaluate_ucp_ui_extension_a2ui_mcp_guard,
    verify_ucp_split_payment_no_credential_echo,
)


class UCPUiQuoteOfferDeclaredFieldsGuardTest(unittest.TestCase):
    def test_ucp_ui_extension_model_context_and_cart_merge(self) -> None:
        # Business UI strings injected into MCP text content[] are blocked (UCP PR #899)
        leaked_ctx = evaluate_ucp_ui_extension_a2ui_mcp_guard(
            ui_extension_negotiated=True,
            ui_media_type="application/vnd.a2ui+json",
            platform_supported_formats=("application/vnd.a2ui+json",),
            contains_executable_html_or_script=False,
            transport_surface="response_ui_field",
            included_in_mcp_text_content_array=True,
            requested_ui_action_operation_id="create_cart",
            negotiated_capabilities=("dev.ucp.shopping.cart",),
            has_existing_held_cart=True,
            platform_enforces_buyer_consent_and_disclosures=True,
        )
        self.assertFalse(leaked_ctx.admitted)
        self.assertEqual(leaked_ctx.decision_code, "BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED")

        # Valid A2UI response omitted from model context and merging create_cart -> update_cart
        ok_ui = evaluate_ucp_ui_extension_a2ui_mcp_guard(
            ui_extension_negotiated=True,
            ui_media_type="application/vnd.a2ui+json",
            platform_supported_formats=("application/vnd.a2ui+json",),
            contains_executable_html_or_script=False,
            transport_surface="response_ui_field",
            included_in_mcp_text_content_array=False,
            requested_ui_action_operation_id="create_cart",
            negotiated_capabilities=("dev.ucp.shopping.cart",),
            has_existing_held_cart=True,
            platform_enforces_buyer_consent_and_disclosures=True,
        )
        self.assertTrue(ok_ui.admitted)
        self.assertEqual(ok_ui.resolved_operation, "update_cart")

    def test_ucp_quote_lifecycle_and_totals_reflection(self) -> None:
        # Missing or mismatched totals[type="quote"] entry fails (UCP PR #930)
        bad_totals = evaluate_ucp_quote_lifecycle_and_totals_guard(
            quote_id="qt_930",
            quote_status="accepted",
            quote_subtotal_minor=45_000,
            quote_expires_at_epoch=1800000000,
            now_epoch=1790000000,
            buyer_accepted_id="qt_930",
            is_complete_checkout_request=False,
            accepted_id_present_on_complete_request=False,
            totals_entries=({"type": "subtotal", "amount": 45_000},),
        )
        self.assertFalse(bad_totals.admitted)
        self.assertEqual(bad_totals.decision_code, "AUTHORITATIVE_TOTALS_QUOTE_ENTRY_MISMATCH")

        # Valid accepted quote reflected in totals[] and projected onto Order
        ok_quote = evaluate_ucp_quote_lifecycle_and_totals_guard(
            quote_id="qt_930",
            quote_status="accepted",
            quote_subtotal_minor=45_000,
            quote_expires_at_epoch=1800000000,
            now_epoch=1790000000,
            buyer_accepted_id="qt_930",
            is_complete_checkout_request=True,
            accepted_id_present_on_complete_request=False,
            totals_entries=({"type": "quote", "amount": 45_000},),
        )
        self.assertTrue(ok_quote.admitted)
        self.assertEqual(ok_quote.order_projection, {"id": "qt_930", "subtotal": 45_000})

    def test_ucp_offer_decision_integrity_provenance_and_commit(self) -> None:
        base_fields = {"sku": "sku_gpu_h200", "unit_price_minor": 250_000}
        provenance_ext = {"return_window_override": "not_accepted", "territory": "US-ONLY"}
        full_subject = {
            "offer_id": "off_918",
            "base": base_fields,
            "provenance_extensions": provenance_ext,
        }
        full_digest = "sha-256:" + hashlib.sha256(
            json.dumps(full_subject, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        # Under-bound digest omitting provenance extensions is blocked (UCP PR #918)
        underbound = evaluate_ucp_offer_decision_integrity_guard(
            offer_id="off_918",
            base_offer_fields=base_fields,
            commercial_provenance_extensions=provenance_ext,
            signed_digest_includes_provenance_extensions=False,
            submitted_offer_digest="sha-256:0000",
            offer_stage_state="checkout_committed",
            checkout_inventory_and_budget_locked=True,
        )
        self.assertFalse(underbound.admitted)
        self.assertEqual(underbound.decision_code, "OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED")

        # Valid full-provenance digest + checkout_committed passes
        ok_offer = evaluate_ucp_offer_decision_integrity_guard(
            offer_id="off_918",
            base_offer_fields=base_fields,
            commercial_provenance_extensions=provenance_ext,
            signed_digest_includes_provenance_extensions=True,
            submitted_offer_digest=full_digest,
            offer_stage_state="checkout_committed",
            checkout_inventory_and_budget_locked=True,
        )
        self.assertTrue(ok_offer.admitted)
        self.assertEqual(ok_offer.decision_code, "OFFER_PROVENANCE_AND_COMMIT_INTEGRITY_VERIFIED")

    def test_ucp_declared_fields_and_split_payment_credential_echo(self) -> None:
        # Scope mismatch (item-scoped field placed at checkout level) is blocked (UCP PR #915)
        bad_scope = evaluate_ucp_declared_fields_extensible_checkout(
            config_schemas={
                "com.acme.freight.dock_door": {"scope": "checkout"},
                "com.acme.engraving.text": {"scope": "line_item"},
            },
            checkout_required_declared_fields=("com.acme.freight.dock_door",),
            line_item_required_declared_fields=("com.acme.engraving.text",),
            checkout_declared_fields={
                "com.acme.freight.dock_door": "DOCK-4B",
                "com.acme.engraving.text": "WRONG-SCOPE",
            },
            line_item_declared_fields={},
        )
        self.assertFalse(bad_scope.admitted)
        self.assertEqual(bad_scope.decision_code, "DECLARED_FIELDS_SCHEMA_OR_SCOPE_MISMATCH_BLOCKED")

        # Echoing gift-card or card token in split-payment response is blocked (UCP PR #893)
        echo_leak = verify_ucp_split_payment_no_credential_echo(
            response_payment_instruments=(
                {"id": "inst_gc_1", "type": "gift_card", "credential": {"token": "gc_secret_123"}},
                {"id": "inst_cc_2", "type": "card", "brand": "visa", "last_digits": "4242"},
            ),
        )
        self.assertFalse(echo_leak.admitted)
        self.assertEqual(echo_leak.decision_code, "SPLIT_PAYMENT_CREDENTIAL_ECHO_LEAK_BLOCKED")
        self.assertEqual(echo_leak.leaked_instrument_ids, ("inst_gc_1",))

        clean_resp = verify_ucp_split_payment_no_credential_echo(
            response_payment_instruments=(
                {"id": "inst_gc_1", "type": "gift_card", "last_digits": "9876"},
                {"id": "inst_cc_2", "type": "card", "brand": "visa", "last_digits": "4242"},
            ),
        )
        self.assertTrue(clean_resp.admitted)
        self.assertEqual(clean_resp.decision_code, "SPLIT_PAYMENT_RESPONSE_CREDENTIAL_OMITTED_CLEAN")


if __name__ == "__main__":
    unittest.main()
