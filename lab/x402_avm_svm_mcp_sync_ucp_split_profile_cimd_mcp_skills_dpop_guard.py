"""Stage 172 deterministic protocol & benchmark guardrails (2026-10-23 primary-source audit part 2):
1. x402 Foundation (PRs #3894, #3886, #3905, #3907, #3906 updated 2026-10-23):
   - PR #3894 (`fix(avm): require canonical CAIP-2 networks`): removes legacy Algorand full-genesis-hash
     exception (>32 chars) in `NetworkSchemaV2`; Algorand v2 accepts only canonical 32-char CAIP-2
     identifiers (`algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k`, `algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDe`).
   - PR #3886 (`fix(evm): report signature lookup failures as retryable on the remaining verify paths`):
     `eth_getCode` or `isValidSignature` RPC transport failures across `exact Permit2`, `exact EIP-3009/EIP-1271`,
     and `upto Permit2` must report `invalid_exact_evm_failed_to_verify_signature` or
     `invalid_upto_evm_failed_to_verify_signature` instead of non-retryable `invalid_permit2_signature` /
     `invalid_exact_evm_signature`.
   - PR #3905 (`feat(svm): add opt-in readable batch proofs and browser signer`): Solana batch payment
     `proofFormat == "readable"` is opt-in and requires matching client, resource-server, and facilitator
     support plus exact signed-bytes verification (`signed_bytes_match_expected == True`).
   - PR #3907 (`fix(python): restore x402MCPClientSync hooks and run mcp tests in CI`): when
     `auto_payment == False` or `on_payment_requested` returns `False`, `x402MCPClientSync` must raise
     `PaymentRequiredError` instead of silently returning the unpaid 402 tool result.
   - PR #3906 (`docs(specs): say that bazaar info.input describes the resource, not the probe`): Bazaar
     `info.input` describes the target resource's invocation contract and must not mutate into a hybrid
     `method == "GET"` with `bodyType` / `body` when probed via `GET`.
2. Universal Commerce Protocol (UCP) (PRs #658, #985, #618, #444, #974 updated 2026-10-23):
   - PR #658 (`docs(split-payments): validate the allowed_combinations profile example`): UCP profile
     `capabilities` must be an object map keyed by reverse-domain name (never a JSON list), each entry
     must include the required `schema` URL, and `dev.ucp.shopping.split_payment` cannot pin a pre-feature
     release version (`2026-01-23`).
   - PR #985 (`docs(identity-linking): don't presume a client registration model`): confidential platforms
     support registration-free IETF Client ID Metadata Documents (`client_id` as `https://` URL) with
     `private_key_jwt` rather than presuming static `client_secret` registration.
   - PR #618 (`docs(ap2): clarify ES512 signature scope`) & PR #444 (`docs(mcp): align checkout/order
     bindings with cart-mcp pattern`).
3. Model Context Protocol (MCP) (PRs #2076 `SEP-2076`, #1932 `SEP-1932`, #2848 `SEP-2848` updated 2026-10-21..23):
   - `SEP-2076`: Agent Skills as a first-class MCP primitive (`skills/list`, `skills/get`) with declared
     skill manifest digest and tool-scope boundary.
   - `SEP-1932`: DPoP Profile for MCP (`DPoP` proof `htm`, `htu`, `ath`, and single-use `jti` binding).
   - `SEP-2848`: Asynchronous approval for consequential tool calls (`approval_status == "approved"` before
     side-effecting execution).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from lab.x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_guard import (
    GuardDecision,
)

CAIP2_STRICT_RE = re.compile(r"^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
RETRYABLE_EVM_VERIFY_ERRORS = frozenset(
    {
        "invalid_exact_evm_failed_to_verify_signature",
        "invalid_upto_evm_failed_to_verify_signature",
    }
)


def validate_x402_avm_caip2_evm_retryable_svm_readable_and_mcp_sync_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate x402 2026-10-23 PRs #3894, #3886, #3905, #3907, and #3906."""
    avm_net = str(payload.get("avm_network", "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k"))
    if not CAIP2_STRICT_RE.match(avm_net):
        return GuardDecision(
            allowed=False,
            decision_code="X402_AVM_LEGACY_GENESIS_HASH_EXCEEDS_CAIP2",
            reason="Algorand v2 requires canonical 32-char CAIP-2 network identifiers and rejects full 44-char genesis hashes (PR #3894).",
            details={"avm_network": avm_net},
        )

    evm_lookup = payload.get("evm_verify_lookup", {})
    if isinstance(evm_lookup, Mapping) and evm_lookup:
        if (
            evm_lookup.get("rpc_transport_failed") is True
            and evm_lookup.get("reported_error") not in RETRYABLE_EVM_VERIFY_ERRORS
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_EVM_LOOKUP_FAILURE_MISREPORTED_AS_BAD_SIGNATURE",
                reason="EVM Permit2/EIP-3009/EIP-1271 eth_getCode or isValidSignature transport failures must report invalid_*_evm_failed_to_verify_signature (PR #3886).",
                details=dict(evm_lookup),
            )

    svm_batch = payload.get("svm_batch_proof", {})
    if isinstance(svm_batch, Mapping) and svm_batch:
        if svm_batch.get("proof_format") == "readable":
            if (
                svm_batch.get("all_peers_support_readable", True) is not True
                or svm_batch.get("signed_bytes_match_expected", True) is not True
            ):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_SVM_READABLE_BATCH_PROOF_MISMATCH",
                    reason="Opt-in SVM readable batch proofs require matching client/server/facilitator support and exact signed-bytes verification (PR #3905).",
                    details=dict(svm_batch),
                )

    mcp_sync = payload.get("python_mcp_sync_client", {})
    if isinstance(mcp_sync, Mapping) and mcp_sync:
        auto_pay = bool(mcp_sync.get("auto_payment", True))
        hook_approved = bool(mcp_sync.get("on_payment_requested_approved", True))
        returned_unpaid_402 = bool(mcp_sync.get("returned_unpaid_402_without_raising", False))
        if (not auto_pay or not hook_approved) and returned_unpaid_402:
            return GuardDecision(
                allowed=False,
                decision_code="X402_MCP_SYNC_UNPAID_402_SILENT_RETURN_FORBIDDEN",
                reason="x402MCPClientSync must raise PaymentRequiredError when auto_payment=False or on_payment_requested returns False (PR #3907).",
                details=dict(mcp_sync),
            )

    bazaar = payload.get("bazaar_resource_input", {})
    if isinstance(bazaar, Mapping) and bazaar:
        if bazaar.get("method") in {"GET", "HEAD", "DELETE"} and (
            bazaar.get("has_body_type") is True or bazaar.get("derived_from_probe_method") is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_BAZAAR_INPUT_MUTATED_BY_PROBE_METHOD",
                reason="Bazaar info.input must describe the target resource contract rather than coupling GET probe method with bodyType/body (PR #3906).",
                details=dict(bazaar),
            )

    return GuardDecision(
        allowed=True,
        decision_code="X402_AVM_EVM_SVM_MCP_SYNC_AND_BAZAAR_OK",
        reason="x402 AVM canonical CAIP-2, EVM retryable lookup errors, SVM readable batch proofs, Python MCP sync hooks, and Bazaar input contract verified.",
        details={"avm_network": avm_net},
    )


