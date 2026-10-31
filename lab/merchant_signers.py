"""Opt-in local signer permission fencing, not Visa or signature verification."""

import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lab.checkout_admission import validate_signed_checkout
from lab.payment_approvals import ApprovalAdmission, PaymentApprovalStore
from lab.payment_attempts import (
    DispatchDecision,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP, RequestSignatureSnapshot, TimedRequestSignatureSnapshot,
    require_signature_time,
)

SignerPermissionState = Literal["active", "revoked"]
AdmissionProvenancePath = Literal[
    "direct_reservation", "approval_admission", "timed_signer_admission",
]


class MerchantSignerError(ValueError):
    """Trusted local signer configuration or permission cannot admit this request."""


@dataclass(frozen=True)
class MerchantSignerScope:
    """Trusted exact merchant route/key binding; constructing it is not authentication."""

    tenant_id: str
    merchant: str
    target_uri: str
    key_id: str

    def __post_init__(self) -> None:
        for value in (self.tenant_id, self.merchant, self.target_uri, self.key_id):
            if not isinstance(value, str) or not value or value != value.strip():
                raise MerchantSignerError("Canonical nonblank signer scope strings are required.")
        for value in (self.target_uri, self.key_id):
            if not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise MerchantSignerError("Route and key ID must be ASCII without controls.")

    @property
    def key(self) -> tuple[str, str, str, str]:
        return self.tenant_id, self.merchant, self.target_uri, self.key_id


@dataclass(frozen=True)
class MerchantSignerPermissionStatus:
    """Persisted local signer permission state, not signature proof or admission authority."""

    scope: MerchantSignerScope
    state: SignerPermissionState

    def __post_init__(self) -> None:
        if not isinstance(self.scope, MerchantSignerScope):
            raise MerchantSignerError("A trusted MerchantSignerScope is required.")
        if not isinstance(self.state, str) or self.state not in ("active", "revoked"):
            raise MerchantSignerError("Signer permission state must be active or revoked.")


@dataclass(frozen=True)
class TimedSignerAdmission:
    """Local timed-branch execution history, not signature proof or current permission."""

    fingerprint: str
    scope: MerchantSignerScope
    signature_label: str
    created: int
    expires: int
    admitted_at: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise MerchantSignerError(
                "Timed-admission fingerprint must be a 64-char hex SHA-256 digest."
            )
        if not isinstance(self.scope, MerchantSignerScope):
            raise MerchantSignerError("A trusted MerchantSignerScope is required.")
        if (
            not isinstance(self.signature_label, str)
            or re.fullmatch(r"[a-z*][a-z0-9_.*-]*", self.signature_label) is None
        ):
            raise MerchantSignerError("Stored timed-admission signature label is invalid.")
        if (
            any(type(value) is not int for value in (self.created, self.expires, self.admitted_at))
            or not 0 <= self.created <= self.admitted_at < self.expires <= MAX_SIGNATURE_TIMESTAMP
        ):
            raise MerchantSignerError("Stored timed-admission times are invalid.")


@dataclass(frozen=True)
class OperationAdmissionProvenance:
    """Single-snapshot local execution provenance across attempt, approval, and timed-signer tables."""

    fingerprint: str
    attempt: PaymentAttempt
    approval_admission: ApprovalAdmission | None
    timed_signer_admission: TimedSignerAdmission | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise MerchantSignerError("Provenance fingerprint must be a 64-char hex SHA-256 digest.")
        if not isinstance(self.attempt, PaymentAttempt):
            raise MerchantSignerError("Provenance requires a validated PaymentAttempt.")
        if (
            self.approval_admission is not None
            and not isinstance(self.approval_admission, ApprovalAdmission)
        ):
            raise MerchantSignerError("Provenance approval_admission must be ApprovalAdmission or None.")
        if (
            self.timed_signer_admission is not None
            and not isinstance(self.timed_signer_admission, TimedSignerAdmission)
        ):
            raise MerchantSignerError(
                "Provenance timed_signer_admission must be TimedSignerAdmission or None."
            )
        if (
            self.approval_admission is not None
            and self.approval_admission.fingerprint != self.fingerprint
        ):
            raise MerchantSignerError(
                "Approval admission fingerprint differs from provenance fingerprint."
            )
        if self.timed_signer_admission is not None:
            if self.approval_admission is None:
                raise MerchantSignerError(
                    "Orphan timed-admission record exists without an approval admission."
                )
            if self.timed_signer_admission.fingerprint != self.fingerprint:
                raise MerchantSignerError(
                    "Timed-admission fingerprint differs from provenance fingerprint."
                )
            if self.timed_signer_admission.admitted_at != self.approval_admission.admitted_at:
                raise MerchantSignerError(
                    "Timed-admission clock sample differs from approval admission."
                )
            if not 0 <= self.timed_signer_admission.admitted_at < self.approval_admission.expires_at:
                raise MerchantSignerError(
                    "Timed-admission clock sample is outside approval admission expiry."
                )

    @property
    def path(self) -> AdmissionProvenancePath:
        if self.timed_signer_admission is not None:
            return "timed_signer_admission"
        if self.approval_admission is not None:
            return "approval_admission"
        return "direct_reservation"


