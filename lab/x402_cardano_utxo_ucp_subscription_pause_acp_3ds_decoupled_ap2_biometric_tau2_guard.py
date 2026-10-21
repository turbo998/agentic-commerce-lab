"""Stage 164: x402 Cardano eUTxO / L3 Gas / ZK Solvency / Streaming Metering,
Google UCP Subscription Pause / Age-Gate / Warranty Binding, OpenAI/Stripe ACP
3DS Decoupled Auth / Instant Payout Velocity, Google AP2 FIDO2 Biometric /
SPIFFE Federated Trust, MCP Roots Sandbox, Stripe Connect Destination Charge,
Visa TAP Push-Provisioning & Sierra tau-bench 2.0 Price-Match / Loyalty Guard
(CD-01..CD-16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import pathlib
import urllib.parse
from typing import Any


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CD-01: x402 Cardano eUTxO Native Token & Min-Ada Preservation Guard
# ---------------------------------------------------------------------------
def evaluate_x402_cardano_eutxo_native_token_guard(
    *,
    network: str,
    policy_id: str,
    expected_policy_id: str,
    asset_name_hex: str,
    expected_asset_name_hex: str,
    token_amount: int,
    required_token_amount: int,
    output_lovelace: int,
    min_utxo_lovelace: int,
    tx_ttl_slot: int,
    current_slot: int,
    max_ttl_window_slots: int = 600,
    has_unauthorized_plutus_datum_drain: bool = False,
    collateral_return_valid: bool = True,
) -> GuardDecision:
    if network != "cardano:mainnet":
        return GuardDecision(
            False,
            "X402_CARDANO_NETWORK_UNSUPPORTED",
            f"Unsupported Cardano CAIP-2 network '{network}'.",
        )
    if policy_id.lower() != expected_policy_id.lower() or len(policy_id) != 56:
        return GuardDecision(
            False,
            "X402_CARDANO_POLICY_ID_MISMATCH",
            "Cardano native token policy_id does not match expected 56-hex script hash.",
        )
    if asset_name_hex.lower() != expected_asset_name_hex.lower():
        return GuardDecision(
            False,
            "X402_CARDANO_ASSET_NAME_MISMATCH",
            "Cardano native token asset_name_hex mismatch.",
        )
    if has_unauthorized_plutus_datum_drain or not collateral_return_valid:
        return GuardDecision(
            False,
            "X402_CARDANO_PLUTUS_COLLATERAL_DRAIN_BLOCKED",
            "Cardano eUTxO transaction contains unauthorized Plutus datum or invalid collateral return.",
        )
    if output_lovelace < min_utxo_lovelace or min_utxo_lovelace < 1_000_000:
        return GuardDecision(
            False,
            "X402_CARDANO_MIN_UTXO_LOVELACE_VIOLATION",
            "Cardano multi-asset output violates minUTxO lovelace preservation requirement.",
        )
    if tx_ttl_slot <= current_slot or (tx_ttl_slot - current_slot) > max_ttl_window_slots:
        return GuardDecision(
            False,
            "X402_CARDANO_TTL_SLOT_WINDOW_INVALID",
            "Cardano transaction ttl slot is expired or exceeds max_ttl_window_slots.",
        )
    if token_amount < required_token_amount or required_token_amount <= 0:
        return GuardDecision(
            False,
            "X402_CARDANO_TOKEN_AMOUNT_INSUFFICIENT",
            "Cardano native token transfer amount is below required settlement amount.",
        )
    return GuardDecision(
        True,
        "X402_CARDANO_EUTXO_SETTLEMENT_VERIFIED",
        "Cardano eUTxO native token bundle, minUTxO lovelace, and slot TTL verified.",
        {
            "network": network,
            "policy_id": policy_id.lower(),
            "token_amount": token_amount,
            "output_lovelace": output_lovelace,
        },
    )


# ---------------------------------------------------------------------------
# CD-02: x402 L3 Custom Gas Token & Sequencer Force-Inclusion Guard
# ---------------------------------------------------------------------------
def evaluate_x402_l3_custom_gas_sequencer_guard(
    *,
    payment_amount_minor: int,
    l1_da_blob_fee_minor: int,
    l3_execution_fee_minor: int,
    rollup_fee_scalar_bps: int,
    max_rollup_fee_scalar_bps: int = 12000,
    max_total_fee_ratio_bps: int = 2500,
    sequencer_soft_confirmed_only: bool = False,
    l1_batch_posted: bool = True,
    high_value_threshold_minor: int = 50_000,
) -> GuardDecision:
    if payment_amount_minor <= 0:
        return GuardDecision(
            False,
            "X402_L3_PAYMENT_AMOUNT_INVALID",
            "Payment amount must be positive.",
        )
    if rollup_fee_scalar_bps > max_rollup_fee_scalar_bps or rollup_fee_scalar_bps <= 0:
        return GuardDecision(
            False,
            "X402_L3_FEE_SCALAR_GOUGING_BLOCKED",
            "L3 custom gas token rollup_fee_scalar_bps exceeds maximum permitted ceiling.",
        )
    total_fee_minor = l1_da_blob_fee_minor + l3_execution_fee_minor
    fee_ratio_bps = (total_fee_minor * 10000) // payment_amount_minor
    if fee_ratio_bps > max_total_fee_ratio_bps:
        return GuardDecision(
            False,
            "X402_L3_DA_BLOB_FEE_CEILING_EXCEEDED",
            f"Combined L1 DA blob + L3 execution fee ({fee_ratio_bps} bps) exceeds {max_total_fee_ratio_bps} bps cap.",
        )
    if payment_amount_minor >= high_value_threshold_minor and (
        sequencer_soft_confirmed_only or not l1_batch_posted
    ):
        return GuardDecision(
            False,
            "X402_L3_UNPOSTED_SEQUENCER_SOFT_CONFIRM_REJECTED",
            "High-value L3 settlement cannot rely solely on unposted sequencer soft-confirmation.",
        )
    return GuardDecision(
        True,
        "X402_L3_CUSTOM_GAS_SETTLEMENT_ADMITTED",
        "L3 custom gas fee scalar, L1 DA blob fee ratio, and batch finality verified.",
        {"total_fee_minor": total_fee_minor, "fee_ratio_bps": fee_ratio_bps},
    )


# ---------------------------------------------------------------------------
# CD-03: x402 Facilitator Proof-of-Solvency & Reserve Attestation Guard
# ---------------------------------------------------------------------------
def evaluate_x402_facilitator_solvency_reserve_guard(
    *,
    attested_reserves_minor: int,
    total_liabilities_minor: int,
    pending_settlement_minor: int,
    merkle_root_age_seconds: int,
    max_attestation_age_seconds: int = 3600,
    min_reserve_ratio_bps: int = 10000,
    zk_snark_proof_valid: bool = True,
) -> GuardDecision:
    if not zk_snark_proof_valid:
        return GuardDecision(
            False,
            "X402_FACILITATOR_ZK_SOLVENCY_PROOF_INVALID",
            "Facilitator zero-knowledge proof-of-solvency verification failed.",
        )
    if merkle_root_age_seconds < 0 or merkle_root_age_seconds > max_attestation_age_seconds:
        return GuardDecision(
            False,
            "X402_FACILITATOR_RESERVE_ATTESTATION_STALE",
            "Facilitator Merkle reserve attestation age exceeds freshness window.",
        )
    projected_liabilities = total_liabilities_minor + max(0, pending_settlement_minor)
    if projected_liabilities <= 0:
        return GuardDecision(
            False,
            "X402_FACILITATOR_LIABILITIES_INVALID",
            "Projected facilitator liabilities must be positive.",
        )
    reserve_ratio_bps = (attested_reserves_minor * 10000) // projected_liabilities
    if reserve_ratio_bps < min_reserve_ratio_bps:
        return GuardDecision(
            False,
            "X402_FACILITATOR_UNDERCOLLATERALIZED_BLOCKED",
            f"Facilitator reserve ratio ({reserve_ratio_bps} bps) is below required {min_reserve_ratio_bps} bps.",
        )
    return GuardDecision(
        True,
        "X402_FACILITATOR_SOLVENCY_VERIFIED",
        "Facilitator ZK proof of solvency and reserve collateralization ratio verified.",
        {"reserve_ratio_bps": reserve_ratio_bps, "projected_liabilities": projected_liabilities},
    )


# ---------------------------------------------------------------------------
# CD-04: x402 Streaming SSE Pay-Per-Token Metering Settlement Guard
# ---------------------------------------------------------------------------
def evaluate_x402_streaming_token_metering_guard(
    *,
    expected_prev_chunk_seq: int,
    chunk_seq: int,
    delivered_tokens: int,
    billed_tokens: int,
    unit_price_micro_usd: int,
    cumulative_billed_micro_usd: int,
    stream_cap_micro_usd: int,
    chunk_payload_sha256: str,
    receipt_payload_sha256: str,
) -> GuardDecision:
    if chunk_seq != expected_prev_chunk_seq + 1:
        return GuardDecision(
            False,
            "X402_STREAM_CHUNK_SEQUENCE_GAP",
            f"Non-monotonic stream chunk_seq {chunk_seq} (expected {expected_prev_chunk_seq + 1}).",
        )
    if not hmac.compare_digest(chunk_payload_sha256.lower(), receipt_payload_sha256.lower()):
        return GuardDecision(
            False,
            "X402_STREAM_CHUNK_HASH_MISMATCH",
            "Streaming chunk payload SHA-256 does not match metered receipt digest.",
        )
    if billed_tokens > delivered_tokens or delivered_tokens <= 0:
        return GuardDecision(
            False,
            "X402_STREAM_GHOST_TOKEN_OVERBILLING_BLOCKED",
            "Billed token count exceeds cryptographically verified delivered tokens.",
        )
    chunk_charge_micro_usd = billed_tokens * unit_price_micro_usd
    new_cumulative_micro_usd = cumulative_billed_micro_usd + chunk_charge_micro_usd
    if new_cumulative_micro_usd > stream_cap_micro_usd:
        return GuardDecision(
            False,
            "X402_STREAM_BUDGET_CAP_EXCEEDED",
            "Cumulative streaming token charge exceeds authorized stream_cap_micro_usd.",
        )
    return GuardDecision(
        True,
        "X402_STREAM_METERING_CHUNK_SETTLED",
        "Streaming SSE pay-per-token chunk sequence, digest, and cap verified.",
        {
            "chunk_seq": chunk_seq,
            "chunk_charge_micro_usd": chunk_charge_micro_usd,
            "new_cumulative_micro_usd": new_cumulative_micro_usd,
        },
    )


# ---------------------------------------------------------------------------
# CD-05: Google UCP Subscription Pause & Proration Credit Conservation Guard
# ---------------------------------------------------------------------------
def evaluate_ucp_subscription_pause_proration_guard(
    *,
    subscription_state: str,
    requested_pause_days: int,
    max_pause_days: int = 90,
    cycle_price_minor: int,
    cycle_total_days: int,
    unused_days_in_cycle: int,
    reported_proration_credit_minor: int,
    pause_period_charge_minor: int = 0,
    auto_resume_notified_hours_ahead: int = 48,
) -> GuardDecision:
    if requested_pause_days <= 0 or requested_pause_days > max_pause_days:
        return GuardDecision(
            False,
            "UCP_SUBSCRIPTION_PAUSE_WINDOW_EXCEEDED",
            f"Requested pause duration ({requested_pause_days}d) exceeds max {max_pause_days}d.",
        )
    if subscription_state == "PAUSED" and pause_period_charge_minor > 0:
        return GuardDecision(
            False,
            "UCP_SUBSCRIPTION_PAUSED_BILLING_LEAK_BLOCKED",
            "Recurring charges are prohibited while subscription state is PAUSED.",
        )
    if cycle_total_days <= 0 or unused_days_in_cycle < 0 or unused_days_in_cycle > cycle_total_days:
        return GuardDecision(
            False,
            "UCP_SUBSCRIPTION_CYCLE_DAYS_INVALID",
            "Invalid subscription billing cycle day counts.",
        )
    expected_credit_minor = (cycle_price_minor * unused_days_in_cycle) // cycle_total_days
    if reported_proration_credit_minor != expected_credit_minor:
        return GuardDecision(
            False,
            "UCP_SUBSCRIPTION_PRORATION_CREDIT_DRIFT",
            f"Reported proration credit ({reported_proration_credit_minor}) != expected ({expected_credit_minor}).",
        )
    if auto_resume_notified_hours_ahead < 24:
        return GuardDecision(
            False,
            "UCP_SUBSCRIPTION_SILENT_AUTO_RESUME_BLOCKED",
            "Auto-resuming a paused subscription requires >= 24h advance notification.",
        )
    return GuardDecision(
        True,
        "UCP_SUBSCRIPTION_PAUSE_PRORATION_VERIFIED",
        "Subscription pause window, zero-charge state, and proration credit conservation verified.",
        {"expected_credit_minor": expected_credit_minor},
    )


# ---------------------------------------------------------------------------
# CD-06: Google UCP Age-Restricted & Regulated SKU Compliance Gate
# ---------------------------------------------------------------------------
def evaluate_ucp_age_restricted_regulated_sku_guard(
    *,
    is_age_restricted_sku: bool,
    required_minimum_age: int,
    zk_age_attestation_verified: bool,
    attested_minimum_age: int,
    issuer_trusted: bool,
    adult_signature_on_delivery_required: bool,
    self_asserted_only: bool = False,
) -> GuardDecision:
    if not is_age_restricted_sku:
        return GuardDecision(True, "UCP_UNRESTRICTED_SKU_ADMITTED", "SKU is not age-restricted.")
    if self_asserted_only or not zk_age_attestation_verified or not issuer_trusted:
        return GuardDecision(
            False,
            "UCP_AGE_ATTESTATION_UNVERIFIED_BLOCKED",
            "Age-restricted SKU requires trusted cryptographic zero-knowledge age attestation.",
        )
    if attested_minimum_age < required_minimum_age:
        return GuardDecision(
            False,
            "UCP_AGE_THRESHOLD_NOT_MET",
            f"Attested minimum age ({attested_minimum_age}) is below required ({required_minimum_age}).",
        )
    if not adult_signature_on_delivery_required:
        return GuardDecision(
            False,
            "UCP_ADULT_DELIVERY_SIGNATURE_MISSING",
            "Age-restricted fulfillment must enforce adult_signature_on_delivery_required=True.",
        )
    return GuardDecision(
        True,
        "UCP_AGE_RESTRICTED_COMPLIANCE_VERIFIED",
        "Zero-knowledge age attestation and adult delivery signature requirement verified.",
        {"required_minimum_age": required_minimum_age},
    )


# ---------------------------------------------------------------------------
# CD-07: Google UCP Warranty & Protection Plan Serial-to-SKU Binding Guard
# ---------------------------------------------------------------------------
def evaluate_ucp_warranty_protection_plan_binding_guard(
    *,
    parent_hardware_line_active: bool,
    parent_sku_price_minor: int,
    plan_min_hardware_price_minor: int,
    plan_max_hardware_price_minor: int,
    hardware_serial_sha256: str,
    bound_serial_sha256: str,
    coverage_start_epoch: int,
    delivery_confirmed_epoch: int,
) -> GuardDecision:
    if not parent_hardware_line_active:
        return GuardDecision(
            False,
            "UCP_ORPHAN_WARRANTY_ON_CANCELLED_HARDWARE_BLOCKED",
            "Protection plan cannot be billed when parent hardware line item is cancelled or absent.",
        )
    if not (plan_min_hardware_price_minor <= parent_sku_price_minor <= plan_max_hardware_price_minor):
        return GuardDecision(
            False,
            "UCP_WARRANTY_PRICE_BAND_MISMATCH",
            "Protection plan tier does not match parent hardware SKU price band.",
        )
    if not hardware_serial_sha256 or not hmac.compare_digest(
        hardware_serial_sha256.lower(), bound_serial_sha256.lower()
    ):
        return GuardDecision(
            False,
            "UCP_WARRANTY_SERIAL_BINDING_MISMATCH",
            "Protection plan serial digest does not match fulfilled hardware serial digest.",
        )
    if coverage_start_epoch < delivery_confirmed_epoch:
        return GuardDecision(
            False,
            "UCP_WARRANTY_PREMATURE_COVERAGE_START_BLOCKED",
            "Warranty coverage start timestamp cannot precede physical hardware delivery.",
        )
    return GuardDecision(
        True,
        "UCP_WARRANTY_SERIAL_BINDING_VERIFIED",
        "Protection plan price band, hardware serial binding, and delivery-aligned coverage verified.",
        {"hardware_serial_sha256": hardware_serial_sha256.lower()},
    )


# ---------------------------------------------------------------------------
# CD-08: OpenAI/Stripe ACP 3DS Decoupled Authentication & CAVV Binding Guard
# ---------------------------------------------------------------------------
def evaluate_acp_3ds_decoupled_auth_guard(
    *,
    trans_status: str,
    oob_challenge_completed: bool,
    elapsed_oob_seconds: int,
    max_oob_window_seconds: int = 900,
    cavv_present: bool,
    eci: str,
    bound_checkout_session_id: str,
    expected_checkout_session_id: str,
) -> GuardDecision:
    if trans_status != "D":
        return GuardDecision(
            False,
            "ACP_3DS_DECOUPLED_STATUS_INVALID",
            f"Expected EMV 3DS decoupled transStatus 'D', got '{trans_status}'.",
        )
    if not oob_challenge_completed:
        return GuardDecision(
            False,
            "ACP_3DS_DECOUPLED_PREMATURE_CAPTURE_BLOCKED",
            "Cannot capture decoupled 3DS transaction before out-of-band authentication completes.",
        )
    if elapsed_oob_seconds < 0 or elapsed_oob_seconds > max_oob_window_seconds:
        return GuardDecision(
            False,
            "ACP_3DS_DECOUPLED_WINDOW_EXPIRED",
            "Decoupled 3DS out-of-band authentication exceeded max_oob_window_seconds.",
        )
    if not cavv_present or eci not in {"05", "02"}:
        return GuardDecision(
            False,
            "ACP_3DS_CAVV_OR_ECI_INVALID",
            "Decoupled 3DS completion is missing cryptographic CAVV or liability-shift ECI ('05'/'02').",
        )
    if bound_checkout_session_id != expected_checkout_session_id:
        return GuardDecision(
            False,
            "ACP_3DS_SESSION_BINDING_MISMATCH",
            "3DS decoupled authentication result is bound to a different checkout_session_id.",
        )
    return GuardDecision(
        True,
        "ACP_3DS_DECOUPLED_AUTH_VERIFIED",
        "EMV 3DS decoupled OOB completion, CAVV/ECI liability shift, and session binding verified.",
        {"eci": eci, "elapsed_oob_seconds": elapsed_oob_seconds},
    )


# ---------------------------------------------------------------------------
# CD-09: OpenAI/Stripe ACP Instant Merchant Payout & Reserve Hold Guard
# ---------------------------------------------------------------------------
def evaluate_acp_instant_payout_reserve_guard(
    *,
    merchant_account_age_days: int,
    min_merchant_age_days: int = 30,
    delivery_confirmed: bool,
    bonded_reserve_minor: int,
    requested_instant_payout_minor: int,
    daily_instant_payout_used_minor: int,
    daily_instant_payout_cap_minor: int,
) -> GuardDecision:
    if requested_instant_payout_minor <= 0:
        return GuardDecision(
            False,
            "ACP_INSTANT_PAYOUT_AMOUNT_INVALID",
            "Requested instant payout amount must be positive.",
        )
    if merchant_account_age_days < min_merchant_age_days:
        return GuardDecision(
            False,
            "ACP_NEW_MERCHANT_INSTANT_PAYOUT_BLOCKED",
            "New merchant accounts below minimum seasoning age cannot execute instant payouts.",
        )
    if not delivery_confirmed and bonded_reserve_minor < requested_instant_payout_minor:
        return GuardDecision(
            False,
            "ACP_UNCONFIRMED_DELIVERY_RESERVE_DEFICIT",
            "Instant payout before delivery confirmation requires >= 100% bonded reserve coverage.",
        )
    if (daily_instant_payout_used_minor + requested_instant_payout_minor) > daily_instant_payout_cap_minor:
        return GuardDecision(
            False,
            "ACP_DAILY_INSTANT_PAYOUT_VELOCITY_EXCEEDED",
            "Requested instant payout exceeds merchant daily instant-payout velocity cap.",
        )
    return GuardDecision(
        True,
        "ACP_INSTANT_PAYOUT_ADMITTED",
        "Merchant seasoning, delivery/reserve coverage, and daily instant-payout velocity verified.",
        {"requested_instant_payout_minor": requested_instant_payout_minor},
    )


# ---------------------------------------------------------------------------
# CD-10: Google AP2 WebAuthn/FIDO2 Biometric Presence & SignCount Guard
# ---------------------------------------------------------------------------
def evaluate_ap2_fido2_biometric_uv_guard(
    *,
    authenticator_flags_byte: int,
    prev_sign_count: int,
    current_sign_count: int,
    rp_id_hash_hex: str,
    expected_rp_id: str,
    is_hardware_backed_passkey: bool = True,
) -> GuardDecision:
    up_bit = bool(authenticator_flags_byte & 0x01)
    uv_bit = bool(authenticator_flags_byte & 0x04)
    if not up_bit or not uv_bit:
        return GuardDecision(
            False,
            "AP2_FIDO2_BIOMETRIC_UV_UP_MISSING",
            "WebAuthn authenticatorData flags must have both User Present (0x01) and User Verified (0x04) bits set.",
        )
    if not is_hardware_backed_passkey:
        return GuardDecision(
            False,
            "AP2_FIDO2_SOFTWARE_PASSKEY_REJECTED",
            "High-value AP2 mandate requires hardware-backed FIDO2 authenticator.",
        )
    expected_rp_hash = hashlib.sha256(expected_rp_id.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(rp_id_hash_hex.lower(), expected_rp_hash.lower()):
        return GuardDecision(
            False,
            "AP2_FIDO2_RP_ID_HASH_MISMATCH",
            "WebAuthn authenticatorData rpIdHash does not match expected relying party.",
        )
    if current_sign_count <= prev_sign_count:
        return GuardDecision(
            False,
            "AP2_FIDO2_SIGN_COUNT_CLONE_DETECTED",
            f"Non-monotonic FIDO2 signCount ({current_sign_count} <= {prev_sign_count}) indicates cloned authenticator.",
        )
    return GuardDecision(
        True,
        "AP2_FIDO2_BIOMETRIC_PRESENCE_VERIFIED",
        "FIDO2 UP/UV biometric flags, rpIdHash, hardware backing, and monotonic signCount verified.",
        {"current_sign_count": current_sign_count},
    )


# ---------------------------------------------------------------------------
# CD-11: Google AP2 Cross-Org Federated Mandate & SPIFFE Trust Chain Guard
# ---------------------------------------------------------------------------
def evaluate_ap2_federated_spiffe_trust_guard(
    *,
    spiffe_id: str,
    trusted_trust_domains: set[str],
    actor_chain_depth: int,
    max_actor_chain_depth: int = 2,
    token_audience: str,
    expected_audience: str,
    mandate_scope_subset_of_parent: bool = True,
) -> GuardDecision:
    if not spiffe_id.startswith("spiffe://"):
        return GuardDecision(
            False,
            "AP2_SPIFFE_URI_MALFORMED",
            "Workload identity must be a valid spiffe://<trust_domain>/ns/<ns>/sa/<sa> URI.",
        )
    parts = spiffe_id[len("spiffe://") :].split("/")
    if len(parts) < 5 or parts[1] != "ns" or parts[3] != "sa":
        return GuardDecision(
            False,
            "AP2_SPIFFE_PATH_STRUCTURE_INVALID",
            "SPIFFE ID must follow spiffe://<trust_domain>/ns/<namespace>/sa/<service_account>.",
        )
    trust_domain = parts[0]
    if trust_domain not in trusted_trust_domains:
        return GuardDecision(
            False,
            "AP2_SPIFFE_UNTRUSTED_FEDERATION_DOMAIN",
            f"SPIFFE trust domain '{trust_domain}' is not in federated allowlist.",
        )
    if actor_chain_depth <= 0 or actor_chain_depth > max_actor_chain_depth:
        return GuardDecision(
            False,
            "AP2_RFC8693_ACTOR_CHAIN_DEPTH_EXCEEDED",
            f"RFC 8693 act claim delegation depth ({actor_chain_depth}) exceeds max {max_actor_chain_depth}.",
        )
    if token_audience != expected_audience:
        return GuardDecision(
            False,
            "AP2_FEDERATED_AUDIENCE_CONFUSION_BLOCKED",
            "Federated workload token audience does not match target commerce service.",
        )
    if not mandate_scope_subset_of_parent:
        return GuardDecision(
            False,
            "AP2_FEDERATED_SCOPE_ESCALATION_BLOCKED",
            "Exchanged federated token cannot escalate mandate scope beyond parent grant.",
        )
    return GuardDecision(
        True,
        "AP2_FEDERATED_SPIFFE_MANDATE_VERIFIED",
        "SPIFFE trust domain, RFC 8693 actor chain depth, audience, and scope attenuation verified.",
        {"trust_domain": trust_domain, "actor_chain_depth": actor_chain_depth},
    )


# ---------------------------------------------------------------------------
# CD-12: MCP Roots Workspace Sandbox Path-Traversal & Symlink Escape Guard
# ---------------------------------------------------------------------------
def evaluate_mcp_roots_sandbox_escape_guard(
    *,
    allowed_root_path: str,
    requested_uri_or_path: str,
    resolved_symlink_target_path: str | None = None,
) -> GuardDecision:
    decoded = urllib.parse.unquote(urllib.parse.unquote(requested_uri_or_path))
    if decoded.startswith("file://"):
        decoded = decoded[len("file://") :]
    if ".." in decoded.replace("\\", "/").split("/") or "\x00" in decoded:
        return GuardDecision(
            False,
            "MCP_ROOTS_PATH_TRAVERSAL_BLOCKED",
            "Requested path contains '..' traversal segments or null bytes.",
        )
    root_norm = pathlib.PurePosixPath(allowed_root_path.replace("\\", "/"))
    req_norm = pathlib.PurePosixPath(decoded.replace("\\", "/"))
    try:
        req_norm.relative_to(root_norm)
    except ValueError:
        return GuardDecision(
            False,
            "MCP_ROOTS_OUTSIDE_ALLOWED_WORKSPACE",
            f"Requested path '{req_norm}' is outside declared MCP root '{root_norm}'.",
        )
    if resolved_symlink_target_path is not None:
        sym_norm = pathlib.PurePosixPath(resolved_symlink_target_path.replace("\\", "/"))
        try:
            sym_norm.relative_to(root_norm)
        except ValueError:
            return GuardDecision(
                False,
                "MCP_ROOTS_SYMLINK_ESCAPE_BLOCKED",
                f"Symlink target '{sym_norm}' escapes declared MCP root '{root_norm}'.",
            )
    return GuardDecision(
        True,
        "MCP_ROOTS_WORKSPACE_PATH_VERIFIED",
        "Requested path and symlink target are strictly confined within declared MCP root.",
        {"normalized_path": str(req_norm)},
    )


# ---------------------------------------------------------------------------
# CD-13: Stripe Connect Destination Charge & Application Fee Cap Guard
# ---------------------------------------------------------------------------
def evaluate_stripe_connect_destination_charge_guard(
    *,
    charge_amount_minor: int,
    application_fee_amount_minor: int,
    processing_fee_minor: int,
    connected_account_transfers_active: bool,
    on_behalf_of_country: str,
    destination_country: str,
    max_application_fee_bps: int = 3000,
) -> GuardDecision:
    if not connected_account_transfers_active:
        return GuardDecision(
            False,
            "STRIPE_CONNECT_TRANSFERS_CAPABILITY_INACTIVE",
            "Destination connected account does not have active 'transfers' capability.",
        )
    if on_behalf_of_country != destination_country:
        return GuardDecision(
            False,
            "STRIPE_CONNECT_CROSS_REGION_OBO_MISMATCH",
            "on_behalf_of settlement country must match destination connected account region.",
        )
    if charge_amount_minor <= 0 or application_fee_amount_minor < 0:
        return GuardDecision(
            False,
            "STRIPE_CONNECT_CHARGE_AMOUNT_INVALID",
            "Invalid charge or application fee amount.",
        )
    fee_bps = (application_fee_amount_minor * 10000) // charge_amount_minor
    if fee_bps > max_application_fee_bps:
        return GuardDecision(
            False,
            "STRIPE_CONNECT_APPLICATION_FEE_CAP_EXCEEDED",
            f"Application fee ({fee_bps} bps) exceeds maximum {max_application_fee_bps} bps cap.",
        )
    merchant_net_minor = charge_amount_minor - application_fee_amount_minor - processing_fee_minor
    if merchant_net_minor <= 0:
        return GuardDecision(
            False,
            "STRIPE_CONNECT_NEGATIVE_MERCHANT_NET_BLOCKED",
            "Destination charge leaves zero or negative net settlement for connected merchant.",
        )
    return GuardDecision(
        True,
        "STRIPE_CONNECT_DESTINATION_CHARGE_VERIFIED",
        "Connected account capability, OBO region parity, fee cap, and positive merchant net verified.",
        {"merchant_net_minor": merchant_net_minor, "fee_bps": fee_bps},
    )


# ---------------------------------------------------------------------------
# CD-14: Visa TAP Push-to-Wallet Provisioning & SE/TEE Device Binding Guard
# ---------------------------------------------------------------------------
def evaluate_visa_tap_push_provisioning_guard(
    *,
    issuer_provisioning_cryptogram_valid: bool,
    wallet_device_se_hash: str,
    expected_device_se_hash: str,
    provisioning_nonce: str,
    seen_provisioning_nonces: set[str],
    token_requestor_id: str,
    allowed_token_requestor_ids: set[str],
) -> GuardDecision:
    if not issuer_provisioning_cryptogram_valid:
        return GuardDecision(
            False,
            "VISA_TAP_PROVISIONING_CRYPTOGRAM_INVALID",
            "Issuer push-provisioning cryptogram verification failed.",
        )
    if token_requestor_id not in allowed_token_requestor_ids:
        return GuardDecision(
            False,
            "VISA_TAP_UNTRUSTED_TOKEN_REQUESTOR_ID",
            f"Token Requestor ID '{token_requestor_id}' is not authorized.",
        )
    if provisioning_nonce in seen_provisioning_nonces:
        return GuardDecision(
            False,
            "VISA_TAP_PROVISIONING_NONCE_REPLAY_BLOCKED",
            "Push-to-wallet provisioning nonce has already been consumed.",
        )
    if not hmac.compare_digest(wallet_device_se_hash.lower(), expected_device_se_hash.lower()):
        return GuardDecision(
            False,
            "VISA_TAP_DEVICE_SE_BINDING_MISMATCH",
            "Target wallet Secure Element / TEE hardware binding hash mismatch.",
        )
    return GuardDecision(
        True,
        "VISA_TAP_PUSH_PROVISIONING_VERIFIED",
        "Visa TAP push-provisioning cryptogram, TRID, anti-replay nonce, and SE binding verified.",
        {"token_requestor_id": token_requestor_id},
    )


# ---------------------------------------------------------------------------
# CD-15: Sierra tau-bench 2.0 Retail Price-Match & Post-Purchase Price-Drop Guard
# ---------------------------------------------------------------------------
def evaluate_tau2_retail_price_match_guard(
    *,
    competitor_domain: str,
    authorized_competitor_domains: set[str],
    exact_sku_match: bool,
    competitor_in_stock_verified: bool,
    is_liquidation_or_flash_sale: bool,
    quote_age_hours: int,
    days_since_purchase: int,
    original_paid_minor: int,
    competitor_price_minor: int,
    requested_refund_diff_minor: int,
    max_price_match_window_days: int = 14,
) -> GuardDecision:
    if competitor_domain.lower() not in {d.lower() for d in authorized_competitor_domains}:
        return GuardDecision(
            False,
            "TAU2_PRICE_MATCH_UNAUTHORIZED_COMPETITOR",
            f"Competitor domain '{competitor_domain}' is not in authorized price-match retailer list.",
        )
    if not exact_sku_match or not competitor_in_stock_verified or is_liquidation_or_flash_sale:
        return GuardDecision(
            False,
            "TAU2_PRICE_MATCH_INELIGIBLE_OFFER_BLOCKED",
            "Price match requires exact SKU match, live stock availability, and non-liquidation pricing.",
        )
    if quote_age_hours > 24 or days_since_purchase > max_price_match_window_days:
        return GuardDecision(
            False,
            "TAU2_PRICE_MATCH_WINDOW_EXPIRED",
            "Competitor quote age (>24h) or purchase window (>14d) expired.",
        )
    expected_diff_minor = original_paid_minor - competitor_price_minor
    if expected_diff_minor <= 0 or requested_refund_diff_minor != expected_diff_minor:
        return GuardDecision(
            False,
            "TAU2_PRICE_MATCH_REFUND_DIFF_MISMATCH",
            f"Requested price-match refund ({requested_refund_diff_minor}) != verified diff ({expected_diff_minor}).",
        )
    return GuardDecision(
        True,
        "TAU2_PRICE_MATCH_REFUND_APPROVED",
        "Authorized competitor, exact in-stock SKU, window, and exact price difference verified.",
        {"refund_diff_minor": expected_diff_minor},
    )


# ---------------------------------------------------------------------------
# CD-16: Sierra tau-bench 2.0 Loyalty Status-Match & Miles Reinstatement Guard
# ---------------------------------------------------------------------------
def evaluate_tau2_loyalty_status_miles_reinstatement_guard(
    *,
    partner_statement_cryptographic_proof_valid: bool,
    expired_miles_amount: int,
    months_since_expiration: int,
    max_reinstatement_months: int = 12,
    reinstatement_fee_paid: bool,
    already_reinstated_tx_ids: set[str],
    reinstatement_tx_id: str,
) -> GuardDecision:
    if not partner_statement_cryptographic_proof_valid:
        return GuardDecision(
            False,
            "TAU2_LOYALTY_UNVERIFIED_STATEMENT_BLOCKED",
            "Status-match or miles reinstatement requires cryptographic partner statement proof.",
        )
    if reinstatement_tx_id in already_reinstated_tx_ids:
        return GuardDecision(
            False,
            "TAU2_LOYALTY_DOUBLE_REINSTATEMENT_BLOCKED",
            "Loyalty miles reinstatement transaction ID has already been credited.",
        )
    if months_since_expiration > max_reinstatement_months or expired_miles_amount <= 0:
        return GuardDecision(
            False,
            "TAU2_LOYALTY_EXPIRATION_WINDOW_EXCEEDED",
            f"Expired miles ({months_since_expiration}m old) exceed {max_reinstatement_months}m reinstatement window.",
        )
    if not reinstatement_fee_paid:
        return GuardDecision(
            False,
            "TAU2_LOYALTY_REINSTATEMENT_FEE_UNPAID",
            "Expired miles cannot be reinstated before required reinstatement fee is settled.",
        )
    return GuardDecision(
        True,
        "TAU2_LOYALTY_MILES_REINSTATED",
        "Partner statement proof, expiry window, fee payment, and idempotency verified.",
        {"reinstated_miles": expired_miles_amount},
    )
