"""Stage 166 deterministic guardrails: x402 Stellar Soroban SAC/XRPL tfPartialPayment/MEV rebate/sub-call split,
UCP pre-order price-drop guarantee/bundle partial return/cold-chain grocery expiry, ACP network token cryptogram/FX lock,
AP2 ephemeral key epoch rotation/MCC time-of-day velocity, MCP tool schema poisoning, Stripe Issuing real-time auth,
Visa TAP new-device cooling-off, and Sierra tau-bench 2.0 insurance FNOL & B2B SaaS seat commit lock (ST-01..ST-16).
"""

from __future__ import annotations

import dataclasses
from typing import Sequence


@dataclasses.dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str


# ST-01: x402 Foundation #3756/#3752/#3746 Stellar (stellar:pubnet) Soroban SAC USDC & Base Reserve Guard
def evaluate_x402_stellar_soroban_sac_settlement(
    *,
    network: str,
    sac_contract_id: str,
    expected_sac_contract_id: str,
    memo_id: str,
    expected_payment_nonce: str,
    remaining_xlm_stroops: int,
    min_base_reserve_stroops: int = 10_000_000,
    time_bounds_max_ts: int,
    now_ts: int,
    max_ttl_sec: int = 300,
    host_function_verified: bool,
) -> GuardDecision:
    if network != "stellar:pubnet":
        return GuardDecision(False, "X402_STELLAR_NETWORK_MISMATCH_BLOCKED", "Network must be stellar:pubnet.")
    if not host_function_verified or len(sac_contract_id) != 56 or not sac_contract_id.startswith("C"):
        return GuardDecision(
            False,
            "X402_STELLAR_SOROBAN_SAC_CONTRACT_INVALID_BLOCKED",
            "Soroban SAC invocation must be verified and target a valid 56-char C... contract ID.",
        )
    if sac_contract_id != expected_sac_contract_id:
        return GuardDecision(
            False,
            "X402_STELLAR_SAC_ASSET_MISMATCH_BLOCKED",
            "Soroban SAC contract ID does not match expected USDC SAC contract.",
        )
    if not memo_id or memo_id != expected_payment_nonce:
        return GuardDecision(
            False,
            "X402_STELLAR_MEMO_NONCE_UNBOUND_BLOCKED",
            "Stellar transaction memo_id must match expected payment_nonce.",
        )
    if remaining_xlm_stroops < min_base_reserve_stroops:
        return GuardDecision(
            False,
            "X402_STELLAR_BASE_RESERVE_UNDERFLOW_BLOCKED",
            "Remaining XLM balance would fall below Stellar account base reserve requirement.",
        )
    if time_bounds_max_ts <= now_ts or (time_bounds_max_ts - now_ts) > max_ttl_sec:
        return GuardDecision(
            False,
            "X402_STELLAR_TIME_BOUNDS_EXCEEDED_BLOCKED",
            "Stellar transaction time_bounds window is expired or exceeds max TTL.",
        )
    return GuardDecision(True, "X402_STELLAR_SOROBAN_SAC_ADMITTED", "Stellar Soroban SAC settlement verified.")


# ST-02: x402 Foundation #3764/#3760/#3754 XRPL (xrpl:mainnet) tfPartialPayment Exploit & DestinationTag Guard
def evaluate_x402_xrpl_partial_payment_guard(
    *,
    network: str,
    tx_flags: int,
    delivered_amount_drops: int,
    invoice_amount_drops: int,
    destination_tag: int | None,
    expected_destination_tag: int,
    last_ledger_sequence: int,
    current_ledger_sequence: int,
    max_ledger_window: int = 20,
) -> GuardDecision:
    tf_partial_payment = 0x00020000
    if network != "xrpl:mainnet":
        return GuardDecision(False, "X402_XRPL_NETWORK_MISMATCH_BLOCKED", "Network must be xrpl:mainnet.")
    if (tx_flags & tf_partial_payment) != 0 and delivered_amount_drops < invoice_amount_drops:
        return GuardDecision(
            False,
            "X402_XRPL_TF_PARTIAL_PAYMENT_EXPLOIT_BLOCKED",
            "XRPL tfPartialPayment flag with delivered_amount < invoice_amount is blocked.",
        )
    if delivered_amount_drops < invoice_amount_drops:
        return GuardDecision(
            False,
            "X402_XRPL_DELIVERED_AMOUNT_SHORTFALL_BLOCKED",
            "XRPL meta.delivered_amount must be at least invoice_amount_drops.",
        )
    if destination_tag is None or destination_tag != expected_destination_tag:
        return GuardDecision(
            False,
            "X402_XRPL_DESTINATION_TAG_MISMATCH_BLOCKED",
            "XRPL Payment must carry exact invoice DestinationTag.",
        )
    if last_ledger_sequence <= current_ledger_sequence or (last_ledger_sequence - current_ledger_sequence) > max_ledger_window:
        return GuardDecision(
            False,
            "X402_XRPL_LAST_LEDGER_SEQUENCE_WINDOW_BLOCKED",
            "XRPL LastLedgerSequence is expired or exceeds maximum ledger window.",
        )
    return GuardDecision(True, "X402_XRPL_PAYMENT_ADMITTED", "XRPL payment verified against partial-payment exploit.")


