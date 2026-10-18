"""Multi-leg booking two-phase hold Saga (`Stripe Booking` x UCP Reservation) and
Enterprise Three-Way End-of-Day SFTP / MPP Tempo / Metronome Token Ledger Reconciliation Guard.

Pure standard library, zero network calls, zero secrets.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Any


# ---------------------------------------------------------------------------
# 1. Multi-Leg Booking Two-Phase Hold Saga (`HOLD_ALL -> VERIFY -> ATOMIC_CAPTURE_OR_REVERSE`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookingLegHold:
    leg_id: str  # e.g., "flight_gds", "hotel_pms", "gpu_cluster"
    provider_type: str
    amount_minor: int
    capture_method: str  # must be "manual" during HOLD phase
    hold_status: str  # "held" | "failed" | "expired"
    hold_expires_at: int
    terms_refundable_until: int  # epoch until which cancellation is penalty-free (0 if non-refundable)
    summary_claims_free_cancel: bool


@dataclass(frozen=True)
class MultiLegBookingSagaResult:
    saga_outcome: str  # "ATOMIC_CAPTURE_COMMITTED" | "ATOMIC_REVERSE_ABORTED"
    commit_allowed: bool
    reason: str
    effective_saga_deadline_epoch: int
    total_captured_minor: int
    legs_to_cancel_payment_intent: tuple[str, ...]
    orphan_exposure_minor_prevented: int


def verify_multi_leg_booking_saga(
    *,
    legs: list[BookingLegHold],
    commit_attempt_epoch: int,
    safety_buffer_seconds: int = 15,
    buyer_accepts_non_refundable: bool = False,
) -> MultiLegBookingSagaResult:
    """Verify a multi-provider itinerary/reservation Saga before capturing any leg.

    Prevents the classic "orphan leg" failure where an agent immediately captures a
    non-refundable flight (`automatic` capture) and subsequently fails to lock the hotel
    or GPU reservation whose hold TTL expired.
    """
    if not legs:
        return MultiLegBookingSagaResult(
            "ATOMIC_REVERSE_ABORTED",
            False,
            "empty_booking_legs",
            0,
            0,
            (),
            0,
        )

    all_leg_ids = tuple(leg.leg_id for leg in legs)
    total_amount = sum(leg.amount_minor for leg in legs)
    min_expiry = min(leg.hold_expires_at for leg in legs)
    effective_deadline = min_expiry - safety_buffer_seconds

    # Invariant 1: Every leg MUST use manual capture (auth-hold) prior to barrier commit
    for leg in legs:
        if leg.amount_minor <= 0:
            return MultiLegBookingSagaResult(
                "ATOMIC_REVERSE_ABORTED",
                False,
                f"invalid_leg_amount:{leg.leg_id}",
                effective_deadline,
                0,
                all_leg_ids,
                total_amount,
            )
        if leg.capture_method != "manual":
            return MultiLegBookingSagaResult(
                "ATOMIC_REVERSE_ABORTED",
                False,
                f"premature_automatic_capture_forbidden:{leg.leg_id}",
                effective_deadline,
                0,
                all_leg_ids,
                total_amount,
            )
        if leg.hold_status != "held":
            return MultiLegBookingSagaResult(
                "ATOMIC_REVERSE_ABORTED",
                False,
                f"leg_not_in_held_state:{leg.leg_id}:{leg.hold_status}",
                effective_deadline,
                0,
                all_leg_ids,
                total_amount,
            )

    # Invariant 2: Commit must occur before min(hold_expires_at) - safety_buffer_seconds
    if commit_attempt_epoch > effective_deadline:
        return MultiLegBookingSagaResult(
            "ATOMIC_REVERSE_ABORTED",
            False,
            "saga_hold_ttl_expired_or_within_safety_buffer",
            effective_deadline,
            0,
            all_leg_ids,
            total_amount,
        )

    # Invariant 3: Summary vs Terms cancellation window & non-refundable policy gate
    for leg in legs:
        is_currently_non_refundable = leg.terms_refundable_until <= commit_attempt_epoch
        if leg.summary_claims_free_cancel and is_currently_non_refundable:
            return MultiLegBookingSagaResult(
                "ATOMIC_REVERSE_ABORTED",
                False,
                f"summary_claims_free_cancel_but_terms_non_refundable:{leg.leg_id}",
                effective_deadline,
                0,
                all_leg_ids,
                total_amount,
            )
        if is_currently_non_refundable and not buyer_accepts_non_refundable:
            return MultiLegBookingSagaResult(
                "ATOMIC_REVERSE_ABORTED",
                False,
                f"non_refundable_leg_requires_explicit_buyer_opt_in:{leg.leg_id}",
                effective_deadline,
                0,
                all_leg_ids,
                total_amount,
            )

    return MultiLegBookingSagaResult(
        "ATOMIC_CAPTURE_COMMITTED",
        True,
        "ok",
        effective_deadline,
        total_amount,
        (),
        0,
    )


# ---------------------------------------------------------------------------
# 2. Three-Way End-of-Day Reconciliation (Stripe SFTP Batch x MPP Tempo x Metronome Token Ledger)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SftpPayoutBatchRow:
    event_id: str
    tx_id: str
    gross_minor: int
    fee_minor: int
    net_minor: int
    settled_at_utc_hour: int  # 0..23 on day D, or >=24 if settled after 00:00 UTC cutoff (in-flight)
    is_connect_refund_without_reversal: bool = False
    unreversed_transfer_deficit_minor: int = 0


@dataclass(frozen=True)
class ThreeWayReconciliationResult:
    reconciled: bool
    reason: str
    deduplicated_event_count: int
    duplicate_webhook_ids_dropped: tuple[str, ...]
    in_flight_after_cutoff_minor: int
    mpp_subcent_forfeited_usd: str
    connect_unreversed_refund_deficit_minor: int
    expected_bank_payout_minor: int
    reported_bank_payout_minor: int
    unexplained_variance_minor: int


def reconcile_sftp_tempo_token_ledger(
    *,
    sftp_rows: list[SftpPayoutBatchRow],
    mpp_gross_micro_usdc: int,  # 1 USD = 1_000_000 micro-USDC
    mpp_settled_cents_minor: int,
    token_billed_minor: int,
    token_collected_minor: int,
    reported_bank_payout_minor: int,
) -> ThreeWayReconciliationResult:
    """Reconcile end-of-day Stripe SFTP payout feeds against MPP Tempo sub-cent forfeiture,
    Connect reverse-transfer deficits, duplicate webhook deliveries, and 00:00 UTC cutoff in-flight items.
    """
    seen_events: set[str] = set()
    duplicates: list[str] = []
    day_d_net_minor = 0
    in_flight_net_minor = 0
    connect_deficit_minor = 0

    for row in sftp_rows:
        if row.event_id in seen_events:
            duplicates.append(row.event_id)
            continue
        seen_events.add(row.event_id)

        if row.gross_minor - row.fee_minor != row.net_minor:
            return ThreeWayReconciliationResult(
                False,
                f"sftp_row_gross_minus_fee_mismatch:{row.tx_id}",
                len(seen_events),
                tuple(duplicates),
                0,
                "0.000000",
                0,
                0,
                reported_bank_payout_minor,
                reported_bank_payout_minor,
            )

        if row.is_connect_refund_without_reversal:
            connect_deficit_minor += row.unreversed_transfer_deficit_minor

        if row.settled_at_utc_hour >= 24:
            # Settled after 00:00 UTC cutoff -> belongs to D+1 payout batch
            in_flight_net_minor += row.net_minor
        else:
            day_d_net_minor += row.net_minor

    # MPP Tempo sub-cent forfeiture check:
    # mpp_settled_cents_minor * 10_000 micro-USDC <= mpp_gross_micro_usdc
    settled_micro = mpp_settled_cents_minor * 10_000
    if settled_micro > mpp_gross_micro_usdc:
        return ThreeWayReconciliationResult(
            False,
            "mpp_settled_exceeds_gross_micro_usdc",
            len(seen_events),
            tuple(duplicates),
            in_flight_net_minor,
            "0.000000",
            connect_deficit_minor,
            0,
            reported_bank_payout_minor,
            0,
        )
    forfeited_micro = mpp_gross_micro_usdc - settled_micro
    forfeited_usd_str = f"{Decimal(forfeited_micro) / Decimal(1_000_000):.6f}"

    if token_collected_minor != token_billed_minor:
        return ThreeWayReconciliationResult(
            False,
            "metronome_token_billing_collection_mismatch",
            len(seen_events),
            tuple(duplicates),
            in_flight_net_minor,
            forfeited_usd_str,
            connect_deficit_minor,
            0,
            reported_bank_payout_minor,
            token_billed_minor - token_collected_minor,
        )

    if connect_deficit_minor > 0:
        return ThreeWayReconciliationResult(
            False,
            "connect_unreversed_refund_deficit_detected",
            len(seen_events),
            tuple(duplicates),
            in_flight_net_minor,
            forfeited_usd_str,
            connect_deficit_minor,
            day_d_net_minor + mpp_settled_cents_minor + token_collected_minor - connect_deficit_minor,
            reported_bank_payout_minor,
            connect_deficit_minor,
        )

    expected_payout = day_d_net_minor + mpp_settled_cents_minor + token_collected_minor
    variance = reported_bank_payout_minor - expected_payout
    if variance != 0:
        return ThreeWayReconciliationResult(
            False,
            "unexplained_eod_payout_variance",
            len(seen_events),
            tuple(duplicates),
            in_flight_net_minor,
            forfeited_usd_str,
            connect_deficit_minor,
            expected_payout,
            reported_bank_payout_minor,
            variance,
        )

    return ThreeWayReconciliationResult(
        True,
        "ok",
        len(seen_events),
        tuple(duplicates),
        in_flight_net_minor,
        forfeited_usd_str,
        0,
        expected_payout,
        reported_bank_payout_minor,
        0,
    )


def run_demo() -> dict[str, Any]:
    # 1. Valid 3-leg booking saga
    valid_saga = verify_multi_leg_booking_saga(
        legs=[
            BookingLegHold("flight_gds", "airline", 45000, "manual", "held", 1180, 3600, True),
            BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
            BookingLegHold("gpu_reserve", "compute", 15000, "manual", "held", 1240, 3600, True),
        ],
        commit_attempt_epoch=1150,
    )
    # 2. Expired leg triggers atomic reversal of all holds
    expired_saga = verify_multi_leg_booking_saga(
        legs=[
            BookingLegHold("flight_gds", "airline", 45000, "manual", "held", 1180, 3600, True),
            BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
        ],
        commit_attempt_epoch=1175,  # within 15s safety buffer of 1180
    )
    # 3. Clean 3-way SFTP + MPP Tempo + Token reconciliation with deduplicated webhook & D+1 in-flight
    recon = reconcile_sftp_tempo_token_ledger(
        sftp_rows=[
            SftpPayoutBatchRow("evt_1", "tx_1", 10000, 320, 9680, 14),
            SftpPayoutBatchRow("evt_1", "tx_1", 10000, 320, 9680, 14),  # duplicate webhook
            SftpPayoutBatchRow("evt_2", "tx_2", 20000, 610, 19390, 22),
            SftpPayoutBatchRow("evt_3", "tx_3", 15000, 465, 14535, 25),  # in-flight after 00:00 UTC
        ],
        mpp_gross_micro_usdc=43750,  # $0.043750
        mpp_settled_cents_minor=2,   # $0.02 settled, $0.023750 forfeited
        token_billed_minor=1250,
        token_collected_minor=1250,
        reported_bank_payout_minor=9680 + 19390 + 2 + 1250,
    )
    return {
        "stage": "stage6-booking-sftp-reconciliation-guard",
        "valid_saga_committed": valid_saga.commit_allowed,
        "expired_saga_reversed": not expired_saga.commit_allowed
        and expired_saga.orphan_exposure_minor_prevented == 77000,
        "three_way_reconciled": recon.reconciled,
        "duplicate_webhooks_dropped": len(recon.duplicate_webhook_ids_dropped),
        "mpp_subcent_forfeited_usd": recon.mpp_subcent_forfeited_usd,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Multi-Leg Booking Saga and SFTP/MPP/Token Three-Way Reconciliation Guard."
    )
    parser.parse_args(argv)
    print(json.dumps(run_demo(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
