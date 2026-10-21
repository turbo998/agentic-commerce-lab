"""Stage 162 deterministic guardrails: x402 Algorand ASA (`axfer`) & Polkadot AssetHub `transfer_keep_alive`, facilitator webhook HMAC & client session budget, Google UCP BOPIS/Curbside PIN, DCC markup & trade-in clawback mandate, OpenAI/Stripe ACP chargeback representment & B2B tax-exempt certificate, Google AP2 hardware device attestation & M-of-N treasury co-signing, MCP `sampling/createMessage`, Stripe AI portal scope, Visa TAP MIT CIT trace, and Sierra tau2-bench utility meter-read & HazMat carrier guards (AR-01..AR-16)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Sequence


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    decision_code: str
    plane: str
    evidence: dict[str, object]


# ---------------------------------------------------------------------------
# 1. x402 Foundation Guards (AR-01 .. AR-04)
# ---------------------------------------------------------------------------


def verify_x402_algorand_asa_transfer_guard(
    *,
    network: str,
    tx_type: str,
    xfer_asset_id: int,
    expected_asa_id: int,
    asset_receiver: str,
    expected_pay_to: str,
    asset_amount: int,
    min_required_amount: int,
    asset_close_to: str,
    asset_sender: str,
    first_valid_round: int,
    last_valid_round: int,
    current_round: int,
    max_round_window: int = 1000,
) -> GuardEvaluation:
    """AR-01 (#3710/#3705/#3698): Algorand ASA (`axfer`) exact-scheme guard."""
    if network != "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k":
        return GuardEvaluation(
            False,
            "X402_ALGORAND_NETWORK_MISMATCH",
            "settlement",
            {"network": network},
        )
    if tx_type != "axfer":
        return GuardEvaluation(
            False,
            "X402_ALGORAND_TX_TYPE_NOT_AXFER",
            "settlement",
            {"tx_type": tx_type},
        )
    if asset_close_to.strip() != "":
        return GuardEvaluation(
            False,
            "X402_ALGORAND_ASSET_CLOSE_TO_FORBIDDEN",
            "settlement",
            {"asset_close_to": asset_close_to},
        )
    if asset_sender.strip() != "":
        return GuardEvaluation(
            False,
            "X402_ALGORAND_CLAWBACK_ASSET_SENDER_FORBIDDEN",
            "settlement",
            {"asset_sender": asset_sender},
        )
    if xfer_asset_id != expected_asa_id:
        return GuardEvaluation(
            False,
            "X402_ALGORAND_ASA_ID_MISMATCH",
            "settlement",
            {"xfer_asset_id": xfer_asset_id, "expected_asa_id": expected_asa_id},
        )
    if asset_receiver != expected_pay_to:
        return GuardEvaluation(
            False,
            "X402_ALGORAND_RECEIVER_MISMATCH",
            "settlement",
            {"asset_receiver": asset_receiver, "expected_pay_to": expected_pay_to},
        )
    if asset_amount < min_required_amount or min_required_amount <= 0:
        return GuardEvaluation(
            False,
            "X402_ALGORAND_AMOUNT_INSUFFICIENT",
            "settlement",
            {"asset_amount": asset_amount, "min_required_amount": min_required_amount},
        )
    round_span = last_valid_round - first_valid_round
    if round_span <= 0 or round_span > max_round_window:
        return GuardEvaluation(
            False,
            "X402_ALGORAND_ROUND_WINDOW_INVALID",
            "settlement",
            {"round_span": round_span, "max_round_window": max_round_window},
        )
    if not (first_valid_round <= current_round <= last_valid_round):
        return GuardEvaluation(
            False,
            "X402_ALGORAND_ROUND_OUT_OF_RANGE",
            "settlement",
            {
                "first_valid_round": first_valid_round,
                "current_round": current_round,
                "last_valid_round": last_valid_round,
            },
        )
    return GuardEvaluation(
        True,
        "X402_ALGORAND_ASA_TRANSFER_VERIFIED",
        "settlement",
        {
            "xfer_asset_id": xfer_asset_id,
            "asset_amount": asset_amount,
            "round_span": round_span,
        },
    )


def verify_x402_polkadot_assethub_keep_alive_guard(
    *,
    network: str,
    pallet_call: str,
    keep_alive: bool,
    asset_id: int,
    expected_asset_id: int,
    beneficiary: str,
    expected_pay_to: str,
    amount: int,
    min_required_amount: int,
    is_mortal_era: bool,
    era_period_blocks: int,
    signed_genesis_hash: str,
    expected_genesis_hash: str,
    max_era_period_blocks: int = 256,
) -> GuardEvaluation:
    """AR-02 (#3685/#3681/#3676): Polkadot AssetHub `Assets::transfer_keep_alive` guard."""
    if network != "polkadot:68d56f15f85d3136970ec16946040bc1":
        return GuardEvaluation(
            False,
            "X402_POLKADOT_NETWORK_MISMATCH",
            "settlement",
            {"network": network},
        )
    if pallet_call != "Assets::transfer_keep_alive" or not keep_alive:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_KEEP_ALIVE_REQUIRED",
            "settlement",
            {"pallet_call": pallet_call, "keep_alive": keep_alive},
        )
    if asset_id != expected_asset_id:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_ASSET_ID_MISMATCH",
            "settlement",
            {"asset_id": asset_id, "expected_asset_id": expected_asset_id},
        )
    if beneficiary != expected_pay_to:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_BENEFICIARY_MISMATCH",
            "settlement",
            {"beneficiary": beneficiary, "expected_pay_to": expected_pay_to},
        )
    if amount < min_required_amount or min_required_amount <= 0:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_AMOUNT_INSUFFICIENT",
            "settlement",
            {"amount": amount, "min_required_amount": min_required_amount},
        )
    if not is_mortal_era or era_period_blocks <= 0 or era_period_blocks > max_era_period_blocks:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_IMMORTAL_OR_EXCESSIVE_ERA_BLOCKED",
            "settlement",
            {"is_mortal_era": is_mortal_era, "era_period_blocks": era_period_blocks},
        )
    if signed_genesis_hash != expected_genesis_hash:
        return GuardEvaluation(
            False,
            "X402_POLKADOT_GENESIS_HASH_MISMATCH",
            "settlement",
            {
                "signed_genesis_hash": signed_genesis_hash,
                "expected_genesis_hash": expected_genesis_hash,
            },
        )
    return GuardEvaluation(
        True,
        "X402_POLKADOT_ASSETHUB_TRANSFER_VERIFIED",
        "settlement",
        {"asset_id": asset_id, "amount": amount, "era_period_blocks": era_period_blocks},
    )


