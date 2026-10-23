"""Stage 198 deterministic guard module:
x402 Go V2 CAIP-2 Network Grammar & V1 Legacy Exemption (PR #3884), Non-Browser 402 JSON
Rejection Body & settlement_failed Propagation (PR #3882), Bazaar Declared-Input Method
Resolution & Schema Enum Narrowing (PR #3879), Go EVM Gas-Sponsoring Signer Capability &
Stellar Typed Simulation Errors / Rust SDK V1-V2 Primitives (PR #3871 / PR #3870 / PR #3787),
UCP Non-Empty anyOf Branches & Discriminator Pinning in required (PR #760), and MCP SEP-2694
Resumable Task Event Streams (PR #2694), SEP-2624 Trust-Boundary Interceptors (PR #2624),
SEP-2343 Remote Elicitation Auth Binding (PR #2343) & SEP-1933 Workload Identity Federation (PR #1933).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


GO_CAIP2_V2_REGEX = re.compile(r"^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
BASE64URL_NO_PAD_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
QUERY_METHODS = frozenset({"GET", "HEAD", "DELETE"})
WIF_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: Mapping[str, Any]


# ---------------------------------------------------------------------------
# 1. x402 Go V2 CAIP-2 Network Validation (PR #3884)
# ---------------------------------------------------------------------------

def validate_x402_go_v2_caip2_network_envelope(
    *,
    message_type: str,
    x402_version: int,
    network: str | None = None,
    accepted: Mapping[str, Any] | None = None,
    accepts: Sequence[Mapping[str, Any]] | None = None,
) -> GuardDecision:
    """Validate x402 Go SDK V2 CAIP-2 network syntax with V1 legacy exemption (PR #3884)."""
    if x402_version not in (1, 2):
        return GuardDecision(
            allowed=False,
            decision_code="X402_UNSUPPORTED_VERSION_BLOCKED",
            reason=f"Unsupported x402Version: {x402_version}",
            metadata={"x402_version": x402_version},
        )

    def _is_valid_v2_net(net_val: Any) -> bool:
        return isinstance(net_val, str) and bool(GO_CAIP2_V2_REGEX.match(net_val))

    if message_type == "requirements":
        if x402_version == 2 and not _is_valid_v2_net(network):
            return GuardDecision(
                allowed=False,
                decision_code="X402_GO_V2_MALFORMED_CAIP2_NETWORK_BLOCKED",
                reason=f"network {network!r} must be in CAIP-2 format (e.g., 'eip155:84532')",
                metadata={"network": network, "x402_version": x402_version},
            )
        return GuardDecision(
            allowed=True,
            decision_code="X402_GO_NETWORK_REQUIREMENTS_VERIFIED",
            reason="PaymentRequirements network conforms to versioned CAIP-2 rule.",
            metadata={"network": network, "x402_version": x402_version},
        )

    if message_type == "payload":
        if x402_version == 2:
            if not isinstance(accepted, Mapping):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_GO_V2_PAYLOAD_MISSING_ACCEPTED_BLOCKED",
                    reason="V2 PaymentPayload must include an accepted requirements object with CAIP-2 network.",
                    metadata={"x402_version": x402_version},
                )
            acc_net = accepted.get("network")
            if not _is_valid_v2_net(acc_net):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_GO_V2_MALFORMED_CAIP2_NETWORK_BLOCKED",
                    reason=f"accepted.network {acc_net!r} must be in CAIP-2 format (e.g., 'eip155:84532')",
                    metadata={"accepted_network": acc_net, "x402_version": x402_version},
                )
        return GuardDecision(
            allowed=True,
            decision_code="X402_GO_NETWORK_PAYLOAD_VERIFIED",
            reason="PaymentPayload network conforms to versioned CAIP-2 rule.",
            metadata={"x402_version": x402_version},
        )

    if message_type == "payment_required":
        if not isinstance(accepts, Sequence) or len(accepts) == 0:
            return GuardDecision(
                allowed=False,
                decision_code="X402_GO_EMPTY_ACCEPTS_BLOCKED",
                reason="PaymentRequired accepts[] must be non-empty.",
                metadata={"x402_version": x402_version},
            )
        if x402_version == 2:
            for idx, entry in enumerate(accepts):
                entry_net = entry.get("network") if isinstance(entry, Mapping) else None
                if not _is_valid_v2_net(entry_net):
                    return GuardDecision(
                        allowed=False,
                        decision_code="X402_GO_V2_MALFORMED_CAIP2_NETWORK_BLOCKED",
                        reason=f"accepts[{idx}].network {entry_net!r} must be in CAIP-2 format (e.g., 'eip155:84532')",
                        metadata={"index": idx, "network": entry_net, "x402_version": x402_version},
                    )
        return GuardDecision(
            allowed=True,
            decision_code="X402_GO_NETWORK_REQUIRED_VERIFIED",
            reason="PaymentRequired accepts[] networks conform to versioned CAIP-2 rule.",
            metadata={"x402_version": x402_version, "accepts_count": len(accepts)},
        )

    return GuardDecision(
        allowed=False,
        decision_code="X402_GO_UNKNOWN_MESSAGE_TYPE_BLOCKED",
        reason=f"Unknown message_type: {message_type}",
        metadata={"message_type": message_type},
    )


