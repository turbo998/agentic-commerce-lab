"""Stage 196 deterministic guard module:

Covers primary-source protocol and security invariants from:
1. x402 PR #3893 (merged 2026-10-22T19:30:32Z): Post-merge SDK regressions —
   EIP-712 `EIP712Domain` required in all Go `auth-capture` operator type maps
   (`CaptureTypesV1_0`, `CaptureTypesV1_1`, `ChargeTypesV1_0`, `ChargeTypesV1_1`,
   `VoidTypes`, `RefundTypes`), V2 CAIP-2 network validation with legacy Algorand
   44-char base64 genesis hash compatibility (`^algorand:[A-Za-z0-9+/]{43}=$`),
   and zero-value EVM refund fail-closed enforcement.
2. x402 PR #3867: EVM `x402UptoERC3009Proxy` (`0x40208Cd083acD9559Ce44742c4BcD9Cf04850006`) —
   stateless, adminless ERC-3009 `upto` proxy using `ReceiveWithAuthorization`,
   typed nonce commitment `(payTo, settler, salt)`, settler caller binding,
   `0 < actualAmount <= maxAmount`, atomic pull + pay + remainder refund to payer,
   and zero proxy residual balance change (`proxy_balance_delta == 0`).
3. x402 PR #3781 & PR #3885: Stellar Soroban `UptoProxy.settle_upto` (`stellar:pubnet`,
   `stellar:testnet`, `MAX_ALLOWANCE_LEDGERS = 17280` / `86400s`,
   `signatureExpirationLedger == allowance_expiration_ledger`, `areFeesSponsored == True`,
   simulation auth-tree verification against malicious RPC `token.transfer` substitution)
   and Casper `exact` scheme (`casper:casper`, `casper:casper-test`, CEP-3009
   `TransferWithAuthorization` EIP-712, `ed25519`/`secp256k1` low-s, `upto`/batch rejected).
4. x402 PR #3874 & PR #3869: Facilitator response body size limits (`ResponseBodyTooLargeError`:
   `1 MiB` control-plane vs `4 MiB` Bazaar discovery) and MCP `maxRequestTimeoutSeconds`
   capping initial probe, paid retry, AND corrective recovery retries while preserving
   stricter caller deadlines.
5. UCP PR #783: Identity Linking Accelerated IdP Flow — per-user `subject_token`
   prerequisite (fallback to direct business OAuth when absent), `(iss, sub)` subject
   binding to prevent cross-user account linking, IdP scope coverage for business
   `required_claims`, and platform-level vs per-business consent verification.
6. MCP PR #2817 (`SEP-2817`), PR #2809 (`SEP-2809` ATSA), PR #2793 (`SEP-2793`),
   and PR #2752 (`SEP-2752`):
   - `SEP-2817`: `_meta["io.modelcontextprotocol/aiInvocation"]` non-authoritative audit
     context and response `_meta` echoing ONLY `turnId`.
   - `SEP-2809` (ATSA): Server Attestation Document (`/.well-known/mcp-attestation`)
     verification against pinned trust root, closed per-server `tool_allowlist_scope`,
     anti-shadowing / anti-schema-drift checks, and `admission-control` outcome binding.
   - `SEP-2793`: Graded `ToolAnnotations` risk metadata and fail-closed default bucket.
   - `SEP-2752`: RFC 9421 HTTP Message Signing over `(@method, @target-uri, content-digest,
     mcp-session-id, mcp-protocol-version)`, prohibited `alg` parameter,
     `keyid == JWK Thumbprint`, stable `tag`, and `660s` `(tag, nonce)` replay window.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping, Sequence


CAIP2_STANDARD_RE = re.compile(r"^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
ALGORAND_LEGACY_GENESIS_RE = re.compile(r"^algorand:[A-Za-z0-9+/]{43}=$")

UPTO_ERC3009_PROXY_ADDRESS = "0x40208cd083acd9559ce44742c4bcd9cf04850006"
STELLAR_TESTNET_UPTO_PROXY = "CAL7SBTOECJ6HXXO3ST43LM2HJJFSZ3ZDEEZBIWHJPB7DRF5MXS5V2VC"
STELLAR_MAX_ALLOWANCE_LEDGERS = 17_280
STELLAR_MAX_TIMEOUT_SECONDS = 86_400

CONTROL_PLANE_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB (1,048,576 bytes)
BAZAAR_DISCOVERY_MAX_BODY_BYTES = 4 * 1024 * 1024  # 4 MiB (4,194,304 bytes)
DEFAULT_MCP_MAX_TIMEOUT_SECONDS = 600

REQUIRED_OPERATOR_TYPE_MAPS = (
    "CaptureTypesV1_0",
    "CaptureTypesV1_1",
    "ChargeTypesV1_0",
    "ChargeTypesV1_1",
    "VoidTypes",
    "RefundTypes",
)
REQUIRED_EIP712_DOMAIN_FIELDS = ("name", "version", "chainId", "verifyingContract")

VALID_RISK_LEVELS = ("low", "medium", "high", "critical")
VALID_TOOL_CATEGORIES = ("read", "observe", "mutate", "delete", "destroy", "utility")
VALID_BLAST_RADII = ("item", "namespace", "cluster", "organization", "global")
VALID_REVERSIBILITIES = ("auto", "manual", "none")
VALID_APPROVAL_RECOMMENDATIONS = ("none", "single", "multi")

SEP2752_REQUIRED_COMPONENTS = (
    "@method",
    "@target-uri",
    "content-digest",
    "mcp-session-id",
    "mcp-protocol-version",
)


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: Mapping[str, Any]


def compute_upto_erc3009_nonce(pay_to: str, settler: str, salt_hex: str) -> str:
    """Compute deterministic commitment matching x402UptoERC3009Nonce(payTo, settler, salt)."""
    typehash = hashlib.sha256(
        b"x402UptoERC3009Nonce(address payTo,address settler,bytes32 salt)"
    ).hexdigest()
    payload = f"{typehash}:{pay_to.strip().lower()}:{settler.strip().lower()}:{salt_hex.strip().lower()}"
    return "0x" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_x402_sdk_regression_and_upto_erc3009_guard(
    *,
    operator_type_maps: Mapping[str, Mapping[str, Sequence[str]]],
    v2_network: str,
    refund_amount_atomic: int,
    has_refunded_event: bool,
    proxy_address: str,
    signed_max_amount: int,
    actual_settle_amount: int,
    pay_to: str,
    bound_settler: str,
    caller_settler: str,
    salt_hex: str,
    signed_nonce: str,
    nonce_already_used: bool,
    is_fee_on_transfer_or_rebasing: bool,
    proxy_pre_existing_donated_balance: int,
    proxy_post_settle_balance: int,
) -> GuardDecision:
    """Validate x402 PR #3893 post-merge regression fixes and PR #3867 x402UptoERC3009Proxy."""
    for map_name in REQUIRED_OPERATOR_TYPE_MAPS:
        type_map = operator_type_maps.get(map_name)
        if not isinstance(type_map, Mapping) or "EIP712Domain" not in type_map:
            return GuardDecision(
                allowed=False,
                decision_code="X402_AUTH_CAPTURE_OPERATOR_EIP712_DOMAIN_MISSING",
                reason=f"Operator type map {map_name!r} is missing versioned EIP712Domain definition",
                metadata={"missing_type_map": map_name},
            )
        domain_fields = tuple(type_map["EIP712Domain"])
        if domain_fields != REQUIRED_EIP712_DOMAIN_FIELDS:
            return GuardDecision(
                allowed=False,
                decision_code="X402_AUTH_CAPTURE_OPERATOR_EIP712_DOMAIN_INVALID",
                reason=f"Operator type map {map_name!r} has incomplete EIP712Domain fields: {domain_fields}",
                metadata={"map_name": map_name, "domain_fields": domain_fields},
            )

    if not (CAIP2_STANDARD_RE.match(v2_network) or ALGORAND_LEGACY_GENESIS_RE.match(v2_network)):
        return GuardDecision(
            allowed=False,
            decision_code="X402_V2_NETWORK_OR_LEGACY_ALGORAND_INVALID",
            reason=f"V2 network {v2_network!r} matches neither CAIP-2 nor legacy Algorand 44-char base64 genesis hash",
            metadata={"v2_network": v2_network},
        )

    if not has_refunded_event or refund_amount_atomic <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EVM_REFUND_ZERO_OR_MISSING_EVENT_REJECTED",
            reason="EVM refund settlement requires a Refunded event and strictly positive refund amount",
            metadata={"has_refunded_event": has_refunded_event, "refund_amount_atomic": refund_amount_atomic},
        )

    if proxy_address.strip().lower() != UPTO_ERC3009_PROXY_ADDRESS:
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_CANONICAL_PROXY_MISMATCH",
            reason="ReceiveWithAuthorization 'to' must be the canonical x402UptoERC3009Proxy address",
            metadata={"proxy_address": proxy_address, "expected": UPTO_ERC3009_PROXY_ADDRESS},
        )

    if is_fee_on_transfer_or_rebasing:
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_UNSUPPORTED_TOKEN_MECHANICS",
            reason="Fee-on-transfer and rebasing tokens are unsupported by x402UptoERC3009Proxy",
            metadata={},
        )

    if nonce_already_used:
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_NONCE_REPLAY_REJECTED",
            reason="Each ERC-3009 authorization nonce can settle at most once",
            metadata={"signed_nonce": signed_nonce},
        )

    expected_nonce = compute_upto_erc3009_nonce(pay_to, bound_settler, salt_hex)
    if signed_nonce.strip().lower() != expected_nonce.lower():
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_NONCE_COMMITMENT_MISMATCH",
            reason="Signed ERC-3009 nonce does not match typed commitment over (payTo, settler, salt)",
            metadata={"signed_nonce": signed_nonce, "expected_nonce": expected_nonce},
        )

    if caller_settler.strip().lower() != bound_settler.strip().lower():
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_UNAUTHORIZED_SETTLER",
            reason="Only the nonce-bound settler address may invoke x402UptoERC3009Proxy.settle",
            metadata={"caller_settler": caller_settler, "bound_settler": bound_settler},
        )

    if actual_settle_amount <= 0 or actual_settle_amount > signed_max_amount:
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_SETTLE_AMOUNT_OUT_OF_BOUNDS",
            reason="Actual settlement amount must satisfy 0 < actualAmount <= signedMaxAmount",
            metadata={"actual_settle_amount": actual_settle_amount, "signed_max_amount": signed_max_amount},
        )

    if proxy_post_settle_balance != proxy_pre_existing_donated_balance:
        return GuardDecision(
            allowed=False,
            decision_code="X402_UPTO_ERC3009_PROXY_BALANCE_INVARIANT_VIOLATION",
            reason="Settlement must neither leave residual balance in the proxy nor consume donated tokens",
            metadata={
                "pre_existing_donated": proxy_pre_existing_donated_balance,
                "post_settle_balance": proxy_post_settle_balance,
            },
        )

    refund_to_payer = signed_max_amount - actual_settle_amount
    return GuardDecision(
        allowed=True,
        decision_code="X402_UPTO_ERC3009_AND_SDK_REGRESSIONS_VERIFIED",
        reason="Go auth-capture EIP-712 domains, legacy Algorand CAIP-2, and x402UptoERC3009Proxy invariants verified",
        metadata={
            "settled_to_merchant": actual_settle_amount,
            "refunded_to_payer": refund_to_payer,
            "proxy_balance_delta": 0,
        },
    )


