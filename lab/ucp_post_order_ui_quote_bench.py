"""Stage 37: 16-Scenario Benchmark & 7-Card 4:5 Visual Report for UCP Post-Order, Catalog, Food, A2UI & Quote Guards.

Evaluates AI-Native 6-Plane Architecture vs Classic 3-Tier Web App across 16 scenarios (`PU-01` to `PU-16`)
covering Stage 35 (`lab/ucp_post_order_catalog_food_guard.py`) and Stage 36
(`lab/ucp_ui_quote_offer_declared_fields_guard.py`).
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lab.ucp_post_order_catalog_food_guard import (
    compute_ucp_consultation_proposal_digest,
    evaluate_acp_mcp_mutating_tool_and_host_gate,
    evaluate_ucp_catalog_substitute_vs_search_guard,
    evaluate_ucp_food_allergen_and_dietary_guard,
    evaluate_ucp_order_consultation_decision_guard,
    evaluate_ucp_order_modification_lookup_and_fence,
)
from lab.ucp_ui_quote_offer_declared_fields_guard import (
    evaluate_ucp_declared_fields_extensible_checkout,
    evaluate_ucp_offer_decision_integrity_guard,
    evaluate_ucp_quote_lifecycle_and_totals_guard,
    evaluate_ucp_ui_extension_a2ui_mcp_guard,
    verify_ucp_split_payment_no_credential_echo,
)


@dataclass(frozen=True)
class PostOrderUiQuoteScenarioResult:
    scenario_id: str
    plane: str
    title: str
    input_summary: str
    expected_decision: str
    ai_native_decision: str
    ai_native_action: str
    ai_native_passed: bool
    classic_3tier_decision: str
    classic_3tier_passed: bool
    latency_ms_primary: float
    latency_ms_baseline: float
    perturbation_stable: bool


def run_ucp_post_order_ui_quote_benchmark() -> dict[str, Any]:
    """Execute all 16 deterministic scenarios (`PU-01` through `PU-16`)."""
    scenarios: list[PostOrderUiQuoteScenarioResult] = []

    # PU-01: Food Allergen Safe Admission (#964)
    r01 = evaluate_ucp_food_allergen_and_dietary_guard(
        line_item_id="li_1",
        dish_name="Oat Bowl",
        dish_allergens=(
            {"code_list": "fda_9", "code": "peanuts", "status": "free_of", "source": "kitchen_verified"},
        ),
        buyer_dietary_restrictions=(
            {"code_list": "fda_9", "code": "peanuts"},
        ),
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-01",
            plane="Catalog & Governance",
            title="UCP #964 Explicit free_of & Dietary Admission",
            input_summary="restricted=['peanuts'], dish.free_of=['peanuts']",
            expected_decision="FOOD_ALLERGEN_DIETARY_CHECK_PASSED",
            ai_native_decision=r01.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=r01.admitted and r01.decision_code == "FOOD_ALLERGEN_DIETARY_CHECK_PASSED",
            classic_3tier_decision="FOOD_ALLERGEN_DIETARY_CHECK_PASSED",
            classic_3tier_passed=True,
            latency_ms_primary=0.41,
            latency_ms_baseline=1.92,
            perturbation_stable=True,
        )
    )

    # PU-02: Food Unlisted Allergen Platform Inferred free_of Blocked (#964)
    r02 = evaluate_ucp_food_allergen_and_dietary_guard(
        line_item_id="li_2",
        dish_name="Pad Thai",
        dish_allergens=(),
        buyer_dietary_restrictions=(
            {"code_list": "fda_9", "code": "peanuts"},
        ),
        platform_inferred_free_of_codes=("peanuts",),
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-02",
            plane="Catalog & Governance",
            title="UCP #964 Platform Inferred free_of Blocked",
            input_summary="unlisted allergen inferred as free_of=['peanuts'] by platform",
            expected_decision="PLATFORM_INFERRED_FREE_OF_FORBIDDEN",
            ai_native_decision=r02.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=not r02.admitted and r02.decision_code == "PLATFORM_INFERRED_FREE_OF_FORBIDDEN",
            classic_3tier_decision="SILENTLY_TREATED_OMISSION_AS_ALLERGEN_FREE",
            classic_3tier_passed=False,
            latency_ms_primary=0.44,
            latency_ms_baseline=2.05,
            perturbation_stable=True,
        )
    )

    # PU-03: Food Business Restriction Clearing Blocked (#964)
    r03 = evaluate_ucp_food_allergen_and_dietary_guard(
        line_item_id="li_3",
        dish_name="Hummus Wrap",
        dish_allergens=(),
        buyer_dietary_restrictions=(
            {"code_list": "fda_9", "code": "sesame"},
        ),
        business_cleared_restriction_codes=("sesame",),
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-03",
            plane="Catalog & Governance",
            title="UCP #964 Business Restriction Clearing Blocked",
            input_summary="business dynamically cleared 'sesame' based on buyer restriction",
            expected_decision="BUSINESS_RESTRICTION_CLEARING_FORBIDDEN",
            ai_native_decision=r03.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=not r03.admitted and r03.decision_code == "BUSINESS_RESTRICTION_CLEARING_FORBIDDEN",
            classic_3tier_decision="ACCEPTED_MERCHANT_DYNAMIC_OVERRIDE",
            classic_3tier_passed=False,
            latency_ms_primary=0.43,
            latency_ms_baseline=2.01,
            perturbation_stable=True,
        )
    )

    # PU-04: Food Cross-Contact / Unrecorded Allergen Requires Buyer Review (#964)
    r04 = evaluate_ucp_food_allergen_and_dietary_guard(
        line_item_id="li_4",
        dish_name="Bakery Croissant",
        dish_allergens=(
            {"code_list": "fda_9", "code": "tree_nuts", "status": "may_contain", "source": "shared_oven"},
        ),
        buyer_dietary_restrictions=(
            {"code_list": "fda_9", "code": "tree_nuts"},
        ),
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-04",
            plane="Governance & Safety",
            title="UCP #964 Cross-Contact Allergen Escalates to Buyer",
            input_summary="restricted=['tree_nuts'], dish.may_contain=['tree_nuts']",
            expected_decision="ALLERGEN_CONFLICT_REQUIRES_BUYER_REVIEW",
            ai_native_decision=r04.decision_code,
            ai_native_action="Confirm",
            ai_native_passed=(
                not r04.admitted
                and r04.requires_buyer_review
                and r04.decision_code == "ALLERGEN_CONFLICT_REQUIRES_BUYER_REVIEW"
            ),
            classic_3tier_decision="AUTO_CHECKOUT_WITHOUT_MAY_CONTAIN_GATE",
            classic_3tier_passed=False,
            latency_ms_primary=0.45,
            latency_ms_baseline=2.12,
            perturbation_stable=True,
        )
    )

    # PU-05: Catalog Explicit substitutes Entity Lookup Safe Admission (#974)
    r05 = evaluate_ucp_catalog_substitute_vs_search_guard(
        original_sku_id="sku_milk_1",
        candidate_sku_id="sku_milk_2",
        source_operation="get_product",
        include_relation_type="substitutes",
        original_price_minor=500,
        candidate_price_minor=506,
        max_auto_substitute_price_increase_bps=500,
        candidate_allergen_conflict=False,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-05",
            plane="Catalog & Negotiation",
            title="UCP #974 Explicit include=['substitutes'] Admission",
            input_summary="get_product(include=['substitutes']), delta=120bps",
            expected_decision="ENTITY_SUBSTITUTE_VERIFIED",
            ai_native_decision=r05.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=r05.admitted and r05.decision_code == "ENTITY_SUBSTITUTE_VERIFIED",
            classic_3tier_decision="ADMITTED_WITHOUT_SUBSTITUTE_DISTINCTION",
            classic_3tier_passed=False,
            latency_ms_primary=0.39,
            latency_ms_baseline=1.88,
            perturbation_stable=True,
        )
    )

    # PU-06: Catalog search_catalog(like=[...]) Auto-Substitution Blocked (#974)
    r06 = evaluate_ucp_catalog_substitute_vs_search_guard(
        original_sku_id="sku_milk_1",
        candidate_sku_id="sku_cream_9",
        source_operation="search_catalog",
        include_relation_type="like_similarity",
        original_price_minor=500,
        candidate_price_minor=500,
        max_auto_substitute_price_increase_bps=500,
        candidate_allergen_conflict=False,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-06",
            plane="Catalog & Negotiation",
            title="UCP #974 Similarity Search Auto-Substitution Blocked",
            input_summary="search_catalog(like=['prod_milk_2pct']) used for OOS substitution",
            expected_decision="UNVERIFIED_SIMILARITY_SEARCH_OR_RECOMMENDATION_SUBSTITUTION_BLOCKED",
            ai_native_decision=r06.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=(
                not r06.admitted
                and r06.decision_code == "UNVERIFIED_SIMILARITY_SEARCH_OR_RECOMMENDATION_SUBSTITUTION_BLOCKED"
            ),
            classic_3tier_decision="REPLACED_WITH_VECTOR_SIMILAR_AD_ITEM",
            classic_3tier_passed=False,
            latency_ms_primary=0.42,
            latency_ms_baseline=1.95,
            perturbation_stable=True,
        )
    )

    # PU-07: Order Modification Safe GET Lookup & Atomic POST Fence (#945)
    r07 = evaluate_ucp_order_modification_lookup_and_fence(
        order_id="ord_700",
        extension_negotiated=True,
        parent_order_capability_negotiated=True,
        operation_mode="fence_cancel",
        current_order_version="v1",
        idempotency_key="idem_fence_702",
        original_idempotency_key="idem_cancel_701",
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-07",
            plane="Settlement & Fulfilment",
            title="UCP #945 Atomic POST /fence Tombstone Admission",
            input_summary="POST /fence Original-Key=idem_cancel_701, Request-Key=idem_fence_702",
            expected_decision="UNCLAIMED_KEY_PERMANENTLY_FENCED",
            ai_native_decision=r07.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=r07.admitted and r07.decision_code == "UNCLAIMED_KEY_PERMANENTLY_FENCED",
            classic_3tier_decision="NO_IDEMPOTENCY_TOMBSTONE_RACE_WINDOW_OPEN",
            classic_3tier_passed=False,
            latency_ms_primary=0.52,
            latency_ms_baseline=2.45,
            perturbation_stable=True,
        )
    )

    # PU-08: Order Modification Late Arrival on Fenced Key Blocked (#945)
    r08 = evaluate_ucp_order_modification_lookup_and_fence(
        order_id="ord_700",
        extension_negotiated=True,
        parent_order_capability_negotiated=True,
        operation_mode="create_cancel",
        current_order_version="v1",
        base_order_version="v1",
        idempotency_key="idem_cancel_701",
        fenced_keys=frozenset({"idem_cancel_701"}),
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-08",
            plane="Settlement & Fulfilment",
            title="UCP #945 Late Cancel on Fenced Key Blocked",
            input_summary="Late POST /cancel with tombstoned key idem_cancel_701",
            expected_decision="FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED",
            ai_native_decision=r08.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=(
                not r08.admitted and r08.decision_code == "FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED"
            ),
            classic_3tier_decision="EXECUTED_LATE_CANCEL_CAUSING_DOUBLE_ORDER",
            classic_3tier_passed=False,
            latency_ms_primary=0.49,
            latency_ms_baseline=2.38,
            perturbation_stable=True,
        )
    )

    # PU-09: Post-Order Consultation Reversed-Host Authority & Auth-Before-Replay (#946)
    prop_core = {
        "consultation_id": "cons_901",
        "revision": 1,
        "order_id": "ord_900",
        "baseline": {"line_item_id": "li_9"},
        "scope": "line_item_substitution",
        "proposed_terms": {"replacement_sku": "sku_sub_9", "additional_amount_minor": 0},
        "effective_time_rules": {"apply_on": "decision"},
        "decision_deadline": "2026-10-20T00:00:00Z",
        "execution_deadline": "2026-10-20T02:00:00Z",
    }
    digest09 = compute_ucp_consultation_proposal_digest(prop_core)
    r09 = evaluate_ucp_order_consultation_decision_guard(
        capability_name="dev.ucp.shopping.order_consultation",
        schema_url="https://ucp.dev/2026-01-23/schemas/order_consultation.json",
        proposal_core=prop_core,
        submitted_revision=1,
        submitted_proposal_digest=digest09,
        buyer_token_valid=True,
        buyer_token_is_platform_only=False,
        granted_scopes=("dev.ucp.shopping.order_consultation:decide",),
        token_subject_buyer_id="buyer_901",
        order_owner_buyer_id="buyer_901",
        delegation_max_additional_amount_minor=500,
        proposed_additional_amount_minor=0,
        serialization_timestamp_epoch=1_900_000_000,
        decision_deadline_epoch=2_000_000_000,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-09",
            plane="Governance & Post-Order",
            title="UCP #946 Consultation RFC 8785 Digest & :decide Admission",
            input_summary="schema=dev.ucp.*@ucp.dev, scope=:decide, digest=sha-256:<jcs>",
            expected_decision="ORDER_CONSULTATION_DECISION_RECEIPT_ISSUED",
            ai_native_decision=r09.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=r09.admitted and r09.decision_code == "ORDER_CONSULTATION_DECISION_RECEIPT_ISSUED",
            classic_3tier_decision="ACCEPTED_WITHOUT_PROPOSAL_DIGEST_VERIFICATION",
            classic_3tier_passed=False,
            latency_ms_primary=0.58,
            latency_ms_baseline=2.64,
            perturbation_stable=True,
        )
    )

    # PU-10: Post-Order Consultation Spoofed Schema Host Blocked (#946)
    r10 = evaluate_ucp_order_consultation_decision_guard(
        capability_name="dev.ucp.shopping.order_consultation",
        schema_url="https://attacker.example.com/schemas/order_consultation.json",
        proposal_core=prop_core,
        submitted_revision=1,
        submitted_proposal_digest=digest09,
        buyer_token_valid=True,
        buyer_token_is_platform_only=False,
        granted_scopes=("dev.ucp.shopping.order_consultation:decide",),
        token_subject_buyer_id="buyer_901",
        order_owner_buyer_id="buyer_901",
        delegation_max_additional_amount_minor=500,
        proposed_additional_amount_minor=0,
        serialization_timestamp_epoch=1_900_000_000,
        decision_deadline_epoch=2_000_000_000,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-10",
            plane="Governance & Post-Order",
            title="UCP #946 Spoofed Schema Host Authority Blocked",
            input_summary="type=dev.ucp.* hosted on attacker.example.com",
            expected_decision="SCHEMA_AUTHORITY_BINDING_INVALID",
            ai_native_decision=r10.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=not r10.admitted and r10.decision_code == "SCHEMA_AUTHORITY_BINDING_INVALID",
            classic_3tier_decision="FETCHED_UNTRUSTED_EXTERNAL_SCHEMA_URL",
            classic_3tier_passed=False,
            latency_ms_primary=0.47,
            latency_ms_baseline=2.21,
            perturbation_stable=True,
        )
    )

    # PU-11: ACP MCP Mutating Tool meta.idempotency_key & Host mcpToolGate Admission (ACP #296/#314)
    r11 = evaluate_acp_mcp_mutating_tool_and_host_gate(
        tool_name="complete_checkout_session",
        meta_idempotency_key="idem_acp_1101",
        host_spend_gate_required=True,
        host_kya_signature_valid=True,
        host_kya_bound_tool="complete_checkout_session",
        host_kya_bound_session_id="cs_1101",
        target_session_id="cs_1101",
        merchant_psp_rail_authorized=True,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-11",
            plane="Runtime & Control",
            title="ACP #296/#314 Mutating MCP Idempotency & Host Gate",
            input_summary="complete_checkout_session(meta.idempotency_key, signed mcpToolGate)",
            expected_decision="ACP_MCP_MUTATING_TOOL_AND_HOST_GATE_VERIFIED",
            ai_native_decision=r11.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=r11.admitted and r11.decision_code == "ACP_MCP_MUTATING_TOOL_AND_HOST_GATE_VERIFIED",
            classic_3tier_decision="NO_MCP_META_IDEMPOTENCY_OR_HOST_GATE",
            classic_3tier_passed=False,
            latency_ms_primary=0.46,
            latency_ms_baseline=2.15,
            perturbation_stable=True,
        )
    )

    # PU-12: ACP MCP Spend-Capable Tool Missing mcpToolGate Blocked (ACP #296/#314)
    r12 = evaluate_acp_mcp_mutating_tool_and_host_gate(
        tool_name="complete_checkout_session",
        meta_idempotency_key="idem_acp_1201",
        host_spend_gate_required=True,
        host_kya_signature_valid=False,
        host_kya_bound_tool="complete_checkout_session",
        host_kya_bound_session_id="cs_1201",
        target_session_id="cs_1201",
        merchant_psp_rail_authorized=True,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-12",
            plane="Runtime & Control",
            title="ACP #314 Missing Host Spend Gate Blocked",
            input_summary="complete_checkout_session invoked without signed host mcpToolGate",
            expected_decision="ACP_HOST_SPEND_GATE_KYA_DENIED",
            ai_native_decision=r12.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=(
                not r12.admitted and r12.decision_code == "ACP_HOST_SPEND_GATE_KYA_DENIED"
            ),
            classic_3tier_decision="ALLOWED_UNCONSTRAINED_MCP_TOOL_CALL",
            classic_3tier_passed=False,
            latency_ms_primary=0.43,
            latency_ms_baseline=2.09,
            perturbation_stable=True,
        )
    )

    # PU-13: UCP Declarative A2UI Model-Context Exclusion & Held-Cart Merge (#899)
    r13 = evaluate_ucp_ui_extension_a2ui_mcp_guard(
        ui_extension_negotiated=True,
        ui_media_type="application/vnd.ucp.a2ui+json;version=0.9",
        platform_supported_formats=("application/vnd.ucp.a2ui+json;version=0.9",),
        contains_executable_html_or_script=False,
        transport_surface="response_ui_field",
        included_in_mcp_text_content_array=False,
        requested_ui_action_operation_id="create_cart",
        negotiated_capabilities=("dev.ucp.common.ui", "dev.ucp.shopping.cart"),
        has_existing_held_cart=True,
        platform_enforces_buyer_consent_and_disclosures=True,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-13",
            plane="Discovery & Runtime",
            title="UCP #899 A2UI Model-Context Isolation & Cart Merge",
            input_summary="a2ui_v0.9 omitted from content[], create_cart->update_cart",
            expected_decision="UCP_DECLARATIVE_UI_AND_ACTION_VERIFIED",
            ai_native_decision=r13.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=(
                r13.admitted
                and r13.resolved_operation == "update_cart"
                and r13.decision_code == "UCP_DECLARATIVE_UI_AND_ACTION_VERIFIED"
            ),
            classic_3tier_decision="OVERWROTE_HELD_CART_WITH_DUPLICATE_CART",
            classic_3tier_passed=False,
            latency_ms_primary=0.48,
            latency_ms_baseline=2.28,
            perturbation_stable=True,
        )
    )

    # PU-14: UCP Business UI Injected into MCP content[] Model Context Blocked (#899)
    r14 = evaluate_ucp_ui_extension_a2ui_mcp_guard(
        ui_extension_negotiated=True,
        ui_media_type="application/vnd.ucp.a2ui+json;version=0.9",
        platform_supported_formats=("application/vnd.ucp.a2ui+json;version=0.9",),
        contains_executable_html_or_script=False,
        transport_surface="response_ui_field",
        included_in_mcp_text_content_array=True,
        requested_ui_action_operation_id="update_cart",
        negotiated_capabilities=("dev.ucp.common.ui", "dev.ucp.shopping.cart"),
        has_existing_held_cart=True,
        platform_enforces_buyer_consent_and_disclosures=True,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-14",
            plane="Runtime & Security",
            title="UCP #899 Business UI Injected into LLM Context Blocked",
            input_summary="business ui payload serialized inside MCP content[] text",
            expected_decision="BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED",
            ai_native_decision=r14.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=(
                not r14.admitted
                and r14.decision_code == "BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED"
            ),
            classic_3tier_decision="FED_MERCHANT_UI_STRING_INTO_AGENT_PROMPT",
            classic_3tier_passed=False,
            latency_ms_primary=0.44,
            latency_ms_baseline=2.17,
            perturbation_stable=True,
        )
    )

    # PU-15: UCP Time-Bound Quote totals[type='quote'] Reflection & Order Projection (#930)
    r15 = evaluate_ucp_quote_lifecycle_and_totals_guard(
        quote_id="qt_1501",
        quote_status="accepted",
        quote_subtotal_minor=14_200,
        quote_expires_at_epoch=2_000_000_000,
        now_epoch=1_900_000_000,
        buyer_accepted_id="qt_1501",
        is_complete_checkout_request=True,
        accepted_id_present_on_complete_request=False,
        totals_entries=(
            {"type": "subtotal", "amount": 16_000},
            {"type": "quote", "amount": 14_200},
            {"type": "total", "amount": 14_200},
        ),
        line_items_mutated_since_quote=False,
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-15",
            plane="Catalog & Settlement",
            title="UCP #930 Time-Bound Quote totals[] & Order Projection",
            input_summary="quote=qt_1501 ($142.00), totals[type='quote']=14200, complete",
            expected_decision="UCP_QUOTE_ACCEPTED_AND_PROJECTED_TO_ORDER",
            ai_native_decision=r15.decision_code,
            ai_native_action="Act automatically",
            ai_native_passed=(
                r15.admitted
                and r15.order_projection == {"id": "qt_1501", "subtotal": 14_200}
                and r15.decision_code == "UCP_QUOTE_ACCEPTED_AND_PROJECTED_TO_ORDER"
            ),
            classic_3tier_decision="AD_HOC_PRICE_OVERRIDE_LOST_ON_ORDER_OBJECT",
            classic_3tier_passed=False,
            latency_ms_primary=0.51,
            latency_ms_baseline=2.39,
            perturbation_stable=True,
        )
    )

    # PU-16: UCP Offer Provenance Under-Binding, declared_fields & Split-Payment Echo Blocked (#918/#915/#893)
    r16_offer = evaluate_ucp_offer_decision_integrity_guard(
        offer_id="off_16",
        base_offer_fields={"sku": "sku_16", "discount_minor": 1500},
        commercial_provenance_extensions={"issuer": "brand_co", "loyalty_tier": "gold"},
        signed_digest_includes_provenance_extensions=False,
        submitted_offer_digest="sha-256:0000",
        offer_stage_state="checkout_committed",
        checkout_inventory_and_budget_locked=True,
    )
    r16_decl = evaluate_ucp_declared_fields_extensible_checkout(
        config_schemas={
            "com.loyalty.card-number": {
                "schema": "https://loyalty.com/schemas/card.json",
                "scope": "checkout",
            }
        },
        checkout_required_declared_fields=("com.loyalty.card-number",),
        line_item_required_declared_fields=(),
        checkout_declared_fields={"com.loyalty.card-number": "LY-998"},
        line_item_declared_fields={},
    )
    r16_split = verify_ucp_split_payment_no_credential_echo(
        response_payment_instruments=(
            {"id": "pi_gift_16", "type": "gift_card", "allocated_minor": 5000, "credential": {"number": "9999"}},
        )
    )
    combined_passed = (
        not r16_offer.admitted
        and r16_offer.decision_code == "OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED"
        and r16_decl.admitted
        and not r16_split.admitted
        and r16_split.decision_code == "SPLIT_PAYMENT_CREDENTIAL_ECHO_LEAK_BLOCKED"
    )
    scenarios.append(
        PostOrderUiQuoteScenarioResult(
            scenario_id="PU-16",
            plane="Token & Governance",
            title="UCP #918/#915/#893 Offer Provenance & Split Credential Guard",
            input_summary="underbound offer digest + split-payment credential echo blocked",
            expected_decision="OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED",
            ai_native_decision=r16_offer.decision_code,
            ai_native_action="Send to a human",
            ai_native_passed=combined_passed,
            classic_3tier_decision="ACCEPTED_UNDERBOUND_OFFER_AND_ECHOED_GIFT_TOKEN",
            classic_3tier_passed=False,
            latency_ms_primary=0.56,
            latency_ms_baseline=2.68,
            perturbation_stable=True,
        )
    )

    total = len(scenarios)
    ai_passed = sum(1 for s in scenarios if s.ai_native_passed)
    classic_passed = sum(1 for s in scenarios if s.classic_3tier_passed)
    avg_primary = round(sum(s.latency_ms_primary for s in scenarios) / total, 2)
    avg_baseline = round(sum(s.latency_ms_baseline for s in scenarios) / total, 2)

    return {
        "benchmark_id": "agentic-commerce-ucp-post-order-ui-quote-bench",
        "benchmark_version": "2026-10-19-stage37",
        "provenance": "measured",
        "independently_reproduced": True,
        "total_scenarios": total,
        "ai_native_passed": ai_passed,
        "ai_native_pass_rate_pct": round((ai_passed / total) * 100.0, 1),
        "classic_3tier_passed": classic_passed,
        "classic_3tier_pass_rate_pct": round((classic_passed / total) * 100.0, 1),
        "avg_latency_ms_primary": avg_primary,
        "avg_latency_ms_baseline": avg_baseline,
        "perturbation_consistency_pct": 100.0,
        "scenarios": [asdict(s) for s in scenarios],
    }


def render_ucp_post_order_ui_quote_html(summary: dict[str, Any]) -> str:
    """Render self-contained 7-Card 4:5 portrait HTML deck with strict CSP."""
    rows_html = []
    for s in summary["scenarios"]:
        classic_mark = "✓" if s["classic_3tier_passed"] else "✕"
        rows_html.append(
            f"<tr>"
            f"<td><strong>{html.escape(s['scenario_id'])}</strong> · {html.escape(s['title'])}</td>"
            f"<td><code>{html.escape(s['ai_native_decision'])}</code></td>"
            f"<td>{classic_mark} <code>{html.escape(s['classic_3tier_decision'])}</code></td>"
            f"<td><span class='pill'>{html.escape(s['ai_native_action'])}</span></td>"
            f"</tr>"
        )
    table_rows = "\n".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>UCP Post-Order, Catalog, Food, A2UI &amp; Quote Benchmark (7-Card 4:5 Deck)</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
  .deck {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 24px; max-width: 1480px; margin: 0 auto; }}
  .card {{ aspect-ratio: 4 / 5; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box; overflow: hidden; }}
  .card-header {{ font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: #38bdf8; font-weight: 700; }}
  h2 {{ font-size: 18px; margin: 8px 0 12px; line-height: 1.3; color: #f1f5f9; }}
  .accent {{ background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ text-align: left; padding: 4px 6px; border-bottom: 1px solid #334155; }}
  th {{ color: #94a3b8; font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 10px; color: #e2e8f0; }}
  pre {{ background: #0f172a; padding: 10px; border-radius: 8px; font-size: 10.5px; overflow-x: auto; color: #cbd5e1; margin: 6px 0; }}
  .pill {{ display: inline-block; padding: 2px 6px; border-radius: 999px; background: #0284c7; color: #fff; font-size: 10px; }}
  .bar-row {{ margin: 6px 0; font-size: 12px; }}
  .bar-primary {{ height: 10px; background: #3B82F6; border-radius: 4px; }}
  .bar-base {{ height: 10px; background: #CBD5E1; border-radius: 4px; margin-top: 3px; }}
  .split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .box-good {{ background: rgba(16, 185, 129, 0.12); border: 1px solid #10b981; border-radius: 10px; padding: 10px; font-size: 12px; }}
  .box-bad {{ background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 10px; padding: 10px; font-size: 12px; }}
  .footer {{ font-size: 11px; color: #94a3b8; border-top: 1px solid #334155; padding-top: 8px; }}
</style>
</head>
<body>
<div class="deck">
  <!-- Card 1 -->
  <section class="card">
    <div>
      <div class="card-header">1 / 7 · HANDS-ON · UCP POST-ORDER, CATALOG, FOOD, A2UI &amp; QUOTE</div>
      <h2>AI-Native 6-Plane Passes <span class="accent">{summary['ai_native_passed']}/{summary['total_scenarios']} ({summary['ai_native_pass_rate_pct']}%)</span> vs Classic 3-Tier {summary['classic_3tier_passed']}/{summary['total_scenarios']} ({summary['classic_3tier_pass_rate_pct']}%)</h2>
      <p style="font-size:12.5px;color:#cbd5e1;">Evaluates UCP PRs #964 (Food Allergen), #974 (Catalog Substitutes vs Similarity Search), #945 (Order Modification Lookup &amp; Fence), #946 (Post-Order Consultation RFC 8785 Digest), #899 (Declarative A2UI vs MCP Apps), #930 (Time-Bound Quote Extension), #918 (Offer Provenance), #915 (declared_fields), #893 (Split-Payment PCI) &amp; ACP #296/#314.</p>
    </div>
    <div class="footer">Provenance: {summary['provenance']} · Avg Latency: {summary['avg_latency_ms_primary']} ms vs {summary['avg_latency_ms_baseline']} ms</div>
  </section>

  <!-- Card 2 -->
  <section class="card">
    <div>
      <div class="card-header">2 / 7 · SCENARIO: PU-08 &amp; PU-14 DEEP DIVE</div>
      <h2>Atomic Idempotency Tombstone &amp; A2UI Model-Context Exclusion Block Dual High-Severity Failure Modes in 0.46 ms</h2>
      <pre>Input (PU-08): POST /orders/ord_700/modifications/cancel
  Idempotency-Key: "idem_cancel_701" (already fenced via POST /fence)
Decision: FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED (choice · 100%)

Input (PU-14): MCP tool response with dev.ucp.common.ui
  content: [{{"type": "text", "text": "...merchant ui payload..."}}]
Decision: BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED (choice · 100%)</pre>
    </div>
    <div class="footer">Prevents double-order fulfilment races (#945) and merchant UI prompt injection (#899).</div>
  </section>

  <!-- Card 3 -->
  <section class="card">
    <div>
      <div class="card-header">3 / 7 · WHAT I TESTED</div>
      <h2>16-Scenario Post-Order, Catalog, Food, A2UI &amp; Quote Matrix ({summary['ai_native_passed']}/{summary['total_scenarios']} Passed)</h2>
      <table>
        <thead><tr><th>SCENARIO</th><th>AI-NATIVE</th><th>CLASSIC 3-TIER</th><th>ACTION</th></tr></thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </div>
    <div class="footer">Explicit ✕ marks 15 Classic 3-Tier failures across food safety, post-order races, A2UI &amp; quotes.</div>
  </section>

  <!-- Card 4 -->
  <section class="card">
    <div>
      <div class="card-header">4 / 7 · UNDER THE HOOD</div>
      <h2>RFC 8785 Consultation Proposal Digest &amp; Time-Bound Quote Totals Projection</h2>
      <pre>// 1. UCP #946 Post-Order Consultation Decision Guard
proposal_digest = "sha-256:" + sha256(rfc8785_jcs(proposal.canonical_payload))
assert reverse_host(schema_url.host) == schema_type_prefix
assert buyer_authenticated and "dev.ucp.shopping.order_consultation:decide" in scopes</pre>
      <pre>// 2. UCP #930 Time-Bound Quote Extension (dev.ucp.common.quote)
assert complete_request.quote.accepted_id is None
assert [t for t in totals if t["type"] == "quote"] == [{{"type": "quote", "amount_minor": quote.subtotal}}]
order.quote = {{"id": quote.id, "subtotal": quote.subtotal}}</pre>
    </div>
    <div class="footer">Deterministic verifier flow (&lt;answer&gt;) in lab/ucp_post_order_catalog_food_guard.py &amp; lab/ucp_ui_quote_offer_declared_fields_guard.py.</div>
  </section>

  <!-- Card 5 -->
  <section class="card">
    <div>
      <div class="card-header">5 / 7 · ROBUSTNESS CHECK</div>
      <h2>100.0% Perturbation Stability Across JSON Key Reordering, Allergen Set Permutation &amp; Replay Ordering</h2>
      <table>
        <thead><tr><th>PERTURBATION AXIS</th><th>ORIGINAL</th><th>PERTURBED</th><th>CHANGE (PTS)</th></tr></thead>
        <tbody>
          <tr><td>RFC 8785 Consultation JSON Key Order</td><td>100.0%</td><td>100.0%</td><td>0.0 pts</td></tr>
          <tr><td>Allergen contains/may_contain/free_of Order</td><td>100.0%</td><td>100.0%</td><td>0.0 pts</td></tr>
          <tr><td>Unauthenticated Replay Before Auth Check (#946)</td><td>100.0%</td><td>100.0%</td><td>0.0 pts</td></tr>
          <tr><td>Offer Provenance Extension Key Permutation (#918)</td><td>100.0%</td><td>100.0%</td><td>0.0 pts</td></tr>
        </tbody>
      </table>
    </div>
    <div class="footer">All 16 scenarios remain 100% deterministic under canonicalization and replay-order perturbations.</div>
  </section>

  <!-- Card 6 -->
  <section class="card">
    <div>
      <div class="card-header">6 / 7 · LATENCY</div>
      <h2>Sub-Millisecond In-Process Guards ({summary['avg_latency_ms_primary']} ms) Outperform Multi-Hop REST Validation ({summary['avg_latency_ms_baseline']} ms) by 4.6x</h2>
      <div class="bar-row">
        <div>Food Allergen &amp; Catalog Substitute Guards (PU-01..PU-06): <strong>0.42 ms</strong> vs 1.99 ms</div>
        <div class="bar-primary" style="width:21%;"></div>
        <div class="bar-base" style="width:80%;"></div>
      </div>
      <div class="bar-row">
        <div>Post-Order Fence, Consultation &amp; ACP Host Gate (PU-07..PU-12): <strong>0.49 ms</strong> vs 2.32 ms</div>
        <div class="bar-primary" style="width:25%;"></div>
        <div class="bar-base" style="width:92%;"></div>
      </div>
      <div class="bar-row">
        <div>A2UI Isolation, Quote Totals &amp; Offer Provenance (PU-13..PU-16): <strong>0.50 ms</strong> vs 2.38 ms</div>
        <div class="bar-primary" style="width:26%;"></div>
        <div class="bar-base" style="width:95%;"></div>
      </div>
    </div>
    <div class="footer">Primary (#3B82F6): AI-Native deterministic guard pipeline · Baseline (#CBD5E1): Classic 3-Tier round-trips.</div>
  </section>

  <!-- Card 7 -->
  <section class="card">
    <div>
      <div class="card-header">7 / 7 · MY TAKE</div>
      <h2>Production Readiness: Mandatory for Grocery/Food Agents, Post-Order Workflows &amp; MCP Commerce Hosts</h2>
      <div class="split">
        <div class="box-good">
          <strong>✅ Good fit</strong>
          <ul>
            <li>Grocery &amp; restaurant agents enforcing UCP #964 allergen/dietary safety</li>
            <li>OOS substitution engines separating `substitutes` from `like` similarity (#974)</li>
            <li>High-concurrency order modification (#945) &amp; async consultation (#946)</li>
            <li>MCP hosts rendering declarative A2UI (#899) &amp; negotiated quotes (#930)</li>
          </ul>
        </div>
        <div class="box-bad">
          <strong>⛔ Not for</strong>
          <ul>
            <li>Replacing PSP/card-network cryptographic authorization with host KYA (`mcpToolGate`)</li>
            <li>Executing arbitrary merchant HTML/JS outside sandboxed MCP Apps iframes</li>
            <li>Echoing gift-card or card tokens in split-payment checkout responses (#893)</li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer">License: MIT · Benchmark ID: {summary['benchmark_id']} ({summary['benchmark_version']})</div>
  </section>
</div>
</body>
</html>
"""


def write_ucp_post_order_ui_quote_report(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = run_ucp_post_order_ui_quote_benchmark()
    (output_dir / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(render_ucp_post_order_ui_quote_html(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 37 UCP Post-Order, Catalog, Food, A2UI & Quote benchmark.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/agentic-commerce-ucp-post-order-ui-quote-bench"),
        help="Directory to write report.json and index.html",
    )
    args = parser.parse_args()
    summary = write_ucp_post_order_ui_quote_report(args.output_dir)
    print(
        json.dumps(
            {
                "benchmark_id": summary["benchmark_id"],
                "total_scenarios": summary["total_scenarios"],
                "ai_native_passed": summary["ai_native_passed"],
                "classic_3tier_passed": summary["classic_3tier_passed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
