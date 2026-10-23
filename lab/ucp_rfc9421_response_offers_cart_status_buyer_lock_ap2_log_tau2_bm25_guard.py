"""Stage 202 deterministic guard module:
UCP RFC 9421 §2.4 REST Response-to-Request Binding (#698), Catalog Variant Per-Seller
Offers (#810), Complete-Checkout Buyer Identity Lock (#769), Payment Instrument Payer
Taxpayer ID (#742), Cart Terminal Status (#739), State-Bound Merchant Cart Offer (#738),
Platform-Funded Discount Reimbursement (#727), Lower-Funnel Item Snapshot & 6 Fraud
Signals (#751/#750/#797), AP2 Selective-Disclosure Log Redaction (#321), x402 Go
verifyEIP3009 3-Tuple & @x402/next 402 Body (#3875/#3887/#3823/#3801), and Sierra
tau2-bench BM25 Title Indexing (#545), Airline Task 7 Scope (#495), pass^k Infra-Error
Inflation (#493/#497), Persona/Solo/Speech-Tool Stability (#492/#487/#470), and
Cash-Back Dispute Read Completeness (#439/#463).
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    action: str
    reason_code: str
    detail: str
    evidence: Mapping[str, Any]


# ---------------------------------------------------------------------------
# 1. UCP #698: RFC 9421 §2.4 REST Response-to-Request Signature Binding
# ---------------------------------------------------------------------------

def verify_ucp_rfc9421_rest_response_binding(
    *,
    sent_request: Mapping[str, Any],
    received_response: Mapping[str, Any],
    signature_input_components: Sequence[str],
    signature_created: int | None,
    current_timestamp: int,
    provided_signature_hex: str,
    shared_verification_secret: str,
    freshness_window_seconds: int = 300,
    max_future_skew_seconds: int = 30,
    reconstruct_from_response_echo: bool = False,
) -> GuardDecision:
    """Verify RFC 9421 §2.4 `;req` response-to-request binding and `created` freshness (#698)."""
    if reconstruct_from_response_echo:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_RFC9421_RESPONSE_REQUEST_BINDING_MISMATCH_BLOCKED",
            detail="Verifier attempted to reconstruct ;req components from response-echoed fields (self-certifying).",
            evidence={"reconstruct_from_response_echo": True},
        )

    required_components = ["@status", "@authority;req", "@method;req", "@path;req"]
    req_query = str(sent_request.get("query", "") or "")
    req_body = str(sent_request.get("body", "") or "")
    resp_body = str(received_response.get("body", "") or "")

    if req_query:
        required_components.append("@query;req")
    if req_body:
        required_components.append("content-digest;req")
    if resp_body:
        required_components.extend(["content-digest", "content-type"])

    comp_set = set(signature_input_components)
    missing = [c for c in required_components if c not in comp_set]
    if missing:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_RFC9421_RESPONSE_COVERAGE_INSUFFICIENT_BLOCKED",
            detail=f"Response Signature-Input missing required RFC 9421 §2.4 components: {missing}",
            evidence={"missing_components": missing},
        )

    if signature_created is None:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_RFC9421_RESPONSE_EXPIRED_OR_REPLAY_BLOCKED",
            detail="Response Signature-Input omits required created timestamp parameter.",
            evidence={"signature_created": None},
        )

    age = current_timestamp - int(signature_created)
    if age > freshness_window_seconds or age < -max_future_skew_seconds:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_RFC9421_RESPONSE_EXPIRED_OR_REPLAY_BLOCKED",
            detail=f"Response signature age {age}s outside freshness window [-{max_future_skew_seconds}, {freshness_window_seconds}].",
            evidence={"age_seconds": age, "freshness_window_seconds": freshness_window_seconds},
        )

    # Reconstruct signature base strictly from verifier's own sent_request + received_response
    req_digest = hashlib.sha256(req_body.encode("utf-8")).hexdigest() if req_body else ""
    resp_digest = hashlib.sha256(resp_body.encode("utf-8")).hexdigest() if resp_body else ""
    canonical_base = "|".join(
        [
            f"@status:{received_response.get('status', 200)}",
            f"@authority;req:{sent_request.get('authority', '')}",
            f"@method;req:{sent_request.get('method', '')}",
            f"@path;req:{sent_request.get('path', '')}",
            f"@query;req:{req_query}",
            f"content-digest;req:{req_digest}",
            f"content-digest:{resp_digest}",
            f"content-type:{received_response.get('content_type', '')}",
            f"created:{signature_created}",
        ]
    )
    expected_sig = hmac.new(
        shared_verification_secret.encode("utf-8"),
        canonical_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, str(provided_signature_hex or "")):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_RFC9421_RESPONSE_REQUEST_BINDING_MISMATCH_BLOCKED",
            detail="Response signature failed RFC 9421 §2.4 verification against sent request parameters.",
            evidence={
                "sent_path": sent_request.get("path"),
                "sent_authority": sent_request.get("authority"),
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_RFC9421_RESPONSE_BINDING_VERIFIED",
        detail="REST response signature is freshly bound to the exact sent request via RFC 9421 §2.4 ;req components.",
        evidence={"age_seconds": age, "covered_components": list(signature_input_components)},
    )