# ---------------------------------------------------------------------------
# 2. x402 Non-Browser 402 JSON Rejection Body & Bazaar Method Fit (PR #3882, #3879)
# ---------------------------------------------------------------------------

def validate_x402_go_402_json_error_body(
    *,
    is_browser_request: bool,
    has_custom_unpaid_body: bool,
    failure_stage: str,
    payment_required_error: str,
    response_status: int,
    response_headers: Mapping[str, str],
    response_body: Mapping[str, Any] | str,
) -> GuardDecision:
    """Validate x402 Go HTTP 402 JSON error body & settlement_failed propagation (PR #3882)."""
    if response_status != 402:
        return GuardDecision(
            allowed=False,
            decision_code="X402_NON_402_STATUS_BLOCKED",
            reason=f"Expected HTTP 402 status, got {response_status}",
            metadata={"response_status": response_status},
        )
    if response_headers.get("Cache-Control") != "no-store":
        return GuardDecision(
            allowed=False,
            decision_code="X402_MISSING_NO_STORE_HEADER_BLOCKED",
            reason="402 response must set Cache-Control: no-store.",
            metadata={"cache_control": response_headers.get("Cache-Control")},
        )
    if is_browser_request or has_custom_unpaid_body:
        return GuardDecision(
            allowed=True,
            decision_code="X402_BROWSER_OR_CUSTOM_402_BODY_VERIFIED",
            reason="Browser HTML paywall or custom unpaid body preserved.",
            metadata={"is_browser_request": is_browser_request},
        )
    if not isinstance(response_body, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="X402_NON_JSON_402_BODY_BLOCKED",
            reason="Non-browser 402 response body must be a JSON object.",
            metadata={},
        )

    if failure_stage == "settlement":
        if not response_headers.get("PAYMENT-RESPONSE"):
            return GuardDecision(
                allowed=False,
                decision_code="X402_SETTLEMENT_FAILURE_MISSING_PAYMENT_RESPONSE_HEADER_BLOCKED",
                reason="Settlement failure 402 must include PAYMENT-RESPONSE header.",
                metadata={},
            )
        if response_body.get("error") != "settlement_failed":
            return GuardDecision(
                allowed=False,
                decision_code="X402_SETTLEMENT_FAILURE_EMPTY_OR_WRONG_ERROR_BODY_BLOCKED",
                reason="Settlement failure 402 JSON body must be {'error': 'settlement_failed'}.",
                metadata={"actual_error": response_body.get("error")},
            )
        return GuardDecision(
            allowed=True,
            decision_code="X402_SETTLEMENT_FAILURE_402_JSON_VERIFIED",
            reason="Settlement failure 402 JSON body includes {'error': 'settlement_failed'} and PAYMENT-RESPONSE.",
            metadata={"error": "settlement_failed"},
        )

    if not response_headers.get("PAYMENT-REQUIRED"):
        return GuardDecision(
            allowed=False,
            decision_code="X402_VERIFY_FAILURE_MISSING_PAYMENT_REQUIRED_HEADER_BLOCKED",
            reason="Unpaid / verify-failure 402 must include PAYMENT-REQUIRED header.",
            metadata={},
        )
    expected_error = payment_required_error.strip()
    if expected_error:
        if response_body.get("error") != expected_error:
            return GuardDecision(
                allowed=False,
                decision_code="X402_402_JSON_REJECTION_REASON_MISSING_BLOCKED",
                reason=f"Expected 402 JSON body error {expected_error!r}, got {response_body.get('error')!r}",
                metadata={"expected_error": expected_error, "actual_error": response_body.get("error")},
            )
    return GuardDecision(
        allowed=True,
        decision_code="X402_402_JSON_REJECTION_REASON_VERIFIED",
        reason="Non-browser 402 JSON body exposes paymentRequired.Error.",
        metadata={"error": expected_error},
    )


