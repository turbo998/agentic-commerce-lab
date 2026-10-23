"""Stage 180 deterministic protocol and benchmark evaluation guards.

Covers 2026-10-23 primary-source updates across:
1. Model Context Protocol Issue #3394 (`2026-10-23T14:43:58Z`):
   - Lost-response (`LOST_ACK`) retry on mutating `tools/call` (which MCP
     requires to use a fresh JSON-RPC request `id` per attempt):
     - Pre-dispatch durable recording of `logical_operation_id` so the system
       distinguishes `"never_attempted"` from `"attempted_outcome_unknown"`.
     - Blocking retries where the LLM reworded tool arguments
       (`args_reworded_on_retry=True`) without a pre-dispatch
       `logical_operation_id` anchor.
     - Requiring read-back during an in-flight payment/mutation to expose
       `"in_flight"` rather than `"ready_for_payment"`, and classifying
       negative lookups under non-authoritative/delayed visibility (`X02`) as
       `"outcome_unknown"` rather than `"not_executed"`.
     - Reconciling a fresh-key `complete_checkout` retry that returns
       `"session_already_completed"` via authoritative read-back instead of
       surfacing a false payment failure.
2. Model Context Protocol Issue #3430 (`2026-10-23T10:02:41Z`):
   - First-level `InitializeResult.serverInfo.description` requirement when
     `lazy_loading=True`.
   - Separate `routing_metadata_digest` vs. `input_schema_digest` vs.
     `free_prose_digest`, plus detection of cross-tool steering injection in
     `Tool.description` (inspired by the 38,126-server / 23,821-change study
     where 9/12 steering rewrites modified only `Tool.description`).
3. Sierra tau2-bench PR #638 (`2026-10-23T16:20:33Z`) & Issue #678
   (`2026-10-23T12:12:39Z`):
   - `loan_servicing` / `loan_servicing_fr` domain invariants: rejecting
     payments and autopay on `CLOSED_STATUSES = {"paid_off", "charged_off"}`
     (commit `ce55fda`), language-neutral `communicate_info` (`^[A-Z]{2}-\\d+$`
     or integer `< 1000`), excluding free-text transfer `summary` from DB state
     hashes, and rejecting `solo_mode=True`.
   - `result_reward_analysis()` resilience against `make_infra_failure_sim()`
     placeholder records with `reward_info=None` (`#678`).
4. Universal Commerce Protocol PR #792 (`2026-10-23T16:15:08Z`) & Issue #924 /
   PTC 2026-10-15 Minutes (`2026-10-23T16:14:57Z`):
   - `TokenCredential.binding` and `TokenCredential.identity` preservation from
     `/tokenize` through Checkout, processor issuance binding verification, and
     prohibition of `TokenCredential.identity` as caller authentication.
   - Agentic Donations (`#924`) multi-entity transparency (`beneficiary_id`,
     `collector_id`, `receipt_issuer_id`) and strict separation of tax-receipt
     `donation_amount_minor` from for-profit `platform_tip_minor`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

CLOSED_LOAN_STATUSES = frozenset({"paid_off", "charged_off"})
REFERENCE_CODE_RE = re.compile(r"^[A-Z]{2}-\d+$")
STEERING_PATTERNS = (
    re.compile(r"prefer\s+this\s+tool\s+over\s+web\s+search", re.IGNORECASE),
    re.compile(r"instead\s+of\s+(the\s+)?(client'?s?\s+)?(fetch|browser|web\s+search)", re.IGNORECASE),
    re.compile(r"do\s+not\s+use\s+(builtin|built-in|native)\s+(fetch|search|browser)", re.IGNORECASE),
    re.compile(r"always\s+use\s+this\s+tool\s+instead\s+of", re.IGNORECASE),
)


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any]


def validate_mcp_mutating_lost_response_retry(
    *,
    is_mutating_tool: bool,
    attempt_1_jsonrpc_id: str | int,
    retry_jsonrpc_id: str | int,
    pre_dispatch_logical_op_id: str = "",
    retry_logical_op_id: str = "",
    args_reworded_on_retry: bool = False,
    lost_ack_occurred: bool = True,
    readback_status: str = "completed",
    readback_authoritative: bool = True,
    retry_error_code: str = "",
) -> GuardDecision:
    """Validate MCP #3394 mutating `tools/call` lost-response retry invariants."""
    if str(attempt_1_jsonrpc_id) == str(retry_jsonrpc_id):
        return GuardDecision(
            allowed=False,
            decision_code="mcp_retry_jsonrpc_id_reuse_forbidden",
            reason="MCP requires each retry request to use a fresh JSON-RPC request ID within the session.",
            metadata={"attempt_1_jsonrpc_id": attempt_1_jsonrpc_id},
        )

    if not is_mutating_tool:
        return GuardDecision(
            allowed=True,
            decision_code="mcp_mutating_lost_response_retry_ok",
            reason="Read-only MCP tool retry does not risk duplicate external side effects.",
            metadata={"is_mutating_tool": False},
        )

    if not pre_dispatch_logical_op_id.strip():
        return GuardDecision(
            allowed=False,
            decision_code="mcp_pre_dispatch_logical_op_id_missing",
            reason="Mutating tools/call must record a stable logical_operation_id before dispatch to distinguish never-attempted from outcome-unknown.",
            metadata={},
        )

    if args_reworded_on_retry and retry_logical_op_id.strip() != pre_dispatch_logical_op_id.strip():
        return GuardDecision(
            allowed=False,
            decision_code="mcp_mutating_retry_reworded_args_unanchored",
            reason="Reworded tool arguments on retry cannot be deduplicated without matching the pre-dispatch logical_operation_id.",
            metadata={
                "pre_dispatch_logical_op_id": pre_dispatch_logical_op_id,
                "retry_logical_op_id": retry_logical_op_id,
            },
        )

    if lost_ack_occurred:
        if readback_status == "ready_for_payment":
            return GuardDecision(
                allowed=False,
                decision_code="mcp_readback_inflight_masked_as_ready_for_payment",
                reason="In-flight payment read-back must expose 'in_flight' rather than 'ready_for_payment' to prevent duplicate charges.",
                metadata={"readback_status": readback_status},
            )
        if readback_status == "not_found" and not readback_authoritative:
            return GuardDecision(
                allowed=False,
                decision_code="mcp_non_authoritative_negative_lookup_claimed_not_executed",
                reason="Negative lookup on delayed/non-authoritative store (X02) must remain 'outcome_unknown', not proof of non-execution.",
                metadata={"readback_status": readback_status, "readback_authoritative": False},
            )

    reconciled_from_readback = False
    if retry_error_code == "session_already_completed":
        if readback_authoritative and readback_status == "completed":
            reconciled_from_readback = True
        else:
            return GuardDecision(
                allowed=False,
                decision_code="mcp_retry_already_completed_unverified_readback",
                reason="'session_already_completed' on retry requires authoritative 'completed' read-back before succeeding.",
                metadata={"retry_error_code": retry_error_code, "readback_status": readback_status},
            )

    return GuardDecision(
        allowed=True,
        decision_code="mcp_mutating_lost_response_retry_ok",
        reason="Mutating MCP tool retry satisfies pre-dispatch logical identity and authoritative read-back reconciliation.",
        metadata={
            "logical_operation_id": pre_dispatch_logical_op_id,
            "reconciled_from_readback": reconciled_from_readback,
        },
    )


