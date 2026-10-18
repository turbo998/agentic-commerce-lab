"""Unit tests for Stage 23 Digital Goods DRM, Anti-Scalping Ticketing Escrow & C2PA Royalty Split Guard."""

from __future__ import annotations

import unittest

from lab.digital_goods_ticketing_ip_royalty_guard import (
    evaluate_digital_license_seat_activation_guard,
    evaluate_event_ticket_anti_scalping_escrow,
    evaluate_generative_ip_royalty_micro_split,
)


class DigitalGoodsTicketingIPRoyaltyGuardTests(unittest.TestCase):
    def test_digital_license_revokes_on_refund_and_blocks_datacenter_harvesting(self) -> None:
        refunded = evaluate_digital_license_seat_activation_guard(
            {
                "license_id": "lic_01",
                "order_refunded_or_disputed": True,
                "datacenter_bulk_proxy_detected": False,
                "max_concurrent_seats": 2,
                "active_tpm_enclave_fingerprints": ["tpm_a"],
            }
        )
        self.assertFalse(refunded.allowed)
        self.assertTrue(refunded.license_revoked)
        self.assertEqual(refunded.decision_code, "REFUNDED_LICENSE_KEY_REVOKED_BLOCKED")

        harvesting = evaluate_digital_license_seat_activation_guard(
            {
                "license_id": "lic_02",
                "order_refunded_or_disputed": False,
                "datacenter_bulk_proxy_detected": True,
                "max_concurrent_seats": 2,
                "active_tpm_enclave_fingerprints": ["tpm_a"],
            }
        )
        self.assertFalse(harvesting.allowed)
        self.assertEqual(
            harvesting.decision_code, "DATACENTER_BULK_KEY_HARVESTING_BLOCKED"
        )

    def test_digital_license_enforces_tpm_seat_concurrency_limit(self) -> None:
        over_seat = evaluate_digital_license_seat_activation_guard(
            {
                "license_id": "lic_03",
                "order_refunded_or_disputed": False,
                "datacenter_bulk_proxy_detected": False,
                "max_concurrent_seats": 2,
                "active_tpm_enclave_fingerprints": ["tpm_1", "tpm_2", "tpm_3"],
            }
        )
        self.assertFalse(over_seat.allowed)
        self.assertEqual(over_seat.decision_code, "SEAT_CONCURRENCY_LIMIT_EXCEEDED")

        valid_seat = evaluate_digital_license_seat_activation_guard(
            {
                "license_id": "lic_04",
                "order_refunded_or_disputed": False,
                "datacenter_bulk_proxy_detected": False,
                "max_concurrent_seats": 2,
                "active_tpm_enclave_fingerprints": ["tpm_1", "tpm_2"],
            }
        )
        self.assertTrue(valid_seat.allowed)
        self.assertEqual(
            valid_seat.decision_code, "DIGITAL_LICENSE_SEAT_ACTIVATION_GRANTED"
        )

    def test_event_ticket_blocks_scalping_markup_and_expired_static_qr(self) -> None:
        scalp = evaluate_event_ticket_anti_scalping_escrow(
            {
                "ticket_id": "tkt_01",
                "face_value_minor": 10_000,
                "resale_price_minor": 25_000,
                "max_resale_markup_bps": 1_000,
                "qr_token_age_seconds": 5,
                "max_qr_rotation_ttl_seconds": 15,
                "totp_signature_valid": True,
                "venue_turnstile_checked_in": True,
            }
        )
        self.assertFalse(scalp.escrow_released)
        self.assertEqual(
            scalp.decision_code, "RESALE_MARKUP_CAP_EXCEEDED_SCALPING_BLOCKED"
        )

        screenshot = evaluate_event_ticket_anti_scalping_escrow(
            {
                "ticket_id": "tkt_02",
                "face_value_minor": 10_000,
                "resale_price_minor": 10_500,
                "max_resale_markup_bps": 1_000,
                "qr_token_age_seconds": 45,
                "max_qr_rotation_ttl_seconds": 15,
                "totp_signature_valid": True,
                "venue_turnstile_checked_in": True,
            }
        )
        self.assertFalse(screenshot.escrow_released)
        self.assertEqual(
            screenshot.decision_code, "STATIC_SCREENSHOT_QR_EXPIRED_BLOCKED"
        )

    def test_event_ticket_releases_escrow_only_after_venue_checkin(self) -> None:
        checked_in = evaluate_event_ticket_anti_scalping_escrow(
            {
                "ticket_id": "tkt_03",
                "face_value_minor": 10_000,
                "resale_price_minor": 10_800,
                "max_resale_markup_bps": 1_000,
                "qr_token_age_seconds": 8,
                "max_qr_rotation_ttl_seconds": 15,
                "totp_signature_valid": True,
                "venue_turnstile_checked_in": True,
            }
        )
        self.assertTrue(checked_in.escrow_released)
        self.assertEqual(
            checked_in.decision_code, "VENUE_CHECKIN_VERIFIED_ESCROW_RELEASED"
        )

    def test_c2pa_generative_ip_royalty_micro_split_and_scrape_block(self) -> None:
        scraped = evaluate_generative_ip_royalty_micro_split(
            {
                "asset_c2pa_id": "urn:c2pa:img:01",
                "c2pa_manifest_signature_valid": False,
                "unauthorized_training_scrape_detected": True,
                "gross_licensing_fee_minor": 5_000,
                "platform_fee_bps": 500,
                "creators": [{"creator_id": "c1", "weight_bps": 10_000}],
            }
        )
        self.assertFalse(scraped.allowed)
        self.assertEqual(
            scraped.decision_code, "C2PA_PROVENANCE_MISSING_OR_SCRAPE_BLOCKED"
        )

        settled = evaluate_generative_ip_royalty_micro_split(
            {
                "asset_c2pa_id": "urn:c2pa:img:02",
                "c2pa_manifest_signature_valid": True,
                "unauthorized_training_scrape_detected": False,
                "gross_licensing_fee_minor": 10_000,
                "platform_fee_bps": 500,
                "creators": [
                    {"creator_id": "c1", "weight_bps": 3_333},
                    {"creator_id": "c2", "weight_bps": 3_333},
                    {"creator_id": "c3", "weight_bps": 3_334},
                ],
            }
        )
        self.assertTrue(settled.allowed)
        self.assertEqual(settled.decision_code, "C2PA_ROYALTY_MICRO_SPLIT_SETTLED")
        self.assertEqual(settled.conservation_delta_minor, 0)
        self.assertEqual(
            settled.platform_fee_minor + sum(settled.creator_payouts_minor.values()),
            10_000,
        )


if __name__ == "__main__":
    unittest.main()
