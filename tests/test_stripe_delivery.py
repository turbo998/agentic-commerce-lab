"""Synthetic raw-body verification, time boundaries and non-payment semantics."""

import hashlib
import hmac
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_delivery import StripeDeliveryError, verify_stripe_delivery


SYNTHETIC_SECRET = "synthetic-only-not-a-real-secret"
TIMESTAMP = 1700000000
BODY = b'{"id":"evt_synthetic"}'
FIXTURE_SIGNATURE = "585651ea0f3c4918ed81ef14a60ffcf0063a442cf6797db445410d1ef4930528"


def sign(body: bytes, timestamp: int = TIMESTAMP, secret: str = SYNTHETIC_SECRET) -> str:
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


class StripeDeliveryTests(unittest.TestCase):
    def verify(self, body=BODY, header=None, *, now=TIMESTAMP, tolerance=300):
        return verify_stripe_delivery(
            body, sign(body) if header is None else header, SYNTHETIC_SECRET,
            now=now, tolerance=tolerance,
        )

    def test_fixed_fixture_computed_independently_with_dotnet(self) -> None:
        result = self.verify(header=f"t={TIMESTAMP},v1={FIXTURE_SIGNATURE}")
        self.assertEqual(result.timestamp, TIMESTAMP)
        self.assertEqual(result.payload_sha256, hashlib.sha256(BODY).hexdigest())
        self.assertTrue(result.requires_readback)

    def test_body_reserialization_or_single_byte_change_is_rejected(self) -> None:
        header = sign(BODY)
        for modified in (BODY + b"\n", BODY.replace(b":", b": "), BODY.replace(b"id", b"Id")):
            with self.subTest(body=modified), self.assertRaises(StripeDeliveryError):
                self.verify(modified, header)

    def test_wrong_secret_cannot_verify_a_signature(self) -> None:
        with self.assertRaisesRegex(StripeDeliveryError, "mismatch"):
            self.verify(header=sign(BODY, secret="synthetic-wrong-secret"))

    def test_multiple_v1_candidates_support_rotation(self) -> None:
        wrong = "0" * 64
        result = self.verify(header=f"t={TIMESTAMP},v1={wrong},v1={FIXTURE_SIGNATURE}")
        self.assertTrue(result.requires_readback)
        result = self.verify(header=f"t={TIMESTAMP},v1={FIXTURE_SIGNATURE},v1={wrong}")
        self.assertTrue(result.requires_readback)

    def test_other_schemes_cannot_replace_v1(self) -> None:
        with self.assertRaisesRegex(StripeDeliveryError, "v1 signature"):
            self.verify(header=f"t={TIMESTAMP},v0={FIXTURE_SIGNATURE}")
        self.assertTrue(self.verify(
            header=f"t={TIMESTAMP},v0=ignored,v1={FIXTURE_SIGNATURE}"
        ).requires_readback)

    def test_malformed_and_ambiguous_headers_are_explicit_errors(self) -> None:
        headers = (
            "", f"v1={FIXTURE_SIGNATURE}", f"t={TIMESTAMP}",
            f"t={TIMESTAMP},t={TIMESTAMP},v1={FIXTURE_SIGNATURE}",
            f"t=0{TIMESTAMP},v1={FIXTURE_SIGNATURE}",
            f"t=-1,v1={FIXTURE_SIGNATURE}", f"t=1.5,v1={FIXTURE_SIGNATURE}",
            f"t={2**63},v1={FIXTURE_SIGNATURE}",
            f"t={TIMESTAMP},v1=abc", f"t={TIMESTAMP},v1={FIXTURE_SIGNATURE.upper()}",
            f"t={TIMESTAMP},v1={FIXTURE_SIGNATURE},", f"t={TIMESTAMP},v1=",
        )
        for header in headers:
            with self.subTest(header=header), self.assertRaises(StripeDeliveryError):
                self.verify(header=header)

    def test_exact_past_and_future_tolerance_boundaries_are_inclusive(self) -> None:
        for offset in (-300, 300):
            with self.subTest(offset=offset):
                self.assertTrue(self.verify(now=TIMESTAMP + offset).requires_readback)

    def test_stale_and_far_future_signed_deliveries_are_rejected(self) -> None:
        for offset in (-301, 301):
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(StripeDeliveryError, "tolerance window"):
                    self.verify(now=TIMESTAMP + offset)

    def test_zero_negative_boolean_or_noninteger_tolerance_is_rejected(self) -> None:
        for value in (0, -1, True, 300.0, "300", None):
            with self.subTest(value=value), self.assertRaises(StripeDeliveryError):
                self.verify(tolerance=value)

    def test_trusted_clock_must_be_a_nonnegative_integer(self) -> None:
        for value in (-1, True, 1700000000.0, "1700000000", None, 2**63):
            with self.subTest(value=value), self.assertRaises(StripeDeliveryError):
                self.verify(now=value)

    def test_raw_body_and_configuration_types_are_required(self) -> None:
        for body in (BODY.decode(), bytearray(BODY), None):
            with self.subTest(body=body), self.assertRaises(StripeDeliveryError):
                verify_stripe_delivery(body, sign(BODY), SYNTHETIC_SECRET, now=TIMESTAMP)
        for secret in ("", " \t\n", None, b"synthetic"):
            with self.subTest(secret=secret), self.assertRaises(StripeDeliveryError):
                verify_stripe_delivery(BODY, sign(BODY), secret, now=TIMESTAMP)
        with self.assertRaises(StripeDeliveryError):
            verify_stripe_delivery(BODY, None, SYNTHETIC_SECRET, now=TIMESTAMP)

    def test_replay_inside_window_is_not_claimed_to_be_prevented(self) -> None:
        first = self.verify()
        second = self.verify(now=TIMESTAMP + 1)
        self.assertEqual(first, second)
        self.assertTrue(second.requires_readback)

    def test_signature_verification_is_not_json_schema_validation(self) -> None:
        result = self.verify(b"not-json")
        self.assertTrue(result.requires_readback)

    def test_verified_success_event_does_not_change_unknown_payment(self) -> None:
        with TemporaryDirectory() as directory:
            journal = PaymentAttemptJournal(Path(directory) / "attempts.sqlite3")
            operation = PaymentOperation(
                "tenant", "op", "approval", "stripe:test", "acct_synthetic", "key",
                Checkout("shop", "USD", "sku", 1, 1000),
            )
            journal.reserve(operation)
            before = journal.read(operation)
            event = b'{"id":"evt_synthetic","type":"payment_intent.succeeded"}'
            verified = self.verify(event)
            self.assertTrue(verified.requires_readback)
            self.assertEqual(journal.read(operation), before)
            self.assertEqual(before.outcome, "unknown")
            self.assertFalse(journal.reserve(operation).dispatch_allowed)

    def test_raw_body_and_secret_are_not_returned(self) -> None:
        body = b'{"client_secret":"SYNTHETIC_SENSITIVE_MARKER"}'
        result = self.verify(body)
        self.assertEqual(set(asdict(result)), {"timestamp", "payload_sha256", "requires_readback"})
        self.assertNotIn("SYNTHETIC_SENSITIVE_MARKER", repr(result))
        self.assertNotIn(SYNTHETIC_SECRET, repr(result))

    def test_exact_utf8_bytes_are_verified_without_reserialization(self) -> None:
        body = b'{"description":"caf\xc3\xa9"}'
        self.assertTrue(self.verify(body).requires_readback)
        with self.assertRaises(StripeDeliveryError):
            self.verify(b'{"description":"caf\\u00e9"}', sign(body))


if __name__ == "__main__":
    unittest.main()
