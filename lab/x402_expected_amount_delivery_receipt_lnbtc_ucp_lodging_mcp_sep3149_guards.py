"""Stage 230 deterministic guard evaluators (PR-01..PR-16 · 230-Stage Milestone!).

Covers 37 primary-source PRs across x402 Foundation (`#3920`, `#3922`, `#3783`,
`#3688`, `#3207`, `#715`), Universal Commerce Protocol (`#861`, `#801`, `#691`,
`#848`, `#988`, `js-sdk#89`), Model Context Protocol SEPs (`#3149`, `#2633`),
MCP Java/Kotlin/Swift/Ruby/PHP SDKs (`java-sdk#1271`/`#1202`/`#1159`/`#1160`,
`kotlin-sdk#1134`/`#1101`/`#1130`, `swift-sdk#311`/`#310`/`#309`,
`ruby-sdk#632`/`#631`, `php-sdk#614`/`#432`), MCP Apps (`ext-apps#798`/`#824`/
`#821`), MCP Conformance (`#529`/`#564`/`#521`/`#541`), and MCP Registry
(`#1640`/`#1523`/`#1570`/`#1583`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result produced by each Stage 230 protocol guard."""

    scenario_id: str
    passed: bool
    decision_code: str
    action: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


def _canonical_jcs(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# PR-01: x402#3920 & #3922 — Pre-Signature expectedAmount / Tolerance &
#        Network-Pinned EXPECTED_PAY_TO / EXPECTED_ASSET
# ---------------------------------------------------------------------------
def evaluate_x402_expected_amount_and_pinned_recipient_guard(
    *,
    quote_key: str,
    offered_amount_atomic: str | int,
    max_amount_per_payment_atomic: int,
    expected_amount_mode: str,
    explicit_expected_atomic: int | None,
    first_accepted_ledger: dict[str, int],
    expected_amount_tolerance: float,
    offered_network: str,
    offered_pay_to: str,
    offered_asset: str,
    expected_network: str | None,
    expected_pay_to: str | None,
    expected_asset: str | None,
) -> GuardEvaluation:
    """Enforce x402#3920 expectedAmount & #3922 pre-sign recipient/asset pinning."""
    if isinstance(offered_amount_atomic, bool) or not str(offered_amount_atomic).isdigit():
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            decision_code="X402_NON_INTEGER_ATOMIC_AMOUNT_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"offered_amount_atomic": offered_amount_atomic},
        )
    offered = int(offered_amount_atomic)
    if offered <= 0 or offered > max_amount_per_payment_atomic:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            decision_code="X402_MAX_SPEND_CAP_EXCEEDED",
            action="Send to a human",
            confidence=0.99,
            details={"offered": offered, "max_amount_per_payment_atomic": max_amount_per_payment_atomic},
        )
    if expected_amount_tolerance < 1.0:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            decision_code="X402_INVALID_EXPECTED_AMOUNT_TOLERANCE",
            action="Send to a human",
            confidence=0.99,
            details={"expected_amount_tolerance": expected_amount_tolerance},
        )

    anchor_source = None
    expected_val = None
    if expected_amount_mode == "explicit":
        expected_val = explicit_expected_atomic
        anchor_source = "caller-config"
    elif expected_amount_mode == "first-accepted":
        if quote_key in first_accepted_ledger:
            expected_val = first_accepted_ledger[quote_key]
            anchor_source = "quote-ledger"
        else:
            expected_val = offered
            anchor_source = "quote-ledger"

    if expected_val is not None and expected_val > 0:
        upper = expected_val * expected_amount_tolerance
        lower = expected_val / expected_amount_tolerance
        if offered > upper or offered < lower:
            return GuardEvaluation(
                scenario_id="PR-01",
                passed=False,
                decision_code="X402_QUOTE_MISMATCH_ERROR_PRE_SIGN",
                action="Send to a human",
                confidence=0.99,
                details={
                    "quoteKey": quote_key,
                    "expected": expected_val,
                    "offered": offered,
                    "source": anchor_source,
                },
            )

    if (expected_pay_to or expected_asset) and not expected_network:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            decision_code="X402_PINNED_TARGET_MISSING_EXPECTED_NETWORK",
            action="Send to a human",
            confidence=0.99,
            details={"expected_pay_to": expected_pay_to, "expected_asset": expected_asset},
        )
    if expected_network and offered_network != expected_network:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            decision_code="X402_NETWORK_MISMATCH_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"offered_network": offered_network, "expected_network": expected_network},
        )

    if expected_pay_to or expected_asset:
        if offered_network.startswith("eip155:"):
            if expected_pay_to and offered_pay_to.lower() != expected_pay_to.lower():
                return GuardEvaluation(
                    scenario_id="PR-01",
                    passed=False,
                    decision_code="X402_EVM_PAY_TO_MISMATCH",
                    action="Send to a human",
                    confidence=0.99,
                    details={"offered_pay_to": offered_pay_to, "expected_pay_to": expected_pay_to},
                )
            if expected_asset and offered_asset.lower() != expected_asset.lower():
                return GuardEvaluation(
                    scenario_id="PR-01",
                    passed=False,
                    decision_code="X402_EVM_ASSET_MISMATCH",
                    action="Send to a human",
                    confidence=0.99,
                    details={"offered_asset": offered_asset, "expected_asset": expected_asset},
                )
        elif offered_network.startswith("solana:"):
            if expected_pay_to and offered_pay_to != expected_pay_to:
                return GuardEvaluation(
                    scenario_id="PR-01",
                    passed=False,
                    decision_code="X402_SOLANA_CASE_SENSITIVE_PAY_TO_MISMATCH",
                    action="Send to a human",
                    confidence=0.99,
                    details={"offered_pay_to": offered_pay_to, "expected_pay_to": expected_pay_to},
                )
            if expected_asset and offered_asset != expected_asset:
                return GuardEvaluation(
                    scenario_id="PR-01",
                    passed=False,
                    decision_code="X402_SOLANA_CASE_SENSITIVE_ASSET_MISMATCH",
                    action="Send to a human",
                    confidence=0.99,
                    details={"offered_asset": offered_asset, "expected_asset": expected_asset},
                )
        else:
            return GuardEvaluation(
                scenario_id="PR-01",
                passed=False,
                decision_code="X402_UNSUPPORTED_PINNED_NAMESPACE_FAIL_CLOSED",
                action="Send to a human",
                confidence=0.99,
                details={"offered_network": offered_network},
            )

    return GuardEvaluation(
        scenario_id="PR-01",
        passed=True,
        decision_code="X402_EXPECTED_AMOUNT_AND_PINNED_TARGET_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"quoteKey": quote_key, "offered": offered, "network": offered_network},
    )


