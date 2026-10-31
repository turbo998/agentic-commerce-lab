"""Offline verified receipts and local readback claims, never payment authority."""

import json
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn

from lab.stripe_delivery import _require_delivery_time, verify_stripe_delivery

ClaimState = Literal["active", "handled"]


class StripeInboxError(ValueError):
    """A snapshot, trusted scope, or persisted identity violates local policy."""


@dataclass(frozen=True)
class StripeInboxScope:
    """Trusted endpoint configuration, never request-selected account routing."""

    tenant_id: str
    endpoint_id: str
    provider_account: str
    livemode: bool

    def __post_init__(self) -> None:
        for value in (self.tenant_id, self.endpoint_id, self.provider_account):
            if not isinstance(value, str) or not value.strip():
                raise StripeInboxError("Trusted tenant, endpoint and account are required.")
        if type(self.livemode) is not bool:
            raise StripeInboxError("Scope livemode must be boolean.")

    @property
    def key(self) -> tuple[str, str, str, int]:
        return self.tenant_id, self.endpoint_id, self.provider_account, int(self.livemode)


@dataclass(frozen=True)
class InboxReceipt:
    event_id: str
    event_type: str
    provider_reference: str
    payload_sha256: str
    requires_readback: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", self.event_id) is None:
            raise StripeInboxError("Stored receipt Event ID is invalid.")
        if (
            not isinstance(self.event_type, str)
            or self.event_type not in ("payment_intent.succeeded", "payment_intent.payment_failed")
        ):
            raise StripeInboxError("Stored receipt event type is invalid.")
        if (
            not isinstance(self.provider_reference, str)
            or re.fullmatch(r"pi_[A-Za-z0-9_]+", self.provider_reference) is None
        ):
            raise StripeInboxError("Stored receipt object reference is invalid.")
        if (
            not isinstance(self.payload_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256) is None
        ):
            raise StripeInboxError("Stored receipt payload digest is invalid.")
        if type(self.requires_readback) is not bool:
            raise StripeInboxError("Receipt requires_readback flag must be boolean.")


@dataclass(frozen=True)
class InboxDecision:
    receipt: InboxReceipt
    first_seen: bool
    body_matches_first: bool

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, InboxReceipt):
            raise StripeInboxError("An inbox decision requires a persisted receipt.")
        if type(self.first_seen) is not bool or type(self.body_matches_first) is not bool:
            raise StripeInboxError("Inbox decision flags must be boolean.")


def _require_worker_id(worker_id: str) -> None:
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise StripeInboxError("A trusted nonblank worker ID is required.")


@dataclass(frozen=True)
class ReadbackClaim:
    """Local coordination handle, not worker authentication or payment permission."""

    scope: StripeInboxScope
    receipt: InboxReceipt
    worker_id: str
    generation: int

    def __post_init__(self) -> None:
        if not isinstance(self.scope, StripeInboxScope) or not isinstance(self.receipt, InboxReceipt):
            raise StripeInboxError("A claim needs a trusted scope and persisted receipt.")
        _require_worker_id(self.worker_id)
        if type(self.generation) is not int or not 1 <= self.generation <= 2**63 - 1:
            raise StripeInboxError("Generation must be a positive signed-64-bit integer.")


@dataclass(frozen=True)
class ReadbackClaimStatus:
    """Persisted local claim state, not worker liveness or a payment outcome."""

    claim: ReadbackClaim
    state: ClaimState

    def __post_init__(self) -> None:
        if not isinstance(self.claim, ReadbackClaim):
            raise StripeInboxError("A persisted ReadbackClaim is required.")
        if not isinstance(self.state, str) or self.state not in ("active", "handled"):
            raise StripeInboxError("Claim state must be active or handled.")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StripeInboxError("Duplicate JSON object key.")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise StripeInboxError("Nonstandard JSON constant.")


