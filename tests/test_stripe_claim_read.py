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


if __name__ == "__main__":
    unittest.main()