# ---------------------------------------------------------------------------
# PR-02: x402#3783 & #3207 — delivery-receipt Extension & offer-receipt
#        13-Vector Conformance (alg:none / HS256 Confusion Rejection)
# ---------------------------------------------------------------------------
def evaluate_x402_delivery_receipt_and_offer_vector_guard(
    *,
    receipt_payload: dict[str, Any],
    claimed_receipt_id: str,
    signed_octets: str,
    delivery_mode: str,
    payment_response_member_bytes: int,
    session_sig_alg: str,
    session_sig_valid: bool,
    archival_sig_alg: str,
    archival_sig_valid: bool,
    key_directory_epoch_chained: bool,
    offer_jws_segments: int,
    offer_jws_alg: str,
) -> GuardEvaluation:
    """Enforce x402#3783 delivery-receipt & #3207 offer-receipt JWS conformance."""
    if offer_jws_segments != 3:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_OFFER_RECEIPT_PARSE_STAGE_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"offer_jws_segments": offer_jws_segments},
        )
    if offer_jws_alg in ("none", "HS256", "HS384", "HS512"):
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_OFFER_RECEIPT_ALG_CONFUSION_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"offer_jws_alg": offer_jws_alg},
        )

    expected_receipt_id = hashlib.sha256(_canonical_jcs(receipt_payload).encode("utf-8")).hexdigest()
    expected_octets = f"x402-delivery-receipt/1\n{expected_receipt_id}"
    if claimed_receipt_id != expected_receipt_id or signed_octets != expected_octets:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_DELIVERY_RECEIPT_OCTETS_OR_ID_MISMATCH",
            action="Send to a human",
            confidence=0.99,
            details={"claimed_receipt_id": claimed_receipt_id, "expected_receipt_id": expected_receipt_id},
        )
    if delivery_mode == "reference" and payment_response_member_bytes > 1024:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_DELIVERY_RECEIPT_REFERENCE_OVER_1KB_BUDGET",
            action="Send to a human",
            confidence=0.99,
            details={"payment_response_member_bytes": payment_response_member_bytes},
        )
    if session_sig_alg != "Ed25519" or not session_sig_valid:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_DELIVERY_RECEIPT_SESSION_SIG_INVALID",
            action="Send to a human",
            confidence=0.99,
            details={"session_sig_alg": session_sig_alg, "session_sig_valid": session_sig_valid},
        )
    if archival_sig_alg not in ("ML-DSA-65", "ML-DSA-87") or not archival_sig_valid or not key_directory_epoch_chained:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            decision_code="X402_DELIVERY_RECEIPT_ARCHIVAL_PQ_OR_KEY_EPOCH_INVALID",
            action="Send to a human",
            confidence=0.99,
            details={
                "archival_sig_alg": archival_sig_alg,
                "archival_sig_valid": archival_sig_valid,
                "key_directory_epoch_chained": key_directory_epoch_chained,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-02",
        passed=True,
        decision_code="X402_DELIVERY_RECEIPT_AND_OFFER_VECTOR_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"receipt_id": expected_receipt_id, "archival_sig_alg": archival_sig_alg},
    )


