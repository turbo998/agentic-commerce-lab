"""Stage 36: UCP Declarative A2UI / MCP Apps Isolation (`#899`), Time-Bound Quote
Extension (`#930`), Offer Decision-Integrity Provenance Binding (`#918`), Reverse-DNS
`declared_fields` (`#915`), and Split-Payment Credential Echo Prohibition (`#893`).

Implements deterministic offline conformance guards for:
1. UCP PR #899 (`dev.ucp.common.ui`):
   - Declarative A2UI (`ui: {type, content}`) vs executable HTML (restricted to sandboxed
     MCP Apps `io.modelcontextprotocol/ui` or `continue_url`).
   - Model-context isolation: business-authored `ui` payloads MUST be omitted from MCP
     `content[]` text to prevent prompt injection into the LLM context.
   - UI action as request, never act: every UI interaction resolves to a negotiated UCP
     `operationId` and cannot bypass platform buyer-consent or signature checks; `create_cart`
     on a held cart merges via `update_cart`.
2. UCP PR #930 / EP #929 (`dev.ucp.common.quote`):
   - Immutable time-bound quotation across Cart -> Checkout -> Order.
   - Accepted quote (`accepted_id == quote.id`, omitted on `complete`) MUST appear in
     authoritative `totals[]` as exactly one entry of `type == "quote"` matching
     `quote.subtotal`, and project onto Order as `order.quote = {id, subtotal}`.
   - Polling stops at `expires_at`; expired or altered quotes fail closed (`quote_unavailable` /
     `quote_changed`).
3. UCP PR #918 (`offer-decision-integrity-notes`):
   - Blocks provenance under-binding where an Offer digest covers base SKU/price fields
     but omits commercial-provenance extension fields (`OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED`).
   - Blocks conflating Cart-stage `"applied"` offers with Checkout-stage `"committed"`
     allocations (`CART_APPLIED_CONFLATED_WITH_CHECKOUT_COMMITTED_BLOCKED`).
4. UCP PR #915 (`declared_fields` & `required_declared_fields`):
   - Validates Reverse-DNS schema keys in `checkout.config` and enforces order-scope vs
     line-item-scope `required_declared_fields` completeness.
5. UCP PR #893 (Split Payments Credential Flow & PCI Scope):
   - Enforces `Platform -> Business` one-way credential flow (`ucp_response: "omit"`),
     blocking any business response that echoes `credential` or `token` in split-payment
     instruments (`SPLIT_PAYMENT_CREDENTIAL_ECHO_LEAK_BLOCKED`).

Pure Python standard library; zero network calls; zero secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


REVERSE_DNS_KEY_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+){2,}$")


@dataclass(frozen=True)
class UCPUiExtensionGuardResult:
    admitted: bool
    decision_code: str
    resolved_operation: str
    omitted_from_mcp_model_context: bool
    platform_renders_disclosures: bool


@dataclass(frozen=True)
class UCPQuoteLifecycleGuardResult:
    quote_id: str
    admitted: bool
    decision_code: str
    authoritative_quote_total_minor: int
    order_projection: dict[str, Any] | None


@dataclass(frozen=True)
class UCPOfferDecisionIntegrityResult:
    offer_id: str
    admitted: bool
    decision_code: str
    full_provenance_digest: str
    checkout_committed_verified: bool


@dataclass(frozen=True)
class UCPDeclaredFieldsGuardResult:
    admitted: bool
    decision_code: str
    missing_or_invalid_keys: tuple[str, ...]


@dataclass(frozen=True)
class UCPSplitPaymentCredentialEchoResult:
    admitted: bool
    decision_code: str
    leaked_instrument_ids: tuple[str, ...]


def evaluate_ucp_ui_extension_a2ui_mcp_guard(
    *,
    ui_extension_negotiated: bool,
    ui_media_type: str,
    platform_supported_formats: tuple[str, ...],
    contains_executable_html_or_script: bool,
    transport_surface: str,  # "response_ui_field" | "mcp_apps_sandbox" | "embedded_continue_url"
    included_in_mcp_text_content_array: bool,
    requested_ui_action_operation_id: str,
    negotiated_capabilities: tuple[str, ...],
    has_existing_held_cart: bool,
    platform_enforces_buyer_consent_and_disclosures: bool,
) -> UCPUiExtensionGuardResult:
    """Enforce UCP PR #899 (`dev.ucp.common.ui`) A2UI / MCP Apps sandboxing and model-context exclusion."""
    if not ui_extension_negotiated:
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="UI_EXTENSION_NOT_NEGOTIATED",
            resolved_operation="none",
            omitted_from_mcp_model_context=not included_in_mcp_text_content_array,
            platform_renders_disclosures=platform_enforces_buyer_consent_and_disclosures,
        )

    if included_in_mcp_text_content_array:
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED",
            resolved_operation="none",
            omitted_from_mcp_model_context=False,
            platform_renders_disclosures=platform_enforces_buyer_consent_and_disclosures,
        )

    if contains_executable_html_or_script and transport_surface == "response_ui_field":
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="EXECUTABLE_HTML_IN_DECLARATIVE_UI_PAYLOAD_BLOCKED",
            resolved_operation="none",
            omitted_from_mcp_model_context=True,
            platform_renders_disclosures=platform_enforces_buyer_consent_and_disclosures,
        )

    if transport_surface == "response_ui_field" and ui_media_type not in platform_supported_formats:
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="UNSUPPORTED_A2UI_MEDIA_TYPE_FALLBACK_TO_NATIVE",
            resolved_operation="native_fallback",
            omitted_from_mcp_model_context=True,
            platform_renders_disclosures=platform_enforces_buyer_consent_and_disclosures,
        )

    if not platform_enforces_buyer_consent_and_disclosures:
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="UI_ACTION_BYPASSING_PLATFORM_CONSENT_OR_DISCLOSURES_BLOCKED",
            resolved_operation="none",
            omitted_from_mcp_model_context=True,
            platform_renders_disclosures=False,
        )

    op_to_capability = {
        "search_catalog": "dev.ucp.shopping.catalog",
        "lookup_catalog": "dev.ucp.shopping.catalog",
        "create_cart": "dev.ucp.shopping.cart",
        "update_cart": "dev.ucp.shopping.cart",
        "create_checkout": "dev.ucp.shopping.checkout",
        "update_checkout": "dev.ucp.shopping.checkout",
        "complete_checkout": "dev.ucp.shopping.checkout",
    }
    required_cap = op_to_capability.get(requested_ui_action_operation_id)
    if required_cap is None or required_cap not in negotiated_capabilities:
        return UCPUiExtensionGuardResult(
            admitted=False,
            decision_code="UI_ACTION_UNNEGOTIATED_CAPABILITY_BLOCKED",
            resolved_operation="continue_url_fallback",
            omitted_from_mcp_model_context=True,
            platform_renders_disclosures=True,
        )

    resolved_op = (
        "update_cart"
        if requested_ui_action_operation_id == "create_cart" and has_existing_held_cart
        else requested_ui_action_operation_id
    )
    return UCPUiExtensionGuardResult(
        admitted=True,
        decision_code="UCP_DECLARATIVE_UI_AND_ACTION_VERIFIED",
        resolved_operation=resolved_op,
        omitted_from_mcp_model_context=True,
        platform_renders_disclosures=True,
    )


