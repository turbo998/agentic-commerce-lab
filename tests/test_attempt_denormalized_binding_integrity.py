"""Denormalized payment_attempts column parity and read-model dataclass invariants."""

import json
import sqlite3
import unittest
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import (
    MerchantSignerError,
    MerchantSignerScope,
    MerchantSignerStore,
    TimedSignerAdmission,
)
from lab.payment_approvals import (
    ApprovalAdmission,
    PaymentApprovalError,
    PaymentApprovalStatus,
    PaymentApprovalStore,
)
from lab.payment_attempts import (
    AttemptConflict,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP,
    MUTATION_COMPONENTS,
    RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope
from lab.stripe_observation import associate_stripe_intent, reconcile_stripe_intent
from lab.stripe_readback import accept_stripe_readback
from tests.test_stripe_inbox import SECRET, event_body, header

NOW = 1700000000
EXPIRY = NOW + 10
APPROVAL_EXPIRY = NOW + 60
URI = "https://synthetic-shop.example/checkout?cart=one"
DENORMALIZED_COLUMNS = ("approval_id", "provider", "provider_account", "idempotency_key")


class AttemptDenormalizedBindingIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.approvals = PaymentApprovalStore(self.path)
        self.signers = MerchantSignerStore(self.path)
        self.inbox = StripeEventInbox(self.path)
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
        self.approvals.approve(self.operation, expires_at=APPROVAL_EXPIRY)
        self.signers.allow(self.scope)

    def timed_inputs(self):
        body = json.dumps(asdict(self.operation.checkout)).encode()
        digest = compute_rfc9530_content_digest(body)
        snapshot = RequestSignatureSnapshot(
            "sig1",
            self.scope.key_id,
            MUTATION_COMPONENTS,
            "POST",
            self.scope.target_uri,
            "application/json",
            digest,
        )
        return {
            "scope": self.scope,
            "approvals": self.approvals,
            "journal": self.journal,
            "operation": self.operation,
            "signature": TimedRequestSignatureSnapshot(snapshot, NOW - 5, EXPIRY),
            "clock": lambda: NOW,
            "method": "POST",
            "target_uri": self.scope.target_uri,
            "content_type": "application/json",
            "content_digest": digest,
            "content_encoding": None,
            "body": body,
        }

    def test_approval_and_timed_admission_dataclasses_enforce_post_init_invariants(self) -> None:
        fp = self.operation.fingerprint
        for bad_fp, bad_exp, bad_state in (
            ("not-hex", APPROVAL_EXPIRY, "active"),
            ("A" * 64, APPROVAL_EXPIRY, "active"),
            (fp, 0, "active"),
            (fp, -1, "active"),
            (fp, True, "active"),
            (fp, 2**63, "active"),
            (fp, APPROVAL_EXPIRY, "pending"),
            (fp, APPROVAL_EXPIRY, 0),
        ):
            with self.subTest(
                cls="PaymentApprovalStatus", fp=bad_fp, exp=bad_exp, state=bad_state
            ), self.assertRaises(PaymentApprovalError):
                PaymentApprovalStatus(bad_fp, bad_exp, bad_state)  # type: ignore[arg-type]

        for bad_fp, bad_adm, bad_exp in (
            ("not-hex", NOW, APPROVAL_EXPIRY),
            ("A" * 64, NOW, APPROVAL_EXPIRY),
            (fp, -1, APPROVAL_EXPIRY),
            (fp, APPROVAL_EXPIRY, APPROVAL_EXPIRY),
            (fp, APPROVAL_EXPIRY + 1, APPROVAL_EXPIRY),
            (fp, False, APPROVAL_EXPIRY),
            (fp, NOW, True),
            (fp, NOW, 2**63),
        ):
            with self.subTest(
                cls="ApprovalAdmission", fp=bad_fp, adm=bad_adm, exp=bad_exp
            ), self.assertRaises(PaymentApprovalError):
                ApprovalAdmission(bad_fp, bad_adm, bad_exp)  # type: ignore[arg-type]

        for bad_fp, bad_scope, bad_label, bad_created, bad_expires, bad_adm in (
            ("not-hex", self.scope, "sig1", NOW - 5, EXPIRY, NOW),
            (fp, "bad-scope", "sig1", NOW - 5, EXPIRY, NOW),
            (fp, self.scope, "BadLabel", NOW - 5, EXPIRY, NOW),
            (fp, self.scope, "", NOW - 5, EXPIRY, NOW),
            (fp, self.scope, "sig1", -1, EXPIRY, NOW),
            (fp, self.scope, "sig1", NOW + 1, EXPIRY, NOW),
            (fp, self.scope, "sig1", NOW - 5, NOW, NOW),
            (fp, self.scope, "sig1", NOW - 5, MAX_SIGNATURE_TIMESTAMP + 1, NOW),
            (fp, self.scope, "sig1", False, EXPIRY, NOW),
            (fp, self.scope, "sig1", NOW - 5, EXPIRY, True),
        ):
            with self.subTest(
                cls="TimedSignerAdmission",
                fp=bad_fp,
                scope=bad_scope,
                label=bad_label,
                created=bad_created,
                expires=bad_expires,
                adm=bad_adm,
            ), self.assertRaises(MerchantSignerError):
                TimedSignerAdmission(
                    bad_fp, bad_scope, bad_label, bad_created, bad_expires, bad_adm  # type: ignore[arg-type]
                )

    def test_corrupted_denormalized_attempt_columns_fail_closed_across_journal_methods(
        self,
    ) -> None:
        self.assertTrue(self.journal.reserve(self.operation).dispatch_allowed)
        for column in DENORMALIZED_COLUMNS:
            original = getattr(self.operation, column)
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ? WHERE tenant_id = ? AND operation_id = ?",
                        (f"{original}-corrupted", self.operation.tenant_id, self.operation.operation_id),
                    )
                for action in (
                    lambda: self.journal.read(self.operation),
                    lambda: self.journal.read_attempt(self.operation),
                    lambda: self.journal.reserve(self.operation),
                    lambda: self.journal.reconcile(
                        self.operation,
                        observation="succeeded",
                        provider_reference="pi_synthetic_001",
                    ),
                ):
                    with self.assertRaisesRegex(AttemptConflict, "Operation binding changed"):
                        action()
                with closing(sqlite3.connect(self.path)) as db, db:
                    row = db.execute(
                        "SELECT outcome, provider_reference FROM payment_attempts"
                    ).fetchone()
                    self.assertEqual(row, ("unknown", None))
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ? WHERE tenant_id = ? AND operation_id = ?",
                        (original, self.operation.tenant_id, self.operation.operation_id),
                    )
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_corrupted_denormalized_attempt_columns_fail_closed_across_admission_and_provenance(
        self,
    ) -> None:
        self.assertTrue(self.signers.admit(**self.timed_inputs()).dispatch_allowed)
        for column in DENORMALIZED_COLUMNS:
            original = getattr(self.operation, column)
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ?",
                        (f"{original}-corrupted",),
                    )
                with self.assertRaisesRegex(
                    MerchantSignerError, "Attempt record differs from the bound operation"
                ):
                    self.signers.find_provenance(
                        self.approvals, self.journal, self.operation
                    )
                with self.assertRaisesRegex(
                    MerchantSignerError, "Attempt record differs from the bound operation"
                ):
                    self.signers.read_provenance(
                        self.approvals, self.journal, self.operation
                    )
                with self.assertRaisesRegex(AttemptConflict, "Operation binding changed"):
                    self.signers.admit(**self.timed_inputs())
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ?",
                        (original,),
                    )
        self.assertEqual(
            self.signers.read_provenance(self.approvals, self.journal, self.operation).path,
            "timed_signer_admission",
        )

    def test_corrupted_denormalized_attempt_columns_block_stripe_association_and_readback(
        self,
    ) -> None:
        self.assertTrue(self.journal.reserve(self.operation).dispatch_allowed)
        inbox_scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
        body = event_body()
        self.inbox.record(inbox_scope, body, header(body), SECRET, now=NOW)
        claim = self.inbox.claim_next(inbox_scope, "worker-a")
        assert claim is not None
        intent = {
            "object": "payment_intent",
            "id": "pi_synthetic",
            "livemode": False,
            "amount": 1000,
            "amount_received": 1000,
            "currency": "usd",
            "status": "succeeded",
            "transfer_data": None,
            "on_behalf_of": None,
        }

        for column in DENORMALIZED_COLUMNS:
            original = getattr(self.operation, column)
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ?",
                        (f"{original}-corrupted",),
                    )
                with self.assertRaisesRegex(AttemptConflict, "Operation binding changed"):
                    associate_stripe_intent(
                        self.journal,
                        self.operation,
                        retrieved_account="acct_synthetic",
                        expected_reference="pi_synthetic",
                        intent=intent,
                    )
                with self.assertRaisesRegex(AttemptConflict, "Operation binding changed"):
                    reconcile_stripe_intent(
                        self.journal,
                        self.operation,
                        retrieved_account="acct_synthetic",
                        intent=intent,
                    )
                with self.assertRaisesRegex(AttemptConflict, "Operation binding changed"):
                    accept_stripe_readback(
                        self.inbox,
                        self.journal,
                        claim,
                        self.operation,
                        retrieved_account="acct_synthetic",
                        intent=intent,
                    )
                status = self.inbox.read_claim(inbox_scope, "evt_synthetic")
                assert status is not None
                self.assertEqual(status.state, "active")
                with closing(sqlite3.connect(self.path)) as db, db:
                    db.execute(
                        f"UPDATE payment_attempts SET {column} = ?",
                        (original,),
                    )


if __name__ == "__main__":
    unittest.main()