def validate_x402_bazaar_declared_method_enrichment(
    *,
    input_kind: str,
    probe_method: str,
    advertised_method: str,
    schema_method_enum: Sequence[str],
) -> GuardDecision:
    """Validate x402 Go Bazaar EnrichDeclaration method resolution & schema enum narrowing (PR #3879)."""
    upper_probe = probe_method.strip().upper()
    if input_kind == "body":
        expected_method = upper_probe if upper_probe in BODY_METHODS else "POST"
    elif input_kind == "query":
        expected_method = upper_probe if upper_probe in QUERY_METHODS else "GET"
    else:
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_UNKNOWN_INPUT_KIND_BLOCKED",
            reason=f"Unknown Bazaar input_kind: {input_kind}",
            metadata={"input_kind": input_kind},
        )

    if advertised_method != expected_method:
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_CONFLICTING_PROBE_METHOD_ADVERTISED_BLOCKED",
            reason=(
                f"Probe method {upper_probe} conflicts with {input_kind} input; "
                f"expected advertised method {expected_method}, got {advertised_method}"
            ),
            metadata={
                "input_kind": input_kind,
                "probe_method": upper_probe,
                "expected_method": expected_method,
                "advertised_method": advertised_method,
            },
        )
    if list(schema_method_enum) != [expected_method]:
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_SCHEMA_METHOD_ENUM_NOT_NARROWED_BLOCKED",
            reason=f"Schema method enum must be narrowed to [{expected_method!r}], got {list(schema_method_enum)}",
            metadata={"expected_enum": [expected_method], "actual_enum": list(schema_method_enum)},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_BAZAAR_DECLARED_METHOD_ENRICHMENT_VERIFIED",
        reason="Bazaar discovery enrichment advertises input-compatible HTTP method and narrows schema enum.",
        metadata={"resolved_method": expected_method, "input_kind": input_kind},
    )


# ---------------------------------------------------------------------------
# 3. x402 Go Gas-Sponsoring Signer, Stellar Simulation & Rust SDK (PR #3871, #3870, #3787)
# ---------------------------------------------------------------------------

