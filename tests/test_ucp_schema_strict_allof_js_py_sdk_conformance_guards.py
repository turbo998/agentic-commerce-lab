"""Unit tests for Stage 250 UCP Schema, JS SDK, Python SDK, and Conformance guards."""

from __future__ import annotations

import unittest

from lab.ucp_schema_strict_allof_js_py_sdk_conformance_guards import (
    evaluate_ucp_conformance_checkout_lifecycle_status_band_guard,
    evaluate_ucp_conformance_discovery_urls_reachability_guard,
    evaluate_ucp_conformance_postal_address_canonical_fields_guard,
    evaluate_ucp_conformance_shopping_agent_profile_capabilities_guard,
    evaluate_ucp_js_sdk_dependent_required_and_discovery_profile_guard,
    evaluate_ucp_js_sdk_fulfillment_destination_binding_isolation_guard,
    evaluate_ucp_js_sdk_open_schema_catchall_guard,
    evaluate_ucp_js_sdk_open_union_not_enum_guard,
    evaluate_ucp_python_sdk_aware_datetime_and_release_sha_guard,
    evaluate_ucp_python_sdk_dotted_capability_role_containers_guard,
    evaluate_ucp_python_sdk_jwk_public_key_guard,
    evaluate_ucp_python_sdk_single_module_and_dependent_required_guard,
    evaluate_ucp_schema_open_strict_and_lint_quiet_guard,
    evaluate_ucp_schema_openapi_five_pass_compiler_guard,
    evaluate_ucp_schema_strict_allof_closing_guard,
    evaluate_ucp_schema_versioned_urls_and_default_direction_guard,
)