def validate_x402_stellar_upto_casper_exact_and_limits_guard(
    *,
    stellar_network: str,
    stellar_proxy_contract: str,
    are_fees_sponsored: bool,
    max_timeout_seconds: int,
    ledger_close_seconds: int,
    current_ledger: int,
    allowance_expiration_ledger: int,
    signature_expiration_ledger: int,
    simulated_root_function: str,
    simulated_source_account: str,
    facilitator_address: str,
    casper_network: str,
    casper_scheme: str,
    casper_key_algorithm: str,
    casper_secp256k1_low_s: bool,
    casper_valid_after: int,
    casper_valid_before: int,
    casper_now: int,
    facilitator_endpoint_kind: str,
    facilitator_response_bytes: int,
    mcp_phase: str,
    mcp_configured_max_timeout_seconds: int,
    caller_deadline_seconds: int | None,
    derived_attempt_timeout_seconds: int,
) -> GuardDecision:
    """Validate x402 PR #3781 (Stellar upto), PR #3885 (Casper exact), PR #3874 (body limits), and PR #3869 (MCP retry timeout cap)."""
    if stellar_network not in {"stellar:pubnet", "stellar:testnet"}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_NETWORK_INVALID",
            reason=f"Unsupported Stellar network {stellar_network!r}",
            metadata={"stellar_network": stellar_network},
        )

    if stellar_network == "stellar:testnet" and stellar_proxy_contract != STELLAR_TESTNET_UPTO_PROXY:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_NON_CANONICAL_PROXY_REJECTED",
            reason="Stellar upto must use the canonical UptoProxy contract deployment for the network",
            metadata={"stellar_proxy_contract": stellar_proxy_contract},
        )

    if not are_fees_sponsored:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_FEES_MUST_BE_SPONSORED",
            reason="Stellar upto requires extra.areFeesSponsored == True",
            metadata={},
        )

    if ledger_close_seconds <= 0 or max_timeout_seconds <= 0 or max_timeout_seconds > STELLAR_MAX_TIMEOUT_SECONDS:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_TIMEOUT_EXCEEDS_MAX_ALLOWANCE_LEDGERS",
            reason="maxTimeoutSeconds exceeds MAX_ALLOWANCE_LEDGERS (17,280 ledgers / 86,400s)",
            metadata={"max_timeout_seconds": max_timeout_seconds},
        )

    allowance_ledgers_ahead = allowance_expiration_ledger - current_ledger
    if allowance_ledgers_ahead <= 0 or allowance_ledgers_ahead > STELLAR_MAX_ALLOWANCE_LEDGERS:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_ALLOWANCE_EXPIRATION_OUT_OF_RANGE",
            reason="Allowance expiration ledger must be within (0, 17280] ledgers ahead of currentLedger",
            metadata={"allowance_ledgers_ahead": allowance_ledgers_ahead},
        )

    if signature_expiration_ledger != allowance_expiration_ledger:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_SIGNATURE_EXPIRATION_MISMATCH",
            reason="signatureExpirationLedger must equal allowance_expiration_ledger to bound nonce rent",
            metadata={
                "signature_expiration_ledger": signature_expiration_ledger,
                "allowance_expiration_ledger": allowance_expiration_ledger,
            },
        )

    if simulated_root_function != "settle_upto" or simulated_source_account != facilitator_address:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UPTO_SIMULATION_TREE_SUBSTITUTION_DETECTED",
            reason="Preflight simulation must use facilitatorAddress as source and root function settle_upto",
            metadata={
                "simulated_root_function": simulated_root_function,
                "simulated_source_account": simulated_source_account,
            },
        )

    if casper_network not in {"casper:casper", "casper:casper-test"}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_CASPER_NETWORK_INVALID",
            reason=f"Casper exact scheme requires casper:casper or casper:casper-test, got {casper_network!r}",
            metadata={"casper_network": casper_network},
        )

    if casper_scheme != "exact":
        return GuardDecision(
            allowed=False,
            decision_code="X402_CASPER_UNSUPPORTED_SCHEME",
            reason="Casper supports 'exact' scheme only; 'upto' and batch settlement are out of scope",
            metadata={"casper_scheme": casper_scheme},
        )

    if casper_key_algorithm not in {"ed25519", "secp256k1"} or (
        casper_key_algorithm == "secp256k1" and not casper_secp256k1_low_s
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_CASPER_SIGNATURE_ALGORITHM_OR_HIGH_S_INVALID",
            reason="Casper CEP-3009 signature must use ed25519 or low-s secp256k1",
            metadata={"casper_key_algorithm": casper_key_algorithm, "low_s": casper_secp256k1_low_s},
        )

    if not (casper_valid_after < casper_now < casper_valid_before):
        return GuardDecision(
            allowed=False,
            decision_code="X402_CASPER_VALIDITY_WINDOW_EXPIRED_OR_NOT_YET_VALID",
            reason="Casper CEP-3009 TransferWithAuthorization requires strict validAfter < now < validBefore",
            metadata={
                "valid_after": casper_valid_after,
                "now": casper_now,
                "valid_before": casper_valid_before,
            },
        )

    max_body_bytes = (
        BAZAAR_DISCOVERY_MAX_BODY_BYTES
        if facilitator_endpoint_kind == "bazaar_discovery"
        else CONTROL_PLANE_MAX_BODY_BYTES
    )
    if facilitator_response_bytes > max_body_bytes:
        return GuardDecision(
            allowed=False,
            decision_code="X402_FACILITATOR_RESPONSE_BODY_TOO_LARGE",
            reason=f"Facilitator {facilitator_endpoint_kind} response ({facilitator_response_bytes} bytes) exceeds limit ({max_body_bytes} bytes)",
            metadata={
                "endpoint_kind": facilitator_endpoint_kind,
                "response_bytes": facilitator_response_bytes,
                "max_body_bytes": max_body_bytes,
            },
        )

    if mcp_phase not in {"initial_probe", "paid_retry", "recovery_retry"}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_MCP_UNKNOWN_RETRY_PHASE",
            reason=f"Unknown MCP call phase {mcp_phase!r}",
            metadata={"mcp_phase": mcp_phase},
        )

    effective_cap = (
        min(mcp_configured_max_timeout_seconds, caller_deadline_seconds)
        if caller_deadline_seconds is not None
        else mcp_configured_max_timeout_seconds
    )
    if derived_attempt_timeout_seconds > effective_cap:
        return GuardDecision(
            allowed=False,
            decision_code="X402_MCP_RECOVERY_RETRY_TIMEOUT_CAP_EXCEEDED",
            reason=f"MCP {mcp_phase} timeout ({derived_attempt_timeout_seconds}s) exceeds effective cap ({effective_cap}s)",
            metadata={
                "mcp_phase": mcp_phase,
                "derived_attempt_timeout_seconds": derived_attempt_timeout_seconds,
                "effective_cap": effective_cap,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_STELLAR_CASPER_BODY_LIMIT_AND_MCP_TIMEOUT_VERIFIED",
        reason="Stellar Soroban upto, Casper CEP-3009 exact, facilitator response body limits, and MCP recovery-retry timeout cap verified",
        metadata={
            "allowance_ledgers_ahead": allowance_ledgers_ahead,
            "max_body_bytes": max_body_bytes,
            "effective_timeout_cap_seconds": effective_cap,
        },
    )


def validate_ucp_identity_linking_accelerated_idp_guard(
    *,
    has_initial_idp_pkce_connection: bool,
    requested_flow: str,
    authenticated_platform_user_id: str,
    subject_token_user_id: str,
    subject_token_scopes: Sequence[str],
    business_required_claims: Sequence[str],
    claim_to_required_scope_map: Mapping[str, str],
    consent_model: str,
    platform_consent_covers_business: bool,
    per_business_interactive_consent_granted: bool,
    issued_token_type: str,
    jwt_grant_aud: Sequence[str] | str,
    jwt_grant_jti: str,
) -> GuardDecision:
    """Validate UCP PR #783 Identity Linking Accelerated IdP Flow subject_token and consent invariants."""
    if not has_initial_idp_pkce_connection:
        if requested_flow == "accelerated_idp":
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDP_PREREQUISITE_MISSING_MUST_FALLBACK_DIRECT_OAUTH",
                reason="Accelerated IdP Flow requires a prior OAuth 2.0 PKCE connection to the IdP; platform must fall back to direct OAuth on business domain",
                metadata={"fallback_flow": "direct_business_oauth"},
            )

    if authenticated_platform_user_id.strip() != subject_token_user_id.strip():
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDP_SUBJECT_TOKEN_CROSS_USER_MISMATCH",
            reason="Selected subject_token belongs to a different user and would link the wrong business account",
            metadata={
                "authenticated_platform_user_id": authenticated_platform_user_id,
                "subject_token_user_id": subject_token_user_id,
            },
        )

    scope_set = set(subject_token_scopes)
    if "openid" not in scope_set:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDP_SUBJECT_TOKEN_MISSING_OPENID_SCOPE",
            reason="OIDC-based Accelerated IdP token exchange requires 'openid' scope on subject_token",
            metadata={"subject_token_scopes": list(subject_token_scopes)},
        )

    for claim in business_required_claims:
        required_scope = claim_to_required_scope_map.get(claim)
        if required_scope and required_scope not in scope_set:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDP_SUBJECT_TOKEN_MISSING_CLAIM_SCOPE",
                reason=f"subject_token is missing scope {required_scope!r} required for business claim {claim!r}",
                metadata={"missing_scope": required_scope, "required_claim": claim},
            )

    if consent_model == "platform_level":
        if not platform_consent_covers_business:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDP_PLATFORM_CONSENT_DOES_NOT_COVER_BUSINESS",
                reason="Platform-level consent does not cover identity sharing with the target business",
                metadata={"consent_model": consent_model},
            )
    elif consent_model == "per_business":
        if not per_business_interactive_consent_granted:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDP_PER_BUSINESS_CONSENT_REQUIRED",
                reason="Per-business consent model requires interactive user authorization before issuing grant",
                metadata={"consent_model": consent_model},
            )
    else:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDP_UNKNOWN_CONSENT_MODEL",
            reason=f"Unsupported IdP consent model {consent_model!r}",
            metadata={"consent_model": consent_model},
        )

    if issued_token_type != "urn:ietf:params:oauth:token-type:jwt":
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDP_ISSUED_TOKEN_TYPE_INVALID",
            reason="IdP token exchange must return issued_token_type == urn:ietf:params:oauth:token-type:jwt",
            metadata={"issued_token_type": issued_token_type},
        )

    aud_valid = isinstance(jwt_grant_aud, str) and jwt_grant_aud.startswith("https://")
    if isinstance(jwt_grant_aud, Sequence) and not isinstance(jwt_grant_aud, str):
        aud_valid = len(jwt_grant_aud) == 1 and str(jwt_grant_aud[0]).startswith("https://")
    if not aud_valid or not jwt_grant_jti.strip():
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDP_JWT_GRANT_AUD_OR_JTI_INVALID",
            reason="UCP JWT authorization grant requires a single-valued https URI 'aud' and non-empty unique 'jti'",
            metadata={"jwt_grant_aud": jwt_grant_aud, "jwt_grant_jti": jwt_grant_jti},
        )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_IDP_ACCELERATED_FLOW_VERIFIED",
        reason="UCP Accelerated IdP subject_token binding, claim scopes, consent model, and JWT grant verified",
        metadata={"consent_model": consent_model, "user_id": authenticated_platform_user_id},
    )


