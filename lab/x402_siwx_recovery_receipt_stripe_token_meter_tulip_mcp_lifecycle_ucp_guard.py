"""Stage 120 deterministic protocol guards for x402 SIWX server-path recording,
recovery extension fail-closed promotion, Receipt v2 salted commitment & HEAD
non-settlement, Stripe AI cumulative token-meter & Tulip admission gate,
MCP SEP-3392/SEP-3405 extension lifecycle & SDK tiers, and UCP zero-`any`
bundled schema table recovery.

Covers:
1. x402 Foundation PRs `#3840`, `#3848`, `#3843`, `#3830`, `#3827`, `#3826`, `#3822`, `#3813`:
   - `#3840`: Record SIWX payments under the server-settled HTTP request path rather than
     client-supplied `PaymentPayload.resource.url`; an HTTP request with an empty path
     records nothing and never falls back to client URL.
   - `#3848`: Recovery extension promotes staged responses to free replay only when
     keyed on `(server_operation_id, confirmed_settlement_ref)` + matching projection
     hash; failed/pending/canceled settlements or promotion-hook failures remain staged,
     and identical outputs across distinct operation IDs never cross-promote.
   - `#3826`, `#3827`, `#3830`: Clone `extensions` before 402 enrichment so route
     `declaredExtensions.includeTxHash` is preserved, and compute Receipt v2 salted
     `authorizationCommitment` over `(salt, authorization_id)` (`eip3009` nonce or
     `svm-memo` SHA-256).
   - `#3843`, `#3822`, `#3813`: Distinguish Permit2 RPC outages as
     `invalid_permit2_failed_to_verify_signature`, normalize EIP-3009 `yParity` 0/1 to
     `v = 27/28`, and forbid `HEAD` requests from settling payments.
2. Stripe AI PRs `#519`, `#482`, `#464`, and `#506`:
   - `#519`: Cumulative Anthropic streaming `input_tokens` meter (takes latest non-null
     `message_delta.usage.input_tokens`, retaining previous count on null/omitted while
     honoring explicit 0).
   - `#482`: Tulip `ToolkitCore.run_tool()` deterministic admission gate where optional
     AI advisory may escalate low-risk calls to require confirmation (never soften
     high-risk calls) and fails closed on advisory error with hash-chained audit logging.
   - `#464` & `#506`: Dash-form and dot-form normalized Anthropic model ID max-token
     lookup (`64000` / `8192` instead of `4096` fallback) and 256-lane HTTP 402
     micro-wallet Merkle root invoice consolidation.
3. MCP PRs `#3392` (SEP-3392 Extension Lifecycle) and `#3405` (SEP-3405 SDK Tiers):
   - `#3392`: Enforce maturity transition gates across `experimental-ext-*`,
     `beta-ext-*`, `ext-*` (Stable), and Core promotion (forbidding breaking changes in
     Stable extensions without a new core protocol revision).
   - `#3405`: Compute SDK tier strictly from automated conformance pass rates on
     required spec versions.
4. UCP PRs `#894` and `#919`:
   - Recover canonical UCP metadata titles/links and composed `allOf` types after schema
     bundling without early `allOf` branch shadowing, enforcing zero `"any"` cells.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


MODEL_MAX_TOKENS_MAP = {
    "anthropic/claude-3-7-sonnet": 64000,
    "anthropic/claude-3.7-sonnet": 64000,
    "anthropic/claude-3-5-haiku": 8192,
    "anthropic/claude-3.5-haiku": 8192,
    "anthropic/claude-haiku-4-5": 64000,
    "anthropic/claude-haiku-4.5": 64000,
}


@dataclass(frozen=True)
class X402SiwxRecoveryReceiptCheckResult:
    allowed: bool
    reason_code: str
    recorded_siwx_path: str | None
    normalized_v: int
    receipt_tx_included: bool
    authorization_commitment: str
    recovery_promoted: bool


def validate_x402_siwx_recovery_and_receipt(
    *,
    http_method: str,
    has_http_transport: bool,
    server_request_path: str,
    client_payload_resource_url: str,
    requested_protected_path: str,
    settlement_status: str,
    server_operation_id: str,
    lookup_operation_id: str,
    confirmed_settlement_ref: str | None,
    promotion_hook_failed: bool,
    staged_projection_hash: str,
    recomputed_projection_hash: str,
    permit2_rpc_failed: bool,
    permit2_reported_code: str,
    raw_signature_v: int,
    declared_extensions: dict[str, Any],
    mutated_declared_extensions_in_402: bool,
    receipt_version: int,
    authorization_method: str,
    authorization_id: str,
    commitment_salt: str,
) -> X402SiwxRecoveryReceiptCheckResult:
    """Validate x402 PRs #3840, #3848, #3843, #3830, #3827, #3826, #3822, and #3813."""
    # #3813: A HEAD request cannot settle a payment
    if http_method.upper() == "HEAD":
        return X402SiwxRecoveryReceiptCheckResult(
            allowed=False,
            reason_code="X402_HEAD_REQUEST_CANNOT_SETTLE_PAYMENT",
            recorded_siwx_path=None,
            normalized_v=0,
            receipt_tx_included=False,
            authorization_commitment="",
            recovery_promoted=False,
        )

    # #3843: Permit2 signature-check RPC failure must report failed_to_verify_signature
    if permit2_rpc_failed:
        if permit2_reported_code != "invalid_permit2_failed_to_verify_signature":
            return X402SiwxRecoveryReceiptCheckResult(
                allowed=False,
                reason_code="X402_PERMIT2_RPC_FAILURE_MISREPORTED_AS_BAD_SIGNATURE",
                recorded_siwx_path=None,
                normalized_v=0,
                receipt_tx_included=False,
                authorization_commitment="",
                recovery_promoted=False,
            )

    # #3822: Normalize EIP-3009 yParity (0 or 1) to 27 or 28
    if raw_signature_v in (0, 1):
        normalized_v = raw_signature_v + 27
    elif raw_signature_v in (27, 28):
        normalized_v = raw_signature_v
    else:
        return X402SiwxRecoveryReceiptCheckResult(
            allowed=False,
            reason_code="X402_EIP3009_INVALID_SIGNATURE_V",
            recorded_siwx_path=None,
            normalized_v=raw_signature_v,
            receipt_tx_included=False,
            authorization_commitment="",
            recovery_promoted=False,
        )

    # #3840: Record SIWX payments on the server request path
    if has_http_transport:
        recorded_path = server_request_path.strip() or None
    else:
        recorded_path = client_payload_resource_url.strip() or None

    if not recorded_path or recorded_path != requested_protected_path:
        return X402SiwxRecoveryReceiptCheckResult(
            allowed=False,
            reason_code="X402_SIWX_SERVER_PATH_ENTITLEMENT_MISMATCH",
            recorded_siwx_path=recorded_path,
            normalized_v=normalized_v,
            receipt_tx_included=False,
            authorization_commitment="",
            recovery_promoted=False,
        )

    # #3826: Do not mutate declaredExtensions while building a 402 response
    if mutated_declared_extensions_in_402:
        return X402SiwxRecoveryReceiptCheckResult(
            allowed=False,
            reason_code="X402_EXTENSIONS_OBJECT_MUTATED_DURING_402_ENRICHMENT",
            recorded_siwx_path=recorded_path,
            normalized_v=normalized_v,
            receipt_tx_included=False,
            authorization_commitment="",
            recovery_promoted=False,
        )

    cloned_ext = dict(declared_extensions)
    offer_receipt_cfg = cloned_ext.get("offer-receipt", {})
    include_tx = bool(offer_receipt_cfg.get("includeTxHash", False))

    # #3827 & #3830: Receipt payload v2 with salted authorizationCommitment
    commitment = ""
    if receipt_version == 2:
        if authorization_method not in {"eip3009", "svm-memo", "permit2"}:
            return X402SiwxRecoveryReceiptCheckResult(
                allowed=False,
                reason_code="X402_RECEIPT_V2_UNSUPPORTED_AUTHORIZATION_METHOD",
                recorded_siwx_path=recorded_path,
                normalized_v=normalized_v,
                receipt_tx_included=include_tx,
                authorization_commitment="",
                recovery_promoted=False,
            )
        if not authorization_id or not commitment_salt:
            return X402SiwxRecoveryReceiptCheckResult(
                allowed=False,
                reason_code="X402_RECEIPT_V2_MISSING_AUTH_ID_OR_SALT",
                recorded_siwx_path=recorded_path,
                normalized_v=normalized_v,
                receipt_tx_included=include_tx,
                authorization_commitment="",
                recovery_promoted=False,
            )
        auth_token = (
            hashlib.sha256(authorization_id.encode("utf-8")).hexdigest()
            if authorization_method == "svm-memo"
            else authorization_id
        )
        commitment = hashlib.sha256(
            f"{commitment_salt}:{auth_token}".encode("utf-8")
        ).hexdigest()

    # #3848: Recovery extension fail-closed promotion
    if (
        settlement_status != "confirmed"
        or not confirmed_settlement_ref
        or promotion_hook_failed
        or server_operation_id != lookup_operation_id
        or staged_projection_hash != recomputed_projection_hash
    ):
        return X402SiwxRecoveryReceiptCheckResult(
            allowed=False,
            reason_code="X402_RECOVERY_FAIL_CLOSED_UNPROMOTED",
            recorded_siwx_path=recorded_path,
            normalized_v=normalized_v,
            receipt_tx_included=include_tx,
            authorization_commitment=commitment,
            recovery_promoted=False,
        )

    return X402SiwxRecoveryReceiptCheckResult(
        allowed=True,
        reason_code="X402_SIWX_RECOVERY_AND_RECEIPT_VALID",
        recorded_siwx_path=recorded_path,
        normalized_v=normalized_v,
        receipt_tx_included=include_tx,
        authorization_commitment=commitment,
        recovery_promoted=True,
    )


