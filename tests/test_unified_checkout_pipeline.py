"""Unit tests for Stage 8 7-Gate Unified Agentic Checkout Pipeline & Chaos Resilience Benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.booking_sftp_reconciliation_guard import BookingLegHold
from lab.unified_checkout_pipeline import (
    build_golden_pipeline_input,
    execute_unified_agentic_checkout,
    main,
    run_resilience_benchmark_suite,
    write_resilience_report_artifacts,
)


class UnifiedCheckoutPipelineTests(unittest.TestCase):
    def test_golden_7gate_pipeline_commits_and_seals_ce3_merkle_root(self) -> None:
        inp = build_golden_pipeline_input()
        res = execute_unified_agentic_checkout(inp)
        self.assertTrue(res.checkout_committed)
        self.assertIsNone(res.blocked_at_gate)
        self.assertEqual(res.terminal_decision_code, "UNIFIED_PIPELINE_COMMITTED")
        self.assertEqual(res.total_gates_executed, 7)
        self.assertIsNotNone(res.ce3_merkle_root_sha256)
        self.assertEqual(res.eod_variance_minor, 0)

    def test_gate1_short_circuits_on_revoked_key_sybil_quota_and_webmcp_origin(self) -> None:
        revoked = execute_unified_agentic_checkout(
            build_golden_pipeline_input(key_id="tap_kid_revoked_99")
        )
        self.assertFalse(revoked.checkout_committed)
        self.assertEqual(revoked.blocked_at_gate, 1)
        self.assertEqual(revoked.total_gates_executed, 1)
        self.assertIn("AGENT_DIRECTORY_KEY_REVOKED", revoked.terminal_decision_code)

        sybil = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                principal_sku_ledger={("did:web:buyer.example:alice", "gpu_h200_cluster"): 2}
            )
        )
        self.assertFalse(sybil.checkout_committed)
        self.assertEqual(sybil.blocked_at_gate, 1)
        self.assertIn("PRINCIPAL_SCARCITY_QUOTA_EXCEEDED", sybil.terminal_decision_code)

        origin = execute_unified_agentic_checkout(
            build_golden_pipeline_input(webmcp_origin="https://phishing.example.org")
        )
        self.assertFalse(origin.checkout_committed)
        self.assertEqual(origin.blocked_at_gate, 1)
        self.assertIn("WEBMCP_CROSS_ORIGIN_VIOLATION", origin.terminal_decision_code)

    def test_gate2_blocks_corrupted_catalog_shard_and_summary_terms_mismatch(self) -> None:
        bad_feed = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                fetched_shards={
                    "https://shop.merchant.example/feeds/catalog-001.jsonl.gz": b'{"tampered":true}'
                }
            )
        )
        self.assertFalse(bad_feed.checkout_committed)
        self.assertEqual(bad_feed.blocked_at_gate, 2)
        self.assertEqual(bad_feed.total_gates_executed, 2)

        bad_broker = execute_unified_agentic_checkout(
            build_golden_pipeline_input(summary_amount_minor=10000, terms_amount_minor=27300)
        )
        self.assertFalse(bad_broker.checkout_committed)
        self.assertEqual(bad_broker.blocked_at_gate, 2)
        self.assertIn("SUMMARY_TERMS_AMOUNT_MISMATCH", bad_broker.terminal_decision_code)

    def test_gate3_and_gate4_block_customs_tampering_and_token_margin_erosion(self) -> None:
        ddu_downgrade = execute_unified_agentic_checkout(
            build_golden_pipeline_input(proposed_incoterm="DAP", quoted_checkout_total_minor=23500)
        )
        self.assertFalse(ddu_downgrade.checkout_committed)
        self.assertEqual(ddu_downgrade.blocked_at_gate, 3)

        hs_tamper = execute_unified_agentic_checkout(
            build_golden_pipeline_input(proposed_hs_code="3926909900")
        )
        self.assertFalse(hs_tamper.checkout_committed)
        self.assertEqual(hs_tamper.blocked_at_gate, 3)

        margin_trip = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                gross_transaction_usd="2.00",
                input_tokens=80000,
                output_tokens=15000,
                payment_rail="stripe_spt_card",
            )
        )
        self.assertFalse(margin_trip.checkout_committed)
        self.assertEqual(margin_trip.blocked_at_gate, 4)
        self.assertIn("COST_ENVELOPE_EXCEEDED", margin_trip.terminal_decision_code)

    def test_gate5_and_gate6_block_expired_saga_unreversed_refund_and_spt_replay(self) -> None:
        expired_saga = execute_unified_agentic_checkout(
            build_golden_pipeline_input(commit_attempt_epoch=1175)
        )
        self.assertFalse(expired_saga.checkout_committed)
        self.assertEqual(expired_saga.blocked_at_gate, 5)

        auto_capture = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                booking_legs=[
                    BookingLegHold(
                        "flight_gds", "gds", 15000, "automatic", "held", 1180, 86400, True
                    ),
                ]
            )
        )
        self.assertFalse(auto_capture.checkout_committed)
        self.assertEqual(auto_capture.blocked_at_gate, 5)

        unreversed_refund = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                refund_line_amount_minor=5000,
                refund_reverse_transfer=False,
                refund_application_fee=False,
            )
        )
        self.assertFalse(unreversed_refund.checkout_committed)
        self.assertEqual(unreversed_refund.blocked_at_gate, 6)

        spt_replay = execute_unified_agentic_checkout(
            build_golden_pipeline_input(resolved_spt_tokens={"spt_golden_01"})
        )
        self.assertFalse(spt_replay.checkout_committed)
        self.assertEqual(spt_replay.blocked_at_gate, 6)

    def test_gate7_blocks_eod_payout_variance(self) -> None:
        bad_eod = execute_unified_agentic_checkout(
            build_golden_pipeline_input(reported_bank_payout_minor=19999)
        )
        self.assertFalse(bad_eod.checkout_committed)
        self.assertEqual(bad_eod.blocked_at_gate, 7)
        self.assertNotEqual(bad_eod.eod_variance_minor, 0)

    def test_gate2_blocks_free_trial_negative_option_tccv_overflow(self) -> None:
        dark_trial = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                recurring_mandate={
                    "mandate_id": "mandate_onetime_50usd",
                    "allow_recurring": False,
                    "max_total_commitment_minor": 5_000,
                    "max_per_cycle_minor": 5_000,
                },
                subscription_offer_terms={
                    "billing_interval": "month",
                    "trial_days": 7,
                    "auto_convert": True,
                    "initial_charge_minor": 0,
                    "recurring_charge_minor": 19_900,
                    "min_commitment_cycles": 12,
                    "early_termination_fee_minor": 15_000,
                    "cancel_cutoff_hours_before_trial_end": 72.0,
                    "auto_cancel_hook_armed": False,
                    "summary_discloses_recurring": True,
                },
            )
        )
        self.assertFalse(dark_trial.checkout_committed)
        self.assertEqual(dark_trial.blocked_at_gate, 2)
        self.assertIn("NEGATIVE_OPTION_MANDATE_MISMATCH", dark_trial.terminal_decision_code)

    def test_gate6_blocks_b2b_bec_beneficiary_hijack(self) -> None:
        bec_hijack = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                b2b_po_mandate={
                    "po_id": "po_01",
                    "ancillary_allowance_minor": 1000,
                    "lines": [{"sku": "sku_01", "qty_ordered": 2, "unit_price_minor": 10000}],
                },
                b2b_grn_receipt={
                    "lines": [{"sku": "sku_01", "qty_delivered": 2, "qty_rejected_damaged": 0}]
                },
                b2b_e_invoice={
                    "invoice_id": "inv_01",
                    "payout_endpoint_id": "acct_attacker_spoofed",
                    "ancillary_charges_minor": 1000,
                    "lines": [{"sku": "sku_01", "qty_invoiced": 2, "unit_price_minor": 10000}],
                },
                b2b_vendor_master={
                    "kyb_verified_endpoint_id": "acct_seller_jp_01",
                    "ofac_sanctioned": False,
                },
            )
        )
        self.assertFalse(bec_hijack.checkout_committed)
        self.assertEqual(bec_hijack.blocked_at_gate, 6)
        self.assertIn("BENEFICIARY_ENDPOINT_HIJACK_BLOCKED", bec_hijack.terminal_decision_code)

    def test_gate3_blocks_rfq_bait_switch_and_b2b_vat_overcharge(self) -> None:
        from lab.reverse_auction_tax_returns_guard import compute_rfq_bid_commitment

        rfq_fail = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                rfq_spec={"rfq_id": "rfq_pipe_01", "reserve_price_minor": 25_000},
                rfq_bids=[
                    {
                        "seller_id": "acct_seller_jp_01",
                        "all_in_price_minor": 20_000,
                        "salt": "salt_pipe",
                        "commitment_sha256": compute_rfq_bid_commitment(
                            "acct_seller_jp_01", "rfq_pipe_01", 20_000, "salt_pipe"
                        ),
                    }
                ],
                rfq_checkout_quote={
                    "seller_id": "acct_seller_jp_01",
                    "pre_tax_all_in_minor": 22_000,  # bait-and-switch surcharge
                    "tax_charged_minor": 4_400,
                },
                rfq_tax_context={
                    "seller_country": "JP",
                    "buyer_country": "US",
                    "buyer_is_b2b": True,
                    "buyer_vat_verified": True,
                    "seller_tax_registration_valid": True,
                    "statutory_tax_rate_bps": 1000,
                },
            )
        )
        self.assertFalse(rfq_fail.checkout_committed)
        self.assertEqual(rfq_fail.blocked_at_gate, 3)
        self.assertIn("BAIT_SWITCH_SURCHARGE_INJECTION", rfq_fail.terminal_decision_code)

    def test_gate4_blocks_split_tender_cash_out_and_cost_center_encumbrance_overflow(self) -> None:
        launder_fail = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                split_tender_bundle={
                    "order_id": "ord_pipe_01",
                    "gross_order_minor": 20_000,
                    "promo_discount_minor": 2_000,
                    "max_promo_discount_cap_minor": 5_000,
                    "mutually_exclusive_coupons_stacked": False,
                    "closed_loop_tender_minor": 13_000,
                    "captured_open_loop_minor": 5_000,
                    "refund_requested_minor": 15_000,
                    "proposed_open_loop_refund_minor": 15_000,
                    "proposed_closed_loop_refund_minor": 0,
                }
            )
        )
        self.assertFalse(launder_fail.checkout_committed)
        self.assertEqual(launder_fail.blocked_at_gate, 4)
        self.assertIn("CLOSED_LOOP_CASH_OUT_LAUNDERING_BLOCKED", launder_fail.terminal_decision_code)

    def test_gate4_blocks_x402_soft_confirm_on_high_value_and_stablecoin_depeg(self) -> None:
        depeg_fail = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                stablecoin_peg_and_gas_context={
                    "stablecoin_price_usd": "0.9910",
                    "oracle_published_epoch": 1_760_800_040,
                    "now_epoch": 1_760_800_060,
                    "payment_value_usd": "120.00",
                    "relayer_gas_usd": "0.02",
                }
            )
        )
        self.assertFalse(depeg_fail.checkout_committed)
        self.assertEqual(depeg_fail.blocked_at_gate, 4)
        self.assertIn("STABLECOIN_DEPEG_CIRCUIT_BREAKER", depeg_fail.terminal_decision_code)

    def test_gate6_blocks_marketplace_split_rounding_drift_and_bustout_kyb_risk(self) -> None:
        bustout_fail = execute_unified_agentic_checkout(
            build_golden_pipeline_input(
                seller_kyb_risk_profile={
                    "seller_id": "acct_bustout_01",
                    "kyb_verified": True,
                    "dispute_rate_bps": 88,
                    "gmv_velocity_multiple_30d": "4.5",
                    "current_settlement_gross_minor": 50_000,
                    "applied_reserve_bps": 500,
                    "instant_payout_requested": True,
                }
            )
        )
        self.assertFalse(bustout_fail.checkout_committed)
        self.assertEqual(bustout_fail.blocked_at_gate, 6)
        self.assertIn("ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD", bustout_fail.terminal_decision_code)

    def test_resilience_benchmark_and_seven_card_report_generation(self) -> None:
        suite = run_resilience_benchmark_suite()
        self.assertEqual(suite["total_scenarios"], 14)
        self.assertEqual(suite["ai_native_passed"], 14)
        self.assertEqual(suite["classic_3tier_passed"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "resilience-bench"
            json_p, html_p = write_resilience_report_artifacts(out_dir)
            self.assertTrue(json_p.exists())
            self.assertTrue(html_p.exists())
            html_text = html_p.read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_text)
            for idx in range(1, 8):
                self.assertIn(f"Card {idx} of 7", html_text)
            self.assertEqual(main(["--output-dir", str(out_dir)]), 0)


if __name__ == "__main__":
    unittest.main()
