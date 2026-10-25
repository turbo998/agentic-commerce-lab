"""Stage 262: Deterministic guards for Stripe CLI/SDK, AgentKit Financial/SBOR/Groundtruth, MCP ExtAuth/Cache/Transport, and A2A Compat (`PR-01..PR-16`).

Covers 24 primary-source pull requests audited on 2026-10-25:
- PR-01: stripe/stripe-cli#2151 — Daemon per-instance 32-byte token constant-time auth, API-key mode parity & fixture api_base allowlist
- PR-02: stripe/stripe-cli#2152 & #2150 — OpenAPI-driven multipart/form-data binary upload & SIGINT/SIGTERM peer-plugin reaper
- PR-03: stripe/stripe-python#1940 & #1944 + stripe/stripe-node#2905 & #2904 — ASCII-whitespace webhook secret rejection, serializable StripeError.args, fetch lastResponse.statusCode & @stripe/workload-identity
- PR-04: coinbase/agentkit#1514 — AgendaGuardActionProvider pre-sign EVM evidence review boundary (is_safe=False invariant)
- PR-05: coinbase/agentkit#1519 — SborActionProvider read-only benchmark lending rate, 48h freshness & >50 bps stopAndAskHuman guard
- PR-06: coinbase/agentkit#1518 — GroundtruthActionProvider memecoin creator/coin record & statistical known_bad guard
- PR-07: modelcontextprotocol/go-sdk#1451 & #1356 — RFC 8707 resource parameter in ClientCredentialsHandler token request & RFC 9110 empty WWW-Authenticate list elements
- PR-08: modelcontextprotocol/rust-sdk#1308 & #1303 — 2026-07-28 default missing cache hints (ttlMs:0, cacheScope:private) & -32602 INVALID_PARAMS for ungated spec methods
- PR-09: modelcontextprotocol/rust-sdk#1305 & #1304 — Structured ProtectedResourceMetadataInvalidReason & non-blocking FIFO stdio_pipes transport
- PR-10: modelcontextprotocol/typescript-sdk#2995 & #3007 — Exploded slash-separated URI path matching & quiet v2 default Ajv unknown-format logger
- PR-11: modelcontextprotocol/kotlin-sdk#1019, #999 & #998 — Atomic onInitialized late-registration execution, method-keyed rawResult deserialization & CancellationException suppression
- PR-12: modelcontextprotocol/inspector#2704, #2703 & #2707 — CLI option-preceding stdio target preservation, client-specific connect-timeout remedies & ObjectArrayField schema rows
- PR-13: a2aproject/a2a-python#1307, #1304 & #1301 — AgentCard non-object/compat ParseError normalization, major_minor 1.0.0 interface negotiation & quiet -32700 JSON-RPC dispatcher
- PR-14: a2aproject/a2a-python#1306, #1300 & #1298 — v0.3 SendMessageConfiguration history_length=0 unlimited, non-google.rpc.Status REST error fallback & streaming follow-up message_to_save preservation
- PR-15: a2aproject/a2a-java#1215 & #1213 + a2aproject/a2a-js#703 — Java v0.3 explicit JSON null Struct round-trip, centralized Assert.isNullOrEmpty validation & JS Kysely push notification migrations
- PR-16: End-to-end synthesis across Stripe CLI/SDK, AgentKit AgendaGuard/SBOR/Groundtruth, MCP ExtAuth/Cache/Transport, and A2A Multi-Version Resilience
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hmac
import math
import re
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result of a Stage 262 architectural guard evaluation."""

    scenario_id: str
    passed: bool
    action: str
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


ALLOWLISTED_STRIPE_FIXTURE_HOSTS: frozenset[str] = frozenset(
    {
        "api.stripe.com",
        "files.stripe.com",
        "meter-events.stripe.com",
        "qa-api.stripe.com",
    }
)

STRIPE_API_VERSION_PATH_RE = re.compile(r"^/v\d+$")

AGENDA_LOCAL_RISK_DENYLIST: frozenset[str] = frozenset(
    {
        "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",
        "0x722122df12d45b1410ac727761ba7975772da855",
        "0x8589427373d6d84e98730d7795d8f6f8731fda16",
        "0x0836222f2b2b24a3f36f98668ed8f0b38d1a872f",
        "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
        "0x098b716b8aaf21512996dc57eb0615e2383e2f96",
        "0xa0e1c087346358e59675a523171b085c6b308c01",
        "0x53b6936513e738f44fb50d2b9476730c0ab3bfc1",
        "0x61f2382e87903264426543b591b6e4b85c13e488",
        "0x2f389904178ea3c113502280ce42964e7c3a0df4",
    }
)

AGENDA_UNLIMITED_ALLOWANCE_PATTERNS = (
    re.compile(r"ffffffffffffffffffffffffffffffff", re.IGNORECASE),
    re.compile(r"115792089237316195423570985008687907853269984665640564039457584007913129639935"),
)

AGENDA_ADVERSARIAL_INTENT_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules|limits)", re.IGNORECASE),
    re.compile(r"bypass\s+(compliance|limits|checks|security|guardrails)", re.IGNORECASE),
    re.compile(r"override\s+(policy|system|guard|limit)", re.IGNORECASE),
    re.compile(r"drain\s+(all\s+funds|the\s+wallet|treasury|balance)", re.IGNORECASE),
    re.compile(r"emergency\s+(sweep|drain|withdrawal\s+all)", re.IGNORECASE),
    re.compile(r"send\s+all\s+(funds|balance|usdc|eth)", re.IGNORECASE),
)

SBOR_BENCHMARKS: frozenset[str] = frozenset(
    {"SBOR-USD", "SBOR-BTC", "SBOR-STX", "BTC-COLLATERAL-USDC"}
)

MCP_UNGATED_SPEC_METHODS: frozenset[str] = frozenset(
    {
        "tools/call",
        "tools/list",
        "prompts/get",
        "prompts/list",
        "resources/list",
        "resources/templates/list",
        "resources/read",
        "completion/complete",
        "logging/setLevel",
    }
)

MCP_GATED_OR_DISCOVERY_METHODS: frozenset[str] = frozenset(
    {
        "initialize",
        "server/discover",
        "ping",
        "resources/subscribe",
        "resources/unsubscribe",
        "tasks/get",
        "tasks/result",
        "tasks/list",
        "tasks/cancel",
    }
)


def _is_livemode_stripe_key(api_key: str) -> bool:
    return api_key.startswith(("sk_live_", "rk_live_", "mk_live_"))