def validate_x402_gas_sponsoring_stellar_sim_and_rust_primitives(
    *,
    sponsoring_mode: str,
    signer_can_read_contract: bool,
    signer_can_sign_tx: bool,
    extension_skipped_with_single_warning: bool,
    stellar_sim_status: str,
    stellar_error_class: str,
    stellar_error_has_account_and_asset: bool,
    rust_header_b64: str,
    rust_signature_hex: str,
    rust_valid_after: int,
    rust_valid_before: int,
    now_epoch: int,
) -> GuardDecision:
    """Validate Go gas-sponsoring signer capabilities (#3871), Stellar simulation errors (#3870), and Rust SDK (#3787)."""
    if sponsoring_mode == "eip2612" and not signer_can_read_contract:
        if not extension_skipped_with_single_warning:
            return GuardDecision(
                allowed=False,
                decision_code="X402_GO_EIP2612_SIGNER_MISSING_READ_CONTRACT_NOT_SKIPPED_BLOCKED",
                reason="EIP-2612 sponsoring without read-contract capability must skip extension and log once per network.",
                metadata={"sponsoring_mode": sponsoring_mode},
            )
    if sponsoring_mode == "erc20_approval" and not signer_can_sign_tx:
        if not extension_skipped_with_single_warning:
            return GuardDecision(
                allowed=False,
                decision_code="X402_GO_ERC20_APPROVAL_SIGNER_MISSING_TX_SIGN_NOT_SKIPPED_BLOCKED",
                reason="ERC-20 approval sponsoring without tx-signing capability must skip extension and log once per network.",
                metadata={"sponsoring_mode": sponsoring_mode},
            )

    if stellar_sim_status != "ok":
        expected_err = {
            "trustline_missing": "TrustlineMissingError",
            "insufficient_balance": "InsufficientBalanceError",
            "rpc_error": "SimulationFailedError",
        }.get(stellar_sim_status)
        if stellar_error_class != expected_err or (
            stellar_sim_status in ("trustline_missing", "insufficient_balance")
            and not stellar_error_has_account_and_asset
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_STELLAR_UNTYPED_OR_UNCAUGHT_SIMULATION_FAILURE_BLOCKED",
                reason=(
                    f"Stellar pre-sign simulation status {stellar_sim_status!r} must raise typed "
                    f"{expected_err} with account and asset fields before signing."
                ),
                metadata={"stellar_sim_status": stellar_sim_status, "stellar_error_class": stellar_error_class},
            )

    if not BASE64URL_NO_PAD_REGEX.match(rust_header_b64):
        return GuardDecision(
            allowed=False,
            decision_code="X402_RUST_HEADER_NOT_URL_SAFE_NO_PAD_BLOCKED",
            reason="Rust X402Header must use URL_SAFE_NO_PAD Base64 without '+', '/', or '='.",
            metadata={"rust_header_b64": rust_header_b64},
        )
    if not (
        rust_signature_hex.startswith("0x")
        and len(rust_signature_hex) == 132
        and rust_valid_after == now_epoch - 60
        and rust_valid_before > now_epoch
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_RUST_EIP3009_SIGNATURE_OR_WINDOW_INVALID_BLOCKED",
            reason="Rust EIP-3009 signature must be 65-byte 0x hex (132 chars) with validAfter == now - 60 < validBefore.",
            metadata={"sig_len": len(rust_signature_hex), "valid_after": rust_valid_after, "valid_before": rust_valid_before},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_GAS_STELLAR_SIM_AND_RUST_PRIMITIVES_VERIFIED",
        reason="Go gas-sponsoring capability check, Stellar typed simulation handling, and Rust EIP-3009 primitives verified.",
        metadata={"sponsoring_mode": sponsoring_mode, "stellar_sim_status": stellar_sim_status},
    )


# ---------------------------------------------------------------------------
# 4. UCP Non-Empty anyOf Branch & Required Discriminator Pinning (PR #760)
# ---------------------------------------------------------------------------

def validate_ucp_anyof_non_empty_branch_and_discriminator(
    *,
    anyof_branches: Sequence[Mapping[str, Any]],
    discriminator_field: str,
    submitted_credential: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP request_constraints non-empty anyOf branches & required discriminator pinning (PR #760)."""
    if not anyof_branches:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ANYOF_EMPTY_ARRAY_BLOCKED",
            reason="anyOf must be a non-empty array of non-empty Object Constraints.",
            metadata={},
        )

    for idx, branch in enumerate(anyof_branches):
        if not isinstance(branch, Mapping) or len(branch) == 0:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ANYOF_EMPTY_BRANCH_NEUTRALIZATION_BLOCKED",
                reason=f"anyOf[{idx}] is empty ({{}}); an empty branch matches every object and neutralizes alternation.",
                metadata={"branch_index": idx},
            )
        if "path" in branch:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ANYOF_BRANCH_PATH_FORBIDDEN_BLOCKED",
                reason=f"anyOf[{idx}] cannot carry 'path'; branches evaluate against the same selected object.",
                metadata={"branch_index": idx},
            )
        props = branch.get("properties", {})
        req = branch.get("required", [])
        if isinstance(props, Mapping) and discriminator_field in props:
            if not isinstance(req, Sequence) or discriminator_field not in req:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_ANYOF_DISCRIMINATOR_NOT_IN_REQUIRED_BLOCKED",
                    reason=(
                        f"anyOf[{idx}] pins {discriminator_field!r} in properties but omits it from required, "
                        "allowing objects that omit the discriminator to match."
                    ),
                    metadata={"branch_index": idx, "discriminator_field": discriminator_field},
                )

    def _matches_branch(obj: Mapping[str, Any], branch: Mapping[str, Any]) -> bool:
        req_fields = branch.get("required", [])
        for rf in req_fields:
            if rf not in obj or obj[rf] in (None, ""):
                return False
        props = branch.get("properties", {})
        if isinstance(props, Mapping):
            for prop_name, constraint in props.items():
                if prop_name in obj and isinstance(constraint, Mapping):
                    if "const" in constraint and obj[prop_name] != constraint["const"]:
                        return False
                    if "enum" in constraint and obj[prop_name] not in constraint["enum"]:
                        return False
        return True

    matched_indices = [i for i, b in enumerate(anyof_branches) if _matches_branch(submitted_credential, b)]
    if not matched_indices:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SUBMITTED_CREDENTIAL_FAILS_CLOSED_ANYOF_BRANCHES_BLOCKED",
            reason="Submitted credential satisfies none of the closed anyOf branches.",
            metadata={"credential_type": submitted_credential.get(discriminator_field)},
        )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_ANYOF_NON_EMPTY_DISCRIMINATOR_BRANCHES_VERIFIED",
        reason="UCP anyOf branches are non-empty, pin discriminator in required, and validate submitted credential.",
        metadata={"matched_branches": matched_indices},
    )


