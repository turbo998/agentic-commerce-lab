"""Stage 41: UCP Nested Bundle Line Items (#976), Cart-Only Checkout & Deferred Terms (#940/#908),
UCP-AP2 Credential Provider Mandate Tokenization (#916), Google AP2 ISO 4217 Minor-Unit Budget &
ISO 8601 Execution-Date Evaluators (#368/#377/#378) + Non-Fraud Dispute Resolver (#352), and
UCP Catalog Search Purpose (#902) / ACP Delegate Signature & Telemetry Guards (#238/#285/#287/#237).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import re
from typing import Any, Mapping, Sequence


ISO4217_ZERO_DECIMAL_CURRENCIES = frozenset({
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW",
    "PYG", "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
})
ISO4217_THREE_DECIMAL_CURRENCIES = frozenset({
    "BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND",
})
ISO4217_FOUR_DECIMAL_CURRENCIES = frozenset({"CLF", "UYW"})

REGISTERED_SCHEME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class UCPBundleCartDeferredVerdict:
    admitted: bool
    decision_code: str
    computed_checkout_subtotal_minor: int
    computed_checkout_items_discount_minor: int
    parent_line_ids: tuple[str, ...]
    ignored_echoed_component_ids: tuple[str, ...]


@dataclass(frozen=True)
class UCPAP2TokenizeMandateVerdict:
    admitted: bool
    decision_code: str
    issued_opaque_token: str | None
    error_code: str | None


@dataclass(frozen=True)
class AP2BudgetExecutionDisputeVerdict:
    admitted: bool
    decision_code: str
    budget_cap_minor: int
    overturned_amount_minor: int
    dispute_route: str


@dataclass(frozen=True)
class UCPCatalogPurposeACPDelegateVerdict:
    admitted: bool
    decision_code: str
    filtered_result_ids: tuple[str, ...]
    resolved_target_uri: str


def evaluate_ucp_bundle_cart_and_deferred_terms_guard(
    *,
    line_items: Sequence[Mapping[str, Any]],
    reported_checkout_subtotal_minor: int,
    reported_checkout_items_discount_minor: int,
    is_update_request: bool,
    business_rejected_echoed_components: bool,
    cart_id_in_response: bool = False,
    is_deferred_payment_complete: bool = False,
    complete_payment_object: Mapping[str, Any] | None = None,
    complete_includes_selected_term_id: bool = False,
) -> UCPBundleCartDeferredVerdict:
    """Enforce UCP PR #976 (nested bundle line items), PR #940 (input-only cart_id),
    and PR #908 (empty payment: {} on complete for fully deferred payment terms).
    """
    if cart_id_in_response:
        return UCPBundleCartDeferredVerdict(
            admitted=False,
            decision_code="INPUT_ONLY_CART_ID_ECHOED_IN_RESPONSE_BLOCKED",
            computed_checkout_subtotal_minor=0,
            computed_checkout_items_discount_minor=0,
            parent_line_ids=(),
            ignored_echoed_component_ids=(),
        )

    if is_deferred_payment_complete:
        if complete_includes_selected_term_id or complete_payment_object != {}:
            return UCPBundleCartDeferredVerdict(
                admitted=False,
                decision_code="DEFERRED_TERMS_COMPLETE_PAYMENT_SHAPE_INVALID",
                computed_checkout_subtotal_minor=0,
                computed_checkout_items_discount_minor=0,
                parent_line_ids=(),
                ignored_echoed_component_ids=(),
            )

    if is_update_request and business_rejected_echoed_components:
        return UCPBundleCartDeferredVerdict(
            admitted=False,
            decision_code="BUSINESS_REJECTED_ECHOED_BUNDLE_COMPONENTS_FORBIDDEN",
            computed_checkout_subtotal_minor=0,
            computed_checkout_items_discount_minor=0,
            parent_line_ids=(),
            ignored_echoed_component_ids=(),
        )

    by_id: dict[str, Mapping[str, Any]] = {}
    for li in line_items:
        li_id = str(li.get("id", "")).strip()
        if not li_id or li_id in by_id:
            return UCPBundleCartDeferredVerdict(
                admitted=False,
                decision_code="LINE_ITEM_ID_MISSING_OR_DUPLICATE",
                computed_checkout_subtotal_minor=0,
                computed_checkout_items_discount_minor=0,
                parent_line_ids=(),
                ignored_echoed_component_ids=(),
            )
        by_id[li_id] = li

    parent_ids: list[str] = []
    component_ids: list[str] = []
    components_by_parent: dict[str, list[Mapping[str, Any]]] = {}

    for li_id, li in by_id.items():
        parent_id = li.get("parent_id")
        if parent_id is None:
            parent_ids.append(li_id)
        else:
            parent_id_str = str(parent_id).strip()
            if parent_id_str == li_id or parent_id_str not in by_id:
                return UCPBundleCartDeferredVerdict(
                    admitted=False,
                    decision_code="BUNDLE_MULTI_LEVEL_OR_ORPHAN_NESTING_BLOCKED",
                    computed_checkout_subtotal_minor=0,
                    computed_checkout_items_discount_minor=0,
                    parent_line_ids=(),
                    ignored_echoed_component_ids=(),
                )
            # Single-level nesting rule: parent itself MUST NOT carry parent_id
            if by_id[parent_id_str].get("parent_id") is not None:
                return UCPBundleCartDeferredVerdict(
                    admitted=False,
                    decision_code="BUNDLE_MULTI_LEVEL_OR_ORPHAN_NESTING_BLOCKED",
                    computed_checkout_subtotal_minor=0,
                    computed_checkout_items_discount_minor=0,
                    parent_line_ids=(),
                    ignored_echoed_component_ids=(),
                )
            component_ids.append(li_id)
            components_by_parent.setdefault(parent_id_str, []).append(li)

    # Check bundle invariant: sum(component.totals[type=total]) == parent.totals[type=subtotal]
    for parent_id_str, comps in components_by_parent.items():
        parent_li = by_id[parent_id_str]
        parent_subtotal = int(parent_li.get("subtotal_minor", 0))
        comp_total_sum = sum(int(c.get("total_minor", 0)) for c in comps)
        if comp_total_sum != parent_subtotal:
            return UCPBundleCartDeferredVerdict(
                admitted=False,
                decision_code="BUNDLE_COMPONENT_TOTALS_MISMATCH_PARENT_SUBTOTAL",
                computed_checkout_subtotal_minor=0,
                computed_checkout_items_discount_minor=0,
                parent_line_ids=tuple(parent_ids),
                ignored_echoed_component_ids=tuple(component_ids),
            )

    # Aggregate over lines without parent_id only
    computed_subtotal = sum(int(by_id[pid].get("subtotal_minor", 0)) for pid in parent_ids)
    computed_items_discount = sum(int(by_id[pid].get("items_discount_minor", 0)) for pid in parent_ids)

    if (
        reported_checkout_subtotal_minor != computed_subtotal
        or reported_checkout_items_discount_minor != computed_items_discount
    ):
        return UCPBundleCartDeferredVerdict(
            admitted=False,
            decision_code="BUNDLE_COMPONENTS_DOUBLE_COUNTED_IN_CHECKOUT_TOTALS_BLOCKED",
            computed_checkout_subtotal_minor=computed_subtotal,
            computed_checkout_items_discount_minor=computed_items_discount,
            parent_line_ids=tuple(parent_ids),
            ignored_echoed_component_ids=tuple(component_ids),
        )

    return UCPBundleCartDeferredVerdict(
        admitted=True,
        decision_code="UCP_BUNDLE_LINE_ITEMS_AND_CART_CHECKOUT_VERIFIED",
        computed_checkout_subtotal_minor=computed_subtotal,
        computed_checkout_items_discount_minor=computed_items_discount,
        parent_line_ids=tuple(parent_ids),
        ignored_echoed_component_ids=tuple(component_ids),
    )


def evaluate_ucp_ap2_credential_provider_tokenization_guard(
    *,
    ap2_negotiated: bool,
    credential_type: str,
    payment_mandate_present: bool,
    payment_mandate_signature_valid: bool,
    payment_mandate_expired: bool,
    payment_mandate_transaction_id: str,
    checkout_jwt_hash: str,
    binding_checkout_id: str,
    target_checkout_id: str,
    complete_instrument_has_mandate_derived_token: bool,
    mandate_embedded_directly_as_reversible_token: bool,
) -> UCPAP2TokenizeMandateVerdict:
    """Enforce UCP PR #916 Step 3 Payment Mandate Verification & Token Issuance at Credential Provider."""
    if mandate_embedded_directly_as_reversible_token:
        return UCPAP2TokenizeMandateVerdict(
            admitted=False,
            decision_code="REVERSIBLE_COMPOSITE_MANDATE_TOKEN_CONFLATION_BLOCKED",
            issued_opaque_token=None,
            error_code="invalid_token_entropy",
        )

    if ap2_negotiated and not complete_instrument_has_mandate_derived_token:
        return UCPAP2TokenizeMandateVerdict(
            admitted=False,
            decision_code="AP2_NEGOTIATED_WITHOUT_MANDATE_DERIVED_TOKEN_BLOCKED",
            issued_opaque_token=None,
            error_code="payment_mandate_required",
        )

    if credential_type != "ap2_payment_mandate" or not payment_mandate_present:
        return UCPAP2TokenizeMandateVerdict(
            admitted=False,
            decision_code="UNSUPPORTED_OR_MISSING_AP2_SOURCE_CREDENTIAL",
            issued_opaque_token=None,
            error_code="unsupported_credential_type",
        )

    if not payment_mandate_signature_valid or payment_mandate_expired:
        return UCPAP2TokenizeMandateVerdict(
            admitted=False,
            decision_code="AP2_MANDATE_EXPIRED_OR_INVALID_SIGNATURE_AT_TOKENIZE",
            issued_opaque_token=None,
            error_code="invalid_payment_mandate",
        )

    if (
        not payment_mandate_transaction_id
        or payment_mandate_transaction_id != checkout_jwt_hash
        or binding_checkout_id != target_checkout_id
    ):
        return UCPAP2TokenizeMandateVerdict(
            admitted=False,
            decision_code="AP2_MANDATE_CHECKOUT_JWT_CORRELATION_MISMATCH_AT_TOKENIZE",
            issued_opaque_token=None,
            error_code="checkout_correlation_failed",
        )

    return UCPAP2TokenizeMandateVerdict(
        admitted=True,
        decision_code="UCP_AP2_CREDENTIAL_PROVIDER_TOKEN_ISSUED",
        issued_opaque_token=f"tok_ucp_ap2_{binding_checkout_id}",
        error_code=None,
    )


