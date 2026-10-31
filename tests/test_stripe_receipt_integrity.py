from __future__ import annotations

from contextlib import closing
from pathlib import Path
import hmac
import hashlib
import json
import sqlite3
import tempfile
import unittest

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import (
    InboxDecision,
    InboxReceipt,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxError,
    StripeInboxScope,
)
from lab.stripe_observation import associate_stripe_intent
from lab.stripe_readback import StripeReadbackError, accept_stripe_readback


SECRET = "whsec_synthetic_test_secret"
NOW = 1_700_000_000


def event_body(
    event_id: str = "evt_synthetic",
    *,
    event_type: str = "payment_intent.succeeded",
    reference: str = "pi_synthetic",
    livemode: bool = False,
) -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "livemode": livemode,
            "data": {
                "object": {
                    "id": reference,
                    "object": "payment_intent",
                    "livemode": livemode,
                },
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


def header(body: bytes, *, timestamp: int = NOW, secret: str = SECRET) -> str:
    signed = f"{timestamp}.".encode("ascii") + body
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


class StripeReceiptIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "stripe_inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope(
            tenant_id="tenant-a",
            endpoint_id="ep-1",
            provider_account="acct_synthetic",
            livemode=False,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def reserve_operation(self, operation_id: str) -> tuple[PaymentAttemptJournal, PaymentOperation, dict]:
        journal = PaymentAttemptJournal(self.path)
        operation = PaymentOperation(
            "tenant-a",
            operation_id,
            "approval-1",
            "stripe:test",
            "acct_synthetic",
            f"idem-{operation_id}",
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
            journal,
            operation,
            retrieved_account="acct_synthetic",
            expected_reference="pi_synthetic",
            intent={**intent, "amount_received": 0, "status": "processing"},
        )
        return journal, operation, intent

    def record(
        self,
        event_id: str = "evt_synthetic",
        *,
        event_type: str = "payment_intent.succeeded",
        reference: str = "pi_synthetic",
    ) -> InboxReceipt:
        body = event_body(event_id, event_type=event_type, reference=reference)
        return self.inbox.record(self.scope, body, header(body), SECRET, now=NOW).receipt

    def test_inbox_receipt_and_decision_validate_invariants(self) -> None:
        valid = InboxReceipt(
            "evt_synthetic",
            "payment_intent.succeeded",
            "pi_synthetic",
            "0" * 64,
        )
        self.assertEqual(valid.requires_readback, True)
        decision = InboxDecision(valid, True, False)
        self.assertIs(decision.receipt, valid)

        for bad_event_id in (
            None, True, 1, "", "evt_", "pi_synthetic",
            " evt_synthetic", "evt_synthetic\n", "evt_中文", "evt_a' OR 1=1",
        ):
            with self.subTest(event_id=bad_event_id), self.assertRaises(StripeInboxError):
                InboxReceipt(bad_event_id, "payment_intent.succeeded", "pi_synthetic", "0" * 64)

        for bad_type in (
            None, True, 1, "", "charge.succeeded",
            "payment_intent.created", "payment_intent.succeeded ",
        ):
            with self.subTest(event_type=bad_type), self.assertRaises(StripeInboxError):
                InboxReceipt("evt_synthetic", bad_type, "pi_synthetic", "0" * 64)

        for bad_reference in (
            None, True, 1, "", "pi_", "evt_synthetic",
            " pi_synthetic", "pi_synthetic\n", "pi_中文",
        ):
            with self.subTest(provider_reference=bad_reference), self.assertRaises(StripeInboxError):
                InboxReceipt("evt_synthetic", "payment_intent.succeeded", bad_reference, "0" * 64)

        for bad_digest in (
            None, True, 1, "", "0" * 63, "0" * 65,
            "A" * 64, "g" * 64, "0" * 64 + "\n",
        ):
            with self.subTest(payload_sha256=bad_digest), self.assertRaises(StripeInboxError):
                InboxReceipt("evt_synthetic", "payment_intent.succeeded", "pi_synthetic", bad_digest)

        for bad_flag in (None, 1, 0, "true", []):
            with self.subTest(requires_readback=bad_flag), self.assertRaises(StripeInboxError):
                InboxReceipt(
                    "evt_synthetic", "payment_intent.succeeded",
                    "pi_synthetic", "0" * 64, bad_flag,
                )

        for bad_receipt in (None, "evt_synthetic", {}):
            with self.subTest(receipt=bad_receipt), self.assertRaises(StripeInboxError):
                InboxDecision(bad_receipt, True, True)

        for bad_bool in (None, 1, 0, "true"):
            with self.subTest(first_seen=bad_bool), self.assertRaises(StripeInboxError):
                InboxDecision(valid, bad_bool, True)
            with self.subTest(body_matches_first=bad_bool), self.assertRaises(StripeInboxError):
                InboxDecision(valid, True, bad_bool)

    def test_corrupted_persisted_receipt_columns_fail_closed_before_claim_or_read(self) -> None:
        corruptions = (
            ("event_id", "bad_event_id"),
            ("event_type", "charge.succeeded"),
            ("provider_reference", "ch_invalid"),
            ("payload_sha256", "NOT_HEX"),
        )
        for index, (column, bad_value) in enumerate(corruptions):
            with self.subTest(column=column):
                event_id = f"evt_corrupt_{index}"
                self.record(event_id)
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE stripe_event_inbox SET {column}=? WHERE event_id=?",
                        (bad_value, event_id),
                    )
                if column != "event_id":
                    with self.assertRaises(StripeInboxError):
                        self.inbox.read_receipt(self.scope, event_id)
                    body = event_body(event_id)
                    with self.assertRaises(StripeInboxError):
                        self.inbox.record(self.scope, body, header(body), SECRET, now=NOW)
                with self.assertRaises(StripeInboxError):
                    self.inbox.pending(self.scope)
                with self.assertRaises(StripeInboxError):
                    self.inbox.claim_next(self.scope, "worker-a")
                with closing(sqlite3.connect(self.path)) as db, db:
                    count = db.execute("SELECT count(*) FROM stripe_readback_claims").fetchone()[0]
                    self.assertEqual(count, 0)
                    db.execute("DELETE FROM stripe_event_inbox")

    def test_corrupted_persisted_receipt_rejects_claim_reads_handoff_and_completion(self) -> None:
        journal, operation, intent = self.reserve_operation("op-1")
        self.record("evt_claimed")
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None

        for column, good_value, bad_value in (
            ("event_type", "payment_intent.succeeded", "payment_intent.created"),
            ("provider_reference", "pi_synthetic", "bad_pi"),
            ("payload_sha256", claim.receipt.payload_sha256, "F" * 64),
        ):
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE stripe_event_inbox SET {column}=? WHERE event_id='evt_claimed'",
                        (bad_value,),
                    )
                try:
                    with self.assertRaises(StripeInboxError):
                        self.inbox.read_claim(self.scope, "evt_claimed")
                    with self.assertRaises(StripeInboxError):
                        self.inbox.active_claims(self.scope)
                    with self.assertRaises(StripeInboxError):
                        self.inbox.handoff(claim, "worker-b")
                    with self.assertRaises(StripeInboxError):
                        self.inbox.finish_readback(claim)
                    with self.assertRaises(StripeInboxError):
                        accept_stripe_readback(
                            self.inbox,
                            journal,
                            claim,
                            operation,
                            retrieved_account="acct_synthetic",
                            intent=intent,
                        )
                    self.assertEqual(
                        journal.read(operation),
                        PaymentAttempt("unknown", "pi_synthetic"),
                    )
                finally:
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute(
                            f"UPDATE stripe_event_inbox SET {column}=? WHERE event_id='evt_claimed'",
                            (good_value,),
                        )

    def test_orphan_claim_without_inbox_receipt_fails_closed(self) -> None:
        self.record("evt_orphan")
        self.record("evt_valid")
        orphan = self.inbox.claim_next(self.scope, "worker-a")
        valid = self.inbox.claim_next(self.scope, "worker-b")
        assert orphan is not None and valid is not None

        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM stripe_event_inbox WHERE event_id='evt_orphan'")

        with self.assertRaises(StripeInboxError):
            self.inbox.read_claim(self.scope, "evt_orphan")
        with self.assertRaises(StripeInboxError):
            self.inbox.active_claims(self.scope, limit=1)
        with self.assertRaises(StripeInboxError):
            self.inbox.handoff(orphan, "worker-c")
        with self.assertRaises(StripeInboxError):
            self.inbox.finish_readback(orphan)
        self.assertEqual(
            self.inbox.read_claim(self.scope, "evt_valid"),
            ReadbackClaimStatus(valid, "active"),
        )

    def test_corrupted_claim_state_is_not_overwritten_by_finish_or_readback(self) -> None:
        journal, operation, intent = self.reserve_operation("op-state")
        self.record("evt_bad_state")
        claim = self.inbox.claim_next(self.scope, "worker-a")
        assert claim is not None

        for bad_state in ("", "pending", "ACTIVE", "handled ", "1"):
            with self.subTest(state=bad_state):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute("PRAGMA ignore_check_constraints = ON")
                    db.execute(
                        "UPDATE stripe_readback_claims SET state=? WHERE event_id='evt_bad_state'",
                        (bad_state,),
                    )
                with self.assertRaises(StripeInboxError):
                    self.inbox.read_claim(self.scope, "evt_bad_state")
                with self.assertRaises(StripeInboxError):
                    self.inbox.finish_readback(claim)
                with self.assertRaises(StripeInboxError):
                    accept_stripe_readback(
                        self.inbox,
                        journal,
                        claim,
                        operation,
                        retrieved_account="acct_synthetic",
                        intent=intent,
                    )
                with closing(sqlite3.connect(self.path)) as db:
                    stored_state = db.execute(
                        "SELECT state FROM stripe_readback_claims WHERE event_id='evt_bad_state'"
                    ).fetchone()[0]
                self.assertEqual(stored_state, bad_state)
                self.assertEqual(journal.read(operation), PaymentAttempt("unknown", "pi_synthetic"))


if __name__ == "__main__":
    unittest.main()
