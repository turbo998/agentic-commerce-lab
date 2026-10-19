"""Stage 48 deterministic guards for OpenAI/Stripe ACP & Visa TAP 2026-10-19 updates.

Covers:
1. ACP PR #316 (SEP #303 ATDRP-0.1 Agentic Transaction Dispute Resolution Extension):
   - Authorization chain binding:
     `payment_mandate.transaction_id == checkout_hash == checkout_receipt.reference == payment_receipt.reference`
     plus `payment_receipt.transaction_id == ledger_settlement_tx_id`.
   - Section 7.4a fail-closed evidence-pack artifact admissibility table:
     `digest_ok`, `rfc3161_verified`, `producer_present`, `producer_trusted`,
     `self_asserted_only`, `key_unresolved`, `no_record`.
     Only `digest_ok + rfc3161_verified + producer_present + producer_trusted` are admissible.
     Missing timestamp (`digest_ok` without `rfc3161_verified`), self-asserted-only,
     unresolved DID/JWK (`key_unresolved`), or digest mismatch are rejected (`admissible=False`).
   - Section 7.4 deterministic per-line decision rule:
     * Pro-rata order-level adjustment allocation across lines; if `net_allocated <= 0`,
       the line is moot (`uphold`, `overturned_amount = 0`).
     * Missing/invalid mandate, expired mandate (`settled_at > mandate.expires_at`), or
       reused single-use mandate -> `overturn` (full net allocated amount).
     * `settled > authorized_max` -> `partial_overturn` for `min(settled - authorized_max, net_allocated)`.
     * Valid authorization chain where instruction conflicts with signed cart ->
       `uphold` merchant settlement (do NOT reverse merchant charge) and record
       `agent_platform_finding = True` against the agent platform.
   - Decision artifact schema invariants:
     * `prohibited_screened` MUST be `True` (const).
     * `signer` MUST identify a named natural person (`natural_person=True`, non-role name)
       distinct from automated `drafted_by`, and `seal.verify_url` MUST be `https://`.
2. ACP PRs #288/#287/#285 (`Signature` + `Timestamp` required on `delegate_payment`,
   `Signature` required on `delegate_authentication`), PR #296 (`meta.idempotency_key`
   on mutating MCP checkout tools), PR #275 (`DelegateAuthenticationSessionBase` optional
   `authentication_result`), PR #238 (`session_context` raw telemetry object vs
   `delegate_payment.risk_signals` fraud score array), and PR #237 (`app_links`
   Embedded App Deep Links registered scheme verification & web checkout fallback).
3. Visa TAP PR #21 (RFC 9421 `@signature-params` final line without trailing newline,
   individually quoted covered components, algorithm-key type enforcement, and
   verify-before-recording nonce cache keyed to `expires - created <= 480s`) and
   PR #18 (explicit `DIDResolverRegistry` for `did:web:` / `did:tenzro:` and Hybrid PQ
   `ed25519-ml-dsa-65` dual-leg signature verification `64B || 3309B = 3373B` with
   `1952B` FIPS 204 ML-DSA-65 verifying key, fail-closed `503` when `oqs` unavailable).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping

ROLE_ONLY_SIGNER_PATTERNS: tuple[str, ...] = (
    "dispute desk",
    "compliance team",
    "risk engine",
    "auto-adjudicator",
    "arbitration bot",
    "operations queue",
    "department",
)

MUTATING_MCP_CHECKOUT_TOOLS: frozenset[str] = frozenset(
    {
        "create_checkout",
        "update_checkout",
        "complete_checkout",
        "cancel_checkout",
    }
)

FORBIDDEN_SESSION_CONTEXT_RISK_KEYS: frozenset[str] = frozenset(
    {
        "risk_signals",
        "fraud_score",
        "trust_tier",
        "action",
        "score",
    }
)

FORBIDDEN_WEB_SCHEMES_IN_APP_LINKS: frozenset[str] = frozenset(
    {
        "http",
        "https",
        "javascript",
        "data",
        "file",
        "about",
    }
)

CUSTOM_APP_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]+$")


@dataclass(frozen=True)
class ACPATDRPDisputeResolutionGuardResult:
    admitted: bool
    decision_code: str
    auth_chain_valid: bool
    admissible_artifacts_count: int
    rejected_artifacts_count: int
    line_decisions: tuple[dict[str, Any], ...]
    total_overturned_minor: int
    agent_platform_finding_recorded: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ACPDelegateSignatureMCPIdempotencyDeepLinksGuardResult:
    admitted: bool
    decision_code: str
    delegate_headers_valid: bool
    mcp_idempotency_valid: bool
    session_context_separated: bool
    app_links_verified: bool
    fallback_checkout_preserved: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class VisaTAPRFC9421AndHybridPQDIDGuardResult:
    admitted: bool
    decision_code: str
    rfc9421_signature_base_valid: bool
    nonce_recorded_after_verify: bool
    did_resolver_valid: bool
    hybrid_pq_dual_leg_verified: bool
    http_status: int
    reasons: tuple[str, ...]


def evaluate_acp_atdrp_dispute_resolution_guard(
    context: Mapping[str, Any],
) -> ACPATDRPDisputeResolutionGuardResult:
    """Enforce ACP PR #316 (SEP #303 ATDRP-0.1) dispute resolution and admissibility rules."""
    reasons: list[str] = []

    # 1. Decision artifact schema invariants: prohibited_screened, named human signer, seal.verify_url
    prohibited_screened = context.get("prohibited_screened")
    if prohibited_screened is not True:
        reasons.append(
            "ATDRP_PROHIBITED_SCREENED_MUST_BE_TRUE: ATDRP-0.1 decision artifacts require `prohibited_screened: true`"
        )

    signer = context.get("signer")
    drafted_by = str(context.get("drafted_by", "")).strip()
    if not isinstance(signer, Mapping):
        reasons.append("ATDRP_SIGNER_MISSING: decision artifact must include a `signer` object")
    else:
        signer_name = str(signer.get("name", "")).strip()
        is_natural_person = bool(signer.get("natural_person", False))
        lowered_name = signer_name.lower()
        is_role_or_system = (
            not signer_name
            or not is_natural_person
            or any(pat in lowered_name for pat in ROLE_ONLY_SIGNER_PATTERNS)
            or (drafted_by and signer_name == drafted_by)
        )
        if is_role_or_system:
            reasons.append(
                "ATDRP_NON_HUMAN_OR_ROLE_SIGNER_BLOCKED: `signer` must identify a named natural person, not an automated system or role title"
            )

    seal = context.get("seal")
    if not isinstance(seal, Mapping) or not str(seal.get("verify_url", "")).startswith("https://"):
        reasons.append(
            "ATDRP_SEAL_VERIFY_URL_INVALID: `seal.verify_url` must be an absolute https:// verification endpoint"
        )

    # 2. Section 7.4a Evidence Pack Admissibility Table (fail-closed)
    evidence_artifacts = context.get("evidence_artifacts", ())
    admissible_count = 0
    rejected_count = 0
    require_all_evidence_admissible = bool(context.get("require_all_evidence_admissible", False))

    if isinstance(evidence_artifacts, (list, tuple)):
        for idx, art in enumerate(evidence_artifacts):
            if not isinstance(art, Mapping):
                rejected_count += 1
                reasons.append(f"ATDRP_ARTIFACT_INVALID[{idx}]: must be an object")
                continue
            digest_ok = bool(art.get("digest_ok", False))
            rfc3161_verified = bool(art.get("rfc3161_verified", False))
            producer_present = bool(art.get("producer_present", False))
            producer_trusted = bool(art.get("producer_trusted", False))
            self_asserted_only = bool(art.get("self_asserted_only", False))
            key_unresolved = bool(art.get("key_unresolved", False))
            no_record = bool(art.get("no_record", False))

            is_admissible = (
                digest_ok
                and rfc3161_verified
                and producer_present
                and producer_trusted
                and not self_asserted_only
                and not key_unresolved
                and not no_record
            )
            if is_admissible:
                admissible_count += 1
            else:
                rejected_count += 1
                if require_all_evidence_admissible:
                    reasons.append(
                        f"ATDRP_INADMISSIBLE_EVIDENCE_ARTIFACT_BLOCKED[{idx}]: failed Section 7.4a fail-closed admissibility check "
                        f"(digest_ok={digest_ok}, rfc3161_verified={rfc3161_verified}, producer_present={producer_present}, "
                        f"producer_trusted={producer_trusted}, self_asserted_only={self_asserted_only}, key_unresolved={key_unresolved})"
                    )

    # 3. Authorization chain binding check
    auth_chain = context.get("authorization_chain", {})
    auth_chain_valid = True
    if isinstance(auth_chain, Mapping) and auth_chain:
        mandate_tx_id = str(auth_chain.get("payment_mandate_transaction_id", "")).strip()
        checkout_hash = str(auth_chain.get("checkout_hash", "")).strip()
        checkout_receipt_ref = str(auth_chain.get("checkout_receipt_reference", "")).strip()
        payment_receipt_ref = str(auth_chain.get("payment_receipt_reference", "")).strip()
        payment_receipt_tx_id = str(auth_chain.get("payment_receipt_transaction_id", "")).strip()
        ledger_tx_id = str(auth_chain.get("ledger_settlement_tx_id", "")).strip()

        if not (
            mandate_tx_id
            and mandate_tx_id == checkout_hash == checkout_receipt_ref == payment_receipt_ref
            and payment_receipt_tx_id
            and payment_receipt_tx_id == ledger_tx_id
        ):
            auth_chain_valid = False
            if bool(context.get("require_valid_authorization_chain", False)):
                reasons.append(
                    "ATDRP_AUTHORIZATION_CHAIN_BROKEN: payment_mandate.transaction_id, checkout_hash, "
                    "checkout_receipt.reference, and payment_receipt.reference must match, and payment_receipt.transaction_id "
                    "must match ledger_settlement_tx_id"
                )

    # 4. Section 7.4 Deterministic Per-Line Decision Rule
    disputed_lines = context.get("disputed_lines", ())
    order_gross_minor = int(context.get("order_gross_minor", 0))
    order_level_adjustments_minor = int(context.get("order_level_adjustments_minor", 0))

    line_decisions: list[dict[str, Any]] = []
    total_overturned_minor = 0
    agent_platform_finding_recorded = False

    if isinstance(disputed_lines, (list, tuple)):
        for idx, line in enumerate(disputed_lines):
            if not isinstance(line, Mapping):
                continue
            line_id = str(line.get("line_id", f"line_{idx}"))
            gross_settled = int(line.get("gross_settled_minor", 0))
            direct_adjustments = int(line.get("direct_adjustments_minor", 0))

            # Pro-rata order-level adjustment share
            if order_gross_minor > 0 and order_level_adjustments_minor > 0:
                pro_rata_adj = (order_level_adjustments_minor * gross_settled) // order_gross_minor
            else:
                pro_rata_adj = int(line.get("pro_rata_order_adjustment_minor", 0))

            net_allocated = gross_settled - direct_adjustments - pro_rata_adj
            mandate_present = bool(line.get("mandate_present", True))
            mandate_expired = bool(line.get("mandate_expired", False))
            mandate_reused = bool(line.get("mandate_reused", False))
            authorized_max = int(line.get("authorized_max_minor", gross_settled))
            instruction_conflicts_with_cart = bool(line.get("instruction_conflicts_with_cart", False))
            proposed_disposition = line.get("proposed_disposition")
            proposed_overturn_minor = line.get("proposed_overturn_minor")
            merchant_charge_reversed_on_instruction_conflict = bool(
                line.get("merchant_charge_reversed_on_instruction_conflict", False)
            )

            # Determine normative disposition per Section 7.4
            if net_allocated <= 0:
                expected_disposition = "uphold"
                expected_overturn = 0
                finding_against_agent = False
            elif (not auth_chain_valid) or (not mandate_present) or mandate_expired or mandate_reused:
                expected_disposition = "overturn"
                expected_overturn = net_allocated
                finding_against_agent = False
            elif gross_settled > authorized_max:
                excess = gross_settled - authorized_max
                expected_overturn = min(excess, net_allocated)
                expected_disposition = (
                    "overturn" if expected_overturn == net_allocated else "partial_overturn"
                )
                finding_against_agent = False
            elif instruction_conflicts_with_cart:
                # Valid authorization chain, but agent platform cart conflicted with buyer instruction:
                # uphold merchant charge, record finding against agent platform.
                expected_disposition = "uphold"
                expected_overturn = 0
                finding_against_agent = True
                agent_platform_finding_recorded = True
                if merchant_charge_reversed_on_instruction_conflict:
                    reasons.append(
                        f"ATDRP_INSTRUCTION_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN[{line_id}]: when authorization chain is valid "
                        "and buyer instruction conflicts with signed cart, merchant settlement must be upheld and finding recorded against agent platform"
                    )
            else:
                expected_disposition = "uphold"
                expected_overturn = 0
                finding_against_agent = False

            if proposed_disposition is not None and str(proposed_disposition) != expected_disposition:
                reasons.append(
                    f"ATDRP_LINE_DISPOSITION_MISMATCH[{line_id}]: proposed '{proposed_disposition}' != normative '{expected_disposition}'"
                )
            if proposed_overturn_minor is not None and int(proposed_overturn_minor) != expected_overturn:
                reasons.append(
                    f"ATDRP_LINE_OVERTURN_AMOUNT_MISMATCH[{line_id}]: proposed {proposed_overturn_minor} != normative {expected_overturn}"
                )

            total_overturned_minor += expected_overturn
            line_decisions.append(
                {
                    "line_id": line_id,
                    "net_allocated_minor": max(0, net_allocated),
                    "disposition": expected_disposition,
                    "overturned_minor": expected_overturn,
                    "agent_platform_finding": finding_against_agent,
                }
            )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "ACP_ATDRP_DISPUTE_RESOLUTION_VERIFIED"
    elif any("ATDRP_INADMISSIBLE_EVIDENCE_ARTIFACT_BLOCKED" in r for r in reasons):
        decision_code = "ATDRP_INADMISSIBLE_EVIDENCE_ARTIFACT_BLOCKED"
    elif any("ATDRP_NON_HUMAN_OR_ROLE_SIGNER_BLOCKED" in r or "ATDRP_PROHIBITED_SCREENED_MUST_BE_TRUE" in r for r in reasons):
        decision_code = "ATDRP_HUMAN_SIGNER_OR_PROHIBITED_SCREENING_VIOLATION"
    elif any("ATDRP_INSTRUCTION_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN" in r for r in reasons):
        decision_code = "ATDRP_INSTRUCTION_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN"
    elif any("ATDRP_LINE_" in r for r in reasons):
        decision_code = "ATDRP_DETERMINISTIC_DECISION_RULE_VIOLATION"
    else:
        decision_code = "ATDRP_AUTHORIZATION_CHAIN_OR_SEAL_INVALID"

    return ACPATDRPDisputeResolutionGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        auth_chain_valid=auth_chain_valid,
        admissible_artifacts_count=admissible_count,
        rejected_artifacts_count=rejected_count,
        line_decisions=tuple(line_decisions),
        total_overturned_minor=total_overturned_minor,
        agent_platform_finding_recorded=agent_platform_finding_recorded,
        reasons=tuple(reasons),
    )


