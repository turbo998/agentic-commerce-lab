"""Stage 226 deterministic runtime guards covering 44 primary-source PRs across
`Universal-Commerce-Protocol/ucp-schema`, `modelcontextprotocol/ext-apps`,
`modelcontextprotocol/ext-auth`, `modelcontextprotocol/conformance`,
`modelcontextprotocol/ruby-sdk`, and `modelcontextprotocol/php-sdk`:

- PR-01 (`Universal-Commerce-Protocol/ucp-schema#89`):
  Profile-driven OpenAPI 3.1.0 service & type binding (`ucp-schema generate-openapi`).
- PR-02 (`Universal-Commerce-Protocol/ucp-schema#88` & `#87`):
  Open string discriminator union lowering (`<Union>Base`) & decentralized extended subtype discovery (`OU-1..OU-4`).
- PR-03 (`Universal-Commerce-Protocol/ucp-schema#86` & `#85`):
  `.well-known/ucp` profile scoping, orphaned extension pruning & pre/post-slicing AST shape normalizers.
- PR-04 (`Universal-Commerce-Protocol/ucp-schema#91`, `#83`, `#82`, `#81`, & `#78`):
  Directional schema slicing, `$ref` alignment, instance-keyword schema-map linting & non-string-array `required` preservation.
- PR-05 (`modelcontextprotocol/ext-apps#823` & `#822`):
  MCP Apps iframe `allow` semicolon separator + `clipboard-write` & normative `ui/initialize` / `ui/resource-teardown` / `connect-src 'none'` contract.
- PR-06 (`modelcontextprotocol/ext-apps#818` & `#815`):
  Shared `AppBridge` list-change dispatcher across views & pending animation-frame cancellation on `setupSizeChangedNotifications()` cleanup.
- PR-07 (`modelcontextprotocol/ext-apps#816`, `#812`, & `#809`):
  Windows `file:///C:/` root path resolution, dotted-directory `sandbox.html` serving & host-qualified app tool name resolution.
- PR-08 (`modelcontextprotocol/ext-auth#40`, `#38`, `#37`, `#35`, & `#33`):
  MCP DPoP server profile (SEP-1932) Bearer downgrade rejection, `invalid_dpop_proof` vs. `invalid_token`, `dpop_jkt` code binding & SEP-3392 experimental extension alignment.
- PR-09 (`modelcontextprotocol/conformance#561` & `#558`):
  Originating POST SSE stream elicitation correlation (`extra.sendRequest`) & SEP-1036 URL-mode elicitation client/server conformance.
- PR-10 (`modelcontextprotocol/conformance#559`, `#556`, `#555`, & `#554`):
  SEP-2640 directory read `CacheableResult`, SEP-9998 agent discovery conformance, SEP-2243 mandatory `-32020`, & SEP-2164 mandatory `-32602` resource-not-found.
- PR-11 (`modelcontextprotocol/conformance#548`, `#538`, & `#537`):
  SEP-2322 `requestState`-only retry echo, server runner `checks.json` persistence on exception & reject-all server false-green prevention.
- PR-12 (`modelcontextprotocol/ruby-sdk#630`, `#629`, & `#623`):
  MCP Ruby SDK unencodable buffered notification drop, per-item `-32603` on unencodable response & stdio server survival.
- PR-13 (`modelcontextprotocol/ruby-sdk#628`, `#627`, `#625`, `#624`, `#622`, `#620`, `#616`, & `#615`):
  MCP Ruby SDK byte-safe stdio framing, invalid UTF-8 JSON key `-32700 Parse error`, unencodable ping skip & stateless `listChanged`/`subscribe` stripping.
- PR-14 (`modelcontextprotocol/php-sdk#613`, `#608`, & `#606`):
  MCP PHP SDK array-shape nullable/union key preservation, custom registry `publishesListChanges()` & `2026-07-28` `ClientGateway` `InputRequiredResult` guidance.
- PR-15 (`modelcontextprotocol/php-sdk#603`, `#602`, & `#597`):
  MCP PHP SDK unavailable session lock `-32603` alignment, SSE delivery of queued session notifications & `202 Accepted` empty body on notification/response-only POST.
- PR-16 (`modelcontextprotocol/php-sdk#601`, `#599`, & `#598`):
  MCP PHP SDK pre-response stdio notification flush, `{main}` fiber loop HTTP client sends & post-resume session delta persistence.
"""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse


OAS_31_DIALECT = "https://spec.openapis.org/oas/3.1/dialect/base"
ASYMMETRIC_DPOP_ALGS = {"ES256", "ES384", "ES512", "PS256", "PS384", "PS512", "RS256", "RS384", "RS512", "EdDSA"}