# ---------------------------------------------------------------------------
# 2. UCP #810: Catalog Variant Per-Seller offers[] MoR Routing & Price Gate
# ---------------------------------------------------------------------------

_BARE_HOST_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def validate_ucp_variant_per_seller_offer_routing(
    *,
    variant: Mapping[str, Any],
    selected_offer_index: int | None,
    checkout_target_domain: str,
    checkout_item_id: str,
    checkout_unit_price_minor: int,
    verified_well_known_domains: Sequence[str],
) -> GuardDecision:
    """Validate per-seller offers[] MoR routing, item_id substitution, and offer price authority (#810)."""
    offers = variant.get("offers")
    if offers is None:
        # Legacy single-merchant variant path
        if checkout_item_id != variant.get("id") or checkout_unit_price_minor != variant.get("price"):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
                detail="Single-seller variant checkout must use variant.id and variant.price.",
                evidence={"checkout_item_id": checkout_item_id, "variant_id": variant.get("id")},
            )
        return GuardDecision(
            allowed=True,
            action="Act automatically",
            reason_code="UCP_SINGLE_SELLER_VARIANT_ROUTING_OK",
            detail="Variant without offers[] routed via standard single-seller rules.",
            evidence={"checkout_item_id": checkout_item_id},
        )

    if not isinstance(offers, list) or len(offers) == 0 or selected_offer_index is None:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail="Variant with offers[] requires a valid non-empty offers list and explicit offer selection.",
            evidence={"selected_offer_index": selected_offer_index},
        )

    if selected_offer_index < 0 or selected_offer_index >= len(offers):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail="Selected offer index out of range.",
            evidence={"selected_offer_index": selected_offer_index, "offers_count": len(offers)},
        )

    offer = offers[selected_offer_index]
    seller = offer.get("seller") if isinstance(offer, Mapping) else None
    seller_domain = seller.get("domain", "") if isinstance(seller, Mapping) else ""
    offer_item_id = offer.get("item_id", "") if isinstance(offer, Mapping) else ""
    offer_price = offer.get("price") if isinstance(offer, Mapping) else None

    if not _BARE_HOST_RE.match(str(seller_domain)) or seller_domain not in set(verified_well_known_domains):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail=f"Offer seller.domain {seller_domain!r} is not a bare host verified via /.well-known/ucp.",
            evidence={"seller_domain": seller_domain},
        )

    if checkout_target_domain != seller_domain:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail=f"Checkout routed to {checkout_target_domain!r} instead of MoR {seller_domain!r}.",
            evidence={"checkout_target_domain": checkout_target_domain, "expected_domain": seller_domain},
        )

    if checkout_item_id == variant.get("id") or checkout_item_id != offer_item_id:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail="Platform MUST use offers[].item_id and MUST NOT use aggregator variant.id when offers[] is present.",
            evidence={
                "checkout_item_id": checkout_item_id,
                "offer_item_id": offer_item_id,
                "aggregator_variant_id": variant.get("id"),
            },
        )

    if checkout_unit_price_minor != offer_price:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED",
            detail="Platform MUST honor offers[].price over aggregator variant.price.",
            evidence={"checkout_unit_price_minor": checkout_unit_price_minor, "offer_price": offer_price},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_VARIANT_OFFER_MOR_ROUTING_VERIFIED",
        detail="Catalog variant offer routed to verified MoR domain with seller item_id and offer price.",
        evidence={"seller_domain": seller_domain, "item_id": offer_item_id, "price": offer_price},
    )


# ---------------------------------------------------------------------------
# 3. UCP #769: Lock Buyer Identity Fields on complete_checkout
# ---------------------------------------------------------------------------

_LOCKED_BUYER_IDENTITY_FIELDS = frozenset({"first_name", "last_name", "email", "phone_number"})


