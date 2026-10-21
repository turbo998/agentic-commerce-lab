"""Stage 146 deterministic guardrails across x402, UCP, ACP, AP2, MCP, Stripe AI, Visa TAP, and Sierra tau2-bench.

Covers 16 primary-source protocol invariants (DE-01..DE-16):
- DE-01: x402 #3377 & #3376 durable-evidence encrypted delivery evidence & authorization-evidence pre-payment HMAC challenge gate
- DE-02: x402 #3366/#3365 & #3367 ERC-6492 code_deployed classification reuse in settle & SVM upto linear re-read backoff
- DE-03: x402 #3342/#3349/#3331 validatePaidResponse detached-view post-settlement validation without double-payment
- DE-04: x402 #3347/#3346 & #3336 SVM upto delegated receiverAuthorizer caller-identity binding & Stellar feeBumpSigner safety check
- DE-05: UCP #876 & #869 Accelerated IdP DNS-delegated authoritative email matching & auth-gated business response values
- DE-06: UCP #868 conditional Idempotency-Key on 5 irreversible operations & non-echo of sensitive credential fields outside /detokenize
- DE-07: UCP #861/#870 & #848 lodging deterministic cancellation schedule, stay_dates.nights exact count & guest order access credential
- DE-08: UCP #843/#839/#837 interoperable Adjustment types, three-axis Adjustment.cause (abuse vs fraud) & immutable platform_reference
- DE-09: ACP #237/#223/#201/#200 product feed embedded deep links, suggested pricing floor & complete_checkout fulfillment details
- DE-10: ACP #218/#217/#216 Razorpay delegated payment handlers (s2s_cards, upi_intent, upi_circle) mandate & cryptogram integrity
- DE-11: Google AP2 #300 x402 credential provider verified mandate amount extraction (blocking AttributeError 1250 fallback)
- DE-12: Google AP2 #278/#279 & #253 high-entropy checkout_hash anti-rainbow-table claim & RFC 8785 JCS cart_mandate_hash binding
- DE-13: MCP #2937/#2934/#2931 SEP-2243 strict lowercase =?base64? sentinel, SEP-2127 authoritative DNS bootstrap & schema $id
- DE-14: Stripe AI #434/#453/#457 MCP x402 batch payment conservation, per-tool agent identity authorization & preflight error gate
- DE-15: Visa TAP #26/#25/#23/#16 browser-session to agent-key continuity proof & cross-hop mandate digest preservation
- DE-16: Sierra tau2-bench #580/#581/#571/#569 complete gold DB state certification, NL-judge verdict count, retail gift-card/order status & union-key argument check
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date
import hashlib
import hmac
import json
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    evidence: Mapping[str, Any] = field(default_factory=dict)


def _canonical_jcs_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_jcs_sha256_hex(obj: Any) -> str:
    return hashlib.sha256(_canonical_jcs_bytes(obj)).hexdigest()


# ---------------------------------------------------------------------------
# DE-01: x402 #3377 & #3376 durable-evidence & authorization-evidence gate
# ---------------------------------------------------------------------------
def evaluate_x402_durable_and_authorization_evidence(
    *,
    buyer_opted_in_durable_evidence: bool,
    durable_evidence_ext: Mapping[str, Any] | None,
    auth_challenge_secret: str,
    advertised_challenge_nonce: str,
    advertised_payee: str,
    challenge_expires_at: int,
    now_epoch: int,
    client_auth_evidence: Mapping[str, Any] | None,
    seen_challenge_nonces: set[str],
    external_verifier_decision: str,
) -> GuardDecision:
    """Validate x402 #3376 pre-payment authorization-evidence & #3377 durable-evidence."""
    if not isinstance(client_auth_evidence, Mapping):
        return GuardDecision(
            False,
            "X402_AUTH_EVIDENCE_MISSING",
            "Protected route requires authorization-evidence extension payload before verify.",
        )

    echoed_nonce = str(client_auth_evidence.get("challenge_nonce", ""))
    echoed_payee = str(client_auth_evidence.get("payee", ""))
    echoed_hmac = str(client_auth_evidence.get("challenge_hmac", ""))
    opaque_evidence = str(client_auth_evidence.get("evidence", "")).strip()

    expected_hmac = hmac.new(
        auth_challenge_secret.encode("utf-8"),
        f"{advertised_challenge_nonce}:{advertised_payee}:{challenge_expires_at}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if (
        echoed_nonce != advertised_challenge_nonce
        or echoed_payee != advertised_payee
        or not hmac.compare_digest(echoed_hmac, expected_hmac)
        or not opaque_evidence
    ):
        return GuardDecision(
            False,
            "X402_AUTH_EVIDENCE_CHALLENGE_OR_PAYEE_MISMATCH",
            "authorization-evidence challenge HMAC, nonce, payee coverage, or opaque presentation is invalid.",
            {"echoed_nonce": echoed_nonce, "echoed_payee": echoed_payee},
        )

    if now_epoch > challenge_expires_at or echoed_nonce in seen_challenge_nonces:
        return GuardDecision(
            False,
            "X402_AUTH_EVIDENCE_STALE_OR_REPLAYED_CHALLENGE",
            "authorization-evidence challenge has expired or was already consumed.",
            {"echoed_nonce": echoed_nonce, "now_epoch": now_epoch, "expires_at": challenge_expires_at},
        )

    if external_verifier_decision != "allow":
        return GuardDecision(
            False,
            "X402_AUTH_EVIDENCE_VERIFIER_DENIED",
            "External Verifier Contract v1 denied pre-payment authorization-evidence.",
            {"external_verifier_decision": external_verifier_decision},
        )

    if buyer_opted_in_durable_evidence:
        if not isinstance(durable_evidence_ext, Mapping):
            return GuardDecision(
                False,
                "X402_DURABLE_EVIDENCE_MISSING",
                "Buyer opted into durable-evidence in accepts[], but SettlementResponse omitted durable-evidence.",
            )
        ciphertext_digest = str(durable_evidence_ext.get("ciphertext_digest", "")).strip()
        retrieval_uri = str(durable_evidence_ext.get("retrieval_uri", "")).strip()
        eip712_sig = str(durable_evidence_ext.get("facilitator_eip712_sig", "")).strip()
        party_encrypted = bool(durable_evidence_ext.get("party_encrypted", False))
        if (
            not ciphertext_digest.startswith("sha256:")
            or not retrieval_uri.startswith("https://")
            or not eip712_sig.startswith("0x")
            or len(eip712_sig) < 20
            or not party_encrypted
        ):
            return GuardDecision(
                False,
                "X402_DURABLE_EVIDENCE_MALFORMED",
                "durable-evidence must contain party-encrypted ciphertext_digest, HTTPS retrieval_uri, and facilitator EIP-712 receipt signature.",
                {"durable_evidence_ext": dict(durable_evidence_ext)},
            )

    seen_challenge_nonces.add(echoed_nonce)
    return GuardDecision(
        True,
        "X402_DURABLE_AND_AUTH_EVIDENCE_VERIFIED",
        "authorization-evidence pre-verify challenge and durable-evidence encrypted delivery receipt verified.",
        {"consumed_nonce": echoed_nonce},
    )


