"""Atomic local acceptance of trusted readbacks, not provider transactions."""

from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
import re

from lab.payment_attempts import AttemptConflict, PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import (
    InboxReceipt,
    ReadbackClaim,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxScope,
)
from lab.stripe_observation import validate_stripe_intent


class StripeReadbackError(ValueError):
    """The configured stores, active claim or operation do not share a binding."""


@dataclass(frozen=True)
class StripeReadbackProvenance:
    """Single-snapshot local readback provenance, never remote provider authority."""

    scope: StripeInboxScope
    event_id: str
    fingerprint: str
    attempt: PaymentAttempt | None
    receipt: InboxReceipt | None
    claim_status: ReadbackClaimStatus | None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, StripeInboxScope):
            raise StripeReadbackError("A trusted StripeInboxScope is required.")
        if not isinstance(self.event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", self.event_id) is None:
            raise StripeReadbackError("A snapshot Event ID is required.")
        if not isinstance(self.fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None:
            raise StripeReadbackError("Provenance operation fingerprint is invalid.")
        if self.attempt is not None and not isinstance(self.attempt, PaymentAttempt):
            raise StripeReadbackError("Provenance attempt must be a PaymentAttempt or None.")
        if self.receipt is not None and not isinstance(self.receipt, InboxReceipt):
            raise StripeReadbackError("Provenance receipt must be an InboxReceipt or None.")
        if self.claim_status is not None and not isinstance(self.claim_status, ReadbackClaimStatus):
            raise StripeReadbackError("Provenance claim status must be a ReadbackClaimStatus or None.")
        if self.attempt is None and self.receipt is None:
            raise StripeReadbackError(
                "Readback provenance requires a reserved attempt or a recorded receipt."
            )
        if self.receipt is not None and self.receipt.event_id != self.event_id:
            raise StripeReadbackError("Receipt Event ID differs from the provenance lookup key.")
        if self.claim_status is not None and self.receipt is None:
            raise StripeReadbackError("Readback claim status cannot exist without a recorded receipt.")
        if self.claim_status is not None and (
            self.claim_status.claim.scope != self.scope
            or self.claim_status.claim.receipt != self.receipt
        ):
            raise StripeReadbackError(
                "Readback claim status does not match provenance scope or receipt."
            )
        if (
            self.attempt is not None
            and self.attempt.provider_reference is not None
            and self.receipt is not None
            and self.attempt.provider_reference != self.receipt.provider_reference
        ):
            raise StripeReadbackError(
                "Receipt differs from the trusted PaymentIntent association."
            )


def find_stripe_readback_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
) -> StripeReadbackProvenance | None:
    """Read coupled attempt, receipt and claim state in one lock-free snapshot.

    Returns None only when neither the payment attempt nor the scoped webhook
    receipt exists. Fails closed on store mismatch, scope/operation drift,
    corrupted columns, orphan claim rows, or conflicting PaymentIntent IDs.
    """
    if (
        not isinstance(inbox, StripeEventInbox)
        or not isinstance(journal, PaymentAttemptJournal)
        or not isinstance(scope, StripeInboxScope)
        or not isinstance(operation, PaymentOperation)
    ):
        raise StripeReadbackError(
            "Trusted inbox, journal, inbox scope and payment operation are required."
        )
    key = inbox._require_event_lookup(scope, event_id)
    if (
        scope.tenant_id != operation.tenant_id
        or scope.provider_account != operation.provider_account
        or operation.provider != ("stripe:live" if scope.livemode else "stripe:test")
    ):
        raise StripeReadbackError("Inbox scope differs from the bound payment operation.")
    if inbox.path.resolve(strict=True) != journal.path.resolve(strict=True):
        raise StripeReadbackError("Readback provenance requires the same resolved SQLite file.")
    with closing(inbox._connect()) as db:
        row = db.execute(
            "SELECT "
            "att.fingerprint AS att_fingerprint, "
            "att.approval_id AS att_approval_id, "
            "att.provider AS att_provider, "
            "att.provider_account AS att_provider_account, "
            "att.idempotency_key AS att_idempotency_key, "
            "att.outcome AS att_outcome, "
            "att.provider_reference AS att_provider_reference, "
            "i.event_id AS i_event_id, "
            "i.event_type AS i_event_type, "
            "i.provider_reference AS i_provider_reference, "
            "i.payload_sha256 AS i_payload_sha256, "
            "c.event_id AS c_event_id, "
            "c.worker_id AS c_worker_id, "
            "c.generation AS c_generation, "
            "c.state AS c_state "
            "FROM (SELECT 1) "
            "LEFT JOIN payment_attempts att "
            "ON att.tenant_id=? AND att.operation_id=? "
            "LEFT JOIN stripe_event_inbox i "
            "ON i.tenant_id=? AND i.endpoint_id=? "
            "AND i.provider_account=? AND i.livemode=? AND i.event_id=? "
            "LEFT JOIN stripe_readback_claims c "
            "ON c.tenant_id=? AND c.endpoint_id=? "
            "AND c.provider_account=? AND c.livemode=? AND c.event_id=?",
            (operation.tenant_id, operation.operation_id, *key, *key),
        ).fetchone()
    if row is None or (
        row["att_fingerprint"] is None
        and row["i_event_id"] is None
        and row["c_event_id"] is None
    ):
        return None

    attempt: PaymentAttempt | None = None
    if row["att_fingerprint"] is not None:
        if (
            row["att_fingerprint"] != operation.fingerprint
            or row["att_approval_id"] != operation.approval_id
            or row["att_provider"] != operation.provider
            or row["att_provider_account"] != operation.provider_account
            or row["att_idempotency_key"] != operation.idempotency_key
        ):
            raise AttemptConflict("Operation binding differs from the reserved attempt.")
        attempt = journal._attempt(
            {
                "outcome": row["att_outcome"],
                "provider_reference": row["att_provider_reference"],
            }
        )

    receipt: InboxReceipt | None = None
    if row["i_event_id"] is not None or row["c_event_id"] is not None:
        receipt = inbox._receipt(
            {
                "event_id": row["i_event_id"] if row["i_event_id"] is not None else row["c_event_id"],
                "event_type": row["i_event_type"],
                "provider_reference": row["i_provider_reference"],
                "payload_sha256": row["i_payload_sha256"],
            }
        )

    claim_status: ReadbackClaimStatus | None = None
    if row["c_event_id"] is not None:
        assert receipt is not None
        claim_status = ReadbackClaimStatus(
            ReadbackClaim(scope, receipt, row["c_worker_id"], row["c_generation"]),
            row["c_state"],
        )

    return StripeReadbackProvenance(
        scope=scope,
        event_id=event_id,
        fingerprint=operation.fingerprint,
        attempt=attempt,
        receipt=receipt,
        claim_status=claim_status,
    )


def read_stripe_readback_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
) -> StripeReadbackProvenance:
    """Read coupled attempt, receipt and claim provenance or fail closed when absent."""
    provenance = find_stripe_readback_provenance(
        inbox, journal, scope, event_id, operation,
    )
    if provenance is None:
        raise StripeReadbackError(
            "No payment attempt or webhook receipt exists for this operation and event."
        )
    return provenance