def validate_ucp_complete_checkout_buyer_lock(
    *,
    operation: str,
    buyer_consent_negotiated: bool,
    request_buyer_payload: Mapping[str, Any] | None,
) -> GuardDecision:
    """Enforce shared types/buyer.json lock on complete_checkout even when buyer_consent reopens buyer (#769)."""
    if operation != "complete_checkout" or request_buyer_payload is None:
        return GuardDecision(
            allowed=True,
            action="Act automatically",
            reason_code="UCP_BUYER_PAYLOAD_ALLOWED",
            detail="Non-complete operation or absent buyer payload.",
            evidence={"operation": operation},
        )

    if not buyer_consent_negotiated and request_buyer_payload:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_COMPLETE_CHECKOUT_BUYER_IDENTITY_MUTATION_BLOCKED",
            detail="Core complete_checkout omits buyer entirely when buyer_consent is not negotiated.",
            evidence={"keys": sorted(request_buyer_payload.keys())},
        )

    illegal_keys = [k for k in request_buyer_payload.keys() if k != "consent"]
    locked_present = [k for k in illegal_keys if k in _LOCKED_BUYER_IDENTITY_FIELDS]
    if illegal_keys:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_COMPLETE_CHECKOUT_BUYER_IDENTITY_MUTATION_BLOCKED",
            detail=f"complete_checkout buyer payload contains locked/disallowed fields: {illegal_keys}",
            evidence={"illegal_keys": illegal_keys, "locked_identity_fields": locked_present},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_COMPLETE_CHECKOUT_BUYER_CONSENT_ONLY_VERIFIED",
        detail="complete_checkout buyer object carries only buyer.consent; PII fields remain locked.",
        evidence={"allowed_keys": list(request_buyer_payload.keys())},
    )


# ---------------------------------------------------------------------------
# 4. UCP #742: Payment Instrument Core payer.identification & Split Payments
# ---------------------------------------------------------------------------

_TAX_DOC_RULS: Mapping[str, re.Pattern[str]] = {
    "CPF": re.compile(r"^\d{11}$"),
    "CNPJ": re.compile(r"^\d{14}$"),
    "CUIT": re.compile(r"^\d{11}$"),
    "RUT": re.compile(r"^\d{7,9}[0-9K]$"),
}


def validate_ucp_instrument_payer_identification(
    *,
    instruments: Sequence[Mapping[str, Any]],
    jurisdiction_requires_payer_doc: bool = True,
) -> GuardDecision:
    """Validate core payment_instrument.payer.identification ({type, number}) across instruments (#742)."""
    if not instruments:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_INVALID_BLOCKED",
            detail="At least one payment instrument is required.",
            evidence={"instrument_count": 0},
        )

    seen_payers: list[str] = []
    for idx, inst in enumerate(instruments):
        # Reject vendor-namespaced smuggling (e.g. com.mercadopago.payer)
        for k in inst.keys():
            if k.startswith("com.") or k.startswith("vendor_") or k == "vendor_payer":
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_INVALID_BLOCKED",
                    detail=f"Instrument[{idx}] smuggles payer identity inside vendor extension {k!r}.",
                    evidence={"instrument_index": idx, "vendor_key": k},
                )

        payer = inst.get("payer")
        inst_type = str(inst.get("type", ""))
        needs_doc = jurisdiction_requires_payer_doc or inst_type in {"pix", "boleto"}
        if not isinstance(payer, Mapping):
            if needs_doc:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_INVALID_BLOCKED",
                    detail=f"Instrument[{idx}] ({inst_type}) missing required core payer.identification.",
                    evidence={"instrument_index": idx, "type": inst_type},
                )
            continue

        ident = payer.get("identification")
        if not isinstance(ident, Mapping):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_INVALID_BLOCKED",
                detail=f"Instrument[{idx}].payer missing identification object.",
                evidence={"instrument_index": idx},
            )

        doc_type = str(ident.get("type", "")).upper()
        doc_number = str(ident.get("number", "")).strip()
        pattern = _TAX_DOC_RULS.get(doc_type)
        if pattern is None or not pattern.match(doc_number):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_INVALID_BLOCKED",
                detail=f"Instrument[{idx}] payer.identification ({doc_type}) failed format validation.",
                evidence={"instrument_index": idx, "doc_type": doc_type},
            )
        seen_payers.append(f"{doc_type}:{doc_number[:3]}***")

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_INSTRUMENT_PAYER_IDENTIFICATION_VERIFIED",
        detail="All payment instruments carry valid core payer.identification objects.",
        evidence={"instrument_count": len(instruments), "masked_payers": seen_payers},
    )


# ---------------------------------------------------------------------------
# 5. UCP #739: Cart Terminal Status (active | ordered | canceled | expired)
# ---------------------------------------------------------------------------

_VALID_CART_STATUSES = frozenset({"active", "ordered", "canceled", "expired"})
_TERMINAL_CART_STATUSES = frozenset({"ordered", "canceled", "expired"})


