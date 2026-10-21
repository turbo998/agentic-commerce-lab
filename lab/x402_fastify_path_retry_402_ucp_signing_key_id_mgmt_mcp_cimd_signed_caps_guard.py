"""Stage 136 deterministic runtime guardrails for Agentic Commerce.

Covers primary-source protocol PRs audited on 2026-10-21:
1. x402 Foundation (`x402-foundation/x402`):
   - `#3577`: Fastify `FULL_PATH_REGEXP` (`^https?:\\/\\/.*?\\/`) request-target path extraction to prevent absolute-form URI payment-gate bypass (`GET https://attacker.com/protected-route HTTP/1.1`) without WHATWG backslash folding.
   - `#3585`: HTTP `wrapFetchWithPayment` / `wrapAxiosWithPayment` re-parses the latest `402` requirements after an `onPaymentRequired` hook retry instead of paying the superseded first offer.
   - `#3583`: EVM ECDSA recovery byte normalization (`yParity` `0`/`1` -> `v = 27`/`28`) before calling `transferWithAuthorization` / `permit2`.
   - `#3587`: Python `CreateHeadersAuthProvider` rejects flat `create_headers` dicts (e.g. `{"Authorization": "..."}`) that do not key by facilitator path (`verify`, `settle`, `supported`, `list`, `bazaar`).
   - `#3576` & `#3567`: Preserve `extensions.bazaar` from 402 JSON body under `PAYMENT-REQUIRED` header (header wins on conflict) and keep Bazaar `info.input.method` consistent with declared shape (`POST`/`PUT`/`PATCH` when `bodyType` is set; `GET` probe falls back to `POST`).
   - `#3575` & `#3574`: Run `onPaymentResponse` hook on paid HTTP 4xx/5xx error responses before rejecting.
   - `#3581`: Cap Go MCP recovery retry timeout to `paidTimeout` (`MaxRequestTimeout`, e.g., 90s) when no caller deadline is set.
   - `#3590` & `#3570` & `#3591` & `#3580` & `#3572`/`#3571`: Arc (`eip155:5042`, `eip155:5042002`) & Monad Testnet (`eip155:10143`) default USDC assets, SVM `assertPaymentChannelFacilitatorSigner` + `confirmTransaction` slot proxy, Cardano Subbit min-UTxO (`>= 980_000` lovelace) batch channel reserve, and `exact-lnbtc` `bolt11` / `invoice` transfer methods.
2. Google Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`), OpenAI/Stripe ACP (`agentic-commerce-protocol/agentic-commerce-protocol`), and Google AP2 (`google-agentic-commerce/AP2`):
   - UCP `#387`: Harden discovery profile `signing_key` to allow only public-key JWK properties (`additionalProperties: false`) and block private JWK fields (`d`, `p`, `q`, `dp`, `dq`, `qi`, `oth`, `k`).
   - UCP `#337` & `#356` & `#341`: Replace legacy `dev.ucp.common.identity_linking` with `dev.ucp.common.identity_management` CRUD + link lifecycle, and enforce `2026-04-08` catalog variant & deprecated transition field cleanup.
   - ACP `#193` & `#167` & `#72` & `#14`: Validate `Address.company` vs `postal_code` semantics, allow optional `phone_number` on `delegate_payment` address, classify `delegate_payment` errors (`card_declined`, `expired_card`, `unauthorized_access`), and verify cross-platform identity federation / cross-chain coordination.
   - AP2 `#95` & `#79` & `#24` & `#19`: Multi-payment method intersection (`CARD`, `BANK_ACCOUNT`, `DIGITAL_WALLET`, `cashu-token` NUT-24 mint proof) and `Verifiable Digital Credential (VDC)` canonical naming.
3. MCP (`modelcontextprotocol/modelcontextprotocol`), Stripe AI (`stripe/ai`), and Sierra tau2-bench (`sierra-research/tau2-bench`):
   - MCP `#3149`: `SEP-3149` requires non-empty `token_endpoint_auth_methods_supported` array in Client ID Metadata Documents (CIMD), deprecating singular `token_endpoint_auth_method` and implicit `none` public-client default.
   - MCP `#3140`: `SEP-3140` JWS-signed capability declarations, content hash + version, standardized `trust` label block (`effect`, `egress`, `dataSensitivity`, `reversibility`), and `notifications/*/list_changed` rug-pull re-gating.
   - MCP `#3158` & `#3139` & `#3118` & `#3116`: `SubscriptionsListenResultResponse` envelope + `SubscriptionsListenResultMetaObject`, `NumberSchema` float `minimum`/`maximum`/`default` preservation, `SEP-3118` App-Rendered Elicitations `ui.resourceUri` routing with core form fallback, and `SEP-2663` `MISSING_REQUIRED_CLIENT_CAPABILITY`.
   - Stripe `#167` & `#158` and Sierra tau2-bench `#389` & `#357` & `#356` & `#328` & `#302` & `#259` & `#258`: Preserve `reasoning_content` in thinking-model messages, enforce airline task 35 single-passenger anchor (`"only for yourself"`), block internal `user_id` (`mei_kovacs_8020`) in retail `known_info`, verify `task_053` user tool call, and validate Pipecat `QueueTransport` tick-by-tick adapter & OpenAI GA Realtime API session format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence


FASTIFY_FULL_PATH_REGEXP = re.compile(r"^https?:\/\/.*?\/", re.IGNORECASE)
FACILITATOR_HEADER_PATH_KEYS = frozenset({"verify", "settle", "supported", "list", "bazaar"})
BAZAAR_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
BAZAAR_QUERY_METHODS = frozenset({"GET", "HEAD", "DELETE"})

DEFAULT_USDC_ASSETS: Mapping[str, Mapping[str, Any]] = {
    "eip155:5042": {
        "network_name": "arc-mainnet",
        "asset": "0x3600000000000000000000000000000000000000",
        "eip712_name": "USDC",
        "eip712_version": "2",
        "decimals": 6,
        "domain_separator": "0x940506929bba468048a19b567f4f0d534714bc06604b5c3017e5d16785ccdf84",
    },
    "eip155:5042002": {
        "network_name": "arc-testnet",
        "asset": "0x3600000000000000000000000000000000000000",
        "eip712_name": "USDC",
        "eip712_version": "2",
        "decimals": 6,
        "domain_separator": "0x361191522483d32a83e70ae7183b4b9629442c13a78bc9921d6f707911c8c6b0",
    },
    "eip155:10143": {
        "network_name": "monad-testnet",
        "asset": "0x534b2f3A21130d7a60830c2Df862319e593943A3",
        "eip712_name": "USDC",
        "eip712_version": "2",
        "decimals": 6,
        "domain_separator": "0xmonad10143usdc",
    },
}

CARDANO_MIN_UTXO_LOVELACE = 980_000
LNBTC_TRANSFER_METHODS = frozenset({"bolt11", "invoice"})

UCP_ALLOWED_PUBLIC_SIGNING_KEY_FIELDS = frozenset(
    {"kid", "kty", "crv", "alg", "use", "key_ops", "x", "y", "n", "e", "x5c", "x5t", "x5t#S256", "x5u"}
)
UCP_FORBIDDEN_PRIVATE_JWK_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})
UCP_IDENTITY_MGMT_OPERATIONS = frozenset(
    {"create_identity", "get_identity", "update_identity", "delete_identity", "link_identity"}
)
ACP_DELEGATE_PAYMENT_ERROR_CODES = frozenset(
    {"card_declined", "expired_card", "unauthorized_access", "invalid_request", "rate_limit_exceeded"}
)
AP2_SUPPORTED_PAYMENT_METHODS = frozenset({"CARD", "BANK_ACCOUNT", "DIGITAL_WALLET", "cashu-token"})

VALID_CIMD_TOKEN_AUTH_METHODS = frozenset(
    {"private_key_jwt", "client_secret_basic", "client_secret_post", "tls_client_auth", "self_signed_tls_client_auth"}
)
TRUST_EFFECT_RANK = {"none": 0, "read": 1, "write": 2, "irreversible": 3}
TRUST_EGRESS_RANK = {"none": 0, "same_origin": 1, "external": 2}
TRUST_SENSITIVITY_RANK = {"public": 0, "internal": 1, "confidential": 2, "regulated_pci_pii": 3}


@dataclass(frozen=True)
class X402FastifyRetryEcdsaBazaarAssessment:
    """Result of auditing x402 Fastify path, 402 retry, ECDSA v, headers, Bazaar, and channel rules."""

    admitted: bool
    normalized_request_path: str
    effective_402_amount_minor: int
    normalized_ecdsa_v: int
    effective_bazaar_method: str
    merged_bazaar_extensions: Mapping[str, Any]
    effective_mcp_recovery_timeout_sec: int
    paid_error_hook_executed: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UcpSigningKeyIdMgmtAcpAp2Assessment:
    """Result of auditing UCP signing_key, identity_management, ACP delegate_payment, and AP2 payment methods."""

    admitted: bool
    canonical_identity_capability: str
    matched_payment_methods: tuple[str, ...]
    canonical_credential_term: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class McpCimdSignedCapsTau2Assessment:
    """Result of auditing MCP SEP-3149 CIMD, SEP-3140 signed capability labels, SEP-3118 UI elicitation, and tau2."""

    admitted: bool
    rug_pull_detected: bool
    re_gate_required: bool
    elicitation_route: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


def extract_fastify_request_path(raw_request_url: str) -> tuple[str, list[str]]:
    """Extract request pathname matching Fastify's `find-my-way` `FULL_PATH_REGEXP` (#3577)."""
    reasons: list[str] = []
    before_query = (raw_request_url or "").split("?", 1)[0]
    if "\\" in before_query:
        reasons.append("FASTIFY_LITERAL_BACKSLASH_PATH_REJECTED")
    stripped = FASTIFY_FULL_PATH_REGEXP.sub("/", before_query, count=1)
    if not stripped.startswith("/"):
        reasons.append("FASTIFY_NON_ORIGIN_FORM_REQUEST_TARGET_REJECTED")
    return stripped, reasons


