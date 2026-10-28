"""Offline raw-byte Stripe v1 delivery verification, not payment reconciliation."""

import hashlib
import hmac
import re
from dataclasses import dataclass


class StripeDeliveryError(ValueError):
    """A delivery failed this reference's signature, header, or time policy."""


@dataclass(frozen=True)
class VerifiedDelivery:
    timestamp: int
    payload_sha256: str
    requires_readback: bool = True


def verify_stripe_delivery(
    body: bytes,
    signature_header: str,
    endpoint_secret: str,
    *,
    now: int,
    tolerance: int = 300,
) -> VerifiedDelivery:
    """Verify exact bytes with an externally selected endpoint secret and clock.

    Positive tolerance, canonical/unique timestamps and symmetric past/future
    bounds are stricter local policy, not full SDK compatibility. This neither
    parses events nor deduplicates deliveries or modifies payment state.
    """
    if not isinstance(body, bytes):
        raise StripeDeliveryError("The unmodified request body must be bytes.")
    if not isinstance(endpoint_secret, str) or not endpoint_secret.strip():
        raise StripeDeliveryError("A nonblank endpoint secret is required.")
    if not isinstance(signature_header, str) or not signature_header:
        raise StripeDeliveryError("A Stripe-Signature header is required.")
    if type(now) is not int or not 0 <= now <= 2**63 - 1:
        raise StripeDeliveryError("A trusted nonnegative integer clock is required.")
    if type(tolerance) is not int or not 0 < tolerance <= 2**63 - 1:
        raise StripeDeliveryError("Tolerance must be a positive integer; zero cannot disable it.")

    timestamps: list[str] = []
    signatures: list[str] = []
    for component in signature_header.split(","):
        key, separator, value = component.strip().partition("=")
        if not separator or not key or not value:
            raise StripeDeliveryError("Malformed signature header component.")
        if key == "t":
            timestamps.append(value)
        elif key == "v1":
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise StripeDeliveryError("Malformed v1 signature.")
            signatures.append(value)
    if len(timestamps) != 1 or re.fullmatch(r"0|[1-9][0-9]{0,18}", timestamps[0]) is None:
        raise StripeDeliveryError("Exactly one canonical timestamp is required.")
    timestamp = int(timestamps[0])
    if timestamp > 2**63 - 1:
        raise StripeDeliveryError("Timestamp is outside the supported integer range.")
    if not signatures:
        raise StripeDeliveryError("At least one v1 signature is required.")

    signed_bytes = timestamps[0].encode("ascii") + b"." + body
    expected = hmac.new(
        endpoint_secret.encode("utf-8"), signed_bytes, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise StripeDeliveryError("Delivery signature mismatch.")
    if abs(now - timestamp) > tolerance:
        raise StripeDeliveryError("Delivery timestamp is outside the local tolerance window.")
    return VerifiedDelivery(timestamp, hashlib.sha256(body).hexdigest())