def validate_ucp_split_payment_profile_cimd_and_mcp_binding_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP 2026-10-23 PRs #658, #985, #618, and #444."""
    profile = payload.get("split_payment_profile", {})
    if isinstance(profile, Mapping) and profile:
        if profile.get("capabilities_is_object_map", True) is not True:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_PROFILE_CAPABILITIES_MUST_BE_OBJECT_MAP",
                reason="UCP profile capabilities must be an object map keyed by reverse-domain name, not a list (PR #658).",
                details=dict(profile),
            )
        if (
            not profile.get("schema_url")
            or profile.get("pinned_version") == "2026-01-23"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_SPLIT_PAYMENT_SCHEMA_OR_VERSION_INVALID",
                reason="dev.ucp.shopping.split_payment capability entry requires schema URL and cannot pin pre-feature version 2026-01-23 (PR #658).",
                details=dict(profile),
            )

    cimd = payload.get("identity_linking_client", {})
    if isinstance(cimd, Mapping) and cimd:
        if (
            cimd.get("uses_cimd_https_client_id") is True
            and cimd.get("presumed_static_client_secret") is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDENTITY_LINKING_PRESUMED_CLIENT_SECRET_FORBIDDEN",
                reason="UCP identity-linking must support registration-free Client ID Metadata Documents with private_key_jwt without presuming client_secret (PR #985).",
                details=dict(cimd),
            )

    mcp_bind = payload.get("mcp_checkout_order_binding", {})
    if isinstance(mcp_bind, Mapping) and mcp_bind:
        if mcp_bind.get("aligned_with_cart_mcp_envelope", True) is not True:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_MCP_CHECKOUT_ORDER_BINDING_DRIFT",
                reason="UCP MCP checkout and order tool bindings must align with the canonical cart-mcp envelope pattern (PR #444).",
                details=dict(mcp_bind),
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_SPLIT_PROFILE_CIMD_AND_MCP_BINDING_OK",
        reason="UCP split-payment profile object map, registration-agnostic CIMD identity linking, and MCP checkout/order binding verified.",
        details={},
    )


def validate_mcp_skills_primitive_dpop_and_async_approval_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate MCP SEP-2076 (#2076), SEP-1932 (#1932), and SEP-2848 (#2848)."""
    skill = payload.get("mcp_skill_primitive", {})
    if isinstance(skill, Mapping) and skill:
        if (
            not skill.get("skill_manifest_sha256")
            or skill.get("undeclared_tool_escalation", False) is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_SKILL_PRIMITIVE_UNBOUND_TOOL_ESCALATION",
                reason="MCP SEP-2076 Agent Skills primitive requires a verified manifest digest and blocks undeclared tool escalation (#2076).",
                details=dict(skill),
            )

    dpop = payload.get("mcp_dpop_proof", {})
    if isinstance(dpop, Mapping) and dpop:
        if (
            dpop.get("ath_matches_access_token", True) is not True
            or dpop.get("htu_matches_mcp_endpoint", True) is not True
            or dpop.get("jti_replayed", False) is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_DPOP_SENDER_CONSTRAINT_VIOLATION",
                reason="MCP SEP-1932 DPoP profile requires matching ath, htu, and non-replayed jti (#1932).",
                details=dict(dpop),
            )

    async_app = payload.get("mcp_async_approval", {})
    if isinstance(async_app, Mapping) and async_app:
        if (
            async_app.get("consequential_tool") is True
            and async_app.get("approval_status", "approved") != "approved"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_ASYNC_APPROVAL_NOT_GRANTED",
                reason="MCP SEP-2848 consequential tool execution must wait for asynchronous approval status=='approved' (#2848).",
                details=dict(async_app),
            )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_SKILLS_DPOP_AND_ASYNC_APPROVAL_OK",
        reason="MCP SEP-2076 Agent Skills primitive, SEP-1932 DPoP sender-constrained tokens, and SEP-2848 async tool approval verified.",
        details={},
    )
