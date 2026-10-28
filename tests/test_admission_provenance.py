"""Synthetic first-admission history, non-backfill and atomic failure evidence."""

import json
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.payment_approvals import ApprovalAdmission, PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot


NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout"


class AdmissionProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.approvals.approve(self.operation, expires_at=EXPIRY)

    def admit(self, operation=None, *, now=NOW):
        operation = self.operation if operation is None else operation
        body = json.dumps(asdict(operation.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", URI,
            "application/json", digest,
        )
        return self.approvals.admit(
            self.journal, operation, snapshot, clock=lambda: now,
            expected_target_uri=URI, method="POST", target_uri=URI,
            content_type="application/json", content_digest=digest,
            content_encoding=None, body=body,
        )

    def counts(self):
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                         for table in ("payment_attempts", "payment_admissions"))

    def test_first_gate_records_exact_binding_and_times(self) -> None:
        decision = self.admit()
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(self.approvals.read_admission(self.operation),
                         ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY))
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_read_model_is_frozen(self) -> None:
        self.admit()
        record = self.approvals.read_admission(self.operation)
        with self.assertRaises(FrozenInstanceError):
            record.admitted_at = NOW + 1

    def test_read_does_not_create_history_or_reservation(self) -> None:
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)
        self.assertEqual(self.counts(), (0, 0))
        with self.assertRaises(AttemptConflict):
            self.journal.read(self.operation)

    def test_approval_alone_cannot_supply_history(self) -> None:
        self.assertEqual(self.counts(), (0, 0))
        with self.assertRaises(PaymentApprovalError):
            self.approvals.read_admission(self.operation)

    def test_read_requires_a_validated_operation(self) -> None:
        for value in (None, {}, "operation"):
            with self.subTest(value=value), self.assertRaises(PaymentApprovalError):
                self.approvals.read_admission(value)

    def test_record_binds_every_full_operation_dimension(self) -> None:
        self.admit()
        for field in ("approval_id", "provider", "provider_account", "idempotency_key"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.read_admission(replace(self.operation, **{field: "different"}))
        for field, value in (("merchant", "other"), ("currency", "EUR"), ("sku", "other"),
                             ("quantity", 3), ("amount", 2000)):
            with self.subTest(field=field):
                operation = replace(
                    self.operation, checkout=replace(self.operation.checkout, **{field: value}),
                )
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.read_admission(operation)
        for field in ("tenant_id", "operation_id"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
                    self.approvals.read_admission(replace(self.operation, **{field: "different"}))

    def test_tenants_can_reuse_operation_names_without_sharing_history(self) -> None:
        other = replace(self.operation, tenant_id="other", idempotency_key="other-key")
        self.approvals.approve(other, expires_at=EXPIRY + 10)
        self.admit()
        self.admit(other, now=NOW + 1)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW)
        self.assertEqual(self.approvals.read_admission(other),
                         ApprovalAdmission(other.fingerprint, NOW + 1, EXPIRY + 10))
        self.assertEqual(self.counts(), (2, 2))

    def test_retry_does_not_replace_first_time_or_expiry(self) -> None:
        self.admit()
        for now in (NOW + 1, EXPIRY - 1):
            self.assertFalse(self.admit(now=now).dispatch_allowed)
            self.assertEqual(self.approvals.read_admission(self.operation),
                             ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY))
        self.assertEqual(self.counts(), (1, 1))

    def test_read_survives_revocation_without_readmitting(self) -> None:
        self.admit()
        self.approvals.revoke(self.operation)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()
        self.assertEqual(self.counts(), (1, 1))

    def test_read_survives_expiry_without_readmitting(self) -> None:
        self.admit(now=EXPIRY - 1)
        with self.assertRaisesRegex(PaymentApprovalError, "expired"):
            self.admit(now=EXPIRY)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, EXPIRY - 1)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_terminal_reconciliation_preserves_gate_not_payment_evidence(self) -> None:
        self.admit()
        before = self.approvals.read_admission(self.operation)
        final = self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_synthetic",
        )
        self.assertEqual(final.outcome, "succeeded")
        self.assertEqual(self.approvals.read_admission(self.operation), before)
        self.assertFalse(self.admit(now=NOW + 1).dispatch_allowed)
        self.assertEqual(self.approvals.read_admission(self.operation), before)

    def test_direct_reservation_is_never_backfilled_by_later_admission(self) -> None:
        self.assertTrue(self.journal.reserve(self.operation).dispatch_allowed)
        self.assertFalse(self.admit().dispatch_allowed)
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)
        self.assertEqual(self.counts(), (1, 0))

    def test_old_database_upgrade_adds_empty_history_not_backfill(self) -> None:
        self.journal.reserve(self.operation)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DROP TABLE payment_admissions")
        upgraded = PaymentApprovalStore(self.path)
        self.assertEqual(self.counts(), (1, 0))
        with self.assertRaises(PaymentApprovalError):
            upgraded.read_admission(self.operation)
        self.assertFalse(self.admit().dispatch_allowed)
        self.assertEqual(self.counts(), (1, 0))

    def test_terminal_legacy_attempt_is_not_rewritten_as_approved_history(self) -> None:
        self.journal.reserve(self.operation)
        self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_synthetic",
        )
        self.assertFalse(self.admit().dispatch_allowed)
        with self.assertRaises(PaymentApprovalError):
            self.approvals.read_admission(self.operation)
        self.assertEqual(self.counts(), (1, 0))

    def test_rejected_approval_creates_neither_record_nor_reservation(self) -> None:
        self.approvals.revoke(self.operation)
        with self.assertRaises(PaymentApprovalError):
            self.admit()
        self.assertEqual(self.counts(), (0, 0))

    def test_sql_failure_after_reservation_rolls_back_both(self) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""
                CREATE TRIGGER reject_admission BEFORE INSERT ON payment_admissions
                WHEN (SELECT count(*) FROM payment_attempts)=1
                BEGIN SELECT RAISE(ABORT, 'synthetic record failure'); END
            """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic record failure"):
            self.admit()
        self.assertEqual(self.counts(), (0, 0))

    def test_commit_failure_observes_both_writes_then_rolls_back(self) -> None:
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(tuple(connection.execute(
                        f"SELECT count(*) FROM {table}"
                    ).fetchone()[0] for table in ("payment_attempts", "payment_admissions")))
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        with patch.object(self.approvals, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "synthetic commit failure"):
                self.admit()
        self.assertEqual(observed, [(1, 1)])
        self.assertEqual(self.counts(), (0, 0))
        self.assertTrue(self.admit().dispatch_allowed)

    def test_separate_reader_cannot_see_either_uncommitted_write(self) -> None:
        observer = PaymentApprovalStore(self.path)
        observed = []
        db = self.approvals._connect()

        def inspect_visibility():
            observed.append(tuple(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                                  for table in ("payment_attempts", "payment_admissions")))
            with self.assertRaises(PaymentApprovalError):
                observer.read_admission(self.operation)
            with self.assertRaises(AttemptConflict):
                self.journal.read(self.operation)
            return 0

        db.create_function("inspect_visibility", 0, inspect_visibility)
        db.execute("""
            CREATE TEMP TRIGGER inspect_admission AFTER INSERT ON payment_admissions
            BEGIN SELECT inspect_visibility(); END
        """)
        with patch.object(self.approvals, "_connect", return_value=db):
            self.assertTrue(self.admit().dispatch_allowed)
        self.assertEqual(observed, [(1, 1)])
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(observer.read_admission(self.operation).admitted_at, NOW)

    def test_conflicting_orphan_record_cannot_grant_new_dispatch(self) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO payment_admissions VALUES (?,?,?,?,?)",
                       ("tenant", "operation", "other", NOW, EXPIRY))
        with self.assertRaises(sqlite3.IntegrityError):
            self.admit()
        self.assertEqual(self.counts(), (0, 1))
        with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
            self.approvals.read_admission(self.operation)

    def test_stored_noninteger_times_reject_explicitly(self) -> None:
        self.admit()
        for field in ("admitted_at", "expires_at"):
            with self.subTest(field=field):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_admissions SET {field}=?",
                        (NOW + 0.5 if field == "admitted_at" else EXPIRY + 0.5,),
                    )
                with self.assertRaisesRegex(PaymentApprovalError, "times are invalid"):
                    self.approvals.read_admission(self.operation)
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("UPDATE payment_admissions SET admitted_at=?,expires_at=?",
                               (NOW, EXPIRY))

    def test_timestamp_integer_boundaries_are_preserved(self) -> None:
        self.admit(now=0)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, 0)
        other = replace(self.operation, operation_id="max", approval_id="max", idempotency_key="max")
        self.approvals.approve(other, expires_at=2**63 - 1)
        self.admit(other, now=2**63 - 2)
        self.assertEqual(self.approvals.read_admission(other).expires_at, 2**63 - 1)

    def test_concurrent_first_admissions_have_one_record_and_one_dispatch(self) -> None:
        barrier = Barrier(2)

        def act(index):
            barrier.wait(timeout=10)
            return index, self.admit(now=NOW + index)

        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(act, range(2)))
        winners = [index for index, result in decisions if result.dispatch_allowed]
        self.assertEqual(len(winners), 1)
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW + winners[0])

    def test_reopen_keeps_record_without_new_history(self) -> None:
        self.admit()
        reopened = PaymentApprovalStore(self.path)
        self.assertEqual(reopened.read_admission(self.operation),
                         ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY))
        self.assertEqual(self.counts(), (1, 1))

    def test_fresh_process_reads_history_after_revocation(self) -> None:
        self.admit()
        self.approvals.revoke(self.operation)
        script = """
