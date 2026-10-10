"""Deterministic, SQLite-backed, offline delegated checkout simulation."""

import argparse
import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


class PolicyError(ValueError):
    """A request violates the simulated user's delegation."""


@dataclass(frozen=True)
class Quote:
    merchant: str
    sku: str
    quantity: int
    total_minor: int
    currency: str
    expires_at: int

    def __post_init__(self):
        for field in ("quantity", "total_minor", "expires_at"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise PolicyError(f"{field} must be a positive integer")
        if not self.merchant or not self.sku or self.currency not in {"USD", "EUR"}:
            raise PolicyError("merchant, sku and a supported currency are required")

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Delegation:
    merchant: str
    sku: str
    max_quantity: int
    max_total_minor: int
    currency: str
    expires_at: int

    def validate(self, quote: Quote, now: int):
        for field in ("max_quantity", "max_total_minor", "expires_at"):
            if type(getattr(self, field)) is not int or getattr(self, field) <= 0:
                raise PolicyError(f"{field} must be a positive integer")
        if type(now) is not int or now < 0:
            raise PolicyError("now must be a non-negative integer")
        if now >= min(self.expires_at, quote.expires_at):
            raise PolicyError("delegation or quote expired")
        if (quote.merchant, quote.sku, quote.currency) != (
            self.merchant, self.sku, self.currency
        ):
            raise PolicyError("merchant, item or currency outside delegation")
        if quote.quantity > self.max_quantity or quote.total_minor > self.max_total_minor:
            raise PolicyError("quantity or total exceeds delegation")


class Checkout:
    """Local trusted boundary; callers cannot supply arbitrary payment credentials."""

    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS grants (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'consumed'))
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                idempotency_key TEXT UNIQUE NOT NULL,
                fingerprint TEXT NOT NULL,
                grant_id TEXT UNIQUE NOT NULL REFERENCES grants(id),
                total_minor INTEGER NOT NULL,
                currency TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                subject TEXT NOT NULL
            );
        """)

    def close(self):
        self.db.close()

    def grant(self, grant_id: str, delegation: Delegation, quote: Quote, now: int):
        if not grant_id.startswith("sim_") or len(grant_id) <= 4:
            raise PolicyError("grant identifiers must use the sim_ namespace")
        delegation.validate(quote, now)
        self.db.execute(
            "INSERT INTO grants VALUES (?, ?, ?, 'active')",
            (grant_id, quote.fingerprint, min(delegation.expires_at, quote.expires_at)),
        )

    def revoke(self, grant_id: str):
        changed = self.db.execute(
            "UPDATE grants SET status='revoked' WHERE id=? AND status='active'",
            (grant_id,),
        ).rowcount
        if not changed:
            raise PolicyError("grant missing or no longer active")

    def complete(self, grant_id: str, quote: Quote, key: str, now: int) -> dict:
        if not key or type(now) is not int or now < 0:
            raise PolicyError("idempotency key and non-negative integer time required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute(
                "SELECT id, fingerprint, grant_id, total_minor, currency FROM orders "
                "WHERE idempotency_key=?", (key,)
            ).fetchone()
            if previous:
                if previous[1:3] != (quote.fingerprint, grant_id):
                    raise PolicyError("idempotency key reused for a different request")
                result = self._receipt(previous[0], previous[3], previous[4])
            else:
                grant = self.db.execute(
                    "SELECT fingerprint, expires_at, status FROM grants WHERE id=?",
                    (grant_id,),
                ).fetchone()
                if not grant or grant[2] != "active":
                    raise PolicyError("grant missing, revoked or already consumed")
                if now >= min(grant[1], quote.expires_at):
                    raise PolicyError("grant or quote expired")
                if grant[0] != quote.fingerprint:
                    raise PolicyError("quote changed after approval")
                cursor = self.db.execute(
                    "INSERT INTO orders (idempotency_key, fingerprint, grant_id, "
                    "total_minor, currency) VALUES (?, ?, ?, ?, ?)",
                    (key, quote.fingerprint, grant_id, quote.total_minor, quote.currency),
                )
                self.db.execute(
                    "UPDATE grants SET status='consumed' WHERE id=?", (grant_id,)
                )
                self.db.execute(
                    "INSERT INTO events (kind, subject) VALUES ('simulated_order', ?)",
                    (str(cursor.lastrowid),),
                )
                result = self._receipt(cursor.lastrowid, quote.total_minor, quote.currency)
            self.db.execute("COMMIT")
            return result
        except (PolicyError, sqlite3.Error):
            self.db.execute("ROLLBACK")
            raise

    @staticmethod
    def _receipt(order_id: int, total_minor: int, currency: str) -> dict:
        return {
            "mode": "offline_simulation",
            "order_id": order_id,
            "status": "simulated_order",
            "total_minor": total_minor,
            "currency": currency,
            "real_payment": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=":memory:")
    args = parser.parse_args()
    checkout = Checkout(args.database)
    try:
        quote = Quote("synthetic-shop", "coffee-001", 1, 1250, "USD", 200)
        delegation = Delegation("synthetic-shop", "coffee-001", 1, 1500, "USD", 200)
        # Unique IDs keep repeated demonstrations safe with a persistent database.
        run_id = uuid.uuid4().hex
        checkout.grant(f"sim_{run_id}", delegation, quote, now=100)
        receipt = checkout.complete(f"sim_{run_id}", quote, run_id, now=101)
        retry = checkout.complete(f"sim_{run_id}", quote, run_id, now=102)
        print(json.dumps({"receipt": receipt, "retry_same_order": receipt == retry}, indent=2))
    finally:
        checkout.close()


if __name__ == "__main__":
    main()
