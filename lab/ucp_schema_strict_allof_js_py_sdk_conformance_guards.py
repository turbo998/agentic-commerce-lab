"""Stages 250-251 (250-Stage Milestone!): UCP Schema Strict allOf & OpenAPI 5-Pass Compiler,
UCP JS SDK Open-Union & Catchall Guards, UCP Python SDK JwkPublicKey & Single-Module Models,
and UCP Conformance Suite Deterministic Guards.

Covers 22 primary-source PRs across Universal-Commerce-Protocol repositories:
- PR-01: ucp-schema#80 & #79 (omitted-field open vs strict matrix + lint --quiet --strict exit code 1)
- PR-02: ucp-schema#77 (closing explicitly open allOf schemas in strict mode while preserving map schemas)
- PR-03: ucp-schema#75 & #74 (versioned /2026-04-08/schemas/... URLs + default request direction on --schema)
- PR-04: ucp-schema#73 (5-pass OpenAPI 3.1.0 compiler: version uniformity, polarized components, pruning)
- PR-05: js-sdk#87 (ucp-schema generate-types --lang zod + not.enum refine & <Union>Base catchall exclusion)
- PR-06: js-sdk#84 (.catchall(z.any()) on 71 open schemas preserving credential.token vs closed strip/reject)
- PR-07: js-sdk#83 (penalizing unconstrained {id, type} stubs so BindingSchema never leaks into FulfillmentDestination)
- PR-08: js-sdk#80, #79, #73 (non-vacuous dependentRequired superRefine, per-op request fulfillment, discovery services)
- PR-09: python-sdk#101 (ucp-schema generate-types --lang pydantic + JwkPublicKey forbidden private-key fields d..k)
- PR-10: python-sdk#100 & #99 (stripping regex pattern from AwareDatetime Field into mode='before' + SHA-pinned release.yml)
- PR-11: python-sdk#97 & #96 (consolidated topological models.py with model_rebuild() + dependentRequired validator)
- PR-12: python-sdk#94 (splitting dotted capability role containers platform_schema / business_schema / response_*)
- PR-13: conformance#111 (checkout_lifecycle_test 400 <= status < 500 band & removing 409 out-of-stock escape hatch)
- PR-14: conformance#109 (declaring all exercised shopping capabilities in shopping-agent-test.json with version alignment)
- PR-15: conformance#98 (strict test_discovery_urls HTTP 200 reachability with explicit allow_unreachable_urls fixture)
- PR-16: conformance#97 (canonical address_locality and address_region in ShippingDestination PostalAddress)
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

VERSIONED_SCHEMA_URL_RE = re.compile(
    r"^https://ucp\.dev/\d{4}-\d{2}-\d{2}/schemas/[a-z0-9_/-]+\.json$"
)
FULL_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_JWK_PRIVATE_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})
CANONICAL_ROLE_CONTAINERS = frozenset(
    {
        "platform_schema",
        "business_schema",
        "response_checkout_schema",
        "response_order_schema",
    }
)


def evaluate_ucp_schema_open_strict_and_lint_quiet_guard(
    *,
    validation_mode: str,
    schema_explicit_additional_properties: bool | None,
    payload_has_undeclared_field: bool,
    lint_quiet: bool,
    lint_strict: bool,
    lint_warnings_count: int,
    diagnostics_printed: int,
    summary_line_printed: bool,
    process_exit_code: int,
) -> dict[str, Any]:
    """PR-01 (ucp-schema#80 & #79): Omitted-field open vs strict matrix and `lint --quiet --strict` exit code."""
    violations: list[str] = []
    if validation_mode not in {"open", "strict"}:
        violations.append("invalid_validation_mode")

    if schema_explicit_additional_properties is False:
        should_accept_undeclared = False
    elif validation_mode == "strict":
        should_accept_undeclared = False
    else:
        should_accept_undeclared = True

    payload_accepted = not (payload_has_undeclared_field and not should_accept_undeclared)

    if lint_quiet and diagnostics_printed != 0:
        violations.append("quiet_mode_must_suppress_individual_diagnostic_lines")

    expected_exit_code = 1 if (lint_strict and lint_warnings_count > 0) else 0
    if process_exit_code != expected_exit_code:
        violations.append("lint_strict_exit_code_mismatch")
    if expected_exit_code == 1 and not summary_line_printed:
        violations.append("lint_strict_failure_must_print_summary_line")

    allowed = len(violations) == 0 and payload_accepted
    return {
        "allowed": allowed,
        "decision": "UCP_SCHEMA_OPEN_STRICT_AND_LINT_QUIET_VERIFIED"
        if allowed
        else "UCP_SCHEMA_OPEN_STRICT_OR_LINT_QUIET_VIOLATION",
        "should_accept_undeclared": should_accept_undeclared,
        "payload_accepted": payload_accepted,
        "expected_exit_code": expected_exit_code,
        "violations": violations,
    }


def evaluate_ucp_schema_strict_allof_closing_guard(
    *,
    strict_mode: bool,
    has_allof_composition: bool,
    source_unevaluated_properties: bool | None,
    source_additional_properties: bool | Mapping[str, Any] | None,
    resolved_unevaluated_properties: bool | None,
    resolved_additional_properties: bool | Mapping[str, Any] | None,
    undeclared_root_field_rejected: bool,
) -> dict[str, Any]:
    """PR-02 (ucp-schema#77): Overwriting explicit `unevaluatedProperties: true` / `additionalProperties: true` in strict mode."""
    violations: list[str] = []
    is_map_schema = isinstance(source_additional_properties, Mapping)

    if strict_mode:
        if is_map_schema:
            if not isinstance(resolved_additional_properties, Mapping):
                violations.append("strict_mode_must_preserve_map_schema_additional_properties")
        else:
            if source_additional_properties is True and resolved_additional_properties is not False:
                violations.append("strict_mode_must_overwrite_additional_properties_true_to_false")
            if has_allof_composition or source_unevaluated_properties is True:
                if resolved_unevaluated_properties is not False:
                    violations.append("strict_mode_must_overwrite_allof_unevaluated_properties_to_false")
            if not undeclared_root_field_rejected:
                violations.append("undeclared_root_field_escaped_strict_allof_validation")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_SCHEMA_STRICT_ALLOF_CLOSING_VERIFIED"
        if allowed
        else "UCP_SCHEMA_STRICT_ALLOF_LEFT_OPEN",
        "is_map_schema": is_map_schema,
        "violations": violations,
    }


