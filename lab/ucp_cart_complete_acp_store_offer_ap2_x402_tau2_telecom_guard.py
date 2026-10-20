"""Stage 62 deterministic protocol & benchmark guards.

Covers primary-source upstream PRs across four ecosystems:
1. Universal-Commerce-Protocol/ucp PRs #911, #910, #907, #906, #883, #853:
   - Cart-to-checkout conversion & completion (`#911`, `#871`, `#910`):
     `cart_id` MUST be omitted on `complete_checkout` requests (`"complete": "omit"`),
     and `create_checkout` requests converting a cart via `cart_id` MUST still include
     `line_items` (canonically `"line_items": []`) due to monotonic `allOf` inheritance.
   - Checkout signed request `UCP-Agent` coverage (`#907`):
     When a request carries a `UCP-Agent` header, RFC 9421 `Signature-Input` covered
     components MUST include `"ucp-agent"`, otherwise verification fails with
     `coverage_insufficient`.
   - OpenRPC embedded auth required `type` & MCP `complete_checkout` extensions (`#906`, `#883`):
     `ec.auth` and `ep.cart.auth` MUST mark `type` as `"required": true` and provide a
     non-empty auth `type`; MCP `complete_checkout` MUST declare supported completion
     extensions (`dev.ucp.shopping.buyer_consent`, `dev.ucp.common.payment.ap2_mandate`).
   - Normative requirements catalog extractor & reconciliation (`#853`):
     Requirement IDs match `^REQ-[A-Z0-9-]+-[0-9]{2,}$` (<= 42 chars), 10-hex SHA-256
     `content_digest` over `(capability, list_stem, normalized_text)`, and exact clause
     reconciliation (`bolded + unbolded + schema_annotation == total_keyword_clauses`).

2. agentic-commerce-protocol/agentic-commerce-protocol PRs #230, #171, #165, #162, #161:
   - Delegate payment optional `checkout_session_id` & extensible error enums (`#230`, `#161`):
     `allowance.checkout_session_id` is optional on `delegate_payment` (while `reason`,
     `max_amount`, `currency`, `merchant_id`, `expires_at` remain required); `Error.type`
     / `Error.code` support `unauthorized` (401), `internal_server_error` (500), and
     `service_unavailable` (503) with forward-compatible fallback on unknown codes.
   - Store Extension for BOPIS & in-store shopping (`#171`):
     `store_id` is allowed on `create` and `update` checkout requests, and FORBIDDEN on
     `complete` checkout requests to prevent mid-payment repricing/tax race conditions;
     `/stores` discovery enforces `1 <= limit <= 100` and `radius > 0`.
   - Time-bound line-item offer expiry & booking semantics (`#165`):
     Per-line `valid_until` vs. session `quote_expires_at`; `availability_status` values
     `offer_valid` / `offer_expired`; `MessageError.code` values `offer_expired` vs.
     `quote_expired`.
   - Order webhook status semantics for physical vs. digital fulfillment (`#162`):
     `shipped` is restricted to physical shipping (`confirmed -> shipped -> fulfilled`)
     and FORBIDDEN on digital-only orders (`confirmed -> fulfilled`).

3. google-agentic-commerce/AP2 PRs #330, #310, #300, #267:
   - Closed checkout-binding enforcement in `PaymentMandateChain.verify()` (`#330`):
     Verification MUST fail closed if the closed Payment Mandate's `transaction_id` is
     not bound to the expected Checkout JWT (`expected_transaction_id`), even when
     `expected_open_checkout_hash` matches.
   - x402 PSP `settle_payment` fail-closed on missing agent-provider key (`#310`):
     Missing or empty `agent_provider_pub` MUST immediately return
     `agent_provider_key_missing` without executing mandate binding or settlement.
   - x402 credential provider verified mandate amount enforcement (`#300`):
     EIP-3009 authorization MUST use the signed `closed_mandate.payment_amount.amount`
     and fail closed (`verification_failed`) if missing, never falling back to a
     hardcoded `1250` cents when `payment_instrument.payee_address` raises `AttributeError`.
   - TrustBoost AP2 + x402 PII sanitization & Solana anchor proof (`#267`):
     Autonomous agent payloads containing PII (including LATAM `RFC`, `CPF`, `CUIT`)
     require pre-LLM sanitization and a verified `anchor_tx` after HTTP 402 settlement.

4. sierra-research/tau2-bench PRs #611, #610, #609, #615, #621:
   - Active telecom line guard on `refuel_data` (`#611`):
     `refuel_data` MUST reject `"suspended"`, `"pending_activation"`, or `"closed"` lines
     with zero data or billing mutation.
   - Live-environment DB grading & deterministic `ToolFault` injection (`#609`, `#610`):
     Reward is graded against `live_db_hash` / `live_user_db_hash` rather than replay,
     surfacing `replay_divergence` in `RewardInfo.info`; `timeout_before_commit` skips
     tool mutation while `timeout_after_commit` mutates live DB before returning timeout.
   - Language-binding task replacement verification & bridged GPT-5 `tool_choice` (`#615`, `#621`):
     `check_tasks` validates against the recorded language binding (`en` 50 reviewed
     same-ID replacements vs. 1.x registry); bridged `openai/responses/<model>` calls
     preserve `allowed_openai_params=["tool_choice"]` so `tool_choice="required"` is not
     silently dropped to `None`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Mapping, Sequence


UCP_REQ_ID_RE = re.compile(r"^REQ-[A-Z0-9-]+-[0-9]{2,}$")
UCP_HEX10_RE = re.compile(r"^[0-9a-f]{10}$")
UCP_COMPLETE_CHECKOUT_REQUIRED_EXTENSIONS: frozenset[str] = frozenset(
    {
        "dev.ucp.shopping.buyer_consent",
        "dev.ucp.common.payment.ap2_mandate",
    }
)

ACP_DELEGATE_REQUIRED_ALLOWANCE_FIELDS: frozenset[str] = frozenset(
    {"reason", "max_amount", "currency", "merchant_id", "expires_at"}
)
ACP_KNOWN_ERROR_TYPES: frozenset[str] = frozenset(
    {
        "invalid_request",
        "rate_limit_exceeded",
        "processing_error",
        "service_unavailable",
        "unauthorized",
        "internal_server_error",
    }
)
ACP_KNOWN_ERROR_CODES: frozenset[str] = frozenset(
    {
        "invalid_card",
        "expired_card",
        "insufficient_funds",
        "rate_limit_exceeded",
        "unauthorized",
        "internal_server_error",
        "service_unavailable",
    }
)
ACP_VALID_ORDER_STATUSES: frozenset[str] = frozenset(
    {"created", "confirmed", "shipped", "fulfilled", "delivered", "canceled"}
)

AP2_HARDCODED_FALLBACK_AMOUNT_CENTS = 1250
LATAM_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CUIT", re.compile(r"\b\d{2}-\d{8}-\d\b")),
    ("RFC", re.compile(r"\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
)


@dataclass(frozen=True)
class UcpCartCompleteAuthRequirementsGuardResult:
    """Result of validating UCP PRs #911, #910, #907, #906, #883, and #853."""

    allowed: bool
    cart_conversion_valid: bool
    signature_ucp_agent_covered: bool
    embedded_auth_type_valid: bool
    mcp_complete_extensions_valid: bool
    requirements_catalog_valid: bool
    computed_content_digest: str
    error_codes: tuple[str, ...] = field(default_factory=tuple)
    remediation: str = ""


