"""Stage 116 deterministic protocol & benchmark guardrails (2026-10-21 primary-source audit):
1. ACP (#316 / SEP #303, commit 2b2f2dd, 2026-10-21):
   - `UserApproval` and `approval_digest` bind what the user approved (`items[]`, `approved_at`)
     to `CheckoutSessionCompleteRequest.dispute_resolution.approval_digest` via lowercase hex
     SHA-256 of RFC 8785 JCS canonical JSON (Section 4.4a).
   - Dispute provider MUST recompute the JCS SHA-256 digest of `{items, approved_at}` AND verify
     it matches both `user_approval.approval_digest` and the `approval_digest` committed on
     checkout complete; otherwise `user_approval` is inadmissible (unilateral platform statement).
   - Section 7.4 Rule 4: When `user_approval` is admissible and a disputed order item's `sku`,
     `variant`, or `quantity` conflicts with `user_approval.items`, it is recorded as an `intent`
     conflict against `agent_platform` (`merchant_charge_reversed == False`).
2. UCP (#540 commit 207314b 2026-10-21, #966 2026-10-21, #930 2026-10-20):
   - `com.merchantstamp.mandate-evaluation` (#540): AP2 mandate TTL (`evaluated_at <= mandate_exp`)
     is evaluated exactly once at admission of Complete Checkout, using AP2 key discovery via
     `keys[]` in `/.well-known/ucp` (rejecting separate `signing_keys[]` mechanism). Once admitted,
     `complete_in_progress` MUST NOT abort mid-flight with `mandate_expired` even if
     `completed_at > mandate_exp`; expired at admission transitions to `canceled` + `mandate_expired`.
   - `dev.ucp.shopping.policy.return` (#966): Explicit `eligibility` (`window` | `unlimited` |
     `not_accepted`; omitted != unlimited), business-stated `expires_at` (platforms MUST NOT compute
     `expires_at` from `duration` + `anchor`), and charged return fee <= stated fee ceiling.
   - `dev.ucp.common.quote` (#930): Complete Checkout omits redundant `accepted_id` when not
     accepting a new proposal and projects at most one `totals[type="quote"]` entry.
3. x402 Foundation (#3304, #3855, #3857, #3858, 2026-10-21):
   - `response-provenance` (#3304): Recomputes `responseHash = sha256(jcs(fixedPoint))` over the
     closed 5-member set `{endpoint, inputs, result, method, dataVintage}`, enforces the no-collapse
     rule (`no_claim` when absent, never `contradicted`), and requires verifier golden-vector
     self-proof before emitting `contradicted` or `verified`.
   - Paywall reflected XSS (#3855), encoded path separator `%2F`/`%5C` bypass (#3857), and
     batch-settlement refund/stop-flush `pendingSettle` propagation (#3858).
4. Sierra tau2-bench 2.0 (#653 commit 57e5414 2026-10-21, #655 2026-10-21, #640, #652):
   - Knowledge sandbox minimal environment allowlist (`PATH`, `LANG`, `TERM`, `TZ`, `TMPDIR`,
     `HOME`, non-secret `LC_*`), tilde expansion in `denyRead` before overriding `HOME`, and
     redaction of parent secret values >= 8 chars from `stdout`/`stderr` (#653).
   - Root-walk read allowlist emulation via `_compute_read_denies` blocking `data_dir`, `repo_root`,
     `/tmp`, and `/etc/passwd` (#655).
   - `voice-v2` call-level quality gates (`interaction_flag_count >= 2` or
     `experience_bad_utterance_ratio > 0.25` fails call, #640) and offline `Bayes@N` uniform-prior
     Beta cohort integrity (#652).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SECRET_NAME_RE = re.compile(
    r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|AUTH)",
    re.IGNORECASE,
)
UCP_RETURN_ELIGIBILITIES = frozenset({"window", "unlimited", "not_accepted"})
UCP_RETURN_ANCHORS = frozenset({"purchased", "fulfilled", "delivered"})
X402_PROVENANCE_FIXED_POINT_KEYS = frozenset(
    {"endpoint", "inputs", "result", "method", "dataVintage"}
)
TAU2_SANDBOX_BASE_ENV_KEYS = frozenset(
    {"PATH", "LANG", "TERM", "TZ", "TMPDIR", "HOME"}
)


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    details: dict[str, Any]


def compute_jcs_sha256_hex(value: Any) -> str:
    """Compute lowercase hex SHA-256 over RFC 8785 JCS canonical JSON."""
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_acp_user_approval_digest_and_intent_conflict_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate ACP #316 (SEP #303) UserApproval JCS SHA-256 checkout binding and Section 7.4 Rule 4."""
    complete_digest = payload.get("checkout_complete_approval_digest")
    if not isinstance(complete_digest, str) or not HEX64_RE.match(complete_digest):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_COMPLETE_APPROVAL_DIGEST_MISSING_OR_INVALID",
            reason="CheckoutSessionCompleteRequest.dispute_resolution.approval_digest must be a 64-char lowercase hex SHA-256 (#316).",
            details={"checkout_complete_approval_digest": complete_digest},
        )

    user_approval = payload.get("user_approval")
    if not isinstance(user_approval, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_USER_APPROVAL_MISSING",
            reason="DisputeRecord.user_approval must be a mapping (#316).",
            details={},
        )

    items = user_approval.get("items")
    approved_at = user_approval.get("approved_at")
    approval_digest = user_approval.get("approval_digest")
    if (
        not isinstance(items, list)
        or not items
        or not isinstance(approved_at, str)
        or not approved_at.strip()
        or not isinstance(approval_digest, str)
        or not HEX64_RE.match(approval_digest)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_USER_APPROVAL_SCHEMA_INVALID",
            reason="UserApproval requires non-empty items[], RFC 3339 approved_at, and 64-char lowercase hex approval_digest (#316).",
            details={"user_approval": dict(user_approval)},
        )

    approved_index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            return GuardDecision(
                allowed=False,
                decision_code="ACP_USER_APPROVAL_ITEM_INVALID",
                reason="Each UserApproval item must be a mapping (#316).",
                details={"item": item},
            )
        sku = item.get("sku")
        qty = item.get("quantity")
        if (
            not isinstance(sku, str)
            or not sku.strip()
            or isinstance(qty, bool)
            or not isinstance(qty, int)
            or qty < 1
        ):
            return GuardDecision(
                allowed=False,
                decision_code="ACP_USER_APPROVAL_ITEM_INVALID",
                reason="Each UserApproval item requires non-empty sku and integer quantity >= 1 (#316).",
                details={"item": dict(item)},
            )
        approved_index[sku] = {
            "sku": sku,
            "quantity": qty,
            "variant": item.get("variant"),
        }

    recomputed_digest = compute_jcs_sha256_hex(
        {"items": items, "approved_at": approved_at}
    )
    if approval_digest != recomputed_digest or approval_digest != complete_digest:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_USER_APPROVAL_DIGEST_MISMATCH",
            reason="UserApproval JCS SHA-256 digest must match both user_approval.approval_digest and checkout_complete_approval_digest (Section 4.4a, #316).",
            details={
                "recomputed_digest": recomputed_digest,
                "approval_digest": approval_digest,
                "checkout_complete_approval_digest": complete_digest,
            },
        )

    disputed_items = payload.get("disputed_order_items", [])
    resolution = payload.get("dispute_resolution_decision", {})
    if not isinstance(disputed_items, list) or not isinstance(resolution, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DISPUTE_INPUT_INVALID",
            reason="disputed_order_items must be a list and dispute_resolution_decision a mapping.",
            details={},
        )

    has_intent_mismatch = False
    for order_item in disputed_items:
        if not isinstance(order_item, Mapping):
            continue
        sku = str(order_item.get("sku", ""))
        approved_item = approved_index.get(sku)
        if approved_item is None:
            has_intent_mismatch = True
            break
        if order_item.get("variant") != approved_item.get("variant") or order_item.get(
            "quantity"
        ) != approved_item.get("quantity"):
            has_intent_mismatch = True
            break

    if has_intent_mismatch:
        conflict_type = resolution.get("conflict_type")
        liable_party = resolution.get("liable_party")
        merchant_charge_reversed = resolution.get("merchant_charge_reversed")
        if (
            conflict_type != "intent"
            or liable_party != "agent_platform"
            or merchant_charge_reversed is not False
        ):
            return GuardDecision(
                allowed=False,
                decision_code="ACP_INTENT_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN",
                reason="Section 7.4 Rule 4: When an admissible UserApproval conflicts with the agent-confirmed order, it must be recorded as an intent conflict against agent_platform without reversing the merchant charge (#316).",
                details={
                    "conflict_type": conflict_type,
                    "liable_party": liable_party,
                    "merchant_charge_reversed": merchant_charge_reversed,
                },
            )

    return GuardDecision(
        allowed=True,
        decision_code="ACP_USER_APPROVAL_AND_DISPUTE_RULE4_VERIFIED",
        reason="ACP #316 UserApproval JCS SHA-256 digest and Section 7.4 Rule 4 dispute attribution verified.",
        details={"recomputed_digest": recomputed_digest},
    )


