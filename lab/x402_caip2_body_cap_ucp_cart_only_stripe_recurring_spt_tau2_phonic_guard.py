"""Stage 168 deterministic protocol & benchmark guardrails (2026-10-22 primary-source audit):
1. x402 Foundation (commits 3ca54cb #3285, 76f2f28 #3400, bc31d3e #3826, b70da0d #3567,
   6c379c4 #3715, d8e1e7b #3674, 332f65d #3125/#3293, 7438976 #3690, 0ff11aa #3425,
   1e7de94 #3717, 202ba81 #3728, 7617ece #3875, and PRs #3886, #3887, #3575 on 2026-10-22):
   - Strict V2 CAIP-2 network syntax (`^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$`) and V1 payload
     rejection in HTTP resource server with 402 instead of 500 (#3285, #3715).
   - Bounded HTTP response body reads (`1 MiB` for control-plane verify/settle/supported,
     `4 MiB` for Bazaar discovery) and shallow-copy immutability of `extensions` during 402
     response enrichment (#3400, #3826, #3567).
   - Cardano raw-CBOR byte-preserving broadcast (preventing Conway tag-258 re-serialization
     from breaking `vkey` witnesses), Stellar `TRY_AGAIN_LATER` retryable error classification,
     and EVM `exact`/`upto` retryable `failed_to_verify_signature` parity (#3674, #3293, #3690, #3886).
   - Python `x402[mcp]` `mcp<2` upper bound, client retry CORS response-header stripping, and
     Axios Cookie array semicolon preservation + `onPaymentResponse` before 4xx/5xx rejection
     (#3425, #3717, #3728, #3575).
2. Universal Commerce Protocol (UCP) (commits 2bbae24 #940, 4aa3127 #966, and PR #985 on 2026-10-22):
   - Cart-only checkout creation (#940): `create_checkout` requires `line_items` OR `cart_id`
     (`anyOf`); when `cart_id` is provided without negotiated `dev.ucp.shopping.cart` capability,
     the Business MUST reject the request rather than silently falling back to `line_items`;
     when both are present with negotiated Cart capability, Cart contents are authoritative.
   - Merged return policy (#966): explicit `eligibility.type` (`window` | `unlimited` | `not_accepted`),
     business-stated `expires_at` (zero platform date math), and typed `fees[]` ceiling.
   - Identity-linking client registration agnosticism (#985): supports out-of-band `client_id`
     or IETF Client ID Metadata Document HTTPS URL `client_id` with `token_endpoint_auth_methods_supported`
     verification, discarding invalid AS candidates without failing discovery unless none remain.
3. Stripe SPT Recurring & UCP Handler / Stripe AI / MCP (2026-10-22 official docs & commits):
   - Stripe Shared Payment Token (`spt_`) recurring charges (`usage_limits.recurring_interval`):
     rejects `setup_future_usage` and `payment_method_options[card][setup_future_usage]` on
     any `PaymentIntent` using an SPT (including recurring SPTs), and validates `off_session`
     against SPT permissions (`docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md`).
   - Stripe UCP Payment Handler (`com.stripe.payments` 2026-06-25 & `com.google.pay` 2026-01-23):
     blocks `link` completion on `com.stripe.payments`, enforces `binding` + `identity.access_token`
     parity, and defaults omitted SPT `expires_at` to `issued_at + 3600s`.
   - Stripe AI worker-thread event-loop-safe `StripeTool._run` (`326ea8b` / PR `#581`) and MCP
     `SEP-1932` DPoP proof / `SEP-2778` URL-mode `elicitationId` binding.
4. Sierra tau2-bench 2.0 (commit 05736c2 #640/#657/#669, and PRs #671, #670, #667, #666 on 2026-10-22):
   - Retail `exchange_delivered_order_items` same-item exchange rejection (`item_id == new_item_id`, #667).
   - Telecom `can_send_mms` empty-string `mmsc_url == ""` treated as unconfigured (#666).
   - Frozen benchmark LF (`eol=lf`) raw byte digest preservation across Windows checkouts (#671).
   - Phonic (`phonic-1`) speech-to-speech 8kHz G.711 mu-law (`mulaw_8000`) background pump and
     strict playback gating between `assistant_started_speaking` and `assistant_finished_speaking` (#670).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


CAIP2_V2_RE = re.compile(r"^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
MAX_CONTROL_PLANE_RESPONSE_BYTES = 1 << 20  # 1 MiB (1,048,576 bytes)
MAX_BAZAAR_DISCOVERY_RESPONSE_BYTES = 4 << 20  # 4 MiB (4,194,304 bytes)
QUERY_METHODS = frozenset({"GET", "HEAD", "DELETE"})
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
UCP_RETURN_ELIGIBILITIES = frozenset({"window", "unlimited", "not_accepted"})
STRIPE_RECURRING_INTERVALS = frozenset({"day", "week", "month", "year"})


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    details: dict[str, Any]


def validate_x402_caip2_body_cap_and_settlement_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate x402 2026-10-22 commits (#3285, #3400, #3826, #3567, #3715, #3674, #3293, #3690, #3886, #3425, #3717, #3728, #3575)."""
    network = payload.get("network")
    if not isinstance(network, str) or not CAIP2_V2_RE.match(network):
        return GuardDecision(
            allowed=False,
            decision_code="X402_CAIP2_NETWORK_SYNTAX_INVALID",
            reason="V2 network identifier must match strict CAIP-2 syntax ^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$ (#3285).",
            details={"network": network},
        )

    payment_version = payload.get("payment_signature_version", 2)
    server_status_on_v1 = payload.get("server_status_on_v1", 402)
    if payment_version == 1 and server_status_on_v1 != 402:
        return GuardDecision(
            allowed=False,
            decision_code="X402_V1_PAYLOAD_MUST_REJECT_WITH_402",
            reason="HTTP resource server must reject V1 payloads in PAYMENT-SIGNATURE with HTTP 402 instead of 500 (#3715).",
            details={
                "payment_signature_version": payment_version,
                "server_status_on_v1": server_status_on_v1,
            },
        )

    resp_check = payload.get("response_body_check", {})
    if isinstance(resp_check, Mapping):
        plane = str(resp_check.get("plane", "control"))
        body_bytes = int(resp_check.get("body_bytes", 0))
        limit = (
            MAX_BAZAAR_DISCOVERY_RESPONSE_BYTES
            if plane == "discovery"
            else MAX_CONTROL_PLANE_RESPONSE_BYTES
        )
        if body_bytes > limit:
            return GuardDecision(
                allowed=False,
                decision_code="X402_RESPONSE_BODY_TOO_LARGE",
                reason="Facilitator control-plane (1 MiB) and Bazaar discovery (4 MiB) response bodies must be bounded (#3400).",
                details={"plane": plane, "body_bytes": body_bytes, "limit": limit},
            )

    if payload.get("extensions_mutated_in_place") is True:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EXTENSIONS_OBJECT_MUTATED_ON_402",
            reason="createPaymentRequiredResponse must shallow-copy extensions so 402 enrichment never mutates route declarations (#3826).",
            details={},
        )

    bazaar_probe = payload.get("bazaar_probe", {})
    if isinstance(bazaar_probe, Mapping) and bazaar_probe:
        has_body_type = bool(bazaar_probe.get("has_body_type"))
        advertised_method = str(bazaar_probe.get("advertised_method", "GET")).upper()
        if (has_body_type and advertised_method not in BODY_METHODS) or (
            not has_body_type and advertised_method not in QUERY_METHODS
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_BAZAAR_METHOD_INPUT_CONTRADICTION",
                reason="Bazaar advertised HTTP method must match declared input shape (bodyType -> POST/PUT/PATCH, query -> GET/HEAD/DELETE, #3567).",
                details=dict(bazaar_probe),
            )

    cardano_tx = payload.get("cardano_tx", {})
    if isinstance(cardano_tx, Mapping) and cardano_tx:
        if cardano_tx.get("reencoded_cbor_before_submit") is True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_CARDANO_CBOR_REENCODE_MUTATION_FORBIDDEN",
                reason="Cardano facilitator must submit signed transaction bytes unchanged via raw-CBOR endpoint without tag-258 re-serialization (#3674).",
                details=dict(cardano_tx),
            )

    stellar_settle = payload.get("stellar_settle", {})
    if isinstance(stellar_settle, Mapping) and stellar_settle:
        rpc_status = stellar_settle.get("rpc_status")
        error_reason = stellar_settle.get("error_reason")
        if (
            rpc_status == "TRY_AGAIN_LATER"
            and error_reason != "settle_exact_stellar_transaction_submission_retryable"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_STELLAR_TRY_AGAIN_LATER_MUST_BE_RETRYABLE",
                reason="Stellar TRY_AGAIN_LATER status must surface retryable errorReason settle_exact_stellar_transaction_submission_retryable (#3293).",
                details=dict(stellar_settle),
            )

    evm_verify = payload.get("evm_verify", {})
    if isinstance(evm_verify, Mapping) and evm_verify:
        if evm_verify.get("payer_code_lookup_failed") is True:
            scheme = str(evm_verify.get("scheme", "exact"))
            expected_err = (
                "invalid_upto_evm_failed_to_verify_signature"
                if scheme == "upto"
                else "invalid_exact_evm_failed_to_verify_signature"
            )
            if evm_verify.get("reported_error") != expected_err:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_EVM_CODE_LOOKUP_ERROR_MISCLASSIFIED",
                    reason="Failed payer code/signature RPC lookup must report failed_to_verify_signature rather than invalid_signature (#3690/#3886).",
                    details={**dict(evm_verify), "expected_error": expected_err},
                )

    client_hygiene = payload.get("client_hygiene", {})
    if isinstance(client_hygiene, Mapping) and client_hygiene:
        if client_hygiene.get("mcp_major_version", 1) >= 2:
            return GuardDecision(
                allowed=False,
                decision_code="X402_PYTHON_MCP_MAJOR_V2_UNSUPPORTED",
                reason="x402[mcp] must be bounded to mcp<2 so mcp.server.fastmcp remains available (#3425).",
                details=dict(client_hygiene),
            )
        if client_hygiene.get("retry_sent_access_control_expose_headers") is True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_CLIENT_RETRY_CORS_RESPONSE_HEADER_FORBIDDEN",
                reason="Client payment retries must not send response-only Access-Control-Expose-Headers (#3717).",
                details=dict(client_hygiene),
            )
        if client_hygiene.get("axios_cookie_array_dropped_or_comma_joined") is True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_AXIOS_COOKIE_ARRAY_CORRUPTED",
                reason="@x402/axios must preserve Cookie arrays for semicolon serialization on paid retries (#3728).",
                details=dict(client_hygiene),
            )

    return GuardDecision(
        allowed=True,
        decision_code="X402_CAIP2_BODY_CAP_AND_SETTLEMENT_VERIFIED",
        reason="All x402 2026-10-22 CAIP-2, body-cap, extension immutability, Cardano/Stellar/EVM, and client hygiene guards passed.",
        details={"network": network},
    )


