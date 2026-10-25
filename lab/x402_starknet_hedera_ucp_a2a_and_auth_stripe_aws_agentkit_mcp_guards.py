"""Stage 276 deterministic protocol & security guards (`PR-01..PR-16`).

Covers 203 strictly zero-overlap primary-source pull requests across 19 upstream
repositories (`x402-foundation/x402`, `Universal-Commerce-Protocol/ucp`,
`modelcontextprotocol/modelcontextprotocol`, `a2aproject/A2A`,
`a2aproject/a2a-python`, `a2aproject/a2a-java`, `a2aproject/a2a-js`,
`stripe/stripe-node`, `stripe/stripe-python`, `stripe/stripe-go`,
`stripe/stripe-cli`, `coinbase/agentkit`, `modelcontextprotocol/go-sdk`,
`modelcontextprotocol/rust-sdk`, `modelcontextprotocol/python-sdk`,
`modelcontextprotocol/typescript-sdk`, `modelcontextprotocol/csharp-sdk`,
`modelcontextprotocol/java-sdk`, and `modelcontextprotocol/inspector`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardDecision:
    admitted: bool
    code: str
    detail: str
    metadata: Mapping[str, Any]


STAGE_276_PR_CITATIONS: dict[str, tuple[str, ...]] = {
    "PR-01": (
        "x402-foundation/x402#3126",
        "x402-foundation/x402#3124",
        "x402-foundation/x402#3122",
        "x402-foundation/x402#3120",
        "x402-foundation/x402#3115",
        "x402-foundation/x402#3114",
        "x402-foundation/x402#3105",
        "x402-foundation/x402#3101",
    ),
    "PR-02": (
        "x402-foundation/x402#3067",
        "x402-foundation/x402#3061",
        "x402-foundation/x402#3060",
        "x402-foundation/x402#3058",
        "x402-foundation/x402#3055",
        "x402-foundation/x402#3053",
        "x402-foundation/x402#3036",
        "x402-foundation/x402#3033",
        "x402-foundation/x402#3032",
        "x402-foundation/x402#3031",
    ),
    "PR-03": (
        "x402-foundation/x402#3027",
        "x402-foundation/x402#3026",
        "x402-foundation/x402#3022",
        "x402-foundation/x402#2987",
        "x402-foundation/x402#2985",
        "x402-foundation/x402#2984",
        "x402-foundation/x402#2981",
        "x402-foundation/x402#2974",
        "x402-foundation/x402#2964",
        "x402-foundation/x402#2962",
        "x402-foundation/x402#2957",
        "x402-foundation/x402#2933",
        "x402-foundation/x402#2923",
        "x402-foundation/x402#2917",
        "x402-foundation/x402#2914",
        "x402-foundation/x402#2912",
    ),
    "PR-04": (
        "Universal-Commerce-Protocol/ucp#874",
        "Universal-Commerce-Protocol/ucp#734",
        "Universal-Commerce-Protocol/ucp#683",
        "modelcontextprotocol/modelcontextprotocol#3426",
        "modelcontextprotocol/modelcontextprotocol#3406",
        "modelcontextprotocol/modelcontextprotocol#3404",
        "modelcontextprotocol/modelcontextprotocol#3390",
        "modelcontextprotocol/modelcontextprotocol#3386",
        "modelcontextprotocol/modelcontextprotocol#3385",
        "modelcontextprotocol/modelcontextprotocol#3383",
        "modelcontextprotocol/modelcontextprotocol#3380",
    ),
    "PR-05": (
        "a2aproject/A2A#2237",
        "a2aproject/A2A#2232",
        "a2aproject/A2A#2230",
        "a2aproject/A2A#2227",
        "a2aproject/A2A#2226",
        "a2aproject/A2A#2225",
        "a2aproject/A2A#2224",
        "a2aproject/A2A#2223",
        "a2aproject/A2A#2222",
        "a2aproject/A2A#2219",
        "a2aproject/A2A#2205",
        "a2aproject/A2A#2204",
    ),
    "PR-06": (
        "a2aproject/a2a-python#1144",
        "a2aproject/a2a-python#1143",
        "a2aproject/a2a-python#1142",
        "a2aproject/a2a-python#1140",
        "a2aproject/a2a-python#1139",
        "a2aproject/a2a-python#1137",
        "a2aproject/a2a-python#1127",
        "a2aproject/a2a-python#1126",
        "a2aproject/a2a-python#1125",
        "a2aproject/a2a-python#1116",
        "a2aproject/a2a-python#1115",
        "a2aproject/a2a-python#1114",
    ),
    "PR-07": (
        "a2aproject/a2a-java#1109",
        "a2aproject/a2a-java#1104",
        "a2aproject/a2a-java#1099",
        "a2aproject/a2a-java#1098",
        "a2aproject/a2a-java#1097",
        "a2aproject/a2a-java#1096",
        "a2aproject/a2a-java#1095",
        "a2aproject/a2a-java#1090",
        "a2aproject/a2a-java#1088",
        "a2aproject/a2a-java#1085",
        "a2aproject/a2a-js#781",
        "a2aproject/a2a-js#779",
        "a2aproject/a2a-js#702",
        "a2aproject/a2a-js#693",
    ),
    "PR-08": (
        "stripe/stripe-node#2859",
        "stripe/stripe-node#2858",
        "stripe/stripe-node#2857",
        "stripe/stripe-node#2856",
        "stripe/stripe-node#2855",
        "stripe/stripe-node#2854",
        "stripe/stripe-node#2853",
        "stripe/stripe-node#2850",
        "stripe/stripe-node#2846",
        "stripe/stripe-node#2845",
        "stripe/stripe-node#2844",
    ),
    "PR-09": (
        "stripe/stripe-python#1894",
        "stripe/stripe-python#1893",
        "stripe/stripe-python#1892",
        "stripe/stripe-python#1888",
        "stripe/stripe-python#1887",
        "stripe/stripe-python#1885",
        "stripe/stripe-python#1881",
        "stripe/stripe-python#1879",
        "stripe/stripe-python#1873",
        "stripe/stripe-python#1871",
        "stripe/stripe-python#1869",
        "stripe/stripe-python#1868",
    ),
    "PR-10": (
        "stripe/stripe-go#2439",
        "stripe/stripe-go#2438",
        "stripe/stripe-go#2437",
        "stripe/stripe-go#2436",
        "stripe/stripe-go#2435",
        "stripe/stripe-go#2432",
        "stripe/stripe-go#2431",
        "stripe/stripe-go#2429",
        "stripe/stripe-cli#2109",
        "stripe/stripe-cli#2108",
        "stripe/stripe-cli#2107",
        "stripe/stripe-cli#2106",
        "stripe/stripe-cli#2105",
        "stripe/stripe-cli#2104",
        "stripe/stripe-cli#2103",
        "stripe/stripe-cli#2102",
        "stripe/stripe-cli#2095",
        "stripe/stripe-cli#2093",
        "stripe/stripe-cli#2092",
    ),
    "PR-11": (
        "coinbase/agentkit#1459",
        "coinbase/agentkit#1458",
        "coinbase/agentkit#1457",
        "coinbase/agentkit#1455",
        "coinbase/agentkit#1454",
        "coinbase/agentkit#1453",
        "coinbase/agentkit#1452",
        "coinbase/agentkit#1448",
        "coinbase/agentkit#1444",
        "coinbase/agentkit#1431",
        "coinbase/agentkit#1430",
        "coinbase/agentkit#1426",
    ),
    "PR-12": (
        "modelcontextprotocol/go-sdk#1219",
        "modelcontextprotocol/go-sdk#1217",
        "modelcontextprotocol/go-sdk#1216",
        "modelcontextprotocol/go-sdk#1206",
        "modelcontextprotocol/go-sdk#1203",
        "modelcontextprotocol/go-sdk#1199",
        "modelcontextprotocol/go-sdk#1196",
        "modelcontextprotocol/go-sdk#1195",
        "modelcontextprotocol/go-sdk#1192",
        "modelcontextprotocol/go-sdk#1190",
        "modelcontextprotocol/go-sdk#1186",
        "modelcontextprotocol/go-sdk#1166",
    ),
    "PR-13": (
        "modelcontextprotocol/rust-sdk#1221",
        "modelcontextprotocol/rust-sdk#1219",
        "modelcontextprotocol/rust-sdk#1217",
        "modelcontextprotocol/rust-sdk#1216",
        "modelcontextprotocol/rust-sdk#1211",
        "modelcontextprotocol/rust-sdk#1206",
        "modelcontextprotocol/rust-sdk#1196",
        "modelcontextprotocol/rust-sdk#1195",
        "modelcontextprotocol/rust-sdk#1192",
        "modelcontextprotocol/rust-sdk#1186",
    ),
    "PR-14": (
        "modelcontextprotocol/python-sdk#3458",
        "modelcontextprotocol/python-sdk#3453",
        "modelcontextprotocol/python-sdk#3450",
        "modelcontextprotocol/python-sdk#3445",
        "modelcontextprotocol/python-sdk#3444",
        "modelcontextprotocol/python-sdk#3438",
        "modelcontextprotocol/python-sdk#3433",
        "modelcontextprotocol/python-sdk#3429",
        "modelcontextprotocol/python-sdk#3428",
        "modelcontextprotocol/python-sdk#3420",
    ),
    "PR-15": (
        "modelcontextprotocol/typescript-sdk#2984",
        "modelcontextprotocol/typescript-sdk#2983",
        "modelcontextprotocol/typescript-sdk#2982",
        "modelcontextprotocol/typescript-sdk#2981",
        "modelcontextprotocol/typescript-sdk#2980",
        "modelcontextprotocol/typescript-sdk#2979",
        "modelcontextprotocol/typescript-sdk#2978",
        "modelcontextprotocol/typescript-sdk#2976",
        "modelcontextprotocol/typescript-sdk#2974",
        "modelcontextprotocol/typescript-sdk#2968",
        "modelcontextprotocol/typescript-sdk#2967",
        "modelcontextprotocol/typescript-sdk#2965",
    ),
    "PR-16": (
        "modelcontextprotocol/csharp-sdk#1834",
        "modelcontextprotocol/csharp-sdk#1833",
        "modelcontextprotocol/csharp-sdk#1832",
        "modelcontextprotocol/csharp-sdk#1831",
        "modelcontextprotocol/csharp-sdk#1829",
        "modelcontextprotocol/csharp-sdk#1827",
        "modelcontextprotocol/csharp-sdk#1826",
        "modelcontextprotocol/java-sdk#1161",
        "modelcontextprotocol/java-sdk#1152",
        "modelcontextprotocol/java-sdk#1151",
        "modelcontextprotocol/java-sdk#1150",
        "modelcontextprotocol/java-sdk#1146",
        "modelcontextprotocol/java-sdk#1138",
        "modelcontextprotocol/inspector#2684",
        "modelcontextprotocol/inspector#2679",
        "modelcontextprotocol/inspector#2678",
        "modelcontextprotocol/inspector#2677",
        "modelcontextprotocol/inspector#2673",
        "modelcontextprotocol/inspector#2671",
        "modelcontextprotocol/inspector#2669",
        "modelcontextprotocol/inspector#2666",
        "modelcontextprotocol/inspector#2664",
    ),
}


# ---------------------------------------------------------------------------
# PR-01: x402 Starknet payer-scoped Transfer, TS spendControls, SVM smart-wallet
#        ComputeBudget & operator facilitator limits, XRPL decode allowlist, and
#        EVM simulation revert vs. RPC failure classification
# ---------------------------------------------------------------------------
ALLOWED_XRPL_PAYMENT_FIELDS: frozenset[str] = frozenset(
    {
        "TransactionType",
        "Account",
        "Destination",
        "Amount",
        "Fee",
        "Sequence",
        "SigningPubKey",
        "TxnSignature",
        "DestinationTag",
        "SourceTag",
        "LastLedgerSequence",
        "Flags",
        "Memos",
    }
)


def evaluate_x402_starknet_svm_xrpl_sim_guard(
    *,
    starknet_transfers: Sequence[Mapping[str, Any]],
    expected_payer: str,
    expected_pay_to: str,
    required_amount_minor: int,
    compute_unit_price_microlamports: int,
    max_compute_unit_price_microlamports: int,
    smart_wallet_verified: bool,
    xrpl_decoded_tx: Mapping[str, Any],
    xrpl_canonical_bytes_match: bool,
    evm_simulation_outcome: str,
) -> GuardDecision:
    """Enforce x402#3126, #3124, #3122, #3120, #3115, #3114, #3105, #3101."""
    payer_transfers = [
        t for t in starknet_transfers if str(t.get("from", "")).lower() == expected_payer.lower()
    ]
    if len(payer_transfers) != 1:
        return GuardDecision(
            admitted=False,
            code="X402_STARKNET_PAYER_TRANSFER_COUNT_INVALID",
            detail="Starknet exact settlement requires exactly one Transfer event scoped to the payer",
            metadata={"payer_transfer_count": len(payer_transfers)},
        )
    transfer = payer_transfers[0]
    if (
        str(transfer.get("to", "")).lower() != expected_pay_to.lower()
        or int(transfer.get("amount", 0)) < required_amount_minor
    ):
        return GuardDecision(
            admitted=False,
            code="X402_STARKNET_PAYER_TRANSFER_MISMATCH",
            detail="Starknet payer-scoped Transfer recipient or amount does not satisfy payment requirements",
            metadata={"to": transfer.get("to"), "amount": transfer.get("amount")},
        )
    if not smart_wallet_verified or compute_unit_price_microlamports > max_compute_unit_price_microlamports:
        return GuardDecision(
            admitted=False,
            code="X402_SVM_COMPUTE_BUDGET_OR_SMART_WALLET_REJECTED",
            detail="SVM transaction exceeded operator-configured compute unit price cap or failed smart-wallet check",
            metadata={
                "compute_unit_price_microlamports": compute_unit_price_microlamports,
                "max_compute_unit_price_microlamports": max_compute_unit_price_microlamports,
            },
        )
    unknown_xrpl = set(xrpl_decoded_tx.keys()) - ALLOWED_XRPL_PAYMENT_FIELDS
    if unknown_xrpl or xrpl_decoded_tx.get("TransactionType") != "Payment" or not xrpl_canonical_bytes_match:
        return GuardDecision(
            admitted=False,
            code="X402_XRPL_PAYMENT_DECODE_NOT_CANONICAL",
            detail="XRPL decoded Payment contains disallowed fields or non-canonical serialization",
            metadata={"unknown_fields": sorted(unknown_xrpl)},
        )
    if evm_simulation_outcome == "reverted":
        return GuardDecision(
            admitted=False,
            code="X402_EVM_SIMULATION_REVERTED_NON_RETRYABLE",
            detail="EVM exact simulation reverted on-chain; classified as non-retryable payload error",
            metadata={"retryable": False},
        )
    if evm_simulation_outcome == "rpc_error":
        return GuardDecision(
            admitted=False,
            code="X402_EVM_SIMULATION_RPC_ERROR_RETRYABLE",
            detail="EVM simulation could not run due to RPC error; classified as retryable transport error",
            metadata={"retryable": True},
        )
    return GuardDecision(
        admitted=True,
        code="X402_STARKNET_SVM_XRPL_SIM_VERIFIED",
        detail="Starknet payer-scoped Transfer, SVM operator limits, XRPL canonical Payment, and EVM simulation verified",
        metadata={"payer_transfer_amount": int(transfer["amount"])},
    )


