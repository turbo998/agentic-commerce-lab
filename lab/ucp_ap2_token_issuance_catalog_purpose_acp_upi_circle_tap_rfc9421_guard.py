from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True)
class UCPAP2TokenIssuanceAndContentDigestGuardResult:
    admitted: bool
    decision_code: str
    credential_type_valid: bool
    mandate_correlated_with_checkout_jwt: bool
    issued_token_opaque_and_high_entropy: bool
    composite_reversible_token_rejected: bool
    raw_bytes_content_digest_verified: bool
    jcs_mutated_digest_rejected: bool
    violation_Stage: str | None
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UCPCatalogSearchPurposeAndReferenceIdsGuardResult:
    admitted: bool
    decision_code: str
    purpose: str
    purpose_reference_pairing_valid: bool
    self_exclusion_enforced: bool
    distinct_variant_swap_allowed: bool
    returned_item_ids: list[str]
    violation_stage: str | None
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ACPFeedExtensionsAndRazorpayUPICircleGuardResult:
    admitted: bool
    decision_code: str
    feed_extensions_whitelist_valid: bool
    undeclared_feed_extension_fields: list[str]
    upi_circle_delegate_id_opaque: bool
    upi_circle_cryptogram_fresh: bool
    upi_circle_npci_limit_respected: bool
    upi_circle_risk_signals_empty: bool
    violation_stage: str | None
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AP2OpenMandateHashEntropyAndTAPSIMGuardResult:
    admitted: bool
    decision_code: str
    open_mandate_hash_hex: str
    jcs_claims_only_hash_valid: bool
    unicode_codepoint_exactness_preserved: bool
    ed25519_checkout_entropy_valid: bool
    tap_rfc9421_signature_params_final_line: bool
    tap_individually_quoted_components_valid: bool
    violation_stage: str | None
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compute_rfc9530_content_digest(raw_body: bytes) -> str:
    digest_b64 = base64.b64encode(hashlib.sha256(raw_body).digest()).decode("ascii")
    return f"sha-256=:{digest_b64}:"