# ST-03: x402 Foundation #3772/#3768/#3762 Facilitator MEV-Protected Relay & Positive Slippage Rebate Guard
def evaluate_x402_facilitator_mev_rebate_guard(
    *,
    relay_mode: str,
    allowed_private_relays: Sequence[str],
    quoted_price_bps: int,
    execution_price_bps: int,
    max_slippage_bps: int,
    mev_surplus_minor: int,
    rebated_to_buyer_minor: int,
) -> GuardDecision:
    if relay_mode not in allowed_private_relays:
        return GuardDecision(
            False,
            "X402_PUBLIC_MEMPOOL_SANDWICH_EXPOSURE_BLOCKED",
            "Facilitator swap settlement must route via an approved MEV-protected private relay.",
        )
    if execution_price_bps < quoted_price_bps - max_slippage_bps:
        return GuardDecision(
            False,
            "X402_EXECUTION_SLIPPAGE_CAP_EXCEEDED_BLOCKED",
            "Execution price breached maximum allowed slippage tolerance.",
        )
    if mev_surplus_minor > 0 and rebated_to_buyer_minor < mev_surplus_minor:
        return GuardDecision(
            False,
            "X402_FACILITATOR_MEV_SURPLUS_RETENTION_BLOCKED",
            "Positive MEV / price-improvement surplus must be rebated to the buyer.",
        )
    return GuardDecision(True, "X402_MEV_PROTECTED_REBATE_ADMITTED", "Facilitator MEV protection and surplus rebate verified.")


# ST-04: x402 Foundation #3780/#3776/#3770 Multi-Hop Agent Sub-Call Revenue Split Conservation Guard
def evaluate_x402_subcall_revenue_split_guard(
    *,
    orchestrator_did: str,
    downstream_provider_dids: Sequence[str],
    downstream_splits_minor: Sequence[int],
    orchestrator_margin_minor: int,
    buyer_total_paid_minor: int,
    max_orchestrator_margin_bps: int = 2000,
    all_downstream_receipts_signed: bool,
) -> GuardDecision:
    if not downstream_provider_dids or len(downstream_provider_dids) != len(downstream_splits_minor):
        return GuardDecision(
            False,
            "X402_SUBCALL_SPLIT_VECTOR_INVALID_BLOCKED",
            "Downstream provider DIDs and split amounts must be non-empty and equal length.",
        )
    if orchestrator_did in downstream_provider_dids:
        return GuardDecision(
            False,
            "X402_SUBCALL_CIRCULAR_SELF_DEALING_BLOCKED",
            "Orchestrator DID cannot appear as a downstream sub-call recipient to siphon funds.",
        )
    if not all_downstream_receipts_signed:
        return GuardDecision(
            False,
            "X402_SUBCALL_RECEIPT_SIGNATURE_MISSING_BLOCKED",
            "Every downstream sub-call split requires a signed x402 execution receipt.",
        )
    if any(s <= 0 for s in downstream_splits_minor) or orchestrator_margin_minor < 0:
        return GuardDecision(
            False,
            "X402_SUBCALL_NEGATIVE_OR_ZERO_SPLIT_BLOCKED",
            "Downstream splits must be positive and orchestrator margin non-negative.",
        )
    if sum(downstream_splits_minor) + orchestrator_margin_minor != buyer_total_paid_minor:
        return GuardDecision(
            False,
            "X402_SUBCALL_SPLIT_CONSERVATION_MISMATCH_BLOCKED",
            "Sum of downstream splits plus orchestrator margin must equal buyer_total_paid_minor.",
        )
    if orchestrator_margin_minor * 10000 > buyer_total_paid_minor * max_orchestrator_margin_bps:
        return GuardDecision(
            False,
            "X402_ORCHESTRATOR_MARGIN_CAP_EXCEEDED_BLOCKED",
            "Orchestrator margin exceeds maximum allowed basis-point ceiling.",
        )
    return GuardDecision(True, "X402_SUBCALL_REVENUE_SPLIT_ADMITTED", "Multi-hop sub-call revenue split conserved.")


