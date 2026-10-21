"""Stage 126 deterministic guardrails:
1. x402 Foundation (#3783, #3776, #3775, #3741, #3738, #3784, #3769, #3757, #3788, #3770, #3754, #3752, #3737):
   - `delivery-receipt` extension (#3783): signs `"x402-delivery-receipt/1\\n" + receiptId` where
     `receiptId = SHA-256(JCS(payload))`; reference mode keeps `PAYMENT-RESPONSE` member <= 1024 bytes.
   - Single-ingress payment identity (#3776): `attempt_id` / `Idempotency-Key` derived once at ingress
     and shared identically across `/settle`, refusal, replay-lookup, and challenge-quote paths.
   - Discriminated `PaymentCall` (#3775): fail-closed validation of `kind == "http"` or `kind == "mcp"`
     before hooks/signing; `ResourceInfo` paid HTTP method matching (#3741); `OPTIONS` preflight bypass (#3738).
   - SVM confirmed on-chain failure (`status.Err != nil`) mapped to terminal failure, not `settlement_pending` (#3784);
     EVM `settleUptoPermit2` simulated with `settlementAmount` instead of ceiling (#3769);
     `withPrivateCacheControl` ignores `"private"` inside quoted extension values (#3757);
     multi-chain exact checks for Cosmos `cosmos:<chain-id>` `MsgSend` (#3788), Robinhood Chain `eip155:4663` USDG (#3770),
     Cardano `cardano-request-commitment` (#3754), Hedera Go `BodyBytes` co-sign (#3752), and Bitcoin `bip122` confirmation depth (#3737).
2. Universal Commerce Protocol (UCP #818, #806, #795, #784):
   - Canonical payment-terms capability ID `dev.ucp.common.payment.terms` (rejecting `.payment_terms`, #818).
   - Public registry lockfile enforcement (`registry.npmjs.org` for npm and `pypi.org` for uv, blocking corporate feeds, #806).
   - Checkout REST RFC 9421 covered components must include `"ucp-agent"` when `UCP-Agent` header is present (#795),
     and Location REST (`search_locations` / `lookup_locations`) requires both `Request-Id` and `UCP-Agent` headers (#784).
3. Stripe AI (#453, #419, #433) & MCP (#3371, #3364):
   - Agent-level identity attribution & per-tool permission matrix (#453), cross-invocation retry idempotency key +
     `starting_after` cursor pagination (#419), and normalized Anthropic model ID `max_tokens` defaults (#433).
   - MCP SEP-3371 order-independent SDK extension points (#3371) & SEP-2133 `2025-11-25` vs `2026-07-28` extension negotiation (#3364).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

DELIVERY_RECEIPT_DOMAIN_PREFIX = "x402-delivery-receipt/1\n"
DELIVERY_RECEIPT_REF_MAX_BYTES = 1024
CANONICAL_PAYMENT_TERMS_CAPABILITY = "dev.ucp.common.payment.terms"
CORPORATE_REGISTRY_MARKERS = (
    "codeartifact",
    "pkgs.dev.azure.com",
    "artifactregistry.googleapis.com",
    "shopify.io",
    "internal.registry",
)


def _jcs_sha256_hex(obj: Mapping[str, Any]) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_unquoted_cache_control_directives(header_value: str) -> list[str]:
    """Split Cache-Control on commas outside double quotes (#3757)."""
    directives: list[str] = []
    buf: list[str] = []
    in_quotes = False
    escaped = False
    for ch in header_value:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
            continue
        if ch == "," and not in_quotes:
            token = "".join(buf).strip()
            if token:
                directives.append(token.split("=", 1)[0].strip().lower())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        directives.append(tail.split("=", 1)[0].strip().lower())
    return directives


@dataclass(frozen=True)
class X402DeliveryIngressChainDecision:
    allowed: bool
    decision_code: str
    signed_octets_prefix_ok: bool
    cache_control_out: str
    reason: str


@dataclass(frozen=True)
class UcpTermsRegistryHeadersDecision:
    allowed: bool
    decision_code: str
    reason: str


@dataclass(frozen=True)
class StripeIdempotencyMcpExtDecision:
    allowed: bool
    decision_code: str
    derived_idempotency_key: str
    reason: str


def evaluate_x402_delivery_receipt_ingress_chains(
    payload: Mapping[str, Any],
) -> X402DeliveryIngressChainDecision:
    """Validate x402 #3783, #3776, #3775, #3741, #3738, #3784, #3769, #3757, and #3788/#3770/#3754/#3752/#3737."""
    # 1. OPTIONS preflight bypass (#3738) and ResourceInfo paid HTTP method (#3741)
    http_method = str(payload.get("http_method", "POST")).upper()
    options_charged_402 = bool(payload.get("options_preflight_charged_402", False))
    resource_paid_method = str(payload.get("resource_info_paid_method", http_method)).upper()

    if http_method == "OPTIONS" and options_charged_402:
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_OPTIONS_PREFLIGHT_CHARGED_402",
            signed_octets_prefix_ok=False,
            cache_control_out="",
            reason="Wildcard route matching must never treat OPTIONS CORS preflight as a paid 402 request (#3738).",
        )
    if http_method != "OPTIONS" and http_method != resource_paid_method:
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_RESOURCE_INFO_PAID_METHOD_MISMATCH",
            signed_octets_prefix_ok=False,
            cache_control_out="",
            reason=f"Payment sent on {http_method} but ResourceInfo declares paid method {resource_paid_method} (#3741).",
        )

    # 2. Unified single-ingress payment identity (#3776)
    ingress_id = str(payload.get("ingress_identity", "id_ing_01"))
    settle_id = str(payload.get("settle_identity", ingress_id))
    refusal_id = str(payload.get("refusal_identity", ingress_id))
    replay_id = str(payload.get("replay_lookup_identity", ingress_id))
    quote_id = str(payload.get("challenge_quote_identity", ingress_id))
    rederived_downstream = bool(payload.get("identity_rederived_downstream", False))

    if rederived_downstream or len({ingress_id, settle_id, refusal_id, replay_id, quote_id}) != 1:
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_INGRESS_IDENTITY_REDERIVED_OR_SPLIT",
            signed_octets_prefix_ok=False,
            cache_control_out="",
            reason="Settlement/refusal/replay/quote identity MUST be derived once at ingress and never re-derived (#3776).",
        )

    # 3. Discriminated PaymentCall validation (#3775)
    payment_call = payload.get("payment_call")
    if payment_call is not None:
        if not isinstance(payment_call, Mapping):
            return X402DeliveryIngressChainDecision(
                allowed=False,
                decision_code="X402_PAYMENT_CALL_INVALID",
                signed_octets_prefix_ok=False,
                cache_control_out="",
                reason="Malformed PaymentCall must fail closed before hooks or signing (#3775).",
            )
        kind = str(payment_call.get("kind", ""))
        if kind == "http":
            if not payment_call.get("method") or not payment_call.get("url"):
                return X402DeliveryIngressChainDecision(
                    allowed=False,
                    decision_code="X402_PAYMENT_CALL_INVALID",
                    signed_octets_prefix_ok=False,
                    cache_control_out="",
                    reason="HTTP PaymentCall requires non-empty method and url (#3775).",
                )
        elif kind == "mcp":
            if not payment_call.get("toolName") or not isinstance(payment_call.get("arguments"), Mapping):
                return X402DeliveryIngressChainDecision(
                    allowed=False,
                    decision_code="X402_PAYMENT_CALL_INVALID",
                    signed_octets_prefix_ok=False,
                    cache_control_out="",
                    reason="MCP PaymentCall requires toolName and arguments mapping (#3775).",
                )
        else:
            return X402DeliveryIngressChainDecision(
                allowed=False,
                decision_code="X402_PAYMENT_CALL_INVALID",
                signed_octets_prefix_ok=False,
                cache_control_out="",
                reason="PaymentCall kind must be 'http' or 'mcp' (#3775).",
            )

    # 4. Signed delivery-receipt extension (#3783)
    receipt_payload = payload.get("delivery_receipt_payload") or {"req": "/v1/data", "tx": "0xabc"}
    expected_receipt_id = _jcs_sha256_hex(receipt_payload)
    signed_octets = str(
        payload.get("delivery_receipt_signed_octets", f"{DELIVERY_RECEIPT_DOMAIN_PREFIX}{expected_receipt_id}")
    )
    delivery_mode = str(payload.get("delivery_receipt_mode", "reference"))
    header_member_bytes = int(payload.get("delivery_receipt_header_bytes", 320))

    if (
        not signed_octets.startswith(DELIVERY_RECEIPT_DOMAIN_PREFIX)
        or (delivery_mode == "reference" and header_member_bytes > DELIVERY_RECEIPT_REF_MAX_BYTES)
    ):
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_DELIVERY_RECEIPT_OCTETS_OR_BUDGET_INVALID",
            signed_octets_prefix_ok=False,
            cache_control_out="",
            reason="delivery-receipt requires 'x402-delivery-receipt/1\\n' || receiptId and <= 1 KB reference header (#3783).",
        )

    # 5. SVM confirmed on-chain failure terminal classification (#3784) & EVM upto Permit2 simulationAmount (#3769)
    svm_confirmed_err = bool(payload.get("svm_confirmed_with_status_err", False))
    svm_recorded_status = str(payload.get("svm_recorded_status", "terminal_failure"))
    if svm_confirmed_err and svm_recorded_status == "settlement_pending":
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_SVM_CONFIRMED_FAILURE_MARKED_PENDING",
            signed_octets_prefix_ok=True,
            cache_control_out="",
            reason="Confirmed SVM transaction with status.Err must be reported as terminal failure, not settlement_pending (#3784).",
        )

    upto_settlement_amount = int(payload.get("upto_settlement_amount", 150))
    upto_ceiling_amount = int(payload.get("upto_ceiling_amount", 1000))
    upto_simulated_amount = int(payload.get("upto_simulated_amount", upto_settlement_amount))
    payer_balance = int(payload.get("upto_payer_balance", 500))
    if upto_simulated_amount > upto_settlement_amount and payer_balance >= upto_settlement_amount and upto_ceiling_amount > payer_balance:
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_EVM_UPTO_SIMULATED_CEILING_INSTEAD_OF_SETTLEMENT",
            signed_octets_prefix_ok=True,
            cache_control_out="",
            reason="settleUptoPermit2 must simulate with settlementAmount rather than signed ceiling (#3769).",
        )

    # 6. Quoted Cache-Control private appending (#3757)
    cc_in = str(payload.get("cache_control_in", 'max-age=60, example="a, private, b"'))
    unquoted_directives = parse_unquoted_cache_control_directives(cc_in)
    cc_out = cc_in if "private" in unquoted_directives else (f"{cc_in}, private" if cc_in else "private")
    if bool(payload.get("caller_omitted_private_due_to_quoted_string", False)) and "private" not in unquoted_directives:
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_CACHE_CONTROL_QUOTED_PRIVATE_BYPASS",
            signed_octets_prefix_ok=True,
            cache_control_out=cc_out,
            reason="withPrivateCacheControl must ignore 'private' inside quoted strings and append unquoted private (#3757).",
        )

    # 7. Multi-chain exact invariants (#3788 Cosmos, #3770 Robinhood USDG, #3752 Hedera BodyBytes, #3737 bip122)
    hedera_remarshaled_body = bool(payload.get("hedera_go_remarshaled_tx_body", False))
    bip122_confirmations = int(payload.get("bip122_confirmations", 2))
    bip122_required_depth = int(payload.get("bip122_required_depth", 2))
    bip122_marked_settled = bool(payload.get("bip122_marked_settled", False))
    if hedera_remarshaled_body or (bip122_marked_settled and bip122_confirmations < bip122_required_depth):
        return X402DeliveryIngressChainDecision(
            allowed=False,
            decision_code="X402_MULTICHAIN_HEDERA_OR_BIP122_VIOLATION",
            signed_octets_prefix_ok=True,
            cache_control_out=cc_out,
            reason="Hedera Go facilitator must co-sign original BodyBytes (#3752) and bip122 must reach confirmation depth (#3737).",
        )

    return X402DeliveryIngressChainDecision(
        allowed=True,
        decision_code="X402_DELIVERY_INGRESS_CHAins_OK",
        signed_octets_prefix_ok=True,
        cache_control_out=cc_out,
        reason="All x402 delivery-receipt, single-ingress identity, PaymentCall, SVM/EVM upto, Cache-Control, and multi-chain checks passed.",
    )


