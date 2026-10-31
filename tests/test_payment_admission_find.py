"""Scoped optional first-admission history lookup, separating un-admitted from conflict."""

import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.payment_approvals import (
    ApprovalAdmission,
    PaymentApprovalError,
    PaymentApprovalStore,
)
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout"


class PaymentAdmissionFindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.operation = PaymentOperation(
            "tenant-a",
            "op-a",
            "approval-a",
            "stripe:test",
            "acct_synthetic",
            "key-a",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.approvals.approve(self.operation, expires_at=EXPIRY)

    def admit(self, operation: PaymentOperation | None = None, *, now: int = NOW):
        op = self.operation if operation is None else operation
        body = json.dumps(asdict(op.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1",
            "synthetic-key",
            MUTATION_COMPONENTS,
            "POST",
            URI,
            "application/json",
            digest,
        )
        return self.approvals.admit(
            self.journal,
            op,
            snapshot,
            clock=lambda: now,
            expected_target_uri=URI,
            method="POST",
            target_uri=URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )

    def counts(self) -> tuple[int, int]:
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("payment_attempts", "payment_admissions")
            )

    def test_unadmitted_operation_returns_none_without_creating_records(self) -> None:
        self.assertIsNone(self.approvals.find_admission(self.operation))
        self.assertEqual(self.counts(), (0, 0))
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)

    def test_legacy_pre_reserved_attempt_without_admission_row_returns_none(self) -> None:
        decision = self.journal.reserve(self.operation)
        self.assertTrue(decision.dispatch_allowed)
        self.assertIsNone(self.approvals.find_admission(self.operation))
        retry = self.admit(now=NOW + 5)
        self.assertFalse(retry.dispatch_allowed)
        self.assertIsNone(self.approvals.find_admission(self.operation))

    def test_admitted_record_survives_revocation_reopen_and_fresh_process(self) -> None:
        decision = self.admit()
        self.assertTrue(decision.dispatch_allowed)
        expected = ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY)
        self.assertEqual(self.approvals.find_admission(self.operation), expected)

        self.approvals.revoke(self.operation)
        self.assertEqual(
            PaymentApprovalStore(self.path).find_admission(self.operation),
            expected,
        )
        script = (
            "import sys; from pathlib import Path; "
            "from lab.checkout import Checkout; "
            "from lab.payment_approvals import PaymentApprovalStore; "
            "from lab.payment_attempts import PaymentOperation; "
            "op = PaymentOperation('tenant-a','op-a','approval-a','stripe:test',"
            "'acct_synthetic','key-a',Checkout('synthetic-shop','USD','synthetic-sku',2,1000)); "
            "rec = PaymentApprovalStore(Path(sys.argv[1])).find_admission(op); "
            "print(f'{rec.admitted_at}:{rec.expires_at}:{rec.fingerprint == op.fingerprint}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)],
            text=True,
        )
        self.assertEqual(out.strip(), f"{NOW}:{EXPIRY}:True")

    def test_admission_model_is_frozen(self) -> None:
        self.admit()
        rec = self.approvals.find_admission(self.operation)
        self.assertIsNotNone(rec)
        with self.assertRaises(FrozenInstanceError):
            rec.admitted_at = NOW + 1  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            rec.expires_at = EXPIRY + 1  # type: ignore[misc]

    def test_every_bound_dimension_is_verified_while_scopes_stay_isolated(self) -> None:
        self.admit()
        for field in ("approval_id", "provider", "provider_account", "idempotency_key"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.find_admission(replace(self.operation, **{field: "different"}))
        for field, value in (
            ("merchant", "other-shop"),
            ("currency", "EUR"),
            ("sku", "other-sku"),
            ("quantity", 3),
            ("amount", 2000),
        ):
            with self.subTest(field=field):
                changed_checkout = replace(self.operation.checkout, **{field: value})
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.find_admission(
                        replace(self.operation, checkout=changed_checkout)
                    )
        for field in ("tenant_id", "operation_id"):
            with self.subTest(field=field):
                self.assertIsNone(
                    self.approvals.find_admission(replace(self.operation, **{field: "different"}))
                )

    def test_invalid_operation_rejected_before_opening_connection(self) -> None:
        with patch.object(self.approvals, "_connect") as connect:
            for invalid in (None, {}, "operation", 123, self.operation.checkout):
                with self.subTest(invalid=invalid), self.assertRaises(PaymentApprovalError):
                    self.approvals.find_admission(invalid)  # type: ignore[arg-type]
            connect.assert_not_called()

    def test_rolled_back_admission_is_not_reported(self) -> None:
        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        conn = sqlite3.connect(self.path, factory=FailingCommit)
        conn.row_factory = sqlite3.Row
        with patch.object(self.approvals, "_connect", return_value=conn):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.admit()
        self.assertIsNone(self.approvals.find_admission(self.operation))
        self.assertEqual(self.counts(), (0, 0))

    def test_corrupted_persisted_times_raise_payment_approval_error(self) -> None:
        bad_path = Path(self.directory.name) / "corrupted.sqlite3"
        with closing(sqlite3.connect(bad_path)) as db, db:
            db.execute(
                """
                CREATE TABLE payment_admissions (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    admitted_at ANY,
                    expires_at ANY
                )
                """
            )
            db.execute(
                "INSERT INTO payment_admissions VALUES (?,?,?,?,?)",
                (
                    self.operation.tenant_id,
                    self.operation.operation_id,
                    self.operation.fingerprint,
                    NOW,
                    EXPIRY,
                ),
            )
        bad_store = PaymentApprovalStore(bad_path)
        for admitted_at, expires_at in (
            (NOW + 0.5, EXPIRY),
            (NOW, EXPIRY + 0.5),
            (-1, EXPIRY),
            (EXPIRY, EXPIRY),
            (EXPIRY + 1, EXPIRY),
            ("invalid-time", EXPIRY),
            (NOW, None),
        ):
            with self.subTest(admitted_at=admitted_at, expires_at=expires_at):
                with closing(sqlite3.connect(bad_path)) as db, db:
                    db.execute(
                        "UPDATE payment_admissions SET admitted_at=?, expires_at=?",
                        (admitted_at, expires_at),
                    )
                with self.assertRaisesRegex(
                    PaymentApprovalError,
                    "Stored admission times are invalid",
                ):
                    bad_store.find_admission(self.operation)

    def test_select_only_does_not_take_writer_lock(self) -> None:
        self.admit()
        statements: list[str] = []
        connect = self.approvals._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.approvals, "_connect", side_effect=traced):
            self.assertEqual(
                self.approvals.find_admission(self.operation),
                ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY),
            )
            self.assertIsNone(
                self.approvals.find_admission(
                    replace(
                        self.operation,
                        operation_id="absent",
                        approval_id="absent",
                        idempotency_key="absent",
                    )
                )
            )
        select_stmts = [stmt for stmt in statements if "FROM payment_admissions" in stmt]
        self.assertEqual(len(select_stmts), 2)
        self.assertTrue(all(stmt.startswith("SELECT ") for stmt in select_stmts))
        self.assertFalse(any("BEGIN IMMEDIATE" in stmt for stmt in statements))


if __name__ == "__main__":
    unittest.main()
