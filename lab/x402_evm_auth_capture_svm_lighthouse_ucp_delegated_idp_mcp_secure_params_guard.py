"""Stage 134 deterministic guardrails across x402, UCP, Stripe AI, MCP, and Sierra tau2-bench.

Covers primary-source upstream PRs:
1. x402-foundation/x402:
   - #3622: EVM `auth-capture` (`AuthCaptureEscrow`) two-phase authorize -> capture/void lifecycle & zero-fee operator terms
   - #3615: SVM `exact` Phantom Lighthouse pre/post guard instruction classification by program ID
   - #3606 / #3605 / #3603 / #3601: SVM batch cooperative seal/refund `onDistributionConfirmed` callback (`settlement_pending` on callback failure) & server-mode `payment-identifier` recovery with `SettlementResponse` voucher
   - #3604 / #3613 / #3612 / #3610 / #3607 / #3600 / #3599: Buyer Delivery Claim extension, Xahau (`xahau:21337`/`21338`) exact scheme with signed `NetworkID` & Hook fee cap, FastAPI off-event-loop `/supported` init retry, and Fastify `preValidation` parsed-body payment hook
2. Universal-Commerce-Protocol/ucp:
   - #423 / #431: Delegated Identity Providers (`delegated_idps[]`) & accelerated RFC 8693 + RFC 7523 back-channel token exchange under business authority
   - #438 / #501: Self-describing capability `operations[]` intersection & embedded resolved schema `required[]` preservation
   - #407 / #428 / #424 / #421: Per-channel `buyer_consent` (`marketing_consent_options` & `marketing_channels`), `"compliance"` message presentation mode, and split PAN vs. Network Token credential constraints
   - #406 / #405 / #398: Approaching discounts upsell conservation & post-handoff `return_url` allowlist + authoritative session state verification
3. stripe/ai, modelcontextprotocol/modelcontextprotocol & sierra-research/tau2-bench:
   - modelcontextprotocol #3221 / #3193: `SEP-3221` `secureInputSchema` / host-injected `secureArguments` confused-deputy isolation & `SEP-3193` cross-server `flowOrigin` / `flowPolicy` enforcement
   - modelcontextprotocol #3239 / #3185 / #3182 / #3172 / #3171: `SEP-3239` delegated end-user context policy narrowing, root-hoisted `oneOf` property type-check, `SEP-3182` `idempotencyKey`, and `SEP-3172` compensating tool recovery metadata
   - stripe/ai #292 / #235 / #234 / #222: Stripe Connect Accounts v2 (`POST /v2/core/accounts`) enforcement, canonical `https://mcp.stripe.com` URL (no trailing slash), and `stripe-mcp-typescript` header
   - sierra-research/tau2-bench #410 / #407 / #396 / #395 / #392 / #391: `banking_knowledge` v1.0.1 `$105 days` artifact repair, tau-voice interaction metrics golden parity, agent-side transfer stop condition, and core text import isolation
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


ZERO_ADDRESS_EVM = "0x0000000000000000000000000000000000000000"
ALLOWED_SVM_EXACT_PROGRAMS = frozenset(
    {
        "ComputeBudget111111111111111111111111111111",
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
        "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
        "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95",  # Phantom Lighthouse assertion program
    }
)
XAHAU_CAIP2_NETWORKS = frozenset({"xahau:21337", "xahau:21338"})


# ---------------------------------------------------------------------------
# 1. x402 EVM Auth-Capture, SVM Lighthouse, Seal Callback & Buyer Claim Guards
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class X402EvmAuthCaptureDecision:
    allowed: bool
    escrow_state: str
    captured_amount_minor: int
    reason_code: str


def evaluate_x402_evm_auth_capture_guard(
    *,
    action: str,
    authorized_amount_minor: int,
    requested_amount_minor: int,
    current_escrow_state: str,
    server_signature_verified: bool,
    fee_bps: int = 0,
    fee_recipient: str = ZERO_ADDRESS_EVM,
    min_fee_minor: int = 0,
    max_fee_minor: int = 0,
) -> X402EvmAuthCaptureDecision:
    """Enforce x402 EVM `AuthCaptureEscrow` lifecycle & zero-fee operator terms (#3622)."""
    if fee_bps == 0:
        if fee_recipient != ZERO_ADDRESS_EVM or min_fee_minor != 0 or max_fee_minor != 0:
            return X402EvmAuthCaptureDecision(
                allowed=False,
                escrow_state=current_escrow_state,
                captured_amount_minor=0,
                reason_code="X402_EVM_AUTH_CAPTURE_INVALID_ZERO_FEE_OPERATOR_TERMS",
            )
    elif fee_bps < 0 or min_fee_minor < 0 or max_fee_minor < min_fee_minor:
        return X402EvmAuthCaptureDecision(
            allowed=False,
            escrow_state=current_escrow_state,
            captured_amount_minor=0,
            reason_code="X402_EVM_AUTH_CAPTURE_INVALID_FEE_BOUNDS",
        )

    if action == "authorize":
        if current_escrow_state != "none" or authorized_amount_minor <= 0:
            return X402EvmAuthCaptureDecision(
                allowed=False,
                escrow_state=current_escrow_state,
                captured_amount_minor=0,
                reason_code="X402_EVM_AUTH_CAPTURE_AUTHORIZE_INVALID_STATE",
            )
        return X402EvmAuthCaptureDecision(
            allowed=True,
            escrow_state="authorized",
            captured_amount_minor=0,
            reason_code="X402_EVM_AUTH_CAPTURE_AUTHORIZED",
        )

    if not server_signature_verified:
        return X402EvmAuthCaptureDecision(
            allowed=False,
            escrow_state=current_escrow_state,
            captured_amount_minor=0,
            reason_code="X402_EVM_AUTH_CAPTURE_UNSIGNED_LIFECYCLE_CALL_BLOCKED",
        )

    if current_escrow_state != "authorized":
        return X402EvmAuthCaptureDecision(
            allowed=False,
            escrow_state=current_escrow_state,
            captured_amount_minor=0,
            reason_code="X402_EVM_AUTH_CAPTURE_ESCROW_ALREADY_FINALIZED_OR_VOIDED",
        )

    if action == "capture":
        if requested_amount_minor <= 0 or requested_amount_minor > authorized_amount_minor:
            return X402EvmAuthCaptureDecision(
                allowed=False,
                escrow_state=current_escrow_state,
                captured_amount_minor=0,
                reason_code="X402_EVM_AUTH_CAPTURE_AMOUNT_EXCEEDS_AUTHORIZATION",
            )
        return X402EvmAuthCaptureDecision(
            allowed=True,
            escrow_state="captured",
            captured_amount_minor=requested_amount_minor,
            reason_code="X402_EVM_AUTH_CAPTURE_CAPTURED",
        )

    if action == "void":
        return X402EvmAuthCaptureDecision(
            allowed=True,
            escrow_state="voided",
            captured_amount_minor=0,
            reason_code="X402_EVM_AUTH_CAPTURE_VOIDED",
        )

    return X402EvmAuthCaptureDecision(
        allowed=False,
        escrow_state=current_escrow_state,
        captured_amount_minor=0,
        reason_code="X402_EVM_AUTH_CAPTURE_UNKNOWN_ACTION",
    )


@dataclass(frozen=True)
class X402SvmLighthouseSealDecision:
    allowed: bool
    settlement_status: str
    callback_invocations: int
    voucher_attached: bool
    reason_code: str


def evaluate_x402_svm_lighthouse_and_seal_callback_guard(
    *,
    instruction_program_ids: Sequence[str],
    has_transfer_checked: bool,
    close_mode: str = "none",
    tx_landed_onchain: bool = True,
    distribution_callback_succeeded: bool = True,
    prior_callback_invocations: int = 0,
    is_server_mode_recovery: bool = False,
    recovery_bound_to_payer_and_channel: bool = True,
    cached_settlement_voucher_present: bool = True,
) -> X402SvmLighthouseSealDecision:
    """Validate SVM Phantom Lighthouse pre/post guards (#3615), seal/refund callbacks (#3606), and recovery (#3605)."""
    if not instruction_program_ids or not has_transfer_checked:
        return X402SvmLighthouseSealDecision(
            allowed=False,
            settlement_status="rejected",
            callback_invocations=prior_callback_invocations,
            voucher_attached=False,
            reason_code="X402_SVM_MISSING_TRANSFER_CHECKED_INSTRUCTION",
        )

    for prog_id in instruction_program_ids:
        if prog_id not in ALLOWED_SVM_EXACT_PROGRAMS:
            return X402SvmLighthouseSealDecision(
                allowed=False,
                settlement_status="rejected",
                callback_invocations=prior_callback_invocations,
                voucher_attached=False,
                reason_code="X402_SVM_UNTRUSTED_INSTRUCTION_PROGRAM_BLOCKED",
            )

    if is_server_mode_recovery:
        if not recovery_bound_to_payer_and_channel:
            return X402SvmLighthouseSealDecision(
                allowed=False,
                settlement_status="rejected",
                callback_invocations=prior_callback_invocations,
                voucher_attached=False,
                reason_code="X402_BATCH_RECOVERY_UNBOUND_PAYMENT_ID_READ_BLOCKED",
            )
        if not cached_settlement_voucher_present:
            return X402SvmLighthouseSealDecision(
                allowed=False,
                settlement_status="rejected",
                callback_invocations=prior_callback_invocations,
                voucher_attached=False,
                reason_code="X402_BATCH_RECOVERY_MISSING_SETTLEMENT_VOUCHER_BLOCKED",
            )

    if close_mode in {"seal", "refund"}:
        if prior_callback_invocations >= 1:
            return X402SvmLighthouseSealDecision(
                allowed=False,
                settlement_status="duplicate_callback_blocked",
                callback_invocations=prior_callback_invocations,
                voucher_attached=cached_settlement_voucher_present,
                reason_code="X402_SVM_CLOSE_CALLBACK_ALREADY_RECORDED",
            )
        if tx_landed_onchain and not distribution_callback_succeeded:
            return X402SvmLighthouseSealDecision(
                allowed=True,
                settlement_status="settlement_pending",
                callback_invocations=0,
                voucher_attached=cached_settlement_voucher_present,
                reason_code="X402_SVM_CLOSE_CALLBACK_FAILED_SETTLEMENT_PENDING",
            )
        return X402SvmLighthouseSealDecision(
            allowed=True,
            settlement_status="settled",
            callback_invocations=1,
            voucher_attached=cached_settlement_voucher_present,
            reason_code="X402_SVM_LIGHTHOUSE_AND_CLOSE_CALLBACK_VERIFIED",
        )

    return X402SvmLighthouseSealDecision(
        allowed=True,
        settlement_status="settled",
        callback_invocations=prior_callback_invocations,
        voucher_attached=cached_settlement_voucher_present,
        reason_code="X402_SVM_LIGHTHOUSE_EXACT_VERIFIED",
    )


@dataclass(frozen=True)
class X402BuyerClaimXahauRuntimeDecision:
    allowed: bool
    reason_code: str


def evaluate_x402_buyer_claim_xahau_runtime_guard(
    *,
    claim_delivered_status: str = "yes",
    claim_evidence_hash_hex: str = "a" * 64,
    claim_settlement_tx_hash: str = "0x" + "b" * 64,
    buyer_signature_verified: bool = True,
    xahau_network: str = "xahau:21337",
    xahau_signed_network_id: int | None = 21337,
    xahau_invoice_id_bound: bool = True,
    xahau_fee_drops: int = 12_782,
    xahau_max_fee_drops: int = 100_000,
    fastapi_init_retry_blocks_event_loop: bool = False,
    fastify_hook_stage: str = "preValidation",
) -> X402BuyerClaimXahauRuntimeDecision:
    """Validate Buyer Delivery Claim (#3604), Xahau exact (#3612/#3610), FastAPI init (#3613), and Fastify hook (#3607)."""
    if claim_delivered_status not in {"yes", "no", "partial"}:
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_BUYER_CLAIM_INVALID_DELIVERED_STATUS",
        )
    if (
        len(claim_evidence_hash_hex) != 64
        or not claim_settlement_tx_hash
        or not buyer_signature_verified
    ):
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_BUYER_CLAIM_MISSING_EVIDENCE_OR_SIGNATURE",
        )

    if xahau_network not in XAHAU_CAIP2_NETWORKS:
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_XAHAU_UNSUPPORTED_NETWORK",
        )
    expected_net_id = int(xahau_network.split(":")[1])
    if xahau_signed_network_id != expected_net_id or not xahau_invoice_id_bound:
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_XAHAU_MISSING_SIGNED_NETWORK_ID_OR_INVOICE_BINDING",
        )
    if xahau_fee_drops <= 0 or xahau_fee_drops > xahau_max_fee_drops:
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_XAHAU_HOOK_FEE_DROPS_EXCEEDS_MAX",
        )

    if fastapi_init_retry_blocks_event_loop:
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_FASTAPI_SYNC_INIT_RETRY_BLOCKS_EVENT_LOOP",
        )
    if fastify_hook_stage != "preValidation":
        return X402BuyerClaimXahauRuntimeDecision(
            allowed=False,
            reason_code="X402_FASTIFY_HOOK_STAGE_MUST_BE_PREVALIDATION",
        )

    return X402BuyerClaimXahauRuntimeDecision(
        allowed=True,
        reason_code="X402_BUYER_CLAIM_XAHAU_AND_RUNTIME_VERIFIED",
    )