def evaluate_ucp_cart_terminal_status_guard(
    *,
    cart_status: str,
    request_sets_status: bool = False,
    attempted_action: str = "inspect",
) -> GuardDecision:
    """Enforce response-only Cart status and block mutations or re-purchase nudges on terminal carts (#739)."""
    if request_sets_status:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_TERMINAL_STATUS_MUTATION_OR_NUDGE_BLOCKED",
            detail="Cart status has ucp_request: 'omit' and MUST NOT be set by Platform requests.",
            evidence={"request_sets_status": True},
        )

    if cart_status not in _VALID_CART_STATUSES:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_TERMINAL_STATUS_MUTATION_OR_NUDGE_BLOCKED",
            detail=f"Unknown Cart status {cart_status!r}; expected active|ordered|canceled|expired.",
            evidence={"cart_status": cart_status},
        )

    if cart_status in _TERMINAL_CART_STATUSES and attempted_action in {"update_cart", "nudge_checkout", " transition_to_active"}:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_TERMINAL_STATUS_MUTATION_OR_NUDGE_BLOCKED",
            detail=f"Cart in terminal status {cart_status!r} cannot execute {attempted_action!r}.",
            evidence={"cart_status": cart_status, "attempted_action": attempted_action},
        )

    if cart_status == "ordered" and attempted_action == "rebuild_abandoned_cart":
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_TERMINAL_STATUS_MUTATION_OR_NUDGE_BLOCKED",
            detail="Ordered cart completed via continue_url handoff; rebuilding risks double-charging the buyer.",
            evidence={"cart_status": cart_status, "attempted_action": attempted_action},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_CART_STATUS_DISPOSITION_VERIFIED",
        detail=f"Cart disposition {cart_status!r} permits {attempted_action!r}.",
        evidence={"cart_status": cart_status, "attempted_action": attempted_action},
    )


# ---------------------------------------------------------------------------
# 6. UCP #738: State-Bound Merchant Cart Offer Extension
# ---------------------------------------------------------------------------

def evaluate_ucp_state_bound_cart_offer(
    *,
    cart_id: str,
    current_cart_state_ref: str,
    offer: Mapping[str, Any],
    requested_offer_id: str,
    requested_revision: str,
    current_timestamp: int,
    business_can_honor: bool = True,
) -> GuardDecision:
    """Validate apply_offer(cart_id, offer_id, revision) against cart state_ref and expiry (#738)."""
    applies_to = offer.get("applies_to") if isinstance(offer.get("applies_to"), Mapping) else {}
    offer_cart_id = str(applies_to.get("cart_id", ""))
    offer_state_ref = str(applies_to.get("state_ref", ""))
    offer_id = str(offer.get("id", ""))
    offer_revision = str(offer.get("revision", ""))
    expires_at = int(offer.get("expires_at_epoch", 0))

    if offer_id != requested_offer_id or offer_revision != requested_revision or offer_cart_id != cart_id:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_OFFER_STALE_STATE_REF_BLOCKED",
            detail="apply_offer (cart_id, offer_id, revision) does not match the Offer identity.",
            evidence={"requested_offer_id": requested_offer_id, "requested_revision": requested_revision},
        )

    if not offer_state_ref or offer_state_ref != current_cart_state_ref:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_OFFER_STALE_STATE_REF_BLOCKED",
            detail=f"Offer bound to state_ref {offer_state_ref!r} is stale for current Cart state {current_cart_state_ref!r}.",
            evidence={"offer_state_ref": offer_state_ref, "current_cart_state_ref": current_cart_state_ref},
        )

    if current_timestamp >= expires_at or not business_can_honor:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_OFFER_STALE_STATE_REF_BLOCKED",
            detail="Merchant Cart Offer has expired or can no longer be honored by the Business.",
            evidence={"current_timestamp": current_timestamp, "expires_at": expires_at, "business_can_honor": business_can_honor},
        )

    proposed_update = offer.get("proposed_update")
    if not isinstance(proposed_update, Mapping) or "line_items" not in proposed_update or any(
        k in proposed_update for k in ("add", "remove", "patch")
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_CART_OFFER_STALE_STATE_REF_BLOCKED",
            detail="Offer proposed_update MUST use standard Cart line_items replacement semantics, not custom patch verbs.",
            evidence={"proposed_update_keys": list(proposed_update.keys()) if isinstance(proposed_update, Mapping) else []},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_CART_OFFER_STATE_BOUND_APPLIED",
        detail="State-bound merchant Cart Offer verified and applied.",
        evidence={"offer_id": offer_id, "revision": offer_revision, "state_ref": offer_state_ref},
    )


# ---------------------------------------------------------------------------
# 7. UCP #727: Platform-Funded Discount Issuance & Net Reimbursement Gate
# ---------------------------------------------------------------------------

