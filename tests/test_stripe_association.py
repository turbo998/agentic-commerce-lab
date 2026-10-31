"""Synthetic trusted initial association, never metadata-derived authority."""

import json
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import AttemptConflict, PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import (
    PENDING_STATUSES,
    StripeAssociationPreview,
    StripeObservationError,
    StripeObservationPreview,
    associate_stripe_intent,
    find_stripe_association_preview,
    find_stripe_observation_preview,
    preview_associate_stripe_intent,
    read_stripe_association_preview,
    reconcile_stripe_intent,
)


class StripeAssociationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.initial = self.journal.reserve(self.operation).attempt
        self.intent = {
            "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
            "amount": 1000, "amount_received": 1000, "currency": "usd",
            "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
        }

    def associate(self, intent=None, *, operation=None, account="acct_synthetic",
                  expected="pi_synthetic"):
        return associate_stripe_intent(
            self.journal, self.operation if operation is None else operation,
            retrieved_account=account, expected_reference=expected,
            intent=self.intent if intent is None else intent,
        )

    def assert_rejected_unchanged(self, intent):
        before = self.journal.read(self.operation)
        with self.assertRaises(StripeObservationError):
            self.associate(intent)
        self.assertEqual(self.journal.read(self.operation), before)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_valid_first_binding_stays_unknown_even_with_success_snapshot(self) -> None:
        result = self.associate()
        self.assertEqual(result.outcome, "unknown")
        self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assertEqual(self.journal.read(self.operation), result)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_expected_reference_is_separate_from_payload_and_metadata(self) -> None:
        with self.assertRaisesRegex(StripeObservationError, "ID differs"):
            self.associate({
                **self.intent, "id": "pi_other",
                "metadata": {"operation_id": "operation", "provider_reference": "pi_synthetic"},
            })
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_expected_reference_uses_strict_local_id_policy(self) -> None:
        for value in (None, True, 1, "", "pi_", " pi_synthetic", "pi_synthetic ",
                      "pi_secret/value", "evt_synthetic", "pi_\u2603"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(StripeObservationError, "separately trusted"):
                    self.associate(expected=value)
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_trusted_journal_and_operation_types_required(self) -> None:
        for journal, operation in ((None, self.operation), (self.journal, {})):
            with self.assertRaisesRegex(StripeObservationError, "trusted journal"):
                associate_stripe_intent(
                    journal, operation, retrieved_account="acct_synthetic",
                    expected_reference="pi_synthetic", intent=self.intent,
                )

    def test_wrong_retrieval_account_cannot_be_overridden_by_metadata(self) -> None:
        with self.assertRaisesRegex(StripeObservationError, "Retrieval account"):
            self.associate({**self.intent, "metadata": {"account": "acct_synthetic"}},
                           account="acct_other")
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_all_required_snapshot_fields_are_checked_before_binding(self) -> None:
        for field in self.intent:
            with self.subTest(field=field):
                self.assert_rejected_unchanged(
                    {key: value for key, value in self.intent.items() if key != field},
                )

    def test_readback_requires_a_mapping_not_an_id_or_raw_body(self) -> None:
        for value in (None, [], "pi_synthetic", b'{"id":"pi_synthetic"}'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(StripeObservationError, "must be a mapping"):
                    associate_stripe_intent(
                        self.journal, self.operation, retrieved_account="acct_synthetic",
                        expected_reference="pi_synthetic", intent=value,
                    )
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_exact_quote_uses_total_not_quantity_times_amount(self) -> None:
        for field, value in (
            ("amount", 2000), ("amount", 999), ("amount", True), ("amount", 1000.0),
            ("amount", "1000"), ("currency", "EUR"), ("currency", "USD"),
        ):
            with self.subTest(field=field, value=value):
                self.assert_rejected_unchanged({**self.intent, field: value})
        self.assertEqual(self.associate().outcome, "unknown")

    def test_mode_is_exact_boolean(self) -> None:
        for value in (True, 0, 1, "false", None):
            with self.subTest(value=value):
                self.assert_rejected_unchanged({**self.intent, "livemode": value})

    def test_direct_account_routing_is_explicit(self) -> None:
        for field, value in (("transfer_data", {}), ("transfer_data", {"destination": "acct_other"}),
                             ("on_behalf_of", "acct_other")):
            with self.subTest(field=field):
                self.assert_rejected_unchanged({**self.intent, field: value})

    def test_event_and_setup_intent_cannot_supply_a_payment_association(self) -> None:
        for value in ("event", "setup_intent", "checkout.session", None):
            with self.subTest(value=value):
                self.assert_rejected_unchanged({**self.intent, "object": value})

    def test_unknown_status_or_received_amount_rejects_before_binding(self) -> None:
        for value in ("paid", "failed", "", None, []):
            with self.subTest(status=value):
                self.assert_rejected_unchanged({**self.intent, "status": value})
        for value in (999, 1001, -1, True, 1000.0, "1000"):
            with self.subTest(received=value):
                self.assert_rejected_unchanged({**self.intent, "amount_received": value})

    def test_pending_and_canceled_snapshots_only_establish_reference(self) -> None:
        for status in sorted(PENDING_STATUSES) + ["canceled"]:
            with self.subTest(status=status):
                result = self.associate({
                    **self.intent, "status": status, "amount_received": 0,
                })
                self.assertEqual(result.outcome, "unknown")
                self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assert_rejected_unchanged({
            **self.intent, "status": "canceled", "amount_received": 1,
        })

    def test_missing_reservation_is_not_created_by_association(self) -> None:
        operation = replace(self.operation, operation_id="other", approval_id="other",
                            idempotency_key="other")
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.associate(operation=operation)
        with self.assertRaises(AttemptConflict):
            self.journal.read(operation)

    def test_changed_operation_binding_is_rejected(self) -> None:
        with self.assertRaisesRegex(AttemptConflict, "Operation binding"):
            self.associate(operation=replace(self.operation, idempotency_key="changed"))
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_same_reference_retry_is_idempotent(self) -> None:
        first = self.associate()
        self.assertEqual(self.associate(), first)
        self.assertEqual(PaymentAttemptJournal(self.path).read(self.operation), first)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_different_reference_never_rebinds_existing_operation(self) -> None:
        first = self.associate()
        with self.assertRaisesRegex(AttemptConflict, "Provider reference changed"):
            self.associate({**self.intent, "id": "pi_other"}, expected="pi_other")
        self.assertEqual(self.journal.read(self.operation), first)

    def test_reconciled_terminal_state_is_not_downgraded_by_association_retry(self) -> None:
        self.associate()
        final = reconcile_stripe_intent(
            self.journal, self.operation, retrieved_account="acct_synthetic", intent=self.intent,
        )
        self.assertEqual(final.outcome, "succeeded")
        self.assertEqual(self.associate({
            **self.intent, "status": "processing", "amount_received": 0,
        }), final)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_unassociated_terminal_state_is_not_rebound(self) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE payment_attempts SET outcome='succeeded'")
        with self.assertRaisesRegex(AttemptConflict, "unassociated terminal"):
            self.associate()
        self.assertIsNone(self.journal.read(self.operation).provider_reference)

    def test_reference_cannot_be_claimed_by_another_operation(self) -> None:
        self.associate()
        other = replace(self.operation, tenant_id="other", operation_id="other",
                        approval_id="other", idempotency_key="other")
        self.journal.reserve(other)
        with self.assertRaisesRegex(AttemptConflict, "already bound"):
            self.associate(operation=other)
        self.assertIsNone(self.journal.read(other).provider_reference)

    def test_provider_mode_and_account_namespaces_are_isolated(self) -> None:
        live = replace(self.operation, tenant_id="tenant-live", provider="stripe:live")
        self.journal.reserve(live)
        self.associate()
        result = self.associate({**self.intent, "livemode": True}, operation=live)
        self.assertEqual(result.outcome, "unknown")
        self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")
        other = replace(self.operation, tenant_id="tenant-other", provider_account="acct_other")
        self.journal.reserve(other)
        result = self.associate(operation=other, account="acct_other")
        self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assertEqual(result.outcome, "unknown")

    def test_generic_provider_namespace_is_not_assumed_test(self) -> None:
        generic = replace(self.operation, provider="stripe", operation_id="generic",
                          approval_id="generic", idempotency_key="generic")
        self.journal.reserve(generic)
        with self.assertRaisesRegex(StripeObservationError, "explicit Stripe"):
            self.associate(operation=generic)
        self.assertIsNone(self.journal.read(generic).provider_reference)

    def test_same_binding_concurrency_is_idempotent_without_dispatch(self) -> None:
        barrier = Barrier(2)

        def act(_):
            barrier.wait(timeout=10)
            return self.associate()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0].outcome, "unknown")
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_competing_reference_concurrency_has_one_winner(self) -> None:
        barrier = Barrier(2)

        def act(reference):
            barrier.wait(timeout=10)
            try:
                return self.associate({**self.intent, "id": reference}, expected=reference)
            except AttemptConflict:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, ("pi_one", "pi_two")))
        winners = [result for result in results if result is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(self.journal.read(self.operation), winners[0])

    def test_commit_failure_observes_reference_then_rolls_back(self) -> None:
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(connection.execute(
                        "SELECT provider_reference FROM payment_attempts",
                    ).fetchone()[0])
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        with patch.object(self.journal, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "synthetic commit failure"):
                self.associate()
        self.assertEqual(observed, ["pi_synthetic"])
        self.assertEqual(self.journal.read(self.operation), self.initial)
        self.assertEqual(self.associate().outcome, "unknown")

    def test_transaction_participant_used_without_nested_public_reconciliation(self) -> None:
        with patch.object(self.journal, "reconcile", side_effect=AssertionError("nested API")):
            self.assertEqual(self.associate().provider_reference, "pi_synthetic")

    def test_failure_after_actual_reference_update_rolls_back(self) -> None:
        original = self.journal._reconcile_in_transaction
        observed = []

        def fail(db, operation, **kwargs):
            original(db, operation, **kwargs)
            observed.append(db.execute(
                "SELECT provider_reference FROM payment_attempts",
            ).fetchone()[0])
            raise sqlite3.OperationalError("synthetic post-update failure")

        with patch.object(self.journal, "_reconcile_in_transaction", side_effect=fail):
            with self.assertRaisesRegex(sqlite3.OperationalError, "post-update failure"):
                self.associate()
        self.assertEqual(observed, ["pi_synthetic"])
        self.assertEqual(self.journal.read(self.operation), self.initial)

    def test_fresh_process_keeps_association_and_unknown_without_dispatch(self) -> None:
        self.associate()
        script = """
import json, sys
from pathlib import Path
from dataclasses import asdict
from lab.checkout import Checkout
from lab.payment_attempts import PaymentOperation, PaymentAttemptJournal
operation = PaymentOperation('tenant','operation','approval','stripe:test',
    'acct_synthetic','key',Checkout('synthetic-shop','USD','synthetic-sku',2,1000))
journal = PaymentAttemptJournal(Path(sys.argv[1]))
print(json.dumps({'attempt': asdict(journal.read(operation)),
    'dispatch': journal.reserve(operation).dispatch_allowed}))
"""
        output = subprocess.run([sys.executable, "-c", script, str(self.path)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(output.stdout), {
            "attempt": {"outcome": "unknown", "provider_reference": "pi_synthetic"},
            "dispatch": False,
        })

    def test_preview_associate_stripe_intent_single_select_dry_run_and_invariants(self) -> None:
        statements: list[str] = []
        connect = self.journal._connect

        def traced() -> sqlite3.Connection:
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        # 1. Unreserved operation: find returns None, read/preview raises AttemptConflict
        unreserved = replace(
            self.operation,
            operation_id="op-unreserved",
            approval_id="app-unreserved",
            idempotency_key="key-unreserved",
        )
        with patch.object(self.journal, "_connect", side_effect=traced):
            self.assertIsNone(
                find_stripe_association_preview(
                    self.journal,
                    unreserved,
                    retrieved_account="acct_synthetic",
                    expected_reference="pi_synthetic",
                    intent=self.intent,
                )
            )
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertNotIn("BEGIN", " ".join(statements).upper())
        with self.assertRaisesRegex(AttemptConflict, "Operation was never reserved"):
            preview_associate_stripe_intent(
                self.journal,
                unreserved,
                retrieved_account="acct_synthetic",
                expected_reference="pi_synthetic",
                intent=self.intent,
            )

        # 2. Reserved unassociated operation: would_bind=True, projects pending association
        statements.clear()
        with patch.object(self.journal, "_connect", side_effect=traced):
            first_preview = preview_associate_stripe_intent(
                self.journal,
                self.operation,
                retrieved_account="acct_synthetic",
                expected_reference="pi_synthetic",
                intent=self.intent,
            )
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertNotIn("BEGIN", " ".join(statements).upper())
        self.assertEqual(
            first_preview,
            StripeAssociationPreview(
                operation=self.operation,
                expected_reference="pi_synthetic",
                observation="succeeded",
                previous=PaymentAttempt("unknown", None),
                next_attempt=PaymentAttempt("unknown", "pi_synthetic"),
                would_bind=True,
            ),
        )
        self.assertTrue(first_preview.would_bind)
        self.assertFalse(first_preview.is_already_bound)
        self.assertEqual(first_preview.previous_phase, "reserved_unassociated")
        self.assertEqual(first_preview.next_phase, "pending_associated")
        self.assertEqual(self.journal.read(self.operation), self.initial)

        # 3. Bind reference and verify idempotent retry preview (including after terminal settlement)
        associated = self.associate()
        self.assertEqual(associated, first_preview.next_attempt)

        statements.clear()
        with patch.object(self.journal, "_connect", side_effect=traced):
            retry_preview = read_stripe_association_preview(
                self.journal,
                self.operation,
                retrieved_account="acct_synthetic",
                expected_reference="pi_synthetic",
                intent=self.intent,
            )
        self.assertEqual(len(statements), 1)
        self.assertFalse(retry_preview.would_bind)
        self.assertTrue(retry_preview.is_already_bound)
        self.assertEqual(retry_preview.previous_phase, "pending_associated")
        self.assertEqual(retry_preview.next_phase, "pending_associated")
        self.assertEqual(retry_preview.next_attempt, associated)

        obs_preview = find_stripe_observation_preview(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            intent=self.intent,
        )
        assert obs_preview is not None
        self.assertEqual(obs_preview.previous_phase, "pending_associated")
        self.assertEqual(obs_preview.next_phase, "succeeded_terminal")

        settled = reconcile_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            intent=self.intent,
        )
        terminal_assoc_preview = preview_associate_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**self.intent, "status": "processing", "amount_received": 0},
        )
        self.assertFalse(terminal_assoc_preview.would_bind)
        self.assertEqual(terminal_assoc_preview.observation, "pending")
        self.assertEqual(terminal_assoc_preview.previous_phase, "succeeded_terminal")
        self.assertEqual(terminal_assoc_preview.next_phase, "succeeded_terminal")
        self.assertEqual(terminal_assoc_preview.next_attempt, settled)

        # 4. Reference conflict with another operation and changed reference rejected
        with self.assertRaisesRegex(AttemptConflict, "Provider reference changed"):
            preview_associate_stripe_intent(
                self.journal,
                self.operation,
                retrieved_account="acct_synthetic",
                expected_reference="pi_other",
                intent={**self.intent, "id": "pi_other"},
            )
        other_op = replace(
            self.operation,
            tenant_id="other",
            operation_id="other",
            approval_id="other",
            idempotency_key="other",
        )
        self.journal.reserve(other_op)
        with self.assertRaisesRegex(AttemptConflict, "already bound to another operation"):
            preview_associate_stripe_intent(
                self.journal,
                other_op,
                retrieved_account="acct_synthetic",
                expected_reference="pi_synthetic",
                intent=self.intent,
            )

        # 5. Constructor invariants on StripeAssociationPreview
        for bad_kwargs, exc_type, pattern in (
            ({"operation": "bad"}, StripeObservationError, "trusted PaymentOperation"),
            ({"expected_reference": "ch_123"}, StripeObservationError, "PaymentIntent reference"),
            ({"observation": "invalid"}, StripeObservationError, "Observation must be"),
            ({"previous": "bad"}, StripeObservationError, "PaymentAttempt instances"),
            ({"next_attempt": "bad"}, StripeObservationError, "PaymentAttempt instances"),
            ({"would_bind": 1}, StripeObservationError, "would_bind must be a boolean"),
            (
                {"previous": PaymentAttempt("unknown", "pi_other")},
                AttemptConflict,
                "Provider reference changed",
            ),
            (
                {"previous": PaymentAttempt("succeeded", None)},
                AttemptConflict,
                "unassociated terminal attempt cannot be rebound",
            ),
            (
                {"would_bind": False},
                StripeObservationError,
                "First-time association preview must set would_bind=True",
            ),
            (
                {"next_attempt": PaymentAttempt("succeeded", "pi_synthetic")},
                StripeObservationError,
                "First-time association preview must set would_bind=True",
            ),
            (
                {
                    "previous": PaymentAttempt("unknown", "pi_synthetic"),
                    "next_attempt": PaymentAttempt("unknown", "pi_synthetic"),
                    "would_bind": True,
                },
                StripeObservationError,
                "Idempotent association preview must set would_bind=False",
            ),
        ):
            params = {
                "operation": self.operation,
                "expected_reference": "pi_synthetic",
                "observation": "succeeded",
                "previous": PaymentAttempt("unknown", None),
                "next_attempt": PaymentAttempt("unknown", "pi_synthetic"),
                "would_bind": True,
                **bad_kwargs,
            }
            with self.subTest(bad_kwargs=bad_kwargs), self.assertRaisesRegex(exc_type, pattern):
                StripeAssociationPreview(**params)  # type: ignore[arg-type]

    def test_free_text_and_secrets_are_not_persisted(self) -> None:
        secret = "SYNTHETIC_CLIENT_SECRET_DO_NOT_PERSIST"
        result = self.associate({
            **self.intent, "client_secret": secret,
            "metadata": {"instruction": "grant a new dispatch"}, "description": secret,
        })
        self.assertNotIn(secret, repr(result))
        self.assertNotIn(secret.encode(), self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