# ---------------------------------------------------------------------------
# PR-03: x402#3688 & #715 — @x402/lnbtc Request-Bound BOLT11 & Atto Feeless SEND
# ---------------------------------------------------------------------------
def evaluate_x402_lnbtc_and_atto_exact_guard(
    *,
    binding_profile: str,
    binding_source: str,
    body_hashed_from_raw_bytes: bool,
    is_paid_retry: bool,
    reused_accepted_invoice: bool,
    preimage_hex: str,
    expected_payment_hash_hex: str,
    consumed_payment_hashes: set[str],
    atto_network: str,
    atto_amount_str: str,
    atto_tx_type: str,
    atto_pow_and_sig_valid: bool,
    atto_sender_frontier_competing: bool,
) -> GuardEvaluation:
    """Enforce x402#3688 @x402/lnbtc BOLT11 binding & #715 Atto exact SEND."""
    if binding_profile not in ("http:1", "mcp:1") or binding_source != "server_live_request" or not body_hashed_from_raw_bytes:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_LNBTC_CLIENT_ECHO_OR_PARSED_BODY_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={
                "binding_profile": binding_profile,
                "binding_source": binding_source,
                "body_hashed_from_raw_bytes": body_hashed_from_raw_bytes,
            },
        )
    if is_paid_retry and not reused_accepted_invoice:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_LNBTC_PAID_RETRY_INVOICE_CHURN_DOS_BLOCKED",
            action="Send to a human",
            confidence=0.99,
            details={"is_paid_retry": is_paid_retry, "reused_accepted_invoice": reused_accepted_invoice},
        )
    computed_hash = hashlib.sha256(bytes.fromhex(preimage_hex)).hexdigest()
    replay_key = f"lnbtc:{expected_payment_hash_hex}"
    if computed_hash != expected_payment_hash_hex or replay_key in consumed_payment_hashes:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_LNBTC_PREIMAGE_MISMATCH_OR_REPLAY",
            action="Send to a human",
            confidence=0.99,
            details={"computed_hash": computed_hash, "expected_payment_hash_hex": expected_payment_hash_hex},
        )

    if atto_network not in ("atto:live", "atto:beta", "atto:dev", "atto:local"):
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_ATTO_UNSUPPORTED_NETWORK",
            action="Send to a human",
            confidence=0.99,
            details={"atto_network": atto_network},
        )
    if not re.fullmatch(r"[1-9][0-9]*", atto_amount_str) or int(atto_amount_str) >= 2**64:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_ATTO_NON_CANONICAL_UINT64_DECIMAL_STRING",
            action="Send to a human",
            confidence=0.99,
            details={"atto_amount_str": atto_amount_str},
        )
    if atto_tx_type != "SEND" or not atto_pow_and_sig_valid or atto_sender_frontier_competing:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            decision_code="X402_ATTO_SEND_POW_OR_FRONTIER_INVALID",
            action="Send to a human",
            confidence=0.99,
            details={
                "atto_tx_type": atto_tx_type,
                "atto_pow_and_sig_valid": atto_pow_and_sig_valid,
                "atto_sender_frontier_competing": atto_sender_frontier_competing,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-03",
        passed=True,
        decision_code="X402_LNBTC_AND_ATTO_EXACT_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"replay_key": replay_key, "atto_network": atto_network},
    )


# ---------------------------------------------------------------------------
# PR-04: ucp#861, #801, #691 & js-sdk#89 — Lodging Cancellation Schedule,
#        Cart continue_url, Self-Describing price_treatment & allOf required
# ---------------------------------------------------------------------------
def evaluate_ucp_lodging_schedule_cart_continue_price_treatment_guard(
    *,
    cancellation_schedule: list[dict[str, Any]],
    evaluation_epoch: int,
    selected_tier_id: str,
    cart_continue_url: str,
    cart_purchasable: bool,
    continue_url_preserves_items: bool,
    continue_url_has_remediation_fallback: bool,
    price_treatment_tax_inclusion: str | None,
    allof_node_has_properties_key: bool,
    allof_top_level_required: list[str],
    projected_required: list[str],
) -> GuardEvaluation:
    """Enforce ucp#861, #801, #691, and js-sdk#89 invariants."""
    matched_tier = None
    for window in cancellation_schedule:
        start = window.get("starts_at", 0)
        end = window.get("ends_at", 2**62)
        if start <= evaluation_epoch < end:
            matched_tier = window.get("id")
            break
    if matched_tier != selected_tier_id:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_MISMATCH",
            action="Send to a human",
            confidence=0.99,
            details={"matched_tier": matched_tier, "selected_tier_id": selected_tier_id},
        )

    if not cart_continue_url.startswith("https://"):
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            decision_code="UCP_CART_CONTINUE_URL_NOT_HTTPS",
            action="Send to a human",
            confidence=0.99,
            details={"cart_continue_url": cart_continue_url},
        )
    if cart_purchasable and not continue_url_preserves_items:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            decision_code="UCP_CART_CONTINUE_URL_DROPPED_LINE_ITEMS",
            action="Send to a human",
            confidence=0.99,
            details={"cart_purchasable": cart_purchasable, "continue_url_preserves_items": continue_url_preserves_items},
        )
    if not cart_purchasable and not continue_url_has_remediation_fallback:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            decision_code="UCP_CART_UNPURCHASABLE_MISSING_REMEDIATION_FALLBACK",
            action="Send to a human",
            confidence=0.99,
            details={"cart_purchasable": cart_purchasable},
        )

    known_inclusions = {"included", "excluded", "not_applicable"}
    normalized_tax_inclusion = (
        price_treatment_tax_inclusion if price_treatment_tax_inclusion in known_inclusions else None
    )

    if not allof_node_has_properties_key and allof_top_level_required != projected_required:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            decision_code="UCP_JS_SDK_ALLOF_TOP_LEVEL_REQUIRED_DROPPED",
            action="Send to a human",
            confidence=0.99,
            details={"allof_top_level_required": allof_top_level_required, "projected_required": projected_required},
        )

    return GuardEvaluation(
        scenario_id="PR-04",
        passed=True,
        decision_code="UCP_LODGING_CART_PRICE_AND_ALLOF_REQUIRED_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={
            "matched_tier": matched_tier,
            "normalized_tax_inclusion": normalized_tax_inclusion,
            "projected_required": projected_required,
        },
    )


