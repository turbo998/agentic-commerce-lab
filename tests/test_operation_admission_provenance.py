"""Single-snapshot cross-table admission provenance lookup and causal invariant checks."""

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
from lab.merchant_signers import (
    MerchantSignerError,
    MerchantSignerScope,
    MerchantSignerStore,
    OperationAdmissionProvenance,
    TimedSignerAdmission,
)
from lab.payment_approvals import ApprovalAdmission, PaymentApprovalStore
from lab.payment_attempts import PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP,
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

NOW = 1700000000
EXPIRY = NOW + 10
APPROVAL_EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class OperationAdmissionProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.operation = PaymentOperation(
            "tenant",
            "operation",
            "approval",
            "stripe:test",
            "acct_synthetic",
            "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.scope = MerchantSignerScope("tenant", "synthetic-shop", URI, "synthetic-key")
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self.signers.allow(self.scope)

    def make_operation(self, op_id: str) -> PaymentOperation:
        op = replace(
            self.operation,
            operation_id=op_id,
            approval_id=f"approval-{op_id}",
            idempotency_key=f"key-{op_id}",
        )
        self.approvals.approve(op, expires_at=APPROVAL_EXPIRY)
        return op

    def timed_inputs(self, operation: PaymentOperation | None = None, *, timed: bool = True):
        operation = self.operation if operation is None else operation
        body = json.dumps(asdict(operation.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1",
            self.scope.key_id,
            MUTATION_COMPONENTS,
            "POST",
            self.scope.target_uri,
            "application/json",
            digest,
        )
        signature = (
            TimedRequestSignatureSnapshot(snapshot, NOW - 5, EXPIRY) if timed else snapshot
        )
        return {
            "scope": self.scope,
            "approvals": self.approvals,
            "journal": self.journal,
            "operation": operation,
            "signature": signature,
            "clock": lambda: NOW,
            "method": "POST",
            "target_uri": self.scope.target_uri,
            "content_type": "application/json",
            "content_digest": digest,
            "content_encoding": None,
            "body": body,
        }

    def test_unreserved_operation_returns_none_and_read_raises_without_creating_rows(self) -> None:
        self.assertIsNone(
            self.signers.find_provenance(self.approvals, self.journal, self.operation)
        )
        with self.assertRaisesRegex(
            MerchantSignerError, "No reservation or admission record exists"
        ):
            self.signers.read_provenance(self.approvals, self.journal, self.operation)
        with closing(sqlite3.connect(self.path)) as db:
            counts = tuple(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in (
                    "payment_attempts",
                    "payment_admissions",
                    "merchant_timed_admissions",
                )
            )
        self.assertEqual(counts, (0, 0, 0))

    def test_classifies_all_three_provenance_paths_and_survives_revocation_and_settlement(
        self,
    ) -> None:
        direct_op = self.make_operation("direct")
        approval_op = self.make_operation("approval")
        timed_op = self.operation

        self.assertTrue(self.journal.reserve(direct_op).dispatch_allowed)
        self.assertTrue(self.signers.admit(**self.timed_inputs(approval_op, timed=False)).dispatch_allowed)
        self.assertTrue(self.signers.admit(**self.timed_inputs(timed_op, timed=True)).dispatch_allowed)

        direct_prov = self.signers.read_provenance(self.approvals, self.journal, direct_op)
        self.assertEqual(direct_prov.path, "direct_reservation")
        self.assertEqual(
            direct_prov,
            OperationAdmissionProvenance(
                direct_op.fingerprint,
                PaymentAttempt("unknown", None),
                None,
                None,
            ),
        )

        approval_prov = self.signers.read_provenance(self.approvals, self.journal, approval_op)
        self.assertEqual(approval_prov.path, "approval_admission")
        self.assertEqual(
            approval_prov,
            OperationAdmissionProvenance(
                approval_op.fingerprint,
                PaymentAttempt("unknown", None),
                ApprovalAdmission(approval_op.fingerprint, NOW, APPROVAL_EXPIRY),
                None,
            ),
        )

        self.signers.revoke(self.scope)
        self.journal.reconcile(
            timed_op, observation="succeeded", provider_reference="pi_settled_123"
        )
        timed_prov = self.signers.read_provenance(self.approvals, self.journal, timed_op)
        self.assertEqual(timed_prov.path, "timed_signer_admission")
        self.assertEqual(
            timed_prov,
            OperationAdmissionProvenance(
                timed_op.fingerprint,
                PaymentAttempt("succeeded", "pi_settled_123"),
                ApprovalAdmission(timed_op.fingerprint, NOW, APPROVAL_EXPIRY),
                TimedSignerAdmission(
                    timed_op.fingerprint,
                    self.scope,
                    "sig1",
                    NOW - 5,
                    EXPIRY,
                    NOW,
                ),
            ),
        )
        with self.assertRaises(FrozenInstanceError):
            timed_prov.fingerprint = "0" * 64  # type: ignore[misc]

    def test_rejects_untrusted_inputs_cross_file_stores_and_direct_dataclass_corruption(
        self,
    ) -> None:
        with patch.object(
            self.signers, "_connect", side_effect=AssertionError("unexpected DB access")
        ):
            for bad_approvals, bad_journal, bad_op in (
                (None, self.journal, self.operation),
                (self.approvals, None, self.operation),
                (self.approvals, self.journal, None),
                ({}, self.journal, self.operation),
                (self.approvals, {}, self.operation),
                (self.approvals, self.journal, "operation"),
            ):
                with self.subTest(
                    approvals=bad_approvals, journal=bad_journal, operation=bad_op
                ), self.assertRaises(MerchantSignerError):
                    self.signers.find_provenance(bad_approvals, bad_journal, bad_op)  # type: ignore[arg-type]

            other_path = Path(self.directory.name) / "other.sqlite3"
            other_journal = PaymentAttemptJournal(other_path)
            other_approvals = PaymentApprovalStore(other_path)
            for app, jrnl in (
                (other_approvals, self.journal),
                (self.approvals, other_journal),
            ):
                with self.subTest(app=app.path, jrnl=jrnl.path), self.assertRaisesRegex(
                    MerchantSignerError, "same resolved SQLite file"
                ):
                    self.signers.find_provenance(app, jrnl, self.operation)

        valid_attempt = PaymentAttempt("unknown", None)
        valid_adm = ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY)
        valid_tmd = TimedSignerAdmission(
            self.operation.fingerprint, self.scope, "sig1", NOW - 5, EXPIRY, NOW
        )
        other_fp = "a" * 64
        for fp, att, adm, tmd in (
            ("not-hex", valid_attempt, None, None),
            (self.operation.fingerprint, "unknown", None, None),
            (self.operation.fingerprint, valid_attempt, "bad", None),
            (self.operation.fingerprint, valid_attempt, valid_adm, "bad"),
            (self.operation.fingerprint, valid_attempt, None, valid_tmd),
            (
                self.operation.fingerprint,
                valid_attempt,
                replace(valid_adm, fingerprint=other_fp),
                None,
            ),
            (
                self.operation.fingerprint,
                valid_attempt,
                valid_adm,
                replace(valid_tmd, fingerprint=other_fp),
            ),
            (
                self.operation.fingerprint,
                valid_attempt,
                valid_adm,
                replace(valid_tmd, admitted_at=NOW + 1),
            ),
            (
                self.operation.fingerprint,
                valid_attempt,
                ApprovalAdmission(self.operation.fingerprint, APPROVAL_EXPIRY, APPROVAL_EXPIRY),
                replace(valid_tmd, admitted_at=APPROVAL_EXPIRY),
            ),
        ):
            with self.subTest(fp=fp, att=att, adm=adm, tmd=tmd), self.assertRaises(
                MerchantSignerError
            ):
                OperationAdmissionProvenance(fp, att, adm, tmd)  # type: ignore[arg-type]

    def test_rejects_ten_dimension_fingerprint_mismatches_and_table_fingerprint_drift(
        self,
    ) -> None:
        self.signers.admit(**self.timed_inputs())
        checkout = self.operation.checkout
        drifted_operations = (
            replace(self.operation, approval_id="other-approval"),
            replace(self.operation, provider="stripe:other"),
            replace(self.operation, provider_account="acct_other"),
            replace(self.operation, idempotency_key="other-key"),
            replace(self.operation, checkout=replace(checkout, merchant="other-shop")),
            replace(self.operation, checkout=replace(checkout, currency="EUR")),
            replace(self.operation, checkout=replace(checkout, sku="other-sku")),
            replace(self.operation, checkout=replace(checkout, quantity=3)),
            replace(self.operation, checkout=replace(checkout, amount=1001)),
        )
        for drifted in drifted_operations:
            with self.subTest(drifted=drifted), self.assertRaisesRegex(
                MerchantSignerError, "differs from the bound operation"
            ):
                self.signers.find_provenance(self.approvals, self.journal, drifted)

        for table in (
            "payment_attempts",
            "payment_admissions",
            "merchant_timed_admissions",
        ):
            with self.subTest(table=table):
                with closing(sqlite3.connect(self.path)) as db:
                    with db:
                        db.execute(f"UPDATE {table} SET fingerprint = ?", ("0" * 64,))
                with self.assertRaisesRegex(
                    MerchantSignerError, "differs from the bound operation"
                ):
                    self.signers.find_provenance(
                        self.approvals, self.journal, self.operation
                    )
                with closing(sqlite3.connect(self.path)) as db:
                    with db:
                        db.execute(
                            f"UPDATE {table} SET fingerprint = ?",
                            (self.operation.fingerprint,),
                        )

    def test_rejects_cross_table_orphans_clock_split_brain_and_corrupted_columns(self) -> None:
        self.signers.admit(**self.timed_inputs())
        with closing(sqlite3.connect(self.path)) as db:
            baseline_att = db.execute("SELECT * FROM payment_attempts").fetchone()
            baseline_adm = db.execute("SELECT * FROM payment_admissions").fetchone()
            baseline_tmd = db.execute("SELECT * FROM merchant_timed_admissions").fetchone()

        def restore() -> None:
            with closing(sqlite3.connect(self.path)) as db:
                with db:
                    for table, row in (
                        ("payment_attempts", baseline_att),
                        ("payment_admissions", baseline_adm),
                        ("merchant_timed_admissions", baseline_tmd),
                    ):
                        db.execute(f"DELETE FROM {table}")
                        placeholders = ",".join("?" for _ in row)
                        db.execute(f"INSERT INTO {table} VALUES ({placeholders})", row)

        mutations = (
            ("DELETE FROM payment_attempts", "Orphan admission record"),
            (
                "DELETE FROM payment_attempts; DELETE FROM payment_admissions",
                "Orphan admission record",
            ),
            ("DELETE FROM payment_admissions", "Orphan timed-admission record"),
            (
                f"UPDATE merchant_timed_admissions SET admitted_at = {NOW + 1}",
                "Timed-admission clock sample differs from approval admission",
            ),
            (
                "UPDATE payment_attempts SET outcome = 'pending'",
                "Stored attempt outcome is invalid",
            ),
            (
                "UPDATE payment_attempts SET outcome = 'succeeded', provider_reference = NULL",
                "Stored attempt provider reference is invalid",
            ),
            (
                "UPDATE payment_attempts SET outcome = 'succeeded', provider_reference = '   '",
                "Stored attempt provider reference is invalid",
            ),
            (
                f"UPDATE payment_admissions SET expires_at = {NOW}",
                "Stored approval admission times are invalid",
            ),
            (
                "UPDATE merchant_timed_admissions SET target_uri = ' https://synthetic-shop.example/checkout'",
                "Canonical nonblank signer scope strings",
            ),
            (
                "UPDATE merchant_timed_admissions SET key_id = 'bad\x7fkey'",
                "Route and key ID must be ASCII without controls",
            ),
            (
                "UPDATE merchant_timed_admissions SET signature_label = 'BadLabel'",
                "Stored timed-admission signature label is invalid",
            ),
            (
                f"UPDATE merchant_timed_admissions SET created = {NOW + 1}",
                "Stored timed-admission times are invalid",
            ),
            (
                f"UPDATE merchant_timed_admissions SET expires = {MAX_SIGNATURE_TIMESTAMP + 1}",
                "Stored timed-admission times are invalid",
            ),
        )
        for sql_stmt, pattern in mutations:
            with self.subTest(sql_stmt=sql_stmt):
                restore()
                with closing(sqlite3.connect(self.path)) as db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    with db:
                        db.executescript(sql_stmt)
                with self.assertRaisesRegex(MerchantSignerError, pattern):
                    self.signers.find_provenance(
                        self.approvals, self.journal, self.operation
                    )
        restore()

    def test_single_select_snapshot_takes_no_write_locks_under_concurrent_writer(self) -> None:
        self.signers.admit(**self.timed_inputs())
        statements: list[str] = []
        original_connect = self.signers._connect

        def traced_connect() -> sqlite3.Connection:
            db = original_connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.signers, "_connect", side_effect=traced_connect):
            provenance = self.signers.read_provenance(
                self.approvals, self.journal, self.operation
            )
        self.assertEqual(provenance.path, "timed_signer_admission")
        select_statements = [stmt for stmt in statements if stmt.startswith("SELECT")]
        self.assertEqual(len(select_statements), 1)
        for forbidden in ("BEGIN", "INSERT", "UPDATE", "DELETE", "REPLACE"):
            self.assertFalse(any(forbidden in stmt.upper() for stmt in statements))

        writer = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import sqlite3, sys; "
                    "db = sqlite3.connect(sys.argv[1]); "
                    "db.execute('PRAGMA journal_mode = WAL'); "
                    "db.execute('BEGIN IMMEDIATE'); "
                    "sys.stdout.write('locked\\n'); sys.stdout.flush(); "
                    "sys.stdin.readline()"
                ),
                str(self.path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert writer.stdout is not None
            self.assertEqual(writer.stdout.readline().strip(), "locked")
            concurrent = self.signers.read_provenance(
                self.approvals, self.journal, self.operation
            )
            self.assertEqual(concurrent, provenance)
        finally:
            if writer.stdin is not None:
                writer.stdin.write("\n")
                writer.stdin.flush()
            writer.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
