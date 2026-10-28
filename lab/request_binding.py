"""Opt-in merchant JSON request binding, not signature verification or authorization."""

from dataclasses import dataclass
import hmac
import re

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest


MAX_BODY_BYTES = 1024 * 1024
MUTATION_COMPONENTS = ("@method", "@target-uri", "content-type", "content-digest")
MAX_SIGNATURE_TIMESTAMP = 999_999_999_999_999


class RequestBindingError(ValueError):
    """The request does not meet the local signed-mutation profile."""


@dataclass(frozen=True)
class RequestSignatureSnapshot:
    """One trusted verifier's signed values; constructing this is not authentication."""

    signature_label: str
    key_id: str
    covered_components: tuple[str, ...]
    method: str
    target_uri: str
    content_type: str
    content_digest: str


@dataclass(frozen=True)
class TimedRequestSignatureSnapshot:
    """Same verified signature's snapshot and authenticated signature parameters.

    The adapter must supply created/expires from that signature, not another label
    or unsigned input. Construction is not cryptographic or provenance verification.
    """

    signature: RequestSignatureSnapshot
    created: int
    expires: int


def require_signature_time(signature: TimedRequestSignatureSnapshot, *, now: int) -> None:
    """Apply a zero-skew local window to preverified metadata, not verify a signature."""
    if (not isinstance(signature, TimedRequestSignatureSnapshot)
            or not isinstance(signature.signature, RequestSignatureSnapshot)):
        raise RequestBindingError("One trusted timed signature snapshot is required.")
    if type(now) is not int or not 0 <= now <= 2**63 - 1:
        raise RequestBindingError("Signature clock must be a nonnegative signed-64-bit integer.")
    if any(type(value) is not int or not 0 <= value <= MAX_SIGNATURE_TIMESTAMP
           for value in (signature.created, signature.expires)):
        raise RequestBindingError("Signature timestamps must be nonnegative Structured Field Integers.")
    if not signature.created < signature.expires:
        raise RequestBindingError("Signature creation must precede expiry.")
    if not signature.created <= now < signature.expires:
        raise RequestBindingError("Signature is outside the local admission time window.")


def _ascii_text(value: object, name: str) -> str:
    if (
        not isinstance(value, str) or not value or not value.isascii()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise RequestBindingError(f"{name} must be nonempty ASCII without controls")
    return value


def require_bound_json_mutation(
    signature: RequestSignatureSnapshot,
    *,
    method: str,
    target_uri: str,
    content_type: str,
    content_digest: str,
    content_encoding: str | None,
    body: bytes,
) -> None:
    """Compare actual ingress values/bytes to one preverified signature snapshot.

    The trusted adapter owns full RFC verification, key/tag/time/nonce policy,
    faithful target-URI derivation and raw duplicate-header rejection. Never take
    the snapshot from request JSON or an agent; no provenance is verified here.
    """
    if not isinstance(signature, RequestSignatureSnapshot):
        raise RequestBindingError("one trusted signature snapshot is required")
    label = _ascii_text(signature.signature_label, "signature label")
    if re.fullmatch(r"[a-z*][a-z0-9_.*-]*", label) is None:
        raise RequestBindingError("signature label must be a structured-field key")
    key_id = _ascii_text(signature.key_id, "key ID")
    if key_id != key_id.strip():
        raise RequestBindingError("key ID must not have surrounding whitespace")
    components = signature.covered_components
    if not isinstance(components, tuple) or any(
        not isinstance(component, str)
        or re.fullmatch(r"@?[a-z][a-z0-9_-]*", component) is None
        for component in components
    ):
        raise RequestBindingError("covered components must be bare identifiers in a tuple")
    if len(set(components)) != len(components):
        raise RequestBindingError("duplicate covered components are unsupported")
    if not set(MUTATION_COMPONENTS).issubset(components):
        raise RequestBindingError("one signature must cover every mutation component")
    for name, actual_value, signed_value in (
        ("method", method, signature.method),
        ("target_uri", target_uri, signature.target_uri),
        ("content_type", content_type, signature.content_type),
        ("content_digest", content_digest, signature.content_digest),
    ):
        actual = _ascii_text(actual_value, name)
        signed = _ascii_text(signed_value, f"signed {name}")
        if actual != signed:
            raise RequestBindingError(f"{name} differs from the signed snapshot")
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        raise RequestBindingError("only uppercase mutation methods are supported")
    if content_type != "application/json":
        raise RequestBindingError("only exact application/json is supported")
    if content_encoding is not None:
        raise RequestBindingError("Content-Encoding must be absent")
    if not isinstance(body, bytes):
        raise RequestBindingError("body must be original immutable bytes")
    if len(body) > MAX_BODY_BYTES:
        raise RequestBindingError("body exceeds the local 1 MiB limit")
    expected = compute_rfc9530_content_digest(body)
    if not hmac.compare_digest(content_digest, expected):
        raise RequestBindingError("canonical SHA256 Content-Digest does not match raw body")