# ---------------------------------------------------------------------------
# PR-05: modelcontextprotocol#3149 & #2633 — SEP-3149 CIMD
#        token_endpoint_auth_methods_supported & SEP-2633 mcp.json
# ---------------------------------------------------------------------------
def evaluate_mcp_sep3149_cimd_and_sep2633_mcp_json_guard(
    *,
    cimd_metadata: dict[str, Any],
    as_supported_auth_methods: list[str],
    mcp_json_config: dict[str, Any],
) -> GuardEvaluation:
    """Enforce SEP-3149 CIMD required auth array & SEP-2633 mcp.json schema."""
    methods = cimd_metadata.get("token_endpoint_auth_methods_supported")
    if not isinstance(methods, list) or not methods or not all(isinstance(m, str) and m for m in methods):
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            decision_code="MCP_SEP3149_CIMD_AUTH_METHODS_ARRAY_REQUIRED",
            action="Send to a human",
            confidence=0.99,
            details={"cimd_metadata_keys": sorted(cimd_metadata.keys())},
        )
    common_methods = [m for m in methods if m in as_supported_auth_methods]
    if not common_methods:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            decision_code="MCP_SEP3149_CIMD_AS_AUTH_INTERSECTION_EMPTY",
            action="Send to a human",
            confidence=0.99,
            details={"cimd_methods": methods, "as_supported": as_supported_auth_methods},
        )

    servers = mcp_json_config.get("mcpServers") or mcp_json_config.get("servers")
    if not isinstance(servers, dict) or not servers:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            decision_code="MCP_SEP2633_MCP_JSON_SERVERS_MISSING",
            action="Send to a human",
            confidence=0.99,
            details={"mcp_json_keys": sorted(mcp_json_config.keys())},
        )
    for name, srv in servers.items():
        stype = srv.get("type")
        if stype not in ("stdio", "http"):
            return GuardEvaluation(
                scenario_id="PR-05",
                passed=False,
                decision_code="MCP_SEP2633_INVALID_SERVER_TRANSPORT_TYPE",
                action="Send to a human",
                confidence=0.99,
                details={"server": name, "type": stype},
            )
        if srv.get("plaintext_secret_in_file", False):
            return GuardEvaluation(
                scenario_id="PR-05",
                passed=False,
                decision_code="MCP_SEP2633_PLAINTEXT_SECRET_REJECTED",
                action="Send to a human",
                confidence=0.99,
                details={"server": name},
            )

    return GuardEvaluation(
        scenario_id="PR-05",
        passed=True,
        decision_code="MCP_SEP3149_CIMD_AND_SEP2633_MCP_JSON_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"negotiated_auth_method": common_methods[0], "server_count": len(servers)},
    )


# ---------------------------------------------------------------------------
# PR-06: java-sdk#1271, #1202, #1159, & #1160 — McpServerTool Shortcuts,
#        SEP-2243 Mcp-Param-{Name} Validation, Idle GET Flush & listRoots Gate
# ---------------------------------------------------------------------------
def evaluate_mcp_java_sdk_param_header_flush_roots_guard(
    *,
    registered_tool_names: list[str],
    header_marked_params: dict[str, Any],
    http_mcp_param_headers: dict[str, str],
    idle_get_headers_flushed_immediately: bool,
    client_initialized: bool,
    client_supports_roots: bool,
    server_called_list_roots: bool,
    threw_illegal_state_before_session: bool,
) -> GuardEvaluation:
    """Enforce java-sdk#1271, #1202, #1159, and #1160 invariants."""
    if len(registered_tool_names) != len(set(registered_tool_names)):
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            decision_code="MCP_JAVA_DUPLICATE_SERVER_TOOL_NAME_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"registered_tool_names": registered_tool_names},
        )
    for param_name, body_val in header_marked_params.items():
        header_key = f"Mcp-Param-{param_name}"
        if body_val is not None:
            if header_key not in http_mcp_param_headers or http_mcp_param_headers[header_key] != str(body_val):
                return GuardEvaluation(
                    scenario_id="PR-06",
                    passed=False,
                    decision_code="MCP_JAVA_SEP2243_PARAM_HEADER_MISMATCH_MINUS_32020",
                    action="Send to a human",
                    confidence=0.99,
                    details={"error_code": -32020, "param": param_name, "expected": str(body_val)},
                )
    if not idle_get_headers_flushed_immediately:
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            decision_code="MCP_JAVA_IDLE_STREAMABLE_GET_NOT_FLUSHED",
            action="Send to a human",
            confidence=0.99,
            details={"idle_get_headers_flushed_immediately": idle_get_headers_flushed_immediately},
        )
    if server_called_list_roots and (not client_initialized or not client_supports_roots):
        if not threw_illegal_state_before_session:
            return GuardEvaluation(
                scenario_id="PR-06",
                passed=False,
                decision_code="MCP_JAVA_UNSUPPORTED_LIST_ROOTS_SENT_OVER_WIRE",
                action="Send to a human",
                confidence=0.99,
                details={"client_initialized": client_initialized, "client_supports_roots": client_supports_roots},
            )

    return GuardEvaluation(
        scenario_id="PR-06",
        passed=True,
        decision_code="MCP_JAVA_PARAM_HEADER_FLUSH_AND_ROOTS_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"tool_count": len(registered_tool_names), "checked_params": sorted(header_marked_params.keys())},
    )


