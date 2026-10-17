"""Unit tests for Poppy v0.1 discovery/token verification and Sierra retail mutation guards."""

import unittest

from lab.poppy_guard import (
    CatalogVariant,
    DPoPProof,
    PaymentInstrument,
    PoppyConversationGuard,
    RetailOrder,
    RetailOrderMutationGuard,
    SessionAssertionClaims,
    SessionToken,
    StandingPermission,
    build_rfc8414_metadata_url,
    run_demo,
    sha256_token,
    verify_cross_company_content_boundary,
    verify_hosted_company_isolation,
    verify_poppy_assertion_audience,
    verify_poppy_browser_session_exchange,
    verify_poppy_discovery,
    verify_poppy_mcp_protected_resource,
    verify_poppy_request_token,
    verify_poppy_session_assertion,
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
        # Per #37 (efc12168): post-redirect host must match organization.domain ignoring case only (no www. stripping)
        res = verify_poppy_discovery(
            "https://www.manzanitasupply.example/.well-known/poppy.json",
            self.poppy_doc,
            {**self.oauth_meta, "dpop_signing_alg_values_supported": ["ES256"]},
            final_well_known_url="https://ManzanitaSupply.Example/.well-known/poppy.json",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason, "verified")

        unredirected_www = verify_poppy_discovery(
            "https://www.manzanitasupply.example/.well-known/poppy.json",
            self.poppy_doc,
            self.oauth_meta,
        )
        self.assertFalse(unredirected_www.allowed)
        self.assertEqual(unredirected_www.reason, "organization_domain_mismatch")

        missing_es256 = verify_poppy_discovery(
            "https://manzanitasupply.example/.well-known/poppy.json",
            self.poppy_doc,
            {**self.oauth_meta, "dpop_signing_alg_values_supported": ["RS256"]},
        )
        self.assertFalse(missing_es256.allowed)
        self.assertEqual(missing_es256.reason, "dpop_es256_unsupported")

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

    def test_assertion_audience_and_dpop_token_vs_api_status_codes(self) -> None:
        issuer = "https://auth.manzanitasupply.example"
        self.assertTrue(verify_poppy_assertion_audience(issuer, auth_issuer=issuer).allowed)
        for bad_aud in [
            "https://auth.manzanitasupply.example/oauth/token",
            [issuer],
            "",
            None,
        ]:
            with self.subTest(bad_aud=bad_aud):
                chk = verify_poppy_assertion_audience(bad_aud, auth_issuer=issuer)
                self.assertFalse(chk.allowed)
                self.assertEqual(chk.http_status, 400)
                self.assertEqual(chk.error, "invalid_client_or_session_assertion_aud")

        dpop_token = SessionToken(
            access_token="tok_dpop_status",
            token_type="DPoP",
            session_id="ses_status",
            client_id="https://agent.example/agent.json",
            user_id="usr_1",
            signed_in=True,
            account_id="cust_1",
            scopes=frozenset({"poppy:read"}),
            sign_in_method="direct",
            jwk_thumbprint="jkt_status",
            expires_at=2000,
        )
        # Missing DPoP proof returns 400 at token endpoint and 401 at API endpoint (#36)
        tok_ep = verify_poppy_request_token(
            token=dpop_token,
            channel="token",
            http_method="POST",
            target_url="https://auth.manzanitasupply.example/oauth/token",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
            dpop_proof=None,
        )
        self.assertEqual((tok_ep.allowed, tok_ep.http_status, tok_ep.error), (False, 400, "invalid_dpop_proof"))

        api_ep = verify_poppy_request_token(
            token=dpop_token,
            channel="openapi",
            http_method="GET",
            target_url="https://api.manzanitasupply.example/orders",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
            dpop_proof=None,
        )
        self.assertEqual((api_ep.allowed, api_ep.http_status, api_ep.error), (False, 401, "invalid_dpop_proof"))

        # Server-issued DPoP nonce mismatch returns use_dpop_nonce
        proof_no_nonce = DPoPProof(
            jti="jti_n1",
            htm="GET",
            htu="https://api.manzanitasupply.example/orders",
            iat=1000,
            ath=sha256_token("tok_dpop_status"),
            jwk_thumbprint="jkt_status",
        )
        nonce_chk = verify_poppy_request_token(
            token=dpop_token,
            channel="openapi",
            http_method="GET",
            target_url="https://api.manzanitasupply.example/orders",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
            dpop_proof=proof_no_nonce,
            expected_dpop_nonce="srv_nonce_99",
        )
        self.assertEqual((nonce_chk.allowed, nonce_chk.http_status, nonce_chk.error), (False, 401, "use_dpop_nonce"))

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

    def test_company_kit_session_vs_browser_assertion_and_mcp_metadata(self) -> None:
        # Per #35 (95fcbf22c599) checks/session.ts: browser assertion rejected at token endpoint
        seen_jti: set[str] = set()
        browser_as_session = SessionAssertionClaims(
            typ="poppy-browser+jwt",
            iss="https://agent.example/agent.json",
            sub="usr_1",
            aud="https://auth.manzanitasupply.example",
            iat=1000,
            exp=1060,
            jti="jti_browser_123456789012345",
            session_id="ses_1",
            return_to="https://manzanitasupply.example/orders/ord_1",
        )
        rejected = verify_poppy_session_assertion(
            browser_as_session,
            auth_issuer="https://auth.manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
        )
        self.assertEqual((rejected.allowed, rejected.http_status, rejected.error), (False, 400, "invalid_grant"))

        # Valid session assertion succeeds once, replay fails with 400 invalid_grant, unknown session_id -> invalid_session
        valid_session_assertion = SessionAssertionClaims(
            typ="poppy-session+jwt",
            iss="https://agent.example/agent.json",
            sub="usr_1",
            aud="https://auth.manzanitasupply.example",
            iat=1000,
            exp=1060,
            jti="jti_session_123456789012345",
            session_id="ses_1",
        )
        active_owners = {"ses_1": ("https://agent.example/agent.json", "usr_1")}
        ok_sess = verify_poppy_session_assertion(
            valid_session_assertion,
            auth_issuer="https://auth.manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
            active_sessions=active_owners,
        )
        self.assertTrue(ok_sess.allowed)
        replayed_sess = verify_poppy_session_assertion(
            valid_session_assertion,
            auth_issuer="https://auth.manzanitasupply.example",
            now=1011,
            seen_jti=seen_jti,
            active_sessions=active_owners,
        )
        self.assertEqual((replayed_sess.allowed, replayed_sess.error), (False, "invalid_grant"))

        unknown_sess = verify_poppy_session_assertion(
            SessionAssertionClaims(
                typ="poppy-session+jwt",
                iss="https://agent.example/agent.json",
                sub="usr_1",
                aud="https://auth.manzanitasupply.example",
                iat=1000,
                exp=1060,
                jti="jti_unknown_123456789012345",
                session_id="ses_missing",
            ),
            auth_issuer="https://auth.manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
            active_sessions=active_owners,
        )
        self.assertEqual((unknown_sess.allowed, unknown_sess.error), (False, "invalid_session"))

        # Browser session endpoint (#35 patterns/web-browsing.md & browser-assertion.schema.json)
        active_tokens = {
            "ses_1": SessionToken(
                access_token="tok_1",
                token_type="DPoP",
                session_id="ses_1",
                client_id="https://agent.example/agent.json",
                user_id="usr_1",
                signed_in=True,
                account_id="cust_1",
                scopes=frozenset({"poppy:read"}),
                sign_in_method="mediated",
                jwk_thumbprint="jkt_1",
                expires_at=2000,
            )
        }
        browser_endpoint = "https://manzanitasupply.example/poppy/browser-session"
        valid_browser = SessionAssertionClaims(
            typ="poppy-browser+jwt",
            iss="https://agent.example/agent.json",
            sub="usr_1",
            aud=browser_endpoint,
            iat=1000,
            exp=1060,
            jti="jti_brows_ok_12345678901234",
            session_id="ses_1",
            return_to="https://manzanitasupply.example/orders/ord_1",
        )
        b_ok = verify_poppy_browser_session_exchange(
            valid_browser,
            browser_session_endpoint=browser_endpoint,
            organization_domain="manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
            active_sessions=active_tokens,
        )
        self.assertTrue(b_ok.allowed)
        self.assertEqual(b_ok.http_status, 303)
        self.assertEqual(b_ok.cookie_attributes["SameSite"], "Lax")
        self.assertEqual(b_ok.cookie_attributes["scopes"], ["poppy:read"])

        # Prefix-spoofed return_to domain & SameSite=Strict are rejected
        evil_return = verify_poppy_browser_session_exchange(
            SessionAssertionClaims(
                **{
                    **valid_browser.__dict__,
                    "jti": "jti_brows_ev_12345678901234",
                    "return_to": "https://manzanitasupply.example.evil.test/orders",
                }
            ),
            browser_session_endpoint=browser_endpoint,
            organization_domain="manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
            active_sessions=active_tokens,
        )
        self.assertEqual((evil_return.allowed, evil_return.error), (False, "return_to_domain_mismatch"))

        strict_cookie = verify_poppy_browser_session_exchange(
            SessionAssertionClaims(
                **{**valid_browser.__dict__, "jti": "jti_brows_st_12345678901234"}
            ),
            browser_session_endpoint=browser_endpoint,
            organization_domain="manzanitasupply.example",
            now=1010,
            seen_jti=seen_jti,
            active_sessions=active_tokens,
            cookie_same_site="Strict",
        )
        self.assertEqual(
            (strict_cookie.allowed, strict_cookie.error),
            (False, "samesite_strict_breaks_cross_site_redirect"),
        )

        # Symmetric HS256 DPoP alg is forbidden even if caller lists it in supported algs (#35 dpop-proof.schema.json)
        hs_proof = DPoPProof(
            jti="jti_hs256_1234567890123456",
            htm="GET",
            htu="https://api.manzanitasupply.example/orders",
            iat=1000,
            ath=sha256_token("tok_1"),
            jwk_thumbprint="jkt_1",
            alg="HS256",
        )
        hs_res = verify_poppy_request_token(
            token=active_tokens["ses_1"],
            channel="openapi",
            http_method="GET",
            target_url="https://api.manzanitasupply.example/orders",
            now=1000,
            poppy_auth_config=self.poppy_doc["auth"],
            dpop_proof=hs_proof,
            dpop_signing_algs_supported={"ES256", "HS256"},
        )
        self.assertEqual((hs_res.allowed, hs_res.error), (False, "invalid_dpop_proof"))

        # MCP Protected Resource Metadata (RFC 9728, #35 checks/mcp.ts)
        mcp_meta_ok = verify_poppy_mcp_protected_resource(
            mcp_server_url="https://mcp.manzanitasupply.example/mcp",
            auth_issuer="https://auth.manzanitasupply.example",
            unauthenticated_http_status=401,
            www_authenticate_header='Bearer resource_metadata="https://mcp.manzanitasupply.example/.well-known/oauth-protected-resource/mcp"',
            protected_resource_metadata={
                "resource": "https://mcp.manzanitasupply.example/mcp",
                "authorization_servers": ["https://auth.manzanitasupply.example"],
            },
        )
        self.assertTrue(mcp_meta_ok.allowed)


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

        # Per #41/#49: Session remains tied to cust_alice even after sign-out; signing in as cust_bob returns 400
        self.guard.sign_out_session("ses_alice", revoked=True)
        diff_acct = self.guard.authenticate_session_account(
            session_id="ses_alice",
            account_id="cust_bob",
            sign_in_method="direct",
        )
        self.assertEqual((diff_acct.allowed, diff_acct.http_status, diff_acct.code), (False, 400, "account_mismatch"))

        # Per #53: Automatic background re-sign-in with stored mediated credentials after revocation is forbidden
        auto_med = self.guard.authenticate_session_account(
            session_id="ses_alice",
            account_id="cust_alice",
            sign_in_method="mediated",
            stored_credentials_used=True,
            user_initiated=False,
        )
        self.assertEqual(
            (auto_med.allowed, auto_med.http_status, auto_med.code),
            (False, 403, "auto_resignin_after_revocation_forbidden"),
        )

        # User-initiated sign-in back to the same bound account succeeds
        re_signin = self.guard.authenticate_session_account(
            session_id="ses_alice",
            account_id="cust_alice",
            sign_in_method="mediated",
            stored_credentials_used=True,
            user_initiated=True,
        )
        self.assertEqual((re_signin.allowed, re_signin.http_status, re_signin.code), (True, 200, "signed_in"))

    def test_security_considerations_cross_company_and_summary_terms_agreement(self) -> None:
        # Per #51 Section 8.1: Company A content cannot trigger action/data transfer to Company B
        blocked = verify_cross_company_content_boundary(
            source_company_domain="manzanitasupply.example",
            target_company_domain="exfiltrate-partner.example",
            triggered_by_company_content=True,
            explicit_user_target_domains={"manzanitasupply.example"},
        )
        self.assertEqual(
            (blocked.allowed, blocked.http_status, blocked.code),
            (False, 403, "cross_company_prompt_injection_blocked"),
        )

        # Per #51 operations §3.1 & Section 8.1: misleading summary vs structured terms blocks confirmation
        prop = self.guard.propose_item_change(
            token=self.alice_token,
            order_id="ord_pending",
            action="modify_pending_order_items",
            current_item_id="jkt-m",
            replacement_item_id="jkt-l",
            payment_method_id="card_orig",
            now=1000,
        )
        op_id = prop.operation["operation_id"]
        self.guard.operations[op_id].summary = (
            "modify_pending_order_items on order ord_pending: replace Storm Jacket M (jkt-m) "
            "with Storm Jacket L (jkt-l), price_difference_cents=0, payment_method_id=card_orig."
        )
        mismatch = self.guard.confirm_operation(
            token=self.alice_token,
            operation_id=op_id,
            revision=1,
            approved_by="user",
            now=1010,
        )
        self.assertEqual((mismatch.allowed, mismatch.http_status, mismatch.code), (False, 409, "summary_terms_mismatch"))

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

    def test_rfc8414_path_scoped_metadata_url_and_hosted_company_isolation(self) -> None:
        # RFC 8414 Section 3.1 inserts /.well-known/oauth-authorization-server before issuer path
        self.assertEqual(
            build_rfc8414_metadata_url("https://auth.platform.example/outfitters"),
            "https://auth.platform.example/.well-known/oauth-authorization-server/outfitters",
        )
        self.assertEqual(
            build_rfc8414_metadata_url("https://auth.manzanitasupply.example"),
            "https://auth.manzanitasupply.example/.well-known/oauth-authorization-server",
        )
        for bad_issuer in (
            "http://auth.platform.example/outfitters",
            "https://auth.platform.example/outfitters/",
            "https://auth.platform.example/outfitters?tenant=1",
        ):
            with self.assertRaises(ValueError):
                build_rfc8414_metadata_url(bad_issuer)

        outfitters_meta = {
            "issuer": "https://auth.platform.example/outfitters",
            "poppy_domains": ["outfitters.example", "outfitters-uk.example"],
        }
        books_meta = {
            "issuer": "https://auth.platform.example/books",
            "poppy_domains": ["books.example"],
        }

        # Two domains sharing the exact same path-scoped issuer are one Company
        same_company = verify_hosted_company_isolation(
            token_issuer="https://auth.platform.example/outfitters",
            target_company_issuer="https://auth.platform.example/outfitters",
            target_storefront_domain="outfitters-uk.example",
            target_oauth_metadata=outfitters_meta,
            agent_user_id="usr_outfitters_1",
            known_user_ids_by_issuer={
                "https://auth.platform.example/outfitters": "usr_outfitters_1",
                "https://auth.platform.example/books": "usr_books_9",
            },
        )
        self.assertTrue(same_company.allowed)

        # Cross-company token reuse on same platform host is rejected
        cross_token = verify_hosted_company_isolation(
            token_issuer="https://auth.platform.example/outfitters",
            target_company_issuer="https://auth.platform.example/books",
            target_storefront_domain="books.example",
            target_oauth_metadata=books_meta,
            agent_user_id="usr_books_9",
            known_user_ids_by_issuer={},
        )
        self.assertFalse(cross_token.allowed)
        self.assertEqual(cross_token.reason, "cross_company_token_rejected")

        # Reusing the same opaque user_id across distinct issuers on the same platform is rejected
        reused_uid = verify_hosted_company_isolation(
            token_issuer="https://auth.platform.example/books",
            target_company_issuer="https://auth.platform.example/books",
            target_storefront_domain="books.example",
            target_oauth_metadata=books_meta,
            agent_user_id="usr_shared_bad",
            known_user_ids_by_issuer={
                "https://auth.platform.example/outfitters": "usr_shared_bad",
            },
        )
        self.assertFalse(reused_uid.allowed)
        self.assertEqual(reused_uid.reason, "cross_company_user_id_reuse_forbidden")

    def test_milestone2_conversation_checks_and_direct_conversation_isolation(self) -> None:
        conv_guard = PoppyConversationGuard()
        other_user_token = SessionToken(
            access_token="tok_dpop_bob",
            token_type="DPoP",
            session_id="ses_bob",
            client_id="https://agent.example/agent.json",
            user_id="usr_Bob99",
            signed_in=False,
            account_id=None,
            scopes=frozenset(),
            jwk_thumbprint="jkt_p256_bob",
            expires_at=2000,
        )

        # conversations.not-found -> 404 conversation_not_found
        status, body = conv_guard.read_events(token=self.alice_token, conversation_id="cnv_unknown")
        self.assertEqual((status, body["error"]), (404, "conversation_not_found"))

        # conversations.invalid-message-id & conversations.empty-message -> 400 invalid_request
        bad_id_status, bad_id_body = conv_guard.start_conversation(
            token=self.alice_token,
            message={"id": "msg validator!", "sender": "agent", "text": "hello"},
        )
        self.assertEqual((bad_id_status, bad_id_body["error"]), (400, "invalid_request"))

        empty_status, empty_body = conv_guard.start_conversation(
            token=self.alice_token,
            message={"id": "msg_empty_1", "sender": "agent"},
        )
        self.assertEqual((empty_status, empty_body["error"]), (400, "invalid_request"))

        # conversations.start -> 201 Created
        first_msg = {"id": "msg_first_1", "sender": "agent", "text": "Validator test message."}
        st_start, start_body = conv_guard.start_conversation(
            token=self.alice_token,
            message=first_msg,
        )
        self.assertEqual(st_start, 201)
        conv_id = start_body["conversation_id"]
        self.assertEqual(start_body["status"], "idle")
        self.assertEqual(start_body["responder"], "agent")

        # Cross-user access returns 404 conversation_not_found (enumeration prevention)
        cross_st, cross_body = conv_guard.read_events(token=other_user_token, conversation_id=conv_id)
        self.assertEqual((cross_st, cross_body["error"]), (404, "conversation_not_found"))

        # conversations.retry-same-id -> 201 with same conversation_id, no duplicate event
        st_retry, retry_body = conv_guard.start_conversation(
            token=self.alice_token,
            message=first_msg,
        )
        self.assertEqual(st_retry, 201)
        self.assertEqual(retry_body["conversation_id"], conv_id)

        # conversations.message-id-conflict -> 409 message_id_conflict when content differs
        st_conflict, conflict_body = conv_guard.start_conversation(
            token=self.alice_token,
            message={"id": "msg_first_1", "sender": "agent", "text": "Changed text."},
        )
        self.assertEqual((st_conflict, conflict_body["error"]), (409, "message_id_conflict"))

        # conversations.follow-up -> 202 Accepted
        st_follow, follow_body = conv_guard.post_message(
            token=self.alice_token,
            conversation_id=conv_id,
            message={"id": "msg_second_2", "sender": "agent", "text": "Follow-up question."},
        )
        self.assertEqual(st_follow, 202)
        self.assertEqual(follow_body["status"], "idle")

        # Section 7.10 Direct Conversation: direct messages never leak into parent GET /events
        st_dir, dir_body = conv_guard.open_direct_conversation(
            token=self.alice_token,
            conversation_id=conv_id,
            direct_customer_message="Private customer note not for Personal Agent.",
        )
        self.assertEqual(st_dir, 201)
        self.assertIn("direct_conversation_id", dir_body)
        st_dir_dup, dir_dup_body = conv_guard.open_direct_conversation(
            token=self.alice_token,
            conversation_id=conv_id,
            direct_customer_message="Second concurrent direct chat.",
        )
        self.assertEqual((st_dir_dup, dir_dup_body["error"]), (409, "direct_conversation_already_open"))
        st_dir_close, _ = conv_guard.close_direct_conversation(
            token=self.alice_token,
            conversation_id=conv_id,
        )
        self.assertEqual(st_dir_close, 200)

        # conversations.events-read, user-message-recorded, retry-not-duplicated
        st_read, read_body = conv_guard.read_events(token=self.alice_token, conversation_id=conv_id, wait=1)
        self.assertEqual(st_read, 200)
        self.assertFalse(read_body["has_more"])
        first_events = [
            e for e in read_body["events"]
            if e["type"] == "message" and e["message"]["id"] == "msg_first_1"
        ]
        self.assertEqual(len(first_events), 1)
        self.assertEqual(first_events[0]["message"]["role"], "user")
        # Direct customer message text is not present in parent events
        self.assertNotIn("Private customer note", str(read_body["events"]))
        direct_states = [e.get("direct") for e in read_body["events"] if e["type"] == "state"]
        self.assertEqual(direct_states, ["direct_opened", "direct_closed"])

        # conversations.invalid-wait & conversations.unknown-cursor
        st_bad_wait, bad_wait_body = conv_guard.read_events(
            token=self.alice_token, conversation_id=conv_id, wait="soon"
        )
        self.assertEqual((st_bad_wait, bad_wait_body["error"]), (400, "invalid_request"))
        st_bad_cur, bad_cur_body = conv_guard.read_events(
            token=self.alice_token, conversation_id=conv_id, cursor="evt_unknown_999"
        )
        self.assertEqual((st_bad_cur, bad_cur_body["error"]), (400, "invalid_cursor"))

        # conversations.close, close-event, close-again, closed-message, closed-handoff
        cursor_before_close = read_body["cursor"]
        st_close, close_body = conv_guard.close_conversation(
            token=self.alice_token, conversation_id=conv_id
        )
        self.assertEqual((st_close, close_body["status"]), (200, "closed"))
        _, after_close = conv_guard.read_events(
            token=self.alice_token, conversation_id=conv_id, cursor=cursor_before_close
        )
        self.assertEqual(len(after_close["events"]), 1)
        self.assertEqual(after_close["events"][0]["status"], "closed")

        st_close_again, close_again_body = conv_guard.close_conversation(
            token=self.alice_token, conversation_id=conv_id
        )
        self.assertEqual((st_close_again, close_again_body["status"]), (200, "closed"))
        _, after_second_close = conv_guard.read_events(
            token=self.alice_token, conversation_id=conv_id, cursor=after_close["cursor"]
        )
        self.assertEqual(after_second_close["events"], [])

        st_closed_msg, closed_msg_body = conv_guard.post_message(
            token=self.alice_token,
            conversation_id=conv_id,
            message={"id": "msg_after_close", "sender": "agent", "text": "Still there?"},
        )
        self.assertEqual((st_closed_msg, closed_msg_body["error"]), (409, "conversation_closed"))
        st_closed_ho, closed_ho_body = conv_guard.request_handoff(
            token=self.alice_token, conversation_id=conv_id
        )
        self.assertEqual((st_closed_ho, closed_ho_body["error"]), (409, "conversation_closed"))


if __name__ == "__main__":
    unittest.main()
