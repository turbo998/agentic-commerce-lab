"""Stage 212 deterministic security guardrails (2026-10-23).

Covers 16 primary-source Issues/PRs (PR-01..PR-16) across UCP, ACP, AP2, x402, MCP, and Sierra tau2-bench:
- PR-01: Universal-Commerce-Protocol/ucp#800 & #788 — Standardized Intermediate Representation (IR) AST & Cart->Checkout Cross-Capability Extension State Projection
- PR-02: Universal-Commerce-Protocol/ucp#676 & #113 — keys[] / signing_keys[] Dual-Key Migration Window & Checkout ETag / If-Match Optimistic Concurrency Control
- PR-03: Universal-Commerce-Protocol/ucp#701 & #732 — Normative Extension Ratification Governance Gate & Automated JSON Schema Canonical Formatting Check
- PR-04: agentic-commerce-protocol/agentic-commerce-protocol#120 & #60 — ACP Idempotency Payload Digest Equivalence (409 Conflict on Mismatch) & Merchant-Defined Data Namespace Validation
- PR-05: agentic-commerce-protocol/agentic-commerce-protocol#38 & #140 — ACP Credit Card Surcharge Cap / Jurisdiction Disclosure & OpenAPI/Schema Description+Example Consistency Gate
- PR-06: google-agentic-commerce/AP2#120 & #36 — Anonymous VDC Privacy-Preserving IntentMandate Authorization & Checkout Agent Bridge Role Separation
- PR-07: google-agentic-commerce/AP2#65 & #33 — Enterprise B2B PO/Net-Terms Mandate Extension & Brazilian Central Bank PIX Instant Payment Rail Binding
- PR-08: x402-foundation/x402#3620 & #3614 — Pooled Escrow Batch-Settlement Agent-Crew Spending Policy & SpendControls Client-Side maxTimeoutSeconds Ceiling
- PR-09: x402-foundation/x402#3582 & #3564 — Fetch/Axios onPaymentRequired Retry Updated Requirements Re-Evaluation & Axios onPaymentResponse Execution on Paid 4xx/5xx
- PR-10: x402-foundation/x402#3557 & #3510 — @x402/fetch extensions.bazaar Preservation Across Settle & Atomic Integer String Constraint on PaymentRequirements.amount
- PR-11: x402-foundation/x402#3505 & #3504 — Non-USD-Quoted Default Assets Explicit FX Rate Conversion & Arc (eip155:5042) Native Gas-Asset Client-Broadcast EIP-3009
- PR-12: x402-foundation/x402#3782 & #3720 — presign-guard Pre-Sign OFAC Wallet Screening + Simulation & knos-order Third-Party Signed Acceptance Escrow Release
- PR-13: modelcontextprotocol/modelcontextprotocol#3229 & #3393 — Native MCP Token Metering / Session Budget Enforcement & Client-Side x402 Paid Tool Flow
- PR-14: modelcontextprotocol/modelcontextprotocol#3232 & #3044 — Confidential Prompt/Instruction visibility="hidden" Isolation & CacheableResult ttlMs + cacheScope Enforcement
- PR-15: sierra-research/tau2-bench#390 & #65 — Lazy Optional Voice Dependency Import Isolation on Base Install & Retail calculate Tool Optionality When Inline Math Matches
- PR-16: sierra-research/tau2-bench#204 & #42 — Full Multi-Turn User-Agent Trajectory Export in tau2 run & Orchestrator agent_msg.validate() Exception Recovery
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GuardDecision:
    admitted: bool
    decision_code: str
    detail: str


# ---------------------------------------------------------------------------
# PR-01: UCP #800 & #788 — Standardized IR Strategy & Cart->Checkout Projection
# ---------------------------------------------------------------------------
def audit_ucp_ir_codegen_and_cart_to_checkout_extension_projection(
    payload: Mapping[str, Any],
) -> GuardDecision:
    ir = payload.get("ucp_ir")
    projection = payload.get("cart_to_checkout_projection")
    if not isinstance(ir, Mapping) or not isinstance(projection, Mapping):
        return GuardDecision(
            False,
            "UCP_IR_INVALID_OR_EXTENSION_PROJECTION_DROPPED_BLOCKED",
            "Missing ucp_ir or cart_to_checkout_projection descriptor",
        )
    ir_version = str(ir.get("ir_version", "")).strip()
    unresolved_refs = int(ir.get("unresolved_schema_refs", 1))
    deterministic_ast = bool(ir.get("deterministic_ast", False))
    if not ir_version or unresolved_refs != 0 or not deterministic_ast:
        return GuardDecision(
            False,
            "UCP_IR_INVALID_OR_EXTENSION_PROJECTION_DROPPED_BLOCKED",
            "UCP Intermediate Representation must have resolved refs and a deterministic AST (#800)",
        )
    cart_exts = set(projection.get("cart_extensions") or [])
    checkout_exts = set(projection.get("checkout_extensions") or [])
    lossless_state = bool(projection.get("extension_state_preserved", False))
    if not cart_exts or not cart_exts.issubset(checkout_exts) or not lossless_state:
        return GuardDecision(
            False,
            "UCP_IR_INVALID_OR_EXTENSION_PROJECTION_DROPPED_BLOCKED",
            "Cross-capability extension state must project losslessly from Cart to Checkout (#788)",
        )
    return GuardDecision(
        True,
        "UCP_IR_AND_CART_TO_CHECKOUT_PROJECTION_VERIFIED",
        "UCP IR AST and Cart-to-Checkout extension state projection verified",
    )


# ---------------------------------------------------------------------------
# PR-02: UCP #676 & #113 — Dual keys[]/signing_keys[] Window & Checkout ETag/If-Match
# ---------------------------------------------------------------------------
def audit_ucp_signing_keys_migration_and_checkout_etag_if_match(
    payload: Mapping[str, Any],
) -> GuardDecision:
    profile = payload.get("ucp_profile_keys")
    concurrency = payload.get("checkout_update")
    if not isinstance(profile, Mapping) or not isinstance(concurrency, Mapping):
        return GuardDecision(
            False,
            "UCP_SIGNING_KEYS_MIGRATION_BREAK_OR_ETAG_CONFLICT_BLOCKED",
            "Missing ucp_profile_keys or checkout_update object",
        )
    keys = profile.get("keys")
    legacy_fallback = bool(profile.get("supports_legacy_signing_keys_fallback", False))
    if not isinstance(keys, list) or len(keys) == 0 or not legacy_fallback:
        return GuardDecision(
            False,
            "UCP_SIGNING_KEYS_MIGRATION_BREAK_OR_ETAG_CONFLICT_BLOCKED",
            "Mixed-version UCP verifiers must publish keys[] while retaining signing_keys[] fallback (#676)",
        )
    if_match = str(concurrency.get("if_match", "")).strip()
    current_etag = str(concurrency.get("current_etag", "")).strip()
    if not if_match or not current_etag or if_match != current_etag:
        return GuardDecision(
            False,
            "UCP_SIGNING_KEYS_MIGRATION_BREAK_OR_ETAG_CONFLICT_BLOCKED",
            "Concurrent checkout updates require matching ETag / If-Match precondition (#113)",
        )
    return GuardDecision(
        True,
        "UCP_SIGNING_KEYS_FALLBACK_AND_ETAG_PRECONDITION_VERIFIED",
        "UCP dual signing_keys[] fallback and checkout ETag/If-Match verified",
    )


# ---------------------------------------------------------------------------
# PR-03: UCP #701 & #732 — Normative Extension Ratification & JSON Schema Formatting
# ---------------------------------------------------------------------------
def audit_ucp_extension_ratification_and_json_schema_formatting(
    payload: Mapping[str, Any],
) -> GuardDecision:
    ext = payload.get("extension_governance")
    lint = payload.get("schema_formatting")
    if not isinstance(ext, Mapping) or not isinstance(lint, Mapping):
        return GuardDecision(
            False,
            "UCP_UNRATIFIED_NORMATIVE_EXTENSION_OR_UNFORMATTED_SCHEMA_BLOCKED",
            "Missing extension_governance or schema_formatting object",
        )
    claims_normative = bool(ext.get("claims_normative_ucp_namespace", False))
    ratified_by_dtc = bool(ext.get("ratified_by_domain_tech_council", False))
    independent_impls = int(ext.get("independent_implementations", 0))
    if claims_normative and (not ratified_by_dtc or independent_impls < 2):
        return GuardDecision(
            False,
            "UCP_UNRATIFIED_NORMATIVE_EXTENSION_OR_UNFORMATTED_SCHEMA_BLOCKED",
            "Normative dev.ucp.* promotion requires DTC ratification and >= 2 independent implementations (#701)",
        )
    prettier_enabled = bool(lint.get("validate_json_prettier", False))
    formatting_clean = bool(lint.get("schema_formatting_clean", False))
    if not prettier_enabled or not formatting_clean:
        return GuardDecision(
            False,
            "UCP_UNRATIFIED_NORMATIVE_EXTENSION_OR_UNFORMATTED_SCHEMA_BLOCKED",
            "CI JSON schema formatting/linting must be enabled and clean (#732)",
        )
    return GuardDecision(
        True,
        "UCP_EXTENSION_RATIFICATION_AND_SCHEMA_FORMATTING_VERIFIED",
        "UCP extension ratification path and JSON schema formatting verified",
    )


# ---------------------------------------------------------------------------
# PR-04: ACP #120 & #60 — Idempotency Payload Digest & Merchant-Defined Data
# ---------------------------------------------------------------------------
def audit_acp_idempotency_payload_digest_and_merchant_defined_data(
    payload: Mapping[str, Any],
) -> GuardDecision:
    idem = payload.get("idempotency_check")
    mdd = payload.get("merchant_defined_data")
    if not isinstance(idem, Mapping) or not isinstance(mdd, Mapping):
        return GuardDecision(
            False,
            "ACP_IDEMPOTENCY_PAYLOAD_CONFLICT_OR_INVALID_MERCHANT_DATA_BLOCKED",
            "Missing idempotency_check or merchant_defined_data",
        )
    key = str(idem.get("idempotency_key", "")).strip()
    first_digest = str(idem.get("first_request_sha256", "")).strip()
    retry_digest = str(idem.get("retry_request_sha256", "")).strip()
    if not key or not first_digest or first_digest != retry_digest:
        return GuardDecision(
            False,
            "ACP_IDEMPOTENCY_PAYLOAD_CONFLICT_OR_INVALID_MERCHANT_DATA_BLOCKED",
            "Reusing an ACP Idempotency-Key with a mutated payload digest must fail with 409 Conflict (#120)",
        )
    if len(mdd) == 0 or len(mdd) > 32:
        return GuardDecision(
            False,
            "ACP_IDEMPOTENCY_PAYLOAD_CONFLICT_OR_INVALID_MERCHANT_DATA_BLOCKED",
            "ACP merchant_defined_data must contain 1..32 bounded key/value entries (#60)",
        )
    for k, v in mdd.items():
        if not isinstance(k, str) or not k.strip() or not isinstance(v, str) or len(v) > 256:
            return GuardDecision(
                False,
                "ACP_IDEMPOTENCY_PAYLOAD_CONFLICT_OR_INVALID_MERCHANT_DATA_BLOCKED",
                "ACP merchant_defined_data values must be bounded strings <= 256 chars (#60)",
            )
    return GuardDecision(
        True,
        "ACP_IDEMPOTENCY_AND_MERCHANT_DEFINED_DATA_VERIFIED",
        "ACP idempotency payload digest and merchant_defined_data verified",
    )


# ---------------------------------------------------------------------------
# PR-05: ACP #38 & #140 — Surcharging Compliance & Schema Description/Example Gate
# ---------------------------------------------------------------------------
def audit_acp_surcharging_disclosure_and_schema_consistency_examples(
    payload: Mapping[str, Any],
) -> GuardDecision:
    surcharge = payload.get("surcharge_policy")
    schema_audit = payload.get("schema_consistency_audit")
    if not isinstance(surcharge, Mapping) or not isinstance(schema_audit, Mapping):
        return GuardDecision(
            False,
            "ACP_ILLEGAL_SURCHARGE_OR_MISSING_SCHEMA_EXAMPLES_BLOCKED",
            "Missing surcharge_policy or schema_consistency_audit",
        )
    card_funding = str(surcharge.get("card_funding", "")).strip().lower()
    surcharge_bps = int(surcharge.get("surcharge_bps", 0))
    jurisdiction_allows = bool(surcharge.get("jurisdiction_allows_surcharge", False))
    buyer_disclosed = bool(surcharge.get("explicit_line_item_disclosed", False))
    # Debit/prepaid surcharging or >400 bps (4%) or prohibited jurisdiction is blocked
    if surcharge_bps > 0 and (
        card_funding in {"debit", "prepaid"}
        or surcharge_bps > 400
        or not jurisdiction_allows
        or not buyer_disclosed
    ):
        return GuardDecision(
            False,
            "ACP_ILLEGAL_SURCHARGE_OR_MISSING_SCHEMA_EXAMPLES_BLOCKED",
            "ACP card surcharge violates debit prohibition, 400 bps network cap, jurisdiction rule, or disclosure (#38)",
        )
    missing_desc = int(schema_audit.get("missing_descriptions_count", 1))
    missing_examples = int(schema_audit.get("missing_examples_count", 1))
    if missing_desc != 0 or missing_examples != 0:
        return GuardDecision(
            False,
            "ACP_ILLEGAL_SURCHARGE_OR_MISSING_SCHEMA_EXAMPLES_BLOCKED",
            "ACP validate-consistency requires zero missing descriptions or examples (#140)",
        )
    return GuardDecision(
        True,
        "ACP_SURCHARGE_COMPLIANCE_AND_SCHEMA_EXAMPLES_VERIFIED",
        "ACP surcharge compliance and schema descriptions/examples verified",
    )


# ---------------------------------------------------------------------------
# PR-06: AP2 #120 & #36 — Anonymous VDC IntentMandate & Checkout Agent Bridge Role
# ---------------------------------------------------------------------------
def audit_ap2_anonymous_vdc_intent_mandate_and_checkout_agent_role(
    payload: Mapping[str, Any],
) -> GuardDecision:
    vdc = payload.get("anonymous_vdc_mandate")
    bridge = payload.get("checkout_agent_bridge")
    if not isinstance(vdc, Mapping) or not isinstance(bridge, Mapping):
        return GuardDecision(
            False,
            "AP2_ANONYMOUS_VDC_PII_LEAK_OR_CHECKOUT_AGENT_BYPASS_BLOCKED",
            "Missing anonymous_vdc_mandate or checkout_agent_bridge",
        )
    zk_proof_valid = bool(vdc.get("bbs_or_zkp_proof_valid", False))
    exposed_pii = list(vdc.get("exposed_pii_fields") or [])
    nonce_bound = bool(vdc.get("challenge_nonce_bound", False))
    if not zk_proof_valid or len(exposed_pii) > 0 or not nonce_bound:
        return GuardDecision(
            False,
            "AP2_ANONYMOUS_VDC_PII_LEAK_OR_CHECKOUT_AGENT_BYPASS_BLOCKED",
            "Anonymous VDC IntentMandate must verify ZKP/BBS+ proof with zero PII leakage and nonce binding (#120)",
        )
    shopping_agent_touches_raw_pan = bool(bridge.get("shopping_agent_touches_raw_pan", True))
    checkout_agent_attested = bool(bridge.get("checkout_agent_role_attested", False))
    if shopping_agent_touches_raw_pan or not checkout_agent_attested:
        return GuardDecision(
            False,
            "AP2_ANONYMOUS_VDC_PII_LEAK_OR_CHECKOUT_AGENT_BYPASS_BLOCKED",
            "AP2 Checkout Agent role must isolate payment credentials from the Shopping Agent (#36)",
        )
    return GuardDecision(
        True,
        "AP2_ANONYMOUS_VDC_AND_CHECKOUT_AGENT_BRIDGE_VERIFIED",
        "AP2 Anonymous VDC IntentMandate and Checkout Agent bridge role verified",
    )


# ---------------------------------------------------------------------------
# PR-07: AP2 #65 & #33 — Enterprise B2B Mandate & Brazilian PIX Rail Integration
# ---------------------------------------------------------------------------
def audit_ap2_b2b_procurement_mandate_and_pix_instant_rail(
    payload: Mapping[str, Any],
) -> GuardDecision:
    b2b = payload.get("b2b_mandate")
    pix = payload.get("pix_settlement")
    if not isinstance(b2b, Mapping) or not isinstance(pix, Mapping):
        return GuardDecision(
            False,
            "AP2_B2B_MANDATE_UNAUTHORIZED_OR_PIX_BINDING_INVALID_BLOCKED",
            "Missing b2b_mandate or pix_settlement descriptor",
        )
    po_number = str(b2b.get("purchase_order_id", "")).strip()
    cost_center = str(b2b.get("cost_center_id", "")).strip()
    approver_sig = bool(b2b.get("authorized_signatory_verified", False))
    amount_minor = int(b2b.get("invoice_amount_minor", 0))
    limit_minor = int(b2b.get("cost_center_limit_minor", 0))
    if not po_number or not cost_center or not approver_sig or amount_minor <= 0 or amount_minor > limit_minor:
        return GuardDecision(
            False,
            "AP2_B2B_MANDATE_UNAUTHORIZED_OR_PIX_BINDING_INVALID_BLOCKED",
            "AP2 B2B mandate requires PO, cost-center signatory approval, and invoice <= limit (#65)",
        )
    rail = str(pix.get("rail", "")).strip()
    txid = str(pix.get("pix_txid", "")).strip()
    bacen_dict_verified = bool(pix.get("bacen_dict_key_verified", False))
    # PIX txid is 26..35 alphanumeric chars in BACEN spec
    if rail != "br.gov.bcb.pix" or len(txid) < 26 or len(txid) > 35 or not bacen_dict_verified:
        return GuardDecision(
            False,
            "AP2_B2B_MANDATE_UNAUTHORIZED_OR_PIX_BINDING_INVALID_BLOCKED",
            "AP2 PIX integration requires br.gov.bcb.pix rail, 26..35 char txid, and BACEN DICT verification (#33)",
        )
    return GuardDecision(
        True,
        "AP2_B2B_MANDATE_AND_PIX_RAIL_VERIFIED",
        "AP2 B2B procurement mandate and Brazilian PIX rail binding verified",
    )


# ---------------------------------------------------------------------------
# PR-08: x402 #3620 & #3614 — Pooled Escrow Agent Crew Policy & maxTimeoutSeconds Cap
# ---------------------------------------------------------------------------
def audit_x402_pooled_escrow_crew_policy_and_spend_controls_timeout_cap(
    payload: Mapping[str, Any],
) -> GuardDecision:
    pool = payload.get("pooled_escrow")
    controls = payload.get("spend_controls")
    if not isinstance(pool, Mapping) or not isinstance(controls, Mapping):
        return GuardDecision(
            False,
            "X402_POOLED_ESCROW_POLICY_BREACH_OR_TIMEOUT_WINDOW_EXCESSIVE_BLOCKED",
            "Missing pooled_escrow or spend_controls descriptor",
        )
    escrow_cap = int(pool.get("pool_escrow_cap_minor", 0))
    crew_total_claimed = int(pool.get("crew_cumulative_claimed_minor", 0))
    member_call_minor = int(pool.get("member_call_minor", 0))
    member_per_call_cap = int(pool.get("member_per_call_cap_minor", 0))
    if (
        escrow_cap <= 0
        or crew_total_claimed + member_call_minor > escrow_cap
        or member_call_minor > member_per_call_cap
    ):
        return GuardDecision(
            False,
            "X402_POOLED_ESCROW_POLICY_BREACH_OR_TIMEOUT_WINDOW_EXCESSIVE_BLOCKED",
            "Agent crew member spend exceeds per-call cap or pooled batch-settlement escrow ceiling (#3620)",
        )
    server_req_timeout = int(controls.get("server_max_timeout_seconds", 0))
    client_cap_timeout = int(controls.get("client_max_timeout_seconds_cap", 300))
    signed_validity_window = int(controls.get("signed_validity_window_seconds", 0))
    if signed_validity_window <= 0 or signed_validity_window > min(server_req_timeout, client_cap_timeout):
        return GuardDecision(
            False,
            "X402_POOLED_ESCROW_POLICY_BREACH_OR_TIMEOUT_WINDOW_EXCESSIVE_BLOCKED",
            "EIP-3009 validBefore window must be capped by SpendControls.maxTimeoutSeconds (#3614)",
        )
    return GuardDecision(
        True,
        "X402_POOLED_ESCROW_AND_TIMEOUT_CAP_VERIFIED",
        "x402 pooled escrow agent-crew policy and client maxTimeoutSeconds cap verified",
    )


# ---------------------------------------------------------------------------
# PR-09: x402 #3582 & #3564 — Hook Retry Updated Requirements & Paid 4xx/5xx Hook
# ---------------------------------------------------------------------------
def audit_x402_retry_updated_requirements_and_error_status_response_hook(
    payload: Mapping[str, Any],
) -> GuardDecision:
    retry = payload.get("payment_required_retry")
    err_hook = payload.get("paid_error_response")
    if not isinstance(retry, Mapping) or not isinstance(err_hook, Mapping):
        return GuardDecision(
            False,
            "X402_STALE_RETRY_REQUIREMENTS_OR_SKIPPED_ERROR_RESPONSE_HOOK_BLOCKED",
            "Missing payment_required_retry or paid_error_response",
        )
    latest_402_amount = str(retry.get("latest_402_amount", "")).strip()
    signed_payload_amount = str(retry.get("signed_payload_amount", "")).strip()
    rebound_to_latest_402 = bool(retry.get("rebound_to_latest_402_requirements", False))
    if not latest_402_amount or latest_402_amount != signed_payload_amount or not rebound_to_latest_402:
        return GuardDecision(
            False,
            "X402_STALE_RETRY_REQUIREMENTS_OR_SKIPPED_ERROR_RESPONSE_HOOK_BLOCKED",
            "Fetch/Axios must re-evaluate updated 402 PaymentRequirements after onPaymentRequired retry (#3582)",
        )
    http_status = int(err_hook.get("http_status", 200))
    has_payment_response_header = bool(err_hook.get("has_payment_response_header", False))
    on_payment_response_invoked = bool(err_hook.get("on_payment_response_invoked", False))
    if http_status >= 400 and has_payment_response_header and not on_payment_response_invoked:
        return GuardDecision(
            False,
            "X402_STALE_RETRY_REQUIREMENTS_OR_SKIPPED_ERROR_RESPONSE_HOOK_BLOCKED",
            "Axios must invoke onPaymentResponse hooks even when a paid request returns HTTP 4xx/5xx (#3564)",
        )
    return GuardDecision(
        True,
        "X402_RETRY_REQUIREMENTS_AND_ERROR_RESPONSE_HOOK_VERIFIED",
        "x402 updated retry requirements and paid 4xx/5xx onPaymentResponse hook verified",
    )


# ---------------------------------------------------------------------------
# PR-10: x402 #3557 & #3510 — @x402/fetch Bazaar Preservation & Atomic Integer Amount
# ---------------------------------------------------------------------------
def audit_x402_fetch_bazaar_extension_preservation_and_atomic_integer_amount(
    payload: Mapping[str, Any],
) -> GuardDecision:
    bazaar_preserved = bool(payload.get("fetch_preserved_extensions_bazaar", False))
    amount_str = str(payload.get("payment_requirements_amount", "")).strip()
    if not bazaar_preserved:
        return GuardDecision(
            False,
            "X402_FETCH_DROPPED_BAZAAR_EXT_OR_NON_INTEGRAL_ATOMIC_AMOUNT_BLOCKED",
            "@x402/fetch must preserve extensions.bazaar across payment payload construction and settle (#3557)",
        )
    if not amount_str.isdigit() or int(amount_str) <= 0:
        return GuardDecision(
            False,
            "X402_FETCH_DROPPED_BAZAAR_EXT_OR_NON_INTEGRAL_ATOMIC_AMOUNT_BLOCKED",
            "PaymentRequirements.amount must be a positive base-10 integer string in atomic units (#3510)",
        )
    return GuardDecision(
        True,
        "X402_FETCH_BAZAAR_PRESERVATION_AND_ATOMIC_INTEGER_AMOUNT_VERIFIED",
        "@x402/fetch extensions.bazaar preservation and integer atomic amount verified",
    )


# ---------------------------------------------------------------------------
# PR-11: x402 #3505 & #3504 — Non-USD Asset Spend Cap FX & Arc Native Gas EIP-3009
# ---------------------------------------------------------------------------
def audit_x402_non_usd_spend_cap_fx_and_arc_native_gas_eip3009(
    payload: Mapping[str, Any],
) -> GuardDecision:
    asset = payload.get("spend_cap_asset")
    arc = payload.get("arc_native_gas_settlement")
    if not isinstance(asset, Mapping) or not isinstance(arc, Mapping):
        return GuardDecision(
            False,
            "X402_UNCONVERTED_NON_USD_SPEND_CAP_OR_ARC_GAS_TRANSFER_INVALID_BLOCKED",
            "Missing spend_cap_asset or arc_native_gas_settlement",
        )
    currency = str(asset.get("quote_currency", "USD")).strip().upper()
    assumed_usd_1to1 = bool(asset.get("assumed_usd_1to1_without_fx", False))
    fx_rate_verified = bool(asset.get("fx_oracle_rate_applied", False))
    if currency != "USD" and (assumed_usd_1to1 or not fx_rate_verified):
        return GuardDecision(
            False,
            "X402_UNCONVERTED_NON_USD_SPEND_CAP_OR_ARC_GAS_TRANSFER_INVALID_BLOCKED",
            "Non-USD-pegged default assets require explicit FX conversion rather than 1:1 USD decimals assumption (#3505)",
        )
    network = str(arc.get("network", "")).strip()
    transfer_method = str(arc.get("asset_transfer_method", "")).strip()
    receipt_verified = bool(arc.get("tx_receipt_confirmed", False))
    if network != "eip155:5042" or transfer_method != "client-broadcast-eip3009" or not receipt_verified:
        return GuardDecision(
            False,
            "X402_UNCONVERTED_NON_USD_SPEND_CAP_OR_ARC_GAS_TRANSFER_INVALID_BLOCKED",
            "Arc (eip155:5042) native gas-asset EOA settlement requires confirmed client-broadcast-eip3009 (#3504)",
        )
    return GuardDecision(
        True,
        "X402_NON_USD_FX_SPEND_CAP_AND_ARC_EIP3009_VERIFIED",
        "x402 non-USD FX spend cap conversion and Arc native gas EIP-3009 settlement verified",
    )


# ---------------------------------------------------------------------------
# PR-12: x402 #3782 & #3720 — presign-guard OFAC Screen & knos-order Arbiter Release
# ---------------------------------------------------------------------------
def audit_x402_presign_ofac_guard_and_knos_order_arbiter_acceptance(
    payload: Mapping[str, Any],
) -> GuardDecision:
    presign = payload.get("presign_guard")
    knos = payload.get("knos_order_escrow")
    if not isinstance(presign, Mapping) or not isinstance(knos, Mapping):
        return GuardDecision(
            False,
            "X402_OFAC_SANCTIONED_PAYEE_OR_UNATTESTED_KNOS_ORDER_RELEASE_BLOCKED",
            "Missing presign_guard or knos_order_escrow",
        )
    ofac_clear = bool(presign.get("ofac_sanctions_clear", False))
    pre_sign_sim_ok = bool(presign.get("pre_sign_simulation_passed", False))
    if not ofac_clear or not pre_sign_sim_ok:
        return GuardDecision(
            False,
            "X402_OFAC_SANCTIONED_PAYEE_OR_UNATTESTED_KNOS_ORDER_RELEASE_BLOCKED",
            "presign-guard requires OFAC sanctions clearance and pre-sign simulation pass before signing (#3782)",
        )
    arbiter_did = str(knos.get("third_party_arbiter_did", "")).strip()
    payer_did = str(knos.get("payer_did", "")).strip()
    payee_did = str(knos.get("payee_did", "")).strip()
    acceptance_sig = bool(knos.get("signed_acceptance_verified", False))
    if (
        not arbiter_did
        or arbiter_did in {payer_did, payee_did}
        or not acceptance_sig
    ):
        return GuardDecision(
            False,
            "X402_OFAC_SANCTIONED_PAYEE_OR_UNATTESTED_KNOS_ORDER_RELEASE_BLOCKED",
            "knos-order escrow release requires an independent third-party arbiter signed acceptance (#3720)",
        )
    return GuardDecision(
        True,
        "X402_PRESIGN_OFAC_GUARD_AND_KNOS_ORDER_ESCROW_VERIFIED",
        "x402 presign-guard OFAC screen and knos-order third-party acceptance verified",
    )


# ---------------------------------------------------------------------------
# PR-13: MCP #3229 & #3393 — Native Token Metering / Session Budget & Paid MCP Tools
# ---------------------------------------------------------------------------
def audit_mcp_token_metering_session_budget_and_paid_tool_x402_flow(
    payload: Mapping[str, Any],
) -> GuardDecision:
    budget = payload.get("mcp_session_budget")
    paid_tool = payload.get("paid_tool_call")
    if not isinstance(budget, Mapping) or not isinstance(paid_tool, Mapping):
        return GuardDecision(
            False,
            "MCP_SESSION_TOKEN_BUDGET_EXCEEDED_OR_UNPAID_X402_TOOL_CALL_BLOCKED",
            "Missing mcp_session_budget or paid_tool_call",
        )
    consumed_tokens = int(budget.get("consumed_tokens", 0))
    call_tokens = int(budget.get("estimated_call_tokens", 0))
    max_session_tokens = int(budget.get("max_session_tokens", 0))
    if max_session_tokens <= 0 or consumed_tokens + call_tokens > max_session_tokens:
        return GuardDecision(
            False,
            "MCP_SESSION_TOKEN_BUDGET_EXCEEDED_OR_UNPAID_X402_TOOL_CALL_BLOCKED",
            "MCP tool invocation exceeds native session token metering budget (#3229)",
        )
    requires_payment = bool(paid_tool.get("requires_x402_payment", False))
    payment_settled = bool(paid_tool.get("x402_payment_receipt_verified", False))
    price_disclosed = bool(paid_tool.get("tool_price_disclosed_in_descriptor", False))
    if requires_payment and (not payment_settled or not price_disclosed):
        return GuardDecision(
            False,
            "MCP_SESSION_TOKEN_BUDGET_EXCEEDED_OR_UNPAID_X402_TOOL_CALL_BLOCKED",
            "Paid MCP tool requires pre-disclosed price and verified x402 payment receipt (#3393)",
        )
    return GuardDecision(
        True,
        "MCP_TOKEN_METERING_AND_PAID_TOOL_X402_FLOW_VERIFIED",
        "MCP native token metering budget and client-side x402 paid tool flow verified",
    )


# ---------------------------------------------------------------------------
# PR-14: MCP #3232 & #3044 — Confidential Prompt visibility="hidden" & CacheableResult
# ---------------------------------------------------------------------------
def audit_mcp_hidden_prompt_visibility_and_cacheable_result_scope(
    payload: Mapping[str, Any],
) -> GuardDecision:
    prompt_cfg = payload.get("confidential_prompt")
    cache_cfg = payload.get("cacheable_result")
    if not isinstance(prompt_cfg, Mapping) or not isinstance(cache_cfg, Mapping):
        return GuardDecision(
            False,
            "MCP_HIDDEN_PROMPT_EXPOSED_OR_CROSS_SESSION_CACHE_LEAK_BLOCKED",
            "Missing confidential_prompt or cacheable_result",
        )
    hidden = bool(prompt_cfg.get("hidden", False))
    rendered_in_user_ui = bool(prompt_cfg.get("rendered_in_user_ui", False))
    if hidden and rendered_in_user_ui:
        return GuardDecision(
            False,
            "MCP_HIDDEN_PROMPT_EXPOSED_OR_CROSS_SESSION_CACHE_LEAK_BLOCKED",
            "Confidential MCP prompts/instructions marked hidden: true must not be exposed in end-user UI (#3232)",
        )
    ttl_ms = int(cache_cfg.get("ttlMs", 0))
    cache_scope = str(cache_cfg.get("cacheScope", "")).strip()
    contains_user_private_data = bool(cache_cfg.get("contains_user_private_data", False))
    if ttl_ms <= 0 or cache_scope not in {"session", "global"} or (
        contains_user_private_data and cache_scope == "global"
    ):
        return GuardDecision(
            False,
            "MCP_HIDDEN_PROMPT_EXPOSED_OR_CROSS_SESSION_CACHE_LEAK_BLOCKED",
            "CacheableResult requires positive ttlMs and forbids global cacheScope for user-private data (#3044)",
        )
    return GuardDecision(
        True,
        "MCP_HIDDEN_PROMPT_AND_CACHEABLE_RESULT_SCOPE_VERIFIED",
        "MCP hidden prompt visibility isolation and CacheableResult scope verified",
    )


# ---------------------------------------------------------------------------
# PR-15: Sierra tau2-bench #390 & #65 — Lazy Voice Import & Retail calculate Optional
# ---------------------------------------------------------------------------
def audit_tau2_lazy_voice_import_and_retail_calculate_optionality(
    payload: Mapping[str, Any],
) -> GuardDecision:
    eager_voice_import_on_text_run = bool(payload.get("eager_voice_import_on_text_run", False))
    retail_eval = payload.get("retail_math_eval")
    if eager_voice_import_on_text_run or not isinstance(retail_eval, Mapping):
        return GuardDecision(
            False,
            "TAU2_EAGER_VOICE_IMPORT_CRASH_OR_FALSE_CALCULATE_PENALTY_BLOCKED",
            "Base text runner must lazy-import voice dependencies rather than crashing without voice extra (#390)",
        )
    inline_math_accurate = bool(retail_eval.get("inline_math_accurate", False))
    called_calculate_tool = bool(retail_eval.get("called_calculate_tool", False))
    penalized_for_missing_calculate = bool(retail_eval.get("penalized_for_missing_calculate", False))
    if inline_math_accurate and not called_calculate_tool and penalized_for_missing_calculate:
        return GuardDecision(
            False,
            "TAU2_EAGER_VOICE_IMPORT_CRASH_OR_FALSE_CALCULATE_PENALTY_BLOCKED",
            "Retail evaluation must not penalize accurate inline arithmetic when calculate tool is omitted (#65)",
        )
    return GuardDecision(
        True,
        "TAU2_LAZY_VOICE_IMPORT_AND_RETAIL_CALCULATE_OPTIONALITY_VERIFIED",
        "tau2-bench lazy voice import and retail calculate optionality verified",
    )


# ---------------------------------------------------------------------------
# PR-16: Sierra tau2-bench #204 & #42 — Full Trajectory Export & validate() Recovery
# ---------------------------------------------------------------------------
def audit_tau2_detailed_conversation_history_and_validate_recovery(
    payload: Mapping[str, Any],
) -> GuardDecision:
    export = payload.get("simulation_export")
    orchestrator = payload.get("orchestrator_validation")
    if not isinstance(export, Mapping) or not isinstance(orchestrator, Mapping):
        return GuardDecision(
            False,
            "TAU2_SUMMARY_ONLY_EXPORT_OR_UNCAUGHT_VALIDATE_SHUTDOWN_BLOCKED",
            "Missing simulation_export or orchestrator_validation",
        )
    includes_full_turns = bool(export.get("includes_full_turn_trajectory", False))
    includes_tool_traces = bool(export.get("includes_step_by_step_tool_traces", False))
    if not includes_full_turns or not includes_tool_traces:
        return GuardDecision(
            False,
            "TAU2_SUMMARY_ONLY_EXPORT_OR_UNCAUGHT_VALIDATE_SHUTDOWN_BLOCKED",
            "tau2 run output must preserve full turn-by-turn conversation history and tool traces (#204)",
        )
    validate_threw = bool(orchestrator.get("agent_msg_validate_threw", False))
    entire_eval_aborted = bool(orchestrator.get("entire_eval_shut_down", False))
    recorded_as_task_error = bool(orchestrator.get("recorded_as_task_level_error", False))
    if validate_threw and (entire_eval_aborted or not recorded_as_task_error):
        return GuardDecision(
            False,
            "TAU2_SUMMARY_ONLY_EXPORT_OR_UNCAUGHT_VALIDATE_SHUTDOWN_BLOCKED",
            "Orchestrator must isolate agent_msg.validate() exceptions to the task without shutting down the run (#42)",
        )
    return GuardDecision(
        True,
        "TAU2_DETAILED_TRAJECTORY_AND_VALIDATE_RECOVERY_VERIFIED",
        "tau2-bench full trajectory export and agent_msg.validate() recovery verified",
    )