def validate_ucp_cart_only_checkout_and_return_identity_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP 2026-10-22 commits (2bbae24 #940 cart-only checkout, 4aa3127 #966 return policy, and #985 client identity)."""
    checkout_create = payload.get("checkout_create", {})
    if not isinstance(checkout_create, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CHECKOUT_CREATE_INVALID",
            reason="checkout_create must be a mapping (#940).",
            details={},
        )

    has_cart_id = bool(checkout_create.get("cart_id"))
    line_items = checkout_create.get("line_items")
    has_line_items = isinstance(line_items, list) and len(line_items) > 0
    cart_capability_negotiated = bool(
        checkout_create.get("cart_capability_negotiated", False)
    )

    if not has_cart_id and line_items is None:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CREATE_CHECKOUT_MISSING_ITEM_SOURCE",
            reason="Create Checkout requires at least one of line_items or cart_id via schema anyOf (#940, 2bbae24).",
            details=dict(checkout_create),
        )

    if has_cart_id and not cart_capability_negotiated:
        if checkout_create.get("business_rejected_unnegotiated_cart_id") is not True:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_UNNEGOTIATED_CART_ID_SILENT_FALLBACK_FORBIDDEN",
                reason="Business MUST reject Create Checkout providing cart_id when Cart capability is not negotiated, and MUST NOT fall back to inline line_items (#940, 2bbae24).",
                details=dict(checkout_create),
            )

    if has_cart_id and has_line_items and cart_capability_negotiated:
        if checkout_create.get("authoritative_source", "cart") != "cart":
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CART_PRECEDENCE_VIOLATION",
                reason="When both cart_id and line_items are present, Cart contents are authoritative and overlapping checkout fields must be ignored (#940, 2bbae24).",
                details=dict(checkout_create),
            )

    return_policy = payload.get("return_policy", {})
    if isinstance(return_policy, Mapping) and return_policy:
        eligibility_type = return_policy.get("eligibility_type")
        if eligibility_type not in UCP_RETURN_ELIGIBILITIES:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_RETURN_ELIGIBILITY_TYPE_INVALID",
                reason="Return eligibility.type must be explicitly 'window', 'unlimited', or 'not_accepted'; omitted never means unlimited (#966, 4aa3127).",
                details=dict(return_policy),
            )
        if return_policy.get("platform_did_date_math") is True:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_RETURN_PLATFORM_DATE_MATH_FORBIDDEN",
                reason="The Business states return deadlines and platforms must do no date math (#966, 4aa3127).",
                details=dict(return_policy),
            )
        charged_fee = int(return_policy.get("charged_fee_minor", 0))
        stated_max_fee = int(return_policy.get("stated_max_fee_minor", 0))
        if charged_fee > stated_max_fee:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_RETURN_FEE_EXCEEDS_STATED_CEILING",
                reason="Charged return fee cannot exceed the business-stated typed fee ceiling (#966, 4aa3127).",
                details=dict(return_policy),
            )

    identity_linking = payload.get("identity_linking", {})
    if isinstance(identity_linking, Mapping) and identity_linking:
        auth_method = identity_linking.get("client_auth_method")
        supported_methods = identity_linking.get(
            "token_endpoint_auth_methods_supported", []
        )
        if (
            isinstance(supported_methods, list)
            and supported_methods
            and auth_method not in supported_methods
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDENTITY_CLIENT_AUTH_METHOD_UNSUPPORTED",
                reason="Platform must authenticate at the token endpoint using a method listed in token_endpoint_auth_methods_supported (#985).",
                details=dict(identity_linking),
            )
        if (
            identity_linking.get("single_invalid_as_entry_aborted_discovery") is True
            and int(identity_linking.get("remaining_valid_as_entries", 0)) > 0
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDENTITY_DISCOVERY_PREMATURE_ABORT",
                reason="An invalid AS candidate entry must be discarded and must not fail discovery when valid entries remain (#985).",
                details=dict(identity_linking),
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_CART_ONLY_RETURN_AND_IDENTITY_VERIFIED",
        reason="UCP #940 cart-only checkout creation, #966 explicit return policy, and #985 client identity rules verified.",
        details={"has_cart_id": has_cart_id, "has_line_items": has_line_items},
    )