def verify_x402_facilitator_webhook_hmac_guard(
    *,
    webhook_secret: str,
    timestamp_epoch: int,
    current_epoch: int,
    event_id: str,
    raw_body: str,
    provided_signature_hex: str,
    seen_event_ids: Sequence[str],
    max_skew_seconds: int = 300,
) -> GuardEvaluation:
    """AR-03 (#3670/#3664/#3658): Facilitator webhook HMAC-SHA256 & event replay guard."""
    if not event_id.strip():
        return GuardEvaluation(
            False,
            "X402_WEBHOOK_EVENT_ID_EMPTY",
            "settlement",
            {"event_id": event_id},
        )
    if event_id in set(seen_event_ids):
        return GuardEvaluation(
            False,
            "X402_WEBHOOK_EVENT_REPLAY_DETECTED",
            "settlement",
            {"event_id": event_id},
        )
    skew = abs(current_epoch - timestamp_epoch)
    if skew > max_skew_seconds:
        return GuardEvaluation(
            False,
            "X402_WEBHOOK_TIMESTAMP_SKEW_EXCEEDED",
            "settlement",
            {"skew_seconds": skew, "max_skew_seconds": max_skew_seconds},
        )
    signing_input = f"{timestamp_epoch}.{event_id}.{raw_body}".encode("utf-8")
    expected_sig = hmac.new(
        webhook_secret.encode("utf-8"), signing_input, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_signature_hex):
        return GuardEvaluation(
            False,
            "X402_WEBHOOK_HMAC_SIGNATURE_INVALID",
            "settlement",
            {"event_id": event_id},
        )
    return GuardEvaluation(
        True,
        "X402_WEBHOOK_CALLBACK_AUTHENTICATED",
        "settlement",
        {"event_id": event_id, "skew_seconds": skew},
    )


def verify_x402_client_session_budget_guard(
    *,
    origin: str,
    requested_payment_atomic: int,
    cumulative_origin_spent_atomic: int,
    cumulative_session_spent_atomic: int,
    max_payment_per_request_atomic: int,
    max_payment_per_origin_atomic: int,
    max_payment_per_session_atomic: int,
) -> GuardEvaluation:
    """AR-04 (#3455/#3449/#3442): `@x402/core` client cumulative session & origin budget breaker."""
    if requested_payment_atomic <= 0:
        return GuardEvaluation(
            False,
            "X402_CLIENT_PAYMENT_AMOUNT_NON_POSITIVE",
            "settlement",
            {"requested_payment_atomic": requested_payment_atomic},
        )
    if requested_payment_atomic > max_payment_per_request_atomic:
        return GuardEvaluation(
            False,
            "X402_CLIENT_PER_REQUEST_CEILING_EXCEEDED",
            "settlement",
            {
                "requested_payment_atomic": requested_payment_atomic,
                "max_payment_per_request_atomic": max_payment_per_request_atomic,
            },
        )
    new_origin_total = cumulative_origin_spent_atomic + requested_payment_atomic
    if new_origin_total > max_payment_per_origin_atomic:
        return GuardEvaluation(
            False,
            "X402_CLIENT_ORIGIN_BUDGET_EXHAUSTED",
            "settlement",
            {
                "origin": origin,
                "new_origin_total": new_origin_total,
                "max_payment_per_origin_atomic": max_payment_per_origin_atomic,
            },
        )
    new_session_total = cumulative_session_spent_atomic + requested_payment_atomic
    if new_session_total > max_payment_per_session_atomic:
        return GuardEvaluation(
            False,
            "X402_CLIENT_SESSION_BUDGET_EXHAUSTED",
            "settlement",
            {
                "new_session_total": new_session_total,
                "max_payment_per_session_atomic": max_payment_per_session_atomic,
            },
        )
    return GuardEvaluation(
        True,
        "X402_CLIENT_BUDGET_WITHIN_LIMITS",
        "settlement",
        {
            "origin": origin,
            "new_origin_total": new_origin_total,
            "new_session_total": new_session_total,
        },
    )


# ---------------------------------------------------------------------------
# 2. Google UCP Guards (AR-05 .. AR-07)
# ---------------------------------------------------------------------------