# ---------------------------------------------------------------------------
# PR-07: kotlin-sdk#1134, #1101, & #1130 — Cold/Lazy Pagination Flows,
#        StdioServerTransport Cancellation Isolation & SSE Deprecation
# ---------------------------------------------------------------------------
def evaluate_mcp_kotlin_sdk_flow_stdio_cancel_sse_guard(
    *,
    requests_sent_before_flow_collect: int,
    pages_fetched_lazily_one_by_one: bool,
    handler_threw_cancellation: bool,
    transport_scope_active: bool,
    stdio_read_loop_kept_running: bool,
    sse_transport_marked_deprecated_sep2596: bool,
) -> GuardEvaluation:
    """Enforce kotlin-sdk#1134, #1101, and #1130 invariants."""
    if requests_sent_before_flow_collect != 0 or not pages_fetched_lazily_one_by_one:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            decision_code="MCP_KOTLIN_PAGINATION_FLOW_NOT_COLD_OR_LAZY",
            action="Send to a human",
            confidence=0.99,
            details={
                "requests_sent_before_flow_collect": requests_sent_before_flow_collect,
                "pages_fetched_lazily_one_by_one": pages_fetched_lazily_one_by_one,
            },
        )
    if handler_threw_cancellation and transport_scope_active and not stdio_read_loop_kept_running:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            decision_code="MCP_KOTLIN_HANDLER_CANCEL_CLOSED_STDIO_TRANSPORT",
            action="Send to a human",
            confidence=0.99,
            details={"stdio_read_loop_kept_running": stdio_read_loop_kept_running},
        )
    if not sse_transport_marked_deprecated_sep2596:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            decision_code="MCP_KOTLIN_SSE_TRANSPORT_MISSING_DEPRECATION",
            action="Send to a human",
            confidence=0.99,
            details={"sse_transport_marked_deprecated_sep2596": sse_transport_marked_deprecated_sep2596},
        )

    return GuardEvaluation(
        scenario_id="PR-07",
        passed=True,
        decision_code="MCP_KOTLIN_FLOW_STDIO_CANCEL_AND_SSE_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"stdio_read_loop_kept_running": stdio_read_loop_kept_running},
    )


# ---------------------------------------------------------------------------
# PR-08: swift-sdk#311, #310, & #309 — Header-Only ;base64 Data URL Detection,
#        Raw-Byte %XX Percent-Decoding & Heartbeat Failure State Transition
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_sdk_data_url_and_heartbeat_guard(
    *,
    data_url: str,
    expected_is_base64: bool,
    expected_decoded_bytes: bytes | None,
    heartbeat_post_backoff_states: list[str],
) -> GuardEvaluation:
    """Enforce swift-sdk#309, #310, and #311 data URL & heartbeat invariants."""
    if not data_url.startswith("data:") or "," not in data_url:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            decision_code="MCP_SWIFT_INVALID_DATA_URL_SYNTAX",
            action="Send to a human",
            confidence=0.99,
            details={"data_url": data_url},
        )
    header, payload = data_url[5:].split(",", 1)
    is_base64 = header.endswith(";base64")
    if is_base64 != expected_is_base64:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            decision_code="MCP_SWIFT_PAYLOAD_BASE64_MARKER_CONFUSION",
            action="Send to a human",
            confidence=0.99,
            details={"header": header, "is_base64": is_base64, "expected_is_base64": expected_is_base64},
        )

    decoded: bytes | None = None
    if not is_base64:
        out = bytearray()
        i = 0
        ok = True
        while i < len(payload):
            if payload[i] == "%":
                if i + 2 >= len(payload) or not re.fullmatch(r"[0-9A-Fa-f]{2}", payload[i + 1 : i + 3]):
                    ok = False
                    break
                out.append(int(payload[i + 1 : i + 3], 16))
                i += 3
            else:
                out.extend(payload[i].encode("utf-8"))
                i += 1
        decoded = bytes(out) if ok else None

    if decoded != expected_decoded_bytes:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            decision_code="MCP_SWIFT_DATA_URL_PERCENT_BYTE_DECODE_MISMATCH",
            action="Send to a human",
            confidence=0.99,
            details={"decoded": decoded, "expected": expected_decoded_bytes},
        )
    if not any(s in ("disconnected", "cancelled", "connecting") for s in heartbeat_post_backoff_states):
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            decision_code="MCP_SWIFT_HEARTBEAT_TRANSPORT_STATE_UNVERIFIED",
            action="Send to a human",
            confidence=0.99,
            details={"heartbeat_post_backoff_states": heartbeat_post_backoff_states},
        )

    return GuardEvaluation(
        scenario_id="PR-08",
        passed=True,
        decision_code="MCP_SWIFT_DATA_URL_AND_HEARTBEAT_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"is_base64": is_base64, "decoded_len": len(decoded) if decoded is not None else None},
    )