def evaluate_ucp_schema_versioned_urls_and_default_direction_guard(
    *,
    schema_version_dir: str,
    schema_id_urls: Sequence[str],
    capability_schema_urls: Sequence[str],
    explicit_schema_flag_passed: bool,
    request_flag_passed: bool,
    response_flag_passed: bool,
    resolved_direction: str | None,
) -> dict[str, Any]:
    """PR-03 (ucp-schema#75 & #74): Versioned `/2026-04-08/schemas/...` URLs and default request direction on `--schema`."""
    violations: list[str] = []
    expected_prefix = f"https://ucp.dev/{schema_version_dir}/schemas/"

    for url in list(schema_id_urls) + list(capability_schema_urls):
        if not VERSIONED_SCHEMA_URL_RE.match(url) or not url.startswith(expected_prefix):
            violations.append(f"unversioned_or_mismatched_schema_url:{url}")

    if request_flag_passed and response_flag_passed:
        if resolved_direction is not None:
            violations.append("conflicting_request_and_response_flags_must_fail")
    elif explicit_schema_flag_passed and not request_flag_passed and not response_flag_passed:
        if resolved_direction != "request":
            violations.append("explicit_schema_without_direction_must_default_to_request")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_SCHEMA_VERSIONED_URLS_AND_DEFAULT_DIRECTION_VERIFIED"
        if allowed
        else "UCP_SCHEMA_URL_VERSION_OR_DIRECTION_VIOLATION",
        "expected_prefix": expected_prefix,
        "violations": violations,
    }


