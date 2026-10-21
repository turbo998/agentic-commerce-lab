"""Stage 118 deterministic protocol guards for x402 Stellar `upto` & SVM batch commit,
UCP media variants & OpenAPI header synthesis, Stripe AI plugin/MCP hardening,
and MCP SEP-3415 events + Sierra tau2-bench voice/reward guards.

Covers:
1. x402 Foundation PRs `#3859`, `#3860`, `#3862`, and `#3854`:
   - `#3859`: Stellar `upto` Soroban settlement contract (`0 <= amount <= max_amount`),
     pinned network contract address & WASM hash, facilitator authorization match,
     fee ceiling (`<= 500_000` stroops), timeout window (`15..300` s),
     `signerAuthorizations` bound (`<= 4`), idempotent repeat settle for same amount
     (refusing different amount), and broadcast-pending tx hash retention.
   - `#3860`: Stellar contract account (`C...`, version byte 16) auth-entry signing via
     `authorizeEntry` override while rejecting contract transaction-envelope signing.
   - `#3862`: Go resource server wildcard network scheme lookup (`eip155:*` covering
     `eip155:8453` after exact-key check) with `BeforeVerify` hook execution.
   - `#3854`: SVM server-signed batch-settlement post-commit operation completion
     (`operationStore.complete` runs only after durable `ChannelStore.update` succeeds).
2. UCP PRs `#690` (`#941`/`#935`), `#898`, and `#914`:
   - `#690`: Open `Media` variants (`sources[]`, `preview`, `name`, `duration`),
     `https` media URL enforcement, sandboxed credentialless iframe isolation for
     `external_video` (`allow_top_navigation=False`), and graceful fallback for
     unrecognized media `type`.
   - `#898`: Composed extension schema validation (`$defs/<capability>`) for top-level
     extension fields (`fulfillment` object `description` + `line_item_ids` on update,
     `ap2` mandate format).
   - `#914`: OpenAPI 3.1 `securitySchemes` + content-map HTTP header table synthesis
     (`Authorization`, `X-API-Key`, `Content-Type` on non-GET, `Accept` on 2xx) with
     case-insensitive deduplication and optional-alternative requiredness semantics.
3. Stripe AI PRs `#579`, `#532`, and `#542`:
   - `#579` & `#532`: Portable comma-separated string `allowed-tools` in skill
     frontmatter, current-turn explicit confirmation bound to exact
     `(operation, amount_minor, currency, target)` for money movement/customer writes,
     explicit user consent for `--accept-tos` and `stripe feedback`, and pinned
     `@stripe/cli@1.51.0` / `skills@1.7.0`.
   - `#542`: `@stripe/mcp` stdio proxy immediate JSON-RPC `-32603` error response on
     forwarding failure for requests (with `id` preserved) and silent `None` for
     notifications/responses.
4. MCP PRs `#3415` & `#3384` and Sierra tau2-bench PRs `#631`, `#583`, & `#563`:
   - `#3415`: `io.modelcontextprotocol/events` subscription/delivery validation,
     opaque cursor resume with `truncated` signaling, and Standard Webhooks TTL.
   - `#3384`: RFC 8252 Section 8.3 loopback IP literals (`127.0.0.1` / `[::1]`) for
     native-app CIMD `redirect_uris` (rejecting `localhost`).
   - `#631`, `#583`, & `#563`: `ava_zero_pipecat` SmallWebRTC + RTVI unmodified domain
     policy & bearer auth, recorded trajectory reward component breakdown, and lazy
     `__getattr__` voice dependency isolation for core `tau2` imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


PINNED_STELLAR_TESTNET_UPTO_CONTRACT = (
    "CBTVKCHLSGQ3WSV3NKSU6FZR4FZMC6ENMDMXUS5XQ66HYVUUHYE3TU7U"
)
PINNED_STELLAR_TESTNET_WASM_PREFIX = "cc2d2fef"
MAX_STELLAR_UPTO_FEE_STROOPS = 500_000
MIN_STELLAR_UPTO_TIMEOUT_SECONDS = 15
MAX_STELLAR_UPTO_TIMEOUT_SECONDS = 300
MAX_SIGNER_AUTHORIZATIONS = 4

STRIPE_WRITE_OPERATIONS = frozenset(
    {
        "charges.create",
        "payment_intents.create",
        "payment_intents.confirm",
        "refunds.create",
        "payment_links.create",
        "customers.create",
        "customers.update",
    }
)
PINNED_STRIPE_CLI_VERSION = "1.51.0"
PINNED_SKILLS_CLI_VERSION = "1.7.0"


@dataclass(frozen=True)
class X402StellarUptoAndBatchCheckResult:
    allowed: bool
    reason_code: str
    settled_amount: int
    matched_scheme_key: str
    operation_completed: bool
    tx_status: str


def validate_x402_stellar_upto_and_svm_batch(
    *,
    network: str,
    contract_address: str,
    wasm_hash: str,
    payer_account: str,
    signs_tx_envelope: bool,
    has_authorize_entry_override: bool,
    max_amount: int,
    settle_amount: int,
    current_ledger: int,
    expiration_ledger: int,
    terms_facilitator: str,
    caller_facilitator: str,
    fee_stroops: int,
    max_timeout_seconds: int,
    signer_authorizations_count: int,
    contract_state_archived: bool,
    prior_settled_amount: int | None,
    may_have_broadcast: bool,
    broadcast_tx_hash: str | None,
    registered_schemes: dict[str, dict[str, Any]],
    requested_scheme: str,
    svm_channel_write_succeeded: bool,
    svm_callback_retried: bool,
    complete_called_inside_channel_callback: bool,
) -> X402StellarUptoAndBatchCheckResult:
    """Validate x402 PRs #3859, #3860, #3862, and #3854."""
    if network == "stellar:testnet":
        if contract_address != PINNED_STELLAR_TESTNET_UPTO_CONTRACT:
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_UPTO_UNTRUSTED_CONTRACT_ADDRESS",
                settled_amount=0,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )
        if not wasm_hash.startswith(PINNED_STELLAR_TESTNET_WASM_PREFIX):
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_UPTO_WASM_HASH_MISMATCH",
                settled_amount=0,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )
    elif network == "stellar:pubnet":
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_PUBNET_NOT_DEPLOYED",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    # #3860: Contract account ('C...') vs classic account ('G...') signing
    if payer_account.startswith("C"):
        if signs_tx_envelope:
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_CONTRACT_ACCOUNT_CANNOT_SIGN_ENVELOPE",
                settled_amount=0,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )
        if not has_authorize_entry_override:
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_CONTRACT_ACCOUNT_MISSING_AUTHORIZE_ENTRY_OVERRIDE",
                settled_amount=0,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )
    elif not payer_account.startswith("G"):
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_INVALID_ACCOUNT_PREFIX",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    # #3859: Facilitator & contract guardrails
    if contract_state_archived:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_ARCHIVED_CONTRACT_STATE",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    if fee_stroops > MAX_STELLAR_UPTO_FEE_STROOPS:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_FEE_CEILING_EXCEEDED",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    if not (
        MIN_STELLAR_UPTO_TIMEOUT_SECONDS
        <= max_timeout_seconds
        <= MAX_STELLAR_UPTO_TIMEOUT_SECONDS
    ):
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_TIMEOUT_OUT_OF_RANGE",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    if signer_authorizations_count > MAX_SIGNER_AUTHORIZATIONS:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_TOO_MANY_SIGNER_AUTHORIZATIONS",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    # Idempotent repeat settle check (#3859): repeat for same payment returns first result
    # even after expiry, but different amount is refused.
    if prior_settled_amount is not None:
        if settle_amount != prior_settled_amount:
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_UPTO_REPEAT_DIFFERENT_AMOUNT_REFUSED",
                settled_amount=prior_settled_amount,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )
    else:
        if current_ledger > expiration_ledger:
            return X402StellarUptoAndBatchCheckResult(
                allowed=False,
                reason_code="X402_STELLAR_UPTO_AUTH_EXPIRED",
                settled_amount=0,
                matched_scheme_key="",
                operation_completed=False,
                tx_status="rejected",
            )

    if not terms_facilitator or terms_facilitator != caller_facilitator:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_FACILITATOR_MISMATCH",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    if settle_amount < 0 or settle_amount > max_amount:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_AMOUNT_EXCEEDS_MAX",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    if may_have_broadcast and not broadcast_tx_hash:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_STELLAR_UPTO_BROADCAST_MISSING_TX_HASH",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="failed_without_hash",
        )

    # #3862: Server scheme lookup through exact match then wildcard registration
    matched_key = ""
    if network in registered_schemes and requested_scheme in registered_schemes[network]:
        matched_key = network
    else:
        family = network.split(":", 1)[0] + ":*" if ":" in network else "*"
        if family in registered_schemes and requested_scheme in registered_schemes[family]:
            matched_key = family

    if not matched_key:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_SCHEME_NOT_REGISTERED_FOR_NETWORK",
            settled_amount=0,
            matched_scheme_key="",
            operation_completed=False,
            tx_status="rejected",
        )

    scheme_meta = registered_schemes[matched_key][requested_scheme]
    if not scheme_meta.get("before_verify_hook_ran", True):
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_WILDCARD_SCHEME_BEFORE_VERIFY_HOOK_SKIPPED",
            settled_amount=0,
            matched_scheme_key=matched_key,
            operation_completed=False,
            tx_status="rejected",
        )

    # #3854: SVM batch operation completion only after durable ChannelStore.update commits
    if complete_called_inside_channel_callback and (
        svm_callback_retried or not svm_channel_write_succeeded
    ):
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_SVM_PREMATURE_OPERATION_COMPLETE_INSIDE_CHANNEL_CALLBACK",
            settled_amount=0,
            matched_scheme_key=matched_key,
            operation_completed=False,
            tx_status="rejected",
        )

    if not svm_channel_write_succeeded:
        return X402StellarUptoAndBatchCheckResult(
            allowed=False,
            reason_code="X402_SVM_CHANNEL_WRITE_FAILED_OPERATION_NOT_COMPLETED",
            settled_amount=0,
            matched_scheme_key=matched_key,
            operation_completed=False,
            tx_status="rejected",
        )

    tx_status = "pending" if may_have_broadcast else "settled"
    return X402StellarUptoAndBatchCheckResult(
        allowed=True,
        reason_code="X402_STELLAR_UPTO_AND_SVM_BATCH_VALID",
        settled_amount=settle_amount,
        matched_scheme_key=matched_key,
        operation_completed=True,
        tx_status=tx_status,
    )