def verify_ucp_bopis_curbside_pickup_guard(
    *,
    pickup_store_id: str,
    active_store_ids: Sequence[str],
    pickup_window_start_epoch: int,
    pickup_window_end_epoch: int,
    authorized_pickup_person_sha256: str,
    order_fulfillment_state: str,
    emit_pickup_release_pin: bool,
) -> GuardEvaluation:
    """AR-05 (#814/#809/#804/#798): UCP BOPIS & curbside pickup locker/PIN handoff guard."""
    if pickup_store_id not in set(active_store_ids):
        return GuardEvaluation(
            False,
            "UCP_BOPIS_STORE_INACTIVE_OR_UNKNOWN",
            "catalog_discovery",
            {"pickup_store_id": pickup_store_id},
        )
    if pickup_window_end_epoch <= pickup_window_start_epoch:
        return GuardEvaluation(
            False,
            "UCP_BOPIS_WINDOW_INVALID",
            "catalog_discovery",
            {
                "pickup_window_start_epoch": pickup_window_start_epoch,
                "pickup_window_end_epoch": pickup_window_end_epoch,
            },
        )
    if len(authorized_pickup_person_sha256.strip()) != 64:
        return GuardEvaluation(
            False,
            "UCP_BOPIS_PICKUP_PERSON_HASH_MISSING",
            "catalog_discovery",
            {"authorized_pickup_person_sha256": authorized_pickup_person_sha256},
        )
    if emit_pickup_release_pin and order_fulfillment_state != "ready_for_pickup":
        return GuardEvaluation(
            False,
            "UCP_BOPIS_PREMATURE_RELEASE_PIN_BLOCKED",
            "catalog_discovery",
            {"order_fulfillment_state": order_fulfillment_state},
        )
    return GuardEvaluation(
        True,
        "UCP_BOPIS_CURBSIDE_PICKUP_VERIFIED",
        "catalog_discovery",
        {
            "pickup_store_id": pickup_store_id,
            "order_fulfillment_state": order_fulfillment_state,
        },
    )


def verify_ucp_dcc_multi_currency_parity_guard(
    *,
    display_currency: str,
    settlement_currency: str,
    fx_rate_quote_id: str,
    dcc_applied: bool,
    dcc_markup_bps: int,
    buyer_dcc_opt_in: bool,
    max_dcc_markup_bps: int = 300,
) -> GuardEvaluation:
    """AR-06 (#795/#790/#784/#778): UCP multi-currency display vs. settlement & DCC anti-gouging guard."""
    if not settlement_currency.strip() or not display_currency.strip():
        return GuardEvaluation(
            False,
            "UCP_CURRENCY_CODE_MISSING",
            "catalog_discovery",
            {"display_currency": display_currency, "settlement_currency": settlement_currency},
        )
    if display_currency != settlement_currency and not fx_rate_quote_id.strip():
        return GuardEvaluation(
            False,
            "UCP_CROSS_CURRENCY_FX_QUOTE_ID_REQUIRED",
            "catalog_discovery",
            {"display_currency": display_currency, "settlement_currency": settlement_currency},
        )
    if dcc_applied:
        if not buyer_dcc_opt_in:
            return GuardEvaluation(
                False,
                "UCP_DCC_WITHOUT_EXPLICIT_BUYER_OPT_IN_BLOCKED",
                "catalog_discovery",
                {"buyer_dcc_opt_in": buyer_dcc_opt_in},
            )
        if dcc_markup_bps < 0 or dcc_markup_bps > max_dcc_markup_bps:
            return GuardEvaluation(
                False,
                "UCP_DCC_MARKUP_BPS_EXCEEDS_CAP",
                "catalog_discovery",
                {"dcc_markup_bps": dcc_markup_bps, "max_dcc_markup_bps": max_dcc_markup_bps},
            )
    return GuardEvaluation(
        True,
        "UCP_MULTI_CURRENCY_DCC_PARITY_VERIFIED",
        "catalog_discovery",
        {
            "display_currency": display_currency,
            "settlement_currency": settlement_currency,
            "dcc_markup_bps": dcc_markup_bps,
        },
    )


def verify_ucp_trade_in_credit_mandate_guard(
    *,
    instant_trade_in_credit_applied: bool,
    trade_in_serial_sha256: str,
    provisional_credit_minor: int,
    max_trade_in_credit_minor: int,
    new_item_price_minor: int,
    clawback_authorization_mandate_id: str,
    inspection_deadline_days: int,
) -> GuardEvaluation:
    """AR-07 (#775/#770/#764/#758): UCP trade-in conditional valuation & clawback mandate guard."""
    if not instant_trade_in_credit_applied:
        return GuardEvaluation(
            True,
            "UCP_NO_INSTANT_TRADE_IN_APPLIED",
            "catalog_discovery",
            {"instant_trade_in_credit_applied": False},
        )
    if len(trade_in_serial_sha256.strip()) != 64:
        return GuardEvaluation(
            False,
            "UCP_TRADE_IN_SERIAL_HASH_INVALID",
            "catalog_discovery",
            {"trade_in_serial_sha256": trade_in_serial_sha256},
        )
    if (
        provisional_credit_minor <= 0
        or provisional_credit_minor > max_trade_in_credit_minor
        or provisional_credit_minor > new_item_price_minor
    ):
        return GuardEvaluation(
            False,
            "UCP_TRADE_IN_CREDIT_OUT_OF_BOUNDS",
            "catalog_discovery",
            {
                "provisional_credit_minor": provisional_credit_minor,
                "max_trade_in_credit_minor": max_trade_in_credit_minor,
                "new_item_price_minor": new_item_price_minor,
            },
        )
    if not clawback_authorization_mandate_id.strip():
        return GuardEvaluation(
            False,
            "UCP_TRADE_IN_CLAWBACK_MANDATE_REQUIRED",
            "catalog_discovery",
            {"provisional_credit_minor": provisional_credit_minor},
        )
    if inspection_deadline_days < 7 or inspection_deadline_days > 30:
        return GuardEvaluation(
            False,
            "UCP_TRADE_IN_INSPECTION_WINDOW_INVALID",
            "catalog_discovery",
            {"inspection_deadline_days": inspection_deadline_days},
        )
    return GuardEvaluation(
        True,
        "UCP_TRADE_IN_CREDIT_MANDATE_VERIFIED",
        "catalog_discovery",
        {
            "provisional_credit_minor": provisional_credit_minor,
            "clawback_authorization_mandate_id": clawback_authorization_mandate_id,
        },
    )