# ---------------------------------------------------------------------------
# DE-02: x402 #3366/#3365 ERC-6492 settle reuse & #3367 SVM upto linear backoff
# ---------------------------------------------------------------------------
def evaluate_x402_erc6492_settle_reuse_and_svm_backoff(
    *,
    verify_code_deployed: bool | None,
    settle_performed_second_eth_get_code: bool,
    settle_deployed_factory_wrap: bool,
    svm_reread_delays_ms: Sequence[int],
    base_delay_ms: int = 200,
    max_attempts: int = 5,
) -> GuardDecision:
    """Enforce x402 #3366/#3365 ERC-6492 verify code_deployed reuse in settle and #3367 SVM linear backoff."""
    if verify_code_deployed is None:
        return GuardDecision(
            False,
            "X402_ERC6492_VERIFY_CLASSIFICATION_MISSING",
            "ERC6492SignatureData must record code_deployed during verify_universal_signature.",
        )

    if settle_performed_second_eth_get_code:
        return GuardDecision(
            False,
            "X402_ERC6492_REDUNDANT_SETTLE_GETCODE_FORBIDDEN",
            "v2 exact settle must reuse code_deployed from verify instead of issuing a second eth_getCode that can disagree under RPC lag.",
        )

    expected_factory_deploy = not verify_code_deployed
    if settle_deployed_factory_wrap != expected_factory_deploy:
        return GuardDecision(
            False,
            "X402_ERC6492_SETTLE_DEPLOY_MISMATCH",
            "Settle ERC-6492 factory wrap decision disagrees with verified code_deployed state.",
            {"verify_code_deployed": verify_code_deployed, "settle_deployed_factory_wrap": settle_deployed_factory_wrap},
        )

    if not svm_reread_delays_ms or len(svm_reread_delays_ms) > max_attempts:
        return GuardDecision(
            False,
            "X402_SVM_UPTO_BACKOFF_ATTEMPTS_OUT_OF_BOUNDS",
            "SVM upto channel re-read attempts must be non-empty and bounded by max_attempts.",
            {"attempts": len(svm_reread_delays_ms), "max_attempts": max_attempts},
        )

    expected_linear = [base_delay_ms * (idx + 1) for idx in range(len(svm_reread_delays_ms))]
    if list(svm_reread_delays_ms) != expected_linear:
        return GuardDecision(
            False,
            "X402_SVM_UPTO_NON_LINEAR_BACKOFF_REJECTED",
            "SVM upto channel re-reads must follow linear backoff (base_delay_ms * attempt).",
            {"observed": list(svm_reread_delays_ms), "expected": expected_linear},
        )

    return GuardDecision(
        True,
        "X402_ERC6492_REUSE_AND_SVM_LINEAR_BACKOFF_VALID",
        "ERC-6492 settle reused verified code_deployed state and SVM upto followed linear backoff.",
        {"verify_code_deployed": verify_code_deployed, "svm_reread_delays_ms": list(svm_reread_delays_ms)},
    )


# ---------------------------------------------------------------------------
# DE-03: x402 #3342/#3349/#3331 validatePaidResponse detached view & no re-pay
# ---------------------------------------------------------------------------
def evaluate_x402_detached_paid_response_validation(
    *,
    paid_result: Mapping[str, Any],
    payment_context: Mapping[str, Any],
    validator_hook: Callable[[dict[str, Any], dict[str, Any]], bool] | None,
    payment_attempts_issued: int,
) -> GuardDecision:
    """Run validatePaidResponse on detached deep copies and prevent second payment on validation failure."""
    if payment_attempts_issued != 1:
        return GuardDecision(
            False,
            "X402_PAID_RESPONSE_MULTIPLE_PAYMENTS_BLOCKED",
            "Paid response validation must never trigger a second payment attempt when validation rejects.",
            {"payment_attempts_issued": payment_attempts_issued},
        )

    original_result_snapshot = copy.deepcopy(dict(paid_result))
    original_context_snapshot = copy.deepcopy(dict(payment_context))

    if validator_hook is not None:
        detached_result = copy.deepcopy(original_result_snapshot)
        detached_context = copy.deepcopy(original_context_snapshot)
        hook_ok = validator_hook(detached_result, detached_context)
        if dict(paid_result) != original_result_snapshot or dict(payment_context) != original_context_snapshot:
            return GuardDecision(
                False,
                "X402_PAID_RESPONSE_CALLER_MUTATION_LEAKED",
                "validatePaidResponse modified the live result or payment context instead of operating on a detached view.",
            )
        if not hook_ok:
            return GuardDecision(
                False,
                "X402_PAID_RESPONSE_VALIDATION_ERROR_PRESERVED",
                "PaidResponseValidationError raised with original result and settlement receipt preserved and zero re-payment.",
                {
                    "preserved_result": original_result_snapshot,
                    "preserved_receipt": original_context_snapshot.get("settlement_receipt"),
                    "payment_attempts_issued": payment_attempts_issued,
                },
            )

    return GuardDecision(
        True,
        "X402_PAID_RESPONSE_DETACHED_VIEW_VERIFIED",
        "Paid response validated on a detached copy with original result and settlement receipt intact.",
        {"preserved_result": original_result_snapshot},
    )