@dataclass(frozen=True)
class AcpStoreOfferOrderDelegateGuardResult:
    """Result of validating ACP PRs #230, #171, #165, #162, and #161."""

    allowed: bool
    delegate_allowance_valid: bool
    delegate_error_forward_compatible: bool
    normalized_error_category: str
    store_extension_valid: bool
    time_bound_offer_valid: bool
    order_status_valid: bool
    derived_message_code: str
    error_codes: tuple[str, ...] = field(default_factory=tuple)
    remediation: str = ""


@dataclass(frozen=True)
class Ap2ClosedBindingX402TrustBoostGuardResult:
    """Result of validating Google AP2 PRs #330, #310, #300, and #267."""

    allowed: bool
    closed_checkout_binding_verified: bool
    psp_key_fail_closed_verified: bool
    authorized_amount_cents: int
    pii_sanitized_verified: bool
    detected_unredacted_pii_types: tuple[str, ...] = field(default_factory=tuple)
    error_codes: tuple[str, ...] = field(default_factory=tuple)
    remediation: str = ""


@dataclass(frozen=True)
class Tau2TelecomLiveDbFaultCliGuardResult:
    """Result of validating Sierra tau2-bench PRs #611, #610, #609, #615, and #621."""

    allowed: bool
    telecom_refuel_valid: bool
    updated_data_gb: float
    updated_bill_usd: float
    live_db_reward_passed: bool
    replay_divergence_detected: bool
    language_pack_verified: bool
    gpt5_tool_choice_preserved: bool
    effective_tool_choice: str
    error_codes: tuple[str, ...] = field(default_factory=tuple)
    remediation: str = ""


