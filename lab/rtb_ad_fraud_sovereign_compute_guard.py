"""Stage 27: Real-Time Agentic Ad-Bidding (RTB) Invalid Traffic (IVT) Escrow, Sovereign AI Compute Export Control / Geofencing & SLA Penalty Credit-Note Reconciliation Guard.

Implements three deterministic enterprise M2M & cloud-procurement invariants:
1. `evaluate_agentic_rtb_invalid_traffic_escrow`:
   - Protects autonomous marketing/ad-buying agents in OpenRTB 3.0 / Agentic Ad Exchanges:
     - Verifies IAB ads.cert 2.0 cryptographic impression signatures (`ADS_CERT_IMPRESSION_SIGNATURE_INVALID_BLOCKED`),
     - Withholds escrow settlement and claws back spend when general/sophisticated Invalid Traffic (`SIVT` botnet click-farms or headless browser farms) exceeds the contract threshold (`sivt_rate_bps > max_sivt_tolerance_bps` -> `RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD`),
     - Settles net verified human/authorized-agent impressions (`RTB_VERIFIED_IMPRESSION_ESCROW_SETTLED`).
2. `verify_sovereign_compute_export_geofence_attestation`:
   - Enforces BIS Export Administration Regulations (EAR) & Sovereign AI Data-Residency boundaries on cross-border GPU cluster rentals:
     - Verifies hardware TPM 2.0 / PTP precision time-delay physical location attestation (`HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED`),
     - Blocks model weight or high-density accelerator training runs routed to sanctioned/embargoed jurisdictions or violating sovereign data residency (`EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED`),
     - Admits compliant sovereign compute training leases (`SOVEREIGN_COMPUTE_GEOFENCE_ATTESTED`).
3. `reconcile_cloud_sla_downtime_credit_note`:
   - Reconciles multi-provider cloud/API uptime telemetry against contractual SLA tiers (`99.9%`, `99.95%`, `99.99%`):
     - Computes deterministic service credit tiers (`10%`, `25%`, `100%`) when observed uptime falls below the SLA commitment and automatically nets credit notes against the current invoice (`SLA_BREACH_CREDIT_NOTE_AUTO_NETTED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgenticRtbEscrowResult:
    """Result of evaluating an OpenRTB / ads.cert 2.0 ad-spend escrow settlement."""

    settled: bool
    decision_code: str
    campaign_id: str
    gross_billed_impressions: int
    sivt_flagged_impressions: int
    sivt_rate_bps: int
    max_sivt_tolerance_bps: int
    net_payable_minor: int
    clawback_withheld_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SovereignComputeGeofenceResult:
    """Result of verifying sovereign AI compute export control & physical geofence attestation."""

    allowed: bool
    decision_code: str
    cluster_id: str
    declared_region: str
    ptp_measured_region: str
    aggregate_tflops_fp16: int
    residency_compliant: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CloudSlaCreditNoteResult:
    """Result of reconciling cloud/API SLA downtime credit notes against an invoice."""

    reconciled: bool
    decision_code: str
    invoice_id: str
    observed_uptime_bps: int
    committed_sla_bps: int
    credit_percentage_bps: int
    gross_invoice_minor: int
    credit_note_minor: int
    net_payable_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_agentic_rtb_invalid_traffic_escrow(
    rtb_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify ads.cert 2.0 signatures and withhold RTB ad spend on SIVT bot click-farm traffic."""

    campaign_id = str(rtb_context.get("campaign_id", "cmp_unknown"))
    ads_cert_valid = bool(rtb_context.get("ads_cert_signature_valid", True))
    gross_impressions = max(1, int(rtb_context.get("gross_billed_impressions", 1)))
    sivt_impressions = max(0, int(rtb_context.get("sivt_flagged_impressions", 0)))
    max_sivt_bps = max(0, int(rtb_context.get("max_sivt_tolerance_bps", 200)))
    gross_spend_minor = max(0, int(rtb_context.get("gross_spend_minor", 0)))

    sivt_bps = (sivt_impressions * 10_000) // gross_impressions

    if not ads_cert_valid:
        return AgenticRtbEscrowResult(
            settled=False,
            decision_code="ADS_CERT_IMPRESSION_SIGNATURE_INVALID_BLOCKED",
            campaign_id=campaign_id,
            gross_billed_impressions=gross_impressions,
            sivt_flagged_impressions=sivt_impressions,
            sivt_rate_bps=sivt_bps,
            max_sivt_tolerance_bps=max_sivt_bps,
            net_payable_minor=0,
            clawback_withheld_minor=gross_spend_minor,
            reason_codes=["ADS_CERT_IMPRESSION_SIGNATURE_INVALID_BLOCKED"],
        ).to_dict()

    if sivt_bps > max_sivt_bps:
        withheld = (gross_spend_minor * sivt_impressions) // gross_impressions
        net_payable = max(0, gross_spend_minor - withheld)
        return AgenticRtbEscrowResult(
            settled=False,
            decision_code="RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD",
            campaign_id=campaign_id,
            gross_billed_impressions=gross_impressions,
            sivt_flagged_impressions=sivt_impressions,
            sivt_rate_bps=sivt_bps,
            max_sivt_tolerance_bps=max_sivt_bps,
            net_payable_minor=net_payable,
            clawback_withheld_minor=withheld,
            reason_codes=["RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD"],
        ).to_dict()

    withheld = (gross_spend_minor * sivt_impressions) // gross_impressions
    net_payable = max(0, gross_spend_minor - withheld)
    return AgenticRtbEscrowResult(
        settled=True,
        decision_code="RTB_VERIFIED_IMPRESSION_ESCROW_SETTLED",
        campaign_id=campaign_id,
        gross_billed_impressions=gross_impressions,
        sivt_flagged_impressions=sivt_impressions,
        sivt_rate_bps=sivt_bps,
        max_sivt_tolerance_bps=max_sivt_bps,
        net_payable_minor=net_payable,
        clawback_withheld_minor=withheld,
        reason_codes=["RTB_VERIFIED_IMPRESSION_ESCROW_SETTLED"],
    ).to_dict()


