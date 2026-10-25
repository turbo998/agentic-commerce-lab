"""Stage 234 (235-Stage Milestone!) deterministic protocol security guards (`PR-01..PR-16`).

Covers 38 primary-source upstream PRs across x402 Foundation (`#3923`, `#3921`, `#3916`, `#3903`,
`#3911`, `#3897`, `#3888`, `#3915`), Universal Commerce Protocol (`#946`, `#945`, `#938`, `#899`,
`#916`, `#908`, `#893`, `#976`, `#963`, `#934`, `#917`, `#912`), Agentic Commerce Protocol (`#296`,
`#288`, `#287`, `#285`, `#273`), Google AP2 (`#365`, `#364`, `#363`, `#359`, `#352`), Model Context
Protocol Spec SEPs (`#3371`, `#3364`, `#3279`, `#2847`, `#3185`, `#3118`, `#3094`, `#2632`, `#3235`,
`#3191`, `#2781`), and MCP Inspector (`#2796`, `#2794`, `#2792`, `#2790`, `#2795`, `#2777`, `#2774`, `#2801`).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    reason: str
    evidence: dict[str, Any]


def evaluate_x402_svm_pending_batch_recovery_and_settle_seal_payout_guard(
    *,
    retained_pending_channels: list[str],
    new_candidate_channels: list[str],
    regrouped_before_pending_recovery: bool,
    single_active_redemption_owner: bool,
    settle_seal_confirmed: bool,
    confirmed_tx_token_balance_delta_minor: int,
    recorded_merchant_payout_minor: int,
    payer_refund_amount_unchanged: bool,
    callback_deduped_by_network_and_tx: bool,
    ambiguous_evidence: bool,
    returned_status: str,
) -> GuardEvaluation:
    """PR-01: x402 #3923 & #3921 SVM pending batch recovery journal & Go SettleSeal payout attribution."""
    if not single_active_redemption_owner:
        return GuardEvaluation(
            passed=False,
            decision_code="SVM_JOURNAL_MULTIPLE_REDEMPTION_OWNERS_REJECTED",
            reason="SVM pending distribution recovery requires a single active redemption owner per journal scope (#3923).",
            evidence={"single_active_redemption_owner": single_active_redemption_owner},
        )
    overlap = set(retained_pending_channels).intersection(new_candidate_channels)
    if retained_pending_channels and regrouped_before_pending_recovery and overlap:
        return GuardEvaluation(
            passed=False,
            decision_code="SVM_PENDING_BATCH_REGROUPED_BEFORE_RECOVERY",
            reason="Retained pending SVM distribution channels must be recovered before regrouping into new batches (#3923).",
            evidence={"overlap": sorted(overlap)},
        )
    if ambiguous_evidence:
        if returned_status != "settlement_pending":
            return GuardEvaluation(
                passed=False,
                decision_code="SVM_AMBIGUOUS_CLOSE_EVIDENCE_MUST_RETURN_PENDING",
                reason="Missing or ambiguous cooperative-close evidence must return settlement_pending (#3921).",
                evidence={"returned_status": returned_status},
            )
    elif settle_seal_confirmed:
        if (
            recorded_merchant_payout_minor != confirmed_tx_token_balance_delta_minor
            or not payer_refund_amount_unchanged
            or not callback_deduped_by_network_and_tx
        ):
            return GuardEvaluation(
                passed=False,
                decision_code="SVM_SETTLE_SEAL_PAYOUT_ATTRIBUTION_INVALID",
                reason="SettleSeal must record merchant payout from confirmed token-balance delta and deduplicate callbacks (#3921).",
                evidence={
                    "confirmed_tx_token_balance_delta_minor": confirmed_tx_token_balance_delta_minor,
                    "recorded_merchant_payout_minor": recorded_merchant_payout_minor,
                    "payer_refund_amount_unchanged": payer_refund_amount_unchanged,
                    "callback_deduped_by_network_and_tx": callback_deduped_by_network_and_tx,
                },
            )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_SVM_PENDING_RECOVERY_AND_SETTLE_SEAL_VERIFIED",
        reason="SVM pending batch recovery journal and SettleSeal cooperative-close payout attribution verified.",
        evidence={"recorded_merchant_payout_minor": recorded_merchant_payout_minor},
    )