def iso4217_minor_unit_exponent(currency: str) -> int:
    code = currency.strip().upper()
    if code in ISO4217_ZERO_DECIMAL_CURRENCIES:
        return 0
    if code in ISO4217_THREE_DECIMAL_CURRENCIES:
        return 3
    if code in ISO4217_FOUR_DECIMAL_CURRENCIES:
        return 4
    return 2


def major_to_minor_units_floor(max_major: float | str | Decimal, currency: str) -> int:
    exp = iso4217_minor_unit_exponent(currency)
    scaled = Decimal(str(max_major)) * (Decimal(10) ** exp)
    return int(scaled.to_integral_value(rounding=ROUND_FLOOR))


def _parse_iso8601_bound(val: str) -> date | datetime:
    text = val.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return date.fromisoformat(text)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _within_iso8601_window(execution_date_str: str, not_before_str: str, not_after_str: str) -> bool:
    try:
        exec_val = _parse_iso8601_bound(execution_date_str)
        nb_val = _parse_iso8601_bound(not_before_str)
        na_val = _parse_iso8601_bound(not_after_str)
    except (ValueError, TypeError):
        return False

    # Compare against not_before
    if isinstance(exec_val, datetime) and isinstance(nb_val, datetime):
        if exec_val < nb_val:
            return False
    else:
        exec_d = exec_val.date() if isinstance(exec_val, datetime) else exec_val
        nb_d = nb_val.date() if isinstance(nb_val, datetime) else nb_val
        if exec_d < nb_d:
            return False

    # Compare against not_after
    if isinstance(exec_val, datetime) and isinstance(na_val, datetime):
        if exec_val > na_val:
            return False
    else:
        exec_d = exec_val.date() if isinstance(exec_val, datetime) else exec_val
        na_d = na_val.date() if isinstance(na_val, datetime) else na_val
        if exec_d > na_d:
            return False

    return True