# ---------------------------------------------------------------------------
# 3. OpenAI / Stripe ACP Guards (AR-08 .. AR-09)
# ---------------------------------------------------------------------------


def verify_acp_chargeback_representment_guard(
    *,
    dispute_id: str,
    order_receipt_sha256: str,
    delivery_proof_sha256: str,
    user_approval_jws: str,
    evidence_submitted_epoch: int,
    dispute_due_by_epoch: int,
    disputed_amount_minor: int,
    receipt_total_minor: int,
) -> GuardEvaluation:
    """AR-08 (#249/#245/#238/#233): ACP chargeback representment evidence bundle guard."""
    if not dispute_id.strip():
        return GuardEvaluation(
            False,
            "ACP_DISPUTE_ID_MISSING",
            "dispute_non_repudiation",
            {"dispute_id": dispute_id},
        )
    if len(order_receipt_sha256.strip()) != 64 or len(delivery_proof_sha256.strip()) != 64:
        return GuardEvaluation(
            False,
            "ACP_REPRESENTMENT_HASH_EVIDENCE_INCOMPLETE",
            "dispute_non_repudiation",
            {
                "order_receipt_sha256": order_receipt_sha256,
                "delivery_proof_sha256": delivery_proof_sha256,
            },
        )
    if len(user_approval_jws.split(".")) != 3:
        return GuardEvaluation(
            False,
            "ACP_REPRESENTMENT_USER_APPROVAL_JWS_MISSING",
            "dispute_non_repudiation",
            {"user_approval_jws": user_approval_jws},
        )
    if evidence_submitted_epoch > dispute_due_by_epoch:
        return GuardEvaluation(
            False,
            "ACP_REPRESENTMENT_DEADLINE_EXPIRED",
            "dispute_non_repudiation",
            {
                "evidence_submitted_epoch": evidence_submitted_epoch,
                "dispute_due_by_epoch": dispute_due_by_epoch,
            },
        )
    if disputed_amount_minor <= 0 or disputed_amount_minor > receipt_total_minor:
        return GuardEvaluation(
            False,
            "ACP_REPRESENTMENT_AMOUNT_MISMATCH",
            "dispute_non_repudiation",
            {
                "disputed_amount_minor": disputed_amount_minor,
                "receipt_total_minor": receipt_total_minor,
            },
        )
    return GuardEvaluation(
        True,
        "ACP_CHARGEBACK_REPRESENTMENT_BUNDLE_VERIFIED",
        "dispute_non_repudiation",
        {"dispute_id": dispute_id, "disputed_amount_minor": disputed_amount_minor},
    )


def verify_acp_b2b_tax_exemption_certificate_guard(
    *,
    tax_exempt_claimed: bool,
    tax_minor: int,
    tax_exemption_certificate_id: str,
    certificate_jurisdiction: str,
    shipping_jurisdiction: str,
    certificate_expires_epoch: int,
    current_epoch: int,
    verified_by_tax_engine: bool,
) -> GuardEvaluation:
    """AR-09 (#229/#224/#219/#212): ACP B2B tax-exemption certificate verification guard."""
    if not tax_exempt_claimed:
        if tax_minor <= 0:
            return GuardEvaluation(
                False,
                "ACP_ZERO_TAX_WITHOUT_EXEMPTION_BLOCKED",
                "settlement",
                {"tax_minor": tax_minor},
            )
        return GuardEvaluation(
            True,
            "ACP_STANDARD_TAXED_CHECKOUT_VERIFIED",
            "settlement",
            {"tax_minor": tax_minor},
        )
    if not tax_exemption_certificate_id.strip():
        return GuardEvaluation(
            False,
            "ACP_TAX_EXEMPT_CERTIFICATE_ID_MISSING",
            "settlement",
            {"tax_exemption_certificate_id": tax_exemption_certificate_id},
        )
    if certificate_jurisdiction != shipping_jurisdiction:
        return GuardEvaluation(
            False,
            "ACP_TAX_EXEMPT_JURISDICTION_MISMATCH",
            "settlement",
            {
                "certificate_jurisdiction": certificate_jurisdiction,
                "shipping_jurisdiction": shipping_jurisdiction,
            },
        )
    if certificate_expires_epoch <= current_epoch:
        return GuardEvaluation(
            False,
            "ACP_TAX_EXEMPT_CERTIFICATE_EXPIRED",
            "settlement",
            {
                "certificate_expires_epoch": certificate_expires_epoch,
                "current_epoch": current_epoch,
            },
        )
    if not verified_by_tax_engine:
        return GuardEvaluation(
            False,
            "ACP_TAX_EXEMPT_ENGINE_VERIFICATION_REQUIRED",
            "settlement",
            {"verified_by_tax_engine": verified_by_tax_engine},
        )
    return GuardEvaluation(
        True,
        "ACP_B2B_TAX_EXEMPT_CERTIFICATE_VERIFIED",
        "settlement",
        {
            "tax_exemption_certificate_id": tax_exemption_certificate_id,
            "certificate_jurisdiction": certificate_jurisdiction,
        },
    )


