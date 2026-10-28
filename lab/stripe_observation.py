"""Offline direct-account PaymentIntent readback policy, not a Stripe client."""

from collections.abc import Mapping

from lab.payment_attempts import Observation, PaymentAttempt, PaymentAttemptJournal, PaymentOperation


PENDING_STATUSES = frozenset({
    "requires_payment_method", "requires_confirmation", "requires_action",
    "processing", "requires_capture",
})


class StripeObservationError(ValueError):
    """A provider readback is incomplete, inconsistent, or outside this policy."""


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
    if operation.provider not in ("stripe:test", "stripe:live"):
        raise StripeObservationError("An explicit Stripe test/live provider binding is required.")
    if retrieved_account != operation.provider_account:
        raise StripeObservationError("Retrieval account differs from the bound provider account.")
    if not isinstance(intent, Mapping):
        raise StripeObservationError("PaymentIntent readback must be a mapping.")


def validate_stripe_intent(
    operation: PaymentOperation, previous: PaymentAttempt, *,
    retrieved_account: str, intent: Mapping[str, object],
) -> Observation:
    """Map a trusted readback against persisted state, without writing or retrieving."""
    _require_context(operation, retrieved_account, intent)
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
