"""Offline direct-account PaymentIntent readback policy, not a Stripe client."""

import re
from collections.abc import Mapping
from contextlib import closing

from lab.payment_attempts import (
    AttemptConflict, Observation, PaymentAttempt, PaymentAttemptJournal, PaymentOperation,
)


PENDING_STATUSES = frozenset({
    "requires_payment_method", "requires_confirmation", "requires_action",
    "processing", "requires_capture",
})


class StripeObservationError(ValueError):
    """A provider readback is incomplete, inconsistent, or outside this policy."""


def associate_stripe_intent(
    journal: PaymentAttemptJournal, operation: PaymentOperation, *,
    retrieved_account: str, expected_reference: str, intent: Mapping[str, object],
) -> PaymentAttempt:
    """Validate before binding a separately trusted first PaymentIntent reference.

    The adapter authenticates retrieval, freshness and operation-to-reference
    correlation independently of the payload. This never reserves, sends or
    infers a payment outcome; identical retries preserve existing terminal state.
    """
    if not isinstance(journal, PaymentAttemptJournal) or not isinstance(operation, PaymentOperation):
        raise StripeObservationError("A trusted journal and PaymentOperation are required.")
    if (not isinstance(expected_reference, str)
            or re.fullmatch(r"pi_[A-Za-z0-9_]+", expected_reference) is None):
        raise StripeObservationError("A separately trusted PaymentIntent reference is required.")
    with closing(journal._connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = journal._find(db, operation)
        if row is None:
            raise AttemptConflict("Operation was never reserved.")
        previous = journal._attempt(row)
        validate_stripe_intent(
            operation, PaymentAttempt("unknown", expected_reference),
            retrieved_account=retrieved_account, intent=intent,
        )
        if previous.provider_reference not in (None, expected_reference):
            raise AttemptConflict("Provider reference changed; investigate the conflict.")
        if previous.provider_reference == expected_reference:
            return previous
        if previous.outcome != "unknown":
            raise AttemptConflict("An unassociated terminal attempt cannot be rebound.")
        return journal._reconcile_in_transaction(
            db, operation, observation="pending", provider_reference=expected_reference,
        )


def reconcile_stripe_intent(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    intent: Mapping[str, object],
) -> PaymentAttempt:
    """Validate a trusted synthetic readback before closing a bound operation.

    The caller authenticates retrieval, freshness and the initial intent-to-
    operation association. This is not a webhook verifier or an agent tool.
    Provider namespaces stripe:test/stripe:live are local policy conventions.
    Only direct-account, exact-full-amount payments are supported.
    """
    if not isinstance(journal, PaymentAttemptJournal) or not isinstance(operation, PaymentOperation):
        raise StripeObservationError("A trusted journal and PaymentOperation are required.")
    _require_context(operation, retrieved_account, intent)
    previous = journal.read(operation)
    observation = validate_stripe_intent(
        operation, previous, retrieved_account=retrieved_account, intent=intent,
    )
    assert previous.provider_reference is not None
    return journal.reconcile(
        operation, observation=observation, provider_reference=previous.provider_reference,
    )


def _require_context(
    operation: PaymentOperation, retrieved_account: str, intent: Mapping[str, object],
) -> None:
    if not isinstance(operation, PaymentOperation):
        raise StripeObservationError("A trusted PaymentOperation is required.")
    if operation.provider not in ("stripe:test", "stripe:live"):
        raise StripeObservationError("An explicit Stripe test/live provider binding is required.")
    if not isinstance(retrieved_account, str) or retrieved_account != operation.provider_account:
        raise StripeObservationError("Retrieval account differs from the bound provider account.")
    if not isinstance(intent, Mapping):
        raise StripeObservationError("PaymentIntent readback must be a mapping.")


def validate_stripe_intent(
    operation: PaymentOperation, previous: PaymentAttempt, *,
    retrieved_account: str, intent: Mapping[str, object],
) -> Observation:
    """Map a trusted readback against persisted state, without writing or retrieving."""
    _require_context(operation, retrieved_account, intent)
    if not isinstance(previous, PaymentAttempt):
        raise StripeObservationError("A persisted PaymentAttempt is required.")
    if previous.provider_reference is None or not previous.provider_reference.startswith("pi_"):
        raise StripeObservationError("A trusted PaymentIntent association must be persisted first.")
    if intent.get("object") != "payment_intent":
        raise StripeObservationError("Readback must be a PaymentIntent, not an event or SetupIntent.")
    if intent.get("id") != previous.provider_reference:
        raise StripeObservationError("PaymentIntent ID differs from the persisted association.")
    mode = intent.get("livemode")
    if type(mode) is not bool or mode != (operation.provider == "stripe:live"):
        raise StripeObservationError("PaymentIntent mode differs from the bound provider namespace.")
    if intent.get("currency") != operation.checkout.currency.lower():
        raise StripeObservationError("PaymentIntent currency differs from the approved quote.")
    amount = intent.get("amount")
    received = intent.get("amount_received")
    if type(amount) is not int or amount != operation.checkout.amount:
        raise StripeObservationError("PaymentIntent amount differs from the approved quote.")
    if type(received) is not int or not 0 <= received <= amount:
        raise StripeObservationError("PaymentIntent amount_received is invalid for this policy.")
    for field in ("transfer_data", "on_behalf_of"):
        if field not in intent or intent[field] is not None:
            raise StripeObservationError("Explicit direct-account routing fields are required.")

    status = intent.get("status")
    observation: Observation
    if status == "succeeded":
        if received != amount:
            raise StripeObservationError("Successful readback does not confirm the full amount.")
        observation = "succeeded"
    elif status == "canceled":
        if received != 0:
            raise StripeObservationError("Canceled readback has funds received; investigate.")
        observation = "failed"
    elif isinstance(status, str) and status in PENDING_STATUSES:
        observation = "pending"
    else:
        raise StripeObservationError("Unknown or missing PaymentIntent status; investigate.")
    return observation