class StripeEventInbox:
    """Persist verified hints and fence local claim completion, not payment results.

    Callers own endpoint mapping, authenticated workers, explicit recovery,
    actual readback and ACK policy. No remote request or economic effect is fenced.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS stripe_event_inbox (
                    tenant_id TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    provider_account TEXT NOT NULL,
                    livemode INTEGER NOT NULL CHECK(livemode IN (0,1)),
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    provider_reference TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (tenant_id,endpoint_id,provider_account,livemode,event_id)
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS stripe_readback_claims (
                    tenant_id TEXT NOT NULL,
                    endpoint_id TEXT NOT NULL,
                    provider_account TEXT NOT NULL,
                    livemode INTEGER NOT NULL CHECK(livemode IN (0,1)),
                    event_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    generation INTEGER NOT NULL CHECK(generation>0),
                    state TEXT NOT NULL CHECK(state IN ('active','handled')),
                    PRIMARY KEY (tenant_id,endpoint_id,provider_account,livemode,event_id),
                    FOREIGN KEY (tenant_id,endpoint_id,provider_account,livemode,event_id)
                        REFERENCES stripe_event_inbox
                        (tenant_id,endpoint_id,provider_account,livemode,event_id)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _receipt(row: sqlite3.Row) -> InboxReceipt:
        return InboxReceipt(
            row["event_id"], row["event_type"],
            row["provider_reference"], row["payload_sha256"],
        )

    def record(
        self, scope: StripeInboxScope, body: bytes, signature_header: str,
        endpoint_secret: str | tuple[str, ...], *, now: int, tolerance: int = 300,
    ) -> InboxDecision:
        """Verify and commit without interpreting a payment outcome.

        A secret tuple is a trusted active-key snapshot for this scope, never a
        header-selected keyring. Rotation does not change receipt identity.
        Fixed now checks ingress only, not time after waiting for the writer.
        """
        return self._record(
            scope, body, signature_header, endpoint_secret, now=now,
            tolerance=tolerance, admission_clock=None,
        )

    def record_with_clock(
        self, scope: StripeInboxScope, body: bytes, signature_header: str,
        endpoint_secret: str | tuple[str, ...], *,
        clock: Callable[[], int], tolerance: int = 300,
    ) -> InboxDecision:
        """Check ingress, then recheck the signed timestamp after the write lock.

        Successful/duplicate paths sample twice; HMAC and JSON run only at ingress.
        The callback must return fresh trusted time at each boundary. This does
        not expire durable work, refresh secret configuration or prove a payment.
        """
        if not isinstance(scope, StripeInboxScope) or not callable(clock):
            raise StripeInboxError("A trusted scope and clock callable are required.")
        return self._record(
            scope, body, signature_header, endpoint_secret, now=clock(),
            tolerance=tolerance, admission_clock=clock,
        )

    def _record(
        self, scope: StripeInboxScope, body: bytes, signature_header: str,
        endpoint_secret: str | tuple[str, ...], *, now: int, tolerance: int,
        admission_clock: Callable[[], int] | None,
    ) -> InboxDecision:
        if not isinstance(scope, StripeInboxScope):
            raise StripeInboxError("A trusted StripeInboxScope is required.")
        verified = verify_stripe_delivery(
            body, signature_header, endpoint_secret, now=now, tolerance=tolerance,
        )
        try:
            event = json.loads(
                body.decode("utf-8"), object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StripeInboxError("A UTF-8 snapshot JSON object is required.") from error
        if not isinstance(event, dict) or event.get("object") != "event":
            raise StripeInboxError("Only snapshot Event objects are supported.")
        if event.get("livemode") is not scope.livemode:
            raise StripeInboxError("Event mode differs from trusted endpoint scope.")
        if event.get("account") is not None or event.get("context") is not None:
            raise StripeInboxError("Connect and organization contexts are unsupported.")
        event_id, event_type = event.get("id"), event.get("type")
        if not isinstance(event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", event_id) is None:
            raise StripeInboxError("A snapshot Event ID is required.")
        if event_type not in ("payment_intent.succeeded", "payment_intent.payment_failed"):
            raise StripeInboxError("This reference only accepts two PaymentIntent event types.")
        data = event.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("object"), dict):
            raise StripeInboxError("A PaymentIntent snapshot is required.")
        intent = data["object"]
        reference = intent.get("id")
        if (
            intent.get("object") != "payment_intent"
            or intent.get("livemode") is not scope.livemode
            or not isinstance(reference, str)
            or re.fullmatch(r"pi_[A-Za-z0-9_]+", reference) is None
        ):
            raise StripeInboxError("Snapshot object reference or mode is invalid.")

        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if admission_clock is not None:
                _require_delivery_time(verified.timestamp, now=admission_clock(), tolerance=tolerance)
            previous = db.execute(
                "SELECT * FROM stripe_event_inbox WHERE tenant_id=? AND endpoint_id=?"
                " AND provider_account=? AND livemode=? AND event_id=?",
                (*scope.key, event_id),
            ).fetchone()
            if previous is not None:
                receipt = self._receipt(previous)
                if receipt.event_type != event_type or receipt.provider_reference != reference:
                    raise StripeInboxError("Event ID has conflicting type or object bindings.")
                return InboxDecision(
                    receipt, False, receipt.payload_sha256 == verified.payload_sha256,
                )
            db.execute(
                "INSERT INTO stripe_event_inbox "
                "(tenant_id,endpoint_id,provider_account,livemode,event_id,"
                "event_type,provider_reference,payload_sha256) VALUES (?,?,?,?,?,?,?,?)",
                (*scope.key, event_id, event_type, reference, verified.payload_sha256),
            )
            return InboxDecision(
                InboxReceipt(event_id, event_type, reference, verified.payload_sha256),
                True, True,
            )

    @staticmethod
    def _require_event_lookup(
        scope: StripeInboxScope, event_id: str,
    ) -> tuple[str, str, str, int, str]:
        if not isinstance(scope, StripeInboxScope):
            raise StripeInboxError("A trusted StripeInboxScope is required.")
        if not isinstance(event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", event_id) is None:
            raise StripeInboxError("A snapshot Event ID is required.")
        return (*scope.key, event_id)

    def read_receipt(self, scope: StripeInboxScope, event_id: str) -> InboxReceipt | None:
        """Read original scoped history, not authenticate or admit a delivery.

        Absence is not a payment result. Presence grants no ACK, worker or payment
        authority and never substitutes for the ingress verification pipeline.
        """
        key = self._require_event_lookup(scope, event_id)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT * FROM stripe_event_inbox WHERE tenant_id=? AND endpoint_id=?"
                " AND provider_account=? AND livemode=? AND event_id=?",
                key,
            ).fetchone()
            return None if row is None else self._receipt(row)

    def read_claim(
        self, scope: StripeInboxScope, event_id: str,
    ) -> ReadbackClaimStatus | None:
        """Read scoped local claim state without claiming, handing off or completing.

        Absence means only that no claim row exists for this scoped Event ID.
        An active or handled record is local coordination history, not worker
        liveness, authenticated provider readback or a payment outcome.
        """
        key = self._require_event_lookup(scope, event_id)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT c.event_id,i.event_type,i.provider_reference,i.payload_sha256,"
                "c.worker_id,c.generation,c.state FROM stripe_readback_claims c"
                " LEFT JOIN stripe_event_inbox i"
                " USING(tenant_id,endpoint_id,provider_account,livemode,event_id)"
                " WHERE c.tenant_id=? AND c.endpoint_id=? AND c.provider_account=?"
                " AND c.livemode=? AND c.event_id=?",
                key,
            ).fetchone()
            if row is None:
                return None
            claim = ReadbackClaim(
                scope, self._receipt(row), row["worker_id"], row["generation"],
            )
            return ReadbackClaimStatus(claim, row["state"])

    def pending(self, scope: StripeInboxScope, *, limit: int = 100) -> tuple[InboxReceipt, ...]:
        """Enumerate all receipts, regardless of claim state, in local receipt order."""
        if not isinstance(scope, StripeInboxScope):
            raise StripeInboxError("A trusted StripeInboxScope is required.")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise StripeInboxError("Pending limit must be an integer from 1 to 1000.")
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT * FROM stripe_event_inbox WHERE tenant_id=? AND endpoint_id=?"
                " AND provider_account=? AND livemode=? ORDER BY rowid LIMIT ?",
                (*scope.key, limit),
            ).fetchall()
            return tuple(self._receipt(row) for row in rows)

    def claim_next(self, scope: StripeInboxScope, worker_id: str) -> ReadbackClaim | None:
        """Claim one never-claimed hint; None means no available work, not an error."""
        if not isinstance(scope, StripeInboxScope):
            raise StripeInboxError("A trusted StripeInboxScope is required.")
        _require_worker_id(worker_id)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT i.* FROM stripe_event_inbox i LEFT JOIN stripe_readback_claims c"
                " USING(tenant_id,endpoint_id,provider_account,livemode,event_id)"
                " WHERE i.tenant_id=? AND i.endpoint_id=? AND i.provider_account=?"
                " AND i.livemode=? AND c.event_id IS NULL ORDER BY i.rowid LIMIT 1",
                scope.key,
            ).fetchone()
            if row is None:
                return None
            receipt = self._receipt(row)
            db.execute(
                "INSERT INTO stripe_readback_claims"
                " (tenant_id,endpoint_id,provider_account,livemode,event_id,"
                "worker_id,generation,state) VALUES (?,?,?,?,?,?,1,'active')",
                (*scope.key, receipt.event_id, worker_id),
            )
            return ReadbackClaim(scope, receipt, worker_id, 1)

    def _current_claim(self, db: sqlite3.Connection, claim: ReadbackClaim) -> sqlite3.Row:
        if not isinstance(claim, ReadbackClaim):
            raise StripeInboxError("A persisted ReadbackClaim is required.")
        row = db.execute(
            "SELECT i.*,c.worker_id,c.generation,c.state FROM stripe_event_inbox i"
            " JOIN stripe_readback_claims c"
            " USING(tenant_id,endpoint_id,provider_account,livemode,event_id)"
            " WHERE i.tenant_id=? AND i.endpoint_id=? AND i.provider_account=?"
            " AND i.livemode=? AND i.event_id=?",
            (*claim.scope.key, claim.receipt.event_id),
        ).fetchone()
        if (
            row is None or row["worker_id"] != claim.worker_id
            or row["generation"] != claim.generation or self._receipt(row) != claim.receipt
        ):
            raise StripeInboxError("Readback claim binding is stale or invalid.")
        if row["state"] not in ("active", "handled"):
            raise StripeInboxError("Stored readback claim state is invalid.")
        return row

    def handoff(self, claim: ReadbackClaim, worker_id: str) -> ReadbackClaim:
        """Apply a trusted controller's recovery decision; never infer expiry."""
        _require_worker_id(worker_id)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = self._current_claim(db, claim)
            if row["state"] != "active":
                raise StripeInboxError("Handled hints cannot be handed off.")
            if claim.generation == 2**63 - 1:
                raise StripeInboxError("Readback generation is exhausted.")
            generation = claim.generation + 1
            db.execute(
                "UPDATE stripe_readback_claims SET worker_id=?,generation=?"
                " WHERE tenant_id=? AND endpoint_id=? AND provider_account=?"
                " AND livemode=? AND event_id=?",
                (worker_id, generation, *claim.scope.key, claim.receipt.event_id),
            )
            return ReadbackClaim(claim.scope, claim.receipt, worker_id, generation)

    def finish_readback(self, claim: ReadbackClaim) -> None:
        """Record trusted local hint handling, not authenticated provider/payment facts."""
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._finish_in_transaction(db, claim)

    def _finish_in_transaction(self, db: sqlite3.Connection, claim: ReadbackClaim) -> None:
        """Participate in a caller-owned transaction without committing it."""
        if not db.in_transaction:
            raise StripeInboxError("Completion requires an active transaction.")
        row = self._current_claim(db, claim)
        if row["state"] == "handled":
            return
        db.execute(
            "UPDATE stripe_readback_claims SET state='handled'"
            " WHERE tenant_id=? AND endpoint_id=? AND provider_account=?"
            " AND livemode=? AND event_id=?",
            (*claim.scope.key, claim.receipt.event_id),
        )

    def active_claims(
        self, scope: StripeInboxScope, *, limit: int = 100,
    ) -> tuple[ReadbackClaim, ...]:
        """List recovery hints, not live lease validity or permission to write externally."""
        if not isinstance(scope, StripeInboxScope):
            raise StripeInboxError("A trusted StripeInboxScope is required.")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise StripeInboxError("Active-claim limit must be an integer from 1 to 1000.")
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT c.event_id,i.event_type,i.provider_reference,i.payload_sha256,"
                "c.worker_id,c.generation FROM stripe_readback_claims c"
                " LEFT JOIN stripe_event_inbox i"
                " USING(tenant_id,endpoint_id,provider_account,livemode,event_id)"
                " WHERE c.tenant_id=? AND c.endpoint_id=? AND c.provider_account=?"
                " AND c.livemode=? AND c.state='active' ORDER BY i.rowid, c.rowid LIMIT ?",
                (*scope.key, limit),
            ).fetchall()
            return tuple(
                ReadbackClaim(scope, self._receipt(row), row["worker_id"], row["generation"])
                for row in rows
            )