# ST-05: Google UCP #852/#848/#842/#838 Pre-Order Deposit Cap & Lowest-Price-Guarantee Capture Guard
def evaluate_ucp_preorder_price_guarantee_guard(
    *,
    preorder_msrp_minor: int,
    release_day_price_minor: int,
    deposit_paid_minor: int,
    requested_final_capture_minor: int,
    max_deposit_bps: int = 2500,
    carrier_shipped_scan_verified: bool,
) -> GuardDecision:
    if deposit_paid_minor * 10000 > preorder_msrp_minor * max_deposit_bps:
        return GuardDecision(
            False,
            "UCP_PREORDER_DEPOSIT_CAP_EXCEEDED_BLOCKED",
            "Pre-order deposit exceeds 25% statutory/protocol ceiling.",
        )
    if not carrier_shipped_scan_verified:
        return GuardDecision(
            False,
            "UCP_PREORDER_PRE_SHIPMENT_CAPTURE_BLOCKED",
            "Final pre-order balance capture is prohibited before verified carrier shipment scan.",
        )
    effective_price = min(preorder_msrp_minor, release_day_price_minor)
    expected_final_capture = max(0, effective_price - deposit_paid_minor)
    if requested_final_capture_minor != expected_final_capture:
        return GuardDecision(
            False,
            "UCP_PREORDER_PRICE_DROP_GUARANTEE_VIOLATION_BLOCKED",
            "Final capture must honor lowest-price guarantee minus deposit already paid.",
        )
    return GuardDecision(True, "UCP_PREORDER_FINAL_CAPTURE_ADMITTED", "Pre-order price guarantee and shipment gate verified.")


# ST-06: Google UCP #860/#856/#850 Bundled Kit Partial Return Pro-Rata Discount Clawback Guard
def evaluate_ucp_bundle_partial_return_guard(
    *,
    bundle_total_paid_minor: int,
    returned_item_standalone_msrp_minor: int,
    retained_items_standalone_msrp_minor: int,
    requested_refund_minor: int,
) -> GuardDecision:
    total_standalone = returned_item_standalone_msrp_minor + retained_items_standalone_msrp_minor
    if total_standalone <= 0 or bundle_total_paid_minor <= 0:
        return GuardDecision(False, "UCP_BUNDLE_PRICING_INVALID_BLOCKED", "Bundle and standalone prices must be positive.")
    max_unbundled_refund = max(0, bundle_total_paid_minor - retained_items_standalone_msrp_minor)
    prorated_refund = (bundle_total_paid_minor * returned_item_standalone_msrp_minor) // total_standalone
    allowed_ceiling = min(prorated_refund, max_unbundled_refund) if max_unbundled_refund > 0 else prorated_refund
    if requested_refund_minor > prorated_refund or requested_refund_minor > max_unbundled_refund:
        return GuardDecision(
            False,
            "UCP_BUNDLE_PARTIAL_RETURN_DISCOUNT_ARBITRAGE_BLOCKED",
            "Partial bundle return refund exceeds pro-rata share or retained standalone value clawback.",
        )
    if requested_refund_minor != allowed_ceiling:
        return GuardDecision(
            False,
            "UCP_BUNDLE_PRORATA_REFUND_MISMATCH_BLOCKED",
            "Partial bundle refund must match deterministic clawback-adjusted ceiling.",
        )
    return GuardDecision(True, "UCP_BUNDLE_PARTIAL_RETURN_ADMITTED", "Bundled kit partial return clawback verified.")


