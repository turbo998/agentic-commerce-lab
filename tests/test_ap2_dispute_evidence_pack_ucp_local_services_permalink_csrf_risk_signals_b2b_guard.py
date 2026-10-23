"""Unit tests for Stage 182 deterministic guard module."""

from __future__ import annotations

import hashlib
import unittest

from lab.ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_guard import (
    validate_ap2_dispute_evidence_pack,
    validate_ucp_local_services_booking_checkout,
    validate_ucp_permalink_and_risk_signals_and_b2b,
)


class TestStage182Guard(unittest.TestCase):
    def test_ap2_dispute_evidence_pack(self) -> None:
        intent = "eyJhbGciOiJFUzI1NiJ9.intent~disc1~"
        cart = "eyJhbGciOiJFUzI1NiJ9.cart~disc2~"
        payment = "eyJhbGciOiJFUzI1NiJ9.payment~disc3~kbjwt"
        i_hash = hashlib.sha256(intent.encode("utf-8")).hexdigest()
        c_hash = hashlib.sha256(cart.encode("utf-8")).hexdigest()

        ok = validate_ap2_dispute_evidence_pack(
            intent_compact_sd_jwt=intent,
            cart_compact_sd_jwt=cart,
            payment_compact_sd_jwt=payment,
            claimed_intent_hash=i_hash,
            claimed_cart_hash=c_hash,
            key_snapshots=[
                {"kid": "k1", "key_provenance_class": "x5c_chain"},
                {"kid": "k2", "key_provenance_class": "jwks_tls_snapshot"},
            ],
            anchor_mechanism="opentimestamps",
            anchored_row_count=34,
            total_row_count=42,
            anchored_byte_length=40338,
            expected_anchored_prefix_sha256="ddaeea7a",
            actual_anchored_prefix_sha256="ddaeea7a",
            dispute_relies_solely_on_post_anchor_rows=False,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.metadata["unanchored_rebuild_window_rows"], 8)

        flattened = validate_ap2_dispute_evidence_pack(
            intent_compact_sd_jwt=intent,
            cart_compact_sd_jwt=cart,
            payment_compact_sd_jwt=payment,
            claimed_intent_hash=i_hash,
            claimed_cart_hash=c_hash,
            key_snapshots=[{"kid": "k1", "key_provenance_class": "x5c_chain", "flattened": True}],
        )
        self.assertFalse(flattened.allowed)
        self.assertEqual(
            flattened.decision_code,
            "ap2_dispute_pack_key_provenance_missing_or_flattened",
        )

        rebuild_window = validate_ap2_dispute_evidence_pack(
            intent_compact_sd_jwt=intent,
            cart_compact_sd_jwt=cart,
            payment_compact_sd_jwt=payment,
            claimed_intent_hash=i_hash,
            claimed_cart_hash=c_hash,
            key_snapshots=[{"kid": "k1", "key_provenance_class": "x5c_chain"}],
            anchored_row_count=34,
            total_row_count=42,
            dispute_relies_solely_on_post_anchor_rows=True,
        )
        self.assertFalse(rebuild_window.allowed)
        self.assertEqual(
            rebuild_window.decision_code,
            "ap2_dispute_pack_unanchored_rebuild_window_time_claim_forbidden",
        )

    def test_ucp_local_services_booking_checkout(self) -> None:
        ok = validate_ucp_local_services_booking_checkout(
            has_hold=True,
            slot_hold_expires_at_epoch=1761265000,
            checkout_timestamp_epoch=1761264500,
            active_slot_holder_agent_id="agent_a",
            requesting_agent_id="agent_a",
            payment_status="captured",
            booking_status="confirmed",
        )
        self.assertTrue(ok.allowed)

        expired = validate_ucp_local_services_booking_checkout(
            has_hold=True,
            slot_hold_expires_at_epoch=1761264000,
            checkout_timestamp_epoch=1761264500,
            active_slot_holder_agent_id="agent_a",
            requesting_agent_id="agent_a",
            payment_status="captured",
            booking_status="confirmed",
        )
        self.assertFalse(expired.allowed)
        self.assertEqual(expired.decision_code, "ucp_services_slot_hold_expired_before_charge")

        unmatched = validate_ucp_local_services_booking_checkout(
            has_hold=True,
            slot_hold_expires_at_epoch=1761265000,
            checkout_timestamp_epoch=1761264500,
            active_slot_holder_agent_id="agent_a",
            requesting_agent_id="agent_a",
            payment_status="captured",
            booking_status="failed_conflict",
            unmatched_charge_auto_resolved=False,
        )
        self.assertFalse(unmatched.allowed)
        self.assertEqual(
            unmatched.decision_code,
            "ucp_services_unmatched_charge_without_confirmed_booking",
        )

    def test_ucp_permalink_and_risk_signals_and_b2b(self) -> None:
        ok = validate_ucp_permalink_and_risk_signals_and_b2b(
            is_permalink_load=True,
            permalink_triggers_irreversible_action=False,
            buyer_authenticated=True,
            existing_cart_non_empty=True,
            explicit_buyer_merge_action=True,
            signals={
                "dev.ucp.buyer_ip": "34.102.136.180",
                "dev.ucp.user_agent": "ShopifyAgent/2.0",
                "com.stripe.risk.session_attestation": "att_991",
            },
            buyer_ip_is_cloud_range=True,
            agent_identity_attested=True,
            is_b2b_procurement=True,
            organization_id="org_enterprise_01",
            cost_center_id="cc_rd_402",
            order_amount_minor=250000,
            auto_approval_limit_minor=100000,
            approval_authority_verified=True,
        )
        self.assertTrue(ok.allowed)

        csrf = validate_ucp_permalink_and_risk_signals_and_b2b(
            is_permalink_load=True,
            buyer_authenticated=True,
            existing_cart_non_empty=True,
            explicit_buyer_merge_action=False,
        )
        self.assertFalse(csrf.allowed)
        self.assertEqual(csrf.decision_code, "ucp_permalink_authenticated_cart_silent_merge_csrf")


if __name__ == "__main__":
    unittest.main()
