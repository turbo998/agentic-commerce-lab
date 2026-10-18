"""Stage 10: Enterprise B2B 3-Way Match (`PO == GRN == Invoice`), Split-Shipment Partial
Capture Escrow, Beneficiary Hijack / Sanctions Screening & Dynamic Discounting (`2/10 Net 30`) Guard.

Implements deterministic verification for:
1. Split-Shipment Partial Capture & Milestone Escrow (`UNFULFILLED_BACKORDER_CAPTURE_VIOLATION`):
   - Prevents capturing funds for backordered / unshipped or damaged/rejected quantities.
   - Only `qty_accepted = max(0, qty_delivered - qty_rejected_damaged)` may be billed or captured.
2. Deterministic 3-Way Match (`PO Mandate == GRN == e-Invoice`):
   - `qty_invoiced <= qty_accepted` (blocks `THREE_WAY_MATCH_QTY_OVERBILL`)
   - `unit_price_invoiced_minor <= unit_price_po_minor` (blocks `THREE_WAY_MATCH_UNIT_PRICE_DRIFT`, 0 bps positive price drift tolerance)
   - `freight_tax_invoiced_minor <= po_freight_tax_allowance_minor * (1 + max_ancillary_variance_bps / 10000)`
     (blocks `THREE_WAY_MATCH_ANCILLARY_VARIANCE_EXCEEDED`)
3. Beneficiary Endpoint Hijack (BEC) & OFAC Sanctions Screening:
   - Invoice payout endpoint (`stripe_connect_account_id`, `iban`, or `wallet_address`) must match
     the KYB-attested vendor master fingerprint (`BENEFICIARY_ENDPOINT_HIJACK_BLOCKED`).
   - Blocks sanctioned entities or wallets (`SANCTIONS_SCREENING_HIT`).
4. Dynamic Cash Discounting Implied APR Actuarial Calculator (`evaluate_dynamic_discounting_apr`):
     APR_implied = (d / (1 - d)) * (365 / (T_net - T_disc))
   - E.g. `2/10 Net 30` -> (0.02 / 0.98) * (365 / 20) = 37.2449% implied risk-free annualized return.
   - Triggers early settlement on day `T_disc` when `APR_implied >= treasury_hurdle_apr_pct` and
     3-way match is verified.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_prefixed(payload: Any) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class B2BThreeWayMatchResult:
    settlement_approved: bool
    decision_code: str
    po_id: str
    invoice_id: str
    authorized_po_total_minor: int
    accepted_grn_merchandise_minor: int
    invoiced_merchandise_minor: int
    invoiced_ancillary_minor: int
    approved_partial_capture_minor: int
    remaining_escrow_hold_minor: int
    beneficiary_verified: bool
    sanctions_clear: bool
    reasons: list[str] = field(default_factory=list)
    reconciliation_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DynamicDiscountingDecision:
    take_early_discount: bool
    decision_code: str
    discount_rate_bps: int
    discount_day: int
    net_due_day: int
    accelerated_days: int
    implied_apr_pct: float
    treasury_hurdle_apr_pct: float
    net_spread_apr_pct: float
    gross_invoice_minor: int
    discounted_settlement_minor: int
    savings_minor: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_b2b_three_way_match_and_escrow(
    po_mandate: Mapping[str, Any],
    grn_receipt: Mapping[str, Any],
    e_invoice: Mapping[str, Any],
    vendor_master: Mapping[str, Any],
    *,
    sanctioned_endpoints: set[str] | None = None,
    max_ancillary_variance_bps: int = 100,
) -> B2BThreeWayMatchResult:
    """Verify B2B 3-way match (`PO == GRN == e-Invoice`), split-shipment partial capture,
    beneficiary endpoint integrity (BEC defense), and sanctions screening.
    """
    reasons: list[str] = []
    sanctioned = sanctioned_endpoints or set()

    po_id = str(po_mandate.get("po_id") or "po_unknown")
    invoice_id = str(e_invoice.get("invoice_id") or "inv_unknown")

    # 1. Sanctions & Beneficiary Endpoint Hijack (BEC) verification
    inv_endpoint = str(e_invoice.get("payout_endpoint_id") or "").strip()
    kyb_endpoint = str(vendor_master.get("kyb_verified_endpoint_id") or "").strip()
    vendor_sanctioned = bool(vendor_master.get("ofac_sanctioned", False)) or (
        inv_endpoint in sanctioned
    )
    sanctions_clear = not vendor_sanctioned
    if not sanctions_clear:
        reasons.append(
            f"SANCTIONS_SCREENING_HIT: vendor or payout endpoint {inv_endpoint!r} matched sanctions blocklist."
        )

    beneficiary_verified = bool(inv_endpoint) and inv_endpoint == kyb_endpoint
    if not beneficiary_verified:
        reasons.append(
            f"BENEFICIARY_ENDPOINT_HIJACK_BLOCKED: invoice payout endpoint {inv_endpoint!r} does not match KYB vendor master {kyb_endpoint!r}."
        )

    # 2. Index PO lines, GRN lines, and Invoice lines by SKU
    po_lines = {
        str(line["sku"]): line for line in po_mandate.get("lines", []) if "sku" in line
    }
    grn_lines = {
        str(line["sku"]): line for line in grn_receipt.get("lines", []) if "sku" in line
    }
    inv_lines = list(e_invoice.get("lines", []))

    authorized_po_merch_minor = sum(
        int(line.get("qty_ordered", 0)) * int(line.get("unit_price_minor", 0))
        for line in po_lines.values()
    )
    po_ancillary_allowance_minor = int(po_mandate.get("ancillary_allowance_minor", 0))
    authorized_po_total_minor = authorized_po_merch_minor + po_ancillary_allowance_minor

    accepted_grn_merch_minor = 0
    for sku, po_line in po_lines.items():
        grn_line = grn_lines.get(sku, {})
        qty_deliv = int(grn_line.get("qty_delivered", 0))
        qty_rej = int(grn_line.get("qty_rejected_damaged", 0))
        qty_acc = max(0, qty_deliv - qty_rej)
        accepted_grn_merch_minor += qty_acc * int(po_line.get("unit_price_minor", 0))

    invoiced_merch_minor = 0
    for inv_line in inv_lines:
        sku = str(inv_line.get("sku") or "")
        qty_inv = int(inv_line.get("qty_invoiced", 0))
        price_inv = int(inv_line.get("unit_price_minor", 0))
        invoiced_merch_minor += qty_inv * price_inv

        if sku not in po_lines:
            reasons.append(f"THREE_WAY_MATCH_UNORDERED_SKU: invoice SKU {sku!r} not in PO.")
            continue

        po_line = po_lines[sku]
        qty_ordered = int(po_line.get("qty_ordered", 0))
        price_po = int(po_line.get("unit_price_minor", 0))

        grn_line = grn_lines.get(sku, {})
        qty_delivered = int(grn_line.get("qty_delivered", 0))
        qty_rejected = int(grn_line.get("qty_rejected_damaged", 0))
        qty_accepted = max(0, qty_delivered - qty_rejected)

        # Check unfulfilled backorder premature capture attempt
        if qty_inv > qty_delivered and qty_delivered < qty_ordered:
            reasons.append(
                f"UNFULFILLED_BACKORDER_CAPTURE_VIOLATION: SKU {sku!r} invoiced qty ({qty_inv}) includes unshipped backorder (delivered={qty_delivered}, ordered={qty_ordered})."
            )
        # Check damaged/rejected overbilling
        elif qty_inv > qty_accepted:
            reasons.append(
                f"THREE_WAY_MATCH_QTY_OVERBILL: SKU {sku!r} invoiced qty ({qty_inv}) exceeds GRN accepted qty ({qty_accepted} = delivered {qty_delivered} - rejected {qty_rejected})."
            )

        # Check zero positive unit-price tolerance
        if price_inv > price_po:
            reasons.append(
                f"THREE_WAY_MATCH_UNIT_PRICE_DRIFT: SKU {sku!r} invoiced unit price ({price_inv}) exceeds PO contract price ({price_po})."
            )

    # 3. Check ancillary (freight/tax) tolerance corridor
    invoiced_ancillary_minor = int(e_invoice.get("ancillary_charges_minor", 0))
    max_allowed_ancillary = (
        po_ancillary_allowance_minor * (10_000 + max_ancillary_variance_bps)
    ) // 10_000
    if invoiced_ancillary_minor > max_allowed_ancillary:
        reasons.append(
            f"THREE_WAY_MATCH_ANCILLARY_VARIANCE_EXCEEDED: invoiced ancillary ({invoiced_ancillary_minor}) exceeds PO allowance + {max_ancillary_variance_bps} bps ({max_allowed_ancillary})."
        )

    # 4. Check capture request against verified invoice total
    requested_capture_minor = int(
        e_invoice.get(
            "requested_capture_minor",
            invoiced_merch_minor + invoiced_ancillary_minor,
        )
    )
    max_capturable_now = accepted_grn_merch_minor + min(
        invoiced_ancillary_minor, max_allowed_ancillary
    )
    if requested_capture_minor > max_capturable_now and not any(
        r.startswith("UNFULFILLED_BACKORDER_CAPTURE_VIOLATION") for r in reasons
    ):
        reasons.append(
            f"ESCROW_OVER_CAPTURE_BLOCKED: requested_capture_minor ({requested_capture_minor}) exceeds GRN-backed capturable ceiling ({max_capturable_now})."
        )

    settlement_approved = len(reasons) == 0
    if settlement_approved:
        approved_capture = requested_capture_minor
        remaining_escrow = max(0, authorized_po_total_minor - approved_capture)
        decision_code = (
            "THREE_WAY_MATCH_PARTIAL_CAPTURE_APPROVED"
            if remaining_escrow > 0
            else "THREE_WAY_MATCH_FULL_CAPTURE_APPROVED"
        )
    else:
        approved_capture = 0
        remaining_escrow = authorized_po_total_minor
        decision_code = reasons[0].split(":", 1)[0]

    digest = _sha256_prefixed(
        {
            "po_id": po_id,
            "invoice_id": invoice_id,
            "decision_code": decision_code,
            "approved_capture": approved_capture,
            "remaining_escrow": remaining_escrow,
        }
    )

    return B2BThreeWayMatchResult(
        settlement_approved=settlement_approved,
        decision_code=decision_code,
        po_id=po_id,
        invoice_id=invoice_id,
        authorized_po_total_minor=authorized_po_total_minor,
        accepted_grn_merchandise_minor=accepted_grn_merch_minor,
        invoiced_merchandise_minor=invoiced_merch_minor,
        invoiced_ancillary_minor=invoiced_ancillary_minor,
        approved_partial_capture_minor=approved_capture,
        remaining_escrow_hold_minor=remaining_escrow,
        beneficiary_verified=beneficiary_verified,
        sanctions_clear=sanctions_clear,
        reasons=reasons,
        reconciliation_digest=digest,
    )


def evaluate_dynamic_discounting_apr(
    *,
    gross_invoice_minor: int,
    discount_rate_bps: int,
    discount_day: int,
    net_due_day: int,
    treasury_hurdle_apr_pct: float = 8.0,
    three_way_match_verified: bool = True,
) -> DynamicDiscountingDecision:
    """Calculate implied annualized return (APR) of early payment discount terms (e.g. 2/10 Net 30).

    Formula:
      APR_implied = (d / (1 - d)) * (365 / (T_net - T_disc)) * 100
    """
    accelerated_days = max(1, net_due_day - discount_day)
    d = discount_rate_bps / 10_000.0
    if d <= 0.0 or d >= 1.0:
        implied_apr_pct = 0.0
    else:
        implied_apr_pct = round((d / (1.0 - d)) * (365.0 / accelerated_days) * 100.0, 4)

    savings_minor = (gross_invoice_minor * discount_rate_bps) // 10_000
    discounted_settlement_minor = gross_invoice_minor - savings_minor
    net_spread = round(implied_apr_pct - treasury_hurdle_apr_pct, 4)

    if not three_way_match_verified:
        take_early = False
        code = "HOLD_FOR_THREE_WAY_MATCH_RESOLUTION"
    elif implied_apr_pct >= treasury_hurdle_apr_pct:
        take_early = True
        code = "ACCELERATE_SETTLEMENT_CAPTURE_DISCOUNT"
    else:
        take_early = False
        code = "PAY_ON_NET_DUE_DATE_BELOW_HURDLE"

    return DynamicDiscountingDecision(
        take_early_discount=take_early,
        decision_code=code,
        discount_rate_bps=discount_rate_bps,
        discount_day=discount_day,
        net_due_day=net_due_day,
        accelerated_days=accelerated_days,
        implied_apr_pct=implied_apr_pct,
        treasury_hurdle_apr_pct=treasury_hurdle_apr_pct,
        net_spread_apr_pct=net_spread,
        gross_invoice_minor=gross_invoice_minor,
        discounted_settlement_minor=discounted_settlement_minor,
        savings_minor=savings_minor,
    )


def run_demo_scenarios() -> list[dict[str, Any]]:
    """Run deterministic Stage 10 B2B 3-way match, BEC defense, and 2/10 Net 30 scenarios."""
    scenarios: list[dict[str, Any]] = []

    # 1. Compliant split-shipment partial capture (60 of 100 units delivered, 0 damaged)
    s1 = verify_b2b_three_way_match_and_escrow(
        po_mandate={
            "po_id": "po_gpu_rack_01",
            "ancillary_allowance_minor": 50_000,
            "lines": [{"sku": "sku_h200_node", "qty_ordered": 10, "unit_price_minor": 200_000}],
        },
        grn_receipt={
            "lines": [{"sku": "sku_h200_node", "qty_delivered": 6, "qty_rejected_damaged": 0}]
        },
        e_invoice={
            "invoice_id": "inv_gpu_part1",
            "payout_endpoint_id": "acct_connect_kyb_vendor_01",
            "ancillary_charges_minor": 30_000,
            "lines": [{"sku": "sku_h200_node", "qty_invoiced": 6, "unit_price_minor": 200_000}],
        },
        vendor_master={
            "kyb_verified_endpoint_id": "acct_connect_kyb_vendor_01",
            "ofac_sanctioned": False,
        },
    )
    scenarios.append({"scenario_id": "S10_01_PARTIAL_SHIPMENT_3WAY_OK", **s1.to_dict()})

    # 2. Unfulfilled backorder + BEC payout endpoint hijack attempt
    s2 = verify_b2b_three_way_match_and_escrow(
        po_mandate={
            "po_id": "po_gpu_rack_01",
            "ancillary_allowance_minor": 50_000,
            "lines": [{"sku": "sku_h200_node", "qty_ordered": 10, "unit_price_minor": 200_000}],
        },
        grn_receipt={
            "lines": [{"sku": "sku_h200_node", "qty_delivered": 6, "qty_rejected_damaged": 1}]
        },
        e_invoice={
            "invoice_id": "inv_hijacked_full",
            "payout_endpoint_id": "acct_attacker_spoofed_99",
            "ancillary_charges_minor": 50_000,
            "lines": [{"sku": "sku_h200_node", "qty_invoiced": 10, "unit_price_minor": 205_000}],
        },
        vendor_master={
            "kyb_verified_endpoint_id": "acct_connect_kyb_vendor_01",
            "ofac_sanctioned": False,
        },
    )
    scenarios.append({"scenario_id": "S10_02_BEC_AND_BACKORDER_OVERBILL_BLOCKED", **s2.to_dict()})

    # 3. Dynamic discounting 2/10 Net 30 (37.2449% implied APR vs 8.0% treasury hurdle)
    s3 = evaluate_dynamic_discounting_apr(
        gross_invoice_minor=1_230_000,
        discount_rate_bps=200,  # 2%
        discount_day=10,
        net_due_day=30,
        treasury_hurdle_apr_pct=8.0,
        three_way_match_verified=s1.settlement_approved,
    )
    scenarios.append({"scenario_id": "S10_03_2_10_NET_30_DYNAMIC_DISCOUNT", **s3.to_dict()})

    return scenarios


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 10 B2B 3-Way Match, Escrow & Dynamic Discounting Guard demo."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    results = run_demo_scenarios()
    if args.json:
        print(json.dumps({"scenarios": results}, indent=2))
    else:
        print("=== Stage 10: B2B 3-Way Match, Split-Shipment Escrow & Dynamic Discounting ===")
        for item in results:
            print(f"  [{item['scenario_id']}] decision={item['decision_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
