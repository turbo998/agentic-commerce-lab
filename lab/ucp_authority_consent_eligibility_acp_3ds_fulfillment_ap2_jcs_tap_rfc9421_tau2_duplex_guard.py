"""Stage 80 deterministic protocol & evaluation guard:
UCP Namespace Authority Binding (`#530`), Per-Segment Buyer Consent (`#451`), Eligibility Claims & Verification Contract (`#250`), Payment Auth Actions (`#458`), Admission-Time Mandate TTL (`#540`), Raw `r||s` ECDSA Signatures (`#590`), Embedded `params.error` (`#494`) & Link/Cart Continuity (`#247`, `#246`),
ACP Consumer 3DS (`#53`), Mixed-Cart Fulfillment & Address Contact (`#52`, `#51`), Return Policy Link (`#49`), TLS 1.3 (`#32`), 6–8 Digit IIN (`#9`), B2B Decimal Quantities (`#3`) & Exact 4-Digit `display_last4` (`#1`),
Google AP2 RFC 8785 JCS Cart-to-Payment Mandate Binding (`#251`), DID + STARK Settlement (`#257`), Typed `PaymentDetailsModifier` (`#48`) & Visa TAP RFC 9421 Merchant-Backend Signature Verifier (`#21`),
and Sierra tau2-bench Full-Duplex Voice Rescoring (`#399`), Banking Reverse-Chronological Ordering (`#403`), Lost/Stolen Discoverable Read Calls (`#402`), Nested JSON/Numeric Normalization (`#401`, `#397`), Batch Replay Isolation (`#393`), Platinum 10% Cash-Back Consistency (`#388`) & Airline/LLM Execution Fixes (`#362`, `#361`, `#360`, `#358`).
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


RDNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
DER_BASE64_PREFIXES = ("MEUC", "MEQC", "MEYCI")
IIN_RE = re.compile(r"^\d{6,8}$")
LAST4_RE = re.compile(r"^\d{4}$")
INDIVIDUAL_QUOTED_COMPONENTS_RE = re.compile(r'^\("(?:[^"\s]+)"(?:\s+"(?:[^"\s]+)")*\)$')


def _is_valid_rdns(identifier: str) -> bool:
    parts = str(identifier).split(".")
    if len(parts) < 3:
        return False
    return all(bool(RDNS_LABEL_RE.match(p)) for p in parts)


def _compute_rdns_authority_domain(rdns_name: str) -> str:
    parts = str(rdns_name).split(".")
    if len(parts) < 2:
        return ""
    return f"{parts[1]}.{parts[0]}".lower()


def verify_ucp_authority_consent_eligibility_mandate_ttl_and_signature_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify UCP PRs #590, #540, #530, #507, #494, #485, #458, #451, #265, #250, #247, #246."""
    violations: list[str] = []

    # 1. Namespace Authority Binding & broadened RDNS grammar (#530)
    for idx, cap in enumerate(payload.get("capabilities", [])):
        name = str(cap.get("name", ""))
        schema_url = str(cap.get("schema", ""))
        if not _is_valid_rdns(name):
            violations.append(f"UCP_RDNS_GRAMMAR_INVALID:{idx}")
            continue
        parsed = urlparse(schema_url)
        expected_domain = _compute_rdns_authority_domain(name)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            host == expected_domain or host.endswith("." + expected_domain)
        ):
            violations.append(
                f"UCP_NAMESPACE_AUTHORITY_BINDING_MISMATCH:{idx}:{host}!={expected_domain}"
            )

    # 2. Per-purpose & per-segment buyer consent (#451)
    consent_map = payload.get("buyer", {}).get("consent", {})
    if isinstance(consent_map, dict):
        for purpose_key, entry in consent_map.items():
            if not _is_valid_rdns(purpose_key):
                violations.append(f"UCP_CONSENT_PURPOSE_RDNS_INVALID:{purpose_key}")
            if not isinstance(entry, dict):
                violations.append(f"UCP_CONSENT_OBJECT_INVALID:{purpose_key}")
                continue
            if not isinstance(entry.get("granted"), bool) or entry.get("source") not in {
                "business",
                "platform",
            }:
                violations.append(f"UCP_CONSENT_STATE_OR_SOURCE_INVALID:{purpose_key}")
            segments = entry.get("segments", {})
            if isinstance(segments, dict):
                for seg_key, seg_val in segments.items():
                    if not _is_valid_rdns(seg_key) or not isinstance(
                        seg_val.get("granted"), bool
                    ):
                        violations.append(
                            f"UCP_CONSENT_SEGMENT_INVALID:{purpose_key}:{seg_key}"
                        )

    # 3. Eligibility claims & verification contract at checkout completion (#250)
    eligibility = payload.get("eligibility_verification", {})
    if eligibility:
        for claim in eligibility.get("claims", []):
            if claim.get("influenced_checkout") is True and claim.get("status") not in {
                "verified",
                "rescinded",
            }:
                violations.append(
                    f"UCP_UNRESOLVED_ELIGIBILITY_CLAIM_BLOCKS_COMPLETE:{claim.get('id', 'unknown')}"
                )
        if eligibility.get("mutated_checkout_on_verification_failure") is True:
            violations.append("UCP_ELIGIBILITY_FAILURE_CHECKOUT_MUTATION_FORBIDDEN")

    # 4. Admission-time AP2 mandate TTL evaluation (#540)
    mandate_eval = payload.get("mandate_evaluation", {})
    if mandate_eval:
        if (
            mandate_eval.get("expired_at_admission") is True
            and mandate_eval.get("entered_complete_in_progress") is True
        ):
            violations.append("UCP_EXPIRED_MANDATE_ADMITTED_TO_COMPLETE_IN_PROGRESS")
        if (
            mandate_eval.get("expired_at_admission") is False
            and mandate_eval.get("expired_during_settlement") is True
            and mandate_eval.get("aborted_settlement_on_post_admission_expiry") is True
        ):
            violations.append("UCP_POST_ADMISSION_TTL_EXPIRY_MUST_NOT_ABORT_SETTLEMENT")

    # 5. Raw r||s ECDSA signature encoding (#590) & embedded params.error / link delegation / cart discount (#494, #247, #246)
    sig_val = str(payload.get("ecdsa_signature_b64", ""))
    if sig_val and sig_val.startswith(DER_BASE64_PREFIXES):
        violations.append("UCP_ECDSA_DER_SIGNATURE_ENCODING_FORBIDDEN_RAW_RS_REQUIRED")

    embedded = payload.get("embedded_session", {})
    if embedded:
        if embedded.get("is_error_notification") is True and not isinstance(
            embedded.get("params", {}).get("error"), dict
        ):
            violations.append("UCP_EMBEDDED_ERROR_MUST_WRAP_UNDER_PARAMS_ERROR")
        if (
            embedded.get("ec_delegate_link_open") is True
            and embedded.get("buyer_activated_link") is True
            and embedded.get("emitted_link_open_request") is not True
        ):
            violations.append("UCP_EMBEDDED_LINK_DELEGATION_OPEN_REQUEST_MISSING")

    cart_conv = payload.get("cart_to_checkout_conversion", {})
    if cart_conv:
        cart_codes = set(cart_conv.get("cart_discount_codes", []))
        checkout_codes = set(cart_conv.get("checkout_discount_codes", []))
        if not cart_codes.issubset(checkout_codes):
            violations.append("UCP_CART_DISCOUNT_CONTINUITY_DROPPED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify ACP PRs #53, #52, #51, #50, #49, #48, #32, #9, #7, #3, #1."""
    violations: list[str] = []

    # 1. TLS 1.3 requirement (#32)
    tls_version = str(payload.get("tls_version", "TLSv1.3"))
    if tls_version != "TLSv1.3":
        violations.append(f"ACP_TLS_1_3_REQUIRED:{tls_version}")

    # 2. Mixed-cart fulfillment selection & integer totals & shipping contact (#52, #51)
    fulfillment = payload.get("fulfillment", {})
    if fulfillment:
        addr = fulfillment.get("shipping_address", {})
        if addr:
            if not addr.get("name") or not (addr.get("phone") or addr.get("email")):
                violations.append("ACP_FULFILLMENT_ADDRESS_CONTACT_DETAILS_MISSING")
        for idx, opt in enumerate(fulfillment.get("shipping_options", [])):
            for field in ("subtotal", "tax", "total"):
                val = opt.get(field)
                if val is not None and (not isinstance(val, int) or isinstance(val, bool)):
                    violations.append(f"ACP_FULFILLMENT_OPTION_AMOUNT_NOT_INTEGER:{idx}:{field}")
        cart_item_ids = set(fulfillment.get("cart_line_item_ids", []))
        covered_ids = set(fulfillment.get("covered_line_item_ids", []))
        if cart_item_ids and cart_item_ids != covered_ids:
            violations.append("ACP_MIXED_CART_FULFILLMENT_COVERAGE_INCOMPLETE")

    # 3. Return policy link vs deprecated seller_shop_policies (#49)
    for idx, link in enumerate(payload.get("links", [])):
        if link.get("type") == "seller_shop_policies":
            violations.append(f"ACP_DEPRECATED_SELLER_SHOP_POLICIES_LINK_FORBIDDEN:{idx}")

    # 4. Card 6-8 digit IIN (#9) & exact 4-digit display_last4 (#1)
    card = payload.get("payment_method_card", {})
    if card:
        iin = str(card.get("iin", ""))
        last4 = str(card.get("display_last4", ""))
        if not IIN_RE.match(iin):
            violations.append(f"ACP_CARD_IIN_LENGTH_INVALID:{iin}")
        if not LAST4_RE.match(last4):
            violations.append(f"ACP_CARD_DISPLAY_LAST4_INVALID:{last4}")

    # 5. B2B positive decimal quantities (#3)
    for idx, item in enumerate(payload.get("line_items", [])):
        qty = item.get("quantity")
        if not isinstance(qty, (int, float)) or isinstance(qty, bool) or float(qty) <= 0.0:
            violations.append(f"ACP_B2B_LINE_ITEM_QUANTITY_NON_POSITIVE:{idx}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Google AP2 PRs #370, #257, #251, #48, #29, #20 and Visa TAP PR #21."""
    violations: list[str] = []

    # 1. AP2 RFC 8785 JCS CartMandate -> PaymentMandate binding (#251, #370)
    jcs_binding = payload.get("ap2_jcs_binding", {})
    if jcs_binding:
        if jcs_binding.get("canonicalization_scheme") != "RFC8785_JCS":
            violations.append("AP2_JCS_RFC8785_CANONICALIZATION_REQUIRED")
        if jcs_binding.get("cart_jcs_sha256") != jcs_binding.get("payment_mandate_cart_hash"):
            violations.append("AP2_CART_TO_PAYMENT_MANDATE_JCS_HASH_MISMATCH")

    # 2. AP2 DID + STARK settlement commitment (#257), Vertex AI modifier typing (#48) & VDC terminology (#20)
    ap2_meta = payload.get("ap2_mandate_metadata", {})
    if ap2_meta:
        if ap2_meta.get("did_settlement_enabled") is True and (
            not ap2_meta.get("delegation_did_verified")
            or not ap2_meta.get("stark_commitment_verified")
        ):
            violations.append("AP2_DID_STARK_SETTLEMENT_COMMITMENT_UNVERIFIED")
        if ap2_meta.get("payment_details_modifier_data_type") == "Any":
            violations.append("AP2_PAYMENT_DETAILS_MODIFIER_UNTYPED_ANY_FORBIDDEN")
        if ap2_meta.get("uses_legacy_vc_term") is True:
            violations.append("AP2_LEGACY_VC_TERM_FORBIDDEN_USE_VDC")

    # 3. Visa TAP RFC 9421 merchant-backend signature verifier (#21)
    tap_sig = payload.get("tap_rfc9421_verification", {})
    if tap_sig:
        if tap_sig.get("signature_base_ends_with_signature_params") is not True:
            violations.append("TAP_RFC9421_SIGNATURE_PARAMS_LINE_MISSING")
        comp_str = str(tap_sig.get("covered_components_raw", ""))
        if comp_str and not INDIVIDUAL_QUOTED_COMPONENTS_RE.match(comp_str):
            violations.append("TAP_RFC9421_COVERED_COMPONENTS_SINGLE_BLOB_INVALID")
        alg = str(tap_sig.get("alg", ""))
        key_type = str(tap_sig.get("agent_registry_key_type", ""))
        valid_pairs = {
            ("ed25519", "Ed25519PublicKey"),
            ("rsa-pss-sha256", "RSAPublicKey"),
        }
        if (alg, key_type) not in valid_pairs:
            violations.append(f"TAP_RFC9421_ALG_KEY_TYPE_CONFUSION:{alg}:{key_type}")
        if tap_sig.get("nonce_recorded_before_signature_verified") is True:
            violations.append("TAP_RFC9421_NONCE_RECORDED_BEFORE_VERIFICATION")
        if tap_sig.get("nonce_reused_before_expiry") is True:
            violations.append("TAP_RFC9421_NONCE_REPLAY_DETECTED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def verify_tau2_voice_rescoring_banking_ordering_and_llm_execution_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Sierra tau2-bench PRs #403, #402, #401, #399, #397, #393, #388, #362, #361, #360, #358."""
    violations: list[str] = []

    # 1. Full-duplex voice trajectory rescoring (#399)
    rescore = payload.get("voice_trajectory_rescoring", {})
    if rescore:
        if rescore.get("is_full_duplex_voice") is True:
            if (
                rescore.get("passed_communication_mode") != "FULL_DUPLEX"
                or rescore.get("evaluated_field") != "simulation.ticks"
            ):
                violations.append("TAU2_FULL_DUPLEX_VOICE_RESCORED_AS_HALF_DUPLEX_MESSAGES")

    # 2. Banking transaction reverse-chronological ordering (#403), lost/stolen discoverable reads (#402) & 10% cash-back doc (#388)
    banking = payload.get("banking_knowledge_eval", {})
    if banking:
        if banking.get("transactions_most_recent_first") is not True:
            violations.append("TAU2_BANKING_TRANSACTIONS_NOT_REVERSE_CHRONOLOGICAL")
        if banking.get("duplicate_dispute_targeted_earliest") is not True:
            violations.append("TAU2_BANKING_DUPLICATE_DISPUTE_MUST_TARGET_EARLIEST")
        if (
            banking.get("unlocked_discoverable_card_reads") is True
            and banking.get("called_unlocked_discoverable_card_reads") is not True
        ):
            violations.append("TAU2_BANKING_LOST_STOLEN_GOLD_SKIPPED_DISCOVERABLE_READS")
        if banking.get("platinum_rewards_doc_002_title_rate_pct") != 10:
            violations.append("TAU2_BANKING_PLATINUM_DOC_002_CONTRADICTORY_4PCT_TITLE")

    # 3. Nested JSON string & numeric tool arg normalization (#401, #397) & batch replay fault isolation (#393)
    grader = payload.get("action_and_replay_grader", {})
    if grader:
        if grader.get("normalized_nested_json_strings") is not True:
            violations.append("TAU2_ACTION_GRADER_NESTED_JSON_WHITESPACE_MISMATCH")
        if grader.get("normalized_numeric_int_float_args") is not True:
            violations.append("TAU2_DB_HASH_INT_FLOAT_SPELLING_SENSITIVITY")
        if grader.get("batch_aborted_on_single_simulation_replay_error") is True:
            violations.append("TAU2_BATCH_EVALUATION_ABORTED_BY_SINGLE_REPLAY_ERROR")

    # 4. Airline seat release (#362), UserMessage tool_calls (#361), ContextWindowExceeded (#360) & reasoning temperature (#358)
    runtime = payload.get("runtime_and_airline", {})
    if runtime:
        if (
            runtime.get("reservation_cancelled") is True
            and runtime.get("seats_restored_to_inventory") is not True
        ):
            violations.append("TAU2_AIRLINE_CANCELLED_SEATS_NOT_RELEASED")
        if runtime.get("preserved_user_message_tool_calls") is not True:
            violations.append("TAU2_LITELLM_USER_MESSAGE_TOOL_CALLS_DROPPED")
        if runtime.get("retried_context_window_exceeded_as_infra_error") is True:
            violations.append("TAU2_CONTEXT_WINDOW_EXCEEDED_MISCLASSIFIED_AS_INFRA_ERROR")
        if (
            runtime.get("is_reasoning_model") is True
            and runtime.get("sent_zero_temperature_param") is True
        ):
            violations.append("TAU2_REASONING_MODEL_ZERO_TEMPERATURE_BAD_REQUEST")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
