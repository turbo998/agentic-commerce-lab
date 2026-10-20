"""Stage 86 deterministic guardrails: UCP PropertyValue attributes & RFC 9535 message.path (#401, #397, #380),
ACP RejectedDiscount / DiscountErrorCode & Message.resolution / Error vs MessageError (#101, #100, #115),
Coinbase x402 no-wallet extension & ERC-8021 Builder Code suffix (#317, #31),
and Sierra tau2-bench buffered full-duplex audio drain & Hospitality domain policy (#363, #355).
"""

from __future__ import annotations

import re
from typing import Any


JSONPATH_ROOT_RE = re.compile(r"^\$(\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])+$")

VALID_ACP_DISCOUNT_ERROR_CODES = {
    "discount_code_expired",
    "discount_code_invalid",
    "discount_code_already_applied",
    "discount_code_combination_disallowed",
    "discount_code_minimum_not_met",
    "discount_code_user_not_logged_in",
    "discount_code_user_ineligible",
    "discount_code_usage_limit_reached",
}

VALID_ACP_MESSAGE_RESOLUTIONS = {
    "recoverable",
    "requires_buyer_input",
    "requires_buyer_review",
}

VALID_ACP_TOP_LEVEL_ERROR_TYPES = {
    "invalid_request",
    "request_not_idempotent",
    "processing_error",
    "service_unavailable",
}

ERC_8021_SCHEMA_ID = "01"
ERC_8021_MARKER = "8021000000000000000000008021"


def build_erc8021_suffix(builder_code: str) -> str:
    """Return hex-encoded ERC-8021 suffix: [builderCode UTF-8 hex][01][8021000000000000000000008021]."""
    code_hex = builder_code.encode("utf-8").hex()
    return f"{code_hex}{ERC_8021_SCHEMA_ID}{ERC_8021_MARKER}"


def validate_ucp_attribute_inheritance_and_message_path_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP PR #401 (Product/Variant PropertyValue attributes) and PRs #397/#380 (RFC 9535 message.path)."""
    violations: list[str] = []

    product_attrs = payload.get("product_attributes", [])
    variant_attrs = payload.get("variant_attributes", [])
    merged_attrs = payload.get("merged_variant_attributes", [])

    def _check_attr_list(attrs: Any, label: str) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        if not isinstance(attrs, list):
            violations.append(f"{label}_not_list")
            return indexed
        for idx, attr in enumerate(attrs):
            if not isinstance(attr, dict):
                violations.append(f"{label}_{idx}_not_object")
                continue
            name = attr.get("name")
            val = attr.get("value")
            if not isinstance(name, str) or not name.strip():
                violations.append(f"{label}_{idx}_missing_name")
                continue
            if not isinstance(val, str) or not val.strip():
                violations.append(f"{label}_{idx}_missing_value")
            num_val = attr.get("numeric_value")
            if num_val is not None and (
                isinstance(num_val, bool) or not isinstance(num_val, (int, float))
            ):
                violations.append(f"{label}_{idx}_invalid_numeric_value")
            unit = attr.get("unit")
            if unit is not None and (not isinstance(unit, str) or not unit.strip()):
                violations.append(f"{label}_{idx}_invalid_unit")
            corr_key = (
                f"key:{attr['key'].strip()}"
                if isinstance(attr.get("key"), str) and attr.get("key", "").strip()
                else f"name:{name.strip().lower()}"
            )
            indexed[corr_key] = attr
        return indexed

    prod_idx = _check_attr_list(product_attrs, "product_attributes")
    var_idx = _check_attr_list(variant_attrs, "variant_attributes")
    merged_idx = _check_attr_list(merged_attrs, "merged_variant_attributes")

    expected_merged = dict(prod_idx)
    expected_merged.update(var_idx)
    for corr_key, exp_attr in expected_merged.items():
        actual_attr = merged_idx.get(corr_key)
        if actual_attr is None:
            violations.append(f"ucp_attribute_inheritance_missing:{corr_key}")
        elif actual_attr.get("value") != exp_attr.get("value"):
            violations.append(f"ucp_attribute_override_mismatch:{corr_key}")

    messages = payload.get("messages", [])
    agent_action = payload.get("agent_recovery_action", {})
    if not isinstance(messages, list):
        violations.append("messages_not_list")
    else:
        has_unrecoverable = False
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                violations.append(f"message_{idx}_not_object")
                continue
            path = msg.get("path")
            if path is not None:
                if not isinstance(path, str) or not JSONPATH_ROOT_RE.match(path):
                    violations.append(f"message_{idx}_invalid_rfc9535_jsonpath")
                elif path.startswith("$.items["):
                    violations.append(f"message_{idx}_legacy_items_jsonpath_forbidden")
            severity = msg.get("severity")
            if severity == "unrecoverable":
                has_unrecoverable = True
            elif severity == "recoverable" and isinstance(path, str) and isinstance(agent_action, dict):
                targeted = agent_action.get("targeted_field_path")
                if targeted is not None and targeted != path:
                    violations.append("recoverable_error_remediation_path_mismatch")
        if has_unrecoverable and isinstance(agent_action, dict) and agent_action.get("auto_retry_update_checkout") is True:
            violations.append("unrecoverable_error_auto_retry_forbidden")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "UCP_ATTRIBUTE_AND_MESSAGE_PATH_VALID"
            if allowed
            else "UCP_ATTRIBUTE_OR_MESSAGE_PATH_VIOLATION"
        ),
        "violations": violations,
    }


