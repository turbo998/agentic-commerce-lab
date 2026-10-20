"""Stage 72 deterministic runtime guards covering primary-source PRs across UCP, ACP,
Google AP2, and Sierra tau2-bench:

1. UCP (`Universal-Commerce-Protocol/ucp`):
   - PR `#660`: `buyer.consent` is exempt from Cart and Checkout full-replacement update
     rules; omitting `buyer.consent` on an update MUST retain the prior consent state.
   - PR `#634`: `dev.ucp.shopping.policy.return` extension on `policies[]` (`final_sale: true`
     forbids `window`, `supported_resolutions`, `methods`, and `restocking_fee`; `window`
     requires both `days > 0` and `anchor`; omitted fees mean "not stated", never "free").
   - PR `#628`: RFC 9110 `ETag` / `If-Match` conditional writes on checkout (`412 Precondition
     Failed` on mismatch, `428 Precondition Required` when missing) and `error_response`
     branch on `search_catalog` / `lookup_catalog`.
   - PR `#627` & `#625`: Authority binding accepts exact `name == authority_prefix` as well
     as `name.startswith(authority_prefix + ".")`; JWK `crv: "P-521"` in `profile.json`
     pairs exclusively with `alg: "ES512"` when `alg` is specified.
   - PR `#617`/`#606` & `#605`: `fulfillment_event` links to `fulfillment_method_id`,
     `fulfillment_option_id`, and `estimated_delivery` (`earliest <= latest`);
     `availability` supports `low_stock`, non-negative integer `quantity`, and RFC 3339
     `restock_at`.

2. ACP (`agentic-commerce-protocol/agentic-commerce-protocol`):
   - PR `#85` & `#80`: `AuthenticationMetadata` drops deprecated `channel`; `PaymentProvider`
     requires `merchant_id` and supports `"adyen"` plus `authentication_provider`.
   - PR `#73`: Delegate payment `Allowance.reason` supports `"one_time"`, `"recurring"`,
     and `"subscription"`; `"recurring"` / `"subscription"` require `billing_cycle`
     (`interval`, `interval_count`) and `amount_per_cycle`.
   - PR `#57`: `affiliate_attribution` requires `provider` and (`token` or `publisher_id`),
     is strictly write-only (never returned in `GET`, list, or webhook payloads), enforces
     write-once idempotency (`409 Conflict` on same `Idempotency-Key` with different
     payload), and rejects PII (`pii_not_allowed`).
   - PR `#54` & `#45`: `CancelSessionRequest.intent_trace` requires `reason_code`,
     `trace_summary` (`<= 500` chars), flat scalar `metadata` (no nested objects/arrays),
     and is write-only; Lodging vertical checkout validates `quote_token`.

3. Google AP2 (`google-agentic-commerce/AP2`):
   - PR `#229`: `ap2haggle/ap2/extensions/haggle/v0.1` multi-round negotiation:
     intermediate `Offer`s are unsigned, rounds/price respect `max_rounds`,
     `walk_away_price`, and merchant `cost_floor`, and accepted `NegotiationOutcome`
     carries a merchant-signed `CartMandate`.
   - PR `#228` & `#218`: Human-present `crypto-solana` (Solana Pay single-use `reference`
     pubkey binding matching `recipient`, `amount`, and `spl_mint` to `PaymentMandate`)
     and `crypto-algo` (Algorand USDC ASA transfer with `av:{token[:20]}` note binding).
   - PR `#212` & `#188`: Credentials Provider returns sanitized processor metadata +
     opaque `credential_reference` (no raw wallet credentials), verifies
     `payment_mandate_payer == token_owner`, and serializes Pydantic models via
     `.model_dump()` before storing in ADK `sqlite_session_service` state.

4. Sierra tau2-bench (`sierra-research/tau2-bench`):
   - PR `#329`: `banking_knowledge` `call_discoverable_agent_tool` gates `add_to_db` on
     `mutates_state or tool_name in read_log_allowlist` so extra KB read calls do not
     pollute `agent_discoverable_tools`.
   - PR `#322`: Retail `modify_pending_order_items` assigns each modified item the price
     and options of its own replacement variant rather than cross-contaminating variants.
   - PR `#301`: Telecom `_connect_vpn` deep-copies `default_vpn_details` so `break_vpn()`
     in one simulation does not corrupt `server_performance` across concurrent runs.
   - PR `#273` & `#264`: `Environment.set_state()` skips unknown/hallucinated tool calls
     as a no-op during replay instead of raising `ValueError`, and preserves `raw_data`
     for interleaved thinking models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


RETURN_POLICY_Forbidden_WHEN_FINAL_SALE = frozenset({
    "window",
    "supported_resolutions",
    "methods",
    "restocking_fee",
})

ALLOWED_BILLING_INTERVALS = frozenset({"day", "week", "month", "year"})


def _parse_rfc3339(ts: str) -> datetime:
    normalized = ts.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
    payload: dict[str, Any],
) -> GuardEvaluation:
    # 1. PR #660: buyer.consent exempt from Cart and Checkout full-replacement rules
    consent_update = payload.get("consent_update")
    if isinstance(consent_update, dict):
        prior_consent = consent_update.get("prior_consent")
        request_omitted_consent = bool(consent_update.get("request_omitted_consent", False))
        resulting_consent = consent_update.get("resulting_consent")
        if request_omitted_consent and prior_consent is not None and resulting_consent != prior_consent:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_buyer_consent_dropped_on_full_replacement_update",
                details={"prior_consent": prior_consent, "resulting_consent": resulting_consent},
            )

    # 2. PR #634: dev.ucp.shopping.policy.return extension rules
    return_policy = payload.get("return_policy")
    if isinstance(return_policy, dict):
        if return_policy.get("type") == "dev.ucp.shopping.policy.return":
            if return_policy.get("final_sale") is True:
                present_terms = [k for k in RETURN_POLICY_Forbidden_WHEN_FINAL_SALE if k in return_policy]
                if present_terms:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_return_policy_final_sale_with_return_terms_invalid",
                        details={"present_terms": present_terms},
                    )
            window = return_policy.get("window")
            if window is not None:
                if not isinstance(window, dict):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_return_policy_window_missing_days_or_anchor",
                        details={"window": window},
                    )
                days = window.get("days")
                anchor = window.get("anchor")
                if not isinstance(days, int) or isinstance(days, bool) or days <= 0 or not isinstance(anchor, str) or not anchor.strip():
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_return_policy_window_missing_days_or_anchor",
                        details={"window": window},
                    )
            if return_policy.get("unstated_fee_rendered_as_free") is True:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_unstated_fee_claimed_as_free",
                    details={},
                )

    # 3. PR #628: ETag / If-Match conditional writes on checkout + catalog error_response
    conditional_write = payload.get("conditional_write")
    if isinstance(conditional_write, dict):
        current_etag = conditional_write.get("current_etag")
        if_match = conditional_write.get("if_match")
        conditional_required = bool(conditional_write.get("conditional_required", False))
        applied_mutation = bool(conditional_write.get("applied_mutation", False))
        if conditional_required and not if_match and applied_mutation:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_checkout_conditional_write_etag_mismatch_or_missing",
                details={"reason": "missing_if_match_when_428_required"},
            )
        if if_match is not None and current_etag is not None and if_match != current_etag and applied_mutation:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_checkout_conditional_write_etag_mismatch_or_missing",
                details={"current_etag": current_etag, "if_match": if_match},
            )

    # 4. PR #627 & #625: Authority binding exact/prefix match & P-521/ES512 JWK pairing
    authority_binding = payload.get("authority_binding")
    if isinstance(authority_binding, dict):
        name = str(authority_binding.get("name", ""))
        authority_prefix = str(authority_binding.get("authority_prefix", ""))
        valid_binding = name == authority_prefix or name.startswith(authority_prefix + ".")
        if not valid_binding:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_authority_binding_host_mismatch",
                details={"name": name, "authority_prefix": authority_prefix},
            )

    profile_keys = payload.get("profile_keys")
    if isinstance(profile_keys, list):
        for key in profile_keys:
            if isinstance(key, dict) and key.get("crv") == "P-521":
                alg = key.get("alg")
                if alg is not None and alg != "ES512":
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_profile_p521_key_alg_mismatch",
                        details={"crv": "P-521", "alg": alg},
                    )

    # 5. PR #617 & #605: fulfillment_event delivery window & availability inventory signals
    fulfillment_event = payload.get("fulfillment_event")
    if isinstance(fulfillment_event, dict):
        est = fulfillment_event.get("estimated_delivery")
        if isinstance(est, dict):
            earliest = est.get("earliest")
            latest = est.get("latest")
            if isinstance(earliest, str) and isinstance(latest, str):
                if _parse_rfc3339(earliest) > _parse_rfc3339(latest):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_fulfillment_event_or_inventory_signal_invalid",
                        details={"earliest": earliest, "latest": latest},
                    )

    availability = payload.get("availability")
    if isinstance(availability, dict):
        qty = availability.get("quantity")
        if qty is not None and (not isinstance(qty, int) or isinstance(qty, bool) or qty < 0):
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_fulfillment_event_or_inventory_signal_invalid",
                details={"quantity": qty},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="ucp_consent_return_policy_etag_p521_and_fulfillment_verified",
        details={},
    )


def verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
    payload: dict[str, Any],
) -> GuardEvaluation:
    # 1. PR #85 & #80: AuthenticationMetadata drops channel; PaymentProvider merchant_id
    auth_meta = payload.get("authentication_metadata")
    if isinstance(auth_meta, dict) and "channel" in auth_meta:
        return GuardEvaluation(
            allowed=False,
            reason_code="acp_3ds_authentication_metadata_deprecated_channel_present",
            details={"channel": auth_meta.get("channel")},
        )

    payment_provider = payload.get("payment_provider")
    if isinstance(payment_provider, dict):
        merchant_id = payment_provider.get("merchant_id")
        if not isinstance(merchant_id, str) or not merchant_id.strip():
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_payment_provider_missing_merchant_id_or_invalid_auth_provider",
                details={"payment_provider": payment_provider},
            )

    # 2. PR #73: Delegate payment recurring / subscription Allowance requirements
    allowance = payload.get("allowance")
    if isinstance(allowance, dict):
        reason = allowance.get("reason")
        if reason not in {"one_time", "recurring", "subscription"}:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_recurring_allowance_missing_billing_cycle_or_amount_per_cycle",
                details={"reason": reason},
            )
        if reason in {"recurring", "subscription"}:
            cycle = allowance.get("billing_cycle")
            amt_per_cycle = allowance.get("amount_per_cycle")
            if (
                not isinstance(cycle, dict)
                or cycle.get("interval") not in ALLOWED_BILLING_INTERVALS
                or not isinstance(cycle.get("interval_count"), int)
                or cycle.get("interval_count", 0) <= 0
                or not isinstance(amt_per_cycle, int)
                or isinstance(amt_per_cycle, bool)
                or amt_per_cycle <= 0
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_recurring_allowance_missing_billing_cycle_or_amount_per_cycle",
                    details={"allowance": allowance},
                )

    # 3. PR #57: AffiliateAttribution write-only, token/publisher_id, idempotency & no PII
    affiliate = payload.get("affiliate_attribution")
    if isinstance(affiliate, dict):
        provider = affiliate.get("provider")
        has_id = bool(affiliate.get("token")) or bool(affiliate.get("publisher_id"))
        if not isinstance(provider, str) or not provider.strip() or not has_id:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_affiliate_attribution_missing_provider_or_claim",
                details={"affiliate_attribution": affiliate},
            )
        if affiliate.get("echoed_in_read_or_webhook") is True:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_affiliate_attribution_leaked_in_read_or_webhook",
                details={},
            )
        if affiliate.get("same_idempotency_key_different_payload") is True or affiliate.get("contains_pii") is True:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_affiliate_attribution_idempotency_conflict_or_pii",
                details={},
            )

    # 4. PR #54 & #45: CancelSessionRequest.intent_trace & Lodging quote_token
    intent_trace = payload.get("intent_trace")
    if isinstance(intent_trace, dict):
        reason_code = intent_trace.get("reason_code")
        summary = intent_trace.get("trace_summary", "")
        meta = intent_trace.get("metadata", {})
        echoed = bool(intent_trace.get("echoed_in_get_response", False))
        if not isinstance(reason_code, str) or not reason_code.strip() or len(str(summary)) > 500 or echoed:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_intent_trace_invalid_or_leaked_in_response",
                details={"intent_trace": intent_trace},
            )
        if isinstance(meta, dict):
            for k, v in meta.items():
                if isinstance(v, (dict, list)):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="acp_intent_trace_invalid_or_leaked_in_response",
                        details={"nested_metadata_key": k},
                    )

    lodging_checkout = payload.get("lodging_checkout")
    if isinstance(lodging_checkout, dict):
        if not lodging_checkout.get("quote_token_revalidated", False):
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_lodging_checkout_quote_token_not_revalidated",
                details={"lodging_checkout": lodging_checkout},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="acp_recurring_allowance_affiliate_intent_trace_and_3ds_verified",
        details={},
    )


def verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization(
    payload: dict[str, Any],
) -> GuardEvaluation:
    # 1. PR #229: AP2-Haggle real-time negotiation extension
    haggle = payload.get("haggle_negotiation")
    if isinstance(haggle, dict):
        rounds_used = int(haggle.get("rounds_used", 1))
        max_rounds = int(haggle.get("max_rounds", 5))
        final_price = float(haggle.get("final_price", 0.0))
        walk_away_price = float(haggle.get("buyer_walk_away_price", 0.0))
        cost_floor = float(haggle.get("merchant_cost_floor", 0.0))
        intermediate_offers_signed = bool(haggle.get("intermediate_offers_signed", False))
        outcome_status = haggle.get("outcome_status", "accepted")
        has_signed_cart_mandate = bool(haggle.get("outcome_has_signed_cart_mandate", True))
        if (
            rounds_used > max_rounds
            or final_price > walk_away_price
            or final_price < cost_floor
            or intermediate_offers_signed
            or (outcome_status == "accepted" and not has_signed_cart_mandate)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_haggle_negotiation_constraints_or_signed_outcome_violated",
                details={"haggle_negotiation": haggle},
            )

    # 2. PR #228 & #218: crypto-solana reference pubkey & crypto-algo av:{token[:20]} note binding
    solana_settlement = payload.get("crypto_solana_settlement")
    if isinstance(solana_settlement, dict):
        if (
            not solana_settlement.get("single_use_reference_pubkey_bound", False)
            or not solana_settlement.get("recipient_matches_mandate", False)
            or not solana_settlement.get("amount_matches_mandate", False)
            or not solana_settlement.get("spl_mint_matches_mandate", False)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_crypto_solana_or_algorand_mandate_binding_mismatch",
                details={"crypto_solana_settlement": solana_settlement},
            )

    algo_settlement = payload.get("crypto_algo_settlement")
    if isinstance(algo_settlement, dict):
        token = str(algo_settlement.get("mandate_token", ""))
        note = str(algo_settlement.get("tx_note", ""))
        expected_note = f"av:{token[:20]}"
        if (
            not token
            or note != expected_note
            or not algo_settlement.get("asa_amount_recipient_matched", False)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_crypto_solana_or_algorand_mandate_binding_mismatch",
                details={"expected_note": expected_note, "tx_note": note},
            )

    # 3. PR #212 & #188: Credential sanitization, payer==token_owner & ADK state model_dump()
    cred_binding = payload.get("credential_binding")
    if isinstance(cred_binding, dict):
        if (
            cred_binding.get("raw_wallet_credential_exposed", False)
            or not cred_binding.get("opaque_credential_reference_returned", True)
            or cred_binding.get("payment_mandate_payer") != cred_binding.get("token_owner")
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_credential_response_unsanitized_or_payer_token_mismatch",
                details={"credential_binding": cred_binding},
            )

    adk_session = payload.get("adk_session_state")
    if isinstance(adk_session, dict):
        if not adk_session.get("serialized_via_model_dump", True):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_adk_session_state_unserialized_pydantic_model",
                details={},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="ap2_haggle_solana_algorand_and_credential_sanitization_verified",
        details={},
    )


def verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
    payload: dict[str, Any],
) -> GuardEvaluation:
    # 1. PR #329: banking_knowledge call_discoverable_agent_tool read_log_allowlist
    banking_tool_log = payload.get("banking_discoverable_tool_call")
    if isinstance(banking_tool_log, dict):
        mutates_state = bool(banking_tool_log.get("mutates_state", False))
        tool_name = str(banking_tool_log.get("tool_name", ""))
        allowlist = set(banking_tool_log.get("read_log_allowlist", []))
        logged_to_db = bool(banking_tool_log.get("logged_to_db", False))
        should_log = mutates_state or (tool_name in allowlist)
        if logged_to_db != should_log:
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_banking_discoverable_tool_extra_read_logged_to_db",
                details={"tool_name": tool_name, "logged_to_db": logged_to_db, "should_log": should_log},
            )

    # 2. PR #322: Retail modify_pending_order_items per-item replacement variant price/options
    retail_modify = payload.get("retail_modify_items")
    if isinstance(retail_modify, list):
        for item in retail_modify:
            if isinstance(item, dict):
                if (
                    item.get("applied_price") != item.get("replacement_variant_price")
                    or item.get("applied_options") != item.get("replacement_variant_options")
                ):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="tau2_retail_multi_item_modification_variant_price_cross_contamination",
                        details={"item": item},
                    )

    # 3. PR #301: Telecom _connect_vpn deepcopy(default_vpn_details) isolation
    telecom_vpn = payload.get("telecom_vpn_simulation")
    if isinstance(telecom_vpn, dict):
        if (
            not telecom_vpn.get("used_deepcopy_on_default_vpn_details", True)
            or telecom_vpn.get("concurrent_sim_default_performance") != "EXCELLENT"
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_telecom_vpn_default_details_shared_reference_corruption",
                details={"telecom_vpn_simulation": telecom_vpn},
            )

    # 4. PR #273 & #264: Replay skips unknown tool calls without raising & preserves raw_data
    replay_eval = payload.get("replay_evaluation")
    if isinstance(replay_eval, dict):
        if (
            replay_eval.get("raised_on_unknown_hallucinated_tool", False)
            or not replay_eval.get("interleaved_thinking_raw_data_preserved", True)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_replay_unknown_tool_raised_or_interleaved_thinking_stripped",
                details={"replay_evaluation": replay_eval},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="tau2_banking_read_allowlist_retail_modify_vpn_and_replay_verified",
        details={},
    )
