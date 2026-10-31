"""Parent policy referential parity in provenance lookups and PaymentAttempt invariants."""

import json
import sqlite3
import unittest
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import (
    MerchantSignerError,
    MerchantSignerScope,
    MerchantSignerStore,
)
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import (
    AttemptConflict,
    DispatchDecision,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import (
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

NOW = 1700000000
EXPIRY = NOW + 10
APPROVAL_EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class ProvenanceParentPolicyIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.operation = PaymentOperation(
            "tenant-a",
            "op-a",
            "approval-a",
            "stripe:test",
            "acct_synthetic",
            "key-a",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.scope = MerchantSignerScope(
            "tenant-a", "synthetic-shop", URI, "synthetic-key"
        )
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self.signers.allow(self.scope)

    def admit_timed(self, operation: PaymentOperation | None = None) -> DispatchDecision:
        op = self.operation if operation is None else operation
        body = json.dumps(asdict(op.checkout)).encode()
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
            op,
            timed,
            clock=lambda: NOW,
            method="POST",
            target_uri=self.scope.target_uri,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )

    def test_direct_reservation_without_approval_row_succeeds_unless_approval_conflicts(
        self,
    ) -> None:
        unapproved_op = replace(
            self.operation,
            operation_id="op-direct",
            approval_id="approval-direct",
            idempotency_key="key-direct",
        )
        self.assertTrue(self.journal.reserve(unapproved_op).dispatch_allowed)
        prov = self.signers.read_provenance(
            self.approvals, self.journal, unapproved_op
        )
        self.assertEqual(prov.path, "direct_reservation")
        self.assertIsNone(prov.approval_admission)
        self.assertIsNone(prov.timed_signer_admission)

        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO payment_approvals VALUES (?,?,?,?,0)",
                (
                    unapproved_op.tenant_id,
                    unapproved_op.approval_id,
                    "0" * 64,
                    APPROVAL_EXPIRY,
                ),
            )
        with self.assertRaisesRegex(
            MerchantSignerError, "Approval record differs from the bound operation"
        ):
            self.signers.find_provenance(self.approvals, self.journal, unapproved_op)

    def test_provenance_survives_dual_policy_revocation_and_rejects_parent_policy_tampering(
        self,
    ) -> None:
        self.assertTrue(self.admit_timed().dispatch_allowed)
        self.approvals.revoke(self.operation)
        self.signers.revoke(self.scope)
        prov = self.signers.read_provenance(
            self.approvals, self.journal, self.operation
        )
        self.assertEqual(prov.path, "timed_signer_admission")

        with closing(sqlite3.connect(self.path)) as db:
            base_app = db.execute("SELECT * FROM payment_approvals").fetchone()
            base_adm = db.execute("SELECT * FROM payment_admissions").fetchone()
            base_perm = db.execute(
                "SELECT * FROM merchant_signer_permissions"
            ).fetchone()
            base_tmd = db.execute(
                "SELECT * FROM merchant_timed_admissions"
            ).fetchone()

        def restore() -> None:
            with closing(sqlite3.connect(self.path)) as db, db:
                for table, row in (
                    ("payment_approvals", base_app),
                    ("payment_admissions", base_adm),
                    ("merchant_signer_permissions", base_perm),
                    ("merchant_timed_admissions", base_tmd),
                ):
                    db.execute(f"DELETE FROM {table}")
                    placeholders = ",".join("?" for _ in row)
                    db.execute(f"INSERT INTO {table} VALUES ({placeholders})", row)

        cases = (
            (
                "DELETE FROM payment_approvals",
                "Orphan approval admission record exists without a recorded approval",
            ),
            (
                f"UPDATE payment_approvals SET fingerprint = '{'b' * 64}'",
                "Approval record differs from the bound operation",
            ),
            (
                "UPDATE payment_approvals SET expires_at = 0",
                "Stored approval expiry is invalid",
            ),
            (
                "UPDATE payment_approvals SET expires_at = 1700000060.5",
                "Stored approval expiry is invalid",
            ),
            (
                "UPDATE payment_approvals SET expires_at = 'bad'",
                "Stored approval expiry is invalid",
            ),
            (
                "UPDATE payment_approvals SET revoked = 2",
                "Stored approval revocation state is invalid",
            ),
            (
                "UPDATE payment_approvals SET revoked = 'revoked'",
                "Stored approval revocation state is invalid",
            ),
            (
                f"UPDATE payment_approvals SET expires_at = {APPROVAL_EXPIRY + 1}",
                "Approval admission expiry differs from recorded approval",
            ),
            (
                f"UPDATE payment_admissions SET expires_at = {APPROVAL_EXPIRY - 1}",
                "Approval admission expiry differs from recorded approval",
            ),
            (
                "DELETE FROM merchant_signer_permissions",
                "Orphan timed-admission record exists without a recorded signer permission",
            ),
            (
                "UPDATE merchant_timed_admissions SET key_id = 'unallowed-key'",
                "Orphan timed-admission record exists without a recorded signer permission",
            ),
            (
                "UPDATE merchant_signer_permissions SET revoked = 2",
                "Stored signer permission revocation state is invalid",
            ),
            (
                "UPDATE merchant_signer_permissions SET revoked = 'revoked'",
                "Stored signer permission revocation state is invalid",
            ),
        )
        for sql_stmt, pattern in cases:
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

    def test_payment_attempt_and_dispatch_decision_enforce_post_init_invariants(
        self,
    ) -> None:
        for bad_outcome, bad_ref in (
            ("pending", None),
            ("pending", "pi_123"),
            (1, None),
            ("succeeded", ""),
            ("succeeded", "   "),
            ("failed", ""),
            ("unknown", ""),
            ("unknown", "   "),
            ("unknown", 123),
        ):
            with self.subTest(outcome=bad_outcome, ref=bad_ref), self.assertRaises(
                AttemptConflict
            ):
                PaymentAttempt(bad_outcome, bad_ref)  # type: ignore[arg-type]

        valid_unknown = PaymentAttempt("unknown", None)
        referenced_unknown = PaymentAttempt("unknown", "pi_123")
        settled = PaymentAttempt("succeeded", "pi_123")
        self.assertTrue(DispatchDecision(valid_unknown, True).dispatch_allowed)
        self.assertFalse(DispatchDecision(referenced_unknown, False).dispatch_allowed)
        self.assertFalse(DispatchDecision(settled, False).dispatch_allowed)

        for bad_attempt, bad_allowed in (
            ("unknown", False),
            (None, False),
            (valid_unknown, 1),
            (valid_unknown, 0),
            (valid_unknown, "true"),
            (referenced_unknown, True),
            (settled, True),
            (PaymentAttempt("failed", "pi_123"), True),
        ):
            with self.subTest(
                attempt=bad_attempt, allowed=bad_allowed
            ), self.assertRaises(AttemptConflict):
                DispatchDecision(bad_attempt, bad_allowed)  # type: ignore[arg-type]

    def test_corrupted_provider_reference_and_unassociated_terminal_reconcile_fail_closed(
        self,
    ) -> None:
        self.assertTrue(self.journal.reserve(self.operation).dispatch_allowed)
        for bad_outcome, bad_ref in (
            ("unknown", ""),
            ("unknown", "   "),
            ("unknown", b"raw-bytes"),
            ("succeeded", ""),
            ("succeeded", "   "),
            ("failed", b"raw-bytes"),
        ):
            with self.subTest(outcome=bad_outcome, ref=bad_ref):
                with closing(sqlite3.connect(self.path)) as db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    with db:
                        db.execute(
                            "UPDATE payment_attempts SET outcome = ?, provider_reference = ?",
                            (bad_outcome, bad_ref),
                        )
                for action in (
                    lambda: self.journal.read(self.operation),
                    lambda: self.journal.read_attempt(self.operation),
                    lambda: self.journal.reserve(self.operation),
                    lambda: self.journal.reconcile(
                        self.operation,
                        observation="succeeded",
                        provider_reference="pi_new",
                    ),
                ):
                    with self.assertRaisesRegex(
                        AttemptConflict,
                        "Stored provider reference is invalid; reconciliation required",
                    ):
                        action()

        for terminal in ("succeeded", "failed"):
            with self.subTest(unassociated_terminal=terminal):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        "UPDATE payment_attempts SET outcome = ?, provider_reference = NULL",
                        (terminal,),
                    )
                with self.assertRaisesRegex(
                    AttemptConflict,
                    "Stored provider reference is invalid; reconciliation required",
                ):
                    self.journal.read_attempt(self.operation)
                for obs in ("pending", "succeeded", "failed"):
                    with self.assertRaisesRegex(
                        AttemptConflict,
                        "An unassociated terminal attempt cannot be rebound",
                    ):
                        self.journal.reconcile(
                            self.operation,
                            observation=obs,  # type: ignore[arg-type]
                            provider_reference="pi_new",
                        )


if __name__ == "__main__":
    unittest.main()