def evaluate_ap2_iso4217_budget_execution_and_dispute_guard(
    *,
    budget_max_major: float | str,
    currency: str,
    spend_amount_minor: int,
    execution_date_str: str,
    not_before_str: str,
    not_after_str: str,
    checkout_mandate_hash: str,
    payment_mandate_transaction_id: str,
    receipt_reference: str,
    ordered_units: int,
    fulfilled_units: int,
    unit_price_minor: int,
    delivery_deadline_passed: bool,
) -> AP2BudgetExecutionDisputeVerdict:
    """Enforce Google AP2 PRs #368/#377 (ISO 4217 minor-unit budget cap),
    PR #378 (ISO 8601 chronological execution_date bounds), and PR #352 (post-transaction dispute resolver).
    """
    try:
        cap_minor = major_to_minor_units_floor(budget_max_major, currency)
    except (InvalidOperation, ValueError):
        return AP2BudgetExecutionDisputeVerdict(
            admitted=False,
            decision_code="AP2_BUDGET_INVALID_DECIMAL_FORMAT",
            budget_cap_minor=0,
            overturned_amount_minor=0,
            dispute_route="rejected",
        )

    if spend_amount_minor > cap_minor:
        return AP2BudgetExecutionDisputeVerdict(
            admitted=False,
            decision_code="AP2_BUDGET_ISO4217_MINOR_UNIT_CAP_EXCEEDED",
            budget_cap_minor=cap_minor,
            overturned_amount_minor=0,
            dispute_route="rejected",
        )

    if not _within_iso8601_window(execution_date_str, not_before_str, not_after_str):
        return AP2BudgetExecutionDisputeVerdict(
            admitted=False,
            decision_code="AP2_EXECUTION_DATE_OUTSIDE_ISO8601_WINDOW_BLOCKED",
            budget_cap_minor=cap_minor,
            overturned_amount_minor=0,
            dispute_route="rejected",
        )

    # AP2 PR #352 authorization chain check
    if (
        payment_mandate_transaction_id != checkout_mandate_hash
        or receipt_reference != checkout_mandate_hash
    ):
        return AP2BudgetExecutionDisputeVerdict(
            admitted=False,
            decision_code="AP2_DISPUTE_AUTH_CHAIN_BROKEN_ROUTED_TO_FRAUD",
            budget_cap_minor=cap_minor,
            overturned_amount_minor=0,
            dispute_route="network_fraud_process",
        )

    overturned_minor = 0
    if delivery_deadline_passed and fulfilled_units < ordered_units:
        overturned_minor = (ordered_units - fulfilled_units) * unit_price_minor

    return AP2BudgetExecutionDisputeVerdict(
        admitted=True,
        decision_code="AP2_ISO4217_BUDGET_ISO8601_WINDOW_AND_DISPUTE_VERIFIED",
        budget_cap_minor=cap_minor,
        overturned_amount_minor=overturned_minor,
        dispute_route="non_fraud_performance_resolved" if overturned_minor > 0 else "fulfilled_in_full",
    )


