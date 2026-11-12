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
    select_agentic_payment_and_grounding_architecture,
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

    def test_architect_payment_and_grounding_selection_matrix(self) -> None:
        # 1. Retail checkout + Pre-checkout price & policy verification -> Stripe SPT + Web IQ
        retail_ok = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="retail_checkout",
            grounding_need="pre_checkout_price_and_policy_verification",
            ticket_size_usd="79.00",
        )
        self.assertTrue(retail_ok.allowed)
        self.assertEqual(retail_ok.recommended_payment_rail, "stripe_spt")
        self.assertEqual(retail_ok.recommended_grounding_provider, "webiq")
        self.assertEqual(retail_ok.estimated_grounding_cost_per_1k_usd, 8.0)
        self.assertEqual(retail_ok.token_savings_multiplier, "7.1x")

        # 2. Global multi-acquirer checkout + Interactive DOM bypass -> Visa VIC + Bright Data
        vic_bd = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="global_multi_acquirer_checkout",
            grounding_need="interactive_dom_or_captcha_bypass",
            ticket_size_usd="120.00",
        )
        self.assertTrue(vic_bd.allowed)
        self.assertEqual(vic_bd.recommended_payment_rail, "visa_vic")
        self.assertEqual(vic_bd.recommended_grounding_provider, "brightdata")
        self.assertEqual(vic_bd.estimated_grounding_cost_per_1k_usd, 1.5)

        # 3. Per-call API micropayment + Semantic brand discovery -> x402 USDC + Exa
        x402_exa = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="api_micropayment_per_call",
            grounding_need="semantic_brand_and_research_discovery",
            unit_price_usd="0.020000",
        )
        self.assertTrue(x402_exa.allowed)
        self.assertEqual(x402_exa.recommended_payment_rail, "x402_usdc")
        self.assertEqual(x402_exa.recommended_grounding_provider, "exa")

        # 4. Streaming token metering: 200-unit whole-cent aligned batch ($0.000000 forfeiture) vs 50-unit unaligned
        mpp_aligned = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="streaming_token_metering",
            grounding_need="pre_checkout_price_and_policy_verification",
            mpp_batch_units=200,
            unit_price_usd="0.000350",
        )
        self.assertTrue(mpp_aligned.allowed)
        self.assertEqual(mpp_aligned.recommended_payment_rail, "stripe_mpp_tempo")
        self.assertEqual(mpp_aligned.sub_cent_forfeiture_usd, "0.000000")

        mpp_unaligned = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="streaming_token_metering",
            grounding_need="pre_checkout_price_and_policy_verification",
            mpp_batch_units=50,
            unit_price_usd="0.000350",
        )
        self.assertFalse(mpp_unaligned.allowed)
        self.assertEqual(mpp_unaligned.http_status, 422)
        self.assertEqual(mpp_unaligned.sub_cent_forfeiture_usd, "0.007500")
        self.assertEqual(
            mpp_unaligned.reason,
            "unaligned_mpp_batch_causes_sub_cent_truncation_forfeiture_align_to_200_units",
        )

        # 5. Foundry Bing Grounding is allowed for conversational Q&A, but blocked for autonomous payment digest
        bing_qa_ok = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="conversational_qa_only",
            grounding_need="managed_chat_qa",
        )
        self.assertTrue(bing_qa_ok.allowed)
        self.assertEqual(bing_qa_ok.recommended_grounding_provider, "foundry_bing_grounding")

        bing_checkout_block = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="retail_checkout",
            grounding_need="managed_chat_qa",
        )
        self.assertFalse(bing_checkout_block.allowed)
        self.assertEqual(bing_checkout_block.http_status, 422)
        self.assertEqual(
            bing_checkout_block.reason,
            "foundry_bing_grounding_hides_raw_passages_unsafe_for_autonomous_payment_digest",
        )

        # 6. Connect header trap & MCP OAuth 2.1 / Nov 30 cutoff guards
        connect_hdr_trap = select_agentic_payment_and_grounding_architecture(
            commerce_scenario="marketplace_split_checkout",
            connect_charge_mode="destination_no_obo",
            stripe_account_header_sent=True,
        )
        self.assertFalse(connect_hdr_trap.allowed)
        self.assertEqual(connect_hdr_trap.http_status, 400)

        mcp_cutoff = select_agentic_payment_and_grounding_architecture(
            mcp_auth_mode="legacy_secret_key",
        )
        self.assertFalse(mcp_cutoff.allowed)
        self.assertEqual(mcp_cutoff.http_status, 401)

        rfc9207_bad = select_agentic_payment_and_grounding_architecture(
            mcp_auth_mode="oauth21_rfc9207",
            rfc9207_iss_exact_match=False,
        )
        self.assertFalse(rfc9207_bad.allowed)
        self.assertEqual(rfc9207_bad.http_status, 400)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["architect_selection_guards"]["all_passed"])
        self.assertTrue(suite["b2b_procurement_mandate_guards"]["all_passed"])
        self.assertTrue(suite["cross_border_settlement_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("architect-selector-sandbox", demo_zh)
        self.assertIn("b2b-mandate-selector-sandbox", demo_zh)
        self.assertIn("cross-border-selector-sandbox", demo_zh)

    def test_cross_border_multi_currency_agent_settlement_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_cross_border_agent_settlement

        # 1. UK physical goods (inside 34 countries) -> stripe_spt_v2_multi_currency with chargeback protection
        uk_spt = evaluate_cross_border_agent_settlement(
            asset_class="physical_goods_or_saas",
            merchant_country="GB",
            landed_total_usd="262.40",
            mandate_ceiling_usd="280.00",
            fx_slippage_pct=0.6,
        )
        self.assertTrue(uk_spt.allowed)
        self.assertEqual(uk_spt.recommended_rail, "stripe_spt_v2_multi_currency")
        self.assertTrue(uk_spt.chargeback_protected)

        # 2. Brazil physical goods (outside 34 countries) -> automatic fallback to visa_vic_global_token
        br_vic = evaluate_cross_border_agent_settlement(
            asset_class="physical_goods_or_saas",
            merchant_country="BR",
            landed_total_usd="180.00",
            mandate_ceiling_usd="220.00",
            fx_slippage_pct=0.8,
        )
        self.assertTrue(br_vic.allowed)
        self.assertEqual(br_vic.recommended_rail, "visa_vic_global_token")
        self.assertTrue(br_vic.chargeback_protected)

        # 3. Physical goods forced onto irreversible onchain_stablecoin -> blocked with HTTP 422
        phys_usdc = evaluate_cross_border_agent_settlement(
            asset_class="physical_goods_or_saas",
            requested_rail="onchain_stablecoin",
        )
        self.assertFalse(phys_usdc.allowed)
        self.assertEqual(phys_usdc.http_status, 422)
        self.assertEqual(phys_usdc.action, "Send to a human")

        # 4. Landed cost tariff shock or >2.0% FX slippage -> blocked with HTTP 422 Confirm
        tariff_shock = evaluate_cross_border_agent_settlement(
            asset_class="physical_goods_or_saas",
            landed_total_usd="318.00",
            mandate_ceiling_usd="280.00",
        )
        self.assertFalse(tariff_shock.allowed)
        self.assertEqual(tariff_shock.http_status, 422)

        fx_spike = evaluate_cross_border_agent_settlement(
            asset_class="physical_goods_or_saas",
            fx_slippage_pct=3.4,
        )
        self.assertFalse(fx_spike.allowed)
        self.assertEqual(fx_spike.http_status, 422)

        # 5. Metered API: GCD aligned 200 units at $0.000550 -> $0.000000 forfeiture, whereas 80 units -> 422
        api_ok = evaluate_cross_border_agent_settlement(
            asset_class="metered_digital_api",
            unit_price_usd="0.000550",
            batch_units=200,
            buyer_us_state="CA",
        )
        self.assertTrue(api_ok.allowed)
        self.assertEqual(api_ok.min_zero_truncation_batch_units, 200)
        self.assertEqual(api_ok.sub_cent_forfeited_usd, "0.000000")

        api_unaligned = evaluate_cross_border_agent_settlement(
            asset_class="metered_digital_api",
            unit_price_usd="0.000550",
            batch_units=80,
            buyer_us_state="CA",
        )
        self.assertFalse(api_unaligned.allowed)
        self.assertEqual(api_unaligned.http_status, 422)
        self.assertEqual(api_unaligned.sub_cent_forfeited_usd, "0.004000")

        api_ny = evaluate_cross_border_agent_settlement(
            asset_class="metered_digital_api",
            unit_price_usd="0.000550",
            batch_units=200,
            buyer_us_state="NY",
        )
        self.assertFalse(api_ny.allowed)
        self.assertEqual(api_ny.http_status, 403)

    def test_b2b_procurement_policy_bound_spend_mandate_vs_hitl_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_b2b_procurement_spend_mandate

        # 1. Green Zone: tail spend <= $2,500, AVL vendor, valid MCC, 30d returns -> auto-mint SPT v2 in 376ms
        green = evaluate_b2b_procurement_spend_mandate(
            vendor_in_avl=True,
            mcc_allowed=True,
            order_total_usd="1920.00",
            supplier_rail="marketplace_connect",
        )
        self.assertTrue(green.allowed)
        self.assertEqual(green.http_status, 200)
        self.assertEqual(green.governance_tier, "green_auto_mandate")
        self.assertEqual(green.minted_credential_type, "stripe_connect_spt_v2")
        self.assertEqual(green.action, "Act automatically")

        # 2. Amber Zone unsigned: $4,800 in ($2.5k, $25k] -> 403 + MCP WWW-Authenticate insufficient_scope challenge
        amber_unsigned = evaluate_b2b_procurement_spend_mandate(
            vendor_in_avl=True,
            mcc_allowed=True,
            order_total_usd="4800.00",
            supplier_rail="external_card_supplier",
            manager_passkey_stepup_signed=False,
        )
        self.assertFalse(amber_unsigned.allowed)
        self.assertEqual(amber_unsigned.http_status, 403)
        self.assertEqual(amber_unsigned.governance_tier, "amber_stepup_hitl")
        self.assertIn("insufficient_scope", amber_unsigned.www_authenticate_challenge or "")
        self.assertEqual(amber_unsigned.action, "Confirm")

        # 3. Amber Zone signed with manager FIDO2 Passkey -> 200 + single-use Visa VTS VCN minted
        amber_signed = evaluate_b2b_procurement_spend_mandate(
            vendor_in_avl=True,
            mcc_allowed=True,
            order_total_usd="4800.00",
            supplier_rail="external_card_supplier",
            manager_passkey_stepup_signed=True,
        )
        self.assertTrue(amber_signed.allowed)
        self.assertEqual(amber_signed.http_status, 200)
        self.assertEqual(amber_signed.minted_credential_type, "visa_vts_single_use_vcn")

        # 4. Red Zone blocks: prompt injection, non-AVL vendor, sub-30d return policy, price mismatch, >$25k cap
        red_inj = evaluate_b2b_procurement_spend_mandate(prompt_injection_detected=True)
        self.assertFalse(red_inj.allowed)
        self.assertEqual(red_inj.governance_tier, "red_hard_block")

        red_avl = evaluate_b2b_procurement_spend_mandate(vendor_in_avl=False)
        self.assertFalse(red_avl.allowed)
        self.assertEqual(red_avl.http_status, 403)

        red_ret = evaluate_b2b_procurement_spend_mandate(verified_return_days=7)
        self.assertFalse(red_ret.allowed)
        self.assertEqual(red_ret.http_status, 422)

        red_digest = evaluate_b2b_procurement_spend_mandate(webiq_price_digest_matches=False)
        self.assertFalse(red_digest.allowed)
        self.assertEqual(red_digest.http_status, 422)

        red_cap = evaluate_b2b_procurement_spend_mandate(order_total_usd="68000.00")
        self.assertFalse(red_cap.allowed)
        self.assertEqual(red_cap.governance_tier, "red_hard_block")
        self.assertEqual(red_cap.action, "Send to a human")

    def test_agent_identity_web_bot_auth_tap_vs_waf_selection_and_provenance(self) -> None:
        from pathlib import Path
        from lab.webiq_commerce_demo import evaluate_agent_identity_and_waf_policy

        # 1. Valid RFC 9421 Ed25519 signature + JWKS keyid + Visa TAP token -> 200 fast lane (1.8ms)
        ok_tap = evaluate_agent_identity_and_waf_policy(
            request_channel="commerce_checkout_api",
            has_rfc9421_signature=True,
            jwks_keyid_registered=True,
            content_digest_matches=True,
            signature_age_seconds=8,
            nonce_reused=False,
            visa_tap_token_attached=True,
        )
        self.assertTrue(ok_tap.allowed)
        self.assertEqual(ok_tap.http_status, 200)
        self.assertEqual(ok_tap.edge_route, "verified_rfc9421_visa_tap_fast_lane")
        self.assertEqual(ok_tap.action_pill, "Act automatically")

        # 2. Unsigned spoofed User-Agent on API -> 401 rejected
        spoof = evaluate_agent_identity_and_waf_policy(
            request_channel="commerce_checkout_api",
            has_rfc9421_signature=False,
        )
        self.assertFalse(spoof.allowed)
        self.assertEqual(spoof.http_status, 401)
        self.assertEqual(spoof.action_pill, "Send to a human")

        # 3. Tampered Content-Digest or >300s replay -> 401 rejected
        tampered = evaluate_agent_identity_and_waf_policy(
            request_channel="commerce_checkout_api",
            has_rfc9421_signature=True,
            content_digest_matches=False,
        )
        self.assertFalse(tampered.allowed)
        self.assertEqual(tampered.http_status, 401)

        replayed = evaluate_agent_identity_and_waf_policy(
            request_channel="commerce_checkout_api",
            has_rfc9421_signature=True,
            signature_age_seconds=420,
            nonce_reused=True,
        )
        self.assertFalse(replayed.allowed)
        self.assertEqual(replayed.http_status, 401)

        # 4. Verified crawler exceeding free QPS quota without x402 proof -> 402 Payment Required
        crawl_402 = evaluate_agent_identity_and_waf_policy(
            request_channel="catalog_price_crawl",
            has_rfc9421_signature=True,
            crawl_qps=120,
            free_qps_quota=50,
            x402_payment_proof_attached=False,
        )
        self.assertFalse(crawl_402.allowed)
        self.assertEqual(crawl_402.http_status, 402)
        self.assertEqual(crawl_402.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agent_identity_waf_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("web-bot-auth-selector-sandbox", demo_zh)

        # Verify single-topic split FAQs and explicit provenance tags exist
        repo_root = Path(__file__).resolve().parent.parent
        for rel_doc in (
            "docs/agentic-payment-rails-spt-vic-x402-selection-faq.md",
            "docs/agentic-payment-rails-spt-vic-x402-selection-faq.en.md",
            "docs/webiq-vs-exa-brightdata-grounding-selection-faq.md",
            "docs/webiq-vs-exa-brightdata-grounding-selection-faq.en.md",
            "docs/b2b-procurement-mandate-vs-hitl-selection-faq.md",
            "docs/b2b-procurement-mandate-vs-hitl-selection-faq.en.md",
            "docs/cross-border-agent-settlement-x402-vs-card-network-faq.md",
            "docs/cross-border-agent-settlement-x402-vs-card-network-faq.en.md",
            "docs/ecommerce-agent-identity-web-bot-auth-tap-vs-waf-faq.md",
            "docs/ecommerce-agent-identity-web-bot-auth-tap-vs-waf-faq.en.md",
            "docs/bnpl-webview-handover-vs-headless-agent-faq.md",
            "docs/bnpl-webview-handover-vs-headless-agent-faq.en.md",
            "docs/multi-merchant-split-cart-saga-vs-connect-faq.md",
            "docs/multi-merchant-split-cart-saga-vs-connect-faq.en.md",
            "docs/post-purchase-return-eligibility-vs-refund-confirmation-faq.md",
            "docs/post-purchase-return-eligibility-vs-refund-confirmation-faq.en.md",
            "docs/recurring-replenishment-spt-cadence-vs-vaulting-faq.md",
            "docs/recurring-replenishment-spt-cadence-vs-vaulting-faq.en.md",
            "docs/catalog-feed-manifest-barrier-vs-webhook-4s-sla-faq.md",
            "docs/catalog-feed-manifest-barrier-vs-webhook-4s-sla-faq.en.md",
            "docs/digital-tax-vat-mor-vs-seller-of-record-faq.md",
            "docs/digital-tax-vat-mor-vs-seller-of-record-faq.en.md",
            "docs/service-booking-180d-spt-ttl-vs-409-slot-conflict-faq.md",
            "docs/service-booking-180d-spt-ttl-vs-409-slot-conflict-faq.en.md",
            "docs/pci-dss-spt-resolve-aoc-vs-payment-intent-faq.md",
            "docs/pci-dss-spt-resolve-aoc-vs-payment-intent-faq.en.md",
            "docs/chargeback-dispute-cryptographic-evidence-vs-manual-representment-faq.md",
            "docs/chargeback-dispute-cryptographic-evidence-vs-manual-representment-faq.en.md",
            "docs/dynamic-pricing-quote-lock-ttl-vs-mandate-drift-faq.md",
            "docs/dynamic-pricing-quote-lock-ttl-vs-mandate-drift-faq.en.md",
            "docs/mcp-oauth-audience-stepup-vs-confused-deputy-faq.md",
            "docs/mcp-oauth-audience-stepup-vs-confused-deputy-faq.en.md",
            "docs/ap2-circuit-breaker-recall-tripwire-vs-backoff-faq.md",
            "docs/ap2-circuit-breaker-recall-tripwire-vs-backoff-faq.en.md",
            "docs/idempotency-payload-hash-vs-retry-double-charge-faq.md",
            "docs/idempotency-payload-hash-vs-retry-double-charge-faq.en.md",
            "docs/privacy-pii-vaultless-shipping-token-vs-context-leak-faq.md",
            "docs/privacy-pii-vaultless-shipping-token-vs-context-leak-faq.en.md",
            "docs/inventory-reservation-ttl-hold-vs-oversell-compensation-faq.md",
            "docs/inventory-reservation-ttl-hold-vs-oversell-compensation-faq.en.md",
            "docs/multi-currency-fx-rate-lock-vs-dcc-spread-trap-faq.md",
            "docs/multi-currency-fx-rate-lock-vs-dcc-spread-trap-faq.en.md",
            "docs/loyalty-coupon-atomic-redemption-vs-stacking-abuse-faq.md",
            "docs/loyalty-coupon-atomic-redemption-vs-stacking-abuse-faq.en.md",
            "docs/age-verification-zkp-vc-vs-id-upload-compliance-faq.md",
            "docs/age-verification-zkp-vc-vs-id-upload-compliance-faq.en.md",
            "docs/high-ticket-escrow-delivery-attestation-vs-instant-settlement-faq.md",
            "docs/high-ticket-escrow-delivery-attestation-vs-instant-settlement-faq.en.md",
            "docs/indirect-prompt-injection-dom-poisoning-vs-signed-acp-feed-faq.md",
            "docs/indirect-prompt-injection-dom-poisoning-vs-signed-acp-feed-faq.en.md",
            "docs/multi-agent-shared-budget-allocation-vs-race-spend-faq.md",
            "docs/multi-agent-shared-budget-allocation-vs-race-spend-faq.en.md",
            "docs/return-logistics-reverse-escrow-vs-refund-before-scan-abuse-faq.md",
            "docs/return-logistics-reverse-escrow-vs-refund-before-scan-abuse-faq.en.md",
            "docs/b2b-net30-po-three-way-match-vs-upfront-card-capture-faq.md",
            "docs/b2b-net30-po-three-way-match-vs-upfront-card-capture-faq.en.md",
            "docs/esg-carbon-footprint-verified-shipping-vs-greenwashing-surcharge-faq.md",
            "docs/esg-carbon-footprint-verified-shipping-vs-greenwashing-surcharge-faq.en.md",
            "docs/price-drop-watchlist-mandate-vs-cart-recovery-spam-faq.md",
            "docs/price-drop-watchlist-mandate-vs-cart-recovery-spam-faq.en.md",
            "docs/warranty-claim-telemetry-attestation-vs-serial-fraud-faq.md",
            "docs/warranty-claim-telemetry-attestation-vs-serial-fraud-faq.en.md",
            "docs/b2b-moq-syndicate-escrow-vs-stranded-deposit-shortfall-faq.md",
            "docs/b2b-moq-syndicate-escrow-vs-stranded-deposit-shortfall-faq.en.md",
            "docs/b2b-sealed-bid-reverse-auction-vs-price-signaling-collusion-faq.md",
            "docs/b2b-sealed-bid-reverse-auction-vs-price-signaling-collusion-faq.en.md",
            "docs/cross-border-customs-hs-tariff-mandate-vs-seizure-faq.md",
            "docs/cross-border-customs-hs-tariff-mandate-vs-seizure-faq.en.md",
            "docs/saas-seat-trueup-telemetry-mandate-vs-shelfware-auto-renewal-faq.md",
            "docs/saas-seat-trueup-telemetry-mandate-vs-shelfware-auto-renewal-faq.en.md",
            "docs/freight-detention-demurrage-sla-mandate-vs-carrier-surcharge-faq.md",
            "docs/freight-detention-demurrage-sla-mandate-vs-carrier-surcharge-faq.en.md",
        ):
            doc_text = (repo_root / rel_doc).read_text(encoding="utf-8")
            self.assertIn("synthetic_policy", doc_text, f"Missing synthetic_policy tag in {rel_doc}")
            self.assertIn("not_measured", doc_text, f"Missing not_measured tag in {rel_doc}")

    def test_catalog_feed_manifest_barrier_and_4s_webhook_sla_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_catalog_feed_and_webhook_sla_policy

        # 1. SFTP shards uploaded without manifest.json barrier -> 409 staged awaiting manifest
        no_manifest = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="sftp_bulk_ingest",
            manifest_present=False,
        )
        self.assertFalse(no_manifest.allowed)
        self.assertEqual(no_manifest.http_status, 409)
        self.assertEqual(no_manifest.lane, "staged_awaiting_manifest_barrier")

        # 2. Connect feed import with mode='replace' on inventory feed -> 400 Bad Request
        inv_replace = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="connect_feed_import",
            feed_type="inventory",
            import_mode="replace",
        )
        self.assertFalse(inv_replace.allowed)
        self.assertEqual(inv_replace.http_status, 400)
        self.assertEqual(inv_replace.lane, "blocked_non_product_feed_forbids_replace")

        # 3. Read hook > 4,000 ms with fresh upsert feed (120s <= 900s) -> 200 graceful fallback
        read_fallback = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="product_price_availability",
            hook_elapsed_ms=4320,
            feed_age_seconds=120,
        )
        self.assertTrue(read_fallback.allowed)
        self.assertEqual(read_fallback.http_status, 200)
        self.assertTrue(read_fallback.used_catalog_fallback)
        self.assertEqual(read_fallback.lane, "fallback_to_fresh_upsert_feed")

        # 4. Read hook > 4,000 ms with stale feed (1800s > 900s) -> 503 Confirm
        read_stale = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="product_price_availability",
            hook_elapsed_ms=4320,
            feed_age_seconds=1800,
        )
        self.assertFalse(read_stale.allowed)
        self.assertEqual(read_stale.http_status, 503)
        self.assertEqual(read_stale.lane, "blocked_read_hook_timeout_and_stale_catalog_feed")

        # 5. Write hook finalize_checkout > 4,000 ms -> 504 hard decline ($0.00 charged, NEVER falls back to cache)
        write_timeout = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="finalize_checkout",
            hook_elapsed_ms=4150,
        )
        self.assertFalse(write_timeout.allowed)
        self.assertEqual(write_timeout.http_status, 504)
        self.assertEqual(write_timeout.spt_charged_usd, "0.00")
        self.assertEqual(write_timeout.lane, "hard_decline_finalize_timeout_no_charge")

        # 6. Write hook finalize_checkout <= 4,000 ms with Redis lock -> 200 OK ($79.00 charged)
        write_ok = evaluate_catalog_feed_and_webhook_sla_policy(
            stage="finalize_checkout",
            hook_elapsed_ms=265,
            inventory_locked=True,
            order_amount_usd="79.00",
        )
        self.assertTrue(write_ok.allowed)
        self.assertEqual(write_ok.http_status, 200)
        self.assertEqual(write_ok.spt_charged_usd, "79.00")
        self.assertEqual(write_ok.lane, "finalize_checkout_confirmed_spt_captured")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["catalog_webhook_sla_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("catalog-webhook-sla-sandbox", demo_zh)

    def test_digital_tax_mor_vs_sor_and_b2b_reverse_charge_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_digital_tax_mor_vs_sor_policy

        # 1. Merchant without local EU tax ID -> routes to MOR_MANAGED_TAX ($119.00 locked)
        mor = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=False,
            seller_country="US",
            buyer_country="DE",
            net_amount_cents=10000,
            spt_max_amount_cents=11900,
            statutory_vat_rate_pct=19.0,
        )
        self.assertTrue(mor.allowed)
        self.assertEqual(mor.http_status, 200)
        self.assertEqual(mor.selected_tax_model, "MOR_MANAGED_TAX")
        self.assertEqual(mor.tax_liability_owner, "MOR_PLATFORM")
        self.assertEqual(mor.locked_spt_total_usd, "119.00")

        # 2. Merchant with local EU tax ID -> routes to SOR_STRIPE_TAX ($119.00 locked)
        sor = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=True,
            seller_country="IE",
            buyer_country="DE",
            net_amount_cents=10000,
            spt_max_amount_cents=11900,
            statutory_vat_rate_pct=19.0,
        )
        self.assertTrue(sor.allowed)
        self.assertEqual(sor.selected_tax_model, "SOR_STRIPE_TAX")
        self.assertEqual(sor.tax_liability_owner, "MERCHANT_SOR")

        # 3. Cross-border B2B with verified VAT ID + Web IQ entity name match -> 0% Reverse-Charge ($1,000.00)
        b2b_ok = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=True,
            seller_country="IE",
            buyer_country="DE",
            net_amount_cents=100000,
            spt_max_amount_cents=100000,
            statutory_vat_rate_pct=19.0,
            is_b2b_order=True,
            buyer_tax_id_verified=True,
            webiq_entity_name_matched=True,
        )
        self.assertTrue(b2b_ok.allowed)
        self.assertEqual(b2b_ok.selected_tax_model, "SOR_B2B_REVERSE_CHARGE_0PCT")
        self.assertEqual(b2b_ok.applied_tax_rate_pct, 0.0)
        self.assertEqual(b2b_ok.locked_spt_total_usd, "1000.00")

        # 4. Hijacked VAT ID (Web IQ entity name mismatch) -> fails closed to 19% statutory VAT ($1,190.00)
        b2b_hijack = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=True,
            seller_country="IE",
            buyer_country="DE",
            net_amount_cents=100000,
            spt_max_amount_cents=119000,
            statutory_vat_rate_pct=19.0,
            is_b2b_order=True,
            buyer_tax_id_verified=True,
            webiq_entity_name_matched=False,
        )
        self.assertTrue(b2b_hijack.allowed)
        self.assertEqual(b2b_hijack.selected_tax_model, "SOR_B2B_FALLBACK_STATUTORY_VAT")
        self.assertEqual(b2b_hijack.applied_tax_rate_pct, 19.0)
        self.assertEqual(b2b_hijack.locked_spt_total_usd, "1190.00")

        # 5. Post-mandate tax addition exceeding net-price SPT ceiling -> 422 blocked
        post_tax = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=True,
            seller_country="IE",
            buyer_country="DE",
            net_amount_cents=10000,
            spt_max_amount_cents=10000,
            statutory_vat_rate_pct=19.0,
            tax_calculated_pre_mandate=False,
        )
        self.assertFalse(post_tax.allowed)
        self.assertEqual(post_tax.http_status, 422)

        # 6. Connect Stripe-Account header without on_behalf_of -> 400 blocked
        obo_conflict = evaluate_digital_tax_mor_vs_sor_policy(
            merchant_has_local_tax_id=True,
            is_connect_marketplace=True,
            on_behalf_of_account=None,
            stripe_account_header="acct_sub_de_01",
        )
        self.assertFalse(obo_conflict.allowed)
        self.assertEqual(obo_conflict.http_status, 400)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["digital_tax_compliance_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("digital-tax-mor-sor-sandbox", demo_zh)

    def test_service_booking_180d_spt_and_409_slot_conflict_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_service_booking_180d_spt_and_slot_conflict

        # 1. 45-day hotel booking (<= 180d) -> DEFERRED_SPT_180D_LOCKED ($240.00)
        bk_ok = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=45,
            order_amount_cents=24000,
            spt_max_amount_cents=24000,
        )
        self.assertTrue(bk_ok.allowed)
        self.assertEqual(bk_ok.http_status, 200)
        self.assertEqual(bk_ok.booking_lane, "DEFERRED_SPT_180D_LOCKED")
        self.assertEqual(bk_ok.captured_amount_usd, "240.00")

        # 2. HTTP 409 slot conflict with candidate within ±15m same-day tolerance -> auto-shifted 200 OK
        shift_ok = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=14,
            order_amount_cents=12000,
            spt_max_amount_cents=12000,
            slot_conflict_409=True,
            candidate_slot_shift_minutes=15,
            allowed_slot_shift_minutes=15,
            candidate_same_day=True,
            candidate_price_cents=12000,
        )
        self.assertTrue(shift_ok.allowed)
        self.assertEqual(shift_ok.http_status, 200)
        self.assertEqual(shift_ok.booking_lane, "AUTO_SHIFTED_WITHIN_15M_TOLERANCE")

        # 3. HTTP 409 slot conflict with candidate 120m away (> 15m tolerance) -> 409 Confirm ($0.00 charged)
        shift_hold = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=14,
            order_amount_cents=12000,
            spt_max_amount_cents=12000,
            slot_conflict_409=True,
            candidate_slot_shift_minutes=120,
            allowed_slot_shift_minutes=15,
        )
        self.assertFalse(shift_hold.allowed)
        self.assertEqual(shift_hold.http_status, 409)
        self.assertEqual(shift_hold.captured_amount_usd, "0.00")
        self.assertEqual(shift_hold.action_pill, "Confirm")

        # 4. Cancellation 72h prior (>= 48h Web IQ grounded free window) -> $0.00 + SPT deactivated
        free_cancel = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=45,
            order_amount_cents=24000,
            cancellation_requested=True,
            hours_before_arrival=72,
            grounded_free_cancel_hours=48,
        )
        self.assertTrue(free_cancel.allowed)
        self.assertEqual(free_cancel.spt_status, "deactivated")
        self.assertEqual(free_cancel.captured_amount_usd, "0.00")

        # 5. Late cancellation overcharge attempt (100% > 50% grounded tier) -> 422 blocked
        overcharge = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=45,
            order_amount_cents=24000,
            cancellation_requested=True,
            hours_before_arrival=12,
            grounded_free_cancel_hours=48,
            grounded_max_penalty_pct=50.0,
            requested_penalty_pct=100.0,
        )
        self.assertFalse(overcharge.allowed)
        self.assertEqual(overcharge.http_status, 422)

        # 6. >180-day single SPT horizon (240 days) -> 400 blocked
        over_180d = evaluate_service_booking_180d_spt_and_slot_conflict(
            booking_horizon_days=240,
            order_amount_cents=180000,
        )
        self.assertFalse(over_180d.allowed)
        self.assertEqual(over_180d.http_status, 400)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["service_booking_180d_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("service-booking-180d-sandbox", demo_zh)

    def test_pci_dss_spt_resolve_aoc_vs_payment_intent_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_pci_dss_spt_resolve_vs_payment_intent_policy

        # 1. Standard Stripe Native PaymentIntent consumption -> SAQ-A, 0 raw PAN bytes, 200 OK
        pi_ok = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="stripe_native",
        )
        self.assertTrue(pi_ok.allowed)
        self.assertEqual(pi_ok.http_status, 200)
        self.assertEqual(pi_ok.consumption_lane, "CONSUMED_STRIPE_PI")
        self.assertEqual(pi_ok.pci_compliance_tier, "SAQ-A")
        self.assertEqual(pi_ok.raw_pan_bytes_exposed, 0)

        # 2. Certified Multi-PSP Resolve with PCI AoC + scoped rk_live_ + RSA encryption_block[0..64] -> 200 OK, 0 raw bytes
        res_ok = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="adyen_eu",
            has_pci_aoc=True,
            api_key_type="rk_live_resolve_only",
            encryption_certificate_present=True,
            encryption_start_index=0,
            encryption_end_index=64,
        )
        self.assertTrue(res_ok.allowed)
        self.assertEqual(res_ok.http_status, 200)
        self.assertEqual(res_ok.consumption_lane, "RESOLVED_EXTERNAL_ENCRYPTED")
        self.assertEqual(res_ok.raw_pan_bytes_exposed, 0)
        self.assertEqual(res_ok.spt_lock_state, "RESOLVED_EXTERNAL")

        # 3. Missing PCI AoC or unscoped sk_live_ key -> 403 Forbidden
        no_aoc = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="adyen_eu",
            has_pci_aoc=False,
            api_key_type="sk_live_full",
        )
        self.assertFalse(no_aoc.allowed)
        self.assertEqual(no_aoc.http_status, 403)

        # 4. Mutual-Exclusivity Lock: calling PaymentIntent after Resolve -> 409 Conflict
        mutex_pi = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="stripe_native",
            already_resolved_external=True,
        )
        self.assertFalse(mutex_pi.allowed)
        self.assertEqual(mutex_pi.http_status, 409)
        self.assertEqual(mutex_pi.consumption_lane, "BLOCKED_MUTUAL_EXCLUSIVITY_ALREADY_RESOLVED")

        # 5. Pre-Resolve Web IQ detects external PSP degraded -> lossless failover to Stripe PaymentIntent (200 OK)
        failover_ok = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="worldpay_uk",
            has_pci_aoc=True,
            api_key_type="rk_live_resolve_only",
            webiq_external_psp_status="degraded",
        )
        self.assertTrue(failover_ok.allowed)
        self.assertEqual(failover_ok.http_status, 200)
        self.assertEqual(failover_ok.consumption_lane, "PRE_RESOLVE_FAILOVER_TO_PI")

        # 6. Invalid encryption_block byte-slice bounds -> 400 Bad Request
        bad_slice = evaluate_pci_dss_spt_resolve_vs_payment_intent_policy(
            target_psp="adyen_eu",
            has_pci_aoc=True,
            api_key_type="rk_live_resolve_only",
            encryption_start_index=80,
            encryption_end_index=32,
        )
        self.assertFalse(bad_slice.allowed)
        self.assertEqual(bad_slice.http_status, 400)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["pci_dss_spt_resolve_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("pci-dss-spt-resolve-sandbox", demo_zh)

    def test_chargeback_dispute_cryptographic_evidence_vs_manual_representment_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_chargeback_dispute_evidence_and_deflection

        # 1. Pre-dispute small ticket ($18.00 < $25.00) -> auto-refund deflected, saves $15.00 fee, 0 bps ratio impact
        deflect = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=1800,
            pre_dispute_window=True,
        )
        self.assertTrue(deflect.allowed)
        self.assertEqual(deflect.http_status, 200)
        self.assertEqual(deflect.dispute_lane, "PRE_DISPUTE_AUTO_REFUND_DEFLECTED")
        self.assertEqual(deflect.dispute_fee_saved_usd, "15.00")
        self.assertEqual(deflect.chargeback_ratio_impact_bps, 0)

        # 2. High-ticket 10.4 fraud with ECI 05 Passkey/3DS shift -> auto-win via issuer liability shift
        eci05 = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=68000,
            reason_code="10.4_fraud",
            has_eci_05_liability_shift=True,
        )
        self.assertTrue(eci05.allowed)
        self.assertEqual(eci05.dispute_lane, "ISSUER_LIABILITY_SHIFT_AUTO_WIN")

        # 3. 10.4 friendly fraud with valid CE 3.0 (2 orders 180d old) + signed MandateVC + cloud IP stripped -> 200 OK
        ce30_ok = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=42000,
            reason_code="10.4_fraud",
            has_eci_05_liability_shift=False,
            ce30_prior_undisputed_count=2,
            ce30_history_age_days=180,
            submitted_ip_is_cloud_agent_egress=False,
        )
        self.assertTrue(ce30_ok.allowed)
        self.assertEqual(ce30_ok.dispute_lane, "SUBMITTED_CE30_MANDATE_BUNDLE")

        # 4. 13.7 cancellation/terms dispute with checkout-time Web IQ terms_sha256 -> 200 OK
        terms_ok = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=24000,
            reason_code="13.7_terms_dispute",
        )
        self.assertTrue(terms_ok.allowed)
        self.assertEqual(terms_ok.dispute_lane, "SUBMITTED_WEBIQ_TERMS_SNAPSHOT_BUNDLE")

        # 5. Submitting cloud AI Agent egress IP as buyer IP -> 422 blocked
        cloud_ip = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=42000,
            reason_code="10.4_fraud",
            submitted_ip_is_cloud_agent_egress=True,
        )
        self.assertFalse(cloud_ip.allowed)
        self.assertEqual(cloud_ip.http_status, 422)

        # 6. 13.7 dispute missing checkout-time Web IQ terms_sha256 -> 422 blocked
        no_hash = evaluate_chargeback_dispute_evidence_and_deflection(
            dispute_amount_cents=24000,
            reason_code="13.7_terms_dispute",
            webiq_terms_snapshot_sha256=None,
        )
        self.assertFalse(no_hash.allowed)
        self.assertEqual(no_hash.http_status, 422)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["chargeback_dispute_evidence_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("chargeback-dispute-evidence-sandbox", demo_zh)

    def test_dynamic_pricing_quote_lock_ttl_vs_mandate_drift_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_dynamic_pricing_quote_lock_and_drift_policy

        # 1. Active merchant quote-lock token honors $79.00 even when spot price surges to $89.00
        quote_ok = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=7900,
            live_price_cents=8900,
            has_merchant_quote_lock=True,
            quote_remaining_ttl_seconds=180,
        )
        self.assertTrue(quote_ok.allowed)
        self.assertEqual(quote_ok.http_status, 200)
        self.assertEqual(quote_ok.pricing_lane, "COMMITTED_QUOTE_LOCK_HONORED")
        self.assertEqual(quote_ok.settled_amount_cents, 7900)
        self.assertEqual(quote_ok.buyer_savings_cents, 1000)

        # 2. Expired merchant quote-lock TTL -> 409 blocked
        quote_exp = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=7900,
            live_price_cents=8900,
            has_merchant_quote_lock=True,
            quote_remaining_ttl_seconds=-60,
        )
        self.assertFalse(quote_exp.allowed)
        self.assertEqual(quote_exp.http_status, 409)
        self.assertEqual(quote_exp.pricing_lane, "BLOCKED_QUOTE_LOCK_EXPIRED")

        # 3. Airfare ticks from $500.00 to $508.00 within +3.0% ($515.00) bounded slippage -> 200 OK
        slip_ok = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=50000,
            live_price_cents=50800,
            max_amount_cents=51500,
            allow_bounded_slippage=True,
        )
        self.assertTrue(slip_ok.allowed)
        self.assertEqual(slip_ok.pricing_lane, "COMMITTED_WITHIN_BOUNDED_SLIPPAGE")
        self.assertEqual(slip_ok.settled_amount_cents, 50800)
        self.assertEqual(slip_ok.slippage_applied_cents, 800)

        # 4. Price drops from $500.00 to $485.00 -> captures lower $485.00 and saves $15.00 for buyer
        drop_ok = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=50000,
            live_price_cents=48500,
            max_amount_cents=51500,
            allow_bounded_slippage=True,
        )
        self.assertTrue(drop_ok.allowed)
        self.assertEqual(drop_ok.pricing_lane, "COMMITTED_PRICE_DROP_SAVINGS_CAPTURED")
        self.assertEqual(drop_ok.settled_amount_cents, 48500)
        self.assertEqual(drop_ok.buyer_savings_cents, 1500)

        # 5. Flash-sale rebound ($79.00 -> $81.00) without positive slippage -> 422 blocked (W02)
        drift_422 = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=7900,
            live_price_cents=8100,
            max_amount_cents=7900,
            allow_bounded_slippage=False,
        )
        self.assertFalse(drift_422.allowed)
        self.assertEqual(drift_422.http_status, 422)
        self.assertEqual(drift_422.settled_amount_cents, 0)

        # 6. Stale crawl snapshot (liveCrawlSucceeded=False) -> 409 blocked (W03)
        stale_409 = evaluate_dynamic_pricing_quote_lock_and_drift_policy(
            approved_quote_cents=7900,
            live_price_cents=7900,
            max_amount_cents=7900,
            live_crawl_succeeded=False,
        )
        self.assertFalse(stale_409.allowed)
        self.assertEqual(stale_409.http_status, 409)
        self.assertEqual(stale_409.pricing_lane, "BLOCKED_STALE_CRAWL_SNAPSHOT")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["dynamic_pricing_quote_lock_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("dynamic-pricing-quote-lock-sandbox", demo_zh)

    def test_mcp_oauth_audience_stepup_vs_confused_deputy_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_mcp_oauth_audience_and_stepup_policy

        # 1. Valid OAuth 2.1 step-up scope union with exact RFC 8707 aud & RFC 9207 iss
        stepup_ok = evaluate_mcp_oauth_audience_and_stepup_policy()
        self.assertTrue(stepup_ok.allowed)
        self.assertEqual(stepup_ok.http_status, 200)
        self.assertEqual(stepup_ok.auth_lane, "STEPUP_SCOPE_UNION_AUTHORIZED")
        self.assertEqual(stepup_ok.merged_scopes, ("mcp:tools", "commerce:read", "commerce:checkout"))

        # 2. Confused Deputy cross-MCP token replay -> 401 blocked
        deputy_401 = evaluate_mcp_oauth_audience_and_stepup_policy(
            token_aud="https://compare.plugin.example/mcp",
            target_mcp_uri="https://checkout.merchant.example/mcp",
        )
        self.assertFalse(deputy_401.allowed)
        self.assertEqual(deputy_401.http_status, 401)
        self.assertEqual(deputy_401.auth_lane, "BLOCKED_CONFUSED_DEPUTY_AUD_MISMATCH")

        # 3. RFC 9207 case-folded iss -> 400 blocked + untrusted error UI suppressed
        iss_400 = evaluate_mcp_oauth_audience_and_stepup_policy(
            expected_issuer="https://auth.merchant.example",
            callback_iss="HTTPS://auth.merchant.example",
        )
        self.assertFalse(iss_400.allowed)
        self.assertEqual(iss_400.http_status, 400)
        self.assertTrue(iss_400.suppress_untrusted_error_display)

        # 4. Post-Nov 30, 2026 raw sk_live_ key -> 401 blocked
        nov30_401 = evaluate_mcp_oauth_audience_and_stepup_policy(
            credential_mode="raw_sk_live",
        )
        self.assertFalse(nov30_401.allowed)
        self.assertEqual(nov30_401.http_status, 401)

        # 5. Protected resource requesting offline_access -> 400 blocked
        hygiene_400 = evaluate_mcp_oauth_audience_and_stepup_policy(
            requests_offline_access=True,
        )
        self.assertFalse(hygiene_400.allowed)
        self.assertEqual(hygiene_400.http_status, 400)

        # 6. High-risk refund/treasury tool without human confirmation -> 403 blocked
        refund_403 = evaluate_mcp_oauth_audience_and_stepup_policy(
            credential_mode="agent_tagged_rk_live",
            is_high_risk_financial_tool=True,
            human_confirmed=False,
        )
        self.assertFalse(refund_403.allowed)
        self.assertEqual(refund_403.http_status, 403)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["mcp_oauth_audience_stepup_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("mcp-oauth-audience-stepup-sandbox", demo_zh)

    def test_ap2_circuit_breaker_recall_tripwire_vs_backoff_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_ap2_circuit_breaker_and_recall_policy

        # 1. Normal guarded settlement in CLOSED state
        closed_ok = evaluate_ap2_circuit_breaker_and_recall_policy()
        self.assertTrue(closed_ok.allowed)
        self.assertEqual(closed_ok.http_status, 200)
        self.assertEqual(closed_ok.circuit_state, "CLOSED")

        # 2. Transient 503 recovered via bounded backoff with identical Idempotency-Key
        backoff_ok = evaluate_ap2_circuit_breaker_and_recall_policy(
            downstream_transient_status=503,
            same_idempotency_key=True,
            retry_attempt=1,
        )
        self.assertTrue(backoff_ok.allowed)
        self.assertEqual(backoff_ok.breaker_lane, "RECOVERED_VIA_BOUNDED_BACKOFF")

        # 3. Hourly velocity cap breach -> HTTP 429 OPEN + SPT revoked
        vel_429 = evaluate_ap2_circuit_breaker_and_recall_policy(
            orders_in_hour=6,
            max_orders_per_hour=5,
        )
        self.assertFalse(vel_429.allowed)
        self.assertEqual(vel_429.http_status, 429)
        self.assertEqual(vel_429.circuit_state, "OPEN")
        self.assertTrue(vel_429.spt_revoked)

        # 4. Consecutive policy failures >= 3 (reasoning loop) -> HTTP 423 OPEN + SPT revoked
        loop_423 = evaluate_ap2_circuit_breaker_and_recall_policy(
            consecutive_policy_failures=3,
            max_consecutive_failures=3,
        )
        self.assertFalse(loop_423.allowed)
        self.assertEqual(loop_423.http_status, 423)
        self.assertTrue(loop_423.spt_revoked)

        # 5. Web IQ pre-settlement regulatory recall tripwire (W09) -> HTTP 451 OPEN
        recall_451 = evaluate_ap2_circuit_breaker_and_recall_policy(
            recall_or_sanction_detected=True,
        )
        self.assertFalse(recall_451.allowed)
        self.assertEqual(recall_451.http_status, 451)
        self.assertEqual(recall_451.breaker_lane, "BLOCKED_REGULATORY_RECALL_TRIPWIRE")

        # 6. Timer-only auto-reset forbidden -> HTTP 423; FIDO2 human reset -> HTTP 200 CLOSED
        timer_423 = evaluate_ap2_circuit_breaker_and_recall_policy(
            breaker_currently_open=True,
            timer_only_auto_reset_attempted=True,
            hitl_fido2_reset_verified=False,
        )
        self.assertFalse(timer_423.allowed)
        self.assertEqual(timer_423.http_status, 423)

        fido2_200 = evaluate_ap2_circuit_breaker_and_recall_policy(
            breaker_currently_open=True,
            hitl_fido2_reset_verified=True,
        )
        self.assertTrue(fido2_200.allowed)
        self.assertEqual(fido2_200.circuit_state, "CLOSED")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["ap2_circuit_breaker_recall_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ap2-circuit-breaker-recall-sandbox", demo_zh)

    def test_idempotency_payload_hash_vs_retry_double_charge_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_idempotency_and_retry_deduplication_policy

        # 1. First execution commits charge and seals payload hash
        first_ok = evaluate_idempotency_and_retry_deduplication_policy()
        self.assertTrue(first_ok.allowed)
        self.assertEqual(first_ok.http_status, 200)
        self.assertEqual(first_ok.incremental_charge_cents, 24000)
        self.assertFalse(first_ok.idempotent_replayed)

        # 2. Post-timeout retry with identical payload -> 200 cached replay with $0 incremental charge
        replay_ok = evaluate_idempotency_and_retry_deduplication_policy(
            is_retry=True,
            stored_state="COMPLETED_200",
        )
        self.assertTrue(replay_ok.allowed)
        self.assertEqual(replay_ok.http_status, 200)
        self.assertEqual(replay_ok.incremental_charge_cents, 0)
        self.assertTrue(replay_ok.idempotent_replayed)

        # 3. Concurrent retry while first request is still IN_FLIGHT -> 409 conflict
        inflight_409 = evaluate_idempotency_and_retry_deduplication_policy(
            is_retry=True,
            stored_state="IN_FLIGHT",
        )
        self.assertFalse(inflight_409.allowed)
        self.assertEqual(inflight_409.http_status, 409)

        # 4. LLM parameter drift on retry -> 422 parameter mismatch
        drift_422 = evaluate_idempotency_and_retry_deduplication_policy(
            is_retry=True,
            stored_state="COMPLETED_200",
            incoming_payload_sha256="mutated_amount_26500_sha256",
        )
        self.assertFalse(drift_422.allowed)
        self.assertEqual(drift_422.http_status, 422)

        # 5. Unbound random per-retry UUID -> 400 blocked
        random_400 = evaluate_idempotency_and_retry_deduplication_policy(
            is_retry=True,
            intent_derived_key=False,
        )
        self.assertFalse(random_400.allowed)
        self.assertEqual(random_400.http_status, 400)

        # 6. Terminal card decline cached replay -> 402 replayed without hitting card rail
        decline_402 = evaluate_idempotency_and_retry_deduplication_policy(
            is_retry=True,
            stored_state="TERMINAL_DECLINED_402",
        )
        self.assertFalse(decline_402.allowed)
        self.assertEqual(decline_402.http_status, 402)
        self.assertTrue(decline_402.idempotent_replayed)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["idempotency_deduplication_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("idempotency-deduplication-sandbox", demo_zh)

    def test_privacy_pii_vaultless_shipping_token_vs_context_leak_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_privacy_pii_shipping_token_and_erasure_policy

        # 1. Pre-checkout quote shares coarse postal prefix only with 0 bytes raw PII in LLM context
        quote_ok = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            phase="pre_checkout_quote",
        )
        self.assertTrue(quote_ok.allowed)
        self.assertEqual(quote_ok.http_status, 200)
        self.assertEqual(quote_ok.raw_pii_bytes_in_llm_context, 0)
        self.assertEqual(quote_ok.disclosed_scope, "US-CA-940")

        # 2. Committed winner merchant resolves ship_tok_... over mTLS
        resolve_ok = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            phase="committed_resolve",
        )
        self.assertTrue(resolve_ok.allowed)
        self.assertEqual(resolve_ok.privacy_lane, "VAULT_FULFILLMENT_TOKEN_RESOLVED")

        # 3. Prompt-injected raw PII in LLM arg or URL -> 403 blocked in 15ms
        dlp_403 = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            raw_pii_in_llm_or_url=True,
        )
        self.assertFalse(dlp_403.allowed)
        self.assertEqual(dlp_403.http_status, 403)
        self.assertEqual(dlp_403.privacy_lane, "BLOCKED_PII_CONTEXT_OR_URL_EXFILTRATION")

        # 4. Premature uncommitted or cross-merchant resolve -> 403 blocked
        premature_403 = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            phase="committed_resolve",
            checkout_committed=False,
        )
        self.assertFalse(premature_403.allowed)
        self.assertEqual(premature_403.http_status, 403)

        cross_403 = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            phase="committed_resolve",
            token_merchant_id="merch_winner",
            caller_merchant_id="merch_loser",
        )
        self.assertFalse(cross_403.allowed)
        self.assertEqual(cross_403.http_status, 403)

        # 5. GDPR Art. 17 crypto-shredded per-subject DEK -> 410 Gone
        gdpr_410 = evaluate_privacy_pii_shipping_token_and_erasure_policy(
            gdpr_erasure_revoked_dek=True,
        )
        self.assertFalse(gdpr_410.allowed)
        self.assertEqual(gdpr_410.http_status, 410)
        self.assertEqual(gdpr_410.privacy_lane, "BLOCKED_GDPR_CRYPTO_SHREDDED_KEY")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["privacy_pii_shipping_token_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("privacy-pii-shipping-token-sandbox", demo_zh)

    def test_inventory_reservation_ttl_hold_vs_oversell_compensation_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_inventory_reservation_and_oversell_policy

        # 1. Quote phase (calculate_order) never locks physical stock
        quote_ok = evaluate_inventory_reservation_and_oversell_policy(
            phase="calculate_order",
        )
        self.assertTrue(quote_ok.allowed)
        self.assertFalse(quote_ok.lock_acquired)
        self.assertEqual(quote_ok.inventory_lane, "NON_BINDING_QUOTE_SNAPSHOT")

        # 2. Valid MandateVC + quota <= 2 + active lease & fencing token -> 200 atomic commit
        commit_ok = evaluate_inventory_reservation_and_oversell_policy(
            phase="finalize_checkout",
        )
        self.assertTrue(commit_ok.allowed)
        self.assertTrue(commit_ok.lock_acquired)
        self.assertEqual(commit_ok.captured_amount_cents, 99900)
        self.assertEqual(commit_ok.refund_fee_loss_cents, 0)

        # 3. Cart-hoarding bot exceeding per-buyer active hold quota (>2) -> 429 blocked
        hoard_429 = evaluate_inventory_reservation_and_oversell_policy(
            active_holds_for_buyer=3,
        )
        self.assertFalse(hoard_429.allowed)
        self.assertEqual(hoard_429.http_status, 429)
        self.assertEqual(hoard_429.inventory_lane, "BLOCKED_CART_HOARDING_QUOTA_EXCEEDED")

        # 4. Expired 180s lease or stale fencing token -> 409 pre-auth voided with $0 fee loss
        expired_409 = evaluate_inventory_reservation_and_oversell_policy(
            lease_expired=True,
            fencing_token=41,
            current_committed_token=42,
        )
        self.assertFalse(expired_409.allowed)
        self.assertEqual(expired_409.http_status, 409)
        self.assertEqual(expired_409.refund_fee_loss_cents, 0)
        self.assertEqual(expired_409.inventory_lane, "INVENTORY_LEASE_EXPIRED_PREAUTH_VOIDED")

        # 5. Depleted stock with 14-day backorder -> 409 Confirm
        backorder_409 = evaluate_inventory_reservation_and_oversell_policy(
            available_qty=0,
            backorder_lead_time_days=14,
        )
        self.assertFalse(backorder_409.allowed)
        self.assertEqual(backorder_409.http_status, 409)
        self.assertEqual(backorder_409.action_pill, "Confirm")

        # 6. Hard stockout -> 409 zero-charge abort
        stockout_409 = evaluate_inventory_reservation_and_oversell_policy(
            available_qty=0,
        )
        self.assertFalse(stockout_409.allowed)
        self.assertEqual(stockout_409.http_status, 409)
        self.assertEqual(stockout_409.inventory_lane, "STOCKOUT_ZERO_CHARGE_ABORT")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["inventory_reservation_oversell_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("inventory-reservation-oversell-sandbox", demo_zh)

    def test_multi_currency_fx_rate_lock_vs_dcc_spread_trap_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_multi_currency_fx_and_dcc_policy

        # 1. Clean JPY local currency + 300s FX quote lock within mandate -> 200
        commit_ok = evaluate_multi_currency_fx_and_dcc_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.dcc_savings_cents, 2592)

        # 2. Zero-decimal currency (JPY) multiplied by 100 -> 422 blocked in 14ms
        bug_100x = evaluate_multi_currency_fx_and_dcc_policy(
            presentment_currency="JPY",
            display_price_major=70000,
            submitted_amount_minor=7000000,
        )
        self.assertFalse(bug_100x.allowed)
        self.assertEqual(bug_100x.http_status, 422)
        self.assertEqual(bug_100x.fx_lane, "BLOCKED_ZERO_DECIMAL_100X_MULTIPLIER_BUG")

        # 3. Predatory DCC markup (650 bps > 150 bps) -> 403 blocked
        dcc_403 = evaluate_multi_currency_fx_and_dcc_policy(
            dcc_enabled=True,
            fx_markup_bps=650,
        )
        self.assertFalse(dcc_403.allowed)
        self.assertEqual(dcc_403.http_status, 403)
        self.assertEqual(dcc_403.fx_lane, "BLOCKED_PREDATORY_DCC_MARKUP_TRAP")

        # 4. Expired 300s FX quote or mandate exceeded -> 409 Confirm
        expired_409 = evaluate_multi_currency_fx_and_dcc_policy(
            fx_quote_expired=True,
        )
        self.assertFalse(expired_409.allowed)
        self.assertEqual(expired_409.http_status, 409)
        self.assertEqual(expired_409.action_pill, "Confirm")

        # 5. Pinned FX quote full refund vs unpinned refund slippage block
        refund_ok = evaluate_multi_currency_fx_and_dcc_policy(
            is_refund=True,
            pin_original_fx_quote=True,
        )
        self.assertTrue(refund_ok.allowed)
        self.assertEqual(refund_ok.fx_lane, "PINNED_FX_RATE_FULL_REFUND_RESTORED")

        refund_409 = evaluate_multi_currency_fx_and_dcc_policy(
            is_refund=True,
            pin_original_fx_quote=False,
        )
        self.assertFalse(refund_409.allowed)
        self.assertEqual(refund_409.http_status, 409)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["multi_currency_fx_quote_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("multi-currency-fx-quote-sandbox", demo_zh)

    def test_loyalty_coupon_atomic_redemption_vs_stacking_abuse_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_loyalty_coupon_and_hybrid_saga_policy

        # 1. Valid single promo + 10,000 pts + $80 fiat -> 200 committed
        commit_ok = evaluate_loyalty_coupon_and_hybrid_saga_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.net_points_burned, 10000)
        self.assertEqual(commit_ok.fiat_charged_cents, 8000)

        # 2. Brute-force coupon enumeration (>3 attempts) -> 429 blocked in 14ms
        brute_429 = evaluate_loyalty_coupon_and_hybrid_saga_policy(
            promo_attempts_in_session=4,
        )
        self.assertFalse(brute_429.allowed)
        self.assertEqual(brute_429.http_status, 429)
        self.assertEqual(brute_429.promo_lane, "BLOCKED_COUPON_BRUTE_FORCE_ENUMERATION")

        # 3. Mutually-exclusive coupon stacking or >40% margin breach -> 403 blocked
        stack_403 = evaluate_loyalty_coupon_and_hybrid_saga_policy(
            has_stacking_conflict=True,
            total_discount_bps=6000,
        )
        self.assertFalse(stack_403.allowed)
        self.assertEqual(stack_403.http_status, 403)
        self.assertEqual(stack_403.promo_lane, "BLOCKED_UNAUTHORIZED_COUPON_AUDIENCE_OR_STACKING")

        # 4. Fiat card decline auto-restores soft-held points (0 net points burned)
        decline_402 = evaluate_loyalty_coupon_and_hybrid_saga_policy(
            fiat_charge_succeeded=False,
        )
        self.assertFalse(decline_402.allowed)
        self.assertEqual(decline_402.http_status, 402)
        self.assertEqual(decline_402.net_points_burned, 0)
        self.assertEqual(decline_402.promo_lane, "FIAT_DECLINED_LOYALTY_POINTS_AUTO_RESTORED")

        # 5. Web IQ brand exclusion fine print -> 409 Confirm
        excl_409 = evaluate_loyalty_coupon_and_hybrid_saga_policy(
            brand_excluded_by_terms=True,
        )
        self.assertFalse(excl_409.allowed)
        self.assertEqual(excl_409.http_status, 409)
        self.assertEqual(excl_409.action_pill, "Confirm")

        # 6. Partial return pro-rata split refund -> restores 5,000 pts + $40.00
        ret_200 = evaluate_loyalty_coupon_and_hybrid_saga_policy(
            is_partial_return=True,
        )
        self.assertTrue(ret_200.allowed)
        self.assertEqual(ret_200.net_points_burned, -5000)
        self.assertEqual(ret_200.fiat_charged_cents, -4000)

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["loyalty_coupon_hybrid_saga_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("loyalty-coupon-hybrid-saga-sandbox", demo_zh)

    def test_age_verification_zkp_vc_vs_id_upload_compliance_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_regulated_zkp_eligibility_and_jurisdiction_policy

        # 1. Valid W3C ZKP VC predicate + order_nonce -> 200 committed with 0 PII bytes & adult signature locked
        commit_ok = evaluate_regulated_zkp_eligibility_and_jurisdiction_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.exposed_id_dob_bytes, 0)
        self.assertTrue(commit_ok.adult_signature_locked)

        # 2. Self-attested DOB / checkbox bypass attempt -> 403 blocked in 14ms
        self_403 = evaluate_regulated_zkp_eligibility_and_jurisdiction_policy(
            self_attested_only=True,
        )
        self.assertFalse(self_403.allowed)
        self.assertEqual(self_403.http_status, 403)
        self.assertEqual(self_403.eligibility_lane, "BLOCKED_UNVERIFIED_SELF_ATTESTED_ELIGIBILITY")

        # 3. Raw government ID / prescription photo in agent payload -> 422 blocked in 15ms
        raw_422 = evaluate_regulated_zkp_eligibility_and_jurisdiction_policy(
            has_raw_id_or_rx_in_payload=True,
        )
        self.assertFalse(raw_422.allowed)
        self.assertEqual(raw_422.http_status, 422)
        self.assertEqual(raw_422.exposed_id_dob_bytes, 0)

        # 4. Replayed or expired order_nonce proof -> 401 blocked in 16ms
        replay_401 = evaluate_regulated_zkp_eligibility_and_jurisdiction_policy(
            nonce_matched=False,
        )
        self.assertFalse(replay_401.allowed)
        self.assertEqual(replay_401.http_status, 401)
        self.assertEqual(replay_401.eligibility_lane, "ZKP_NONCE_REPLAY_OR_EXPIRED_BLOCKED")

        # 5. Web IQ prohibited shipping jurisdiction (Dry County / restricted state) -> 451 blocked in 315ms
        juris_451 = evaluate_regulated_zkp_eligibility_and_jurisdiction_policy(
            jurisdiction_prohibited_by_webiq=True,
        )
        self.assertFalse(juris_451.allowed)
        self.assertEqual(juris_451.http_status, 451)
        self.assertEqual(juris_451.eligibility_lane, "JURISDICTION_SHIPPING_RESTRICTION_BLOCKED")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["regulated_zkp_eligibility_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("regulated-zkp-eligibility-sandbox", demo_zh)

    def test_high_ticket_escrow_delivery_attestation_vs_instant_settlement_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_high_ticket_escrow_and_attestation_policy

        # 1. Valid dual-signed authentication + POD + buyer acceptance -> 200 released & warranty minted
        release_ok = evaluate_high_ticket_escrow_and_attestation_policy()
        self.assertTrue(release_ok.allowed)
        self.assertEqual(release_ok.http_status, 200)
        self.assertEqual(release_ok.seller_payout_cents, 450000)
        self.assertTrue(release_ok.warranty_vc_minted)

        # 2. Unescrowed high-ticket instant payout attempt -> 403 blocked in 15ms
        instant_403 = evaluate_high_ticket_escrow_and_attestation_policy(
            escrow_enabled=False,
        )
        self.assertFalse(instant_403.allowed)
        self.assertEqual(instant_403.http_status, 403)
        self.assertEqual(instant_403.escrow_lane, "BLOCKED_UNESCROWED_HIGH_TICKET_INSTANT_PAYOUT")

        # 3. Neutral authentication lab detects counterfeit / SN mismatch -> 422 full buyer refund ($4,500)
        fake_422 = evaluate_high_ticket_escrow_and_attestation_policy(
            authentication_passed=False,
        )
        self.assertFalse(fake_422.allowed)
        self.assertEqual(fake_422.http_status, 422)
        self.assertEqual(fake_422.buyer_refund_cents, 450000)
        self.assertEqual(fake_422.seller_payout_cents, 0)

        # 4. Premature seller withdrawal during 72h buyer inspection window -> 409 blocked in 16ms
        premature_409 = evaluate_high_ticket_escrow_and_attestation_policy(
            inspection_hours_elapsed=12,
            buyer_explicit_accept=False,
        )
        self.assertFalse(premature_409.allowed)
        self.assertEqual(premature_409.http_status, 409)
        self.assertEqual(premature_409.escrow_lane, "PREMATURE_ESCROW_RELEASE_BLOCKED")

        # 5. Web IQ detects hidden As-Is / 7-day warranty below 180-day mandate floor -> 409 Confirm
        warranty_409 = evaluate_high_ticket_escrow_and_attestation_policy(
            warranty_days_grounded_by_webiq=7,
        )
        self.assertFalse(warranty_409.allowed)
        self.assertEqual(warranty_409.http_status, 409)
        self.assertEqual(warranty_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["high_ticket_escrow_attestation_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("high-ticket-escrow-attestation-sandbox", demo_zh)

    def test_indirect_prompt_injection_dom_poisoning_vs_signed_acp_feed_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_indirect_prompt_injection_and_acp_feed_policy

        # 1. Clean sanitized + privilege-separated + payee-pinned checkout -> 200 committed
        commit_ok = evaluate_indirect_prompt_injection_and_acp_feed_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.unauthorized_drain_cents, 0)
        self.assertEqual(commit_ok.total_landed_cost_cents, 29800)

        # 2. Hidden CSS / review indirect prompt injection -> 422 blocked in 15ms
        dom_422 = evaluate_indirect_prompt_injection_and_acp_feed_policy(
            has_hidden_dom_or_review_injection=True,
        )
        self.assertFalse(dom_422.allowed)
        self.assertEqual(dom_422.http_status, 422)
        self.assertEqual(dom_422.security_lane, "BLOCKED_INDIRECT_PROMPT_INJECTION_IN_DOM")

        # 3. Hijacked payee DID or SKU category drift to gift card -> 403 blocked in 13ms
        hijack_403 = evaluate_indirect_prompt_injection_and_acp_feed_policy(
            payee_matches_pinned_allowlist=False,
        )
        self.assertFalse(hijack_403.allowed)
        self.assertEqual(hijack_403.http_status, 403)
        self.assertEqual(hijack_403.security_lane, "BLOCKED_HIJACKED_PAYEE_OR_SKU_DRIFT")

        # 4. Unsigned or tampered ACP structured product feed -> 401 blocked in 16ms
        sig_401 = evaluate_indirect_prompt_injection_and_acp_feed_policy(
            acp_feed_signature_valid=False,
        )
        self.assertFalse(sig_401.allowed)
        self.assertEqual(sig_401.http_status, 401)

        # 5. "$1.00 item + $499.00 shipping fee" bait-and-switch -> 409 Confirm in 310ms
        fee_409 = evaluate_indirect_prompt_injection_and_acp_feed_policy(
            item_price_cents=100,
            shipping_handling_cents=49900,
        )
        self.assertFalse(fee_409.allowed)
        self.assertEqual(fee_409.http_status, 409)
        self.assertEqual(fee_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["indirect_prompt_injection_feed_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("indirect-prompt-injection-feed-sandbox", demo_zh)

    def test_multi_agent_shared_budget_allocation_vs_race_spend_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_multi_agent_shared_budget_allocation_policy

        # 1. Clean hierarchical sub-slice + CAS surplus rebalance commit -> 200 ($1,910 committed, $90 surplus)
        commit_ok = evaluate_multi_agent_shared_budget_allocation_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.committed_total_cents, 191000)
        self.assertEqual(commit_ok.retained_surplus_cents, 9000)

        # 2. Unpartitioned shared root wallet concurrent race hazard -> 403 blocked in 12ms
        race_403 = evaluate_multi_agent_shared_budget_allocation_policy(
            shared_root_wallet_without_slices=True,
        )
        self.assertFalse(race_403.allowed)
        self.assertEqual(race_403.http_status, 403)
        self.assertEqual(race_403.coalition_lane, "SHARED_ROOT_WALLET_CONCURRENT_RACE_BLOCKED")

        # 3. Stale CAS version double-claim on surplus pool -> 409 blocked in 15ms
        cas_409 = evaluate_multi_agent_shared_budget_allocation_policy(
            cas_version_matched=False,
        )
        self.assertFalse(cas_409.allowed)
        self.assertEqual(cas_409.http_status, 409)
        self.assertEqual(cas_409.coalition_lane, "CAS_BUDGET_VERSION_CONFLICT")

        # 4. Circular wait or >4,000ms negotiation deadlock timebox -> 408 blocked in 17ms
        deadlock_408 = evaluate_multi_agent_shared_budget_allocation_policy(
            negotiation_elapsed_ms=5200,
        )
        self.assertFalse(deadlock_408.allowed)
        self.assertEqual(deadlock_408.http_status, 408)
        self.assertEqual(deadlock_408.coalition_lane, "A2A_NEGOTIATION_DEADLOCK_TIMEOUT")

        # 5. Web IQ cross-category bundle arbitrage ($1,620 bundle vs $1,910 split) -> 409 Confirm in 315ms
        bundle_409 = evaluate_multi_agent_shared_budget_allocation_policy(
            webiq_official_bundle_cents=162000,
        )
        self.assertFalse(bundle_409.allowed)
        self.assertEqual(bundle_409.http_status, 409)
        self.assertEqual(bundle_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["multi_agent_shared_budget_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("multi-agent-shared-budget-sandbox", demo_zh)

    def test_return_logistics_reverse_escrow_vs_refund_before_scan_abuse_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_return_logistics_reverse_escrow_policy

        # 1. Clean carrier weight + WMS serial match -> 200 full refund released ($1,200)
        commit_ok = evaluate_return_logistics_reverse_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.refunded_buyer_cents, 120000)

        # 2. Unscanned return label instant refund attempt -> 403 blocked in 13ms
        label_403 = evaluate_return_logistics_reverse_escrow_policy(
            carrier_dropoff_scanned=False,
        )
        self.assertFalse(label_403.allowed)
        self.assertEqual(label_403.http_status, 403)
        self.assertEqual(label_403.rma_lane, "UNSCANNED_RETURN_LABEL_REFUND_BLOCKED")

        # 3. 45g empty envelope mailed for 1,850g laptop -> 422 blocked in 15ms
        weight_422 = evaluate_return_logistics_reverse_escrow_policy(
            inducted_weight_grams=45,
        )
        self.assertFalse(weight_422.allowed)
        self.assertEqual(weight_422.http_status, 422)
        self.assertEqual(weight_422.rma_lane, "RETURN_PACKAGE_WEIGHT_MISMATCH_BLOCKED")

        # 4. Weight-matched broken unit switcheroo (serial mismatch) -> 422 blocked in 19ms
        sn_422 = evaluate_return_logistics_reverse_escrow_policy(
            returned_sn_sha256="sn_broken_999",
        )
        self.assertFalse(sn_422.allowed)
        self.assertEqual(sn_422.http_status, 422)
        self.assertEqual(sn_422.rma_lane, "RETURN_SERIAL_SWITCHEROO_DETECTED")

        # 5. Web IQ hidden 15% ($180) opened-box restocking fee -> 409 Confirm in 315ms
        fee_409 = evaluate_return_logistics_reverse_escrow_policy(
            webiq_restocking_fee_bps=1500,
        )
        self.assertFalse(fee_409.allowed)
        self.assertEqual(fee_409.http_status, 409)
        self.assertEqual(fee_409.restocking_deduction_cents, 18000)
        self.assertEqual(fee_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["return_logistics_reverse_escrow_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("return-logistics-reverse-escrow-sandbox", demo_zh)

    def test_b2b_net30_po_three_way_match_vs_upfront_card_capture_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_b2b_net30_three_way_match_policy

        # 1. Clean PO == GRN == Invoice ($45,000) -> 200 Net-30 ACH scheduled
        commit_ok = evaluate_b2b_net30_three_way_match_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.scheduled_payout_cents, 4500000)

        # 2. Missing signed warehouse Goods Receipt Note (Phantom Invoice) -> 403 blocked in 14ms
        grn_403 = evaluate_b2b_net30_three_way_match_policy(
            grn_verified=False,
        )
        self.assertFalse(grn_403.allowed)
        self.assertEqual(grn_403.http_status, 403)
        self.assertEqual(grn_403.ap_lane, "MISSING_GOODS_RECEIPT_NOTE_PHANTOM_INVOICE")

        # 3. Invoice padded to $48,600 vs $45,000 PO/GRN (+8.0% > 1.0%) -> 422 blocked in 17ms
        pad_422 = evaluate_b2b_net30_three_way_match_policy(
            invoice_amount_cents=4860000,
        )
        self.assertFalse(pad_422.allowed)
        self.assertEqual(pad_422.http_status, 422)
        self.assertEqual(pad_422.ap_lane, "THREE_WAY_MATCH_PRICE_OR_QTY_DISCREPANCY")

        # 4. Web IQ supplier hit sanctions list or KYB revoked -> 451 blocked in 310ms
        kyb_451 = evaluate_b2b_net30_three_way_match_policy(
            webiq_supplier_sanctioned_or_revoked=True,
        )
        self.assertFalse(kyb_451.allowed)
        self.assertEqual(kyb_451.http_status, 451)

        # 5. Web IQ 2/10 Net 30 early-payment discount (2% = $900 savings) -> 409 Confirm in 315ms
        disc_409 = evaluate_b2b_net30_three_way_match_policy(
            early_pay_discount_bps=200,
        )
        self.assertFalse(disc_409.allowed)
        self.assertEqual(disc_409.http_status, 409)
        self.assertEqual(disc_409.early_pay_savings_cents, 90000)
        self.assertEqual(disc_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_net30_three_way_match_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-net30-three-way-match-sandbox", demo_zh)

    def test_esg_carbon_footprint_verified_shipping_vs_greenwashing_surcharge_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_esg_carbon_verified_shipping_policy

        # 1. Compliant low-carbon multimodal shipment (68kg <= 150kg cap) -> 200 committed
        commit_ok = evaluate_esg_carbon_verified_shipping_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.committed_co2e_grams, 68000)

        # 2. Express Air Freight (420kg > 150kg cap) -> 403 blocked in 13ms
        air_403 = evaluate_esg_carbon_verified_shipping_policy(
            shipment_co2e_grams=420000,
        )
        self.assertFalse(air_403.allowed)
        self.assertEqual(air_403.http_status, 403)
        self.assertEqual(air_403.esg_lane, "SCOPE3_CARBON_CAP_EXCEEDED")

        # 3. Unverified +$145 carbon-neutral checkbox surcharge -> 422 blocked in 16ms
        greenwash_422 = evaluate_esg_carbon_verified_shipping_policy(
            offset_surcharge_cents=14500,
            registry_verified=False,
        )
        self.assertFalse(greenwash_422.allowed)
        self.assertEqual(greenwash_422.http_status, 422)
        self.assertEqual(
            greenwash_422.esg_lane, "UNVERIFIED_GREENWASHING_OFFSET_SURCHARGE"
        )

        # 4. Web IQ detects revoked or double-counted carbon credit batch -> 451 blocked in 310ms
        revoked_451 = evaluate_esg_carbon_verified_shipping_policy(
            webiq_registry_credit_revoked_or_double_counted=True,
        )
        self.assertFalse(revoked_451.allowed)
        self.assertEqual(revoked_451.http_status, 451)

        # 5. Web IQ consolidated rail/ocean arbitrage (-83.8% CO2e & saves $380) -> 409 Confirm in 315ms
        rail_409 = evaluate_esg_carbon_verified_shipping_policy(
            low_carbon_route_savings_cents=38000,
        )
        self.assertFalse(rail_409.allowed)
        self.assertEqual(rail_409.http_status, 409)
        self.assertEqual(rail_409.freight_savings_cents, 38000)
        self.assertEqual(rail_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["esg_carbon_verified_shipping_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("esg-carbon-verified-shipping-sandbox", demo_zh)

    def test_price_drop_watchlist_mandate_vs_cart_recovery_spam_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_price_drop_watchlist_mandate_policy

        # 1. Genuine price drop ($820 <= $850 limit) with signed mandate -> 200 executed
        commit_ok = evaluate_price_drop_watchlist_mandate_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.executed_price_cents, 82000)

        # 2. Unsolicited cart-abandonment recovery charge without signed mandate -> 403 blocked in 12ms
        unsol_403 = evaluate_price_drop_watchlist_mandate_policy(
            mandate_signed=False,
        )
        self.assertFalse(unsol_403.allowed)
        self.assertEqual(unsol_403.http_status, 403)
        self.assertEqual(
            unsol_403.watchlist_lane, "UNSOLICITED_CART_RECOVERY_CHARGE_BLOCKED"
        )

        # 3. Fake 25%-off sale still above $850 limit ($899) -> 422 blocked in 15ms
        ceil_422 = evaluate_price_drop_watchlist_mandate_policy(
            checkout_price_cents=89900,
        )
        self.assertFalse(ceil_422.allowed)
        self.assertEqual(ceil_422.http_status, 422)
        self.assertEqual(ceil_422.watchlist_lane, "LIMIT_ORDER_TARGET_PRICE_NOT_MET")

        # 4. Web IQ detects fake-MSRP anchor inflation dark pattern -> 451 blocked in 310ms
        fake_451 = evaluate_price_drop_watchlist_mandate_policy(
            webiq_fake_msrp_anchor_inflated=True,
        )
        self.assertFalse(fake_451.allowed)
        self.assertEqual(fake_451.http_status, 451)

        # 5. Web IQ discovers stackable $75 manufacturer rebate ($745 net) -> 409 Confirm in 315ms
        rebate_409 = evaluate_price_drop_watchlist_mandate_policy(
            extra_rebate_savings_cents=7500,
        )
        self.assertFalse(rebate_409.allowed)
        self.assertEqual(rebate_409.http_status, 409)
        self.assertEqual(rebate_409.executed_price_cents, 74500)
        self.assertEqual(rebate_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["price_drop_watchlist_mandate_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("price-drop-watchlist-mandate-sandbox", demo_zh)

    def test_warranty_claim_telemetry_attestation_vs_serial_fraud_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_warranty_claim_telemetry_attestation_policy,
        )

        # 1. Verified original order serial + signed fault telemetry -> 200 replacement dispatched
        commit_ok = evaluate_warranty_claim_telemetry_attestation_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.replacement_value_cents, 65000)

        # 2. Scraped marketplace serial mismatch -> 403 blocked in 13ms
        serial_403 = evaluate_warranty_claim_telemetry_attestation_policy(
            claimed_serial="sn_ebay_scraped_777",
        )
        self.assertFalse(serial_403.allowed)
        self.assertEqual(serial_403.http_status, 403)
        self.assertEqual(
            serial_403.warranty_lane, "WARRANTY_SERIAL_OWNERSHIP_MISMATCH"
        )

        # 3. Missing signed device fault telemetry (No-Fault-Found abuse) -> 422 blocked in 16ms
        telem_422 = evaluate_warranty_claim_telemetry_attestation_policy(
            telemetry_fault_verified=False,
        )
        self.assertFalse(telem_422.allowed)
        self.assertEqual(telem_422.http_status, 422)
        self.assertEqual(
            telem_422.warranty_lane, "MISSING_DEVICE_FAULT_TELEMETRY_ATTESTATION"
        )

        # 4. Out-of-warranty (820d > 730d) & no OEM recall bulletin -> 451 blocked in 310ms
        exp_451 = evaluate_warranty_claim_telemetry_attestation_policy(
            days_since_purchase=820,
            webiq_oem_extended_program_active=False,
        )
        self.assertFalse(exp_451.allowed)
        self.assertEqual(exp_451.http_status, 451)

        # 5. Web IQ same-day modular repair saves $540 ($110 vs $650) -> 409 Confirm in 315ms
        mod_409 = evaluate_warranty_claim_telemetry_attestation_policy(
            modular_repair_savings_cents=54000,
        )
        self.assertFalse(mod_409.allowed)
        self.assertEqual(mod_409.http_status, 409)
        self.assertEqual(mod_409.modular_repair_savings_cents, 54000)
        self.assertEqual(mod_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["warranty_claim_telemetry_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("warranty-claim-telemetry-sandbox", demo_zh)

    def test_b2b_moq_syndicate_escrow_vs_stranded_deposit_shortfall_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_moq_syndicate_escrow_policy,
        )

        # 1. Verified MOQ reached (1,000 >= 1,000) within 38h <= 72h -> 200 escrow released
        commit_ok = evaluate_b2b_moq_syndicate_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.buyer_settled_cents, 287500)

        # 2. Premature capture attempt while pledged is 650 < 1,000 MOQ -> 403 blocked in 12ms
        short_403 = evaluate_b2b_moq_syndicate_escrow_policy(
            current_pledged_units=650,
        )
        self.assertFalse(short_403.allowed)
        self.assertEqual(short_403.http_status, 403)
        self.assertEqual(
            short_403.syndicate_lane, "MOQ_THRESHOLD_NOT_MET_CAPTURE_BLOCKED"
        )

        # 3. 72h pooling window expired (76h > 72h) below MOQ -> 422 auto-refund in 15ms
        exp_422 = evaluate_b2b_moq_syndicate_escrow_policy(
            current_pledged_units=650,
            elapsed_hours=76,
        )
        self.assertFalse(exp_422.allowed)
        self.assertEqual(exp_422.http_status, 422)
        self.assertEqual(
            exp_422.syndicate_lane, "SYNDICATE_WINDOW_EXPIRED_AUTO_REFUND"
        )

        # 4. Hidden broker markup or unverified factory -> 451 blocked in 310ms
        unver_451 = evaluate_b2b_moq_syndicate_escrow_policy(
            webiq_factory_verified=False,
        )
        self.assertFalse(unver_451.allowed)
        self.assertEqual(unver_451.http_status, 451)

        # 5. Web IQ 1,000-unit wholesale tier saves $625.00 on 250 units -> 409 Confirm in 315ms
        tier_409 = evaluate_b2b_moq_syndicate_escrow_policy(
            next_tier_savings_cents=62500,
        )
        self.assertFalse(tier_409.allowed)
        self.assertEqual(tier_409.http_status, 409)
        self.assertEqual(tier_409.tier_savings_cents, 62500)
        self.assertEqual(tier_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_moq_syndicate_escrow_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-moq-syndicate-escrow-sandbox", demo_zh)

    def test_b2b_sealed_bid_reverse_auction_vs_price_signaling_collusion_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_sealed_bid_reverse_auction_policy,
        )

        # 1. Verified commit-reveal hash + within $45,000 reserve + independent UBO -> 200 awarded ($38,200)
        commit_ok = evaluate_b2b_sealed_bid_reverse_auction_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.awarded_bid_cents, 3820000)
        self.assertEqual(commit_ok.arbitrage_savings_cents, 680000)

        # 2. Post-commit hash tampering -> 403 blocked in 12ms
        hash_403 = evaluate_b2b_sealed_bid_reverse_auction_policy(
            revealed_bid_hash="hash_tampered_44500",
        )
        self.assertFalse(hash_403.allowed)
        self.assertEqual(hash_403.http_status, 403)
        self.assertEqual(
            hash_403.auction_lane, "SEALED_BID_COMMIT_HASH_MISMATCH"
        )

        # 3. Lowest bid ($48,500) exceeds buyer reserve ceiling ($45,000) -> 422 blocked in 15ms
        res_422 = evaluate_b2b_sealed_bid_reverse_auction_policy(
            lowest_revealed_bid_cents=4850000,
        )
        self.assertFalse(res_422.allowed)
        self.assertEqual(res_422.http_status, 422)
        self.assertEqual(
            res_422.auction_lane, "BID_EXCEEDS_RESERVE_PRICE_CEILING"
        )

        # 4. Shared UBO Sybil shell-company bid rigging -> 451 blocked in 310ms
        ubo_451 = evaluate_b2b_sealed_bid_reverse_auction_policy(
            webiq_ubo_collusion_detected=True,
        )
        self.assertFalse(ubo_451.allowed)
        self.assertEqual(ubo_451.http_status, 451)

        # 5. Web IQ ready-stock dispatch saves extra $1,400 ($36,800 net) -> 409 Confirm in 315ms
        arb_409 = evaluate_b2b_sealed_bid_reverse_auction_policy(
            ready_stock_discount_cents=140000,
        )
        self.assertFalse(arb_409.allowed)
        self.assertEqual(arb_409.http_status, 409)
        self.assertEqual(arb_409.awarded_bid_cents, 3680000)
        self.assertEqual(arb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_sealed_bid_auction_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-sealed-bid-auction-sandbox", demo_zh)

    def test_cross_border_customs_hs_tariff_mandate_vs_seizure_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cross_border_customs_ddp_tariff_policy,
        )

        # 1. Verified 1:1 invoice/declaration ($6,000) + valid HS + DDP $6,420 <= $6,900 -> 200 settled
        commit_ok = evaluate_cross_border_customs_ddp_tariff_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_landed_cents, 642000)

        # 2. Undervalued customs declaration ($750 != $6,000 invoice) -> 403 blocked in 12ms
        under_403 = evaluate_cross_border_customs_ddp_tariff_policy(
            declared_customs_value_cents=75000,
        )
        self.assertFalse(under_403.allowed)
        self.assertEqual(under_403.http_status, 403)
        self.assertEqual(
            under_403.customs_lane, "CUSTOMS_UNDERVALUATION_FRAUD_BLOCKED"
        )

        # 3. Missing DDP pre-clearance bond (unbonded DDU) -> 422 blocked in 15ms
        ddu_422 = evaluate_cross_border_customs_ddp_tariff_policy(
            ddp_preclearance_bound=False,
        )
        self.assertFalse(ddu_422.allowed)
        self.assertEqual(ddu_422.http_status, 422)
        self.assertEqual(
            ddu_422.customs_lane, "MISSING_DDP_PRECLEARANCE_OR_CAP_EXCEEDED"
        )

        # 4. Invalid 10-digit HS classification or anti-dumping hit -> 451 blocked in 310ms
        hs_451 = evaluate_cross_border_customs_ddp_tariff_policy(
            webiq_hs_classification_valid=False,
        )
        self.assertFalse(hs_451.allowed)
        self.assertEqual(hs_451.http_status, 451)

        # 5. Web IQ verified FTA Certificate of Origin saves $750 duty -> 409 Confirm in 315ms
        fta_409 = evaluate_cross_border_customs_ddp_tariff_policy(
            fta_tariff_savings_cents=75000,
        )
        self.assertFalse(fta_409.allowed)
        self.assertEqual(fta_409.http_status, 409)
        self.assertEqual(fta_409.fta_tariff_savings_cents, 75000)
        self.assertEqual(fta_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cross_border_customs_ddp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cross-border-customs-ddp-sandbox", demo_zh)

    def test_saas_seat_trueup_telemetry_mandate_vs_shelfware_auto_renewal_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_saas_seat_trueup_telemetry_policy,
        )

        # 1. Right-sized 320 active seats ($230,400) + 0% uplift + SOC2 clean -> 200 settled
        commit_ok = evaluate_saas_seat_trueup_telemetry_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_renewal_cents, 23040000)
        self.assertEqual(commit_ok.shelfware_savings_cents, 12960000)

        # 2. Unpruned 500-seat quote vs 320 active SSO seats (180 zombie seats) -> 403 blocked in 12ms
        zombie_403 = evaluate_saas_seat_trueup_telemetry_policy(
            billed_renewal_seats=500,
            active_sso_30d_seats=320,
        )
        self.assertFalse(zombie_403.allowed)
        self.assertEqual(zombie_403.http_status, 403)
        self.assertEqual(
            zombie_403.trueup_lane, "SHELFWARE_ZOMBIE_SEATS_RENEWAL_BLOCKED"
        )

        # 3. Predatory 12% uplift (1200 bps > 500 bps cap) -> 422 blocked in 15ms
        uplift_422 = evaluate_saas_seat_trueup_telemetry_policy(
            annual_uplift_bps=1200,
        )
        self.assertFalse(uplift_422.allowed)
        self.assertEqual(uplift_422.http_status, 422)
        self.assertEqual(
            uplift_422.trueup_lane, "EXCESSIVE_RENEWAL_PRICE_UPLIFT_BLOCKED"
        )

        # 4. Vendor SOC2 compliance hold or tier deprecation via Web IQ -> 451 blocked in 310ms
        trust_451 = evaluate_saas_seat_trueup_telemetry_policy(
            webiq_vendor_compliance_clean=False,
        )
        self.assertFalse(trust_451.allowed)
        self.assertEqual(trust_451.http_status, 451)

        # 5. Web IQ discovers public committed-use annual pool saving extra $18,400 -> 409 Confirm in 315ms
        promo_409 = evaluate_saas_seat_trueup_telemetry_policy(
            webiq_public_promo_savings_cents=1840000,
        )
        self.assertFalse(promo_409.allowed)
        self.assertEqual(promo_409.http_status, 409)
        self.assertEqual(promo_409.settled_renewal_cents, 21200000)
        self.assertEqual(promo_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["saas_seat_trueup_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("saas-seat-trueup-sandbox", demo_zh)

    def test_freight_detention_demurrage_sla_mandate_vs_carrier_surcharge_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_freight_detention_demurrage_sla_policy,
        )

        # 1. Clean 4-day dwell (<= 5-day free time) + $5,800 base freight -> 200 settled
        commit_ok = evaluate_freight_detention_demurrage_sla_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_freight_cents, 580000)

        # 2. False $4,200 D&D billed inside 5-day free time (dwell=4 <= 5) -> 403 blocked in 12ms
        free_403 = evaluate_freight_detention_demurrage_sla_policy(
            container_dwell_days=4,
            contracted_free_time_days=5,
            claimed_dd_surcharge_cents=420000,
        )
        self.assertFalse(free_403.allowed)
        self.assertEqual(free_403.http_status, 403)
        self.assertEqual(
            free_403.freight_lane, "FREE_TIME_WINDOW_SURCHARGE_FRAUD_BLOCKED"
        )

        # 3. Unapproved $1,800 Peak Season Surcharge (PSS) -> 422 blocked in 15ms
        pss_422 = evaluate_freight_detention_demurrage_sla_policy(
            unapproved_pss_surcharge_cents=180000,
        )
        self.assertFalse(pss_422.allowed)
        self.assertEqual(pss_422.http_status, 422)
        self.assertEqual(
            pss_422.freight_lane, "UNAPPROVED_ACCESSORIAL_RATE_CAP_EXCEEDED"
        )

        # 4. Web IQ confirms terminal gate lockout (FMC OSRA exemption) -> 451 blocked in 310ms
        fmc_451 = evaluate_freight_detention_demurrage_sla_policy(
            container_dwell_days=8,
            contracted_free_time_days=5,
            claimed_dd_surcharge_cents=240000,
            webiq_port_closure_carrier_fault=True,
        )
        self.assertFalse(fmc_451.allowed)
        self.assertEqual(fmc_451.http_status, 451)

        # 5. Web IQ confirms 6-day vessel delay unlocking $950 SLA rebate -> 409 Confirm in 315ms
        sla_409 = evaluate_freight_detention_demurrage_sla_policy(
            webiq_vessel_delay_rebate_cents=95000,
        )
        self.assertFalse(sla_409.allowed)
        self.assertEqual(sla_409.http_status, 409)
        self.assertEqual(sla_409.settled_freight_cents, 485000)
        self.assertEqual(sla_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["freight_dd_sla_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("freight-dd-sla-sandbox", demo_zh)

    def test_cold_chain_telemetry_escrow_vs_spoilage_dispute_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cold_chain_telemetry_escrow_policy,
        )

        # 1. Clean 5.4C within 2C-8C + valid hardware signature -> 200 settled ($24,000)
        commit_ok = evaluate_cold_chain_telemetry_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_escrow_cents, 2400000)

        # 2. Severe transit excursion (18.5C for 240m > 30m limit) -> 403 frozen in 12ms
        spoil_403 = evaluate_cold_chain_telemetry_escrow_policy(
            observed_max_temp_c=18.5,
            excursion_minutes=240,
        )
        self.assertFalse(spoil_403.allowed)
        self.assertEqual(spoil_403.http_status, 403)
        self.assertEqual(
            spoil_403.cold_chain_lane, "THERMAL_EXCURSION_SPOILAGE_ESCROW_FROZEN"
        )

        # 3. Missing hardware NFC/BLE datalogger signature -> 422 blocked in 15ms
        nosig_422 = evaluate_cold_chain_telemetry_escrow_policy(
            datalogger_signature_valid=False,
        )
        self.assertFalse(nosig_422.allowed)
        self.assertEqual(nosig_422.http_status, 422)
        self.assertEqual(
            nosig_422.cold_chain_lane, "MISSING_SIGNED_IOT_DATALOGGER_ATTESTATION"
        )

        # 4. Web IQ detects active FDA/EMA lot recall -> 451 blocked in 310ms
        fda_451 = evaluate_cold_chain_telemetry_escrow_policy(
            webiq_fda_lot_recall_active=True,
        )
        self.assertFalse(fda_451.allowed)
        self.assertEqual(fda_451.http_status, 451)

        # 5. Minor excursion (9.2C / 25m) within stability budget applies $3,600 concession -> 409 Confirm
        stab_409 = evaluate_cold_chain_telemetry_escrow_policy(
            observed_max_temp_c=9.2,
            excursion_minutes=25,
            stability_discount_cents=360000,
        )
        self.assertFalse(stab_409.allowed)
        self.assertEqual(stab_409.http_status, 409)
        self.assertEqual(stab_409.settled_escrow_cents, 2040000)
        self.assertEqual(stab_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cold_chain_telemetry_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cold-chain-telemetry-sandbox", demo_zh)

    def test_cloud_gpu_spot_preemption_sla_mandate_vs_ghost_node_billing_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cloud_gpu_spot_preemption_sla_policy,
        )

        # 1. Healthy DCGM Xid=0 + 52% MFU (>=35%) + checkpoint grace -> 200 settled ($12,800)
        commit_ok = evaluate_cloud_gpu_spot_preemption_sla_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_compute_cents, 1280000)

        # 2. Ghost-node Xid 79 fault / 0% MFU NCCL hang -> 403 blocked in 12ms
        ghost_403 = evaluate_cloud_gpu_spot_preemption_sla_policy(
            dcgm_xid_healthy=False,
            effective_mfu_bps=0,
        )
        self.assertFalse(ghost_403.allowed)
        self.assertEqual(ghost_403.http_status, 403)
        self.assertEqual(
            ghost_403.compute_lane, "GHOST_NODE_ECC_XID_FAULT_BILLING_BLOCKED"
        )

        # 3. Brutal Spot eviction without 120s checkpoint drain grace -> 422 waived in 15ms
        evict_422 = evaluate_cloud_gpu_spot_preemption_sla_policy(
            checkpoint_grace_honored=False,
        )
        self.assertFalse(evict_422.allowed)
        self.assertEqual(evict_422.http_status, 422)
        self.assertEqual(
            evict_422.compute_lane, "UNGRACEFUL_PREEMPTION_LOST_PROGRESS_WAIVED"
        )

        # 4. Web IQ detects provider InfiniBand fabric outage / CVE -> 451 blocked in 310ms
        fab_451 = evaluate_cloud_gpu_spot_preemption_sla_policy(
            webiq_provider_fabric_healthy=False,
        )
        self.assertFalse(fab_451.allowed)
        self.assertEqual(fab_451.http_status, 451)

        # 5. Web IQ discovers adjacent region off-peak block saving $2,400 ($10,400 net) -> 409 Confirm
        arb_409 = evaluate_cloud_gpu_spot_preemption_sla_policy(
            offpeak_arbitrage_savings_cents=240000,
        )
        self.assertFalse(arb_409.allowed)
        self.assertEqual(arb_409.http_status, 409)
        self.assertEqual(arb_409.settled_compute_cents, 1040000)
        self.assertEqual(arb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cloud_gpu_sla_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cloud-gpu-sla-sandbox", demo_zh)

    def test_retail_media_ad_spend_ivt_clawback_vs_click_farm_drain_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_retail_media_ad_spend_ivt_clawback_policy,
        )

        # 1. Clean 1.8% SIVT (180 <= 500 bps) + 30d return window cleared -> 200 settled ($18,000)
        commit_ok = evaluate_retail_media_ad_spend_ivt_clawback_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_media_cents, 1800000)

        # 2. Click-farm headless bot spike (42.0% = 4200 bps > 500 bps) -> 403 blocked in 12ms
        bot_403 = evaluate_retail_media_ad_spend_ivt_clawback_policy(
            sivt_bot_rate_bps=4200,
        )
        self.assertFalse(bot_403.allowed)
        self.assertEqual(bot_403.http_status, 403)
        self.assertEqual(
            bot_403.media_lane, "SIVT_BOT_TRAFFIC_THRESHOLD_BREACH_BLOCKED"
        )

        # 3. Premature affiliate payout before 30-day return window clears -> 422 blocked in 15ms
        ret_422 = evaluate_retail_media_ad_spend_ivt_clawback_policy(
            return_window_cleared=False,
        )
        self.assertFalse(ret_422.allowed)
        self.assertEqual(ret_422.http_status, 422)
        self.assertEqual(
            ret_422.media_lane, "AFFILIATE_CLAWBACK_RETURN_WINDOW_PENDING"
        )

        # 4. Web IQ detects brand-unsafe placement or missing FTC #ad tag -> 451 blocked in 310ms
        ftc_451 = evaluate_retail_media_ad_spend_ivt_clawback_policy(
            webiq_brand_safety_and_ftc_compliant=False,
        )
        self.assertFalse(ftc_451.allowed)
        self.assertEqual(ftc_451.http_status, 451)

        # 5. Web IQ discovers direct publisher PMP saving $3,100 ($14,900 net) -> 409 Confirm
        pmp_409 = evaluate_retail_media_ad_spend_ivt_clawback_policy(
            direct_pmp_savings_cents=310000,
        )
        self.assertFalse(pmp_409.allowed)
        self.assertEqual(pmp_409.http_status, 409)
        self.assertEqual(pmp_409.settled_media_cents, 1490000)
        self.assertEqual(pmp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["retail_media_ivt_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("retail-media-ivt-sandbox", demo_zh)

    def test_capex_milestone_retainage_lien_waiver_vs_double_payment_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_capex_milestone_retainage_lien_waiver_policy,
        )

        # 1. Signed tier-2 lien waivers + 10% ($15,000) retainage held -> 200 settled ($135,000 net)
        commit_ok = evaluate_capex_milestone_retainage_lien_waiver_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_progress_cents, 13500000)
        self.assertEqual(commit_ok.retainage_locked_cents, 1500000)

        # 2. Missing tier-2 subcontractor conditional lien waiver -> 403 blocked in 12ms
        lien_403 = evaluate_capex_milestone_retainage_lien_waiver_policy(
            subcontractor_lien_waivers_signed=False,
        )
        self.assertFalse(lien_403.allowed)
        self.assertEqual(lien_403.http_status, 403)
        self.assertEqual(
            lien_403.capex_lane, "MISSING_SUBCONTRACTOR_LIEN_WAIVER_BLOCKED"
        )

        # 3. Omitted 10% statutory retainage holdback (0 bps < 1000 bps) -> 422 blocked in 15ms
        ret_422 = evaluate_capex_milestone_retainage_lien_waiver_policy(
            retainage_withheld_bps=0,
        )
        self.assertFalse(ret_422.allowed)
        self.assertEqual(ret_422.http_status, 422)
        self.assertEqual(
            ret_422.capex_lane, "STATUTORY_RETAINAGE_HOLDBACK_VIOLATION"
        )

        # 4. Web IQ detects failed municipal inspection or Stop-Work Order -> 451 blocked in 310ms
        mun_451 = evaluate_capex_milestone_retainage_lien_waiver_policy(
            webiq_municipal_permit_inspection_passed=False,
        )
        self.assertFalse(mun_451.allowed)
        self.assertEqual(mun_451.http_status, 451)

        # 5. Web IQ discovers Owner-Direct Purchase (ODP) saving $9,500 ($125,500 net) -> 409 Confirm
        odp_409 = evaluate_capex_milestone_retainage_lien_waiver_policy(
            odp_material_savings_cents=950000,
        )
        self.assertFalse(odp_409.allowed)
        self.assertEqual(odp_409.http_status, 409)
        self.assertEqual(odp_409.settled_progress_cents, 12550000)
        self.assertEqual(odp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["capex_lien_waiver_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("capex-lien-waiver-sandbox", demo_zh)

    def test_healthcare_prior_auth_hsa_split_tender_vs_claim_denial_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_healthcare_prior_auth_hsa_split_tender_policy,
        )

        # 1. Approved EDI 278 PA ($2,750 payer) + $450 IIAS HSA copay -> 200 settled
        commit_ok = evaluate_healthcare_prior_auth_hsa_split_tender_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_patient_hsa_cents, 45000)
        self.assertEqual(commit_ok.payer_adjudicated_cents, 275000)

        # 2. Missing EDI 278 payer Prior Authorization ($3,200 surprise bill risk) -> 403 blocked in 12ms
        pa_403 = evaluate_healthcare_prior_auth_hsa_split_tender_policy(
            edi278_prior_auth_approved=False,
        )
        self.assertFalse(pa_403.allowed)
        self.assertEqual(pa_403.http_status, 403)
        self.assertEqual(
            pa_403.healthcare_lane, "MISSING_PAYER_PRIOR_AUTHORIZATION_BLOCKED"
        )

        # 3. $120 non-medical cosmetic SKU mixed into HSA/FSA tender -> 422 blocked in 15ms
        iias_422 = evaluate_healthcare_prior_auth_hsa_split_tender_policy(
            ineligible_hsa_sku_cents=12000,
        )
        self.assertFalse(iias_422.allowed)
        self.assertEqual(iias_422.http_status, 422)
        self.assertEqual(
            iias_422.healthcare_lane, "INELIGIBLE_SKU_ON_HSA_FSA_TENDER_BLOCKED"
        )

        # 4. Web IQ detects Out-of-Network pharmacy or unmet step therapy -> 451 blocked in 310ms
        net_451 = evaluate_healthcare_prior_auth_hsa_split_tender_policy(
            webiq_formulary_and_network_compliant=False,
        )
        self.assertFalse(net_451.allowed)
        self.assertEqual(net_451.http_status, 451)

        # 5. Web IQ discovers $400 manufacturer Copay Assistance Card ($50 net patient pay) -> 409 Confirm
        copay_409 = evaluate_healthcare_prior_auth_hsa_split_tender_policy(
            copay_assistance_savings_cents=40000,
        )
        self.assertFalse(copay_409.allowed)
        self.assertEqual(copay_409.http_status, 409)
        self.assertEqual(copay_409.settled_patient_hsa_cents, 5000)
        self.assertEqual(copay_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["healthcare_prior_auth_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("healthcare-prior-auth-sandbox", demo_zh)

    def test_ev_fleet_iso15118_charging_tariff_mandate_vs_demand_charge_spike_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ev_fleet_iso15118_charging_tariff_policy,
        )

        # 1. Peak-shaved 980 kW (<= 1,200 kW cap) + ISO 15118 cert -> 200 settled ($4,800)
        commit_ok = evaluate_ev_fleet_iso15118_charging_tariff_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_energy_cents, 480000)

        # 2. Uncoordinated 3,000 kW spike (> 1,200 kW cap) -> 403 blocked in 12ms
        peak_403 = evaluate_ev_fleet_iso15118_charging_tariff_policy(
            depot_peak_load_kw=3000,
        )
        self.assertFalse(peak_403.allowed)
        self.assertEqual(peak_403.http_status, 403)
        self.assertEqual(
            peak_403.energy_lane, "PEAK_DEMAND_CHARGE_SPIKE_CAP_EXCEEDED"
        )

        # 3. $850 overnight idle overstay surcharge or cloned RFID -> 422 blocked in 15ms
        idle_422 = evaluate_ev_fleet_iso15118_charging_tariff_policy(
            idle_overstay_surcharge_cents=85000,
        )
        self.assertFalse(idle_422.allowed)
        self.assertEqual(idle_422.http_status, 422)
        self.assertEqual(
            idle_422.energy_lane,
            "UNAUTHENTICATED_RFID_OR_IDLE_OVERSTAY_FEE_BLOCKED",
        )

        # 4. Web IQ detects ISO grid Flex Alert or expired DC meter calibration -> 451 blocked in 310ms
        grid_451 = evaluate_ev_fleet_iso15118_charging_tariff_policy(
            webiq_grid_and_meter_compliant=False,
        )
        self.assertFalse(grid_451.allowed)
        self.assertEqual(grid_451.http_status, 451)

        # 5. Web IQ discovers $1,150 Super-Off-Peak + V2G export savings ($3,650 net) -> 409 Confirm
        v2g_409 = evaluate_ev_fleet_iso15118_charging_tariff_policy(
            v2g_offpeak_savings_cents=115000,
        )
        self.assertFalse(v2g_409.allowed)
        self.assertEqual(v2g_409.http_status, 409)
        self.assertEqual(v2g_409.settled_energy_cents, 365000)
        self.assertEqual(v2g_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["ev_fleet_energy_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ev-fleet-energy-sandbox", demo_zh)

    def test_ai_dataset_sdk_spdx_sbom_royalty_mandate_vs_agpl_ip_contamination_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy,
        )

        # 1. Clean SPDX 3.0 permissive/commercial + signed C2PA chain -> 200 settled ($28,000)
        commit_ok = evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_royalty_cents, 2800000)

        # 2. Hidden AGPL-3.0 or CC-BY-NC contamination -> 403 blocked in 12ms
        agpl_403 = evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy(
            has_viral_agpl_or_nc_contamination=True,
        )
        self.assertFalse(agpl_403.allowed)
        self.assertEqual(agpl_403.http_status, 403)
        self.assertEqual(
            agpl_403.ip_lane, "VIRAL_COPYLEFT_OR_NONCOMMERCIAL_LICENSE_BLOCKED"
        )

        # 3. Missing signed SPDX 3.0 AI-BOM or C2PA provenance -> 422 blocked in 15ms
        nosbom_422 = evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy(
            signed_spdx_c2pa_provenance_valid=False,
        )
        self.assertFalse(nosbom_422.allowed)
        self.assertEqual(nosbom_422.http_status, 422)
        self.assertEqual(
            nosbom_422.ip_lane, "MISSING_SIGNED_SPDX_SBOM_OR_C2PA_PROVENANCE"
        )

        # 4. Web IQ detects upstream DMCA lawsuit or W3C TDM opt-out -> 451 blocked in 310ms
        dmca_451 = evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy(
            webiq_ip_litigation_and_tdm_clean=False,
        )
        self.assertFalse(dmca_451.allowed)
        self.assertEqual(dmca_451.http_status, 451)

        # 5. Web IQ deduplicates repackaged free Apache-2.0 shards saving $6,400 ($21,600 net) -> 409 Confirm
        dir_409 = evaluate_ai_dataset_sdk_spdx_sbom_royalty_policy(
            direct_rightsholder_savings_cents=640000,
        )
        self.assertFalse(dir_409.allowed)
        self.assertEqual(dir_409.http_status, 409)
        self.assertEqual(dir_409.settled_royalty_cents, 2160000)
        self.assertEqual(dir_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["dataset_sbom_royalty_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("dataset-sbom-royalty-sandbox", demo_zh)

    def test_agri_commodity_moisture_telemetry_parametric_hedge_vs_adulteration_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agri_commodity_moisture_parametric_hedge_policy,
        )

        # 1. Clean 13.8% dry-matter + <5 ppb aflatoxin + EUDR clean -> 200 settled ($64,000)
        commit_ok = evaluate_agri_commodity_moisture_parametric_hedge_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_commodity_cents, 6400000)

        # 2. Aflatoxin (>20 ppb) or mold spoilage breach -> 403 rejected in 12ms
        spoil_403 = evaluate_agri_commodity_moisture_parametric_hedge_policy(
            aflatoxin_or_spoilage_breach=True,
        )
        self.assertFalse(spoil_403.allowed)
        self.assertEqual(spoil_403.http_status, 403)
        self.assertEqual(
            spoil_403.agri_lane, "AFLATOXIN_OR_MOISTURE_SPOILAGE_REJECTED"
        )

        # 3. Wet grain billed at gross weight without shrinkage deduction -> 422 blocked in 15ms
        wet_422 = evaluate_agri_commodity_moisture_parametric_hedge_policy(
            moisture_shrinkage_deducted=False,
        )
        self.assertFalse(wet_422.allowed)
        self.assertEqual(wet_422.http_status, 422)
        self.assertEqual(
            wet_422.agri_lane, "UNADJUSTED_WATER_WEIGHT_BILLING_BLOCKED"
        )

        # 4. Web IQ detects EUDR deforestation or phytosanitary quarantine -> 451 blocked in 310ms
        eudr_451 = evaluate_agri_commodity_moisture_parametric_hedge_policy(
            webiq_eudr_and_phytosanitary_clean=False,
        )
        self.assertFalse(eudr_451.allowed)
        self.assertEqual(eudr_451.http_status, 451)

        # 5. Web IQ confirms NOAA drought index unlocking $5,200 parametric payout ($58,800 net) -> 409 Confirm
        noaa_409 = evaluate_agri_commodity_moisture_parametric_hedge_policy(
            parametric_weather_payout_cents=520000,
        )
        self.assertFalse(noaa_409.allowed)
        self.assertEqual(noaa_409.http_status, 409)
        self.assertEqual(noaa_409.settled_commodity_cents, 5880000)
        self.assertEqual(noaa_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agri_moisture_hedge_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agri-moisture-hedge-sandbox", demo_zh)

    def test_event_ticketing_rotating_barcode_mandate_vs_phantom_scalper_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_event_ticketing_rotating_barcode_policy,
        )

        # 1. Primary-registry seat escrowed + barcode reissued + all-in price -> 200 settled ($3,600)
        commit_ok = evaluate_event_ticketing_rotating_barcode_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ticket_cents, 360000)

        # 2. Speculative phantom listing or static PDF barcode -> 403 blocked in 12ms
        pdf_403 = evaluate_event_ticketing_rotating_barcode_policy(
            primary_registry_seat_escrowed=False,
        )
        self.assertFalse(pdf_403.allowed)
        self.assertEqual(pdf_403.http_status, 403)
        self.assertEqual(
            pdf_403.ticket_lane,
            "SPECULATIVE_PHANTOM_TICKET_OR_STATIC_PDF_BLOCKED",
        )

        # 3. 38% drip-pricing junk fee or scalper markup breach -> 422 blocked in 15ms
        junk_422 = evaluate_event_ticketing_rotating_barcode_policy(
            junk_fee_or_scalper_markup_breach=True,
        )
        self.assertFalse(junk_422.allowed)
        self.assertEqual(junk_422.http_status, 422)
        self.assertEqual(
            junk_422.ticket_lane, "SCALPER_PRICE_CAP_OR_FTC_JUNK_FEE_VIOLATION"
        )

        # 4. Web IQ detects undisclosed obstructed view or postponed event -> 451 blocked in 310ms
        view_451 = evaluate_event_ticketing_rotating_barcode_policy(
            webiq_venue_view_and_event_active=False,
        )
        self.assertFalse(view_451.allowed)
        self.assertEqual(view_451.http_status, 451)

        # 5. Web IQ discovers official primary box-office release saving $750 ($2,850 net) -> 409 Confirm
        box_409 = evaluate_event_ticketing_rotating_barcode_policy(
            box_office_release_savings_cents=75000,
        )
        self.assertFalse(box_409.allowed)
        self.assertEqual(box_409.http_status, 409)
        self.assertEqual(box_409.settled_ticket_cents, 285000)
        self.assertEqual(box_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["event_ticket_provenance_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("event-ticket-provenance-sandbox", demo_zh)

    def test_on_demand_cnc_3d_manufacturing_cmm_metrology_escrow_vs_cad_ip_theft_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_on_demand_cnc_cmm_metrology_escrow_policy,
        )

        # 1. Enclave-bound 50-cycle G-code + verified CMM QIF (6um <= 10um) & 7075-T6 MTR -> 200 settled ($32,000)
        commit_ok = evaluate_on_demand_cnc_cmm_metrology_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cnc_cents, 3200000)

        # 2. Raw editable .STEP file or unbound G-code counter -> 403 blocked in 12ms
        cad_403 = evaluate_on_demand_cnc_cmm_metrology_escrow_policy(
            signed_gcode_enclave_bound=False,
        )
        self.assertFalse(cad_403.allowed)
        self.assertEqual(cad_403.http_status, 403)
        self.assertEqual(
            cad_403.cnc_lane, "UNENCRYPTED_CAD_EXFILTRATION_OR_OVERRUN_BLOCKED"
        )

        # 3. 45um CMM runout breach or 6061 alloy substitution -> 422 blocked in 15ms
        cmm_422 = evaluate_on_demand_cnc_cmm_metrology_escrow_policy(
            cmm_tolerance_and_mtr_verified=False,
        )
        self.assertFalse(cmm_422.allowed)
        self.assertEqual(cmm_422.http_status, 422)
        self.assertEqual(
            cmm_422.cnc_lane, "CMM_GD_AND_T_TOLERANCE_OR_MTR_ALLOY_BREACH"
        )

        # 4. Web IQ detects suspended AS9100D certificate in OASIS -> 451 blocked in 310ms
        oas_451 = evaluate_on_demand_cnc_cmm_metrology_escrow_policy(
            webiq_as9100_oasis_and_itar_clean=False,
        )
        self.assertFalse(oas_451.allowed)
        self.assertEqual(oas_451.http_status, 451)

        # 5. Web IQ discovers local 5-axis pallet nesting saving $4,600 ($27,400 net) -> 409 Confirm
        nest_409 = evaluate_on_demand_cnc_cmm_metrology_escrow_policy(
            local_nesting_savings_cents=460000,
        )
        self.assertFalse(nest_409.allowed)
        self.assertEqual(nest_409.http_status, 409)
        self.assertEqual(nest_409.settled_cnc_cents, 2740000)
        self.assertEqual(nest_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cnc_metrology_escrow_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cnc-metrology-escrow-sandbox", demo_zh)

    def test_iot_esim_sgp32_roaming_cap_mandate_vs_bill_shock_shutdown_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_iot_esim_sgp32_roaming_cap_policy,
        )

        # 1. Active CDR ICCIDs + Zone-1/2 PLMN whitelist -> 200 settled ($14,500)
        commit_ok = evaluate_iot_esim_sgp32_roaming_cap_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_bce_cents, 1450000)

        # 2. Zone-4 maritime satellite latch or runaway OTA loop -> 403 blocked in 12ms
        roam_403 = evaluate_iot_esim_sgp32_roaming_cap_policy(
            roaming_zone_or_quota_breach=True,
        )
        self.assertFalse(roam_403.allowed)
        self.assertEqual(roam_403.http_status, 403)
        self.assertEqual(
            roam_403.iot_lane, "RUNAWAY_ROAMING_QUOTA_OR_ZONE_BREACH_BLOCKED"
        )

        # 3. 1,800 zero-traffic zombie SIMs billed ($2,700 MRC) -> 422 blocked in 15ms
        zomb_422 = evaluate_iot_esim_sgp32_roaming_cap_policy(
            zombie_inactive_sims_billed=True,
        )
        self.assertFalse(zomb_422.allowed)
        self.assertEqual(zomb_422.http_status, 422)
        self.assertEqual(
            zomb_422.iot_lane, "ZOMBIE_INACTIVE_SIM_MRC_BILLING_BLOCKED"
        )

        # 4. Web IQ detects 90-day permanent-roaming ban (Brazil Anatel / Turkey BTK) -> 451 blocked in 310ms
        perm_451 = evaluate_iot_esim_sgp32_roaming_cap_policy(
            webiq_permanent_roaming_compliant=False,
        )
        self.assertFalse(perm_451.allowed)
        self.assertEqual(perm_451.http_status, 451)

        # 5. Web IQ discovers GSMA SGP.32 local MNO profile swap saving $3,400 ($11,100 net) -> 409 Confirm
        sgp_409 = evaluate_iot_esim_sgp32_roaming_cap_policy(
            sgp32_local_profile_savings_cents=340000,
        )
        self.assertFalse(sgp_409.allowed)
        self.assertEqual(sgp_409.http_status, 409)
        self.assertEqual(sgp_409.settled_bce_cents, 1110000)
        self.assertEqual(sgp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["iot_esim_roaming_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("iot-esim-roaming-sandbox", demo_zh)

    def test_clinical_trial_dct_ecoa_adherence_stipend_mandate_vs_duplicate_subject_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_clinical_trial_dct_ecoa_stipend_policy,
        )

        # 1. Unique ZKP subject + smart-blister eCOA + IRB cap -> 200 settled ($1,200)
        commit_ok = evaluate_clinical_trial_dct_ecoa_stipend_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_stipend_cents, 120000)

        # 2. Cross-site duplicate subject inside 30-day washout -> 403 blocked in 12ms
        dup_403 = evaluate_clinical_trial_dct_ecoa_stipend_policy(
            duplicate_subject_hash_detected=True,
        )
        self.assertFalse(dup_403.allowed)
        self.assertEqual(dup_403.http_status, 403)
        self.assertEqual(
            dup_403.dct_lane, "DUPLICATE_TRIAL_SUBJECT_ENROLLMENT_BLOCKED"
        )

        # 3. Backfilled diary without smart-blister proof or IRB cap breach -> 422 blocked in 15ms
        ecoa_422 = evaluate_clinical_trial_dct_ecoa_stipend_policy(
            ecoa_adherence_and_irb_cap_verified=False,
        )
        self.assertFalse(ecoa_422.allowed)
        self.assertEqual(ecoa_422.http_status, 422)
        self.assertEqual(
            ecoa_422.dct_lane, "MISSING_ECOA_DOSING_PROOF_OR_IRB_CAP_BREACH"
        )

        # 4. Web IQ detects FDA Clinical Hold or unconsented V2.0 amendment -> 451 blocked in 310ms
        hold_451 = evaluate_clinical_trial_dct_ecoa_stipend_policy(
            webiq_nct_protocol_and_econsent_active=False,
        )
        self.assertFalse(hold_451.allowed)
        self.assertEqual(hold_451.http_status, 451)

        # 5. Web IQ discovers home-phlebotomy + transit voucher saving $240 ($960 net) -> 409 Confirm
        home_409 = evaluate_clinical_trial_dct_ecoa_stipend_policy(
            home_phlebotomy_voucher_savings_cents=24000,
        )
        self.assertFalse(home_409.allowed)
        self.assertEqual(home_409.http_status, 409)
        self.assertEqual(home_409.settled_stipend_cents, 96000)
        self.assertEqual(home_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["dct_stipend_adherence_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("dct-stipend-adherence-sandbox", demo_zh)

    def test_cre_triple_net_cam_reconciliation_submeter_mandate_vs_landlord_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cre_triple_net_cam_submeter_policy,
        )

        # 1. CapEx-free GL + BACnet submeter & 5% cap + county tax roll matched -> 200 settled ($42,000)
        commit_ok = evaluate_cre_triple_net_cam_submeter_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cam_cents, 4200000)

        # 2. Structural roof CapEx improperly expensed in operating CAM -> 403 blocked in 12ms
        capex_403 = evaluate_cre_triple_net_cam_submeter_policy(
            capex_improperly_expensed_in_cam=True,
        )
        self.assertFalse(capex_403.allowed)
        self.assertEqual(capex_403.http_status, 403)
        self.assertEqual(
            capex_403.cre_lane, "IMPROPER_CAPEX_PASSTHROUGH_IN_CAM_BLOCKED"
        )

        # 3. Pro-rata utility padding ignoring BACnet submeter or >5% cap -> 422 blocked in 15ms
        sub_422 = evaluate_cre_triple_net_cam_submeter_policy(
            submeter_and_controllable_cap_verified=False,
        )
        self.assertFalse(sub_422.allowed)
        self.assertEqual(sub_422.http_status, 422)
        self.assertEqual(
            sub_422.cre_lane,
            "CONTROLLABLE_CAM_CAP_OR_SUBMETER_MISMATCH_BLOCKED",
        )

        # 4. Web IQ detects withheld 18% county property tax appeal reduction -> 451 blocked in 310ms
        tax_451 = evaluate_cre_triple_net_cam_submeter_policy(
            webiq_county_tax_roll_matched=False,
        )
        self.assertFalse(tax_451.allowed)
        self.assertEqual(tax_451.http_status, 451)

        # 5. Web IQ discovers $3,800 municipal utility efficiency rebate ($38,200 net) -> 409 Confirm
        reb_409 = evaluate_cre_triple_net_cam_submeter_policy(
            utility_rebate_cam_offset_cents=380000,
        )
        self.assertFalse(reb_409.allowed)
        self.assertEqual(reb_409.http_status, 409)
        self.assertEqual(reb_409.settled_cam_cents, 3820000)
        self.assertEqual(reb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cre_nnn_cam_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cre-nnn-cam-sandbox", demo_zh)

    def test_commercial_trucking_fuel_card_telematics_j1939_mandate_vs_skimming_siphoning_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_trucking_fuel_telematics_policy,
        )

        # 1. ELD GPS within 150m + J1939 tank delta matches 250 gal (#2 ULSD) -> 200 settled ($950)
        commit_ok = evaluate_commercial_trucking_fuel_telematics_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_fuel_cents, 95000)

        # 2. Skimmed card swiped 400 miles away from tractor ELD GPS -> 403 blocked in 12ms
        gps_403 = evaluate_commercial_trucking_fuel_telematics_policy(
            gps_pump_proximity_matched=False,
        )
        self.assertFalse(gps_403.allowed)
        self.assertEqual(gps_403.http_status, 403)
        self.assertEqual(
            gps_403.fuel_lane, "GPS_PUMP_PROXIMITY_GHOST_FUELING_BLOCKED"
        )

        # 3. Side-tank siphoning (250 gal billed vs +160 gal in tank) or gas grade -> 422 blocked in 15ms
        j1939_422 = evaluate_commercial_trucking_fuel_telematics_policy(
            j1939_tank_delta_and_grade_verified=False,
        )
        self.assertFalse(j1939_422.allowed)
        self.assertEqual(j1939_422.http_status, 422)
        self.assertEqual(
            j1939_422.fuel_lane, "J1939_TANK_LEVEL_DELTA_OR_FUEL_GRADE_BREACH"
        )

        # 4. Web IQ detects water-in-diesel contamination citation at station -> 451 blocked in 310ms
        qual_451 = evaluate_commercial_trucking_fuel_telematics_policy(
            webiq_station_fuel_quality_and_ifta_clean=False,
        )
        self.assertFalse(qual_451.allowed)
        self.assertEqual(qual_451.http_status, 451)

        # 5. Web IQ discovers OPIS Cost-Plus + IFTA pre-tax stop saving $135 ($815 net) -> 409 Confirm
        opis_409 = evaluate_commercial_trucking_fuel_telematics_policy(
            opis_ifta_corridor_savings_cents=13500,
        )
        self.assertFalse(opis_409.allowed)
        self.assertEqual(opis_409.http_status, 409)
        self.assertEqual(opis_409.settled_fuel_cents, 81500)
        self.assertEqual(opis_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["fleet_fuel_telematics_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("fleet-fuel-telematics-sandbox", demo_zh)

    def test_aviation_mro_faa8130_traceability_mandate_vs_bogus_sup_parts_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aviation_mro_faa8130_traceability_policy,
        )

        # 1. Cryptographic Part-145 8130-3 + NDT crack-free + FAA UPN clean -> 200 settled ($95,000)
        commit_ok = evaluate_aviation_mro_faa8130_traceability_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_mro_cents, 9500000)

        # 2. Forged PDF 8130-3 scan or broken Back-to-Birth chain (SUP) -> 403 blocked in 12ms
        sup_403 = evaluate_aviation_mro_faa8130_traceability_policy(
            cryptographic_8130_back_to_birth_verified=False,
        )
        self.assertFalse(sup_403.allowed)
        self.assertEqual(sup_403.http_status, 403)
        self.assertEqual(
            sup_403.mro_lane, "SUSPECTED_UNAPPROVED_PART_BOGUS_8130_BLOCKED"
        )

        # 3. Missing signed NDT eddy-current crack proof or cycle shortfall -> 422 blocked in 15ms
        ndt_422 = evaluate_aviation_mro_faa8130_traceability_policy(
            ndt_inspection_and_cycles_verified=False,
        )
        self.assertFalse(ndt_422.allowed)
        self.assertEqual(ndt_422.http_status, 422)
        self.assertEqual(
            ndt_422.mro_lane,
            "MISSING_NDT_CRACK_ATTESTATION_OR_CYCLE_SHORTFALL",
        )

        # 4. Web IQ detects active FAA UPN / EASA SIB bogus-part alert -> 451 blocked in 310ms
        upn_451 = evaluate_aviation_mro_faa8130_traceability_policy(
            webiq_faa_upn_and_ad_clean=False,
        )
        self.assertFalse(upn_451.allowed)
        self.assertEqual(upn_451.http_status, 451)

        # 5. Web IQ discovers FAA-approved PMA equivalent saving $18,500 ($76,500 net) -> 409 Confirm
        pma_409 = evaluate_aviation_mro_faa8130_traceability_policy(
            faa_pma_equivalent_savings_cents=1850000,
        )
        self.assertFalse(pma_409.allowed)
        self.assertEqual(pma_409.http_status, 409)
        self.assertEqual(pma_409.settled_mro_cents, 7650000)
        self.assertEqual(pma_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aviation_mro_traceability_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aviation-mro-traceability-sandbox", demo_zh)

    def test_battery_black_mass_icp_assay_escrow_mandate_vs_slag_adulteration_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_battery_black_mass_icp_assay_escrow_policy,
        )

        # 1. Homogenized ICP-MS grade + dry tare + Basel PIC clean -> 200 settled ($110,000)
        commit_ok = evaluate_battery_black_mass_icp_assay_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_black_mass_cents, 11000000)

        # 2. Stratified LFP substitution or iron slag adulteration -> 403 blocked in 12ms
        slag_403 = evaluate_battery_black_mass_icp_assay_escrow_policy(
            icp_ms_cobalt_nickel_grade_breach=True,
        )
        self.assertFalse(slag_403.allowed)
        self.assertEqual(slag_403.http_status, 403)
        self.assertEqual(
            slag_403.assay_lane, "SLAG_ADULTERATION_OR_LFP_SUBSTITUTION_BLOCKED"
        )

        # 3. Unadjusted 14% moisture tare or >2.5% PVDF fluorine penalty -> 422 blocked in 15ms
        flr_422 = evaluate_battery_black_mass_icp_assay_escrow_policy(
            fluorine_or_moisture_penalty_unadjusted=True,
        )
        self.assertFalse(flr_422.allowed)
        self.assertEqual(flr_422.http_status, 422)
        self.assertEqual(
            flr_422.assay_lane,
            "UNADJUSTED_FLUORINE_PENALTY_OR_MOISTURE_TARE_BLOCKED",
        )

        # 4. Web IQ detects missing Basel Convention hazardous-waste PIC permit -> 451 blocked in 310ms
        bas_451 = evaluate_battery_black_mass_icp_assay_escrow_policy(
            webiq_basel_pic_and_battery_passport_valid=False,
        )
        self.assertFalse(bas_451.allowed)
        self.assertEqual(bas_451.http_status, 451)

        # 5. Web IQ discovers toll-refining sulfate swap saving $12,500 ($97,500 net) -> 409 Confirm
        toll_409 = evaluate_battery_black_mass_icp_assay_escrow_policy(
            toll_refining_arbitrage_savings_cents=1250000,
        )
        self.assertFalse(toll_409.allowed)
        self.assertEqual(toll_409.http_status, 409)
        self.assertEqual(toll_409.settled_black_mass_cents, 9750000)
        self.assertEqual(toll_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["black_mass_assay_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("black-mass-assay-sandbox", demo_zh)

    def test_media_sync_licensing_isrc_iswc_voice_clone_mandate_vs_copyright_takedown_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_media_sync_isrc_iswc_voice_clone_policy,
        )

        # 1. 100% Master ISRC + 100% Publishing ISWC + signed Voice VC -> 200 settled ($15,000)
        commit_ok = evaluate_media_sync_isrc_iswc_voice_clone_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_sync_cents, 1500000)

        # 2. Missing 15% co-publisher ISWC split signature -> 403 blocked in 12ms
        iswc_403 = evaluate_media_sync_isrc_iswc_voice_clone_policy(
            master_isrc_and_100pct_iswc_publishing_cleared=False,
        )
        self.assertFalse(iswc_403.allowed)
        self.assertEqual(iswc_403.http_status, 403)
        self.assertEqual(
            iswc_403.sync_lane,
            "INCOMPLETE_ISWC_PUBLISHING_OR_MASTER_SYNC_CLEARANCE_BLOCKED",
        )

        # 3. Missing SAG-AFTRA / ELVIS Act actor voice replica VC -> 422 blocked in 15ms
        vox_422 = evaluate_media_sync_isrc_iswc_voice_clone_policy(
            biometric_voice_consent_and_term_verified=False,
        )
        self.assertFalse(vox_422.allowed)
        self.assertEqual(vox_422.http_status, 422)
        self.assertEqual(
            vox_422.sync_lane,
            "MISSING_SAG_AFTRA_VOICE_REPLICA_CONSENT_OR_TERM_BREACH",
        )

        # 4. Web IQ detects Songview sample/authorship dispute hold -> 451 blocked in 310ms
        pro_451 = evaluate_media_sync_isrc_iswc_voice_clone_policy(
            webiq_pro_songview_repertory_clean=False,
        )
        self.assertFalse(pro_451.allowed)
        self.assertEqual(pro_451.http_status, 451)

        # 5. Web IQ discovers One-Stop 200% pre-cleared track saving $3,900 ($11,100 net) -> 409 Confirm
        one_409 = evaluate_media_sync_isrc_iswc_voice_clone_policy(
            one_stop_catalog_savings_cents=390000,
        )
        self.assertFalse(one_409.allowed)
        self.assertEqual(one_409.http_status, 409)
        self.assertEqual(one_409.settled_sync_cents, 1110000)
        self.assertEqual(one_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["media_sync_voice_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("media-sync-voice-sandbox", demo_zh)

    def test_humanitarian_disaster_relief_mcc_aid_mandate_vs_ghost_beneficiary_gouging_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_humanitarian_disaster_relief_mcc_aid_policy,
        )

        # 1. ZKP unique disaster household + essential MCC + fair price -> 200 settled ($25,000)
        commit_ok = evaluate_humanitarian_disaster_relief_mcc_aid_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_relief_cents, 2500000)

        # 2. Sybil ghost household or cross-NGO duplicate claim -> 403 blocked in 12ms
        sybil_403 = evaluate_humanitarian_disaster_relief_mcc_aid_policy(
            sybil_ghost_household_detected=True,
        )
        self.assertFalse(sybil_403.allowed)
        self.assertEqual(sybil_403.http_status, 403)
        self.assertEqual(
            sybil_403.relief_lane,
            "SYBIL_GHOST_BENEFICIARY_OR_POLYGON_MISMATCH_BLOCKED",
        )

        # 3. Prohibited gambling/liquor MCC or POS cashback kickback -> 422 blocked in 15ms
        mcc_422 = evaluate_humanitarian_disaster_relief_mcc_aid_policy(
            mcc_essential_relief_whitelist_verified=False,
        )
        self.assertFalse(mcc_422.allowed)
        self.assertEqual(mcc_422.http_status, 422)
        self.assertEqual(
            mcc_422.relief_lane,
            "PROHIBITED_MCC_DIVERSION_OR_CASHBACK_KICKBACK_BLOCKED",
        )

        # 4. Web IQ detects $85 roof tarp violating emergency anti-gouging cap -> 451 blocked in 310ms
        gouge_451 = evaluate_humanitarian_disaster_relief_mcc_aid_policy(
            webiq_emergency_anti_gouging_compliant=False,
        )
        self.assertFalse(gouge_451.allowed)
        self.assertEqual(gouge_451.http_status, 451)

        # 5. Web IQ discovers regional relief cooperative bulk kit saving $4,200 ($20,800 net) -> 409 Confirm
        coop_409 = evaluate_humanitarian_disaster_relief_mcc_aid_policy(
            cooperative_bulk_relief_savings_cents=420000,
        )
        self.assertFalse(coop_409.allowed)
        self.assertEqual(coop_409.http_status, 409)
        self.assertEqual(coop_409.settled_relief_cents, 2080000)
        self.assertEqual(coop_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["disaster_relief_aid_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("disaster-relief-aid-sandbox", demo_zh)

    def test_datacenter_24x7_hourly_ppa_t_eac_mandate_vs_annual_rec_greenwashing_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_datacenter_24x7_hourly_ppa_teac_policy,
        )

        # 1. 100% same-grid hourly T-EACs + negative-LMP zero-floor + clean registry -> 200 settled ($180,000)
        commit_ok = evaluate_datacenter_24x7_hourly_ppa_teac_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ppa_cents, 18000000)

        # 2. Cross-grid or annual unbundled REC mismatch ("nighttime solar") -> 403 blocked in 12ms
        grid_403 = evaluate_datacenter_24x7_hourly_ppa_teac_policy(
            hourly_same_grid_teac_matched=False,
        )
        self.assertFalse(grid_403.allowed)
        self.assertEqual(grid_403.http_status, 403)
        self.assertEqual(
            grid_403.ppa_lane,
            "TEMPORAL_OR_GRID_DELIVERABILITY_MISMATCH_BLOCKED",
        )

        # 3. Unadjusted billing during negative wholesale LMP (-$28/MWh) hours -> 422 blocked in 15ms
        lmp_422 = evaluate_datacenter_24x7_hourly_ppa_teac_policy(
            negative_lmp_curtailment_clause_honored=False,
        )
        self.assertFalse(lmp_422.allowed)
        self.assertEqual(lmp_422.http_status, 422)
        self.assertEqual(
            lmp_422.ppa_lane,
            "NEGATIVE_LMP_ZERO_FLOOR_CLAUSE_BREACH_BLOCKED",
        )

        # 4. Web IQ detects double-counted M-RETS serial or non-additional legacy hydro -> 451 blocked in 310ms
        reg_451 = evaluate_datacenter_24x7_hourly_ppa_teac_policy(
            webiq_rec_registry_and_additionality_clean=False,
        )
        self.assertFalse(reg_451.allowed)
        self.assertEqual(reg_451.http_status, 451)

        # 5. Web IQ discovers BESS solar trough-to-peak time-shift saving $24,500 ($155,500 net) -> 409 Confirm
        bess_409 = evaluate_datacenter_24x7_hourly_ppa_teac_policy(
            bess_storage_timeshift_savings_cents=2450000,
        )
        self.assertFalse(bess_409.allowed)
        self.assertEqual(bess_409.http_status, 409)
        self.assertEqual(bess_409.settled_ppa_cents, 15550000)
        self.assertEqual(bess_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["datacenter_hourly_ppa_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("datacenter-hourly-ppa-sandbox", demo_zh)

    def test_clinical_lab_ivd_reagent_lot_qc_mandate_vs_expired_calibration_failure_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_clinical_lab_ivd_reagent_lot_qc_policy,
        )

        # 1. Westgard QC pass + >=180d single-lot UDI + clean FDA status -> 200 settled ($42,000)
        commit_ok = evaluate_clinical_lab_ivd_reagent_lot_qc_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ivd_cents, 4200000)

        # 2. On-analyzer Westgard 1_3s/2_2s QC calibration failure -> 403 blocked in 12ms
        qc_403 = evaluate_clinical_lab_ivd_reagent_lot_qc_policy(
            westgard_lot_qc_calibration_passed=False,
        )
        self.assertFalse(qc_403.allowed)
        self.assertEqual(qc_403.http_status, 403)
        self.assertEqual(
            qc_403.ivd_lane,
            "WESTGARD_LOT_TO_LOT_QC_CALIBRATION_FAILURE_BLOCKED",
        )

        # 3. Short-dated UDI (<180 days) or fragmented multi-lot shipment -> 422 blocked in 15ms
        udi_422 = evaluate_clinical_lab_ivd_reagent_lot_qc_policy(
            udi_remaining_shelf_life_days_ok=False,
        )
        self.assertFalse(udi_422.allowed)
        self.assertEqual(udi_422.http_status, 422)
        self.assertEqual(
            udi_422.ivd_lane,
            "SHORT_DATED_UDI_EXPIRY_OR_FRAGMENTED_LOT_BLOCKED",
        )

        # 4. Web IQ detects FDA Class I/II recall or EUDAMED FSN -> 451 blocked in 310ms
        fda_451 = evaluate_clinical_lab_ivd_reagent_lot_qc_policy(
            webiq_fda_ivd_recall_and_udi_clean=False,
        )
        self.assertFalse(fda_451.allowed)
        self.assertEqual(fda_451.http_status, 451)

        # 5. Web IQ discovers GPO 6-month sequestered master lot saving $6,300 ($35,700 net) -> 409 Confirm
        gpo_409 = evaluate_clinical_lab_ivd_reagent_lot_qc_policy(
            gpo_sequestered_lot_savings_cents=630000,
        )
        self.assertFalse(gpo_409.allowed)
        self.assertEqual(gpo_409.http_status, 409)
        self.assertEqual(gpo_409.settled_ivd_cents, 3570000)
        self.assertEqual(gpo_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["clinical_ivd_reagent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("clinical-ivd-reagent-sandbox", demo_zh)

    def test_corporate_mice_hotel_room_block_attrition_mandate_vs_double_dip_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_corporate_mice_hotel_attrition_policy,
        )

        # 1. Resold-room mitigation applied + capped BEO fees + clean occupancy audit -> 200 settled ($85,000)
        commit_ok = evaluate_corporate_mice_hotel_attrition_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_folio_cents, 8500000)

        # 2. Unmitigated room-block attrition double-dipping -> 403 blocked in 12ms
        dip_403 = evaluate_corporate_mice_hotel_attrition_policy(
            resold_room_mitigation_credit_applied=False,
        )
        self.assertFalse(dip_403.allowed)
        self.assertEqual(dip_403.http_status, 403)
        self.assertEqual(
            dip_403.mice_lane,
            "UNMITIGATED_ROOM_ATTRITION_DOUBLE_DIP_BLOCKED",
        )

        # 3. Uncontracted 26% in-house AV admin fee or compounded service fee -> 422 blocked in 15ms
        av_422 = evaluate_corporate_mice_hotel_attrition_policy(
            contracted_av_and_service_fee_cap_honored=False,
        )
        self.assertFalse(av_422.allowed)
        self.assertEqual(av_422.http_status, 422)
        self.assertEqual(
            av_422.mice_lane,
            "UNCONTRACTED_AV_MONOPOLY_OR_COMPOUND_FEE_BLOCKED",
        )

        # 4. Web IQ proves hotel was sold out on event nights or omitted OTA attendees -> 451 blocked in 310ms
        sold_451 = evaluate_corporate_mice_hotel_attrition_policy(
            webiq_hotel_occupancy_and_block_audit_clean=False,
        )
        self.assertFalse(sold_451.allowed)
        self.assertEqual(sold_451.http_status, 451)

        # 5. Web IQ discovers certified outside AV production saving $14,500 ($70,500 net) -> 409 Confirm
        out_409 = evaluate_corporate_mice_hotel_attrition_policy(
            outside_av_production_savings_cents=1450000,
        )
        self.assertFalse(out_409.allowed)
        self.assertEqual(out_409.http_status, 409)
        self.assertEqual(out_409.settled_folio_cents, 7050000)
        self.assertEqual(out_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["mice_hotel_attrition_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("mice-hotel-attrition-sandbox", demo_zh)

    def test_semiconductor_wafer_foundry_kgd_yield_escrow_mandate_vs_gross_wafer_defect_billing_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_semiconductor_wafer_kgd_yield_policy,
        )

        # 1. >=75% Bin-1 KGD yield + ATE-signed STDFv4/DPAT + clean BIS/ERAI -> 200 settled ($240,000)
        commit_ok = evaluate_semiconductor_wafer_kgd_yield_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_wafer_cents, 24000000)

        # 2. CP wafer-sort Bin-1 KGD yield crash (<75%) on gross-wafer invoice -> 403 blocked in 12ms
        yield_403 = evaluate_semiconductor_wafer_kgd_yield_policy(
            stdf_cp_kgd_yield_floor_met=False,
        )
        self.assertFalse(yield_403.allowed)
        self.assertEqual(yield_403.http_status, 403)
        self.assertEqual(
            yield_403.kgd_lane,
            "PARAMETRIC_WAFER_SORT_KGD_YIELD_COLLAPSE_BLOCKED",
        )

        # 3. Unsigned CSV wafer map or unscreened DPAT IDDQ leakage outliers -> 422 blocked in 15ms
        stdf_422 = evaluate_semiconductor_wafer_kgd_yield_policy(
            ate_signed_stdf_and_pat_outlier_verified=False,
        )
        self.assertFalse(stdf_422.allowed)
        self.assertEqual(stdf_422.http_status, 422)
        self.assertEqual(
            stdf_422.kgd_lane,
            "UNSIGNED_STDF_WAFER_MAP_OR_DPAT_OUTLIER_BLOCKED",
        )

        # 4. Web IQ detects BIS 3A090 restriction or ERAI laser-remarked counterfeit lot -> 451 blocked in 310ms
        bis_451 = evaluate_semiconductor_wafer_kgd_yield_policy(
            webiq_export_fdpr_and_erai_lot_clean=False,
        )
        self.assertFalse(bis_451.allowed)
        self.assertEqual(bis_451.http_status, 451)

        # 5. Web IQ discovers Foundry MPW shuttle reticle-sharing saving $38,000 ($202,000 net) -> 409 Confirm
        mpw_409 = evaluate_semiconductor_wafer_kgd_yield_policy(
            mpw_shuttle_reticle_savings_cents=3800000,
        )
        self.assertFalse(mpw_409.allowed)
        self.assertEqual(mpw_409.http_status, 409)
        self.assertEqual(mpw_409.settled_wafer_cents, 20200000)
        self.assertEqual(mpw_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["semiconductor_kgd_yield_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("semiconductor-kgd-yield-sandbox", demo_zh)

    def test_maritime_bunker_fuel_coriolis_mfm_sulfur_mandate_vs_cappuccino_short_delivery_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_maritime_bunker_fuel_coriolis_mfm_policy,
        )

        # 1. Sealed Coriolis MFM 500 MT mass + ISO 8217 sulfur/Cat-Fines pass + clean port -> 200 settled ($320,000)
        commit_ok = evaluate_maritime_bunker_fuel_coriolis_mfm_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_bunker_cents, 32000000)

        # 2. Cappuccino aerated-foam shortfall or missing Coriolis MFM eBDN -> 403 blocked in 12ms
        foam_403 = evaluate_maritime_bunker_fuel_coriolis_mfm_policy(
            coriolis_mfm_mass_and_zero_aerated_foam_verified=False,
        )
        self.assertFalse(foam_403.allowed)
        self.assertEqual(foam_403.http_status, 403)
        self.assertEqual(
            foam_403.bunker_lane,
            "CAPPUCCINO_AERATED_FOAM_OR_MISSING_CORIOLIS_MFM_BLOCKED",
        )

        # 3. Off-spec MARPOL sulfur (>0.50%) or Cat-Fines (>60 ppm) -> 422 blocked in 15ms
        spec_422 = evaluate_maritime_bunker_fuel_coriolis_mfm_policy(
            iso8217_sulfur_and_cat_fines_spec_passed=False,
        )
        self.assertFalse(spec_422.allowed)
        self.assertEqual(spec_422.http_status, 422)
        self.assertEqual(
            spec_422.bunker_lane,
            "MARPOL_SULFUR_OR_ISO8217_CAT_FINES_OFF_SPEC_BLOCKED",
        )

        # 4. Web IQ detects VPS/FOBAS chlorinated-organics port alert -> 451 blocked in 310ms
        imo_451 = evaluate_maritime_bunker_fuel_coriolis_mfm_policy(
            webiq_port_bunker_alert_and_barge_license_clean=False,
        )
        self.assertFalse(imo_451.allowed)
        self.assertEqual(imo_451.http_status, 451)

        # 5. Web IQ discovers FuelEU ISCC B30 bio-bunker saving $28,000 ($292,000 net) -> 409 Confirm
        bio_409 = evaluate_maritime_bunker_fuel_coriolis_mfm_policy(
            fueleu_bio_bunker_arbitrage_savings_cents=2800000,
        )
        self.assertFalse(bio_409.allowed)
        self.assertEqual(bio_409.http_status, 409)
        self.assertEqual(bio_409.settled_bunker_cents, 29200000)
        self.assertEqual(bio_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["maritime_bunker_fuel_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("maritime-bunker-fuel-sandbox", demo_zh)

    def test_cpg_retail_slotting_endcap_planogram_mandate_vs_phantom_deduction_diversion_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cpg_retail_slotting_planogram_scanback_policy,
        )

        # 1. >=95% C2PA planogram CV + EDI 852 POS scan-back + live circular price -> 200 settled ($65,000)
        commit_ok = evaluate_cpg_retail_slotting_planogram_scanback_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_promo_cents, 6500000)

        # 2. Phantom endcap display (210/500 stores unbuilt in backroom) -> 403 blocked in 12ms
        phan_403 = evaluate_cpg_retail_slotting_planogram_scanback_policy(
            planogram_endcap_cv_compliance_verified=False,
        )
        self.assertFalse(phan_403.allowed)
        self.assertEqual(phan_403.http_status, 403)
        self.assertEqual(
            phan_403.promo_lane,
            "PHANTOM_ENDCAP_DISPLAY_OR_BACKROOM_STOCK_BLOCKED",
        )

        # 3. Off-invoice forward-buying diversion claim without EDI 852 POS scans -> 422 blocked in 15ms
        fwd_422 = evaluate_cpg_retail_slotting_planogram_scanback_policy(
            pos_scan_back_vs_forward_buy_verified=False,
        )
        self.assertFalse(fwd_422.allowed)
        self.assertEqual(fwd_422.http_status, 422)
        self.assertEqual(
            fwd_422.promo_lane,
            "FORWARD_BUYING_DIVERSION_OR_MISSING_EDI852_SCAN_BLOCKED",
        )

        # 4. Web IQ detects retailer kept $4.99 shelf price without passing promo discount -> 451 blocked in 310ms
        circ_451 = evaluate_cpg_retail_slotting_planogram_scanback_policy(
            webiq_retail_circular_promo_price_live=False,
        )
        self.assertFalse(circ_451.allowed)
        self.assertEqual(circ_451.http_status, 451)

        # 5. Web IQ discovers cross-category co-op endcap split saving $11,500 ($53,500 net) -> 409 Confirm
        coop_409 = evaluate_cpg_retail_slotting_planogram_scanback_policy(
            coop_cross_category_endcap_savings_cents=1150000,
        )
        self.assertFalse(coop_409.allowed)
        self.assertEqual(coop_409.http_status, 409)
        self.assertEqual(coop_409.settled_promo_cents, 5350000)
        self.assertEqual(coop_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cpg_trade_promo_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cpg-trade-promo-sandbox", demo_zh)

    def test_telecom_wholesale_a2p_sms_ait_clawback_mandate_vs_botnet_toll_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_telecom_wholesale_a2p_sms_ait_policy,
        )

        # 1. Human OTP conversion >=5% + STIR/SHAKEN A-Level + clean FCC RMD -> 200 settled ($48,000)
        commit_ok = evaluate_telecom_wholesale_a2p_sms_ait_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_telecom_cents, 4800000)

        # 2. Botnet SMS pumping AIT burst (<5% OTP conversion) -> 403 blocked in 12ms
        ait_403 = evaluate_telecom_wholesale_a2p_sms_ait_policy(
            otp_conversion_rate_and_ait_filter_passed=False,
        )
        self.assertFalse(ait_403.allowed)
        self.assertEqual(ait_403.http_status, 403)
        self.assertEqual(
            ait_403.telecom_lane,
            "SMS_PUMPING_AIT_ZERO_CONVERSION_BLOCKED",
        )

        # 3. Missing STIR/SHAKEN A-Level attestation or gray-route SIM-box hop -> 422 blocked in 15ms
        stir_422 = evaluate_telecom_wholesale_a2p_sms_ait_policy(
            stir_shaken_full_attestation_verified=False,
        )
        self.assertFalse(stir_422.allowed)
        self.assertEqual(stir_422.http_status, 422)
        self.assertEqual(
            stir_422.telecom_lane,
            "MISSING_STIR_SHAKEN_ATTESTATION_OR_GRAY_ROUTE_BLOCKED",
        )

        # 4. Web IQ detects FCC RMD removal order or GSMA IRSF fraud prefix -> 451 blocked in 310ms
        fcc_451 = evaluate_telecom_wholesale_a2p_sms_ait_policy(
            webiq_fcc_rmd_and_prefix_reputation_clean=False,
        )
        self.assertFalse(fcc_451.allowed)
        self.assertEqual(fcc_451.http_status, 451)

        # 5. Web IQ discovers FIDO2 Passkey + WhatsApp Auth saving $16,800 ($31,200 net) -> 409 Confirm
        pk_409 = evaluate_telecom_wholesale_a2p_sms_ait_policy(
            passkey_whatsapp_channel_savings_cents=1680000,
        )
        self.assertFalse(pk_409.allowed)
        self.assertEqual(pk_409.http_status, 409)
        self.assertEqual(pk_409.settled_telecom_cents, 3120000)
        self.assertEqual(pk_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["telecom_a2p_sms_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("telecom-a2p-sms-sandbox", demo_zh)

    def test_franchise_royalty_pos_net_sales_gift_card_mandate_vs_gross_delivery_overcharge_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_franchise_royalty_pos_giftcard_policy,
        )

        # 1. Net adjusted POS sales + 1:1 gift-card credit + clean FDD Item 6 -> 200 settled ($28,000)
        commit_ok = evaluate_franchise_royalty_pos_giftcard_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_royalty_cents, 2800000)

        # 2. Royalty charged on gross 3PD commissions or sales tax -> 403 blocked in 12ms
        gross_403 = evaluate_franchise_royalty_pos_giftcard_policy(
            net_adjusted_pos_sales_royalty_verified=False,
        )
        self.assertFalse(gross_403.allowed)
        self.assertEqual(gross_403.http_status, 403)
        self.assertEqual(
            gross_403.franchise_lane,
            "GROSS_3PD_COMMISSION_OR_TAX_ROYALTY_OVERCHARGE_BLOCKED",
        )

        # 3. Uncredited cross-store corporate gift-card redemptions -> 422 blocked in 15ms
        gc_422 = evaluate_franchise_royalty_pos_giftcard_policy(
            gift_card_cross_store_redemption_credited=False,
        )
        self.assertFalse(gc_422.allowed)
        self.assertEqual(gc_422.http_status, 422)
        self.assertEqual(
            gc_422.franchise_lane,
            "UNCREDITED_GIFT_CARD_OR_LOYALTY_REDEMPTION_SWEEP_BLOCKED",
        )

        # 4. Web IQ detects undisclosed mid-term tech fee absent from FDD Item 6 -> 451 blocked in 310ms
        fdd_451 = evaluate_franchise_royalty_pos_giftcard_policy(
            webiq_fdd_item6_and_ad_fund_audit_clean=False,
        )
        self.assertFalse(fdd_451.allowed)
        self.assertEqual(fdd_451.http_status, 451)

        # 5. Web IQ discovers Franchisee Purchasing Co-Op rebate offset saving $4,200 ($23,800 net) -> 409 Confirm
        coop_409 = evaluate_franchise_royalty_pos_giftcard_policy(
            franchisee_coop_rebate_offset_cents=420000,
        )
        self.assertFalse(coop_409.allowed)
        self.assertEqual(coop_409.http_status, 409)
        self.assertEqual(coop_409.settled_royalty_cents, 2380000)
        self.assertEqual(coop_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["franchise_royalty_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("franchise-royalty-sandbox", demo_zh)

    def test_pharma_pbm_formulary_rebate_340b_duplicate_discount_mandate_vs_double_dip_claim_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_pharma_pbm_340b_rebate_policy,
        )

        # 1. Zero 340B/Medicaid overlap + B2 reversals purged + clean HRSA OPAIS -> 200 settled ($195,000)
        commit_ok = evaluate_pharma_pbm_340b_rebate_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rebate_cents, 19500000)

        # 2. HRSA 340B or Medicaid duplicate-discount overlap -> 403 blocked in 12ms
        dup_403 = evaluate_pharma_pbm_340b_rebate_policy(
            hrsa_340b_and_medicaid_duplicate_discount_excluded=False,
        )
        self.assertFalse(dup_403.allowed)
        self.assertEqual(dup_403.http_status, 403)
        self.assertEqual(
            dup_403.pbm_lane,
            "HRSA_340B_OR_MEDICAID_DUPLICATE_DISCOUNT_BLOCKED",
        )

        # 3. Unpurged NCPDP B2 counter abandonment reversals or tier breach -> 422 blocked in 15ms
        b2_422 = evaluate_pharma_pbm_340b_rebate_policy(
            ncpdp_b2_reversals_purged_and_tier_verified=False,
        )
        self.assertFalse(b2_422.allowed)
        self.assertEqual(b2_422.http_status, 422)
        self.assertEqual(
            b2_422.pbm_lane,
            "UNPURGED_NCPDP_B2_REVERSAL_OR_TIER_BREACH_BLOCKED",
        )

        # 4. Web IQ detects terminated HRSA OPAIS contract pharmacy -> 451 blocked in 310ms
        opais_451 = evaluate_pharma_pbm_340b_rebate_policy(
            webiq_hrsa_opais_and_formulary_tier_clean=False,
        )
        self.assertFalse(opais_451.allowed)
        self.assertEqual(opais_451.http_status, 451)

        # 5. Web IQ discovers transparent Pass-Through PBM saving $26,500 ($168,500 net) -> 409 Confirm
        pass_409 = evaluate_pharma_pbm_340b_rebate_policy(
            transparent_pbm_passthrough_savings_cents=2650000,
        )
        self.assertFalse(pass_409.allowed)
        self.assertEqual(pass_409.http_status, 409)
        self.assertEqual(pass_409.settled_rebate_cents, 16850000)
        self.assertEqual(pass_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["pharma_pbm_340b_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("pharma-pbm-340b-sandbox", demo_zh)

    def test_industrial_equipment_pbth_vibration_telemetry_mandate_vs_fixed_amc_downtime_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_industrial_equipment_pbth_vibration_policy,
        )

        # 1. OPC-UA productive load hours + ISO 20816 Zone A/B vibration + clean ICS -> 200 settled ($75,000)
        commit_ok = evaluate_industrial_equipment_pbth_vibration_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_pbth_cents, 7500000)

        # 2. Fault-idle wall-clock billing or <99.0% SLA breach -> 403 blocked in 12ms
        idle_403 = evaluate_industrial_equipment_pbth_vibration_policy(
            opcua_productive_load_hours_and_sla_met=False,
        )
        self.assertFalse(idle_403.allowed)
        self.assertEqual(idle_403.http_status, 403)
        self.assertEqual(
            idle_403.pbth_lane,
            "UNPLANNED_DOWNTIME_OR_IDLE_WALLCLOCK_BILLING_BLOCKED",
        )

        # 3. Post-PM ISO 20816 Zone D vibration (7.8 mm/s fake PM sign-off) -> 422 blocked in 15ms
        vib_422 = evaluate_industrial_equipment_pbth_vibration_policy(
            iso20816_vibration_and_oil_tribology_passed=False,
        )
        self.assertFalse(vib_422.allowed)
        self.assertEqual(vib_422.http_status, 422)
        self.assertEqual(
            vib_422.pbth_lane,
            "ISO20816_VIBRATION_ZONE_D_OR_FAKE_PM_SIGN_OFF_BLOCKED",
        )

        # 4. Web IQ detects unpatched CISA ICS-CERT vulnerability or OEM safety recall -> 451 blocked in 310ms
        ics_451 = evaluate_industrial_equipment_pbth_vibration_policy(
            webiq_ics_safety_bulletin_and_spares_clean=False,
        )
        self.assertFalse(ics_451.allowed)
        self.assertEqual(ics_451.http_status, 451)

        # 5. Web IQ discovers scheduled-turnaround reman cartridge swap saving $11,200 ($63,800 net) -> 409 Confirm
        turn_409 = evaluate_industrial_equipment_pbth_vibration_policy(
            turnaround_window_reman_savings_cents=1120000,
        )
        self.assertFalse(turn_409.allowed)
        self.assertEqual(turn_409.http_status, 409)
        self.assertEqual(turn_409.settled_pbth_cents, 6380000)
        self.assertEqual(turn_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["industrial_pbth_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("industrial-pbth-sandbox", demo_zh)

    def test_fine_jewelry_gia_diamond_kimberley_escrow_mandate_vs_cvd_clone_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_fine_jewelry_gia_diamond_kimberley_policy,
        )

        # 1. Bonded FTIR/PL natural + KPC/G7 origin + clean GIA Report Check -> 200 settled ($140,000)
        commit_ok = evaluate_fine_jewelry_gia_diamond_kimberley_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_diamond_cents, 14000000)

        # 2. Cloned-girdle CVD/HPHT lab-grown synthetic substitution -> 403 blocked in 12ms
        cvd_403 = evaluate_fine_jewelry_gia_diamond_kimberley_policy(
            gia_diamondcheck_ftir_natural_verified=False,
        )
        self.assertFalse(cvd_403.allowed)
        self.assertEqual(cvd_403.http_status, 403)
        self.assertEqual(
            cvd_403.diamond_lane,
            "CVD_HPHT_SYNTHETIC_CLONED_GIRDLE_FRAUD_BLOCKED",
        )

        # 3. Missing Kimberley Process Certificate or G7 >=0.50ct origin proof -> 422 blocked in 15ms
        kpc_422 = evaluate_fine_jewelry_gia_diamond_kimberley_policy(
            kimberley_process_and_g7_origin_verified=False,
        )
        self.assertFalse(kpc_422.allowed)
        self.assertEqual(kpc_422.http_status, 422)
        self.assertEqual(
            kpc_422.diamond_lane,
            "MISSING_KIMBERLEY_PROCESS_OR_G7_ORIGIN_TRACEABILITY_BLOCKED",
        )

        # 4. Web IQ detects JSA stolen-stone alert or post-grading HPHT treatment -> 451 blocked in 310ms
        gia_451 = evaluate_fine_jewelry_gia_diamond_kimberley_policy(
            webiq_gia_report_check_and_rapnet_clean=False,
        )
        self.assertFalse(gia_451.allowed)
        self.assertEqual(gia_451.http_status, 451)

        # 5. Web IQ discovers direct Sightholder bourse sourcing saving $19,500 ($120,500 net) -> 409 Confirm
        sh_409 = evaluate_fine_jewelry_gia_diamond_kimberley_policy(
            sightholder_direct_bourse_savings_cents=1950000,
        )
        self.assertFalse(sh_409.allowed)
        self.assertEqual(sh_409.http_status, 409)
        self.assertEqual(sh_409.settled_diamond_cents, 12050000)
        self.assertEqual(sh_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["diamond_gia_kimberley_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("diamond-gia-kimberley-sandbox", demo_zh)

    def test_corporate_legal_ebilling_ledes_utbms_mandate_vs_block_billing_padding_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_corporate_legal_ebilling_ledes_utbms_policy,
        )

        # 1. Discrete 0.1h LEDES 1998B + OCG rate card + clean docket -> 200 settled ($92,000)
        commit_ok = evaluate_corporate_legal_ebilling_ledes_utbms_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_legal_cents, 9200000)

        # 2. 8.5h semicolon block-billing or unapproved OCG rate hike -> 403 blocked in 12ms
        blk_403 = evaluate_corporate_legal_ebilling_ledes_utbms_policy(
            ledes_anti_block_billing_and_rate_cap_passed=False,
        )
        self.assertFalse(blk_403.allowed)
        self.assertEqual(blk_403.http_status, 403)
        self.assertEqual(
            blk_403.legal_lane,
            "BLOCK_BILLING_OR_OCG_RATE_CARD_BREACH_BLOCKED",
        )

        # 3. Passive associate shadowing or clerical work billed at attorney rate -> 422 blocked in 15ms
        utb_422 = evaluate_corporate_legal_ebilling_ledes_utbms_policy(
            utbms_no_clerical_or_associate_shadowing_verified=False,
        )
        self.assertFalse(utb_422.allowed)
        self.assertEqual(utb_422.http_status, 422)
        self.assertEqual(
            utb_422.legal_lane,
            "CLERICAL_TASK_AT_ATTORNEY_RATE_OR_SHADOWING_BLOCKED",
        )

        # 4. Web IQ detects 14-min court docket minute entry vs 7.5 hrs billed -> 451 blocked in 310ms
        doc_451 = evaluate_corporate_legal_ebilling_ledes_utbms_policy(
            webiq_court_docket_duration_and_bar_clean=False,
        )
        self.assertFalse(doc_451.allowed)
        self.assertEqual(doc_451.http_status, 451)

        # 5. Web IQ discovers ALSP L140 e-Discovery unbundling saving $21,500 ($70,500 net) -> 409 Confirm
        alsp_409 = evaluate_corporate_legal_ebilling_ledes_utbms_policy(
            alsp_ediscovery_unbundling_savings_cents=2150000,
        )
        self.assertFalse(alsp_409.allowed)
        self.assertEqual(alsp_409.http_status, 409)
        self.assertEqual(alsp_409.settled_legal_cents, 7050000)
        self.assertEqual(alsp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["legal_ledes_utbms_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("legal-ledes-utbms-sandbox", demo_zh)

    def test_industrial_wastewater_cod_ammonia_telemetry_mandate_vs_grab_sample_surcharge_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_industrial_wastewater_cod_telemetry_policy,
        )

        # 1. 24h flow-weighted composite COD + 28% evaporative credit + clean EPA ECHO -> 200 settled ($54,000)
        commit_ok = evaluate_industrial_wastewater_cod_telemetry_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_wastewater_cents, 5400000)

        # 2. Single 15-min CIP grab-sample spike extrapolated across 30 days -> 403 blocked in 12ms
        grab_403 = evaluate_industrial_wastewater_cod_telemetry_policy(
            flow_weighted_composite_cod_and_ph_verified=False,
        )
        self.assertFalse(grab_403.allowed)
        self.assertEqual(grab_403.http_status, 403)
        self.assertEqual(
            grab_403.wastewater_lane,
            "GRAB_SAMPLE_SPIKE_EXTRAPOLATION_OVERBILLING_BLOCKED",
        )

        # 3. Missing cooling-tower evaporation or product-water submeter credit -> 422 blocked in 15ms
        evap_422 = evaluate_industrial_wastewater_cod_telemetry_policy(
            evaporative_cooling_submeter_deduction_applied=False,
        )
        self.assertFalse(evap_422.allowed)
        self.assertEqual(evap_422.http_status, 422)
        self.assertEqual(
            evap_422.wastewater_lane,
            "MISSING_EVAPORATIVE_COOLING_SUBMETER_DEDUCTION_BLOCKED",
        )

        # 4. Web IQ detects contracted wastewater operator in EPA ECHO SNC status -> 451 blocked in 310ms
        epa_451 = evaluate_industrial_wastewater_cod_telemetry_policy(
            webiq_epa_echo_npdes_compliance_clean=False,
        )
        self.assertFalse(epa_451.allowed)
        self.assertEqual(epa_451.http_status, 451)

        # 5. Web IQ discovers industrial-symbiosis byproduct carbon saving $8,400 ($45,600 net) -> 409 Confirm
        sym_409 = evaluate_industrial_wastewater_cod_telemetry_policy(
            industrial_symbiosis_carbon_savings_cents=840000,
        )
        self.assertFalse(sym_409.allowed)
        self.assertEqual(sym_409.http_status, 409)
        self.assertEqual(sym_409.settled_wastewater_cents, 4560000)
        self.assertEqual(sym_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["industrial_wastewater_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("industrial-wastewater-sandbox", demo_zh)

    def test_commercial_airline_acmi_wet_lease_block_hour_mandate_vs_aog_guaranteed_minimum_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_airline_acmi_wet_lease_policy,
        )

        # 1. Pro-rata AOG MGBH + ACARS OOOI block hours + clean IOSA/EU261 -> 200 settled ($450,000)
        commit_ok = evaluate_commercial_airline_acmi_wet_lease_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_acmi_cents, 45000000)

        # 2. Unadjusted MGBH billed during 6-day lessor-fault AOG grounding -> 403 blocked in 12ms
        aog_403 = evaluate_commercial_airline_acmi_wet_lease_policy(
            aog_lessor_fault_mgbh_reduction_applied=False,
        )
        self.assertFalse(aog_403.allowed)
        self.assertEqual(aog_403.http_status, 403)
        self.assertEqual(
            aog_403.acmi_lane,
            "LESSOR_AOG_UNADJUSTED_MGBH_SHORTFALL_BLOCKED",
        )

        # 3. Handwritten pilot logbook padding vs ACARS OOOI telemetry -> 422 blocked in 15ms
        oooi_422 = evaluate_commercial_airline_acmi_wet_lease_policy(
            acars_oooi_block_time_reconciled=False,
        )
        self.assertFalse(oooi_422.allowed)
        self.assertEqual(oooi_422.http_status, 422)
        self.assertEqual(
            oooi_422.acmi_lane,
            "MANUAL_LOGBOOK_PADDING_OR_ACARS_OOOI_MISMATCH_BLOCKED",
        )

        # 4. Web IQ detects lapsed IOSA audit or unindemnified EU261 claims -> 451 blocked in 310ms
        iosa_451 = evaluate_commercial_airline_acmi_wet_lease_policy(
            webiq_iosa_registry_and_eu261_indemnity_clean=False,
        )
        self.assertFalse(iosa_451.allowed)
        self.assertEqual(iosa_451.http_status, 451)

        # 5. Web IQ discovers AMI damp-lease cabin-crew conversion saving $52,000 ($398,000 net) -> 409 Confirm
        ami_409 = evaluate_commercial_airline_acmi_wet_lease_policy(
            damp_lease_ami_crew_savings_cents=5200000,
        )
        self.assertFalse(ami_409.allowed)
        self.assertEqual(ami_409.http_status, 409)
        self.assertEqual(ami_409.settled_acmi_cents, 39800000)
        self.assertEqual(ami_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aviation_acmi_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aviation-acmi-sandbox", demo_zh)

    def test_sports_athlete_nil_sponsorship_morals_audience_mandate_vs_upfront_payout_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_sports_athlete_nil_sponsorship_policy,
        )

        # 1. Authentic human audience + NCAA/CSC active roster + clean morals/FTC -> 200 settled ($60,000)
        commit_ok = evaluate_sports_athlete_nil_sponsorship_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_nil_cents, 6000000)

        # 2. 48% bot followers or competitor logo ambush breach -> 403 blocked in 12ms
        bot_403 = evaluate_sports_athlete_nil_sponsorship_policy(
            verified_human_audience_and_exclusivity_passed=False,
        )
        self.assertFalse(bot_403.allowed)
        self.assertEqual(bot_403.http_status, 403)
        self.assertEqual(
            bot_403.nil_lane,
            "BOT_FOLLOWER_INFLATION_OR_COMPETITOR_AMBUSH_BLOCKED",
        )

        # 3. Missing NCAA/CSC disclosure receipt or transfer-portal opt-out -> 422 blocked in 15ms
        ncaa_422 = evaluate_sports_athlete_nil_sponsorship_policy(
            ncaa_csc_disclosure_and_active_roster_verified=False,
        )
        self.assertFalse(ncaa_422.allowed)
        self.assertEqual(ncaa_422.http_status, 422)
        self.assertEqual(
            ncaa_422.nil_lane,
            "MISSING_NCAA_CSC_DISCLOSURE_OR_ROSTER_ELIGIBILITY_BLOCKED",
        )

        # 4. Web IQ detects official league suspension or omitted FTC #ad tag -> 451 blocked in 310ms
        mor_451 = evaluate_sports_athlete_nil_sponsorship_policy(
            webiq_morals_clause_and_ftc_disclosure_clean=False,
        )
        self.assertFalse(mor_451.allowed)
        self.assertEqual(mor_451.http_status, 451)

        # 5. Web IQ discovers 5-player group co-licensing bundle saving $10,800 ($49,200 net) -> 409 Confirm
        grp_409 = evaluate_sports_athlete_nil_sponsorship_policy(
            group_roster_colicensing_savings_cents=1080000,
        )
        self.assertFalse(grp_409.allowed)
        self.assertEqual(grp_409.http_status, 409)
        self.assertEqual(grp_409.settled_nil_cents, 4920000)
        self.assertEqual(grp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["athlete_nil_sponsorship_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("athlete-nil-sandbox", demo_zh)

    def test_datacenter_colocation_pdu_kwh_pue_cap_mandate_vs_breaker_commit_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_datacenter_colocation_pdu_pue_policy,
        )

        # 1. PDU active kWh + <=1.30 PUE cap + active DOM cross-connects -> 200 settled ($115,000)
        commit_ok = evaluate_datacenter_colocation_pdu_pue_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_colo_cents, 11500000)

        # 2. 500 kW breaker nameplate commit billed instead of 310 kW PDU active kWh -> 403 blocked in 12ms
        brk_403 = evaluate_datacenter_colocation_pdu_pue_policy(
            pdu_actual_kwh_vs_breaker_nameplate_verified=False,
        )
        self.assertFalse(brk_403.allowed)
        self.assertEqual(brk_403.http_status, 403)
        self.assertEqual(
            brk_403.colo_lane,
            "BREAKER_NAMEPLATE_OR_PHANTOM_KW_OVERBILLING_BLOCKED",
        )

        # 3. 1.68 degraded PUE pass-through (>1.30 cap) or 18 dark zombie cross-connects -> 422 blocked in 15ms
        pue_422 = evaluate_datacenter_colocation_pdu_pue_policy(
            pue_ceiling_and_active_crossconnect_verified=False,
        )
        self.assertFalse(pue_422.allowed)
        self.assertEqual(pue_422.http_status, 422)
        self.assertEqual(
            pue_422.colo_lane,
            "CONTRACTUAL_PUE_CAP_BREACH_OR_ZOMBIE_CROSSCONNECT_BLOCKED",
        )

        # 4. Web IQ detects bogus heatwave PUE exemption during 19C wet-bulb month -> 451 blocked in 310ms
        wx_451 = evaluate_datacenter_colocation_pdu_pue_policy(
            webiq_ashrae_weather_and_utility_tariff_clean=False,
        )
        self.assertFalse(wx_451.allowed)
        self.assertEqual(wx_451.http_status, 451)

        # 5. Web IQ discovers PeeringDB IXP port consolidation saving $14,200 ($100,800 net) -> 409 Confirm
        ixp_409 = evaluate_datacenter_colocation_pdu_pue_policy(
            ixp_peering_crossconnect_savings_cents=1420000,
        )
        self.assertFalse(ixp_409.allowed)
        self.assertEqual(ixp_409.http_status, 409)
        self.assertEqual(ixp_409.settled_colo_cents, 10080000)
        self.assertEqual(ixp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["datacenter_colo_pue_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("datacenter-colo-sandbox", demo_zh)

    def test_bulk_chemical_iso_tank_ecd_cleaning_heel_mandate_vs_cross_contamination_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_bulk_chemical_isotank_cleaning_heel_policy,
        )

        # 1. Signed EFTCO e-ECD + 420kg heel tare credited + valid CSC/IMDG -> 200 settled ($38,000)
        commit_ok = evaluate_bulk_chemical_isotank_cleaning_heel_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_isotank_cents, 3800000)

        # 2. Prohibited prior cargo or missing EFTCO e-ECD valve-wash proof -> 403 blocked in 12ms
        eecd_403 = evaluate_bulk_chemical_isotank_cleaning_heel_policy(
            eftco_eecd_and_prior_cargo_clean_verified=False,
        )
        self.assertFalse(eecd_403.allowed)
        self.assertEqual(eecd_403.http_status, 403)
        self.assertEqual(
            eecd_403.isotank_lane,
            "PRIOR_CARGO_CONTAMINATION_OR_MISSING_EFTCO_EECD_BLOCKED",
        )

        # 3. Uncredited 420kg clinging heel tare or unmanifested disposal fee -> 422 blocked in 15ms
        heel_422 = evaluate_bulk_chemical_isotank_cleaning_heel_policy(
            heel_residue_tare_and_disposal_reconciled=False,
        )
        self.assertFalse(heel_422.allowed)
        self.assertEqual(heel_422.http_status, 422)
        self.assertEqual(
            heel_422.isotank_lane,
            "UNCREDITED_TANK_HEEL_RESIDUE_OR_PHANTOM_DISPOSAL_BLOCKED",
        )

        # 4. Web IQ detects expired 2.5-year CSC hydro test or wrong UN IMDG T-Code -> 451 blocked in 310ms
        imdg_451 = evaluate_bulk_chemical_isotank_cleaning_heel_policy(
            webiq_imdg_tcode_and_csc_hydro_test_clean=False,
        )
        self.assertFalse(imdg_451.allowed)
        self.assertEqual(imdg_451.http_status, 451)

        # 5. Web IQ discovers dedicated 1.5-bar nitrogen-blanket reload saving $5,800 ($32,200 net) -> 409 Confirm
        n2_409 = evaluate_bulk_chemical_isotank_cleaning_heel_policy(
            dedicated_nitrogen_reload_savings_cents=580000,
        )
        self.assertFalse(n2_409.allowed)
        self.assertEqual(n2_409.http_status, 409)
        self.assertEqual(n2_409.settled_isotank_cents, 3220000)
        self.assertEqual(n2_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["chemical_isotank_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("chemical-isotank-sandbox", demo_zh)

    def test_automotive_dealership_floorplan_vin_telemetry_mandate_vs_sold_out_of_trust_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_automotive_dealership_floorplan_vin_policy,
        )

        # 1. CAN-bus VIN on lot + exclusive UCC-1/e-MSO lien + clean NHTSA -> 200 settled ($210,000)
        commit_ok = evaluate_automotive_dealership_floorplan_vin_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_floorplan_cents, 21000000)

        # 2. Sold-Out-of-Trust (SOT) off-lot float fraud or >250mi demo breach -> 403 blocked in 12ms
        sot_403 = evaluate_automotive_dealership_floorplan_vin_policy(
            obd2_uwb_lot_presence_and_odometer_verified=False,
        )
        self.assertFalse(sot_403.allowed)
        self.assertEqual(sot_403.http_status, 403)
        self.assertEqual(
            sot_403.floorplan_lane,
            "SOLD_OUT_OF_TRUST_OR_ODOMETER_DEMO_BREACH_BLOCKED",
        )

        # 3. Cross-lender Double-Flooring duplicate VIN pledge -> 422 blocked in 15ms
        dbl_422 = evaluate_automotive_dealership_floorplan_vin_policy(
            ucc1_nmvtis_single_lien_verified=False,
        )
        self.assertFalse(dbl_422.allowed)
        self.assertEqual(dbl_422.http_status, 422)
        self.assertEqual(
            dbl_422.floorplan_lane,
            "DOUBLE_FLOORING_DUPLICATE_VIN_LIEN_BLOCKED",
        )

        # 4. Web IQ detects open NHTSA Stop-Sale recall or NMVTIS flood title -> 451 blocked in 310ms
        nht_451 = evaluate_automotive_dealership_floorplan_vin_policy(
            webiq_nhtsa_stop_sale_and_title_brand_clean=False,
        )
        self.assertFalse(nht_451.allowed)
        self.assertEqual(nht_451.http_status, 451)

        # 5. Web IQ discovers OEM 30-day in-transit subvention saving $9,600 ($200,400 net) -> 409 Confirm
        sub_409 = evaluate_automotive_dealership_floorplan_vin_policy(
            oem_in_transit_subvention_savings_cents=960000,
        )
        self.assertFalse(sub_409.allowed)
        self.assertEqual(sub_409.http_status, 409)
        self.assertEqual(sub_409.settled_floorplan_cents, 20040000)
        self.assertEqual(sub_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["auto_floorplan_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("auto-floorplan-sandbox", demo_zh)

    def test_programmatic_dooh_billboard_proof_of_play_mandate_vs_dark_screen_flat_lease_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_programmatic_dooh_proof_of_play_policy,
        )

        # 1. Verified 900 plays * $15 * 0.75x footfall = $10,125 settled ($7,875 saved) -> 200 OK
        commit_ok = evaluate_programmatic_dooh_proof_of_play_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_dooh_cents, 1012500)
        self.assertEqual(commit_ok.clawback_savings_cents, 787500)

        # 2. Dark screen or dimmed luminance (<3,500 nits) -> 403 blocked in 12ms
        dark_403 = evaluate_programmatic_dooh_proof_of_play_policy(
            tpm_framebuffer_and_luminance_verified=False,
        )
        self.assertFalse(dark_403.allowed)
        self.assertEqual(dark_403.http_status, 403)
        self.assertEqual(
            dark_403.dooh_lane,
            "DARK_SCREEN_OR_DIMMED_LUMINANCE_BILLING_BLOCKED",
        )

        # 3. Unadjusted ghost footfall CPM overbilling -> 422 blocked in 15ms
        foot_422 = evaluate_programmatic_dooh_proof_of_play_policy(
            footfall_multiplier_applied=False,
        )
        self.assertFalse(foot_422.allowed)
        self.assertEqual(foot_422.http_status, 422)
        self.assertEqual(
            foot_422.dooh_lane,
            "UNADJUSTED_GHOST_FOOTFALL_CPM_OVERBILLING_BLOCKED",
        )

        # 4. Web IQ detects municipal scaffolding obstructing sightline -> 451 blocked in 310ms
        scaf_451 = evaluate_programmatic_dooh_proof_of_play_policy(
            webiq_sightline_and_permit_clean=False,
        )
        self.assertFalse(scaf_451.allowed)
        self.assertEqual(scaf_451.http_status, 451)

        # 5. Web IQ discovers weather/daypart indoor transit reallocation saving $1,850 ($8,275 net) -> 409 Confirm
        wea_409 = evaluate_programmatic_dooh_proof_of_play_policy(
            daypart_weather_reallocation_savings_cents=185000,
        )
        self.assertFalse(wea_409.allowed)
        self.assertEqual(wea_409.http_status, 409)
        self.assertEqual(wea_409.settled_dooh_cents, 827500)
        self.assertEqual(wea_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["outdoor_dooh_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("outdoor-dooh-billboard-sandbox", demo_zh)

    def test_commercial_seed_biotech_trait_pcr_germination_mandate_vs_brown_bag_piracy_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_seed_trait_pcr_policy,
        )

        # 1. Verified qPCR F1 purity (>=98%) + ISTA germination (>=92%) + UPOV split -> 200 OK ($160,000)
        commit_ok = evaluate_commercial_seed_trait_pcr_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_seed_cents, 16000000)

        # 2. Brown-Bag F2 piracy or diluted biotech trait purity -> 403 blocked in 12ms
        f2_403 = evaluate_commercial_seed_trait_pcr_policy(
            qpcr_trait_purity_and_upov_license_verified=False,
        )
        self.assertFalse(f2_403.allowed)
        self.assertEqual(f2_403.http_status, 403)
        self.assertEqual(
            f2_403.seed_lane,
            "BROWN_BAG_F2_PIRACY_OR_TRAIT_DILUTION_BLOCKED",
        )

        # 3. Stale carryover seed with ISTA germination <92% -> 422 blocked in 15ms
        germ_422 = evaluate_commercial_seed_trait_pcr_policy(
            ista_germination_and_moisture_passed=False,
        )
        self.assertFalse(germ_422.allowed)
        self.assertEqual(germ_422.http_status, 422)
        self.assertEqual(
            germ_422.seed_lane,
            "STALE_SEED_LOW_ISTA_GERMINATION_OR_MOISTURE_BLOCKED",
        )

        # 4. Web IQ detects GDD frost-zone mismatch or noxious-weed quarantine -> 451 blocked in 310ms
        eco_451 = evaluate_commercial_seed_trait_pcr_policy(
            webiq_ecozone_and_phytosanitary_clean=False,
        )
        self.assertFalse(eco_451.allowed)
        self.assertEqual(eco_451.http_status, 451)

        # 5. Web IQ discovers co-op biological seed-treatment rebate saving $22,400 ($137,600 net) -> 409 Confirm
        reb_409 = evaluate_commercial_seed_trait_pcr_policy(
            coop_seed_treatment_rebate_savings_cents=2240000,
        )
        self.assertFalse(reb_409.allowed)
        self.assertEqual(reb_409.http_status, 409)
        self.assertEqual(reb_409.settled_seed_cents, 13760000)
        self.assertEqual(reb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["commercial_seed_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("seed-trait-pcr-sandbox", demo_zh)

    def test_fine_art_auction_provenance_droit_de_suite_mandate_vs_looted_forgery_wire_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_fine_art_auction_provenance_policy,
        )

        # 1. Verified Catalogue Raisonne + XRF pigment + ALR/UCC-1 clean -> 200 OK ($350,000)
        commit_ok = evaluate_fine_art_auction_provenance_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_art_cents, 35000000)

        # 2. Anachronistic synthetic pigment forgery or missing Catalogue Raisonne -> 403 blocked in 12ms
        xrf_403 = evaluate_fine_art_auction_provenance_policy(
            catalogue_raisonne_and_xrf_pigment_verified=False,
        )
        self.assertFalse(xrf_403.allowed)
        self.assertEqual(xrf_403.http_status, 403)
        self.assertEqual(
            xrf_403.art_lane,
            "ANACHRONISTIC_XRF_PIGMENT_FORGERY_OR_UNCATALOGUED_BLOCKED",
        )

        # 3. Art Loss Register (ALR) stolen hit or undisclosed UCC-1 art lien -> 422 blocked in 15ms
        alr_422 = evaluate_fine_art_auction_provenance_policy(
            alr_interpol_and_ucc1_lien_clear=False,
        )
        self.assertFalse(alr_422.allowed)
        self.assertEqual(alr_422.http_status, 422)
        self.assertEqual(
            alr_422.art_lane,
            "ALR_LOOTED_CLAIM_OR_UNDISCLOSED_UCC1_ART_LIEN_BLOCKED",
        )

        # 4. Web IQ detects cultural treasure export ban or CITES ivory frame -> 451 blocked in 310ms
        exp_451 = evaluate_fine_art_auction_provenance_policy(
            webiq_export_license_and_droit_de_suite_clean=False,
        )
        self.assertFalse(exp_451.allowed)
        self.assertEqual(exp_451.http_status, 451)

        # 5. Web IQ discovers bonded Art Freeport warrant transfer saving $31,000 ($319,000 net) -> 409 Confirm
        frp_409 = evaluate_fine_art_auction_provenance_policy(
            freeport_bonded_transfer_tax_savings_cents=3100000,
        )
        self.assertFalse(frp_409.allowed)
        self.assertEqual(frp_409.http_status, 409)
        self.assertEqual(frp_409.settled_art_cents, 31900000)
        self.assertEqual(frp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["fine_art_provenance_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("fine-art-provenance-sandbox", demo_zh)

    def test_mining_concentrate_offtake_tc_rc_umpire_assay_mandate_vs_provisional_overpayment_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_mining_concentrate_offtake_tcrc_policy,
        )

        # 1. Verified DMT moisture deducted + TC/RC & penalties applied + umpire escrow -> 200 OK ($480,000)
        commit_ok = evaluate_mining_concentrate_offtake_tcrc_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_mining_cents, 48000000)

        # 2. Wet-ton billing without H2O deduction or load-port assay inflation -> 403 blocked in 12ms
        wet_403 = evaluate_mining_concentrate_offtake_tcrc_policy(
            dmt_moisture_and_umpire_assay_verified=False,
        )
        self.assertFalse(wet_403.allowed)
        self.assertEqual(wet_403.http_status, 403)
        self.assertEqual(
            wet_403.mining_lane,
            "WET_TON_MOISTURE_OR_LOAD_PORT_ASSAY_INFLATION_BLOCKED",
        )

        # 3. Omitted smelter TC/RC or undeducted arsenic penalty -> 422 blocked in 15ms
        tcrc_422 = evaluate_mining_concentrate_offtake_tcrc_policy(
            tcrc_and_penalty_elements_deducted=False,
        )
        self.assertFalse(tcrc_422.allowed)
        self.assertEqual(tcrc_422.http_status, 422)
        self.assertEqual(
            tcrc_422.mining_lane,
            "OMITTED_SMELTER_TCRC_OR_IMPURITY_PENALTY_BLOCKED",
        )

        # 4. Web IQ detects Arsenic >0.50% customs ban or IMSBC TML breach -> 451 blocked in 310ms
        ars_451 = evaluate_mining_concentrate_offtake_tcrc_policy(
            webiq_customs_arsenic_and_imsbc_tml_clean=False,
        )
        self.assertFalse(ars_451.allowed)
        self.assertEqual(ars_451.http_status, 451)

        # 5. Web IQ discovers bonded port 1:2 clean-concentrate blending saving $46,000 ($434,000 net) -> 409 Confirm
        bld_409 = evaluate_mining_concentrate_offtake_tcrc_policy(
            bonded_blending_hub_savings_cents=4600000,
        )
        self.assertFalse(bld_409.allowed)
        self.assertEqual(bld_409.http_status, 409)
        self.assertEqual(bld_409.settled_mining_cents, 43400000)
        self.assertEqual(bld_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["mining_offtake_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("mining-offtake-tcrc-sandbox", demo_zh)

    def test_aviation_saf_book_and_claim_corsia_scope3_mandate_vs_greenwashing_surcharge_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aviation_saf_book_and_claim_policy,
        )

        # 1. Verified RSB/ISCC LEI retirement + ASTM D7566 uplift + clean PoS -> 200 OK ($260,000)
        commit_ok = evaluate_aviation_saf_book_and_claim_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_saf_cents, 26000000)

        # 2. Scope 3 double-counting or unretired PDF certificate -> 403 blocked in 12ms
        dup_403 = evaluate_aviation_saf_book_and_claim_policy(
            rsb_iscc_unique_lei_retirement_verified=False,
        )
        self.assertFalse(dup_403.allowed)
        self.assertEqual(dup_403.http_status, 403)
        self.assertEqual(
            dup_403.saf_lane,
            "SCOPE3_DOUBLE_COUNTING_OR_UNRETIRED_SAF_SERIAL_BLOCKED",
        )

        # 3. Missing current-vintage ASTM D7566 hydrant uplift receipt or LCA <70% -> 422 blocked in 15ms
        iou_422 = evaluate_aviation_saf_book_and_claim_policy(
            astm_d7566_uplift_and_lca_70pct_passed=False,
        )
        self.assertFalse(iou_422.allowed)
        self.assertEqual(iou_422.http_status, 422)
        self.assertEqual(
            iou_422.saf_lane,
            "UNINJECTED_FORWARD_IOU_OR_LOW_LCA_SAF_BLOCKED",
        )

        # 4. Web IQ detects suspended ISCC certificate or palm-oil PFAD feedstock -> 451 blocked in 310ms
        plm_451 = evaluate_aviation_saf_book_and_claim_policy(
            webiq_corsia_feedstock_and_pos_clean=False,
        )
        self.assertFalse(plm_451.allowed)
        self.assertEqual(plm_451.http_status, 451)

        # 5. Web IQ discovers IRA 45Z & LCFS tax-credit pass-through saving $38,000 ($222,000 net) -> 409 Confirm
        tax_409 = evaluate_aviation_saf_book_and_claim_policy(
            clean_fuel_tax_credit_passthrough_cents=3800000,
        )
        self.assertFalse(tax_409.allowed)
        self.assertEqual(tax_409.http_status, 409)
        self.assertEqual(tax_409.settled_saf_cents, 22200000)
        self.assertEqual(tax_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aviation_saf_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aviation-saf-book-claim-sandbox", demo_zh)

    def test_hospital_surgical_implant_consignment_udi_rfid_mandate_vs_rep_sheet_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_hospital_surgical_implant_consignment_policy,
        )

        # 1. Verified EHR patient implant UDI + CSSD sterilization + GPO cap -> 200 OK ($145,000)
        commit_ok = evaluate_hospital_surgical_implant_consignment_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_implant_cents, 14500000)

        # 2. Dropped/un-implanted screw on handwritten rep charge sheet -> 403 blocked in 12ms
        drp_403 = evaluate_hospital_surgical_implant_consignment_policy(
            ehr_patient_implant_udi_matched=False,
        )
        self.assertFalse(drp_403.allowed)
        self.assertEqual(drp_403.http_status, 403)
        self.assertEqual(
            drp_403.implant_lane,
            "UNIMPLANTED_OR_DROPPED_SCREW_REP_SHEET_BILLING_BLOCKED",
        )

        # 3. Unsterilized rep trunk stock or GPO price cap breach -> 422 blocked in 15ms
        trk_422 = evaluate_hospital_surgical_implant_consignment_policy(
            cssd_autoclave_and_gpo_price_cap_passed=False,
        )
        self.assertFalse(trk_422.allowed)
        self.assertEqual(trk_422.http_status, 422)
        self.assertEqual(
            trk_422.implant_lane,
            "UNSTERILIZED_TRUNK_STOCK_OR_GPO_PRICE_CAP_BREACH_BLOCKED",
        )

        # 4. Web IQ detects FDA GUDID Class I recalled implant lot -> 451 blocked in 310ms
        rec_451 = evaluate_hospital_surgical_implant_consignment_policy(
            webiq_gudid_recall_and_vbp_tier_clean=False,
        )
        self.assertFalse(rec_451.allowed)
        self.assertEqual(rec_451.http_status, 451)

        # 5. Web IQ discovers Case-ID Construct Cap saving $26,800 ($118,200 net) -> 409 Confirm
        cap_409 = evaluate_hospital_surgical_implant_consignment_policy(
            construct_cap_case_rate_savings_cents=2680000,
        )
        self.assertFalse(cap_409.allowed)
        self.assertEqual(cap_409.http_status, 409)
        self.assertEqual(cap_409.settled_implant_cents, 11820000)
        self.assertEqual(cap_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["surgical_implant_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("hospital-implant-consignment-sandbox", demo_zh)

    def test_subsea_dark_fiber_iru_otdr_diverse_conduit_mandate_vs_collapsed_path_broker_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_subsea_dark_fiber_iru_otdr_policy,
        )

        # 1. Verified KMZ >=50m diversity + bidirectional OTDR <=18dB + consortium NDA -> 200 OK ($520,000)
        commit_ok = evaluate_subsea_dark_fiber_iru_otdr_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_iru_cents, 52000000)

        # 2. Collapsed-path shared manhole or shared Cable Landing Station (<50m) -> 403 blocked in 12ms
        kmz_403 = evaluate_subsea_dark_fiber_iru_otdr_policy(
            kmz_manhole_diversity_50m_verified=False,
        )
        self.assertFalse(kmz_403.allowed)
        self.assertEqual(kmz_403.http_status, 403)
        self.assertEqual(
            kmz_403.iru_lane,
            "COLLAPSED_PATH_SHARED_MANHOLE_OR_CLS_DIVERSITY_FRAUD_BLOCKED",
        )

        # 3. Bidirectional OTDR span loss >18dB or detour RTD breach -> 422 blocked in 15ms
        otdr_422 = evaluate_subsea_dark_fiber_iru_otdr_policy(
            bidirectional_otdr_loss_and_rtd_sla_passed=False,
        )
        self.assertFalse(otdr_422.allowed)
        self.assertEqual(otdr_422.http_status, 422)
        self.assertEqual(
            otdr_422.iru_lane,
            "OTDR_SPAN_LOSS_EXCEEDED_OR_DETOUR_LATENCY_BREACH_BLOCKED",
        )

        # 4. Web IQ detects active subsea cable fault or missing consortium NDA -> 451 blocked in 310ms
        nda_451 = evaluate_subsea_dark_fiber_iru_otdr_policy(
            webiq_cable_fault_and_consortium_nda_clean=False,
        )
        self.assertFalse(nda_451.allowed)
        self.assertEqual(nda_451.http_status, 451)

        # 5. Web IQ discovers direct consortium Open-Cable spectrum IRU saving $64,000 ($456,000 net) -> 409 Confirm
        opn_409 = evaluate_subsea_dark_fiber_iru_otdr_policy(
            open_cable_spectrum_direct_savings_cents=6400000,
        )
        self.assertFalse(opn_409.allowed)
        self.assertEqual(opn_409.http_status, 409)
        self.assertEqual(opn_409.settled_iru_cents, 45600000)
        self.assertEqual(opn_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["subsea_iru_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("subsea-dark-fiber-iru-sandbox", demo_zh)

    def test_film_tv_production_completion_bond_tax_credit_mandate_vs_unaudited_drawdown_overrun_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_film_tv_production_completion_bond_policy,
        )

        # 1. Verified DPR/OCF progress + EFC within 10% bond + QPE & guild lockbox -> 200 OK ($320,000)
        commit_ok = evaluate_film_tv_production_completion_bond_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_drawdown_cents, 32000000)

        # 2. Behind-schedule shoot or EFC breaching 10% completion-bond contingency -> 403 blocked in 12ms
        efc_403 = evaluate_film_tv_production_completion_bond_policy(
            dpr_script_progress_and_efc_bond_verified=False,
        )
        self.assertFalse(efc_403.allowed)
        self.assertEqual(efc_403.http_status, 403)
        self.assertEqual(
            efc_403.production_lane,
            "EFC_COMPLETION_BOND_OVERRUN_OR_MISSING_DPR_OCF_BLOCKED",
        )

        # 3. Non-local spend forfeiting QPE tax credit or unpaid guild P&H fringes -> 422 blocked in 15ms
        qpe_422 = evaluate_film_tv_production_completion_bond_policy(
            qpe_local_spend_and_guild_fringe_locked=False,
        )
        self.assertFalse(qpe_422.allowed)
        self.assertEqual(qpe_422.http_status, 422)
        self.assertEqual(
            qpe_422.production_lane,
            "DISQUALIFIED_QPE_TAX_CREDIT_SPEND_OR_UNPAID_GUILD_FRINGE_BLOCKED",
        )

        # 4. Web IQ detects unconsented SAG-AFTRA AI Digital Replica or title defect -> 451 blocked in 310ms
        sag_451 = evaluate_film_tv_production_completion_bond_policy(
            webiq_sag_aftra_ai_replica_and_chain_of_title_clean=False,
        )
        self.assertFalse(sag_451.allowed)
        self.assertEqual(sag_451.http_status, 451)

        # 5. Web IQ discovers transferable tax-credit bridge monetization saving $48,000 ($272,000 net) -> 409 Confirm
        tax_409 = evaluate_film_tv_production_completion_bond_policy(
            transferable_tax_credit_monetization_savings_cents=4800000,
        )
        self.assertFalse(tax_409.allowed)
        self.assertEqual(tax_409.http_status, 409)
        self.assertEqual(tax_409.settled_drawdown_cents, 27200000)
        self.assertEqual(tax_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["film_production_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("film-tv-completion-bond-sandbox", demo_zh)

    def test_municipal_snow_plow_avl_blade_down_salt_telemetry_mandate_vs_ghost_pass_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_municipal_snow_plow_avl_salt_policy,
        )

        # 1. Verified hydraulic blade-down + geofenced auger salt mass + NWS clean -> 200 OK ($68,000)
        commit_ok = evaluate_municipal_snow_plow_avl_salt_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_snow_cents, 6800000)

        # 2. Blade-up ghost pass or stationary cab-heater idling -> 403 blocked in 12ms
        gho_403 = evaluate_municipal_snow_plow_avl_salt_policy(
            hydraulic_blade_down_and_active_speed_verified=False,
        )
        self.assertFalse(gho_403.allowed)
        self.assertEqual(gho_403.http_status, 403)
        self.assertEqual(
            gho_403.snow_lane,
            "BLADE_UP_GHOST_PASS_OR_STATIONARY_IDLING_PADDING_BLOCKED",
        )

        # 3. Off-site salt diversion or manual ticket exceeding geofenced auger integral -> 422 blocked in 15ms
        aug_422 = evaluate_municipal_snow_plow_avl_salt_policy(
            closed_loop_auger_salt_tonnage_reconciled=False,
        )
        self.assertFalse(aug_422.allowed)
        self.assertEqual(aug_422.http_status, 422)
        self.assertEqual(
            aug_422.snow_lane,
            "DIVERTED_SALT_TONNAGE_OR_UNRECONCILED_AUGER_PULSE_BLOCKED",
        )

        # 4. Web IQ detects snowfall below trigger or EPA watershed chloride breach -> 451 blocked in 310ms
        nws_451 = evaluate_municipal_snow_plow_avl_salt_policy(
            webiq_nws_snowfall_and_epa_chloride_clean=False,
        )
        self.assertFalse(nws_451.allowed)
        self.assertEqual(nws_451.http_status, 451)

        # 5. Web IQ discovers 23.3% pre-wet brine 30% salt reduction saving $11,400 ($56,600 net) -> 409 Confirm
        brn_409 = evaluate_municipal_snow_plow_avl_salt_policy(
            prewet_brine_anti_icing_savings_cents=1140000,
        )
        self.assertFalse(brn_409.allowed)
        self.assertEqual(brn_409.http_status, 409)
        self.assertEqual(brn_409.settled_snow_cents, 5660000)
        self.assertEqual(brn_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["snow_plow_avl_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("snow-plow-avl-salt-sandbox", demo_zh)

    def test_offshore_wind_sov_charter_dp2_wave_height_mandate_vs_breakdown_weather_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_offshore_wind_sov_charter_dp2_policy,
        )

        # 1. Verified Waverider buoy Hs + DP2/W2W gangway + off-hire fuel carve-out -> 200 OK ($420,000)
        commit_ok = evaluate_offshore_wind_sov_charter_dp2_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_sov_cents, 42000000)

        # 2. Mechanical gangway/DP2 breakdown disguised as weather standby -> 403 blocked in 12ms
        brk_403 = evaluate_offshore_wind_sov_charter_dp2_policy(
            waverider_hs_and_dp2_gangway_uptime_verified=False,
        )
        self.assertFalse(brk_403.allowed)
        self.assertEqual(brk_403.http_status, 403)
        self.assertEqual(
            brk_403.sov_lane,
            "MECHANICAL_BREAKDOWN_DISGUISED_AS_WEATHER_STANDBY_BLOCKED",
        )

        # 3. Uncredited MGO bunker fuel burned during Off-Hire window -> 422 blocked in 15ms
        mgo_422 = evaluate_offshore_wind_sov_charter_dp2_policy(
            offhire_mgo_fuel_deduction_reconciled=False,
        )
        self.assertFalse(mgo_422.allowed)
        self.assertEqual(mgo_422.http_status, 422)
        self.assertEqual(
            mgo_422.sov_lane,
            "UNCREDITED_OFFHIRE_MGO_BUNKER_CONSUMPTION_BLOCKED",
        )

        # 4. Web IQ detects cabotage violation or expired DNV annual DP2 FMEA trials -> 451 blocked in 310ms
        dnv_451 = evaluate_offshore_wind_sov_charter_dp2_policy(
            webiq_cabotage_and_dnv_dp_trials_clean=False,
        )
        self.assertFalse(dnv_451.allowed)
        self.assertEqual(dnv_451.http_status, 451)

        # 5. Web IQ discovers OSS charging buoy hybrid green power saving $54,000 ($366,000 net) -> 409 Confirm
        buy_409 = evaluate_offshore_wind_sov_charter_dp2_policy(
            offshore_charging_buoy_hybrid_savings_cents=5400000,
        )
        self.assertFalse(buy_409.allowed)
        self.assertEqual(buy_409.http_status, 409)
        self.assertEqual(buy_409.settled_sov_cents, 36600000)
        self.assertEqual(buy_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["offshore_sov_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("offshore-wind-sov-sandbox", demo_zh)

    def test_luxury_watch_horological_witschi_enquirus_mandate_vs_frankenwatch_super_clone_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_luxury_watch_horological_escrow_policy,
        )

        # 1. Verified free-sprung balance + Witschi 292 deg amplitude + Enquirus clean -> 200 OK ($85,000)
        commit_ok = evaluate_luxury_watch_horological_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_watch_cents, 8500000)

        # 2. Frankenwatch super-clone movement or aftermarket dial -> 403 blocked in 12ms
        frk_403 = evaluate_luxury_watch_horological_escrow_policy(
            freesprung_balance_and_oem_dial_verified=False,
        )
        self.assertFalse(frk_403.allowed)
        self.assertEqual(frk_403.http_status, 403)
        self.assertEqual(
            frk_403.watch_lane,
            "FRANKENWATCH_SUPER_CLONE_MOVEMENT_OR_AFTERMARKET_DIAL_BLOCKED",
        )

        # 3. Low Witschi amplitude (<265 deg) or failed dry-vacuum seal -> 422 blocked in 15ms
        amp_422 = evaluate_luxury_watch_horological_escrow_policy(
            witschi_six_position_amplitude_and_pressure_passed=False,
        )
        self.assertFalse(amp_422.allowed)
        self.assertEqual(amp_422.http_status, 422)
        self.assertEqual(
            amp_422.watch_lane,
            "LOW_WITSCHI_AMPLITUDE_OR_FAILED_VACUUM_PRESSURE_BLOCKED",
        )

        # 4. Web IQ detects stolen serial in Enquirus / The Watch Register -> 451 blocked in 310ms
        enq_451 = evaluate_luxury_watch_horological_escrow_policy(
            webiq_enquirus_watch_register_clean=False,
        )
        self.assertFalse(enq_451.allowed)
        self.assertEqual(enq_451.http_status, 451)

        # 5. Web IQ discovers bonded vault & OEM overhaul credit saving $6,800 ($78,200 net) -> 409 Confirm
        cpo_409 = evaluate_luxury_watch_horological_escrow_policy(
            bonded_cpo_overhaul_credit_savings_cents=680000,
        )
        self.assertFalse(cpo_409.allowed)
        self.assertEqual(cpo_409.http_status, 409)
        self.assertEqual(cpo_409.settled_watch_cents, 7820000)
        self.assertEqual(cpo_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["luxury_watch_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("luxury-watch-horological-sandbox", demo_zh)

    def test_semiconductor_photomask_reticle_kla_defect_pellicle_mandate_vs_repeating_wafer_scrap_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_semiconductor_photomask_reticle_policy,
        )

        # 1. Verified OASIS SHA-256 + KLA D2DB / Zeiss AIMS zero defect + CD-SEM/pellicle -> 200 OK ($380,000)
        commit_ok = evaluate_semiconductor_photomask_reticle_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_reticle_cents, 38000000)

        # 2. Printable repeating reticle defect or Die-to-Die-only inspection -> 403 blocked in 12ms
        d2d_403 = evaluate_semiconductor_photomask_reticle_policy(
            kla_d2db_and_zeiss_aims_zero_defect_verified=False,
        )
        self.assertFalse(d2d_403.allowed)
        self.assertEqual(d2d_403.http_status, 403)
        self.assertEqual(
            d2d_403.reticle_lane,
            "PRINTABLE_REPEATING_RETICLE_DEFECT_OR_DIE_TO_DIE_ONLY_BLOCKED",
        )

        # 3. CD-SEM uniformity excursion (>0.8nm 3sigma) or CNT pellicle defect -> 422 blocked in 15ms
        cdu_422 = evaluate_semiconductor_photomask_reticle_policy(
            cd_sem_uniformity_and_cnt_pellicle_passed=False,
        )
        self.assertFalse(cdu_422.allowed)
        self.assertEqual(cdu_422.http_status, 422)
        self.assertEqual(
            cdu_422.reticle_lane,
            "CD_SEM_UNIFORMITY_EXCURSION_OR_CNT_PELLICLE_DEFECT_BLOCKED",
        )

        # 4. Web IQ detects foundry PDK mask-rule errata conflict or EAR 3B001 hold -> 451 blocked in 310ms
        pdk_451 = evaluate_semiconductor_photomask_reticle_policy(
            webiq_pdk_revision_and_export_control_clean=False,
        )
        self.assertFalse(pdk_451.allowed)
        self.assertEqual(pdk_451.http_status, 451)

        # 5. Web IQ discovers BEOL 4-in-1 Multi-Layer Reticle (MLR) consolidation saving $58,000 ($322,000 net) -> 409 Confirm
        mlr_409 = evaluate_semiconductor_photomask_reticle_policy(
            multi_layer_reticle_mlr_consolidation_savings_cents=5800000,
        )
        self.assertFalse(mlr_409.allowed)
        self.assertEqual(mlr_409.http_status, 409)
        self.assertEqual(mlr_409.settled_reticle_cents, 32200000)
        self.assertEqual(mlr_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["photomask_reticle_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("photomask-reticle-kla-sandbox", demo_zh)

    def test_satellite_eo_sar_tasking_cloud_cover_rpc_orthorectified_mandate_vs_cloudy_frame_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_satellite_eo_sar_tasking_policy,
        )

        # 1. Verified Target-AOI cloud mask <=10% + Off-Nadir <=20 deg + GCP RPC CE90 <=1.5m -> 200 OK ($145,000)
        commit_ok = evaluate_satellite_eo_sar_tasking_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_tasking_cents, 14500000)

        # 2. Core Target AOI polygon obscured by >10% clouds/shadow/glint -> 403 blocked in 11ms
        cld_403 = evaluate_satellite_eo_sar_tasking_policy(
            aoi_polygon_cloud_and_glint_free_verified=False,
        )
        self.assertFalse(cld_403.allowed)
        self.assertEqual(cld_403.http_status, 403)
        self.assertEqual(
            cld_403.satellite_lane,
            "TARGET_AOI_POLYGON_CLOUD_OR_GLINT_OBSCURED_BLOCKED",
        )

        # 3. High Off-Nadir (>20 deg) building layover or RPC CE90 (>1.5m) drift -> 422 blocked in 14ms
        nadir_422 = evaluate_satellite_eo_sar_tasking_policy(
            off_nadir_angle_and_rpc_ortho_ce90_passed=False,
        )
        self.assertFalse(nadir_422.allowed)
        self.assertEqual(nadir_422.http_status, 422)
        self.assertEqual(
            nadir_422.satellite_lane,
            "HIGH_OFF_NADIR_LAYOVER_OR_RPC_CE90_DRIFT_BLOCKED",
        )

        # 4. Web IQ detects sovereign shutter-control restriction or AI derivative EULA breach -> 451 blocked in 295ms
        eula_451 = evaluate_satellite_eo_sar_tasking_policy(
            webiq_shutter_control_and_derivative_eula_clean=False,
        )
        self.assertFalse(eula_451.allowed)
        self.assertEqual(eula_451.http_status, 451)

        # 5. Web IQ pairs 48h archive optical basemap with all-weather X-band Spotlight SAR saving $34,000 ($111,000 net) -> 409 Confirm
        sar_409 = evaluate_satellite_eo_sar_tasking_policy(
            archive_plus_sar_fusion_tasking_savings_cents=3400000,
        )
        self.assertFalse(sar_409.allowed)
        self.assertEqual(sar_409.http_status, 409)
        self.assertEqual(sar_409.settled_tasking_cents, 11100000)
        self.assertEqual(sar_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["satellite_eo_sar_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("satellite-eo-sar-sandbox", demo_zh)

    def test_lng_cargo_custody_transfer_mmbtu_raman_bog_mandate_vs_volumetric_ageing_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_lng_cargo_custody_transfer_policy,
        )

        # 1. Verified GIIGNL Net MMBtu + BOG Vapor-Return deducted + CTMS/Wobbe OK -> 200 OK ($42,000,000)
        commit_ok = evaluate_lng_cargo_custody_transfer_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cargo_cents, 4200000000)

        # 2. Raw volumetric m3 billing or omitted displaced shore-vapor BOG deduction -> 403 blocked in 12ms
        vol_403 = evaluate_lng_cargo_custody_transfer_policy(
            giignl_mmbtu_and_bog_vapor_return_deducted=False,
        )
        self.assertFalse(vol_403.allowed)
        self.assertEqual(vol_403.http_status, 403)
        self.assertEqual(
            vol_403.lng_lane,
            "VOLUMETRIC_BILLING_OR_MISSING_BOG_VAPOR_RETURN_DEDUCTION_BLOCKED",
        )

        # 3. CTMS trim/list ballast distortion or Wobbe Index excursion -> 422 blocked in 15ms
        ctms_422 = evaluate_lng_cargo_custody_transfer_policy(
            ctms_trim_list_and_wobbe_index_passed=False,
        )
        self.assertFalse(ctms_422.allowed)
        self.assertEqual(ctms_422.http_status, 422)
        self.assertEqual(
            ctms_422.lng_lane,
            "CTMS_TRIM_LIST_DISTORTION_OR_WOBBE_INDEX_EXCURSION_BLOCKED",
        )

        # 4. Web IQ detects ISO 6976 reference-temperature mismatch or AIS dark-STS transfer -> 451 blocked in 305ms
        ais_451 = evaluate_lng_cargo_custody_transfer_policy(
            webiq_giignl_reference_temp_and_sanctions_clean=False,
        )
        self.assertFalse(ais_451.allowed)
        self.assertEqual(ais_451.http_status, 451)

        # 5. Web IQ matches terminal -162C cryogenic cold-energy valorization credit saving $680,000 ($41,320,000 net) -> 409 Confirm
        cold_409 = evaluate_lng_cargo_custody_transfer_policy(
            cryogenic_cold_energy_valorization_savings_cents=68000000,
        )
        self.assertFalse(cold_409.allowed)
        self.assertEqual(cold_409.http_status, 409)
        self.assertEqual(cold_409.settled_cargo_cents, 4132000000)
        self.assertEqual(cold_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["lng_custody_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("lng-cargo-custody-sandbox", demo_zh)

    def test_rail_freight_carload_aei_demurrage_constructive_placement_mandate_vs_bunching_surcharge_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_rail_freight_carload_demurrage_policy,
        )

        # 1. Verified AEI RFID switch timestamps + zero bunching/missed-switch -> 200 OK ($92,000)
        commit_ok = evaluate_rail_freight_carload_demurrage_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rail_cents, 9200000)

        # 2. Carrier-induced railcar bunching or missed switch billed as Constructive Placement -> 403 blocked in 11ms
        bch_403 = evaluate_rail_freight_carload_demurrage_policy(
            aei_rfid_and_anti_bunching_missed_switch_verified=False,
        )
        self.assertFalse(bch_403.allowed)
        self.assertEqual(bch_403.http_status, 403)
        self.assertEqual(
            bch_403.rail_lane,
            "CARRIER_RAILCAR_BUNCHING_OR_MISSED_SWITCH_DEMURRAGE_BLOCKED",
        )

        # 3. Private *X railcar billed demurrage on private siding or WIM tare overweight -> 422 blocked in 14ms
        xcar_422 = evaluate_rail_freight_carload_demurrage_policy(
            private_siding_x_car_and_wim_tare_weight_passed=False,
        )
        self.assertFalse(xcar_422.allowed)
        self.assertEqual(xcar_422.http_status, 422)
        self.assertEqual(
            xcar_422.rail_lane,
            "PRIVATE_X_CAR_SIDING_CHARGE_OR_WIM_TARE_OVERWEIGHT_BLOCKED",
        )

        # 4. Web IQ detects STB 49 CFR 1333 embargo breach or FRA hazmat routing violation -> 451 blocked in 295ms
        stb_451 = evaluate_rail_freight_carload_demurrage_policy(
            webiq_stb_1333_reciprocity_and_hazmat_clean=False,
        )
        self.assertFalse(stb_451.allowed)
        self.assertEqual(stb_451.http_status, 451)

        # 5. Web IQ applies Private-Car Loaded Mileage Allowance & Block-Swap credit saving $24,500 ($67,500 net) -> 409 Confirm
        mil_409 = evaluate_rail_freight_carload_demurrage_policy(
            private_car_mileage_and_block_swap_savings_cents=2450000,
        )
        self.assertFalse(mil_409.allowed)
        self.assertEqual(mil_409.http_status, 409)
        self.assertEqual(mil_409.settled_rail_cents, 6750000)
        self.assertEqual(mil_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["rail_carload_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("rail-freight-carload-sandbox", demo_zh)

    def test_grid_scale_bess_tolling_soh_rte_dispatch_mandate_vs_nameplate_degradation_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_grid_scale_bess_tolling_policy,
        )

        # 1. Verified POI Usable SOH >=92% + Net AC-AC RTE >=86% incl. Aux HVAC -> 200 OK ($280,000)
        commit_ok = evaluate_grid_scale_bess_tolling_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_tolling_cents, 28000000)

        # 2. Unadjusted DC nameplate MWh billing despite usable SOH <92% -> 403 blocked in 11ms
        soh_403 = evaluate_grid_scale_bess_tolling_policy(
            poi_usable_soh_and_capacity_test_verified=False,
        )
        self.assertFalse(soh_403.allowed)
        self.assertEqual(soh_403.http_status, 403)
        self.assertEqual(
            soh_403.bess_lane,
            "UNADJUSTED_NAMEPLATE_MWH_OR_POI_SOH_SHORTFALL_BLOCKED",
        )

        # 3. Net AC-AC RTE <86% including Aux HVAC chillers or peak thermal derating -> 422 blocked in 14ms
        rte_422 = evaluate_grid_scale_bess_tolling_policy(
            net_ac_ac_rte_including_aux_hvac_passed=False,
        )
        self.assertFalse(rte_422.allowed)
        self.assertEqual(rte_422.http_status, 422)
        self.assertEqual(
            rte_422.bess_lane,
            "NET_AC_AC_RTE_AUX_LOSS_BREACH_OR_PEAK_THERMAL_DERATING_BLOCKED",
        )

        # 4. Web IQ detects OEM warranty EFC (>365/yr) breach or UL 9540A lapse -> 451 blocked in 295ms
        efc_451 = evaluate_grid_scale_bess_tolling_policy(
            webiq_efc_warranty_cap_and_ul9540a_clean=False,
        )
        self.assertFalse(efc_451.allowed)
        self.assertEqual(efc_451.http_status, 451)

        # 5. Web IQ co-optimizes Day-Ahead + Synchronized Spinning Reserve stacking saving $42,000 ($238,000 net) -> 409 Confirm
        rsv_409 = evaluate_grid_scale_bess_tolling_policy(
            co_optimized_reserve_stacking_savings_cents=4200000,
        )
        self.assertFalse(rsv_409.allowed)
        self.assertEqual(rsv_409.http_status, 409)
        self.assertEqual(rsv_409.settled_tolling_cents, 23800000)
        self.assertEqual(rsv_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["grid_bess_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("grid-bess-tolling-sandbox", demo_zh)

    def test_municipal_water_nrw_dma_minimum_night_flow_mandate_vs_estimated_leakage_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_municipal_water_nrw_dma_policy,
        )

        # 1. Verified DMA 02:00-04:00 MNF reduction + Critical-Point pressure >=25m -> 200 OK ($165,000)
        commit_ok = evaluate_municipal_water_nrw_dma_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_nrw_cents, 16500000)

        # 2. Paper leak estimate without actual DMA magmeter MNF drop -> 403 blocked in 11ms
        mnf_403 = evaluate_municipal_water_nrw_dma_policy(
            dma_night_flow_mnf_magmeter_reduction_verified=False,
        )
        self.assertFalse(mnf_403.allowed)
        self.assertEqual(mnf_403.http_status, 403)
        self.assertEqual(
            mnf_403.water_lane,
            "PAPER_LEAK_ESTIMATE_WITHOUT_DMA_MNF_REDUCTION_BLOCKED",
        )

        # 3. PRV valve-choking dropping Critical-Point pressure <25 mH2O -> 422 blocked in 14ms
        prv_422 = evaluate_municipal_water_nrw_dma_policy(
            critical_point_pressure_and_boundary_valve_passed=False,
        )
        self.assertFalse(prv_422.allowed)
        self.assertEqual(prv_422.http_status, 422)
        self.assertEqual(
            prv_422.water_lane,
            "PRV_VALVE_CHOKING_CRITICAL_PRESSURE_STARVATION_BLOCKED",
        )

        # 4. Web IQ detects AWWA M36 audit discrepancy or terminal free chlorine <0.2 mg/L -> 451 blocked in 295ms
        chl_451 = evaluate_municipal_water_nrw_dma_policy(
            webiq_awwa_m36_audit_and_chlorine_residual_clean=False,
        )
        self.assertFalse(chl_451.allowed)
        self.assertEqual(chl_451.http_status, 451)

        # 5. Web IQ couples closed-loop PRV modulation with booster pump VFD saving $28,000 ($137,000 net) -> 409 Confirm
        vfd_409 = evaluate_municipal_water_nrw_dma_policy(
            prv_pressure_modulation_and_pump_vfd_savings_cents=2800000,
        )
        self.assertFalse(vfd_409.allowed)
        self.assertEqual(vfd_409.http_status, 409)
        self.assertEqual(vfd_409.settled_nrw_cents, 13700000)
        self.assertEqual(vfd_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["water_nrw_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("municipal-water-nrw-sandbox", demo_zh)

    def test_aviation_rotable_exchange_aog_egt_margin_ber_cap_mandate_vs_outright_core_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aviation_rotable_exchange_policy,
        )

        # 1. Verified ATEC bench log + Overhauled FMV cap + >=500 FH ACARS reliability -> 200 OK ($185,000)
        commit_ok = evaluate_aviation_rotable_exchange_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rotable_cents, 18500000)

        # 2. Unsubstantiated BER claim without ATEC bench log or unreturned condemned core -> 403 blocked in 11ms
        ber_403 = evaluate_aviation_rotable_exchange_policy(
            atec_bench_log_and_core_title_return_verified=False,
        )
        self.assertFalse(ber_403.allowed)
        self.assertEqual(ber_403.http_status, 403)
        self.assertEqual(
            ber_403.rotable_lane,
            "UNSUBSTANTIATED_BER_CLAIM_OR_CORE_RETENTION_DOUBLE_DIP_BLOCKED",
        )

        # 3. OEM new Catalog List Price (CLP) overcharge on used unit or incoming DOA rogue unit -> 422 blocked in 14ms
        clp_422 = evaluate_aviation_rotable_exchange_policy(
            fmv_ber_cap_and_incoming_lru_mtbur_passed=False,
        )
        self.assertFalse(clp_422.allowed)
        self.assertEqual(clp_422.http_status, 422)
        self.assertEqual(
            clp_422.rotable_lane,
            "OEM_CLP_LIST_PRICE_OVERCHARGE_OR_INCOMING_ROGUE_UNIT_DOA_BLOCKED",
        )

        # 4. Web IQ detects unlawful late-core fee during customs hold or missing dual-release tag -> 451 blocked in 295ms
        cst_451 = evaluate_aviation_rotable_exchange_policy(
            webiq_customs_stop_clock_and_dual_release_clean=False,
        )
        self.assertFalse(cst_451.allowed)
        self.assertEqual(cst_451.http_status, 451)

        # 5. Web IQ matches FAA Form 8110-3 DER repair rescuing core from BER saving $52,000 ($133,000 net) -> 409 Confirm
        der_409 = evaluate_aviation_rotable_exchange_policy(
            faa_der_repair_and_flat_rate_exchange_savings_cents=5200000,
        )
        self.assertFalse(der_409.allowed)
        self.assertEqual(der_409.http_status, 409)
        self.assertEqual(der_409.settled_rotable_cents, 13300000)
        self.assertEqual(der_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aviation_rotable_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aviation-rotable-exchange-sandbox", demo_zh)

    def test_pharma_active_uld_envirotainer_compressor_telemetry_mandate_vs_tarmac_excursion_demurrage_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_pharma_active_uld_envirotainer_policy,
        )

        # 1. Verified origin SOC >=95% + transit shore power + 6-probe 2-8C intact -> 200 OK ($68,000)
        commit_ok = evaluate_pharma_active_uld_envirotainer_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_uld_cents, 6800000)

        # 2. Uncharged handover or transit GHA left ULD unplugged on tarmac -> 403 blocked in 11ms
        soc_403 = evaluate_pharma_active_uld_envirotainer_policy(
            precool_soc_and_tarmac_shore_power_verified=False,
        )
        self.assertFalse(soc_403.allowed)
        self.assertEqual(soc_403.http_status, 403)
        self.assertEqual(
            soc_403.uld_lane,
            "UNPLUGGED_TARMAC_GHA_BATTERY_DRAIN_OR_UNCHARGED_HANDOVER_BLOCKED",
        )

        # 3. Sub-2.0C protein freeze excursion or unauthorized tarmac door-open -> 422 blocked in 14ms
        frz_422 = evaluate_pharma_active_uld_envirotainer_policy(
            six_probe_2_to_8c_no_freeze_and_door_seal_passed=False,
        )
        self.assertFalse(frz_422.allowed)
        self.assertEqual(frz_422.http_status, 422)
        self.assertEqual(
            frz_422.uld_lane,
            "SUB_2C_PROTEIN_FREEZE_EXCURSION_OR_DOOR_SEAL_BREACH_BLOCKED",
        )

        # 4. Web IQ detects non-CEIV transit handler or unwaived demurrage during FDA/customs hold -> 451 blocked in 295ms
        ceiv_451 = evaluate_pharma_active_uld_envirotainer_policy(
            webiq_ceiv_station_and_customs_stop_clock_clean=False,
        )
        self.assertFalse(ceiv_451.allowed)
        self.assertEqual(ceiv_451.http_status, 451)

        # 5. Web IQ matches One-Way Pool return & PCM VIP passive consolidation saving $16,500 ($51,500 net) -> 409 Confirm
        pool_409 = evaluate_pharma_active_uld_envirotainer_policy(
            one_way_pool_return_and_pcm_hybrid_savings_cents=1650000,
        )
        self.assertFalse(pool_409.allowed)
        self.assertEqual(pool_409.http_status, 409)
        self.assertEqual(pool_409.settled_uld_cents, 5150000)
        self.assertEqual(pool_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["pharma_uld_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("pharma-active-uld-sandbox", demo_zh)

    def test_cement_scm_fly_ash_loi_libs_sulfate_mandate_vs_high_carbon_adulteration_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cement_scm_fly_ash_policy,
        )

        # 1. Verified pre-blow LIBS LOI <=3.0% + XRF SO3/CaO clean -> 200 OK ($118,000)
        commit_ok = evaluate_cement_scm_fly_ash_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_scm_cents, 11800000)

        # 2. High unburned carbon (LOI >3.0%) or SCR ammonia slip -> 403 silo valve locked in 11ms
        loi_403 = evaluate_cement_scm_fly_ash_policy(
            online_libs_loi_and_ammonia_slip_verified=False,
        )
        self.assertFalse(loi_403.allowed)
        self.assertEqual(loi_403.http_status, 403)
        self.assertEqual(
            loi_403.scm_lane,
            "HIGH_LOI_UNBURNED_CARBON_OR_AMMONIA_SLIP_SILO_VALVE_LOCKED",
        )

        # 3. Expansive CFB high-SO3/Free-CaO or inert limestone adulteration -> 422 blocked in 14ms
        xrf_422 = evaluate_cement_scm_fly_ash_policy(
            xrf_so3_free_cao_and_glass_activity_passed=False,
        )
        self.assertFalse(xrf_422.allowed)
        self.assertEqual(xrf_422.http_status, 422)
        self.assertEqual(
            xrf_422.scm_lane,
            "EXPANSIVE_CFB_SO3_FREE_CAO_OR_LIMESTONE_ADULTERATION_BLOCKED",
        )

        # 4. Web IQ detects unapproved CFB boiler origin or fake EPD Scope 3 claim -> 451 blocked in 295ms
        epd_451 = evaluate_cement_scm_fly_ash_policy(
            webiq_boiler_origin_and_epd_scope3_clean=False,
        )
        self.assertFalse(epd_451.allowed)
        self.assertEqual(epd_451.http_status, 451)

        # 5. Web IQ optimizes 55% ternary slag+ash clinker replacement saving $23,000 ($95,000 net) -> 409 Confirm
        trn_409 = evaluate_cement_scm_fly_ash_policy(
            ternary_clinker_substitution_and_epd_savings_cents=2300000,
        )
        self.assertFalse(trn_409.allowed)
        self.assertEqual(trn_409.http_status, 409)
        self.assertEqual(trn_409.settled_scm_cents, 9500000)
        self.assertEqual(trn_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cement_scm_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cement-scm-fly-ash-sandbox", demo_zh)

    def test_pelagic_seafood_tuna_iuu_vms_histamine_superfrozen_mandate_vs_fad_bycatch_spoilage_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_pelagic_seafood_tuna_policy,
        )

        # 1. Verified continuous VMS/EM + -60C hold + Histamine <=30 ppm & zero CO -> 200 OK ($215,000)
        commit_ok = evaluate_pelagic_seafood_tuna_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_tuna_cents, 21500000)

        # 2. Dark-vessel AIS shutoff or FAD-closure IUU poaching -> 403 blocked in 11ms
        iuu_403 = evaluate_pelagic_seafood_tuna_policy(
            vms_ais_continuous_and_em_zero_iuu_verified=False,
        )
        self.assertFalse(iuu_403.allowed)
        self.assertEqual(iuu_403.http_status, 403)
        self.assertEqual(
            iuu_403.tuna_lane,
            "DARK_VESSEL_AIS_GAP_OR_FAD_CLOSURE_IUU_POACHING_BLOCKED",
        )

        # 3. Histamine >30 ppm or illegal Carbon Monoxide (CO) cherry-red color fraud -> 422 blocked in 14ms
        his_422 = evaluate_pelagic_seafood_tuna_policy(
            superfrozen_minus60c_histamine_and_zero_co_passed=False,
        )
        self.assertFalse(his_422.allowed)
        self.assertEqual(his_422.http_status, 422)
        self.assertEqual(
            his_422.tuna_lane,
            "SCOMBROID_HISTAMINE_SPIKE_OR_CARBON_MONOXIDE_COLOR_FRAUD_BLOCKED",
        )

        # 4. Web IQ detects delisted RFMO vessel or missing NOAA SIMP / EU IUU catch certificate -> 451 blocked in 295ms
        rfmo_451 = evaluate_pelagic_seafood_tuna_policy(
            webiq_rfmo_good_standing_and_simp_clean=False,
        )
        self.assertFalse(rfmo_451.allowed)
        self.assertEqual(rfmo_451.http_status, 451)

        # 5. Web IQ routes via Direct Port -60C Superfreezer Container saving $31,000 ($184,000 net) -> 409 Confirm
        reefer_409 = evaluate_pelagic_seafood_tuna_policy(
            direct_port_superfreezer_container_savings_cents=3100000,
        )
        self.assertFalse(reefer_409.allowed)
        self.assertEqual(reefer_409.http_status, 409)
        self.assertEqual(reefer_409.settled_tuna_cents, 18400000)
        self.assertEqual(reefer_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["pelagic_tuna_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("pelagic-seafood-tuna-sandbox", demo_zh)

    def test_industrial_gas_asu_pipeline_specific_power_liquid_backup_mandate_vs_take_or_pay_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_industrial_gas_asu_pipeline_policy,
        )

        # 1. Verified Specific Power <=0.42 kWh/Nm3 + 0C Nm3 mass flow + 5.5N purity -> 200 OK ($340,000)
        commit_ok = evaluate_industrial_gas_asu_pipeline_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_asu_cents, 34000000)

        # 2. Fouled compressor excess kWh or 5x backup liquid surcharge on vendor ASU trip -> 403 blocked in 11ms
        spc_403 = evaluate_industrial_gas_asu_pipeline_policy(
            specific_power_cap_and_trip_liquid_waiver_verified=False,
        )
        self.assertFalse(spc_403.allowed)
        self.assertEqual(spc_403.http_status, 403)
        self.assertEqual(
            spc_403.asu_lane,
            "EXCESS_COMPRESSOR_POWER_OR_VENDOR_TRIP_LIQUID_SURCHARGE_BLOCKED",
        )

        # 3. 20C reference-temperature +7.32% volume inflation or sub-5.5N purity excursion -> 422 blocked in 14ms
        nm3_422 = evaluate_industrial_gas_asu_pipeline_policy(
            iso_0c_nm3_mass_flow_and_5n5_purity_passed=False,
        )
        self.assertFalse(nm3_422.allowed)
        self.assertEqual(nm3_422.http_status, 422)
        self.assertEqual(
            nm3_422.asu_lane,
            "REFERENCE_TEMP_20C_VOLUME_INFLATION_OR_PURITY_EXCURSION_BLOCKED",
        )

        # 4. Web IQ detects unwaived Take-or-Pay during grid curtailment or unmetered piggyback LAR -> 451 blocked in 295ms
        top_451 = evaluate_industrial_gas_asu_pipeline_policy(
            webiq_grid_curtailment_rollover_and_piggyback_clean=False,
        )
        self.assertFalse(top_451.allowed)
        self.assertEqual(top_451.http_status, 451)

        # 5. Web IQ applies Merchant LAR co-product share & valley-power liquefaction saving $49,000 ($291,000 net) -> 409 Confirm
        lar_409 = evaluate_industrial_gas_asu_pipeline_policy(
            merchant_liquid_argon_and_valley_power_savings_cents=4900000,
        )
        self.assertFalse(lar_409.allowed)
        self.assertEqual(lar_409.http_status, 409)
        self.assertEqual(lar_409.settled_asu_cents, 29100000)
        self.assertEqual(lar_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["industrial_asu_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("industrial-gas-asu-sandbox", demo_zh)

    def test_mining_blasting_emulsion_vod_fragmentation_p80_mandate_vs_wet_hole_misfire_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_mining_blasting_emulsion_vod_policy,
        )

        # 1. Verified in-hole VOD >=5,200 m/s + 3D LiDAR P80 <=25cm + PPV <=12mm/s -> 200 OK ($155,000)
        commit_ok = evaluate_mining_blasting_emulsion_vod_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_blasting_cents, 15500000)

        # 2. Low-VOD deflagration (<5,200 m/s, orange NOx fumes) or cavity over-pumping -> 403 blocked in 11ms
        vod_403 = evaluate_mining_blasting_emulsion_vod_policy(
            in_hole_vod_and_cup_density_detonation_verified=False,
        )
        self.assertFalse(vod_403.allowed)
        self.assertEqual(vod_403.http_status, 403)
        self.assertEqual(
            vod_403.blasting_lane,
            "LOW_VOD_DEFLAGRATION_NOX_FUME_OR_CAVITY_OVERPUMP_BLOCKED",
        )

        # 3. Oversize boulder muckpile (P80 >25cm) or highwall PPV excursion -> 422 blocked in 14ms
        p80_422 = evaluate_mining_blasting_emulsion_vod_policy(
            lidar_muckpile_p80_and_ppv_vibration_passed=False,
        )
        self.assertFalse(p80_422.allowed)
        self.assertEqual(p80_422.http_status, 422)
        self.assertEqual(
            p80_422.blasting_lane,
            "OVERSIZE_BOULDER_P80_BREACH_OR_HIGHWALL_PPV_EXCURSION_BLOCKED",
        )

        # 4. Web IQ detects unconfirmed electronic detonator UID misfire risk or MSHA hold -> 451 blocked in 295ms
        uid_451 = evaluate_mining_blasting_emulsion_vod_policy(
            webiq_detonator_uid_geofence_and_msha_clean=False,
        )
        self.assertFalse(uid_451.allowed)
        self.assertEqual(uid_451.http_status, 451)

        # 5. Web IQ couples drill MWD with Mine-to-Mill SAG-mill power optimization saving $29,000 ($126,000 net) -> 409 Confirm
        m2m_409 = evaluate_mining_blasting_emulsion_vod_policy(
            mine_to_mill_sag_power_optimization_savings_cents=2900000,
        )
        self.assertFalse(m2m_409.allowed)
        self.assertEqual(m2m_409.http_status, 409)
        self.assertEqual(m2m_409.settled_blasting_cents, 12600000)
        self.assertEqual(m2m_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["mining_blasting_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("mining-blasting-vod-sandbox", demo_zh)

    def test_semiconductor_upw_ultrapure_water_toc_boron_nanoparticle_mandate_vs_resin_breakthrough_wafer_scrap_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_semiconductor_upw_ultrapure_water_policy,
        )

        # 1. Verified POU TOC/DO <=1.0 ppb + Boron <=15 ppt & Silica <=0.5 ppb + 20nm clean -> 200 OK ($240,000)
        commit_ok = evaluate_semiconductor_upw_ultrapure_water_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_upw_cents, 24000000)

        # 2. Cleanroom POU TOC/DO (>1.0 ppb) or 20nm particle excursion -> 403 blocked in 11ms
        toc_403 = evaluate_semiconductor_upw_ultrapure_water_policy(
            pou_toc_do_and_20nm_particle_verified=False,
        )
        self.assertFalse(toc_403.allowed)
        self.assertEqual(toc_403.http_status, 403)
        self.assertEqual(
            toc_403.upw_lane,
            "POU_TOC_DISSOLVED_OXYGEN_OR_20NM_PARTICLE_EXCURSION_BLOCKED",
        )

        # 3. Silent Boron (>15 ppt) or Colloidal Silica (>0.5 ppb) resin breakthrough behind 18.2 MOhm resistivity -> 422 blocked in 14ms
        bor_422 = evaluate_semiconductor_upw_ultrapure_water_policy(
            boron_ppt_and_colloidal_silica_resin_passed=False,
        )
        self.assertFalse(bor_422.allowed)
        self.assertEqual(bor_422.http_status, 422)
        self.assertEqual(
            bor_422.upw_lane,
            "SILENT_BORON_PPT_OR_COLLOIDAL_SILICA_RESIN_BREAKTHROUGH_BLOCKED",
        )

        # 4. Web IQ detects overdue nuclear-grade resin/185nm UV lamp or TMAH discharge breach -> 451 blocked in 295ms
        f63_451 = evaluate_semiconductor_upw_ultrapure_water_policy(
            webiq_semi_f63_consumable_and_wastewater_clean=False,
        )
        self.assertFalse(f63_451.allowed)
        self.assertEqual(f63_451.http_status, 451)

        # 5. Web IQ orchestrates >=78% Cascade Rinse Reclaim & RO brine reuse saving $38,000 ($202,000 net) -> 409 Confirm
        rec_409 = evaluate_semiconductor_upw_ultrapure_water_policy(
            cascade_rinse_reclaim_and_ro_brine_savings_cents=3800000,
        )
        self.assertFalse(rec_409.allowed)
        self.assertEqual(rec_409.http_status, 409)
        self.assertEqual(rec_409.settled_upw_cents, 20200000)
        self.assertEqual(rec_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["semiconductor_upw_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("semiconductor-upw-sandbox", demo_zh)

    def test_aviation_deicing_glycol_brix_refractometer_holdover_mandate_vs_diluted_fluid_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aviation_deicing_glycol_brix_policy,
        )

        # 1. Verified nozzle Brix LOUT <= OAT-10C + Type IV viscosity >=18,000 mPa-s -> 200 OK ($74,000)
        commit_ok = evaluate_aviation_deicing_glycol_brix_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_deicing_cents, 7400000)

        # 2. Over-diluted glycol billed at neat price or LOUT buffer <10C -> 403 blocked in 11ms
        brx_403 = evaluate_aviation_deicing_glycol_brix_policy(
            nozzle_brix_lout_buffer_and_net_glycol_verified=False,
        )
        self.assertFalse(brx_403.allowed)
        self.assertEqual(brx_403.http_status, 403)
        self.assertEqual(
            brx_403.deicing_lane,
            "OVER_DILUTED_GLYCOL_OR_LOUT_10C_BUFFER_BREACH_BLOCKED",
        )

        # 3. Sheared Type IV viscosity (<18,000 mPa-s) or premature gate-spray HOT expiry re-spray -> 422 blocked in 14ms
        vis_422 = evaluate_aviation_deicing_glycol_brix_policy(
            type_iv_viscosity_and_acdm_hot_window_passed=False,
        )
        self.assertFalse(vis_422.allowed)
        self.assertEqual(vis_422.http_status, 422)
        self.assertEqual(
            vis_422.deicing_lane,
            "SHEARED_TYPE_IV_VISCOSITY_OR_PREMATURE_HOT_RESPRAY_BLOCKED",
        )

        # 4. Web IQ detects missing ACARS Anti-Icing Code or uncredited stormwater BOD charge -> 451 blocked in 295ms
        acr_451 = evaluate_aviation_deicing_glycol_brix_policy(
            webiq_acars_anti_icing_code_and_stormwater_clean=False,
        )
        self.assertFalse(acr_451.allowed)
        self.assertEqual(acr_451.http_status, 451)

        # 5. Web IQ routes fleet to Runway-End CDP with 72% spent-glycol re-distillation saving $18,500 ($55,500 net) -> 409 Confirm
        cdp_409 = evaluate_aviation_deicing_glycol_brix_policy(
            cdp_pad_and_glycol_redistillation_savings_cents=1850000,
        )
        self.assertFalse(cdp_409.allowed)
        self.assertEqual(cdp_409.http_status, 409)
        self.assertEqual(cdp_409.settled_deicing_cents, 5550000)
        self.assertEqual(cdp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aviation_deicing_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aviation-deicing-brix-sandbox", demo_zh)

    def test_ocean_container_street_turn_iicl6_damage_csc_mandate_vs_empty_repositioning_mr_gouging_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ocean_container_street_turn_policy,
        )

        # 1. Verified Gate-Out/In 3D diff + IICL-6 wear immunity + floor moisture <=14% -> 200 OK ($48,000)
        commit_ok = evaluate_ocean_container_street_turn_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_container_cents, 4800000)

        # 2. Pre-existing Gate-Out dent or sub-25mm IICL-6 wear billed as M&R damage -> 403 blocked in 11ms
        mrg_403 = evaluate_ocean_container_street_turn_policy(
            gate_out_in_3d_diff_and_iicl6_wear_verified=False,
        )
        self.assertFalse(mrg_403.allowed)
        self.assertEqual(mrg_403.http_status, 403)
        self.assertEqual(
            mrg_403.container_lane,
            "PRE_EXISTING_GATE_OUT_DENT_OR_IICL6_WEAR_MR_GOUGING_BLOCKED",
        )

        # 3. Damp wood floor (>14% moisture) or roof pinhole light leak on street-turn -> 422 blocked in 14ms
        flr_422 = evaluate_ocean_container_street_turn_policy(
            street_turn_floor_moisture_and_csc_plate_passed=False,
        )
        self.assertFalse(flr_422.allowed)
        self.assertEqual(flr_422.http_status, 422)
        self.assertEqual(
            flr_422.container_lane,
            "DAMP_FLOOR_MOISTURE_OR_ROOF_PINHOLE_LIGHT_LEAK_BLOCKED",
        )

        # 4. Web IQ detects Per-Diem billed during depot appointment lockout or inflated CEDEX tariff -> 451 blocked in 295ms
        fmc_451 = evaluate_ocean_container_street_turn_policy(
            webiq_fmc_return_slot_waiver_and_cedex_clean=False,
        )
        self.assertFalse(fmc_451.allowed)
        self.assertEqual(fmc_451.http_status, 451)

        # 5. Web IQ matches inland Import-to-Export Street-Turn saving $14,200 ($33,800 net) -> 409 Confirm
        str_409 = evaluate_ocean_container_street_turn_policy(
            inland_street_turn_triangulation_savings_cents=1420000,
        )
        self.assertFalse(str_409.allowed)
        self.assertEqual(str_409.http_status, 409)
        self.assertEqual(str_409.settled_container_cents, 3380000)
        self.assertEqual(str_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["container_street_turn_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ocean-container-street-turn-sandbox", demo_zh)

    def test_derms_smart_inverter_ieee2030_5_volt_var_curtailment_mandate_vs_overvoltage_trip_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_derms_smart_inverter_volt_var_policy,
        )

        # 1. Verified IEEE 1547 Volt-VAR + sealed PCC 0.2S meter + utility PF >=0.95 -> 200 OK ($86,000)
        commit_ok = evaluate_derms_smart_inverter_volt_var_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_derms_cents, 8600000)

        # 2. Unity cos-phi=1 causing midday overvoltage trip or utility low-PF penalty -> 403 blocked in 11ms
        vvr_403 = evaluate_derms_smart_inverter_volt_var_policy(
            volt_var_reactive_support_and_pf_verified=False,
        )
        self.assertFalse(vvr_403.allowed)
        self.assertEqual(vvr_403.http_status, 403)
        self.assertEqual(
            vvr_403.derms_lane,
            "UNITY_PF_OVERVOLTAGE_TRIP_OR_UTILITY_PF_PENALTY_BLOCKED",
        )

        # 3. Inverter-app +6.5% ghost kWh inflation over sealed PCC 0.2S revenue meter -> 422 blocked in 14ms
        pcc_422 = evaluate_derms_smart_inverter_volt_var_policy(
            pcc_02s_revenue_meter_net_kwh_passed=False,
        )
        self.assertFalse(pcc_422.allowed)
        self.assertEqual(pcc_422.http_status, 422)
        self.assertEqual(
            pcc_422.derms_lane,
            "INVERTER_APP_GHOST_KWH_TRANSFORMER_LOSS_INFLATION_BLOCKED",
        )

        # 4. Web IQ detects IEEE 2030.5 DOE export breach or negative-LMP reverse backfeed -> 451 blocked in 295ms
        doe_451 = evaluate_derms_smart_inverter_volt_var_policy(
            webiq_ieee2030_5_doe_and_negative_lmp_clean=False,
        )
        self.assertFalse(doe_451.allowed)
        self.assertEqual(doe_451.http_status, 451)

        # 5. Web IQ routes curtailed midday solar to HVAC chiller pre-cooling & EV charging saving $19,500 ($66,500 net) -> 409 Confirm
        thrm_409 = evaluate_derms_smart_inverter_volt_var_policy(
            midday_thermal_precool_and_var_credit_savings_cents=1950000,
        )
        self.assertFalse(thrm_409.allowed)
        self.assertEqual(thrm_409.http_status, 409)
        self.assertEqual(thrm_409.settled_derms_cents, 6650000)
        self.assertEqual(thrm_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["derms_volt_var_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("derms-smart-inverter-sandbox", demo_zh)

    def test_marine_biobunker_b30_iscc_c14_oxidation_stability_mandate_vs_ucome_fraud_filter_clogging_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_marine_biobunker_b30_iscc_policy,
        )

        # 1. Verified ASTM D6866 14C >=29% + ISO 8217:2024 Rancimat >=8h + EU UDB retired -> 200 OK ($295,000)
        commit_ok = evaluate_marine_biobunker_b30_iscc_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_biobunker_cents, 29500000)

        # 2. ASTM D6866 14C biogenic shortfall or virgin palm oil laundered as UCOME -> 403 blocked in 11ms
        c14_403 = evaluate_marine_biobunker_b30_iscc_policy(
            astm_d6866_c14_biogenic_and_non_palm_verified=False,
        )
        self.assertFalse(c14_403.allowed)
        self.assertEqual(c14_403.http_status, 403)
        self.assertEqual(
            c14_403.biobunker_lane,
            "C14_BIOGENIC_SHORTFALL_OR_PALM_OIL_UCOME_LAUNDERING_BLOCKED",
        )

        # 3. ISO 8217:2024 Rancimat <8h oxidation sludge or high CFPP wax gelling -> 422 blocked in 14ms
        rnc_422 = evaluate_marine_biobunker_b30_iscc_policy(
            iso8217_2024_rancimat_and_cfpp_stability_passed=False,
        )
        self.assertFalse(rnc_422.allowed)
        self.assertEqual(rnc_422.http_status, 422)
        self.assertEqual(
            rnc_422.biobunker_lane,
            "RANCIMAT_OXIDATION_SLUDGE_OR_CFPP_WAX_PLUGGING_BLOCKED",
        )

        # 4. Web IQ detects unretired ISCC EU PoS in EU Union Database (UDB) -> 451 blocked in 295ms
        udb_451 = evaluate_marine_biobunker_b30_iscc_policy(
            webiq_eu_udb_pos_retirement_and_fueleu_clean=False,
        )
        self.assertFalse(udb_451.allowed)
        self.assertEqual(udb_451.http_status, 451)

        # 5. Web IQ optimizes FuelEU Maritime Compliance Pooling & HVO blend saving $44,000 ($251,000 net) -> 409 Confirm
        pool_409 = evaluate_marine_biobunker_b30_iscc_policy(
            fueleu_pooling_and_hvo_blend_savings_cents=4400000,
        )
        self.assertFalse(pool_409.allowed)
        self.assertEqual(pool_409.http_status, 409)
        self.assertEqual(pool_409.settled_biobunker_cents, 25100000)
        self.assertEqual(pool_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["marine_biobunker_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("marine-biobunker-c14-sandbox", demo_zh)

    def test_heavy_rigging_air_ride_mri_fab_tool_shocklog_g_force_mandate_vs_concealed_transit_damage_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_heavy_rigging_air_ride_shocklog_policy,
        )

        # 1. Verified internal-frame ShockLog <=1.5G + cryo cold-head <=4.5 psi + air-caster load OK -> 200 OK ($135,000)
        commit_ok = evaluate_heavy_rigging_air_ride_shocklog_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rigging_cents, 13500000)

        # 2. Concealed internal ShockLog >1.5G drop shock despite intact outer crate -> 403 blocked in 11ms
        shk_403 = evaluate_heavy_rigging_air_ride_shocklog_policy(
            internal_shocklog_1_5g_and_tilt_verified=False,
        )
        self.assertFalse(shk_403.allowed)
        self.assertEqual(shk_403.http_status, 403)
        self.assertEqual(
            shk_403.rigging_lane,
            "CONCEALED_INTERNAL_SHOCKLOG_EXCURSION_CLEAN_RECEIPT_BLOCKED",
        )

        # 3. Superconducting MRI cryocooler power loss or cleanroom raised-floor overload -> 422 blocked in 14ms
        cry_422 = evaluate_heavy_rigging_air_ride_shocklog_policy(
            cryo_cold_head_and_air_caster_floor_load_passed=False,
        )
        self.assertFalse(cry_422.allowed)
        self.assertEqual(cry_422.http_status, 422)
        self.assertEqual(
            cry_422.rigging_lane,
            "MRI_CRYO_QUENCH_PRESSURE_OR_CLEANROOM_FLOOR_OVERLOAD_BLOCKED",
        )

        # 4. Web IQ detects unwaived Carmack $0.50/lb liability trap or missing concealed re-calibration rider -> 451 blocked in 295ms
        ins_451 = evaluate_heavy_rigging_air_ride_shocklog_policy(
            webiq_all_risk_declared_value_and_permit_clean=False,
        )
        self.assertFalse(ins_451.allowed)
        self.assertEqual(ins_451.http_status, 451)

        # 5. Web IQ batches shared cleanroom gantry & wire-rope skid return saving $24,000 ($111,000 net) -> 409 Confirm
        gnt_409 = evaluate_heavy_rigging_air_ride_shocklog_policy(
            shared_cleanroom_gantry_and_skid_return_savings_cents=2400000,
        )
        self.assertFalse(gnt_409.allowed)
        self.assertEqual(gnt_409.http_status, 409)
        self.assertEqual(gnt_409.settled_rigging_cents, 11100000)
        self.assertEqual(gnt_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["heavy_rigging_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("heavy-rigging-shocklog-sandbox", demo_zh)

    def test_power_transformer_lpt_sfra_dga_acetylene_impact_mandate_vs_winding_shift_energization_blast_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_power_transformer_lpt_sfra_policy,
        )

        # 1. Verified site-vs-FAT SFRA rho >=0.995 + 72h DGA C2H2 == 0.0 ppm -> 200 OK ($450,000)
        commit_ok = evaluate_power_transformer_lpt_sfra_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_lpt_cents, 45000000)

        # 2. Transit winding buckling (SFRA rho <0.995) or nitrogen pressure moisture ingress -> 403 blocked in 11ms
        sfr_403 = evaluate_power_transformer_lpt_sfra_policy(
            site_vs_fat_sfra_and_n2_dewpoint_verified=False,
        )
        self.assertFalse(sfr_403.allowed)
        self.assertEqual(sfr_403.http_status, 403)
        self.assertEqual(
            sfr_403.lpt_lane,
            "TRANSIT_WINDING_BUCKLING_SFRA_DRIFT_OR_N2_MOISTURE_BLOCKED",
        )

        # 3. Post-72h soak DGA detects trace Acetylene (C2H2 >0 ppm) or PD >100 pC -> 422 blocked in 14ms
        dga_422 = evaluate_power_transformer_lpt_sfra_policy(
            energization_72h_dga_zero_acetylene_passed=False,
        )
        self.assertFalse(dga_422.allowed)
        self.assertEqual(dga_422.http_status, 422)
        self.assertEqual(
            dga_422.lpt_lane,
            "POST_72H_DGA_ACETYLENE_INTERNAL_ARCING_OR_PD_BREACH_BLOCKED",
        )

        # 4. Web IQ detects uncompensated IEEE C57.120 excess no-load core loss -> 451 blocked in 295ms
        llec_451 = evaluate_power_transformer_lpt_sfra_policy(
            webiq_ieee_c57_loss_capitalization_and_oil_clean=False,
        )
        self.assertFalse(llec_451.allowed)
        self.assertEqual(llec_451.http_status, 451)

        # 5. Web IQ applies Natural Ester FR3 deluge-wall waiver & +15% overload saving $62,000 ($388,000 net) -> 409 Confirm
        fr3_409 = evaluate_power_transformer_lpt_sfra_policy(
            natural_ester_fr3_fire_wall_and_overload_savings_cents=6200000,
        )
        self.assertFalse(fr3_409.allowed)
        self.assertEqual(fr3_409.http_status, 409)
        self.assertEqual(fr3_409.settled_lpt_cents, 38800000)
        self.assertEqual(fr3_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["power_transformer_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("power-transformer-sfra-sandbox", demo_zh)

    def test_timber_sawmill_3d_laser_log_scaling_eudr_polygon_mandate_vs_bark_void_overscaling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_timber_sawmill_3d_log_scaling_policy,
        )

        # 1. Verified 3D laser under-bark net JAS volume + zero heart-rot + EUDR polygon -> 200 OK ($175,000)
        commit_ok = evaluate_timber_sawmill_3d_log_scaling_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_timber_cents, 17500000)

        # 2. Manual caliper over-bark scaling or wax-concealed hollow heart-rot -> 403 blocked in 11ms
        brk_403 = evaluate_timber_sawmill_3d_log_scaling_policy(
            laser_under_bark_and_heart_rot_deducted=False,
        )
        self.assertFalse(brk_403.allowed)
        self.assertEqual(brk_403.http_status, 403)
        self.assertEqual(
            brk_403.timber_lane,
            "OVER_BARK_MANUAL_SCALING_OR_HOLLOW_HEART_ROT_INFLATION_BLOCKED",
        )

        # 3. Fungal blue-stain (>2%) or missing ISPM-15 pine-nematode fumigation -> 422 blocked in 14ms
        stn_422 = evaluate_timber_sawmill_3d_log_scaling_policy(
            sapstain_blue_stain_and_ispm15_passed=False,
        )
        self.assertFalse(stn_422.allowed)
        self.assertEqual(stn_422.http_status, 422)
        self.assertEqual(
            stn_422.timber_lane,
            "FUNGAL_BLUE_STAIN_DISCOLORATION_OR_PINE_NEMATODE_BREACH_BLOCKED",
        )

        # 4. Web IQ detects missing EUDR >4ha GeoJSON polygon or post-2020 deforestation overlap -> 451 blocked in 295ms
        eudr_451 = evaluate_timber_sawmill_3d_log_scaling_policy(
            webiq_eudr_polygon_and_fsc_coc_clean=False,
        )
        self.assertFalse(eudr_451.allowed)
        self.assertEqual(eudr_451.http_status, 451)

        # 5. Web IQ links 3D log scan to CNC Curve-Sawing (+8.5% yield) & bark pellet offtake saving $27,500 ($147,500 net) -> 409 Confirm
        crv_409 = evaluate_timber_sawmill_3d_log_scaling_policy(
            curve_sawing_yield_and_biomass_pellet_savings_cents=2750000,
        )
        self.assertFalse(crv_409.allowed)
        self.assertEqual(crv_409.http_status, 409)
        self.assertEqual(crv_409.settled_timber_cents, 14750000)
        self.assertEqual(crv_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["timber_scaling_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("timber-3d-scaling-sandbox", demo_zh)

    def test_geothermal_egs_drilling_enthalpy_wellhead_seismicity_mandate_vs_footage_short_circuit_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_geothermal_egs_drilling_enthalpy_policy,
        )

        # 1. Verified 30-day enthalpy >=1,650 kJ/kg + net >=8.0 MWe + tracer >=120h + TLS <=2.0 -> 200 OK ($380,000)
        commit_ok = evaluate_geothermal_egs_drilling_enthalpy_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_geothermal_cents, 38000000)

        # 2. Footage-only claim on tight hole or enthalpy < 1,650 kJ/kg -> 403 blocked in 12ms
        ent_403 = evaluate_geothermal_egs_drilling_enthalpy_policy(
            wellhead_enthalpy_and_mwe_verified=False,
        )
        self.assertFalse(ent_403.allowed)
        self.assertEqual(ent_403.http_status, 403)
        self.assertEqual(
            ent_403.geothermal_lane,
            "SUB_COMMERCIAL_ENTHALPY_OR_FOOTAGE_BLOCKED",
        )

        # 3. 36h cold-water thermal short-circuit (<120h) or NCG > 1.5 wt% -> 422 blocked in 15ms
        trc_422 = evaluate_geothermal_egs_drilling_enthalpy_policy(
            interwell_tracer_residence_and_ncg_passed=False,
        )
        self.assertFalse(trc_422.allowed)
        self.assertEqual(trc_422.http_status, 422)
        self.assertEqual(
            trc_422.geothermal_lane,
            "THERMAL_SHORT_CIRCUIT_OR_HIGH_NCG_SCALING_BLOCKED",
        )

        # 4. Web IQ detects induced seismicity ML > 2.0 breaching TLS Red Zone -> 451 blocked in 295ms
        tls_451 = evaluate_geothermal_egs_drilling_enthalpy_policy(
            webiq_seismic_tls_and_uic_permit_clean=False,
        )
        self.assertFalse(tls_451.allowed)
        self.assertEqual(tls_451.http_status, 451)

        # 5. Web IQ routes 75°C lithium-rich brine to DLE skid saving $52,000 ($328,000 net) -> 409 Confirm
        dle_409 = evaluate_geothermal_egs_drilling_enthalpy_policy(
            dle_lithium_brine_valorization_savings_cents=5200000,
        )
        self.assertFalse(dle_409.allowed)
        self.assertEqual(dle_409.http_status, 409)
        self.assertEqual(dle_409.settled_geothermal_cents, 32800000)
        self.assertEqual(dle_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["geothermal_egs_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("geothermal-egs-enthalpy-sandbox", demo_zh)

    def test_subsea_hvdc_cable_laying_rov_burial_depth_das_strain_mandate_vs_shallow_exposure_anchor_strike_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_subsea_hvdc_cable_laying_policy,
        )

        # 1. Verified ROV DoL >=1.5m + zero free-span + BOTDR strain <=1,500 microstrain -> 200 OK ($420,000)
        commit_ok = evaluate_subsea_hvdc_cable_laying_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_subsea_cable_cents, 42000000)

        # 2. Plow skip leaving DoL < 1.5m or seabed free-span exposure -> 403 blocked in 12ms
        dol_403 = evaluate_subsea_hvdc_cable_laying_policy(
            rov_tss440_burial_depth_and_freespan_verified=False,
        )
        self.assertFalse(dol_403.allowed)
        self.assertEqual(dol_403.http_status, 403)
        self.assertEqual(
            dol_403.subsea_cable_lane,
            "SHALLOW_BURIAL_DEPTH_OR_FREE_SPAN_EXPOSURE_BLOCKED",
        )

        # 3. Stern chute over-bend (<3.5m MBR) or BOTDR strain > 1,500 microstrain -> 422 blocked in 15ms
        mbr_422 = evaluate_subsea_hvdc_cable_laying_policy(
            botdr_strain_mbr_and_hv_soak_passed=False,
        )
        self.assertFalse(mbr_422.allowed)
        self.assertEqual(mbr_422.http_status, 422)
        self.assertEqual(
            mbr_422.subsea_cable_lane,
            "MBR_OVERBEND_STRAIN_OR_HV_SOAK_FAILURE_BLOCKED",
        )

        # 4. Web IQ detects missing UXO ALARP sign-off or unpublished NtM protection zone -> 451 blocked in 295ms
        uxo_451 = evaluate_subsea_hvdc_cable_laying_policy(
            webiq_uxo_alarp_and_ntm_chart_clean=False,
        )
        self.assertFalse(uxo_451.allowed)
        self.assertEqual(uxo_451.http_status, 451)

        # 5. Web IQ substitutes Fallpipe Rock Placement over 120m bedrock outcrop deducting $58,000 ($362,000 net) -> 409 Confirm
        rck_409 = evaluate_subsea_hvdc_cable_laying_policy(
            rock_placement_berm_deduction_savings_cents=5800000,
        )
        self.assertFalse(rck_409.allowed)
        self.assertEqual(rck_409.http_status, 409)
        self.assertEqual(rck_409.settled_subsea_cable_cents, 36200000)
        self.assertEqual(rck_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["subsea_cable_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("subsea-hvdc-cable-sandbox", demo_zh)

    def test_industrial_steam_as_a_service_dryness_fraction_ultrasonic_trap_mandate_vs_wet_steam_mass_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_industrial_steam_dryness_trap_policy,
        )

        # 1. Verified steam dryness x >=0.97 + zero trap blow-through + pure condensate -> 200 OK ($155,000)
        commit_ok = evaluate_industrial_steam_dryness_trap_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_steam_cents, 15500000)

        # 2. Wet steam liquid carryover (x = 0.82 < 0.97) billed as gross mass -> 403 blocked in 11ms
        wet_403 = evaluate_industrial_steam_dryness_trap_policy(
            steam_dryness_fraction_and_net_gj_verified=False,
        )
        self.assertFalse(wet_403.allowed)
        self.assertEqual(wet_403.http_status, 403)
        self.assertEqual(
            wet_403.steam_lane,
            "WET_STEAM_LIQUID_CARRYOVER_OVERBILLING_BLOCKED",
        )

        # 3. 40 kHz failed-open trap blow-through or condensate conductivity > 10 uS/cm -> 422 blocked in 14ms
        trp_422 = evaluate_industrial_steam_dryness_trap_policy(
            ultrasonic_trap_and_condensate_purity_passed=False,
        )
        self.assertFalse(trp_422.allowed)
        self.assertEqual(trp_422.http_status, 422)
        self.assertEqual(
            trp_422.steam_lane,
            "STEAM_TRAP_BLOW_THROUGH_OR_CONDENSATE_CONTAMINATION_BLOCKED",
        )

        # 4. Web IQ detects expired boiler safety cert or fake biomass carbon factor -> 451 blocked in 290ms
        ets_451 = evaluate_industrial_steam_dryness_trap_policy(
            webiq_boiler_safety_and_carbon_factor_clean=False,
        )
        self.assertFalse(ets_451.allowed)
        self.assertEqual(ets_451.http_status, 451)

        # 5. Web IQ dispatches MVR compressor to upgrade 0.15 MPa flash steam saving $24,800 ($130,200 net) -> 409 Confirm
        mvr_409 = evaluate_industrial_steam_dryness_trap_policy(
            mvr_flash_steam_recompression_savings_cents=2480000,
        )
        self.assertFalse(mvr_409.allowed)
        self.assertEqual(mvr_409.http_status, 409)
        self.assertEqual(mvr_409.settled_steam_cents, 13020000)
        self.assertEqual(mvr_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["industrial_steam_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("industrial-steam-dryness-sandbox", demo_zh)

    def test_potash_phosphate_fertilizer_k2o_cadmium_caking_mandate_vs_dolomite_filler_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_potash_phosphate_fertilizer_policy,
        )

        # 1. Verified conveyor LIBS K2O >=60% + water-soluble P2O5 + crush >=35N + Cd <=20 -> 200 OK ($260,000)
        commit_ok = evaluate_potash_phosphate_fertilizer_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_fertilizer_cents, 26000000)

        # 2. Dolomite filler adulteration (K2O < 60%) or low water-soluble P2O5 -> 403 blocked in 11ms
        grd_403 = evaluate_potash_phosphate_fertilizer_policy(
            libs_icp_nutrient_grade_verified=False,
        )
        self.assertFalse(grd_403.allowed)
        self.assertEqual(grd_403.http_status, 403)
        self.assertEqual(
            grd_403.fertilizer_lane,
            "NUTRIENT_GRADE_DEFICIT_OR_FILLER_ADULTERATION_BLOCKED",
        )

        # 3. Ocean-transit hygroscopic hold caking or granule crush < 35N -> 422 blocked in 14ms
        cak_422 = evaluate_potash_phosphate_fertilizer_policy(
            anti_caking_moisture_and_crush_strength_passed=False,
        )
        self.assertFalse(cak_422.allowed)
        self.assertEqual(cak_422.http_status, 422)
        self.assertEqual(
            cak_422.fertilizer_lane,
            "HYGROSCOPIC_CAKING_OR_GRANULE_CRUSH_FAILURE_BLOCKED",
        )

        # 4. Web IQ detects cadmium Cd > 20 mg/kg P2O5 or sanctioned potash origin -> 451 blocked in 290ms
        cdm_451 = evaluate_potash_phosphate_fertilizer_policy(
            webiq_cadmium_cap_and_origin_sanction_clean=False,
        )
        self.assertFalse(cdm_451.allowed)
        self.assertEqual(cdm_451.http_status, 451)

        # 5. Web IQ routes bulk MOP + DAP to port Bulk-Blending tower saving $34,000 ($226,000 net) -> 409 Confirm
        bbl_409 = evaluate_potash_phosphate_fertilizer_policy(
            port_bulk_blending_soil_formula_savings_cents=3400000,
        )
        self.assertFalse(bbl_409.allowed)
        self.assertEqual(bbl_409.http_status, 409)
        self.assertEqual(bbl_409.settled_fertilizer_cents, 22600000)
        self.assertEqual(bbl_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["potash_fertilizer_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("potash-phosphate-fertilizer-sandbox", demo_zh)

    def test_airport_ground_handling_sgha_gpu_pca_delay_code_mandate_vs_apu_burn_turnaround_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_airport_ground_handling_sgha_policy,
        )

        # 1. Verified GPU/PCA hookup <=3 min + honest delay codes + active ISAGO -> 200 OK ($92,000)
        commit_ok = evaluate_airport_ground_handling_sgha_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_sgha_cents, 9200000)

        # 2. Late GPU/PCA hookup forcing APU fuel burn -> 403 blocked in 11ms
        gpu_403 = evaluate_airport_ground_handling_sgha_policy(
            gpu_pca_hookup_and_apu_off_verified=False,
        )
        self.assertFalse(gpu_403.allowed)
        self.assertEqual(gpu_403.http_status, 403)
        self.assertEqual(
            gpu_403.sgha_lane,
            "GPU_PCA_HOOKUP_FAILURE_OR_APU_FUEL_BURN_BLOCKED",
        )

        # 3. Ramp equipment delay (Code 32/35) misattributed to ATC Code 81 -> 422 blocked in 14ms
        dly_422 = evaluate_airport_ground_handling_sgha_policy(
            turnaround_vision_delay_code_honest=False,
        )
        self.assertFalse(dly_422.allowed)
        self.assertEqual(dly_422.http_status, 422)
        self.assertEqual(
            dly_422.sgha_lane,
            "RAMP_HANDLING_DELAY_CODE_MISATTRIBUTION_BLOCKED",
        )

        # 4. Web IQ detects expired IATA ISAGO cert or GSE proximity breach -> 451 blocked in 285ms
        isg_451 = evaluate_airport_ground_handling_sgha_policy(
            webiq_isago_audit_and_gse_proximity_clean=False,
        )
        self.assertFalse(isg_451.allowed)
        self.assertEqual(isg_451.http_status, 451)

        # 5. Web IQ applies TaxiBot green-taxi & baggage SLA deduction saving $14,200 ($77,800 net) -> 409 Confirm
        txb_409 = evaluate_airport_ground_handling_sgha_policy(
            taxibot_green_taxi_and_sla_deduction_savings_cents=1420000,
        )
        self.assertFalse(txb_409.allowed)
        self.assertEqual(txb_409.http_status, 409)
        self.assertEqual(txb_409.settled_sgha_cents, 7780000)
        self.assertEqual(txb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["airport_sgha_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("airport-ground-handling-sandbox", demo_zh)

    def test_semiconductor_electronic_specialty_gas_nf3_wf6_crds_moisture_heel_mandate_vs_etch_drift_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_semiconductor_esg_specialty_gas_policy,
        )

        # 1. Verified inline CRDS H2O <=10 ppb + zero HF + heel credited + cylinder valid -> 200 OK ($210,000)
        commit_ok = evaluate_semiconductor_esg_specialty_gas_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_esg_gas_cents, 21000000)

        # 2. Valve moisture ingress (180 ppb > 10 ppb) forming HF acid hydrolysis -> 403 blocked in 11ms
        h2o_403 = evaluate_semiconductor_esg_specialty_gas_policy(
            crds_sub_ppb_moisture_and_hf_verified=False,
        )
        self.assertFalse(h2o_403.allowed)
        self.assertEqual(h2o_403.http_status, 403)
        self.assertEqual(
            h2o_403.esg_gas_lane,
            "SUB_PPB_MOISTURE_OR_ACID_HYDROLYSIS_BREACH_BLOCKED",
        )

        # 3. Uncredited 12% returned cylinder heel or trace metal particles > 1 ppt -> 422 blocked in 14ms
        hel_422 = evaluate_semiconductor_esg_specialty_gas_policy(
            load_cell_heel_credit_and_metal_purity_passed=False,
        )
        self.assertFalse(hel_422.allowed)
        self.assertEqual(hel_422.http_status, 422)
        self.assertEqual(
            hel_422.esg_gas_lane,
            "CYLINDER_HEEL_UNCREDITED_OR_METAL_PARTICLE_BLOCKED",
        )

        # 4. Web IQ detects expired Y-ton cylinder ultrasonic test or EU F-Gas breach -> 451 blocked in 290ms
        cyl_451 = evaluate_semiconductor_esg_specialty_gas_policy(
            webiq_cylinder_hydrotest_and_fgas_clean=False,
        )
        self.assertFalse(cyl_451.allowed)
        self.assertEqual(cyl_451.http_status, 451)

        # 5. Web IQ applies 12% heel rebate + sub-fab exhaust Xe/Kr recovery saving $29,400 ($180,600 net) -> 409 Confirm
        rec_409 = evaluate_semiconductor_esg_specialty_gas_policy(
            heel_credit_and_exhaust_xenon_recovery_savings_cents=2940000,
        )
        self.assertFalse(rec_409.allowed)
        self.assertEqual(rec_409.http_status, 409)
        self.assertEqual(rec_409.settled_esg_gas_cents, 18060000)
        self.assertEqual(rec_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["semiconductor_esg_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("semiconductor-esg-gas-sandbox", demo_zh)

    def test_district_cooling_chilled_water_btu_low_delta_t_mandate_vs_volumetric_flow_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_district_cooling_chilled_water_policy,
        )

        # 1. Verified supply <=6.0°C + paired Pt1000 BTU + return Delta-T >=8.0°C -> 200 OK ($135,000)
        commit_ok = evaluate_district_cooling_chilled_water_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cooling_cents, 13500000)

        # 2. Warm supply (>6.0°C) or unpaired RTD zero-drift -> 403 blocked in 11ms
        tmp_403 = evaluate_district_cooling_chilled_water_policy(
            paired_pt1000_and_supply_temp_verified=False,
        )
        self.assertFalse(tmp_403.allowed)
        self.assertEqual(tmp_403.http_status, 403)
        self.assertEqual(
            tmp_403.cooling_lane,
            "WARM_SUPPLY_TEMP_OR_UNPAIRED_BTU_DRIFT_BLOCKED",
        )

        # 3. 3-way bypass or PHE fouling causing Low-Delta-T Syndrome (<8.0°C) -> 422 blocked in 14ms
        dlt_422 = evaluate_district_cooling_chilled_water_policy(
            return_delta_t_and_picv_balance_passed=False,
        )
        self.assertFalse(dlt_422.allowed)
        self.assertEqual(dlt_422.http_status, 422)
        self.assertEqual(
            dlt_422.cooling_lane,
            "LOW_DELTA_T_BYPASS_OR_FOULING_PENALTY_BLOCKED",
        )

        # 4. Web IQ detects cooling-tower Legionella > 1,000 CFU/L or refrigerant leak -> 451 blocked in 285ms
        leg_451 = evaluate_district_cooling_chilled_water_policy(
            webiq_legionella_ashrae188_and_refrigerant_clean=False,
        )
        self.assertFalse(leg_451.allowed)
        self.assertEqual(leg_451.http_status, 451)

        # 5. Web IQ dispatches off-peak TES tank & wet-bulb economizer saving $21,600 ($113,400 net) -> 409 Confirm
        tes_409 = evaluate_district_cooling_chilled_water_policy(
            tes_thermal_storage_and_free_cooling_savings_cents=2160000,
        )
        self.assertFalse(tes_409.allowed)
        self.assertEqual(tes_409.http_status, 409)
        self.assertEqual(tes_409.settled_cooling_cents, 11340000)
        self.assertEqual(tes_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["district_cooling_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("district-cooling-delta-t-sandbox", demo_zh)

    def test_offshore_wind_wtiv_jackup_spudcan_preload_rpd_mandate_vs_punch_through_standby_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_offshore_wtiv_jackup_charter_policy,
        )

        # 1. Verified spudcan preload >=110% + RPD <=0.5 deg + honest crane/wind logs -> 200 OK ($480,000)
        commit_ok = evaluate_offshore_wtiv_jackup_charter_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_wtiv_cents, 48000000)

        # 2. Incomplete spudcan preload holding or leg RPD > 0.5 deg -> 403 blocked in 12ms
        spd_403 = evaluate_offshore_wtiv_jackup_charter_policy(
            spudcan_preload_and_rpd_verified=False,
        )
        self.assertFalse(spd_403.allowed)
        self.assertEqual(spd_403.http_status, 403)
        self.assertEqual(
            spd_403.wtiv_lane,
            "SPUDCAN_PRELOAD_SHORTFALL_OR_RPD_SKEW_BLOCKED",
        )

        # 3. 130m wind <=10 m/s while crane/jacking fault disguised as weather standby -> 422 blocked in 15ms
        crn_422 = evaluate_offshore_wtiv_jackup_charter_policy(
            boom_tip_wind_and_crane_plc_honest=False,
        )
        self.assertFalse(crn_422.allowed)
        self.assertEqual(crn_422.http_status, 422)
        self.assertEqual(
            crn_422.wtiv_lane,
            "CRANE_JACKING_BREAKDOWN_DISGUISED_AS_WIND_STANDBY_BLOCKED",
        )

        # 4. Web IQ detects missing WTG site-specific CPT MWS CoA or footprint overlap -> 451 blocked in 290ms
        mws_451 = evaluate_offshore_wtiv_jackup_charter_policy(
            webiq_mws_cpt_and_footprint_clearance_clean=False,
        )
        self.assertFalse(mws_451.allowed)
        self.assertEqual(mws_451.http_status, 451)

        # 5. Web IQ dispatches DP2 Feeder Barge for offshore component transfer saving $64,000 ($416,000 net) -> 409 Confirm
        fdr_409 = evaluate_offshore_wtiv_jackup_charter_policy(
            feeder_barge_offshore_transfer_savings_cents=6400000,
        )
        self.assertFalse(fdr_409.allowed)
        self.assertEqual(fdr_409.http_status, 409)
        self.assertEqual(fdr_409.settled_wtiv_cents, 41600000)
        self.assertEqual(fdr_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["offshore_wtiv_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("offshore-wtiv-jackup-sandbox", demo_zh)

    def test_cleanroom_ffu_ulpa_iso14644_pao_scan_amc_outgassing_mandate_vs_blind_filter_swap_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cleanroom_ffu_ulpa_filtration_policy,
        )

        # 1. Verified in-situ ISO 14644-3 scan <=0.01% + zero-boron ePTFE + FM 4920 valid -> 200 OK ($165,000)
        commit_ok = evaluate_cleanroom_ffu_ulpa_filtration_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cleanroom_cents, 16500000)

        # 2. Unseated silicone gel-seal bypass leak (>0.01% penetration) -> 403 blocked in 11ms
        lek_403 = evaluate_cleanroom_ffu_ulpa_filtration_policy(
            iso14644_scan_leak_and_velocity_verified=False,
        )
        self.assertFalse(lek_403.allowed)
        self.assertEqual(lek_403.http_status, 403)
        self.assertEqual(
            lek_403.cleanroom_lane,
            "GEL_SEAL_BYPASS_LEAK_OR_AIRFLOW_NONUNIFORMITY_BLOCKED",
        )

        # 3. Borosilicate fiberglass boron outgassing or premature calendar swap (<180 Pa) -> 422 blocked in 14ms
        brn_422 = evaluate_cleanroom_ffu_ulpa_filtration_policy(
            ptfe_zero_boron_and_terminal_dp_passed=False,
        )
        self.assertFalse(brn_422.allowed)
        self.assertEqual(brn_422.http_status, 422)
        self.assertEqual(
            brn_422.cleanroom_lane,
            "BORON_AMC_OUTGASSING_OR_PREMATURE_SWAP_BLOCKED",
        )

        # 4. Web IQ detects missing FM 4920 fire rating or EU GMP Annex 1 monitoring gap -> 451 blocked in 285ms
        gmp_451 = evaluate_cleanroom_ffu_ulpa_filtration_policy(
            webiq_fm4920_fire_and_gmp_annex1_clean=False,
        )
        self.assertFalse(gmp_451.allowed)
        self.assertEqual(gmp_451.http_status, 451)

        # 5. Web IQ applies DP condition-based swap & EC-fan setback saving $26,400 ($138,600 net) -> 409 Confirm
        cbd_409 = evaluate_cleanroom_ffu_ulpa_filtration_policy(
            dp_condition_based_swap_and_ec_fan_savings_cents=2640000,
        )
        self.assertFalse(cbd_409.allowed)
        self.assertEqual(cbd_409.http_status, 409)
        self.assertEqual(cbd_409.settled_cleanroom_cents, 13860000)
        self.assertEqual(cbd_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cleanroom_ffu_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cleanroom-ffu-ulpa-sandbox", demo_zh)

    def test_precious_metal_catalyst_pt_pd_ir_refining_tolling_fire_assay_mandate_vs_wet_lot_shrinkage_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_precious_metal_catalyst_tolling_policy,
        )

        # 1. Verified witnessed LOI + Fire-Assay split <=0.03% + CO dispersion >=65% -> 200 OK ($340,000)
        commit_ok = evaluate_precious_metal_catalyst_tolling_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_catalyst_cents, 34000000)

        # 2. Refiner inflates burn-off LOI shrinkage or assay split > 0.03 wt% -> 403 blocked in 12ms
        loi_403 = evaluate_precious_metal_catalyst_tolling_policy(
            witnessed_loi_and_fire_assay_split_verified=False,
        )
        self.assertFalse(loi_403.allowed)
        self.assertEqual(loi_403.http_status, 403)
        self.assertEqual(
            loi_403.catalyst_lane,
            "LOI_SHRINKAGE_INFLATION_OR_ASSAY_SPLIT_BLOCKED",
        )

        # 3. Sintered fresh catalyst failing CO chemisorption dispersion (<65%) -> 422 blocked in 15ms
        dsp_422 = evaluate_precious_metal_catalyst_tolling_policy(
            co_chemisorption_dispersion_and_recovery_passed=False,
        )
        self.assertFalse(dsp_422.allowed)
        self.assertEqual(dsp_422.http_status, 422)
        self.assertEqual(
            dsp_422.catalyst_lane,
            "LOW_METAL_DISPERSION_OR_REFINING_RECOVERY_BLOCKED",
        )

        # 4. Web IQ detects missing Basel PIC manifest or non-LPPM sponge source -> 451 blocked in 290ms
        bsl_451 = evaluate_precious_metal_catalyst_tolling_policy(
            webiq_basel_hazmat_and_lppm_good_delivery_clean=False,
        )
        self.assertFalse(bsl_451.allowed)
        self.assertEqual(bsl_451.http_status, 451)

        # 5. Web IQ executes Loco Zurich PGM Metal-Pool closed-loop transfer saving $56,000 ($284,000 net) -> 409 Confirm
        pol_409 = evaluate_precious_metal_catalyst_tolling_policy(
            pgm_metal_pool_closed_loop_tolling_savings_cents=5600000,
        )
        self.assertFalse(pol_409.allowed)
        self.assertEqual(pol_409.http_status, 409)
        self.assertEqual(pol_409.settled_catalyst_cents, 28400000)
        self.assertEqual(pol_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["precious_catalyst_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("precious-metal-catalyst-sandbox", demo_zh)

    def test_automated_cold_storage_asrs_dewpoint_frost_shuttle_throughput_mandate_vs_pallet_slot_freeze_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_automated_cold_storage_asrs_policy,
        )

        # 1. Verified airlock dew-point <=-35°C + FEM 9.851 throughput >=45 pallets/h + O2 <=15% -> 200 OK ($145,000)
        commit_ok = evaluate_automated_cold_storage_asrs_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cold_asrs_cents, 14500000)

        # 2. Desiccant rotor off raising dew-point > -35°C (frost blindness) -> 403 blocked in 11ms
        dew_403 = evaluate_automated_cold_storage_asrs_policy(
            airlock_dewpoint_and_top_rack_temp_verified=False,
        )
        self.assertFalse(dew_403.allowed)
        self.assertEqual(dew_403.http_status, 403)
        self.assertEqual(
            dew_403.cold_asrs_lane,
            "AIRLOCK_DEWPOINT_FROST_OR_THERMAL_STRATIFICATION_BLOCKED",
        )

        # 3. Stacker-crane throughput < 45 pallets/h or bogus re-palletizing fee -> 422 blocked in 14ms
        crn_422 = evaluate_automated_cold_storage_asrs_policy(
            fem9851_dual_command_throughput_and_contour_passed=False,
        )
        self.assertFalse(crn_422.allowed)
        self.assertEqual(crn_422.http_status, 422)
        self.assertEqual(
            crn_422.cold_asrs_lane,
            "STACKER_CRANE_THROUGHPUT_BREACH_OR_PALLET_FEE_BLOCKED",
        )

        # 4. Web IQ detects offline VdS 3527 hypoxic fire system or ammonia leak -> 451 blocked in 285ms
        hyp_451 = evaluate_automated_cold_storage_asrs_policy(
            webiq_hypoxic_fire_and_ammonia_safety_clean=False,
        )
        self.assertFalse(hyp_451.allowed)
        self.assertEqual(hyp_451.http_status, 451)

        # 5. Web IQ dispatches off-peak -29°C Thermal-Flywheel pre-cooling saving $23,200 ($121,800 net) -> 409 Confirm
        fly_409 = evaluate_automated_cold_storage_asrs_policy(
            supercooling_thermal_flywheel_dr_savings_cents=2320000,
        )
        self.assertFalse(fly_409.allowed)
        self.assertEqual(fly_409.http_status, 409)
        self.assertEqual(fly_409.settled_cold_asrs_cents, 12180000)
        self.assertEqual(fly_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["automated_cold_asrs_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("automated-cold-asrs-sandbox", demo_zh)

    def test_rail_ballast_tamping_grinding_track_geometry_tqi_mandate_vs_pass_kilometer_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_rail_ballast_tamping_grinding_policy,
        )

        # 1. Verified post-100k-ton EN 13848 TQI <=1.5mm + zero RCF/bluing + CWR SFT safe -> 200 OK ($220,000)
        commit_ok = evaluate_rail_ballast_tamping_grinding_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rail_tamping_cents, 22000000)

        # 2. Shallow tamping / skipped DGS causing post-tonnage rebound (sigma > 1.5mm) -> 403 blocked in 12ms
        tqi_403 = evaluate_rail_ballast_tamping_grinding_policy(
            post_tonnage_tqi_and_dgs_stabilization_verified=False,
        )
        self.assertFalse(tqi_403.allowed)
        self.assertEqual(tqi_403.http_status, 403)
        self.assertEqual(
            tqi_403.rail_tamping_lane,
            "POST_TONNAGE_TQI_REBOUND_OR_SHALLOW_TAMPING_BLOCKED",
        )

        # 3. Residual RCF cracks (>0.1mm) or martensitic grind bluing -> 422 blocked in 15ms
        rcf_422 = evaluate_rail_ballast_tamping_grinding_policy(
            eddy_current_rcf_and_no_bluing_passed=False,
        )
        self.assertFalse(rcf_422.allowed)
        self.assertEqual(rcf_422.http_status, 422)
        self.assertEqual(
            rcf_422.rail_tamping_lane,
            "RCF_HEAD_CHECK_RESIDUAL_OR_GRIND_BLUING_BLOCKED",
        )

        # 4. Web IQ detects CWR rail temp > SFT + 15°C or possession overrun -> 451 blocked in 285ms
        cwr_451 = evaluate_rail_ballast_tamping_grinding_policy(
            webiq_cwr_rail_temp_and_possession_clean=False,
        )
        self.assertFalse(cwr_451.allowed)
        self.assertEqual(cwr_451.http_status, 451)

        # 5. Web IQ switches tangent track to 80 km/h Preventive High-Speed Grinding saving $35,200 ($184,800 net) -> 409 Confirm
        hsg_409 = evaluate_rail_ballast_tamping_grinding_policy(
            predictive_high_speed_grinding_savings_cents=3520000,
        )
        self.assertFalse(hsg_409.allowed)
        self.assertEqual(hsg_409.http_status, 409)
        self.assertEqual(hsg_409.settled_rail_tamping_cents, 18480000)
        self.assertEqual(hsg_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["rail_tamping_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("rail-ballast-tamping-sandbox", demo_zh)

    def test_rng_biomethane_pipeline_injection_siloxane_gc_ims_d3_rin_mandate_vs_turbine_silica_glazing_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_rng_biomethane_pipeline_injection_policy,
        )

        # 1. Verified GC-IMS siloxanes <=0.1 mg/Nm3 + O2 <=0.2% + authentic D3 RIN -> 200 OK ($195,000)
        commit_ok = evaluate_rng_biomethane_pipeline_injection_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rng_cents, 19500000)

        # 2. Siloxane breakthrough (>0.1 mg/Nm3) risking turbine/SOFC silica glazing -> 403 blocked in 11ms
        sil_403 = evaluate_rng_biomethane_pipeline_injection_policy(
            gc_ims_siloxane_and_wobbe_verified=False,
        )
        self.assertFalse(sil_403.allowed)
        self.assertEqual(sil_403.http_status, 403)
        self.assertEqual(
            sil_403.rng_lane,
            "SILOXANE_BREAKTHROUGH_OR_WOBBE_INDEX_BLOCKED",
        )

        # 3. Wellfield air intrusion (O2 > 0.2%) or H2S > 4 ppmv triggering Slam-Shut diversion -> 422 blocked in 14ms
        oxy_422 = evaluate_rng_biomethane_pipeline_injection_policy(
            paramagnetic_o2_and_h2s_slam_shut_passed=False,
        )
        self.assertFalse(oxy_422.allowed)
        self.assertEqual(oxy_422.http_status, 422)
        self.assertEqual(
            oxy_422.rng_lane,
            "OXYGEN_H2S_CORROSION_SLAM_SHUT_DIVERSION_BLOCKED",
        )

        # 4. Web IQ detects unverified EPA D3 RIN QAP or fake negative-CI pathway -> 451 blocked in 285ms
        rin_451 = evaluate_rng_biomethane_pipeline_injection_policy(
            webiq_epa_d3_rin_qap_and_lcfs_clean=False,
        )
        self.assertFalse(rin_451.allowed)
        self.assertEqual(rin_451.http_status, 451)

        # 5. Web IQ monetizes stripped biogenic CO2 tail-gas for e-methanol synthesis saving $31,200 ($163,800 net) -> 409 Confirm
        co2_409 = evaluate_rng_biomethane_pipeline_injection_policy(
            biogenic_co2_methanol_offtake_savings_cents=3120000,
        )
        self.assertFalse(co2_409.allowed)
        self.assertEqual(co2_409.http_status, 409)
        self.assertEqual(co2_409.settled_rng_cents, 16380000)
        self.assertEqual(co2_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["rng_biomethane_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("rng-biomethane-pipeline-sandbox", demo_zh)

    def test_subsea_pipeline_cathodic_protection_ag_agcl_potential_anode_mandate_vs_passivation_embrittlement_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_subsea_cathodic_protection_policy,
        )

        # 1. Verified DNV capacity >=2,000 Ah/kg + ROV [-1,050, -800] mV + OSPAR Cd-free -> 200 OK ($185,000)
        commit_ok = evaluate_subsea_cathodic_protection_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_subsea_cp_cents, 18500000)

        # 2. Low Indium (<0.015%) causing anode passivation (<2,000 Ah/kg) -> 403 blocked in 11ms
        pas_403 = evaluate_subsea_cathodic_protection_policy(
            dnv_amp_hour_capacity_and_indium_verified=False,
        )
        self.assertFalse(pas_403.allowed)
        self.assertEqual(pas_403.http_status, 403)
        self.assertEqual(
            pas_403.subsea_cp_lane,
            "ANODE_PASSIVATION_OR_LOW_AMP_HOUR_CAPACITY_BLOCKED",
        )

        # 3. Underprotection (>-800 mV) or overprotection HISC (<-1,050 mV) -> 422 blocked in 14ms
        emb_422 = evaluate_subsea_cathodic_protection_policy(
            rov_ag_agcl_potential_window_passed=False,
        )
        self.assertFalse(emb_422.allowed)
        self.assertEqual(emb_422.http_status, 422)
        self.assertEqual(
            emb_422.subsea_cp_lane,
            "UNDERPROTECTION_OR_HYDROGEN_EMBRITTLEMENT_BLOCKED",
        )

        # 4. Web IQ detects OSPAR toxic cadmium breach or steel-core shrinkage debonding -> 451 blocked in 285ms
        cad_451 = evaluate_subsea_cathodic_protection_policy(
            webiq_ospar_cadmium_free_and_core_bond_clean=False,
        )
        self.assertFalse(cad_451.allowed)
        self.assertEqual(cad_451.http_status, 451)

        # 5. Web IQ replaces diver welding with FiGS-targeted ROV clamp-on anode sleds saving $29,600 ($155,400 net) -> 409 Confirm
        sld_409 = evaluate_subsea_cathodic_protection_policy(
            rov_targeted_anode_sled_retrofit_savings_cents=2960000,
        )
        self.assertFalse(sld_409.allowed)
        self.assertEqual(sld_409.http_status, 409)
        self.assertEqual(sld_409.settled_subsea_cp_cents, 15540000)
        self.assertEqual(sld_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["subsea_cp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("subsea-cathodic-protection-sandbox", demo_zh)

    def test_swro_seawater_desalination_isobaric_erd_boron_sdi_mandate_vs_fouling_power_passthrough_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_swro_seawater_desalination_policy,
        )

        # 1. Verified normalized SEC <=3.0 kWh/m3 + boron <=0.5 mg/L + balanced LSI -> 200 OK ($230,000)
        commit_ok = evaluate_swro_seawater_desalination_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_swro_cents, 23000000)

        # 2. Fouled membranes / worn PX rotor spiking SEC > 3.0 kWh/m3 -> 403 blocked in 11ms
        sec_403 = evaluate_swro_seawater_desalination_policy(
            isobaric_px_sec_and_sdi_verified=False,
        )
        self.assertFalse(sec_403.allowed)
        self.assertEqual(sec_403.http_status, 403)
        self.assertEqual(
            sec_403.swro_lane,
            "SPECIFIC_ENERGY_CAP_OR_PX_MIXING_BREACH_BLOCKED",
        )

        # 3. Skipped second-pass NaOH leaving boron > 0.5 mg/L or corrosive negative LSI -> 422 blocked in 14ms
        brn_422 = evaluate_swro_seawater_desalination_policy(
            permeate_boron_and_lsi_remineralization_passed=False,
        )
        self.assertFalse(brn_422.allowed)
        self.assertEqual(brn_422.http_status, 422)
        self.assertEqual(
            brn_422.swro_lane,
            "BORON_TOXICITY_OR_CORROSIVE_LSI_WATER_BLOCKED",
        )

        # 4. Web IQ detects marine outfall salinity plume > +2.0 psu or residual chlorine -> 451 blocked in 285ms
        out_451 = evaluate_swro_seawater_desalination_policy(
            webiq_brine_outfall_plume_and_dechlorination_clean=False,
        )
        self.assertFalse(out_451.allowed)
        self.assertEqual(out_451.http_status, 451)

        # 5. Web IQ pipes 70 g/L brine to Chlor-Alkali plant & shifts RO load to off-peak saving $36,800 ($193,200 net) -> 409 Confirm
        brn_409 = evaluate_swro_seawater_desalination_policy(
            chlor_alkali_brine_and_tou_storage_savings_cents=3680000,
        )
        self.assertFalse(brn_409.allowed)
        self.assertEqual(brn_409.http_status, 409)
        self.assertEqual(brn_409.settled_swro_cents, 19320000)
        self.assertEqual(brn_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["swro_desalination_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("swro-seawater-desalination-sandbox", demo_zh)

    def test_elevator_escalator_traction_rope_mrt_brake_torque_mandate_vs_phantom_pm_visit_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_elevator_escalator_mro_policy,
        )

        # 1. Verified hoistway dwell >=45m + dual-brake symmetry + ISO 4309 MRT clean -> 200 OK ($115,000)
        commit_ok = evaluate_elevator_escalator_mro_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_elevator_cents, 11500000)

        # 2. 5-minute lobby tap-and-go phantom PM visit or brake stroke asymmetry -> 403 blocked in 11ms
        pmv_403 = evaluate_elevator_escalator_mro_policy(
            car_top_pit_dwell_and_brake_stroke_verified=False,
        )
        self.assertFalse(pmv_403.allowed)
        self.assertEqual(pmv_403.http_status, 403)
        self.assertEqual(
            pmv_403.elevator_lane,
            "PHANTOM_PM_VISIT_OR_BRAKE_STROKE_ASYMMETRY_BLOCKED",
        )

        # 3. OEM trip-counter lockout extortion on healthy belt (LMA = 0.8%) -> 422 blocked in 14ms
        mrt_422 = evaluate_elevator_escalator_mro_policy(
            iso4309_mrt_rope_and_no_counter_extortion_passed=False,
        )
        self.assertFalse(mrt_422.allowed)
        self.assertEqual(mrt_422.http_status, 422)
        self.assertEqual(
            mrt_422.elevator_lane,
            "ROPE_MRT_DEFECT_UNRESOLVED_OR_COUNTER_LOCK_BLOCKED",
        )

        # 4. Web IQ detects active door-lock jumper bypass or overdue Cat-5 test -> 451 blocked in 285ms
        jmp_451 = evaluate_elevator_escalator_mro_policy(
            webiq_tsg_governor_and_zero_door_jumper_clean=False,
        )
        self.assertFalse(jmp_451.allowed)
        self.assertEqual(jmp_451.http_status, 451)

        # 5. Web IQ extends healthy belt via MRT & credits 4-quadrant regen drive saving $18,400 ($96,600 net) -> 409 Confirm
        reg_409 = evaluate_elevator_escalator_mro_policy(
            regenerative_drive_and_mrt_life_extension_savings_cents=1840000,
        )
        self.assertFalse(reg_409.allowed)
        self.assertEqual(reg_409.http_status, 409)
        self.assertEqual(reg_409.settled_elevator_cents, 9660000)
        self.assertEqual(reg_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["elevator_mro_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("elevator-escalator-mro-sandbox", demo_zh)

    def test_automated_container_terminal_sts_spreader_twistlock_gmph_mandate_vs_eccentric_berth_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_automated_container_terminal_sts_policy,
        )

        # 1. Verified net GMPH >=32 Moves/h + 4-twistlock eccentricity <=10% + SOLAS VGM clean -> 200 OK ($250,000)
        commit_ok = evaluate_automated_container_terminal_sts_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_terminal_sts_cents, 25000000)

        # 2. AGV starvation dropping net GMPH < 32 or padded unproductive restows -> 403 blocked in 11ms
        gmp_403 = evaluate_automated_container_terminal_sts_policy(
            net_gmph_and_zero_unproductive_restow_verified=False,
        )
        self.assertFalse(gmp_403.allowed)
        self.assertEqual(gmp_403.http_status, 403)
        self.assertEqual(
            gmp_403.terminal_sts_lane,
            "CRANE_GMPH_SLA_BREACH_OR_UNPRODUCTIVE_RESTOW_BLOCKED",
        )

        # 3. Spreader 4-twistlock load-pins detect eccentricity > 10% or fatigued pin -> 422 blocked in 14ms
        tws_422 = evaluate_automated_container_terminal_sts_policy(
            twistlock_eccentricity_and_ndt_cycle_passed=False,
        )
        self.assertFalse(tws_422.allowed)
        self.assertEqual(tws_422.http_status, 422)
        self.assertEqual(
            tws_422.terminal_sts_lane,
            "TWISTLOCK_ECCENTRIC_OVERLOAD_OR_FATIGUE_CRACK_BLOCKED",
        )

        # 4. Web IQ detects SOLAS VGM weight discrepancy (>5%) or IMDG segregation breach -> 451 blocked in 285ms
        vgm_451 = evaluate_automated_container_terminal_sts_policy(
            webiq_solas_vgm_and_imdg_segregation_clean=False,
        )
        self.assertFalse(vgm_451.allowed)
        self.assertEqual(vgm_451.http_status, 451)

        # 5. Web IQ deploys Tandem-Lift spreaders to depart 8h early & slow-steam saving $40,000 ($210,000 net) -> 409 Confirm
        tdm_409 = evaluate_automated_container_terminal_sts_policy(
            tandem_lift_early_departure_bunker_savings_cents=4000000,
        )
        self.assertFalse(tdm_409.allowed)
        self.assertEqual(tdm_409.http_status, 409)
        self.assertEqual(tdm_409.settled_terminal_sts_cents, 21000000)
        self.assertEqual(tdm_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["container_sts_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("automated-container-sts-sandbox", demo_zh)

    def test_pulp_paper_kraft_admt_moisture_kappa_viscosity_mandate_vs_wet_bale_degradation_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_pulp_paper_kraft_admt_policy,
        )

        # 1. Verified microwave ADMT + CED viscosity >=750 mL/g + ECF/EUDR clean -> 200 OK ($205,000)
        commit_ok = evaluate_pulp_paper_kraft_admt_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_pulp_cents, 20500000)

        # 2. Wet-core bales (>10% moisture) billed on unadjusted gross weight -> 403 blocked in 11ms
        wet_403 = evaluate_pulp_paper_kraft_admt_policy(
            microwave_admt_dryness_verified=False,
        )
        self.assertFalse(wet_403.allowed)
        self.assertEqual(wet_403.http_status, 403)
        self.assertEqual(
            wet_403.pulp_lane,
            "EXCESS_BALE_MOISTURE_UNADJUSTED_ADMT_BLOCKED",
        )

        # 3. Over-bleaching degrading CED intrinsic viscosity (<750 mL/g) -> 422 blocked in 14ms
        vis_422 = evaluate_pulp_paper_kraft_admt_policy(
            ced_intrinsic_viscosity_and_dirt_passed=False,
        )
        self.assertFalse(vis_422.allowed)
        self.assertEqual(vis_422.http_status, 422)
        self.assertEqual(
            vis_422.pulp_lane,
            "CELLULOSE_VISCOSITY_DEGRADATION_OR_DIRT_SPECK_BLOCKED",
        )

        # 4. Web IQ detects elemental chlorine AOX breach or missing EUDR polygon -> 451 blocked in 285ms
        aox_451 = evaluate_pulp_paper_kraft_admt_policy(
            webiq_ecf_aox_and_eudr_polygon_clean=False,
        )
        self.assertFalse(aox_451.allowed)
        self.assertEqual(aox_451.http_status, 451)

        # 5. Web IQ switches to pumped Slush Pulp & credits Crude Tall Oil saving $32,800 ($172,200 net) -> 409 Confirm
        sls_409 = evaluate_pulp_paper_kraft_admt_policy(
            slush_pulp_pipeline_and_tall_oil_savings_cents=3280000,
        )
        self.assertFalse(sls_409.allowed)
        self.assertEqual(sls_409.http_status, 409)
        self.assertEqual(sls_409.settled_pulp_cents, 17220000)
        self.assertEqual(sls_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["kraft_pulp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("kraft-pulp-admt-sandbox", demo_zh)

    def test_float_solar_glass_nis_heat_soak_laser_scanner_transmittance_mandate_vs_spontaneous_shatter_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_float_solar_glass_hst_policy,
        )

        # 1. Verified EN 14179-1 290°C HST + transmittance >=94.0% + roller wave <=0.05mm -> 200 OK ($170,000)
        commit_ok = evaluate_float_solar_glass_hst_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_glass_cents, 17000000)

        # 2. Skipped or shortchanged 290°C heat-soak cycle leaving un-detonated NiS stones -> 403 blocked in 11ms
        hst_403 = evaluate_float_solar_glass_hst_policy(
            en14179_heat_soak_and_laser_stone_verified=False,
        )
        self.assertFalse(hst_403.allowed)
        self.assertEqual(hst_403.http_status, 403)
        self.assertEqual(
            hst_403.glass_lane,
            "SKIPPED_HEAT_SOAK_NIS_STONE_OR_BUBBLE_DEFECT_BLOCKED",
        )

        # 3. High-iron tint dropping solar transmittance < 94.0% or roller-wave distortion -> 422 blocked in 14ms
        opt_422 = evaluate_float_solar_glass_hst_policy(
            ultra_clear_transmittance_and_roller_wave_passed=False,
        )
        self.assertFalse(opt_422.allowed)
        self.assertEqual(opt_422.http_status, 422)
        self.assertEqual(
            opt_422.glass_lane,
            "LOW_SOLAR_TRANSMITTANCE_OR_ROLLER_WAVE_DISTORTION_BLOCKED",
        )

        # 4. Web IQ detects under-filled IGU argon (<90%) or missing SGCC cert -> 451 blocked in 285ms
        arg_451 = evaluate_float_solar_glass_hst_policy(
            webiq_en1279_argon_and_sgcc_safety_clean=False,
        )
        self.assertFalse(arg_451.allowed)
        self.assertEqual(arg_451.http_status, 451)

        # 5. Web IQ returns 35% segregated ultra-clear cullet to float furnace saving $27,200 ($142,800 net) -> 409 Confirm
        cul_409 = evaluate_float_solar_glass_hst_policy(
            ultra_clear_cullet_furnace_return_savings_cents=2720000,
        )
        self.assertFalse(cul_409.allowed)
        self.assertEqual(cul_409.http_status, 409)
        self.assertEqual(cul_409.settled_glass_cents, 14280000)
        self.assertEqual(cul_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["float_glass_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("float-solar-glass-sandbox", demo_zh)

    def test_tire_rubber_mooney_viscosity_mdr_cure_eudr_polygon_mandate_vs_scorched_coagulum_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_tire_rubber_mooney_mdr_policy,
        )

        # 1. Verified arrival MDR ts2 >=4.5m + Mooney in window + dispersion >=95% -> 200 OK ($190,000)
        commit_ok = evaluate_tire_rubber_mooney_mdr_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rubber_cents, 19000000)

        # 2. In-transit thermal scorching (ts2 < 4.5 min) or Mooney viscosity spike -> 403 blocked in 11ms
        scr_403 = evaluate_tire_rubber_mooney_mdr_policy(
            arrival_mooney_and_mdr_scorch_verified=False,
        )
        self.assertFalse(scr_403.allowed)
        self.assertEqual(scr_403.http_status, 403)
        self.assertEqual(
            scr_403.rubber_lane,
            "PREMATURE_SCORCH_OR_MOONEY_VISCOSITY_DRIFT_BLOCKED",
        )

        # 3. Shortchanged Banbury mixing leaving dispersion < 95.0% -> 422 blocked in 14ms
        dsp_422 = evaluate_tire_rubber_mooney_mdr_policy(
            carbon_black_silica_dispersion_passed=False,
        )
        self.assertFalse(dsp_422.allowed)
        self.assertEqual(dsp_422.http_status, 422)
        self.assertEqual(
            dsp_422.rubber_lane,
            "CARBON_BLACK_SILICA_POOR_DISPERSION_AGGLOMERATE_BLOCKED",
        )

        # 4. Web IQ detects missing EUDR rubber plantation polygon or REACH PAH > 10 ppm -> 451 blocked in 285ms
        eud_451 = evaluate_tire_rubber_mooney_mdr_policy(
            webiq_eudr_rubber_polygon_and_pah_clean=False,
        )
        self.assertFalse(eud_451.allowed)
        self.assertEqual(eud_451.http_status, 451)

        # 5. Web IQ blends 25% ISCC pyrolysis rCB & adopts liquid-phase wet masterbatch saving $30,400 ($159,600 net) -> 409 Confirm
        rcb_409 = evaluate_tire_rubber_mooney_mdr_policy(
            recovered_carbon_black_and_wet_masterbatch_savings_cents=3040000,
        )
        self.assertFalse(rcb_409.allowed)
        self.assertEqual(rcb_409.http_status, 409)
        self.assertEqual(rcb_409.settled_rubber_cents, 15960000)
        self.assertEqual(rcb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["tire_rubber_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("tire-rubber-mooney-sandbox", demo_zh)

    def test_biopharma_cdmo_bioreactor_titer_hcp_endotoxin_mandate_vs_slot_reservation_batch_failure_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_biopharma_cdmo_bioreactor_policy,
        )

        # 1. Verified Raman titer >=5.0 g/L + HCP <=100 ppm + endotoxin <=0.1 EU/mg -> 200 OK ($390,000)
        commit_ok = evaluate_biopharma_cdmo_bioreactor_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cdmo_cents, 39000000)

        # 2. SUB bag pinhole contamination or DO drift crashing titer < 5.0 g/L -> 403 blocked in 12ms
        tit_403 = evaluate_biopharma_cdmo_bioreactor_policy(
            raman_titer_and_sterility_verified=False,
        )
        self.assertFalse(tit_403.allowed)
        self.assertEqual(tit_403.http_status, 403)
        self.assertEqual(
            tit_403.cdmo_lane,
            "LOW_BIOREACTOR_TITER_OR_MYCOPLASMA_CONTAMINATION_BLOCKED",
        )

        # 3. Over-cycled Protein-A resin leaving HCP > 100 ppm -> 422 blocked in 15ms
        hcp_422 = evaluate_biopharma_cdmo_bioreactor_policy(
            protein_a_hcp_endotoxin_and_sec_passed=False,
        )
        self.assertFalse(hcp_422.allowed)
        self.assertEqual(hcp_422.http_status, 422)
        self.assertEqual(
            hcp_422.cdmo_lane,
            "HOST_CELL_PROTEIN_OR_ENDOTOXIN_AGGREGATE_BLOCKED",
        )

        # 4. Web IQ detects 21 CFR Part 11 audit-trail deletion or active FDA OAI warning -> 451 blocked in 290ms
        fda_451 = evaluate_biopharma_cdmo_bioreactor_policy(
            webiq_part11_audit_trail_and_fda_oai_clean=False,
        )
        self.assertFalse(fda_451.allowed)
        self.assertEqual(fda_451.http_status, 451)

        # 5. Web IQ applies N-1 ATF perfusion & 3-column PCC chromatography saving $62,000 ($328,000 net) -> 409 Confirm
        pcc_409 = evaluate_biopharma_cdmo_bioreactor_policy(
            n1_perfusion_and_continuous_chromatography_savings_cents=6200000,
        )
        self.assertFalse(pcc_409.allowed)
        self.assertEqual(pcc_409.http_status, 409)
        self.assertEqual(pcc_409.settled_cdmo_cents, 32800000)
        self.assertEqual(pcc_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["biopharma_cdmo_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("biopharma-cdmo-bioreactor-sandbox", demo_zh)

    def test_salmon_aquaculture_ras_3d_biomass_fcr_geosmin_astaxanthin_mandate_vs_feed_waste_muddy_flavor_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_salmon_aquaculture_ras_policy,
        )

        # 1. Verified stereo-3D eFCR <=1.15 + fasted HOG + Geosmin <=10 ng/kg + SalmoFan >=26 -> 200 OK ($160,000)
        commit_ok = evaluate_salmon_aquaculture_ras_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_salmon_cents, 16000000)

        # 2. Pellet sinking waste (eFCR > 1.15) or unfasted gut weight -> 403 blocked in 11ms
        fcr_403 = evaluate_salmon_aquaculture_ras_policy(
            stereo_3d_efcr_and_fasting_gut_verified=False,
        )
        self.assertFalse(fcr_403.allowed)
        self.assertEqual(fcr_403.http_status, 403)
        self.assertEqual(
            fcr_403.salmon_lane,
            "FEED_CONVERSION_WASTE_OR_UNFASTED_GUT_WEIGHT_BLOCKED",
        )

        # 3. Unpurged RAS Geosmin (>10 ng/kg muddy flavor) or pale flesh (SalmoFan <26) -> 422 blocked in 14ms
        geo_422 = evaluate_salmon_aquaculture_ras_policy(
            gcms_geosmin_and_salmofan_color_passed=False,
        )
        self.assertFalse(geo_422.allowed)
        self.assertEqual(geo_422.http_status, 422)
        self.assertEqual(
            geo_422.salmon_lane,
            "GEOSMIN_MUDDY_OFF_FLAVOR_OR_PALE_FLESH_BLOCKED",
        )

        # 4. Web IQ detects BarentsWatch sea-lice breach (>0.2/fish) or missing ASC cert -> 451 blocked in 285ms
        lic_451 = evaluate_salmon_aquaculture_ras_policy(
            webiq_sea_lice_and_asc_marintrust_clean=False,
        )
        self.assertFalse(lic_451.allowed)
        self.assertEqual(lic_451.http_status, 451)

        # 5. Web IQ substitutes Schizochytrium algal oil & RAS sludge biogas CHP saving $25,600 ($134,400 net) -> 409 Confirm
        alg_409 = evaluate_salmon_aquaculture_ras_policy(
            algal_omega3_and_sludge_biogas_savings_cents=2560000,
        )
        self.assertFalse(alg_409.allowed)
        self.assertEqual(alg_409.http_status, 409)
        self.assertEqual(alg_409.settled_salmon_cents, 13440000)
        self.assertEqual(alg_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["salmon_aquaculture_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("salmon-aquaculture-ras-sandbox", demo_zh)

    def test_textile_dyeing_finishing_spectrophotometer_delta_e_zdhc_mrsl_mandate_vs_shade_lot_shrinkage_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_textile_dyeing_finishing_policy,
        )

        # 1. Verified inline CMC Delta-E <=0.8 + GSM shrinkage <=3.0% + fastness >=4.0 + ZDHC clean -> 200 OK ($145,000)
        commit_ok = evaluate_textile_dyeing_finishing_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_textile_cents, 14500000)

        # 2. Mid-roll shade drift (CMC Delta-E > 0.8) or side-to-center shading -> 403 blocked in 11ms
        shd_403 = evaluate_textile_dyeing_finishing_policy(
            inline_spectrophotometer_delta_e_verified=False,
        )
        self.assertFalse(shd_403.allowed)
        self.assertEqual(shd_403.http_status, 403)
        self.assertEqual(
            shd_403.textile_lane,
            "SHADE_VARIATION_DELTA_E_OR_SIDE_CENTER_SHADING_BLOCKED",
        )

        # 3. Stenter over-stretching inflating yardage & causing shrinkage > 3.0% -> 422 blocked in 14ms
        shr_422 = evaluate_textile_dyeing_finishing_policy(
            gsm_shrinkage_and_fastness_passed=False,
        )
        self.assertFalse(shr_422.allowed)
        self.assertEqual(shr_422.http_status, 422)
        self.assertEqual(
            shr_422.textile_lane,
            "EXCESS_FABRIC_SHRINKAGE_OR_POOR_COLOR_FASTNESS_BLOCKED",
        )

        # 4. Web IQ detects banned carcinogenic azo arylamines (>20 ppm) or revoked OEKO-TEX -> 451 blocked in 285ms
        azo_451 = evaluate_textile_dyeing_finishing_policy(
            webiq_zdhc_mrsl_and_oeko_tex_clean=False,
        )
        self.assertFalse(azo_451.allowed)
        self.assertEqual(azo_451.http_status, 451)

        # 5. Web IQ routes to Supercritical CO2 waterless dyeing & MVR heat recovery saving $23,200 ($121,800 net) -> 409 Confirm
        co2_409 = evaluate_textile_dyeing_finishing_policy(
            supercritical_co2_and_heat_recovery_savings_cents=2320000,
        )
        self.assertFalse(co2_409.allowed)
        self.assertEqual(co2_409.http_status, 409)
        self.assertEqual(co2_409.settled_textile_cents, 12180000)
        self.assertEqual(co2_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["textile_dyeing_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("textile-dyeing-finishing-sandbox", demo_zh)

    def test_flour_milling_bakery_farinograph_falling_number_don_mycotoxin_mandate_vs_sprouted_wheat_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_flour_milling_bakery_policy,
        )

        # 1. Verified Falling Number >=300s + Farinograph stability >=10 min + 14% moisture + DON <=0.75 ppm -> 200 OK ($135,000)
        commit_ok = evaluate_flour_milling_bakery_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_flour_cents, 13500000)

        # 2. Sprouted wheat alpha-amylase (FN < 300s) or weak gluten (<10 min) -> 403 blocked in 11ms
        fn_403 = evaluate_flour_milling_bakery_policy(
            falling_number_and_farinograph_stability_verified=False,
        )
        self.assertFalse(fn_403.allowed)
        self.assertEqual(fn_403.http_status, 403)
        self.assertEqual(
            fn_403.flour_lane,
            "SPROUTED_WHEAT_FALLING_NUMBER_OR_WEAK_GLUTEN_BLOCKED",
        )

        # 3. Over-tempered water weight (>14.0% unadjusted) or high bran ash (>0.55%) -> 422 blocked in 14ms
        mst_422 = evaluate_flour_milling_bakery_policy(
            moisture_14pct_dry_basis_and_ash_passed=False,
        )
        self.assertFalse(mst_422.allowed)
        self.assertEqual(mst_422.http_status, 422)
        self.assertEqual(
            mst_422.flour_lane,
            "EXCESS_TEMPERING_MOISTURE_OR_HIGH_BRAN_ASH_BLOCKED",
        )

        # 4. Web IQ detects Fusarium DON vomitoxin (>0.75 ppm) or banned ADA bleach -> 451 blocked in 285ms
        don_451 = evaluate_flour_milling_bakery_policy(
            webiq_don_mycotoxin_and_clean_label_clean=False,
        )
        self.assertFalse(don_451.allowed)
        self.assertEqual(don_451.http_status, 451)

        # 5. Web IQ switches to bulk pneumatic tanker & fungal xylanase enzyme blend saving $21,600 ($113,400 net) -> 409 Confirm
        slb_409 = evaluate_flour_milling_bakery_policy(
            bulk_pneumatic_silo_and_enzyme_savings_cents=2160000,
        )
        self.assertFalse(slb_409.allowed)
        self.assertEqual(slb_409.http_status, 409)
        self.assertEqual(slb_409.settled_flour_cents, 11340000)
        self.assertEqual(slb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["flour_milling_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("flour-milling-bakery-sandbox", demo_zh)

    def test_high_speed_ai_server_pcb_ccl_tdr_impedance_backdrill_caf_mandate_vs_signal_loss_delamination_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_high_speed_ai_pcb_ccl_policy,
        )

        # 1. Verified Coupon TDR +-5% + X-Ray backdrill <=6 mil + Class 3 288C + clean IC -> 200 OK ($230,000)
        commit_ok = evaluate_high_speed_ai_pcb_ccl_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_pcb_cents, 23000000)

        # 2. TDR impedance drift (>+-5%) or X-Ray backdrill stub > 6.0 mil -> 403 blocked in 11ms
        tdr_403 = evaluate_high_speed_ai_pcb_ccl_policy(
            tdr_impedance_and_xray_backdrill_stub_verified=False,
        )
        self.assertFalse(tdr_403.allowed)
        self.assertEqual(tdr_403.http_status, 403)
        self.assertEqual(
            tdr_403.pcb_lane,
            "TDR_IMPEDANCE_MISMATCH_OR_BACKDRILL_STUB_BLOCKED",
        )

        # 3. IPC Class 3 288C thermal delamination or hole-wall copper < 25 um -> 422 blocked in 14ms
        thm_422 = evaluate_high_speed_ai_pcb_ccl_policy(
            ipc_class3_thermal_stress_and_plating_passed=False,
        )
        self.assertFalse(thm_422.allowed)
        self.assertEqual(thm_422.http_status, 422)
        self.assertEqual(
            thm_422.pcb_lane,
            "THERMAL_STRESS_DELAMINATION_OR_PLATING_VOID_BLOCKED",
        )

        # 4. Web IQ detects unapproved CCL glass/resin swap or halide CAF breach -> 451 blocked in 285ms
        caf_451 = evaluate_high_speed_ai_pcb_ccl_policy(
            webiq_ccl_lot_and_ionic_caf_cleanliness_clean=False,
        )
        self.assertFalse(caf_451.allowed)
        self.assertEqual(caf_451.http_status, 451)

        # 5. Web IQ applies signal/power hybrid stackup & etchant Cu recovery saving $36,800 ($193,200 net) -> 409 Confirm
        hyb_409 = evaluate_high_speed_ai_pcb_ccl_policy(
            hybrid_stackup_and_etchant_copper_savings_cents=3680000,
        )
        self.assertFalse(hyb_409.allowed)
        self.assertEqual(hyb_409.http_status, 409)
        self.assertEqual(hyb_409.settled_pcb_cents, 19320000)
        self.assertEqual(hyb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["high_speed_pcb_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("high-speed-ai-pcb-sandbox", demo_zh)

    def test_metallurgical_coking_coal_csr_vitrinite_reflectance_gieseler_mandate_vs_blend_fraud_furnace_choking_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_metallurgical_coking_coal_policy,
        )

        # 1. Verified unimodal vitrinite Ro + CSR >=65% + Gieseler >=800 ddpm + low alkali -> 200 OK ($340,000)
        commit_ok = evaluate_metallurgical_coking_coal_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_coking_cents, 34000000)

        # 2. Bimodal vitrinite reflectance blend fraud or CSR < 65% -> 403 blocked in 12ms
        csr_403 = evaluate_metallurgical_coking_coal_policy(
            unimodal_vitrinite_ro_and_csr_verified=False,
        )
        self.assertFalse(csr_403.allowed)
        self.assertEqual(csr_403.http_status, 403)
        self.assertEqual(
            csr_403.coking_lane,
            "BIMODAL_VITRINITE_BLEND_FRAUD_OR_LOW_CSR_BLOCKED",
        )

        # 3. Stockpile oxidation collapsing Gieseler fluidity (<800 ddpm) or wet-quench water -> 422 blocked in 15ms
        flu_422 = evaluate_metallurgical_coking_coal_policy(
            gieseler_fluidity_and_dry_basis_passed=False,
        )
        self.assertFalse(flu_422.allowed)
        self.assertEqual(flu_422.http_status, 422)
        self.assertEqual(
            flu_422.coking_lane,
            "OXIDIZED_GIESELER_FLUIDITY_OR_QUENCH_WATER_BLOCKED",
        )

        # 4. Web IQ detects excess ash alkali (K2O+Na2O > 0.25%) or high phosphorus -> 451 blocked in 290ms
        alk_451 = evaluate_metallurgical_coking_coal_policy(
            webiq_alkali_phosphorus_and_origin_clean=False,
        )
        self.assertFalse(alk_451.allowed)
        self.assertEqual(alk_451.http_status, 451)

        # 5. Web IQ applies CDQ dry-quench steam power & COG PSA hydrogen saving $54,400 ($285,600 net) -> 409 Confirm
        cdq_409 = evaluate_metallurgical_coking_coal_policy(
            cdq_dry_quench_power_and_cog_hydrogen_savings_cents=5440000,
        )
        self.assertFalse(cdq_409.allowed)
        self.assertEqual(cdq_409.http_status, 409)
        self.assertEqual(cdq_409.settled_coking_cents, 28560000)
        self.assertEqual(cdq_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["coking_coal_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("metallurgical-coking-coal-sandbox", demo_zh)

    def test_battery_grade_lithium_carbonate_lfp_cathode_magnetic_impurity_icp_mandate_vs_dendrite_short_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_battery_lithium_lfp_cathode_policy,
        )

        # 1. Verified ICP-MS magnetic <=50 ppb + 0.1C >=158 mAh/g + moisture <=300 ppm + clean DBP -> 200 OK ($380,000)
        commit_ok = evaluate_battery_lithium_lfp_cathode_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_battery_lfp_cents, 38000000)

        # 2. Magnetic particles (Fe+Cr+Ni+Zn > 50 ppb) or high-Na industrial grade fraud -> 403 blocked in 12ms
        mag_403 = evaluate_battery_lithium_lfp_cathode_policy(
            icp_ms_magnetic_impurity_and_purity_verified=False,
        )
        self.assertFalse(mag_403.allowed)
        self.assertEqual(mag_403.http_status, 403)
        self.assertEqual(
            mag_403.battery_lfp_lane,
            "MAGNETIC_PARTICLE_PPB_EXCEEDANCE_OR_SODIUM_IMPURITY_BLOCKED",
        )

        # 3. Low 0.1C specific capacity (<158 mAh/g) or Karl Fischer moisture > 300 ppm -> 422 blocked in 15ms
        cap_422 = evaluate_battery_lithium_lfp_cathode_policy(
            coin_cell_capacity_psd_d50_and_karl_fischer_passed=False,
        )
        self.assertFalse(cap_422.allowed)
        self.assertEqual(cap_422.http_status, 422)
        self.assertEqual(
            cap_422.battery_lfp_lane,
            "LOW_FIRST_CYCLE_CAPACITY_OR_KARL_FISCHER_MOISTURE_BLOCKED",
        )

        # 4. Web IQ detects missing EU Battery Passport LCA or fake recycled lithium -> 451 blocked in 290ms
        dbp_451 = evaluate_battery_lithium_lfp_cathode_policy(
            webiq_eu_battery_passport_and_feoc_traceability_clean=False,
        )
        self.assertFalse(dbp_451.allowed)
        self.assertEqual(dbp_451.http_status, 451)

        # 5. Web IQ applies closed-loop cathode scrap / black-mass tolling saving $60,800 ($319,200 net) -> 409 Confirm
        tol_409 = evaluate_battery_lithium_lfp_cathode_policy(
            lithium_hydroxide_mvr_and_black_mass_tolling_savings_cents=6080000,
        )
        self.assertFalse(tol_409.allowed)
        self.assertEqual(tol_409.http_status, 409)
        self.assertEqual(tol_409.settled_battery_lfp_cents, 31920000)
        self.assertEqual(tol_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["battery_lfp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("battery-lithium-lfp-sandbox", demo_zh)

    def test_corrugated_packaging_ect_box_compression_cobb_moisture_mandate_vs_recycled_liner_collapse_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_corrugated_packaging_ect_bct_policy,
        )

        # 1. Verified TAPPI ECT >=44 lb/in + BCT >=4,500 N + Cobb60 <=30 g/m2 + clean FSC -> 200 OK ($140,000)
        commit_ok = evaluate_corrugated_packaging_ect_bct_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_corrugated_cents, 14000000)

        # 2. Chalk-filler adulterated liner or crushed flutes dropping ECT < 44 lb/in -> 403 blocked in 11ms
        ect_403 = evaluate_corrugated_packaging_ect_bct_policy(
            tappi_ect_edge_crush_and_bct_verified=False,
        )
        self.assertFalse(ect_403.allowed)
        self.assertEqual(ect_403.http_status, 403)
        self.assertEqual(
            ect_403.corrugated_lane,
            "LOW_ECT_EDGE_CRUSH_OR_BCT_STACK_COLLAPSE_BLOCKED",
        )

        # 3. High Cobb60 water absorption (>30 g/m2) or starch pin-adhesion delamination -> 422 blocked in 14ms
        cob_422 = evaluate_corrugated_packaging_ect_bct_policy(
            iso535_cobb60_water_absorption_and_pin_adhesion_passed=False,
        )
        self.assertFalse(cob_422.allowed)
        self.assertEqual(cob_422.http_status, 422)
        self.assertEqual(
            cob_422.corrugated_lane,
            "HIGH_COBB_WATER_ABSORPTION_OR_PIN_ADHESION_DELAMINATION_BLOCKED",
        )

        # 4. Web IQ detects revoked FSC-CoC certificate or EU PPWR banned PFAS -> 451 blocked in 285ms
        fsc_451 = evaluate_corrugated_packaging_ect_bct_policy(
            webiq_fsc_coc_and_eu_ppwr_pfas_free_clean=False,
        )
        self.assertFalse(fsc_451.allowed)
        self.assertEqual(fsc_451.http_status, 451)

        # 5. Web IQ switches to Fanfold Box-on-Demand & closed-loop OCC bales saving $22,400 ($117,600 net) -> 409 Confirm
        bod_409 = evaluate_corrugated_packaging_ect_bct_policy(
            box_on_demand_right_sizing_and_occ_loop_savings_cents=2240000,
        )
        self.assertFalse(bod_409.allowed)
        self.assertEqual(bod_409.http_status, 409)
        self.assertEqual(bod_409.settled_corrugated_cents, 11760000)
        self.assertEqual(bod_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["corrugated_packaging_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("corrugated-packaging-ect-sandbox", demo_zh)

    def test_automotive_ahss_galvanized_coil_yield_gauge_xrf_coating_mandate_vs_head_tail_stamping_split_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_automotive_ahss_coil_policy,
        )

        # 1. Verified full-coil IMPOC yield <=+-35 MPa + XRF zinc >=60/60 + clean CBAM/IATF -> 200 OK ($275,000)
        commit_ok = evaluate_automotive_ahss_coil_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ahss_coil_cents, 27500000)

        # 2. Uncropped head/tail yield spike (>+-35 MPa) risking stamping split -> 403 blocked in 11ms
        yld_403 = evaluate_automotive_ahss_coil_policy(
            full_coil_impoc_yield_and_elongation_verified=False,
        )
        self.assertFalse(yld_403.allowed)
        self.assertEqual(yld_403.http_status, 403)
        self.assertEqual(
            yld_403.ahss_coil_lane,
            "COIL_HEAD_TAIL_YIELD_DRIFT_OR_ELONGATION_SPLIT_BLOCKED",
        )

        # 3. Skimmed XRF zinc coating (<60/60 g/m2), O5 dross or positive-gauge overbilling -> 422 blocked in 14ms
        znc_422 = evaluate_automotive_ahss_coil_policy(
            xrf_zinc_coating_and_theoretical_area_weight_passed=False,
        )
        self.assertFalse(znc_422.allowed)
        self.assertEqual(znc_422.http_status, 422)
        self.assertEqual(
            znc_422.ahss_coil_lane,
            "ZINC_COATING_UNDERWEIGHT_OR_SURFACE_DROSS_DEFECT_BLOCKED",
        )

        # 4. Web IQ detects fake CBAM H2-DRI green-steel EPD or expired IATF 16949 -> 451 blocked in 285ms
        cbm_451 = evaluate_automotive_ahss_coil_policy(
            webiq_cbam_green_steel_and_iatf16949_clean=False,
        )
        self.assertFalse(cbm_451.allowed)
        self.assertEqual(cbm_451.http_status, 451)

        # 5. Web IQ applies Tailor-Welded Blanks (TWB) & closed-loop prompt stamping scrap saving $44,000 ($231,000 net) -> 409 Confirm
        twb_409 = evaluate_automotive_ahss_coil_policy(
            tailor_welded_blank_and_prompt_scrap_loop_savings_cents=4400000,
        )
        self.assertFalse(twb_409.allowed)
        self.assertEqual(twb_409.http_status, 409)
        self.assertEqual(twb_409.settled_ahss_coil_cents, 23100000)
        self.assertEqual(twb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["automotive_ahss_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("automotive-ahss-coil-sandbox", demo_zh)

    def test_solar_polysilicon_topcon_wafer_minority_carrier_lifetime_ttv_mandate_vs_oxygen_ring_breakage_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_solar_polysilicon_topcon_wafer_policy,
        )

        # 1. Verified lifetime >=1,500 us + [Oi] <=12 ppma + TTV <=12 um + clean PPE2 -> 200 OK ($315,000)
        commit_ok = evaluate_solar_polysilicon_topcon_wafer_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_solar_wafer_cents, 31500000)

        # 2. Low minority-carrier lifetime (<1,500 us) or high oxygen ring -> 403 blocked in 12ms
        tau_403 = evaluate_solar_polysilicon_topcon_wafer_policy(
            minority_carrier_lifetime_and_ftir_oxygen_verified=False,
        )
        self.assertFalse(tau_403.allowed)
        self.assertEqual(tau_403.http_status, 403)
        self.assertEqual(
            tau_403.solar_wafer_lane,
            "LOW_MINORITY_CARRIER_LIFETIME_OR_OXYGEN_RING_DEFECT_BLOCKED",
        )

        # 3. Wedge slicing TTV (>12 um) or hidden PL microcracks -> 422 blocked in 15ms
        ttv_422 = evaluate_solar_polysilicon_topcon_wafer_policy(
            wafer_ttv_warp_and_pl_microcrack_passed=False,
        )
        self.assertFalse(ttv_422.allowed)
        self.assertEqual(ttv_422.http_status, 422)
        self.assertEqual(
            ttv_422.solar_wafer_lane,
            "WAFER_TTV_WARP_EXCEEDANCE_OR_PL_MICROCRACK_BLOCKED",
        )

        # 4. Web IQ detects French PPE2 carbon footprint breach or broken quartz lineage -> 451 blocked in 290ms
        ecs_451 = evaluate_solar_polysilicon_topcon_wafer_policy(
            webiq_ppe2_carbon_footprint_and_traceability_clean=False,
        )
        self.assertFalse(ecs_451.allowed)
        self.assertEqual(ecs_451.http_status, 451)

        # 5. Web IQ blends FBR granular polysilicon & credits ingot crown/tail tolling saving $50,400 ($264,600 net) -> 409 Confirm
        fbr_409 = evaluate_solar_polysilicon_topcon_wafer_policy(
            fbr_granular_polysilicon_and_ingot_scrap_tolling_savings_cents=5040000,
        )
        self.assertFalse(fbr_409.allowed)
        self.assertEqual(fbr_409.http_status, 409)
        self.assertEqual(fbr_409.settled_solar_wafer_cents, 26460000)
        self.assertEqual(fbr_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["solar_wafer_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("solar-topcon-wafer-sandbox", demo_zh)

    def test_cooling_tower_chiller_condenser_approach_coc_legionella_mandate_vs_chemical_drum_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cooling_tower_chiller_treatment_policy,
        )

        # 1. Verified condenser approach <=1.5C + PTSA + CoC >=6.0 + clean Legionella qPCR -> 200 OK ($150,000)
        commit_ok = evaluate_cooling_tower_chiller_treatment_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cooling_tower_cents, 15000000)

        # 2. Diluted chemical drums causing condenser scaling (approach > 1.5C) -> 403 blocked in 11ms
        app_403 = evaluate_cooling_tower_chiller_treatment_policy(
            condenser_approach_temp_and_ptsa_verified=False,
        )
        self.assertFalse(app_403.allowed)
        self.assertEqual(app_403.http_status, 403)
        self.assertEqual(
            app_403.cooling_tower_lane,
            "CONDENSER_APPROACH_SCALING_OR_PTSA_UNDERDOSE_BLOCKED",
        )

        # 3. Secret blowdown dumping (CoC < 6.0) or copper corrosion > 0.1 mpy -> 422 blocked in 14ms
        coc_422 = evaluate_cooling_tower_chiller_treatment_policy(
            cycles_of_concentration_and_lpr_corrosion_passed=False,
        )
        self.assertFalse(coc_422.allowed)
        self.assertEqual(coc_422.http_status, 422)
        self.assertEqual(
            coc_422.cooling_tower_lane,
            "BLOWDOWN_VALVE_WATER_WASTE_OR_CORROSION_RATE_BLOCKED",
        )

        # 4. Web IQ detects ASHRAE 188 Legionella qPCR breach or phosphate violation -> 451 blocked in 285ms
        leg_451 = evaluate_cooling_tower_chiller_treatment_policy(
            webiq_legionella_qpcr_and_zero_phosphate_clean=False,
        )
        self.assertFalse(leg_451.allowed)
        self.assertEqual(leg_451.http_status, 451)

        # 5. Web IQ routes AHU dehumidification condensate & electro-descaling saving $24,000 ($126,000 net) -> 409 Confirm
        ahu_409 = evaluate_cooling_tower_chiller_treatment_policy(
            ahu_condensate_recovery_and_electrochemical_savings_cents=2400000,
        )
        self.assertFalse(ahu_409.allowed)
        self.assertEqual(ahu_409.http_status, 409)
        self.assertEqual(ahu_409.settled_cooling_tower_cents, 12600000)
        self.assertEqual(ahu_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cooling_tower_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cooling-tower-treatment-sandbox", demo_zh)

    def test_offshore_wind_composite_blade_paut_cscan_dsc_cure_lps_mandate_vs_dry_spot_delamination_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_offshore_wind_composite_blade_policy,
        )

        # 1. Verified PAUT C-Scan zero dry-spot + DSC Tg >=75C + LPS <=20 mOhm + clean DNV -> 200 OK ($460,000)
        commit_ok = evaluate_offshore_wind_composite_blade_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_wind_blade_cents, 46000000)

        # 2. Spar-cap VARTM dry spot/wrinkle or shear-web bondline void (>1.5%) -> 403 blocked in 12ms
        ut_403 = evaluate_offshore_wind_composite_blade_policy(
            paut_cscan_spar_cap_and_web_bondline_verified=False,
        )
        self.assertFalse(ut_403.allowed)
        self.assertEqual(ut_403.http_status, 403)
        self.assertEqual(
            ut_403.wind_blade_lane,
            "SPAR_CAP_DRY_SPOT_OR_WEB_BONDLINE_VOID_BLOCKED",
        )

        # 3. Premature demolding under-cure (DSC Tg < 75C) or static moment imbalance -> 422 blocked in 15ms
        dsc_422 = evaluate_offshore_wind_composite_blade_policy(
            dsc_glass_transition_tg_and_mass_moment_passed=False,
        )
        self.assertFalse(dsc_422.allowed)
        self.assertEqual(dsc_422.http_status, 422)
        self.assertEqual(
            dsc_422.wind_blade_lane,
            "UNDERCURED_RESIN_LOW_TG_OR_MASS_MOMENT_IMBALANCE_BLOCKED",
        )

        # 4. Web IQ detects IEC 61400-24 LPS continuity breach (>20 mOhm) or missing DNV cert -> 451 blocked in 290ms
        lps_451 = evaluate_offshore_wind_composite_blade_policy(
            webiq_lps_lightning_continuity_and_dnv_cert_clean=False,
        )
        self.assertFalse(lps_451.allowed)
        self.assertEqual(lps_451.http_status, 451)

        # 5. Web IQ upgrades to cleavable recyclable epoxy & factory LEP shield saving $73,600 ($386,400 net) -> 409 Confirm
        rec_409 = evaluate_offshore_wind_composite_blade_policy(
            recyclable_resin_decommission_and_lep_shield_savings_cents=7360000,
        )
        self.assertFalse(rec_409.allowed)
        self.assertEqual(rec_409.http_status, 409)
        self.assertEqual(rec_409.settled_wind_blade_cents, 38640000)
        self.assertEqual(rec_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["wind_blade_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("offshore-wind-blade-sandbox", demo_zh)

    def test_aseptic_dairy_beverage_uht_f0_lethality_peroxide_atp_mandate_vs_bloated_pack_spoilage_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aseptic_dairy_uht_copack_policy,
        )

        # 1. Verified continuous F0 >=6.0 min + H2O2 <=0.5 ppm + incubated ATP <15 RLU -> 200 OK ($165,000)
        commit_ok = evaluate_aseptic_dairy_uht_copack_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_aseptic_uht_cents, 16500000)

        # 2. Holding-tube temperature dip (F0 < 6.0 min) or bypassed FDV diversion -> 403 blocked in 11ms
        f0_403 = evaluate_aseptic_dairy_uht_copack_policy(
            uht_f0_lethality_and_fdv_interlock_verified=False,
        )
        self.assertFalse(f0_403.allowed)
        self.assertEqual(f0_403.http_status, 403)
        self.assertEqual(
            f0_403.aseptic_uht_lane,
            "UHT_F0_LETHALITY_DROP_OR_FDV_BYPASS_BLOCKED",
        )

        # 3. Aseptic chamber pressure loss (<+15 Pa) or H2O2 residue > 0.5 ppm -> 422 blocked in 14ms
        h2o2_422 = evaluate_aseptic_dairy_uht_copack_policy(
            aseptic_overpressure_peroxide_and_seal_passed=False,
        )
        self.assertFalse(h2o2_422.allowed)
        self.assertEqual(h2o2_422.http_status, 422)
        self.assertEqual(
            h2o2_422.aseptic_uht_lane,
            "ASEPTIC_CHAMBER_PRESSURE_LOSS_OR_PEROXIDE_RESIDUE_BLOCKED",
        )

        # 4. Web IQ detects 7-day incubated ATP positivity (>=15 RLU) or Aflatoxin M1 breach -> 451 blocked in 285ms
        atp_451 = evaluate_aseptic_dairy_uht_copack_policy(
            webiq_atp_sterility_and_aflatoxin_m1_clean=False,
        )
        self.assertFalse(atp_451.allowed)
        self.assertEqual(atp_451.http_status, 451)

        # 5. Web IQ activates 92% UHT regenerative heat exchange & NF CIP caustic recovery saving $26,400 ($138,600 net) -> 409 Confirm
        reg_409 = evaluate_aseptic_dairy_uht_copack_policy(
            uht_regenerative_heat_and_cip_caustic_savings_cents=2640000,
        )
        self.assertFalse(reg_409.allowed)
        self.assertEqual(reg_409.http_status, 409)
        self.assertEqual(reg_409.settled_aseptic_uht_cents, 13860000)
        self.assertEqual(reg_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["aseptic_uht_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aseptic-dairy-uht-sandbox", demo_zh)

    def test_ev_hairpin_motor_magnet_wire_iacs_pdiv_corona_mandate_vs_inverter_insulation_breakdown_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ev_hairpin_magnet_wire_policy,
        )

        # 1. Verified 150C PDIV >=1,350 Vpk + O2 <=5 ppm + >=101.0% IACS + clean UL 1446 -> 200 OK ($325,000)
        commit_ok = evaluate_ev_hairpin_magnet_wire_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_magnet_wire_cents, 32500000)

        # 2. Thin R-corner enamel dropping 150C PDIV (<1,350 Vpk) or HV spark pinholes -> 403 blocked in 12ms
        pd_403 = evaluate_ev_hairpin_magnet_wire_policy(
            high_temp_pdiv_corona_and_zero_pinhole_verified=False,
        )
        self.assertFalse(pd_403.allowed)
        self.assertEqual(pd_403.http_status, 403)
        self.assertEqual(
            pd_403.magnet_wire_lane,
            "LOW_PDIV_CORONA_INCEPTION_OR_CORNER_ENAMEL_PINHOLE_BLOCKED",
        )

        # 3. High copper oxygen (O2 > 5 ppm) laser-weld porosity or 3D U-bend cracking -> 422 blocked in 15ms
        oxy_422 = evaluate_ev_hairpin_magnet_wire_policy(
            ofc_oxygen_ppm_iacs_and_hairpin_bend_passed=False,
        )
        self.assertFalse(oxy_422.allowed)
        self.assertEqual(oxy_422.http_status, 422)
        self.assertEqual(
            oxy_422.magnet_wire_lane,
            "HIGH_COPPER_OXYGEN_LASER_WELD_POROSITY_OR_BEND_CRACK_BLOCKED",
        )

        # 4. Web IQ detects missing UL 1446 ATF oil compatibility or Copper Mark breach -> 451 blocked in 290ms
        ul_451 = evaluate_ev_hairpin_magnet_wire_policy(
            webiq_ul1446_atf_oil_and_copper_mark_clean=False,
        )
        self.assertFalse(ul_451.allowed)
        self.assertEqual(ul_451.http_status, 451)

        # 5. Web IQ routes 12% hairpin TU1 offcuts to upcast tolling & foamed PI saving $52,000 ($273,000 net) -> 409 Confirm
        tol_409 = evaluate_ev_hairpin_magnet_wire_policy(
            hairpin_scrap_copper_tolling_and_foamed_pi_savings_cents=5200000,
        )
        self.assertFalse(tol_409.allowed)
        self.assertEqual(tol_409.http_status, 409)
        self.assertEqual(tol_409.settled_magnet_wire_cents, 27300000)
        self.assertEqual(tol_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["magnet_wire_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ev-hairpin-magnet-wire-sandbox", demo_zh)

    def test_aerospace_titanium_ti64_billet_triple_var_hard_alpha_ut_mandate_vs_inclusion_burst_overbilling_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aerospace_titanium_ti64_billet_policy,
        )

        # 1. Verified Triple-VAR + Class AA immersion UT zero #2 FBH + zero beta fleck -> 200 OK ($440,000)
        commit_ok = evaluate_aerospace_titanium_ti64_billet_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_titanium_billet_cents, 44000000)

        # 2. Type I hard-alpha (#2 FBH echo) or non-Triple-VAR melt -> 403 blocked in 12ms
        ut_403 = evaluate_aerospace_titanium_ti64_billet_policy(
            triple_var_and_multizone_immersion_ut_class_aa_verified=False,
        )
        self.assertFalse(ut_403.allowed)
        self.assertEqual(ut_403.http_status, 403)
        self.assertEqual(
            ut_403.titanium_billet_lane,
            "HARD_ALPHA_INCLUSION_OR_NON_TRIPLE_VAR_MELT_BLOCKED",
        )

        # 3. Vanadium-rich beta flecks or hydrogen > 80 ppm -> 422 blocked in 15ms
        bet_422 = evaluate_aerospace_titanium_ti64_billet_policy(
            zero_beta_fleck_and_beta_transus_hydrogen_passed=False,
        )
        self.assertFalse(bet_422.allowed)
        self.assertEqual(bet_422.http_status, 422)
        self.assertEqual(
            bet_422.titanium_billet_lane,
            "BETA_FLECK_SEGREGATION_OR_HYDROGEN_EMBRITTLEMENT_BLOCKED",
        )

        # 4. Web IQ detects lapsed Nadcap NDT accreditation or sanctioned sponge -> 451 blocked in 290ms
        nad_451 = evaluate_aerospace_titanium_ti64_billet_policy(
            webiq_nadcap_ndt_and_sponge_pedigree_clean=False,
        )
        self.assertFalse(nad_451.allowed)
        self.assertEqual(nad_451.http_status, 451)

        # 5. Web IQ routes 80% buy-to-fly CNC TC4 chips into EBCHM/PAM cold-hearth revert saving $70,400 ($369,600 net) -> 409 Confirm
        rev_409 = evaluate_aerospace_titanium_ti64_billet_policy(
            buy_to_fly_titanium_chip_hearth_revert_savings_cents=7040000,
        )
        self.assertFalse(rev_409.allowed)
        self.assertEqual(rev_409.http_status, 409)
        self.assertEqual(rev_409.settled_titanium_billet_cents, 36960000)
        self.assertEqual(rev_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["titanium_billet_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aerospace-titanium-ti64-sandbox", demo_zh)

    def test_municipal_drinking_water_uf_membrane_pdt_pac_alumina_mandate_vs_broken_fiber_turbidity_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_municipal_water_uf_pac_policy,
        )

        # 1. Verified EPA LT2 PDT <=0.01 bar/min + active Al2O3 >=10.5% + clean NSF 60 -> 200 OK ($180,000)
        commit_ok = evaluate_municipal_water_uf_pac_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_municipal_uf_cents, 18000000)

        # 2. Broken UF fibers (PDT > 0.01 bar/min, LRV < 4.0) or high TMP -> 403 blocked in 11ms
        pdt_403 = evaluate_municipal_water_uf_pac_policy(
            uf_pressure_decay_lrv4_and_tmp_verified=False,
        )
        self.assertFalse(pdt_403.allowed)
        self.assertEqual(pdt_403.http_status, 403)
        self.assertEqual(
            pdt_403.municipal_uf_lane,
            "UF_MEMBRANE_PRESSURE_DECAY_BREACH_OR_HIGH_TMP_BLOCKED",
        )

        # 3. Diluted liquid PAC (<10.5% Al2O3) or finished-water residual Al > 0.10 mg/L -> 422 blocked in 14ms
        pac_422 = evaluate_municipal_water_uf_pac_policy(
            pac_alumina_grade_and_residual_aluminum_passed=False,
        )
        self.assertFalse(pac_422.allowed)
        self.assertEqual(pac_422.http_status, 422)
        self.assertEqual(
            pac_422.municipal_uf_lane,
            "PAC_ALUMINA_DILUTION_OR_RESIDUAL_ALUMINUM_BLOCKED",
        )

        # 4. Web IQ detects industrial waste-acid heavy metals (As/Pb/Cd) or revoked NSF 60 -> 451 blocked in 285ms
        nsf_451 = evaluate_municipal_water_uf_pac_policy(
            webiq_nsf60_potable_and_heavy_metal_clean=False,
        )
        self.assertFalse(nsf_451.allowed)
        self.assertEqual(nsf_451.http_status, 451)

        # 5. Web IQ activates SCD streaming-current dosing & UF backwash seed recycle saving $28,800 ($151,200 net) -> 409 Confirm
        scd_409 = evaluate_municipal_water_uf_pac_policy(
            scd_streaming_current_and_backwash_seed_savings_cents=2880000,
        )
        self.assertFalse(scd_409.allowed)
        self.assertEqual(scd_409.http_status, 409)
        self.assertEqual(scd_409.settled_municipal_uf_cents, 15120000)
        self.assertEqual(scd_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["municipal_uf_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("municipal-water-uf-pac-sandbox", demo_zh)

    def test_commercial_greenhouse_hydroponic_par_dli_drain_ec_uv_mandate_vs_root_rot_tipburn_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_greenhouse_hydroponic_dli_ec_policy,
        )

        # 1. Verified canopy DLI >=25 mol/m2/d + PPE >=3.2 + slab EC 2.8-3.8 + clean UV qPCR -> 200 OK ($145,000)
        commit_ok = evaluate_greenhouse_hydroponic_dli_ec_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_greenhouse_cents, 14500000)

        # 2. Degraded LEDs dropping canopy DLI (<25 mol/m2/d) or PPE < 3.2 -> 403 blocked in 11ms
        dli_403 = evaluate_greenhouse_hydroponic_dli_ec_policy(
            canopy_par_dli_and_led_ppe_verified=False,
        )
        self.assertFalse(dli_403.allowed)
        self.assertEqual(dli_403.http_status, 403)
        self.assertEqual(
            dli_403.greenhouse_lane,
            "LOW_CANOPY_PAR_DLI_OR_INEFFICIENT_LED_PPE_BLOCKED",
        )

        # 3. Stonewool slab salinity spike (EC > 4.5 mS/cm) or pH emitter clog -> 422 blocked in 14ms
        ec_422 = evaluate_greenhouse_hydroponic_dli_ec_policy(
            root_zone_slab_ec_ph_and_vpd_passed=False,
        )
        self.assertFalse(ec_422.allowed)
        self.assertEqual(ec_422.http_status, 422)
        self.assertEqual(
            ec_422.greenhouse_lane,
            "ROOT_ZONE_EC_SALINITY_SPIKE_OR_PH_PRECIPITATION_BLOCKED",
        )

        # 4. Web IQ detects drain-water Pythium/ToBRFV qPCR positive or perchlorate breach -> 451 blocked in 285ms
        uv_451 = evaluate_greenhouse_hydroponic_dli_ec_policy(
            webiq_uv_pathogen_qpcr_and_perchlorate_clean=False,
        )
        self.assertFalse(uv_451.allowed)
        self.assertEqual(uv_451.http_status, 451)

        # 5. Web IQ activates CHP flue-gas 1,000 ppm CO2 enrichment & ISE drain reuse saving $23,200 ($121,800 net) -> 409 Confirm
        chp_409 = evaluate_greenhouse_hydroponic_dli_ec_policy(
            chp_co2_enrichment_and_drain_recycle_savings_cents=2320000,
        )
        self.assertFalse(chp_409.allowed)
        self.assertEqual(chp_409.http_status, 409)
        self.assertEqual(chp_409.settled_greenhouse_cents, 12180000)
        self.assertEqual(chp_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["greenhouse_hydroponic_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("greenhouse-hydroponic-sandbox", demo_zh)

    def test_hv_xlpe_underground_cable_ac_resonant_pd_eccentricity_mandate_vs_water_tree_joint_explosion_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_hv_xlpe_power_cable_policy,
        )

        # 1. Verified VCV X-ray eccentricity <=8% + hot-set <=100% + AC PD <=5 pC -> 200 OK ($395,000)
        commit_ok = evaluate_hv_xlpe_power_cable_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_hv_cable_cents, 39500000)

        # 2. VCV X-ray eccentricity (>8%) or under-crosslinked hot-set (>100%) -> 403 blocked in 12ms
        ecc_403 = evaluate_hv_xlpe_power_cable_policy(
            xray_eccentricity_and_hot_set_crosslink_verified=False,
        )
        self.assertFalse(ecc_403.allowed)
        self.assertEqual(ecc_403.http_status, 403)
        self.assertEqual(
            ecc_403.hv_cable_lane,
            "XLPE_INSULATION_ECCENTRICITY_OR_UNDER_CROSSLINK_HOTSET_BLOCKED",
        )

        # 3. AC resonant partial discharge (>5 pC), DC hipot or high conductor Rdc -> 422 blocked in 15ms
        pd_422 = evaluate_hv_xlpe_power_cable_policy(
            ac_resonant_partial_discharge_and_dc_resistance_passed=False,
        )
        self.assertFalse(pd_422.allowed)
        self.assertEqual(pd_422.http_status, 422)
        self.assertEqual(
            pd_422.hv_cable_lane,
            "PARTIAL_DISCHARGE_CORONA_SPIKE_OR_CONDUCTOR_DC_RESISTANCE_BLOCKED",
        )

        # 4. Web IQ detects missing KEMA PQ certificate or non-super-clean XLPE resin -> 451 blocked in 290ms
        kem_451 = evaluate_hv_xlpe_power_cable_policy(
            webiq_kema_pq_and_superclean_resin_clean=False,
        )
        self.assertFalse(kem_451.allowed)
        self.assertEqual(kem_451.http_status, 451)

        # 5. Web IQ activates DTS fiber dynamic ampacity (RTTR) & retired copper tolling saving $63,200 ($331,800 net) -> 409 Confirm
        dts_409 = evaluate_hv_xlpe_power_cable_policy(
            dts_dynamic_ampacity_and_copper_tolling_savings_cents=6320000,
        )
        self.assertFalse(dts_409.allowed)
        self.assertEqual(dts_409.http_status, 409)
        self.assertEqual(dts_409.settled_hv_cable_cents, 33180000)
        self.assertEqual(dts_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["hv_xlpe_cable_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("hv-xlpe-cable-sandbox", demo_zh)

    def test_pharma_borosilicate_glass_vial_usp660_hydrolytic_delamination_mandate_vs_flake_recall_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_pharma_borosilicate_vial_policy,
        )

        # 1. Verified 5.0 COE + USP <660> <=0.10 mL + stress <=40 nm/mm + active CDE A -> 200 OK ($215,000)
        commit_ok = evaluate_pharma_borosilicate_vial_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_pharma_vial_cents, 21500000)

        # 2. 7.0 low-borosilicate fraud or heel delamination risk (USP <1660>) -> 403 blocked in 11ms
        del_403 = evaluate_pharma_borosilicate_vial_policy(
            usp660_surface_hydrolytic_and_delamination_verified=False,
        )
        self.assertFalse(del_403.allowed)
        self.assertEqual(del_403.http_status, 403)
        self.assertEqual(
            del_403.pharma_vial_lane,
            "USP660_HYDROLYTIC_EXTRACTABLES_OR_DELAMINATION_RISK_BLOCKED",
        )

        # 3. Residual annealing stress (>40 nm/mm) or warped neck CCIT leak -> 422 blocked in 14ms
        str_422 = evaluate_pharma_borosilicate_vial_policy(
            annealing_birefringence_and_neck_ccit_passed=False,
        )
        self.assertFalse(str_422.allowed)
        self.assertEqual(str_422.http_status, 422)
        self.assertEqual(
            str_422.pharma_vial_lane,
            "ANNEALING_BIREFRINGENCE_STRESS_OR_NECK_FINISH_LEAK_BLOCKED",
        )

        # 4. Web IQ detects lapsed NMPA CDE 'I' status / FDA DMF or endotoxin breach -> 451 blocked in 285ms
        cde_451 = evaluate_pharma_borosilicate_vial_policy(
            webiq_cde_dmf_active_and_endotoxin_clean=False,
        )
        self.assertFalse(cde_451.allowed)
        self.assertEqual(cde_451.http_status, 451)

        # 5. Web IQ upgrades to RTU Nest-and-Tub & hydrophobic overfill reduction saving $34,400 ($180,600 net) -> 409 Confirm
        rtu_409 = evaluate_pharma_borosilicate_vial_policy(
            rtu_nest_tub_and_overfill_reduction_savings_cents=3440000,
        )
        self.assertFalse(rtu_409.allowed)
        self.assertEqual(rtu_409.http_status, 409)
        self.assertEqual(rtu_409.settled_pharma_vial_cents, 18060000)
        self.assertEqual(rtu_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["pharma_vial_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("pharma-borosilicate-vial-sandbox", demo_zh)

    def test_hospital_hotel_linen_laundry_rfid_a0_thermal_disinfection_mandate_vs_wet_weight_nosocomial_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_hospital_hotel_linen_laundry_policy,
        )

        # 1. Verified EN ISO 15883 A0 >=600 s + UHF RFID dry weight + pH 6.0-7.5 -> 200 OK ($130,000)
        commit_ok = evaluate_hospital_hotel_linen_laundry_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_linen_laundry_cents, 13000000)

        # 2. Cold-bleach fake wash (A0 < 600 s) or PAA underdose -> 403 blocked in 11ms
        a0_403 = evaluate_hospital_hotel_linen_laundry_policy(
            thermal_disinfection_a0_and_paa_verified=False,
        )
        self.assertFalse(a0_403.allowed)
        self.assertEqual(a0_403.http_status, 403)
        self.assertEqual(
            a0_403.linen_laundry_lane,
            "THERMAL_DISINFECTION_A0_DEFICIT_OR_PAA_UNDERDOSE_BLOCKED",
        )

        # 3. Damp wet-weight inflation (>6% H2O), RFID shortfall or alkaline pH > 7.5 -> 422 blocked in 14ms
        rfd_422 = evaluate_hospital_hotel_linen_laundry_policy(
            rfid_dry_piece_weight_and_neutral_ph_passed=False,
        )
        self.assertFalse(rfd_422.allowed)
        self.assertEqual(rfd_422.http_status, 422)
        self.assertEqual(
            rfd_422.linen_laundry_lane,
            "RFID_DRY_PIECE_MISMATCH_OR_ALKALINE_PH_CHLORINE_DAMAGE_BLOCKED",
        )

        # 4. Web IQ detects EN 14065 MRSA/Mucorales positivity or barrier breach -> 451 blocked in 285ms
        bio_451 = evaluate_hospital_hotel_linen_laundry_policy(
            webiq_en14065_bioindicator_and_barrier_clean=False,
        )
        self.assertFalse(bio_451.allowed)
        self.assertEqual(bio_451.http_status, 451)

        # 5. Web IQ credits counterflow heat recovery & RFID 100-wash depreciation saving $20,800 ($109,200 net) -> 409 Confirm
        rec_409 = evaluate_hospital_hotel_linen_laundry_policy(
            counterflow_heat_recovery_and_rfid_depreciation_savings_cents=2080000,
        )
        self.assertFalse(rec_409.allowed)
        self.assertEqual(rec_409.http_status, 409)
        self.assertEqual(rec_409.settled_linen_laundry_cents, 10920000)
        self.assertEqual(rec_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["linen_laundry_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("hospital-linen-laundry-sandbox", demo_zh)

    def test_aluminum_smelter_prebaked_carbon_anode_co2_air_reactivity_vanadium_mandate_vs_dusting_net_carbon_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_aluminum_smelter_prebaked_anode_policy,
        )

        # 1. Verified ISO 12988/12989 CO2 >=88% & Air >=75% + XRF V<=180ppm/Na<=120ppm -> 200 OK ($950,000)
        commit_ok = evaluate_aluminum_smelter_prebaked_anode_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_prebaked_anode_cents, 95000000)

        # 2. Under-baked selective binder oxidation (CO2 < 88% / dust > 2.5%) -> 403 blocked in 12ms
        co2_403 = evaluate_aluminum_smelter_prebaked_anode_policy(
            co2_and_air_reactivity_residue_verified=False,
        )
        self.assertFalse(co2_403.allowed)
        self.assertEqual(co2_403.http_status, 403)
        self.assertEqual(
            co2_403.prebaked_anode_lane,
            "CO2_OR_AIR_REACTIVITY_RESIDUE_DEFICIT_DUSTING_BLOCKED",
        )

        # 3. High shot-coke vanadium (>180 ppm) or bath-contaminated butt sodium (>120 ppm) -> 422 blocked in 15ms
        vna_422 = evaluate_aluminum_smelter_prebaked_anode_policy(
            vanadium_sodium_ash_and_resistivity_passed=False,
        )
        self.assertFalse(vna_422.allowed)
        self.assertEqual(vna_422.http_status, 422)
        self.assertEqual(
            vna_422.prebaked_anode_lane,
            "VANADIUM_SODIUM_CATALYTIC_IMPURITY_OR_RESISTIVITY_EXCEEDED_BLOCKED",
        )

        # 4. Web IQ detects excess B[a]P PAH pitch or revoked ASI certification -> 451 blocked in 290ms
        pah_451 = evaluate_aluminum_smelter_prebaked_anode_policy(
            webiq_asi_pah_and_calciner_compliance_clean=False,
        )
        self.assertFalse(pah_451.allowed)
        self.assertEqual(pah_451.http_status, 451)

        # 5. Web IQ credits 22% clean anode-butt return & dual-slot -45mV energy saving $152,000 ($798,000 net) -> 409 Confirm
        but_409 = evaluate_aluminum_smelter_prebaked_anode_policy(
            clean_anode_butt_recycling_and_slotted_energy_credit_cents=15200000,
        )
        self.assertFalse(but_409.allowed)
        self.assertEqual(but_409.http_status, 409)
        self.assertEqual(but_409.settled_prebaked_anode_cents, 79800000)
        self.assertEqual(but_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["prebaked_anode_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("aluminum-prebaked-anode-sandbox", demo_zh)

    def test_nuclear_zirconium_cladding_hafnium_hydride_swu_enrichment_mandate_vs_neutron_poison_creep_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_nuclear_zirconium_fuel_policy,
        )

        # 1. Verified ASTM B353 Hf <=50 ppm + EBC <=1.5 ppm + ASTM B811 Fn <=0.30 -> 200 OK ($1,850,000)
        commit_ok = evaluate_nuclear_zirconium_fuel_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_nuclear_fuel_cents, 185000000)

        # 2. Hafnium carryover (Hf > 50 ppm, 104 barns) or high EBC poison -> 403 blocked in 11ms
        hf_403 = evaluate_nuclear_zirconium_fuel_policy(
            hafnium_cobalt_and_ebc_neutron_cross_section_verified=False,
        )
        self.assertFalse(hf_403.allowed)
        self.assertEqual(hf_403.http_status, 403)
        self.assertEqual(
            hf_403.nuclear_fuel_lane,
            "HAFNIUM_NEUTRON_POISON_OR_EBC_CROSS_SECTION_EXCEEDED_BLOCKED",
        )

        # 3. Radial hydride orientation (Fn > 0.30) or G2 white nodular steam corrosion -> 422 blocked in 14ms
        fn_422 = evaluate_nuclear_zirconium_fuel_policy(
            radial_hydride_fn_and_autoclave_corrosion_passed=False,
        )
        self.assertFalse(fn_422.allowed)
        self.assertEqual(fn_422.http_status, 422)
        self.assertEqual(
            fn_422.nuclear_fuel_lane,
            "RADIAL_HYDRIDE_ORIENTATION_FN_OR_AUTOCLAVE_NODULAR_CORROSION_BLOCKED",
        )

        # 4. Web IQ detects active NRC 10 CFR Part 21 defect notice or IAEA safeguards hold -> 451 blocked in 280ms
        p21_451 = evaluate_nuclear_zirconium_fuel_policy(
            webiq_nrc_part21_and_iaea_safeguards_clean=False,
        )
        self.assertFalse(p21_451.allowed)
        self.assertEqual(p21_451.http_status, 451)

        # 5. Web IQ credits optimal SWU tails (0.18%) & dry U3O8 recycle saving $222,000 ($1,628,000 net) -> 409 Confirm
        swu_409 = evaluate_nuclear_zirconium_fuel_policy(
            optimal_swu_tails_assay_and_uo2_scrap_recycle_credit_cents=22200000,
        )
        self.assertFalse(swu_409.allowed)
        self.assertEqual(swu_409.http_status, 409)
        self.assertEqual(swu_409.settled_nuclear_fuel_cents, 162800000)
        self.assertEqual(swu_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["nuclear_zirconium_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("nuclear-zirconium-fuel-sandbox", demo_zh)

    def test_oilfield_drilling_mud_api_barite_specific_gravity_hthp_filtrate_mandate_vs_lost_circulation_stuck_pipe_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_oilfield_drilling_mud_policy,
        )

        # 1. Verified API 13A SG >=4.20 + Ca2+ <=250 mg/kg + 180°C HTHP <=12 mL -> 200 OK ($480,000)
        commit_ok = evaluate_oilfield_drilling_mud_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_drilling_mud_cents, 48000000)

        # 2. Limestone adulteration (SG < 4.20 g/cm3) or soluble calcium (> 250 mg/kg) -> 403 blocked in 11ms
        sg_403 = evaluate_oilfield_drilling_mud_policy(
            api13a_barite_sg_and_soluble_calcium_verified=False,
        )
        self.assertFalse(sg_403.allowed)
        self.assertEqual(sg_403.http_status, 403)
        self.assertEqual(
            sg_403.drilling_mud_lane,
            "BARITE_SPECIFIC_GRAVITY_DEFICIT_OR_SOLUBLE_CALCIUM_FLOCCULATION_BLOCKED",
        )

        # 3. Excessive 180°C HTHP filtrate (>12 mL) or inclined barite sag (SF > 0.53) -> 422 blocked in 14ms
        hthp_422 = evaluate_oilfield_drilling_mud_policy(
            hthp_filtrate_loss_and_barite_sag_factor_passed=False,
        )
        self.assertFalse(hthp_422.allowed)
        self.assertEqual(hthp_422.http_status, 422)
        self.assertEqual(
            hthp_422.drilling_mud_lane,
            "HTHP_FILTRATION_LOSS_OR_BARITE_SAG_STUCK_PIPE_RISK_BLOCKED",
        )

        # 4. Web IQ detects excess Hg/Cd (>1/3 ppm) or revoked API 13A license -> 451 blocked in 285ms
        epa_451 = evaluate_oilfield_drilling_mud_policy(
            webiq_epa_hg_cd_and_api_monogram_clean=False,
        )
        self.assertFalse(epa_451.allowed)
        self.assertEqual(epa_451.http_status, 451)

        # 5. Web IQ credits 82% dual-centrifuge barite recovery saving $86,400 ($393,600 net) -> 409 Confirm
        cen_409 = evaluate_oilfield_drilling_mud_policy(
            dual_centrifuge_barite_recovery_and_zero_npt_credit_cents=8640000,
        )
        self.assertFalse(cen_409.allowed)
        self.assertEqual(cen_409.http_status, 409)
        self.assertEqual(cen_409.settled_drilling_mud_cents, 39360000)
        self.assertEqual(cen_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["drilling_mud_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("oilfield-drilling-mud-sandbox", demo_zh)

    def test_uhmwpe_ballistic_mooring_fiber_intrinsic_viscosity_tenacity_creep_mandate_vs_decalin_thermal_rupture_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_uhmwpe_ballistic_mooring_policy,
        )

        # 1. Verified ASTM D4020 IV >=20 dL/g + Tenacity >=35 cN/dtex + ISO 18692 Creep <=0.02%/d -> 200 OK ($620,000)
        commit_ok = evaluate_uhmwpe_ballistic_mooring_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_uhmwpe_fiber_cents, 62000000)

        # 2. Low-MW blend (IV < 20 dL/g) or low sonic modulus (< 1,250 cN/dtex) -> 403 blocked in 11ms
        ten_403 = evaluate_uhmwpe_ballistic_mooring_policy(
            intrinsic_viscosity_and_sonic_tenacity_verified=False,
        )
        self.assertFalse(ten_403.allowed)
        self.assertEqual(ten_403.http_status, 403)
        self.assertEqual(
            ten_403.uhmwpe_fiber_lane,
            "TENACITY_SONIC_MODULUS_OR_INTRINSIC_VISCOSITY_DEFICIT_BLOCKED",
        )

        # 3. High 70°C creep rate (>0.02%/d) or residual decalin solvent (>500 ppm) -> 422 blocked in 14ms
        crp_422 = evaluate_uhmwpe_ballistic_mooring_policy(
            mooring_creep_rate_and_decalin_residue_passed=False,
        )
        self.assertFalse(crp_422.allowed)
        self.assertEqual(crp_422.http_status, 422)
        self.assertEqual(
            crp_422.uhmwpe_fiber_lane,
            "MOORING_CREEP_RATE_OR_DECALIN_SOLVENT_RESIDUE_EXCEEDED_BLOCKED",
        )

        # 4. Web IQ detects delisted NIJ CPL model, forged DNV cert or export hold -> 451 blocked in 280ms
        dnv_451 = evaluate_uhmwpe_ballistic_mooring_policy(
            webiq_dnv_nij_cert_and_export_control_clean=False,
        )
        self.assertFalse(dnv_451.allowed)
        self.assertEqual(dnv_451.http_status, 451)

        # 5. Web IQ credits 99.6% decalin recovery & retired rope take-back saving $86,800 ($533,200 net) -> 409 Confirm
        dec_409 = evaluate_uhmwpe_ballistic_mooring_policy(
            closed_loop_decalin_recovery_and_retired_rope_credit_cents=8680000,
        )
        self.assertFalse(dec_409.allowed)
        self.assertEqual(dec_409.http_status, 409)
        self.assertEqual(dec_409.settled_uhmwpe_fiber_cents, 53320000)
        self.assertEqual(dec_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["uhmwpe_fiber_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("uhmwpe-ballistic-mooring-sandbox", demo_zh)

    def test_high_purity_quartz_crucible_sand_hydroxyl_alkali_cristobalite_mandate_vs_bubble_collapse_dislocation_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_high_purity_quartz_crucible_policy,
        )

        # 1. Verified FTIR OH- <=30 ppm + ICP Li+Na+K <=0.8 ppm + IBFL bubble <=0.5% -> 200 OK ($540,000)
        commit_ok = evaluate_high_purity_quartz_crucible_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_quartz_crucible_cents, 54000000)

        # 2. High silanol hydroxyl (OH- > 30 ppm) or 1,500°C sag deflection (>1.5 mm) -> 403 blocked in 11ms
        oh_403 = evaluate_high_purity_quartz_crucible_policy(
            ftir_hydroxyl_and_high_temp_viscosity_verified=False,
        )
        self.assertFalse(oh_403.allowed)
        self.assertEqual(oh_403.http_status, 403)
        self.assertEqual(
            oh_403.quartz_crucible_lane,
            "HYDROXYL_HIGH_TEMP_VISCOSITY_DEFICIT_CRUCIBLE_COLLAPSE_BLOCKED",
        )

        # 3. Inner bubble-free layer vacuum expansion (>0.5%) or alkali devitrification -> 422 blocked in 14ms
        bub_422 = evaluate_high_purity_quartz_crucible_policy(
            alkali_metal_trace_and_inner_bubble_free_layer_passed=False,
        )
        self.assertFalse(bub_422.allowed)
        self.assertEqual(bub_422.http_status, 422)
        self.assertEqual(
            bub_422.quartz_crucible_lane,
            "INNER_LAYER_BUBBLE_GROWTH_OR_ALKALI_DEVITRIFICATION_BLOCKED",
        )

        # 4. Web IQ detects counterfeit vein-quartz substituted for IOTA-CG inner sand -> 451 blocked in 285ms
        iot_451 = evaluate_high_purity_quartz_crucible_policy(
            webiq_iota_sand_provenance_and_semi_pv27_clean=False,
        )
        self.assertFalse(iot_451.allowed)
        self.assertEqual(iot_451.http_status, 451)

        # 5. Web IQ credits nano-Ba(OH)2 430h RCZ longevity & cullet return saving $81,000 ($459,000 net) -> 409 Confirm
        rcz_409 = evaluate_high_purity_quartz_crucible_policy(
            barium_cristobalite_armor_430h_rcz_and_cullet_credit_cents=8100000,
        )
        self.assertFalse(rcz_409.allowed)
        self.assertEqual(rcz_409.http_status, 409)
        self.assertEqual(rcz_409.settled_quartz_crucible_cents, 45900000)
        self.assertEqual(rcz_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["quartz_crucible_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("high-purity-quartz-crucible-sandbox", demo_zh)

    def test_trenchless_sewer_uv_cipp_flexural_modulus_dsc_cure_mandate_vs_groundwater_buckling_styrene_spill_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_trenchless_sewer_uv_cipp_policy,
        )

        # 1. Verified ISO 11296-4 E0 >=12,000 MPa + full wall thickness + DSC Tg >=95°C -> 200 OK ($360,000)
        commit_ok = evaluate_trenchless_sewer_uv_cipp_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_uv_cipp_cents, 36000000)

        # 2. Shaved wall thickness (-45% cubic buckling stiffness) or fast-pull UV under-cure -> 403 blocked in 12ms
        mod_403 = evaluate_trenchless_sewer_uv_cipp_policy(
            flexural_modulus_wall_thickness_and_dsc_cure_verified=False,
        )
        self.assertFalse(mod_403.allowed)
        self.assertEqual(mod_403.http_status, 403)
        self.assertEqual(
            mod_403.uv_cipp_lane,
            "FLEXURAL_MODULUS_WALL_THICKNESS_OR_UV_CURE_DEGREE_DEFICIT_BLOCKED",
        )

        # 3. 3D laser invert fin/wrinkle (>2% ID) or hydrostatic joint leakage -> 422 blocked in 15ms
        las_422 = evaluate_trenchless_sewer_uv_cipp_policy(
            laser_profiler_wrinkle_and_hydrostatic_seal_passed=False,
        )
        self.assertFalse(las_422.allowed)
        self.assertEqual(las_422.http_status, 422)
        self.assertEqual(
            las_422.uv_cipp_lane,
            "LASER_PROFILER_WRINKLE_FIN_OR_HYDROSTATIC_LEAKAGE_EXCEEDED_BLOCKED",
        )

        # 4. Web IQ detects forged DIBt 50-yr creep approval or styrene monomer water spill -> 451 blocked in 285ms
        dib_451 = evaluate_trenchless_sewer_uv_cipp_policy(
            webiq_dibt_50yr_creep_and_styrene_free_clean=False,
        )
        self.assertFalse(dib_451.allowed)
        self.assertEqual(dib_451.http_status, 451)

        # 5. Web IQ credits styrene-free vinyl-ester & trenchless paving offset saving $50,400 ($309,600 net) -> 409 Confirm
        pav_409 = evaluate_trenchless_sewer_uv_cipp_policy(
            styrene_free_resin_and_trenchless_paving_savings_cents=5040000,
        )
        self.assertFalse(pav_409.allowed)
        self.assertEqual(pav_409.http_status, 409)
        self.assertEqual(pav_409.settled_uv_cipp_cents, 30960000)
        self.assertEqual(pav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["uv_cipp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("trenchless-uv-cipp-sandbox", demo_zh)

    def test_recurring_replenishment_spt_cadence_vs_vaulting_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_recurring_replenishment_spt_policy

        # 1. Compliant cadence SPT off_session renewal -> 200 OK
        rec_ok = evaluate_recurring_replenishment_spt_policy(
            off_session=True,
            recurring_interval_configured=True,
            recurring_interval="month",
            live_renewal_price_usd="58.00",
            interval_mandate_ceiling_usd="65.00",
        )
        self.assertTrue(rec_ok.allowed)
        self.assertEqual(rec_ok.http_status, 200)
        self.assertEqual(rec_ok.lane, "cadence_spt_off_session_renewed")
        self.assertEqual(rec_ok.fcb_state, "CLOSED")
        self.assertEqual(rec_ok.action, "Act automatically")

        # 2. Forbidden setup_future_usage on SPT -> 400 Bad Request
        sfu_block = evaluate_recurring_replenishment_spt_policy(
            setup_future_usage="off_session",
        )
        self.assertFalse(sfu_block.allowed)
        self.assertEqual(sfu_block.http_status, 400)
        self.assertEqual(sfu_block.lane, "blocked_spt_forbids_setup_future_usage")

        # 3. off_session=True without recurring_interval -> 400 Bad Request
        no_interval = evaluate_recurring_replenishment_spt_policy(
            off_session=True,
            recurring_interval_configured=False,
        )
        self.assertFalse(no_interval.allowed)
        self.assertEqual(no_interval.http_status, 400)
        self.assertEqual(no_interval.lane, "blocked_off_session_without_recurring_interval")

        # 4. Web IQ safety recall trips FCB CLOSED -> OPEN -> 409 Conflict
        recall_fcb = evaluate_recurring_replenishment_spt_policy(
            webiq_recall_risk_level="veryHigh",
        )
        self.assertFalse(recall_fcb.allowed)
        self.assertEqual(recall_fcb.http_status, 409)
        self.assertEqual(recall_fcb.fcb_state, "OPEN")
        self.assertEqual(recall_fcb.lane, "fcb_tripped_product_safety_recall_blocked")

        # 5. Silent renewal price hike above interval ceiling -> 422 Unprocessable
        price_hike = evaluate_recurring_replenishment_spt_policy(
            live_renewal_price_usd="74.00",
            interval_mandate_ceiling_usd="65.00",
        )
        self.assertFalse(price_hike.allowed)
        self.assertEqual(price_hike.http_status, 422)
        self.assertEqual(price_hike.lane, "blocked_renewal_price_exceeds_interval_ceiling")

        # 6. Reversible requires_action -> active after buyer 3DS step-up -> 200 OK
        recovered = evaluate_recurring_replenishment_spt_policy(
            spt_state="requires_action",
            buyer_completed_3ds=True,
        )
        self.assertTrue(recovered.allowed)
        self.assertEqual(recovered.http_status, 200)
        self.assertEqual(recovered.spt_next_state, "active")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["recurring_replenishment_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("recurring-spt-selector-sandbox", demo_zh)

    def test_post_purchase_refund_and_return_policy_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_post_purchase_refund_and_return_policy

        # 1. Compliant read-only return policy grounding & RMA draft -> 200 OK
        rma_ok = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="return_eligibility_rma_draft",
            browse_http_status=200,
            browse_query="return window restocking fee",
            summary_restocking_fee_usd="0.00",
            terms_restocking_fee_usd="0.00",
        )
        self.assertTrue(rma_ok.allowed)
        self.assertEqual(rma_ok.http_status, 200)
        self.assertEqual(rma_ok.lane, "return_rma_draft_verified")
        self.assertEqual(rma_ok.action, "Act automatically")

        # 2. Browse 202 Accepted async crawl -> 202 Defer (never fabricate return deadline)
        browse_202 = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="return_eligibility_rma_draft",
            browse_http_status=202,
        )
        self.assertFalse(browse_202.allowed)
        self.assertEqual(browse_202.http_status, 202)
        self.assertEqual(browse_202.lane, "defer_browse_202_no_fabricated_deadline")

        # 3. Summary ($0) vs Terms ($15 restocking fee) mismatch -> 409 Conflict
        fee_mismatch = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="return_eligibility_rma_draft",
            browse_http_status=200,
            summary_restocking_fee_usd="0.00",
            terms_restocking_fee_usd="15.00",
        )
        self.assertFalse(fee_mismatch.allowed)
        self.assertEqual(fee_mismatch.http_status, 409)
        self.assertEqual(fee_mismatch.lane, "blocked_summary_terms_restocking_fee_mismatch")

        # 4. Unconfirmed create_refund / send_money -> 403 paused for human confirmation
        refund_paused = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="mcp_refund_or_treasury_write",
            mcp_tool_name="create_refund",
            mcp_auth_mode="oauth",
            human_confirmed=False,
        )
        self.assertFalse(refund_paused.allowed)
        self.assertEqual(refund_paused.http_status, 403)
        self.assertEqual(refund_paused.lane, "paused_mcp_refund_requires_human_confirmation")

        # 5. Post-Nov 30 sk_live_* or >180d dormant payout key -> 401/403 blocked
        sk_cutoff = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="mcp_refund_or_treasury_write",
            mcp_auth_mode="legacy_sk",
            human_confirmed=True,
        )
        self.assertFalse(sk_cutoff.allowed)
        self.assertEqual(sk_cutoff.http_status, 401)

        dormant_180d = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="mcp_refund_or_treasury_write",
            mcp_auth_mode="agent_rk",
            days_since_last_transfer_or_payout=185,
            human_confirmed=True,
        )
        self.assertFalse(dormant_180d.allowed)
        self.assertEqual(dormant_180d.http_status, 403)

        # 6. Human confirmed refund with active OAuth -> 200 OK
        refund_ok = evaluate_post_purchase_refund_and_return_policy(
            operation_lane="mcp_refund_or_treasury_write",
            mcp_tool_name="create_refund",
            mcp_auth_mode="oauth",
            human_confirmed=True,
        )
        self.assertTrue(refund_ok.allowed)
        self.assertEqual(refund_ok.http_status, 200)
        self.assertEqual(refund_ok.lane, "confirmed_mcp_refund_executed")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["post_purchase_refund_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("post-purchase-refund-selector-sandbox", demo_zh)

    def test_multi_merchant_split_cart_saga_vs_connect(self) -> None:
        from lab.webiq_commerce_demo import evaluate_multi_merchant_split_cart_saga

        # 1. Compliant Connect Separate Charges without OBO and without Stripe-Account header -> 200 OK
        conn_ok = evaluate_multi_merchant_split_cart_saga(
            topology="stripe_connect_separate_charges",
            on_behalf_of_set=False,
            stripe_account_header_present=False,
            leg_amounts_usd=("580.00", "480.00", "320.00"),
            bundle_mandate_ceiling_usd="1500.00",
        )
        self.assertTrue(conn_ok.allowed)
        self.assertEqual(conn_ok.http_status, 200)
        self.assertEqual(conn_ok.recommended_pattern, "connect_unified_split_transfers")

        # 2. Connect Separate Charges without OBO but passing Stripe-Account header -> 400 Bad Request
        conn_trap = evaluate_multi_merchant_split_cart_saga(
            topology="stripe_connect_separate_charges",
            on_behalf_of_set=False,
            stripe_account_header_present=True,
        )
        self.assertFalse(conn_trap.allowed)
        self.assertEqual(conn_trap.http_status, 400)
        self.assertEqual(conn_trap.recommended_pattern, "blocked_connect_header_without_obo")

        # 3. Cross-merchant 2-phase manual pre-auth hold all legs succeed -> 200 OK
        saga_ok = evaluate_multi_merchant_split_cart_saga(
            topology="cross_merchant_2phase_saga",
            all_or_nothing_bundle=True,
            capture_method="manual",
            leg_amounts_usd=("620.00", "480.00", "320.00"),
            bundle_mandate_ceiling_usd="1500.00",
        )
        self.assertTrue(saga_ok.allowed)
        self.assertEqual(saga_ok.http_status, 200)
        self.assertEqual(saga_ok.recommended_pattern, "two_phase_preauth_captured_all")

        # 4. Cross-merchant Leg 3 fails (409 OOS) -> Saga cancels Legs 1 & 2 ($1,100 released, $0.00 loss)
        saga_rollback = evaluate_multi_merchant_split_cart_saga(
            topology="cross_merchant_2phase_saga",
            all_or_nothing_bundle=True,
            capture_method="manual",
            leg_amounts_usd=("620.00", "480.00", "320.00"),
            bundle_mandate_ceiling_usd="1500.00",
            failed_leg_index=2,
            failed_leg_reason="slot_unavailable_409",
        )
        self.assertFalse(saga_rollback.allowed)
        self.assertEqual(saga_rollback.http_status, 409)
        self.assertEqual(saga_rollback.recommended_pattern, "saga_compensated_preauth_released_zero_loss")
        self.assertEqual(saga_rollback.held_and_released_usd, "1100.00")
        self.assertEqual(saga_rollback.settled_loss_usd, "0.00")

        # 5. Naive automatic capture on interdependent bundle -> 400 Bad Request
        naive_block = evaluate_multi_merchant_split_cart_saga(
            topology="cross_merchant_2phase_saga",
            all_or_nothing_bundle=True,
            capture_method="automatic",
        )
        self.assertFalse(naive_block.allowed)
        self.assertEqual(naive_block.http_status, 400)
        self.assertEqual(naive_block.recommended_pattern, "blocked_naive_automatic_capture_on_bundle")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["split_cart_saga_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("split-cart-saga-selector-sandbox", demo_zh)

    def test_bnpl_webview_handover_vs_headless_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import evaluate_bnpl_webview_handover_policy

        # 1. Compliant 0% APR Pay-in-4 in isolated system WebView -> HTTP 202 requires_redirect_handover
        handover_ok = evaluate_bnpl_webview_handover_policy(
            payment_rail="klarna_pay_in_4",
            principal_usd="800.00",
            total_repayment_usd="800.00",
            mandate_ceiling_usd="820.00",
            apr_pct=0.0,
            max_allowed_apr_pct=0.0,
            execution_surface="isolated_system_webview",
        )
        self.assertTrue(handover_ok.allowed)
        self.assertEqual(handover_ok.http_status, 202)
        self.assertEqual(handover_ok.recommended_flow, "controlled_webview_redirect_handover")
        self.assertEqual(handover_ok.action_pill, "Confirm")

        # 2. Headless browser attempting to auto-sign BNPL loan -> HTTP 403 hard block
        headless_block = evaluate_bnpl_webview_handover_policy(
            payment_rail="affirm_installments",
            execution_surface="headless_browser_automation",
        )
        self.assertFalse(headless_block.allowed)
        self.assertEqual(headless_block.http_status, 403)
        self.assertEqual(headless_block.recommended_flow, "blocked_headless_bnpl_prohibited")
        self.assertEqual(headless_block.action_pill, "Send to a human")

        # 3. Hidden 24.99% APR exceeding mandate ceiling or APR cap -> HTTP 403 block
        apr_trap = evaluate_bnpl_webview_handover_policy(
            payment_rail="affirm_installments",
            principal_usd="800.00",
            total_repayment_usd="912.40",
            mandate_ceiling_usd="820.00",
            apr_pct=24.99,
            max_allowed_apr_pct=0.0,
            execution_surface="isolated_system_webview",
        )
        self.assertFalse(apr_trap.allowed)
        self.assertEqual(apr_trap.http_status, 403)
        self.assertEqual(apr_trap.recommended_flow, "blocked_apr_or_total_repayment_exceeds_mandate")

        # 4. Unattended background task -> HTTP 409 recommends SPT v2 fallback
        unattended = evaluate_bnpl_webview_handover_policy(
            payment_rail="klarna_pay_in_4",
            execution_surface="unattended_background_task",
        )
        self.assertFalse(unattended.allowed)
        self.assertEqual(unattended.http_status, 409)
        self.assertEqual(unattended.recommended_flow, "fallback_to_spt_for_unattended_task")

        # 5. Card token rail (Stripe SPT v2) -> HTTP 200 zero redirect autonomous settlement
        card_auto = evaluate_bnpl_webview_handover_policy(
            payment_rail="stripe_spt_v2",
            principal_usd="450.00",
            total_repayment_usd="450.00",
            mandate_ceiling_usd="500.00",
            execution_surface="unattended_background_task",
        )
        self.assertTrue(card_auto.allowed)
        self.assertEqual(card_auto.http_status, 200)
        self.assertEqual(card_auto.recommended_flow, "autonomous_card_token_zero_redirect")
        self.assertEqual(card_auto.action_pill, "Act automatically")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["bnpl_webview_handover_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("bnpl-handover-selector-sandbox", demo_zh)


if __name__ == "__main__":
    unittest.main()