def evaluate_ucp_schema_openapi_five_pass_compiler_guard(
    *,
    merged_spec_versions: Sequence[str],
    schema_base_configured: bool,
    polarized_components_emitted: Sequence[str],
    remaining_ucp_annotations_count: int,
    external_file_refs_remaining: int,
    unreachable_schemas_remaining: int,
    synthesized_rest_paths: Sequence[str],
) -> dict[str, Any]:
    """PR-04 (ucp-schema#73): 5-Pass `export-openapi` OpenAPI 3.1.0 compiler invariants."""
    violations: list[str] = []
    unique_versions = set(merged_spec_versions)
    if len(unique_versions) != 1:
        violations.append("merged_specs_x_ucp_version_mismatch")
    if not schema_base_configured:
        violations.append("missing_x_ucp_schema_base")
    if not any(name.endswith("_Request") or name.endswith("_Response") for name in polarized_components_emitted):
        violations.append("missing_direction_polarized_openapi_components")
    if remaining_ucp_annotations_count > 0:
        violations.append("ucp_annotations_leaked_into_exported_openapi")
    if external_file_refs_remaining > 0:
        violations.append("unrewritten_external_file_refs_in_openapi")
    if unreachable_schemas_remaining > 0:
        violations.append("unreachable_component_schemas_not_pruned")
    required_paths = {"/checkouts", "/checkouts/{id}", "/checkouts/{id}/complete"}
    if not required_paths.issubset(set(synthesized_rest_paths)):
        violations.append("missing_synthesized_openrpc_rest_paths")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_SCHEMA_OPENAPI_FIVE_PASS_COMPILER_VERIFIED"
        if allowed
        else "UCP_SCHEMA_OPENAPI_COMPILER_VIOLATION",
        "unique_versions_count": len(unique_versions),
        "violations": violations,
    }


def evaluate_ucp_js_sdk_open_union_not_enum_guard(
    *,
    codegen_backend: str,
    known_enum_Literals: Sequence[str],
    catchall_has_not_enum_refine: bool,
    union_base_includes_open_catchall: bool,
    extension_branch_matched_for_extension_value: bool,
) -> dict[str, Any]:
    """PR-05 (js-sdk#87): `ucp-schema generate-types --lang zod` and `not.enum` open-union `<Union>Base` guard."""
    violations: list[str] = []
    if codegen_backend != "ucp-schema-generate-types-zod":
        violations.append("legacy_zod_codegen_backend_not_migrated")
    if not known_enum_Literals:
        violations.append("empty_known_enum_literals")
    if not catchall_has_not_enum_refine:
        violations.append("open_union_catchall_missing_not_enum_refine")
    if union_base_includes_open_catchall:
        violations.append("union_base_must_exclude_open_string_catchall_to_prevent_shadowing")
    if not extension_branch_matched_for_extension_value:
        violations.append("extension_union_branch_shadowed_by_base_catchall")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_JS_SDK_OPEN_UNION_NOT_ENUM_GUARD_VERIFIED"
        if allowed
        else "UCP_JS_SDK_OPEN_UNION_CATCHALL_POISONING",
        "violations": violations,
    }


def evaluate_ucp_js_sdk_open_schema_catchall_guard(
    *,
    open_schemas_total: int,
    open_schemas_with_catchall_count: int,
    parsed_credential_payload: Mapping[str, Any],
    closed_schema_rejected_undeclared: bool,
) -> dict[str, Any]:
    """PR-06 (js-sdk#84): `.catchall(z.any())` on all 71 open Zod object schemas preserving `credential.token`."""
    violations: list[str] = []
    if open_schemas_total < 71 or open_schemas_with_catchall_count != open_schemas_total:
        violations.append("open_zod_schemas_missing_catchall_z_any")
    token_val = parsed_credential_payload.get("token")
    if not isinstance(token_val, str) or not token_val.strip():
        violations.append("payment_credential_token_stripped_by_zod_object")
    if not closed_schema_rejected_undeclared:
        violations.append("closed_zod_schema_failed_to_strip_or_reject_undeclared")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_JS_SDK_OPEN_SCHEMA_CATCHALL_VERIFIED"
        if allowed
        else "UCP_JS_SDK_CREDENTIAL_TOKEN_STRIPPED",
        "open_schemas_with_catchall_count": open_schemas_with_catchall_count,
        "violations": violations,
    }


