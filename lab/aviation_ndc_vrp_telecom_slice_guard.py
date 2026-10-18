"""Stage 32: IATA NDC Interline Baggage/IRROPS Settlement, PSD2/Open-Banking Variable Recurring Payment (VRP) Sweeping Guard & Telecom 5G Network-Slice SLA Escrow.

Implements deterministic AI-Native settlement guardrails for:
1. Aviation IATA NDC / ONE Order Interline Baggage & Irregular Operations (IRROPS) EU261 / DOT
   statutory compensation and inter-carrier settlement (`evaluate_iata_ndc_irrops_interline_escrow`).
2. UK OBIE / EU PSD3 Open-Banking Variable Recurring Payment (VRP) commercial vs sweeping guard,
   per-transaction and monthly cumulative ceiling enforcement (`evaluate_open_banking_vrp_sweeping_guard`).
3. Telecom 3GPP 5G Network-Slice uRLLC / eMBB SLA packet-loss and jitter telemetry escrow
   (`evaluate_telecom_5g_network_slice_sla_escrow`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IATANDCIrropsEscrowResult:
    order_id: str
    admitted: bool
    decision_code: str
    gross_ticket_fare_minor: int
    operating_carrier_fault_share_minor: int
    marketing_carrier_share_minor: int
    eu261_or_dot_statutory_compensation_minor: int
    passenger_total_refund_and_comp_minor: int
    conservation_delta_minor: int


@dataclass(frozen=True)
class OpenBankingVRPGuardResult:
    vrp_mandate_id: str
    admitted: bool
    decision_code: str
    transfer_amount_minor: int
    projected_monthly_cumulative_minor: int
    max_monthly_cumulative_minor: int
    sweeping_same_beneficial_owner_verified: bool


@dataclass(frozen=True)
class Telecom5GSliceSLAResult:
    slice_id: str
    admitted: bool
    decision_code: str
    contract_slice_fee_minor: int
    observed_latency_p99_ms: float
    observed_packet_loss_bps: int
    sla_penalty_rebate_minor: int
    operator_net_settlement_minor: int
    conservation_delta_minor: int


def evaluate_iata_ndc_irrops_interline_escrow(
    *,
    order_id: str,
    gross_ticket_fare_minor: int,
    arrival_delay_minutes: int,
    flight_distance_km: int,
    extraordinary_weather_or_atc_strike: bool,
    flight_cancelled_unrebooked: bool,
    operating_carrier_prorate_bps: int,
) -> IATANDCIrropsEscrowResult:
    """Settle IATA ONE Order interline prorate splits and EU261/DOT statutory IRROPS passenger compensation."""
    if not (0 <= operating_carrier_prorate_bps <= 10000):
        raise ValueError("operating_carrier_prorate_bps must be in [0, 10000]")

    if flight_cancelled_unrebooked:
        ticket_refund_minor = gross_ticket_fare_minor
        operating_share = 0
        marketing_share = 0
    else:
        ticket_refund_minor = 0
        operating_share = (gross_ticket_fare_minor * operating_carrier_prorate_bps) // 10000
        marketing_share = gross_ticket_fare_minor - operating_share

    if arrival_delay_minutes >= 180 and not extraordinary_weather_or_atc_strike:
        if flight_distance_km <= 1500:
            statutory_comp_minor = 250_00
        elif flight_distance_km <= 3500:
            statutory_comp_minor = 400_00
        else:
            statutory_comp_minor = 600_00
    else:
        statutory_comp_minor = 0

    passenger_total_minor = ticket_refund_minor + statutory_comp_minor
    conservation_delta = gross_ticket_fare_minor - (
        ticket_refund_minor + operating_share + marketing_share
    )

    if flight_cancelled_unrebooked or statutory_comp_minor > 0:
        decision_code = "IATA_IRROPS_STATUTORY_COMPENSATION_OR_REFUND_TRIGGERED"
    elif extraordinary_weather_or_atc_strike and arrival_delay_minutes >= 180:
        decision_code = "IRROPS_EXTRAORDINARY_CIRCUMSTANCE_COMPENSATION_EXEMPT"
    else:
        decision_code = "IATA_ONE_ORDER_INTERLINE_PRORATE_SETTLED"

    return IATANDCIrropsEscrowResult(
        order_id=order_id,
        admitted=True,
        decision_code=decision_code,
        gross_ticket_fare_minor=gross_ticket_fare_minor,
        operating_carrier_fault_share_minor=operating_share,
        marketing_carrier_share_minor=marketing_share,
        eu261_or_dot_statutory_compensation_minor=statutory_comp_minor,
        passenger_total_refund_and_comp_minor=passenger_total_minor,
        conservation_delta_minor=conservation_delta,
    )


def evaluate_open_banking_vrp_sweeping_guard(
    *,
    vrp_mandate_id: str,
    vrp_category: str,  # "SWEEPING" or "COMMERCIAL"
    debtor_beneficial_owner_id: str,
    creditor_beneficial_owner_id: str,
    transfer_amount_minor: int,
    max_single_payment_minor: int,
    current_month_cumulative_minor: int,
    max_monthly_cumulative_minor: int,
    psu_sca_bound_device_signature_valid: bool,
) -> OpenBankingVRPGuardResult:
    """Enforce UK OBIE / EU PSD3 Variable Recurring Payment (VRP) sweeping ownership rules and periodic caps."""
    same_owner = debtor_beneficial_owner_id == creditor_beneficial_owner_id
    projected_monthly = current_month_cumulative_minor + transfer_amount_minor

    if not psu_sca_bound_device_signature_valid:
        return OpenBankingVRPGuardResult(
            vrp_mandate_id=vrp_mandate_id,
            admitted=False,
            decision_code="VRP_SCA_CONSENT_BINDING_SIGNATURE_INVALID_BLOCKED",
            transfer_amount_minor=transfer_amount_minor,
            projected_monthly_cumulative_minor=projected_monthly,
            max_monthly_cumulative_minor=max_monthly_cumulative_minor,
            sweeping_same_beneficial_owner_verified=same_owner,
        )

    if vrp_category == "SWEEPING" and not same_owner:
        return OpenBankingVRPGuardResult(
            vrp_mandate_id=vrp_mandate_id,
            admitted=False,
            decision_code="VRP_SWEEPING_THIRD_PARTY_MERCHANT_BYPASS_BLOCKED",
            transfer_amount_minor=transfer_amount_minor,
            projected_monthly_cumulative_minor=projected_monthly,
            max_monthly_cumulative_minor=max_monthly_cumulative_minor,
            sweeping_same_beneficial_owner_verified=False,
        )

    if (
        transfer_amount_minor > max_single_payment_minor
        or projected_monthly > max_monthly_cumulative_minor
    ):
        return OpenBankingVRPGuardResult(
            vrp_mandate_id=vrp_mandate_id,
            admitted=False,
            decision_code="VRP_PERIODIC_OR_SINGLE_LIMIT_EXCEEDED_BLOCKED",
            transfer_amount_minor=transfer_amount_minor,
            projected_monthly_cumulative_minor=projected_monthly,
            max_monthly_cumulative_minor=max_monthly_cumulative_minor,
            sweeping_same_beneficial_owner_verified=same_owner,
        )

    return OpenBankingVRPGuardResult(
        vrp_mandate_id=vrp_mandate_id,
        admitted=True,
        decision_code="OPEN_BANKING_VRP_EXECUTION_SETTLED",
        transfer_amount_minor=transfer_amount_minor,
        projected_monthly_cumulative_minor=projected_monthly,
        max_monthly_cumulative_minor=max_monthly_cumulative_minor,
        sweeping_same_beneficial_owner_verified=same_owner,
    )


def evaluate_telecom_5g_network_slice_sla_escrow(
    *,
    slice_id: str,
    contract_slice_fee_minor: int,
    committed_latency_p99_ms: float,
    observed_latency_p99_ms: float,
    committed_max_packet_loss_bps: int,
    observed_packet_loss_bps: int,
    twamp_telemetry_signature_valid: bool,
) -> Telecom5GSliceSLAResult:
    """Evaluate 3GPP 5G uRLLC network-slice TWAMP telemetry and slash escrow on latency/packet-loss SLA breach."""
    if not twamp_telemetry_signature_valid:
        return Telecom5GSliceSLAResult(
            slice_id=slice_id,
            admitted=False,
            decision_code="UNSIGNED_TWAMP_5G_SLICE_TELEMETRY_BLOCKED",
            contract_slice_fee_minor=contract_slice_fee_minor,
            observed_latency_p99_ms=observed_latency_p99_ms,
            observed_packet_loss_bps=observed_packet_loss_bps,
            sla_penalty_rebate_minor=0,
            operator_net_settlement_minor=0,
            conservation_delta_minor=0,
        )

    latency_breach = observed_latency_p99_ms > committed_latency_p99_ms
    loss_breach = observed_packet_loss_bps > committed_max_packet_loss_bps

    if latency_breach and loss_breach:
        penalty_bps = 5000  # 50% rebate
    elif latency_breach or loss_breach:
        penalty_bps = 2500  # 25% rebate
    else:
        penalty_bps = 0

    rebate_minor = (contract_slice_fee_minor * penalty_bps) // 10000
    operator_net_minor = contract_slice_fee_minor - rebate_minor
    conservation_delta = contract_slice_fee_minor - (rebate_minor + operator_net_minor)

    decision_code = (
        "TELECOM_5G_URLLC_SLA_BREACH_REBATE_SLASHED"
        if penalty_bps > 0
        else "TELECOM_5G_SLICE_SLA_VERIFIED_SETTLED"
    )
    return Telecom5GSliceSLAResult(
        slice_id=slice_id,
        admitted=True,
        decision_code=decision_code,
        contract_slice_fee_minor=contract_slice_fee_minor,
        observed_latency_p99_ms=observed_latency_p99_ms,
        observed_packet_loss_bps=observed_packet_loss_bps,
        sla_penalty_rebate_minor=rebate_minor,
        operator_net_settlement_minor=operator_net_minor,
        conservation_delta_minor=conservation_delta,
    )
