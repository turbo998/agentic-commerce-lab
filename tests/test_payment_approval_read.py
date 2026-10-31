"""Scoped local approval-record state lookup, not live expiry or dispatch authority."""

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
    PaymentApprovalStatus,
    PaymentApprovalStore,
)
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class PaymentApprovalReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.operation = PaymentOperation(
            "tenant",
            "operation",
            "approval",
            "stripe:test",
            "acct_synthetic",
            "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )

    def admit(self, operation: PaymentOperation | None = None, *, now: int = NOW):
        target = self.operation if operation is None else operation
        body = json.dumps(asdict(target.checkout)).encode()
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
            target,
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

    def table_counts(self) -> tuple[int, int, int]:
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("payment_approvals", "payment_admissions", "payment_attempts")
            )

    def test_absent_approval_returns_none_without_creating_records(self) -> None:
        self.assertIsNone(self.approvals.read_approval(self.operation))
        self.assertEqual(self.table_counts(), (0, 0, 0))
        with self.assertRaises(PaymentApprovalError):
            self.approvals.read_admission(self.operation)
        with self.assertRaises(AttemptConflict):
            self.journal.read(self.operation)

    def test_active_status_readable_before_admission_and_survives_fresh_process(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        expected = PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active")
        self.assertEqual(self.approvals.read_approval(self.operation), expected)
        self.assertEqual(PaymentApprovalStore(self.path).read_approval(self.operation), expected)
        self.assertEqual(self.table_counts(), (1, 0, 0))
        script = (
            "import sys; from pathlib import Path; "
            "from lab.checkout import Checkout; "
            "from lab.payment_approvals import PaymentApprovalStore; "
            "from lab.payment_attempts import PaymentOperation; "
            "op = PaymentOperation('tenant','operation','approval','stripe:test',"
            "'acct_synthetic','key',Checkout('synthetic-shop','USD','synthetic-sku',2,1000)); "
            "status = PaymentApprovalStore(Path(sys.argv[1])).read_approval(op); "
            "print(f'{status.state}:{status.expires_at}:{status.fingerprint == op.fingerprint}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)],
            text=True,
        )
        self.assertEqual(out.strip(), f"active:{EXPIRY}:True")

    def test_status_dataclass_is_frozen(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        status = self.approvals.read_approval(self.operation)
        self.assertIsNotNone(status)
        with self.assertRaises(FrozenInstanceError):
            status.state = "revoked"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            status.expires_at = EXPIRY + 1  # type: ignore[misc]

    def test_revoked_status_persists_across_repeated_revocations_and_admission_history(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        decision = self.admit(now=NOW)
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(
            self.approvals.read_approval(self.operation),
            PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active"),
        )
        self.approvals.revoke(self.operation)
        self.approvals.revoke(self.operation)
        expected = PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "revoked")
        self.assertEqual(self.approvals.read_approval(self.operation), expected)
        self.assertEqual(
            self.approvals.read_admission(self.operation),
            ApprovalAdmission(self.operation.fingerprint, NOW, EXPIRY),
        )
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit(now=NOW + 1)

    def test_active_record_state_does_not_bypass_expiry_gate_at_admission(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        status = self.approvals.read_approval(self.operation)
        self.assertEqual(status, PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active"))
        with self.assertRaisesRegex(PaymentApprovalError, "expired"):
            self.admit(now=EXPIRY)
        self.assertEqual(self.table_counts(), (1, 0, 0))
        self.assertEqual(
            self.approvals.read_approval(self.operation),
            PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active"),
        )

    def test_every_bound_operation_dimension_is_verified_while_scopes_stay_isolated(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        for field in ("operation_id", "provider", "provider_account", "idempotency_key"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.read_approval(replace(self.operation, **{field: "different"}))
        for field, value in (
            ("merchant", "other-shop"),
            ("currency", "EUR"),
            ("sku", "other-sku"),
            ("quantity", 3),
            ("amount", 2000),
        ):
            with self.subTest(field=field):
                checkout = replace(self.operation.checkout, **{field: value})
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.approvals.read_approval(replace(self.operation, checkout=checkout))

        for unbound in (
            replace(self.operation, tenant_id="other-tenant"),
            replace(self.operation, approval_id="other-approval"),
        ):
            with self.subTest(unbound=unbound):
                self.assertIsNone(self.approvals.read_approval(unbound))

    def test_failed_commit_rolls_back_approve_and_revoke_status(self) -> None:
        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        failing_approve = sqlite3.connect(self.path, factory=FailingCommit)
        failing_approve.row_factory = sqlite3.Row
        with patch.object(self.approvals, "_connect", return_value=failing_approve):
            with self.assertRaisesRegex(sqlite3.OperationalError, "synthetic commit failure"):
                self.approvals.approve(self.operation, expires_at=EXPIRY)
        self.assertIsNone(self.approvals.read_approval(self.operation))

        self.approvals.approve(self.operation, expires_at=EXPIRY)
        failing_revoke = sqlite3.connect(self.path, factory=FailingCommit)
        failing_revoke.row_factory = sqlite3.Row
        with patch.object(self.approvals, "_connect", return_value=failing_revoke):
            with self.assertRaisesRegex(sqlite3.OperationalError, "synthetic commit failure"):
                self.approvals.revoke(self.operation)
        self.assertEqual(
            self.approvals.read_approval(self.operation),
            PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active"),
        )

    def test_invalid_operation_rejected_before_opening_connection(self) -> None:
        with patch.object(self.approvals, "_connect") as connect:
            for invalid in (None, {}, "approval", ("tenant", "approval")):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(PaymentApprovalError):
                        self.approvals.read_approval(invalid)  # type: ignore[arg-type]
            connect.assert_not_called()

    def test_corrupted_stored_metadata_is_rejected(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA ignore_check_constraints=ON")
            db.execute(
                "UPDATE payment_approvals SET expires_at=0 WHERE tenant_id=? AND approval_id=?",
                (self.operation.tenant_id, self.operation.approval_id),
            )
        with self.assertRaisesRegex(PaymentApprovalError, "Stored approval expiry is invalid"):
            self.approvals.read_approval(self.operation)

        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA ignore_check_constraints=ON")
            db.execute(
                "UPDATE payment_approvals SET expires_at=?, revoked=2 WHERE tenant_id=? AND approval_id=?",
                (EXPIRY, self.operation.tenant_id, self.operation.approval_id),
            )
        with self.assertRaisesRegex(
            PaymentApprovalError, "Stored approval revocation state is invalid"
        ):
            self.approvals.read_approval(self.operation)

    def test_storage_errors_propagate_and_select_only_takes_no_writer_lock(self) -> None:
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        with patch.object(
            self.approvals, "_connect", side_effect=sqlite3.OperationalError("database is locked")
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "database is locked"):
                self.approvals.read_approval(self.operation)

        statements: list[str] = []
        connect = self.approvals._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.approvals, "_connect", side_effect=traced):
            status = self.approvals.read_approval(self.operation)
        self.assertEqual(status, PaymentApprovalStatus(self.operation.fingerprint, EXPIRY, "active"))
        relevant = [stmt.strip().upper() for stmt in statements if not stmt.upper().startswith("PRAGMA")]
        self.assertEqual(len(relevant), 1)
        self.assertTrue(relevant[0].startswith("SELECT "))
        for forbidden in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(forbidden, relevant[0])


if __name__ == "__main__":
    unittest.main()