# ---------------------------------------------------------------------------
# 2. UCP Delegated IdP, Capability Operations, Marketing Consent & Upsell Guards
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UcpDelegatedIdpAndCapabilityOpsDecision:
    allowed: bool
    enabled_operations: tuple[str, ...]
    reason_code: str


def evaluate_ucp_delegated_idp_and_capability_ops_guard(
    *,
    business_issuer: str,
    business_delegated_idps: Sequence[str],
    platform_idp_issuer: str,
    rfc8693_grant_type: str,
    rfc7523_client_assertion_verified: bool,
    issued_access_token_issuer: str,
    intersected_capabilities: Mapping[str, Sequence[str]],
    requested_operation: str,
    embedded_schema_required_preserved: bool = True,
) -> UcpDelegatedIdpAndCapabilityOpsDecision:
    """Validate UCP delegated IdP RFC 8693/7523 flow (#423), capability `operations[]` (#438), and embedded `required` (#501)."""
    if not embedded_schema_required_preserved:
        return UcpDelegatedIdpAndCapabilityOpsDecision(
            allowed=False,
            enabled_operations=(),
            reason_code="UCP_EMBEDDED_SCHEMA_REQUIRED_FIELDS_DROPPED",
        )

    if platform_idp_issuer not in business_delegated_idps:
        return UcpDelegatedIdpAndCapabilityOpsDecision(
            allowed=False,
            enabled_operations=(),
            reason_code="UCP_DELEGATED_IDP_NOT_TRUSTED_BY_BUSINESS",
        )

    if (
        rfc8693_grant_type != "urn:ietf:params:oauth:grant-type:token-exchange"
        or not rfc7523_client_assertion_verified
    ):
        return UcpDelegatedIdpAndCapabilityOpsDecision(
            allowed=False,
            enabled_operations=(),
            reason_code="UCP_DELEGATED_IDP_INVALID_TOKEN_EXCHANGE_OR_ASSERTION",
        )

    if issued_access_token_issuer != business_issuer:
        return UcpDelegatedIdpAndCapabilityOpsDecision(
            allowed=False,
            enabled_operations=(),
            reason_code="UCP_DELEGATED_IDP_TOKEN_MUST_BE_ISSUED_BY_BUSINESS_AUTHORITY",
        )

    enabled_ops: list[str] = []
    for ops in intersected_capabilities.values():
        for op in ops:
            if op not in enabled_ops:
                enabled_ops.append(op)

    if requested_operation not in enabled_ops:
        return UcpDelegatedIdpAndCapabilityOpsDecision(
            allowed=False,
            enabled_operations=tuple(enabled_ops),
            reason_code="UCP_OPERATION_NOT_ENABLED_BY_INTERSECTED_CAPABILITY",
        )

    return UcpDelegatedIdpAndCapabilityOpsDecision(
        allowed=True,
        enabled_operations=tuple(enabled_ops),
        reason_code="UCP_DELEGATED_IDP_AND_CAPABILITY_OPS_VERIFIED",
    )