# ---------------------------------------------------------------------------
# DE-04: x402 #3347/#3346 SVM delegated receiverAuthorizer & #3336 Stellar feeBumpSigner
# ---------------------------------------------------------------------------
def evaluate_x402_svm_delegated_authorizer_and_stellar_feebump(
    *,
    svm_payload_type: str,
    delegated_receiver_authorizer: bool,
    deposit_bound_caller_id: str | None,
    claim_caller_id: str | None,
    facilitator_primary_signers: Sequence[str],
    facilitator_fee_bump_signer: str | None,
    stellar_client_roles: Mapping[str, str],
) -> GuardDecision:
    """Validate x402 #3347/#3346 SVM upto delegated receiverAuthorizer identity binding & #3336 Stellar feeBumpSigner safety."""
    if svm_payload_type not in {"deposit", "claim"}:
        return GuardDecision(
            False,
            "X402_SVM_UPTO_PAYLOAD_TYPE_INVALID",
            "SVM upto settle routing requires server-stamped payload.type in {'deposit', 'claim'}.",
            {"svm_payload_type": svm_payload_type},
        )

    if delegated_receiver_authorizer and svm_payload_type == "claim":
        if not deposit_bound_caller_id or not claim_caller_id or deposit_bound_caller_id != claim_caller_id:
            return GuardDecision(
                False,
                "X402_SVM_DELEGATED_AUTHORIZER_CALLER_MISMATCH",
                "Facilitator-delegated SVM upto receiverAuthorizer requires claim caller identity to match the deposit-bound caller identity.",
                {"deposit_bound_caller_id": deposit_bound_caller_id, "claim_caller_id": claim_caller_id},
            )

    signing_addresses = set(facilitator_primary_signers)
    if facilitator_fee_bump_signer:
        signing_addresses.add(facilitator_fee_bump_signer)

    for role_name in ("payer", "tx_source", "op_source", "auth_signer"):
        role_addr = str(stellar_client_roles.get(role_name, "")).strip()
        if role_addr and role_addr in signing_addresses:
            return GuardDecision(
                False,
                "X402_STELLAR_FACILITATOR_OR_FEEBUMP_IN_CLIENT_ROLE",
                f"Facilitator-controlled address (including feeBumpSigner) forbidden in client role '{role_name}'.",
                {"role": role_name, "address": role_addr},
            )

    return GuardDecision(
        True,
        "X402_DELEGATED_AUTHORIZER_AND_STELLAR_FEEBUMP_SAFE",
        "SVM upto delegated receiverAuthorizer caller binding and Stellar feeBumpSigner safety verified.",
        {"signing_addresses_count": len(signing_addresses)},
    )


# ---------------------------------------------------------------------------
# DE-05: UCP #876 DNS-delegated authoritative email IdP & #869 auth-gated values
# ---------------------------------------------------------------------------
def evaluate_ucp_dns_authoritative_email_linking_and_auth_gate(
    *,
    buyer_email: str,
    idp_issuer: str,
    email_verified_claim: bool,
    dns_txt_records: Mapping[str, Sequence[str]],
    is_authenticated: bool,
    response_contains_business_populated_private_values: bool,
) -> GuardDecision:
    """Validate UCP #876 draft-hardt-email-verification §3 DNS delegation & #869 auth-gated business values."""
    if not is_authenticated and response_contains_business_populated_private_values:
        return GuardDecision(
            False,
            "UCP_UNAUTHENTICATED_BUSINESS_PRIVATE_VALUES_BLOCKED",
            "Business-populated private response values must be gated on completed authentication (#869).",
        )

    if "@" not in buyer_email:
        return GuardDecision(False, "UCP_BUYER_EMAIL_INVALID", "buyer_email must contain an '@' domain.")

    email_domain = buyer_email.rsplit("@", 1)[1].strip().lower()
    dns_name = f"_email-verification.{email_domain}"
    txt_entries = [str(entry).strip() for entry in dns_txt_records.get(dns_name, ())]
    expected_record = f"iss={idp_issuer}"

    if not email_verified_claim or expected_record not in txt_entries:
        return GuardDecision(
            False,
            "UCP_ACCELERATED_IDP_NOT_DNS_AUTHORITATIVE_FOR_EMAIL",
            "Auto-linking by email on the Accelerated IdP path is forbidden unless email_verified=true and DNS _email-verification.<domain> delegates to the IdP issuer (#876).",
            {"dns_name": dns_name, "idp_issuer": idp_issuer, "txt_entries": txt_entries},
        )

    return GuardDecision(
        True,
        "UCP_DNS_AUTHORITATIVE_EMAIL_AND_AUTH_GATE_VALID",
        "IdP verified as DNS-delegated authoritative email issuer and business values properly gated on authentication.",
        {"email_domain": email_domain, "idp_issuer": idp_issuer},
    )


# ---------------------------------------------------------------------------
# DE-06: UCP #868 conditional Idempotency-Key & credential sensitivity non-echo
# ---------------------------------------------------------------------------
IRREVERSIBLE_UCP_OPERATIONS = frozenset(
    {
        "complete_checkout",
        "cancel_checkout",
        "cancel_cart",
        "complete_booking_session",
        "cancel_booking_session",
    }
)
RELAXED_UCP_WRITE_OPERATIONS = frozenset(
    {
        "create_checkout",
        "update_checkout",
        "create_cart",
        "update_cart",
        "create_booking_session",
        "update_booking_session",
    }
)
SENSITIVE_CREDENTIAL_FIELDS = frozenset({"number", "cvc", "cryptogram", "token_requestor_id"})


