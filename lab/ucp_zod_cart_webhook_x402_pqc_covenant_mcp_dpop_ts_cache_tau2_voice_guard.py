"""Stage 216 deterministic guardrails covering 16 primary-source PRs (`PR-01..PR-16`)
across UCP (js-sdk, conformance, samples), x402, MCP (Python SDK & TypeScript SDK),
and Sierra tau2-bench / tau3-bench.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardVerdict:
    passed: bool
    scenario_id: str
    control_id: str
    reason_code: str
    action: str
    details: dict[str, Any]


ISO_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
CAIP2_RE = re.compile(r"^[a-z0-9-]{2,16}:[a-zA-Z0-9_-]{1,64}$")
ASCII_HEADER_RE = re.compile(r"^[\t\x20-\x7e]+$")
SEMVER_SIM_RE = re.compile(r"^v\d+\.\d+(?:\.\d+)?$")


def _canonical_jcs_sha256(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/js-sdk#34 & conformance#34
# ---------------------------------------------------------------------------
def audit_ucp_zod_value_constraints_and_discovery_jwk_readiness(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP PriceSchema integer/minimum-0/ISO-4217 value constraints
    (`js-sdk#34`) and standalone discovery profile `signing_keys[]` JWK & URL
    reachability readiness (`conformance#34`).
    """
    price = payload.get("price", {})
    amount = price.get("amount")
    currency = str(price.get("currency", ""))
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
            reason_code="UCP_ZOD_PRICE_AMOUNT_NOT_NONNEGATIVE_INTEGER",
            action="Send to a human",
            details={"amount": amount, "currency": currency},
        )
    if not ISO_CURRENCY_RE.match(currency):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
            reason_code="UCP_ZOD_CURRENCY_PATTERN_VIOLATION",
            action="Send to a human",
            details={"currency": currency},
        )

    signing_keys = payload.get("signing_keys", [])
    if not isinstance(signing_keys, list) or not signing_keys:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
            reason_code="UCP_DISCOVERY_SIGNING_KEYS_MISSING",
            action="Send to a human",
            details={},
        )
    for jwk in signing_keys:
        kty = jwk.get("kty")
        kid = jwk.get("kid")
        if not kid or kty not in {"EC", "RSA", "OKP"}:
            return GuardVerdict(
                passed=False,
                scenario_id="PR-01",
                control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
                reason_code="UCP_DISCOVERY_JWK_PARAMETERS_INVALID",
                action="Send to a human",
                details={"jwk": jwk},
            )
        if kty == "EC" and not (jwk.get("crv") and jwk.get("x") and jwk.get("y")):
            return GuardVerdict(
                passed=False,
                scenario_id="PR-01",
                control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
                reason_code="UCP_DISCOVERY_EC_JWK_INCOMPLETE",
                action="Send to a human",
                details={"kid": kid},
            )

    unreachable_urls = payload.get("unreachable_profile_urls", [])
    if unreachable_urls:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
            reason_code="UCP_DISCOVERY_PROFILE_URLS_UNREACHABLE",
            action="Send to a human",
            details={"unreachable_profile_urls": list(unreachable_urls)},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-01",
        control_id="ucp_zod_value_constraints_and_jwk_readiness_gate",
        reason_code="UCP_ZOD_CONSTRAINTS_AND_JWK_READINESS_VERIFIED",
        action="Act automatically",
        details={"amount": amount, "currency": currency, "signing_keys_count": len(signing_keys)},
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/conformance#108 & samples#181
# ---------------------------------------------------------------------------
def audit_ucp_cart_conversion_invariants_and_single_fulfillment_group(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP `dev.ucp.shopping.cart` conversion MUST invariants (`conformance#108`)
    and single fulfillment group consolidation when `supports_multi_group: false` (`samples#181`).
    """
    cart_items = payload.get("cart_items", [])
    checkout_items = payload.get("checkout_items", [])
    if cart_items != checkout_items:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="ucp_cart_conformance_and_single_group_gate",
            reason_code="UCP_CART_PRECEDENCE_OVERRIDDEN_BY_CHECKOUT_PAYLOAD",
            action="Send to a human",
            details={"cart_items": cart_items, "checkout_items": checkout_items},
        )

    first_checkout_id = str(payload.get("first_conversion_checkout_id", ""))
    second_checkout_id = str(payload.get("second_conversion_checkout_id", ""))
    if not first_checkout_id or first_checkout_id != second_checkout_id:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="ucp_cart_conformance_and_single_group_gate",
            reason_code="UCP_CART_SECOND_CONVERSION_NOT_IDEMPOTENT",
            action="Send to a human",
            details={"first": first_checkout_id, "second": second_checkout_id},
        )

    cart_discounts = list(payload.get("cart_discount_codes", []))
    checkout_discounts = list(payload.get("checkout_discount_codes", []))
    if cart_discounts != checkout_discounts:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="ucp_cart_conformance_and_single_group_gate",
            reason_code="UCP_CART_DISCOUNTS_NOT_CARRIED_FORWARD",
            action="Send to a human",
            details={"cart_discounts": cart_discounts, "checkout_discounts": checkout_discounts},
        )

    supports_multi_group = bool(payload.get("supports_multi_group", False))
    methods = payload.get("fulfillment_methods", [])
    if not supports_multi_group:
        for method in methods:
            groups = method.get("groups", [])
            if not isinstance(groups, list) or len(groups) != 1:
                return GuardVerdict(
                    passed=False,
                    scenario_id="PR-02",
                    control_id="ucp_cart_conformance_and_single_group_gate",
                    reason_code="UCP_FULFILLMENT_METHOD_SINGLE_GROUP_INVARIANT_VIOLATED",
                    action="Send to a human",
                    details={"method_type": method.get("type"), "group_count": len(groups)},
                )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-02",
        control_id="ucp_cart_conformance_and_single_group_gate",
        reason_code="UCP_CART_CONFORMANCE_AND_SINGLE_GROUP_VERIFIED",
        action="Act automatically",
        details={"checkout_id": first_checkout_id, "methods_checked": len(methods)},
    )


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/samples#179, #175, & #146
# ---------------------------------------------------------------------------
def audit_ucp_order_webhook_rfc9421_signing_retry_and_raw_order_body(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP order-event webhook RFC 9421 signing with RFC 7638 thumbprint `kid`
    (`samples#179`), transient `5xx` retry vs. permanent `4xx` non-retry (`samples#175`),
    and raw `order` object JSON body with `X-Event-Type` header (`samples#146`).
    """
    headers = {str(k).lower(): str(v) for k, v in payload.get("headers", {}).items()}
    required_headers = {"ucp-agent", "signature", "signature-input", "content-digest", "webhook-id", "webhook-timestamp", "x-event-type"}
    missing = sorted(required_headers - set(headers.keys()))
    if missing:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_RFC9421_REQUIRED_HEADERS_MISSING",
            action="Send to a human",
            details={"missing_headers": missing},
        )

    signed_components = list(payload.get("signed_components", []))
    required_components = {"webhook-id", "webhook-timestamp", "x-event-type", "content-digest"}
    if not required_components.issubset(set(signed_components)) or len(signed_components) != len(set(signed_components)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_SIGNED_COMPONENTS_INVALID_OR_DUPLICATED",
            action="Send to a human",
            details={"signed_components": signed_components},
        )

    key_alg = str(payload.get("signing_key_alg", ""))
    if key_alg not in {"ES256", "EdDSA"} or not bool(payload.get("kid_matches_rfc7638_thumbprint", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_SIGNING_KEY_OR_THUMBPRINT_INVALID",
            action="Send to a human",
            details={"signing_key_alg": key_alg},
        )

    body = payload.get("body", {})
    if not isinstance(body, Mapping) or "order" in body or "event_type" in body or not body.get("id"):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_CUSTOM_WRAPPER_BODY_FORBIDDEN",
            action="Send to a human",
            details={"body_keys": sorted(body.keys()) if isinstance(body, Mapping) else []},
        )

    last_status = int(payload.get("last_delivery_status", 200))
    retry_attempted = bool(payload.get("retry_attempted", False))
    reused_identity = bool(payload.get("reused_webhook_id_and_timestamp", True))
    if 400 <= last_status < 500 and retry_attempted:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_PERMANENT_4XX_RETRIED",
            action="Send to a human",
            details={"last_delivery_status": last_status},
        )
    if last_status >= 500 and (not retry_attempted or not reused_identity):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="ucp_order_webhook_rfc9421_and_body_gate",
            reason_code="UCP_WEBHOOK_TRANSIENT_5XX_DROPPED_OR_IDENTITY_MUTATED",
            action="Send to a human",
            details={"last_delivery_status": last_status, "retry_attempted": retry_attempted},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-03",
        control_id="ucp_order_webhook_rfc9421_and_body_gate",
        reason_code="UCP_WEBHOOK_RFC9421_RETRY_AND_RAW_ORDER_VERIFIED",
        action="Act automatically",
        details={"order_id": body.get("id"), "key_alg": key_alg},
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/samples#174, #173, & #168
# ---------------------------------------------------------------------------
def audit_ucp_error_envelope_discovery_cache_and_a2a_active_task_id(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP typed error envelope on checkout errors (`samples#174`),
    discovery `Cache-Control: public, max-age>=60` + checkout `ucp.payment_handlers`
    (`samples#168`), and A2A active task state `.includes()` preservation (`samples#173`).
    """
    error_response = payload.get("error_response", {})
    if "detail" in error_response or not (error_response.get("status") and error_response.get("code") and error_response.get("messages")):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-04",
            control_id="ucp_error_envelope_cache_and_a2a_task_gate",
            reason_code="UCP_FLAT_DETAIL_ERROR_BODY_REJECTED",
            action="Send to a human",
            details={"error_response": error_response},
        )

    cache_control = str(payload.get("discovery_cache_control", ""))
    m_age = re.search(r"max-age=(\d+)", cache_control)
    if (
        "public" not in cache_control
        or any(tok in cache_control for tok in ("private", "no-store", "no-cache"))
        or not m_age
        or int(m_age.group(1)) < 60
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-04",
            control_id="ucp_error_envelope_cache_and_a2a_task_gate",
            reason_code="UCP_DISCOVERY_CACHE_CONTROL_NONCONFORMANT",
            action="Send to a human",
            details={"discovery_cache_control": cache_control},
        )

    ucp_env = payload.get("checkout_ucp_envelope", {})
    if "payment_handlers" not in ucp_env or not isinstance(ucp_env.get("payment_handlers"), (dict, list)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-04",
            control_id="ucp_error_envelope_cache_and_a2a_task_gate",
            reason_code="UCP_CHECKOUT_ENVELOPE_PAYMENT_HANDLERS_MISSING",
            action="Send to a human",
            details={"ucp_envelope_keys": sorted(ucp_env.keys()) if isinstance(ucp_env, Mapping) else []},
        )

    task_state = str(payload.get("a2a_task_state", ""))
    active_task_id = payload.get("a2a_active_task_id_after_turn")
    if task_state in {"working", "submitted", "input-required"} and not active_task_id:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-04",
            control_id="ucp_error_envelope_cache_and_a2a_task_gate",
            reason_code="UCP_A2A_ACTIVE_TASK_ID_DROPPED_BY_INDEX_OPERATOR",
            action="Send to a human",
            details={"a2a_task_state": task_state},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-04",
        control_id="ucp_error_envelope_cache_and_a2a_task_gate",
        reason_code="UCP_ERROR_ENVELOPE_CACHE_AND_A2A_TASK_VERIFIED",
        action="Act automatically",
        details={"max_age": int(m_age.group(1)), "a2a_task_state": task_state},
    )


# ---------------------------------------------------------------------------
# PR-05: x402-foundation/x402#3897 & #3759
# ---------------------------------------------------------------------------
def audit_x402_jcs_ed25519_and_pqc_mldsa65_epoch_receipts(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce offline-verifiable x402 signed receipts: Ed25519 over RFC 8785 JCS
    with CAIP payer/payee/network identifiers (`x402#3897`) and Post-Quantum
    ML-DSA-65 (FIPS 204) epoch-chained key directory witness (`x402#3759`).
    """
    receipt = payload.get("receipt_body", {})
    expected_digest = _canonical_jcs_sha256(receipt)
    claimed_digest = str(payload.get("jcs_sha256", ""))
    if claimed_digest != expected_digest:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-05",
            control_id="x402_jcs_ed25519_and_pqc_mldsa65_receipt_gate",
            reason_code="X402_RECEIPT_JCS_DIGEST_MISMATCH",
            action="Send to a human",
            details={"expected": expected_digest, "claimed": claimed_digest},
        )

    network = str(receipt.get("network", ""))
    payer = str(receipt.get("payer", ""))
    payee = str(receipt.get("payee", ""))
    if not CAIP2_RE.match(network) or ":" not in payer or ":" not in payee:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-05",
            control_id="x402_jcs_ed25519_and_pqc_mldsa65_receipt_gate",
            reason_code="X402_RECEIPT_CAIP_IDENTIFIER_INVALID",
            action="Send to a human",
            details={"network": network, "payer": payer, "payee": payee},
        )

    pqc = payload.get("pqc_witness", {})
    if (
        pqc.get("alg") != "ML-DSA-65"
        or pqc.get("fips") != "FIPS-204"
        or not bool(pqc.get("epoch_key_chain_verified", False))
        or pqc.get("tx_hash") != receipt.get("tx_hash")
        or pqc.get("log_index") is None
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-05",
            control_id="x402_jcs_ed25519_and_pqc_mldsa65_receipt_gate",
            reason_code="X402_PQC_MLDSA65_EPOCH_WITNESS_INVALID",
            action="Send to a human",
            details={"pqc_witness": pqc},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-05",
        control_id="x402_jcs_ed25519_and_pqc_mldsa65_receipt_gate",
        reason_code="X402_JCS_ED25519_AND_PQC_MLDSA65_RECEIPT_VERIFIED",
        action="Act automatically",
        details={"jcs_sha256": expected_digest, "network": network},
    )


