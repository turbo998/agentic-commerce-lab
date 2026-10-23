"""Stage 178 deterministic guard module for 2026-10-23 UCP, x402 & MCP updates.

Covers:
1. Google UCP PR #988 (`2026-10-23T16:49:17Z`), PR #584 (`2026-10-23T16:15:03Z`)
   & PR #791 (`2026-10-23T16:15:06Z`):
   - Order MCP message signing (`get_order` request signature & signed response
     binding)
   - `order.payment.instruments[]` (`order_payment_instrument` read-only subset:
     requires `id` & `type`, allows `amount`/`billing_address`/`display`, and
     forbids checkout collection-time fields `credential`, `handler_id`,
     `selected`)
   - Payment handler participant identifier (`identity.access_token` mapped to
     `config.business_id`, forbidden as Tokenizer authentication per
     `tokenization.md` Binding rule 4).
2. x402 Foundation PR #3656 (`2026-10-23T16:58:16Z`):
   - `extensions.reviews` specification: `1..4` `providers[]`, `provider` host
     must match `read`/`write` URL host, inline `rating`/`count` self-claims
     forbidden in 402 responses, payment-backed review requires `payer != payTo`
     and non-fund-moving signature.
3. x402 Foundation PR #3881 & #3877 (`2026-10-23T16:18:24Z`), PR #2728
   (`2026-10-23T16:34:08Z`), PR #3883 (`2026-10-23T16:13:47Z`) & PR #3508/#3911
   (`2026-10-23T16:34:33Z`):
   - `resolve_settlement_override_amount` ceiling against
     `PaymentRequirements.amount` (`invalid_settlement_override` on raw,
     percent, or dollar override above authorized maximum)
   - EIP-3009 plain 65-byte ECDSA low-s canonical check (`s <= secp256k1_n // 2`,
     `invalid_exact_evm_non_canonical_signature`, skipping ERC-1271/6492
     wrapper lengths)
   - Non-browser HTTP 402 JSON body `{"error": ...}` (`settlement_failed` on
     exception) and Python MCP paid tool `handle_payment_response` single
     corrective-402 retry ceiling.
4. Model Context Protocol SEP-3415 (`#3415` commit `b0efd11`
   `2026-10-23T14:59:13Z` & `2ec39b9`):
   - `Mcp-Name` header required on Streamable HTTP `events/poll`,
     `events/stream`, `events/subscribe`, and `events/unsubscribe`
   - `webhook-id` transport delivery ID decoupled from upstream `eventId`, with
     `eventId` deduplicated per `(subscriptionId, eventId)` so a single event
     matching two subscriptions reaches both, and `subscriptionId` echoed on
     every `notifications/events/*` message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_HALF_N = SECP256K1_N // 2

FORBIDDEN_ORDER_INSTRUMENT_FIELDS = frozenset(
    {"credential", "handler_id", "handler_reference", "selected", "selection_state"}
)
ALLOWED_ORDER_INSTRUMENT_FIELDS = frozenset(
    {"id", "type", "amount", "billing_address", "display"}
)
MCP_EVENTS_METHODS = frozenset(
    {"events/poll", "events/stream", "events/subscribe", "events/unsubscribe"}
)


def validate_ucp_order_mcp_signing_and_payment_instruments(
    *,
    mcp_tool: str,
    request_signature_valid: bool,
    response_signature_present: bool,
    require_signed_response: bool,
    order_payment_instruments: list[dict[str, Any]],
    tokenizer_auth_uses_identity_access_token: bool = False,
    handler_type: str = "processor-tokenizer",
    handler_config: dict[str, Any] | None = None,
) -> GuardDecision:
    """Validate UCP PR #988 Order MCP signing, PR #584 `order.payment.instruments`, and PR #791 participant ID rules."""
    if mcp_tool == "get_order" and not request_signature_valid:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_order_mcp_request_signature_invalid",
            reason="get_order over MCP requires a valid Message Signature per signatures.md#mcp-transport.",
        )
    if mcp_tool == "get_order" and require_signed_response and not response_signature_present:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_order_mcp_response_signature_missing",
            reason="Order MCP binding business conformance requires signing responses when enforced.",
        )

    if tokenizer_auth_uses_identity_access_token:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_tokenizer_identity_access_token_auth_forbidden",
            reason="Per tokenization.md Binding rule 4 and PR #791, identity.access_token is a participant identifier and MUST NOT be accepted as authentication.",
        )

    cfg = handler_config or {}
    if handler_type in {"processor-tokenizer", "platform-tokenizer"} and not cfg.get("business_id"):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_handler_config_business_id_missing",
            reason=f"{handler_type} configuration must publish business_id as the participant identifier.",
        )
    if handler_type == "encrypted-credential" and "identity" in cfg:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_encrypted_credential_identity_member_forbidden",
            reason="encrypted-credential handler implements neither /tokenize nor /detokenize and must use business_id + binding.json rather than payment_identity.json.",
        )

    if not order_payment_instruments:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_order_payment_instruments_empty",
            reason="order.payment.instruments must contain at least one order_payment_instrument entry.",
        )

    for idx, inst in enumerate(order_payment_instruments):
        leaked = set(inst.keys()) & FORBIDDEN_ORDER_INSTRUMENT_FIELDS
        if leaked:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_order_payment_collection_field_leaked",
                reason=f"order_payment_instrument[{idx}] leaked checkout collection-time fields: {sorted(leaked)}.",
            )
        unknown = set(inst.keys()) - ALLOWED_ORDER_INSTRUMENT_FIELDS
        if unknown:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_order_payment_unknown_field",
                reason=f"order_payment_instrument[{idx}] contains unsupported fields: {sorted(unknown)}.",
            )
        if not inst.get("id") or not inst.get("type"):
            return GuardDecision(
                allowed=False,
                decision_code="ucp_order_payment_required_id_or_type_missing",
                reason=f"order_payment_instrument[{idx}] requires non-empty 'id' and 'type'.",
            )

    return GuardDecision(
        allowed=True,
        decision_code="ucp_order_mcp_and_payment_instruments_ok",
        reason="UCP PR #988 Order MCP signing, PR #584 order_payment_instrument read-only subset, and PR #791 participant ID verified.",
        metadata={"instrument_count": len(order_payment_instruments)},
    )


