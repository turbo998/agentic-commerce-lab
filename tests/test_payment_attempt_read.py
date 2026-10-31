"""Scoped local payment-attempt state lookup, distinguishing unreserved from conflict."""

import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import (
    AttemptConflict,
    AttemptReconciliationPreview,
    AttemptReservationPreview,
    DispatchDecision,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)


class PaymentAttemptReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "attempts.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.operation = PaymentOperation(
            "tenant-a",
            "op-a",
            "approval-a",
            "stripe:test",
            "acct_synthetic",
            "key-a",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )

    def attempt_count(self) -> int:
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT count(*) FROM payment_attempts").fetchone()[0]

    def test_absent_attempt_returns_none_without_creating_records(self) -> None:
        self.assertIsNone(self.journal.read_attempt(self.operation))
        self.assertEqual(self.attempt_count(), 0)
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation)

    def test_reserved_and_reconciled_states_survive_reopen_and_fresh_process(self) -> None:
        decision = self.journal.reserve(self.operation)
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(
            self.journal.read_attempt(self.operation),
            PaymentAttempt("unknown", None),
        )
        pending = self.journal.reconcile(
            self.operation,
            observation="pending",
            provider_reference="pi_synthetic_001",
        )
        self.assertEqual(pending, PaymentAttempt("unknown", "pi_synthetic_001"))
        self.assertEqual(self.journal.read_attempt(self.operation), pending)

        succeeded = self.journal.reconcile(
            self.operation,
            observation="succeeded",
            provider_reference="pi_synthetic_001",
        )
        self.assertEqual(succeeded, PaymentAttempt("succeeded", "pi_synthetic_001"))
        self.assertEqual(
            PaymentAttemptJournal(self.path).read_attempt(self.operation),
            succeeded,
        )
        script = (
            "import sys; from pathlib import Path; "
            "from lab.checkout import Checkout; "
            "from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation; "
            "op = PaymentOperation('tenant-a','op-a','approval-a','stripe:test',"
            "'acct_synthetic','key-a',Checkout('synthetic-shop','USD','synthetic-sku',2,1000)); "
            "attempt = PaymentAttemptJournal(Path(sys.argv[1])).read_attempt(op); "
            "print(f'{attempt.outcome}:{attempt.provider_reference}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)],
            text=True,
        )
        self.assertEqual(out.strip(), "succeeded:pi_synthetic_001")

    def test_failed_outcome_is_readable_and_attempt_model_is_frozen(self) -> None:
        self.journal.reserve(self.operation)
        failed = self.journal.reconcile(
            self.operation,
            observation="failed",
            provider_reference="pi_synthetic_failed",
        )
        attempt = self.journal.read_attempt(self.operation)
        self.assertEqual(attempt, failed)
        self.assertIsNotNone(attempt)
        with self.assertRaises(FrozenInstanceError):
            attempt.outcome = "succeeded"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            attempt.provider_reference = "pi_other"  # type: ignore[misc]

    def test_every_bound_dimension_is_verified_while_scopes_stay_isolated(self) -> None:
        self.journal.reserve(self.operation)
        for field in ("approval_id", "provider", "provider_account", "idempotency_key"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(AttemptConflict, "binding changed"):
                    self.journal.read_attempt(replace(self.operation, **{field: "different"}))
        for field, value in (
            ("merchant", "other-shop"),
            ("currency", "EUR"),
            ("sku", "other-sku"),
            ("quantity", 3),
            ("amount", 2000),
        ):
            with self.subTest(field=field):
                changed_checkout = replace(self.operation.checkout, **{field: value})
                with self.assertRaisesRegex(AttemptConflict, "binding changed"):
                    self.journal.read_attempt(
                        replace(self.operation, checkout=changed_checkout)
                    )
        other_tenant = replace(
            self.operation,
            tenant_id="tenant-b",
            idempotency_key="key-b",
        )
        other_op = replace(
            self.operation,
            operation_id="op-b",
            approval_id="approval-b",
            idempotency_key="key-b",
        )
        self.assertIsNone(self.journal.read_attempt(other_tenant))
        self.assertIsNone(self.journal.read_attempt(other_op))

    def test_invalid_operation_rejected_before_opening_connection(self) -> None:
        with patch.object(self.journal, "_connect") as connect:
            for invalid in (None, {}, "operation", 123, self.operation.checkout):
                with self.subTest(invalid=invalid), self.assertRaises(AttemptConflict):
                    self.journal.read_attempt(invalid)  # type: ignore[arg-type]
            connect.assert_not_called()

    def test_rolled_back_reservation_or_reconciliation_is_not_reported(self) -> None:
        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        conn_reserve = sqlite3.connect(self.path, factory=FailingCommit)
        conn_reserve.row_factory = sqlite3.Row
        with patch.object(self.journal, "_connect", return_value=conn_reserve):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.journal.reserve(self.operation)
        self.assertIsNone(self.journal.read_attempt(self.operation))

        self.journal.reserve(self.operation)
        conn_reconcile = sqlite3.connect(self.path, factory=FailingCommit)
        conn_reconcile.row_factory = sqlite3.Row
        with patch.object(self.journal, "_connect", return_value=conn_reconcile):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.journal.reconcile(
                    self.operation,
                    observation="succeeded",
                    provider_reference="pi_synthetic_001",
                )
        self.assertEqual(
            self.journal.read_attempt(self.operation),
            PaymentAttempt("unknown", None),
        )

    def test_corrupted_persisted_row_raises_attempt_conflict(self) -> None:
        bad_path = Path(self.directory.name) / "corrupted.sqlite3"
        with closing(sqlite3.connect(bad_path)) as db, db:
            db.execute(
                """
                CREATE TABLE payment_attempts (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_account TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    outcome ANY,
                    provider_reference ANY
                )
                """
            )
            db.execute(
                "INSERT INTO payment_attempts VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    self.operation.tenant_id,
                    self.operation.operation_id,
                    self.operation.approval_id,
                    self.operation.provider,
                    self.operation.provider_account,
                    self.operation.idempotency_key,
                    self.operation.fingerprint,
                    "invalid_outcome",
                    "pi_001",
                ),
            )
        bad_journal = PaymentAttemptJournal(bad_path)
        with self.assertRaisesRegex(AttemptConflict, "Stored outcome is invalid"):
            bad_journal.read_attempt(self.operation)

        for outcome, provider_ref in (
            ("succeeded", None),
            ("failed", None),
            ("unknown", ""),
            ("unknown", "   "),
            ("succeeded", 123),
        ):
            with self.subTest(outcome=outcome, provider_ref=provider_ref):
                with closing(sqlite3.connect(bad_path)) as db, db:
                    db.execute(
                        "UPDATE payment_attempts SET outcome=?, provider_reference=?",
                        (outcome, provider_ref),
                    )
                with self.assertRaisesRegex(
                    AttemptConflict,
                    "Stored provider reference is invalid",
                ):
                    bad_journal.read_attempt(self.operation)

    def test_select_only_does_not_take_writer_lock(self) -> None:
        self.journal.reserve(self.operation)
        statements: list[str] = []
        connect = self.journal._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.journal, "_connect", side_effect=traced):
            self.assertEqual(
                self.journal.read_attempt(self.operation),
                PaymentAttempt("unknown", None),
            )
            self.assertIsNone(
                self.journal.read_attempt(
                    replace(
                        self.operation,
                        operation_id="absent",
                        approval_id="absent",
                        idempotency_key="absent",
                    )
                )
            )
        select_stmts = [stmt for stmt in statements if "FROM payment_attempts" in stmt]
        self.assertEqual(len(select_stmts), 2)
        self.assertTrue(all(stmt.startswith("SELECT ") for stmt in select_stmts))
        self.assertFalse(any("BEGIN IMMEDIATE" in stmt for stmt in statements))

    def test_attempt_phase_and_preview_dataclasses_enforce_invariants(self) -> None:
        reserved = PaymentAttempt("unknown", None)
        pending = PaymentAttempt("unknown", "pi_001")
        succeeded = PaymentAttempt("succeeded", "pi_001")
        failed = PaymentAttempt("failed", "pi_001")
        self.assertEqual(reserved.phase, "reserved_unassociated")
        self.assertFalse(reserved.is_terminal)
        self.assertEqual(pending.phase, "pending_associated")
        self.assertFalse(pending.is_terminal)
        self.assertEqual(succeeded.phase, "succeeded_terminal")
        self.assertTrue(succeeded.is_terminal)
        self.assertEqual(failed.phase, "failed_terminal")
        self.assertTrue(failed.is_terminal)

        for corrupted in (PaymentAttempt("succeeded", None), PaymentAttempt("failed", None)):
            with self.subTest(corrupted=corrupted):
                with self.assertRaisesRegex(
                    AttemptConflict, "Stored provider reference is invalid"
                ):
                    _ = corrupted.phase
                with self.assertRaisesRegex(
                    AttemptConflict, "Stored provider reference is invalid"
                ):
                    _ = corrupted.is_terminal

        with self.assertRaises(AttemptConflict):
            AttemptReservationPreview(
                operation=self.operation,
                existing_attempt=None,
                decision=DispatchDecision(reserved, False),
                would_insert=True,
            )
        with self.assertRaises(AttemptConflict):
            AttemptReservationPreview(
                operation=self.operation,
                existing_attempt=reserved,
                decision=DispatchDecision(reserved, False),
                would_insert=True,
            )
        with self.assertRaises(AttemptConflict):
            AttemptReservationPreview(
                operation=self.operation,
                existing_attempt=PaymentAttempt("succeeded", None),
                decision=DispatchDecision(PaymentAttempt("succeeded", None), False),
                would_insert=False,
            )
        with self.assertRaises(AttemptConflict):
            AttemptReconciliationPreview(
                operation=self.operation,
                observation="succeeded",
                previous_attempt=reserved,
                resulting_attempt=succeeded,
                state_changed=False,
            )
        with self.assertRaises(AttemptConflict):
            AttemptReconciliationPreview(
                operation=self.operation,
                observation="succeeded",
                previous_attempt=PaymentAttempt("succeeded", None),
                resulting_attempt=succeeded,
                state_changed=True,
            )

    def test_preview_reserve_and_preview_reconcile_are_lock_free_single_selects(self) -> None:
        statements: list[str] = []
        connect = self.journal._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.journal, "_connect", side_effect=traced):
            reserve_preview = self.journal.preview_reserve(self.operation)
            with self.assertRaisesRegex(AttemptConflict, "never reserved"):
                self.journal.preview_reconcile(
                    self.operation,
                    observation="pending",
                    provider_reference="pi_001",
                )
        self.assertIsNone(reserve_preview.existing_attempt)
        self.assertTrue(reserve_preview.would_insert)
        self.assertTrue(reserve_preview.dispatch_allowed)
        self.assertEqual(reserve_preview.phase, "reserved_unassociated")
        self.assertEqual(self.attempt_count(), 0)

        self.journal.reserve(self.operation)
        statements.clear()
        with patch.object(self.journal, "_connect", side_effect=traced):
            existing_preview = self.journal.preview_reserve(self.operation)
            pending_preview = self.journal.preview_reconcile(
                self.operation,
                observation="pending",
                provider_reference="pi_001",
            )
        self.assertEqual(existing_preview.existing_attempt, PaymentAttempt("unknown", None))
        self.assertFalse(existing_preview.would_insert)
        self.assertFalse(existing_preview.dispatch_allowed)
        self.assertEqual(existing_preview.phase, "reserved_unassociated")
        self.assertEqual(pending_preview.previous_phase, "reserved_unassociated")
        self.assertEqual(pending_preview.resulting_phase, "pending_associated")
        self.assertTrue(pending_preview.state_changed)

        select_stmts = [stmt for stmt in statements if "FROM payment_attempts" in stmt]
        self.assertEqual(len(select_stmts), 2)
        self.assertTrue(all(stmt.startswith("SELECT") for stmt in select_stmts))
        self.assertFalse(any("BEGIN IMMEDIATE" in stmt for stmt in statements))

        # Verify conflicts in preview_reserve and preview_reconcile
        with self.assertRaisesRegex(AttemptConflict, "Approval already reserved"):
            self.journal.preview_reserve(
                replace(self.operation, operation_id="op-b", idempotency_key="key-b")
            )
        with self.assertRaisesRegex(AttemptConflict, "idempotency key already bound"):
            self.journal.preview_reserve(
                replace(
                    self.operation,
                    tenant_id="tenant-b",
                    operation_id="op-b",
                    approval_id="approval-b",
                )
            )
        self.journal.reconcile(
            self.operation,
            observation="succeeded",
            provider_reference="pi_001",
        )
        same_terminal = self.journal.preview_reconcile(
            self.operation,
            observation="succeeded",
            provider_reference="pi_001",
        )
        self.assertFalse(same_terminal.state_changed)
        self.assertEqual(same_terminal.previous_phase, "succeeded_terminal")
        self.assertEqual(same_terminal.resulting_phase, "succeeded_terminal")
        with self.assertRaisesRegex(AttemptConflict, "Terminal outcome"):
            self.journal.preview_reconcile(
                self.operation,
                observation="failed",
                provider_reference="pi_001",
            )
        with self.assertRaisesRegex(AttemptConflict, "Provider reference changed"):
            self.journal.preview_reconcile(
                self.operation,
                observation="succeeded",
                provider_reference="pi_002",
            )

        other_op = replace(
            self.operation,
            operation_id="op-other",
            approval_id="approval-other",
            idempotency_key="key-other",
        )
        self.journal.reserve(other_op)
        with self.assertRaisesRegex(AttemptConflict, "reference already bound"):
            self.journal.preview_reconcile(
                other_op,
                observation="succeeded",
                provider_reference="pi_001",
            )

        # Unassociated terminal corruption fails closed across reserve and preview_reserve
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE payment_attempts SET outcome='succeeded', provider_reference=NULL "
                "WHERE tenant_id=? AND operation_id=?",
                (other_op.tenant_id, other_op.operation_id),
            )
        with self.assertRaisesRegex(
            AttemptConflict, "Stored provider reference is invalid"
        ):
            self.journal.preview_reserve(other_op)
        with self.assertRaisesRegex(
            AttemptConflict, "Stored provider reference is invalid"
        ):
            self.journal.reserve(other_op)


if __name__ == "__main__":
    unittest.main()