def validate_acp_rejected_discount_and_message_resolution_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP PR #101 (RejectedDiscount/DiscountErrorCode), PR #100 (Message.resolution), and PR #115 (Error vs MessageError)."""
    violations: list[str] = []

    http_status = int(payload.get("http_status", 200))
    has_checkout_session = bool(payload.get("has_checkout_session", True))
    top_level_error = payload.get("top_level_error")
    discounts = payload.get("discounts", {})
    messages = payload.get("messages", [])
    agent_auto_retry = bool(payload.get("agent_auto_retry_or_place_order", False))

    if 200 <= http_status < 300:
        if top_level_error is not None:
            violations.append("acp_2xx_response_cannot_use_top_level_protocol_error")
        if not has_checkout_session:
            violations.append("acp_2xx_response_missing_checkout_session")
    else:
        if has_checkout_session:
            violations.append("acp_4xx_5xx_error_cannot_embed_valid_checkout_session")
        if not isinstance(top_level_error, dict):
            violations.append("acp_4xx_5xx_missing_top_level_error")
        else:
            err_type = top_level_error.get("type")
            if err_type not in VALID_ACP_TOP_LEVEL_ERROR_TYPES:
                violations.append("acp_top_level_error_invalid_type")

    if isinstance(discounts, dict):
        for idx, app in enumerate(discounts.get("applied", [])):
            if not isinstance(app, dict):
                violations.append(f"applied_discount_{idx}_not_object")
                continue
            amt = app.get("amount")
            allocs = app.get("allocations")
            if isinstance(allocs, list) and allocs:
                alloc_sum = sum(
                    int(a.get("amount", 0))
                    for a in allocs
                    if isinstance(a, dict) and isinstance(a.get("amount"), int)
                )
                if isinstance(amt, int) and alloc_sum != amt:
                    violations.append(f"applied_discount_{idx}_allocation_sum_mismatch")

        for idx, rej in enumerate(discounts.get("rejected", [])):
            if not isinstance(rej, dict):
                violations.append(f"rejected_discount_{idx}_not_object")
                continue
            code = rej.get("code")
            reason = rej.get("reason")
            if not isinstance(code, str) or not code.strip():
                violations.append(f"rejected_discount_{idx}_missing_code")
            if reason not in VALID_ACP_DISCOUNT_ERROR_CODES:
                violations.append(f"rejected_discount_{idx}_invalid_error_code")

    if isinstance(messages, list):
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                violations.append(f"acp_message_{idx}_not_object")
                continue
            resolution = msg.get("resolution")
            if resolution is not None:
                if resolution not in VALID_ACP_MESSAGE_RESOLUTIONS:
                    violations.append(f"acp_message_{idx}_invalid_resolution")
                elif resolution in {"requires_buyer_input", "requires_buyer_review"} and agent_auto_retry:
                    violations.append(
                        f"acp_message_{idx}_{resolution}_blocks_autonomous_retry_or_order"
                    )

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "ACP_DISCOUNT_AND_MESSAGE_RESOLUTION_VALID"
            if allowed
            else "ACP_DISCOUNT_OR_MESSAGE_RESOLUTION_VIOLATION"
        ),
        "violations": violations,
    }