@dataclass(frozen=True)
class UcpMediaExtensionAndHeadersCheckResult:
    allowed: bool
    reason_code: str
    synthesized_headers: tuple[tuple[str, bool], ...]
    featured_media_url: str


def validate_ucp_media_extension_and_headers(
    *,
    media_items: list[dict[str, Any]],
    require_https_media: bool,
    checkout_example: dict[str, Any],
    is_update_operation: bool,
    http_method: str,
    parameter_headers: list[str],
    security_alternatives: list[dict[str, str]],
    has_request_body_content: bool,
    has_2xx_response_content: bool,
) -> UcpMediaExtensionAndHeadersCheckResult:
    """Validate UCP PRs #690 (#941/#935), #898, and #914."""
    if not media_items:
        return UcpMediaExtensionAndHeadersCheckResult(
            allowed=False,
            reason_code="UCP_MEDIA_EMPTY",
            synthesized_headers=(),
            featured_media_url="",
        )

    featured_url = ""
    for item in media_items:
        m_type = item.get("type")
        m_url = item.get("url")
        if not isinstance(m_type, str) or not m_type or not isinstance(m_url, str) or not m_url:
            return UcpMediaExtensionAndHeadersCheckResult(
                allowed=False,
                reason_code="UCP_MEDIA_MISSING_REQUIRED_TYPE_OR_URL",
                synthesized_headers=(),
                featured_media_url="",
            )
        parsed = urlparse(m_url)
        if require_https_media and parsed.scheme != "https":
            return UcpMediaExtensionAndHeadersCheckResult(
                allowed=False,
                reason_code="UCP_MEDIA_NON_HTTPS_URL_REFUSED",
                synthesized_headers=(),
                featured_media_url="",
            )
        if m_type == "external_video":
            if item.get("sources"):
                return UcpMediaExtensionAndHeadersCheckResult(
                    allowed=False,
                    reason_code="UCP_EXTERNAL_VIDEO_MUST_NOT_HAVE_PLAYABLE_SOURCES",
                    synthesized_headers=(),
                    featured_media_url="",
                )
            if not item.get("sandbox_isolated", False) or item.get(
                "allow_top_navigation", False
            ):
                return UcpMediaExtensionAndHeadersCheckResult(
                    allowed=False,
                    reason_code="UCP_EXTERNAL_VIDEO_IFRAME_NOT_ISOLATED",
                    synthesized_headers=(),
                    featured_media_url="",
                )
        elif m_type in {"image", "video", "model_3d"}:
            for src in item.get("sources", []):
                src_url = src.get("url", "")
                if require_https_media and urlparse(src_url).scheme != "https":
                    return UcpMediaExtensionAndHeadersCheckResult(
                        allowed=False,
                        reason_code="UCP_MEDIA_SOURCE_NON_HTTPS_URL_REFUSED",
                        synthesized_headers=(),
                        featured_media_url="",
                    )
                if not src.get("mime_type"):
                    return UcpMediaExtensionAndHeadersCheckResult(
                        allowed=False,
                        reason_code="UCP_MEDIA_SOURCE_MISSING_MIME_TYPE",
                        synthesized_headers=(),
                        featured_media_url="",
                    )
        else:
            # Unknown media type (#690): must not reject product; fallback to preview + name
            if item.get("rejected_for_unknown_type", False):
                return UcpMediaExtensionAndHeadersCheckResult(
                    allowed=False,
                    reason_code="UCP_MEDIA_UNKNOWN_TYPE_MUST_NOT_BE_REJECTED",
                    synthesized_headers=(),
                    featured_media_url="",
                )
        if not featured_url:
            featured_url = m_url

    # #898: Validate top-level extension fields in checkout examples
    fulfillment = checkout_example.get("fulfillment")
    if isinstance(fulfillment, dict):
        for opt in fulfillment.get("options", []):
            desc = opt.get("description")
            if desc is not None and not isinstance(desc, dict):
                return UcpMediaExtensionAndHeadersCheckResult(
                    allowed=False,
                    reason_code="UCP_FULFILLMENT_OPTION_DESCRIPTION_MUST_BE_OBJECT",
                    synthesized_headers=(),
                    featured_media_url=featured_url,
                )
        if is_update_operation:
            for method in fulfillment.get("methods", []):
                line_item_ids = method.get("line_item_ids")
                if not isinstance(line_item_ids, list) or not line_item_ids:
                    return UcpMediaExtensionAndHeadersCheckResult(
                        allowed=False,
                        reason_code="UCP_FULFILLMENT_UPDATE_MISSING_LINE_ITEM_IDS",
                        synthesized_headers=(),
                        featured_media_url=featured_url,
                    )

    ap2_ext = checkout_example.get("ap2")
    if isinstance(ap2_ext, dict):
        for field_name in ("merchant_authorization", "checkout_mandate"):
            val = ap2_ext.get(field_name)
            if val is not None and (not isinstance(val, str) or val.count(".") < 2):
                return UcpMediaExtensionAndHeadersCheckResult(
                    allowed=False,
                    reason_code=f"UCP_AP2_EXTENSION_INVALID_FORMAT:{field_name}",
                    synthesized_headers=(),
                    featured_media_url=featured_url,
                )

    # #914: Synthesize HTTP headers from securitySchemes and content maps
    existing_lower = {h.lower() for h in parameter_headers}
    if len(existing_lower) != len(parameter_headers):
        return UcpMediaExtensionAndHeadersCheckResult(
            allowed=False,
            reason_code="UCP_DUPLICATE_PARAMETER_HEADER_ROW",
            synthesized_headers=(),
            featured_media_url=featured_url,
        )

    rows: list[tuple[str, bool]] = [(h, True) for h in parameter_headers]
    header_Touch_counts: dict[str, int] = {}
    header_canonical: dict[str, str] = {}

    for alt in security_alternatives:
        alt_headers: set[str] = set()
        for scheme_type, header_name in alt.items():
            if scheme_type in {"http", "oauth2", "openIdConnect"}:
                h_name = "Authorization"
            elif scheme_type == "apiKey_header" and header_name:
                h_name = header_name
            else:
                # mutualTLS, cookie, query, or empty optional '{}' produce no row
                continue
            alt_headers.add(h_name)
        for h_name in alt_headers:
            low = h_name.lower()
            header_canonical.setdefault(low, h_name)
            header_Touch_counts[low] = header_Touch_counts.get(low, 0) + 1

    total_alts = len(security_alternatives)
    for low, h_name in header_canonical.items():
        if low in existing_lower:
            continue
        is_required = total_alts > 0 and header_Touch_counts[low] == total_alts
        rows.append((h_name, is_required))
        existing_lower.add(low)

    if http_method.upper() != "GET" and has_request_body_content:
        if "content-type" not in existing_lower:
            rows.append(("Content-Type", True))
            existing_lower.add("content-type")

    if has_2xx_response_content:
        if "accept" not in existing_lower:
            rows.append(("Accept", False))
            existing_lower.add("accept")

    return UcpMediaExtensionAndHeadersCheckResult(
        allowed=True,
        reason_code="UCP_MEDIA_EXTENSION_AND_HEADERS_VALID",
        synthesized_headers=tuple(rows),
        featured_media_url=featured_url,
    )


