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
    MerchantSignerPermissionStatus,
    MerchantSignerScope,
    MerchantSignerStore,
    OperationAdmissionProvenance,
    TimedSignerAdmission,
)
from lab.payment_approvals import (
    ApprovalAdmission,
    PaymentApprovalStatus,
    PaymentApprovalStore,
)
from lab.payment_attempts import (
    AttemptConflict,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import (
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)
from lab.stripe_inbox import (
    InboxReceipt,
    ReadbackClaim,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxError,
    StripeInboxScope,
)
from lab.stripe_observation import associate_stripe_intent
from lab.stripe_readback import (
    StripeLifecycleProvenance,
    StripeReadbackError,
    StripeReadbackProvenance,
    accept_stripe_readback,
    find_stripe_lifecycle_provenance,
    read_stripe_lifecycle_provenance,
    read_stripe_readback_provenance,
)
from tests.test_stripe_inbox import NOW, SECRET, event_body, header

TARGET_URI = "https://shop-a.example/checkout?cart=1"


class StripeLifecycleProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "stripe_lifecycle_provenance.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.scope = StripeInboxScope(
            tenant_id="tenant-a",
            endpoint_id="ep-1",
            provider_account="acct_synthetic",
            livemode=False,
        )
        self.operation = PaymentOperation(
            tenant_id="tenant-a",
            operation_id="op-1",
            approval_id="app-1",
            provider="stripe:test",
            provider_account="acct_synthetic",
            idempotency_key="idem-1",
            checkout=Checkout("shop-a", "USD", "sku-1", 1, 1000),
        )
        self.signer_scope = MerchantSignerScope(
            tenant_id="tenant-a",
            merchant="shop-a",
            target_uri=TARGET_URI,
            key_id="key-1",
        )
        self.body = json.dumps(asdict(self.operation.checkout), sort_keys=True).encode("utf-8")
        self.digest = compute_rfc9530_content_digest(self.body)
        self.signature = RequestSignatureSnapshot(
            signature_label="sig1",
            key_id="key-1",
            covered_components=MUTATION_COMPONENTS,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=self.digest,
        )
        self.timed_signature = TimedRequestSignatureSnapshot(
            signature=self.signature,
            created=100,
            expires=300,
        )
        self.intent = {
            "object": "payment_intent",
            "id": "pi_synthetic",
            "livemode": False,
            "amount": 1000,
            "amount_received": 1000,
            "currency": "usd",
            "status": "succeeded",
            "transfer_data": None,
            "on_behalf_of": None,
        }

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def record_webhook(
        self,
        event_id: str = "evt_synthetic",
        *,
        scope: StripeInboxScope | None = None,
        reference: str = "pi_synthetic",
    ) -> InboxReceipt:
        target_scope = self.scope if scope is None else scope
        body = event_body(event_id, reference=reference, live=target_scope.livemode)
        return self.inbox.record(target_scope, body, header(body), SECRET, now=NOW).receipt

    def test_seven_table_timed_signer_to_readback_acceptance_and_revocation_lifecycle(self) -> None:
        # 1. Empty across all 7 tables -> find returns None, read raises
        self.assertIsNone(
            find_stripe_lifecycle_provenance(
                self.inbox,
                self.journal,
                self.approvals,
                self.scope,
                "evt_synthetic",
                self.operation,
                signers=self.signers,
            )
        )
        with self.assertRaisesRegex(StripeReadbackError, "No lifecycle provenance exists"):
            read_stripe_lifecycle_provenance(
                self.inbox,
                self.journal,
                self.approvals,
                self.scope,
                "evt_synthetic",
                self.operation,
                signers=self.signers,
            )

        # 2. Pre-staged approval before admission or webhook -> approval_status visible, admission_path is None
        self.approvals.approve(self.operation, expires_at=500)
        self.signers.allow(self.signer_scope)
        staged = read_stripe_lifecycle_provenance(
            self.inbox,
            self.journal,
            self.approvals,
            self.scope,
            "evt_synthetic",
            self.operation,
            signers=self.signers,
        )
        self.assertEqual(
            staged,
            StripeLifecycleProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=None,
                approval_status=PaymentApprovalStatus(self.operation.fingerprint, 500, "active"),
                approval_admission=None,
                signer_permission=None,
                timed_signer_admission=None,
                receipt=None,
                claim_status=None,
            ),
        )
        self.assertIsNone(staged.admission_path)
        self.assertIsNone(staged.admission_provenance)
        self.assertIsNone(staged.readback_provenance)

        # 3. Timed-signer admission reserves attempt + records payment_admissions + merchant_timed_admissions
        decision = self.signers.admit(
            self.signer_scope,
            self.approvals,
            self.journal,
            self.operation,
            self.timed_signature,
            clock=lambda: 150,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=self.digest,
            content_encoding=None,
            body=self.body,
        )
        self.assertTrue(decision.dispatch_allowed)

        expected_approval_adm = ApprovalAdmission(self.operation.fingerprint, 150, 500)
        expected_timed_adm = TimedSignerAdmission(
            self.operation.fingerprint,
            self.signer_scope,
            "sig1",
            100,
            300,
            150,
        )
        admitted = read_stripe_lifecycle_provenance(
            self.inbox,
            self.journal,
            self.approvals,
            self.scope,
            "evt_synthetic",
            self.operation,
            signers=self.signers,
        )
        self.assertEqual(admitted.admission_path, "timed_signer_admission")
        self.assertEqual(
            admitted,
            StripeLifecycleProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", None),
                approval_status=PaymentApprovalStatus(self.operation.fingerprint, 500, "active"),
                approval_admission=expected_approval_adm,
                signer_permission=MerchantSignerPermissionStatus(self.signer_scope, "active"),
                timed_signer_admission=expected_timed_adm,
                receipt=None,
                claim_status=None,
            ),
        )
        self.assertEqual(
            admitted.admission_provenance,
            OperationAdmissionProvenance(
                self.operation.fingerprint,
                PaymentAttempt("unknown", None),
                expected_approval_adm,
                expected_timed_adm,
            ),
        )
        self.assertEqual(
            admitted.readback_provenance,
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", None),
                receipt=None,
                claim_status=None,
            ),
        )

        # 4. Outbound PaymentIntent association + inbound webhook receipt + claim + handoff + acceptance
        associate_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**self.intent, "status": "processing", "amount_received": 0},
        )
        receipt = self.record_webhook("evt_synthetic", reference="pi_synthetic")
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None
        handed_off = self.inbox.handoff(claim, "worker-b")
        accepted = accept_stripe_readback(
            self.inbox,
            self.journal,
            handed_off,
            self.operation,
            retrieved_account="acct_synthetic",
            intent=self.intent,
        )
        self.assertEqual(accepted, PaymentAttempt("succeeded", "pi_synthetic"))

        # 5. Revoke both operator approval and merchant signer permission after acceptance
        self.approvals.revoke(self.operation)
        self.signers.revoke(self.signer_scope)

        statements: list[str] = []
        original_connect = self.inbox._connect

        def traced_connect() -> sqlite3.Connection:
            db = original_connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.inbox, "_connect", side_effect=traced_connect):
            final_prov = read_stripe_lifecycle_provenance(
                self.inbox,
                self.journal,
                self.approvals,
                self.scope,
                "evt_synthetic",
                self.operation,
                signers=self.signers,
            )

        self.assertEqual(
            final_prov,
            StripeLifecycleProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("succeeded", "pi_synthetic"),
                approval_status=PaymentApprovalStatus(self.operation.fingerprint, 500, "revoked"),
                approval_admission=expected_approval_adm,
                signer_permission=MerchantSignerPermissionStatus(self.signer_scope, "revoked"),
                timed_signer_admission=expected_timed_adm,
                receipt=receipt,
                claim_status=ReadbackClaimStatus(handed_off, "handled"),
            ),
        )
        self.assertEqual(final_prov.admission_path, "timed_signer_admission")
        self.assertEqual(
            final_prov.admission_provenance,
            self.signers.read_provenance(self.approvals, self.journal, self.operation),
        )
        self.assertEqual(
            final_prov.readback_provenance,
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            ),
        )
        select_statements = [
            stmt.strip()
            for stmt in statements
            if not stmt.strip().upper().startswith("PRAGMA")
        ]
        self.assertEqual(len(select_statements), 1)
        self.assertTrue(select_statements[0].upper().startswith("SELECT"))
        for forbidden in ("BEGIN", "INSERT", "UPDATE", "DELETE"):
            self.assertNotIn(forbidden, select_statements[0].upper())
        with self.assertRaises(FrozenInstanceError):
            final_prov.event_id = "evt_mutated"  # type: ignore[misc]

    def test_five_table_mode_supports_direct_reservation_approval_admission_and_early_webhook(self) -> None:
        # Use a fresh SQLite file where MerchantSignerStore is never instantiated
        five_table_path = Path(self.tempdir.name) / "five_table_only.sqlite3"
        inbox = StripeEventInbox(five_table_path)
        journal = PaymentAttemptJournal(five_table_path)
        approvals = PaymentApprovalStore(five_table_path)

        # 1. Early webhook before reservation
        early_op = replace(
            self.operation,
            operation_id="op-early",
            approval_id="app-early",
            idempotency_key="idem-early",
        )
        early_receipt = self.inbox.record(
            self.scope,
            event_body("evt_early", reference="pi_early", live=False),
            header(event_body("evt_early", reference="pi_early", live=False)),
            SECRET,
            now=NOW,
        ).receipt
        # Record on five_table_path inbox too
        body_early = event_body("evt_early", reference="pi_early", live=False)
        early_receipt = inbox.record(self.scope, body_early, header(body_early), SECRET, now=NOW).receipt
        early_prov = read_stripe_lifecycle_provenance(
            inbox, journal, approvals, self.scope, "evt_early", early_op
        )
        self.assertIsNone(early_prov.admission_path)
        self.assertIsNone(early_prov.attempt)
        self.assertEqual(early_prov.receipt, early_receipt)

        # 2. Direct reservation (no approval record)
        direct_op = replace(
            self.operation,
            operation_id="op-direct",
            approval_id="app-direct",
            idempotency_key="idem-direct",
        )
        journal.reserve(direct_op)
        direct_prov = read_stripe_lifecycle_provenance(
            inbox, journal, approvals, self.scope, "evt_direct", direct_op
        )
        self.assertEqual(direct_prov.admission_path, "direct_reservation")
        self.assertEqual(direct_prov.attempt, PaymentAttempt("unknown", None))
        self.assertIsNone(direct_prov.approval_status)
        self.assertIsNone(direct_prov.approval_admission)
        self.assertIsNone(direct_prov.signer_permission)
        self.assertIsNone(direct_prov.timed_signer_admission)

        # 3. Approval admission (5-table mode without MerchantSignerStore)
        approvals.approve(self.operation, expires_at=400)
        decision = approvals.admit(
            journal,
            self.operation,
            self.signature,
            clock=lambda: 120,
            expected_target_uri=TARGET_URI,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=self.digest,
            content_encoding=None,
            body=self.body,
        )
        self.assertTrue(decision.dispatch_allowed)
        app_prov = read_stripe_lifecycle_provenance(
            inbox, journal, approvals, self.scope, "evt_synthetic", self.operation
        )
        self.assertEqual(app_prov.admission_path, "approval_admission")
        self.assertEqual(
            app_prov.approval_status,
            PaymentApprovalStatus(self.operation.fingerprint, 400, "active"),
        )
        self.assertEqual(
            app_prov.approval_admission,
            ApprovalAdmission(self.operation.fingerprint, 120, 400),
        )
        self.assertIsNone(app_prov.signer_permission)
        self.assertIsNone(app_prov.timed_signer_admission)

    def test_store_scope_and_type_boundaries_fail_closed(self) -> None:
        other_path = Path(self.tempdir.name) / "other.sqlite3"
        other_inbox = StripeEventInbox(other_path)
        other_journal = PaymentAttemptJournal(other_path)
        other_approvals = PaymentApprovalStore(other_path)
        other_signers = MerchantSignerStore(other_path)

        for bad_kwargs, pattern in (
            (
                {"inbox": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"journal": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"approvals": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"scope": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"operation": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"signers": "bad"},  # type: ignore[dict-item]
                "Trusted inbox, journal, approvals, inbox scope and payment operation",
            ),
            (
                {"inbox": other_inbox},
                "same resolved SQLite file",
            ),
            (
                {"journal": other_journal},
                "same resolved SQLite file",
            ),
            (
                {"approvals": other_approvals},
                "same resolved SQLite file",
            ),
            (
                {"signers": other_signers},
                "same resolved SQLite file",
            ),
            (
                {"scope": replace(self.scope, tenant_id="tenant-b")},
                "Inbox scope differs from the bound payment operation",
            ),
            (
                {"scope": replace(self.scope, provider_account="acct_other")},
                "Inbox scope differs from the bound payment operation",
            ),
            (
                {"scope": replace(self.scope, livemode=True)},
                "Inbox scope differs from the bound payment operation",
            ),
        ):
            kwargs = {
                "inbox": self.inbox,
                "journal": self.journal,
                "approvals": self.approvals,
                "scope": self.scope,
                "event_id": "evt_synthetic",
                "operation": self.operation,
                "signers": self.signers,
                **bad_kwargs,
            }
            with self.subTest(bad_kwargs=bad_kwargs):
                with self.assertRaisesRegex(StripeReadbackError, pattern):
                    find_stripe_lifecycle_provenance(**kwargs)  # type: ignore[arg-type]

        for bad_event_id in ("pi_123", "evt_", " evt_1", ""):
            with self.subTest(bad_event_id=bad_event_id):
                with self.assertRaisesRegex(StripeInboxError, "Event ID"):
                    find_stripe_lifecycle_provenance(
                        self.inbox,
                        self.journal,
                        self.approvals,
                        self.scope,
                        bad_event_id,
                        self.operation,
                    )

        hardlink_path = Path(self.tempdir.name) / "hardlink_lifecycle.sqlite3"
        try:
            os.link(self.path, hardlink_path)
        except OSError:
            pass
        else:
            hardlink_journal = PaymentAttemptJournal(hardlink_path)
            with self.assertRaisesRegex(StripeReadbackError, "same resolved SQLite file"):
                find_stripe_lifecycle_provenance(
                    self.inbox,
                    hardlink_journal,
                    self.approvals,
                    self.scope,
                    "evt_synthetic",
                    self.operation,
                )

    def test_cross_plane_corruption_and_binding_drift_fail_closed(self) -> None:
        self.approvals.approve(self.operation, expires_at=500)
        self.signers.allow(self.signer_scope)
        self.signers.admit(
            self.signer_scope,
            self.approvals,
            self.journal,
            self.operation,
            self.timed_signature,
            clock=lambda: 150,
            method="POST",
            target_uri=TARGET_URI,
            content_type="application/json",
            content_digest=self.digest,
            content_encoding=None,
            body=self.body,
        )
        associate_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**self.intent, "status": "processing", "amount_received": 0},
        )
        self.record_webhook("evt_synthetic", reference="pi_synthetic")
        self.inbox.claim_next(self.scope, "worker-a")

        # 1. Caller operation binding drift against reserved payment_attempts row
        for drifted_op in (
            replace(self.operation, approval_id="app-other"),
            replace(self.operation, idempotency_key="idem-other"),
            replace(self.operation, checkout=Checkout("shop-a", "USD", "sku-1", 1, 9999)),
        ):
            with self.subTest(drifted_op=drifted_op):
                with self.assertRaisesRegex(
                    AttemptConflict, "Operation binding differs from the reserved attempt"
                ):
                    find_stripe_lifecycle_provenance(
                        self.inbox,
                        self.journal,
                        self.approvals,
                        self.scope,
                        "evt_synthetic",
                        drifted_op,
                        signers=self.signers,
                    )

        # 2. Conflicting PaymentIntent IDs between journal and webhook receipt
        self.record_webhook("evt_other_pi", reference="pi_other")
        with self.assertRaisesRegex(
            StripeReadbackError, "Receipt differs from the trusted PaymentIntent association"
        ):
            find_stripe_lifecycle_provenance(
                self.inbox,
                self.journal,
                self.approvals,
                self.scope,
                "evt_other_pi",
                self.operation,
                signers=self.signers,
            )

        # 3. Direct SQLite corruption across the 7 joined tables
        baseline_bytes = self.path.read_bytes()

        def run_with_mutation(sql: str, params: tuple[object, ...] = ()) -> None:
            try:
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(sql, params)
                find_stripe_lifecycle_provenance(
                    self.inbox,
                    self.journal,
                    self.approvals,
                    self.scope,
                    "evt_synthetic",
                    self.operation,
                    signers=self.signers,
                )
            finally:
                self.path.write_bytes(baseline_bytes)

        for sql, params, exc_type, pattern in (
            (
                "UPDATE payment_approvals SET fingerprint = ? WHERE approval_id = 'app-1'",
                ("0" * 64,),
                StripeReadbackError,
                "Approval record differs from the bound operation",
            ),
            (
                "UPDATE payment_approvals SET expires_at = 'bad' WHERE approval_id = 'app-1'",
                (),
                StripeReadbackError,
                "Stored approval expiry is invalid",
            ),
            (
                "UPDATE payment_approvals SET revoked = 'bad' WHERE approval_id = 'app-1'",
                (),
                StripeReadbackError,
                "Stored approval revocation state is invalid",
            ),
            (
                "UPDATE payment_admissions SET fingerprint = ? WHERE operation_id = 'op-1'",
                ("0" * 64,),
                StripeReadbackError,
                "Approval admission record differs from the bound operation",
            ),
            (
                "DELETE FROM payment_attempts WHERE operation_id = 'op-1'",
                (),
                StripeReadbackError,
                "Orphan approval admission record exists without a reserved payment attempt",
            ),
            (
                "DELETE FROM payment_approvals WHERE approval_id = 'app-1'",
                (),
                StripeReadbackError,
                "Orphan approval admission record exists without a recorded approval",
            ),
            (
                "UPDATE payment_approvals SET expires_at = 999 WHERE approval_id = 'app-1'",
                (),
                StripeReadbackError,
                "Approval admission expiry differs from recorded approval",
            ),
            (
                "UPDATE payment_admissions SET admitted_at = 'bad' WHERE operation_id = 'op-1'",
                (),
                StripeReadbackError,
                "Stored admission times are invalid",
            ),
            (
                "UPDATE merchant_timed_admissions SET fingerprint = ? WHERE operation_id = 'op-1'",
                ("0" * 64,),
                StripeReadbackError,
                "Timed-admission record differs from the bound operation",
            ),
            (
                "DELETE FROM payment_admissions WHERE operation_id = 'op-1'",
                (),
                StripeReadbackError,
                "Orphan timed-admission record exists without an approval admission",
            ),
            (
                "DELETE FROM merchant_signer_permissions WHERE key_id = 'key-1'",
                (),
                StripeReadbackError,
                "Orphan timed-admission record exists without a recorded signer permission",
            ),
            (
                "UPDATE merchant_signer_permissions SET revoked = 'bad' WHERE key_id = 'key-1'",
                (),
                StripeReadbackError,
                "Stored signer permission revocation state is invalid",
            ),
            (
                "UPDATE merchant_timed_admissions SET signature_label = 'BAD LABEL' WHERE operation_id = 'op-1'",
                (),
                StripeReadbackError,
                "Stored timed-admission signature label is invalid",
            ),
            (
                "UPDATE merchant_timed_admissions SET admitted_at = 160 WHERE operation_id = 'op-1'",
                (),
                StripeReadbackError,
                "Timed-admission clock sample differs from approval admission",
            ),
            (
                "DELETE FROM stripe_event_inbox WHERE event_id = 'evt_synthetic'",
                (),
                StripeInboxError,
                "Stored receipt event type is invalid",
            ),
        ):
            with self.subTest(sql=sql):
                with self.assertRaisesRegex(exc_type, pattern):
                    run_with_mutation(sql, params)

    def test_dataclass_post_init_rejects_inconsistent_lifecycle_structures(self) -> None:
        attempt = PaymentAttempt("unknown", "pi_synthetic")
        approval_status = PaymentApprovalStatus(self.operation.fingerprint, 500, "active")
        approval_adm = ApprovalAdmission(self.operation.fingerprint, 150, 500)
        signer_perm = MerchantSignerPermissionStatus(self.signer_scope, "active")
        timed_adm = TimedSignerAdmission(
            self.operation.fingerprint, self.signer_scope, "sig1", 100, 300, 150
        )
        receipt = InboxReceipt(
            "evt_synthetic", "payment_intent.succeeded", "pi_synthetic", "a" * 64
        )
        claim = ReadbackClaim(self.scope, receipt, "worker-a", 1)
        claim_status = ReadbackClaimStatus(claim, "active")

        base_kwargs: dict[str, object] = {
            "scope": self.scope,
            "event_id": "evt_synthetic",
            "fingerprint": self.operation.fingerprint,
            "attempt": attempt,
            "approval_status": approval_status,
            "approval_admission": approval_adm,
            "signer_permission": signer_perm,
            "timed_signer_admission": timed_adm,
            "receipt": receipt,
            "claim_status": claim_status,
        }

        for overrides, pattern in (
            ({"scope": "bad"}, "StripeInboxScope"),
            ({"event_id": "bad"}, "snapshot Event ID"),
            ({"fingerprint": "bad"}, "operation fingerprint is invalid"),
            ({"attempt": "bad"}, "PaymentAttempt or None"),
            ({"approval_status": "bad"}, "PaymentApprovalStatus or None"),
            ({"approval_admission": "bad"}, "ApprovalAdmission or None"),
            ({"signer_permission": "bad"}, "MerchantSignerPermissionStatus or None"),
            ({"timed_signer_admission": "bad"}, "TimedSignerAdmission or None"),
            ({"receipt": "bad"}, "InboxReceipt or None"),
            ({"claim_status": "bad"}, "ReadbackClaimStatus or None"),
            (
                {
                    "attempt": None,
                    "approval_status": None,
                    "approval_admission": None,
                    "signer_permission": None,
                    "timed_signer_admission": None,
                    "receipt": None,
                    "claim_status": None,
                },
                "requires at least one recorded lifecycle artifact",
            ),
            (
                {"approval_status": PaymentApprovalStatus("b" * 64, 500, "active")},
                "Approval record differs from the bound operation",
            ),
            (
                {"approval_admission": ApprovalAdmission("b" * 64, 150, 500)},
                "Approval admission record differs from the bound operation",
            ),
            (
                {"attempt": None},
                "Orphan approval admission record exists without a reserved payment attempt",
            ),
            (
                {"approval_status": None},
                "Orphan approval admission record exists without a recorded approval",
            ),
            (
                {"approval_admission": ApprovalAdmission(self.operation.fingerprint, 150, 499)},
                "Approval admission expiry differs from recorded approval",
            ),
            (
                {
                    "timed_signer_admission": TimedSignerAdmission(
                        "b" * 64, self.signer_scope, "sig1", 100, 300, 150
                    )
                },
                "Timed-admission record differs from the bound operation",
            ),
            (
                {"approval_admission": None},
                "Orphan timed-admission record exists without an approval admission",
            ),
            (
                {"signer_permission": None},
                "Orphan timed-admission record exists without a recorded signer permission",
            ),
            (
                {
                    "signer_permission": MerchantSignerPermissionStatus(
                        replace(self.signer_scope, key_id="key-2"), "active"
                    )
                },
                "Signer permission scope differs from timed-admission scope",
            ),
            (
                {
                    "signer_permission": MerchantSignerPermissionStatus(
                        replace(self.signer_scope, tenant_id="tenant-b"), "active"
                    ),
                    "timed_signer_admission": TimedSignerAdmission(
                        self.operation.fingerprint,
                        replace(self.signer_scope, tenant_id="tenant-b"),
                        "sig1",
                        100,
                        300,
                        150,
                    ),
                },
                "Timed-admission tenant differs from provenance scope",
            ),
            (
                {"timed_signer_admission": None},
                "Signer permission status requires a timed-admission route/key binding",
            ),
            (
                {"event_id": "evt_other"},
                "Receipt Event ID differs from the provenance lookup key",
            ),
            (
                {"receipt": None},
                "Readback claim status cannot exist without a recorded receipt",
            ),
            (
                {
                    "claim_status": ReadbackClaimStatus(
                        ReadbackClaim(
                            replace(self.scope, endpoint_id="ep-other"),
                            receipt,
                            "worker-a",
                            1,
                        ),
                        "active",
                    )
                },
                "Readback claim status does not match provenance scope or receipt",
            ),
            (
                {"attempt": PaymentAttempt("unknown", "pi_other")},
                "Receipt differs from the trusted PaymentIntent association",
            ),
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(StripeReadbackError, pattern):
                    StripeLifecycleProvenance(**{**base_kwargs, **overrides})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
