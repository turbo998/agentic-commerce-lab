"""Synthetic merchant binding tests; no cryptographic signature verification."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_BODY_BYTES,
    MUTATION_COMPONENTS,
    RequestBindingError,
    RequestSignatureSnapshot,
    require_bound_json_mutation,
)


BODY = b'{"amount":1000,"currency":"usd"}'
DIGEST = "sha-256=:oiO2DcatvCkR58BziJsiDfEYHFU0+mvljDpwmBw1TFQ=:"
URI = "https://synthetic-shop.example/checkout?cart=one"


class RequestBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS,
            "POST", URI, "application/json", DIGEST,
        )

    def bind(self, signature=None, **changes):
        values = {
            "method": "POST", "target_uri": URI, "content_type": "application/json",
            "content_digest": DIGEST, "content_encoding": None, "body": BODY,
        }
        values.update(changes)
        return require_bound_json_mutation(
            self.snapshot if signature is None else signature, **values,
        )

    def test_independent_dotnet_vector_returns_none(self) -> None:
        self.assertEqual(compute_rfc9530_content_digest(BODY), DIGEST)
        self.assertIsNone(self.bind())

    def test_body_tampering_with_original_header_rejects(self) -> None:
        with self.assertRaisesRegex(RequestBindingError, "raw body"):
            self.bind(body=BODY.replace(b"1000", b"9000"))

    def test_recomputed_header_cannot_replace_signed_digest(self) -> None:
        changed = BODY.replace(b"1000", b"9000")
        with self.assertRaisesRegex(RequestBindingError, "signed snapshot"):
            self.bind(body=changed, content_digest=compute_rfc9530_content_digest(changed))

    def test_changed_request_metadata_rejects(self) -> None:
        for field, value in (
            ("method", "DELETE"),
            ("target_uri", URI.replace("one", "two")),
            ("target_uri", URI.replace("synthetic-shop", "different-shop")),
            ("target_uri", URI.replace("/checkout", "/refund")),
            ("content_type", "text/plain"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(RequestBindingError, "signed snapshot"):
                    self.bind(**{field: value})

    def test_target_uri_is_not_normalized(self) -> None:
        for uri in (URI.replace("cart=one", "cart=%6Fne"), URI.replace("https", "HTTPS")):
            with self.subTest(uri=uri):
                with self.assertRaises(RequestBindingError):
                    self.bind(target_uri=uri)

    def test_no_missing_component_is_inferred(self) -> None:
        for missing in MUTATION_COMPONENTS:
            snapshot = replace(
                self.snapshot,
                covered_components=tuple(c for c in MUTATION_COMPONENTS if c != missing),
            )
            with self.subTest(missing=missing):
                with self.assertRaisesRegex(RequestBindingError, "every mutation"):
                    self.bind(snapshot)

    def test_authority_and_path_do_not_substitute_for_target_uri(self) -> None:
        snapshot = replace(
            self.snapshot,
            covered_components=("@method", "@authority", "@path", "content-type", "content-digest"),
        )
        with self.assertRaisesRegex(RequestBindingError, "every mutation"):
            self.bind(snapshot)

    def test_unrelated_signatures_cannot_union_coverage(self) -> None:
        first = replace(self.snapshot, covered_components=("@method", "@target-uri"))
        second = replace(
            self.snapshot, signature_label="sig2",
            covered_components=("content-type", "content-digest"),
        )
        for signature in (first, second, (first, second), {"sig1": first, "sig2": second}):
            with self.subTest(signature=signature):
                with self.assertRaises(RequestBindingError):
                    self.bind(signature)

    def test_parameterized_components_are_not_flattened(self) -> None:
        for component in (
            "content-digest;sf", "content-digest;req", "content-digest;tr",
            "@target-uri;req", '"@method"', "Content-Type",
        ):
            with self.subTest(component=component):
                snapshot = replace(
                    self.snapshot, covered_components=(*MUTATION_COMPONENTS, component),
                )
                with self.assertRaisesRegex(RequestBindingError, "bare identifiers"):
                    self.bind(snapshot)

    def test_duplicate_components_reject(self) -> None:
        snapshot = replace(
            self.snapshot, covered_components=(*MUTATION_COMPONENTS, "content-digest"),
        )
        with self.assertRaisesRegex(RequestBindingError, "duplicate"):
            self.bind(snapshot)

    def test_mutable_or_nontext_component_metadata_rejects(self) -> None:
        for components in (list(MUTATION_COMPONENTS), None, (*MUTATION_COMPONENTS, 5)):
            with self.subTest(components=components):
                with self.assertRaises(RequestBindingError):
                    self.bind(replace(self.snapshot, covered_components=components))

    def test_bare_additional_components_and_different_order_are_supported(self) -> None:
        snapshot = replace(
            self.snapshot,
            covered_components=("x-operation-id", *reversed(MUTATION_COMPONENTS)),
        )
        self.assertIsNone(self.bind(snapshot))

    def test_snapshot_identity_metadata_is_required(self) -> None:
        for field, value in (
            ("signature_label", ""), ("signature_label", "Sig1"),
            ("signature_label", "sig1;foo"), ("key_id", ""),
            ("key_id", " key"), ("key_id", "key\n"), ("key_id", "\u00e9"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(RequestBindingError):
                    self.bind(replace(self.snapshot, **{field: value}))

    def test_only_exact_mutation_methods_are_supported(self) -> None:
        for method in ("GET", "post", " POST", "", None, 1):
            with self.subTest(method=method):
                with self.assertRaises(RequestBindingError):
                    self.bind(replace(self.snapshot, method=method), method=method)
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertIsNone(self.bind(replace(self.snapshot, method=method), method=method))

    def test_exact_json_type_is_a_local_restriction(self) -> None:
        for content_type in ("text/plain", "application/json; charset=utf-8", "Application/JSON"):
            with self.subTest(content_type=content_type):
                with self.assertRaisesRegex(RequestBindingError, "exact application/json"):
                    self.bind(
                        replace(self.snapshot, content_type=content_type),
                        content_type=content_type,
                    )

    def test_any_present_content_encoding_rejects(self) -> None:
        for encoding in ("gzip", "identity", "", False, ["gzip"]):
            with self.subTest(encoding=encoding):
                with self.assertRaisesRegex(RequestBindingError, "must be absent"):
                    self.bind(content_encoding=encoding)

    def test_canonical_digest_profile_rejects_richer_or_malformed_forms(self) -> None:
        for digest in (
            DIGEST + ", sha-512=:AA==:", DIGEST + ", " + DIGEST,
            DIGEST + ";foo=1", DIGEST.replace("sha-256", "SHA-256"),
            DIGEST.replace("=:", "= :"), DIGEST.replace("+", "-"),
            DIGEST.replace("TFQ=", "TFQ"), "sha-256=:AA==:", "sha-256=:!!!:",
            DIGEST + " ", " " + DIGEST,
        ):
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(RequestBindingError, "canonical SHA256"):
                    self.bind(replace(self.snapshot, content_digest=digest), content_digest=digest)

    def test_invalid_text_fails_explicitly_not_compare_digest_type_error(self) -> None:
        for field in ("method", "target_uri", "content_type", "content_digest"):
            for value in (None, 7, b"ascii", "", "\u00e9", "line\r\nbreak", "\x7f"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(RequestBindingError):
                        self.bind(**{field: value})
                    with self.assertRaises(RequestBindingError):
                        self.bind(replace(self.snapshot, **{field: value}))

    def test_only_raw_immutable_bytes_are_supported(self) -> None:
        for body in (BODY.decode(), bytearray(BODY), memoryview(BODY), {}, None):
            with self.subTest(body=body):
                with self.assertRaisesRegex(RequestBindingError, "immutable bytes"):
                    self.bind(body=body)

    def test_body_is_not_json_reserialized(self) -> None:
        with self.assertRaisesRegex(RequestBindingError, "raw body"):
            self.bind(body=b'{"amount": 1000, "currency": "usd"}')

    def test_exact_local_body_limit_and_one_byte_over(self) -> None:
        for length in (MAX_BODY_BYTES, MAX_BODY_BYTES + 1):
            body = b" " * length
            digest = compute_rfc9530_content_digest(body)
            snapshot = replace(self.snapshot, content_digest=digest)
            with self.subTest(length=length):
                if length == MAX_BODY_BYTES:
                    self.assertIsNone(self.bind(snapshot, content_digest=digest, body=body))
                else:
                    with self.assertRaisesRegex(RequestBindingError, "1 MiB"):
                        self.bind(snapshot, content_digest=digest, body=body)

    def test_binding_does_not_parse_json_or_consume_a_nonce(self) -> None:
        body = b"not-json"
        digest = compute_rfc9530_content_digest(body)
        snapshot = replace(self.snapshot, content_digest=digest)
        for _ in range(2):
            self.assertIsNone(self.bind(snapshot, content_digest=digest, body=body))

    def test_snapshot_is_immutable_but_not_cryptographic_proof(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.method = "DELETE"
        self.assertIsNone(self.bind(replace(self.snapshot, key_id="another-preverified-key")))

    def test_binding_neither_closes_unknown_nor_grants_new_dispatch(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaymentAttemptJournal(Path(directory) / "attempts.sqlite3")
            operation = PaymentOperation(
                "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
                Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
            )
            journal.reserve(operation)
            journal.reconcile(operation, observation="pending", provider_reference="pi_synthetic")
            before = journal.read(operation)
            self.assertIsNone(self.bind())
            with self.assertRaises(RequestBindingError):
                self.bind(body=b"tampered")
            self.assertEqual(journal.read(operation), before)
            self.assertEqual(before.outcome, "unknown")
            self.assertFalse(journal.reserve(operation).dispatch_allowed)


if __name__ == "__main__":
    unittest.main()
