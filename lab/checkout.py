"""Deterministic authorization and atomic local checkout receipts."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path


class AuthorizationError(ValueError):
    """The checkout exceeds an approved mandate or reuses its authority."""


@dataclass(frozen=True)
class Checkout:
    """A synthetic merchant quote, including tax and shipping in minor units."""

    merchant: str
    currency: str
    sku: str
    quantity: int
    amount: int

    def __post_init__(self) -> None:
        if not self.merchant or not self.sku:
            raise ValueError("Checkout requires a merchant and a nonempty SKU.")
        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isupper():
            raise ValueError("Currency must be a three-letter uppercase ASCII code.")
        if not self.currency.isalpha():
            raise ValueError("Currency must contain only letters.")
        for name, value in (("amount", self.amount), ("quantity", self.quantity)):
            if type(value) is not int or not 0 < value <= 2**63 - 1:
                raise ValueError(f"{name} must be a positive signed 64-bit integer.")

    @property
    def digest(self) -> str:
        """Return a local cart binding; this is not a protocol signature."""
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class Receipt:
    """A persisted local outcome with no card or payment token information."""

    order_id: str
    amount: int
    currency: str
    status: str = "simulated"


class CheckoutStore:
    """Persist trusted approvals and receipts; never call a real payment rail."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS mandates (
                    id TEXT PRIMARY KEY,
                    merchant TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    cart_digest TEXT NOT NULL,
                    max_amount INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    request_key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    mandate_id TEXT NOT NULL UNIQUE REFERENCES mandates(id),
                    order_id TEXT NOT NULL UNIQUE,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def approve(
        self, mandate_id: str, checkout: Checkout, *, max_amount: int, expires_at: int
    ) -> None:
        """Trusted operator entry point, not an agent tool or consent UI."""
        if not mandate_id:
            raise ValueError("Approval requires a nonempty mandate ID.")
        if type(max_amount) is not int or not checkout.amount <= max_amount <= 2**63 - 1:
            raise ValueError("Approval limit must cover the quote in signed 64-bit minor units.")
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise ValueError("Approval expiry must be a positive signed 64-bit Unix timestamp.")
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO mandates (id,merchant,currency,cart_digest,max_amount,expires_at)"
                " VALUES (?,?,?,?,?,?)",
                (mandate_id, checkout.merchant, checkout.currency, checkout.digest,
                 max_amount, expires_at),
            )

    def revoke(self, mandate_id: str) -> None:
        """Revoke unspent authority without erasing completed receipts."""
        with closing(self._connect()) as db, db:
            cursor = db.execute("UPDATE mandates SET revoked=1 WHERE id=?", (mandate_id,))
            if cursor.rowcount != 1:
                raise AuthorizationError(f"Cannot revoke unknown mandate {mandate_id!r}.")

    def execute(
        self, mandate_id: str, checkout: Checkout, *, request_key: str, now: int
    ) -> Receipt:
        """Atomically consume one approval; identical retries return the same receipt."""
        if not request_key:
            raise ValueError("Checkout requires a nonempty idempotency key.")
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise ValueError("The trusted clock must provide a nonnegative Unix timestamp.")
        fingerprint = hashlib.sha256(
            json.dumps([mandate_id, checkout.digest], separators=(",", ":")).encode()
        ).hexdigest()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT * FROM receipts WHERE request_key=?", (request_key,)
            ).fetchone()
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise AuthorizationError("Idempotency key conflicts with an earlier checkout.")
                return Receipt(previous["order_id"], previous["amount"], previous["currency"])
            mandate = db.execute(
                "SELECT * FROM mandates WHERE id=?", (mandate_id,)
            ).fetchone()
            if mandate is None:
                raise AuthorizationError("No trusted approval exists for this mandate.")
            if mandate["revoked"] or now >= mandate["expires_at"]:
                raise AuthorizationError("Mandate is revoked or expired; obtain new approval.")
            if checkout.merchant != mandate["merchant"] or checkout.currency != mandate["currency"]:
                raise AuthorizationError("Merchant or currency differs from the trusted approval.")
            if checkout.amount > mandate["max_amount"]:
                raise AuthorizationError("Checkout exceeds the approved spending limit.")
            if checkout.digest != mandate["cart_digest"]:
                raise AuthorizationError("Cart changed after approval; obtain new approval.")
            if db.execute(
                "SELECT 1 FROM receipts WHERE mandate_id=?", (mandate_id,)
            ).fetchone():
                raise AuthorizationError("Mandate already consumed; retry with the original key.")
            receipt = Receipt(f"sim_{fingerprint[:24]}", checkout.amount, checkout.currency)
            db.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?,?)",
                (request_key, fingerprint, mandate_id, receipt.order_id,
                 receipt.amount, receipt.currency),
            )
            return receipt