def validate_mcp_lazy_routing_and_description_steering(
    *,
    lazy_loading: bool,
    server_routing_description: str,
    pinned_input_schema_digest: str,
    current_input_schema_digest: str,
    pinned_routing_metadata_digest: str,
    current_routing_metadata_digest: str,
    previous_tool_description: str,
    current_tool_description: str,
    reapproved: bool = False,
) -> GuardDecision:
    """Validate MCP #3430 server-level routing description & cross-tool steering pin."""
    if lazy_loading and not server_routing_description.strip():
        return GuardDecision(
            allowed=False,
            decision_code="mcp_lazy_loading_server_routing_description_missing",
            reason="Lazy/deferred tool loading requires a non-empty server-level routing description in InitializeResult.",
            metadata={"lazy_loading": True},
        )

    if pinned_input_schema_digest != current_input_schema_digest and not reapproved:
        return GuardDecision(
            allowed=False,
            decision_code="mcp_input_schema_digest_changed_requires_reapproval",
            reason="Tool inputSchema digest changed without host re-approval.",
            metadata={
                "pinned_input_schema_digest": pinned_input_schema_digest,
                "current_input_schema_digest": current_input_schema_digest,
            },
        )

    if pinned_routing_metadata_digest != current_routing_metadata_digest and not reapproved:
        return GuardDecision(
            allowed=False,
            decision_code="mcp_routing_metadata_digest_changed_requires_reapproval",
            reason="Structured routing metadata digest changed without host re-approval.",
            metadata={
                "pinned_routing_metadata_digest": pinned_routing_metadata_digest,
                "current_routing_metadata_digest": current_routing_metadata_digest,
            },
        )

    prev_has_steering = any(p.search(previous_tool_description) for p in STEERING_PATTERNS)
    curr_has_steering = any(p.search(current_tool_description) for p in STEERING_PATTERNS)
    if prev_has_steering != curr_has_steering and not reapproved:
        return GuardDecision(
            allowed=False,
            decision_code="mcp_tool_description_cross_tool_steering_detected",
            reason="Tool description added or removed a cross-tool routing/steering directive without host re-approval.",
            metadata={
                "prev_has_steering": prev_has_steering,
                "curr_has_steering": curr_has_steering,
            },
        )

    prose_changed = previous_tool_description != current_tool_description
    return GuardDecision(
        allowed=True,
        decision_code="mcp_lazy_routing_and_description_pin_ok",
        reason="Server routing description, schema/routing digests, and prose steering check passed.",
        metadata={
            "prose_changed_benign": prose_changed and not (prev_has_steering != curr_has_steering),
        },
    )