def evaluate_acp_delegate_signature_mcp_idempotency_and_deep_links_guard(
    context: Mapping[str, Any],
) -> ACPDelegateSignatureMCPIdempotencyDeepLinksGuardResult:
    """Enforce ACP PRs #288/#287/#285, #296, #275, #238, and #237."""
    reasons: list[str] = []
    delegate_headers_valid = True
    mcp_idempotency_valid = True
    session_context_separated = True
    app_links_verified = True
    fallback_checkout_preserved = True

    # 1. Delegate Payment / Delegate Authentication required cryptographic headers (#288/#287/#285)
    endpoint = str(context.get("endpoint", "")).strip()
    headers = context.get("headers", {})
    if not isinstance(headers, Mapping):
        headers = {}

    sig_header = str(headers.get("Signature", "")).strip()
    ts_header = str(headers.get("Timestamp", "")).strip()
    signature_verified = bool(context.get("signature_verified", True))
    timestamp_skew_seconds = abs(int(context.get("timestamp_skew_seconds", 0)))
    max_timestamp_skew_seconds = int(context.get("max_timestamp_skew_seconds", 300))

    if endpoint == "/agentic_commerce/delegate_payment":
        if not sig_header or not ts_header or not signature_verified or timestamp_skew_seconds > max_timestamp_skew_seconds:
            delegate_headers_valid = False
            reasons.append(
                "ACP_DELEGATE_PAYMENT_SIGNATURE_OR_TIMESTAMP_INVALID: `/agentic_commerce/delegate_payment` requires valid `Signature` and fresh `Timestamp` headers"
            )
    elif endpoint.startswith("/agentic_commerce/delegate_authentication"):
        if not sig_header or not signature_verified:
            delegate_headers_valid = False
            reasons.append(
                "ACP_DELEGATE_AUTH_SIGNATURE_MISSING_OR_INVALID: `delegate_authentication` endpoints require a valid `Signature` header"
            )

    # 2. DelegateAuthenticationSessionBase optional authentication_result (#275)
    auth_session = context.get("delegate_authentication_session")
    if isinstance(auth_session, Mapping):
        auth_status = str(auth_session.get("status", "")).strip()
        has_auth_result = auth_session.get("authentication_result") is not None
        if auth_status == "authenticated" and not has_auth_result:
            reasons.append(
                "ACP_DELEGATE_AUTH_RESULT_REQUIRED_WHEN_AUTHENTICATED: `authentication_result` is required once status == 'authenticated'"
            )
        if bool(auth_session.get("rejected_missing_auth_result_on_initial_create", False)):
            reasons.append(
                "ACP_DELEGATE_AUTH_INITIAL_RESULT_OVERCONSTRAINED: `authentication_result` must be optional on initial create before challenge completion"
            )

    # 3. MCP mutating checkout tools meta.idempotency_key & parity (#296)
    mcp_call = context.get("mcp_tool_call")
    if isinstance(mcp_call, Mapping):
        tool_name = str(mcp_call.get("tool_name", "")).strip()
        meta = mcp_call.get("meta", {})
        idemp_key = str(meta.get("idempotency_key", "")).strip() if isinstance(meta, Mapping) else ""
        reused_with_different_params = bool(mcp_call.get("reused_key_with_different_parameters", False))
        concurrent_duplicate_in_flight = bool(mcp_call.get("concurrent_duplicate_in_flight", False))
        expected_error_code = str(mcp_call.get("returned_error_code", "")).strip()

        if tool_name in MUTATING_MCP_CHECKOUT_TOOLS and not idemp_key:
            mcp_idempotency_valid = False
            reasons.append(
                f"ACP_MCP_MUTATING_TOOL_MISSING_IDEMPOTENCY_KEY: MCP tool '{tool_name}' requires `meta.idempotency_key`"
            )
        if reused_with_different_params and expected_error_code != "idempotency_conflict":
            mcp_idempotency_valid = False
            reasons.append(
                "ACP_MCP_IDEMPOTENCY_CONFLICT_UNENFORCED: reusing `meta.idempotency_key` with different parameters must return `idempotency_conflict`"
            )
        if concurrent_duplicate_in_flight and expected_error_code != "idempotency_in_flight":
            mcp_idempotency_valid = False
            reasons.append(
                "ACP_MCP_IDEMPOTENCY_IN_FLIGHT_UNENFORCED: concurrent duplicate `meta.idempotency_key` must return `idempotency_in_flight`"
            )

    # 4. session_context raw telemetry object vs delegate_payment.risk_signals (#238)
    session_context = context.get("session_context")
    if session_context is not None:
        if not isinstance(session_context, Mapping):
            session_context_separated = False
            reasons.append("ACP_SESSION_CONTEXT_NOT_OBJECT: `session_context` must be a structured object")
        else:
            leaked_risk_keys = sorted(k for k in session_context.keys() if str(k) in FORBIDDEN_SESSION_CONTEXT_RISK_KEYS)
            if leaked_risk_keys:
                session_context_separated = False
                reasons.append(
                    f"ACP_SESSION_CONTEXT_CONFLATED_WITH_RISK_SIGNALS: `session_context` must only carry raw device/session telemetry, not fraud scores {leaked_risk_keys}"
                )
            device = session_context.get("device")
            if isinstance(device, Mapping):
                tz = str(device.get("timezone", "")).strip()
                if tz and ("/" not in tz or tz.startswith(("UTC+", "UTC-", "GMT+", "GMT-"))):
                    session_context_separated = False
                    reasons.append(
                        f"ACP_SESSION_CONTEXT_TIMEZONE_NOT_IANA: `device.timezone` '{tz}' must be an IANA timezone identifier"
                    )

    # 5. Embedded App Deep Links `app_links` scheme verification & fallback (#237)
    app_links = context.get("app_links")
    registered_schemes = {
        str(s).strip().lower() for s in context.get("registered_app_schemes", ()) if str(s).strip()
    }
    if isinstance(app_links, Mapping):
        for field_name in ("ios_url", "android_url", "universal_url"):
            raw_url = app_links.get(field_name)
            if raw_url is None:
                continue
            url_str = str(raw_url).strip()
            if field_name == "universal_url":
                if not url_str.startswith("https://") or len(url_str) > 2048:
                    app_links_verified = False
                    reasons.append(
                        "ACP_APP_LINKS_UNIVERSAL_URL_INVALID: `universal_url` must be an https:// URL <= 2048 chars"
                    )
            else:
                scheme = url_str.split("://", 1)[0].lower() if "://" in url_str else ""
                if (
                    not CUSTOM_APP_SCHEME_RE.match(url_str)
                    or len(url_str) > 2048
                    or scheme in FORBIDDEN_WEB_SCHEMES_IN_APP_LINKS
                    or (registered_schemes and scheme not in registered_schemes)
                ):
                    app_links_verified = False
                    reasons.append(
                        f"ACP_APP_LINKS_UNREGISTERED_OR_WEB_SCHEME_BLOCKED[{field_name}]: '{url_str}' must use a verified registered custom app scheme"
                    )

        if bool(context.get("deep_link_cancelled_or_failed", False)):
            if not bool(context.get("fell_back_to_embedded_web_checkout", False)) or bool(
                context.get("checkout_session_aborted_on_deep_link_cancel", False)
            ):
                fallback_checkout_preserved = False
                reasons.append(
                    "ACP_APP_LINKS_FALLBACK_BROKEN: when native app deep link fails or is cancelled, agent must fall back to embedded web checkout without aborting the session"
                )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "ACP_DELEGATE_SIGNATURE_MCP_IDEMPOTENCY_AND_DEEP_LINKS_VERIFIED"
    elif not delegate_headers_valid:
        decision_code = "ACP_DELEGATE_SIGNATURE_OR_TIMESTAMP_HEADER_BLOCKED"
    elif not mcp_idempotency_valid:
        decision_code = "ACP_MCP_IDEMPOTENCY_KEY_OR_CONFLICT_BLOCKED"
    elif not session_context_separated:
        decision_code = "ACP_SESSION_CONTEXT_RISK_SIGNAL_CONFLATION_BLOCKED"
    elif not app_links_verified or not fallback_checkout_preserved:
        decision_code = "ACP_APP_LINKS_UNREGISTERED_SCHEME_OR_FALLBACK_BLOCKED"
    else:
        decision_code = "ACP_DELEGATE_AUTH_SESSION_SCHEMA_VIOLATION"

    return ACPDelegateSignatureMCPIdempotencyDeepLinksGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        delegate_headers_valid=delegate_headers_valid,
        mcp_idempotency_valid=mcp_idempotency_valid,
        session_context_separated=session_context_separated,
        app_links_verified=app_links_verified,
        fallback_checkout_preserved=fallback_checkout_preserved,
        reasons=tuple(reasons),
    )