def _validate_stripe_fixture_api_base(raw_url: str) -> bool:
    if not raw_url or "#" in raw_url or raw_url.endswith("?"):
        return False
    parsed = urlparse(raw_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.netloc != parsed.hostname:
        return False
    if parsed.query or parsed.fragment:
        return False
    if parsed.path not in ("", "/") and not STRIPE_API_VERSION_PATH_RE.match(parsed.path):
        return False
    host = parsed.hostname.lower()
    if host in ALLOWLISTED_STRIPE_FIXTURE_HOSTS or host.endswith(".corp.stripe.com"):
        return True
    return False


# ---------------------------------------------------------------------------
# PR-01: stripe/stripe-cli#2151
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_daemon_auth_and_fixture_url_guard(
    *,
    daemon_token: str,
    header_values: list[str],
    auth_checked_before_telemetry: bool,
    stderr_contains_token: bool,
    api_key: str,
    requested_livemode: bool,
    fixture_api_base: str,
) -> GuardEvaluation:
    """Validate Stripe CLI daemon per-instance token auth, key-mode parity, and fixture api_base allowlist."""
    if len(daemon_token) != 64 or any(c not in "0123456789abcdef" for c in daemon_token.lower()):
        return GuardEvaluation(
            scenario_id="stripe_cli_daemon_auth_fixture_url",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_DAEMON_WEAK_OR_MISSING_TOKEN",
            details={"daemon_token_len": len(daemon_token)},
        )
    if len(header_values) != 1 or not header_values[0] or not hmac.compare_digest(
        header_values[0].encode("utf-8"), daemon_token.encode("utf-8")
    ):
        return GuardEvaluation(
            scenario_id="stripe_cli_daemon_auth_fixture_url",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_DAEMON_UNAUTHENTICATED_RPC",
            details={"header_count": len(header_values)},
        )
    if not auth_checked_before_telemetry or stderr_contains_token:
        return GuardEvaluation(
            scenario_id="stripe_cli_daemon_auth_fixture_url",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_DAEMON_TELEMETRY_OR_STDERR_TOKEN_LEAK",
            details={
                "auth_checked_before_telemetry": auth_checked_before_telemetry,
                "stderr_contains_token": stderr_contains_token,
            },
        )
    if _is_livemode_stripe_key(api_key) != requested_livemode:
        return GuardEvaluation(
            scenario_id="stripe_cli_daemon_auth_fixture_url",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_API_KEY_MODE_MISMATCH",
            details={"requested_livemode": requested_livemode},
        )
    if fixture_api_base and not _validate_stripe_fixture_api_base(fixture_api_base):
        return GuardEvaluation(
            scenario_id="stripe_cli_daemon_auth_fixture_url",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_FIXTURE_UNTRUSTED_API_BASE_URL",
            details={"fixture_api_base": fixture_api_base},
        )
    return GuardEvaluation(
        scenario_id="stripe_cli_daemon_auth_fixture_url",
        passed=True,
        action="Act automatically",
        reason_code="STRIPE_DAEMON_AUTH_AND_FIXTURE_URL_VERIFIED",
        details={"fixture_api_base": fixture_api_base or "default"},
    )


# ---------------------------------------------------------------------------
# PR-02: stripe/stripe-cli#2152 & #2150
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_multipart_and_plugin_reaper_guard(
    *,
    request_media_type: str,
    param_format: str,
    raw_flag_value: str,
    effective_param_value: str,
    dispatched_method: str,
    merged_additional_params: bool,
    dry_run_is_v2: bool,
    help_placeholder: str,
    sigint_sigterm_reaper_installed: bool,
    reaps_peer_plugins_via_cleanup_all_clients: bool,
) -> GuardEvaluation:
    """Validate Stripe CLI OpenAPI multipart/form-data binary flag handling and peer-plugin signal reaper."""
    if request_media_type == "multipart/form-data":
        if dispatched_method != "MakeMultiPartRequestWithAdditionalParams" or not merged_additional_params:
            return GuardEvaluation(
                scenario_id="stripe_cli_multipart_and_plugin_reaper",
                passed=False,
                action="Send to a human",
                reason_code="STRIPE_CLI_MULTIPART_NOT_DISPATCHED_OR_MISSING_PARAMS",
                details={"dispatched_method": dispatched_method},
            )
        if param_format == "binary":
            expected_val = raw_flag_value if raw_flag_value.startswith("@") else f"@{raw_flag_value}"
            if effective_param_value != expected_val or help_placeholder != "<file-path>":
                return GuardEvaluation(
                    scenario_id="stripe_cli_multipart_and_plugin_reaper",
                    passed=False,
                    action="Send to a human",
                    reason_code="STRIPE_CLI_BINARY_FLAG_PATH_SENT_AS_PLAIN_STRING",
                    details={
                        "effective_param_value": effective_param_value,
                        "help_placeholder": help_placeholder,
                    },
                )
        if dry_run_is_v2:
            return GuardEvaluation(
                scenario_id="stripe_cli_multipart_and_plugin_reaper",
                passed=False,
                action="Send to a human",
                reason_code="STRIPE_CLI_MULTIPART_MISCLASSIFIED_AS_V2_JSON",
                details={"dry_run_is_v2": dry_run_is_v2},
            )
    if not sigint_sigterm_reaper_installed or not reaps_peer_plugins_via_cleanup_all_clients:
        return GuardEvaluation(
            scenario_id="stripe_cli_multipart_and_plugin_reaper",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_CLI_ORPHANED_PEER_PLUGIN_ON_SIGNAL",
            details={
                "sigint_sigterm_reaper_installed": sigint_sigterm_reaper_installed,
                "reaps_peer_plugins_via_cleanup_all_clients": reaps_peer_plugins_via_cleanup_all_clients,
            },
        )
    return GuardEvaluation(
        scenario_id="stripe_cli_multipart_and_plugin_reaper",
        passed=True,
        action="Act automatically",
        reason_code="STRIPE_CLI_MULTIPART_AND_PLUGIN_REAPER_VERIFIED",
        details={"effective_param_value": effective_param_value},
    )


# ---------------------------------------------------------------------------
# PR-03: stripe/stripe-python#1940 & #1944 + stripe/stripe-node#2905 & #2904
# ---------------------------------------------------------------------------
def evaluate_stripe_sdk_webhook_error_fetch_and_wif_guard(
    *,
    webhook_secret: str | None,
    rejected_before_hmac: bool,
    stripe_error_args_tuple_len: int,
    pickle_celery_roundtrip_ok: bool,
    fetch_raw_response_has_status_code: bool,
    fetch_status_code_value: int | None,
    workload_identity_package_name: str,
    workload_identity_tag_prefix: str,
) -> GuardEvaluation:
    """Validate Stripe Python blank-ASCII webhook secret rejection, serializable StripeError.args, and Stripe Node fetch statusCode & workload-identity package."""
    is_blank_ascii = webhook_secret is None or webhook_secret.strip(" \t\r\n\f\v") == ""
    if is_blank_ascii and not rejected_before_hmac:
        return GuardEvaluation(
            scenario_id="stripe_sdk_webhook_error_fetch_wif",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_WEBHOOK_ASCII_WHITESPACE_SECRET_ACCEPTED_AS_HMAC_KEY",
            details={"webhook_secret_repr": repr(webhook_secret)},
        )
    if not is_blank_ascii and rejected_before_hmac:
        return GuardEvaluation(
            scenario_id="stripe_sdk_webhook_error_fetch_wif",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_WEBHOOK_VALID_NONBLANK_SECRET_REJECTED",
            details={"webhook_secret_len": len(webhook_secret or "")},
        )
    if stripe_error_args_tuple_len < 6 or not pickle_celery_roundtrip_ok:
        return GuardEvaluation(
            scenario_id="stripe_sdk_webhook_error_fetch_wif",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_ERROR_ARGS_NOT_SERIALIZABLE",
            details={
                "stripe_error_args_tuple_len": stripe_error_args_tuple_len,
                "pickle_celery_roundtrip_ok": pickle_celery_roundtrip_ok,
            },
        )
    if not fetch_raw_response_has_status_code or fetch_status_code_value is None:
        return GuardEvaluation(
            scenario_id="stripe_sdk_webhook_error_fetch_wif",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_NODE_FETCH_LAST_RESPONSE_STATUS_CODE_UNDEFINED",
            details={"fetch_status_code_value": fetch_status_code_value},
        )
    if (
        workload_identity_package_name != "@stripe/workload-identity"
        or workload_identity_tag_prefix != "wif-v"
    ):
        return GuardEvaluation(
            scenario_id="stripe_sdk_webhook_error_fetch_wif",
            passed=False,
            action="Send to a human",
            reason_code="STRIPE_NODE_LEGACY_AWS_WORKLOAD_IDENTITY_NAME",
            details={
                "workload_identity_package_name": workload_identity_package_name,
                "workload_identity_tag_prefix": workload_identity_tag_prefix,
            },
        )
    return GuardEvaluation(
        scenario_id="stripe_sdk_webhook_error_fetch_wif",
        passed=True,
        action="Act automatically",
        reason_code="STRIPE_SDK_WEBHOOK_ERROR_FETCH_AND_WIF_VERIFIED",
        details={
            "is_blank_ascii": is_blank_ascii,
            "fetch_status_code_value": fetch_status_code_value,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: coinbase/agentkit#1514
# ---------------------------------------------------------------------------
def evaluate_agentkit_agenda_guard_evidence_boundary(
    *,
    protocol_family: str,
    recipient: str,
    amount_usd: float,
    velocity_24h_usd: float | None,
    max_single_limit_usd: float,
    daily_velocity_limit_usd: float,
    calldata: str,
    intent: str,
    remote_http_called_on_local_reject: bool,
    allow_redirects: bool,
    returned_is_safe: bool,
    returned_decision: str,
    sanctions_aml_claimed_true: bool,
    velocity_limits_claimed_true: bool,
    history_verified_claimed_true: bool,
) -> GuardEvaluation:
    """Validate AgentKit AgendaGuard pre-sign EVM evidence review boundary (#1514)."""
    if protocol_family != "evm":
        return GuardEvaluation(
            scenario_id="agentkit_agenda_guard_boundary",
            passed=False,
            action="Send to a human",
            reason_code="AGENDA_GUARD_UNSUPPORTED_NON_EVM_NETWORK",
            details={"protocol_family": protocol_family},
        )
    for name, val in (
        ("max_single_limit_usd", max_single_limit_usd),
        ("daily_velocity_limit_usd", daily_velocity_limit_usd),
    ):
        if not math.isfinite(val) or val <= 0:
            return GuardEvaluation(
                scenario_id="agentkit_agenda_guard_boundary",
                passed=False,
                action="Send to a human",
                reason_code="AGENDA_GUARD_INVALID_LIMIT_CONFIG",
                details={"field": name, "value": val},
            )
    if not math.isfinite(amount_usd) or amount_usd < 0 or (
        velocity_24h_usd is not None and (not math.isfinite(velocity_24h_usd) or velocity_24h_usd < 0)
    ):
        return GuardEvaluation(
            scenario_id="agentkit_agenda_guard_boundary",
            passed=False,
            action="Send to a human",
            reason_code="AGENDA_GUARD_INVALID_FINANCIAL_INPUT",
            details={"amount_usd": amount_usd, "velocity_24h_usd": velocity_24h_usd},
        )
    if (
        returned_is_safe
        or sanctions_aml_claimed_true
        or velocity_limits_claimed_true
        or history_verified_claimed_true
        or allow_redirects
    ):
        return GuardEvaluation(
            scenario_id="agentkit_agenda_guard_boundary",
            passed=False,
            action="Send to a human",
            reason_code="AGENDA_GUARD_FALSE_AUTHORIZATION_OR_REDIRECT_RELAXATION",
            details={
                "returned_is_safe": returned_is_safe,
                "allow_redirects": allow_redirects,
            },
        )
    norm_recipient = recipient.strip().lower()
    norm_calldata = calldata.strip().lower()
    denied = norm_recipient in AGENDA_LOCAL_RISK_DENYLIST
    unlimited = norm_calldata.startswith("0x095ea7b3") and any(
        p.search(norm_calldata) for p in AGENDA_UNLIMITED_ALLOWANCE_PATTERNS
    )
    suspicious = any(p.search(intent) for p in AGENDA_ADVERSARIAL_INTENT_PATTERNS)
    local_reject_required = denied or unlimited or suspicious

    if local_reject_required:
        if returned_decision != "reject" or remote_http_called_on_local_reject:
            return GuardEvaluation(
                scenario_id="agentkit_agenda_guard_boundary",
                passed=False,
                action="Send to a human",
                reason_code="AGENDA_GUARD_LOCAL_REJECTION_BYPASSED_OR_LEAKED_HTTP",
                details={
                    "returned_decision": returned_decision,
                    "remote_http_called_on_local_reject": remote_http_called_on_local_reject,
                },
            )
        return GuardEvaluation(
            scenario_id="agentkit_agenda_guard_boundary",
            passed=True,
            action="Send to a human",
            reason_code="AGENDA_GUARD_LOCAL_EVIDENCE_REJECTED_DETERMINISTICALLY",
            details={"decision": returned_decision, "is_safe": False},
        )

    if returned_decision not in ("step_up_human_required", "reject"):
        return GuardEvaluation(
            scenario_id="agentkit_agenda_guard_boundary",
            passed=False,
            action="Send to a human",
            reason_code="AGENDA_GUARD_REMOTE_ALLOW_RELAXED_HUMAN_STEP_UP",
            details={"returned_decision": returned_decision},
        )

    return GuardEvaluation(
        scenario_id="agentkit_agenda_guard_boundary",
        passed=True,
        action="Confirm",
        reason_code="AGENDA_GUARD_STEP_UP_HUMAN_REQUIRED_ENFORCED",
        details={"decision": returned_decision, "is_safe": False},
    )


# ---------------------------------------------------------------------------
# PR-05: coinbase/agentkit#1519
# ---------------------------------------------------------------------------
def evaluate_agentkit_sbor_benchmark_rate_guard(
    *,
    benchmark: str,
    side: str,
    offered_rate_pct: float,
    benchmark_rate_pct: float | None,
    fixing_age_hours: float | None,
    missing_benchmark_treated_as_zero: bool,
    metadata_sanitized: bool,
    stop_and_ask_human_returned: bool,
) -> GuardEvaluation:
    """Validate AgentKit SBOR read-only lending benchmark provider (#1519)."""
    if benchmark not in SBOR_BENCHMARKS or side not in ("borrow", "supply"):
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_INVALID_BENCHMARK_OR_SIDE",
            details={"benchmark": benchmark, "side": side},
        )
    if not math.isfinite(offered_rate_pct) or offered_rate_pct <= 0 or offered_rate_pct > 100:
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_OFFERED_RATE_OUT_OF_PERCENTAGE_BOUNDS",
            details={"offered_rate_pct": offered_rate_pct},
        )
    if missing_benchmark_treated_as_zero or not metadata_sanitized:
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_MISSING_BENCHMARK_ZEROED_OR_UNSANITIZED_METADATA",
            details={
                "missing_benchmark_treated_as_zero": missing_benchmark_treated_as_zero,
                "metadata_sanitized": metadata_sanitized,
            },
        )
    if fixing_age_hours is None or not math.isfinite(fixing_age_hours) or fixing_age_hours > 48.0:
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_FIXING_STALE_OVER_48_HOURS",
            details={"fixing_age_hours": fixing_age_hours},
        )
    if benchmark_rate_pct is None or not math.isfinite(benchmark_rate_pct):
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_BENCHMARK_NOT_PUBLISHED_IN_FIXING",
            details={"benchmark": benchmark},
        )
    diff_bps = round((offered_rate_pct - benchmark_rate_pct) * 100)
    expected_stop = side == "borrow" and (offered_rate_pct - benchmark_rate_pct) * 100 > 50.0
    if stop_and_ask_human_returned != expected_stop:
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=False,
            action="Send to a human",
            reason_code="SBOR_STOP_AND_ASK_HUMAN_FLAG_MISMATCH",
            details={
                "diff_bps": diff_bps,
                "expected_stop": expected_stop,
                "stop_and_ask_human_returned": stop_and_ask_human_returned,
            },
        )
    if expected_stop:
        return GuardEvaluation(
            scenario_id="agentkit_sbor_benchmark_rate",
            passed=True,
            action="Confirm",
            reason_code="SBOR_BORROW_OVER_50BPS_HUMAN_CONFIRMATION_REQUIRED",
            details={"diff_bps": diff_bps, "stopAndAskHuman": True},
        )
    return GuardEvaluation(
        scenario_id="agentkit_sbor_benchmark_rate",
        passed=True,
        action="Act automatically",
        reason_code="SBOR_BENCHMARK_RATE_WITHIN_THRESHOLD",
        details={"diff_bps": diff_bps, "stopAndAskHuman": False},
    )


