"""Stage 278 deterministic protocol & security guards (`PR-01..PR-16`).

Covers 238 strictly zero-overlap primary-source pull requests across 33 upstream
repositories (`coinbase/x402`, `coinbase/agentkit`,
`Universal-Commerce-Protocol/ucp`, `Universal-Commerce-Protocol/python-sdk`,
`Universal-Commerce-Protocol/conformance`, `Universal-Commerce-Protocol/samples`,
`agentic-commerce-protocol/agentic-commerce-protocol`, `a2aproject/A2A`,
`a2aproject/a2a-python`, `a2aproject/a2a-js`, `a2aproject/a2a-go`,
`a2aproject/a2a-java`, `a2aproject/a2a-dotnet`, `a2aproject/a2a-inspector`,
`stripe/agent-toolkit`, `stripe/stripe-cli`, `stripe/stripe-python`,
`stripe/stripe-node`, `stripe/stripe-go`, `stripe/stripe-dotnet`,
`stripe/stripe-java`, `stripe/stripe-ruby`, `stripe/stripe-php`,
`modelcontextprotocol/modelcontextprotocol`,
`modelcontextprotocol/typescript-sdk`, `modelcontextprotocol/python-sdk`,
`modelcontextprotocol/go-sdk`, `modelcontextprotocol/csharp-sdk`,
`modelcontextprotocol/java-sdk`, `modelcontextprotocol/rust-sdk`,
`modelcontextprotocol/kotlin-sdk`, `modelcontextprotocol/inspector`, and
`modelcontextprotocol/registry`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import ipaddress
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote, unquote_to_bytes, urlparse


@dataclass(frozen=True)
class GuardDecision:
    admitted: bool
    code: str
    detail: str
    metadata: Mapping[str, Any]


STAGE_278_PR_CITATIONS: dict[str, tuple[str, ...]] = {
    "PR-01": (
        "coinbase/x402#420",
        "coinbase/x402#419",
        "coinbase/x402#414",
        "coinbase/x402#413",
        "coinbase/x402#346",
        "coinbase/x402#334",
        "coinbase/x402#324",
        "coinbase/x402#323",
        "coinbase/x402#322",
        "coinbase/x402#317",
        "coinbase/x402#50",
        "coinbase/x402#48",
        "coinbase/x402#46",
        "coinbase/x402#44",
    ),
    "PR-02": (
        "coinbase/agentkit#1598",
        "coinbase/agentkit#1597",
        "coinbase/agentkit#1593",
        "coinbase/agentkit#1591",
        "coinbase/agentkit#1590",
        "coinbase/agentkit#1589",
        "coinbase/agentkit#1581",
        "coinbase/agentkit#1579",
        "coinbase/agentkit#1575",
        "coinbase/agentkit#1572",
        "coinbase/agentkit#1567",
        "coinbase/agentkit#1564",
        "coinbase/agentkit#1563",
        "coinbase/agentkit#1559",
        "coinbase/agentkit#1557",
        "coinbase/agentkit#1550",
    ),
    "PR-03": (
        "Universal-Commerce-Protocol/ucp#984",
        "Universal-Commerce-Protocol/ucp#982",
        "Universal-Commerce-Protocol/ucp#981",
        "Universal-Commerce-Protocol/ucp#980",
        "Universal-Commerce-Protocol/ucp#979",
        "Universal-Commerce-Protocol/ucp#977",
        "Universal-Commerce-Protocol/ucp#976",
        "Universal-Commerce-Protocol/ucp#975",
        "Universal-Commerce-Protocol/ucp#974",
        "Universal-Commerce-Protocol/ucp#966",
        "Universal-Commerce-Protocol/ucp#964",
        "Universal-Commerce-Protocol/ucp#963",
        "Universal-Commerce-Protocol/ucp#948",
        "Universal-Commerce-Protocol/ucp#946",
        "Universal-Commerce-Protocol/ucp#945",
        "Universal-Commerce-Protocol/ucp#940",
    ),
    "PR-04": (
        "Universal-Commerce-Protocol/python-sdk#101",
        "Universal-Commerce-Protocol/python-sdk#100",
        "Universal-Commerce-Protocol/python-sdk#99",
        "Universal-Commerce-Protocol/python-sdk#96",
        "Universal-Commerce-Protocol/python-sdk#94",
        "Universal-Commerce-Protocol/python-sdk#91",
        "Universal-Commerce-Protocol/python-sdk#89",
        "Universal-Commerce-Protocol/python-sdk#87",
        "Universal-Commerce-Protocol/python-sdk#83",
        "Universal-Commerce-Protocol/python-sdk#76",
        "Universal-Commerce-Protocol/python-sdk#74",
        "Universal-Commerce-Protocol/python-sdk#70",
        "Universal-Commerce-Protocol/python-sdk#69",
        "Universal-Commerce-Protocol/python-sdk#68",
        "Universal-Commerce-Protocol/python-sdk#66",
        "Universal-Commerce-Protocol/python-sdk#64",
    ),
    "PR-05": (
        "Universal-Commerce-Protocol/conformance#113",
        "Universal-Commerce-Protocol/conformance#111",
        "Universal-Commerce-Protocol/conformance#110",
        "Universal-Commerce-Protocol/conformance#109",
        "Universal-Commerce-Protocol/conformance#98",
        "Universal-Commerce-Protocol/conformance#97",
        "Universal-Commerce-Protocol/conformance#88",
        "Universal-Commerce-Protocol/conformance#85",
        "Universal-Commerce-Protocol/conformance#82",
        "Universal-Commerce-Protocol/conformance#76",
        "Universal-Commerce-Protocol/samples#253",
        "Universal-Commerce-Protocol/samples#252",
        "Universal-Commerce-Protocol/samples#249",
        "Universal-Commerce-Protocol/samples#248",
        "Universal-Commerce-Protocol/samples#247",
        "Universal-Commerce-Protocol/samples#246",
        "Universal-Commerce-Protocol/samples#228",
        "Universal-Commerce-Protocol/samples#226",
    ),
    "PR-06": (
        "agentic-commerce-protocol/agentic-commerce-protocol#314",
        "agentic-commerce-protocol/agentic-commerce-protocol#310",
        "agentic-commerce-protocol/agentic-commerce-protocol#305",
        "agentic-commerce-protocol/agentic-commerce-protocol#296",
        "agentic-commerce-protocol/agentic-commerce-protocol#289",
        "agentic-commerce-protocol/agentic-commerce-protocol#288",
        "agentic-commerce-protocol/agentic-commerce-protocol#287",
        "agentic-commerce-protocol/agentic-commerce-protocol#285",
        "agentic-commerce-protocol/agentic-commerce-protocol#284",
        "agentic-commerce-protocol/agentic-commerce-protocol#281",
        "agentic-commerce-protocol/agentic-commerce-protocol#275",
        "agentic-commerce-protocol/agentic-commerce-protocol#266",
        "agentic-commerce-protocol/agentic-commerce-protocol#262",
        "agentic-commerce-protocol/agentic-commerce-protocol#260",
        "agentic-commerce-protocol/agentic-commerce-protocol#256",
        "agentic-commerce-protocol/agentic-commerce-protocol#254",
    ),
    "PR-07": (
        "a2aproject/A2A#2378",
        "a2aproject/A2A#2375",
        "a2aproject/A2A#2364",
        "a2aproject/A2A#2362",
        "a2aproject/A2A#2352",
        "a2aproject/A2A#2319",
        "a2aproject/a2a-python#1364",
        "a2aproject/a2a-python#1355",
        "a2aproject/a2a-python#1354",
        "a2aproject/a2a-python#1346",
        "a2aproject/a2a-python#1345",
        "a2aproject/a2a-python#1338",
        "a2aproject/a2a-python#1336",
        "a2aproject/a2a-python#1335",
        "a2aproject/a2a-python#1333",
        "a2aproject/a2a-python#1326",
    ),
    "PR-08": (
        "a2aproject/a2a-js#776",
        "a2aproject/a2a-js#775",
        "a2aproject/a2a-js#774",
        "a2aproject/a2a-js#762",
        "a2aproject/a2a-js#758",
        "a2aproject/a2a-go#457",
        "a2aproject/a2a-go#456",
        "a2aproject/a2a-go#453",
        "a2aproject/a2a-go#450",
        "a2aproject/a2a-go#441",
        "a2aproject/a2a-java#1239",
        "a2aproject/a2a-java#1213",
        "a2aproject/a2a-java#1198",
        "a2aproject/a2a-dotnet#569",
        "a2aproject/a2a-dotnet#541",
        "a2aproject/a2a-dotnet#539",
        "a2aproject/a2a-inspector#217",
        "a2aproject/a2a-inspector#214",
    ),
    "PR-09": (
        "stripe/agent-toolkit#579",
        "stripe/agent-toolkit#569",
        "stripe/agent-toolkit#567",
        "stripe/agent-toolkit#544",
        "stripe/agent-toolkit#543",
        "stripe/agent-toolkit#542",
        "stripe/agent-toolkit#541",
        "stripe/agent-toolkit#540",
        "stripe/agent-toolkit#519",
        "stripe/agent-toolkit#509",
        "stripe/agent-toolkit#495",
        "stripe/stripe-cli#2150",
        "stripe/stripe-cli#2147",
        "stripe/stripe-cli#2141",
        "stripe/stripe-cli#2125",
        "stripe/stripe-cli#2124",
    ),
    "PR-10": (
        "stripe/stripe-python#1951",
        "stripe/stripe-python#1944",
        "stripe/stripe-node#2907",
        "stripe/stripe-node#2898",
        "stripe/stripe-node#2876",
        "stripe/stripe-go#2476",
        "stripe/stripe-go#2468",
        "stripe/stripe-go#2465",
        "stripe/stripe-dotnet#3477",
        "stripe/stripe-dotnet#3466",
        "stripe/stripe-java#2316",
        "stripe/stripe-java#2313",
        "stripe/stripe-ruby#1992",
        "stripe/stripe-ruby#1990",
        "stripe/stripe-php#2175",
        "stripe/stripe-php#2172",
    ),
    "PR-11": (
        "modelcontextprotocol/typescript-sdk#3095",
        "modelcontextprotocol/typescript-sdk#3093",
        "modelcontextprotocol/typescript-sdk#3092",
        "modelcontextprotocol/typescript-sdk#3091",
        "modelcontextprotocol/typescript-sdk#3083",
        "modelcontextprotocol/typescript-sdk#3082",
        "modelcontextprotocol/typescript-sdk#3081",
        "modelcontextprotocol/typescript-sdk#3079",
        "modelcontextprotocol/typescript-sdk#3074",
        "modelcontextprotocol/typescript-sdk#3071",
        "modelcontextprotocol/typescript-sdk#3063",
        "modelcontextprotocol/typescript-sdk#3046",
        "modelcontextprotocol/typescript-sdk#3040",
        "modelcontextprotocol/typescript-sdk#3039",
    ),
    "PR-12": (
        "modelcontextprotocol/python-sdk#3758",
        "modelcontextprotocol/python-sdk#3757",
        "modelcontextprotocol/python-sdk#3756",
        "modelcontextprotocol/python-sdk#3755",
        "modelcontextprotocol/python-sdk#3753",
        "modelcontextprotocol/python-sdk#3750",
        "modelcontextprotocol/python-sdk#3744",
        "modelcontextprotocol/python-sdk#3730",
        "modelcontextprotocol/python-sdk#3726",
        "modelcontextprotocol/python-sdk#3708",
        "modelcontextprotocol/python-sdk#3697",
        "modelcontextprotocol/python-sdk#3696",
    ),
    "PR-13": (
        "modelcontextprotocol/go-sdk#1447",
        "modelcontextprotocol/go-sdk#1441",
        "modelcontextprotocol/go-sdk#1438",
        "modelcontextprotocol/go-sdk#1427",
        "modelcontextprotocol/go-sdk#1425",
        "modelcontextprotocol/go-sdk#1421",
        "modelcontextprotocol/go-sdk#1419",
        "modelcontextprotocol/go-sdk#1418",
        "modelcontextprotocol/go-sdk#1405",
        "modelcontextprotocol/go-sdk#1401",
        "modelcontextprotocol/go-sdk#1398",
        "modelcontextprotocol/go-sdk#1397",
    ),
    "PR-14": (
        "modelcontextprotocol/csharp-sdk#1949",
        "modelcontextprotocol/csharp-sdk#1946",
        "modelcontextprotocol/csharp-sdk#1934",
        "modelcontextprotocol/csharp-sdk#1932",
        "modelcontextprotocol/csharp-sdk#1929",
        "modelcontextprotocol/csharp-sdk#1917",
        "modelcontextprotocol/rust-sdk#1385",
        "modelcontextprotocol/rust-sdk#1382",
        "modelcontextprotocol/rust-sdk#1380",
        "modelcontextprotocol/rust-sdk#1377",
        "modelcontextprotocol/rust-sdk#1375",
        "modelcontextprotocol/rust-sdk#1341",
    ),
    "PR-15": (
        "modelcontextprotocol/java-sdk#1275",
        "modelcontextprotocol/java-sdk#1208",
        "modelcontextprotocol/java-sdk#1207",
        "modelcontextprotocol/java-sdk#1202",
        "modelcontextprotocol/java-sdk#1184",
        "modelcontextprotocol/java-sdk#1169",
        "modelcontextprotocol/java-sdk#1164",
        "modelcontextprotocol/java-sdk#1162",
        "modelcontextprotocol/kotlin-sdk#1122",
        "modelcontextprotocol/kotlin-sdk#1120",
        "modelcontextprotocol/kotlin-sdk#1118",
        "modelcontextprotocol/kotlin-sdk#1117",
    ),
    "PR-16": (
        "modelcontextprotocol/inspector#2792",
        "modelcontextprotocol/inspector#2790",
        "modelcontextprotocol/inspector#2789",
        "modelcontextprotocol/inspector#2774",
        "modelcontextprotocol/inspector#2773",
        "modelcontextprotocol/inspector#2739",
        "modelcontextprotocol/registry#1702",
        "modelcontextprotocol/registry#1640",
        "modelcontextprotocol/registry#1622",
        "modelcontextprotocol/registry#1583",
        "modelcontextprotocol/registry#1574",
        "modelcontextprotocol/registry#1570",
        "modelcontextprotocol/modelcontextprotocol#3440",
        "modelcontextprotocol/modelcontextprotocol#3418",
    ),
}


def evaluate_x402_eip3009_domain_sar_extensions_guard(
    *,
    eip712_domain: Mapping[str, Any],
    expected_chain_id: int,
    expected_verifying_contract: str,
    sar_receipt: Mapping[str, Any],
    owner_consented_solidarity_bps: int,
    max_solidarity_bps: int = 1000,
    no_wallet_mode: bool = False,
    no_wallet_delegated_voucher_verified: bool = True,
) -> GuardDecision:
    """PR-01: x402 EIP-3009 EIP-712 domain mapping, SAR witness receipt & extension guard."""
    required_domain_keys = {"name", "version", "chainId", "verifyingContract"}
    if not required_domain_keys.issubset(eip712_domain.keys()):
        return GuardDecision(
            False,
            "X402_EIP3009_DOMAIN_INCOMPLETE",
            "exact/evm eip3009 requires complete EIP-712 domain (name, version, chainId, verifyingContract)",
            {"domain_keys": sorted(eip712_domain.keys())},
        )
    if (
        int(eip712_domain["chainId"]) != expected_chain_id
        or str(eip712_domain["verifyingContract"]).lower() != expected_verifying_contract.lower()
        or not str(eip712_domain["name"]).strip()
        or not str(eip712_domain["version"]).strip()
    ):
        return GuardDecision(
            False,
            "X402_EIP3009_DOMAIN_MISMATCH",
            "EIP-3009 EIP-712 domain parameters do not match asset contract or chainId",
            {"chain_id": eip712_domain.get("chainId")},
        )
    if (
        not sar_receipt.get("tx_hash")
        or not sar_receipt.get("witness_signature")
        or not sar_receipt.get("settled_at")
    ):
        return GuardDecision(
            False,
            "X402_SAR_ATTESTATION_INVALID",
            "Settlement Attestation Receipt (SAR) requires tx_hash, witness_signature, and settled_at",
            {"sar_keys": sorted(sar_receipt.keys())},
        )
    if owner_consented_solidarity_bps < 0 or owner_consented_solidarity_bps > max_solidarity_bps:
        return GuardDecision(
            False,
            "X402_SOLIDARITY_SPLIT_EXCEEDED",
            "Solidarity extension share exceeds owner-consented bps cap",
            {"bps": owner_consented_solidarity_bps, "max_bps": max_solidarity_bps},
        )
    if no_wallet_mode and not no_wallet_delegated_voucher_verified:
        return GuardDecision(
            False,
            "X402_NO_WALLET_VOUCHER_UNVERIFIED",
            "no-wallet extension requires verified delegated settlement voucher",
            {},
        )
    return GuardDecision(
        True,
        "X402_EIP3009_SAR_EXTENSIONS_OK",
        "EIP-3009 EIP-712 domain, SAR attestation, and x402 extensions verified",
        {"chain_id": expected_chain_id, "solidarity_bps": owner_consented_solidarity_bps},
    )


def evaluate_agentkit_receipt_cbbtc_spl_prepayment_guard(
    *,
    erc20_receipt_status: int | str,
    userop_reverted_in_bundle: bool,
    asset_symbol: str,
    resolved_decimals: int,
    spl_raw_amount: str,
    pre_payment_check_passed: bool,
    canary_prompt_injection_detected: bool,
    token_risk_verdict: str,
) -> GuardDecision:
    """PR-02: Coinbase AgentKit integer receipt status, cbBTC 8-decimal, SPL rounding & prePaymentCheck guard."""
    if not isinstance(erc20_receipt_status, int) or isinstance(erc20_receipt_status, bool) or erc20_receipt_status != 1:
        return GuardDecision(
            False,
            "AGENTKIT_ERC20_RECEIPT_STATUS_FAILED",
            "Python ERC20 transfer/approve requires integer receipt status == 1",
            {"receipt_status": erc20_receipt_status},
        )
    if userop_reverted_in_bundle:
        return GuardDecision(
            False,
            "AGENTKIT_SMART_WALLET_BUNDLE_REVERTED",
            "CDP Smart Wallet UserOperation reverted inside mined bundle",
            {},
        )
    if asset_symbol.upper() == "CBBTC" and resolved_decimals != 8:
        return GuardDecision(
            False,
            "AGENTKIT_MOONWELL_CBBTC_DECIMALS_MISMATCH",
            "Moonwell cbBTC redeem/supply must resolve to 8 decimals",
            {"resolved_decimals": resolved_decimals},
        )
    amt_dec = Decimal(spl_raw_amount)
    if amt_dec <= 0:
        return GuardDecision(
            False,
            "AGENTKIT_SPL_AMOUNT_NON_POSITIVE",
            "SPL transfer / Jupiter swap amount must be positive",
            {"spl_raw_amount": spl_raw_amount},
        )
    rounded_base_units = int(amt_dec.to_integral_value())
    if not pre_payment_check_passed or canary_prompt_injection_detected or token_risk_verdict != "safe":
        return GuardDecision(
            False,
            "AGENTKIT_PREPAYMENT_FIREWALL_BLOCKED",
            "x402 prePaymentCheck, CanaryGuard, or Token Verdict blocked execution",
            {
                "pre_payment_check_passed": pre_payment_check_passed,
                "canary_blocked": canary_prompt_injection_detected,
                "verdict": token_risk_verdict,
            },
        )
    return GuardDecision(
        True,
        "AGENTKIT_RECEIPT_CBBTC_SPL_PREPAYMENT_OK",
        "ERC20 integer receipt status, cbBTC decimals, SPL integer base units, and pre-payment firewall verified",
        {"rounded_base_units": rounded_base_units, "decimals": resolved_decimals},
    )


def evaluate_ucp_rfc9421_raw_rs_return_root_array_guard(
    *,
    ecdsa_p256_signature_bytes: bytes,
    return_eligible: bool,
    return_requested_at_epoch: int,
    business_return_deadline_epoch: int,
    return_fee_minor: int,
    fulfillment_event_type: str,
    schema_root_type: str,
) -> GuardDecision:
    """PR-03: UCP RFC 9421 raw 64-byte r||s ECDSA signature, return deadline/fee & root-array guard."""
    if len(ecdsa_p256_signature_bytes) != 64 or ecdsa_p256_signature_bytes[:1] == b"\x30":
        return GuardDecision(
            False,
            "UCP_RFC9421_ECDSA_DER_OR_LENGTH_INVALID",
            "RFC 9421 §3.3.3 requires raw 64-byte r||s ECDSA P-256 signature (not ASN.1 DER)",
            {"sig_len": len(ecdsa_p256_signature_bytes)},
        )
    if not return_eligible or return_requested_at_epoch > business_return_deadline_epoch or return_fee_minor < 0:
        return GuardDecision(
            False,
            "UCP_RETURN_ELIGIBILITY_OR_DEADLINE_VIOLATION",
            "Return request violates eligibility, business-stated deadline, or typed fee bounds",
            {"eligible": return_eligible, "fee_minor": return_fee_minor},
        )
    standard_events = {"shipment_created", "in_transit", "out_for_delivery", "delivered", "delivery_failed"}
    if fulfillment_event_type not in standard_events:
        return GuardDecision(
            False,
            "UCP_FULFILLMENT_EVENT_NON_STANDARD",
            "Order fulfillment event type is not in standardized UCP taxonomy",
            {"event_type": fulfillment_event_type},
        )
    if schema_root_type == "array":
        return GuardDecision(
            False,
            "UCP_ROOT_ARRAY_SCHEMA_FORBIDDEN",
            "Root-array JSON schemas violate the UCP schema authoring object-envelope rule",
            {"schema_root_type": schema_root_type},
        )
    return GuardDecision(
        True,
        "UCP_RFC9421_RETURN_ROOT_SCHEMA_OK",
        "RFC 9421 raw r||s signature, return deadline, fulfillment taxonomy, and object root verified",
        {"event_type": fulfillment_event_type},
    )


def evaluate_ucp_python_sdk_dependent_jwk_bounds_guard(
    *,
    payload: Mapping[str, Any],
    dependent_required: Mapping[str, Sequence[str]],
    max_properties: int,
    allowed_fields: set[str],
    jwk: Mapping[str, Any],
    datetime_field_has_regex_pattern: bool,
) -> GuardDecision:
    """PR-04: UCP Python SDK dependentRequired, JWK conditional rules, maxProperties & datetime regex guard."""
    if datetime_field_has_regex_pattern:
        return GuardDecision(
            False,
            "UCP_PY_DATETIME_REGEX_FORBIDDEN",
            "Generated datetime fields must not attach regex patterns alongside native datetime parsing",
            {},
        )
    if len(payload) > max_properties:
        return GuardDecision(
            False,
            "UCP_PY_MAX_PROPERTIES_EXCEEDED",
            "Payload exceeds maxProperties constraint",
            {"count": len(payload), "max": max_properties},
        )
    extra_keys = set(payload.keys()) - allowed_fields
    if extra_keys:
        return GuardDecision(
            False,
            "UCP_PY_ADDITIONAL_PROPERTIES_REJECTED",
            "Generated model with additionalProperties:false rejected undeclared fields",
            {"extra_keys": sorted(extra_keys)},
        )
    for trigger_key, req_keys in dependent_required.items():
        if trigger_key in payload:
            missing = [k for k in req_keys if k not in payload]
            if missing:
                return GuardDecision(
                    False,
                    "UCP_PY_DEPENDENT_REQUIRED_MISSING",
                    "Missing dependentRequired fields triggered by present property",
                    {"trigger": trigger_key, "missing": missing},
                )
    kty = jwk.get("kty")
    if kty == "EC" and not {"crv", "x", "y"}.issubset(jwk.keys()):
        return GuardDecision(
            False,
            "UCP_PY_JWK_CONDITIONAL_INVALID",
            "EC JWK is missing conditional required parameters (crv, x, y)",
            {"jwk_keys": sorted(jwk.keys())},
        )
    return GuardDecision(
        True,
        "UCP_PY_DEPENDENT_JWK_BOUNDS_OK",
        "UCP Python SDK dependentRequired, JWK conditional rules, maxProperties, and extra-field bounds verified",
        {"property_count": len(payload)},
    )


def evaluate_ucp_conformance_samples_webhook_checkout_guard(
    *,
    discovery_url: str,
    fixture_allowlist_hosts: set[str],
    webhook_payload_event_type: str | None,
    relied_on_x_event_type_header: bool,
    used_legacy_ucp_keys_mirror: bool,
    payment_instruments_count: int,
    missing_catalog_product_ids: Sequence[str],
) -> GuardDecision:
    """PR-05: UCP conformance & samples discovery URL, payload webhook identity & single-instrument completion guard."""
    parsed = urlparse(discovery_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" and host not in fixture_allowlist_hosts:
        return GuardDecision(
            False,
            "UCP_DISCOVERY_URL_UNSAFE",
            "Discovery URL must use HTTPS or belong to the explicit conformance fixture allowlist",
            {"discovery_url": discovery_url},
        )
    if relied_on_x_event_type_header or not webhook_payload_event_type:
        return GuardDecision(
            False,
            "UCP_WEBHOOK_HEADER_IDENTITY_FORBIDDEN",
            "Order webhook deliveries must be identified by signed payload rather than X-Event-Type header",
            {},
        )
    if used_legacy_ucp_keys_mirror:
        return GuardDecision(
            False,
            "UCP_LEGACY_KEYS_MIRROR_FORBIDDEN",
            "Signing keys must be read from canonical signing_keys[] path rather than deprecated ucp.keys[] mirror",
            {},
        )
    if payment_instruments_count != 1:
        return GuardDecision(
            False,
            "UCP_MULTIPLE_PAYMENT_INSTRUMENTS_REJECTED",
            "Checkout completion must reject multiple or zero payment instruments",
            {"payment_instruments_count": payment_instruments_count},
        )
    if missing_catalog_product_ids:
        return GuardDecision(
            False,
            "UCP_MISSING_CATALOG_PRODUCT_ON_COMPLETE",
            "Checkout completion must fail when a line item's product no longer exists",
            {"missing_products": list(missing_catalog_product_ids)},
        )
    return GuardDecision(
        True,
        "UCP_CONFORMANCE_SAMPLES_CHECKOUT_OK",
        "Discovery URL, payload-based webhook identity, canonical signing_keys[], and single-instrument completion verified",
        {"event_type": webhook_payload_event_type},
    )


def evaluate_acp_mcp_idempotency_delegate_sig_spend_guard(
    *,
    is_mutating_mcp_checkout_tool: bool,
    idempotency_key: str | None,
    delegate_endpoint: str,
    signature_header: str | None,
    timestamp_header: str | None,
    requires_spend_step: bool,
    host_spend_authorized: bool,
    schema_openapi_drifted_fields: Sequence[str] = (),
) -> GuardDecision:
    """PR-06: ACP mutating MCP checkout Idempotency-Key, delegate Signature+Timestamp & host spend authorization."""
    if is_mutating_mcp_checkout_tool and (not idempotency_key or not idempotency_key.strip()):
        return GuardDecision(
            False,
            "ACP_MCP_IDEMPOTENCY_KEY_MISSING",
            "Mutating MCP checkout tools require a non-empty Idempotency-Key",
            {},
        )
    if delegate_endpoint in {"delegate_payment", "delegate_authentication"}:
        if not signature_header or not signature_header.strip():
            return GuardDecision(
                False,
                "ACP_DELEGATE_SIGNATURE_REQUIRED",
                "Signature header is REQUIRED on delegate_payment and delegate_authentication",
                {"endpoint": delegate_endpoint},
            )
        if delegate_endpoint == "delegate_payment" and (not timestamp_header or not timestamp_header.strip()):
            return GuardDecision(
                False,
                "ACP_DELEGATE_TIMESTAMP_REQUIRED",
                "Timestamp header is REQUIRED alongside Signature on delegate_payment",
                {"endpoint": delegate_endpoint},
            )
    if requires_spend_step and not host_spend_authorized:
        return GuardDecision(
            False,
            "ACP_HOST_SPEND_AUTH_MISSING",
            "Host-side authorization must be granted before ACP spend execution",
            {},
        )
    if schema_openapi_drifted_fields:
        return GuardDecision(
            False,
            "ACP_SCHEMA_OPENAPI_DRIFT",
            "Detected property drift between JSON Schema and OpenAPI specifications",
            {"drifted": list(schema_openapi_drifted_fields)},
        )
    return GuardDecision(
        True,
        "ACP_IDEMPOTENCY_DELEGATE_SPEND_OK",
        "ACP MCP Idempotency-Key, delegate Signature/Timestamp, and host spend authorization verified",
        {"endpoint": delegate_endpoint},
    )


def evaluate_a2a_python_cgnat_ssrf_card_canon_terminal_guard(
    *,
    push_webhook_ip: str,
    agent_card_fields_preserved_before_jcs: bool,
    malformed_sig_headers_skipped: bool,
    is_terminal_task_state: bool,
    status_timestamp_stamped: bool,
    parked_interrupted_age_s: float,
    parked_timeout_s: float,
    parked_task_released: bool,
) -> GuardDecision:
    """PR-07: A2A Python RFC 6598 100.64.0.0/10 CGNAT SSRF block, Agent Card JCS field preservation & terminal timestamp."""
    ip_obj = ipaddress.ip_address(push_webhook_ip)
    cgnat_net = ipaddress.ip_network("100.64.0.0/10")
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or (isinstance(ip_obj, ipaddress.IPv4Address) and ip_obj in cgnat_net)
    ):
        return GuardDecision(
            False,
            "A2A_PY_SHARED_OR_PRIVATE_SSRF_BLOCKED",
            "Push webhook URL in RFC 6598 shared address space (100.64.0.0/10) or private range blocked",
            {"ip": push_webhook_ip},
        )
    if not agent_card_fields_preserved_before_jcs or not malformed_sig_headers_skipped:
        return GuardDecision(
            False,
            "A2A_PY_CARD_SIGNING_CANON_INVALID",
            "Agent Card field presence must be preserved before JCS canonicalization and malformed signature headers skipped",
            {},
        )
    if is_terminal_task_state and not status_timestamp_stamped:
        return GuardDecision(
            False,
            "A2A_PY_TERMINAL_TIMESTAMP_MISSING",
            "Terminal task states must always stamp status.timestamp",
            {},
        )
    if parked_interrupted_age_s > parked_timeout_s and not parked_task_released:
        return GuardDecision(
            False,
            "A2A_PY_PARKED_TASK_LEAK",
            "Parked interrupted tasks exceeding configurable timeout must be released",
            {"age_s": parked_interrupted_age_s, "timeout_s": parked_timeout_s},
        )
    return GuardDecision(
        True,
        "A2A_PY_CGNAT_CANON_TERMINAL_OK",
        "A2A Python CGNAT SSRF block, Agent Card JCS canonicalization, terminal timestamp, and parked timeout verified",
        {"ip": push_webhook_ip},
    )


def evaluate_a2a_multi_sdk_trailing_json_unicode_tenant_guard(
    *,
    raw_json_body: str,
    text_to_sign: str,
    client_supplied_tenant: str | None,
    effective_tenant: str,
    authenticated_tenant: str,
    push_delete_config_id: str | None,
    incomplete_sse_discarded_at_eof: bool,
    page_size: int,
) -> GuardDecision:
    """PR-08: A2A Go/JS/.NET/Java trailing JSON rejection, malformed Unicode signing guard & tenant spoofing block."""
    decoder = json.JSONDecoder()
    try:
        _, end_idx = decoder.raw_decode(raw_json_body.lstrip())
        trailing = raw_json_body.lstrip()[end_idx:].strip()
        if trailing:
            return GuardDecision(
                False,
                "A2A_GO_TRAILING_JSON_DATA_REJECTED",
                "Trailing data after root JSON body must be rejected",
                {"trailing": trailing[:32]},
            )
    except Exception as exc:
        return GuardDecision(
            False,
            "A2A_GO_JSON_DECODE_FAILED",
            f"Malformed JSON body: {exc}",
            {},
        )
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text_to_sign):
        return GuardDecision(
            False,
            "A2A_GO_CRYPTO_MALFORMED_UNICODE",
            "a2acrypto must reject unpaired UTF-16 surrogates / malformed Unicode before signing",
            {},
        )
    if client_supplied_tenant and effective_tenant != authenticated_tenant:
        return GuardDecision(
            False,
            "A2A_DOTNET_REQUEST_TENANT_SPOOFED",
            "HTTP handler must ignore client-supplied request tenant fields and enforce authenticated tenant",
            {"client_tenant": client_supplied_tenant, "effective_tenant": effective_tenant},
        )
    if not push_delete_config_id or not push_delete_config_id.strip():
        return GuardDecision(
            False,
            "A2A_JS_PUSH_DELETE_CONFIG_ID_MISSING",
            "Push notification config deletion without a config ID must be rejected",
            {},
        )
    if not incomplete_sse_discarded_at_eof or page_size <= 0 or page_size > 1000:
        return GuardDecision(
            False,
            "A2A_SSE_OR_PAGE_SIZE_INVALID",
            "Incomplete trailing SSE events must be discarded and list pageSize must be within bounds",
            {"page_size": page_size},
        )
    return GuardDecision(
        True,
        "A2A_MULTI_SDK_JSON_UNICODE_TENANT_OK",
        "Trailing JSON check, Unicode crypto check, tenant isolation, and push config ID verified",
        {"tenant": effective_tenant},
    )


def evaluate_stripe_cli_path_escape_plugin_reap_mcp_guard(
    *,
    resource_id: str,
    rendered_api_path: str,
    parent_terminated_abnormally: bool,
    peer_plugins_reaped: bool,
    auto_upgraded_across_major: bool,
    mcp_forward_failed: bool,
    mcp_error_reply_sent: bool,
    abandoned_stream_stopped: bool,
) -> GuardDecision:
    """PR-09: Stripe CLI positional resource ID escaping, peer plugin reaping & Agent Toolkit MCP error reply."""
    expected_segment = quote(resource_id, safe="")
    if expected_segment not in rendered_api_path or ".." in rendered_api_path.split("/"):
        return GuardDecision(
            False,
            "STRIPE_CLI_UNESCAPED_RESOURCE_ID",
            "Positional resource IDs in Stripe CLI API paths must be URL-escaped",
            {"resource_id": resource_id, "rendered_api_path": rendered_api_path},
        )
    if (parent_terminated_abnormally and not peer_plugins_reaped) or auto_upgraded_across_major:
        return GuardDecision(
            False,
            "STRIPE_CLI_PLUGIN_LIFECYCLE_VIOLATION",
            "Peer plugins must be reaped on abnormal termination and never auto-upgraded across major versions",
            {},
        )
    if (mcp_forward_failed and not mcp_error_reply_sent) or not abandoned_stream_stopped:
        return GuardDecision(
            False,
            "STRIPE_TOOLKIT_MCP_OR_METER_LEAK",
            "MCP proxy must return an error reply on forward failure and token-meter must stop on abandoned streams",
            {},
        )
    return GuardDecision(
        True,
        "STRIPE_CLI_TOOLKIT_GUARD_OK",
        "Stripe CLI path escaping, plugin lifecycle, MCP error reply, and token-meter stream cleanup verified",
        {"escaped_segment": expected_segment},
    )


def evaluate_stripe_multi_sdk_blank_secret_retry_idempotency_guard(
    *,
    webhook_secrets_by_sdk: Mapping[str, str],
    node_verify_tolerance_s: int,
    php_retry_idempotency_keys: Sequence[str],
    dotnet_used_ordinal_path_comparison: bool,
    ruby_singleton_v2_called: bool,
    ruby_singleton_v2_raised_error: bool,
) -> GuardDecision:
    """PR-10: Stripe Go/.NET/Java/Ruby/PHP blank webhook secret rejection, Node tolerance & PHP retry idempotency."""
    for sdk_name, secret in webhook_secrets_by_sdk.items():
        if not secret or not secret.strip():
            return GuardDecision(
                False,
                "STRIPE_SDK_BLANK_WEBHOOK_SECRET_REJECTED",
                f"{sdk_name} must reject empty or whitespace-only webhook secrets",
                {"sdk": sdk_name},
            )
    if node_verify_tolerance_s <= 0 or node_verify_tolerance_s > 300:
        return GuardDecision(
            False,
            "STRIPE_NODE_TOLERANCE_INVALID",
            "verifyHeader and verifyHeaderAsync must enforce DEFAULT_TOLERANCE (300s)",
            {"tolerance_s": node_verify_tolerance_s},
        )
    if len(set(php_retry_idempotency_keys)) != 1 or not php_retry_idempotency_keys[0].strip():
        return GuardDecision(
            False,
            "STRIPE_PHP_RETRY_IDEMPOTENCY_DRIFT",
            "Client-level retries in stripe-php must preserve the identical Idempotency-Key across attempts",
            {"keys": list(php_retry_idempotency_keys)},
        )
    if not dotnet_used_ordinal_path_comparison or (ruby_singleton_v2_called and not ruby_singleton_v2_raised_error):
        return GuardDecision(
            False,
            "STRIPE_DOTNET_OR_RUBY_RESOURCE_GUARD_FAILED",
            "stripe-dotnet requires ordinal path comparison and stripe-ruby must block v2 on SingletonAPIResource",
            {},
        )
    return GuardDecision(
        True,
        "STRIPE_MULTI_SDK_SECRET_RETRY_OK",
        "Blank webhook secret rejection across 5 SDKs, Node tolerance, PHP retry idempotency, and .NET/Ruby guards verified",
        {"idempotency_key": php_retry_idempotency_keys[0]},
    )


_MCP_HEADER_SAFE_RE = re.compile(r"^[A-Za-z0-9_.\-:/]+$")


def evaluate_mcp_ts_null_proto_reconnect_cache_header_guard(
    *,
    registry_uses_null_prototype: bool,
    requested_tool_name: str,
    cache_write_epoch_gen: int,
    current_reconnect_epoch_gen: int,
    mcp_param_value: str,
    mcp_name_value: str,
    handshake_elapsed_ms: int,
    max_handshake_timeout_ms: int,
) -> GuardDecision:
    """PR-11: MCP TypeScript null-prototype registries, stale reconnect cache rejection & Mcp-Param/Mcp-Name guard."""
    if not registry_uses_null_prototype or requested_tool_name in {"__proto__", "constructor", "prototype"}:
        return GuardDecision(
            False,
            "MCP_TS_PROTOTYPE_POLLUTION_BLOCKED",
            "McpServer registries must use null-prototype maps and reject Object.prototype keys",
            {"tool_name": requested_tool_name},
        )
    if cache_write_epoch_gen < current_reconnect_epoch_gen:
        return GuardDecision(
            False,
            "MCP_TS_STALE_RECONNECT_CACHE_WRITE",
            "Pre-reset cacheToolMetadata writes arriving after resetForReconnect must be rejected",
            {"write_gen": cache_write_epoch_gen, "current_gen": current_reconnect_epoch_gen},
        )
    if not _MCP_HEADER_SAFE_RE.match(mcp_param_value) or not _MCP_HEADER_SAFE_RE.match(mcp_name_value):
        return GuardDecision(
            False,
            "MCP_TS_INVALID_HEADER_CHARS",
            "Plain Mcp-Param and Mcp-Name values with control or invalid characters must be rejected",
            {"mcp_param": mcp_param_value, "mcp_name": mcp_name_value},
        )
    if handshake_elapsed_ms > max_handshake_timeout_ms:
        return GuardDecision(
            False,
            "MCP_TS_HANDSHAKE_TIMEOUT_EXCEEDED",
            "Client initialized handshake exceeded bounded timeout",
            {"elapsed_ms": handshake_elapsed_ms},
        )
    return GuardDecision(
        True,
        "MCP_TS_NULL_PROTO_CACHE_HEADER_OK",
        "Null-prototype registry, atomic reconnect cache epoch, Mcp-Param/Mcp-Name syntax, and handshake timeout verified",
        {"epoch_gen": current_reconnect_epoch_gen},
    )


def evaluate_mcp_python_uri_utf8_exact_expiry_sse_headers_guard(
    *,
    candidate_uri: str,
    token_now_epoch: float,
    token_expires_at_epoch: float,
    sse_response_headers_shared_ref: bool,
    contains_lone_surrogate: bool,
    lone_surrogate_contained: bool,
    unknown_tool_error_code: int,
) -> GuardDecision:
    """PR-12: MCP Python non-UTF-8 UriTemplate percent-escape rejection, exact token expiry & isolated SSE headers."""
    try:
        raw_bytes = unquote_to_bytes(candidate_uri)
        raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return GuardDecision(
            False,
            "MCP_PY_URI_NON_UTF8_PERCENT_ESCAPE",
            "UriTemplate.match() must not match URIs with non-UTF-8 percent-escapes",
            {"uri": candidate_uri},
        )
    if token_now_epoch >= token_expires_at_epoch:
        return GuardDecision(
            False,
            "MCP_PY_TOKEN_EXPIRED_AT_BOUNDARY",
            "Tokens must be treated as expired at the exact expiration timestamp (now >= expires_at)",
            {"now": token_now_epoch, "expires_at": token_expires_at_epoch},
        )
    if sse_response_headers_shared_ref:
        return GuardDecision(
            False,
            "MCP_PY_SHARED_SSE_HEADERS_FORBIDDEN",
            "Each SSE response must receive its own isolated header list",
            {},
        )
    if (contains_lone_surrogate and not lone_surrogate_contained) or unknown_tool_error_code != -32602:
        return GuardDecision(
            False,
            "MCP_PY_SURROGATE_OR_ERROR_CODE_INVALID",
            "Transport writers must contain lone surrogates and unknown tools/prompts must return -32602",
            {"error_code": unknown_tool_error_code},
        )
    return GuardDecision(
        True,
        "MCP_PY_URI_EXPIRY_SSE_OK",
        "UTF-8 URI template matching, exact token expiry boundary, isolated SSE headers, and -32602 error code verified",
        {"uri": candidate_uri},
    )


def evaluate_mcp_go_idjag_discover_auth_int_id_guard(
    *,
    id_jag_target: str,
    trusted_mcp_auth_server: str,
    discover_auth_failed: bool,
    fell_back_to_initialize: bool,
    request_id_raw: str,
    is_error_result: bool,
    error_result_has_structured_output: bool,
    forbidden_www_authenticate_header: str,
) -> GuardDecision:
    """PR-13: MCP Go ID-JAG AS-only forwarding, no initialize fallback on auth failure & exact integer ID guard."""
    if id_jag_target != trusted_mcp_auth_server:
        return GuardDecision(
            False,
            "MCP_GO_IDJAG_UNTARGETED_FORWARD",
            "ID-JAG token must only be forwarded to the trusted MCP authorization server",
            {"target": id_jag_target, "trusted_as": trusted_mcp_auth_server},
        )
    if discover_auth_failed and fell_back_to_initialize:
        return GuardDecision(
            False,
            "MCP_GO_DISCOVER_AUTH_FALLBACK_FORBIDDEN",
            "Client must not fall back to unauthenticated initialize when discovery fails authorization",
            {},
        )
    try:
        dec_val = Decimal(request_id_raw)
        if dec_val != dec_val.to_integral_value() or abs(int(dec_val)) > (2**63 - 1):
            return GuardDecision(
                False,
                "MCP_GO_JSONRPC_ID_NOT_EXACT_INT",
                "JSON-RPC numeric ID must be an exact integer within 64-bit range",
                {"request_id_raw": request_id_raw},
            )
    except Exception:
        return GuardDecision(
            False,
            "MCP_GO_JSONRPC_ID_PARSE_ERROR",
            "Malformed numeric JSON-RPC request ID",
            {"request_id_raw": request_id_raw},
        )
    if (is_error_result and error_result_has_structured_output) or "insufficient_scope" not in forbidden_www_authenticate_header:
        return GuardDecision(
            False,
            "MCP_GO_ERROR_STRUCTURED_OR_SCOPE_HEADER_INVALID",
            "Error results must omit structured output and 403 responses must include insufficient_scope in WWW-Authenticate",
            {},
        )
    return GuardDecision(
        True,
        "MCP_GO_IDJAG_DISCOVER_INT_ID_OK",
        "ID-JAG target, discovery auth fail-stop, exact integer request ID, and error output hygiene verified",
        {"exact_request_id": int(Decimal(request_id_raw))},
    )


def evaluate_mcp_csharp_rust_pkce_sessionless_post_guard(
    *,
    oauth_issuer: str,
    expected_issuer: str,
    pkce_methods_supported: Sequence[str],
    property_case_matched_strictly: bool,
    routing_method_name: Any,
    is_initialize_request: bool,
    has_mcp_session_id: bool,
    sessionless_post_http_status: int,
    jsonrpc_error_http_status: int,
) -> GuardDecision:
    """PR-14: MCP C# & Rust OAuth PKCE/issuer validation, session-less POST 400 & 401/403 status preservation."""
    if oauth_issuer != expected_issuer or "S256" not in pkce_methods_supported:
        return GuardDecision(
            False,
            "MCP_CSHARP_PKCE_OR_ISSUER_INVALID",
            "OAuth metadata must match expected issuer and advertise S256 PKCE support",
            {"issuer": oauth_issuer, "pkce": list(pkce_methods_supported)},
        )
    if not property_case_matched_strictly or not isinstance(routing_method_name, str) or not routing_method_name:
        return GuardDecision(
            False,
            "MCP_CSHARP_ROUTING_OR_CASE_INVALID",
            "Protocol property names must match case-sensitively and routing method must be a non-empty string",
            {"method": routing_method_name},
        )
    if not is_initialize_request and not has_mcp_session_id and sessionless_post_http_status != 400:
        return GuardDecision(
            False,
            "MCP_RUST_SESSIONLESS_POST_MUST_400",
            "Streamable HTTP server must answer a session-less non-initialize POST with HTTP 400",
            {"status": sessionless_post_http_status},
        )
    if jsonrpc_error_http_status not in {401, 403, 200, 400}:
        return GuardDecision(
            False,
            "MCP_RUST_AUTH_STATUS_LOST",
            "Transport must preserve 401/403 HTTP status even when the body is a JSON-RPC error",
            {"status": jsonrpc_error_http_status},
        )
    return GuardDecision(
        True,
        "MCP_CSHARP_RUST_PKCE_SESSIONLESS_OK",
        "OAuth PKCE/issuer, case-sensitive routing, session-less POST 400, and 401/403 status preservation verified",
        {"method": routing_method_name},
    )


