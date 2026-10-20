"""Unit tests for Stage 58 protocol and benchmark guards."""

from __future__ import annotations

import unittest

from lab.ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_guard import (
    TAU2_LEGACY_RCS_SEEDS,
    TAU2_RCS_V3_SEEDS,
    TAU2_VOICE_V2_LANGUAGES,
    compute_sha256_b64url,
    verify_acp_item_url_and_feed_upsert_guard,
    verify_ap2_multihop_present_and_atomic_consumption_guard,
    verify_tau2_voice_v2_banking_entity_and_crossed_pass3_guard,
    verify_ucp_purchase_options_and_seller_offers_guard,
)


class TestStage58ProtocolAndVoiceGuards(unittest.TestCase):
    def _sample_catalog_variant(self) -> dict:
        return {
            "id": "gid://merchant/Variant/coffee-1kg",
            "price": 2400,
            "purchase_options": [
                {
                    "id": "opt_onetime",
                    "title": "One-time purchase",
                    "price": 2400,
                },
                {
                    "id": "opt_sub_monthly",
                    "title": "Subscribe & save 15%",
                    "description": "Delivered monthly, cancel anytime",
                    "price": 2040,
                    "list_price": 2400,
                },
            ],
            "offers": [
                {
                    "seller": {"domain": "roaster-a.example.com", "name": "Roaster A"},
                    "item_id": "roaster_a_sku_99",
                    "price": 2400,
                },
                {
                    "seller": {"domain": "roaster-b.example.com", "name": "Roaster B"},
                    "item_id": "roaster_b_sku_77",
                    "price": 2350,
                },
            ],
        }

    def test_ucp_purchase_options_and_seller_offers_happy_path_and_304(self) -> None:
        variant = self._sample_catalog_variant()
        res = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="update",
            request_line_item={
                "item": {"id": "roaster_a_sku_99"},
                "selected_purchase_option_id": "opt_sub_monthly",
            },
            catalog_variant=variant,
            response_line_item={
                "item": {"id": "roaster_a_sku_99", "price": 2040},
                "purchase_options": variant["purchase_options"],
                "selected_purchase_option_id": "opt_sub_monthly",
            },
            order_line_item={
                "purchase_option": {
                    "id": "opt_sub_monthly",
                    "title": "Subscribe & save 15%",
                }
            },
            selected_offer_seller_domain="roaster-a.example.com",
            profile_http_status=304,
            is_conditional_request=True,
            mcp_tool_schema_defs={"agent": {"type": "object"}},
            mcp_ucp_agent_ref="#/$defs/agent",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "UCP_PURCHASE_OPTIONS_AND_SELLER_OFFERS_VERIFIED")
        self.assertEqual(res.resolved_purchase_option_id, "opt_sub_monthly")
        self.assertEqual(res.resolved_line_price_minor, 2040)
        self.assertEqual(res.resolved_mor_domain, "roaster-a.example.com")
        self.assertEqual(res.resolved_checkout_item_id, "roaster_a_sku_99")

    def test_ucp_purchase_options_and_offers_rejections(self) -> None:
        variant = self._sample_catalog_variant()
        # 1. Forbidden 302 redirect on profile fetch (PR #933)
        r_302 = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="create",
            request_line_item={"item": {"id": "roaster_a_sku_99"}},
            catalog_variant=variant,
            profile_http_status=302,
        )
        self.assertFalse(r_302.allowed)
        self.assertEqual(r_302.decision_code, "UCP_FORBIDDEN_HTTP_REDIRECT")

        # 2. Reserved ucp_ prefix in MCP $defs (PR #831 W007)
        r_w007 = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="create",
            request_line_item={"item": {"id": "roaster_a_sku_99"}},
            catalog_variant=variant,
            mcp_tool_schema_defs={"ucp_agent": {"type": "object"}},
        )
        self.assertFalse(r_w007.allowed)
        self.assertEqual(r_w007.decision_code, "UCP_SCHEMA_W007_RESERVED_UCP_PREFIX_IN_DEFS")

        # 3. Using variant.id instead of offers[].item_id at checkout (PR #811)
        r_var_id = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="create",
            request_line_item={"item": {"id": "gid://merchant/Variant/coffee-1kg"}},
            catalog_variant=variant,
        )
        self.assertFalse(r_var_id.allowed)
        self.assertEqual(r_var_id.decision_code, "UCP_MULTI_SELLER_VARIANT_ID_USED_AT_CHECKOUT")

        # 4. Silent substitution of stale purchase option without warning (PR #901)
        r_stale = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="update",
            request_line_item={
                "item": {"id": "roaster_a_sku_99"},
                "selected_purchase_option_id": "opt_withdrawn_999",
            },
            catalog_variant=variant,
            response_warnings=[],
        )
        self.assertFalse(r_stale.allowed)
        self.assertEqual(r_stale.decision_code, "UCP_STALE_PURCHASE_OPTION_SILENT_SUBSTITUTION_FORBIDDEN")

        # 5. Sending selected_purchase_option_id on complete_checkout (PR #901)
        r_complete = verify_ucp_purchase_options_and_seller_offers_guard(
            operation="complete",
            request_line_item={
                "item": {"id": "roaster_a_sku_99"},
                "selected_purchase_option_id": "opt_onetime",
            },
            catalog_variant=variant,
        )
        self.assertFalse(r_complete.allowed)
        self.assertEqual(r_complete.decision_code, "UCP_SELECTED_PURCHASE_OPTION_OMIT_ON_COMPLETE")

    def test_acp_item_url_and_feed_upsert_guards(self) -> None:
        cross_map = {"sku_shared_1": {"brand-a.example.com", "brand-b.example.com"}}
        ok = verify_acp_item_url_and_feed_upsert_guard(
            checkout_items=[
                {
                    "id": "sku_shared_1",
                    "url": "https://brand-b.example.com/products/sku-shared-1",
                }
            ],
            cross_listed_sku_storefronts=cross_map,
            feed_server_url="https://agent.example.com",
            upsert_products_request={
                "products": [{"id": "prod_1", "variants": [{"id": "var_1"}]}]
            },
            upsert_products_response={"id": "feed_01", "accepted": True},
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.resolved_brand_storefront, "brand-b.example.com")

        # Missing Item.url on cross-listed SKU (PR #281)
        missing_url = verify_acp_item_url_and_feed_upsert_guard(
            checkout_items=[{"id": "sku_shared_1"}],
            cross_listed_sku_storefronts=cross_map,
        )
        self.assertFalse(missing_url.allowed)
        self.assertEqual(missing_url.decision_code, "ACP_CROSS_LISTED_SKU_REQUIRES_ITEM_URL")

        # Merchant-hosted Feed API server URL & empty variants (PR #256)
        bad_feed = verify_acp_item_url_and_feed_upsert_guard(
            checkout_items=[
                {
                    "id": "sku_shared_1",
                    "url": "https://brand-a.example.com/products/sku-shared-1",
                }
            ],
            cross_listed_sku_storefronts=cross_map,
            feed_server_url="https://merchant.example.com",
        )
        self.assertFalse(bad_feed.allowed)
        self.assertEqual(bad_feed.decision_code, "ACP_FEED_SERVER_MUST_BE_AGENT_HOSTED")

    def test_ap2_multihop_present_and_atomic_consumption_guards(self) -> None:
        hop0 = "eyJ0eXAiOiJKV1QifQ.hop0~cnf:key0~limit:5000~"
        hop1 = "eyJ0eXAiOiJKV1QifQ.hop1~cnf:key1~merchant:roaster_a~internal_note:secret~"
        chain = f"{hop0.removesuffix('~')}~~{hop1}"
        checkout_jwt = "eyJhbGciOiJFUzI1NiJ9.checkout_payload_A.sig"
        checkout_hash = compute_sha256_b64url(checkout_jwt)
        reserved: set[str] = set()

        res = verify_ap2_multihop_present_and_atomic_consumption_guard(
            mandate_chain_token=chain,
            claims_to_disclose={"merchant"},
            new_presentation_jwt="eyJ0eXAiOiJraitqd3QifQ.pres2",
            expected_prior_hop_digests={0: compute_sha256_b64url(hop0.removesuffix("~"))},
            presented_checkout_jwt=checkout_jwt,
            closed_mandate_checkout_hash=checkout_hash,
            expected_checkout_hash_arg=None,
            payment_mandate_hash="pm_hash_001",
            checkout_transaction_id="chk_tx_001",
            reserved_keys=reserved,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.hop_count, 3)
        self.assertNotIn("internal_note", res.wire_presentation_token or "")
        self.assertTrue((res.wire_presentation_token or "").startswith(hop0.removesuffix("~") + "~~"))

        # Replay fails with mandate_already_used (PR #347)
        replay = verify_ap2_multihop_present_and_atomic_consumption_guard(
            mandate_chain_token=chain,
            claims_to_disclose={"merchant"},
            new_presentation_jwt="eyJ0eXAiOiJraitqd3QifQ.pres2",
            presented_checkout_jwt=checkout_jwt,
            closed_mandate_checkout_hash=checkout_hash,
            payment_mandate_hash="pm_hash_001",
            checkout_transaction_id="chk_tx_002",
            reserved_keys=reserved,
        )
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.decision_code, "mandate_already_used")

        # Checkout substitution caught even when expected_checkout_hash_arg is None (PR #359)
        sub = verify_ap2_multihop_present_and_atomic_consumption_guard(
            mandate_chain_token=chain,
            claims_to_disclose={"merchant"},
            new_presentation_jwt="eyJ0eXAiOiJraitqd3QifQ.pres2",
            presented_checkout_jwt="eyJhbGciOiJFUzI1NiJ9.checkout_payload_B.sig",
            closed_mandate_checkout_hash=checkout_hash,
            expected_checkout_hash_arg=None,
            payment_mandate_hash="pm_hash_009",
            checkout_transaction_id="chk_tx_009",
            reserved_keys=reserved,
        )
        self.assertFalse(sub.allowed)
        self.assertEqual(sub.decision_code, "AP2_PRESENTED_CHECKOUT_HASH_MISMATCH")

    def test_tau2_voice_v2_submission_and_crossed_pass3_guards(self) -> None:
        pins = {lang: f"pin_{lang}_v1" for lang in TAU2_VOICE_V2_LANGUAGES}
        cells = [
            {
                "language": lang,
                "binding_revision": pins[lang],
                "scored_calls": 97,
                "missing_rewards": 0,
                "errored_rewards": 0,
                "unscored_rewards": 0,
                "unjudged_applicable_measures": 0,
            }
            for lang in TAU2_VOICE_V2_LANGUAGES
        ]
        fps = {lang: f"sha256_{lang}" for lang in TAU2_VOICE_V2_LANGUAGES}
        ok = verify_tau2_voice_v2_banking_entity_and_crossed_pass3_guard(
            benchmark_version="voice-v2-banking",
            task_subset_name="banking_knowledge_97",
            cells=cells,
            expected_binding_revisions=pins,
            max_call_duration_sec=180.0,
            pass3_mode="crossed",
            pass3_seeds=TAU2_RCS_V3_SEEDS,
            reused_regular_seed=42,
            regular_results_read_only=True,
            gemini_38_extended_thinking=True,
            google_genai_version=(2, 26),
            has_benchmark_diagnostics_json=True,
            recorded_verdict_fingerprints=fps,
            recomputed_verdict_fingerprints=dict(fps),
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.total_expected_calls, 582)

        # Reject legacy RCS seeds (9401, 9402, 9403) (PR #639)
        bad_seeds = verify_tau2_voice_v2_banking_entity_and_crossed_pass3_guard(
            benchmark_version="voice-v2-banking",
            task_subset_name="banking_knowledge_97",
            cells=cells,
            expected_binding_revisions=pins,
            max_call_duration_sec=180.0,
            pass3_mode="crossed",
            pass3_seeds=TAU2_LEGACY_RCS_SEEDS,
            recorded_verdict_fingerprints=fps,
            recomputed_verdict_fingerprints=dict(fps),
        )
        self.assertFalse(bad_seeds.allowed)
        self.assertEqual(bad_seeds.decision_code, "TAU2_CROSSED_PASS3_SEEDS_MUST_MATCH_RCS_V3")


if __name__ == "__main__":
    unittest.main()
