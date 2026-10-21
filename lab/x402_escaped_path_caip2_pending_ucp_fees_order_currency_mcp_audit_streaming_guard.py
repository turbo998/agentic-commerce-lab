"""Stage 138: x402 Escaped/Decoded Path Route Matching, Strict CAIP-2 Chain ID,
Non-Terminal Settlement Pending Reconciliation & Fastify Buffered Raw Drain,
UCP Itemized Fees, Top-Level Order Currency & Update Checkout ID Omission, and
MCP SEP-3004 Tamper-Evident Audit Hash-Chain, SEP-2664/2998 Streaming Tool
Authority & Sierra tau2-bench Reward-Basis / Barge-In Guardrails.

Covers primary-source PRs:
- x402-foundation/x402 #3543, #3542, #3521, #3545, #3561, #3548, #3519, #3514,
  #3508, #3565, #3538, #3551, #3563, #3523, #3546, #3549
- Universal-Commerce-Protocol/ucp #220, #210, #145, #147, #96, #109, #184
- modelcontextprotocol/modelcontextprotocol #3004, #3005, #3000, #2998, #3071,
  #3002, #3094, #3109, #3006
- sierra-research/tau2-bench #226, #248, #221, #240, #239, #236, #210, #208,
  #177, #170
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any
from urllib.parse import unquote

STRICT_EVM_CAIP2_RE = re.compile(r"^eip155:([1-9][0-9]*)$")
ISO_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
FORBIDDEN_JWK_PRIVATE_FIELDS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth", "k"})

ARBITRUM_DEFAULT_ASSETS: tuple[dict[str, Any], ...] = (
    {
        "symbol": "USDC",
        "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "decimals": 6,
        "assetTransferMethod": "eip3009",
    },
    {
        "symbol": "USDs",
        "address": "0xD74f5255D557944cf7Dd0E45FF521520002D5748",
        "decimals": 18,
        "assetTransferMethod": "permit2",
    },
)


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    decision_code: str
    detail: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Gate 1: x402 Escaped/Decoded Path Route Matching, Strict CAIP-2 Chain ID,
#         Settlement Pending Reconciliation, Fastify Raw Drain & JWS JWK
# ---------------------------------------------------------------------------

def evaluate_x402_escaped_path_and_caip2_guard(
    *,
    protected_routes: tuple[str, ...],
    request_raw_path: str,
    network_caip2: str,
) -> GuardEvaluation:
    """Enforce x402 #3543/#3542 escaped + decoded route matching & #3521 strict CAIP-2."""
    # Check for malformed percent-encoding or double-encoded traversal
    if re.search(r"%(?![0-9A-Fa-f]{2})", request_raw_path):
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_MALFORMED_PERCENT_ENCODING_REJECTED",
            detail="Request path contains malformed percent-encoding sequence (#3543/#3542).",
            metadata={"request_raw_path": request_raw_path},
        )
    decoded_once = unquote(request_raw_path)
    decoded_twice = unquote(decoded_once)
    if ".." in decoded_once.split("/") or ".." in decoded_twice.split("/"):
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_ENCODED_DOT_TRAVERSAL_REJECTED",
            detail="Decoded request path contains dot-segment traversal (#3543/#3542).",
            metadata={"decoded_once": decoded_once, "decoded_twice": decoded_twice},
        )

    matched_route = None
    for route in protected_routes:
        if request_raw_path == route or decoded_once == route or decoded_twice == route:
            matched_route = route
            break

    caip_match = STRICT_EVM_CAIP2_RE.match(network_caip2)
    if not caip_match:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_MALFORMED_CAIP2_CHAIN_ID_REJECTED",
            detail=f"CAIP-2 network '{network_caip2}' failed strict ^eip155:[1-9][0-9]*$ check (#3521).",
            metadata={"network_caip2": network_caip2, "matched_route": matched_route},
        )

    chain_id = int(caip_match.group(1))
    return GuardEvaluation(
        allowed=True,
        decision_code="X402_ESCAPED_PATH_AND_CAIP2_VERIFIED",
        detail="Escaped/decoded route matching and strict CAIP-2 chain ID verified.",
        metadata={
            "matched_route": matched_route,
            "requires_payment": matched_route is not None,
            "decoded_path": decoded_once,
            "chain_id": chain_id,
        },
    )


