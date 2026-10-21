"""Stage 140: x402 MCP accepts Snapshot, Bare InvalidReason, PaymentResponse
Verification, SVM Transaction Version Negotiation & 2xx-Only Settlement Gate,
UCP Namespace Isolation, Price-on-Request, ready_for_complete, ACP Non-Bearer
Digital Entitlement & AP2 Withheld Disclosure / Independent checkout_hash /
Visa TAP Revocation Guardrails, and MCP stdio Boundary, Error Code Partition,
Stripe Pre-Tool Spend Policy & Sierra tau2-bench Flown-Segment Guardrails.

Covers primary-source PRs & Issues:
- x402-foundation/x402 #3503, #3507, #3502, #3499, #3496, #3495, #3494, #3482,
  #3481, #3486, #3480, #3478, #3474, #3473, #3475, #3471, #3466, #3459, #3457, #3477
- Universal-Commerce-Protocol/ucp #983, #973, #969, #967, #949, #957, #956
- agentic-commerce-protocol/agentic-commerce-protocol #293, #291, #286
- google-agentic-commerce/AP2 #376, #374, #372, #339, #331
- visa/trusted-agent-protocol #26, #25, #23
- modelcontextprotocol/modelcontextprotocol #2973, #2972, #2924, #2907
- stripe/ai #531, #487, #436, #82
- sierra-research/tau2-bench #163, #155, #142, #138, #39, #26
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    decision_code: str
    detail: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Gate 1: x402 MCP accepts Snapshot, Bare InvalidReason, PaymentResponse Check,
#         SVM Transaction Version Negotiation, 2xx Settlement Gate & Gas RPC
# ---------------------------------------------------------------------------

def evaluate_x402_mcp_accepts_snapshot_and_svm_version_guard(
    *,
    accepts_snapshotted_before_enricher: bool,
    enricher_mutated_baseline: bool,
    fastmcp_invalid_reason: str,
    payment_made: bool,
    payment_response_present: bool,
    logged_as_settled: bool,
    mcp_tool_timeout_sec: int,
    retry_request_headers: tuple[str, ...],
    svm_client_tx_version: int,
    facilitator_supported_tx_versions: tuple[int, ...],
    upstream_http_status: int,
    settlement_triggered: bool,
    gas_sponsoring_advertised: bool,
    client_has_rpc_url: bool,
    stellar_inclusion_fee_stroops: int,
) -> GuardEvaluation:
    """Enforce x402 #3496/#3495, #3494, #3499/#3482, #3481, #3478, #3474/#3473, #3471, #3459 & #3503."""
    if not accepts_snapshotted_before_enricher or enricher_mutated_baseline:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_MCP_ACCEPTS_BASELINE_MUTATED_BY_ENRICHER",
            detail="MCP 402 config.accepts must be snapshotted before scheme enrichers mutate extra in place (#3496/#3495).",
            metadata={
                "accepts_snapshotted_before_enricher": accepts_snapshotted_before_enricher,
                "enricher_mutated_baseline": enricher_mutated_baseline,
            },
        )

    if fastmcp_invalid_reason.startswith("Payment verification failed:"):
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_FASTMCP_PREFIXED_INVALID_REASON_REJECTED",
            detail="FastMCP 402 responses must expose bare InvalidReason codes for recovery matching (#3494).",
            metadata={"fastmcp_invalid_reason": fastmcp_invalid_reason},
        )

    if payment_made and not payment_response_present and logged_as_settled:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_MCP_SETTLED_LOGGED_WITHOUT_PAYMENT_RESPONSE",
            detail="Client must verify x402/payment-response before logging a paid tool call as settled (#3499/#3482).",
            metadata={"payment_made": payment_made, "payment_response_present": payment_response_present},
        )

    if mcp_tool_timeout_sec <= 0 or mcp_tool_timeout_sec > 600:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_MCP_TOOL_CALL_TIMEOUT_CAP_EXCEEDED",
            detail=f"MCP tool-call timeout ({mcp_tool_timeout_sec}s) exceeds 600s (10m) cap (#3481/#3486).",
            metadata={"mcp_tool_timeout_sec": mcp_tool_timeout_sec},
        )

    for h in retry_request_headers:
        if h.lower().startswith("access-control-"):
            return GuardEvaluation(
                allowed=False,
                decision_code="X402_CLIENT_RETRY_RESPONSE_ONLY_CORS_HEADER_LEAK",
                detail=f"Client retry request leaked response-only CORS header '{h}' (#3478).",
                metadata={"header": h},
            )

    if svm_client_tx_version not in facilitator_supported_tx_versions:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_SVM_TX_VERSION_NOT_ADVERTISED_BY_FACILITATOR",
            detail=f"SVM transaction version {svm_client_tx_version} not in extra.transactionVersions {facilitator_supported_tx_versions} (#3474/#3473).",
            metadata={
                "svm_client_tx_version": svm_client_tx_version,
                "facilitator_supported_tx_versions": facilitator_supported_tx_versions,
            },
        )

    if not (200 <= upstream_http_status < 300) and settlement_triggered:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_NON_2XX_RESPONSE_SETTLEMENT_BLOCKED",
            detail=f"Non-2xx HTTP response ({upstream_http_status}) must not trigger payment settlement (#3471).",
            metadata={"upstream_http_status": upstream_http_status},
        )

    if gas_sponsoring_advertised and not client_has_rpc_url:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_GAS_SPONSORING_CLIENT_MISSING_RPC_URL",
            detail="Gas sponsoring advertised in 402 body but client signer lacks rpcUrl to read chain state (#3459).",
            metadata={"gas_sponsoring_advertised": gas_sponsoring_advertised},
        )

    if stellar_inclusion_fee_stroops < 100:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_STELLAR_INCLUSION_FEE_BELOW_BASE_FEE",
            detail="Stellar facilitator inclusionFeeStroops must be >= 100 stroops BASE_FEE (#3503/#3507).",
            metadata={"stellar_inclusion_fee_stroops": stellar_inclusion_fee_stroops},
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="X402_MCP_SNAPSHOT_SVM_TX_VERSION_AND_2XX_GATE_VERIFIED",
        detail="x402 MCP accepts snapshot, bare InvalidReason, paymentResponse check, SVM tx version, and 2xx gate verified.",
        metadata={"svm_client_tx_version": svm_client_tx_version, "upstream_http_status": upstream_http_status},
    )


