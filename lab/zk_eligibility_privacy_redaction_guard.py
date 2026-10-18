"""Stage 17: Zero-Knowledge Selective-Disclosure Eligibility, PCI-DSS 4.0.1 Redaction Firewall & GDPR Crypto-Shredding Guard.

Implements three deterministic privacy and compliance controls for Agentic Commerce:
1. ``evaluate_zk_selective_disclosure_eligibility``: Verifies IETF SD-JWT / zk-VC boolean
   eligibility predicates (age, residency, B2B accreditation), blocks over-privileged merchant
   MCP requests for raw PII (DOB/SSN/Passport), and prevents presentation replay.
2. ``scan_and_redact_agent_context_pii_pci``: Scans agent prompts/tool payloads for Luhn-valid
   PANs, CVVs, SSNs, and live API secrets (`sk_live_*`, `rk_live_*`), redacting them in-place
   and tripping PCI-DSS v4.0.1 circuit breakers.
3. ``verify_crypto_shredding_erasure_tombstone``: Reconciles GDPR Art. 17 Right-to-Erasure with
   ACP PR #316 ATDRP §7.4a immutable Merkle audit trees via per-principal KMS CEK destruction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any


PROHIBITED_RAW_PII_FIELDS: frozenset[str] = frozenset(
    {
        "raw_date_of_birth",
        "date_of_birth",
        "ssn",
        "social_security_number",
        "passport_number",
        "national_id_number",
        "drivers_license_number",
        "raw_biometric_template",
    }
)

DEFAULT_TRUSTED_ISSUER_DIDS: frozenset[str] = frozenset(
    {
        "did:web:trust.visa.com:tap-vc",
        "did:web:identity.stripe.com:vc-issuer",
        "did:web:eudi.ec.europa.eu:pid-issuer",
        "did:web:registry.ap2.google:credential-issuer",
    }
)

_SECRET_KEY_REGEX = re.compile(r"\b(?:sk_live|rk_live|whsec)_[A-Za-z0-9]{8,}\b")
_SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CVV_REGEX = re.compile(r"\b(?:cvv|cvc|cid)\s*[:=]?\s*\d{3,4}\b", re.IGNORECASE)
_PAN_CANDIDATE_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


@dataclass(frozen=True)
class ZkEligibilityEvaluationResult:
    """Result of selective-disclosure / zero-knowledge eligibility verification."""

    allowed: bool
    decision_code: str
    checkout_session_id: str
    issuer_did: str
    satisfied_predicates: list[str]
    missing_predicates: list[str]
    blocked_raw_pii_fields: list[str]
    proof_age_seconds: int
    zero_raw_pii_exposed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PciRedactionFirewallResult:
    """Result of PCI-DSS v4.0.1 & secret redaction scan on agent context."""

    safe_to_transmit: bool
    decision_code: str
    redacted_text: str
    pan_matches_redacted: int
    cvv_matches_redacted: int
    secret_keys_redacted: int
    ssn_matches_redacted: int
    detected_violation_types: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CryptoShreddingTombstoneResult:
    """Result of GDPR Art. 17 crypto-shredding & ATDRP Merkle root verification."""

    valid: bool
    decision_code: str
    principal_did: str
    kms_cek_id: str
    kms_cek_destroyed: bool
    pii_mathematically_irrecoverable: bool
    merkle_root_preserved: bool
    recomputed_merkle_root: str
    expected_merkle_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _passes_luhn(digits: str) -> bool:
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse_digits = digits[::-1]
    for idx, ch in enumerate(reverse_digits):
        n = int(ch)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def evaluate_zk_selective_disclosure_eligibility(
    eligibility_context: dict[str, Any],
) -> ZkEligibilityEvaluationResult:
    """Verify selective-disclosure (SD-JWT / zk-VC) predicates and block raw PII harvesting."""

    session_id = str(eligibility_context.get("checkout_session_id", ""))
    presentation_nonce = str(eligibility_context.get("presentation_nonce", ""))
    issuer_did = str(eligibility_context.get("issuer_did", ""))
    trusted_issuers = set(
        eligibility_context.get("trusted_issuer_dids", DEFAULT_TRUSTED_ISSUER_DIDS)
    )
    issued_at_epoch = int(eligibility_context.get("issued_at_epoch", 0))
    now_epoch = int(eligibility_context.get("now_epoch", 0))
    max_proof_ttl_seconds = int(eligibility_context.get("max_proof_ttl_seconds", 300))
    signature_valid = bool(eligibility_context.get("signature_valid", True))

    requested_fields = [
        str(f).strip().lower()
        for f in eligibility_context.get("merchant_requested_fields", [])
    ]
    disclosed_raw_pii = [
        str(f).strip().lower()
        for f in eligibility_context.get("disclosed_raw_pii_fields", [])
    ]
    blocked_pii = sorted(
        set(
            f
            for f in (requested_fields + disclosed_raw_pii)
            if f in PROHIBITED_RAW_PII_FIELDS
        )
    )

    required_predicates = [
        str(p) for p in eligibility_context.get("required_predicates", [])
    ]
    verified_predicates_map: dict[str, bool] = {
        str(k): bool(v)
        for k, v in dict(eligibility_context.get("verified_predicates", {})).items()
    }

    satisfied = [p for p in required_predicates if verified_predicates_map.get(p) is True]
    missing = [p for p in required_predicates if verified_predicates_map.get(p) is not True]
    proof_age = now_epoch - issued_at_epoch

    if blocked_pii:
        return ZkEligibilityEvaluationResult(
            allowed=False,
            decision_code="OVERPRIVILEGED_PII_HARVESTING_BLOCKED",
            checkout_session_id=session_id,
            issuer_did=issuer_did,
            satisfied_predicates=satisfied,
            missing_predicates=missing,
            blocked_raw_pii_fields=blocked_pii,
            proof_age_seconds=proof_age,
            zero_raw_pii_exposed=False,
        )

    if not signature_valid or issuer_did not in trusted_issuers:
        return ZkEligibilityEvaluationResult(
            allowed=False,
            decision_code="UNTRUSTED_ZK_CREDENTIAL_ISSUER_OR_BAD_SIG",
            checkout_session_id=session_id,
            issuer_did=issuer_did,
            satisfied_predicates=satisfied,
            missing_predicates=missing,
            blocked_raw_pii_fields=[],
            proof_age_seconds=proof_age,
            zero_raw_pii_exposed=True,
        )

    if (
        not session_id
        or presentation_nonce != session_id
        or proof_age < 0
        or proof_age > max_proof_ttl_seconds
    ):
        return ZkEligibilityEvaluationResult(
            allowed=False,
            decision_code="ZK_CREDENTIAL_EXPIRED_OR_REPLAYED",
            checkout_session_id=session_id,
            issuer_did=issuer_did,
            satisfied_predicates=satisfied,
            missing_predicates=missing,
            blocked_raw_pii_fields=[],
            proof_age_seconds=proof_age,
            zero_raw_pii_exposed=True,
        )

    if missing:
        return ZkEligibilityEvaluationResult(
            allowed=False,
            decision_code="ELIGIBILITY_PREDICATE_UNSATISFIED",
            checkout_session_id=session_id,
            issuer_did=issuer_did,
            satisfied_predicates=satisfied,
            missing_predicates=missing,
            blocked_raw_pii_fields=[],
            proof_age_seconds=proof_age,
            zero_raw_pii_exposed=True,
        )

    return ZkEligibilityEvaluationResult(
        allowed=True,
        decision_code="ZK_SELECTIVE_DISCLOSURE_ELIGIBILITY_VERIFIED",
        checkout_session_id=session_id,
        issuer_did=issuer_did,
        satisfied_predicates=satisfied,
        missing_predicates=[],
        blocked_raw_pii_fields=[],
        proof_age_seconds=proof_age,
        zero_raw_pii_exposed=True,
    )


def scan_and_redact_agent_context_pii_pci(
    payload_text: str,
    *,
    block_on_detection: bool = True,
) -> PciRedactionFirewallResult:
    """Detect and redact Luhn-valid PANs, CVVs, live secret keys, and SSNs from agent context."""

    redacted = str(payload_text)
    pan_count = 0
    cvv_count = 0
    secret_count = 0
    ssn_count = 0
    violations: list[str] = []

    def _replace_secret(match: re.Match[str]) -> str:
        nonlocal secret_count
        secret_count += 1
        return "<REDACTED_SECRET_KEY>"

    redacted = _SECRET_KEY_REGEX.sub(_replace_secret, redacted)
    if secret_count > 0:
        violations.append("LIVE_API_SECRET_KEY")

    def _replace_cvv(match: re.Match[str]) -> str:
        nonlocal cvv_count
        cvv_count += 1
        return "<REDACTED_CVV>"

    redacted = _CVV_REGEX.sub(_replace_cvv, redacted)
    if cvv_count > 0:
        violations.append("PCI_CVV_SECURITY_CODE")

    def _replace_ssn(match: re.Match[str]) -> str:
        nonlocal ssn_count
        ssn_count += 1
        return "<REDACTED_SSN>"

    redacted = _SSN_REGEX.sub(_replace_ssn, redacted)
    if ssn_count > 0:
        violations.append("RAW_TAX_ID_SSN")

    def _replace_pan(match: re.Match[str]) -> str:
        nonlocal pan_count
        raw = match.group(0)
        digits = "".join(ch for ch in raw if ch.isdigit())
        if _passes_luhn(digits):
            pan_count += 1
            return f"<REDACTED_PAN_L4:{digits[-4:]}>"
        return raw

    redacted = _PAN_CANDIDATE_REGEX.sub(_replace_pan, redacted)
    if pan_count > 0:
        violations.insert(0, "PCI_RAW_PAN_LUHN_MATCH")

    total_hits = pan_count + cvv_count + secret_count + ssn_count
    if total_hits > 0 and block_on_detection:
        code = (
            "PCI_RAW_PAN_OR_CVV_LEAK_BLOCKED"
            if (pan_count > 0 or cvv_count > 0)
            else "SENSITIVE_SECRET_OR_PII_CONTEXT_LEAK_BLOCKED"
        )
        return PciRedactionFirewallResult(
            safe_to_transmit=False,
            decision_code=code,
            redacted_text=redacted,
            pan_matches_redacted=pan_count,
            cvv_matches_redacted=cvv_count,
            secret_keys_redacted=secret_count,
            ssn_matches_redacted=ssn_count,
            detected_violation_types=violations,
        )

    return PciRedactionFirewallResult(
        safe_to_transmit=True,
        decision_code="CONTEXT_CLEAN_PCI_PII_COMPLIANT",
        redacted_text=redacted,
        pan_matches_redacted=pan_count,
        cvv_matches_redacted=cvv_count,
        secret_keys_redacted=secret_count,
        ssn_matches_redacted=ssn_count,
        detected_violation_types=violations,
    )


def verify_crypto_shredding_erasure_tombstone(
    tombstone_bundle: dict[str, Any],
) -> CryptoShreddingTombstoneResult:
    """Verify GDPR Art. 17 crypto-shredding tombstone and ATDRP Merkle root preservation."""

    principal_did = str(tombstone_bundle.get("principal_did", ""))
    kms_cek_id = str(tombstone_bundle.get("kms_cek_id", ""))
    kms_cek_destroyed = bool(tombstone_bundle.get("kms_cek_destroyed", False))
    kms_destruction_receipt_sig = str(
        tombstone_bundle.get("kms_destruction_receipt_sig", "")
    )
    plaintext_pii_still_present = bool(
        tombstone_bundle.get("plaintext_pii_still_present", False)
    )
    pii_leaf_ciphertext_hex = str(tombstone_bundle.get("pii_leaf_ciphertext_hex", ""))
    pii_leaf_salt = str(tombstone_bundle.get("pii_leaf_salt", ""))
    financial_commitment_leaf_hash = str(
        tombstone_bundle.get("financial_commitment_leaf_hash", "")
    )
    expected_merkle_root = str(tombstone_bundle.get("expected_merkle_root", ""))

    pii_leaf_hash = hashlib.sha256(
        f"{pii_leaf_ciphertext_hex}|{pii_leaf_salt}".encode("utf-8")
    ).hexdigest()
    recomputed_root = hashlib.sha256(
        f"{pii_leaf_hash}|{financial_commitment_leaf_hash}".encode("utf-8")
    ).hexdigest()
    root_preserved = bool(expected_merkle_root) and (
        recomputed_root == expected_merkle_root
    )

    if plaintext_pii_still_present or not kms_cek_destroyed or not kms_destruction_receipt_sig:
        return CryptoShreddingTombstoneResult(
            valid=False,
            decision_code="GDPR_ERASURE_INCOMPLETE_KEY_STILL_ACTIVE",
            principal_did=principal_did,
            kms_cek_id=kms_cek_id,
            kms_cek_destroyed=kms_cek_destroyed,
            pii_mathematically_irrecoverable=False,
            merkle_root_preserved=root_preserved,
            recomputed_merkle_root=recomputed_root,
            expected_merkle_root=expected_merkle_root,
        )

    if not root_preserved:
        return CryptoShreddingTombstoneResult(
            valid=False,
            decision_code="ATDRP_MERKLE_ROOT_INTEGRITY_BROKEN",
            principal_did=principal_did,
            kms_cek_id=kms_cek_id,
            kms_cek_destroyed=True,
            pii_mathematically_irrecoverable=True,
            merkle_root_preserved=False,
            recomputed_merkle_root=recomputed_root,
            expected_merkle_root=expected_merkle_root,
        )

    return CryptoShreddingTombstoneResult(
        valid=True,
        decision_code="CRYPTO_SHREDDED_TOMBSTONE_VERIFIED",
        principal_did=principal_did,
        kms_cek_id=kms_cek_id,
        kms_cek_destroyed=True,
        pii_mathematically_irrecoverable=True,
        merkle_root_preserved=True,
        recomputed_merkle_root=recomputed_root,
        expected_merkle_root=expected_merkle_root,
    )


def _demo() -> None:
    zk_res = evaluate_zk_selective_disclosure_eligibility(
        {
            "checkout_session_id": "cs_zk_20261019_01",
            "presentation_nonce": "cs_zk_20261019_01",
            "issuer_did": "did:web:trust.visa.com:tap-vc",
            "issued_at_epoch": 1792368000,
            "now_epoch": 1792368045,
            "max_proof_ttl_seconds": 300,
            "signature_valid": True,
            "merchant_requested_fields": ["age_over_21", "residency_eu"],
            "required_predicates": ["age_over_21", "residency_eu"],
            "verified_predicates": {"age_over_21": True, "residency_eu": True},
        }
    )

    pci_res = scan_and_redact_agent_context_pii_pci(
        "User pasted raw Visa card 4242 4242 4242 4242 with CVV: 889 and key sk_live_9876543210abcdef in prompt"
    )

    pii_hash = hashlib.sha256(b"enc_blob_99a1|salt_01").hexdigest()
    fin_hash = hashlib.sha256(b"order_total_125000_ddp").hexdigest()
    expected_root = hashlib.sha256(f"{pii_hash}|{fin_hash}".encode("utf-8")).hexdigest()
    shred_res = verify_crypto_shredding_erasure_tombstone(
        {
            "principal_did": "did:web:buyer.example:alice",
            "kms_cek_id": "arn:aws:kms:eu-central-1:111122223333:key/cek-alice-01",
            "kms_cek_destroyed": True,
            "kms_destruction_receipt_sig": "kms_destroy_sig_ed25519_01",
            "plaintext_pii_still_present": False,
            "pii_leaf_ciphertext_hex": "enc_blob_99a1",
            "pii_leaf_salt": "salt_01",
            "financial_commitment_leaf_hash": fin_hash,
            "expected_merkle_root": expected_root,
        }
    )

    summary = {
        "stage": "stage17-zk-eligibility-pci-redaction-crypto-shredding",
        "zk_eligibility_decision": zk_res.decision_code,
        "zero_raw_pii_exposed": zk_res.zero_raw_pii_exposed,
        "pci_firewall_decision": pci_res.decision_code,
        "pci_redacted_preview": pci_res.redacted_text,
        "crypto_shredding_decision": shred_res.decision_code,
        "merkle_root_preserved": shred_res.merkle_root_preserved,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    _demo()
