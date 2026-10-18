import tempfile
import unittest
from pathlib import Path

from lab.cross_border_b2b_guard import SellerSplitAllocation
from lab.protocol_readiness_auditor import (
    EnterprisePipelineAuditInput,
    audit_enterprise_agentic_checkout_pipeline,
    main,
    run_demo,
    write_workbench_artifact,
)
from lab.workload_arch_bench import compute_rfc9530_sha256


class ProtocolReadinessAuditorTests(unittest.TestCase):
    def _base_input(self) -> EnterprisePipelineAuditInput:
        shard_bytes = b'{"id":"sku_ind_sensor_01","price":21000,"hs_code":"8471300100"}'
        shard_url = "https://merchant.example/feeds/catalog-001.jsonl.gz"
        return EnterprisePipelineAuditInput(
            as_of_date="2026-10-19",
            mcp_auth_class="stripe_agent_key",
            charge_type="separate_charges_and_transfers",
            seller_profile_owner="platform",
            has_on_behalf_of=False,
            stripe_account_header=None,
            connected_account_id="acct_tokyo_01",
            buyer_charge_minor=27300,
            allocations=[
                SellerSplitAllocation("acct_tokyo_01", 27300, 24570, 2730, "JPY", "150.00", "150.15")
            ],
            now_epoch=100,
            fx_quote_expires_at=200,
            catalog_manifest={
                "files": [
                    {
                        "url": shard_url,
                        "format": "jsonl+gzip",
                        "digest": compute_rfc9530_sha256(shard_bytes),
                    }
                ]
            },
            fetched_shards={shard_url: shard_bytes},
            parsed_primary_records=[{"id": "sku_ind_sensor_01", "price": 21000}],
            structured_terms_amount_minor=27300,
            summary_amount_minor=27300,
            consequential_confirmed=True,
            gross_transaction_usd="273.00",
            platform_take_rate_bps=1000,
            input_tokens=8000,
            output_tokens=1500,
            payment_rail="stripe_spt_card",
            buyer_mandate_max_landed_minor=28000,
            buyer_requires_ddp=True,
            proposed_incoterm="DDP",
            catalog_hs_code="8471300100",
            proposed_hs_code="8471309900",
            fob_merchandise_minor=21000,
            freight_insurance_minor=2500,
            estimated_duty_tax_minor=3800,
            quoted_checkout_total_minor=27300,
            dispute_gateway="stripe",
            mandate_jws_compact="eyJhbGciOiJFUzI1NiJ9.eyJtYXgiOjI4MDAwfQ.sig_ok",
            network_cryptogram_type="visa_vic_tavv",
        )

    def test_healthy_enterprise_pipeline_scores_100_with_42_days_left(self) -> None:
        res = audit_enterprise_agentic_checkout_pipeline(self._base_input())
        self.assertTrue(res.ready_for_production)
        self.assertEqual(res.overall_readiness_score, 100)
        self.assertEqual(res.days_until_stripe_mcp_cutoff, 42)
        self.assertEqual(res.blocking_reasons, [])
        self.assertEqual(res.gateway_api_method, "stripe.disputes.update")

    def test_legacy_mcp_key_and_multi_phase_blockers_detected(self) -> None:
        base = self._base_input()
        failing = EnterprisePipelineAuditInput(
            **{
                **base.__dict__,
                "mcp_auth_class": "restricted_api_key_rak",
                "summary_amount_minor": 19900,  # summary != terms
                "proposed_incoterm": "DAP",  # DDP downgrade
            }
        )
        res = audit_enterprise_agentic_checkout_pipeline(failing)
        self.assertFalse(res.ready_for_production)
        self.assertLess(res.overall_readiness_score, 60)
        self.assertIn("phase_a:mcp_legacy_key_requires_migration_within_42_days", res.blocking_reasons)
        self.assertIn("phase_b:summary_terms_amount_mismatch", res.blocking_reasons)
        self.assertIn("phase_c:incoterm_downgrade_from_ddp_forbidden", res.blocking_reasons)

    def test_workbench_html_and_cli_generation(self) -> None:
        demo = run_demo()
        self.assertTrue(demo["ready_for_production"])
        self.assertEqual(demo["overall_readiness_score"], 100)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "workbench"
            self.assertEqual(main(["--output-dir", str(out_dir)]), 0)
            html_path = write_workbench_artifact(out_dir)
            self.assertTrue(html_path.exists())
            text = html_path.read_text(encoding="utf-8")
            self.assertIn("Stripe MCP Cutoff: 2026-11-30 (42 Days Left)", text)
            self.assertIn("Interactive FinOps", text)


if __name__ == "__main__":
    unittest.main()