# ---------------------------------------------------------------------------
# PR-06: coinbase/agentkit#1518
# ---------------------------------------------------------------------------
def evaluate_agentkit_groundtruth_record_guard(
    *,
    address: str,
    explicit_chain: str | None,
    inferred_chain: str,
    api_url_has_trailing_slash: bool,
    creator_described_as_safe: bool,
    unsettled_coin_described_as_clean: bool,
    known_bad_null_treated_as_innocent: bool,
    known_bad_flag: bool | None,
    resolved_launches: int,
    binomial_p_value: float | None,
    http_status: int,
    http_402_x402_remedy_surfaced: bool,
) -> GuardEvaluation:
    """Validate AgentKit GROUNDTRUTH memecoin creator/coin record and known-bad statistical guard (#1518)."""
    expected_chain = explicit_chain or ("rh" if address.startswith("0x") else "solana")
    if inferred_chain != expected_chain or api_url_has_trailing_slash:
        return GuardEvaluation(
            scenario_id="agentkit_groundtruth_record",
            passed=False,
            action="Send to a human",
            reason_code="GROUNDTRUTH_CHAIN_INFERENCE_OR_URL_NORMALIZATION_INVALID",
            details={"inferred_chain": inferred_chain, "expected_chain": expected_chain},
        )
    if (
        creator_described_as_safe
        or unsettled_coin_described_as_clean
        or known_bad_null_treated_as_innocent
    ):
        return GuardEvaluation(
            scenario_id="agentkit_groundtruth_record",
            passed=False,
            action="Send to a human",
            reason_code="GROUNDTRUTH_RECORD_MISINTERPRETED_AS_SAFETY_RATING",
            details={
                "creator_described_as_safe": creator_described_as_safe,
                "unsettled_coin_described_as_clean": unsettled_coin_described_as_clean,
                "known_bad_null_treated_as_innocent": known_bad_null_treated_as_innocent,
            },
        )
    if http_status == 402 and not http_402_x402_remedy_surfaced:
        return GuardEvaluation(
            scenario_id="agentkit_groundtruth_record",
            passed=False,
            action="Send to a human",
            reason_code="GROUNDTRUTH_HTTP_402_MISSING_X402_OR_API_KEY_REMEDY",
            details={"http_status": http_status},
        )
    if known_bad_flag is True:
        if resolved_launches < 5 or binomial_p_value is None or binomial_p_value >= 0.01:
            return GuardEvaluation(
                scenario_id="agentkit_groundtruth_record",
                passed=False,
                action="Send to a human",
                reason_code="GROUNDTRUTH_KNOWN_BAD_STATISTICAL_BASIS_INVALID",
                details={
                    "resolved_launches": resolved_launches,
                    "binomial_p_value": binomial_p_value,
                },
            )
        return GuardEvaluation(
            scenario_id="agentkit_groundtruth_record",
            passed=False,
            action="Send to a human",
            reason_code="GROUNDTRUTH_CREATOR_FLAGGED_KNOWN_BAD",
            details={
                "resolved_launches": resolved_launches,
                "binomial_p_value": binomial_p_value,
            },
        )
    return GuardEvaluation(
        scenario_id="agentkit_groundtruth_record",
        passed=True,
        action="Act automatically",
        reason_code="GROUNDTRUTH_RECORD_SEMANTICS_VERIFIED",
        details={"chain": inferred_chain, "known_bad_flag": known_bad_flag},
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/go-sdk#1451 & #1356
# ---------------------------------------------------------------------------
def evaluate_mcp_go_extauth_resource_and_www_authenticate_guard(
    *,
    prm_resource: str,
    endpoint_params_resource: list[str],
    redirects_restricted: bool,
    www_authenticate_header: str,
    parsed_error_param: str | None,
    step_up_authorization_triggered: bool,
) -> GuardEvaluation:
    """Validate MCP Go SDK ClientCredentialsHandler RFC 8707 resource param (#1451) and RFC 9110 empty WWW-Authenticate list elements (#1356)."""
    if not prm_resource or endpoint_params_resource != [prm_resource] or not redirects_restricted:
        return GuardEvaluation(
            scenario_id="mcp_go_extauth_resource_www_auth",
            passed=False,
            action="Send to a human",
            reason_code="MCP_GO_CLIENT_CREDENTIALS_MISSING_RFC8707_RESOURCE_OR_REDIRECT_GUARD",
            details={
                "prm_resource": prm_resource,
                "endpoint_params_resource": endpoint_params_resource,
                "redirects_restricted": redirects_restricted,
            },
        )
    has_empty_element_insufficient_scope = (
        ",," in www_authenticate_header and 'error="insufficient_scope"' in www_authenticate_header
    )
    if has_empty_element_insufficient_scope and (
        parsed_error_param != "insufficient_scope" or not step_up_authorization_triggered
    ):
        return GuardEvaluation(
            scenario_id="mcp_go_extauth_resource_www_auth",
            passed=False,
            action="Send to a human",
            reason_code="MCP_GO_WWW_AUTHENTICATE_EMPTY_ELEMENT_DROPPED_INSUFFICIENT_SCOPE",
            details={"parsed_error_param": parsed_error_param},
        )
    return GuardEvaluation(
        scenario_id="mcp_go_extauth_resource_www_auth",
        passed=True,
        action="Act automatically",
        reason_code="MCP_GO_EXTAUTH_RESOURCE_AND_WWW_AUTHENTICATE_VERIFIED",
        details={"resource": prm_resource, "parsed_error_param": parsed_error_param},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/rust-sdk#1308 & #1303
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_cache_hints_and_invalid_params_guard(
    *,
    negotiated_protocol_version: str,
    result_is_complete: bool,
    ttl_ms: int | None,
    cache_scope: str | None,
    legacy_result_type_stripped: bool,
    malformed_request_method: str,
    returned_jsonrpc_error_code: int,
) -> GuardEvaluation:
    """Validate MCP Rust SDK 2026-07-28 default missing cache hints (#1308) and -32602 INVALID_PARAMS for ungated spec methods (#1303)."""
    is_2026_07_28_or_later = negotiated_protocol_version >= "2026-07-28"
    if is_2026_07_28_or_later and result_is_complete:
        if ttl_ms is None or ttl_ms < 0 or cache_scope not in ("private", "public"):
            return GuardEvaluation(
                scenario_id="mcp_rust_cache_hints_and_invalid_params",
                passed=False,
                action="Send to a human",
                reason_code="MCP_RUST_2026_07_28_MISSING_CACHE_HINTS",
                details={"ttl_ms": ttl_ms, "cache_scope": cache_scope},
            )
    elif not is_2026_07_28_or_later and not legacy_result_type_stripped:
        return GuardEvaluation(
            scenario_id="mcp_rust_cache_hints_and_invalid_params",
            passed=False,
            action="Send to a human",
            reason_code="MCP_RUST_LEGACY_PEER_RESULT_TYPE_NOT_STRIPPED",
            details={"negotiated_protocol_version": negotiated_protocol_version},
        )

    if malformed_request_method in MCP_UNGATED_SPEC_METHODS:
        if returned_jsonrpc_error_code != -32602:
            return GuardEvaluation(
                scenario_id="mcp_rust_cache_hints_and_invalid_params",
                passed=False,
                action="Send to a human",
                reason_code="MCP_RUST_UNGATED_SPEC_METHOD_RETURNED_METHOD_NOT_FOUND",
                details={
                    "malformed_request_method": malformed_request_method,
                    "returned_jsonrpc_error_code": returned_jsonrpc_error_code,
                },
            )
    elif malformed_request_method in MCP_GATED_OR_DISCOVERY_METHODS:
        if returned_jsonrpc_error_code not in (-32601, -32602):
            return GuardEvaluation(
                scenario_id="mcp_rust_cache_hints_and_invalid_params",
                passed=False,
                action="Send to a human",
                reason_code="MCP_RUST_UNEXPECTED_GATED_ERROR_CODE",
                details={"returned_jsonrpc_error_code": returned_jsonrpc_error_code},
            )

    return GuardEvaluation(
        scenario_id="mcp_rust_cache_hints_and_invalid_params",
        passed=True,
        action="Act automatically",
        reason_code="MCP_RUST_CACHE_HINTS_AND_INVALID_PARAMS_VERIFIED",
        details={"ttl_ms": ttl_ms, "cache_scope": cache_scope, "error_code": returned_jsonrpc_error_code},
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/rust-sdk#1305 & #1304
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_structured_prm_error_and_stdio_pipes_guard(
    *,
    prm_error_variant: str,
    preserves_oauth_http_client_error_source: bool,
    flattened_to_string_metadata_error: bool,
    stdin_is_fifo: bool,
    stdout_is_fifo: bool,
    selected_transport_backend: str,
    fd_duplicated_with_o_nonblock: bool,
) -> GuardEvaluation:
    """Validate MCP Rust SDK structured protected-resource discovery errors (#1305) and non-blocking FIFO stdio_pipes transport (#1304)."""
    valid_variants = {
        "DiscoveryRequestFailed",
        "ProtectedResourceMetadataInvalid",
        "AuthorizationServersUnavailable",
        "None",
    }
    if flattened_to_string_metadata_error or prm_error_variant not in valid_variants:
        return GuardEvaluation(
            scenario_id="mcp_rust_prm_error_and_stdio_pipes",
            passed=False,
            action="Send to a human",
            reason_code="MCP_RUST_PRM_ERROR_FLATTENED_TO_STRING",
            details={"prm_error_variant": prm_error_variant},
        )
    if prm_error_variant == "DiscoveryRequestFailed" and not preserves_oauth_http_client_error_source:
        return GuardEvaluation(
            scenario_id="mcp_rust_prm_error_and_stdio_pipes",
            passed=False,
            action="Send to a human",
            reason_code="MCP_RUST_DISCOVERY_ERROR_SOURCE_CHAIN_LOST",
            details={"prm_error_variant": prm_error_variant},
        )
    both_fifos = stdin_is_fifo and stdout_is_fifo
    if both_fifos:
        if selected_transport_backend != "unix_pipe_reactor" or not fd_duplicated_with_o_nonblock:
            return GuardEvaluation(
                scenario_id="mcp_rust_prm_error_and_stdio_pipes",
                passed=False,
                action="Send to a human",
                reason_code="MCP_RUST_STDIO_PIPES_BLOCKING_POOL_FALLBACK_ON_FIFO",
                details={"selected_transport_backend": selected_transport_backend},
            )
    else:
        if selected_transport_backend != "tokio_blocking_stdio":
            return GuardEvaluation(
                scenario_id="mcp_rust_prm_error_and_stdio_pipes",
                passed=False,
                action="Send to a human",
                reason_code="MCP_RUST_NON_FIFO_WRAPPED_AS_UNIX_PIPE",
                details={"selected_transport_backend": selected_transport_backend},
            )
    return GuardEvaluation(
        scenario_id="mcp_rust_prm_error_and_stdio_pipes",
        passed=True,
        action="Act automatically",
        reason_code="MCP_RUST_PRM_ERROR_AND_STDIO_PIPES_VERIFIED",
        details={"selected_transport_backend": selected_transport_backend},
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/typescript-sdk#2995 & #3007
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_uri_exploded_path_and_ajv_format_guard(
    *,
    template_operator: str,
    exploded: bool,
    uri_input: str,
    matched_segments: list[str] | None,
    uri_length_validated: bool,
    default_ajv_unknown_format_warning_suppressed: bool,
    known_formats_still_validated: bool,
    custom_ajv_logger_preserved: bool,
) -> GuardEvaluation:
    """Validate MCP TypeScript SDK exploded slash-separated URI template matching (#2995) and quiet v2 default Ajv unknown-format logger (#3007)."""
    if not uri_length_validated or len(uri_input) > 1_000_000:
        return GuardEvaluation(
            scenario_id="mcp_ts_uri_exploded_and_ajv_format",
            passed=False,
            action="Send to a human",
            reason_code="MCP_TS_URI_TEMPLATE_LENGTH_UNBOUNDED",
            details={"uri_len": len(uri_input)},
        )
    if template_operator == "/" and exploded:
        if not matched_segments or any("/" in seg or "," in seg for seg in matched_segments):
            return GuardEvaluation(
                scenario_id="mcp_ts_uri_exploded_and_ajv_format",
                passed=False,
                action="Send to a human",
                reason_code="MCP_TS_EXPLODED_SLASH_PATH_MATCH_FAILED",
                details={"matched_segments": matched_segments},
            )
    if (
        not default_ajv_unknown_format_warning_suppressed
        or not known_formats_still_validated
        or not custom_ajv_logger_preserved
    ):
        return GuardEvaluation(
            scenario_id="mcp_ts_uri_exploded_and_ajv_format",
            passed=False,
            action="Send to a human",
            reason_code="MCP_TS_AJV_FORMAT_LOGGER_MISCONFIGURED",
            details={
                "default_ajv_unknown_format_warning_suppressed": default_ajv_unknown_format_warning_suppressed,
                "known_formats_still_validated": known_formats_still_validated,
                "custom_ajv_logger_preserved": custom_ajv_logger_preserved,
            },
        )
    return GuardEvaluation(
        scenario_id="mcp_ts_uri_exploded_and_ajv_format",
        passed=True,
        action="Act automatically",
        reason_code="MCP_TS_URI_EXPLODED_AND_AJV_FORMAT_VERIFIED",
        details={"matched_segments": matched_segments},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/kotlin-sdk#1019, #999 & #998
# ---------------------------------------------------------------------------
def evaluate_mcp_kotlin_session_result_and_cancellation_guard(
    *,
    uses_atomic_persistent_list_for_initialized: bool,
    late_registered_on_initialized_ran_immediately: bool,
    concurrent_registrations_preserved_count: int,
    expected_registrations_count: int,
    raw_result_captured_on_wire_decode: bool,
    sse_replay_rewrites_id_in_raw_json_not_copy: bool,
    deserializes_by_request_method_first: bool,
    cancellation_exception_suppressed_from_on_error: bool,
) -> GuardEvaluation:
    """Validate MCP Kotlin SDK atomic onInitialized callbacks (#1019), method-keyed rawResult deserialization (#999), and CancellationException suppression (#998)."""
    if (
        not uses_atomic_persistent_list_for_initialized
        or not late_registered_on_initialized_ran_immediately
        or concurrent_registrations_preserved_count != expected_registrations_count
    ):
        return GuardEvaluation(
            scenario_id="mcp_kotlin_session_result_cancellation",
            passed=False,
            action="Send to a human",
            reason_code="MCP_KOTLIN_ON_INITIALIZED_RACE_OR_LATE_CALLBACK_DROPPED",
            details={
                "concurrent_registrations_preserved_count": concurrent_registrations_preserved_count,
                "expected_registrations_count": expected_registrations_count,
            },
        )
    if (
        not raw_result_captured_on_wire_decode
        or not sse_replay_rewrites_id_in_raw_json_not_copy
        or not deserializes_by_request_method_first
    ):
        return GuardEvaluation(
            scenario_id="mcp_kotlin_session_result_cancellation",
            passed=False,
            action="Send to a human",
            reason_code="MCP_KOTLIN_SHAPE_POLYMORPHISM_CLASS_CAST_OR_COPY_DROPPED_RAW_RESULT",
            details={
                "raw_result_captured_on_wire_decode": raw_result_captured_on_wire_decode,
                "sse_replay_rewrites_id_in_raw_json_not_copy": sse_replay_rewrites_id_in_raw_json_not_copy,
            },
        )
    if not cancellation_exception_suppressed_from_on_error:
        return GuardEvaluation(
            scenario_id="mcp_kotlin_session_result_cancellation",
            passed=False,
            action="Send to a human",
            reason_code="MCP_KOTLIN_CANCELLATION_EXCEPTION_REPORTED_AS_ERROR",
            details={"cancellation_exception_suppressed_from_on_error": False},
        )
    return GuardEvaluation(
        scenario_id="mcp_kotlin_session_result_cancellation",
        passed=True,
        action="Act automatically",
        reason_code="MCP_KOTLIN_SESSION_RESULT_AND_CANCELLATION_VERIFIED",
        details={"callbacks_executed": concurrent_registrations_preserved_count},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/inspector#2704, #2703 & #2707
# ---------------------------------------------------------------------------
def evaluate_mcp_inspector_cli_target_timeout_and_schema_form_guard(
    *,
    cli_option_precedes_stdio_target: bool,
    stdio_target_preserved: bool,
    unknown_server_flags_forwarded: bool,
    client_surface: str,
    timeout_remedy_text: str,
    array_of_object_schema_rendered_as_rows: bool,
) -> GuardEvaluation:
    """Validate MCP Inspector CLI option-preceding stdio target (#2704), client-specific connect-timeout remedies (#2703), and ObjectArrayField schema rows (#2707)."""
    if cli_option_precedes_stdio_target and (
        not stdio_target_preserved or not unknown_server_flags_forwarded
    ):
        return GuardEvaluation(
            scenario_id="mcp_inspector_cli_timeout_schema_form",
            passed=False,
            action="Send to a human",
            reason_code="MCP_INSPECTOR_CLI_STDIO_TARGET_OR_SERVER_FLAG_DROPPED",
            details={
                "stdio_target_preserved": stdio_target_preserved,
                "unknown_server_flags_forwarded": unknown_server_flags_forwarded,
            },
        )
    if client_surface in ("cli", "mcpdo") and "Server Settings" in timeout_remedy_text:
        return GuardEvaluation(
            scenario_id="mcp_inspector_cli_timeout_schema_form",
            passed=False,
            action="Send to a human",
            reason_code="MCP_INSPECTOR_WEB_SERVER_SETTINGS_REMEDY_SHOWN_IN_CLI",
            details={"client_surface": client_surface, "timeout_remedy_text": timeout_remedy_text},
        )
    if client_surface in ("cli", "mcpdo") and "--connect-timeout" not in timeout_remedy_text:
        return GuardEvaluation(
            scenario_id="mcp_inspector_cli_timeout_schema_form",
            passed=False,
            action="Send to a human",
            reason_code="MCP_INSPECTOR_CLI_MISSING_CONNECT_TIMEOUT_FLAG_REMEDY",
            details={"client_surface": client_surface, "timeout_remedy_text": timeout_remedy_text},
        )
    if not array_of_object_schema_rendered_as_rows:
        return GuardEvaluation(
            scenario_id="mcp_inspector_cli_timeout_schema_form",
            passed=False,
            action="Send to a human",
            reason_code="MCP_INSPECTOR_ARRAY_OF_OBJECTS_FELL_BACK_TO_RAW_JSON",
            details={"array_of_object_schema_rendered_as_rows": False},
        )
    return GuardEvaluation(
        scenario_id="mcp_inspector_cli_timeout_schema_form",
        passed=True,
        action="Act automatically",
        reason_code="MCP_INSPECTOR_CLI_TIMEOUT_AND_SCHEMA_FORM_VERIFIED",
        details={"client_surface": client_surface},
    )


# ---------------------------------------------------------------------------
# PR-13: a2aproject/a2a-python#1307, #1304 & #1301
# ---------------------------------------------------------------------------
def evaluate_a2a_python_card_parse_version_and_jsonrpc_stderr_guard(
    *,
    decoded_agent_card_is_dict: bool,
    compat_helper_raised_type_or_attr_error: bool,
    normalized_to_agent_card_resolution_error: bool,
    advertised_versions: list[str],
    selected_interface_version: str,
    malformed_jsonrpc_printed_traceback_to_stderr: bool,
) -> GuardEvaluation:
    """Validate A2A Python AgentCard ParseError normalization (#1307), major_minor 1.0.0 interface negotiation (#1304), and quiet -32700 JSON-RPC dispatcher (#1301)."""
    if (not decoded_agent_card_is_dict or compat_helper_raised_type_or_attr_error) and not normalized_to_agent_card_resolution_error:
        return GuardEvaluation(
            scenario_id="a2a_python_card_version_jsonrpc",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_UNHANDLED_CARD_TYPE_OR_ATTRIBUTE_ERROR",
            details={"decoded_agent_card_is_dict": decoded_agent_card_is_dict},
        )
    has_1_0_patch = any(v.startswith("1.0.") or v == "1.0" for v in advertised_versions)
    if has_1_0_patch and not selected_interface_version.startswith("1.0"):
        return GuardEvaluation(
            scenario_id="a2a_python_card_version_jsonrpc",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_PATCH_VERSION_1_0_0_FELL_BACK_TO_0_3",
            details={
                "advertised_versions": advertised_versions,
                "selected_interface_version": selected_interface_version,
            },
        )
    if malformed_jsonrpc_printed_traceback_to_stderr:
        return GuardEvaluation(
            scenario_id="a2a_python_card_version_jsonrpc",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_MALFORMED_JSONRPC_TRACEBACK_STDERR_LEAK",
            details={"malformed_jsonrpc_printed_traceback_to_stderr": True},
        )
    return GuardEvaluation(
        scenario_id="a2a_python_card_version_jsonrpc",
        passed=True,
        action="Act automatically",
        reason_code="A2A_PYTHON_CARD_VERSION_AND_JSONRPC_VERIFIED",
        details={"selected_interface_version": selected_interface_version},
    )


# ---------------------------------------------------------------------------
# PR-14: a2aproject/a2a-python#1306, #1300 & #1298
# ---------------------------------------------------------------------------
def evaluate_a2a_python_send_config_rest_error_and_followup_guard(
    *,
    v03_proto_send_config_history_length: int,
    mapped_send_config_history_length: int | None,
    rest_error_payload: Any,
    rest_http_status: int,
    raised_attribute_error_on_non_status_body: bool,
    mapped_to_http_status_fallback_error: bool,
    existing_task_re_emitted_on_stream_followup: bool,
    followup_message_to_save_preserved: bool,
    spurious_duplicate_task_error_logged: bool,
) -> GuardEvaluation:
    """Validate A2A Python v0.3 SendMessageConfiguration history_length=0->None (#1306), non-Status REST error fallback (#1300), and streaming follow-up message_to_save preservation (#1298)."""
    if v03_proto_send_config_history_length == 0 and mapped_send_config_history_length is not None:
        return GuardEvaluation(
            scenario_id="a2a_python_send_config_rest_followup",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_V03_SEND_MESSAGE_ZERO_HISTORY_TRUNCATED",
            details={"mapped_send_config_history_length": mapped_send_config_history_length},
        )
    is_valid_google_rpc_status = (
        isinstance(rest_error_payload, dict) and isinstance(rest_error_payload.get("error"), dict)
    )
    if not is_valid_google_rpc_status and (
        raised_attribute_error_on_non_status_body or not mapped_to_http_status_fallback_error
    ):
        return GuardEvaluation(
            scenario_id="a2a_python_send_config_rest_followup",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_REST_NON_STATUS_ERROR_RAISED_ATTRIBUTE_ERROR",
            details={"rest_http_status": rest_http_status},
        )
    if existing_task_re_emitted_on_stream_followup and (
        not followup_message_to_save_preserved or spurious_duplicate_task_error_logged
    ):
        return GuardEvaluation(
            scenario_id="a2a_python_send_config_rest_followup",
            passed=False,
            action="Send to a human",
            reason_code="A2A_PYTHON_STREAMING_FOLLOWUP_MESSAGE_DROPPED_ON_REEMITTED_TASK",
            details={
                "followup_message_to_save_preserved": followup_message_to_save_preserved,
                "spurious_duplicate_task_error_logged": spurious_duplicate_task_error_logged,
            },
        )
    return GuardEvaluation(
        scenario_id="a2a_python_send_config_rest_followup",
        passed=True,
        action="Act automatically",
        reason_code="A2A_PYTHON_SEND_CONFIG_REST_AND_FOLLOWUP_VERIFIED",
        details={"mapped_send_config_history_length": mapped_send_config_history_length},
    )


# ---------------------------------------------------------------------------
# PR-15: a2aproject/a2a-java#1215 & #1213 + a2aproject/a2a-js#703
# ---------------------------------------------------------------------------
def evaluate_a2a_java_explicit_null_struct_and_js_migration_guard(
    *,
    struct_contains_explicit_null: bool,
    from_proto_value_returns_null_for_null_value: bool,
    from_proto_struct_uses_hashmap_not_collectors_to_map: bool,
    to_proto_maps_null_to_null_value: bool,
    centralized_assert_is_null_or_empty_used: bool,
    a2a_js_kysely_push_store_migration_applied: bool,
    a2a_js_node_engine_major: int,
) -> GuardEvaluation:
    """Validate A2A Java v0.3 explicit JSON null Struct conversion (#1215), centralized Assert.isNullOrEmpty (#1213), and A2A JS Kysely push notification store migrations (#703)."""
    if struct_contains_explicit_null and (
        not from_proto_value_returns_null_for_null_value
        or not from_proto_struct_uses_hashmap_not_collectors_to_map
        or not to_proto_maps_null_to_null_value
    ):
        return GuardEvaluation(
            scenario_id="a2a_java_null_struct_and_js_migration",
            passed=False,
            action="Send to a human",
            reason_code="A2A_JAVA_V03_EXPLICIT_JSON_NULL_THROW_OR_NPE",
            details={
                "from_proto_value_returns_null_for_null_value": from_proto_value_returns_null_for_null_value,
                "from_proto_struct_uses_hashmap_not_collectors_to_map": from_proto_struct_uses_hashmap_not_collectors_to_map,
            },
        )
    if not centralized_assert_is_null_or_empty_used:
        return GuardEvaluation(
            scenario_id="a2a_java_null_struct_and_js_migration",
            passed=False,
            action="Send to a human",
            reason_code="A2A_JAVA_FRAGMENTED_SERVER_VALIDATION",
            details={"centralized_assert_is_null_or_empty_used": False},
        )
    if not a2a_js_kysely_push_store_migration_applied or a2a_js_node_engine_major < 22:
        return GuardEvaluation(
            scenario_id="a2a_java_null_struct_and_js_migration",
            passed=False,
            action="Send to a human",
            reason_code="A2A_JS_PUSH_STORE_MIGRATION_OR_NODE_ENGINE_INVALID",
            details={"a2a_js_node_engine_major": a2a_js_node_engine_major},
        )
    return GuardEvaluation(
        scenario_id="a2a_java_null_struct_and_js_migration",
        passed=True,
        action="Act automatically",
        reason_code="A2A_JAVA_NULL_STRUCT_AND_JS_MIGRATION_VERIFIED",
        details={"a2a_js_node_engine_major": a2a_js_node_engine_major},
    )


# ---------------------------------------------------------------------------
# PR-16: End-to-End Cross-Stack Synthesis Guard
# ---------------------------------------------------------------------------
def evaluate_stage262_cross_stack_synthesis_guard(
    *,
    stripe_eval: GuardEvaluation,
    agentkit_eval: GuardEvaluation,
    mcp_eval: GuardEvaluation,
    a2a_eval: GuardEvaluation,
) -> GuardEvaluation:
    """Validate end-to-end synthesis across Stripe CLI/SDK, AgentKit, MCP, and A2A guards."""
    sub_evals = (stripe_eval, agentkit_eval, mcp_eval, a2a_eval)
    failed = [e for e in sub_evals if not e.passed]
    if failed:
        return GuardEvaluation(
            scenario_id="stage262_cross_stack_synthesis",
            passed=False,
            action="Send to a human",
            reason_code=f"SYNTHESIS_HALTED_BY_{failed[0].reason_code}",
            details={"failed_scenarios": [e.scenario_id for e in failed]},
        )
    if any(e.action == "Confirm" for e in sub_evals):
        return GuardEvaluation(
            scenario_id="stage262_cross_stack_synthesis",
            passed=True,
            action="Confirm",
            reason_code="STAGE262_CROSS_STACK_SYNTHESIS_STEP_UP_CONFIRMED",
            details={"verified_layers": [e.scenario_id for e in sub_evals]},
        )
    return GuardEvaluation(
        scenario_id="stage262_cross_stack_synthesis",
        passed=True,
        action="Act automatically",
        reason_code="STAGE262_CROSS_STACK_SYNTHESIS_VERIFIED",
        details={"verified_layers": [e.scenario_id for e in sub_evals]},
    )
