"""Offline durable payment-attempt recovery, not a PSP or authorization service."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lab.checkout import Checkout

Outcome = Literal["unknown", "succeeded", "failed"]
Observation = Literal["pending", "succeeded", "failed"]


class AttemptConflict(ValueError):
    """An operation, approval, provider key, or result has conflicting bindings."""


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string.")


@dataclass(frozen=True)
class PaymentOperation:
    """Trusted, already-approved synthetic operation; never store payment tokens."""

    tenant_id: str
    operation_id: str
    approval_id: str
    provider: str
    provider_account: str
    idempotency_key: str
    checkout: Checkout

    def __post_init__(self) -> None:
        for name in (
            "tenant_id", "operation_id", "approval_id", "provider",
            "provider_account", "idempotency_key",
        ):
            _require_text(name, getattr(self, name))
        if not isinstance(self.checkout, Checkout):
            raise ValueError("checkout must be a validated Checkout.")

    @property
    def fingerprint(self) -> str:
        binding = [
            self.tenant_id, self.operation_id, self.approval_id, self.provider,
            self.provider_account, self.idempotency_key, self.checkout.digest,
        ]
        return hashlib.sha256(
            json.dumps(binding, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()


@dataclass(frozen=True)
class PaymentAttempt:
    outcome: Outcome
    provider_reference: str | None


@dataclass(frozen=True)
class DispatchDecision:
    attempt: PaymentAttempt
    dispatch_allowed: bool


class PaymentAttemptJournal:
    """Grant one local dispatch decision, then require trusted reconciliation.

    Callers must validate consent, expiry, revocation and payment scope before
    reserve(), and authenticate provider observations before reconcile().
    Neither method is an agent tool. Local commits cannot atomically send a
    network request, so even a crash before sending leaves an unknown outcome.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_attempts (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_account TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    outcome TEXT NOT NULL CHECK(outcome IN ('unknown','succeeded','failed')),
                    provider_reference TEXT,
                    PRIMARY KEY (tenant_id, operation_id),
                    UNIQUE (tenant_id, approval_id),
                    UNIQUE (provider, provider_account, idempotency_key),
                    UNIQUE (provider, provider_account, provider_reference)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _find(db: sqlite3.Connection, operation: PaymentOperation) -> sqlite3.Row | None:
        row = db.execute(
            "SELECT * FROM payment_attempts WHERE tenant_id=? AND operation_id=?",
            (operation.tenant_id, operation.operation_id),
        ).fetchone()
        if row is not None and row["fingerprint"] != operation.fingerprint:
            raise AttemptConflict("Operation binding changed; do not dispatch.")
        return row

    @staticmethod
    def _attempt(row: sqlite3.Row) -> PaymentAttempt:
        outcome = row["outcome"]
        if outcome not in ("unknown", "succeeded", "failed"):
            raise AttemptConflict("Stored outcome is invalid; reconciliation required.")
        return PaymentAttempt(outcome, row["provider_reference"])

    def reserve(self, operation: PaymentOperation) -> DispatchDecision:
        """Commit before dispatch; a repeated reservation never authorizes a send."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = self._find(db, operation)
            if previous is not None:
                return DispatchDecision(self._attempt(previous), False)
            if db.execute(
                "SELECT 1 FROM payment_attempts WHERE tenant_id=? AND approval_id=?",
                (operation.tenant_id, operation.approval_id),
            ).fetchone():
                raise AttemptConflict("Approval already reserved by another operation.")
            if db.execute(
                "SELECT 1 FROM payment_attempts WHERE provider=? AND provider_account=?"
                " AND idempotency_key=?",
                (operation.provider, operation.provider_account, operation.idempotency_key),
            ).fetchone():
                raise AttemptConflict("Provider idempotency key already bound.")
            db.execute(
                "INSERT INTO payment_attempts "
                "(tenant_id,operation_id,approval_id,provider,provider_account,"
                "idempotency_key,fingerprint,outcome) VALUES (?,?,?,?,?,?,?,'unknown')",
                (operation.tenant_id, operation.operation_id, operation.approval_id,
                 operation.provider, operation.provider_account, operation.idempotency_key,
                 operation.fingerprint),
            )
            return DispatchDecision(PaymentAttempt("unknown", None), True)

    def read(self, operation: PaymentOperation) -> PaymentAttempt:
        """Read a bound attempt without creating authority or changing its state."""
        with closing(self._connect()) as db:
            row = self._find(db, operation)
            if row is None:
                raise AttemptConflict("Operation was never reserved.")
            return self._attempt(row)

    def reconcile(
        self, operation: PaymentOperation, *,
        observation: Observation, provider_reference: str,
    ) -> PaymentAttempt:
        """Record trusted synthetic provider facts, not model text or HTTP errors.

        'succeeded' is the adapter's payment result, not settlement finality,
        fulfilled inventory, or the end of the refund/dispute lifecycle.
        """
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            return self._reconcile_in_transaction(
                db, operation, observation=observation, provider_reference=provider_reference,
            )

    def _reconcile_in_transaction(
        self, db: sqlite3.Connection, operation: PaymentOperation, *,
        observation: Observation, provider_reference: str,
    ) -> PaymentAttempt:
        """Participate in a caller-owned transaction without committing it."""
        if not db.in_transaction:
            raise AttemptConflict("Reconciliation requires an active transaction.")
        if observation not in ("pending", "succeeded", "failed"):
            raise ValueError("Observation must be pending, succeeded, or failed.")
        _require_text("provider_reference", provider_reference)
        outcome: Outcome = "unknown" if observation == "pending" else observation
        row = self._find(db, operation)
        if row is None:
            raise AttemptConflict("Operation was never reserved.")
        previous = self._attempt(row)
        if previous.provider_reference not in (None, provider_reference):
            raise AttemptConflict("Provider reference changed; investigate the conflict.")
        if previous.outcome != "unknown" and previous.outcome != outcome:
            raise AttemptConflict("Terminal outcome cannot be overwritten.")
        if db.execute(
            "SELECT 1 FROM payment_attempts WHERE provider=? AND provider_account=?"
            " AND provider_reference=? AND NOT (tenant_id=? AND operation_id=?)",
            (operation.provider, operation.provider_account, provider_reference,
             operation.tenant_id, operation.operation_id),
        ).fetchone():
            raise AttemptConflict("Provider reference already bound to another operation.")
        db.execute(
            "UPDATE payment_attempts SET outcome=?,provider_reference=?"
            " WHERE tenant_id=? AND operation_id=?",
            (outcome, provider_reference, operation.tenant_id, operation.operation_id),
        )
        return PaymentAttempt(outcome, provider_reference)


def main() -> None:
    """Illustrate a lost response without sending a payment or calling a model."""
    from dataclasses import asdict
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="commerce-attempt-") as directory:
        path = Path(directory) / "attempts.sqlite3"
        operation = PaymentOperation(
            "synthetic-tenant", "synthetic-operation", "synthetic-approval",
            "synthetic-psp", "synthetic-account", "synthetic-key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
        )
        first = PaymentAttemptJournal(path).reserve(operation)
        # Simulate the gap after a provider executes but before its reply arrives.
        restarted = PaymentAttemptJournal(path)
        retry = restarted.reserve(operation)
        if not first.dispatch_allowed or retry.dispatch_allowed:
            raise RuntimeError("The journal did not enforce a single dispatch decision.")
        final = restarted.reconcile(
            operation, observation="succeeded", provider_reference="sim-payment"
        )
        print(json.dumps({
            "synthetic": True,
            "real_payments": False,
            "first_dispatch_allowed": first.dispatch_allowed,
            "after_restart": asdict(retry),
            "reconciled": asdict(final),
            "settlement_verified": False,
        }))


if __name__ == "__main__":
    main()
