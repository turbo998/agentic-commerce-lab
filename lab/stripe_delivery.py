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

    def __post_init__(self) -> None:
        if type(self.timestamp) is not int or not 0 <= self.timestamp <= 2**63 - 1:
            raise StripeDeliveryError("Timestamp must be a nonnegative signed-64-bit integer.")
        if (
            not isinstance(self.payload_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256) is None
        ):
            raise StripeDeliveryError("Payload digest must be a 64-char hex SHA-256 string.")
        if self.requires_readback is not True:
            raise StripeDeliveryError("VerifiedDelivery requires_readback must be True.")


def _require_delivery_clock(now: int, tolerance: int) -> None:
    if type(now) is not int or not 0 <= now <= 2**63 - 1:
        raise StripeDeliveryError("A trusted nonnegative integer clock is required.")
    if type(tolerance) is not int or not 0 < tolerance <= 2**63 - 1:
        raise StripeDeliveryError("Tolerance must be a positive integer; zero cannot disable it.")


def _require_delivery_time(timestamp: int, *, now: int, tolerance: int) -> None:
    _require_delivery_clock(now, tolerance)
    if abs(now - timestamp) > tolerance:
        raise StripeDeliveryError("Delivery timestamp is outside the local tolerance window.")


def verify_stripe_delivery(
    body: bytes,
    signature_header: str,
    endpoint_secret: str | tuple[str, ...],
    *,
    now: int,
    tolerance: int = 300,
) -> VerifiedDelivery:
    """Verify exact bytes with trusted endpoint secrets and a clock.

    Positive tolerance, canonical/unique timestamps and symmetric past/future
    bounds are stricter local policy, not full SDK compatibility. This neither
    parses events nor deduplicates deliveries or modifies payment state.
    A nonempty tuple expresses overlap for the same endpoint/account/mode only.
    Callers own secret selection and retirement; no remote expiry is inferred.
    """
    if not isinstance(body, bytes):
        raise StripeDeliveryError("The unmodified request body must be bytes.")
    secrets = (endpoint_secret,) if isinstance(endpoint_secret, str) else endpoint_secret
    if (not isinstance(secrets, tuple) or not secrets
            or any(not isinstance(secret, str) or not secret.strip() for secret in secrets)):
        raise StripeDeliveryError("A nonblank endpoint secret or nonempty tuple of secrets is required.")
    if not isinstance(signature_header, str) or not signature_header:
        raise StripeDeliveryError("A Stripe-Signature header is required.")
    _require_delivery_clock(now, tolerance)

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
    expected_signatures = (
        hmac.new(secret.encode("utf-8"), signed_bytes, hashlib.sha256).hexdigest()
        for secret in secrets
    )
    if not any(hmac.compare_digest(expected, candidate)
               for expected in expected_signatures for candidate in signatures):
        raise StripeDeliveryError("Delivery signature mismatch.")
    _require_delivery_time(timestamp, now=now, tolerance=tolerance)
    return VerifiedDelivery(timestamp, hashlib.sha256(body).hexdigest())