# ---------------------------------------------------------------------------
# 4. Google AP2 Guards (AR-10 .. AR-11)
# ---------------------------------------------------------------------------


def verify_ap2_hardware_device_attestation_guard(
    *,
    amount_minor: int,
    high_value_threshold_minor: int,
    device_attestation_verdict: str,
    attested_public_key_thumbprint: str,
    mandate_cnf_jkt: str,
    attestation_issued_epoch: int,
    current_epoch: int,
    max_attestation_age_seconds: int = 300,
) -> GuardEvaluation:
    """AR-10 (#318/#314/#309/#304): Google AP2 hardware-backed device attestation binding."""
    if amount_minor < high_value_threshold_minor:
        return GuardEvaluation(
            True,
            "AP2_BELOW_HIGH_VALUE_DEVICE_ATTESTATION_THRESHOLD",
            "mandates_tokenization",
            {"amount_minor": amount_minor},
        )
    if device_attestation_verdict != "MEETS_STRONG_INTEGRITY":
        return GuardEvaluation(
            False,
            "AP2_DEVICE_ATTESTATION_STRONG_INTEGRITY_REQUIRED",
            "mandates_tokenization",
            {"device_attestation_verdict": device_attestation_verdict},
        )
    if not attested_public_key_thumbprint.strip() or attested_public_key_thumbprint != mandate_cnf_jkt:
        return GuardEvaluation(
            False,
            "AP2_ATTESTED_KEY_CNF_JKT_MISMATCH",
            "mandates_tokenization",
            {
                "attested_public_key_thumbprint": attested_public_key_thumbprint,
                "mandate_cnf_jkt": mandate_cnf_jkt,
            },
        )
    age = current_epoch - attestation_issued_epoch
    if age < 0 or age > max_attestation_age_seconds:
        return GuardEvaluation(
            False,
            "AP2_DEVICE_ATTESTATION_STALE",
            "mandates_tokenization",
            {"age_seconds": age, "max_attestation_age_seconds": max_attestation_age_seconds},
        )
    return GuardEvaluation(
        True,
        "AP2_HARDWARE_DEVICE_ATTESTATION_VERIFIED",
        "mandates_tokenization",
        {"mandate_cnf_jkt": mandate_cnf_jkt, "age_seconds": age},
    )


def verify_ap2_treasury_cosigner_threshold_guard(
    *,
    mandate_digest_sha256: str,
    required_threshold_m: int,
    authorized_treasury_signers: Sequence[str],
    cosigner_entries: Sequence[dict[str, object]],
) -> GuardEvaluation:
    """AR-11 (#301/#296/#291/#286): Google AP2 M-of-N treasury co-signer threshold mandate guard."""
    if required_threshold_m < 2 or len(mandate_digest_sha256.strip()) != 64:
        return GuardEvaluation(
            False,
            "AP2_TREASURY_THRESHOLD_POLICY_INVALID",
            "mandates_tokenization",
            {"required_threshold_m": required_threshold_m},
        )
    allowed_signers = set(authorized_treasury_signers)
    verified_signers: set[str] = set()
    for entry in cosigner_entries:
        signer_id = str(entry.get("signer_id", ""))
        signed_digest = str(entry.get("signed_digest_sha256", ""))
        sig_valid = bool(entry.get("signature_valid", False))
        if signer_id not in allowed_signers:
            return GuardEvaluation(
                False,
                "AP2_TREASURY_UNAUTHORIZED_COSIGNER",
                "mandates_tokenization",
                {"signer_id": signer_id},
            )
        if signed_digest != mandate_digest_sha256 or not sig_valid:
            return GuardEvaluation(
                False,
                "AP2_TREASURY_COSIGNATURE_DIGEST_OR_SIG_INVALID",
                "mandates_tokenization",
                {"signer_id": signer_id, "signed_digest": signed_digest},
            )
        if signer_id in verified_signers:
            return GuardEvaluation(
                False,
                "AP2_TREASURY_DUPLICATE_COSIGNER_BLOCKED",
                "mandates_tokenization",
                {"signer_id": signer_id},
            )
        verified_signers.add(signer_id)
    if len(verified_signers) < required_threshold_m:
        return GuardEvaluation(
            False,
            "AP2_TREASURY_QUORUM_NOT_MET",
            "mandates_tokenization",
            {
                "verified_signers_count": len(verified_signers),
                "required_threshold_m": required_threshold_m,
            },
        )
    return GuardEvaluation(
        True,
        "AP2_TREASURY_COSIGNER_QUORUM_VERIFIED",
        "mandates_tokenization",
        {
            "verified_signers_count": len(verified_signers),
            "required_threshold_m": required_threshold_m,
        },
    )


# ---------------------------------------------------------------------------
# 5. MCP, Stripe AI, Visa TAP & Sierra tau2-bench Guards (AR-12 .. AR-16)
# ---------------------------------------------------------------------------