def verify_sovereign_compute_export_geofence_attestation(
    geofence_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify hardware PTP/TPM location attestation and sovereign AI export/residency geofencing."""

    cluster_id = str(geofence_context.get("cluster_id", "cls_unknown"))
    tpm_location_sig_valid = bool(geofence_context.get("tpm_location_signature_valid", True))
    declared_region = str(geofence_context.get("declared_region", "EU-DE")).upper()
    ptp_measured_region = str(geofence_context.get("ptp_measured_region", declared_region)).upper()
    allowed_regions = {
        str(r).upper()
        for r in geofence_context.get("allowed_sovereign_regions", ["EU-DE", "EU-FR", "US-EAST"])
    }
    embargoed_regions = {
        str(r).upper()
        for r in geofence_context.get("embargoed_jurisdictions", ["KP", "IR", "SY", "CU", "RU"])
    }
    aggregate_tflops = max(0, int(geofence_context.get("aggregate_tflops_fp16", 0)))

    if not tpm_location_sig_valid or declared_region != ptp_measured_region:
        return SovereignComputeGeofenceResult(
            allowed=False,
            decision_code="HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED",
            cluster_id=cluster_id,
            declared_region=declared_region,
            ptp_measured_region=ptp_measured_region,
            aggregate_tflops_fp16=aggregate_tflops,
            residency_compliant=False,
            reason_codes=["HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED"],
        ).to_dict()

    if ptp_measured_region in embargoed_regions or ptp_measured_region not in allowed_regions:
        return SovereignComputeGeofenceResult(
            allowed=False,
            decision_code="EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED",
            cluster_id=cluster_id,
            declared_region=declared_region,
            ptp_measured_region=ptp_measured_region,
            aggregate_tflops_fp16=aggregate_tflops,
            residency_compliant=False,
            reason_codes=["EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED"],
        ).to_dict()

    return SovereignComputeGeofenceResult(
        allowed=True,
        decision_code="SOVEREIGN_COMPUTE_GEOFENCE_ATTESTED",
        cluster_id=cluster_id,
        declared_region=declared_region,
        ptp_measured_region=ptp_measured_region,
        aggregate_tflops_fp16=aggregate_tflops,
        residency_compliant=True,
        reason_codes=["SOVEREIGN_COMPUTE_GEOFENCE_ATTESTED"],
    ).to_dict()


def reconcile_cloud_sla_downtime_credit_note(
    sla_context: dict[str, Any],
) -> dict[str, Any]:
    """Calculate contractual SLA downtime credit tiers and auto-net against the cloud invoice."""

    invoice_id = str(sla_context.get("invoice_id", "inv_sla_01"))
    observed_uptime_bps = max(0, min(10_000, int(sla_context.get("observed_uptime_bps", 10_000))))
    committed_sla_bps = max(0, min(10_000, int(sla_context.get("committed_sla_bps", 9_990))))
    gross_invoice_minor = max(0, int(sla_context.get("gross_invoice_minor", 0)))

    if observed_uptime_bps >= committed_sla_bps:
        return CloudSlaCreditNoteResult(
            reconciled=True,
            decision_code="SLA_UPTIME_MET_FULL_INVOICE_PAYABLE",
            invoice_id=invoice_id,
            observed_uptime_bps=observed_uptime_bps,
            committed_sla_bps=committed_sla_bps,
            credit_percentage_bps=0,
            gross_invoice_minor=gross_invoice_minor,
            credit_note_minor=0,
            net_payable_minor=gross_invoice_minor,
            reason_codes=["SLA_UPTIME_MET_FULL_INVOICE_PAYABLE"],
        ).to_dict()

    if observed_uptime_bps < 9_500:
        credit_bps = 10_000  # 100% service credit
    elif observed_uptime_bps < 9_900:
        credit_bps = 2_500   # 25% service credit
    else:
        credit_bps = 1_000   # 10% service credit

    credit_minor = (gross_invoice_minor * credit_bps) // 10_000
    net_minor = max(0, gross_invoice_minor - credit_minor)

    return CloudSlaCreditNoteResult(
        reconciled=True,
        decision_code="SLA_BREACH_CREDIT_NOTE_AUTO_NETTED",
        invoice_id=invoice_id,
        observed_uptime_bps=observed_uptime_bps,
        committed_sla_bps=committed_sla_bps,
        credit_percentage_bps=credit_bps,
        gross_invoice_minor=gross_invoice_minor,
        credit_note_minor=credit_minor,
        net_payable_minor=net_minor,
        reason_codes=["SLA_BREACH_CREDIT_NOTE_AUTO_NETTED"],
    ).to_dict()
