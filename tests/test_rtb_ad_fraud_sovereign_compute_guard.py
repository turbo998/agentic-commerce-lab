"""Unit tests for Stage 27: Real-Time Agentic Ad-Bidding (RTB) Invalid Traffic (IVT) Escrow, Sovereign AI Compute Export Control / Geofencing & SLA Credit-Note Reconciliation Guard."""

from __future__ import annotations

import unittest

from lab.rtb_ad_fraud_sovereign_compute_guard import (
    evaluate_agentic_rtb_invalid_traffic_escrow,
    reconcile_cloud_sla_downtime_credit_note,
    verify_sovereign_compute_export_geofence_attestation,
)


class TestRtbAdFraudSovereignComputeGuard(unittest.TestCase):
    def test_rtb_ads_cert_and_sivt_bot_click_farm_withholding(self) -> None:
        bad_sig = evaluate_agentic_rtb_invalid_traffic_escrow(
            {
                "campaign_id": "cmp_01",
                "ads_cert_signature_valid": False,
                "gross_billed_impressions": 100_000,
                "sivt_flagged_impressions": 500,
                "max_sivt_tolerance_bps": 200,
                "gross_spend_minor": 500_000,
            }
        )
        self.assertFalse(bad_sig["settled"])
        self.assertEqual(
            bad_sig["decision_code"],
            "ADS_CERT_IMPRESSION_SIGNATURE_INVALID_BLOCKED",
        )

        bot_farm = evaluate_agentic_rtb_invalid_traffic_escrow(
            {
                "campaign_id": "cmp_02",
                "ads_cert_signature_valid": True,
                "gross_billed_impressions": 100_000,
                "sivt_flagged_impressions": 18_000,
                "max_sivt_tolerance_bps": 200,
                "gross_spend_minor": 500_000,
            }
        )
        self.assertFalse(bot_farm["settled"])
        self.assertEqual(
            bot_farm["decision_code"],
            "RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD",
        )
        self.assertEqual(bot_farm["clawback_withheld_minor"], 90_000)

    def test_rtb_clean_impressions_settled(self) -> None:
        clean = evaluate_agentic_rtb_invalid_traffic_escrow(
            {
                "campaign_id": "cmp_03",
                "ads_cert_signature_valid": True,
                "gross_billed_impressions": 100_000,
                "sivt_flagged_impressions": 1_000,
                "max_sivt_tolerance_bps": 200,
                "gross_spend_minor": 500_000,
            }
        )
        self.assertTrue(clean["settled"])
        self.assertEqual(clean["decision_code"], "RTB_VERIFIED_IMPRESSION_ESCROW_SETTLED")
        self.assertEqual(clean["net_payable_minor"], 495_000)

    def test_sovereign_compute_geofence_spoof_and_embargo_blocked(self) -> None:
        spoofed = verify_sovereign_compute_export_geofence_attestation(
            {
                "cluster_id": "cls_h100_01",
                "tpm_location_signature_valid": True,
                "declared_region": "EU-DE",
                "ptp_measured_region": "RU",
                "allowed_sovereign_regions": ["EU-DE", "EU-FR"],
                "aggregate_tflops_fp16": 64_000,
            }
        )
        self.assertFalse(spoofed["allowed"])
        self.assertEqual(
            spoofed["decision_code"],
            "HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED",
        )

        embargoed = verify_sovereign_compute_export_geofence_attestation(
            {
                "cluster_id": "cls_h100_02",
                "tpm_location_signature_valid": True,
                "declared_region": "IR",
                "ptp_measured_region": "IR",
                "allowed_sovereign_regions": ["EU-DE", "EU-FR"],
                "aggregate_tflops_fp16": 64_000,
            }
        )
        self.assertFalse(embargoed["allowed"])
        self.assertEqual(
            embargoed["decision_code"],
            "EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED",
        )

    def test_sovereign_compute_compliant_and_cloud_sla_credit_note(self) -> None:
        compliant = verify_sovereign_compute_export_geofence_attestation(
            {
                "cluster_id": "cls_h100_03",
                "tpm_location_signature_valid": True,
                "declared_region": "EU-DE",
                "ptp_measured_region": "EU-DE",
                "allowed_sovereign_regions": ["EU-DE", "EU-FR"],
                "aggregate_tflops_fp16": 32_000,
            }
        )
        self.assertTrue(compliant["allowed"])
        self.assertEqual(compliant["decision_code"], "SOVEREIGN_COMPUTE_GEOFENCE_ATTESTED")

        sla_breach = reconcile_cloud_sla_downtime_credit_note(
            {
                "invoice_id": "inv_cloud_01",
                "observed_uptime_bps": 9_850,
                "committed_sla_bps": 9_990,
                "gross_invoice_minor": 1_000_000,
            }
        )
        self.assertTrue(sla_breach["reconciled"])
        self.assertEqual(sla_breach["decision_code"], "SLA_BREACH_CREDIT_NOTE_AUTO_NETTED")
        self.assertEqual(sla_breach["credit_percentage_bps"], 2_500)
        self.assertEqual(sla_breach["credit_note_minor"], 250_000)
        self.assertEqual(sla_breach["net_payable_minor"], 750_000)


if __name__ == "__main__":
    unittest.main()
