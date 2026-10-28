"""Offline verified snapshot receipt; not a payment or completed-work queue."""

import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from lab.stripe_delivery import verify_stripe_delivery


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


@dataclass(frozen=True)
class InboxDecision:
    receipt: InboxReceipt
    first_seen: bool
    body_matches_first: bool


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
    """Commit a minimal verified receipt; every stored row still needs readback.

    Callers own endpoint-secret/account mapping and eventual worker/ACK policy.
    No claim, processed flag, payment association or downstream effect is granted.
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

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _receipt(row: sqlite3.Row) -> InboxReceipt:
        return InboxReceipt(
            row["event_id"], row["event_type"],
            row["provider_reference"], row["payload_sha256"],
        )

    def record(
        self, scope: StripeInboxScope, body: bytes, signature_header: str,
        endpoint_secret: str, *, now: int, tolerance: int = 300,
    ) -> InboxDecision:
        """Verify and commit before returning, without interpreting a payment outcome."""
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

    def pending(self, scope: StripeInboxScope, *, limit: int = 100) -> tuple[InboxReceipt, ...]:
        """Enumerate readback hints in local receipt order, not provider event order."""
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