# ---------------------------------------------------------------------------
# 5. MCP SEP-2694 Resumable Task Event Streams (PR #2694)
# ---------------------------------------------------------------------------

def validate_mcp_sep2694_resumable_task_event_stream(
    *,
    task_id: str,
    active_streams_on_connection: Sequence[str],
    after_cursor: int | None,
    earliest_retained_seq: int,
    latest_retained_seq: int,
    emitted_events: Sequence[Mapping[str, Any]],
) -> GuardDecision:
    """Validate MCP SEP-2694 tasks/stream & notifications/tasks/event resumable delivery (PR #2694)."""
    if task_id in active_streams_on_connection:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2694_DUPLICATE_ACTIVE_STREAM_ON_CONNECTION_BLOCKED",
            reason="At most one active tasks/stream request per task per connection is allowed (-32602).",
            metadata={"task_id": task_id, "jsonrpc_code": -32602},
        )
    if after_cursor is not None and (not isinstance(after_cursor, int) or isinstance(after_cursor, bool) or after_cursor < 0):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2694_NEGATIVE_OR_INVALID_AFTER_CURSOR_BLOCKED",
            reason="tasks/stream 'after' parameter must be a non-negative integer (-32602).",
            metadata={"after_cursor": after_cursor, "jsonrpc_code": -32602},
        )
    if after_cursor is not None and after_cursor + 1 < earliest_retained_seq:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2694_EVENTS_GONE_CURSOR_TOO_OLD_BLOCKED",
            reason=f"Events after seq {after_cursor} are no longer retained; return -32010 events_gone.",
            metadata={
                "jsonrpc_code": -32010,
                "reason": "events_gone",
                "task_id": task_id,
                "earliest_seq": earliest_retained_seq,
            },
        )

    expected_seq = earliest_retained_seq if after_cursor is None else after_cursor + 1
    for idx, ev in enumerate(emitted_events):
        seq = ev.get("seq")
        ev_task = ev.get("taskId")
        ev_type = str(ev.get("type", ""))
        payload = ev.get("payload")
        meta = ev.get("_meta", {})
        related_task = meta.get("io.modelcontextprotocol/related-task", {}) if isinstance(meta, Mapping) else {}

        if seq != expected_seq:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2694_NON_CONTIGUOUS_EVENT_SEQUENCE_BLOCKED",
                reason=f"Event[{idx}] seq {seq} does not match expected contiguous seq {expected_seq}.",
                metadata={"expected_seq": expected_seq, "actual_seq": seq},
            )
        expected_seq += 1

        if ev_task != task_id or not isinstance(related_task, Mapping) or related_task.get("taskId") != task_id:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2694_MISSING_OR_MISMATCHED_RELATED_TASK_META_BLOCKED",
                reason="notifications/tasks/event must include _meta['io.modelcontextprotocol/related-task'].taskId == params.taskId.",
                metadata={"event_task_id": ev_task, "related_task": related_task},
            )
        if "." not in ev_type or ev_type.startswith(".") or ev_type.endswith("."):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2694_UNPREFIXED_EVENT_TYPE_BLOCKED",
                reason=f"Implementation-defined task event type {ev_type!r} must use a vendor reverse-DNS prefix.",
                metadata={"event_type": ev_type},
            )
        if not isinstance(payload, Mapping):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2694_NON_OBJECT_EVENT_PAYLOAD_BLOCKED",
                reason="TaskEvent payload must be a JSON object.",
                metadata={"seq": seq},
            )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_SEP2694_RESUMABLE_TASK_STREAM_VERIFIED",
        reason="MCP SEP-2694 tasks/stream cursor, contiguous sequence, vendor prefix, and related-task metadata verified.",
        metadata={"task_id": task_id, "delivered_count": len(emitted_events), "latest_retained_seq": latest_retained_seq},
    )


