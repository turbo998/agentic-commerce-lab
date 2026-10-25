"""Stage 280 deterministic guards covering 293 zero-overlap primary-source PRs across 40 repositories.

Spans x402 streamed request cloning & AgentKit CDP idempotency (`PR-01`), AP2 dSD-JWT delegation chains &
Visa TAP post-quantum hybrid DID resolution (`PR-02`), UCP core 304 Not Modified profile fetching &
requires_escalation continue_url (`PR-03`), UCP Python SDK uniqueItems/minProperties/contains (`PR-04`),
UCP Conformance & Samples line-item quantity & sparse order serialization (`PR-05`), ACP OpenAPI inline
$ref validation & integer refund minor units (`PR-06`), A2A spec & Python SDK push-failure isolation &
ActiveTask release (`PR-07`), A2A multi-language SDKs (`PR-08`), Stripe Agent Toolkit tulip gate &
7-language SDK account scoping (`PR-09`), Sierra tau2-bench knowledge-base sandbox & 1-to-1 action matching
(`PR-10`), and MCP 11-language SDKs, Conformance, Inspector, Registry & SEP-3415/3405 (`PR-11..PR-16`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


STAGE280_PR_GROUPS: dict[str, tuple[str, ...]] = {
    "PR-01": (
        "coinbase/x402#312",
        "coinbase/x402#306",
        "coinbase/x402#297",
        "coinbase/x402#283",
        "coinbase/x402#277",
        "coinbase/x402#257",
        "coinbase/x402#412",
        "coinbase/x402#408",
        "coinbase/x402#391",
        "coinbase/x402#390",
        "coinbase/agentkit#1530",
        "coinbase/agentkit#1507",
        "coinbase/agentkit#1468",
        "coinbase/agentkit#1469",
        "coinbase/agentkit#1545",
        "coinbase/agentkit#1552",
        "coinbase/agentkit#1554",
        "coinbase/agentkit#1491",
    ),
    "PR-02": (
        "google-agentic-commerce/AP2#384",
        "google-agentic-commerce/AP2#383",
        "google-agentic-commerce/AP2#378",
        "google-agentic-commerce/AP2#377",
        "google-agentic-commerce/AP2#368",
        "google-agentic-commerce/AP2#365",
        "google-agentic-commerce/AP2#363",
        "google-agentic-commerce/AP2#359",
        "google-agentic-commerce/AP2#351",
        "google-agentic-commerce/AP2#347",
        "google-agentic-commerce/AP2#342",
        "google-agentic-commerce/AP2#335",
        "google-agentic-commerce/AP2#330",
        "google-agentic-commerce/AP2#326",
        "google-agentic-commerce/AP2#324",
        "google-agentic-commerce/AP2#318",
        "visa/trusted-agent-protocol#18",
        "visa/trusted-agent-protocol#9",
    ),
    "PR-03": (
        "Universal-Commerce-Protocol/ucp#939",
        "Universal-Commerce-Protocol/ucp#938",
        "Universal-Commerce-Protocol/ucp#934",
        "Universal-Commerce-Protocol/ucp#933",
        "Universal-Commerce-Protocol/ucp#932",
        "Universal-Commerce-Protocol/ucp#930",
        "Universal-Commerce-Protocol/ucp#928",
        "Universal-Commerce-Protocol/ucp#918",
        "Universal-Commerce-Protocol/ucp#917",
        "Universal-Commerce-Protocol/ucp#916",
        "Universal-Commerce-Protocol/ucp#915",
        "Universal-Commerce-Protocol/ucp#914",
        "Universal-Commerce-Protocol/ucp#913",
        "Universal-Commerce-Protocol/ucp#912",
        "Universal-Commerce-Protocol/ucp#911",
        "Universal-Commerce-Protocol/ucp#908",
    ),
    "PR-04": (
        "Universal-Commerce-Protocol/python-sdk#98",
        "Universal-Commerce-Protocol/python-sdk#97",
        "Universal-Commerce-Protocol/python-sdk#85",
        "Universal-Commerce-Protocol/python-sdk#84",
        "Universal-Commerce-Protocol/python-sdk#82",
        "Universal-Commerce-Protocol/python-sdk#78",
        "Universal-Commerce-Protocol/python-sdk#67",
        "Universal-Commerce-Protocol/python-sdk#65",
        "Universal-Commerce-Protocol/python-sdk#62",
        "Universal-Commerce-Protocol/python-sdk#61",
        "Universal-Commerce-Protocol/python-sdk#59",
        "Universal-Commerce-Protocol/python-sdk#58",
        "Universal-Commerce-Protocol/python-sdk#57",
        "Universal-Commerce-Protocol/python-sdk#56",
        "Universal-Commerce-Protocol/python-sdk#55",
        "Universal-Commerce-Protocol/python-sdk#52",
    ),
    "PR-05": (
        "Universal-Commerce-Protocol/conformance#93",
        "Universal-Commerce-Protocol/conformance#87",
        "Universal-Commerce-Protocol/conformance#86",
        "Universal-Commerce-Protocol/conformance#84",
        "Universal-Commerce-Protocol/conformance#83",
        "Universal-Commerce-Protocol/conformance#81",
        "Universal-Commerce-Protocol/conformance#80",
        "Universal-Commerce-Protocol/conformance#78",
        "Universal-Commerce-Protocol/conformance#77",
        "Universal-Commerce-Protocol/conformance#75",
        "Universal-Commerce-Protocol/conformance#73",
        "Universal-Commerce-Protocol/samples#243",
        "Universal-Commerce-Protocol/samples#235",
        "Universal-Commerce-Protocol/samples#234",
        "Universal-Commerce-Protocol/samples#232",
        "Universal-Commerce-Protocol/samples#224",
        "Universal-Commerce-Protocol/samples#220",
        "Universal-Commerce-Protocol/samples#214",
    ),
    "PR-06": (
        "agentic-commerce-protocol/agentic-commerce-protocol#309",
        "agentic-commerce-protocol/agentic-commerce-protocol#273",
        "agentic-commerce-protocol/agentic-commerce-protocol#270",
        "agentic-commerce-protocol/agentic-commerce-protocol#261",
        "agentic-commerce-protocol/agentic-commerce-protocol#255",
        "agentic-commerce-protocol/agentic-commerce-protocol#253",
        "agentic-commerce-protocol/agentic-commerce-protocol#252",
        "agentic-commerce-protocol/agentic-commerce-protocol#249",
        "agentic-commerce-protocol/agentic-commerce-protocol#245",
        "agentic-commerce-protocol/agentic-commerce-protocol#243",
        "agentic-commerce-protocol/agentic-commerce-protocol#241",
        "agentic-commerce-protocol/agentic-commerce-protocol#238",
        "agentic-commerce-protocol/agentic-commerce-protocol#237",
        "agentic-commerce-protocol/agentic-commerce-protocol#232",
        "agentic-commerce-protocol/agentic-commerce-protocol#230",
        "agentic-commerce-protocol/agentic-commerce-protocol#219",
    ),
    "PR-07": (
        "a2aproject/A2A#2384",
        "a2aproject/A2A#2341",
        "a2aproject/A2A#2332",
        "a2aproject/A2A#2316",
        "a2aproject/A2A#2310",
        "a2aproject/A2A#2285",
        "a2aproject/a2a-python#1348",
        "a2aproject/a2a-python#1343",
        "a2aproject/a2a-python#1340",
        "a2aproject/a2a-python#1329",
        "a2aproject/a2a-python#1304",
        "a2aproject/a2a-python#1302",
        "a2aproject/a2a-python#1301",
        "a2aproject/a2a-python#1300",
        "a2aproject/a2a-python#1298",
        "a2aproject/a2a-python#1297",
        "a2aproject/a2a-python#1287",
    ),
    "PR-08": (
        "a2aproject/a2a-js#764",
        "a2aproject/a2a-js#755",
        "a2aproject/a2a-js#748",
        "a2aproject/a2a-js#747",
        "a2aproject/a2a-js#745",
        "a2aproject/a2a-js#744",
        "a2aproject/a2a-go#467",
        "a2aproject/a2a-go#461",
        "a2aproject/a2a-go#459",
        "a2aproject/a2a-go#455",
        "a2aproject/a2a-go#448",
        "a2aproject/a2a-go#437",
        "a2aproject/a2a-java#1199",
        "a2aproject/a2a-java#1185",
        "a2aproject/a2a-java#1184",
        "a2aproject/a2a-dotnet#572",
        "a2aproject/a2a-dotnet#568",
        "a2aproject/a2a-inspector#213",
    ),
    "PR-09": (
        "stripe/agent-toolkit#560",
        "stripe/agent-toolkit#550",
        "stripe/agent-toolkit#482",
        "stripe/agent-toolkit#480",
        "stripe/agent-toolkit#469",
        "stripe/agent-toolkit#464",
        "stripe/stripe-cli#2149",
        "stripe/stripe-cli#2144",
        "stripe/stripe-cli#2090",
        "stripe/stripe-cli#2084",
        "stripe/stripe-cli#2083",
        "stripe/stripe-cli#2082",
        "stripe/stripe-python#1919",
        "stripe/stripe-python#1911",
        "stripe/stripe-node#2899",
        "stripe/stripe-go#2469",
        "stripe/stripe-go#2444",
        "stripe/stripe-dotnet#3482",
        "stripe/stripe-java#2294",
        "stripe/stripe-ruby#1995",
        "stripe/stripe-php#2170",
        "stripe/stripe-php#2151",
    ),
    "PR-10": (
        "sierra-research/tau2-bench#677",
        "sierra-research/tau2-bench#671",
        "sierra-research/tau2-bench#667",
        "sierra-research/tau2-bench#666",
        "sierra-research/tau2-bench#665",
        "sierra-research/tau2-bench#655",
        "sierra-research/tau2-bench#653",
        "sierra-research/tau2-bench#652",
        "sierra-research/tau2-bench#650",
        "sierra-research/tau2-bench#645",
        "sierra-research/tau2-bench#642",
        "sierra-research/tau2-bench#639",
        "sierra-research/tau2-bench#638",
        "sierra-research/tau2-bench#636",
        "sierra-research/tau2-bench#634",
        "sierra-research/tau2-bench#632",
    ),
    "PR-11": (
        "modelcontextprotocol/typescript-sdk#3087",
        "modelcontextprotocol/typescript-sdk#3059",
        "modelcontextprotocol/typescript-sdk#3048",
        "modelcontextprotocol/typescript-sdk#3035",
        "modelcontextprotocol/typescript-sdk#3034",
        "modelcontextprotocol/typescript-sdk#3030",
        "modelcontextprotocol/typescript-sdk#3028",
        "modelcontextprotocol/typescript-sdk#3024",
        "modelcontextprotocol/typescript-sdk#3010",
        "modelcontextprotocol/typescript-sdk#2994",
        "modelcontextprotocol/typescript-sdk#2993",
        "modelcontextprotocol/python-sdk#3746",
        "modelcontextprotocol/python-sdk#3734",
        "modelcontextprotocol/python-sdk#3700",
        "modelcontextprotocol/python-sdk#3694",
        "modelcontextprotocol/python-sdk#3672",
        "modelcontextprotocol/python-sdk#3667",
        "modelcontextprotocol/python-sdk#3663",
        "modelcontextprotocol/python-sdk#3660",
    ),
    "PR-12": (
        "modelcontextprotocol/go-sdk#1420",
        "modelcontextprotocol/go-sdk#1414",
        "modelcontextprotocol/go-sdk#1412",
        "modelcontextprotocol/go-sdk#1410",
        "modelcontextprotocol/go-sdk#1408",
        "modelcontextprotocol/go-sdk#1400",
        "modelcontextprotocol/go-sdk#1399",
        "modelcontextprotocol/go-sdk#1396",
        "modelcontextprotocol/go-sdk#1393",
        "modelcontextprotocol/go-sdk#1392",
        "modelcontextprotocol/go-sdk#1390",
        "modelcontextprotocol/go-sdk#1388",
        "modelcontextprotocol/go-sdk#1378",
        "modelcontextprotocol/rust-sdk#1370",
        "modelcontextprotocol/rust-sdk#1361",
        "modelcontextprotocol/rust-sdk#1349",
        "modelcontextprotocol/rust-sdk#1344",
        "modelcontextprotocol/rust-sdk#1343",
        "modelcontextprotocol/rust-sdk#1328",
        "modelcontextprotocol/rust-sdk#1326",
        "modelcontextprotocol/rust-sdk#1319",
        "modelcontextprotocol/rust-sdk#1306",
    ),
    "PR-13": (
        "modelcontextprotocol/csharp-sdk#1943",
        "modelcontextprotocol/csharp-sdk#1924",
        "modelcontextprotocol/csharp-sdk#1921",
        "modelcontextprotocol/csharp-sdk#1906",
        "modelcontextprotocol/csharp-sdk#1903",
        "modelcontextprotocol/csharp-sdk#1900",
        "modelcontextprotocol/csharp-sdk#1891",
        "modelcontextprotocol/csharp-sdk#1890",
        "modelcontextprotocol/java-sdk#1271",
        "modelcontextprotocol/java-sdk#1264",
        "modelcontextprotocol/java-sdk#1259",
        "modelcontextprotocol/java-sdk#1258",
        "modelcontextprotocol/kotlin-sdk#1130",
        "modelcontextprotocol/kotlin-sdk#1103",
        "modelcontextprotocol/kotlin-sdk#1102",
        "modelcontextprotocol/kotlin-sdk#1101",
        "modelcontextprotocol/kotlin-sdk#1100",
    ),
    "PR-14": (
        "modelcontextprotocol/swift-sdk#313",
        "modelcontextprotocol/swift-sdk#309",
        "modelcontextprotocol/swift-sdk#303",
        "modelcontextprotocol/swift-sdk#302",
        "modelcontextprotocol/swift-sdk#301",
        "modelcontextprotocol/swift-sdk#300",
        "modelcontextprotocol/swift-sdk#298",
        "modelcontextprotocol/swift-sdk#295",
        "modelcontextprotocol/swift-sdk#293",
        "modelcontextprotocol/swift-sdk#292",
        "modelcontextprotocol/swift-sdk#291",
        "modelcontextprotocol/swift-sdk#288",
        "modelcontextprotocol/swift-sdk#278",
        "modelcontextprotocol/swift-sdk#269",
        "modelcontextprotocol/swift-sdk#268",
        "modelcontextprotocol/swift-sdk#267",
    ),
    "PR-15": (
        "modelcontextprotocol/ruby-sdk#629",
        "modelcontextprotocol/ruby-sdk#627",
        "modelcontextprotocol/ruby-sdk#624",
        "modelcontextprotocol/ruby-sdk#623",
        "modelcontextprotocol/ruby-sdk#616",
        "modelcontextprotocol/ruby-sdk#615",
        "modelcontextprotocol/ruby-sdk#614",
        "modelcontextprotocol/ruby-sdk#604",
        "modelcontextprotocol/ruby-sdk#591",
        "modelcontextprotocol/ruby-sdk#590",
        "modelcontextprotocol/ruby-sdk#585",
        "modelcontextprotocol/ruby-sdk#583",
        "modelcontextprotocol/php-sdk#606",
        "modelcontextprotocol/php-sdk#602",
        "modelcontextprotocol/php-sdk#597",
        "modelcontextprotocol/php-sdk#596",
        "modelcontextprotocol/php-sdk#589",
        "modelcontextprotocol/php-sdk#588",
        "modelcontextprotocol/php-sdk#581",
        "modelcontextprotocol/php-sdk#576",
        "modelcontextprotocol/php-sdk#572",
        "modelcontextprotocol/php-sdk#570",
    ),
    "PR-16": (
        "modelcontextprotocol/conformance#560",
        "modelcontextprotocol/conformance#558",
        "modelcontextprotocol/conformance#555",
        "modelcontextprotocol/conformance#554",
        "modelcontextprotocol/conformance#537",
        "modelcontextprotocol/conformance#534",
        "modelcontextprotocol/conformance#528",
        "modelcontextprotocol/conformance#527",
        "modelcontextprotocol/conformance#525",
        "modelcontextprotocol/conformance#524",
        "modelcontextprotocol/conformance#523",
        "modelcontextprotocol/conformance#508",
        "modelcontextprotocol/inspector#2747",
        "modelcontextprotocol/inspector#2737",
        "modelcontextprotocol/inspector#2735",
        "modelcontextprotocol/inspector#2731",
        "modelcontextprotocol/inspector#2714",
        "modelcontextprotocol/inspector#2713",
        "modelcontextprotocol/registry#1735",
        "modelcontextprotocol/registry#1726",
        "modelcontextprotocol/modelcontextprotocol#3415",
        "modelcontextprotocol/modelcontextprotocol#3405",
    ),
}


@dataclass(frozen=True)
class GuardEvaluation:
    scenario_id: str
    passed: bool
    reason_code: str
    cited_prs: tuple[str, ...]
    details: dict[str, Any]


def evaluate_x402_stream_clone_and_agentkit_cdp_idempotency_guard(
    *,
    request_is_stream: bool,
    request_cloned_before_402_retry: bool,
    unparseable_accepts_skipped: bool,
    valid_accepts_remaining: int,
    signer_address: str,
    cdp_value_moving: bool,
    cdp_idempotency_key: str,
    evm_expected_address: str,
    evm_actual_address: str,
    quote_amount_minor: int,
    auto_pay_limit_minor: int,
    quote_settlement_identity_bound: bool,
    preflight_passed: bool,
) -> GuardEvaluation:
    """PR-01: coinbase/x402 (#306, #297, #277, #283, #312) & coinbase/agentkit (#1530, #1507, #1468, #1545)."""
    cited = STAGE280_PR_GROUPS["PR-01"]
    if request_is_stream and not request_cloned_before_402_retry:
        return GuardEvaluation(
            "PR-01",
            False,
            "X402_STREAMED_REQUEST_NOT_CLONED_BEFORE_RETRY",
            cited,
            {"request_is_stream": request_is_stream},
        )
    if not unparseable_accepts_skipped or valid_accepts_remaining <= 0:
        return GuardEvaluation(
            "PR-01",
            False,
            "X402_ACCEPTS_PARSE_CRASH_OR_EMPTY",
            cited,
            {"valid_accepts_remaining": valid_accepts_remaining},
        )
    if not signer_address.strip().startswith("0x") or len(signer_address.strip()) != 42:
        return GuardEvaluation(
            "PR-01",
            False,
            "X402_EVM_SIGNER_MISSING_ADDRESS",
            cited,
            {"signer_address": signer_address},
        )
    if cdp_value_moving and not cdp_idempotency_key.strip():
        return GuardEvaluation(
            "PR-01",
            False,
            "AGENTKIT_CDP_MISSING_IDEMPOTENCY_KEY",
            cited,
            {"cdp_value_moving": cdp_value_moving},
        )
    if evm_expected_address.strip().lower() != evm_actual_address.strip().lower():
        return GuardEvaluation(
            "PR-01",
            False,
            "AGENTKIT_EVM_ADDRESS_MISMATCH",
            cited,
            {"expected": evm_expected_address, "actual": evm_actual_address},
        )
    if quote_amount_minor > auto_pay_limit_minor or not quote_settlement_identity_bound or not preflight_passed:
        return GuardEvaluation(
            "PR-01",
            False,
            "AGENTKIT_X402_QUOTE_OR_AUTOPAY_LIMIT_VIOLATION",
            cited,
            {
                "quote_amount_minor": quote_amount_minor,
                "auto_pay_limit_minor": auto_pay_limit_minor,
                "quote_settlement_identity_bound": quote_settlement_identity_bound,
            },
        )
    return GuardEvaluation(
        "PR-01",
        True,
        "X402_STREAM_CLONE_AND_AGENTKIT_IDEMPOTENCY_VERIFIED",
        cited,
        {"quote_amount_minor": quote_amount_minor, "valid_accepts_remaining": valid_accepts_remaining},
    )


def evaluate_ap2_sdjwt_delegation_and_visa_tap_pqc_guard(
    *,
    has_reference_in_store_cb_callable: bool,
    cnf_jwk_dumped_in_json_mode: bool,
    execution_date_iso: str,
    window_start_iso: str,
    window_end_iso: str,
    currency: str,
    budget_max_major: float,
    budget_max_minor: int,
    requested_minor: int,
    terminal_kb_aud_present: bool,
    terminal_kb_nonce_present: bool,
    closed_checkout_binding_verified: bool,
    mandate_already_consumed: bool,
    rail_confirmation_verified: bool,
    tap_did_key_resolved: bool,
    tap_hybrid_alg: str,
    tap_mtls_authorized: bool,
) -> GuardEvaluation:
    """PR-02: google-agentic-commerce/AP2 (#384, #383, #378, #377, #368, #347, #342, #335, #330) & visa/TAP (#18, #9)."""
    cited = STAGE280_PR_GROUPS["PR-02"]
    if not has_reference_in_store_cb_callable or not cnf_jwk_dumped_in_json_mode:
        return GuardEvaluation(
            "PR-02",
            False,
            "AP2_RECEIPT_CALLBACK_OR_CNF_JWK_MODE_INVALID",
            cited,
            {"has_reference_in_store_cb_callable": has_reference_in_store_cb_callable},
        )
    try:
        exec_dt = datetime.fromisoformat(execution_date_iso.replace("Z", "+00:00"))
        start_dt = datetime.fromisoformat(window_start_iso.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(window_end_iso.replace("Z", "+00:00"))
    except ValueError:
        return GuardEvaluation("PR-02", False, "AP2_EXECUTION_DATE_NOT_ISO8601", cited, {})
    if not (start_dt <= exec_dt <= end_dt):
        return GuardEvaluation(
            "PR-02",
            False,
            "AP2_EXECUTION_DATE_OUTSIDE_WINDOW",
            cited,
            {"execution_date_iso": execution_date_iso},
        )
    exponent = 0 if currency.upper() in {"JPY", "KRW", "VND"} else (3 if currency.upper() in {"BHD", "KWD"} else 2)
    expected_minor = int(round(budget_max_major * (10**exponent)))
    if budget_max_minor != expected_minor or requested_minor > budget_max_minor:
        return GuardEvaluation(
            "PR-02",
            False,
            "AP2_ISO4217_MINOR_UNIT_BUDGET_CAP_VIOLATION",
            cited,
            {"currency": currency, "expected_minor": expected_minor, "budget_max_minor": budget_max_minor},
        )
    if (
        not terminal_kb_aud_present
        or not terminal_kb_nonce_present
        or not closed_checkout_binding_verified
        or mandate_already_consumed
        or not rail_confirmation_verified
    ):
        return GuardEvaluation(
            "PR-02",
            False,
            "AP2_SDJWT_TERMINAL_HOP_OR_ATOMIC_MANDATE_FAILURE",
            cited,
            {"mandate_already_consumed": mandate_already_consumed},
        )
    if not tap_did_key_resolved or tap_hybrid_alg != "Ed25519+ML-DSA-65" or not tap_mtls_authorized:
        return GuardEvaluation(
            "PR-02",
            False,
            "VISA_TAP_DID_OR_PQC_HYBRID_MTLS_REJECTED",
            cited,
            {"tap_hybrid_alg": tap_hybrid_alg, "tap_mtls_authorized": tap_mtls_authorized},
        )
    return GuardEvaluation(
        "PR-02",
        True,
        "AP2_SDJWT_AND_VISA_TAP_PQC_VERIFIED",
        cited,
        {"currency": currency, "budget_max_minor": budget_max_minor, "tap_hybrid_alg": tap_hybrid_alg},
    )


def evaluate_ucp_304_profile_escalation_and_deferred_payment_guard(
    *,
    profile_http_status: int,
    has_cached_profile: bool,
    treated_304_as_redirect_error: bool,
    checkout_status: str,
    continue_url: str,
    is_complete_checkout_request: bool,
    has_cart_id_field: bool,
    payment_terms_deferred: bool,
    payment_object: dict[str, Any] | None,
    ap2_mandate_verified_by_cp: bool,
    content_digest_matches: bool,
) -> GuardEvaluation:
    """PR-03: Universal-Commerce-Protocol/ucp (#933, #932, #917, #916, #915, #912, #911, #908)."""
    cited = STAGE280_PR_GROUPS["PR-03"]
    if profile_http_status == 304 and (treated_304_as_redirect_error or not has_cached_profile):
        return GuardEvaluation(
            "PR-03",
            False,
            "UCP_304_NOT_MODIFIED_MISCLASSIFIED_AS_REDIRECT",
            cited,
            {"profile_http_status": profile_http_status},
        )
    if checkout_status == "requires_escalation" and not continue_url.strip().startswith("https://"):
        return GuardEvaluation(
            "PR-03",
            False,
            "UCP_REQUIRES_ESCALATION_MISSING_CONTINUE_URL",
            cited,
            {"checkout_status": checkout_status, "continue_url": continue_url},
        )
    if is_complete_checkout_request and has_cart_id_field:
        return GuardEvaluation(
            "PR-03",
            False,
            "UCP_COMPLETE_CHECKOUT_FORBIDS_CART_ID",
            cited,
            {"has_cart_id_field": has_cart_id_field},
        )
    if payment_terms_deferred:
        if payment_object is None or len(payment_object) != 0:
            return GuardEvaluation(
                "PR-03",
                False,
                "UCP_DEFERRED_TERMS_REQUIRE_EMPTY_PAYMENT_OBJECT",
                cited,
                {"payment_object": payment_object},
            )
    if not ap2_mandate_verified_by_cp or not content_digest_matches:
        return GuardEvaluation(
            "PR-03",
            False,
            "UCP_AP2_MANDATE_OR_CONTENT_DIGEST_INVALID",
            cited,
            {"ap2_mandate_verified_by_cp": ap2_mandate_verified_by_cp},
        )
    return GuardEvaluation(
        "PR-03",
        True,
        "UCP_304_ESCALATION_AND_DEFERRED_TERMS_VERIFIED",
        cited,
        {"checkout_status": checkout_status, "profile_http_status": profile_http_status},
    )


def evaluate_ucp_python_sdk_unique_items_and_contains_guard(
    *,
    array_items: list[str],
    unique_items_required: bool,
    validator_scoped_to_declaring_class: bool,
    required_contains_token: str,
    min_contains: int,
    max_contains: int,
    object_properties_count: int,
    min_properties: int,
    catalog_included_in_ucp_metadata_union: bool,
    transition_ucp_request_handled: bool,
) -> GuardEvaluation:
    """PR-04: Universal-Commerce-Protocol/python-sdk (#67, #61, #59, #58, #57, #55, #52)."""
    cited = STAGE280_PR_GROUPS["PR-04"]
    if unique_items_required and len(set(array_items)) != len(array_items):
        return GuardEvaluation(
            "PR-04",
            False,
            "UCP_PY_SDK_UNIQUE_ITEMS_VIOLATION",
            cited,
            {"array_items": array_items},
        )
    if not validator_scoped_to_declaring_class:
        return GuardEvaluation(
            "PR-04",
            False,
            "UCP_PY_SDK_VALIDATOR_SCOPE_LEAK",
            cited,
            {},
        )
    contains_hits = sum(1 for item in array_items if item == required_contains_token)
    if not (min_contains <= contains_hits <= max_contains):
        return GuardEvaluation(
            "PR-04",
            False,
            "UCP_PY_SDK_CONTAINS_BOUNDS_VIOLATION",
            cited,
            {"contains_hits": contains_hits, "min_contains": min_contains, "max_contains": max_contains},
        )
    if object_properties_count < min_properties:
        return GuardEvaluation(
            "PR-04",
            False,
            "UCP_PY_SDK_MIN_PROPERTIES_VIOLATION",
            cited,
            {"object_properties_count": object_properties_count, "min_properties": min_properties},
        )
    if not catalog_included_in_ucp_metadata_union or not transition_ucp_request_handled:
        return GuardEvaluation(
            "PR-04",
            False,
            "UCP_PY_SDK_METADATA_UNION_OR_TRANSITION_MARKER_ERROR",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-04",
        True,
        "UCP_PY_SDK_CONSTRAINTS_VERIFIED",
        cited,
        {"contains_hits": contains_hits, "object_properties_count": object_properties_count},
    )


def evaluate_ucp_conformance_and_samples_order_envelope_guard(
    *,
    line_item_quantities: list[int],
    order_response_has_null_padded_optionals: bool,
    missing_order_returns_ucp_envelope: bool,
    invalid_input_routed_via_discovered_endpoint: bool,
    checkout_creation_status_code: int,
    in_band_payment_and_fulfillment_errors_accepted: bool,
    webhook_uses_checkout_line_item_ids: bool,
) -> GuardEvaluation:
    """PR-05: Universal-Commerce-Protocol/conformance (#87, #83, #81, #78, #77, #75) & samples (#243, #224, #220, #214)."""
    cited = STAGE280_PR_GROUPS["PR-05"]
    if not line_item_quantities or any(q <= 0 for q in line_item_quantities):
        return GuardEvaluation(
            "PR-05",
            False,
            "UCP_SAMPLES_INVALID_LINE_ITEM_QUANTITY",
            cited,
            {"line_item_quantities": line_item_quantities},
        )
    if order_response_has_null_padded_optionals or not missing_order_returns_ucp_envelope:
        return GuardEvaluation(
            "PR-05",
            False,
            "UCP_SAMPLES_NULL_PADDING_OR_MISSING_ORDER_ENVELOPE_ERROR",
            cited,
            {"order_response_has_null_padded_optionals": order_response_has_null_padded_optionals},
        )
    if checkout_creation_status_code not in {200, 201}:
        return GuardEvaluation(
            "PR-05",
            False,
            "UCP_CONFORMANCE_UNEXPECTED_CREATION_STATUS",
            cited,
            {"checkout_creation_status_code": checkout_creation_status_code},
        )
    if (
        not invalid_input_routed_via_discovered_endpoint
        or not in_band_payment_and_fulfillment_errors_accepted
        or not webhook_uses_checkout_line_item_ids
    ):
        return GuardEvaluation(
            "PR-05",
            False,
            "UCP_CONFORMANCE_ENDPOINT_OR_LINE_ITEM_ID_DRIFT",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-05",
        True,
        "UCP_CONFORMANCE_AND_SAMPLES_VERIFIED",
        cited,
        {"checkout_creation_status_code": checkout_creation_status_code},
    )


def evaluate_acp_openapi_examples_and_minor_unit_refund_guard(
    *,
    openapi_inline_examples_match_ref_schemas: bool,
    delegate_payment_error_envelope_unwrapped: bool,
    refund_amount_value: Any,
    checkout_line_items_match_schema: bool,
    session_context_telemetry_present: bool,
    upsert_products_response_in_feed_bundle: bool,
) -> GuardEvaluation:
    """PR-06: agentic-commerce-protocol/agentic-commerce-protocol (#270, #255, #252, #249, #243, #241, #238, #219)."""
    cited = STAGE280_PR_GROUPS["PR-06"]
    if not isinstance(refund_amount_value, int) or isinstance(refund_amount_value, bool) or refund_amount_value <= 0:
        return GuardEvaluation(
            "PR-06",
            False,
            "ACP_REFUND_AMOUNT_NOT_POSITIVE_INTEGER_MINOR_UNITS",
            cited,
            {"refund_amount_value": refund_amount_value},
        )
    if not openapi_inline_examples_match_ref_schemas or not delegate_payment_error_envelope_unwrapped:
        return GuardEvaluation(
            "PR-06",
            False,
            "ACP_OPENAPI_INLINE_EXAMPLE_OR_ERROR_ENVELOPE_DRIFT",
            cited,
            {},
        )
    if (
        not checkout_line_items_match_schema
        or not session_context_telemetry_present
        or not upsert_products_response_in_feed_bundle
    ):
        return GuardEvaluation(
            "PR-06",
            False,
            "ACP_LINE_ITEM_OR_SESSION_CONTEXT_SCHEMA_MISMATCH",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-06",
        True,
        "ACP_OPENAPI_EXAMPLES_AND_REFUND_MINOR_UNITS_VERIFIED",
        cited,
        {"refund_amount_value": refund_amount_value},
    )


def evaluate_a2a_python_push_isolation_and_active_task_guard(
    *,
    push_notification_failed: bool,
    task_lifecycle_aborted_by_push_failure: bool,
    direct_message_response_completed: bool,
    active_task_released: bool,
    followup_message_preserved_on_reemit: bool,
    malformed_jsonrpc_printed_traceback_to_stderr: bool,
    non_status_rest_error_handled: bool,
    terminal_error_names_task_state: bool,
    sender_attribution_valid: bool,
) -> GuardEvaluation:
    """PR-07: a2aproject/A2A (#2310, #2316) & a2a-python (#1329, #1302, #1301, #1300, #1298, #1297, #1287)."""
    cited = STAGE280_PR_GROUPS["PR-07"]
    if push_notification_failed and task_lifecycle_aborted_by_push_failure:
        return GuardEvaluation(
            "PR-07",
            False,
            "A2A_PYTHON_PUSH_FAILURE_ABORTED_TASK_LIFECYCLE",
            cited,
            {},
        )
    if direct_message_response_completed and not active_task_released:
        return GuardEvaluation(
            "PR-07",
            False,
            "A2A_PYTHON_ACTIVE_TASK_LEAKED_AFTER_DIRECT_MESSAGE",
            cited,
            {},
        )
    if malformed_jsonrpc_printed_traceback_to_stderr:
        return GuardEvaluation(
            "PR-07",
            False,
            "A2A_PYTHON_STDERR_TRACEBACK_LEAK_ON_MALFORMED_JSONRPC",
            cited,
            {},
        )
    if (
        not followup_message_preserved_on_reemit
        or not non_status_rest_error_handled
        or not terminal_error_names_task_state
        or not sender_attribution_valid
    ):
        return GuardEvaluation(
            "PR-07",
            False,
            "A2A_PYTHON_FOLLOWUP_OR_REST_ERROR_CONTRACT_VIOLATION",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-07",
        True,
        "A2A_PYTHON_PUSH_ISOLATION_AND_ACTIVE_TASK_VERIFIED",
        cited,
        {"active_task_released": active_task_released},
    )


def evaluate_a2a_multilang_streaming_and_tenant_routing_guard(
    *,
    js_jsonrpc_error_http_status: int,
    js_media_type_matches_default_input_modes: bool,
    js_unapplied_migration_downgrade_refused: bool,
    go_streaming_json_error_surfaced: bool,
    go_page_token_preserves_task_id_underscore: bool,
    java_failed_terminal_enqueue_recovered: bool,
    java_multitenant_card_resolved_via_router: bool,
    dotnet_loopback_push_destination_opt_in: bool,
    dotnet_is_loopback_push: bool,
) -> GuardEvaluation:
    """PR-08: a2a-js (#755, #748, #747, #745), a2a-go (#467, #459), a2a-java (#1185, #1184), a2a-dotnet (#568)."""
    cited = STAGE280_PR_GROUPS["PR-08"]
    if js_jsonrpc_error_http_status != 200 or not js_media_type_matches_default_input_modes or not js_unapplied_migration_downgrade_refused:
        return GuardEvaluation(
            "PR-08",
            False,
            "A2A_JS_JSONRPC_STATUS_OR_INPUT_MODE_VIOLATION",
            cited,
            {"js_jsonrpc_error_http_status": js_jsonrpc_error_http_status},
        )
    if not go_streaming_json_error_surfaced or not go_page_token_preserves_task_id_underscore:
        return GuardEvaluation(
            "PR-08",
            False,
            "A2A_GO_STREAMING_ERROR_OR_UNDERSCORE_TOKEN_TRUNCATION",
            cited,
            {},
        )
    if not java_failed_terminal_enqueue_recovered or not java_multitenant_card_resolved_via_router:
        return GuardEvaluation(
            "PR-08",
            False,
            "A2A_JAVA_TERMINAL_ENQUEUE_OR_TENANT_ROUTER_FAILURE",
            cited,
            {},
        )
    if dotnet_is_loopback_push and not dotnet_loopback_push_destination_opt_in:
        return GuardEvaluation(
            "PR-08",
            False,
            "A2A_DOTNET_LOOPBACK_PUSH_WITHOUT_OPT_IN",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-08",
        True,
        "A2A_MULTILANG_STREAMING_AND_TENANT_ROUTING_VERIFIED",
        cited,
        {"js_jsonrpc_error_http_status": js_jsonrpc_error_http_status},
    )


def evaluate_stripe_tulip_gate_and_sdk_account_scoping_guard(
    *,
    tulip_admission_gate_passed: bool,
    model_id: str,
    resolved_max_tokens: int,
    cli_plugin_is_known: bool,
    cli_auto_install_allowed: bool,
    event_handler_account_scoped_across_py_java_php: bool,
    php_malformed_webhook_sig_items_handled: bool,
    go_normalized_path_param_valid: bool,
    python_service_path_params_positional_only: bool,
) -> GuardEvaluation:
    """PR-09: stripe/agent-toolkit (#482, #464), stripe-cli (#2149, #2084), & Stripe SDKs (#1911, #2294, #2151, #2170)."""
    cited = STAGE280_PR_GROUPS["PR-09"]
    if not tulip_admission_gate_passed:
        return GuardEvaluation(
            "PR-09",
            False,
            "STRIPE_TULIP_RUN_TOOL_ADMISSION_GATE_DENIED",
            cited,
            {},
        )
    normalized_model = model_id.replace(".", "-")
    if "claude-3-5" in normalized_model or "claude-4" in normalized_model or "gpt-5" in normalized_model:
        if resolved_max_tokens <= 0:
            return GuardEvaluation(
                "PR-09",
                False,
                "STRIPE_DOT_FORM_MODEL_MAX_TOKENS_UNRESOLVED",
                cited,
                {"model_id": model_id, "resolved_max_tokens": resolved_max_tokens},
            )
    if not cli_plugin_is_known and cli_auto_install_allowed:
        return GuardEvaluation(
            "PR-09",
            False,
            "STRIPE_CLI_UNKNOWN_PLUGIN_AUTO_INSTALL_BLOCKED",
            cited,
            {},
        )
    if (
        not event_handler_account_scoped_across_py_java_php
        or not php_malformed_webhook_sig_items_handled
        or not go_normalized_path_param_valid
        or not python_service_path_params_positional_only
    ):
        return GuardEvaluation(
            "PR-09",
            False,
            "STRIPE_SDK_ACCOUNT_SCOPING_OR_WEBHOOK_SIG_ERROR",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-09",
        True,
        "STRIPE_TULIP_GATE_AND_SDK_ACCOUNT_SCOPING_VERIFIED",
        cited,
        {"model_id": model_id, "resolved_max_tokens": resolved_max_tokens},
    )


def evaluate_tau2_knowledge_sandbox_and_evaluator_matching_guard(
    *,
    requested_read_path: str,
    knowledge_base_root: str,
    shell_env_keys: set[str],
    gold_action_count: int,
    matched_unique_tool_call_count: int,
    reused_single_tool_call_for_multiple_gold: bool,
    exchange_old_item_id: str,
    exchange_new_item_id: str,
    mmsc_url: str,
    can_send_mms_result: bool,
) -> GuardEvaluation:
    """PR-10: sierra-research/tau2-bench (#667, #666, #665, #655, #653, #650, #634, #671)."""
    cited = STAGE280_PR_GROUPS["PR-10"]
    norm_req = requested_read_path.replace("\\", "/").lstrip("/")
    norm_root = knowledge_base_root.replace("\\", "/").lstrip("/")
    if ".." in norm_req.split("/") or not norm_req.startswith(norm_root):
        return GuardEvaluation(
            "PR-10",
            False,
            "TAU2_KNOWLEDGE_SANDBOX_OUTSIDE_READ_DENIED",
            cited,
            {"requested_read_path": requested_read_path, "knowledge_base_root": knowledge_base_root},
        )
    forbidden_env = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "STRIPE_API_KEY"}
    if shell_env_keys & forbidden_env:
        return GuardEvaluation(
            "PR-10",
            False,
            "TAU2_SANDBOX_SHELL_SECRET_ENV_LEAK",
            cited,
            {"leaked": sorted(shell_env_keys & forbidden_env)},
        )
    if reused_single_tool_call_for_multiple_gold or matched_unique_tool_call_count != gold_action_count:
        return GuardEvaluation(
            "PR-10",
            False,
            "TAU2_EVALUATOR_NON_BIJECTIVE_ACTION_MATCH",
            cited,
            {"gold_action_count": gold_action_count, "matched_unique_tool_call_count": matched_unique_tool_call_count},
        )
    if exchange_old_item_id == exchange_new_item_id:
        return GuardEvaluation(
            "PR-10",
            False,
            "TAU2_RETAIL_SAME_ITEM_EXCHANGE_REJECTED",
            cited,
            {"item_id": exchange_old_item_id},
        )
    if not mmsc_url.strip() and can_send_mms_result:
        return GuardEvaluation(
            "PR-10",
            False,
            "TAU2_TELECOM_EMPTY_MMSC_URL_TREATED_AS_CONFIGURED",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-10",
        True,
        "TAU2_KNOWLEDGE_SANDBOX_AND_EVALUATOR_VERIFIED",
        cited,
        {"gold_action_count": gold_action_count},
    )


def evaluate_mcp_ts_py_uri_fragment_and_dpop_guard(
    *,
    uri_template_matched_value: str,
    stale_stdio_frames_cleared_on_restart: bool,
    dpop_proof_attached_on_token_request: bool,
    bytes_tool_output_base64_encoded: bool,
    invalid_host_origin_crashed_sse_server: bool,
    completion_items_count: int,
    completion_page_size: int,
) -> GuardEvaluation:
    """PR-11: modelcontextprotocol/typescript-sdk (#3034, #3030, #3010, #2993) & python-sdk (#3700, #3672, #3667, #3663, #3660)."""
    cited = STAGE280_PR_GROUPS["PR-11"]
    if "#" in uri_template_matched_value:
        return GuardEvaluation(
            "PR-11",
            False,
            "MCP_TS_URI_TEMPLATE_MATCHED_FRAGMENT_DELIMITER",
            cited,
            {"uri_template_matched_value": uri_template_matched_value},
        )
    if not stale_stdio_frames_cleared_on_restart:
        return GuardEvaluation(
            "PR-11",
            False,
            "MCP_TS_STALE_STDIO_FRAMES_NOT_CLEARED",
            cited,
            {},
        )
    if not dpop_proof_attached_on_token_request or not bytes_tool_output_base64_encoded or invalid_host_origin_crashed_sse_server:
        return GuardEvaluation(
            "PR-11",
            False,
            "MCP_PY_DPOP_OR_BYTES_OUTPUT_OR_SSE_HOST_CRASH",
            cited,
            {},
        )
    if completion_items_count > 100 and completion_page_size > 100:
        return GuardEvaluation(
            "PR-11",
            False,
            "MCP_PY_COMPLETION_EXCEEDS_100_ITEM_PAGE_LIMIT",
            cited,
            {"completion_items_count": completion_items_count, "completion_page_size": completion_page_size},
        )
    return GuardEvaluation(
        "PR-11",
        True,
        "MCP_TS_PY_URI_FRAGMENT_AND_DPOP_VERIFIED",
        cited,
        {"completion_page_size": completion_page_size},
    )


def evaluate_mcp_go_rust_preinit_and_stateless_2026_07_28_guard(
    *,
    request_before_initialize: bool,
    preinit_error_code: int,
    peer_cancellation_bound_before_id_reuse: bool,
    resource_metadata_secret_redacted: bool,
    session_protocol_version: str,
    server_to_client_request_attempted: bool,
    server_to_client_request_rejected: bool,
    host_and_origin_literals_validated: bool,
    multiline_auth_secret_rejected: bool,
) -> GuardEvaluation:
    """PR-12: modelcontextprotocol/go-sdk (#1400, #1396, #1393, #1390, #1378) & rust-sdk (#1349, #1344, #1343, #1326, #1319, #1306)."""
    cited = STAGE280_PR_GROUPS["PR-12"]
    if request_before_initialize and preinit_error_code != -32600:
        return GuardEvaluation(
            "PR-12",
            False,
            "MCP_GO_PREINIT_REQUEST_NOT_REJECTED_WITH_INVALID_REQUEST",
            cited,
            {"preinit_error_code": preinit_error_code},
        )
    if not peer_cancellation_bound_before_id_reuse or not resource_metadata_secret_redacted:
        return GuardEvaluation(
            "PR-12",
            False,
            "MCP_GO_CANCELLATION_REUSE_OR_METADATA_SECRET_LEAK",
            cited,
            {},
        )
    if session_protocol_version == "2026-07-28" and server_to_client_request_attempted and not server_to_client_request_rejected:
        return GuardEvaluation(
            "PR-12",
            False,
            "MCP_RUST_2026_07_28_SERVER_TO_CLIENT_REQUEST_ALLOWED",
            cited,
            {"session_protocol_version": session_protocol_version},
        )
    if not host_and_origin_literals_validated or not multiline_auth_secret_rejected:
        return GuardEvaluation(
            "PR-12",
            False,
            "MCP_RUST_HOST_ORIGIN_OR_MULTILINE_SECRET_VIOLATION",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-12",
        True,
        "MCP_GO_RUST_PREINIT_AND_2026_07_28_VERIFIED",
        cited,
        {"session_protocol_version": session_protocol_version},
    )


def evaluate_mcp_csharp_java_kotlin_id_jag_and_rfc3986_guard(
    *,
    discovered_issuer: str,
    id_jag_audience: str,
    cancellation_misreported_as_missing_oauth_meta: bool,
    comma_separated_uri_vars_split: bool,
    java_bare_cr_terminated_message: bool,
    kotlin_sse_endpoint_resolved_per_rfc3986: bool,
    kotlin_stdio_kept_running_on_handler_cancel: bool,
) -> GuardEvaluation:
    """PR-13: modelcontextprotocol/csharp-sdk (#1900, #1891, #1890), java-sdk (#1264), kotlin-sdk (#1103, #1101, #1100)."""
    cited = STAGE280_PR_GROUPS["PR-13"]
    if not discovered_issuer.strip() or discovered_issuer.strip() != id_jag_audience.strip():
        return GuardEvaluation(
            "PR-13",
            False,
            "MCP_CSHARP_ID_JAG_AUDIENCE_MISMATCH_WITH_DISCOVERED_ISSUER",
            cited,
            {"discovered_issuer": discovered_issuer, "id_jag_audience": id_jag_audience},
        )
    if cancellation_misreported_as_missing_oauth_meta or not comma_separated_uri_vars_split:
        return GuardEvaluation(
            "PR-13",
            False,
            "MCP_CSHARP_CANCELLATION_OR_URI_TEMPLATE_SPLIT_ERROR",
            cited,
            {},
        )
    if java_bare_cr_terminated_message:
        return GuardEvaluation(
            "PR-13",
            False,
            "MCP_JAVA_BARE_CR_PREMATURE_MESSAGE_TERMINATION",
            cited,
            {},
        )
    if not kotlin_sse_endpoint_resolved_per_rfc3986 or not kotlin_stdio_kept_running_on_handler_cancel:
        return GuardEvaluation(
            "PR-13",
            False,
            "MCP_KOTLIN_SSE_RFC3986_OR_STDIO_CANCEL_CRASH",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-13",
        True,
        "MCP_CSHARP_JAVA_KOTLIN_GUARDS_VERIFIED",
        cited,
        {"id_jag_audience": id_jag_audience},
    )


def evaluate_mcp_swift_pkce_modulo_and_stateless_id_collision_guard(
    *,
    pkce_random_byte: int,
    pkce_byte_accepted: bool,
    oauth_issuer_validated: bool,
    omitted_refresh_token_retained: bool,
    client_secret_basic_percent_encoded: bool,
    base64_detected_from_data_url_header_only: bool,
    in_flight_request_ids: set[str],
    incoming_request_id: str,
    stateless_collision_rejected: bool,
    resource_templates_excluded_from_resources_list: bool,
) -> GuardEvaluation:
    """PR-14: modelcontextprotocol/swift-sdk (#313, #309, #303, #300, #295, #293, #278, #269, #268, #267)."""
    cited = STAGE280_PR_GROUPS["PR-14"]
    # 66-character unreserved PKCE alphabet: 256 - (256 % 66) = 198 (or 64*3=192 / 66*3=198; >= 198 causes modulo bias)
    if pkce_random_byte >= 198 and pkce_byte_accepted:
        return GuardEvaluation(
            "PR-14",
            False,
            "MCP_SWIFT_PKCE_MODULO_BIAS_BYTE_ACCEPTED",
            cited,
            {"pkce_random_byte": pkce_random_byte},
        )
    if incoming_request_id in in_flight_request_ids and not stateless_collision_rejected:
        return GuardEvaluation(
            "PR-14",
            False,
            "MCP_SWIFT_STATELESS_HTTP_IN_FLIGHT_ID_COLLISION",
            cited,
            {"incoming_request_id": incoming_request_id},
        )
    if (
        not oauth_issuer_validated
        or not omitted_refresh_token_retained
        or not client_secret_basic_percent_encoded
        or not base64_detected_from_data_url_header_only
        or not resource_templates_excluded_from_resources_list
    ):
        return GuardEvaluation(
            "PR-14",
            False,
            "MCP_SWIFT_OAUTH_OR_DATA_URL_OR_TEMPLATE_LIST_VIOLATION",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-14",
        True,
        "MCP_SWIFT_PKCE_AND_STATELESS_ID_VERIFIED",
        cited,
        {"incoming_request_id": incoming_request_id},
    )


def evaluate_mcp_ruby_php_auth_redaction_and_elicitation_isolation_guard(
    *,
    ruby_retained_error_text: str,
    ruby_non_jsonrpc2_rejected: bool,
    ruby_non_utf8_json_key_code: int,
    ruby_undeclared_capability_code: int,
    php_host_and_origin_validated_independently: bool,
    php_parallel_elicitation_answers_isolated: bool,
    php_queued_notifications_bundled_in_request_json: bool,
    php_unreachable_session_store_http_status: int,
) -> GuardEvaluation:
    """PR-15: modelcontextprotocol/ruby-sdk (#624, #615, #604, #591, #590) & php-sdk (#602, #589, #588, #581, #572, #570)."""
    cited = STAGE280_PR_GROUPS["PR-15"]
    if "Bearer " in ruby_retained_error_text or not ruby_non_jsonrpc2_rejected:
        return GuardEvaluation(
            "PR-15",
            False,
            "MCP_RUBY_AUTH_HEADER_LEAK_OR_NON_JSONRPC2_ACCEPTED",
            cited,
            {},
        )
    if ruby_non_utf8_json_key_code != -32700 or ruby_undeclared_capability_code != -32601:
        return GuardEvaluation(
            "PR-15",
            False,
            "MCP_RUBY_NON_UTF8_KEY_OR_UNDECLARED_CAPABILITY_CODE_MISMATCH",
            cited,
            {"non_utf8_code": ruby_non_utf8_json_key_code, "undeclared_code": ruby_undeclared_capability_code},
        )
    if (
        not php_host_and_origin_validated_independently
        or not php_parallel_elicitation_answers_isolated
        or php_queued_notifications_bundled_in_request_json
        or php_unreachable_session_store_http_status != 503
    ):
        return GuardEvaluation(
            "PR-15",
            False,
            "MCP_PHP_ELICITATION_CROSSTALK_OR_SESSION_STORE_STATUS_ERROR",
            cited,
            {"php_unreachable_session_store_http_status": php_unreachable_session_store_http_status},
        )
    return GuardEvaluation(
        "PR-15",
        True,
        "MCP_RUBY_PHP_GUARDS_VERIFIED",
        cited,
        {"php_unreachable_session_store_http_status": php_unreachable_session_store_http_status},
    )


def evaluate_mcp_conformance_sep2243_dpop_and_inspector_scripts_guard(
    *,
    sep2243_header_mismatch_error_code: int,
    sep2164_resource_not_found_error_code: int,
    reject_all_server_scored_green: bool,
    sep1932_dpop_jkt_bound: bool,
    sep1932_bearer_downgrade_rejected: bool,
    inspector_npm_allow_scripts_stripped: bool,
    inspector_directory_read_has_ttl_and_cache_scope: bool,
    registry_backup_verifiable: bool,
) -> GuardEvaluation:
    """PR-16: modelcontextprotocol/conformance (#555, #554, #537, #528..#523), inspector (#2747, #2714, #2713), registry (#1726)."""
    cited = STAGE280_PR_GROUPS["PR-16"]
    if sep2243_header_mismatch_error_code != -32020 or sep2164_resource_not_found_error_code != -32002:
        return GuardEvaluation(
            "PR-16",
            False,
            "MCP_CONFORMANCE_SEP2243_OR_SEP2164_ERROR_CODE_VIOLATION",
            cited,
            {
                "sep2243_code": sep2243_header_mismatch_error_code,
                "sep2164_code": sep2164_resource_not_found_error_code,
            },
        )
    if reject_all_server_scored_green or not sep1932_dpop_jkt_bound or not sep1932_bearer_downgrade_rejected:
        return GuardEvaluation(
            "PR-16",
            False,
            "MCP_CONFORMANCE_DPOP_DOWNGRADE_OR_FALSE_GREEN_SCORE",
            cited,
            {},
        )
    if (
        not inspector_npm_allow_scripts_stripped
        or not inspector_directory_read_has_ttl_and_cache_scope
        or not registry_backup_verifiable
    ):
        return GuardEvaluation(
            "PR-16",
            False,
            "MCP_INSPECTOR_INSTALL_SCRIPT_OR_DIRECTORY_CACHE_VIOLATION",
            cited,
            {},
        )
    return GuardEvaluation(
        "PR-16",
        True,
        "MCP_CONFORMANCE_DPOP_AND_INSPECTOR_VERIFIED",
        cited,
        {"sep2243_code": sep2243_header_mismatch_error_code},
    )