def evaluate_x402_settlement_pending_and_fastify_buffer_guard(
    *,
    settlement_status: str,
    tx_hash: str,
    reconciled_on_chain: bool,
    client_mapped_status: str,
    fastify_buffered_raw_consumed: bool,
    error_pass_replayed_private_body: bool,
    jws_header_kid: str,
    jws_header_jwk: dict[str, Any] | None,
    trusted_kids: dict[str, str],
    bare_dollar_price: bool,
    selected_arbitrum_asset: str,
    python_mcp_paid_tool_handled: bool,
    python_mcp_corrective_retries: int,
    eip6492_factory_allowlisted: bool,
    gas_sponsor_rpc_capable: bool,
) -> GuardEvaluation:
    """Enforce x402 #3545/#3561, #3548, #3519, #3514, #3508, #3565 & #3551."""
    if settlement_status == "settlement_pending":
        if not tx_hash or not reconciled_on_chain:
            return GuardEvaluation(
                allowed=False,
                decision_code="X402_SETTLEMENT_PENDING_UNRECONCILED_RETRY_BLOCKED",
                detail="Non-terminal settlement_pending must reconcile on-chain via PendingSettlementStore before retry (#3545).",
                metadata={"settlement_status": settlement_status, "tx_hash": tx_hash},
            )
        if client_mapped_status == "settle_failed":
            return GuardEvaluation(
                allowed=False,
                decision_code="X402_CLIENT_PENDING_MISCLASSIFIED_AS_SETTLE_FAILED",
                detail="Typed client misclassified non-terminal settlement_pending as terminal settle_failed (#3561).",
                metadata={"client_mapped_status": client_mapped_status},
            )

    if not fastify_buffered_raw_consumed or error_pass_replayed_private_body:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_FASTIFY_BUFFERED_RAW_RESPONSE_REPLAY_LEAK",
            detail="Fastify buffered raw response calls were not consumed, risking status/body leak on error pass (#3548).",
            metadata={
                "fastify_buffered_raw_consumed": fastify_buffered_raw_consumed,
                "error_pass_replayed_private_body": error_pass_replayed_private_body,
            },
        )

    if jws_header_kid not in trusted_kids:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_JWS_UNKNOWN_KID_REJECTED",
            detail="Offer/receipt JWS header kid is not in the trusted key registry (#3519).",
            metadata={"jws_header_kid": jws_header_kid},
        )
    if jws_header_jwk is not None:
        leaked = FORBIDDEN_JWK_PRIVATE_FIELDS.intersection(jws_header_jwk.keys())
        if leaked:
            return GuardEvaluation(
                allowed=False,
                decision_code="X402_JWS_HEADER_JWK_PRIVATE_KEY_LEAK",
                detail=f"Offer/receipt JWS header jwk contains private key fields {sorted(leaked)} (#3519).",
                metadata={"leaked_fields": sorted(leaked)},
            )
        if jws_header_jwk.get("x") != trusted_kids[jws_header_kid]:
            return GuardEvaluation(
                allowed=False,
                decision_code="X402_JWS_HEADER_JWK_KID_MISMATCH",
                detail="Offer/receipt JWS header inline jwk does not match registered kid public key (#3519).",
                metadata={"jws_header_kid": jws_header_kid},
            )

    if bare_dollar_price and selected_arbitrum_asset != ARBITRUM_DEFAULT_ASSETS[0]["symbol"]:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_ARBITRUM_BARE_DOLLAR_ASSET_ORDER_MISMATCH",
            detail="Bare dollar price on Arbitrum One must resolve to USDC (eip3009) before Sperax USDs (permit2) (#3514).",
            metadata={"selected_arbitrum_asset": selected_arbitrum_asset},
        )

    if not python_mcp_paid_tool_handled or python_mcp_corrective_retries > 1:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_PYTHON_MCP_PAID_TOOL_RESPONSE_UNHANDLED",
            detail="Python MCP client must dispatch paid tool results via handle_payment_response with at most 1 corrective retry (#3508).",
            metadata={
                "python_mcp_paid_tool_handled": python_mcp_paid_tool_handled,
                "python_mcp_corrective_retries": python_mcp_corrective_retries,
            },
        )

    if not eip6492_factory_allowlisted:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_EIP6492_FACTORY_NOT_ALLOWLISTED",
            detail="EIP-6492 counterfactual wallet factory is not on the facilitator allowlist (#3565).",
            metadata={"eip6492_factory_allowlisted": eip6492_factory_allowlisted},
        )

    if not gas_sponsor_rpc_capable:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_GAS_SPONSORING_RPC_CAPABILITY_MISSING",
            detail="Facilitator gas sponsoring requested on an RPC endpoint lacking sponsorship capability (#3551).",
            metadata={"gas_sponsor_rpc_capable": gas_sponsor_rpc_capable},
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="X402_SETTLEMENT_FASTIFY_JWK_PERMIT2_MCP_VERIFIED",
        detail="x402 settlement_pending reconciliation, Fastify raw drain, JWS jwk/kid, Arbitrum USDC/USDs ordering, and Python MCP verified.",
        metadata={"jws_header_kid": jws_header_kid, "selected_arbitrum_asset": selected_arbitrum_asset},
    )


