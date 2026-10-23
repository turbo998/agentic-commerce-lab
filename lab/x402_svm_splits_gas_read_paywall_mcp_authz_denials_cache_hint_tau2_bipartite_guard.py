"""Stage 192 deterministic guardrails for x402 SVM Multi-Payee Splits, Python Gas-Sponsoring Chain-Read Gate & Paywall Auto-Detection, MCP SEP-2643 Structured Authorization Denials & SEP-2419 cache_hint, and Sierra tau2-bench Maximum Bipartite Action Matching.

Covers primary-source specifications and PRs:
1. x402 `exact` on SVM §5 Multi-Payee Splits (`x402-foundation/x402` PR #3221):
   - Sponsor `/supported` capability advertisement (`maxSplits` default 0, range 0..8;
     `ataCreationSponsored` default False) and fail-closed rejection (`split_count_exceeded`,
     `split_ata_creation_not_authorized`).
   - Absolute base-unit integer `splits[].amount` in `[1, 2^64 - 1]`, strictly positive
     merchant remainder `primary = amount - sum(splits[].amount) > 0`
     (`split_remainder_not_positive`), and distinct `payTo` addresses across primary + splits.
   - Distinct per-leg `TransferChecked` matching (`split_leg_unmatched`,
     `split_unexpected_transfer`) with exact equality (`==`) on split legs and overpayment
     tolerance (`>= primary`) only on the primary leg.
   - Symmetric opt-in `AssociatedTokenProgram: CreateIdempotent` ATA creation (rejecting
     non-idempotent `Create`, unmarked recipients, or unadvertised sponsor) and generalized
     Path 1 static instruction layout `[3 + N + K, 7 + N + K]`.
   - Client consent verification displaying `splits[].memo` alongside `payTo` (never in place
     of `payTo`).
2. x402 Python Gas Sponsoring Chain-Read Gate (PR #3903), `@x402/paywall` `accepts[0]`
   Auto-Detection (PR #3600), and `create_headers` `Mapping` Support (PR #3895):
   - Once-per-network warning and extension skip when gas sponsoring is advertised but
     signer lacks `read_contract`; silent skip when signer has `read_contract` but lacks
     `sign_transaction` for `erc20ApprovalGasSponsoring`.
   - `@x402/paywall` auto-detection inspecting only `accepts[0]` (`scheme == "exact"` and
     supported network prefix `eip155:` / `solana:` / `algorand:`), falling back to static
     HTML when `accepts[0]` is `upto` or an unsupported network even if `accepts[1]` is
     `exact` EVM.
   - Path-keyed `create_headers` accepting any `collections.abc.Mapping` value while
     rejecting flat header dictionaries lacking `"verify"` / `"settle"` / `"supported"`.
3. MCP `SEP-2643` Structured Authorization Denials (PR #2643) & `SEP-2419` `cache_hint`
   (PR #2419):
   - `_meta["io.modelcontextprotocol/authorization"]` envelope validation: no attachment on
     partial execution, no `remediationHints` when `remediation` is `"unavailable"` or
     `"undisclosed"`, capability-gated `"url"` / `"task"` hints vs. `"undisclosed"` fallback,
     omission of `authorization_reference` on single-use RAR credentials, and non-authoritative
     `authorizationContextId` retry echo.
   - `CallToolResult._meta.cache_hint` validation (`"no-cache"` / `"cache"`), non-propagation
     to LLM/downstream, and client sensitivity override protection.
4. Sierra tau2-bench `ActionEvaluator` Maximum Bipartite One-to-One Matching (PR #665):
   - Augmenting-path maximum bipartite matching (`_match_actions`) ensuring each predicted
     tool call satisfies at most one gold action (`N` repeated gold entries require `N`
     matching calls, and constrained gold actions reclaim specific calls from unconstrained
     gold actions regardless of order).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


U64_MAX = (1 << 64) - 1
AUTH_HEADER_PATHS = ("verify", "settle", "supported")
SUPPORTED_PAYWALL_PREFIXES = ("eip155:", "solana:", "algorand:")


def _is_canonical_u64_positive_str(val: Any) -> bool:
    if not isinstance(val, str) or not val or not val.isdigit():
        return False
    if len(val) > 1 and val.startswith("0"):
        return False
    parsed = int(val)
    return 1 <= parsed <= U64_MAX


@dataclass(frozen=True)
class SvmMultiPayeeSplitsGuardDecision:
    allowed: bool
    decision_code: str
    primary_remainder: int
    leg_count: int
    path1_min_instructions: int
    path1_max_instructions: int


def evaluate_x402_svm_multi_payee_splits_guard(
    *,
    total_amount_str: str,
    primary_pay_to: str,
    primary_ata_creation_required: bool,
    splits: list[dict[str, Any]],
    sponsor_max_splits: int | None,
    sponsor_ata_creation_sponsored: bool | None,
    observed_transfers: list[dict[str, Any]],
    observed_ata_creations: list[dict[str, Any]],
    decompiled_instruction_count: int,
    client_consented_splits: list[dict[str, Any]] | None = None,
    wallet_displays_memo_instead_of_address: bool = False,
) -> SvmMultiPayeeSplitsGuardDecision:
    """Enforce x402 `exact` on SVM §5 Multi-Payee Splits invariants (PR #3221)."""
    if not _is_canonical_u64_positive_str(total_amount_str):
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="invalid_total_amount",
            primary_remainder=0,
            leg_count=0,
            path1_min_instructions=0,
            path1_max_instructions=0,
        )
    total_amount = int(total_amount_str)

    effective_max_splits = 0 if sponsor_max_splits is None else sponsor_max_splits
    effective_ata_sponsored = bool(sponsor_ata_creation_sponsored)

    n_splits = len(splits)
    if n_splits > 8 or n_splits > effective_max_splits:
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_count_exceeded",
            primary_remainder=0,
            leg_count=n_splits + 1,
            path1_min_instructions=0,
            path1_max_instructions=0,
        )

    if wallet_displays_memo_instead_of_address:
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_memo_replaced_recipient_address",
            primary_remainder=0,
            leg_count=n_splits + 1,
            path1_min_instructions=0,
            path1_max_instructions=0,
        )

    if client_consented_splits is not None:
        normalized_actual = [
            (s.get("payTo"), s.get("amount"), s.get("memo", ""))
            for s in splits
        ]
        normalized_consented = [
            (s.get("payTo"), s.get("amount"), s.get("memo", ""))
            for s in client_consented_splits
        ]
        if normalized_actual != normalized_consented:
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code="split_client_consent_mismatch",
                primary_remainder=0,
                leg_count=n_splits + 1,
                path1_min_instructions=0,
                path1_max_instructions=0,
            )

    seen_payees = {primary_pay_to}
    split_sum = 0
    marked_ata_recipients: set[str] = set()
    if primary_ata_creation_required:
        marked_ata_recipients.add(primary_pay_to)

    for split in splits:
        payee = split.get("payTo", "")
        amt_str = split.get("amount", "")
        memo = split.get("memo")
        ata_req = bool(split.get("ataCreationRequired", False))
        if not isinstance(payee, str) or not payee or payee in seen_payees:
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code="split_duplicate_or_invalid_payee",
                primary_remainder=0,
                leg_count=n_splits + 1,
                path1_min_instructions=0,
                path1_max_instructions=0,
            )
        seen_payees.add(payee)
        if not _is_canonical_u64_positive_str(amt_str):
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code="split_invalid_amount",
                primary_remainder=0,
                leg_count=n_splits + 1,
                path1_min_instructions=0,
                path1_max_instructions=0,
            )
        if memo is not None and (not isinstance(memo, str) or len(memo.encode("utf-8")) > 566):
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code="split_invalid_memo",
                primary_remainder=0,
                leg_count=n_splits + 1,
                path1_min_instructions=0,
                path1_max_instructions=0,
            )
        split_sum += int(amt_str)
        if ata_req:
            marked_ata_recipients.add(payee)

    primary_remainder = total_amount - split_sum
    if primary_remainder <= 0:
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_remainder_not_positive",
            primary_remainder=primary_remainder,
            leg_count=n_splits + 1,
            path1_min_instructions=0,
            path1_max_instructions=0,
        )

    # §5.4 ATA creation checks
    if marked_ata_recipients and not effective_ata_sponsored:
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_ata_creation_not_authorized",
            primary_remainder=primary_remainder,
            leg_count=n_splits + 1,
            path1_min_instructions=0,
            path1_max_instructions=0,
        )

    created_owners: set[str] = set()
    for ata_ix in observed_ata_creations:
        owner = ata_ix.get("owner", "")
        ix_name = ata_ix.get("instruction", "")
        already_exists = bool(ata_ix.get("ata_already_exists", False))
        if (
            not effective_ata_sponsored
            or owner not in marked_ata_recipients
            or ix_name != "CreateIdempotent"
            or already_exists
            or owner in created_owners
        ):
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code="split_ata_creation_not_authorized",
                primary_remainder=primary_remainder,
                leg_count=n_splits + 1,
                path1_min_instructions=0,
                path1_max_instructions=0,
            )
        created_owners.add(owner)

    k_creates = len(observed_ata_creations)
    min_ix = 3 + n_splits + k_creates
    max_ix = 7 + n_splits + k_creates
    if not (min_ix <= decompiled_instruction_count <= max_ix):
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_static_layout_count_out_of_bounds",
            primary_remainder=primary_remainder,
            leg_count=n_splits + 1,
            path1_min_instructions=min_ix,
            path1_max_instructions=max_ix,
        )

    # §5.3 Per-leg distinct transfer matching: primary tolerates >=, splits require ==
    required_legs: list[tuple[str, int, bool]] = [(primary_pay_to, primary_remainder, True)]
    for split in splits:
        required_legs.append((split["payTo"], int(split["amount"]), False))

    if len(observed_transfers) < len(required_legs):
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_leg_unmatched",
            primary_remainder=primary_remainder,
            leg_count=len(required_legs),
            path1_min_instructions=min_ix,
            path1_max_instructions=max_ix,
        )
    if len(observed_transfers) > len(required_legs):
        return SvmMultiPayeeSplitsGuardDecision(
            allowed=False,
            decision_code="split_unexpected_transfer",
            primary_remainder=primary_remainder,
            leg_count=len(required_legs),
            path1_min_instructions=min_ix,
            path1_max_instructions=max_ix,
        )

    used_transfer_indices: set[int] = set()
    for leg_pay_to, leg_amount, allow_overpay in required_legs:
        matched_idx = None
        for idx, tx_transfer in enumerate(observed_transfers):
            if idx in used_transfer_indices:
                continue
            obs_to = tx_transfer.get("payTo")
            obs_amt = int(tx_transfer.get("amount", -1))
            if obs_to != leg_pay_to:
                continue
            if allow_overpay and obs_amt >= leg_amount:
                matched_idx = idx
                break
            if not allow_overpay and obs_amt == leg_amount:
                matched_idx = idx
                break
        if matched_idx is None:
            # Determine if a transfer existed to an unexpected payee vs wrong amount
            all_declared = {leg[0] for leg in required_legs}
            if any(t.get("payTo") not in all_declared for t in observed_transfers):
                code = "split_unexpected_transfer"
            else:
                code = "split_leg_unmatched"
            return SvmMultiPayeeSplitsGuardDecision(
                allowed=False,
                decision_code=code,
                primary_remainder=primary_remainder,
                leg_count=len(required_legs),
                path1_min_instructions=min_ix,
                path1_max_instructions=max_ix,
            )
        used_transfer_indices.add(matched_idx)

    return SvmMultiPayeeSplitsGuardDecision(
        allowed=True,
        decision_code="svm_multi_payee_splits_verified",
        primary_remainder=primary_remainder,
        leg_count=len(required_legs),
        path1_min_instructions=min_ix,
        path1_max_instructions=max_ix,
    )


