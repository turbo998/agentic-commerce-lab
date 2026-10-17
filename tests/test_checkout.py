"""Authorization boundary, persistence and concurrent replay regression tests."""

import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.checkout import AuthorizationError, Checkout, CheckoutStore, Receipt


class CheckoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = CheckoutStore(Path(self.directory.name) / "checkout.sqlite3")
        self.quote = Checkout("synthetic-shop", "USD", "sku-demo", 1, 1000)
        self.store.approve("approval", self.quote, max_amount=1000, expires_at=200)

    def execute(self, *, key: str = "request", now: int = 100) -> Receipt:
        return self.store.execute("approval", self.quote, request_key=key, now=now)

    def test_restart_and_retry_after_expiry_preserve_outcome(self) -> None:
        original = self.execute()
        restarted = CheckoutStore(self.store.path)
        self.assertEqual(
            original, restarted.execute("approval", self.quote, request_key="request", now=200)
        )
        self.assertEqual(original.status, "simulated")

    def test_exact_expiry_boundary(self) -> None:
        with self.assertRaisesRegex(AuthorizationError, "expired"):
            self.execute(now=200)
        self.assertEqual(self.execute(now=199).amount, 1000)

    def test_revoked_authority_and_existing_receipt(self) -> None:
        self.store.revoke("approval")
        with self.assertRaisesRegex(AuthorizationError, "revoked"):
            self.execute()
        with self.assertRaises(AuthorizationError):
            self.store.revoke("unknown")

    def test_revoke_does_not_erase_completed_outcome(self) -> None:
        original = self.execute()
        self.store.revoke("approval")
        self.assertEqual(original, self.execute())

    def test_cart_substitution_and_budget(self) -> None:
        changes = [
            {"merchant": "different-shop"}, {"currency": "EUR"}, {"sku": "different-sku"},
            {"quantity": 2}, {"amount": 999}, {"amount": 1001},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(AuthorizationError):
                self.store.execute(
                    "approval", replace(self.quote, **change), request_key="request", now=100
                )
        self.assertEqual(self.execute().amount, 1000)

    def test_key_conflict(self) -> None:
        self.execute()
        with self.assertRaisesRegex(AuthorizationError, "conflicts"):
            self.store.execute(
                "approval", replace(self.quote, sku="changed"), request_key="request", now=100
            )

    def test_single_use_approval(self) -> None:
        self.execute()
        with self.assertRaisesRegex(AuthorizationError, "consumed"):
            self.execute(key="new-request")

    def test_missing_approval_and_duplicate_provisioning(self) -> None:
        with self.assertRaisesRegex(AuthorizationError, "No trusted approval"):
            self.store.execute("missing", self.quote, request_key="request", now=100)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.approve("approval", self.quote, max_amount=1000, expires_at=300)

    def test_invalid_money_and_input(self) -> None:
        for amount in [0, -1, 1.1, True, 2**63]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                replace(self.quote, amount=amount)
        for currency in ["usd", "US", "US1", "ＵＳＤ"]:
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                replace(self.quote, currency=currency)
        with self.assertRaises(ValueError):
            self.execute(key="")
        with self.assertRaises(ValueError):
            self.execute(now=True)
        with self.assertRaises(ValueError):
            self.store.approve("new", self.quote, max_amount=999, expires_at=200)

    def test_concurrent_identical_requests_share_one_receipt(self) -> None:
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda _: self.execute(), range(8)))
        self.assertTrue(all(receipt == receipts[0] for receipt in receipts))
        with closing(sqlite3.connect(self.store.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM receipts").fetchone()[0], 1)

    def test_concurrent_different_keys_cannot_spend_twice(self) -> None:
        def attempt(key: str) -> str:
            try:
                self.execute(key=key)
                return "accepted"
            except AuthorizationError:
                return "blocked"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ["request-a", "request-b"]))
        self.assertCountEqual(results, ["accepted", "blocked"])


if __name__ == "__main__":
    unittest.main()