@dataclass(frozen=True)
class UcpMarketingUpsellReturnUrlDecision:
    allowed: bool
    reason_code: str


def evaluate_ucp_marketing_upsell_and_return_url_guard(
    *,
    marketing_consent_options: Sequence[Mapping[str, Any]],
    submitted_marketing_channels: Sequence[Mapping[str, Any]],
    message_presentation: str = "compliance",
    subtotal_minor: int = 4000,
    total_minor: int = 4000,
    approaching_discounts: Sequence[Mapping[str, Any]] = (),
    return_url: str = "https://platform.example.com/checkout/return",
    allowed_return_origins: Sequence[str] = ("https://platform.example.com",),
    return_query_status_hint: str | None = None,
    session_api_verified_status: str | None = None,
) -> UcpMarketingUpsellReturnUrlDecision:
    """Validate UCP per-channel marketing consent (#407), `compliance` mode (#428), approaching discounts (#406), and `return_url` (#398)."""
    if message_presentation == "disclosure" or message_presentation not in {"notice", "compliance"}:
        return UcpMarketingUpsellReturnUrlDecision(
            allowed=False,
            reason_code="UCP_MESSAGE_PRESENTATION_LEGACY_DISCLOSURE_OR_INVALID",
        )

    offered_ids: set[str] = set()
    for opt in marketing_consent_options:
        cid = str(opt.get("channel_id") or "").strip()
        text = str(opt.get("display_text") or "").strip()
        priv = str(opt.get("privacy_policy_url") or "").strip()
        if not cid or not text or not priv.startswith("https://"):
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_MARKETING_OPTION_MISSING_REQUIRED_METADATA",
            )
        offered_ids.add(cid)

    for sub in submitted_marketing_channels:
        cid = str(sub.get("channel_id") or "").strip()
        if cid not in offered_ids:
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_MARKETING_CHANNEL_NOT_IN_BUSINESS_OPTIONS",
            )
        if not bool(sub.get("explicit_buyer_decision", True)):
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_MARKETING_CHANNEL_PRECHECKED_WITHOUT_DECISION",
            )

    for disc in approaching_discounts:
        threshold = int(disc.get("threshold_minor", 0))
        remaining = int(disc.get("spend_remaining_minor", 0))
        if threshold <= subtotal_minor or remaining != threshold - subtotal_minor:
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_APPROACHING_DISCOUNT_THRESHOLD_ARITHMETIC_MISMATCH",
            )
        if total_minor < subtotal_minor:
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_APPROACHING_DISCOUNT_PREMATURELY_APPLIED_TO_TOTAL",
            )

    parsed = urlparse(return_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.scheme != "https" or origin not in allowed_return_origins:
        return UcpMarketingUpsellReturnUrlDecision(
            allowed=False,
            reason_code="UCP_RETURN_URL_UNTRUSTED_ORIGIN_OR_INSECURE",
        )

    if return_query_status_hint is not None:
        if session_api_verified_status is None or session_api_verified_status != return_query_status_hint:
            return UcpMarketingUpsellReturnUrlDecision(
                allowed=False,
                reason_code="UCP_RETURN_URL_STATUS_HINT_UNVERIFIED_OR_MISMATCH",
            )

    return UcpMarketingUpsellReturnUrlDecision(
        allowed=True,
        reason_code="UCP_MARKETING_UPSELL_AND_RETURN_URL_VERIFIED",
    )


# ---------------------------------------------------------------------------
# 3. MCP Secure Params / Flow Policy / Delegated User, Stripe v2 & tau2-bench
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class McpSecureParamsFlowAndStripeDecision:
    allowed: bool
    deduplicated_replay: bool
    reason_code: str


def evaluate_mcp_secure_params_flow_and_stripe_v2_guard(
    *,
    secure_input_keys: Sequence[str],
    model_arguments: Mapping[str, Any],
    host_secure_arguments: Mapping[str, Any],
    flow_origins: Sequence[str],
    server_allowed_flow_origins: Sequence[str],
    end_user_verification_level: str = "verified",
    end_user_jwt_verified: bool = True,
    server_published_scopes: Sequence[str] = ("orders:read", "orders:write"),
    client_requested_scopes: Sequence[str] = ("orders:read",),
    oneof_root_property_types: Mapping[str, type] | None = None,
    oneof_instance: Mapping[str, Any] | None = None,
    idempotency_key: str | None = None,
    seen_idempotency_keys: Sequence[str] = (),
    stripe_connect_api_version: str = "v2",
    stripe_legacy_account_type: str | None = None,
    stripe_mcp_url: str = "https://mcp.stripe.com",
    stripe_mcp_header: str = "stripe-mcp-typescript",
) -> McpSecureParamsFlowAndStripeDecision:
    """Enforce MCP SEP-3221 (#3221), SEP-3193 (#3193), SEP-3239 (#3239), #3185, SEP-3182 (#3182), and Stripe v2 (#292/#234/#222)."""
    # 1. SEP-3221 secureInputSchema vs model arguments isolation
    for key in secure_input_keys:
        if key in model_arguments:
            return McpSecureParamsFlowAndStripeDecision(
                allowed=False,
                deduplicated_replay=False,
                reason_code="MCP_SEP3221_MODEL_CONTROLLED_SECURE_PARAM_INJECTION_BLOCKED",
            )
        if key not in host_secure_arguments:
            return McpSecureParamsFlowAndStripeDecision(
                allowed=False,
                deduplicated_replay=False,
                reason_code="MCP_SEP3221_MISSING_HOST_INJECTED_SECURE_ARGUMENT",
            )

    # 2. SEP-3193 cross-server flowOrigin vs flowPolicy
    allowed_origins = set(server_allowed_flow_origins)
    if not flow_origins or any(origin not in allowed_origins for origin in flow_origins):
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="MCP_SEP3193_UNTRUSTED_CROSS_SERVER_FLOW_ORIGIN_BLOCKED",
        )

    # 3. SEP-3239 delegated end-user context narrowing & JWT verification
    if end_user_verification_level not in {"anonymous", "claimed", "verified"}:
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="MCP_SEP3239_INVALID_VERIFICATION_LEVEL",
        )
    if end_user_verification_level == "verified" and not end_user_jwt_verified:
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="MCP_SEP3239_VERIFIED_USER_REQUIRES_SIGNED_JWT",
        )
    published_set = set(server_published_scopes)
    if any(scope not in published_set for scope in client_requested_scopes):
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="MCP_SEP3239_CLIENT_SCOPE_EXPANSION_BLOCKED",
        )

    # 4. #3185 root-hoisted property type check before `oneOf` exclusivity
    if oneof_root_property_types is not None and oneof_instance is not None:
        for k, val in oneof_instance.items():
            expected_type = oneof_root_property_types.get(k)
            if expected_type is not None and not isinstance(val, expected_type):
                return McpSecureParamsFlowAndStripeDecision(
                    allowed=False,
                    deduplicated_replay=False,
                    reason_code="MCP_ONEOF_INACTIVE_BRANCH_TYPE_BYPASS_BLOCKED",
                )
        present_keys = [k for k in oneof_root_property_types if k in oneof_instance]
        if len(present_keys) != 1:
            return McpSecureParamsFlowAndStripeDecision(
                allowed=False,
                deduplicated_replay=False,
                reason_code="MCP_ONEOF_MUTUAL_EXCLUSIVITY_VIOLATION",
            )

    # 5. Stripe Connect Accounts v2 & MCP URL/header hygiene (#292, #234, #222)
    if stripe_connect_api_version != "v2" or stripe_legacy_account_type in {"express", "custom", "standard"}:
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="STRIPE_CONNECT_LEGACY_V1_ACCOUNT_TYPE_BLOCKED",
        )
    if stripe_mcp_url.endswith("/") or stripe_mcp_url != "https://mcp.stripe.com":
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="STRIPE_MCP_URL_TRAILING_SLASH_OR_INVALID_HOST",
        )
    if stripe_mcp_header not in {"stripe-mcp-typescript", "stripe-mcp-python", "stripe-mcp-local"}:
        return McpSecureParamsFlowAndStripeDecision(
            allowed=False,
            deduplicated_replay=False,
            reason_code="STRIPE_MCP_HEADER_UNRECOGNIZED",
        )

    # 6. SEP-3182 idempotencyKey deduplication
    is_replay = bool(idempotency_key and idempotency_key in seen_idempotency_keys)
    return McpSecureParamsFlowAndStripeDecision(
        allowed=True,
        deduplicated_replay=is_replay,
        reason_code="MCP_SECURE_PARAMS_FLOW_AND_STRIPE_V2_VERIFIED",
    )