# ---------------------------------------------------------------------------
# Gate 2: UCP Itemized Fees (#220), Top-Level Order Currency (#210),
#         Checkout Update ID Omission (#145) & First-Class Errors (#147)
# ---------------------------------------------------------------------------

def evaluate_ucp_itemized_fees_order_currency_and_update_id_guard(
    *,
    order_currency: str,
    line_item_currencies: tuple[str, ...],
    itemized_fees: tuple[dict[str, Any], ...],
    declared_fees_total_minor: int,
    is_update_request: bool,
    payload_contains_checkout_id: bool,
    error_code: str | None,
    error_severity: str | None,
    schema_extends_parents: tuple[str, ...],
) -> GuardEvaluation:
    """Enforce UCP #220 itemized fees, #210 top-level Order.currency, #145 & #147/#96."""
    if not ISO_CURRENCY_RE.match(order_currency):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_ORDER_TOP_LEVEL_CURRENCY_INVALID",
            detail=f"Top-level Order.currency '{order_currency}' must be a valid 3-letter ISO 4217 code (#210).",
            metadata={"order_currency": order_currency},
        )

    for c in line_item_currencies:
        if c != order_currency:
            return GuardEvaluation(
                allowed=False,
                decision_code="UCP_ORDER_LINE_ITEM_CURRENCY_MISMATCH",
                detail=f"Line item currency '{c}' mismatches top-level Order.currency '{order_currency}' (#210).",
                metadata={"order_currency": order_currency, "line_item_currency": c},
            )

    computed_fees = 0
    for fee in itemized_fees:
        amt = int(fee.get("amount_minor", -1))
        fee_type = str(fee.get("type", "")).strip()
        if amt < 0 or not fee_type:
            return GuardEvaluation(
                allowed=False,
                decision_code="UCP_ITEMIZED_FEE_NEGATIVE_OR_UNTYPED",
                detail="Itemized fee extension requires non-negative amount_minor and explicit fee type (#220).",
                metadata={"fee": fee},
            )
        computed_fees += amt

    if computed_fees != declared_fees_total_minor:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_ITEMIZED_FEES_TOTAL_MISMATCH",
            detail=f"Sum of itemized fees ({computed_fees}) != declared_fees_total_minor ({declared_fees_total_minor}) (#220).",
            metadata={"computed_fees": computed_fees, "declared_fees_total_minor": declared_fees_total_minor},
        )

    if is_update_request and payload_contains_checkout_id:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_UPDATE_CHECKOUT_ID_DEPRECATED_MUST_OMIT",
            detail="Checkout update requests must omit 'id' in payload body (deprecated_required_to_omit, #145).",
            metadata={"is_update_request": is_update_request},
        )

    if error_code is not None and error_severity not in {"recoverable", "requires_buyer_input", "fatal"}:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_FIRST_CLASS_ERROR_SEVERITY_MISSING",
            detail="UCP first-class error concept requires explicit classification severity (#147).",
            metadata={"error_code": error_code, "error_severity": error_severity},
        )

    if len(schema_extends_parents) != len(set(schema_extends_parents)):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_MULTI_PARENT_SCHEMA_DUPLICATE_RESOLUTION",
            detail="Multi-parent schema extension contains duplicate/ambiguous parent references (#96/#91).",
            metadata={"schema_extends_parents": schema_extends_parents},
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="UCP_FEES_CURRENCY_UPDATE_ID_AND_SCHEMA_VERIFIED",
        detail="UCP itemized fees, top-level Order.currency, update checkout id omission, and multi-parent schema verified.",
        metadata={"order_currency": order_currency, "computed_fees": computed_fees},
    )


