"""Unit tests for Stage 176 UCP #974/#897/#939/#774 & AP2 #290/#338 guard module."""

from __future__ import annotations

import unittest

from lab.ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_guard import (
    split_ucp_jsonpath,
    ucp_jsonpath_to_pointer,
    validate_ap2_trail_head_window_and_cadence,
    validate_ucp_business_identity_and_jsonpath,
    validate_ucp_catalog_search_and_substitutes,
    validate_ucp_food_checkout_and_fulfillment,
)


class TestStage176Guard(unittest.TestCase):
    def test_ucp_catalog_similarity_and_substitutes(self) -> None:
        # 1. Valid search_catalog with product anchor self-exclusion & batch truncation
        res_search = validate_ucp_catalog_search_and_substitutes(
            operation="search_catalog",
            like_anchors=[
                {"id": "prod_abc123", "kind": "product", "resolved": True},
                {"id": "prod_extra1", "kind": "product", "resolved": True},
                {"id": "prod_extra2", "kind": "product", "resolved": True},
            ],
            max_anchors=2,
            candidate_products=[
                {"id": "prod_abc123", "variants": [{"id": "v1", "price_minor": 12000}]},
                {"id": "prod_def456", "variants": [{"id": "v2", "price_minor": 14000}]},
            ],
            price_max_minor=15000,
        )
        self.assertTrue(res_search.allowed)
        self.assertEqual(res_search.decision_code, "ucp_catalog_similarity_search_ok")
        self.assertEqual(len(res_search.metadata["results"]), 1)
        self.assertEqual(res_search.metadata["results"][0]["id"], "prod_def456")
        self.assertIn("batch_limit_applied", res_search.metadata["warnings"])

        # 2. All anchors unresolved -> must return empty rather than unconstrained browse
        res_unresolved = validate_ucp_catalog_search_and_substitutes(
            operation="search_catalog",
            like_anchors=[{"id": "prod_missing", "kind": "product", "resolved": False}],
            candidate_products=[{"id": "prod_def456", "variants": [{"id": "v2", "price_minor": 14000}]}],
        )
        self.assertFalse(res_unresolved.allowed)
        self.assertEqual(
            res_unresolved.decision_code,
            "ucp_catalog_search_all_anchors_unresolved_empty",
        )

        # 3. Substitute list containing self variant is rejected
        res_self_sub = validate_ucp_catalog_search_and_substitutes(
            operation="get_product",
            requested_id="prod_abc123_size10",
            requested_is_variant=True,
            include=["substitutes"],
            primary_product={"id": "prod_abc123", "variants": [{"id": "prod_abc123_size10", "price_minor": 12000}]},
            raw_substitutes=[
                {"id": "prod_abc123", "variants": [{"id": "prod_abc123_size10", "price_minor": 12000}]}
            ],
        )
        self.assertFalse(res_self_sub.allowed)
        self.assertEqual(
            res_self_sub.decision_code,
            "ucp_catalog_substitute_contains_self_variant",
        )

        # 4. Sibling variant allowed & fail-safe absence when merchant doesn't support substitutes
        res_absent = validate_ucp_catalog_search_and_substitutes(
            operation="get_product",
            requested_id="prod_abc123_size10",
            requested_is_variant=True,
            include=["substitutes"],
            merchant_supports_substitutes=False,
            primary_product={"id": "prod_abc123", "variants": [{"id": "prod_abc123_size10", "price_minor": 12000}]},
        )
        self.assertTrue(res_absent.allowed)
        self.assertEqual(
            res_absent.decision_code,
            "ucp_catalog_include_substitutes_absent_not_offered",
        )
        self.assertFalse(res_absent.metadata["substitutes_key_present"])

    def test_ucp_food_checkout_and_fulfillment(self) -> None:
        res_ok = validate_ucp_food_checkout_and_fulfillment(
            rest_path="/checkout-sessions/chk_food_01",
            establishment_id="est_ramen_01",
            line_items=[
                {
                    "establishment_id": "est_ramen_01",
                    "unit_price_minor": 1500,
                    "quantity": 2,
                    "modifications": [{"name": "extra_egg", "price_minor": 200, "quantity": 1}],
                }
            ],
            fulfillment_method={
                "type": "delivery",
                "destination": {"physical_address": "123 Market St"},
            },
            tax_minor=300,
            delivery_fee_minor=400,
            gratuity_minor=500,
            declared_total_minor=4600,
        )
        self.assertTrue(res_ok.allowed)
        self.assertEqual(res_ok.decision_code, "ucp_food_checkout_and_fulfillment_ok")

        res_multi = validate_ucp_food_checkout_and_fulfillment(
            rest_path="/checkout-sessions/chk_food_01",
            establishment_id="est_ramen_01",
            line_items=[
                {"establishment_id": "est_ramen_01", "unit_price_minor": 1500, "quantity": 1},
                {"establishment_id": "est_sushi_02", "unit_price_minor": 2000, "quantity": 1},
            ],
            fulfillment_method={
                "type": "delivery",
                "destination": {"physical_address": "123 Market St"},
            },
            tax_minor=300,
            delivery_fee_minor=400,
            gratuity_minor=500,
            declared_total_minor=4700,
        )
        self.assertFalse(res_multi.allowed)
        self.assertEqual(res_multi.decision_code, "ucp_food_multi_establishment_forbidden")

        res_plural = validate_ucp_food_checkout_and_fulfillment(
            rest_path="/checkout-sessions/chk_food_01",
            establishment_id="est_ramen_01",
            line_items=[{"establishment_id": "est_ramen_01", "unit_price_minor": 1500, "quantity": 1}],
            fulfillment_method={
                "type": "delivery",
                "destinations": [{"physical_address": "123 Market St"}],
            },
            tax_minor=150,
            delivery_fee_minor=200,
            gratuity_minor=300,
            declared_total_minor=2150,
        )
        self.assertFalse(res_plural.allowed)
        self.assertEqual(res_plural.decision_code, "ucp_food_plural_destinations_forbidden")

    def test_ucp_business_identity_and_jsonpath_and_ap2_trail_head(self) -> None:
        profile = {
            "ucp": {
                "capabilities": {
                    "dev.ucp.common.business": [
                        {
                            "version": "2026-10-23",
                            "config": {
                                "business": {
                                    "name": "Acme Outdoor Co.",
                                    "media": [{"role": "logo", "url": "https://acme.example/logo.png"}],
                                    "links": [{"type": "website", "url": "https://acme.example"}],
                                }
                            },
                        }
                    ],
                    "dev.ucp.common.identity_linking": [
                        {
                            "config": {
                                "providers": {"com.example.attestor": [{"issuer": "https://idp.example"}]},
                                "scopes": {"dev.ucp.shopping.order:read": True},
                            }
                        }
                    ],
                }
            }
        }
        res_biz = validate_ucp_business_identity_and_jsonpath(
            profile=profile,
            extract_expr="$.ucp.capabilities['dev.ucp.common.identity_linking'][0].config.providers['com.example.attestor'][0]",
        )
        self.assertTrue(res_biz.allowed)
        self.assertEqual(
            res_biz.metadata["json_pointer"],
            "/ucp/capabilities/dev.ucp.common.identity_linking/0/config/providers/com.example.attestor/0",
        )
        self.assertEqual(
            split_ucp_jsonpath("$.scopes['dev.ucp.shopping.order:read']"),
            [("scopes", None), ("dev.ucp.shopping.order:read", None)],
        )
        self.assertEqual(
            ucp_jsonpath_to_pointer("$.scopes['dev.ucp.shopping.order:read']"),
            "/scopes/dev.ucp.shopping.order:read",
        )

        # Unquoted dotted reverse-domain key fails closed
        res_unquoted = validate_ucp_business_identity_and_jsonpath(
            profile=profile,
            extract_expr="$.ucp.capabilities.dev.ucp.common.identity_linking[0]",
        )
        self.assertFalse(res_unquoted.allowed)
        self.assertEqual(
            res_unquoted.decision_code,
            "ucp_jsonpath_unquoted_dotted_key_rejected",
        )

        # AP2 trail-head-ref-v1 cadence & window_anchor
        res_ap2_ok = validate_ap2_trail_head_window_and_cadence(
            checkpoints=[
                {"timestamp_s": 1000, "record_count": 2},
                {"timestamp_s": 1300, "record_count": 0, "empty_period_seal": "seal_01"},
            ],
            declared_max_period_s=600,
            records=[
                {"seq": 0, "terminal": True},
                {"seq": 1, "terminal": True},
            ],
            expected_record_count=2,
            window_anchor="certified",
            verdict="complete",
            require_certified_start=True,
            require_terminal_receipt=True,
        )
        self.assertTrue(res_ap2_ok.allowed)
        self.assertEqual(res_ap2_ok.decision_code, "ap2_trail_head_window_and_cadence_ok")

        res_ap2_uncert = validate_ap2_trail_head_window_and_cadence(
            checkpoints=[
                {"timestamp_s": 1000, "record_count": 1},
                {"timestamp_s": 1200, "record_count": 1},
            ],
            declared_max_period_s=600,
            records=[{"seq": 0, "terminal": True}],
            expected_record_count=1,
            window_anchor="uncertified",
            verdict="continuity_only",
            require_certified_start=True,
        )
        self.assertFalse(res_ap2_uncert.allowed)
        self.assertEqual(
            res_ap2_uncert.decision_code,
            "ap2_window_anchor_uncertified_continuity_only_rejected",
        )


if __name__ == "__main__":
    unittest.main()