@dataclass(frozen=True)
class StripeTokenMeterAndTulipCheckResult:
    allowed: bool
    reason_code: str
    billed_input_tokens: int
    resolved_max_tokens: int
    effective_risk_level: str


def validate_stripe_token_meter_and_tulip_gate(
    *,
    message_start_input_tokens: int,
    message_delta_input_tokens_stream: list[int | None],
    reported_billed_input_tokens: int,
    rule_risk_level: str,
    advisory_risk_level: str | None,
    advisory_raised_error: bool,
    user_confirmed_high_risk: bool,
    audit_chain_linked: bool,
    model_id: str,
    lane_id: int,
    merkle_root_verified: bool,
) -> StripeTokenMeterAndTulipCheckResult:
    """Validate Stripe AI PRs #519, #482, #464, and #506."""
    # #519: Cumulative Anthropic input token meter
    effective_tokens = message_start_input_tokens
    for delta_val in message_delta_input_tokens_stream:
        if delta_val is not None:
            effective_tokens = delta_val

    if reported_billed_input_tokens != effective_tokens:
        return StripeTokenMeterAndTulipCheckResult(
            allowed=False,
            reason_code="STRIPE_TOKEN_METER_NON_CUMULATIVE_INPUT_UNDERBILLING",
            billed_input_tokens=effective_tokens,
            resolved_max_tokens=0,
            effective_risk_level="high",
        )

    # #482: Tulip admission gate & one-way escalation advisory
    if not audit_chain_linked:
        return StripeTokenMeterAndTulipCheckResult(
            allowed=False,
            reason_code="STRIPE_TULIP_AUDIT_CHAIN_BROKEN",
            billed_input_tokens=effective_tokens,
            resolved_max_tokens=0,
            effective_risk_level="high",
        )

    if advisory_raised_error:
        effective_risk = "high"
    elif rule_risk_level == "high" or advisory_risk_level == "high":
        # Advisory can escalate low -> high, never soften high -> low
        effective_risk = "high"
    else:
        effective_risk = "low"

    if effective_risk == "high" and not user_confirmed_high_risk:
        return StripeTokenMeterAndTulipCheckResult(
            allowed=False,
            reason_code="STRIPE_TULIP_HIGH_RISK_TOOL_CALL_DENIED",
            billed_input_tokens=effective_tokens,
            resolved_max_tokens=0,
            effective_risk_level=effective_risk,
        )

    # #464: Dash-form and normalized dot-form model ID maxTokens lookup
    resolved_max = MODEL_MAX_TOKENS_MAP.get(model_id, 4096)
    if resolved_max == 4096 and model_id.startswith("anthropic/claude-"):
        return StripeTokenMeterAndTulipCheckResult(
            allowed=False,
            reason_code="STRIPE_LANGUAGE_MODEL_NORMALIZED_DOT_ID_FALLBACK_4096",
            billed_input_tokens=effective_tokens,
            resolved_max_tokens=resolved_max,
            effective_risk_level=effective_risk,
        )

    # #506: SynapticChain 256-lane HTTP 402 micro-wallet Merkle invoice consolidation
    if not (0 <= lane_id < 256) or not merkle_root_verified:
        return StripeTokenMeterAndTulipCheckResult(
            allowed=False,
            reason_code="STRIPE_SYNAPTIC_402_LANE_OR_MERKLE_PROOF_INVALID",
            billed_input_tokens=effective_tokens,
            resolved_max_tokens=resolved_max,
            effective_risk_level=effective_risk,
        )

    return StripeTokenMeterAndTulipCheckResult(
        allowed=True,
        reason_code="STRIPE_TOKEN_METER_AND_TULIP_GATE_VALID",
        billed_input_tokens=effective_tokens,
        resolved_max_tokens=resolved_max,
        effective_risk_level=effective_risk,
    )