# ST-07: Google UCP #868/#864/#858 Perishable Cold-Chain Grocery Lot Expiry & Thermal Excursion Guard
def evaluate_ucp_perishable_cold_chain_guard(
    *,
    delivered_at_ts: int,
    lot_expiry_ts: int,
    min_shelf_life_sec: int = 432_000,
    max_recorded_temp_celsius: float,
    max_allowed_temp_celsius: float = 4.0,
    require_physical_return_on_spoilage: bool,
) -> GuardDecision:
    if max_recorded_temp_celsius > max_allowed_temp_celsius:
        return GuardDecision(
            False,
            "UCP_COLD_CHAIN_THERMAL_EXCURSION_AUTO_REFUND_BLOCKED",
            "Cold-chain temperature exceeded 4.0C ceiling; shipment must be rejected/auto-refunded.",
        )
    if (lot_expiry_ts - delivered_at_ts) < min_shelf_life_sec:
        return GuardDecision(
            False,
            "UCP_PERISHABLE_MIN_SHELF_LIFE_BREACH_BLOCKED",
            "Perishable lot remaining shelf life at delivery is below 5-day minimum.",
        )
    if require_physical_return_on_spoilage:
        return GuardDecision(
            False,
            "UCP_SPOILED_PERISHABLE_PHYSICAL_RETURN_DEMAND_BLOCKED",
            "Merchant cannot require physical return of spoiled/temperature-abused perishable food.",
        )
    return GuardDecision(True, "UCP_PERISHABLE_COLD_CHAIN_ADMITTED", "Cold-chain telemetry and lot shelf-life verified.")


# ST-08: OpenAI/Stripe ACP #278/#274/#268/#264 Network Token Cryptogram (TAVV) Domain & FPAN Fallback Guard
def evaluate_acp_network_token_cryptogram_guard(
    *,
    used_raw_fpan_fallback: bool,
    token_bin_8digit: str,
    cryptogram_present: bool,
    cryptogram_merchant_domain_hash: str,
    expected_merchant_domain_hash: str,
    cryptogram_age_sec: int,
    max_cryptogram_age_sec: int = 300,
    cryptogram_replayed: bool,
) -> GuardDecision:
    if used_raw_fpan_fallback:
        return GuardDecision(
            False,
            "ACP_RAW_FPAN_FALLBACK_DOWNGRADE_BLOCKED",
            "Silent downgrade from network token to raw FPAN is prohibited.",
        )
    if len(token_bin_8digit) != 8 or not token_bin_8digit.isdigit():
        return GuardDecision(
            False,
            "ACP_NETWORK_TOKEN_8DIGIT_IIN_INVALID_BLOCKED",
            "Network token must carry a valid 8-digit ISO/IEC 7812-1 IIN/BIN.",
        )
    if not cryptogram_present or cryptogram_replayed:
        return GuardDecision(
            False,
            "ACP_TAVV_CRYPTOGRAM_MISSING_OR_REPLAYED_BLOCKED",
            "Single-use network token TAVV cryptogram is missing or replayed.",
        )
    if cryptogram_merchant_domain_hash != expected_merchant_domain_hash:
        return GuardDecision(
            False,
            "ACP_CRYPTOGRAM_MERCHANT_DOMAIN_MISMATCH_BLOCKED",
            "Network token cryptogram merchant_domain_hash does not match checkout merchant.",
        )
    if cryptogram_age_sec < 0 or cryptogram_age_sec > max_cryptogram_age_sec:
        return GuardDecision(
            False,
            "ACP_CRYPTOGRAM_TTL_EXPIRED_BLOCKED",
            "Network token cryptogram age exceeds 300s freshness window.",
        )
    return GuardDecision(True, "ACP_NETWORK_TOKEN_CRYPTOGRAM_ADMITTED", "ACP network token TAVV and domain binding verified.")


