r"""Stage 29: Autonomous Agricultural / Commodity Futures Weather-Index Escrow, Telecom eSIM M2M Roaming CDR Settlement & Open-Banking ISO 20022 `pain.008` SEPA/FedNow Mandate Guard.

Implements three deterministic real-world physical & banking-rail settlement invariants:
1. `evaluate_commodity_weather_index_forward_escrow`:
   - Governs autonomous agri-food and industrial commodity forward contracts settled against satellite/WMO weather-station telemetry:
     - Verifies multi-source WMO/satellite oracle quorum (`oracle_quorum_verified == True` -> blocks `UNVERIFIED_WEATHER_ORACLE_QUORUM_BLOCKED`),
     - Triggers automatic parametric drought/frost hedge compensation when cumulative Growing Degree Days (`GDD`) or precipitation deviates beyond `drought_trigger_mm` (`PARAMETRIC_WEATHER_HEDGE_PAYOUT_TRIGGERED`),
     - Releases normal forward-contract settlement when climate indices remain within normal bounds (`COMMODITY_FORWARD_NORMAL_SETTLED`).
2. `evaluate_m2m_esim_roaming_cdr_settlement`:
   - Governs GSMA SGP.32 IoT/autonomous-fleet eSIM wholesale roaming Call Detail Record (`CDR`) clearing (BCE / TAP3):
     - Blocks phantom or replayed roaming CDR batches (`CDR_BATCH_REPLAY_OR_SIGNATURE_INVALID_BLOCKED`),
     - Enforces wholesale per-MB data-rate caps (`rate_per_mb_minor <= max_wholesale_rate_per_mb_minor`) to prevent "bill-shock" roaming arbitrage (`ROAMING_WHOLESALE_RATE_CAP_BREACH_BLOCKED`),
     - Settles verified wholesale M2M roaming usage (`M2M_ESIM_ROAMING_CDR_SETTLED`).
3. `verify_open_banking_pain008_direct_debit_mandate`:
   - Enforces SEPA Direct Debit (`SDD B2B` / `CORE`) and FedNow / RTP Request-for-Payment (`RfP`) ISO 20022 `pain.008` account-to-account (`A2A`) pull guardrails:
     - Verifies active Unique Mandate Reference (`UMR`) and debtor IBAN/account binding (`PAIN008_UMR_OR_IBAN_BINDING_INVALID_BLOCKED`),
     - Blocks unauthorized SDD B2B pull attempts exceeding `max_single_debit_minor` or lacking debtor bank pre-registration (`PAIN008_B2B_PRE_REGISTRATION_OR_CAP_BLOCKED`),
     - Admits compliant ISO 20022 `pain.008` A2A settlement (`ISO20022_PAIN008_DIRECT_DEBIT_SETTLED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CommodityWeatherEscrowResult:
    """Result of evaluating a commodity forward contract with weather-index hedge."""

    settled: bool
    decision_code: str
    contract_id: str
    observed_rainfall_mm: int
    drought_trigger_mm: int
    forward_notional_minor: int
    hedge_payout_to_buyer_minor: int
    net_seller_settlement_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class M2mEsimRoamingSettlementResult:
    """Result of evaluating GSMA SGP.32 M2M eSIM wholesale roaming CDR settlement."""

    settled: bool
    decision_code: str
    cdr_batch_id: str
    billed_megabytes: int
    rate_per_mb_minor: int
    max_wholesale_rate_per_mb_minor: int
    total_settlement_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpenBankingPain008Result:
    """Result of verifying an ISO 20022 pain.008 SEPA/A2A direct debit instruction."""

    allowed: bool
    decision_code: str
    umr_id: str
    debit_amount_minor: int
    max_single_debit_minor: int
    b2b_no_refund_waiver_registered: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_commodity_weather_index_forward_escrow(
    weather_context: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate commodity forward escrow against WMO/satellite weather-index triggers."""

    contract_id = str(weather_context.get("contract_id", "cmd_unknown"))
    oracle_verified = bool(weather_context.get("oracle_quorum_verified", True))
    observed_rainfall_mm = max(0, int(weather_context.get("observed_rainfall_mm", 100)))
    drought_trigger_mm = max(0, int(weather_context.get("drought_trigger_mm", 50)))
    notional_minor = max(0, int(weather_context.get("forward_notional_minor", 0)))
    hedge_rebate_bps = max(0, min(10_000, int(weather_context.get("hedge_rebate_bps", 3_000))))

    if not oracle_verified:
        return CommodityWeatherEscrowResult(
            settled=False,
            decision_code="UNVERIFIED_WEATHER_ORACLE_QUORUM_BLOCKED",
            contract_id=contract_id,
            observed_rainfall_mm=observed_rainfall_mm,
            drought_trigger_mm=drought_trigger_mm,
            forward_notional_minor=notional_minor,
            hedge_payout_to_buyer_minor=0,
            net_seller_settlement_minor=0,
            reason_codes=["UNVERIFIED_WEATHER_ORACLE_QUORUM_BLOCKED"],
        ).to_dict()

    if observed_rainfall_mm < drought_trigger_mm:
        payout = (notional_minor * hedge_rebate_bps) // 10_000
        return CommodityWeatherEscrowResult(
            settled=True,
            decision_code="PARAMETRIC_WEATHER_HEDGE_PAYOUT_TRIGGERED",
            contract_id=contract_id,
            observed_rainfall_mm=observed_rainfall_mm,
            drought_trigger_mm=drought_trigger_mm,
            forward_notional_minor=notional_minor,
            hedge_payout_to_buyer_minor=payout,
            net_seller_settlement_minor=max(0, notional_minor - payout),
            reason_codes=["PARAMETRIC_WEATHER_HEDGE_PAYOUT_TRIGGERED"],
        ).to_dict()

    return CommodityWeatherEscrowResult(
        settled=True,
        decision_code="COMMODITY_FORWARD_NORMAL_SETTLED",
        contract_id=contract_id,
        observed_rainfall_mm=observed_rainfall_mm,
        drought_trigger_mm=drought_trigger_mm,
        forward_notional_minor=notional_minor,
        hedge_payout_to_buyer_minor=0,
        net_seller_settlement_minor=notional_minor,
        reason_codes=["COMMODITY_FORWARD_NORMAL_SETTLED"],
    ).to_dict()


