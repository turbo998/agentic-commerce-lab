"""Scoped local readback-claim state lookup, not lease liveness or payment proof."""

import json
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
from lab.payment_attempts import PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import (
    ClaimTransitionPreview,
    InboxDecision,
    InboxEventProvenance,
    InboxReceipt,
    InboxRecordPreview,
    ReadbackClaim,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxError,
    StripeInboxScope,
)
from lab.stripe_observation import associate_stripe_intent
from lab.stripe_readback import StripeReadbackError, accept_stripe_readback
from tests.test_stripe_inbox import NOW, SECRET, event_body, header
from tests.test_stripe_readback import FailingCommit


class StripeClaimReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

    def record(self, event_id: str = "evt_synthetic", *, scope=None, body=None):
        scope = self.scope if scope is None else scope
        body = event_body(event_id, live=scope.livemode) if body is None else body
        return self.inbox.record(scope, body, header(body), SECRET, now=NOW).receipt

    def failed_connection(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        return db

    def test_absent_or_unclaimed_receipt_returns_none_without_creating_work(self) -> None:
        self.assertIsNone(self.inbox.read_claim(self.scope, "evt_absent"))
        self.assertIsNone(self.inbox.read_receipt(self.scope, "evt_absent"))
        receipt = self.record("evt_unclaimed")
        self.assertEqual(self.inbox.read_receipt(self.scope, "evt_unclaimed"), receipt)
        self.assertIsNone(self.inbox.read_claim(self.scope, "evt_unclaimed"))
        claim = self.inbox.claim_next(self.scope, "worker-a")
        self.assertEqual(claim.receipt, receipt)
        self.assertEqual(claim.generation, 1)

    def test_active_claim_status_survives_reopen_and_fresh_process(self) -> None:
        self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        expected = ReadbackClaimStatus(claim, "active")
        self.assertEqual(self.inbox.read_claim(self.scope, "evt_synthetic"), expected)
        self.assertEqual(
            StripeEventInbox(self.path).read_claim(self.scope, "evt_synthetic"),
            expected,
        )
        script = (
            "import sys; from pathlib import Path; "
            "from lab.stripe_inbox import StripeEventInbox, StripeInboxScope; "
            "db = StripeEventInbox(Path(sys.argv[1])); "
            "scope = StripeInboxScope('tenant','endpoint','acct_synthetic',False); "
            "status = db.read_claim(scope, 'evt_synthetic'); "
            "print(f'{status.state}:{status.claim.worker_id}:{status.claim.generation}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)], text=True,
        )
        self.assertEqual(out.strip(), "active:worker-a:1")

    def test_handoff_and_same_worker_handoff_update_persisted_claim_status(self) -> None:
        self.record()
        first = self.inbox.claim_next(self.scope, "worker-a")
        second = self.inbox.handoff(first, "worker-b")
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_synthetic"),
            ReadbackClaimStatus(second, "active"),
        )
        third = self.inbox.handoff(second, "worker-b")
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_synthetic"),
            ReadbackClaimStatus(third, "active"),
        )
        self.assertEqual(third.generation, 3)

    def test_handled_status_persists_after_finish_readback(self) -> None:
        self.record()
        first = self.inbox.claim_next(self.scope, "worker-a")
        second = self.inbox.handoff(first, "worker-b")
        self.inbox.finish_readback(second)
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        self.assertIsNone(self.inbox.claim_next(self.scope, "worker-c"))
        status = self.inbox.read_claim(self.scope, "evt_synthetic")
        self.assertEqual(status, ReadbackClaimStatus(second, "handled"))
        self.assertTrue(status.claim.receipt.requires_readback)
        with self.assertRaisesRegex(StripeInboxError, "Handled"):
            self.inbox.handoff(status.claim, "worker-c")
        self.inbox.finish_readback(status.claim)
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_synthetic"),
            ReadbackClaimStatus(second, "handled"),
        )

    def test_handled_status_persists_after_atomic_readback_acceptance(self) -> None:
        journal = PaymentAttemptJournal(self.path)
        operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("shop", "USD", "sku", 1, 1000),
        )
        journal.reserve(operation)
        intent = {
            "id": "pi_synthetic",
            "object": "payment_intent",
            "livemode": False,
            "currency": "usd",
            "amount": 1000,
            "amount_received": 1000,
            "status": "succeeded",
            "transfer_data": None,
            "on_behalf_of": None,
        }
        associate_stripe_intent(
            journal, operation, retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic", intent={**intent, "amount_received": 0, "status": "processing"},
        )
        self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        attempt = accept_stripe_readback(
            self.inbox, journal, claim, operation,
            retrieved_account="acct_synthetic", intent=intent,
        )
        self.assertEqual(attempt, PaymentAttempt("succeeded", "pi_synthetic"))
        status = self.inbox.read_claim(self.scope, "evt_synthetic")
        self.assertEqual(status, ReadbackClaimStatus(claim, "handled"))
        with self.assertRaisesRegex(StripeReadbackError, "Already-handled"):
            accept_stripe_readback(
                self.inbox, journal, status.claim, operation,
                retrieved_account="acct_synthetic", intent=intent,
            )

    def test_duplicate_reserialized_delivery_preserves_claim_and_first_hash(self) -> None:
        first_receipt = self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        self.inbox.finish_readback(claim)
        reserialized = json.dumps(json.loads(event_body()), indent=2).encode()
        duplicate = self.inbox.record(self.scope, reserialized, header(reserialized), SECRET, now=NOW)
        self.assertFalse(duplicate.body_matches_first)
        status = self.inbox.read_claim(self.scope, "evt_synthetic")
        self.assertEqual(status, ReadbackClaimStatus(claim, "handled"))
        self.assertEqual(status.claim.receipt, first_receipt)

    def test_every_trusted_scope_dimension_and_event_id_isolated(self) -> None:
        self.record("evt_first")
        self.record("evt_second")
        first_claim = self.inbox.claim_next(self.scope, "worker-1")
        second_claim = self.inbox.claim_next(self.scope, "worker-2")
        self.inbox.finish_readback(second_claim)
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_first"),
            ReadbackClaimStatus(first_claim, "active"),
        )
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_second"),
            ReadbackClaimStatus(second_claim, "handled"),
        )
        for field, value in (
            ("tenant_id", "other"),
            ("endpoint_id", "other"),
            ("provider_account", "acct_other"),
            ("livemode", True),
        ):
            with self.subTest(field=field):
                other_scope = replace(self.scope, **{field: value})
                self.assertIsNone(self.inbox.read_claim(other_scope, "evt_first"))
                self.record("evt_first", scope=other_scope)
                self.assertIsNone(self.inbox.read_claim(other_scope, "evt_first"))
                other_claim = self.inbox.claim_next(other_scope, f"worker-{field}")
                self.assertEqual(
                    self.inbox.read_claim(other_scope, "evt_first"),
                    ReadbackClaimStatus(other_claim, "active"),
                )

    def test_claim_beyond_maximum_active_claims_page_is_found_and_recoverable(self) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany(
                "INSERT INTO stripe_event_inbox VALUES (?,?,?,?,?,?,?,?)",
                [(*self.scope.key, f"evt_{i}", "payment_intent.succeeded",
                  "pi_synthetic", "0" * 64) for i in range(1001)],
            )
            db.executemany(
                "INSERT INTO stripe_readback_claims VALUES (?,?,?,?,?,?,1,'active')",
                [(*self.scope.key, f"evt_{i}", "worker-a") for i in range(1001)],
            )
        active_ids = [c.receipt.event_id for c in self.inbox.active_claims(self.scope, limit=1000)]
        self.assertNotIn("evt_1000", active_ids)
        status = self.inbox.read_claim(self.scope, "evt_1000")
        self.assertIsNotNone(status)
        self.assertEqual(status.state, "active")
        self.assertEqual(status.claim.receipt.event_id, "evt_1000")
        recovered = self.inbox.handoff(status.claim, "worker-b")
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_1000"),
            ReadbackClaimStatus(recovered, "active"),
        )
        self.inbox.finish_readback(recovered)
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_1000"),
            ReadbackClaimStatus(recovered, "handled"),
        )

    def test_failed_commit_preserves_prior_claim_status(self) -> None:
        self.record()
        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.claim_next(self.scope, "worker-a")
        self.assertIsNone(self.inbox.read_claim(self.scope, "evt_synthetic"))

        claim = self.inbox.claim_next(self.scope, "worker-a")
        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.handoff(claim, "worker-b")
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_synthetic"),
            ReadbackClaimStatus(claim, "active"),
        )

        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.finish_readback(claim)
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_synthetic"),
            ReadbackClaimStatus(claim, "active"),
        )

    def test_invalid_scope_event_id_and_status_fields_rejected_before_connection(self) -> None:
        with patch.object(self.inbox, "_connect") as connect:
            for bad_scope in (None, {}, "tenant"):
                with self.subTest(scope=bad_scope), self.assertRaises(StripeInboxError):
                    self.inbox.read_claim(bad_scope, "evt_synthetic")
            for bad_event_id in (
                None, True, 1, [], "", "evt_", "pi_synthetic",
                " evt_valid", "evt_valid\n", "evt_中文", "evt_a' OR 1=1",
            ):
                with self.subTest(event_id=bad_event_id), self.assertRaises(StripeInboxError):
                    self.inbox.read_claim(self.scope, bad_event_id)
            connect.assert_not_called()

        self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        for bad_claim in (None, "claim", {}):
            with self.subTest(claim=bad_claim), self.assertRaises(StripeInboxError):
                ReadbackClaimStatus(bad_claim, "active")
        for bad_state in (None, True, "", "pending", "ACTIVE", "active "):
            with self.subTest(state=bad_state), self.assertRaises(StripeInboxError):
                ReadbackClaimStatus(claim, bad_state)
        status = self.inbox.read_claim(self.scope, "evt_synthetic")
        with self.assertRaises(FrozenInstanceError):
            status.state = "handled"

    def test_corrupted_stored_claim_metadata_is_rejected(self) -> None:
        self.record("evt_bad_worker")
        self.inbox.claim_next(self.scope, "worker-a")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE stripe_readback_claims SET worker_id='   ' WHERE event_id='evt_bad_worker'"
            )
        with self.assertRaises(StripeInboxError):
            self.inbox.read_claim(self.scope, "evt_bad_worker")

        self.record("evt_bad_gen")
        self.inbox.claim_next(self.scope, "worker-a")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE stripe_readback_claims SET generation='not-an-int' WHERE event_id='evt_bad_gen'"
            )
        with self.assertRaises(StripeInboxError):
            self.inbox.read_claim(self.scope, "evt_bad_gen")

    def test_storage_errors_propagate_and_select_is_read_only(self) -> None:
        with patch.object(self.inbox, "_connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                self.inbox.read_claim(self.scope, "evt_synthetic")

        self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        statements: list[str] = []
        connect = self.inbox._connect

        def traced() -> sqlite3.Connection:
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.inbox, "_connect", side_effect=traced), patch(
            "lab.stripe_inbox.verify_stripe_delivery", side_effect=AssertionError("verification"),
        ), patch("lab.stripe_inbox.json.loads", side_effect=AssertionError("JSON")):
            self.assertEqual(
                self.inbox.read_claim(self.scope, "evt_synthetic"),
                ReadbackClaimStatus(claim, "active"),
            )
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT "))
        self.assertNotIn("BEGIN", " ".join(statements).upper())

    def test_inbox_event_provenance_tracks_unreceived_unclaimed_active_and_handled_phases(self) -> None:
        self.assertIsNone(self.inbox.find_provenance(self.scope, "evt_absent"))
        with self.assertRaisesRegex(StripeInboxError, "No inbox receipt exists"):
            self.inbox.read_provenance(self.scope, "evt_absent")

        receipt = self.record("evt_lifecycle")
        unclaimed = self.inbox.read_provenance(self.scope, "evt_lifecycle")
        self.assertEqual(
            unclaimed,
            InboxEventProvenance(self.scope, receipt, None),
        )
        self.assertEqual(unclaimed.phase, "unclaimed")
        self.assertEqual(self.inbox.find_provenance(self.scope, "evt_lifecycle"), unclaimed)

        claim = self.inbox.claim_next(self.scope, "worker-a")
        active = self.inbox.read_provenance(self.scope, "evt_lifecycle")
        self.assertEqual(
            active,
            InboxEventProvenance(
                self.scope,
                receipt,
                ReadbackClaimStatus(claim, "active"),
            ),
        )
        self.assertEqual(active.phase, "active")

        handed_off = self.inbox.handoff(claim, "worker-b")
        active_two = self.inbox.read_provenance(self.scope, "evt_lifecycle")
        self.assertEqual(
            active_two,
            InboxEventProvenance(
                self.scope,
                receipt,
                ReadbackClaimStatus(handed_off, "active"),
            ),
        )
        self.assertEqual(active_two.phase, "active")

        self.inbox.finish_readback(handed_off)
        handled = self.inbox.read_provenance(self.scope, "evt_lifecycle")
        self.assertEqual(
            handled,
            InboxEventProvenance(
                self.scope,
                receipt,
                ReadbackClaimStatus(handed_off, "handled"),
            ),
        )
        self.assertEqual(handled.phase, "handled")
        with self.assertRaises(FrozenInstanceError):
            handled.claim_status = None  # type: ignore[misc]

    def test_inbox_event_provenance_detects_orphan_claim_and_enforces_invariants(self) -> None:
        receipt = self.record("evt_orphan")
        claim = self.inbox.claim_next(self.scope, "worker-a")
        status = ReadbackClaimStatus(claim, "active")

        other_scope = replace(self.scope, tenant_id="other")
        other_receipt = self.record("evt_other")
        with self.assertRaisesRegex(StripeInboxError, "trusted scope and persisted receipt"):
            InboxEventProvenance("bad", receipt, None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(StripeInboxError, "trusted scope and persisted receipt"):
            InboxEventProvenance(self.scope, "bad", None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(StripeInboxError, "ReadbackClaimStatus or None"):
            InboxEventProvenance(self.scope, receipt, "bad")  # type: ignore[arg-type]
        with self.assertRaisesRegex(StripeInboxError, "scope or receipt differs"):
            InboxEventProvenance(other_scope, receipt, status)
        with self.assertRaisesRegex(StripeInboxError, "scope or receipt differs"):
            InboxEventProvenance(self.scope, other_receipt, status)

        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA foreign_keys = OFF")
            with db:
                db.execute(
                    "DELETE FROM stripe_event_inbox WHERE event_id = 'evt_orphan'"
                )
        with self.assertRaisesRegex(StripeInboxError, "Orphan readback claim"):
            self.inbox.find_provenance(self.scope, "evt_orphan")
        with self.assertRaisesRegex(StripeInboxError, "Orphan readback claim"):
            self.inbox.read_provenance(self.scope, "evt_orphan")

    def test_corrupted_claim_columns_rejected_by_provenance_and_write_transitions(self) -> None:
        self.record("evt_bad_claim")
        claim = self.inbox.claim_next(self.scope, "worker-a")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(
                "UPDATE stripe_readback_claims SET generation='not-an-int' WHERE event_id='evt_bad_claim'"
            )
        with self.assertRaisesRegex(StripeInboxError, "Readback claim binding is stale or invalid"):
            self.inbox.handoff(claim, "worker-b")
        with self.assertRaisesRegex(StripeInboxError, "Readback claim binding is stale or invalid"):
            self.inbox.finish_readback(claim)
        with self.assertRaisesRegex(StripeInboxError, "positive signed-64-bit integer"):
            self.inbox.find_provenance(self.scope, "evt_bad_claim")
        with self.assertRaisesRegex(StripeInboxError, "positive signed-64-bit integer"):
            self.inbox.read_provenance(self.scope, "evt_bad_claim")

        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA ignore_check_constraints = ON")
            with db:
                db.execute(
                    "UPDATE stripe_readback_claims SET generation=1, state='corrupted' WHERE event_id='evt_bad_claim'"
                )
        with self.assertRaisesRegex(StripeInboxError, "Claim state must be active or handled"):
            self.inbox.find_provenance(self.scope, "evt_bad_claim")

        self.record("evt_trace")
        self.inbox.claim_next(self.scope, "worker-a")
        statements: list[str] = []
        connect = self.inbox._connect

        def traced() -> sqlite3.Connection:
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.inbox, "_connect", side_effect=traced):
            prov = self.inbox.read_provenance(self.scope, "evt_trace")
        self.assertEqual(prov.phase, "active")
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].strip().startswith("SELECT"))
        self.assertNotIn("BEGIN", " ".join(statements).upper())

    def test_preview_record_handoff_and_finish_readback_single_select_dry_runs(self) -> None:
        statements: list[str] = []
        connect = self.inbox._connect

        def traced() -> sqlite3.Connection:
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        body = event_body("evt_preview")
        sig = header(body)
        with patch.object(self.inbox, "_connect", side_effect=traced):
            first_preview = self.inbox.preview_record(
                self.scope, body, sig, SECRET, now=NOW,
            )
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertNotIn("BEGIN", " ".join(statements).upper())
        self.assertIsNone(first_preview.existing_receipt)
        self.assertIsNone(first_preview.existing_claim_status)
        self.assertTrue(first_preview.would_insert_receipt)
        self.assertTrue(first_preview.decision.first_seen)
        self.assertTrue(first_preview.decision.body_matches_first)
        self.assertEqual(first_preview.event_phase, "unclaimed")
        self.assertIsNone(self.inbox.read_receipt(self.scope, "evt_preview"))

        actual = self.inbox.record(self.scope, body, sig, SECRET, now=NOW)
        self.assertEqual(actual, first_preview.decision)

        # Duplicate preview with identical body vs mutated body
        statements.clear()
        with patch.object(self.inbox, "_connect", side_effect=traced):
            dup_preview = self.inbox.preview_record(
                self.scope, body, sig, SECRET, now=NOW,
            )
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertEqual(dup_preview.existing_receipt, actual.receipt)
        self.assertIsNone(dup_preview.existing_claim_status)
        self.assertFalse(dup_preview.would_insert_receipt)
        self.assertFalse(dup_preview.decision.first_seen)
        self.assertTrue(dup_preview.decision.body_matches_first)
        self.assertEqual(dup_preview.event_phase, "unclaimed")

        mutated_event = json.loads(body)
        mutated_event["created"] = NOW + 1
        mutated_body = json.dumps(mutated_event).encode()
        dup_mismatch = self.inbox.preview_record(
            self.scope, mutated_body, header(mutated_body), SECRET, now=NOW,
        )
        self.assertFalse(dup_mismatch.would_insert_receipt)
        self.assertFalse(dup_mismatch.decision.first_seen)
        self.assertFalse(dup_mismatch.decision.body_matches_first)

        # Conflicting event_type or provider_reference rejected by preview_record
        conflict_event = json.loads(body)
        conflict_event["type"] = "payment_intent.payment_failed"
        conflict_body = json.dumps(conflict_event).encode()
        with self.assertRaisesRegex(StripeInboxError, "conflicting type or object bindings"):
            self.inbox.preview_record(
                self.scope, conflict_body, header(conflict_body), SECRET, now=NOW,
            )

        # Claim and preview handoff / finish_readback
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None
        active_record_preview = self.inbox.preview_record(
            self.scope, body, sig, SECRET, now=NOW,
        )
        self.assertEqual(active_record_preview.event_phase, "active")
        self.assertEqual(
            active_record_preview.existing_claim_status,
            ReadbackClaimStatus(claim, "active"),
        )

        statements.clear()
        with patch.object(self.inbox, "_connect", side_effect=traced):
            handoff_preview = self.inbox.preview_handoff(claim, "worker-b")
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertNotIn("BEGIN", " ".join(statements).upper())
        expected_next_claim = ReadbackClaim(self.scope, actual.receipt, "worker-b", 2)
        self.assertEqual(
            handoff_preview,
            ClaimTransitionPreview(
                existing_claim_status=ReadbackClaimStatus(claim, "active"),
                projected_claim_status=ReadbackClaimStatus(expected_next_claim, "active"),
                would_write=True,
            ),
        )
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_preview"),
            ReadbackClaimStatus(claim, "active"),
        )

        handed = self.inbox.handoff(claim, "worker-b")
        self.assertEqual(handed, expected_next_claim)

        statements.clear()
        with patch.object(self.inbox, "_connect", side_effect=traced):
            finish_preview = self.inbox.preview_finish_readback(handed)
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertEqual(
            finish_preview,
            ClaimTransitionPreview(
                existing_claim_status=ReadbackClaimStatus(handed, "active"),
                projected_claim_status=ReadbackClaimStatus(handed, "handled"),
                would_write=True,
            ),
        )

        self.inbox.finish_readback(handed)
        statements.clear()
        with patch.object(self.inbox, "_connect", side_effect=traced):
            idempotent_finish = self.inbox.preview_finish_readback(handed)
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT"))
        self.assertEqual(
            idempotent_finish,
            ClaimTransitionPreview(
                existing_claim_status=ReadbackClaimStatus(handed, "handled"),
                projected_claim_status=ReadbackClaimStatus(handed, "handled"),
                would_write=False,
            ),
        )
        with self.assertRaisesRegex(StripeInboxError, "Handled hints cannot be handed off"):
            self.inbox.preview_handoff(handed, "worker-c")

        # Constructor invariants for InboxRecordPreview and ClaimTransitionPreview
        other_scope = replace(self.scope, tenant_id="other")
        other_receipt = InboxReceipt("evt_other", "payment_intent.succeeded", "pi_synthetic", "0" * 64)
        for bad_kwargs, pattern in (
            ({"scope": "bad"}, "StripeInboxScope is required"),
            ({"decision": "bad"}, "decision must be an InboxDecision"),
            ({"would_insert_receipt": 1}, "would_insert_receipt must be a boolean"),
            (
                {
                    "existing_receipt": None,
                    "existing_claim_status": ReadbackClaimStatus(handed, "handled"),
                },
                "Orphan readback claim",
            ),
            (
                {"existing_receipt": None, "would_insert_receipt": False},
                "First-seen inbox preview must set",
            ),
            (
                {
                    "existing_receipt": actual.receipt,
                    "decision": InboxDecision(actual.receipt, False, True),
                    "would_insert_receipt": True,
                },
                "Duplicate inbox preview must match",
            ),
            (
                {
                    "existing_receipt": actual.receipt,
                    "existing_claim_status": ReadbackClaimStatus(
                        ReadbackClaim(other_scope, actual.receipt, "worker-a", 1),
                        "active",
                    ),
                    "decision": InboxDecision(actual.receipt, False, True),
                    "would_insert_receipt": False,
                },
                "scope or receipt differs",
            ),
        ):
            params = {
                "scope": self.scope,
                "existing_receipt": None,
                "existing_claim_status": None,
                "decision": InboxDecision(actual.receipt, True, True),
                "would_insert_receipt": True,
                **bad_kwargs,
            }
            with self.subTest(bad_kwargs=bad_kwargs), self.assertRaisesRegex(StripeInboxError, pattern):
                InboxRecordPreview(**params)  # type: ignore[arg-type]

        for bad_transition, pattern in (
            (
                {"existing_claim_status": "bad"},
                "ReadbackClaimStatus instances",
            ),
            (
                {
                    "projected_claim_status": ReadbackClaimStatus(
                        ReadbackClaim(other_scope, actual.receipt, "worker-b", 2),
                        "active",
                    ),
                },
                "scope or receipt differs",
            ),
            (
                {
                    "projected_claim_status": ReadbackClaimStatus(
                        ReadbackClaim(self.scope, other_receipt, "worker-b", 2),
                        "active",
                    ),
                },
                "scope or receipt differs",
            ),
            ({"would_write": 1}, "would_write must be a boolean"),
            (
                {"would_write": False},
                "valid active handoff or finish_readback transition",
            ),
            (
                {
                    "existing_claim_status": ReadbackClaimStatus(claim, "handled"),
                    "projected_claim_status": ReadbackClaimStatus(expected_next_claim, "active"),
                    "would_write": True,
                },
                "valid active handoff or finish_readback transition",
            ),
        ):
            params = {
                "existing_claim_status": ReadbackClaimStatus(claim, "active"),
                "projected_claim_status": ReadbackClaimStatus(expected_next_claim, "active"),
                "would_write": True,
                **bad_transition,
            }
            with self.subTest(bad_transition=bad_transition), self.assertRaisesRegex(
                StripeInboxError, pattern,
            ):
                ClaimTransitionPreview(**params)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
