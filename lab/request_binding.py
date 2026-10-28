"""Opt-in merchant JSON request binding, not signature verification or authorization."""

from dataclasses import dataclass
import hmac
import re

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest


MAX_BODY_BYTES = 1024 * 1024
MUTATION_COMPONENTS = ("@method", "@target-uri", "content-type", "content-digest")


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
