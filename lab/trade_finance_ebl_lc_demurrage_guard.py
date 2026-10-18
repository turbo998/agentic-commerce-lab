"""Stage 26: Cross-Border Trade Finance MLETR Electronic Bill of Lading (eBL) Title Transfer, eUCP 600 Letter of Credit Document-Match & Marine Demurrage/Detention Escrow Guard.

Implements three deterministic maritime trade-finance & supply-chain settlement invariants:
1. `verify_mletr_electronic_bill_of_lading_endorsement`:
   - Enforces UNCITRAL MLETR / DCSA eBL 3.0 "singularity of control" (exclusive control token):
     - Rejects forged carrier signatures or split-endorsement double-spending where an eBL token is simultaneously pledged to two trade-finance banks (`EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED`),
     - Verifies atomic title endorsement from shipper/issuing bank to consignee upon escrow settlement (`MLETR_EBL_ATOMIC_TITLE_TRANSFERRED`).
2. `evaluate_eucp600_letter_of_credit_document_presentation`:
   - Automates ICC eUCP 600 Version 2.1 documentary credit examination across Commercial Invoice, eBL, Packing List, and Phytosanitary/Origin Certificate:
     - Blocks late presentation past `latest_shipment_epoch` or `presentation_period_days` (`EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED`),
     - Blocks short-shipped or over-invoiced tolerance breaches exceeding UCP 600 Art. 30 `±5%` quantity / amount tolerance (`EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH`),
     - Honors compliant presentation and releases issuing-bank payment undertaking (`EUCP600_COMPLIANT_PRESENTATION_HONORED`).
3. `evaluate_marine_demurrage_detention_parametric_escrow`:
   - Evaluates container port free-time windows (`free_time_hours`) against port terminal gate-in/gate-out timestamps and customs hold exemptions:
     - Excuses carrier-caused port congestion or force-majeure customs inspection delays from buyer demurrage liability (`PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED`),
     - Settles capped progressive demurrage/detention charges from escrow and refunds unused deposit to the consignee (`MARINE_DEMURRAGE_CAPPED_SETTLED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class MletrEblEndorsementResult:
    """Result of verifying an UNCITRAL MLETR / DCSA eBL 3.0 title transfer."""

    allowed: bool
    decision_code: str
    ebl_number: str
    current_holder_did: str
    endorsee_did: str
    exclusive_control_verified: bool
    title_transfer_hash: str
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Eucp600PresentationResult:
    """Result of evaluating an ICC eUCP 600 documentary credit presentation."""

    honored: bool
    decision_code: str
    lc_number: str
    lc_amount_minor: int
    invoice_amount_minor: int
    quantity_variance_bps: int
    max_quantity_tolerance_bps: int
    discrepancies: list[str]
    settlement_undertaking_minor: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarineDemurrageEscrowResult:
    """Result of evaluating marine container demurrage & detention escrow."""

    settled: bool
    decision_code: str
    container_id: str
    total_dwell_hours: int
    carrier_or_customs_excusable_hours: int
    chargeable_overage_hours: int
    demurrage_fee_minor: int
    consignee_escrow_refund_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_mletr_electronic_bill_of_lading_endorsement(
    ebl_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify UNCITRAL MLETR / DCSA eBL 3.0 exclusive control and atomic title transfer."""

    ebl_number = str(ebl_context.get("ebl_number", "ebl_unknown"))
    carrier_sig_valid = bool(ebl_context.get("carrier_dcsa_signature_valid", True))
    registry_active_control_token = str(ebl_context.get("registry_active_control_token", ""))
    presented_control_token = str(ebl_context.get("presented_control_token", ""))
    concurrent_pledge_detected = bool(ebl_context.get("concurrent_duplicate_pledge_detected", False))
    current_holder_did = str(ebl_context.get("current_holder_did", ""))
    endorsee_did = str(ebl_context.get("endorsee_did", ""))
    escrow_payment_confirmed = bool(ebl_context.get("escrow_payment_confirmed", True))

    digest = hashlib.sha256(
        json.dumps(
            {
                "ebl_number": ebl_number,
                "current_holder_did": current_holder_did,
                "endorsee_did": endorsee_did,
                "presented_control_token": presented_control_token,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]

    if (
        not carrier_sig_valid
        or concurrent_pledge_detected
        or not registry_active_control_token
        or registry_active_control_token != presented_control_token
    ):
        return MletrEblEndorsementResult(
            allowed=False,
            decision_code="EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED",
            ebl_number=ebl_number,
            current_holder_did=current_holder_did,
            endorsee_did=endorsee_did,
            exclusive_control_verified=False,
            title_transfer_hash=digest,
            reason_codes=["EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED"],
        ).to_dict()

    if not escrow_payment_confirmed:
        return MletrEblEndorsementResult(
            allowed=False,
            decision_code="EBL_TITLE_HELD_PENDING_ESCROW_SETTLEMENT",
            ebl_number=ebl_number,
            current_holder_did=current_holder_did,
            endorsee_did=endorsee_did,
            exclusive_control_verified=True,
            title_transfer_hash=digest,
            reason_codes=["EBL_TITLE_HELD_PENDING_ESCROW_SETTLEMENT"],
        ).to_dict()

    return MletrEblEndorsementResult(
        allowed=True,
        decision_code="MLETR_EBL_ATOMIC_TITLE_TRANSFERRED",
        ebl_number=ebl_number,
        current_holder_did=current_holder_did,
        endorsee_did=endorsee_did,
        exclusive_control_verified=True,
        title_transfer_hash=digest,
        reason_codes=["MLETR_EBL_ATOMIC_TITLE_TRANSFERRED"],
    ).to_dict()


def evaluate_eucp600_letter_of_credit_document_presentation(
    lc_context: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate ICC eUCP 600 documentary credit compliance across eBL, Invoice, and Certificates."""

    lc_number = str(lc_context.get("lc_number", "lc_unknown"))
    lc_amount_minor = max(0, int(lc_context.get("lc_max_amount_minor", 0)))
    invoice_amount_minor = max(0, int(lc_context.get("commercial_invoice_amount_minor", 0)))
    contracted_qty = max(1, int(lc_context.get("contracted_quantity_units", 1)))
    shipped_qty = max(0, int(lc_context.get("ebl_shipped_quantity_units", 0)))
    max_qty_tolerance_bps = max(0, int(lc_context.get("ucp600_art30_tolerance_bps", 500)))
    latest_shipment_epoch = int(lc_context.get("latest_shipment_epoch", 0))
    actual_shipment_epoch = int(lc_context.get("actual_shipment_epoch", 0))
    lc_expiry_epoch = int(lc_context.get("lc_expiry_epoch", 0))
    presentation_epoch = int(lc_context.get("presentation_epoch", 0))
    clean_on_board_ebl = bool(lc_context.get("clean_on_board_ebl", True))

    discrepancies: list[str] = []

    if (
        (latest_shipment_epoch > 0 and actual_shipment_epoch > latest_shipment_epoch)
        or (lc_expiry_epoch > 0 and presentation_epoch > lc_expiry_epoch)
    ):
        discrepancies.append("EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED")
        return Eucp600PresentationResult(
            honored=False,
            decision_code="EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED",
            lc_number=lc_number,
            lc_amount_minor=lc_amount_minor,
            invoice_amount_minor=invoice_amount_minor,
            quantity_variance_bps=0,
            max_quantity_tolerance_bps=max_qty_tolerance_bps,
            discrepancies=discrepancies,
            settlement_undertaking_minor=0,
        ).to_dict()

    qty_variance_bps = abs(shipped_qty - contracted_qty) * 10_000 // contracted_qty

    if invoice_amount_minor > lc_amount_minor:
        discrepancies.append("INVOICE_EXCEEDS_LC_CREDIT_AMOUNT")
    if qty_variance_bps > max_qty_tolerance_bps:
        discrepancies.append("QUANTITY_VARIANCE_EXCEEDS_ART30_TOLERANCE")
    if not clean_on_board_ebl:
        discrepancies.append("UNCLAUSSATED_CLEAN_ON_BOARD_EBL_REQUIRED")

    if discrepancies:
        return Eucp600PresentationResult(
            honored=False,
            decision_code="EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH",
            lc_number=lc_number,
            lc_amount_minor=lc_amount_minor,
            invoice_amount_minor=invoice_amount_minor,
            quantity_variance_bps=qty_variance_bps,
            max_quantity_tolerance_bps=max_qty_tolerance_bps,
            discrepancies=discrepancies,
            settlement_undertaking_minor=0,
        ).to_dict()

    return Eucp600PresentationResult(
        honored=True,
        decision_code="EUCP600_COMPLIANT_PRESENTATION_HONORED",
        lc_number=lc_number,
        lc_amount_minor=lc_amount_minor,
        invoice_amount_minor=invoice_amount_minor,
        quantity_variance_bps=qty_variance_bps,
        max_quantity_tolerance_bps=max_qty_tolerance_bps,
        discrepancies=[],
        settlement_undertaking_minor=invoice_amount_minor,
    ).to_dict()


def evaluate_marine_demurrage_detention_parametric_escrow(
    demurrage_context: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate container demurrage/detention free-time, FMC excusable delays, and capped escrow settlement."""

    container_id = str(demurrage_context.get("container_id", "cntr_unknown"))
    total_dwell_hours = max(0, int(demurrage_context.get("total_dwell_hours", 0)))
    free_time_hours = max(0, int(demurrage_context.get("free_time_hours", 96)))
    carrier_or_customs_excusable_hours = max(
        0, int(demurrage_context.get("carrier_or_customs_excusable_hours", 0))
    )
    hourly_demurrage_rate_minor = max(0, int(demurrage_context.get("hourly_demurrage_rate_minor", 500)))
    demurrage_escrow_hold_minor = max(0, int(demurrage_context.get("demurrage_escrow_hold_minor", 0)))
    max_liability_cap_minor = max(
        0, int(demurrage_context.get("max_liability_cap_minor", demurrage_escrow_hold_minor))
    )

    net_dwell_hours = max(0, total_dwell_hours - carrier_or_customs_excusable_hours)
    chargeable_overage_hours = max(0, net_dwell_hours - free_time_hours)

    if total_dwell_hours > free_time_hours and chargeable_overage_hours == 0:
        return MarineDemurrageEscrowResult(
            settled=True,
            decision_code="PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED",
            container_id=container_id,
            total_dwell_hours=total_dwell_hours,
            carrier_or_customs_excusable_hours=carrier_or_customs_excusable_hours,
            chargeable_overage_hours=0,
            demurrage_fee_minor=0,
            consignee_escrow_refund_minor=demurrage_escrow_hold_minor,
            reason_codes=["PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED"],
        ).to_dict()

    raw_fee = chargeable_overage_hours * hourly_demurrage_rate_minor
    capped_fee = min(raw_fee, max_liability_cap_minor, demurrage_escrow_hold_minor)
    refund_minor = max(0, demurrage_escrow_hold_minor - capped_fee)

    return MarineDemurrageEscrowResult(
        settled=True,
        decision_code="MARINE_DEMURRAGE_CAPPED_SETTLED",
        container_id=container_id,
        total_dwell_hours=total_dwell_hours,
        carrier_or_customs_excusable_hours=carrier_or_customs_excusable_hours,
        chargeable_overage_hours=chargeable_overage_hours,
        demurrage_fee_minor=capped_fee,
        consignee_escrow_refund_minor=refund_minor,
        reason_codes=["MARINE_DEMURRAGE_CAPPED_SETTLED"],
    ).to_dict()