def evaluate_x402_go_read_signer_allowance_py_gas_warn_and_mcp_hooks_guard(
    *,
    signer_has_direct_read_contract: bool,
    fallback_rpc_url_configured: bool,
    resolved_via_read_signer_helper: bool,
    attempted_allowance_read_without_rpc: bool,
    server_advertises_gas_sponsoring: bool,
    py_signer_can_read_chain: bool,
    py_logged_once_per_network_with_rpc_url_hint: bool,
    py_gas_sponsoring_skipped_cleanly: bool,
    py_mcp_sync_hooks_supported: set[str],
) -> GuardEvaluation:
    """PR-02: x402 #3916, #3903 & #3911 Go resolveReadSigner, Python gas-sponsoring warning & MCP sync hooks."""
    if attempted_allowance_read_without_rpc:
        return GuardEvaluation(
            passed=False,
            decision_code="GO_ALLOWANCE_READ_WITHOUT_RPC_CLIENT_REJECTED",
            reason="Signers without an RPC client must not issue ERC-20 allowance reads that can only fail (#3916).",
            evidence={"attempted_allowance_read_without_rpc": attempted_allowance_read_without_rpc},
        )
    if not signer_has_direct_read_contract and fallback_rpc_url_configured and not resolved_via_read_signer_helper:
        return GuardEvaluation(
            passed=False,
            decision_code="GO_ALLOWANCE_SHORT_CIRCUIT_BYPASSED_RESOLVE_READ_SIGNER",
            reason="Go exact/upto ERC-20 allowance checks must resolve fallback RPCURL via resolveReadSigner (#3916).",
            evidence={"resolved_via_read_signer_helper": resolved_via_read_signer_helper},
        )
    if server_advertises_gas_sponsoring and not py_signer_can_read_chain:
        if not py_logged_once_per_network_with_rpc_url_hint or not py_gas_sponsoring_skipped_cleanly:
            return GuardEvaluation(
                passed=False,
                decision_code="PY_GAS_SPONSORING_MISSING_CHAIN_READ_WARNING",
                reason="Python gas sponsoring must warn once per network naming EthAccountSignerWithRPC/rpc_url and skip (#3903).",
                evidence={
                    "py_logged_once_per_network_with_rpc_url_hint": py_logged_once_per_network_with_rpc_url_hint,
                    "py_gas_sponsoring_skipped_cleanly": py_gas_sponsoring_skipped_cleanly,
                },
            )
    required_hooks = {"on_payment_required", "on_before_payment", "on_after_payment"}
    if not required_hooks.issubset(py_mcp_sync_hooks_supported):
        return GuardEvaluation(
            passed=False,
            decision_code="PY_MCP_SYNC_CLIENT_HOOKS_PARITY_MISSING",
            reason="Python x402MCPClientSync must support on_payment_required, on_before_payment, and on_after_payment (#3911).",
            evidence={"supported": sorted(py_mcp_sync_hooks_supported)},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_GO_READ_SIGNER_PY_GAS_WARN_AND_MCP_HOOKS_VERIFIED",
        reason="Go resolveReadSigner allowance check, Python gas-sponsoring warning, and MCP sync hooks verified.",
        evidence={"hooks": sorted(py_mcp_sync_hooks_supported)},
    )


def evaluate_x402_jcs_receipts_halvorai_instruction_and_extension_interop_guard(
    *,
    receipt_canonicalization: str,
    receipt_signature_alg: str,
    caip_payer: str,
    caip_payee: str,
    caip_network: str,
    offline_verified_with_issuer_pubkey: bool,
    halvor_agent_id: str,
    halvor_owner_id: str,
    halvor_instruction_sha256: str,
    extension_touches_wire_extensions_field: bool,
    extension_listed_section: str,
) -> GuardEvaluation:
    """PR-03: x402 #3897, #3888 & #3915 x402-receipts JCS Ed25519, HalvorAI instruction binding & extension split."""
    if (
        receipt_canonicalization != "RFC8785_JCS"
        or receipt_signature_alg != "ed25519"
        or not offline_verified_with_issuer_pubkey
        or ":" not in caip_payer
        or ":" not in caip_payee
        or ":" not in caip_network
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_RECEIPTS_JCS_ED25519_OR_CAIP_INVALID",
            reason="x402-receipts requires Ed25519 over RFC 8785 JCS JSON with CAIP payer, payee, and network IDs (#3897).",
            evidence={
                "receipt_canonicalization": receipt_canonicalization,
                "receipt_signature_alg": receipt_signature_alg,
                "offline_verified_with_issuer_pubkey": offline_verified_with_issuer_pubkey,
            },
        )
    if not halvor_agent_id or not halvor_owner_id or len(halvor_instruction_sha256) != 64:
        return GuardEvaluation(
            passed=False,
            decision_code="HALVORAI_INSTRUCTION_PAYMENT_BINDING_INVALID",
            reason="HalvorAI payment signatures must attach agent, owner, and 64-hex SHA-256 instruction hash (#3888).",
            evidence={"halvor_instruction_sha256": halvor_instruction_sha256},
        )
    expected_section = "payload_extensions" if extension_touches_wire_extensions_field else "adjacent_utilities"
    if extension_listed_section != expected_section:
        return GuardEvaluation(
            passed=False,
            decision_code="THIRD_PARTY_EXTENSION_INTEROP_SECTION_MISMATCH",
            reason="Packages must be classified by whether they read/write the wire x402 payload extensions field (#3915).",
            evidence={"expected_section": expected_section, "actual_section": extension_listed_section},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_JCS_RECEIPTS_HALVORAI_AND_INTEROP_SPLIT_VERIFIED",
        reason="x402-receipts offline JCS Ed25519 receipt, HalvorAI instruction binding, and interop classification verified.",
        evidence={"caip_network": caip_network, "section": extension_listed_section},
    )