def compute_ucp_requirement_digest(
    capability: str,
    list_stem: str,
    normalized_text: str,
) -> str:
    """Compute the 10-hex SHA-256 content digest per UCP PR #853."""
    payload = f"{capability.strip()}|{list_stem.strip()}|{' '.join(normalized_text.strip().split())}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]


def validate_ucp_cart_complete_auth_requirements_guard(
    *,
    checkout_operation: str,
    checkout_payload: Mapping[str, Any],
    cart_id_ucp_request_map: Mapping[str, str] | None = None,
    has_ucp_agent_header: bool = True,
    signature_input_covered_components: Sequence[str] = ("@method", "@target-uri", "content-digest", "ucp-agent"),
    embedded_auth_method: str = "ec.auth",
    embedded_auth_type_required_in_openrpc: bool = True,
    embedded_auth_type_value: str | None = "oauth2",
    mcp_complete_supported_extensions: Sequence[str] = (
        "dev.ucp.shopping.buyer_consent",
        "dev.ucp.common.payment.ap2_mandate",
    ),
    requirement_record: Mapping[str, Any] | None = None,
    extraction_counts: Mapping[str, int] | None = None,
) -> UcpCartCompleteAuthRequirementsGuardResult:
    """Validate UCP PRs #911, #910, #907, #906, #883, and #853."""
    errors: list[str] = []
    remediations: list[str] = []

    op = checkout_operation.strip().lower()
    cart_conversion_valid = True

    # 1. PR #911 / #871 & PR #910: cart_id omitted on complete_checkout; line_items required on create_checkout
    if cart_id_ucp_request_map is not None:
        complete_rule = str(cart_id_ucp_request_map.get("complete", "include")).strip().lower()
        if complete_rule != "omit":
            cart_conversion_valid = False
            errors.append("ucp_cart_id_schema_missing_complete_omit")
            remediations.append(
                'Set `"complete": "omit"` on `cart_id.ucp_request` in `shopping/cart.json#/$defs/checkout` (PR #911).'
            )

    if op == "complete_checkout" and "cart_id" in checkout_payload:
        cart_conversion_valid = False
        errors.append("ucp_cart_id_forbidden_on_complete_checkout")
        remediations.append(
            "Omit `cart_id` on `complete_checkout` requests; `cart_id` is only valid during cart-to-checkout conversion (PR #911/#871)."
        )

    if op == "create_checkout" and "cart_id" in checkout_payload:
        if "line_items" not in checkout_payload or not isinstance(checkout_payload.get("line_items"), list):
            cart_conversion_valid = False
            errors.append("ucp_line_items_required_on_cart_conversion")
            remediations.append(
                'Pass `"line_items": []` when converting a cart via `cart_id` on `create_checkout` because `allOf` inherits `line_items` as required (PR #910).'
            )

    # 2. PR #907: UCP-Agent header must be covered in Signature-Input
    normalized_covered = {c.strip().lower() for c in signature_input_covered_components}
    signature_ucp_agent_covered = True
    if has_ucp_agent_header and "ucp-agent" not in normalized_covered:
        signature_ucp_agent_covered = False
        errors.append("ucp_signature_coverage_insufficient_ucp_agent")
        remediations.append(
            'Include `"ucp-agent"` in `Signature-Input` covered components whenever the request carries a `UCP-Agent` header (PR #907).'
        )

    # 3. PR #906 & PR #883: OpenRPC embedded auth `type` required & MCP complete_checkout extensions
    embedded_auth_type_valid = True
    if embedded_auth_method in {"ec.auth", "ep.cart.auth"}:
        if not embedded_auth_type_required_in_openrpc:
            embedded_auth_type_valid = False
            errors.append("ucp_openrpc_embedded_auth_type_not_marked_required")
            remediations.append(
                'Mark `type` param with `"required": true` on `ec.auth` and `ep.cart.auth` in `embedded.openrpc.json` (PR #906).'
            )
        if not isinstance(embedded_auth_type_value, str) or not embedded_auth_type_value.strip():
            embedded_auth_type_valid = False
            errors.append("ucp_embedded_auth_missing_type_param")
            remediations.append(
                "Supply a non-empty `type` string when invoking `ec.auth` or `ep.cart.auth` (PR #906)."
            )

    ext_set = {e.strip() for e in mcp_complete_supported_extensions if isinstance(e, str)}
    mcp_complete_extensions_valid = UCP_COMPLETE_CHECKOUT_REQUIRED_EXTENSIONS.issubset(ext_set)
    if not mcp_complete_extensions_valid:
        errors.append("ucp_mcp_complete_checkout_missing_extensions")
        remediations.append(
            "Expose both `dev.ucp.shopping.buyer_consent` and `dev.ucp.common.payment.ap2_mandate` under MCP `complete_checkout` (PR #883)."
        )

    # 4. PR #853: Requirements extractor catalog record & clause reconciliation
    requirements_catalog_valid = True
    computed_digest = ""
    if requirement_record is not None:
        req_id = str(requirement_record.get("id", "")).strip()
        capability = str(requirement_record.get("capability", "dev.ucp.shopping.checkout")).strip()
        list_stem = str(requirement_record.get("list_stem", "")).strip()
        clause = str(requirement_record.get("clause", "")).strip()
        provided_digest = str(requirement_record.get("content_digest", "")).strip()
        computed_digest = compute_ucp_requirement_digest(capability, list_stem, clause)

        if not UCP_REQ_ID_RE.match(req_id) or len(req_id) > 42:
            requirements_catalog_valid = False
            errors.append("ucp_requirement_id_invalid_format")
            remediations.append(
                "Format requirement IDs to match `^REQ-[A-Z0-9-]+-[0-9]{2,}$` with max length 42 (PR #853)."
            )
        if not UCP_HEX10_RE.match(provided_digest) or (
            requirement_record.get("verify_digest_match", False) and provided_digest != computed_digest
        ):
            requirements_catalog_valid = False
            errors.append("ucp_requirement_content_digest_mismatch")
            remediations.append(
                "Ensure `content_digest` is the 10-hex SHA-256 of `(capability, list_stem, normalized_text)` (PR #853)."
            )

    if extraction_counts is not None:
        bolded = int(extraction_counts.get("bolded_obligations", 0))
        unbolded = int(extraction_counts.get("unbolded_reported", 0))
        annotations = int(extraction_counts.get("schema_annotation_only", 0))
        total = int(extraction_counts.get("total_keyword_clauses", 0))
        if bolded + unbolded + annotations != total or total <= 0:
            requirements_catalog_valid = False
            errors.append("ucp_requirements_extraction_reconciliation_failed")
            remediations.append(
                "Reconcile extracted bolded obligations + unbolded reported + schema-annotation clauses to equal total RFC 2119 keyword clauses (PR #853)."
            )

    return UcpCartCompleteAuthRequirementsGuardResult(
        allowed=len(errors) == 0,
        cart_conversion_valid=cart_conversion_valid,
        signature_ucp_agent_covered=signature_ucp_agent_covered,
        embedded_auth_type_valid=embedded_auth_type_valid,
        mcp_complete_extensions_valid=mcp_complete_extensions_valid,
        requirements_catalog_valid=requirements_catalog_valid,
        computed_content_digest=computed_digest,
        error_codes=tuple(errors),
        remediation=" ".join(remediations),
    )