def accept_stripe_readback(
    inbox: StripeEventInbox, journal: PaymentAttemptJournal, claim: ReadbackClaim,
    operation: PaymentOperation, *,
    retrieved_account: str, intent: Mapping[str, object],
) -> PaymentAttempt:
    """Commit a fenced journal update and hint completion in one local transaction.

    Stores must share a canonical SQLite file. The caller authenticates workers,
    retrieval and freshness outside this transaction; a claim is not authority.
    Already-handled acceptance rejects, including a retry after a lost response.
    """
    if (
        not isinstance(inbox, StripeEventInbox)
        or not isinstance(journal, PaymentAttemptJournal)
        or not isinstance(claim, ReadbackClaim)
        or not isinstance(operation, PaymentOperation)
    ):
        raise StripeReadbackError(
            "Trusted inbox, journal, readback claim and payment operation are required."
        )
    if inbox.path.resolve(strict=True) != journal.path.resolve(strict=True):
        raise StripeReadbackError("Atomic acceptance requires the same resolved SQLite file.")
    with closing(inbox._connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        current = inbox._current_claim(db, claim)
        if current["state"] != "active":
            raise StripeReadbackError("Already-handled hints cannot authorize acceptance.")
        if (
            claim.scope.tenant_id != operation.tenant_id
            or claim.scope.provider_account != operation.provider_account
            or operation.provider != ("stripe:live" if claim.scope.livemode else "stripe:test")
        ):
            raise StripeReadbackError("Claim scope differs from the bound payment operation.")
        row = journal._find(db, operation)
        if row is None:
            raise AttemptConflict("Operation was never reserved.")
        previous = journal._attempt(row)
        if previous.provider_reference != claim.receipt.provider_reference:
            raise StripeReadbackError("Receipt differs from the trusted PaymentIntent association.")
        observation = validate_stripe_intent(
            operation, previous, retrieved_account=retrieved_account, intent=intent,
        )
        result = journal._reconcile_in_transaction(
            db, operation, observation=observation,
            provider_reference=claim.receipt.provider_reference,
        )
        inbox._finish_in_transaction(db, claim)
    return result