def evaluate_visa_tap_rfc9421_and_hybrid_pq_did_guard(
    context: Mapping[str, Any],
) -> VisaTAPRFC9421AndHybridPQDIDGuardResult:
    """Enforce Visa TAP PR #21 (RFC 9421 signature base & nonce cache) and PR #18 (Hybrid PQ & DID resolver)."""
    reasons: list[str] = []
    rfc9421_signature_base_valid = True
    nonce_recorded_after_verify = True
    did_resolver_valid = True
    hybrid_pq_dual_leg_verified = True
    http_status = 200

    # 1. RFC 9421 Signature Base & Algorithm-Key Binding (Visa TAP PR #21)
    signature_base = str(context.get("signature_base", ""))
    covered_components = tuple(str(c) for c in context.get("covered_components", ("@authority", "@path")))
    created = int(context.get("created", 0))
    expires = int(context.get("expires", 0))
    alg = str(context.get("alg", "ed25519")).strip()
    key_type = str(context.get("key_type", "Ed25519")).strip()

    if signature_base:
        if signature_base.endswith("\n") or "\r\n" in signature_base:
            rfc9421_signature_base_valid = False
            http_status = 401
            reasons.append(
                "VISA_TAP_RFC9421_TRAILING_NEWLINE_OR_CRLF_FORBIDDEN: RFC 9421 signature base must not end with a trailing newline or use CRLF"
            )
        lines = signature_base.split("\n")
        if not lines or not lines[-1].startswith('"@signature-params": ('):
            rfc9421_signature_base_valid = False
            http_status = 401
            reasons.append(
                'VISA_TAP_RFC9421_SIGNATURE_PARAMS_LINE_MALFORMED: final line must be `"@signature-params": ("@authority" "@path" ...);created=...`'
            )
        else:
            expected_quoted = " ".join(f'"{c}"' for c in covered_components)
            if f"({expected_quoted})" not in lines[-1]:
                rfc9421_signature_base_valid = False
                http_status = 401
                reasons.append(
                    f"VISA_TAP_RFC9421_COVERED_COMPONENTS_QUOTING_INVALID: covered components must be individually quoted as ({expected_quoted})"
                )

    if expires <= created or (expires - created) > 480:
        rfc9421_signature_base_valid = False
        http_status = 401
        reasons.append(
            f"VISA_TAP_WINDOW_INVALID: expires ({expires}) - created ({created}) must be positive and <= 480 seconds"
        )

    # Algorithm-to-key-type enforcement (prevent algorithm confusion)
    expected_key_types = {
        "ed25519": "Ed25519",
        "ecdsa-p256-sha256": "EC_P256",
        "ecdsa-p384-sha384": "EC_P384",
        "rsa-pss-sha256": "RSA",
        "ed25519-ml-dsa-65": "HybridEd25519MLDSA65",
    }
    if alg not in expected_key_types or expected_key_types[alg] != key_type:
        rfc9421_signature_base_valid = False
        http_status = 401
        reasons.append(
            f"VISA_TAP_ALG_KEY_TYPE_CONFUSION_BLOCKED: alg '{alg}' incompatible with key_type '{key_type}'"
        )

    # 2. Verify-before-recording nonce cache (PR #21)
    nonce = str(context.get("nonce", "")).strip()
    seen_nonces = {str(n) for n in context.get("seen_nonces", ())}
    recorded_nonce_before_crypto_verify = bool(context.get("recorded_nonce_before_crypto_verify", False))
    crypto_signature_valid = bool(context.get("crypto_signature_valid", True))

    if recorded_nonce_before_crypto_verify:
        nonce_recorded_after_verify = False
        http_status = 401
        reasons.append(
            "VISA_TAP_PRE_VERIFY_NONCE_POISONING_VULNERABILITY_BLOCKED: nonce must only be recorded after cryptographic signature verification succeeds"
        )
    if not nonce or nonce in seen_nonces:
        nonce_recorded_after_verify = False
        http_status = 401
        reasons.append("VISA_TAP_NONCE_REPLAY_DETECTED: nonce is missing or already recorded in active window")
    if not crypto_signature_valid:
        http_status = 401
        reasons.append("VISA_TAP_SIGNATURE_CRYPTO_VERIFY_FAILED: cryptographic signature verification failed")

    # 3. Explicit DIDResolverRegistry for did:web: / did:tenzro: (PR #18)
    keyid = str(context.get("keyid", "")).strip()
    if keyid.startswith("did:"):
        did_registry_configured = bool(context.get("did_registry_configured", False))
        registered_did_methods = {str(m) for m in context.get("registered_did_methods", ())}
        did_method = ":".join(keyid.split(":", 2)[:2]) if keyid.count(":") >= 2 else ""
        did_verification_method_found = bool(context.get("did_verification_method_found", True))

        if not did_registry_configured or did_method not in registered_did_methods or not did_verification_method_found:
            did_resolver_valid = False
            http_status = 401
            reasons.append(
                f"VISA_TAP_DID_RESOLUTION_FAILED: keyid '{keyid}' requires an explicit DIDResolverRegistry with method '{did_method}' and matching verificationMethod"
            )

    # 4. Hybrid PQ `ed25519-ml-dsa-65` dual-leg verification (`64B || 3309B = 3373B`, `1952B` PK) (PR #18)
    if alg == "ed25519-ml-dsa-65":
        oqs_runtime_available = bool(context.get("oqs_runtime_available", True))
        signature_byte_length = int(context.get("signature_byte_length", 3373))
        mldsa65_public_key_byte_length = int(context.get("mldsa65_public_key_byte_length", 1952))
        ed25519_leg_valid = bool(context.get("ed25519_leg_valid", True))
        mldsa65_leg_valid = bool(context.get("mldsa65_leg_valid", True))

        if not oqs_runtime_available:
            hybrid_pq_dual_leg_verified = False
            http_status = 503
            reasons.append(
                "VISA_TAP_HYBRID_PQ_RUNTIME_UNAVAILABLE_FAIL_CLOSED_503: ML-DSA-65 runtime unavailable; must fail closed with HTTP 503 rather than downgrading to classical Ed25519"
            )
        else:
            if signature_byte_length != 3373:
                hybrid_pq_dual_leg_verified = False
                http_status = 401
                reasons.append(
                    f"VISA_TAP_HYBRID_PQ_SIGNATURE_LENGTH_INVALID: expected 3373 bytes (64B Ed25519 || 3309B ML-DSA-65), got {signature_byte_length}"
                )
            if mldsa65_public_key_byte_length != 1952:
                hybrid_pq_dual_leg_verified = False
                http_status = 401
                reasons.append(
                    f"VISA_TAP_HYBRID_PQ_PUBLIC_KEY_LENGTH_INVALID: expected 1952-byte FIPS 204 ML-DSA-65 public key, got {mldsa65_public_key_byte_length}"
                )
            if not (ed25519_leg_valid and mldsa65_leg_valid):
                hybrid_pq_dual_leg_verified = False
                http_status = 401
                reasons.append(
                    f"VISA_TAP_HYBRID_PQ_SINGLE_LEG_FORGERY_BLOCKED: both Ed25519 ({ed25519_leg_valid}) and ML-DSA-65 ({mldsa65_leg_valid}) legs must verify"
                )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "VISA_TAP_RFC9421_AND_HYBRID_PQ_DID_VERIFIED"
    elif http_status == 503:
        decision_code = "VISA_TAP_HYBRID_PQ_RUNTIME_UNAVAILABLE_FAIL_CLOSED_503"
    elif not hybrid_pq_dual_leg_verified:
        decision_code = "VISA_TAP_HYBRID_PQ_DUAL_LEG_OR_LENGTH_BLOCKED"
    elif not did_resolver_valid:
        decision_code = "VISA_TAP_DID_RESOLVER_OR_KEYID_BLOCKED"
    elif not nonce_recorded_after_verify:
        decision_code = "VISA_TAP_NONCE_REPLAY_OR_PRE_VERIFY_POISONING_BLOCKED"
    else:
        decision_code = "VISA_TAP_RFC9421_SIGNATURE_BASE_OR_ALG_CONFUSION_BLOCKED"

    return VisaTAPRFC9421AndHybridPQDIDGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        rfc9421_signature_base_valid=rfc9421_signature_base_valid,
        nonce_recorded_after_verify=nonce_recorded_after_verify,
        did_resolver_valid=did_resolver_valid,
        hybrid_pq_dual_leg_verified=hybrid_pq_dual_leg_verified,
        http_status=http_status,
        reasons=tuple(reasons),
    )
