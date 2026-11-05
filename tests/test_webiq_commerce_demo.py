"""Unit tests for Microsoft Web IQ v3 contract & Agentic Commerce integration (`lab/webiq_commerce_demo.py`)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.checkout import Checkout
from lab.webiq_commerce_demo import (
    WebIQClient,
    WebIQClientConfig,
    WebIQHTTPError,
    WebIQValidationError,
    build_mpp_pay_continuation,
    build_webiq_live_demo_payload,
    clamp_auto_max_response_length,
    classify_webiq_error_response,
    evaluate_booking_and_mpp_dual_path_guard,
    evaluate_delegated_checkout_hook,
    evaluate_oca_agreement_transition,
    evaluate_replenishment_with_webiq_recall_guard,
    evaluate_webiq_search_finops,
    evaluate_webmcp_tool_call,
    main,
    normalize_webiq_response,
    parse_webiq_retry_after,
    render_webiq_live_demo_html,
    render_webiq_seven_card_html,
    run_grounded_discovery_and_checkout,
    run_webiq_commerce_benchmark_suite,
    ground_return_policy_passage,
    validate_connect_catalog_import_and_hooks,
    validate_link_spend_request,
    validate_mcp_oauth21_rfc9207_and_stepup,
    validate_sftp_catalog_batch,
    validate_spt_resolution_and_payment_intent,
    validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt,
    validate_stripe_agent_key_and_embedded_session,
    validate_ucp_payment_completion,
    validate_visa_vic_vts_passkey_enrollment,
    verify_post_purchase_return_policy,
)


class WebIQContractTest(unittest.TestCase):
    """Verify official Microsoft Web IQ v3 REST & MCP contract invariants."""

    def setUp(self) -> None:
        self.client = WebIQClient()

    def test_response_field_omission_normalization(self) -> None:
        raw = {
            "nullField": None,
            "emptyStr": "",
            "emptyList": [],
            "whitespaceStr": "   ",
            "boolFalse": False,
            "intZero": 0,
            "emptyDict": {},
            "nested": {
                "dropMe": None,
                "dropEmpty": "",
                "keepZero": 0,
            },
            "content": [],
        }
        norm_rest = normalize_webiq_response(raw, preserve_envelope_content=False)
        self.assertNotIn("nullField", norm_rest)
        self.assertNotIn("emptyStr", norm_rest)
        self.assertNotIn("emptyList", norm_rest)
        self.assertNotIn("content", norm_rest)
        self.assertEqual(norm_rest["whitespaceStr"], "   ")
        self.assertIs(norm_rest["boolFalse"], False)
        self.assertEqual(norm_rest["intZero"], 0)
        self.assertEqual(norm_rest["emptyDict"], {})
        self.assertEqual(norm_rest["nested"], {"keepZero": 0})

        norm_mcp = normalize_webiq_response(raw, preserve_envelope_content=True)
        self.assertIn("content", norm_mcp)
        self.assertEqual(norm_mcp["content"], [])

    def test_search_web_validation_and_max_length_cap(self) -> None:
        with self.assertRaises(WebIQValidationError):
            self.client.search_web("")
        with self.assertRaises(WebIQValidationError):
            self.client.search_web("x" * 1001)
        with self.assertRaises(WebIQValidationError):
            self.client.search_web("headphones", max_results=51)
        with self.assertRaises(WebIQValidationError):
            self.client.search_web("headphones", location="37.77,-122.41")

        # Without full-document entitlement, maxLength > 3000 is capped at 3000
        res = self.client.search_web(
            "headphones",
            max_length=9000,
            location="lat:47.6062;long:-122.3321",
        )
        self.assertEqual(res["maxLength"], 3000)
        self.assertNotIn("emptyListOmitted", res)
        self.assertNotIn("nullFieldOmitted", res)

    def test_search_web_content_format_entitlement_gate(self) -> None:
        for fmt in ("text", "html", "markdown"):
            with self.assertRaises(WebIQHTTPError) as ctx:
                self.client.search_web("headphones", content_format=fmt)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctx.exception.error_code, "AuthContentFormatForbidden")

        entitled_client = WebIQClient(WebIQClientConfig(full_document_entitled=True))
        res = entitled_client.search_web("headphones", content_format="markdown", max_length=8000)
        self.assertEqual(res["contentFormat"], "markdown")
        self.assertEqual(res["maxLength"], 8000)
        self.assertTrue(res["results"][0]["content"].startswith("[MARKDOWN FULL DOC]"))

    def test_consumer_site_operator_safesearch_bypass_guard(self) -> None:
        with self.assertRaises(WebIQHTTPError) as ctx:
            self.client.search_web("site:untrusted.example wireless earbuds", safe_search="strict")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.error_code, "SiteOperatorSafeSearchBypassBlocked")

        # Allowlisted merchant domain succeeds under strict safeSearch
        allowlisted_client = WebIQClient(
            WebIQClientConfig(
                consumer_safe_profile=True,
                allowed_site_domains=frozenset({"shop.nordicaudio.example"}),
            )
        )
        res = allowlisted_client.search_web("site:shop.nordicaudio.example headphones", safe_search="strict")
        self.assertGreaterEqual(len(res["results"]), 1)

    def test_china_url_redirection_click_url_preserved(self) -> None:
        res = self.client.search_web("降噪耳机", fixture_key="china_redirect")
        hit = res["results"][0]
        self.assertEqual(hit["domain"], "cn.shop.nordicaudio.example")
        self.assertIn("clickUrl", hit)
        self.assertEqual(hit["contentTier"], "entitled")

    def test_search_news_max_results_cap(self) -> None:
        with self.assertRaises(WebIQValidationError):
            self.client.search_news("recall", max_results=21)
        res = self.client.search_news("recall", max_results=20)
        self.assertEqual(res["results"][0]["riskLevel"], "veryHigh")
        self.assertNotIn("author", res["results"][0])  # empty string omitted

    def test_browse_https_enforcement_and_render_dynamic_pages(self) -> None:
        with self.assertRaises(WebIQHTTPError) as ctx:
            self.client.browse("http://shop.nordicaudio.example/products/anc-pro-headphones")
        self.assertEqual(ctx.exception.status_code, 410)
        self.assertEqual(ctx.exception.error_code, "HttpSchemeGone")

        with self.assertRaises(WebIQHTTPError) as dyn_ctx:
            self.client.browse(
                "https://shop.nordicaudio.example/products/anc-pro-headphones",
                live_crawl="force",
                render_dynamic_pages=True,
            )
        self.assertEqual(dyn_ctx.exception.status_code, 400)
        self.assertEqual(dyn_ctx.exception.error_code, "InvalidRenderDynamicPages")

    def test_browse_202_retry_after_and_live_crawl_succeeded_semantics(self) -> None:
        # 202 Accepted omits title, content, isAdult, lastUpdatedAt, crawledAt
        pending = self.client.browse("https://shop.nordicaudio.example/policies/returns-202", live_crawl="force")
        self.assertEqual(pending["httpStatus"], 202)
        self.assertEqual(pending["retryAfter"], "60s")
        for omitted_key in ("title", "content", "isAdult", "lastUpdatedAt", "crawledAt"):
            self.assertNotIn(omitted_key, pending)

        # Fresh 200 OK omits liveCrawlSucceeded (never emitted as True)
        fresh = self.client.browse(
            "https://shop.nordicaudio.example/products/anc-pro-headphones",
            live_crawl="force",
        )
        self.assertEqual(fresh["httpStatus"], 200)
        self.assertNotIn("liveCrawlSucceeded", fresh)

        # Stale 200 OK on liveCrawl='force' includes liveCrawlSucceeded: False
        stale = self.client.browse(
            "https://shop.nordicaudio.example/products/anc-pro-headphones-stale",
            live_crawl="force",
        )
        self.assertEqual(stale["httpStatus"], 200)
        self.assertIs(stale["liveCrawlSucceeded"], False)

    def test_browse_passage_requires_query_and_selects_policy_evidence(self) -> None:
        policy_url = "https://shop.nordicaudio.example/policies/returns"
        with self.assertRaises(WebIQValidationError):
            self.client.browse(policy_url, content_format="passage", query="   ")
        with self.assertRaises(WebIQValidationError):
            self.client.browse(policy_url, content_format="markdown", query="x" * 1001)

        passage = self.client.browse(
            policy_url,
            content_format="passage",
            query="restocking fee",
            max_length=160,
        )
        full = self.client.browse(policy_url, content_format="markdown")
        self.assertEqual(passage["contentFormat"], "passage")
        self.assertEqual(passage["query"], "restocking fee")
        self.assertIn("restocking_fee_minor=0", passage["content"])
        self.assertLess(len(passage["content"]), len(full["content"]))
        self.assertNotIn("query", full)

        grounded = ground_return_policy_passage(
            self.client,
            policy_url=policy_url,
            query="return window restocking fee",
        )
        self.assertTrue(grounded["grounded"])
        self.assertEqual(grounded["reason"], "passage_contains_merchant_policy")

    def test_auto_clamping_and_malformed_evidence_omission(self) -> None:
        self.assertEqual(clamp_auto_max_response_length(500), 1500)
        self.assertEqual(clamp_auto_max_response_length(999999), 500000)
        self.assertEqual(clamp_auto_max_response_length(None), 10000)

        res = self.client.auto(
            "VoltMax recall",
            mode="advanced",
            max_response_length=800,
            response_filter=["web", "news"],
            include_malformed_evidence=True,
        )
        self.assertEqual(res["maxResponseLength"], 1500)
        for item in res["results"]:
            self.assertIn(item["evidence"]["type"], {"web", "news"})
            self.assertTrue(item["evidence"]["content"].strip())
            for cit in item["citations"]:
                self.assertNotEqual(cit["url"], "https://orphan.example")
                self.assertNotEqual(cit["url"], "https://empty.example")

    def test_mcp_tool_entitlement_and_envelope(self) -> None:
        with self.assertRaises(WebIQHTTPError) as ctx:
            self.client.call_mcp_tool("images", {"query": "headphones"})
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.error_code, "ToolNotEntitledForAppId")

        env = self.client.call_mcp_tool(
            "browse",
            {"url": "https://shop.nordicaudio.example/policies/returns-202"},
        )
        self.assertEqual(env["content"], [])
        self.assertEqual(env["preserveWhitespace"], "   ")
        self.assertIs(env["preserveFalse"], False)
        self.assertEqual(env["preserveZero"], 0)
        self.assertEqual(env["preserveEmptyObj"], {})


class WebIQCommerceScenariosTest(unittest.TestCase):
    """Verify the 4 Agentic Commerce business scenarios & 7-card benchmark output."""

    def setUp(self) -> None:
        self.client = WebIQClient()
        self.quote = Checkout("nordic-audio-shop", "USD", "anc-pro-01", 1, 7900)

    def test_scenario_1_grounded_discovery_and_checkout(self) -> None:
        happy = run_grounded_discovery_and_checkout(
            self.client,
            query="Nordic Audio Pro ANC Headphones",
            browse_url="https://shop.nordicaudio.example/products/anc-pro-headphones",
            approved_checkout=self.quote,
        )
        self.assertTrue(happy.allowed)
        self.assertTrue(happy.injection_detected)
        self.assertFalse(happy.mandate_mutated)
        self.assertEqual(happy.verified_amount_minor, 7900)
        self.assertIsNotNone(happy.receipt_order_id)

        drift = run_grounded_discovery_and_checkout(
            self.client,
            query="Nordic Audio Pro ANC Headphones",
            browse_url="https://shop.nordicaudio.example/products/anc-pro-headphones-drift",
            approved_checkout=self.quote,
        )
        self.assertFalse(drift.allowed)
        self.assertIn("price_drift_blocked", drift.reason)

        stale = run_grounded_discovery_and_checkout(
            self.client,
            query="Nordic Audio Pro ANC Headphones",
            browse_url="https://shop.nordicaudio.example/products/anc-pro-headphones-stale",
            approved_checkout=self.quote,
        )
        self.assertFalse(stale.allowed)
        self.assertEqual(stale.reason, "stale_grounding_blocked")

    def test_scenario_2_autonomous_replenishment_recall_circuit_breaker(self) -> None:
        tripped = evaluate_replenishment_with_webiq_recall_guard(
            self.client,
            product_query="VoltMax Smart Espresso Pods",
            fixture_key="battery_recall",
            fcb_state="CLOSED",
        )
        self.assertFalse(tripped.allowed)
        self.assertEqual(tripped.fcb_next_state, "OPEN")
        self.assertIn("VENDOR_TRUST", tripped.tripped_conditions)
        self.assertTrue(tripped.recovery_mandate_required)

        blocked_open = evaluate_replenishment_with_webiq_recall_guard(
            self.client,
            product_query="VoltMax Smart Espresso Pods",
            fixture_key="battery_recall",
            fcb_state="OPEN",
            human_recovery_mandate_signed=False,
        )
        self.assertFalse(blocked_open.allowed)
        self.assertEqual(blocked_open.fcb_next_state, "OPEN")

        recovered = evaluate_replenishment_with_webiq_recall_guard(
            self.client,
            product_query="RoastCraft Organic Coffee Beans",
            fixture_key="clean_replenishment",
            fcb_state="OPEN",
            human_recovery_mandate_signed=True,
        )
        self.assertTrue(recovered.allowed)
        self.assertEqual(recovered.fcb_next_state, "HALF_OPEN")

        clean = evaluate_replenishment_with_webiq_recall_guard(
            self.client,
            product_query="RoastCraft Organic Coffee Beans",
            fixture_key="clean_replenishment",
            fcb_state="CLOSED",
        )
        self.assertTrue(clean.allowed)
        self.assertEqual(clean.fcb_next_state, "CLOSED")

    def test_scenario_3_post_purchase_return_policy_verification(self) -> None:
        pending_202 = verify_post_purchase_return_policy(
            self.client,
            policy_url="https://shop.nordicaudio.example/policies/returns-202",
            order_age_days=10,
            proposed_summary_window_days=30,
            proposed_summary_fee_minor=0,
            proposed_terms_window_days=30,
            proposed_terms_fee_minor=0,
        )
        self.assertFalse(pending_202.allowed)
        self.assertEqual(pending_202.browse_status, 202)
        self.assertEqual(pending_202.retry_after, "60s")
        self.assertTrue(pending_202.platform_fabricated_deadline_blocked)

        mismatch = verify_post_purchase_return_policy(
            self.client,
            policy_url="https://shop.nordicaudio.example/policies/returns",
            order_age_days=10,
            proposed_summary_window_days=30,
            proposed_summary_fee_minor=0,
            proposed_terms_window_days=30,
            proposed_terms_fee_minor=1500,
        )
        self.assertFalse(mismatch.allowed)
        self.assertFalse(mismatch.poppy_summary_matches_terms)

        valid = verify_post_purchase_return_policy(
            self.client,
            policy_url="https://shop.nordicaudio.example/policies/returns",
            order_age_days=14,
            proposed_summary_window_days=30,
            proposed_summary_fee_minor=0,
            proposed_terms_window_days=30,
            proposed_terms_fee_minor=0,
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.merchant_return_window_days, 30)

    def test_scenario_4_finops_and_seven_card_report_cli(self) -> None:
        finops = evaluate_webiq_search_finops(queries_count=200, content_tier="standard")
        self.assertEqual(finops.token_reduction_ratio, "7.1x")
        self.assertTrue(finops.mpp_aligned_schedule)
        self.assertEqual(finops.aligned_forfeited_usd, "0.000000")
        self.assertEqual(finops.mpp_recommended_step_units, 200)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertEqual(suite["total_scenarios"], 12)
        self.assertEqual(suite["webiq_guarded_passed"], 12)

        html_zh = render_webiq_seven_card_html(suite, lang="zh")
        self.assertIn("Content-Security-Policy", html_zh)
        for card_idx in range(1, 8):
            self.assertIn(f'id="card-{card_idx}"', html_zh)

        with TemporaryDirectory(prefix="webiq-report-") as tmpdir:
            out_dir = Path(tmpdir) / "bench"
            rc = main(["--output-dir", str(out_dir)])
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "report.json").is_file())
            self.assertTrue((out_dir / "index.html").is_file())
            self.assertTrue((out_dir / "index.en.html").is_file())
            self.assertTrue((out_dir / "live-demo.html").is_file())
            self.assertTrue((out_dir / "live-demo.en.html").is_file())

    def test_h5_live_demo_payload_and_html_generation(self) -> None:
        suite = run_webiq_commerce_benchmark_suite()
        payload = build_webiq_live_demo_payload(suite)
        self.assertEqual(len(payload["scenarios"]), 4)
        self.assertEqual(len(payload["subcases_map"]), 12)
        for idx in range(1, 13):
            w_code = f"W{idx:02d}"
            self.assertIn(w_code, payload["subcases_map"])
            mapping = payload["subcases_map"][w_code]
            scen = payload["scenarios"][mapping["scenarioIdx"]]
            mode_ids = {m["id"] for m in scen["modes"]}
            self.assertIn(mapping["modeId"], mode_ids)
            for m in scen["modes"]:
                self.assertEqual(len(m["planes"]), 4)

        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        demo_en = render_webiq_live_demo_html(suite, lang="en")
        expected_csp = (
            "default-src 'none'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; img-src data:;"
        )
        self.assertIn(expected_csp, demo_zh)
        self.assertIn(expected_csp, demo_en)
        self.assertIn('<html lang="zh">', demo_zh)
        self.assertIn('<html lang="en">', demo_en)
        self.assertIn("window.__WEBIQ_LIVE_DEMO_DATA__", demo_zh)
        self.assertIn("finops-query-slider", demo_zh)
        self.assertIn("playStepByStep()", demo_zh)
        self.assertIn("toggleLanguage()", demo_zh)

        with TemporaryDirectory(prefix="webiq-h5-cli-") as tmpdir:
            demo_path = Path(tmpdir) / "custom-demo.html"
            rc = main(["--live-demo-html", str(demo_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(demo_path.is_file())
            self.assertTrue((Path(tmpdir) / "custom-demo.en.html").is_file())

    def test_stage_1752_retry_after_link_wallet_mpp_and_webmcp_guards(self) -> None:
        # 1. Dual-format retryAfter parser & error classifier
        dur = parse_webiq_retry_after("60s", reference_utc="2026-11-01T00:00:00Z")
        self.assertEqual(dur["format"], "duration_seconds")
        self.assertEqual(dur["wait_seconds"], 60)

        ts = parse_webiq_retry_after("2026-11-01T00:01:30Z", reference_utc="2026-11-01T00:00:00Z")
        self.assertEqual(ts["format"], "iso8601_utc_timestamp")
        self.assertEqual(ts["wait_seconds"], 90)

        # HTTP 429 AuthUserThrottled requires duration, while 429 TooManyOnDemandCrawls requires UTC timestamp
        c_throttled = classify_webiq_error_response(429, "AuthUserThrottled", "60s")
        self.assertEqual(c_throttled["retry_after_format"], "duration_seconds")
        c_crawls = classify_webiq_error_response(
            429, "TooManyOnDemandCrawls", "2026-11-01T00:01:30Z", reference_utc="2026-11-01T00:00:00Z"
        )
        self.assertEqual(c_crawls["retry_after_format"], "iso8601_utc_timestamp")
        self.assertEqual(c_crawls["wait_seconds"], 90)
        with self.assertRaises(WebIQValidationError):
            classify_webiq_error_response(429, "TooManyOnDemandCrawls", "60s")

        # Non-retryable 403 UrlDisallowed / 410 HttpSchemeGone
        c_disallowed = classify_webiq_error_response(403, "UrlDisallowed")
        self.assertFalse(c_disallowed["retryable"])
        self.assertFalse(c_disallowed["allow_fabricated_fallback"])

        # 2. Stripe Link Agent Wallet (`liwltoken_...`, >=100 char context, mutual-exclusion flags)
        valid_ctx = (
            "Purchasing Nordic Audio Pro ANC Headphones ($79.00 USD) approved by principal under "
            "mandate-webiq-01 after live HTTPS Web IQ Browse price verification."
        )
        spt_ok = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="shared_payment_token",
            context=valid_ctx,
            amount_minor=7900,
            network_id="stripe_network",
        )
        self.assertTrue(spt_ok.allowed)
        self.assertEqual(spt_ok.status, "active")

        card_ok = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="card",
            context=valid_ctx,
            amount_minor=7900,
            merchant_name="Nordic Audio Shop",
            merchant_url="https://shop.nordicaudio.example",
        )
        self.assertTrue(card_ok.allowed)

        lpt_ok = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="link_pay_token",
            context=valid_ctx,
            amount_minor=7900,
            merchant_account_id="acct_1NordicAudio",
        )
        self.assertTrue(lpt_ok.allowed)

        # Reject merchant secret key leak, short context, flag conflict, or echoed scope escalation
        sk_leak = validate_link_spend_request(
            access_token="sk_live_merchant_secret",
            credential_type="shared_payment_token",
            context=valid_ctx,
            amount_minor=7900,
            network_id="stripe_network",
        )
        self.assertFalse(sk_leak.allowed)
        self.assertEqual(sk_leak.reason, "invalid_link_access_token_plane")

        short_ctx = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="shared_payment_token",
            context="Buy headphones now",
            amount_minor=7900,
            network_id="stripe_network",
        )
        self.assertFalse(short_ctx.allowed)
        self.assertEqual(short_ctx.reason, "context_too_short_min_100_chars")

        conflict = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="shared_payment_token",
            context=valid_ctx,
            amount_minor=7900,
            network_id="stripe_network",
            merchant_name="Forbidden For SPT",
        )
        self.assertFalse(conflict.allowed)
        self.assertEqual(conflict.reason, "spt_requires_network_id_and_forbids_merchant_fields")

        scope_esc = validate_link_spend_request(
            access_token="liwltoken_live_abc123",
            credential_type="shared_payment_token",
            context=valid_ctx,
            amount_minor=7900,
            network_id="stripe_network",
            requested_scopes=("spend:requests:read",),
            echoed_scopes=("spend:requests:read", "spend:requests:create"),
        )
        self.assertFalse(scope_esc.allowed)
        self.assertEqual(scope_esc.reason, "oauth_echoed_scope_privilege_escalation")

        # 3. HTTP 402 `mpp pay` continuation (`_next.pay_argv` anti-injection & method=='stripe')
        mpp_ok = build_mpp_pay_continuation(
            challenge_method="stripe",
            next_payload={
                "pay_argv": {
                    "command": "mpp",
                    "args": ["pay", "-t", "spt_live_001", "https://api.merchant.example/v1/search"],
                }
            },
        )
        self.assertTrue(mpp_ok["allowed"])
        self.assertEqual(mpp_ok["argv"][0], "mpp")

        mpp_non_stripe = build_mpp_pay_continuation(
            challenge_method="tempo_custom",
            next_payload={"pay_argv": {"command": "mpp", "args": ["pay", "-t", "spt_1", "https://a.example"]}},
        )
        self.assertFalse(mpp_non_stripe["allowed"])
        self.assertEqual(mpp_non_stripe["reason"], "unsupported_402_challenge_method_no_card_fallback")

        mpp_inj = build_mpp_pay_continuation(
            challenge_method="stripe",
            next_payload={
                "pay_argv": {
                    "command": "mpp",
                    "args": ["pay", "-t", "spt_1; rm -rf /", "https://api.merchant.example"],
                }
            },
        )
        self.assertFalse(mpp_inj["allowed"])
        self.assertEqual(mpp_inj["reason"], "shell_metacharacter_injection_in_pay_argv_blocked")

        # 4. WebMCP consequentialHint & tool rediscovery gate
        webmcp_unconfirmed = evaluate_webmcp_tool_call(
            {"name": "submit_payment", "annotations": {"consequentialHint": True}},
            human_confirmed=False,
        )
        self.assertFalse(webmcp_unconfirmed["allowed"])
        self.assertEqual(webmcp_unconfirmed["reason"], "webmcp_consequential_hint_requires_human_confirmation")

        webmcp_stale = evaluate_webmcp_tool_call(
            {"name": "submit_payment", "annotations": {"consequentialHint": True}},
            payment_method_changed=True,
            tools_rediscovered=False,
            human_confirmed=True,
        )
        self.assertFalse(webmcp_stale["allowed"])
        self.assertEqual(
            webmcp_stale["reason"],
            "webmcp_tool_rediscovery_required_after_payment_method_change",
        )

        webmcp_ok = evaluate_webmcp_tool_call(
            {"name": "submit_payment", "annotations": {"consequentialHint": True}},
            payment_method_changed=True,
            tools_rediscovered=True,
            human_confirmed=True,
        )
        self.assertTrue(webmcp_ok["allowed"])

    def test_stage_1753_oca_sftp_ucp_and_hook_guards(self) -> None:
        # 1. Stripe v2 Orchestrated Commerce Agreements (OCA) state machine & asymmetric termination lock
        agent_init = evaluate_oca_agreement_transition(
            current_state="none",
            actor="agent",
            action="initiate",
        )
        self.assertFalse(agent_init.allowed)
        self.assertEqual(agent_init.reason, "oca_initiation_requires_seller_actor")

        seller_init = evaluate_oca_agreement_transition(
            current_state="none",
            actor="seller",
            action="initiate",
        )
        self.assertTrue(seller_init.allowed)
        self.assertEqual(seller_init.next_state, "partially_confirmed")

        unverified_confirm = evaluate_oca_agreement_transition(
            current_state="partially_confirmed",
            actor="agent",
            action="confirm",
            seller_profile_verified=False,
        )
        self.assertFalse(unverified_confirm.allowed)

        confirmed = evaluate_oca_agreement_transition(
            current_state="partially_confirmed",
            actor="agent",
            action="confirm",
        )
        self.assertTrue(confirmed.allowed)
        self.assertEqual(confirmed.next_state, "confirmed")

        terminated_by_seller = evaluate_oca_agreement_transition(
            current_state="confirmed",
            actor="seller",
            action="terminate",
        )
        self.assertTrue(terminated_by_seller.allowed)
        self.assertEqual(terminated_by_seller.next_state, "terminated")
        self.assertEqual(terminated_by_seller.terminated_by, "seller")

        # Non-terminating party (agent) cannot re-initiate
        agent_reinit = evaluate_oca_agreement_transition(
            current_state="terminated",
            actor="agent",
            action="reinitiate",
            terminated_by="seller",
        )
        self.assertFalse(agent_reinit.allowed)
        self.assertEqual(agent_reinit.reason, "oca_reinitiation_locked_to_terminating_party")

        seller_reinit = evaluate_oca_agreement_transition(
            current_state="terminated",
            actor="seller",
            action="reinitiate",
            terminated_by="seller",
        )
        self.assertTrue(seller_reinit.allowed)
        self.assertEqual(seller_reinit.next_state, "partially_confirmed")

        # 2. Stripe SFTP Hybrid Catalog Ingestion (`manifest.json` barrier, `disable_checkout`, `delete=true`)
        no_manifest = validate_sftp_catalog_batch(
            feed_type="product_master",
            manifest_present=False,
        )
        self.assertFalse(no_manifest.allowed)
        self.assertEqual(no_manifest.reason, "manifest_json_barrier_incomplete_or_shard_count_mismatch")

        bare_name = validate_sftp_catalog_batch(
            feed_type="product_master",
            resolved_shard_paths=("full_catalog_part_1_of_1.csv.gz",),
        )
        self.assertFalse(bare_name.allowed)
        self.assertEqual(bare_name.reason, "shard_path_must_use_relative_or_absolute_path_not_bare_name")

        sample_rows = [
            {"id": "sku_active_1", "disable_checkout": "false", "delete": "false"},
            {"id": "sku_discovery_only", "disable_checkout": "true", "delete": "false"},
            {"id": "sku_deleted_9", "delete": "true", "price": "9999 USD"},
        ]
        disable_block = validate_sftp_catalog_batch(
            feed_type="delta",
            rows=sample_rows,
            requested_checkout_sku_id="sku_discovery_only",
        )
        self.assertFalse(disable_block.allowed)
        self.assertEqual(
            disable_block.reason,
            "disable_checkout_true_blocks_requested_session_redirect_to_link",
        )

        valid_batch = validate_sftp_catalog_batch(
            feed_type="delta",
            rows=sample_rows,
            requested_checkout_sku_id="sku_active_1",
        )
        self.assertTrue(valid_batch.allowed)
        self.assertEqual(valid_batch.deleted_sku_ids, ("sku_deleted_9",))
        self.assertEqual(valid_batch.discovery_only_sku_ids, ("sku_discovery_only",))
        self.assertEqual(valid_batch.checkout_eligible_sku_ids, ("sku_active_1",))

        # 3. Stripe UCP Payment Handler Split (`com.stripe.payments` vs `com.google.pay` & Link Trap)
        ucp_card_ok = validate_ucp_payment_completion(
            handler_name="com.stripe.payments",
            handler_id="stripe_payments",
            instrument_type="card",
            credential_type="stripe_payment_token",
            credential_token="spt_live_7900",
        )
        self.assertTrue(ucp_card_ok.allowed)

        ucp_link_trap = validate_ucp_payment_completion(
            handler_name="com.stripe.payments",
            handler_id="stripe_payments",
            instrument_type="link",
            credential_type="link_pay_token",
            credential_token="lpt_live_7900",
        )
        self.assertFalse(ucp_link_trap.allowed)
        self.assertEqual(
            ucp_link_trap.reason,
            "ucp_stripe_payments_handler_does_not_support_link_completion",
        )

        ucp_gpay_wrong = validate_ucp_payment_completion(
            handler_name="com.stripe.payments",
            handler_id="stripe_payments",
            instrument_type="google_pay",
            credential_type="PAYMENT_GATEWAY",
            credential_token="gpay_tok_1",
        )
        self.assertFalse(ucp_gpay_wrong.allowed)
        self.assertEqual(ucp_gpay_wrong.reason, "google_pay_requires_separate_com_google_pay_handler")

        ucp_gpay_ok = validate_ucp_payment_completion(
            handler_name="com.google.pay",
            handler_id="stripe-handler",
            instrument_type="card",
            credential_type="PAYMENT_GATEWAY",
            credential_token="gpay_tok_1",
        )
        self.assertTrue(ucp_gpay_ok.allowed)

        # 4. Seller Checkout Hooks (4s timeout, HTTP 424 mapping, context match, Affirm webview ban)
        hook_ok = evaluate_delegated_checkout_hook(
            hook_type="v1.delegated_checkout.finalize_checkout",
            hook_latency_ms=420,
        )
        self.assertTrue(hook_ok["allowed"])

        hook_timeout = evaluate_delegated_checkout_hook(
            hook_type="v1.delegated_checkout.finalize_checkout",
            hook_latency_ms=4100,
        )
        self.assertFalse(hook_timeout["allowed"])
        self.assertEqual(hook_timeout["status"], "declined_timeout_4s")

        hook_424 = evaluate_delegated_checkout_hook(
            hook_type="v1.delegated_checkout.customize_checkout",
            seller_http_status=503,
            idempotent_endpoint=True,
        )
        self.assertFalse(hook_424["allowed"])
        self.assertEqual(hook_424["agent_http_status"], 424)
        self.assertTrue(hook_424["retryable"])

        affirm_bot = evaluate_delegated_checkout_hook(
            hook_type="v1.delegated_checkout.finalize_checkout",
            payment_method="affirm",
            agent_programmatic_webview_interaction=True,
        )
        self.assertFalse(affirm_bot["allowed"])
        self.assertEqual(
            affirm_bot["reason"],
            "affirm_webview_automation_or_uncontrolled_device_forbidden",
        )

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["stage_1753_guards"]["all_passed"])

    def test_stage_1754_spt_resolve_connect_catalog_booking_and_mpp_guards(self) -> None:
        # 1. Stripe SPT Resolve API (single-use, mutual-exclusivity with PaymentIntent, PCI AoC RSA slice)
        resolve_ok = validate_spt_resolution_and_payment_intent(
            flow="resolve_api",
            credential_type="agentic_token",
            cryptogram_type="TAVV",
            pci_aoc_on_file=False,
            encryption_block_fields="number:0:16,cryptogram:16:28",
        )
        self.assertTrue(resolve_ok.allowed)
        self.assertTrue(resolve_ok.encrypted_for_processor)

        resolve_twice = validate_spt_resolution_and_payment_intent(
            flow="resolve_api",
            previously_resolved=True,
        )
        self.assertFalse(resolve_twice.allowed)
        self.assertEqual(resolve_twice.http_status, 400)
        self.assertEqual(resolve_twice.reason, "spt_resolve_rejected_400_already_resolved_single_use_only")

        resolve_after_pi = validate_spt_resolution_and_payment_intent(
            flow="resolve_api",
            previously_used_in_payment_intent=True,
        )
        self.assertFalse(resolve_after_pi.allowed)
        self.assertEqual(resolve_after_pi.reason, "spt_resolve_rejected_400_already_used_in_payment_intent")

        # Recurring SPT PaymentIntent forbids setup_future_usage
        pi_sfu_block = validate_spt_resolution_and_payment_intent(
            flow="payment_intent",
            setup_future_usage_set=True,
            recurring_interval_configured=True,
        )
        self.assertFalse(pi_sfu_block.allowed)
        self.assertEqual(pi_sfu_block.reason, "spt_forbids_setup_future_usage_on_payment_intent")

        pi_off_session_no_interval = validate_spt_resolution_and_payment_intent(
            flow="payment_intent",
            off_session=True,
            recurring_interval_configured=False,
        )
        self.assertFalse(pi_off_session_no_interval.allowed)
        self.assertEqual(pi_off_session_no_interval.reason, "off_session_requires_spt_recurring_interval")

        # Connect direct charge requires connected_account profile + Stripe-Account header
        connect_direct_bad = validate_spt_resolution_and_payment_intent(
            flow="payment_intent",
            connect_charge_type="direct",
            network_profile_owner="platform",
            stripe_account_header_present=False,
        )
        self.assertFalse(connect_direct_bad.allowed)
        self.assertEqual(
            connect_direct_bad.reason,
            "connect_direct_charge_requires_connected_account_profile_and_stripe_account_header",
        )

        # 2. Stripe Connect Catalog Imports & Asymmetric 4-Second Hook Timeout
        import_403 = validate_connect_catalog_import_and_hooks(
            product_catalog_imports_write_permission=False,
        )
        self.assertFalse(import_403.allowed)
        self.assertEqual(import_403.http_status, 403)

        import_expired_url = validate_connect_catalog_import_and_hooks(
            upload_elapsed_seconds=301,
        )
        self.assertFalse(import_expired_url.allowed)
        self.assertEqual(import_expired_url.http_status, 410)

        import_inv_replace = validate_connect_catalog_import_and_hooks(
            feed_type="inventory",
            mode="replace",
        )
        self.assertFalse(import_inv_replace.allowed)
        self.assertEqual(import_inv_replace.reason, "non_product_feed_requires_upsert_mode")

        # Price hook >4,000 ms falls back to feed and continues checkout!
        price_hook_fallback = validate_connect_catalog_import_and_hooks(
            feed_type="pricing",
            mode="upsert",
            price_hook_latency_ms=4600,
            approval_hook_latency_ms=350,
            finalize_checkout_application_fee_minor=250,
        )
        self.assertTrue(price_hook_fallback.allowed)
        self.assertTrue(price_hook_fallback.price_hook_fallback_to_feed)
        self.assertTrue(price_hook_fallback.checkout_continues)

        # Platform fee omitted when platform pays Stripe fees -> blocked
        zero_platform_fee = validate_connect_catalog_import_and_hooks(
            platform_pays_stripe_fees=True,
            finalize_checkout_application_fee_minor=0,
        )
        self.assertFalse(zero_platform_fee.allowed)
        self.assertEqual(
            zero_platform_fee.reason,
            "missing_finalize_checkout_application_fee_causes_platform_loss",
        )

        # 3. Service Bookings (180d SPT max, 409 slot_unavailable, 24h Idempotency-Key conflict) & MPP/AP4M
        booking_181d = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="service_booking",
            spt_ttl_days=181,
        )
        self.assertFalse(booking_181d.allowed)
        self.assertEqual(booking_181d.reason, "booking_spt_expiry_exceeds_180_days_max")

        booking_slot_taken = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="service_booking",
            spt_ttl_days=90,
            slot_already_taken=True,
        )
        self.assertFalse(booking_slot_taken.allowed)
        self.assertEqual(booking_slot_taken.http_status, 409)
        self.assertEqual(booking_slot_taken.error_code, "slot_unavailable")

        booking_idem_conflict = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="service_booking",
            idempotency_key_reused=True,
            payload_matches_original=False,
        )
        self.assertFalse(booking_idem_conflict.allowed)
        self.assertEqual(booking_idem_conflict.http_status, 409)

        # Monetized MCP dual-path & Machine Payment guards
        browser_redirect = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="monetized_mcp",
            accept_header="text/html,application/xhtml+xml",
        )
        self.assertTrue(browser_redirect.allowed)
        self.assertEqual(browser_redirect.http_status, 302)
        self.assertEqual(browser_redirect.route_mode, "browser_redirect_302")

        card_below_min = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="monetized_mcp",
            payment_rail="card_spt",
            amount_usd="0.49",
        )
        self.assertFalse(card_below_min.allowed)
        self.assertEqual(card_below_min.reason, "card_spt_below_0_50_usd_minimum")

        ny_stablecoin = evaluate_booking_and_mpp_dual_path_guard(
            scenario_kind="monetized_mcp",
            payment_rail="tempo_mpp",
            amount_usd="0.05",
            us_state="NY",
        )
        self.assertFalse(ny_stablecoin.allowed)
        self.assertEqual(ny_stablecoin.http_status, 403)
        self.assertEqual(ny_stablecoin.reason, "stablecoin_machine_payments_unavailable_in_new_york")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["stage_1754_guards"]["all_passed"])

    def test_stage_1755_visa_vic_mcp_rfc9207_and_stripe_agent_key_guards(self) -> None:
        # 1. Visa Intelligent Commerce (VIC) VTS Token + VPP Passkey Enrollment & Device Binding
        vic_no_cvv2 = validate_visa_vic_vts_passkey_enrollment(cvv2_present=False)
        self.assertFalse(vic_no_cvv2.allowed)
        self.assertEqual(
            vic_no_cvv2.reason,
            "vic_vts_pan_enrollment_requires_cvv2_for_agent_token_requestor",
        )

        vic_raw_pan = validate_visa_vic_vts_passkey_enrollment(raw_16_digit_token_stored_by_agent=True)
        self.assertFalse(vic_raw_pan.allowed)
        self.assertEqual(vic_raw_pan.reason, "vic_forbids_agent_storing_raw_16_digit_token_or_pan")

        # Existing passkey (action='AUTHENTICATE') skips device binding
        vic_existing = validate_visa_vic_vts_passkey_enrollment(attestation_action="AUTHENTICATE")
        self.assertTrue(vic_existing.allowed)
        self.assertEqual(vic_existing.device_binding_status, "SKIPPED")
        self.assertTrue(vic_existing.can_call_credentials_for_instruction)

        # Device binding CHALLENGE via out-of-band MAP notification
        vic_oob_ok = validate_visa_vic_vts_passkey_enrollment(
            attestation_action="REGISTER",
            device_binding_status="CHALLENGE",
            step_up_method="APP-TO-APP",
            map_oob_event="TOKEN_DEVICE_BINDING_APPROVED",
            map_oob_identifiers_matched=True,
        )
        self.assertTrue(vic_oob_ok.allowed)

        vic_oob_mismatch = validate_visa_vic_vts_passkey_enrollment(
            attestation_action="REGISTER",
            device_binding_status="CHALLENGE",
            step_up_method="OUTBOUNDCALL",
            map_oob_event="CARDHOLDER_STEPUP_APPROVED",
            map_oob_identifiers_matched=False,
        )
        self.assertFalse(vic_oob_mismatch.allowed)
        self.assertEqual(vic_oob_mismatch.http_status, 401)

        # Fail-closed Passkey setup & ban on silent agent retry
        vic_silent_retry = validate_visa_vic_vts_passkey_enrollment(
            passkey_setup_succeeded=False,
            silent_agent_retry_attempted=True,
        )
        self.assertFalse(vic_silent_retry.allowed)
        self.assertEqual(vic_silent_retry.reason, "vic_forbids_silent_agent_passkey_registration_retry")

        vic_fail_closed = validate_visa_vic_vts_passkey_enrollment(
            passkey_setup_succeeded=False,
            approved_without_passkey=False,
        )
        self.assertFalse(vic_fail_closed.allowed)
        self.assertFalse(vic_fail_closed.can_call_credentials_for_instruction)

        # 2. MCP OAuth 2.1 (2026-07-28) RFC 9207 `iss` Matrix & Step-Up Scope Union
        mcp_query_tok = validate_mcp_oauth21_rfc9207_and_stepup(access_token_in_query_string=True)
        self.assertFalse(mcp_query_tok.allowed)
        self.assertEqual(mcp_query_tok.reason, "mcp_forbids_access_token_in_uri_query_string")

        mcp_offline = validate_mcp_oauth21_rfc9207_and_stepup(
            www_authenticate_scopes=("commerce:checkout", "offline_access"),
        )
        self.assertFalse(mcp_offline.allowed)
        self.assertEqual(mcp_offline.reason, "mcp_protected_resource_forbids_offline_access_scope")

        mcp_missing_iss = validate_mcp_oauth21_rfc9207_and_stepup(
            as_iss_parameter_supported=True,
            callback_iss=None,
            is_error_response=True,
        )
        self.assertFalse(mcp_missing_iss.allowed)
        self.assertTrue(mcp_missing_iss.suppress_error_fields_display)

        # RFC 3986 §6.2.1 simple string comparison forbids case-folding or trailing-slash normalization
        mcp_case_mismatch = validate_mcp_oauth21_rfc9207_and_stepup(
            expected_as_issuer="https://auth.merchant.example",
            as_iss_parameter_supported=False,
            callback_iss="https://AUTH.merchant.example",
            is_error_response=True,
        )
        self.assertFalse(mcp_case_mismatch.allowed)
        self.assertTrue(mcp_case_mismatch.suppress_error_fields_display)
        self.assertEqual(
            mcp_case_mismatch.reason,
            "rfc9207_iss_mismatch_simple_string_comparison_failed",
        )

        mcp_stepup = validate_mcp_oauth21_rfc9207_and_stepup(
            previous_scopes=("mcp:tools", "commerce:read"),
            www_authenticate_scopes=("commerce:read", "commerce:checkout"),
            insufficient_scope_error=True,
            step_up_retry_count=0,
        )
        self.assertTrue(mcp_stepup.allowed)
        self.assertEqual(mcp_stepup.merged_scopes, ("mcp:tools", "commerce:read", "commerce:checkout"))

        # 3. Stripe Agent Restricted Keys (180d Payout Lock / Approval Rules) & Embedded RequestedSession
        stripe_180d = validate_stripe_agent_key_and_embedded_session(
            action_type="payout",
            days_since_last_transfer_or_payout=181,
            human_approval_granted=True,
        )
        self.assertFalse(stripe_180d.allowed)
        self.assertEqual(
            stripe_180d.reason,
            "stripe_api_key_transfer_payout_locked_after_180_days_inactivity",
        )

        stripe_no_approval = validate_stripe_agent_key_and_embedded_session(
            action_type="send_money",
            human_approval_granted=False,
        )
        self.assertFalse(stripe_no_approval.allowed)
        self.assertEqual(
            stripe_no_approval.reason,
            "stripe_agent_key_or_mcp_treasury_requires_human_approval",
        )

        stripe_proxy = validate_stripe_agent_key_and_embedded_session(
            source_blocked_proxy_vpn_tor=True,
        )
        self.assertFalse(stripe_proxy.allowed)
        self.assertEqual(
            stripe_proxy.reason,
            "stripe_advanced_access_policy_asn_country_or_proxy_blocked",
        )

        stripe_elem_bad = validate_stripe_agent_key_and_embedded_session(
            ui_surface="payment_element",
            payment_element_billing_details="auto",
        )
        self.assertFalse(stripe_elem_bad.allowed)
        self.assertEqual(
            stripe_elem_bad.reason,
            "embedded_payment_element_requires_billing_details_never_with_address_elements",
        )

        stripe_3ds_pending = validate_stripe_agent_key_and_embedded_session(
            spt_state="requires_action",
            buyer_completed_redirect_or_3ds=False,
        )
        self.assertFalse(stripe_3ds_pending.allowed)
        self.assertEqual(stripe_3ds_pending.spt_next_state, "requires_action")

        stripe_3ds_done = validate_stripe_agent_key_and_embedded_session(
            spt_state="requires_action",
            buyer_completed_redirect_or_3ds=True,
        )
        self.assertTrue(stripe_3ds_done.allowed)
        self.assertEqual(stripe_3ds_done.spt_next_state, "active")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["stage_1755_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("stage1755-sandbox", demo_zh)

    def test_stage_1756_webiq_rbac_stripe_mcp_nov30_and_bnpl_spt_guards(self) -> None:
        # 1. Azure ARM provisioning & Entra ID data-plane RBAC ("Cognitive Services User" or "Cognitive Services WebIQ User")
        bad_arm = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            arm_sku="S0",
        )
        self.assertFalse(bad_arm.allowed)
        self.assertEqual(
            bad_arm.reason,
            "webiq_arm_requires_grounding_kind_g3_sku_and_global_location",
        )

        owner_only = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            entra_assigned_roles=("Owner", "Contributor"),
        )
        self.assertFalse(owner_only.allowed)
        self.assertEqual(owner_only.http_status, 403)
        self.assertEqual(
            owner_only.reason,
            "webiq_entra_data_plane_requires_cognitive_services_user_or_webiq_user_role",
        )

        # 2. Browse passage validation on REST (400) vs MCP (200 + result.isError=True)
        rest_blank_query = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            browse_content_format="passage",
            browse_query="   ",
            mcp_transport=False,
        )
        self.assertFalse(rest_blank_query.allowed)
        self.assertEqual(rest_blank_query.http_status, 400)
        self.assertFalse(rest_blank_query.mcp_is_error)

        mcp_blank_query = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            browse_content_format="passage",
            browse_query="",
            mcp_transport=True,
        )
        self.assertFalse(mcp_blank_query.allowed)
        self.assertEqual(mcp_blank_query.http_status, 200)
        self.assertTrue(mcp_blank_query.mcp_is_error)

        passage_force_crawl = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            browse_content_format="passage",
            browse_query="return window",
            browse_live_crawl="force",
            mcp_transport=False,
        )
        self.assertFalse(passage_force_crawl.allowed)
        self.assertEqual(passage_force_crawl.http_status, 400)

        # 3. Stripe MCP Nov 30, 2026 Auth Cutoff (OAuth or Agent-tagged rk_* required) & Confirmation Gate
        mcp_sk_cutoff = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            post_nov30_2026_cutoff=True,
            stripe_mcp_auth_method="secret_key",
        )
        self.assertFalse(mcp_sk_cutoff.allowed)
        self.assertEqual(mcp_sk_cutoff.http_status, 401)
        self.assertTrue(mcp_sk_cutoff.oauth_discovery_challenge)

        mcp_untagged_rk = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            post_nov30_2026_cutoff=True,
            stripe_mcp_auth_method="untagged_restricted_key",
        )
        self.assertFalse(mcp_untagged_rk.allowed)
        self.assertEqual(mcp_untagged_rk.http_status, 401)

        mcp_refund_unconfirmed = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            stripe_mcp_auth_method="oauth",
            stripe_mcp_tool="create_refund",
            human_confirmation_granted=False,
        )
        self.assertFalse(mcp_refund_unconfirmed.allowed)
        self.assertEqual(mcp_refund_unconfirmed.http_status, 403)
        self.assertEqual(
            mcp_refund_unconfirmed.reason,
            "stripe_mcp_refund_or_treasury_tool_requires_human_confirmation",
        )

        # 4. Multi-Rail SPT (Affirm BNPL WebView human navigation & no forwarding payment_intent.requires_action)
        affirm_bot = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            spt_rail="affirm",
            agent_programmatic_webview_interaction=True,
        )
        self.assertFalse(affirm_bot.allowed)
        self.assertEqual(affirm_bot.http_status, 403)
        self.assertEqual(
            affirm_bot.reason,
            "affirm_bnpl_forbids_agent_webview_automation_or_uncontrolled_device",
        )

        affirm_uncontrolled_dev = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            spt_rail="affirm",
            agent_has_device_navigation_control=False,
        )
        self.assertFalse(affirm_uncontrolled_dev.allowed)
        self.assertEqual(affirm_uncontrolled_dev.http_status, 403)

        forward_pi_action = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            spt_rail="klarna",
            forward_pi_requires_action_to_agent=True,
        )
        self.assertFalse(forward_pi_action.allowed)
        self.assertEqual(forward_pi_action.http_status, 400)
        self.assertEqual(
            forward_pi_action.reason,
            "spt_forbids_forwarding_payment_intent_requires_action_to_agent",
        )

        all_ok = validate_stage1756_webiq_rbac_stripe_mcp_and_bnpl_spt(
            entra_assigned_roles=("Cognitive Services User",),
            browse_content_format="passage",
            browse_query="Nordic Audio return window",
            browse_live_crawl="fallback",
            stripe_mcp_auth_method="agent_restricted_key",
            stripe_mcp_tool="create_refund",
            human_confirmation_granted=True,
            spt_rail="affirm",
            agent_programmatic_webview_interaction=False,
            agent_has_device_navigation_control=True,
        )
        self.assertTrue(all_ok.allowed)
        self.assertEqual(all_ok.http_status, 200)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["stage_1756_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("stage1756-sandbox", demo_zh)


if __name__ == "__main__":
    unittest.main()