_STRAY_DAY_CURRENCY_RE = re.compile(r"\$(\d{3})\s+days\b")


@dataclass(frozen=True)
class Tau2BankingKbVoiceAndUserSimDecision:
    allowed: bool
    sanitized_kb_text: str
    repaired_day_count_artifacts: int
    reason_code: str


def evaluate_tau2_banking_kb_voice_and_usersim_guard(
    *,
    kb_text: str,
    voice_interaction_metrics_parity: bool = True,
    voice_banking_task_count: int = 97,
    transfer_stop_triggered_by: str = "agent",
    eager_optional_deps_imported: Sequence[str] = (),
) -> Tau2BankingKbVoiceAndUserSimDecision:
    """Repair tau2 `banking_knowledge` `$105 days` artifacts (#410/#407) and enforce voice/usersim guards (#396/#395/#392/#391)."""
    repaired_count = 0

    def _replace_day(match: re.Match[str]) -> str:
        nonlocal repaired_count
        days = int(match.group(1))
        if days >= 105:
            repaired_count += 1
            return f"{days} days"
        return match.group(0)

    sanitized = _STRAY_DAY_CURRENCY_RE.sub(_replace_day, kb_text)

    if any(dep in {"scipy", "rank_bm25"} for dep in eager_optional_deps_imported):
        return Tau2BankingKbVoiceAndUserSimDecision(
            allowed=False,
            sanitized_kb_text=sanitized,
            repaired_day_count_artifacts=repaired_count,
            reason_code="TAU2_CORE_TEXT_EAGER_OPTIONAL_IMPORT_BLOCKED",
        )

    if transfer_stop_triggered_by != "agent":
        return Tau2BankingKbVoiceAndUserSimDecision(
            allowed=False,
            sanitized_kb_text=sanitized,
            repaired_day_count_artifacts=repaired_count,
            reason_code="TAU2_USERSIM_PREMATURE_TRANSFER_STOP_BLOCKED",
        )

    if not voice_interaction_metrics_parity or voice_banking_task_count != 97:
        return Tau2BankingKbVoiceAndUserSimDecision(
            allowed=False,
            sanitized_kb_text=sanitized,
            repaired_day_count_artifacts=repaired_count,
            reason_code="TAU2_VOICE_INTERACTION_METRICS_OR_BANKING_TRACK_MISMATCH",
        )

    return Tau2BankingKbVoiceAndUserSimDecision(
        allowed=True,
        sanitized_kb_text=sanitized,
        repaired_day_count_artifacts=repaired_count,
        reason_code="TAU2_BANKING_KB_VOICE_AND_USERSIM_VERIFIED",
    )
