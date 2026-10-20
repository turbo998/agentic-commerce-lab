"""Stage 88 deterministic guardrails across UCP, ACP, Coinbase x402, and Sierra tau2-bench:

1. UCP Identity Linking OAuth 2.0 Capability-Driven Scopes, Variant `options` Rename &
   Order/Webhook Header Separation (`Universal-Commerce-Protocol/ucp #354`, `#353`, `#342`, `#370`)
2. ACP Extensions Framework JSONPath `extends`, Hierarchical `LineItem` & B2B Tax Exemption
   (`agentic-commerce-protocol/agentic-commerce-protocol #89`, `#83`)
3. Coinbase x402 EIP-712 Domain Mapping for EIP-3009 & `@x402/base` Runtime Network Scoping
   (`coinbase/x402 #324`, `#312`, `#229`)
4. Sierra tau2-bench Multilingual `LanguagePack` / `communicate_info` Judge & Submission
   Metric Validation Gate (`Sierra-Research/tau2-bench #348`, `#352`, `#342`)
"""

from __future__ import annotations

import re
from typing import Any

REVERSE_DNS_CAP_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9_]+)+(:[a-z0-9_]+)?$")
JSONPATH_EXTENDS_RE = re.compile(r"^\$\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+|\[\d+\])*$")
ALLOWED_BASE_NETWORKS = {"eip155:8453", "eip155:84532"}
ALLOWED_CERT_TYPES = {"resale", "exempt_organization", "government"}


def validate_ucp_identity_oauth_and_webhook_header_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #354 Identity Linking OAuth 2.0, #353 variant.options, and #342/#370 headers."""
    violations: list[str] = []

    identity_cfg = payload.get("identity_linking", {})
    capabilities_map = identity_cfg.get("config", {}).get("capabilities", {})
    if not isinstance(capabilities_map, dict) or not capabilities_map:
        violations.append("UCP_IDENTITY_LINKING_CAPABILITIES_MAP_MISSING")
    else:
        for cap_name, cap_rule in capabilities_map.items():
            if cap_name.startswith("ucp:scopes:") or not REVERSE_DNS_CAP_RE.match(
                str(cap_name)
            ):
                violations.append(f"UCP_IDENTITY_LEGACY_OR_INVALID_SCOPE:{cap_name}")
            if not isinstance(cap_rule, dict) or not isinstance(
                cap_rule.get("auth_required"), bool
            ):
                violations.append(f"UCP_IDENTITY_AUTH_REQUIRED_BOOL_MISSING:{cap_name}")

    if identity_cfg.get("negotiation_pruned_by_identity_linking") is True:
        violations.append("UCP_CAPABILITY_NEGOTIATION_PRUNED_BY_IDENTITY_LINKING")

    requested_scopes = identity_cfg.get("requested_scopes", [])
    for sc in requested_scopes:
        if str(sc).startswith("ucp:scopes:") or not REVERSE_DNS_CAP_RE.match(str(sc)):
            violations.append(f"UCP_OAUTH_REQUESTED_SCOPE_INVALID:{sc}")

    discovery = identity_cfg.get("discovery", {})
    rfc8414_status = discovery.get("rfc8414_status", 200)
    fell_back_to_oidc = bool(discovery.get("fell_back_to_oidc", False))
    oidc_status = discovery.get("oidc_status", 200)
    if rfc8414_status != 200:
        if rfc8414_status != 404 and fell_back_to_oidc:
            violations.append(
                f"UCP_RFC8414_NON_404_ILLEGAL_OIDC_FALLBACK:{rfc8414_status}"
            )
        if rfc8414_status == 404 and fell_back_to_oidc and oidc_status != 200:
            violations.append(f"UCP_OIDC_FALLBACK_NON_200:{oidc_status}")
        if rfc8414_status != 404 and not discovery.get("aborted", False):
            violations.append(f"UCP_RFC8414_ERROR_MUST_ABORT:{rfc8414_status}")

    oauth = identity_cfg.get("oauth_security", {})
    if oauth.get("pkce_method") != "S256":
        violations.append(f"UCP_PKCE_S256_REQUIRED:{oauth.get('pkce_method')}")
    expected_iss = oauth.get("expected_issuer")
    received_iss = oauth.get("received_issuer")
    if not expected_iss or not received_iss or expected_iss != received_iss:
        violations.append("UCP_ISSUER_BYTE_FOR_BYTE_MISMATCH")
    if oauth.get("registered_redirect_uri") != oauth.get("request_redirect_uri"):
        violations.append("UCP_REDIRECT_URI_EXACT_MATCH_REQUIRED")
    scopes_supported = oauth.get("scopes_supported")
    if not isinstance(scopes_supported, list) or not scopes_supported:
        violations.append("UCP_RFC8414_SCOPES_SUPPORTED_MISSING")
    else:
        for sc in requested_scopes:
            if sc not in scopes_supported:
                violations.append(f"UCP_REQUESTED_SCOPE_NOT_IN_METADATA:{sc}")

    auth_gate = identity_cfg.get("auth_gate_check", {})
    if auth_gate.get("auth_required") is True and not auth_gate.get(
        "has_buyer_identity_token", True
    ):
        if auth_gate.get("error_code") != "identity_required":
            violations.append("UCP_MISSING_IDENTITY_REQUIRED_ERROR_CODE")

    variant = payload.get("variant", {})
    if "selected_options" in variant:
        violations.append("UCP_VARIANT_LEGACY_SELECTED_OPTIONS_FORBIDDEN")
    if not isinstance(variant.get("options"), list) or not variant.get("options"):
        violations.append("UCP_VARIANT_OPTIONS_REQUIRED")

    webhook = payload.get("order_webhook", {})
    wb_body = webhook.get("body", {})
    wb_headers = webhook.get("headers", {})
    if "event_id" in wb_body or "created_time" in wb_body:
        violations.append("UCP_WEBHOOK_DANGLING_BODY_FIELDS_FORBIDDEN")
    if not wb_headers.get("event_id") or not wb_headers.get("created_time"):
        violations.append("UCP_WEBHOOK_EVENT_HEADERS_MISSING")

    get_order_headers = payload.get("get_order_response_headers", {})
    for required_hdr in ("Signature", "Signature-Input", "Content-Digest"):
        if not get_order_headers.get(required_hdr):
            violations.append(f"UCP_GET_ORDER_SIGNATURE_HEADER_MISSING:{required_hdr}")

    return {
        "allowed": len(violations) == 0,
        "decision_code": (
            "UCP_IDENTITY_OAUTH_AND_WEBHOOK_HEADERS_VALID"
            if not violations
            else violations[0]
        ),
        "violations": violations,
    }


