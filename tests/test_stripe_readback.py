"""Synthetic local claim fencing, explicit recovery and non-payment invariants."""

import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import ReadbackClaim, StripeEventInbox, StripeInboxError, StripeInboxScope
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


class FailingCommit(sqlite3.Connection):
    def __exit__(self, *args):
        self.rollback()
        raise sqlite3.OperationalError("synthetic commit failure")


class StripeReadbackTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

    def record(self, event_id="evt_synthetic", scope=None):
        scope = self.scope if scope is None else scope
        body = event_body(event_id, live=scope.livemode)
        return self.inbox.record(scope, body, header(body), SECRET, now=NOW)

    def claim(self):
        self.record()
        claim = self.inbox.claim_next(self.scope, "worker-a")
        self.assertIsNotNone(claim)
        return claim

    def failed_connection(self):
        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        return db

    def test_empty_inbox_has_no_available_work(self):
        self.assertIsNone(self.inbox.claim_next(self.scope, "worker-a"))
        self.assertEqual(self.inbox.active_claims(self.scope), ())

    def test_claim_is_durable_and_not_automatically_reassigned(self):
        claim = self.claim()
        reopened = StripeEventInbox(self.path)
        self.assertEqual(reopened.active_claims(self.scope), (claim,))
        self.assertIsNone(reopened.claim_next(self.scope, "worker-b"))
        self.assertEqual(claim.generation, 1)

    def test_concurrent_claims_grant_one_handle(self):
        self.record()
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda worker: self.inbox.claim_next(self.scope, worker), ("a", "b")))
        self.assertEqual(sum(claim is not None for claim in claims), 1)

    def test_different_events_for_same_object_have_distinct_work(self):
        self.record("evt_first")
        self.record("evt_second")
        first = self.inbox.claim_next(self.scope, "worker-a")
        second = self.inbox.claim_next(self.scope, "worker-b")
        self.assertNotEqual(first.receipt.event_id, second.receipt.event_id)
        self.assertEqual(first.receipt.provider_reference, second.receipt.provider_reference)

    def test_handoff_invalidates_old_completion_and_persists_generation(self):
        old = self.claim()
        current = self.inbox.handoff(old, "worker-b")
        self.assertEqual(current.generation, 2)
        self.assertEqual(StripeEventInbox(self.path).active_claims(self.scope), (current,))
        with self.assertRaisesRegex(StripeInboxError, "stale"):
            self.inbox.finish_readback(old)
        self.inbox.finish_readback(current)
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        with self.assertRaises(StripeInboxError):
            self.inbox.finish_readback(old)

    def test_same_worker_handoff_still_fences_aba(self):
        old = self.claim()
        current = self.inbox.handoff(old, old.worker_id)
        self.assertEqual(current.worker_id, old.worker_id)
        self.assertEqual(current.generation, old.generation + 1)
        with self.assertRaises(StripeInboxError):
            self.inbox.finish_readback(old)

    def test_stale_handoff_cannot_take_back_current_work(self):
        old = self.claim()
        current = self.inbox.handoff(old, "worker-b")
        with self.assertRaises(StripeInboxError):
            self.inbox.handoff(old, "worker-c")
        self.assertEqual(self.inbox.active_claims(self.scope), (current,))

    def test_concurrent_handoffs_have_one_compare_and_increment_winner(self):
        old = self.claim()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.inbox.handoff, old, worker) for worker in ("b", "c")]
            successes, conflicts = [], []
            for future in futures:
                try:
                    successes.append(future.result())
                except StripeInboxError as error:
                    conflicts.append(error)
        self.assertEqual((len(successes), len(conflicts)), (1, 1))
        self.assertEqual(successes[0].generation, 2)

    def test_finish_is_idempotent_and_redelivery_does_not_resurrect_work(self):
        claim = self.claim()
        self.inbox.finish_readback(claim)
        self.inbox.finish_readback(claim)
        self.assertFalse(self.record().first_seen)
        self.assertIsNone(self.inbox.claim_next(self.scope, "worker-b"))
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        self.assertEqual(self.inbox.pending(self.scope), (claim.receipt,))
        self.assertTrue(claim.receipt.requires_readback)

    def test_handled_work_cannot_be_handed_off(self):
        claim = self.claim()
        self.inbox.finish_readback(claim)
        with self.assertRaisesRegex(StripeInboxError, "Handled"):
            self.inbox.handoff(claim, "worker-b")

    def test_scope_isolates_active_work(self):
        scopes = (
            self.scope, replace(self.scope, tenant_id="second"),
            replace(self.scope, endpoint_id="second"),
            replace(self.scope, provider_account="acct_second"),
            replace(self.scope, livemode=True),
        )
        for scope in scopes:
            self.record(scope=scope)
            claim = self.inbox.claim_next(scope, "worker-a")
            self.assertEqual(self.inbox.active_claims(scope), (claim,))
        self.assertEqual(len(self.inbox.active_claims(self.scope)), 1)

    def test_modified_claim_bindings_are_rejected_without_state_change(self):
        claim = self.claim()
        invalid = (
            replace(claim, worker_id="other"), replace(claim, generation=2),
            replace(claim, scope=replace(self.scope, tenant_id="missing")),
            replace(claim, receipt=replace(claim.receipt, provider_reference="pi_other")),
            replace(claim, receipt=replace(claim.receipt, payload_sha256="0" * 64)),
            replace(claim, receipt=replace(claim.receipt, requires_readback=False)),
        )
        for modified in invalid:
            with self.subTest(claim=modified), self.assertRaises(StripeInboxError):
                self.inbox.finish_readback(modified)
        self.assertEqual(self.inbox.active_claims(self.scope), (claim,))

    def test_invalid_claim_worker_scope_and_limits_are_explicit_errors(self):
        claim = self.claim()
        for worker in ("", " ", None, 1):
            with self.subTest(worker=worker), self.assertRaises(StripeInboxError):
                self.inbox.claim_next(self.scope, worker)
            with self.assertRaises(StripeInboxError):
                self.inbox.handoff(claim, worker)
        for generation in (0, -1, True, 1.0, 2**63):
            with self.subTest(generation=generation), self.assertRaises(StripeInboxError):
                replace(claim, generation=generation)
        for limit in (0, -1, True, 1001, "1"):
            with self.subTest(limit=limit), self.assertRaises(StripeInboxError):
                self.inbox.active_claims(self.scope, limit=limit)
        for operation in (self.inbox.finish_readback, lambda value: self.inbox.handoff(value, "b")):
            with self.assertRaises(StripeInboxError):
                operation(None)
        with self.assertRaises(StripeInboxError):
            self.inbox.claim_next(None, "worker-a")
        with self.assertRaises(StripeInboxError):
            self.inbox.active_claims(None)
        with self.assertRaises(StripeInboxError):
            ReadbackClaim(None, claim.receipt, "a", 1)

    def test_generation_exhaustion_cannot_wrap_or_replace_ownership(self):
        claim = self.claim()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE stripe_readback_claims SET generation=?", (2**63 - 1,))
        last = replace(claim, generation=2**63 - 1)
        with self.assertRaisesRegex(StripeInboxError, "exhausted"):
            self.inbox.handoff(last, "worker-b")
        self.assertEqual(self.inbox.active_claims(self.scope), (last,))

    def test_fresh_process_can_finish_durable_current_work(self):
        claim = self.claim()
        script = (
            "import sys; from pathlib import Path; "
            "from lab.stripe_inbox import StripeEventInbox, StripeInboxScope; "
            "db = StripeEventInbox(Path(sys.argv[1])); "
            "scope = StripeInboxScope('tenant','endpoint','acct_synthetic',False); "
            "db.finish_readback(db.active_claims(scope)[0]); print(len(db.active_claims(scope)))"
        )
        result = subprocess.check_output([sys.executable, "-c", script, str(self.path)], text=True)
        self.assertEqual(result.strip(), "0")
        self.assertIsNone(self.inbox.claim_next(self.scope, "worker-b"))
        self.inbox.finish_readback(claim)

    def test_additive_upgrade_preserves_legacy_receipt_schema_and_data(self):
        receipt = self.record().receipt
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DROP TABLE stripe_readback_claims")
        reopened = StripeEventInbox(self.path)
        self.assertEqual(reopened.pending(self.scope), (receipt,))
        self.assertEqual(reopened.claim_next(self.scope, "a").receipt, receipt)

    def test_failed_claim_commit_does_not_grant_or_persist_ownership(self):
        self.record()
        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.claim_next(self.scope, "worker-a")
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        self.assertEqual(self.inbox.claim_next(self.scope, "worker-b").generation, 1)

    def test_failed_handoff_commit_preserves_old_ownership(self):
        old = self.claim()
        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.handoff(old, "worker-b")
        self.assertEqual(self.inbox.active_claims(self.scope), (old,))
        self.inbox.finish_readback(old)

    def test_failed_finish_commit_preserves_active_claim(self):
        claim = self.claim()
        with patch.object(self.inbox, "_connect", side_effect=self.failed_connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.inbox.finish_readback(claim)
        self.assertEqual(self.inbox.active_claims(self.scope), (claim,))
        self.inbox.finish_readback(claim)

    def test_active_enumeration_is_bounded_and_in_local_receipt_order(self):
        for event_id in ("evt_first", "evt_second"):
            self.record(event_id)
            self.inbox.claim_next(self.scope, "worker-a")
        active = self.inbox.active_claims(self.scope, limit=1)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].receipt.event_id, "evt_first")

    def test_handoff_and_handling_do_not_change_payment_authority_or_outcome(self):
        journal = PaymentAttemptJournal(Path(self.directory.name) / "payments.sqlite3")
        op = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("shop", "USD", "sku", 1, 1000),
        )
        journal.reserve(op)
        current = self.inbox.handoff(self.claim(), "worker-b")
        self.inbox.finish_readback(current)
        self.assertEqual(journal.read(op).outcome, "unknown")
        self.assertIsNone(journal.read(op).provider_reference)
        self.assertFalse(journal.reserve(op).dispatch_allowed)


if __name__ == "__main__":
    unittest.main()
