"""Synthetic shared-transaction fencing, rollback and standalone compatibility."""

import json
import os
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from lab.checkout import Checkout
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope
from lab.stripe_observation import StripeObservationError
from lab.stripe_readback import StripeReadbackError, accept_stripe_readback
from tests.test_stripe_inbox import NOW, SECRET, event_body, header


class StripeAtomicReadbackTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.inbox = StripeEventInbox(self.path)
        self.journal = PaymentAttemptJournal(self.path)
        self.scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
        )
        self.journal.reserve(self.operation)
        self.journal.reconcile(
            self.operation, observation="pending", provider_reference="pi_synthetic",
        )
        self.record(event_body())
        self.claim = self.inbox.claim_next(self.scope, "worker-a")
        self.assertIsNotNone(self.claim)
        self.before = self.journal.read(self.operation)
        self.intent = {
            "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
            "amount": 1000, "amount_received": 1000, "currency": "usd",
            "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
        }

    def record(self, body):
        return self.inbox.record(
            self.scope, body, header(body), SECRET, now=NOW,
        )

    def accept(self, *, claim=None, operation=None, intent=None, account="acct_synthetic"):
        return accept_stripe_readback(
            self.inbox, self.journal, self.claim if claim is None else claim,
            self.operation if operation is None else operation,
            retrieved_account=account, intent=self.intent if intent is None else intent,
        )

    def assert_unchanged(self) -> None:
        self.assertEqual(self.journal.read(self.operation), self.before)
        self.assertEqual(self.inbox.active_claims(self.scope), (self.claim,))
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_success_commits_both_without_new_dispatch(self) -> None:
        result = self.accept()
        self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(result.provider_reference, "pi_synthetic")
        self.assertEqual(self.journal.read(self.operation), result)
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        self.assertEqual(len(self.inbox.pending(self.scope)), 1)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_fresh_process_observes_coupled_commit(self) -> None:
        self.accept()
        script = """
import json, sys
from pathlib import Path
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope
p = Path(sys.argv[1])
o = PaymentOperation('tenant','operation','approval','stripe:test','acct_synthetic','key',
    Checkout('synthetic-shop','USD','synthetic-sku',1,1000))
s = StripeInboxScope('tenant','endpoint','acct_synthetic',False)
print(json.dumps({'outcome': PaymentAttemptJournal(p).read(o).outcome,
    'active': len(StripeEventInbox(p).active_claims(s))}))
"""
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(output.stdout), {"outcome": "succeeded", "active": 0})

    def test_different_database_rejects_without_either_mutation(self) -> None:
        other = PaymentAttemptJournal(self.path.with_name("separate.sqlite3"))
        other.reserve(self.operation)
        with self.assertRaisesRegex(StripeReadbackError, "same resolved"):
            accept_stripe_readback(
                self.inbox, other, self.claim, self.operation,
                retrieved_account="acct_synthetic", intent=self.intent,
            )
        self.assertIsNone(other.read(self.operation).provider_reference)
        self.assert_unchanged()

    def test_resolved_path_spelling_is_supported(self) -> None:
        spelling = self.path.parent / "unused" / ".." / self.path.name
        journal = PaymentAttemptJournal(spelling)
        result = accept_stripe_readback(
            self.inbox, journal, self.claim, self.operation,
            retrieved_account="acct_synthetic", intent=self.intent,
        )
        self.assertEqual(result.outcome, "succeeded")
        self.assertEqual(self.inbox.active_claims(self.scope), ())

    def test_distinct_hard_link_name_is_not_a_supported_journal_namespace(self) -> None:
        alias = self.path.with_name("hardlink.sqlite3")
        os.link(self.path, alias)
        journal = PaymentAttemptJournal(self.path)
        journal.path = alias
        with self.assertRaises(StripeReadbackError):
            accept_stripe_readback(
                self.inbox, journal, self.claim, self.operation,
                retrieved_account="acct_synthetic", intent=self.intent,
            )
        self.assert_unchanged()

    def test_stale_owner_cannot_write_payment(self) -> None:
        current = self.inbox.handoff(self.claim, "worker-b")
        with self.assertRaises(StripeInboxError):
            self.accept()
        self.assertEqual(self.journal.read(self.operation), self.before)
        self.assertEqual(self.inbox.active_claims(self.scope), (current,))
        self.assertEqual(self.accept(claim=current).outcome, "succeeded")

    def test_same_worker_new_generation_still_fences_old_handle(self) -> None:
        current = self.inbox.handoff(self.claim, "worker-a")
        with self.assertRaises(StripeInboxError):
            self.accept()
        self.assertEqual(self.journal.read(self.operation), self.before)
        self.assertEqual(current.generation, self.claim.generation + 1)

    def test_forged_receipt_cannot_rebind_subject(self) -> None:
        forged = replace(
            self.claim, receipt=replace(self.claim.receipt, provider_reference="pi_other"),
        )
        with self.assertRaises(StripeInboxError):
            self.accept(claim=forged)
        self.assert_unchanged()

    def test_scope_tenant_account_and_mode_must_match(self) -> None:
        for change in (
            {"tenant_id": "other-tenant"}, {"provider_account": "acct_other"},
            {"provider": "stripe:live"}, {"provider": "other-provider"},
        ):
            with self.subTest(change=change), self.assertRaises(StripeReadbackError):
                self.accept(operation=replace(self.operation, **change))
            self.assert_unchanged()

    def test_missing_operation_is_not_reserved_by_acceptance(self) -> None:
        with self.assertRaises(AttemptConflict):
            self.accept(operation=replace(self.operation, operation_id="unreserved"))
        self.assert_unchanged()

    def test_changed_approval_binding_is_rejected(self) -> None:
        with self.assertRaises(AttemptConflict):
            self.accept(operation=replace(self.operation, approval_id="other-approval"))
        self.assert_unchanged()

    def test_event_cannot_supply_missing_trusted_association(self) -> None:
        operation = replace(
            self.operation, operation_id="unassociated", approval_id="approval-2",
            idempotency_key="key-2",
        )
        self.journal.reserve(operation)
        with self.assertRaises(StripeReadbackError):
            self.accept(operation=operation)
        self.assertIsNone(self.journal.read(operation).provider_reference)
        self.assert_unchanged()

    def test_persisted_receipt_subject_must_match_existing_association(self) -> None:
        self.record(event_body("evt_other", reference="pi_other"))
        other = self.inbox.claim_next(self.scope, "worker-a")
        with self.assertRaises(StripeReadbackError):
            self.accept(claim=other)
        self.assertEqual(self.journal.read(self.operation), self.before)
        self.assertEqual(self.inbox.active_claims(self.scope), (self.claim, other))

    def test_readback_binding_failures_roll_back_and_preserve_claim(self) -> None:
        for change in (
            {"id": "pi_other"}, {"object": "event"}, {"livemode": True},
            {"currency": "eur"}, {"amount": 999}, {"amount": True},
            {"amount_received": 999}, {"status": "failed"},
            {"transfer_data": {}}, {"on_behalf_of": "acct_other"},
        ):
            with self.subTest(change=change), self.assertRaises(StripeObservationError):
                self.accept(intent={**self.intent, **change})
            self.assert_unchanged()
        with self.assertRaises(StripeObservationError):
            self.accept(account="acct_other")
        self.assert_unchanged()

    def test_pending_handles_hint_but_keeps_unknown_and_no_dispatch(self) -> None:
        result = self.accept(intent={
            **self.intent, "status": "processing", "amount_received": 0,
        })
        self.assertEqual(result, self.before)
        self.assertEqual(self.inbox.active_claims(self.scope), ())
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_latest_state_not_success_snapshot_controls_outcome(self) -> None:
        result = self.accept(intent={
            **self.intent, "status": "canceled", "amount_received": 0,
        })
        self.assertEqual(result.outcome, "failed")
        self.assertEqual(self.inbox.active_claims(self.scope), ())

    def test_failed_attempt_snapshot_can_have_latest_success(self) -> None:
        event = json.loads(event_body("evt_old_failure"))
        event["type"] = "payment_intent.payment_failed"
        self.record(json.dumps(event).encode())
        claim = self.inbox.claim_next(self.scope, "worker-b")
        self.assertEqual(self.accept(claim=claim).outcome, "succeeded")
        self.assertEqual(self.inbox.active_claims(self.scope), (self.claim,))

    def test_conflicting_terminal_result_does_not_finish_claim(self) -> None:
        self.journal.reconcile(
            self.operation, observation="failed", provider_reference="pi_synthetic",
        )
        with self.assertRaises(AttemptConflict):
            self.accept()
        self.assertEqual(self.journal.read(self.operation).outcome, "failed")
        self.assertEqual(self.inbox.active_claims(self.scope), (self.claim,))

    def test_standalone_finish_cannot_claim_payment_acceptance(self) -> None:
        self.inbox.finish_readback(self.claim)
        self.inbox.finish_readback(self.claim)
        with self.assertRaises(StripeReadbackError):
            self.accept()
        self.assertEqual(self.journal.read(self.operation), self.before)
        self.assertEqual(self.inbox.active_claims(self.scope), ())

    def test_already_accepted_retry_explicitly_rejects_without_corruption(self) -> None:
        result = self.accept()
        with self.assertRaises(StripeReadbackError):
            self.accept()
        self.assertEqual(self.journal.read(self.operation), result)
        with self.assertRaises(StripeInboxError):
            self.inbox.handoff(self.claim, "worker-b")

    def test_failure_after_payment_update_rolls_back_both(self) -> None:
        with closing(self.inbox._connect()) as db, db:
            db.execute("""
                CREATE TRIGGER fail_completion BEFORE UPDATE OF state
                ON stripe_readback_claims WHEN NEW.state='handled'
                AND (SELECT outcome FROM payment_attempts LIMIT 1)='succeeded'
                BEGIN SELECT RAISE(ABORT,'synthetic after payment update'); END
            """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "after payment update"):
            self.accept()
        self.assert_unchanged()

    def test_commit_failure_after_both_updates_rolls_back_both(self) -> None:
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append((
                        connection.execute("SELECT outcome FROM payment_attempts").fetchone()[0],
                        connection.execute("SELECT state FROM stripe_readback_claims").fetchone()[0],
                    ))
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        connection = sqlite3.connect(self.path, factory=FailingCommit)
        connection.row_factory = sqlite3.Row
        with patch.object(self.inbox, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.accept()
        self.assertEqual(observed, [("succeeded", "handled")])
        self.assert_unchanged()

    def test_transaction_participants_refuse_autocommit_use(self) -> None:
        with closing(self.inbox._connect()) as db:
            with self.assertRaises(AttemptConflict):
                self.journal._reconcile_in_transaction(
                    db, self.operation, observation="succeeded",
                    provider_reference="pi_synthetic",
                )
            with self.assertRaises(StripeInboxError):
                self.inbox._finish_in_transaction(db, self.claim)
        self.assert_unchanged()

    def test_concurrent_handoff_and_acceptance_have_one_winner(self) -> None:
        barrier = Barrier(2)

        def act(accept):
            barrier.wait(timeout=10)
            try:
                return ("accepted", self.accept()) if accept else (
                    "handed-off", self.inbox.handoff(self.claim, "worker-b"),
                )
            except (StripeInboxError, StripeReadbackError):
                return "rejected", None

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(act, (True, False)))
        self.assertEqual(sum(kind == "rejected" for kind, _ in outcomes), 1)
        if outcomes[0][0] == "accepted":
            self.assertEqual(self.journal.read(self.operation).outcome, "succeeded")
            self.assertEqual(self.inbox.active_claims(self.scope), ())
        else:
            self.assertEqual(self.journal.read(self.operation), self.before)
            self.assertEqual(self.inbox.active_claims(self.scope), (outcomes[1][1],))

    def test_concurrent_acceptance_has_one_commit_not_two_success_responses(self) -> None:
        barrier = Barrier(2)

        def act(_):
            barrier.wait(timeout=10)
            try:
                return self.accept().outcome
            except StripeReadbackError:
                return "already-handled"

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(
                list(pool.map(act, range(2))), ["succeeded", "already-handled"],
            )
        self.assertEqual(self.inbox.active_claims(self.scope), ())


if __name__ == "__main__":
    unittest.main()
