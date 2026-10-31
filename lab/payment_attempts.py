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
AttemptPhase = Literal[
    "reserved_unassociated",
    "pending_associated",
    "succeeded_terminal",
    "failed_terminal",
]


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

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, str) or self.outcome not in (
            "unknown",
            "succeeded",
            "failed",
        ):
            raise AttemptConflict("Stored outcome is invalid; reconciliation required.")
        if self.provider_reference is not None and (
            not isinstance(self.provider_reference, str) or not self.provider_reference.strip()
        ):
            raise AttemptConflict(
                "Stored provider reference is invalid; reconciliation required."
            )

    @property
    def phase(self) -> AttemptPhase:
        if self.outcome == "unknown":
            return (
                "reserved_unassociated"
                if self.provider_reference is None
                else "pending_associated"
            )
        if self.provider_reference is None:
            raise AttemptConflict(
                "Stored provider reference is invalid; reconciliation required."
            )
        return (
            "succeeded_terminal"
            if self.outcome == "succeeded"
            else "failed_terminal"
        )

    @property
    def is_terminal(self) -> bool:
        return self.phase in ("succeeded_terminal", "failed_terminal")


@dataclass(frozen=True)
class DispatchDecision:
    attempt: PaymentAttempt
    dispatch_allowed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, PaymentAttempt):
            raise AttemptConflict("DispatchDecision attempt must be a PaymentAttempt.")
        if type(self.dispatch_allowed) is not bool:
            raise AttemptConflict("DispatchDecision dispatch_allowed must be a bool.")
        if self.dispatch_allowed and (
            self.attempt.outcome != "unknown" or self.attempt.provider_reference is not None
        ):
            raise AttemptConflict(
                "DispatchDecision cannot allow dispatch for a settled or referenced attempt."
            )


@dataclass(frozen=True)
class AttemptReservationPreview:
    """Read-only single-SELECT preview of reserve(operation) without mutating journal state."""

    operation: PaymentOperation
    existing_attempt: PaymentAttempt | None
    decision: DispatchDecision
    would_insert: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise AttemptConflict("A trusted PaymentOperation is required.")
        if self.existing_attempt is not None:
            if not isinstance(self.existing_attempt, PaymentAttempt):
                raise AttemptConflict(
                    "AttemptReservationPreview existing_attempt must be a PaymentAttempt or None."
                )
            _ = self.existing_attempt.phase
        if not isinstance(self.decision, DispatchDecision):
            raise AttemptConflict(
                "AttemptReservationPreview decision must be a DispatchDecision."
            )
        if type(self.would_insert) is not bool:
            raise AttemptConflict(
                "AttemptReservationPreview would_insert must be a bool."
            )
        if self.existing_attempt is None:
            if not self.would_insert or self.decision != DispatchDecision(
                PaymentAttempt("unknown", None), True
            ):
                raise AttemptConflict(
                    "Unreserved AttemptReservationPreview must allow first dispatch and insert."
                )
        else:
            if self.would_insert or self.decision != DispatchDecision(
                self.existing_attempt, False
            ):
                raise AttemptConflict(
                    "Existing AttemptReservationPreview must deny dispatch and not insert."
                )

    @property
    def phase(self) -> AttemptPhase:
        return self.decision.attempt.phase

    @property
    def dispatch_allowed(self) -> bool:
        return self.decision.dispatch_allowed