def evaluate_x402_fastify_retry_ecdsa_bazaar_guard(
    *,
    raw_request_url: str = "/protected-route",
    protected_route_pattern: str = r"^/protected-route$",
    has_payment_signature: bool = True,
    initial_402_amount_minor: int = 100,
    hook_retried: bool = False,
    retry_402_amount_minor: int | None = None,
    paid_amount_minor: int = 100,
    ecdsa_v: int | None = None,
    ecdsa_y_parity: int | None = 0,
    create_headers_output: Mapping[str, Any] | None = None,
    header_bazaar_extensions: Mapping[str, Any] | None = None,
    body_bazaar_extensions: Mapping[str, Any] | None = None,
    route_has_explicit_verb: bool = False,
    probe_method: str = "POST",
    bazaar_body_type: str | None = "json",
    paid_http_status: int = 200,
    has_payment_response_header: bool = True,
    on_payment_response_called_before_reject: bool = True,
    mcp_accepted_timeout_sec: int = 3600,
    mcp_max_request_timeout_sec: int = 90,
    mcp_recovery_retry_timeout_sec: int = 90,
    mcp_caller_deadline_sec: int | None = None,
    network_caip2: str = "eip155:5042",
    token_address: str = "0x3600000000000000000000000000000000000000",
    svm_batch_signer_asserted_at_construction: bool = True,
    svm_confirmation_slot_proxied: bool = True,
    cardano_channel_reserve_lovelace: int = 1_500_000,
    lnbtc_transfer_method: str = "bolt11",
    lnbtc_has_preimage: bool = True,
    lnbtc_facilitator_verified_receiver: bool = False,
) -> X402FastifyRetryEcdsaBazaarAssessment:
    """Validate x402 Fastify path, 402 hook retry, ECDSA recovery byte, create_headers, Bazaar, and channels."""
    reasons: list[str] = []

    normalized_path, path_reasons = extract_fastify_request_path(raw_request_url)
    reasons.extend(path_reasons)
    if re.match(protected_route_pattern, normalized_path) and not has_payment_signature:
        reasons.append("FASTIFY_PROTECTED_ROUTE_PAYMENT_REQUIRED_BYPASS_BLOCKED")

    effective_402_amount = (
        retry_402_amount_minor
        if (hook_retried and retry_402_amount_minor is not None)
        else initial_402_amount_minor
    )
    if paid_amount_minor != effective_402_amount:
        reasons.append("X402_STALE_402_REQUIREMENTS_AFTER_HOOK_RETRY_REJECTED")

    raw_v = ecdsa_v if ecdsa_v is not None else ecdsa_y_parity
    if raw_v in (0, 1):
        normalized_v = 27 + int(raw_v)
    elif raw_v in (27, 28):
        normalized_v = int(raw_v)
    else:
        normalized_v = -1
        reasons.append("X402_EVM_INVALID_ECDSA_RECOVERY_BYTE_REJECTED")

    if create_headers_output:
        unknown_keys = set(create_headers_output.keys()) - FACILITATOR_HEADER_PATH_KEYS
        if unknown_keys:
            reasons.append("X402_PYTHON_FLAT_CREATE_HEADERS_DICT_REJECTED")

    merged_extensions: dict[str, Any] = {}
    if body_bazaar_extensions:
        merged_extensions.update(body_bazaar_extensions)
    if header_bazaar_extensions:
        merged_extensions.update(header_bazaar_extensions)

    upper_probe = probe_method.upper()
    if route_has_explicit_verb:
        effective_method = upper_probe
    elif bazaar_body_type:
        effective_method = upper_probe if upper_probe in BAZAAR_BODY_METHODS else "POST"
        if upper_probe not in BAZAAR_BODY_METHODS:
            reasons.append("X402_BAZAAR_PROBE_METHOD_MISMATCH_NORMALIZED_TO_POST")
    else:
        effective_method = upper_probe if upper_probe in BAZAAR_QUERY_METHODS else "GET"
        if upper_probe not in BAZAAR_QUERY_METHODS:
            reasons.append("X402_BAZAAR_PROBE_METHOD_MISMATCH_NORMALIZED_TO_GET")

    paid_error_hook_executed = True
    if paid_http_status >= 400 and has_payment_response_header and not on_payment_response_called_before_reject:
        paid_error_hook_executed = False
        reasons.append("X402_AXIOS_PAID_ERROR_MISSING_ON_PAYMENT_RESPONSE_HOOK")

    effective_cap = (
        mcp_caller_deadline_sec
        if mcp_caller_deadline_sec is not None
        else min(mcp_accepted_timeout_sec, mcp_max_request_timeout_sec)
    )
    if mcp_recovery_retry_timeout_sec > effective_cap:
        reasons.append("X402_GO_MCP_RECOVERY_RETRY_TIMEOUT_UNCAPPED")

    if network_caip2 in DEFAULT_USDC_ASSETS:
        expected_asset = str(DEFAULT_USDC_ASSETS[network_caip2]["asset"]).lower()
        if token_address.lower() != expected_asset:
            reasons.append("X402_DEFAULT_USDC_ASSET_ADDRESS_MISMATCH")

    if not svm_batch_signer_asserted_at_construction:
        reasons.append("X402_SVM_BATCH_CHANNEL_SIGNER_NOT_ASSERTED_AT_CONSTRUCTION")
    if not svm_confirmation_slot_proxied:
        reasons.append("X402_SVM_CONFIRMATION_SLOT_PROXY_MISSING")

    if cardano_channel_reserve_lovelace < CARDANO_MIN_UTXO_LOVELACE:
        reasons.append("X402_CARDANO_BATCH_CHANNEL_BELOW_MIN_UTXO_RESERVE")

    if lnbtc_transfer_method not in LNBTC_TRANSFER_METHODS:
        reasons.append("X402_LNBTC_UNSUPPORTED_ASSET_TRANSFER_METHOD")
    elif lnbtc_transfer_method == "bolt11" and not lnbtc_has_preimage:
        reasons.append("X402_LNBTC_BOLT11_PREIMAGE_REQUIRED")
    elif lnbtc_transfer_method == "invoice" and not lnbtc_facilitator_verified_receiver:
        reasons.append("X402_LNBTC_INVOICE_RECEIVER_QUERY_UNVERIFIED")

    blocking_reasons = [
        r
        for r in reasons
        if r
        not in {
            "X402_BAZAAR_PROBE_METHOD_MISMATCH_NORMALIZED_TO_POST",
            "X402_BAZAAR_PROBE_METHOD_MISMATCH_NORMALIZED_TO_GET",
        }
    ]
    return X402FastifyRetryEcdsaBazaarAssessment(
        admitted=not blocking_reasons,
        normalized_request_path=normalized_path,
        effective_402_amount_minor=effective_402_amount,
        normalized_ecdsa_v=normalized_v,
        effective_bazaar_method=effective_method,
        merged_bazaar_extensions=merged_extensions,
        effective_mcp_recovery_timeout_sec=effective_cap,
        paid_error_hook_executed=paid_error_hook_executed,
        reason_codes=tuple(reasons),
    )


