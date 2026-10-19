"""Unit tests for Stage 35 UCP Post-Order Lifecycle, Catalog Substitution,
Food Allergen Safety & ACP MCP Mutating Tool / Host Spend Gate Guards.
"""

from __future__ import annotations

import unittest

from lab.ucp_post_order_catalog_food_guard import (
    compute_ucp_consultation_proposal_digest,
    evaluate_acp_mcp_mutating_tool_and_host_gate,
    evaluate_ucp_catalog_substitute_vs_search_guard,
    evaluate_ucp_food_allergen_and_dietary_guard,
    evaluate_ucp_order_consultation_decision_guard,
    evaluate_ucp_order_modification_lookup_and_fence,
)


class UCPPostOrderCatalogFoodGuardTest(unittest.TestCase):
    def test_ucp_food_allergen_fail_closed_and_no_inference(self) -> None:
        # Platform inferring free_of is strictly forbidden (UCP PR #964)
        inferred = evaluate_ucp_food_allergen_and_dietary_guard(
            line_item_id="line_01",
            dish_name="Pad Thai",
            dish_allergens=(),
            buyer_dietary_restrictions=({"code_list": "fda_falcpa", "code": "peanuts"},),
            platform_inferred_free_of_codes=("peanuts",),
        )
        self.assertFalse(inferred.admitted)
        self.assertEqual(inferred.decision_code, "PLATFORM_INFERRED_FREE_OF_FORBIDDEN")

        # Unrecorded allergen on a restricted buyer profile triggers requires_buyer_review
        unrecorded = evaluate_ucp_food_allergen_and_dietary_guard(
            line_item_id="line_02",
            dish_name="Seasonal Soup",
            dish_allergens=(
                {"code_list": "eu_1169_2011", "code": "gluten", "status": "free_of", "source": "kitchen"},
            ),
            buyer_dietary_restrictions=(
                {"code_list": "eu_1169_2011", "code": "celery"},
            ),
        )
        self.assertFalse(unrecorded.admitted)
        self.assertTrue(unrecorded.requires_buyer_review)
        self.assertEqual(unrecorded.decision_code, "ALLERGEN_CONFLICT_REQUIRES_BUYER_REVIEW")
        self.assertIn("celery", unrecorded.conflict_allergen_codes)

        # Explicitly business-asserted free_of passes
        safe = evaluate_ucp_food_allergen_and_dietary_guard(
            line_item_id="line_03",
            dish_name="Certified Allergen-Safe Bowl",
            dish_allergens=(
                {"code_list": "eu_1169_2011", "code": "celery", "status": "free_of", "source": "lab_test"},
            ),
            buyer_dietary_restrictions=(
                {"code_list": "eu_1169_2011", "code": "celery"},
            ),
        )
        self.assertTrue(safe.admitted)
        self.assertEqual(safe.decision_code, "FOOD_ALLERGEN_DIETARY_CHECK_PASSED")

    def test_ucp_catalog_substitute_vs_similarity_search(self) -> None:
        # Open-ended search_catalog(like=...) result blocked from auto-substitution (UCP PR #974)
        search_swap = evaluate_ucp_catalog_substitute_vs_search_guard(
            original_sku_id="sku_jacket_m",
            candidate_sku_id="sku_similar_coat",
            source_operation="search_catalog",
            include_relation_type="like_similarity",
            original_price_minor=10_000,
            candidate_price_minor=10_000,
        )
        self.assertFalse(search_swap.admitted)
        self.assertEqual(
            search_swap.decision_code,
            "UNVERIFIED_SIMILARITY_SEARCH_OR_RECOMMENDATION_SUBSTITUTION_BLOCKED",
        )

        # Business-asserted get_product(include=["substitutes"]) within price tolerance passes
        valid_sub = evaluate_ucp_catalog_substitute_vs_search_guard(
            original_sku_id="sku_milk_1l",
            candidate_sku_id="sku_organic_milk_1l",
            source_operation="get_product",
            include_relation_type="substitutes",
            original_price_minor=400,
            candidate_price_minor=415,
            max_auto_substitute_price_increase_bps=500,
        )
        self.assertTrue(valid_sub.admitted)
        self.assertEqual(valid_sub.decision_code, "ENTITY_SUBSTITUTE_VERIFIED")

    def test_ucp_order_modification_safe_lookup_and_atomic_fence(self) -> None:
        # Safe lookup MUST NOT mutate state (UCP PR #945 / EP #943)
        mutating_lookup = evaluate_ucp_order_modification_lookup_and_fence(
            order_id="ord_101",
            extension_negotiated=True,
            parent_order_capability_negotiated=True,
            operation_mode="lookup_cancel",
            current_order_version="v2",
            original_idempotency_key="idem_cancel_01",
            lookup_attempts_state_mutation=True,
        )
        self.assertFalse(mutating_lookup.admitted)
        self.assertEqual(mutating_lookup.decision_code, "UNSAFE_GET_LOOKUP_STATE_MUTATION_FORBIDDEN")

        # Fencing an unclaimed key writes tombstone; subsequent late arrival with old key is blocked
        fence_res = evaluate_ucp_order_modification_lookup_and_fence(
            order_id="ord_101",
            extension_negotiated=True,
            parent_order_capability_negotiated=True,
            operation_mode="fence_cancel",
            current_order_version="v2",
            idempotency_key="idem_fence_fresh_02",
            original_idempotency_key="idem_cancel_01",
            claimed_keys=frozenset(),
        )
        self.assertTrue(fence_res.admitted)
        self.assertEqual(fence_res.lookup_or_fence_outcome, "fenced")

        late_cancel = evaluate_ucp_order_modification_lookup_and_fence(
            order_id="ord_101",
            extension_negotiated=True,
            parent_order_capability_negotiated=True,
            operation_mode="create_cancel",
            current_order_version="v2",
            base_order_version="v2",
            idempotency_key="idem_cancel_01",
            fenced_keys=frozenset({"idem_cancel_01"}),
        )
        self.assertFalse(late_cancel.admitted)
        self.assertEqual(late_cancel.decision_code, "FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED")
        self.assertEqual(late_cancel.http_status, 409)

    def test_ucp_order_consultation_digest_and_authorization(self) -> None:
        proposal = {
            "consultation_id": "cons_946",
            "revision": 2,
            "order_id": "ord_946",
            "baseline": {"total_minor": 12000},
            "scope": {"type": "line_item", "id": "li_1"},
            "proposed_terms": {"total_minor": 13500},
            "effective_time_rules": {"mode": "immediate_on_approval"},
            "decision_deadline": "2026-10-20T12:00:00Z",
            "execution_deadline": "2026-10-21T12:00:00Z",
        }
        digest = compute_ucp_consultation_proposal_digest(proposal)

        # Vendor namespace served from ucp.dev violates authority binding
        bad_ns = evaluate_ucp_order_consultation_decision_guard(
            capability_name="com.example.shopping.order_consultation",
            schema_url="https://ucp.dev/schemas/shopping/order_consultation.json",
            proposal_core=proposal,
            submitted_revision=2,
            submitted_proposal_digest=digest,
            buyer_token_valid=True,
            buyer_token_is_platform_only=False,
            granted_scopes=("dev.ucp.shopping.order_consultation:decide",),
            token_subject_buyer_id="buyer_01",
            order_owner_buyer_id="buyer_01",
            delegation_max_additional_amount_minor=2000,
            proposed_additional_amount_minor=1500,
            serialization_timestamp_epoch=1792480000,
            decision_deadline_epoch=1792490000,
        )
        self.assertFalse(bad_ns.admitted)
        self.assertEqual(bad_ns.decision_code, "SCHEMA_AUTHORITY_BINDING_INVALID")

        # Only order:manage scope without order_consultation:decide fails with 403 insufficient_scope
        bad_scope = evaluate_ucp_order_consultation_decision_guard(
            capability_name="dev.ucp.shopping.order_consultation",
            schema_url="https://ucp.dev/schemas/shopping/order_consultation.json",
            proposal_core=proposal,
            submitted_revision=2,
            submitted_proposal_digest=digest,
            buyer_token_valid=True,
            buyer_token_is_platform_only=False,
            granted_scopes=("dev.ucp.shopping.order:manage",),
            token_subject_buyer_id="buyer_01",
            order_owner_buyer_id="buyer_01",
            delegation_max_additional_amount_minor=2000,
            proposed_additional_amount_minor=1500,
            serialization_timestamp_epoch=1792480000,
            decision_deadline_epoch=1792490000,
        )
        self.assertFalse(bad_scope.admitted)
        self.assertEqual(bad_scope.decision_code, "insufficient_scope")
        self.assertEqual(bad_scope.http_status, 403)

        # Valid buyer-authenticated decision with matching RFC 8785 digest succeeds
        ok_decision = evaluate_ucp_order_consultation_decision_guard(
            capability_name="dev.ucp.shopping.order_consultation",
            schema_url="https://ucp.dev/schemas/shopping/order_consultation.json",
            proposal_core=proposal,
            submitted_revision=2,
            submitted_proposal_digest=digest,
            buyer_token_valid=True,
            buyer_token_is_platform_only=False,
            granted_scopes=("dev.ucp.shopping.order_consultation:decide",),
            token_subject_buyer_id="buyer_01",
            order_owner_buyer_id="buyer_01",
            delegation_max_additional_amount_minor=2000,
            proposed_additional_amount_minor=1500,
            serialization_timestamp_epoch=1792480000,
            decision_deadline_epoch=1792490000,
        )
        self.assertTrue(ok_decision.admitted)
        self.assertEqual(ok_decision.decision_code, "ORDER_CONSULTATION_DECISION_RECEIPT_ISSUED")

    def test_acp_mcp_mutating_tool_idempotency_and_host_gate(self) -> None:
        missing_idem = evaluate_acp_mcp_mutating_tool_and_host_gate(
            tool_name="complete_checkout_session",
            meta_idempotency_key=None,
            host_spend_gate_required=True,
            host_kya_signature_valid=True,
            host_kya_bound_tool="complete_checkout_session",
            host_kya_bound_session_id="cs_123",
            target_session_id="cs_123",
            merchant_psp_rail_authorized=True,
        )
        self.assertFalse(missing_idem.admitted)
        self.assertEqual(missing_idem.decision_code, "ACP_MCP_MUTATING_TOOL_IDEMPOTENCY_KEY_MISSING")

        valid_gate = evaluate_acp_mcp_mutating_tool_and_host_gate(
            tool_name="complete_checkout_session",
            meta_idempotency_key="idem_acp_mcp_998877",
            host_spend_gate_required=True,
            host_kya_signature_valid=True,
            host_kya_bound_tool="complete_checkout_session",
            host_kya_bound_session_id="cs_123",
            target_session_id="cs_123",
            merchant_psp_rail_authorized=True,
        )
        self.assertTrue(valid_gate.admitted)
        self.assertEqual(valid_gate.decision_code, "ACP_MCP_MUTATING_TOOL_AND_HOST_GATE_VERIFIED")


if __name__ == "__main__":
    unittest.main()
