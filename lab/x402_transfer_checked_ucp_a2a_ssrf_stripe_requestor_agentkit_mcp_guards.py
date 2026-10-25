"""Stage 274 deterministic protocol and security guards (137 zero-overlap primary-source PRs, PR-01..PR-16).

Covers:
- PR-01 (x402-foundation/x402#3132, #3133, #3153, #3180):
  TS SVM exact TransferChecked instruction discriminator (data[0] == 12), TS SIWX challenge
  origin binding to 402 response URL, Monad USDC v1 EIP-712 domain name "USDC", and missing/null
  accepted requirements protocol error handling without TypeError.
- PR-02 (x402-foundation/x402#3156, #3155, #3164, #3183, #3190):
  Go SDK buyer spendControls (maxAmountPerCall, maxCumulativeSpend, allowedPayees), TS SVM upto
  ComputeBudget instructions, SVM batch-settlement channel monotonicity, and injected RPC client
  validation for Go/TS SVM upto facilitators.
- PR-03 (x402-foundation/x402#3186, #3131, #3241, #3255, #3274, #3315):
  offer-receipt v2 proof-of-delivery responseHash binding, experimental shared-payment-token (spt)
  scheme merchant/amount/expiry verification, Go/Python/TS default asset parity, Python MCP payment
  flow hooks, SVM upto RPC config separation, and builder-code `a` field validation.
- PR-04 (Universal-Commerce-Protocol/ucp#889, #888, #886, #885, #878, #851, #772, #704, #700):
  Off-site link classification in check_links.py (protocol-relative and external schemes), serialized
  gh-pages deploys with job timeouts, uv pre-commit validator execution, and latest spec link parity.
- PR-05 (a2aproject/A2A#2322, #2319, #2310, #2270, #2246, #2240):
  Client-written artifacts on SendMessageRequest, valid §8.4.1 RFC 8785 JCS AgentCard example,
  Message.sender attribution, TaskState terminal vs non-terminal interrupted semantics, jcs_depth_v1
  nesting bound (<= 128), and AI Catalog discovery preference.
- PR-06 (a2aproject/a2a-python#1164, #1218, #1220, #1222, #1225, #1243):
  Push-notification webhook URL SSRF hardening before dispatch, defensive deep-copy of in-memory
  push configs, out-of-range datetime task ordering guard, configurable SSE shutdown grace period,
  A2A-Version minor & query fallback validation, and ACTS conformance auth precondition.
- PR-07 (a2aproject/a2a-python#1183, #1182, #1180, #1177, #1176, #1167, #1165, #1158, #1153):
  Task state transition validation (blocking terminal escape), JSON-RPC/gRPC internal error message
  sanitization, abstract get_info_for_dispatch, history_length upper bound, task ID length & message
  content validation, gRPC error mapping & A2A-Version enforcement, and TCK Task-before-status ordering.
- PR-08 (a2aproject/a2a-java#1141, #1148, #1149, #1156, #1163, #1124, #1112, a2aproject/a2a-js#743):
  Java HTTP PostBuilder followRedirects=false default, SSEParserConfig 1 MB per-line limit, per-task
  push notification ordering, unknown tenant 404 on @PublicAgentCard, omitted push config ID generation,
  GHSA-4fpj-g9jf-9rgg threat model, and JS optional driver peers.
- PR-09 (stripe/stripe-node#2862, #2865, #2870, #2871, #2874, #2880, #2892, #2899):
  Removal of top-level stripe.constructEventWithoutVerification, removal of top-level ErrorType export,
  stripe-mock OPENAPI_VERSION pin, Node >= 20 requirement, explicit types-test failure, and npm release env.
- PR-10 (stripe/stripe-python#1896, #1909, #1910, #1914, #1915, #1918, #1923, #1935):
  APIRequestor URL hardening against cross-origin/traversal resource paths in fetch_related_object,
  removal of StripeObject.request, TransferReversal rename, notice suppression, and positional-only path args.
- PR-11 (stripe/stripe-go#2440, #2442, #2445, #2451, #2453, #2455, #2456, #2461,
  stripe/stripe-cli#2111, #2114, #2115, #2118, #2121, #2138, #2139, #2142, #2146):
  Go exact decimal string representation, dynamic map free-form objects, Go >= 1.24 floor, CLI custom
  install directory auto-update preservation, unified agentsetup RunCommand, and sandbox login guidance.
- PR-12 (coinbase/agentkit#1480, #1468, #1481, #1479, #1474, #1473, #1464, #1462):
  ERC-20 token metadata sanitization against indirect prompt injection, x402 quote/settlement-identity/
  maxPaymentUsdc binding, merona seller pre-check, TruthBear verification, DefiLlama TVL, and Taskmarket escrow.
- PR-13 (modelcontextprotocol/go-sdk#1223, #1224, #1226, #1232, #1241, #1244, #1339, #1409,
  modelcontextprotocol/rust-sdk#1231, #1247, #1256):
  Go legacy transport max body size, StreamKeepAlive SSE comments, json.Number precision in tool schemas,
  non-blocking cancel notify on teardown, disallowing OPTIONS in CORS AllowedMethods, Rust saturating SSE
  reconnect backoff, protocol version negotiation exposure, and 2026-07-28 session/GET stream release.
- PR-14 (modelcontextprotocol/python-sdk#3462, #3470, #3485, #3516, #3541,
  modelcontextprotocol/typescript-sdk#2990, #2993, #2994, #3009, #3083):
  Python byte-for-byte path-less OAuth resource indicator preservation, TypeAdapter validation, replay
  buffer before network delivery, TS separate Set-Cookie header array forwarding, clearing stale stdio
  frames before restart, and RFC 6570 operator-aware scalar URI variable expansion.
- PR-15 (modelcontextprotocol/csharp-sdk#1838, #1839, #1841, #1843, #1845, #1849, #1853,
  modelcontextprotocol/java-sdk#1168, #1170, modelcontextprotocol/kotlin-sdk#695, #696, #697, #706):
  C# SseClientSessionTransport POST response disposal, closing stdio input before waiting for exit,
  CIMD public client `none` token auth, AutoDetect 405 JSON-RPC SSE fallback, Java 400 INVALID_REQUEST
  on malformed body, and Kotlin SEP-986 tool name validation, SEP-1613 $schema, & CancellationException propagation.
- PR-16 (modelcontextprotocol/inspector#2687, #2688, #2689, #2693, #2695, #2711, #2729, #2741):
  Hiding 'Run as task' on modern-era (2026-07-28) connections via offersRunAsTask, universal --version/-V
  launcher output, TUI Esc filter clearing before exit, one-line browser opener warning, and sidebar column clamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import ipaddress
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardVerdict:
    passed: bool
    scenario_id: str
    code: str
    detail: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PR-01: x402-foundation/x402#3132, #3133, #3153, #3180
# ---------------------------------------------------------------------------
def verify_x402_svm_transfer_checked_siwx_monad_accepted_guard(
    *,
    svm_instruction_index_2_data: Sequence[int],
    siwx_challenge_origin: str,
    response_402_origin: str,
    monad_usdc_eip712_domain_name: str,
    accepted_requirements: Mapping[str, Any] | None,
) -> GuardVerdict:
    """Validate x402 SVM TransferChecked discriminator, SIWX origin, Monad USDC domain, and accepted presence."""
    if not svm_instruction_index_2_data or int(svm_instruction_index_2_data[0]) != 12:
        disc = svm_instruction_index_2_data[0] if svm_instruction_index_2_data else None
        return GuardVerdict(
            False,
            "PR-01",
            "X402_SVM_EXACT_TRANSFER_CHECKED_DISCRIMINATOR_REQUIRED",
            f"SVM exact instruction[2] discriminator {disc!r} != 12 (TransferChecked required)",
            {"discriminator": disc},
        )
    if siwx_challenge_origin.strip().lower() != response_402_origin.strip().lower():
        return GuardVerdict(
            False,
            "PR-01",
            "X402_SIWX_CHALLENGE_ORIGIN_MISMATCH",
            f"SIWX challenge origin {siwx_challenge_origin!r} != 402 response origin {response_402_origin!r}",
            {"challenge_origin": siwx_challenge_origin, "response_origin": response_402_origin},
        )
    if monad_usdc_eip712_domain_name != "USDC":
        return GuardVerdict(
            False,
            "PR-01",
            "X402_MONAD_USDC_DOMAIN_NAME_INVALID",
            f"Monad USDC EIP-712 domain name {monad_usdc_eip712_domain_name!r} != 'USDC'",
            {"domain_name": monad_usdc_eip712_domain_name},
        )
    if not isinstance(accepted_requirements, Mapping) or not accepted_requirements.get("scheme"):
        return GuardVerdict(
            False,
            "PR-01",
            "X402_MISSING_ACCEPTED_REQUIREMENTS_NO_MATCH",
            "Missing or null accepted payment requirements treated as stable no-match error",
            {"accepted_present": isinstance(accepted_requirements, Mapping)},
        )
    return GuardVerdict(
        True,
        "PR-01",
        "X402_SVM_TRANSFER_CHECKED_SIWX_MONAD_ACCEPTED_VERIFIED",
        "SVM TransferChecked discriminator 12, SIWX origin, Monad 'USDC' domain, and accepted requirements verified",
        {"discriminator": 12, "origin": response_402_origin},
    )


# ---------------------------------------------------------------------------
# PR-02: x402-foundation/x402#3156, #3155, #3164, #3183, #3190
# ---------------------------------------------------------------------------
def verify_x402_go_spend_controls_svm_upto_compute_budget_guard(
    *,
    call_amount_atomic: int,
    max_amount_per_call_atomic: int,
    cumulative_spend_atomic: int,
    max_cumulative_spend_atomic: int,
    payee: str,
    allowed_payees: Sequence[str],
    has_compute_unit_limit_ix: bool,
    has_compute_unit_price_ix: bool,
    batch_cumulative_monotonic: bool,
    upto_facilitator_rpc_injected: bool,
) -> GuardVerdict:
    """Validate Go SDK spendControls, SVM upto ComputeBudget instructions, batch monotonicity, and RPC injection."""
    if call_amount_atomic <= 0 or call_amount_atomic > max_amount_per_call_atomic:
        return GuardVerdict(
            False,
            "PR-02",
            "X402_SPEND_CONTROLS_PER_CALL_LIMIT_EXCEEDED",
            f"Call amount {call_amount_atomic} exceeds maxAmountPerCall {max_amount_per_call_atomic}",
            {"call_amount_atomic": call_amount_atomic, "max_amount_per_call_atomic": max_amount_per_call_atomic},
        )
    if cumulative_spend_atomic + call_amount_atomic > max_cumulative_spend_atomic:
        return GuardVerdict(
            False,
            "PR-02",
            "X402_SPEND_CONTROLS_CUMULATIVE_LIMIT_EXCEEDED",
            "Cumulative spend would exceed buyer maxCumulativeSpend ceiling",
            {"projected_cumulative": cumulative_spend_atomic + call_amount_atomic},
        )
    if allowed_payees and payee not in allowed_payees:
        return GuardVerdict(
            False,
            "PR-02",
            "X402_SPEND_CONTROLS_PAYEE_NOT_ALLOWED",
            f"Payee {payee!r} is not in buyer spendControls.allowedPayees",
            {"payee": payee},
        )
    if not has_compute_unit_limit_ix or not has_compute_unit_price_ix:
        return GuardVerdict(
            False,
            "PR-02",
            "X402_SVM_UPTO_COMPUTE_BUDGET_MISSING",
            "SVM upto transaction must include ComputeBudget unit limit and unit price instructions",
            {"has_limit": has_compute_unit_limit_ix, "has_price": has_compute_unit_price_ix},
        )
    if not batch_cumulative_monotonic or not upto_facilitator_rpc_injected:
        return GuardVerdict(
            False,
            "PR-02",
            "X402_SVM_BATCH_OR_FACILITATOR_RPC_INVALID",
            "SVM batch-settlement must remain monotonic and upto facilitator must accept injected RPC client",
            {"batch_monotonic": batch_cumulative_monotonic, "rpc_injected": upto_facilitator_rpc_injected},
        )
    return GuardVerdict(
        True,
        "PR-02",
        "X402_SPEND_CONTROLS_AND_SVM_UPTO_VERIFIED",
        "Go spendControls, SVM upto ComputeBudget instructions, batch settlement, and RPC injection verified",
        {"remaining_budget": max_cumulative_spend_atomic - (cumulative_spend_atomic + call_amount_atomic)},
    )


# ---------------------------------------------------------------------------
# PR-03: x402-foundation/x402#3186, #3131, #3241, #3255, #3274, #3315
# ---------------------------------------------------------------------------
_BUILDER_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def verify_x402_offer_receipt_pod_spt_builder_code_guard(
    *,
    receipt_version: int,
    delivered_body_bytes: bytes,
    signed_response_hash_hex: str,
    signed_response_hash_alg: str,
    signed_response_hash_encoding: str,
    spt_merchant_id: str,
    expected_merchant_id: str,
    spt_amount_atomic: int,
    required_amount_atomic: int,
    spt_not_expired: bool,
    builder_code_a: str,
) -> GuardVerdict:
    """Validate offer-receipt v2 proof-of-delivery responseHash, shared-payment-token scope, and builder-code `a`."""
    computed_hash = hashlib.sha256(delivered_body_bytes).hexdigest()
    if receipt_version == 2:
        if signed_response_hash_alg != "sha256" or signed_response_hash_encoding not in ("raw", "identity"):
            return GuardVerdict(
                False,
                "PR-03",
                "X402_OFFER_RECEIPT_V2_HASH_METADATA_INVALID",
                f"Invalid v2 offer-receipt hash metadata alg={signed_response_hash_alg!r}, enc={signed_response_hash_encoding!r}",
                {"alg": signed_response_hash_alg, "encoding": signed_response_hash_encoding},
            )
        if signed_response_hash_hex.lower() != computed_hash.lower():
            return GuardVerdict(
                False,
                "PR-03",
                "X402_OFFER_RECEIPT_PROOF_OF_DELIVERY_HASH_MISMATCH",
                "Delivered response body SHA-256 does not match signed offer-receipt v2 responseHash",
                {"expected": computed_hash, "actual": signed_response_hash_hex},
            )
    if spt_merchant_id != expected_merchant_id or spt_amount_atomic != required_amount_atomic or not spt_not_expired:
        return GuardVerdict(
            False,
            "PR-03",
            "X402_SHARED_PAYMENT_TOKEN_SCOPE_MISMATCH",
            "Shared Payment Token (SPT) merchant, fixed-price amount, or expiry failed verification",
            {"spt_merchant_id": spt_merchant_id, "spt_amount_atomic": spt_amount_atomic, "not_expired": spt_not_expired},
        )
    if not _BUILDER_CODE_RE.match(builder_code_a):
        return GuardVerdict(
            False,
            "PR-03",
            "X402_BUILDER_CODE_A_FIELD_INVALID",
            f"Invalid builder-code `a` field {builder_code_a!r} (must match ^[A-Za-z0-9_-]{{1,32}}$)",
            {"builder_code_a": builder_code_a},
        )
    return GuardVerdict(
        True,
        "PR-03",
        "X402_OFFER_RECEIPT_POD_SPT_BUILDER_CODE_VERIFIED",
        "offer-receipt v2 proof-of-delivery responseHash, SPT fixed-price scope, and builder-code verified",
        {"response_hash": computed_hash, "builder_code_a": builder_code_a},
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp#889, #888, #886, #885, #878, #851, #772, #704, #700
# ---------------------------------------------------------------------------
def verify_ucp_offsite_link_checker_ci_serialization_guard(
    *,
    candidate_link: str,
    classified_as_external: bool,
    gh_pages_serialized_concurrency: bool,
    gh_pages_has_timeout_minutes: bool,
    pre_commit_uses_uv: bool,
    readme_points_to_latest_spec: bool,
) -> GuardVerdict:
    """Validate UCP off-site link classification (#772), gh-pages concurrency/timeout (#700), and uv hooks (#704)."""
    parsed = urlparse(candidate_link)
    is_offsite = bool(parsed.scheme in ("http", "https") or candidate_link.startswith("//") or bool(parsed.netloc))
    if is_offsite and not classified_as_external:
        return GuardVerdict(
            False,
            "PR-04",
            "UCP_OFFSITE_LINK_MISCLASSIFIED_AS_LOCAL_PATH",
            f"Off-site link {candidate_link!r} must be classified as external in check_links.py",
            {"candidate_link": candidate_link},
        )
    if not gh_pages_serialized_concurrency or not gh_pages_has_timeout_minutes:
        return GuardVerdict(
            False,
            "PR-04",
            "UCP_GH_PAGES_DEPLOY_UNSERIALIZED_OR_NO_TIMEOUT",
            "gh-pages deploy workflow must serialize concurrency and enforce job timeout-minutes",
            {"serialized": gh_pages_serialized_concurrency, "has_timeout": gh_pages_has_timeout_minutes},
        )
    if not pre_commit_uses_uv or not readme_points_to_latest_spec:
        return GuardVerdict(
            False,
            "PR-04",
            "UCP_PRECOMMIT_UV_OR_LATEST_SPEC_LINK_DRIFT",
            "Pre-commit validators must run through uv and README must link to latest spec",
            {"pre_commit_uses_uv": pre_commit_uses_uv, "readme_latest": readme_points_to_latest_spec},
        )
    return GuardVerdict(
        True,
        "PR-04",
        "UCP_OFFSITE_LINK_AND_CI_SERIALIZATION_VERIFIED",
        "UCP off-site link classification, serialized gh-pages deploy, uv pre-commit, and spec link verified",
        {"candidate_link": candidate_link, "is_offsite": is_offsite},
    )


# ---------------------------------------------------------------------------
# PR-05: a2aproject/A2A#2322, #2319, #2310, #2270, #2246, #2240
# ---------------------------------------------------------------------------
_A2A_TERMINAL_STATES = frozenset({"TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED", "TASK_STATE_REJECTED"})
_A2A_INTERRUPTED_NON_TERMINAL_STATES = frozenset({"TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"})


def verify_a2a_spec_client_artifacts_interrupted_state_jcs_depth_guard(
    *,
    task_state: str,
    treated_as_terminal: bool,
    client_artifacts_accepted_in_send_message: bool,
    message_sender_attributed: bool,
    jcs_nesting_depth: int,
    spec_card_jcs_example_valid: bool,
) -> GuardVerdict:
    """Validate A2A spec TaskState interrupted non-terminal semantics, client artifacts, and JCS depth <= 128."""
    if task_state in _A2A_INTERRUPTED_NON_TERMINAL_STATES and treated_as_terminal:
        return GuardVerdict(
            False,
            "PR-05",
            "A2A_INTERRUPTED_TASK_STATE_MISTREATED_AS_TERMINAL",
            f"Interrupted state {task_state} is non-terminal and must remain transitionable by the server",
            {"task_state": task_state},
        )
    if task_state in _A2A_TERMINAL_STATES and not treated_as_terminal:
        return GuardVerdict(
            False,
            "PR-05",
            "A2A_TERMINAL_TASK_STATE_NOT_ENFORCED",
            f"Terminal state {task_state} must be classified as terminal",
            {"task_state": task_state},
        )
    if jcs_nesting_depth > 128:
        return GuardVerdict(
            False,
            "PR-05",
            "A2A_JCS_DEPTH_V1_BOUND_EXCEEDED",
            f"JCS nesting depth {jcs_nesting_depth} exceeds jcs_depth_v1 bound of 128",
            {"jcs_nesting_depth": jcs_nesting_depth},
        )
    if not client_artifacts_accepted_in_send_message or not message_sender_attributed or not spec_card_jcs_example_valid:
        return GuardVerdict(
            False,
            "PR-05",
            "A2A_CLIENT_ARTIFACTS_OR_SENDER_ATTRIBUTION_MISSING",
            "SendMessageRequest client artifacts, Message.sender attribution, and valid §8.4.1 AgentCard required",
            {"client_artifacts": client_artifacts_accepted_in_send_message, "sender": message_sender_attributed},
        )
    return GuardVerdict(
        True,
        "PR-05",
        "A2A_SPEC_ARTIFACTS_INTERRUPTED_JCS_DEPTH_VERIFIED",
        "A2A non-terminal interrupted states, SendMessageRequest artifacts, sender attribution, and jcs_depth_v1 verified",
        {"task_state": task_state, "jcs_nesting_depth": jcs_nesting_depth},
    )


# ---------------------------------------------------------------------------
# PR-06: a2aproject/a2a-python#1164, #1218, #1220, #1222, #1225, #1243
# ---------------------------------------------------------------------------
def _is_ssrf_unsafe_webhook_url(webhook_url: str) -> tuple[bool, str]:
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https":
        return True, f"non-https scheme {parsed.scheme!r}"
    host = (parsed.hostname or "").strip().lower()
    if not host or host in ("localhost", "localhost.localdomain") or host.endswith(".internal") or host.endswith(".local"):
        return True, f"forbidden internal hostname {host!r}"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True, f"non-global IP {ip}"
    except ValueError:
        pass
    return False, "ok"


def verify_a2a_python_push_ssrf_deepcopy_version_guard(
    *,
    webhook_url: str,
    stored_push_config_shares_caller_ref: bool,
    task_ordering_handles_out_of_range_datetime: bool,
    sse_shutdown_grace_period_seconds: float,
    a2a_version_header: str,
) -> GuardVerdict:
    """Validate A2A Python push-notification SSRF guard (#1164), deep-copy isolation (#1218), and A2A-Version (#1225)."""
    unsafe, reason = _is_ssrf_unsafe_webhook_url(webhook_url)
    if unsafe:
        return GuardVerdict(
            False,
            "PR-06",
            "A2A_PYTHON_PUSH_WEBHOOK_SSRF_BLOCKED",
            f"Push-notification webhook URL rejected by SSRF guard: {reason}",
            {"webhook_url": webhook_url, "reason": reason},
        )
    if stored_push_config_shares_caller_ref:
        return GuardVerdict(
            False,
            "PR-06",
            "A2A_PYTHON_PUSH_CONFIG_MUTABLE_ALIAS_LEAK",
            "InMemoryPushNotificationConfigStore must deep-copy push configs on set_info/get_info",
            {"shares_caller_ref": True},
        )
    if not re.match(r"^(0\.3|1\.\d+)$", a2a_version_header.strip()):
        return GuardVerdict(
            False,
            "PR-06",
            "A2A_PYTHON_INVALID_A2A_VERSION_MINOR",
            f"Unsupported or malformed A2A-Version {a2a_version_header!r}",
            {"a2a_version": a2a_version_header},
        )
    if not task_ordering_handles_out_of_range_datetime or sse_shutdown_grace_period_seconds < 0:
        return GuardVerdict(
            False,
            "PR-06",
            "A2A_PYTHON_DATETIME_ORDERING_OR_SSE_GRACE_INVALID",
            "Task ordering must guard out-of-range datetimes and SSE grace period must be non-negative",
            {"grace_seconds": sse_shutdown_grace_period_seconds},
        )
    return GuardVerdict(
        True,
        "PR-06",
        "A2A_PYTHON_PUSH_SSRF_DEEPCOPY_VERSION_VERIFIED",
        "A2A Python push webhook SSRF guard, deep-copied config store, datetime ordering, and A2A-Version verified",
        {"webhook_url": webhook_url, "a2a_version": a2a_version_header},
    )


# ---------------------------------------------------------------------------
# PR-07: a2aproject/a2a-python#1183, #1182, #1180, #1177, #1176, #1167, #1165, #1158, #1153
# ---------------------------------------------------------------------------
def verify_a2a_python_terminal_escape_error_sanitization_bounds_guard(
    *,
    current_task_state: str,
    next_task_state: str,
    error_message_returned_to_client: str,
    history_length_requested: int,
    max_history_length: int,
    task_id: str,
    message_parts_count: int,
    tck_task_enqueued_before_status_event: bool,
) -> GuardVerdict:
    """Validate A2A Python terminal state transition lock (#1182), error sanitization (#1183), and bounds (#1177/#1176)."""
    if current_task_state in _A2A_TERMINAL_STATES and next_task_state != current_task_state:
        return GuardVerdict(
            False,
            "PR-07",
            "A2A_PYTHON_TERMINAL_STATE_ESCAPE_BLOCKED",
            f"Cannot transition task from terminal state {current_task_state} to {next_task_state}",
            {"current": current_task_state, "next": next_task_state},
        )
    if any(tok in error_message_returned_to_client for tok in ("Traceback", "sqlalchemy.", "psycopg", "/home/", "C:\\")):
        return GuardVerdict(
            False,
            "PR-07",
            "A2A_PYTHON_UNSANITIZED_INTERNAL_ERROR_LEAK",
            "Internal exception details leaked in JSON-RPC / gRPC client error message",
            {"error_message": error_message_returned_to_client},
        )
    if history_length_requested < 0 or history_length_requested > max_history_length:
        return GuardVerdict(
            False,
            "PR-07",
            "A2A_PYTHON_HISTORY_LENGTH_UPPER_BOUND_EXCEEDED",
            f"Requested history_length {history_length_requested} exceeds upper bound {max_history_length}",
            {"history_length": history_length_requested, "max_history_length": max_history_length},
        )
    if not task_id or len(task_id) > 256 or message_parts_count <= 0 or not tck_task_enqueued_before_status_event:
        return GuardVerdict(
            False,
            "PR-07",
            "A2A_PYTHON_TASK_ID_OR_MESSAGE_CONTENT_INVALID",
            "Task ID must be 1..256 chars, message content non-empty, and Task enqueued before status update",
            {"task_id_len": len(task_id), "message_parts_count": message_parts_count},
        )
    return GuardVerdict(
        True,
        "PR-07",
        "A2A_PYTHON_TERMINAL_LOCK_AND_SANITIZATION_VERIFIED",
        "A2A Python terminal state lock, error message sanitization, history_length cap, and task bounds verified",
        {"state": next_task_state, "history_length": history_length_requested},
    )


# ---------------------------------------------------------------------------
# PR-08: a2aproject/a2a-java#1141, #1148, #1149, #1156, #1163, #1124, #1112, a2aproject/a2a-js#743
# ---------------------------------------------------------------------------
def verify_a2a_java_redirect_sse_line_cap_tenant_card_guard(
    *,
    post_builder_follow_redirects_default: bool,
    sse_line_bytes: int,
    sse_max_line_bytes: int,
    per_task_push_order_preserved: bool,
    tenant_exists: bool,
    public_card_http_status: int,
) -> GuardVerdict:
    """Validate A2A Java PostBuilder followRedirects=false default (#1141), 1 MB SSE line cap (#1149), and tenant 404 (#1112)."""
    if post_builder_follow_redirects_default:
        return GuardVerdict(
            False,
            "PR-08",
            "A2A_JAVA_POST_BUILDER_REDIRECT_DEFAULT_UNSAFE",
            "PostBuilder.followRedirects must default to false to prevent cross-origin credential leakage",
            {"follow_redirects_default": True},
        )
    if sse_line_bytes > sse_max_line_bytes:
        return GuardVerdict(
            False,
            "PR-08",
            "A2A_JAVA_SSE_LINE_LENGTH_LIMIT_EXCEEDED",
            f"SSE line length {sse_line_bytes} exceeds SSEParserConfig limit {sse_max_line_bytes}",
            {"sse_line_bytes": sse_line_bytes, "max_bytes": sse_max_line_bytes},
        )
    if not tenant_exists and public_card_http_status != 404:
        return GuardVerdict(
            False,
            "PR-08",
            "A2A_JAVA_UNKNOWN_TENANT_CARD_MUST_RETURN_404",
            f"Unknown tenant on public agent card returned HTTP {public_card_http_status} instead of 404",
            {"http_status": public_card_http_status},
        )
    if not per_task_push_order_preserved:
        return GuardVerdict(
            False,
            "PR-08",
            "A2A_JAVA_PER_TASK_PUSH_ORDER_VIOLATION",
            "Push notifications for a single task must be delivered in sequential order",
            {"per_task_push_order_preserved": False},
        )
    return GuardVerdict(
        True,
        "PR-08",
        "A2A_JAVA_REDIRECT_SSE_TENANT_CARD_VERIFIED",
        "A2A Java PostBuilder redirect default=false, 1 MB SSE line limit, per-task push order, and tenant 404 verified",
        {"sse_max_line_bytes": sse_max_line_bytes, "public_card_http_status": public_card_http_status},
    )


# ---------------------------------------------------------------------------
# PR-09: stripe/stripe-node#2862, #2865, #2870, #2871, #2874, #2880, #2892, #2899
# ---------------------------------------------------------------------------
def verify_stripe_node_webhook_verification_runtime_guard(
    *,
    top_level_construct_event_without_verification_exposed: bool,
    top_level_error_type_exported: bool,
    node_major_version: int,
    stripe_mock_matches_openapi_version: bool,
    types_test_fails_on_error: bool,
    npm_publish_requires_release_env: bool,
) -> GuardVerdict:
    """Validate Stripe Node removal of top-level constructEventWithoutVerification (#2862) and Node >= 20 (#2871)."""
    if top_level_construct_event_without_verification_exposed:
        return GuardVerdict(
            False,
            "PR-09",
            "STRIPE_NODE_TOP_LEVEL_UNVERIFIED_CONSTRUCT_EVENT_EXPOSED",
            "Deprecated top-level stripe.constructEventWithoutVerification must be removed (#2862)",
            {"exposed": True},
        )
    if top_level_error_type_exported:
        return GuardVerdict(
            False,
            "PR-09",
            "STRIPE_NODE_TOP_LEVEL_ERRORTYPE_EXPORTED",
            "Top-level ErrorType export must be removed from Stripe client (#2865)",
            {"error_type_exported": True},
        )
    if node_major_version < 20:
        return GuardVerdict(
            False,
            "PR-09",
            "STRIPE_NODE_UNSUPPORTED_NODE_18_RUNTIME",
            f"Node.js major version {node_major_version} < 20 (Node 18 support dropped in #2871)",
            {"node_major_version": node_major_version},
        )
    if not (stripe_mock_matches_openapi_version and types_test_fails_on_error and npm_publish_requires_release_env):
        return GuardVerdict(
            False,
            "PR-09",
            "STRIPE_NODE_BUILD_OR_RELEASE_CONTRACT_DRIFT",
            "stripe-mock version pin, types-test error gate, and npm release environment are required",
            {"stripe_mock_pinned": stripe_mock_matches_openapi_version},
        )
    return GuardVerdict(
        True,
        "PR-09",
        "STRIPE_NODE_WEBHOOK_AND_RUNTIME_VERIFIED",
        "Stripe Node top-level unverified webhook helper removal, Node >= 20 floor, and release guards verified",
        {"node_major_version": node_major_version},
    )


# ---------------------------------------------------------------------------
# PR-10: stripe/stripe-python#1896, #1909, #1910, #1914, #1915, #1918, #1923, #1935
# ---------------------------------------------------------------------------
def verify_stripe_python_requestor_malicious_url_guard(
    *,
    resource_url: str,
    stripe_object_request_method_removed: bool,
    transfer_reversal_renamed: bool,
    positional_only_path_params: bool,
) -> GuardVerdict:
    """Validate Stripe Python APIRequestor defense against malicious resource URLs (#1896) and v16 cleanups."""
    parsed = urlparse(resource_url)
    if parsed.scheme or parsed.netloc or not resource_url.startswith("/") or resource_url.startswith("//") or ".." in resource_url.split("/"):
        return GuardVerdict(
            False,
            "PR-10",
            "STRIPE_PYTHON_MALICIOUS_RESOURCE_URL_REJECTED",
            f"Malicious or off-origin resource URL {resource_url!r} rejected by APIRequestor (#1896)",
            {"resource_url": resource_url},
        )
    if not (stripe_object_request_method_removed and transfer_reversal_renamed and positional_only_path_params):
        return GuardVerdict(
            False,
            "PR-10",
            "STRIPE_PYTHON_V16_SURFACE_DRIFT",
            "StripeObject.request removal, TransferReversal rename, and positional-only path args required",
            {"request_removed": stripe_object_request_method_removed},
        )
    return GuardVerdict(
        True,
        "PR-10",
        "STRIPE_PYTHON_REQUESTOR_URL_AND_V16_VERIFIED",
        "Stripe Python APIRequestor relative path hardening and v16 surface contracts verified",
        {"resource_url": resource_url},
    )


# ---------------------------------------------------------------------------
# PR-11: stripe/stripe-go#2440, #2442, #2445, #2451, #2453, #2455, #2456, #2461,
#        stripe/stripe-cli#2111, #2114, #2115, #2118, #2121, #2138, #2139, #2142, #2146
# ---------------------------------------------------------------------------
_DECIMAL_STRING_RE = re.compile(r"^-?\d+(\.\d+)?$")


def verify_stripe_go_exact_decimal_cli_autoupdate_dir_guard(
    *,
    decimal_wire_value: Any,
    freeform_object_is_dynamic_map: bool,
    go_minor_version: int,
    cli_custom_install_dir_preserved: bool,
    agentsetup_single_run_command: bool,
) -> GuardVerdict:
    """Validate Stripe Go exact decimal wire representation (#2442/#2455), Go >= 24 (#2453), and CLI install dir (#2111)."""
    if not isinstance(decimal_wire_value, str) or not _DECIMAL_STRING_RE.match(decimal_wire_value):
        return GuardVerdict(
            False,
            "PR-11",
            "STRIPE_GO_FLOAT_PRECISION_DRIFT_ON_DECIMAL",
            f"Decimal value {decimal_wire_value!r} must use exact string-backed decimal type instead of float64",
            {"decimal_wire_value": decimal_wire_value},
        )
    if go_minor_version < 24:
        return GuardVerdict(
            False,
            "PR-11",
            "STRIPE_GO_UNSUPPORTED_RUNTIME_BELOW_1_24",
            f"Go 1.{go_minor_version} is unsupported (Go 1.22 and 1.23 dropped in #2453)",
            {"go_minor_version": go_minor_version},
        )
    if not (freeform_object_is_dynamic_map and cli_custom_install_dir_preserved and agentsetup_single_run_command):
        return GuardVerdict(
            False,
            "PR-11",
            "STRIPE_GO_DYNAMIC_MAP_OR_CLI_INSTALL_DIR_DRIFT",
            "Free-form dynamic maps, CLI custom install dir preservation, and unified agentsetup RunCommand required",
            {"custom_dir_preserved": cli_custom_install_dir_preserved},
        )
    return GuardVerdict(
        True,
        "PR-11",
        "STRIPE_GO_EXACT_DECIMAL_AND_CLI_DIR_VERIFIED",
        "Stripe Go exact decimal type, dynamic maps, Go >= 1.24 floor, and CLI custom install dir verified",
        {"decimal": decimal_wire_value, "go_version": f"1.{go_minor_version}"},
    )


# ---------------------------------------------------------------------------
# PR-12: coinbase/agentkit#1480, #1468, #1481, #1479, #1474, #1473, #1464, #1462
# ---------------------------------------------------------------------------
_PROMPT_INJECTION_PATTERNS = ("ignore previous", "system prompt", "transfer all", "\x00", "\r", "\n")


def verify_agentkit_erc20_metadata_x402_quote_binding_guard(
    *,
    raw_token_name: str,
    raw_token_symbol: str,
    sanitized_metadata_enforced: bool,
    quoted_pay_to: str,
    settlement_pay_to: str,
    quoted_amount_usdc: float,
    settlement_amount_usdc: float,
    max_payment_usdc: float,
    quote_already_consumed: bool,
) -> GuardVerdict:
    """Validate AgentKit ERC-20 metadata sanitization (#1480) and x402 quote/identity/limit binding (#1468)."""
    lowered = f"{raw_token_name} {raw_token_symbol}".lower()
    if any(pat in lowered for pat in _PROMPT_INJECTION_PATTERNS) and not sanitized_metadata_enforced:
        return GuardVerdict(
            False,
            "PR-12",
            "AGENTKIT_ERC20_METADATA_PROMPT_INJECTION_UNSANITIZED",
            "Untrusted ERC-20 token name/symbol contains prompt-injection or control characters without sanitization",
            {"raw_token_name": raw_token_name, "raw_token_symbol": raw_token_symbol},
        )
    if quote_already_consumed:
        return GuardVerdict(
            False,
            "PR-12",
            "AGENTKIT_X402_ONE_USE_QUOTE_REPLAYED",
            "One-use x402 quote binding has already been consumed and cannot be replayed (#1468)",
            {"quote_already_consumed": True},
        )
    if quoted_pay_to.lower() != settlement_pay_to.lower() or abs(quoted_amount_usdc - settlement_amount_usdc) > 1e-9:
        return GuardVerdict(
            False,
            "PR-12",
            "AGENTKIT_X402_QUOTE_OR_SETTLEMENT_IDENTITY_DRIFT",
            "Settlement payTo or amount drifted from the frozen preflight x402 quote (#1468)",
            {"quoted_pay_to": quoted_pay_to, "settlement_pay_to": settlement_pay_to},
        )
    if settlement_amount_usdc > max_payment_usdc:
        return GuardVerdict(
            False,
            "PR-12",
            "AGENTKIT_X402_AUTO_PAY_LIMIT_EXCEEDED",
            f"Settlement amount {settlement_amount_usdc} USDC exceeds maxPaymentUsdc {max_payment_usdc}",
            {"settlement_amount_usdc": settlement_amount_usdc, "max_payment_usdc": max_payment_usdc},
        )
    return GuardVerdict(
        True,
        "PR-12",
        "AGENTKIT_ERC20_SANITIZATION_AND_X402_QUOTE_VERIFIED",
        "AgentKit ERC-20 token metadata sanitization and x402 quote/identity/auto-pay limit binding verified",
        {"settlement_pay_to": settlement_pay_to, "settlement_amount_usdc": settlement_amount_usdc},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/go-sdk#1223, #1224, #1226, #1232, #1241, #1244, #1339, #1409,
#        modelcontextprotocol/rust-sdk#1231, #1247, #1256
# ---------------------------------------------------------------------------
def verify_mcp_go_body_limit_rust_saturating_backoff_guard(
    *,
    legacy_transport_body_bytes: int,
    max_body_bytes: int,
    cors_allowed_methods: Sequence[str],
    json_number_precision_preserved: bool,
    retry_attempt: int,
    base_backoff_ms: int,
    max_backoff_ms: int,
    computed_backoff_ms: int,
    session_kept_on_2026_07_28: bool,
) -> GuardVerdict:
    """Validate MCP Go legacy max request body (#1224), CORS methods (#1223), and Rust saturating SSE backoff (#1231)."""
    if legacy_transport_body_bytes > max_body_bytes:
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_GO_LEGACY_TRANSPORT_BODY_LIMIT_EXCEEDED",
            f"Legacy SSE request body {legacy_transport_body_bytes} bytes exceeds max {max_body_bytes} bytes (#1224)",
            {"body_bytes": legacy_transport_body_bytes, "max_body_bytes": max_body_bytes},
        )
    if "OPTIONS" in [m.upper() for m in cors_allowed_methods]:
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_GO_CORS_OPTIONS_METHOD_FORBIDDEN",
            "CORS AllowedMethods config must not explicitly list OPTIONS (#1223)",
            {"cors_allowed_methods": list(cors_allowed_methods)},
        )
    expected_saturated = min(max_backoff_ms, base_backoff_ms * (2 ** min(retry_attempt, 62)))
    if computed_backoff_ms <= 0 or computed_backoff_ms > max_backoff_ms or computed_backoff_ms != expected_saturated:
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_RUST_SSE_BACKOFF_OVERFLOW_OR_UNSATURATED",
            f"SSE reconnect backoff {computed_backoff_ms}ms failed saturating cap {expected_saturated}ms (#1231)",
            {"computed_backoff_ms": computed_backoff_ms, "expected_saturated": expected_saturated},
        )
    if not json_number_precision_preserved or session_kept_on_2026_07_28:
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_GO_NUMBER_PRECISION_OR_RUST_2026_07_28_SESSION_LEAK",
            "Go tool schema JSON number precision and Rust 2026-07-28 stateless session release required",
            {"json_number_precision_preserved": json_number_precision_preserved},
        )
    return GuardVerdict(
        True,
        "PR-13",
        "MCP_GO_BODY_LIMIT_AND_RUST_SATURATING_BACKOFF_VERIFIED",
        "MCP Go body limit, CORS config, json.Number precision, and Rust saturating SSE backoff verified",
        {"saturated_backoff_ms": computed_backoff_ms},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/python-sdk#3462, #3470, #3485, #3516, #3541,
#        modelcontextprotocol/typescript-sdk#2990, #2993, #2994, #3009, #3083
# ---------------------------------------------------------------------------
def verify_mcp_python_exact_resource_ts_set_cookie_stdio_guard(
    *,
    advertised_prm_resource: str,
    serialized_oauth_resource_param: str,
    response_set_cookie_headers: Sequence[str],
    forwarded_set_cookie_headers: Sequence[str],
    stale_stdio_frames_cleared_on_restart: bool,
    replay_buffered_before_live_handoff: bool,
) -> GuardVerdict:
    """Validate MCP Python exact RFC 8707 resource indicator (#3462) and TS multi-Set-Cookie forwarding (#2990)."""
    if advertised_prm_resource != serialized_oauth_resource_param:
        return GuardVerdict(
            False,
            "PR-14",
            "MCP_PYTHON_OAUTH_RESOURCE_INDICATOR_TRAILING_SLASH_MUTATED",
            f"OAuth resource indicator mutated from {advertised_prm_resource!r} to {serialized_oauth_resource_param!r} (#3462)",
            {"advertised": advertised_prm_resource, "serialized": serialized_oauth_resource_param},
        )
    if list(response_set_cookie_headers) != list(forwarded_set_cookie_headers):
        return GuardVerdict(
            False,
            "PR-14",
            "MCP_TS_NODE_ADAPTER_SET_COOKIE_DROPPED",
            "Node response adapter dropped or collapsed multiple Set-Cookie headers (#2990)",
            {"expected_count": len(response_set_cookie_headers), "forwarded_count": len(forwarded_set_cookie_headers)},
        )
    if not stale_stdio_frames_cleared_on_restart or not replay_buffered_before_live_handoff:
        return GuardVerdict(
            False,
            "PR-14",
            "MCP_TS_STALE_STDIO_OR_PYTHON_REPLAY_HANDOFF_DRIFT",
            "TS stdio client must clear stale frames on restart (#2993) and Python must buffer replay before live handoff (#3541)",
            {"stdio_cleared": stale_stdio_frames_cleared_on_restart},
        )
    return GuardVerdict(
        True,
        "PR-14",
        "MCP_PYTHON_RESOURCE_AND_TS_SET_COOKIE_VERIFIED",
        "MCP Python byte-for-byte OAuth resource indicator, TS Set-Cookie forwarding, and stdio reset verified",
        {"resource": serialized_oauth_resource_param, "cookies_count": len(forwarded_set_cookie_headers)},
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/csharp-sdk#1838, #1839, #1841, #1843, #1845, #1849, #1853,
#        modelcontextprotocol/java-sdk#1168, #1170, modelcontextprotocol/kotlin-sdk#695, #696, #697, #706
# ---------------------------------------------------------------------------
_SEP986_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def verify_mcp_csharp_sse_dispose_java_400_kotlin_sep986_guard(
    *,
    csharp_sse_post_response_disposed: bool,
    csharp_stdio_input_closed_before_wait: bool,
    cimd_public_client_token_auth_method: str,
    java_malformed_body_http_status: int,
    kotlin_tool_name: str,
    kotlin_cancellation_exception_propagated: bool,
) -> GuardVerdict:
    """Validate MCP C# SSE POST disposal (#1841), CIMD `none` auth (#1845), Java 400 (#1168), and Kotlin SEP-986 (#695)."""
    if not csharp_sse_post_response_disposed or not csharp_stdio_input_closed_before_wait:
        return GuardVerdict(
            False,
            "PR-15",
            "MCP_CSHARP_SSE_POST_LEAK_OR_STDIO_HANG",
            "C# SseClientSessionTransport must dispose POST response (#1841) and close stdio input before wait (#1838)",
            {"post_disposed": csharp_sse_post_response_disposed, "stdio_closed": csharp_stdio_input_closed_before_wait},
        )
    if cimd_public_client_token_auth_method != "none":
        return GuardVerdict(
            False,
            "PR-15",
            "MCP_CSHARP_CIMD_PUBLIC_CLIENT_AUTH_METHOD_INVALID",
            f"CIMD public client token-endpoint auth method {cimd_public_client_token_auth_method!r} != 'none' (#1845)",
            {"auth_method": cimd_public_client_token_auth_method},
        )
    if java_malformed_body_http_status != 400:
        return GuardVerdict(
            False,
            "PR-15",
            "MCP_JAVA_MALFORMED_BODY_MUST_RETURN_400",
            f"Malformed JSON request body returned HTTP {java_malformed_body_http_status} instead of 400 INVALID_REQUEST (#1168)",
            {"http_status": java_malformed_body_http_status},
        )
    if not _SEP986_TOOL_NAME_RE.match(kotlin_tool_name) or not kotlin_cancellation_exception_propagated:
        return GuardVerdict(
            False,
            "PR-15",
            "MCP_KOTLIN_SEP986_TOOL_NAME_OR_CANCELLATION_INVALID",
            f"Invalid SEP-986 tool name {kotlin_tool_name!r} or swallowed CancellationException (#695/#706)",
            {"tool_name": kotlin_tool_name},
        )
    return GuardVerdict(
        True,
        "PR-15",
        "MCP_CSHARP_JAVA_KOTLIN_GUARDS_VERIFIED",
        "MCP C# SSE POST disposal & CIMD auth=none, Java 400 malformed body, and Kotlin SEP-986 verified",
        {"tool_name": kotlin_tool_name, "java_status": java_malformed_body_http_status},
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/inspector#2687, #2688, #2689, #2693, #2695, #2711, #2729, #2741
# ---------------------------------------------------------------------------
def verify_mcp_inspector_modern_era_run_as_task_launcher_guard(
    *,
    protocol_era: str,
    run_as_task_toggle_visible: bool,
    launcher_prints_version_in_all_modes: bool,
    tui_esc_clears_filter_before_exit: bool,
    browser_opener_warning_single_line: bool,
) -> GuardVerdict:
    """Validate MCP Inspector hiding 'Run as task' on modern-era (2026-07-28) connections (#2687) and CLI/TUI guards."""
    if protocol_era == "2026-07-28" and run_as_task_toggle_visible:
        return GuardVerdict(
            False,
            "PR-16",
            "MCP_INSPECTOR_MODERN_ERA_RUN_AS_TASK_EXPOSED",
            "Under SEP-2663 (2026-07-28), task creation is server-directed; 'Run as task' must be hidden (#2687)",
            {"protocol_era": protocol_era, "run_as_task_toggle_visible": True},
        )
    if not (launcher_prints_version_in_all_modes and tui_esc_clears_filter_before_exit and browser_opener_warning_single_line):
        return GuardVerdict(
            False,
            "PR-16",
            "MCP_INSPECTOR_LAUNCHER_OR_TUI_UX_DRIFT",
            "Launcher --version/-V parity (#2695), TUI Esc filter clear (#2693), and 1-line opener warning (#2689) required",
            {"version_all_modes": launcher_prints_version_in_all_modes},
        )
    return GuardVerdict(
        True,
        "PR-16",
        "MCP_INSPECTOR_MODERN_TASK_AND_LAUNCHER_VERIFIED",
        "MCP Inspector SEP-2663 modern-era 'Run as task' suppression, launcher --version, and TUI Esc filter verified",
        {"protocol_era": protocol_era, "run_as_task_toggle_visible": run_as_task_toggle_visible},
    )