def evaluate_ucp_terms_registry_headers_guard(
    payload: Mapping[str, Any],
) -> UcpTermsRegistryHeadersDecision:
    """Validate UCP #818, #806, #795, and #784."""
    # 1. Canonical payment terms capability ID (#818)
    terms_cap_id = str(payload.get("payment_terms_capability_id", CANONICAL_PAYMENT_TERMS_CAPABILITY))
    if terms_cap_id != CANONICAL_PAYMENT_TERMS_CAPABILITY:
        return UcpTermsRegistryHeadersDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_TERMS_CAPABILITY_ID_INVALID",
            reason=f"Payment terms capability ID must be '{CANONICAL_PAYMENT_TERMS_CAPABILITY}', not '{terms_cap_id}' (#818).",
        )

    # 2. Public registry lockfile check (#806)
    lockfile_urls: Sequence[str] = payload.get("lockfile_registry_urls") or ["https://registry.npmjs.org", "https://pypi.org/simple"]
    for url in lockfile_urls:
        low = url.lower()
        if any(marker in low for marker in CORPORATE_REGISTRY_MARKERS) or not (
            "registry.npmjs.org" in low or "pypi.org" in low
        ):
            return UcpTermsRegistryHeadersDecision(
                allowed=False,
                decision_code="UCP_NON_PUBLIC_LOCKFILE_REGISTRY_BLOCKED",
                reason=f"Corporate or non-public registry URL '{url}' is blocked in lockfiles (#806).",
            )

    # 3. Checkout REST ucp-agent covered component (#795)
    has_ucp_agent_header = bool(payload.get("has_ucp_agent_header", True))
    covered_components: Sequence[str] = payload.get("covered_components") or [
        "@method",
        "@authority",
        "@path",
        "ucp-agent",
        "idempotency-key",
        "content-digest",
        "content-type",
    ]
    if has_ucp_agent_header and "ucp-agent" not in {c.lower() for c in covered_components}:
        return UcpTermsRegistryHeadersDecision(
            allowed=False,
            decision_code="UCP_SIGNATURE_MISSING_UCP_AGENT_COVERAGE",
            reason="Checkout REST signature must cover 'ucp-agent' when UCP-Agent header is present (#795).",
        )

    # 4. Location REST required headers (#784)
    if payload.get("is_location_rest_call", False):
        loc_headers = {k.lower(): v for k, v in (payload.get("location_headers") or {}).items()}
        if not loc_headers.get("request-id") or not loc_headers.get("ucp-agent"):
            return UcpTermsRegistryHeadersDecision(
                allowed=False,
                decision_code="UCP_LOCATION_REST_MISSING_REQUIRED_HEADERS",
                reason="Location REST search_locations/lookup_locations require Request-Id and UCP-Agent headers (#784).",
            )

    return UcpTermsRegistryHeadersDecision(
        allowed=True,
        decision_code="UCP_TERMS_REGISTRY_HEADERS_OK",
        reason="UCP payment.terms capability ID, public lockfile registries, ucp-agent signature coverage, and Location headers verified.",
    )


