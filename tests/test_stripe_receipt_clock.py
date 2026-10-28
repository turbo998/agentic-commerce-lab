"""Synthetic ingress/post-lock receipt time, actual SQL waiting and old-path compatibility."""

import hashlib
import hmac
import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import Mock, patch

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


class StripeReceiptClockTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

    def record(self, *, clock=None, body=None, signature=None, secret=SECRET, tolerance=300):
        body = event_body() if body is None else body
        signature = header(body) if signature is None else signature
        return self.inbox.record_with_clock(
            self.scope, body, signature, secret,
            clock=Mock(return_value=NOW) if clock is None else clock, tolerance=tolerance,
        )

    def test_success_takes_two_samples_and_returns_original_receipt_shape(self):
        clock = Mock(side_effect=(NOW, NOW + 1))
        decision = self.record(clock=clock)
        self.assertTrue(decision.first_seen)
        self.assertTrue(decision.receipt.requires_readback)
        self.assertEqual(clock.call_count, 2)
        self.assertEqual(set(asdict(decision.receipt)), {
            "event_id", "event_type", "provider_reference", "payload_sha256", "requires_readback",
        })

    def test_required_clock_has_no_implicit_or_none_fallback(self):
        body = event_body()
        with self.assertRaises(TypeError):
            self.inbox.record_with_clock(self.scope, body, header(body), SECRET)
        for value in (None, NOW, True, "clock"):
            with self.subTest(value=value), self.assertRaises(StripeInboxError):
                self.inbox.record_with_clock(self.scope, body, header(body), SECRET, clock=value)
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_invalid_scope_rejects_without_sampling(self):
        clock = Mock(return_value=NOW)
        body = event_body()
        with self.assertRaises(StripeInboxError):
            self.inbox.record_with_clock(None, body, header(body), SECRET, clock=clock)
        clock.assert_not_called()

    def test_invalid_first_clock_never_connects(self):
        for value in (None, True, -1, 1.0, "time", 2**63):
            clock = Mock(return_value=value)
            with self.subTest(value=value), patch.object(self.inbox, "_connect") as connect:
                with self.assertRaises(StripeDeliveryError):
                    self.record(clock=clock)
                connect.assert_not_called()
            clock.assert_called_once_with()
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_first_clock_exception_is_explicit_without_storage(self):
        clock = Mock(side_effect=RuntimeError("synthetic ingress clock failure"))
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "ingress clock"):
                self.record(clock=clock)
            connect.assert_not_called()
        clock.assert_called_once_with()

    def test_invalid_second_clock_creates_no_receipt(self):
        for value in (None, True, -1, 1.0, "time", 2**63):
            clock = Mock(side_effect=(NOW, value))
            with self.subTest(value=value), self.assertRaises(StripeDeliveryError):
                self.record(clock=clock)
            self.assertEqual(clock.call_count, 2)
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_second_clock_exception_rolls_back_without_fallback(self):
        clock = Mock(side_effect=(NOW, RuntimeError("synthetic admission clock failure")))
        with self.assertRaisesRegex(RuntimeError, "admission clock"):
            self.record(clock=clock)
        self.assertEqual(clock.call_count, 2)
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_initially_stale_or_future_delivery_never_reaches_database(self):
        for now in (NOW - 301, NOW + 301):
            clock = Mock(return_value=now)
            with self.subTest(now=now), patch.object(self.inbox, "_connect") as connect:
                with self.assertRaisesRegex(StripeDeliveryError, "tolerance"):
                    self.record(clock=clock)
                connect.assert_not_called()
            clock.assert_called_once_with()

    def test_invalid_hmac_precedes_json_and_second_sample(self):
        body = b"not-json"
        clock = Mock(return_value=NOW)
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaisesRegex(StripeDeliveryError, "mismatch"):
                self.record(clock=clock, body=body, signature=header(body, secret="synthetic-wrong"))
            connect.assert_not_called()
        clock.assert_called_once_with()

    def test_invalid_json_never_reaches_second_sample_or_database(self):
        clock = Mock(return_value=NOW)
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaises(StripeInboxError):
                self.record(clock=clock, body=b"not-json")
            connect.assert_not_called()
        clock.assert_called_once_with()

    def test_duplicate_json_members_remain_explicit_errors(self):
        body = event_body().replace(b'"evt_synthetic"', b'"evt_synthetic","id":"evt_other"')
        clock = Mock(return_value=NOW)
        with patch.object(self.inbox, "_connect") as connect:
            with self.assertRaisesRegex(StripeInboxError, "Duplicate"):
                self.record(clock=clock, body=body)
            connect.assert_not_called()
        clock.assert_called_once_with()

    def test_invalid_tolerance_cannot_disable_either_boundary(self):
        for value in (0, -1, True, 300.0, "300", None):
            clock = Mock(return_value=NOW)
            with self.subTest(value=value), patch.object(self.inbox, "_connect") as connect:
                with self.assertRaises(StripeDeliveryError):
                    self.record(clock=clock, tolerance=value)
                connect.assert_not_called()
            clock.assert_called_once_with()

    def test_exact_past_and_future_post_lock_boundaries_are_inclusive(self):
        for offset in (-300, 300):
            clock = Mock(side_effect=(NOW, NOW + offset))
            with self.subTest(offset=offset):
                self.assertTrue(self.record(clock=clock).receipt.requires_readback)
                self.assertEqual(clock.call_count, 2)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_second_sample_beyond_past_boundary_is_rejected(self):
        with self.assertRaisesRegex(StripeDeliveryError, "tolerance"):
            self.record(clock=Mock(side_effect=(NOW, NOW + 301)))
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_second_sample_clock_rollback_beyond_future_boundary_is_rejected(self):
        with self.assertRaisesRegex(StripeDeliveryError, "tolerance"):
            self.record(clock=Mock(side_effect=(NOW, NOW - 301)))
        self.assertEqual(self.inbox.pending(self.scope), ())

    def blocked_record(self, before_release, clock, *, legacy=False):
        attempted = Event()
        connect = self.inbox._connect
        body = event_body()
        signature = header(body)

        def traced_connect():
            db = connect()
            db.set_trace_callback(lambda sql: attempted.set() if sql == "BEGIN IMMEDIATE" else None)
            return db

        def run():
            if legacy:
                return self.inbox.record(self.scope, body, signature, SECRET, now=NOW)
            return self.record(clock=clock, body=body, signature=signature)

        with closing(sqlite3.connect(self.path)) as blocker, blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with patch.object(self.inbox, "_connect", side_effect=traced_connect):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(run)
                    try:
                        self.assertTrue(attempted.wait(5), "Actual BEGIN was not attempted.")
                        self.assertEqual(clock.call_count, 0 if legacy else 1)
                        self.assertFalse(future.done())
                        before_release()
                    finally:
                        blocker.commit()
                    return future

    def test_actual_lock_wait_crossing_recency_window_rejects_before_receipt_write(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire():
            current[0] = NOW + 301

        future = self.blocked_record(expire, clock)
        self.assertIsInstance(future.exception(), StripeDeliveryError)
        self.assertEqual(clock.call_count, 2)
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_actual_lock_wait_at_exact_boundary_still_records(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def advance():
            current[0] = NOW + 300

        self.assertTrue(self.blocked_record(advance, clock).result().first_seen)
        self.assertEqual(clock.call_count, 2)

    def test_queued_expired_duplicate_preserves_first_receipt_and_claim(self):
        first = self.record()
        claim = self.inbox.claim_next(self.scope, "worker")
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire():
            current[0] = NOW + 301

        self.assertIsInstance(self.blocked_record(expire, clock).exception(), StripeDeliveryError)
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))
        self.inbox.finish_readback(claim)
        self.assertIsNone(self.inbox.claim_next(self.scope, "other"))

    def test_fresh_resigned_duplicate_preserves_receipt_and_active_claim(self):
        first = self.record()
        claim = self.inbox.claim_next(self.scope, "worker")
        body = event_body()
        clock = Mock(side_effect=(NOW + 20, NOW + 21))
        duplicate = self.record(clock=clock, body=body, signature=header(body, timestamp=NOW + 20))
        self.assertFalse(duplicate.first_seen)
        self.assertEqual(duplicate.receipt, first.receipt)
        self.assertEqual(clock.call_count, 2)
        self.inbox.finish_readback(claim)

    def test_reserialized_duplicate_does_not_replace_first_body_hash(self):
        first = self.record()
        body = json.dumps(json.loads(event_body()), separators=(",", ":"), sort_keys=True).encode()
        duplicate = self.record(body=body)
        self.assertFalse(duplicate.first_seen)
        self.assertFalse(duplicate.body_matches_first)
        self.assertEqual(duplicate.receipt, first.receipt)

    def test_hmac_and_json_run_once_between_ingress_sample_and_lock(self):
        events = []
        body = event_body()
        signature = header(body)
        original_hmac, original_json, connect = hmac.new, json.loads, self.inbox._connect

        def clock():
            events.append("clock")
            return NOW

        def authenticate(*args, **kwargs):
            events.append("hmac")
            return original_hmac(*args, **kwargs)

        def parse(*args, **kwargs):
            events.append("json")
            return original_json(*args, **kwargs)

        def traced_connect():
            events.append("connect")
            return connect()

        with patch("lab.stripe_delivery.hmac.new", side_effect=authenticate), \
                patch("lab.stripe_inbox.json.loads", side_effect=parse), \
                patch.object(self.inbox, "_connect", side_effect=traced_connect):
            self.record(clock=clock, body=body, signature=signature)
        self.assertEqual(events, ["clock", "hmac", "json", "connect", "clock"])

    def test_active_secret_overlap_is_not_reverified_under_lock(self):
        body = event_body()
        signature = header(body, secret="synthetic-new")
        original = hmac.new
        clock = Mock(return_value=NOW)
        with patch("lab.stripe_delivery.hmac.new", wraps=original) as authenticate:
            self.assertTrue(self.record(
                clock=clock, body=body, signature=signature,
                secret=("synthetic-old", "synthetic-new"),
            ).first_seen)
        self.assertEqual(authenticate.call_count, 2)
        self.assertEqual(clock.call_count, 2)

    def test_old_fixed_now_path_retains_ingress_only_semantics_after_wait(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire():
            current[0] = NOW + 301

        self.assertTrue(self.blocked_record(expire, clock, legacy=True).result().first_seen)
        clock.assert_not_called()

    def test_concurrent_new_admissions_keep_one_first_seen(self):
        clocks = [Mock(return_value=NOW), Mock(return_value=NOW + 1)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda clock: self.record(clock=clock), clocks))
        self.assertEqual(sum(result.first_seen for result in results), 1)
        for clock in clocks:
            self.assertEqual(clock.call_count, 2)
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)

    def test_reopen_and_mixed_old_new_paths_share_receipt_identity(self):
        first = self.record()
        self.inbox = StripeEventInbox(self.path)
        body = event_body()
        old = self.inbox.record(self.scope, body, header(body), SECRET, now=NOW)
        self.assertFalse(old.first_seen)
        self.assertEqual(old.receipt, first.receipt)
        self.assertEqual(self.inbox.pending(self.scope), (first.receipt,))

    def test_receipt_admission_never_closes_or_redispatches_unknown_payment(self):
        journal = PaymentAttemptJournal(self.path)
        operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("shop", "USD", "sku", 1, 1000),
        )
        before = journal.reserve(operation).attempt
        self.assertTrue(self.record().receipt.requires_readback)
        self.assertEqual(journal.read(operation), before)
        self.assertEqual(before.outcome, "unknown")
        self.assertFalse(journal.reserve(operation).dispatch_allowed)

    def test_real_receipt_insert_failure_rolls_back_before_return(self):
        observed = []

        class FailingWrite(sqlite3.Connection):
            def execute(connection, sql, parameters=()):
                result = super().execute(sql, parameters)
                if sql.startswith("INSERT INTO stripe_event_inbox "):
                    observed.append(connection.execute("SELECT count(*) FROM stripe_event_inbox").fetchone()[0])
                    raise RuntimeError("synthetic post-receipt failure")
                return result

        db = sqlite3.connect(self.path, factory=FailingWrite)
        db.row_factory = sqlite3.Row
        with patch.object(self.inbox, "_connect", return_value=db):
            with self.assertRaisesRegex(RuntimeError, "post-receipt"):
                self.record()
        self.assertEqual(observed, [1])
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_failed_commit_rolls_back_receipt_without_success_result(self):
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(connection.execute("SELECT count(*) FROM stripe_event_inbox").fetchone()[0])
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic receipt commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        with patch.object(self.inbox, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "receipt commit"):
                self.record()
        self.assertEqual(observed, [1])
        self.assertEqual(self.inbox.pending(self.scope), ())

    def test_epoch_zero_and_signed64_maximum_delivery_clocks(self):
        for index, timestamp in enumerate((0, 2**63 - 1)):
            body = event_body(f"evt_bound_{index}")
            clock = Mock(return_value=timestamp)
            with self.subTest(timestamp=timestamp):
                self.assertTrue(self.record(
                    body=body, signature=header(body, timestamp=timestamp), clock=clock,
                ).first_seen)
                self.assertEqual(clock.call_count, 2)

    def test_new_path_does_not_add_schema_or_persist_clock_or_secret_material(self):
        with closing(sqlite3.connect(self.path)) as db:
            before = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
        result = self.record()
        with closing(sqlite3.connect(self.path)) as db:
            after = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
        self.assertEqual(before, after)
        self.assertEqual(result.receipt.payload_sha256, hashlib.sha256(event_body()).hexdigest())
        self.assertNotIn(SECRET, repr(result))


if __name__ == "__main__":
    unittest.main()
