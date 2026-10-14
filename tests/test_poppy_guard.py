"""Unit tests for Poppy v0.1 discovery/token verification and Sierra retail mutation guards."""

import unittest

from lab.poppy_guard import (
    CatalogVariant,
    DPoPProof,
    PaymentInstrument,
    RetailOrder,
    RetailOrderMutationGuard,
    SessionToken,
    StandingPermission,
    run_demo,
    sha256_token,
    verify_poppy_discovery,
    verify_poppy_request_token,
)


class PoppyDiscoveryAndTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.poppy_doc = {
            "protocol_version": "0.1",
            "organization": {"name": "Manzanita Supply", "domain": "manzanitasupply.example"},
            "auth": {
                "issuer": "https://auth.manzanitasupply.example",
                "direct": {"scopes": ["poppy:read", "poppy:write", "addresses"]},
                "device": {"scopes": ["poppy:read", "poppy:write"]},
                "mediated": {"scopes": ["poppy:read"]},
            },
        }
        self.oauth_meta = {
            "issuer": "https://auth.manzanitasupply.example",
            "poppy_domains": ["manzanitasupply.example", "manzanitasupply.co.uk"],
        }

    def test_discovery_verifies_mutual_issuer_and_domain(self) -> None:
        res = verify_poppy_discovery(
            "https://www.manzanitasupply.example/.well-known/poppy.json",
            self.poppy_doc,
            self.oauth_meta,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason, "verified")

        spoofed_meta = {
            "issuer": "https://auth.manzanitasupply.example",
            "poppy_domains": ["othercompany.example"],
        }
        spoofed = verify_poppy_discovery(
            "https://manzanitasupply.example/.well-known/poppy.json",
            self.poppy_doc,
            spoofed_meta,
        )
        self.assertFalse(spoofed.allowed)
        self.assertEqual(spoofed.reason, "issuer_domain_unverified")

    def test_discovery_rejects_unsupported_major_version_or_bad_host(self) -> None:
        v1_doc = {**self.poppy_doc, "protocol_version": "1.0"}
        res = verify_poppy_discovery(
            "https://manzanitasupply.example/.well-known/poppy.json",
            v1_doc,
            self.oauth_meta,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.reason, "unsupported_major_version")

        mismatch = verify_poppy_discovery(
            "https://attacker.example/.well-known/poppy.json",
            self.poppy_doc,
            self.oauth_meta,
        )
        self.assertFalse(mismatch.allowed)
        self.assertEqual(mismatch.reason, "organization_domain_mismatch")

    def test_dpop_required_for_openapi_and_resource_bound_bearer_for_mcp(self) -> None:
        dpop_token = SessionToken(
            access_token="tok_dpop_1",
            token_type="DPoP",
            session_id="ses_1",
            client_id="https://agent.example/agent.json",
            user_id="usr_1",
            signed_in=True,
            account_id="cust_1",
            scopes=frozenset({"poppy:read", "poppy:write"}),
            sign_in_method="direct",
            jwk_thumbprint="jkt_1",
            expires_at=2000,
        )
        url = "https://api.manzanitasupply.example/orders/ord_1/exchanges?draft=true"
        proof = DPoPProof(
            jti="jti_unique_1",
            htm="POST",
            htu="https://api.manzanitasupply.example/orders/ord_1/exchanges",
            iat=1000,
            ath=sha256_token("tok_dpop_1"),
            jwk_thumbprint="jkt_1",
        )
        seen: set[str] = set()
        ok = verify_poppy_request_token(
            token=dpop_token,
            channel="openapi",
            http_method="POST",
            target_url=url,
            now=1005,
            poppy_auth_config=self.poppy_doc["auth"],
            required_scopes={"poppy:write"},
            dpop_proof=proof,
            seen_jti=seen,
        )
        self.assertTrue(ok.allowed)

        # Replaying same jti is rejected
        replay = verify_poppy_request_token(
            token=dpop_token,
            channel="openapi",
            http_method="POST",
            target_url=url,
            now=1006,
            poppy_auth_config=self.poppy_doc["auth"],
            required_scopes={"poppy:write"},
            dpop_proof=proof,
            seen_jti=seen,
        )
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.error, "invalid_dpop_proof")

        # MCP requires resource-bound Bearer token
        mcp_url = "https://mcp.manzanitasupply.example/mcp"
        mcp_token = SessionToken(
            access_token="tok_mcp_1",
            token_type="Bearer",
            session_id="ses_1",
            client_id="https://agent.example/agent.json",
            user_id="usr_1",
            signed_in=True,
            account_id="cust_1",
            scopes=frozenset({"poppy:read"}),
            sign_in_method="mediated",
            resource=mcp_url,
            expires_at=2000,
        )
        mcp_ok = verify_poppy_request_token(
            token=mcp_token,
            channel="mcp",
            http_method="POST",
            target_url=mcp_url,
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
            required_scopes={"poppy:read"},
        )
        self.assertTrue(mcp_ok.allowed)

        # Bearer token rejected on OpenAPI channel
        bearer_on_api = verify_poppy_request_token(
            token=mcp_token,
            channel="openapi",
            http_method="GET",
            target_url="https://api.manzanitasupply.example/orders",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
        )
        self.assertFalse(bearer_on_api.allowed)
        self.assertEqual(bearer_on_api.error, "dpop_required")

    def test_mediated_sign_in_cannot_exceed_declared_scope_cap(self) -> None:
        overprivileged = SessionToken(
            access_token="tok_med_write",
            token_type="DPoP",
            session_id="ses_2",
            client_id="https://agent.example/agent.json",
            user_id="usr_1",
            signed_in=True,
            account_id="cust_1",
            scopes=frozenset({"poppy:read", "poppy:write"}),
            sign_in_method="mediated",
            jwk_thumbprint="jkt_2",
            expires_at=2000,
        )
        res = verify_poppy_request_token(
            token=overprivileged,
            channel="openapi",
            http_method="POST",
            target_url="https://api.manzanitasupply.example/orders",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.error, "invalid_scope")


class RetailOrderMutationGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = RetailOrderMutationGuard(
            company_domain="manzanitasupply.example",
            catalog={
                "jkt-m": CatalogVariant("jkt-m", "prod-jkt", "Storm Jacket M", 10000, 2),
                "jkt-l": CatalogVariant("jkt-l", "prod-jkt", "Storm Jacket L", 11500, 1),
                "jkt-xl": CatalogVariant("jkt-xl", "prod-jkt", "Storm Jacket XL", 13000, 0),
                "hat-os": CatalogVariant("hat-os", "prod-hat", "Wool Hat", 4000, 5),
            },
            orders={
                "ord_pending": RetailOrder(
                    order_id="ord_pending",
                    customer_id="cust_alice",
                    status="pending",
                    items={"line_1": "jkt-m"},
                    original_payment_method_id="card_orig",
                ),
                "ord_delivered": RetailOrder(
                    order_id="ord_delivered",
                    customer_id="cust_alice",
                    status="delivered",
                    items={"line_1": "jkt-m"},
                    original_payment_method_id="card_orig",
                ),
                "ord_bob": RetailOrder(
                    order_id="ord_bob",
                    customer_id="cust_bob",
                    status="pending",
                    items={"line_1": "jkt-m"},
                    original_payment_method_id="card_bob",
                ),
            },
            payment_methods={
                "cust_alice": {
                    "card_orig": PaymentInstrument("card_orig", "card"),
                    "gc_small": PaymentInstrument("gc_small", "gift_card", balance_cents=500),
                    "gc_large": PaymentInstrument("gc_large", "gift_card", balance_cents=5000),
                    "paypal_alt": PaymentInstrument("paypal_alt", "paypal"),
                },
                "cust_bob": {
                    "card_bob": PaymentInstrument("card_bob", "card"),
                },
            },
        )
        self.alice_token = SessionToken(
            access_token="tok_alice",
            token_type="DPoP",
            session_id="ses_alice",
            client_id="https://agent.example/agent.json",
            user_id="usr_alice",
            signed_in=True,
            account_id="cust_alice",
            scopes=frozenset({"poppy:read", "poppy:write"}),
            sign_in_method="direct",
            jwk_thumbprint="jkt_alice",
            expires_at=5000,
        )

    def test_enforces_sign_in_scope_and_single_customer_session_lock(self) -> None:
        guest_token = SessionToken(
            access_token="tok_guest",
            token_type="DPoP",
            session_id="ses_guest",
            client_id="https://agent.example/agent.json",
            user_id="usr_alice",
            signed_in=False,
            account_id=None,
            scopes=frozenset(),
            expires_at=5000,
        )
        res_guest = self.guard.propose_item_change(
            token=guest_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertEqual(res_guest.code, "sign_in_required")

        read_only = SessionToken(
            **{**self.alice_token.__dict__, "scopes": frozenset({"poppy:read"})}
        )
        res_ro = self.guard.propose_item_change(
            token=read_only,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertEqual(res_ro.code, "insufficient_scope")

        # Cross-customer access in same session is blocked with account_mismatch
        cross_cust = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_bob",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="card_bob",
            now=1000,
        )
        self.assertEqual(cross_cust.code, "account_mismatch")

    def test_enforces_tau2_retail_domain_invariants(self) -> None:
        # Same variant swap forbidden
        same_var = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-m",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertEqual(same_var.code, "same_variant_swap_forbidden")

        # Cross-product swap forbidden
        cross_prod = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="hat-os",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertEqual(cross_prod.code, "cross_product_swap_forbidden")

        # Out of stock variant rejected
        oos = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-xl",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertEqual(oos.code, "out_of_stock")

        # Non-original non-gift-card payment method (e.g. PayPal) rejected
        bad_pm = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="paypal_alt",
            now=1000,
        )
        self.assertEqual(bad_pm.code, "unsupported_payment_method")

        # Insufficient gift card balance for positive price difference ($15.00 > $5.00)
        low_gc = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="gc_small",
            now=1000,
        )
        self.assertEqual(low_gc.code, "insufficient_gift_card_balance")

    def test_operations_revision_standing_permission_and_idempotent_confirm(self) -> None:
        prop = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_delivered",
            action="exchange_delivered_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="gc_small",
            now=1000,
        )
        self.assertFalse(prop.allowed)
        self.assertEqual(prop.code, "insufficient_gift_card_balance")

        prop_ok = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_delivered",
            action="exchange_delivered_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="card_orig",
            now=1000,
        )
        self.assertTrue(prop_ok.allowed)
        op_id = prop_ok.operation["operation_id"]

        # Revise payment method to gc_large -> increments revision to 2
        rev = self.guard.revise_operation(
            token=self.alice_token,
            operation_id=op_id,
            replacement_item_id="jkt-l",
            payment_method_id="gc_large",
            now=1010,
        )
        self.assertTrue(rev.allowed)
        self.assertEqual(rev.operation["revision"], 2)

        # Confirming stale revision 1 fails with terms_changed
        stale = self.guard.confirm_operation(
            token=self.alice_token,
            operation_id=op_id,
            revision=1,
            approved_by="user",
            now=1020,
        )
        self.assertFalse(stale.allowed)
        self.assertEqual(stale.code, "terms_changed")

        # Standing permission with max $10.00 cannot approve $15.00 price difference
        perm_low = StandingPermission(
            company_domain="manzanitasupply.example",
            account_id="cust_alice",
            allowed_actions=frozenset({"exchange_delivered_order_items"}),
            max_price_difference_cents=1000,
            expires_at=2000,
        )
        perm_fail = self.guard.confirm_operation(
            token=self.alice_token,
            operation_id=op_id,
            revision=2,
            approved_by="permission",
            now=1020,
            standing_permission=perm_low,
        )
        self.assertFalse(perm_fail.allowed)
        self.assertEqual(perm_fail.code, "user_approval_required")

        # Standing permission with max $20.00 succeeds on revision 2
        perm_ok = StandingPermission(
            company_domain="manzanitasupply.example",
            account_id="cust_alice",
            allowed_actions=frozenset({"exchange_delivered_order_items"}),
            max_price_difference_cents=2000,
            expires_at=2000,
        )
        confirmed = self.guard.confirm_operation(
            token=self.alice_token,
            operation_id=op_id,
            revision=2,
            approved_by="permission",
            now=1025,
            standing_permission=perm_ok,
        )
        self.assertTrue(confirmed.allowed)
        self.assertEqual(confirmed.code, "succeeded")
        self.assertEqual(
            self.guard.payment_methods["cust_alice"]["gc_large"].balance_cents,
            3500,
        )

        # Repeated confirm is idempotent and does not deduct gift card balance again
        repeated = self.guard.confirm_operation(
            token=self.alice_token,
            operation_id=op_id,
            revision=2,
            approved_by="permission",
            now=1030,
            standing_permission=perm_ok,
        )
        self.assertTrue(repeated.allowed)
        self.assertEqual(repeated.code, "already_final")
        self.assertEqual(
            self.guard.payment_methods["cust_alice"]["gc_large"].balance_cents,
            3500,
        )

    def test_run_demo_completes_cleanly(self) -> None:
        summary = run_demo()
        self.assertTrue(summary["discovery_verified"])
        self.assertEqual(summary["proposal_code"], "proposed")
        self.assertEqual(summary["chat_confirm_blocked"], "conversation_message_cannot_confirm")
        self.assertEqual(summary["confirmed_state"], "succeeded")
        self.assertEqual(summary["order_status_after_confirm"], "pending (items modified)")
        self.assertEqual(
            summary["second_pending_modify_blocked"],
            "one_time_modification_limit_exceeded",
        )


if __name__ == "__main__":
    unittest.main()
