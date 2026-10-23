"""Deterministic guard for Stage 190:
1. x402 Python High-s EIP-3009 EOA vs. Deployed Smart-Wallet Gate (PR #3912),
   ECDSA yParity (0/1 -> 27/28) Recovery Byte Normalization (PR #3583),
   upto Permit2 Settle-Time Metered Simulation (PR #3769), and
   Gate Hook Fail-Closed Fixed Client Error (PR #3702).
2. x402 exact on TRON Binding (PR #2076): decimal CAIP-2 network IDs,
   32-bit masked TIP-712 chainId, Base58Check 0x41 -> 20-byte 0x hex normalization,
   pinned x402ExactPermit2Proxy runtime hash, and two-stage expiry timing (B vs 0).
3. x402 SVM Cooperative seal & refund Durable Payout Callback Recovery (PR #3606):
   durable result persistence before callback, extra.paidToReceiver vs refund amount,
   in-flight coalescing, and settlement_pending retry without rebroadcasting.
4. MCP SEP-2487 Opaque execution.requirements Preconditions (PR #2487) and
   SEP-2028 Group-Based _meta to HTTP Header Forwarding (PR #2028).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_HALF_N = SECP256K1_N // 2

ALLOWED_TRON_DECIMAL_NETWORKS: dict[str, int] = {
    "tron:728126428": 728126428,
    "tron:3448148188": 3448148188,
    "tron:2494104990": 2494104990,
}

PINNED_TRON_PERMIT2_PROXY_COMMIT = "19b19d5e16e044b4557c4fa70089118f8c66188d"
PINNED_TRON_PERMIT2_PROXY_RUNTIME_BYTES = 3593
PINNED_TRON_PERMIT2_PROXY_MAINNET_SHA256 = (
    "a4e90eed8aeb8d7fa165980da56d6533b7fd843f5a2d92f5843ce15c55a29fb0"
)
MIN_TRON_SAFETY_MARGIN_SECONDS = 6


@dataclass(frozen=True)
class EvmSignatureUptoHookDecision:
    allowed: bool
    reason: str
    normalized_v: int
    simulated_amount: int
    client_error_message: str


@dataclass(frozen=True)
class TronExactBindingDecision:
    allowed: bool
    reason: str
    tip712_chain_id: int
    normalized_hex_address: str
    required_min_expiry: int


@dataclass(frozen=True)
class SvmSealCallbackRecoveryDecision:
    allowed: bool
    reason: str
    broadcast_count: int
    callback_invocations: int
    response_amount: str
    callback_amount: str
    recorded_marker_set: bool


@dataclass(frozen=True)
class McpRequirementsAndMetaForwardingDecision:
    allowed: bool
    reason: str
    client_may_filter_tool: bool
    forwarded_headers: dict[str, str]


def validate_evm_signature_upto_and_hook_guard(
    *,
    signature_len: int,
    s_value: int,
    payer_code_len: int,
    raw_recovery_byte: int,
    permitted_amount: int,
    settlement_amount: int,
    payer_balance: int,
    simulate_in_settle: bool = True,
    gate_hook_threw: bool = False,
    gate_hook_exception_detail: str = "",
    exposed_client_error_message: str = "extension hook failed",
) -> EvmSignatureUptoHookDecision:
    """Validate x402 PRs #3912, #3583, #3769, and #3702."""
    if gate_hook_threw:
        if (
            exposed_client_error_message != "extension hook failed"
            or (
                gate_hook_exception_detail
                and gate_hook_exception_detail in exposed_client_error_message
            )
        ):
            return EvmSignatureUptoHookDecision(
                allowed=False,
                reason="gate_hook_internal_error_leaked",
                normalized_v=0,
                simulated_amount=0,
                client_error_message=exposed_client_error_message,
            )
        return EvmSignatureUptoHookDecision(
            allowed=False,
            reason="extension_hook_error",
            normalized_v=0,
            simulated_amount=0,
            client_error_message="extension hook failed",
        )

    # PR #3912: 65-byte high-s is rejected ONLY for plain EOAs (payer_code_len == 0).
    # Deployed ERC-1271 smart wallets (payer_code_len > 0) or non-65-byte ERC-6492 signatures pass.
    if signature_len == 65 and payer_code_len == 0:
        if s_value <= 0 or s_value > SECP256K1_HALF_N:
            return EvmSignatureUptoHookDecision(
                allowed=False,
                reason="invalid_exact_evm_non_canonical_signature",
                normalized_v=0,
                simulated_amount=0,
                client_error_message="",
            )

    # PR #3583: Normalize yParity 0/1 to 27/28 for 65-byte ECDSA signatures.
    normalized_v = raw_recovery_byte
    if signature_len == 65 and payer_code_len == 0:
        if raw_recovery_byte in (0, 1):
            normalized_v = raw_recovery_byte + 27
        elif raw_recovery_byte not in (27, 28):
            return EvmSignatureUptoHookDecision(
                allowed=False,
                reason="invalid_ecdsa_recovery_byte",
                normalized_v=raw_recovery_byte,
                simulated_amount=0,
                client_error_message="",
            )

    # PR #3769: upto settle checks settlementAmount <= permittedAmount before re-verify,
    # skips simulation when settlementAmount == 0, and simulates with settlementAmount.
    if settlement_amount < 0 or permitted_amount <= 0:
        return EvmSignatureUptoHookDecision(
            allowed=False,
            reason="invalid_upto_amount",
            normalized_v=normalized_v,
            simulated_amount=0,
            client_error_message="",
        )
    if settlement_amount > permitted_amount:
        return EvmSignatureUptoHookDecision(
            allowed=False,
            reason="upto_settlement_exceeds_permitted_amount",
            normalized_v=normalized_v,
            simulated_amount=0,
            client_error_message="",
        )

    should_simulate = simulate_in_settle and settlement_amount > 0
    simulated_amount = settlement_amount if should_simulate else 0
    if should_simulate and payer_balance < simulated_amount:
        return EvmSignatureUptoHookDecision(
            allowed=False,
            reason="upto_simulation_insufficient_balance_for_settlement_amount",
            normalized_v=normalized_v,
            simulated_amount=simulated_amount,
            client_error_message="",
        )

    return EvmSignatureUptoHookDecision(
        allowed=True,
        reason="ok",
        normalized_v=normalized_v,
        simulated_amount=simulated_amount,
        client_error_message="",
    )