def validate_acp_extensions_jsonpath_and_enhanced_checkout_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #89 Extensions Framework JSONPath & #83 Enhanced Checkout hierarchy/tax."""
    violations: list[str] = []

    extensions = payload.get("capabilities", {}).get("extensions", [])
    if not isinstance(extensions, list) or not extensions:
        violations.append("ACP_EXTENSIONS_LIST_MISSING")
    else:
        for idx, ext in enumerate(extensions):
            name = ext.get("name")
            extends = ext.get("extends")
            if not isinstance(name, str) or not name.strip():
                violations.append(f"ACP_EXTENSION_NAME_MISSING:{idx}")
            if not isinstance(extends, list) or not extends:
                violations.append(f"ACP_EXTENSION_EXTENDS_EMPTY:{idx}")
            else:
                for jp in extends:
                    if not isinstance(jp, str) or not JSONPATH_EXTENDS_RE.match(jp):
                        violations.append(f"ACP_EXTENSION_INVALID_JSONPATH:{jp}")

    applied_discounts = payload.get("discounts", {}).get("applied", [])
    priorities: list[int] = []
    for idx, disc in enumerate(applied_discounts):
        method = disc.get("method", "across")
        if method not in {"each", "across"}:
            violations.append(f"ACP_DISCOUNT_INVALID_METHOD:{method}")
        if "priority" in disc:
            prio = disc["priority"]
            if not isinstance(prio, int) or prio < 1:
                violations.append(f"ACP_DISCOUNT_INVALID_PRIORITY:{prio}")
            else:
                priorities.append(prio)
        if method == "each":
            allocs = disc.get("allocations", [])
            if not isinstance(allocs, list) or not allocs:
                violations.append(f"ACP_DISCOUNT_EACH_ALLOCATIONS_REQUIRED:{idx}")
            else:
                alloc_sum = sum(int(a.get("amount", 0)) for a in allocs)
                if alloc_sum != int(disc.get("amount", -1)):
                    violations.append(
                        f"ACP_DISCOUNT_EACH_ALLOCATION_SUM_MISMATCH:{alloc_sum}!={disc.get('amount')}"
                    )
    if len(priorities) != len(set(priorities)):
        violations.append("ACP_DISCOUNT_DUPLICATE_STACKING_PRIORITY")

    line_items = payload.get("line_items", [])
    line_ids = {
        str(li.get("id")) for li in line_items if isinstance(li, dict) and li.get("id")
    }
    for idx, li in enumerate(line_items):
        item_obj = li.get("item", {})
        if not isinstance(item_obj, dict) or set(item_obj.keys()) != {"id"}:
            violations.append(f"ACP_LINE_ITEM_REF_MUST_ONLY_CONTAIN_ID:{idx}")
        qty = li.get("quantity")
        if not isinstance(qty, int) or qty < 1:
            violations.append(f"ACP_LINE_ITEM_QUANTITY_INVALID:{idx}")
        else:
            max_q = li.get("max_quantity_per_order")
            avail_q = li.get("available_quantity")
            if isinstance(max_q, int) and qty > max_q:
                violations.append(f"ACP_LINE_ITEM_EXCEEDS_MAX_ORDER_QTY:{qty}>{max_q}")
            if (
                li.get("availability_status") == "in_stock"
                and isinstance(avail_q, int)
                and qty > avail_q
            ):
                violations.append(f"ACP_LINE_ITEM_EXCEEDS_AVAILABLE_QTY:{qty}>{avail_q}")

        parent_id = li.get("parent_id")
        if parent_id is not None:
            if parent_id == li.get("id") or str(parent_id) not in line_ids:
                violations.append(f"ACP_LINE_ITEM_INVALID_PARENT_ID:{parent_id}")

        if li.get("tax_exempt") is True:
            buyer_exempt = payload.get("buyer", {}).get("tax_exemption", {})
            checkout_ts = str(payload.get("checkout_timestamp", ""))
            expires_at = str(buyer_exempt.get("expires_at", ""))
            cert_type = buyer_exempt.get("certificate_type")
            exempt_regions = buyer_exempt.get("exempt_regions", [])
            ship_state = payload.get("shipping_region")
            if not buyer_exempt.get("certificate_id") or cert_type not in ALLOWED_CERT_TYPES:
                violations.append("ACP_TAX_EXEMPTION_CERTIFICATE_INVALID")
            if not expires_at or (checkout_ts and expires_at <= checkout_ts):
                violations.append("ACP_TAX_EXEMPTION_CERTIFICATE_EXPIRED")
            if ship_state and ship_state not in exempt_regions:
                violations.append(
                    f"ACP_TAX_EXEMPTION_REGION_NOT_COVERED:{ship_state}"
                )

    return {
        "allowed": len(violations) == 0,
        "decision_code": (
            "ACP_EXTENSIONS_AND_ENHANCED_CHECKOUT_VALID"
            if not violations
            else violations[0]
        ),
        "violations": violations,
    }