def validate_stripe_recurring_spt_ucp_handler_and_toolkit_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Stripe 2026-10-22 recurring SPT rules, UCP handler contract, and Stripe AI #581 worker-thread loop safety."""
    spt_pi = payload.get("spt_payment_intent", {})
    if isinstance(spt_pi, Mapping) and spt_pi:
        uses_spt = bool(spt_pi.get("uses_shared_payment_granted_token", True))
        if uses_spt:
            if (
                spt_pi.get("setup_future_usage") is not None
                or spt_pi.get("card_setup_future_usage") is not None
            ):
                return GuardDecision(
                    allowed=False,
                    decision_code="STRIPE_SPT_SETUP_FUTURE_USAGE_REJECTED",
                    reason="Stripe rejects setup_future_usage and payment_method_options[card][setup_future_usage] when creating or confirming a PaymentIntent with an SPT, including a recurring SPT (2026-10-22).",
                    details=dict(spt_pi),
                )
            if spt_pi.get("is_recurring_charge") is True:
                recurring_interval = spt_pi.get("spt_recurring_interval")
                if recurring_interval not in STRIPE_RECURRING_INTERVALS:
                    return GuardDecision(
                        allowed=False,
                        decision_code="STRIPE_SPT_RECURRING_INTERVAL_REQUIRED",
                        reason="Recurring charges reusing an SPT directly in each PaymentIntent require usage_limits.recurring_interval on the SPT (2026-10-22).",
                        details=dict(spt_pi),
                    )
            if (
                spt_pi.get("off_session") is True
                and spt_pi.get("spt_off_session_permitted") is False
            ):
                return GuardDecision(
                    allowed=False,
                    decision_code="STRIPE_SPT_OFF_SESSION_PERMISSION_DENIED",
                    reason="Stripe validates off_session separately against the SPT's permissions (2026-10-22).",
                    details=dict(spt_pi),
                )

    ucp_handler = payload.get("stripe_ucp_handler", {})
    if isinstance(ucp_handler, Mapping) and ucp_handler:
        instrument_type = ucp_handler.get("instrument_type")
        handler_id = ucp_handler.get("handler_id")
        if instrument_type == "link" and handler_id == "stripe_payments":
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_UCP_LINK_COMPLETION_UNSUPPORTED",
                reason="Link can appear in com.stripe.payments configuration, but this handler does not support Link payment completion (2026-10-22).",
                details=dict(ucp_handler),
            )
        if ucp_handler.get("identity_access_token") != ucp_handler.get(
            "seller_business_profile"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_UCP_BUSINESS_PROFILE_MISMATCH",
                reason="Tokenization identity.access_token must match the checkout handler's config.business_profile (2026-10-22).",
                details=dict(ucp_handler),
            )

    toolkit_sync = payload.get("stripe_toolkit_sync_run", {})
    if isinstance(toolkit_sync, Mapping) and toolkit_sync:
        if toolkit_sync.get("uses_deprecated_get_event_loop") is True:
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_TOOLKIT_DEPRECATED_GET_EVENT_LOOP_FORBIDDEN",
                reason="StripeTool._run must use asyncio.get_running_loop() + asyncio.run() fallback so sync LangChain/CrewAI calls succeed when worker threads have no event loop (#581).",
                details=dict(toolkit_sync),
            )

    return GuardDecision(
        allowed=True,
        decision_code="STRIPE_RECURRING_SPT_UCP_AND_TOOLKIT_VERIFIED",
        reason="Stripe recurring SPT rules, UCP payment handler contract, and thread-safe toolkit execution verified.",
        details={},
    )