def _parse_rfc3339_utc(ts: str) -> datetime:
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_acp_store_offer_order_delegate_guard(
    *,
    allowance_payload: Mapping[str, Any],
    delegate_error_payload: Mapping[str, Any] | None = None,
    strict_error_enum_rejection: bool = False,
    checkout_operation: str = "create",
    request_has_store_id: bool = False,
    response_store: Mapping[str, Any] | None = None,
    store_query_limit: int = 20,
    store_query_radius_km: float = 50.0,
    now_iso: str = "2026-10-20T12:00:00Z",
    session_quote_expires_at: str | None = "2026-10-20T12:30:00Z",
    line_item_valid_until: str | None = "2026-10-20T12:15:00Z",
    line_item_availability_status: str = "offer_valid",
    session_status: str = "ready_for_payment",
    emitted_message_codes: Sequence[str] = (),
    fulfillment_type: str = "shipping",
    order_status: str = "shipped",
) -> AcpStoreOfferOrderDelegateGuardResult:
    """Validate ACP PRs #230, #171, #165, #162, and #161."""
    errors: list[str] = []
    remediations: list[str] = []

    # 1. PR #230: allowance.checkout_session_id is optional, but core 5 fields required
    missing_allowance = [
        f for f in sorted(ACP_DELEGATE_REQUIRED_ALLOWANCE_FIELDS) if f not in allowance_payload or allowance_payload.get(f) in (None, "")
    ]
    delegate_allowance_valid = len(missing_allowance) == 0
    if "checkout_session_id" in allowance_payload and allowance_payload.get("checkout_session_id") == "":
        delegate_allowance_valid = False
        errors.append("acp_delegate_allowance_empty_checkout_session_id")
        remediations.append(
            "Omit `allowance.checkout_session_id` when unused rather than passing an empty string (ACP PR #230)."
        )
    if missing_allowance:
        errors.append("acp_delegate_allowance_missing_required_fields")
        remediations.append(
            f"Provide required allowance fields ({', '.join(missing_allowance)}); only `checkout_session_id` is optional (ACP PR #230)."
        )

    # 2. PR #161: Delegate Payment Error enums (401/500/503) & forward compatibility
    delegate_error_forward_compatible = True
    normalized_error_category = "none"
    if delegate_error_payload is not None:
        err_type = str(delegate_error_payload.get("type", "")).strip()
        err_code = str(delegate_error_payload.get("code", "")).strip()
        if not err_type or not err_code:
            delegate_error_forward_compatible = False
            errors.append("acp_delegate_error_missing_type_or_code")
            remediations.append("Include non-empty `type` and `code` in Delegate Payment Error responses (ACP PR #161).")
        elif strict_error_enum_rejection and (
            err_type not in ACP_KNOWN_ERROR_TYPES or err_code not in ACP_KNOWN_ERROR_CODES
        ):
            delegate_error_forward_compatible = False
            errors.append("acp_delegate_error_strict_enum_rejection_forbidden")
            remediations.append(
                "Do not reject unrecognized future Delegate Payment Error `type`/`code` values; fall back to generic error handling per RFC §4.2 (ACP PR #161)."
            )
        else:
            if err_type in ACP_KNOWN_ERROR_TYPES and err_code in ACP_KNOWN_ERROR_CODES:
                normalized_error_category = f"known:{err_type}:{err_code}"
            else:
                normalized_error_category = f"fallback_generic:{err_type}:{err_code}"

    # 3. PR #171: Store Extension for BOPIS and In-Store Shopping
    store_extension_valid = True
    op = checkout_operation.strip().lower()
    if op == "complete" and request_has_store_id:
        store_extension_valid = False
        errors.append("acp_store_id_forbidden_on_checkout_complete")
        remediations.append(
            "Exclude `store_id` from `CheckoutSessionCompleteRequest` to avoid mid-payment inventory/tax recalculation races; update store via `CheckoutSessionUpdateRequest` first (ACP PR #171)."
        )
    if response_store is not None:
        store_id_val = str(response_store.get("id", "")).strip()
        store_name_val = str(response_store.get("name", "")).strip()
        if not store_id_val or not store_name_val:
            store_extension_valid = False
            errors.append("acp_store_response_missing_id_or_name")
            remediations.append("Include required `id` and `name` fields in `CheckoutSession.store` (ACP PR #171).")
    if store_query_limit < 1 or store_query_limit > 100 or store_query_radius_km <= 0:
        store_extension_valid = False
        errors.append("acp_store_discovery_invalid_query_bounds")
        remediations.append(
            "Enforce `1 <= limit <= 100` (default 20) and `radius > 0` km on `GET /stores` proximity search (ACP PR #171)."
        )

    # 4. PR #165: Time-bound offer expiry (valid_until, offer_valid/offer_expired, offer_expired vs quote_expired)
    time_bound_offer_valid = True
    derived_message_code = "none"
    now_dt = _parse_rfc3339_utc(now_iso)
    quote_expired = False
    line_expired = False

    if session_quote_expires_at:
        quote_dt = _parse_rfc3339_utc(session_quote_expires_at)
        quote_expired = now_dt >= quote_dt
    if line_item_valid_until:
        line_dt = _parse_rfc3339_utc(line_item_valid_until)
        line_expired = now_dt >= line_dt

    msg_codes = {m.strip() for m in emitted_message_codes}
    if quote_expired:
        derived_message_code = "quote_expired"
        if "quote_expired" not in msg_codes or session_status == "ready_for_payment":
            time_bound_offer_valid = False
            errors.append("acp_quote_expired_not_enforced")
            remediations.append(
                'Emit `MessageError.code = "quote_expired"` and block payment readiness when `quote_expires_at` has passed (ACP PR #165).'
            )
    elif line_expired:
        derived_message_code = "offer_expired"
        if (
            line_item_availability_status != "offer_expired"
            or "offer_expired" not in msg_codes
            or session_status == "ready_for_payment"
        ):
            time_bound_offer_valid = False
            errors.append("acp_line_item_offer_expired_not_enforced")
            remediations.append(
                'Set `availability_status: "offer_expired"`, `status: "not_ready_for_payment"`, and emit `MessageError.code = "offer_expired"` when `LineItem.valid_until` is past (ACP PR #165).'
            )
    else:
        if line_item_valid_until and line_item_availability_status == "offer_expired":
            time_bound_offer_valid = False
            errors.append("acp_premature_offer_expired_status")
            remediations.append(
                'Keep `availability_status: "offer_valid"` while `LineItem.valid_until` is still in the future (ACP PR #165).'
            )

    # 5. PR #162: Order status semantics (shipped vs fulfilled vs delivered across shipping/digital)
    order_status_valid = True
    norm_status = order_status.strip().lower()
    norm_fulfillment = fulfillment_type.strip().lower()
    if norm_status not in ACP_VALID_ORDER_STATUSES:
        order_status_valid = False
        errors.append("acp_order_status_unknown")
        remediations.append("Use a valid ACP order status (`created`, `confirmed`, `shipped`, `fulfilled`, `delivered`, `canceled`) (ACP PR #162).")
    elif norm_fulfillment == "digital" and norm_status in {"shipped", "delivered"}:
        order_status_valid = False
        errors.append("acp_digital_order_forbidden_shipped_status")
        remediations.append(
            "Do not use `shipped` or physical `delivered` on digital-only orders; progress directly `confirmed -> fulfilled` (ACP PR #162)."
        )

    return AcpStoreOfferOrderDelegateGuardResult(
        allowed=len(errors) == 0,
        delegate_allowance_valid=delegate_allowance_valid,
        delegate_error_forward_compatible=delegate_error_forward_compatible,
        normalized_error_category=normalized_error_category,
        store_extension_valid=store_extension_valid,
        time_bound_offer_valid=time_bound_offer_valid,
        order_status_valid=order_status_valid,
        derived_message_code=derived_message_code,
        error_codes=tuple(errors),
        remediation=" ".join(remediations),
    )


