"""Offline direct-account PaymentIntent readback policy, not a Stripe client."""

import re
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass

from lab.payment_attempts import (
    AttemptConflict,
    AttemptPhase,
    Observation,
    Outcome,
    PaymentAttempt,
    PaymentAttemptJournal,
    PaymentOperation,
)


PENDING_STATUSES = frozenset({
    "requires_payment_method", "requires_confirmation", "requires_action",
    "processing", "requires_capture",
})
_PI_RE = re.compile(r"pi_[A-Za-z0-9_]+")


class StripeObservationError(ValueError):
    """A provider readback is incomplete, inconsistent, or outside this policy."""


@dataclass(frozen=True)
class StripeObservationPreview:
    """Read-only reconciliation preview; never mutates payment_attempts or grants authority."""

    operation: PaymentOperation
    previous: PaymentAttempt
    observation: Observation
    next_attempt: PaymentAttempt

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise StripeObservationError("A trusted PaymentOperation is required.")
        if not isinstance(self.previous, PaymentAttempt) or not isinstance(
            self.next_attempt, PaymentAttempt
        ):
            raise StripeObservationError("Persisted and projected PaymentAttempt instances are required.")
        if (
            self.previous.provider_reference is None
            or _PI_RE.fullmatch(self.previous.provider_reference) is None
        ):
            raise StripeObservationError("A trusted PaymentIntent association must be persisted first.")
        if self.next_attempt.provider_reference != self.previous.provider_reference:
            raise StripeObservationError(
                "Projected PaymentAttempt reference differs from persisted association."
            )
        if not isinstance(self.observation, str) or self.observation not in (
            "pending",
            "succeeded",
            "failed",
        ):
            raise StripeObservationError("Observation must be pending, succeeded, or failed.")
        expected_outcome: Outcome = (
            "unknown" if self.observation == "pending" else self.observation
        )
        if self.previous.outcome != "unknown" and self.previous.outcome != expected_outcome:
            raise AttemptConflict("Terminal outcome cannot be overwritten.")
        if self.next_attempt.outcome != expected_outcome:
            raise StripeObservationError(
                "Projected PaymentAttempt outcome does not match observation transition."
            )

    @property
    def would_advance(self) -> bool:
        return self.previous.outcome != self.next_attempt.outcome

    @property
    def is_terminal(self) -> bool:
        return self.next_attempt.outcome in ("succeeded", "failed")

    @property
    def previous_phase(self) -> AttemptPhase:
        return self.previous.phase

    @property
    def next_phase(self) -> AttemptPhase:
        return self.next_attempt.phase


@dataclass(frozen=True)
class StripeAssociationPreview:
    """Read-only association preview; never mutates payment_attempts or grants authority."""

    operation: PaymentOperation
    expected_reference: str
    observation: Observation
    previous: PaymentAttempt
    next_attempt: PaymentAttempt
    would_bind: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PaymentOperation):
            raise StripeObservationError("A trusted PaymentOperation is required.")
        if (
            not isinstance(self.expected_reference, str)
            or _PI_RE.fullmatch(self.expected_reference) is None
        ):
            raise StripeObservationError(
                "A separately trusted PaymentIntent reference is required."
            )
        if not isinstance(self.observation, str) or self.observation not in (
            "pending",
            "succeeded",
            "failed",
        ):
            raise StripeObservationError(
                "Observation must be pending, succeeded, or failed."
            )
        if not isinstance(self.previous, PaymentAttempt) or not isinstance(
            self.next_attempt, PaymentAttempt
        ):
            raise StripeObservationError(
                "Persisted and projected PaymentAttempt instances are required."
            )
        if type(self.would_bind) is not bool:
            raise StripeObservationError("would_bind must be a boolean.")
        if self.previous.provider_reference not in (None, self.expected_reference):
            raise AttemptConflict(
                "Provider reference changed; investigate the conflict."
            )
        if self.previous.provider_reference is None:
            if self.previous.outcome != "unknown":
                raise AttemptConflict(
                    "An unassociated terminal attempt cannot be rebound."
                )
            if not self.would_bind or self.next_attempt != PaymentAttempt(
                "unknown", self.expected_reference
            ):
                raise StripeObservationError(
                    "First-time association preview must set would_bind=True and project pending association."
                )
        else:
            if self.would_bind or self.next_attempt != self.previous:
                raise StripeObservationError(
                    "Idempotent association preview must set would_bind=False and preserve previous attempt."
                )

    @property
    def previous_phase(self) -> AttemptPhase:
        return self.previous.phase

    @property
    def next_phase(self) -> AttemptPhase:
        return self.next_attempt.phase

    @property
    def is_already_bound(self) -> bool:
        return not self.would_bind


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
    if not isinstance(expected_reference, str) or _PI_RE.fullmatch(expected_reference) is None:
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