def verify_mcp_sampling_create_message_guard(
    *,
    human_sampled_approval: bool,
    max_tokens: int,
    include_context: str,
    sampling_depth: int,
    system_prompt: str,
    max_allowed_tokens: int = 4096,
) -> GuardEvaluation:
    """AR-12 (MCP #3335/#3328/#3321/#3314): MCP `sampling/createMessage` HITL & context isolation guard."""
    if not human_sampled_approval:
        return GuardEvaluation(
            False,
            "MCP_SAMPLING_HUMAN_APPROVAL_REQUIRED",
            "fiduciary_policy",
            {"human_sampled_approval": human_sampled_approval},
        )
    if include_context == "allServers":
        return GuardEvaluation(
            False,
            "MCP_SAMPLING_ALL_SERVERS_CONTEXT_EXFIL_BLOCKED",
            "fiduciary_policy",
            {"include_context": include_context},
        )
    if sampling_depth > 1 or sampling_depth < 1:
        return GuardEvaluation(
            False,
            "MCP_SAMPLING_RECURSIVE_DEPTH_EXCEEDED",
            "fiduciary_policy",
            {"sampling_depth": sampling_depth},
        )
    if max_tokens <= 0 or max_tokens > max_allowed_tokens:
        return GuardEvaluation(
            False,
            "MCP_SAMPLING_TOKEN_CEILING_EXCEEDED",
            "fiduciary_policy",
            {"max_tokens": max_tokens, "max_allowed_tokens": max_allowed_tokens},
        )
    lowered = system_prompt.lower()
    if "ignore previous" in lowered or "exfiltrate" in lowered:
        return GuardEvaluation(
            False,
            "MCP_SAMPLING_SYSTEM_PROMPT_HIJACK_BLOCKED",
            "fiduciary_policy",
            {"system_prompt_length": len(system_prompt)},
        )
    return GuardEvaluation(
        True,
        "MCP_SAMPLING_CREATE_MESSAGE_VERIFIED",
        "fiduciary_policy",
        {"max_tokens": max_tokens, "include_context": include_context},
    )


def verify_stripe_ai_portal_session_scope_guard(
    *,
    customer_id: str,
    bound_principal_customer_id: str,
    has_active_subscription: bool,
    allow_payment_method_removal_without_replacement: bool,
    requested_Switch_price_ids: Sequence[str],
    catalog_allowed_price_ids: Sequence[str],
) -> GuardEvaluation:
    """AR-13 (Stripe AI #468/#462/#455/#448): Stripe Customer Portal configuration scope guard."""
    if not customer_id.strip() or customer_id != bound_principal_customer_id:
        return GuardEvaluation(
            False,
            "STRIPE_PORTAL_CUSTOMER_PRINCIPAL_MISMATCH",
            "mandates_tokenization",
            {
                "customer_id": customer_id,
                "bound_principal_customer_id": bound_principal_customer_id,
            },
        )
    if has_active_subscription and allow_payment_method_removal_without_replacement:
        return GuardEvaluation(
            False,
            "STRIPE_PORTAL_UNSAFE_PM_REMOVAL_ON_ACTIVE_SUB_BLOCKED",
            "mandates_tokenization",
            {"has_active_subscription": has_active_subscription},
        )
    allowed_set = set(catalog_allowed_price_ids)
    disallowed = [p for p in requested_Switch_price_ids if p not in allowed_set]
    if disallowed:
        return GuardEvaluation(
            False,
            "STRIPE_PORTAL_UNLISTED_PRICE_SWITCH_BLOCKED",
            "mandates_tokenization",
            {"disallowed_price_ids": disallowed},
        )
    return GuardEvaluation(
        True,
        "STRIPE_PORTAL_SESSION_SCOPE_VERIFIED",
        "mandates_tokenization",
        {"customer_id": customer_id, "allowed_prices_count": len(requested_Switch_price_ids)},
    )


def verify_visa_tap_mit_standing_instruction_guard(
    *,
    is_merchant_initiated: bool,
    initial_cit_transaction_id: str,
    standing_instruction_agreement_digest: str,
    mit_amount_minor: int,
    agreement_max_variable_amount_minor: int,
    mit_interval_days: int,
    agreement_min_interval_days: int,
) -> GuardEvaluation:
    """AR-14 (Visa TAP #19/#16/#12/#6): Visa TAP MIT standing-instruction CIT trace binding."""
    if not is_merchant_initiated:
        return GuardEvaluation(
            True,
            "VISA_TAP_CIT_FLOW_APPLICABLE",
            "edge_identity",
            {"is_merchant_initiated": False},
        )
    if not initial_cit_transaction_id.strip():
        return GuardEvaluation(
            False,
            "VISA_TAP_MIT_INITIAL_CIT_TRACE_MISSING",
            "edge_identity",
            {"initial_cit_transaction_id": initial_cit_transaction_id},
        )
    if len(standing_instruction_agreement_digest.strip()) != 64:
        return GuardEvaluation(
            False,
            "VISA_TAP_MIT_AGREEMENT_DIGEST_INVALID",
            "edge_identity",
            {"standing_instruction_agreement_digest": standing_instruction_agreement_digest},
        )
    if mit_amount_minor <= 0 or mit_amount_minor > agreement_max_variable_amount_minor:
        return GuardEvaluation(
            False,
            "VISA_TAP_MIT_AMOUNT_EXCEEDS_AGREEMENT_CAP",
            "edge_identity",
            {
                "mit_amount_minor": mit_amount_minor,
                "agreement_max_variable_amount_minor": agreement_max_variable_amount_minor,
            },
        )
    if mit_interval_days < agreement_min_interval_days:
        return GuardEvaluation(
            False,
            "VISA_TAP_MIT_INTERVAL_TOO_FREQUENT",
            "edge_identity",
            {
                "mit_interval_days": mit_interval_days,
                "agreement_min_interval_days": agreement_min_interval_days,
            },
        )
    return GuardEvaluation(
        True,
        "VISA_TAP_MIT_STANDING_INSTRUCTION_VERIFIED",
        "edge_identity",
        {
            "initial_cit_transaction_id": initial_cit_transaction_id,
            "mit_amount_minor": mit_amount_minor,
        },
    )