# ---------------------------------------------------------------------------
# Gate 3: MCP SEP-3004 Tamper-Evident Audit Hash-Chain, SEP-2243 -32020,
#         SEP-2664/2998 Streaming Tool Final Authority, Mcp-Param-* Schema
#         Gate (#3071) & Sierra tau2-bench NL_ASSERTION / Barge-In / LiveKit
# ---------------------------------------------------------------------------

def compute_audit_record_hash(prev_hash: str, canonical_payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}:{canonical_payload}".encode("utf-8")).hexdigest()


def evaluate_mcp_audit_chain_streaming_and_tau2_guard(
    *,
    audit_chain: tuple[dict[str, str], ...],
    header_mismatch_error_code: int,
    side_effect_triggered_on_partial_chunk: bool,
    final_call_tool_result_received: bool,
    mcp_param_header_sent: bool,
    input_schema_obtained: bool,
    reward_basis_includes_nl_assertion: bool,
    nl_assertion_evaluator_executed: bool,
    livekit_tick_blocking: bool,
    barge_in_agent_yielded_audio: bool,
) -> GuardEvaluation:
    """Enforce MCP #3004, #3005, #3000/#2998, #3071 and tau2-bench #226, #248, #221."""
    prev_hash = "0" * 64
    for idx, rec in enumerate(audit_chain):
        expected = compute_audit_record_hash(prev_hash, rec.get("canonical_payload", ""))
        if rec.get("prev_hash") != prev_hash or rec.get("record_hash") != expected:
            return GuardEvaluation(
                allowed=False,
                decision_code="MCP_SEP3004_AUDIT_HASH_CHAIN_TAMPERED",
                detail=f"Tamper-evident audit record #{idx} failed canonical SHA-256 hash-chain verification (#3004).",
                metadata={"index": idx, "expected_hash": expected, "actual_hash": rec.get("record_hash")},
            )
        prev_hash = expected

    if header_mismatch_error_code != -32020:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_SEP2243_HEADER_MISMATCH_CODE_DRIFT",
            detail=f"SEP-2243 HeaderMismatch must use error code -32020, got {header_mismatch_error_code} (#3005).",
            metadata={"header_mismatch_error_code": header_mismatch_error_code},
        )

    if side_effect_triggered_on_partial_chunk or not final_call_tool_result_received:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_STREAMING_PARTIAL_CHUNK_AUTHORITY_VIOLATION",
            detail="Streaming tool progress/partial_result chunks are non-authoritative; wait for final CallToolResult (#3000/#2998).",
            metadata={
                "side_effect_triggered_on_partial_chunk": side_effect_triggered_on_partial_chunk,
                "final_call_tool_result_received": final_call_tool_result_received,
            },
        )

    if mcp_param_header_sent and not input_schema_obtained:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PARAM_HEADER_WITHOUT_INPUT_SCHEMA_REJECTED",
            detail="Mcp-Param-* headers must not be constructed when tool inputSchema has not been obtained (#3071).",
            metadata={"mcp_param_header_sent": mcp_param_header_sent, "input_schema_obtained": input_schema_obtained},
        )

    if reward_basis_includes_nl_assertion and not nl_assertion_evaluator_executed:
        return GuardEvaluation(
            allowed=False,
            decision_code="TAU2_NL_ASSERTION_EVALUATOR_SKIPPED",
            detail="EvaluationType.ALL must execute NL_ASSERTION evaluator when present in task reward_basis (#226).",
            metadata={"reward_basis_includes_nl_assertion": reward_basis_includes_nl_assertion},
        )

    if livekit_tick_blocking or not barge_in_agent_yielded_audio:
        return GuardEvaluation(
            allowed=False,
            decision_code="TAU2_LIVEKIT_BLOCKING_OR_BARGE_IN_FAILURE",
            detail="LiveKit tick must be non-blocking via background queue (#248) and agent must yield on user barge-in (#221).",
            metadata={
                "livekit_tick_blocking": livekit_tick_blocking,
                "barge_in_agent_yielded_audio": barge_in_agent_yielded_audio,
            },
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_AUDIT_STREAMING_AND_TAU2_VERIFIED",
        detail="MCP SEP-3004 hash chain, SEP-2243 -32020, streaming CallToolResult authority, Mcp-Param-* schema gate, and tau2-bench verified.",
        metadata={"audit_records_verified": len(audit_chain), "tail_hash": prev_hash},
    )
