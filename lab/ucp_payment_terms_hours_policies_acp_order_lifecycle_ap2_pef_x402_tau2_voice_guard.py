"""Stage 76 deterministic protocol & runtime guard:
UCP Payment Terms Selection & Deterministic Location Hours / Core Policies / Media Variants,
ACP Native Order Post-Purchase Lifecycle & Message Resolution / Version Negotiation,
Google AP2 Multi-Hop SD-JWT Delegation Chain / Payment Evidence Frame (PEF) & Coinbase x402 Bazaar / Facilitator / Attestation Guards,
and Sierra tau2-bench Voice Role-Flip Whitespace / Qwen Realtime Nested Tools / Usage-Cost & Parallel WorkQueue Lease Guards.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

VALID_WEEKDAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_OFFSET_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
URI_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")

ACP_RESOLUTIONS = {"recoverable", "requires_buyer_input", "requires_buyer_review"}
ACP_FULFILLMENT_TYPES = {"shipping", "pickup", "digital"}
ACP_ADJUSTMENT_TYPES = {"refund", "credit", "return", "dispute", "chargeback"}

PEF_CLAIM_TYPES = {
    "payment_admission",
    "payment_settlement",
    "payment_cancellation",
    "payment_refund",
    "composite_verdict",
}
COMPLIANCE_VERDICTS = {"ALLOW", "REFER", "DENY"}
SETTLEMENT_STATES = {"SETTLED", "PENDING_FINALITY", "REVERSED"}
TRUST_VERDICTS = {"TRUSTED", "PROVISIONAL", "INSUFFICIENT_EVIDENCE", "UNTRUSTED"}

X402_TESTNET_NETWORKS = {"eip155:84532", "eip155:11142220", "eip155:421614", "solana:devnet"}
X402_REGISTERED_EIP3009_USDC = {
    "eip155:8453": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "eip155:42220": "0xceba9300f2b948710d2653dd7b07f33a8b32118c",
    "eip155:11142220": "0x01c5c0122039549ad1493b8220cabedd739bc44e",
    "eip155:42161": "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
}

TAU2_DEFAULT_VOICE_CONCURRENCY = {
    "gemini": 40,
    "openai": 40,
    "xai": 40,
    "livekit": 10,
    "nova": 5,
    "qwen": 5,
}


def _jcs_sha256(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_ucp_payment_terms_deterministic_hours_policies_and_media_variants(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify UCP PRs #712/#692/#603/#741 (Payment Terms selection & simplification),
    PR #687/#589 (Location deterministic operating hours & open_at),
    and PRs #572/#688/#671/#690 (core policies[], destination authorship, media variants).
    """
    violations: list[str] = []

    # 1. Payment Terms Checkout Selection & Simplification (#712, #692, #603, #741)
    payment = payload.get("payment") or {}
    terms = payment.get("terms")
    selected_term_id = payment.get("selected_term_id")
    instruments = payment.get("instruments") or []
    messages = payload.get("messages") or []

    for inst in instruments:
        if "term_refs" in inst:
            violations.append("UCP_DEPRECATED_INSTRUMENT_TERM_REFS_FORBIDDEN")

    selected_term: dict[str, Any] | None = None
    if terms is not None:
        if not isinstance(terms, list):
            violations.append("UCP_PAYMENT_TERMS_NOT_ARRAY")
        else:
            term_ids: set[str] = set()
            for idx, term in enumerate(terms):
                tid = term.get("id")
                if not isinstance(tid, str) or not tid.strip():
                    violations.append(f"UCP_PAYMENT_TERM_ID_MISSING:{idx}")
                else:
                    term_ids.add(tid)
                if term.get("is_subscription") or term.get("recurrence"):
                    violations.append(f"UCP_SUBSCRIPTION_IN_PAYMENT_TERMS_FORBIDDEN:{tid}")
                schedules = term.get("schedules")
                if not isinstance(schedules, list) or not schedules:
                    violations.append(f"UCP_PAYMENT_TERM_SCHEDULES_EMPTY:{tid}")
                else:
                    for s_idx, sched in enumerate(schedules):
                        if "totals" in sched:
                            violations.append(
                                f"UCP_PAYMENT_SCHEDULE_TOTALS_ARRAY_FORBIDDEN:{tid}:{s_idx}"
                            )
                        amt = sched.get("amount")
                        if not isinstance(amt, int) or isinstance(amt, bool) or amt < 0:
                            violations.append(
                                f"UCP_PAYMENT_SCHEDULE_SCALAR_AMOUNT_INVALID:{tid}:{s_idx}"
                            )
                        desc = sched.get("description")
                        if not isinstance(desc, str) or not desc.strip():
                            violations.append(
                                f"UCP_PAYMENT_SCHEDULE_DESCRIPTION_REQUIRED:{tid}:{s_idx}"
                            )
                        due_at = sched.get("due_at")
                        if due_at is not None and (
                            not isinstance(due_at, str)
                            or not RFC3339_OFFSET_RE.match(due_at)
                        ):
                            violations.append(
                                f"UCP_PAYMENT_SCHEDULE_DUE_AT_INVALID:{tid}:{s_idx}"
                            )
                if tid == selected_term_id:
                    selected_term = term

            if selected_term_id is not None and selected_term is None:
                violations.append("UCP_SELECTED_PAYMENT_TERM_NOT_FOUND")

    if selected_term is not None:
        schedules = selected_term.get("schedules") or []
        if len(schedules) > 1 and (
            payment.get("split_payments") or len(instruments) > 1
        ):
            violations.append(
                "UCP_MULTI_SCHEDULE_TERM_SPLIT_PAYMENT_COMPOSITION_FORBIDDEN"
            )

    if payment.get("previous_selected_term_id") and (
        payment.get("previous_selected_term_id") != selected_term_id
        and payment.get("business_repriced_or_changed_term", False)
    ):
        has_term_warning = any(
            m.get("type") == "warning" and m.get("code") == "payment_term_changed"
            for m in messages
            if isinstance(m, dict)
        )
        if not has_term_warning:
            violations.append("UCP_PAYMENT_TERM_CHANGED_WARNING_REQUIRED")

    # 2. Location Service Deterministic Operating Hours (#687, #589)
    location = payload.get("location") or {}
    hours = location.get("hours")
    exceptions = location.get("exceptions")
    tz = location.get("timezone")

    if (hours is not None or exceptions is not None) and (
        not isinstance(tz, str) or "/" not in tz
    ):
        violations.append("UCP_LOCATION_IANA_TIMEZONE_REQUIRED")

    if isinstance(hours, list):
        for idx, h in enumerate(hours):
            if "open" in h or "close" in h:
                violations.append(f"UCP_HOURS_LEGACY_OPEN_CLOSE_KEYS_FORBIDDEN:{idx}")
            day = h.get("day")
            if day not in VALID_WEEKDAYS:
                violations.append(f"UCP_HOURS_INVALID_WEEKDAY:{idx}:{day}")
            opens = h.get("opens")
            closes = h.get("closes")
            if not isinstance(opens, str) or not isinstance(closes, str):
                violations.append(f"UCP_WEEKLY_HOURS_OPENS_CLOSES_PAIR_REQUIRED:{idx}")
            elif not HHMM_RE.match(opens) or not HHMM_RE.match(closes):
                violations.append(f"UCP_WEEKLY_HOURS_TIME_FORMAT_INVALID:{idx}")
            elif opens == closes:
                violations.append(f"UCP_HOURS_AMBIGUOUS_EQUAL_TIME_PAIR_FORBIDDEN:{idx}")

    if isinstance(exceptions, list):
        seen_ranges: list[tuple[str, str]] = []
        for idx, exc in enumerate(exceptions):
            if any(k in exc for k in ("from", "through", "label", "open", "close")):
                violations.append(f"UCP_EXCEPTION_HOURS_LEGACY_KEYS_FORBIDDEN:{idx}")
            vf = exc.get("valid_from")
            vt = exc.get("valid_through")
            if (
                not isinstance(vf, str)
                or not isinstance(vt, str)
                or not DATE_RE.match(vf)
                or not DATE_RE.match(vt)
                or vf > vt
            ):
                violations.append(f"UCP_EXCEPTION_HOURS_DATE_BOUNDS_INVALID:{idx}")
            else:
                for prev_vf, prev_vt in seen_ranges:
                    # Intersecting non-identical exception ranges are forbidden
                    if max(vf, prev_vf) <= min(vt, prev_vt) and (vf, vt) != (
                        prev_vf,
                        prev_vt,
                    ):
                        violations.append(
                            f"UCP_EXCEPTION_HOURS_OVERLAP_FORBIDDEN:{idx}"
                        )
                        break
                seen_ranges.append((vf, vt))

            has_opens = "opens" in exc and exc.get("opens") is not None
            has_closes = "closes" in exc and exc.get("closes") is not None
            if has_opens != has_closes:
                violations.append(
                    f"UCP_EXCEPTION_HOURS_INSEPARABLE_OPENS_CLOSES:{idx}"
                )
            elif has_opens and has_closes:
                o_val = exc["opens"]
                c_val = exc["closes"]
                if (
                    not isinstance(o_val, str)
                    or not isinstance(c_val, str)
                    or not HHMM_RE.match(o_val)
                    or not HHMM_RE.match(c_val)
                ):
                    violations.append(f"UCP_EXCEPTION_HOURS_TIME_FORMAT_INVALID:{idx}")
                elif o_val == c_val:
                    violations.append(
                        f"UCP_EXCEPTION_HOURS_EQUAL_TIME_CLOSURE_FORBIDDEN:{idx}"
                    )

    location_filters = payload.get("location_filters") or {}
    hours_filter = location_filters.get("hours")
    if isinstance(hours_filter, dict):
        if "open_now" in hours_filter:
            violations.append("UCP_IMPLICIT_OPEN_NOW_FILTER_FORBIDDEN")
        open_at = hours_filter.get("open_at")
        if open_at is not None and (
            not isinstance(open_at, str) or not RFC3339_OFFSET_RE.match(open_at)
        ):
            violations.append("UCP_HOURS_FILTER_OPEN_AT_OFFSET_REQUIRED")

    # 3. Core policies[] Disclosure Linkage, Destination Authorship & Media (#572, #688, #671, #690)
    policies = payload.get("policies")
    if isinstance(policies, list):
        for idx, pol in enumerate(policies):
            ptype = pol.get("type")
            desc = pol.get("description")
            if not isinstance(ptype, str) or "." not in ptype:
                violations.append(f"UCP_POLICY_RDNS_TYPE_REQUIRED:{idx}")
            if not isinstance(desc, dict) or not str(desc.get("plain", "")).strip():
                violations.append(f"UCP_POLICY_PLAIN_DESCRIPTION_REQUIRED:{idx}")
            if ptype == "dev.ucp.shopping.policy.refund":
                has_window = "window" in pol and pol.get("window") is not None
                has_final = bool(pol.get("final_sale", False))
                if has_window and has_final:
                    violations.append(f"UCP_REFUND_POLICY_WINDOW_XOR_FINAL_SALE:{idx}")
                if has_final:
                    targets = pol.get("applies_to") or ["$"]
                    for target_path in targets:
                        has_disclosure = any(
                            m.get("type") == "warning"
                            and m.get("presentation") == "disclosure"
                            and m.get("code") == ptype
                            and m.get("path", "$") == target_path
                            for m in messages
                            if isinstance(m, dict)
                        )
                        if not has_disclosure:
                            violations.append(
                                f"UCP_POLICY_DISCLOSURE_WARNING_MISSING:{target_path}"
                            )

    fulfillment_request = payload.get("fulfillment_request") or {}
    for m_idx, method in enumerate(fulfillment_request.get("methods") or []):
        mtype = method.get("type")
        if mtype in {"pickup", "curbside"} and method.get("destinations"):
            violations.append(
                f"UCP_NON_SHIPPING_REQUEST_DESTINATIONS_AUTHORSHIP_FORBIDDEN:{m_idx}:{mtype}"
            )
        if method.get("auto_selected_from_context_location", False):
            violations.append(
                f"UCP_CONTEXT_LOCATION_AUTO_DESTINATION_SELECTION_FORBIDDEN:{m_idx}"
            )

    media_items = payload.get("media") or []
    for idx, item in enumerate(media_items):
        mtype = item.get("type", "image")
        url = item.get("url")
        if not isinstance(url, str) or not URI_RE.match(url):
            violations.append(f"UCP_MEDIA_URL_INVALID:{idx}")
        if mtype == "external_video" and item.get("sources"):
            violations.append(f"UCP_EXTERNAL_VIDEO_DIRECT_SOURCES_FORBIDDEN:{idx}")
        for s_idx, src in enumerate(item.get("sources") or []):
            if not isinstance(src.get("mime_type"), str) or "/" not in src.get("mime_type", ""):
                violations.append(f"UCP_MEDIA_SOURCE_MIME_TYPE_REQUIRED:{idx}:{s_idx}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
        "selected_term_id": selected_term_id,
        "location_timezone": tz,
    }