def evaluate_ucp_conditional_idempotency_and_credential_redaction(
    *,
    operation: str,
    idempotency_key: str | None,
    conflicting_payload_for_existing_key: bool,
    endpoint_contract: str,
    entity_response_credential_fields: Sequence[str],
) -> GuardDecision:
    """Enforce UCP #868 mandatory Idempotency-Key on 5 irreversible ops and non-echo of sensitive credential fields outside /detokenize."""
    if operation in IRREVERSIBLE_UCP_OPERATIONS and not (idempotency_key and idempotency_key.strip()):
        return GuardDecision(
            False,
            "UCP_IRREVERSIBLE_OP_IDEMPOTENCY_KEY_REQUIRED",
            f"Operation '{operation}' has an irreversible effect and requires Idempotency-Key (#868).",
            {"operation": operation},
        )

    if operation not in IRREVERSIBLE_UCP_OPERATIONS and operation not in RELAXED_UCP_WRITE_OPERATIONS:
        return GuardDecision(
            False,
            "UCP_UNKNOWN_WRITE_OPERATION",
            f"Unrecognized UCP write operation '{operation}'.",
        )

    if idempotency_key and conflicting_payload_for_existing_key:
        return GuardDecision(
            False,
            "UCP_IDEMPOTENCY_KEY_CONFLICT_409",
            "Reusing an Idempotency-Key with a different request payload must be rejected with HTTP 409.",
            {"idempotency_key": idempotency_key},
        )

    leaked_fields = sorted(set(entity_response_credential_fields) & SENSITIVE_CREDENTIAL_FIELDS)
    if endpoint_contract != "/detokenize" and leaked_fields:
        return GuardDecision(
            False,
            "UCP_SENSITIVE_CREDENTIAL_ECHO_OUTSIDE_DETOKENIZE",
            "Sensitive PAN/Network Token credential fields (number, cvc, cryptogram, token_requestor_id) MUST NOT be echoed outside /detokenize (#868).",
            {"endpoint_contract": endpoint_contract, "leaked_fields": leaked_fields},
        )

    return GuardDecision(
        True,
        "UCP_CONDITIONAL_IDEMPOTENCY_AND_CREDENTIAL_NON_ECHO_VALID",
        "UCP conditional Idempotency-Key requirement and credential field non-echo verified.",
        {"operation": operation, "idempotency_key_present": bool(idempotency_key)},
    )


# ---------------------------------------------------------------------------
# DE-07: UCP #861/#870 lodging cancellation schedule & nights + #848 guest order credential
# ---------------------------------------------------------------------------
def evaluate_ucp_lodging_schedule_nights_and_guest_order_credential(
    *,
    check_in_date: str,
    check_out_date: str,
    declared_nights: int,
    cancellation_schedule: Sequence[Mapping[str, Any]],
    evaluation_epoch: int,
    selected_penalty_minor: int,
    is_guest_buyer: bool,
    issued_order_credential: str | None,
    presented_order_credential: str | None,
) -> GuardDecision:
    """Validate UCP #861 deterministic cancellation schedule, #870 stay_dates.nights, and #848 guest order access credential."""
    d_in = date.fromisoformat(check_in_date)
    d_out = date.fromisoformat(check_out_date)
    actual_nights = (d_out - d_in).days
    if actual_nights < 1 or declared_nights != actual_nights:
        return GuardDecision(
            False,
            "UCP_LODGING_STAY_DATES_NIGHTS_MISMATCH",
            "stay_dates.nights must be >= 1 and equal the exact calendar day difference between check_in_date and check_out_date (#870).",
            {"declared_nights": declared_nights, "actual_nights": actual_nights},
        )

    matched_tier: Mapping[str, Any] | None = None
    for tier in cancellation_schedule:
        start_ts = int(tier.get("effective_from_epoch", 0))
        end_ts = int(tier.get("effective_until_epoch", 0))
        if start_ts <= evaluation_epoch < end_ts:
            matched_tier = tier
            break

    if matched_tier is None or int(matched_tier.get("penalty_minor", -1)) != selected_penalty_minor:
        return GuardDecision(
            False,
            "UCP_LODGING_CANCELLATION_SCHEDULE_MISMATCH",
            "Selected pre-purchase cancellation penalty does not match the deterministic cancellation schedule at evaluation_epoch (#861).",
            {"evaluation_epoch": evaluation_epoch, "selected_penalty_minor": selected_penalty_minor},
        )

    if is_guest_buyer:
        if (
            not issued_order_credential
            or len(issued_order_credential.strip()) < 16
            or presented_order_credential != issued_order_credential
        ):
            return GuardDecision(
                False,
                "UCP_GUEST_ORDER_ACCESS_CREDENTIAL_INVALID",
                "Guest post-purchase order access requires presenting the opaque order-bound credential issued at checkout completion (#848).",
            )

    return GuardDecision(
        True,
        "UCP_LODGING_SCHEDULE_NIGHTS_AND_GUEST_CREDENTIAL_VALID",
        "Lodging stay_dates.nights, deterministic cancellation schedule, and guest order access credential verified.",
        {"nights": actual_nights, "penalty_minor": selected_penalty_minor},
    )


# ---------------------------------------------------------------------------
# DE-08: UCP #843/#837 Adjustment standard types & 3-axis cause + #839 platform_reference
# ---------------------------------------------------------------------------
STANDARD_ADJUSTMENT_TYPES = frozenset(
    {"refund", "return", "credit", "price_adjustment", "dispute", "cancellation"}
)
VALID_CAUSE_CATEGORIES = frozenset(
    {
        "amount_divergence",
        "authority_exceeded",
        "intent_mismatch",
        "duplicate_execution",
        "misrepresentation",
        "fulfillment_mismatch",
        "terms_not_honored",
        "technical_fault",
    }
)
VALID_CAUSE_ATTRIBUTED_TO = frozenset({"business", "platform", "buyer", "psp", "carrier"})
VALID_CAUSE_NATURES = frozenset(
    {"error", "fault", "abuse", "fraud", "compromise", "disagreement", "undetermined"}
)


