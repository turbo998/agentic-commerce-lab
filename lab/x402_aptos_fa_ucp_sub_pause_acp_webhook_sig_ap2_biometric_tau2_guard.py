"""Stage 158 deterministic guardrails (`AD-01..AD-16`).

Covers first-hand upstream PRs and issues across x402 Foundation, Google UCP,
OpenAI/Stripe ACP, Google AP2, Model Context Protocol (MCP), Stripe AI,
Visa Trusted Agent Protocol (TAP), and Sierra tau-bench 2.0:

- AD-01: x402 #3780/#3778/#3772 — Aptos (`aptos:1`) Fungible Asset (`0x1::primary_fungible_store::transfer`) metadata object address allowlist, expiration_timestamp_secs window & gas_unit_price cap.
- AD-02: x402 #3765/#3761/#3758 — EVM ERC-4337 PackedUserOperation canonical EntryPoint v0.7 binding, paymasterAndData validity window & total UserOp gas ceiling.
- AD-03: x402 #3749/#3746/#3742 — HTTP 402 `accepts[]` multi-option deterministic scheme-network-asset selection priority & positive integer amount validation.
- AD-04: x402 #3492/#3489/#3484 — `@x402/hono` & `@x402/next` edge streaming response completion gate before committing `Payment-Response` settlement receipt.
- AD-05: UCP #971/#968/#965/#944 — Subscription lifecycle pause/resume & skip-cycle state machine (`max_pause_days`, deterministic `next_billing_at` & paused/skipped capture block).
- AD-06: UCP #942/#937/#928/#925 — Split-shipment partial capture conservation, carrier tracking proof requirement & single shipping-fee capture guard.
- AD-07: UCP #841/#838/#833/#829 — Age-restricted cryptographic verification & adult signature requirement + hazmat air-transport prohibition (`lithium_ion_un3480`, `flammable_liquid_class3`).
- AD-08: ACP #306/#305/#303/#301 — Webhook raw-body HMAC-SHA256 verification, 300s timestamp replay window & monotonic per-session `event_sequence` terminal-state guard.
- AD-09: ACP #272/#269/#267/#264 — B2B tax-exemption certificate jurisdiction nexus match, expiration check & `buyer_tax_id` binding before zeroing tax.
- AD-10: AP2 #366/#362/#360/#356 — Step-up WebAuthn / Passkey biometric `uv=true` & `up=true` hardware presence gate on high-value/high-risk mandates + `rpIdHash` binding.
- AD-11: AP2 #345/#342/#340/#336 — Corporate procurement M-of-N distinct approver quorum, requester separation-of-duties (no self-approval) & cost-center budget gate.
- AD-12: MCP #3382/#3378/#3375/#3368 — OAuth 2.1 Resource Server RFC 8707 `aud` exact URI match, DPoP `cnf.jkt` binding & downstream third-party token passthrough block.
- AD-13: Stripe AI #505/#502/#498/#494 — Connect `application_fee_amount` floor, `transfer_amount + application_fee <= charge_amount` conservation & `on_behalf_of` regional currency lock.
- AD-14: Visa TAP #10/#6/#5/#4 — Visa Payment Passkey & Click-to-Pay FIDO2 dynamic JCS challenge binding, checkout origin match & monotonic `signCount` clone detection.
- AD-15: Sierra tau-bench 2.0 #618/#615/#612/#605 — Pharmacy prescription refill interval gate (controlled-substance early refill block), active DEA/NPI & insurance prior-authorization gate.
- AD-16: Sierra tau-bench 2.0 #598/#595/#592/#590 — B2B SaaS annual contract minimum seat lock, renewal notice-window enforcement & audit-log retention preservation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Sequence


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    evidence: dict[str, object]


def _canonical_jcs_sha256(payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


CANONICAL_ENTRYPOINT_V07 = "0x0000000071727de22e5e9d8baf0edac6f37da032"
AIR_SHIPPING_METHODS = {"air_express", "next_day_air", "second_day_air", "intl_air_priority"}
AIR_FORBIDDEN_HAZMAT_CLASSES = {"lithium_ion_un3480", "flammable_liquid_class3", "explosives_class1", "toxic_gas_class2"}


# ---------------------------------------------------------------------------
# AD-01: x402 #3780/#3778/#3772 — Aptos Fungible Asset transfer & sponsor cap
# ---------------------------------------------------------------------------
def evaluate_x402_aptos_fungible_asset_sponsor_guard(
    *,
    network: str,
    entry_function_id: str,
    asset_metadata_address: str,
    expected_asset_metadata_address: str,
    transfer_amount: int,
    required_amount: int,
    expiration_timestamp_secs: int,
    now_unix: int,
    max_ttl_seconds: int = 300,
    gas_unit_price: int = 100,
    max_gas_unit_price: int = 1000,
    max_gas_amount: int = 2000,
    max_sponsored_gas_units: int = 5000,
) -> GuardDecision:
    if network.strip() != "aptos:1":
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_CAIP2_NETWORK_MISMATCH_BLOCKED",
            reason="Aptos mainnet settlement requires exact CAIP-2 network 'aptos:1'.",
            evidence={"network": network},
        )
    if entry_function_id.strip() != "0x1::primary_fungible_store::transfer":
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_ENTRY_FUNCTION_NOT_ALLOWLISTED_BLOCKED",
            reason="Aptos x402 FA transfer must invoke canonical '0x1::primary_fungible_store::transfer'.",
            evidence={"entry_function_id": entry_function_id},
        )
    if asset_metadata_address.strip().lower() != expected_asset_metadata_address.strip().lower():
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_FA_METADATA_OBJECT_MISMATCH_BLOCKED",
            reason="Aptos Fungible Asset metadata object address does not match merchant accepted asset.",
            evidence={
                "asset_metadata_address": asset_metadata_address,
                "expected_asset_metadata_address": expected_asset_metadata_address,
            },
        )
    if expiration_timestamp_secs <= now_unix or (expiration_timestamp_secs - now_unix) > max_ttl_seconds:
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_EXPIRATION_WINDOW_INVALID_BLOCKED",
            reason="Aptos transaction expiration_timestamp_secs is expired or exceeds max_ttl_seconds.",
            evidence={
                "expiration_timestamp_secs": expiration_timestamp_secs,
                "now_unix": now_unix,
                "max_ttl_seconds": max_ttl_seconds,
            },
        )
    if gas_unit_price <= 0 or gas_unit_price > max_gas_unit_price or max_gas_amount <= 0 or max_gas_amount > max_sponsored_gas_units:
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_SPONSOR_GAS_CEILING_EXCEEDED_BLOCKED",
            reason="Aptos sponsored transaction gas_unit_price or max_gas_amount exceeds fee-payer ceiling.",
            evidence={
                "gas_unit_price": gas_unit_price,
                "max_gas_unit_price": max_gas_unit_price,
                "max_gas_amount": max_gas_amount,
                "max_sponsored_gas_units": max_sponsored_gas_units,
            },
        )
    if transfer_amount < required_amount or required_amount <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_APTOS_FA_TRANSFER_UNDERPAYMENT_BLOCKED",
            reason="Aptos Fungible Asset transfer amount is below required_amount.",
            evidence={"transfer_amount": transfer_amount, "required_amount": required_amount},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_APTOS_FA_SPONSOR_VERIFIED",
        reason="Aptos Fungible Asset metadata object, expiration window, and sponsored gas limits verified.",
        evidence={
            "asset_metadata_address": asset_metadata_address.lower(),
            "transfer_amount": transfer_amount,
            "total_max_octas_gas": gas_unit_price * max_gas_amount,
        },
    )


# ---------------------------------------------------------------------------
# AD-02: x402 #3765/#3761/#3758 — ERC-4337 PackedUserOperation paymaster guard
# ---------------------------------------------------------------------------
def evaluate_x402_erc4337_userop_paymaster_guard(
    *,
    entry_point_address: str,
    paymaster_valid_after: int,
    paymaster_valid_until: int,
    now_unix: int,
    call_gas_limit: int,
    verification_gas_limit: int,
    pre_verification_gas: int,
    max_total_userop_gas: int,
    paymaster_signature_valid: bool,
) -> GuardDecision:
    if entry_point_address.strip().lower() != CANONICAL_ENTRYPOINT_V07:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ERC4337_UNTRUSTED_ENTRYPOINT_BLOCKED",
            reason="ERC-4337 PackedUserOperation must target canonical EntryPoint v0.7.",
            evidence={
                "entry_point_address": entry_point_address,
                "expected_entry_point": CANONICAL_ENTRYPOINT_V07,
            },
        )
    if not paymaster_signature_valid:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ERC4337_PAYMASTER_SIGNATURE_INVALID_BLOCKED",
            reason="ERC-4337 paymasterAndData cryptographic signature failed verification.",
            evidence={"paymaster_signature_valid": paymaster_signature_valid},
        )
    if now_unix < paymaster_valid_after or now_unix >= paymaster_valid_until:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ERC4337_PAYMASTER_WINDOW_EXPIRED_BLOCKED",
            reason="Current timestamp falls outside ERC-4337 paymaster [validAfter, validUntil) window.",
            evidence={
                "now_unix": now_unix,
                "paymaster_valid_after": paymaster_valid_after,
                "paymaster_valid_until": paymaster_valid_until,
            },
        )
    if min(call_gas_limit, verification_gas_limit, pre_verification_gas) <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ERC4337_NON_POSITIVE_GAS_LIMIT_BLOCKED",
            reason="ERC-4337 UserOperation gas limits must all be positive integers.",
            evidence={
                "call_gas_limit": call_gas_limit,
                "verification_gas_limit": verification_gas_limit,
                "pre_verification_gas": pre_verification_gas,
            },
        )
    total_gas = call_gas_limit + verification_gas_limit + pre_verification_gas
    if total_gas > max_total_userop_gas:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ERC4337_TOTAL_GAS_CEILING_EXCEEDED_BLOCKED",
            reason="ERC-4337 combined UserOperation gas exceeds max_total_userop_gas ceiling.",
            evidence={"total_gas": total_gas, "max_total_userop_gas": max_total_userop_gas},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_ERC4337_USEROP_PAYMASTER_VERIFIED",
        reason="ERC-4337 EntryPoint v0.7, paymaster validity window, and total gas budget verified.",
        evidence={"entry_point": CANONICAL_ENTRYPOINT_V07, "total_gas": total_gas},
    )


# ---------------------------------------------------------------------------
# AD-03: x402 #3749/#3746/#3742 — HTTP 402 accepts[] deterministic selector
# ---------------------------------------------------------------------------
def evaluate_x402_accepts_option_selection_guard(
    *,
    accepts: Sequence[dict[str, object]],
    supported_networks: Sequence[str],
    client_max_budget_minor: int,
) -> GuardDecision:
    if not accepts:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ACCEPTS_EMPTY_LIST_BLOCKED",
            reason="HTTP 402 Payment-Required accepts[] array must not be empty.",
            evidence={"accepts_count": 0},
        )
    supported_set = {n.strip() for n in supported_networks if n.strip()}
    valid_candidates: list[tuple[int, int, int, dict[str, object]]] = []
    for idx, entry in enumerate(accepts):
        scheme = str(entry.get("scheme", "")).strip()
        network = str(entry.get("network", "")).strip()
        raw_amount = str(entry.get("maxAmountRequired", "")).strip()
        if scheme not in {"exact", "upto"}:
            return GuardDecision(
                allowed=False,
                decision_code="X402_ACCEPTS_UNSUPPORTED_SCHEME_IN_LIST_BLOCKED",
                reason="All accepts[] entries must declare a valid scheme ('exact' or 'upto').",
                evidence={"index": idx, "scheme": scheme},
            )
        if not raw_amount.isdigit() or int(raw_amount) <= 0:
            return GuardDecision(
                allowed=False,
                decision_code="X402_ACCEPTS_NON_POSITIVE_INTEGER_AMOUNT_BLOCKED",
                reason="accepts[].maxAmountRequired must be a positive base-10 integer string.",
                evidence={"index": idx, "maxAmountRequired": raw_amount},
            )
        amount_int = int(raw_amount)
        if network in supported_set and amount_int <= client_max_budget_minor:
            scheme_rank = 0 if scheme == "exact" else 1
            valid_candidates.append((scheme_rank, amount_int, idx, dict(entry)))
    if not valid_candidates:
        return GuardDecision(
            allowed=False,
            decision_code="X402_ACCEPTS_NO_COMPATIBLE_WITHIN_BUDGET_OPTION_BLOCKED",
            reason="No accepts[] payment option matches client supported networks within budget.",
            evidence={
                "supported_networks": sorted(supported_set),
                "client_max_budget_minor": client_max_budget_minor,
            },
        )
    valid_candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    chosen = valid_candidates[0][3]
    return GuardDecision(
        allowed=True,
        decision_code="X402_ACCEPTS_DETERMINISTIC_OPTION_SELECTED",
        reason="Deterministic scheme-first, lowest-cost compatible payment option selected.",
        evidence={
            "selected_scheme": chosen.get("scheme"),
            "selected_network": chosen.get("network"),
            "selected_amount": int(str(chosen.get("maxAmountRequired"))),
        },
    )


# ---------------------------------------------------------------------------
# AD-04: x402 #3492/#3489/#3484 — Edge streaming completion gate
# ---------------------------------------------------------------------------
def evaluate_x402_edge_stream_completion_settlement_guard(
    *,
    upstream_http_status: int,
    stream_aborted: bool,
    bytes_streamed: int,
    expected_content_length: int,
    settlement_committed_early: bool,
) -> GuardDecision:
    if settlement_committed_early:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EDGE_PREMATURE_STREAM_SETTLEMENT_BLOCKED",
            reason="Edge middleware must not finalize settlement before upstream stream completes.",
            evidence={"settlement_committed_early": settlement_committed_early},
        )
    if upstream_http_status < 200 or upstream_http_status >= 300:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EDGE_NON_2XX_UPSTREAM_SETTLEMENT_BLOCKED",
            reason="Upstream handler returned non-2xx status; payment settlement must be aborted.",
            evidence={"upstream_http_status": upstream_http_status},
        )
    if stream_aborted or bytes_streamed != expected_content_length or expected_content_length <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EDGE_TRUNCATED_STREAM_SETTLEMENT_BLOCKED",
            reason="Upstream response stream aborted or truncated before expected_content_length.",
            evidence={
                "stream_aborted": stream_aborted,
                "bytes_streamed": bytes_streamed,
                "expected_content_length": expected_content_length,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_EDGE_STREAM_COMPLETED_SETTLEMENT_COMMITTED",
        reason="Upstream response stream completed intact prior to committing Payment-Response receipt.",
        evidence={"bytes_streamed": bytes_streamed, "upstream_http_status": upstream_http_status},
    )


# ---------------------------------------------------------------------------
# AD-05: UCP #971/#968/#965/#944 — Subscription pause/resume & skip-cycle guard
# ---------------------------------------------------------------------------
def evaluate_ucp_subscription_pause_skip_cycle_guard(
    *,
    subscription_status: str,
    requested_action: str,
    pause_duration_days: int,
    max_pause_days: int,
    billing_cycle_id: str,
    skipped_cycle_ids: Sequence[str],
    expected_next_billing_unix: int,
    reported_next_billing_unix: int,
) -> GuardDecision:
    if requested_action == "pause" and (pause_duration_days <= 0 or pause_duration_days > max_pause_days):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SUBSCRIPTION_PAUSE_DURATION_EXCEEDED_BLOCKED",
            reason="Requested subscription pause duration exceeds merchant max_pause_days policy.",
            evidence={"pause_duration_days": pause_duration_days, "max_pause_days": max_pause_days},
        )
    if requested_action == "charge":
        if subscription_status.strip().lower() == "paused":
            return GuardDecision(
                allowed=False,
                decision_code="UCP_SUBSCRIPTION_CHARGE_WHILE_PAUSED_BLOCKED",
                reason="Recurring charge is prohibited while subscription status is 'paused'.",
                evidence={"subscription_status": subscription_status, "billing_cycle_id": billing_cycle_id},
            )
        if billing_cycle_id in {c.strip() for c in skipped_cycle_ids}:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_SUBSCRIPTION_SKIPPED_CYCLE_CHARGE_BLOCKED",
                reason="Recurring charge is prohibited for a billing_cycle_id marked as skipped.",
                evidence={"billing_cycle_id": billing_cycle_id, "skipped_cycle_ids": list(skipped_cycle_ids)},
            )
    if expected_next_billing_unix != reported_next_billing_unix:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SUBSCRIPTION_NEXT_BILLING_DRIFT_BLOCKED",
            reason="Subscription reported_next_billing_unix does not match deterministic cycle shift.",
            evidence={
                "expected_next_billing_unix": expected_next_billing_unix,
                "reported_next_billing_unix": reported_next_billing_unix,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_SUBSCRIPTION_LIFECYCLE_STATE_VERIFIED",
        reason="Subscription pause/skip state transition and next_billing_at schedule verified.",
        evidence={
            "subscription_status": subscription_status,
            "requested_action": requested_action,
            "next_billing_unix": reported_next_billing_unix,
        },
    )


# ---------------------------------------------------------------------------
# AD-06: UCP #942/#937/#928/#925 — Split-shipment partial capture conservation
# ---------------------------------------------------------------------------
def evaluate_ucp_split_shipment_partial_capture_guard(
    *,
    authorized_total_minor: int,
    prior_captured_minor: int,
    current_shipment_items_minor: int,
    current_shipment_tax_minor: int,
    current_shipment_shipping_minor: int,
    shipping_already_captured: bool,
    carrier_code: str,
    tracking_number: str,
) -> GuardDecision:
    if not carrier_code.strip() or len(tracking_number.strip()) < 6:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SPLIT_SHIPMENT_MISSING_TRACKING_PROOF_BLOCKED",
            reason="Split-shipment partial capture requires non-empty carrier_code and valid tracking_number.",
            evidence={"carrier_code": carrier_code, "tracking_number": tracking_number},
        )
    if shipping_already_captured and current_shipment_shipping_minor > 0:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SPLIT_SHIPMENT_DUPLICATE_SHIPPING_FEE_BLOCKED",
            reason="Order-level shipping fee was already captured on an earlier split shipment.",
            evidence={
                "shipping_already_captured": shipping_already_captured,
                "current_shipment_shipping_minor": current_shipment_shipping_minor,
            },
        )
    current_total = current_shipment_items_minor + current_shipment_tax_minor + current_shipment_shipping_minor
    cumulative_captured = prior_captured_minor + current_total
    if current_total <= 0 or cumulative_captured > authorized_total_minor:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SPLIT_SHIPMENT_OVER_CAPTURE_BLOCKED",
            reason="Cumulative split-shipment captures exceed original authorized_total_minor.",
            evidence={
                "authorized_total_minor": authorized_total_minor,
                "prior_captured_minor": prior_captured_minor,
                "current_total": current_total,
                "cumulative_captured": cumulative_captured,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_SPLIT_SHIPMENT_PARTIAL_CAPTURE_VERIFIED",
        reason="Split-shipment carrier tracking proof, single shipping capture, and cumulative ceiling verified.",
        evidence={
            "current_capture_minor": current_total,
            "cumulative_captured_minor": cumulative_captured,
            "remaining_authorized_minor": authorized_total_minor - cumulative_captured,
        },
    )


# ---------------------------------------------------------------------------
# AD-07: UCP #841/#838/#833/#829 — Age-restricted & hazmat shipping gate
# ---------------------------------------------------------------------------
def evaluate_ucp_regulated_age_hazmat_fulfillment_guard(
    *,
    required_min_age: int,
    age_verified_min_years: int | None,
    age_verification_token_id: str | None,
    adult_signature_required_on_delivery: bool,
    hazmat_classes: Sequence[str],
    selected_shipping_method: str,
) -> GuardDecision:
    if required_min_age > 0:
        if (
            age_verified_min_years is None
            or age_verified_min_years < required_min_age
            or not age_verification_token_id
            or not age_verification_token_id.strip()
            or not adult_signature_required_on_delivery
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_REGULATED_AGE_VERIFICATION_OR_SIGNATURE_MISSING_BLOCKED",
                reason="Age-restricted item requires cryptographic age verification >= required_min_age and adult_signature_required_on_delivery.",
                evidence={
                    "required_min_age": required_min_age,
                    "age_verified_min_years": age_verified_min_years,
                    "age_verification_token_id": age_verification_token_id,
                    "adult_signature_required_on_delivery": adult_signature_required_on_delivery,
                },
            )
    normalized_hazmat = {h.strip().lower() for h in hazmat_classes if h.strip()}
    forbidden_hits = sorted(normalized_hazmat & AIR_FORBIDDEN_HAZMAT_CLASSES)
    if forbidden_hits and selected_shipping_method.strip().lower() in AIR_SHIPPING_METHODS:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_REGULATED_HAZMAT_AIR_TRANSPORT_FORBIDDEN_BLOCKED",
            reason="Hazardous materials (e.g., UN3480 lithium-ion or Class 3 flammable) cannot use air shipping.",
            evidence={
                "forbidden_hazmat_classes": forbidden_hits,
                "selected_shipping_method": selected_shipping_method,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_REGULATED_AGE_AND_HAZMAT_COMPLIANCE_VERIFIED",
        reason="Age-restricted verification, adult delivery signature, and ground hazmat routing verified.",
        evidence={
            "required_min_age": required_min_age,
            "hazmat_classes": sorted(normalized_hazmat),
            "selected_shipping_method": selected_shipping_method,
        },
    )


# ---------------------------------------------------------------------------
# AD-08: ACP #306/#305/#303/#301 — Webhook HMAC-SHA256 & monotonic sequence
# ---------------------------------------------------------------------------
def evaluate_acp_webhook_hmac_sequence_guard(
    *,
    webhook_secret: str,
    signature_timestamp: int,
    now_unix: int,
    raw_body: str,
    provided_hmac_hex: str,
    event_sequence: int,
    last_processed_sequence: int,
    current_session_state: str,
    incoming_event_state: str,
    max_timestamp_skew_seconds: int = 300,
) -> GuardDecision:
    if abs(now_unix - signature_timestamp) > max_timestamp_skew_seconds:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_WEBHOOK_TIMESTAMP_OUTSIDE_REPLAY_WINDOW_BLOCKED",
            reason="ACP webhook timestamp skew exceeds 300-second replay protection window.",
            evidence={
                "signature_timestamp": signature_timestamp,
                "now_unix": now_unix,
                "max_timestamp_skew_seconds": max_timestamp_skew_seconds,
            },
        )
    signed_payload = f"{signature_timestamp}.{raw_body}".encode("utf-8")
    expected_hmac = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hmac, provided_hmac_hex.strip().lower()):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_WEBHOOK_RAW_BODY_HMAC_MISMATCH_BLOCKED",
            reason="ACP webhook HMAC-SHA256 signature over raw body failed constant-time verification.",
            evidence={"signature_timestamp": signature_timestamp},
        )
    if event_sequence <= last_processed_sequence:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_WEBHOOK_STALE_OR_DUPLICATE_SEQUENCE_BLOCKED",
            reason="ACP webhook event_sequence is not strictly greater than last_processed_sequence.",
            evidence={
                "event_sequence": event_sequence,
                "last_processed_sequence": last_processed_sequence,
            },
        )
    terminal_states = {"completed", "canceled", "expired"}
    if current_session_state.strip().lower() in terminal_states and incoming_event_state.strip().lower() not in terminal_states:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_WEBHOOK_TERMINAL_STATE_REGRESSION_BLOCKED",
            reason="Cannot regress a terminal ACP checkout session state back to a non-terminal state.",
            evidence={
                "current_session_state": current_session_state,
                "incoming_event_state": incoming_event_state,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_WEBHOOK_HMAC_AND_SEQUENCE_VERIFIED",
        reason="ACP webhook raw-body HMAC, replay window, and monotonic state progression verified.",
        evidence={"event_sequence": event_sequence, "incoming_event_state": incoming_event_state},
    )


# ---------------------------------------------------------------------------
# AD-09: ACP #272/#269/#267/#264 — B2B tax-exemption certificate nexus guard
# ---------------------------------------------------------------------------
def evaluate_acp_b2b_tax_exemption_certificate_guard(
    *,
    claim_tax_exempt: bool,
    certificate_id: str | None,
    certificate_Verified_by_authority: bool,
    certificate_expires_at: int,
    now_unix: int,
    certificate_jurisdictions: Sequence[str],
    shipping_jurisdiction: str,
    certificate_buyer_tax_id: str,
    session_buyer_tax_id: str,
    reported_tax_amount_minor: int,
    standard_tax_amount_minor: int,
) -> GuardDecision:
    if not claim_tax_exempt:
        if reported_tax_amount_minor != standard_tax_amount_minor:
            return GuardDecision(
                allowed=False,
                decision_code="ACP_TAX_STANDARD_AMOUNT_MISMATCH_BLOCKED",
                reason="Non-exempt checkout must apply standard_tax_amount_minor.",
                evidence={
                    "reported_tax_amount_minor": reported_tax_amount_minor,
                    "standard_tax_amount_minor": standard_tax_amount_minor,
                },
            )
        return GuardDecision(
            allowed=True,
            decision_code="ACP_STANDARD_TAX_APPLIED",
            reason="Standard tax amount applied for non-exempt checkout.",
            evidence={"reported_tax_amount_minor": reported_tax_amount_minor},
        )
    if (
        not certificate_id
        or not certificate_Verified_by_authority
        or certificate_expires_at <= now_unix
        or shipping_jurisdiction.strip().upper() not in {j.strip().upper() for j in certificate_jurisdictions}
        or not session_buyer_tax_id.strip()
        or certificate_buyer_tax_id.strip() != session_buyer_tax_id.strip()
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_B2B_TAX_EXEMPTION_CERTIFICATE_INVALID_BLOCKED",
            reason="B2B tax exemption requires authority-verified, unexpired certificate covering shipping_jurisdiction and matching buyer_tax_id.",
            evidence={
                "certificate_id": certificate_id,
                "certificate_Verified_by_authority": certificate_Verified_by_authority,
                "certificate_expires_at": certificate_expires_at,
                "now_unix": now_unix,
                "shipping_jurisdiction": shipping_jurisdiction,
                "certificate_jurisdictions": list(certificate_jurisdictions),
            },
        )
    if reported_tax_amount_minor != 0:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_B2B_TAX_EXEMPT_NONZERO_TAX_DRIFT_BLOCKED",
            reason="Verified full tax-exemption certificate must result in zero tax_amount_minor.",
            evidence={"reported_tax_amount_minor": reported_tax_amount_minor},
        )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_B2B_TAX_EXEMPTION_CERTIFICATE_VERIFIED",
        reason="B2B tax-exemption certificate jurisdiction nexus, expiry, and buyer_tax_id verified.",
        evidence={"certificate_id": certificate_id, "shipping_jurisdiction": shipping_jurisdiction.upper()},
    )


# ---------------------------------------------------------------------------
# AD-10: AP2 #366/#362/#360/#356 — Step-up WebAuthn biometric UV/UP gate
# ---------------------------------------------------------------------------
def evaluate_ap2_step_up_biometric_uv_guard(
    *,
    amount_minor: int,
    autonomous_limit_minor: int,
    risk_tier: str,
    webauthn_assertion_present: bool,
    authenticator_flag_up: bool,
    authenticator_flag_uv: bool,
    rp_id_hash_hex: str,
    expected_rp_id: str,
) -> GuardDecision:
    requires_step_up = amount_minor > autonomous_limit_minor or risk_tier.strip().lower() == "high"
    if not requires_step_up:
        return GuardDecision(
            allowed=True,
            decision_code="AP2_WITHIN_AUTONOMOUS_LIMIT_ADMITTED",
            reason="Mandate is within autonomous agent limit and low/normal risk tier.",
            evidence={"amount_minor": amount_minor, "autonomous_limit_minor": autonomous_limit_minor},
        )
    expected_rp_hash = hashlib.sha256(expected_rp_id.strip().encode("utf-8")).hexdigest()
    if (
        not webauthn_assertion_present
        or not authenticator_flag_up
        or not authenticator_flag_uv
        or rp_id_hash_hex.strip().lower() != expected_rp_hash
    ):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_STEP_UP_WEBAUTHN_BIOMETRIC_UV_REQUIRED_BLOCKED",
            reason="Transactions above autonomous_limit_minor or high risk require WebAuthn assertion with UP=true, UV=true, and matching rpIdHash.",
            evidence={
                "amount_minor": amount_minor,
                "autonomous_limit_minor": autonomous_limit_minor,
                "risk_tier": risk_tier,
                "webauthn_assertion_present": webauthn_assertion_present,
                "authenticator_flag_up": authenticator_flag_up,
                "authenticator_flag_uv": authenticator_flag_uv,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_STEP_UP_WEBAUTHN_BIOMETRIC_UV_VERIFIED",
        reason="Hardware WebAuthn user presence (UP), biometric user verification (UV), and rpIdHash verified.",
        evidence={"expected_rp_id": expected_rp_id, "amount_minor": amount_minor},
    )


# ---------------------------------------------------------------------------
# AD-11: AP2 #345/#342/#340/#336 — Corporate M-of-N approval quorum & SoD
# ---------------------------------------------------------------------------
def evaluate_ap2_corporate_quorum_sod_guard(
    *,
    requester_principal_id: str,
    approver_principal_ids: Sequence[str],
    authorized_finance_approvers: Sequence[str],
    required_quorum: int,
    requisition_amount_minor: int,
    cost_center_available_budget_minor: int,
) -> GuardDecision:
    requester = requester_principal_id.strip()
    normalized_approvers = [a.strip() for a in approver_principal_ids if a.strip()]
    if requester in normalized_approvers:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_CORPORATE_SOD_SELF_APPROVAL_BLOCKED",
            reason="Separation of Duties (SoD) violation: requester cannot be one of the mandate approvers.",
            evidence={"requester_principal_id": requester, "approver_principal_ids": normalized_approvers},
        )
    allowed_set = {a.strip() for a in authorized_finance_approvers if a.strip()}
    distinct_valid_approvers = sorted({a for a in normalized_approvers if a in allowed_set})
    if len(distinct_valid_approvers) < required_quorum or required_quorum <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_CORPORATE_QUORUM_INSUFFICIENT_BLOCKED",
            reason="Corporate procurement mandate lacks M-of-N distinct authorized approver signatures.",
            evidence={
                "distinct_valid_approvers": distinct_valid_approvers,
                "required_quorum": required_quorum,
            },
        )
    if requisition_amount_minor <= 0 or requisition_amount_minor > cost_center_available_budget_minor:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_CORPORATE_COST_CENTER_BUDGET_EXCEEDED_BLOCKED",
            reason="Requisition amount exceeds department cost-center available budget.",
            evidence={
                "requisition_amount_minor": requisition_amount_minor,
                "cost_center_available_budget_minor": cost_center_available_budget_minor,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_CORPORATE_QUORUM_AND_SOD_VERIFIED",
        reason="Corporate M-of-N distinct approvers, Separation of Duties, and cost-center budget verified.",
        evidence={
            "distinct_valid_approvers": distinct_valid_approvers,
            "requisition_amount_minor": requisition_amount_minor,
        },
    )


# ---------------------------------------------------------------------------
# AD-12: MCP #3382/#3378/#3375/#3368 — RFC 8707 aud & token passthrough block
# ---------------------------------------------------------------------------
def evaluate_mcp_oauth_audience_passthrough_guard(
    *,
    token_aud: str,
    canonical_mcp_server_uri: str,
    token_cnf_jkt: str,
    dpop_proof_jkt: str,
    forward_caller_token_to_downstream: bool,
) -> GuardDecision:
    if forward_caller_token_to_downstream:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_OAUTH_DOWNSTREAM_TOKEN_PASSTHROUGH_BLOCKED",
            reason="MCP server must never forward caller OAuth access token to downstream third-party MCP servers.",
            evidence={"forward_caller_token_to_downstream": forward_caller_token_to_downstream},
        )
    if token_aud.strip() != canonical_mcp_server_uri.strip():
        return GuardDecision(
            allowed=False,
            decision_code="MCP_OAUTH_RFC8707_AUDIENCE_MISMATCH_BLOCKED",
            reason="OAuth 2.1 access token 'aud' claim does not exactly match canonical_mcp_server_uri.",
            evidence={"token_aud": token_aud, "canonical_mcp_server_uri": canonical_mcp_server_uri},
        )
    if not token_cnf_jkt.strip() or token_cnf_jkt.strip() != dpop_proof_jkt.strip():
        return GuardDecision(
            allowed=False,
            decision_code="MCP_OAUTH_DPOP_JKT_THUMBPRINT_MISMATCH_BLOCKED",
            reason="OAuth token cnf.jkt thumbprint does not match presented DPoP proof key thumbprint.",
            evidence={"token_cnf_jkt": token_cnf_jkt, "dpop_proof_jkt": dpop_proof_jkt},
        )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_OAUTH_AUDIENCE_AND_DPOP_VERIFIED",
        reason="MCP OAuth 2.1 RFC 8707 audience binding, DPoP thumbprint, and zero token passthrough verified.",
        evidence={"canonical_mcp_server_uri": canonical_mcp_server_uri, "cnf_jkt": token_cnf_jkt},
    )


# ---------------------------------------------------------------------------
# AD-13: Stripe AI #505/#502/#498/#494 — Connect fee & transfer conservation
# ---------------------------------------------------------------------------
def evaluate_stripe_connect_fee_transfer_guard(
    *,
    charge_amount_minor: int,
    application_fee_amount_minor: int,
    min_platform_fee_minor: int,
    transfer_data_amount_minor: int,
    on_behalf_of_country: str,
    settlement_currency_country: str,
    cross_border_transfers_enabled: bool,
) -> GuardDecision:
    if application_fee_amount_minor < min_platform_fee_minor or application_fee_amount_minor < 0:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_CONNECT_PLATFORM_FEE_BELOW_FLOOR_BLOCKED",
            reason="Connect application_fee_amount_minor is below required platform margin floor.",
            evidence={
                "application_fee_amount_minor": application_fee_amount_minor,
                "min_platform_fee_minor": min_platform_fee_minor,
            },
        )
    if transfer_data_amount_minor <= 0 or (transfer_data_amount_minor + application_fee_amount_minor) > charge_amount_minor:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_CONNECT_TRANSFER_PLUS_FEE_EXCEEDS_CHARGE_BLOCKED",
            reason="Connect transfer_data.amount + application_fee_amount exceeds charge_amount_minor.",
            evidence={
                "charge_amount_minor": charge_amount_minor,
                "transfer_data_amount_minor": transfer_data_amount_minor,
                "application_fee_amount_minor": application_fee_amount_minor,
            },
        )
    if not cross_border_transfers_enabled and on_behalf_of_country.strip().upper() != settlement_currency_country.strip().upper():
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_CONNECT_CROSS_BORDER_OBO_MISMATCH_BLOCKED",
            reason="on_behalf_of connected account country does not match settlement region while cross-border is disabled.",
            evidence={
                "on_behalf_of_country": on_behalf_of_country,
                "settlement_currency_country": settlement_currency_country,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="STRIPE_CONNECT_FEE_AND_TRANSFER_VERIFIED",
        reason="Stripe Connect platform fee floor, transfer conservation, and regional OBO alignment verified.",
        evidence={
            "charge_amount_minor": charge_amount_minor,
            "transfer_data_amount_minor": transfer_data_amount_minor,
            "application_fee_amount_minor": application_fee_amount_minor,
        },
    )


# ---------------------------------------------------------------------------
# AD-14: Visa TAP #10/#6/#5/#4 — Payment Passkey & Click-to-Pay FIDO2 binding
# ---------------------------------------------------------------------------
def evaluate_visa_tap_passkey_c2p_binding_guard(
    *,
    merchant_id: str,
    amount_minor: int,
    currency: str,
    tap_session_nonce: str,
    client_data_challenge_hex: str,
    client_data_origin: str,
    expected_checkout_origin: str,
    presented_sign_count: int,
    stored_sign_count: int,
) -> GuardDecision:
    expected_challenge = _canonical_jcs_sha256(
        {
            "amount_minor": amount_minor,
            "currency": currency.strip().upper(),
            "merchant_id": merchant_id.strip(),
            "tap_session_nonce": tap_session_nonce.strip(),
        }
    )
    if client_data_challenge_hex.strip().lower() != expected_challenge:
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_PASSKEY_CHALLENGE_MISMATCH_BLOCKED",
            reason="Visa Payment Passkey clientDataJSON.challenge does not match dynamic transaction JCS digest.",
            evidence={
                "client_data_challenge_hex": client_data_challenge_hex,
                "expected_challenge": expected_challenge,
            },
        )
    if client_data_origin.strip() != expected_checkout_origin.strip():
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_PASSKEY_ORIGIN_MISMATCH_BLOCKED",
            reason="Visa Payment Passkey clientDataJSON.origin does not match expected_checkout_origin.",
            evidence={
                "client_data_origin": client_data_origin,
                "expected_checkout_origin": expected_checkout_origin,
            },
        )
    if presented_sign_count <= stored_sign_count:
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_PASSKEY_SIGN_COUNT_REPLAY_BLOCKED",
            reason="Visa Payment Passkey authenticator signCount did not increment (cloned or replayed assertion).",
            evidence={
                "presented_sign_count": presented_sign_count,
                "stored_sign_count": stored_sign_count,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="VISA_TAP_PASSKEY_C2P_ASSERTION_VERIFIED",
        reason="Visa Payment Passkey dynamic transaction challenge, checkout origin, and monotonic signCount verified.",
        evidence={"expected_challenge": expected_challenge, "presented_sign_count": presented_sign_count},
    )


# ---------------------------------------------------------------------------
# AD-15: Sierra tau-bench 2.0 #618/#615/#612/#605 — Pharmacy refill & prior-auth
# ---------------------------------------------------------------------------
def evaluate_tau2_pharmacy_refill_prior_auth_guard(
    *,
    refills_remaining: int,
    is_controlled_substance: bool,
    days_since_last_fill: int,
    day_supply: int,
    prescriber_npi_active: bool,
    requires_prior_auth: bool,
    prior_auth_approved: bool,
) -> GuardDecision:
    if not prescriber_npi_active or refills_remaining <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_PHARMACY_INACTIVE_PRESCRIBER_OR_ZERO_REFILLS_BLOCKED",
            reason="Prescription refill requires active prescriber NPI and refills_remaining >= 1.",
            evidence={"prescriber_npi_active": prescriber_npi_active, "refills_remaining": refills_remaining},
        )
    min_ratio = 0.90 if is_controlled_substance else 0.75
    min_days_required = int(round(day_supply * min_ratio))
    if days_since_last_fill < min_days_required:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_PHARMACY_EARLY_REFILL_INTERVAL_BLOCKED",
            reason="Prescription refill requested before minimum days_since_last_fill threshold.",
            evidence={
                "is_controlled_substance": is_controlled_substance,
                "days_since_last_fill": days_since_last_fill,
                "min_days_required": min_days_required,
            },
        )
    if requires_prior_auth and not prior_auth_approved:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_PHARMACY_PRIOR_AUTHORIZATION_MISSING_BLOCKED",
            reason="Insurance prior authorization must be approved before dispensing and billing copay.",
            evidence={"requires_prior_auth": requires_prior_auth, "prior_auth_approved": prior_auth_approved},
        )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_PHARMACY_REFILL_AND_PRIOR_AUTH_VERIFIED",
        reason="Prescription refill interval, prescriber NPI status, and prior authorization verified.",
        evidence={"refills_remaining_after": refills_remaining - 1, "days_since_last_fill": days_since_last_fill},
    )


# ---------------------------------------------------------------------------
# AD-16: Sierra tau-bench 2.0 #598/#595/#592/#590 — B2B SaaS seat & renewal lock
# ---------------------------------------------------------------------------
def evaluate_tau2_saas_contract_seat_downgrade_guard(
    *,
    requested_seats: int,
    contracted_min_seats: int,
    now_unix: int,
    contract_renewal_unix: int,
    is_non_renewal_request: bool,
    required_notice_days: int,
    preserve_compliance_audit_logs: bool,
) -> GuardDecision:
    if not preserve_compliance_audit_logs:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SAAS_AUDIT_LOG_PURGE_ON_DOWNGRADE_BLOCKED",
            reason="Workspace tier or seat modification must preserve compliance audit log retention.",
            evidence={"preserve_compliance_audit_logs": preserve_compliance_audit_logs},
        )
    if now_unix < contract_renewal_unix and requested_seats < contracted_min_seats:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SAAS_MID_TERM_BELOW_CONTRACTED_SEATS_BLOCKED",
            reason="Mid-term seat reduction below contracted_min_seats is prohibited before contract_renewal_unix.",
            evidence={
                "requested_seats": requested_seats,
                "contracted_min_seats": contracted_min_seats,
                "now_unix": now_unix,
                "contract_renewal_unix": contract_renewal_unix,
            },
        )
    if is_non_renewal_request:
        notice_seconds_remaining = contract_renewal_unix - now_unix
        if notice_seconds_remaining < required_notice_days * 86400:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_SAAS_RENEWAL_NOTICE_WINDOW_MISSED_BLOCKED",
                reason="Annual contract non-renewal notice was submitted inside the locked notice window.",
                evidence={
                    "notice_days_remaining": notice_seconds_remaining // 86400,
                    "required_notice_days": required_notice_days,
                },
            )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_SAAS_CONTRACT_SEAT_CHANGE_VERIFIED",
        reason="B2B SaaS seat floor, renewal notice window, and compliance audit-log retention verified.",
        evidence={"requested_seats": requested_seats, "contracted_min_seats": contracted_min_seats},
    )