def evaluate_ucp_post_order_consultation_and_cancellation_modification_guard(
    *,
    capability_name: str,
    schema_url: str,
    parent_order_capability_active: bool,
    proposal_revision_id: str,
    decision_target_revision_id: str,
    prior_terminal_decision_recorded: bool,
    modification_op: str,
    base_order_version: str,
    current_order_version: str,
    lookup_changed_admission_state: bool,
    lookup_key_in_header_not_url: bool,
    fence_has_fresh_idempotency_key: bool,
    cache_control_header: str,
) -> GuardEvaluation:
    """PR-04: UCP #946 & #945 post-order consultation (EP #944) and cancellation-first order modification (EP #943)."""
    parsed = urlparse(schema_url)
    host_labels = [p for p in (parsed.hostname or "").split(".") if p]
    derived_prefix = ".".join(reversed(host_labels))
    if parsed.scheme != "https" or not derived_prefix or not capability_name.startswith(derived_prefix + "."):
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_EXTENSION_SCHEMA_AUTHORITY_BINDING_FAILED",
            reason="Capability namespace must match reversed HTTPS schema host authority prefix (#946, #945).",
            evidence={"capability_name": capability_name, "schema_url": schema_url, "derived_prefix": derived_prefix},
        )
    if not parent_order_capability_active:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_ORDER_EXTENSION_WITHOUT_ACTIVE_PARENT_REJECTED",
            reason="Order consultation/modification extensions must be pruned when parent Order capability is inactive (#946, #945).",
            evidence={"parent_order_capability_active": parent_order_capability_active},
        )
    if prior_terminal_decision_recorded or proposal_revision_id != decision_target_revision_id:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_CONSULTATION_REVISION_OR_TERMINAL_DECISION_VIOLATION",
            reason="Order consultation permits exactly one terminal approve/decline bound to the exact revision_id (#946).",
            evidence={
                "proposal_revision_id": proposal_revision_id,
                "decision_target_revision_id": decision_target_revision_id,
                "prior_terminal_decision_recorded": prior_terminal_decision_recorded,
            },
        )
    if (
        modification_op != "cancel"
        or base_order_version != current_order_version
        or lookup_changed_admission_state
        or not lookup_key_in_header_not_url
        or not fence_has_fresh_idempotency_key
        or cache_control_header != "no-store"
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_ORDER_MODIFICATION_CONTRACT_VIOLATION",
            reason="Order modification only enables cancel with matching base_order_version, safe lookup, fresh fence key, and no-store (#945).",
            evidence={
                "modification_op": modification_op,
                "base_order_version": base_order_version,
                "current_order_version": current_order_version,
                "lookup_changed_admission_state": lookup_changed_admission_state,
                "fence_has_fresh_idempotency_key": fence_has_fresh_idempotency_key,
                "cache_control_header": cache_control_header,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="UCP_CONSULTATION_AND_CANCELLATION_MODIFICATION_VERIFIED",
        reason="UCP post-order consultation and cancellation-first order modification invariants verified.",
        evidence={"capability_name": capability_name, "order_version": current_order_version},
    )


def evaluate_ucp_capability_event_webhooks_and_common_ui_binding_guard(
    *,
    business_webhook_events: list[str],
    platform_webhook_events: list[str] | None,
    delivered_events: list[str],
    platform_recognized_by_business: bool,
    webhook_rfc9421_signed: bool,
    response_valid_without_ui: bool,
    ui_payload_contains_executable_html: bool,
    ui_action_bypasses_buyer_consent: bool,
) -> GuardEvaluation:
    """PR-05: UCP #938 capability event webhooks (`config.webhook`) & #899 `dev.ucp.common.ui` A2UI/MCP Apps."""
    if not platform_recognized_by_business or not webhook_rfc9421_signed:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_CAPABILITY_WEBHOOK_UNRECOGNIZED_PLATFORM_OR_UNSIGNED",
            reason="Capability event webhooks require a recognized platform and RFC 9421 signature verification (#938).",
            evidence={
                "platform_recognized_by_business": platform_recognized_by_business,
                "webhook_rfc9421_signed": webhook_rfc9421_signed,
            },
        )
    expected_set = (
        set(business_webhook_events)
        if platform_webhook_events is None
        else set(business_webhook_events).intersection(platform_webhook_events)
    )
    if set(delivered_events) != expected_set:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_CAPABILITY_WEBHOOK_INTERSECTION_MISMATCH",
            reason="Delivered capability webhook events must equal the intersection of business and platform event sets (#938).",
            evidence={"expected": sorted(expected_set), "delivered": sorted(delivered_events)},
        )
    if not response_valid_without_ui or ui_payload_contains_executable_html or ui_action_bypasses_buyer_consent:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_COMMON_UI_SANDOX_OR_CONSENT_VIOLATION",
            reason="UCP responses must stay complete without ui, keep executable HTML out of ui field, and enforce buyer consent (#899).",
            evidence={
                "response_valid_without_ui": response_valid_without_ui,
                "ui_payload_contains_executable_html": ui_payload_contains_executable_html,
                "ui_action_bypasses_buyer_consent": ui_action_bypasses_buyer_consent,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="UCP_CAPABILITY_WEBHOOKS_AND_COMMON_UI_VERIFIED",
        reason="UCP capability event webhooks and dev.ucp.common.ui A2UI/MCP Apps bindings verified.",
        evidence={"delivered_events": sorted(delivered_events)},
    )