def validate_x402_eip712_domain_and_base_passthrough_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 #324 EIP-712 domain mapping for eip3009 & #312 @x402/base scoping."""
    violations: list[str] = []

    accepted = payload.get("accepted", {})
    extra = accepted.get("extra", {})
    domain = payload.get("eip712_domain", {})
    auth = payload.get("authorization", {})

    expected_name = extra.get("name")
    expected_version = extra.get("version")
    network = str(accepted.get("network", ""))
    expected_asset = str(accepted.get("asset", ""))

    if not expected_name or domain.get("name") != expected_name:
        violations.append(
            f"X402_EIP712_DOMAIN_NAME_MISMATCH:{domain.get('name')}!={expected_name}"
        )
    if not expected_version or str(domain.get("version")) != str(expected_version):
        violations.append(
            f"X402_EIP712_DOMAIN_VERSION_MISMATCH:{domain.get('version')}!={expected_version}"
        )
    if not network.startswith("eip155:") or ":" not in network:
        violations.append(f"X402_INVALID_CAIP2_EVM_NETWORK:{network}")
    else:
        chain_ref = int(network.split(":", 1)[1])
        if domain.get("chainId") != chain_ref:
            violations.append(
                f"X402_EIP712_DOMAIN_CHAINID_MISMATCH:{domain.get('chainId')}!={chain_ref}"
            )
    if (
        not expected_asset
        or str(domain.get("verifyingContract", "")).lower() != expected_asset.lower()
    ):
        violations.append("X402_EIP712_VERIFYING_CONTRACT_ASSET_MISMATCH")

    recovered_signer = str(payload.get("recovered_signer", ""))
    auth_from = str(auth.get("from", ""))
    if not recovered_signer or not auth_from or recovered_signer.lower() != auth_from.lower():
        violations.append("X402_EIP3009_RECOVERED_SIGNER_MISMATCH")

    base_pkg = payload.get("base_scheme_invocation", {})
    target_net = str(base_pkg.get("network", ""))
    scheme = str(base_pkg.get("scheme", "exact"))
    role = str(base_pkg.get("role", "client"))
    if target_net not in ALLOWED_BASE_NETWORKS:
        violations.append(f"X402_BASE_SCHEME_OFF_BASE_NETWORK_REJECTED:{target_net}")
    if scheme == "auth-capture" and role in {"server", "facilitator"}:
        violations.append(f"X402_BASE_AUTH_CAPTURE_CLIENT_ONLY:{role}")

    return {
        "allowed": len(violations) == 0,
        "decision_code": (
            "X402_EIP712_DOMAIN_AND_BASE_PASSTHROUGH_VALID"
            if not violations
            else violations[0]
        ),
        "violations": violations,
    }