def find_stripe_association_preview(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    expected_reference: str,
    intent: Mapping[str, object],
) -> StripeAssociationPreview | None:
    """Preview PaymentIntent association in one lock-free SELECT without writing."""
    if not isinstance(journal, PaymentAttemptJournal) or not isinstance(operation, PaymentOperation):
        raise StripeObservationError("A trusted journal and PaymentOperation are required.")
    if not isinstance(expected_reference, str) or _PI_RE.fullmatch(expected_reference) is None:
        raise StripeObservationError("A separately trusted PaymentIntent reference is required.")
    _require_context(operation, retrieved_account, intent)
    with closing(journal._connect()) as db:
        row = db.execute(
            """SELECT
                p.*,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM payment_attempts other
                        WHERE other.provider = p.provider
                          AND other.provider_account = p.provider_account
                          AND other.provider_reference = ?
                          AND NOT (
                              other.tenant_id = p.tenant_id
                              AND other.operation_id = p.operation_id
                          )
                    ) THEN 1
                    ELSE 0
                END AS reference_conflict
            FROM payment_attempts p
            WHERE p.tenant_id = ? AND p.operation_id = ?
            """,
            (expected_reference, operation.tenant_id, operation.operation_id),
        ).fetchone()
    if row is None:
        return None
    journal._verify_row_binding(row, operation)
    previous = journal._attempt(row)
    observation = validate_stripe_intent(
        operation,
        PaymentAttempt("unknown", expected_reference),
        retrieved_account=retrieved_account,
        intent=intent,
    )
    if previous.provider_reference not in (None, expected_reference):
        raise AttemptConflict("Provider reference changed; investigate the conflict.")
    if previous.provider_reference is None and previous.outcome != "unknown":
        raise AttemptConflict("An unassociated terminal attempt cannot be rebound.")
    if row["reference_conflict"]:
        raise AttemptConflict("Provider reference already bound to another operation.")
    would_bind = previous.provider_reference is None
    next_attempt = (
        PaymentAttempt("unknown", expected_reference)
        if would_bind
        else previous
    )
    return StripeAssociationPreview(
        operation=operation,
        expected_reference=expected_reference,
        observation=observation,
        previous=previous,
        next_attempt=next_attempt,
        would_bind=would_bind,
    )


def read_stripe_association_preview(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    expected_reference: str,
    intent: Mapping[str, object],
) -> StripeAssociationPreview:
    """Preview PaymentIntent association in one lock-free SELECT or raise if unreserved."""
    preview = find_stripe_association_preview(
        journal,
        operation,
        retrieved_account=retrieved_account,
        expected_reference=expected_reference,
        intent=intent,
    )
    if preview is None:
        raise AttemptConflict("Operation was never reserved.")
    return preview


def preview_associate_stripe_intent(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    expected_reference: str,
    intent: Mapping[str, object],
) -> StripeAssociationPreview:
    """Preview associate_stripe_intent() in one lock-free SELECT without writing."""
    return read_stripe_association_preview(
        journal,
        operation,
        retrieved_account=retrieved_account,
        expected_reference=expected_reference,
        intent=intent,
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
    with closing(journal._connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row = journal._find(db, operation)
        if row is None:
            raise AttemptConflict("Operation was never reserved.")
        previous = journal._attempt(row)
        observation = validate_stripe_intent(
            operation, previous, retrieved_account=retrieved_account, intent=intent,
        )
        assert previous.provider_reference is not None
        return journal._reconcile_in_transaction(
            db, operation, observation=observation, provider_reference=previous.provider_reference,
        )


def find_stripe_observation_preview(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    intent: Mapping[str, object],
) -> StripeObservationPreview | None:
    """Preview PaymentIntent reconciliation in one lock-free SELECT without writing."""
    if not isinstance(journal, PaymentAttemptJournal) or not isinstance(operation, PaymentOperation):
        raise StripeObservationError("A trusted journal and PaymentOperation are required.")
    _require_context(operation, retrieved_account, intent)
    with closing(journal._connect()) as db:
        row = db.execute(
            """
            SELECT
                p.*,
                CASE
                    WHEN p.provider_reference IS NOT NULL AND EXISTS (
                        SELECT 1 FROM payment_attempts other
                        WHERE other.provider = p.provider
                          AND other.provider_account = p.provider_account
                          AND other.provider_reference = p.provider_reference
                          AND NOT (
                              other.tenant_id = p.tenant_id
                              AND other.operation_id = p.operation_id
                          )
                    ) THEN 1
                    ELSE 0
                END AS reference_conflict
            FROM payment_attempts p
            WHERE p.tenant_id = ? AND p.operation_id = ?
            """,
            (operation.tenant_id, operation.operation_id),
        ).fetchone()
    if row is None:
        return None
    journal._verify_row_binding(row, operation)
    previous = journal._attempt(row)
    observation = validate_stripe_intent(
        operation, previous, retrieved_account=retrieved_account, intent=intent,
    )
    assert previous.provider_reference is not None
    outcome: Outcome = "unknown" if observation == "pending" else observation
    if previous.outcome != "unknown" and previous.outcome != outcome:
        raise AttemptConflict("Terminal outcome cannot be overwritten.")
    if row["reference_conflict"]:
        raise AttemptConflict("Provider reference already bound to another operation.")
    return StripeObservationPreview(
        operation=operation,
        previous=previous,
        observation=observation,
        next_attempt=PaymentAttempt(outcome, previous.provider_reference),
    )


def read_stripe_observation_preview(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    *,
    retrieved_account: str,
    intent: Mapping[str, object],
) -> StripeObservationPreview:
    """Preview PaymentIntent reconciliation in one lock-free SELECT or raise if unreserved."""
    preview = find_stripe_observation_preview(
        journal,
        operation,
        retrieved_account=retrieved_account,
        intent=intent,
    )
    if preview is None:
        raise AttemptConflict("Operation was never reserved.")
    return preview


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
    if (
        previous.provider_reference is None
        or _PI_RE.fullmatch(previous.provider_reference) is None
    ):
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