def evaluate_ucp_js_sdk_fulfillment_destination_binding_isolation_guard(
    *,
    unconstrained_id_type_penalized_in_contest: bool,
    fulfillment_destination_members: Sequence[str],
    malformed_shipping_error_mentions_reverse_domain_regex: bool,
) -> dict[str, Any]:
    """PR-07 (js-sdk#83): Preventing `BindingSchema` reverse-domain leakage into `FulfillmentDestinationSchema`."""
    violations: list[str] = []
    if not unconstrained_id_type_penalized_in_contest:
        violations.append("unconstrained_id_type_stub_not_penalized_in_name_contest")
    if "BindingSchema" in set(fulfillment_destination_members):
        violations.append("binding_schema_leaked_into_fulfillment_destination_union")
    if malformed_shipping_error_mentions_reverse_domain_regex:
        violations.append("shipping_validation_error_polluted_by_binding_reverse_domain_regex")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_JS_SDK_FULFILLMENT_DESTINATION_BINDING_ISOLATION_VERIFIED"
        if allowed
        else "UCP_JS_SDK_BINDING_SCHEMA_LEAKAGE",
        "violations": violations,
    }


def evaluate_ucp_js_sdk_dependent_required_and_discovery_profile_guard(
    *,
    dependent_required_uses_tautology_true: bool,
    missing_dependent_field_rejected: bool,
    fulfillment_request_variants: Sequence[str],
    discovery_profile_ucp_keys: Sequence[str],
) -> dict[str, Any]:
    """PR-08 (js-sdk#80, #79, #73): Non-vacuous `dependentRequired`, per-op request fulfillment, and discovery `services`."""
    violations: list[str] = []
    if dependent_required_uses_tautology_true:
        violations.append("vacuous_dependent_required_or_true_tautology_detected")
    if not missing_dependent_field_rejected:
        violations.append("time_interval_missing_dependent_required_field_not_rejected")
    expected_variants = {
        "FulfillmentCreateRequest",
        "FulfillmentUpdateRequest",
        "FulfillmentCompleteRequest",
    }
    if not expected_variants.issubset(set(fulfillment_request_variants)):
        violations.append("missing_per_operation_fulfillment_request_variants")
    if not {"version", "services", "capabilities"}.issubset(set(discovery_profile_ucp_keys)):
        violations.append("discovery_profile_ucp_missing_services_from_business_schema")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_JS_SDK_DEPENDENT_REQUIRED_AND_DISCOVERY_VERIFIED"
        if allowed
        else "UCP_JS_SDK_DEPENDENT_REQUIRED_OR_DISCOVERY_DEFECT",
        "violations": violations,
    }


def evaluate_ucp_python_sdk_jwk_public_key_guard(
    *,
    codegen_backend: str,
    jwk_payload: Mapping[str, Any],
    validator_rejected_private_fields: bool,
) -> dict[str, Any]:
    """PR-09 (python-sdk#101): `JwkPublicKey` forbidden private-key fields (`d`, `p`, `q`, `dp`, `dq`, `qi`, `oth`, `k`)."""
    violations: list[str] = []
    if codegen_backend != "ucp-schema-generate-types-pydantic":
        violations.append("legacy_datamodel_code_generator_backend_not_migrated")

    leaked_fields = sorted(FORBIDDEN_JWK_PRIVATE_FIELDS.intersection(set(jwk_payload.keys())))
    if leaked_fields and not validator_rejected_private_fields:
        violations.append(f"jwk_public_key_accepted_forbidden_private_fields:{','.join(leaked_fields)}")
    if not leaked_fields and validator_rejected_private_fields:
        violations.append("jwk_public_key_false_positive_on_clean_public_key")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_PYTHON_SDK_JWK_PUBLIC_KEY_GUARD_VERIFIED"
        if allowed
        else "UCP_PYTHON_SDK_JWK_PRIVATE_KEY_LEAKAGE",
        "leaked_private_fields": leaked_fields,
        "violations": violations,
    }


