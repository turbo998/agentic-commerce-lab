"""Stage 74 deterministic protocol and benchmark guardrails.

Covers primary-source PRs across UCP, ACP, Google AP2, Coinbase x402, and Sierra tau2-bench:
1. UCP Lodging Booking Capability & Cancellation Policy Extension (#780), vertical-agnostic
   token binding vs. participant authorization (#762, #746), Location root-level spatial
   relations / item availability / self-describing amenities (#766, #765, #753), and
   Request Constraints outer RFC 9535 path targeting & anyOf (#757, #744).
2. ACP mandatory POST Idempotency-Key & replay headers (#121), /.well-known/acp.json
   discovery (#137), DiscountsResponse.rejected[] + 3DS frictionless.type + sale extension
   (#129, #123), and MessageInfo/Refund.amount/IIN/risk_signals schema alignment
   (#262, #249, #214, #116).
3. Google AP2 RFC 8785 JCS cart-to-payment mandate hash (#253), KB-SD-JWT per-hop and
   terminal aud/nonce binding (#342, #326, #313), immediate payment execution window
   enforcement (#318), budget major-vs-minor unit normalization (#340), and Coinbase x402
   streamed body cloning (#306), unknown accepts filtering (#297), top-level signer
   address check (#277), and EIP-3009 EIP-712 domain completeness (#323).
4. Sierra tau-bench 2.0 Gemini Live 8kHz native telephony + START_SENSITIVITY_HIGH +
   SlidingWindow + en-US transcription hint (#544, #511, #510, #509), silent GoAway
   reconnect deadline enforcement (#461), full-duplex nonblocking user generation
   (#525, #522), and empty text-mode user-simulator completion retry (#471).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List


_REVERSE_DOMAIN_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+){2,}$")
_EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_VALID_LODGING_REFUNDABILITY = {"refundable", "partially_refundable", "non_refundable"}
_VALID_GUEST_ROLES = {"primary_guest", "additional_guest"}


def _canonicalize_jcs_strip_nulls(value: Any) -> Any:
    """Recursively strips None/null values per AP2 PR #253 before RFC 8785 JCS serialization."""
    if isinstance(value, dict):
        return {
            str(k): _canonicalize_jcs_strip_nulls(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            if v is not None
        }
    if isinstance(value, list):
        return [_canonicalize_jcs_strip_nulls(item) for item in value]
    return value


def compute_ap2_jcs_cart_mandate_hash(cart_mandate: Dict[str, Any]) -> str:
    """Computes hex(sha256(JCS(CartMandate))) with null optional fields stripped (AP2 PR #253)."""
    cleaned = _canonicalize_jcs_strip_nulls(cart_mandate)
    canonical_bytes = json.dumps(
        cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def verify_ucp_lodging_booking_token_binding_location_spatial_and_constraint_path(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Verifies UCP PRs #780, #766, #765, #762, #757, #753, #746, and #744."""
    reasons: List[str] = []

    # 1. PR #780: Lodging Booking Capability (dev.ucp.lodging.booking) & Cancellation Policy
    lodging = payload.get("lodging_booking", {})
    guests = lodging.get("guests", [])
    guest_ids = {
        g.get("id")
        for g in guests
        if isinstance(g, dict) and isinstance(g.get("id"), str) and g.get("id").strip()
    }
    stays = lodging.get("stays", [])
    if not isinstance(stays, list) or not stays:
        reasons.append("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid")
    else:
        for stay in stays:
            if not isinstance(stay, dict):
                reasons.append("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid")
                break
            has_stay_id = isinstance(stay.get("id"), str) and bool(stay.get("id").strip())
            acc_id = (stay.get("accommodation_type") or {}).get("id")
            rp_id = (stay.get("rate_plan") or {}).get("id")
            has_compound = isinstance(acc_id, str) and bool(acc_id.strip()) and isinstance(rp_id, str) and bool(rp_id.strip())
            dates = stay.get("stay_dates") or {}
            start_date = str(dates.get("start_date", ""))
            end_date = str(dates.get("end_date", ""))
            if not (has_stay_id or has_compound) or not start_date or not end_date or start_date >= end_date:
                reasons.append("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid")
                break
            assignments = stay.get("guest_assignments", [])
            for assign in assignments:
                if (
                    not isinstance(assign, dict)
                    or assign.get("guest_id") not in guest_ids
                    or assign.get("role") not in _VALID_GUEST_ROLES
                ):
                    reasons.append("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid")
                    break

    policies = lodging.get("policies", [])
    for policy in policies:
        if isinstance(policy, dict) and policy.get("type") == "dev.ucp.lodging.policy.cancellation":
            refundability = policy.get("refundability")
            desc_plain = ((policy.get("description") or {}).get("plain") or "").strip()
            if refundability not in _VALID_LODGING_REFUNDABILITY or not desc_plain:
                reasons.append("ucp_lodging_stay_guest_assignment_or_cancellation_policy_invalid")
                break

    # 2. PRs #762 & #746: Vertical-agnostic token binding {type, id} vs sibling participant identity
    token_check = payload.get("token_binding_check", {})
    mint_binding = token_check.get("mint_binding") or {}
    burn_binding = token_check.get("burn_binding") or {}
    b_type = mint_binding.get("type")
    b_id = mint_binding.get("id")
    if (
        not isinstance(b_type, str)
        or not _REVERSE_DOMAIN_RE.match(b_type)
        or not isinstance(b_id, str)
        or len(b_id.strip()) < 1
        or "identity" in mint_binding
        or "identity" in burn_binding
        or "checkout_id" in mint_binding
    ):
        reasons.append("ucp_token_binding_coupled_to_participant_identity_or_invalid_shape")
    else:
        # Rule 1 (#762): compare type and id only, ignoring unrecognized open members
        resource_equal = (
            mint_binding.get("type") == burn_binding.get("type")
            and mint_binding.get("id") == burn_binding.get("id")
        )
        # Rule 4 (#762): verify participant authorization separately at burn
        minted_participant = token_check.get("minted_participant_id")
        caller_is_target_business = bool(token_check.get("caller_is_target_business", False))
        burn_identity = token_check.get("burn_identity")
        effective_participant = (
            minted_participant
            if caller_is_target_business and burn_identity is None
            else burn_identity
        )
        if not resource_equal or not minted_participant or effective_participant != minted_participant:
            reasons.append("ucp_token_binding_coupled_to_participant_identity_or_invalid_shape")

    # 3. PRs #766, #765, #753: Location spatial relations, filters.items[], Lookup inputs[], self-describing amenities
    location = payload.get("location_discovery", {})
    req = location.get("request") or {}
    filters = req.get("filters") or {}
    if "geo" in filters or "inventory" in filters:
        reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
    items_filter = filters.get("items", [])
    if not isinstance(items_filter, list) or any(not isinstance(i, str) or not i.strip() for i in items_filter):
        reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
    candidate_available = set(location.get("candidate_available_items", []))
    if items_filter and not set(items_filter).issubset(candidate_available):
        reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")

    is_lookup = bool(location.get("is_lookup", False))
    returned_locations = location.get("returned_locations", [])
    for loc in returned_locations:
        if not isinstance(loc, dict):
            reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
            break
        if is_lookup:
            inputs_corr = loc.get("inputs")
            if not isinstance(inputs_corr, list) or not inputs_corr:
                reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
                break
        amenities = loc.get("amenities", {})
        if not isinstance(amenities, dict):
            reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
            break
        for am_key, am_val in amenities.items():
            if (
                not isinstance(am_key, str)
                or not _REVERSE_DOMAIN_RE.match(am_key)
                or not isinstance(am_val, dict)
                or not isinstance(am_val.get("description"), str)
                or not am_val.get("description").strip()
            ):
                reasons.append("ucp_location_spatial_filter_or_amenity_description_violation")
                break

    # 4. PRs #757 & #744: Request Constraints outer-only RFC 9535 path targeting & anyOf
    rc = payload.get("request_constraint", {})
    outer_path = rc.get("path")
    derived_norm_path = rc.get("derived_normalized_path", "$")
    effective_path = outer_path if outer_path is not None else derived_norm_path
    if not isinstance(effective_path, str) or not effective_path.startswith("$"):
        reasons.append("ucp_request_constraint_inner_path_or_empty_anyof")
    inner_ops = rc.get("inner_operators", [])
    if any(isinstance(op, dict) and "path" in op for op in inner_ops):
        reasons.append("ucp_request_constraint_inner_path_or_empty_anyof")
    if "anyOf" in rc:
        any_of = rc.get("anyOf")
        if not isinstance(any_of, list) or len(any_of) == 0:
            reasons.append("ucp_request_constraint_inner_path_or_empty_anyof")

    dedup_reasons = list(dict.fromkeys(reasons))
    return {
        "allowed": len(dedup_reasons) == 0,
        "reasons": dedup_reasons,
        "effective_constraint_path": effective_path,
        "guest_pool_count": len(guest_ids),
    }


def verify_acp_mandatory_idempotency_wellknown_discovery_sale_and_schema_alignment(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Verifies ACP PRs #262, #249, #214, #137, #129, #123, #121, and #116."""
    reasons: List[str] = []

    # 1. PR #121 (SEP #120): Mandatory Idempotency-Key on POST + 400/409/422 error codes + Idempotent-Replayed
    idem = payload.get("post_idempotency", {})
    key = idem.get("idempotency_key")
    in_flight = bool(idem.get("in_flight", False))
    prior_hash = idem.get("prior_payload_hash")
    current_hash = idem.get("current_payload_hash")
    is_replay = bool(idem.get("is_cached_replay", False))
    resp_headers = idem.get("response_headers") or {}

    http_status = 200
    error_code = None
    if not isinstance(key, str) or not (1 <= len(key.strip()) <= 255):
        http_status = 400
        error_code = "idempotency_key_required"
        reasons.append("acp_post_idempotency_contract_violation")
    elif in_flight:
        http_status = 409
        error_code = "idempotency_in_flight"
        if "Retry-After" not in resp_headers:
            reasons.append("acp_post_idempotency_contract_violation")
        else:
            reasons.append("acp_post_idempotency_in_flight_rejected")
    elif prior_hash is not None and current_hash != prior_hash:
        http_status = 422
        error_code = "idempotency_conflict"
        reasons.append("acp_post_idempotency_conflict_rejected")
    elif is_replay and resp_headers.get("Idempotent-Replayed") != "true":
        reasons.append("acp_post_idempotency_contract_violation")

    # 2. PR #137 (SEP #136): /.well-known/acp.json discovery document
    wk = payload.get("well_known_acp") or {}
    if (
        wk.get("requires_auth") is True
        or not isinstance(wk.get("protocol_version"), str)
        or not wk.get("protocol_version", "").strip()
        or not isinstance(wk.get("api_base_url"), str)
        or not wk.get("api_base_url", "").startswith("https://")
        or not isinstance(wk.get("transports"), list)
        or not wk.get("transports")
        or not isinstance(wk.get("currencies"), list)
        or not wk.get("currencies")
        or not isinstance(wk.get("locales"), list)
        or not wk.get("locales")
    ):
        reasons.append("acp_well_known_discovery_document_invalid")

    # 3. PRs #129 & #123: DiscountsResponse.rejected[], 3DS frictionless.type == "low_risk", sale extension
    discounts = payload.get("discounts") or {}
    if not isinstance(discounts.get("rejected"), list):
        reasons.append("acp_discount_rejected_or_sale_extension_invalid")

    frictionless = (
        ((payload.get("authentication_metadata") or {}).get("flow_preference") or {}).get("frictionless")
    )
    if frictionless is not None:
        if not isinstance(frictionless, dict) or frictionless.get("type") != "low_risk":
            reasons.append("acp_discount_rejected_or_sale_extension_invalid")

    sales_registry = {
        s.get("id")
        for s in (payload.get("sales") or [])
        if isinstance(s, dict) and isinstance(s.get("id"), str) and s.get("id").strip()
    }
    for item in payload.get("line_items", []):
        if not isinstance(item, dict):
            continue
        sale_obj = item.get("sale")
        if sale_obj is not None:
            sale_id = sale_obj.get("sale_id") if isinstance(sale_obj, dict) else None
            compare_at = sale_obj.get("compare_at_amount") if isinstance(sale_obj, dict) else None
            amount = item.get("amount")
            if (
                sale_id not in sales_registry
                or not isinstance(compare_at, int)
                or isinstance(compare_at, bool)
                or not isinstance(amount, int)
                or compare_at <= amount
            ):
                reasons.append("acp_discount_rejected_or_sale_extension_invalid")
                break

    # 4. PRs #262, #249, #214, #116: Message* fields, Refund.amount integer minor units, IIN <= 8, empty risk_signals
    for msg in payload.get("messages", []):
        if not isinstance(msg, dict):
            reasons.append("acp_message_refund_iin_or_risk_signals_schema_mismatch")
            break
        forbidden = {"id", "message", "display_context"} & set(msg.keys())
        required_ok = all(
            isinstance(msg.get(k), str) and bool(msg.get(k).strip())
            for k in ("type", "content_type", "content")
        )
        if forbidden or not required_ok:
            reasons.append("acp_message_refund_iin_or_risk_signals_schema_mismatch")
            break

    for refund in payload.get("refunds", []):
        amt = refund.get("amount") if isinstance(refund, dict) else None
        if not isinstance(amt, int) or isinstance(amt, bool) or amt < 0:
            reasons.append("acp_message_refund_iin_or_risk_signals_schema_mismatch")
            break

    delegate = payload.get("delegate_payment") or {}
    risk_signals = delegate.get("risk_signals", [])
    iin = str((delegate.get("card") or {}).get("iin", ""))
    if (
        not isinstance(risk_signals, list)
        or not iin.isdigit()
        or not (6 <= len(iin) <= 8)
    ):
        reasons.append("acp_message_refund_iin_or_risk_signals_schema_mismatch")

    dedup_reasons = list(dict.fromkeys(reasons))
    return {
        "allowed": len(dedup_reasons) == 0,
        "reasons": dedup_reasons,
        "http_status": http_status,
        "error_code": error_code,
    }


def verify_ap2_jcs_cart_hash_sdjwt_hops_execution_window_and_x402_stream_accepts(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Verifies AP2 PRs #342, #340, #326, #318, #313, #253 and Coinbase x402 PRs #323, #306, #297, #277."""
    reasons: List[str] = []

    # 1. AP2 PR #253: RFC 8785 JCS cart_mandate_hash binding
    cart_mandate = payload.get("cart_mandate") or {}
    payment_contents = payload.get("payment_mandate_contents") or {}
    computed_hash = compute_ap2_jcs_cart_mandate_hash(cart_mandate)
    claimed_hash = payment_contents.get("cart_mandate_hash")
    claimed_cart_id = payment_contents.get("cart_mandate_id")
    if (
        not claimed_cart_id
        or claimed_cart_id != cart_mandate.get("id")
        or not isinstance(claimed_hash, str)
        or claimed_hash != computed_hash
    ):
        reasons.append("ap2_jcs_cart_mandate_hash_mismatch")

    # 2. AP2 PRs #342, #326, #313: KB-SD-JWT per-hop and terminal aud/nonce verification
    sdjwt_hops = payload.get("kb_sdjwt_hops", [])
    if not isinstance(sdjwt_hops, list) or not sdjwt_hops:
        reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
    else:
        for hop in sdjwt_hops:
            if not isinstance(hop, dict):
                reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
                break
            aud = hop.get("aud")
            nonce = hop.get("nonce")
            exp_aud = hop.get("expected_aud")
            exp_nonce = hop.get("expected_nonce")
            is_terminal = bool(hop.get("is_terminal", False))
            # PR #342: structural presence of non-empty string aud & nonce on every hop
            if not isinstance(aud, str) or not aud.strip() or not isinstance(nonce, str) or not nonce.strip():
                reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
                break
            # PR #313: honor expected_aud / expected_nonce on every hop (including intermediate)
            if exp_aud is not None and aud != exp_aud:
                reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
                break
            if exp_nonce is not None and nonce != exp_nonce:
                reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
                break
            # PR #326: terminal hop carrying aud/nonce MUST be verified with expected_aud & expected_nonce
            if is_terminal and (exp_aud != aud or exp_nonce != nonce):
                reasons.append("ap2_kb_sdjwt_hop_or_terminal_aud_nonce_unbound")
                break

    # 3. AP2 PRs #318 & #340: Omitted execution_date evaluated at UTC clock + major vs minor budget units
    exec_win = payload.get("execution_window") or {}
    not_before = str(exec_win.get("not_before", ""))
    not_after = str(exec_win.get("not_after", ""))
    effective_exec = str(exec_win.get("execution_date") or exec_win.get("verifier_utc_now") or "")
    if not not_before or not not_after or not effective_exec or not (not_before <= effective_exec <= not_after):
        reasons.append("ap2_immediate_payment_outside_execution_window")

    budget = payload.get("budget_check") or {}
    budget_max_major = budget.get("budget_max_major", 0)
    amount_range_max_minor = budget.get("amount_range_max_minor", 0)
    total_spend_minor = budget.get("total_spend_minor", 0)
    payment_amount_minor = budget.get("payment_amount_minor", 0)
    budget_max_minor = int(round(float(budget_max_major) * 100))
    if total_spend_minor > budget_max_minor or payment_amount_minor > int(amount_range_max_minor):
        reasons.append("ap2_budget_major_vs_minor_unit_overflow")

    # 4. Coinbase x402 PRs #323, #306, #297, #277
    x402 = payload.get("x402_client") or {}
    body_is_stream = bool(x402.get("body_is_readable_stream", False))
    request_cloned = bool(x402.get("request_cloned_before_unpaid_probe", False))
    if body_is_stream and not request_cloned:
        reasons.append("x402_stream_body_accepts_or_signer_address_violation")

    supported_networks = set(x402.get("supported_networks", ["eip155:8453", "eip155:84532", "base"]))
    accepts = x402.get("accepts", [])
    throw_on_unknown = bool(x402.get("throw_on_unknown_accepts_entry", False))
    payable_rails = [
        entry for entry in accepts
        if isinstance(entry, dict) and entry.get("network") in supported_networks
    ]
    if throw_on_unknown or not payable_rails:
        reasons.append("x402_stream_body_accepts_or_signer_address_violation")

    signer = x402.get("signer") or {}
    signer_addr = signer.get("address")
    if not isinstance(signer_addr, str) or not _EVM_ADDRESS_RE.match(signer_addr):
        reasons.append("x402_stream_body_accepts_or_signer_address_violation")

    domain = x402.get("eip712_domain") or {}
    if (
        not isinstance(domain.get("name"), str)
        or not domain.get("name", "").strip()
        or not isinstance(domain.get("version"), str)
        or not domain.get("version", "").strip()
        or not isinstance(domain.get("verifyingContract"), str)
        or not _EVM_ADDRESS_RE.match(domain.get("verifyingContract", ""))
    ):
        reasons.append("x402_stream_body_accepts_or_signer_address_violation")

    dedup_reasons = list(dict.fromkeys(reasons))
    return {
        "allowed": len(dedup_reasons) == 0,
        "reasons": dedup_reasons,
        "computed_cart_mandate_hash": computed_hash,
        "selected_payable_network": payable_rails[0]["network"] if payable_rails else None,
    }


def verify_tau2_gemini_8khz_telephony_goaway_reconnect_nonblocking_duplex_and_empty_turn_retry(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Verifies Sierra tau-bench 2.0 PRs #544, #525, #522, #511, #510, #509, #471, and #461."""
    reasons: List[str] = []

    # 1. PRs #544, #511, #510, #509: Gemini 8kHz telephony native input, HIGH start sensitivity, SlidingWindow, en-US hint
    gemini = payload.get("gemini_live_config") or {}
    sample_rate = gemini.get("input_sample_rate_hz")
    upsampled_client_side = bool(gemini.get("client_side_ratecv_upsampling", False))
    start_sens = gemini.get("start_of_speech_sensitivity")
    sliding_window = bool(gemini.get("context_compression_sliding_window", False))
    lang_codes = gemini.get("transcription_language_codes", [])

    if (
        sample_rate != 8000
        or upsampled_client_side
        or start_sens != "START_SENSITIVITY_HIGH"
        or not sliding_window
        or not isinstance(lang_codes, list)
        or not lang_codes
    ):
        reasons.append("tau2_gemini_telephony_8khz_or_sliding_window_misconfigured")

    # 2. PR #461: GoAway reconnect deadline enforced even when server goes silent
    goaway = payload.get("goaway_watchdog") or {}
    goaway_received = bool(goaway.get("goaway_received", False))
    server_silent = bool(goaway.get("server_went_silent", False))
    deadline_checked_outside_recv = bool(goaway.get("deadline_checked_on_silent_stream", False))
    reconnected = bool(goaway.get("reconnected_before_drop", False))
    if goaway_received and server_silent and (not deadline_checked_outside_recv or not reconnected):
        reasons.append("tau2_gemini_goaway_silent_server_missed_reconnect")

    # 3. PRs #525 & #522: Full-duplex nonblocking user generation & single user initialization
    duplex = payload.get("full_duplex_runtime") or {}
    if (
        not bool(duplex.get("nonblocking_user_generation", False))
        or not bool(duplex.get("text_only_llm_history", False))
        or bool(duplex.get("duplicate_user_init", False))
    ):
        reasons.append("tau2_full_duplex_tick_blocked_or_duplicate_user_init")

    # 4. PR #471: Retry empty text-mode user-simulator completion with ###STOP### reminder
    sim = payload.get("user_simulator_turn") or {}
    initial_empty = bool(sim.get("initial_empty_completion", False))
    retried_with_stop_hint = bool(sim.get("retried_with_stop_reminder", False))
    crashed_episode = bool(sim.get("crashed_as_infrastructure_error", False))
    if initial_empty and (not retried_with_stop_hint or crashed_episode):
        reasons.append("tau2_empty_user_simulator_completion_unretried_crash")

    dedup_reasons = list(dict.fromkeys(reasons))
    return {
        "allowed": len(dedup_reasons) == 0,
        "reasons": dedup_reasons,
        "input_sample_rate_hz": sample_rate,
    }