def validate_tau2_loan_servicing_and_reward_breakdown(
    *,
    loan_status: str,
    operation: str,
    solo_mode: bool = False,
    communicate_info: list[str] | None = None,
    transfer_record: dict[str, Any] | None = None,
    simulation_rewards: list[dict[str, Any] | None] | None = None,
) -> GuardDecision:
    """Validate Sierra tau2-bench PR #638 (`loan_servicing` EN/FR) & Issue #678."""
    if solo_mode:
        return GuardDecision(
            allowed=False,
            decision_code="tau2_loan_servicing_solo_mode_unsupported",
            reason="loan_servicing does not support solo_mode=True.",
            metadata={"solo_mode": True},
        )

    if operation in {"make_payment", "enroll_autopay"} and loan_status in CLOSED_LOAN_STATUSES:
        return GuardDecision(
            allowed=False,
            decision_code="tau2_loan_servicing_closed_status_payment_forbidden",
            reason=f"Operation '{operation}' is forbidden on closed loan status '{loan_status}' (paid_off or charged_off).",
            metadata={"loan_status": loan_status, "operation": operation},
        )

    for token in communicate_info or []:
        is_ref_code = bool(REFERENCE_CODE_RE.match(token))
        is_small_int = token.isdigit() and 0 <= int(token) < 1000
        if not (is_ref_code or is_small_int):
            return GuardDecision(
                allowed=False,
                decision_code="tau2_loan_servicing_non_neutral_communicate_info",
                reason="communicate_info must contain only reference codes (e.g. PM-31887) or whole numbers < 1000 for EN/FR parity.",
                metadata={"invalid_token": token},
            )

    hashed_transfer_state = None
    if transfer_record is not None:
        if not transfer_record.get("transfer_id") or not transfer_record.get("reason"):
            return GuardDecision(
                allowed=False,
                decision_code="tau2_loan_servicing_transfer_missing_structured_fields",
                reason="transfer_to_human_agents must record structured {transfer_id, reason}.",
                metadata={},
            )
        canonical = json.dumps(
            {
                "transfer_id": str(transfer_record["transfer_id"]),
                "reason": str(transfer_record["reason"]),
            },
            sort_keys=True,
        )
        hashed_transfer_state = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    sims = simulation_rewards if simulation_rewards is not None else [{"reward": 1.0, "reward_breakdown": {"db": 1.0}}]
    scored_count = 0
    skipped_unscored_count = 0
    for item in sims:
        if item is None or item.get("reward_breakdown") is None:
            skipped_unscored_count += 1
        else:
            scored_count += 1

    return GuardDecision(
        allowed=True,
        decision_code="tau2_loan_servicing_and_reward_breakdown_ok",
        reason="loan_servicing EN/FR invariants and unscored simulation filtering succeeded.",
        metadata={
            "scored_count": scored_count,
            "skipped_unscored_count": skipped_unscored_count,
            "hashed_transfer_state": hashed_transfer_state,
        },
    )