def validate_tron_exact_binding_guard(
    *,
    network: str,
    provided_tip712_chain_id: int,
    tron_payload_hex: str,
    provided_tip712_address: str,
    transfer_method: str,
    proxy_commit: str = PINNED_TRON_PERMIT2_PROXY_COMMIT,
    proxy_runtime_bytes: int = PINNED_TRON_PERMIT2_PROXY_RUNTIME_BYTES,
    proxy_runtime_sha256: str = PINNED_TRON_PERMIT2_PROXY_MAINNET_SHA256,
    s_value: int = 1,
    stage: str = "verify",
    now_seconds: int = 1_700_000_000,
    expiry_seconds: int = 1_700_000_120,
    settlement_S: int = 12,
    business_B: int = 20,
    safety_M: int = 6,
) -> TronExactBindingDecision:
    """Validate x402 exact on TRON binding (PR #2076)."""
    if network not in ALLOWED_TRON_DECIMAL_NETWORKS:
        return TronExactBindingDecision(
            allowed=False,
            reason="invalid_tron_caip2_network",
            tip712_chain_id=0,
            normalized_hex_address="",
            required_min_expiry=0,
        )

    expected_chain_id = ALLOWED_TRON_DECIMAL_NETWORKS[network] & 0xFFFFFFFF
    if provided_tip712_chain_id != expected_chain_id:
        return TronExactBindingDecision(
            allowed=False,
            reason="tron_tip712_chain_id_mismatch",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address="",
            required_min_expiry=0,
        )

    cleaned_payload = tron_payload_hex.lower().removeprefix("0x")
    if len(cleaned_payload) != 42 or not cleaned_payload.startswith("41"):
        return TronExactBindingDecision(
            allowed=False,
            reason="invalid_tron_0x41_address_payload",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address="",
            required_min_expiry=0,
        )
    normalized_hex = "0x" + cleaned_payload[2:]
    if provided_tip712_address.lower() != normalized_hex:
        return TronExactBindingDecision(
            allowed=False,
            reason="tron_tip712_address_normalization_mismatch",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address=normalized_hex,
            required_min_expiry=0,
        )

    if transfer_method not in ("tip3009", "permit2"):
        return TronExactBindingDecision(
            allowed=False,
            reason="unsupported_tron_transfer_method",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address=normalized_hex,
            required_min_expiry=0,
        )

    if transfer_method == "permit2":
        if (
            proxy_commit != PINNED_TRON_PERMIT2_PROXY_COMMIT
            or proxy_runtime_bytes != PINNED_TRON_PERMIT2_PROXY_RUNTIME_BYTES
            or proxy_runtime_sha256 != PINNED_TRON_PERMIT2_PROXY_MAINNET_SHA256
        ):
            return TronExactBindingDecision(
                allowed=False,
                reason="untrusted_tron_permit2_proxy_bytecode",
                tip712_chain_id=expected_chain_id,
                normalized_hex_address=normalized_hex,
                required_min_expiry=0,
            )

    if s_value <= 0 or s_value > SECP256K1_HALF_N:
        return TronExactBindingDecision(
            allowed=False,
            reason="tron_non_canonical_high_s_signature",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address=normalized_hex,
            required_min_expiry=0,
        )

    if safety_M < MIN_TRON_SAFETY_MARGIN_SECONDS:
        return TronExactBindingDecision(
            allowed=False,
            reason="tron_safety_margin_below_minimum",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address=normalized_hex,
            required_min_expiry=0,
        )

    effective_B = business_B if stage == "verify" else 0
    required_min_expiry = now_seconds + settlement_S + effective_B + safety_M
    if expiry_seconds <= required_min_expiry:
        return TronExactBindingDecision(
            allowed=False,
            reason="tron_authorization_expiry_buffer_insufficient",
            tip712_chain_id=expected_chain_id,
            normalized_hex_address=normalized_hex,
            required_min_expiry=required_min_expiry,
        )

    return TronExactBindingDecision(
        allowed=True,
        reason="ok",
        tip712_chain_id=expected_chain_id,
        normalized_hex_address=normalized_hex,
        required_min_expiry=required_min_expiry,
    )