def evaluate_ucp_python_sdk_aware_datetime_and_release_sha_guard(
    *,
    aware_datetime_field_has_pattern_kwarg: bool,
    has_mode_before_str_regex_validator: bool,
    valid_iso8601_parsed_without_type_error: bool,
    workflow_action_refs: Mapping[str, str],
    checkout_persist_credentials: bool,
) -> dict[str, Any]:
    """PR-10 (python-sdk#100 & #99): Stripping `pattern` from `AwareDatetime` `Field(...)` + SHA-pinned `release.yml`."""
    violations: list[str] = []
    if aware_datetime_field_has_pattern_kwarg:
        violations.append("aware_datetime_field_retains_post_parse_regex_pattern")
    if not has_mode_before_str_regex_validator:
        violations.append("missing_mode_before_str_regex_validator_for_open_at")
    if not valid_iso8601_parsed_without_type_error:
        violations.append("aware_datetime_raised_type_error_on_valid_timestamp")

    for action_name, ref in workflow_action_refs.items():
        if not FULL_COMMIT_SHA_RE.match(ref):
            violations.append(f"unpinned_github_action_ref:{action_name}@{ref}")
    if checkout_persist_credentials:
        violations.append("release_workflow_checkout_must_set_persist_credentials_false")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_PYTHON_SDK_AWARE_DATETIME_AND_RELEASE_SHA_VERIFIED"
        if allowed
        else "UCP_PYTHON_SDK_DATETIME_OR_WORKFLOW_VIOLATION",
        "violations": violations,
    }


def evaluate_ucp_python_sdk_single_module_and_dependent_required_guard(
    *,
    consolidated_single_models_module: bool,
    topologically_sorted_and_rebuilt: bool,
    recursive_models_instantiate_cleanly: bool,
    dependent_required_checks_model_fields_set: bool,
    missing_dependent_field_raises_value_error: bool,
) -> dict[str, Any]:
    """PR-11 (python-sdk#97 & #96): Consolidated `ucp_sdk/models.py` + `model_fields_set` `dependentRequired` validator."""
    violations: list[str] = []
    if not consolidated_single_models_module:
        violations.append("fragmented_multi_file_models_risk_circular_import")
    if not topologically_sorted_and_rebuilt or not recursive_models_instantiate_cleanly:
        violations.append("pydantic_forward_ref_or_circular_model_rebuild_failure")
    if not dependent_required_checks_model_fields_set or not missing_dependent_field_raises_value_error:
        violations.append("pydantic_dependent_required_validator_missing_or_vacuous")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_PYTHON_SDK_SINGLE_MODULE_AND_DEPENDENT_REQUIRED_VERIFIED"
        if allowed
        else "UCP_PYTHON_SDK_CIRCULAR_MODEL_OR_DEPENDENT_REQUIRED_DEFECT",
        "violations": violations,
    }


def evaluate_ucp_python_sdk_dotted_capability_role_containers_guard(
    *,
    emitted_role_containers: Sequence[str],
    overwritten_schema_collisions: int,
) -> dict[str, Any]:
    """PR-12 (python-sdk#94): Splitting dotted capability schemas across distinct role containers."""
    violations: list[str] = []
    missing_roles = sorted(CANONICAL_ROLE_CONTAINERS - set(emitted_role_containers))
    if missing_roles:
        violations.append(f"missing_capability_role_containers:{','.join(missing_roles)}")
    if overwritten_schema_collisions > 0:
        violations.append("dotted_capability_name_collided_across_role_containers")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_PYTHON_SDK_ROLE_CONTAINERS_SPLIT_VERIFIED"
        if allowed
        else "UCP_PYTHON_SDK_CAPABILITY_ROLE_COLLISION",
        "missing_roles": missing_roles,
        "violations": violations,
    }


def evaluate_ucp_conformance_checkout_lifecycle_status_band_guard(
    *,
    mutate_completed_status_code: int,
    complete_completed_status_code: int,
    out_of_stock_create_status_code: int,
    test_suite_allows_200_on_out_of_stock_create: bool,
) -> dict[str, Any]:
    """PR-13 (conformance#111): `400 <= status < 500` error band and removal of `409` out-of-stock escape hatch."""
    violations: list[str] = []
    if not (400 <= mutate_completed_status_code < 500):
        violations.append("mutate_completed_checkout_must_return_4xx")
    if not (400 <= complete_completed_status_code < 500):
        violations.append("complete_already_completed_checkout_must_return_4xx")
    if not (400 <= out_of_stock_create_status_code < 500):
        violations.append("out_of_stock_create_checkout_must_fail_with_4xx")
    if test_suite_allows_200_on_out_of_stock_create:
        violations.append("legacy_409_escape_hatch_allowed_out_of_stock_create_to_pass")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_CONFORMANCE_CHECKOUT_LIFECYCLE_4XX_BAND_VERIFIED"
        if allowed
        else "UCP_CONFORMANCE_CHECKOUT_LIFECYCLE_STATUS_VIOLATION",
        "violations": violations,
    }