def validate_ucp_admission_mandate_ttl_and_return_policy_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP #540 (commit 207314b) admission-only AP2 mandate TTL, #966 return policy, and #930 quote."""
    mandate_eval = payload.get("mandate_evaluation", {})
    if not isinstance(mandate_eval, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MANDATE_EVAL_INVALID",
            reason="mandate_evaluation must be a mapping (#540).",
            details={},
        )

    key_discovery_source = mandate_eval.get("key_discovery_source")
    if key_discovery_source != "well_known_ucp_keys":
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MANDATE_EVAL_LEGACY_SIGNING_KEYS_FORBIDDEN",
            reason="Mandate evaluation receipts must resolve JWK keys via keys[] in /.well-known/ucp rather than separate signing_keys[] (#540 commit 207314b).",
            details={"key_discovery_source": key_discovery_source},
        )

    evaluated_at = mandate_eval.get("evaluated_at_epoch")
    mandate_exp = mandate_eval.get("mandate_exp_epoch")
    completed_at = mandate_eval.get("completed_at_epoch")
    admission_result = mandate_eval.get("admission_result")
    aborted_for_post_admission_expiry = mandate_eval.get(
        "aborted_for_post_admission_expiry", False
    )
    if not isinstance(evaluated_at, int) or not isinstance(mandate_exp, int):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MANDATE_TIMESTAMPS_INVALID",
            reason="evaluated_at_epoch and mandate_exp_epoch must be integers (#540).",
            details={},
        )

    if evaluated_at <= mandate_exp:
        if admission_result != "VALID" or aborted_for_post_admission_expiry is not False:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_POST_ADMISSION_MANDATE_EXPIRY_ABORT_FORBIDDEN",
                reason="Mandate liveness is evaluated once at admission (evaluated_at <= mandate_exp); complete_in_progress must not abort mid-flight for post-admission expiry (#540).",
                details={
                    "evaluated_at_epoch": evaluated_at,
                    "mandate_exp_epoch": mandate_exp,
                    "completed_at_epoch": completed_at,
                    "admission_result": admission_result,
                    "aborted_for_post_admission_expiry": aborted_for_post_admission_expiry,
                },
            )
    else:
        if (
            admission_result != "MANDATE_EXPIRED"
            or mandate_eval.get("checkout_status") != "canceled"
            or mandate_eval.get("error_code") != "mandate_expired"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_EXPIRED_AT_ADMISSION_MUST_CANCEL",
                reason="When evaluated_at > mandate_exp at admission, checkout must cancel with mandate_expired (#540).",
                details=dict(mandate_eval),
            )

    return_policy = payload.get("return_policy", {})
    if not isinstance(return_policy, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_RETURN_POLICY_INVALID",
            reason="return_policy must be a mapping (#966).",
            details={},
        )

    eligibility = return_policy.get("eligibility")
    if eligibility not in UCP_RETURN_ELIGIBILITIES:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_RETURN_ELIGIBILITY_OMITTED_OR_INVALID",
            reason="return_policy.eligibility must be explicitly 'window', 'unlimited', or 'not_accepted' (omitted != unlimited, #966).",
            details={"eligibility": eligibility},
        )

    anchor = return_policy.get("anchor", "delivered")
    if (
        return_policy.get("platform_computed_expires_at") is True
        or anchor not in UCP_RETURN_ANCHORS
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_RETURN_PLATFORM_COMPUTED_EXPIRES_AT_FORBIDDEN",
            reason="Business must state expires_at directly; platforms must not compute dates from duration + anchor, and anchors are restricted to purchased/fulfilled/delivered (#966).",
            details=dict(return_policy),
        )

    charged_fee = return_policy.get("charged_return_fee_minor", 0)
    stated_max_fee = return_policy.get("stated_max_return_fee_minor", 0)
    if (
        not isinstance(charged_fee, int)
        or not isinstance(stated_max_fee, int)
        or charged_fee > stated_max_fee
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_RETURN_FEE_EXCEEDS_STATED_MAXIMUM",
            reason="Charged return fee cannot exceed the business-stated fee maximum (#966).",
            details={
                "charged_return_fee_minor": charged_fee,
                "stated_max_return_fee_minor": stated_max_fee,
            },
        )

    quote_state = payload.get("quote_extension", {})
    if isinstance(quote_state, Mapping):
        if (
            quote_state.get("complete_includes_redundant_accepted_id") is True
            or quote_state.get("quote_totals_entries_count", 1) > 1
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_QUOTE_COMPLETE_INVARIANT_VIOLATION",
                reason="Complete Checkout must omit redundant accepted_id and emit at most one totals[type='quote'] entry (#930).",
                details=dict(quote_state),
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_MANDATE_TTL_RETURN_AND_QUOTE_VERIFIED",
        reason="UCP #540 admission-only mandate TTL, #966 explicit return policy, and #930 quote invariants verified.",
        details={"admission_result": admission_result, "eligibility": eligibility},
    )