def evaluate_ucp_ap2_token_issuance_and_content_digest_guard(
    *,
    ap2_negotiated: bool,
    tokenize_request: dict[str, Any],
    checkout_jwt_transaction_id: str,
    mandate_transaction_id: str,
    mandate_signature_valid: bool,
    mandate_expired: bool,
    issued_payment_token: str,
    token_entropy_bits: int,
    token_embeds_reversible_mandate: bool,
    complete_checkout_has_mandate_derived_token: bool,
    raw_http_response_bytes: bytes,
    content_digest_header: str,
    verifier_canonicalized_body_with_jcs: bool = False,
) -> UCPAP2TokenIssuanceAndContentDigestGuardResult:
    """Enforce UCP PR #916 (AP2 Payment Mandate verification & token issuance) and PR #917 (RFC 9530 raw-byte Content-Digest)."""
    if ap2_negotiated and not complete_checkout_has_mandate_derived_token:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_AP2_PAYMENT_MANDATE_REQUIRED",
            credential_type_valid=False,
            mandate_correlated_with_checkout_jwt=False,
            issued_token_opaque_and_high_entropy=False,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="complete_checkout_payment_instrument",
            remediation="Return UCP error_code='payment_mandate_required' when AP2 is negotiated but the selected instrument carries no mandate-derived token (UCP PR #916).",
        )

    if "payment_mandate" in tokenize_request:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_AP2_TOP_LEVEL_MANDATE_MEMBER_FORBIDDEN",
            credential_type_valid=False,
            mandate_correlated_with_checkout_jwt=False,
            issued_token_opaque_and_high_entropy=False,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="tokenize_request_shape",
            remediation="Present the AP2 Payment Mandate inside credential={'type': 'ap2_payment_mandate', 'payment_mandate': '...', 'checkout_jwt': '...'} rather than adding a top-level payment_mandate member on /tokenize (UCP PR #916).",
        )

    credential = tokenize_request.get("credential")
    binding = tokenize_request.get("binding")
    if (
        not isinstance(credential, dict)
        or credential.get("type") != "ap2_payment_mandate"
        or not isinstance(credential.get("payment_mandate"), str)
        or not credential.get("payment_mandate", "").strip()
        or not isinstance(credential.get("checkout_jwt"), str)
        or not credential.get("checkout_jwt", "").strip()
        or not isinstance(binding, dict)
        or binding.get("type") != "dev.ucp.shopping.checkout"
        or not str(binding.get("id", "")).strip()
    ):
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_AP2_INVALID_SOURCE_CREDENTIAL_ENVELOPE",
            credential_type_valid=False,
            mandate_correlated_with_checkout_jwt=False,
            issued_token_opaque_and_high_entropy=False,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="tokenize_source_credential",
            remediation="Require credential.type=='ap2_payment_mandate' with non-empty payment_mandate (SD-JWT+kb), checkout_jwt (Compact JWS), and checkout binding (UCP PR #916).",
        )

    if not mandate_signature_valid or mandate_expired or checkout_jwt_transaction_id != mandate_transaction_id:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_AP2_CP_MANDATE_VERIFICATION_FAILED",
            credential_type_valid=True,
            mandate_correlated_with_checkout_jwt=False,
            issued_token_opaque_and_high_entropy=False,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="credential_provider_verification",
            remediation="Credential Provider MUST verify Payment Mandate signature, key binding, expiration, and transaction_id correlation against checkout_jwt before issuing a payment token (UCP PR #916).",
        )

    if token_embeds_reversible_mandate or token_entropy_bits < 128 or "." in issued_payment_token or "~" in issued_payment_token:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_AP2_COMPOSITE_REVERSIBLE_TOKEN_REJECTED",
            credential_type_valid=True,
            mandate_correlated_with_checkout_jwt=True,
            issued_token_opaque_and_high_entropy=False,
            composite_reversible_token_rejected=False,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="token_issuance_opacity",
            remediation="Do not embed a reversible signed mandate JWT/SD-JWT as a 'composite token' in credential.token; issue an opaque, non-reversible token with >= 128 bits of entropy (UCP PR #916).",
        )

    if verifier_canonicalized_body_with_jcs:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_SHOPPING_CONTENT_DIGEST_JCS_MUTATION_FORBIDDEN",
            credential_type_valid=True,
            mandate_correlated_with_checkout_jwt=True,
            issued_token_opaque_and_high_entropy=True,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=False,
            violation_Stage="content_digest_verification",
            remediation="Compute and verify Content-Digest per RFC 9530 over the exact raw HTTP body bytes without RFC 8785 JCS re-canonicalization (UCP PR #917).",
        )

    expected_digest = _compute_rfc9530_content_digest(raw_http_response_bytes)
    if content_digest_header != expected_digest:
        return UCPAP2TokenIssuanceAndContentDigestGuardResult(
            admitted=False,
            decision_code="UCP_SHOPPING_CONTENT_DIGEST_MISMATCH",
            credential_type_valid=True,
            mandate_correlated_with_checkout_jwt=True,
            issued_token_opaque_and_high_entropy=True,
            composite_reversible_token_rejected=True,
            raw_bytes_content_digest_verified=False,
            jcs_mutated_digest_rejected=True,
            violation_Stage="content_digest_verification",
            remediation="Ensure Content-Digest header matches sha-256=:<base64>: over raw HTTP body bytes per RFC 9530 (UCP PR #917).",
        )

    return UCPAP2TokenIssuanceAndContentDigestGuardResult(
        admitted=True,
        decision_code="UCP_AP2_TOKEN_ISSUANCE_AND_RAW_CONTENT_DIGEST_VERIFIED",
        credential_type_valid=True,
        mandate_correlated_with_checkout_jwt=True,
        issued_token_opaque_and_high_entropy=True,
        composite_reversible_token_rejected=True,
        raw_bytes_content_digest_verified=True,
        jcs_mutated_digest_rejected=True,
        violation_Stage=None,
        remediation="none",
    )