import json, sys
from pathlib import Path
from dataclasses import asdict
from lab.checkout import Checkout
from lab.payment_attempts import PaymentOperation, PaymentAttemptJournal
from lab.payment_approvals import PaymentApprovalStore
path = Path(sys.argv[1])
operation = PaymentOperation('tenant','operation','approval','stripe:test',
    'acct_synthetic','key',Checkout('synthetic-shop','USD','synthetic-sku',2,1000))
record = PaymentApprovalStore(path).read_admission(operation)
print(json.dumps({'record': asdict(record),
    'outcome': PaymentAttemptJournal(path).read(operation).outcome}))
"""
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(output.stdout), {
            "record": asdict(ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY)),
            "outcome": "unknown",
        })

    def test_record_contains_no_request_approver_or_provider_secrets(self) -> None:
        self.admit()
        with closing(self.approvals._connect()) as db:
            row = dict(db.execute("SELECT * FROM payment_admissions").fetchone())
        self.assertEqual(set(row), {
            "tenant_id", "operation_id", "fingerprint", "admitted_at", "expires_at",
        })
        self.assertNotIn("acct_synthetic", json.dumps(row))
        self.assertNotIn("synthetic-sku", json.dumps(row))
        self.assertEqual(set(asdict(self.approvals.read_admission(self.operation))),
                         {"fingerprint", "admitted_at", "expires_at"})


if __name__ == "__main__":
    unittest.main()