@dataclass(frozen=True)
class EvmGasSponsorPaywallHeadersDecision:
    allowed: bool
    decision_code: str
    warning_count_for_network: int
    extension_signed: bool
    rendered_paywall_kind: str


def evaluate_x402_gas_read_paywall_and_headers_guard(
    *,
    network: str,
    advertised_sponsoring_key: str | None,
    signer_can_read_contract: bool,
    signer_can_sign_transaction: bool,
    warned_networks: set[str],
    invocation_count: int = 1,
    accepts: list[dict[str, str]] | None = None,
    custom_paywall_registered: bool = False,
    create_headers_result: Mapping[str, Any] | None = None,
) -> EvmGasSponsorPaywallHeadersDecision:
    """Enforce x402 PRs #3903, #3600, and #3895."""
    # 1. PR #3895: create_headers path-keyed Mapping validation
    if create_headers_result is not None:
        has_path_key = any(
            isinstance(create_headers_result.get(path), Mapping)
            for path in AUTH_HEADER_PATHS
        )
        if not has_path_key and any(
            not isinstance(v, Mapping) for v in create_headers_result.values()
        ):
            return EvmGasSponsorPaywallHeadersDecision(
                allowed=False,
                decision_code="create_headers_flat_dict_rejected",
                warning_count_for_network=0,
                extension_signed=False,
                rendered_paywall_kind="none",
            )

    # 2. PR #3903: Gas sponsoring chain-read gate & once-per-network warning
    warnings_emitted = 0
    extension_signed = False
    if advertised_sponsoring_key in ("eip2612GasSponsoring", "erc20ApprovalGasSponsoring"):
        for _ in range(max(1, invocation_count)):
            if not signer_can_read_contract:
                if network not in warned_networks:
                    warned_networks.add(network)
                    warnings_emitted += 1
                extension_signed = False
            elif (
                advertised_sponsoring_key == "erc20ApprovalGasSponsoring"
                and not signer_can_sign_transaction
            ):
                # Silent skip when signer can read contract but cannot sign raw transactions
                extension_signed = False
            else:
                extension_signed = True

    # 3. PR #3600: @x402/paywall inspects ONLY accepts[0]
    rendered_paywall_kind = "fallback_static_html"
    if custom_paywall_registered:
        rendered_paywall_kind = "custom_provider_html"
    elif accepts:
        first_req = accepts[0]
        scheme = first_req.get("scheme", "")
        req_net = first_req.get("network", "")
        if scheme == "exact" and any(
            req_net.startswith(prefix) for prefix in SUPPORTED_PAYWALL_PREFIXES
        ):
            matched_prefix = next(
                prefix for prefix in SUPPORTED_PAYWALL_PREFIXES if req_net.startswith(prefix)
            )
            rendered_paywall_kind = f"paywall_{matched_prefix.rstrip(':')}"

    return EvmGasSponsorPaywallHeadersDecision(
        allowed=True,
        decision_code="gas_read_paywall_headers_verified",
        warning_count_for_network=warnings_emitted,
        extension_signed=extension_signed,
        rendered_paywall_kind=rendered_paywall_kind,
    )