def evaluate_ucp_catalog_search_purpose_and_reference_ids_guard(
    *,
    purpose: str | None,
    reference_ids: list[str] | None,
    query: str | None,
    filters: dict[str, Any] | None,
    anchor_variant_to_parent: dict[str, str],
    candidate_results: list[dict[str, str]],
) -> UCPCatalogSearchPurposeAndReferenceIdsGuardResult:
    """Enforce UCP PR #902 (`dev.ucp.shopping.catalog.search` `purpose` and `reference_ids` pairing and self-exclusion rules)."""
    effective_purpose = purpose if purpose is not None else "search"
    supported_purposes = {"search", "recommendation", "swap"}
    if effective_purpose not in supported_purposes:
        return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
            admitted=False,
            decision_code="UCP_CATALOG_SEARCH_UNSUPPORTED_PURPOSE",
            purpose=effective_purpose,
            purpose_reference_pairing_valid=False,
            self_exclusion_enforced=False,
            distinct_variant_swap_allowed=False,
            returned_item_ids=[],
            violation_stage="purpose_validation",
            remediation="Reject unsupported purpose values with HTTP 400 unsupported_purpose / JSON-RPC -32602 rather than falling back to generic browse (UCP PR #902).",
        )

    has_refs = reference_ids is not None
    if has_refs:
        if (
            not isinstance(reference_ids, list)
            or len(reference_ids) == 0
            or any(not isinstance(r, str) or not r.strip() for r in reference_ids)
            or len(set(reference_ids)) != len(reference_ids)
        ):
            return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                admitted=False,
                decision_code="UCP_CATALOG_SEARCH_INVALID_REFERENCE_IDS",
                purpose=effective_purpose,
                purpose_reference_pairing_valid=False,
                self_exclusion_enforced=False,
                distinct_variant_swap_allowed=False,
                returned_item_ids=[],
                violation_stage="reference_ids_schema",
                remediation="Ensure reference_ids is a non-empty array of unique, non-empty strings (UCP PR #902).",
            )

    if effective_purpose == "search":
        if has_refs:
            return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                admitted=False,
                decision_code="UCP_CATALOG_SEARCH_REFERENCE_IDS_FORBIDDEN_ON_SEARCH",
                purpose=effective_purpose,
                purpose_reference_pairing_valid=False,
                self_exclusion_enforced=False,
                distinct_variant_swap_allowed=False,
                returned_item_ids=[],
                violation_stage="purpose_reference_pairing",
                remediation="Omit reference_ids when purpose is 'search' (or omitted); reference_ids requires purpose='recommendation' or 'swap' (UCP PR #902).",
            )
        if not (query and query.strip()) and not filters:
            return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                admitted=False,
                decision_code="UCP_CATALOG_SEARCH_EMPTY_SEARCH_INPUT",
                purpose=effective_purpose,
                purpose_reference_pairing_valid=False,
                self_exclusion_enforced=False,
                distinct_variant_swap_allowed=False,
                returned_item_ids=[],
                violation_stage="search_input_validation",
                remediation="Provide at least one of query or filters when purpose=='search' (UCP PR #902).",
            )

    if effective_purpose == "swap" and not has_refs:
        return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
            admitted=False,
            decision_code="UCP_CATALOG_SEARCH_SWAP_REQUIRES_REFERENCE_IDS",
            purpose=effective_purpose,
            purpose_reference_pairing_valid=False,
            self_exclusion_enforced=False,
            distinct_variant_swap_allowed=False,
            returned_item_ids=[],
            violation_stage="purpose_reference_pairing",
            remediation="Require non-empty reference_ids when purpose=='swap' (UCP PR #902).",
        )

    ref_set = set(reference_ids or [])
    parent_set = {anchor_variant_to_parent[r] for r in ref_set if r in anchor_variant_to_parent}
    returned_ids: list[str] = []
    distinct_variant_swap = False

    for item in candidate_results:
        item_id = str(item.get("id", ""))
        parent_id = str(item.get("parent_product_id", ""))
        is_variant = bool(item.get("is_variant", False))

        if item_id in ref_set:
            return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                admitted=False,
                decision_code="UCP_CATALOG_SEARCH_SELF_EXCLUSION_VIOLATION",
                purpose=effective_purpose,
                purpose_reference_pairing_valid=True,
                self_exclusion_enforced=False,
                distinct_variant_swap_allowed=False,
                returned_item_ids=[],
                violation_stage="self_exclusion_guard",
                remediation="Exclude all referenced product/variant IDs from recommendation and swap results (UCP PR #902).",
            )

        if effective_purpose == "recommendation" and (item_id in parent_set or parent_id in parent_set or parent_id in ref_set):
            return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                admitted=False,
                decision_code="UCP_CATALOG_RECOMMENDATION_PARENT_EXCLUSION_VIOLATION",
                purpose=effective_purpose,
                purpose_reference_pairing_valid=True,
                self_exclusion_enforced=False,
                distinct_variant_swap_allowed=False,
                returned_item_ids=[],
                violation_stage="recommendation_parent_exclusion",
                remediation="Exclude the parent product (and sibling variants) of any referenced variant when purpose=='recommendation' (UCP PR #902).",
            )

        if effective_purpose == "swap":
            if item_id in parent_set and not is_variant:
                return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
                    admitted=False,
                    decision_code="UCP_CATALOG_SWAP_BARE_PARENT_EXCLUSION_VIOLATION",
                    purpose=effective_purpose,
                    purpose_reference_pairing_valid=True,
                    self_exclusion_enforced=False,
                    distinct_variant_swap_allowed=False,
                    returned_item_ids=[],
                    violation_stage="swap_parent_exclusion",
                    remediation="Exclude bare parent product of a referenced variant in swap results unless returning a distinct substitute variant of that parent (UCP PR #902).",
                )
            if is_variant and parent_id in parent_set and item_id not in ref_set:
                distinct_variant_swap = True

        returned_ids.append(item_id)

    return UCPCatalogSearchPurposeAndReferenceIdsGuardResult(
        admitted=True,
        decision_code="UCP_CATALOG_SEARCH_PURPOSE_AND_EXCLUSION_VERIFIED",
        purpose=effective_purpose,
        purpose_reference_pairing_valid=True,
        self_exclusion_enforced=True,
        distinct_variant_swap_allowed=distinct_variant_swap,
        returned_item_ids=returned_ids,
        violation_stage=None,
        remediation="none",
    )


