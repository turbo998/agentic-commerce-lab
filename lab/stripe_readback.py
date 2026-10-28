"""Atomic local acceptance of trusted readbacks, not provider transactions."""

from collections.abc import Mapping
from contextlib import closing

from lab.payment_attempts import AttemptConflict, PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import ReadbackClaim, StripeEventInbox
from lab.stripe_observation import validate_stripe_intent


class StripeReadbackError(ValueError):
    """The configured stores, active claim or operation do not share a binding."""


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
