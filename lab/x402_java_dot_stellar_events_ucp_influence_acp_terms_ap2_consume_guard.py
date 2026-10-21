"""Stage 144 deterministic guardrails for x402 Java dot-segment/Stellar/body-cap/minDeposit, UCP commercial influence/browser cart/invoice-SEPA/at-property currency, ACP 3DS terms_digest/MCP idempotency, AP2 single-use mandate/receipt/instrument-type/PSP key/token rollback, MCP stateless error codes, Stripe MCP resourceTemplates, Visa TAP signed receipt, and tau2-bench thought-signature/seed/order invariance."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import unquote


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# 1. JS-01: x402 #3864 Java normalizePath() decode-before-dot-resolution & root .. clamping
def evaluate_x402_java_decode_before_dot_segment_guard(
    *,
    raw_request_path: str,
    protected_prefixes: tuple[str, ...] = ("/private", "/paid"),
) -> dict[str, Any]:
    path = raw_request_path or "/"
    for _ in range(4):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    segments: list[str] = []
    clamped_above_root = False
    for seg in path.split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            if segments:
                segments.pop()
            else:
                clamped_above_root = True
        else:
            segments.append(seg)
    normalized = "/" + "/".join(segments)
    requires_payment = any(
        normalized == prefix or normalized.startswith(prefix.rstrip("/") + "/")
        for prefix in protected_prefixes
    )
    naive_matched = any(
        raw_request_path == prefix or raw_request_path.startswith(prefix.rstrip("/") + "/")
        for prefix in protected_prefixes
    )
    bypass_blocked = requires_payment and not naive_matched
    return {
        "normalized_path": normalized,
        "requires_payment": requires_payment,
        "clamped_above_root": clamped_above_root,
        "bypass_blocked": bypass_blocked,
        "reason": (
            "X402_JAVA_ENCODED_DOT_SEGMENT_PAYWALL_BYPASS_BLOCKED"
            if bypass_blocked
            else "OK"
        ),
    }


# 2. JS-02: x402 #3399 Stellar Soroban informational events vs payment asset emitter & single transfer
def evaluate_x402_stellar_soroban_emitter_event_guard(
    *,
    requirements_asset: str,
    expected_sender: str,
    expected_recipient: str,
    expected_amount: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    asset_transfers: list[dict[str, Any]] = []
    foreign_informational_count = 0
    for ev in events:
        emitter_id = str(ev.get("emitter_id") or "").strip()
        if not emitter_id:
            return {
                "allowed": False,
                "reason": "X402_STELLAR_EVENT_MISSING_EMITTER_ID",
                "foreign_informational_count": foreign_informational_count,
            }
        topic = str(ev.get("topic") or "").strip().lower()
        if emitter_id != requirements_asset:
            foreign_informational_count += 1
            continue
        if topic in {"mint", "burn", "clawback"}:
            return {
                "allowed": False,
                "reason": "X402_STELLAR_ASSET_FORBIDDEN_SUPPLY_OR_CLAWBACK_EVENT",
                "foreign_informational_count": foreign_informational_count,
            }
        if topic == "transfer":
            asset_transfers.append(ev)
        else:
            return {
                "allowed": False,
                "reason": "X402_STELLAR_ASSET_UNEXPECTED_EVENT_TOPIC",
                "foreign_informational_count": foreign_informational_count,
            }

    if len(asset_transfers) != 1:
        return {
            "allowed": False,
            "reason": "X402_STELLAR_ASSET_TRANSFER_INVARIANT_VIOLATION",
            "foreign_informational_count": foreign_informational_count,
        }
    tx = asset_transfers[0]
    if (
        tx.get("sender") != expected_sender
        or tx.get("recipient") != expected_recipient
        or int(tx.get("amount", -1)) != expected_amount
    ):
        return {
            "allowed": False,
            "reason": "X402_STELLAR_ASSET_TRANSFER_MISMATCH",
            "foreign_informational_count": foreign_informational_count,
        }
    return {
        "allowed": True,
        "reason": "OK",
        "foreign_informational_count": foreign_informational_count,
    }


# 3. JS-03: x402 #3400 TypeScript HTTPFacilitatorClient & Bazaar tiered streaming response-body caps
def evaluate_x402_facilitator_tiered_body_limit_guard(
    *,
    endpoint_kind: str,
    chunks_byte_lengths: list[int],
) -> dict[str, Any]:
    control_plane_limit = 1 * 1024 * 1024  # 1 MiB
    bazaar_limit = 4 * 1024 * 1024  # 4 MiB
    if endpoint_kind in {"verify", "settle", "supported"}:
        tier_limit = control_plane_limit
    elif endpoint_kind == "bazaar":
        tier_limit = bazaar_limit
    else:
        return {
            "allowed": False,
            "reason": "X402_FACILITATOR_UNKNOWN_ENDPOINT_KIND",
            "tier_limit_bytes": 0,
            "bytes_read_before_cancel": 0,
        }

    accumulated = 0
    for chunk_len in chunks_byte_lengths:
        if chunk_len < 0:
            return {
                "allowed": False,
                "reason": "X402_FACILITATOR_NEGATIVE_CHUNK_SIZE",
                "tier_limit_bytes": tier_limit,
                "bytes_read_before_cancel": accumulated,
            }
        accumulated += chunk_len
        if accumulated > tier_limit:
            return {
                "allowed": False,
                "reason": "X402_FACILITATOR_RESPONSE_BODY_LIMIT_EXCEEDED",
                "tier_limit_bytes": tier_limit,
                "bytes_read_before_cancel": accumulated,
            }
    return {
        "allowed": True,
        "reason": "OK",
        "tier_limit_bytes": tier_limit,
        "bytes_read_before_cancel": accumulated,
    }


# 4. JS-04: x402 #3410/#3409/#3408 90s default facilitator timeout & extra.minDeposit spend-cap clamping
def evaluate_x402_min_deposit_and_facilitator_timeout_guard(
    *,
    amount_atomic: int,
    server_min_deposit_hint: int | None,
    enforce_min_deposit: bool,
    spend_cap_per_payment: int | None,
    deposit_multiplier: int = 10,
    configured_timeout_seconds: int | None = None,
    is_legacy_30s_default: bool = False,
) -> dict[str, Any]:
    effective_timeout = 90 if configured_timeout_seconds is None else configured_timeout_seconds
    if is_legacy_30s_default or effective_timeout < 90:
        return {
            "allowed": False,
            "reason": "X402_FACILITATOR_SETTLE_TIMEOUT_TOO_SHORT",
            "effective_timeout_seconds": effective_timeout,
            "sized_deposit_atomic": 0,
        }
    base_deposit = (
        server_min_deposit_hint
        if (server_min_deposit_hint is not None and server_min_deposit_hint > 0)
        else amount_atomic * deposit_multiplier
    )
    sized_deposit = max(base_deposit, amount_atomic)
    if spend_cap_per_payment is not None:
        if amount_atomic > spend_cap_per_payment:
            return {
                "allowed": False,
                "reason": "X402_AMOUNT_EXCEEDS_MAX_AMOUNT_PER_PAYMENT",
                "effective_timeout_seconds": effective_timeout,
                "sized_deposit_atomic": 0,
            }
        max_deposit = spend_cap_per_payment * deposit_multiplier
        sized_deposit = min(sized_deposit, max_deposit)
    if (
        enforce_min_deposit
        and server_min_deposit_hint is not None
        and sized_deposit < server_min_deposit_hint
    ):
        return {
            "allowed": False,
            "reason": "X402_MIN_DEPOSIT_EXCEEDS_CLAMPED_SPEND_CAP",
            "effective_timeout_seconds": effective_timeout,
            "sized_deposit_atomic": sized_deposit,
        }
    return {
        "allowed": True,
        "reason": "OK",
        "effective_timeout_seconds": effective_timeout,
        "sized_deposit_atomic": sized_deposit,
    }


# 5. JS-05: UCP #973 Commercial influence provenance continuity across commerce stages
def evaluate_ucp_commercial_influence_provenance_guard(
    *,
    stage_projections: list[dict[str, Any]],
) -> dict[str, Any]:
    required_stages = ["catalog", "offer", "cart", "checkout", "handoff"]
    if [s.get("stage") for s in stage_projections] != required_stages:
        return {
            "allowed": False,
            "reason": "UCP_COMMERCIAL_INFLUENCE_STAGE_SEQUENCE_INCOMPLETE",
        }
    baseline: dict[str, Any] | None = None
    required_keys = (
        "extension_id",
        "subject_id",
        "influencer_id",
        "asserter_id",
        "intervention_type",
        "effect",
        "reason_code",
    )
    for entry in stage_projections:
        assertion = entry.get("assertion")
        if not isinstance(assertion, dict):
            return {
                "allowed": False,
                "reason": "UCP_COMMERCIAL_INFLUENCE_ASSERTION_DROPPED",
            }
        for key in required_keys:
            if not str(assertion.get(key) or "").strip():
                return {
                    "allowed": False,
                    "reason": f"UCP_COMMERCIAL_INFLUENCE_MISSING_{key.upper()}",
                }
        if assertion["extension_id"] != "io.github.arjun2075.shopping.commercial_influence":
            return {
                "allowed": False,
                "reason": "UCP_COMMERCIAL_INFLUENCE_INVALID_EXTENSION_ID",
            }
        fingerprint = {k: assertion[k] for k in required_keys}
        if baseline is None:
            baseline = fingerprint
        elif fingerprint != baseline:
            return {
                "allowed": False,
                "reason": "UCP_COMMERCIAL_INFLUENCE_PROVENANCE_BROKEN",
            }
    return {
        "allowed": True,
        "reason": "OK",
        "subject_id": baseline["subject_id"] if baseline else "",
    }


# 6. JS-06: UCP #967 Browser-to-UCP Cart Continuation verifier-bound exchange
def evaluate_ucp_browser_cart_continuation_guard(
    *,
    native_browser_cart_id: str,
    existing_ucp_cart_id: str | None,
    resolved_ucp_cart_id: str,
    verifier_bound_proof_valid: bool,
    rebuilt_from_agent_item_list: bool,
    raw_browser_cookie_forwarded: bool,
) -> dict[str, Any]:
    if raw_browser_cookie_forwarded or rebuilt_from_agent_item_list or not verifier_bound_proof_valid:
        return {
            "allowed": False,
            "reason": "UCP_BROWSER_CART_CONTINUATION_UNVERIFIED_REBUILD_OR_COOKIE_LEAK",
        }
    if not native_browser_cart_id.strip() or not resolved_ucp_cart_id.strip():
        return {
            "allowed": False,
            "reason": "UCP_BROWSER_CART_ID_EMPTY",
        }
    if existing_ucp_cart_id is not None and resolved_ucp_cart_id != existing_ucp_cart_id:
        return {
            "allowed": False,
            "reason": "UCP_BROWSER_CART_IDENTITY_DRIFT",
        }
    return {
        "allowed": True,
        "reason": "OK",
        "resolved_ucp_cart_id": resolved_ucp_cart_id,
    }


# 7. JS-07: UCP #957 & #956 Credential-less invoice & mandate-bound sepa_debit instruments
_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")


def evaluate_ucp_invoice_and_sepa_debit_instrument_guard(
    *,
    instrument: dict[str, Any],
) -> dict[str, Any]:
    inst_type = str(instrument.get("type") or "").strip()
    if inst_type == "invoice":
        if instrument.get("credential") is not None:
            return {
                "allowed": False,
                "reason": "UCP_INVOICE_INSTRUMENT_FORBIDS_PAYMENT_CREDENTIAL",
            }
        if int(instrument.get("amount_charged_at_completion", -1)) != 0:
            return {
                "allowed": False,
                "reason": "UCP_INVOICE_INSTRUMENT_NONZERO_COMPLETION_CHARGE",
            }
        recipient = str(instrument.get("invoice_recipient") or "").strip()
        ref = str(instrument.get("po_reference") or instrument.get("vat_id") or "").strip()
        if not recipient or not ref:
            return {
                "allowed": False,
                "reason": "UCP_INVOICE_INSTRUMENT_MISSING_BILLING_METADATA",
            }
        return {"allowed": True, "reason": "OK", "instrument_type": "invoice"}

    if inst_type == "sepa_debit":
        iban = str(instrument.get("iban") or "").replace(" ", "").upper()
        holder = str(instrument.get("account_holder") or "").strip()
        mandate_hash = str(instrument.get("mandate_text_hash") or "").strip()
        mandate_accepted = instrument.get("mandate_accepted") is True
        if not _IBAN_RE.match(iban) or not holder or not mandate_hash or not mandate_accepted:
            return {
                "allowed": False,
                "reason": "UCP_SEPA_DEBIT_MANDATE_OR_IBAN_INVALID",
            }
        return {"allowed": True, "reason": "OK", "instrument_type": "sepa_debit"}

    return {
        "allowed": False,
        "reason": "UCP_INVOICE_OR_SEPA_DEBIT_INSTRUMENT_INVALID",
    }


# 8. JS-08: UCP #955 Local-currency amounts for property-collected lodging charges
def evaluate_ucp_at_property_local_currency_guard(
    *,
    booking_currency: str,
    property_local_currency: str,
    schedule_item: dict[str, Any],
    included_in_online_capture_minor: int,
) -> dict[str, Any]:
    if schedule_item.get("type") != "at_property":
        return {"allowed": False, "reason": "UCP_SCHEDULE_NOT_AT_PROPERTY"}
    if included_in_online_capture_minor != 0:
        return {
            "allowed": False,
            "reason": "UCP_AT_PROPERTY_CHARGE_CAPTURED_ONLINE",
        }
    local_amt = schedule_item.get("local_amount")
    booking_amt = schedule_item.get("booking_amount")
    if not isinstance(local_amt, dict) or not isinstance(booking_amt, dict):
        return {
            "allowed": False,
            "reason": "UCP_AT_PROPERTY_LOCAL_CURRENCY_MISMATCH",
        }
    if (
        local_amt.get("currency") != property_local_currency
        or int(local_amt.get("amount_minor", 0)) <= 0
        or booking_amt.get("currency") != booking_currency
        or int(booking_amt.get("amount_minor", 0)) <= 0
    ):
        return {
            "allowed": False,
            "reason": "UCP_AT_PROPERTY_LOCAL_CURRENCY_MISMATCH",
        }
    return {"allowed": True, "reason": "OK"}


# 9. JS-09: ACP #308 terms_digest field on AuthenticationResult to bind 3DS results to checkout terms
def compute_acp_checkout_terms_digest(checkout_terms: dict[str, Any]) -> str:
    canonical_terms = {
        "checkout_session_id": str(checkout_terms.get("checkout_session_id") or ""),
        "merchant_id": str(checkout_terms.get("merchant_id") or ""),
        "currency": str(checkout_terms.get("currency") or ""),
        "total_minor": int(checkout_terms.get("total_minor", -1)),
        "line_items": checkout_terms.get("line_items") or [],
    }
    return _canonical_sha256(canonical_terms)


def evaluate_acp_3ds_terms_digest_binding_guard(
    *,
    checkout_terms: dict[str, Any],
    authentication_result: dict[str, Any],
) -> dict[str, Any]:
    expected_digest = compute_acp_checkout_terms_digest(checkout_terms)
    provided_digest = str(authentication_result.get("terms_digest") or "").strip()
    if not provided_digest or provided_digest != expected_digest:
        return {
            "allowed": False,
            "reason": "ACP_3DS_TERMS_DIGEST_MISSING_OR_MISMATCH",
            "expected_terms_digest": expected_digest,
        }
    return {
        "allowed": True,
        "reason": "OK",
        "expected_terms_digest": expected_digest,
    }


# 10. JS-10: ACP #295 & #194 Mutating MCP checkout idempotency_key & default delivery option selection
def evaluate_acp_mcp_mutating_idempotency_and_default_delivery_guard(
    *,
    tool_name: str,
    meta: dict[str, Any],
    fulfillment_options: list[dict[str, Any]],
    selected_fulfillment_options: list[str] | None,
    totals: list[dict[str, Any]],
) -> dict[str, Any]:
    mutating_tools = {
        "create_checkout_session",
        "update_checkout_session",
        "complete_checkout_session",
        "cancel_checkout_session",
    }
    if tool_name in mutating_tools:
        idem_key = str(meta.get("idempotency_key") or "").strip()
        api_version = str(meta.get("api_version") or "").strip()
        if not idem_key or not api_version:
            return {
                "allowed": False,
                "reason": "ACP_MCP_IDEMPOTENCY_OR_DEFAULT_DELIVERY_MISSING",
            }
    if fulfillment_options:
        option_ids = {str(o.get("id") or "") for o in fulfillment_options if o.get("id")}
        if not selected_fulfillment_options or not all(
            sel in option_ids for sel in selected_fulfillment_options
        ):
            return {
                "allowed": False,
                "reason": "ACP_MCP_IDEMPOTENCY_OR_DEFAULT_DELIVERY_MISSING",
            }
        has_fulfillment_total = any(t.get("type") == "fulfillment" for t in totals)
        if not has_fulfillment_total:
            return {
                "allowed": False,
                "reason": "ACP_MCP_IDEMPOTENCY_OR_DEFAULT_DELIVERY_MISSING",
            }
    return {"allowed": True, "reason": "OK"}


# 11. JS-11: AP2 #346/#327/#374 Single-use closed Payment Mandate consumption & rail-backed PaymentReceipt
def evaluate_ap2_closed_mandate_single_use_and_receipt_guard(
    *,
    closed_mandate_hash: str,
    consumed_mandate_hashes: set[str],
    receipt: dict[str, Any],
    rail_settlement_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    if not closed_mandate_hash.strip():
        return {"allowed": False, "reason": "AP2_CLOSED_MANDATE_HASH_EMPTY"}
    if closed_mandate_hash in consumed_mandate_hashes:
        return {"allowed": False, "reason": "AP2_CLOSED_MANDATE_REPLAY_DETECTED"}

    if "result" in receipt or receipt.get("status") not in {"Success", "Error"}:
        return {"allowed": False, "reason": "AP2_RECEIPT_NON_CANONICAL_STATUS_FIELD"}
    if not receipt.get("iss") or not receipt.get("iat") or receipt.get("reference") != closed_mandate_hash:
        return {"allowed": False, "reason": "AP2_RECEIPT_MISSING_REQUIRED_CLAIMS"}

    if receipt["status"] == "Success":
        if (
            not isinstance(rail_settlement_evidence, dict)
            or rail_settlement_evidence.get("rail_settled") is not True
            or not str(rail_settlement_evidence.get("psp_confirmation_id") or "").strip()
            or bool(rail_settlement_evidence.get("is_generated_uuid_stub"))
        ):
            return {
                "allowed": False,
                "reason": "AP2_RECEIPT_SUCCESS_WITHOUT_RAIL_SETTLEMENT_EVIDENCE",
            }
    consumed_mandate_hashes.add(closed_mandate_hash)
    return {"allowed": True, "reason": "OK"}


# 12. JS-12: AP2 #320/#309/#308 (id, type) instrument binding, PSP agent_provider_pub & post-settlement token consumption
def evaluate_ap2_instrument_type_psp_key_and_token_rollback_guard(
    *,
    allowed_payment_instruments: list[dict[str, Any]],
    selected_instrument: dict[str, Any],
    agent_provider_pub_loaded: bool,
    psp_settlement_succeeded: bool,
    token_store_entry: dict[str, Any],
) -> dict[str, Any]:
    if not agent_provider_pub_loaded:
        token_store_entry["used"] = False
        return {
            "allowed": False,
            "reason": "AP2_AGENT_PROVIDER_KEY_MISSING",
            "token_marked_used": False,
        }
    sel_pair = (
        str(selected_instrument.get("id") or "").strip(),
        str(selected_instrument.get("type") or "").strip(),
    )
    allowed_pairs = {
        (str(item.get("id") or "").strip(), str(item.get("type") or "").strip())
        for item in allowed_payment_instruments
    }
    if not sel_pair[0] or not sel_pair[1] or sel_pair not in allowed_pairs:
        token_store_entry["used"] = False
        return {
            "allowed": False,
            "reason": "AP2_PAYMENT_INSTRUMENT_ID_TYPE_MISMATCH",
            "token_marked_used": False,
        }
    if not psp_settlement_succeeded:
        token_store_entry["used"] = False
        return {
            "allowed": False,
            "reason": "AP2_PSP_SETTLEMENT_FAILED_TOKEN_ROLLED_BACK",
            "token_marked_used": False,
        }
    token_store_entry["used"] = True
    return {
        "allowed": True,
        "reason": "OK",
        "token_marked_used": True,
    }


# 13. JS-13: MCP #3092/#3002/#2992 Stateless MCP SEP-2243 (-32020 HeaderMismatch) & unverified clientInfo/serverInfo isolation
def evaluate_mcp_stateless_error_codes_and_self_reported_info_guard(
    *,
    header_mismatch_detected: bool,
    proposed_error_code: int | None,
    request_meta: dict[str, Any],
    security_decision_uses_client_or_server_info: bool,
) -> dict[str, Any]:
    if security_decision_uses_client_or_server_info:
        return {
            "allowed": False,
            "reason": "MCP_SELF_REPORTED_INFO_USED_FOR_AUTH_BLOCKED",
        }
    if header_mismatch_detected:
        if proposed_error_code != -32020:
            return {
                "allowed": False,
                "reason": "MCP_SEP2243_STALE_HEADER_MISMATCH_ERROR_CODE",
            }
        return {"allowed": True, "reason": "OK", "error_code": -32020}

    if (
        not request_meta.get("io.modelcontextprotocol/protocolVersion")
        or not isinstance(request_meta.get("io.modelcontextprotocol/clientCapabilities"), dict)
    ):
        return {
            "allowed": False,
            "reason": "MCP_STATELESS_MISSING_REQUIRED_PROTOCOL_OR_CAPABILITIES",
        }
    return {"allowed": True, "reason": "OK"}


# 14. JS-14: Stripe AI #436/#432/#320 resources/templates/list sync, dot-normalized Anthropic max_tokens & per-agent spend limits
_ANTHROPIC_DEFAULT_MAX_TOKENS = {
    "claude-3.7-sonnet": 64000,
    "claude-3.5-sonnet": 8192,
    "claude-3.5-haiku": 8192,
}


def evaluate_stripe_mcp_resource_templates_and_model_spend_guard(
    *,
    resources_capability_advertised: bool,
    resource_templates_list_supported: bool,
    raw_model_id: str,
    agent_signature_valid: bool,
    tx_amount_minor: int,
    daily_spent_minor: int,
    per_tx_limit_minor: int,
    daily_limit_minor: int,
) -> dict[str, Any]:
    if resources_capability_advertised and not resource_templates_list_supported:
        return {
            "allowed": False,
            "reason": "STRIPE_MCP_RESOURCE_TEMPLATES_METHOD_NOT_FOUND_BLOCKED",
            "resolved_max_tokens": 0,
        }
    normalized_model = raw_model_id.lower().removeprefix("anthropic/")
    normalized_model = re.sub(r"-\d{8}$", "", normalized_model)
    normalized_model = re.sub(r"claude-(\d+)-(\d+)-", r"claude-\1.\2-", normalized_model)
    resolved_max_tokens = _ANTHROPIC_DEFAULT_MAX_TOKENS.get(normalized_model, 4096)
    if normalized_model in _ANTHROPIC_DEFAULT_MAX_TOKENS and resolved_max_tokens == 4096:
        return {
            "allowed": False,
            "reason": "STRIPE_ANTHROPIC_DOT_MODEL_MAX_TOKENS_FALLBACK_BUG",
            "resolved_max_tokens": resolved_max_tokens,
        }
    if not agent_signature_valid:
        return {
            "allowed": False,
            "reason": "STRIPE_AGENT_PAYMENT_SIGNATURE_MISSING_OR_INVALID",
            "resolved_max_tokens": resolved_max_tokens,
        }
    if tx_amount_minor > per_tx_limit_minor or (daily_spent_minor + tx_amount_minor) > daily_limit_minor:
        return {
            "allowed": False,
            "reason": "STRIPE_AGENT_SPEND_LIMIT_EXCEEDED",
            "resolved_max_tokens": resolved_max_tokens,
        }
    return {
        "allowed": True,
        "reason": "OK",
        "resolved_max_tokens": resolved_max_tokens,
        "resource_templates_response": {"resourceTemplates": []},
    }


# 15. JS-15: Visa TAP #16/#15/#8 Post-authentication merchant-signed transaction receipt & commit-time economic state binding
def evaluate_visa_tap_signed_receipt_and_commit_state_guard(
    *,
    tap_request_signature: str,
    commit_economic_state: dict[str, Any],
    merchant_receipt: dict[str, Any],
    treat_tap_verification_as_settlement_truth: bool,
) -> dict[str, Any]:
    if treat_tap_verification_as_settlement_truth:
        return {
            "allowed": False,
            "reason": "VISA_TAP_AUTH_CONFLATED_WITH_SETTLEMENT_TRUTH",
        }
    expected_state_hash = _canonical_sha256(commit_economic_state)
    if (
        not tap_request_signature.strip()
        or merchant_receipt.get("tap_request_signature") != tap_request_signature
        or merchant_receipt.get("commit_state_hash") != expected_state_hash
        or not str(merchant_receipt.get("merchant_signature") or "").strip()
        or not int(merchant_receipt.get("timestamp", 0))
    ):
        return {
            "allowed": False,
            "reason": "VISA_TAP_UNSIGNED_RECEIPT_OR_UNBOUND_COMMIT_STATE",
        }
    return {
        "allowed": True,
        "reason": "OK",
        "commit_state_hash": expected_state_hash,
    }


# 16. JS-16: Sierra tau2-bench #559/#558/#557/#514 Thought-signature preservation, explicit seed support & order-invariant hashing
def evaluate_tau2_thought_signature_seed_and_order_invariant_guard(
    *,
    tool_call: dict[str, Any],
    provider: str,
    seed: int | None,
    litellm_drop_params: bool,
    gold_action_args: dict[str, Any],
    candidate_action_args: dict[str, Any],
    gold_payment_history: list[dict[str, Any]],
    candidate_payment_history: list[dict[str, Any]],
) -> dict[str, Any]:
    thought_sig = (tool_call.get("provider_specific_fields") or {}).get("thought_signature")
    packed_in_id = "__thought__" in str(tool_call.get("id") or "")
    if provider == "gemini" and not (thought_sig or packed_in_id):
        return {
            "allowed": False,
            "reason": "TAU2_GEMINI_THOUGHT_SIGNATURE_LOST_ON_TRANSPORT",
        }
    if seed is not None and provider == "gemini" and litellm_drop_params:
        return {
            "allowed": False,
            "reason": "TAU2_UNSUPPORTED_PROVIDER_SEED_DROPPED",
        }

    def _normalize_args(args: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in args.items():
            if isinstance(v, list):
                out[k] = sorted(v, key=lambda x: json.dumps(x, sort_keys=True))
            else:
                out[k] = v
        return out

    action_match = _normalize_args(gold_action_args) == _normalize_args(candidate_action_args)
    gold_db_hash = _canonical_sha256(
        sorted(gold_payment_history, key=lambda x: json.dumps(x, sort_keys=True))
    )
    cand_db_hash = _canonical_sha256(
        sorted(candidate_payment_history, key=lambda x: json.dumps(x, sort_keys=True))
    )
    db_match = gold_db_hash == cand_db_hash
    if not action_match or not db_match:
        return {
            "allowed": False,
            "reason": "TAU2_ACTION_OR_DB_STATE_MISMATCH",
            "action_match": action_match,
            "db_match": db_match,
        }
    return {
        "allowed": True,
        "reason": "OK",
        "action_match": True,
        "db_match": True,
        "canonical_db_hash": gold_db_hash,
    }