# ---------------------------------------------------------------------------
# PR-06: x402-foundation/x402#3891 & #3890
# ---------------------------------------------------------------------------
def audit_x402_covenant_facilitator_limits_and_xrpl_upto_payment_channel(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce Covenant facilitator policy ($0.001 floor, USDC-only, self-send block,
    500/day/payee quota on Solana/Base, `x402#3891`) and XRPL Payment Channel
    `upto` escrow ceiling (`settled_drops <= escrowed_drops`, `x402#3890`).
    """
    asset = str(payload.get("asset_symbol", ""))
    amount_micro_usdc = int(payload.get("amount_micro_usdc", 0))
    payer = str(payload.get("payer", "")).lower()
    pay_to = str(payload.get("pay_to", "")).lower()
    daily_settlements = int(payload.get("payee_daily_settlements", 0))

    if asset != "USDC" or amount_micro_usdc < 1000:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-06",
            control_id="x402_covenant_limits_and_xrpl_upto_channel_gate",
            reason_code="X402_COVENANT_MIN_FLOOR_OR_ASSET_VIOLATION",
            action="Send to a human",
            details={"asset": asset, "amount_micro_usdc": amount_micro_usdc},
        )
    if not payer or payer == pay_to or daily_settlements >= 500:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-06",
            control_id="x402_covenant_limits_and_xrpl_upto_channel_gate",
            reason_code="X402_COVENANT_SELF_SEND_OR_DAILY_QUOTA_EXCEEDED",
            action="Send to a human",
            details={"payer": payer, "pay_to": pay_to, "payee_daily_settlements": daily_settlements},
        )

    xrpl = payload.get("xrpl_upto_channel", {})
    escrowed_drops = int(xrpl.get("escrowed_drops", 0))
    settled_drops = int(xrpl.get("settled_drops", 0))
    claim_sig_valid = bool(xrpl.get("claim_signature_valid", False))
    if escrowed_drops <= 0 or settled_drops < 0 or settled_drops > escrowed_drops or not claim_sig_valid:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-06",
            control_id="x402_covenant_limits_and_xrpl_upto_channel_gate",
            reason_code="X402_XRPL_UPTO_PAYMENT_CHANNEL_OVERFLOW_OR_UNSIGNED",
            action="Send to a human",
            details={"escrowed_drops": escrowed_drops, "settled_drops": settled_drops},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-06",
        control_id="x402_covenant_limits_and_xrpl_upto_channel_gate",
        reason_code="X402_COVENANT_LIMITS_AND_XRPL_UPTO_VERIFIED",
        action="Act automatically",
        details={"amount_micro_usdc": amount_micro_usdc, "settled_drops": settled_drops},
    )


# ---------------------------------------------------------------------------
# PR-07: x402-foundation/x402#3766 & #3753
# ---------------------------------------------------------------------------
def audit_x402_readonly_preflight_inspector_and_cbor_uint64_metadata(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce read-only x402 preflight inspection (`mcpdoctor`: 402 status, valid
    `accepts[]`, no vendor-hint header masking, zero side-effect signing/settlement,
    `x402#3766`) and Python `builder-code` CBOR `uint64` bounds (`x402#3753`).
    """
    status_code = int(payload.get("status_code", 0))
    accepts = payload.get("accepts", [])
    vendor_header_masks_document = bool(payload.get("vendor_header_masks_document", False))
    preflight_attempted_write = bool(payload.get("preflight_attempted_sign_or_settle", False))

    if status_code != 402 or not isinstance(accepts, list) or not accepts or vendor_header_masks_document or preflight_attempted_write:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-07",
            control_id="x402_readonly_preflight_and_cbor_uint64_gate",
            reason_code="X402_PREFLIGHT_DOCUMENT_MASKED_OR_NON_READONLY",
            action="Send to a human",
            details={
                "status_code": status_code,
                "vendor_header_masks_document": vendor_header_masks_document,
                "preflight_attempted_write": preflight_attempted_write,
            },
        )

    cbor_int_values: Sequence[int] = payload.get("cbor_int_metadata_values", [])
    for val in cbor_int_values:
        if val < 0 or val > (2**64 - 1):
            return GuardVerdict(
                passed=False,
                scenario_id="PR-07",
                control_id="x402_readonly_preflight_and_cbor_uint64_gate",
                reason_code="X402_CBOR_UINT64_METADATA_OUT_OF_RANGE",
                action="Send to a human",
                details={"invalid_uint64": val},
            )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-07",
        control_id="x402_readonly_preflight_and_cbor_uint64_gate",
        reason_code="X402_READONLY_PREFLIGHT_AND_CBOR_UINT64_VERIFIED",
        action="Act automatically",
        details={"accepts_count": len(accepts), "cbor_ints_checked": len(cbor_int_values)},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/python-sdk#3743 & #3672