# ---------------------------------------------------------------------------
# Gate 2: UCP Namespace Isolation (#983), Price-on-Request (#969),
#         ready_for_complete (#949), ACP Digital Bearer / PO Approval (#293/#291),
#         AP2 Withheld Disclosure / Independent checkout_hash (#339/#331/#376/#372)
#         & Visa TAP Revocation Standing (#26/#25)
# ---------------------------------------------------------------------------

def evaluate_ucp_acp_ap2_and_tap_temporal_authority_guard(
    *,
    third_party_extension_key: str,
    catalog_variant_requires_quote: bool,
    catalog_variant_selling_price_minor: int | None,
    catalog_pricing_state: str,
    checkout_status_before_complete: str,
    digital_entitlement_audience_bound: bool,
    is_purchase_order_payment: bool,
    po_account_owner_approved: bool,
    ap2_withheld_Constraint_disclosures: int,
    ap2_caller_supplied_expected_checkout_hash: bool,
    ap2_recurrence_within_execution_window: bool,
    ap2_cnf_jwk_use_is_string: bool,
    tap_originating_agent_revoked: bool,
    tap_action_attestation_verified: bool,
) -> GuardEvaluation:
    """Enforce UCP #983/#969/#949, ACP #293/#291, AP2 #339/#331/#376/#372 & Visa TAP #26/#25."""
    if "." not in third_party_extension_key or third_party_extension_key.startswith("dev.ucp."):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_THIRD_PARTY_EXTENSION_NAMESPACE_VIOLATION",
            detail="Third-party entity extensions must be isolated under reverse-DNS vendor namespace (#983).",
            metadata={"third_party_extension_key": third_party_extension_key},
        )

    if catalog_variant_requires_quote and (
        catalog_variant_selling_price_minor == 0 or catalog_pricing_state != "price_on_request"
    ):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_PRICE_ON_REQUEST_FAKE_ZERO_PRICE_REJECTED",
            detail="Quote-required catalog variants must use explicit price_on_request state, not a fake 0 price (#969).",
            metadata={
                "catalog_variant_selling_price_minor": catalog_variant_selling_price_minor,
                "catalog_pricing_state": catalog_pricing_state,
            },
        )

    if checkout_status_before_complete != "ready_for_complete":
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_COMPLETE_CHECKOUT_REQUIRES_READY_STATUS",
            detail=f"Complete Checkout requires status 'ready_for_complete', got '{checkout_status_before_complete}' (#949).",
            metadata={"checkout_status_before_complete": checkout_status_before_complete},
        )

    if not digital_entitlement_audience_bound:
        return GuardEvaluation(
            allowed=False,
            decision_code="ACP_TRANSFERABLE_BEARER_DIGITAL_ENTITLEMENT_BLOCKED",
            detail="Digital fulfillment access_url/license_key must be bound to buyer/account/audience (#293).",
            metadata={"digital_entitlement_audience_bound": digital_entitlement_audience_bound},
        )

    if is_purchase_order_payment and not po_account_owner_approved:
        return GuardEvaluation(
            allowed=False,
            decision_code="ACP_PURCHASE_ORDER_MISSING_ACCOUNT_OWNER_APPROVAL",
            detail="Purchase-order PaymentData requires explicit account-owner approval before order placement (#291).",
            metadata={"is_purchase_order_payment": is_purchase_order_payment},
        )

    if ap2_withheld_Constraint_disclosures > 0:
        return GuardEvaluation(
            allowed=False,
            decision_code="AP2_WITHHELD_CONSTRAINT_DISCLOSURE_FAIL_CLOSED",
            detail="Withheld SD-JWT constraint disclosures (budget.max / acceptable_items) must fail closed (#339).",
            metadata={"ap2_withheld_Constraint_disclosures": ap2_withheld_Constraint_disclosures},
        )

    if not ap2_caller_supplied_expected_checkout_hash:
        return GuardEvaluation(
            allowed=False,
            decision_code="AP2_MISSING_INDEPENDENT_EXPECTED_CHECKOUT_HASH",
            detail="CheckoutMandateChain.verify() requires caller-supplied expected_checkout_hash context (#331).",
            metadata={"ap2_caller_supplied_expected_checkout_hash": ap2_caller_supplied_expected_checkout_hash},
        )

    if not ap2_recurrence_within_execution_window or not ap2_cnf_jwk_use_is_string:
        return GuardEvaluation(
            allowed=False,
            decision_code="AP2_RECURRENCE_WINDOW_OR_CNF_JWK_USE_INVALID",
            detail="AP2 agent_recurrence execution window (#376) and string cnf.jwk['use'] (#372) must be valid.",
            metadata={
                "ap2_recurrence_within_execution_window": ap2_recurrence_within_execution_window,
                "ap2_cnf_jwk_use_is_string": ap2_cnf_jwk_use_is_string,
            },
        )

    if tap_originating_agent_revoked or not tap_action_attestation_verified:
        return GuardEvaluation(
            allowed=False,
            decision_code="VISA_TAP_REVOKED_AGENT_OR_MISSING_ACTION_ATTESTATION",
            detail="Visa TAP rejects instructions from revoked agents (#26) or lacking pre-pay ACTION attestation (#25).",
            metadata={
                "tap_originating_agent_revoked": tap_originating_agent_revoked,
                "tap_action_attestation_verified": tap_action_attestation_verified,
            },
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="UCP_ACP_AP2_AND_TAP_TEMPORAL_AUTHORITY_VERIFIED",
        detail="UCP namespace/price-on-request/ready_for_complete, ACP digital/PO, AP2 fail-closed disclosures, and Visa TAP verified.",
        metadata={"third_party_extension_key": third_party_extension_key},
    )


