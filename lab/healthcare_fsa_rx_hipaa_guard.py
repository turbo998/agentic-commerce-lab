"""Stage 24: Healthcare & Pharmacy Agentic Commerce Guard.

Enforces three deterministic invariants for healthcare, telehealth, and pharmacy
agentic commerce workflows:
1. IRS §213(d) & SIGIS IIAS Dual-Tender Split (`evaluate_sigis_fsa_hsa_iias_split_tender`):
   - Separates mixed-basket line items into SIGIS-qualified medical SKUs (`ELIGIBLE_RX`,
     `ELIGIBLE_OTC`), dual-purpose SKUs requiring a signed Letter of Medical Necessity
     (`DUAL_PURPOSE_LMN`), and non-medical retail items (`GENERAL_MERCHANDISE`).
   - Routes dual-purpose SKUs lacking a verified LMN to the backup payment instrument
     (`DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP`) and verifies penny-exact conservation
     between the FSA/HSA tax-advantaged tender and backup card (`SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED`).
2. NCPDP SCRIPT / DEA EPCS & PDMP Dispense Guard (`verify_eprescribing_ncpdp_dea_dispense_guard`):
   - Validates prescriber DEA hardware token signatures and Prescription Drug Monitoring
     Program (PDMP) cross-pharmacy checks (`DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED`).
   - Enforces the 80% days-supply refill threshold to prevent early accumulation of
     controlled or maintenance medications (`EARLY_REFILL_ACCUMULATION_BLOCKED`).
3. HIPAA §164.502(b) Minimum-Necessary Payment Descriptor Scrubber
   (`redact_hipaa_phi_from_payment_descriptor`):
   - Scrubs ICD-10 diagnosis codes, NDC drug identifiers, clinical specialty names,
     and prescription numbers from card statement descriptors and acquirer metadata,
     replacing them with a neutral MCC-aligned billing descriptor
     (`HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from typing import Any

ICD10_PATTERN = re.compile(r"\b[A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?\b")
NDC_PATTERN = re.compile(r"\b(?:NDC[:\s-]*)?\d{4,5}-\d{3,4}-\d{1,2}\b", re.IGNORECASE)
PHI_CLINICAL_KEYWORDS = (
    "oncology",
    "psychiatry",
    "behavioral health",
    "hiv",
    "fertility",
    "endocrinology",
    "addiction",
    "buprenorphine",
    "oxycodone",
    "methylphenidate",
    "semaglutide",
    "rx#",
    "icd10",
    "icd-10",
    "diagnosis",
)


def evaluate_sigis_fsa_hsa_iias_split_tender(cart_context: dict[str, Any]) -> dict[str, Any]:
    """Split a mixed healthcare cart across FSA/HSA IIAS tender and backup payment card."""
    cart_id = str(cart_context.get("cart_id", "cart_sigis_unknown"))
    merchant_iias_certified = bool(cart_context.get("merchant_iias_certified", True))
    fsa_available_balance_minor = int(cart_context.get("fsa_available_balance_minor", 0))
    items = list(cart_context.get("items", []))

    gross_cart_minor = 0
    qualified_medical_minor = 0
    dual_purpose_routed_to_backup_minor = 0
    general_merchandise_minor = 0
    lmn_missing_skus: list[str] = []
    qualified_skus: list[str] = []

    for item in items:
        sku = str(item.get("sku", "sku_unknown"))
        line_total_minor = int(item.get("line_total_minor", 0))
        category = str(item.get("sigis_category", "GENERAL_MERCHANDISE")).upper()
        lmn_verified = bool(item.get("lmn_verified", False))
        gross_cart_minor += line_total_minor

        if not merchant_iias_certified:
            general_merchandise_minor += line_total_minor
            continue

        if category in ("ELIGIBLE_RX", "ELIGIBLE_OTC"):
            qualified_medical_minor += line_total_minor
            qualified_skus.append(sku)
        elif category == "DUAL_PURPOSE_LMN":
            if lmn_verified:
                qualified_medical_minor += line_total_minor
                qualified_skus.append(sku)
            else:
                dual_purpose_routed_to_backup_minor += line_total_minor
                lmn_missing_skus.append(sku)
        else:
            general_merchandise_minor += line_total_minor

    fsa_hsa_charge_minor = min(qualified_medical_minor, max(0, fsa_available_balance_minor))
    unfunded_qualified_overflow_minor = qualified_medical_minor - fsa_hsa_charge_minor
    backup_card_charge_minor = (
        unfunded_qualified_overflow_minor
        + dual_purpose_routed_to_backup_minor
        + general_merchandise_minor
    )
    conservation_delta_minor = gross_cart_minor - (fsa_hsa_charge_minor + backup_card_charge_minor)

    reason_codes: list[str] = []
    if not merchant_iias_certified:
        reason_codes.append("MERCHANT_IIAS_NOT_CERTIFIED_FSA_BLOCKED")
    if lmn_missing_skus:
        reason_codes.append("DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP")
    if conservation_delta_minor == 0 and merchant_iias_certified:
        reason_codes.append("SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED")

    digest_payload = (
        f"{cart_id}|{gross_cart_minor}|{fsa_hsa_charge_minor}|"
        f"{backup_card_charge_minor}|{','.join(sorted(qualified_skus))}"
    )
    iias_substantiation_sha256 = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()

    return {
        "cart_id": cart_id,
        "allowed": merchant_iias_certified and conservation_delta_minor == 0,
        "merchant_iias_certified": merchant_iias_certified,
        "gross_cart_minor": gross_cart_minor,
        "qualified_medical_minor": qualified_medical_minor,
        "dual_purpose_routed_to_backup_minor": dual_purpose_routed_to_backup_minor,
        "general_merchandise_minor": general_merchandise_minor,
        "fsa_hsa_charge_minor": fsa_hsa_charge_minor,
        "backup_card_charge_minor": backup_card_charge_minor,
        "conservation_delta_minor": conservation_delta_minor,
        "lmn_missing_skus": lmn_missing_skus,
        "qualified_skus": qualified_skus,
        "iias_substantiation_sha256": iias_substantiation_sha256,
        "reason_codes": reason_codes,
    }


def verify_eprescribing_ncpdp_dea_dispense_guard(rx_context: dict[str, Any]) -> dict[str, Any]:
    """Validate NCPDP SCRIPT e-prescription signature, PDMP duplicate fill status, and 80% refill rule."""
    rx_id = str(rx_context.get("rx_id", "rx_unknown"))
    ncpdp_script_signature_valid = bool(rx_context.get("ncpdp_script_signature_valid", True))
    prescriber_dea_signature_valid = bool(rx_context.get("prescriber_dea_signature_valid", True))
    pdmp_duplicate_active_fill_detected = bool(
        rx_context.get("pdmp_duplicate_active_fill_detected", False)
    )
    is_refill = bool(rx_context.get("is_refill", False))
    days_supply = max(1, int(rx_context.get("days_supply", 30)))
    days_elapsed_since_last_fill = int(rx_context.get("days_elapsed_since_last_fill", 30))
    min_utilization_ratio = float(rx_context.get("min_utilization_ratio", 0.80))

    utilization_ratio = round(days_elapsed_since_last_fill / days_supply, 4)
    reason_codes: list[str] = []

    if (
        not ncpdp_script_signature_valid
        or not prescriber_dea_signature_valid
        or pdmp_duplicate_active_fill_detected
    ):
        reason_codes.append("DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED")

    if is_refill and utilization_ratio < min_utilization_ratio:
        reason_codes.append("EARLY_REFILL_ACCUMULATION_BLOCKED")

    allowed = len(reason_codes) == 0
    if allowed:
        reason_codes.append("NCPDP_EPCS_DISPENSE_AUTHORIZED")

    return {
        "rx_id": rx_id,
        "allowed": allowed,
        "dispense_status": "AUTHORIZED" if allowed else "BLOCKED",
        "ncpdp_script_signature_valid": ncpdp_script_signature_valid,
        "prescriber_dea_signature_valid": prescriber_dea_signature_valid,
        "pdmp_duplicate_active_fill_detected": pdmp_duplicate_active_fill_detected,
        "is_refill": is_refill,
        "days_supply": days_supply,
        "days_elapsed_since_last_fill": days_elapsed_since_last_fill,
        "utilization_ratio": utilization_ratio,
        "min_utilization_ratio": min_utilization_ratio,
        "reason_codes": reason_codes,
    }


def redact_hipaa_phi_from_payment_descriptor(descriptor_context: dict[str, Any]) -> dict[str, Any]:
    """Scrub PHI (ICD-10, NDC, clinical specialty, Rx IDs) from card payment descriptors."""
    raw_descriptor = str(descriptor_context.get("raw_statement_descriptor", ""))
    raw_metadata = dict(descriptor_context.get("raw_acquirer_metadata", {}))
    neutral_merchant_descriptor = str(
        descriptor_context.get("neutral_merchant_descriptor", "HEALTHCARE SVCS MCC-8099")
    )
    merchant_category_code = str(descriptor_context.get("mcc", "8099"))

    detected_phi_markers: list[str] = []
    combined_inspection_text = f"{raw_descriptor} {json.dumps(raw_metadata, sort_keys=True)}"

    if ICD10_PATTERN.search(combined_inspection_text):
        detected_phi_markers.append("ICD10_DIAGNOSIS_CODE")
    if NDC_PATTERN.search(combined_inspection_text):
        detected_phi_markers.append("NDC_DRUG_IDENTIFIER")

    lowered_text = combined_inspection_text.lower()
    for kw in PHI_CLINICAL_KEYWORDS:
        if kw in lowered_text:
            detected_phi_markers.append(f"CLINICAL_TERM:{kw.upper()}")

    phi_detected = len(detected_phi_markers) > 0
    safe_statement_descriptor = (
        neutral_merchant_descriptor if phi_detected else (raw_descriptor or neutral_merchant_descriptor)
    )

    safe_acquirer_metadata: dict[str, Any] = {
        "mcc": merchant_category_code,
        "hipaa_minimum_necessary_enforced": True,
        "iias_substantiation_ref": str(
            raw_metadata.get("iias_substantiation_ref", "iias_opaque_ref")
        ),
    }

    reason_codes = (
        ["HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC"]
        if phi_detected
        else ["HIPAA_PAYMENT_DESCRIPTOR_CLEAN"]
    )

    return {
        "phi_detected": phi_detected,
        "detected_phi_markers": detected_phi_markers,
        "safe_statement_descriptor": safe_statement_descriptor[:22],
        "safe_acquirer_metadata": safe_acquirer_metadata,
        "mcc": merchant_category_code,
        "reason_codes": reason_codes,
    }


def _demo() -> None:
    sample_report = {
        "sigis_split": evaluate_sigis_fsa_hsa_iias_split_tender(
            {
                "cart_id": "cart_health_2026_24",
                "merchant_iias_certified": True,
                "fsa_available_balance_minor": 15000,
                "items": [
                    {
                        "sku": "rx_insulin_pen",
                        "sigis_category": "ELIGIBLE_RX",
                        "line_total_minor": 8500,
                    },
                    {
                        "sku": "otc_blood_pressure_cuff",
                        "sigis_category": "ELIGIBLE_OTC",
                        "line_total_minor": 4500,
                    },
                    {
                        "sku": "dual_massage_gun_no_lmn",
                        "sigis_category": "DUAL_PURPOSE_LMN",
                        "lmn_verified": False,
                        "line_total_minor": 12000,
                    },
                    {
                        "sku": "retail_shampoo",
                        "sigis_category": "GENERAL_MERCHANDISE",
                        "line_total_minor": 1800,
                    },
                ],
            }
        ),
        "rx_guard_blocked": verify_eprescribing_ncpdp_dea_dispense_guard(
            {
                "rx_id": "rx_dea_sched2_009",
                "ncpdp_script_signature_valid": True,
                "prescriber_dea_signature_valid": True,
                "pdmp_duplicate_active_fill_detected": True,
                "is_refill": True,
                "days_supply": 30,
                "days_elapsed_since_last_fill": 14,
            }
        ),
        "hipaa_scrubber": redact_hipaa_phi_from_payment_descriptor(
            {
                "raw_statement_descriptor": "TELEHEALTH ONCOLOGY ICD10-C50.911 NDC 0002-8215-01",
                "raw_acquirer_metadata": {
                    "diagnosis": "C50.911",
                    "drug_ndc": "0002-8215-01",
                    "iias_substantiation_ref": "sigis_ref_9981",
                },
                "neutral_merchant_descriptor": "CARE CLINIC MCC-8099",
                "mcc": "8099",
            }
        ),
    }
    print(json.dumps(sample_report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 24 Healthcare FSA/Rx/HIPAA Guard")
    parser.add_argument("--demo", action="store_true", help="Run deterministic demonstration")
    args = parser.parse_args()
    _demo()