@dataclass(frozen=True)
class McpAuthzDenialAndCacheHintDecision:
    allowed: bool
    decision_code: str
    effective_remediation: str
    should_cache_result: bool
    forwarded_meta_keys: tuple[str, ...]


def evaluate_mcp_sep2643_authz_denial_and_sep2419_cache_hint_guard(
    *,
    partial_execution: bool = False,
    envelope: dict[str, Any] | None = None,
    result_type: str = "complete",
    client_supports_url_elicitation: bool = False,
    client_supports_tasks: bool = False,
    server_has_interactive_or_task_remedy: bool = False,
    single_use_credential: bool = False,
    is_retry: bool = False,
    retry_echoed_context_id: str | None = None,
    server_treats_context_id_as_authz: bool = False,
    server_rejects_missing_context_id: bool = False,
    server_validates_token_against_actual_operation: bool = True,
    result_meta: dict[str, Any] | None = None,
    result_is_sensitive_or_mutable: bool = False,
    default_client_cache_policy: bool = True,
) -> McpAuthzDenialAndCacheHintDecision:
    """Enforce MCP SEP-2643 Structured Authorization Denials and SEP-2419 cache_hint."""
    if envelope is not None:
        if partial_execution:
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_envelope_on_partial_execution_forbidden",
                effective_remediation="invalid",
                should_cache_result=False,
                forwarded_meta_keys=(),
            )

        reason = envelope.get("reason")
        remediation = envelope.get("remediation")
        hints = envelope.get("remediationHints")
        if reason != "insufficient_authorization" or remediation not in (
            "available",
            "unavailable",
            "undisclosed",
        ):
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_invalid_reason_or_remediation",
                effective_remediation="invalid",
                should_cache_result=False,
                forwarded_meta_keys=(),
            )

        if remediation in ("unavailable", "undisclosed") and hints is not None:
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_hints_forbidden_when_not_available",
                effective_remediation=remediation,
                should_cache_result=False,
                forwarded_meta_keys=(),
            )

        # When server holds a URL/task remedy but client declared neither capability,
        # server MUST use "undisclosed", NEVER "unavailable".
        if (
            server_has_interactive_or_task_remedy
            and not client_supports_url_elicitation
            and not client_supports_tasks
            and remediation == "unavailable"
        ):
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_capability_gated_remedy_marked_unavailable",
                effective_remediation=remediation,
                should_cache_result=False,
                forwarded_meta_keys=(),
            )

        if isinstance(hints, list):
            for hint in hints:
                if not isinstance(hint, dict) or not isinstance(hint.get("type"), str):
                    return McpAuthzDenialAndCacheHintDecision(
                        allowed=False,
                        decision_code="mcp_sep2643_malformed_remediation_hint",
                        effective_remediation=remediation,
                        should_cache_result=False,
                        forwarded_meta_keys=(),
                    )
                h_type = hint["type"]
                if h_type == "url":
                    if not client_supports_url_elicitation or result_type != "input_required":
                        return McpAuthzDenialAndCacheHintDecision(
                            allowed=False,
                            decision_code="mcp_sep2643_url_hint_without_capability_or_input_required",
                            effective_remediation=remediation,
                            should_cache_result=False,
                            forwarded_meta_keys=(),
                        )
                elif h_type == "task":
                    if not client_supports_tasks or result_type not in ("task", "task_poll"):
                        return McpAuthzDenialAndCacheHintDecision(
                            allowed=False,
                            decision_code="mcp_sep2643_task_hint_without_capability_or_task_result",
                            effective_remediation=remediation,
                            should_cache_result=False,
                            forwarded_meta_keys=(),
                        )
                elif h_type == "authorization_remediation":
                    details = hint.get("authorization_details")
                    if not isinstance(details, list) or not details:
                        return McpAuthzDenialAndCacheHintDecision(
                            allowed=False,
                            decision_code="mcp_sep2643_missing_rar_authorization_details",
                            effective_remediation=remediation,
                            should_cache_result=False,
                            forwarded_meta_keys=(),
                        )
                    if single_use_credential and "authorization_reference" in hint:
                        return McpAuthzDenialAndCacheHintDecision(
                            allowed=False,
                            decision_code="mcp_sep2643_single_use_rar_must_omit_reference",
                            effective_remediation=remediation,
                            should_cache_result=False,
                            forwarded_meta_keys=(),
                        )

    if is_retry:
        if server_treats_context_id_as_authz:
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_context_id_treated_as_authorization",
                effective_remediation="invalid",
                should_cache_result=False,
                forwarded_meta_keys=(),
            )
        if retry_echoed_context_id is None and server_rejects_missing_context_id:
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_missing_context_id_rejected",
                effective_remediation="invalid",
                should_cache_result=False,
                forwarded_meta_keys=(),
            )
        if not server_validates_token_against_actual_operation:
            return McpAuthzDenialAndCacheHintDecision(
                allowed=False,
                decision_code="mcp_sep2643_token_not_validated_against_operation",
                effective_remediation="invalid",
                should_cache_result=False,
                forwarded_meta_keys=(),
            )

    # SEP-2419: CallToolResult._meta.cache_hint
    meta = dict(result_meta or {})
    raw_hint = meta.get("cache_hint")
    if raw_hint == "no-cache":
        should_cache = False
    elif raw_hint == "cache":
        # Malicious/misconfigured server cannot force caching of sensitive/mutable results
        should_cache = not result_is_sensitive_or_mutable
    else:
        # Absent or unrecognized hint falls back to client default (unless sensitive/mutable)
        should_cache = default_client_cache_policy and not result_is_sensitive_or_mutable

    # Strip cache_hint before propagating _meta to model or downstream systems
    forwarded_keys = tuple(sorted(k for k in meta if k != "cache_hint"))

    return McpAuthzDenialAndCacheHintDecision(
        allowed=True,
        decision_code="mcp_sep2643_and_sep2419_verified",
        effective_remediation=(envelope or {}).get("remediation", "none"),
        should_cache_result=should_cache,
        forwarded_meta_keys=forwarded_keys,
    )


