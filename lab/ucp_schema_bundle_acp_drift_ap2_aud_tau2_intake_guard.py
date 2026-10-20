"""Stage 54 deterministic guards: UCP ucp-schema 2.0.0 bundled $ref restoration (#982)
& Variant seller.logo non-authority rule (#962), ACP JSON Schema <-> OpenAPI property
drift & allOf additionalProperties sibling starvation guard (#310, #290, #284, #275),
Google AP2 kb+sd-jwt+kb terminal aud/nonce enforcement (#369), cnf.jwk JSON-mode enum
serialization (#385/#383) & verify_receipt callback safety (#384) + Poppy v0.2 (#71),
and Sierra tau-bench 2.0.0 intake entity-capture policy (#642) + Visa TAP x402 checkout (#11).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
import re
from typing import Any, Callable


ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_12H_RE = re.compile(r"^(?:[1-9]|1[0-2]):[0-5]\d (?:AM|PM)$")


@dataclass(frozen=True)
class UcpSchemaBundleSellerLogoGuardResult:
    allowed: bool
    reason_code: str
    restored_ref_count: int
    normalized_cache_key: str
    seller_logo_present: bool
    seller_authority_bound: bool
    violations: tuple[str, ...]


def verify_ucp_schema_bundle_and_seller_logo(
    *,
    schema_path: str,
    direction: str = "response",
    operation: str = "read",
    bundle: bool = True,
    unbundled_refs: dict[str, str],
    bundled_properties: dict[str, dict[str, Any]],
    variant_payload: dict[str, Any],
    platform_claims_seller_discovery_authority: bool = False,
) -> UcpSchemaBundleSellerLogoGuardResult:
    """Verify UCP PR #982 bundled $ref restoration and PR #962 seller.logo rules."""
    violations: list[str] = []

    raw_path = PurePosixPath(schema_path)
    normalized_posix = str(Path(schema_path).resolve()) if ":" in schema_path or "\\" in schema_path else str(
        PurePosixPath("/", *[p for p in raw_path.parts if p not in ("", ".")])
    )
    if ".." in raw_path.parts:
        # Resolve parent segments deterministically
        resolved_parts: list[str] = []
        for part in raw_path.parts:
            if part in ("", ".", "/"):
                continue
            if part == "..":
                if resolved_parts:
                    resolved_parts.pop()
            else:
                resolved_parts.append(part)
        normalized_posix = "/" + "/".join(resolved_parts)

    bundle_suffix = ":bundled" if bundle else ""
    normalized_cache_key = f"{normalized_posix}:{direction}:{operation}{bundle_suffix}"
    if ".." in schema_path or schema_path.startswith("./"):
        # Verify caller did not leave relative segments in cache key
        if ".." in normalized_cache_key or "/./" in normalized_cache_key:
            violations.append("UNNORMALIZED_SCHEMA_CACHE_KEY")

    restored_count = 0
    for prop_path, expected_ref in unbundled_refs.items():
        if expected_ref.startswith("#/$defs/") and not expected_ref.endswith(":forwarded_cross_file"):
            # Same-file $defs that do not forward to a cross-file $ref are intentionally left alone
            continue
        prop_node = bundled_properties.get(prop_path)
        if not isinstance(prop_node, dict):
            violations.append(f"MISSING_BUNDLED_PROPERTY:{prop_path}")
            continue
        restored_ref = prop_node.get("$ref")
        if not isinstance(restored_ref, str) or not restored_ref.strip():
            violations.append(f"UNRESTORED_BUNDLED_CROSS_FILE_REF:{prop_path}")
        else:
            restored_count += 1

    seller = variant_payload.get("seller")
    seller_logo_present = False
    if seller is not None:
        if not isinstance(seller, dict):
            violations.append("INVALID_VARIANT_SELLER_OBJECT")
        else:
            logo = seller.get("logo")
            if logo is not None:
                if not isinstance(logo, dict):
                    violations.append("INVALID_SELLER_LOGO_MEDIA_OBJECT")
                else:
                    seller_logo_present = True
                    media_type = logo.get("type")
                    url = logo.get("url")
                    alt_text = logo.get("alt_text")
                    if not isinstance(media_type, str) or not media_type.strip():
                        violations.append("MISSING_SELLER_LOGO_MEDIA_TYPE")
                    if not isinstance(url, str) or not url.startswith("https://"):
                        violations.append("INVALID_SELLER_LOGO_URL")
                    if not isinstance(alt_text, str) or not alt_text.strip():
                        violations.append("MISSING_SELLER_LOGO_ALT_TEXT")

    if platform_claims_seller_discovery_authority:
        violations.append("SELLER_LOGO_AUTHORITY_CONFUSION_BLOCKED")

    allowed = len(violations) == 0
    reason_code = "OK" if allowed else violations[0]
    return UcpSchemaBundleSellerLogoGuardResult(
        allowed=allowed,
        reason_code=reason_code,
        restored_ref_count=restored_count,
        normalized_cache_key=normalized_cache_key,
        seller_logo_present=seller_logo_present,
        seller_authority_bound=False,
        violations=tuple(violations),
    )


