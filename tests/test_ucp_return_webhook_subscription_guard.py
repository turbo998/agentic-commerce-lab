"""Unit tests for Stage 38 UCP Return Policy (#966), Capability Webhooks (#938),
Purchase Options & Subscriptions (#890), Business Identity (#939), and Escalation continue_url (#912).
"""

from __future__ import annotations

import unittest

from lab.ucp_return_webhook_subscription_guard import (
    evaluate_ucp_business_identity_and_escalation_guard,
    evaluate_ucp_capability_event_webhook_guard,
    evaluate_ucp_purchase_options_subscription_payment_guard,
    evaluate_ucp_return_policy_eligibility_and_fees_guard,
)


class TestUCPReturnWebhookSubscriptionGuard(unittest.TestCase):
    def test_return_policy_eligibility_deadline_and_narrowest_wins_fees(self) -> None:
        fees = (
            {"type": "dev.ucp.shopping.fee.restocking", "basis_points": 1500, "max_amount": 5000},
            {"type": "dev.ucp.shopping.fee.restocking", "methods": ["in_store"], "amount": 0},
            {"type": "dev.ucp.shopping.fee.return_shipping", "methods": ["by_mail"], "amount": 500},
        )
        # In-store overrides restocking to 0 -> free return in store
        in_store = evaluate_ucp_return_policy_eligibility_and_fees_guard(
            eligibility={"type": "window", "duration": "P30D", "anchor": "delivered", "expires_at": "2026-11-20T00:00:00Z"},
            anchor_event_occurred=True,
            platform_computed_deadline_from_duration=False,
            selected_channel="in_store",
            guaranteed_methods=("in_store", "by_mail"),
            fees=fees,
            item_unit_price_minor=20_000,
            platform_presents_channel_as_free=True,
        )
        self.assertTrue(in_store.admitted)
        self.assertTrue(in_store.channel_is_free_return)
        self.assertEqual(in_store.resolved_channel_fees_minor["dev.ucp.shopping.fee.restocking"], 0)

        # By-mail has 15% restocking ($30) + $5 shipping -> presenting as free is blocked
        by_mail_false_free = evaluate_ucp_return_policy_eligibility_and_fees_guard(
            eligibility={"type": "window", "duration": "P30D", "anchor": "delivered"},
            anchor_event_occurred=False,
            platform_computed_deadline_from_duration=False,
            selected_channel="by_mail",
            guaranteed_methods=("in_store", "by_mail"),
            fees=fees,
            item_unit_price_minor=20_000,
            platform_presents_channel_as_free=True,
        )
        self.assertFalse(by_mail_false_free.admitted)
        self.assertEqual(by_mail_false_free.decision_code, "CHANNEL_FALSELY_PRESENTED_AS_FREE_RETURN_BLOCKED")

        # Platform computing date from duration is blocked
        computed_date = evaluate_ucp_return_policy_eligibility_and_fees_guard(
            eligibility={"type": "window", "duration": "P30D", "anchor": "delivered"},
            anchor_event_occurred=False,
            platform_computed_deadline_from_duration=True,
            selected_channel="in_store",
            guaranteed_methods=("in_store",),
            fees=fees,
            item_unit_price_minor=20_000,
            platform_presents_channel_as_free=False,
        )
        self.assertFalse(computed_date.admitted)
        self.assertEqual(computed_date.decision_code, "PLATFORM_COMPUTED_RETURN_DEADLINE_FORBIDDEN")

    def test_capability_event_webhook_thin_envelope_and_unfiltered_readback(self) -> None:
        ok = evaluate_ucp_capability_event_webhook_guard(
            capability_name="dev.ucp.common.location.lookup",
            platform_recognized_by_business=True,
            subscription_request_rfc9421_signed=True,
            webhook_url="https://platform.example.com/webhooks/ucp",
            webhook_follows_redirects=False,
            platform_requested_events=("dev.ucp.common.location.lookup:updated", "dev.ucp.common.location.lookup:removed"),
            business_supported_events=("dev.ucp.common.location.lookup:updated", "dev.ucp.common.location.lookup:removed"),
            event_type="dev.ucp.common.location.lookup:removed",
            is_broadcast_capability=True,
            payload_is_thin_event_envelope=True,
            platform_treats_thin_event_as_state_without_read=False,
            is_location_removed_event=True,
            platform_confirmed_removal_with_unfiltered_lookup=True,
            covered_signature_components=("webhook-id", "webhook-timestamp", "ucp-agent", "content-digest"),
            webhook_timestamp_Skew_seconds=12,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.decision_code, "UCP_CAPABILITY_EVENT_WEBHOOK_VERIFIED")

        filtered_delist = evaluate_ucp_capability_event_webhook_guard(
            capability_name="dev.ucp.common.location.lookup",
            platform_recognized_by_business=True,
            subscription_request_rfc9421_signed=True,
            webhook_url="https://platform.example.com/webhooks/ucp",
            webhook_follows_redirects=False,
            platform_requested_events=None,
            business_supported_events=("dev.ucp.common.location.lookup:removed",),
            event_type="dev.ucp.common.location.lookup:removed",
            is_broadcast_capability=True,
            payload_is_thin_event_envelope=True,
            platform_treats_thin_event_as_state_without_read=False,
            is_location_removed_event=True,
            platform_confirmed_removal_with_unfiltered_lookup=False,
            covered_signature_components=("webhook-id", "webhook-timestamp", "ucp-agent"),
            webhook_timestamp_Skew_seconds=5,
        )
        self.assertFalse(filtered_delist.admitted)
        self.assertEqual(filtered_delist.decision_code, "FILTERED_LOOKUP_USED_FOR_LOCATION_REMOVAL_BLOCKED")

    def test_purchase_options_open_ended_vs_amounted_instruments(self) -> None:
        # Pay in 4 / gift card pays $17 today (amount=1700), while open-ended card (amount=None) is retained at amount=0
        ok = evaluate_ucp_purchase_options_subscription_payment_guard(
            has_one_time_option=True,
            default_option_has_schedules=False,
            selected_option_has_schedules=True,
            withdrawn_subscription_replaced_by_another_subscription=False,
            subscription_disclosure_presented_or_ap2_mandate_bound=True,
            is_deferred_paid_trial=False,
            payment_terms_capability_active=False,
            today_order_total_minor=1700,
            submitted_instruments=(
                {"id": "pi_gift_today", "amount": 1700, "supports_recurring": False},
                {"id": "pi_card_recurring", "amount": None, "supports_recurring": True},
            ),
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.retained_recurring_instrument_ids, ("pi_card_recurring",))
        self.assertEqual(ok.today_instrument_allocations, {"pi_gift_today": 1700, "pi_card_recurring": 0})

        # Amounted-only submission for a subscription is blocked
        no_open_ended = evaluate_ucp_purchase_options_subscription_payment_guard(
            has_one_time_option=True,
            default_option_has_schedules=False,
            selected_option_has_schedules=True,
            withdrawn_subscription_replaced_by_another_subscription=False,
            subscription_disclosure_presented_or_ap2_mandate_bound=True,
            is_deferred_paid_trial=False,
            payment_terms_capability_active=False,
            today_order_total_minor=1700,
            submitted_instruments=(
                {"id": "pi_gift_today", "amount": 1700, "supports_recurring": False},
            ),
        )
        self.assertFalse(no_open_ended.admitted)
        self.assertEqual(no_open_ended.decision_code, "SUBSCRIPTION_MISSING_OPEN_ENDED_RECURRING_INSTRUMENT")

    def test_business_identity_and_escalation_continue_url(self) -> None:
        ok = evaluate_ucp_business_identity_and_escalation_guard(
            business_identity_in_capabilities=True,
            business_identity_conflated_with_branch_location=False,
            checkout_status="requires_escalation",
            continue_url="https://merchant.example.com/checkout/escalate/123",
        )
        self.assertTrue(ok.admitted)

        missing_url = evaluate_ucp_business_identity_and_escalation_guard(
            business_identity_in_capabilities=True,
            business_identity_conflated_with_branch_location=False,
            checkout_status="requires_escalation",
            continue_url=None,
        )
        self.assertFalse(missing_url.admitted)
        self.assertEqual(missing_url.decision_code, "ESCALATION_WITHOUT_CONTINUE_URL_BLOCKED")


if __name__ == "__main__":
    unittest.main()