def evaluate_ucp_ap2_mandate_tokenize_deferred_empty_payment_and_split_redaction_guard(
    *,
    ap2_negotiated: bool,
    tokenize_credential_type: str,
    payment_mandate_sd_jwt_kb_present: bool,
    checkout_jwt_present: bool,
    mandate_tx_id_matches_checkout_jwt: bool,
    complete_checkout_carries_opaque_token: bool,
    deferred_payment_term: bool,
    complete_payment_object: dict[str, Any],
    split_payment_response_instruments: list[dict[str, Any]],
) -> GuardEvaluation:
    """PR-06: UCP #916 AP2 mandate /tokenize step, #908 deferred empty payment: {} & #893 split credential redaction."""
    if ap2_negotiated:
        if (
            tokenize_credential_type != "ap2_payment_mandate"
            or not payment_mandate_sd_jwt_kb_present
            or not checkout_jwt_present
            or not mandate_tx_id_matches_checkout_jwt
            or not complete_checkout_carries_opaque_token
        ):
            return GuardEvaluation(
                passed=False,
                decision_code="payment_mandate_required",
                reason="AP2 flow requires Step 3 /tokenize verification of ap2_payment_mandate + checkout_jwt before complete (#916).",
                evidence={
                    "tokenize_credential_type": tokenize_credential_type,
                    "mandate_tx_id_matches_checkout_jwt": mandate_tx_id_matches_checkout_jwt,
                    "complete_checkout_carries_opaque_token": complete_checkout_carries_opaque_token,
                },
            )
    if deferred_payment_term and complete_payment_object != {}:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_DEFERRED_TERM_COMPLETE_PAYMENT_MUST_BE_EMPTY_OBJECT",
            reason="Fully deferred payment terms require payment: {} with selected_term_id omitted on complete_checkout (#908).",
            evidence={"complete_payment_object": complete_payment_object},
        )
    for inst in split_payment_response_instruments:
        if "credential" in inst:
            return GuardEvaluation(
                passed=False,
                decision_code="UCP_SPLIT_PAYMENT_RESPONSE_CREDENTIAL_ECHO_FORBIDDEN",
                reason="Businesses MUST NOT echo payment credentials back in split-payment responses (#893).",
                evidence={"instrument_id": inst.get("id", "unknown")},
            )
    return GuardEvaluation(
        passed=True,
        decision_code="UCP_AP2_TOKENIZE_DEFERRED_EMPTY_AND_SPLIT_REDACTION_VERIFIED",
        reason="AP2 mandate token issuance, deferred empty payment object, and split-payment credential redaction verified.",
        evidence={"ap2_negotiated": ap2_negotiated, "deferred_payment_term": deferred_payment_term},
    )


def evaluate_ucp_bundle_parent_id_ecdsa_raw_rs_content_digest_and_escalation_url_guard(
    *,
    line_items: list[dict[str, Any]],
    reported_subtotal_minor: int,
    ecdsa_curve: str,
    signature_bytes: bytes,
    raw_http_body_bytes: bytes,
    content_digest_b64_sha256: str,
    checkout_status: str,
    continue_url: str | None,
) -> GuardEvaluation:
    """PR-07: UCP #976 bundle parent_id totals, #963/#934 raw r||s ECDSA, #917 raw-byte Content-Digest & #912 continue_url."""
    known_ids = {item["id"] for item in line_items if "id" in item}
    top_level_sum = 0
    for item in line_items:
        parent_id = item.get("parent_id")
        if parent_id is not None:
            if parent_id not in known_ids or parent_id == item.get("id"):
                return GuardEvaluation(
                    passed=False,
                    decision_code="UCP_BUNDLE_PARENT_ID_REFERENCE_INVALID",
                    reason="Nested line item parent_id must reference a valid parent bundle line item (#976).",
                    evidence={"item_id": item.get("id"), "parent_id": parent_id},
                )
        else:
            top_level_sum += int(item.get("total_minor", 0))
    if reported_subtotal_minor != top_level_sum:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_BUNDLE_COMPONENT_TOTAL_DOUBLE_COUNTED",
            reason="Component line items with parent_id are a breakdown of parent totals and MUST NOT be additive (#976).",
            evidence={"reported_subtotal_minor": reported_subtotal_minor, "expected_top_level_sum": top_level_sum},
        )
    expected_len = 64 if ecdsa_curve == "P-256" else (96 if ecdsa_curve == "P-384" else -1)
    if len(signature_bytes) != expected_len or (signature_bytes and signature_bytes[0] == 0x30):
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_ECDSA_ASN1_DER_OR_WRONG_WIDTH_REJECTED",
            reason="ECDSA signatures MUST use fixed-width raw r||s (64B P-256 §3.3.4, 96B P-384 §3.3.5), not ASN.1 DER (#963, #934).",
            evidence={"ecdsa_curve": ecdsa_curve, "len": len(signature_bytes)},
        )
    expected_digest_hex = hashlib.sha256(raw_http_body_bytes).hexdigest()
    if content_digest_b64_sha256 != expected_digest_hex:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_CONTENT_DIGEST_RAW_BODY_BYTES_MISMATCH",
            reason="Content-Digest MUST hash the raw HTTP body bytes per RFC 9530, not JCS-canonicalized JSON (#917).",
            evidence={"expected_sha256": expected_digest_hex, "actual": content_digest_b64_sha256},
        )
    if checkout_status == "requires_escalation" and not continue_url:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_REQUIRES_ESCALATION_MISSING_CONTINUE_URL",
            reason="Checkout responses with status=requires_escalation MUST include continue_url (#912).",
            evidence={"checkout_status": checkout_status, "continue_url": continue_url},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="UCP_BUNDLE_ECDSA_RAW_RS_DIGEST_AND_ESCALATION_VERIFIED",
        reason="Nested bundle totals, fixed-width raw r||s ECDSA, RFC 9530 Content-Digest, and escalation continue_url verified.",
        evidence={"subtotal_minor": reported_subtotal_minor, "ecdsa_curve": ecdsa_curve},
    )