@dataclass(frozen=True)
class StripePluginAndMcpForwardingCheckResult:
    allowed: bool
    reason_code: str
    forwarding_error_response: dict[str, Any] | None


def validate_stripe_plugin_and_mcp_forwarding(
    *,
    skill_allowed_tools: Any,
    operation: str,
    amount_minor: int,
    currency: str,
    target_id: str,
    current_turn_confirmation: dict[str, Any] | None,
    requires_tos_acceptance: bool,
    user_accepted_tos: bool,
    passed_accept_tos_flag: bool,
    auto_submitted_feedback: bool,
    user_approved_feedback: bool,
    stripe_cli_version: str,
    skills_cli_version: str,
    mcp_forwarding_failed: bool,
    mcp_failure_message: str,
    mcp_incoming_jsonrpc: dict[str, Any] | None,
) -> StripePluginAndMcpForwardingCheckResult:
    """Validate Stripe AI PRs #579, #532, and #542."""
    # #532 Rule 1: allowed-tools in skill frontmatter must be comma-separated str, not list
    if not isinstance(skill_allowed_tools, str) or not skill_allowed_tools.strip():
        return StripePluginAndMcpForwardingCheckResult(
            allowed=False,
            reason_code="STRIPE_PLUGIN_ALLOWED_TOOLS_MUST_BE_STRING",
            forwarding_error_response=None,
        )

    # #532 Rule 4: Pinned CLI versions
    if stripe_cli_version != PINNED_STRIPE_CLI_VERSION:
        return StripePluginAndMcpForwardingCheckResult(
            allowed=False,
            reason_code="STRIPE_CLI_VERSION_PIN_MISMATCH",
            forwarding_error_response=None,
        )
    if skills_cli_version != PINNED_SKILLS_CLI_VERSION:
        return StripePluginAndMcpForwardingCheckResult(
            allowed=False,
            reason_code="STRIPE_SKILLS_CLI_VERSION_PIN_MISMATCH",
            forwarding_error_response=None,
        )

    # #532 Rule 2: Money movement / customer writes require current-turn explicit confirmation
    if operation in STRIPE_WRITE_OPERATIONS:
        if not isinstance(current_turn_confirmation, dict):
            return StripePluginAndMcpForwardingCheckResult(
                allowed=False,
                reason_code="STRIPE_WRITE_MISSING_CURRENT_TURN_CONFIRMATION",
                forwarding_error_response=None,
            )
        if not current_turn_confirmation.get("is_current_turn", False):
            return StripePluginAndMcpForwardingCheckResult(
                allowed=False,
                reason_code="STRIPE_WRITE_STALE_PRIOR_TURN_CONFIRMATION",
                forwarding_error_response=None,
            )
        if (
            current_turn_confirmation.get("operation") != operation
            or current_turn_confirmation.get("amount_minor") != amount_minor
            or current_turn_confirmation.get("currency") != currency
            or current_turn_confirmation.get("target_id") != target_id
        ):
            return StripePluginAndMcpForwardingCheckResult(
                allowed=False,
                reason_code="STRIPE_WRITE_CONFIRMATION_PARAMETER_MISMATCH",
                forwarding_error_response=None,
            )

    # #532 Rule 3: --accept-tos requires explicit user consent
    if requires_tos_acceptance and passed_accept_tos_flag and not user_accepted_tos:
        return StripePluginAndMcpForwardingCheckResult(
            allowed=False,
            reason_code="STRIPE_PROJECTS_UNCONSENTED_ACCEPT_TOS",
            forwarding_error_response=None,
        )

    # #532 Rule 5: stripe feedback requires user approval
    if auto_submitted_feedback and not user_approved_feedback:
        return StripePluginAndMcpForwardingCheckResult(
            allowed=False,
            reason_code="STRIPE_APPS_UNAPPROVED_AUTO_FEEDBACK",
            forwarding_error_response=None,
        )

    # #542: @stripe/mcp forwarding failure response
    forwarding_resp: dict[str, Any] | None = None
    if mcp_forwarding_failed and mcp_incoming_jsonrpc is not None:
        is_request = (
            "method" in mcp_incoming_jsonrpc and "id" in mcp_incoming_jsonrpc
        )
        if is_request:
            forwarding_resp = {
                "jsonrpc": "2.0",
                "id": mcp_incoming_jsonrpc["id"],
                "error": {
                    "code": -32603,
                    "message": (
                        "Error forwarding request to the Stripe MCP server: "
                        f"{mcp_failure_message}"
                    ),
                },
            }

    return StripePluginAndMcpForwardingCheckResult(
        allowed=True,
        reason_code="STRIPE_PLUGIN_AND_MCP_FORWARDING_VALID",
        forwarding_error_response=forwarding_resp,
    )