# ST-09: OpenAI/Stripe ACP #286/#282/#276 Multi-Currency FX Rate Lock & Refund FX Parity Guard
def evaluate_acp_multicurrency_fx_parity_guard(
    *,
    fx_quote_age_sec: int,
    max_quote_ttl_sec: int = 600,
    fx_spread_bps: int,
    max_spread_bps: int = 150,
    is_refund: bool,
    capture_fx_rate_micro: int,
    applied_fx_rate_micro: int,
) -> GuardDecision:
    if not is_refund and (fx_quote_age_sec < 0 or fx_quote_age_sec > max_quote_ttl_sec):
        return GuardDecision(
            False,
            "ACP_FX_QUOTE_TTL_EXPIRED_BLOCKED",
            "Multi-currency settlement FX quote expired.",
        )
    if fx_spread_bps < 0 or fx_spread_bps > max_spread_bps:
        return GuardDecision(
            False,
            "ACP_FX_SPREAD_CAP_EXCEEDED_BLOCKED",
            "Multi-currency FX spread exceeds 150 bps ceiling.",
        )
    if is_refund and applied_fx_rate_micro != capture_fx_rate_micro:
        return GuardDecision(
            False,
            "ACP_REFUND_FX_RATE_DRIFT_ARBITRAGE_BLOCKED",
            "Full/partial refund must apply original capture FX rate to prevent FX drift loss.",
        )
    return GuardDecision(True, "ACP_MULTICURRENCY_FX_PARITY_ADMITTED", "Multi-currency FX lock and refund parity verified.")


# ST-10: Google AP2 #348/#344/#338/#334 Ephemeral Session Key Forward-Secrecy Epoch Rotation Guard
def evaluate_ap2_ephemeral_key_rotation_guard(
    *,
    key_epoch: int,
    min_active_epoch: int,
    epoch_age_sec: int,
    max_epoch_age_sec: int = 3600,
    epoch_signature_count: int,
    max_signatures_per_epoch: int = 50,
    hkdf_ratchet_prev_hash_matched: bool,
) -> GuardDecision:
    if key_epoch < min_active_epoch:
        return GuardDecision(
            False,
            "AP2_REVOKED_OR_STALE_KEY_EPOCH_BLOCKED",
            "Mandate signed with a revoked or superseded ephemeral key epoch.",
        )
    if not hkdf_ratchet_prev_hash_matched:
        return GuardDecision(
            False,
            "AP2_HKDF_RATCHET_CHAIN_BROKEN_BLOCKED",
            "Ephemeral session key HKDF ratchet continuity check failed.",
        )
    if epoch_age_sec > max_epoch_age_sec or epoch_signature_count > max_signatures_per_epoch:
        return GuardDecision(
            False,
            "AP2_EPHEMERAL_KEY_ROTATION_OVERDUE_BLOCKED",
            "Ephemeral session key exceeded 3600s TTL or 50-signature rotation cap.",
        )
    return GuardDecision(True, "AP2_EPHEMERAL_KEY_EPOCH_ADMITTED", "AP2 forward-secret ephemeral key epoch verified.")


# ST-11: Google AP2 #356/#352/#346 Spend Velocity Sliding-Window & MCC Time-of-Day Policy Guard
def evaluate_ap2_velocity_mcc_time_window_guard(
    *,
    mcc: str,
    allowed_mccs: Sequence[str],
    current_hour_utc: int,
    allowed_start_hour_utc: int,
    allowed_end_hour_utc: int,
    tx_amount_minor: int,
    hourly_spent_minor: int,
    hourly_cap_minor: int,
    subminute_tx_count: int,
    max_subminute_tx_count: int = 3,
) -> GuardDecision:
    if mcc not in allowed_mccs:
        return GuardDecision(
            False,
            "AP2_MCC_POLICY_RESTRICTION_BLOCKED",
            "Merchant Category Code (MCC) is not permitted by the AP2 mandate.",
        )
    if not (allowed_start_hour_utc <= current_hour_utc < allowed_end_hour_utc):
        return GuardDecision(
            False,
            "AP2_TIME_OF_DAY_WINDOW_VIOLATION_BLOCKED",
            "Transaction attempted outside permitted UTC business hours window.",
        )
    if subminute_tx_count > max_subminute_tx_count:
        return GuardDecision(
            False,
            "AP2_SUBMINUTE_BURST_SPLITTING_BLOCKED",
            "Rapid sub-minute transaction burst detected (smurfing/velocity bypass).",
        )
    if hourly_spent_minor + tx_amount_minor > hourly_cap_minor:
        return GuardDecision(
            False,
            "AP2_HOURLY_SLIDING_VELOCITY_CAP_EXCEEDED_BLOCKED",
            "Transaction would exceed hourly sliding-window spend velocity cap.",
        )
    return GuardDecision(True, "AP2_VELOCITY_MCC_TIME_POLICY_ADMITTED", "AP2 MCC, time-of-day, and sliding velocity verified.")


