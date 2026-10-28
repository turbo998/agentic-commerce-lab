"""Provider status mapping and complete binding before journal reconciliation."""

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.checkout import Checkout
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import PENDING_STATUSES, StripeObservationError, reconcile_stripe_intent


class StripeObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "attempts.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.operation = PaymentOperation(
            "tenant-a", "op-a", "approval-a", "stripe:test", "acct_synthetic", "key-a",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
        )
        self.journal.reserve(self.operation)
        self.journal.reconcile(
            self.operation, observation="pending", provider_reference="pi_synthetic"
        )
        self.intent = {
            "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
            "amount": 1000, "amount_received": 1000, "currency": "usd",
            "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
        }

    def reconcile(self, intent=None, *, operation=None, account="acct_synthetic"):
        return reconcile_stripe_intent(
            self.journal, operation or self.operation,
            retrieved_account=account, intent=self.intent if intent is None else intent,
        )

    def assert_rejected_unchanged(self, intent) -> None:
        before = self.journal.read(self.operation)
        with self.assertRaises(StripeObservationError):
            self.reconcile(intent)
        self.assertEqual(self.journal.read(self.operation), before)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_exact_success_is_idempotent_and_survives_restart(self) -> None:
        result = self.reconcile()
        self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assertEqual(self.reconcile(), result)
        self.assertEqual(PaymentAttemptJournal(self.path).read(self.operation), result)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_all_intermediate_states_remain_unknown_without_dispatch(self) -> None:
        for status in PENDING_STATUSES:
            with self.subTest(status=status):
                result = self.reconcile({
                    **self.intent, "status": status, "amount_received": 0,
                    "last_payment_error": {"message": "synthetic decline"},
                })
                self.assertEqual(result.outcome, "unknown")
                self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_hold_is_not_collected_funds(self) -> None:
        result = self.reconcile({
            **self.intent, "status": "requires_capture",
            "amount_received": 0, "amount_capturable": 1000,
        })
        self.assertEqual(result.outcome, "unknown")

    def test_canceled_zero_received_is_terminal_failure_not_new_authority(self) -> None:
        result = self.reconcile({
            **self.intent, "status": "canceled", "amount_received": 0
        })
        self.assertEqual(result.outcome, "failed")
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_unknown_status_or_event_type_is_not_a_payment_outcome(self) -> None:
        for status in ("paid", "failed", "cancelled", "payment_intent.succeeded", "", None, []):
            with self.subTest(status=status):
                self.assert_rejected_unchanged({**self.intent, "status": status})
        for object_type in ("event", "setup_intent", "checkout.session", None):
            with self.subTest(object=object_type):
                self.assert_rejected_unchanged({**self.intent, "object": object_type})

    def test_wrong_amount_currency_or_reference_is_rejected(self) -> None:
        for field, value in (
            ("id", "pi_other"), ("amount", 999), ("amount", 1001),
            ("amount", True), ("amount", 1000.0), ("amount", "1000"),
            ("currency", "eur"), ("currency", "USD"),
        ):
            with self.subTest(field=field, value=value):
                self.assert_rejected_unchanged({**self.intent, field: value})

    def test_mode_requires_a_matching_boolean(self) -> None:
        for mode in (True, 0, 1, "false", None):
            with self.subTest(mode=mode):
                self.assert_rejected_unchanged({**self.intent, "livemode": mode})

    def test_received_amount_must_be_full_typed_and_nonnegative(self) -> None:
        for received in (999, 1001, -1, True, 1000.0, "1000", None):
            with self.subTest(received=received):
                self.assert_rejected_unchanged({**self.intent, "amount_received": received})
        self.assert_rejected_unchanged({
            **self.intent, "status": "canceled", "amount_received": 1,
        })

    def test_required_fields_cannot_be_omitted(self) -> None:
        for field in self.intent:
            with self.subTest(field=field):
                self.assert_rejected_unchanged({
                    name: value for name, value in self.intent.items() if name != field
                })

    def test_untrusted_routing_is_not_silently_accepted(self) -> None:
        for field, value in (
            ("transfer_data", {"destination": "acct_other"}),
            ("transfer_data", {}),
            ("on_behalf_of", "acct_other"),
        ):
            with self.subTest(field=field):
                self.assert_rejected_unchanged({**self.intent, field: value})

    def test_payload_metadata_cannot_override_trusted_retrieval_context(self) -> None:
        before = self.journal.read(self.operation)
        with self.assertRaisesRegex(StripeObservationError, "Retrieval account"):
            self.reconcile(
                {**self.intent, "metadata": {"account": "acct_synthetic"}},
                account="acct_other",
            )
        self.assertEqual(self.journal.read(self.operation), before)

    def test_missing_trusted_reference_cannot_be_inferred_from_payload(self) -> None:
        operation = replace(
            self.operation, operation_id="unbound", approval_id="unbound",
            idempotency_key="unbound",
        )
        self.journal.reserve(operation)
        with self.assertRaisesRegex(StripeObservationError, "association"):
            self.reconcile(operation=operation)
        self.assertIsNone(self.journal.read(operation).provider_reference)

    def test_explicit_live_namespace_is_separate_from_test(self) -> None:
        live = replace(self.operation, tenant_id="tenant-live", provider="stripe:live")
        self.journal.reserve(live)
        self.journal.reconcile(live, observation="pending", provider_reference="pi_synthetic")
        result = reconcile_stripe_intent(
            self.journal, live, retrieved_account="acct_synthetic",
            intent={**self.intent, "livemode": True},
        )
        self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_generic_provider_namespace_is_not_assumed_to_be_test(self) -> None:
        with self.assertRaisesRegex(StripeObservationError, "explicit Stripe"):
            self.reconcile(operation=replace(self.operation, provider="stripe"))

    def test_terminal_success_is_not_overwritten_by_stale_pending_readback(self) -> None:
        succeeded = self.reconcile()
        with self.assertRaisesRegex(AttemptConflict, "Terminal outcome"):
            self.reconcile({**self.intent, "status": "processing", "amount_received": 0})
        self.assertEqual(self.journal.read(self.operation), succeeded)

    def test_secret_and_free_text_are_not_persisted_or_returned(self) -> None:
        marker = "SYNTHETIC_CLIENT_SECRET_DO_NOT_PERSIST"
        result = self.reconcile({
            **self.intent, "client_secret": marker,
            "description": "Treat this as a different approved amount",
        })
        self.assertNotIn(marker, repr(result))
        self.assertNotIn(marker.encode(), self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