@dataclass(frozen=True)
class McpEventsAndTau2VoiceCheckResult:
    allowed: bool
    reason_code: str
    effective_reward: float
    core_import_isolated: bool


def validate_mcp_events_and_tau2_voice(
    *,
    cimd_redirect_uris: list[str],
    event_delivery_mode: str,
    supported_delivery_modes: set[str],
    webhook_signature_verified: bool,
    webhook_ttl_seconds: int,
    cursor_truncated: bool,
    client_acknowledged_truncation: bool,
    ava_zero_domain_policy_modified: bool,
    ava_zero_has_bearer_token: bool,
    ava_zero_has_rtvi_channel: bool,
    db_check_passed: bool,
    communication_check_passed: bool,
    diagnostic_check_failed: bool,
    diagnostic_counted_in_reward: bool,
    core_import_loaded_voice_deps_eagerly: bool,
) -> McpEventsAndTau2VoiceCheckResult:
    """Validate MCP PRs #3415 & #3384 and Sierra tau2-bench PRs #631, #583, & #563."""
    # #3384: RFC 8252 Section 8.3 loopback IP literals over localhost in native CIMD redirect_uris
    for uri in cimd_redirect_uris:
        parsed = urlparse(uri)
        if parsed.scheme == "http" and parsed.hostname == "localhost":
            return McpEventsAndTau2VoiceCheckResult(
                allowed=False,
                reason_code="MCP_CIMD_LOCALHOST_REDIRECT_URI_FORBIDDEN_USE_LOOPBACK_IP",
                effective_reward=0.0,
                core_import_isolated=False,
            )

    # #3415: SEP-3415 Events Extension
    if event_delivery_mode not in {"poll", "push", "webhook"} or (
        event_delivery_mode not in supported_delivery_modes
    ):
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="MCP_EVENTS_UNSUPPORTED_DELIVERY_MODE",
            effective_reward=0.0,
            core_import_isolated=False,
        )

    if event_delivery_mode == "webhook":
        if not webhook_signature_verified or webhook_ttl_seconds <= 0:
            return McpEventsAndTau2VoiceCheckResult(
                allowed=False,
                reason_code="MCP_EVENTS_WEBHOOK_SIGNATURE_OR_TTL_INVALID",
                effective_reward=0.0,
                core_import_isolated=False,
            )

    if cursor_truncated and not client_acknowledged_truncation:
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="MCP_EVENTS_TRUNCATED_CURSOR_UNACKNOWLEDGED",
            effective_reward=0.0,
            core_import_isolated=False,
        )

    # tau2 #631: ava_zero_pipecat SmallWebRTC + RTVI adaptor invariants
    if ava_zero_domain_policy_modified:
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="TAU2_AVA_ZERO_DOMAIN_POLICY_MODIFIED",
            effective_reward=0.0,
            core_import_isolated=False,
        )
    if not ava_zero_has_bearer_token or not ava_zero_has_rtvi_channel:
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="TAU2_AVA_ZERO_MISSING_BEARER_OR_RTVI_CHANNEL",
            effective_reward=0.0,
            core_import_isolated=False,
        )

    # tau2 #583: diagnostic checks must not count toward reward
    if diagnostic_check_failed and diagnostic_counted_in_reward:
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="TAU2_DIAGNOSTIC_CHECK_POLLUTED_REWARD",
            effective_reward=0.0,
            core_import_isolated=False,
        )

    # tau2 #563: core imports must load voice providers lazily via __getattr__
    if core_import_loaded_voice_deps_eagerly:
        return McpEventsAndTau2VoiceCheckResult(
            allowed=False,
            reason_code="TAU2_EAGER_VOICE_DEPENDENCY_IMPORT_ON_CORE_LOAD",
            effective_reward=0.0,
            core_import_isolated=False,
        )

    effective_reward = 1.0 if (db_check_passed and communication_check_passed) else 0.0
    return McpEventsAndTau2VoiceCheckResult(
        allowed=True,
        reason_code="MCP_EVENTS_AND_TAU2_VOICE_VALID",
        effective_reward=effective_reward,
        core_import_isolated=True,
    )
