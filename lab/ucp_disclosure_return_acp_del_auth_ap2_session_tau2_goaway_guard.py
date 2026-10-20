"""Stage 98 deterministic guardrails:
1. UCP `message_warning` Disclosure Contract (#267), Return Extension (#257),
   Platform-Attested `signals` (#203), and `get_product` Variant Narrowing (#195).
2. ACP Delegated Authentication 3DS Lifecycle (#93), `Error.supported_versions` (#99),
   and `PaymentHandler.display_name` / Deferred `capture_method` (#130).
3. Google AP2 HNP `SessionAuthorization` & `SpendingRuleSet` (#77) and
   A2A Micropayment Channel State Machine (#83).
4. Sierra tau2-bench `GeminiLiveProvider` Silent `GoAway` Deadline Reconnection (#461),
   Banking Multi-Card Fraud / ATM Fee / Duplicate Dispute Tie-Breaker (#382, #381, #380),
   and `to_litellm_messages` User Tool-Call Preservation (#361).
"""

from __future__ import annotations

import re
from typing import Any

_DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_ucp_disclosure_return_signals_and_get_product_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PRs #267, #257, #203, and #195."""
    violations: list[str] = []

    # 1. UCP #267: warning presentation="disclosure" contract & warning-only image_url/url
    messages = payload.get("messages", [])
    platform_supports_disclosure = bool(
        payload.get("platform_supports_disclosure_rendering", True)
    )
    platform_dismissed_disclosure = bool(
        payload.get("platform_dismissed_or_hidden_disclosure", False)
    )
    escalated_via_continue_url = bool(payload.get("escalated_via_continue_url", False))
    continue_url = str(payload.get("continue_url", ""))

    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            violations.append(f"ucp_message_not_object:{idx}")
            continue
        mtype = str(msg.get("type", ""))
        if mtype != "warning" and ("image_url" in msg or "url" in msg):
            violations.append(f"ucp_non_warning_message_has_image_or_url_field:{idx}")
        presentation = msg.get("presentation")
        if presentation is not None and presentation not in {"notice", "disclosure"}:
            violations.append(f"ucp_invalid_warning_presentation:{presentation}")
        if mtype == "warning" and presentation == "disclosure":
            if platform_dismissed_disclosure:
                violations.append("ucp_disclosure_warning_dismissed_or_hidden")
            if not platform_supports_disclosure:
                if not escalated_via_continue_url or not continue_url.startswith(
                    "https://"
                ):
                    violations.append(
                        "ucp_unrenderable_disclosure_missing_continue_url_escalation"
                    )

    # 2. UCP #257: dev.ucp.shopping.return extension
    return_policies = payload.get("return_policies")
    line_items = payload.get("line_items", [])
    agent_claimed_returnable_items = set(
        payload.get("agent_claimed_returnable_item_ids", [])
    )
    if isinstance(return_policies, dict):
        for pid, pol in return_policies.items():
            if not isinstance(pol, dict):
                violations.append(f"ucp_return_policy_not_object:{pid}")
                continue
            methods = pol.get("methods", [])
            for midx, method in enumerate(methods):
                if not isinstance(method, dict):
                    violations.append(f"ucp_return_method_not_object:{pid}:{midx}")
                    continue
                m_type = str(method.get("type", "")).strip()
                fee = method.get("fee")
                if not m_type or not isinstance(fee, dict):
                    violations.append(f"ucp_return_method_missing_type_or_fee:{pid}:{midx}")
                    continue
                f_type = str(fee.get("type", "")).strip()
                if not f_type:
                    violations.append(f"ucp_return_fee_missing_type:{pid}:{midx}")
                elif f_type == "fixed_fee":
                    amt = fee.get("amount")
                    if isinstance(amt, bool) or not isinstance(amt, int) or amt < 0:
                        violations.append(
                            f"ucp_return_fixed_fee_missing_or_invalid_minor_amount:{pid}:{midx}"
                        )
        for item in line_items:
            if not isinstance(item, dict):
                continue
            rp_id = item.get("return_policy_id")
            item_id = str(item.get("id", ""))
            if rp_id is not None:
                if rp_id not in return_policies:
                    violations.append(f"ucp_line_item_unknown_return_policy_id:{rp_id}")
                else:
                    pol = return_policies[rp_id]
                    resolutions = pol.get("supported_resolutions")
                    if (
                        isinstance(resolutions, list)
                        and len(resolutions) == 0
                        and item_id in agent_claimed_returnable_items
                    ):
                        violations.append(
                            f"ucp_final_sale_item_claimed_returnable:{item_id}"
                        )

    # 3. UCP #203: signals for authorization & abuse
    if "signals" in payload:
        signals_source = str(payload.get("signals_source", "platform_observed"))
        if signals_source != "platform_observed":
            violations.append(f"ucp_signals_not_platform_observed:{signals_source}")
    a2a_data_attributes = payload.get("a2a_data_attributes", [])
    if "a2a.ucp.checkout.risk_signals" in a2a_data_attributes:
        violations.append("ucp_deprecated_a2a_risk_signals_attribute_used")

    # 4. UCP #195: get_product single-resource operation & product.selected anchor
    get_product_resp = payload.get("get_product_response")
    if isinstance(get_product_resp, dict):
        if "products" in get_product_resp and "product" not in get_product_resp:
            violations.append("ucp_get_product_returned_plural_products_array")
        product = get_product_resp.get("product")
        if isinstance(product, dict):
            selected = product.get("selected", [])
            selected_map = {
                str(opt.get("name")): str(opt.get("label"))
                for opt in selected
                if isinstance(opt, dict) and opt.get("name") and opt.get("label")
            }
            for vidx, variant in enumerate(product.get("variants", [])):
                if not isinstance(variant, dict):
                    continue
                if "selected_options" in variant:
                    violations.append(
                        f"ucp_variant_uses_legacy_selected_options_field:{vidx}"
                    )
                v_opts = {
                    str(opt.get("name")): str(opt.get("label"))
                    for opt in variant.get("options", [])
                    if isinstance(opt, dict) and opt.get("name") and opt.get("label")
                }
                for s_name, s_label in selected_map.items():
                    if v_opts.get(s_name) != s_label:
                        violations.append(
                            f"ucp_get_product_variant_mismatch_selected_anchor:{vidx}:{s_name}"
                        )

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_delegated_auth_supported_versions_and_display_name_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce ACP PRs #93, #99, and #130."""
    violations: list[str] = []

    # 1. ACP #93: Delegated Authentication 3-endpoint 3DS contract
    del_auth = payload.get("delegated_authentication")
    if isinstance(del_auth, dict):
        session_id = str(del_auth.get("authentication_session_id", "")).strip()
        if not session_id:
            violations.append("acp_delegated_auth_missing_session_id")
        create_action = str(del_auth.get("create_action_type", ""))
        fingerprint_executed = bool(del_auth.get("fingerprint_executed", True))
        authenticate_called = bool(del_auth.get("authenticate_called", False))
        if (
            create_action == "fingerprint"
            and authenticate_called
            and not fingerprint_executed
        ):
            violations.append("acp_delegated_auth_authenticate_before_fingerprint")

        auth_action = str(del_auth.get("authenticate_action_type", ""))
        challenge_completed = bool(del_auth.get("challenge_completed", True))
        retrieve_called = bool(del_auth.get("retrieve_called", False))
        if (
            auth_action == "challenge"
            and retrieve_called
            and not challenge_completed
        ):
            violations.append("acp_delegated_auth_retrieve_before_challenge")

        channel_in_create = bool(del_auth.get("channel_data_in_create", True))
        channel_in_authenticate = bool(
            del_auth.get("channel_data_in_authenticate", False)
        )
        if authenticate_called and not (channel_in_create or channel_in_authenticate):
            violations.append("acp_delegated_auth_missing_channel_data")

        if bool(del_auth.get("idempotency_key_reused_with_different_params", False)):
            if int(del_auth.get("status_code", 200)) != 409:
                violations.append("acp_delegated_auth_idempotency_mismatch_not_409")

    # 2. ACP #99: Error.supported_versions on version mismatch errors
    error_obj = payload.get("error")
    if isinstance(error_obj, dict):
        code = str(error_obj.get("code", ""))
        if code in {"unsupported_api_version", "missing_api_version"}:
            supported = error_obj.get("supported_versions")
            if (
                not isinstance(supported, list)
                or len(supported) == 0
                or any(
                    not isinstance(v, str) or not _DATE_VERSION_RE.match(v)
                    for v in supported
                )
            ):
                violations.append("acp_version_error_missing_or_invalid_supported_versions")
            else:
                retry_ver = payload.get("agent_retry_api_version")
                if retry_ver is not None and retry_ver not in supported:
                    violations.append(
                        f"acp_agent_retry_version_not_in_supported_versions:{retry_ver}"
                    )

    # 3. ACP #130: PaymentHandler.display_name & deferred capture_method
    for idx, handler in enumerate(payload.get("payment_handlers", [])):
        if not isinstance(handler, dict):
            continue
        if "display_name" in handler:
            dname = handler.get("display_name")
            hname = str(handler.get("name", ""))
            if not isinstance(dname, str) or not dname.strip() or dname.strip() == hname:
                violations.append(f"acp_payment_handler_invalid_display_name:{idx}")

    payment_data = payload.get("payment_data")
    if isinstance(payment_data, dict) and "capture_method" in payment_data:
        violations.append("acp_payment_data_undeclared_capture_method_forbidden")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_hnp_session_spending_rules_and_micropayment_channel_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce Google AP2 PRs #77 and #83."""
    violations: list[str] = []

    # 1. AP2 #77: HNP IntentMandate SessionAuthorization & SpendingRuleSet
    hnp_mandate = payload.get("hnp_intent_mandate")
    if isinstance(hnp_mandate, dict):
        confirm_req = bool(hnp_mandate.get("user_cart_confirmation_required", False))
        if not confirm_req:
            sess = hnp_mandate.get("session_authorization")
            now_ts = int(payload.get("current_timestamp", 1776643200))
            if not isinstance(sess, dict):
                violations.append("ap2_hnp_missing_session_authorization")
            else:
                agent_did = str(sess.get("agent_did", ""))
                status = str(sess.get("status", ""))
                expiry_ts = int(sess.get("session_expiry_ts", 0))
                revoked = bool(sess.get("is_revoked", False))
                if not agent_did.startswith("did:"):
                    violations.append("ap2_hnp_invalid_agent_did")
                if status != "ACTIVE" or revoked or expiry_ts <= now_ts:
                    violations.append("ap2_hnp_session_expired_or_revoked")

            rules = hnp_mandate.get("spending_rules", {})
            tx = payload.get("transaction_context", {})
            if isinstance(rules, dict) and isinstance(tx, dict) and tx:
                amt = int(tx.get("amount_minor", 0))
                cum_spent = int(tx.get("cumulative_spent_minor", 0))
                max_per_tx = int(rules.get("max_per_transaction_minor", 0))
                max_total = int(rules.get("max_total_budget_minor", 0))
                if max_per_tx > 0 and amt > max_per_tx:
                    violations.append("ap2_spending_rule_per_tx_limit_exceeded")
                if max_total > 0 and (cum_spent + amt) > max_total:
                    violations.append("ap2_spending_rule_total_budget_exceeded")
                allowed_merchants = rules.get("allowed_merchants")
                if (
                    isinstance(allowed_merchants, list)
                    and allowed_merchants
                    and tx.get("merchant_id") not in allowed_merchants
                ):
                    violations.append("ap2_spending_rule_merchant_not_allowed")
                allowed_categories = rules.get("allowed_categories")
                if (
                    isinstance(allowed_categories, list)
                    and allowed_categories
                    and tx.get("category") not in allowed_categories
                ):
                    violations.append("ap2_spending_rule_category_not_allowed")
                del_depth = int(hnp_mandate.get("delegation_depth", 1))
                max_depth = int(rules.get("max_delegation_depth", 1))
                if del_depth > max_depth:
                    violations.append("ap2_spending_rule_delegation_depth_exceeded")

    # 2. AP2 #83: A2A Micropayment Channel state machine
    channel = payload.get("micropayment_channel")
    if isinstance(channel, dict):
        deposit = int(channel.get("deposit_atomic", 0))
        min_deposit = int(channel.get("min_deposit_atomic", 0))
        voucher_nonce = int(channel.get("voucher_nonce", 0))
        last_nonce = int(channel.get("last_voucher_nonce", 0))
        cum_voucher = int(channel.get("cumulative_voucher_atomic", 0))
        tokens = int(channel.get("tokens_consumed", 0))
        rate_atomic = int(channel.get("rate_per_token_atomic", 0))
        if deposit < min_deposit:
            violations.append("ap2_micropayment_deposit_below_minimum")
        if voucher_nonce <= last_nonce:
            violations.append("ap2_micropayment_voucher_nonce_not_monotonic")
        if cum_voucher > deposit:
            violations.append("ap2_micropayment_voucher_exceeds_channel_deposit")
        if rate_atomic > 0 and cum_voucher != tokens * rate_atomic:
            violations.append("ap2_micropayment_token_rate_accounting_mismatch")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Enforce Sierra tau2-bench PRs #461, #382, #381, #380, and #361."""
    violations: list[str] = []

    # 1. tau2-bench #461: GeminiLiveProvider silent GoAway deadline reconnection
    gemini_live = payload.get("gemini_live_goaway")
    if isinstance(gemini_live, dict):
        go_away_received = bool(gemini_live.get("go_away_received", False))
        deadline_elapsed = bool(gemini_live.get("reconnect_deadline_elapsed", False))
        needs_reconnection = bool(gemini_live.get("needs_reconnection", True))
        reconnection_performed = bool(gemini_live.get("reconnection_performed", True))
        if go_away_received and deadline_elapsed:
            if not needs_reconnection or not reconnection_performed:
                violations.append(
                    "tau2_gemini_silent_goaway_deadline_missed_reconnection"
                )

    # 2. tau2-bench #382: Task 082 multi-card debit fraud close_and_reissue enforcement
    disputed_cards = payload.get("disputed_debit_cards", [])
    closed_card_ids = set(payload.get("closed_debit_card_ids", []))
    replaced_card_ids = set(payload.get("replaced_debit_card_ids", []))
    for card in disputed_cards:
        if not isinstance(card, dict):
            continue
        cid = str(card.get("card_id", ""))
        reason = str(card.get("dispute_reason", ""))
        action = str(card.get("card_action", ""))
        if reason in {"card_present_fraud", "card_not_present_fraud"} or action == "close_and_reissue":
            if cid not in closed_card_ids or cid not in replaced_card_ids:
                violations.append(f"tau2_fraud_disputed_debit_card_not_closed_and_reissued:{cid}")

    # 3. tau2-bench #381: Task 074 Light Blue ATM fee net credit
    atm_fee_audit = payload.get("light_blue_atm_fee_audit")
    if isinstance(atm_fee_audit, dict):
        overcharged_cents = int(atm_fee_audit.get("free_tier_overcharged_cents", 0))
        uncharged_fee_cents = int(atm_fee_audit.get("uncharged_fee_cents", 0))
        credited_cents = int(atm_fee_audit.get("credited_cents", 0))
        expected_net = overcharged_cents - uncharged_fee_cents
        if credited_cents != expected_net:
            violations.append(
                f"tau2_light_blue_atm_fee_net_credit_mismatch:{credited_cents}!={expected_net}"
            )

    # 4. tau2-bench #380: Tasks 083/084 duplicate transaction posting_sequence tie-breaker
    dup_pair = payload.get("duplicate_transactions")
    if isinstance(dup_pair, list) and len(dup_pair) >= 2:
        seqs = [tx.get("posting_sequence") for tx in dup_pair if isinstance(tx, dict)]
        if any(not isinstance(s, int) for s in seqs) or len(set(seqs)) != len(dup_pair):
            violations.append("tau2_duplicate_transactions_missing_unique_posting_sequence")
        else:
            earliest_tx = min(
                (tx for tx in dup_pair if isinstance(tx, dict)),
                key=lambda x: int(x["posting_sequence"]),
            )
            disputed_tx_id = str(payload.get("disputed_transaction_id", ""))
            if disputed_tx_id and disputed_tx_id != str(earliest_tx.get("id", "")):
                violations.append(
                    f"tau2_duplicate_dispute_not_earliest_posting_sequence:{disputed_tx_id}"
                )

    # 5. tau2-bench #361: preserve user tool_calls in to_litellm_messages
    user_msg_conv = payload.get("user_message_litellm_conversion")
    if isinstance(user_msg_conv, dict):
        in_calls = user_msg_conv.get("input_user_tool_calls", [])
        out_calls = user_msg_conv.get("output_litellm_tool_calls", [])
        if isinstance(in_calls, list) and len(in_calls) > 0:
            if not isinstance(out_calls, list) or len(out_calls) != len(in_calls):
                violations.append("tau2_litellm_user_tool_calls_dropped")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