@dataclass(frozen=True)
class AcpSchemaOpenApiDriftGuardResult:
    allowed: bool
    reason_code: str
    unlisted_drift_entries: tuple[str, ...]
    stale_known_entries: tuple[str, ...]
    violations: tuple[str, ...]


def verify_acp_schema_openapi_property_drift(
    *,
    version: str,
    spec_name: str,
    json_schema_defs: dict[str, dict[str, Any]],
    openapi_schemas: dict[str, dict[str, Any]],
    known_property_drift: set[str],
    allof_composed_schemas: dict[str, dict[str, Any]] | None = None,
) -> AcpSchemaOpenApiDriftGuardResult:
    """Verify ACP PR #310 JSON Schema <-> OpenAPI property drift and PRs #290/#284/#275."""
    violations: list[str] = []
    detected_drift: set[str] = set()
    composed_keywords = {
        "allOf",
        "oneOf",
        "anyOf",
        "not",
        "if",
        "then",
        "else",
        "$ref",
        "patternProperties",
        "discriminator",
    }

    for schema_name, oapi_obj in openapi_schemas.items():
        if not isinstance(oapi_obj, dict):
            continue
        if "display_order" in oapi_obj and "display_order" not in (oapi_obj.get("properties") or {}):
            violations.append(f"PAYMENT_HANDLER_DISPLAY_ORDER_MISINDENTED:{schema_name}")

    shared_names = sorted(set(json_schema_defs.keys()) & set(openapi_schemas.keys()))
    for name in shared_names:
        js_obj = json_schema_defs[name]
        oa_obj = openapi_schemas[name]
        if not isinstance(js_obj, dict) or not isinstance(oa_obj, dict):
            continue
        if any(k in js_obj for k in composed_keywords) or any(k in oa_obj for k in composed_keywords):
            continue
        js_props = set((js_obj.get("properties") or {}).keys())
        oa_props = set((oa_obj.get("properties") or {}).keys())
        if not js_props and not oa_props:
            continue
        for p in sorted(js_props - oa_props):
            detected_drift.add(f"{version}/{spec_name}/{name}/{p} json-only")
        for p in sorted(oa_props - js_props):
            detected_drift.add(f"{version}/{spec_name}/{name}/{p} openapi-only")

    unlisted = sorted(detected_drift - known_property_drift)
    stale = sorted(
        entry
        for entry in known_property_drift
        if entry.startswith(f"{version}/{spec_name}/") and entry not in detected_drift
    )
    for item in unlisted:
        violations.append(f"UNLISTED_SCHEMA_OPENAPI_PROPERTY_DRIFT:{item}")
    for item in stale:
        violations.append(f"STALE_KNOWN_DRIFT_ENTRY:{item}")

    if allof_composed_schemas:
        for composed_name, info in allof_composed_schemas.items():
            base_additional_props = info.get("base_additional_properties", True)
            base_props = set(info.get("base_properties") or ())
            sibling_props = set(info.get("sibling_properties") or ())
            starved = sorted(sibling_props - base_props)
            if base_additional_props is False and starved:
                violations.append(
                    f"ALLOF_ADDITIONAL_PROPERTIES_SIBLING_STARVATION:{composed_name}:{','.join(starved)}"
                )

    allowed = len(violations) == 0
    reason_code = "OK" if allowed else violations[0]
    return AcpSchemaOpenApiDriftGuardResult(
        allowed=allowed,
        reason_code=reason_code,
        unlisted_drift_entries=tuple(unlisted),
        stale_known_entries=tuple(stale),
        violations=tuple(violations),
    )


@dataclass(frozen=True)
class Ap2KbAudCnfPoppyDpopGuardResult:
    allowed: bool
    reason_code: str
    terminal_aud_verified: bool
    cnf_jwk_json_safe: bool
    receipt_verified: bool
    dpop_jti_bits: int
    violations: tuple[str, ...]