def evaluate_ucp_platform_funded_discount_reimbursement(
    *,
    capability_negotiated: bool,
    funding_reference: str,
    approved_subsidy_cap_minor: int,
    order_applied_discount_minor: int,
    refunded_or_canceled_subsidy_minor: int,
    claimed_reimbursement_minor: int,
) -> GuardDecision:
    """Validate Platform-funded discount issuance, Order attribution, and net reimbursement (#727)."""
    if not capability_negotiated or not funding_reference.strip():
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_PLATFORM_DISCOUNT_REIMBURSEMENT_OVERFLOW_BLOCKED",
            detail="Platform-funded discount requires negotiated capability and durable funding_reference.",
            evidence={"capability_negotiated": capability_negotiated, "funding_reference": funding_reference},
        )

    if order_applied_discount_minor > approved_subsidy_cap_minor or order_applied_discount_minor < 0:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_PLATFORM_DISCOUNT_REIMBURSEMENT_OVERFLOW_BLOCKED",
            detail="Order applied platform discount exceeds the issued subsidy commitment cap.",
            evidence={
                "order_applied_discount_minor": order_applied_discount_minor,
                "approved_subsidy_cap_minor": approved_subsidy_cap_minor,
            },
        )

    expected_net_reimbursement = max(0, order_applied_discount_minor - refunded_or_canceled_subsidy_minor)
    if claimed_reimbursement_minor != expected_net_reimbursement:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_PLATFORM_DISCOUNT_REIMBURSEMENT_OVERFLOW_BLOCKED",
            detail=f"Claimed reimbursement {claimed_reimbursement_minor} != net applied amount {expected_net_reimbursement}.",
            evidence={
                "claimed_reimbursement_minor": claimed_reimbursement_minor,
                "expected_net_reimbursement": expected_net_reimbursement,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_PLATFORM_DISCOUNT_REIMBURSEMENT_VERIFIED",
        detail="Platform-funded discount net reimbursement reconciled against Order and refund adjustments.",
        evidence={"funding_reference": funding_reference, "net_reimbursement_minor": expected_net_reimbursement},
    )


# ---------------------------------------------------------------------------
# 8. UCP #751, #750, #797: Lower-Funnel Item Snapshot & 6 Fraud Risk Signals
# ---------------------------------------------------------------------------

def validate_ucp_item_snapshot_and_fraud_signals(
    *,
    request_item_payload: Mapping[str, Any],
    order_captured_list_price: int | None,
    order_returned_list_price: int | None,
    catalog_current_list_price: int | None,
    response_options_complete: bool,
    signals: Mapping[str, Any],
) -> GuardDecision:
    """Enforce response-only item.list_price (#751), item.options (#750), and typed fraud signals (#797)."""
    if "list_price" in request_item_payload or "options" in request_item_payload:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
            detail="Platform Cart/Checkout requests MUST omit response-only item.list_price and item.options.",
            evidence={"request_item_keys": list(request_item_payload.keys())},
        )

    if order_captured_list_price is not None and order_returned_list_price != order_captured_list_price:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
            detail="Order item.list_price MUST remain the immutable order-creation snapshot, not live catalog state.",
            evidence={
                "order_captured_list_price": order_captured_list_price,
                "order_returned_list_price": order_returned_list_price,
                "catalog_current_list_price": catalog_current_list_price,
            },
        )

    if not response_options_complete:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
            detail="When present, item.options MUST carry the complete selected option set for the Variant (#750).",
            evidence={"response_options_complete": False},
        )

    # Validate #797 fraud signal types
    ip_country = signals.get("dev.ucp.buyer_ip_country")
    if ip_country is not None and (not isinstance(ip_country, str) or len(ip_country) != 2 or not ip_country.isalpha()):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
            detail="dev.ucp.buyer_ip_country must be a 2-letter ISO country code.",
            evidence={"buyer_ip_country": ip_country},
        )

    for dim_key in ("dev.ucp.browser_screen_height", "dev.ucp.browser_screen_width"):
        val = signals.get(dim_key)
        if val is not None and (isinstance(val, bool) or not isinstance(val, int) or val <= 0):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
                detail=f"{dim_key} must be a positive integer.",
                evidence={dim_key: val},
            )

    java_enabled = signals.get("dev.ucp.browser_java_enabled")
    if java_enabled is not None and not isinstance(java_enabled, bool):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="UCP_ITEM_SNAPSHOT_OR_FRAUD_SIGNAL_SPOOF_BLOCKED",
            detail="dev.ucp.browser_java_enabled must be a boolean.",
            evidence={"browser_java_enabled": java_enabled},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="UCP_ITEM_SNAPSHOT_AND_FRAUD_SIGNALS_VERIFIED",
        detail="Lower-funnel item list_price/options snapshot and fraud environment signals verified.",
        evidence={"order_list_price": order_returned_list_price, "signal_keys": sorted(signals.keys())},
    )


# ---------------------------------------------------------------------------
# 9. AP2 #321: Selective-Disclosure Plaintext Payment Artifact Log Redaction
# ---------------------------------------------------------------------------

_SENSITIVE_AP2_LOG_KEYS = frozenset(
    {
        "payment_token",
        "paymentmandate",
        "payment_mandate",
        "checkoutmandate",
        "checkout_mandate",
        "paymentreceipt",
        "payment_receipt",
        "risk_data",
        "sd_jwt_disclosures",
    }
)


