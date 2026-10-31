"""Trusted local approval records and atomic admission, not proof of consent."""

import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lab.checkout_admission import validate_signed_checkout
from lab.payment_attempts import (
    AttemptConflict,
    AttemptPhase,
    DispatchDecision,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import RequestSignatureSnapshot

ApprovalState = Literal["active", "revoked"]
ApprovalTimedState = Literal["active", "expired", "revoked"]
TwoStoreAdmissionPath = Literal["direct_reservation", "approval_admission"]


class PaymentApprovalError(ValueError):
    """An approval, configured store or clock cannot admit the bound operation."""


@dataclass(frozen=True)
class PaymentApprovalStatus:
    """Persisted local approval record state, not live validity or dispatch authority."""

    fingerprint: str
    expires_at: int
    state: ApprovalState

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise PaymentApprovalError(
                "Approval fingerprint must be a 64-char hex SHA-256 digest."
            )
        if type(self.expires_at) is not int or not 0 < self.expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Stored approval expiry is invalid.")
        if not isinstance(self.state, str) or self.state not in ("active", "revoked"):
            raise PaymentApprovalError("Stored approval revocation state is invalid.")

    def state_at(self, now: int) -> ApprovalTimedState:
        """Evaluate approval status against a trusted nonnegative signed-64-bit clock."""
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise PaymentApprovalError(
                "Clock must return a nonnegative signed-64-bit integer."
            )
        if self.state == "revoked":
            return "revoked"
        if now >= self.expires_at:
            return "expired"
        return "active"


@dataclass(frozen=True)
class ApprovalAdmission:
    """Local first-gate history, not authenticated consent or a payment receipt."""

    fingerprint: str
    admitted_at: int
    expires_at: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise PaymentApprovalError(
                "Admission fingerprint must be a 64-char hex SHA-256 digest."
            )
        if (
            type(self.admitted_at) is not int
            or type(self.expires_at) is not int
            or not 0 <= self.admitted_at < self.expires_at <= 2**63 - 1
        ):
            raise PaymentApprovalError("Stored admission times are invalid.")


@dataclass(frozen=True)
class ApprovalAdmissionProvenance:
    """Local cross-table attempt, approval-status and first-admission snapshot, not authority."""

    fingerprint: str
    attempt: PaymentAttempt
    approval_status: PaymentApprovalStatus | None
    approval_admission: ApprovalAdmission | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise PaymentApprovalError(
                "Provenance fingerprint must be a 64-char hex SHA-256 digest."
            )
        if not isinstance(self.attempt, PaymentAttempt):
            raise PaymentApprovalError("A persisted PaymentAttempt is required.")
        if self.attempt.provider_reference is None and self.attempt.outcome != "unknown":
            raise PaymentApprovalError(
                "Stored attempt outcome and provider reference are inconsistent."
            )
        if self.approval_status is not None:
            if not isinstance(self.approval_status, PaymentApprovalStatus):
                raise PaymentApprovalError(
                    "approval_status must be a PaymentApprovalStatus or None."
                )
            if self.approval_status.fingerprint != self.fingerprint:
                raise PaymentApprovalError("Approval differs from the bound operation.")
        if self.approval_admission is not None:
            if not isinstance(self.approval_admission, ApprovalAdmission):
                raise PaymentApprovalError(
                    "approval_admission must be an ApprovalAdmission or None."
                )
            if self.approval_admission.fingerprint != self.fingerprint:
                raise PaymentApprovalError("Admission record differs from the bound operation.")
            if self.approval_status is None:
                raise PaymentApprovalError(
                    "Orphan admission record exists without a recorded approval."
                )
            if self.approval_admission.expires_at != self.approval_status.expires_at:
                raise PaymentApprovalError(
                    "Stored admission expiry differs from the recorded approval expiry."
                )

    @property
    def path(self) -> TwoStoreAdmissionPath:
        if self.approval_admission is not None:
            return "approval_admission"
        return "direct_reservation"

    @property
    def attempt_phase(self) -> AttemptPhase:
        return self.attempt.phase


@dataclass(frozen=True)
class ApprovalAdmissionPreview:
    """Single-SELECT read-only dry-run preview of PaymentApprovalStore.admit()."""

    operation: PaymentOperation
    now: int
    approval_status: PaymentApprovalStatus
    existing_attempt: PaymentAttempt | None
    existing_admission: ApprovalAdmission | None
    decision: DispatchDecision
    projected_admission: ApprovalAdmission | None
    would_record_admission: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise PaymentApprovalError("A trusted PaymentOperation is required.")
        if type(self.now) is not int or not 0 <= self.now <= 2**63 - 1:
            raise PaymentApprovalError(
                "Clock must return a nonnegative signed-64-bit integer."
            )
        if not isinstance(self.approval_status, PaymentApprovalStatus):
            raise PaymentApprovalError(
                "approval_status must be a PaymentApprovalStatus."
            )
        if self.approval_status.fingerprint != self.operation.fingerprint:
            raise PaymentApprovalError("Approval differs from the bound operation.")
        if self.approval_status.state != "active":
            raise PaymentApprovalError("Approval is revoked.")
        if self.now >= self.approval_status.expires_at:
            raise PaymentApprovalError("Approval is expired.")
        if self.existing_attempt is not None:
            if not isinstance(self.existing_attempt, PaymentAttempt):
                raise PaymentApprovalError(
                    "existing_attempt must be a PaymentAttempt or None."
                )
            _ = self.existing_attempt.phase
        if self.existing_admission is not None:
            if not isinstance(self.existing_admission, ApprovalAdmission):
                raise PaymentApprovalError(
                    "existing_admission must be an ApprovalAdmission or None."
                )
            if self.existing_admission.fingerprint != self.operation.fingerprint:
                raise PaymentApprovalError(
                    "Admission record differs from the bound operation."
                )
            if self.existing_attempt is None:
                raise PaymentApprovalError(
                    "Orphan admission record exists without a payment reservation."
                )
            if self.existing_admission.expires_at != self.approval_status.expires_at:
                raise PaymentApprovalError(
                    "Stored admission expiry differs from the recorded approval expiry."
                )
        if not isinstance(self.decision, DispatchDecision):
            raise PaymentApprovalError("decision must be a DispatchDecision.")
        if type(self.would_record_admission) is not bool:
            raise PaymentApprovalError("would_record_admission must be a bool.")
        if self.existing_attempt is None:
            expected_admission = ApprovalAdmission(
                self.operation.fingerprint, self.now, self.approval_status.expires_at
            )
            if (
                not self.would_record_admission
                or self.decision
                != DispatchDecision(PaymentAttempt("unknown", None), True)
                or self.projected_admission != expected_admission
            ):
                raise PaymentApprovalError(
                    "Unreserved approval preview must allow dispatch and project a new admission."
                )
        else:
            if (
                self.would_record_admission
                or self.decision != DispatchDecision(self.existing_attempt, False)
                or self.projected_admission != self.existing_admission
            ):
                raise PaymentApprovalError(
                    "Existing attempt approval preview must deny dispatch and never backfill admission."
                )

    @property
    def dispatch_allowed(self) -> bool:
        return self.decision.dispatch_allowed

    @property
    def attempt_phase(self) -> AttemptPhase:
        return self.decision.attempt.phase


@dataclass(frozen=True)
class ApprovalRevocationPreview:
    """Single-SELECT read-only dry-run preview of PaymentApprovalStore.revoke()."""

    operation: PaymentOperation
    existing_status: PaymentApprovalStatus
    projected_status: PaymentApprovalStatus
    would_revoke: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise PaymentApprovalError("A trusted PaymentOperation is required.")
        if not isinstance(self.existing_status, PaymentApprovalStatus) or not isinstance(
            self.projected_status, PaymentApprovalStatus
        ):
            raise PaymentApprovalError(
                "existing_status and projected_status must be PaymentApprovalStatus instances."
            )
        if self.existing_status.fingerprint != self.operation.fingerprint:
            raise PaymentApprovalError("Approval differs from the bound operation.")
        expected_projected = PaymentApprovalStatus(
            self.existing_status.fingerprint,
            self.existing_status.expires_at,
            "revoked",
        )
        if self.projected_status != expected_projected:
            raise PaymentApprovalError(
                "projected_status must match existing_status with state='revoked'."
            )
        if type(self.would_revoke) is not bool:
            raise PaymentApprovalError("would_revoke must be a boolean.")
        if self.would_revoke != (self.existing_status.state == "active"):
            raise PaymentApprovalError(
                "would_revoke must be True iff existing_status is active."
            )


@dataclass(frozen=True)
class ApprovalGrantPreview:
    """Single-SELECT read-only dry-run preview of PaymentApprovalStore.approve()."""

    operation: PaymentOperation
    expires_at: int
    projected_status: PaymentApprovalStatus
    would_record: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise PaymentApprovalError("A trusted PaymentOperation is required.")
        if type(self.expires_at) is not int or not 0 < self.expires_at <= 2**63 - 1:
            raise PaymentApprovalError(
                "Approval expiry must be a positive signed-64-bit integer."
            )
        expected_projected = PaymentApprovalStatus(
            self.operation.fingerprint,
            self.expires_at,
            "active",
        )
        if self.projected_status != expected_projected:
            raise PaymentApprovalError(
                "projected_status must match active PaymentApprovalStatus for the operation."
            )
        if type(self.would_record) is not bool or not self.would_record:
            raise PaymentApprovalError(
                "would_record must be True for a valid ApprovalGrantPreview."
            )


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
        expires_at, revoked = row["expires_at"], row["revoked"]
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Stored approval expiry is invalid.")
        if type(revoked) is not int or revoked not in (0, 1):
            raise PaymentApprovalError("Stored approval revocation state is invalid.")
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

    def preview_approve(
        self, operation: PaymentOperation, *, expires_at: int
    ) -> ApprovalGrantPreview:
        """Preview approve() in one lock-free SELECT without mutating payment_approvals."""
        self._require_operation(operation)
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Approval expiry must be a positive signed-64-bit integer.")
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT 1 FROM payment_approvals WHERE tenant_id=? AND approval_id=?",
                (operation.tenant_id, operation.approval_id),
            ).fetchone()
        if row is not None:
            raise PaymentApprovalError("Approval already recorded; replacement is forbidden.")
        return ApprovalGrantPreview(
            operation=operation,
            expires_at=expires_at,
            projected_status=PaymentApprovalStatus(
                operation.fingerprint, expires_at, "active"
            ),
            would_record=True,
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

    def preview_revoke(
        self, operation: PaymentOperation
    ) -> ApprovalRevocationPreview:
        """Preview revoke() in one lock-free SELECT without mutating payment_approvals."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = self._bound_approval(db, operation)
        existing_status = PaymentApprovalStatus(
            row["fingerprint"],
            row["expires_at"],
            "revoked" if row["revoked"] else "active",
        )
        projected_status = PaymentApprovalStatus(
            row["fingerprint"],
            row["expires_at"],
            "revoked",
        )
        return ApprovalRevocationPreview(
            operation=operation,
            existing_status=existing_status,
            projected_status=projected_status,
            would_revoke=existing_status.state == "active",
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

    def find_provenance(
        self,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
    ) -> ApprovalAdmissionProvenance | None:
        """Read cross-table attempt, approval-status and first-admission history in one snapshot."""
        if (
            not isinstance(journal, PaymentAttemptJournal)
            or not isinstance(operation, PaymentOperation)
        ):
            raise PaymentApprovalError("A trusted journal and PaymentOperation are required.")
        if self.path.resolve(strict=True) != journal.path.resolve(strict=True):
            raise PaymentApprovalError(
                "Cross-table provenance lookup requires the same resolved SQLite file."
            )
        with closing(self._connect()) as db:
            row = db.execute(
                """
                SELECT
                    att.fingerprint AS att_fingerprint,
                    att.approval_id AS att_approval_id,
                    att.provider AS att_provider,
                    att.provider_account AS att_provider_account,
                    att.idempotency_key AS att_idempotency_key,
                    att.outcome AS att_outcome,
                    att.provider_reference AS att_provider_reference,
                    adm.fingerprint AS adm_fingerprint,
                    adm.admitted_at AS adm_admitted_at,
                    adm.expires_at AS adm_expires_at,
                    app.fingerprint AS app_fingerprint,
                    app.expires_at AS app_expires_at,
                    app.revoked AS app_revoked
                FROM (SELECT 1)
                LEFT JOIN payment_attempts att
                    ON att.tenant_id=? AND att.operation_id=?
                LEFT JOIN payment_admissions adm
                    ON adm.tenant_id=? AND adm.operation_id=?
                LEFT JOIN payment_approvals app
                    ON app.tenant_id=? AND app.approval_id=?
                """,
                (
                    operation.tenant_id,
                    operation.operation_id,
                    operation.tenant_id,
                    operation.operation_id,
                    operation.tenant_id,
                    operation.approval_id,
                ),
            ).fetchone()
        if row is None or (row["att_fingerprint"] is None and row["adm_fingerprint"] is None):
            return None
        if row["att_fingerprint"] is None:
            raise PaymentApprovalError(
                "Orphan admission record exists without a payment reservation."
            )
        att_row = {
            "fingerprint": row["att_fingerprint"],
            "approval_id": row["att_approval_id"],
            "provider": row["att_provider"],
            "provider_account": row["att_provider_account"],
            "idempotency_key": row["att_idempotency_key"],
            "outcome": row["att_outcome"],
            "provider_reference": row["att_provider_reference"],
        }
        journal._verify_row_binding(att_row, operation)
        attempt = journal._attempt(att_row)
        if attempt.provider_reference is None and attempt.outcome != "unknown":
            raise AttemptConflict("Stored attempt outcome and provider reference are inconsistent.")

        approval_status: PaymentApprovalStatus | None = None
        if row["app_fingerprint"] is not None:
            if row["app_fingerprint"] != operation.fingerprint:
                raise PaymentApprovalError("Approval differs from the bound operation.")
            app_expires_at, app_revoked = row["app_expires_at"], row["app_revoked"]
            if type(app_expires_at) is not int or not 0 < app_expires_at <= 2**63 - 1:
                raise PaymentApprovalError("Stored approval expiry is invalid.")
            if type(app_revoked) is not int or app_revoked not in (0, 1):
                raise PaymentApprovalError("Stored approval revocation state is invalid.")
            approval_status = PaymentApprovalStatus(
                operation.fingerprint,
                app_expires_at,
                "revoked" if app_revoked else "active",
            )

        approval_admission: ApprovalAdmission | None = None
        if row["adm_fingerprint"] is not None:
            if row["adm_fingerprint"] != operation.fingerprint:
                raise PaymentApprovalError("Admission record differs from the bound operation.")
            adm_at, adm_exp = row["adm_admitted_at"], row["adm_expires_at"]
            if (
                type(adm_at) is not int
                or type(adm_exp) is not int
                or not 0 <= adm_at < adm_exp <= 2**63 - 1
            ):
                raise PaymentApprovalError("Stored admission times are invalid.")
            if approval_status is None:
                raise PaymentApprovalError(
                    "Orphan admission record exists without a recorded approval."
                )
            if adm_exp != approval_status.expires_at:
                raise PaymentApprovalError(
                    "Stored admission expiry differs from the recorded approval expiry."
                )
            approval_admission = ApprovalAdmission(operation.fingerprint, adm_at, adm_exp)

        return ApprovalAdmissionProvenance(
            operation.fingerprint,
            attempt,
            approval_status,
            approval_admission,
        )

    def read_provenance(
        self,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
    ) -> ApprovalAdmissionProvenance:
        """Read required cross-table provenance or raise if the operation was never reserved."""
        provenance = self.find_provenance(journal, operation)
        if provenance is None:
            raise PaymentApprovalError(
                "No reservation or admission record exists for this operation."
            )
        return provenance

    def preview_admit(
        self,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
        signature: RequestSignatureSnapshot,
        *,
        now: int,
        expected_target_uri: str,
        method: str,
        target_uri: str,
        content_type: str,
        content_digest: str,
        content_encoding: str | None,
        body: bytes,
    ) -> ApprovalAdmissionPreview:
        """Preview admit() in one lock-free SELECT without mutating state."""
        if not isinstance(journal, PaymentAttemptJournal):
            raise PaymentApprovalError("A trusted journal and clock callable are required.")
        validate_signed_checkout(
            operation, signature, expected_target_uri=expected_target_uri, method=method,
            target_uri=target_uri, content_type=content_type, content_digest=content_digest,
            content_encoding=content_encoding, body=body,
        )
        if self.path.resolve(strict=True) != journal.path.resolve(strict=True):
            raise PaymentApprovalError("Atomic admission requires the same resolved SQLite file.")
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT
                    app.fingerprint AS app_fingerprint,
                    app.expires_at AS app_expires_at,
                    app.revoked AS app_revoked,
                    att.tenant_id AS att_tenant_id,
                    att.operation_id AS att_operation_id,
                    att.approval_id AS att_approval_id,
                    att.provider AS att_provider,
                    att.provider_account AS att_provider_account,
                    att.idempotency_key AS att_idempotency_key,
                    att.fingerprint AS att_fingerprint,
                    att.outcome AS att_outcome,
                    att.provider_reference AS att_provider_reference,
                    adm.fingerprint AS adm_fingerprint,
                    adm.admitted_at AS adm_admitted_at,
                    adm.expires_at AS adm_expires_at,
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
                LEFT JOIN payment_approvals AS app
                    ON app.tenant_id = ? AND app.approval_id = ?
                LEFT JOIN payment_attempts AS att
                    ON att.tenant_id = ? AND att.operation_id = ?
                LEFT JOIN payment_admissions AS adm
                    ON adm.tenant_id = ? AND adm.operation_id = ?""",
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
                    operation.approval_id,
                    operation.tenant_id,
                    operation.operation_id,
                    operation.tenant_id,
                    operation.operation_id,
                ),
            ).fetchone()
        assert row is not None
        if row["app_fingerprint"] is None:
            raise PaymentApprovalError("No recorded approval exists for this scope.")
        if row["app_fingerprint"] != operation.fingerprint:
            raise PaymentApprovalError("Approval differs from the bound operation.")
        app_expires_at, app_revoked = row["app_expires_at"], row["app_revoked"]
        if type(app_expires_at) is not int or not 0 < app_expires_at <= 2**63 - 1:
            raise PaymentApprovalError("Stored approval expiry is invalid.")
        if type(app_revoked) is not int or app_revoked not in (0, 1):
            raise PaymentApprovalError("Stored approval revocation state is invalid.")
        if app_revoked != 0:
            raise PaymentApprovalError("Approval is revoked.")
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise PaymentApprovalError("Clock must return a nonnegative signed-64-bit integer.")
        if now >= app_expires_at:
            raise PaymentApprovalError("Approval is expired.")
        approval_status = PaymentApprovalStatus(
            operation.fingerprint, app_expires_at, "active"
        )

        existing_admission: ApprovalAdmission | None = None
        if row["adm_fingerprint"] is not None:
            if row["adm_fingerprint"] != operation.fingerprint:
                raise PaymentApprovalError("Admission record differs from the bound operation.")
            adm_at, adm_exp = row["adm_admitted_at"], row["adm_expires_at"]
            if (
                type(adm_at) is not int
                or type(adm_exp) is not int
                or not 0 <= adm_at < adm_exp <= 2**63 - 1
            ):
                raise PaymentApprovalError("Stored admission times are invalid.")
            if row["att_tenant_id"] is None:
                raise PaymentApprovalError(
                    "Orphan admission record exists without a payment reservation."
                )
            if adm_exp != app_expires_at:
                raise PaymentApprovalError(
                    "Stored admission expiry differs from the recorded approval expiry."
                )
            existing_admission = ApprovalAdmission(operation.fingerprint, adm_at, adm_exp)

        if row["att_tenant_id"] is not None:
            att_row = {
                "fingerprint": row["att_fingerprint"],
                "approval_id": row["att_approval_id"],
                "provider": row["att_provider"],
                "provider_account": row["att_provider_account"],
                "idempotency_key": row["att_idempotency_key"],
                "outcome": row["att_outcome"],
                "provider_reference": row["att_provider_reference"],
            }
            journal._verify_row_binding(att_row, operation)
            existing_attempt = journal._attempt(att_row)
            if existing_attempt.provider_reference is None and existing_attempt.outcome != "unknown":
                raise AttemptConflict(
                    "Stored provider reference is invalid; reconciliation required."
                )
            return ApprovalAdmissionPreview(
                operation=operation,
                now=now,
                approval_status=approval_status,
                existing_attempt=existing_attempt,
                existing_admission=existing_admission,
                decision=DispatchDecision(existing_attempt, False),
                projected_admission=existing_admission,
                would_record_admission=False,
            )

        if row["approval_conflict"]:
            raise AttemptConflict("Approval already reserved by another operation.")
        if row["idempotency_conflict"]:
            raise AttemptConflict("Provider idempotency key already bound.")
        projected = ApprovalAdmission(operation.fingerprint, now, app_expires_at)
        return ApprovalAdmissionPreview(
            operation=operation,
            now=now,
            approval_status=approval_status,
            existing_attempt=None,
            existing_admission=None,
            decision=DispatchDecision(PaymentAttempt("unknown", None), True),
            projected_admission=projected,
            would_record_admission=True,
        )

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