def validate_ap2_closed_binding_x402_trustboost_guard(
    *,
    expected_open_checkout_hash: str,
    actual_open_checkout_hash: str,
    closed_mandate_transaction_id: str | None,
    expected_checkout_jwt_hash: str | None,
    agent_provider_pub: str | None,
    mandate_signature_valid: bool = True,
    verified_mandate_amount_cents: int | None = 4800,
    proposed_eip3009_amount_cents: int = 4800,
    payload_text: str = "Order summary for customer [REDACTED_CPF]",
    x402_payment_settled: bool = True,
    solana_anchor_tx: str | None = "5xTrustBoostAnchorTxProof998",
) -> Ap2ClosedBindingX402TrustBoostGuardResult:
    """Validate Google AP2 PRs #330, #310, #300, and #267."""
    errors: list[str] = []
    remediations: list[str] = []

    # 1. AP2 PR #330: Closed checkout-binding in PaymentMandateChain.verify()
    closed_checkout_binding_verified = True
    if not expected_open_checkout_hash or expected_open_checkout_hash != actual_open_checkout_hash:
        closed_checkout_binding_verified = False
        errors.append("ap2_open_checkout_hash_mismatch")
        remediations.append("Verify `expected_open_checkout_hash` matches the open mandate checkout hash (AP2 PR #330).")
    if (
        not closed_mandate_transaction_id
        or not expected_checkout_jwt_hash
        or closed_mandate_transaction_id.strip() != expected_checkout_jwt_hash.strip()
    ):
        closed_checkout_binding_verified = False
        errors.append("ap2_closed_mandate_checkout_binding_unverified")
        remediations.append(
            "Fail closed in `PaymentMandateChain.verify()` unless the closed Payment Mandate `transaction_id` matches the expected Checkout JWT binding (AP2 PR #330)."
        )

    # 2. AP2 PR #310: Fail closed in x402 PSP when agent-provider public key is missing
    psp_key_fail_closed_verified = True
    if not isinstance(agent_provider_pub, str) or not agent_provider_pub.strip():
        psp_key_fail_closed_verified = False
        errors.append("agent_provider_key_missing")
        remediations.append(
            "Return `agent_provider_key_missing` immediately in `x402_psp_mcp.settle_payment` when `agent_provider_pub` cannot be loaded (AP2 PR #310)."
        )
    elif not mandate_signature_valid:
        psp_key_fail_closed_verified = False
        errors.append("mandate_verification_failed")
        remediations.append("Reject malformed or unsigned SD-JWT mandates in `settle_payment` (AP2 PR #310).")

    # 3. AP2 PR #300: Authorize the verified mandate amount in x402 credential provider (never fallback to 1250)
    authorized_amount_cents = 0
    if verified_mandate_amount_cents is None or verified_mandate_amount_cents <= 0:
        errors.append("verification_failed_missing_payment_amount")
        remediations.append(
            "Fail closed when `closed_mandate.payment_amount.amount` is missing rather than substituting a hardcoded fallback amount (AP2 PR #300)."
        )
    elif proposed_eip3009_amount_cents != verified_mandate_amount_cents:
        if proposed_eip3009_amount_cents == AP2_HARDCODED_FALLBACK_AMOUNT_CENTS:
            errors.append("ap2_x402_hardcoded_1250_amount_fallback_detected")
        else:
            errors.append("ap2_x402_authorized_amount_mismatch")
        remediations.append(
            "Sign EIP-3009 authorization for the exact verified `closed_mandate.payment_amount.amount`, never a hardcoded `1250` fallback (AP2 PR #300)."
        )
    else:
        authorized_amount_cents = verified_mandate_amount_cents

    # 4. AP2 PR #267: TrustBoost PII sanitization + HTTP 402 x402 settlement + Solana anchor proof
    detected_pii: list[str] = []
    for pii_label, pattern in LATAM_PII_PATTERNS:
        if pattern.search(payload_text):
            detected_pii.append(pii_label)

    pii_sanitized_verified = True
    if detected_pii:
        pii_sanitized_verified = False
        errors.append("ap2_trustboost_unredacted_pii_in_payload")
        remediations.append(
            f"Sanitize PII ({', '.join(detected_pii)}) via TrustBoost `/sanitize` before forwarding autonomous agent payloads to LLMs or merchants (AP2 PR #267)."
        )
    if not x402_payment_settled or not isinstance(solana_anchor_tx, str) or not solana_anchor_tx.strip():
        pii_sanitized_verified = False
        errors.append("ap2_trustboost_missing_x402_or_anchor_proof")
        remediations.append(
            "Complete HTTP 402 x402 USDC settlement and verify the Solana `anchor_tx` proof for PII sanitization (AP2 PR #267)."
        )

    return Ap2ClosedBindingX402TrustBoostGuardResult(
        allowed=len(errors) == 0,
        closed_checkout_binding_verified=closed_checkout_binding_verified,
        psp_key_fail_closed_verified=psp_key_fail_closed_verified,
        authorized_amount_cents=authorized_amount_cents,
        pii_sanitized_verified=pii_sanitized_verified,
        detected_unredacted_pii_types=tuple(detected_pii),
        error_codes=tuple(errors),
        remediation=" ".join(remediations),
    )