def evaluate_acp_mcp_idempotency_delegate_signature_timestamp_and_server_timing_guard(
    *,
    mcp_tool_is_mutating: bool,
    idempotency_key: str | None,
    delegate_operation: str,
    signature_header: str | None,
    timestamp_header: str | None,
    server_timing_header: str | None,
) -> GuardEvaluation:
    """PR-08: ACP #296, #288, #287, #285 & #273 MCP Idempotency-Key, delegate Signature/Timestamp & Server-Timing."""
    if mcp_tool_is_mutating and not idempotency_key:
        return GuardEvaluation(
            passed=False,
            decision_code="ACP_MUTATING_MCP_TOOL_MISSING_IDEMPOTENCY_KEY",
            reason="Mutating ACP MCP checkout tools require an Idempotency-Key (#296).",
            evidence={"mcp_tool_is_mutating": mcp_tool_is_mutating},
        )
    if delegate_operation in {"delegate_payment", "delegate_authentication"}:
        if not signature_header or not timestamp_header:
            return GuardEvaluation(
                passed=False,
                decision_code="ACP_DELEGATE_MISSING_SIGNATURE_OR_TIMESTAMP",
                reason="ACP delegate_payment and delegate_authentication require both Signature and Timestamp headers (#288, #287, #285).",
                evidence={"delegate_operation": delegate_operation, "has_signature": bool(signature_header)},
            )
    if not server_timing_header or "dur=" not in server_timing_header:
        return GuardEvaluation(
            passed=False,
            decision_code="ACP_SERVER_TIMING_HEADER_INVALID",
            reason="ACP responses must format Server-Timing metrics with duration parameters (#273).",
            evidence={"server_timing_header": server_timing_header},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="ACP_MCP_IDEMPOTENCY_DELEGATE_SIG_AND_TIMING_VERIFIED",
        reason="ACP mutating MCP Idempotency-Key, delegate Signature/Timestamp headers, and Server-Timing verified.",
        evidence={"delegate_operation": delegate_operation},
    )


def evaluate_ap2_presented_checkout_hash_multihop_present_ec_receipt_and_dispute_guard(
    *,
    closed_mandate_checkout_hash: str,
    presented_checkout_jwt: str,
    multihop_chain_tokens: list[str],
    last_hop_isolated_for_redaction: bool,
    prior_hop_disclosure_tampered: bool,
    receipt_public_key_kind: str,
    normalized_ec_pubkey_via_jwk: bool,
    plaintext_logs_contain_sensitive_artifacts: bool,
    dispute_payment_mandate_tx_id: str,
    dispute_receipt_references: list[str],
) -> GuardEvaluation:
    """PR-09: Google AP2 #359, #363, #365, #364 & #352 presented checkout hash, multi-hop present, EC receipt & dispute."""
    computed_checkout_hash = hashlib.sha256(presented_checkout_jwt.encode("utf-8")).hexdigest()
    if computed_checkout_hash != closed_mandate_checkout_hash:
        return GuardEvaluation(
            passed=False,
            decision_code="AP2_PRESENTED_CHECKOUT_JWT_HASH_MISMATCH",
            reason="CheckoutMandateChain.verify() must always compare H(presented_checkout_jwt) with closed_mandate.checkout_hash (#359).",
            evidence={"expected": closed_mandate_checkout_hash, "computed": computed_checkout_hash},
        )
    if len(multihop_chain_tokens) > 1 and (not last_hop_isolated_for_redaction or prior_hop_disclosure_tampered):
        return GuardEvaluation(
            passed=False,
            decision_code="AP2_MULTIHOP_PRESENT_ISOLATION_OR_TAMPER_FAILURE",
            reason="MandateClient.present() must isolate the final SD-JWT hop and reject tampered prior-hop disclosures (#363).",
            evidence={
                "hops": len(multihop_chain_tokens),
                "last_hop_isolated_for_redaction": last_hop_isolated_for_redaction,
                "prior_hop_disclosure_tampered": prior_hop_disclosure_tampered,
            },
        )
    if receipt_public_key_kind == "pyca_ec_public_key" and not normalized_ec_pubkey_via_jwk:
        return GuardEvaluation(
            passed=False,
            decision_code="AP2_VERIFY_RECEIPT_EC_PUBLIC_KEY_NOT_NORMALIZED",
            reason="ReceiptClient.verify_receipt must normalize cryptography EC public keys via JWK.from_pyca (#365).",
            evidence={"receipt_public_key_kind": receipt_public_key_kind},
        )
    if plaintext_logs_contain_sensitive_artifacts:
        return GuardEvaluation(
            passed=False,
            decision_code="AP2_SENSITIVE_PAYMENT_ARTIFACTS_LOGGED",
            reason="AP2 HTTP/FastMCP/merchant/processor logs must never write tokens, mandates, or risk_data to plaintext (#364).",
            evidence={"plaintext_logs_contain_sensitive_artifacts": True},
        )
    if dispute_payment_mandate_tx_id != closed_mandate_checkout_hash or any(
        ref != closed_mandate_checkout_hash for ref in dispute_receipt_references
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="AP2_DISPUTE_AUTHORIZATION_CHAIN_REFERENCE_MISMATCH",
            reason="Post-transaction dispute resolution requires payment_mandate.transaction_id and both receipts to match checkout_hash (#352).",
            evidence={
                "closed_mandate_checkout_hash": closed_mandate_checkout_hash,
                "dispute_payment_mandate_tx_id": dispute_payment_mandate_tx_id,
                "dispute_receipt_references": dispute_receipt_references,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="AP2_CHECKOUT_HASH_MULTIHOP_RECEIPT_AND_DISPUTE_VERIFIED",
        reason="AP2 presented checkout hash, multi-hop present isolation, EC receipt verification, and dispute chain verified.",
        evidence={"checkout_hash": computed_checkout_hash},
    )


def evaluate_mcp_sep3371_sdk_extension_points_and_versioned_negotiation_guard(
    *,
    registration_order_independent: bool,
    dependencies_satisfied_at_execution: bool,
    custom_method_conflict_detected: bool,
    custom_method_rejected_on_checked_path: bool,
    protocol_version: str,
    negotiation_surface: str,
) -> GuardEvaluation:
    """PR-10: MCP SEP-3371 (#3371) SDK extension points & #3364 2025-11-25 vs 2026-07-28 extension negotiation."""
    if not registration_order_independent or not dependencies_satisfied_at_execution:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3371_EXTENSION_DEPENDENCY_ORDER_FAILURE",
            reason="SEP-3371 requires order-independent extension registration and execution-time dependency verification (#3371).",
            evidence={
                "registration_order_independent": registration_order_independent,
                "dependencies_satisfied_at_execution": dependencies_satisfied_at_execution,
            },
        )
    if custom_method_conflict_detected and not custom_method_rejected_on_checked_path:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3371_CUSTOM_METHOD_CONFLICT_ALLOWED",
            reason="SEP-3371 checked extension registration must reject custom method name conflicts and type changes (#3371).",
            evidence={"custom_method_conflict_detected": True},
        )
    expected_surface = "initialize_capabilities_extensions" if protocol_version == "2025-11-25" else "per_request_capabilities"
    if negotiation_surface != expected_surface:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_EXTENSION_NEGOTIATION_SURFACE_VERSION_MISMATCH",
            reason="2025-11-25 uses initialize extensions (SEP-2133) whereas 2026-07-28+ uses per-request capability negotiation (#3364).",
            evidence={"protocol_version": protocol_version, "negotiation_surface": negotiation_surface},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_SEP3371_SDK_EXTENSIONS_AND_NEGOTIATION_VERIFIED",
        reason="SEP-3371 SDK extension points and version-specific extension negotiation verified.",
        evidence={"protocol_version": protocol_version, "negotiation_surface": negotiation_surface},
    )