def audit_ap2_selective_disclosure_log_payload(
    *,
    log_record: Mapping[str, Any],
    allow_unrecognized_parts_verbatim: bool = False,
) -> GuardDecision:
    """Block plaintext logging of AP2 payment tokens, mandates, receipts, and risk_data (#321)."""
    if allow_unrecognized_parts_verbatim:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="AP2_PLAINTEXT_PAYMENT_ARTIFACT_LOG_LEAK_BLOCKED",
            detail="watch_log / base_server_executor MUST NOT log unrecognized A2A/MCP data parts verbatim.",
            evidence={"allow_unrecognized_parts_verbatim": True},
        )

    leaked_keys: list[str] = []

    def _scan(obj: Any) -> None:
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                norm_k = str(k).lower().strip()
                if norm_k in _SENSITIVE_AP2_LOG_KEYS and v not in ("<REDACTED>", "[REDACTED]", None):
                    leaked_keys.append(str(k))
                _scan(v)
        elif isinstance(obj, list):
            for item in obj:
                _scan(item)

    _scan(log_record)
    if leaked_keys:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="AP2_PLAINTEXT_PAYMENT_ARTIFACT_LOG_LEAK_BLOCKED",
            detail=f"Plaintext AP2 sensitive payment artifacts detected in log record: {leaked_keys}",
            evidence={"leaked_keys": leaked_keys},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="AP2_SELECTIVE_DISCLOSURE_LOG_REDACTED",
        detail="AP2 log record preserves selective disclosure and redacts sensitive payment artifacts.",
        evidence={"redacted": True},
    )


# ---------------------------------------------------------------------------
# 10. x402 #3875, #3887, #3823, #3801: Go verifyEIP3009 3-Tuple & @x402/next 402 Body
# ---------------------------------------------------------------------------

def validate_x402_verify_eip3009_and_next_402_contract(
    *,
    verify_return_tuple_len: int,
    ecdsa_s_is_canonical_low: bool,
    verify_error_code: str | None,
    next_unpaid_402_json_body: Mapping[str, Any],
    xp_track: str = "Standards",
    xp_has_conformance_tests: bool = True,
) -> GuardDecision:
    """Enforce 3-value return on Go verifyEIP3009 (#3875/#3887), @x402/next 402 body (#3875), and XP conformance (#3801)."""
    if verify_return_tuple_len != 3:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="X402_VERIFY_EIP3009_ARITY_OR_NEXT_402_BODY_DRIFT_BLOCKED",
            detail=f"verifyEIP3009 returned {verify_return_tuple_len} values; expected 3 (*VerifyResponse, *EIP3009SignatureClassification, error).",
            evidence={"verify_return_tuple_len": verify_return_tuple_len},
        )

    if not ecdsa_s_is_canonical_low and verify_error_code != "ErrInvalidSignatureS":
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="X402_VERIFY_EIP3009_ARITY_OR_NEXT_402_BODY_DRIFT_BLOCKED",
            detail="Non-canonical high-s EIP-3009 signature must fail with ErrInvalidSignatureS.",
            evidence={"verify_error_code": verify_error_code},
        )

    if dict(next_unpaid_402_json_body) != {"error": "Payment required"}:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="X402_VERIFY_EIP3009_ARITY_OR_NEXT_402_BODY_DRIFT_BLOCKED",
            detail="@x402/next default unpaid non-browser 402 JSON body must be {'error': 'Payment required'}, not {}.",
            evidence={"next_unpaid_402_json_body": dict(next_unpaid_402_json_body)},
        )

    if xp_track == "Standards" and not xp_has_conformance_tests:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="X402_VERIFY_EIP3009_ARITY_OR_NEXT_402_BODY_DRIFT_BLOCKED",
            detail="Standards Track XP (x402 Proposal) requires conformance tests before finalization (#3801).",
            evidence={"xp_track": xp_track, "xp_has_conformance_tests": xp_has_conformance_tests},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="X402_VERIFY_EIP3009_AND_NEXT_402_VERIFIED",
        detail="Go verifyEIP3009 3-tuple classification, @x402/next 402 JSON body, and XP conformance verified.",
        evidence={"verify_return_tuple_len": 3, "next_402_body": dict(next_unpaid_402_json_body)},
    )


# ---------------------------------------------------------------------------
# 11. Sierra tau2-bench #545: banking_knowledge BM25 + Grep Title Indexing
# ---------------------------------------------------------------------------

