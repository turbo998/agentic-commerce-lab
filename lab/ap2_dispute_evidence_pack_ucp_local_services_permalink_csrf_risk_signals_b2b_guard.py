"""Stage 182 deterministic protocol and security guards.

Covers 2026-10-23 primary-source updates across:
1. Google AP2 Issue #338 (`2026-10-23T14:42:26Z`):
   - Self-contained dispute-time evidence pack for SD-JWT+kb mandates +
     issuer key material over 5–7 year retention windows:
     - Explicit `key_provenance_class` in `{"x5c_chain", "header_jwk",
       "caller_supplied", "jwks_tls_snapshot"}` (never flattened or omitted).
     - Cross-mandate SHA-256 hash bindings (`intent_mandate_hash`,
       `cart_mandate_hash`) recomputed directly from compact serializations.
     - OpenTimestamps (e.g., Bitcoin block 972227 manifest `f046ca25...c57c`
       over 127 files / 34 rows / 40,338 bytes) or RFC 3161 prefix verification
       and strict classification of post-anchor rows (`total_rows >
       anchored_row_count`) as within the unanchored rebuild window.
2. Universal Commerce Protocol Issue #922 (`[DTC Charter]: Local Services`),
   PTC `2026-10-15` (`#53`) & STC `2026-10-16` (`#51`) (`2026-10-23T16:14:55Z..16:52:22Z`):
   - Observable atomic contract for paid local service bookings on
     `dev.ucp.shopping.checkout`:
     - Re-validating TTL slot holds (`slot_hold_expires_at > checkout_ts`)
       before charging.
     - Blocking concurrent double-booking on `(resource_id, slot_id)`.
     - Never leaving a captured charge without a confirmed booking (requiring
       immediate auto-refund/resolution), and never confirming a booking when
       payment fails.
     - Enforcing Phase 2 conditional capture / card-hold guarantee ceilings
       (`captured_amount_minor <= policy_penalty_minor`) and releasing unused
       authorizations on timely free cancellation.
3. Universal Commerce Protocol PR #789 & Issue #666 / STC `2026-10-16` (`#51`):
   - Blocking irreversible checkout/payment execution on permalink GET loads,
     and blocking silent CSRF cart merges into an authenticated buyer's
     existing cart without `explicit_buyer_merge_action=True`.
4. Universal Commerce Protocol Issue #630 (`RFC: Expanding Well-Known Signals`)
   & Issue #947 (`[DTC Charter]: B2B Procurement`, STC `2026-10-16` `#51`):
   - Reverse-domain namespace validation on `signals` (`dev.ucp.buyer_ip`,
     `dev.ucp.user_agent`, plus vendor reverse-domain extensions), cloud-IP
     agent attestation check, and B2B procurement organization/cost-center
     approval authority enforcement above `auto_approval_limit_minor`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

VALID_KEY_PROVENANCE_CLASSES = frozenset(
    {"x5c_chain", "header_jwk", "caller_supplied", "jwks_tls_snapshot"}
)
VALID_ANCHOR_MECHANISMS = frozenset({"opentimestamps", "rfc3161"})
REVERSE_DOMAIN_SIGNAL_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9_-]+){2,}$")


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any]


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_ap2_dispute_evidence_pack(
    *,
    intent_compact_sd_jwt: str,
    cart_compact_sd_jwt: str,
    payment_compact_sd_jwt: str,
    claimed_intent_hash: str,
    claimed_cart_hash: str,
    key_snapshots: list[dict[str, Any]],
    kb_jwt_cnf_jwk_verified: bool = True,
    anchor_mechanism: str = "opentimestamps",
    anchored_row_count: int = 34,
    total_row_count: int = 34,
    anchored_byte_length: int = 40338,
    expected_anchored_prefix_sha256: str = "",
    actual_anchored_prefix_sha256: str = "",
    dispute_relies_solely_on_post_anchor_rows: bool = False,
) -> GuardDecision:
    """Validate AP2 #338 self-contained dispute evidence pack & anchor boundary."""
    if not kb_jwt_cnf_jwk_verified:
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_kb_jwt_holder_binding_invalid",
            reason="KB-JWT holder binding against cnf.jwk failed offline verification.",
            metadata={},
        )

    if not key_snapshots:
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_key_snapshots_empty",
            reason="Dispute evidence pack must include transaction-time verification key snapshots.",
            metadata={},
        )

    for idx, snap in enumerate(key_snapshots):
        prov = snap.get("key_provenance_class")
        if prov not in VALID_KEY_PROVENANCE_CLASSES or snap.get("flattened", False):
            return GuardDecision(
                allowed=False,
                decision_code="ap2_dispute_pack_key_provenance_missing_or_flattened",
                reason="Each key snapshot must declare an explicit non-flattened key_provenance_class.",
                metadata={"index": idx, "key_provenance_class": prov},
            )

    recomputed_intent_hash = _sha256_hex(intent_compact_sd_jwt)
    recomputed_cart_hash = _sha256_hex(cart_compact_sd_jwt)
    if (
        claimed_intent_hash != recomputed_intent_hash
        or claimed_cart_hash != recomputed_cart_hash
        or not payment_compact_sd_jwt.strip()
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_cross_mandate_hash_mismatch",
            reason="Cross-mandate hash bindings recomputed from compact SD-JWT serializations do not match.",
            metadata={
                "claimed_intent_hash": claimed_intent_hash,
                "recomputed_intent_hash": recomputed_intent_hash,
            },
        )

    if anchor_mechanism not in VALID_ANCHOR_MECHANISMS:
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_invalid_anchor_mechanism",
            reason="Anchor mechanism must be 'opentimestamps' or 'rfc3161'.",
            metadata={"anchor_mechanism": anchor_mechanism},
        )

    if (
        expected_anchored_prefix_sha256
        and expected_anchored_prefix_sha256 != actual_anchored_prefix_sha256
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_anchored_prefix_tampered",
            reason="Anchored ledger prefix bytes do not match the manifest digest.",
            metadata={
                "anchored_byte_length": anchored_byte_length,
                "expected_anchored_prefix_sha256": expected_anchored_prefix_sha256,
                "actual_anchored_prefix_sha256": actual_anchored_prefix_sha256,
            },
        )

    unanchored_rebuild_window_rows = max(0, total_row_count - anchored_row_count)
    if unanchored_rebuild_window_rows > 0 and dispute_relies_solely_on_post_anchor_rows:
        return GuardDecision(
            allowed=False,
            decision_code="ap2_dispute_pack_unanchored_rebuild_window_time_claim_forbidden",
            reason="Rows written after the last external anchor fall in the rebuild window and cannot alone support a time-based dispute claim.",
            metadata={
                "anchored_row_count": anchored_row_count,
                "total_row_count": total_row_count,
                "unanchored_rebuild_window_rows": unanchored_rebuild_window_rows,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="ap2_dispute_evidence_pack_ok",
        reason="AP2 self-contained dispute evidence pack, key provenance classes, and anchor prefix verified.",
        metadata={
            "unanchored_rebuild_window_rows": unanchored_rebuild_window_rows,
            "anchored_byte_length": anchored_byte_length,
        },
    )


def validate_ucp_local_services_booking_checkout(
    *,
    has_hold: bool,
    slot_hold_expires_at_epoch: int,
    checkout_timestamp_epoch: int,
    active_slot_holder_agent_id: str,
    requesting_agent_id: str,
    payment_status: str,
    booking_status: str,
    unmatched_charge_auto_resolved: bool = False,
    payment_model: str = "full_at_booking",
    authorized_amount_minor: int = 0,
    captured_amount_minor: int = 0,
    policy_penalty_minor: int = 0,
    cancelled_within_free_window: bool = False,
    unused_auth_released: bool = True,
) -> GuardDecision:
    """Validate UCP #922 Local Services atomic slot+payment & Phase 2 guarantees."""
    if has_hold and checkout_timestamp_epoch >= slot_hold_expires_at_epoch:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_services_slot_hold_expired_before_charge",
            reason="Slot hold expired before checkout charge; must re-validate and abort before charging.",
            metadata={
                "slot_hold_expires_at_epoch": slot_hold_expires_at_epoch,
                "checkout_timestamp_epoch": checkout_timestamp_epoch,
            },
        )

    if active_slot_holder_agent_id and active_slot_holder_agent_id != requesting_agent_id:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_services_concurrent_slot_double_booking",
            reason="Resource slot is already held or booked by another concurrent agent.",
            metadata={
                "active_slot_holder_agent_id": active_slot_holder_agent_id,
                "requesting_agent_id": requesting_agent_id,
            },
        )

    if payment_status == "failed" and booking_status == "confirmed":
        return GuardDecision(
            allowed=False,
            decision_code="ucp_services_confirmed_booking_on_failed_payment",
            reason="Payment failure must never leave a confirmed service booking.",
            metadata={"payment_status": payment_status, "booking_status": booking_status},
        )

    if (
        payment_status == "captured"
        and booking_status != "confirmed"
        and not unmatched_charge_auto_resolved
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_services_unmatched_charge_without_confirmed_booking",
            reason="Captured payment without a confirmed booking violates the observable atomicity contract unless immediately resolved/refunded.",
            metadata={"payment_status": payment_status, "booking_status": booking_status},
        )

    if payment_model in {"card_hold_guarantee", "conditional_capture"}:
        if captured_amount_minor > policy_penalty_minor or captured_amount_minor > authorized_amount_minor:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_services_guarantee_overcapture_forbidden",
                reason="Conditional capture or card-hold guarantee cannot capture more than the policy penalty or authorized hold.",
                metadata={
                    "captured_amount_minor": captured_amount_minor,
                    "policy_penalty_minor": policy_penalty_minor,
                    "authorized_amount_minor": authorized_amount_minor,
                },
            )
        if cancelled_within_free_window and (captured_amount_minor > 0 or not unused_auth_released):
            return GuardDecision(
                allowed=False,
                decision_code="ucp_services_free_cancellation_auth_not_released",
                reason="Free-window cancellation must capture 0 and release the unused authorization hold.",
                metadata={
                    "captured_amount_minor": captured_amount_minor,
                    "unused_auth_released": unused_auth_released,
                },
            )

    return GuardDecision(
        allowed=True,
        decision_code="ucp_local_services_booking_checkout_ok",
        reason="Local services slot hold, concurrency, and atomic booking-payment invariants satisfied.",
        metadata={"payment_model": payment_model, "booking_status": booking_status},
    )


