"""Opt-in local signer permission fencing, not Visa or signature verification."""

import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from lab.checkout_admission import validate_signed_checkout
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import DispatchDecision, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_SIGNATURE_TIMESTAMP, RequestSignatureSnapshot, TimedRequestSignatureSnapshot,
    require_signature_time,
)


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
class TimedSignerAdmission:
    """Local timed-branch execution history, not signature proof or current permission."""

    fingerprint: str
    scope: MerchantSignerScope
    signature_label: str
    created: int
    expires: int
    admitted_at: int


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

    def read_timed_admission(self, operation: PaymentOperation) -> TimedSignerAdmission:
        """Read first timed-branch history without checking or granting current authority."""
        if not isinstance(operation, PaymentOperation):
            raise MerchantSignerError("A trusted PaymentOperation is required.")
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT * FROM merchant_timed_admissions WHERE tenant_id=? AND operation_id=?",
                (operation.tenant_id, operation.operation_id),
            ).fetchone()
        if row is None:
            raise MerchantSignerError("No first timed-admission record exists for this operation.")
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