def evaluate_ucp_catalog_purpose_and_acp_delegate_telemetry_guard(
    *,
    search_purpose: str | None,
    reference_ids: Sequence[str] | None,
    has_query_or_filters: bool,
    candidate_results: Sequence[Mapping[str, str]],
    acp_endpoint: str,
    signature_header_present: bool,
    timestamp_header_present: bool,
    complete_checkout_uses_legacy_risk_signals_for_telemetry: bool,
    merchant_registered_scheme: str,
    product_url: str,
    app_links: Sequence[Mapping[str, str]],
    client_platform: str = "chatgpt",
) -> UCPCatalogPurposeACPDelegateVerdict:
    """Enforce UCP PR #902 (catalog.search purpose & reference_ids self-exclusion) and
    ACP PRs #238 (session_context separation), #285/#287 (required Signature/Timestamp), and #237 (app_links).
    """
    effective_purpose = "search" if search_purpose is None else search_purpose.strip()
    if effective_purpose not in {"search", "recommendation", "swap"}:
        return UCPCatalogPurposeACPDelegateVerdict(
            admitted=False,
            decision_code="UNSUPPORTED_SEARCH_PURPOSE_FALLBACK_BROWSE_BLOCKED",
            filtered_result_ids=(),
            resolved_target_uri=product_url,
        )

    refs = tuple(str(r).strip() for r in (reference_ids or ()) if str(r).strip())
    if effective_purpose == "search":
        if refs or not has_query_or_filters:
            return UCPCatalogPurposeACPDelegateVerdict(
                admitted=False,
                decision_code="CATALOG_SEARCH_PURPOSE_REFERENCE_IDS_PAIRING_INVALID",
                filtered_result_ids=(),
                resolved_target_uri=product_url,
            )
    elif effective_purpose == "swap":
        if not refs:
            return UCPCatalogPurposeACPDelegateVerdict(
                admitted=False,
                decision_code="CATALOG_SEARCH_PURPOSE_REFERENCE_IDS_PAIRING_INVALID",
                filtered_result_ids=(),
                resolved_target_uri=product_url,
            )

    # Self-exclusion check (UCP #902)
    ref_set = set(refs)
    referenced_parent_products = {
        str(item.get("product_id", ""))
        for item in candidate_results
        if str(item.get("variant_id", "")) in ref_set or str(item.get("product_id", "")) in ref_set
    }
    returned_ids: list[str] = []
    for item in candidate_results:
        pid = str(item.get("product_id", ""))
        vid = str(item.get("variant_id", ""))
        if item.get("included_in_response", "true") == "true":
            if pid in ref_set or vid in ref_set:
                return UCPCatalogPurposeACPDelegateVerdict(
                    admitted=False,
                    decision_code="CATALOG_SEARCH_ANCHOR_SELF_EXCLUSION_VIOLATED",
                    filtered_result_ids=(),
                    resolved_target_uri=product_url,
                )
            if effective_purpose == "recommendation" and pid in referenced_parent_products:
                return UCPCatalogPurposeACPDelegateVerdict(
                    admitted=False,
                    decision_code="CATALOG_SEARCH_ANCHOR_SELF_EXCLUSION_VIOLATED",
                    filtered_result_ids=(),
                    resolved_target_uri=product_url,
                )
            returned_ids.append(vid or pid)

    # ACP PR #285 & #287: Signature & Timestamp required on delegate_payment; Signature required on delegate_authentication
    if acp_endpoint == "delegate_payment":
        if not signature_header_present or not timestamp_header_present:
            return UCPCatalogPurposeACPDelegateVerdict(
                admitted=False,
                decision_code="ACP_DELEGATE_ENDPOINT_UNSIGNED_REQUEST_BLOCKED",
                filtered_result_ids=tuple(returned_ids),
                resolved_target_uri=product_url,
            )
    elif acp_endpoint == "delegate_authentication":
        if not signature_header_present:
            return UCPCatalogPurposeACPDelegateVerdict(
                admitted=False,
                decision_code="ACP_DELEGATE_ENDPOINT_UNSIGNED_REQUEST_BLOCKED",
                filtered_result_ids=tuple(returned_ids),
                resolved_target_uri=product_url,
            )

    # ACP PR #238: complete_checkout telemetry must use session_context in unreleased spec, not overloaded risk_signals
    if complete_checkout_uses_legacy_risk_signals_for_telemetry:
        return UCPCatalogPurposeACPDelegateVerdict(
            admitted=False,
            decision_code="ACP_TELEMETRY_RISK_SIGNALS_NAME_COLLISION_BLOCKED",
            filtered_result_ids=tuple(returned_ids),
            resolved_target_uri=product_url,
        )

    # ACP PR #237: app_links resolution & scheme squatting guard
    resolved_uri = product_url
    for link in app_links:
        if link.get("platform") == client_platform:
            uri = str(link.get("uri", "")).strip()
            scheme = uri.split("://", 1)[0] if "://" in uri else ""
            if not REGISTERED_SCHEME_RE.match(scheme) or scheme != merchant_registered_scheme:
                return UCPCatalogPurposeACPDelegateVerdict(
                    admitted=False,
                    decision_code="ACP_APP_LINK_UNREGISTERED_SCHEME_SQUATTING_BLOCKED",
                    filtered_result_ids=tuple(returned_ids),
                    resolved_target_uri=product_url,
                )
            resolved_uri = uri
            break

    return UCPCatalogPurposeACPDelegateVerdict(
        admitted=True,
        decision_code="UCP_CATALOG_PURPOSE_AND_ACP_DELEGATE_TELEMETRY_VERIFIED",
        filtered_result_ids=tuple(returned_ids),
        resolved_target_uri=resolved_uri,
    )