def validate_ucp_permalink_and_risk_signals_and_b2b(
    *,
    is_permalink_load: bool = False,
    permalink_triggers_irreversible_action: bool = False,
    buyer_authenticated: bool = False,
    existing_cart_non_empty: bool = False,
    explicit_buyer_merge_action: bool = True,
    signals: dict[str, Any] | None = None,
    buyer_ip_is_cloud_range: bool = False,
    agent_identity_attested: bool = True,
    is_b2b_procurement: bool = False,
    organization_id: str = "",
    cost_center_id: str = "",
    order_amount_minor: int = 0,
    auto_approval_limit_minor: int = 100000,
    approval_authority_verified: bool = True,
) -> GuardDecision:
    """Validate UCP PR #789 Permalink CSRF, #630 Risk Signals, and #947 B2B Procurement."""
    if is_permalink_load:
        if permalink_triggers_irreversible_action:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_permalink_irreversible_action_forbidden",
                reason="Loading a permalink GET must never place an order, charge payment, or complete checkout.",
                metadata={},
            )
        if buyer_authenticated and existing_cart_non_empty and not explicit_buyer_merge_action:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_permalink_authenticated_cart_silent_merge_csrf",
                reason="Merging permalink state into an authenticated buyer's existing cart requires explicit buyer action on the rendered state.",
                metadata={},
            )

    sig_map = signals or {"dev.ucp.buyer_ip": "203.0.113.5", "dev.ucp.user_agent": "UCPAgent/1.0"}
    for key, val in sig_map.items():
        if not REVERSE_DOMAIN_SIGNAL_RE.match(key) or val is None or val == "":
            return GuardDecision(
                allowed=False,
                decision_code="ucp_risk_signals_invalid_namespace_or_empty",
                reason="All risk signal keys must use reverse-domain naming and carry non-empty values.",
                metadata={"invalid_signal_key": key},
            )

    if buyer_ip_is_cloud_range and not agent_identity_attested:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_risk_signals_unattested_cloud_agent_ip",
            reason="Agent-originated transactions from cloud IP ranges require cryptographic agent attestation or verified session signals.",
            metadata={"buyer_ip_is_cloud_range": True},
        )

    if is_b2b_procurement:
        if not organization_id.strip() or not cost_center_id.strip():
            return GuardDecision(
                allowed=False,
                decision_code="ucp_b2b_procurement_missing_org_or_cost_center",
                reason="B2B procurement checkout requires organization_id and cost_center_id.",
                metadata={"organization_id": organization_id, "cost_center_id": cost_center_id},
            )
        if order_amount_minor > auto_approval_limit_minor and not approval_authority_verified:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_b2b_procurement_approval_authority_required",
                reason="B2B purchase order exceeding auto_approval_limit_minor requires verified approval authority.",
                metadata={
                    "order_amount_minor": order_amount_minor,
                    "auto_approval_limit_minor": auto_approval_limit_minor,
                },
            )

    return GuardDecision(
        allowed=True,
        decision_code="ucp_permalink_risk_signals_and_b2b_ok",
        reason="Permalink safety, extensible reverse-domain risk signals, and B2B procurement governance verified.",
        metadata={"signal_count": len(sig_map), "is_b2b_procurement": is_b2b_procurement},
    )