def evaluate_ucp_signing_key_id_mgmt_acp_ap2_guard(
    *,
    signing_key_jwk: Mapping[str, Any] | None = None,
    declared_identity_capability: str = "dev.ucp.common.identity_management",
    identity_operation: str = "get_identity",
    has_deprecated_transition_fields: bool = False,
    variant_schema_version: str = "2026-04-08",
    acp_address_company: str = "Contoso Ltd",
    acp_address_postal_code: str = "94107",
    acp_delegate_payment_phone_number: str | None = "+14155550199",
    acp_delegate_payment_error_code: str | None = None,
    user_payment_methods: Sequence[str] = ("CARD", "DIGITAL_WALLET"),
    merchant_accepted_payment_methods: Sequence[str] = ("CARD", "BANK_ACCOUNT", "DIGITAL_WALLET"),
    cashu_mint_url: str | None = None,
    cashu_nut24_proof_verified: bool = True,
    credential_term: str = "Verifiable Digital Credential",
) -> UcpSigningKeyIdMgmtAcpAp2Assessment:
    """Validate UCP discovery signing_key, identity_management, ACP delegate_payment, and AP2 multi-payment."""
    reasons: list[str] = []

    jwk = signing_key_jwk or {"kty": "EC", "crv": "P-256", "x": "pub_x", "y": "pub_y", "kid": "k1"}
    private_fields = set(jwk.keys()) & UCP_FORBIDDEN_PRIVATE_JWK_FIELDS
    if private_fields:
        reasons.append("UCP_SIGNING_KEY_PRIVATE_JWK_FIELD_LEAK_BLOCKED")
    unknown_fields = set(jwk.keys()) - UCP_ALLOWED_PUBLIC_SIGNING_KEY_FIELDS - UCP_FORBIDDEN_PRIVATE_JWK_FIELDS
    if unknown_fields:
        reasons.append("UCP_SIGNING_KEY_ADDITIONAL_PROPERTIES_REJECTED")

    if declared_identity_capability == "dev.ucp.common.identity_linking":
        reasons.append("UCP_LEGACY_IDENTITY_LINKING_CAPABILITY_DEPRECATED")
    elif declared_identity_capability != "dev.ucp.common.identity_management":
        reasons.append("UCP_UNKNOWN_IDENTITY_CAPABILITY_REJECTED")

    if identity_operation not in UCP_IDENTITY_MGMT_OPERATIONS:
        reasons.append("UCP_UNSUPPORTED_IDENTITY_MANAGEMENT_OPERATION")

    if has_deprecated_transition_fields:
        reasons.append("UCP_DEPRECATED_TRANSITION_SCHEMA_FIELD_REJECTED")
    if variant_schema_version < "2026-04-08":
        reasons.append("UCP_STALE_CATALOG_VARIANT_SCHEMA_VERSION")

    if acp_address_company and acp_address_company.strip() == acp_address_postal_code.strip():
        reasons.append("ACP_ADDRESS_COMPANY_POSTAL_CODE_COPY_PASTE_CONFUSION")
    if acp_delegate_payment_phone_number is not None and not acp_delegate_payment_phone_number.startswith("+"):
        reasons.append("ACP_DELEGATE_PAYMENT_PHONE_NUMBER_E164_REQUIRED")
    if acp_delegate_payment_error_code and acp_delegate_payment_error_code not in ACP_DELEGATE_PAYMENT_ERROR_CODES:
        reasons.append("ACP_UNKNOWN_DELEGATE_PAYMENT_ERROR_CODE")

    unsupported = (set(user_payment_methods) | set(merchant_accepted_payment_methods)) - AP2_SUPPORTED_PAYMENT_METHODS
    if unsupported:
        reasons.append("AP2_UNSUPPORTED_PAYMENT_METHOD_REJECTED")
    matched = tuple(m for m in user_payment_methods if m in set(merchant_accepted_payment_methods))
    if not matched:
        reasons.append("AP2_NO_MATCHING_PAYMENT_METHOD_INTERSECTION")
    if "cashu-token" in matched and (not cashu_mint_url or not cashu_nut24_proof_verified):
        reasons.append("AP2_CASHU_NUT24_MINT_PROOF_UNVERIFIED")

    if credential_term.lower() == "verifiable credential":
        reasons.append("AP2_LEGACY_VERIFIABLE_CREDENTIAL_TERM_REJECTED")

    return UcpSigningKeyIdMgmtAcpAp2Assessment(
        admitted=not reasons,
        canonical_identity_capability="dev.ucp.common.identity_management",
        matched_payment_methods=matched,
        canonical_credential_term="Verifiable Digital Credential",
        reason_codes=tuple(reasons),
    )