def verify_ap2_kb_aud_cnf_and_poppy_dpop_rules(
    *,
    terminal_hop_typ: str,
    token_aud: str,
    expected_aud: str,
    token_nonce: str,
    expected_nonce: str,
    cnf_jwk_payload: dict[str, Any],
    receipt_reference: str | None,
    has_reference_in_store_cb: Callable[[str | None], bool] | None,
    poppy_request_target: str,
    poppy_carries_session_token: bool,
    poppy_is_mcp_bearer_token_request: bool = False,
    poppy_dpop_proof: dict[str, Any] | None = None,
    poppy_http_method: str = "GET",
    poppy_idempotency_key: str | None = None,
) -> Ap2KbAudCnfPoppyDpopGuardResult:
    """Verify AP2 #369 kb+sd-jwt+kb aud/nonce enforcement, #385/#383 cnf.jwk JSON mode,
    #384 verify_receipt callback safety, and Poppy v0.2 #71 (39b35bd) DPoP/Idempotency rules.
    """
    violations: list[str] = []

    valid_kb_typs = {"kb+sd-jwt", "kb-sd-jwt", "kb+sd-jwt+kb", "kb-sd-jwt+kb"}
    if terminal_hop_typ not in valid_kb_typs:
        violations.append(f"INVALID_AP2_KB_TOKEN_TYP:{terminal_hop_typ}")

    # AP2 #369 fix: enforce expected_aud and expected_nonce on terminal hop even when typ is kb+sd-jwt+kb
    terminal_aud_verified = False
    if token_aud != expected_aud:
        violations.append("AP2_KB_SD_JWT_AUD_MISMATCH")
    elif token_nonce != expected_nonce:
        violations.append("AP2_KB_SD_JWT_NONCE_MISMATCH")
    else:
        terminal_aud_verified = True

    # AP2 #385 / #383: cnf.jwk must serialize enums (e.g. use, alg) as plain JSON strings
    cnf_jwk_json_safe = True
    for k, v in cnf_jwk_payload.items():
        if isinstance(v, Enum) or (k in ("use", "alg", "kty", "crv") and not isinstance(v, str)):
            cnf_jwk_json_safe = False
            violations.append(f"AP2_CNF_JWK_ENUM_NOT_JSON_SERIALIZED:{k}")

    # AP2 #384: check has_reference_in_store_cb is not None before calling
    receipt_verified = True
    if has_reference_in_store_cb is not None:
        if not has_reference_in_store_cb(receipt_reference):
            receipt_verified = False
            violations.append("AP2_RECEIPT_REFERENCE_NOT_IN_STORE")

    # Poppy v0.2 #71 (39b35bd): DPoP proof rules
    needs_dpop = (
        poppy_request_target == "token_endpoint" and not poppy_is_mcp_bearer_token_request
    ) or poppy_carries_session_token
    exempt_dpop = poppy_request_target in ("revocation", "device_authorization") or (
        poppy_request_target == "token_endpoint" and poppy_is_mcp_bearer_token_request
    )

    dpop_jti_bits = 0
    if needs_dpop and not exempt_dpop:
        if not isinstance(poppy_dpop_proof, dict):
            violations.append("POPPY_MISSING_DPOP_PROOF")
        else:
            alg = poppy_dpop_proof.get("alg")
            if alg != "ES256":
                violations.append(f"POPPY_INVALID_DPOP_ALG:{alg}")
            jti = str(poppy_dpop_proof.get("jti") or "")
            padded = jti + "=" * ((4 - len(jti) % 4) % 4)
            try:
                raw_jti = base64.urlsafe_b64decode(padded.encode("ascii"))
                dpop_jti_bits = len(raw_jti) * 8
            except Exception:
                dpop_jti_bits = 0
            if dpop_jti_bits < 128:
                violations.append(f"POPPY_DPOP_JTI_ENTROPY_TOO_LOW:{dpop_jti_bits}")

    if poppy_http_method.upper() in ("POST", "PUT", "PATCH", "DELETE") and poppy_request_target == "api_write":
        if not isinstance(poppy_idempotency_key, str) or len(poppy_idempotency_key.strip()) < 16:
            violations.append("POPPY_API_WRITE_MISSING_IDEMPOTENCY_KEY")

    allowed = len(violations) == 0
    reason_code = "OK" if allowed else violations[0]
    return Ap2KbAudCnfPoppyDpopGuardResult(
        allowed=allowed,
        reason_code=reason_code,
        terminal_aud_verified=terminal_aud_verified,
        cnf_jwk_json_safe=cnf_jwk_json_safe,
        receipt_verified=receipt_verified,
        dpop_jti_bits=dpop_jti_bits,
        violations=tuple(violations),
    )


def _verify_mod97_member_id(code: str) -> bool:
    digits = re.sub(r"\D", "", code)
    if len(digits) < 4:
        return False
    return int(digits) % 97 == 1


@dataclass(frozen=True)
class Tau2IntakeAndTapX402GuardResult:
    allowed: bool
    reason_code: str
    submitted_field_count: int
    x402_mode: str
    x402_total_usd: float
    violations: tuple[str, ...]