def validate_tau2_exchange_mms_windows_hash_and_phonic_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Sierra tau2-bench 2.0 2026-10-22 PRs (#667 retail exchange, #666 telecom MMS, #671 Windows LF hash, #670 Phonic voice)."""
    retail_exchange = payload.get("retail_exchange", {})
    if isinstance(retail_exchange, Mapping) and retail_exchange:
        item_ids = retail_exchange.get("item_ids", [])
        new_item_ids = retail_exchange.get("new_item_ids", [])
        if isinstance(item_ids, list) and isinstance(new_item_ids, list):
            for old_id, new_id in zip(item_ids, new_item_ids):
                if old_id == new_id:
                    return GuardDecision(
                        allowed=False,
                        decision_code="TAU2_RETAIL_SAME_ITEM_EXCHANGE_REJECTED",
                        reason="exchange_delivered_order_items rejects an exchange where new_item_id equals item_id (#667).",
                        details={"item_id": old_id, "new_item_id": new_id},
                    )

    telecom_mms = payload.get("telecom_mms", {})
    if isinstance(telecom_mms, Mapping) and telecom_mms:
        mmsc_url = telecom_mms.get("mmsc_url")
        can_send_mms_result = telecom_mms.get("can_send_mms_result", False)
        if (mmsc_url is None or str(mmsc_url).strip() == "") and can_send_mms_result is True:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_TELECOM_EMPTY_MMSC_URL_UNCONFIGURED",
                reason="Telecom can_send_mms must treat an empty MMSC URL ('') as unconfigured matching check_apn_settings (#666).",
                details=dict(telecom_mms),
            )

    frozen_hash = payload.get("frozen_benchmark_checkout", {})
    if isinstance(frozen_hash, Mapping) and frozen_hash:
        if frozen_hash.get("line_endings") == "CRLF":
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_WINDOWS_CRLF_FROZEN_HASH_DRIFT",
                reason="Frozen benchmark pins hash raw file bytes, so text checkouts must retain LF (* text=auto eol=lf, #671).",
                details=dict(frozen_hash),
            )

    phonic_voice = payload.get("phonic_voice_adapter", {})
    if isinstance(phonic_voice, Mapping) and phonic_voice:
        if phonic_voice.get("audio_format") != "mulaw_8000":
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_PHONIC_AUDIO_FORMAT_MISMATCH",
                reason="Phonic speech-to-speech adapter requires 8 kHz G.711 mu-law (mulaw_8000) pass-through (#670).",
                details=dict(phonic_voice),
            )
        if phonic_voice.get("queued_inter_utterance_silence_frames") is True:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_PHONIC_INTER_UTTERANCE_SILENCE_QUEUE_DELAY",
                reason="Phonic adapter must play frames only between assistant_started_speaking and assistant_finished_speaking so silence frames during orchestrator stalls do not delay later replies (#670).",
                details=dict(phonic_voice),
            )
        if not phonic_voice.get("session_id"):
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_PHONIC_SESSION_ID_MISSING",
                reason="Phonic provider must record conversation_created.conversation_id as provider.session_id (#670).",
                details=dict(phonic_voice),
            )

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_EXCHANGE_MMS_HASH_AND_PHONIC_VERIFIED",
        reason="Sierra tau2-bench 2.0 #667 retail exchange, #666 telecom MMS, #671 LF frozen hash, and #670 Phonic audio-native adapter verified.",
        details={},
    )