def verify_acp_post_purchase_order_lifecycle_resolution_intervention_and_version_negotiation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify ACP PR #106 (SEP #105 Native Orders lifecycle tracking),
    PRs #100/#143/#118/#115 (Message.resolution, intervention_required vs requires_3ds, Error vs MessageError),
    and PRs #99/#117 (supported_versions[] negotiation and continuous session fulfillment total parity).
    """
    violations: list[str] = []

    # 1. Native Orders Post-Purchase Lifecycle (#106)
    order = payload.get("order") or {}
    line_items = order.get("line_items") or []
    ordered_by_item: dict[str, int] = {}
    shipped_by_item: dict[str, int] = {}

    for idx, li in enumerate(line_items):
        li_id = li.get("id")
        qty = li.get("quantity") or {}
        ordered = qty.get("ordered")
        shipped = qty.get("shipped")
        if (
            not isinstance(li_id, str)
            or not isinstance(ordered, int)
            or not isinstance(shipped, int)
            or ordered < 0
            or shipped < 0
            or shipped > ordered
        ):
            violations.append(f"ACP_ORDER_LINE_ITEM_QUANTITY_INVALID:{idx}")
        else:
            ordered_by_item[li_id] = ordered
            shipped_by_item[li_id] = shipped

    fulfillments = order.get("fulfillments") or []
    fulfilled_accum: dict[str, int] = {}
    for f_idx, ful in enumerate(fulfillments):
        ftype = ful.get("type")
        if ftype not in ACP_FULFILLMENT_TYPES:
            violations.append(f"ACP_ORDER_FULFILLMENT_TYPE_INVALID:{f_idx}:{ftype}")
        for ref in ful.get("line_items") or []:
            rid = ref.get("id")
            rqty = ref.get("quantity")
            if rid not in ordered_by_item or not isinstance(rqty, int) or rqty <= 0:
                violations.append(f"ACP_ORDER_FULFILLMENT_ITEM_REF_INVALID:{f_idx}:{rid}")
            else:
                fulfilled_accum[rid] = fulfilled_accum.get(rid, 0) + rqty
                if fulfilled_accum[rid] > ordered_by_item[rid]:
                    violations.append(
                        f"ACP_ORDER_FULFILLMENT_EXCEEDS_ORDERED:{rid}"
                    )

    adjustments = order.get("adjustments") or []
    for a_idx, adj in enumerate(adjustments):
        atype = adj.get("type")
        amt = adj.get("amount")
        if atype not in ACP_ADJUSTMENT_TYPES:
            violations.append(f"ACP_ORDER_ADJUSTMENT_TYPE_INVALID:{a_idx}:{atype}")
        if not isinstance(amt, int) or isinstance(amt, bool) or amt < 0:
            violations.append(f"ACP_ORDER_ADJUSTMENT_MINOR_AMOUNT_INVALID:{a_idx}")

    # 2. Message.resolution & intervention_required vs requires_3ds (#100, #143, #118, #115)
    messages = payload.get("messages") or []
    for m_idx, msg in enumerate(messages):
        res = msg.get("resolution")
        if res is not None and res not in ACP_RESOLUTIONS:
            violations.append(f"ACP_MESSAGE_RESOLUTION_INVALID:{m_idx}:{res}")
        if msg.get("type") == "error":
            code = msg.get("code")
            reason = msg.get("failure_context")
            if reason == "capability_mismatch" and code != "intervention_required":
                violations.append(
                    f"ACP_CAPABILITY_MISMATCH_REQUIRES_INTERVENTION_REQUIRED_CODE:{m_idx}"
                )
            if reason == "missing_authentication_result_on_complete" and code != "requires_3ds":
                violations.append(
                    f"ACP_MISSING_AUTH_RESULT_REQUIRES_3DS_CODE:{m_idx}"
                )
        if "supported_versions" in msg:
            violations.append(f"ACP_TOP_LEVEL_ERROR_FIELD_ON_SESSION_MESSAGE:{m_idx}")

    # 3. Version mismatch supported_versions[] & continuous session fulfillment total parity (#99, #117)
    http_error = payload.get("http_error")
    if isinstance(http_error, dict):
        err_code = http_error.get("code")
        if err_code in {"unsupported_api_version", "missing_api_version"}:
            sup = http_error.get("supported_versions")
            if (
                not isinstance(sup, list)
                or not sup
                or not all(isinstance(v, str) and DATE_RE.match(v) for v in sup)
            ):
                violations.append("ACP_VERSION_ERROR_SUPPORTED_VERSIONS_REQUIRED")

    session_transition = payload.get("session_transition")
    if isinstance(session_transition, dict):
        prev_opt = session_transition.get("updated_fulfillment_option_id")
        prev_cost = session_transition.get("updated_fulfillment_cost_minor")
        prev_total = session_transition.get("updated_total_minor")
        terminal_opt = session_transition.get("terminal_fulfillment_option_id")
        terminal_cost = session_transition.get("terminal_fulfillment_cost_minor")
        terminal_total = session_transition.get("terminal_total_minor")
        if (
            prev_opt != terminal_opt
            or prev_cost != terminal_cost
            or prev_total != terminal_total
        ):
            violations.append("ACP_SESSION_TERMINAL_FULFILLMENT_TOTAL_DRIFT")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
        "tracked_line_items": len(ordered_by_item),
        "fulfillments_count": len(fulfillments),
        "adjustments_count": len(adjustments),
    }


def verify_ap2_sdjwt_delegation_chain_pef_attestation_and_x402_bazaar_facilitator_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Google AP2 PRs #350/#371/#159 (multi-hop ~~ SD-JWT delegation chain & Pydantic state serialization),
    AP2 PRs #274/#272/#271/#269/#276 (Payment Evidence Frame, Compliance/Settlement/Trust envelopes & spend cap),
    and Coinbase x402 PRs #283/#206/#244/#180/#317/#225/#136 (Bazaar format validation, public facilitator guard, Celo/Arbitrum USDC & counterparty attestation).
    """
    violations: list[str] = []

    # 1. Multi-Hop SD-JWT Delegation Chain (`~~` split before `~`) & Session State (#350, #159)
    raw_sdjwt_chain = payload.get("sd_jwt_chain", "")
    decoded_hops: list[dict[str, Any]] = []
    if isinstance(raw_sdjwt_chain, str) and raw_sdjwt_chain:
        if payload.get("decoder_split_single_tilde_first", False) and "~~" in raw_sdjwt_chain:
            violations.append("AP2_SDJWT_CHAIN_SINGLE_TILDE_SPLIT_CORRUPTION")
        raw_hops = raw_sdjwt_chain.split("~~")
        for h_idx, raw_hop in enumerate(raw_hops):
            parts = raw_hop.split("~")
            if len(parts) < 2 or not parts[0]:
                violations.append(f"AP2_SDJWT_HOP_MALFORMED:{h_idx}")
            else:
                issuer_jwt = parts[0]
                kb_jwt = parts[-1] if parts[-1] else None
                disclosures = [p for p in parts[1:-1] if p]
                decoded_hops.append(
                    {
                        "hop_index": h_idx,
                        "issuer_jwt": issuer_jwt,
                        "disclosures_count": len(disclosures),
                        "kb_jwt": kb_jwt,
                    }
                )

    session_state_entries = payload.get("session_state_entries") or []
    for s_idx, entry in enumerate(session_state_entries):
        if entry.get("stored_as_raw_pydantic_instance", False) or not entry.get(
            "serialized_via_model_dump", True
        ):
            violations.append(f"AP2_SESSION_STATE_UNSERIALIZED_PYDANTIC_MODEL:{s_idx}")

    # 2. Payment Evidence Frame (PEF), Compliance/Settlement/Trust & Session Spend Cap (#274, #272, #271, #269, #276)
    pef = payload.get("payment_evidence_frame")
    computed_frame_id: str | None = None
    if isinstance(pef, dict):
        claim_type = pef.get("claim_type")
        if claim_type not in PEF_CLAIM_TYPES:
            violations.append(f"AP2_PEF_CLAIM_TYPE_INVALID:{claim_type}")
        inner_receipt = pef.get("receipt") or {}
        expected_receipt_hash = _jcs_sha256(inner_receipt)
        if pef.get("receipt_hash") != expected_receipt_hash:
            violations.append("AP2_PEF_RECEIPT_HASH_MISMATCH")
        preimage = {
            k: v for k, v in pef.items() if k not in {"frame_id", "signature"}
        }
        computed_frame_id = _jcs_sha256(preimage)
        if pef.get("frame_id") != computed_frame_id:
            violations.append("AP2_PEF_FRAME_ID_MISMATCH")

        comp_verdict = inner_receipt.get("compliance_verdict")
        if comp_verdict is not None and comp_verdict not in COMPLIANCE_VERDICTS:
            violations.append(f"AP2_COMPLIANCE_RECEIPT_VERDICT_INVALID:{comp_verdict}")
        settle_state = inner_receipt.get("settlement_result")
        if settle_state is not None and settle_state not in SETTLEMENT_STATES:
            violations.append(f"AP2_SETTLEMENT_ATTESTATION_STATE_INVALID:{settle_state}")
        trust_verdict = inner_receipt.get("composite_trust_verdict")
        if trust_verdict is not None and trust_verdict not in TRUST_VERDICTS:
            violations.append(f"AP2_COMPOSITE_TRUST_VERDICT_INVALID:{trust_verdict}")

    spend_cap = payload.get("session_spend_cap_minor")
    cumulative_spend = payload.get("session_cumulative_spend_minor", 0)
    requested_spend = payload.get("requested_payment_minor", 0)
    if isinstance(spend_cap, int) and cumulative_spend + requested_spend > spend_cap:
        violations.append("AP2_AGENT_SPEND_CAP_EXCEEDED_402")

    # 3. Coinbase x402 Bazaar Format Validation, Public Facilitator Guard, Celo/Arbitrum USDC & Attestation (#283, #206, #244, #180, #225, #136)
    x402 = payload.get("x402") or {}
    bazaar = x402.get("bazaar_discovery")
    if isinstance(bazaar, dict):
        if not bazaar.get("ajv_formats_registered", True):
            violations.append("X402_BAZAAR_AJV_FORMATS_UNREGISTERED")
        endpoint_uri = bazaar.get("resource_uri", "")
        updated_at = bazaar.get("updated_at", "")
        if not isinstance(endpoint_uri, str) or not URI_RE.match(endpoint_uri):
            violations.append("X402_BAZAAR_RESOURCE_URI_FORMAT_INVALID")
        if not isinstance(updated_at, str) or not RFC3339_OFFSET_RE.match(updated_at):
            violations.append("X402_BAZAAR_DATETIME_FORMAT_INVALID")

    facilitator_url = x402.get("facilitator_url", "")
    network = x402.get("network", "")
    if (
        facilitator_url.rstrip("/") == "https://x402.org/facilitator"
        and network
        and network not in X402_TESTNET_NETWORKS
    ):
        violations.append(f"X402_PUBLIC_FACILITATOR_MAINNET_MISMATCH:{network}")

    usdc_asset = x402.get("usdc_asset")
    if isinstance(usdc_asset, dict) and network in X402_REGISTERED_EIP3009_USDC:
        expected_addr = X402_REGISTERED_EIP3009_USDC[network]
        actual_addr = str(usdc_asset.get("address", "")).lower()
        if actual_addr != expected_addr or usdc_asset.get("decimals") != 6 or usdc_asset.get("transfer_method") != "EIP-3009":
            violations.append(f"X402_REGISTERED_STABLECOIN_CONFIG_MISMATCH:{network}")

    attestation = x402.get("counterparty_attestation")
    if isinstance(attestation, dict):
        issuer_did = attestation.get("issuer_did", "")
        merchant_did = attestation.get("merchant_did", "")
        if not issuer_did.startswith("did:") or issuer_did == merchant_did:
            violations.append("X402_SELF_ASSERTED_COUNTERPARTY_ATTESTATION_FORBIDDEN")
        if not attestation.get("ed25519_signature_verified", False):
            violations.append("X402_COUNTERPARTY_ATTESTATION_SIGNATURE_INVALID")
        if attestation.get("contains_subjective_judgment_field", False):
            violations.append("X402_FACT_ATTESTATION_SUBJECTIVE_JUDGMENT_FORBIDDEN")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
        "decoded_hops_count": len(decoded_hops),
        "computed_frame_id": computed_frame_id,
    }


