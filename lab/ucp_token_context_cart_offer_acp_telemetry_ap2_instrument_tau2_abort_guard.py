"""Stage 66 runtime guards for UCP, ACP, Google AP2, and Sierra tau2-bench.

Covers 20 primary-source PRs across the four core protocol repositories:
1. Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`):
   - PR #793: `ucp/version` permalink protocol version control parameter (consumed on resolution, never leaked to redirect URL, never returns JSON `version_unsupported` to browser GET)
   - PR #792: `TokenCredential` `binding` and `identity` issuance context carried unchanged through checkout (and `identity` never accepted as caller auth)
   - PR #773: State-bound Cart `Offer` in `actions` map (`applies_to.cart_id` + `applies_to.state_ref`, immutable `id` + `revision`, no parallel `offers.available[]`)
   - PR #740: Terminal Cart `status` (`active | ordered | canceled | expired`, immutable terminal disposition)
   - PR #730: `action.ready` success branch constrained with `maxProperties: 0` (`{}`)
   - PR #719: `com.mercadopago.shopping.digital_delivery` Order extension (`redeemable_artifact | entitlement`, pointer-only `reference` + `lookup`, no cached balance, delivery != settlement)
   - PR #716: OpenAPI 3.1 authentication declared via `components.securitySchemes` instead of ignored header parameters (`Authorization`, `Accept`, `Content-Type`, `X-API-Key`)
2. Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`):
   - PR #238: `session_context` object for raw buyer/device telemetry on `complete_checkout` & `delegate_payment` vs. `delegate_payment.risk_signals` array of normalized fraud results
   - PR #237: Embedded App Deep Links (`app_links` priority list on `Product`/`Variant` with safe fallback to canonical `url`)
   - PR #232: Post-checkout Order schema alignment (3-field quantity model `ordered == fulfilled + canceled`, `returned <= fulfilled`, and order-level `completed` status)
   - PR #149, #114, #111: `content_attribution` URL citations, `dev.acp.seller_backed.*` handlers (`requires_delegate_payment=True`, `requires_pci_compliance=False`, no credential transfer, points balance check), and `x402` crypto SPT flow
3. Google Agent Payments Protocol (`google-agentic-commerce/AP2`):
   - PR #301: `AllowedPaymentInstrumentEvaluator` matching by `(type, id)` tuple rather than `id` alone (Fixes #299 item 2)
   - PR #307: Versioned `delegate-SD-JWT` golden vectors wire invariants (`N` segments -> `N - 1` `~~` joins, trailing `~`, intact JWS signature)
   - PR #305 & #216: `@ap2-protocol/sdk` TypeScript/Zod receipt `oneOf` branch required fields (`psp_confirmation_id`/`network_confirmation_id` vs. `error`/`error_description`) & `ghost-protocol` EIP-712 non-custodial `IntentMandate` monthly cap
4. Sierra tau2-bench (`sierra-research/tau2-bench`):
   - PR #548: Record `###OUT-OF-SCOPE###` aborts as `TerminationReason.OUT_OF_SCOPE` (ordered before `###STOP###`, zero reward) across `initialize()`, `step()`, and `full_duplex_orchestrator` (Fixes #517)
   - PR #562: Parse fenced Markdown JSON in NL-assertion judge responses via `extract_json_from_llm_response` while raising on malformed JSON (Fixes #555)
   - PR #533: Preserve directory-format checkpoint and index until replacement trajectory file write succeeds
   - PR #606, #602, #596: Synchronize aggregate banking `tasks.json` (97 tasks including task `102` `NL_ASSERTION`), enforce lowercase airline `user_id`, and validate `campus` dual-control v1.0.1 scoring (`[DB, COMMUNICATE]` + `env_assertions`, no `ACTION`)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import json
import re


_DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALID_CART_STATUSES = frozenset({"active", "ordered", "canceled", "expired"})
_TERMINAL_CART_STATUSES = frozenset({"ordered", "canceled", "expired"})
_IGNORED_OPENAPI_HEADER_PARAMS = frozenset({"authorization", "accept", "content-type", "x-api-key"})
_SELLER_BACKED_HANDLERS = frozenset(
    {
        "dev.acp.seller_backed.saved_card",
        "dev.acp.seller_backed.gift_card",
        "dev.acp.seller_backed.points",
        "dev.acp.seller_backed.store_credit",
    }
)


@dataclass(frozen=True)
class UCPTokenContextCartOfferSecurityAuditResult:
    passed: bool
    reason_codes: tuple[str, ...]
    resolved_permalink_version: str
    cart_terminal: bool


def verify_ucp_permalink_version_token_context_cart_offer_and_security_schemes(
    *,
    permalink_has_ucp_field_paths: bool,
    permalink_ucp_versions: Sequence[str],
    redirect_url_contains_control_params: bool,
    browser_returned_json_version_unsupported: bool,
    issued_token_binding: Mapping[str, Any],
    presented_token_binding: Mapping[str, Any],
    token_identity_accepted_as_caller_auth: bool,
    cart_has_parallel_offers_available_array: bool,
    cart_id: str,
    cart_state_ref: str,
    offer_action_applies_to_cart_id: str,
    offer_action_applies_to_state_ref: str,
    offer_revision_immutable: bool,
    cart_previous_status: str,
    cart_next_status: str,
    payment_action_ready_result: Mapping[str, Any],
    payment_action_ready_is_error_branch: bool,
    digital_delivery_extension: Mapping[str, Any],
    openapi_declared_header_param_names: Sequence[str],
    openapi_has_security_schemes: bool,
) -> UCPTokenContextCartOfferSecurityAuditResult:
    reasons: list[str] = []

    resolved_version = "default"
    if permalink_has_ucp_field_paths:
        if len(permalink_ucp_versions) != 1 or not _DATE_VERSION_RE.match(str(permalink_ucp_versions[0])):
            reasons.append("ucp_permalink_version_missing_or_leaked_on_redirect")
        else:
            resolved_version = str(permalink_ucp_versions[0])
    elif len(permalink_ucp_versions) > 1 or (
        len(permalink_ucp_versions) == 1 and not _DATE_VERSION_RE.match(str(permalink_ucp_versions[0]))
    ):
        reasons.append("ucp_permalink_version_missing_or_leaked_on_redirect")

    if redirect_url_contains_control_params or browser_returned_json_version_unsupported:
        if "ucp_permalink_version_missing_or_leaked_on_redirect" not in reasons:
            reasons.append("ucp_permalink_version_missing_or_leaked_on_redirect")

    if (
        dict(issued_token_binding) != dict(presented_token_binding)
        or token_identity_accepted_as_caller_auth
    ):
        reasons.append("ucp_token_credential_binding_mutated_or_mismatch")

    if (
        cart_has_parallel_offers_available_array
        or offer_action_applies_to_cart_id != cart_id
        or offer_action_applies_to_state_ref != cart_state_ref
        or not offer_revision_immutable
    ):
        reasons.append("ucp_cart_offer_state_ref_mismatch_or_parallel_array")

    if (
        cart_previous_status not in _VALID_CART_STATUSES
        or cart_next_status not in _VALID_CART_STATUSES
        or (
            cart_previous_status in _TERMINAL_CART_STATUSES
            and cart_next_status != cart_previous_status
        )
    ):
        reasons.append("ucp_cart_terminal_status_invalid_or_mutated")

    if not payment_action_ready_is_error_branch and len(payment_action_ready_result) > 0:
        reasons.append("ucp_payment_action_ready_non_empty_success_object")

    dd_attached_to = str(digital_delivery_extension.get("attached_to", ""))
    dd_kind = str(digital_delivery_extension.get("kind", ""))
    dd_has_reference_and_lookup = bool(
        digital_delivery_extension.get("reference") and digital_delivery_extension.get("lookup")
    )
    dd_caches_mutable_balance = bool(digital_delivery_extension.get("caches_mutable_balance", False))
    dd_releases_settlement_on_delivery = bool(
        digital_delivery_extension.get("releases_settlement_on_delivery", False)
    )
    if (
        dd_attached_to != "order"
        or dd_kind not in {"redeemable_artifact", "entitlement"}
        or not dd_has_reference_and_lookup
        or dd_caches_mutable_balance
        or dd_releases_settlement_on_delivery
    ):
        reasons.append("ucp_digital_delivery_cached_balance_or_premature_settlement")

    lowered_headers = {str(h).strip().lower() for h in openapi_declared_header_param_names}
    if not openapi_has_security_schemes or bool(lowered_headers & _IGNORED_OPENAPI_HEADER_PARAMS):
        reasons.append("ucp_openapi_ignored_auth_header_parameter_declared")

    return UCPTokenContextCartOfferSecurityAuditResult(
        passed=len(reasons) == 0,
        reason_codes=tuple(reasons),
        resolved_permalink_version=resolved_version,
        cart_terminal=cart_next_status in _TERMINAL_CART_STATUSES,
    )


@dataclass(frozen=True)
class ACPSessionContextAppLinksOrderAuditResult:
    passed: bool
    reason_codes: tuple[str, ...]
    selected_experience_uri: str


def verify_acp_session_context_app_links_order_alignment_and_seller_backed(
    *,
    complete_checkout_has_legacy_risk_signals_object: bool,
    complete_checkout_session_context: Mapping[str, Any] | None,
    delegate_payment_session_context: Mapping[str, Any] | None,
    delegate_payment_risk_signals: Any,
    product_url: str,
    app_links: Sequence[Mapping[str, str]],
    client_supported_platforms: Sequence[str],
    selected_uri: str,
    order_status: str,
    line_item_quantities: Mapping[str, int],
    content_attribution_urls: Sequence[str],
    seller_backed_handler: Mapping[str, Any],
    x402_crypto_facilitator_verified: bool,
) -> ACPSessionContextAppLinksOrderAuditResult:
    reasons: list[str] = []

    if (
        complete_checkout_has_legacy_risk_signals_object
        or not isinstance(complete_checkout_session_context, Mapping)
        or not isinstance(delegate_payment_risk_signals, (list, tuple))
        or (
            delegate_payment_session_context is not None
            and not isinstance(delegate_payment_session_context, Mapping)
        )
    ):
        reasons.append("acp_session_context_or_risk_signals_schema_collision")
    else:
        for sig in delegate_payment_risk_signals:
            if not isinstance(sig, Mapping) or not {"type", "score", "action"}.issubset(sig.keys()):
                reasons.append("acp_session_context_or_risk_signals_schema_collision")
                break

    expected_uri = product_url
    supported_set = {str(p) for p in client_supported_platforms}
    for entry in app_links:
        plat = str(entry.get("platform", ""))
        uri = str(entry.get("uri", ""))
        if plat in supported_set and uri:
            expected_uri = uri
            break
    if not product_url.startswith("https://") or selected_uri != expected_uri:
        reasons.append("acp_feed_app_links_invalid_or_missing_url_fallback")

    q_ordered = int(line_item_quantities.get("ordered", -1))
    q_fulfilled = int(line_item_quantities.get("fulfilled", -1))
    q_canceled = int(line_item_quantities.get("canceled", -1))
    q_returned = int(line_item_quantities.get("returned", -1))
    if (
        order_status == "fulfilled"
        or order_status not in {"created", "confirmed", "completed", "canceled"}
        or q_ordered < 0
        or q_fulfilled < 0
        or q_canceled < 0
        or q_returned < 0
        or q_ordered != (q_fulfilled + q_canceled)
        or q_returned > q_fulfilled
    ):
        reasons.append("acp_order_post_checkout_quantity_or_status_violation")

    for u in content_attribution_urls:
        if not str(u).startswith("https://"):
            reasons.append("acp_content_attribution_invalid_url")
            break

    h_id = str(seller_backed_handler.get("id", ""))
    req_del = bool(seller_backed_handler.get("requires_delegate_payment", False))
    req_pci = bool(seller_backed_handler.get("requires_pci_compliance", True))
    transferred_creds = bool(seller_backed_handler.get("credentials_transferred_to_agent", False))
    points_balance = int(seller_backed_handler.get("points_balance_minor", 0))
    purchase_amount = int(seller_backed_handler.get("purchase_amount_minor", 0))
    if (
        h_id not in _SELLER_BACKED_HANDLERS
        or not req_del
        or req_pci
        or transferred_creds
        or (h_id == "dev.acp.seller_backed.points" and points_balance < purchase_amount)
        or not x402_crypto_facilitator_verified
    ):
        reasons.append("acp_seller_backed_or_x402_crypto_handler_violation")

    return ACPSessionContextAppLinksOrderAuditResult(
        passed=len(reasons) == 0,
        reason_codes=tuple(reasons),
        selected_experience_uri=expected_uri,
    )


@dataclass(frozen=True)
class AP2InstrumentTypeIdGoldenVectorAuditResult:
    passed: bool
    reason_codes: tuple[str, ...]
    matched_instrument_pair: tuple[str, str] | None


def verify_ap2_instrument_type_id_golden_vectors_and_zod_sdk(
    *,
    allowed_instruments: Sequence[Mapping[str, str]],
    presented_instrument: Mapping[str, str],
    vector_segment_count: int,
    wire_double_tilde_joins: int,
    wire_ends_with_tilde: bool,
    jws_signatures_valid: bool,
    receipt_payload: Mapping[str, Any],
    ghost_protocol_mandate: Mapping[str, Any],
) -> AP2InstrumentTypeIdGoldenVectorAuditResult:
    reasons: list[str] = []

    p_type = str(presented_instrument.get("type", ""))
    p_id = str(presented_instrument.get("id", ""))
    matched_pair: tuple[str, str] | None = None
    for allowed in allowed_instruments:
        if str(allowed.get("type", "")) == p_type and str(allowed.get("id", "")) == p_id:
            matched_pair = (p_type, p_id)
            break
    if matched_pair is None:
        reasons.append("ap2_allowed_payment_instrument_type_mismatch")

    if (
        vector_segment_count < 1
        or wire_double_tilde_joins != (vector_segment_count - 1)
        or not wire_ends_with_tilde
        or not jws_signatures_valid
    ):
        reasons.append("ap2_delegate_sd_jwt_golden_vector_wire_violation")

    r_status = str(receipt_payload.get("status", ""))
    if r_status == "success":
        if not (
            receipt_payload.get("psp_confirmation_id")
            and receipt_payload.get("network_confirmation_id")
        ):
            reasons.append("ap2_receipt_oneof_branch_required_fields_missing")
    elif r_status == "error":
        if not (receipt_payload.get("error") and receipt_payload.get("error_description")):
            reasons.append("ap2_receipt_oneof_branch_required_fields_missing")
    else:
        reasons.append("ap2_receipt_oneof_branch_required_fields_missing")

    chain_id = int(ghost_protocol_mandate.get("chain_id", 0))
    eip712_valid = bool(ghost_protocol_mandate.get("eip712_signature_valid", False))
    monthly_cap_usdc = int(ghost_protocol_mandate.get("monthly_cap_minor", 0))
    requested_spend_usdc = int(ghost_protocol_mandate.get("requested_spend_minor", 0))
    if chain_id != 8453 or not eip712_valid or requested_spend_usdc > monthly_cap_usdc:
        reasons.append("ap2_autonomous_infra_intent_mandate_cap_or_sig_invalid")

    return AP2InstrumentTypeIdGoldenVectorAuditResult(
        passed=len(reasons) == 0,
        reason_codes=tuple(reasons),
        matched_instrument_pair=matched_pair,
    )


def extract_fenced_or_plain_nl_judge_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = fence_match.group(1) if fence_match else text
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("NL judge response must decode to a JSON object")
    return parsed


@dataclass(frozen=True)
class Tau2OutOfScopeAbortFencedJsonCheckpointAuditResult:
    passed: bool
    reason_codes: tuple[str, ...]
    classified_termination_reason: str


def verify_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus(
    *,
    user_message: str,
    recorded_termination_reason: str,
    assigned_reward: float,
    nl_judge_raw_response: str,
    malformed_json_swallowed_as_empty: bool,
    checkpoint_unlinked_before_replacement_write: bool,
    banking_aggregate_task_count: int,
    banking_individual_task_count: int,
    banking_task_102_has_nl_assertion: bool,
    airline_user_id: str,
    campus_reward_basis: Sequence[str],
    campus_has_env_assertions: bool,
) -> Tau2OutOfScopeAbortFencedJsonCheckpointAuditResult:
    reasons: list[str] = []

    if "###OUT-OF-SCOPE###" in user_message:
        expected_reason = "OUT_OF_SCOPE"
    elif "###STOP###" in user_message or "###TRANSFER###" in user_message:
        expected_reason = "USER_STOP"
    else:
        expected_reason = "CONTINUE"

    if recorded_termination_reason != expected_reason or (
        expected_reason == "OUT_OF_SCOPE" and assigned_reward != 0.0
    ):
        reasons.append("tau2_out_of_scope_abort_conflated_with_user_stop")

    if malformed_json_swallowed_as_empty:
        reasons.append("tau2_nl_judge_fenced_json_or_malformed_swallowed")
    else:
        try:
            parsed = extract_fenced_or_plain_nl_judge_json(nl_judge_raw_response)
            if "results" not in parsed or not isinstance(parsed["results"], list):
                reasons.append("tau2_nl_judge_fenced_json_or_malformed_swallowed")
        except Exception:
            reasons.append("tau2_nl_judge_fenced_json_or_malformed_swallowed")

    if checkpoint_unlinked_before_replacement_write:
        reasons.append("tau2_checkpoint_pre_unlink_data_loss_on_write_failure")

    if (
        banking_aggregate_task_count != 97
        or banking_individual_task_count != 97
        or not banking_task_102_has_nl_assertion
        or airline_user_id != airline_user_id.lower()
        or not airline_user_id
        or tuple(campus_reward_basis) != ("DB", "COMMUNICATE")
        or "ACTION" in campus_reward_basis
        or not campus_has_env_assertions
    ):
        reasons.append("tau2_banking_aggregate_or_airline_campus_invariant_violation")

    return Tau2OutOfScopeAbortFencedJsonCheckpointAuditResult(
        passed=len(reasons) == 0,
        reason_codes=tuple(reasons),
        classified_termination_reason=expected_reason,
    )