def evaluate_ucp_quote_lifecycle_and_totals_guard(
    *,
    quote_id: str,
    quote_status: str,
    quote_subtotal_minor: int,
    quote_expires_at_epoch: int,
    now_epoch: int,
    buyer_accepted_id: str | None,
    is_complete_checkout_request: bool,
    accepted_id_present_on_complete_request: bool,
    totals_entries: tuple[dict[str, Any], ...],
    line_items_mutated_since_quote: bool = False,
) -> UCPQuoteLifecycleGuardResult:
    """Enforce UCP PR #930 (EP #929 `dev.ucp.common.quote`) immutability, expiry, and `totals` reflection."""
    if now_epoch >= quote_expires_at_epoch:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="quote_unavailable",
            authoritative_quote_total_minor=0,
            order_projection=None,
        )

    if line_items_mutated_since_quote:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="quote_changed",
            authoritative_quote_total_minor=0,
            order_projection=None,
        )

    if is_complete_checkout_request and accepted_id_present_on_complete_request:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="ACCEPTED_ID_MUST_BE_OMITTED_ON_COMPLETE",
            authoritative_quote_total_minor=0,
            order_projection=None,
        )

    if buyer_accepted_id != quote_id:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="QUOTE_ACCEPTANCE_ID_MISMATCH",
            authoritative_quote_total_minor=0,
            order_projection=None,
        )

    quote_totals = [t for t in totals_entries if t.get("type") == "quote"]
    if len(quote_totals) != 1 or int(quote_totals[0].get("amount", -1)) != quote_subtotal_minor:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="AUTHORITATIVE_TOTALS_QUOTE_ENTRY_MISMATCH",
            authoritative_quote_total_minor=0,
            order_projection=None,
        )

    known_ready_statuses = {"accepted", "issued", "ready"}
    if quote_status not in known_ready_statuses and is_complete_checkout_request:
        return UCPQuoteLifecycleGuardResult(
            quote_id=quote_id,
            admitted=False,
            decision_code="UNKNOWN_OR_PENDING_QUOTE_STATUS_FAIL_CLOSED",
            authoritative_quote_total_minor=quote_subtotal_minor,
            order_projection=None,
        )

    return UCPQuoteLifecycleGuardResult(
        quote_id=quote_id,
        admitted=True,
        decision_code="UCP_QUOTE_ACCEPTED_AND_PROJECTED_TO_ORDER",
        authoritative_quote_total_minor=quote_subtotal_minor,
        order_projection={"id": quote_id, "subtotal": quote_subtotal_minor},
    )