class MerchantSignerStore:
    """Trusted-operator allow/revoke metadata; never an agent tool or key directory.

    Bindings cannot be replaced or reactivated. Local revoke-first blocks this
    gate's admission, but cannot undo a prior reservation or fence an external send.
    Legacy approval/journal APIs bypass this opt-in boundary.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS merchant_signer_permissions (
                    tenant_id TEXT NOT NULL,
                    merchant TEXT NOT NULL,
                    target_uri TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    revoked INTEGER NOT NULL CHECK(revoked IN (0,1)),
                    PRIMARY KEY (tenant_id,merchant,target_uri,key_id)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS merchant_timed_admissions (
                    tenant_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    target_uri TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    signature_label TEXT NOT NULL,
                    created INTEGER NOT NULL CHECK(created>=0),
                    expires INTEGER NOT NULL CHECK(expires>created AND expires<=999999999999999),
                    admitted_at INTEGER NOT NULL CHECK(admitted_at>=created AND admitted_at<expires),
                    PRIMARY KEY (tenant_id,operation_id)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _require_scope(scope: MerchantSignerScope) -> None:
        if not isinstance(scope, MerchantSignerScope):
            raise MerchantSignerError("A trusted MerchantSignerScope is required.")

    @staticmethod
    def _require_operation(operation: PaymentOperation) -> None:
        if not isinstance(operation, PaymentOperation):
            raise MerchantSignerError("A trusted PaymentOperation is required.")

    @staticmethod
    def _permission(db: sqlite3.Connection, scope: MerchantSignerScope) -> sqlite3.Row:
        row = db.execute(
            "SELECT revoked FROM merchant_signer_permissions"
            " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?", scope.key,
        ).fetchone()
        if row is None:
            raise MerchantSignerError("No recorded signer permission exists for this scope.")
        return row

    def allow(self, scope: MerchantSignerScope) -> None:
        """Record trusted operator policy, not a verified key or consumer consent."""
        self._require_scope(scope)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM merchant_signer_permissions"
                " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?", scope.key,
            ).fetchone():
                raise MerchantSignerError("Signer permission already recorded; replacement is forbidden.")
            db.execute("INSERT INTO merchant_signer_permissions VALUES (?,?,?,?,0)", scope.key)

    def revoke(self, scope: MerchantSignerScope) -> None:
        """Irreversibly revoke an existing scope; repeated revocation is idempotent."""
        self._require_scope(scope)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._permission(db, scope)
            db.execute(
                "UPDATE merchant_signer_permissions SET revoked=1"
                " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?", scope.key,
            )

    def read_permission(self, scope: MerchantSignerScope) -> MerchantSignerPermissionStatus | None:
        """Read local signer permission state without verifying signatures or granting authority."""
        self._require_scope(scope)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT revoked FROM merchant_signer_permissions"
                " WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?",
                scope.key,
            ).fetchone()
        if row is None:
            return None
        revoked = row["revoked"]
        if type(revoked) is not int or revoked not in (0, 1):
            raise MerchantSignerError("Stored signer permission revocation state is invalid.")
        return MerchantSignerPermissionStatus(scope, "revoked" if revoked else "active")

    def find_timed_admission(self, operation: PaymentOperation) -> TimedSignerAdmission | None:
        """Read first timed-branch history or return None if absent, without new authority."""
        self._require_operation(operation)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT * FROM merchant_timed_admissions WHERE tenant_id=? AND operation_id=?",
                (operation.tenant_id, operation.operation_id),
            ).fetchone()
        if row is None:
            return None
        if row["fingerprint"] != operation.fingerprint:
            raise MerchantSignerError("Timed-admission record differs from the bound operation.")
        scope = MerchantSignerScope(
            operation.tenant_id, operation.checkout.merchant, row["target_uri"], row["key_id"],
        )
        label = row["signature_label"]
        if not isinstance(label, str) or re.fullmatch(r"[a-z*][a-z0-9_.*-]*", label) is None:
            raise MerchantSignerError("Stored timed-admission signature label is invalid.")
        created, expires, admitted_at = row["created"], row["expires"], row["admitted_at"]
        if (any(type(value) is not int for value in (created, expires, admitted_at))
                or not 0 <= created <= admitted_at < expires <= MAX_SIGNATURE_TIMESTAMP):
            raise MerchantSignerError("Stored timed-admission times are invalid.")
        return TimedSignerAdmission(operation.fingerprint, scope, label, created, expires, admitted_at)

    def read_timed_admission(self, operation: PaymentOperation) -> TimedSignerAdmission:
        """Read first timed-branch history without checking or granting current authority."""
        admission = self.find_timed_admission(operation)
        if admission is None:
            raise MerchantSignerError("No first timed-admission record exists for this operation.")
        return admission

    def find_provenance(
        self,
        approvals: PaymentApprovalStore,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
    ) -> OperationAdmissionProvenance | None:
        """Read a single-query cross-table provenance snapshot without locks or new authority."""
        if (
            not isinstance(approvals, PaymentApprovalStore)
            or not isinstance(journal, PaymentAttemptJournal)
            or not isinstance(operation, PaymentOperation)
        ):
            raise MerchantSignerError("Trusted stores and PaymentOperation are required.")
        if not (
            self.path.resolve(strict=True)
            == approvals.path.resolve(strict=True)
            == journal.path.resolve(strict=True)
        ):
            raise MerchantSignerError(
                "Cross-table provenance inspection requires the same resolved SQLite file."
            )
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT"
                " att.approval_id AS att_approval_id,"
                " att.provider AS att_provider,"
                " att.provider_account AS att_provider_account,"
                " att.idempotency_key AS att_idempotency_key,"
                " att.fingerprint AS att_fingerprint,"
                " att.outcome AS att_outcome,"
                " att.provider_reference AS att_provider_reference,"
                " adm.fingerprint AS adm_fingerprint,"
                " adm.admitted_at AS adm_admitted_at,"
                " adm.expires_at AS adm_expires_at,"
                " tmd.fingerprint AS tmd_fingerprint,"
                " tmd.target_uri AS tmd_target_uri,"
                " tmd.key_id AS tmd_key_id,"
                " tmd.signature_label AS tmd_signature_label,"
                " tmd.created AS tmd_created,"
                " tmd.expires AS tmd_expires,"
                " tmd.admitted_at AS tmd_admitted_at"
                " FROM (SELECT ? AS tenant_id, ? AS operation_id) k"
                " LEFT JOIN payment_attempts att USING (tenant_id, operation_id)"
                " LEFT JOIN payment_admissions adm USING (tenant_id, operation_id)"
                " LEFT JOIN merchant_timed_admissions tmd USING (tenant_id, operation_id)",
                (operation.tenant_id, operation.operation_id),
            ).fetchone()
        assert row is not None
        att_fp = row["att_fingerprint"]
        adm_fp = row["adm_fingerprint"]
        tmd_fp = row["tmd_fingerprint"]
        if att_fp is None and adm_fp is None and tmd_fp is None:
            return None
        for fp, label in (
            (att_fp, "Attempt"),
            (adm_fp, "Admission"),
            (tmd_fp, "Timed-admission"),
        ):
            if fp is not None and fp != operation.fingerprint:
                raise MerchantSignerError(f"{label} record differs from the bound operation.")
        if att_fp is None:
            raise MerchantSignerError(
                "Orphan admission record exists without a reserved payment attempt."
            )
        if (
            row["att_approval_id"] != operation.approval_id
            or row["att_provider"] != operation.provider
            or row["att_provider_account"] != operation.provider_account
            or row["att_idempotency_key"] != operation.idempotency_key
        ):
            raise MerchantSignerError("Attempt record differs from the bound operation.")
        if tmd_fp is not None and adm_fp is None:
            raise MerchantSignerError(
                "Orphan timed-admission record exists without an approval admission."
            )

        outcome = row["att_outcome"]
        if not isinstance(outcome, str) or outcome not in ("unknown", "succeeded", "failed"):
            raise MerchantSignerError("Stored attempt outcome is invalid; reconciliation required.")
        provider_reference = row["att_provider_reference"]
        if provider_reference is None:
            if outcome != "unknown":
                raise MerchantSignerError(
                    "Stored attempt provider reference is invalid; reconciliation required."
                )
        elif not isinstance(provider_reference, str) or not provider_reference.strip():
            raise MerchantSignerError(
                "Stored attempt provider reference is invalid; reconciliation required."
            )
        attempt = PaymentAttempt(outcome, provider_reference)

        approval_admission: ApprovalAdmission | None = None
        if adm_fp is not None:
            adm_admitted_at, adm_expires_at = row["adm_admitted_at"], row["adm_expires_at"]
            if (
                type(adm_admitted_at) is not int
                or type(adm_expires_at) is not int
                or not 0 <= adm_admitted_at < adm_expires_at <= 2**63 - 1
            ):
                raise MerchantSignerError("Stored approval admission times are invalid.")
            approval_admission = ApprovalAdmission(
                operation.fingerprint, adm_admitted_at, adm_expires_at
            )

        timed_signer_admission: TimedSignerAdmission | None = None
        if tmd_fp is not None:
            scope = MerchantSignerScope(
                operation.tenant_id,
                operation.checkout.merchant,
                row["tmd_target_uri"],
                row["tmd_key_id"],
            )
            sig_label = row["tmd_signature_label"]
            if not isinstance(sig_label, str) or re.fullmatch(r"[a-z*][a-z0-9_.*-]*", sig_label) is None:
                raise MerchantSignerError("Stored timed-admission signature label is invalid.")
            created, expires, tmd_admitted_at = (
                row["tmd_created"],
                row["tmd_expires"],
                row["tmd_admitted_at"],
            )
            if (
                any(type(value) is not int for value in (created, expires, tmd_admitted_at))
                or not 0 <= created <= tmd_admitted_at < expires <= MAX_SIGNATURE_TIMESTAMP
            ):
                raise MerchantSignerError("Stored timed-admission times are invalid.")
            timed_signer_admission = TimedSignerAdmission(
                operation.fingerprint, scope, sig_label, created, expires, tmd_admitted_at,
            )

        return OperationAdmissionProvenance(
            operation.fingerprint,
            attempt,
            approval_admission,
            timed_signer_admission,
        )

    def read_provenance(
        self,
        approvals: PaymentApprovalStore,
        journal: PaymentAttemptJournal,
        operation: PaymentOperation,
    ) -> OperationAdmissionProvenance:
        """Read required cross-table provenance or raise if the operation was never reserved."""
        provenance = self.find_provenance(approvals, journal, operation)
        if provenance is None:
            raise MerchantSignerError(
                "No reservation or admission record exists for this operation."
            )
        return provenance

    def admit(
        self, scope: MerchantSignerScope, approvals: PaymentApprovalStore,
        journal: PaymentAttemptJournal, operation: PaymentOperation,
        signature: RequestSignatureSnapshot | TimedRequestSignatureSnapshot, *,
        clock: Callable[[], int],
        method: str, target_uri: str, content_type: str, content_digest: str,
        content_encoding: str | None, body: bytes,
    ) -> DispatchDecision:
        """Fence local signer permission and approval/reservation in one transaction.

        The adapter has already verified the full signature and stable keyid/key
        provenance. Timed input checks its window at the same post-lock sample as
        approval; bare input retains no signature-time check. No nonce is consumed
        or local policy authenticated. Approval history proves neither signer nor
        timed-signature admission. Only a new timed reservation records local timed
        history; retries and legacy attempts are never backfilled.
        """
        self._require_scope(scope)
        timed = signature if isinstance(signature, TimedRequestSignatureSnapshot) else None
        snapshot = timed.signature if timed is not None else signature
        if (not isinstance(approvals, PaymentApprovalStore)
                or not isinstance(journal, PaymentAttemptJournal)
                or not isinstance(operation, PaymentOperation)
                or not isinstance(snapshot, RequestSignatureSnapshot) or not callable(clock)):
            raise MerchantSignerError("Trusted stores, operation, signature and clock are required.")
        if (scope.tenant_id != operation.tenant_id or scope.merchant != operation.checkout.merchant
                or scope.key_id != snapshot.key_id):
            raise MerchantSignerError("Signer scope differs from operation or verified key ID.")
        validate_signed_checkout(
            operation, snapshot, expected_target_uri=scope.target_uri, method=method,
            target_uri=target_uri, content_type=content_type, content_digest=content_digest,
            content_encoding=content_encoding, body=body,
        )
        if not (self.path.resolve(strict=True) == approvals.path.resolve(strict=True)
                == journal.path.resolve(strict=True)):
            raise MerchantSignerError("Atomic signer admission requires the same resolved SQLite file.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if self._permission(db, scope)["revoked"] != 0:
                raise MerchantSignerError("Signer permission is revoked.")
            admission_clock = clock
            admitted_at: int | None = None
            if timed is not None:
                def checked_clock() -> int:
                    nonlocal admitted_at
                    now = clock()
                    require_signature_time(timed, now=now)
                    admitted_at = now
                    return now
                admission_clock = checked_clock
            decision = approvals._admit_in_transaction(db, journal, operation, clock=admission_clock)
            if timed is not None and decision.dispatch_allowed:
                if admitted_at is None:
                    raise MerchantSignerError("Timed admission did not sample its trusted clock.")
                db.execute(
                    "INSERT INTO merchant_timed_admissions"
                    " (tenant_id,operation_id,fingerprint,target_uri,key_id,signature_label,"
                    " created,expires,admitted_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (operation.tenant_id, operation.operation_id, operation.fingerprint,
                     scope.target_uri, scope.key_id, snapshot.signature_label,
                     timed.created, timed.expires, admitted_at),
                )
        return decision
