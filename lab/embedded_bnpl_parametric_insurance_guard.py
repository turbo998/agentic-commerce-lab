"""Stage 20: Embedded BNPL / B2B Trade-Credit Underwriting, Parametric SLA Microinsurance & Invoice Factoring Double-Pledge Guard.

Implements three deterministic production guardrails for Agentic Commerce working-capital financing,
embedded parametric insurance, and B2B receivable factoring:
1. Embedded BNPL & B2B Net-Terms Underwriting (`evaluate_agentic_bnpl_trade_credit_underwriting`):
   - Verifies Debt Service Coverage Ratio (`dscr >= 1.35`), open-banking real-time cash buffer,
     and cross-issuer BNPL stacking velocity (`concurrent_active_bnpl_issuers <= max_concurrent_issuers`),
     blocking phantom multi-issuer over-indebtedness (`MULTI_ISSUER_BNPL_STACKING_BLOCKED`).
   - Uses Largest Remainder Method to generate an exact integer-cent installment schedule where
     `sum(installment_principal_minor) == financed_principal_minor`.
2. Parametric SLA Microinsurance Instant Settlement (`evaluate_parametric_sla_microinsurance_claim`):
   - Verifies multi-oracle quorum signatures (`oracle_quorum_signatures >= 2`) and deterministic
     threshold breach (`actual_metric >= policy_trigger_threshold`) for instant no-adjuster payout
     (`PARAMETRIC_INSTANT_PAYOUT_SETTLED`).
   - Enforces the Indemnity Principle to block double-dipping when the buyer already received a
     merchant refund or SLA credit (`DOUBLE_DIP_INDEMNITY_BLOCKED`).
3. B2B Invoice Factoring UCC Lien & Double-Pledge Guard (`verify_invoice_factoring_ucc_lien_uniqueness`):
   - Computes a canonical SHA-256 invoice fingerprint and verifies global lien registry uniqueness
     plus buyer ERP Notice of Assignment (NOA) lock, blocking double-pledging fraud
     (`INVOICE_DOUBLE_PLEDGING_BLOCKED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class BnplTradeCreditDecision:
    approved: bool
    decision_code: str
    applicant_id: str
    credit_mode: str
    financed_principal_minor: int
    installment_count: int
    installment_principal_minor: list[int]
    principal_conservation_delta_minor: int
    dscr: str
    concurrent_active_bnpl_issuers: int
    post_purchase_dti_bps: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParametricInsuranceClaimDecision:
    payout_approved: bool
    decision_code: str
    policy_id: str
    hazard_type: str
    oracle_quorum_signatures: int
    actual_metric: str
    policy_trigger_threshold: str
    verified_economic_loss_minor: int
    merchant_already_refunded_minor: int
    approved_payout_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InvoiceFactoringLienDecision:
    allowed: bool
    decision_code: str
    invoice_id: str
    canonical_invoice_sha256: str
    requesting_factor_id: str
    existing_pledged_factor_id: str | None
    notice_of_assignment_locked: bool
    approved_advance_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_agentic_bnpl_trade_credit_underwriting(
    credit_request: dict[str, Any],
) -> BnplTradeCreditDecision:
    """Underwrite B2C 4-Pay BNPL or B2B Net-30/60 trade credit and generate exact schedule."""
    applicant_id = str(credit_request.get("applicant_id", "buyer_unknown"))
    credit_mode = str(credit_request.get("credit_mode", "BNPL_4PAY"))
    principal = int(credit_request.get("financed_principal_minor", 0))
    installment_count = max(int(credit_request.get("installment_count", 4)), 1)
    dscr = Decimal(str(credit_request.get("dscr", "1.50")))
    min_dscr = Decimal(str(credit_request.get("min_dscr", "1.35")))
    concurrent_issuers = int(credit_request.get("concurrent_active_bnpl_issuers", 0))
    max_concurrent_issuers = int(credit_request.get("max_concurrent_bnpl_issuers", 2))
    post_dti_bps = int(credit_request.get("post_purchase_dti_bps", 2500))
    max_dti_bps = int(credit_request.get("max_dti_bps", 4000))
    cash_buffer = int(credit_request.get("available_cash_buffer_minor", principal))
    min_cash_buffer = int(credit_request.get("required_cash_buffer_minor", principal // max(installment_count, 1)))

    # 1. Cross-Issuer BNPL Stacking & Debt Velocity Check
    if concurrent_issuers > max_concurrent_issuers or post_dti_bps > max_dti_bps:
        return BnplTradeCreditDecision(
            approved=False,
            decision_code="MULTI_ISSUER_BNPL_STACKING_BLOCKED",
            applicant_id=applicant_id,
            credit_mode=credit_mode,
            financed_principal_minor=principal,
            installment_count=installment_count,
            installment_principal_minor=[],
            principal_conservation_delta_minor=0,
            dscr=f"{dscr:.2f}",
            concurrent_active_bnpl_issuers=concurrent_issuers,
            post_purchase_dti_bps=post_dti_bps,
            reason=(
                f"Applicant has {concurrent_issuers} active BNPL issuers (max {max_concurrent_issuers}) "
                f"or post-purchase DTI {post_dti_bps} bps > {max_dti_bps} bps."
            ),
        )

    # 2. DSCR & Open-Banking Cash Buffer Check
    if dscr < min_dscr or cash_buffer < min_cash_buffer:
        return BnplTradeCreditDecision(
            approved=False,
            decision_code="INSUFFICIENT_DSCR_OR_CASH_BUFFER_DECLINED",
            applicant_id=applicant_id,
            credit_mode=credit_mode,
            financed_principal_minor=principal,
            installment_count=installment_count,
            installment_principal_minor=[],
            principal_conservation_delta_minor=0,
            dscr=f"{dscr:.2f}",
            concurrent_active_bnpl_issuers=concurrent_issuers,
            post_purchase_dti_bps=post_dti_bps,
            reason=(
                f"DSCR ({dscr:.2f} < {min_dscr:.2f}) or open-banking cash buffer "
                f"({cash_buffer} < {min_cash_buffer} minor) insufficient."
            ),
        )

    # 3. Deterministic Largest-Remainder Installment Principal Schedule
    base_share = principal // installment_count
    remainder = principal % installment_count
    schedule = [base_share + (1 if i < remainder else 0) for i in range(installment_count)]
    delta = principal - sum(schedule)

    return BnplTradeCreditDecision(
        approved=True,
        decision_code="BNPL_TRADE_CREDIT_APPROVED",
        applicant_id=applicant_id,
        credit_mode=credit_mode,
        financed_principal_minor=principal,
        installment_count=installment_count,
        installment_principal_minor=schedule,
        principal_conservation_delta_minor=delta,
        dscr=f"{dscr:.2f}",
        concurrent_active_bnpl_issuers=concurrent_issuers,
        post_purchase_dti_bps=post_dti_bps,
        reason="Underwriting approved; exact installment schedule generated with zero rounding drift.",
    )


def evaluate_parametric_sla_microinsurance_claim(
    claim_context: dict[str, Any],
) -> ParametricInsuranceClaimDecision:
    """Evaluate multi-oracle parametric SLA insurance claim and enforce Indemnity Principle."""
    policy_id = str(claim_context.get("policy_id", "pol_unknown"))
    hazard_type = str(claim_context.get("hazard_type", "CLOUD_SLA_DOWNTIME_MINUTES"))
    quorum_sigs = int(claim_context.get("oracle_quorum_signatures", 0))
    min_quorum = int(claim_context.get("min_oracle_quorum", 2))
    actual_metric = Decimal(str(claim_context.get("actual_metric", "0")))
    threshold = Decimal(str(claim_context.get("policy_trigger_threshold", "30")))
    economic_loss = int(claim_context.get("verified_economic_loss_minor", 0))
    merchant_refunded = int(claim_context.get("merchant_already_refunded_minor", 0))
    scheduled_benefit = int(claim_context.get("scheduled_parametric_benefit_minor", economic_loss))

    if quorum_sigs < min_quorum:
        return ParametricInsuranceClaimDecision(
            payout_approved=False,
            decision_code="INSUFFICIENT_ORACLE_QUORUM_SIGNATURES",
            policy_id=policy_id,
            hazard_type=hazard_type,
            oracle_quorum_signatures=quorum_sigs,
            actual_metric=str(actual_metric),
            policy_trigger_threshold=str(threshold),
            verified_economic_loss_minor=economic_loss,
            merchant_already_refunded_minor=merchant_refunded,
            approved_payout_minor=0,
            reason=f"Oracle quorum signatures ({quorum_sigs}) below required minimum ({min_quorum}).",
        )

    if actual_metric < threshold:
        return ParametricInsuranceClaimDecision(
            payout_approved=False,
            decision_code="PARAMETRIC_THRESHOLD_NOT_REACHED",
            policy_id=policy_id,
            hazard_type=hazard_type,
            oracle_quorum_signatures=quorum_sigs,
            actual_metric=str(actual_metric),
            policy_trigger_threshold=str(threshold),
            verified_economic_loss_minor=economic_loss,
            merchant_already_refunded_minor=merchant_refunded,
            approved_payout_minor=0,
            reason=f"Observed metric ({actual_metric}) below policy trigger threshold ({threshold}).",
        )

    # Indemnity Principle: Buyer cannot profit by double-dipping merchant refund + insurance payout
    unindemnified_loss = max(economic_loss - merchant_refunded, 0)
    if unindemnified_loss == 0 or merchant_refunded + scheduled_benefit > economic_loss:
        return ParametricInsuranceClaimDecision(
            payout_approved=False,
            decision_code="DOUBLE_DIP_INDEMNITY_BLOCKED",
            policy_id=policy_id,
            hazard_type=hazard_type,
            oracle_quorum_signatures=quorum_sigs,
            actual_metric=str(actual_metric),
            policy_trigger_threshold=str(threshold),
            verified_economic_loss_minor=economic_loss,
            merchant_already_refunded_minor=merchant_refunded,
            approved_payout_minor=0,
            reason=(
                f"Indemnity violation: buyer already received {merchant_refunded} minor from merchant "
                f"against {economic_loss} minor loss; proposed payout ({scheduled_benefit}) would double-dip."
            ),
        )

    payout = min(scheduled_benefit, unindemnified_loss)
    return ParametricInsuranceClaimDecision(
        payout_approved=True,
        decision_code="PARAMETRIC_INSTANT_PAYOUT_SETTLED",
        policy_id=policy_id,
        hazard_type=hazard_type,
        oracle_quorum_signatures=quorum_sigs,
        actual_metric=str(actual_metric),
        policy_trigger_threshold=str(threshold),
        verified_economic_loss_minor=economic_loss,
        merchant_already_refunded_minor=merchant_refunded,
        approved_payout_minor=payout,
        reason="Oracle quorum and parametric threshold verified; instant payout settled within indemnity cap.",
    )


def verify_invoice_factoring_ucc_lien_uniqueness(
    factoring_request: dict[str, Any],
) -> InvoiceFactoringLienDecision:
    """Verify B2B invoice SHA-256 fingerprint against global lien registry to block double-pledging."""
    invoice_id = str(factoring_request.get("invoice_id", "inv_unknown"))
    seller_id = str(factoring_request.get("seller_id", "acct_seller"))
    buyer_id = str(factoring_request.get("buyer_id", "buyer_corp"))
    invoice_number = str(factoring_request.get("invoice_number", invoice_id))
    invoice_total = int(factoring_request.get("invoice_total_minor", 0))
    issue_date = str(factoring_request.get("issue_date", "2026-10-19"))
    requesting_factor = str(factoring_request.get("requesting_factor_id", "factor_alpha"))
    advance_rate_bps = int(factoring_request.get("advance_rate_bps", 8500))
    noa_locked = bool(factoring_request.get("notice_of_assignment_locked", True))
    pledged_registry: dict[str, str] = dict(factoring_request.get("global_lien_registry", {}))

    canonical_payload = f"{seller_id}|{buyer_id}|{invoice_number}|{invoice_total}|{issue_date}"
    fingerprint = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    existing_factor = pledged_registry.get(fingerprint) or pledged_registry.get(invoice_id)
    if existing_factor is not None and existing_factor != requesting_factor:
        return InvoiceFactoringLienDecision(
            allowed=False,
            decision_code="INVOICE_DOUBLE_PLEDGING_BLOCKED",
            invoice_id=invoice_id,
            canonical_invoice_sha256=fingerprint,
            requesting_factor_id=requesting_factor,
            existing_pledged_factor_id=existing_factor,
            notice_of_assignment_locked=noa_locked,
            approved_advance_minor=0,
            reason=(
                f"Invoice '{invoice_id}' (fingerprint {fingerprint[:12]}...) is already pledged "
                f"to factor '{existing_factor}'."
            ),
        )

    if not noa_locked:
        return InvoiceFactoringLienDecision(
            allowed=False,
            decision_code="NOTICE_OF_ASSIGNMENT_UNLOCKED_BLOCKED",
            invoice_id=invoice_id,
            canonical_invoice_sha256=fingerprint,
            requesting_factor_id=requesting_factor,
            existing_pledged_factor_id=None,
            notice_of_assignment_locked=False,
            approved_advance_minor=0,
            reason="Buyer ERP has not countersigned Notice of Assignment (NOA) payment redirection lock.",
        )

    advance_minor = (invoice_total * advance_rate_bps) // 10_000
    return InvoiceFactoringLienDecision(
        allowed=True,
        decision_code="INVOICE_FACTORING_LIEN_REGISTERED",
        invoice_id=invoice_id,
        canonical_invoice_sha256=fingerprint,
        requesting_factor_id=requesting_factor,
        existing_pledged_factor_id=None,
        notice_of_assignment_locked=True,
        approved_advance_minor=advance_minor,
        reason="Canonical invoice lien verified unique and NOA locked; factoring advance approved.",
    )


def main() -> None:
    bnpl = evaluate_agentic_bnpl_trade_credit_underwriting(
        {
            "applicant_id": "buyer_corp_20",
            "credit_mode": "BNPL_4PAY",
            "financed_principal_minor": 10001,
            "installment_count": 4,
            "dscr": "1.65",
            "concurrent_active_bnpl_issuers": 1,
            "post_purchase_dti_bps": 2400,
            "available_cash_buffer_minor": 8000,
        }
    )
    claim = evaluate_parametric_sla_microinsurance_claim(
        {
            "policy_id": "pol_sla_gpu_20",
            "hazard_type": "GPU_CLUSTER_SLA_DOWNTIME_MINUTES",
            "oracle_quorum_signatures": 3,
            "actual_metric": "47.5",
            "policy_trigger_threshold": "30.0",
            "verified_economic_loss_minor": 50000,
            "merchant_already_refunded_minor": 0,
            "scheduled_parametric_benefit_minor": 50000,
        }
    )
    double_pledge = verify_invoice_factoring_ucc_lien_uniqueness(
        {
            "invoice_id": "inv_2026_9001",
            "seller_id": "acct_seller_01",
            "buyer_id": "buyer_enterprise_01",
            "invoice_number": "INV-2026-9001",
            "invoice_total_minor": 2500000,
            "issue_date": "2026-10-19",
            "requesting_factor_id": "factor_beta",
            "notice_of_assignment_locked": True,
            "global_lien_registry": {"inv_2026_9001": "factor_alpha"},
        }
    )
    summary = {
        "stage": "stage20-embedded-bnpl-parametric-insurance-guard",
        "bnpl_decision": bnpl.decision_code,
        "bnpl_schedule_minor": bnpl.installment_principal_minor,
        "parametric_claim_decision": claim.decision_code,
        "parametric_payout_minor": claim.approved_payout_minor,
        "factoring_double_pledge_decision": double_pledge.decision_code,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