class TestUcpSchemaStrictAllofJsPySdkConformanceGuards(unittest.TestCase):
    def test_ucp_schema_and_js_sdk_guards_pr01_to_pr08(self) -> None:
        # PR-01
        ok1 = evaluate_ucp_schema_open_strict_and_lint_quiet_guard(
            validation_mode="strict",
            schema_explicit_additional_properties=None,
            payload_has_undeclared_field=False,
            lint_quiet=True,
            lint_strict=True,
            lint_warnings_count=2,
            diagnostics_printed=0,
            summary_line_printed=True,
            process_exit_code=1,
        )
        self.assertTrue(ok1["allowed"])
        bad1 = evaluate_ucp_schema_open_strict_and_lint_quiet_guard(
            validation_mode="strict",
            schema_explicit_additional_properties=None,
            payload_has_undeclared_field=True,
            lint_quiet=True,
            lint_strict=True,
            lint_warnings_count=2,
            diagnostics_printed=0,
            summary_line_printed=False,
            process_exit_code=0,
        )
        self.assertFalse(bad1["allowed"])

        # PR-02
        ok2 = evaluate_ucp_schema_strict_allof_closing_guard(
            strict_mode=True,
            has_allof_composition=True,
            source_unevaluated_properties=True,
            source_additional_properties=True,
            resolved_unevaluated_properties=False,
            resolved_additional_properties=False,
            undeclared_root_field_rejected=True,
        )
        self.assertTrue(ok2["allowed"])
        bad2 = evaluate_ucp_schema_strict_allof_closing_guard(
            strict_mode=True,
            has_allof_composition=True,
            source_unevaluated_properties=True,
            source_additional_properties=True,
            resolved_unevaluated_properties=True,
            resolved_additional_properties=True,
            undeclared_root_field_rejected=False,
        )
        self.assertFalse(bad2["allowed"])

        # PR-03
        ok3 = evaluate_ucp_schema_versioned_urls_and_default_direction_guard(
            schema_version_dir="2026-04-08",
            schema_id_urls=["https://ucp.dev/2026-04-08/schemas/shopping/checkout.json"],
            capability_schema_urls=["https://ucp.dev/2026-04-08/schemas/shopping/order.json"],
            explicit_schema_flag_passed=True,
            request_flag_passed=False,
            response_flag_passed=False,
            resolved_direction="request",
        )
        self.assertTrue(ok3["allowed"])
        bad3 = evaluate_ucp_schema_versioned_urls_and_default_direction_guard(
            schema_version_dir="2026-04-08",
            schema_id_urls=["https://ucp.dev/schemas/shopping/checkout.json"],
            capability_schema_urls=[],
            explicit_schema_flag_passed=True,
            request_flag_passed=False,
            response_flag_passed=False,
            resolved_direction=None,
        )
        self.assertFalse(bad3["allowed"])

        # PR-04
        ok4 = evaluate_ucp_schema_openapi_five_pass_compiler_guard(
            merged_spec_versions=["2026-04-08", "2026-04-08"],
            schema_base_configured=True,
            polarized_components_emitted=["Checkout_Create_Request", "Checkout_Complete_Response"],
            remaining_ucp_annotations_count=0,
            external_file_refs_remaining=0,
            unreachable_schemas_remaining=0,
            synthesized_rest_paths=["/checkouts", "/checkouts/{id}", "/checkouts/{id}/complete"],
        )
        self.assertTrue(ok4["allowed"])
        bad4 = evaluate_ucp_schema_openapi_five_pass_compiler_guard(
            merged_spec_versions=["2026-01-23", "2026-04-08"],
            schema_base_configured=False,
            polarized_components_emitted=["Checkout"],
            remaining_ucp_annotations_count=1,
            external_file_refs_remaining=1,
            unreachable_schemas_remaining=2,
            synthesized_rest_paths=["/checkouts"],
        )
        self.assertFalse(bad4["allowed"])

        # PR-05
        ok5 = evaluate_ucp_js_sdk_open_union_not_enum_guard(
            codegen_backend="ucp-schema-generate-types-zod",
            known_enum_Literals=["subtotal", "tax", "total"],
            catchall_has_not_enum_refine=True,
            union_base_includes_open_catchall=False,
            extension_branch_matched_for_extension_value=True,
        )
        self.assertTrue(ok5["allowed"])
        bad5 = evaluate_ucp_js_sdk_open_union_not_enum_guard(
            codegen_backend="ucp-schema-generate-types-zod",
            known_enum_Literals=["subtotal", "tax", "total"],
            catchall_has_not_enum_refine=False,
            union_base_includes_open_catchall=True,
            extension_branch_matched_for_extension_value=False,
        )
        self.assertFalse(bad5["allowed"])

        # PR-06
        ok6 = evaluate_ucp_js_sdk_open_schema_catchall_guard(
            open_schemas_total=71,
            open_schemas_with_catchall_count=71,
            parsed_credential_payload={"type": "token", "token": "tok_ucp_live_998"},
            closed_schema_rejected_undeclared=True,
        )
        self.assertTrue(ok6["allowed"])
        bad6 = evaluate_ucp_js_sdk_open_schema_catchall_guard(
            open_schemas_total=71,
            open_schemas_with_catchall_count=0,
            parsed_credential_payload={"type": "token"},
            closed_schema_rejected_undeclared=True,
        )
        self.assertFalse(bad6["allowed"])

        # PR-07
        ok7 = evaluate_ucp_js_sdk_fulfillment_destination_binding_isolation_guard(
            unconstrained_id_type_penalized_in_contest=True,
            fulfillment_destination_members=["ShippingDestinationSchema", "RetailLocationSchema"],
            malformed_shipping_error_mentions_reverse_domain_regex=False,
        )
        self.assertTrue(ok7["allowed"])
        bad7 = evaluate_ucp_js_sdk_fulfillment_destination_binding_isolation_guard(
            unconstrained_id_type_penalized_in_contest=False,
            fulfillment_destination_members=["ShippingDestinationSchema", "BindingSchema"],
            malformed_shipping_error_mentions_reverse_domain_regex=True,
        )
        self.assertFalse(bad7["allowed"])

        # PR-08
        ok8 = evaluate_ucp_js_sdk_dependent_required_and_discovery_profile_guard(
            dependent_required_uses_tautology_true=False,
            missing_dependent_field_rejected=True,
            fulfillment_request_variants=[
                "FulfillmentCreateRequest",
                "FulfillmentUpdateRequest",
                "FulfillmentCompleteRequest",
            ],
            discovery_profile_ucp_keys=["version", "services", "capabilities"],
        )
        self.assertTrue(ok8["allowed"])
        bad8 = evaluate_ucp_js_sdk_dependent_required_and_discovery_profile_guard(
            dependent_required_uses_tautology_true=True,
            missing_dependent_field_rejected=False,
            fulfillment_request_variants=["FulfillmentRequest"],
            discovery_profile_ucp_keys=["version", "capabilities"],
        )
        self.assertFalse(bad8["allowed"])

    def test_ucp_python_sdk_and_conformance_guards_pr09_to_pr16(self) -> None:
        # PR-09
        ok9 = evaluate_ucp_python_sdk_jwk_public_key_guard(
            codegen_backend="ucp-schema-generate-types-pydantic",
            jwk_payload={"kty": "EC", "crv": "P-256", "x": "abc", "y": "def", "d": "secret"},
            validator_rejected_private_fields=True,
        )
        self.assertTrue(ok9["allowed"])
        bad9 = evaluate_ucp_python_sdk_jwk_public_key_guard(
            codegen_backend="ucp-schema-generate-types-pydantic",
            jwk_payload={"kty": "EC", "crv": "P-256", "x": "abc", "y": "def", "d": "secret"},
            validator_rejected_private_fields=False,
        )
        self.assertFalse(bad9["allowed"])

        # PR-10
        ok10 = evaluate_ucp_python_sdk_aware_datetime_and_release_sha_guard(
            aware_datetime_field_has_pattern_kwarg=False,
            has_mode_before_str_regex_validator=True,
            valid_iso8601_parsed_without_type_error=True,
            workflow_action_refs={
                "actions/checkout": "11bd71901bbe5b1630ceea73d27597364c9af683",
            },
            checkout_persist_credentials=False,
        )
        self.assertTrue(ok10["allowed"])
        bad10 = evaluate_ucp_python_sdk_aware_datetime_and_release_sha_guard(
            aware_datetime_field_has_pattern_kwarg=True,
            has_mode_before_str_regex_validator=False,
            valid_iso8601_parsed_without_type_error=False,
            workflow_action_refs={"actions/checkout": "v4"},
            checkout_persist_credentials=True,
        )
        self.assertFalse(bad10["allowed"])

        # PR-11
        ok11 = evaluate_ucp_python_sdk_single_module_and_dependent_required_guard(
            consolidated_single_models_module=True,
            topologically_sorted_and_rebuilt=True,
            recursive_models_instantiate_cleanly=True,
            dependent_required_checks_model_fields_set=True,
            missing_dependent_field_raises_value_error=True,
        )
        self.assertTrue(ok11["allowed"])
        bad11 = evaluate_ucp_python_sdk_single_module_and_dependent_required_guard(
            consolidated_single_models_module=False,
            topologically_sorted_and_rebuilt=False,
            recursive_models_instantiate_cleanly=False,
            dependent_required_checks_model_fields_set=False,
            missing_dependent_field_raises_value_error=False,
        )
        self.assertFalse(bad11["allowed"])

        # PR-12
        ok12 = evaluate_ucp_python_sdk_dotted_capability_role_containers_guard(
            emitted_role_containers=[
                "platform_schema",
                "business_schema",
                "response_checkout_schema",
                "response_order_schema",
            ],
            overwritten_schema_collisions=0,
        )
        self.assertTrue(ok12["allowed"])
        bad12 = evaluate_ucp_python_sdk_dotted_capability_role_containers_guard(
            emitted_role_containers=["response_order_schema"],
            overwritten_schema_collisions=3,
        )
        self.assertFalse(bad12["allowed"])

        # PR-13
        ok13 = evaluate_ucp_conformance_checkout_lifecycle_status_band_guard(
            mutate_completed_status_code=422,
            complete_completed_status_code=409,
            out_of_stock_create_status_code=400,
            test_suite_allows_200_on_out_of_stock_create=False,
        )
        self.assertTrue(ok13["allowed"])
        bad13 = evaluate_ucp_conformance_checkout_lifecycle_status_band_guard(
            mutate_completed_status_code=200,
            complete_completed_status_code=500,
            out_of_stock_create_status_code=200,
            test_suite_allows_200_on_out_of_stock_create=True,
        )
        self.assertFalse(bad13["allowed"])

        # PR-14
        ok14 = evaluate_ucp_conformance_shopping_agent_profile_capabilities_guard(
            exercised_capabilities=["dev.ucp.shopping.checkout", "dev.ucp.shopping.fulfillment"],
            declared_agent_capabilities={
                "dev.ucp.shopping.checkout": "2026-01-23",
                "dev.ucp.shopping.fulfillment": "2026-01-23",
            },
            merchant_capability_versions={
                "dev.ucp.shopping.checkout": "2026-01-23",
                "dev.ucp.shopping.fulfillment": "2026-01-23",
            },
        )
        self.assertTrue(ok14["allowed"])
        bad14 = evaluate_ucp_conformance_shopping_agent_profile_capabilities_guard(
            exercised_capabilities=["dev.ucp.shopping.checkout", "dev.ucp.shopping.fulfillment"],
            declared_agent_capabilities={"dev.ucp.shopping.checkout": "2026-01-23"},
            merchant_capability_versions={"dev.ucp.shopping.checkout": "2026-01-23"},
        )
        self.assertFalse(bad14["allowed"])

        # PR-15
        ok15 = evaluate_ucp_conformance_discovery_urls_reachability_guard(
            discovered_urls_status={
                "https://ucp.dev/2026-04-08/schemas/shopping/checkout.json": 200,
                "https://dummy.invalid/ext.json": 404,
            },
            allow_unreachable_urls=["https://dummy.invalid/ext.json"],
        )
        self.assertTrue(ok15["allowed"])
        bad15 = evaluate_ucp_conformance_discovery_urls_reachability_guard(
            discovered_urls_status={"https://merchant.example/broken.json": 404},
            allow_unreachable_urls=[],
        )
        self.assertFalse(bad15["allowed"])

        # PR-16
        ok16 = evaluate_ucp_conformance_postal_address_canonical_fields_guard(
            shipping_destination_payload={
                "type": "shipping",
                "street_address": "1600 Amphitheatre Pkwy",
                "address_locality": "Mountain View",
                "address_region": "CA",
                "postal_code": "94043",
                "address_country": "US",
            }
        )
        self.assertTrue(ok16["allowed"])
        bad16 = evaluate_ucp_conformance_postal_address_canonical_fields_guard(
            shipping_destination_payload={
                "type": "shipping",
                "street_address": "1600 Amphitheatre Pkwy",
                "locality": "Mountain View",
                "administrative_area": "CA",
                "postal_code": "94043",
                "address_country": "US",
            }
        )
        self.assertFalse(bad16["allowed"])


if __name__ == "__main__":
    unittest.main()
