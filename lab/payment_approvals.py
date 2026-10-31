"""Trusted local approval records and atomic admission, not proof of consent."""

import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lab.checkout_admission import validate_signed_checkout
from lab.payment_attempts import DispatchDecision, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import RequestSignatureSnapshot

ApprovalState = Literal["active", "revoked"]


class PaymentApprovalError(ValueError):
    """An approval, configured store or clock cannot admit the bound operation."""


@dataclass(frozen=True)
class PaymentApprovalStatus:
    """Persisted local approval record state, not live validity or dispatch authority."""

    fingerprint: str
    expires_at: int
    state: ApprovalState


@dataclass(frozen=True)
class ApprovalAdmission:
    """Local first-gate history, not authenticated consent or a payment receipt."""

    fingerprint: str
    admitted_at: int
    expires_at: int


class PaymentApprovalStore:
    """Opt-in trusted-operator metadata, not an agent tool or consent service.

    Records are immutable and never reactivated or pruned by this API. Admission
    and revocation serialize locally; revocation cannot undo a prior reservation
    or stop an external send. Direct journal/SQL writes bypass this boundary.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_approvals (
                    tenant_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    expires_at INTEGER NOT NULL CHECK(expires_at>0),
                    revoked INTEGER NOT NULL CHECK(revoked IN (0,1)),
                    PRIMARY KEY (tenant_id,approval_id)
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_admissions (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    admitted_at INTEGER NOT NULL CHECK(admitted_at>=0),
                    expires_at INTEGER NOT NULL CHECK(expires_at>admitted_at),
                    PRIMARY KEY (tenant_id,operation_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _require_operation(operation: PaymentOperation) -> None:
        if not isinstance(operation, PaymentOperation):
            raise PaymentApprovalError("A trusted PaymentOperation is required.")

    @staticmethod
    def _bound_approval(db: sqlite3.Connection, operation: PaymentOperation) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM payment_approvals WHERE tenant_id=? AND approval_id=?",
            (operation.tenant_id, operation.approval_id),
        ).fetchone()
        if row is None:
            raise PaymentApprovalError("No recorded approval exists for this scope.")
        if row["fingerprint"] != operation.fingerprint:
            raise PaymentApprovalError("Approval differs from the bound operation.")
        return row

    def approve(self, operation: PaymentOperation, *, expires_at: int) -> None:
        """Record trusted operator input; never infer or prove a person's consent."""
        self._require_operation(operation)
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Approval expiry must be a positive signed-64-bit integer.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM payment_approvals WHERE tenant_id=? AND approval_id=?",
                (operation.tenant_id, operation.approval_id),
            ).fetchone():
                raise PaymentApprovalError("Approval already recorded; replacement is forbidden.")
            db.execute(
                "INSERT INTO payment_approvals VALUES (?,?,?,?,0)",
                (operation.tenant_id, operation.approval_id, operation.fingerprint, expires_at),
            )

    def revoke(self, operation: PaymentOperation) -> None:
        """Revoke the exact recorded binding; repeated revocation is idempotent."""
        self._require_operation(operation)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._bound_approval(db, operation)
            db.execute(
                "UPDATE payment_approvals SET revoked=1 WHERE tenant_id=? AND approval_id=?",
                (operation.tenant_id, operation.approval_id),
            )

    def read_approval(self, operation: PaymentOperation) -> PaymentApprovalStatus | None:
        """Read local approval record state without clock sampling or new authority."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT fingerprint,expires_at,revoked FROM payment_approvals"
                " WHERE tenant_id=? AND approval_id=?",
                (operation.tenant_id, operation.approval_id),
            ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != operation.fingerprint:
            raise PaymentApprovalError("Approval differs from the bound operation.")
        expires_at, revoked = row["expires_at"], row["revoked"]
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Stored approval expiry is invalid.")
        if type(revoked) is not int or revoked not in (0, 1):
            raise PaymentApprovalError("Stored approval revocation state is invalid.")
        return PaymentApprovalStatus(
            row["fingerprint"],
            expires_at,
            "revoked" if revoked else "active",
        )

    def find_admission(self, operation: PaymentOperation) -> ApprovalAdmission | None:
        """Read first-gate history or return None if absent, without new authority."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT fingerprint,admitted_at,expires_at FROM payment_admissions"
                " WHERE tenant_id=? AND operation_id=?",
                (operation.tenant_id, operation.operation_id),
            ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != operation.fingerprint:
            raise PaymentApprovalError("Admission record differs from the bound operation.")
        admitted_at, expires_at = row["admitted_at"], row["expires_at"]
        if (type(admitted_at) is not int or type(expires_at) is not int
                or not 0 <= admitted_at < expires_at <= 2**63 - 1):
            raise PaymentApprovalError("Stored admission times are invalid.")
        return ApprovalAdmission(row["fingerprint"], admitted_at, expires_at)

    def read_admission(self, operation: PaymentOperation) -> ApprovalAdmission:
        """Read first-gate history even after revocation, without new authority."""
        admission = self.find_admission(operation)
        if admission is None:
            raise PaymentApprovalError("No first-admission record exists for this operation.")
        return admission

    def admit(
        self,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
        signature: RequestSignatureSnapshot,
        *,
        clock: Callable[[], int],
        expected_target_uri: str,
        method: str,
        target_uri: str,
        content_type: str,
        content_digest: str,
        content_encoding: str | None,
        body: bytes,
    ) -> DispatchDecision:
        """Validate signed input, then fence local approval and reservation together.

        A trusted fresh clock is sampled after the write lock is acquired. Even
        non-dispatch retries require active approval; use journal.read for recovery
        after revocation/expiry. First-gate history commits with a new reservation;
        existing reservations are never backfilled. No payment is sent or undone.
        """
        if not isinstance(journal, PaymentAttemptJournal) or not callable(clock):
            raise PaymentApprovalError("A trusted journal and clock callable are required.")
        validate_signed_checkout(
            operation, signature, expected_target_uri=expected_target_uri, method=method,
            target_uri=target_uri, content_type=content_type, content_digest=content_digest,
            content_encoding=content_encoding, body=body,
        )
        if self.path.resolve(strict=True) != journal.path.resolve(strict=True):
            raise PaymentApprovalError("Atomic admission requires the same resolved SQLite file.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            decision = self._admit_in_transaction(db, journal, operation, clock=clock)
        return decision

    def _admit_in_transaction(
        self, db: sqlite3.Connection, journal: PaymentAttemptJournal,
        operation: PaymentOperation, *, clock: Callable[[], int],
    ) -> DispatchDecision:
        """Participate in a caller-owned transaction after signed input validation."""
        if not db.in_transaction:
            raise PaymentApprovalError("Approval admission requires an active transaction.")
        row = self._bound_approval(db, operation)
        if row["revoked"] != 0:
            raise PaymentApprovalError("Approval is revoked.")
        expires_at = row["expires_at"]
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Stored approval expiry is invalid.")
        now = clock()
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise PaymentApprovalError("Clock must return a nonnegative signed-64-bit integer.")
        if now >= expires_at:
            raise PaymentApprovalError("Approval is expired.")
        decision = journal._reserve_in_transaction(db, operation)
        if decision.dispatch_allowed:
            db.execute(
                "INSERT INTO payment_admissions"
                " (tenant_id,operation_id,fingerprint,admitted_at,expires_at)"
                " VALUES (?,?,?,?,?)",
                (operation.tenant_id, operation.operation_id, operation.fingerprint,
                 now, expires_at),
            )
        return decision
