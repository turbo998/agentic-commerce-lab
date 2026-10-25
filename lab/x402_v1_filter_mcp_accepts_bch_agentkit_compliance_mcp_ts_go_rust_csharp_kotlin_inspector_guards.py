"""Stage 238 deterministic protocol & security guards (`PR-01..PR-16`).

Covers 48 primary-source issues and pull requests across:
- `x402-foundation/x402` (`#3930`, `#3929`, `#3928`, `#3924`, `#3917`, `#3908`, `#3793`, `#3611`, `#3592`)
- `coinbase/agentkit` (`#1585`, `#1579`, `#1577`, `#1575`, `#1564`, `#1563`)
- `modelcontextprotocol/typescript-sdk` (`#3049`, `#3046`, `#3042`, `#3040`, `#3039`, `#3038`, `#3035`, `#3030`)
- `modelcontextprotocol/go-sdk` (`#1437`, `#1434`, `#1420`, `#1410`, `#1408`, `#1407`, `#1405`, `#1403`, `#1401`, `#1400`, `#1399`, `#1398`, `#1397`, `#1396`, `#1388`)
- `modelcontextprotocol/rust-sdk` (`#1378`, `#1372`, `#1370`, `#1358`, `#1352`, `#1349`, `#1346`, `#1344`, `#1343`, `#1341`, `#1340`)
- `modelcontextprotocol/csharp-sdk` (`#1948`, `#1891`, `#1890`)
- `modelcontextprotocol/kotlin-sdk` (`#1132`, `#1103`, `#1102`, `#1100`)
- `modelcontextprotocol/inspector` (`#2806`, `#2789`, `#2786`, `#2735`, `#2733`, `#2732`, `#2731`, `#2714`, `#2713`)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote, urlparse


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    action: str
    details: dict[str, Any]


CAIP2_TO_V1_NETWORK: dict[str, str] = {
    "eip155:8453": "base",
    "eip155:84532": "base-sepolia",
    "eip155:137": "polygon",
    "eip155:80002": "polygon-amoy",
    "eip155:43114": "avalanche",
    "eip155:43113": "avalanche-fuji",
    "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp": "solana",
    "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1": "solana-devnet",
}
V1_TO_CAIP2_NETWORK: dict[str, str] = {v: k for k, v in CAIP2_TO_V1_NETWORK.items()}
MAINNET_V1_NETWORKS = {"base", "polygon", "avalanche", "sei", "solana"}


# PR-01: x402-foundation/x402#3930 & #3928
def evaluate_x402_v1_network_filter_and_facilitator_supported_guard(
    *,
    configured_networks: Sequence[str],
    offer_x402_version: int,
    offer_network: str,
    facilitator_supported_kinds: Sequence[Mapping[str, Any]],
    facilitator_supports_v1_requirements_model: bool,
) -> GuardEvaluation:
    allowed_caip2: set[str] = set()
    allowed_v1: set[str] = set()
    for net in configured_networks:
        if ":" in net:
            allowed_caip2.add(net)
            if net in CAIP2_TO_V1_NETWORK:
                allowed_v1.add(CAIP2_TO_V1_NETWORK[net])
        else:
            allowed_v1.add(net)
            if net in V1_TO_CAIP2_NETWORK:
                allowed_caip2.add(V1_TO_CAIP2_NETWORK[net])

    if offer_x402_version == 1:
        if offer_network not in allowed_v1:
            is_mainnet_downgrade = offer_network in MAINNET_V1_NETWORKS
            code = (
                "X402_V1_MAINNET_DOWNGRADE_ON_TESTNET_CLIENT_BLOCKED"
                if is_mainnet_downgrade
                else "X402_V1_UNREGISTERED_NETWORK_BLOCKED"
            )
            return GuardEvaluation(
                passed=False,
                decision_code=code,
                action="Send to a human",
                details={
                    "configured_networks": list(configured_networks),
                    "allowed_v1_networks": sorted(allowed_v1),
                    "offer_network": offer_network,
                },
            )
    elif offer_x402_version == 2:
        if offer_network not in allowed_caip2:
            return GuardEvaluation(
                passed=False,
                decision_code="X402_V2_UNREGISTERED_NETWORK_BLOCKED",
                action="Send to a human",
                details={
                    "configured_networks": list(configured_networks),
                    "allowed_caip2_networks": sorted(allowed_caip2),
                    "offer_network": offer_network,
                },
            )
    else:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_UNSUPPORTED_VERSION_BLOCKED",
            action="Send to a human",
            details={"offer_x402_version": offer_x402_version},
        )

    for kind in facilitator_supported_kinds:
        k_ver = kind.get("x402Version")
        k_net = str(kind.get("network", ""))
        if k_ver == 1:
            if not facilitator_supports_v1_requirements_model:
                return GuardEvaluation(
                    passed=False,
                    decision_code="X402_FACILITATOR_ADVERTISES_UNSUPPORTED_V1_KIND_BLOCKED",
                    action="Send to a human",
                    details={"advertised_kind": dict(kind)},
                )
            if k_net not in allowed_v1:
                return GuardEvaluation(
                    passed=False,
                    decision_code="X402_FACILITATOR_UNFILTERED_V1_SUPPORTED_KIND_BLOCKED",
                    action="Send to a human",
                    details={"advertised_kind": dict(kind), "allowed_v1": sorted(allowed_v1)},
                )
        elif k_ver == 2 and k_net not in allowed_caip2:
            return GuardEvaluation(
                passed=False,
                decision_code="X402_FACILITATOR_UNFILTERED_V2_SUPPORTED_KIND_BLOCKED",
                action="Send to a human",
                details={"advertised_kind": dict(kind), "allowed_caip2": sorted(allowed_caip2)},
            )

    return GuardEvaluation(
        passed=True,
        decision_code="X402_V1_NETWORK_FILTER_AND_SUPPORTED_VERIFIED",
        action="Act automatically",
        details={
            "allowed_caip2_networks": sorted(allowed_caip2),
            "allowed_v1_networks": sorted(allowed_v1),
            "supported_kinds_count": len(facilitator_supported_kinds),
        },
    )


# PR-02: x402-foundation/x402#3917 (#3908) & #3929
def evaluate_x402_non_object_header_and_facilitator_payload_guard(
    *,
    decoded_header_json: Any,
    payment_payload_inner: Any,
    requirement_network: str,
    registered_facilitator_networks: Sequence[str],
    facilitator_http_status_on_invalid: int,
) -> GuardEvaluation:
    if not isinstance(decoded_header_json, Mapping):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_NON_OBJECT_PAYMENT_HEADER_JSON_REJECTED",
            action="Send to a human",
            details={"decoded_type": type(decoded_header_json).__name__},
        )
    if not isinstance(payment_payload_inner, Mapping):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_NON_OBJECT_PAYMENT_PAYLOAD_INNER_REJECTED",
            action="Send to a human",
            details={"inner_type": type(payment_payload_inner).__name__},
        )
    if facilitator_http_status_on_invalid >= 500:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_FACILITATOR_UNHANDLED_HTTP_500_ON_INVALID_PAYLOAD_BLOCKED",
            action="Send to a human",
            details={"facilitator_http_status_on_invalid": facilitator_http_status_on_invalid},
        )
    if requirement_network not in set(registered_facilitator_networks):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_FACILITATOR_UNREGISTERED_NETWORK_STRUCTURED_REFUSAL",
            action="Send to a human",
            details={
                "requirement_network": requirement_network,
                "registered_networks": list(registered_facilitator_networks),
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_OBJECT_HEADER_AND_FACILITATOR_PAYLOAD_VERIFIED",
        action="Act automatically",
        details={"requirement_network": requirement_network},
    )


# PR-03: x402-foundation/x402#3924 & #3793
def evaluate_x402_mcp_multi_network_matching_and_test_gate_guard(
    *,
    accepts: Sequence[Mapping[str, Any]],
    payment_payload: Mapping[str, Any],
    wrapper_uses_hardcoded_accepts_zero: bool,
    pytest_testpaths: Sequence[str],
    sync_client_methods: Sequence[str],
) -> GuardEvaluation:
    if wrapper_uses_hardcoded_accepts_zero and len(accepts) > 1:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_MCP_WRAPPER_HARDCODED_ACCEPTS_ZERO_BLOCKED",
            action="Send to a human",
            details={"accepts_count": len(accepts)},
        )
    accepted_req = payment_payload.get("accepted")
    payload_net = (
        accepted_req.get("network")
        if isinstance(accepted_req, Mapping)
        else payment_payload.get("network")
    )
    payload_scheme = (
        accepted_req.get("scheme")
        if isinstance(accepted_req, Mapping)
        else payment_payload.get("scheme")
    )
    matched: Mapping[str, Any] | None = None
    for req in accepts:
        if req.get("network") == payload_net and req.get("scheme") == payload_scheme:
            matched = req
            break
    if matched is None:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_MCP_NO_MATCHING_PAYMENT_REQUIREMENT_BLOCKED",
            action="Send to a human",
            details={"payload_network": payload_net, "payload_scheme": payload_scheme},
        )
    if "mcp/tests" not in set(pytest_testpaths):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_PYTHON_MCP_TESTS_OMITTED_FROM_CI_TESTPATHS_BLOCKED",
            action="Send to a human",
            details={"pytest_testpaths": list(pytest_testpaths)},
        )
    required_sync_methods = {"on_before_payment", "call_tool_with_payment"}
    missing_methods = sorted(required_sync_methods - set(sync_client_methods))
    if missing_methods:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_MCP_SYNC_CLIENT_METHOD_PARITY_MISSING_BLOCKED",
            action="Send to a human",
            details={"missing_methods": missing_methods},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_MCP_MULTI_NETWORK_MATCHING_AND_TEST_GATE_VERIFIED",
        action="Act automatically",
        details={
            "matched_network": matched.get("network"),
            "matched_asset": matched.get("asset"),
            "matched_pay_to": matched.get("payTo"),
        },
    )


# PR-04: x402-foundation/x402#3611 & #3592
def evaluate_x402_bch_exact_and_php_v2_sdk_guard(
    *,
    bch_network: str,
    sighash_type: int,
    cashaddr_p2pkh_matches_pay_to: bool,
    utxo_outpoint_unspent: bool,
    fulcrum_quorum_verified: bool,
    settlement_claim_already_locked: bool,
    php_sdk_targets_v2_only: bool,
    php_sdk_commits_vendor_dir: bool,
) -> GuardEvaluation:
    if bch_network not in {"bch:mainnet", "bch:chipnet", "bip122:000000000000000000651ef99cb9fcbe"}:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BCH_UNSUPPORTED_NETWORK_BLOCKED",
            action="Send to a human",
            details={"bch_network": bch_network},
        )
    # BCH BIP-143 requires SIGHASH_ALL | SIGHASH_FORKID = 0x41 (65)
    if sighash_type != 0x41:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BCH_MISSING_SIGHASH_FORKID_BLOCKED",
            action="Send to a human",
            details={"sighash_type": hex(sighash_type), "expected": "0x41"},
        )
    if not cashaddr_p2pkh_matches_pay_to or not utxo_outpoint_unspent or not fulcrum_quorum_verified:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BCH_UTXO_OR_CASHADDR_VERIFICATION_FAILED",
            action="Send to a human",
            details={
                "cashaddr_p2pkh_matches_pay_to": cashaddr_p2pkh_matches_pay_to,
                "utxo_outpoint_unspent": utxo_outpoint_unspent,
                "fulcrum_quorum_verified": fulcrum_quorum_verified,
            },
        )
    if settlement_claim_already_locked:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BCH_DUPLICATE_SETTLEMENT_CLAIM_BLOCKED",
            action="Send to a human",
            details={"settlement_claim_already_locked": True},
        )
    if not php_sdk_targets_v2_only or php_sdk_commits_vendor_dir:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_PHP_SDK_V1_LEGACY_OR_VENDOR_TREE_BLOCKED",
            action="Send to a human",
            details={
                "php_sdk_targets_v2_only": php_sdk_targets_v2_only,
                "php_sdk_commits_vendor_dir": php_sdk_commits_vendor_dir,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_BCH_EXACT_AND_PHP_V2_SDK_VERIFIED",
        action="Act automatically",
        details={"bch_network": bch_network, "sighash_type": "0x41"},
    )


# PR-05: coinbase/agentkit#1585 & #1564
def evaluate_agentkit_stablecoin_compliance_and_mizan_zk_guard(
    *,
    ofac_address_sanctioned: bool,
    counterparty_sanctions_hits: Sequence[str],
    mizan_credential_status: str,
    require_proven_counterparty: bool,
) -> GuardEvaluation:
    if ofac_address_sanctioned or len(counterparty_sanctions_hits) > 0:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_STABLECOIN_GATEWAYS_SANCTIONS_HIT_BLOCKED",
            action="Send to a human",
            details={
                "ofac_address_sanctioned": ofac_address_sanctioned,
                "counterparty_sanctions_hits": list(counterparty_sanctions_hits),
            },
        )
    valid_statuses = {"PROVEN", "REFUSED", "NOT_SIGNIFICANT", "UNVERIFIED"}
    if mizan_credential_status not in valid_statuses:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_MIZAN_UNKNOWN_STATUS_BLOCKED",
            action="Send to a human",
            details={"mizan_credential_status": mizan_credential_status},
        )
    if mizan_credential_status == "REFUSED" or (
        require_proven_counterparty and mizan_credential_status != "PROVEN"
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_MIZAN_COUNTERPARTY_NOT_PROVEN_BLOCKED",
            action="Send to a human",
            details={
                "mizan_credential_status": mizan_credential_status,
                "require_proven_counterparty": require_proven_counterparty,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="AGENTKIT_COMPLIANCE_AND_MIZAN_ZK_PROVEN_VERIFIED",
        action="Act automatically",
        details={"mizan_credential_status": mizan_credential_status},
    )


# PR-06: coinbase/agentkit#1577, #1579, #1575, & #1563
def evaluate_agentkit_x402_hook_base_units_and_erc4337_receipt_guard(
    *,
    before_payment_hook_approved: bool,
    human_amount_str: str,
    token_symbol: str,
    token_decimals: int,
    submitted_base_units: int,
    moonwell_resolved_from_network_object: bool,
    erc4337_bundle_tx_mined: bool,
    erc4337_user_op_receipt_success: bool,
) -> GuardEvaluation:
    if not before_payment_hook_approved:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_X402_BEFORE_PAYMENT_HOOK_ABORTED",
            action="Send to a human",
            details={"before_payment_hook_approved": False},
        )
    if not moonwell_resolved_from_network_object or (
        token_symbol.lower() == "cbbtc" and token_decimals != 8
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_MOONWELL_TOKEN_DECIMALS_MISMATCH_BLOCKED",
            action="Send to a human",
            details={
                "token_symbol": token_symbol,
                "token_decimals": token_decimals,
                "moonwell_resolved_from_network_object": moonwell_resolved_from_network_object,
            },
        )
    exact_base_units = int(
        (Decimal(human_amount_str) * (Decimal(10) ** token_decimals)).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )
    if submitted_base_units != exact_base_units:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_SVM_FLOAT_BASE_UNIT_DRIFT_BLOCKED",
            action="Send to a human",
            details={
                "human_amount": human_amount_str,
                "expected_base_units": exact_base_units,
                "submitted_base_units": submitted_base_units,
            },
        )
    if not erc4337_bundle_tx_mined or not erc4337_user_op_receipt_success:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_ERC4337_REVERTED_USEROP_IN_MINED_BUNDLE_BLOCKED",
            action="Send to a human",
            details={
                "erc4337_bundle_tx_mined": erc4337_bundle_tx_mined,
                "erc4337_user_op_receipt_success": erc4337_user_op_receipt_success,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="AGENTKIT_HOOK_BASE_UNITS_AND_ERC4337_RECEIPT_VERIFIED",
        action="Act automatically",
        details={"exact_base_units": exact_base_units, "token_decimals": token_decimals},
    )


# PR-07: modelcontextprotocol/typescript-sdk#3049, #3046, & #3030
def evaluate_mcp_ts_sampling_history_abort_and_tool_snapshot_guard(
    *,
    sampling_messages: Sequence[Mapping[str, Any]],
    TerminationReason: str,
    error_code_emitted: str,
    mirror_schema_revision: int,
    validation_schema_revision: int,
) -> GuardEvaluation:
    pending_tool_uses: set[str] = set()
    for msg in sampling_messages:
        role = msg.get("role")
        content = msg.get("content", [])
        blocks = content if isinstance(content, list) else [content]
        if role == "assistant":
            if pending_tool_uses:
                return GuardEvaluation(
                    passed=False,
                    decision_code="MCP_TS_SAMPLING_UNBALANCED_TOOL_USE_HISTORY_BLOCKED",
                    action="Send to a human",
                    details={"unmatched_tool_use_ids": sorted(pending_tool_uses)},
                )
            for b in blocks:
                if isinstance(b, Mapping) and b.get("type") == "tool_use":
                    pending_tool_uses.add(str(b.get("id", "")))
        elif role == "user":
            for b in blocks:
                if isinstance(b, Mapping) and b.get("type") == "tool_result":
                    tid = str(b.get("toolUseId") or b.get("tool_use_id") or "")
                    pending_tool_uses.discard(tid)
    if pending_tool_uses:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_SAMPLING_UNBALANCED_TOOL_USE_HISTORY_BLOCKED",
            action="Send to a human",
            details={"unmatched_tool_use_ids": sorted(pending_tool_uses)},
        )
    if TerminationReason == "abort_signal" and error_code_emitted == "RequestTimeout":
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_ABORT_SIGNAL_CONFLATED_WITH_TIMEOUT_BLOCKED",
            action="Send to a human",
            details={"TerminationReason": TerminationReason, "error_code_emitted": error_code_emitted},
        )
    if mirror_schema_revision != validation_schema_revision:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_TOOL_DEFINITION_TORN_SNAPSHOT_BLOCKED",
            action="Send to a human",
            details={
                "mirror_schema_revision": mirror_schema_revision,
                "validation_schema_revision": validation_schema_revision,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_TS_SAMPLING_ABORT_AND_TOOL_SNAPSHOT_VERIFIED",
        action="Act automatically",
        details={"schema_revision": mirror_schema_revision},
    )


# PR-08: modelcontextprotocol/typescript-sdk#3042, #3040, #3039, #3038, & #3035
def evaluate_mcp_ts_auth_encoding_null_proto_and_local_ref_guard(
    *,
    requested_resource_url: str,
    configured_resource_url: str,
    client_id: str,
    client_secret: str,
    encoded_basic_decoded_payload: str,
    registry_uses_null_prototype: bool,
    tool_name: str,
    output_schema_uses_local_ref: bool,
    local_ref_target_type: str,
    classified_as_object_schema: bool,
) -> GuardEvaluation:
    req_norm = requested_resource_url.rstrip("/")
    cfg_norm = configured_resource_url.rstrip("/")
    if req_norm != cfg_norm and not req_norm.startswith(cfg_norm + "/"):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_PROTECTED_RESOURCE_MISMATCH_BLOCKED",
            action="Send to a human",
            details={
                "requested_resource_url": requested_resource_url,
                "configured_resource_url": configured_resource_url,
            },
        )
    expected_basic_pair = f"{quote(client_id, safe='')}:{quote(client_secret, safe='')}"
    if encoded_basic_decoded_payload != expected_basic_pair:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_CLIENT_SECRET_BASIC_UNENCODED_CREDENTIALS_BLOCKED",
            action="Send to a human",
            details={
                "expected_basic_pair": expected_basic_pair,
                "actual_basic_pair": encoded_basic_decoded_payload,
            },
        )
    object_proto_names = {"constructor", "toString", "valueOf", "__proto__", "hasOwnProperty"}
    if not registry_uses_null_prototype and tool_name in object_proto_names:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_OBJECT_PROTOTYPE_REGISTRY_COLLISION_BLOCKED",
            action="Send to a human",
            details={"tool_name": tool_name},
        )
    if output_schema_uses_local_ref and local_ref_target_type == "object" and not classified_as_object_schema:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_LOCAL_REF_OBJECT_OUTPUT_SCHEMA_MISCLASSIFIED_BLOCKED",
            action="Send to a human",
            details={"local_ref_target_type": local_ref_target_type},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_TS_AUTH_ENCODING_NULL_PROTO_AND_LOCAL_REF_VERIFIED",
        action="Act automatically",
        details={"normalized_resource": req_norm, "tool_name": tool_name},
    )


# PR-09: modelcontextprotocol/go-sdk#1437, #1396, & #1388
def evaluate_mcp_go_redirect_origin_bearer_metadata_and_aud_guard(
    *,
    endpoint_url: str,
    redirect_target_url: str | None,
    challenges: Sequence[Mapping[str, str]],
    selected_resource_metadata_scheme: str,
    token_aud: str,
    expected_resource_aud: str,
    token_info_user_id: str,
) -> GuardEvaluation:
    if redirect_target_url is not None:
        ep = urlparse(endpoint_url)
        rt = urlparse(redirect_target_url)
        if (ep.scheme.lower(), ep.netloc.lower()) != (rt.scheme.lower(), rt.netloc.lower()):
            return GuardEvaluation(
                passed=False,
                decision_code="MCP_GO_CROSS_ORIGIN_TRANSPORT_REDIRECT_BLOCKED",
                action="Send to a human",
                details={"endpoint_url": endpoint_url, "redirect_target_url": redirect_target_url},
            )
    if selected_resource_metadata_scheme.lower() != "bearer":
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_NON_BEARER_RESOURCE_METADATA_CHALLENGE_BLOCKED",
            action="Send to a human",
            details={
                "selected_scheme": selected_resource_metadata_scheme,
                "challenges_count": len(challenges),
            },
        )
    if token_aud != expected_resource_aud or not token_info_user_id.strip():
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_TOKEN_AUDIENCE_OR_USER_ID_BINDING_MISSING_BLOCKED",
            action="Send to a human",
            details={
                "token_aud": token_aud,
                "expected_resource_aud": expected_resource_aud,
                "token_info_user_id": token_info_user_id,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_REDIRECT_ORIGIN_BEARER_METADATA_AND_AUD_VERIFIED",
        action="Act automatically",
        details={"endpoint_origin": urlparse(endpoint_url).netloc, "user_id": token_info_user_id},
    )


# PR-10: modelcontextprotocol/go-sdk#1434, #1420, #1410, #1408, & #1403
def evaluate_mcp_go_logging_session_header_schema_and_sse_context_guard(
    *,
    logging_transport_forwards_session_state: bool,
    sse_stream_detached_from_connect_ctx: bool,
    schema_has_type_array_or_bool_subschema: bool,
    x_mcp_headers_extracted: bool,
    sampling_tool_result_preserves_empty_text: bool,
) -> GuardEvaluation:
    if not logging_transport_forwards_session_state:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_LOGGING_TRANSPORT_DROPPED_SESSION_STATE_BLOCKED",
            action="Send to a human",
            details={"logging_transport_forwards_session_state": False},
        )
    if not sse_stream_detached_from_connect_ctx:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_SSE_STREAM_BOUND_TO_CONNECT_TIMEOUT_BLOCKED",
            action="Send to a human",
            details={"sse_stream_detached_from_connect_ctx": False},
        )
    if schema_has_type_array_or_bool_subschema and not x_mcp_headers_extracted:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_TYPE_ARRAY_OR_BOOL_HID_X_MCP_HEADER_BLOCKED",
            action="Send to a human",
            details={"schema_has_type_array_or_bool_subschema": True, "x_mcp_headers_extracted": False},
        )
    if not sampling_tool_result_preserves_empty_text:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_SAMPLING_TOOL_RESULT_OMITTED_EMPTY_CONTENT_BLOCKED",
            action="Send to a human",
            details={"sampling_tool_result_preserves_empty_text": False},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_LOGGING_SESSION_HEADER_SCHEMA_AND_SSE_VERIFIED",
        action="Act automatically",
        details={"x_mcp_headers_extracted": x_mcp_headers_extracted},
    )


# PR-11: modelcontextprotocol/go-sdk#1407, #1405, #1401, #1400, #1399, #1398, & #1397
def evaluate_mcp_go_jsonrpc_id_precision_and_error_response_guard(
    *,
    raw_request_id_literal: str,
    decoded_request_id: int | str | None,
    handler_uncoded_error_rpc_code: int,
    marshal_failure_sent_error_response: bool,
    rejected_id_returned_null_id_jsonrpc_error: bool,
    null_input_request_rejected: bool,
    is_error_result_has_structured_content: bool,
) -> GuardEvaluation:
    # Check exact integer ID decoding for >2^53 or integral decimal/exponent forms
    if re.fullmatch(r"\d+(\.0+)?([eE][+-]?\d+)?", raw_request_id_literal):
        exact_dec = Decimal(raw_request_id_literal)
        if exact_dec == exact_dec.to_integral_value():
            expected_int = int(exact_dec)
            if decoded_request_id != expected_int:
                return GuardEvaluation(
                    passed=False,
                    decision_code="MCP_GO_JSONRPC_REQUEST_ID_FLOAT64_PRECISION_LOSS_BLOCKED",
                    action="Send to a human",
                    details={
                        "raw_request_id_literal": raw_request_id_literal,
                        "expected_int": expected_int,
                        "decoded_request_id": decoded_request_id,
                    },
                )
    if handler_uncoded_error_rpc_code != -32603:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_UNCODED_HANDLER_ERROR_ZERO_CODE_BLOCKED",
            action="Send to a human",
            details={"handler_uncoded_error_rpc_code": handler_uncoded_error_rpc_code},
        )
    if (
        not marshal_failure_sent_error_response
        or not rejected_id_returned_null_id_jsonrpc_error
        or not null_input_request_rejected
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_MARSHAL_OR_INVALID_ID_ERROR_RESPONSE_MISSING_BLOCKED",
            action="Send to a human",
            details={
                "marshal_failure_sent_error_response": marshal_failure_sent_error_response,
                "rejected_id_returned_null_id_jsonrpc_error": rejected_id_returned_null_id_jsonrpc_error,
                "null_input_request_rejected": null_input_request_rejected,
            },
        )
    if is_error_result_has_structured_content:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_ERROR_RESULT_LEAKED_STRUCTURED_CONTENT_BLOCKED",
            action="Send to a human",
            details={"is_error_result_has_structured_content": True},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_JSONRPC_ID_PRECISION_AND_ERROR_RESPONSE_VERIFIED",
        action="Act automatically",
        details={"decoded_request_id": decoded_request_id, "rpc_error_code": handler_uncoded_error_rpc_code},
    )


# PR-12: modelcontextprotocol/rust-sdk#1372, #1358, #1352, & #1341
def evaluate_mcp_rust_www_authenticate_dcr_scope_and_4xx_guard(
    *,
    www_authenticate_challenges_parsed_separately: bool,
    selected_bearer_scope: str,
    dpop_challenge_scope: str,
    dcr_selected_auth_method: str,
    dcr_supported_auth_methods: Sequence[str],
    dcr_returned_client_secret: str,
    initial_login_requested_scopes: Sequence[str],
    challenge_requested_scopes: Sequence[str],
    http_401_403_with_jsonrpc_body_treated_as_auth_error: bool,
) -> GuardEvaluation:
    if not www_authenticate_challenges_parsed_separately or selected_bearer_scope == dpop_challenge_scope:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_WWW_AUTHENTICATE_CROSS_CHALLENGE_MIX_BLOCKED",
            action="Send to a human",
            details={
                "www_authenticate_challenges_parsed_separately": www_authenticate_challenges_parsed_separately,
                "selected_bearer_scope": selected_bearer_scope,
                "dpop_challenge_scope": dpop_challenge_scope,
            },
        )
    allowed_methods = set(dcr_supported_auth_methods) if dcr_supported_auth_methods else {"none"}
    if dcr_selected_auth_method not in allowed_methods:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_DCR_UNSUPPORTED_AUTH_METHOD_BLOCKED",
            action="Send to a human",
            details={
                "dcr_selected_auth_method": dcr_selected_auth_method,
                "allowed_methods": sorted(allowed_methods),
            },
        )
    if dcr_selected_auth_method in {"client_secret_basic", "client_secret_post"} and not dcr_returned_client_secret.strip():
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_DCR_CONFIDENTIAL_CLIENT_EMPTY_SECRET_BLOCKED",
            action="Send to a human",
            details={"dcr_selected_auth_method": dcr_selected_auth_method},
        )
    if challenge_requested_scopes and list(initial_login_requested_scopes) != list(challenge_requested_scopes):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_INITIAL_AUTH_OVERBROAD_SCOPE_ESCALATION_BLOCKED",
            action="Send to a human",
            details={
                "challenge_requested_scopes": list(challenge_requested_scopes),
                "initial_login_requested_scopes": list(initial_login_requested_scopes),
            },
        )
    if not http_401_403_with_jsonrpc_body_treated_as_auth_error:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_HTTP_4XX_MASKED_BY_JSONRPC_BODY_BLOCKED",
            action="Send to a human",
            details={"http_401_403_with_jsonrpc_body_treated_as_auth_error": False},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_RUST_WWW_AUTHENTICATE_DCR_SCOPE_AND_4XX_VERIFIED",
        action="Act automatically",
        details={
            "selected_bearer_scope": selected_bearer_scope,
            "dcr_selected_auth_method": dcr_selected_auth_method,
        },
    )


# PR-13: modelcontextprotocol/rust-sdk#1378, #1370, #1349, #1346, #1344, #1343, & #1340
def evaluate_mcp_rust_per_request_schema_host_and_cancel_guard(
    *,
    per_request_tool_schema_lookup: bool,
    host_header_checked_before_auth_middleware: bool,
    output_schema_generated_for_serialize: bool,
    peer_protocol_version: str,
    structured_content_type: str,
    non_object_structured_content_omitted: bool,
    invalid_request_reply_preserved_on_cancel: bool,
    abandoned_request_sent_cancelled_notification: bool,
) -> GuardEvaluation:
    if not per_request_tool_schema_lookup:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_STALE_CACHED_TOOL_SCHEMA_FOR_HEADERS_BLOCKED",
            action="Send to a human",
            details={"per_request_tool_schema_lookup": False},
        )
    if not host_header_checked_before_auth_middleware or not output_schema_generated_for_serialize:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_HOST_CHECK_OR_SERIALIZE_SCHEMA_CONTRACT_BLOCKED",
            action="Send to a human",
            details={
                "host_header_checked_before_auth_middleware": host_header_checked_before_auth_middleware,
                "output_schema_generated_for_serialize": output_schema_generated_for_serialize,
            },
        )
    if (
        peer_protocol_version in {"2025-06-18", "2025-11-25"}
        and structured_content_type != "object"
        and not non_object_structured_content_omitted
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_NON_OBJECT_STRUCTURED_OUTPUT_SENT_TO_LEGACY_PEER_BLOCKED",
            action="Send to a human",
            details={
                "peer_protocol_version": peer_protocol_version,
                "structured_content_type": structured_content_type,
            },
        )
    if not invalid_request_reply_preserved_on_cancel or not abandoned_request_sent_cancelled_notification:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_CANCEL_REPLY_OR_ABANDONED_NOTIFICATION_DROPPED_BLOCKED",
            action="Send to a human",
            details={
                "invalid_request_reply_preserved_on_cancel": invalid_request_reply_preserved_on_cancel,
                "abandoned_request_sent_cancelled_notification": abandoned_request_sent_cancelled_notification,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_RUST_PER_REQUEST_SCHEMA_HOST_AND_CANCEL_VERIFIED",
        action="Act automatically",
        details={"peer_protocol_version": peer_protocol_version},
    )


# PR-14: modelcontextprotocol/csharp-sdk#1948, #1891, & #1890
def evaluate_mcp_csharp_oauth_state_cancellation_and_id_jag_guard(
    *,
    oauth_state_entropy_bits: int,
    oauth_state_matches_callback: bool,
    additional_params_overrides_state: bool,
    metadata_discovery_cancelled_rethrows_operation_canceled: bool,
    discovered_issuer: str,
    id_jag_token_exchange_audience: str,
) -> GuardEvaluation:
    if oauth_state_entropy_bits < 256 or not oauth_state_matches_callback or additional_params_overrides_state:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_OAUTH_STATE_CSRF_VALIDATION_FAILED",
            action="Send to a human",
            details={
                "oauth_state_entropy_bits": oauth_state_entropy_bits,
                "oauth_state_matches_callback": oauth_state_matches_callback,
                "additional_params_overrides_state": additional_params_overrides_state,
            },
        )
    if not metadata_discovery_cancelled_rethrows_operation_canceled:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_CANCELLATION_MASKED_AS_MISSING_METADATA_BLOCKED",
            action="Send to a human",
            details={"metadata_discovery_cancelled_rethrows_operation_canceled": False},
        )
    if id_jag_token_exchange_audience != discovered_issuer:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_ID_JAG_AUDIENCE_TRAILING_SLASH_MISMATCH_BLOCKED",
            action="Send to a human",
            details={
                "discovered_issuer": discovered_issuer,
                "id_jag_token_exchange_audience": id_jag_token_exchange_audience,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_CSHARP_OAUTH_STATE_CANCELLATION_AND_ID_JAG_VERIFIED",
        action="Act automatically",
        details={"discovered_issuer": discovered_issuer, "state_bits": oauth_state_entropy_bits},
    )


# PR-15: modelcontextprotocol/kotlin-sdk#1132, #1103, #1102, #1100 & inspector#2806, #2789, #2786, #2735, #2733, #2732, #2731, #2714, #2713
def evaluate_mcp_kotlin_init_buffer_rfc3986_and_inspector_security_guard(
    *,
    kotlin_buffers_messages_during_initializing: bool,
    kotlin_sse_endpoint_resolved_rfc3986: bool,
    kotlin_lazy_state_message_evaluated: bool,
    inspector_vite_dev_cors_restricted_to_allowed_origins: bool,
    inspector_bare_403_resolves_protocol_entry: bool,
    inspector_oauth_secret_carried_across_backends: bool,
    inspector_strips_npm_config_allow_scripts: bool,
    load_error_rate: float,
    load_max_error_rate: float,
    load_p99_ms: float,
    load_max_p99_ms: float,
) -> GuardEvaluation:
    if (
        not kotlin_buffers_messages_during_initializing
        or not kotlin_sse_endpoint_resolved_rfc3986
        or not kotlin_lazy_state_message_evaluated
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_KOTLIN_INIT_BUFFER_OR_RFC3986_SSE_ENDPOINT_BLOCKED",
            action="Send to a human",
            details={
                "kotlin_buffers_messages_during_initializing": kotlin_buffers_messages_during_initializing,
                "kotlin_sse_endpoint_resolved_rfc3986": kotlin_sse_endpoint_resolved_rfc3986,
                "kotlin_lazy_state_message_evaluated": kotlin_lazy_state_message_evaluated,
            },
        )
    if (
        not inspector_vite_dev_cors_restricted_to_allowed_origins
        or not inspector_bare_403_resolves_protocol_entry
        or not inspector_oauth_secret_carried_across_backends
        or not inspector_strips_npm_config_allow_scripts
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_CORS_OAUTH_OR_INSTALL_SCRIPT_POLICY_BLOCKED",
            action="Send to a human",
            details={
                "inspector_vite_dev_cors_restricted_to_allowed_origins": inspector_vite_dev_cors_restricted_to_allowed_origins,
                "inspector_bare_403_resolves_protocol_entry": inspector_bare_403_resolves_protocol_entry,
                "inspector_oauth_secret_carried_across_backends": inspector_oauth_secret_carried_across_backends,
                "inspector_strips_npm_config_allow_scripts": inspector_strips_npm_config_allow_scripts,
            },
        )
    if load_error_rate > load_max_error_rate or load_p99_ms > load_max_p99_ms:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_MCPDO_LOAD_THRESHOLD_EXCEEDED_BLOCKED",
            action="Send to a human",
            details={
                "load_error_rate": load_error_rate,
                "load_max_error_rate": load_max_error_rate,
                "load_p99_ms": load_p99_ms,
                "load_max_p99_ms": load_max_p99_ms,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_KOTLIN_AND_INSPECTOR_SECURITY_VERIFIED",
        action="Act automatically",
        details={"load_error_rate": load_error_rate, "load_p99_ms": load_p99_ms},
    )


# PR-16: Composite All-15 Gate
def evaluate_stage238_239_all_15_guards(
    evaluations: Sequence[GuardEvaluation],
) -> GuardEvaluation:
    failed = [ev for ev in evaluations if not ev.passed]
    if len(evaluations) != 15 or failed:
        return GuardEvaluation(
            passed=False,
            decision_code="STAGE238_239_COMPOSITE_GUARD_FAILED",
            action="Send to a human",
            details={
                "total_evaluated": len(evaluations),
                "failed_codes": [ev.decision_code for ev in failed],
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="STAGE238_239_ALL_15_GUARDS_VERIFIED",
        action="Act automatically",
        details={
            "total_evaluated": 15,
            "verified_codes": [ev.decision_code for ev in evaluations],
        },
    )