@dataclass(frozen=True)
class Tau2BipartiteActionMatchDecision:
    allowed: bool
    decision_code: str
    gold_matches: tuple[bool, ...]
    all_matched: bool


def evaluate_tau2_bipartite_action_matching(
    *,
    predicted_tool_calls: list[dict[str, Any]],
    golden_actions: list[dict[str, Any]],
) -> Tau2BipartiteActionMatchDecision:
    """Enforce Sierra tau2-bench PR #665 one-to-one maximum bipartite action matching."""

    def _compare(gold: dict[str, Any], call: dict[str, Any]) -> bool:
        if gold.get("name") != call.get("name"):
            return False
        if gold.get("requestor", "assistant") != call.get("requestor", "assistant"):
            return False
        compare_args = gold.get("compare_args")
        gold_args = gold.get("arguments") or {}
        call_args = call.get("arguments") or {}
        if compare_args is None:
            return gold_args == call_args
        return all(gold_args.get(k) == call_args.get(k) for k in compare_args)

    candidates = [
        [
            j
            for j, call in enumerate(predicted_tool_calls)
            if _compare(gold, call)
        ]
        for gold in golden_actions
    ]
    owner: dict[int, int] = {}

    def assign(gold_idx: int, seen: set[int]) -> bool:
        for call_idx in candidates[gold_idx]:
            if call_idx in seen:
                continue
            seen.add(call_idx)
            if call_idx not in owner or assign(owner[call_idx], seen):
                owner[call_idx] = gold_idx
                return True
        return False

    for gold_idx in range(len(golden_actions)):
        assign(gold_idx, set())

    matched_gold_indices = set(owner.values())
    matches = tuple(idx in matched_gold_indices for idx in range(len(golden_actions)))
    all_matched = all(matches)

    return Tau2BipartiteActionMatchDecision(
        allowed=all_matched,
        decision_code="tau2_bipartite_all_gold_actions_matched"
        if all_matched
        else "tau2_bipartite_unmatched_gold_action",
        gold_matches=matches,
        all_matched=all_matched,
    )