# ---------------------------------------------------------------------------
# PR-09: ruby-sdk#632 & #631 — subscriptions/listen resources_subscribe_handler
#        Consultation & ServerSession#notify_* exception_reporter Rescue
# ---------------------------------------------------------------------------
def evaluate_mcp_ruby_sdk_listen_auth_and_notify_rescue_guard(
    *,
    requested_resource_uris: list[str],
    allowed_resource_uris: set[str],
    consulted_resources_subscribe_handler: bool,
    notify_transport_failed: bool,
    used_public_configuration_exception_reporter: bool,
    leaked_no_method_error_to_tool_caller: bool,
) -> GuardEvaluation:
    """Enforce ruby-sdk#632 and #631 invariants."""
    distinct_uris = list(dict.fromkeys(requested_resource_uris))
    unauthorized = [u for u in distinct_uris if u not in allowed_resource_uris]
    if not consulted_resources_subscribe_handler or unauthorized:
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            decision_code="MCP_RUBY_LISTEN_BYPASSED_SUBSCRIBE_HANDLER",
            action="Send to a human",
            confidence=0.99,
            details={
                "consulted_resources_subscribe_handler": consulted_resources_subscribe_handler,
                "unauthorized": unauthorized,
            },
        )
    if notify_transport_failed and (not used_public_configuration_exception_reporter or leaked_no_method_error_to_tool_caller):
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            decision_code="MCP_RUBY_PRIVATE_REPORT_EXCEPTION_NO_METHOD_ERROR",
            action="Send to a human",
            confidence=0.99,
            details={
                "used_public_configuration_exception_reporter": used_public_configuration_exception_reporter,
                "leaked_no_method_error_to_tool_caller": leaked_no_method_error_to_tool_caller,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-09",
        passed=True,
        decision_code="MCP_RUBY_LISTEN_AUTH_AND_NOTIFY_RESCUE_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"authorized_uris": distinct_uris},
    )


# ---------------------------------------------------------------------------
# PR-10: php-sdk#614 & #432 — Client Transport Close on Reconnect &
#        Fail-Fast Missing symfony/finder File-Discovery Guard
# ---------------------------------------------------------------------------
def evaluate_mcp_php_sdk_reconnect_close_and_finder_guard(
    *,
    previous_transport_closed_on_reconnect: bool,
    replacement_transport_closed_on_disconnect: bool,
    file_discovery_configured: bool,
    custom_discoverer_used: bool,
    symfony_finder_installed: bool,
    failed_fast_at_server_build: bool,
) -> GuardEvaluation:
    """Enforce php-sdk#614 and #432 invariants."""
    if not previous_transport_closed_on_reconnect or not replacement_transport_closed_on_disconnect:
        return GuardEvaluation(
            scenario_id="PR-10",
            passed=False,
            decision_code="MCP_PHP_RECONNECT_PREVIOUS_TRANSPORT_LEAKED",
            action="Send to a human",
            confidence=0.99,
            details={
                "previous_transport_closed_on_reconnect": previous_transport_closed_on_reconnect,
                "replacement_transport_closed_on_disconnect": replacement_transport_closed_on_disconnect,
            },
        )
    if file_discovery_configured and not custom_discoverer_used and not symfony_finder_installed:
        if not failed_fast_at_server_build:
            return GuardEvaluation(
                scenario_id="PR-10",
                passed=False,
                decision_code="MCP_PHP_MISSING_FINDER_SILENT_SKIP_REJECTED",
                action="Send to a human",
                confidence=0.99,
                details={"symfony_finder_installed": symfony_finder_installed},
            )

    return GuardEvaluation(
        scenario_id="PR-10",
        passed=True,
        decision_code="MCP_PHP_RECONNECT_CLOSE_AND_FINDER_GUARD_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"previous_transport_closed_on_reconnect": previous_transport_closed_on_reconnect},
    )


# ---------------------------------------------------------------------------
# PR-11: ext-apps#798, #824, & #821 — WebMCP document.modelContext Same-Origin
#        Sandbox Relay, Map-Server get-screenshot Tool & v1/v2 Peer Line
# ---------------------------------------------------------------------------
def evaluate_mcp_apps_webmcp_screenshot_and_peer_line_guard(
    *,
    view_tools_exposed_via_model_context: bool,
    relay_is_same_origin_sandbox_proxy: bool,
    map_server_exposes_get_screenshot: bool,
    host_mcp_sdk_major: int,
    selected_ext_apps_major: int,
) -> GuardEvaluation:
    """Enforce ext-apps#798, #821, and #824 invariants."""
    if not view_tools_exposed_via_model_context or not relay_is_same_origin_sandbox_proxy:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            decision_code="MCP_APPS_WEBMCP_RELAY_ORIGIN_VIOLATION",
            action="Send to a human",
            confidence=0.99,
            details={
                "view_tools_exposed_via_model_context": view_tools_exposed_via_model_context,
                "relay_is_same_origin_sandbox_proxy": relay_is_same_origin_sandbox_proxy,
            },
        )
    if not map_server_exposes_get_screenshot:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            decision_code="MCP_APPS_MAP_SERVER_GET_SCREENSHOT_MISSING",
            action="Send to a human",
            confidence=0.99,
            details={"map_server_exposes_get_screenshot": map_server_exposes_get_screenshot},
        )
    if host_mcp_sdk_major != selected_ext_apps_major:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            decision_code="MCP_APPS_SDK_PEER_MAJOR_LINE_MISMATCH",
            action="Send to a human",
            confidence=0.99,
            details={"host_mcp_sdk_major": host_mcp_sdk_major, "selected_ext_apps_major": selected_ext_apps_major},
        )

    return GuardEvaluation(
        scenario_id="PR-11",
        passed=True,
        decision_code="MCP_APPS_WEBMCP_SCREENSHOT_AND_PEER_LINE_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"selected_ext_apps_major": selected_ext_apps_major},
    )