# ---------------------------------------------------------------------------
# 6. MCP SEP-2624 Interceptors, SEP-2343 Elicitation Auth & SEP-1933 WIF (PR #2624, #2343, #1933)
# ---------------------------------------------------------------------------

def validate_mcp_sep2624_interceptor_trust_boundary_pipeline(
    *,
    direction: str,
    executed_stages: Sequence[str],
    mutators: Sequence[Mapping[str, Any]],
    validators: Sequence[Mapping[str, Any]],
    atomic_mutation_applied: bool,
) -> GuardDecision:
    """Validate MCP SEP-2624 trust-boundary interceptor execution order, priority ordering & failOpen (PR #2624)."""
    if direction == "sending":
        expected_stages = ["mutate", "validate", "send"]
    elif direction == "receiving":
        expected_stages = ["validate", "mutate", "process"]
    else:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2624_UNKNOWN_DIRECTION_BLOCKED",
            reason=f"Unknown interceptor direction: {direction}",
            metadata={"direction": direction},
        )

    if list(executed_stages) != expected_stages:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2624_TRUST_BOUNDARY_STAGE_ORDER_VIOLATION_BLOCKED",
            reason=f"Direction {direction!r} requires stage order {expected_stages}, got {list(executed_stages)}",
            metadata={"direction": direction, "expected": expected_stages, "actual": list(executed_stages)},
        )

    sort_keys = [
        (int(m.get("priority_hint", 0)), str(m.get("name", "")))
        for m in mutators
    ]
    if sort_keys != sorted(sort_keys):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP2624_MUTATOR_PRIORITY_ORDER_VIOLATION_BLOCKED",
            reason="Mutators must execute sequentially ordered by (priorityHint, alphabetical name).",
            metadata={"sort_keys": sort_keys},
        )

    for m in mutators:
        mode = m.get("mode", "active")
        fail_open = bool(m.get("fail_open", False))
        status = m.get("status", "ok")
        if status in ("error", "timeout") and mode == "active" and not fail_open:
            if atomic_mutation_applied:
                return GuardDecision(
                    allowed=False,
                    decision_code="MCP_SEP2624_NON_ATOMIC_OR_FAIL_CLOSED_MUTATION_BYPASS_BLOCKED",
                    reason=f"Active mutator {m.get('name')!r} failed ({status}) with failOpen=false; chain must abort atomically.",
                    metadata={"mutator": m.get("name"), "status": status},
                )
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2624_ACTIVE_MUTATOR_FAILURE_HALTED_BLOCKED",
                reason=f"Active mutator {m.get('name')!r} failed ({status}) with failOpen=false.",
                metadata={"mutator": m.get("name"), "status": status, "jsonrpc_code": -32000 if status == "timeout" else -32603},
            )

    for v in validators:
        mode = v.get("mode", "active")
        fail_open = bool(v.get("fail_open", False))
        status = v.get("status", "ok")
        valid = bool(v.get("valid", True))
        severity = str(v.get("severity", "info"))
        if mode == "active":
            if status in ("error", "timeout") and not fail_open:
                return GuardDecision(
                    allowed=False,
                    decision_code="MCP_SEP2624_VALIDATOR_CRASH_OR_TIMEOUT_FAIL_CLOSED_BLOCKED",
                    reason=f"Active validator {v.get('name')!r} failed ({status}) with failOpen=false.",
                    metadata={"validator": v.get("name"), "status": status},
                )
            if not valid and severity == "error":
                return GuardDecision(
                    allowed=False,
                    decision_code="MCP_SEP2624_VALIDATION_ERROR_SEVERITY_BLOCKED",
                    reason=f"Active validator {v.get('name')!r} returned valid=false with severity='error'.",
                    metadata={"validator": v.get("name"), "severity": severity},
                )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_SEP2624_INTERCEPTOR_PIPELINE_VERIFIED",
        reason="MCP SEP-2624 trust-boundary stage order, mutator priority sorting, and validator gating verified.",
        metadata={"direction": direction, "mutators_count": len(mutators), "validators_count": len(validators)},
    )


