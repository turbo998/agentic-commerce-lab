from __future__ import annotations

from contextlib import closing
from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import (
    AttemptConflict,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.stripe_inbox import (
    InboxReceipt,
    ReadbackClaim,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxError,
    StripeInboxScope,
)
from lab.stripe_observation import (
    StripeObservationError,
    associate_stripe_intent,
    reconcile_stripe_intent,
    validate_stripe_intent,
)
from lab.stripe_readback import (
    StripeReadbackError,
    StripeReadbackProvenance,
    accept_stripe_readback,
    find_stripe_readback_provenance,
    read_stripe_readback_provenance,
)
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


class StripeReadbackProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "stripe_readback_provenance.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.journal = PaymentAttemptJournal(self.path)
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

    def record(
        self,
        event_id: str = "evt_synthetic",
        *,
        scope: StripeInboxScope | None = None,
        reference: str = "pi_synthetic",
    ) -> InboxReceipt:
        target_scope = self.scope if scope is None else scope
        body = event_body(event_id, reference=reference, live=target_scope.livemode)
        return self.inbox.record(target_scope, body, header(body), SECRET, now=NOW).receipt

    def test_single_snapshot_lifecycle_from_unreserved_through_atomic_acceptance(self) -> None:
        # 1. Neither attempt nor receipt exists -> find returns None, read raises
        self.assertIsNone(
            find_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            )
        )
        with self.assertRaisesRegex(StripeReadbackError, "No payment attempt or webhook receipt"):
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            )

        # 2. Webhook recorded and claimed for an unreserved operation
        early_op = replace(
            self.operation,
            operation_id="op-early-webhook",
            approval_id="app-early",
            idempotency_key="idem-early",
        )
        early_receipt = self.record("evt_early", reference="pi_early")
        self.assertEqual(
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_early", early_op
            ),
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_early",
                fingerprint=early_op.fingerprint,
                attempt=None,
                receipt=early_receipt,
                claim_status=None,
            ),
        )
        early_claim = self.inbox.claim_next(self.scope, "worker-early")
        assert early_claim is not None
        self.assertEqual(
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_early", early_op
            ),
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_early",
                fingerprint=early_op.fingerprint,
                attempt=None,
                receipt=early_receipt,
                claim_status=ReadbackClaimStatus(early_claim, "active"),
            ),
        )

        # 3. Operation reserved (unassociated), webhook not yet recorded
        self.journal.reserve(self.operation)
        self.assertEqual(
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            ),
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", None),
                receipt=None,
                claim_status=None,
            ),
        )

        # 4. Webhook recorded while operation is still unassociated
        receipt = self.record("evt_synthetic", reference="pi_synthetic")
        self.assertEqual(
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            ),
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", None),
                receipt=receipt,
                claim_status=None,
            ),
        )

        # 5. Associate PaymentIntent on journal + claim and handoff on inbox
        associate_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**self.intent, "status": "processing", "amount_received": 0},
        )
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None
        handed_off = self.inbox.handoff(claim, "worker-b")
        self.assertEqual(
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            ),
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", "pi_synthetic"),
                receipt=receipt,
                claim_status=ReadbackClaimStatus(handed_off, "active"),
            ),
        )

        # 6. Atomic acceptance updates both attempt outcome and claim state
        accepted = accept_stripe_readback(
            self.inbox,
            self.journal,
            handed_off,
            self.operation,
            retrieved_account="acct_synthetic",
            intent=self.intent,
        )
        self.assertEqual(accepted, PaymentAttempt("succeeded", "pi_synthetic"))

        statements: list[str] = []
        original_connect = self.inbox._connect

        def traced_connect() -> sqlite3.Connection:
            db = original_connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.inbox, "_connect", side_effect=traced_connect):
            provenance = read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
            )
        self.assertEqual(
            provenance,
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("succeeded", "pi_synthetic"),
                receipt=receipt,
                claim_status=ReadbackClaimStatus(handed_off, "handled"),
            ),
        )
        select_statements = [
            stmt for stmt in statements if stmt.lstrip().upper().startswith("SELECT")
        ]
        self.assertEqual(len(select_statements), 1)
        self.assertFalse(
            any("BEGIN" in stmt.upper() for stmt in statements),
            f"Unexpected transaction statement in {statements!r}",
        )

    def test_pre_connection_argument_scope_and_file_validation(self) -> None:
        with patch.object(self.inbox, "_connect") as connect_mock:
            for bad_inbox in (None, "inbox", self.journal):
                with self.subTest(inbox=bad_inbox), self.assertRaises(StripeReadbackError):
                    find_stripe_readback_provenance(
                        bad_inbox,  # type: ignore[arg-type]
                        self.journal,
                        self.scope,
                        "evt_synthetic",
                        self.operation,
                    )
            for bad_journal in (None, "journal", self.inbox):
                with self.subTest(journal=bad_journal), self.assertRaises(StripeReadbackError):
                    find_stripe_readback_provenance(
                        self.inbox,
                        bad_journal,  # type: ignore[arg-type]
                        self.scope,
                        "evt_synthetic",
                        self.operation,
                    )
            for bad_scope in (None, "scope", self.operation):
                with self.subTest(scope=bad_scope), self.assertRaises(StripeReadbackError):
                    find_stripe_readback_provenance(
                        self.inbox,
                        self.journal,
                        bad_scope,  # type: ignore[arg-type]
                        "evt_synthetic",
                        self.operation,
                    )
            for bad_op in (None, "operation", self.scope):
                with self.subTest(operation=bad_op), self.assertRaises(StripeReadbackError):
                    find_stripe_readback_provenance(
                        self.inbox,
                        self.journal,
                        self.scope,
                        "evt_synthetic",
                        bad_op,  # type: ignore[arg-type]
                    )
            for bad_event_id in (None, 1, "", "evt_", "pi_synthetic", " evt_synthetic"):
                with self.subTest(event_id=bad_event_id), self.assertRaises(StripeInboxError):
                    find_stripe_readback_provenance(
                        self.inbox,
                        self.journal,
                        self.scope,
                        bad_event_id,  # type: ignore[arg-type]
                        self.operation,
                    )
            for op_change in (
                {"tenant_id": "other-tenant"},
                {"provider_account": "acct_other"},
                {"provider": "stripe:live"},
                {"provider": "other-provider"},
            ):
                with self.subTest(op_change=op_change), self.assertRaises(StripeReadbackError):
                    find_stripe_readback_provenance(
                        self.inbox,
                        self.journal,
                        self.scope,
                        "evt_synthetic",
                        replace(self.operation, **op_change),
                    )
            for bad_claim in (None, "claim", {}):
                with self.subTest(handoff_claim=bad_claim), self.assertRaises(StripeInboxError):
                    self.inbox.handoff(bad_claim, "worker-a")  # type: ignore[arg-type]
                with self.subTest(finish_claim=bad_claim), self.assertRaises(StripeInboxError):
                    self.inbox.finish_readback(bad_claim)  # type: ignore[arg-type]
            connect_mock.assert_not_called()

        # Also check stripe_observation type validation
        for bad_journal, bad_op in ((None, self.operation), (self.journal, None)):
            with self.subTest(reconcile_types=(bad_journal, bad_op)):
                with self.assertRaises(StripeObservationError):
                    reconcile_stripe_intent(
                        bad_journal,  # type: ignore[arg-type]
                        bad_op,  # type: ignore[arg-type]
                        retrieved_account="acct_synthetic",
                        intent=self.intent,
                    )
        for bad_prev in (None, "attempt", {}):
            with self.subTest(validate_previous=bad_prev):
                with self.assertRaises(StripeObservationError):
                    validate_stripe_intent(
                        self.operation,
                        bad_prev,  # type: ignore[arg-type]
                        retrieved_account="acct_synthetic",
                        intent=self.intent,
                    )

        # Separate SQLite files or hardlink aliases are rejected
        separate_journal = PaymentAttemptJournal(self.path.with_name("separate.sqlite3"))
        with self.assertRaisesRegex(StripeReadbackError, "same resolved"):
            find_stripe_readback_provenance(
                self.inbox, separate_journal, self.scope, "evt_synthetic", self.operation
            )
        hardlink_path = self.path.with_name("hardlink.sqlite3")
        os.link(self.path, hardlink_path)
        aliased_journal = PaymentAttemptJournal(self.path)
        aliased_journal.path = hardlink_path
        with self.assertRaisesRegex(StripeReadbackError, "same resolved"):
            find_stripe_readback_provenance(
                self.inbox, aliased_journal, self.scope, "evt_synthetic", self.operation
            )

    def test_cross_table_reference_conflicts_and_corrupted_rows_fail_closed(self) -> None:
        self.journal.reserve(self.operation)
        associate_stripe_intent(
            self.journal,
            self.operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**self.intent, "status": "processing", "amount_received": 0},
        )
        self.record("evt_synthetic", reference="pi_synthetic")
        self.record("evt_mismatch", reference="pi_other")

        # 1. Event receipt for a different PaymentIntent than the bound attempt
        with self.assertRaisesRegex(StripeReadbackError, "Receipt differs"):
            find_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_mismatch", self.operation
            )
        with self.assertRaisesRegex(StripeReadbackError, "Receipt differs"):
            read_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_mismatch", self.operation
            )

        # 2. 10-dimension operation mutations & denormalized column corruption
        for op_mutation in (
            replace(self.operation, approval_id="app-other"),
            replace(self.operation, idempotency_key="idem-other"),
            replace(
                self.operation,
                checkout=replace(self.operation.checkout, amount=2000),
            ),
        ):
            with self.subTest(op_mutation=op_mutation), self.assertRaises(AttemptConflict):
                find_stripe_readback_provenance(
                    self.inbox, self.journal, self.scope, "evt_synthetic", op_mutation
                )

        for col, orig, bad in (
            ("fingerprint", self.operation.fingerprint, "0" * 64),
            ("approval_id", self.operation.approval_id, "tampered-app"),
            ("provider", self.operation.provider, "stripe:live"),
            ("provider_account", self.operation.provider_account, "acct_tampered"),
            ("idempotency_key", self.operation.idempotency_key, "tampered-idem"),
            ("outcome", "unknown", "corrupted-outcome"),
            ("provider_reference", "pi_synthetic", "   "),
        ):
            with self.subTest(att_col=col):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(
                        f"UPDATE payment_attempts SET {col}=? WHERE operation_id='op-1'",
                        (bad,),
                    )
                with self.assertRaises(AttemptConflict):
                    find_stripe_readback_provenance(
                        self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
                    )
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {col}=? WHERE operation_id='op-1'",
                        (orig,),
                    )

        # 3. Corrupted receipt or claim columns fail closed
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None
        for table, col, orig, bad in (
            ("stripe_event_inbox", "event_type", "payment_intent.succeeded", "charge.succeeded"),
            ("stripe_event_inbox", "provider_reference", "pi_synthetic", "bad_pi"),
            ("stripe_event_inbox", "payload_sha256", claim.receipt.payload_sha256, "Z" * 64),
            ("stripe_readback_claims", "worker_id", "worker-a", "   "),
            ("stripe_readback_claims", "generation", 1, 0),
            ("stripe_readback_claims", "state", "active", "corrupted"),
        ):
            with self.subTest(table=table, col=col):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(
                        f"UPDATE {table} SET {col}=? WHERE event_id='evt_synthetic'",
                        (bad,),
                    )
                with self.assertRaises(StripeInboxError):
                    find_stripe_readback_provenance(
                        self.inbox, self.journal, self.scope, "evt_synthetic", self.operation
                    )
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE {table} SET {col}=? WHERE event_id='evt_synthetic'",
                        (orig,),
                    )

        # 4. Orphan stripe_readback_claims row (without parent stripe_event_inbox row)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute(
                "INSERT INTO stripe_readback_claims VALUES (?,?,?,?,?,?,1,'active')",
                (*self.scope.key, "evt_orphan_claim", "worker-orphan"),
            )
        with self.assertRaises(StripeInboxError):
            find_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_orphan_claim", self.operation
            )
        unreserved_op = replace(
            self.operation,
            operation_id="op-unreserved",
            approval_id="app-unreserved",
            idempotency_key="idem-unreserved",
        )
        with self.assertRaises(StripeInboxError):
            find_stripe_readback_provenance(
                self.inbox, self.journal, self.scope, "evt_orphan_claim", unreserved_op
            )

    def test_stripe_readback_provenance_dataclass_invariants_and_immutability(self) -> None:
        receipt = InboxReceipt(
            "evt_synthetic",
            "payment_intent.succeeded",
            "pi_synthetic",
            "a" * 64,
        )
        claim = ReadbackClaim(self.scope, receipt, "worker-a", 1)
        claim_status = ReadbackClaimStatus(claim, "active")
        attempt = PaymentAttempt("unknown", "pi_synthetic")

        valid = StripeReadbackProvenance(
            scope=self.scope,
            event_id="evt_synthetic",
            fingerprint=self.operation.fingerprint,
            attempt=attempt,
            receipt=receipt,
            claim_status=claim_status,
        )
        with self.assertRaises(FrozenInstanceError):
            valid.event_id = "evt_other"  # type: ignore[misc]

        for bad_scope in (None, "scope", {}):
            with self.subTest(scope=bad_scope), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=bad_scope,  # type: ignore[arg-type]
                    event_id="evt_synthetic",
                    fingerprint=self.operation.fingerprint,
                    attempt=attempt,
                    receipt=receipt,
                    claim_status=claim_status,
                )

        for bad_event_id in (None, 1, "", "evt_", "pi_synthetic"):
            with self.subTest(event_id=bad_event_id), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=self.scope,
                    event_id=bad_event_id,  # type: ignore[arg-type]
                    fingerprint=self.operation.fingerprint,
                    attempt=attempt,
                    receipt=None,
                    claim_status=None,
                )

        for bad_fp in (None, 1, "", "0" * 63, "A" * 64):
            with self.subTest(fingerprint=bad_fp), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=self.scope,
                    event_id="evt_synthetic",
                    fingerprint=bad_fp,  # type: ignore[arg-type]
                    attempt=attempt,
                    receipt=receipt,
                    claim_status=claim_status,
                )

        for bad_attempt in ("attempt", 1, {}):
            with self.subTest(attempt=bad_attempt), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=self.scope,
                    event_id="evt_synthetic",
                    fingerprint=self.operation.fingerprint,
                    attempt=bad_attempt,  # type: ignore[arg-type]
                    receipt=receipt,
                    claim_status=claim_status,
                )

        for bad_receipt in ("receipt", 1, {}):
            with self.subTest(receipt=bad_receipt), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=self.scope,
                    event_id="evt_synthetic",
                    fingerprint=self.operation.fingerprint,
                    attempt=attempt,
                    receipt=bad_receipt,  # type: ignore[arg-type]
                    claim_status=None,
                )

        for bad_claim_status in ("claim_status", 1, {}):
            with self.subTest(claim_status=bad_claim_status), self.assertRaises(StripeReadbackError):
                StripeReadbackProvenance(
                    scope=self.scope,
                    event_id="evt_synthetic",
                    fingerprint=self.operation.fingerprint,
                    attempt=attempt,
                    receipt=receipt,
                    claim_status=bad_claim_status,  # type: ignore[arg-type]
                )

        # Neither attempt nor receipt present
        with self.assertRaisesRegex(StripeReadbackError, "requires a reserved attempt"):
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=None,
                receipt=None,
                claim_status=None,
            )

        # Receipt event_id differs from lookup event_id
        with self.assertRaisesRegex(StripeReadbackError, "Event ID differs"):
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_other",
                fingerprint=self.operation.fingerprint,
                attempt=attempt,
                receipt=receipt,
                claim_status=claim_status,
            )

        # Claim status without receipt
        with self.assertRaisesRegex(StripeReadbackError, "cannot exist without a recorded receipt"):
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=attempt,
                receipt=None,
                claim_status=claim_status,
            )

        # Claim status with mismatched scope or receipt
        other_scope = replace(self.scope, endpoint_id="ep-other")
        with self.assertRaisesRegex(StripeReadbackError, "does not match provenance scope"):
            StripeReadbackProvenance(
                scope=other_scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=attempt,
                receipt=receipt,
                claim_status=claim_status,
            )

        # Attempt and receipt have conflicting PaymentIntent references
        with self.assertRaisesRegex(StripeReadbackError, "Receipt differs"):
            StripeReadbackProvenance(
                scope=self.scope,
                event_id="evt_synthetic",
                fingerprint=self.operation.fingerprint,
                attempt=PaymentAttempt("unknown", "pi_other"),
                receipt=receipt,
                claim_status=claim_status,
            )


if __name__ == "__main__":
    unittest.main()
