"""Stage 1735: Two-store approval-admission provenance reader & stored policy row integrity tests."""

from __future__ import annotations

from contextlib import closing
from dataclasses import FrozenInstanceError, asdict, replace
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import (
    MerchantSignerError,
    MerchantSignerPermissionStatus,
    MerchantSignerScope,
    MerchantSignerStore,
    SignerAdmissionPreview,
    SignerGrantPreview,
    SignerRevocationPreview,
    TimedSignerAdmission,
)
from lab.payment_approvals import (
    ApprovalAdmission,
    ApprovalAdmissionPreview,
    ApprovalAdmissionProvenance,
    ApprovalGrantPreview,
    ApprovalRevocationPreview,
    PaymentApprovalError,
    PaymentApprovalStatus,
    PaymentApprovalStore,
)
from lab.payment_attempts import (
    AttemptConflict,
    DispatchDecision,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import (
    MUTATION_COMPONENTS,
    RequestBindingError,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)
from lab.stripe_delivery import StripeDeliveryError, VerifiedDelivery
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope
from lab.stripe_readback import StripeReadbackError, accept_stripe_readback
from tests.test_stripe_inbox import SECRET, event_body, header


NOW = 1_700_000_000
APPROVAL_EXPIRY = NOW + 300
SIG_CREATED = NOW - 10
SIG_EXPIRES = NOW + 60
TARGET_URI = "https://synthetic-shop.example/checkout"


class ApprovalAdmissionProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "provenance_two_store.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.checkout = Checkout("synthetic-shop", "USD", "sku-1", 1, 2500)
        self.operation = PaymentOperation(
            "tenant-a",
            "op-1",
            "approval-1",
            "stripe:test",
            "acct_synthetic",
            "idem-op-1",
            self.checkout,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _body_and_digest(
        self, operation: PaymentOperation | None = None
    ) -> tuple[bytes, str]:
        op = self.operation if operation is None else operation
        body = json.dumps(
            asdict(op.checkout), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return body, compute_rfc9530_content_digest(body)

    def _admit_approval(
        self,
        operation: PaymentOperation | None = None,
        *,
        admitted_at: int = NOW,
    ) -> None:
        op = self.operation if operation is None else operation
        body, digest = self._body_and_digest(op)
        bare = RequestSignatureSnapshot(
            "sig1",
            "key-2026-11",
            MUTATION_COMPONENTS,
            "POST",
            TARGET_URI,
            "application/json",
            digest,
        )
        decision = self.approvals.admit(
            self.journal,
            op,
            bare,
            clock=lambda: admitted_at,
            expected_target_uri=TARGET_URI,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertTrue(decision.dispatch_allowed)

    def test_approval_admission_provenance_across_unreserved_legacy_and_admitted_paths(
        self,
    ) -> None:
        # 1. Unreserved operation (with or without unused approval row) returns None
        self.assertIsNone(self.approvals.find_provenance(self.journal, self.operation))
        with self.assertRaisesRegex(
            PaymentApprovalError,
            "No reservation or admission record exists for this operation.",
        ):
            self.approvals.read_provenance(self.journal, self.operation)

        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self.assertIsNone(self.approvals.find_provenance(self.journal, self.operation))

        # Verify no merchant_signer_* tables were created in 2-store mode
        with closing(sqlite3.connect(self.path)) as db:
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertEqual(
            tables, {"payment_attempts", "payment_approvals", "payment_admissions"}
        )

        # 2. Direct legacy reservation without an approval row
        legacy_op = replace(
            self.operation,
            operation_id="op-legacy-no-app",
            approval_id="approval-legacy-none",
            idempotency_key="idem-legacy-no-app",
        )
        self.assertTrue(self.journal.reserve(legacy_op).dispatch_allowed)
        self.assertEqual(
            self.approvals.read_provenance(self.journal, legacy_op),
            ApprovalAdmissionProvenance(
                legacy_op.fingerprint,
                PaymentAttempt("unknown", None),
                None,
                None,
            ),
        )

        # 3. Direct legacy reservation with an approval row (active then revoked)
        legacy_with_app = replace(
            self.operation,
            operation_id="op-legacy-with-app",
            approval_id="approval-legacy-with-app",
            idempotency_key="idem-legacy-with-app",
        )
        self.approvals.approve(legacy_with_app, expires_at=APPROVAL_EXPIRY)
        self.assertTrue(self.journal.reserve(legacy_with_app).dispatch_allowed)
        self.assertEqual(
            self.approvals.read_provenance(self.journal, legacy_with_app),
            ApprovalAdmissionProvenance(
                legacy_with_app.fingerprint,
                PaymentAttempt("unknown", None),
                PaymentApprovalStatus(
                    legacy_with_app.fingerprint, APPROVAL_EXPIRY, "active"
                ),
                None,
            ),
        )
        self.approvals.revoke(legacy_with_app)
        self.assertEqual(
            self.approvals.read_provenance(self.journal, legacy_with_app),
            ApprovalAdmissionProvenance(
                legacy_with_app.fingerprint,
                PaymentAttempt("unknown", None),
                PaymentApprovalStatus(
                    legacy_with_app.fingerprint, APPROVAL_EXPIRY, "revoked"
                ),
                None,
            ),
        )

        # 4. Full admitted operation across revocation and reconciliation
        self._admit_approval(self.operation, admitted_at=NOW)
        prov = self.approvals.read_provenance(self.journal, self.operation)
        self.assertEqual(
            prov,
            ApprovalAdmissionProvenance(
                self.operation.fingerprint,
                PaymentAttempt("unknown", None),
                PaymentApprovalStatus(
                    self.operation.fingerprint, APPROVAL_EXPIRY, "active"
                ),
                ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY),
            ),
        )
        with self.assertRaises(FrozenInstanceError):
            prov.attempt = PaymentAttempt("succeeded", "pi_x")  # type: ignore[misc]

        self.approvals.revoke(self.operation)
        self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_settled"
        )
        self.assertEqual(
            self.approvals.find_provenance(self.journal, self.operation),
            ApprovalAdmissionProvenance(
                self.operation.fingerprint,
                PaymentAttempt("succeeded", "pi_settled"),
                PaymentApprovalStatus(
                    self.operation.fingerprint, APPROVAL_EXPIRY, "revoked"
                ),
                ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY),
            ),
        )

    def test_approval_admission_provenance_detects_cross_table_orphans_and_drift(
        self,
    ) -> None:
        with patch.object(self.approvals, "_connect") as connect:
            for bad_journal in (None, {}, "journal"):
                with self.subTest(journal=bad_journal), self.assertRaises(
                    PaymentApprovalError
                ):
                    self.approvals.find_provenance(bad_journal, self.operation)  # type: ignore[arg-type]
            for bad_op in (None, {}, "operation"):
                with self.subTest(operation=bad_op), self.assertRaises(
                    PaymentApprovalError
                ):
                    self.approvals.find_provenance(self.journal, bad_op)  # type: ignore[arg-type]
            connect.assert_not_called()

        other_journal = PaymentAttemptJournal(
            Path(self.tempdir.name) / "separate.sqlite3"
        )
        with self.assertRaisesRegex(PaymentApprovalError, "same resolved SQLite file"):
            self.approvals.find_provenance(other_journal, self.operation)

        alias_path = Path(self.tempdir.name) / "hardlink.sqlite3"
        os.link(self.path, alias_path)
        alias_journal = PaymentAttemptJournal(self.path)
        alias_journal.path = alias_path
        with self.assertRaisesRegex(PaymentApprovalError, "same resolved SQLite file"):
            self.approvals.find_provenance(alias_journal, self.operation)

        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self._admit_approval(self.operation, admitted_at=NOW)

        with closing(sqlite3.connect(self.path)) as db:
            att_snap = db.execute("SELECT * FROM payment_attempts").fetchall()
            adm_snap = db.execute("SELECT * FROM payment_admissions").fetchall()
            app_snap = db.execute("SELECT * FROM payment_approvals").fetchall()

        def restore() -> None:
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute("PRAGMA ignore_check_constraints = ON")
                db.execute("DELETE FROM payment_attempts")
                db.execute("DELETE FROM payment_admissions")
                db.execute("DELETE FROM payment_approvals")
                db.executemany(
                    "INSERT INTO payment_attempts VALUES (?,?,?,?,?,?,?,?,?)", att_snap
                )
                db.executemany(
                    "INSERT INTO payment_admissions VALUES (?,?,?,?,?)", adm_snap
                )
                db.executemany(
                    "INSERT INTO payment_approvals VALUES (?,?,?,?,?)", app_snap
                )

        for label, sql, exc_type, pattern in (
            (
                "orphan_admission_without_attempt",
                "DELETE FROM payment_attempts",
                PaymentApprovalError,
                "Orphan admission record exists without a payment reservation.",
            ),
            (
                "orphan_admission_without_approval",
                "DELETE FROM payment_approvals",
                PaymentApprovalError,
                "Orphan admission record exists without a recorded approval.",
            ),
            (
                "admission_expiry_drift",
                f"UPDATE payment_admissions SET expires_at = {APPROVAL_EXPIRY - 1}",
                PaymentApprovalError,
                "Stored admission expiry differs from the recorded approval expiry.",
            ),
            (
                "approval_fingerprint_drift",
                "UPDATE payment_approvals SET fingerprint = '" + ("f" * 64) + "'",
                PaymentApprovalError,
                "Approval differs from the bound operation.",
            ),
            (
                "approval_expiry_corrupted",
                "UPDATE payment_approvals SET expires_at = 0",
                PaymentApprovalError,
                "Stored approval expiry is invalid.",
            ),
            (
                "approval_revoked_corrupted",
                "UPDATE payment_approvals SET revoked = 2",
                PaymentApprovalError,
                "Stored approval revocation state is invalid.",
            ),
            (
                "admission_fingerprint_drift",
                "UPDATE payment_admissions SET fingerprint = '" + ("e" * 64) + "'",
                PaymentApprovalError,
                "Admission record differs from the bound operation.",
            ),
            (
                "admission_times_corrupted",
                f"UPDATE payment_admissions SET admitted_at = {APPROVAL_EXPIRY}",
                PaymentApprovalError,
                "Stored admission times are invalid.",
            ),
            (
                "attempt_approval_drift",
                "UPDATE payment_attempts SET approval_id = 'other-approval'",
                AttemptConflict,
                "Operation binding changed; do not dispatch.",
            ),
            (
                "attempt_provider_drift",
                "UPDATE payment_attempts SET provider = 'stripe:live'",
                AttemptConflict,
                "Operation binding changed; do not dispatch.",
            ),
            (
                "attempt_unassociated_terminal",
                "UPDATE payment_attempts SET outcome = 'succeeded', provider_reference = NULL",
                AttemptConflict,
                "Stored attempt outcome and provider reference are inconsistent.",
            ),
        ):
            with self.subTest(case=label):
                restore()
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.executescript(sql)
                with self.assertRaisesRegex(exc_type, pattern):
                    self.approvals.find_provenance(self.journal, self.operation)
        restore()

        # Constructor invariants on ApprovalAdmissionProvenance
        fp = self.operation.fingerprint
        att = PaymentAttempt("unknown", None)
        status = PaymentApprovalStatus(fp, APPROVAL_EXPIRY, "active")
        adm = ApprovalAdmission(fp, NOW, APPROVAL_EXPIRY)
        other_fp = "a" * 64

        for kwargs, pattern in (
            (
                dict(
                    fingerprint="bad",
                    attempt=att,
                    approval_status=status,
                    approval_admission=adm,
                ),
                "64-char hex",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt="not-attempt",
                    approval_status=status,
                    approval_admission=adm,
                ),
                "PaymentAttempt is required",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=PaymentAttempt("succeeded", None),
                    approval_status=status,
                    approval_admission=adm,
                ),
                "inconsistent",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status="bad",
                    approval_admission=None,
                ),
                "PaymentApprovalStatus or None",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status=PaymentApprovalStatus(
                        other_fp, APPROVAL_EXPIRY, "active"
                    ),
                    approval_admission=None,
                ),
                "Approval differs",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status=status,
                    approval_admission="bad",
                ),
                "ApprovalAdmission or None",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status=status,
                    approval_admission=ApprovalAdmission(
                        other_fp, NOW, APPROVAL_EXPIRY
                    ),
                ),
                "Admission record differs",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status=None,
                    approval_admission=adm,
                ),
                "Orphan admission record",
            ),
            (
                dict(
                    fingerprint=fp,
                    attempt=att,
                    approval_status=status,
                    approval_admission=ApprovalAdmission(
                        fp, NOW, APPROVAL_EXPIRY - 1
                    ),
                ),
                "Stored admission expiry differs",
            ),
        ):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                PaymentApprovalError, pattern
            ):
                ApprovalAdmissionProvenance(**kwargs)  # type: ignore[arg-type]

    def test_corrupted_policy_rows_fail_closed_in_revoke_and_admit(self) -> None:
        signers = MerchantSignerStore(self.path)
        scope = MerchantSignerScope(
            "tenant-a", "synthetic-shop", TARGET_URI, "key-2026-11"
        )
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        signers.allow(scope)

        body, digest = self._body_and_digest(self.operation)
        bare = RequestSignatureSnapshot(
            "sig1",
            scope.key_id,
            MUTATION_COMPONENTS,
            "POST",
            TARGET_URI,
            "application/json",
            digest,
        )
        timed = TimedRequestSignatureSnapshot(bare, SIG_CREATED, SIG_EXPIRES)

        # 1. Corrupted payment_approvals.expires_at or payment_approvals.revoked fails closed in revoke() and admit()
        for bad_col, bad_val, pattern in (
            ("expires_at", 0, "Stored approval expiry is invalid."),
            ("expires_at", -5, "Stored approval expiry is invalid."),
            ("expires_at", 1.5, "Stored approval expiry is invalid."),
            ("expires_at", "invalid-expiry", "Stored approval expiry is invalid."),
            ("revoked", 2, "Stored approval revocation state is invalid."),
            ("revoked", -1, "Stored approval revocation state is invalid."),
            ("revoked", b"0", "Stored approval revocation state is invalid."),
            ("revoked", "revoked", "Stored approval revocation state is invalid."),
        ):
            with self.subTest(table="payment_approvals", col=bad_col, val=bad_val):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(
                        f"UPDATE payment_approvals SET {bad_col}=?", (bad_val,)
                    )
                try:
                    with self.assertRaisesRegex(PaymentApprovalError, pattern):
                        self.approvals.revoke(self.operation)
                    with self.assertRaisesRegex(PaymentApprovalError, pattern):
                        self.approvals.admit(
                            self.journal,
                            self.operation,
                            bare,
                            clock=lambda: NOW,
                            expected_target_uri=TARGET_URI,
                            method="POST",
                            target_uri=TARGET_URI,
                            content_type="application/json",
                            content_digest=digest,
                            content_encoding=None,
                            body=body,
                        )
                    with self.assertRaisesRegex(PaymentApprovalError, pattern):
                        signers.admit(
                            scope,
                            self.approvals,
                            self.journal,
                            self.operation,
                            timed,
                            clock=lambda: NOW,
                            method="POST",
                            target_uri=TARGET_URI,
                            content_type="application/json",
                            content_digest=digest,
                            content_encoding=None,
                            body=body,
                        )
                finally:
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute("PRAGMA ignore_check_constraints = ON")
                        db.execute(
                            "UPDATE payment_approvals SET expires_at=?, revoked=0",
                            (APPROVAL_EXPIRY,),
                        )

        # 2. Corrupted merchant_signer_permissions.revoked fails closed in revoke() and admit()
        for bad_revoked in (2, -1, 1.5, b"0", "revoked"):
            with self.subTest(
                table="merchant_signer_permissions", revoked=bad_revoked
            ):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(
                        "UPDATE merchant_signer_permissions SET revoked=?",
                        (bad_revoked,),
                    )
                try:
                    with self.assertRaisesRegex(
                        MerchantSignerError,
                        "Stored signer permission revocation state is invalid.",
                    ):
                        signers.revoke(scope)
                    with self.assertRaisesRegex(
                        MerchantSignerError,
                        "Stored signer permission revocation state is invalid.",
                    ):
                        signers.admit(
                            scope,
                            self.approvals,
                            self.journal,
                            self.operation,
                            timed,
                            clock=lambda: NOW,
                            method="POST",
                            target_uri=TARGET_URI,
                            content_type="application/json",
                            content_digest=digest,
                            content_encoding=None,
                            body=body,
                        )
                finally:
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute("PRAGMA ignore_check_constraints = ON")
                        db.execute("UPDATE merchant_signer_permissions SET revoked=0")

    def test_stripe_readback_and_verified_delivery_fail_closed_invariants(self) -> None:
        inbox = StripeEventInbox(self.path)
        scope = StripeInboxScope("tenant-a", "endpoint-1", "acct_synthetic", False)
        body = event_body()
        inbox.record(scope, body, header(body), SECRET, now=NOW)
        claim = inbox.claim_next(scope, "worker-1")
        assert claim is not None
        intent = {
            "object": "payment_intent",
            "id": "pi_synthetic",
            "livemode": False,
            "amount": 2500,
            "amount_received": 2500,
            "currency": "usd",
            "status": "succeeded",
            "transfer_data": None,
            "on_behalf_of": None,
        }

        with patch.object(inbox, "_connect") as connect:
            for kwargs in (
                dict(
                    inbox=None,
                    journal=self.journal,
                    claim=claim,
                    operation=self.operation,
                ),
                dict(
                    inbox=inbox,
                    journal=None,
                    claim=claim,
                    operation=self.operation,
                ),
                dict(
                    inbox=inbox,
                    journal=self.journal,
                    claim=None,
                    operation=self.operation,
                ),
                dict(
                    inbox=inbox,
                    journal=self.journal,
                    claim=claim,
                    operation=None,
                ),
            ):
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                    StripeReadbackError,
                    "Trusted inbox, journal, readback claim and payment operation are required.",
                ):
                    accept_stripe_readback(
                        kwargs["inbox"],  # type: ignore[arg-type]
                        kwargs["journal"],  # type: ignore[arg-type]
                        kwargs["claim"],  # type: ignore[arg-type]
                        kwargs["operation"],  # type: ignore[arg-type]
                        retrieved_account="acct_synthetic",
                        intent=intent,
                    )
            connect.assert_not_called()

        valid_delivery = VerifiedDelivery(NOW, "a" * 64)
        self.assertTrue(valid_delivery.requires_readback)
        with self.assertRaises(FrozenInstanceError):
            valid_delivery.requires_readback = False  # type: ignore[misc]

        for bad_ts in (-1, True, 1.5, "1700000000", None, 2**63):
            with self.subTest(timestamp=bad_ts), self.assertRaises(
                StripeDeliveryError
            ):
                VerifiedDelivery(bad_ts, "a" * 64)  # type: ignore[arg-type]
        for bad_digest in ("", "A" * 64, "a" * 63, "a" * 65, "g" * 64, None, 123):
            with self.subTest(payload_sha256=bad_digest), self.assertRaises(
                StripeDeliveryError
            ):
                VerifiedDelivery(NOW, bad_digest)  # type: ignore[arg-type]
        for bad_flag in (False, 1, 0, None, "true"):
            with self.subTest(requires_readback=bad_flag), self.assertRaises(
                StripeDeliveryError
            ):
                VerifiedDelivery(NOW, "a" * 64, bad_flag)  # type: ignore[arg-type]

    def test_approval_status_state_at_and_provenance_properties(self) -> None:
        active_status = PaymentApprovalStatus(
            self.operation.fingerprint, APPROVAL_EXPIRY, "active"
        )
        revoked_status = PaymentApprovalStatus(
            self.operation.fingerprint, APPROVAL_EXPIRY, "revoked"
        )
        self.assertEqual(active_status.state_at(0), "active")
        self.assertEqual(active_status.state_at(APPROVAL_EXPIRY - 1), "active")
        self.assertEqual(active_status.state_at(APPROVAL_EXPIRY), "expired")
        self.assertEqual(active_status.state_at(APPROVAL_EXPIRY + 10), "expired")
        self.assertEqual(revoked_status.state_at(0), "revoked")
        self.assertEqual(revoked_status.state_at(APPROVAL_EXPIRY + 10), "revoked")

        for bad_now in (-1, True, False, 1.5, "1700000000", None, 2**63):
            with self.subTest(now=bad_now), self.assertRaisesRegex(
                PaymentApprovalError, "nonnegative signed-64-bit integer"
            ):
                active_status.state_at(bad_now)  # type: ignore[arg-type]

        # Direct reservation provenance properties
        self.journal.reserve(self.operation)
        direct_prov = self.approvals.read_provenance(self.journal, self.operation)
        self.assertEqual(direct_prov.path, "direct_reservation")
        self.assertEqual(direct_prov.attempt_phase, "reserved_unassociated")

        signers = MerchantSignerStore(self.path)
        op_prov = signers.read_provenance(self.approvals, self.journal, self.operation)
        self.assertEqual(op_prov.path, "direct_reservation")
        self.assertEqual(op_prov.attempt_phase, "reserved_unassociated")

        self.journal.reconcile(
            self.operation, observation="pending", provider_reference="pi_pending"
        )
        self.assertEqual(
            self.approvals.read_provenance(self.journal, self.operation).attempt_phase,
            "pending_associated",
        )
        self.assertEqual(
            signers.read_provenance(
                self.approvals, self.journal, self.operation
            ).attempt_phase,
            "pending_associated",
        )

        self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_pending"
        )
        self.assertEqual(
            self.approvals.read_provenance(self.journal, self.operation).attempt_phase,
            "succeeded_terminal",
        )
        self.assertEqual(
            signers.read_provenance(
                self.approvals, self.journal, self.operation
            ).attempt_phase,
            "succeeded_terminal",
        )

    def test_payment_approval_preview_admit_single_select_and_non_backfill(
        self,
    ) -> None:
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        body, digest = self._body_and_digest(self.operation)
        bare = RequestSignatureSnapshot(
            "sig1",
            "key-2026-11",
            MUTATION_COMPONENTS,
            "POST",
            TARGET_URI,
            "application/json",
            digest,
        )

        statements: list[str] = []
        orig_connect = self.approvals._connect

        def traced_connect() -> sqlite3.Connection:
            db = orig_connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.approvals, "_connect", side_effect=traced_connect):
            preview = self.approvals.preview_admit(
                self.journal,
                self.operation,
                bare,
                now=NOW,
                expected_target_uri=TARGET_URI,
                method="POST",
                target_uri=TARGET_URI,
                content_type="application/json",
                content_digest=digest,
                content_encoding=None,
                body=body,
            )
        sql_Only = [
            s.strip().upper()
            for s in statements
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_Only), 1)
        self.assertTrue(sql_Only[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_Only[0])

        self.assertTrue(preview.dispatch_allowed)
        self.assertTrue(preview.would_record_admission)
        self.assertEqual(preview.attempt_phase, "reserved_unassociated")
        self.assertIsNone(preview.existing_attempt)
        self.assertIsNone(preview.existing_admission)
        self.assertEqual(
            preview.projected_admission,
            ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY),
        )
        self.assertIsNone(self.journal.read_attempt(self.operation))

        # After real admit(), preview_admit() reports retry denial and preserves existing_admission
        decision = self.approvals.admit(
            self.journal,
            self.operation,
            bare,
            clock=lambda: NOW,
            expected_target_uri=TARGET_URI,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertEqual(decision, preview.decision)
        retry_preview = self.approvals.preview_admit(
            self.journal,
            self.operation,
            bare,
            now=NOW + 5,
            expected_target_uri=TARGET_URI,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertFalse(retry_preview.dispatch_allowed)
        self.assertFalse(retry_preview.would_record_admission)
        self.assertEqual(
            retry_preview.existing_admission,
            ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY),
        )
        self.assertEqual(
            retry_preview.projected_admission,
            ApprovalAdmission(self.operation.fingerprint, NOW, APPROVAL_EXPIRY),
        )

        # Legacy direct reservation does not backfill admission in preview_admit()
        legacy_op = replace(
            self.operation,
            operation_id="op-legacy",
            approval_id="approval-legacy",
            idempotency_key="idem-legacy",
        )
        self.approvals.approve(legacy_op, expires_at=APPROVAL_EXPIRY)
        self.journal.reserve(legacy_op)
        legacy_body, legacy_digest = self._body_and_digest(legacy_op)
        legacy_sig = replace(bare, content_digest=legacy_digest)
        legacy_preview = self.approvals.preview_admit(
            self.journal,
            legacy_op,
            legacy_sig,
            now=NOW,
            expected_target_uri=TARGET_URI,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=legacy_digest,
            content_encoding=None,
            body=legacy_body,
        )
        self.assertFalse(legacy_preview.dispatch_allowed)
        self.assertFalse(legacy_preview.would_record_admission)
        self.assertIsNone(legacy_preview.existing_admission)
        self.assertIsNone(legacy_preview.projected_admission)

        # Expiration, revocation, and conflicts in preview_admit()
        with self.assertRaisesRegex(PaymentApprovalError, "Approval is expired"):
            self.approvals.preview_admit(
                self.journal,
                self.operation,
                bare,
                now=APPROVAL_EXPIRY,
                expected_target_uri=TARGET_URI,
                method="POST",
                target_uri=TARGET_URI,
                content_type="application/json",
                content_digest=digest,
                content_encoding=None,
                body=body,
            )
        self.approvals.revoke(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "Approval is revoked"):
            self.approvals.preview_admit(
                self.journal,
                self.operation,
                bare,
                now=NOW,
                expected_target_uri=TARGET_URI,
                method="POST",
                target_uri=TARGET_URI,
                content_type="application/json",
                content_digest=digest,
                content_encoding=None,
                body=body,
            )

    def test_merchant_signer_preview_admit_single_select_and_paths(self) -> None:
        signers = MerchantSignerStore(self.path)
        scope = MerchantSignerScope(
            "tenant-a", "synthetic-shop", TARGET_URI, "key-2026-11"
        )
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        signers.allow(scope)
        body, digest = self._body_and_digest(self.operation)
        bare = RequestSignatureSnapshot(
            "sig1",
            scope.key_id,
            MUTATION_COMPONENTS,
            "POST",
            TARGET_URI,
            "application/json",
            digest,
        )
        timed = TimedRequestSignatureSnapshot(bare, SIG_CREATED, SIG_EXPIRES)

        # Bare signature preview
        bare_preview = signers.preview_admit(
            scope,
            self.approvals,
            self.journal,
            self.operation,
            bare,
            now=NOW,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertTrue(bare_preview.dispatch_allowed)
        self.assertTrue(bare_preview.would_record_approval_admission)
        self.assertFalse(bare_preview.would_record_timed_admission)
        self.assertIsNone(bare_preview.projected_timed_admission)
        self.assertEqual(bare_preview.projected_path, "approval_admission")

        # Timed signature preview in single SELECT
        statements: list[str] = []
        orig_connect = signers._connect

        def traced_connect() -> sqlite3.Connection:
            db = orig_connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(signers, "_connect", side_effect=traced_connect):
            timed_preview = signers.preview_admit(
                scope,
                self.approvals,
                self.journal,
                self.operation,
                timed,
                now=NOW,
                method="POST",
                target_uri=TARGET_URI,
                content_type="application/json",
                content_digest=digest,
                content_encoding=None,
                body=body,
            )
        sql_only = [
            s.strip().upper()
            for s in statements
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_only), 1)
        self.assertTrue(sql_only[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_only[0])

        self.assertTrue(timed_preview.dispatch_allowed)
        self.assertTrue(timed_preview.would_record_approval_admission)
        self.assertTrue(timed_preview.would_record_timed_admission)
        self.assertEqual(timed_preview.projected_path, "timed_signer_admission")
        self.assertEqual(
            timed_preview.projected_timed_admission,
            TimedSignerAdmission(
                self.operation.fingerprint,
                scope,
                "sig1",
                SIG_CREATED,
                SIG_EXPIRES,
                NOW,
            ),
        )
        self.assertIsNone(self.journal.read_attempt(self.operation))

        # Timed signature window rejection in preview_admit()
        for bad_now in (SIG_CREATED - 1, SIG_EXPIRES):
            with self.subTest(bad_now=bad_now), self.assertRaises(RequestBindingError):
                signers.preview_admit(
                    scope,
                    self.approvals,
                    self.journal,
                    self.operation,
                    timed,
                    now=bad_now,
                    method="POST",
                    target_uri=TARGET_URI,
                    content_type="application/json",
                    content_digest=digest,
                    content_encoding=None,
                    body=body,
                )

        # Real timed admit() matches preview, and retry preview never backfills or mutates
        decision = signers.admit(
            scope,
            self.approvals,
            self.journal,
            self.operation,
            timed,
            clock=lambda: NOW,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertEqual(decision, timed_preview.decision)
        retry_preview = signers.preview_admit(
            scope,
            self.approvals,
            self.journal,
            self.operation,
            timed,
            now=NOW + 5,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=digest,
            content_encoding=None,
            body=body,
        )
        self.assertFalse(retry_preview.dispatch_allowed)
        self.assertFalse(retry_preview.would_record_approval_admission)
        self.assertFalse(retry_preview.would_record_timed_admission)
        self.assertEqual(retry_preview.projected_path, "timed_signer_admission")
        self.assertEqual(
            retry_preview.projected_timed_admission,
            timed_preview.projected_timed_admission,
        )

        # Revoked signer fails closed in preview_admit()
        signers.revoke(scope)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            signers.preview_admit(
                scope,
                self.approvals,
                self.journal,
                self.operation,
                timed,
                now=NOW,
                method="POST",
                target_uri=TARGET_URI,
                content_type="application/json",
                content_digest=digest,
                content_encoding=None,
                body=body,
            )

    def test_approval_and_signer_preview_revoke_single_select_and_invariants(
        self,
    ) -> None:
        signers = MerchantSignerStore(self.path)
        scope = MerchantSignerScope(
            "tenant-a", "synthetic-shop", TARGET_URI, "key-2026-11"
        )
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        signers.allow(scope)

        # 1. PaymentApprovalStore.preview_revoke() executes a single lock-free SELECT
        app_stmts: list[str] = []
        orig_app_connect = self.approvals._connect

        def traced_app_connect() -> sqlite3.Connection:
            db = orig_app_connect()
            db.set_trace_callback(app_stmts.append)
            return db

        with patch.object(self.approvals, "_connect", side_effect=traced_app_connect):
            app_rev = self.approvals.preview_revoke(self.operation)
        sql_app = [
            s.strip().upper()
            for s in app_stmts
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_app), 1)
        self.assertTrue(sql_app[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_app[0])

        self.assertTrue(app_rev.would_revoke)
        self.assertEqual(app_rev.existing_status.state, "active")
        self.assertEqual(app_rev.projected_status.state, "revoked")
        self.assertEqual(
            self.approvals.read_approval(self.operation),
            PaymentApprovalStatus(
                self.operation.fingerprint, APPROVAL_EXPIRY, "active"
            ),
        )

        # After revoke(), preview_revoke() is idempotent with would_revoke=False
        self.approvals.revoke(self.operation)
        app_rev_after = self.approvals.preview_revoke(self.operation)
        self.assertFalse(app_rev_after.would_revoke)
        self.assertEqual(app_rev_after.existing_status.state, "revoked")
        self.assertEqual(app_rev_after.projected_status.state, "revoked")

        # Unknown or mismatched operation raises PaymentApprovalError
        unknown_op = replace(self.operation, approval_id="unknown-app")
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.approvals.preview_revoke(unknown_op)
        drift_op = replace(
            self.operation,
            checkout=replace(self.operation.checkout, amount=9999),
        )
        with self.assertRaisesRegex(PaymentApprovalError, "differs from the bound"):
            self.approvals.preview_revoke(drift_op)

        # ApprovalRevocationPreview dataclass invariants
        for bad_app_kwargs in (
            {"operation": "bad"},
            {"existing_status": "bad"},
            {"projected_status": app_rev.existing_status},
            {"would_revoke": 1},
            {"would_revoke": False},
        ):
            with self.subTest(bad_app_kwargs=bad_app_kwargs):
                with self.assertRaises(PaymentApprovalError):
                    replace(app_rev, **bad_app_kwargs)  # type: ignore[arg-type]

        # 2. MerchantSignerStore.preview_revoke() executes a single lock-free SELECT
        sig_stmts: list[str] = []
        orig_sig_connect = signers._connect

        def traced_sig_connect() -> sqlite3.Connection:
            db = orig_sig_connect()
            db.set_trace_callback(sig_stmts.append)
            return db

        with patch.object(signers, "_connect", side_effect=traced_sig_connect):
            sig_rev = signers.preview_revoke(scope)
        sql_sig = [
            s.strip().upper()
            for s in sig_stmts
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_sig), 1)
        self.assertTrue(sql_sig[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_sig[0])

        self.assertTrue(sig_rev.would_revoke)
        self.assertEqual(sig_rev.existing_status.state, "active")
        self.assertEqual(sig_rev.projected_status.state, "revoked")
        self.assertEqual(
            signers.read_permission(scope),
            MerchantSignerPermissionStatus(scope, "active"),
        )

        # After revoke(), preview_revoke() is idempotent with would_revoke=False
        signers.revoke(scope)
        sig_rev_after = signers.preview_revoke(scope)
        self.assertFalse(sig_rev_after.would_revoke)
        self.assertEqual(sig_rev_after.existing_status.state, "revoked")
        self.assertEqual(sig_rev_after.projected_status.state, "revoked")

        # Unknown scope raises MerchantSignerError
        unknown_scope = replace(scope, key_id="unknown-key")
        with self.assertRaisesRegex(MerchantSignerError, "No recorded signer"):
            signers.preview_revoke(unknown_scope)

        # SignerRevocationPreview dataclass invariants
        for bad_sig_kwargs in (
            {"scope": "bad"},
            {"existing_status": "bad"},
            {"projected_status": sig_rev.existing_status},
            {"would_revoke": 1},
            {"would_revoke": False},
        ):
            with self.subTest(bad_sig_kwargs=bad_sig_kwargs):
                with self.assertRaises(MerchantSignerError):
                    replace(sig_rev, **bad_sig_kwargs)  # type: ignore[arg-type]

        # 3. PaymentApprovalStore.preview_approve() and MerchantSignerStore.preview_allow()
        fresh_op = replace(self.operation, approval_id="fresh-approval", operation_id="fresh-op")
        fresh_scope = replace(scope, key_id="fresh-key-2026-11")

        grant_app_stmts: list[str] = []

        def traced_grant_app_connect() -> sqlite3.Connection:
            db = orig_app_connect()
            db.set_trace_callback(grant_app_stmts.append)
            return db

        with patch.object(self.approvals, "_connect", side_effect=traced_grant_app_connect):
            app_grant = self.approvals.preview_approve(fresh_op, expires_at=APPROVAL_EXPIRY)
        sql_grant_app = [
            s.strip().upper()
            for s in grant_app_stmts
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_grant_app), 1)
        self.assertTrue(sql_grant_app[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_grant_app[0])

        self.assertTrue(app_grant.would_record)
        self.assertEqual(
            app_grant.projected_status,
            PaymentApprovalStatus(fresh_op.fingerprint, APPROVAL_EXPIRY, "active"),
        )
        self.assertIsNone(self.approvals.read_approval(fresh_op))

        # Duplicate approval fails closed in preview_approve()
        with self.assertRaisesRegex(PaymentApprovalError, "already recorded"):
            self.approvals.preview_approve(self.operation, expires_at=APPROVAL_EXPIRY)

        for bad_grant_app_kwargs in (
            {"operation": "bad"},
            {"expires_at": 0},
            {"projected_status": app_rev.projected_status},
            {"would_record": False},
            {"would_record": 1},
        ):
            with self.subTest(bad_grant_app_kwargs=bad_grant_app_kwargs):
                with self.assertRaises(PaymentApprovalError):
                    replace(app_grant, **bad_grant_app_kwargs)  # type: ignore[arg-type]

        grant_sig_stmts: list[str] = []

        def traced_grant_sig_connect() -> sqlite3.Connection:
            db = orig_sig_connect()
            db.set_trace_callback(grant_sig_stmts.append)
            return db

        with patch.object(signers, "_connect", side_effect=traced_grant_sig_connect):
            sig_grant = signers.preview_allow(fresh_scope)
        sql_grant_sig = [
            s.strip().upper()
            for s in grant_sig_stmts
            if not s.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(sql_grant_sig), 1)
        self.assertTrue(sql_grant_sig[0].startswith("SELECT"))
        for kw in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(kw, sql_grant_sig[0])

        self.assertTrue(sig_grant.would_record)
        self.assertEqual(
            sig_grant.projected_status,
            MerchantSignerPermissionStatus(fresh_scope, "active"),
        )
        self.assertIsNone(signers.read_permission(fresh_scope))

        # Duplicate signer scope fails closed in preview_allow()
        with self.assertRaisesRegex(MerchantSignerError, "already recorded"):
            signers.preview_allow(scope)

        for bad_grant_sig_kwargs in (
            {"scope": "bad"},
            {"projected_status": sig_rev.projected_status},
            {"would_record": False},
            {"would_record": 1},
        ):
            with self.subTest(bad_grant_sig_kwargs=bad_grant_sig_kwargs):
                with self.assertRaises(MerchantSignerError):
                    replace(sig_grant, **bad_grant_sig_kwargs)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