# ST-12: MCP #3365/#3360/#3355 Tool Schema Poisoning & Hidden Prompt-Injection Sanitizer
def evaluate_mcp_tool_schema_poisoning_guard(
    *,
    tool_description: str,
    schema_sha256: str,
    pinned_lockfile_sha256: str,
    has_invisible_unicode_tags: bool,
) -> GuardDecision:
    lowered = tool_description.lower()
    poison_markers = ("ignore previous", "<system>", "override_instruction", "exfiltrate", "curl http")
    if has_invisible_unicode_tags or any(marker in lowered for marker in poison_markers):
        return GuardDecision(
            False,
            "MCP_TOOL_SCHEMA_PROMPT_INJECTION_POISONING_BLOCKED",
            "MCP tool description contains hidden prompt-injection markers or Unicode tag characters.",
        )
    if not schema_sha256 or schema_sha256 != pinned_lockfile_sha256:
        return GuardDecision(
            False,
            "MCP_TOOL_SCHEMA_LOCKFILE_HASH_DRIFT_BLOCKED",
            "MCP tool schema SHA-256 drifted from pinned lockfile digest (rug-pull blocked).",
        )
    return GuardDecision(True, "MCP_TOOL_SCHEMA_INTEGRITY_ADMITTED", "MCP tool schema integrity and description verified.")


# ST-13: Stripe AI #490/#486/#480 Issuing Virtual Card Real-Time Authorization Webhook Guard
def evaluate_stripe_issuing_realtime_auth_guard(
    *,
    webhook_decision_latency_ms: int,
    max_sla_ms: int = 2000,
    mcc: str,
    auth_amount_minor: int,
    existing_open_holds_minor: int,
    card_spending_limit_minor: int,
    merchant_country: str,
    allowed_countries: Sequence[str],
) -> GuardDecision:
    prohibited_cash_mccs = {"4829", "6010", "6011", "6051", "7995"}
    if webhook_decision_latency_ms > max_sla_ms:
        return GuardDecision(
            False,
            "STRIPE_ISSUING_WEBHOOK_SLA_TIMEOUT_DECLINED",
            "Real-time issuing authorization exceeded 2000ms SLA and failed closed.",
        )
    if mcc in prohibited_cash_mccs:
        return GuardDecision(
            False,
            "STRIPE_ISSUING_QUASI_CASH_MCC_BLOCKED",
            "Quasi-cash, wire transfer, ATM, and wagering MCCs are blocked on agent virtual cards.",
        )
    if merchant_country not in allowed_countries:
        return GuardDecision(
            False,
            "STRIPE_ISSUING_COUNTRY_RESTRICTION_BLOCKED",
            "Merchant country is outside virtual card geographic allowlist.",
        )
    if auth_amount_minor + existing_open_holds_minor > card_spending_limit_minor:
        return GuardDecision(
            False,
            "STRIPE_ISSUING_OPEN_HOLDS_LIMIT_EXCEEDED_BLOCKED",
            "Authorization amount plus open holds exceeds virtual card spending limit.",
        )
    return GuardDecision(True, "STRIPE_ISSUING_REALTIME_AUTH_APPROVED", "Stripe Issuing real-time authorization approved.")