def evaluate_tau2_bm25_grep_title_aware_retrieval(
    *,
    documents: Sequence[Mapping[str, str]],
    query: str,
    include_title_in_index: bool,
    expected_top_doc_id: str,
) -> GuardDecision:
    """Ensure BM25 and grep index both doc.title and doc.content so title matches rank first (#545)."""
    if not include_title_in_index:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_BM25_GREP_TITLE_OMISSION_BLOCKED",
            detail="BM25Indexer and grep must index doc.title alongside doc.content (#545).",
            evidence={"include_title_in_index": False},
        )

    q_tokens = [t.lower() for t in re.findall(r"[a-z0-9]+", query)]
    scored: list[tuple[int, str]] = []
    for doc in documents:
        doc_id = str(doc.get("id", ""))
        title = str(doc.get("title", "")).lower()
        body = str(doc.get("text", "")).lower()
        # Title hits receive higher weight + exact phrase bonus
        title_score = sum(3 for tok in q_tokens if tok in title)
        if query.lower() in title:
            title_score += 10
        body_score = sum(1 for tok in q_tokens if tok in body)
        scored.append((title_score + body_score, doc_id))

    scored.sort(key=lambda x: (-x[0], x[1]))
    top_doc_id = scored[0][1] if scored else ""
    if top_doc_id != expected_top_doc_id:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_BM25_GREP_TITLE_OMISSION_BLOCKED",
            detail=f"Top retrieved document {top_doc_id!r} != expected {expected_top_doc_id!r}.",
            evidence={"top_doc_id": top_doc_id, "expected_top_doc_id": expected_top_doc_id},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="TAU2_BM25_GREP_TITLE_INDEXING_VERIFIED",
        detail="Title-aware BM25 + grep retrieval ranked the authoritative policy document first.",
        evidence={"top_doc_id": top_doc_id, "score": scored[0][0]},
    )


# ---------------------------------------------------------------------------
# 12. Sierra tau2-bench #495: Airline Task 7 "Other Upcoming Flights" Scope
# ---------------------------------------------------------------------------

def evaluate_tau2_airline_task7_other_flights_total(
    *,
    reservation_totals_usd: Mapping[str, int],
    cancelled_in_session_ids: Sequence[str],
    user_question_scope: str,
    communicated_amount_usd: int,
) -> GuardDecision:
    """Resolve Airline Task 7 'other upcoming flights' ($708) vs 'all upcoming flights' ($1,628) (#495)."""
    cancelled_set = set(cancelled_in_session_ids)
    all_total = sum(int(v) for v in reservation_totals_usd.values())
    other_total = sum(int(v) for k, v in reservation_totals_usd.items() if k not in cancelled_set)

    if user_question_scope == "other_upcoming_flights":
        expected = other_total
    elif user_question_scope == "all_upcoming_flights":
        expected = all_total
    else:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_AIRLINE_TASK7_OTHER_FLIGHTS_SCOPE_MISMATCH_BLOCKED",
            detail=f"Unknown question scope {user_question_scope!r}.",
            evidence={"user_question_scope": user_question_scope},
        )

    if communicated_amount_usd != expected:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_AIRLINE_TASK7_OTHER_FLIGHTS_SCOPE_MISMATCH_BLOCKED",
            detail=f"Communicated total ${communicated_amount_usd} mismatches {user_question_scope} total ${expected}.",
            evidence={
                "communicated_amount_usd": communicated_amount_usd,
                "expected_usd": expected,
                "other_total_usd": other_total,
                "all_total_usd": all_total,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="TAU2_AIRLINE_TASK7_SCOPE_TOTAL_VERIFIED",
        detail=f"Communicated total ${communicated_amount_usd} matches {user_question_scope} scope.",
        evidence={"communicated_amount_usd": communicated_amount_usd, "scope": user_question_scope},
    )


# ---------------------------------------------------------------------------
# 13. Sierra tau2-bench #493, #497: pass^k Infrastructure-Error Inflation Guard
# ---------------------------------------------------------------------------

def evaluate_tau2_pass_hat_k_infra_error_integrity(
    *,
    configured_trials: int,
    successful_trials: int,
    infrastructure_error_trials: int,
    reported_pass_hat_1: float,
    allow_silent_infra_exclusion: bool = False,
) -> GuardDecision:
    """Prevent pass^1 from reporting 100% when infrastructure errors are silently excluded (#493, #497)."""
    if configured_trials <= 0 or successful_trials < 0 or infrastructure_error_trials < 0:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_PASS_HAT_K_INFRA_EXCLUSION_INFLATION_BLOCKED",
            detail="Invalid trial counts.",
            evidence={"configured_trials": configured_trials},
        )

    if allow_silent_infra_exclusion and infrastructure_error_trials > 0:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_PASS_HAT_K_INFRA_EXCLUSION_INFLATION_BLOCKED",
            detail="Excluding INFRASTRUCTURE_ERROR trials silently inflates pass^k (e.g. 1/4 success -> 100% pass^1).",
            evidence={
                "configured_trials": configured_trials,
                "successful_trials": successful_trials,
                "infrastructure_error_trials": infrastructure_error_trials,
                "reported_pass_hat_1": reported_pass_hat_1,
            },
        )

    true_pass_hat_1 = round(successful_trials / configured_trials, 4)
    if abs(reported_pass_hat_1 - true_pass_hat_1) > 1e-4:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_PASS_HAT_K_INFRA_EXCLUSION_INFLATION_BLOCKED",
            detail=f"Reported pass^1 ({reported_pass_hat_1}) diverges from full-denominator pass^1 ({true_pass_hat_1}).",
            evidence={"reported_pass_hat_1": reported_pass_hat_1, "true_pass_hat_1": true_pass_hat_1},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="TAU2_PASS_HAT_K_DENOMINATOR_VERIFIED",
        detail="pass^k denominator includes all configured trials and explicitly surfaces infrastructure errors.",
        evidence={"true_pass_hat_1": true_pass_hat_1, "infrastructure_error_trials": infrastructure_error_trials},
    )


