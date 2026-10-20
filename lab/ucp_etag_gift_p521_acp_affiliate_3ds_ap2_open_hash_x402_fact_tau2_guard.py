"""Stage 100 deterministic guardrails across UCP, ACP, Google AP2, Coinbase x402, and Sierra tau2-bench.

Covers:
1. UCP PR #628 (`ETag`/`If-Match` conditional writes & `search_catalog`/`lookup_catalog` standard error envelope),
   PR #625 (`profile.json` `P-521` <-> `ES512` curve-to-algorithm pairing),
   PR #540 (`com.merchantstamp.mandate-evaluation` AP2 TTL at admission), and
   PR #508 (`dev.ucp.shopping.gift` recipient-required gift checkout).
2. ACP PR #57 (Affiliate Attribution write-only multi-touch transport & PII/idempotency rules),
   PR #66 (Merchant 3DS Execution `3ds_method` & `3ds_challenge` state machine), and
   PR #45 (Hotel discovery & live rate hydration `quote_token` revalidation).
3. Google AP2 PR #279 (`open_mandate_hash` RFC 8785 JCS derivation over unsigned claims) &
   PR #278 (Entropy-based `checkout_hash` payload requirement), plus
   Coinbase x402 PR #225 (Independent Fact Attestation extension) &
   PR #206 (Public testnet facilitator mainnet 500 routing guard).
4. Sierra tau2-bench PR #513 (Banking `banking_knowledge` write-critic & nested JSON arg comparison),
   PR #484 (`close_bank_account_7392` fixed-set `reason` validation),
   PR #516 (`Tool` / `ToolKitBase` Pydantic kwarg coercion), and
   PR #508 (`SOLO_AGENT_IMPLEMENTATIONS` `llm_agent_solo_gt` solo-mode re-grading detection).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

UCP_CURVE_TO_ALG: dict[str, str] = {
    "P-256": "ES256",
    "P-384": "ES384",
    "P-521": "ES512",
    "Ed25519": "EdDSA",
}

FORBIDDEN_GIFT_WIRE_FIELDS: frozenset[str] = frozenset(
    {
        "recipient_id",
        "selection_token",
        "friend_list",
        "recipient_email",
        "recipient_phone",
        "recipient_address",
    }
)

FORBIDDEN_AFFILIATE_PII_KEYS: frozenset[str] = frozenset(
    {
        "email",
        "buyer_email",
        "phone",
        "phone_number",
        "user_id",
        "ssn",
    }
)

TESTNET_ONLY_PUBLIC_FACILITATORS: frozenset[str] = frozenset(
    {
        "https://x402.org/facilitator",
        "https://x402.org/facilitator/",
    }
)

MAINNET_NETWORKS: frozenset[str] = frozenset(
    {
        "eip155:8453",  # Base Mainnet
        "eip155:1",  # Ethereum Mainnet
        "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",  # Solana Mainnet
    }
)

ALLOWED_BANK_CLOSURE_REASONS: frozenset[str] = frozenset(
    {
        "customer_request",
        "simplifying_finances",
        "moving_banks",
        "fees_too_high",
        "fraud_suspected",
        "other",
    }
)

SOLO_AGENT_IMPLEMENTATIONS: tuple[str, ...] = (
    "llm_agent_solo",
    "llm_agent_solo_gt",
)


def compute_rfc8785_jcs_sha256(claims_obj: dict[str, Any]) -> str:
    """Compute deterministic RFC 8785 JCS SHA-256 hex digest over unsigned mandate claims."""
    canonical = json.dumps(claims_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_ucp_conditional_writes_p521_mandate_ttl_and_gift_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #628 ETag/error envelope, #625 P-521/ES512, #540 AP2 mandate TTL at admission, and #508 gift checkout."""
    violations: list[str] = []

    # 1. UCP #628: ETag / If-Match conditional writes, 409 idempotency conflict, and catalog error envelope
    cw = payload.get("conditional_write", {})
    is_state_changing = bool(cw.get("is_state_changing", True))
    if_match = cw.get("if_match_header")
    current_etag = cw.get("current_etag")
    if is_state_changing and if_match is not None and current_etag is not None:
        if str(if_match) != str(current_etag):
            violations.append("UCP_628_IF_MATCH_ETAG_MISMATCH_412")
    if bool(cw.get("idempotency_key_reused", False)) and bool(cw.get("payload_digest_changed", False)):
        violations.append("UCP_628_IDEMPOTENCY_CONFLICT_409")

    cat_op = payload.get("catalog_operation", {})
    if bool(cat_op.get("request_cannot_be_served", False)):
        resp = cat_op.get("response", {})
        ucp_meta = resp.get("ucp", {}) if isinstance(resp, dict) else {}
        messages = resp.get("messages", []) if isinstance(resp, dict) else []
        if ucp_meta.get("status") != "error" or not isinstance(messages, list) or len(messages) == 0:
            violations.append("UCP_628_CATALOG_MISSING_STANDARD_ERROR_ENVELOPE")

    # 2. UCP #625: profile.json P-521 <-> ES512 curve-to-algorithm pairing
    for key_entry in payload.get("signing_keys", []):
        crv = str(key_entry.get("crv", ""))
        alg = key_entry.get("alg")
        expected_alg = UCP_CURVE_TO_ALG.get(crv)
        if expected_alg is not None and alg is not None and str(alg) != expected_alg:
            violations.append(f"UCP_625_CURVE_ALG_MISMATCH:{crv}!={alg}")

    # 3. UCP #540: AP2 mandate liveness evaluated once at admission of Complete Checkout
    me = payload.get("mandate_evaluation", {})
    evaluated_at = me.get("evaluated_at")
    mandate_exp = me.get("mandate_exp")
    checkout_status = str(me.get("checkout_status", "complete_in_progress"))
    post_admission_aborted = bool(me.get("aborted_after_admission_due_to_ttl", False))

    if isinstance(evaluated_at, int) and isinstance(mandate_exp, int):
        expired_at_admission = evaluated_at > mandate_exp
        if expired_at_admission and checkout_status != "canceled":
            violations.append("UCP_540_EXPIRED_AT_ADMISSION_MUST_TERMINATE_CANCELED")
        if not expired_at_admission and post_admission_aborted:
            violations.append("UCP_540_POST_ADMISSION_TTL_ABORT_FORBIDDEN")
    else:
        violations.append("UCP_540_INVALID_EPOCH_INTEGER_TIMESTAMPS")

    # 4. UCP #508: Recipient-required gift checkout
    gift_ctx = payload.get("gift_checkout", {})
    gift_obj = gift_ctx.get("gift", {})
    if isinstance(gift_obj, dict):
        for forbidden_key in FORBIDDEN_GIFT_WIRE_FIELDS:
            if forbidden_key in gift_obj:
                violations.append(f"UCP_508_WIRE_RECIPIENT_PII_OR_HANDLE_FORBIDDEN:{forbidden_key}")
        if bool(gift_obj.get("recipient_required", False)):
            recipient_selected = bool(gift_ctx.get("recipient_selected_on_business", False))
            status = str(gift_ctx.get("checkout_status", ""))
            continue_url = str(gift_ctx.get("continue_url", ""))
            if not recipient_selected:
                if status != "requires_escalation" or not continue_url.startswith("https://"):
                    violations.append("UCP_508_MISSING_RECIPIENT_ESCALATION_REQUIRED")
    complete_body = gift_ctx.get("complete_request_body", {})
    if isinstance(complete_body, dict) and "gift" in complete_body:
        violations.append("UCP_508_GIFT_FIELD_FORBIDDEN_IN_COMPLETE_REQUEST")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #57 affiliate attribution, #66 Merchant 3DS execution, and #45 hotel rate hydration."""
    violations: list[str] = []

    # 1. ACP #57: Affiliate Attribution write-only transport, touchpoint phase, PII & idempotency
    aff = payload.get("affiliate_attribution_context", {})
    endpoint_phase = str(aff.get("endpoint_phase", "create"))  # create | update | complete
    attr_req = aff.get("request_affiliate_attribution")
    if isinstance(attr_req, dict):
        touchpoint = str(attr_req.get("touchpoint", ""))
        if endpoint_phase == "create" and touchpoint != "first":
            violations.append("ACP_57_CREATE_REQUIRES_FIRST_TOUCHPOINT")
        elif endpoint_phase == "complete" and touchpoint != "last":
            violations.append("ACP_57_COMPLETE_REQUIRES_LAST_TOUCHPOINT")
        elif touchpoint not in {"first", "last"}:
            violations.append("ACP_57_INVALID_TOUCHPOINT_ENUM")

        token = str(attr_req.get("token", ""))
        if not token:
            violations.append("ACP_57_MISSING_ATTRIBUTION_TOKEN")

        metadata = attr_req.get("metadata", {})
        if isinstance(metadata, dict):
            for k, v in metadata.items():
                if str(k).lower() in FORBIDDEN_AFFILIATE_PII_KEYS or "@" in str(v):
                    violations.append(f"ACP_57_AFFILIATE_PII_LEAK_FORBIDDEN:{k}")

    resp_body = aff.get("response_body", {})
    if isinstance(resp_body, dict) and "affiliate_attribution" in resp_body:
        violations.append("ACP_57_AFFILIATE_ATTRIBUTION_ECHOED_IN_RESPONSE")

    if bool(aff.get("idempotency_key_reused", False)) and bool(aff.get("attribution_payload_changed", False)):
        if int(aff.get("http_status", 200)) != 409:
            violations.append("ACP_57_IDEMPOTENCY_PAYLOAD_CONFLICT_409_REQUIRED")

    # 2. ACP #66: Merchant 3DS Execution (`3ds_method` -> `3ds_challenge` -> `cres`)
    m3ds = payload.get("merchant_3ds", {})
    pending_action = str(m3ds.get("pending_action", "none"))
    if pending_action == "3ds_method":
        if not str(m3ds.get("method_url", "")).startswith("https://") or not str(
            m3ds.get("three_ds_server_trans_id", "")
        ):
            violations.append("ACP_66_3DS_METHOD_MISSING_URL_OR_TRANS_ID")
        if str(m3ds.get("method_completion_indicator", "")) not in {"Y", "N", "U"}:
            violations.append("ACP_66_3DS_METHOD_MISSING_COMPLETION_INDICATOR")
    elif pending_action == "3ds_challenge":
        if not str(m3ds.get("acs_url", "")).startswith("https://") or not str(m3ds.get("encoded_creq", "")):
            violations.append("ACP_66_3DS_CHALLENGE_MISSING_ACS_URL_OR_CREQ")
        if bool(m3ds.get("finalize_requested", False)) and not str(m3ds.get("cres", "")):
            violations.append("ACP_66_3DS_CHALLENGE_FINALIZE_WITHOUT_CRES")

    # 3. ACP #45: Hotel discovery & live rate hydration quote revalidation
    hotel = payload.get("hotel_checkout", {})
    if bool(hotel.get("used_static_catalog_price_only", False)):
        violations.append("ACP_45_STATIC_CATALOG_PRICE_USED_WITHOUT_HYDRATION_QUOTE")
    quote_token = str(hotel.get("quote_token", ""))
    quote_expires_at = int(hotel.get("quote_expires_at", 0))
    checkout_now = int(hotel.get("checkout_now", 0))
    if not quote_token or quote_expires_at <= checkout_now:
        violations.append("ACP_45_EXPIRED_OR_MISSING_HYDRATION_QUOTE_TOKEN")
    if not bool(hotel.get("cancellation_policy_snapshot_preserved", True)):
        violations.append("ACP_45_MISSING_CANCELLATION_POLICY_SNAPSHOT")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate AP2 #279 open_mandate_hash JCS vectors, #278 checkout_hash entropy, x402 #225 Fact Attestation, and #206 mainnet facilitator."""
    violations: list[str] = []

    # 1. AP2 #279: open_mandate_hash = SHA-256(JCS_RFC8785(unsigned_open_checkout_mandate_body))
    omh = payload.get("open_mandate_hash_check", {})
    if bool(omh.get("hashed_jws_compact_envelope", False)):
        violations.append("AP2_279_JWS_ENVELOPE_HASHED_INSTEAD_OF_UNSIGNED_CLAIMS")
    claims_obj = omh.get("unsigned_claims")
    provided_hash = omh.get("open_mandate_hash")
    if isinstance(claims_obj, dict) and provided_hash is not None:
        expected_hash = compute_rfc8785_jcs_sha256(claims_obj)
        if str(provided_hash) != expected_hash:
            violations.append("AP2_279_OPEN_MANDATE_HASH_MISMATCH")

    # 2. AP2 #278: Entropy-based checkout_hash requirement (supports Ed25519 when payload carries >=128 bits entropy)
    ent = payload.get("checkout_jwt_entropy", {})
    entropy_bits = int(ent.get("payload_entropy_bits", 0))
    has_session_nonce = bool(ent.get("has_high_entropy_nonce_claim", False))
    if entropy_bits < 128 or not has_session_nonce:
        violations.append("AP2_278_LOW_ENTROPY_CHECKOUT_JWT_PAYLOAD")

    # 3. Coinbase x402 #225: Independent Fact Attestation extension
    fa = payload.get("fact_attestation", {})
    attester_signer = str(fa.get("attester_signer", "")).strip().lower()
    pay_to = str(fa.get("pay_to", "")).strip().lower()
    if not attester_signer or attester_signer == pay_to:
        violations.append("X402_225_SELF_ASSERTED_PAYTO_FACT_ATTESTATION_REJECTED")
    if "judgment" in fa or "is_legit" in fa or "is_fraud" in fa:
        violations.append("X402_225_JUDGMENT_LABEL_FORBIDDEN_FACTS_ONLY")
    observations = fa.get("observations", [])
    if not isinstance(observations, list) or len(observations) == 0:
        violations.append("X402_225_EMPTY_FACT_OBSERVATIONS")
    else:
        for obs in observations:
            if not isinstance(obs, dict) or not str(obs.get("method", "")).strip():
                violations.append("X402_225_OBSERVATION_MISSING_DISCLOSED_METHOD")

    # 4. Coinbase x402 #206: Public facilitator returns 500 on Base/Solana Mainnet
    fac = payload.get("x402_facilitator_routing", {})
    network = str(fac.get("network", ""))
    facilitator_url = str(fac.get("facilitator_url", "")).strip()
    if network in MAINNET_NETWORKS and facilitator_url in TESTNET_ONLY_PUBLIC_FACILITATORS:
        violations.append("X402_206_TESTNET_PUBLIC_FACILITATOR_ON_MAINNET_500")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #513 write-critic/JSON args, #484 close_bank_account_7392 reason, #516 Pydantic coercion, and #508 solo_gt."""
    violations: list[str] = []

    # 1. Sierra tau2-bench #513: Generic write-critic gate & nested JSON-string tool arg comparison
    wc = payload.get("write_critic_gate", {})
    if bool(wc.get("is_mutating_tool", True)):
        if not bool(wc.get("verification_completed", False)) or not bool(wc.get("critic_approved", False)):
            violations.append("TAU2_513_UNVERIFIED_MUTATING_TOOL_BLOCKED_BY_CRITIC")

    nested_args = wc.get("nested_json_arg_comparison")
    if isinstance(nested_args, dict):
        gold_str = str(nested_args.get("gold_arguments_json", "{}"))
        pred_str = str(nested_args.get("pred_arguments_json", "{}"))
        used_raw_string_compare = bool(nested_args.get("used_raw_string_compare", False))
        if used_raw_string_compare:
            violations.append("TAU2_513_RAW_STRING_COMPARISON_ON_NESTED_JSON_ARGS")
        try:
            if json.loads(gold_str) != json.loads(pred_str):
                violations.append("TAU2_513_PARSED_NESTED_JSON_ARGS_MISMATCH")
        except ValueError:
            violations.append("TAU2_513_INVALID_NESTED_JSON_ARGS")

    # 2. Sierra tau2-bench #484: close_bank_account_7392 fixed-set reason validation
    cba = payload.get("close_bank_account_call", {})
    reason = str(cba.get("reason", "customer_request"))
    if reason not in ALLOWED_BANK_CLOSURE_REASONS:
        violations.append(f"TAU2_484_INVALID_FREE_TEXT_CLOSURE_REASON:{reason}")

    # 3. Sierra tau2-bench #516: Tool / ToolKitBase Pydantic schema validation & coercion
    tk = payload.get("tool_kwarg_validation", {})
    expected_int_arg = tk.get("expected_int_arg", 2)
    coerced_via_schema = bool(tk.get("coerced_via_pydantic_schema", True))
    if not coerced_via_schema:
        violations.append("TAU2_516_BYPASSED_PYDANTIC_KWARG_COERCION")
    if isinstance(expected_int_arg, float):
        if not expected_int_arg.is_integer():
            violations.append("TAU2_516_NON_INTEGRAL_FLOAT_FOR_INT_PARAM")
    elif not isinstance(expected_int_arg, int) or isinstance(expected_int_arg, bool):
        violations.append("TAU2_516_INVALID_TYPE_FOR_INT_PARAM")

    # 4. Sierra tau2-bench #508: detect llm_agent_solo_gt as solo mode when re-grading trajectories
    solo = payload.get("solo_mode_regrading", {})
    agent_impl = str(solo.get("agent_implementation", "llm_agent_solo_gt"))
    user_impl = str(solo.get("user_implementation", "dummy_user"))
    detected_is_solo = bool(solo.get("detected_is_solo", True))
    expected_is_solo = (agent_impl in SOLO_AGENT_IMPLEMENTATIONS) and (user_impl == "dummy_user")
    if detected_is_solo != expected_is_solo:
        violations.append("TAU2_508_SOLO_GT_DETECTION_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