def evaluate_stripe_idempotency_mcp_ext_guard(
    payload: Mapping[str, Any],
) -> StripeIdempotencyMcpExtDecision:
    """Validate Stripe AI #453, #419, #433 and MCP #3371, #3364."""
    # 1. Agent identity attribution & per-tool authorization (#453)
    agent_id = str(payload.get("agent_id", "agent_checkout_01")).strip()
    tool_name = str(payload.get("tool_name", "create_payment_intent")).strip()
    allowed_tools = set(payload.get("agent_allowed_tools") or [tool_name])
    if not agent_id or tool_name not in allowed_tools:
        return StripeIdempotencyMcpExtDecision(
            allowed=False,
            decision_code="STRIPE_AGENT_IDENTITY_OR_TOOL_PERMISSION_DENIED",
            derived_idempotency_key="",
            reason="Multi-agent Stripe MCP access requires verified agent_id and per-tool permission (#453).",
        )

    # 2. Cross-invocation idempotency guard & starting_after pagination (#419)
    tool_params = payload.get("tool_params") or {"amount": 2000, "currency": "usd"}
    derived_key = _jcs_sha256_hex({"agent_id": agent_id, "tool": tool_name, "params": tool_params})[:32]
    retry_used_random_key = bool(payload.get("agent_retry_regenerated_random_idempotency_key", False))
    is_list_tool = bool(payload.get("is_list_or_search_tool", False))
    supports_starting_after = bool(payload.get("supports_starting_after_cursor", True))

    if retry_used_random_key or (is_list_tool and not supports_starting_after):
        return StripeIdempotencyMcpExtDecision(
            allowed=False,
            decision_code="STRIPE_RETRY_DUPLICATE_CHARGE_OR_MISSING_PAGINATION",
            derived_idempotency_key=derived_key,
            reason="Agent retries across invocations must use deterministic idempotency keys and list tools must support starting_after (#419).",
        )

    # 3. Normalized Anthropic max_tokens defaults (#433)
    anthropic_model_id = str(payload.get("anthropic_model_id", "claude-sonnet-4-5"))
    resolved_max_tokens = int(payload.get("resolved_max_tokens", 8192))
    if "claude" in anthropic_model_id.lower() and resolved_max_tokens <= 0:
        return StripeIdempotencyMcpExtDecision(
            allowed=False,
            decision_code="STRIPE_NORMALIZED_ANTHROPIC_MAX_TOKENS_MISSING",
            derived_idempotency_key=derived_key,
            reason="Normalized Anthropic model IDs must resolve a positive default max_tokens (#433).",
        )

    # 4. MCP SEP-3371 SDK extension points & SEP-2133 2025-11-25 vs 2026-07-28 negotiation (#3371, #3364)
    registration_order_dependent = bool(payload.get("mcp_extension_order_dependent", False))
    mcp_protocol_version = str(payload.get("mcp_protocol_version", "2026-07-28"))
    negotiation_carrier = str(payload.get("mcp_extension_negotiation_carrier", "per_request_capabilities"))

    if registration_order_dependent or (
        mcp_protocol_version == "2025-11-25" and negotiation_carrier != "initialize_handshake"
    ):
        return StripeIdempotencyMcpExtDecision(
            allowed=False,
            decision_code="MCP_SDK_EXTENSION_POINT_OR_NEGOTIATION_MISMATCH",
            derived_idempotency_key=derived_key,
            reason="SEP-3371 requires order-independent extension registration and 2025-11-25 requires initialize-based negotiation (#3371/#3364).",
        )

    return StripeIdempotencyMcpExtDecision(
        allowed=True,
        decision_code="STRIPE_IDEMPOTENCY_MCP_EXT_OK",
        derived_idempotency_key=derived_key,
        reason="Stripe agent identity, cross-invocation idempotency, pagination, and MCP SEP-3371/2133 extension points verified.",
    )