def verify_tau2_utility_meter_billing_dispute_guard(
    *,
    smart_meter_telemetry_verified: bool,
    billed_usage_kwh: int,
    verified_meter_reading_kwh: int,
    tariff_minor_per_kwh: int,
    requested_credit_minor: int,
) -> GuardEvaluation:
    """AR-15 (Sierra tau2-bench #561/#556/#551/#546): Utility billing dispute meter-read conservation."""
    if not smart_meter_telemetry_verified:
        return GuardEvaluation(
            False,
            "TAU2_UTILITY_METER_TELEMETRY_UNVERIFIED",
            "fiduciary_policy",
            {"smart_meter_telemetry_verified": smart_meter_telemetry_verified},
        )
    if billed_usage_kwh <= verified_meter_reading_kwh:
        return GuardEvaluation(
            False,
            "TAU2_UTILITY_NO_OVERCHARGE_DETECTED",
            "fiduciary_policy",
            {
                "billed_usage_kwh": billed_usage_kwh,
                "verified_meter_reading_kwh": verified_meter_reading_kwh,
            },
        )
    overcharged_kwh = billed_usage_kwh - verified_meter_reading_kwh
    recalculated_overcharge_minor = overcharged_kwh * tariff_minor_per_kwh
    if requested_credit_minor <= 0 or requested_credit_minor > recalculated_overcharge_minor:
        return GuardEvaluation(
            False,
            "TAU2_UTILITY_CREDIT_EXCEEDS_OVERCHARGE",
            "fiduciary_policy",
            {
                "requested_credit_minor": requested_credit_minor,
                "recalculated_overcharge_minor": recalculated_overcharge_minor,
            },
        )
    return GuardEvaluation(
        True,
        "TAU2_UTILITY_BILLING_DISPUTE_CREDIT_VERIFIED",
        "fiduciary_policy",
        {
            "overcharged_kwh": overcharged_kwh,
            "requested_credit_minor": requested_credit_minor,
        },
    )


def verify_tau2_hazmat_coldchain_carrier_guard(
    *,
    un_hazmat_class: str,
    requires_reefer_cold_chain: bool,
    carrier_hazmat_certified: bool,
    carrier_reefer_certified: bool,
    route_tunnel_restriction_compliant: bool,
) -> GuardEvaluation:
    """AR-16 (Sierra tau2-bench #542/#538/#533/#528): HazMat & cold-chain carrier certification guard."""
    if un_hazmat_class.strip() != "":
        if not carrier_hazmat_certified:
            return GuardEvaluation(
                False,
                "TAU2_CARRIER_HAZMAT_CERTIFICATION_MISSING",
                "fiduciary_policy",
                {"un_hazmat_class": un_hazmat_class},
            )
        if not route_tunnel_restriction_compliant:
            return GuardEvaluation(
                False,
                "TAU2_HAZMAT_ROUTE_TUNNEL_RESTRICTION_VIOLATED",
                "fiduciary_policy",
                {"un_hazmat_class": un_hazmat_class},
            )
    if requires_reefer_cold_chain and not carrier_reefer_certified:
        return GuardEvaluation(
            False,
            "TAU2_CARRIER_REEFER_COLD_CHAIN_CERT_MISSING",
            "fiduciary_policy",
            {"requires_reefer_cold_chain": requires_reefer_cold_chain},
        )
    return GuardEvaluation(
        True,
        "TAU2_HAZMAT_COLDCHAIN_CARRIER_VERIFIED",
        "fiduciary_policy",
        {
            "un_hazmat_class": un_hazmat_class,
            "requires_reefer_cold_chain": requires_reefer_cold_chain,
        },
    )