def evaluate_ucp_adjustment_cause_and_platform_reference(
    *,
    adjustment_type: str,
    cause: Mapping[str, Any],
    false_assertion_made: bool,
    create_platform_reference: str | None,
    update_or_complete_includes_platform_reference: bool,
    response_platform_reference: str | None,
) -> GuardDecision:
    """Validate UCP #843 standard Adjustment types, #837 three-axis cause (abuse vs fraud), and #839 platform_reference."""
    if adjustment_type not in STANDARD_ADJUSTMENT_TYPES and not adjustment_type.startswith("ext."):
        return GuardDecision(
            False,
            "UCP_ADJUSTMENT_TYPE_UNRECOGNIZED",
            "Adjustment.type must be one of the 6 standard types or a vendor-namespaced extension (#843).",
            {"adjustment_type": adjustment_type},
        )

    category = str(cause.get("category", ""))
    attributed_to = str(cause.get("attributed_to", ""))
    nature = str(cause.get("nature", ""))
    if (
        category not in VALID_CAUSE_CATEGORIES
        or attributed_to not in VALID_CAUSE_ATTRIBUTED_TO
        or nature not in VALID_CAUSE_NATURES
    ):
        return GuardDecision(
            False,
            "UCP_ADJUSTMENT_CAUSE_AXES_INVALID",
            "Adjustment.cause requires valid independent category, attributed_to, and nature axes (#837).",
            {"cause": dict(cause)},
        )

    if nature == "fraud" and not false_assertion_made:
        return GuardDecision(
            False,
            "UCP_ADJUSTMENT_FRAUD_WITHOUT_FALSE_ASSERTION",
            "Adjustment.cause.nature='fraud' requires a false assertion of identity, entitlement, or material fact; rule exploitation without false assertion must be classified as 'abuse' (#837).",
        )
    if nature == "abuse" and false_assertion_made:
        return GuardDecision(
            False,
            "UCP_ADJUSTMENT_ABUSE_WITH_FALSE_ASSERTION",
            "False assertion of identity, entitlement, or material fact must be classified as 'fraud', not 'abuse' (#837).",
        )

    if update_or_complete_includes_platform_reference:
        return GuardDecision(
            False,
            "UCP_PLATFORM_REFERENCE_FORBIDDEN_ON_UPDATE_OR_COMPLETE",
            "platform_reference must be omitted on checkout update and complete requests (#839).",
        )

    if create_platform_reference is not None and response_platform_reference != create_platform_reference:
        return GuardDecision(
            False,
            "UCP_PLATFORM_REFERENCE_CORRELATION_DRIFT",
            "Checkout and order responses must preserve the exact platform_reference supplied on checkout create (#839).",
            {"expected": create_platform_reference, "observed": response_platform_reference},
        )

    return GuardDecision(
        True,
        "UCP_ADJUSTMENT_CAUSE_AND_PLATFORM_REFERENCE_VALID",
        "Adjustment type, three-axis cause (abuse vs fraud distinction), and platform_reference correlation verified.",
        {"adjustment_type": adjustment_type, "nature": nature},
    )