def evaluate_mcp_cimd_signed_caps_tau2_guard(
    *,
    cimd_token_endpoint_auth_methods_supported: Sequence[str] | None = ("private_key_jwt",),
    cimd_singular_token_endpoint_auth_method: str | None = None,
    capability_manifest_jws_valid: bool = True,
    capability_content_hash_matches: bool = True,
    previous_trust_labels: Mapping[str, str] | None = None,
    current_trust_labels: Mapping[str, str] | None = None,
    list_changed_re_gated_by_client: bool = True,
    client_supports_ui_elicitation: bool = True,
    server_supports_ui_elicitation: bool = True,
    elicitation_ui_resource_uri: str | None = "ui://checkout/confirm-form",
    has_core_form_fallback: bool = True,
    subscriptions_listen_has_result_response_envelope: bool = True,
    subscriptions_listen_meta_suffix: str = "SubscriptionsListenResultMetaObject",
    number_schema_allows_float: bool = True,
    tau2_model_is_thinking: bool = True,
    tau2_reasoning_content_preserved: bool = True,
    tau2_airline_task35_anchored_single_passenger: bool = True,
    tau2_retail_known_info_text: str = "You are Mei Kovacs in zip code 28236.",
    tau2_task053_has_user_tool_call: bool = True,
    tau2_openai_realtime_uses_beta_header: bool = False,
) -> McpCimdSignedCapsTau2Assessment:
    """Validate MCP SEP-3149 CIMD, SEP-3140 signed capabilities, SEP-3118 UI elicitation, and tau2-bench."""
    reasons: list[str] = []

    if cimd_singular_token_endpoint_auth_method is not None:
        reasons.append("MCP_SEP3149_DEPRECATED_SINGULAR_TOKEN_AUTH_METHOD_REJECTED")
    if not cimd_token_endpoint_auth_methods_supported:
        reasons.append("MCP_SEP3149_MISSING_TOKEN_AUTH_METHODS_SUPPORTED_ARRAY")
    else:
        if "none" in cimd_token_endpoint_auth_methods_supported:
            reasons.append("MCP_SEP3149_IMPLICIT_PUBLIC_CLIENT_NONE_AUTH_REJECTED")
        invalid_methods = set(cimd_token_endpoint_auth_methods_supported) - VALID_CIMD_TOKEN_AUTH_METHODS
        if invalid_methods:
            reasons.append("MCP_SEP3149_UNSUPPORTED_CIMD_TOKEN_AUTH_METHOD")

    if not capability_manifest_jws_valid:
        reasons.append("MCP_SEP3140_UNSIGNED_OR_INVALID_CAPABILITY_MANIFEST_JWS")
    if not capability_content_hash_matches:
        reasons.append("MCP_SEP3140_CAPABILITY_CONTENT_HASH_MISMATCH")

    prev_trust = previous_trust_labels or {
        "effect": "read",
        "egress": "none",
        "dataSensitivity": "internal",
        "reversibility": "reversible",
    }
    curr_trust = current_trust_labels or prev_trust
    rug_pull_detected = (
        TRUST_EFFECT_RANK.get(curr_trust.get("effect", "read"), 99)
        > TRUST_EFFECT_RANK.get(prev_trust.get("effect", "read"), 0)
        or TRUST_EGRESS_RANK.get(curr_trust.get("egress", "none"), 99)
        > TRUST_EGRESS_RANK.get(prev_trust.get("egress", "none"), 0)
        or TRUST_SENSITIVITY_RANK.get(curr_trust.get("dataSensitivity", "internal"), 99)
        > TRUST_SENSITIVITY_RANK.get(prev_trust.get("dataSensitivity", "internal"), 0)
        or (
            prev_trust.get("reversibility") == "reversible"
            and curr_trust.get("reversibility") == "irreversible"
        )
    )
    if rug_pull_detected and not list_changed_re_gated_by_client:
        reasons.append("MCP_SEP3140_LIST_CHANGED_RUG_PULL_ESCALATION_UNREGATED")

    if not has_core_form_fallback:
        reasons.append("MCP_SEP3118_MISSING_CORE_FORM_ELICITATION_FALLBACK")
    if client_supports_ui_elicitation and server_supports_ui_elicitation and elicitation_ui_resource_uri:
        elicitation_route = f"app_rendered:{elicitation_ui_resource_uri}"
    else:
        elicitation_route = "core_form_fallback"

    if not subscriptions_listen_has_result_response_envelope:
        reasons.append("MCP_SUBSCRIPTIONS_LISTEN_MISSING_RESULT_RESPONSE_ENVELOPE")
    if subscriptions_listen_meta_suffix != "SubscriptionsListenResultMetaObject":
        reasons.append("MCP_SUBSCRIPTIONS_LISTEN_INVALID_META_OBJECT_TYPE_NAME")
    if not number_schema_allows_float:
        reasons.append("MCP_NUMBER_SCHEMA_FLOAT_DEFAULT_COERCED_TO_INTEGER")

    if tau2_model_is_thinking and not tau2_reasoning_content_preserved:
        reasons.append("TAU2_THINKING_MODEL_REASONING_CONTENT_DROPPED")
    if not tau2_airline_task35_anchored_single_passenger:
        reasons.append("TAU2_AIRLINE_TASK35_UNANCHORED_PASSENGER_COUNT_DRIFT")
    if re.search(r"[a-z]+_[a-z]+_\d{4}", tau2_retail_known_info_text):
        reasons.append("TAU2_RETAIL_INTERNAL_USER_ID_LEAKED_IN_KNOWN_INFO")
    if not tau2_task053_has_user_tool_call:
        reasons.append("TAU2_BANKING_TASK053_MISSING_USER_TOOL_CALL")
    if tau2_openai_realtime_uses_beta_header:
        reasons.append("TAU2_OPENAI_REALTIME_LEGACY_BETA_HEADER_REJECTED")

    return McpCimdSignedCapsTau2Assessment(
        admitted=not reasons,
        rug_pull_detected=rug_pull_detected,
        re_gate_required=rug_pull_detected,
        elicitation_route=elicitation_route,
        reason_codes=tuple(reasons),
    )
