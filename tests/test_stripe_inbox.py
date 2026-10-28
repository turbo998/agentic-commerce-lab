"""Synthetic receipt identity, persistence, rejection and non-payment invariants."""

import hashlib
import hmac
import json
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope

SECRET = "synthetic-only-inbox-secret"
NOW = 1700000000


def event_body(event_id="evt_synthetic", *, live=False, reference="pi_synthetic"):
    return json.dumps({
        "id": event_id, "object": "event", "livemode": live,
        "type": "payment_intent.succeeded", "created": NOW,
        "data": {"object": {"id": reference, "object": "payment_intent", "livemode": live}},
    }).encode()


def header(body, *, timestamp=NOW, secret=SECRET):
    signature = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


class StripeInboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

    def record(self, body=None, *, scope=None, timestamp=NOW, secret=SECRET, now=NOW):
        body = event_body() if body is None else body
        return self.inbox.record(
            self.scope if scope is None else scope, body,
            header(body, timestamp=timestamp, secret=secret), SECRET, now=now,
        )

    def test_receipt_survives_reopen_and_remains_readback_required(self):
        result = self.record()
        self.assertTrue(result.first_seen)
        self.assertTrue(result.body_matches_first)
        reopened = StripeEventInbox(self.path)
        self.assertEqual(reopened.pending(self.scope), (result.receipt,))
        self.assertTrue(result.receipt.requires_readback)

    def test_repeated_delivery_is_one_receipt_after_restart(self):
        first = self.record()
        self.inbox = StripeEventInbox(self.path)
        duplicate = self.record()
        self.assertFalse(duplicate.first_seen)
        self.assertEqual(duplicate.receipt, first.receipt)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_receipt_is_visible_to_a_fresh_python_process(self):
        self.record()
        script = (
            "import sys; from pathlib import Path; "
            "from lab.stripe_inbox import StripeEventInbox, StripeInboxScope; "
            "inbox = StripeEventInbox(Path(sys.argv[1])); "
            "scope = StripeInboxScope('tenant','endpoint','acct_synthetic',False); "
            "print(inbox.pending(scope)[0].event_id)"
        )
        output = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path)], text=True,
        )
        self.assertEqual(output.strip(), "evt_synthetic")

    def test_new_delivery_signature_timestamp_or_secret_is_not_new_identity(self):
        first = self.record()
        body = event_body()
        duplicate = self.inbox.record(
            self.scope, body, header(body, timestamp=NOW + 10, secret="synthetic-rotated"),
            "synthetic-rotated", now=NOW + 10,
        )
        self.assertFalse(duplicate.first_seen)
        self.assertEqual(duplicate.receipt, first.receipt)

    def test_reserialized_body_is_explicitly_observed_without_new_receipt(self):
        first = self.record()
        body = json.dumps(json.loads(event_body()), separators=(",", ":"), sort_keys=True).encode()
        duplicate = self.record(body)
        self.assertFalse(duplicate.first_seen)
        self.assertFalse(duplicate.body_matches_first)
        self.assertEqual(duplicate.receipt.payload_sha256, first.receipt.payload_sha256)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_concurrent_same_event_has_one_first_seen_decision(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.record(), range(2)))
        self.assertEqual(sum(result.first_seen for result in results), 1)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_distinct_event_ids_for_same_object_are_not_business_dedup(self):
        self.assertTrue(self.record(event_body("evt_first")).first_seen)
        self.assertTrue(self.record(event_body("evt_second")).first_seen)
        self.assertEqual(len(self.inbox.pending(self.scope)), 2)

    def test_scope_isolates_tenant_endpoint_account_and_mode(self):
        scopes = (
            self.scope, replace(self.scope, tenant_id="second"),
            replace(self.scope, endpoint_id="second"),
            replace(self.scope, provider_account="acct_second"),
            replace(self.scope, livemode=True),
        )
        for scope in scopes:
            with self.subTest(scope=scope):
                self.assertTrue(self.record(event_body(live=scope.livemode), scope=scope).first_seen)
                self.assertEqual(len(self.inbox.pending(scope)), 1)

    def test_same_id_cannot_change_type_or_object_reference(self):
        first = self.record()
        for field in ("type", "reference"):
            event = json.loads(event_body())
            if field == "type":
                event["type"] = "payment_intent.payment_failed"
            else:
                event["data"]["object"]["id"] = "pi_other"
            with self.subTest(field=field), self.assertRaisesRegex(StripeInboxError, "conflicting"):
                self.record(json.dumps(event).encode())
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))

    def test_authentication_precedes_json_parsing_and_duplicates(self):
        with self.assertRaises(StripeDeliveryError):
            self.record(b"not-json", secret="synthetic-wrong")
        self.record()
        with self.assertRaises(StripeDeliveryError):
            self.record(secret="synthetic-wrong")
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_stale_delivery_cannot_bypass_verification_on_duplicate(self):
        self.record()
        with self.assertRaises(StripeDeliveryError):
            self.record(now=NOW + 301)

    def test_malformed_utf8_json_or_ambiguous_keys_are_not_recorded(self):
        bodies = (
            b"\xff", b"not-json", b"[]", b"null",
            event_body().replace(b'"evt_synthetic"', b'"evt_synthetic","id":"evt_other"'),
            event_body().replace(b'"created": 1700000000', b'"created": NaN'),
            event_body().replace(b'"object": "payment_intent"', b'"object": "payment_intent","id":"pi_other"'),
        )
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(StripeInboxError):
                self.record(body)
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_thin_connect_organization_and_other_types_are_explicitly_rejected(self):
        for field, value in (
            ("object", "event_notification"), ("type", "invoice.paid"),
            ("account", "acct_other"), ("context", "organization/context"),
        ):
            event = json.loads(event_body())
            event[field] = value
            with self.subTest(field=field), self.assertRaises(StripeInboxError):
                self.record(json.dumps(event).encode())
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_missing_fields_or_invalid_snapshot_shapes_are_rejected(self):
        for field in ("id", "object", "livemode", "type", "data"):
            event = json.loads(event_body())
            del event[field]
            with self.subTest(field=field), self.assertRaises(StripeInboxError):
                self.record(json.dumps(event).encode())
        for data in (None, [], {"object": []}, {"object": {"id": "ch_wrong", "object": "charge"}}):
            event = json.loads(event_body())
            event["data"] = data
            with self.subTest(data=data), self.assertRaises(StripeInboxError):
                self.record(json.dumps(event).encode())

    def test_event_and_nested_object_mode_are_strict_boolean_bindings(self):
        for nested in (False, True):
            for value in (True, 0, "false", None):
                event = json.loads(event_body())
                target = event["data"]["object"] if nested else event
                target["livemode"] = value
                with self.subTest(nested=nested, value=value), self.assertRaises(StripeInboxError):
                    self.record(json.dumps(event).encode())

    def test_invalid_scope_and_pending_limit_are_explicit_errors(self):
        for changes in ({"tenant_id": ""}, {"endpoint_id": " "}, {"provider_account": None}, {"livemode": 0}):
            with self.subTest(changes=changes), self.assertRaises(StripeInboxError):
                replace(self.scope, **changes)
        for limit in (0, -1, True, 1001, "1"):
            with self.subTest(limit=limit), self.assertRaises(StripeInboxError):
                self.inbox.pending(self.scope, limit=limit)
        with self.assertRaises(StripeInboxError):
            self.inbox.pending(None)
        with self.assertRaises(StripeInboxError):
            self.inbox.record(None, event_body(), header(event_body()), SECRET, now=NOW)

    def test_pending_order_is_local_receipt_order_not_created_timestamp(self):
        newer = json.loads(event_body("evt_arrived_first"))
        older = json.loads(event_body("evt_arrived_second"))
        older["created"] = NOW - 10000000
        self.record(json.dumps(newer).encode())
        self.record(json.dumps(older).encode())
        self.assertEqual(
            [receipt.event_id for receipt in self.inbox.pending(self.scope)],
            ["evt_arrived_first", "evt_arrived_second"],
        )
        self.assertEqual(len(self.inbox.pending(self.scope, limit=1)), 1)

    def test_commit_failure_returns_no_success_and_preserves_no_receipt(self):
        class FailingCommit(sqlite3.Connection):
            def __exit__(self, *args):
                self.rollback()
                raise sqlite3.OperationalError("synthetic commit failure")

        def connect():
            db = sqlite3.connect(self.path, factory=FailingCommit)
            db.row_factory = sqlite3.Row
            return db

        with patch.object(self.inbox, "_connect", side_effect=connect):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.record()
        self.assertEqual(StripeEventInbox(self.path).pending(self.scope), ())
        self.assertTrue(self.record().first_seen)

    def test_sensitive_payload_and_endpoint_secret_are_not_persisted(self):
        event = json.loads(event_body())
        event["data"]["object"]["client_secret"] = "SYNTHETIC_CLIENT_SECRET_MARKER"
        event["data"]["object"]["metadata"] = {"private": "SYNTHETIC_PRIVATE_MARKER"}
        self.record(json.dumps(event).encode())
        content = self.path.read_bytes()
        for marker in (SECRET, "SYNTHETIC_CLIENT_SECRET_MARKER", "SYNTHETIC_PRIVATE_MARKER"):
            self.assertNotIn(marker.encode(), content)

    def test_payment_failed_snapshot_still_only_schedules_readback(self):
        event = json.loads(event_body())
        event["type"] = "payment_intent.payment_failed"
        result = self.record(json.dumps(event).encode())
        self.assertTrue(result.first_seen)
        self.assertTrue(result.receipt.requires_readback)

    def test_receipt_and_duplicate_cannot_close_unknown_or_allow_new_payment(self):
        journal = PaymentAttemptJournal(Path(self.directory.name) / "payments.sqlite3")
        op = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("shop", "USD", "sku", 1, 1000),
        )
        journal.reserve(op)
        self.record()
        self.record()
        self.assertEqual(journal.read(op).outcome, "unknown")
        self.assertIsNone(journal.read(op).provider_reference)
        self.assertFalse(journal.reserve(op).dispatch_allowed)


if __name__ == "__main__":
    unittest.main()