def validate_mcp_sep2343_elicitation_auth_and_sep1933_wif(
    *,
    is_remote_server: bool,
    elicitation_requested: bool,
    mcp_authorization_authenticated: bool,
    bound_to_user_sub_and_client_id: bool,
    bound_to_session_id_only: bool,
    wif_grant_type: str,
    wif_issuer: str,
    trusted_issuers: Sequence[str],
    oidc_jwks_uri: str,
    jwt_ttl_seconds: int,
    tenant_key_isolated: bool,
    tenant_claim_issuer_controlled: bool,
    target_resource_matches_server: bool,
) -> GuardDecision:
    """Validate MCP SEP-2343 remote elicitation auth binding (#2343) and SEP-1933 Workload Identity Federation (#1933)."""
    if elicitation_requested and is_remote_server:
        if not mcp_authorization_authenticated or not bound_to_user_sub_and_client_id or bound_to_session_id_only:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SEP2343_REMOTE_ELICITATION_WITHOUT_AUTH_USER_BINDING_BLOCKED",
                reason=(
                    "Remote MCP servers implementing elicitation must authenticate user identity via MCP "
                    "authorization and bind state to (client_id, user sub), never session ID alone."
                ),
                metadata={
                    "mcp_authorization_authenticated": mcp_authorization_authenticated,
                    "bound_to_session_id_only": bound_to_session_id_only,
                },
            )

    if wif_grant_type != WIF_GRANT_TYPE:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP1933_INVALID_GRANT_TYPE_BLOCKED",
            reason=f"WIF token request must use grant_type {WIF_GRANT_TYPE!r}.",
            metadata={"wif_grant_type": wif_grant_type},
        )
    if not wif_issuer.startswith("https://") or wif_issuer not in trusted_issuers:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP1933_UNTRUSTED_OR_INSECURE_ISSUER_BLOCKED",
            reason=f"Workload JWT issuer {wif_issuer!r} must use https:// and belong to trusted_issuers.",
            metadata={"wif_issuer": wif_issuer},
        )
    if not oidc_jwks_uri.startswith("https://"):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP1933_NON_HTTPS_JWKS_URI_BLOCKED",
            reason=f"OIDC Discovery jwks_uri {oidc_jwks_uri!r} must use https://.",
            metadata={"oidc_jwks_uri": oidc_jwks_uri},
        )
    if jwt_ttl_seconds <= 0 or jwt_ttl_seconds > 3600:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP1933_EXCESSIVE_WORKLOAD_JWT_TTL_BLOCKED",
            reason=f"Workload JWT lifetime ({jwt_ttl_seconds}s) must be short-lived (1..3600s).",
            metadata={"jwt_ttl_seconds": jwt_ttl_seconds},
        )
    if not tenant_key_isolated or not tenant_claim_issuer_controlled or not target_resource_matches_server:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SEP1933_MULTI_TENANT_OR_RESOURCE_AUDIENCE_VIOLATION_BLOCKED",
            reason="WIF grant must enforce per-tenant issuing key/issuer-controlled claim isolation and canonical MCP server resource binding.",
            metadata={
                "tenant_key_isolated": tenant_key_isolated,
                "tenant_claim_issuer_controlled": tenant_claim_issuer_controlled,
                "target_resource_matches_server": target_resource_matches_server,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_SEP2343_AND_SEP1933_WIF_VERIFIED",
        reason="Remote elicitation user-identity binding (SEP-2343) and Workload Identity Federation (SEP-1933) verified.",
        metadata={"wif_issuer": wif_issuer, "jwt_ttl_seconds": jwt_ttl_seconds},
    )