@dataclass(frozen=True)
class McpLifecycleAndUcpTableCheckResult:
    allowed: bool
    reason_code: str
    computed_sdk_tier: int
    any_type_cells_count: int


def validate_mcp_lifecycle_and_ucp_schema_tables(
    *,
    extension_repo_name: str,
    maturity_stage: str,
    has_extensions_track_sep: bool,
    has_standards_track_sep: bool,
    has_sep2484_conformance: bool,
    introduces_breaking_change: bool,
    has_new_core_protocol_revision: bool,
    conformance_pass_rate_pct: float,
    claimed_sdk_tier: int,
    obsolete_early_allof_branch_present: bool,
    schema_table_fields: list[dict[str, Any]],
) -> McpLifecycleAndUcpTableCheckResult:
    """Validate MCP PRs #3392 & #3405 and UCP PRs #894 & #919."""
    # #3392: Extension Lifecycle repository naming and transition rules
    expected_prefix = {
        "experimental": "experimental-ext-",
        "beta": "beta-ext-",
        "stable": "ext-",
        "core": "core-",
    }.get(maturity_stage, "")
    if not expected_prefix or not extension_repo_name.startswith(expected_prefix):
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="MCP_EXTENSION_REPO_PREFIX_MISMATCH",
            computed_sdk_tier=3,
            any_type_cells_count=0,
        )

    if maturity_stage == "beta" and not has_extensions_track_sep:
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="MCP_BETA_EXTENSION_MISSING_SEP",
            computed_sdk_tier=3,
            any_type_cells_count=0,
        )

    if maturity_stage == "stable":
        if not has_extensions_track_sep or not has_sep2484_conformance:
            return McpLifecycleAndUcpTableCheckResult(
                allowed=False,
                reason_code="MCP_STABLE_EXTENSION_MISSING_SEP_OR_CONFORMANCE",
                computed_sdk_tier=3,
                any_type_cells_count=0,
            )
        if introduces_breaking_change and not has_new_core_protocol_revision:
            return McpLifecycleAndUcpTableCheckResult(
                allowed=False,
                reason_code="MCP_STABLE_EXTENSION_BREAKING_CHANGE_WITHOUT_CORE_REVISION",
                computed_sdk_tier=3,
                any_type_cells_count=0,
            )

    if maturity_stage == "core" and not has_standards_track_sep:
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="MCP_CORE_PROMOTION_MISSING_STANDARDS_TRACK_SEP",
            computed_sdk_tier=3,
            any_type_cells_count=0,
        )

    # #3405: Conformance-Driven SDK Tiers
    if conformance_pass_rate_pct >= 100.0:
        computed_tier = 1
    elif conformance_pass_rate_pct >= 80.0:
        computed_tier = 2
    else:
        computed_tier = 3

    if claimed_sdk_tier < computed_tier:
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="MCP_SDK_TIER_INFLATED_BEYOND_CONFORMANCE",
            computed_sdk_tier=computed_tier,
            any_type_cells_count=0,
        )

    # UCP #894 & #919: Bundled schema type recovery & zero-'any' cell enforcement
    if obsolete_early_allof_branch_present:
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="UCP_OBSOLETE_ALLOF_BRANCH_SHADOWS_BUNDLED_TYPE_RECOVERY",
            computed_sdk_tier=computed_tier,
            any_type_cells_count=len(schema_table_fields),
        )

    any_cells = 0
    for field in schema_table_fields:
        resolved_type = field.get("resolved_display_type", "any")
        if resolved_type == "any":
            any_cells += 1

    if any_cells > 0:
        return McpLifecycleAndUcpTableCheckResult(
            allowed=False,
            reason_code="UCP_SCHEMA_TABLE_CONTAINS_UNRESOLVED_ANY_CELLS",
            computed_sdk_tier=computed_tier,
            any_type_cells_count=any_cells,
        )

    return McpLifecycleAndUcpTableCheckResult(
        allowed=True,
        reason_code="MCP_LIFECYCLE_AND_UCP_SCHEMA_TABLES_VALID",
        computed_sdk_tier=computed_tier,
        any_type_cells_count=0,
    )
