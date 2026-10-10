import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from lab.commerce import Checkout, Delegation, PolicyError, Quote


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.checkout = Checkout()
        self.addCleanup(self.checkout.close)
        self.quote = Quote("shop", "coffee", 1, 1250, "USD", 200)
        self.delegation = Delegation("shop", "coffee", 1, 1500, "USD", 200)

    def grant(self):
        self.checkout.grant("sim_one", self.delegation, self.quote, 100)

    def test_happy_path_and_retry(self):
        self.grant()
        first = self.checkout.complete("sim_one", self.quote, "key", 101)
        retry = self.checkout.complete("sim_one", self.quote, "key", 300)
        self.assertEqual(first, retry)
        self.assertFalse(first["real_payment"])
        self.assertEqual(self.checkout.db.execute("SELECT count(*) FROM orders").fetchone()[0], 1)
        self.assertEqual(self.checkout.db.execute("SELECT count(*) FROM events").fetchone()[0], 1)

    def test_policy_constraints(self):
        for change in (
            {"merchant": "other"}, {"sku": "other"}, {"quantity": 2},
            {"total_minor": 1501}, {"currency": "EUR"}, {"expires_at": 100},
        ):
            with self.subTest(change=change), self.assertRaises(PolicyError):
                self.checkout.grant("sim_one", self.delegation, replace(self.quote, **change), 100)

    def test_exact_budget_is_allowed(self):
        quote = replace(self.quote, total_minor=1500)
        self.checkout.grant("sim_exact", self.delegation, quote, 100)
        self.assertEqual(self.checkout.complete("sim_exact", quote, "key", 101)["total_minor"], 1500)

    def test_changed_quote_does_not_consume_grant(self):
        self.grant()
        with self.assertRaisesRegex(PolicyError, "quote changed"):
            self.checkout.complete("sim_one", replace(self.quote, total_minor=1251), "key", 101)
        self.checkout.complete("sim_one", self.quote, "key", 102)

    def test_replay_under_new_key_is_rejected(self):
        self.grant()
        self.checkout.complete("sim_one", self.quote, "key", 101)
        with self.assertRaises(PolicyError):
            self.checkout.complete("sim_one", self.quote, "other", 102)

    def test_idempotency_conflict_is_rejected(self):
        self.grant()
        self.checkout.complete("sim_one", self.quote, "key", 101)
        for grant, quote in (
            ("sim_other", self.quote), ("sim_one", replace(self.quote, total_minor=1200))
        ):
            with self.subTest(grant=grant), self.assertRaises(PolicyError):
                self.checkout.complete(grant, quote, "key", 102)

    def test_revocation_and_expiry(self):
        self.grant()
        self.checkout.revoke("sim_one")
        with self.assertRaises(PolicyError):
            self.checkout.complete("sim_one", self.quote, "key", 101)
        with self.assertRaises(PolicyError):
            self.checkout.revoke("missing")
        self.checkout.grant("sim_two", self.delegation, self.quote, 100)
        with self.assertRaises(PolicyError):
            self.checkout.complete("sim_two", self.quote, "key", 200)

    def test_missing_grant_and_invalid_key(self):
        for grant, key in (("missing", "key"), ("sim_one", "")):
            with self.subTest(grant=grant), self.assertRaises(PolicyError):
                self.checkout.complete(grant, self.quote, key, 100)

    def test_invalid_amounts_are_rejected(self):
        for value in (-1, 0, 1.5, True):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                replace(self.quote, total_minor=value)

    def test_database_failure_rolls_back_payment_and_event(self):
        self.grant()
        self.checkout.db.execute(
            "CREATE TRIGGER fail_event BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.checkout.complete("sim_one", self.quote, "key", 101)
        self.assertEqual(self.checkout.db.execute("SELECT count(*) FROM orders").fetchone()[0], 0)
        self.assertEqual(self.checkout.db.execute("SELECT status FROM grants").fetchone()[0], "active")

    def test_persistent_retry_across_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.sqlite3"
            one = Checkout(path)
            try:
                one.grant("sim_one", self.delegation, self.quote, 100)
                first = one.complete("sim_one", self.quote, "key", 101)
            finally:
                one.close()
            two = Checkout(path)
            try:
                self.assertEqual(two.complete("sim_one", self.quote, "key", 102), first)
            finally:
                two.close()

    def test_concurrent_requests_cannot_double_consume_grant(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.sqlite3"
            setup = Checkout(path)
            try:
                setup.grant("sim_one", self.delegation, self.quote, 100)
            finally:
                setup.close()

            def buy(key):
                checkout = Checkout(path)
                try:
                    return checkout.complete("sim_one", self.quote, key, 101)
                except PolicyError:
                    return "rejected"
                finally:
                    checkout.close()

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(buy, ["one", "two"]))
            self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
            self.assertEqual(results.count("rejected"), 1)


if __name__ == "__main__":
    unittest.main()