# ---------------------------------------------------------------------------
# 14. Sierra tau2-bench #492, #487, #470: Persona DOB, Solo Gemini, Speech+Tool
# ---------------------------------------------------------------------------

def validate_tau2_persona_solo_and_simulator_turn(
    *,
    persona_stated_age: int,
    db_birth_year: int,
    reference_year: int,
    is_solo_mode: bool,
    first_message_role: str | None,
    first_message_content: str | None,
    user_sim_turn_has_speech: bool,
    user_sim_turn_has_tracking_tool: bool,
    orchestrator_drops_speech_on_tool_call: bool = False,
) -> GuardDecision:
    """Validate Telecom persona age vs DB DOB (#492), Solo opening user turn (#487), and speech+tool turn (#470)."""
    expected_age = reference_year - db_birth_year
    if abs(persona_stated_age - expected_age) > 1:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_PERSONA_DOB_SOLO_GEMINI_OR_SPEECH_TOOL_CRASH_BLOCKED",
            detail=f"Persona age ({persona_stated_age}) conflicts with DB DOB year ({db_birth_year}, age ~{expected_age}).",
            evidence={"persona_stated_age": persona_stated_age, "expected_age": expected_age},
        )

    if is_solo_mode:
        if first_message_role != "user" or first_message_content != "Begin working on the ticket.":
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason_code="TAU2_PERSONA_DOB_SOLO_GEMINI_OR_SPEECH_TOOL_CRASH_BLOCKED",
                detail="LLMSoloAgent must seed persistent content-free UserMessage('Begin working on the ticket.') for Gemini.",
                evidence={"first_message_role": first_message_role, "first_message_content": first_message_content},
            )

    if user_sim_turn_has_speech and user_sim_turn_has_tracking_tool and orchestrator_drops_speech_on_tool_call:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_PERSONA_DOB_SOLO_GEMINI_OR_SPEECH_TOOL_CRASH_BLOCKED",
            detail="Orchestrator dropped user speech when routing tracking-only user tool call, causing empty retry crash (#470).",
            evidence={"orchestrator_drops_speech_on_tool_call": True},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="TAU2_PERSONA_SOLO_AND_SIMULATOR_VERIFIED",
        detail="Telecom persona age matches DB DOB, Solo opening user turn seeded, and speech+tracking-tool preserved.",
        evidence={"expected_age": expected_age, "is_solo_mode": is_solo_mode},
    )


# ---------------------------------------------------------------------------
# 15. Sierra tau2-bench #439, #463: Read-Tool Completeness & Write Equivalence
# ---------------------------------------------------------------------------

def validate_tau2_kb_read_tool_and_write_equivalence(
    *,
    kb_required_tables: Sequence[str],
    agent_callable_read_tables: Sequence[str],
    unretired_card_closure_threads: Sequence[str],
    write_arg_semantically_equivalent: bool,
    penalize_equivalent_write_arg: bool = False,
) -> GuardDecision:
    """Ensure KB-required tables (e.g. cash_back_disputes) have read tools (#439) and avoid loose write penalties (#463)."""
    callable_set = set(agent_callable_read_tables)
    missing_tables = [t for t in kb_required_tables if t not in callable_set]
    if missing_tables:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_UNDISCOVERABLE_TABLE_OR_LOOSE_WRITE_PENALTY_BLOCKED",
            detail=f"KB procedure requires reading {missing_tables}, but no agent-callable read tool exposes them (#439).",
            evidence={"missing_read_tables": missing_tables},
        )

    if unretired_card_closure_threads:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_UNDISCOVERABLE_TABLE_OR_LOOSE_WRITE_PENALTY_BLOCKED",
            detail=f"Task scenario leaves card closure request(s) unretired: {list(unretired_card_closure_threads)} (#463).",
            evidence={"unretired_card_closure_threads": list(unretired_card_closure_threads)},
        )

    if write_arg_semantically_equivalent and penalize_equivalent_write_arg:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason_code="TAU2_UNDISCOVERABLE_TABLE_OR_LOOSE_WRITE_PENALTY_BLOCKED",
            detail="Evaluator penalized semantically equivalent free-text write argument in db_match (#463).",
            evidence={"penalize_equivalent_write_arg": True},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason_code="TAU2_KB_READ_TOOL_AND_WRITE_EQUIVALENCE_VERIFIED",
        detail="All KB-mandated tables have agent read tools and equivalent write arguments are normalized.",
        evidence={"read_tables": sorted(callable_set)},
    )