# ST-14: Visa TAP #32/#29/#26 New-Device Enrollment 24h Cooling-Off & SMS Downgrade Guard
def evaluate_visa_tap_device_cooldown_guard(
    *,
    now_ts: int,
    device_enrolled_at_ts: int,
    cooldown_window_sec: int = 86_400,
    tx_amount_minor: int,
    new_device_cap_minor: int = 10_000,
    issuer_oob_idv_verified: bool,
    step_up_method: str,
) -> GuardDecision:
    if step_up_method == "sms_otp":
        return GuardDecision(
            False,
            "VISA_TAP_SMS_OTP_DOWNGRADE_BLOCKED",
            "Downgrade from hardware FIDO2/passkey to phishable SMS OTP is prohibited.",
        )
    in_cooldown = (now_ts - device_enrolled_at_ts) < cooldown_window_sec
    if in_cooldown and tx_amount_minor > new_device_cap_minor and not issuer_oob_idv_verified:
        return GuardDecision(
            False,
            "VISA_TAP_NEW_DEVICE_24H_COOLDOWN_CAP_BLOCKED",
            "High-value transaction within 24h of new device enrollment requires issuer OOB IDV.",
        )
    return GuardDecision(True, "VISA_TAP_DEVICE_STEP_UP_ADMITTED", "Visa TAP device cooling-off and step-up verified.")


# ST-15: Sierra tau-bench 2.0 #592/#588/#585 Insurance FNOL Active Coverage & Deductible Math Guard
def evaluate_tau2_insurance_fnol_claim_guard(
    *,
    policy_active_start_ts: int,
    policy_active_end_ts: int,
    incident_ts: int,
    peril_code: str,
    covered_perils: Sequence[str],
    approved_loss_minor: int,
    deductible_minor: int,
    coverage_limit_minor: int,
    proposed_payout_minor: int,
) -> GuardDecision:
    if not (policy_active_start_ts <= incident_ts <= policy_active_end_ts):
        return GuardDecision(
            False,
            "TAU2_INSURANCE_INCIDENT_OUTSIDE_ACTIVE_POLICY_BLOCKED",
            "Incident timestamp falls outside active policy effective period (backdating blocked).",
        )
    if peril_code not in covered_perils:
        return GuardDecision(
            False,
            "TAU2_INSURANCE_EXCLUDED_PERIL_BLOCKED",
            "Claimed peril is excluded under the policy schedule.",
        )
    expected_payout = min(coverage_limit_minor, max(0, approved_loss_minor - deductible_minor))
    if proposed_payout_minor != expected_payout:
        return GuardDecision(
            False,
            "TAU2_INSURANCE_DEDUCTIBLE_OR_LIMIT_MATH_MISMATCH_BLOCKED",
            "Proposed claim payout violates deductible subtraction or policy limit cap.",
        )
    return GuardDecision(True, "TAU2_INSURANCE_FNOL_PAYOUT_ADMITTED", "Insurance FNOL policy coverage and deductible math verified.")


# ST-16: Sierra tau-bench 2.0 #600/#596/#593 B2B SaaS Seat Commit-Term Lock & Data Export Guard
def evaluate_tau2_saas_seat_commit_export_guard(
    *,
    now_ts: int,
    renewal_date_ts: int,
    current_seats: int,
    requested_seats: int,
    contract_min_committed_seats: int,
    apply_immediately: bool,
    workspace_deprovision_requested: bool,
    data_export_archive_sha256: str,
) -> GuardDecision:
    if apply_immediately and now_ts < renewal_date_ts and requested_seats < contract_min_committed_seats:
        return GuardDecision(
            False,
            "TAU2_SAAS_MIDTERM_COMMIT_SEAT_REDUCTION_BLOCKED",
            "Immediate seat reduction below annual committed minimum before renewal date is blocked.",
        )
    if workspace_deprovision_requested and len(data_export_archive_sha256) != 64:
        return GuardDecision(
            False,
            "TAU2_SAAS_DEPROVISION_WITHOUT_EXPORT_ARCHIVE_BLOCKED",
            "Workspace deprovisioning requires a verified 64-hex customer data export SHA-256 archive.",
        )
    if requested_seats <= 0 and not workspace_deprovision_requested:
        return GuardDecision(
            False,
            "TAU2_SAAS_ZERO_SEAT_INVALID_BLOCKED",
            "Active subscription seat count must remain positive.",
        )
    return GuardDecision(True, "TAU2_SAAS_SEAT_CHANGE_ADMITTED", "B2B SaaS seat commitment and export retention verified.")
