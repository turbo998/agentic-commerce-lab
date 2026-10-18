"""Unit tests for Stage 20 Embedded BNPL, Parametric Microinsurance & Invoice Factoring Guard."""

from __future__ import annotations

import unittest

from lab.embedded_bnpl_parametric_insurance_guard import (
    evaluate_agentic_bnpl_trade_credit_underwriting,
    evaluate_parametric_sla_microinsurance_claim,
    verify_invoice_factoring_ucc_lien_uniqueness,
)


class EmbeddedBnplParametricInsuranceGuardTestSuite(unittest.TestCase):
    def test_bnpl_blocks_multi_issuer_stacking_and_conserves_installments(self) -> None:
        stacked = evaluate_agentic_bnpl_trade_credit_underwriting(
            {
                "applicant_id": "buyer_stacker",
                "credit_mode": "BNPL_4PAY",
                "financed_principal_minor": 40000,
                "installment_count": 4,
                "dscr": "1.80",
                "concurrent_active_bnpl_issuers": 4,
                "max_concurrent_bnpl_issuers": 2,
                "post_purchase_dti_bps": 4600,
            }
        )
        self.assertFalse(stacked.approved)
        self.assertEqual(stacked.decision_code, "MULTI_ISSUER_BNPL_STACKING_BLOCKED")

        approved = evaluate_agentic_bnpl_trade_credit_underwriting(
            {
                "applicant_id": "buyer_prime",
                "credit_mode": "BNPL_4PAY",
                "financed_principal_minor": 10003,
                "installment_count": 4,
                "dscr": "1.62",
                "concurrent_active_bnpl_issuers": 1,
                "post_purchase_dti_bps": 2100,
                "available_cash_buffer_minor": 9000,
            }
        )
        self.assertTrue(approved.approved)
        self.assertEqual(approved.decision_code, "BNPL_TRADE_CREDIT_APPROVED")
        self.assertEqual(approved.installment_principal_minor, [2501, 2501, 2501, 2500])
        self.assertEqual(approved.principal_conservation_delta_minor, 0)

    def test_bnpl_declines_low_dscr_or_cash_buffer(self) -> None:
        declined = evaluate_agentic_bnpl_trade_credit_underwriting(
            {
                "applicant_id": "buyer_thin",
                "credit_mode": "B2B_NET_30",
                "financed_principal_minor": 100000,
                "installment_count": 3,
                "dscr": "1.12",
                "min_dscr": "1.35",
                "concurrent_active_bnpl_issuers": 0,
                "post_purchase_dti_bps": 2000,
            }
        )
        self.assertFalse(declined.approved)
        self.assertEqual(declined.decision_code, "INSUFFICIENT_DSCR_OR_CASH_BUFFER_DECLINED")

    def test_parametric_microinsurance_instant_settlement_and_double_dip_block(self) -> None:
        settled = evaluate_parametric_sla_microinsurance_claim(
            {
                "policy_id": "pol_flight_01",
                "hazard_type": "FLIGHT_DELAY_MINUTES",
                "oracle_quorum_signatures": 3,
                "min_oracle_quorum": 2,
                "actual_metric": "185",
                "policy_trigger_threshold": "120",
                "verified_economic_loss_minor": 30000,
                "merchant_already_refunded_minor": 0,
                "scheduled_parametric_benefit_minor": 30000,
            }
        )
        self.assertTrue(settled.payout_approved)
        self.assertEqual(settled.decision_code, "PARAMETRIC_INSTANT_PAYOUT_SETTLED")
        self.assertEqual(settled.approved_payout_minor, 30000)

        double_dip = evaluate_parametric_sla_microinsurance_claim(
            {
                "policy_id": "pol_flight_01",
                "hazard_type": "FLIGHT_DELAY_MINUTES",
                "oracle_quorum_signatures": 3,
                "min_oracle_quorum": 2,
                "actual_metric": "185",
                "policy_trigger_threshold": "120",
                "verified_economic_loss_minor": 30000,
                "merchant_already_refunded_minor": 30000,
                "scheduled_parametric_benefit_minor": 30000,
            }
        )
        self.assertFalse(double_dip.payout_approved)
        self.assertEqual(double_dip.decision_code, "DOUBLE_DIP_INDEMNITY_BLOCKED")

    def test_invoice_factoring_blocks_double_pledging_and_approves_unique_lien(self) -> None:
        first = verify_invoice_factoring_ucc_lien_uniqueness(
            {
                "invoice_id": "inv_8801",
                "seller_id": "acct_s1",
                "buyer_id": "buyer_b1",
                "invoice_number": "INV-8801",
                "invoice_total_minor": 100000,
                "issue_date": "2026-10-19",
                "requesting_factor_id": "factor_alpha",
                "notice_of_assignment_locked": True,
                "global_lien_registry": {},
            }
        )
        self.assertTrue(first.allowed)
        self.assertEqual(first.decision_code, "INVOICE_FACTORING_LIEN_REGISTERED")
        self.assertEqual(first.approved_advance_minor, 85000)

        duplicate = verify_invoice_factoring_ucc_lien_uniqueness(
            {
                "invoice_id": "inv_8801_alias",
                "seller_id": "acct_s1",
                "buyer_id": "buyer_b1",
                "invoice_number": "INV-8801",
                "invoice_total_minor": 100000,
                "issue_date": "2026-10-19",
                "requesting_factor_id": "factor_beta",
                "notice_of_assignment_locked": True,
                "global_lien_registry": {first.canonical_invoice_sha256: "factor_alpha"},
            }
        )
        self.assertFalse(duplicate.allowed)
        self.assertEqual(duplicate.decision_code, "INVOICE_DOUBLE_PLEDGING_BLOCKED")
        self.assertEqual(duplicate.existing_pledged_factor_id, "factor_alpha")


if __name__ == "__main__":
    unittest.main()