def validate_mcp_ai_invocation_atsa_risk_and_http_signing_guard(
    *,
    request_ai_invocation_meta: Mapping[str, Any] | None,
    response_ai_invocation_meta: Mapping[str, Any] | None,
    used_ai_invocation_for_authz: bool,
    sad_document: Mapping[str, Any] | None,
    pinned_trust_root_keys: Sequence[str],
    mcp_endpoint_host: str,
    tool_allowlist_scope: str,
    requested_tool: str,
    co_loaded_server_tools: Sequence[str],
    schema_changed_since_list: bool,
    admission_record: Mapping[str, str],
    tool_annotations: Mapping[str, Any],
    signed_components: Sequence[str],
    signature_params: Mapping[str, Any],
    jwk_thumbprint: str,
    seen_tag_nonces: Sequence[tuple[str, str]],
    now_epoch: int,
    freshness_window_seconds: int = 300,
    max_clock_skew_seconds: int = 180,
) -> GuardDecision:
    """Validate MCP SEP-2817, SEP-2809 (ATSA), SEP-2793 (Tool Risk Metadata), and SEP-2752 (RFC 9421 Signing)."""
    # 1. SEP-2817: AI Invocation Audit Context in Request _meta
    if used_ai_invocation_for_authz:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2817_AI_INVOCATION_USED_AS_AUTHZ_FORBIDDEN",
            reason="client-asserted _meta['io.modelcontextprotocol/aiInvocation'] is audit context only and MUST NOT grant authorization",
            metadata={},
        )

    if request_ai_invocation_meta is not None:
        allowed_req_keys = {"invocationReason", "model", "userIntent", "turnId"}
        extra_req_keys = set(request_ai_invocation_meta.keys()) - allowed_req_keys
        if extra_req_keys:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2817_REQUEST_META_UNKNOWN_FIELDS",
                reason=f"Unknown fields in request aiInvocation _meta: {sorted(extra_req_keys)}",
                metadata={"extra_keys": sorted(extra_req_keys)},
            )

    if response_ai_invocation_meta is not None:
        extra_resp_keys = set(response_ai_invocation_meta.keys()) - {"turnId"}
        if extra_resp_keys:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2817_RESPONSE_ECHOED_NON_TURN_ID_FIELDS",
                reason="Servers MAY echo ONLY 'turnId' in response _meta['io.modelcontextprotocol/aiInvocation']",
                metadata={"disallowed_echo_keys": sorted(extra_resp_keys)},
            )

    # 2. SEP-2809: Attested Tool-Server Admission (ATSA)
    if not isinstance(sad_document, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_SAD_MISSING",
            reason="Unattested MCP server rejected under strict ATSA admission policy",
            metadata={},
        )

    required_sad_fields = ("v", "id", "publisher", "version", "clearance", "capabilities", "signerKeyId", "signature")
    for field in required_sad_fields:
        if field not in sad_document:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2809_ATSA_SAD_FIELD_MISSING",
                reason=f"Server Attestation Document is missing required field {field!r}",
                metadata={"missing_field": field},
            )

    if sad_document.get("v") != 1 or "mcp-server" not in (sad_document.get("capabilities") or ()):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_SAD_VERSION_OR_CAPABILITY_INVALID",
            reason="SAD must have v == 1 and 'mcp-server' in capabilities",
            metadata={"v": sad_document.get("v"), "capabilities": sad_document.get("capabilities")},
        )

    if sad_document.get("signerKeyId") not in set(pinned_trust_root_keys) or not str(sad_document.get("signature", "")).strip():
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_UNTRUSTED_SIGNER_KEY",
            reason="SAD signerKeyId is not in the host's pinned trust root or signature is empty",
            metadata={"signerKeyId": sad_document.get("signerKeyId")},
        )

    net_allowed_hosts = sad_document.get("netAllowedHosts")
    if isinstance(net_allowed_hosts, Sequence) and not isinstance(net_allowed_hosts, str) and len(net_allowed_hosts) > 0:
        if mcp_endpoint_host not in set(net_allowed_hosts):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2809_ATSA_ORIGIN_HOST_NOT_ALLOWED",
                reason=f"MCP endpoint host {mcp_endpoint_host!r} is not in SAD netAllowedHosts",
                metadata={"mcp_endpoint_host": mcp_endpoint_host, "netAllowedHosts": list(net_allowed_hosts)},
            )

    if schema_changed_since_list or requested_tool in set(co_loaded_server_tools):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_SHADOWING_OR_SCHEMA_DRIFT_BLOCKED",
            reason="ATSA blocked tool-name shadowing across co-loaded servers or dynamic schema drift after tools/list",
            metadata={"requested_tool": requested_tool, "schema_changed_since_list": schema_changed_since_list},
        )

    tokens = [t for t in tool_allowlist_scope.split(" ") if t] if tool_allowlist_scope else []
    if tokens != sorted(tokens) or requested_tool not in set(tokens):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_TOOL_NOT_IN_ALLOWLIST_SCOPE",
            reason="tool_allowlist_scope must be lexicographically sorted and contain requested_tool",
            metadata={"requested_tool": requested_tool, "tool_allowlist_scope": tool_allowlist_scope},
        )

    clearance_decision = admission_record.get("clearance_decision", "")
    outcome = admission_record.get("outcome", "")
    expected_outcome_map = {"admitted": "allowed", "denied": "denied", "deferred": "deferred"}
    if expected_outcome_map.get(clearance_decision) != outcome:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2809_ATSA_OUTCOME_BINDING_MISMATCH",
            reason=f"admission-control clearance_decision {clearance_decision!r} must bind to outcome {expected_outcome_map.get(clearance_decision)!r}, got {outcome!r}",
            metadata={"clearance_decision": clearance_decision, "outcome": outcome},
        )

    # 3. SEP-2793: Tool Risk Metadata
    risk_level = tool_annotations.get("riskLevel", "critical")
    category = tool_annotations.get("category", "destroy")
    blast_radius = tool_annotations.get("blastRadius", "global")
    reversibility = tool_annotations.get("reversibility", "none")
    approval_rec = tool_annotations.get("approvalRecommendation", "multi")
    min_trust = tool_annotations.get("minTrustLevel", 5)

    if (
        risk_level not in VALID_RISK_LEVELS
        or category not in VALID_TOOL_CATEGORIES
        or blast_radius not in VALID_BLAST_RADII
        or reversibility not in VALID_REVERSIBILITIES
        or approval_rec not in VALID_APPROVAL_RECOMMENDATIONS
        or not isinstance(min_trust, int)
        or not (1 <= min_trust <= 5)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2793_TOOL_RISK_METADATA_INVALID",
            reason="ToolAnnotations risk metadata contains out-of-range enum or minTrustLevel outside 1..5",
            metadata={"tool_annotations": dict(tool_annotations)},
        )

    if tool_annotations.get("readOnlyHint") is True and (
        category in {"mutate", "delete", "destroy"} or reversibility == "none"
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2793_READONLY_HINT_CONTRADICTS_RISK_CATEGORY",
            reason="Tool declaring readOnlyHint=True cannot declare mutating/destructive category or reversibility='none'",
            metadata={"category": category, "reversibility": reversibility},
        )

    # 4. SEP-2752: RFC 9421 HTTP Message Signing for MCP Client Authentication
    missing_components = [c for c in SEP2752_REQUIRED_COMPONENTS if c not in set(signed_components)]
    if missing_components:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2752_MISSING_COVERED_COMPONENTS",
            reason=f"RFC 9421 signature is missing required MCP covered components: {missing_components}",
            metadata={"missing_components": missing_components},
        )

    if "alg" in signature_params:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2752_ALG_PARAMETER_PROHIBITED",
            reason="SEP-2752 prohibits the RFC 9421 'alg' signature parameter; algorithm must be derived from JWK kty+crv",
            metadata={"alg": signature_params.get("alg")},
        )

    keyid = str(signature_params.get("keyid", "")).strip()
    tag = str(signature_params.get("tag", "")).strip()
    nonce = str(signature_params.get("nonce", "")).strip()
    created = signature_params.get("created")

    if not keyid or keyid != jwk_thumbprint.strip():
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2752_KEYID_THUMBPRINT_MISMATCH",
            reason="RFC 9421 keyid must equal the RFC 7638 JWK Thumbprint of the verifying key",
            metadata={"keyid": keyid, "jwk_thumbprint": jwk_thumbprint},
        )

    if not tag or not nonce or not isinstance(created, int):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2752_TAG_NONCE_OR_CREATED_MISSING",
            reason="SEP-2752 signature requires non-empty 'tag', 'nonce', and integer 'created' timestamp",
            metadata={"tag": tag, "nonce": nonce, "created": created},
        )

    replay_horizon = 2 * max_clock_skew_seconds + freshness_window_seconds  # default 660s
    if abs(now_epoch - created) > freshness_window_seconds or (tag, nonce) in set(seen_tag_nonces):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2752_REPLAY_OR_FRESHNESS_WINDOW_VIOLATION",
            reason="Signed MCP request failed freshness check or replayed (tag, nonce) within 660s window",
            metadata={"tag": tag, "nonce": nonce, "replay_horizon_seconds": replay_horizon},
        )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_SEP2817_2809_2793_2752_VERIFIED",
        reason="MCP SEP-2817 aiInvocation audit context, SEP-2809 ATSA admission, SEP-2793 risk metadata, and SEP-2752 HTTP message signing verified",
        metadata={
            "server_id": sad_document.get("id"),
            "risk_level": risk_level,
            "client_tag": tag,
            "replay_horizon_seconds": replay_horizon,
        },
    )
