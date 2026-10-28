"""Synthetic local signer ordering, shared approval state and bounded authority."""

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
from threading import Event
from unittest.mock import Mock, patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.checkout_admission import CheckoutAdmissionError
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot


NOW = 1700000000
EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"


class MerchantSignerTests(unittest.TestCase):
    def setUp(self) -> None:
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
        self.approvals.approve(self.operation, expires_at=EXPIRY)
        self.signers.allow(self.scope)

    def inputs(self, **changes):
        operation = changes.get("operation", self.operation)
        scope = changes.get("scope", self.scope)
        checkout = operation.checkout if isinstance(operation, PaymentOperation) else self.operation.checkout
        route = scope.target_uri if isinstance(scope, MerchantSignerScope) else URI
        key_id = scope.key_id if isinstance(scope, MerchantSignerScope) else self.scope.key_id
        body = json.dumps(asdict(checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        values = {
            "scope": self.scope, "approvals": self.approvals, "journal": self.journal,
            "operation": self.operation,
            "signature": RequestSignatureSnapshot(
                "sig1", key_id, MUTATION_COMPONENTS, "POST", route, "application/json", digest,
            ),
            "clock": lambda: NOW, "method": "POST", "target_uri": route,
            "content_type": "application/json", "content_digest": digest,
            "content_encoding": None, "body": body,
        }
        values.update(changes)
        return values

    def admit(self, **changes):
        return self.signers.admit(**self.inputs(**changes))

    def assert_unreserved(self) -> None:
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)

    def test_valid_permission_composes_approval_history_and_one_dispatch(self):
        first, retry = self.admit(), self.admit()
        self.assertTrue(first.dispatch_allowed)
        self.assertFalse(retry.dispatch_allowed)
        self.assertEqual(first.attempt, retry.attempt)
        self.assertEqual(first.attempt.outcome, "unknown")
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW)

    def test_scope_requires_canonical_text_and_ascii_route_key(self):
        for field in ("tenant_id", "merchant", "target_uri", "key_id"):
            for value in ("", " ", " padded ", None, 123):
                with self.subTest(field=field, value=value), self.assertRaises(MerchantSignerError):
                    replace(self.scope, **{field: value})
        for field in ("target_uri", "key_id"):
            for value in ("nonascii-\u00e9", "line\nbreak", "delete\x7f"):
                with self.subTest(field=field, value=value), self.assertRaises(MerchantSignerError):
                    replace(self.scope, **{field: value})

    def test_operator_and_admission_inputs_require_trusted_types(self):
        for value in (None, {}, "scope"):
            with self.subTest(value=value), self.assertRaises(MerchantSignerError):
                self.signers.allow(value)
            with self.subTest(value=value), self.assertRaises(MerchantSignerError):
                self.signers.revoke(value)
        for field in ("scope", "approvals", "journal", "operation", "signature", "clock"):
            with self.subTest(field=field), self.assertRaises(MerchantSignerError):
                self.admit(**{field: None})
        self.assert_unreserved()

    def test_allow_binding_cannot_be_replaced_or_reactivated(self):
        with self.assertRaisesRegex(MerchantSignerError, "replacement"):
            self.signers.allow(self.scope)
        self.signers.revoke(self.scope)
        with self.assertRaisesRegex(MerchantSignerError, "replacement"):
            self.signers.allow(self.scope)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()
        self.assert_unreserved()

    def test_missing_permission_cannot_be_supplied_by_a_valid_snapshot(self):
        with self.assertRaisesRegex(MerchantSignerError, "No recorded"):
            self.admit(scope=replace(self.scope, key_id="unregistered-key"))
        self.assert_unreserved()

    def test_revoke_missing_scope_is_explicit_and_does_not_create_permission(self):
        scope = replace(self.scope, key_id="missing")
        with self.assertRaisesRegex(MerchantSignerError, "No recorded"):
            self.signers.revoke(scope)
        with self.assertRaisesRegex(MerchantSignerError, "No recorded"):
            self.admit(scope=scope)

    def test_revocation_is_idempotent_and_survives_reopen(self):
        self.signers.revoke(self.scope)
        self.signers = MerchantSignerStore(self.path)
        self.signers.revoke(self.scope)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()
        self.assert_unreserved()

    def test_permission_isolated_by_tenant_merchant_route_and_key(self):
        cases = (
            (replace(self.scope, tenant_id="other"), replace(self.operation, tenant_id="other")),
            (replace(self.scope, merchant="other"),
             replace(self.operation, checkout=replace(self.operation.checkout, merchant="other"))),
            (replace(self.scope, target_uri=URI + "&other=1"), self.operation),
            (replace(self.scope, key_id="other"), self.operation),
        )
        for scope, operation in cases:
            with self.subTest(scope=scope), self.assertRaisesRegex(MerchantSignerError, "No recorded"):
                self.admit(scope=scope, operation=operation)
        self.assert_unreserved()

    def test_scope_must_match_trusted_operation_and_verified_key(self):
        for scope in (
            replace(self.scope, tenant_id="other"), replace(self.scope, merchant="other"),
        ):
            with self.subTest(scope=scope), self.assertRaisesRegex(MerchantSignerError, "differs"):
                self.admit(scope=scope)
        signature = replace(self.inputs()["signature"], key_id="other")
        with self.assertRaisesRegex(MerchantSignerError, "differs"):
            self.admit(signature=signature)
        self.assert_unreserved()

    def test_revoking_one_scope_does_not_revoke_another_key(self):
        other = replace(self.scope, key_id="other")
        self.signers.allow(other)
        self.signers.revoke(self.scope)
        self.assertTrue(self.admit(scope=other).dispatch_allowed)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()

    def test_local_allow_cannot_supply_missing_or_revoked_approval(self):
        with self.assertRaisesRegex(PaymentApprovalError, "No recorded"):
            self.admit(operation=replace(self.operation, approval_id="missing"))
        self.approvals.revoke(self.operation)
        with self.assertRaisesRegex(PaymentApprovalError, "revoked"):
            self.admit()
        self.assert_unreserved()

    def test_expired_or_invalid_clock_approval_never_reserves(self):
        for value in (EXPIRY, EXPIRY + 1, True, None, 1.5, -1, 2**63):
            with self.subTest(value=value), self.assertRaises(PaymentApprovalError):
                self.admit(clock=lambda: value)
        self.assert_unreserved()

    def test_revoked_permission_never_calls_clock_or_reservation(self):
        self.signers.revoke(self.scope)
        clock = Mock(return_value=NOW)
        with patch.object(self.journal, "_reserve_in_transaction") as reserve:
            with self.assertRaises(MerchantSignerError):
                self.admit(clock=clock)
            reserve.assert_not_called()
        clock.assert_not_called()
        self.assert_unreserved()

    def test_signature_body_quote_and_route_checks_remain_before_storage(self):
        signature = self.inputs()["signature"]
        changes = (
            {"body": self.inputs()["body"] + b"\n"},
            {"signature": replace(signature, covered_components=("@method",))},
            {"target_uri": URI + "&changed=1"},
            {"operation": replace(self.operation, checkout=replace(self.operation.checkout, amount=999)),
             "signature": signature},
        )
        for change in changes:
            with self.subTest(change=change), patch.object(self.signers, "_connect") as connect:
                with self.assertRaises((RequestBindingError, CheckoutAdmissionError)):
                    self.admit(**change)
                connect.assert_not_called()
        self.assert_unreserved()

    def test_all_three_stores_must_share_one_resolved_file(self):
        other_approvals = PaymentApprovalStore(self.path.parent / "other-approval.sqlite3")
        other_journal = PaymentAttemptJournal(self.path.parent / "other-attempt.sqlite3")
        for change in ({"approvals": other_approvals}, {"journal": other_journal}):
            with self.subTest(change=change), self.assertRaisesRegex(MerchantSignerError, "same resolved"):
                self.admit(**change)
        self.assert_unreserved()

    def test_resolved_path_spelling_uses_same_transaction(self):
        nested = self.path.parent / "nested"
        nested.mkdir()
        self.signers = MerchantSignerStore(nested / ".." / self.path.name)
        self.assertTrue(self.admit().dispatch_allowed)

    def test_no_nested_public_approval_or_reservation_transaction(self):
        with patch.object(self.approvals, "admit", side_effect=AssertionError("nested approval")), \
                patch.object(self.journal, "reserve", side_effect=AssertionError("nested reserve")):
            self.assertTrue(self.admit().dispatch_allowed)

    def test_private_approval_participant_rejects_autocommit(self):
        with closing(self.approvals._connect()) as db:
            with self.assertRaisesRegex(PaymentApprovalError, "active transaction"):
                self.approvals._admit_in_transaction(
                    db, self.journal, self.operation, clock=lambda: NOW,
                )
        self.assert_unreserved()

    def blocked_admission(self, before_release, clock):
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
                    future = pool.submit(self.admit, clock=clock)
                    try:
                        self.assertTrue(attempted.wait(5), "Actual BEGIN was not attempted.")
                        clock.assert_not_called()
                        before_release(blocker)
                    finally:
                        blocker.commit()
                    return future.exception(timeout=10)

    def test_committed_revoke_while_admission_waits_blocks_reservation(self):
        def revoke(db):
            db.execute(
                "UPDATE merchant_signer_permissions SET revoked=1"
                " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?", self.scope.key,
            )

        clock = Mock(return_value=NOW)
        error = self.blocked_admission(revoke, clock)
        self.assertIsInstance(error, MerchantSignerError)
        self.assertIn("revoked", str(error))
        clock.assert_not_called()
        self.assert_unreserved()

    def test_approval_clock_is_still_sampled_after_actual_lock_wait(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire(db):
            current[0] = EXPIRY

        error = self.blocked_admission(expire, clock)
        self.assertIsInstance(error, PaymentApprovalError)
        self.assertIn("expired", str(error))
        clock.assert_called_once_with()
        self.assert_unreserved()

    def test_reservation_before_revoke_is_not_undone_and_retry_is_denied(self):
        self.assertTrue(self.admit().dispatch_allowed)
        history = self.approvals.read_admission(self.operation)
        self.signers.revoke(self.scope)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")
        self.assertEqual(self.approvals.read_admission(self.operation), history)
        self.assertFalse(self.journal.reserve(self.operation).dispatch_allowed)

    def test_concurrent_admissions_grant_only_one_dispatch(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.admit(), range(2)))
        self.assertEqual(sum(result.dispatch_allowed for result in results), 1)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW)

    def test_exception_after_real_reservation_and_history_rolls_back_both(self):
        original = self.approvals._admit_in_transaction
        observed = []

        def fail(db, journal, operation, *, clock):
            original(db, journal, operation, clock=clock)
            observed.append(tuple(db.execute(
                "SELECT (SELECT count(*) FROM payment_attempts),"
                " (SELECT count(*) FROM payment_admissions)",
            ).fetchone()))
            raise RuntimeError("synthetic post-admission failure")

        with patch.object(self.approvals, "_admit_in_transaction", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "post-admission"):
                self.admit()
        self.assertEqual(observed, [(1, 1)])
        self.assert_unreserved()
        self.assertTrue(self.admit().dispatch_allowed)

    def test_failed_commit_observes_then_rolls_back_reservation_and_history(self):
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

    def test_allow_and_revoke_commit_failures_do_not_publish_policy_changes(self):
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(tuple(tuple(row) for row in connection.execute(
                        "SELECT key_id,revoked FROM merchant_signer_permissions ORDER BY key_id",
                    )))
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic policy commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        other = replace(self.scope, key_id="other")
        for action in (lambda: self.signers.allow(other), lambda: self.signers.revoke(self.scope)):
            db = sqlite3.connect(self.path, factory=FailingCommit)
            db.row_factory = sqlite3.Row
            with patch.object(self.signers, "_connect", return_value=db):
                with self.assertRaisesRegex(sqlite3.OperationalError, "policy commit"):
                    action()
        self.assertEqual(observed, [
            (("other", 0), ("synthetic-key", 0)), (("synthetic-key", 1),),
        ])
        with self.assertRaisesRegex(MerchantSignerError, "No recorded"):
            self.admit(scope=other)
        self.assertTrue(self.admit().dispatch_allowed)

    def test_legacy_reservation_or_admission_is_not_signer_provenance(self):
        self.journal.reserve(self.operation)
        self.assertFalse(self.admit().dispatch_allowed)
        with self.assertRaisesRegex(PaymentApprovalError, "No first-admission"):
            self.approvals.read_admission(self.operation)
        self.signers.revoke(self.scope)
        values = self.inputs()
        for key in ("scope", "approvals"):
            values.pop(key)
        values["expected_target_uri"] = URI
        self.assertFalse(self.approvals.admit(**values).dispatch_allowed)

    def test_revoke_persists_to_a_fresh_process(self):
        self.signers.revoke(self.scope)
        script = """
import sys, json
from pathlib import Path
from dataclasses import asdict
from lab.checkout import Checkout
from lab.payment_attempts import PaymentOperation, PaymentAttemptJournal
from lab.payment_approvals import PaymentApprovalStore
from lab.merchant_signers import MerchantSignerStore, MerchantSignerScope, MerchantSignerError
from lab.request_binding import RequestSignatureSnapshot, MUTATION_COMPONENTS
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
p = Path(sys.argv[1])
uri = 'https://synthetic-shop.example/checkout?cart=one'
op = PaymentOperation('tenant','operation','approval','stripe:test','acct_synthetic','key',
    Checkout('synthetic-shop','USD','synthetic-sku',2,1000))
body = json.dumps(asdict(op.checkout)).encode()
digest = compute_rfc9530_content_digest(body)
scope = MerchantSignerScope('tenant','synthetic-shop',uri,'synthetic-key')
snapshot = RequestSignatureSnapshot('sig1','synthetic-key',MUTATION_COMPONENTS,
    'POST',uri,'application/json',digest)
try:
    MerchantSignerStore(p).admit(scope,PaymentApprovalStore(p),PaymentAttemptJournal(p),op,
        snapshot,clock=lambda:1700000000,method='POST',target_uri=uri,
        content_type='application/json',content_digest=digest,content_encoding=None,body=body)
except MerchantSignerError as error:
    assert 'revoked' in str(error)
    print('revoked')
else:
    raise AssertionError('Revocation lost across process.')
"""
        output = subprocess.check_output([sys.executable, "-c", script, str(self.path)], text=True)
        self.assertEqual(output.strip(), "revoked")
        self.assert_unreserved()

    def test_permission_table_contains_no_keys_signature_or_body_material(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(merchant_signer_permissions)")}
            row = db.execute("SELECT * FROM merchant_signer_permissions").fetchone()
        self.assertEqual(columns, {"tenant_id", "merchant", "target_uri", "key_id", "revoked"})
        self.assertEqual(row, (*self.scope.key, 0))


if __name__ == "__main__":
    unittest.main()
