"""Optional local timed-signer admission lookup without inferring authority or mutating state."""

import json
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import (
    MerchantSignerError,
    MerchantSignerScope,
    MerchantSignerStore,
    TimedSignerAdmission,
)
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP,
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

NOW = 1700000000
EXPIRY = NOW + 10
URI = "https://synthetic-shop.example/checkout?cart=one"
TABLES = ("payment_attempts", "payment_admissions", "merchant_timed_admissions")


class TimedSignerAdmissionFindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.operation = PaymentOperation(
            "tenant",
            "operation",
            "approval",
            "stripe:test",
            "acct_synthetic",
            "key",
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
            "sig1",
            scope.key_id,
            MUTATION_COMPONENTS,
            "POST",
            scope.target_uri,
            "application/json",
            digest,
        )
        values = {
            "scope": scope,
            "approvals": self.approvals,
            "journal": self.journal,
            "operation": operation,
            "signature": TimedRequestSignatureSnapshot(snapshot, NOW - 5, EXPIRY),
            "clock": lambda: NOW,
            "method": "POST",
            "target_uri": scope.target_uri,
            "content_type": "application/json",
            "content_digest": digest,
            "content_encoding": None,
            "body": body,
        }
        values.update(changes)
        return values

    def admit(self, **changes):
        return self.signers.admit(**self.inputs(**changes))

    def table_counts(self) -> tuple[int, int, int]:
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in TABLES
            )

    def test_absent_or_non_timed_paths_return_none_without_side_effects(self) -> None:
        self.assertIsNone(self.signers.find_timed_admission(self.operation))
        self.assertEqual(self.table_counts(), (0, 0, 0))
        with self.assertRaisesRegex(MerchantSignerError, "No first timed-admission"):
            self.signers.read_timed_admission(self.operation)

        # Bare RequestSignatureSnapshot admission records attempt + approval admission, not timed admission
        bare_snapshot = self.inputs()["signature"].signature
        self.assertTrue(self.admit(signature=bare_snapshot).dispatch_allowed)
        self.assertIsNone(self.signers.find_timed_admission(self.operation))
        self.assertIsNotNone(self.approvals.find_admission(self.operation))
        self.assertIsNotNone(self.journal.read_attempt(self.operation))
        self.assertEqual(self.table_counts(), (1, 1, 0))

        # Generic approval admission on another operation also has no timed-signer record
        other_op = replace(
            self.operation,
            operation_id="op-approval-only",
            approval_id="approval-only",
            idempotency_key="key-approval-only",
        )
        self.approvals.approve(other_op, expires_at=NOW + 60)
        generic_inputs = self.inputs(operation=other_op)
        generic_inputs.pop("scope")
        generic_inputs.pop("approvals")
        generic_inputs["signature"] = generic_inputs["signature"].signature
        generic_inputs["expected_target_uri"] = URI
        self.assertTrue(self.approvals.admit(**generic_inputs).dispatch_allowed)
        self.assertIsNone(self.signers.find_timed_admission(other_op))
        self.assertIsNotNone(self.approvals.find_admission(other_op))

        # Direct journal reservation has neither approval nor timed-signer record
        legacy_op = replace(
            self.operation,
            operation_id="op-legacy",
            approval_id="approval-legacy",
            idempotency_key="key-legacy",
        )
        self.assertTrue(self.journal.reserve(legacy_op).dispatch_allowed)
        self.assertIsNone(self.signers.find_timed_admission(legacy_op))
        self.assertIsNone(self.approvals.find_admission(legacy_op))
        self.assertIsNotNone(self.journal.read_attempt(legacy_op))

    def test_admitted_timed_operation_returns_history_and_survives_revocation_and_reopen(self) -> None:
        decision = self.admit(clock=lambda: NOW + 1)
        self.assertTrue(decision.dispatch_allowed)
        expected = TimedSignerAdmission(
            self.operation.fingerprint,
            self.scope,
            "sig1",
            NOW - 5,
            EXPIRY,
            NOW + 1,
        )
        self.assertEqual(self.signers.find_timed_admission(self.operation), expected)
        self.assertEqual(self.signers.read_timed_admission(self.operation), expected)
        self.signers.revoke(self.scope)
        self.approvals.revoke(self.operation)
        self.assertEqual(self.signers.find_timed_admission(self.operation), expected)
        self.assertEqual(
            MerchantSignerStore(self.path).find_timed_admission(self.operation),
            expected,
        )
        script = (
            "import json, sys; from dataclasses import asdict; from pathlib import Path; "
            "from lab.checkout import Checkout; from lab.merchant_signers import MerchantSignerStore; "
            "from lab.payment_attempts import PaymentOperation; "
            "data = json.loads(sys.argv[2]); data['checkout'] = Checkout(**data['checkout']); "
            "op = PaymentOperation(**data); "
            "rec = MerchantSignerStore(Path(sys.argv[1])).find_timed_admission(op); "
            "print(f'{rec.signature_label}:{rec.admitted_at}:{rec.expires}')"
        )
        out = subprocess.check_output(
            [sys.executable, "-c", script, str(self.path), json.dumps(asdict(self.operation))],
            text=True,
        )
        self.assertEqual(out.strip(), f"sig1:{NOW + 1}:{EXPIRY}")

    def test_fingerprint_mismatch_raises_error_while_other_scope_returns_none(self) -> None:
        self.admit()
        for field in ("approval_id", "provider", "provider_account", "idempotency_key"):
            drifted = replace(self.operation, **{field: f"other-{field}"})
            with self.subTest(field=field), self.assertRaisesRegex(
                MerchantSignerError, "bound operation"
            ):
                self.signers.find_timed_admission(drifted)
        for checkout_field, value in (
            ("merchant", "other-shop"),
            ("currency", "EUR"),
            ("sku", "other-sku"),
            ("quantity", 3),
            ("amount", 2000),
        ):
            drifted_checkout = replace(self.operation.checkout, **{checkout_field: value})
            drifted = replace(self.operation, checkout=drifted_checkout)
            with self.subTest(checkout_field=checkout_field), self.assertRaisesRegex(
                MerchantSignerError, "bound operation"
            ):
                self.signers.find_timed_admission(drifted)

        self.assertIsNone(
            self.signers.find_timed_admission(
                replace(self.operation, tenant_id="other-tenant")
            )
        )
        self.assertIsNone(
            self.signers.find_timed_admission(
                replace(self.operation, operation_id="other-operation")
            )
        )

    def test_invalid_operation_rejected_before_opening_connection(self) -> None:
        with patch.object(self.signers, "_connect") as connect:
            for invalid in (None, {}, "operation", 123, self.scope, self.operation.checkout):
                with self.subTest(invalid=invalid), self.assertRaises(MerchantSignerError):
                    self.signers.find_timed_admission(invalid)  # type: ignore[arg-type]
            connect.assert_not_called()

    def test_corrupted_stored_times_label_or_scope_raise_error(self) -> None:
        self.admit()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA ignore_check_constraints=ON")
            for name, value in (
                ("created", "bad"),
                ("created", -1),
                ("created", 1.5),
                ("expires", "bad"),
                ("expires", MAX_SIGNATURE_TIMESTAMP + 1),
                ("admitted_at", "bad"),
                ("admitted_at", NOW + 0.5),
                ("admitted_at", EXPIRY),
            ):
                db.execute(f"UPDATE merchant_timed_admissions SET {name}=?", (value,))
                db.commit()
                with self.subTest(name=name, value=value), self.assertRaisesRegex(
                    MerchantSignerError, "times are invalid"
                ):
                    self.signers.find_timed_admission(self.operation)
                db.execute(
                    "UPDATE merchant_timed_admissions SET created=?,expires=?,admitted_at=?",
                    (NOW - 5, EXPIRY, NOW),
                )
                db.commit()

            for label in ("", "Sig1", "sig;created=1", "sig\n", b"sig1"):
                db.execute("UPDATE merchant_timed_admissions SET signature_label=?", (label,))
                db.commit()
                with self.subTest(label=label), self.assertRaisesRegex(
                    MerchantSignerError, "label"
                ):
                    self.signers.find_timed_admission(self.operation)
            db.execute("UPDATE merchant_timed_admissions SET signature_label='sig1'")
            db.commit()

            for scope_col in ("target_uri", "key_id"):
                for bad_val in ("", " padded ", "line\nbreak", "nonascii-\u00e9", b"bytes"):
                    db.execute(f"UPDATE merchant_timed_admissions SET {scope_col}=?", (bad_val,))
                    db.commit()
                    with self.subTest(scope_col=scope_col, bad_val=bad_val), self.assertRaises(
                        MerchantSignerError
                    ):
                        self.signers.find_timed_admission(self.operation)
                    db.execute(
                        "UPDATE merchant_timed_admissions SET target_uri=?,key_id=?",
                        (URI, self.scope.key_id),
                    )
                    db.commit()

    def test_select_only_does_not_take_writer_lock_or_check_live_permission(self) -> None:
        self.admit()
        statements: list[str] = []
        connect = self.signers._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.signers, "_connect", side_effect=traced), \
                patch.object(self.signers, "_permission", side_effect=AssertionError("live permission")), \
                patch("lab.merchant_signers.require_signature_time", side_effect=AssertionError("live time")):
            self.assertEqual(
                self.signers.find_timed_admission(self.operation),
                TimedSignerAdmission(
                    self.operation.fingerprint,
                    self.scope,
                    "sig1",
                    NOW - 5,
                    EXPIRY,
                    NOW,
                ),
            )
            self.assertIsNone(
                self.signers.find_timed_admission(
                    replace(self.operation, operation_id="absent")
                )
            )
        select_stmts = [
            stmt for stmt in statements if "FROM merchant_timed_admissions" in stmt
        ]
        self.assertEqual(len(select_stmts), 2)
        self.assertTrue(all(stmt.startswith("SELECT ") for stmt in select_stmts))
        self.assertFalse(any("BEGIN IMMEDIATE" in stmt for stmt in statements))


if __name__ == "__main__":
    unittest.main()
