"""Coupled mandate-and-receipt provenance inspection and stored-row integrity tests."""

import sqlite3
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.checkout import (
    AuthorizationError,
    Checkout,
    CheckoutProvenance,
    CheckoutStore,
    MandateStatus,
    Receipt,
    _execution_fingerprint,
)


class CheckoutProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "checkout.sqlite3"
        self.store = CheckoutStore(self.path)
        self.quote = Checkout("synthetic-shop", "USD", "sku-demo", 1, 1000)
        self.fingerprint = _execution_fingerprint("approval", self.quote)

    def test_lifecycle_provenance_and_lock_free_single_query_snapshot(self) -> None:
        # 1. Absent before approval
        self.assertIsNone(self.store.read_mandate("approval", self.quote))
        self.assertIsNone(
            self.store.read_receipt("approval", self.quote, request_key="request")
        )
        self.assertIsNone(self.store.find_provenance("approval", self.quote))
        self.assertIsNone(
            self.store.find_provenance("approval", self.quote, request_key="request")
        )
        with self.assertRaisesRegex(AuthorizationError, "No trusted approval"):
            self.store.read_provenance("approval", self.quote)

        # 2. Approved active mandate before execution
        self.store.approve("approval", self.quote, max_amount=1200, expires_at=200)
        expected_mandate = MandateStatus(
            mandate_id="approval",
            merchant="synthetic-shop",
            currency="USD",
            cart_digest=self.quote.digest,
            max_amount=1200,
            expires_at=200,
            state="active",
        )
        self.assertEqual(self.store.read_mandate("approval", self.quote), expected_mandate)
        self.assertIsNone(
            self.store.read_receipt("approval", self.quote, request_key="request")
        )
        unspent = self.store.read_provenance("approval", self.quote, request_key="request")
        self.assertEqual(
            unspent,
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=expected_mandate,
                request_key=None,
                receipt=None,
            ),
        )

        # 3. Single-statement read-only SQLite snapshot check
        statements: list[str] = []
        original_connect = self.store._connect

        def traced_connect() -> sqlite3.Connection:
            db = original_connect()
            db.set_trace_callback(statements.append)
            return db

        self.store._connect = traced_connect  # type: ignore[method-assign]
        try:
            statements.clear()
            snap = self.store.read_provenance("approval", self.quote, request_key="request")
            self.assertEqual(snap, unspent)
            selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
            self.assertEqual(len(selects), 1)
            self.assertFalse(any("BEGIN IMMEDIATE" in s.upper() for s in statements))
        finally:
            self.store._connect = original_connect  # type: ignore[method-assign]

        # 4. Executed mandate + receipt provenance
        receipt = self.store.execute("approval", self.quote, request_key="request", now=100)
        self.assertEqual(
            self.store.read_receipt("approval", self.quote, request_key="request"),
            receipt,
        )
        spent = self.store.read_provenance("approval", self.quote)
        self.assertEqual(
            spent,
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=expected_mandate,
                request_key="request",
                receipt=receipt,
            ),
        )
        self.assertEqual(
            self.store.read_provenance("approval", self.quote, request_key="request"),
            spent,
        )

        # 5. Revocation after execution preserves completed receipt and updates state
        self.store.revoke("approval")
        revoked_mandate = replace(expected_mandate, state="revoked")
        self.assertEqual(self.store.read_mandate("approval", self.quote), revoked_mandate)
        self.assertEqual(
            self.store.read_receipt("approval", self.quote, request_key="request"),
            receipt,
        )
        self.assertEqual(
            self.store.read_provenance("approval", self.quote, request_key="request"),
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=revoked_mandate,
                request_key="request",
                receipt=receipt,
            ),
        )

    def test_binding_mismatch_and_key_conflicts_fail_closed(self) -> None:
        self.store.approve("approval", self.quote, max_amount=1000, expires_at=200)
        self.store.execute("approval", self.quote, request_key="request", now=100)

        # Different request_key on already-consumed mandate fails closed
        with self.assertRaisesRegex(AuthorizationError, "already consumed"):
            self.store.find_provenance("approval", self.quote, request_key="other-key")
        self.assertIsNone(
            self.store.read_receipt("approval", self.quote, request_key="other-key")
        )

        # Reused request_key with a different mandate or cart fails closed
        other_quote = replace(self.quote, sku="other-sku")
        self.store.approve("other-approval", other_quote, max_amount=1000, expires_at=200)
        for reader in (
            lambda: self.store.read_receipt(
                "other-approval", other_quote, request_key="request"
            ),
            lambda: self.store.find_provenance(
                "other-approval", other_quote, request_key="request"
            ),
        ):
            with self.assertRaisesRegex(AuthorizationError, "conflicts"):
                reader()

        # Cart / merchant / currency / budget drift on read_mandate and find_provenance
        for bad_quote, pattern in (
            (replace(self.quote, merchant="other-shop"), "Merchant or currency"),
            (replace(self.quote, currency="EUR"), "Merchant or currency"),
            (replace(self.quote, amount=1001), "spending limit"),
            (replace(self.quote, sku="other-sku"), "Cart changed"),
        ):
            with self.subTest(bad_quote=bad_quote):
                with self.assertRaisesRegex(AuthorizationError, pattern):
                    self.store.read_mandate("approval", bad_quote)
                with self.assertRaisesRegex(AuthorizationError, pattern):
                    self.store.find_provenance("approval", bad_quote)

    def test_input_and_dataclass_invariants_fail_closed(self) -> None:
        for bad_id in ("", None, 123):
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ValueError):
                    self.store.approve(bad_id, self.quote, max_amount=1000, expires_at=200)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.revoke(bad_id)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.read_mandate(bad_id, self.quote)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.find_provenance(bad_id, self.quote)  # type: ignore[arg-type]
        for bad_checkout in (None, "quote", 123):
            with self.subTest(bad_checkout=bad_checkout):
                with self.assertRaises(ValueError):
                    self.store.approve("m", bad_checkout, max_amount=1000, expires_at=200)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.read_mandate("m", bad_checkout)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.execute("m", bad_checkout, request_key="k", now=100)  # type: ignore[arg-type]
        for bad_key in ("", 123):
            with self.subTest(bad_key=bad_key):
                with self.assertRaises(ValueError):
                    self.store.read_receipt("approval", self.quote, request_key=bad_key)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    self.store.find_provenance("approval", self.quote, request_key=bad_key)  # type: ignore[arg-type]

        valid_status = MandateStatus(
            mandate_id="approval",
            merchant="synthetic-shop",
            currency="USD",
            cart_digest=self.quote.digest,
            max_amount=1000,
            expires_at=200,
            state="active",
        )
        valid_receipt = Receipt(f"sim_{self.fingerprint[:24]}", 1000, "USD")

        for kwargs in (
            {"mandate_id": ""},
            {"merchant": ""},
            {"currency": "usd"},
            {"cart_digest": "bad"},
            {"max_amount": 0},
            {"max_amount": True},
            {"expires_at": 0},
            {"expires_at": True},
            {"state": "expired"},
        ):
            with self.subTest(status_kwargs=kwargs):
                with self.assertRaises(AuthorizationError):
                    replace(valid_status, **kwargs)  # type: ignore[arg-type]

        for kwargs in (
            {"order_id": "sim_bad"},
            {"order_id": "sim_" + "A" * 24},
            {"amount": 0},
            {"amount": True},
            {"currency": "usd"},
            {"status": "settled"},
        ):
            with self.subTest(receipt_kwargs=kwargs):
                with self.assertRaises(AuthorizationError):
                    replace(valid_receipt, **kwargs)  # type: ignore[arg-type]

        with self.assertRaisesRegex(AuthorizationError, "request_key cannot be set"):
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=valid_status,
                request_key="request",
                receipt=None,
            )
        with self.assertRaisesRegex(AuthorizationError, "request_key is required"):
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=valid_status,
                request_key=None,
                receipt=valid_receipt,
            )
        with self.assertRaisesRegex(AuthorizationError, "Orphan receipt"):
            CheckoutProvenance(
                mandate_id="approval",
                fingerprint=self.fingerprint,
                mandate_status=None,
                request_key="request",
                receipt=valid_receipt,
            )

    def test_corrupted_mandate_and_receipt_rows_fail_closed(self) -> None:
        self.store.approve("approval", self.quote, max_amount=1000, expires_at=200)
        self.store.execute("approval", self.quote, request_key="request", now=100)

        # 1. Corrupt mandates columns and verify read_mandate, revoke, execute, find_provenance fail closed
        mandate_corruptions = (
            ("revoked", 2, "revocation state"),
            ("revoked", -1, "revocation state"),
            ("revoked", "active", "revocation state"),
            ("expires_at", 0, "mandate expiry"),
            ("expires_at", -10, "mandate expiry"),
            ("expires_at", 1.5, "mandate expiry"),
            ("expires_at", "invalid", "mandate expiry"),
            ("max_amount", 0, "max_amount"),
            ("max_amount", -10, "max_amount"),
            ("cart_digest", "not-a-sha256", "cart_digest"),
            ("currency", "usd", "mandate currency"),
            ("merchant", "", "mandate merchant"),
        )
        for column, bad_value, pattern in mandate_corruptions:
            with self.subTest(table="mandates", column=column, bad_value=bad_value):
                with closing(sqlite3.connect(self.path)) as db, db:
                    orig = db.execute(
                        f"SELECT {column} FROM mandates WHERE id='approval'"
                    ).fetchone()[0]
                    db.execute(
                        f"UPDATE mandates SET {column}=? WHERE id='approval'",
                        (bad_value,),
                    )
                try:
                    for action in (
                        lambda: self.store.read_mandate("approval", self.quote),
                        lambda: self.store.revoke("approval"),
                        lambda: self.store.read_receipt(
                            "approval", self.quote, request_key="request"
                        ),
                        lambda: self.store.find_provenance(
                            "approval", self.quote, request_key="request"
                        ),
                        lambda: self.store.execute(
                            "approval", self.quote, request_key="request", now=100
                        ),
                    ):
                        with self.assertRaisesRegex(AuthorizationError, pattern):
                            action()
                finally:
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute(
                            f"UPDATE mandates SET {column}=? WHERE id='approval'",
                            (orig,),
                        )

        # 2. Corrupt receipts columns and verify read_receipt, find_provenance, execute fail closed
        receipt_corruptions = (
            ("fingerprint", "not-hex", "receipt fingerprint"),
            ("order_id", "sim_" + "0" * 24, "order_id differs"),
            ("order_id", "bad_order", "Receipt order_id"),
            ("amount", 999, "receipt differs"),
            ("amount", 0, "Receipt amount"),
            ("currency", "EUR", "receipt differs"),
            ("currency", "usd", "Currency must be"),
        )
        for column, bad_value, pattern in receipt_corruptions:
            with self.subTest(table="receipts", column=column, bad_value=bad_value):
                with closing(sqlite3.connect(self.path)) as db, db:
                    orig = db.execute(
                        f"SELECT {column} FROM receipts WHERE request_key='request'"
                    ).fetchone()[0]
                    db.execute(
                        f"UPDATE receipts SET {column}=? WHERE request_key='request'",
                        (bad_value,),
                    )
                try:
                    for action in (
                        lambda: self.store.read_receipt(
                            "approval", self.quote, request_key="request"
                        ),
                        lambda: self.store.find_provenance(
                            "approval", self.quote, request_key="request"
                        ),
                        lambda: self.store.execute(
                            "approval", self.quote, request_key="request", now=100
                        ),
                        lambda: self.store.execute(
                            "approval", self.quote, request_key="second-key", now=100
                        ),
                    ):
                        with self.assertRaisesRegex(AuthorizationError, pattern):
                            action()
                finally:
                    with closing(sqlite3.connect(self.path)) as db, db:
                        db.execute(
                            f"UPDATE receipts SET {column}=? WHERE request_key='request'",
                            (orig,),
                        )

        # 3. Orphan receipt when parent mandate is deleted with foreign_keys OFF
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("DELETE FROM mandates WHERE id='approval'")
        for action in (
            lambda: self.store.read_receipt(
                "approval", self.quote, request_key="request"
            ),
            lambda: self.store.find_provenance("approval", self.quote),
            lambda: self.store.find_provenance(
                "approval", self.quote, request_key="request"
            ),
            lambda: self.store.execute(
                "approval", self.quote, request_key="request", now=100
            ),
        ):
            with self.assertRaisesRegex(AuthorizationError, "Orphan receipt"):
                action()


if __name__ == "__main__":
    unittest.main()