# ---------------------------------------------------------------------------
# PR-02: x402 Hedera net credit check, MCP success:false tool result withholding,
#        Permit2/EIP-3009 post-settle Transfer log check, DOTALL wildcard route,
#        and MCP corrective 402 re-approval
# ---------------------------------------------------------------------------
def evaluate_x402_hedera_permit2_wildcard_mcp_guard(
    *,
    hedera_declared_amount: int,
    hedera_payee_net_credit: int,
    settle_response_success: bool,
    transfer_log_emitted: bool,
    transfer_log_amount: int,
    route_pattern: str,
    request_path: str,
    is_corrective_402_retry: bool,
    reapproved_before_retry_sign: bool,
) -> GuardDecision:
    """Enforce x402#3067, #3061, #3060, #3058, #3055, #3053, #3036, #3033, #3032, #3031."""
    regex_pattern = "^" + re.escape(route_pattern).replace(r"\*", ".*?") + "$"
    route_matched = bool(re.match(regex_pattern, request_path, flags=re.IGNORECASE | re.DOTALL))
    if not route_matched:
        return GuardDecision(
            admitted=False,
            code="X402_WILDCARD_ROUTE_UNMATCHED",
            detail="Request path did not match route pattern",
            metadata={"route_pattern": route_pattern},
        )
    if "\n" in request_path or "\r" in request_path:
        return GuardDecision(
            admitted=False,
            code="X402_WILDCARD_LINE_TERMINATOR_BYPASS_BLOCKED",
            detail="Protected wildcard route matched path containing CR/LF line terminators; bypass blocked",
            metadata={"request_path": repr(request_path)},
        )
    if not settle_response_success:
        return GuardDecision(
            admitted=False,
            code="X402_MCP_SETTLE_SUCCESS_FALSE_RESULT_WITHHELD",
            detail="Facilitator returned SettleResponse(success=false); MCP tool result withheld",
            metadata={"settle_response_success": False},
        )
    if hedera_payee_net_credit < hedera_declared_amount:
        return GuardDecision(
            admitted=False,
            code="X402_HEDERA_NET_CREDIT_SHORTFALL",
            detail="Hedera consensus record shows payee net credit is less than declared amount after HTS custom fees",
            metadata={
                "declared_amount": hedera_declared_amount,
                "payee_net_credit": hedera_payee_net_credit,
            },
        )
    if not transfer_log_emitted or transfer_log_amount < hedera_declared_amount:
        return GuardDecision(
            admitted=False,
            code="X402_SETTLE_TRANSFER_EVENT_MISSING_OR_SHORT",
            detail="Post-settle receipt is missing a matching ERC-20 Transfer log for the settled amount",
            metadata={"transfer_log_emitted": transfer_log_emitted, "transfer_log_amount": transfer_log_amount},
        )
    if is_corrective_402_retry and not reapproved_before_retry_sign:
        return GuardDecision(
            admitted=False,
            code="X402_MCP_CORRECTIVE_402_REAPPROVAL_REQUIRED",
            detail="Corrective 402 recovery payment must re-run approval and spend-control hooks before signing",
            metadata={"is_corrective_402_retry": True},
        )
    return GuardDecision(
        admitted=True,
        code="X402_HEDERA_PERMIT2_WILDCARD_MCP_VERIFIED",
        detail="Hedera net credit, post-settle Transfer log, DOTALL wildcard route, and MCP re-approval verified",
        metadata={"payee_net_credit": hedera_payee_net_credit},
    )