def verify_tau2_voice_role_flip_qwen_nested_tools_usage_cost_and_parallel_lease_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Sierra tau2-bench PRs #440/#526/#523/#521 (voice role-flip whitespace drop & tri-state realtime user generation),
    PRs #449/#450 (Qwen qwen3.5-omni-plus-realtime nested function tool schema),
    and PRs #454/#456/#455/#483/#546/#535 (audio-native usage/cost accounting, concurrency caps, parallel WorkQueue leases & tau-voice boundary).
    """
    violations: list[str] = []

    # 1. Voice Streaming User Simulator Role-Flip Whitespace Guard (#440) & Tri-State Realtime Generation (#526)
    raw_turns = payload.get("flipped_role_turns") or []
    retained_turns: list[dict[str, Any]] = []
    for idx, turn in enumerate(raw_turns):
        content = str(turn.get("content") or "")
        tool_calls = turn.get("tool_calls") or []
        if not content.strip() and not tool_calls:
            if turn.get("retained_after_flip", False):
                violations.append(f"TAU2_VOICE_ROLE_FLIP_WHITESPACE_TURN_LEAKED:{idx}")
        else:
            retained_turns.append(turn)

    provider = str(payload.get("audio_native_provider", "openai")).lower()
    cli_realtime_override = payload.get("cli_realtime_generation_override")
    expected_realtime = (
        bool(cli_realtime_override)
        if cli_realtime_override is not None
        else (provider == "openai")
    )
    if payload.get("effective_realtime_generation", expected_realtime) != expected_realtime:
        violations.append("TAU2_REALTIME_USER_GENERATION_RESOLUTION_MISMATCH")

    # 2. Qwen Realtime Tool Calling Wire Format (#449, #450)
    qwen_cfg = payload.get("qwen_session_config")
    if isinstance(qwen_cfg, dict):
        model = qwen_cfg.get("model", "")
        tools = qwen_cfg.get("tools") or []
        if tools and model == "qwen3-omni-flash-realtime":
            violations.append("TAU2_QWEN_FLASH_MODEL_TOOL_CALLING_UNSUPPORTED")
        for t_idx, tool in enumerate(tools):
            if tool.get("type") != "function" or not isinstance(tool.get("function"), dict):
                violations.append(f"TAU2_QWEN_FLATTENED_TOOL_SCHEMA_FORBIDDEN:{t_idx}")
        if "tool_choice" in qwen_cfg:
            violations.append("TAU2_QWEN_UNSUPPORTED_TOOL_CHOICE_PARAM_FORBIDDEN")
        vad = qwen_cfg.get("turn_detection") or {}
        if "prefix_padding_ms" in vad:
            violations.append("TAU2_QWEN_VAD_PREFIX_PADDING_MS_FORBIDDEN")
        if qwen_cfg.get("voice") == "Cherry" and model == "qwen3.5-omni-plus-realtime":
            violations.append("TAU2_QWEN_3_5_LEGACY_CHERRY_VOICE_DEFAULT_FORBIDDEN")

    # 3. Audio-Native Usage/Cost Accounting (#454), Concurrency Limits (#456), Parallel WorkQueue Leases (#455) & Standard Boundary (#483, #535)
    usage_records = payload.get("usage_records") or []
    cumulative_by_scope: dict[str, int] = {}
    delta_sum = 0
    for u_idx, rec in enumerate(usage_records):
        mode = rec.get("accounting_mode", "delta")
        scope = rec.get("scope", "default")
        tokens = int(rec.get("tokens", 0))
        if mode == "cumulative":
            if rec.get("aggregated_by_summing_running_totals", False):
                violations.append(f"TAU2_CUMULATIVE_USAGE_DOUBLE_COUNTED:{u_idx}")
            cumulative_by_scope[scope] = tokens
        else:
            delta_sum += tokens

        if rec.get("pricing_status") in {"unknown_model", "unverified"}:
            if rec.get("cost_usd") is not None:
                violations.append(
                    f"TAU2_UNKNOWN_MODEL_SILENT_ZERO_COST_FORBIDDEN:{u_idx}"
                )

    requested_concurrency = payload.get("requested_concurrency")
    has_explicit_override = payload.get("explicit_provider_limit_override", False)
    default_cap = TAU2_DEFAULT_VOICE_CONCURRENCY.get(provider)
    if (
        default_cap is not None
        and isinstance(requested_concurrency, int)
        and requested_concurrency > default_cap
        and not has_explicit_override
    ):
        violations.append(
            f"TAU2_VOICE_PROVIDER_CONCURRENCY_CAP_EXCEEDED:{provider}:{requested_concurrency}>{default_cap}"
        )

    work_queue = payload.get("parallel_work_queue")
    if isinstance(work_queue, dict):
        if work_queue.get("worker_writes_checkpoint_directly", False):
            violations.append("TAU2_PARALLEL_WORKER_DIRECT_CHECKPOINT_WRITE_FORBIDDEN")
        if work_queue.get("expired_lease_requeued_above_max_retries", False):
            violations.append("TAU2_PARALLEL_LEASE_RETRY_CAP_EXCEEDED")

    submission = payload.get("voice_submission")
    if isinstance(submission, dict):
        if submission.get("track") == "standard" and (
            submission.get("modified_benchmark_prompts_or_tools", False)
            or submission.get("trained_on_taubench_eval_data", False)
        ):
            violations.append("TAU2_VOICE_STANDARD_TRACK_BOUNDARY_VIOLATION")
        if submission.get("contains_unsanitized_reviewer_notes", False):
            violations.append("TAU2_ELICITATION_RAW_REVIEWER_EXPORT_LEAK")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
        "retained_turns_count": len(retained_turns),
        "effective_realtime_generation": expected_realtime,
        "normalized_total_tokens": delta_sum + sum(cumulative_by_scope.values()),
    }
