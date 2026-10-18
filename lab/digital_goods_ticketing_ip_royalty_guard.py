"""Stage 23: Digital Goods / SaaS Seat DRM Revocation, Secondary Ticketing Anti-Scalping Rotating-QR Escrow & C2PA Generative IP Micro-Royalty Split Guard.

Implements three deterministic digital-asset & ticketing invariants:
1. `evaluate_digital_license_seat_activation_guard`:
   - Defends instant-delivery digital goods (API keys, CAD/industrial software
     licenses, game/ebook activation codes) against "download-and-refund" friendly
     fraud (`REFUNDED_LICENSE_KEY_REVOKED_BLOCKED`), datacenter proxy bulk key
     harvesting (`DATACENTER_BULK_KEY_HARVESTING_BLOCKED`), and TPM/Enclave seat
     sharing beyond licensed concurrency (`SEAT_CONCURRENCY_LIMIT_EXCEEDED`).
2. `evaluate_event_ticket_anti_scalping_escrow`:
   - Enforces face-value resale markup caps (`RESALE_MARKUP_CAP_EXCEEDED_SCALPING_BLOCKED`),
   - Blocks static screenshot ticket fraud by requiring `<= 15s` rotating TOTP
     cryptographic QR tokens (`STATIC_SCREENSHOT_QR_EXPIRED_BLOCKED`),
   - Releases secondary ticket escrow only upon verified venue turnstile check-in
     (`VENUE_CHECKIN_VERIFIED_ESCROW_RELEASED`).
3. `evaluate_generative_ip_royalty_micro_split`:
   - Verifies C2PA Content Credentials provenance and blocks unauthorized training
     scrapes (`C2PA_PROVENANCE_MISSING_OR_SCRAPE_BLOCKED`),
   - Splits licensing fees across multi-creator contribution weights via the
     Largest Remainder Method with `conservation_delta_minor == 0`
     (`C2PA_ROYALTY_MICRO_SPLIT_SETTLED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any

from lab.marketplace_split_settlement_guard import allocate_by_largest_remainder


@dataclass(frozen=True)
class DigitalLicenseSeatActivationResult:
    """Result of evaluating a digital license / SaaS seat activation request."""

    allowed: bool
    decision_code: str
    license_id: str
    active_tpm_seats: int
    max_concurrent_seats: int
    license_revoked: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventTicketAntiScalpingEscrowResult:
    """Result of secondary event ticket anti-scalping, rotating TOTP QR, and venue escrow."""

    escrow_released: bool
    decision_code: str
    ticket_id: str
    face_value_minor: int
    resale_price_minor: int
    resale_markup_bps: int
    max_resale_markup_bps: int
    qr_token_age_seconds: int
    venue_checked_in: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenerativeIPRoyaltySplitResult:
    """Result of C2PA provenance verification and multi-creator micro-royalty split."""

    allowed: bool
    decision_code: str
    asset_c2pa_id: str
    gross_licensing_fee_minor: int
    platform_fee_minor: int
    net_creator_pool_minor: int
    creator_payouts_minor: dict[str, int]
    conservation_delta_minor: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_digital_license_seat_activation_guard(
    license_context: dict[str, Any],
) -> DigitalLicenseSeatActivationResult:
    """Verify digital license / SaaS seat activation against refund revocation, bulk harvesting, and TPM seat limits."""

    license_id = str(license_context.get("license_id", ""))
    refunded_or_disputed = bool(license_context.get("order_refunded_or_disputed", False))
    datacenter_proxy = bool(license_context.get("datacenter_bulk_proxy_detected", False))
    max_seats = max(1, int(license_context.get("max_concurrent_seats", 1)))
    tpm_fingerprints = {
        str(fp).strip()
        for fp in license_context.get("active_tpm_enclave_fingerprints", [])
        if str(fp).strip()
    }
    active_seats = len(tpm_fingerprints)

    if refunded_or_disputed:
        return DigitalLicenseSeatActivationResult(
            allowed=False,
            decision_code="REFUNDED_LICENSE_KEY_REVOKED_BLOCKED",
            license_id=license_id,
            active_tpm_seats=active_seats,
            max_concurrent_seats=max_seats,
            license_revoked=True,
        )

    if datacenter_proxy:
        return DigitalLicenseSeatActivationResult(
            allowed=False,
            decision_code="DATACENTER_BULK_KEY_HARVESTING_BLOCKED",
            license_id=license_id,
            active_tpm_seats=active_seats,
            max_concurrent_seats=max_seats,
            license_revoked=False,
        )

    if active_seats > max_seats:
        return DigitalLicenseSeatActivationResult(
            allowed=False,
            decision_code="SEAT_CONCURRENCY_LIMIT_EXCEEDED",
            license_id=license_id,
            active_tpm_seats=active_seats,
            max_concurrent_seats=max_seats,
            license_revoked=False,
        )

    return DigitalLicenseSeatActivationResult(
        allowed=True,
        decision_code="DIGITAL_LICENSE_SEAT_ACTIVATION_GRANTED",
        license_id=license_id,
        active_tpm_seats=active_seats,
        max_concurrent_seats=max_seats,
        license_revoked=False,
    )


def evaluate_event_ticket_anti_scalping_escrow(
    ticket_bundle: dict[str, Any],
) -> EventTicketAntiScalpingEscrowResult:
    """Enforce secondary ticket markup caps, `<= 15s` rotating TOTP QR, and venue check-in escrow release."""

    ticket_id = str(ticket_bundle.get("ticket_id", ""))
    face_value = max(1, int(ticket_bundle.get("face_value_minor", 1)))
    resale_price = max(0, int(ticket_bundle.get("resale_price_minor", 0)))
    max_markup_bps = max(0, int(ticket_bundle.get("max_resale_markup_bps", 1_000)))
    qr_age_sec = int(ticket_bundle.get("qr_token_age_seconds", 0))
    max_qr_ttl_sec = int(ticket_bundle.get("max_qr_rotation_ttl_seconds", 15))
    totp_valid = bool(ticket_bundle.get("totp_signature_valid", False))
    venue_checked_in = bool(ticket_bundle.get("venue_turnstile_checked_in", False))

    markup_bps = max(0, ((resale_price - face_value) * 10_000) // face_value)

    if markup_bps > max_markup_bps:
        return EventTicketAntiScalpingEscrowResult(
            escrow_released=False,
            decision_code="RESALE_MARKUP_CAP_EXCEEDED_SCALPING_BLOCKED",
            ticket_id=ticket_id,
            face_value_minor=face_value,
            resale_price_minor=resale_price,
            resale_markup_bps=markup_bps,
            max_resale_markup_bps=max_markup_bps,
            qr_token_age_seconds=qr_age_sec,
            venue_checked_in=venue_checked_in,
        )

    if not totp_valid or qr_age_sec < 0 or qr_age_sec > max_qr_ttl_sec:
        return EventTicketAntiScalpingEscrowResult(
            escrow_released=False,
            decision_code="STATIC_SCREENSHOT_QR_EXPIRED_BLOCKED",
            ticket_id=ticket_id,
            face_value_minor=face_value,
            resale_price_minor=resale_price,
            resale_markup_bps=markup_bps,
            max_resale_markup_bps=max_markup_bps,
            qr_token_age_seconds=qr_age_sec,
            venue_checked_in=venue_checked_in,
        )

    if not venue_checked_in:
        return EventTicketAntiScalpingEscrowResult(
            escrow_released=False,
            decision_code="ESCROW_HELD_PENDING_VENUE_CHECKIN",
            ticket_id=ticket_id,
            face_value_minor=face_value,
            resale_price_minor=resale_price,
            resale_markup_bps=markup_bps,
            max_resale_markup_bps=max_markup_bps,
            qr_token_age_seconds=qr_age_sec,
            venue_checked_in=False,
        )

    return EventTicketAntiScalpingEscrowResult(
        escrow_released=True,
        decision_code="VENUE_CHECKIN_VERIFIED_ESCROW_RELEASED",
        ticket_id=ticket_id,
        face_value_minor=face_value,
        resale_price_minor=resale_price,
        resale_markup_bps=markup_bps,
        max_resale_markup_bps=max_markup_bps,
        qr_token_age_seconds=qr_age_sec,
        venue_checked_in=True,
    )


def evaluate_generative_ip_royalty_micro_split(
    ip_bundle: dict[str, Any],
) -> GenerativeIPRoyaltySplitResult:
    """Verify C2PA Content Credentials signature and split creator micro-royalties with zero rounding drift."""

    asset_id = str(ip_bundle.get("asset_c2pa_id", ""))
    c2pa_valid = bool(ip_bundle.get("c2pa_manifest_signature_valid", False))
    scrape_detected = bool(ip_bundle.get("unauthorized_training_scrape_detected", False))
    gross_minor = max(0, int(ip_bundle.get("gross_licensing_fee_minor", 0)))
    platform_bps = max(0, int(ip_bundle.get("platform_fee_bps", 500)))
    creators: list[dict[str, Any]] = list(ip_bundle.get("creators", []))

    if not c2pa_valid or scrape_detected or not creators:
        return GenerativeIPRoyaltySplitResult(
            allowed=False,
            decision_code="C2PA_PROVENANCE_MISSING_OR_SCRAPE_BLOCKED",
            asset_c2pa_id=asset_id,
            gross_licensing_fee_minor=gross_minor,
            platform_fee_minor=0,
            net_creator_pool_minor=0,
            creator_payouts_minor={},
            conservation_delta_minor=0,
        )

    platform_fee = (gross_minor * platform_bps + 5_000) // 10_000
    creator_pool = max(0, gross_minor - platform_fee)
    weights = [max(1, int(c.get("weight_bps", 1))) for c in creators]
    splits = allocate_by_largest_remainder(creator_pool, weights)

    payouts: dict[str, int] = {}
    for c, amt in zip(creators, splits):
        cid = str(c.get("creator_id", ""))
        payouts[cid] = payouts.get(cid, 0) + amt

    delta = gross_minor - (platform_fee + sum(payouts.values()))
    return GenerativeIPRoyaltySplitResult(
        allowed=True,
        decision_code="C2PA_ROYALTY_MICRO_SPLIT_SETTLED",
        asset_c2pa_id=asset_id,
        gross_licensing_fee_minor=gross_minor,
        platform_fee_minor=platform_fee,
        net_creator_pool_minor=creator_pool,
        creator_payouts_minor=payouts,
        conservation_delta_minor=delta,
    )


def main() -> int:
    lic_res = evaluate_digital_license_seat_activation_guard(
        {
            "license_id": "lic_cad_23",
            "order_refunded_or_disputed": True,
            "datacenter_bulk_proxy_detected": False,
            "max_concurrent_seats": 3,
            "active_tpm_enclave_fingerprints": ["tpm_01"],
        }
    )
    tkt_res = evaluate_event_ticket_anti_scalping_escrow(
        {
            "ticket_id": "tkt_concert_23",
            "face_value_minor": 10_000,
            "resale_price_minor": 10_800,
            "max_resale_markup_bps": 1_000,
            "qr_token_age_seconds": 6,
            "max_qr_rotation_ttl_seconds": 15,
            "totp_signature_valid": True,
            "venue_turnstile_checked_in": True,
        }
    )
    ip_res = evaluate_generative_ip_royalty_micro_split(
        {
            "asset_c2pa_id": "urn:c2pa:dataset:med-imaging-v4",
            "c2pa_manifest_signature_valid": True,
            "unauthorized_training_scrape_detected": False,
            "gross_licensing_fee_minor": 10_000,
            "platform_fee_bps": 500,
            "creators": [
                {"creator_id": "creator_alpha", "weight_bps": 3_333},
                {"creator_id": "creator_beta", "weight_bps": 3_333},
                {"creator_id": "creator_gamma", "weight_bps": 3_334},
            ],
        }
    )
    print(
        json.dumps(
            {
                "stage": "stage23-digital-goods-ticketing-ip-royalty-guard",
                "refunded_license_decision": lic_res.decision_code,
                "ticket_escrow_decision": tkt_res.decision_code,
                "c2pa_royalty_decision": ip_res.decision_code,
                "c2pa_creator_payouts": ip_res.creator_payouts_minor,
                "conservation_delta_minor": ip_res.conservation_delta_minor,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
