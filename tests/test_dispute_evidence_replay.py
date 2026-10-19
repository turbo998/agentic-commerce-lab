import unittest
from pathlib import Path
import tempfile

from lab.dispute_evidence_replay import (
    ACP_APPENDIX_C_GATEWAYS,
    ACP_APPENDIX_C_GATEWAYS_LINKING_DISPUTE_TO_PAYMENT,
    ACP_APPENDIX_C_GATEWAYS_WITH_AGENT_SIGNAL,
    ACP_APPENDIX_C_GATEWAYS_WITH_STRUCTURED_MANDATE_FIELD,
    CryptographicDisputeEvidenceInput,
    compile_cryptographic_dispute_bundle,
    main,
    run_b2b_and_dispute_benchmark_suite,
    write_b2b_benchmark_artifacts,
)


class DisputeEvidenceReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog_payload = (
            '{"id":"sku_ind_sensor_01","price":21000,"hs_code":"8471300100","incoterm":"DDP"}'
        )
        import hashlib

        self.catalog_sha = hashlib.sha256(self.catalog_payload.encode("utf-8")).hexdigest()

    def _valid_input(self, gateway: str = "stripe") -> CryptographicDisputeEvidenceInput:
        return CryptographicDisputeEvidenceInput(
            dispute_reason_code="visa_10_4",
            gateway=gateway,
            mandate_id="mandate_ap2_901",
            mandate_jws_compact="eyJhbGciOiJFUzI1NiJ9.eyJtYXgiOjI4MDAwfQ.sig_ok",
            mandate_max_amount_minor=28000,
            mandate_expires_at=2000,
            settled_at=1500,
            spt_id="spt_live_901",
            spt_bound_seller_id="acct_tokyo_01",
            actual_merchant_id="acct_tokyo_01",
            spt_max_amount_minor=28000,
            settled_amount_minor=27300,
            network_cryptogram_type="visa_vic_tavv",
            network_cryptogram_present=True,
            catalog_shard_payload=self.catalog_payload,
            catalog_expected_sha256=self.catalog_sha,
            buyer_required_ddp=True,
            settled_incoterm="DDP",
            catalog_hs_code="8471300100",
            customs_declared_hs_code="8471309900",
            unpaid_import_duty_minor=0,
            connect_conservation_valid=True,
        )

    def test_all_17_acp_appendix_c_gateways_map_deterministically(self) -> None:
        self.assertEqual(len(ACP_APPENDIX_C_GATEWAYS), 17)
        self.assertEqual(len(ACP_APPENDIX_C_GATEWAYS_LINKING_DISPUTE_TO_PAYMENT), 7)
        self.assertIn("nuvei", ACP_APPENDIX_C_GATEWAYS_LINKING_DISPUTE_TO_PAYMENT)
        self.assertEqual(
            ACP_APPENDIX_C_GATEWAYS["nuvei"]["payment_link_mechanism"],
            "Chargeback DMN TransactionDetails.TransactionId",
        )
        self.assertEqual(len(ACP_APPENDIX_C_GATEWAYS_WITH_AGENT_SIGNAL), 2)
        self.assertEqual(len(ACP_APPENDIX_C_GATEWAYS_WITH_STRUCTURED_MANDATE_FIELD), 0)
        for gw in ACP_APPENDIX_C_GATEWAYS:
            res = compile_cryptographic_dispute_bundle(self._valid_input(gateway=gw))
            self.assertTrue(res.defensible)
            self.assertEqual(res.completeness_score, 100)
            self.assertEqual(res.assigned_liability, "buyer_liable_merchant_wins")
            self.assertEqual(len(res.gateway_payload), 4)

    def test_tamper_detection_and_liability_routing(self) -> None:
        base = self._valid_input()

        # Expired mandate -> agent_platform_liable
        expired = CryptographicDisputeEvidenceInput(**{**base.__dict__, "settled_at": 2500})
        res_exp = compile_cryptographic_dispute_bundle(expired)
        self.assertFalse(res_exp.defensible)
        self.assertEqual(res_exp.assigned_liability, "agent_platform_liable")
        self.assertEqual(res_exp.violation_code, "mandate_expired_prior_to_settlement")

        # SPT cross-merchant replay -> agent_platform_liable
        replay = CryptographicDisputeEvidenceInput(
            **{**base.__dict__, "actual_merchant_id": "acct_other"}
        )
        res_rep = compile_cryptographic_dispute_bundle(replay)
        self.assertFalse(res_rep.defensible)
        self.assertEqual(res_rep.assigned_liability, "agent_platform_liable")
        self.assertEqual(res_rep.violation_code, "spt_cross_merchant_replay_mismatch")

        # Catalog sha-256 mismatch -> merchant_liable
        tampered_cat = CryptographicDisputeEvidenceInput(
            **{**base.__dict__, "catalog_expected_sha256": "0" * 64}
        )
        res_cat = compile_cryptographic_dispute_bundle(tampered_cat)
        self.assertFalse(res_cat.defensible)
        self.assertEqual(res_cat.assigned_liability, "merchant_liable")
        self.assertEqual(res_cat.violation_code, "ucp_catalog_repr_digest_mismatch")

        # Undisclosed DDU duty on DDP mandate -> agent_platform_liable
        ddu_leak = CryptographicDisputeEvidenceInput(
            **{**base.__dict__, "settled_incoterm": "DAP", "unpaid_import_duty_minor": 3800}
        )
        res_ddu = compile_cryptographic_dispute_bundle(ddu_leak)
        self.assertFalse(res_ddu.defensible)
        self.assertEqual(res_ddu.assigned_liability, "agent_platform_liable")
        self.assertEqual(res_ddu.violation_code, "undisclosed_ddu_customs_duty_on_ddp_mandate")

    def test_b2b_and_dispute_seven_card_report_generation(self) -> None:
        suite = run_b2b_and_dispute_benchmark_suite()
        self.assertEqual(suite["total_scenarios"], 10)
        self.assertEqual(suite["ai_native_passed"], 10)
        self.assertEqual(suite["classic_3tier_passed"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "b2b-bench"
            self.assertEqual(main(["--output-dir", str(out_dir)]), 0)
            json_path, html_path = write_b2b_benchmark_artifacts(out_dir)
            self.assertTrue(json_path.exists())
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_text)
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', html_text)


if __name__ == "__main__":
    unittest.main()