def evaluate_acp_feed_extensions_and_razorpay_upi_circle_guard(
    *,
    feed_metadata_extensions: list[dict[str, Any]],
    feed_object_extension_paths: list[str],
    delegate_payment_request: dict[str, Any],
    now_epoch_seconds: int,
    cryptogram_expires_epoch_seconds: int,
) -> ACPFeedExtensionsAndRazorpayUPICircleGuardResult:
    """Enforce ACP PR #223 (FeedMetadata.extensions JSONPath whitelist) and PR #216 (Razorpay UPI Circle handler `com.razorpay.upi_circle`)."""
    declared_paths: set[str] = set()
    for ext in feed_metadata_extensions:
        schema_url = str(ext.get("schema", ""))
        spec_url = str(ext.get("spec", ""))
        if not schema_url.startswith("https://") or not spec_url.startswith("https://"):
            return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
                admitted=False,
                decision_code="ACP_FEED_EXTENSION_INSECURE_SCHEMA_URI",
                feed_extensions_whitelist_valid=False,
                undeclared_feed_extension_fields=[],
                upi_circle_delegate_id_opaque=False,
                upi_circle_cryptogram_fresh=False,
                upi_circle_npci_limit_respected=False,
                upi_circle_risk_signals_empty=False,
                violation_stage="feed_metadata_extension_declaration",
                remediation="Require HTTPS URLs for FeedMetadata.extensions[*].schema and spec (ACP PR #223).",
            )
        for path in ext.get("extends", []):
            if isinstance(path, str) and path.startswith("$."):
                declared_paths.add(path)

    undeclared = [p for p in feed_object_extension_paths if p not in declared_paths]
    if undeclared:
        return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
            admitted=False,
            decision_code="ACP_FEED_UNDECLARED_EXTENSION_FIELD_REJECTED",
            feed_extensions_whitelist_valid=False,
            undeclared_feed_extension_fields=undeclared,
            upi_circle_delegate_id_opaque=False,
            upi_circle_cryptogram_fresh=False,
            upi_circle_npci_limit_respected=False,
            upi_circle_risk_signals_empty=False,
            violation_stage="feed_schema_composition",
            remediation="Feed producers MUST NOT include undeclared extension fields outside FeedMetadata.extensions[*].extends JSONPath whitelist (ACP PR #223).",
        )

    pm = delegate_payment_request.get("payment_method", {})
    cred = delegate_payment_request.get("credential", {})
    allowance = delegate_payment_request.get("allowance", {})
    risk_signals = delegate_payment_request.get("risk_signals")

    delegate_id = str(pm.get("delegate_id", ""))
    if (
        pm.get("type") != "upi_circle"
        or "mandate_id" in pm
        or not delegate_id.startswith("ucirc_")
    ):
        return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
            admitted=False,
            decision_code="ACP_UPI_CIRCLE_RAW_MANDATE_ID_OR_INVALID_DELEGATE_ID",
            feed_extensions_whitelist_valid=True,
            undeclared_feed_extension_fields=[],
            upi_circle_delegate_id_opaque=False,
            upi_circle_cryptogram_fresh=False,
            upi_circle_npci_limit_respected=False,
            upi_circle_risk_signals_empty=False,
            violation_stage="upi_circle_payment_method",
            remediation="Use payment_method.type=='upi_circle' with an opaque delegate_id (ucirc_...) and never expose raw PSP mandate_id (ACP PR #216).",
        )

    if (
        cred.get("type") != "upi_circle_cryptogram"
        or not str(cred.get("value", "")).strip()
        or cryptogram_expires_epoch_seconds <= now_epoch_seconds
    ):
        return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
            admitted=False,
            decision_code="ACP_UPI_CIRCLE_EXPIRED_OR_MISSING_CRYPTOGRAM",
            feed_extensions_whitelist_valid=True,
            undeclared_feed_extension_fields=[],
            upi_circle_delegate_id_opaque=True,
            upi_circle_cryptogram_fresh=False,
            upi_circle_npci_limit_respected=False,
            upi_circle_risk_signals_empty=False,
            violation_stage="upi_circle_credential",
            remediation="Require a fresh one-time credential.type=='upi_circle_cryptogram' with expires_at strictly in the future before submitting DelegatePaymentRequest (ACP PR #216).",
        )

    currency = str(allowance.get("currency", "")).lower()
    max_amount = int(allowance.get("max_amount", 0))
    # NPCI UPI Circle hard limit: INR 15,000 == 1,500,000 paise (minor units)
    if currency != "inr" or max_amount <= 0 or max_amount > 1500000:
        return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
            admitted=False,
            decision_code="ACP_UPI_CIRCLE_CURRENCY_OR_NPCI_LIMIT_EXCEEDED",
            feed_extensions_whitelist_valid=True,
            undeclared_feed_extension_fields=[],
            upi_circle_delegate_id_opaque=True,
            upi_circle_cryptogram_fresh=True,
            upi_circle_npci_limit_respected=False,
            upi_circle_risk_signals_empty=False,
            violation_stage="upi_circle_allowance_limit",
            remediation="Restrict com.razorpay.upi_circle to currency=='inr' and enforce NPCI per-transaction ceiling max_amount <= 1500000 paise (INR 15,000) (ACP PR #216).",
        )

    if not isinstance(risk_signals, list) or len(risk_signals) != 0:
        return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
            admitted=False,
            decision_code="ACP_UPI_CIRCLE_NON_EMPTY_CARD_RISK_SIGNALS",
            feed_extensions_whitelist_valid=True,
            undeclared_feed_extension_fields=[],
            upi_circle_delegate_id_opaque=True,
            upi_circle_cryptogram_fresh=True,
            upi_circle_npci_limit_respected=True,
            upi_circle_risk_signals_empty=False,
            violation_stage="upi_circle_risk_signals",
            remediation="Submit risk_signals=[] (empty array) for UPI Circle delegated payments rather than inapplicable card-testing signals (ACP PR #216).",
        )

    return ACPFeedExtensionsAndRazorpayUPICircleGuardResult(
        admitted=True,
        decision_code="ACP_FEED_EXTENSIONS_AND_UPI_CIRCLE_VERIFIED",
        feed_extensions_whitelist_valid=True,
        undeclared_feed_extension_fields=[],
        upi_circle_delegate_id_opaque=True,
        upi_circle_cryptogram_fresh=True,
        upi_circle_npci_limit_respected=True,
        upi_circle_risk_signals_empty=True,
        violation_stage=None,
        remediation="none",
    )