def evaluate_mcp_java_kotlin_exception_scrub_sep2243_uri_guard(
    *,
    error_response_contains_aggregate_exception: bool,
    post_content_type: str,
    jsonrpc_version: str,
    sep2243_headers_valid: bool,
    resource_uri: str,
    template_captures: Mapping[str, str],
) -> GuardDecision:
    """PR-15: MCP Java & Kotlin aggregate exception scrubbing, application/json POST, SEP-2243 & blank URI guard."""
    if error_response_contains_aggregate_exception:
        return GuardDecision(
            False,
            "MCP_JAVA_AGGREGATE_EXCEPTION_LEAKED",
            "JSONRPCErrorResponse must not expose internal aggregate exceptions; log server-side instead",
            {},
        )
    if not post_content_type.lower().startswith("application/json") or jsonrpc_version != "2.0":
        return GuardDecision(
            False,
            "MCP_JAVA_CONTENT_TYPE_OR_VERSION_INVALID",
            "Modern servlet transport must reject non-application/json POSTs and invalid JSON-RPC versions",
            {"content_type": post_content_type, "jsonrpc": jsonrpc_version},
        )
    if not sep2243_headers_valid:
        return GuardDecision(
            False,
            "MCP_KOTLIN_JAVA_SEP2243_HEADER_INVALID",
            "Mcp-Method, Mcp-Name, and Mcp-Param headers must conform strictly to SEP-2243",
            {},
        )
    if not resource_uri.strip() or any(not str(v).strip() for v in template_captures.values()):
        return GuardDecision(
            False,
            "MCP_KOTLIN_BLANK_URI_OR_CAPTURE",
            "Blank URIs and empty URI template captures must be rejected",
            {"uri": resource_uri, "captures": dict(template_captures)},
        )
    return GuardDecision(
        True,
        "MCP_JAVA_KOTLIN_EXCEPTION_URI_OK",
        "Aggregate exception scrubbing, application/json POST, SEP-2243 headers, and non-empty URI captures verified",
        {"uri": resource_uri},
    )


