"""Stage 78 deterministic protocol & runtime guard:
UCP Sale-Basis Quantity Steps (`#653`), Non-Empty Actions/Policies (`#669`, `#661`), Loyalty Breakdown Invariant (`#662`), Request-Shape Omission (`#651`, `#646`), Event Feed & Post-Strip Array Elision (`#686`, `#679`, `#673`),
ACP Delegated 3DS Authentication API (`#93`, `#80`, `#85`, `#66`) & Payment Handlers / Extensions Framework (`#90`, `#89`, `#77`, `#76`),
Google AP2 Cross-Merchant Atomic Budget Authority (`#252`), TrustBoost Pre-LLM PII Sanitization (`#267`) & Normative Verifier `checkout_hash` Obligation (`#243`, `#233`),
and Sierra tau2-bench `gptlive` Full-Duplex Provider (`#409`), Transient Transcription Retry (`#418`), Viewer Truncation (`#434`), Active Reward Gates (`#411`) & Banking Answer-Key Scrubbing (`#429`, `#414`, `#412`, `#408`).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any


REVERSE_DNS_RE = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+){2,}$")
ALLOWED_EVENT_TRANSPORTS = {"webhook", "sse", "poll"}
ACP_DELEGATED_AUTH_ENDPOINTS = {"create", "authenticate", "retrieve"}
AP2_BUDGET_VERBS = {"authorize", "commit", "refund", "query"}
ANSWER_KEY_LEAK_MARKERS = (
    "SHOULD BE FREE",
    "AFTER 2 FREE",
    "AFTER FREE ALLOWANCE",
)


def verify_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify UCP PRs #686, #679, #673, #669, #662, #661, #653, #651, #646."""
    violations: list[str] = []

    # 1. Sale-basis quantity steps (#653)
    for idx, li in enumerate(payload.get("line_items", [])):
        qty = li.get("quantity")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            violations.append(f"UCP_QUANTITY_MUST_BE_POSITIVE_INTEGER_STEPS:{idx}")
            continue
        item = li.get("item", {})
        price = item.get("price")
        q_unit = item.get("quantity_unit")
        scale = 0
        if q_unit is not None:
            unit_code = q_unit.get("unit", "")
            scale = q_unit.get("scale", 0)
            display_text = q_unit.get("display_text", "")
            if not unit_code or not display_text:
                violations.append(f"UCP_QUANTITY_UNIT_DESCRIPTOR_INCOMPLETE:{idx}")
            if not isinstance(scale, int) or isinstance(scale, bool) or scale < 0:
                violations.append(f"UCP_QUANTITY_UNIT_SCALE_INVALID:{idx}")
                scale = 0
            if unit_code == "C62" and scale != 0:
                violations.append(f"UCP_QUANTITY_UNIT_C62_NONZERO_SCALE_FORBIDDEN:{idx}")
        if isinstance(price, int) and isinstance(li.get("authoritative_subtotal"), int):
            expected_subtotal = int(
                (Decimal(price) * Decimal(qty) / (Decimal(10) ** Decimal(scale))).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            if li["authoritative_subtotal"] != expected_subtotal:
                violations.append(
                    f"UCP_VARIABLE_QUANTITY_LINE_TOTAL_ROUNDING_MISMATCH:{idx}:{li['authoritative_subtotal']}!={expected_subtotal}"
                )

        unit_price = item.get("unit_price")
        if isinstance(unit_price, dict):
            measure = unit_price.get("measure", {})
            reference = unit_price.get("reference", {})
            m_val = measure.get("value")
            r_val = reference.get("value")
            if (
                not isinstance(m_val, int)
                or m_val <= 0
                or not isinstance(r_val, int)
                or r_val <= 0
                or measure.get("unit") != reference.get("unit")
                or measure.get("currency") != reference.get("currency")
            ):
                violations.append(f"UCP_UNIT_PRICE_COMPARATOR_MISMATCH:{idx}")

    # 2. Non-empty actions map (#669)
    if "actions" in payload:
        actions = payload["actions"]
        if not isinstance(actions, dict) or len(actions) == 0:
            violations.append("UCP_EMPTY_ACTIONS_MAP_FORBIDDEN")

    # 3. Non-empty policies[].applies_to & valid product category/tag JSONPath (#661)
    for idx, pol in enumerate(payload.get("policies", [])):
        if "applies_to" in pol:
            applies_to = pol["applies_to"]
            if not isinstance(applies_to, list) or len(applies_to) == 0:
                violations.append(f"UCP_POLICY_EMPTY_APPLIES_TO_FORBIDDEN:{idx}")
            else:
                for path_expr in applies_to:
                    if "@.category==" in str(path_expr) or "@.category ==" in str(path_expr):
                        violations.append(f"UCP_POLICY_INVALID_PRODUCT_CATEGORY_SCALAR_PATH:{idx}")

    # 4. Loyalty earning_forecast.breakdown sum invariant (#662)
    loyalty = payload.get("loyalty")
    if isinstance(loyalty, dict):
        forecast = loyalty.get("earning_forecast")
        if isinstance(forecast, dict):
            total_amt = forecast.get("amount")
            breakdown = forecast.get("breakdown", [])
            if isinstance(total_amt, int) and isinstance(breakdown, list) and breakdown:
                b_sum = sum(int(b.get("amount", 0)) for b in breakdown if isinstance(b, dict))
                if b_sum != total_amt:
                    violations.append(f"UCP_LOYALTY_EARNING_BREAKDOWN_SUM_MISMATCH:{b_sum}!={total_amt}")
        for disc in loyalty.get("discounts", []):
            if disc.get("expressed_in_major_units") is True:
                violations.append("UCP_LOYALTY_MAJOR_UNIT_AMOUNT_FORBIDDEN")

    # 5. Request-shape read-only field omission (#651, #646)
    req_env = payload.get("request_envelope")
    if isinstance(req_env, dict):
        op = req_env.get("op", "update_checkout")
        body = req_env.get("body", {})
        forbidden_always = {"status", "totals", "continue_url", "expires_at"}
        present_forbidden = forbidden_always.intersection(body.keys())
        if present_forbidden:
            violations.append("UCP_REQUEST_BODY_SERVER_ASSIGNED_FIELD_LEAK")
        if op in {"create_checkout", "update_checkout", "create_cart"} and "id" in body:
            violations.append(f"UCP_REQUEST_BODY_DEPRECATED_ID_FORBIDDEN:{op}")

    # 6. Event feed & post-strip array elision (#673, #686, #679)
    event_feed = payload.get("event_feed")
    if isinstance(event_feed, dict):
        transports = set(event_feed.get("transports", []))
        if (
            not str(event_feed.get("url", "")).startswith("https://")
            or not event_feed.get("event_types")
            or not transports
            or not transports.issubset(ALLOWED_EVENT_TRANSPORTS)
        ):
            violations.append("UCP_EVENT_FEED_CONTRACT_INVALID")

    elision = payload.get("array_elision_check")
    if isinstance(elision, dict):
        if elision.get("recorded_pre_strip_index") is True:
            violations.append("UCP_ARRAY_ELISION_PRE_STRIP_INDEX_MISMATCH")

    mcp_idemp = payload.get("mcp_idempotency")
    if isinstance(mcp_idemp, dict):
        if mcp_idemp.get("key_reused_with_different_payload") is True and mcp_idemp.get("jsonrpc_error_code") != -32000:
            violations.append("UCP_MCP_IDEMPOTENCY_CONFLICT_CODE_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_acp_delegated_authentication_and_payment_handlers_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify ACP PRs #93, #90, #89, #85, #80, #77, #76, #66."""
    violations: list[str] = []

    # 1. Delegated Authentication API (#93, #80, #85, #66)
    auth = payload.get("delegated_authentication", {})
    if auth:
        endpoints = set(auth.get("implemented_endpoints", []))
        if not ACP_DELEGATED_AUTH_ENDPOINTS.issubset(endpoints):
            violations.append("ACP_DELEGATED_AUTH_ENDPOINTS_INCOMPLETE")
        if not auth.get("authentication_session_id"):
            violations.append("ACP_DELEGATED_AUTH_SESSION_ID_REQUIRED")
        if auth.get("create_action_type") == "fingerprint" and not auth.get("fingerprint_completed_before_authenticate", True):
            violations.append("ACP_DELEGATED_AUTH_FINGERPRINT_STEP_SKIPPED")
        if auth.get("authenticate_action_type") == "challenge" and not auth.get("challenge_completed_before_retrieve", True):
            violations.append("ACP_DELEGATED_AUTH_CHALLENGE_STEP_SKIPPED")
        if not auth.get("retrieve_called_before_checkout_complete", True):
            violations.append("ACP_DELEGATED_AUTH_RETRIEVE_STEP_SKIPPED")
        if not auth.get("channel_provided_in_create_or_authenticate", True):
            violations.append("ACP_DELEGATED_AUTH_CHANNEL_DATA_MISSING")
        if auth.get("idempotency_conflict_detected") is True and auth.get("http_status") != 409:
            violations.append("ACP_DELEGATED_AUTH_IDEMPOTENCY_409_REQUIRED")

    auth_meta = payload.get("authentication_metadata", {})
    if "channel" in auth_meta:
        violations.append("ACP_AUTH_METADATA_DEPRECATED_CHANNEL_FIELD_FORBIDDEN")

    # 2. Payment Handlers Framework (#90)
    if "payment_methods" in payload:
        violations.append("ACP_LEGACY_PAYMENT_METHODS_STRING_ARRAY_FORBIDDEN")

    handlers = payload.get("capabilities", {}).get("payment", {}).get("handlers", [])
    handler_by_id: dict[str, dict[str, Any]] = {}
    for idx, h in enumerate(handlers):
        h_id = h.get("id", "")
        h_name = h.get("name", "")
        psp = h.get("psp", "")
        req_del = h.get("requires_delegate_payment")
        req_pci = h.get("requires_pci_compliance")
        cfg = h.get("config", {})
        if not h_id or not REVERSE_DNS_RE.match(str(h_name)):
            violations.append(f"ACP_PAYMENT_HANDLER_REVERSE_DNS_NAME_INVALID:{idx}")
        if not psp or not isinstance(req_del, bool) or not isinstance(req_pci, bool):
            violations.append(f"ACP_PAYMENT_HANDLER_METADATA_INCOMPLETE:{idx}")
        if req_del is True and not cfg.get("merchant_id"):
            violations.append(f"ACP_PAYMENT_HANDLER_MERCHANT_ID_REQUIRED:{idx}")
        if h_id:
            handler_by_id[h_id] = h

    del_req = payload.get("delegate_payment_request")
    if isinstance(del_req, dict):
        h_id = del_req.get("handler_id")
        matched = handler_by_id.get(h_id, {})
        expected_mid = matched.get("config", {}).get("merchant_id")
        actual_mid = del_req.get("constraints", {}).get("merchant_id")
        if expected_mid and actual_mid != expected_mid:
            violations.append(f"ACP_HANDLER_DELEGATE_MERCHANT_ID_MISMATCH:{actual_mid}!={expected_mid}")

    # 3. Discount Extension (#89)
    discounts = payload.get("discounts")
    if isinstance(discounts, dict):
        for idx, applied in enumerate(discounts.get("applied", [])):
            amt = applied.get("amount")
            allocs = applied.get("allocations", [])
            if isinstance(amt, int) and allocs:
                alloc_sum = sum(int(a.get("amount", 0)) for a in allocs)
                if alloc_sum != amt:
                    violations.append(f"ACP_DISCOUNT_ALLOCATION_SUM_MISMATCH:{idx}")
        for idx, rej in enumerate(discounts.get("rejected", [])):
            if not rej.get("code") or not rej.get("reason_code"):
                violations.append(f"ACP_DISCOUNT_REJECTION_REASON_CODE_REQUIRED:{idx}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_ap2_cross_merchant_budget_authority_and_trustboost_pii_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Google AP2 PRs #267, #252, #243, #233."""
    violations: list[str] = []

    # 1. Cross-merchant atomic budget authority (#252)
    budget = payload.get("cross_merchant_budget", {})
    if budget:
        if budget.get("isolated_per_merchant_context") is True:
            violations.append("AP2_ISOLATED_MERCHANT_BUDGET_CONTEXT_RACE")
        verbs = set(budget.get("authority_verbs", []))
        if not AP2_BUDGET_VERBS.issubset(verbs):
            violations.append("AP2_BUDGET_AUTHORITY_VERBS_INCOMPLETE")
        total_budget = int(budget.get("total_budget_minor", 0))
        committed = int(budget.get("committed_minor", 0))
        held = int(budget.get("active_holds_minor", 0))
        req = int(budget.get("requested_authorize_minor", 0))
        if committed + held + req > total_budget:
            violations.append(
                f"AP2_CROSS_MERCHANT_BUDGET_AUTHORIZE_EXCEEDED:{committed + held + req}>{total_budget}"
            )

    # 2. TrustBoost pre-LLM PII sanitization + Solana x402 proof (#267)
    pii = payload.get("trustboost_pii", {})
    if pii:
        if pii.get("contains_pii") is True and pii.get("sanitized_before_llm") is not True:
            violations.append("AP2_RAW_PII_EXPOSED_TO_LLM_BEFORE_SANITIZATION")
        if pii.get("x402_sanitization_paid") is not True:
            violations.append("AP2_TRUSTBOOST_X402_PAYMENT_REQUIRED_402")
        if not pii.get("solana_anchor_tx") or pii.get("anchor_proof_verified") is not True:
            violations.append("AP2_TRUSTBOOST_SOLANA_ANCHOR_PROOF_UNVERIFIED")

    # 3. Normative verifier obligation for checkout_hash (#243, #233)
    verifier = payload.get("mandate_verifier", {})
    if verifier:
        if verifier.get("recomputed_checkout_hash") != verifier.get("mandate_checkout_hash"):
            violations.append("AP2_VERIFIER_CHECKOUT_HASH_OBLIGATION_UNMET")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_tau2_gptlive_provider_transcription_retry_and_banking_leak_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Sierra tau2-bench PRs #434, #429, #426, #418, #414, #412, #411, #409, #408."""
    violations: list[str] = []

    # 1. gptlive audio-native provider (#409)
    gptlive = payload.get("gptlive_session", {})
    if gptlive:
        if gptlive.get("uses_responses_delegation") is not True or gptlive.get("sent_response_create") is True:
            violations.append("TAU2_GPTLIVE_RESPONSES_DELEGATION_PROTOCOL_VIOLATION")
        if gptlive.get("joined_call_id_via_output_item_added") is not True:
            violations.append("TAU2_GPTLIVE_ITEM_ID_JOIN_REQUIRED")
        if gptlive.get("rms_hysteresis_silence_gate_enabled") is not True:
            violations.append("TAU2_GPTLIVE_RMS_SILENCE_GATE_REQUIRED")
        if gptlive.get("live_suite_executed") is True and gptlive.get("gptlive_test_enabled_env") is not True:
            violations.append("TAU2_GPTLIVE_ALPHA_ENV_GATE_MISSING")

    # 2. Transient transcription retry (#418) & viewer tool-result truncation (#434)
    transcription = payload.get("transcription_event", {})
    if transcription:
        if (
            transcription.get("transient_error") is True
            and transcription.get("retried") is not True
            and transcription.get("returned_empty_transcript") is True
        ):
            violations.append("TAU2_TRANSIENT_TRANSCRIPTION_SWALLOWED_AS_EMPTY")

    viewer = payload.get("viewer_render", {})
    if viewer:
        max_chars = int(viewer.get("max_tool_result_chars", 500))
        full_flag = bool(viewer.get("full_tool_results", False))
        rendered_len = int(viewer.get("rendered_tool_result_chars", 0))
        if not full_flag and rendered_len > max_chars:
            violations.append(f"TAU2_VIEW_TOOL_RESULT_NOT_TRUNCATED:{rendered_len}>{max_chars}")

    # 3. Active reward criteria gates (#411)
    reward_gate = payload.get("reward_gate", {})
    if reward_gate:
        for basis in reward_gate.get("active_reward_basis", []):
            criteria = reward_gate.get("criteria_by_basis", {}).get(basis, [])
            if not criteria:
                violations.append(f"TAU2_EMPTY_ACTIVE_REWARD_BASIS_GATE:{basis}")

    # 4. Banking numeric string arg coercion (#429) & ATM fee answer-key leak scrubbing (#412, #414)
    banking = payload.get("banking_knowledge", {})
    if banking:
        if banking.get("rejected_numeric_string_arg") is True:
            violations.append("TAU2_BANKING_NUMERIC_STRING_ARG_REJECTED")
        if banking.get("task_074_light_blue_gold_credit") is not None:
            if float(banking["task_074_light_blue_gold_credit"]) != 14.50:
                violations.append("TAU2_BANKING_T074_LIGHT_BLUE_ATM_FEE_UNDER_REFUND")
        for idx, desc in enumerate(banking.get("db_transaction_descriptions", [])):
            upper_desc = str(desc).upper()
            if any(marker in upper_desc for marker in ANSWER_KEY_LEAK_MARKERS):
                violations.append(f"TAU2_BANKING_DB_ANSWER_KEY_ANNOTATION_LEAK:{idx}")
        if banking.get("kb_day_count_has_currency_sign") is True:
            violations.append("TAU2_BANKING_KB_DAY_COUNT_STRAY_CURRENCY_SIGN")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
