"""Opt-in signed checkout admission, not pricing, consent or a payment adapter."""

import json
from dataclasses import asdict
from typing import NoReturn

from lab.json_members import unique_members
from lab.payment_attempts import DispatchDecision, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import RequestSignatureSnapshot, require_bound_json_mutation


class CheckoutAdmissionError(ValueError):
    """The request is not an unambiguous representation of the trusted checkout."""


def _checkout_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    try:
        return unique_members(pairs)
    except ValueError as error:
        raise CheckoutAdmissionError("Duplicate checkout JSON member.") from error


def _bounded_integer(value: str) -> int:
    if len(value) > 20:
        raise CheckoutAdmissionError("Checkout integer token exceeds the local limit.")
    return int(value)


def _reject_fraction_or_constant(value: str) -> NoReturn:
    raise CheckoutAdmissionError("Only integer JSON numbers are supported.")


def validate_signed_checkout(
    operation: PaymentOperation,
    signature: RequestSignatureSnapshot,
    *,
    expected_target_uri: str,
    method: str,
    target_uri: str,
    content_type: str,
    content_digest: str,
    content_encoding: str | None,
    body: bytes,
) -> None:
    """Bind ingress and match a trusted quote without reserving or authorizing.

    The caller owns signature provenance, route/operation lookup, pricing, consent,
    expiry and revocation. None of those trusted inputs may come from agent JSON.
    No journal state, approval, nonce or provider is changed.
    """
    if not isinstance(operation, PaymentOperation):
        raise CheckoutAdmissionError("A trusted PaymentOperation is required.")
    if (
        not isinstance(expected_target_uri, str) or not expected_target_uri
        or target_uri != expected_target_uri
    ):
        raise CheckoutAdmissionError("Target URI differs from trusted route configuration.")
    if method != "POST":
        raise CheckoutAdmissionError("Checkout admission requires POST.")
    require_bound_json_mutation(
        signature, method=method, target_uri=target_uri, content_type=content_type,
        content_digest=content_digest, content_encoding=content_encoding, body=body,
    )
    try:
        payload = json.loads(
            body.decode("utf-8"), object_pairs_hook=_checkout_members,
            parse_int=_bounded_integer, parse_float=_reject_fraction_or_constant,
            parse_constant=_reject_fraction_or_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise CheckoutAdmissionError("A valid UTF-8 checkout JSON object is required.") from error
    if not isinstance(payload, dict) or set(payload) != {
        "merchant", "currency", "sku", "quantity", "amount",
    }:
        raise CheckoutAdmissionError("Only the five checkout fields are supported.")
    for field in ("merchant", "currency", "sku"):
        value = payload[field]
        if not isinstance(value, str):
            raise CheckoutAdmissionError(f"Checkout {field} must be a string.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise CheckoutAdmissionError("Checkout strings must contain Unicode scalars.") from error
    for field in ("quantity", "amount"):
        if type(payload[field]) is not int:
            raise CheckoutAdmissionError(f"Checkout {field} must be an integer, not boolean.")
    if payload != asdict(operation.checkout):
        raise CheckoutAdmissionError("Request differs from the trusted checkout.")


def reserve_signed_checkout(
    journal: PaymentAttemptJournal,
    operation: PaymentOperation,
    signature: RequestSignatureSnapshot,
    *,
    expected_target_uri: str,
    method: str,
    target_uri: str,
    content_type: str,
    content_digest: str,
    content_encoding: str | None,
    body: bytes,
) -> DispatchDecision:
    """Bind/match then reserve; caller still checks consent, expiry and revocation."""
    if not isinstance(journal, PaymentAttemptJournal) or not isinstance(operation, PaymentOperation):
        raise CheckoutAdmissionError("A trusted journal and PaymentOperation are required.")
    validate_signed_checkout(
        operation, signature, expected_target_uri=expected_target_uri, method=method,
        target_uri=target_uri, content_type=content_type, content_digest=content_digest,
        content_encoding=content_encoding, body=body,
    )
    return journal.reserve(operation)