def run_demo() -> dict[str, object]:
    """Run a deterministic smoke check across AR-01..AR-16."""
    h64 = "c" * 64
    webhook_secret = "whsec_x402_stage162"
    raw_body = '{"event":"settlement.confirmed","tx":"0xabc"}'
    sig = hmac.new(
        webhook_secret.encode("utf-8"),
        f"1761000000.evt_162.{raw_body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    checks = {
        "AR-01": verify_x402_algorand_asa_transfer_guard(
            network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
            tx_type="axfer",
            xfer_asset_id=31566704,
            expected_asa_id=31566704,
            asset_receiver="ALGO_MERCHANT_ADDR",
            expected_pay_to="ALGO_MERCHANT_ADDR",
            asset_amount=5_000_000,
            min_required_amount=5_000_000,
            asset_close_to="",
            asset_sender="",
            first_valid_round=42_000_000,
            last_valid_round=42_000_800,
            current_round=42_000_100,
        ).allowed,
        "AR-02": verify_x402_polkadot_assethub_keep_alive_guard(
            network="polkadot:68d56f15f85d3136970ec16946040bc1",
            pallet_call="Assets::transfer_keep_alive",
            keep_alive=True,
            asset_id=1337,
            expected_asset_id=1337,
            beneficiary="15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5",
            expected_pay_to="15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5",
            amount=5_000_000,
            min_required_amount=5_000_000,
            is_mortal_era=True,
            era_period_blocks=64,
            signed_genesis_hash="0x68d56f15f85d3136970ec16946040bc1",
            expected_genesis_hash="0x68d56f15f85d3136970ec16946040bc1",
        ).allowed,
        "AR-03": verify_x402_facilitator_webhook_hmac_guard(
            webhook_secret=webhook_secret,
            timestamp_epoch=1761000000,
            current_epoch=1761000040,
            event_id="evt_162",
            raw_body=raw_body,
            provided_signature_hex=sig,
            seen_event_ids=["evt_161"],
        ).allowed,
        "AR-04": verify_x402_client_session_budget_guard(
            origin="https://api.merchant.example",
            requested_payment_atomic=500_000,
            cumulative_origin_spent_atomic=1_000_000,
            cumulative_session_spent_atomic=2_500_000,
            max_payment_per_request_atomic=1_000_000,
            max_payment_per_origin_atomic=2_000_000,
            max_payment_per_session_atomic=5_000_000,
        ).allowed,
        "AR-05": verify_ucp_bopis_curbside_pickup_guard(
            pickup_store_id="store_nyc_01",
            active_store_ids=["store_nyc_01", "store_sfo_02"],
            pickup_window_start_epoch=1761000000,
            pickup_window_end_epoch=1761086400,
            authorized_pickup_person_sha256=h64,
            order_fulfillment_state="ready_for_pickup",
            emit_pickup_release_pin=True,
        ).allowed,
        "AR-06": verify_ucp_dcc_multi_currency_parity_guard(
            display_currency="EUR",
            settlement_currency="USD",
            fx_rate_quote_id="fxq_162",
            dcc_applied=True,
            dcc_markup_bps=150,
            buyer_dcc_opt_in=True,
        ).allowed,
        "AR-07": verify_ucp_trade_in_credit_mandate_guard(
            instant_trade_in_credit_applied=True,
            trade_in_serial_sha256=h64,
            provisional_credit_minor=35000,
            max_trade_in_credit_minor=50000,
            new_item_price_minor=99900,
            clawback_authorization_mandate_id="mandate_tradein_clawback_01",
            inspection_deadline_days=14,
        ).allowed,
        "AR-08": verify_acp_chargeback_representment_guard(
            dispute_id="dp_162",
            order_receipt_sha256=h64,
            delivery_proof_sha256=h64,
            user_approval_jws="eyJhbGciOiJFZERTQSJ9.eyJhcHByb3ZhbCI6dHJ1ZX0.c2ln",
            evidence_submitted_epoch=1761000000,
            dispute_due_by_epoch=1761600000,
            disputed_amount_minor=12500,
            receipt_total_minor=12500,
        ).allowed,
        "AR-09": verify_acp_b2b_tax_exemption_certificate_guard(
            tax_exempt_claimed=True,
            tax_minor=0,
            tax_exemption_certificate_id="txcert_ny_9981",
            certificate_jurisdiction="US-NY",
            shipping_jurisdiction="US-NY",
            certificate_expires_epoch=1790000000,
            current_epoch=1761000000,
            verified_by_tax_engine=True,
        ).allowed,
        "AR-10": verify_ap2_hardware_device_attestation_guard(
            amount_minor=150000,
            high_value_threshold_minor=100000,
            device_attestation_verdict="MEETS_STRONG_INTEGRITY",
            attested_public_key_thumbprint="jkt_hw_se_01",
            mandate_cnf_jkt="jkt_hw_se_01",
            attestation_issued_epoch=1761000000,
            current_epoch=1761000090,
        ).allowed,
        "AR-11": verify_ap2_treasury_cosigner_threshold_guard(
            mandate_digest_sha256=h64,
            required_threshold_m=2,
            authorized_treasury_signers=["cfo_key", "controller_key", "vp_fin_key"],
            cosigner_entries=[
                {"signer_id": "cfo_key", "signed_digest_sha256": h64, "signature_valid": True},
                {"signer_id": "controller_key", "signed_digest_sha256": h64, "signature_valid": True},
            ],
        ).allowed,
        "AR-12": verify_mcp_sampling_create_message_guard(
            human_sampled_approval=True,
            max_tokens=1024,
            include_context="thisServer",
            sampling_depth=1,
            system_prompt="Summarize the product warranty terms accurately.",
        ).allowed,
        "AR-13": verify_stripe_ai_portal_session_scope_guard(
            customer_id="cus_principal_01",
            bound_principal_customer_id="cus_principal_01",
            has_active_subscription=True,
            allow_payment_method_removal_without_replacement=False,
            requested_Switch_price_ids=["price_pro_monthly", "price_pro_annual"],
            catalog_allowed_price_ids=["price_pro_monthly", "price_pro_annual", "price_team"],
        ).allowed,
        "AR-14": verify_visa_tap_mit_standing_instruction_guard(
            is_merchant_initiated=True,
            initial_cit_transaction_id="cit_visa_99182",
            standing_instruction_agreement_digest=h64,
            mit_amount_minor=4900,
            agreement_max_variable_amount_minor=6000,
            mit_interval_days=30,
            agreement_min_interval_days=28,
        ).allowed,
        "AR-15": verify_tau2_utility_meter_billing_dispute_guard(
            smart_meter_telemetry_verified=True,
            billed_usage_kwh=850,
            verified_meter_reading_kwh=600,
            tariff_minor_per_kwh=20,
            requested_credit_minor=5000,
        ).allowed,
        "AR-16": verify_tau2_hazmat_coldchain_carrier_guard(
            un_hazmat_class="UN3480",
            requires_reefer_cold_chain=True,
            carrier_hazmat_certified=True,
            carrier_reefer_certified=True,
            route_tunnel_restriction_compliant=True,
        ).allowed,
    }
    return {"stage": "stage162", "all_passed": all(checks.values()), "checks": checks}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