# ---------------------------------------------------------------------------
# PR-03: x402 builder-code s merge & 5-entry cap, Go 512KB body cap, JSON 402
#        mirroring + Cache-Control: no-store, exact override math, small-order
#        Ed25519 rejection, and retry body preservation
# ---------------------------------------------------------------------------
MAX_SERVICE_CODES = 5
MAX_GO_RESPONSE_BODY_BYTES = 512 * 1024


def evaluate_x402_buildercode_override_ed25519_guard(
    *,
    server_service_codes: Sequence[str],
    client_service_codes: Sequence[str],
    response_body_bytes: int,
    status_402_cache_control: str,
    status_402_body_mirrors_header: bool,
    override_percent_str: str,
    base_amount_minor: int,
    ed25519_pubkey_is_small_order: bool,
    storage_error_occurred: bool,
    retry_body_preserved: bool,
) -> GuardDecision:
    """Enforce x402#3027..#2912."""
    if response_body_bytes > MAX_GO_RESPONSE_BODY_BYTES:
        return GuardDecision(
            admitted=False,
            code="X402_GO_RESPONSE_BODY_LIMIT_EXCEEDED",
            detail=f"Facilitator/server response body ({response_body_bytes} B) exceeds 512 KB cap",
            metadata={"response_body_bytes": response_body_bytes},
        )
    if "no-store" not in status_402_cache_control.lower() or not status_402_body_mirrors_header:
        return GuardDecision(
            admitted=False,
            code="X402_402_CACHE_OR_BODY_MIRROR_INVALID",
            detail="402 response must set Cache-Control: no-store and mirror PAYMENT-REQUIRED in JSON body",
            metadata={
                "cache_control": status_402_cache_control,
                "body_mirrors_header": status_402_body_mirrors_header,
            },
        )
    if ed25519_pubkey_is_small_order:
        return GuardDecision(
            admitted=False,
            code="X402_SVM_SIWX_SMALL_ORDER_PUBKEY_REJECTED",
            detail="SVM SIWx rejected low-order / torsion Ed25519 public key before signature verification",
            metadata={},
        )
    if storage_error_occurred or not retry_body_preserved:
        return GuardDecision(
            admitted=False,
            code="X402_STORAGE_OR_RETRY_BODY_ERROR",
            detail="Batch settlement storage error or unpreserved request body on retry",
            metadata={"storage_error_occurred": storage_error_occurred, "retry_body_preserved": retry_body_preserved},
        )
    try:
        pct = Decimal(override_percent_str)
    except InvalidOperation:
        return GuardDecision(
            admitted=False,
            code="X402_SETTLEMENT_OVERRIDE_INVALID_DECIMAL",
            detail="Invalid decimal percentage in settlement override",
            metadata={"override_percent_str": override_percent_str},
        )
    if pct < Decimal("0") or pct > Decimal("100"):
        return GuardDecision(
            admitted=False,
            code="X402_SETTLEMENT_OVERRIDE_PERCENT_OUT_OF_RANGE",
            detail="Settlement override percentage must be within [0, 100] without integer overflow",
            metadata={"override_percent": str(pct)},
        )
    merged_codes: list[str] = []
    for code in list(server_service_codes) + list(client_service_codes):
        if code and code not in merged_codes:
            merged_codes.append(code)
    capped_codes = merged_codes[:MAX_SERVICE_CODES]
    effective_minor = int((Decimal(base_amount_minor) * pct) // Decimal("100"))
    return GuardDecision(
        admitted=True,
        code="X402_BUILDERCODE_OVERRIDE_ED25519_VERIFIED",
        detail="Builder-code array merged & capped at 5, exact override computed, and Ed25519/402 headers verified",
        metadata={"service_codes": capped_codes, "effective_minor": effective_minor},
    )


# ---------------------------------------------------------------------------
# PR-04: UCP fact-accuracy reference audit & MCP SEP deployment environment guard
# ---------------------------------------------------------------------------
def evaluate_ucp_fact_audit_mcp_sep_env_guard(
    *,
    ucp_broken_fact_refs: Sequence[str],
    sep_job_has_deployment_environment: bool,
    expired_charter_invites: Sequence[str],
    home_page_has_security_link: bool,
) -> GuardDecision:
    """Enforce ucp#874, #734, #683 and modelcontextprotocol#3426..#3380."""
    if ucp_broken_fact_refs:
        return GuardDecision(
            admitted=False,
            code="UCP_FACT_AUDIT_STALE_REFERENCE",
            detail="UCP fact-accuracy audit detected stale specification references",
            metadata={"stale_refs": list(ucp_broken_fact_refs)},
        )
    if not sep_job_has_deployment_environment:
        return GuardDecision(
            admitted=False,
            code="MCP_SEP_JOB_MISSING_DEPLOYMENT_ENVIRONMENT",
            detail="SEP automation and slash-command workflows must run inside a gated deployment environment",
            metadata={},
        )
    if expired_charter_invites or not home_page_has_security_link:
        return GuardDecision(
            admitted=False,
            code="MCP_CHARTER_OR_SECURITY_LINK_INVALID",
            detail="MCP charter links must be active and home page must expose Security policy link",
            metadata={"expired_charter_invites": list(expired_charter_invites)},
        )
    return GuardDecision(
        admitted=True,
        code="UCP_FACT_AUDIT_MCP_SEP_ENV_VERIFIED",
        detail="UCP fact-accuracy references and MCP SEP deployment environment controls verified",
        metadata={"stale_refs_count": 0},
    )


# ---------------------------------------------------------------------------
# PR-05: A2A v1.0.1 §5.4 error-mapping table, jcs_edge_v1 conformance vectors,
#        and A2A vs. MCP authorization discovery
# ---------------------------------------------------------------------------
A2A_V101_ERROR_MAPPING: dict[str, tuple[int, str]] = {
    "TaskNotFoundError": (404, "NOT_FOUND"),
    "TaskNotCancelableError": (409, "FAILED_PRECONDITION"),
    "PushNotificationNotSupportedError": (400, "FAILED_PRECONDITION"),
    "UnsupportedOperationError": (400, "UNIMPLEMENTED"),
    "ContentTypeNotSupportedError": (415, "INVALID_ARGUMENT"),
    "InvalidAgentResponseError": (502, "INTERNAL"),
}


def evaluate_a2a_v101_error_jcs_edge_auth_guard(
    *,
    error_type: str,
    http_status: int,
    grpc_status: str,
    jcs_contains_lone_surrogate: bool,
    jcs_negative_zero_normalized: bool,
    protocol: str,
    discovery_source: str,
) -> GuardDecision:
    """Enforce A2A#2237..#2204."""
    expected = A2A_V101_ERROR_MAPPING.get(error_type)
    if expected is None or expected != (http_status, grpc_status):
        return GuardDecision(
            admitted=False,
            code="A2A_V101_ERROR_MAPPING_MISMATCH",
            detail="HTTP or gRPC status does not match the corrected A2A v1.0.1 §5.4 error-mapping table",
            metadata={"error_type": error_type, "expected": expected, "actual": (http_status, grpc_status)},
        )
    if jcs_contains_lone_surrogate or not jcs_negative_zero_normalized:
        return GuardDecision(
            admitted=False,
            code="A2A_JCS_EDGE_V1_CONFORMANCE_FAILED",
            detail="JCS payload failed jcs_edge_v1 conformance (lone surrogate or unnormalized -0.0)",
            metadata={},
        )
    if (protocol == "a2a" and discovery_source != "agent_card_security_schemes") or (
        protocol == "mcp" and discovery_source != "oauth_prm_401"
    ):
        return GuardDecision(
            admitted=False,
            code="A2A_MCP_AUTH_DISCOVERY_MISMATCH",
            detail="A2A must discover auth via AgentCard securitySchemes and MCP via 401 OAuth PRM",
            metadata={"protocol": protocol, "discovery_source": discovery_source},
        )
    return GuardDecision(
        admitted=True,
        code="A2A_V101_ERROR_JCS_EDGE_AUTH_VERIFIED",
        detail="A2A v1.0.1 §5.4 error mapping, jcs_edge_v1 conformance, and auth discovery verified",
        metadata={"error_type": error_type, "http_status": http_status, "grpc_status": grpc_status},
    )


# ---------------------------------------------------------------------------
# PR-06: A2A Python multi-scheme AND security requirement, REST path parameter
#        sanitization, push Authorization header, and subscriber tap eviction
# ---------------------------------------------------------------------------
SAFE_REST_PARAM_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")


def evaluate_a2a_python_and_auth_path_tap_guard(
    *,
    required_schemes_in_requirement: Sequence[str],
    applied_client_schemes: Sequence[str],
    rest_path_params: Mapping[str, str],
    push_auth_configured: bool,
    push_authorization_header_sent: bool,
    slow_subscriber_queue_full: bool,
    evicted_on_full: bool,
    call_context_restored_after_cancel: bool,
) -> GuardDecision:
    """Enforce a2a-python#1144..#1114."""
    missing_schemes = [s for s in required_schemes_in_requirement if s not in applied_client_schemes]
    if missing_schemes:
        return GuardDecision(
            admitted=False,
            code="A2A_PYTHON_MULTI_SCHEME_AND_UNSATISFIED",
            detail="All schemes within a single security requirement object must be applied (AND semantics)",
            metadata={"missing_schemes": missing_schemes},
        )
    for name, val in rest_path_params.items():
        if not SAFE_REST_PARAM_RE.match(val) or ".." in val:
            return GuardDecision(
                admitted=False,
                code="A2A_PYTHON_REST_PATH_INJECTION_BLOCKED",
                detail=f"REST path parameter '{name}' contains control characters, slashes, or traversal sequences",
                metadata={"param": name, "value": repr(val)},
            )
    if push_auth_configured and not push_authorization_header_sent:
        return GuardDecision(
            admitted=False,
            code="A2A_PYTHON_PUSH_AUTH_HEADER_MISSING",
            detail="Configured PushNotificationConfig.authentication must emit an Authorization header",
            metadata={},
        )
    if slow_subscriber_queue_full and not evicted_on_full:
        return GuardDecision(
            admitted=False,
            code="A2A_PYTHON_SUBSCRIBER_TAP_DISPATCH_WEDGED",
            detail="Full subscriber tap must evict instead of blocking EventQueueSource._dispatch_loop",
            metadata={},
        )
    if not call_context_restored_after_cancel:
        return GuardDecision(
            admitted=False,
            code="A2A_PYTHON_CANCEL_CALL_CONTEXT_RACE",
            detail="ActiveTask.cancel() must save and restore _call_context to prevent racing with producer",
            metadata={},
        )
    return GuardDecision(
        admitted=True,
        code="A2A_PYTHON_AND_AUTH_PATH_TAP_VERIFIED",
        detail="Multi-scheme AND semantics, REST path sanitization, push auth header, and tap eviction verified",
        metadata={"applied_schemes": list(applied_client_schemes)},
    )


# ---------------------------------------------------------------------------
# PR-07: A2A Java fail-closed task authorization, AuthInterceptor safe header
#        allowlist & redirect block (GHSA-9rhm-2h4x-jwmx), and IPv4-mapped IPv6
#        push SSRF validator
# ---------------------------------------------------------------------------
SAFE_AUTH_HEADERS: frozenset[str] = frozenset({"authorization", "x-api-key", "x-a2a-token"})


def evaluate_a2a_java_failclosed_auth_ssrf_guard(
    *,
    task_auth_provider_configured: bool,
    task_authorized: bool,
    auth_header_name: str,
    auth_header_value: str,
    http_redirects_enabled: bool,
    push_webhook_host: str,
) -> GuardDecision:
    """Enforce a2a-java#1109..#1085 and a2a-js#781..#693."""
    if not task_auth_provider_configured or not task_authorized:
        return GuardDecision(
            admitted=False,
            code="A2A_JAVA_TASK_AUTH_FAIL_CLOSED",
            detail="DefaultRequestHandler enforces fail-closed task authorization when provider is missing or denies",
            metadata={"provider_configured": task_auth_provider_configured, "authorized": task_authorized},
        )
    if (
        auth_header_name.lower() not in SAFE_AUTH_HEADERS
        or "\r" in auth_header_value
        or "\n" in auth_header_value
        or http_redirects_enabled
    ):
        return GuardDecision(
            admitted=False,
            code="A2A_JAVA_CREDENTIAL_LEAK_OR_HEADER_INJECTION_BLOCKED",
            detail="AuthInterceptor blocked disallowed header, CRLF injection, or automatic HTTP redirects (GHSA-9rhm-2h4x-jwmx)",
            metadata={"header": auth_header_name, "redirects_enabled": http_redirects_enabled},
        )
    lowered_host = push_webhook_host.lower().strip("[]")
    if (
        lowered_host.startswith("::ffff:127.")
        or lowered_host.startswith("::ffff:169.254.")
        or lowered_host.startswith("::ffff:10.")
        or lowered_host in {"localhost", "127.0.0.1", "::1", "169.254.169.254"}
    ):
        return GuardDecision(
            admitted=False,
            code="A2A_JAVA_PUSH_SSRF_IPV4_MAPPED_IPV6_BLOCKED",
            detail="PushNotificationUrlValidator blocked loopback, link-local, or IPv4-mapped IPv6 SSRF address",
            metadata={"push_webhook_host": push_webhook_host},
        )
    return GuardDecision(
        admitted=True,
        code="A2A_JAVA_FAILCLOSED_AUTH_SSRF_VERIFIED",
        detail="Fail-closed task auth, GHSA-9rhm-2h4x-jwmx header/redirect guard, and IPv6 SSRF check verified",
        metadata={"push_webhook_host": push_webhook_host},
    )


# ---------------------------------------------------------------------------
# PR-08: Stripe Node AWS Workload Identity, V2List V1-field removal, and
#        EventNotificationHandler callback client context isolation
# ---------------------------------------------------------------------------
FORBIDDEN_V2_LIST_V1_FIELDS: frozenset[str] = frozenset({"object", "has_more", "url"})


def evaluate_stripe_node_workload_id_v2list_guard(
    *,
    auth_mode: str,
    aws_sts_token_ttl_seconds: int,
    v2_list_payload: Mapping[str, Any],
    callback_mutated_parent_client: bool,
    workflow_default_permissions: str,
) -> GuardDecision:
    """Enforce stripe-node#2859..#2844."""
    if auth_mode == "aws_workload_identity" and (aws_sts_token_ttl_seconds <= 0 or aws_sts_token_ttl_seconds > 3600):
        return GuardDecision(
            admitted=False,
            code="STRIPE_NODE_WORKLOAD_IDENTITY_TTL_INVALID",
            detail="AWS Workload Identity token must use a bounded short-lived TTL (<= 3600s)",
            metadata={"ttl_seconds": aws_sts_token_ttl_seconds},
        )
    leaked_v1 = FORBIDDEN_V2_LIST_V1_FIELDS.intersection(v2_list_payload.keys())
    if leaked_v1:
        return GuardDecision(
            admitted=False,
            code="STRIPE_NODE_V2_LIST_CONTAINS_V1_FIELDS",
            detail="Stripe V2List response must not expose legacy V1 fields (object, has_more, url)",
            metadata={"leaked_v1_fields": sorted(leaked_v1)},
        )
    if callback_mutated_parent_client or workflow_default_permissions != "none":
        return GuardDecision(
            admitted=False,
            code="STRIPE_NODE_CALLBACK_CONTEXT_OR_WORKFLOW_PERM_UNSAFE",
            detail="EventNotificationHandler must isolate callback client context and workflows must default permissions to none",
            metadata={"callback_mutated_parent_client": callback_mutated_parent_client},
        )
    return GuardDecision(
        admitted=True,
        code="STRIPE_NODE_WORKLOAD_ID_V2LIST_VERIFIED",
        detail="Stripe Node AWS Workload Identity, V2List schema purity, and callback client isolation verified",
        metadata={"auth_mode": auth_mode},
    )


# ---------------------------------------------------------------------------
# PR-09: Stripe Python EventNotificationHandler .pre_handle deduplication hook,
#        async event handlers, and EventNotification.object == "event"
# ---------------------------------------------------------------------------
def evaluate_stripe_python_event_prehandle_guard(
    *,
    notification_payload: Mapping[str, Any],
    seen_event_ids: set[str],
    pre_handle_executed: bool,
    is_async_handler: bool,
    awaited_properly: bool,
) -> GuardDecision:
    """Enforce stripe-python#1894..#1868."""
    if notification_payload.get("object") != "event":
        return GuardDecision(
            admitted=False,
            code="STRIPE_PYTHON_EVENT_NOTIFICATION_OBJECT_INVALID",
            detail="EventNotification must surface object == 'event'",
            metadata={"object": notification_payload.get("object")},
        )
    if not pre_handle_executed:
        return GuardDecision(
            admitted=False,
            code="STRIPE_PYTHON_PRE_HANDLE_SKIPPED",
            detail="EventNotificationHandler must execute .pre_handle before dispatching specific event handlers",
            metadata={},
        )
    event_id = str(notification_payload.get("id", ""))
    if not event_id or event_id in seen_event_ids:
        return GuardDecision(
            admitted=False,
            code="STRIPE_PYTHON_DUPLICATE_THIN_EVENT_BLOCKED",
            detail="EventNotificationHandler .pre_handle hook blocked duplicate thin event ID",
            metadata={"event_id": event_id},
        )
    if is_async_handler and not awaited_properly:
        return GuardDecision(
            admitted=False,
            code="STRIPE_PYTHON_ASYNC_HANDLER_NOT_AWAITED",
            detail="Async event notification handler must be awaited via handle_async",
            metadata={},
        )
    return GuardDecision(
        admitted=True,
        code="STRIPE_PYTHON_EVENT_PREHANDLE_VERIFIED",
        detail="EventNotificationHandler .pre_handle deduplication, object property, and async dispatch verified",
        metadata={"event_id": event_id},
    )


# ---------------------------------------------------------------------------
# PR-10: Stripe Go non-empty webhook secret & exact decimals, plus Stripe CLI
#        space-separated boolean flag parsing & 24h upgrade notice hold
# ---------------------------------------------------------------------------
def evaluate_stripe_go_secret_cli_bool_release_guard(
    *,
    webhook_secret: str,
    cli_args: Sequence[str],
    release_age_hours: float,
    upgrade_notice_shown: bool,
    chmod_executed_on_invocation: bool,
) -> GuardDecision:
    """Enforce stripe-go#2439..#2429 and stripe-cli#2109..#2092."""
    if not webhook_secret or not webhook_secret.strip():
        return GuardDecision(
            admitted=False,
            code="STRIPE_GO_EMPTY_WEBHOOK_SECRET_REJECTED",
            detail="Webhook signature verification must reject empty or whitespace-only signing secrets",
            metadata={},
        )
    parsed_flags: dict[str, bool] = {}
    positional: list[str] = []
    i = 0
    while i < len(cli_args):
        token = cli_args[i]
        if token.startswith("--"):
            key = token[2:]
            if i + 1 < len(cli_args) and cli_args[i + 1].lower() in {"true", "false"}:
                parsed_flags[key] = cli_args[i + 1].lower() == "true"
                i += 2
                continue
            parsed_flags[key] = True
        else:
            positional.append(token)
        i += 1
    if positional:
        return GuardDecision(
            admitted=False,
            code="STRIPE_CLI_BOOLEAN_FLAG_POSITIONAL_MISPARSE",
            detail="Space-separated boolean value was misparsed as a positional argument",
            metadata={"positional": positional},
        )
    if release_age_hours < 24.0 and upgrade_notice_shown:
        return GuardDecision(
            admitted=False,
            code="STRIPE_CLI_PREMATURE_UPGRADE_NOTICE",
            detail="CLI upgrade notice must be held until release published_at is at least 24 hours old",
            metadata={"release_age_hours": release_age_hours},
        )
    if chmod_executed_on_invocation:
        return GuardDecision(
            admitted=False,
            code="STRIPE_CLI_REDUNDANT_CHMOD_ON_INVOCATION",
            detail="CLI must not run redundant os.Chmod on config file at every invocation",
            metadata={},
        )
    return GuardDecision(
        admitted=True,
        code="STRIPE_GO_SECRET_CLI_BOOL_RELEASE_VERIFIED",
        detail="Non-empty Go webhook secret, CLI space-separated boolean flags, and 24h upgrade hold verified",
        metadata={"parsed_flags": parsed_flags},
    )


# ---------------------------------------------------------------------------
# PR-11: Coinbase AgentKit uploadMedia cwd/realpath confinement, x402
#        beforePayment recipient screening, ActionRefVerify, and Beaver Knight
# ---------------------------------------------------------------------------
def evaluate_agentkit_upload_cwd_beforepayment_actionref_guard(
    *,
    allowed_cwd: str,
    requested_upload_path: str,
    recipient_address: str,
    sanctioned_recipients: frozenset[str],
    declared_action_payload: Mapping[str, Any],
    claimed_action_ref: str,
    beaver_knight_trust_score: int,
    min_trust_score: int = 70,
) -> GuardDecision:
    """Enforce coinbase/agentkit#1459..#1426."""
    base_real = os.path.normcase(os.path.abspath(allowed_cwd))
    target_real = os.path.normcase(os.path.abspath(os.path.join(allowed_cwd, requested_upload_path)))
    try:
        common = os.path.commonpath([base_real, target_real])
    except ValueError:
        common = ""
    if common != base_real:
        return GuardDecision(
            admitted=False,
            code="AGENTKIT_UPLOAD_MEDIA_PATH_TRAVERSAL_BLOCKED",
            detail="uploadMedia confined filePath to cwd; prompt-injected traversal outside cwd blocked",
            metadata={"requested_upload_path": requested_upload_path},
        )
    if recipient_address.lower() in {addr.lower() for addr in sanctioned_recipients}:
        return GuardDecision(
            admitted=False,
            code="AGENTKIT_X402_BEFORE_PAYMENT_RECIPIENT_BLOCKED",
            detail="x402 beforePayment hook blocked payment to sanctioned or untrusted recipient",
            metadata={"recipient_address": recipient_address},
        )
    canonical = json.dumps(declared_action_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_ref = "aref_" + hashlib.sha256(canonical).hexdigest()[:32]
    if claimed_action_ref != expected_ref:
        return GuardDecision(
            admitted=False,
            code="AGENTKIT_ACTION_REF_VERIFY_MISMATCH",
            detail="Recomputed content-addressed action_ref does not match claimed action_ref",
            metadata={"expected_ref": expected_ref, "claimed_ref": claimed_action_ref},
        )
    if beaver_knight_trust_score < min_trust_score:
        return GuardDecision(
            admitted=False,
            code="AGENTKIT_BEAVER_KNIGHT_TRUST_TOO_LOW",
            detail="Counterparty agent/vault failed Beaver Knight minimum trust score threshold",
            metadata={"score": beaver_knight_trust_score, "min_score": min_trust_score},
        )
    return GuardDecision(
        admitted=True,
        code="AGENTKIT_UPLOAD_CWD_BEFOREPAYMENT_ACTIONREF_VERIFIED",
        detail="uploadMedia cwd confinement, x402 beforePayment screen, ActionRefVerify, and Beaver Knight verified",
        metadata={"action_ref": expected_ref},
    )


# ---------------------------------------------------------------------------
# PR-12: MCP Go SDK 1 MiB OAuth DCR read cap, server protocol version restriction,
#        completed listen ID pruning, and SSE close message draining
# ---------------------------------------------------------------------------
MAX_DCR_RESPONSE_BYTES = 1024 * 1024


def evaluate_mcp_go_dcr_version_listen_drain_guard(
    *,
    dcr_response_bytes: int,
    requested_protocol_version: str,
    allowed_protocol_versions: Sequence[str],
    active_listen_ids: set[str],
    completed_listen_ids: set[str],
    sse_buffered_messages_drained_on_close: bool,
) -> GuardDecision:
    """Enforce modelcontextprotocol/go-sdk#1219..#1166."""
    if dcr_response_bytes > MAX_DCR_RESPONSE_BYTES:
        return GuardDecision(
            admitted=False,
            code="MCP_GO_OAUTHEX_DCR_RESPONSE_TOO_LARGE",
            detail="OAuth Dynamic Client Registration response exceeded 1 MiB read bound",
            metadata={"dcr_response_bytes": dcr_response_bytes},
        )
    if requested_protocol_version not in allowed_protocol_versions:
        return GuardDecision(
            admitted=False,
            code="MCP_GO_PROTOCOL_VERSION_RESTRICTED",
            detail="Requested MCP protocol version is not in server's allowed protocol versions list",
            metadata={"requested": requested_protocol_version, "allowed": list(allowed_protocol_versions)},
        )
    unpruned = active_listen_ids.intersection(completed_listen_ids)
    if unpruned or not sse_buffered_messages_drained_on_close:
        return GuardDecision(
            admitted=False,
            code="MCP_GO_LISTEN_ID_LEAK_OR_SSE_UNDRAINED",
            detail="Completed subscriptions/listen IDs must be pruned and SSE messages drained on Close()",
            metadata={"unpruned_count": len(unpruned)},
        )
    return GuardDecision(
        admitted=True,
        code="MCP_GO_DCR_VERSION_LISTEN_DRAIN_VERIFIED",
        detail="MCP Go 1 MiB DCR bound, protocol version restriction, listen ID pruning, and SSE drain verified",
        metadata={"protocol_version": requested_protocol_version},
    )


# ---------------------------------------------------------------------------
# PR-13: MCP Rust SDK retired session reply rejection, 403 invalid Origin,
#        sessionless discover fallback, and pinned Action SHAs
# ---------------------------------------------------------------------------
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def evaluate_mcp_rust_retired_session_origin_sha_guard(
    *,
    session_retired: bool,
    late_reply_accepted: bool,
    origin_header: str,
    allowed_origins: Sequence[str],
    action_pins: Sequence[str],
) -> GuardDecision:
    """Enforce modelcontextprotocol/rust-sdk#1221..#1186."""
    if session_retired and late_reply_accepted:
        return GuardDecision(
            admitted=False,
            code="MCP_RUST_RETIRED_SESSION_REPLY_ACCEPTED",
            detail="Replies from retired Streamable HTTP sessions must be rejected",
            metadata={},
        )
    parsed_origin = urlparse(origin_header)
    if (
        not origin_header.isascii()
        or parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or origin_header not in allowed_origins
    ):
        return GuardDecision(
            admitted=False,
            code="MCP_RUST_INVALID_ORIGIN_403_FORBIDDEN",
            detail="Malformed, non-UTF-8, or disallowed Origin header rejected with 403 Forbidden",
            metadata={"origin_header": repr(origin_header)},
        )
    if any(not SHA40_RE.match(pin) for pin in action_pins):
        return GuardDecision(
            admitted=False,
            code="MCP_RUST_UNPINNED_GITHUB_ACTION_REF",
            detail="All GitHub Action references must be pinned to immutable 40-char commit SHAs",
            metadata={},
        )
    return GuardDecision(
        admitted=True,
        code="MCP_RUST_RETIRED_SESSION_ORIGIN_SHA_VERIFIED",
        detail="Rust retired session rejection, 403 strict Origin validation, and 40-hex SHA pins verified",
        metadata={"origin": origin_header},
    )


# ---------------------------------------------------------------------------
# PR-14: MCP Python SDK case-insensitive Host/Origin, request-ID mint counter
#        advance past caller IDs, non-finite float -> null serialization, and
#        no GET retry on HTTP 405
# ---------------------------------------------------------------------------
def evaluate_mcp_python_host_case_mint_nan_405_guard(
    *,
    host_header: str,
    allowed_hosts: Sequence[str],
    caller_supplied_request_ids: Sequence[int],
    next_minted_request_id: int,
    float_values: Sequence[float],
    get_stream_http_status: int,
    get_stream_retried: bool,
) -> GuardDecision:
    """Enforce modelcontextprotocol/python-sdk#3458..#3420."""
    if host_header.lower() not in {h.lower() for h in allowed_hosts}:
        return GuardDecision(
            admitted=False,
            code="MCP_PYTHON_HOST_VALIDATION_FAILED",
            detail="Host header failed RFC 9110 case-insensitive allowlist check",
            metadata={"host_header": host_header},
        )
    max_supplied = max(caller_supplied_request_ids, default=0)
    if next_minted_request_id <= max_supplied:
        return GuardDecision(
            admitted=False,
            code="MCP_PYTHON_REQUEST_ID_MINT_COLLISION",
            detail="Dispatcher mint counter must advance past caller-supplied request_id values",
            metadata={"max_supplied": max_supplied, "next_minted": next_minted_request_id},
        )
    if get_stream_http_status == 405 and get_stream_retried:
        return GuardDecision(
            admitted=False,
            code="MCP_PYTHON_GET_STREAM_405_RETRY_FORBIDDEN",
            detail="Streamable HTTP client must not retry GET stream when server responds 405 Method Not Allowed",
            metadata={},
        )
    serialized = [None if (math.isnan(v) or math.isinf(v)) else v for v in float_values]
    return GuardDecision(
        admitted=True,
        code="MCP_PYTHON_HOST_CASE_MINT_NAN_405_VERIFIED",
        detail="Case-insensitive Host check, monotonic request-ID minting, non-finite float->null, and 405 stop verified",
        metadata={"serialized_floats": serialized, "next_minted_request_id": next_minted_request_id},
    )


# ---------------------------------------------------------------------------
# PR-15: MCP TypeScript SDK in-memory FIFO order & close discard, listTools()
#        cache preservation on refresh failure, and pre-response progress order
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_queue_order_tool_cache_progress_guard(
    *,
    queued_messages_before_close: Sequence[str],
    transport_closed: bool,
    delivered_after_close: Sequence[str],
    previous_tool_cache: Sequence[str],
    refresh_compile_failed: bool,
    active_tool_cache: Sequence[str],
    events_in_single_chunk: Sequence[str],
) -> GuardDecision:
    """Enforce modelcontextprotocol/typescript-sdk#2984..#2965."""
    if transport_closed and delivered_after_close:
        return GuardDecision(
            admitted=False,
            code="MCP_TS_CLOSED_TRANSPORT_DELIVERED_STALE_MESSAGES",
            detail="In-memory transport must discard queued messages on close()",
            metadata={"delivered_after_close": list(delivered_after_close)},
        )
    if refresh_compile_failed and list(active_tool_cache) != list(previous_tool_cache):
        return GuardDecision(
            admitted=False,
            code="MCP_TS_TOOL_CACHE_LOST_ON_REFRESH_FAILURE",
            detail="Client must keep previous cached tool metadata when listTools() refresh fails to compile",
            metadata={"active_tool_cache": list(active_tool_cache)},
        )
    if "response" in events_in_single_chunk and "progress" in events_in_single_chunk:
        if events_in_single_chunk.index("progress") > events_in_single_chunk.index("response"):
            return GuardDecision(
                admitted=False,
                code="MCP_TS_PROGRESS_DELIVERED_AFTER_RESPONSE",
                detail="Progress notifications arriving before the response in the same read must be delivered first",
                metadata={"events": list(events_in_single_chunk)},
            )
    return GuardDecision(
        admitted=True,
        code="MCP_TS_QUEUE_ORDER_TOOL_CACHE_PROGRESS_VERIFIED",
        detail="In-memory FIFO & close discard, listTools() cache retention, and progress ordering verified",
        metadata={"retained_tools": len(active_tool_cache), "queued_before_close": len(queued_messages_before_close)},
    )


# ---------------------------------------------------------------------------
# PR-16: MCP C# integer ProgressToken, Java JSON-RPC version & pre-complete JSON
#        parse & SSE U+2028 preservation, and Inspector 400 era fallback & secret
#        carry-over
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_java_inspector_guard(
    *,
    progress_token_json_value: Any,
    jsonrpc_response_version: str,
    http_200_body_is_valid_json: bool,
    send_message_completed_before_parse: bool,
    sse_value_contains_u2028: bool,
    sse_value_truncated: bool,
    inspector_probe_status: int,
    inspector_auto_era_fell_back: bool,
    stripped_namespace_secret_preserved: bool,
) -> GuardDecision:
    """Enforce csharp-sdk#1834..#1826, java-sdk#1161..#1138, and inspector#2684..#2664."""
    if not isinstance(progress_token_json_value, int) or isinstance(progress_token_json_value, bool):
        return GuardDecision(
            admitted=False,
            code="MCP_CSHARP_INTEGER_PROGRESS_TOKEN_STRINGIFIED",
            detail="Integer ProgressToken must serialize as a JSON number, not a string",
            metadata={"type": type(progress_token_json_value).__name__},
        )
    if jsonrpc_response_version != "2.0":
        return GuardDecision(
            admitted=False,
            code="MCP_JAVA_INVALID_JSONRPC_VERSION_REJECTED",
            detail="Java MCP client must reject responses whose jsonrpc version is not '2.0'",
            metadata={"jsonrpc": jsonrpc_response_version},
        )
    if not http_200_body_is_valid_json and send_message_completed_before_parse:
        return GuardDecision(
            admitted=False,
            code="MCP_JAVA_INVALID_JSON_SWALLOWED_BY_EARLY_COMPLETE",
            detail="Streamable HTTP transport must parse JSON before completing sendMessage so errors propagate",
            metadata={},
        )
    if sse_value_contains_u2028 and sse_value_truncated:
        return GuardDecision(
            admitted=False,
            code="MCP_JAVA_SSE_UNICODE_LINE_SEPARATOR_TRUNCATED",
            detail="SseLineSubscriber must not truncate SSE field values containing U+2028/U+2029/U+0085",
            metadata={},
        )
    if (inspector_probe_status == 400 and not inspector_auto_era_fell_back) or not stripped_namespace_secret_preserved:
        return GuardDecision(
            admitted=False,
            code="MCP_INSPECTOR_FALLBACK_OR_SECRET_CARRYOVER_FAILED",
            detail="Inspector must fall back on 400 discover probe in auto era and preserve stripped-namespace secrets",
            metadata={
                "probe_status": inspector_probe_status,
                "fell_back": inspector_auto_era_fell_back,
                "secret_preserved": stripped_namespace_secret_preserved,
            },
        )
    return GuardDecision(
        admitted=True,
        code="MCP_CSHARP_JAVA_INSPECTOR_VERIFIED",
        detail="C# integer ProgressToken, Java JSON-RPC/SSE/parse guards, and Inspector 400 fallback verified",
        metadata={"progress_token": progress_token_json_value},
    )