def evaluate_mcp_sep3279_negotiated_tool_result_variants_and_structured_content_guard(
    *,
    advertised_output_variants: set[str],
    requested_outputs: set[str],
    returned_outputs: dict[str, dict[str, Any]],
    all_structured_variants_match_schema: bool,
    forced_redundant_text_content_duplication: bool,
) -> GuardEvaluation:
    """PR-11: MCP SEP-3279 (#3279) negotiated tool result variants & #2847 structuredContent without TextContent duplication."""
    valid_audiences = {"assistant", "user", "programmatic", "extension"}
    if not requested_outputs.issubset(advertised_output_variants) or not set(returned_outputs.keys()).issubset(
        valid_audiences
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3279_UNADVERTISED_OR_INVALID_AUDIENCE_VARIANT",
            reason="SEP-3279 requestedOutputs must be a subset of Tool.outputVariants and route only to valid audiences (#3279).",
            evidence={
                "advertised": sorted(advertised_output_variants),
                "requested": sorted(requested_outputs),
                "returned": sorted(returned_outputs.keys()),
            },
        )
    if not all_structured_variants_match_schema or forced_redundant_text_content_duplication:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3279_SCHEMA_OR_TEXT_DUPLICATION_VIOLATION",
            reason="Structured output variants must validate against their schemas without forcing redundant TextContent JSON duplication (#3279, #2847).",
            evidence={
                "all_structured_variants_match_schema": all_structured_variants_match_schema,
                "forced_redundant_text_content_duplication": forced_redundant_text_content_duplication,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_SEP3279_VARIANTS_AND_STRUCTURED_CONTENT_VERIFIED",
        reason="SEP-3279 audience-routed tool result variants and non-duplicated structuredContent verified.",
        evidence={"returned_audiences": sorted(returned_outputs.keys())},
    )


def evaluate_mcp_input_schema_oneof_root_properties_typecheck_guard(
    *,
    schema: dict[str, Any],
    instance: dict[str, Any],
) -> GuardEvaluation:
    """PR-12: MCP #3185 close `oneOf` inactive-branch type-check bypass by hoisting `properties` to schema root."""
    root_props = schema.get("properties")
    one_of = schema.get("oneOf", [])
    if not isinstance(root_props, dict) or any("properties" in branch for branch in one_of if isinstance(branch, dict)):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_ONEOF_BRANCH_LOCAL_PROPERTIES_BYPASS_DETECTED",
            reason="inputSchema using oneOf must hoist properties to the schema root so inactive branches cannot bypass type checks (#3185).",
            evidence={"has_root_properties": isinstance(root_props, dict)},
        )
    for key, val in instance.items():
        prop_spec = root_props.get(key)
        if prop_spec and prop_spec.get("type") == "string" and not isinstance(val, str):
            return GuardEvaluation(
                passed=False,
                decision_code="MCP_ROOT_PROPERTY_TYPE_MISMATCH_REJECTED",
                reason="Root property type check rejected non-string value before oneOf exclusivity evaluation (#3185).",
                evidence={"field": key, "value": val},
            )
    matching_branches = 0
    for branch in one_of:
        req = branch.get("required", [])
        if req and all(k in instance for k in req):
            matching_branches += 1
    if matching_branches != 1:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_ONEOF_MUTUAL_EXCLUSIVITY_VIOLATION",
            reason="Instance must satisfy exactly one mutually exclusive oneOf required branch (#3185).",
            evidence={"matching_branches": matching_branches, "instance_keys": sorted(instance.keys())},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_ONEOF_ROOT_PROPERTIES_TYPECHECK_VERIFIED",
        reason="MCP inputSchema root-hoisted properties and oneOf mutual exclusivity verified.",
        evidence={"instance_keys": sorted(instance.keys())},
    )