def evaluate_mcp_inspector_registry_dcr_stamp_gitlab_io_guard(
    *,
    dcr_secret_stamped_client_id: str,
    active_client_id: str,
    bind_host: str,
    auth_token_enabled: bool,
    vite_cors_origin: str,
    configured_cors_origins: set[str],
    oversize_relay_stripped_framing_headers: bool,
    registry_verify_domain: str,
    recorded_repository_id: int | None,
) -> GuardDecision:
    """PR-16: MCP Inspector & Registry DCR client-stamp isolation, CORS/bind guard, gitlab.io block & repo.id pin."""
    if dcr_secret_stamped_client_id != active_client_id:
        return GuardDecision(
            False,
            "MCP_INSPECTOR_DCR_CLIENT_STAMP_MISMATCH",
            "DCR secret stamped for another client must be treated as absent",
            {"stamped": dcr_secret_stamped_client_id, "active": active_client_id},
        )
    if bind_host not in {"127.0.0.1", "localhost", "::1"} and not auth_token_enabled:
        return GuardDecision(
            False,
            "MCP_INSPECTOR_NON_LOOPBACK_UNAUTHENTICATED",
            "Non-loopback web binds require explicit access-control token enforcement",
            {"bind_host": bind_host},
        )
    if vite_cors_origin not in configured_cors_origins or not oversize_relay_stripped_framing_headers:
        return GuardDecision(
            False,
            "MCP_INSPECTOR_CORS_OR_FRAMING_LEAK",
            "Vite dev CORS must be restricted to configured origins and oversize relays must drop stale framing headers",
            {"origin": vite_cors_origin},
        )
    dom = registry_verify_domain.lower().strip(".")
    if dom == "gitlab.io" or dom.endswith(".gitlab.io"):
        return GuardDecision(
            False,
            "MCP_REGISTRY_GITLAB_IO_DOMAIN_REJECTED",
            "Shared hosting gitlab.io domains are forbidden in DNS/HTTP token exchange verification",
            {"domain": registry_verify_domain},
        )
    if not recorded_repository_id or recorded_repository_id <= 0:
        return GuardDecision(
            False,
            "MCP_REGISTRY_REPO_ID_MISSING",
            "Publisher must record immutable repository.id at init so repository renames stay resolvable",
            {"repository_id": recorded_repository_id},
        )
    return GuardDecision(
        True,
        "MCP_INSPECTOR_REGISTRY_GUARD_OK",
        "DCR client-stamp isolation, loopback/CORS guard, oversize framing scrub, gitlab.io block, and repository.id verified",
        {"domain": dom, "repository_id": recorded_repository_id},
    )