def validate_svm_seal_callback_recovery_guard(
    *,
    intent: str,
    deposit_amount: int,
    already_claimed_amount: int,
    cumulative_amount: int,
    durable_result_present: bool,
    durable_paid_to_receiver_present: bool,
    already_recorded: bool,
    in_flight_pass_active: bool,
    callback_fails_first_attempt: bool,
    retry_after_failure: bool,
) -> SvmSealCallbackRecoveryDecision:
    """Validate x402 SVM seal/refund payout callback recovery and coalescing (PR #3606)."""
    if intent not in ("seal", "refund"):
        return SvmSealCallbackRecoveryDecision(
            allowed=False,
            reason="invalid_close_intent",
            broadcast_count=0,
            callback_invocations=0,
            response_amount="0",
            callback_amount="0",
            recorded_marker_set=False,
        )

    if cumulative_amount < already_claimed_amount or cumulative_amount > deposit_amount:
        return SvmSealCallbackRecoveryDecision(
            allowed=False,
            reason="invalid_cumulative_voucher_bounds",
            broadcast_count=0,
            callback_invocations=0,
            response_amount="0",
            callback_amount="0",
            recorded_marker_set=False,
        )

    paid_to_receiver = str(cumulative_amount - already_claimed_amount)
    response_amount = (
        str(deposit_amount - cumulative_amount) if intent == "refund" else paid_to_receiver
    )

    if intent == "refund" and durable_result_present and not durable_paid_to_receiver_present:
        return SvmSealCallbackRecoveryDecision(
            allowed=False,
            reason="durable_refund_missing_paid_to_receiver",
            broadcast_count=0,
            callback_invocations=0,
            response_amount=response_amount,
            callback_amount="0",
            recorded_marker_set=False,
        )

    broadcast_count = 0 if durable_result_present else 1

    if already_recorded:
        return SvmSealCallbackRecoveryDecision(
            allowed=True,
            reason="ok_idempotent_replay_without_rebroadcast",
            broadcast_count=0,
            callback_invocations=0,
            response_amount=response_amount,
            callback_amount=paid_to_receiver,
            recorded_marker_set=True,
        )

    if in_flight_pass_active:
        return SvmSealCallbackRecoveryDecision(
            allowed=True,
            reason="ok_coalesced_in_flight_accounting",
            broadcast_count=broadcast_count,
            callback_invocations=1,
            response_amount=response_amount,
            callback_amount=paid_to_receiver,
            recorded_marker_set=not callback_fails_first_attempt,
        )

    if callback_fails_first_attempt and not retry_after_failure:
        return SvmSealCallbackRecoveryDecision(
            allowed=False,
            reason="settlement_pending",
            broadcast_count=broadcast_count,
            callback_invocations=1,
            response_amount=response_amount,
            callback_amount=paid_to_receiver,
            recorded_marker_set=False,
        )

    callback_invocations = 2 if (callback_fails_first_attempt and retry_after_failure) else 1
    return SvmSealCallbackRecoveryDecision(
        allowed=True,
        reason="ok",
        broadcast_count=1,
        callback_invocations=callback_invocations,
        response_amount=response_amount,
        callback_amount=paid_to_receiver,
        recorded_marker_set=True,
    )