def evaluate_ucp_offer_decision_integrity_guard(
    *,
    offer_id: str,
    base_offer_fields: dict[str, Any],
    commercial_provenance_extensions: dict[str, Any],
    signed_digest_includes_provenance_extensions: bool,
    submitted_offer_digest: str,
    offer_stage_state: str,  # "cart_applied" | "checkout_committed"
    checkout_inventory_and_budget_locked: bool,
) -> UCPOfferDecisionIntegrityResult:
    """Enforce UCP PR #918 Offer decision-integrity (provenance binding & applied-vs-committed separation)."""
    combined_subject = {
        "offer_id": offer_id,
        "base": base_offer_fields,
        "provenance_extensions": commercial_provenance_extensions,
    }
    full_digest = "sha-256:" + hashlib.sha256(
        json.dumps(combined_subject, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    if commercial_provenance_extensions and (
        not signed_digest_includes_provenance_extensions or submitted_offer_digest != full_digest
    ):
        return UCPOfferDecisionIntegrityResult(
            offer_id=offer_id,
            admitted=False,
            decision_code="OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED",
            full_provenance_digest=full_digest,
            checkout_committed_verified=False,
        )

    if offer_stage_state != "checkout_committed" or not checkout_inventory_and_budget_locked:
        return UCPOfferDecisionIntegrityResult(
            offer_id=offer_id,
            admitted=False,
            decision_code="CART_APPLIED_CONFLATED_WITH_CHECKOUT_COMMITTED_BLOCKED",
            full_provenance_digest=full_digest,
            checkout_committed_verified=False,
        )

    return UCPOfferDecisionIntegrityResult(
        offer_id=offer_id,
        admitted=True,
        decision_code="OFFER_PROVENANCE_AND_COMMIT_INTEGRITY_VERIFIED",
        full_provenance_digest=full_digest,
        checkout_committed_verified=True,
    )


def evaluate_ucp_declared_fields_extensible_checkout(
    *,
    config_schemas: dict[str, dict[str, str]],
    checkout_required_declared_fields: tuple[str, ...],
    line_item_required_declared_fields: tuple[str, ...],
    checkout_declared_fields: dict[str, Any],
    line_item_declared_fields: dict[str, Any],
) -> UCPDeclaredFieldsGuardResult:
    """Enforce UCP PR #915 Reverse-DNS `declared_fields` and `required_declared_fields` scope binding."""
    invalid_keys: list[str] = []

    for key, spec in config_schemas.items():
        if not REVERSE_DNS_KEY_RE.match(key) or spec.get("scope") not in {"checkout", "line_item"}:
            invalid_keys.append(key)

    for req_key in checkout_required_declared_fields:
        schema_spec = config_schemas.get(req_key)
        if (
            not schema_spec
            or schema_spec.get("scope") != "checkout"
            or req_key not in checkout_declared_fields
            or checkout_declared_fields[req_key] in (None, "")
        ):
            invalid_keys.append(req_key)

    for req_key in line_item_required_declared_fields:
        schema_spec = config_schemas.get(req_key)
        if (
            not schema_spec
            or schema_spec.get("scope") != "line_item"
            or req_key not in line_item_declared_fields
            or line_item_declared_fields[req_key] in (None, "")
        ):
            invalid_keys.append(req_key)

    for provided_key in checkout_declared_fields:
        schema_spec = config_schemas.get(provided_key)
        if not schema_spec or schema_spec.get("scope") != "checkout":
            invalid_keys.append(provided_key)

    for provided_key in line_item_declared_fields:
        schema_spec = config_schemas.get(provided_key)
        if not schema_spec or schema_spec.get("scope") != "line_item":
            invalid_keys.append(provided_key)

    if invalid_keys:
        return UCPDeclaredFieldsGuardResult(
            admitted=False,
            decision_code="DECLARED_FIELDS_SCHEMA_OR_SCOPE_MISMATCH_BLOCKED",
            missing_or_invalid_keys=tuple(dict.fromkeys(invalid_keys)),
        )

    return UCPDeclaredFieldsGuardResult(
        admitted=True,
        decision_code="UCP_DECLARED_FIELDS_SCOPE_AND_SCHEMA_VERIFIED",
        missing_or_invalid_keys=(),
    )


def verify_ucp_split_payment_no_credential_echo(
    *,
    response_payment_instruments: tuple[dict[str, Any], ...],
) -> UCPSplitPaymentCredentialEchoResult:
    """Enforce UCP PR #893: Businesses MUST NOT echo `credential` or `token` in split-payment responses."""
    leaked_ids: list[str] = []
    for idx, inst in enumerate(response_payment_instruments):
        inst_id = str(inst.get("id", f"instrument_{idx}"))
        if "credential" in inst or "token" in inst:
            leaked_ids.append(inst_id)
            continue
        nested = inst.get("data") or {}
        if isinstance(nested, dict) and ("credential" in nested or "token" in nested):
            leaked_ids.append(inst_id)

    if leaked_ids:
        return UCPSplitPaymentCredentialEchoResult(
            admitted=False,
            decision_code="SPLIT_PAYMENT_CREDENTIAL_ECHO_LEAK_BLOCKED",
            leaked_instrument_ids=tuple(leaked_ids),
        )

    return UCPSplitPaymentCredentialEchoResult(
        admitted=True,
        decision_code="SPLIT_PAYMENT_RESPONSE_CREDENTIAL_OMITTED_CLEAN",
        leaked_instrument_ids=(),
    )
