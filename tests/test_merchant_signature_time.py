"""Synthetic same-signature time policy, real lock ordering and compatibility."""

import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import Mock, patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.checkout_admission import CheckoutAdmissionError
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP, MUTATION_COMPONENTS, RequestBindingError,
    RequestSignatureSnapshot, TimedRequestSignatureSnapshot, require_signature_time,
)


NOW = 1700000000
SIGNATURE_EXPIRY = NOW + 10
APPROVAL_EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class MerchantSignatureTimeTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.scope = MerchantSignerScope("tenant", "synthetic-shop", URI, "synthetic-key")
        self.body = json.dumps(asdict(self.operation.checkout)).encode()
        self.digest = compute_rfc9530_content_digest(self.body)
        self.snapshot = RequestSignatureSnapshot(
            "sig1", self.scope.key_id, MUTATION_COMPONENTS, "POST", URI,
            "application/json", self.digest,
        )
        self.signature = TimedRequestSignatureSnapshot(self.snapshot, NOW - 5, SIGNATURE_EXPIRY)
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self.signers.allow(self.scope)

    def admit(self, **changes):
        values = {
            "scope": self.scope, "approvals": self.approvals, "journal": self.journal,
            "operation": self.operation, "signature": self.signature, "clock": lambda: NOW,
            "method": "POST", "target_uri": URI, "content_type": "application/json",
            "content_digest": self.digest, "content_encoding": None, "body": self.body,
        }
        values.update(changes)
        return self.signers.admit(**values)

    def assert_unreserved(self):
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)

    def test_snapshot_and_metadata_are_frozen_not_a_verification_claim(self):
        with self.assertRaises(FrozenInstanceError):
            self.signature.created = 0
        with self.assertRaises(FrozenInstanceError):
            self.signature.signature.key_id = "changed"
        self.assertIs(self.signature.signature, self.snapshot)
        self.assertEqual(self.snapshot.covered_components, MUTATION_COMPONENTS)
        self.assertNotIn("@signature-params", self.snapshot.covered_components)

    def test_creation_boundary_is_inclusive(self):
        signature = replace(self.signature, created=NOW)
        require_signature_time(signature, now=NOW)
        self.assertTrue(self.admit(signature=signature).dispatch_allowed)

    def test_expiry_boundary_is_exclusive_before_any_reservation(self):
        for now in (SIGNATURE_EXPIRY, SIGNATURE_EXPIRY + 1):
            with self.subTest(now=now), self.assertRaisesRegex(RequestBindingError, "window"):
                self.admit(clock=lambda: now)
        self.assert_unreserved()

    def test_future_creation_and_invalid_order_never_admit(self):
        for created, expires in (
            (NOW + 1, SIGNATURE_EXPIRY), (NOW, NOW), (SIGNATURE_EXPIRY, NOW),
        ):
            with self.subTest(created=created, expires=expires), self.assertRaises(RequestBindingError):
                self.admit(signature=replace(self.signature, created=created, expires=expires))
        self.assert_unreserved()

    def test_structured_field_integer_bounds_and_strict_scalar_types(self):
        class IntegerSubclass(int):
            pass

        invalid = (
            None, True, False, 1.0, "1700000000", -1, MAX_SIGNATURE_TIMESTAMP + 1,
            2**63 - 1, float("nan"), float("inf"), IntegerSubclass(NOW),
        )
        for name in ("created", "expires"):
            for value in invalid:
                with self.subTest(name=name, value=value), self.assertRaisesRegex(
                    RequestBindingError, "Structured Field",
                ):
                    self.admit(signature=replace(self.signature, **{name: value}))
        self.assert_unreserved()

    def test_maximum_structured_field_timestamp_is_accepted_not_signed64(self):
        signature = replace(
            self.signature, created=MAX_SIGNATURE_TIMESTAMP - 1, expires=MAX_SIGNATURE_TIMESTAMP,
        )
        require_signature_time(signature, now=MAX_SIGNATURE_TIMESTAMP - 1)
        with self.assertRaisesRegex(RequestBindingError, "window"):
            require_signature_time(signature, now=MAX_SIGNATURE_TIMESTAMP)

    def test_zero_epoch_is_a_valid_creation_timestamp(self):
        require_signature_time(replace(self.signature, created=0, expires=1), now=0)

    def test_trusted_clock_is_strict_nonnegative_signed64(self):
        for value in (None, True, False, -1, 1.0, "1700000000", 2**63, float("nan")):
            with self.subTest(value=value), self.assertRaisesRegex(RequestBindingError, "clock"):
                self.admit(clock=lambda: value)
        with self.assertRaisesRegex(RequestBindingError, "window"):
            require_signature_time(self.signature, now=2**63 - 1)
        self.assert_unreserved()

    def test_pure_validator_requires_one_wrapper_and_one_nested_snapshot(self):
        for value in (None, {}, self.snapshot):
            with self.subTest(value=value), self.assertRaisesRegex(RequestBindingError, "snapshot"):
                require_signature_time(value, now=NOW)
        for nested in (None, {}, self.signature):
            with self.subTest(nested=nested), self.assertRaisesRegex(RequestBindingError, "snapshot"):
                require_signature_time(replace(self.signature, signature=nested), now=NOW)

    def test_required_metadata_has_no_constructor_default(self):
        with self.assertRaises(TypeError):
            TimedRequestSignatureSnapshot(self.snapshot)
        with self.assertRaises(TypeError):
            TimedRequestSignatureSnapshot(self.snapshot, NOW)

    def test_invalid_nested_timed_input_cannot_downgrade_to_legacy(self):
        for nested in (None, {}, self.signature):
            with self.subTest(nested=nested), patch.object(self.signers, "_connect") as connect:
                with self.assertRaises(MerchantSignerError):
                    self.admit(signature=replace(self.signature, signature=nested))
                connect.assert_not_called()
        self.assert_unreserved()

    def test_one_clock_sample_is_reused_by_approval_and_history(self):
        clock = Mock(side_effect=(NOW + 3, APPROVAL_EXPIRY))
        decision = self.admit(clock=clock)
        self.assertTrue(decision.dispatch_allowed)
        clock.assert_called_once_with()
        admission = self.approvals.read_admission(self.operation)
        self.assertEqual(admission.admitted_at, NOW + 3)
        self.assertEqual(admission.expires_at, APPROVAL_EXPIRY)

    def test_valid_retry_does_not_dispatch_or_refresh_original_history(self):
        first = self.admit()
        history = self.approvals.read_admission(self.operation)
        clock = Mock(return_value=SIGNATURE_EXPIRY - 1)
        retry = self.admit(clock=clock)
        clock.assert_called_once_with()
        self.assertFalse(retry.dispatch_allowed)
        self.assertEqual(first.attempt, retry.attempt)
        self.assertEqual(self.approvals.read_admission(self.operation), history)

    def test_expired_retry_cannot_bypass_time_or_change_history(self):
        first = self.admit()
        history = self.approvals.read_admission(self.operation)
        with self.assertRaisesRegex(RequestBindingError, "window"):
            self.admit(clock=lambda: SIGNATURE_EXPIRY)
        self.assertEqual(self.journal.read(self.operation), first.attempt)
        self.assertEqual(self.approvals.read_admission(self.operation), history)

    def test_bare_compatibility_path_has_no_new_signature_time_policy(self):
        clock = Mock(return_value=SIGNATURE_EXPIRY)
        self.assertTrue(self.admit(signature=self.snapshot, clock=clock).dispatch_allowed)
        clock.assert_called_once_with()
        with self.assertRaisesRegex(RequestBindingError, "window"):
            self.admit(clock=lambda: SIGNATURE_EXPIRY)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, SIGNATURE_EXPIRY)

    def test_timed_input_preserves_original_key_route_body_quote_and_coverage_checks(self):
        changes = (
            {"signature": replace(self.signature, signature=replace(self.snapshot, key_id="other"))},
            {"signature": replace(
                self.signature, signature=replace(self.snapshot, covered_components=("@method",)),
            )},
            {"body": self.body + b"\n"}, {"target_uri": URI + "&other=1"},
            {"operation": replace(
                self.operation, checkout=replace(self.operation.checkout, amount=999),
            )},
        )
        for change in changes:
            with self.subTest(change=change), patch.object(self.signers, "_connect") as connect:
                with self.assertRaises((MerchantSignerError, RequestBindingError, CheckoutAdmissionError)):
                    self.admit(**change)
                connect.assert_not_called()
        self.assert_unreserved()

    def test_timed_input_still_requires_clock_callable(self):
        with self.assertRaises(MerchantSignerError):
            self.admit(clock=NOW)
        self.assert_unreserved()

    def test_clock_exception_is_explicit_and_rolls_back(self):
        clock = Mock(side_effect=RuntimeError("synthetic clock unavailable"))
        with self.assertRaisesRegex(RuntimeError, "clock unavailable"):
            self.admit(clock=clock)
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_revoked_permission_still_rejects_before_sampling_clock(self):
        self.signers.revoke(self.scope)
        clock = Mock(return_value=NOW)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit(clock=clock)
        clock.assert_not_called()
        self.assert_unreserved()

    def test_revoked_approval_still_rejects_before_sampling_clock(self):
        self.approvals.revoke(self.operation)
        clock = Mock(return_value=NOW)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit(clock=clock)
        clock.assert_not_called()
        self.assert_unreserved()

    def test_valid_signature_cannot_extend_approval_expiry(self):
        signature = replace(self.signature, expires=APPROVAL_EXPIRY + 10)
        with self.assertRaisesRegex(PaymentApprovalError, "expired"):
            self.admit(signature=signature, clock=lambda: APPROVAL_EXPIRY)
        self.assert_unreserved()

    def blocked_admission(self, before_release, clock, **changes):
        attempted = Event()
        connect = self.signers._connect

        def traced_connect():
            db = connect()
            db.set_trace_callback(lambda sql: attempted.set() if sql == "BEGIN IMMEDIATE" else None)
            return db

        with closing(sqlite3.connect(self.path)) as blocker, blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with patch.object(self.signers, "_connect", side_effect=traced_connect):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.admit, clock=clock, **changes)
                    try:
                        self.assertTrue(attempted.wait(5), "Actual BEGIN was not attempted.")
                        clock.assert_not_called()
                        self.assertFalse(future.done())
                        before_release(blocker)
                    finally:
                        blocker.commit()
                    return future

    def test_actual_lock_wait_crossing_signature_expiry_rejects(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire(db):
            current[0] = SIGNATURE_EXPIRY

        future = self.blocked_admission(expire, clock)
        self.assertIsInstance(future.exception(), RequestBindingError)
        self.assertIn("window", str(future.exception()))
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_actual_lock_wait_still_valid_uses_post_lock_time_in_history(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def advance(db):
            current[0] = SIGNATURE_EXPIRY - 1

        decision = self.blocked_admission(advance, clock).result()
        self.assertTrue(decision.dispatch_allowed)
        clock.assert_called_once_with()
        self.assertEqual(
            self.approvals.read_admission(self.operation).admitted_at, SIGNATURE_EXPIRY - 1,
        )

    def test_future_created_at_ingress_can_become_valid_at_lock_sample(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def advance(db):
            current[0] = NOW + 1

        decision = self.blocked_admission(
            advance, clock, signature=replace(self.signature, created=NOW + 1),
        ).result()
        self.assertTrue(decision.dispatch_allowed)
        clock.assert_called_once_with()
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW + 1)

    def test_committed_revoke_while_timed_admission_waits_still_wins(self):
        clock = Mock(return_value=NOW)

        def revoke(db):
            db.execute(
                "UPDATE merchant_signer_permissions SET revoked=1"
                " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?", self.scope.key,
            )

        future = self.blocked_admission(revoke, clock)
        self.assertIsInstance(future.exception(), MerchantSignerError)
        clock.assert_not_called()
        self.assert_unreserved()

    def test_legacy_reservation_cannot_be_backfilled_by_valid_timed_retry(self):
        first = self.journal.reserve(self.operation)
        self.assertFalse(self.admit().dispatch_allowed)
        self.assertEqual(self.journal.read(self.operation), first.attempt)
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)
        with self.assertRaisesRegex(RequestBindingError, "window"):
            self.admit(clock=lambda: SIGNATURE_EXPIRY)

    def test_error_after_real_reservation_and_history_rolls_back(self):
        original = self.approvals._admit_in_transaction
        observed = []
        clock = Mock(return_value=NOW)

        def fail(db, journal, operation, *, clock):
            original(db, journal, operation, clock=clock)
            observed.append(tuple(db.execute(
                "SELECT (SELECT count(*) FROM payment_attempts),"
                " (SELECT count(*) FROM payment_admissions)",
            ).fetchone()))
            raise RuntimeError("synthetic post-admission failure")

        with patch.object(self.approvals, "_admit_in_transaction", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "post-admission"):
                self.admit(clock=clock)
        self.assertEqual(observed, [(1, 1)])
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_failed_commit_rolls_back_timed_reservation_and_history(self):
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(tuple(connection.execute(
                        "SELECT (SELECT count(*) FROM payment_attempts),"
                        " (SELECT count(*) FROM payment_admissions)",
                    ).fetchone()))
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        with patch.object(self.signers, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.admit()
        self.assertEqual(observed, [(1, 1)])
        self.assert_unreserved()

    def test_concurrent_timed_admissions_grant_one_dispatch(self):
        clocks = [Mock(return_value=NOW), Mock(return_value=NOW + 1)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(lambda clock: self.admit(clock=clock), clocks))
        self.assertEqual(sum(decision.dispatch_allowed for decision in decisions), 1)
        for clock in clocks:
            clock.assert_called_once_with()
        self.assertIn(self.approvals.read_admission(self.operation).admitted_at, (NOW, NOW + 1))

    def test_admission_preserves_initialized_schema_and_distinct_approval_history(self):
        with closing(sqlite3.connect(self.path)) as db:
            before = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
        self.admit()
        self.signers = MerchantSignerStore(self.path)
        self.assertFalse(self.admit().dispatch_allowed)
        with closing(sqlite3.connect(self.path)) as db:
            after = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
            permission = db.execute("SELECT * FROM merchant_signer_permissions").fetchone()
        self.assertEqual(before, after)
        self.assertEqual(permission, (*self.scope.key, 0))
        self.assertEqual(self.approvals.read_admission(self.operation).expires_at, APPROVAL_EXPIRY)


if __name__ == "__main__":
    unittest.main()