# ---------------------------------------------------------------------------
# Gate 3: MCP stdio Trust Boundary (#2973), Mcp-Param-* ttlMs: 0 Decoupling
#         (#2972), Post-Approval Drift (#2924), Stripe Pre-Tool Spend Policy
#         (#531/#82) & Sierra tau2-bench Already-Flown Flight Guard (#26/#39/#138/#155)
# ---------------------------------------------------------------------------

def evaluate_mcp_stdio_stripe_policy_and_tau2_flown_flight_guard(
    *,
    is_stdio_transport: bool,
    stdio_peer_sandboxed_or_trusted: bool,
    input_schema_present: bool,
    schema_ttl_ms: int,
    mcp_param_header_emitted: bool,
    post_approval_tool_schema_drifted: bool,
    stripe_pre_tool_spend_policy_checked: bool,
    stripe_checkout_unintended_customer_assigned: bool,
    airline_flight_segment_already_flown: bool,
    agent_modified_or_cancelled_flown_flight: bool,
    reward_basis_contains_action: bool,
    leaderboard_submission_has_email_and_prompt_flag: bool,
) -> GuardEvaluation:
    """Enforce MCP #2973/#2972/#2924, Stripe #531/#82, and tau2-bench #26/#39/#138/#155."""
    if is_stdio_transport and not stdio_peer_sandboxed_or_trusted:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_STDIO_UNTRUSTED_PEER_EQUIVALENT_PRIVILEGE_BLOCKED",
            detail="stdio MCP peers execute with host user privileges and must be sandboxed or trusted (#2973).",
            metadata={"is_stdio_transport": is_stdio_transport},
        )

    if mcp_param_header_emitted and not input_schema_present:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PARAM_HEADER_WITHOUT_SCHEMA_BLOCKED",
            detail="Mcp-Param-* header emission requires obtained inputSchema regardless of ttlMs (#2972).",
            metadata={"schema_ttl_ms": schema_ttl_ms},
        )

    if post_approval_tool_schema_drifted:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_POST_APPROVAL_TOOL_DEFINITION_DRIFT_RUG_PULL",
            detail="Server mutated tool definition after session admission approval (rug-pull corpus, #2924).",
            metadata={"post_approval_tool_schema_drifted": post_approval_tool_schema_drifted},
        )

    if not stripe_pre_tool_spend_policy_checked or stripe_checkout_unintended_customer_assigned:
        return GuardEvaluation(
            allowed=False,
            decision_code="STRIPE_MCP_SPEND_POLICY_OR_CUSTOMER_ASSIGNMENT_VIOLATION",
            detail="Stripe MCP calls require pre-tool spend policy check (#531) and block unintended customer assignment (#82).",
            metadata={
                "stripe_pre_tool_spend_policy_checked": stripe_pre_tool_spend_policy_checked,
                "stripe_checkout_unintended_customer_assigned": stripe_checkout_unintended_customer_assigned,
            },
        )

    if airline_flight_segment_already_flown and agent_modified_or_cancelled_flown_flight:
        return GuardEvaluation(
            allowed=False,
            decision_code="TAU2_AIRLINE_ALREADY_FLOWN_SEGMENT_MODIFICATION_BLOCKED",
            detail="Agent cannot cancel or modify a reservation when any portion of the flight has already been flown (#26).",
            metadata={"airline_flight_segment_already_flown": airline_flight_segment_already_flown},
        )

    if not reward_basis_contains_action or not leaderboard_submission_has_email_and_prompt_flag:
        return GuardEvaluation(
            allowed=False,
            decision_code="TAU2_DEFAULT_ACTION_REWARD_OR_SUBMISSION_SCHEMA_INVALID",
            detail="tau2-bench requires RewardType.ACTION in default reward_basis (#138) and validated submission fields (#155).",
            metadata={
                "reward_basis_contains_action": reward_basis_contains_action,
                "leaderboard_submission_has_email_and_prompt_flag": leaderboard_submission_has_email_and_prompt_flag,
            },
        )

    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_STDIO_STRIPE_POLICY_AND_TAU2_FLOWN_FLIGHT_VERIFIED",
        detail="MCP stdio boundary, ttlMs: 0 Mcp-Param-* decoupling, Stripe spend policy, and tau2 flown-flight rules verified.",
        metadata={"schema_ttl_ms": schema_ttl_ms},
    )