def evaluate_ucp_conformance_shopping_agent_profile_capabilities_guard(
    *,
    exercised_capabilities: Sequence[str],
    declared_agent_capabilities: Mapping[str, str],
    merchant_capability_versions: Mapping[str, str],
) -> dict[str, Any]:
    """PR-14 (conformance#109): Declaring all exercised shopping capabilities in `shopping-agent-test.json`."""
    violations: list[str] = []
    undeclared: list[str] = []
    version_mismatches: list[str] = []

    for cap in exercised_capabilities:
        if cap not in declared_agent_capabilities:
            undeclared.append(cap)
        else:
            agent_ver = declared_agent_capabilities[cap]
            merch_ver = merchant_capability_versions.get(cap)
            if merch_ver is not None and agent_ver != merch_ver:
                version_mismatches.append(f"{cap}:{agent_ver}!={merch_ver}")

    if undeclared:
        violations.append(f"exercised_capabilities_missing_from_agent_profile:{','.join(undeclared)}")
    if version_mismatches:
        violations.append(f"agent_merchant_capability_version_mismatch:{','.join(version_mismatches)}")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_CONFORMANCE_AGENT_PROFILE_CAPABILITIES_VERIFIED"
        if allowed
        else "UCP_CONFORMANCE_AGENT_CAPABILITY_INTERSECTION_PRUNED",
        "undeclared_capabilities": undeclared,
        "version_mismatches": version_mismatches,
        "violations": violations,
    }


def evaluate_ucp_conformance_discovery_urls_reachability_guard(
    *,
    discovered_urls_status: Mapping[str, int],
    allow_unreachable_urls: Sequence[str],
) -> dict[str, Any]:
    """PR-15 (conformance#98): Strict `test_discovery_urls` reachability with `allow_unreachable_urls` fixture allowlist."""
    violations: list[str] = []
    allow_set = set(allow_unreachable_urls)
    unreachable_unallowlisted: list[str] = []

    for url, status in discovered_urls_status.items():
        if status != 200 and url not in allow_set:
            unreachable_unallowlisted.append(f"{url}({status})")

    if unreachable_unallowlisted:
        violations.append(f"unreachable_discovery_urls:{','.join(unreachable_unallowlisted)}")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_CONFORMANCE_DISCOVERY_URLS_REACHABILITY_VERIFIED"
        if allowed
        else "UCP_CONFORMANCE_UNREACHABLE_DISCOVERY_URL",
        "unreachable_unallowlisted": unreachable_unallowlisted,
        "violations": violations,
    }


def evaluate_ucp_conformance_postal_address_canonical_fields_guard(
    *,
    shipping_destination_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """PR-16 (conformance#97): Canonical `address_locality` and `address_region` in `ShippingDestination`."""
    violations: list[str] = []
    legacy_keys = {"locality", "administrative_area"}.intersection(set(shipping_destination_payload.keys()))
    if legacy_keys:
        violations.append(f"legacy_non_schema_postal_address_fields_used:{','.join(sorted(legacy_keys))}")

    for required_key in ("street_address", "address_locality", "address_region", "postal_code", "address_country"):
        val = shipping_destination_payload.get(required_key)
        if not isinstance(val, str) or not val.strip():
            violations.append(f"missing_canonical_postal_address_field:{required_key}")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision": "UCP_CONFORMANCE_POSTAL_ADDRESS_CANONICAL_FIELDS_VERIFIED"
        if allowed
        else "UCP_CONFORMANCE_POSTAL_ADDRESS_LEGACY_FIELD_VIOLATION",
        "violations": violations,
    }
