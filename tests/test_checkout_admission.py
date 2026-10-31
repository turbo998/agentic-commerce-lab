"""Synthetic admission ordering, exact semantics and durable dispatch boundaries."""

import json
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.checkout_admission import (
    CheckoutAdmissionError,
    preview_signed_checkout,
    reserve_signed_checkout,
)
from lab.json_members import unique_members
from lab.mcp_migration import unique_members as legacy_unique_members
from lab.payment_attempts import AttemptConflict, PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MAX_BODY_BYTES, MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot,
)


URI = "https://synthetic-shop.example/checkout?cart=one"


class CheckoutAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "commerce.sqlite3"
        self.journal = PaymentAttemptJournal(self.path)
        self.operation = PaymentOperation(
            "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
            Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
        )
        self.payload = asdict(self.operation.checkout)
        self.body = json.dumps(self.payload).encode()

    def admit(self, body=None, *, journal=None, operation=None, signature=None, **changes):
        body = self.body if body is None else body
        digest = compute_rfc9530_content_digest(body)
        values = {
            "expected_target_uri": URI, "method": "POST", "target_uri": URI,
            "content_type": "application/json", "content_digest": digest,
            "content_encoding": None, "body": body,
        }
        snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", URI,
            "application/json", digest,
        )
        values.update(changes)
        return reserve_signed_checkout(
            self.journal if journal is None else journal,
            self.operation if operation is None else operation,
            snapshot if signature is None else signature, **values,
        )

    def assert_unreserved(self) -> None:
        with self.assertRaisesRegex(AttemptConflict, "never reserved"):
            self.journal.read(self.operation)

    def test_valid_admission_returns_existing_unknown_dispatch_decision(self) -> None:
        digest = compute_rfc9530_content_digest(self.body)
        snapshot = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", URI,
            "application/json", digest,
        )
        preview = preview_signed_checkout(
            self.journal, self.operation, snapshot,
            expected_target_uri=URI, method="POST", target_uri=URI,
            content_type="application/json", content_digest=digest,
            content_encoding=None, body=self.body,
        )
        self.assertTrue(preview.would_insert)
        self.assertTrue(preview.dispatch_allowed)
        self.assertEqual(preview.phase, "reserved_unassociated")
        self.assert_unreserved()
        decision = self.admit()
        self.assertTrue(decision.dispatch_allowed)
        self.assertEqual(decision.attempt.outcome, "unknown")
        self.assertIsNone(decision.attempt.provider_reference)
        self.assertEqual(self.journal.read(self.operation), decision.attempt)
        after_preview = preview_signed_checkout(
            self.journal, self.operation, snapshot,
            expected_target_uri=URI, method="POST", target_uri=URI,
            content_type="application/json", content_digest=digest,
            content_encoding=None, body=self.body,
        )
        self.assertFalse(after_preview.would_insert)
        self.assertFalse(after_preview.dispatch_allowed)
        self.assertEqual(after_preview.existing_attempt, decision.attempt)

    def test_amount_is_total_not_unit_price(self) -> None:
        self.assertEqual(self.operation.checkout.quantity, 2)
        self.assertTrue(self.admit().dispatch_allowed)
        changed = dict(self.payload, amount=2000)
        with self.assertRaisesRegex(CheckoutAdmissionError, "trusted checkout"):
            self.admit(json.dumps(changed).encode())
        self.assertEqual(self.journal.read(self.operation).outcome, "unknown")

    def test_semantically_equal_different_signed_bytes_do_not_redispatch(self) -> None:
        first = self.admit()
        second_body = json.dumps(dict(reversed(list(self.payload.items()))), indent=2).encode()
        self.assertNotEqual(second_body, self.body)
        second = self.admit(second_body)
        self.assertTrue(first.dispatch_allowed)
        self.assertFalse(second.dispatch_allowed)
        self.assertEqual(first.attempt, second.attempt)

    def test_request_binding_failure_precedes_parser_and_reservation(self) -> None:
        with patch("lab.checkout_admission.json.loads") as decode, patch.object(
            self.journal, "reserve",
        ) as reserve:
            with self.assertRaises(RequestBindingError):
                self.admit(content_digest="sha-256=:invalid:")
            decode.assert_not_called()
            reserve.assert_not_called()
        self.assert_unreserved()

    def test_deep_input_and_decoder_recursion_failure_fail_explicitly(self) -> None:
        with self.assertRaises(CheckoutAdmissionError):
            self.admit(b"[" * 2000 + b"0" + b"]" * 2000)
        with patch("lab.checkout_admission.json.loads", side_effect=RecursionError):
            with self.assertRaisesRegex(CheckoutAdmissionError, "valid UTF-8"):
                self.admit()
        self.assert_unreserved()

    def test_route_configuration_is_trusted_not_chosen_by_signature(self) -> None:
        for configured in ("https://other.example/checkout", "", None):
            with self.subTest(configured=configured):
                with self.assertRaisesRegex(CheckoutAdmissionError, "route configuration"):
                    self.admit(expected_target_uri=configured)
        self.assert_unreserved()

    def test_another_signed_method_is_not_checkout_admission(self) -> None:
        for method in ("PUT", "DELETE", "post"):
            snapshot = RequestSignatureSnapshot(
                "sig1", "key", MUTATION_COMPONENTS, method, URI, "application/json",
                compute_rfc9530_content_digest(self.body),
            )
            with self.subTest(method=method):
                with self.assertRaisesRegex(CheckoutAdmissionError, "requires POST"):
                    self.admit(signature=snapshot, method=method)
        self.assert_unreserved()

    def test_every_trusted_checkout_field_must_match(self) -> None:
        for field, value in (
            ("merchant", "other-shop"), ("currency", "EUR"), ("currency", "usd"),
            ("sku", "other-sku"), ("quantity", 3), ("amount", 999),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(CheckoutAdmissionError, "trusted checkout"):
                    self.admit(json.dumps(dict(self.payload, **{field: value})).encode())
                self.assert_unreserved()

    def test_unknown_authority_or_provider_fields_are_not_accepted(self) -> None:
        for field in ("approval_id", "operation_id", "provider", "idempotency_key", "status"):
            with self.subTest(field=field):
                body = json.dumps(dict(self.payload, **{field: "agent-selected"})).encode()
                with self.assertRaisesRegex(CheckoutAdmissionError, "five checkout fields"):
                    self.admit(body)
        self.assert_unreserved()

    def test_missing_fields_and_nonobject_roots_reject(self) -> None:
        bodies = [b"null", b"[]", b"true", b"1000", b'"checkout"']
        bodies += [
            json.dumps({k: v for k, v in self.payload.items() if k != field}).encode()
            for field in self.payload
        ]
        for body in bodies:
            with self.subTest(body=body):
                with self.assertRaises(CheckoutAdmissionError):
                    self.admit(body)
        self.assert_unreserved()

    def test_duplicate_names_reject_even_when_last_value_matches(self) -> None:
        for prefix in (b'"amount":9000,', b'"amount":1000,', b'"\\u0061mount":9000,'):
            with self.subTest(prefix=prefix):
                with self.assertRaisesRegex(CheckoutAdmissionError, "Duplicate"):
                    self.admit(b"{" + prefix + self.body[1:])
        self.assert_unreserved()

    def test_nested_duplicate_names_are_not_hidden(self) -> None:
        body = self.body[:-1] + b',"extra":{"hidden":1,"hidden":2}}'
        with self.assertRaisesRegex(CheckoutAdmissionError, "Duplicate"):
            self.admit(body)
        self.assert_unreserved()

    def test_boolean_and_string_numbers_are_not_coerced(self) -> None:
        for field in ("quantity", "amount"):
            for value in (True, False, "1000", None):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(CheckoutAdmissionError, "must be an integer"):
                        self.admit(json.dumps(dict(self.payload, **{field: value})).encode())
        self.assert_unreserved()

    def test_fraction_exponent_and_nonfinite_tokens_reject(self) -> None:
        for token in (b"1000.0", b"1e3", b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(token=token):
                body = self.body.replace(b'"amount": 1000', b'"amount": ' + token)
                self.assertNotEqual(body, self.body)
                with self.assertRaisesRegex(CheckoutAdmissionError, "integer JSON numbers"):
                    self.admit(body)
        self.assert_unreserved()

    def test_invalid_integer_values_cannot_match_trusted_quote(self) -> None:
        for field in ("quantity", "amount"):
            for value in (0, -1, 2**63, 10**19):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(CheckoutAdmissionError):
                        self.admit(json.dumps(dict(self.payload, **{field: value})).encode())
        self.assert_unreserved()

    def test_integer_tokens_are_bounded_before_conversion(self) -> None:
        with self.assertRaisesRegex(CheckoutAdmissionError, "trusted checkout"):
            self.admit(self.body.replace(b'"amount": 1000', b'"amount": ' + b"9" * 20))
        for token in (b"9" * 21, b"9" * 5000):
            with self.subTest(length=len(token)):
                body = self.body.replace(b'"amount": 1000', b'"amount": ' + token)
                with self.assertRaisesRegex(CheckoutAdmissionError, "token exceeds"):
                    self.admit(body)
        self.assert_unreserved()

    def test_trusted_signed64_boundary_is_not_rounded(self) -> None:
        checkout = replace(self.operation.checkout, amount=2**63 - 1, quantity=2**63 - 1)
        operation = replace(self.operation, checkout=checkout)
        decision = self.admit(json.dumps(asdict(checkout)).encode(), operation=operation)
        self.assertTrue(decision.dispatch_allowed)

    def test_nonstring_text_fields_reject(self) -> None:
        for field in ("merchant", "currency", "sku"):
            for value in (1, True, None, {}, []):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(CheckoutAdmissionError, "must be a string"):
                        self.admit(json.dumps(dict(self.payload, **{field: value})).encode())
        self.assert_unreserved()

    def test_unicode_scalars_work_without_normalizing_identity(self) -> None:
        checkout = replace(self.operation.checkout, merchant="caf\u00e9", sku="\u5546\u54c1")
        operation = replace(self.operation, checkout=checkout)
        decision = self.admit(json.dumps(asdict(checkout)).encode(), operation=operation)
        self.assertTrue(decision.dispatch_allowed)
        decomposed = dict(asdict(checkout), merchant="cafe\u0301")
        with self.assertRaisesRegex(CheckoutAdmissionError, "trusted checkout"):
            self.admit(json.dumps(decomposed).encode(), operation=operation)

    def test_unpaired_surrogate_rejects_even_in_trusted_quote(self) -> None:
        checkout = replace(self.operation.checkout, merchant="\ud800")
        operation = replace(self.operation, checkout=checkout)
        with self.assertRaisesRegex(CheckoutAdmissionError, "Unicode scalars"):
            self.admit(json.dumps(asdict(checkout)).encode(), operation=operation)
        self.assert_unreserved()

    def test_invalid_utf8_bom_and_json_fail_explicitly(self) -> None:
        for body in (b"\xff", b"\xef\xbb\xbf" + self.body, b"{", self.body + b"{}"):
            with self.subTest(body_length=len(body)):
                with self.assertRaisesRegex(CheckoutAdmissionError, "valid UTF-8"):
                    self.admit(body)
        self.assert_unreserved()

    def test_exact_body_limit_accepts_valid_padded_json_and_rejects_one_more(self) -> None:
        body = self.body + b" " * (MAX_BODY_BYTES - len(self.body))
        with self.assertRaisesRegex(RequestBindingError, "1 MiB"):
            self.admit(body + b" ")
        self.assert_unreserved()
        for length in (MAX_BODY_BYTES - 1, MAX_BODY_BYTES):
            with self.subTest(length=length):
                decision = self.admit(body[:length])
                self.assertEqual(decision.dispatch_allowed, length == MAX_BODY_BYTES - 1)

    def test_rejected_request_does_not_consume_first_dispatch(self) -> None:
        with self.assertRaises(CheckoutAdmissionError):
            self.admit(json.dumps(dict(self.payload, amount=1)).encode())
        self.assert_unreserved()
        self.assertTrue(self.admit().dispatch_allowed)
        self.assertFalse(self.admit().dispatch_allowed)

    def test_existing_unknown_survives_rejected_and_valid_retries(self) -> None:
        self.admit()
        before = self.journal.read(self.operation)
        with self.assertRaises(CheckoutAdmissionError):
            self.admit(json.dumps(dict(self.payload, amount=9000)).encode())
        self.assertEqual(self.journal.read(self.operation), before)
        decision = self.admit()
        self.assertFalse(decision.dispatch_allowed)
        self.assertEqual(decision.attempt, before)

    def test_terminal_retry_does_not_reopen_or_dispatch(self) -> None:
        self.admit()
        terminal = self.journal.reconcile(
            self.operation, observation="succeeded", provider_reference="pi_synthetic",
        )
        decision = self.admit()
        self.assertFalse(decision.dispatch_allowed)
        self.assertEqual(decision.attempt, terminal)

    def test_existing_journal_conflicts_and_storage_errors_propagate(self) -> None:
        self.admit()
        changed = replace(self.operation, approval_id="different-approval")
        with self.assertRaises(AttemptConflict):
            self.admit(operation=changed)
        with patch.object(self.journal, "reserve", side_effect=OSError("synthetic storage failure")):
            with self.assertRaisesRegex(OSError, "storage failure"):
                self.admit()

    def test_concurrent_admissions_grant_one_dispatch(self) -> None:
        barrier = Barrier(2)

        def reserve():
            journal = PaymentAttemptJournal(self.path)
            barrier.wait(timeout=10)
            return self.admit(journal=journal)

        with ThreadPoolExecutor(max_workers=2) as pool:
            decisions = list(pool.map(lambda _: reserve(), range(2)))
        self.assertEqual(sum(d.dispatch_allowed for d in decisions), 1)
        self.assertTrue(all(d.attempt.outcome == "unknown" for d in decisions))

    def test_fresh_process_admission_does_not_redispatch(self) -> None:
        self.admit()
        script = """
import json, sys
from pathlib import Path
from lab.checkout import Checkout
from lab.checkout_admission import reserve_signed_checkout
from lab.payment_attempts import PaymentOperation, PaymentAttemptJournal
from lab.request_binding import RequestSignatureSnapshot, MUTATION_COMPONENTS
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
body = bytes.fromhex(sys.argv[2])
uri = sys.argv[3]
digest = compute_rfc9530_content_digest(body)
operation = PaymentOperation('tenant','operation','approval','stripe:test',
    'acct_synthetic','key',Checkout('synthetic-shop','USD','synthetic-sku',2,1000))
snapshot = RequestSignatureSnapshot('sig1','synthetic-key',MUTATION_COMPONENTS,
    'POST',uri,'application/json',digest)
decision = reserve_signed_checkout(PaymentAttemptJournal(Path(sys.argv[1])), operation,
    snapshot, expected_target_uri=uri, method='POST', target_uri=uri,
    content_type='application/json', content_digest=digest, content_encoding=None, body=body)
print(json.dumps({'dispatch':decision.dispatch_allowed,'outcome':decision.attempt.outcome}))
"""
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path), self.body.hex(), URI],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(output.stdout), {"dispatch": False, "outcome": "unknown"})

    def test_legacy_duplicate_hook_is_reexported_unchanged(self) -> None:
        self.assertIs(legacy_unique_members, unique_members)
        self.assertEqual(legacy_unique_members([("field", 1)]), {"field": 1})
        with self.assertRaisesRegex(ValueError, "Duplicate JSON member; use one value per field"):
            legacy_unique_members([("field", 1), ("field", 2)])

    def test_legacy_direct_file_cli_is_preserved(self) -> None:
        script = Path(__file__).resolve().parents[1] / "lab" / "mcp_migration.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("--as-of", result.stdout)


if __name__ == "__main__":
    unittest.main()