def validate_x402_reviews_extension(
    *,
    phase: str,
    providers: list[dict[str, Any]],
    payer: str = "",
    pay_to: str = "",
    payment_settled: bool = True,
    review_signature_moves_funds: bool = False,
) -> GuardDecision:
    """Validate x402 PR #3656 `extensions.reviews` specification."""
    if not (1 <= len(providers) <= 4):
        return GuardDecision(
            allowed=False,
            decision_code="x402_reviews_provider_count_out_of_bounds",
            reason=f"extensions.reviews.providers[] must contain 1 to 4 entries (got {len(providers)}).",
        )

    url_key = "read" if phase == "402" else "write"
    for idx, entry in enumerate(providers):
        if "rating" in entry or "count" in entry or "score" in entry:
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_self_claimed_rating_forbidden",
                reason=f"providers[{idx}] carries inline rating/count/score; x402 reviews extension carries links only to prevent server self-claims.",
            )
        provider_host = str(entry.get("provider", "")).strip().lower()
        link_url = str(entry.get(url_key, "")).strip()
        if not provider_host or not link_url:
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_provider_or_link_missing",
                reason=f"providers[{idx}] requires 'provider' host and '{url_key}' link.",
            )
        parsed = urlparse(link_url)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != provider_host:
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_provider_host_mismatch",
                reason=f"providers[{idx}] provider '{provider_host}' MUST equal the HTTPS host of '{link_url}'.",
            )

    if phase == "post_payment":
        if not payment_settled or not payer or not pay_to:
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_unsettled_payment_rejected",
                reason="Payment-backed review requires verified settlement from payer to payTo.",
            )
        if payer.lower() == pay_to.lower():
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_self_dealing_payer_equals_payto",
                reason="Payment-backed review rejects self-dealing where payer == payTo.",
            )
        if review_signature_moves_funds:
            return GuardDecision(
                allowed=False,
                decision_code="x402_reviews_fund_moving_signature_forbidden",
                reason="Review signature message MUST NOT be capable of moving funds.",
            )

    return GuardDecision(
        allowed=True,
        decision_code="x402_reviews_extension_ok",
        reason="x402 PR #3656 reviews extension providers, host binding, and payment-backed anti-self-dealing verified.",
        metadata={"provider_count": len(providers), "phase": phase},
    )