def _jcs_serialize(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float):
        raise ValueError("Float encoding forbidden for currency minor units in AP2 open_mandate_hash")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_jcs_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        items = []
        for k in sorted(value.keys()):
            items.append(f"{json.dumps(str(k), ensure_ascii=False)}:{_jcs_serialize(value[k])}")
        return "{" + ",".join(items) + "}"
    raise TypeError(f"Unsupported JCS type: {type(value)!r}")


_RFC9421_QUOTED_COMPONENT_RE = re.compile(r'^"(?:[^"\s]+)"(?:\s+"(?:[^"\s]+)")*$')


def evaluate_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard(
    *,
    unsigned_open_checkout_mandate_claims: dict[str, Any],
    hashed_over_jws_compact_envelope: bool,
    applied_unicode_normalization_before_hash: bool,
    checkout_jwt_signature_alg: str,
    checkout_jwt_payload_entropy_bits: int,
    tap_signature_base_lines: list[str],
    tap_signature_input_components_raw: str,
    tap_signature_alg: str,
) -> AP2OpenMandateHashEntropyAndTAPSIMGuardResult:
    """Enforce AP2 PR #279 (`open_mandate_hash` JCS derivation), AP2 PR #278 (entropy-based `checkout_hash` allowing Ed25519), and Visa TAP PR #21 (RFC 9421 `@signature-params` conformance)."""
    if hashed_over_jws_compact_envelope:
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="AP2_OPEN_MANDATE_HASH_OVER_JWS_ENVELOPE_FORBIDDEN",
            open_mandate_hash_hex="",
            jcs_claims_only_hash_valid=False,
            unicode_codepoint_exactness_preserved=True,
            ed25519_checkout_entropy_valid=False,
            tap_rfc9421_signature_params_final_line=False,
            tap_individually_quoted_components_valid=False,
            violation_stage="open_mandate_hash_input",
            remediation="Compute open_mandate_hash = SHA-256(JCS_RFC8785(unsigned_open_checkout_mandate_body)) over the unsigned claims object, never over the JWS compact string (AP2 PR #279).",
        )

    if applied_unicode_normalization_before_hash:
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="AP2_OPEN_MANDATE_HASH_UNICODE_NORMALIZATION_FORBIDDEN",
            open_mandate_hash_hex="",
            jcs_claims_only_hash_valid=True,
            unicode_codepoint_exactness_preserved=False,
            ed25519_checkout_entropy_valid=False,
            tap_rfc9421_signature_params_final_line=False,
            tap_individually_quoted_components_valid=False,
            violation_stage="open_mandate_hash_unicode",
            remediation="Preserve exact Unicode code points (NFC vs NFD must produce distinct hashes per vectors 006a/006b) without pre-normalizing strings before RFC 8785 JCS hashing (AP2 PR #279).",
        )

    try:
        canonical_json = _jcs_serialize(unsigned_open_checkout_mandate_claims)
    except ValueError:
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="AP2_OPEN_MANDATE_HASH_FLOAT_MINOR_UNIT_REJECTED",
            open_mandate_hash_hex="",
            jcs_claims_only_hash_valid=False,
            unicode_codepoint_exactness_preserved=True,
            ed25519_checkout_entropy_valid=False,
            tap_rfc9421_signature_params_final_line=False,
            tap_individually_quoted_components_valid=False,
            violation_stage="open_mandate_hash_minor_units",
            remediation="Encode currency amounts as integer minor units per vector currency-minor-unit-005 (AP2 PR #279).",
        )

    open_mandate_hash_hex = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    if checkout_jwt_payload_entropy_bits < 128 or checkout_jwt_signature_alg not in {"EdDSA", "Ed25519", "ES256", "PS256"}:
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="AP2_CHECKOUT_HASH_LOW_PAYLOAD_ENTROPY_REJECTED",
            open_mandate_hash_hex=open_mandate_hash_hex,
            jcs_claims_only_hash_valid=True,
            unicode_codepoint_exactness_preserved=True,
            ed25519_checkout_entropy_valid=False,
            tap_rfc9421_signature_params_final_line=False,
            tap_individually_quoted_components_valid=False,
            violation_stage="checkout_jwt_entropy",
            remediation="Require >= 128 bits of payload entropy in the Checkout JWT so deterministic schemes like Ed25519 satisfy rainbow-table resistance without banning Ed25519 (AP2 PR #278).",
        )

    if (
        not tap_signature_base_lines
        or not tap_signature_base_lines[-1].startswith('"@signature-params": ')
        or any(line.startswith(("nonce:", "created:", "expires:")) for line in tap_signature_base_lines)
    ):
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="TAP_RFC9421_MISSING_SIGNATURE_PARAMS_LINE",
            open_mandate_hash_hex=open_mandate_hash_hex,
            jcs_claims_only_hash_valid=True,
            unicode_codepoint_exactness_preserved=True,
            ed25519_checkout_entropy_valid=True,
            tap_rfc9421_signature_params_final_line=False,
            tap_individually_quoted_components_valid=False,
            violation_stage="tap_rfc9421_signature_base",
            remediation="Reconstruct the RFC 9421 signature base with '@signature-params' as the final line instead of appending bare nonce/created/expires lines (visa/trusted-agent-protocol PR #21).",
        )

    if (
        not _RFC9421_QUOTED_COMPONENT_RE.match(tap_signature_input_components_raw.strip())
        or tap_signature_alg not in {"ed25519", "rsa-pss-sha256", "ed25519-ml-dsa-65"}
    ):
        return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
            admitted=False,
            decision_code="TAP_RFC9421_MALFORMED_COVERED_COMPONENTS_OR_ALG",
            open_mandate_hash_hex=open_mandate_hash_hex,
            jcs_claims_only_hash_valid=True,
            unicode_codepoint_exactness_preserved=True,
            ed25519_checkout_entropy_valid=True,
            tap_rfc9421_signature_params_final_line=True,
            tap_individually_quoted_components_valid=False,
            violation_stage="tap_rfc9421_covered_components",
            remediation='Parse RFC 9421 covered components as individually quoted identifiers ("@authority" "@path") and honor alg="ed25519" or "rsa-pss-sha256" (visa/trusted-agent-protocol PR #21).',
        )

    return AP2OpenMandateHashEntropyAndTAPSIMGuardResult(
        admitted=True,
        decision_code="AP2_OPEN_MANDATE_HASH_ENTROPY_AND_TAP_RFC9421_VERIFIED",
        open_mandate_hash_hex=open_mandate_hash_hex,
        jcs_claims_only_hash_valid=True,
        unicode_codepoint_exactness_preserved=True,
        ed25519_checkout_entropy_valid=True,
        tap_rfc9421_signature_params_final_line=True,
        tap_individually_quoted_components_valid=True,
        violation_stage=None,
        remediation="none",
    )
