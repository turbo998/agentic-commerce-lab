import json
from pathlib import Path
import tempfile
import unittest

from lab.workload_arch_bench import (
    audit_mpp_streaming_session,
    compile_atdrp_card_rail_evidence,
    compute_rfc9530_sha256,
    evaluate_ap2_fiduciary_circuit_breaker,
    main,
    render_seven_card_html,
    run_six_plane_benchmark_suite,
    verify_connect_spt_routing,
    verify_spt_agent_state_transition,
    verify_spt_resolve_single_use,
    verify_ucp_catalog_feed_snapshot,
)


class WorkloadArchBenchTests(unittest.TestCase):
    def test_connect_spt_routing_direct_and_destination(self) -> None:
        direct_ok = verify_connect_spt_routing(
            charge_type="direct",
            seller_profile_owner="connected_account",
            stripe_account_header="acct_connected_123",
            connected_account_id="acct_connected_123",
        )
        self.assertTrue(direct_ok.valid)
        self.assertTrue(direct_ok.requires_stripe_account_header)

        direct_bad_profile = verify_connect_spt_routing(
            charge_type="direct",
            seller_profile_owner="platform",
            stripe_account_header="acct_connected_123",
        )
        self.assertFalse(direct_bad_profile.valid)
        self.assertEqual(
            direct_bad_profile.reason,
            "direct_charge_requires_connected_account_business_profile",
        )

        direct_bad_header = verify_connect_spt_routing(
            charge_type="direct",
            seller_profile_owner="connected_account",
            stripe_account_header=None,
        )
        self.assertFalse(direct_bad_header.valid)
        self.assertEqual(
            direct_bad_header.reason,
            "direct_charge_missing_or_mismatched_stripe_account_header",
        )

        dest_obo_ok = verify_connect_spt_routing(
            charge_type="destination",
            seller_profile_owner="connected_account",
            has_on_behalf_of=True,
        )
        self.assertTrue(dest_obo_ok.valid)
        self.assertEqual(dest_obo_ok.recommended_business_profile_owner, "connected_account")

        dest_obo_bad = verify_connect_spt_routing(
            charge_type="destination",
            seller_profile_owner="platform",
            has_on_behalf_of=True,
            strict_obo_recommendation=True,
        )
        self.assertFalse(dest_obo_bad.valid)
        self.assertEqual(
            dest_obo_bad.reason,
            "on_behalf_of_recommends_connected_account_business_profile",
        )

    def test_spt_resolve_single_use_and_rsa_block_slices(self) -> None:
        ledger: set[str] = set()
        first = verify_spt_resolve_single_use(
            "spt_grant_01",
            {
                "type": "agentic_token",
                "network_rail": "mastercard_agent_pay",
                "cryptogram_type": "TAVV",
                "cryptogram": "AgAAAAAAAIR8CQr5AA==",
                "encryption_block_fields": ["pan:0:16", "exp_month:16:2", "exp_year:18:4"],
            },
            resolved_token_ledger=ledger,
            decrypted_block="5555555555554444092029",
        )
        self.assertTrue(first.allowed)
        self.assertEqual(
            first.extracted_fields,
            {"pan": "5555555555554444", "exp_month": "09", "exp_year": "2029"},
        )

        second = verify_spt_resolve_single_use(
            "spt_grant_01",
            {
                "type": "agentic_token",
                "network_rail": "mastercard_agent_pay",
                "cryptogram_type": "TAVV",
                "cryptogram": "AgAAAAAAAIR8CQr5AA==",
            },
            resolved_token_ledger=ledger,
        )
        self.assertFalse(second.allowed)
        self.assertEqual(second.reason, "single_use_resolve_replayed")

        overlap = verify_spt_resolve_single_use(
            "spt_grant_02",
            {
                "type": "fpan",
                "network_rail": "raw_fpan",
                "encryption_block_fields": ["pan:0:16", "cvv:14:3"],
            },
            resolved_token_ledger=ledger,
            decrypted_block="4111111111111234999",
        )
        self.assertFalse(overlap.allowed)
        self.assertEqual(overlap.reason, "encryption_block_overlapping_slices")

    def test_spt_agent_state_machine_and_ap2_fcb(self) -> None:
        step_up = verify_spt_agent_state_transition("active", "step_up_3ds_required")
        self.assertTrue(step_up.allowed)
        self.assertEqual(step_up.next_status, "requires_action")

        blocked_charge = verify_spt_agent_state_transition("requires_action", "charge_attempt")
        self.assertFalse(blocked_charge.allowed)
        self.assertEqual(blocked_charge.reason, "charge_attempt_requires_active_spt")

        recovered = verify_spt_agent_state_transition(
            "requires_action", "handle_next_action_succeeded", hashed_value="3ds_hash_ok"
        )
        self.assertTrue(recovered.allowed)
        self.assertEqual(recovered.next_status, "active")

        deactivated = verify_spt_agent_state_transition("active", "deactivate")
        self.assertTrue(deactivated.allowed)
        self.assertEqual(deactivated.next_status, "deactivated")

        resurrect = verify_spt_agent_state_transition("deactivated", "charge_attempt")
        self.assertFalse(resurrect.allowed)
        self.assertEqual(resurrect.reason, "deactivated_spt_is_terminal")

        fcb_trip = evaluate_ap2_fiduciary_circuit_breaker(
            current_state="CLOSED",
            amount_minor=20000,
            single_tx_limit_minor=10000,
            cumulative_spend_minor=45000,
            cumulative_limit_minor=50000,
            tx_count_in_window=5,
            max_tx_per_window=5,
            merchant_category="luxury",
            allowed_categories={"groceries"},
        )
        self.assertFalse(fcb_trip.allowed)
        self.assertEqual(fcb_trip.next_state, "OPEN")
        self.assertIn("VALUE_THRESHOLD", fcb_trip.tripped_conditions)

        fcb_half = evaluate_ap2_fiduciary_circuit_breaker(
            current_state="OPEN",
            amount_minor=1000,
            single_tx_limit_minor=10000,
            cumulative_spend_minor=1000,
            cumulative_limit_minor=50000,
            tx_count_in_window=1,
            max_tx_per_window=5,
            merchant_category="groceries",
            allowed_categories={"groceries"},
            human_recovery_mandate_verified=True,
        )
        self.assertTrue(fcb_half.allowed)
        self.assertEqual(fcb_half.next_state, "HALF_OPEN")

        fcb_closed = evaluate_ap2_fiduciary_circuit_breaker(
            current_state="HALF_OPEN",
            amount_minor=1000,
            single_tx_limit_minor=10000,
            cumulative_spend_minor=1000,
            cumulative_limit_minor=50000,
            tx_count_in_window=1,
            max_tx_per_window=5,
            merchant_category="groceries",
            allowed_categories={"groceries"},
            probe_succeeded=True,
        )
        self.assertTrue(fcb_closed.allowed)
        self.assertEqual(fcb_closed.next_state, "CLOSED")

    def test_ucp_catalog_feed_digest_and_variant_merge(self) -> None:
        raw = b'{"id":"sku_1"}\n'
        digest = compute_rfc9530_sha256(raw)
        bad = verify_ucp_catalog_feed_snapshot(
            previous_catalog={"sku_1": {"id": "sku_1"}, "sku_2": {"id": "sku_2"}},
            manifest={"files": [{"url": "https://m.example/f1.jsonl.gz", "format": "jsonl+gzip", "digest": digest}]},
            fetched_shards={"https://m.example/f1.jsonl.gz": b"corrupted"},
            parsed_primary_records=[{"id": "sku_1"}],
        )
        self.assertFalse(bad.valid)
        self.assertFalse(bad.deletions_permitted)
        self.assertEqual(len(bad.merged_records), 2)

        ok = verify_ucp_catalog_feed_snapshot(
            previous_catalog={"sku_1": {"id": "sku_1"}, "sku_2": {"id": "sku_2"}},
            manifest={"files": [{"url": "https://m.example/f1.jsonl.gz", "format": "jsonl+gzip", "digest": digest}]},
            fetched_shards={"https://m.example/f1.jsonl.gz": raw},
            parsed_primary_records=[
                {"id": "sku_1", "variants": [{"id": "v1", "price": 100}, {"id": "v2", "price": 200}]}
            ],
            supplemental_records=[{"id": "sku_1", "variants": [{"id": "v2", "price": 180}]}],
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.deletions_permitted)
        self.assertEqual(len(ok.merged_records), 1)
        self.assertEqual(ok.merged_records["sku_1"]["variants"][0]["price"], 100)
        self.assertEqual(ok.merged_records["sku_1"]["variants"][1]["price"], 180)

    def test_atdrp_card_rail_evidence_and_mpp_forfeiture(self) -> None:
        ev = compile_atdrp_card_rail_evidence(
            gateway="braintree",
            dispute_payment_id="bt_tx_1",
            evidence_pack_payment_id="bt_tx_1",
            digest_ok=True,
            rfc3161_verified=True,
            mandate_jws="jws_token",
            Checkout_hash="sha256:abc",
        )
        self.assertTrue(ev.admissible)
        self.assertEqual(ev.payment_agent_signal_field, "transaction.facilitator_details")
        self.assertIsNone(ev.issuer_structured_mandate_field)

        mpp_bad = audit_mpp_streaming_session(
            unit_price_usd="0.000350",
            units_per_settlement_cycle=50,
            total_units_consumed=125,
            deposit_usd="1.000000",
        )
        self.assertTrue(mpp_bad.valid)
        self.assertFalse(mpp_bad.zero_forfeiture_schedule)
        self.assertEqual(mpp_bad.settled_usd, "0.02")
        self.assertEqual(mpp_bad.forfeited_subcent_usd, "0.023750")
        self.assertEqual(mpp_bad.recommended_units_per_settlement, 200)

        mpp_good = audit_mpp_streaming_session(
            unit_price_usd="0.000350",
            units_per_settlement_cycle=200,
            total_units_consumed=400,
            deposit_usd="1.000000",
        )
        self.assertTrue(mpp_good.valid)
        self.assertTrue(mpp_good.zero_forfeiture_schedule)
        self.assertEqual(mpp_good.forfeited_subcent_usd, "0.000000")

    def test_suite_and_seven_card_html_generation(self) -> None:
        report = run_six_plane_benchmark_suite()
        self.assertEqual(report["total_scenarios"], 12)
        self.assertEqual(report["ai_native_passed"], 12)
        html_doc = render_seven_card_html(report)
        for card_idx in range(1, 8):
            self.assertIn(f'id="card-{card_idx}"', html_doc)
        self.assertIn("Content-Security-Policy", html_doc)

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            rc = main(["--output-dir", str(out_path)])
            self.assertEqual(rc, 0)
            saved_report = json.loads((out_path / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_report["ai_native_passed"], 12)
            self.assertTrue((out_path / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