def _is_valid_ascii_meta_value(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 256:
        return False
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code > 0x7E:
            return False
    return True


def _is_valid_w3c_traceparent(value: str) -> bool:
    parts = value.split("-")
    if len(parts) != 4:
        return False
    version, trace_id, parent_id, flags = parts
    if len(version) != 2 or len(trace_id) != 32 or len(parent_id) != 16 or len(flags) != 2:
        return False
    try:
        int(version, 16)
        trace_int = int(trace_id, 16)
        parent_int = int(parent_id, 16)
        int(flags, 16)
    except ValueError:
        return False
    return trace_int != 0 and parent_int != 0


def validate_mcp_requirements_and_meta_forwarding_guard(
    *,
    declared_requirements: Sequence[str],
    server_satisfied_requirements: Sequence[str],
    client_known_requirements: Mapping[str, bool],
    client_attempted_equivalence_inference: bool = False,
    meta_fields: Mapping[str, object] | None = None,
    existing_outbound_headers: Mapping[str, str] | None = None,
    trace_context_policy: str = "clear-and-use-meta",
    baggage_policy: str = "prefer-meta",
    custom_groups: Mapping[str, Mapping[str, object]] | None = None,
) -> McpRequirementsAndMetaForwardingDecision:
    """Validate MCP SEP-2487 execution.requirements & SEP-2028 _meta header forwarding."""
    if client_attempted_equivalence_inference:
        return McpRequirementsAndMetaForwardingDecision(
            allowed=False,
            reason="sep2487_client_inferred_requirement_equivalence",
            client_may_filter_tool=False,
            forwarded_headers={},
        )

    all_known_to_client = all(req in client_known_requirements for req in declared_requirements)
    any_known_unsatisfied = any(
        (req in client_known_requirements and not client_known_requirements[req])
        for req in declared_requirements
    )
    client_may_filter_tool = bool(declared_requirements) and (
        all_known_to_client or any_known_unsatisfied
    )

    server_satisfied_set = set(server_satisfied_requirements)
    unmet_on_server = [req for req in declared_requirements if req not in server_satisfied_set]
    if unmet_on_server:
        return McpRequirementsAndMetaForwardingDecision(
            allowed=False,
            reason=f"sep2487_unmet_requirements:{','.join(unmet_on_server)}",
            client_may_filter_tool=client_may_filter_tool,
            forwarded_headers={},
        )

    # SEP-2028 4-stage pipeline:
    # 1. Validate _meta values (visible ASCII + space, <= 256 chars, total <= 8KB)
    meta = dict(meta_fields or {})
    total_bytes = sum(len(str(k)) + len(str(v)) for k, v in meta.items())
    if total_bytes > 8192:
        meta = {}

    validated_meta: dict[str, str] = {}
    for k, v in meta.items():
        if _is_valid_ascii_meta_value(v):
            validated_meta[k.lower()] = str(v)

    # 2. Per-header validation (e.g., W3C traceparent format)
    if "traceparent" in validated_meta and not _is_valid_w3c_traceparent(
        validated_meta["traceparent"]
    ):
        del validated_meta["traceparent"]

    final_headers: dict[str, str] = {
        k.lower(): v for k, v in (existing_outbound_headers or {}).items()
    }

    groups: dict[str, dict[str, object]] = {
        "trace-context": {
            "headers": ["traceparent", "tracestate"],
            "policy": trace_context_policy,
            "required": ["traceparent"],
        },
        "baggage": {
            "headers": ["baggage"],
            "policy": baggage_policy,
            "required": [],
        },
    }
    if custom_groups:
        for group_name, cfg in custom_groups.items():
            groups[group_name] = dict(cfg)

    # 3. Required check + 4. Policy application
    for group_cfg in groups.values():
        group_headers = [str(h).lower() for h in group_cfg.get("headers", [])]
        required_headers = [str(r).lower() for r in group_cfg.get("required", [])]
        policy = str(group_cfg.get("policy", "ignore-meta"))

        if policy == "ignore-meta":
            continue

        # Step 3: If any required header is missing from validated_meta, skip the group!
        if any(req_h not in validated_meta for req_h in required_headers):
            continue

        present_in_meta = [h for h in group_headers if h in validated_meta]
        if not present_in_meta:
            continue

        if policy == "clear-and-use-meta":
            for h in group_headers:
                final_headers.pop(h, None)
            for h in present_in_meta:
                final_headers[h] = validated_meta[h]
        elif policy == "prefer-meta":
            for h in present_in_meta:
                final_headers[h] = validated_meta[h]

    return McpRequirementsAndMetaForwardingDecision(
        allowed=True,
        reason="ok",
        client_may_filter_tool=client_may_filter_tool,
        forwarded_headers=final_headers,
    )
