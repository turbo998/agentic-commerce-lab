"""Stage 228 deterministic runtime guards covering 48 primary-source PRs across
`visa/trusted-agent-protocol`, `stripe/agent-toolkit`,
`agentic-commerce-protocol/agentic-commerce-protocol`,
`Universal-Commerce-Protocol/ucp`, `google-agentic-commerce/AP2`,
`google-agentic-commerce/a2a-x402`, `coinbase/agentkit`,
`modelcontextprotocol/{python-sdk,typescript-sdk,go-sdk,rust-sdk,csharp-sdk,inspector}`,
and `sierra-research/tau2-bench`:

- PR-01 (`visa/trusted-agent-protocol#21`, `#18`, & `#11`):
  Visa TAP merchant backend RFC 9421 §2.5 `@signature-params` base reconstruction,
  individually quoted covered components, `ed25519` + `ed25519-ml-dsa-65` hybrid PQ
  dual verification (HTTP 503 fail-closed when `oqs` is absent), `did:web:` / `did:tenzro:`
  DID resolution, and x402 USDC settlement on Solana & Base.
- PR-02 (`stripe/agent-toolkit#586`, `#579`, `#569`, `#567`, & Stripe MCP `2026-10-31` cutoff):
  Stripe Agent Toolkit atomic in-memory skill sync (preserving existing skills on download
  failure), OpenAI Agent Plugin `extensions` metadata, provider-neutral hook scripts,
  `STRIPE_CLI_TELEMETRY_OPTOUT=1` on Claude startup checks, and Stripe MCP `2026-10-31`
  rejection (`401` + OAuth discovery challenge) of `sk_live_*` / untagged `rk_live_*`.
- PR-03 (`agentic-commerce-protocol/agentic-commerce-protocol#316`, `#314`, & `#310`):
  ACP SEP `#303` Dispute Resolution Extension (`dispute_resolution` / ATDRP-0.1) binding
  AP2 mandates/receipts + ACP Order into a signed `Order.adjustment` (`type: "dispute"`),
  host-side pre-spend authorization gate, and JSON Schema <-> OpenAPI property drift detection.
- PR-04 (`Universal-Commerce-Protocol/ucp#985`, `#982`, & `#981`):
  UCP registration-neutral identity linking (`private_key_jwt` & CIMD vs. `client_secret`),
  `ucp-schema` 2.0.0 bundled whole-file `$ref` type-link restoration, and postal
  `dev.shopify.common.address_line_components` (`street_address` / `extended_address` / `address_code`).
- PR-05 (`google-agentic-commerce/AP2#385`, `#384`, `#383`, `#378`, & `#377`):
  Google AP2 SD-JWT `cnf.jwk` JSON-mode serialization (`use="sig"` as string), optional
  `has_reference_in_store_cb` `None` check, chronological ISO 8601 `execution_date` bounds,
  and ISO 4217 currency-exponent `Decimal` `payment.budget` minor-unit conversion.
- PR-06 (`google-agentic-commerce/a2a-x402#191`, `#190`, & `#186`):
  Google A2A-x402 `PaymentRequirements.extra` EIP-712 domain signing (`name`/`version`
  without calling reverting `version()`), CSPRNG 32-byte EIP-3009 nonce generation
  (`os.urandom(32)`), and deferred A2A `completed` event until `settle_payment()` finishes.
- PR-07 (`coinbase/agentkit#1599`, `#1598`, & `#1597`):
  Coinbase AgentKit `token_verdict` x402 pre-signature spend guard (`<= $0.02` USDC on Base,
  typed `SOLID`/`CAUTION`/`DANGER` verdict & 6 signals) and Python ERC-20 / swap approval
  integer receipt `status == 1` check.
- PR-08 (`coinbase/agentkit#1596`, `#1593`, & `#1591`):
  Coinbase AgentKit `BotsRated` unpaid signed seller/MCP preflight probe (`never pays` in
  read-only mode) and `SelfPaid` zero-net-cost Base USDC Aave V3 / Morpho yield collateral guard.
- PR-09 (`modelcontextprotocol/python-sdk#3759`, `#3758`, `#3757`, & `#3756`):
  MCP Python SDK `HEAD /sse` `405 Method Not Allowed` (`Allow: GET`), bare `dict`/`set`/`frozenset`
  & `typing.Dict[str, X]` structured output parity, and auto-generated schema `title` stripping.
- PR-10 (`modelcontextprotocol/typescript-sdk#3096`, `#3095`, `#3093`, `#3092`, & `#3091`):
  MCP TypeScript SDK prompt `icons` preservation, recursive `$defs` object-shaped `$ref`
  detection, atomic `cacheToolMetadata` swap, monotonic `resetForReconnect` cache epoch,
  and post-response `AbortSignal` listener removal.
- PR-11 (`modelcontextprotocol/go-sdk#1449`, `#1447`, & `#1446`):
  MCP Go SDK `ErrConnectionClosed` wrapping on interrupted calls/notifications, nil titled
  enum entry `-32602` elicitation rejection, and custom `slog.Level` floor mapping.
- PR-12 (`modelcontextprotocol/rust-sdk#1393` & `modelcontextprotocol/csharp-sdk#1955`):
  MCP Rust SDK same-origin IPv6 ULA (`fc00::/7`) OAuth issuer admission and MCP C# SDK
  non-completing cancellation-token task verification.
- PR-13 (`modelcontextprotocol/inspector#2795`, `#2794`, & `#2792`):
  MCP Inspector CLI/mcpdo HTTP 429 `rate_limited` retry timing envelope, static client
  SEP-2352 issuer stamp persistence, and cross-client DCR secret stamp rejection.
- PR-14 (`modelcontextprotocol/inspector#2793`, `#2791`, & `#2790`):
  MCP Inspector `--load-connections` multi-session HTTP/SSE load guard (rejecting `stdio`),
  non-loopback web bind security warning, and `$HOME` test catalog `os.tmpdir()` isolation.
- PR-15 (`sierra-research/tau2-bench#680` & `#677`):
  Sierra tau2-bench `LLMSoloAgent` private `done` tool list isolation and retail `known_info`
  internal `user_id` (`mei_kovacs_8020`) leakage prevention.
- PR-16 (`sierra-research/tau2-bench#674`, `#679`, `#676`, & `#675`):
  Sierra tau2-bench non-object tool arguments & empty agent replies scored as `AGENT_ERROR`
  (retained in score denominator) and leaderboard submission integrity (`Ava Zero` / `phonic-1`).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import ipaddress
from typing import Any, Callable
from urllib.parse import urlparse


ISO4217_ZERO_DECIMAL = {
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW",
    "PYG", "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
}
ISO4217_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
ISO4217_FOUR_DECIMAL = {"CLF", "UYW"}

MCP_LOG_LEVEL_THRESHOLDS: list[tuple[int, str]] = [
    (-4, "debug"),
    (0, "info"),
    (2, "notice"),
    (4, "warning"),
    (8, "error"),
    (10, "critical"),
    (12, "alert"),
    (14, "emergency"),
]


def _verdict(
    *,
    allow: bool,
    code: str,
    reason: str,
    upstream_pr: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "allow": allow,
        "code": code,
        "reason": reason,
        "upstream_pr": upstream_pr,
        "details": details or {},
    }


def iso4217_minor_unit_exponent(currency: str) -> int:
    code = currency.upper().strip()
    if code in ISO4217_ZERO_DECIMAL:
        return 0
    if code in ISO4217_THREE_DECIMAL:
        return 3
    if code in ISO4217_FOUR_DECIMAL:
        return 4
    return 2


def major_to_minor_units(value: str | int | float | Decimal, currency: str) -> int:
    exp = iso4217_minor_unit_exponent(currency)
    scale = Decimal(10) ** exp
    quantized = (Decimal(str(value)) * scale).to_integral_value(rounding=ROUND_FLOOR)
    return int(quantized)


# ---------------------------------------------------------------------------
# PR-01: visa/trusted-agent-protocol#21, #18, & #11
# ---------------------------------------------------------------------------
def evaluate_visa_tap_rfc9421_hybrid_pq_did_x402_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce Visa TAP RFC 9421 signature base, hybrid PQ + DID resolution, and x402 checkout."""
    upstream_pr = "visa/trusted-agent-protocol#21, #18, #11"

    has_signature_params_final_line = bool(payload.get("has_signature_params_final_line", True))
    covered_components_individually_quoted = bool(payload.get("covered_components_individually_quoted", True))
    supports_arbitrary_label_and_param_order = bool(payload.get("supports_arbitrary_label_and_param_order", True))
    if (
        not has_signature_params_final_line
        or not covered_components_individually_quoted
        or not supports_arbitrary_label_and_param_order
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_TAP_NONCONFORMANT_RFC9421_SIGNATURE_BASE",
            reason="TAP merchant verifier must end Sig-Base with @signature-params and parse individually quoted components with arbitrary labels/order (trusted-agent-protocol#21).",
            upstream_pr=upstream_pr,
        )

    alg = str(payload.get("alg", "ed25519")).lower()
    if alg not in {"rsa-pss-sha256", "ed25519", "ed25519-ml-dsa-65"}:
        return _verdict(
            allow=False,
            code="BLOCKED_TAP_UNSUPPORTED_SIGNATURE_ALG",
            reason="TAP verifier must support rsa-pss-sha256, ed25519, and ed25519-ml-dsa-65 (trusted-agent-protocol#21, #18).",
            upstream_pr=upstream_pr,
            details={"alg": alg},
        )

    if alg == "ed25519-ml-dsa-65":
        oqs_installed = bool(payload.get("oqs_installed", True))
        http_status_on_missing_oqs = int(payload.get("http_status_on_missing_oqs", 503))
        ed25519_verified = bool(payload.get("ed25519_verified", True))
        ml_dsa_65_verified = bool(payload.get("ml_dsa_65_verified", True))
        if not oqs_installed:
            if http_status_on_missing_oqs != 503:
                return _verdict(
                    allow=False,
                    code="BLOCKED_TAP_HYBRID_PQ_MISSING_OQS_MUST_FAIL_CLOSED_503",
                    reason="Hybrid ed25519-ml-dsa-65 verification must fail closed with HTTP 503 when liboqs-python is unavailable (trusted-agent-protocol#18).",
                    upstream_pr=upstream_pr,
                    details={"http_status_on_missing_oqs": http_status_on_missing_oqs},
                )
        elif not (ed25519_verified and ml_dsa_65_verified):
            return _verdict(
                allow=False,
                code="BLOCKED_TAP_HYBRID_PQ_PARTIAL_SIGNATURE_REJECTED",
                reason="Both Ed25519 and ML-DSA-65 signatures over the same Sig-Base must verify (trusted-agent-protocol#18).",
                upstream_pr=upstream_pr,
                details={"ed25519_verified": ed25519_verified, "ml_dsa_65_verified": ml_dsa_65_verified},
            )

    key_id = str(payload.get("key_id", "did:web:agent.example.com"))
    registered_did_methods = set(payload.get("registered_did_methods", ["web"]))
    if key_id.startswith("did:"):
        parts = key_id.split(":")
        method = parts[1] if len(parts) >= 3 else ""
        if method not in registered_did_methods:
            return _verdict(
                allow=False,
                code="BLOCKED_TAP_UNREGISTERED_DID_METHOD",
                reason="TAP agent-registry only resolves explicitly registered DID methods such as did:web: or opt-in did:tenzro: (trusted-agent-protocol#18).",
                upstream_pr=upstream_pr,
                details={"key_id": key_id, "registered_did_methods": sorted(registered_did_methods)},
            )

    x402_enabled = bool(payload.get("x402_enabled", True))
    if x402_enabled:
        x402_network = str(payload.get("x402_network", "eip155:84532"))
        solana_ata_ready = bool(payload.get("solana_ata_ready", True))
        cdn_logs_x402_headers = bool(payload.get("cdn_logs_x402_headers", True))
        if x402_network.startswith("solana:") and not solana_ata_ready:
            return _verdict(
                allow=False,
                code="BLOCKED_TAP_X402_SOLANA_ATA_MISSING",
                reason="TAP x402 Solana USDC checkout requires merchant ATA setup prior to settlement (trusted-agent-protocol#11).",
                upstream_pr=upstream_pr,
            )
        if not cdn_logs_x402_headers:
            return _verdict(
                allow=False,
                code="BLOCKED_TAP_CDN_X402_HEADER_LOGGING_MISSING",
                reason="TAP CDN proxy must preserve and log x402 payment headers across checkout requests (trusted-agent-protocol#11).",
                upstream_pr=upstream_pr,
            )

    return _verdict(
        allow=True,
        code="ALLOW_VISA_TAP_RFC9421_HYBRID_PQ_DID_X402_VALID",
        reason="Visa TAP RFC 9421 signature verification, hybrid PQ + DID resolution, and x402 settlement invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-02: stripe/agent-toolkit#586, #579, #569, #567 & Stripe MCP 2026-10-31
# ---------------------------------------------------------------------------
def evaluate_stripe_toolkit_atomic_skill_sync_and_mcp_cutoff_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce Stripe Agent Toolkit atomic skill sync, plugin hooks/metadata, and MCP 2026-10-31 key cutoff."""
    upstream_pr = "stripe/agent-toolkit#586, #579, #569, #567; docs.stripe.com/mcp.md"

    download_error_count = int(payload.get("download_error_count", 0))
    output_dirs_cleaned_before_download = bool(payload.get("output_dirs_cleaned_before_download", False))
    previous_skills_preserved_on_failure = bool(payload.get("previous_skills_preserved_on_failure", True))
    if output_dirs_cleaned_before_download or (download_error_count > 0 and not previous_skills_preserved_on_failure):
        return _verdict(
            allow=False,
            code="BLOCKED_STRIPE_SKILL_SYNC_WIPED_ON_DOWNLOAD_FAILURE",
            reason="Skill sync must buffer downloads in memory and abort before cleaning output directories if any download fails (agent-toolkit#586).",
            upstream_pr=upstream_pr,
            details={
                "download_error_count": download_error_count,
                "output_dirs_cleaned_before_download": output_dirs_cleaned_before_download,
            },
        )

    has_openai_plugin_extensions_metadata = bool(payload.get("has_openai_plugin_extensions_metadata", True))
    speculative_codex_dir_removed = bool(payload.get("speculative_codex_dir_removed", True))
    provider_neutral_hooks_synced = bool(payload.get("provider_neutral_hooks_synced", True))
    if not (has_openai_plugin_extensions_metadata and speculative_codex_dir_removed and provider_neutral_hooks_synced):
        return _verdict(
            allow=False,
            code="BLOCKED_STRIPE_PLUGIN_METADATA_OR_HOOK_DRIFT",
            reason="Stripe Agent Plugin must publish OpenAI extensions metadata, remove speculative codex files, and use shared-provider-scripts/provider-hooks (agent-toolkit#579, #569).",
            upstream_pr=upstream_pr,
        )

    startup_check_telemetry_optout = bool(payload.get("startup_check_telemetry_optout", True))
    report_usage_telemetry_enabled = bool(payload.get("report_usage_telemetry_enabled", True))
    if not startup_check_telemetry_optout or not report_usage_telemetry_enabled:
        return _verdict(
            allow=False,
            code="BLOCKED_STRIPE_STARTUP_TELEMETRY_MISCONFIGURED",
            reason="Claude startup checks (stripe --version / whoami) must set STRIPE_CLI_TELEMETRY_OPTOUT=1 while keeping report_usage enabled (agent-toolkit#567).",
            upstream_pr=upstream_pr,
        )

    mcp_key_type = str(payload.get("mcp_key_type", "rak_agent"))
    has_agent_tag = bool(payload.get("has_agent_tag", True))
    rejection_http_status = int(payload.get("rejection_http_status", 200))
    has_oauth_discovery_challenge = bool(payload.get("has_oauth_discovery_challenge", True))
    if mcp_key_type == "sk_full_access" or (mcp_key_type == "rk_restricted" and not has_agent_tag):
        if rejection_http_status != 401 or not has_oauth_discovery_challenge:
            return _verdict(
                allow=False,
                code="BLOCKED_STRIPE_MCP_UNSUPPORTED_API_KEY_NOT_REJECTED_401",
                reason="By the 2026-10-31 cutoff, Stripe MCP must reject full-access secret keys and untagged restricted keys with HTTP 401 and an OAuth discovery challenge.",
                upstream_pr=upstream_pr,
                details={"mcp_key_type": mcp_key_type, "rejection_http_status": rejection_http_status},
            )

    return _verdict(
        allow=True,
        code="ALLOW_STRIPE_TOOLKIT_SYNC_AND_MCP_CUTOFF_VALID",
        reason="Stripe Agent Toolkit atomic skill sync, plugin hooks/metadata, telemetry opt-out, and MCP key cutoff invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-03: agentic-commerce-protocol/agentic-commerce-protocol#316, #314, & #310
# ---------------------------------------------------------------------------
def evaluate_acp_atdrp_dispute_host_auth_and_schema_drift_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce ACP SEP #303 ATDRP-0.1 dispute extension, host pre-spend check, and JSON Schema/OpenAPI parity."""
    upstream_pr = "agentic-commerce-protocol/agentic-commerce-protocol#316, #314, #310"

    required_evidence = {"checkout_mandate", "payment_mandate", "checkout_receipt", "payment_receipt", "acp_order"}
    provided_evidence = set(payload.get("dispute_evidence_artifacts", list(required_evidence)))
    if not required_evidence.issubset(provided_evidence):
        return _verdict(
            allow=False,
            code="BLOCKED_ACP_ATDRP_MISSING_MANDATE_OR_RECEIPT_EVIDENCE",
            reason="ATDRP-0.1 dispute records must bind AP2 checkout_mandate, payment_mandate, checkout_receipt, payment_receipt, and the ACP Order (acp#316).",
            upstream_pr=upstream_pr,
            details={"missing": sorted(required_evidence - provided_evidence)},
        )

    determination = payload.get("determination") or {}
    decision = str(determination.get("decision", "overturn"))
    has_signer_and_seal = bool(determination.get("signer")) and bool(determination.get("seal"))
    order_adjustment_type = str(payload.get("order_adjustment_type", "dispute"))
    if decision not in {"uphold", "overturn"} or not has_signer_and_seal or order_adjustment_type != "dispute":
        return _verdict(
            allow=False,
            code="BLOCKED_ACP_ATDRP_INVALID_DETERMINATION_OR_ADJUSTMENT",
            reason="ATDRP-0.1 determination requires uphold/overturn decision, signer, cryptographic seal, and Order.adjustment of type 'dispute' (acp#316).",
            upstream_pr=upstream_pr,
        )

    sensitive_tool = str(payload.get("sensitive_tool", "complete_checkout_session"))
    host_authorization_checked = bool(payload.get("host_authorization_checked", True))
    if sensitive_tool in {"complete_checkout_session", "delegate_payment"} and not host_authorization_checked:
        return _verdict(
            allow=False,
            code="BLOCKED_ACP_MISSING_HOST_SPEND_AUTHORIZATION_GATE",
            reason="Sensitive ACP spend calls (complete_checkout_session, delegate_payment) require host-side allow/deny authorization gating (acp#314).",
            upstream_pr=upstream_pr,
            details={"sensitive_tool": sensitive_tool},
        )

    json_schema_props = set(payload.get("json_schema_properties", ["id", "line_items", "currency", "totals"]))
    openapi_props = set(payload.get("openapi_properties", ["id", "line_items", "currency", "totals"]))
    if json_schema_props != openapi_props:
        return _verdict(
            allow=False,
            code="BLOCKED_ACP_JSON_SCHEMA_OPENAPI_PROPERTY_DRIFT",
            reason="Comparable object schemas in JSON Schema $defs and OpenAPI components.schemas must have identical property sets (acp#310).",
            upstream_pr=upstream_pr,
            details={
                "json_schema_only": sorted(json_schema_props - openapi_props),
                "openapi_only": sorted(openapi_props - json_schema_props),
            },
        )

    return _verdict(
        allow=True,
        code="ALLOW_ACP_ATDRP_HOST_AUTH_AND_SCHEMA_PARITY_VALID",
        reason="ACP SEP #303 ATDRP-0.1 dispute resolution, host spend gate, and JSON Schema/OpenAPI property parity satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp#985, #982, & #981
# ---------------------------------------------------------------------------
def evaluate_ucp_identity_linking_cimd_bundled_refs_address_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP registration-neutral identity linking, bundled ref link restoration, and postal address components."""
    upstream_pr = "Universal-Commerce-Protocol/ucp#985, #982, #981"

    client_id_model = str(payload.get("client_id_model", "cimd"))
    token_auth_method = str(payload.get("token_auth_method", "private_key_jwt"))
    presumes_single_registration_model = bool(payload.get("presumes_single_registration_model", False))
    if presumes_single_registration_model:
        return _verdict(
            allow=False,
            code="BLOCKED_UCP_IDENTITY_LINKING_PRESUMED_REGISTRATION_MODEL",
            reason="UCP identity-linking must remain neutral across out-of-band registration and advertised registration-free methods such as CIMD (ucp#985).",
            upstream_pr=upstream_pr,
        )
    if token_auth_method == "client_secret" and client_id_model in {"cimd", "confidential_platform"}:
        return _verdict(
            allow=False,
            code="BLOCKED_UCP_IDENTITY_LINKING_CLIENT_SECRET_FORBIDDEN",
            reason="CIMD and confidential platforms must authenticate with private_key_jwt (RFC 7523 §2.2) or public-client PKCE rather than client_secret (ucp#985).",
            upstream_pr=upstream_pr,
            details={"client_id_model": client_id_model, "token_auth_method": token_auth_method},
        )

    unresolved_bundled_whole_file_type_links = int(payload.get("unresolved_bundled_whole_file_type_links", 0))
    if unresolved_bundled_whole_file_type_links > 0:
        return _verdict(
            allow=False,
            code="BLOCKED_UCP_BUNDLED_SCHEMA_BROKEN_TYPE_LINKS",
            reason="Bundled ucp-schema 2.0.0 reference generator must restore whole-file $ref type links after non-root $id stripping (ucp#982).",
            upstream_pr=upstream_pr,
            details={"unresolved_bundled_whole_file_type_links": unresolved_bundled_whole_file_type_links},
        )

    address_components = payload.get("address_line_components") or {}
    address_code_in_street_line = bool(payload.get("address_code_in_street_line", False))
    allowed_component_keys = {
        "street_name",
        "street_number",
        "additional_information",
        "district",
        "subdistrict",
    }
    unknown_keys = set(address_components.keys()) - allowed_component_keys
    if unknown_keys or address_code_in_street_line:
        return _verdict(
            allow=False,
            code="BLOCKED_UCP_ADDRESS_LINE_COMPONENTS_INVALID",
            reason="address_line_components only permits street_name, street_number, additional_information, district, subdistrict, and keeps address_code separate from street lines (ucp#981).",
            upstream_pr=upstream_pr,
            details={"unknown_keys": sorted(unknown_keys), "address_code_in_street_line": address_code_in_street_line},
        )

    return _verdict(
        allow=True,
        code="ALLOW_UCP_IDENTITY_LINKING_BUNDLED_REFS_ADDRESS_VALID",
        reason="UCP registration-neutral identity linking, ucp-schema 2.0.0 type links, and postal address_line_components invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-05: google-agentic-commerce/AP2#385, #384, #383, #378, & #377
# ---------------------------------------------------------------------------
def _parse_iso8601_date_or_dt(raw: str) -> date | datetime:
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return date.fromisoformat(raw)
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _compare_ap2_window(exec_raw: str, not_before_raw: str, not_after_raw: str) -> bool:
    exec_val = _parse_iso8601_date_or_dt(exec_raw)
    nb_val = _parse_iso8601_date_or_dt(not_before_raw)
    na_val = _parse_iso8601_date_or_dt(not_after_raw)

    for bound, is_lower in ((nb_val, True), (na_val, False)):
        if isinstance(exec_val, datetime) and isinstance(bound, datetime):
            ok = exec_val >= bound if is_lower else exec_val <= bound
        else:
            exec_d = exec_val.date() if isinstance(exec_val, datetime) else exec_val
            bound_d = bound.date() if isinstance(bound, datetime) else bound
            ok = exec_d >= bound_d if is_lower else exec_d <= bound_d
        if not ok:
            return False
    return True


def evaluate_ap2_sdjwt_json_mode_iso8601_and_iso4217_budget_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce AP2 SD-JWT cnf.jwk JSON-mode dump, None-safe receipt callback, ISO 8601 window, and ISO 4217 budget."""
    upstream_pr = "google-agentic-commerce/AP2#385, #384, #383, #378, #377"

    cnf_jwk_use_is_str = isinstance(payload.get("cnf_jwk_use", "sig"), str)
    cnf_jwk_dumped_json_mode = bool(payload.get("cnf_jwk_dumped_json_mode", True))
    if not cnf_jwk_use_is_str or not cnf_jwk_dumped_json_mode:
        return _verdict(
            allow=False,
            code="BLOCKED_AP2_SDJWT_CNF_JWK_ENUM_NOT_JSON_SERIALIZED",
            reason="ParsedToken.cnf_jwk must use model_dump(mode='json', exclude_none=True) so JWK enum fields like 'use' serialize as strings (AP2#385, #383).",
            upstream_pr=upstream_pr,
        )

    unconditional_none_callback_invoked = bool(payload.get("unconditional_none_callback_invoked", False))
    if unconditional_none_callback_invoked:
        return _verdict(
            allow=False,
            code="BLOCKED_AP2_VERIFY_RECEIPT_NONE_CALLBACK_TYPEERROR",
            reason="ReceiptClient.verify_receipt must check has_reference_in_store_cb is not None before calling it (AP2#384).",
            upstream_pr=upstream_pr,
        )

    exec_date = str(payload.get("execution_date", "2026-03-31"))
    not_before = str(payload.get("not_before", "2026-03-31T00:00:00Z"))
    not_after = str(payload.get("not_after", "2026-04-30T23:59:59Z"))
    expected_window_pass = bool(payload.get("expected_window_pass", True))
    try:
        actual_window_pass = _compare_ap2_window(exec_date, not_before, not_after)
    except ValueError:
        actual_window_pass = False

    used_lexical_comparison = bool(payload.get("used_lexical_comparison", False))
    if used_lexical_comparison or actual_window_pass != expected_window_pass:
        return _verdict(
            allow=False,
            code="BLOCKED_AP2_EXECUTION_DATE_LEXICAL_OR_OUT_OF_WINDOW",
            reason="ExecutionDateEvaluator must parse and compare ISO 8601 instants/dates chronologically and fail closed on invalid dates (AP2#378).",
            upstream_pr=upstream_pr,
            details={
                "execution_date": exec_date,
                "actual_window_pass": actual_window_pass,
                "expected_window_pass": expected_window_pass,
            },
        )

    currency = str(payload.get("currency", "JPY"))
    budget_max_major = payload.get("budget_max_major", "1000")
    payment_amount_minor = int(payload.get("payment_amount_minor", 1000))
    reported_budget_limit_minor = int(
        payload.get("reported_budget_limit_minor", major_to_minor_units(budget_max_major, currency))
    )
    true_limit_minor = major_to_minor_units(budget_max_major, currency)
    if reported_budget_limit_minor != true_limit_minor or payment_amount_minor > true_limit_minor:
        return _verdict(
            allow=False,
            code="BLOCKED_AP2_BUDGET_ISO4217_MINOR_UNIT_VIOLATION",
            reason="BudgetEvaluator must convert budget.max via Decimal and ISO 4217 currency exponents (0/2/3/4) and reject payments above the minor-unit cap (AP2#377).",
            upstream_pr=upstream_pr,
            details={
                "currency": currency,
                "true_limit_minor": true_limit_minor,
                "reported_budget_limit_minor": reported_budget_limit_minor,
                "payment_amount_minor": payment_amount_minor,
            },
        )

    return _verdict(
        allow=True,
        code="ALLOW_AP2_SDJWT_ISO8601_AND_ISO4217_BUDGET_VALID",
        reason="AP2 SD-JWT cnf.jwk JSON-mode serialization, None-safe receipt callback, ISO 8601 execution window, and ISO 4217 budget invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-06: google-agentic-commerce/a2a-x402#191, #190, & #186
# ---------------------------------------------------------------------------
def evaluate_a2a_x402_extra_domain_random_nonce_deferred_completion_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce A2A-x402 extra EIP-712 domain, 32-byte random EIP-3009 nonce, and deferred paid completion."""
    upstream_pr = "google-agentic-commerce/a2a-x402#191, #190, #186"

    extra = payload.get("requirements_extra") or {}
    queried_contract_version_when_extra_present = bool(
        payload.get("queried_contract_version_when_extra_present", False)
    )
    signed_domain_name = str(payload.get("signed_domain_name", extra.get("name", "USDC")))
    signed_domain_version = str(payload.get("signed_domain_version", extra.get("version", "2")))
    if extra.get("name") and extra.get("version"):
        if (
            queried_contract_version_when_extra_present
            or signed_domain_name != extra["name"]
            or signed_domain_version != extra["version"]
        ):
            return _verdict(
                allow=False,
                code="BLOCKED_A2A_X402_IGNORED_ADVERTISED_EIP712_EXTRA_DOMAIN",
                reason="process_payment must sign with EIP-712 domain (name, version) advertised in requirements.extra without calling reverting contract version() (a2a-x402#191).",
                upstream_pr=upstream_pr,
            )

    called_eip2612_nonces = bool(payload.get("called_eip2612_nonces", False))
    nonce_byte_length = int(payload.get("nonce_byte_length", 32))
    nonces_unique_across_payments = bool(payload.get("nonces_unique_across_payments", True))
    if called_eip2612_nonces or nonce_byte_length != 32 or not nonces_unique_across_payments:
        return _verdict(
            allow=False,
            code="BLOCKED_A2A_X402_SEQUENTIAL_OR_INVALID_EIP3009_NONCE",
            reason="EIP-3009 authorizations must generate unique 32-byte random nonces via os.urandom(32) without calling EIP-2612 nonces(owner) (a2a-x402#190).",
            upstream_pr=upstream_pr,
        )

    completed_emitted_before_settlement = bool(payload.get("completed_emitted_before_settlement", False))
    settlement_succeeded = bool(payload.get("settlement_succeeded", True))
    final_task_state = str(payload.get("final_task_state", "completed" if settlement_succeeded else "failed"))
    final_response_has_payment_receipt = bool(payload.get("final_response_has_payment_receipt", settlement_succeeded))
    if completed_emitted_before_settlement:
        return _verdict(
            allow=False,
            code="BLOCKED_A2A_X402_PREMATURE_COMPLETION_BEFORE_SETTLEMENT",
            reason="A2A paid delegate must defer response-ending completion until settle_payment() finishes so the event queue stays open for receipt attachment (a2a-x402#186).",
            upstream_pr=upstream_pr,
        )
    if settlement_succeeded and (final_task_state != "completed" or not final_response_has_payment_receipt):
        return _verdict(
            allow=False,
            code="BLOCKED_A2A_X402_MISSING_FINAL_SETTLEMENT_RECEIPT",
            reason="Successful settlement must attach payment receipt metadata to the final completed response (a2a-x402#186).",
            upstream_pr=upstream_pr,
        )
    if not settlement_succeeded and final_task_state != "failed":
        return _verdict(
            allow=False,
            code="BLOCKED_A2A_X402_SETTLEMENT_FAILURE_MASKED_AS_COMPLETED",
            reason="Failed settlement must emit a final failed task status rather than completed (a2a-x402#186).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_A2A_X402_DOMAIN_NONCE_AND_DEFERRED_COMPLETION_VALID",
        reason="A2A-x402 advertised EIP-712 domain, 32-byte random EIP-3009 nonce, and deferred post-settlement completion invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-07: coinbase/agentkit#1599, #1598, & #1597
# ---------------------------------------------------------------------------
def evaluate_agentkit_token_verdict_spend_cap_and_receipt_status_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce AgentKit token_verdict x402 spend guard (<= $0.02 USDC on Base) & integer receipt status check."""
    upstream_pr = "coinbase/agentkit#1599, #1598, #1597"

    challenge_network = str(payload.get("challenge_network", "eip155:8453"))
    challenge_asset_symbol = str(payload.get("challenge_asset_symbol", "USDC"))
    challenge_amount_atomic = int(payload.get("challenge_amount_atomic", 20000))
    max_amount_per_payment_atomic = int(payload.get("max_amount_per_payment_atomic", 20000))
    if (
        challenge_network != "eip155:8453"
        or challenge_asset_symbol != "USDC"
        or challenge_amount_atomic <= 0
        or challenge_amount_atomic > max_amount_per_payment_atomic
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_TOKEN_VERDICT_SPEND_CAP_EXCEEDED",
            reason="token_verdict payment policy must filter challenges to USDC on Base (eip155:8453) at or under maxAmountPerPayment ($0.02 / 20000 atomic units) before signing (agentkit#1599, #1598).",
            upstream_pr=upstream_pr,
            details={
                "challenge_network": challenge_network,
                "challenge_amount_atomic": challenge_amount_atomic,
                "max_amount_per_payment_atomic": max_amount_per_payment_atomic,
            },
        )

    verdict_label = str(payload.get("verdict_label", "SOLID"))
    verdict_score = int(payload.get("verdict_score", 88))
    signal_count = int(payload.get("signal_count", 6))
    if verdict_label not in {"SOLID", "CAUTION", "DANGER"} or not (0 <= verdict_score <= 100) or signal_count != 6:
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_TOKEN_VERDICT_SCHEMA_INVALID",
            reason="token_verdict response must provide SOLID/CAUTION/DANGER verdict, 0..100 score, and 6 market-structure signals (agentkit#1598).",
            upstream_pr=upstream_pr,
        )

    tx_receipt_status = payload.get("tx_receipt_status", 1)
    reported_tx_success = bool(payload.get("reported_tx_success", True))
    if not isinstance(tx_receipt_status, int) or (tx_receipt_status != 1 and reported_tx_success):
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_REVERTED_ERC20_OR_SWAP_RECEIPT_IGNORED",
            reason="Python ERC20 transfer/approve and swap approval must check integer receipt status == 1 and fail on reverted (status == 0) transactions (agentkit#1597).",
            upstream_pr=upstream_pr,
            details={"tx_receipt_status": tx_receipt_status, "reported_tx_success": reported_tx_success},
        )

    return _verdict(
        allow=True,
        code="ALLOW_AGENTKIT_TOKEN_VERDICT_AND_RECEIPT_STATUS_VALID",
        reason="AgentKit token_verdict pre-signature spend guard and ERC-20/swap integer receipt status verification satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-08: coinbase/agentkit#1596, #1593, & #1591
# ---------------------------------------------------------------------------
def evaluate_agentkit_botsrated_preflight_and_selfpaid_yield_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce AgentKit BotsRated unpaid signed preflight probe and SelfPaid zero-net-cost Base yield guard."""
    upstream_pr = "coinbase/agentkit#1596, #1593, #1591"

    mode = str(payload.get("botsrated_mode", "preflight"))
    paid_check_opt_in = bool(payload.get("paid_check_opt_in", False))
    wallet_payment_signed = bool(payload.get("wallet_payment_signed", False))
    probe_receipt_signed = bool(payload.get("probe_receipt_signed", True))
    challenge_402_valid = bool(payload.get("challenge_402_valid", True))
    if (mode == "preflight" or not paid_check_opt_in) and wallet_payment_signed:
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_BOTSRATED_UNOPTED_WALLET_PAYMENT",
            reason="BotsRated read-only/preflight lookups must never spend from the agent wallet unless paid check is explicitly opted in (agentkit#1596, #1593).",
            upstream_pr=upstream_pr,
        )
    if not probe_receipt_signed or not challenge_402_valid:
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_BOTSRATED_INVALID_SELLER_PREFLIGHT",
            reason="BotsRated preflight requires a signed probe receipt and a valid 402 challenge before paying an x402 seller (agentkit#1593).",
            upstream_pr=upstream_pr,
        )

    selfpaid_chain_id = int(payload.get("selfpaid_chain_id", 8453))
    selfpaid_protocol = str(payload.get("selfpaid_protocol", "aave_v3"))
    collateral_usdc = float(payload.get("collateral_usdc", 500.0))
    apy_bps = int(payload.get("apy_bps", 620))
    lockup_days = int(payload.get("lockup_days", 0))
    days_to_reimbursement = float(payload.get("days_to_reimbursement", 7.3))
    if (
        selfpaid_chain_id != 8453
        or selfpaid_protocol not in {"aave_v3", "morpho"}
        or collateral_usdc <= 0
        or apy_bps <= 0
        or lockup_days != 0
        or days_to_reimbursement <= 0
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_AGENTKIT_SELFPAID_INVALID_YIELD_QUOTE",
            reason="SelfPaid zero-net-cost USDC payments require Base Mainnet (8453), Aave V3 or Morpho yield collateral, zero lockup, and positive APY/reimbursement horizon (agentkit#1591).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_AGENTKIT_BOTSRATED_AND_SELFPAID_VALID",
        reason="AgentKit BotsRated unpaid seller/MCP preflight and SelfPaid Base USDC yield-collateral invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/python-sdk#3759, #3758, #3757, & #3756
# ---------------------------------------------------------------------------
def evaluate_mcp_python_sse_head_405_structured_dict_and_title_strip_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce MCP Python SDK HEAD /sse 405 response, bare dict/typing.Dict structured output, and title stripping."""
    upstream_pr = "modelcontextprotocol/python-sdk#3759, #3758, #3757, #3756"

    http_method = str(payload.get("http_method", "HEAD")).upper()
    if http_method == "HEAD":
        head_status = int(payload.get("head_status", 405))
        allow_header = str(payload.get("allow_header", "GET"))
        opened_sse_session_or_stream = bool(payload.get("opened_sse_session_or_stream", False))
        if head_status != 405 or allow_header != "GET" or opened_sse_session_or_stream:
            return _verdict(
                allow=False,
                code="BLOCKED_PYTHON_SDK_HEAD_SSE_OPENED_STREAM_OR_WRONG_STATUS",
                reason="MCPServer.sse_app() must answer HEAD on the SSE endpoint with 405 and Allow: GET without opening a session or stream (python-sdk#3759).",
                upstream_pr=upstream_pr,
            )

    bare_dict_has_object_output_schema = bool(payload.get("bare_dict_has_object_output_schema", True))
    typing_dict_wrapped_in_result = bool(payload.get("typing_dict_wrapped_in_result", False))
    bare_set_wrapped_in_result = bool(payload.get("bare_set_wrapped_in_result", True))
    bare_list_unstructured_by_default = bool(payload.get("bare_list_unstructured_by_default", True))
    if (
        not bare_dict_has_object_output_schema
        or typing_dict_wrapped_in_result
        or not bare_set_wrapped_in_result
        or not bare_list_unstructured_by_default
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_PYTHON_SDK_RETURN_ANNOTATION_SCHEMA_MISMATCH",
            reason="Bare dict and typing.Dict[str, X] must emit unwrapped object outputSchema, bare set/frozenset wrap in {'result': ...}, and bare list/tuple stay unstructured by default (python-sdk#3758, #3756).",
            upstream_pr=upstream_pr,
        )

    auto_generated_titles_present = bool(payload.get("auto_generated_titles_present", False))
    explicit_field_titles_preserved = bool(payload.get("explicit_field_titles_preserved", True))
    if auto_generated_titles_present or not explicit_field_titles_preserved:
        return _verdict(
            allow=False,
            code="BLOCKED_PYTHON_SDK_GENERATED_SCHEMA_TITLES_LEAKED",
            reason="Tool inputSchema and outputSchema must drop auto-generated Pydantic/SDK titles while keeping explicit Field(title=...) titles (python-sdk#3757).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_PYTHON_SDK_SSE_HEAD_405_DICT_SCHEMA_AND_TITLES_VALID",
        reason="MCP Python SDK HEAD /sse 405, bare dict/typing.Dict structured output parity, and schema title stripping invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/typescript-sdk#3096, #3095, #3093, #3092, & #3091
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_prompt_icons_defs_ref_atomic_cache_and_abort_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce MCP TypeScript SDK prompt icons, recursive $defs object $ref, atomic cache, reset epoch, and abort cleanup."""
    upstream_pr = "modelcontextprotocol/typescript-sdk#3096, #3095, #3093, #3092, #3091"

    prompt_icons_preserved = bool(payload.get("prompt_icons_preserved", True))
    typeless_defs_object_ref_recognized = bool(payload.get("typeless_defs_object_ref_recognized", True))
    partial_tool_cache_on_schema_error = bool(payload.get("partial_tool_cache_on_schema_error", False))
    stale_pre_reset_cache_write_accepted = bool(payload.get("stale_pre_reset_cache_write_accepted", False))
    abort_listener_removed_on_response = bool(payload.get("abort_listener_removed_on_response", True))
    cancelled_sent_after_response_resolved = bool(payload.get("cancelled_sent_after_response_resolved", False))

    if not prompt_icons_preserved:
        return _verdict(
            allow=False,
            code="BLOCKED_TS_SDK_PROMPT_ICONS_DROPPED",
            reason="registerPrompt() and RegisteredPrompt.update() must preserve prompt icons in prompts/list (typescript-sdk#3096).",
            upstream_pr=upstream_pr,
        )
    if not typeless_defs_object_ref_recognized:
        return _verdict(
            allow=False,
            code="BLOCKED_TS_SDK_DEFS_OBJECT_SHAPED_REF_REJECTED",
            reason="isProvablyObjectShapedRoot must treat $ref to a provably object-shaped $defs/definitions entry as an object schema (typescript-sdk#3095).",
            upstream_pr=upstream_pr,
        )
    if partial_tool_cache_on_schema_error:
        return _verdict(
            allow=False,
            code="BLOCKED_TS_SDK_NON_ATOMIC_CACHE_TOOL_METADATA",
            reason="cacheToolMetadata must stage validators/sets in local variables and swap atomically only after all tools succeed (typescript-sdk#3093).",
            upstream_pr=upstream_pr,
        )
    if stale_pre_reset_cache_write_accepted:
        return _verdict(
            allow=False,
            code="BLOCKED_TS_SDK_PRE_RESET_CACHE_WRITE_ACCEPTED",
            reason="ClientResponseCache must reject in-flight cache writes captured before resetForReconnect() (typescript-sdk#3092).",
            upstream_pr=upstream_pr,
        )
    if not abort_listener_removed_on_response or cancelled_sent_after_response_resolved:
        return _verdict(
            allow=False,
            code="BLOCKED_TS_SDK_LEAKED_REQUEST_ABORT_LISTENER",
            reason="Protocol.request() must remove its signal abort listener when the response arrives and never send notifications/cancelled for an answered request (typescript-sdk#3091).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_TS_SDK_ICONS_DEFS_ATOMIC_CACHE_AND_ABORT_VALID",
        reason="MCP TypeScript SDK prompt icons, $defs object $ref, atomic tool metadata cache, reconnect cache epoch, and abort cleanup invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/go-sdk#1449, #1447, & #1446
# ---------------------------------------------------------------------------
def map_slog_level_to_mcp(slog_level: int) -> str:
    chosen = "debug"
    for threshold, name in MCP_LOG_LEVEL_THRESHOLDS:
        if slog_level >= threshold:
            chosen = name
        else:
            break
    return chosen


def evaluate_mcp_go_err_connection_closed_nil_enum_and_slog_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce MCP Go SDK ErrConnectionClosed wrapping, nil titled enum rejection (-32602), and custom slog floor mapping."""
    upstream_pr = "modelcontextprotocol/go-sdk#1449, #1447, #1446"

    notification_wraps_err_connection_closed = bool(payload.get("notification_wraps_err_connection_closed", True))
    interrupted_call_wraps_err_connection_closed = bool(
        payload.get("interrupted_call_wraps_err_connection_closed", True)
    )
    underlying_cause_preserved = bool(payload.get("underlying_cause_preserved", True))
    if not (
        notification_wraps_err_connection_closed
        and interrupted_call_wraps_err_connection_closed
        and underlying_cause_preserved
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_GO_SDK_MISSING_ERR_CONNECTION_CLOSED_WRAP",
            reason="Notifications after closure and calls interrupted by reader termination must wrap ErrConnectionClosed while preserving the underlying cause (go-sdk#1449).",
            upstream_pr=upstream_pr,
        )

    has_null_titled_enum_entry = bool(payload.get("has_null_titled_enum_entry", False))
    panicked_on_null_enum = bool(payload.get("panicked_on_null_enum", False))
    null_enum_error_code = int(payload.get("null_enum_error_code", -32602))
    if has_null_titled_enum_entry and (panicked_on_null_enum or null_enum_error_code != -32602):
        return _verdict(
            allow=False,
            code="BLOCKED_GO_SDK_NULL_TITLED_ENUM_PANIC_OR_WRONG_CODE",
            reason="validateTitledEnumEntry must reject nil enum entries in oneOf/anyOf with -32602 instead of panicking (go-sdk#1447).",
            upstream_pr=upstream_pr,
        )

    slog_level = int(payload.get("slog_level", 1))  # slog.LevelInfo + 1
    mapped_mcp_level = str(payload.get("mapped_mcp_level", map_slog_level_to_mcp(slog_level)))
    expected_mcp_level = map_slog_level_to_mcp(slog_level)
    if mapped_mcp_level != expected_mcp_level:
        return _verdict(
            allow=False,
            code="BLOCKED_GO_SDK_CUSTOM_SLOG_LEVEL_MISLABELED_DEBUG",
            reason="slogLevelToMCP must map custom slog levels to the nearest lower MCP level (e.g. LevelInfo+1 -> 'info') rather than 'debug' (go-sdk#1446).",
            upstream_pr=upstream_pr,
            details={"slog_level": slog_level, "mapped_mcp_level": mapped_mcp_level, "expected": expected_mcp_level},
        )

    return _verdict(
        allow=True,
        code="ALLOW_GO_SDK_CONN_CLOSED_NIL_ENUM_AND_SLOG_VALID",
        reason="MCP Go SDK ErrConnectionClosed wrapping, nil titled enum -32602 guard, and custom slog floor mapping invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/rust-sdk#1393 & modelcontextprotocol/csharp-sdk#1955
# ---------------------------------------------------------------------------
def _effective_origin(raw_url: str) -> tuple[str, str, int] | None:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme.lower(), parsed.hostname.lower(), port


def evaluate_mcp_rust_ipv6_ula_issuer_and_csharp_cancel_task_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce MCP Rust SDK same-origin IPv6 ULA OAuth issuer admission and C# SDK blocking cancellation task."""
    upstream_pr = "modelcontextprotocol/rust-sdk#1393, modelcontextprotocol/csharp-sdk#1955"

    resource_url = str(payload.get("resource_url", "https://[fd00::1]:8443/mcp"))
    issuer_url = str(payload.get("issuer_url", "https://[fd00::1]:8443"))
    issuer_admitted = bool(payload.get("issuer_admitted", True))

    res_origin = _effective_origin(resource_url)
    iss_origin = _effective_origin(issuer_url)
    is_same_origin_ula = False
    if res_origin and iss_origin and res_origin == iss_origin and res_origin[0] == "https":
        try:
            ip = ipaddress.ip_address(iss_origin[1])
            is_same_origin_ula = isinstance(ip, ipaddress.IPv6Address) and (
                ip in ipaddress.IPv6Network("fc00::/7")
            )
        except ValueError:
            is_same_origin_ula = False

    if is_same_origin_ula != issuer_admitted:
        return _verdict(
            allow=False,
            code="BLOCKED_RUST_SDK_IPV6_ULA_SAME_ORIGIN_ISSUER_MISMATCH",
            reason="rmcp OAuth discovery must allow a native IPv6 ULA issuer (fc00::/7) iff scheme, IP, and effective port match the configured resource URL (rust-sdk#1393).",
            upstream_pr=upstream_pr,
            details={
                "resource_url": resource_url,
                "issuer_url": issuer_url,
                "is_same_origin_ula": is_same_origin_ula,
                "issuer_admitted": issuer_admitted,
            },
        )

    task_waits_for_cancellation_token = bool(payload.get("task_waits_for_cancellation_token", True))
    task_completed_before_cancel_call = bool(payload.get("task_completed_before_cancel_call", False))
    if not task_waits_for_cancellation_token or task_completed_before_cancel_call:
        return _verdict(
            allow=False,
            code="BLOCKED_CSHARP_SDK_CANCEL_TEST_PREMATURE_TASK_COMPLETION",
            reason="Task store cancellation verification must use a task that runs until its cancellation token fires (csharp-sdk#1955).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_RUST_IPV6_ULA_ISSUER_AND_CSHARP_CANCEL_VALID",
        reason="MCP Rust SDK same-origin IPv6 ULA OAuth issuer admission and C# SDK cancellation task invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/inspector#2795, #2794, & #2792
# ---------------------------------------------------------------------------
def evaluate_mcp_inspector_429_envelope_static_stamp_and_dcr_owner_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce MCP Inspector CLI/mcpdo 429 retry envelope, static client SEP-2352 stamp, and DCR secret owner verification."""
    upstream_pr = "modelcontextprotocol/inspector#2795, #2794, #2792"

    error_envelope = payload.get("error_envelope") or {
        "code": "rate_limited",
        "status": 429,
        "method": "tools/list",
        "retryAfter": "30",
        "retryAfterMs": 30000,
    }
    if (
        error_envelope.get("code") != "rate_limited"
        or error_envelope.get("status") != 429
        or not error_envelope.get("method")
        or error_envelope.get("retryAfterMs") is None
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_CLI_MISSING_429_RETRY_ENVELOPE",
            reason="CLI and mcpdo HTTP 429 error envelopes must preserve code='rate_limited', status=429, method, retryAfter, and retryAfterMs (inspector#2795).",
            upstream_pr=upstream_pr,
        )

    static_client_issuer_stamp_persisted = bool(payload.get("static_client_issuer_stamp_persisted", True))
    startup_reseed_overwrote_issuer_stamp = bool(payload.get("startup_reseed_overwrote_issuer_stamp", False))
    if not static_client_issuer_stamp_persisted or startup_reseed_overwrote_issuer_stamp:
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_STATIC_CLIENT_SEP2352_STAMP_LOST",
            reason="Static OAuth client SEP-2352 issuer stamp must persist in the preregistered slot across saves and startup restarts (inspector#2794).",
            upstream_pr=upstream_pr,
        )

    state_client_id = str(payload.get("state_client_id", "client-b"))
    secret_stamp_owner_client_id = str(payload.get("secret_stamp_owner_client_id", "client-a"))
    secret_stamp_mac_valid = bool(payload.get("secret_stamp_mac_valid", True))
    returned_secret = payload.get("returned_secret")
    owner_matches = (state_client_id == secret_stamp_owner_client_id) and secret_stamp_mac_valid
    if not owner_matches and returned_secret is not None:
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_CROSS_CLIENT_DCR_SECRET_LEAKED",
            reason="joinServerOAuthState must read a DCR secret stamped for another client_id or with an invalid MAC as absent (inspector#2792).",
            upstream_pr=upstream_pr,
            details={
                "state_client_id": state_client_id,
                "secret_stamp_owner_client_id": secret_stamp_owner_client_id,
            },
        )

    return _verdict(
        allow=True,
        code="ALLOW_INSPECTOR_429_ENVELOPE_STATIC_STAMP_AND_DCR_OWNER_VALID",
        reason="MCP Inspector HTTP 429 retry envelope, static client SEP-2352 issuer stamp, and DCR secret owner verification satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/inspector#2793, #2791, & #2790
# ---------------------------------------------------------------------------
def is_loopback_host(hostname: str) -> bool:
    host = hostname.strip().lower().strip("[]")
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        return False


def evaluate_mcp_inspector_load_connections_bind_warning_and_home_isolation_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce Inspector --load-connections transport guard, non-loopback bind warning, and tmpdir catalog isolation."""
    upstream_pr = "modelcontextprotocol/inspector#2793, #2791, #2790"

    transport = str(payload.get("transport", "streamable-http")).lower()
    load_connections = int(payload.get("load_connections", 4))
    load_run_accepted = bool(payload.get("load_run_accepted", True))
    if (transport == "stdio" and load_connections > 1 and load_run_accepted) or load_connections < 1:
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_LOAD_CONNECTIONS_INVALID_STDIO_OR_COUNT",
            reason="--load-connections > 1 must be rejected on stdio transport and require positive integer session count (inspector#2791).",
            upstream_pr=upstream_pr,
            details={"transport": transport, "load_connections": load_connections},
        )

    bind_hostname = str(payload.get("bind_hostname", "0.0.0.0"))
    emitted_non_loopback_warning = bool(payload.get("emitted_non_loopback_warning", True))
    should_warn = not is_loopback_host(bind_hostname)
    if should_warn != emitted_non_loopback_warning:
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_NON_LOOPBACK_BIND_WARNING_MISMATCH",
            reason="Web server must emit a startup security warning iff bound to a non-loopback host (inspector#2790).",
            upstream_pr=upstream_pr,
            details={"bind_hostname": bind_hostname, "should_warn": should_warn},
        )

    default_catalog_under_tmpdir = bool(payload.get("default_catalog_under_tmpdir", True))
    if not default_catalog_under_tmpdir:
        return _verdict(
            allow=False,
            code="BLOCKED_INSPECTOR_TEST_CATALOG_ESCAPED_TMPDIR",
            reason="CLI test suite must isolate getDefaultMcpConfigPath() inside os.tmpdir() and never touch ~/.mcp-inspector (inspector#2793).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_INSPECTOR_LOAD_CONNECTIONS_BIND_WARNING_AND_ISOLATION_VALID",
        reason="MCP Inspector --load-connections, non-loopback bind warning, and tmpdir catalog isolation invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-15: sierra-research/tau2-bench#680 & #677
# ---------------------------------------------------------------------------
def evaluate_tau2_solo_stop_tool_isolation_and_retail_known_info_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce tau2-bench solo agent 'done' tool list isolation and retail known_info internal user_id scrubbing."""
    upstream_pr = "sierra-research/tau2-bench#680, #677"

    caller_tool_list_mutated = bool(payload.get("caller_tool_list_mutated", False))
    solo_agent_done_tool_count = int(payload.get("solo_agent_done_tool_count", 1))
    normal_agent_has_done_tool = bool(payload.get("normal_agent_has_done_tool", False))
    if caller_tool_list_mutated or solo_agent_done_tool_count != 1 or normal_agent_has_done_tool:
        return _verdict(
            allow=False,
            code="BLOCKED_TAU2_SHARED_TOOL_LIST_SOLO_DONE_LEAK",
            reason="LLMSoloAgent.add_stop_tool() must not mutate shared caller tool lists or leak duplicate/solo 'done' tools (tau2-bench#680).",
            upstream_pr=upstream_pr,
            details={
                "caller_tool_list_mutated": caller_tool_list_mutated,
                "solo_agent_done_tool_count": solo_agent_done_tool_count,
                "normal_agent_has_done_tool": normal_agent_has_done_tool,
            },
        )

    known_info_text = str(payload.get("known_info_text", "You are Mei Kovacs in zip code 80202."))
    if "mei_kovacs_8020" in known_info_text:
        return _verdict(
            allow=False,
            code="BLOCKED_TAU2_RETAIL_KNOWN_INFO_INTERNAL_USER_ID_LEAK",
            reason="Retail user_scenario.known_info must state 'You are Mei Kovacs' rather than leaking internal ID 'mei_kovacs_8020' before find_user_id_by_name_zip (tau2-bench#677).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_TAU2_SOLO_STOP_ISOLATION_AND_RETAIL_KNOWN_INFO_VALID",
        reason="Sierra tau2-bench solo stop-tool list isolation and retail Mei Kovacs known_info invariants satisfied.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#674, #679, #676, & #675
# ---------------------------------------------------------------------------
def evaluate_tau2_malformed_tool_call_agent_error_and_leaderboard_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce tau2-bench scoring of non-object tool args / empty replies as AGENT_ERROR and leaderboard hygiene."""
    upstream_pr = "sierra-research/tau2-bench#674, #679, #676, #675"

    malformed_tool_args_or_empty_reply = bool(payload.get("malformed_tool_args_or_empty_reply", True))
    recorded_error_kind = str(payload.get("recorded_error_kind", "AGENT_ERROR"))
    included_in_score_denominator = bool(payload.get("included_in_score_denominator", True))
    trial_reward = float(payload.get("trial_reward", 0.0))
    if malformed_tool_args_or_empty_reply:
        if (
            recorded_error_kind != "AGENT_ERROR"
            or not included_in_score_denominator
            or trial_reward != 0.0
        ):
            return _verdict(
                allow=False,
                code="BLOCKED_TAU2_MALFORMED_CALL_OR_EMPTY_REPLY_DROPPED_AS_INFRA_ERROR",
                reason="Non-object JSON tool arguments and empty agent replies must be scored as AGENT_ERROR (reward=0.0, kept in 2.0 denominator) rather than INFRASTRUCTURE_ERROR (tau2-bench#674).",
                upstream_pr=upstream_pr,
                details={
                    "recorded_error_kind": recorded_error_kind,
                    "included_in_score_denominator": included_in_score_denominator,
                },
            )

    withdrawn_phonic1_present = bool(payload.get("withdrawn_phonic1_present", False))
    ava_zero_release_dated = bool(payload.get("ava_zero_release_dated", True))
    voice_toggle_labeled_english = bool(payload.get("voice_toggle_labeled_english", True))
    if withdrawn_phonic1_present or not ava_zero_release_dated or not voice_toggle_labeled_english:
        return _verdict(
            allow=False,
            code="BLOCKED_TAU2_LEADERBOARD_SUBMISSION_METADATA_DRIFT",
            reason="tau2-bench leaderboard must remove withdrawn phonic-1 submissions, date Ava Zero release, and label the voice toggle English (tau2-bench#679, #676, #675).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_TAU2_AGENT_ERROR_DENOMINATOR_AND_LEADERBOARD_VALID",
        reason="Sierra tau2-bench malformed tool call / empty reply AGENT_ERROR scoring and leaderboard integrity satisfied.",
        upstream_pr=upstream_pr,
    )


STAGE228_GUARD_EVALUATORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "PR-01": evaluate_visa_tap_rfc9421_hybrid_pq_did_x402_guard,
    "PR-02": evaluate_stripe_toolkit_atomic_skill_sync_and_mcp_cutoff_guard,
    "PR-03": evaluate_acp_atdrp_dispute_host_auth_and_schema_drift_guard,
    "PR-04": evaluate_ucp_identity_linking_cimd_bundled_refs_address_guard,
    "PR-05": evaluate_ap2_sdjwt_json_mode_iso8601_and_iso4217_budget_guard,
    "PR-06": evaluate_a2a_x402_extra_domain_random_nonce_deferred_completion_guard,
    "PR-07": evaluate_agentkit_token_verdict_spend_cap_and_receipt_status_guard,
    "PR-08": evaluate_agentkit_botsrated_preflight_and_selfpaid_yield_guard,
    "PR-09": evaluate_mcp_python_sse_head_405_structured_dict_and_title_strip_guard,
    "PR-10": evaluate_mcp_ts_prompt_icons_defs_ref_atomic_cache_and_abort_guard,
    "PR-11": evaluate_mcp_go_err_connection_closed_nil_enum_and_slog_guard,
    "PR-12": evaluate_mcp_rust_ipv6_ula_issuer_and_csharp_cancel_task_guard,
    "PR-13": evaluate_mcp_inspector_429_envelope_static_stamp_and_dcr_owner_guard,
    "PR-14": evaluate_mcp_inspector_load_connections_bind_warning_and_home_isolation_guard,
    "PR-15": evaluate_tau2_solo_stop_tool_isolation_and_retail_known_info_guard,
    "PR-16": evaluate_tau2_malformed_tool_call_agent_error_and_leaderboard_guard,
}


def evaluate_stage228_scenario(scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    evaluator = STAGE228_GUARD_EVALUATORS.get(scenario_id)
    if evaluator is None:
        raise KeyError(f"Unknown Stage 228 scenario_id: {scenario_id}")
    return evaluator(payload)