def validate_tau2_multilingual_judge_and_submission_metrics_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #348/#352 multilingual judge & #342 submission metric validation."""
    violations: list[str] = []

    eval_cfg = payload.get("multilingual_eval", {})
    lang = str(eval_cfg.get("language", "en"))
    script = str(eval_cfg.get("script", "Latn"))
    explicit_param = eval_cfg.get("llm_communicate_judge_param")
    force_env = bool(eval_cfg.get("force_env_var", False))
    judge_activated = bool(eval_cfg.get("judge_activated", False))
    justification = str(eval_cfg.get("justification", ""))
    nl_prompt_has_lang_hint = bool(eval_cfg.get("nl_prompt_has_lang_hint", False))
    in_regular_sampling_pool = bool(
        eval_cfg.get("pack_persona_in_regular_sampling_pool", False)
    )

    if explicit_param is not None:
        expected_judge = bool(explicit_param)
    elif force_env:
        expected_judge = True
    else:
        expected_judge = lang != "en"

    if judge_activated != expected_judge:
        violations.append(
            f"TAU2_COMMUNICATE_JUDGE_ACTIVATION_MISMATCH:{judge_activated}!={expected_judge}"
        )
    if judge_activated and not justification.startswith("[llm_judge]"):
        violations.append("TAU2_COMMUNICATE_JUDGE_PREFIX_MISSING")
    if not judge_activated and justification.startswith("[llm_judge]"):
        violations.append("TAU2_ENGLISH_SUBSTRING_UNEXPECTED_LLM_JUDGE_PREFIX")

    if lang != "en":
        if not script or not nl_prompt_has_lang_hint:
            violations.append("TAU2_NON_ENGLISH_NL_ASSERTIONS_LANG_HINT_MISSING")
        if in_regular_sampling_pool:
            violations.append("TAU2_MULTILINGUAL_PERSONA_LEAKED_TO_REGULAR_POOL")
    else:
        if nl_prompt_has_lang_hint:
            violations.append("TAU2_ENGLISH_NL_ASSERTIONS_MUST_ remain_BYTE_IDENTICAL")

    sub = payload.get("submission_validation", {})
    declared_domains = set(sub.get("declared_domains", []))
    trajectory_domains = set(sub.get("trajectory_domains", []))
    if not declared_domains or declared_domains != trajectory_domains:
        violations.append("TAU2_SUBMISSION_MISSING_DOMAIN_RESULTS")

    declared_pass_k = sub.get("declared_pass_k", {})
    recomputed_pass_k = sub.get("recomputed_pass_k", {})
    for k, val in declared_pass_k.items():
        if k not in recomputed_pass_k or abs(float(val) - float(recomputed_pass_k[k])) > 1e-6:
            violations.append(f"TAU2_SUBMISSION_PASS_K_METRIC_MISMATCH:{k}")

    declared_cost = float(sub.get("declared_cost", 0.0))
    recomputed_cost = float(sub.get("recomputed_cost", 0.0))
    if abs(declared_cost - recomputed_cost) > 1e-6:
        violations.append("TAU2_SUBMISSION_COST_METRIC_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "decision_code": (
            "TAU2_MULTILINGUAL_JUDGE_AND_SUBMISSION_VALID"
            if not violations
            else violations[0]
        ),
        "violations": violations,
    }