# ---------------------------------------------------------------------------
# PR-12: conformance#529 & #564 — SEP-1932 DPoP Discovery Signals &
#        Harmonized Token-Request Proof / iat-Window / Nonce Retry
# ---------------------------------------------------------------------------
def evaluate_mcp_conformance_sep1932_dpop_discovery_and_proof_guard(
    *,
    www_authenticate_schemes: list[str],
    prm_dpop_algs_supported: list[str],
    token_request_has_dpop_proof: bool,
    proof_iat_skew_seconds: int,
    max_iat_skew_seconds: int,
    retried_on_use_dpop_nonce: bool,
) -> GuardEvaluation:
    """Enforce conformance#529 and #564 SEP-1932 DPoP discovery & proof checks."""
    if "DPoP" not in www_authenticate_schemes or not prm_dpop_algs_supported:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            decision_code="MCP_CONFORMANCE_SEP1932_DPOP_DISCOVERY_MISSING",
            action="Send to a human",
            confidence=0.99,
            details={
                "www_authenticate_schemes": www_authenticate_schemes,
                "prm_dpop_algs_supported": prm_dpop_algs_supported,
            },
        )
    if not token_request_has_dpop_proof or abs(proof_iat_skew_seconds) > max_iat_skew_seconds or not retried_on_use_dpop_nonce:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            decision_code="MCP_CONFORMANCE_SEP1932_TOKEN_PROOF_OR_NONCE_INVALID",
            action="Send to a human",
            confidence=0.99,
            details={
                "token_request_has_dpop_proof": token_request_has_dpop_proof,
                "proof_iat_skew_seconds": proof_iat_skew_seconds,
                "retried_on_use_dpop_nonce": retried_on_use_dpop_nonce,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-12",
        passed=True,
        decision_code="MCP_CONFORMANCE_SEP1932_DPOP_DISCOVERY_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"prm_dpop_algs_supported": prm_dpop_algs_supported},
    )


# ---------------------------------------------------------------------------
# PR-13: conformance#521 & #541 — SEP-3415 Triggers & Events Server/Client
#        Conformance Suite (150 Negative Controls, Dedup & Cursor Resume)
# ---------------------------------------------------------------------------
def evaluate_mcp_conformance_sep3415_events_suite_guard(
    *,
    events_list_supported: bool,
    subscription_listen_mcp_name_header_valid: bool,
    negative_controls_rejected_count: int,
    duplicate_event_id_deduplicated: bool,
    cursor_resume_replayed_missed_events: bool,
) -> GuardEvaluation:
    """Enforce conformance#521 and #541 SEP-3415 Events server/client checks."""
    if (
        not events_list_supported
        or not subscription_listen_mcp_name_header_valid
        or negative_controls_rejected_count < 150
        or not duplicate_event_id_deduplicated
        or not cursor_resume_replayed_missed_events
    ):
        return GuardEvaluation(
            scenario_id="PR-13",
            passed=False,
            decision_code="MCP_CONFORMANCE_SEP3415_EVENTS_CHECK_FAILED",
            action="Send to a human",
            confidence=0.99,
            details={
                "events_list_supported": events_list_supported,
                "subscription_listen_mcp_name_header_valid": subscription_listen_mcp_name_header_valid,
                "negative_controls_rejected_count": negative_controls_rejected_count,
                "duplicate_event_id_deduplicated": duplicate_event_id_deduplicated,
                "cursor_resume_replayed_missed_events": cursor_resume_replayed_missed_events,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-13",
        passed=True,
        decision_code="MCP_CONFORMANCE_SEP3415_EVENTS_SUITE_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"negative_controls_rejected_count": negative_controls_rejected_count},
    )


# ---------------------------------------------------------------------------
# PR-14: registry#1640 & #1523 — .well-known/mcp-registry-auth HTTP Contract
#        & Pinned mcp-publisher v1.8.1 Sigstore cosign verify-blob Gate
# ---------------------------------------------------------------------------
def evaluate_mcp_registry_http_auth_and_sigstore_installer_guard(
    *,
    http_status: int,
    accept_header: str,
    user_agent: str,
    proof_body_bytes: int,
    elapsed_seconds: float,
    installer_version_tag: str,
    cosign_verify_blob_passed: bool,
    extracted_before_verify: bool,
) -> GuardEvaluation:
    """Enforce registry#1640 HTTP auth fetch contract & #1523 cosign check."""
    if (
        http_status != 200
        or accept_header != "text/plain"
        or user_agent != "mcp-registry/1.0"
        or proof_body_bytes <= 0
        or proof_body_bytes > 4096
        or elapsed_seconds > 10.0
    ):
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            decision_code="MCP_REGISTRY_HTTP_VERIFICATION_CONTRACT_VIOLATION",
            action="Send to a human",
            confidence=0.99,
            details={
                "http_status": http_status,
                "proof_body_bytes": proof_body_bytes,
                "elapsed_seconds": elapsed_seconds,
            },
        )
    if installer_version_tag == "latest" or not re.fullmatch(r"v\d+\.\d+\.\d+", installer_version_tag):
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            decision_code="MCP_REGISTRY_MUTABLE_LATEST_INSTALLER_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={"installer_version_tag": installer_version_tag},
        )
    if not cosign_verify_blob_passed or extracted_before_verify:
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            decision_code="MCP_REGISTRY_UNVERIFIED_SIGSTORE_BUNDLE_REJECTED",
            action="Send to a human",
            confidence=0.99,
            details={
                "cosign_verify_blob_passed": cosign_verify_blob_passed,
                "extracted_before_verify": extracted_before_verify,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-14",
        passed=True,
        decision_code="MCP_REGISTRY_HTTP_AUTH_AND_SIGSTORE_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"installer_version_tag": installer_version_tag, "proof_body_bytes": proof_body_bytes},
    )