def validate_x402_no_wallet_and_erc8021_builder_code_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 PR #317 (no-wallet extension) and PR #31 (ERC-8021 Builder Code suffix)."""
    violations: list[str] = []

    pay_req = payload.get("payment_requirements", {})
    no_wallet = payload.get("no_wallet_extension")
    client_ctx = payload.get("client_context", {})

    if isinstance(no_wallet, dict):
        info = no_wallet.get("info")
        if not isinstance(info, dict):
            violations.append("x402_no_wallet_missing_info")
        else:
            any_wallet = info.get("anyWalletWorks")
            server_locks_wallet = bool(info.get("server_locks_specific_wallet", False))
            if not isinstance(any_wallet, bool):
                violations.append("x402_no_wallet_missing_any_wallet_works")
            elif any_wallet is False and not server_locks_wallet:
                violations.append("x402_no_wallet_false_any_wallet_works_lockin")
            elif any_wallet is True and server_locks_wallet:
                violations.append("x402_no_wallet_deceptive_any_wallet_works")

            req = info.get("requires")
            if not isinstance(req, dict):
                violations.append("x402_no_wallet_missing_requires")
            else:
                for field in ("asset", "network", "amount"):
                    val = req.get(field)
                    if not isinstance(val, str) or not val.strip():
                        violations.append(f"x402_no_wallet_requires_missing_{field}")
                    elif isinstance(pay_req, dict) and field in pay_req and str(pay_req[field]) != val:
                        violations.append(f"x402_no_wallet_requires_{field}_mismatch_with_payment_requirements")

            wallets = info.get("wallets")
            if wallets is not None:
                if not isinstance(wallets, list) or len(wallets) > 8:
                    violations.append("x402_no_wallet_wallets_invalid_or_exceeds_max_8")
                else:
                    for idx, w in enumerate(wallets):
                        if not isinstance(w, dict):
                            violations.append(f"x402_no_wallet_wallet_{idx}_not_object")
                            continue
                        w_name = w.get("name")
                        w_docs = w.get("docs")
                        w_cust = w.get("custodial")
                        w_inst = w.get("install")
                        if not isinstance(w_name, str) or not (1 <= len(w_name) <= 64):
                            violations.append(f"x402_no_wallet_wallet_{idx}_invalid_name")
                        if not isinstance(w_docs, str) or not w_docs.startswith("https://"):
                            violations.append(f"x402_no_wallet_wallet_{idx}_invalid_docs_uri")
                        if not isinstance(w_cust, bool):
                            violations.append(f"x402_no_wallet_wallet_{idx}_missing_custodial_boolean")
                        if w_inst is not None and (not isinstance(w_inst, str) or len(w_inst) > 256):
                            violations.append(f"x402_no_wallet_wallet_{idx}_invalid_install")

        if isinstance(client_ctx, dict):
            if client_ctx.get("auto_execute_wallet_install") is True:
                violations.append("x402_no_wallet_untrusted_install_auto_exec_forbidden")
            has_signer = bool(client_ctx.get("has_signer", False))
            balance = int(client_ctx.get("asset_balance", 0))
            req_amt = int(
                info.get("requires", {}).get("amount", "0")
                if isinstance(info, dict) and isinstance(info.get("requires"), dict)
                and str(info.get("requires", {}).get("amount", "0")).isdigit()
                else 0
            )
            if has_signer and balance < req_amt and client_ctx.get("attempt_wallet_install") is True:
                violations.append("x402_no_wallet_funds_shortfall_cannot_be_fixed_by_wallet_install")
            if client_ctx.get("echoed_no_wallet_in_payment_payload") is True:
                violations.append("x402_no_wallet_echo_in_payment_payload_forbidden")

    erc8021 = payload.get("erc8021_settlement")
    if isinstance(erc8021, dict):
        builder_code = erc8021.get("builder_code")
        base_calldata = erc8021.get("base_calldata", "")
        tx_data = erc8021.get("tx_data", "")
        if not isinstance(base_calldata, str) or not base_calldata.startswith("0x"):
            violations.append("erc8021_invalid_base_calldata")
        elif builder_code is None or builder_code == "":
            if tx_data != base_calldata:
                violations.append("erc8021_unexpected_suffix_when_builder_code_absent")
        elif not isinstance(builder_code, str):
            violations.append("erc8021_builder_code_not_string")
        else:
            expected_tx_data = f"{base_calldata}{build_erc8021_suffix(builder_code)}"
            if tx_data != expected_tx_data:
                violations.append("erc8021_calldata_suffix_mismatch")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "X402_NO_WALLET_AND_ERC8021_VALID"
            if allowed
            else "X402_NO_WALLET_OR_ERC8021_VIOLATION"
        ),
        "violations": violations,
    }