def _verdict(
    *,
    allow: bool,
    code: str,
    reason: str,
    upstream_pr: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "allow": allow,
        "code": code,
        "reason": reason,
        "upstream_pr": upstream_pr,
        "details": details or {},
    }


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/ucp-schema#89
# ---------------------------------------------------------------------------
def evaluate_ucp_schema_generate_openapi_binding_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce profile-driven OpenAPI 3.1.0 service and type binding (`ucp-schema#89`)."""
    upstream_pr = "Universal-Commerce-Protocol/ucp-schema#89"
    has_rest_binding = bool(payload.get("has_rest_binding", True))
    has_service_schema = bool(payload.get("has_service_schema", True))
    exit_code = int(payload.get("exit_code", 0))

    if not has_rest_binding or not has_service_schema:
        if exit_code != 2:
            return _verdict(
                allow=False,
                code="BLOCKED_OPENAPI_INVALID_SERVICE_BINDING_EXIT_CODE",
                reason="MCP/embedded-only profiles or REST bindings without 'schema' must fail with exit code 2 (ucp-schema#89).",
                upstream_pr=upstream_pr,
                details={"has_rest_binding": has_rest_binding, "has_service_schema": has_service_schema, "exit_code": exit_code},
            )
        return _verdict(
            allow=True,
            code="ALLOW_OPENAPI_SERVICE_BINDING_REJECTED_CLEANLY",
            reason="Missing REST binding or service schema rejected with exit code 2.",
            upstream_pr=upstream_pr,
        )

    dialect = str(payload.get("json_schema_dialect", ""))
    if dialect != OAS_31_DIALECT:
        return _verdict(
            allow=False,
            code="BLOCKED_OPENAPI_DIALECT_MISMATCH",
            reason=f"OpenAPI 3.1 output must set jsonSchemaDialect='{OAS_31_DIALECT}', got '{dialect}' (ucp-schema#89).",
            upstream_pr=upstream_pr,
        )

    snake_case_wrappers = list(payload.get("snake_case_wrapper_schemas", []))
    if snake_case_wrappers:
        return _verdict(
            allow=False,
            code="BLOCKED_OPENAPI_SNAKE_CASE_WRAPPER_SCHEMAS_PRESENT",
            reason=f"Template snake_case wrapper schemas must be eliminated from components.schemas: {snake_case_wrappers} (ucp-schema#89).",
            upstream_pr=upstream_pr,
        )

    unrewritten_defs_refs = int(payload.get("unrewritten_defs_refs", 0))
    if unrewritten_defs_refs > 0:
        return _verdict(
            allow=False,
            code="BLOCKED_OPENAPI_UNREWRITTEN_DEFS_REFS",
            reason=f"All '#/$defs/<Name>' pointers must be rewritten to '#/components/schemas/<Name>' (ucp-schema#89).",
            upstream_pr=upstream_pr,
        )

    unreachable_components = list(payload.get("unreachable_component_schemas", []))
    discriminator_count = int(payload.get("discriminator_keyword_count", 0))
    empty_webhooks_present = bool(payload.get("empty_webhooks_key_present", False))
    if unreachable_components or discriminator_count > 0 or empty_webhooks_present:
        return _verdict(
            allow=False,
            code="BLOCKED_OPENAPI_UNPRUNED_COMPONENTS_OR_DISCRIMINATOR",
            reason=(
                "OpenAPI output must prune unreachable components, omit empty 'webhooks', "
                "and emit zero 'discriminator' keywords (ucp-schema#89)."
            ),
            upstream_pr=upstream_pr,
            details={
                "unreachable_components": unreachable_components,
                "discriminator_count": discriminator_count,
                "empty_webhooks_present": empty_webhooks_present,
            },
        )

    return _verdict(
        allow=True,
        code="ALLOW_UCP_SCHEMA_GENERATE_OPENAPI_VALID",
        reason="Profile-driven OpenAPI 3.1 service & type binding satisfies all structural invariants.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/ucp-schema#88 & #87
# ---------------------------------------------------------------------------
def evaluate_ucp_schema_open_union_and_extended_subtype_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce open string discriminator union lowering (`#87`) and decentralized
    extended subtype registration (`#88`) invariants `OU-1..OU-4`.
    """
    upstream_pr = "Universal-Commerce-Protocol/ucp-schema#88, #87"
    union_name = str(payload.get("union_name", "FulfillmentDestination"))
    base_ref = f"#/$defs/{union_name}Base"
    anyof_refs = list(payload.get("anyof_refs", []))
    known_variant_refs = list(payload.get("known_variant_refs", []))
    extended_subtype_refs = list(payload.get("extended_subtype_refs", []))
    known_tags = set(payload.get("known_tags", []))
    extended_tags = set(payload.get("extended_tags", []))
    base_not_enum = set(payload.get("base_not_enum", []))
    has_openapi_discriminator = bool(payload.get("has_openapi_discriminator", False))
    variant_or_base_has_disc_default = bool(payload.get("variant_or_base_has_disc_default", False))
    subtype_retains_parent_ref_in_allof = bool(payload.get("subtype_retains_parent_ref_in_allof", False))

    # OU-1: all known + extended subtype refs appear in anyOf before trailing <Union>Base
    expected_refs = set(known_variant_refs) | set(extended_subtype_refs)
    if not anyof_refs or anyof_refs[-1] != base_ref or not expected_refs.issubset(set(anyof_refs[:-1])):
        return _verdict(
            allow=False,
            code="BLOCKED_OU1_UNION_ANYOF_ORDER_OR_MISSING_SUBTYPE",
            reason=(
                f"{union_name}.anyOf must list all known and decentralized extended subtype $refs "
                f"before the trailing '{base_ref}' fallback (OU-1, ucp-schema#87, #88)."
            ),
            upstream_pr=upstream_pr,
            details={"anyof_refs": anyof_refs, "expected_refs": sorted(expected_refs)},
        )

    # OU-2: <Union>Base.properties.<disc>.not.enum contains all known + extended tags
    expected_tags = known_tags | extended_tags
    if base_not_enum != expected_tags:
        return _verdict(
            allow=False,
            code="BLOCKED_OU2_BASE_NOT_ENUM_MISSING_EXTENDED_TAGS",
            reason=(
                f"{union_name}Base discriminator not.enum must match {sorted(expected_tags)}, "
                f"got {sorted(base_not_enum)} (OU-2, ucp-schema#87, #88)."
            ),
            upstream_pr=upstream_pr,
        )

    # OU-3 & OU-4 + parent ref removal
    if has_openapi_discriminator or variant_or_base_has_disc_default or subtype_retains_parent_ref_in_allof:
        return _verdict(
            allow=False,
            code="BLOCKED_OU3_OU4_DISCRIMINATOR_OR_DEFAULT_LEAK",
            reason=(
                "Open union lowering must omit OpenAPI 'discriminator' (OU-3), strip 'default' from "
                "discriminator properties (OU-4), and remove parent union $ref from subtype allOf (ucp-schema#87, #88)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_UCP_SCHEMA_OPEN_UNION_AND_EXTENDED_SUBTYPES_VALID",
        reason="Open union lowering and decentralized extended subtype registration satisfy OU-1..OU-4.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/ucp-schema#86 & #85
# ---------------------------------------------------------------------------
def evaluate_ucp_schema_profile_scoping_and_ast_normalizer_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce `.well-known/ucp` profile scoping (`#85`) and AST shape normalizers (`#86`)."""
    upstream_pr = "Universal-Commerce-Protocol/ucp-schema#86, #85"
    profile_flag_used = bool(payload.get("profile_flag_used", True))
    schema_dir_or_cap_flag_used = bool(payload.get("schema_dir_or_cap_flag_used", False))
    if profile_flag_used and schema_dir_or_cap_flag_used:
        return _verdict(
            allow=False,
            code="BLOCKED_PROFILE_AND_SCHEMA_DIR_MUTUAL_EXCLUSIVITY",
            reason="--profile is mutually exclusive with --schema-dir, --capability, and --extension (ucp-schema#85).",
            upstream_pr=upstream_pr,
        )

    user_agent = str(payload.get("http_user_agent", ""))
    if not user_agent.startswith("ucp-schema/"):
        return _verdict(
            allow=False,
            code="BLOCKED_MISSING_UCP_SCHEMA_USER_AGENT",
            reason=f"Remote .well-known/ucp loader must send 'ucp-schema/<version>' User-Agent, got '{user_agent}' (ucp-schema#85).",
            upstream_pr=upstream_pr,
        )

    orphaned_extensions_retained = list(payload.get("orphaned_extensions_retained", []))
    if orphaned_extensions_retained:
        return _verdict(
            allow=False,
            code="BLOCKED_ORPHANED_EXTENSIONS_NOT_PRUNED",
            reason=f"Extensions whose 'extends' parent capability is inactive must be pruned: {orphaned_extensions_retained} (ucp-schema#85).",
            upstream_pr=upstream_pr,
        )

    hoisted_variants = set(payload.get("hoisted_inline_variants", []))
    required_hoisted = {"ShippingMethod", "PickupMethod", "Oauth2Provider"}
    if not required_hoisted.issubset(hoisted_variants):
        return _verdict(
            allow=False,
            code="BLOCKED_INLINE_CONDITIONAL_VARIANTS_NOT_HOISTED",
            reason=f"Pre-slicing must hoist inline conditional variants {sorted(required_hoisted)} (ucp-schema#86).",
            upstream_pr=upstream_pr,
        )

    totals_contains_allof_stripped = bool(payload.get("totals_contains_allof_stripped", False))
    extends_normalized_to_anyof = bool(payload.get("extends_normalized_to_anyof", False))
    location_timezone_dependent_required = bool(payload.get("location_timezone_dependent_required", False))
    if not (totals_contains_allof_stripped and extends_normalized_to_anyof and location_timezone_dependent_required):
        return _verdict(
            allow=False,
            code="BLOCKED_AST_NORMALIZER_PASS_INCOMPLETE",
            reason=(
                "Post-slicing AST normalizers must strip Totals.allOf contains, rewrite scalar|array oneOf to anyOf, "
                "and lower Location.timezone presence if/then into dependentRequired (ucp-schema#86)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_UCP_SCHEMA_PROFILE_AND_AST_NORMALIZERS_VALID",
        reason=".well-known/ucp profile scoping and AST shape normalizers verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp-schema#91, #83, #82, #81, & #78
# ---------------------------------------------------------------------------
def evaluate_ucp_schema_slicing_lint_and_required_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce instance-keyword schema-map linting (`#91`), non-string-array `required`
    preservation (`#78`), and directional schema slicing + `$ref` alignment (`#81`, `#82`, `#83`).
    """
    upstream_pr = "Universal-Commerce-Protocol/ucp-schema#91, #83, #82, #81, #78"
    linted_instance_named_properties = set(payload.get("linted_instance_named_properties", []))
    required_instance_names = {"default", "const", "examples", "enum"}
    if not required_instance_names.issubset(linted_instance_named_properties):
        return _verdict(
            allow=False,
            code="BLOCKED_INSTANCE_KEYWORD_PROPERTY_SCHEMA_SKIPPED",
            reason=(
                "check_refs and check_annotations must traverse schema values inside properties/$defs "
                "named 'default', 'const', 'examples', or 'enum' (ucp-schema#91)."
            ),
            upstream_pr=upstream_pr,
        )

    authored_required = payload.get("authored_required")
    resolved_required = payload.get("resolved_required")
    is_string_array = isinstance(authored_required, list) and all(isinstance(x, str) for x in authored_required)
    if not is_string_array and resolved_required != authored_required:
        return _verdict(
            allow=False,
            code="BLOCKED_NON_STRING_ARRAY_REQUIRED_REWRITTEN",
            reason=(
                f"Non-string-array required ({authored_required!r}) must be preserved untouched "
                f"instead of rewritten to {resolved_required!r} (ucp-schema#78)."
            ),
            upstream_pr=upstream_pr,
        )

    directional_refs_aligned = bool(payload.get("directional_refs_aligned", False))
    ucp_keywords_stripped = bool(payload.get("ucp_keywords_stripped", False))
    colliding_defs_parent_qualified = bool(payload.get("colliding_defs_parent_qualified", False))
    if not (directional_refs_aligned and ucp_keywords_stripped and colliding_defs_parent_qualified):
        return _verdict(
            allow=False,
            code="BLOCKED_DIRECTIONAL_SLICING_OR_QUALIFICATION_INVALID",
            reason=(
                "Codegen must strip authoring UCP keywords, parent-qualify colliding local $defs, "
                "and align directional request $refs to <Target><Suffix> (ucp-schema#81, #82, #83)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_UCP_SCHEMA_SLICING_LINT_AND_REQUIRED_VALID",
        reason="Instance-keyword schema-map linting, required preservation, and directional slicing verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-05: modelcontextprotocol/ext-apps#823 & #822
# ---------------------------------------------------------------------------
def evaluate_mcp_ext_apps_iframe_allow_and_normative_spec_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce semicolon-separated iframe `allow` attribute with `clipboard-write` (`#823`)
    and normative `ui/initialize`, `ui/resource-teardown` request, and `connect-src 'none'` (`#822`).
    """
    upstream_pr = "modelcontextprotocol/ext-apps#823, #822"
    declared_permissions = list(payload.get("declared_permissions", []))
    iframe_allow_attr = str(payload.get("iframe_allow_attr", ""))
    expected_allow = "; ".join(declared_permissions)
    if iframe_allow_attr != expected_allow or "clipboard-write" not in declared_permissions:
        return _verdict(
            allow=False,
            code="BLOCKED_IFRAME_ALLOW_PERMISSION_POLICY_MALFORMED",
            reason=(
                f"Iframe allow attribute must join directives with '; ' and include 'clipboard-write' "
                f"(expected '{expected_allow}', got '{iframe_allow_attr}', ext-apps#823)."
            ),
            upstream_pr=upstream_pr,
        )

    handshake_method = str(payload.get("handshake_method", ""))
    handshake_params = payload.get("handshake_params") or {}
    if handshake_method != "ui/initialize" or not {"appInfo", "appCapabilities", "protocolVersion"}.issubset(handshake_params.keys()):
        return _verdict(
            allow=False,
            code="BLOCKED_MCP_APPS_INVALID_HANDSHAKE_METHOD_OR_PARAMS",
            reason="MCP Apps handshake must send 'ui/initialize' with appInfo, appCapabilities, and protocolVersion (ext-apps#822).",
            upstream_pr=upstream_pr,
        )

    teardown_is_request_with_id = bool(payload.get("teardown_is_request_with_id", False))
    default_connect_src = str(payload.get("default_connect_src", ""))
    if not teardown_is_request_with_id or default_connect_src != "'none'":
        return _verdict(
            allow=False,
            code="BLOCKED_MCP_APPS_TEARDOWN_OR_DEFAULT_CSP_DRIFT",
            reason="ui/resource-teardown must be a request with id and default CSP connect-src must be \"'none'\" (ext-apps#822).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_EXT_APPS_IFRAME_AND_SPEC_VALID",
        reason="MCP Apps iframe allow policy, ui/initialize handshake, and default CSP connect-src verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-06: modelcontextprotocol/ext-apps#818 & #815
# ---------------------------------------------------------------------------
def evaluate_mcp_ext_apps_shared_dispatcher_and_raf_cleanup_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce shared list-change dispatcher across multiple `AppBridge` views (`#818`)
    and pending animation frame cancellation on `setupSizeChangedNotifications()` cleanup (`#815`).
    """
    upstream_pr = "modelcontextprotocol/ext-apps#818, #815"
    ready_views = list(payload.get("ready_views", []))
    not_ready_views = list(payload.get("not_ready_views", []))
    disconnected_views = list(payload.get("disconnected_views", []))
    notified_views = list(payload.get("notified_views", []))
    caller_custom_handler_preserved = bool(payload.get("caller_custom_handler_preserved", True))

    if notified_views != ready_views or any(v in notified_views for v in not_ready_views + disconnected_views):
        return _verdict(
            allow=False,
            code="BLOCKED_APPBRIDGE_LIST_CHANGED_ROUTING_DRIFT",
            reason=(
                f"Shared AppBridge list-change dispatcher must notify all and only Apps-ready connected views "
                f"{ready_views}, got {notified_views} (ext-apps#818)."
            ),
            upstream_pr=upstream_pr,
        )

    if not caller_custom_handler_preserved:
        return _verdict(
            allow=False,
            code="BLOCKED_CALLER_CUSTOM_LIST_CHANGE_HANDLER_OVERWRITTEN",
            reason="Caller-installed list-change handler on MCP Client must not be overwritten by bridge joins/disconnects (ext-apps#818).",
            upstream_pr=upstream_pr,
        )

    pending_raf_id = payload.get("pending_raf_id_at_cleanup", 0)
    raf_cancelled_on_cleanup = bool(payload.get("raf_cancelled_on_cleanup", False))
    post_cleanup_size_notifications = int(payload.get("post_cleanup_size_notifications", 0))
    if pending_raf_id is not None and (not raf_cancelled_on_cleanup or post_cleanup_size_notifications > 0):
        return _verdict(
            allow=False,
            code="BLOCKED_POST_CLEANUP_SIZE_CHANGED_NOTIFICATION_LEAK",
            reason=(
                "setupSizeChangedNotifications() cleanup must cancel pending requestAnimationFrame "
                "(including ID 0) and emit 0 notifications after cleanup (ext-apps#815)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_EXT_APPS_DISPATCHER_AND_RAF_CLEANUP_VALID",
        reason="Shared AppBridge list-change forwarding and pending animation-frame cancellation verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/ext-apps#816, #812, & #809
# ---------------------------------------------------------------------------
def evaluate_mcp_ext_apps_windows_file_url_sandbox_and_tool_prefix_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce Windows `file:///C:/` path resolution (`#816`), dotted-directory
    `sandbox.html` serving (`#812`), and host-qualified tool name resolution (`#809`).
    """
    upstream_pr = "modelcontextprotocol/ext-apps#816, #812, #809"
    file_url = str(payload.get("file_url", "file:///C:/Users/me/Report%20#3.pdf"))
    resolved_win_path = str(payload.get("resolved_win_path", ""))
    expected_win_path = str(payload.get("expected_win_path", r"C:\Users\me\Report #3.pdf"))
    if resolved_win_path != expected_win_path or resolved_win_path.startswith(("C:\\C:\\", "/C:")):
        return _verdict(
            allow=False,
            code="BLOCKED_WINDOWS_FILE_URL_DOUBLE_DRIVE_OR_TRUNCATION",
            reason=(
                f"Windows fileUrlToPath('{file_url}') must resolve to '{expected_win_path}' "
                f"without double drive prefix or '#' truncation, got '{resolved_win_path}' (ext-apps#816)."
            ),
            upstream_pr=upstream_pr,
        )

    checkout_has_dotted_ancestor = bool(payload.get("checkout_has_dotted_ancestor", True))
    sendfile_uses_root_option = bool(payload.get("sendfile_uses_root_option", False))
    sandbox_http_status = int(payload.get("sandbox_http_status", 200))
    if checkout_has_dotted_ancestor and (not sendfile_uses_root_option or sandbox_http_status != 200):
        return _verdict(
            allow=False,
            code="BLOCKED_DOTTED_DIR_SANDBOX_HTML_404",
            reason="basic-host must serve sandbox.html via res.sendFile('sandbox.html', { root: DIRECTORY }) so dotted paths return 200 (ext-apps#812).",
            upstream_pr=upstream_pr,
        )

    invoked_entry_tool = str(payload.get("invoked_entry_tool", "pdf-server-display_pdf"))
    base_followup_tool = str(payload.get("base_followup_tool", "read_pdf_bytes"))
    resolved_followup_tool = str(payload.get("resolved_followup_tool", ""))
    expected_prefix = invoked_entry_tool[: -len("display_pdf")] if invoked_entry_tool.endswith("display_pdf") else ""
    expected_followup = f"{expected_prefix}{base_followup_tool}"
    if resolved_followup_tool != expected_followup:
        return _verdict(
            allow=False,
            code="BLOCKED_UNQUALIFIED_VIEWER_FOLLOWUP_TOOL_NAME",
            reason=(
                f"Viewer follow-up tool call must inherit host prefix '{expected_followup}', "
                f"got '{resolved_followup_tool}' (ext-apps#809)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_EXT_APPS_WINDOWS_SANDBOX_AND_TOOL_PREFIX_VALID",
        reason="Windows file:// path resolution, dotted-directory sandbox.html serving, and host-prefixed tool resolution verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/ext-auth#40, #38, #37, #35, & #33
# ---------------------------------------------------------------------------
def evaluate_mcp_ext_auth_dpop_and_sep3392_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce MCP DPoP server profile (`#33`, `#35`) and SEP-3392 experimental
    extension conventions (`#37`, `#38`, `#40`).
    """
    upstream_pr = "modelcontextprotocol/ext-auth#40, #38, #37, #35, #33"
    token_is_dpop_bound = bool(payload.get("token_is_dpop_bound", True))
    auth_scheme = str(payload.get("auth_scheme", "DPoP"))
    http_status = int(payload.get("http_status", 200))
    if token_is_dpop_bound and auth_scheme.lower() == "bearer":
        if http_status != 401:
            return _verdict(
                allow=False,
                code="BLOCKED_DPOP_BEARER_DOWNGRADE_ACCEPTED",
                reason="Server MUST NOT accept a DPoP-bound token under the Bearer scheme; must reject with HTTP 401 (ext-auth#33).",
                upstream_pr=upstream_pr,
            )
        return _verdict(
            allow=True,
            code="ALLOW_DPOP_BEARER_DOWNGRADE_REJECTED_401",
            reason="DPoP-bound token presented under Bearer scheme rejected with HTTP 401.",
            upstream_pr=upstream_pr,
        )

    dpop_proof_valid = bool(payload.get("dpop_proof_valid", True))
    error_code = str(payload.get("error_code", ""))
    if not dpop_proof_valid:
        if http_status != 401 or error_code != "invalid_dpop_proof":
            return _verdict(
                allow=False,
                code="BLOCKED_DPOP_PROOF_FAILURE_WRONG_ERROR_CODE",
                reason=f"RFC 9449 §4.3 DPoP proof failures must return HTTP 401 with error='invalid_dpop_proof', got {http_status}/{error_code!r} (ext-auth#33).",
                upstream_pr=upstream_pr,
            )

    supported_algs = list(payload.get("dpop_signing_alg_values_supported", []))
    if not supported_algs or any(alg not in ASYMMETRIC_DPOP_ALGS for alg in supported_algs):
        return _verdict(
            allow=False,
            code="BLOCKED_DPOP_METADATA_INVALID_SIGNING_ALGS",
            reason=f"Protected Resource Metadata must advertise non-empty asymmetric dpop_signing_alg_values_supported, got {supported_algs} (ext-auth#33).",
            upstream_pr=upstream_pr,
        )

    dpop_jkt_bound = bool(payload.get("dpop_jkt_bound_to_auth_code", False))
    dpop_and_wif_in_experimental_dir = bool(payload.get("dpop_and_wif_in_experimental_dir", False))
    if not dpop_jkt_bound or not dpop_and_wif_in_experimental_dir:
        return _verdict(
            allow=False,
            code="BLOCKED_DPOP_JKT_OR_SEP3392_LAYOUT_DRIFT",
            reason="Authorization request must bind dpop_jkt alongside PKCE (#35) and place DPoP/WIF under specification/experimental/ (#37, #38, #40).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_EXT_AUTH_DPOP_AND_SEP3392_VALID",
        reason="MCP DPoP server profile, dpop_jkt binding, and SEP-3392 experimental layout verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/conformance#561 & #558
# ---------------------------------------------------------------------------
def evaluate_mcp_conformance_url_elicitation_and_stream_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce originating POST SSE stream correlation (`#561`) and SEP-1036 URL-mode
    elicitation client/server conformance (`#558`).
    """
    upstream_pr = "modelcontextprotocol/conformance#561, #558"
    elicitation_sent_on_originating_post_stream = bool(payload.get("elicitation_sent_on_originating_post_stream", False))
    if not elicitation_sent_on_originating_post_stream:
        return _verdict(
            allow=False,
            code="BLOCKED_ELICITATION_SENT_ON_SEPARATE_GET_STREAM",
            reason="Tool handler must use extra.sendRequest() so elicitation arrives on the originating tools/call POST stream (conformance#561).",
            upstream_pr=upstream_pr,
        )

    emitted_error_code = payload.get("emitted_error_code")
    if emitted_error_code == -32042:
        return _verdict(
            allow=False,
            code="BLOCKED_RETIRED_URL_ELICITATION_REQUIRED_ERROR_32042",
            reason="2026-07-28 implementations MUST NOT emit retired error code -32042 (URLElicitationRequiredError, conformance#558).",
            upstream_pr=upstream_pr,
        )

    client_declared_url_mode = bool(payload.get("client_declared_url_mode", True))
    if not client_declared_url_mode:
        http_status = int(payload.get("http_status", 200))
        req_caps = ((payload.get("error_data") or {}).get("requiredCapabilities") or {}).get("elicitation") or {}
        if http_status != 400 or emitted_error_code != -32021 or "url" not in req_caps:
            return _verdict(
                allow=False,
                code="BLOCKED_MISSING_URL_CAPABILITY_NOT_REJECTED_32021",
                reason=(
                    "When client does not declare elicitation.url (including elicitation: {} or {form: {}}), "
                    "server must return HTTP 400 + JSON-RPC -32021 naming elicitation.url (conformance#558)."
                ),
                upstream_pr=upstream_pr,
            )
        return _verdict(
            allow=True,
            code="ALLOW_MISSING_URL_CAPABILITY_REJECTED_32021",
            reason="Undeclared elicitation.url capability rejected with HTTP 400 and -32021.",
            upstream_pr=upstream_pr,
        )

    url_value = str(payload.get("elicitation_url", "https://auth.example.com/consent"))
    parsed_url = urlparse(url_value)
    if not (parsed_url.scheme and parsed_url.netloc) or " " in url_value:
        return _verdict(
            allow=False,
            code="BLOCKED_INVALID_URL_ELICITATION_URI",
            reason=f"URL-mode elicitation url must be a valid absolute RFC 3986 URI, got '{url_value}' (conformance#558).",
            upstream_pr=upstream_pr,
        )

    declined_url_prefetched = bool(payload.get("declined_url_prefetched", False))
    missing_mode_treated_as_form = bool(payload.get("missing_mode_treated_as_form", False))
    newest_request_state_echoed = bool(payload.get("newest_request_state_echoed", False))
    decline_and_cancel_handled = bool(payload.get("decline_and_cancel_handled", False))
    if declined_url_prefetched or not (missing_mode_treated_as_form and newest_request_state_echoed and decline_and_cancel_handled):
        return _verdict(
            allow=False,
            code="BLOCKED_SEP1036_CLIENT_OR_SERVER_FLOW_VIOLATION",
            reason=(
                "SEP-1036 requires zero URL prefetch on declined requests, missing mode treated as form, "
                "newest requestState echoed each round, and graceful server handling of decline/cancel (conformance#558)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_CONFORMANCE_URL_ELICITATION_AND_STREAM_VALID",
        reason="Originating POST SSE stream correlation and SEP-1036 URL-mode elicitation conformance verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/conformance#559, #556, #555, & #554
# ---------------------------------------------------------------------------
def evaluate_mcp_conformance_skills_agents_and_error_codes_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce SEP-2640 directory read `CacheableResult` (`#559`), SEP-9998 agent discovery (`#556`),
    SEP-2243 mandatory `-32020` (`#555`), and SEP-2164 mandatory `-32602` (`#554`).
    """
    upstream_pr = "modelcontextprotocol/conformance#559, #556, #555, #554"
    dir_read_result = payload.get("directory_read_result") or {}
    if not isinstance(dir_read_result.get("ttlMs"), int) or dir_read_result.get("cacheScope") not in {"public", "private"}:
        return _verdict(
            allow=False,
            code="BLOCKED_DIRECTORY_READ_MISSING_CACHEABLE_RESULT_FIELDS",
            reason="2026-07-28 resources/directory/read result MUST carry integer ttlMs and cacheScope (conformance#559).",
            upstream_pr=upstream_pr,
        )

    hidden_agent_leaked_or_distinguishable = bool(payload.get("hidden_agent_leaked_or_distinguishable", False))
    agent_tools_match_tools_list = bool(payload.get("agent_tools_match_tools_list", False))
    agents_results_have_cache_attrs = bool(payload.get("agents_results_have_cache_attrs", False))
    if hidden_agent_leaked_or_distinguishable or not (agent_tools_match_tools_list and agents_results_have_cache_attrs):
        return _verdict(
            allow=False,
            code="BLOCKED_AGENT_DISCOVERY_CONFORMANCE_VIOLATION",
            reason=(
                "Agent discovery must keep hidden agents indistinguishable from unknown ones (agent_not_found), "
                "match tools/list entries, and include ttlMs/cacheScope (conformance#556)."
            ),
            upstream_pr=upstream_pr,
        )

    header_mismatch_error_code = int(payload.get("header_mismatch_error_code", 0))
    header_mismatch_http_status = int(payload.get("header_mismatch_http_status", 200))
    if header_mismatch_http_status != 400 or header_mismatch_error_code != -32020:
        return _verdict(
            allow=False,
            code="BLOCKED_SEP2243_HEADER_MISMATCH_MUST_BE_32020",
            reason=(
                f"SEP-2243 standard/custom header mismatch rejection MUST return HTTP 400 and JSON-RPC -32020, "
                f"got HTTP {header_mismatch_http_status} / {header_mismatch_error_code} (conformance#555)."
            ),
            upstream_pr=upstream_pr,
        )

    resource_not_found_error_code = int(payload.get("resource_not_found_error_code", 0))
    if resource_not_found_error_code != -32602:
        return _verdict(
            allow=False,
            code="BLOCKED_SEP2164_RESOURCE_NOT_FOUND_MUST_BE_32602",
            reason=(
                f"SEP-2164 nonexistent resource MUST return JSON-RPC -32602 (retired -32002 is forbidden), "
                f"got {resource_not_found_error_code} (conformance#554)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_CONFORMANCE_SKILLS_AGENTS_AND_ERROR_CODES_VALID",
        reason="SEP-2640 directory cache attributes, SEP-9998 agent discovery, SEP-2243 -32020, and SEP-2164 -32602 verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/conformance#548, #538, & #537
# ---------------------------------------------------------------------------
def evaluate_mcp_conformance_mrtr_state_only_and_runner_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce SEP-2322 `requestState`-only retry echo (`#548`), `checks.json` persistence
    on server scenario throw (`#538`), and reject-all server false-green prevention (`#537`).
    """
    upstream_pr = "modelcontextprotocol/conformance#548, #538, #537"
    initial_request_state = payload.get("initial_request_state")
    retry_request_state = payload.get("retry_request_state")
    client_retried_state_only = bool(payload.get("client_retried_state_only", False))
    if not client_retried_state_only or retry_request_state != initial_request_state:
        return _verdict(
            allow=False,
            code="BLOCKED_MRTR_REQUEST_STATE_ONLY_RETRY_MISSING_OR_MUTATED",
            reason=(
                "Client must retry InputRequiredResult carrying requestState without inputRequests "
                "and echo requestState byte-for-byte (conformance#548)."
            ),
            upstream_pr=upstream_pr,
        )

    scenario_threw_exception = bool(payload.get("scenario_threw_exception", False))
    checks_json_persisted = bool(payload.get("checks_json_persisted", False))
    timeout_cleared_in_finally = bool(payload.get("timeout_cleared_in_finally", False))
    if scenario_threw_exception and not (checks_json_persisted and timeout_cleared_in_finally):
        return _verdict(
            allow=False,
            code="BLOCKED_RUNNER_THROW_LOST_CHECKS_JSON_OR_TIMEOUT",
            reason="Server runner must persist FAILURE check to checks.json and clear timeout in finally when a scenario throws (conformance#538).",
            upstream_pr=upstream_pr,
        )

    server_rejects_everything_32000 = bool(payload.get("server_rejects_everything_32000", False))
    scored_scenarios_marked_green = bool(payload.get("scored_scenarios_marked_green", False))
    if server_rejects_everything_32000 and scored_scenarios_marked_green:
        return _verdict(
            allow=False,
            code="BLOCKED_REJECT_ALL_SERVER_FALSE_GREEN",
            reason="A server rejecting all requests with -32000 must fail/untestable on validate-input and unsupported-methods instead of going green (conformance#537).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_CONFORMANCE_MRTR_STATE_ONLY_AND_RUNNER_VALID",
        reason="MRTR requestState-only echo, runner exception persistence, and reject-all control probes verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/ruby-sdk#630, #629, & #623
# ---------------------------------------------------------------------------
def evaluate_mcp_ruby_sdk_unencodable_notification_and_reply_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce unencodable buffered notification drop (`#630`), per-item `-32603`
    on unencodable response (`#629`), and stdio server survival (`#623`).
    """
    upstream_pr = "modelcontextprotocol/ruby-sdk#630, #629, #623"
    has_unencodable_buffered_notification = bool(payload.get("has_unencodable_buffered_notification", True))
    unencodable_notification_dropped = bool(payload.get("unencodable_notification_dropped", False))
    http_response_status = int(payload.get("http_response_status", 200))
    if has_unencodable_buffered_notification and (not unencodable_notification_dropped or http_response_status == 500):
        return _verdict(
            allow=False,
            code="BLOCKED_RUBY_UNENCODABLE_NOTIFICATION_CRASHED_RESPONSE_500",
            reason=(
                "Streamable HTTP transport must validate notification JSON when buffered and drop "
                "unencodable notifications instead of failing the HTTP exchange with 500 (ruby-sdk#630)."
            ),
            upstream_pr=upstream_pr,
        )

    unencodable_reply_error_code = int(payload.get("unencodable_reply_error_code", 0))
    unencodable_reply_preserves_id = bool(payload.get("unencodable_reply_preserves_id", False))
    batch_sibling_results_preserved = bool(payload.get("batch_sibling_results_preserved", False))
    stdio_server_kept_running = bool(payload.get("stdio_server_kept_running", False))
    if (
        unencodable_reply_error_code != -32603
        or not unencodable_reply_preserves_id
        or not batch_sibling_results_preserved
        or not stdio_server_kept_running
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_RUBY_UNENCODABLE_REPLY_CRASH_OR_BATCH_LOSS",
            reason=(
                "Unencodable replies must answer -32603 carrying the request id, preserve sibling batch "
                "results, and keep the stdio server running (ruby-sdk#629, #623)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_RUBY_SDK_UNENCODABLE_HANDLING_VALID",
        reason="Ruby SDK unencodable notification drop, per-item -32603 reply fallback, and stdio survival verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/ruby-sdk#628, #627, #625, #624, #622, #620, #616, & #615
# ---------------------------------------------------------------------------
def evaluate_mcp_ruby_sdk_bytes_utf8_ping_and_capabilities_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce byte-safe stdio framing (`#627`, `#625`), invalid UTF-8 JSON key `-32700` (`#624`),
    unencodable ping skip (`#628`), omitted unreadable error `id` (`#622`, `#615`), and
    stateless `listChanged`/`subscribe` stripping (`#620`).
    """
    upstream_pr = "modelcontextprotocol/ruby-sdk#628, #627, #625, #624, #622, #620, #616, #615"
    stdio_frames_stripped_as_bytes = bool(payload.get("stdio_frames_stripped_as_bytes", False))
    if not stdio_frames_stripped_as_bytes:
        return _verdict(
            allow=False,
            code="BLOCKED_RUBY_STDIO_STRING_STRIP_ENCODING_ERROR",
            reason="Client and server stdio frames must be stripped as bytes to avoid String#strip ArgumentError/EncodingError (ruby-sdk#627, #625).",
            upstream_pr=upstream_pr,
        )

    invalid_utf8_key_error_code = int(payload.get("invalid_utf8_key_error_code", 0))
    invalid_utf8_key_http_status = int(payload.get("invalid_utf8_key_http_status", 200))
    if invalid_utf8_key_error_code != -32700 or invalid_utf8_key_http_status != 400:
        return _verdict(
            allow=False,
            code="BLOCKED_RUBY_INVALID_UTF8_KEY_NOT_PARSE_ERROR_32700",
            reason=(
                f"Invalid UTF-8 JSON object key must return HTTP 400 and JSON-RPC -32700 Parse error, "
                f"got HTTP {invalid_utf8_key_http_status} / {invalid_utf8_key_error_code} (ruby-sdk#624)."
            ),
            upstream_pr=upstream_pr,
        )

    unencodable_ping_skipped = bool(payload.get("unencodable_ping_skipped", False))
    unreadable_id_omitted_from_error = bool(payload.get("unreadable_id_omitted_from_error", False))
    stateless_init_strips_list_changed_and_subscribe = bool(
        payload.get("stateless_init_strips_list_changed_and_subscribe", False)
    )
    if not (unencodable_ping_skipped and unreadable_id_omitted_from_error and stateless_init_strips_list_changed_and_subscribe):
        return _verdict(
            allow=False,
            code="BLOCKED_RUBY_PING_OR_STATELESS_CAPABILITY_DRIFT",
            reason=(
                "Ruby SDK must skip stdio pings with unencodable ids (#628), omit id when request id is unreadable (#622, #615), "
                "and strip listChanged/subscribe from stateless HTTP initialize (#620)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_RUBY_SDK_BYTES_UTF8_PING_AND_CAPABILITIES_VALID",
        reason="Ruby SDK byte framing, invalid UTF-8 key -32700, unencodable ping skip, and stateless capability stripping verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/php-sdk#613, #608, & #606
# ---------------------------------------------------------------------------
def evaluate_mcp_php_sdk_array_shape_registry_and_gateway_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce array-shape nullable/union key preservation (`#613`), custom registry
    `publishesListChanges()` (`#608`), and `2026-07-28` `ClientGateway` guidance (`#606`).
    """
    upstream_pr = "modelcontextprotocol/php-sdk#613, #608, #606"
    outer_param_schema_type = payload.get("outer_param_schema_type")
    nickname_property_type = payload.get("nickname_property_type")
    code_property_type = payload.get("code_property_type")
    if (
        outer_param_schema_type != "object"
        or sorted(nickname_property_type or []) != ["null", "string"]
        or sorted(code_property_type or []) != ["integer", "string"]
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_ARRAY_SHAPE_NULLABLE_OR_UNION_KEY_COLLAPSED",
            reason=(
                "Array shape with nullable/union keys (array{name: string, nickname: string|null, code: int|string}) "
                "must stay type='object' with inner union property types instead of collapsing to ['array', 'null'] (php-sdk#613)."
            ),
            upstream_pr=upstream_pr,
        )

    custom_registry_publishes = bool(payload.get("custom_registry_publishes_list_changes", True))
    announced_list_changed = bool(payload.get("announced_list_changed", False))
    if custom_registry_publishes and not announced_list_changed:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_CUSTOM_REGISTRY_LIST_CHANGED_SUPPRESSED",
            reason="Server must announce listChanged when RegistryInterface::publishesListChanges() is true (php-sdk#608).",
            upstream_pr=upstream_pr,
        )

    gateway_refusal_message = str(payload.get("gateway_refusal_message", ""))
    if "InputRequiredResult" not in gateway_refusal_message:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_GATEWAY_MISLEADING_REMOVED_MESSAGE",
            reason="2026-07-28 ClientGateway::sample()/listRoots() refusal must point callers to InputRequiredResult (php-sdk#606).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_PHP_SDK_ARRAY_SHAPE_REGISTRY_AND_GATEWAY_VALID",
        reason="PHP SDK array-shape nullable/union keys, custom registry listChanged, and InputRequiredResult guidance verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/php-sdk#603, #602, & #597
# ---------------------------------------------------------------------------
def evaluate_mcp_php_sdk_session_lock_sse_queue_and_202_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce unavailable session lock `-32603` (`#603`), SSE delivery of queued
    session notifications (`#602`), and `202 Accepted` with empty body on
    notification/response-only POST (`#597`).
    """
    upstream_pr = "modelcontextprotocol/php-sdk#603, #602, #597"
    lock_unavailable_http_status = int(payload.get("lock_unavailable_http_status", 200))
    lock_unavailable_error_code = int(payload.get("lock_unavailable_error_code", 0))
    lock_unavailable_message = str(payload.get("lock_unavailable_message", ""))
    if (
        lock_unavailable_http_status != 503
        or lock_unavailable_error_code != -32603
        or lock_unavailable_message != "Session lock is unavailable."
    ):
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_SESSION_LOCK_UNAVAILABLE_DIALECT_MISMATCH",
            reason=(
                "Unavailable session lock must return HTTP 503 with -32603 'Session lock is unavailable.' "
                "to match unavailable session store (php-sdk#603)."
            ),
            upstream_pr=upstream_pr,
        )

    has_queued_notifications_on_request = bool(payload.get("has_queued_notifications_on_request", True))
    request_answer_content_type = str(payload.get("request_answer_content_type", ""))
    bundled_into_json_array = bool(payload.get("bundled_into_json_array", False))
    if has_queued_notifications_on_request and (bundled_into_json_array or request_answer_content_type != "text/event-stream"):
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_QUEUED_NOTIFICATIONS_BUNDLED_AS_JSON_ARRAY",
            reason="Queued session notifications on a plain request must be sent as text/event-stream SSE ahead of the response, never bundled as a JSON array (php-sdk#602).",
            upstream_pr=upstream_pr,
        )

    notification_only_post_status = int(payload.get("notification_only_post_status", 200))
    notification_only_post_body = str(payload.get("notification_only_post_body", ""))
    notification_only_drained_queue = bool(payload.get("notification_only_drained_queue", False))
    if notification_only_post_status != 202 or notification_only_post_body != "" or notification_only_drained_queue:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_NOTIFICATION_ONLY_POST_NOT_202_EMPTY",
            reason="POST carrying only notifications/responses must return 202 Accepted with empty body and preserve queued messages (php-sdk#597).",
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_PHP_SDK_LOCK_SSE_AND_202_VALID",
        reason="PHP SDK unavailable session lock -32603, SSE queued notification delivery, and 202 empty-body POST verified.",
        upstream_pr=upstream_pr,
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/php-sdk#601, #599, & #598
# ---------------------------------------------------------------------------
def evaluate_mcp_php_sdk_fiber_send_flush_and_session_delta_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce pre-response stdio notification flush (`#601`), `{main}` fiber loop
    HTTP client sends (`#599`), and post-resume session delta persistence (`#598`).
    """
    upstream_pr = "modelcontextprotocol/php-sdk#601, #599, #598"
    stdio_wire_order = list(payload.get("stdio_wire_order", []))
    if stdio_wire_order != ["notification", "response"]:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_STDIO_RESPONSE_WRITTEN_BEFORE_NOTIFICATION",
            reason=f"handleFiberTermination() must flush queued outgoing notifications before writing the final response, got {stdio_wire_order} (php-sdk#601).",
            upstream_pr=upstream_pr,
        )

    http_send_executed_from_main = bool(payload.get("http_send_executed_from_main", False))
    if not http_send_executed_from_main:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_HTTP_SEND_INSIDE_REQUEST_FIBER",
            reason="HttpTransport::send() must suspend inside the request fiber so tick()->processSends() sends from {main} (php-sdk#599).",
            upstream_pr=upstream_pr,
        )

    stored_session_state = dict(payload.get("stored_session_state") or {})
    expected_session_state = dict(payload.get("expected_session_state") or {})
    overwrote_concurrent_keys = bool(payload.get("overwrote_concurrent_keys", False))
    if stored_session_state != expected_session_state or overwrote_concurrent_keys:
        return _verdict(
            allow=False,
            code="BLOCKED_PHP_POST_RESUME_SESSION_WRITE_LOST_OR_CLOBBERED",
            reason=(
                "Terminating suspended fiber must persist its post-resume modified session keys "
                "under the session lock without overwriting concurrent session keys (php-sdk#598)."
            ),
            upstream_pr=upstream_pr,
        )

    return _verdict(
        allow=True,
        code="ALLOW_MCP_PHP_SDK_FIBER_SEND_FLUSH_AND_SESSION_DELTA_VALID",
        reason="PHP SDK pre-response stdio flush, {main} fiber HTTP send, and post-resume session delta persistence verified.",
        upstream_pr=upstream_pr,
    )


SCENARIO_EVALUATORS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "PR-01": evaluate_ucp_schema_generate_openapi_binding_guard,
    "PR-02": evaluate_ucp_schema_open_union_and_extended_subtype_guard,
    "PR-03": evaluate_ucp_schema_profile_scoping_and_ast_normalizer_guard,
    "PR-04": evaluate_ucp_schema_slicing_lint_and_required_guard,
    "PR-05": evaluate_mcp_ext_apps_iframe_allow_and_normative_spec_guard,
    "PR-06": evaluate_mcp_ext_apps_shared_dispatcher_and_raf_cleanup_guard,
    "PR-07": evaluate_mcp_ext_apps_windows_file_url_sandbox_and_tool_prefix_guard,
    "PR-08": evaluate_mcp_ext_auth_dpop_and_sep3392_guard,
    "PR-09": evaluate_mcp_conformance_url_elicitation_and_stream_guard,
    "PR-10": evaluate_mcp_conformance_skills_agents_and_error_codes_guard,
    "PR-11": evaluate_mcp_conformance_mrtr_state_only_and_runner_guard,
    "PR-12": evaluate_mcp_ruby_sdk_unencodable_notification_and_reply_guard,
    "PR-13": evaluate_mcp_ruby_sdk_bytes_utf8_ping_and_capabilities_guard,
    "PR-14": evaluate_mcp_php_sdk_array_shape_registry_and_gateway_guard,
    "PR-15": evaluate_mcp_php_sdk_session_lock_sse_queue_and_202_guard,
    "PR-16": evaluate_mcp_php_sdk_fiber_send_flush_and_session_delta_guard,
}


def evaluate_stage226_scenario(scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    evaluator = SCENARIO_EVALUATORS.get(scenario_id)
    if evaluator is None:
        raise ValueError(f"Unknown Stage 226 scenario_id: {scenario_id}")
    return evaluator(payload)