def validate_x402_settlement_override_and_low_s_and_mcp(
    *,
    authorized_amount_atomic: int,
    override_value: str | int | None = None,
    token_decimals: int = 6,
    signature_len_bytes: int = 65,
    ecdsa_s_int: int | None = None,
    payment_required_error: str | None = None,
    settlement_threw: bool = False,
    mcp_paid_tool_handled_via_callback: bool = True,
    mcp_corrective_402_retries: int = 0,
) -> GuardDecision:
    """Validate x402 PR #3881/#3877 settlement override ceiling, PR #2728 low-s EIP-3009, PR #3883 402 JSON body, and PR #3508 Python MCP paid response handling."""
    resolved_atomic = authorized_amount_atomic
    if override_value is not None:
        raw_str = str(override_value).strip()
        if raw_str.endswith("%"):
            pct = Decimal(raw_str[:-1])
            resolved_atomic = int((Decimal(authorized_amount_atomic) * pct) / Decimal(100))
        elif raw_str.startswith("$"):
            dollars = Decimal(raw_str[1:])
            resolved_atomic = int(dollars * (Decimal(10) ** token_decimals))
        else:
            resolved_atomic = int(raw_str)

        if resolved_atomic < 0 or resolved_atomic > authorized_amount_atomic:
            return GuardDecision(
                allowed=False,
                decision_code="invalid_settlement_override",
                reason=f"Settlement override ({resolved_atomic}) exceeds authorized PaymentRequirements.amount ({authorized_amount_atomic}).",
                metadata={"resolved_atomic": resolved_atomic},
            )

    if signature_len_bytes == 65 and ecdsa_s_int is not None:
        if ecdsa_s_int <= 0 or ecdsa_s_int > SECP256K1_HALF_N:
            return GuardDecision(
                allowed=False,
                decision_code="invalid_exact_evm_non_canonical_signature",
                reason="Plain 65-byte EIP-3009 ECDSA signature has non-canonical high-s > secp256k1_n / 2 (PR #2728).",
            )

    if not mcp_paid_tool_handled_via_callback:
        return GuardDecision(
            allowed=False,
            decision_code="x402_mcp_paid_response_handler_bypassed",
            reason="Python MCP client must dispatch paid tool results and retry responses through handle_payment_response (PR #3508).",
        )
    if mcp_corrective_402_retries > 1:
        return GuardDecision(
            allowed=False,
            decision_code="x402_mcp_corrective_402_retry_limit_exceeded",
            reason="Python MCP client permits at most a single corrective-402 recovery retry (PR #3508).",
        )

    http_402_body: dict[str, str] = {}
    if settlement_threw:
        http_402_body = {"error": "settlement_failed"}
    elif payment_required_error:
        http_402_body = {"error": payment_required_error}

    return GuardDecision(
        allowed=True,
        decision_code="x402_settlement_override_low_s_and_mcp_ok",
        reason="x402 PR #3881/#3877 override ceiling, PR #2728 low-s EIP-3009, PR #3883 402 error body, and PR #3508 MCP response handler verified.",
        metadata={
            "resolved_atomic": resolved_atomic,
            "http_402_body": http_402_body,
            "erc1271_wrapper_skipped": signature_len_bytes != 65,
        },
    )


def validate_mcp_sep3415_events_transport_and_dedup(
    *,
    method: str,
    mcp_name_header: str | None,
    deliveries: list[dict[str, str]],
) -> GuardDecision:
    """Validate MCP SEP-3415 (`#3415` commits `2ec39b9` & `b0efd11`) `Mcp-Name` header & `(subscriptionId, eventId)` deduplication."""
    if method in MCP_EVENTS_METHODS and not (mcp_name_header or "").strip():
        return GuardDecision(
            allowed=False,
            decision_code="mcp_events_mcp_name_header_missing",
            reason=f"SEP-3415 requires the Mcp-Name HTTP header on Streamable HTTP {method} requests.",
        )

    seen_per_subscription: set[tuple[str, str]] = set()
    accepted_deliveries: list[dict[str, str]] = []
    for idx, item in enumerate(deliveries):
        sub_id = str(item.get("subscription_id", "")).strip()
        event_id = str(item.get("event_id", "")).strip()
        webhook_id = str(item.get("webhook_id", "")).strip()
        if not sub_id or not event_id or not webhook_id:
            return GuardDecision(
                allowed=False,
                decision_code="mcp_events_subscription_or_ids_missing",
                reason=f"Delivery[{idx}] on notifications/events/* must echo subscription_id, event_id, and transport webhook_id.",
            )
        key = (sub_id, event_id)
        if key in seen_per_subscription:
            return GuardDecision(
                allowed=False,
                decision_code="mcp_events_within_subscription_duplicate_dropped",
                reason=f"Duplicate event_id '{event_id}' within subscription '{sub_id}' (webhook_id '{webhook_id}' retry) deduplicated.",
                metadata={"accepted_deliveries": accepted_deliveries},
            )
        seen_per_subscription.add(key)
        accepted_deliveries.append(item)

    return GuardDecision(
        allowed=True,
        decision_code="mcp_sep3415_events_ok",
        reason="MCP SEP-3415 Mcp-Name header and per-subscription eventId deduplication (decoupled from webhook-id) verified.",
        metadata={"accepted_count": len(accepted_deliveries)},
    )
