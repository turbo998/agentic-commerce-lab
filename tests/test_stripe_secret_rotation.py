"""Synthetic trusted-key overlap, retirement and durable receipt invariants."""

import hashlib
import hmac
import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_delivery import StripeDeliveryError, verify_stripe_delivery
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


OLD = SECRET
NEW = "synthetic-only-rotation-new"
FOREIGN = "synthetic-only-other-endpoint"


class StripeSecretRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
        self.body = event_body()

    def verify(self, secrets=(OLD, NEW), *, body=None, signature=None, now=NOW, tolerance=300):
        body = self.body if body is None else body
        return verify_stripe_delivery(
            body, header(body, secret=NEW) if signature is None else signature,
            secrets, now=now, tolerance=tolerance,
        )

    def record(self, *, secret=NEW, secrets=(OLD, NEW), body=None, scope=None):
        body = self.body if body is None else body
        return self.inbox.record(
            self.scope if scope is None else scope, body, header(body, secret=secret),
            secrets, now=NOW,
        )

    def test_scalar_and_singleton_tuple_have_identical_result(self):
        self.assertEqual(self.verify(NEW), self.verify((NEW,)))
        self.assertEqual(self.record(secrets=NEW).receipt, self.record(secrets=(NEW,)).receipt)

    def test_either_active_secret_and_configuration_order_can_match(self):
        for secrets in ((OLD, NEW), (NEW, OLD)):
            for signing_secret in (OLD, NEW):
                with self.subTest(secrets=secrets, signing_secret=signing_secret):
                    result = self.verify(secrets, signature=header(self.body, secret=signing_secret))
                    self.assertTrue(result.requires_readback)

    def test_multiple_v1_candidates_and_key_orders_use_same_signed_bytes(self):
        old_v1 = header(self.body, secret=OLD).split(",")[1]
        new_v1 = header(self.body, secret=NEW).split(",")[1]
        for secrets in ((OLD, NEW), (NEW, OLD), (NEW,), (OLD,)):
            for values in ((old_v1, new_v1), (new_v1, old_v1)):
                with self.subTest(secrets=secrets, values=values):
                    self.verify(secrets, signature=f"t={NOW},v1={'0' * 64}," + ",".join(values))

    def test_foreign_only_signature_does_not_select_an_unconfigured_key(self):
        with self.assertRaisesRegex(StripeDeliveryError, "mismatch"):
            self.verify(signature=header(self.body, secret=FOREIGN))

    def test_hmac_is_computed_once_per_tried_key_not_per_signature_candidate(self):
        signed = header(self.body, secret=NEW) + f",v1={'0' * 64}"
        with patch("lab.stripe_delivery.hmac.new", wraps=hmac.new) as digest:
            self.verify((OLD, NEW), signature=signed)
            self.assertEqual(digest.call_count, 2)

    def test_every_tuple_entry_is_validated_even_after_a_matching_first_key(self):
        signed = header(self.body, secret=NEW)
        for value in ("", " \t\n", None, b"bytes", 123, True, (NEW,)):
            with self.subTest(value=value), patch("lab.stripe_delivery.hmac.new") as digest:
                with self.assertRaisesRegex(StripeDeliveryError, "nonempty tuple"):
                    self.verify((NEW, value), signature=signed)
                digest.assert_not_called()

    def test_empty_mutable_nested_and_other_configurations_are_explicit_errors(self):
        for value in ((), [], [NEW], {NEW}, {"secret": NEW}, b"bytes", None, 123, ((NEW,),)):
            with self.subTest(value=value), self.assertRaises(StripeDeliveryError):
                self.verify(value)

    def test_duplicate_valid_config_entries_are_harmless(self):
        self.assertEqual(self.verify((NEW, NEW)), self.verify(NEW))

    def test_malformed_v1_is_not_ignored_alongside_a_valid_match(self):
        signed = header(self.body, secret=NEW)
        for signature in (signed + ",v1=abc", "v1=abc," + signed, signed + ",v1="):
            with self.subTest(signature=signature), self.assertRaises(StripeDeliveryError):
                self.verify(signature=signature)

    def test_ambiguous_or_noncanonical_timestamp_still_rejects(self):
        signed = header(self.body, secret=NEW)
        for signature in (signed + f",t={NOW}", signed.replace(f"t={NOW}", f"t=0{NOW}")):
            with self.subTest(signature=signature), self.assertRaises(StripeDeliveryError):
                self.verify(signature=signature)

    def test_rotation_never_allows_reserialization_or_single_byte_mutation(self):
        signed = header(self.body, secret=NEW)
        for body in (self.body + b"\n", self.body.replace(b": ", b":"), self.body[:-1] + b" "):
            with self.subTest(body=body), self.assertRaisesRegex(StripeDeliveryError, "mismatch"):
                self.verify(body=body, signature=signed)

    def test_rotation_does_not_extend_delivery_freshness_or_disable_tolerance(self):
        for offset in (-300, 300):
            self.verify(now=NOW + offset)
        for offset in (-301, 301):
            with self.subTest(offset=offset), self.assertRaisesRegex(StripeDeliveryError, "tolerance"):
                self.verify(now=NOW + offset)
        for tolerance in (0, -1, True, 300.0):
            with self.subTest(tolerance=tolerance), self.assertRaises(StripeDeliveryError):
                self.verify(tolerance=tolerance)

    def test_result_exposes_digest_not_keys_or_selected_key_index(self):
        result = self.verify()
        self.assertEqual(set(asdict(result)), {"timestamp", "payload_sha256", "requires_readback"})
        self.assertEqual(result.payload_sha256, hashlib.sha256(self.body).hexdigest())
        self.assertNotIn(OLD, repr(result))
        self.assertNotIn(NEW, repr(result))

    def test_delivery_verifier_still_does_not_parse_json(self):
        self.assertTrue(self.verify(body=b"not-json").requires_readback)

    def test_resigned_event_is_same_receipt_after_restart_and_retirement(self):
        first = self.record(secret=OLD)
        self.inbox = StripeEventInbox(self.path)
        duplicate = self.record(secrets=(NEW,))
        self.assertTrue(first.first_seen)
        self.assertFalse(duplicate.first_seen)
        self.assertTrue(duplicate.body_matches_first)
        self.assertEqual(first.receipt, duplicate.receipt)
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))

    def test_retired_old_only_signature_rejects_before_duplicate_lookup(self):
        first = self.record(secret=OLD)
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaisesRegex(StripeDeliveryError, "mismatch"):
                self.record(secret=OLD, secrets=(NEW,))
            connect.assert_not_called()
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))

    def test_invalid_key_config_is_not_hidden_by_matching_signature_or_duplicate(self):
        first = self.record()
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaises(StripeDeliveryError):
                self.record(secrets=(NEW, ""))
            connect.assert_not_called()
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))

    def test_signature_and_configuration_checks_precede_json_decoding(self):
        with self.assertRaises(StripeDeliveryError):
            self.record(body=b"not-json", secrets=(NEW, None))
        with self.assertRaises(StripeDeliveryError):
            self.record(body=b"not-json", secret=FOREIGN)
        with self.assertRaises(StripeInboxError):
            self.record(body=b"not-json")
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_reserialized_resigned_body_is_not_a_new_receipt(self):
        first = self.record(secret=OLD)
        changed = json.dumps(json.loads(self.body), separators=(",", ":"), sort_keys=True).encode()
        second = self.record(body=changed)
        self.assertFalse(second.first_seen)
        self.assertFalse(second.body_matches_first)
        self.assertEqual(second.receipt, first.receipt)

    def test_concurrent_old_and_new_signatures_have_one_first_seen_winner(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(lambda secret: self.record(secret=secret), (OLD, NEW)))
        self.assertEqual(sum(decision.first_seen for decision in decisions), 1)
        self.assertEqual(decisions[0].receipt, decisions[1].receipt)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_rotated_redelivery_does_not_resurrect_handled_claim(self):
        self.record(secret=OLD)
        claim = self.inbox.claim_next(self.scope, "worker")
        self.assertIsNotNone(claim)
        assert claim is not None
        self.inbox.finish_readback(claim)
        self.assertFalse(self.record().first_seen)
        self.assertIsNone(self.inbox.claim_next(self.scope, "second-worker"))
        self.assertEqual(self.inbox.active_claims(self.scope), ())

    def test_distinct_events_are_not_business_deduplicated_by_matching_keys(self):
        first = self.record(secret=OLD)
        second = self.record(body=event_body("evt_second"))
        self.assertTrue(first.first_seen and second.first_seen)
        self.assertEqual(len(self.inbox.pending(self.scope)), 2)

    def test_scope_and_mode_validation_are_unchanged(self):
        for scope in (
            self.scope, replace(self.scope, tenant_id="second"),
            replace(self.scope, endpoint_id="second"),
            replace(self.scope, provider_account="acct_second"),
            replace(self.scope, livemode=True),
        ):
            with self.subTest(scope=scope):
                self.assertTrue(self.record(
                    body=event_body(live=scope.livemode), scope=scope,
                ).first_seen)
                self.assertEqual(len(self.inbox.pending(scope)), 1)
        with self.assertRaises(StripeInboxError):
            self.record(scope=replace(self.scope, livemode=True))

    def test_other_endpoint_key_is_not_an_automatic_fallback(self):
        other = replace(self.scope, endpoint_id="other")
        with self.assertRaises(StripeDeliveryError):
            self.record(scope=other, secrets=(FOREIGN,))
        self.assertEqual(self.inbox.pending(other), ())
        self.assertTrue(self.record(scope=other, secret=FOREIGN, secrets=(FOREIGN,)).first_seen)

    def test_rotated_success_event_never_reconciles_or_grants_another_dispatch(self):
        journal = PaymentAttemptJournal(self.path)
        operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("shop", "USD", "sku", 1, 1000),
        )
        self.assertTrue(journal.reserve(operation).dispatch_allowed)
        before = journal.read(operation)
        self.assertTrue(self.record().receipt.requires_readback)
        self.assertEqual(journal.read(operation), before)
        self.assertEqual(before.outcome, "unknown")
        self.assertFalse(journal.reserve(operation).dispatch_allowed)

    def test_secrets_raw_body_and_sensitive_fields_are_not_persisted(self):
        event = json.loads(self.body)
        event["description"] = "SYNTHETIC_PRIVATE_MARKER"
        self.record(body=json.dumps(event).encode())
        with closing(sqlite3.connect(self.path)) as db:
            stored = "\n".join(db.iterdump())
            columns = {row[1] for row in db.execute("PRAGMA table_info(stripe_event_inbox)")}
        for value in (OLD, NEW, "SYNTHETIC_PRIVATE_MARKER"):
            self.assertNotIn(value, stored)
        self.assertEqual(columns, {
            "tenant_id", "endpoint_id", "provider_account", "livemode",
            "event_id", "event_type", "provider_reference", "payload_sha256",
        })


if __name__ == "__main__":
    unittest.main()
