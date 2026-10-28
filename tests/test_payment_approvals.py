"""Synthetic same-file approval ordering, expiry, persistence and rollback."""

import json
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Event
from unittest.mock import Mock, patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout, CheckoutStore
from lab.checkout_admission import CheckoutAdmissionError, validate_signed_checkout
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot


NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class PaymentApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.approvals.approve(self.operation, expires_at=EXPIRY)

    def admit(self, *, operation=None, journal=None, approvals=None, body=None, **changes):
        operation = self.operation if operation is None else operation
        body = json.dumps(asdict(operation.checkout)).encode() if body is None else body
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", URI,
            "application/json", digest,
        )
        values = {
            "clock": lambda: NOW, "expected_target_uri": URI, "method": "POST",
            "target_uri": URI, "content_type": "application/json",
            "content_digest": digest, "content_encoding": None, "body": body,
        }
        values.update(changes)
        return (self.approvals if approvals is None else approvals).admit(
            self.journal if journal is None else journal, operation, snapshot, **values,
        )

    def assert_unreserved(self, operation=None) -> None:
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation if operation is None else operation)

    def failing_commit(self, query):
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(connection.execute(query).fetchone()[0])
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        connection = sqlite3.connect(self.path, factory=FailingCommit)
        connection.row_factory = sqlite3.Row
        return connection, observed

    def test_valid_approval_admits_once_and_keeps_unknown(self) -> None:
        first, retry = self.admit(), self.admit()
        self.assertTrue(first.dispatch_allowed)
        self.assertFalse(retry.dispatch_allowed)
        self.assertEqual(first.attempt, retry.attempt)
        self.assertEqual(first.attempt.outcome, "unknown")
        self.assertIsNone(first.attempt.provider_reference)

    def test_missing_approval_cannot_be_supplied_by_a_signature(self) -> None:
        operation = replace(self.operation, approval_id="unrecorded")
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.admit(operation=operation)
        self.assert_unreserved()

    def test_expiry_metadata_has_strict_signed64_bounds(self) -> None:
        for value in (True, 1.5, None, "1700000060", 0, -1, 2**63):
            with self.subTest(value=value):
                with self.assertRaises(PaymentApprovalError):
                    self.approvals.approve(
                        replace(self.operation, approval_id="other"), expires_at=value,
                    )
        self.approvals.approve(
            replace(self.operation, approval_id="maximum"), expires_at=2**63 - 1,
        )

    def test_operator_methods_require_validated_operation_type(self) -> None:
        for value in (None, {}, "approval"):
            with self.subTest(value=value):
                with self.assertRaises(PaymentApprovalError):
                    self.approvals.approve(value, expires_at=EXPIRY)
                with self.assertRaises(PaymentApprovalError):
                    self.approvals.revoke(value)
        self.assert_unreserved()

    def test_approval_binds_every_existing_operation_dimension(self) -> None:
        for field in (
            "operation_id", "provider", "provider_account", "idempotency_key",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.admit(operation=replace(self.operation, **{field: "different"}))
        for field, value in (
            ("merchant", "other-shop"), ("currency", "EUR"), ("sku", "other-sku"),
            ("quantity", 3), ("amount", 2000),
        ):
            with self.subTest(field=field):
                checkout = replace(self.operation.checkout, **{field: value})
                with self.assertRaisesRegex(PaymentApprovalError, "bound operation"):
                    self.admit(operation=replace(self.operation, checkout=checkout))
        self.assert_unreserved()

    def test_tenant_and_approval_scope_are_not_interchangeable(self) -> None:
        for operation in (
            replace(self.operation, tenant_id="other-tenant"),
            replace(self.operation, approval_id="other-approval"),
        ):
            with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
                self.admit(operation=operation)
        other = replace(self.operation, tenant_id="other-tenant", idempotency_key="other-key")
        self.approvals.approve(other, expires_at=EXPIRY)
        self.assertTrue(self.admit(operation=other).dispatch_allowed)
        self.assertTrue(self.admit().dispatch_allowed)

    def test_approvals_cannot_be_replaced_extended_or_reactivated(self) -> None:
        for expires_at in (EXPIRY, EXPIRY + 1):
            with self.assertRaisesRegex(PaymentApprovalError, "replacement is forbidden"):
                self.approvals.approve(self.operation, expires_at=expires_at)
        self.approvals.revoke(self.operation)
        with self.assertRaises(PaymentApprovalError):
            self.approvals.approve(self.operation, expires_at=EXPIRY + 100)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()
        self.assert_unreserved()

    def test_exact_expiry_rejects_even_existing_retry(self) -> None:
        self.assertTrue(self.admit(clock=lambda: EXPIRY - 1).dispatch_allowed)
        for now in (EXPIRY, EXPIRY + 1):
            with self.subTest(now=now):
                with self.assertRaisesRegex(PaymentApprovalError, "expired"):
                    self.admit(clock=lambda: now)
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_expired_first_admission_does_not_reserve(self) -> None:
        with self.assertRaisesRegex(PaymentApprovalError, "expired"):
            self.admit(clock=lambda: EXPIRY)
        self.assert_unreserved()

    def test_clock_values_are_strict_and_do_not_create_defaults(self) -> None:
        for now in (True, 1.5, None, "1700000000", -1, 2**63):
            with self.subTest(now=now):
                with self.assertRaisesRegex(PaymentApprovalError, "Clock must return"):
                    self.admit(clock=lambda: now)
        self.assert_unreserved()

    def test_invalid_stored_expiry_fails_explicitly(self) -> None:
        with closing(self.approvals._connect()) as db, db:
            db.execute("UPDATE payment_approvals SET expires_at=?", (NOW + 0.5,))
        with self.assertRaisesRegex(PaymentApprovalError, "Stored approval expiry"):
            self.admit()
        self.assert_unreserved()

    def test_clock_failure_propagates_without_reservation(self) -> None:
        clock = Mock(side_effect=OSError("synthetic clock unavailable"))
        with self.assertRaisesRegex(OSError, "clock unavailable"):
            self.admit(clock=clock)
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_noncallable_clock_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(PaymentApprovalError, "clock callable"):
            self.admit(clock=NOW)
        self.assert_unreserved()

    def test_revoke_is_idempotent_and_blocks_first_dispatch(self) -> None:
        self.approvals.revoke(self.operation)
        self.approvals.revoke(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()
        self.assert_unreserved()

    def test_later_revocation_cannot_undo_committed_unknown(self) -> None:
        decision = self.admit()
        self.approvals.revoke(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()
        self.assertEqual(self.journal.read(self.operation), decision.attempt)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_terminal_state_remains_readable_after_revocation(self) -> None:
        self.admit()
        terminal = self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_synthetic",
        )
        self.approvals.revoke(self.operation)
        with self.assertRaises(PaymentApprovalError):
            self.admit()
        self.assertEqual(self.journal.read(self.operation), terminal)

    def test_revoke_requires_exact_binding_and_known_scope(self) -> None:
        for operation in (
            replace(self.operation, approval_id="unknown"),
            replace(self.operation, idempotency_key="changed-key"),
        ):
            with self.assertRaises(PaymentApprovalError):
                self.approvals.revoke(operation)
        self.assertTrue(self.admit().dispatch_allowed)

    def test_distinct_database_rejects_before_reservation(self) -> None:
        other = PaymentAttemptJournal(self.path.with_name("separate.sqlite3"))
        with self.assertRaisesRegex(PaymentApprovalError, "same resolved"):
            self.admit(journal=other)
        with self.assertRaises(AttemptConflict):
            other.read(self.operation)
        self.assert_unreserved()

    def test_binding_and_semantic_errors_precede_clock_and_reservation(self) -> None:
        clock = Mock(return_value=NOW)
        with patch.object(self.journal, "_reserve_in_transaction") as reserve:
            with self.assertRaises(RequestBindingError):
                self.admit(clock=clock, content_digest="sha-256=:invalid:")
            with self.assertRaises(CheckoutAdmissionError):
                self.admit(clock=clock, body=b'{"amount":1}')
            reserve.assert_not_called()
        clock.assert_not_called()
        self.assert_unreserved()

    def test_pure_checkout_validation_has_no_journal_side_effect(self) -> None:
        body = json.dumps(asdict(self.operation.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", URI, "application/json", digest,
        )
        self.assertIsNone(validate_signed_checkout(
            self.operation, snapshot, expected_target_uri=URI, method="POST",
            target_uri=URI, content_type="application/json", content_digest=digest,
            content_encoding=None, body=body,
        ))
        self.assert_unreserved()

    def test_reservation_participant_requires_active_transaction(self) -> None:
        with closing(self.approvals._connect()) as db:
            with self.assertRaisesRegex(AttemptConflict, "active transaction"):
                self.journal._reserve_in_transaction(db, self.operation)
        self.assert_unreserved()

    def test_no_nested_public_journal_connection_is_used(self) -> None:
        with patch.object(self.journal, "_connect", side_effect=AssertionError("nested connection")):
            self.assertTrue(self.admit().dispatch_allowed)
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_post_insert_failure_rolls_back_reservation(self) -> None:
        reserve = self.journal._reserve_in_transaction
        observed = []

        def fail(db, operation):
            reserve(db, operation)
            observed.append(db.execute("SELECT COUNT(*) FROM payment_attempts").fetchone()[0])
            raise sqlite3.OperationalError("synthetic after insert")

        with patch.object(self.journal, "_reserve_in_transaction", side_effect=fail):
            with self.assertRaisesRegex(sqlite3.OperationalError, "after insert"):
                self.admit()
        self.assertEqual(observed, [1])
        self.assert_unreserved()
        self.assertTrue(self.admit().dispatch_allowed)

    def test_reservation_commit_failure_returns_no_dispatch(self) -> None:
        connection, observed = self.failing_commit("SELECT COUNT(*) FROM payment_attempts")
        with patch.object(self.approvals, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.admit()
        self.assertEqual(observed, [1])
        self.assert_unreserved()
        self.assertTrue(self.admit().dispatch_allowed)

    def test_approval_commit_failure_does_not_persist_a_grant(self) -> None:
        other = replace(self.operation, approval_id="second-approval")
        connection, observed = self.failing_commit(
            "SELECT COUNT(*) FROM payment_approvals WHERE approval_id='second-approval'",
        )
        with patch.object(self.approvals, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.approvals.approve(other, expires_at=EXPIRY)
        self.assertEqual(observed, [1])
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.admit(operation=other)
        self.assert_unreserved()

    def test_revoke_commit_failure_does_not_claim_revocation(self) -> None:
        connection, observed = self.failing_commit("SELECT revoked FROM payment_approvals")
        with patch.object(self.approvals, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.approvals.revoke(self.operation)
        self.assertEqual(observed, [1])
        self.assertTrue(self.admit().dispatch_allowed)

    def test_concurrent_admissions_grant_one_dispatch(self) -> None:
        barrier = Barrier(2)

        def act(_):
            barrier.wait(timeout=10)
            return self.admit()

        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(act, range(2)))
        self.assertEqual(sum(d.dispatch_allowed for d in decisions), 1)

    def test_clock_is_sampled_after_waiting_for_write_lock(self) -> None:
        attempting = Event()
        current_time = [NOW]
        clock = Mock(side_effect=lambda: current_time[0])
        original_connect = self.approvals._connect

        def connect():
            db = original_connect()
            db.set_trace_callback(
                lambda statement: attempting.set() if statement == "BEGIN IMMEDIATE" else None,
            )
            return db

        with closing(sqlite3.connect(self.path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with patch.object(self.approvals, "_connect", side_effect=connect):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.admit, clock=clock)
                    try:
                        self.assertTrue(attempting.wait(timeout=5))
                        clock.assert_not_called()
                        current_time[0] = EXPIRY
                    finally:
                        blocker.commit()
                    with self.assertRaisesRegex(PaymentApprovalError, "expired"):
                        future.result(timeout=10)
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_committed_revocation_wins_over_waiting_admission(self) -> None:
        attempting = Event()
        original_connect = self.approvals._connect

        def connect():
            db = original_connect()
            db.set_trace_callback(
                lambda statement: attempting.set() if statement == "BEGIN IMMEDIATE" else None,
            )
            return db

        with closing(sqlite3.connect(self.path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            blocker.execute("UPDATE payment_approvals SET revoked=1")
            with patch.object(self.approvals, "_connect", side_effect=connect):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.admit)
                    try:
                        self.assertTrue(attempting.wait(timeout=5))
                    finally:
                        blocker.commit()
                    with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
                        future.result(timeout=10)
        self.assert_unreserved()

    def test_concurrent_revoke_and_admission_follow_serial_order(self) -> None:
        barrier = Barrier(2)

        def act(revoke):
            barrier.wait(timeout=10)
            if revoke:
                self.approvals.revoke(self.operation)
                return "revoked"
            try:
                return self.admit()
            except PaymentApprovalError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            admission, revocation = list(pool.map(act, (False, True)))
        self.assertEqual(revocation, "revoked")
        if admission == "rejected":
            self.assert_unreserved()
        else:
            self.assertTrue(admission.dispatch_allowed)
            self.assertEqual(self.journal.read(self.operation), admission.attempt)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()

    def test_legacy_reservation_cannot_supply_a_missing_approval(self) -> None:
        operation = replace(self.operation, approval_id="unrecorded")
        first = self.journal.reserve(operation)
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.admit(operation=operation)
        self.assertEqual(self.journal.read(operation), first.attempt)
        self.assertFalse(self.journal.reserve(operation).dispatch_allowed)

    def test_legacy_global_mandate_is_not_a_scoped_operation_approval(self) -> None:
        operation = replace(self.operation, approval_id="legacy-approval")
        CheckoutStore(self.path).approve(
            operation.approval_id, operation.checkout,
            max_amount=operation.checkout.amount, expires_at=EXPIRY,
        )
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded approval"):
            self.admit(operation=operation)
        self.assert_unreserved()

    def test_persisted_metadata_contains_no_raw_body_or_tokens(self) -> None:
        with closing(self.approvals._connect()) as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(payment_approvals)")}
            row = dict(db.execute("SELECT * FROM payment_approvals").fetchone())
        self.assertEqual(columns, {"tenant_id", "approval_id", "fingerprint", "expires_at", "revoked"})
        self.assertEqual(row["fingerprint"], self.operation.fingerprint)
        self.assertNotIn("synthetic-sku", json.dumps(row))
        self.assertNotIn("acct_synthetic", json.dumps(row))

    def test_fresh_process_keeps_revocation_and_unknown_state(self) -> None:
        self.admit()
        self.approvals.revoke(self.operation)
        script = """
import json, sys
from pathlib import Path
from dataclasses import asdict
from lab.checkout import Checkout
from lab.payment_attempts import PaymentOperation, PaymentAttemptJournal
from lab.payment_approvals import PaymentApprovalStore, PaymentApprovalError
from lab.request_binding import RequestSignatureSnapshot, MUTATION_COMPONENTS
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
path = Path(sys.argv[1])
operation = PaymentOperation('tenant','operation','approval','stripe:test',
    'acct_synthetic','key',Checkout('synthetic-shop','USD','synthetic-sku',2,1000))
journal = PaymentAttemptJournal(path)
body = json.dumps(asdict(operation.checkout)).encode()
uri = 'https://synthetic-shop.example/checkout?cart=one'
digest = compute_rfc9530_content_digest(body)
snapshot = RequestSignatureSnapshot('sig1','synthetic-key',MUTATION_COMPONENTS,
    'POST',uri,'application/json',digest)
try:
    PaymentApprovalStore(path).admit(journal,operation,snapshot,clock=lambda:1700000000,
        expected_target_uri=uri,method='POST',target_uri=uri,content_type='application/json',
        content_digest=digest,content_encoding=None,body=body)
except PaymentApprovalError:
    result = 'blocked'
else:
    raise AssertionError('revocation did not survive process restart')
print(json.dumps({'admission':result,'outcome':journal.read(operation).outcome}))
"""
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(output.stdout), {"admission": "blocked", "outcome": "unknown"})


if __name__ == "__main__":
    unittest.main()