def evaluate_m2m_esim_roaming_cdr_settlement(
    cdr_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify GSMA SGP.32 IoT/M2M eSIM wholesale roaming CDR batch signatures and rate caps."""

    batch_id = str(cdr_context.get("cdr_batch_id", "cdr_unknown"))
    signature_valid = bool(cdr_context.get("visited_network_signature_valid", True))
    replay_detected = bool(cdr_context.get("batch_replay_detected", False))
    billed_mb = max(0, int(cdr_context.get("billed_megabytes", 0)))
    rate_per_mb = max(0, int(cdr_context.get("rate_per_mb_minor", 0)))
    max_rate_per_mb = max(0, int(cdr_context.get("max_wholesale_rate_per_mb_minor", 50)))

    if not signature_valid or replay_detected:
        return M2mEsimRoamingSettlementResult(
            settled=False,
            decision_code="CDR_BATCH_REPLAY_OR_SIGNATURE_INVALID_BLOCKED",
            cdr_batch_id=batch_id,
            billed_megabytes=billed_mb,
            rate_per_mb_minor=rate_per_mb,
            max_wholesale_rate_per_mb_minor=max_rate_per_mb,
            total_settlement_minor=0,
            reason_codes=["CDR_BATCH_REPLAY_OR_SIGNATURE_INVALID_BLOCKED"],
        ).to_dict()

    if rate_per_mb > max_rate_per_mb:
        return M2mEsimRoamingSettlementResult(
            settled=False,
            decision_code="ROAMING_WHOLESALE_RATE_CAP_BREACH_BLOCKED",
            cdr_batch_id=batch_id,
            billed_megabytes=billed_mb,
            rate_per_mb_minor=rate_per_mb,
            max_wholesale_rate_per_mb_minor=max_rate_per_mb,
            total_settlement_minor=0,
            reason_codes=["ROAMING_WHOLESALE_RATE_CAP_BREACH_BLOCKED"],
        ).to_dict()

    total_minor = billed_mb * rate_per_mb
    return M2mEsimRoamingSettlementResult(
        settled=True,
        decision_code="M2M_ESIM_ROAMING_CDR_SETTLED",
        cdr_batch_id=batch_id,
        billed_megabytes=billed_mb,
        rate_per_mb_minor=rate_per_mb,
        max_wholesale_rate_per_mb_minor=max_rate_per_mb,
        total_settlement_minor=total_minor,
        reason_codes=["M2M_ESIM_ROAMING_CDR_SETTLED"],
    ).to_dict()


def verify_open_banking_pain008_direct_debit_mandate(
    pain008_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify ISO 20022 pain.008 SEPA B2B / A2A direct debit mandate registration and caps."""

    umr_id = str(pain008_context.get("umr_id", "UMR-UNKNOWN"))
    umr_signature_valid = bool(pain008_context.get("umr_signature_valid", True))
    iban_binding_matches = bool(pain008_context.get("debtor_iban_binding_matches", True))
    b2b_pre_registered = bool(pain008_context.get("debtor_bank_b2b_mandate_registered", True))
    debit_minor = max(0, int(pain008_context.get("debit_amount_minor", 0)))
    max_debit_minor = max(0, int(pain008_context.get("max_single_debit_minor", 1_000_000)))

    if not umr_signature_valid or not iban_binding_matches:
        return OpenBankingPain008Result(
            allowed=False,
            decision_code="PAIN008_UMR_OR_IBAN_BINDING_INVALID_BLOCKED",
            umr_id=umr_id,
            debit_amount_minor=debit_minor,
            max_single_debit_minor=max_debit_minor,
            b2b_no_refund_waiver_registered=b2b_pre_registered,
            reason_codes=["PAIN008_UMR_OR_IBAN_BINDING_INVALID_BLOCKED"],
        ).to_dict()

    if not b2b_pre_registered or debit_minor > max_debit_minor:
        return OpenBankingPain008Result(
            allowed=False,
            decision_code="PAIN008_B2B_PRE_REGISTRATION_OR_CAP_BLOCKED",
            umr_id=umr_id,
            debit_amount_minor=debit_minor,
            max_single_debit_minor=max_debit_minor,
            b2b_no_refund_waiver_registered=b2b_pre_registered,
            reason_codes=["PAIN008_B2B_PRE_REGISTRATION_OR_CAP_BLOCKED"],
        ).to_dict()

    return OpenBankingPain008Result(
        allowed=True,
        decision_code="ISO20022_PAIN008_DIRECT_DEBIT_SETTLED",
        umr_id=umr_id,
        debit_amount_minor=debit_minor,
        max_single_debit_minor=max_debit_minor,
        b2b_no_refund_waiver_registered=True,
        reason_codes=["ISO20022_PAIN008_DIRECT_DEBIT_SETTLED"],
    ).to_dict()
