"""Stage 104 deterministic guardrails across UCP, ACP, Google AP2 + Coinbase x402, and Sierra tau2-bench.

Covers:
1. UCP PR #566/#483 (Canonical `keys[]` JWK Set & Web Bot Auth `tag="web-bot-auth"` dual-audience signature),
   PR #538 (`dev.ucp.common.ask` read-only natural-language Q&A),
   PR #530 (Reverse-domain `schema` URL authority binding vs. free-origin `https://` `spec` URL), and
   PR #460 (`Rating.distribution` and `verified_count` conservation).
2. ACP PR #53/#52 (Consumer 3DS & enhanced mixed-cart fulfillment + contact details),
   PR #9 (ISO/IEC 7812-1 6-to-8 digit `iin` & 4-digit `display_last4`), and
   PR #3 (B2B fractional decimal quantities with `exclusiveMinimum: 0`).
3. Google AP2 PR #243 (Normative verifier `checkout_hash` recomputation obligation),
   PR #252 (Cross-merchant cumulative budget enforcement), and
   Coinbase x402 PR #354 (SpendGuard per-call & rolling-window USDC cap).
4. Sierra tau2-bench PR #584 (Omit contentless tool-call turns from NL judge prompt),
   PR #581 (Reject NL-assertion judge replies with wrong number of verdicts),
   PR #570 (Paired row-wise list sorting in `Action.compare_with_tool_call`),
   PR #569 (Union-key check when gold arguments are omitted), and
   PR #566 (Deterministic sorted `KnowledgeBase.load` path order).
"""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Any


