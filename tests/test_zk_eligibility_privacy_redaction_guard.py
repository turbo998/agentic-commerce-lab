"""Unit tests for Stage 17 ZK Selective-Disclosure Eligibility, PCI-DSS Redaction & Crypto-Shredding Guard."""

from __future__ import annotations

import hashlib
import unittest

from lab.zk_eligibility_privacy_redaction_guard import (
    evaluate_zk_selective_disclosure_eligibility,
    scan_and_redact_agent_context_pii_pci,
    verify_crypto_shredding_erasure_tombstone,
)


class ZkEligibilityPrivacyRedactionGuardTestSuite(unittest.TestCase):
    def test_zk_selective_disclosure_passes_without_raw_pii(self) -> None:
        res = evaluate_zk_selective_disclosure_eligibility(
            {
                "checkout_session_id": "cs_01",
                "presentation_nonce": "cs_01",
                "issuer_did": "did:web:trust.visa.com:tap-vc",
                "issued_at_epoch": 1_000,
                "now_epoch": 1_120,
                "max_proof_ttl_seconds": 300,
                "signature_valid": True,
                "merchant_requested_fields": ["age_over_21", "professional_license_active"],
                "required_predicates": ["age_over_21", "professional_license_active"],
                "verified_predicates": {
                    "age_over_21": True,
                    "professional_license_active": True,
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.zero_raw_pii_exposed)
        self.assertEqual(res.decision_code, "ZK_SELECTIVE_DISCLOSURE_ELIGIBILITY_VERIFIED")

    def test_zk_blocks_overprivileged_raw_pii_harvesting_and_replay(self) -> None:
        harvest = evaluate_zk_selective_disclosure_eligibility(
            {
                "checkout_session_id": "cs_02",
                "presentation_nonce": "cs_02",
                "issuer_did": "did:web:trust.visa.com:tap-vc",
                "issued_at_epoch": 1_000,
                "now_epoch": 1_050,
                "merchant_requested_fields": ["age_over_21", "ssn", "raw_date_of_birth"],
                "required_predicates": ["age_over_21"],
                "verified_predicates": {"age_over_21": True},
            }
        )
        self.assertFalse(harvest.allowed)
        self.assertEqual(harvest.decision_code, "OVERPRIVILEGED_PII_HARVESTING_BLOCKED")
        self.assertIn("ssn", harvest.blocked_raw_pii_fields)

        replay = evaluate_zk_selective_disclosure_eligibility(
            {
                "checkout_session_id": "cs_02",
                "presentation_nonce": "cs_old_session",
                "issuer_did": "did:web:trust.visa.com:tap-vc",
                "issued_at_epoch": 1_000,
                "now_epoch": 1_050,
                "required_predicates": ["age_over_21"],
                "verified_predicates": {"age_over_21": True},
            }
        )
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.decision_code, "ZK_CREDENTIAL_EXPIRED_OR_REPLAYED")

    def test_pci_firewall_blocks_and_redacts_luhn_pan_cvv_and_live_secret(self) -> None:
        dirty = (
            "Please charge 4242-4242-4242-4242 (CVV=901) using key sk_live_abcdef1234567890 "
            "for taxpayer 123-45-6789."
        )
        res = scan_and_redact_agent_context_pii_pci(dirty)
        self.assertFalse(res.safe_to_transmit)
        self.assertEqual(res.decision_code, "PCI_RAW_PAN_OR_CVV_LEAK_BLOCKED")
        self.assertEqual(res.pan_matches_redacted, 1)
        self.assertEqual(res.cvv_matches_redacted, 1)
        self.assertEqual(res.secret_keys_redacted, 1)
        self.assertEqual(res.ssn_matches_redacted, 1)
        self.assertIn("<REDACTED_PAN_L4:4242>", res.redacted_text)
        self.assertNotIn("sk_live_abcdef1234567890", res.redacted_text)

        clean = scan_and_redact_agent_context_pii_pci(
            "Tokenized SPT spt_live_99812 for SKU-GPU-H200 quantity 2"
        )
        self.assertTrue(clean.safe_to_transmit)
        self.assertEqual(clean.decision_code, "CONTEXT_CLEAN_PCI_PII_COMPLIANT")

    def test_crypto_shredding_tombstone_preserves_atdrp_merkle_root(self) -> None:
        pii_hash = hashlib.sha256(b"cipher_pii_01|salt_99").hexdigest()
        fin_hash = hashlib.sha256(b"fin_leaf_50000").hexdigest()
        root = hashlib.sha256(f"{pii_hash}|{fin_hash}".encode("utf-8")).hexdigest()

        ok = verify_crypto_shredding_erasure_tombstone(
            {
                "principal_did": "did:web:buyer.example:bob",
                "kms_cek_id": "kms-key-bob-01",
                "kms_cek_destroyed": True,
                "kms_destruction_receipt_sig": "sig_kms_destroyed_99",
                "plaintext_pii_still_present": False,
                "pii_leaf_ciphertext_hex": "cipher_pii_01",
                "pii_leaf_salt": "salt_99",
                "financial_commitment_leaf_hash": fin_hash,
                "expected_merkle_root": root,
            }
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.merkle_root_preserved)
        self.assertEqual(ok.decision_code, "CRYPTO_SHREDDED_TOMBSTONE_VERIFIED")

        active_key = verify_crypto_shredding_erasure_tombstone(
            {
                "principal_did": "did:web:buyer.example:bob",
                "kms_cek_id": "kms-key-bob-01",
                "kms_cek_destroyed": False,
                "kms_destruction_receipt_sig": "",
                "plaintext_pii_still_present": False,
                "pii_leaf_ciphertext_hex": "cipher_pii_01",
                "pii_leaf_salt": "salt_99",
                "financial_commitment_leaf_hash": fin_hash,
                "expected_merkle_root": root,
            }
        )
        self.assertFalse(active_key.valid)
        self.assertEqual(
            active_key.decision_code, "GDPR_ERASURE_INCOMPLETE_KEY_STILL_ACTIVE"
        )


if __name__ == "__main__":
    unittest.main()