def validate_x402_response_provenance_and_paywall_routing_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate x402 Foundation #3304 response-provenance, #3855 paywall XSS, #3857 encoded path routing, and #3858 batch settlement."""
    provenance = payload.get("response_provenance", {})
    if not isinstance(provenance, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="X402_PROVENANCE_INVALID",
            reason="response_provenance must be a mapping (#3304).",
            details={},
        )

    fixed_point = provenance.get("fixed_point")
    response_hash = provenance.get("response_hash")
    verification_outcome = provenance.get("verification_outcome")
    verifier_self_proof_passed = provenance.get("verifier_self_proof_passed", False)

    if response_hash is None:
        if verification_outcome != "no_claim":
            return GuardDecision(
                allowed=False,
                decision_code="X402_PROVENANCE_NO_COLLAPSE_VIOLATION",
                reason="Absence of responseHash must produce 'no_claim', never 'contradicted' (#3304).",
                details={"verification_outcome": verification_outcome},
            )
    else:
        if (
            not isinstance(fixed_point, Mapping)
            or set(fixed_point.keys()) != X402_PROVENANCE_FIXED_POINT_KEYS
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_PROVENANCE_FIXED_POINT_KEYS_INVALID",
                reason="response-provenance fixedPoint must contain exactly {endpoint, inputs, result, method, dataVintage} (#3304).",
                details={
                    "keys": list(fixed_point.keys())
                    if isinstance(fixed_point, Mapping)
                    else None
                },
            )
        if verifier_self_proof_passed is not True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_PROVENANCE_SELF_PROOF_REQUIRED",
                reason="Verifier must pass pinned golden-vector RFC 8785 self-proof before stating a verdict (#3304).",
                details={"verifier_self_proof_passed": verifier_self_proof_passed},
            )
        expected_hash = compute_jcs_sha256_hex(fixed_point)
        if response_hash != expected_hash:
            return GuardDecision(
                allowed=False,
                decision_code="X402_RESPONSE_PROVENANCE_HASH_MISMATCH",
                reason="responseHash does not match sha256(jcs(fixedPoint)) (#3304).",
                details={
                    "response_hash": response_hash,
                    "expected_hash": expected_hash,
                },
            )

    paywall_script_json = payload.get("paywall_inline_config_json", "")
    if not isinstance(paywall_script_json, str) or "<" in paywall_script_json:
        return GuardDecision(
            allowed=False,
            decision_code="X402_PAYWALL_UNESCAPED_SCRIPT_TAG",
            reason="Inline script paywall configuration must escape '<' to prevent reflected XSS (#3855).",
            details={"paywall_inline_config_json": paywall_script_json},
        )

    route_check = payload.get("legacy_route_match", {})
    if isinstance(route_check, Mapping):
        raw_path = str(route_check.get("raw_path", ""))
        served_unpaid = route_check.get("served_unpaid", False)
        has_encoded_sep = any(
            tok in raw_path for tok in ("%2F", "%2f", "%5C", "%5c", "\\")
        )
        if has_encoded_sep and served_unpaid is True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_ENCODED_PATH_SEPARATOR_BYPASS",
                reason="Encoded path separators (%2F/%5C) in parameterized routes must match raw path and require 402 payment (#3857).",
                details=dict(route_check),
            )

    batch_settle = payload.get("batch_settlement", {})
    if isinstance(batch_settle, Mapping):
        if (
            batch_settle.get("refund_carried_claims") is True
            and batch_settle.get("pending_settle_after_refund") is not True
        ) or batch_settle.get("stop_flush_calls_settle") is not True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_BATCH_SETTLEMENT_REFUND_OR_FLUSH_SKIPPED",
                reason="refundChannel with claims must set pendingSettle and stop({flush: true}) must invoke settle() (#3858).",
                details=dict(batch_settle),
            )

    return GuardDecision(
        allowed=True,
        decision_code="X402_PROVENANCE_PAYWALL_AND_SETTLEMENT_VERIFIED",
        reason="x402 #3304 response-provenance, #3855 XSS serializer, #3857 route matching, and #3858 batch settlement verified.",
        details={},
    )


