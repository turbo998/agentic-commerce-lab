"""Stage 210 deterministic protocol & security guardrails (2026-10-23 · 210-Stage Milestone!).

Covers 16 primary-source upstream issues and PRs across UCP, ACP, AP2, x402, MCP, and Sierra tau2-bench:
- PR-01: Universal-Commerce-Protocol/ucp#682 & #55 (Bulk Product Discovery DWG & Catalog Search+Lookup capabilities)
- PR-02: Universal-Commerce-Protocol/ucp#591 & #420 (Asymmetric key signatures & host-delegated 3DS2 challenge flow)
- PR-03: Universal-Commerce-Protocol/ucp#112 & #63 (Line item ID vs catalog item ID separation & Order TotalResponse.type enum)
- PR-04: agentic-commerce-protocol/agentic-commerce-protocol#84 & #81 (SelectedFulfillmentOption naming cleanup & YYYY-MM-DD versioning)
- PR-05: agentic-commerce-protocol/agentic-commerce-protocol#55 & #40 (ACP 3DS 2.x authentication flow & x402 payment method support)
- PR-06: google-agentic-commerce/AP2#127 & #43 (Mandate Verifiable Credential JSON Schema & SEDI/KERI guardianship spend controls)
- PR-07: x402-foundation/x402#3334 & #3330 (settlePayment override ceiling <= PaymentRequirements.amount & Axios paid-response validation hook)
- PR-08: x402-foundation/x402#3352 & #3333 (Stellar smart-account diagnostic events & mandatory areFeesSponsored: true validation)
- PR-09: x402-foundation/x402#3332 & #3351 (Stellar feeBumpSigner inclusion in signingAddresses safety checks & SVM compute-unit policy)
- PR-10: x402-foundation/x402#3381 & #3396 (x402.agent-switchboard/v0 SCITT relay & declarative endpoint conformance profiles)
- PR-11: x402-foundation/x402#3677 & #3638 (CDP Bazaar discovery indexing readiness preflight against silent blockers)
- PR-12: x402-foundation/x402#3645 & #3633 (Kaspa BlockDAG & Bitcoin Cash UTXO exact/batch settlement conservation)
- PR-13: modelcontextprotocol/modelcontextprotocol#2991 & #2989 (SEP-2243 HeaderMismatch -32020 error code & subscriptions/listen envelope)
- PR-14: modelcontextprotocol/modelcontextprotocol#2188 & #2166 (SEP-2188 notifications/elicitation/pending timeout & SEP-2166 HTTPS resource URLs)
- PR-15: sierra-research/tau2-bench#104 & #81 (Telecom <= 2.0GB refuel upper bound policy & default ACTION reward_basis)
- PR-16: sierra-research/tau2-bench#84 & #43 (Airline Task 7 cancellation policy eligibility & graceful agent_msg.validate() exception handling)
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardDecision:
    admitted: bool
    decision_code: str
    reason: str
    Metadata: Mapping[str, Any] | None = None


_DATE_VER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ORDER_TOTAL_TYPES = {
    "items_discount",
    "subtotal",
    "discount",
    "fulfillment",
    "tax",
    "fee",
    "total",
}


# PR-01: UCP #682 & #55
def audit_ucp_bulk_catalog_discovery_and_search_lookup_capabilities(
    payload: Mapping[str, Any],
) -> GuardDecision:
    capabilities = payload.get("declared_catalog_capabilities")
    search_req = payload.get("search_request")
    lookup_req = payload.get("lookup_request")
    bulk_snapshot = payload.get("bulk_snapshot")

    required_caps = {"dev.ucp.shopping.catalog.search", "dev.ucp.shopping.catalog.lookup"}
    if not isinstance(capabilities, Sequence) or not required_caps.issubset(set(capabilities)):
        return GuardDecision(
            False,
            "UCP_CATALOG_DISCOVERY_OR_SEARCH_LOOKUP_INVALID_BLOCKED",
            "merchant must declare dev.ucp.shopping.catalog.search and dev.ucp.shopping.catalog.lookup",
        )
    if not isinstance(search_req, Mapping) or not isinstance(lookup_req, Mapping) or not isinstance(bulk_snapshot, Mapping):
        return GuardDecision(
            False,
            "UCP_CATALOG_DISCOVERY_OR_SEARCH_LOOKUP_INVALID_BLOCKED",
            "search_request, lookup_request, and bulk_snapshot objects are required",
        )
    page_size = search_req.get("page_size")
    query_text = search_req.get("query")
    if not isinstance(query_text, str) or not query_text.strip() or not isinstance(page_size, int) or not (1 <= page_size <= 250):
        return GuardDecision(
            False,
            "UCP_CATALOG_DISCOVERY_OR_SEARCH_LOOKUP_INVALID_BLOCKED",
            "catalog.search requires non-empty query and page_size in 1..250",
        )
    lookup_ids = lookup_req.get("ids")
    if not isinstance(lookup_ids, Sequence) or isinstance(lookup_ids, (str, bytes)) or len(lookup_ids) == 0:
        return GuardDecision(
            False,
            "UCP_CATALOG_DISCOVERY_OR_SEARCH_LOOKUP_INVALID_BLOCKED",
            "catalog.lookup requires a non-empty list of product or variant identifiers",
        )
    if bulk_snapshot.get("web_scraping_fallback") is True or not isinstance(bulk_snapshot.get("snapshot_id"), str):
        return GuardDecision(
            False,
            "UCP_CATALOG_DISCOVERY_OR_SEARCH_LOOKUP_INVALID_BLOCKED",
            "bulk product discovery requires a signed snapshot_id and forbids ad-hoc HTML scraping fallback",
        )
    return GuardDecision(
        True,
        "UCP_BULK_CATALOG_AND_SEARCH_LOOKUP_VERIFIED",
        "UCP bulk catalog snapshot and catalog.search / catalog.lookup capabilities verified",
    )


# PR-02: UCP #591 & #420
def audit_ucp_asymmetric_key_signature_and_host_delegated_3ds2(
    payload: Mapping[str, Any],
) -> GuardDecision:
    sig_alg = payload.get("signature_algorithm")
    jwks_kid = payload.get("jwks_kid")
    three_ds2 = payload.get("three_ds2_challenge")

    if sig_alg not in {"ES256", "ES384", "ES512", "EdDSA", "RS256"}:
        return GuardDecision(
            False,
            "UCP_SYMMETRIC_KEY_OR_MERCHANT_IFRAME_3DS2_BLOCKED",
            f"UCP message verification requires asymmetric public/private key algorithm, got '{sig_alg}'",
        )
    if not isinstance(jwks_kid, str) or not jwks_kid.strip():
        return GuardDecision(
            False,
            "UCP_SYMMETRIC_KEY_OR_MERCHANT_IFRAME_3DS2_BLOCKED",
            "asymmetric signature requires non-empty jwks_kid",
        )
    if not isinstance(three_ds2, Mapping):
        return GuardDecision(
            False,
            "UCP_SYMMETRIC_KEY_OR_MERCHANT_IFRAME_3DS2_BLOCKED",
            "three_ds2_challenge object is required",
        )
    if (
        three_ds2.get("delegated_to_host") is not True
        or three_ds2.get("merchant_injected_iframe") is True
        or not str(three_ds2.get("acs_url", "")).startswith("https://")
        or not isinstance(three_ds2.get("three_ds_server_trans_id"), str)
        or not three_ds2.get("three_ds_server_trans_id", "").strip()
    ):
        return GuardDecision(
            False,
            "UCP_SYMMETRIC_KEY_OR_MERCHANT_IFRAME_3DS2_BLOCKED",
            "3DS2 challenge in native UCP must be delegated to host UI over https:// acs_url without merchant iframe injection",
        )
    return GuardDecision(
        True,
        "UCP_ASYMMETRIC_CRYPTO_AND_HOST_3DS2_VERIFIED",
        "asymmetric key signature and host-delegated 3DS2 challenge flow verified",
    )


# PR-03: UCP #112 & #63
def audit_ucp_line_item_vs_catalog_item_id_and_order_total_enum(
    payload: Mapping[str, Any],
) -> GuardDecision:
    line_items = payload.get("line_items")
    order_totals = payload.get("order_totals")
    if not isinstance(line_items, Sequence) or isinstance(line_items, (str, bytes)) or len(line_items) == 0:
        return GuardDecision(
            False,
            "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
            "line_items must be a non-empty list",
        )
    seen_line_ids: set[str] = set()
    for li in line_items:
        if not isinstance(li, Mapping):
            return GuardDecision(
                False,
                "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
                "line_item entry must be an object",
            )
        line_id = li.get("id")
        item_obj = li.get("item")
        item_id = item_obj.get("id") if isinstance(item_obj, Mapping) else None
        if not isinstance(line_id, str) or not line_id.strip() or not isinstance(item_id, str) or not item_id.strip():
            return GuardDecision(
                False,
                "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
                "both line_item.id and line_item.item.id must be non-empty strings",
            )
        if line_id == item_id or line_id in seen_line_ids:
            return GuardDecision(
                False,
                "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
                "line_item.id must be a unique checkout line identifier distinct from catalog item.id",
            )
        seen_line_ids.add(line_id)
    if not isinstance(order_totals, Sequence) or isinstance(order_totals, (str, bytes)) or len(order_totals) == 0:
        return GuardDecision(
            False,
            "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
            "order_totals must be a non-empty list",
        )
    for tot in order_totals:
        if not isinstance(tot, Mapping) or tot.get("type") not in _ORDER_TOTAL_TYPES:
            return GuardDecision(
                False,
                "UCP_LINE_ITEM_ID_COLLISION_OR_TOTAL_ENUM_MISMATCH_BLOCKED",
                f"Order TotalResponse.type '{tot.get('type') if isinstance(tot, Mapping) else tot}' is not in canonical enum",
            )
    return GuardDecision(
        True,
        "UCP_LINE_ITEM_ID_SEPARATION_AND_TOTAL_ENUM_VERIFIED",
        "distinct line_item.id vs item.id and canonical Order TotalResponse.type enum verified",
    )


# PR-04: ACP #84 & #81
def audit_acp_selected_fulfillment_singular_and_date_version_snapshot(
    payload: Mapping[str, Any],
) -> GuardDecision:
    schema_names = payload.get("schema_names")
    spec_version_dir = payload.get("spec_version_dir")
    live_edit_in_snapshot = payload.get("live_edit_in_snapshot", False)

    if not isinstance(schema_names, Sequence) or isinstance(schema_names, (str, bytes)) or len(schema_names) == 0:
        return GuardDecision(
            False,
            "ACP_DEPRECATED_PROMOTION_PLURAL_SCHEMA_OR_VERSION_DIR_INVALID_BLOCKED",
            "schema_names must be a non-empty list",
        )
    name_set = set(schema_names)
    if "AvailablePromotion" in name_set or "SelectedFulfillmentOptions" in name_set:
        return GuardDecision(
            False,
            "ACP_DEPRECATED_PROMOTION_PLURAL_SCHEMA_OR_VERSION_DIR_INVALID_BLOCKED",
            "removed AvailablePromotion or plural SelectedFulfillmentOptions schema referenced",
        )
    if "SelectedFulfillmentOption" not in name_set:
        return GuardDecision(
            False,
            "ACP_DEPRECATED_PROMOTION_PLURAL_SCHEMA_OR_VERSION_DIR_INVALID_BLOCKED",
            "canonical singular SelectedFulfillmentOption schema is required",
        )
    if not isinstance(spec_version_dir, str) or (
        spec_version_dir != "unreleased" and not _DATE_VER_RE.match(spec_version_dir)
    ):
        return GuardDecision(
            False,
            "ACP_DEPRECATED_PROMOTION_PLURAL_SCHEMA_OR_VERSION_DIR_INVALID_BLOCKED",
            "ACP spec directory must be 'unreleased' or a YYYY-MM-DD snapshot",
        )
    if spec_version_dir != "unreleased" and live_edit_in_snapshot is True:
        return GuardDecision(
            False,
            "ACP_DEPRECATED_PROMOTION_PLURAL_SCHEMA_OR_VERSION_DIR_INVALID_BLOCKED",
            "frozen YYYY-MM-DD snapshot directories are immutable; live changes must reside in 'unreleased'",
        )
    return GuardDecision(
        True,
        "ACP_SCHEMA_NAMING_AND_DATE_VERSION_SNAPSHOT_VERIFIED",
        "singular SelectedFulfillmentOption schema and YYYY-MM-DD versioning verified",
    )


# PR-05: ACP #55 & #40
def audit_acp_3ds2_challenge_flow_and_x402_payment_method(
    payload: Mapping[str, Any],
) -> GuardDecision:
    auth_flow = payload.get("acp_3ds2_flow")
    x402_method = payload.get("acp_x402_payment_method")
    if not isinstance(auth_flow, Mapping) or not isinstance(x402_method, Mapping):
        return GuardDecision(
            False,
            "ACP_3DS2_FLOW_INCOMPLETE_OR_X402_PAYMENT_INVALID_BLOCKED",
            "acp_3ds2_flow and acp_x402_payment_method objects are required",
        )
    ver = auth_flow.get("three_ds_version")
    trans_status = auth_flow.get("transaction_status")
    acs_url = auth_flow.get("acs_challenge_url")
    if (
        not isinstance(ver, str)
        or not ver.startswith("2.")
        or trans_status not in {"Y", "A", "C", "D"}
        or (trans_status in {"C", "D"} and (not isinstance(acs_url, str) or not acs_url.startswith("https://")))
    ):
        return GuardDecision(
            False,
            "ACP_3DS2_FLOW_INCOMPLETE_OR_X402_PAYMENT_INVALID_BLOCKED",
            "ACP requires_3ds flow must specify 3DS 2.x version, valid transaction_status, and https:// acs_challenge_url",
        )
    if (
        x402_method.get("type") != "x402"
        or x402_method.get("scheme") not in {"exact", "upto"}
        or not isinstance(x402_method.get("network"), str)
        or ":" not in x402_method.get("network", "")
        or not isinstance(x402_method.get("max_amount_minor"), int)
        or x402_method.get("max_amount_minor", 0) <= 0
    ):
        return GuardDecision(
            False,
            "ACP_3DS2_FLOW_INCOMPLETE_OR_X402_PAYMENT_INVALID_BLOCKED",
            "ACP x402 payment method requires type=='x402', scheme in {'exact','upto'}, CAIP-2 network, and positive max_amount_minor",
        )
    return GuardDecision(
        True,
        "ACP_3DS2_AUTHENTICATION_AND_X402_PAYMENT_VERIFIED",
        "ACP 3DS 2.x authentication flow and x402 payment method binding verified",
    )


# PR-06: AP2 #127 & #43
def audit_ap2_mandate_vc_json_schema_and_sedi_keri_guardianship(
    payload: Mapping[str, Any],
) -> GuardDecision:
    mandate_vc = payload.get("mandate_vc")
    guardianship = payload.get("sedi_keri_guardianship")
    if not isinstance(mandate_vc, Mapping) or not isinstance(guardianship, Mapping):
        return GuardDecision(
            False,
            "AP2_MANDATE_VC_SCHEMA_MISSING_OR_GUARDIAN_CAP_EXCEEDED_BLOCKED",
            "mandate_vc and sedi_keri_guardianship objects are required",
        )
    vc_types = mandate_vc.get("type")
    cred_schema = mandate_vc.get("credentialSchema")
    schema_id = cred_schema.get("id") if isinstance(cred_schema, Mapping) else None
    if (
        not isinstance(vc_types, Sequence)
        or "VerifiableCredential" not in vc_types
        or not any(t in vc_types for t in ("IntentMandateCredential", "CartMandateCredential"))
        or not isinstance(schema_id, str)
        or not schema_id.startswith("https://")
    ):
        return GuardDecision(
            False,
            "AP2_MANDATE_VC_SCHEMA_MISSING_OR_GUARDIAN_CAP_EXCEEDED_BLOCKED",
            "AP2 Mandate VC requires VerifiableCredential + Intent/CartMandateCredential types and https:// credentialSchema.id",
        )
    guardian_aid = guardianship.get("guardian_keri_aid")
    kel_verified = guardianship.get("keri_kel_verified")
    ward_spend = guardianship.get("ward_spend_minor")
    guardian_cap = guardianship.get("guardian_cap_minor")
    if (
        not isinstance(guardian_aid, str)
        or not guardian_aid.strip()
        or kel_verified is not True
        or not isinstance(ward_spend, int)
        or not isinstance(guardian_cap, int)
        or ward_spend <= 0
        or ward_spend > guardian_cap
    ):
        return GuardDecision(
            False,
            "AP2_MANDATE_VC_SCHEMA_MISSING_OR_GUARDIAN_CAP_EXCEEDED_BLOCKED",
            "SEDI/KERI guardianship requires verified KERI KEL and ward_spend_minor <= guardian_cap_minor",
        )
    return GuardDecision(
        True,
        "AP2_MANDATE_VC_SCHEMA_AND_SEDI_GUARDIANSHIP_VERIFIED",
        "AP2 published mandate VC JSON Schema and SEDI/KERI guardianship spend cap verified",
    )


# PR-07: x402 #3334 & #3330
def audit_x402_settlement_override_ceiling_and_axios_response_validator(
    payload: Mapping[str, Any],
) -> GuardDecision:
    authorized_max_minor = payload.get("authorized_max_amount_minor")
    resolved_override_minor = payload.get("resolved_override_amount_minor")
    axios_hook_configured = payload.get("axios_validate_paid_response_configured", False)
    paid_response_valid = payload.get("paid_response_schema_valid", False)

    if (
        not isinstance(authorized_max_minor, int)
        or not isinstance(resolved_override_minor, int)
        or resolved_override_minor <= 0
        or resolved_override_minor > authorized_max_minor
    ):
        return GuardDecision(
            False,
            "X402_SETTLEMENT_OVERRIDE_EXCEEDS_MAX_OR_AXIOS_RESPONSE_UNVALIDATED_BLOCKED",
            "settlePayment() resolved override amount must be > 0 and <= PaymentRequirements.amount",
        )
    if axios_hook_configured is not True or paid_response_valid is not True:
        return GuardDecision(
            False,
            "X402_SETTLEMENT_OVERRIDE_EXCEEDS_MAX_OR_AXIOS_RESPONSE_UNVALIDATED_BLOCKED",
            "@x402/axios paid response must pass the caller's validatePaidResponse hook before returning to app code",
        )
    return GuardDecision(
        True,
        "X402_SETTLEMENT_OVERRIDE_CEILING_AND_AXIOS_HOOK_VERIFIED",
        "settlePayment override ceiling <= authorized maximum and Axios paid-response validation hook verified",
    )


# PR-08: x402 #3352 & #3333
def audit_x402_stellar_smart_account_events_and_sponsored_fees(
    payload: Mapping[str, Any],
) -> GuardDecision:
    are_fees_sponsored = payload.get("are_fees_sponsored")
    diagnostic_events = payload.get("simulation_contract_events")
    false_rejected_smart_account = payload.get("rejected_non_transfer_contract_event", False)

    if are_fees_sponsored is not True:
        return GuardDecision(
            False,
            "X402_STELLAR_UNSPONSORED_FEES_OR_SMART_ACCOUNT_EVENT_REJECTED_BLOCKED",
            "ExactStellarScheme requires areFeesSponsored: true; false breaks 100% of official client settlements",
        )
    if false_rejected_smart_account is True:
        return GuardDecision(
            False,
            "X402_STELLAR_UNSPONSORED_FEES_OR_SMART_ACCOUNT_EVENT_REJECTED_BLOCKED",
            "validateSimulationEvents must not reject custom smart-account spend-cap events when valid SEP-41 transfer is present",
        )
    if not isinstance(diagnostic_events, Sequence) or isinstance(diagnostic_events, (str, bytes)) or len(diagnostic_events) == 0:
        return GuardDecision(
            False,
            "X402_STELLAR_UNSPONSORED_FEES_OR_SMART_ACCOUNT_EVENT_REJECTED_BLOCKED",
            "simulation_contract_events must be a non-empty list",
        )
    has_sep41_transfer = any(
        isinstance(ev, Mapping) and ev.get("topic") == "transfer" and ev.get("sep41_compliant") is True
        for ev in diagnostic_events
    )
    if not has_sep41_transfer:
        return GuardDecision(
            False,
            "X402_STELLAR_UNSPONSORED_FEES_OR_SMART_ACCOUNT_EVENT_REJECTED_BLOCKED",
            "Stellar simulation must include a verified SEP-41 transfer event",
        )
    return GuardDecision(
        True,
        "X402_STELLAR_SMART_ACCOUNT_EVENTS_AND_SPONSORED_FEES_VERIFIED",
        "Stellar smart-account diagnostic event tolerance and mandatory fee sponsorship verified",
    )


# PR-09: x402 #3332 & #3351
def audit_x402_stellar_fee_bump_signer_safety_and_svm_compute_unit_policy(
    payload: Mapping[str, Any],
) -> GuardDecision:
    fee_bump_signer = payload.get("stellar_fee_bump_signer")
    signing_addresses = payload.get("facilitator_safety_signing_addresses")
    tx_recipient = payload.get("stellar_tx_recipient")
    svm_cu_policy = payload.get("svm_compute_unit_policy")

    if (
        not isinstance(fee_bump_signer, str)
        or not fee_bump_signer.strip()
        or not isinstance(signing_addresses, Sequence)
        or fee_bump_signer not in signing_addresses
        or tx_recipient in signing_addresses
    ):
        return GuardDecision(
            False,
            "X402_STELLAR_FEE_BUMP_SIGNER_UNPROTECTED_OR_SVM_CU_EXCEEDED_BLOCKED",
            "feeBumpSigner must be included in facilitator safety signingAddresses and barred from self-transfer/drain",
        )
    if not isinstance(svm_cu_policy, Mapping):
        return GuardDecision(
            False,
            "X402_STELLAR_FEE_BUMP_SIGNER_UNPROTECTED_OR_SVM_CU_EXCEEDED_BLOCKED",
            "svm_compute_unit_policy object is required",
        )
    tx_cu = svm_cu_policy.get("tx_compute_unit_limit")
    op_max_cu = svm_cu_policy.get("operator_max_cu")
    if (
        not isinstance(tx_cu, int)
        or not isinstance(op_max_cu, int)
        or op_max_cu > 400_000
        or tx_cu <= 0
        or tx_cu > op_max_cu
    ):
        return GuardDecision(
            False,
            "X402_STELLAR_FEE_BUMP_SIGNER_UNPROTECTED_OR_SVM_CU_EXCEEDED_BLOCKED",
            "SVM SetComputeUnitLimit exceeds operator policy or 400,000 CU reference maximum (compute_unit_limit_exceeded)",
        )
    return GuardDecision(
        True,
        "X402_STELLAR_FEE_BUMP_SAFETY_AND_SVM_CU_POLICY_VERIFIED",
        "Stellar feeBumpSigner safety inclusion and SVM operator compute-unit policy verified",
    )


# PR-10: x402 #3381 & #3396
def audit_x402_agent_switchboard_scitt_and_declarative_conformance(
    payload: Mapping[str, Any],
) -> GuardDecision:
    switchboard = payload.get("agent_switchboard")
    conformance = payload.get("conformance_profile")
    if not isinstance(switchboard, Mapping) or not isinstance(conformance, Mapping):
        return GuardDecision(
            False,
            "X402_SWITCHBOARD_SCITT_UNATTESTED_OR_ENDPOINT_NONCONFORMANT_BLOCKED",
            "agent_switchboard and conformance_profile objects are required",
        )
    if (
        switchboard.get("protocol") != "x402.agent-switchboard/v0"
        or switchboard.get("scitt_transparency_verified") is not True
        or not isinstance(switchboard.get("relay_ttl_seconds"), int)
        or not (1 <= switchboard.get("relay_ttl_seconds", 0) <= 86400)
    ):
        return GuardDecision(
            False,
            "X402_SWITCHBOARD_SCITT_UNATTESTED_OR_ENDPOINT_NONCONFORMANT_BLOCKED",
            "x402.agent-switchboard/v0 requires verified IETF SCITT receipt and bounded relay_ttl_seconds",
        )
    if (
        not isinstance(conformance.get("spec_version"), str)
        or not conformance.get("spec_version", "").strip()
        or conformance.get("declarative_profile_valid") is not True
        or conformance.get("failed_assertions") != 0
    ):
        return GuardDecision(
            False,
            "X402_SWITCHBOARD_SCITT_UNATTESTED_OR_ENDPOINT_NONCONFORMANT_BLOCKED",
            "deployed endpoint failed declarative x402 conformance profile assertions",
        )
    return GuardDecision(
        True,
        "X402_SWITCHBOARD_SCITT_AND_CONFORMANCE_PROFILE_VERIFIED",
        "x402.agent-switchboard/v0 SCITT attestation and declarative conformance profile verified",
    )


# PR-11: x402 #3677 & #3638
def audit_x402_bazaar_indexing_readiness_preflight(
    payload: Mapping[str, Any],
) -> GuardDecision:
    bazaar_in_402 = payload.get("bazaar_extension_present_in_402")
    io_schema_valid = payload.get("bazaar_input_output_schema_valid")
    public_https = payload.get("resource_url_public_https")
    cdp_settlement_seen = payload.get("cdp_facilitator_settlement_confirmed")

    if (
        bazaar_in_402 is not True
        or io_schema_valid is not True
        or public_https is not True
        or cdp_settlement_seen is not True
    ):
        return GuardDecision(
            False,
            "X402_BAZAAR_SILENT_INDEXING_BLOCKER_DETECTED",
            "Bazaar discovery indexing requires extensions.bazaar in 402 response, valid I/O schema, public HTTPS URL, and confirmed CDP settlement",
        )
    return GuardDecision(
        True,
        "X402_BAZAAR_INDEXING_READINESS_VERIFIED",
        "all CDP Bazaar settlement-driven indexing preflight requirements verified",
    )


# PR-12: x402 #3645 & #3633
def audit_x402_kaspa_and_bch_utxo_exact_settlement(
    payload: Mapping[str, Any],
) -> GuardDecision:
    kaspa = payload.get("kaspa_exact")
    bch = payload.get("bch_exact")
    if not isinstance(kaspa, Mapping) or not isinstance(bch, Mapping):
        return GuardDecision(
            False,
            "X402_KASPA_OR_BCH_UTXO_CONSERVATION_VIOLATION_BLOCKED",
            "kaspa_exact and bch_exact objects are required",
        )
    kas_net = kaspa.get("network")
    kas_paid = kaspa.get("output_sompi")
    kas_req = kaspa.get("required_sompi")
    kas_rbf = kaspa.get("unconfirmed_rbf_replaceable", False)
    if (
        not isinstance(kas_net, str)
        or not kas_net.startswith("kaspa:")
        or not isinstance(kas_paid, int)
        or not isinstance(kas_req, int)
        or kas_req <= 0
        or kas_paid < kas_req
        or kas_rbf is True
    ):
        return GuardDecision(
            False,
            "X402_KASPA_OR_BCH_UTXO_CONSERVATION_VIOLATION_BLOCKED",
            "Kaspa exact binding requires kaspa: network, output_sompi >= required_sompi, and non-RBF finality",
        )
    bch_sats = bch.get("output_satoshis")
    bch_req = bch.get("required_satoshis")
    sighash_forkid = bch.get("sighash_forkid_set")
    if (
        not isinstance(bch_sats, int)
        or not isinstance(bch_req, int)
        or bch_sats < 546
        or bch_sats < bch_req
        or sighash_forkid is not True
    ):
        return GuardDecision(
            False,
            "X402_KASPA_OR_BCH_UTXO_CONSERVATION_VIOLATION_BLOCKED",
            "BCH exact binding requires satoshis >= 546 dust limit, output >= required, and SIGHASH_FORKID",
        )
    return GuardDecision(
        True,
        "X402_KASPA_AND_BCH_UTXO_EXACT_SETTLEMENT_VERIFIED",
        "Kaspa Sompi and Bitcoin Cash Satoshi UTXO exact settlement bindings verified",
    )


# PR-13: MCP #2991 & #2989
def audit_mcp_sep2243_header_mismatch_32020_and_subscriptions_listen_envelope(
    payload: Mapping[str, Any],
) -> GuardDecision:
    header_mismatch_code = payload.get("header_mismatch_error_code")
    listen_response = payload.get("subscriptions_listen_response")

    if header_mismatch_code != -32020:
        return GuardDecision(
            False,
            "MCP_STALE_HEADER_MISMATCH_32001_OR_MISSING_LISTEN_ENVELOPE_BLOCKED",
            f"SEP-2243 HeaderMismatch error code must be renumbered -32020 (got {header_mismatch_code})",
        )
    if not isinstance(listen_response, Mapping):
        return GuardDecision(
            False,
            "MCP_STALE_HEADER_MISMATCH_32001_OR_MISSING_LISTEN_ENVELOPE_BLOCKED",
            "subscriptions_listen_response object is required",
        )
    if (
        listen_response.get("envelope_type") != "SubscriptionsListenResultResponse"
        or listen_response.get("meta_type") != "SubscriptionsListenResultMeta"
    ):
        return GuardDecision(
            False,
            "MCP_STALE_HEADER_MISMATCH_32001_OR_MISSING_LISTEN_ENVELOPE_BLOCKED",
            "subscriptions/listen requires dedicated SubscriptionsListenResultResponse and SubscriptionsListenResultMeta",
        )
    return GuardDecision(
        True,
        "MCP_HEADER_MISMATCH_32020_AND_LISTEN_ENVELOPE_VERIFIED",
        "SEP-2243 HeaderMismatch -32020 code and subscriptions/listen response envelope verified",
    )


# PR-14: MCP #2188 & #2166
def audit_mcp_elicitation_pending_timeout_and_oob_https_resource(
    payload: Mapping[str, Any],
) -> GuardDecision:
    pending_notif = payload.get("elicitation_pending_notification")
    oob_resource = payload.get("oob_resource")
    if not isinstance(pending_notif, Mapping) or not isinstance(oob_resource, Mapping):
        return GuardDecision(
            False,
            "MCP_ELICITATION_TIMEOUT_UNCOORDINATED_OR_INSECURE_HTTP_URL_BLOCKED",
            "elicitation_pending_notification and oob_resource objects are required",
        )
    if (
        pending_notif.get("method") != "notifications/elicitation/pending"
        or not isinstance(pending_notif.get("elicitationId"), str)
        or not pending_notif.get("elicitationId", "").strip()
        or pending_notif.get("client_timeout_extended") is not True
    ):
        return GuardDecision(
            False,
            "MCP_ELICITATION_TIMEOUT_UNCOORDINATED_OR_INSECURE_HTTP_URL_BLOCKED",
            "SEP-2188 requires notifications/elicitation/pending with elicitationId and coordinated client timeout extension",
        )
    http_url = oob_resource.get("httpUrl")
    expires_at = oob_resource.get("httpUrlExpiresAt")
    now_epoch = oob_resource.get("now_epoch")
    if (
        not isinstance(http_url, str)
        or not http_url.startswith("https://")
        or not isinstance(expires_at, int)
        or not isinstance(now_epoch, int)
        or now_epoch >= expires_at
    ):
        return GuardDecision(
            False,
            "MCP_ELICITATION_TIMEOUT_UNCOORDINATED_OR_INSECURE_HTTP_URL_BLOCKED",
            "SEP-2166 out-of-band resource access requires https:// httpUrl and unexpired httpUrlExpiresAt",
        )
    return GuardDecision(
        True,
        "MCP_ELICITATION_PENDING_AND_OOB_HTTPS_RESOURCE_VERIFIED",
        "SEP-2188 elicitation timeout coordination and SEP-2166 HTTPS resource URL verified",
    )


# PR-15: tau2-bench #104 & #81
def audit_tau2_telecom_refuel_upper_bound_and_action_reward_basis(
    payload: Mapping[str, Any],
) -> GuardDecision:
    refuel_gb = payload.get("refuel_data_gb")
    user_needed_gb = payload.get("user_needed_data_gb")
    hardcoded_exact_2gb_enforced = payload.get("hardcoded_exact_2gb_enforced", False)
    reward_basis = payload.get("reward_basis")

    if hardcoded_exact_2gb_enforced is True:
        return GuardDecision(
            False,
            "TAU2_HARDCODED_2GB_REFUEL_OR_MISSING_ACTION_REWARD_BASIS_BLOCKED",
            "Telecom policy states 2GB is the maximum refuel limit, not a mandatory exact 2.0GB requirement",
        )
    if (
        not isinstance(refuel_gb, (int, float))
        or not isinstance(user_needed_gb, (int, float))
        or refuel_gb <= 0
        or refuel_gb > 2.0
        or refuel_gb < user_needed_gb
    ):
        return GuardDecision(
            False,
            "TAU2_HARDCODED_2GB_REFUEL_OR_MISSING_ACTION_REWARD_BASIS_BLOCKED",
            "refuel_data_gb must satisfy user_needed_data_gb and not exceed the 2.0GB policy maximum",
        )
    if not isinstance(reward_basis, Sequence) or "ACTION" not in reward_basis:
        return GuardDecision(
            False,
            "TAU2_HARDCODED_2GB_REFUEL_OR_MISSING_ACTION_REWARD_BASIS_BLOCKED",
            "default reward_basis must include 'ACTION' so expected tool actions are evaluated",
        )
    return GuardDecision(
        True,
        "TAU2_TELECOM_REFUEL_BOUND_AND_ACTION_REWARD_BASIS_VERIFIED",
        "Telecom <=2.0GB refuel upper bound policy and ACTION reward_basis inclusion verified",
    )


# PR-16: tau2-bench #84 & #43
def audit_tau2_airline_cancellation_eligibility_and_agent_msg_validation_catch(
    payload: Mapping[str, Any],
) -> GuardDecision:
    booking = payload.get("booking_cancellation_check")
    unhandled_validate_exception = payload.get("unhandled_agent_msg_validate_exception", False)

    if unhandled_validate_exception is True:
        return GuardDecision(
            False,
            "TAU2_IMPOSSIBLE_CANCELLATION_EXPECTATION_OR_VALIDATE_CRASH_BLOCKED",
            "exceptions in agent_msg.validate() must be caught and handled gracefully",
        )
    if not isinstance(booking, Mapping):
        return GuardDecision(
            False,
            "TAU2_IMPOSSIBLE_CANCELLATION_EXPECTATION_OR_VALIDATE_CRASH_BLOCKED",
            "booking_cancellation_check object is required",
        )
    eligible = any(
        booking.get(k) is True
        for k in (
            "booked_within_24h",
            "flight_cancelled_by_airline",
            "is_business_class",
            "covered_by_travel_insurance",
        )
    )
    expected_cancelled = booking.get("test_expects_cancelled")
    if expected_cancelled is True and not eligible:
        return GuardDecision(
            False,
            "TAU2_IMPOSSIBLE_CANCELLATION_EXPECTATION_OR_VALIDATE_CRASH_BLOCKED",
            "task test expectation requires cancelling an ineligible booking contrary to airline cancellation policy",
        )
    return GuardDecision(
        True,
        "TAU2_AIRLINE_CANCELLATION_POLICY_AND_VALIDATE_GUARD_VERIFIED",
        "airline cancellation policy eligibility consistency and graceful agent_msg validation verified",
    )