def validate_tau2_telecom_livedb_fault_cli_guard(
    *,
    line_status: str = "active",
    line_owned_by_customer: bool = True,
    refuel_amount_gb: float = 2.0,
    initial_data_gb: float = 5.0,
    initial_bill_usd: float = 40.0,
    rate_per_gb_usd: float = 5.0,
    attempted_mutation_on_inactive: bool = False,
    live_db_hash: str = "sha256:live_after_commit_abc",
    expected_target_db_hash: str = "sha256:live_after_commit_abc",
    replayed_db_hash: str = "sha256:live_after_commit_abc",
    reward_graded_from: str = "live",
    injected_tool_fault: str = "none",
    tool_mutated_live_db: bool = True,
    recorded_language: str | None = "en",
    verified_against_pack_tasks: bool = True,
    is_bridged_gpt5_responses_call: bool = True,
    allowed_openai_params: Sequence[str] = ("tool_choice",),
    requested_tool_choice: str = "required",
    sent_tool_choice: str | None = "required",
) -> Tau2TelecomLiveDbFaultCliGuardResult:
    """Validate Sierra tau2-bench PRs #611, #610, #609, #615, and #621."""
    errors: list[str] = []
    remediations: list[str] = []

    # 1. PR #611: Active telecom line guard before data refueling
    norm_line_status = line_status.strip().lower()
    telecom_refuel_valid = True
    updated_data_gb = initial_data_gb
    updated_bill_usd = initial_bill_usd

    if norm_line_status != "active":
        if attempted_mutation_on_inactive:
            telecom_refuel_valid = False
            errors.append("tau2_telecom_inactive_line_refuel_mutation")
            remediations.append(
                f"Block `refuel_data` on `{norm_line_status}` telecom lines and leave data allowance and customer bill unchanged (tau2-bench PR #611)."
            )
    elif not line_owned_by_customer or refuel_amount_gb <= 0:
        if attempted_mutation_on_inactive:
            telecom_refuel_valid = False
            errors.append("tau2_telecom_invalid_refuel_request")
            remediations.append("Verify customer line ownership and positive `refuel_amount_gb` before mutating telecom DB (tau2-bench PR #611).")
    else:
        updated_data_gb = round(initial_data_gb + refuel_amount_gb, 4)
        updated_bill_usd = round(initial_bill_usd + refuel_amount_gb * rate_per_gb_usd, 4)

    # 2. PR #609 & PR #610: Grade DB check against live environment & deterministic ToolFault semantics
    replay_divergence_detected = live_db_hash.strip() != replayed_db_hash.strip()
    live_db_reward_passed = live_db_hash.strip() == expected_target_db_hash.strip()

    if reward_graded_from.strip().lower() != "live":
        errors.append("tau2_db_check_graded_from_replay_instead_of_live")
        remediations.append(
            "Grade environment DB reward against `live_db_hash` / `live_user_db_hash` and record replay differences as `replay_divergence` in `RewardInfo.info` (tau2-bench PR #609)."
        )

    fault_mode = injected_tool_fault.strip().lower()
    if fault_mode == "timeout_before_commit" and tool_mutated_live_db:
        errors.append("tau2_tool_fault_timeout_before_commit_mutated_db")
        remediations.append(
            "`timeout_before_commit` must skip the tool execution and leave the live database unmutated (tau2-bench PR #610)."
        )
    elif fault_mode == "timeout_after_commit" and not tool_mutated_live_db:
        errors.append("tau2_tool_fault_timeout_after_commit_skipped_mutation")
        remediations.append(
            "`timeout_after_commit` must execute the tool mutation on the live database before returning the timeout fault (tau2-bench PR #610)."
        )

    # 3. PR #615: Verify trajectory tasks against recorded language binding (e.g., `en` pack replacements)
    language_pack_verified = True
    if recorded_language and recorded_language.strip().lower() == "en" and not verified_against_pack_tasks:
        language_pack_verified = False
        errors.append("tau2_en_trajectory_verified_against_stale_registry_tasks")
        remediations.append(
            "Compare results with a recorded language binding against that language pack's reviewed task replacements rather than 1.x base registry tasks (tau2-bench PR #615)."
        )

    # 4. PR #621: Keep `tool_choice` on bridged GPT-5 Responses calls via `allowed_openai_params=["tool_choice"]`
    gpt5_tool_choice_preserved = True
    effective_tool_choice = sent_tool_choice or "none"
    if is_bridged_gpt5_responses_call:
        allowed_params_set = {p.strip() for p in allowed_openai_params}
        if "tool_choice" not in allowed_params_set or sent_tool_choice != requested_tool_choice:
            gpt5_tool_choice_preserved = False
            errors.append("tau2_gpt5_bridged_call_dropped_tool_choice")
            remediations.append(
                'Pass `allowed_openai_params=["tool_choice"]` on bridged `openai/responses/<model>` calls so `tool_choice` is not silently dropped to `None` (tau2-bench PR #621).'
            )

    return Tau2TelecomLiveDbFaultCliGuardResult(
        allowed=len(errors) == 0,
        telecom_refuel_valid=telecom_refuel_valid,
        updated_data_gb=updated_data_gb,
        updated_bill_usd=updated_bill_usd,
        live_db_reward_passed=live_db_reward_passed,
        replay_divergence_detected=replay_divergence_detected,
        language_pack_verified=language_pack_verified,
        gpt5_tool_choice_preserved=gpt5_tool_choice_preserved,
        effective_tool_choice=effective_tool_choice,
        error_codes=tuple(errors),
        remediation=" ".join(remediations),
    )