def validate_ucp_wba_keys_ask_rdns_authority_and_rating_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #566/#483 canonical keys[] & WBA signature, #538 ask Q&A, #530 RDNS schema authority, and #460 Rating."""
    violations: list[str] = []

    # 1. UCP #566 & #483: Canonical keys[] JWK Set & WBA dual-audience signature
    prof = payload.get("profile_keys_and_wba", {})
    if bool(prof.get("has_legacy_signing_keys_field", False)):
        violations.append("UCP_566_LEGACY_SIGNING_KEYS_FIELD_FORBIDDEN")
    keys = prof.get("keys", [])
    if not isinstance(keys, list) or len(keys) == 0:
        violations.append("UCP_566_MISSING_CANONICAL_KEYS_JWKS")

    if bool(prof.get("is_wba_dual_audience", False)):
        if str(prof.get("signature_tag", "")) != "web-bot-auth":
            violations.append("UCP_483_WBA_MISSING_WEB_BOT_AUTH_TAG")
        covered = set(prof.get("covered_components", []))
        if "ucp-agent" not in covered or "signature-agent" not in covered:
            violations.append("UCP_483_WBA_MISSING_DUAL_AUDIENCE_COMPONENTS")
        if not bool(prof.get("keyid_is_rfc7638_thumbprint", False)):
            violations.append("UCP_483_WBA_KEYID_NOT_RFC7638_THUMBPRINT")
        created = int(prof.get("created", 0))
        expires = int(prof.get("expires", 0))
        if created <= 0 or expires <= created:
            violations.append("UCP_483_WBA_INVALID_CREATED_EXPIRES_WINDOW")

    # 2. UCP #538: dev.ucp.common.ask read-only natural-language Q&A
    ask = payload.get("ask_capability", {})
    if bool(ask.get("mutated_commerce_state", False)):
        violations.append("UCP_538_ASK_CAPABILITY_MUTATED_COMMERCE_STATE")
    if bool(ask.get("superseded_structured_capability", False)):
        violations.append("UCP_538_ASK_SUPERSEDED_STRUCTURED_CAPABILITY")
    if not str(ask.get("answer_plain", "")).strip():
        violations.append("UCP_538_EMPTY_ASK_PLAIN_ANSWER")

    # 3. UCP #530: Reverse-domain schema URL authority binding
    rdns = payload.get("rdns_authority_binding", {})
    cap_name = str(rdns.get("capability_name", "")).strip()
    schema_url = str(rdns.get("schema_url", "")).strip()
    spec_url = str(rdns.get("spec_url", "")).strip()
    parts = cap_name.split(".")
    if len(parts) < 3:
        violations.append("UCP_530_INVALID_RDNS_CAPABILITY_NAME")
    else:
        expected_authority = f"{parts[1]}.{parts[0]}"
        parsed_schema = urlparse(schema_url)
        host = (parsed_schema.hostname or "").lower()
        if parsed_schema.scheme != "https" or not (
            host == expected_authority or host.endswith("." + expected_authority)
        ):
            violations.append("UCP_530_SCHEMA_URL_AUTHORITY_MISMATCH")
    parsed_spec = urlparse(spec_url)
    if parsed_spec.scheme != "https" or not parsed_spec.hostname:
        violations.append("UCP_530_SPEC_URL_NOT_HTTPS")

    # 4. UCP #460: Rating distribution & verified_count conservation
    rating = payload.get("rating_check", {})
    total_count = int(rating.get("count", 0))
    verified_count = int(rating.get("verified_count", 0))
    dist = rating.get("distribution", {})
    dist_sum = sum(int(v) for v in dist.values()) if isinstance(dist, dict) else 0
    if verified_count < 0 or verified_count > total_count:
        violations.append("UCP_460_VERIFIED_COUNT_EXCEEDS_TOTAL_COUNT")
    if dist_sum > total_count:
        violations.append("UCP_460_DISTRIBUTION_SUM_EXCEEDS_TOTAL_COUNT")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #53/#52 consumer 3DS & mixed fulfillment, #9 8-char IIN, and #3 B2B decimal quantities."""
    violations: list[str] = []

    # 1. ACP #52 & #53: Mixed-cart fulfillment options, shipping contact details & complete shipping address
    ff = payload.get("fulfillment_and_3ds", {})
    addr = ff.get("fulfillment_address", {})
    if bool(ff.get("has_physical_shipping", True)):
        for field in ("name", "phone", "email"):
            if not str(addr.get(field, "")).strip():
                violations.append(f"ACP_52_MISSING_FULFILLMENT_CONTACT_FIELD:{field}")
    cart_item_ids = set(ff.get("cart_line_item_ids", []))
    covered_item_ids = set(ff.get("fulfillment_covered_item_ids", []))
    if cart_item_ids != covered_item_ids:
        violations.append("ACP_52_MIXED_CART_ITEMS_NOT_FULLY_COVERED_BY_FULFILLMENT_OPTIONS")
    if bool(ff.get("tax_computed_at_complete", False)) and not bool(ff.get("shipping_address_in_complete", False)):
        violations.append("ACP_52_MISSING_SHIPPING_ADDRESS_IN_COMPLETE_FOR_TAX")
    if bool(ff.get("requires_consumer_3ds", False)) and not bool(ff.get("consumer_3ds_cryptogram_verified", False)):
        violations.append("ACP_53_UNVERIFIED_CONSUMER_3DS_AUTHENTICATION")

    # 2. ACP #9: 6-to-8 digit ISO/IEC 7812-1 IIN and 4-digit display_last4
    card = payload.get("card_metadata", {})
    iin = str(card.get("iin", ""))
    last4 = str(card.get("display_last4", ""))
    if not iin.isdigit() or not (6 <= len(iin) <= 8):
        violations.append("ACP_9_INVALID_ISO7812_IIN_LENGTH")
    if not last4.isdigit() or len(last4) != 4:
        violations.append("ACP_9_INVALID_DISPLAY_LAST4_LENGTH")

    # 3. ACP #3: B2B decimal quantity support (exclusiveMinimum: 0)
    b2b = payload.get("b2b_line_item", {})
    qty = float(b2b.get("quantity", 0))
    unit_price = int(b2b.get("unit_price_minor", 0))
    declared_subtotal = int(b2b.get("subtotal_minor", 0))
    if qty <= 0.0:
        violations.append("ACP_3_NON_POSITIVE_B2B_DECIMAL_QUANTITY")
    elif round(qty * unit_price) != declared_subtotal:
        violations.append("ACP_3_DECIMAL_QUANTITY_SUBTOTAL_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Google AP2 #243 verifier checkout_hash obligation, #252 cross-merchant budget, and x402 #354 SpendGuard."""
    violations: list[str] = []

    # 1. AP2 #243: Normative verifier obligation for checkout_hash
    vh = payload.get("verifier_checkout_hash", {})
    if not bool(vh.get("verifier_recomputed_checkout_hash", False)):
        violations.append("AP2_243_VERIFIER_SKIPPED_CHECKOUT_HASH_RECOMPUTATION")
    expected_ch = str(vh.get("recomputed_checkout_hash", ""))
    claimed_ch = str(vh.get("payment_mandate_checkout_hash", ""))
    if not expected_ch or expected_ch != claimed_ch:
        violations.append("AP2_243_CHECKOUT_HASH_MISMATCH")

    # 2. AP2 #252: Cross-merchant cumulative budget enforcement
    cmb = payload.get("cross_merchant_budget", {})
    cap = int(cmb.get("session_budget_cap_minor", 0))
    allocations = cmb.get("merchant_allocations", [])
    total_allocated = sum(int(a.get("amount_minor", 0)) for a in allocations)
    if total_allocated > cap:
        violations.append("AP2_252_CROSS_MERCHANT_CUMULATIVE_BUDGET_EXCEEDED")
    seen_nonces: set[str] = set()
    for a in allocations:
        n = str(a.get("nonce", ""))
        if n in seen_nonces:
            violations.append("AP2_252_DUPLICATE_CROSS_MERCHANT_ALLOCATION_NONCE")
        seen_nonces.add(n)

    # 3. Coinbase x402 #354: SpendGuard per-call and rolling-window USDC cap
    sg = payload.get("x402_spendguard", {})
    if int(sg.get("call_amount_usdc_micro", 0)) > int(sg.get("max_per_call_usdc_micro", 0)):
        violations.append("X402_354_SPENDGUARD_PER_CALL_CAP_EXCEEDED")
    if int(sg.get("window_cumulative_usdc_micro", 0)) > int(sg.get("max_window_usdc_micro", 0)):
        violations.append("X402_354_SPENDGUARD_WINDOW_CAP_EXCEEDED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #584, #581, #570, #569, and #566 evaluation guards."""
    violations: list[str] = []

    # 1. Sierra tau2-bench #584 & #581: NL-Assertions Judge contentless turn omission & verdict count check
    nlj = payload.get("nl_judge_check", {})
    if bool(nlj.get("serialized_literal_assistant_none", False)):
        violations.append("TAU2_584_LITERAL_ASSISTANT_NONE_IN_NL_JUDGE_PROMPT")
    expected_assertions = int(nlj.get("expected_assertion_count", 0))
    returned_verdicts = int(nlj.get("returned_verdict_count", 0))
    if expected_assertions != returned_verdicts:
        violations.append("TAU2_581_NL_JUDGE_VERDICT_COUNT_MISMATCH")

    # 2. Sierra tau2-bench #570 & #569: Paired list sorting & union-key gold argument check
    act = payload.get("action_comparison_check", {})
    gold_pairs = list(zip(act.get("gold_item_ids", []), act.get("gold_new_item_ids", [])))
    call_pairs = list(zip(act.get("call_item_ids", []), act.get("call_new_item_ids", [])))
    if sorted(gold_pairs) != sorted(call_pairs):
        violations.append("TAU2_570_SWAPPED_OR_MISMATCHED_PAIRED_ACTION_LISTS")
    gold_keys = set(act.get("gold_arg_keys", []))
    call_keys = set(act.get("call_arg_keys", []))
    if gold_keys != call_keys:
        violations.append("TAU2_569_OMITTED_OR_EXTRA_GOLD_ARG_KEYS")

    # 3. Sierra tau2-bench #566: Sorted KnowledgeBase.load document order
    kb = payload.get("knowledge_base_load", {})
    loaded_filenames = list(kb.get("loaded_filenames", []))
    if loaded_filenames != sorted(loaded_filenames):
        violations.append("TAU2_566_UNSORTED_FILESYSTEM_KB_LOAD_ORDER")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