# ---------------------------------------------------------------------------
# PR-15: registry#1570 & #1583 — Immutable Forge repository.id at init &
#        Strict validateArgument ("positional" | "named" + value/valueHint)
# ---------------------------------------------------------------------------
def evaluate_mcp_registry_repo_id_and_argument_validator_guard(
    *,
    repository_block: dict[str, Any],
    arguments: list[dict[str, Any]],
) -> GuardEvaluation:
    """Enforce registry#1570 repository.id & #1583 argument validation."""
    repo_url = repository_block.get("url", "")
    repo_id = repository_block.get("id", "")
    if not repo_url or not isinstance(repo_id, str) or not repo_id.strip():
        return GuardEvaluation(
            scenario_id="PR-15",
            passed=False,
            decision_code="MCP_REGISTRY_MISSING_IMMUTABLE_REPOSITORY_ID",
            action="Send to a human",
            confidence=0.99,
            details={"repository_block": repository_block},
        )
    for idx, arg in enumerate(arguments):
        arg_type = arg.get("type")
        if arg_type not in ("positional", "named"):
            return GuardEvaluation(
                scenario_id="PR-15",
                passed=False,
                decision_code="MCP_REGISTRY_INVALID_ARGUMENT_TYPE_REJECTED",
                action="Send to a human",
                confidence=0.99,
                details={"index": idx, "type": arg_type, "error_ref": "invalid-argument-type"},
            )
        if arg_type == "positional":
            val = arg.get("value")
            hint = arg.get("valueHint")
            if not (isinstance(val, str) and val.strip()) and not (isinstance(hint, str) and hint.strip()):
                return GuardEvaluation(
                    scenario_id="PR-15",
                    passed=False,
                    decision_code="MCP_REGISTRY_POSITIONAL_ARG_VALUE_OR_HINT_REQUIRED",
                    action="Send to a human",
                    confidence=0.99,
                    details={"index": idx, "error_ref": "positional-argument-value-or-hint-required"},
                )
        elif arg_type == "named":
            name = arg.get("name")
            if not isinstance(name, str) or not name.strip():
                return GuardEvaluation(
                    scenario_id="PR-15",
                    passed=False,
                    decision_code="MCP_REGISTRY_NAMED_ARG_NAME_REQUIRED",
                    action="Send to a human",
                    confidence=0.99,
                    details={"index": idx},
                )

    return GuardEvaluation(
        scenario_id="PR-15",
        passed=True,
        decision_code="MCP_REGISTRY_REPO_ID_AND_ARGUMENTS_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"repository_id": repo_id, "argument_count": len(arguments)},
    )


# ---------------------------------------------------------------------------
# PR-16: ucp#848 & #988 — Guest Post-Purchase Single-Order Access Credentials
#        & Order MCP Binding Detached JWS / RFC 9421 Message Signing
# ---------------------------------------------------------------------------
def evaluate_ucp_guest_order_credentials_and_mcp_signing_guard(
    *,
    token_scoped_order_id: str,
    requested_order_id: str,
    token_scopes: list[str],
    order_claimed_by_account: bool,
    guest_token_revoked: bool,
    mcp_order_message_signed: bool,
    mcp_signature_verified: bool,
    mcp_payload_digest_matches: bool,
) -> GuardEvaluation:
    """Enforce ucp#848 guest order access credential scoping & #988 MCP signing."""
    allowed_guest_scopes = {"order:read", "order:return_initiate"}
    if token_scoped_order_id != requested_order_id or not set(token_scopes).issubset(allowed_guest_scopes):
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            decision_code="UCP_GUEST_ORDER_TOKEN_CROSS_ORDER_OR_SCOPE_ESCALATION",
            action="Send to a human",
            confidence=0.99,
            details={
                "token_scoped_order_id": token_scoped_order_id,
                "requested_order_id": requested_order_id,
                "token_scopes": token_scopes,
            },
        )
    if order_claimed_by_account and not guest_token_revoked:
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            decision_code="UCP_CLAIMED_ORDER_GUEST_TOKEN_NOT_REVOKED",
            action="Send to a human",
            confidence=0.99,
            details={"order_claimed_by_account": order_claimed_by_account, "guest_token_revoked": guest_token_revoked},
        )
    if not mcp_order_message_signed or not mcp_signature_verified or not mcp_payload_digest_matches:
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            decision_code="UCP_ORDER_MCP_BINDING_SIGNATURE_INVALID",
            action="Send to a human",
            confidence=0.99,
            details={
                "mcp_order_message_signed": mcp_order_message_signed,
                "mcp_signature_verified": mcp_signature_verified,
                "mcp_payload_digest_matches": mcp_payload_digest_matches,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-16",
        passed=True,
        decision_code="UCP_GUEST_ORDER_CREDENTIALS_AND_MCP_SIGNING_VERIFIED",
        action="Act automatically",
        confidence=0.99,
        details={"order_id": requested_order_id, "scopes": token_scopes},
    )
