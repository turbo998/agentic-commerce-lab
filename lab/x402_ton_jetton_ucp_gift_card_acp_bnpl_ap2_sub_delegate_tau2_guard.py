"""Stage 160 deterministic guardrails (`TN-01..TN-16`).

Covers first-hand upstream PRs and issues across x402 Foundation, Google UCP,
OpenAI/Stripe ACP, Google AP2, Model Context Protocol (MCP), Stripe AI,
Visa Trusted Agent Protocol (TAP), and Sierra tau-bench 2.0:

- TN-01: x402 #3740/#3736/#3729 — TON (`ton:-239`) TIP-3 Jetton (`transfer#0f8a7ea5`) master-derived wallet verification, `forward_ton_amount` notification gas floor & 64-bit `query_id` replay deduplication.
- TN-02: x402 #3722/#3719/#3714 — Cosmos Noble (`cosmos:noble-1`) IBC `MsgTransfer` (`uusdc`) channel/port allowlist, bounded `timeout_timestamp` window & memo `x402_payment_id` binding.
- TN-03: x402 #3695/#3692/#3689 — Facilitator `/settle` idempotent `(network, payment_payload_sha256)` receipt cache & conflicting `paymentRequirements` hijack block.
- TN-04: x402 #3469/#3464/#3460 — `@x402/axios` & `@x402/fetch` cross-origin HTTP 3xx redirect `Payment` / `X-PAYMENT` credential strip & retry halt.
- TN-05: UCP #941/#936/#927/#923 — Gift card & store credit redemption guard (blocking gift-card-to-gift-card purchase loops, cash-out withdrawal & balance over-deduction).
- TN-06: UCP #921/#913/#909/#895 — Pre-order authorization hold window vs delayed-capture mandate requirement & pre-order price-guarantee ceiling.
- TN-07: UCP #828/#825/#821/#817 — Warranty/protection-plan parent hardware SKU attachment, quantity parity & category eligibility guard.
- TN-08: ACP #299/#298/#283/#277 — BNPL installment disclosure (`apr_bps`, `installment_count`, `total_repayment_minor` conservation), amount range & prohibited category block.
- TN-09: ACP #265/#263/#258/#254 — Digital fulfillment license/download URL release gated on `captured` payment status, attempt ceiling & buyer-bound URL expiry.
- TN-10: AP2 #354/#350/#344/#337 — Sub-agent delegation hop-depth ceiling (`max_delegation_hops`) & strict monotonic MCC + per-tx amount attenuation.
- TN-11: AP2 #334/#329/#325/#322 — Mandate revocation status list (`CRL`/bitstring) freshness window (`<= 300s`), signature verification & revoked index block.
- TN-12: MCP #3361/#3355/#3348/#3341 — `resources/read` & `prompts/get` active MIME-type block (`text/html`, `image/svg+xml` script), prompt-injection delimiter strip & size cap.
- TN-13: Stripe AI #491/#488/#478/#472 — Stripe Issuing virtual card per-auth spend limit ceiling, explicit MCC allowlist (no wildcard) & post-session auto-freeze.
- TN-14: Visa TAP #15/#11/#8/#2 — Visa Intelligent Commerce (VIC) UI-displayed card `last4` & `issuer_brand` parity with attested `vic_token_metadata` (blocking card substitution).
- TN-15: Sierra tau-bench 2.0 #589/#586/#582/#578 — Insurance claim active policy on loss date, covered peril check, deductible/limit payout conservation & duplicate incident block.
- TN-16: Sierra tau-bench 2.0 #576/#572/#568/#565 — E-commerce flash-sale per-household quantity limit across normalized address hash & payment fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    evidence: dict[str, object]


BNPL_PROHIBITED_CATEGORIES = {"gift_cards", "gambling", "crypto", "wire_transfer", "bail_bonds"}
FORBIDDEN_MCP_RESOURCE_MIMES = {"text/html", "application/javascript", "text/javascript", "application/xhtml+xml"}
INJECTION_MARKERS = ("<|im_start|>", "<|im_end|>", "ignore previous instructions", "system override:")


# ---------------------------------------------------------------------------
# TN-01: x402 #3740/#3736/#3729 — TON TIP-3 Jetton transfer & gas floor guard
# ---------------------------------------------------------------------------
def evaluate_x402_ton_jetton_transfer_guard(
    *,
    network: str,
    op_code_hex: str,
    jetton_master_address: str,
    expected_jetton_master_address: str,
    jetton_wallet_verified_by_master: bool,
    jetton_amount: int,
    required_jetton_amount: int,
    forward_ton_amount_nanotons: int,
    min_forward_ton_nanotons: int,
    query_id: int,
    seen_query_ids: Sequence[int],
) -> GuardDecision:
    if network.strip() not in {"ton:-239", "ton:mainnet"}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_NETWORK_MISMATCH_BLOCKED",
            reason="TON mainnet x402 settlement requires network 'ton:-239' or 'ton:mainnet'.",
            evidence={"network": network},
        )
    if op_code_hex.strip().lower() != "0x0f8a7ea5":
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_INVALID_JETTON_OP_CODE_BLOCKED",
            reason="TON TIP-3 Jetton transfer message must use op::transfer (0x0f8a7ea5).",
            evidence={"op_code_hex": op_code_hex},
        )
    if (
        not jetton_wallet_verified_by_master
        or jetton_master_address.strip().lower() != expected_jetton_master_address.strip().lower()
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_UNVERIFIED_JETTON_WALLET_OR_MASTER_BLOCKED",
            reason="Sender Jetton wallet was not derived from the official expected Jetton master contract.",
            evidence={
                "jetton_master_address": jetton_master_address,
                "expected_jetton_master_address": expected_jetton_master_address,
                "jetton_wallet_verified_by_master": jetton_wallet_verified_by_master,
            },
        )
    if forward_ton_amount_nanotons < min_forward_ton_nanotons or min_forward_ton_nanotons <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_FORWARD_GAS_BELOW_FLOOR_BLOCKED",
            reason="TON Jetton transfer forward_ton_amount is below minimum notification gas floor.",
            evidence={
                "forward_ton_amount_nanotons": forward_ton_amount_nanotons,
                "min_forward_ton_nanotons": min_forward_ton_nanotons,
            },
        )
    if query_id <= 0 or query_id >= (1 << 64) or query_id in set(seen_query_ids):
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_QUERY_ID_REPLAY_OR_RANGE_BLOCKED",
            reason="TON Jetton transfer query_id is out of uint64 range or replayed.",
            evidence={"query_id": query_id},
        )
    if jetton_amount < required_jetton_amount or required_jetton_amount <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_TON_JETTON_UNDERPAYMENT_BLOCKED",
            reason="TON Jetton transfer amount is below required_jetton_amount.",
            evidence={"jetton_amount": jetton_amount, "required_jetton_amount": required_jetton_amount},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_TON_JETTON_TRANSFER_VERIFIED",
        reason="TON TIP-3 Jetton master derivation, forward gas floor, and uint64 query_id verified.",
        evidence={"jetton_amount": jetton_amount, "query_id": query_id},
    )


# ---------------------------------------------------------------------------
# TN-02: x402 #3722/#3719/#3714 — Cosmos Noble IBC MsgTransfer guard
# ---------------------------------------------------------------------------
def evaluate_x402_cosmos_noble_ibc_transfer_guard(
    *,
    network: str,
    denom: str,
    source_port: str,
    source_channel: str,
    allowed_channels: Sequence[str],
    timeout_timestamp_ns: int,
    now_ns: int,
    max_ibc_timeout_ns: int,
    memo_payment_id: str,
    expected_payment_id: str,
    amount_minor: int,
    required_amount_minor: int,
) -> GuardDecision:
    if network.strip() != "cosmos:noble-1" or denom.strip() != "uusdc":
        return GuardDecision(
            allowed=False,
            decision_code="X402_COSMOS_NOBLE_DENOM_OR_CHAIN_MISMATCH_BLOCKED",
            reason="Cosmos IBC settlement requires 'cosmos:noble-1' and native 'uusdc' denom.",
            evidence={"network": network, "denom": denom},
        )
    if source_port.strip() != "transfer" or source_channel.strip() not in {c.strip() for c in allowed_channels}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_COSMOS_IBC_UNTRUSTED_CHANNEL_BLOCKED",
            reason="IBC MsgTransfer source_port/source_channel is not in the trusted channel allowlist.",
            evidence={
                "source_port": source_port,
                "source_channel": source_channel,
                "allowed_channels": list(allowed_channels),
            },
        )
    if timeout_timestamp_ns <= now_ns or (timeout_timestamp_ns - now_ns) > max_ibc_timeout_ns:
        return GuardDecision(
            allowed=False,
            decision_code="X402_COSMOS_IBC_TIMEOUT_WINDOW_INVALID_BLOCKED",
            reason="IBC timeout_timestamp_ns is expired or exceeds max_ibc_timeout_ns lockup ceiling.",
            evidence={
                "timeout_timestamp_ns": timeout_timestamp_ns,
                "now_ns": now_ns,
                "max_ibc_timeout_ns": max_ibc_timeout_ns,
            },
        )
    if not expected_payment_id.strip() or memo_payment_id.strip() != expected_payment_id.strip():
        return GuardDecision(
            allowed=False,
            decision_code="X402_COSMOS_IBC_MEMO_PAYMENT_ID_MISMATCH_BLOCKED",
            reason="IBC MsgTransfer memo x402_payment_id does not match expected checkout payment ID.",
            evidence={"memo_payment_id": memo_payment_id, "expected_payment_id": expected_payment_id},
        )
    if amount_minor < required_amount_minor or required_amount_minor <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_COSMOS_IBC_UNDERPAYMENT_BLOCKED",
            reason="IBC MsgTransfer amount is below required_amount_minor.",
            evidence={"amount_minor": amount_minor, "required_amount_minor": required_amount_minor},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_COSMOS_NOBLE_IBC_TRANSFER_VERIFIED",
        reason="Cosmos Noble uusdc IBC channel allowlist, timeout window, and memo payment binding verified.",
        evidence={"source_channel": source_channel, "amount_minor": amount_minor},
    )


# ---------------------------------------------------------------------------
# TN-03: x402 #3695/#3692/#3689 — Facilitator /settle idempotent receipt cache
# ---------------------------------------------------------------------------
def evaluate_x402_facilitator_settle_idempotency_guard(
    *,
    network: str,
    payment_payload_sha256: str,
    requirements_sha256: str,
    cached_receipts: dict[str, dict[str, str]],
) -> GuardDecision:
    cache_key = f"{network.strip()}:{payment_payload_sha256.strip().lower()}"
    existing = cached_receipts.get(cache_key)
    if existing is not None:
        if existing.get("requirements_sha256") != requirements_sha256.strip().lower():
            return GuardDecision(
                allowed=False,
                decision_code="X402_SETTLE_PAYLOAD_REQUIREMENTS_CONFLICT_BLOCKED",
                reason="Same signed payment_payload_sha256 was re-submitted against conflicting paymentRequirements.",
                evidence={
                    "cache_key": cache_key,
                    "cached_requirements_sha256": existing.get("requirements_sha256"),
                    "incoming_requirements_sha256": requirements_sha256.lower(),
                },
            )
        return GuardDecision(
            allowed=True,
            decision_code="X402_SETTLE_IDEMPOTENT_CACHED_RECEIPT_RETURNED",
            reason="Duplicate /settle call matched cached receipt without re-broadcasting transaction.",
            evidence={"cache_key": cache_key, "tx_hash": existing.get("tx_hash")},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_SETTLE_FRESH_SUBMISSION_ADMITTED",
        reason="Fresh (network, payment_payload_sha256) admitted for on-chain broadcast.",
        evidence={"cache_key": cache_key},
    )


# ---------------------------------------------------------------------------
# TN-04: x402 #3469/#3464/#3460 — Cross-origin 3xx redirect header strip guard
# ---------------------------------------------------------------------------
def evaluate_x402_redirect_credential_strip_guard(
    *,
    initial_request_url: str,
    redirect_status_code: int,
    redirect_location_url: str,
    payment_header_forwarded_on_redirect: bool,
) -> GuardDecision:
    u1 = urlparse(initial_request_url.strip())
    u2 = urlparse(redirect_location_url.strip())
    origin_1 = (u1.scheme.lower(), u1.hostname or "", u1.port or (443 if u1.scheme == "https" else 80))
    origin_2 = (u2.scheme.lower(), u2.hostname or "", u2.port or (443 if u2.scheme == "https" else 80))
    is_cross_origin = origin_1 != origin_2
    if redirect_status_code in {301, 302, 303, 307, 308} and is_cross_origin and payment_header_forwarded_on_redirect:
        return GuardDecision(
            allowed=False,
            decision_code="X402_CROSS_ORIGIN_REDIRECT_PAYMENT_LEAK_BLOCKED",
            reason="HTTP 3xx cross-origin redirect must strip Payment / X-PAYMENT headers to prevent credential exfiltration.",
            evidence={
                "initial_origin": f"{origin_1[0]}://{origin_1[1]}:{origin_1[2]}",
                "redirect_origin": f"{origin_2[0]}://{origin_2[1]}:{origin_2[2]}",
                "redirect_status_code": redirect_status_code,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_REDIRECT_CREDENTIAL_POLICY_VERIFIED",
        reason="Cross-origin redirect stripped payment headers or stayed on same origin.",
        evidence={"is_cross_origin": is_cross_origin, "redirect_status_code": redirect_status_code},
    )


# ---------------------------------------------------------------------------
# TN-05: UCP #941/#936/#927/#923 — Gift card & store credit loop/cashout guard
# ---------------------------------------------------------------------------
def evaluate_ucp_gift_card_redemption_guard(
    *,
    gift_card_balance_minor: int,
    gift_card_applied_minor: int,
    cart_contains_gift_card_sku: bool,
    cash_out_requested: bool,
    order_total_minor: int,
) -> GuardDecision:
    if cart_contains_gift_card_sku and gift_card_applied_minor > 0:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_GIFT_CARD_PURCHASE_WITH_GIFT_CARD_LOOP_BLOCKED",
            reason="Closed-loop gift cards or store credit cannot be used to purchase other gift cards.",
            evidence={
                "cart_contains_gift_card_sku": cart_contains_gift_card_sku,
                "gift_card_applied_minor": gift_card_applied_minor,
            },
        )
    if cash_out_requested:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_GIFT_CARD_CASH_OUT_WITHDRAWAL_BLOCKED",
            reason="Closed-loop gift card balance cannot be withdrawn as cash or open-loop transfer.",
            evidence={"cash_out_requested": cash_out_requested},
        )
    if (
        gift_card_applied_minor < 0
        or gift_card_applied_minor > gift_card_balance_minor
        or gift_card_applied_minor > order_total_minor
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_GIFT_CARD_OVER_DEDUCTION_BLOCKED",
            reason="Applied gift card amount exceeds available gift_card_balance_minor or order_total_minor.",
            evidence={
                "gift_card_balance_minor": gift_card_balance_minor,
                "gift_card_applied_minor": gift_card_applied_minor,
                "order_total_minor": order_total_minor,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_GIFT_CARD_REDEMPTION_VERIFIED",
        reason="Gift card anti-loop, non-cashout, and split-tender balance deduction verified.",
        evidence={
            "gift_card_applied_minor": gift_card_applied_minor,
            "remaining_card_charge_minor": order_total_minor - gift_card_applied_minor,
        },
    )


# ---------------------------------------------------------------------------
# TN-06: UCP #921/#913/#909/#895 — Pre-order hold expiry & price guarantee
# ---------------------------------------------------------------------------
def evaluate_ucp_preorder_hold_and_price_guarantee_guard(
    *,
    days_until_ship: int,
    card_auth_hold_max_days: int,
    delayed_capture_mandate_present: bool,
    preorder_price_guarantee_minor: int,
    final_ship_charge_minor: int,
) -> GuardDecision:
    if days_until_ship > card_auth_hold_max_days and not delayed_capture_mandate_present:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PREORDER_HOLD_EXPIRY_WITHOUT_DELAYED_MANDATE_BLOCKED",
            reason="Pre-order shipping beyond card_auth_hold_max_days requires a delayed_capture_mandate.",
            evidence={
                "days_until_ship": days_until_ship,
                "card_auth_hold_max_days": card_auth_hold_max_days,
                "delayed_capture_mandate_present": delayed_capture_mandate_present,
            },
        )
    if final_ship_charge_minor > preorder_price_guarantee_minor or final_ship_charge_minor <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PREORDER_PRICE_GUARANTEE_BREACH_BLOCKED",
            reason="Final capture at shipment cannot exceed the buyer's locked preorder_price_guarantee_minor.",
            evidence={
                "preorder_price_guarantee_minor": preorder_price_guarantee_minor,
                "final_ship_charge_minor": final_ship_charge_minor,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_PREORDER_HOLD_AND_PRICE_VERIFIED",
        reason="Pre-order authorization hold horizon and price guarantee ceiling verified.",
        evidence={"days_until_ship": days_until_ship, "final_ship_charge_minor": final_ship_charge_minor},
    )


# ---------------------------------------------------------------------------
# TN-07: UCP #828/#825/#821/#817 — Warranty attachment & orphan guard
# ---------------------------------------------------------------------------
def evaluate_ucp_warranty_attachment_guard(
    *,
    covered_parent_line_id: str,
    active_hardware_lines: dict[str, dict[str, object]],
    warranty_quantity: int,
    warranty_eligible_category: str,
) -> GuardDecision:
    parent = active_hardware_lines.get(covered_parent_line_id.strip())
    if parent is None:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_WARRANTY_ORPHAN_PARENT_LINE_BLOCKED",
            reason="Warranty plan references a missing, removed, or returned parent hardware line item.",
            evidence={"covered_parent_line_id": covered_parent_line_id},
        )
    parent_qty = int(parent.get("quantity", 0))
    parent_category = str(parent.get("category", "")).strip().lower()
    if warranty_quantity <= 0 or warranty_quantity > parent_qty:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_WARRANTY_QUANTITY_EXCEEDS_HARDWARE_BLOCKED",
            reason="Warranty quantity cannot exceed covered parent hardware line quantity.",
            evidence={"warranty_quantity": warranty_quantity, "parent_quantity": parent_qty},
        )
    if parent_category != warranty_eligible_category.strip().lower():
        return GuardDecision(
            allowed=False,
            decision_code="UCP_WARRANTY_CATEGORY_INELIGIBLE_BLOCKED",
            reason="Parent hardware category does not match warranty plan eligible category.",
            evidence={
                "parent_category": parent_category,
                "warranty_eligible_category": warranty_eligible_category,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_WARRANTY_ATTACHMENT_VERIFIED",
        reason="Warranty parent hardware linkage, quantity parity, and category eligibility verified.",
        evidence={"covered_parent_line_id": covered_parent_line_id, "warranty_quantity": warranty_quantity},
    )


# ---------------------------------------------------------------------------
# TN-08: ACP #299/#298/#283/#277 — BNPL installment disclosure & category guard
# ---------------------------------------------------------------------------
def evaluate_acp_bnpl_installment_disclosure_guard(
    *,
    order_total_minor: int,
    bnpl_min_minor: int,
    bnpl_max_minor: int,
    cart_categories: Sequence[str],
    apr_bps: int,
    installment_amounts_minor: Sequence[int],
    disclosed_total_repayment_minor: int,
    user_approval_binds_bnpl_terms: bool,
) -> GuardDecision:
    prohibited_hits = sorted({c.strip().lower() for c in cart_categories if c.strip()} & BNPL_PROHIBITED_CATEGORIES)
    if prohibited_hits:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_BNPL_PROHIBITED_MERCHANT_CATEGORY_BLOCKED",
            reason="BNPL installment tender is prohibited for high-risk or cash-equivalent categories.",
            evidence={"prohibited_categories": prohibited_hits},
        )
    if order_total_minor < bnpl_min_minor or order_total_minor > bnpl_max_minor:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_BNPL_ORDER_AMOUNT_OUT_OF_RANGE_BLOCKED",
            reason="Order total falls outside BNPL provider [bnpl_min_minor, bnpl_max_minor] eligibility range.",
            evidence={
                "order_total_minor": order_total_minor,
                "bnpl_min_minor": bnpl_min_minor,
                "bnpl_max_minor": bnpl_max_minor,
            },
        )
    if (
        not installment_amounts_minor
        or any(x <= 0 for x in installment_amounts_minor)
        or sum(installment_amounts_minor) != disclosed_total_repayment_minor
        or disclosed_total_repayment_minor < order_total_minor
        or apr_bps < 0
        or not user_approval_binds_bnpl_terms
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_BNPL_INSTALLMENT_DISCLOSURE_MISMATCH_BLOCKED",
            reason="BNPL installment schedule sum must equal disclosed_total_repayment_minor and be bound in UserApproval.",
            evidence={
                "sum_installments": sum(installment_amounts_minor),
                "disclosed_total_repayment_minor": disclosed_total_repayment_minor,
                "user_approval_binds_bnpl_terms": user_approval_binds_bnpl_terms,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_BNPL_INSTALLMENT_DISCLOSURE_VERIFIED",
        reason="BNPL eligibility range, category restrictions, and installment repayment schedule verified.",
        evidence={
            "installment_count": len(installment_amounts_minor),
            "disclosed_total_repayment_minor": disclosed_total_repayment_minor,
        },
    )


# ---------------------------------------------------------------------------
# TN-09: ACP #265/#263/#258/#254 — Digital fulfillment license/download guard
# ---------------------------------------------------------------------------
def evaluate_acp_digital_fulfillment_entitlement_guard(
    *,
    payment_status: str,
    download_attempts: int,
    max_download_attempts: int,
    url_bound_buyer_id: str,
    requesting_buyer_id: str,
    url_expires_at: int,
    now_unix: int,
) -> GuardDecision:
    if payment_status.strip().lower() != "captured":
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DIGITAL_FULFILLMENT_BEFORE_CAPTURE_BLOCKED",
            reason="Digital license key or download URL cannot be released before payment_status == 'captured'.",
            evidence={"payment_status": payment_status},
        )
    if not requesting_buyer_id.strip() or url_bound_buyer_id.strip() != requesting_buyer_id.strip():
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DIGITAL_FULFILLMENT_BUYER_MISMATCH_BLOCKED",
            reason="Signed digital download URL buyer binding does not match requesting_buyer_id.",
            evidence={"url_bound_buyer_id": url_bound_buyer_id, "requesting_buyer_id": requesting_buyer_id},
        )
    if now_unix >= url_expires_at or download_attempts >= max_download_attempts:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DIGITAL_FULFILLMENT_EXPIRED_OR_EXHAUSTED_BLOCKED",
            reason="Digital download URL has expired or exceeded max_download_attempts.",
            evidence={
                "download_attempts": download_attempts,
                "max_download_attempts": max_download_attempts,
                "url_expires_at": url_expires_at,
                "now_unix": now_unix,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_DIGITAL_FULFILLMENT_RELEASE_VERIFIED",
        reason="Payment capture finality, buyer identity binding, and download quota verified.",
        evidence={"remaining_attempts": max_download_attempts - download_attempts - 1},
    )


# ---------------------------------------------------------------------------
# TN-10: AP2 #354/#350/#344/#337 — Sub-agent delegation attenuation guard
# ---------------------------------------------------------------------------
def evaluate_ap2_sub_delegate_attenuation_guard(
    *,
    current_hop_depth: int,
    max_delegation_hops: int,
    parent_max_amount_minor: int,
    child_max_amount_minor: int,
    parent_allowed_mccs: Sequence[str],
    child_allowed_mccs: Sequence[str],
) -> GuardDecision:
    if current_hop_depth <= 0 or current_hop_depth > max_delegation_hops:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_DELEGATION_HOP_DEPTH_EXCEEDED_BLOCKED",
            reason="Sub-agent delegation chain depth exceeds max_delegation_hops.",
            evidence={"current_hop_depth": current_hop_depth, "max_delegation_hops": max_delegation_hops},
        )
    if child_max_amount_minor <= 0 or child_max_amount_minor > parent_max_amount_minor:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_DELEGATION_AMOUNT_PRIVILEGE_ESCALATION_BLOCKED",
            reason="Child sub-mandate max_amount_minor cannot exceed parent mandate ceiling.",
            evidence={
                "parent_max_amount_minor": parent_max_amount_minor,
                "child_max_amount_minor": child_max_amount_minor,
            },
        )
    parent_set = {m.strip() for m in parent_allowed_mccs if m.strip()}
    child_set = {m.strip() for m in child_allowed_mccs if m.strip()}
    if not child_set or not child_set.issubset(parent_set):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_DELEGATION_MCC_SCOPE_ESCALATION_BLOCKED",
            reason="Child sub-mandate allowed_mccs must be a non-empty subset of parent_allowed_mccs.",
            evidence={
                "parent_allowed_mccs": sorted(parent_set),
                "child_allowed_mccs": sorted(child_set),
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_DELEGATION_ATTENUATION_VERIFIED",
        reason="Sub-agent hop depth, amount ceiling attenuation, and MCC subset attenuation verified.",
        evidence={"current_hop_depth": current_hop_depth, "child_max_amount_minor": child_max_amount_minor},
    )


# ---------------------------------------------------------------------------
# TN-11: AP2 #334/#329/#325/#322 — Mandate revocation status list freshness
# ---------------------------------------------------------------------------
def evaluate_ap2_revocation_status_list_freshness_guard(
    *,
    status_list_signature_valid: bool,
    status_list_issued_at: int,
    now_unix: int,
    max_staleness_seconds: int,
    mandate_revocation_bit: int,
) -> GuardDecision:
    if not status_list_signature_valid:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_REVOCATION_LIST_SIGNATURE_INVALID_BLOCKED",
            reason="Mandate revocation status list signature failed cryptographic verification.",
            evidence={"status_list_signature_valid": status_list_signature_valid},
        )
    if status_list_issued_at > now_unix + 30 or (now_unix - status_list_issued_at) > max_staleness_seconds:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_REVOCATION_LIST_STALE_FAIL_CLOSED_BLOCKED",
            reason="Mandate revocation status list age exceeds max_staleness_seconds (fail-closed).",
            evidence={
                "status_list_issued_at": status_list_issued_at,
                "now_unix": now_unix,
                "max_staleness_seconds": max_staleness_seconds,
            },
        )
    if mandate_revocation_bit != 0:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_MANDATE_REVOKED_IN_STATUS_LIST_BLOCKED",
            reason="Mandate index bit is set to 1 (revoked) in the authoritative status list.",
            evidence={"mandate_revocation_bit": mandate_revocation_bit},
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_REVOCATION_STATUS_ACTIVE_VERIFIED",
        reason="Fresh, cryptographically signed revocation status list confirms mandate bit == 0.",
        evidence={"staleness_seconds": now_unix - status_list_issued_at},
    )


# ---------------------------------------------------------------------------
# TN-12: MCP #3361/#3355/#3348/#3341 — Resource MIME & prompt-injection guard
# ---------------------------------------------------------------------------
def evaluate_mcp_resource_mime_and_injection_guard(
    *,
    declared_mime_type: str,
    resource_content: str,
    max_resource_bytes: int,
) -> GuardDecision:
    mime = declared_mime_type.strip().lower()
    content_bytes = len(resource_content.encode("utf-8"))
    if content_bytes > max_resource_bytes or max_resource_bytes <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_RESOURCE_SIZE_CAP_EXCEEDED_BLOCKED",
            reason="MCP resource payload size exceeds max_resource_bytes ceiling.",
            evidence={"content_bytes": content_bytes, "max_resource_bytes": max_resource_bytes},
        )
    lower_content = resource_content.lower()
    if mime in FORBIDDEN_MCP_RESOURCE_MIMES or ("svg" in mime and "<script" in lower_content):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_RESOURCE_ACTIVE_EXECUTABLE_MIME_BLOCKED",
            reason="MCP resources/read blocks executable HTML/JS or script-bearing SVG payloads.",
            evidence={"declared_mime_type": declared_mime_type},
        )
    for marker in INJECTION_MARKERS:
        if marker in lower_content:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_RESOURCE_PROMPT_INJECTION_MARKER_BLOCKED",
                reason="Untrusted MCP resource contains control-token or prompt-injection override markers.",
                evidence={"detected_marker": marker},
            )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_RESOURCE_SAFE_MIME_AND_CONTENT_VERIFIED",
        reason="MCP resource MIME type, byte length, and injection-marker scan passed.",
        evidence={"declared_mime_type": mime, "content_bytes": content_bytes},
    )


# ---------------------------------------------------------------------------
# TN-13: Stripe AI #491/#488/#478/#472 — Issuing virtual card spend controls
# ---------------------------------------------------------------------------
def evaluate_stripe_issuing_virtual_card_spend_guard(
    *,
    spending_limit_amount_minor: int | None,
    spending_limit_interval: str,
    mandate_ceiling_minor: int,
    allowed_mcc_categories: Sequence[str],
    auto_freeze_on_session_end: bool,
) -> GuardDecision:
    if (
        spending_limit_amount_minor is None
        or spending_limit_amount_minor <= 0
        or spending_limit_amount_minor > mandate_ceiling_minor
        or spending_limit_interval.strip() not in {"per_authorization", "daily"}
    ):
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_ISSUING_MISSING_OR_EXCESSIVE_SPEND_LIMIT_BLOCKED",
            reason="Stripe Issuing agent virtual card requires per_authorization/daily spending_limit <= mandate_ceiling_minor.",
            evidence={
                "spending_limit_amount_minor": spending_limit_amount_minor,
                "spending_limit_interval": spending_limit_interval,
                "mandate_ceiling_minor": mandate_ceiling_minor,
            },
        )
    normalized_mccs = [m.strip() for m in allowed_mcc_categories if m.strip()]
    if not normalized_mccs or "*" in normalized_mccs:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_ISSUING_WILDCARD_MCC_CATEGORIES_BLOCKED",
            reason="Stripe Issuing virtual card must specify an explicit MCC allowlist without wildcard '*'.",
            evidence={"allowed_mcc_categories": list(allowed_mcc_categories)},
        )
    if not auto_freeze_on_session_end:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_ISSUING_UNFROZEN_POST_SESSION_CARD_BLOCKED",
            reason="Agent-provisioned virtual card must enable auto_freeze_on_session_end.",
            evidence={"auto_freeze_on_session_end": auto_freeze_on_session_end},
        )
    return GuardDecision(
        allowed=True,
        decision_code="STRIPE_ISSUING_VIRTUAL_CARD_CONTROLS_VERIFIED",
        reason="Stripe Issuing virtual card spend ceiling, explicit MCC allowlist, and auto-freeze verified.",
        evidence={
            "spending_limit_amount_minor": spending_limit_amount_minor,
            "allowed_mcc_categories": normalized_mccs,
        },
    )


# ---------------------------------------------------------------------------
# TN-14: Visa TAP #15/#11/#8/#2 — VIC tokenized card last4 & brand parity
# ---------------------------------------------------------------------------
def evaluate_visa_vic_card_display_parity_guard(
    *,
    ui_displayed_last4: str,
    ui_displayed_brand: str,
    ui_displayed_funding_source: str,
    token_attested_last4: str,
    token_attested_brand: str,
    token_attested_funding_source: str,
) -> GuardDecision:
    if (
        ui_displayed_last4.strip() != token_attested_last4.strip()
        or ui_displayed_brand.strip().lower() != token_attested_brand.strip().lower()
        or ui_displayed_funding_source.strip().lower() != token_attested_funding_source.strip().lower()
    ):
        return GuardDecision(
            allowed=False,
            decision_code="VISA_VIC_DISPLAY_TOKEN_CARD_SUBSTITUTION_BLOCKED",
            reason="UI-displayed card last4/brand/funding does not match cryptographically attested VIC token metadata.",
            evidence={
                "ui_displayed": {
                    "last4": ui_displayed_last4,
                    "brand": ui_displayed_brand,
                    "funding": ui_displayed_funding_source,
                },
                "token_attested": {
                    "last4": token_attested_last4,
                    "brand": token_attested_brand,
                    "funding": token_attested_funding_source,
                },
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="VISA_VIC_DISPLAY_TOKEN_PARITY_VERIFIED",
        reason="Visa Intelligent Commerce UI card display matches attested network token metadata.",
        evidence={"last4": token_attested_last4, "brand": token_attested_brand},
    )


# ---------------------------------------------------------------------------
# TN-15: Sierra tau-bench 2.0 #589/#586/#582/#578 — Insurance claim deductible
# ---------------------------------------------------------------------------
def evaluate_tau2_insurance_claim_deductible_guard(
    *,
    coverage_active_on_loss_date: bool,
    peril_type: str,
    covered_perils: Sequence[str],
    verified_loss_minor: int,
    deductible_minor: int,
    policy_limit_minor: int,
    proposed_payout_minor: int,
    incident_hash: str,
    prior_paid_incident_hashes: Sequence[str],
) -> GuardDecision:
    if not coverage_active_on_loss_date or peril_type.strip().lower() not in {p.strip().lower() for p in covered_perils}:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_INSURANCE_INACTIVE_POLICY_OR_EXCLUDED_PERIL_BLOCKED",
            reason="Insurance policy was inactive on loss date or peril_type is excluded from coverage.",
            evidence={
                "coverage_active_on_loss_date": coverage_active_on_loss_date,
                "peril_type": peril_type,
                "covered_perils": list(covered_perils),
            },
        )
    if incident_hash.strip() in {h.strip() for h in prior_paid_incident_hashes}:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_INSURANCE_DUPLICATE_INCIDENT_CLAIM_BLOCKED",
            reason="Duplicate insurance claim submitted for an already-adjudicated incident_hash.",
            evidence={"incident_hash": incident_hash},
        )
    expected_payout = max(0, min(verified_loss_minor - deductible_minor, policy_limit_minor))
    if proposed_payout_minor != expected_payout or proposed_payout_minor <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_INSURANCE_DEDUCTIBLE_OR_LIMIT_CALCULATION_BLOCKED",
            reason="Proposed insurance payout violates min(verified_loss - deductible, policy_limit) conservation.",
            evidence={
                "verified_loss_minor": verified_loss_minor,
                "deductible_minor": deductible_minor,
                "policy_limit_minor": policy_limit_minor,
                "expected_payout": expected_payout,
                "proposed_payout_minor": proposed_payout_minor,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_INSURANCE_CLAIM_PAYOUT_VERIFIED",
        reason="Insurance policy coverage, incident uniqueness, and net-of-deductible payout verified.",
        evidence={"approved_payout_minor": expected_payout},
    )


# ---------------------------------------------------------------------------
# TN-16: Sierra tau-bench 2.0 #576/#572/#568/#565 — Flash-sale household quota
# ---------------------------------------------------------------------------
def evaluate_tau2_flash_sale_household_quota_guard(
    *,
    requested_qty: int,
    max_per_household_qty: int,
    prior_qty_by_address_hash: int,
    prior_qty_by_payment_fingerprint: int,
    prior_qty_by_account_id: int,
) -> GuardDecision:
    effective_prior_qty = max(prior_qty_by_address_hash, prior_qty_by_payment_fingerprint, prior_qty_by_account_id)
    if requested_qty <= 0 or (effective_prior_qty + requested_qty) > max_per_household_qty:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_FLASH_SALE_HOUSEHOLD_QUOTA_EXCEEDED_BLOCKED",
            reason="Cumulative flash-sale quantity across household address, payment method, or account exceeds max_per_household_qty.",
            evidence={
                "requested_qty": requested_qty,
                "effective_prior_qty": effective_prior_qty,
                "max_per_household_qty": max_per_household_qty,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_FLASH_SALE_HOUSEHOLD_QUOTA_VERIFIED",
        reason="Flash-sale purchase is within per-household quantity limit across address and payment graph.",
        evidence={"cumulative_household_qty": effective_prior_qty + requested_qty},
    )