def validate_tau2_buffered_audio_drain_and_hospitality_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench PR #363 (buffered full-duplex audio drain) and PR #355 (Hospitality domain policy)."""
    violations: list[str] = []

    duplex = payload.get("full_duplex_finalize")
    if isinstance(duplex, dict):
        buffered_bytes = int(duplex.get("buffered_audio_bytes_before_finalize", 0))
        ticks_count = int(duplex.get("ticks_count", 0))
        drained_into_last_tick = bool(duplex.get("drained_into_last_tick", False))
        buffer_cleared = bool(duplex.get("buffer_cleared_after_finalize", False))
        last_tick_contains_speech = bool(duplex.get("last_tick_contains_speech", False))

        if buffered_bytes > 0:
            if not buffer_cleared:
                violations.append("tau2_buffered_agent_audio_not_cleared")
            if ticks_count > 0:
                if not drained_into_last_tick:
                    violations.append("tau2_buffered_agent_audio_not_drained_to_final_tick")
                if not last_tick_contains_speech:
                    violations.append("tau2_final_tick_contains_speech_not_set")

    hosp = payload.get("hospitality_turn")
    if isinstance(hosp, dict):
        tool_calls_in_turn = int(hosp.get("tool_calls_in_turn", 0))
        has_guest_reply = bool(hosp.get("has_guest_reply_in_same_turn", False))
        if tool_calls_in_turn > 1:
            violations.append("tau2_hospitality_multiple_tool_calls_in_single_turn")
        if tool_calls_in_turn >= 1 and has_guest_reply:
            violations.append("tau2_hospitality_tool_call_and_guest_reply_in_same_turn")

        op = hosp.get("operation")
        if op in {"read_reservation", "modify_reservation", "cancel_reservation"}:
            if not bool(hosp.get("confirmation_number_verified", False)) or not bool(
                hosp.get("guest_name_matches_reservation", False)
            ):
                violations.append("tau2_hospitality_unverified_reservation_access")

        num_guests = int(hosp.get("num_guests_including_children", 1))
        room_capacity = int(hosp.get("room_capacity", 2))
        if num_guests > room_capacity:
            violations.append("tau2_hospitality_party_exceeds_room_capacity")

        num_rooms = int(hosp.get("num_rooms_requested", 1))
        transferred = bool(hosp.get("transferred_to_human_agents", False))
        if num_rooms > 4 and not transferred:
            violations.append("tau2_hospitality_group_booking_over_4_rooms_requires_transfer")

        rate_plan = hosp.get("rate_plan_id", "RP_FLEX")
        if op == "modify_dates" and rate_plan == "RP_SAVER":
            violations.append("tau2_hospitality_saver_rate_date_change_forbidden")
        if bool(hosp.get("cancel_and_rebook_workaround_for_saver", False)):
            violations.append("tau2_hospitality_saver_cancel_rebook_workaround_forbidden")
        if op == "cancel_reservation":
            days_before = int(hosp.get("days_before_arrival", 5))
            total_price = int(hosp.get("total_price_eur", 0))
            first_night = int(hosp.get("first_night_price_eur", 0))
            quoted_refund = int(hosp.get("quoted_refund_eur", 0))
            if rate_plan == "RP_SAVER":
                expected_refund = 0
            elif days_before >= 2:
                expected_refund = total_price
            else:
                expected_refund = max(0, total_price - first_night)
            if quoted_refund != expected_refund:
                violations.append("tau2_hospitality_cancellation_refund_calculation_mismatch")
            if not bool(hosp.get("guest_confirmed_refund_before_cancel", True)):
                violations.append("tau2_hospitality_cancel_without_guest_confirmation")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "TAU2_AUDIO_DRAIN_AND_HOSPITALITY_VALID"
            if allowed
            else "TAU2_AUDIO_DRAIN_OR_HOSPITALITY_VIOLATION"
        ),
        "violations": violations,
    }
