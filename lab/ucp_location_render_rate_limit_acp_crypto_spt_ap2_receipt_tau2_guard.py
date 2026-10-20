"""Stage 112 deterministic protocol guardrails:
1. UCP (#642, #635, #622): `context.location` precedence rules, `com.mercadopago.payment.render_artifact`
   inert trust contract, and MCP Shopping `-32004` (`rate_limit_exceeded`) retry signaling.
2. ACP (#116, #111): ISO/IEC 7812-1 `PaymentMethodCard.iin` 6..8 digit validation and `PaymentMethodCrypto`
   (`type: "crypto"`, `x402_payload`) SPT deferred-settlement alignment.
3. Google AP2 (#385, #365) + Coinbase x402 (#324): JSON-mode string serialization for `cnf.jwk` enums,
   signature-first `verify_receipt` before `has_reference_in_store_cb`, and EIP-3009 4-field EIP-712 domain mapping.
4. Sierra tau2-bench (#632, #602, #600): `tau2 factory` 4-word `non_directed_phrases` & `<=1` bounded repair,
   lowercase airline `user_id`, and `check_status_bar` telecom user-simulator grounding.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Stage112GuardResult:
    allowed: bool
    decision_code: str
    detail: str
    metadata: dict[str, Any]


def resolve_ucp_effective_location(payload: Mapping[str, Any]) -> str:
    """Resolve effective store/branch location with authoritative override (#642)."""
    pickup_loc = str(payload.get("fulfillment_pickup_location_id", "") or "").strip()
    if pickup_loc:
        return pickup_loc
    fulfills_to = str(payload.get("catalog_search_fulfills_to", "") or "").strip()
    if fulfills_to:
        return fulfills_to
    ctx = payload.get("context", {})
    if isinstance(ctx, Mapping):
        return str(ctx.get("location", "") or "").strip()
    return ""


def validate_ucp_location_render_artifact_and_rate_limit_guard(
    payload: Mapping[str, Any],
) -> Stage112GuardResult:
    """Validate UCP #642 `context.location` precedence, #635 `render_artifact`, and #622 `-32004` rate limit."""
    eff_loc = resolve_ucp_effective_location(payload)
    claimed_loc = payload.get("claimed_effective_location")
    if claimed_loc is not None and str(claimed_loc) != eff_loc:
        return Stage112GuardResult(
            False,
            "UCP_LOCATION_PRECEDENCE_VIOLATION",
            "`context.location` hint must yield to authoritative `filters.fulfills_to` or `fulfillment.pickup_location_id` (#642).",
            {"expected_location": eff_loc, "claimed_location": claimed_loc},
        )

    artifact = payload.get("render_artifact_action", {})
    if isinstance(artifact, Mapping) and artifact:
        if "required" in artifact:
            return Stage112GuardResult(
                False,
                "UCP_RENDER_ARTIFACT_FORBIDDEN_REQUIRED_FIELD",
                "`com.mercadopago.payment.render_artifact` instances must not carry `required`; gating uses recoverable Message (#635).",
                {},
            )
        if artifact.get("contains_credentials_or_otp") is True:
            return Stage112GuardResult(
                False,
                "UCP_RENDER_ARTIFACT_CREDENTIAL_LEAK_BLOCKED",
                "`render_artifact` trust contract forbids PAN, OTP, or credentials in display data (#635).",
                {},
            )
        if artifact.get("uses_continue_url_redirect") is True:
            return Stage112GuardResult(
                False,
                "UCP_RENDER_ARTIFACT_REDIRECT_FORBIDDEN",
                "In-session `render_artifact` resolves by polling Get Checkout without `continue_url` redirects (#635).",
                {},
            )
        inst_url = str(artifact.get("instructions_url", "") or "")
        allowed_origins = tuple(str(x) for x in artifact.get("allowed_https_origins", ["https://www.mercadopago.com"]))
        if inst_url and (not inst_url.startswith("https://") or not inst_url.startswith(allowed_origins)):
            return Stage112GuardResult(
                False,
                "UCP_RENDER_ARTIFACT_UNTRUSTED_INSTRUCTIONS_URL",
                "`instructions_url` must use an allowlisted `https://` origin (#635).",
                {"instructions_url": inst_url},
            )

    mcp_err = payload.get("mcp_error", {})
    if isinstance(mcp_err, Mapping) and mcp_err:
        if mcp_err.get("error_slug") == "rate_limit_exceeded":
            if mcp_err.get("code") != -32004 or mcp_err.get("declared_methods_count", 13) != 13:
                return Stage112GuardResult(
                    False,
                    "UCP_MCP_RATE_LIMIT_ERROR_CONTRACT_INVALID",
                    "MCP Shopping `rate_limit_exceeded` must use code `-32004` across all 13 methods (#622).",
                    {"code": mcp_err.get("code"), "declared_methods_count": mcp_err.get("declared_methods_count")},
                )

    return Stage112GuardResult(
        True,
        "UCP_LOCATION_RENDER_ARTIFACT_AND_RATE_LIMIT_VERIFIED",
        "UCP #642 `context.location` precedence, #635 `render_artifact` contract, and #622 `-32004` verified.",
        {"effective_location": eff_loc},
    )


_IIN_RE = re.compile(r"^\d{6,8}$")
_SUPPORTED_X402_NETWORKS = frozenset({"eip155:8453", "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"})


def validate_acp_iin_length_and_crypto_spt_guard(
    payload: Mapping[str, Any],
) -> Stage112GuardResult:
    """Validate ACP #116 6..8 digit IIN maxLength and #111 x402-backed `PaymentMethodCrypto` SPT issuance."""
    card = payload.get("payment_method_card", {})
    if isinstance(card, Mapping) and card:
        iin = str(card.get("iin", ""))
        if not _IIN_RE.match(iin):
            return Stage112GuardResult(
                False,
                "ACP_CARD_IIN_LENGTH_OR_FORMAT_INVALID",
                "`PaymentMethodCard.iin` must be a 6-to-8 digit ISO/IEC 7812-1 string (#116).",
                {"iin": iin},
            )

    crypto = payload.get("payment_method_crypto", {})
    if isinstance(crypto, Mapping) and crypto:
        if crypto.get("type") != "crypto":
            return Stage112GuardResult(
                False,
                "ACP_CRYPTO_METHOD_TYPE_INVALID",
                "`PaymentMethodCrypto.type` must equal `\"crypto\"` (#111).",
                {"type": crypto.get("type")},
            )
        network = str(crypto.get("network", ""))
        if network not in _SUPPORTED_X402_NETWORKS:
            return Stage112GuardResult(
                False,
                "ACP_X402_NETWORK_UNSUPPORTED",
                "Unsupported CAIP-2 network for ACP `PaymentMethodCrypto` (`x402_network_unsupported`, #111).",
                {"network": network},
            )
        if crypto.get("signature_verified") is not True or crypto.get("nonce_unused") is not True:
            return Stage112GuardResult(
                False,
                "ACP_X402_PAYLOAD_INVALID_OR_REPLAYED",
                "Facilitator verification failed for signature or reused nonce (`x402_invalid`/`x402_rejected`, #111).",
                {},
            )
        if int(crypto.get("valid_before", 0)) <= int(crypto.get("current_unix", 0)):
            return Stage112GuardResult(
                False,
                "ACP_X402_AUTHORIZATION_EXPIRED",
                "x402 authorization `validBefore` has already expired (`x402_rejected`, #111).",
                {},
            )
        if int(crypto.get("x402_amount_minor", 0)) != int(crypto.get("allowance_amount_minor", -1)):
            return Stage112GuardResult(
                False,
                "ACP_X402_ALLOWANCE_AMOUNT_MISMATCH",
                "x402 signed payload amount must match `delegate_payment` allowance amount (#111).",
                {
                    "x402_amount_minor": crypto.get("x402_amount_minor"),
                    "allowance_amount_minor": crypto.get("allowance_amount_minor"),
                },
            )

    return Stage112GuardResult(
        True,
        "ACP_IIN_LENGTH_AND_CRYPTO_SPT_VERIFIED",
        "ACP #116 6..8 digit IIN and #111 x402-based `PaymentMethodCrypto` SPT flow verified.",
        {},
    )


def validate_ap2_jwk_json_receipt_key_and_x402_eip712_domain_guard(
    payload: Mapping[str, Any],
) -> Stage112GuardResult:
    """Validate AP2 #385 JSON-mode `cnf.jwk`, #365 `verify_receipt` order, and x402 #324 EIP-712 domain mapping."""
    cnf_jwk = payload.get("ap2_cnf_jwk", {})
    if isinstance(cnf_jwk, Mapping) and cnf_jwk:
        use_val = cnf_jwk.get("use")
        kty_val = cnf_jwk.get("kty")
        if type(use_val) is not str or type(kty_val) is not str or "." in str(use_val):
            return Stage112GuardResult(
                False,
                "AP2_CNF_JWK_ENUM_NOT_JSON_SERIALIZED",
                "`ParsedToken.cnf_jwk` must dump `JsonWebKey` with `mode=\"json\"` so `use`/`kty` are plain strings (#385).",
                {"use": repr(use_val), "kty": repr(kty_val)},
            )

    receipt = payload.get("ap2_receipt_verification", {})
    if isinstance(receipt, Mapping) and receipt:
        key_kind = str(receipt.get("public_key_kind", "jwk"))
        if key_kind not in ("jwk", "pyca_ec"):
            return Stage112GuardResult(
                False,
                "AP2_RECEIPT_UNSUPPORTED_KEY_TYPE",
                "`ReceiptClient.verify_receipt` only accepts JWK or `pyca` EC public keys normalized via `JWK.from_pyca` (#365).",
                {"public_key_kind": key_kind},
            )
        sig_ok = receipt.get("signature_valid") is True
        ref_cb_called = receipt.get("reference_callback_invoked") is True
        if not sig_ok and ref_cb_called:
            return Stage112GuardResult(
                False,
                "AP2_RECEIPT_REFERENCE_CALLBACK_BEFORE_SIG_CHECK",
                "Receipts with invalid signatures must be rejected before invoking `has_reference_in_store_cb` (#365).",
                {},
            )
        if not sig_ok:
            return Stage112GuardResult(
                False,
                "AP2_RECEIPT_SIGNATURE_INVALID",
                "Receipt JWS signature failed verification (#365).",
                {},
            )
        if receipt.get("reference_in_store") is False:
            return Stage112GuardResult(
                False,
                "AP2_RECEIPT_REFERENCE_NOT_FOUND_IN_STORE",
                "Valid receipt signature but `receipt_reference_not_found_in_store` (#365).",
                {},
            )

    eip3009 = payload.get("x402_eip3009_domain", {})
    if isinstance(eip3009, Mapping) and eip3009:
        req = eip3009.get("payment_requirements", {})
        dom = eip3009.get("eip712_domain", {})
        extra = req.get("extra", {}) if isinstance(req, Mapping) else {}
        net = str(req.get("network", "eip155:0"))
        expected_chain_id = int(net.split(":")[1]) if ":" in net and net.split(":")[1].isdigit() else -1
        if (
            dom.get("name") != extra.get("name")
            or dom.get("version") != extra.get("version")
            or int(dom.get("chainId", -2)) != expected_chain_id
            or str(dom.get("verifyingContract", "")).lower() != str(req.get("asset", "")).lower()
        ):
            return Stage112GuardResult(
                False,
                "X402_EIP3009_EIP712_DOMAIN_MAPPING_MISMATCH",
                "EIP-3009 `TransferWithAuthorization` EIP-712 domain must map `(extra.name, extra.version, network chainId, asset)` (#324).",
                {"domain": dict(dom)},
            )

    return Stage112GuardResult(
        True,
        "AP2_JWK_RECEIPT_AND_X402_EIP712_DOMAIN_VERIFIED",
        "AP2 #385 JSON JWK, #365 EC receipt verification order, and x402 #324 EIP-712 domain mapping verified.",
        {},
    )


def validate_tau2_factory_brevity_airline_userid_and_status_bar_guard(
    payload: Mapping[str, Any],
) -> Stage112GuardResult:
    """Validate Sierra tau2-bench #632 factory draft budgets/repair, #602 lowercase airline `user_id`, and #600 `check_status_bar`."""
    factory = payload.get("factory_draft", {})
    if isinstance(factory, Mapping) and factory:
        lang = str(factory.get("pack_language", "en"))
        has_origin = bool(factory.get("has_language_directive_origin", False))
        if (lang == "en" and has_origin) or (lang != "en" and not has_origin):
            return Stage112GuardResult(
                False,
                "TAU2_FACTORY_LANGUAGE_DIRECTIVE_RULE_VIOLATION",
                "Non-English packs must supply `language_directive.origin` and English packs must omit it (#632).",
                {"pack_language": lang, "has_language_directive_origin": has_origin},
            )
        phrases = factory.get("non_directed_phrases", [])
        if isinstance(phrases, Sequence):
            for phrase in phrases:
                if len(str(phrase).split()) > 4:
                    return Stage112GuardResult(
                        False,
                        "TAU2_FACTORY_NON_DIRECTED_PHRASE_BUDGET_EXCEEDED",
                        "`non_directed_phrases` entries must not exceed the 4-word brevity budget (#632).",
                        {"phrase": str(phrase)},
                    )
        if int(factory.get("repair_attempts", 0)) > 1:
            return Stage112GuardResult(
                False,
                "TAU2_FACTORY_BOUNDED_REPAIR_EXCEEDED",
                "`tau2 factory` draft repair is bounded to at most 1 `factory_draft_repair` call (#632).",
                {"repair_attempts": factory.get("repair_attempts")},
            )

    airline = payload.get("airline_tool_call", {})
    if isinstance(airline, Mapping) and airline:
        uid = str(airline.get("user_id", ""))
        if not uid or uid != uid.lower():
            return Stage112GuardResult(
                False,
                "TAU2_AIRLINE_USER_ID_NOT_LOWERCASE",
                "Airline `user_id` must be entirely lowercase (`book_reservation`, `get_user_details`, `send_certificate`, #602).",
                {"user_id": uid},
            )

    telecom_grounding = payload.get("telecom_tool_grounding", {})
    if isinstance(telecom_grounding, Mapping) and telecom_grounding:
        referenced_tools = [str(x) for x in telecom_grounding.get("referenced_user_tools", [])]
        if "get_status_bar" in referenced_tools or "check_status_bar" not in referenced_tools:
            return Stage112GuardResult(
                False,
                "TAU2_TELECOM_STATUS_BAR_TOOL_GROUNDING_MISMATCH",
                "Telecom user-simulator instructions must reference exposed `check_status_bar` instead of phantom `get_status_bar` (#600).",
                {"referenced_user_tools": referenced_tools},
            )

    return Stage112GuardResult(
        True,
        "TAU2_FACTORY_AIRLINE_USERID_AND_STATUS_BAR_VERIFIED",
        "Sierra tau2-bench #632 factory brevity/bounded repair, #602 lowercase airline `user_id`, and #600 `check_status_bar` verified.",
        {},
    )