@dataclass(frozen=True)
class AttemptReconciliationPreview:
    """Read-only single-SELECT preview of reconcile(operation, ...) without mutating journal state."""

    operation: PaymentOperation
    observation: Observation
    previous_attempt: PaymentAttempt
    resulting_attempt: PaymentAttempt
    state_changed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise AttemptConflict("A trusted PaymentOperation is required.")
        if not isinstance(self.observation, str) or self.observation not in (
            "pending",
            "succeeded",
            "failed",
        ):
            raise ValueError("Observation must be pending, succeeded, or failed.")
        if not isinstance(self.previous_attempt, PaymentAttempt):
            raise AttemptConflict(
                "AttemptReconciliationPreview previous_attempt must be a PaymentAttempt."
            )
        if (
            self.previous_attempt.provider_reference is None
            and self.previous_attempt.outcome != "unknown"
        ):
            raise AttemptConflict("An unassociated terminal attempt cannot be rebound.")
        if not isinstance(self.resulting_attempt, PaymentAttempt):
            raise AttemptConflict(
                "AttemptReconciliationPreview resulting_attempt must be a PaymentAttempt."
            )
        if self.resulting_attempt.provider_reference is None:
            raise AttemptConflict(
                "Reconciled attempt must bind a non-null provider_reference."
            )
        if type(self.state_changed) is not bool:
            raise AttemptConflict(
                "AttemptReconciliationPreview state_changed must be a bool."
            )
        expected_outcome: Outcome = (
            "unknown" if self.observation == "pending" else self.observation
        )
        if self.resulting_attempt.outcome != expected_outcome:
            raise AttemptConflict(
                "Resulting attempt outcome does not match observation."
            )
        if self.previous_attempt.provider_reference not in (
            None,
            self.resulting_attempt.provider_reference,
        ):
            raise AttemptConflict("Provider reference changed; investigate the conflict.")
        if (
            self.previous_attempt.outcome != "unknown"
            and self.previous_attempt.outcome != self.resulting_attempt.outcome
        ):
            raise AttemptConflict("Terminal outcome cannot be overwritten.")
        if self.state_changed != (self.previous_attempt != self.resulting_attempt):
            raise AttemptConflict(
                "state_changed does not match previous_attempt != resulting_attempt."
            )

    @property
    def previous_phase(self) -> AttemptPhase:
        return self.previous_attempt.phase

    @property
    def resulting_phase(self) -> AttemptPhase:
        return self.resulting_attempt.phase


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
    def _require_operation(operation: PaymentOperation) -> None:
        if not isinstance(operation, PaymentOperation):
            raise AttemptConflict("A trusted PaymentOperation is required.")

    @staticmethod
    def _verify_row_binding(row: sqlite3.Row, operation: PaymentOperation) -> None:
        if (
            row["fingerprint"] != operation.fingerprint
            or row["approval_id"] != operation.approval_id
            or row["provider"] != operation.provider
            or row["provider_account"] != operation.provider_account
            or row["idempotency_key"] != operation.idempotency_key
        ):
            raise AttemptConflict("Operation binding changed; do not dispatch.")

    @staticmethod
    def _find(db: sqlite3.Connection, operation: PaymentOperation) -> sqlite3.Row | None:
        row = db.execute(
            "SELECT * FROM payment_attempts WHERE tenant_id=? AND operation_id=?",
            (operation.tenant_id, operation.operation_id),
        ).fetchone()
        if row is not None:
            PaymentAttemptJournal._verify_row_binding(row, operation)
        return row

    @staticmethod
    def _attempt(row: sqlite3.Row) -> PaymentAttempt:
        return PaymentAttempt(row["outcome"], row["provider_reference"])

    def read_attempt(self, operation: PaymentOperation) -> PaymentAttempt | None:
        """Read a bound attempt or return None if unreserved, without granting authority."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = self._find(db, operation)
        if row is None:
            return None
        attempt = self._attempt(row)
        if attempt.provider_reference is None and attempt.outcome != "unknown":
            raise AttemptConflict("Stored provider reference is invalid; reconciliation required.")
        return attempt

    def preview_reserve(
        self, operation: PaymentOperation,
    ) -> AttemptReservationPreview:
        """Preview reserve(operation) in one lock-free SELECT without mutating state."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT
                    current_op.tenant_id AS tenant_id,
                    current_op.operation_id AS operation_id,
                    current_op.approval_id AS approval_id,
                    current_op.provider AS provider,
                    current_op.provider_account AS provider_account,
                    current_op.idempotency_key AS idempotency_key,
                    current_op.fingerprint AS fingerprint,
                    current_op.outcome AS outcome,
                    current_op.provider_reference AS provider_reference,
                    EXISTS(
                        SELECT 1 FROM payment_attempts
                        WHERE tenant_id = ? AND approval_id = ? AND operation_id != ?
                    ) AS approval_conflict,
                    EXISTS(
                        SELECT 1 FROM payment_attempts
                        WHERE provider = ? AND provider_account = ? AND idempotency_key = ?
                          AND NOT (tenant_id = ? AND operation_id = ?)
                    ) AS idempotency_conflict
                FROM (SELECT 1)
                LEFT JOIN payment_attempts AS current_op
                    ON current_op.tenant_id = ? AND current_op.operation_id = ?""",
                (
                    operation.tenant_id,
                    operation.approval_id,
                    operation.operation_id,
                    operation.provider,
                    operation.provider_account,
                    operation.idempotency_key,
                    operation.tenant_id,
                    operation.operation_id,
                    operation.tenant_id,
                    operation.operation_id,
                ),
            ).fetchone()
        if row["tenant_id"] is not None:
            self._verify_row_binding(row, operation)
            existing = self._attempt(row)
            if existing.provider_reference is None and existing.outcome != "unknown":
                raise AttemptConflict(
                    "Stored provider reference is invalid; reconciliation required."
                )
            return AttemptReservationPreview(
                operation=operation,
                existing_attempt=existing,
                decision=DispatchDecision(existing, False),
                would_insert=False,
            )
        if row["approval_conflict"]:
            raise AttemptConflict("Approval already reserved by another operation.")
        if row["idempotency_conflict"]:
            raise AttemptConflict("Provider idempotency key already bound.")
        return AttemptReservationPreview(
            operation=operation,
            existing_attempt=None,
            decision=DispatchDecision(PaymentAttempt("unknown", None), True),
            would_insert=True,
        )

    def preview_reconcile(
        self,
        operation: PaymentOperation,
        *,
        observation: Observation,
        provider_reference: str,
    ) -> AttemptReconciliationPreview:
        """Preview reconcile(operation, ...) in one lock-free SELECT without mutating state."""
        self._require_operation(operation)
        if not isinstance(observation, str) or observation not in (
            "pending",
            "succeeded",
            "failed",
        ):
            raise ValueError("Observation must be pending, succeeded, or failed.")
        _require_text("provider_reference", provider_reference)
        outcome: Outcome = "unknown" if observation == "pending" else observation
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT
                    current_op.tenant_id AS tenant_id,
                    current_op.operation_id AS operation_id,
                    current_op.approval_id AS approval_id,
                    current_op.provider AS provider,
                    current_op.provider_account AS provider_account,
                    current_op.idempotency_key AS idempotency_key,
                    current_op.fingerprint AS fingerprint,
                    current_op.outcome AS outcome,
                    current_op.provider_reference AS provider_reference,
                    EXISTS(
                        SELECT 1 FROM payment_attempts
                        WHERE provider = ? AND provider_account = ? AND provider_reference = ?
                          AND NOT (tenant_id = ? AND operation_id = ?)
                    ) AS reference_conflict
                FROM (SELECT 1)
                LEFT JOIN payment_attempts AS current_op
                    ON current_op.tenant_id = ? AND current_op.operation_id = ?""",
                (
                    operation.provider,
                    operation.provider_account,
                    provider_reference,
                    operation.tenant_id,
                    operation.operation_id,
                    operation.tenant_id,
                    operation.operation_id,
                ),
            ).fetchone()
        if row["tenant_id"] is None:
            raise AttemptConflict("Operation was never reserved.")
        self._verify_row_binding(row, operation)
        previous = self._attempt(row)
        if previous.provider_reference not in (None, provider_reference):
            raise AttemptConflict("Provider reference changed; investigate the conflict.")
        if previous.provider_reference is None and previous.outcome != "unknown":
            raise AttemptConflict("An unassociated terminal attempt cannot be rebound.")
        if previous.outcome != "unknown" and previous.outcome != outcome:
            raise AttemptConflict("Terminal outcome cannot be overwritten.")
        if row["reference_conflict"]:
            raise AttemptConflict("Provider reference already bound to another operation.")
        resulting = PaymentAttempt(outcome, provider_reference)
        return AttemptReconciliationPreview(
            operation=operation,
            observation=observation,
            previous_attempt=previous,
            resulting_attempt=resulting,
            state_changed=(previous != resulting),
        )

    def reserve(self, operation: PaymentOperation) -> DispatchDecision:
        """Commit before dispatch; a repeated reservation never authorizes a send."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            return self._reserve_in_transaction(db, operation)

    def _reserve_in_transaction(
        self, db: sqlite3.Connection, operation: PaymentOperation,
    ) -> DispatchDecision:
        """Participate in a caller-owned transaction without committing it."""
        if not db.in_transaction:
            raise AttemptConflict("Reservation requires an active transaction.")
        previous = self._find(db, operation)
        if previous is not None:
            attempt = self._attempt(previous)
            if attempt.provider_reference is None and attempt.outcome != "unknown":
                raise AttemptConflict(
                    "Stored provider reference is invalid; reconciliation required."
                )
            return DispatchDecision(attempt, False)
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
        if previous.provider_reference is None and previous.outcome != "unknown":
            raise AttemptConflict("An unassociated terminal attempt cannot be rebound.")
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