# ---------------------------------------------------------------------------
# DE-09: ACP #237/#223 product feed deep links & extensions + #201/#200 pricing & complete fulfillment
# ---------------------------------------------------------------------------
def evaluate_acp_feed_deeplink_suggested_price_and_complete_fulfillment(
    *,
    deep_link_url: str,
    allowed_app_schemes: Sequence[str],
    allowed_https_hosts: Sequence[str],
    feed_extension_keys: Sequence[str],
    suggested_price_minor: int,
    merchant_floor_price_minor: int,
    complete_fulfillment_option_id: str | None,
    available_fulfillment_options: Mapping[str, int],
    items_subtotal_minor: int,
    declared_total_minor: int,
) -> GuardDecision:
    """Validate ACP #237/#223 feed deep links & extensions, #201 suggested pricing floor, and #200 fulfillment on complete."""
    parsed = urlparse(deep_link_url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    if scheme == "https":
        if host not in {h.lower() for h in allowed_https_hosts}:
            return GuardDecision(
                False,
                "ACP_FEED_DEEPLINK_UNTRUSTED_HTTPS_HOST",
                "Product feed deep link HTTPS host is not in the merchant's verified domain allowlist (#237).",
                {"deep_link_url": deep_link_url},
            )
    elif scheme not in {s.lower() for s in allowed_app_schemes}:
        return GuardDecision(
            False,
            "ACP_FEED_DEEPLINK_SCHEME_FORBIDDEN",
            "Product feed embedded app deep link uses an unverified or dangerous URI scheme (#237).",
            {"scheme": scheme, "deep_link_url": deep_link_url},
        )

    for ext_key in feed_extension_keys:
        if "." not in ext_key or ext_key.startswith(".") or ext_key.endswith("."):
            return GuardDecision(
                False,
                "ACP_FEED_EXTENSION_NAMESPACE_INVALID",
                "Feed extension keys must use reverse-domain or vendor-namespaced identifiers (#223).",
                {"invalid_key": ext_key},
            )

    if suggested_price_minor < merchant_floor_price_minor:
        return GuardDecision(
            False,
            "ACP_SUGGESTED_PRICING_BELOW_MERCHANT_FLOOR",
            "Suggested pricing on checkout create falls below the merchant's minimum floor price (#201).",
            {"suggested_price_minor": suggested_price_minor, "merchant_floor_price_minor": merchant_floor_price_minor},
        )

    if not complete_fulfillment_option_id or complete_fulfillment_option_id not in available_fulfillment_options:
        return GuardDecision(
            False,
            "ACP_COMPLETE_FULFILLMENT_OPTION_INVALID",
            "Fulfillment details provided on checkout complete must reference a valid available fulfillment option (#200).",
            {"complete_fulfillment_option_id": complete_fulfillment_option_id},
        )

    shipping_minor = int(available_fulfillment_options[complete_fulfillment_option_id])
    if items_subtotal_minor + shipping_minor != declared_total_minor:
        return GuardDecision(
            False,
            "ACP_COMPLETE_FULFILLMENT_TOTAL_MISMATCH",
            "Checkout complete total does not equal items_subtotal_minor + selected fulfillment fee (#200).",
            {"expected_total": items_subtotal_minor + shipping_minor, "declared_total": declared_total_minor},
        )

    return GuardDecision(
        True,
        "ACP_FEED_DEEPLINK_PRICING_AND_COMPLETE_FULFILLMENT_VALID",
        "ACP product feed deep link, extension namespace, suggested pricing floor, and checkout complete fulfillment verified.",
        {"declared_total_minor": declared_total_minor},
    )


# ---------------------------------------------------------------------------
# DE-10: ACP #218/#217/#216 Razorpay delegated payment handlers
# ---------------------------------------------------------------------------
def evaluate_acp_razorpay_delegated_handlers(
    *,
    handler_type: str,
    payload: Mapping[str, Any],
    checkout_amount_minor: int,
    expected_merchant_vpa: str,
    now_epoch: int,
) -> GuardDecision:
    """Validate ACP #218 (s2s_cards), #217 (upi_intent), and #216 (upi_circle) delegated payment handlers."""
    if handler_type == "razorpay_s2s_cards":
        if "raw_pan" in payload or "cvv" in payload:
            return GuardDecision(
                False,
                "ACP_RAZORPAY_S2S_RAW_PAN_FORBIDDEN",
                "razorpay_s2s_cards handler forbids raw PAN/CVV and requires network/gateway token + 3DS/AFA cryptogram (#218).",
            )
        if not payload.get("card_token_id") or not payload.get("afa_cryptogram"):
            return GuardDecision(
                False,
                "ACP_RAZORPAY_S2S_TOKEN_OR_CRYPTOGRAM_MISSING",
                "razorpay_s2s_cards requires card_token_id and 3DS/AFA cryptogram (#218).",
            )
    elif handler_type == "razorpay_upi_intent":
        intent_uri = str(payload.get("upi_intent_uri", ""))
        payee_vpa = str(payload.get("payee_vpa", ""))
        intent_amount_minor = int(payload.get("amount_minor", -1))
        if (
            not intent_uri.startswith("upi://pay?")
            or payee_vpa != expected_merchant_vpa
            or intent_amount_minor != checkout_amount_minor
            or not payload.get("intent_signature")
        ):
            return GuardDecision(
                False,
                "ACP_RAZORPAY_UPI_INTENT_BINDING_INVALID",
                "razorpay_upi_intent requires signed upi://pay URI bound to merchant VPA and exact checkout_amount_minor (#217).",
            )
    elif handler_type == "razorpay_upi_circle":
        mandate_id = str(payload.get("circle_mandate_id", ""))
        primary_approver_vpa = str(payload.get("primary_approver_vpa", ""))
        max_amount_minor = int(payload.get("max_amount_minor", -1))
        expires_at = int(payload.get("expires_at_epoch", 0))
        if (
            not mandate_id
            or not primary_approver_vpa
            or max_amount_minor < checkout_amount_minor
            or now_epoch > expires_at
        ):
            return GuardDecision(
                False,
                "ACP_RAZORPAY_UPI_CIRCLE_DELEGATION_INVALID",
                "razorpay_upi_circle requires an active primary-user delegation mandate covering checkout_amount_minor (#216).",
            )
    else:
        return GuardDecision(
            False,
            "ACP_RAZORPAY_HANDLER_UNKNOWN",
            f"Unsupported Razorpay delegated handler '{handler_type}'.",
        )

    return GuardDecision(
        True,
        "ACP_RAZORPAY_DELEGATED_HANDLER_VERIFIED",
        f"Razorpay delegated payment handler '{handler_type}' contract verified.",
        {"handler_type": handler_type, "checkout_amount_minor": checkout_amount_minor},
    )


# ---------------------------------------------------------------------------
# DE-11: Google AP2 #300 x402 credential provider verified mandate amount (no 1250 fallback)
# ---------------------------------------------------------------------------
def evaluate_ap2_x402_verified_mandate_amount_extraction(
    *,
    closed_mandate: Mapping[str, Any],
    merchant_payee_address: str | None,
    requested_transfer_amount_cents: int,
) -> GuardDecision:
    """Enforce AP2 #300: extract payment_amount.amount from verified ClosedPaymentMandate and forbid AttributeError 1250 fallback."""
    payment_instrument = closed_mandate.get("payment_instrument")
    if isinstance(payment_instrument, Mapping) and "payee_address" in payment_instrument:
        return GuardDecision(
            False,
            "AP2_PAYMENT_INSTRUMENT_UNEXPECTED_PAYEE_FIELD",
            "PaymentInstrument schema has no payee_address; relying on payment_instrument.payee_address triggers AttributeError fallback (#300).",
        )

    payment_amount = closed_mandate.get("payment_amount")
    if not isinstance(payment_amount, Mapping) or not isinstance(payment_amount.get("amount"), int):
        return GuardDecision(
            False,
            "AP2_VERIFIED_MANDATE_AMOUNT_MISSING",
            "Verified ClosedPaymentMandate must contain integer payment_amount.amount; hardcoded 1250 fallback is forbidden (#300).",
        )

    verified_amount_cents = int(payment_amount["amount"])
    if verified_amount_cents <= 0 or requested_transfer_amount_cents != verified_amount_cents:
        return GuardDecision(
            False,
            "AP2_VERIFIED_MANDATE_AMOUNT_MISMATCH_OR_1250_FALLBACK",
            "Authorized x402 transfer amount does not match verified ClosedPaymentMandate.payment_amount.amount (#300).",
            {
                "verified_amount_cents": verified_amount_cents,
                "requested_transfer_amount_cents": requested_transfer_amount_cents,
            },
        )

    if not merchant_payee_address or not merchant_payee_address.startswith("0x") or len(merchant_payee_address) != 42:
        return GuardDecision(
            False,
            "AP2_MERCHANT_PAYEE_ADDRESS_MISSING_OR_INVALID",
            "Verified merchant payee wallet address is required and must not fall back to a demo default (#300).",
        )

    return GuardDecision(
        True,
        "AP2_VERIFIED_MANDATE_AMOUNT_AUTHORIZED",
        "x402 credential provider authorized the exact verified mandate amount without fallback.",
        {"verified_amount_cents": verified_amount_cents, "payee_address": merchant_payee_address},
    )


# ---------------------------------------------------------------------------
# DE-12: Google AP2 #278/#279 high-entropy checkout_hash & #253 RFC 8785 JCS cart binding
# ---------------------------------------------------------------------------
def evaluate_ap2_checkout_hash_entropy_and_jcs_cart_binding(
    *,
    checkout_jwt_payload: Mapping[str, Any],
    cart_mandate_id: str,
    cart_mandate_contents: Mapping[str, Any],
    payment_mandate_contents: Mapping[str, Any],
) -> GuardDecision:
    """Enforce AP2 #278/#279 entropy-based checkout_hash claim and #253 RFC 8785 JCS cart_mandate_hash binding."""
    entropy_nonce = str(checkout_jwt_payload.get("jti") or checkout_jwt_payload.get("nonce") or "").strip()
    # Require at least 16 bytes (32 hex chars / 22 base64url chars) of unpredictable per-session entropy
    if len(entropy_nonce) < 22 or len(set(entropy_nonce)) < 8:
        return GuardDecision(
            False,
            "AP2_CHECKOUT_HASH_LOW_ENTROPY_RAINBOW_TABLE_RISK",
            "Checkout JWT payload must include a high-entropy per-session claim (jti/nonce >= 128 bits) so checkout_hash is unpredictable regardless of signature algorithm (#278).",
            {"entropy_nonce_length": len(entropy_nonce)},
        )

    expected_cart_hash = canonical_jcs_sha256_hex(cart_mandate_contents)
    bound_cart_id = str(payment_mandate_contents.get("cart_mandate_id", ""))
    bound_cart_hash = str(payment_mandate_contents.get("cart_mandate_hash", ""))

    if bound_cart_id != cart_mandate_id or not hmac.compare_digest(bound_cart_hash, expected_cart_hash):
        return GuardDecision(
            False,
            "AP2_JCS_CART_TO_PAYMENT_MANDATE_BINDING_MISMATCH",
            "PaymentMandateContents must include cart_mandate_id and cart_mandate_hash = hex(sha256(jcs(cart_mandate_contents))) per RFC 8785 (#253).",
            {
                "expected_cart_id": cart_mandate_id,
                "bound_cart_id": bound_cart_id,
                "expected_cart_hash": expected_cart_hash,
                "bound_cart_hash": bound_cart_hash,
            },
        )

    return GuardDecision(
        True,
        "AP2_CHECKOUT_ENTROPY_AND_JCS_CART_BINDING_VALID",
        "High-entropy checkout_hash claim and RFC 8785 JCS CartMandate-to-PaymentMandate binding verified.",
        {"cart_mandate_hash": expected_cart_hash},
    )


# ---------------------------------------------------------------------------
# DE-13: MCP #2937 lowercase =?base64? sentinel, #2934 DNS bootstrap & #2931 schema $id
# ---------------------------------------------------------------------------
def evaluate_mcp_base64_sentinel_dns_bootstrap_and_schema_id(
    *,
    mcp_param_header_value: str,
    dns_bootstrap_txt: str,
    authorized_domain: str,
    generated_schema: Mapping[str, Any],
) -> GuardDecision:
    """Validate MCP #2937 strict lowercase =?base64?...?= sentinel, #2934 DNS bootstrap pointer, and #2931 schema $id."""
    if mcp_param_header_value.lower().startswith("=?base64?"):
        if not (mcp_param_header_value.startswith("=?base64?") and mcp_param_header_value.endswith("?=")):
            return GuardDecision(
                False,
                "MCP_SEP2243_BASE64_SENTINEL_CASE_VIOLATION",
                "SEP-2243 base64 sentinel markers are case-sensitive and must be lowercase '=?base64?...?=' (#2937).",
                {"mcp_param_header_value": mcp_param_header_value},
            )

    if not dns_bootstrap_txt.startswith("mcp-server-card="):
        return GuardDecision(
            False,
            "MCP_DNS_BOOTSTRAP_RECORD_MALFORMED",
            "SEP-2127 DNS bootstrap TXT record must point to an HTTPS MCP Server Card URL via 'mcp-server-card=<https_url>' (#2934).",
            {"dns_bootstrap_txt": dns_bootstrap_txt},
        )

    card_url = dns_bootstrap_txt.split("=", 1)[1].strip()
    parsed = urlparse(card_url)
    host = (parsed.hostname or "").lower()
    auth_dom = authorized_domain.lower()
    if parsed.scheme != "https" or not (host == auth_dom or host.endswith("." + auth_dom)):
        return GuardDecision(
            False,
            "MCP_DNS_BOOTSTRAP_UNTRUSTED_TARGET_URL",
            "SEP-2127 DNS bootstrap must resolve to an HTTPS URL under the authorized domain (#2934).",
            {"card_url": card_url, "authorized_domain": authorized_domain},
        )

    schema_id = str(generated_schema.get("$id", "")).strip()
    if not schema_id.startswith("https://modelcontextprotocol.io/schemas/"):
        return GuardDecision(
            False,
            "MCP_GENERATED_SCHEMA_SELF_DESCRIBING_ID_MISSING",
            "Generated MCP schema.json must carry a self-describing '$id' URI (#2931).",
            {"schema_id": schema_id},
        )

    return GuardDecision(
        True,
        "MCP_BASE64_SENTINEL_DNS_BOOTSTRAP_AND_SCHEMA_ID_VALID",
        "MCP lowercase =?base64? sentinel, HTTPS DNS bootstrap pointer, and self-describing schema $id verified.",
        {"card_url": card_url, "schema_id": schema_id},
    )


# ---------------------------------------------------------------------------
# DE-14: Stripe AI #434/#453/#457 x402 batch payment, per-tool auth & preflight gate
# ---------------------------------------------------------------------------
def evaluate_stripe_mcp_x402_batch_and_per_tool_auth(
    *,
    agent_id: str,
    invoked_tool: str,
    agent_tool_permissions: Mapping[str, Sequence[str]],
    batch_items: Sequence[Mapping[str, Any]],
    signed_batch_total_minor: int,
    preflight_errors: Sequence[str],
) -> GuardDecision:
    """Validate Stripe AI #434 MCP x402 batch payment, #453 per-tool agent authorization, and #457 preflight error gate."""
    if preflight_errors:
        return GuardDecision(
            False,
            "STRIPE_PROJECTS_PREFLIGHT_ERROR_GATE_TRIPPED",
            "stripe-projects preflight reported blocking error codes (#457).",
            {"preflight_errors": list(preflight_errors)},
        )

    allowed_tools = set(agent_tool_permissions.get(agent_id, ()))
    if not agent_id or invoked_tool not in allowed_tools:
        return GuardDecision(
            False,
            "STRIPE_AGENT_PER_TOOL_AUTHORIZATION_DENIED",
            f"Agent '{agent_id}' is not authorized to invoke tool '{invoked_tool}' (#453).",
            {"agent_id": agent_id, "invoked_tool": invoked_tool},
        )

    if not batch_items:
        return GuardDecision(False, "STRIPE_X402_BATCH_EMPTY", "MCP x402 batch payment must contain at least one item (#434).")

    seen_nonces: set[str] = set()
    sum_minor = 0
    for item in batch_items:
        nonce = str(item.get("nonce", "")).strip()
        amt = int(item.get("amount_minor", 0))
        if not nonce or nonce in seen_nonces or amt <= 0:
            return GuardDecision(
                False,
                "STRIPE_X402_BATCH_NONCE_OR_AMOUNT_INVALID",
                "Each x402 batch payment item requires a unique nonce and positive amount_minor (#434).",
            )
        seen_nonces.add(nonce)
        sum_minor += amt

    if sum_minor != signed_batch_total_minor:
        return GuardDecision(
            False,
            "STRIPE_X402_BATCH_TOTAL_MISMATCH",
            "Sum of MCP x402 batch items does not equal signed_batch_total_minor (#434).",
            {"sum_minor": sum_minor, "signed_batch_total_minor": signed_batch_total_minor},
        )

    return GuardDecision(
        True,
        "STRIPE_X402_BATCH_AND_PER_TOOL_AUTH_VERIFIED",
        "Stripe AI preflight, per-tool agent identity authorization, and x402 batch payment conservation verified.",
        {"agent_id": agent_id, "batch_total_minor": sum_minor},
    )


# ---------------------------------------------------------------------------
# DE-15: Visa TAP #26/#25/#23/#16 browser-session to agent-key continuity proof
# ---------------------------------------------------------------------------
def evaluate_visa_tap_session_continuity_and_hop_digest(
    *,
    browser_session_id: str,
    agent_key_id: str,
    active_directory_keys: set[str],
    initial_mandate_digest: str,
    terminal_hop_mandate_digest: str,
    continuity_token_hmac: str,
    shared_continuity_secret: str,
) -> GuardDecision:
    """Validate Visa TAP #26/#25/#23/#16 browser-to-agent continuity token and cross-hop mandate digest preservation."""
    if agent_key_id not in active_directory_keys:
        return GuardDecision(
            False,
            "TAP_AGENT_KEY_NOT_ACTIVE_IN_DIRECTORY",
            "Visa TAP agent keyID is missing or revoked in the Agent Directory.",
            {"agent_key_id": agent_key_id},
        )

    if not initial_mandate_digest.startswith("sha-256=:") or initial_mandate_digest != terminal_hop_mandate_digest:
        return GuardDecision(
            False,
            "TAP_CROSS_HOP_MANDATE_DIGEST_MUTATED",
            "Mandate digest drifted across CDN/proxy hops between browser handoff and merchant terminal verification.",
            {"initial": initial_mandate_digest, "terminal": terminal_hop_mandate_digest},
        )

    expected_hmac = hmac.new(
        shared_continuity_secret.encode("utf-8"),
        f"{browser_session_id}:{agent_key_id}:{initial_mandate_digest}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(continuity_token_hmac, expected_hmac):
        return GuardDecision(
            False,
            "TAP_BROWSER_TO_AGENT_CONTINUITY_PROOF_INVALID",
            "Browser-session to TAP agent-key continuity HMAC proof failed verification.",
        )

    return GuardDecision(
        True,
        "TAP_SESSION_CONTINUITY_AND_HOP_DIGEST_VERIFIED",
        "Visa TAP browser-to-agent session continuity proof and cross-hop mandate digest verified.",
        {"agent_key_id": agent_key_id},
    )


# ---------------------------------------------------------------------------
# DE-16: Sierra tau2-bench #580/#581/#571/#569 evaluator & retail task guards
# ---------------------------------------------------------------------------
def evaluate_tau2_gold_db_judge_verdicts_retail_and_union_args(
    *,
    gold_write_actions_total: int,
    gold_write_actions_executed: int,
    nl_assertions_count: int,
    nl_judge_verdicts_count: int,
    retail_order_status: str,
    exchange_price_diff_cents: int,
    gift_card_balance_cents: int,
    agent_tool_args: Mapping[str, Any],
    gold_tool_args: Mapping[str, Any],
    compare_args: Sequence[str] | None = None,
) -> GuardDecision:
    """Enforce Sierra tau2-bench #580 complete gold DB state, #581 NL-judge verdict count, #571 retail gift card/delivered order, and #569 union-key argument check."""
    if gold_write_actions_executed < gold_write_actions_total:
        return GuardDecision(
            False,
            "TAU2_INCOMPLETE_GOLD_DB_STATE_UNCERTIFIED",
            "Evaluator must not certify an incomplete gold DB state when gold write actions failed or were skipped (#580).",
            {"executed": gold_write_actions_executed, "total": gold_write_actions_total},
        )

    if nl_judge_verdicts_count != nl_assertions_count:
        return GuardDecision(
            False,
            "TAU2_NL_JUDGE_VERDICT_COUNT_MISMATCH",
            "NL-assertion judge reply with the wrong number of verdicts must be rejected (#581).",
            {"expected": nl_assertions_count, "observed": nl_judge_verdicts_count},
        )

    if retail_order_status != "delivered" or gift_card_balance_cents < exchange_price_diff_cents:
        return GuardDecision(
            False,
            "TAU2_RETAIL_EXCHANGE_PENDING_ORDER_OR_INSUFFICIENT_GIFTCARD",
            "Retail exchange requires order status 'delivered' (not 'pending') and gift card balance >= price difference (#571).",
            {
                "retail_order_status": retail_order_status,
                "gift_card_balance_cents": gift_card_balance_cents,
                "exchange_price_diff_cents": exchange_price_diff_cents,
            },
        )

    keys_to_check = set(compare_args) if compare_args is not None else (set(agent_tool_args.keys()) | set(gold_tool_args.keys()))
    for k in keys_to_check:
        if k not in agent_tool_args or k not in gold_tool_args or agent_tool_args[k] != gold_tool_args[k]:
            return GuardDecision(
                False,
                "TAU2_ACTION_CHECK_OMITTED_OR_MISMATCHED_GOLD_ARG",
                f"Tool call argument check failed on union key '{k}' (omitted or mismatched gold argument, #569).",
                {"key": k, "agent_keys": sorted(agent_tool_args.keys()), "gold_keys": sorted(gold_tool_args.keys())},
            )

    return GuardDecision(
        True,
        "TAU2_GOLD_DB_JUDGE_RETAIL_AND_UNION_ARGS_VERIFIED",
        "Sierra tau2-bench complete gold DB certification, NL-judge verdict count, retail exchange preconditions, and union-key argument check verified.",
        {"checked_keys": sorted(keys_to_check)},
    )