def evaluate_mcp_sep3118_app_elicitations_sep3094_citations_and_sep2632_progress_guard(
    *,
    elicit_has_core_form_fallback: bool,
    elicit_ui_resource_uri: str,
    elicit_delivered_in_input_required_result: bool,
    elicit_retried_with_request_state: bool,
    citation_resource_uri: str,
    citation_selector_type: str,
    progress_content: dict[str, Any],
) -> GuardEvaluation:
    """PR-13: MCP SEP-3118 (#3118) app-rendered elicitations, SEP-3094 (#3094) citations & SEP-2632 (#2632) progress."""
    if (
        not elicit_has_core_form_fallback
        or not elicit_ui_resource_uri.startswith("ui://")
        or not elicit_delivered_in_input_required_result
        or not elicit_retried_with_request_state
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3118_APP_ELICITATION_CONTRACT_INVALID",
            reason="SEP-3118 requires a core form fallback, ui:// resourceUri in InputRequiredResult, and requestState retry (#3118).",
            evidence={"elicit_ui_resource_uri": elicit_ui_resource_uri},
        )
    valid_selectors = {"TextQuoteSelector", "TextPositionSelector", "CssSelector", "FragmentSelector", "XPathSelector"}
    if not citation_resource_uri or citation_selector_type not in valid_selectors:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP3094_GRANULAR_CITATION_SELECTOR_INVALID",
            reason="SEP-3094 citations require an MCP resource URI and a W3C Web Annotation selector (#3094).",
            evidence={"citation_resource_uri": citation_resource_uri, "citation_selector_type": citation_selector_type},
        )
    required_top = {"event", "text", "actor", "data"}
    data_obj = progress_content.get("data", {})
    if not required_top.issubset(progress_content.keys()) or not {"toolName", "input", "output"}.issubset(
        data_obj.keys() if isinstance(data_obj, dict) else set()
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_SEP2632_STRUCTURED_PROGRESS_CONTENT_INVALID",
            reason="SEP-2632 structured progress content requires event, text, actor, and data.{toolName,input,output} (#2632).",
            evidence={"progress_keys": sorted(progress_content.keys())},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_SEP3118_SEP3094_AND_SEP2632_VERIFIED",
        reason="SEP-3118 app-rendered elicitations, SEP-3094 granular citations, and SEP-2632 structured progress verified.",
        evidence={"citation_selector_type": citation_selector_type, "event": progress_content.get("event")},
    )


