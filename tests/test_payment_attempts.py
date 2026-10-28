"""Durable unknown outcomes, concurrency, and immutable payment bindings."""

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation, main


class PaymentAttemptTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "attempts.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.operation = PaymentOperation(
            "tenant-a", "op-a", "approval-a", "synthetic-psp", "account-a", "key-a",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
        )

    def test_pre_dispatch_commit_survives_restart_and_lost_ack(self) -> None:
        decision = self.journal.reserve(self.operation)
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(decision.attempt.outcome, "unknown")
        # A simulated provider may have charged; no acknowledgement is recorded.
        restarted = PaymentAttemptJournal(self.path)
        self.assertEqual(restarted.read(self.operation), decision.attempt)
        self.assertFalse(restarted.reserve(self.operation).dispatch_allowed)

    def test_crash_before_send_is_also_unknown(self) -> None:
        self.journal.reserve(self.operation)
        restarted = PaymentAttemptJournal(self.path)
        retry = restarted.reserve(self.operation)
        self.assertEqual(retry.attempt.outcome, "unknown")
        self.assertFalse(retry.dispatch_allowed)
        self.assertIsNone(retry.attempt.provider_reference)

    def test_concurrent_reservations_grant_only_one_dispatch(self) -> None:
        def reserve(_: int) -> bool:
            return PaymentAttemptJournal(self.path).reserve(self.operation).dispatch_allowed

        with ThreadPoolExecutor(max_workers=4) as pool:
            decisions = list(pool.map(reserve, range(12)))
        self.assertEqual(decisions.count(True), 1)

    def test_concurrent_operations_cannot_reuse_one_approval(self) -> None:
        def reserve(index: int) -> str:
            operation = replace(
                self.operation, operation_id=f"op-{index}", idempotency_key=f"key-{index}"
            )
            try:
                self.journal.reserve(operation)
                return "dispatch"
            except AttemptConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(reserve, range(2)))
        self.assertCountEqual(decisions, ["dispatch", "conflict"])

    def test_changed_operation_bindings_are_rejected(self) -> None:
        self.journal.reserve(self.operation)
        for field, value in (
            ("approval_id", "new-approval"), ("provider", "new-psp"),
            ("provider_account", "new-account"), ("idempotency_key", "new-key"),
            ("checkout", replace(self.operation.checkout, amount=999)),
            ("checkout", replace(self.operation.checkout, merchant="different")),
            ("checkout", replace(self.operation.checkout, currency="EUR")),
            ("checkout", replace(self.operation.checkout, sku="different")),
            ("checkout", replace(self.operation.checkout, quantity=2)),
        ):
            changed = replace(self.operation, **{field: value})
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(AttemptConflict, "binding changed"):
                    self.journal.reserve(changed)
                with self.assertRaises(AttemptConflict):
                    self.journal.read(changed)
                with self.assertRaises(AttemptConflict):
                    self.journal.reconcile(
                        changed, observation="succeeded", provider_reference="sim-pay-a"
                    )

    def test_new_operation_and_key_do_not_reuse_approval(self) -> None:
        self.journal.reserve(self.operation)
        changed = replace(self.operation, operation_id="new-op", idempotency_key="new-key")
        with self.assertRaisesRegex(AttemptConflict, "Approval already reserved"):
            self.journal.reserve(changed)

    def test_provider_key_collision_is_cross_tenant(self) -> None:
        self.journal.reserve(self.operation)
        changed = replace(self.operation, tenant_id="tenant-b", approval_id="approval-b")
        with self.assertRaisesRegex(AttemptConflict, "idempotency key already bound"):
            self.journal.reserve(changed)

    def test_provider_key_is_scoped_to_account_and_provider(self) -> None:
        self.journal.reserve(self.operation)
        for field in ("provider_account", "provider"):
            with self.subTest(field=field):
                changed = replace(
                    self.operation, tenant_id=f"tenant-{field}", **{field: "different"}
                )
                self.assertTrue(self.journal.reserve(changed).dispatch_allowed)

    def test_tenant_operation_and_approval_ids_are_isolated(self) -> None:
        self.journal.reserve(self.operation)
        other = replace(self.operation, tenant_id="tenant-b", idempotency_key="key-b")
        self.assertTrue(self.journal.reserve(other).dispatch_allowed)
        self.journal.reconcile(other, observation="succeeded", provider_reference="sim-pay-b")
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_pending_then_success_is_persistent_and_idempotent(self) -> None:
        self.journal.reserve(self.operation)
        pending = self.journal.reconcile(
            self.operation, observation="pending", provider_reference="sim-pay-a"
        )
        self.assertEqual(pending.outcome, "unknown")
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)
        succeeded = self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="sim-pay-a"
        )
        restarted = PaymentAttemptJournal(self.path)
        self.assertEqual(restarted.read(self.operation), succeeded)
        self.assertEqual(
            restarted.reconcile(
                self.operation, observation="succeeded", provider_reference="sim-pay-a"
            ), succeeded,
        )
        self.assertFalse(restarted.reserve(self.operation).dispatch_allowed)

    def test_failure_does_not_grant_another_dispatch_or_approval_use(self) -> None:
        self.journal.reserve(self.operation)
        failed = self.journal.reconcile(
            self.operation, observation="failed", provider_reference="sim-pay-a"
        )
        self.assertEqual(failed.outcome, "failed")
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)
        with self.assertRaisesRegex(AttemptConflict, "Approval already reserved"):
            self.journal.reserve(
                replace(self.operation, operation_id="retry-op", idempotency_key="retry-key")
            )

    def test_terminal_outcomes_cannot_be_overwritten(self) -> None:
        for terminal, conflicting in (("succeeded", "failed"), ("failed", "succeeded")):
            with self.subTest(terminal=terminal):
                operation = replace(
                    self.operation, operation_id=terminal,
                    approval_id=terminal, idempotency_key=terminal,
                )
                self.journal.reserve(operation)
                self.journal.reconcile(
                    operation, observation=terminal, provider_reference=terminal
                )
                for observation in (conflicting, "pending"):
                    with self.assertRaisesRegex(AttemptConflict, "Terminal outcome"):
                        self.journal.reconcile(
                            operation, observation=observation, provider_reference=terminal
                        )
                self.assertEqual(self.journal.read(operation).outcome, terminal)

    def test_concurrent_contradictory_observations_cannot_both_commit(self) -> None:
        self.journal.reserve(self.operation)

        def reconcile(outcome: str) -> str:
            try:
                self.journal.reconcile(
                    self.operation, observation=outcome, provider_reference="sim-pay-a"
                )
                return "recorded"
            except AttemptConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reconcile, ["succeeded", "failed"]))
        self.assertCountEqual(results, ["recorded", "conflict"])
        self.assertIn(self.journal.read(self.operation).outcome, ("succeeded", "failed"))

    def test_provider_reference_cannot_change(self) -> None:
        self.journal.reserve(self.operation)
        self.journal.reconcile(
            self.operation, observation="pending", provider_reference="sim-pay-a"
        )
        with self.assertRaisesRegex(AttemptConflict, "Provider reference changed"):
            self.journal.reconcile(
                self.operation, observation="succeeded", provider_reference="sim-pay-b"
            )
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_one_provider_payment_cannot_close_two_operations(self) -> None:
        self.journal.reserve(self.operation)
        other = replace(
            self.operation, operation_id="op-b", approval_id="approval-b",
            idempotency_key="key-b",
        )
        self.journal.reserve(other)
        self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="sim-pay-a"
        )
        with self.assertRaisesRegex(AttemptConflict, "reference already bound"):
            self.journal.reconcile(
                other, observation="succeeded", provider_reference="sim-pay-a"
            )
        self.assertEqual(self.journal.read(other).outcome, "unknown")

    def test_unknown_operation_readback_does_not_create_one(self) -> None:
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation)
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.reconcile(
                self.operation, observation="succeeded", provider_reference="sim-pay-a"
            )
        self.assertTrue(self.journal.reserve(self.operation).dispatch_allowed)

    def test_invalid_operation_metadata_is_explicit(self) -> None:
        for field in (
            "tenant_id", "operation_id", "approval_id", "provider",
            "provider_account", "idempotency_key",
        ):
            for value in ("", " ", None, True, 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.operation, **{field: value})
        with self.assertRaises(ValueError):
            replace(self.operation, checkout=None)

    def test_transport_errors_and_missing_reference_are_not_outcomes(self) -> None:
        self.journal.reserve(self.operation)
        for observation in ("timeout", "not_found", "unknown", "HTTP_500", "", None):
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                self.journal.reconcile(
                    self.operation, observation=observation, provider_reference="sim-pay-a"
                )
        for reference in ("", " ", None):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                self.journal.reconcile(
                    self.operation, observation="succeeded", provider_reference=reference
                )
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_demo_has_explicit_synthetic_and_recovery_boundaries(self) -> None:
        with patch("builtins.print") as output:
            main()
        result = json.loads(output.call_args.args[0])
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["real_payments"])
        self.assertFalse(result["settlement_verified"])
        self.assertTrue(result["first_dispatch_allowed"])
        self.assertFalse(result["after_restart"]["dispatch_allowed"])
        self.assertEqual(result["after_restart"]["attempt"]["outcome"], "unknown")
        self.assertEqual(result["reconciled"]["outcome"], "succeeded")


if __name__ == "__main__":
    unittest.main()