def verify_tau2_intake_and_tap_x402_checkout(
    *,
    consent_obtained: bool,
    ordered_missing_fields: tuple[str, ...],
    logged_captures: dict[str, str],
    submitted_fields: dict[str, str] | None,
    submit_call_count: int,
    call_ended_early: bool,
    submit_and_end_call_same_turn: bool,
    external_or_invented_fields: tuple[str, ...] = (),
    field_types: dict[str, str] | None = None,
    x402_enabled: bool = True,
    cart_subtotal_usd: float = 100.0,
    cart_tax_usd: float = 8.0,
    cart_shipping_usd: float = 0.0,
    cart_total_usd: float = 108.0,
    payment_signature_header: str | None = None,
    payment_required_header: str | None = None,
    payment_response_header: str | None = None,
    facilitator_settled: bool = False,
    configured_networks: tuple[str, ...] = (
        "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1",
        "eip155:84532",
    ),
) -> Tau2IntakeAndTapX402GuardResult:
    """Verify Sierra tau-bench 2.0.0 (#642) intake policy and Visa TAP (#11) x402 checkout."""
    violations: list[str] = []

    if not consent_obtained and (logged_captures or submitted_fields):
        violations.append("TAU2_INTAKE_MISSING_CONSENT_BEFORE_COLLECTION")

    if external_or_invented_fields:
        violations.append("EXTERNAL_OR_INVENTED_VALUE_BLOCKED")

    allowed_field_set = set(ordered_missing_fields)
    for field_name in logged_captures:
        if field_name not in allowed_field_set:
            violations.append(f"UNSCHEDULED_FIELD_COLLECTION_BLOCKED:{field_name}")

    if call_ended_early:
        if submit_call_count > 0 or submitted_fields:
            violations.append("EARLY_HANGUP_SUBMISSION_BLOCKED")
    else:
        if submit_call_count != 1 or not isinstance(submitted_fields, dict):
            violations.append(f"INVALID_SUBMIT_FIELDS_CALL_COUNT:{submit_call_count}")
        else:
            if set(submitted_fields.keys()) != allowed_field_set:
                violations.append("SUBMITTED_FIELDS_MISMATCH_CALLBACK_ORDER")
            for k, val in submitted_fields.items():
                if k not in logged_captures or logged_captures[k] != val:
                    violations.append(f"MISSING_LOG_CAPTURE_BEFORE_SUBMIT:{k}")
                ftype = (field_types or {}).get(k, "")
                if ftype == "date" and not ISO_DATE_RE.match(val):
                    violations.append(f"INVALID_DATE_OR_TIME_FORMAT:{k}")
                elif ftype == "time" and not TIME_12H_RE.match(val):
                    violations.append(f"INVALID_DATE_OR_TIME_FORMAT:{k}")
                elif ftype == "member_id_mod97" and not _verify_mod97_member_id(val):
                    violations.append(f"CODE_CHECK_DIGIT_INVALID:{k}")

    if submit_and_end_call_same_turn:
        violations.append("SUBMIT_AND_END_CALL_SAME_TURN_BLOCKED")

    # Visa TAP #11 x402 checkout verification
    if not x402_enabled:
        violations.append("TAP_X402_DISABLED_ON_SERVER")
    if not configured_networks:
        violations.append("TAP_X402_NO_WALLET_NETWORKS_CONFIGURED")

    expected_total = round(cart_subtotal_usd + cart_tax_usd + cart_shipping_usd, 2)
    if round(cart_total_usd, 2) != expected_total:
        violations.append("TAP_X402_CART_TOTAL_CONSERVATION_MISMATCH")

    if not payment_signature_header:
        x402_mode = "mode_a_402_challenge"
        if not isinstance(payment_required_header, str) or not payment_required_header.strip():
            violations.append("TAP_X402_MISSING_PAYMENT_REQUIRED_HEADER")
    else:
        x402_mode = "mode_b_facilitator_settle"
        if not facilitator_settled:
            violations.append("TAP_X402_FACILITATOR_SETTLEMENT_FAILED")
        if not isinstance(payment_response_header, str) or not payment_response_header.strip():
            violations.append("TAP_X402_MISSING_PAYMENT_RESPONSE_HEADER")

    allowed = len(violations) == 0
    reason_code = "OK" if allowed else violations[0]
    return Tau2IntakeAndTapX402GuardResult(
        allowed=allowed,
        reason_code=reason_code,
        submitted_field_count=len(submitted_fields or {}),
        x402_mode=x402_mode,
        x402_total_usd=round(cart_total_usd, 2),
        violations=tuple(violations),
    )
