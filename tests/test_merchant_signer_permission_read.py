"""Scoped local merchant signer permission state lookup, not signature proof or admission authority."""

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
    MerchantSignerPermissionStatus,
    MerchantSignerScope,
    MerchantSignerStore,
    TimedSignerAdmission,
)
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class MerchantSignerPermissionReadTests(unittest.TestCase):
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

    def admit(self, *, now: int = NOW):
        body = json.dumps(asdict(self.operation.checkout)).encode()
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
        timed = TimedRequestSignatureSnapshot(snapshot, NOW - 5, EXPIRY)
        return self.signers.admit(
            self.scope,
            self.approvals,
            self.journal,
            self.operation,
            timed,
            clock=lambda: now,
            method="POST",
            target_uri=self.scope.target_uri,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )

    def table_counts(self) -> tuple[int, int, int, int]:
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in (
                    "merchant_signer_permissions",
                    "merchant_timed_admissions",
                    "payment_approvals",
                    "payment_attempts",
                )
            )

    def test_absent_permission_returns_none_without_creating_records(self) -> None:
        self.assertIsNone(self.signers.read_permission(self.scope))
        self.assertEqual(self.table_counts(), (0, 0, 0, 0))
        with self.assertRaises(MerchantSignerError):
            self.signers.read_timed_admission(self.operation)
        with self.assertRaises(AttemptConflict):
            self.journal.read(self.operation)

    def test_active_status_readable_before_admission_and_survives_fresh_process(self) -> None:
        self.signers.allow(self.scope)
        expected = MerchantSignerPermissionStatus(self.scope, "active")
        self.assertEqual(self.signers.read_permission(self.scope), expected)
        self.assertEqual(MerchantSignerStore(self.path).read_permission(self.scope), expected)
        self.assertEqual(self.table_counts(), (1, 0, 0, 0))
        script = (
            "import sys; from pathlib import Path; "
            "from lab.merchant_signers import MerchantSignerScope, MerchantSignerStore; "
            "scope = MerchantSignerScope('tenant','synthetic-shop',"
            "'https://synthetic-shop.example/checkout?cart=one','synthetic-key'); "
            "status = MerchantSignerStore(Path(sys.argv[1])).read_permission(scope); "
            "print(f'{status.state}:{status.scope == scope}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)],
            text=True,
        )
        self.assertEqual(out.strip(), "active:True")

    def test_status_dataclass_is_frozen_and_validates_fields(self) -> None:
        status = MerchantSignerPermissionStatus(self.scope, "active")
        with self.assertRaises(FrozenInstanceError):
            status.state = "revoked"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            status.scope = replace(self.scope, key_id="other")  # type: ignore[misc]
        for invalid_scope in (None, {}, "scope"):
            with self.subTest(invalid_scope=invalid_scope), self.assertRaises(MerchantSignerError):
                MerchantSignerPermissionStatus(invalid_scope, "active")  # type: ignore[arg-type]
        for invalid_state in (None, "", "allowed", "pending", True, 0):
            with self.subTest(invalid_state=invalid_state), self.assertRaises(MerchantSignerError):
                MerchantSignerPermissionStatus(self.scope, invalid_state)  # type: ignore[arg-type]

    def test_revoked_status_persists_across_repeated_revocations_and_timed_history(self) -> None:
        self.signers.allow(self.scope)
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        decision = self.admit(now=NOW)
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(
            self.signers.read_permission(self.scope),
            MerchantSignerPermissionStatus(self.scope, "active"),
        )
        self.signers.revoke(self.scope)
        self.signers.revoke(self.scope)
        expected = MerchantSignerPermissionStatus(self.scope, "revoked")
        self.assertEqual(self.signers.read_permission(self.scope), expected)
        self.assertEqual(
            self.signers.read_timed_admission(self.operation),
            TimedSignerAdmission(
                self.operation.fingerprint,
                self.scope,
                "sig1",
                NOW - 5,
                EXPIRY,
                NOW,
            ),
        )
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit(now=NOW + 1)

    def test_active_permission_state_does_not_supply_approval_or_admission(self) -> None:
        self.signers.allow(self.scope)
        status = self.signers.read_permission(self.scope)
        self.assertEqual(status, MerchantSignerPermissionStatus(self.scope, "active"))
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.admit(now=NOW)
        self.assertEqual(self.table_counts(), (1, 0, 0, 0))
        self.assertEqual(
            self.signers.read_permission(self.scope),
            MerchantSignerPermissionStatus(self.scope, "active"),
        )

    def test_every_scope_dimension_is_isolated(self) -> None:
        self.signers.allow(self.scope)
        other_tenant = replace(self.scope, tenant_id="other-tenant")
        other_merchant = replace(self.scope, merchant="other-shop")
        other_route = replace(self.scope, target_uri=URI + "&other=1")
        other_key = replace(self.scope, key_id="other-key")
        for candidate in (other_tenant, other_merchant, other_route, other_key):
            with self.subTest(candidate=candidate):
                self.assertIsNone(self.signers.read_permission(candidate))
        self.signers.allow(other_key)
        self.signers.revoke(other_key)
        self.assertEqual(
            self.signers.read_permission(self.scope),
            MerchantSignerPermissionStatus(self.scope, "active"),
        )
        self.assertEqual(
            self.signers.read_permission(other_key),
            MerchantSignerPermissionStatus(other_key, "revoked"),
        )

    def test_invalid_scope_rejected_before_opening_connection(self) -> None:
        with patch.object(self.signers, "_connect") as connect:
            for invalid in (None, {}, "scope", 123, self.operation):
                with self.subTest(invalid=invalid), self.assertRaises(MerchantSignerError):
                    self.signers.read_permission(invalid)  # type: ignore[arg-type]
            connect.assert_not_called()

    def test_rolled_back_allow_or_revoke_is_not_reported_by_reader(self) -> None:
        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        conn_allow = sqlite3.connect(self.path, factory=FailingCommit)
        conn_allow.row_factory = sqlite3.Row
        with patch.object(self.signers, "_connect", return_value=conn_allow):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.signers.allow(self.scope)
        self.assertIsNone(self.signers.read_permission(self.scope))

        self.signers.allow(self.scope)
        conn_revoke = sqlite3.connect(self.path, factory=FailingCommit)
        conn_revoke.row_factory = sqlite3.Row
        with patch.object(self.signers, "_connect", return_value=conn_revoke):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.signers.revoke(self.scope)
        self.assertEqual(
            self.signers.read_permission(self.scope),
            MerchantSignerPermissionStatus(self.scope, "active"),
        )

    def test_corrupted_persisted_row_raises_explicit_error(self) -> None:
        bad_path = Path(self.directory.name) / "corrupted.sqlite3"
        with closing(sqlite3.connect(bad_path)) as db, db:
            db.execute(
                """
                CREATE TABLE merchant_signer_permissions (
                    tenant_id TEXT NOT NULL,
                    merchant TEXT NOT NULL,
                    target_uri TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    revoked ANY
                )
                """
            )
            db.execute(
                """
                CREATE TABLE merchant_timed_admissions (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    target_uri TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    signature_label TEXT NOT NULL,
                    created INTEGER NOT NULL,
                    expires INTEGER NOT NULL,
                    admitted_at INTEGER NOT NULL
                )
                """
            )
            db.execute(
                "INSERT INTO merchant_signer_permissions VALUES (?,?,?,?,?)",
                (*self.scope.key, 2),
            )
        bad_store = MerchantSignerStore(bad_path)
        with self.assertRaisesRegex(MerchantSignerError, "revocation state is invalid"):
            bad_store.read_permission(self.scope)

        with closing(sqlite3.connect(bad_path)) as db, db:
            db.execute("UPDATE merchant_signer_permissions SET revoked='active'")
        with self.assertRaisesRegex(MerchantSignerError, "revocation state is invalid"):
            bad_store.read_permission(self.scope)

    def test_select_only_does_not_take_writer_lock(self) -> None:
        self.signers.allow(self.scope)
        statements: list[str] = []
        connect = self.signers._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.signers, "_connect", side_effect=traced):
            self.assertEqual(
                self.signers.read_permission(self.scope),
                MerchantSignerPermissionStatus(self.scope, "active"),
            )
            self.assertIsNone(
                self.signers.read_permission(replace(self.scope, key_id="absent"))
            )
        select_stmts = [
            stmt for stmt in statements if "FROM merchant_signer_permissions" in stmt
        ]
        self.assertEqual(len(select_stmts), 2)
        self.assertTrue(all(stmt.startswith("SELECT ") for stmt in select_stmts))
        self.assertFalse(any("BEGIN IMMEDIATE" in stmt for stmt in statements))


if __name__ == "__main__":
    unittest.main()