def validate_ucp_token_credential_context_and_donations(
    *,
    tokenized_binding: dict[str, Any],
    checkout_presented_binding: dict[str, Any],
    processor_issuance_binding: dict[str, Any],
    tokenized_identity: str,
    checkout_presented_identity: str,
    identity_used_as_caller_auth: bool = False,
    is_donation_checkout: bool = False,
    donation_amount_minor: int = 0,
    platform_tip_minor: int = 0,
    tax_receipt_amount_minor: int = 0,
    beneficiary_id: str = "",
    collector_id: str = "",
    receipt_issuer_verified_nonprofit: bool = True,
) -> GuardDecision:
    """Validate UCP PR #792 TokenCredential context & Issue #924 Agentic Donations."""
    if identity_used_as_caller_auth:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_token_credential_identity_used_as_auth_forbidden",
            reason="TokenCredential.identity is a participant identifier and must not be accepted as caller authentication.",
            metadata={"identity": checkout_presented_identity},
        )

    if (
        tokenized_binding != checkout_presented_binding
        or tokenized_identity != checkout_presented_identity
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_token_credential_platform_mutation_forbidden",
            reason="Platforms must preserve TokenCredential.binding and TokenCredential.identity unchanged from tokenization into checkout.",
            metadata={
                "tokenized_binding": tokenized_binding,
                "checkout_presented_binding": checkout_presented_binding,
            },
        )

    if checkout_presented_binding != processor_issuance_binding:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_token_credential_binding_mismatch",
            reason="Presented TokenCredential.binding does not match the processor's issuance record.",
            metadata={
                "checkout_presented_binding": checkout_presented_binding,
                "processor_issuance_binding": processor_issuance_binding,
            },
        )

    if is_donation_checkout:
        if not beneficiary_id.strip() or not collector_id.strip():
            return GuardDecision(
                allowed=False,
                decision_code="ucp_donation_entities_undisclosed",
                reason="Agentic donation checkout must explicitly disclose both beneficiary_id and collector_id (Merchant of Record).",
                metadata={"beneficiary_id": beneficiary_id, "collector_id": collector_id},
            )
        if not receipt_issuer_verified_nonprofit and tax_receipt_amount_minor > 0:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_donation_unverified_tax_receipt_issuer_forbidden",
                reason="Tax-benefit receipts may only be issued when receipt_issuer_verified_nonprofit is True.",
                metadata={"tax_receipt_amount_minor": tax_receipt_amount_minor},
            )
        if tax_receipt_amount_minor != donation_amount_minor or (
            platform_tip_minor > 0
            and tax_receipt_amount_minor == donation_amount_minor + platform_tip_minor
        ):
            return GuardDecision(
                allowed=False,
                decision_code="ucp_donation_platform_tip_commingled_in_tax_receipt",
                reason="For-profit platform tips must be separated from tax-deductible donation_amount_minor on the tax receipt.",
                metadata={
                    "donation_amount_minor": donation_amount_minor,
                    "platform_tip_minor": platform_tip_minor,
                    "tax_receipt_amount_minor": tax_receipt_amount_minor,
                },
            )

    return GuardDecision(
        allowed=True,
        decision_code="ucp_token_credential_context_and_donations_ok",
        reason="TokenCredential binding/identity preservation and Agentic Donations transparency checks passed.",
        metadata={
            "identity": checkout_presented_identity,
            "is_donation_checkout": is_donation_checkout,
        },
    )