def evaluate_mcp_cimd_rfc_security_sections_auth_guide_and_reverse_proxy_guard(
    *,
    as_advertises_cimd_supported: bool,
    token_audience_bound: bool,
    cimd_ssrf_and_domain_trust_checked: bool,
    proxy_sse_buffering_disabled: bool,
    proxy_stateful_session_affinity_enabled: bool,
    proxy_blocks_internal_ssrf_upstreams: bool,
) -> GuardEvaluation:
    """PR-14: MCP #3235, #3191 & #2781 CIMD RFC §8.5/§8.6/§8.9 security controls & reverse-proxy deployment checklist."""
    if not as_advertises_cimd_supported or not token_audience_bound or not cimd_ssrf_and_domain_trust_checked:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CIMD_RFC_SECURITY_OR_AUDIENCE_BINDING_MISSING",
            reason="CIMD authorization requires client_id_metadata_document_supported, token audience binding, and §8.5/§8.6/§8.9 checks (#3235, #3191).",
            evidence={
                "as_advertises_cimd_supported": as_advertises_cimd_supported,
                "token_audience_bound": token_audience_bound,
            },
        )
    if (
        not proxy_sse_buffering_disabled
        or not proxy_stateful_session_affinity_enabled
        or not proxy_blocks_internal_ssrf_upstreams
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_REVERSE_PROXY_DEPLOYMENT_CHECKLIST_FAILED",
            reason="Reverse-proxied MCP servers must disable SSE buffering, enable session affinity, and block SSRF upstreams (#2781).",
            evidence={
                "proxy_sse_buffering_disabled": proxy_sse_buffering_disabled,
                "proxy_stateful_session_affinity_enabled": proxy_stateful_session_affinity_enabled,
                "proxy_blocks_internal_ssrf_upstreams": proxy_blocks_internal_ssrf_upstreams,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_CIMD_RFC_SECURITY_AND_REVERSE_PROXY_VERIFIED",
        reason="Updated CIMD RFC security controls and MCP reverse-proxy deployment checklist verified.",
        evidence={"as_advertises_cimd_supported": True, "proxy_sse_buffering_disabled": True},
    )


def _is_blocked_oauth_hop_ip(raw_host: str) -> bool:
    host = raw_host.strip("[]").lower()
    if host == "fd00:ec2::254":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if isinstance(ip, ipaddress.IPv4Address):
        return ip in ipaddress.ip_network("169.254.0.0/16")
    return ip in ipaddress.ip_network("fe80::/10") or ip == ipaddress.ip_address("fd00:ec2::254")


def evaluate_mcp_inspector_oauth_ssrf_issuer_stamp_dcr_owner_and_bind_guard(
    *,
    oauth_redirect_hop_urls: list[str],
    static_client_issuer_stamp_persisted_in_preregistered_slot: bool,
    dcr_secret_owner_client_id: str,
    current_state_client_id: str,
    foreign_dcr_secret_treated_as_absent: bool,
    web_bind_host: str,
    non_loopback_warning_emitted: bool,
) -> GuardEvaluation:
    """PR-15: MCP Inspector #2796 OAuth SSRF guard, #2794 static issuer stamp, #2792 DCR owner MAC & #2790 bind warning."""
    for url in oauth_redirect_hop_urls:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or _is_blocked_oauth_hop_ip(parsed.hostname or ""):
            return GuardEvaluation(
                passed=False,
                decision_code="INSPECTOR_OAUTH_LINK_LOCAL_OR_METADATA_SSRF_BLOCKED",
                reason="OAuth hops must use http/https and never target 169.254.0.0/16, fe80::/10, or fd00:ec2::254 (#2796).",
                evidence={"blocked_url": url},
            )
    if not static_client_issuer_stamp_persisted_in_preregistered_slot:
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_STATIC_CLIENT_ISSUER_STAMP_LOST",
            reason="Static OAuth clients must persist SEP-2352 issuer stamps in the preregistered slot across restarts (#2794).",
            evidence={"static_client_issuer_stamp_persisted_in_preregistered_slot": False},
        )
    if dcr_secret_owner_client_id != current_state_client_id and not foreign_dcr_secret_treated_as_absent:
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_FOREIGN_DCR_SECRET_LEAKED_ACROSS_CLIENTS",
            reason="DCR secrets stamped for another client_id must be read as absent (#2792).",
            evidence={"owner": dcr_secret_owner_client_id, "current": current_state_client_id},
        )
    is_loopback = web_bind_host in {"127.0.0.1", "::1", "localhost"} or web_bind_host.startswith("127.")
    if not is_loopback and not non_loopback_warning_emitted:
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_NON_LOOPBACK_BIND_WARNING_MISSING",
            reason="Binding the Inspector web UI to a non-loopback host must emit an access-control boundary warning (#2790).",
            evidence={"web_bind_host": web_bind_host},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="INSPECTOR_OAUTH_SSRF_ISSUER_DCR_AND_BIND_VERIFIED",
        reason="MCP Inspector OAuth SSRF hop guard, static client SEP-2352 stamp, DCR owner check, and bind warning verified.",
        evidence={"hops_checked": len(oauth_redirect_hop_urls), "web_bind_host": web_bind_host},
    )


def evaluate_mcp_inspector_rate_limit_envelope_post_refusal_and_oversize_relay_guard(
    *,
    error_envelope: dict[str, Any],
    post_request_http_refused: bool,
    connection_kept_alive_on_post_refusal: bool,
    oversized_error_body_dropped: bool,
    relayed_error_headers: dict[str, str],
    failed_connect_reason_kept_on_card: bool,
) -> GuardEvaluation:
    """PR-16: MCP Inspector #2795 429 envelope, #2777 HTTP-refused POST survival, #2774 framing header drop & #2801 card reason."""
    err = error_envelope.get("error", {})
    if (
        err.get("code") != "rate_limited"
        or err.get("status") != 429
        or "retryAfter" not in err
        or "retryAfterMs" not in err
        or not err.get("method")
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_429_RATE_LIMITED_ENVELOPE_INCOMPLETE",
            reason="CLI and mcpdo 429 error envelopes must preserve code=rate_limited, status=429, method, retryAfter, and retryAfterMs (#2795).",
            evidence={"error_envelope": error_envelope},
        )
    if post_request_http_refused and not connection_kept_alive_on_post_refusal:
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_HTTP_REFUSED_POST_TORE_DOWN_SESSION",
            reason="A bare HTTP-refused request POST must reject that request without tearing down the active session (#2777).",
            evidence={"connection_kept_alive_on_post_refusal": False},
        )
    lower_headers = {k.lower() for k in relayed_error_headers}
    if oversized_error_body_dropped and ({"content-length", "transfer-encoding"} & lower_headers):
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_OVERSIZED_ERROR_RELAY_RETAINED_FRAMING_HEADERS",
            reason="Dropping an oversized upstream error body must also strip content-length and transfer-encoding headers (#2774).",
            evidence={"relayed_headers": sorted(lower_headers)},
        )
    if not failed_connect_reason_kept_on_card:
        return GuardEvaluation(
            passed=False,
            decision_code="INSPECTOR_SERVER_CARD_LOST_CONNECT_FAILURE_REASON",
            reason="Web UI server cards must retain the failure reason when a connection attempt fails (#2801).",
            evidence={"failed_connect_reason_kept_on_card": False},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="INSPECTOR_429_ENVELOPE_POST_SURVIVAL_AND_RELAY_VERIFIED",
        reason="MCP Inspector 429 retry envelope, HTTP-refused POST survival, oversized relay framing cleanup, and card diagnostics verified.",
        evidence={"retry_after_ms": err.get("retryAfterMs")},
    )
