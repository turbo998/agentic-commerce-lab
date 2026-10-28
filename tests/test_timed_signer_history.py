"""Synthetic first timed-branch history, non-backfill and atomic failure evidence."""

import json
import sqlite3
import subprocess
import sys
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
from lab.merchant_signers import (
    MerchantSignerError, MerchantSignerScope, MerchantSignerStore, TimedSignerAdmission,
)
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP, MUTATION_COMPONENTS, RequestBindingError,
    RequestSignatureSnapshot, TimedRequestSignatureSnapshot,
)


NOW = 1700000000
EXPIRY = NOW + 10
URI = "https://synthetic-shop.example/checkout"
TABLES = ("payment_attempts", "payment_admissions", "merchant_timed_admissions")


class TimedSignerHistoryTests(unittest.TestCase):
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
        self.approvals.approve(self.operation, expires_at=NOW + 60)
        self.signers.allow(self.scope)

    def inputs(self, **changes):
        operation = changes.get("operation", self.operation)
        scope = changes.get("scope", self.scope)
        body = json.dumps(asdict(operation.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1", scope.key_id, MUTATION_COMPONENTS, "POST", scope.target_uri,
            "application/json", digest,
        )
        values = {
            "scope": self.scope, "approvals": self.approvals, "journal": self.journal,
            "operation": self.operation,
            "signature": TimedRequestSignatureSnapshot(snapshot, NOW - 5, EXPIRY),
            "clock": lambda: NOW, "method": "POST", "target_uri": scope.target_uri,
            "content_type": "application/json", "content_digest": digest,
            "content_encoding": None, "body": body,
        }
        values.update(changes)
        return values

    def admit(self, **changes):
        return self.signers.admit(**self.inputs(**changes))

    def counts(self):
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in TABLES)

    def assert_no_history(self):
        with self.assertRaisesRegex(MerchantSignerError, "No first timed-admission"):
            self.signers.read_timed_admission(self.operation)

    def test_first_timed_dispatch_records_exact_scope_label_window_and_original_sample(self):
        clock = Mock(side_effect=(NOW + 1, EXPIRY))
        decision = self.admit(clock=clock)
        self.assertTrue(decision.dispatch_allowed)
        clock.assert_called_once_with()
        self.assertEqual(self.signers.read_timed_admission(self.operation), TimedSignerAdmission(
            self.operation.fingerprint, self.scope, "sig1", NOW - 5, EXPIRY, NOW + 1,
        ))
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, NOW + 1)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_history_and_nested_scope_are_frozen(self):
        self.admit()
        record = self.signers.read_timed_admission(self.operation)
        with self.assertRaises(FrozenInstanceError):
            record.admitted_at = NOW + 1
        with self.assertRaises(FrozenInstanceError):
            record.scope.key_id = "other"

    def test_epoch_zero_is_not_mistaken_for_a_missing_clock_sample(self):
        timed = replace(self.inputs()["signature"], created=0, expires=1)
        self.assertTrue(self.admit(signature=timed, clock=lambda: 0).dispatch_allowed)
        record = self.signers.read_timed_admission(self.operation)
        self.assertEqual((record.created, record.expires, record.admitted_at), (0, 1, 0))
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, 0)

    def test_upper_structured_field_window_round_trips_as_integers(self):
        operation = replace(
            self.operation, operation_id="max", approval_id="max", idempotency_key="max",
        )
        self.approvals.approve(operation, expires_at=MAX_SIGNATURE_TIMESTAMP + 1)
        timed = replace(
            self.inputs()["signature"], created=MAX_SIGNATURE_TIMESTAMP - 1,
            expires=MAX_SIGNATURE_TIMESTAMP,
        )
        self.assertTrue(self.admit(
            operation=operation, signature=timed, clock=lambda: MAX_SIGNATURE_TIMESTAMP - 1,
        ).dispatch_allowed)
        record = self.signers.read_timed_admission(operation)
        self.assertEqual(
            (record.created, record.expires, record.admitted_at),
            (MAX_SIGNATURE_TIMESTAMP - 1, MAX_SIGNATURE_TIMESTAMP, MAX_SIGNATURE_TIMESTAMP - 1),
        )

    def test_missing_read_neither_infers_approval_history_nor_creates_writes(self):
        self.assert_no_history()
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_reader_requires_trusted_operation_type(self):
        for value in (None, {}, "operation"):
            with self.subTest(value=value), self.assertRaises(MerchantSignerError):
                self.signers.read_timed_admission(value)
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_full_operation_binding_and_tenant_operation_isolation(self):
        self.admit()
        for name in ("approval_id", "provider", "provider_account", "idempotency_key"):
            with self.subTest(name=name), self.assertRaisesRegex(MerchantSignerError, "bound operation"):
                self.signers.read_timed_admission(replace(self.operation, **{name: "other"}))
        for name, value in (
            ("merchant", "other"), ("currency", "EUR"), ("sku", "other"),
            ("quantity", 3), ("amount", 2000),
        ):
            operation = replace(self.operation, checkout=replace(self.operation.checkout, **{name: value}))
            with self.subTest(name=name), self.assertRaisesRegex(MerchantSignerError, "bound operation"):
                self.signers.read_timed_admission(operation)
        for name in ("tenant_id", "operation_id"):
            with self.subTest(name=name), self.assertRaisesRegex(MerchantSignerError, "No first"):
                self.signers.read_timed_admission(replace(self.operation, **{name: "other"}))

    def test_tenants_can_reuse_operation_names_without_sharing_history(self):
        other = replace(self.operation, tenant_id="other", idempotency_key="other")
        scope = replace(self.scope, tenant_id="other")
        self.approvals.approve(other, expires_at=NOW + 60)
        self.signers.allow(scope)
        self.admit()
        self.admit(operation=other, scope=scope, clock=lambda: NOW + 1)
        self.assertEqual(self.signers.read_timed_admission(self.operation).admitted_at, NOW)
        self.assertEqual(self.signers.read_timed_admission(other).scope, scope)
        self.assertEqual(self.signers.read_timed_admission(other).admitted_at, NOW + 1)
        self.assertEqual(self.counts(), (2, 2, 2))

    def test_retry_cannot_replace_first_scope_key_label_window_or_time(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        other = replace(self.scope, target_uri=URI + "?other=1", key_id="other")
        self.signers.allow(other)
        timed = self.inputs(scope=other)["signature"]
        timed = replace(
            timed, signature=replace(timed.signature, signature_label="sig2"),
            created=NOW - 1, expires=EXPIRY + 10,
        )
        retry = self.admit(scope=other, signature=timed, clock=lambda: NOW + 1)
        self.assertFalse(retry.dispatch_allowed)
        self.assertEqual(self.signers.read_timed_admission(self.operation), original)
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_revocation_blocks_admission_but_preserves_read(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        self.signers.revoke(self.scope)
        self.approvals.revoke(self.operation)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()
        self.assertEqual(self.signers.read_timed_admission(self.operation), original)

    def test_signature_and_approval_expiry_cannot_erase_or_refresh_history(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        for now in (EXPIRY, NOW + 60):
            with self.subTest(now=now), self.assertRaises(RequestBindingError):
                self.admit(clock=lambda: now)
        self.assertEqual(self.signers.read_timed_admission(self.operation), original)

    def test_terminal_attempt_does_not_turn_history_into_payment_proof(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        self.journal.reconcile(self.operation, observation="succeeded", provider_reference="sim-payment")
        self.assertFalse(self.admit().dispatch_allowed)
        self.assertEqual(self.signers.read_timed_admission(self.operation), original)

    def test_bare_signer_admission_cannot_be_backfilled_by_timed_retry(self):
        self.admit(signature=self.inputs()["signature"].signature)
        self.assertFalse(self.admit().dispatch_allowed)
        self.assert_no_history()
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_generic_approval_admission_cannot_be_backfilled(self):
        values = self.inputs()
        values.pop("scope")
        values.pop("approvals")
        values["signature"] = values["signature"].signature
        values["expected_target_uri"] = URI
        self.approvals.admit(**values)
        self.assertFalse(self.admit().dispatch_allowed)
        self.assert_no_history()
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_direct_journal_reservation_cannot_be_backfilled(self):
        self.journal.reserve(self.operation)
        self.assertFalse(self.admit().dispatch_allowed)
        self.assert_no_history()
        self.assertEqual(self.counts(), (1, 0, 0))

    def test_terminal_legacy_attempt_cannot_be_backfilled(self):
        self.journal.reserve(self.operation)
        self.journal.reconcile(self.operation, observation="succeeded", provider_reference="sim-payment")
        self.assertFalse(self.admit().dispatch_allowed)
        self.assert_no_history()
        self.assertEqual(self.counts(), (1, 0, 0))

    def test_upgrade_adds_empty_table_never_reconstructs_prior_timed_execution(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DROP TABLE merchant_timed_admissions")
        self.signers = MerchantSignerStore(self.path)
        self.assert_no_history()
        self.assertFalse(self.admit().dispatch_allowed)
        self.assertEqual(self.counts(), (1, 1, 0))

    def test_upgrade_preserves_existing_revoked_policy_without_inventing_history(self):
        self.signers.revoke(self.scope)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DROP TABLE merchant_timed_admissions")
        self.signers = MerchantSignerStore(self.path)
        with self.assertRaisesRegex(MerchantSignerError, "revoked"):
            self.admit()
        self.assert_no_history()
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_history_survives_reopen(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        self.signers = MerchantSignerStore(self.path)
        self.assertEqual(self.signers.read_timed_admission(self.operation), original)
        self.assertFalse(self.admit().dispatch_allowed)

    def test_history_survives_fresh_process_after_revocation(self):
        self.admit()
        original = asdict(self.signers.read_timed_admission(self.operation))
        self.signers.revoke(self.scope)
        script = """
import json, sys
from dataclasses import asdict
from pathlib import Path
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerStore
from lab.payment_attempts import PaymentOperation
data = json.loads(sys.argv[2])
data["checkout"] = Checkout(**data["checkout"])
operation = PaymentOperation(**data)
print(json.dumps(asdict(MerchantSignerStore(Path(sys.argv[1])).read_timed_admission(operation))))
"""
        output = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path), json.dumps(asdict(self.operation))], text=True,
        )
        self.assertEqual(json.loads(output), original)

    def test_invalid_time_clock_body_or_revocation_creates_no_three_records(self):
        for change in (
            {"clock": lambda: EXPIRY}, {"clock": lambda: True}, {"body": b"{}"},
        ):
            with self.subTest(change=change), self.assertRaises(RequestBindingError):
                self.admit(**change)
            self.assertEqual(self.counts(), (0, 0, 0))
        self.signers.revoke(self.scope)
        with self.assertRaises(MerchantSignerError):
            self.admit()
        self.assertEqual(self.counts(), (0, 0, 0))

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
                        self.assertFalse(future.done())
                        before_release()
                    finally:
                        blocker.commit()
                    return future

    def test_actual_lock_wait_uses_one_post_lock_sample_in_both_histories(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def advance():
            current[0] = EXPIRY - 1

        self.assertTrue(self.blocked_admission(advance, clock).result().dispatch_allowed)
        clock.assert_called_once_with()
        self.assertEqual(self.signers.read_timed_admission(self.operation).admitted_at, EXPIRY - 1)
        self.assertEqual(self.approvals.read_admission(self.operation).admitted_at, EXPIRY - 1)

    def test_expiry_during_actual_lock_wait_creates_no_history(self):
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])

        def expire():
            current[0] = EXPIRY

        future = self.blocked_admission(expire, clock)
        self.assertIsInstance(future.exception(), RequestBindingError)
        clock.assert_called_once_with()
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_concurrent_first_admissions_record_only_the_dispatch_winner(self):
        clocks = [Mock(return_value=NOW), Mock(return_value=NOW + 1)]

        def run(index):
            timed = self.inputs()["signature"]
            return self.admit(
                clock=clocks[index],
                signature=replace(timed, signature=replace(timed.signature, signature_label=f"sig{index}")),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(run, range(2)))
        winners = [index for index, decision in enumerate(decisions) if decision.dispatch_allowed]
        self.assertEqual(len(winners), 1)
        record = self.signers.read_timed_admission(self.operation)
        self.assertEqual(record.signature_label, f"sig{winners[0]}")
        self.assertEqual(record.admitted_at, NOW + winners[0])
        self.assertEqual(self.counts(), (1, 1, 1))
        for clock in clocks:
            clock.assert_called_once_with()

    def test_final_insert_trigger_observes_prior_writes_then_rolls_back_all(self):
        observed = []
        db = self.signers._connect()
        db.create_function("observe_writes", 2, lambda attempts, approvals: observed.append(
            (attempts, approvals),
        ) or 1)
        with db:
            db.execute("""
                CREATE TRIGGER reject_timed BEFORE INSERT ON merchant_timed_admissions
                BEGIN
                    SELECT observe_writes((SELECT count(*) FROM payment_attempts),
                                          (SELECT count(*) FROM payment_admissions));
                    SELECT RAISE(ABORT, 'synthetic timed-history failure');
                END
            """)
        with patch.object(self.signers, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "timed-history failure"):
                self.admit()
        self.assertEqual(observed, [(1, 1)])
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_error_after_real_third_write_rolls_back_all_three(self):
        observed = []

        class FailingWrite(sqlite3.Connection):
            def execute(connection, sql, parameters=()):
                result = super().execute(sql, parameters)
                if sql.startswith("INSERT INTO merchant_timed_admissions"):
                    observed.append(tuple(connection.execute(
                        f"SELECT count(*) FROM {table}"
                    ).fetchone()[0] for table in TABLES))
                    raise RuntimeError("synthetic post-history failure")
                return result

        db = sqlite3.connect(self.path, factory=FailingWrite)
        db.row_factory = sqlite3.Row
        with patch.object(self.signers, "_connect", return_value=db):
            with self.assertRaisesRegex(RuntimeError, "post-history failure"):
                self.admit()
        self.assertEqual(observed, [(1, 1, 1)])
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_commit_failure_observes_three_writes_and_rolls_back_all(self):
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(tuple(connection.execute(
                        f"SELECT count(*) FROM {table}"
                    ).fetchone()[0] for table in TABLES))
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic timed commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        db.row_factory = sqlite3.Row
        with patch.object(self.signers, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "timed commit failure"):
                self.admit()
        self.assertEqual(observed, [(1, 1, 1)])
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_clock_sampling_invariant_failure_never_commits_partial_attempt(self):
        def skip_clock(db, journal, operation, *, clock):
            return journal._reserve_in_transaction(db, operation)

        with patch.object(self.approvals, "_admit_in_transaction", side_effect=skip_clock):
            with self.assertRaisesRegex(MerchantSignerError, "did not sample"):
                self.admit()
        self.assertEqual(self.counts(), (0, 0, 0))

    def test_corrupt_stored_times_are_explicit_errors_not_fresh_clock_checks(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA ignore_check_constraints=ON")
            for name, value in (
                ("created", "bad"), ("created", -1), ("created", 1.5),
                ("expires", "bad"), ("expires", MAX_SIGNATURE_TIMESTAMP + 1),
                ("admitted_at", "bad"), ("admitted_at", NOW + 0.5), ("admitted_at", EXPIRY),
            ):
                db.execute(f"UPDATE merchant_timed_admissions SET {name}=?", (value,))
                db.commit()
                with self.subTest(name=name, value=value), self.assertRaisesRegex(
                    MerchantSignerError, "times are invalid",
                ):
                    self.signers.read_timed_admission(self.operation)
                db.execute(
                    "UPDATE merchant_timed_admissions SET created=?,expires=?,admitted_at=?",
                    (NOW - 5, EXPIRY, NOW),
                )
                db.commit()

    def test_corrupt_stored_scope_is_rejected(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db, db:
            for name in ("target_uri", "key_id"):
                for value in ("", " padded ", "line\nbreak", "nonascii-\u00e9", b"bytes"):
                    db.execute(f"UPDATE merchant_timed_admissions SET {name}=?", (value,))
                    db.commit()
                    with self.subTest(name=name, value=value), self.assertRaises(MerchantSignerError):
                        self.signers.read_timed_admission(self.operation)
                    db.execute(
                        "UPDATE merchant_timed_admissions SET target_uri=?,key_id=?",
                        (URI, self.scope.key_id),
                    )
                    db.commit()

    def test_corrupt_stored_label_is_rejected(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db, db:
            for value in ("", "Sig1", "sig;created=1", "sig\n", b"sig1"):
                db.execute("UPDATE merchant_timed_admissions SET signature_label=?", (value,))
                db.commit()
                with self.subTest(value=value), self.assertRaisesRegex(MerchantSignerError, "label"):
                    self.signers.read_timed_admission(self.operation)
            db.execute("UPDATE merchant_timed_admissions SET signature_label='sig1'")

    def test_read_only_queries_history_without_current_time_or_permission_checks(self):
        self.admit()
        original = self.signers.read_timed_admission(self.operation)
        queries = []
        connect = self.signers._connect

        def traced_connect():
            db = connect()
            db.set_trace_callback(queries.append)
            return db

        with patch.object(self.signers, "_connect", side_effect=traced_connect), \
                patch.object(self.signers, "_permission", side_effect=AssertionError("current policy")), \
                patch("lab.merchant_signers.require_signature_time", side_effect=AssertionError("fresh time")):
            self.assertEqual(self.signers.read_timed_admission(self.operation), original)
        self.assertEqual(len(queries), 1)
        self.assertTrue(queries[0].startswith("SELECT * FROM merchant_timed_admissions"))
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_minimal_storage_has_no_raw_signature_body_or_secret_material(self):
        self.admit()
        with closing(sqlite3.connect(self.path)) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(merchant_timed_admissions)")}
        self.assertEqual(columns, {
            "tenant_id", "operation_id", "fingerprint", "target_uri", "key_id",
            "signature_label", "created", "expires", "admitted_at",
        })


if __name__ == "__main__":
    unittest.main()