def validate_tau2_knowledge_sandbox_and_voice_bayes_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Sierra tau2-bench 2.0 #653 minimal sandbox env, #655 root-walk denyRead, #640 voice call quality, and #652 Bayes@N."""
    sandbox = payload.get("knowledge_sandbox", {})
    if not isinstance(sandbox, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SANDBOX_CONFIG_INVALID",
            reason="knowledge_sandbox must be a mapping (#653/#655).",
            details={},
        )

    env_vars = sandbox.get("env_vars", {})
    sandbox_dir = sandbox.get("sandbox_dir")
    if (
        not isinstance(env_vars, Mapping)
        or not isinstance(sandbox_dir, str)
        or not sandbox_dir
    ):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SANDBOX_CONFIG_INVALID",
            reason="env_vars and sandbox_dir are required (#653).",
            details={},
        )

    if env_vars.get("HOME") != sandbox_dir:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
            reason="Sandbox HOME must be overridden to the per-sandbox directory (#653).",
            details={"HOME": env_vars.get("HOME"), "sandbox_dir": sandbox_dir},
        )

    for key in env_vars:
        if not isinstance(key, str):
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
                reason="Sandbox env keys must be strings (#653).",
                details={"key": key},
            )
        if SECRET_NAME_RE.search(key):
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
                reason="Sandbox environment must strip any variable matching KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PRIVATE|AUTH (#653).",
                details={"leaked_env_key": key},
            )
        if key not in TAU2_SANDBOX_BASE_ENV_KEYS and not key.startswith("LC_"):
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
                reason="Sandbox environment must only include the minimal allowlist (#653).",
                details={"disallowed_env_key": key},
            )

    stdout_text = str(sandbox.get("stdout", ""))
    stderr_text = str(sandbox.get("stderr", ""))
    parent_secrets = sandbox.get("parent_secret_values", [])
    if isinstance(parent_secrets, list):
        for secret in parent_secrets:
            if isinstance(secret, str) and len(secret) >= 8:
                if secret in stdout_text or secret in stderr_text:
                    return GuardDecision(
                        allowed=False,
                        decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
                        reason="Parent secret env values (>=8 chars) must be scrubbed to [REDACTED] in stdout/stderr (#653).",
                        details={},
                    )

    deny_read = sandbox.get("deny_read", [])
    if not isinstance(deny_read, list) or any(
        isinstance(p, str) and p.startswith("~") for p in deny_read
    ):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SANDBOX_ENV_OR_SECRET_LEAK",
            reason="Tilde paths in denyRead must be expanded to real user home absolute paths before overriding HOME (#653).",
            details={"deny_read": deny_read},
        )

    required_denied_paths = sandbox.get("required_outside_kb_denies", [])
    deny_set = {str(p) for p in deny_read}
    if not isinstance(required_denied_paths, list) or not required_denied_paths:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SANDBOX_OUTSIDE_KB_READ_EXPOSED",
            reason="required_outside_kb_denies must list paths outside knowledge_base (#655).",
            details={},
        )
    for req_path in required_denied_paths:
        if str(req_path) not in deny_set:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_SANDBOX_OUTSIDE_KB_READ_EXPOSED",
                reason="_compute_read_denies must deny reads outside knowledge_base (including data_dir, repo_root, /tmp, /etc/passwd) (#655).",
                details={"missing_deny_path": req_path},
            )

    voice_quality = payload.get("voice_v2_call_quality", {})
    if isinstance(voice_quality, Mapping):
        flags = int(voice_quality.get("interaction_flag_count", 0))
        bad_ratio = float(voice_quality.get("experience_bad_utterance_ratio", 0.0))
        passed = voice_quality.get("call_quality_passed", False)
        if (flags >= 2 or bad_ratio > 0.25) and passed is True:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_VOICE_CALL_QUALITY_GATE_BYPASSED",
                reason="voice-v2 call fails when interaction_flag_count >= 2 or experience_bad_utterance_ratio > 0.25 (#640).",
                details=dict(voice_quality),
            )

    bayes = payload.get("bayes_at_n_cohort", {})
    if isinstance(bayes, Mapping):
        if (
            bayes.get("duplicate_trials", 0) != 0
            or bayes.get("missing_grades", 0) != 0
            or bayes.get("infra_error_trials", 0) != 0
        ):
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_BAYES_AT_N_COHORT_INVALID",
                reason="Bayes@N requires zero duplicate trials, zero missing grades, and zero infrastructure errors (#652).",
                details=dict(bayes),
            )

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_SANDBOX_VOICE_AND_BAYES_VERIFIED",
        reason="Sierra tau2-bench 2.0 #653 minimal sandbox env, #655 root-walk denyRead, #640 voice quality, and #652 Bayes@N verified.",
        details={},
    )
