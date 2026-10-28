"""Synthetic scoped history lookup, not current delivery or payment authority."""

import json
import sqlite3
import unittest
from contextlib import closing
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


class StripeReceiptReadTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

    def record(self, event_id="evt_synthetic", *, scope=None, body=None):
        scope = self.scope if scope is None else scope
        body = event_body(event_id, live=scope.livemode) if body is None else body
        return self.inbox.record(scope, body, header(body), SECRET, now=NOW).receipt

    def test_absence_returns_none_without_creating_history(self):
        self.assertIsNone(self.inbox.read_receipt(self.scope, "evt_absent"))
        self.assertEqual(self.inbox.pending(self.scope), ())
        self.assertIsNone(self.inbox.claim_next(self.scope, "worker"))

    def test_original_receipt_is_returned(self):
        receipt = self.record()
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
        self.assertTrue(receipt.requires_readback)

    def test_reader_survives_reopen(self):
        receipt = self.record()
        self.assertEqual(StripeEventInbox(self.path).read_receipt(self.scope, receipt.event_id), receipt)

    def test_every_trusted_scope_dimension_isolated(self):
        self.record()
        for field, value in (("tenant_id", "other"), ("endpoint_id", "other"),
                             ("provider_account", "acct_other"), ("livemode", True)):
            with self.subTest(field=field):
                scope = replace(self.scope, **{field: value})
                self.assertIsNone(self.inbox.read_receipt(scope, "evt_synthetic"))
                receipt = self.record(scope=scope)
                self.assertEqual(self.inbox.read_receipt(scope, receipt.event_id), receipt)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_distinct_event_ids_same_object_remain_distinct(self):
        first, second = self.record("evt_first"), self.record("evt_second")
        self.assertEqual(first.provider_reference, second.provider_reference)
        self.assertEqual(self.inbox.read_receipt(self.scope, "evt_first"), first)
        self.assertEqual(self.inbox.read_receipt(self.scope, "evt_second"), second)

    def test_reserialization_does_not_replace_original_hash(self):
        first = self.record()
        body = json.dumps(json.loads(event_body()), indent=2).encode()
        duplicate = self.inbox.record(self.scope, body, header(body), SECRET, now=NOW)
        self.assertFalse(duplicate.body_matches_first)
        self.assertEqual(self.inbox.read_receipt(self.scope, first.event_id), first)

    def test_active_claim_unchanged(self):
        receipt = self.record()
        claim = self.inbox.claim_next(self.scope, "worker")
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
        replacement = self.inbox.handoff(claim, "new-worker")
        self.assertEqual(replacement.generation, claim.generation + 1)

    def test_handled_claim_not_reopened(self):
        receipt = self.record()
        claim = self.inbox.claim_next(self.scope, "worker")
        self.inbox.finish_readback(claim)
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
        self.assertIsNone(self.inbox.claim_next(self.scope, "another"))

    def test_invalid_scope_rejected_before_connection(self):
        with patch.object(self.inbox, "_connect") as connect:
            for scope in (None, {}, "tenant"):
                with self.subTest(scope=scope), self.assertRaises(StripeInboxError):
                    self.inbox.read_receipt(scope, "evt_synthetic")
            connect.assert_not_called()

    def test_invalid_event_id_rejected_before_connection(self):
        with patch.object(self.inbox, "_connect") as connect:
            for event_id in (None, True, 1, [], "", "evt_", "pi_synthetic",
                             " evt_valid", "evt_valid\n", "evt_中文", "evt_a' OR 1=1"):
                with self.subTest(event_id=event_id), self.assertRaises(StripeInboxError):
                    self.inbox.read_receipt(self.scope, event_id)
            connect.assert_not_called()

    def test_storage_errors_are_not_absence(self):
        with patch.object(self.inbox, "_connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                self.inbox.read_receipt(self.scope, "evt_synthetic")

    def test_select_does_not_take_writer_or_authenticate(self):
        receipt = self.record()
        statements = []
        connect = self.inbox._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.inbox, "_connect", side_effect=traced), patch(
            "lab.stripe_inbox.verify_stripe_delivery", side_effect=AssertionError("verification")
        ), patch("lab.stripe_inbox.json.loads", side_effect=AssertionError("JSON")):
            self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("SELECT "))

    def test_receipt_beyond_maximum_pending_page_is_found(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executemany(
                "INSERT INTO stripe_event_inbox VALUES (?,?,?,?,?,?,?,?)",
                [(*self.scope.key, f"evt_{i}", "payment_intent.succeeded",
                  "pi_synthetic", "0" * 64) for i in range(1001)],
            )
        self.assertNotIn("evt_1000", [r.event_id for r in self.inbox.pending(self.scope, limit=1000)])
        self.assertEqual(self.inbox.read_receipt(self.scope, "evt_1000").event_id, "evt_1000")

    def test_history_does_not_readmit_stale_delivery(self):
        receipt = self.record()
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
        body = event_body()
        times = iter((NOW + 299, NOW + 301))
        with self.assertRaises(StripeDeliveryError):
            self.inbox.record_with_clock(
                self.scope, body, header(body), SECRET, clock=lambda: next(times),
            )
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)

    def test_frozen_receipt_cannot_mutate_persisted_history(self):
        receipt = self.record()
        read = self.inbox.read_receipt(self.scope, receipt.event_id)
        with self.assertRaises(FrozenInstanceError):
            read.payload_sha256 = "changed"
        self.assertEqual(self.inbox.read_receipt(self.scope, receipt.event_id), receipt)