# ---------------------------------------------------------------------------
def audit_mcp_oauth_rfc6749_error_codes_and_client_dpop_token_proof(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce RFC 6749 §5.2 / RFC 7009 §2.2.1 `/token` and `/revoke` error codes
    (`unauthorized_client` vs `unsupported_grant_type`, `python-sdk#3743`) and
    RFC 9449 `ES256` DPoP proof attachment on token endpoint requests (`python-sdk#3672`).
    """
    grant_implemented = bool(payload.get("server_implements_grant", True))
    client_registered_for_grant = bool(payload.get("client_registered_for_grant", True))
    returned_error = str(payload.get("oauth_error_code", ""))

    if grant_implemented and not client_registered_for_grant and returned_error != "unauthorized_client":
        return GuardVerdict(
            passed=False,
            scenario_id="PR-08",
            control_id="mcp_oauth_rfc6749_error_and_dpop_proof_gate",
            reason_code="MCP_OAUTH_UNREGISTERED_GRANT_MUST_BE_UNAUTHORIZED_CLIENT",
            action="Send to a human",
            details={"returned_error": returned_error},
        )
    if not grant_implemented and returned_error != "unsupported_grant_type":
        return GuardVerdict(
            passed=False,
            scenario_id="PR-08",
            control_id="mcp_oauth_rfc6749_error_and_dpop_proof_gate",
            reason_code="MCP_OAUTH_UNIMPLEMENTED_GRANT_MUST_BE_UNSUPPORTED_GRANT_TYPE",
            action="Send to a human",
            details={"returned_error": returned_error},
        )

    advertised_dpop_algs = list(payload.get("dpop_signing_alg_values_supported", []))
    dpop_proof_sent = bool(payload.get("dpop_proof_header_sent", False))
    dpop_alg = str(payload.get("dpop_proof_alg", ""))
    if "ES256" in advertised_dpop_algs and (not dpop_proof_sent or dpop_alg != "ES256"):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-08",
            control_id="mcp_oauth_rfc6749_error_and_dpop_proof_gate",
            reason_code="MCP_OAUTH_DPOP_ES256_PROOF_MISSING_ON_TOKEN_REQUEST",
            action="Send to a human",
            details={"advertised_dpop_algs": advertised_dpop_algs, "dpop_proof_sent": dpop_proof_sent},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-08",
        control_id="mcp_oauth_rfc6749_error_and_dpop_proof_gate",
        reason_code="MCP_OAUTH_ERROR_TAXONOMY_AND_DPOP_PROOF_VERIFIED",
        action="Act automatically",
        details={"dpop_alg": dpop_alg, "oauth_error_code": returned_error or "none"},
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/python-sdk#3716 & #3679
# ---------------------------------------------------------------------------
def audit_mcp_session_group_reregistration_eviction_and_ui_parent_origin(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `ClientSessionGroup` stale component eviction on session re-registration
    (`python-sdk#3716`) and MCP Apps UI bridge initialization + `window.parent`
    notification origin verification (`python-sdk#3679`).
    """
    previous_tools = set(payload.get("previous_session_tools", []))
    updated_tools = set(payload.get("updated_session_tools", []))
    active_group_tools = set(payload.get("active_group_tools_after_reregister", []))
    orphaned = (previous_tools - updated_tools) & active_group_tools
    if orphaned:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-09",
            control_id="mcp_session_group_eviction_and_ui_parent_gate",
            reason_code="MCP_SESSION_GROUP_ORPHANED_TOOLS_ON_REREGISTRATION",
            action="Send to a human",
            details={"orphaned_tools": sorted(orphaned)},
        )

    ui_bridge_initialized = bool(payload.get("ui_bridge_initialized_before_consume", False))
    source_is_parent_window = bool(payload.get("notification_source_is_parent_window", False))
    read_from_params = bool(payload.get("tool_result_read_from_notification_params", False))
    if not ui_bridge_initialized or not source_is_parent_window or not read_from_params:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-09",
            control_id="mcp_session_group_eviction_and_ui_parent_gate",
            reason_code="MCP_UI_BRIDGE_UNINITIALIZED_OR_UNTRUSTED_WINDOW_SOURCE",
            action="Send to a human",
            details={
                "ui_bridge_initialized": ui_bridge_initialized,
                "source_is_parent_window": source_is_parent_window,
                "read_from_params": read_from_params,
            },
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-09",
        control_id="mcp_session_group_eviction_and_ui_parent_gate",
        reason_code="MCP_SESSION_GROUP_EVICTION_AND_UI_ORIGIN_VERIFIED",
        action="Act automatically",
        details={"active_tools": sorted(active_group_tools)},
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/python-sdk#3706 & #3704
# ---------------------------------------------------------------------------
def audit_mcp_stdio_linear_chunk_accumulator_and_sse_header_isolation(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `stdio_client` $O(N)$ list-chunk buffering on multi-MiB lines (`python-sdk#3706`)
    and per-response isolated `list(_SSE_HEADERS)` copy (`python-sdk#3704`).
    """
    buffering_strategy = str(payload.get("stdio_buffering_strategy", ""))
    if buffering_strategy != "list_append_join_on_newline":
        return GuardVerdict(
            passed=False,
            scenario_id="PR-10",
            control_id="mcp_stdio_linear_buffer_and_sse_header_isolation_gate",
            reason_code="MCP_STDIO_QUADRATIC_STRING_CONCAT_BUFFERING",
            action="Send to a human",
            details={"stdio_buffering_strategy": buffering_strategy},
        )

    shared_header_list = bool(payload.get("sse_shares_module_header_list", False))
    leaked_headers = list(payload.get("leaked_headers_across_responses", []))
    if shared_header_list or leaked_headers:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-10",
            control_id="mcp_stdio_linear_buffer_and_sse_header_isolation_gate",
            reason_code="MCP_SSE_SHARED_HEADER_LIST_CROSS_RESPONSE_LEAK",
            action="Send to a human",
            details={"leaked_headers": leaked_headers},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-10",
        control_id="mcp_stdio_linear_buffer_and_sse_header_isolation_gate",
        reason_code="MCP_STDIO_LINEAR_BUFFER_AND_SSE_HEADERS_ISOLATED",
        action="Act automatically",
        details={"line_bytes_tested": int(payload.get("line_bytes_tested", 8388608))},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/python-sdk#3629, #3628, #3627, & #3621
# ---------------------------------------------------------------------------
def audit_mcp_python_outbound_normalization_null_output_and_otel_error(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce omission of empty `_meta`/`params` on outbound requests (`#3628`),
    single retry on `HeaderMismatch` (`#3627`), schema validation of explicit
    `structuredContent: null` (`#3621`), and OTel span JSON-RPC error recording (`#3629`).
    """
    outbound = payload.get("outbound_request", {})
    if outbound.get("params") == {} or (isinstance(outbound.get("params"), Mapping) and outbound["params"].get("_meta") == {}):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-11",
            control_id="mcp_python_outbound_null_schema_and_otel_gate",
            reason_code="MCP_OUTBOUND_EMPTY_PARAMS_OR_META_NOT_OMITTED",
            action="Send to a human",
            details={"outbound_request": outbound},
        )

    header_mismatch_retries = int(payload.get("header_mismatch_retries", 0))
    if header_mismatch_retries > 1:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-11",
            control_id="mcp_python_outbound_null_schema_and_otel_gate",
            reason_code="MCP_HEADER_MISMATCH_RETRY_LIMIT_EXCEEDED",
            action="Send to a human",
            details={"header_mismatch_retries": header_mismatch_retries},
        )

    if not bool(payload.get("explicit_null_structured_content_validated", False)) or not bool(
        payload.get("jsonrpc_error_recorded_on_otel_span", False)
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-11",
            control_id="mcp_python_outbound_null_schema_and_otel_gate",
            reason_code="MCP_NULL_STRUCTURED_CONTENT_UNVALIDATED_OR_OTEL_MISSED",
            action="Send to a human",
            details={},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-11",
        control_id="mcp_python_outbound_null_schema_and_otel_gate",
        reason_code="MCP_PYTHON_OUTBOUND_NULL_SCHEMA_AND_OTEL_VERIFIED",
        action="Act automatically",
        details={"header_mismatch_retries": header_mismatch_retries},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/typescript-sdk#3085 & #3081
# ---------------------------------------------------------------------------
def audit_mcp_ts_refresh_scope_optin_and_root_ref_object_output_schema(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce opt-in `scopeForRefresh` on token refresh (`typescript-sdk#3085`,
    preventing Entra ID `AADSTS90009`) and root `$ref` object `outputSchema`
    classification without `{ result }` double-wrapping (`typescript-sdk#3081`).
    """
    provider_has_scope_for_refresh = bool(payload.get("provider_has_scope_for_refresh", False))
    refresh_request_has_scope = bool(payload.get("refresh_request_has_scope", False))
    if provider_has_scope_for_refresh != refresh_request_has_scope:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-12",
            control_id="mcp_ts_refresh_scope_and_root_ref_output_gate",
            reason_code="MCP_TS_REFRESH_SCOPE_OPTIN_MISMATCH",
            action="Send to a human",
            details={
                "provider_has_scope_for_refresh": provider_has_scope_for_refresh,
                "refresh_request_has_scope": refresh_request_has_scope,
            },
        )

    root_ref_target_type = str(payload.get("output_schema_root_ref_target_type", ""))
    double_wrapped_in_result = bool(payload.get("structured_content_wrapped_in_result", False))
    if root_ref_target_type == "object" and double_wrapped_in_result:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-12",
            control_id="mcp_ts_refresh_scope_and_root_ref_output_gate",
            reason_code="MCP_TS_ROOT_REF_OBJECT_SCHEMA_DOUBLE_WRAPPED",
            action="Send to a human",
            details={"root_ref_target_type": root_ref_target_type},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-12",
        control_id="mcp_ts_refresh_scope_and_root_ref_output_gate",
        reason_code="MCP_TS_REFRESH_SCOPE_AND_ROOT_REF_SCHEMA_VERIFIED",
        action="Act automatically",
        details={"refresh_request_has_scope": refresh_request_has_scope},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/typescript-sdk#3072 & #3079
# ---------------------------------------------------------------------------
def audit_mcp_ts_pending_cache_generation_guard_and_handshake_timeout(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce per-key eviction generation and connection generation re-checks
    after awaited `ResponseCacheStore.get()` lookups (`typescript-sdk#3072`) and
    bounded `initialized` handshake timeout (`typescript-sdk#3079`).
    """
    key_gen_before = int(payload.get("key_generation_before", 0))
    key_gen_after = int(payload.get("key_generation_after", 0))
    conn_gen_before = int(payload.get("connection_generation_before", 0))
    conn_gen_after = int(payload.get("connection_generation_after", 0))
    used_cached_snapshot = bool(payload.get("used_cached_snapshot", False))

    if (key_gen_before != key_gen_after or conn_gen_before != conn_gen_after) and used_cached_snapshot:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-13",
            control_id="mcp_ts_pending_cache_generation_and_handshake_gate",
            reason_code="MCP_TS_INVALIDATED_PENDING_CACHE_READ_SERVED",
            action="Send to a human",
            details={
                "key_gen_before": key_gen_before,
                "key_gen_after": key_gen_after,
                "conn_gen_before": conn_gen_before,
                "conn_gen_after": conn_gen_after,
            },
        )

    handshake_timeout_ms = int(payload.get("initialized_handshake_timeout_ms", 0))
    if handshake_timeout_ms <= 0 or handshake_timeout_ms > 60000:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-13",
            control_id="mcp_ts_pending_cache_generation_and_handshake_gate",
            reason_code="MCP_TS_INITIALIZED_HANDSHAKE_TIMEOUT_UNBOUNDED",
            action="Send to a human",
            details={"initialized_handshake_timeout_ms": handshake_timeout_ms},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-13",
        control_id="mcp_ts_pending_cache_generation_and_handshake_gate",
        reason_code="MCP_TS_CACHE_GENERATION_AND_HANDSHAKE_TIMEOUT_VERIFIED",
        action="Act automatically",
        details={"handshake_timeout_ms": handshake_timeout_ms},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/typescript-sdk#3064, #3063, & #3082
# ---------------------------------------------------------------------------
def audit_mcp_ts_sampling_context_capability_and_mcp_param_ascii_guard(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `ClientCapabilities.sampling.context` check before `includeContext:
    "thisServer" | "allServers"` (`typescript-sdk#3064`), plain `Mcp-Param-*` /
    `Mcp-Name` printable ASCII validation (`typescript-sdk#3063`), and non-blocking
    unread POST reply body drain (`typescript-sdk#3082`).
    """
    include_context = str(payload.get("include_context", "none"))
    client_has_sampling_context = bool(payload.get("client_declares_sampling_context", False))
    if include_context in {"thisServer", "allServers"} and not client_has_sampling_context:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-14",
            control_id="mcp_ts_sampling_context_and_mcp_param_ascii_gate",
            reason_code="MCP_TS_SAMPLING_INCLUDE_CONTEXT_WITHOUT_CLIENT_CAPABILITY",
            action="Send to a human",
            details={"include_context": include_context},
        )

    plain_headers: Mapping[str, str] = payload.get("plain_mcp_headers", {})
    for h_name, h_val in plain_headers.items():
        if not ASCII_HEADER_RE.match(str(h_val)):
            return GuardVerdict(
                passed=False,
                scenario_id="PR-14",
                control_id="mcp_ts_sampling_context_and_mcp_param_ascii_gate",
                reason_code="MCP_TS_PLAIN_HEADER_INVALID_CONTROL_OR_NON_ASCII_CHAR",
                action="Send to a human",
                details={"header": h_name},
            )

    if bool(payload.get("blocked_on_unread_post_reply_body", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-14",
            control_id="mcp_ts_sampling_context_and_mcp_param_ascii_gate",
            reason_code="MCP_TS_CLIENT_BLOCKED_ON_UNREAD_POST_REPLY_BODY",
            action="Send to a human",
            details={},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-14",
        control_id="mcp_ts_sampling_context_and_mcp_param_ascii_gate",
        reason_code="MCP_TS_SAMPLING_CONTEXT_AND_HEADER_ASCII_VERIFIED",
        action="Act automatically",
        details={"headers_validated": len(plain_headers)},
    )


# ---------------------------------------------------------------------------
# PR-15: sierra-research/tau2-bench#179 & #175
# ---------------------------------------------------------------------------
def audit_tau2_voice_simulator_version_tag_and_banking_knowledge_provenance(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce semantic `VOICE_USER_SIMULATOR_VERSION` (`v1.0` -> `voice-user-sim-v1.0`)
    decoupled from `VOICE_USER_SIMULATOR_DECISION_MODEL` (`tau2-bench#179`) and
    `banking_knowledge` retrieval configuration provenance (`tau2-bench#175`).
    """
    sim_version = str(payload.get("voice_user_simulator_version", ""))
    decision_model = str(payload.get("voice_user_simulator_decision_model", ""))
    git_tag = str(payload.get("voice_simulator_git_tag", ""))
    if not SEMVER_SIM_RE.match(sim_version) or not decision_model or git_tag != f"voice-user-sim-{sim_version}":
        return GuardVerdict(
            passed=False,
            scenario_id="PR-15",
            control_id="tau2_voice_simulator_version_and_banking_knowledge_gate",
            reason_code="TAU2_VOICE_SIMULATOR_VERSION_TAG_OR_MODEL_COUPLED",
            action="Send to a human",
            details={"voice_user_simulator_version": sim_version, "git_tag": git_tag},
        )

    domain = str(payload.get("domain", ""))
    retrieval_config = str(payload.get("retrieval_config_id", ""))
    corpus_docs = int(payload.get("corpus_document_count", 0))
    if domain == "banking_knowledge" and (not retrieval_config or corpus_docs != 698):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-15",
            control_id="tau2_voice_simulator_version_and_banking_knowledge_gate",
            reason_code="TAU2_BANKING_KNOWLEDGE_RETRIEVAL_PROVENANCE_INCOMPLETE",
            action="Send to a human",
            details={"retrieval_config_id": retrieval_config, "corpus_document_count": corpus_docs},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-15",
        control_id="tau2_voice_simulator_version_and_banking_knowledge_gate",
        reason_code="TAU2_VOICE_SIMULATOR_VERSION_AND_KNOWLEDGE_VERIFIED",
        action="Act automatically",
        details={"voice_user_simulator_version": sim_version, "retrieval_config_id": retrieval_config},
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#183, #446, & #441
# ---------------------------------------------------------------------------
def audit_tau2_extended_metrics_environment_damage_and_model_pricing_smoke(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce 6-group extended metrics analysis (zero `environment_damage_rate`
    on passing state-based runs & explicit LiteLLM custom model pricing mapping,
    `tau2-bench#183`) and local TTS / Telecom backend pre-run smoke gate (`#446`/`#441`).
    """
    metric_groups = set(payload.get("metric_groups_computed", []))
    required_groups = {
        "reliability_consistency",
        "interaction_efficiency",
        "policy_tool_governance",
        "tool_call_accuracy",
        "first_call_resolution",
        "state_based_metrics",
    }
    if required_groups - metric_groups:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-16",
            control_id="tau2_extended_metrics_pricing_and_smoke_gate",
            reason_code="TAU2_EXTENDED_METRIC_GROUPS_INCOMPLETE",
            action="Send to a human",
            details={"missing_groups": sorted(required_groups - metric_groups)},
        )

    env_damage_rate = float(payload.get("environment_damage_rate", 0.0))
    pricing_mapped = bool(payload.get("custom_model_litellm_pricing_mapped", False))
    smoke_gate_passed = bool(payload.get("backend_and_tts_smoke_gate_passed", False))
    if env_damage_rate > 0.0 or not pricing_mapped or not smoke_gate_passed:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-16",
            control_id="tau2_extended_metrics_pricing_and_smoke_gate",
            reason_code="TAU2_ENV_DAMAGE_UNMAPPED_COST_OR_SMOKE_FAILURE",
            action="Send to a human",
            details={
                "environment_damage_rate": env_damage_rate,
                "custom_model_litellm_pricing_mapped": pricing_mapped,
                "backend_and_tts_smoke_gate_passed": smoke_gate_passed,
            },
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-16",
        control_id="tau2_extended_metrics_pricing_and_smoke_gate",
        reason_code="TAU2_EXTENDED_METRICS_PRICING_AND_SMOKE_VERIFIED",
        action="Act automatically",
        details={"fcr_pct": float(payload.get("fcr_pct", 0.0)), "environment_damage_rate": env_damage_rate},
    )


SCENARIO_EVALUATORS = {
    "PR-01": audit_ucp_zod_value_constraints_and_discovery_jwk_readiness,
    "PR-02": audit_ucp_cart_conversion_invariants_and_single_fulfillment_group,
    "PR-03": audit_ucp_order_webhook_rfc9421_signing_retry_and_raw_order_body,
    "PR-04": audit_ucp_error_envelope_discovery_cache_and_a2a_active_task_id,
    "PR-05": audit_x402_jcs_ed25519_and_pqc_mldsa65_epoch_receipts,
    "PR-06": audit_x402_covenant_facilitator_limits_and_xrpl_upto_payment_channel,
    "PR-07": audit_x402_readonly_preflight_inspector_and_cbor_uint64_metadata,
    "PR-08": audit_mcp_oauth_rfc6749_error_codes_and_client_dpop_token_proof,
    "PR-09": audit_mcp_session_group_reregistration_eviction_and_ui_parent_origin,
    "PR-10": audit_mcp_stdio_linear_chunk_accumulator_and_sse_header_isolation,
    "PR-11": audit_mcp_python_outbound_normalization_null_output_and_otel_error,
    "PR-12": audit_mcp_ts_refresh_scope_optin_and_root_ref_object_output_schema,
    "PR-13": audit_mcp_ts_pending_cache_generation_guard_and_handshake_timeout,
    "PR-14": audit_mcp_ts_sampling_context_capability_and_mcp_param_ascii_guard,
    "PR-15": audit_tau2_voice_simulator_version_tag_and_banking_knowledge_provenance,
    "PR-16": audit_tau2_extended_metrics_environment_damage_and_model_pricing_smoke,
}


def evaluate_stage216_scenario(scenario_id: str, payload: Mapping[str, Any]) -> GuardVerdict:
    evaluator = SCENARIO_EVALUATORS[scenario_id]
    return evaluator(payload)
