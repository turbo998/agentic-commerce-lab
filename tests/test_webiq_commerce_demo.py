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
            "docs/price-drop-watchlist-mandate-vs-cart-recovery-spam-faq.md",
            "docs/price-drop-watchlist-mandate-vs-cart-recovery-spam-faq.en.md",
            "docs/b2b-moq-syndicate-escrow-vs-stranded-deposit-shortfall-faq.md",
            "docs/b2b-moq-syndicate-escrow-vs-stranded-deposit-shortfall-faq.en.md",
            "docs/b2b-sealed-bid-reverse-auction-vs-price-signaling-collusion-faq.md",
            "docs/b2b-sealed-bid-reverse-auction-vs-price-signaling-collusion-faq.en.md",
            "docs/cross-border-customs-hs-tariff-mandate-vs-seizure-faq.md",
            "docs/cross-border-customs-hs-tariff-mandate-vs-seizure-faq.en.md",
            "docs/saas-seat-trueup-telemetry-mandate-vs-shelfware-auto-renewal-faq.md",
            "docs/saas-seat-trueup-telemetry-mandate-vs-shelfware-auto-renewal-faq.en.md",
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


    def test_agentic_3ds2_fido2_spc_biometric_stepup_mandate_vs_sms_otp_scraping_takeover_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_3ds2_fido2_spc_policy,
        )

        # 1. Verified W3C SPC dynamic linking + 3DS 2.3.1 CAVV ECI=05 -> 200 OK ($430,000)
        commit_ok = evaluate_agentic_3ds2_fido2_spc_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_sca_batch_cents, 43000000)

        # 2. SPC dynamic linking mismatch or missing CAVV (ECI=07) -> 403 blocked in 11ms
        spc_403 = evaluate_agentic_3ds2_fido2_spc_policy(
            spc_fido2_dynamic_linking_and_cavv_eci05_verified=False,
        )
        self.assertFalse(spc_403.allowed)
        self.assertEqual(spc_403.http_status, 403)
        self.assertEqual(
            spc_403.sca_stepup_lane,
            "SPC_DYNAMIC_LINKING_MISMATCH_OR_MISSING_CAVV_BLOCKED",
        )

        # 3. Headless browser ACS scraping or plaintext SMS OTP forwarding -> 422 blocked in 14ms
        bot_422 = evaluate_agentic_3ds2_fido2_spc_policy(
            zero_headless_acs_injection_and_no_sms_otp_relay_passed=False,
        )
        self.assertFalse(bot_422.allowed)
        self.assertEqual(bot_422.http_status, 422)
        self.assertEqual(
            bot_422.sca_stepup_lane,
            "HEADLESS_ACS_CHALLENGE_BOT_OR_SMS_OTP_RELAY_BLOCKED",
        )

        # 4. Web IQ detects deprecated 3DS 2.1 schema or breached TRA fraud ratio -> 451 blocked in 280ms
        tra_451 = evaluate_agentic_3ds2_fido2_spc_policy(
            webiq_psd2_tra_exemption_and_3ds231_schema_clean=False,
        )
        self.assertFalse(tra_451.allowed)
        self.assertEqual(tra_451.http_status, 451)

        # 5. Web IQ credits FIDO2 delegated auth & ECI=05 liability shift saving $64,500 ($365,500 net) -> 409 Confirm
        shf_409 = evaluate_agentic_3ds2_fido2_spc_policy(
            fido2_delegated_auth_and_chargeback_liability_shift_credit_cents=6450000,
        )
        self.assertFalse(shf_409.allowed)
        self.assertEqual(shf_409.http_status, 409)
        self.assertEqual(shf_409.settled_sca_batch_cents, 36550000)
        self.assertEqual(shf_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_3ds2_fido2_spc_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-3ds2-fido2-spc-sandbox", demo_zh)

    def test_b2b_supply_chain_finance_dynamic_discounting_reverse_factoring_mandate_vs_double_pledge_invoice_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_scf_dynamic_discount_policy,
        )

        # 1. Verified 3-way match UUID + zero double-pledge + sliding APR >=18% + 15% holdback -> 200 OK ($650,000)
        commit_ok = evaluate_b2b_scf_dynamic_discount_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_scf_ap_cents, 65000000)

        # 2. Double-pledge invoice fraud or missing warehouse GRN -> 403 blocked in 11ms
        plg_403 = evaluate_b2b_scf_dynamic_discount_policy(
            three_way_match_einvoice_uuid_and_zero_double_pledge_verified=False,
        )
        self.assertFalse(plg_403.allowed)
        self.assertEqual(plg_403.http_status, 403)
        self.assertEqual(
            plg_403.scf_discount_lane,
            "DOUBLE_PLEDGE_INVOICE_FRAUD_OR_UNVERIFIED_GRN_BLOCKED",
        )

        # 3. Negative treasury carry (APR <18%) or 100% unconditional IPU without 15% holdback -> 422 blocked in 14ms
        apr_422 = evaluate_b2b_scf_dynamic_discount_policy(
            sliding_scale_apr_above_hurdle_and_15pct_holdback_passed=False,
        )
        self.assertFalse(apr_422.allowed)
        self.assertEqual(apr_422.http_status, 422)
        self.assertEqual(
            apr_422.scf_discount_lane,
            "NEGATIVE_TREASURY_CARRY_APR_OR_ZERO_HOLDBACK_BLOCKED",
        )

        # 4. Web IQ detects tax red-letter invoice reversal or supplier insolvency -> 451 blocked in 280ms
        red_451 = evaluate_b2b_scf_dynamic_discount_policy(
            webiq_tax_red_letter_lock_and_supplier_solvency_clean=False,
        )
        self.assertFalse(red_451.allowed)
        self.assertEqual(red_451.http_status, 451)

        # 5. Web IQ credits Day-12 sliding dynamic discount & ESG SCF rebate saving $58,500 ($591,500 net) -> 409 Confirm
        reb_409 = evaluate_b2b_scf_dynamic_discount_policy(
            sliding_early_pay_discount_and_reverse_factoring_rebate_cents=5850000,
        )
        self.assertFalse(reb_409.allowed)
        self.assertEqual(reb_409.http_status, 409)
        self.assertEqual(reb_409.settled_scf_ap_cents, 59150000)
        self.assertEqual(reb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_scf_dynamic_discount_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-scf-dynamic-discount-sandbox", demo_zh)

    def test_agentic_x402_mpp_streaming_micropayment_channel_netting_mandate_vs_card_fixed_fee_margin_wipeout_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_x402_mpp_streaming_policy,
        )

        # 1. Verified state channel + microcents ledger + <=1.5% fee ratio -> 200 OK ($320,000)
        commit_ok = evaluate_agentic_x402_mpp_streaming_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_mpp_channel_cents, 32000000)

        # 2. Per-call card $0.30 fixed-fee margin wipeout -> 403 blocked in 11ms
        fee_403 = evaluate_agentic_x402_mpp_streaming_policy(
            per_call_fixed_fee_ratio_15pct_and_state_channel_verified=False,
        )
        self.assertFalse(fee_403.allowed)
        self.assertEqual(fee_403.http_status, 403)
        self.assertEqual(
            fee_403.mpp_streaming_lane,
            "PER_CALL_CARD_FIXED_FEE_MARGIN_WIPEOUT_BLOCKED",
        )

        # 3. Sub-cent truncation exploit (floor(0.4c)=0) or voucher nonce replay -> 422 blocked in 14ms
        sub_422 = evaluate_agentic_x402_mpp_streaming_policy(
            monotonic_voucher_nonce_and_zero_subcent_truncation_passed=False,
        )
        self.assertFalse(sub_422.allowed)
        self.assertEqual(sub_422.http_status, 422)
        self.assertEqual(
            sub_422.mpp_streaming_lane,
            "SUB_CENT_TRUNCATION_EXPLOIT_OR_NONCE_REPLAY_BLOCKED",
        )

        # 4. Web IQ detects upstream 5xx error billing or undisclosed surge pricing -> 451 blocked in 280ms
        err_451 = evaluate_agentic_x402_mpp_streaming_policy(
            webiq_upstream_200ok_schema_and_published_tariff_clean=False,
        )
        self.assertFalse(err_451.allowed)
        self.assertEqual(err_451.http_status, 451)

        # 5. Web IQ credits 16M-call single-batch rollup netting & volume tier saving $48,000 ($272,000 net) -> 409 Confirm
        rol_409 = evaluate_agentic_x402_mpp_streaming_policy(
            state_channel_rollup_netting_and_volume_tier_rebate_cents=4800000,
        )
        self.assertFalse(rol_409.allowed)
        self.assertEqual(rol_409.http_status, 409)
        self.assertEqual(rol_409.settled_mpp_channel_cents, 27200000)
        self.assertEqual(rol_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_x402_mpp_streaming_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-x402-mpp-streaming-sandbox", demo_zh)

    def test_b2b_cross_border_withholding_tax_wht_transfer_pricing_trc_mandate_vs_grossup_double_taxation_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_wht_transfer_pricing_policy,
        )

        # 1. Verified WHT split + e-TRC + OECD [Q1, Q3] margin -> 200 OK ($500,000)
        commit_ok = evaluate_b2b_wht_transfer_pricing_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cross_border_b2b_cents, 50000000)

        # 2. Unwithheld cross-border WHT or missing e-TRC -> 403 blocked in 11ms
        trc_403 = evaluate_b2b_wht_transfer_pricing_policy(
            wht_source_withholding_and_etrc_beneficial_owner_verified=False,
        )
        self.assertFalse(trc_403.allowed)
        self.assertEqual(trc_403.http_status, 403)
        self.assertEqual(
            trc_403.wht_tp_lane,
            "UNWITHHELD_CROSS_BORDER_WHT_OR_MISSING_ETRC_BLOCKED",
        )

        # 3. Intercompany margin outside OECD [Q1, Q3] IQR or conduit shell -> 422 blocked in 14ms
        iqr_422 = evaluate_b2b_wht_transfer_pricing_policy(
            oecd_arms_length_iqr_and_anti_conduit_substance_passed=False,
        )
        self.assertFalse(iqr_422.allowed)
        self.assertEqual(iqr_422.http_status, 422)
        self.assertEqual(
            iqr_422.wht_tp_lane,
            "TRANSFER_PRICING_IQR_BREACH_OR_CONDUIT_SHELL_BLOCKED",
        )

        # 4. Web IQ detects OECD Pillar Two UTPR exposure or missing FX tax filing -> 451 blocked in 280ms
        pil_451 = evaluate_b2b_wht_transfer_pricing_policy(
            webiq_pillar_two_15pct_etr_and_fx_tax_filing_clean=False,
        )
        self.assertFalse(pil_451.allowed)
        self.assertEqual(pil_451.http_status, 451)

        # 5. Web IQ credits e-TRC DTA treaty rate reduction & gross-up avoidance saving $62,500 ($437,500 net) -> 409 Confirm
        dta_409 = evaluate_b2b_wht_transfer_pricing_policy(
            dta_treaty_rate_reduction_and_grossup_avoidance_credit_cents=6250000,
        )
        self.assertFalse(dta_409.allowed)
        self.assertEqual(dta_409.http_status, 409)
        self.assertEqual(dta_409.settled_cross_border_b2b_cents, 43750000)
        self.assertEqual(dta_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_wht_transfer_pricing_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-wht-transfer-pricing-sandbox", demo_zh)

    def test_b2b_vendor_onboarding_bank_account_change_bec_fraud_sanctions_mandate_vs_email_iban_hijack_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_vendor_bec_kyb_policy,
        )

        # 1. Verified clearinghouse CoP TIN match + 72h cooling + 4-tier UBO clean -> 200 OK ($780,000)
        commit_ok = evaluate_b2b_vendor_bec_kyb_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_vendor_batch_cents, 78000000)

        # 2. BEC email IBAN hijack or clearinghouse CoP TIN mismatch -> 403 blocked in 11ms
        bec_403 = evaluate_b2b_vendor_bec_kyb_policy(
            bank_cop_tin_invariance_and_zero_email_iban_override_verified=False,
        )
        self.assertFalse(bec_403.allowed)
        self.assertEqual(bec_403.http_status, 403)
        self.assertEqual(
            bec_403.vendor_kyb_lane,
            "BEC_EMAIL_IBAN_HIJACK_OR_COP_TIN_MISMATCH_BLOCKED",
        )

        # 3. 72h cooling-off bypass or employee shell-vendor collision -> 422 blocked in 14ms
        shl_422 = evaluate_b2b_vendor_bec_kyb_policy(
            cooling_off_72h_oob_passkey_and_zero_employee_shell_passed=False,
        )
        self.assertFalse(shl_422.allowed)
        self.assertEqual(shl_422.http_status, 422)
        self.assertEqual(
            shl_422.vendor_kyb_lane,
            "COOLING_OFF_BYPASS_OR_EMPLOYEE_SHELL_CONFLICT_BLOCKED",
        )

        # 4. Web IQ detects tier-3 UBO >=50% OFAC sanctions taint or zero headcount -> 451 blocked in 280ms
        ubo_451 = evaluate_b2b_vendor_bec_kyb_policy(
            webiq_ubo_50pct_sanctions_and_social_security_headcount_clean=False,
        )
        self.assertFalse(ubo_451.allowed)
        self.assertEqual(ubo_451.http_status, 451)

        # 5. Web IQ credits OEM direct catalog disintermediation & BEC insurance saving $93,600 ($686,400 net) -> 409 Confirm
        oem_409 = evaluate_b2b_vendor_bec_kyb_policy(
            oem_direct_catalog_disintermediation_and_bec_insurance_credit_cents=9360000,
        )
        self.assertFalse(oem_409.allowed)
        self.assertEqual(oem_409.http_status, 409)
        self.assertEqual(oem_409.settled_vendor_batch_cents, 68640000)
        self.assertEqual(oem_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_vendor_bec_kyb_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-vendor-bec-kyb-sandbox", demo_zh)

    def test_marketplace_split_settlement_bustout_rolling_reserve_delivery_escrow_mandate_vs_t1_payout_clawback_loss_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_marketplace_split_bustout_policy,
        )

        # 1. Verified 25% rolling reserve + Largest-Remainder penny exact + POD -> 200 OK ($600,000)
        commit_ok = evaluate_marketplace_split_bustout_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_marketplace_gmv_cents, 60000000)

        # 2. Seller bust-out velocity spike without 25% reserve or premature T+1 payout -> 403 blocked in 11ms
        bst_403 = evaluate_marketplace_split_bustout_policy(
            bustout_velocity_reserve_25pct_and_pod_escrow_verified=False,
        )
        self.assertFalse(bst_403.allowed)
        self.assertEqual(bst_403.http_status, 403)
        self.assertEqual(
            bst_403.marketplace_split_lane,
            "SELLER_BUSTOUT_VELOCITY_SPIKE_OR_PREMATURE_PAYOUT_BLOCKED",
        )

        # 3. Split penny conservation error or uncovered refund clawback -> 422 blocked in 14ms
        pny_422 = evaluate_marketplace_split_bustout_policy(
            split_penny_conservation_and_reverse_clawback_passed=False,
        )
        self.assertFalse(pny_422.allowed)
        self.assertEqual(pny_422.http_status, 422)
        self.assertEqual(
            pny_422.marketplace_split_lane,
            "SPLIT_PENNY_CONSERVATION_OR_CLAWBACK_UNCOVERED_BLOCKED",
        )

        # 4. Web IQ detects 0.02kg empty parcel weight mismatch or spoofed POD -> 451 blocked in 280ms
        wgt_451 = evaluate_marketplace_split_bustout_policy(
            webiq_carrier_parcel_weight_and_pod_geohash_clean=False,
        )
        self.assertFalse(wgt_451.allowed)
        self.assertEqual(wgt_451.http_status, 451)

        # 5. Web IQ credits rolling-reserve clawback shield & dispute avoidance saving $90,000 ($510,000 net) -> 409 Confirm
        rsv_409 = evaluate_marketplace_split_bustout_policy(
            rolling_reserve_clawback_shield_and_dispute_avoidance_credit_cents=9000000,
        )
        self.assertFalse(rsv_409.allowed)
        self.assertEqual(rsv_409.http_status, 409)
        self.assertEqual(rsv_409.settled_marketplace_gmv_cents, 51000000)
        self.assertEqual(rsv_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["marketplace_split_bustout_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("marketplace-split-bustout-sandbox", demo_zh)

    def test_agentic_stablecoin_eip3009_depeg_circuit_breaker_kyt_mandate_vs_unlimited_erc20_approve_drain_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_stablecoin_eip3009_policy,
        )

        # 1. Verified EIP-3009 exact signature + TWAP $0.9998 + L1 finalized KYT clean -> 200 OK ($540,000)
        commit_ok = evaluate_agentic_stablecoin_eip3009_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_stablecoin_batch_cents, 54000000)

        # 2. Unlimited ERC-20 approve(MAX_UINT256) or invalid EIP-3009 signature -> 403 blocked in 11ms
        app_403 = evaluate_agentic_stablecoin_eip3009_policy(
            eip3009_exact_signature_and_zero_unlimited_approve_verified=False,
        )
        self.assertFalse(app_403.allowed)
        self.assertEqual(app_403.http_status, 403)
        self.assertEqual(
            app_403.stablecoin_eip3009_lane,
            "UNLIMITED_ERC20_APPROVE_OR_INVALID_EIP3009_BLOCKED",
        )

        # 3. Stablecoin TWAP depeg (<$0.9985) tripping circuit breaker to fiat SPT -> 422 blocked in 14ms
        dpg_422 = evaluate_agentic_stablecoin_eip3009_policy(
            oracle_twap_peg_corridor_and_fiat_fallback_ready=False,
        )
        self.assertFalse(dpg_422.allowed)
        self.assertEqual(dpg_422.http_status, 422)
        self.assertEqual(
            dpg_422.stablecoin_eip3009_lane,
            "STABLECOIN_DEPEG_CIRCUIT_BREAKER_FIAT_FALLBACK_BLOCKED",
        )

        # 4. Web IQ detects unfinalized L2 reorg risk or 5-hop KYT sanctions taint -> 451 blocked in 280ms
        kyt_451 = evaluate_agentic_stablecoin_eip3009_policy(
            webiq_l1_finality_and_kyt_zero_sanctions_taint_clean=False,
        )
        self.assertFalse(kyt_451.allowed)
        self.assertEqual(kyt_451.http_status, 451)

        # 5. Web IQ credits cross-border FX spread elimination & gasless relayer saving $64,800 ($475,200 net) -> 409 Confirm
        fxs_409 = evaluate_agentic_stablecoin_eip3009_policy(
            cross_border_fx_spread_elimination_and_gasless_relayer_credit_cents=6480000,
        )
        self.assertFalse(fxs_409.allowed)
        self.assertEqual(fxs_409.http_status, 409)
        self.assertEqual(fxs_409.settled_stablecoin_batch_cents, 47520000)
        self.assertEqual(fxs_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_stablecoin_eip3009_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-stablecoin-eip3009-sandbox", demo_zh)

    def test_agentic_open_banking_a2a_fednow_sepa_instant_vrp_mandate_vs_irreversible_app_fraud_card_fee_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_open_banking_a2a_vrp_policy,
        )

        # 1. Verified ISO 20022 pain.013 RfP + FAPI 2.0 DPoP VRP + zero screen-scraping -> 200 OK ($480,000)
        commit_ok = evaluate_agentic_open_banking_a2a_vrp_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_a2a_vrp_cents, 48000000)

        # 2. Unprotected raw pacs.008 push (APP fraud risk) or missing pain.013 RfP -> 403 blocked in 11ms
        rfp_403 = evaluate_agentic_open_banking_a2a_vrp_policy(
            iso20022_pain013_rfp_and_escrow_safeguard_verified=False,
        )
        self.assertFalse(rfp_403.allowed)
        self.assertEqual(rfp_403.http_status, 403)
        self.assertEqual(
            rfp_403.open_banking_a2a_lane,
            "UNPROTECTED_RAW_PUSH_APP_FRAUD_OR_MISSING_RFP_BLOCKED",
        )

        # 3. Screen-scraping bank credentials or VRP periodic cap violation -> 422 blocked in 14ms
        scr_422 = evaluate_agentic_open_banking_a2a_vrp_policy(
            fapi2_dpop_vrp_caps_and_zero_screen_scraping_passed=False,
        )
        self.assertFalse(scr_422.allowed)
        self.assertEqual(scr_422.http_status, 422)
        self.assertEqual(
            scr_422.open_banking_a2a_lane,
            "SCREEN_SCRAPING_CREDENTIAL_THEFT_OR_VRP_CAP_BLOCKED",
        )

        # 4. Web IQ detects revoked Open Banking eIDAS cert or high PSR APP fraud risk -> 451 blocked in 280ms
        app_451 = evaluate_agentic_open_banking_a2a_vrp_policy(
            webiq_ob_directory_cert_and_psr_app_fraud_score_clean=False,
        )
        self.assertFalse(app_451.allowed)
        self.assertEqual(app_451.http_status, 451)

        # 5. Web IQ credits 2.9% card interchange elimination & instant discount saving $57,600 ($422,400 net) -> 409 Confirm
        icf_409 = evaluate_agentic_open_banking_a2a_vrp_policy(
            a2a_interchange_fee_elimination_and_instant_settlement_discount_cents=5760000,
        )
        self.assertFalse(icf_409.allowed)
        self.assertEqual(icf_409.http_status, 409)
        self.assertEqual(icf_409.settled_a2a_vrp_cents, 42240000)
        self.assertEqual(icf_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_open_banking_a2a_vrp_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-open-banking-a2a-vrp-sandbox", demo_zh)

    def test_b2b_virtual_card_vcn_level3_line_item_interchange_mandate_vs_level1_downgrade_ghost_card_leak_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_vcn_level3_interchange_policy,
        )

        # 1. Verified single-use exact VCN + penny-exact L3 line items + valid UNSPSC -> 200 OK ($750,000)
        commit_ok = evaluate_b2b_vcn_level3_interchange_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_vcn_batch_cents, 75000000)

        # 2. Static department ghost-card reuse or unbounded VCN limit -> 403 blocked in 11ms
        ghs_403 = evaluate_b2b_vcn_level3_interchange_policy(
            single_use_exact_vcn_and_no_static_ghost_card_verified=False,
        )
        self.assertFalse(ghs_403.allowed)
        self.assertEqual(ghs_403.http_status, 403)
        self.assertEqual(
            ghs_403.vcn_level3_lane,
            "STATIC_GHOST_CARD_REUSE_OR_UNBOUNDED_VCN_BLOCKED",
        )

        # 3. Bare Level 1 clearing (+115 bps downgrade) or 1-cent L3 sum mismatch -> 422 blocked in 14ms
        l1d_422 = evaluate_b2b_vcn_level3_interchange_policy(
            level3_line_item_sum_exact_and_unspsc_schema_passed=False,
        )
        self.assertFalse(l1d_422.allowed)
        self.assertEqual(l1d_422.http_status, 422)
        self.assertEqual(
            l1d_422.vcn_level3_lane,
            "LEVEL1_INTERCHANGE_DOWNGRADE_OR_L3_SUM_MISMATCH_BLOCKED",
        )

        # 4. Web IQ detects spoofed 00000000 UNSPSC code or fake $0.01 tax gaming -> 451 blocked in 280ms
        uns_451 = evaluate_b2b_vcn_level3_interchange_policy(
            webiq_unspsc_commodity_code_and_tax_exemption_clean=False,
        )
        self.assertFalse(uns_451.allowed)
        self.assertEqual(uns_451.http_status, 451)

        # 5. Web IQ credits L3 surcharge waiver & 1.35% issuer rebate saving $82,500 ($667,500 net) -> 409 Confirm
        reb_409 = evaluate_b2b_vcn_level3_interchange_policy(
            l3_interchange_surcharge_waiver_and_issuer_rebate_credit_cents=8250000,
        )
        self.assertFalse(reb_409.allowed)
        self.assertEqual(reb_409.http_status, 409)
        self.assertEqual(reb_409.settled_vcn_batch_cents, 66750000)
        self.assertEqual(reb_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_vcn_level3_interchange_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-vcn-level3-interchange-sandbox", demo_zh)

    def test_agentic_chargeback_ce30_compelling_evidence_ethoca_rdr_mandate_vs_friendly_fraud_vdmp_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_chargeback_ce30_policy,
        )

        # 1. Verified CE 3.0 2-order 120-365d 2-of-4 match + zero double refund -> 200 OK ($460,000)
        commit_ok = evaluate_agentic_chargeback_ce30_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_dispute_batch_cents, 46000000)

        # 2. Missing CE 3.0 2-of-4 match on blind $500 pre-arbitration -> 403 blocked in 11ms
        arb_403 = evaluate_agentic_chargeback_ce30_policy(
            ce30_two_prior_orders_120_365d_and_2of4_match_verified=False,
        )
        self.assertFalse(arb_403.allowed)
        self.assertEqual(arb_403.http_status, 403)
        self.assertEqual(
            arb_403.chargeback_ce30_lane,
            "UNQUALIFIED_CE30_EVIDENCE_OR_BLIND_ARBITRATION_BLOCKED",
        )

        # 3. Duplicate standard refund on active chargeback or negative-ROI fight -> 422 blocked in 14ms
        dbl_422 = evaluate_agentic_chargeback_ce30_policy(
            rdr_ethoca_pre_dispute_triage_and_no_double_refund_passed=False,
        )
        self.assertFalse(dbl_422.allowed)
        self.assertEqual(dbl_422.http_status, 422)
        self.assertEqual(
            dbl_422.chargeback_ce30_lane,
            "DOUBLE_REFUND_ON_ACTIVE_CHARGEBACK_OR_NEGATIVE_ROI_BLOCKED",
        )

        # 4. Web IQ detects VDMP dispute ratio approaching 0.90% or invalid CE 3.0 schema -> 451 blocked in 280ms
        vdm_451 = evaluate_agentic_chargeback_ce30_policy(
            webiq_vdmp_dispute_ratio_and_order_insight_schema_clean=False,
        )
        self.assertFalse(vdm_451.allowed)
        self.assertEqual(vdm_451.http_status, 451)

        # 5. Web IQ credits CE 3.0 liability-shift win & RDR fee avoidance saving $69,000 ($391,000 net) -> 409 Confirm
        win_409 = evaluate_agentic_chargeback_ce30_policy(
            ce30_liability_shift_recovery_and_rdr_fee_avoidance_credit_cents=6900000,
        )
        self.assertFalse(win_409.allowed)
        self.assertEqual(win_409.http_status, 409)
        self.assertEqual(win_409.settled_dispute_batch_cents, 39100000)
        self.assertEqual(win_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_chargeback_ce30_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-chargeback-ce30-sandbox", demo_zh)

    def test_b2b_eucp_ebl_electronic_letter_of_credit_mletr_mandate_vs_paper_bl_demurrage_discrepancy_rejection_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_eucp_ebl_letter_of_credit_policy,
        )

        # 1. Verified MT700 45A mirror + 110% CIF insurance + <=21d DCSA eBL -> 200 OK ($920,000)
        commit_ok = evaluate_b2b_eucp_ebl_letter_of_credit_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_lc_batch_cents, 92000000)

        # 2. LLM paraphrased MT700 45A or CIF insurance < 110% -> 403 blocked in 11ms
        dsc_403 = evaluate_b2b_eucp_ebl_letter_of_credit_policy(
            mt700_45a_mirror_and_cif_insurance_110pct_verified=False,
        )
        self.assertFalse(dsc_403.allowed)
        self.assertEqual(dsc_403.http_status, 403)
        self.assertEqual(
            dsc_403.eucp_ebl_lane,
            "UCP600_MIRROR_OR_INSURANCE_110PCT_DISCREPANCY_BLOCKED",
        )

        # 3. Late presentation (>21d post-shipment) or unendorsed DCSA eBL -> 422 blocked in 14ms
        lat_422 = evaluate_b2b_eucp_ebl_letter_of_credit_policy(
            presentation_within_21d_and_dcsa_ebl_control_endorsed=False,
        )
        self.assertFalse(lat_422.allowed)
        self.assertEqual(lat_422.http_status, 422)
        self.assertEqual(
            lat_422.eucp_ebl_lane,
            "LATE_PRESENTATION_21D_OR_EBL_CONTROL_INVALID",
        )

        # 4. Web IQ detects vessel IMO sanctions port call or non-MLETR law -> 451 blocked in 280ms
        san_451 = evaluate_b2b_eucp_ebl_letter_of_credit_policy(
            webiq_mletr_jurisdiction_and_vessel_sanctions_clean=False,
        )
        self.assertFalse(san_451.allowed)
        self.assertEqual(san_451.http_status, 451)

        # 5. Web IQ credits DCSA eBL zero-demurrage & forfaiting discount saving $64,400 ($855,600 net) -> 409 Confirm
        sav_409 = evaluate_b2b_eucp_ebl_letter_of_credit_policy(
            ebl_zero_demurrage_and_forfaiting_discount_savings_cents=6440000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_lc_batch_cents, 85560000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_eucp_ebl_letter_of_credit_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-eucp-ebl-letter-of-credit-sandbox", demo_zh)

    def test_agentic_bnpl_installment_mdr_margin_guard_partial_refund_reamortization_mandate_vs_margin_wipeout_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_bnpl_installment_mdr_policy,
        )

        # 1. Verified post-MDR margin floor + carrier scan autopay pause + tail-first exact -> 200 OK ($520,000)
        commit_ok = evaluate_agentic_bnpl_installment_mdr_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_bnpl_batch_cents, 52000000)

        # 2. Thin-margin SKU subsidized 0% APR loss or bracketing -> 403 blocked in 11ms
        mdr_403 = evaluate_agentic_bnpl_installment_mdr_policy(
            post_mdr_net_margin_floor_and_anti_bracketing_verified=False,
        )
        self.assertFalse(mdr_403.allowed)
        self.assertEqual(mdr_403.http_status, 403)
        self.assertEqual(
            mdr_403.bnpl_mdr_lane,
            "BNPL_MDR_MARGIN_EROSE_OR_BRACKETING_BLOCKED",
        )

        # 3. Active autopay during return transit or non-tail-first schedule drift -> 422 blocked in 14ms
        ref_422 = evaluate_agentic_bnpl_installment_mdr_policy(
            carrier_dropoff_autopay_pause_and_tail_first_reamortization_exact=False,
        )
        self.assertFalse(ref_422.allowed)
        self.assertEqual(ref_422.http_status, 422)
        self.assertEqual(
            ref_422.bnpl_mdr_lane,
            "PARTIAL_REFUND_REAMORTIZATION_OR_AUTOPAY_PAUSE_FAILED",
        )

        # 4. Web IQ detects missing CFPB Reg Z disclosure or state APR cap breach -> 451 blocked in 280ms
        reg_451 = evaluate_agentic_bnpl_installment_mdr_policy(
            webiq_cfpb_reg_z_disclosure_and_state_usury_cap_clean=False,
        )
        self.assertFalse(reg_451.allowed)
        self.assertEqual(reg_451.http_status, 451)

        # 5. Web IQ routes thin-margin carts to consumer-APR or A2A saving $23,400 ($496,600 net) -> 409 Confirm
        sav_409 = evaluate_agentic_bnpl_installment_mdr_policy(
            dynamic_mdr_arbitrage_and_a2a_routing_savings_cents=2340000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_bnpl_batch_cents, 49660000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_bnpl_installment_mdr_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-bnpl-installment-mdr-sandbox", demo_zh)

    def test_b2b_ers_self_billing_evaluated_receipt_settlement_mandate_vs_supplier_invoice_exception_duplicate_vat_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_ers_self_billing_policy,
        )

        # 1. Verified active SBA + zero duplicate supplier invoice + calibrated net GR -> 200 OK ($680,000)
        commit_ok = evaluate_b2b_ers_self_billing_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ers_batch_cents, 68000000)

        # 2. Rogue supplier EDI 810 invoice on ERS PO or expired SBA -> 403 blocked in 11ms
        dup_403 = evaluate_b2b_ers_self_billing_policy(
            active_sba_agreement_and_zero_duplicate_supplier_invoice_verified=False,
        )
        self.assertFalse(dup_403.allowed)
        self.assertEqual(dup_403.http_status, 403)
        self.assertEqual(
            dup_403.ers_self_billing_lane,
            "DUPLICATE_SUPPLIER_INVOICE_OR_EXPIRED_SBA_BLOCKED",
        )

        # 3. Dock net weight variance > 2% tolerance or unlinked PO price -> 422 blocked in 14ms
        wgt_422 = evaluate_b2b_ers_self_billing_policy(
            calibrated_dock_net_gr_within_tolerance_and_po_price_locked=False,
        )
        self.assertFalse(wgt_422.allowed)
        self.assertEqual(wgt_422.http_status, 422)
        self.assertEqual(
            wgt_422.ers_self_billing_lane,
            "GR_WEIGHT_VARIANCE_OR_PO_PRICE_DRIFT_FAILED",
        )

        # 4. Web IQ detects deregistered supplier VAT ID or missing Art. 224 legend -> 451 blocked in 280ms
        vat_451 = evaluate_b2b_ers_self_billing_policy(
            webiq_supplier_vat_active_and_art224_self_billing_legend_clean=False,
        )
        self.assertFalse(vat_451.allowed)
        self.assertEqual(vat_451.http_status, 451)

        # 5. Web IQ credits zero-touch AP & JIT early-pay discount saving $34,000 ($646,000 net) -> 409 Confirm
        sav_409 = evaluate_b2b_ers_self_billing_policy(
            zero_touch_ap_and_jit_early_pay_discount_savings_cents=3400000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ers_batch_cents, 64600000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_ers_self_billing_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-ers-self-billing-sandbox", demo_zh)

    def test_agentic_multi_psp_smart_routing_local_acquiring_mac_retry_mandate_vs_excessive_retry_fines_crossborder_fee_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_multi_psp_smart_routing_policy,
        )

        # 1. Verified 8-digit BIN local acquiring + zero hard-decline retry + 0400 reversal -> 200 OK ($840,000)
        commit_ok = evaluate_agentic_multi_psp_smart_routing_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_psp_batch_cents, 84000000)

        # 2. Cross-PSP retry on Visa Cat-1 or Mastercard MAC 03/21 hard decline -> 403 blocked in 11ms
        mac_403 = evaluate_agentic_multi_psp_smart_routing_policy(
            zero_hard_decline_cat1_or_mac03_retry_verified=False,
        )
        self.assertFalse(mac_403.allowed)
        self.assertEqual(mac_403.http_status, 403)
        self.assertEqual(
            mac_403.multi_psp_routing_lane,
            "HARD_DECLINE_CAT1_OR_MAC03_RETRY_FORBIDDEN",
        )

        # 3. Unreversed primary timeout or >15 retries in 30 days -> 422 blocked in 14ms
        rev_422 = evaluate_agentic_multi_psp_smart_routing_policy(
            primary_timeout_0400_reversed_and_rolling_30d_under_15_retries=False,
        )
        self.assertFalse(rev_422.allowed)
        self.assertEqual(rev_422.http_status, 422)
        self.assertEqual(
            rev_422.multi_psp_routing_lane,
            "UNREVERSED_TIMEOUT_CASCADE_OR_15X_CAP_EXCEEDED",
        )

        # 4. Web IQ detects unlicensed local acquiring MID or missing cryptogram -> 451 blocked in 280ms
        lic_451 = evaluate_agentic_multi_psp_smart_routing_policy(
            webiq_local_acquiring_license_and_scheme_cryptogram_clean=False,
        )
        self.assertFalse(lic_451.allowed)
        self.assertEqual(lic_451.http_status, 451)

        # 5. Web IQ enables 8-digit BIN local acquiring & smart cascade saving $50,400 ($789,600 net) -> 409 Confirm
        sav_409 = evaluate_agentic_multi_psp_smart_routing_policy(
            bin_local_acquiring_fee_and_false_decline_recovery_savings_cents=5040000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_psp_batch_cents, 78960000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_multi_psp_smart_routing_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-multi-psp-smart-routing-sandbox", demo_zh)

    def test_agentic_cross_border_ddp_ioss_type86_htsus_customs_mandate_vs_ddu_delivery_refusal_undervaluation_fine_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_cross_border_ddp_customs_policy,
        )

        # 1. Verified 1:1 payment-to-customs value + EU €150 IOSS H7 + US 10-digit HTSUS -> 200 OK ($610,000)
        commit_ok = evaluate_agentic_cross_border_ddp_customs_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ddp_batch_cents, 61000000)

        # 2. Customs invoice undervaluation or same-day $800 split evasion -> 403 blocked in 11ms
        val_403 = evaluate_agentic_cross_border_ddp_customs_policy(
            customs_declared_equals_net_paid_and_zero_split_evasion_verified=False,
        )
        self.assertFalse(val_403.allowed)
        self.assertEqual(val_403.http_status, 403)
        self.assertEqual(
            val_403.ddp_customs_lane,
            "CUSTOMS_UNDERVALUATION_OR_SPLIT_EVASION_BLOCKED",
        )

        # 3. EU >€150 misrouted to IOSS or missing 10-digit HTSUS -> 422 blocked in 14ms
        ios_422 = evaluate_agentic_cross_border_ddp_customs_policy(
            eu_ioss_150eur_encrypted_h7_and_us_10digit_htsus_valid=False,
        )
        self.assertFalse(ios_422.allowed)
        self.assertEqual(ios_422.http_status, 422)
        self.assertEqual(
            ios_422.ddp_customs_lane,
            "IOSS_150EUR_BREACH_OR_MISSING_10DIGIT_HTSUS",
        )

        # 4. Web IQ detects TARIC antidumping duty or CBP PGA hold -> 451 blocked in 280ms
        pga_451 = evaluate_agentic_cross_border_ddp_customs_policy(
            webiq_taric_antidumping_and_cbp_pga_clearance_clean=False,
        )
        self.assertFalse(pga_451.allowed)
        self.assertEqual(pga_451.http_status, 451)

        # 5. Web IQ enables full DDP + IOSS H7 eliminating refusals & fees saving $42,700 ($567,300 net) -> 409 Confirm
        sav_409 = evaluate_agentic_cross_border_ddp_customs_policy(
            ddp_ioss_carrier_fee_and_zero_refusal_savings_cents=4270000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ddp_batch_cents, 56730000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_cross_border_ddp_customs_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-cross-border-ddp-customs-sandbox", demo_zh)

    def test_agentic_gift_card_stored_value_enumeration_aml_mandate_vs_card_draining_triangulation_laundering_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_gift_card_stored_value_policy,
        )

        # 1. Verified HSM Argon2id + zero tender loop + <=$2,000 FinCEN cap -> 200 OK ($490,000)
        commit_ok = evaluate_agentic_gift_card_stored_value_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_gift_card_batch_cents, 49000000)

        # 2. Botnet enumeration, GC/BNPL-to-GC loop, or >$2,000 FinCEN cap breach -> 403 blocked in 11ms
        enm_403 = evaluate_agentic_gift_card_stored_value_policy(
            hsm_argon2id_pin_zero_loop_and_fincen_2000usd_cap_verified=False,
        )
        self.assertFalse(enm_403.allowed)
        self.assertEqual(enm_403.http_status, 403)
        self.assertEqual(
            enm_403.gift_card_aml_lane,
            "ENUMERATION_OR_LOOP_OR_FINCEN_2000USD_CAP_BLOCKED",
        )

        # 3. Stolen-card e-GC redeemed 90s later on burner account for liquid goods -> 422 blocked in 14ms
        tri_422 = evaluate_agentic_gift_card_stored_value_policy(
            cross_account_triangulation_cooling_off_and_fido2_passed=False,
        )
        self.assertFalse(tri_422.allowed)
        self.assertEqual(tri_422.http_status, 422)
        self.assertEqual(
            tri_422.gift_card_aml_lane,
            "TRIANGULATION_CARD_TO_GIFT_LAUNDERING_HOLD",
        )

        # 4. Web IQ detects <5-year expiry or illegal dormancy fee under CARD Act -> 451 blocked in 280ms
        act_451 = evaluate_agentic_gift_card_stored_value_policy(
            webiq_us_card_act_5yr_expiry_and_escheatment_clean=False,
        )
        self.assertFalse(act_451.allowed)
        self.assertEqual(act_451.http_status, 451)

        # 5. Web IQ credits closed-loop float & anti-drain saving $39,200 ($450,800 net) -> 409 Confirm
        sav_409 = evaluate_agentic_gift_card_stored_value_policy(
            closed_loop_acquiring_fee_and_drain_prevention_savings_cents=3920000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_gift_card_batch_cents, 45080000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_gift_card_stored_value_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-gift-card-stored-value-sandbox", demo_zh)

    def test_b2b_saas_hybrid_usage_proration_asc606_revenue_recognition_mandate_vs_penny_drift_deferred_revenue_drain_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_saas_hybrid_asc606_policy,
        )

        # 1. Verified exact-second integer proration + credit-note downgrade + FEFO + ASC 606 -> 200 OK ($720,000)
        commit_ok = evaluate_b2b_saas_hybrid_asc606_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_saas_batch_cents, 72000000)

        # 2. Hit-and-run mid-cycle downgrade cash refund or float proration drift -> 403 blocked in 11ms
        prr_403 = evaluate_b2b_saas_hybrid_asc606_policy(
            exact_second_integer_proration_and_credit_note_downgrade_verified=False,
        )
        self.assertFalse(prr_403.allowed)
        self.assertEqual(prr_403.http_status, 403)
        self.assertEqual(
            prr_403.saas_asc606_lane,
            "MID_CYCLE_DOWNGRADE_CASH_DRAIN_OR_PRORATION_DRIFT_BLOCKED",
        )

        # 3. Inverted bucket waterfall or premature Day-1 annual RevRec -> 422 blocked in 14ms
        rev_422 = evaluate_b2b_saas_hybrid_asc606_policy(
            fefo_bucket_waterfall_and_deferred_revenue_lock_valid=False,
        )
        self.assertFalse(rev_422.allowed)
        self.assertEqual(rev_422.http_status, 422)
        self.assertEqual(
            rev_422.saas_asc606_lane,
            "BUCKET_WATERFALL_INVERSION_OR_PREMATURE_REVREC_FAILED",
        )

        # 4. Web IQ detects distorted ASC 606 SSP corridor across POBs -> 451 blocked in 280ms
        ssp_451 = evaluate_b2b_saas_hybrid_asc606_policy(
            webiq_asc606_ssp_corridor_and_audit_trail_clean=False,
        )
        self.assertFalse(ssp_451.allowed)
        self.assertEqual(ssp_451.http_status, 451)

        # 5. Web IQ enables auto-tier commit rollover & SSP automation saving $46,800 ($673,200 net) -> 409 Confirm
        sav_409 = evaluate_b2b_saas_hybrid_asc606_policy(
            auto_tier_commit_rollover_and_audit_savings_cents=4680000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_saas_batch_cents, 67320000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_saas_hybrid_asc606_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-saas-hybrid-asc606-sandbox", demo_zh)

    def test_agentic_reverse_logistics_rma_instant_refund_weight_imei_mandate_vs_box_of_rocks_ftid_return_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_reverse_logistics_rma_policy,
        )

        # 1. Verified hub DWS weight <=5% + dock geohash + 1:1 IMEI parity -> 200 OK ($580,000)
        commit_ok = evaluate_agentic_reverse_logistics_rma_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_rma_batch_cents, 58000000)

        # 2. FTID 20g empty envelope to same-ZIP cafe or weight mismatch -> 403 blocked in 11ms
        ftd_403 = evaluate_agentic_reverse_logistics_rma_policy(
            hub_dws_weight_within_5pct_and_dock_geohash_verified=False,
        )
        self.assertFalse(ftd_403.allowed)
        self.assertEqual(ftd_403.http_status, 403)
        self.assertEqual(
            ftd_403.rma_refund_lane,
            "FTID_EMPTY_ENVELOPE_OR_WEIGHT_MISMATCH_BLOCKED",
        )

        # 3. Inbound vs. outbound IMEI/serial hash mismatch (junk unit swap) -> 422 blocked in 14ms
        swp_422 = evaluate_agentic_reverse_logistics_rma_policy(
            inbound_serial_imei_hash_matches_outbound_verified=False,
        )
        self.assertFalse(swp_422.allowed)
        self.assertEqual(swp_422.http_status, 422)
        self.assertEqual(
            swp_422.rma_refund_lane,
            "SERIAL_IMEI_SWAP_OR_COUNTERFEIT_RETURN_REJECTED",
        )

        # 4. Web IQ detects UN3481 lithium-battery air breach or EU Art. 14 hold -> 451 blocked in 280ms
        bat_451 = evaluate_agentic_reverse_logistics_rma_policy(
            webiq_consumer_rights_depreciation_and_hazmat_battery_clean=False,
        )
        self.assertFalse(bat_451.allowed)
        self.assertEqual(bat_451.http_status, 451)

        # 5. Web IQ enables Instant Exchange bonus & anti-FTID saving $46,400 ($533,600 net) -> 409 Confirm
        sav_409 = evaluate_agentic_reverse_logistics_rma_policy(
            instant_exchange_credit_retention_and_ftid_savings_cents=4640000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_rma_batch_cents, 53360000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_reverse_logistics_rma_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-reverse-logistics-rma-sandbox", demo_zh)

    def test_agentic_hospitality_lodging_car_rental_incremental_auth_reversal_mandate_vs_deposit_hold_delayed_chargeback_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_hospitality_incremental_auth_policy,
        )

        # 1. Verified root TID capture + instant 0420 deposit reversal + zero damage fine -> 200 OK ($650,000)
        commit_ok = evaluate_agentic_hospitality_incremental_auth_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_hospitality_batch_cents, 65000000)

        # 2. Unlinked standalone Sale (30d double hold) or >15% overage without incremental auth -> 403 blocked in 11ms
        lck_403 = evaluate_agentic_hospitality_incremental_auth_policy(
            root_tid_capture_and_instant_0420_deposit_reversal_verified=False,
        )
        self.assertFalse(lck_403.allowed)
        self.assertEqual(lck_403.http_status, 403)
        self.assertEqual(
            lck_403.hospitality_auth_lane,
            "ORPHANED_HOLD_DOUBLE_LOCK_OR_MISSING_INCREMENTAL_AUTH_BLOCKED",
        )

        # 3. Unconsented damage/smoking fine capture or multi-night No-Show -> 422 blocked in 14ms
        dmg_422 = evaluate_agentic_hospitality_incremental_auth_policy(
            zero_unconsented_damage_smoking_fine_and_1night_noshow_cap_valid=False,
        )
        self.assertFalse(dmg_422.allowed)
        self.assertEqual(dmg_422.http_status, 422)
        self.assertEqual(
            dmg_422.hospitality_auth_lane,
            "PROHIBITED_DAMAGE_FINE_CAPTURE_OR_NOSHOW_OVERCHARGE_REJECTED",
        )

        # 4. Web IQ detects missing MCC 7011/7512 folio schema or >90d delayed window -> 451 blocked in 280ms
        fol_451 = evaluate_agentic_hospitality_incremental_auth_policy(
            webiq_mcc_7011_7512_folio_schema_and_90d_window_clean=False,
        )
        self.assertFalse(fol_451.allowed)
        self.assertEqual(fol_451.http_status, 451)

        # 5. Web IQ enables enhanced folio passthrough & dispute avoidance saving $39,000 ($611,000 net) -> 409 Confirm
        sav_409 = evaluate_agentic_hospitality_incremental_auth_policy(
            enhanced_folio_interchange_and_dispute_avoidance_savings_cents=3900000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_hospitality_batch_cents, 61100000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_hospitality_incremental_auth_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-hospitality-incremental-auth-sandbox", demo_zh)


    def test_agentic_creator_payout_1099k_w8ben_backup_withholding_mandate_vs_unverified_tin_penalty_liability_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_creator_payout_1099k_w8ben_policy,
        )

        # 1. Verified IRS TIN match + active W-8BEN + exact royalty/service split -> 200 OK ($550,000)
        commit_ok = evaluate_agentic_creator_payout_1099k_w8ben_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_creator_payout_cents, 55000000)

        # 2. Unverified TIN / missing W-8BEN attempting 100% unwithheld payout -> 403 blocked in 11ms
        tin_403 = evaluate_agentic_creator_payout_1099k_w8ben_policy(
            irs_tin_matched_or_24pct_backup_withholding_escrowed=False,
        )
        self.assertFalse(tin_403.allowed)
        self.assertEqual(tin_403.http_status, 403)
        self.assertEqual(
            tin_403.creator_payout_lane,
            "UNVERIFIED_TIN_OR_MISSING_W8BEN_FULL_PAYOUT_BLOCKED",
        )

        # 3. Expired W-8BEN (>3 calendar years) or US-source royalty misclassified -> 422 blocked in 14ms
        w8b_422 = evaluate_agentic_creator_payout_1099k_w8ben_policy(
            w8ben_within_3yr_expiry_and_us_royalty_sourcing_split_valid=False,
        )
        self.assertFalse(w8b_422.allowed)
        self.assertEqual(w8b_422.http_status, 422)
        self.assertEqual(
            w8b_422.creator_payout_lane,
            "EXPIRED_W8BEN_3YR_OR_US_ROYALTY_MISCLASSIFIED",
        )

        # 4. Web IQ detects invalid treaty LOB claim or missed $600 state 1099-K -> 451 blocked in 280ms
        trt_451 = evaluate_agentic_creator_payout_1099k_w8ben_policy(
            webiq_treaty_lob_and_state_600usd_1099k_threshold_clean=False,
        )
        self.assertFalse(trt_451.allowed)
        self.assertEqual(trt_451.http_status, 451)

        # 5. Web IQ enforces 24% backup escrow & treaty relief saving $44,000 ($506,000 net) -> 409 Confirm
        sav_409 = evaluate_agentic_creator_payout_1099k_w8ben_policy(
            backup_escrow_and_treaty_relief_savings_cents=4400000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_creator_payout_cents, 50600000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_creator_payout_1099k_w8ben_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-creator-payout-1099k-w8ben-sandbox", demo_zh)

    def test_agentic_iap_web_out_dma_anti_steering_consumption_api_mandate_vs_30pct_appstore_tax_refund_abuse_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_iap_web_out_policy,
        )

        # 1. Verified compliant Web-to-App / signed external link + <500ms consumption reply -> 200 OK ($790,000)
        commit_ok = evaluate_agentic_iap_web_out_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_iap_batch_cents, 79000000)

        # 2. Rogue unsigned in-app WebView violating Guideline 3.1.1 -> 403 blocked in 11ms
        str_403 = evaluate_agentic_iap_web_out_policy(
            compliant_web_to_app_313b_or_signed_external_link_entitlement=False,
        )
        self.assertFalse(str_403.allowed)
        self.assertEqual(str_403.http_status, 403)
        self.assertEqual(
            str_403.iap_web_out_lane,
            "UNAUTHORIZED_STEERING_WEBVIEW_OR_GUIDELINE_311_BLOCKED",
        )

        # 3. Missed 12h CONSUMPTION_REQUEST telemetry reply or zombie VIP leak -> 422 blocked in 14ms
        cns_422 = evaluate_agentic_iap_web_out_policy(
            apple_consumption_request_12h_answered_and_refund_jws_revoked=False,
        )
        self.assertFalse(cns_422.allowed)
        self.assertEqual(cns_422.http_status, 422)
        self.assertEqual(
            cns_422.iap_web_out_lane,
            "CONSUMPTION_TELEMETRY_MISSED_OR_ZOMBIE_ENTITLEMENT_LEAK",
        )

        # 4. Web IQ detects negative EU DMA €0.50 CTF unit economics -> 451 blocked in 280ms
        ctf_451 = evaluate_agentic_iap_web_out_policy(
            webiq_dma_ctf_unit_economics_and_storefront_modal_clean=False,
        )
        self.assertFalse(ctf_451.allowed)
        self.assertEqual(ctf_451.http_status, 451)

        # 5. Web IQ enables Web-to-App 2.9% funnel & Consumption API defense saving $63,200 ($726,800 net) -> 409 Confirm
        sav_409 = evaluate_agentic_iap_web_out_policy(
            web_out_commission_arbitrage_and_refund_defense_savings_cents=6320000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_iap_batch_cents, 72680000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_iap_web_out_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-iap-web-out-sandbox", demo_zh)

    def test_agentic_price_match_post_purchase_guarantee_webiq_gtin_mandate_vs_fake_screenshot_spoof_competitor_drain_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_price_match_guarantee_policy,
        )

        # 1. Verified whitelisted 1P domain + live GTIN-14 InStock + exact net-paid delta -> 200 OK ($470,000)
        commit_ok = evaluate_agentic_price_match_guarantee_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_price_match_batch_cents, 47000000)

        # 2. F12 DOM-edited screenshot or spoofed non-whitelisted URL -> 403 blocked in 11ms
        scr_403 = evaluate_agentic_price_match_guarantee_policy(
            zero_screenshot_trust_and_whitelisted_1p_domain_verified=False,
        )
        self.assertFalse(scr_403.allowed)
        self.assertEqual(scr_403.http_status, 403)
        self.assertEqual(
            scr_403.price_match_lane,
            "UNVERIFIED_SCREENSHOT_OR_SPOOFED_COMPETITOR_DOMAIN_BLOCKED",
        )

        # 3. Promo coupon / free-gift double-dip or >30% glitch cap -> 422 blocked in 14ms
        dip_422 = evaluate_agentic_price_match_guarantee_policy(
            net_paid_minus_gift_delta_positive_and_within_30pct_cap=False,
        )
        self.assertFalse(dip_422.allowed)
        self.assertEqual(dip_422.http_status, 422)
        self.assertEqual(
            dip_422.price_match_lane,
            "PROMO_GIFT_DOUBLE_DIP_OR_CAP_EXCEEDED_REJECTED",
        )

        # 4. Web IQ detects refurbished GTIN mismatch, 3P seller, or Out-of-Stock -> 451 blocked in 280ms
        gtn_451 = evaluate_agentic_price_match_guarantee_policy(
            webiq_gtin14_new_condition_and_1p_instock_clean=False,
        )
        self.assertFalse(gtn_451.allowed)
        self.assertEqual(gtn_451.http_status, 451)

        # 5. Web IQ blocks screenshot/OOS fraud & converts valid delta to +10% credit saving $37,600 ($432,400 net) -> 409 Confirm
        sav_409 = evaluate_agentic_price_match_guarantee_policy(
            webiq_fraud_block_and_store_credit_retention_savings_cents=3760000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_price_match_batch_cents, 43240000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_price_match_guarantee_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-price-match-guarantee-sandbox", demo_zh)


    def test_agentic_age_restricted_mdl_iso18013_zkp_adult_signature_mandate_vs_self_attestation_id_leak_fine_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_age_restricted_mdl_policy,
        )

        # 1. Verified ISO 18013-5 mDL age_over_21 + 0-byte PII + ASR 21+ + Wet state -> 200 OK ($410,000)
        commit_ok = evaluate_agentic_age_restricted_mdl_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_age_restricted_batch_cents, 41000000)

        # 2. Unverified checkbox self-attestation or storing raw ID JPEGs -> 403 blocked in 11ms
        slf_403 = evaluate_agentic_age_restricted_mdl_policy(
            iso18013_mdl_age_over_21_and_zero_raw_id_pii_storage_verified=False,
        )
        self.assertFalse(slf_403.allowed)
        self.assertEqual(slf_403.http_status, 403)
        self.assertEqual(
            slf_403.age_restricted_lane,
            "SELF_ATTESTATION_ILLEGAL_OR_RAW_ID_PII_STORAGE_BLOCKED",
        )

        # 3. Missing carrier ASR 21+ adult signature or unattended locker/P.O. Box -> 422 blocked in 14ms
        asr_422 = evaluate_agentic_age_restricted_mdl_policy(
            carrier_asr21_adult_signature_and_no_locker_pobox_locked=False,
        )
        self.assertFalse(asr_422.allowed)
        self.assertEqual(asr_422.http_status, 422)
        self.assertEqual(
            asr_422.age_restricted_lane,
            "MISSING_CARRIER_ASR21_OR_UNATTENDED_LOCKER_REJECTED",
        )

        # 4. Web IQ detects prohibited Dry State (UT/MS/DE) or gallonage quota breach -> 451 blocked in 280ms
        dry_451 = evaluate_agentic_age_restricted_mdl_policy(
            webiq_wet_state_zip4_permit_and_gallonage_quota_clean=False,
        )
        self.assertFalse(dry_451.allowed)
        self.assertEqual(dry_451.http_status, 451)

        # 5. Web IQ enables 1-tap mDL ZKP saving $32,800 ($377,200 net) -> 409 Confirm
        sav_409 = evaluate_agentic_age_restricted_mdl_policy(
            w3c_mdl_conversion_lift_and_ocr_fee_avoidance_savings_cents=3280000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_age_restricted_batch_cents, 37720000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_age_restricted_mdl_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-age-restricted-mdl-sandbox", demo_zh)


    def test_agentic_surge_pricing_emergency_anti_gouging_cap_price_lock_mandate_vs_disaster_5x_multiplier_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_surge_pricing_anti_gouging_policy,
        )

        # 1. Verified <=1.10x emergency clamp + 300s HMAC price-lock + FTC upfront -> 200 OK ($480,000)
        commit_ok = evaluate_agentic_surge_pricing_anti_gouging_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_surge_batch_cents, 48000000)

        # 2. Algorithmic 4.5x surge during declared State of Emergency -> 403 blocked in 11ms
        gou_403 = evaluate_agentic_surge_pricing_anti_gouging_policy(
            emergency_state_surge_clamped_under_10pct_of_30d_baseline=False,
        )
        self.assertFalse(gou_403.allowed)
        self.assertEqual(gou_403.http_status, 403)
        self.assertEqual(
            gou_403.surge_pricing_lane,
            "EMERGENCY_PRICE_GOUGING_MULTIPLIER_BREACH_BLOCKED",
        )

        # 3. Mid-checkout price jump ($24 -> $49 on click) or tampered baseline -> 422 blocked in 14ms
        jmp_422 = evaluate_agentic_surge_pricing_anti_gouging_policy(
            captured_amount_equals_300s_hmac_price_lock_quote=False,
        )
        self.assertFalse(jmp_422.allowed)
        self.assertEqual(jmp_422.http_status, 422)
        self.assertEqual(
            jmp_422.surge_pricing_lane,
            "MID_CHECKOUT_PRICE_JUMP_OR_BASELINE_MANIPULATION_REJECTED",
        )

        # 4. Web IQ detects active post-disaster proclamation extension or FTC drip fee -> 451 blocked in 280ms
        ext_451 = evaluate_agentic_surge_pricing_anti_gouging_policy(
            webiq_fema_proclamation_extension_and_ftc_upfront_fee_clean=False,
        )
        self.assertFalse(ext_451.allowed)
        self.assertEqual(ext_451.http_status, 451)

        # 5. Web IQ enforces emergency clamp & 300s price lock saving $38,400 ($441,600 net) -> 409 Confirm
        sav_409 = evaluate_agentic_surge_pricing_anti_gouging_policy(
            emergency_clamp_fine_avoidance_and_price_lock_savings_cents=3840000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_surge_batch_cents, 44160000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_surge_pricing_anti_gouging_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-surge-pricing-anti-gouging-sandbox", demo_zh)

    def test_agentic_airline_ndc_one_order_adm_dot24h_refund_mandate_vs_skiplagging_churning_adm_penalty_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_airline_ndc_adm_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Zero skiplagging/churning + US DOT cash refund + exact YQ vs. gov tax split ($690,000.00) -> 200 OK
        commit_ok = evaluate_agentic_airline_ndc_adm_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_airline_batch_cents, 69000000)

        # 2. Hidden-city skiplagging or >2x PNR churning -> 403 Blocked
        adm_403 = evaluate_agentic_airline_ndc_adm_policy(
            zero_skiplagging_and_pnr_churn_le_2_verified=False,
        )
        self.assertFalse(adm_403.allowed)
        self.assertEqual(adm_403.http_status, 403)
        self.assertEqual(
            adm_403.decision_code,
            "SKIPLAGGING_OR_PNR_CHURNING_ADM_VIOLATION_BLOCKED",
        )

        # 3. Voucher forced on >=3h delayed flight or YQ/government tax miscalculation -> 422 Blocked
        dot_422 = evaluate_agentic_airline_ndc_adm_policy(
            dot_cash_refund_and_yq_gov_tax_split_exact=False,
        )
        self.assertFalse(dot_422.allowed)
        self.assertEqual(dot_422.http_status, 422)
        self.assertEqual(
            dot_422.decision_code,
            "DOT_CASH_REFUND_DENIED_OR_YQ_GOVERNMENT_TAX_MISCALCULATION",
        )

        # 4. Missing IATA Resolution 830d passenger contact SSR -> 451 Hold
        ssr_451 = evaluate_agentic_airline_ndc_adm_policy(
            webiq_iata_830d_contact_and_dot_disclosure_clean=False,
        )
        self.assertFalse(ssr_451.allowed)
        self.assertEqual(ssr_451.http_status, 451)

        # 5. Web IQ routes via IATA NDC v21.3 waiving GDS fees & ADMs saving $55,200 ($634,800 net) -> 409 Confirm
        sav_409 = evaluate_agentic_airline_ndc_adm_policy(
            ndc_direct_surcharge_waiver_and_zero_adm_savings_cents=5520000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_airline_batch_cents, 63480000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_airline_ndc_adm_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-airline-ndc-adm-sandbox", demo_zh)


    def test_agentic_qsr_grocery_catch_weight_prep_cutoff_commission_cap_mandate_vs_post_prep_cancel_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_qsr_grocery_catch_weight_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. KDS prep cutoff & scale-seal verified + 1x +15% catch-weight capture + <=15% fee cap ($370,000.00) -> 200 OK
        commit_ok = evaluate_agentic_qsr_grocery_catch_weight_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_qsr_grocery_batch_cents, 37000000)

        # 2. Free cancel after KDS_FIRED or false missing-entree claim on weight-verified sealed bag -> 403 Blocked
        kds_403 = evaluate_agentic_qsr_grocery_catch_weight_policy(
            kds_prep_cutoff_and_scale_seal_parity_verified=False,
        )
        self.assertFalse(kds_403.allowed)
        self.assertEqual(kds_403.http_status, 403)
        self.assertEqual(
            kds_403.decision_code,
            "POST_KDS_PREP_FREE_CANCEL_OR_WEIGHT_VERIFIED_MISSING_ITEM_FRAUD_BLOCKED",
        )

        # 3. Second separate charge for catch-weight delta or over +15% cushion -> 422 Blocked
        wgt_422 = evaluate_agentic_qsr_grocery_catch_weight_policy(
            catch_weight_single_root_tid_le_15pct_verified=False,
        )
        self.assertFalse(wgt_422.allowed)
        self.assertEqual(wgt_422.http_status, 422)
        self.assertEqual(
            wgt_422.decision_code,
            "CATCH_WEIGHT_SECOND_CHARGE_OR_OVER_15PCT_CUSHION_BREACH",
        )

        # 4. Exceeding municipal 15% delivery commission cap or missing FDA allergen disclosure -> 451 Hold
        cap_451 = evaluate_agentic_qsr_grocery_catch_weight_policy(
            webiq_municipal_15pct_commission_cap_and_fda_clean=False,
        )
        self.assertFalse(cap_451.allowed)
        self.assertEqual(cap_451.http_status, 451)

        # 5. Web IQ enables 1x +15% catch-weight capture & scale-to-seal fraud defense saving $29,600 ($340,400 net) -> 409 Confirm
        sav_409 = evaluate_agentic_qsr_grocery_catch_weight_policy(
            catch_weight_single_capture_and_seal_savings_cents=2960000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_qsr_grocery_batch_cents, 34040000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_qsr_grocery_catch_weight_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-qsr-grocery-catch-weight-sandbox", demo_zh)

    def test_agentic_loyalty_points_miles_ato_breakage_asc606_mandate_vs_mileage_broker_drain_liability_shock_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_loyalty_points_asc606_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. FIDO2 + >=72h nominee + ASC 606 CPP <=1.25c + original-expiry refund lock ($540,000.00) -> 200 OK
        commit_ok = evaluate_agentic_loyalty_points_asc606_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_loyalty_batch_cents, 54000000)

        # 2. Newly added nominee <72h (Mileage Broker ATO) or gift-card cashout -> 403 Blocked
        ato_403 = evaluate_agentic_loyalty_points_asc606_policy(
            fido2_and_nominee_ge_72h_non_giftcard_verified=False,
        )
        self.assertFalse(ato_403.allowed)
        self.assertEqual(ato_403.http_status, 403)
        self.assertEqual(
            ato_403.decision_code,
            "LOYALTY_ATO_NOMINEE_UNDER_72H_OR_GIFT_CARD_CASHOUT_BLOCKED",
        )

        # 3. Unfunded 2.5c/pt CPP breaching ASC 606 reserve or refund expiry laundering -> 422 Blocked
        cpp_422 = evaluate_agentic_loyalty_points_asc606_policy(
            asc606_cpp_ceiling_and_original_expiry_refund_verified=False,
        )
        self.assertFalse(cpp_422.allowed)
        self.assertEqual(cpp_422.http_status, 422)
        self.assertEqual(
            cpp_422.decision_code,
            "ASC606_CPP_LIABILITY_CEILING_BREACH_OR_EXPIRY_LAUNDERING",
        )

        # 4. Unlawful forfeiture of cash-purchased points or silent DOT devaluation -> 451 Hold
        exp_451 = evaluate_agentic_loyalty_points_asc606_policy(
            webiq_purchased_points_segregated_and_dot_notice_clean=False,
        )
        self.assertFalse(exp_451.allowed)
        self.assertEqual(exp_451.http_status, 451)

        # 5. Web IQ enforces dynamic CPP clamping & 72h nominee lock saving $43,200 ($496,800 net) -> 409 Confirm
        sav_409 = evaluate_agentic_loyalty_points_asc606_policy(
            dynamic_cpp_clamp_and_anti_broker_savings_cents=4320000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_loyalty_batch_cents, 49680000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_loyalty_points_asc606_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-loyalty-points-asc606-sandbox", demo_zh)


    def test_agentic_event_ticketing_rotating_safetix_resale_cap_escrow_mandate_vs_scalper_bot_screenshot_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_event_ticketing_escrow_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. 15s TOTP re-issued + <=1.10x resale cap + Doors_Open+24h escrow + FTC all-in ($450,000.00) -> 200 OK
        commit_ok = evaluate_agentic_event_ticketing_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_ticketing_batch_cents, 45000000)

        # 2. Static PDF/screenshot upload or BOTS Act scalper bot -> 403 Blocked
        pdf_403 = evaluate_agentic_event_ticketing_escrow_policy(
            totp_15s_reissued_and_bots_act_clean=False,
        )
        self.assertFalse(pdf_403.allowed)
        self.assertEqual(pdf_403.http_status, 403)
        self.assertEqual(
            pdf_403.decision_code,
            "STATIC_PDF_SCREENSHOT_TICKET_OR_BOTS_ACT_SCALPER_BLOCKED",
        )

        # 3. Resale price >1.10x face-value cap or pre-event seller payout -> 422 Blocked
        cap_422 = evaluate_agentic_event_ticketing_escrow_policy(
            resale_le_110pct_cap_and_post_event_escrow_verified=False,
        )
        self.assertFalse(cap_422.allowed)
        self.assertEqual(cap_422.http_status, 422)
        self.assertEqual(
            cap_422.decision_code,
            "RESALE_PRICE_CAP_EXCEEDED_OR_PRE_EVENT_PAYOUT_ESCROW_BREACH",
        )

        # 4. FTC 16 CFR Part 464 drip-pricing junk fee violation -> 451 Hold
        ftc_451 = evaluate_agentic_event_ticketing_escrow_policy(
            webiq_ftc_part464_upfront_all_in_price_clean=False,
        )
        self.assertFalse(ftc_451.allowed)
        self.assertEqual(ftc_451.http_status, 451)

        # 5. Web IQ enables barcode re-issuance & face-value exchange saving $36,000 ($414,000 net) -> 409 Confirm
        sav_409 = evaluate_agentic_event_ticketing_escrow_policy(
            barcode_reissuance_and_face_value_savings_cents=3600000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ticketing_batch_cents, 41400000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_event_ticketing_escrow_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-event-ticketing-escrow-sandbox", demo_zh)


    def test_agentic_telecom_dcb_carrier_billing_psd2_cap_anti_cramming_mandate_vs_wap_clickjacking_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_telecom_dcb_psd2_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. GSMA CAMARA + zero Wi-Fi drop trojan + PSD2 €50/€300 cap + FCC clean ($420,000.00) -> 200 OK
        commit_ok = evaluate_agentic_telecom_dcb_psd2_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_dcb_batch_cents, 42000000)

        # 2. WAP clickjacking Wi-Fi drop or silent SMS trojan -> 403 Blocked
        wap_403 = evaluate_agentic_telecom_dcb_psd2_policy(
            camara_number_verified_and_zero_wifi_drop_trojan=False,
        )
        self.assertFalse(wap_403.allowed)
        self.assertEqual(wap_403.http_status, 403)
        self.assertEqual(
            wap_403.decision_code,
            "WAP_CLICKJACKING_WIFI_DROP_OR_SILENT_SMS_TROJAN_BLOCKED",
        )

        # 3. PSD2 Art. 3(l) >€50 tx (or split smurfing), >€300 monthly cap, or physical goods -> 422 Blocked
        psd_422 = evaluate_agentic_telecom_dcb_psd2_policy(
            psd2_art3l_50eur_300eur_cap_and_digital_only_verified=False,
        )
        self.assertFalse(psd_422.allowed)
        self.assertEqual(psd_422.http_status, 422)
        self.assertEqual(
            psd_422.decision_code,
            "PSD2_ART3L_50EUR_300EUR_CAP_OR_PHYSICAL_GOODS_BREACH",
        )

        # 4. FCC 47 CFR § 64.2401 Truth-in-Billing cramming or missing STOP opt-out -> 451 Hold
        fcc_451 = evaluate_agentic_telecom_dcb_psd2_policy(
            webiq_fcc_truth_in_billing_and_stop_keyword_clean=False,
        )
        self.assertFalse(fcc_451.allowed)
        self.assertEqual(fcc_451.http_status, 451)

        # 5. Web IQ enables CAMARA anti-toll-fraud & OCS reservation saving $33,600 ($386,400 net) -> 409 Confirm
        sav_409 = evaluate_agentic_telecom_dcb_psd2_policy(
            camara_anti_toll_fraud_and_haircut_savings_cents=3360000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_dcb_batch_cents, 38640000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_telecom_dcb_psd2_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-telecom-dcb-psd2-sandbox", demo_zh)


    def test_agentic_tax_free_vat_refund_customs_digital_stamp_mandate_vs_domestic_diversion_clawback_loss_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_tax_free_vat_refund_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. PABLO/DIVA digital stamp + non-prepaid credit clawback hold + threshold & <=90d export ($510,000.00) -> 200 OK
        commit_ok = evaluate_agentic_tax_free_vat_refund_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_vat_refund_batch_cents, 51000000)

        # 2. Burner prepaid card domestic diversion or forged paper customs stamp -> 403 Blocked
        div_403 = evaluate_agentic_tax_free_vat_refund_policy(
            customs_digital_stamp_and_non_prepaid_clawback_verified=False,
        )
        self.assertFalse(div_403.allowed)
        self.assertEqual(div_403.http_status, 403)
        self.assertEqual(
            div_403.decision_code,
            "DOMESTIC_DIVERSION_BURNER_CARD_OR_FORGED_CUSTOMS_STAMP_BLOCKED",
        )

        # 3. Below same-day store threshold, ineligible service SKU, or >90d export window -> 422 Blocked
        eli_422 = evaluate_agentic_tax_free_vat_refund_policy(
            same_day_threshold_sealed_goods_and_90d_export_verified=False,
        )
        self.assertFalse(eli_422.allowed)
        self.assertEqual(eli_422.http_status, 422)
        self.assertEqual(
            eli_422.decision_code,
            "VAT_THRESHOLD_INELIGIBLE_SKU_OR_90DAY_EXPORT_WINDOW_BREACH",
        )

        # 4. Opaque 40% fee retention or predatory DCC FX markup -> 451 Hold
        dcc_451 = evaluate_agentic_tax_free_vat_refund_policy(
            webiq_transparent_fee_and_zero_predatory_dcc_clean=False,
        )
        self.assertFalse(dcc_451.allowed)
        self.assertEqual(dcc_451.http_status, 451)

        # 5. Web IQ enables direct PABLO/DIVA clearing & clawback shield saving $40,800 ($469,200 net) -> 409 Confirm
        sav_409 = evaluate_agentic_tax_free_vat_refund_policy(
            direct_digital_customs_and_clawback_shield_savings_cents=4080000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_vat_refund_batch_cents, 46920000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_tax_free_vat_refund_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-tax-free-vat-refund-sandbox", demo_zh)


    def test_agentic_luxury_collectible_authentication_escrow_antifake_mandate_vs_superfake_swap_return_scam_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_luxury_collectible_auth_escrow_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. 2-Hop Auth Hub XRF/movement + NTAG 424 closed + Enquirus/CITES clean ($495,000.00) -> 200 OK
        commit_ok = evaluate_agentic_luxury_collectible_auth_escrow_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_luxury_batch_cents, 49500000)

        # 2. Uninspected P2P payout or Frankenwatch movement/316L alloy mismatch -> 403 Blocked
        fak_403 = evaluate_agentic_luxury_collectible_auth_escrow_policy(
            auth_hub_xrf_and_movement_inspection_verified=False,
        )
        self.assertFalse(fak_403.allowed)
        self.assertEqual(fak_403.http_status, 403)
        self.assertEqual(
            fak_403.decision_code,
            "SUPERFAKE_MOVEMENT_ALLOY_MISMATCH_OR_UNINSPECTED_PAYOUT_BLOCKED",
        )

        # 3. RMA return with severed NTAG 424 DNA tamper loop ('O') or fake CMAC swap -> 422 Blocked
        swp_422 = evaluate_agentic_luxury_collectible_auth_escrow_policy(
            ntag424_dna_tamper_loop_closed_and_cmac_verified=False,
        )
        self.assertFalse(swp_422.allowed)
        self.assertEqual(swp_422.http_status, 422)
        self.assertEqual(
            swp_422.decision_code,
            "NFC_TAMPER_SEAL_BROKEN_OR_RETURN_COUNTERFEIT_SWAP_REJECTED",
        )

        # 4. Stolen Enquirus serial hit, deactivated PSA cert, or missing CITES permit -> 451 Hold
        stl_451 = evaluate_agentic_luxury_collectible_auth_escrow_policy(
            webiq_enquirus_stolen_registry_and_cites_clean=False,
        )
        self.assertFalse(stl_451.allowed)
        self.assertEqual(stl_451.http_status, 451)

        # 5. Web IQ Freeport Vault direct custody & anti-swap lock saving $39,600 ($455,400 net) -> 409 Confirm
        sav_409 = evaluate_agentic_luxury_collectible_auth_escrow_policy(
            freeport_vault_custody_and_anti_swap_savings_cents=3960000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_luxury_batch_cents, 45540000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_luxury_collectible_auth_escrow_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-luxury-collectible-auth-escrow-sandbox", demo_zh)


    def test_b2b_duty_drawback_ftz_inverted_tariff_first_sale_mandate_vs_unrecovered_tariff_double_claim_fine_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_duty_drawback_ftz_tariff_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Unique 7501-EEI lock + First-Sale factory price + FTZ & CBP clean ($790,000.00) -> 200 OK
        commit_ok = evaluate_b2b_duty_drawback_ftz_tariff_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_customs_drawback_batch_cents, 79000000)

        # 2. Duplicate drawback claim on CBP 7501 line or unlinked AES EEI export -> 403 Blocked
        dup_403 = evaluate_b2b_duty_drawback_ftz_tariff_policy(
            ace_import_7501_to_export_eei_vin_lot_unique_lock_verified=False,
        )
        self.assertFalse(dup_403.allowed)
        self.assertEqual(dup_403.http_status, 403)
        self.assertEqual(
            dup_403.decision_code,
            "DUPLICATE_DUTY_DRAWBACK_CLAIM_OR_UNLINKED_7501_EEI_FRAUD_BLOCKED",
        )

        # 3. Taxed on 35% middleman markup instead of First-Sale or inverted FTZ NPF/PF status -> 422 Blocked
        fsl_422 = evaluate_b2b_duty_drawback_ftz_tariff_policy(
            first_sale_factory_tier_arm_length_and_ftz_inverted_election_verified=False,
        )
        self.assertFalse(fsl_422.allowed)
        self.assertEqual(fsl_422.http_status, 422)
        self.assertEqual(
            fsl_422.decision_code,
            "MIDDLEMAN_MARKUP_DUTY_OVERPAYMENT_OR_FTZ_PRIVILEGED_FOREIGN_MISMATCH",
        )

        # 4. CBP CROSS ruling revocation, >5yr expired entry, or USMCA Art. 2.5 breach -> 451 Hold
        cbp_451 = evaluate_b2b_duty_drawback_ftz_tariff_policy(
            webiq_cbp_cross_ruling_and_usmca_article_2_5_lesser_duty_clean=False,
        )
        self.assertFalse(cbp_451.allowed)
        self.assertEqual(cbp_451.http_status, 451)

        # 5. Web IQ FTZ Weekly Entry MPF cap & 99% drawback recovery saving $63,200 ($726,800 net) -> 409 Confirm
        sav_409 = evaluate_b2b_duty_drawback_ftz_tariff_policy(
            ftz_weekly_entry_mpf_cap_and_99pct_drawback_recovery_savings_cents=6320000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_customs_drawback_batch_cents, 72680000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_duty_drawback_ftz_tariff_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-duty-drawback-ftz-tariff-sandbox", demo_zh)


    def test_b2b_cloud_finops_committed_use_cud_ri_arbitrage_mandate_vs_zombie_reservation_egress_waste_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_cloud_finops_cud_ri_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. 90d P10 baseline + Convertible flex + zero egress inversion + EDP clean ($920,000.00) -> 200 OK
        commit_ok = evaluate_b2b_cloud_finops_cud_ri_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_cloud_finops_batch_cents, 92000000)

        # 2. Peak-sized 3-yr rigid Standard RI overprovisioning or non-convertible SKU lock -> 403 Blocked
        zmb_403 = evaluate_b2b_cloud_finops_cud_ri_policy(
            p10_steady_state_waterline_and_convertible_family_flex_verified=False,
        )
        self.assertFalse(zmb_403.allowed)
        self.assertEqual(zmb_403.http_status, 403)
        self.assertEqual(
            zmb_403.decision_code,
            "ZOMBIE_3YR_COMMITMENT_OVERPROVISIONING_OR_NON_CONVERTIBLE_SKU_LOCK_BLOCKED",
        )

        # 3. Cross-AZ / NAT egress explosion exceeding compute discount or unamortized FOCUS cost -> 422 Blocked
        egr_422 = evaluate_b2b_cloud_finops_cud_ri_policy(
            focus_effective_cost_amortization_and_zero_cross_az_egress_verified=False,
        )
        self.assertFalse(egr_422.allowed)
        self.assertEqual(egr_422.http_status, 422)
        self.assertEqual(
            egr_422.decision_code,
            "CROSS_REGION_NAT_EGRESS_EXPLOSION_OR_UNAMORTIZED_UPFRONT_DISTORTION",
        )

        # 4. Marketplace SKU ineligible for 100% EDP/MACC drawdown or year-end shortfall risk -> 451 Hold
        edp_451 = evaluate_b2b_cloud_finops_cud_ri_policy(
            webiq_edp_mac_burn_rate_and_marketplace_private_offer_clean=False,
        )
        self.assertFalse(edp_451.allowed)
        self.assertEqual(edp_451.http_status, 451)

        # 5. Web IQ rolling laddered Convertible SP & EDP/MACC drawdown saving $73,600 ($846,400 net) -> 409 Confirm
        sav_409 = evaluate_b2b_cloud_finops_cud_ri_policy(
            convertible_sp_ladder_and_edp_drawdown_arbitrage_savings_cents=7360000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_cloud_finops_batch_cents, 84640000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_cloud_finops_cud_ri_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-cloud-finops-cud-ri-sandbox", demo_zh)


    def test_b2b_retail_vendor_otif_edi812_chargeback_coop_mdf_mandate_vs_false_otif_deduction_drain_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_retail_vendor_otif_edi812_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Pre-gate AS2 MDN + GS1-128 Grade B + ASC 606 POP + 15 USC 13 clean ($760,000.00) -> 200 OK
        commit_ok = evaluate_b2b_retail_vendor_otif_edi812_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_retail_vendor_batch_cents, 76000000)

        # 2. False OTIF chargeback on retailer dock delay or bogus Late ASN fine -> 403 Blocked
        otf_403 = evaluate_b2b_retail_vendor_otif_edi812_policy(
            edi856_as2_mdn_before_gate_and_retailer_portal_delay_excluded=False,
        )
        self.assertFalse(otf_403.allowed)
        self.assertEqual(otf_403.http_status, 403)
        self.assertEqual(
            otf_403.decision_code,
            "FALSE_OTIF_CHARGEBACK_ON_RETAILER_DOCK_DELAY_OR_LATE_ASN_BLOCKED",
        )

        # 3. Unsubstantiated Co-Op MDF bill-back or bogus $25/carton barcode fine -> 422 Blocked
        mdf_422 = evaluate_b2b_retail_vendor_otif_edi812_policy(
            gs1_128_iso15416_grade_b_vision_and_coop_mdf_proof_of_performance_verified=False,
        )
        self.assertFalse(mdf_422.allowed)
        self.assertEqual(mdf_422.http_status, 422)
        self.assertEqual(
            mdf_422.decision_code,
            "UNVERIFIED_COOP_MDF_BILLBACK_OR_GS1_128_BARCODE_SCAN_DEFECT_BLOCKED",
        )

        # 4. Discriminatory MDF violating Robinson-Patman Act (15 USC 13) or expired dispute window -> 451 Hold
        rpa_451 = evaluate_b2b_retail_vendor_otif_edi812_policy(
            webiq_robinson_patman_15usc13_proportional_mdf_and_30d_dispute_window_clean=False,
        )
        self.assertFalse(rpa_451.allowed)
        self.assertEqual(rpa_451.http_status, 451)

        # 5. Web IQ automated EDI 812 counter-evidence & ASN audit saving $60,800 ($699,200 net) -> 409 Confirm
        sav_409 = evaluate_b2b_retail_vendor_otif_edi812_policy(
            automated_edi812_counter_evidence_and_pre_ship_asn_audit_savings_cents=6080000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_retail_vendor_batch_cents, 69920000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_retail_vendor_otif_edi812_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-retail-vendor-otif-edi812-sandbox", demo_zh)


    def test_b2b_channel_partner_deal_reg_ship_debit_gray_market_mandate_vs_special_pricing_diversion_fraud_selection(
        self,
    ) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_channel_partner_deal_reg_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. End-user DUNS serial active + exclusive Deal-Reg + FCPA/BIS clean ($810,000.00) -> 200 OK
        commit_ok = evaluate_b2b_channel_partner_deal_reg_policy()
        self.assertTrue(commit_ok.allowed)
        self.assertEqual(commit_ok.http_status, 200)
        self.assertEqual(commit_ok.settled_channel_rebate_batch_cents, 81000000)

        # 2. Phantom end-user SPA claim or hardware serials diverted to gray market -> 403 Blocked
        div_403 = evaluate_b2b_channel_partner_deal_reg_policy(
            end_user_duns_domain_telemetry_and_pos_serial_activation_verified=False,
        )
        self.assertFalse(div_403.allowed)
        self.assertEqual(div_403.http_status, 403)
        self.assertEqual(
            div_403.decision_code,
            "PHANTOM_END_USER_SPECIAL_PRICING_FRAUD_OR_GRAY_MARKET_DIVERSION_BLOCKED",
        )

        # 3. Duplicate DUNS Deal-Reg collision, stacked-rebate margin breach, or invalid FIFO -> 422 Blocked
        stk_422 = evaluate_b2b_channel_partner_deal_reg_policy(
            exclusive_deal_reg_incumbency_and_non_stackable_spiff_cap_verified=False,
        )
        self.assertFalse(stk_422.allowed)
        self.assertEqual(stk_422.http_status, 422)
        self.assertEqual(
            stk_422.decision_code,
            "DUPLICATE_DEAL_REG_MARGIN_STACKING_OR_FIFO_PRICE_PROTECTION_BREACH",
        )

        # 4. Excessive public-sector/SOE discount spread (DOJ FCPA risk) or BIS Entity List hit -> 451 Hold
        fcp_451 = evaluate_b2b_channel_partner_deal_reg_policy(
            webiq_doj_fcpa_soes_margin_cap_and_bis_entity_list_end_user_clean=False,
        )
        self.assertFalse(fcp_451.allowed)
        self.assertEqual(fcp_451.http_status, 451)

        # 5. Web IQ automated POS serial reconciliation & anti-diversion saving $64,800 ($745,200 net) -> 409 Confirm
        sav_409 = evaluate_b2b_channel_partner_deal_reg_policy(
            automated_pos_ship_and_debit_reconciliation_and_anti_diversion_savings_cents=6480000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_channel_rebate_batch_cents, 74520000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_channel_partner_deal_reg_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-channel-partner-deal-reg-sandbox", demo_zh)


    def test_b2b_cloud_marketplace_private_offer_edp_macc_drawdown_mpo_vs_zero_drawdown_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_cloud_marketplace_private_offer_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 100% MACC/EDP Benefit-Eligible Plan ID + MPO wholesale floor + idempotent metering -> 200 OK ($800,000.00)
        ok_res = evaluate_b2b_cloud_marketplace_private_offer_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_CLOUD_MARKETPLACE_PRIVATE_OFFER_SETTLED")
        self.assertEqual(ok_res.settled_marketplace_private_offer_cents, 80000000)

        # 2. Non-eligible BYOL/unbadged SKU or exhausted third-party subcap causing 0% MACC/EDP drawdown -> 403 Blocked
        drw_403 = evaluate_b2b_cloud_marketplace_private_offer_policy(
            plan_id_100pct_macc_edp_drawdown_eligible_and_subcap_available_verified=False,
        )
        self.assertFalse(drw_403.allowed)
        self.assertEqual(drw_403.http_status, 403)
        self.assertEqual(
            drw_403.decision_code,
            "NON_ELIGIBLE_MARKETPLACE_OFFER_ZERO_MACC_EDP_COMMIT_DRAWDOWN_BLOCKED",
        )

        # 3. CPPO/MPO channel discount stacking below ISV wholesale floor or double direct+channel commission -> 422 Blocked
        flr_422 = evaluate_b2b_cloud_marketplace_private_offer_policy(
            cppo_mpo_isv_wholesale_floor_and_single_cosale_commission_verified=False,
        )
        self.assertFalse(flr_422.allowed)
        self.assertEqual(flr_422.http_status, 422)
        self.assertEqual(
            flr_422.decision_code,
            "CPPO_MPO_WHOLESALE_FLOOR_BREACH_OR_DOUBLE_COSALE_COMMISSION",
        )

        # 4. Duplicate Marketplace Metering API retry spike or post-expiry +65% public list price cliff -> 451 Hold
        mtr_451 = evaluate_b2b_cloud_marketplace_private_offer_policy(
            webiq_idempotent_metering_api_and_no_post_expiry_public_price_cliff_clean=False,
        )
        self.assertFalse(mtr_451.allowed)
        self.assertEqual(mtr_451.http_status, 451)

        # 5. Web IQ expiring MACC/EDP surplus swap & flexible MPO billing schedule saving $64,000 ($736,000 net) -> 409 Confirm
        sav_409 = evaluate_b2b_cloud_marketplace_private_offer_policy(
            expiring_macc_edp_surplus_swap_and_mpo_flexible_schedule_savings_cents=6400000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_marketplace_private_offer_cents, 73600000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_cloud_marketplace_private_offer_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-cloud-marketplace-private-offer-sandbox", demo_zh)

    def test_agentic_mice_group_hotel_attrition_resale_mitigation_master_folio_vs_double_dip_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_mice_group_hotel_attrition_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant resale mitigation credit + PSI outside-the-block match + 75% net profit & signed BEOs -> 200 OK ($680,000.00)
        ok_res = evaluate_agentic_mice_group_hotel_attrition_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_MICE_GROUP_HOTEL_MASTER_FOLIO_SETTLED")
        self.assertEqual(ok_res.settled_mice_master_folio_cents, 68000000)

        # 2. Hotel resold unpicked-up rooms to transient walk-ins yet bills 100% attrition (Double-Dipping) -> 403 Blocked
        res_403 = evaluate_agentic_mice_group_hotel_attrition_policy(
            audited_house_occupancy_resale_mitigation_credit_applied_and_no_double_dip_verified=False,
        )
        self.assertFalse(res_403.allowed)
        self.assertEqual(res_403.http_status, 403)
        self.assertEqual(
            res_403.decision_code,
            "ATTRITION_RESALE_MITIGATION_CREDIT_OMITTED_OR_DOUBLE_DIP_BLOCKED",
        )

        # 3. Uncredited Outside-the-Block OTA attendees or 100% gross room rate + tax penalty instead of 75% net profit -> 422 Blocked
        out_422 = evaluate_agentic_mice_group_hotel_attrition_policy(
            outside_block_psi_attendee_rooms_credited_and_75pct_net_profit_formula_verified=False,
        )
        self.assertFalse(out_422.allowed)
        self.assertEqual(out_422.http_status, 422)
        self.assertEqual(
            out_422.decision_code,
            "GROSS_ATTRITION_PENALTY_WITHOUT_PROFIT_OFFSET_OR_UNCREDITED_OUTSIDE_BLOCK_ROOMS",
        )

        # 4. Unsigned BEO AV rigging surcharges on Master Folio or compounded service-fee sales tax -> 451 Hold
        beo_451 = evaluate_agentic_mice_group_hotel_attrition_policy(
            webiq_master_folio_beo_onsite_signatures_and_zero_compounded_service_tax_clean=False,
        )
        self.assertFalse(beo_451.allowed)
        self.assertEqual(beo_451.http_status, 451)

        # 5. Web IQ PSI attendee-to-PMS cross-match & resale mitigation saving $54,400 ($625,600 net) -> 409 Confirm
        sav_409 = evaluate_agentic_mice_group_hotel_attrition_policy(
            guest_list_cross_match_and_resale_mitigation_savings_cents=5440000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_mice_master_folio_cents, 62560000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_mice_group_hotel_attrition_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-mice-group-hotel-attrition-sandbox", demo_zh)


    def test_commercial_agent_platform_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_agent_platform_selection_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant hybrid platform (Copilot Studio UI + Foundry 5-state FSM + L1-L3 funnel + MCP OAuth 2.1) -> 200 OK ($125,000.00)
        ok_res = evaluate_commercial_agent_platform_selection_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_COMMERCIAL_AGENT_HYBRID_PLATFORM_SETTLED")
        self.assertEqual(ok_res.settled_commercial_agent_platform_cents, 12500000)

        # 2. Unbounded low-code generative orchestration without deterministic FSM / payload-hash idempotency -> 403 Blocked
        fsm_403 = evaluate_commercial_agent_platform_selection_policy(
            deterministic_fsm_and_payload_hash_idempotency_verified=False,
        )
        self.assertFalse(fsm_403.allowed)
        self.assertEqual(fsm_403.http_status, 403)
        self.assertEqual(
            fsm_403.decision_code,
            "UNBOUNDED_GENERATIVE_ORCHESTRATION_WITHOUT_FSM_IDEMPOTENCY_BLOCKED",
        )

        # 3. Anonymous high-volume browsing traffic without L1/L2/L3 FinOps funnel causing CAC margin wipeout -> 422 Blocked
        cac_422 = evaluate_commercial_agent_platform_selection_policy(
            three_tier_finops_funnel_and_cac_margin_guard_verified=False,
        )
        self.assertFalse(cac_422.allowed)
        self.assertEqual(cac_422.http_status, 422)
        self.assertEqual(
            cac_422.decision_code,
            "ANONYMOUS_HIGH_VOLUME_PER_CONVERSATION_BILLING_MARGIN_WIPEOUT",
        )

        # 4. Missing MCP OAuth 2.1 RFC 8707 aud binding or using post-Nov 30 static sk_live_* key -> 451 Hold
        mcp_451 = evaluate_commercial_agent_platform_selection_policy(
            webiq_mcp_oauth21_audience_binding_and_nov30_key_clean=False,
        )
        self.assertFalse(mcp_451.allowed)
        self.assertEqual(mcp_451.http_status, 451)

        # 5. Hybrid Copilot Studio + Foundry L1-L3 funnel & Web IQ passage optimization saving $26,250 ($98,750 net) -> 409 Confirm
        sav_409 = evaluate_commercial_agent_platform_selection_policy(
            automated_hybrid_platform_and_l1_l3_funnel_savings_cents=2625000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_commercial_agent_platform_cents, 9875000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["commercial_agent_platform_selection_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("commercial-agent-platform-selection-sandbox", demo_zh)

    def test_commercial_search_grounding_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_search_grounding_selection_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Web IQ /v3/browse passage + liveCrawl freshness + SHA-256 price digest -> 200 OK ($110,000.00)
        ok_res = evaluate_commercial_search_grounding_selection_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_COMMERCIAL_SEARCH_GROUNDING_SETTLED")
        self.assertEqual(ok_res.settled_commercial_search_grounding_cents, 11000000)

        # 2. Black-box synthesized answer (Perplexity Sonar / Managed Bing Grounding) used directly for checkout -> 403 Blocked
        blk_403 = evaluate_commercial_search_grounding_selection_policy(
            caller_visible_raw_passage_and_sha256_price_digest_verified=False,
        )
        self.assertFalse(blk_403.allowed)
        self.assertEqual(blk_403.http_status, 403)
        self.assertEqual(
            blk_403.decision_code,
            "BLACKBOX_SYNTHESIZED_ANSWER_OR_INVISIBLE_PASSAGE_CHECKOUT_BLOCKED",
        )

        # 3. Stale crawl cache (liveCrawlSucceeded=false) or unsliced 4,800-token full-page HTML -> 422 Blocked
        stl_422 = evaluate_commercial_search_grounding_selection_policy(
            live_crawl_freshness_and_passage_token_compression_verified=False,
        )
        self.assertFalse(stl_422.allowed)
        self.assertEqual(stl_422.http_status, 422)
        self.assertEqual(
            stl_422.decision_code,
            "STALE_CRAWL_CACHE_OR_UNALIGNED_FULL_PAGE_HTML_TOKEN_BLOAT_BLOCKED",
        )

        # 4. Unsafe Browser-use automation on BNPL/3DS payment WebView or plaintext http:// scheme -> 451 Hold
        web_451 = evaluate_commercial_search_grounding_selection_policy(
            webiq_https_scheme_and_bnpl_webview_non_automation_clean=False,
        )
        self.assertFalse(web_451.allowed)
        self.assertEqual(web_451.http_status, 451)

        # 5. 4-stage tiered grounding & Web IQ passage compression saving $24,200 ($85,800 net) -> 409 Confirm
        sav_409 = evaluate_commercial_search_grounding_selection_policy(
            automated_tiered_grounding_and_passage_compression_savings_cents=2420000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_commercial_search_grounding_cents, 8580000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["commercial_search_grounding_selection_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("commercial-search-grounding-selection-sandbox", demo_zh)

    def test_agent_payment_toolkit_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agent_payment_toolkit_selection_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 5-rail payment routing (Stripe SPT + Visa VIC + MC + PayPal + Single-use VCN) -> 200 OK ($140,000.00)
        ok_res = evaluate_agent_payment_toolkit_selection_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_AGENT_PAYMENT_TOOLKIT_MULTIRAIL_SETTLED")
        self.assertEqual(ok_res.settled_agent_payment_toolkit_cents, 14000000)

        # 2. Raw reusable master card PAN, post-Nov 30 sk_live_* or double SPT resolve -> 403 Blocked
        pan_403 = evaluate_agent_payment_toolkit_selection_policy(
            zero_reusable_pan_and_nov30_key_and_single_resolve_verified=False,
        )
        self.assertFalse(pan_403.allowed)
        self.assertEqual(pan_403.http_status, 403)
        self.assertEqual(
            pan_403.decision_code,
            "RAW_REUSABLE_PAN_OR_POST_NOV30_STATIC_KEY_OR_DOUBLE_RESOLVE_BLOCKED",
        )

        # 3. Calling SPT outside 34 supported countries or unbounded virtual card limit -> 422 Blocked
        reg_422 = evaluate_agent_payment_toolkit_selection_policy(
            spt_34_country_routing_and_single_use_vcard_cap_verified=False,
        )
        self.assertFalse(reg_422.allowed)
        self.assertEqual(reg_422.http_status, 422)
        self.assertEqual(
            reg_422.decision_code,
            "UNSUPPORTED_SPT_REGION_OR_UNBOUNDED_VIRTUAL_CARD_SPEND_LIMIT_BLOCKED",
        )

        # 4. Visa VIC Passkey silent retry or unconfirmed PayPal/MCP refund/payout -> 451 Hold
        vic_451 = evaluate_agent_payment_toolkit_selection_policy(
            webiq_vic_passkey_fail_closed_and_refund_hitl_clean=False,
        )
        self.assertFalse(vic_451.allowed)
        self.assertEqual(vic_451.http_status, 451)

        # 5. Multi-rail routing & single-use VCN interchange rebate saving $29,400 ($110,600 net) -> 409 Confirm
        sav_409 = evaluate_agent_payment_toolkit_selection_policy(
            automated_multirail_routing_and_vcard_rebate_savings_cents=2940000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_agent_payment_toolkit_cents, 11060000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agent_payment_toolkit_selection_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agent-payment-toolkit-selection-sandbox", demo_zh)

    def test_ecommerce_shopping_stylist_bundle_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ecommerce_shopping_stylist_bundle_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant ATP size filter + >=18% net margin + Web IQ fit grounding + 1-click bundle lock -> 200 OK ($155,000.00)
        ok_res = evaluate_ecommerce_shopping_stylist_bundle_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_ECOMMERCE_SHOPPING_STYLIST_BUNDLE_SETTLED")
        self.assertEqual(ok_res.settled_ecommerce_shopping_bundle_cents, 15500000)

        # 2. Out-of-stock variant (ATP=0), disable_checkout=true, or incompatible bundle -> 403 Blocked
        oos_403 = evaluate_ecommerce_shopping_stylist_bundle_policy(
            atp_in_stock_and_disable_checkout_false_and_compat_verified=False,
        )
        self.assertFalse(oos_403.allowed)
        self.assertEqual(oos_403.http_status, 403)
        self.assertEqual(
            oos_403.decision_code,
            "OUT_OF_STOCK_VARIANT_OR_DISABLE_CHECKOUT_OR_INCOMPATIBLE_BUNDLE_BLOCKED",
        )

        # 3. Promo-stacking net-margin breach (<18%) or LLM discount math drift -> 422 Blocked
        mgn_422 = evaluate_ecommerce_shopping_stylist_bundle_policy(
            deterministic_promo_exclusivity_and_18pct_net_margin_verified=False,
        )
        self.assertFalse(mgn_422.allowed)
        self.assertEqual(mgn_422.http_status, 422)
        self.assertEqual(
            mgn_422.decision_code,
            "BUNDLE_DISCOUNT_STACKING_NET_MARGIN_FLOOR_OR_LLM_MATH_DRIFT_BLOCKED",
        )

        # 4. Incomplete SFTP manifest.json barrier or product safety recall alert -> 451 Hold
        rec_451 = evaluate_ecommerce_shopping_stylist_bundle_policy(
            webiq_catalog_manifest_barrier_and_zero_recall_clean=False,
        )
        self.assertFalse(rec_451.allowed)
        self.assertEqual(rec_451.http_status, 451)

        # 5. Cross-category tiered bundling & Web IQ fit return reduction saving $32,550 ($122,450 net) -> 409 Confirm
        sav_409 = evaluate_ecommerce_shopping_stylist_bundle_policy(
            automated_bundle_tier_and_fit_return_reduction_savings_cents=3255000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ecommerce_shopping_bundle_cents, 12245000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["ecommerce_shopping_stylist_bundle_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ecommerce-shopping-stylist-bundle-sandbox", demo_zh)

    def test_ota_travel_rebooking_ndc_saga_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ota_travel_rebooking_ndc_saga_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 2-phase flight+hotel Saga + all-in fare + <=180d SPT + 24h idempotency -> 200 OK ($165,000.00)
        ok_res = evaluate_ota_travel_rebooking_ndc_saga_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_OTA_TRAVEL_REBOOKING_NDC_SAGA_SETTLED")
        self.assertEqual(ok_res.settled_ota_travel_rebooking_cents, 16500000)

        # 2. Unbundled single-leg automatic capture or canceling old booking before holding new -> 403 Blocked
        leg_403 = evaluate_ota_travel_rebooking_ndc_saga_policy(
            two_phase_preauth_saga_and_hold_new_before_cancel_old_verified=False,
        )
        self.assertFalse(leg_403.allowed)
        self.assertEqual(leg_403.http_status, 403)
        self.assertEqual(
            leg_403.decision_code,
            "UNBUNDLED_SINGLE_LEG_CAPTURE_OR_CANCEL_OLD_BEFORE_HOLD_NEW_BLOCKED",
        )

        # 3. Drip pricing (bag/resort fees) breaching T&E cap or negative net rebooking yield -> 422 Blocked
        drp_422 = evaluate_ota_travel_rebooking_ndc_saga_policy(
            all_in_landed_fare_within_te_cap_and_positive_net_rebook_verified=False,
        )
        self.assertFalse(drp_422.allowed)
        self.assertEqual(drp_422.http_status, 422)
        self.assertEqual(
            drp_422.decision_code,
            "DRIP_PRICING_TE_POLICY_BREACH_OR_NEGATIVE_NET_REBOOKING_YIELD_BLOCKED",
        )

        # 4. Forward booking SPT expiry > 180 days or 24h Idempotency-Key payload drift -> 451 Hold
        ttl_451 = evaluate_ota_travel_rebooking_ndc_saga_policy(
            webiq_booking_spt_under_180d_and_24h_idempotency_clean=False,
        )
        self.assertFalse(ttl_451.allowed)
        self.assertEqual(ttl_451.http_status, 451)

        # 5. Automated price-drop rebooking & 2-phase Saga zero-loss saving $34,650 ($130,350 net) -> 409 Confirm
        sav_409 = evaluate_ota_travel_rebooking_ndc_saga_policy(
            automated_price_drop_rebooking_and_saga_zero_loss_savings_cents=3465000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ota_travel_rebooking_cents, 13035000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["ota_travel_rebooking_ndc_saga_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ota-travel-rebooking-ndc-saga-sandbox", demo_zh)

    def test_b2b_rfq_sourcing_contract_redline_copilot_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Normalized DDP Landed TCO + MSA clean + Post-GRN terms + ERP budget lock -> 200 OK ($180,000.00)
        ok_res = evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_B2B_RFQ_SOURCING_CONTRACT_COPILOT_SETTLED")
        self.assertEqual(ok_res.settled_b2b_rfq_copilot_cents, 18000000)

        # 2. Unnormalized EXW raw-price award or bypassed ERP cost-center budget encumbrance -> 403 Blocked
        exw_403 = evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy(
            ddp_landed_tco_normalized_and_erp_budget_encumbrance_verified=False,
        )
        self.assertFalse(exw_403.allowed)
        self.assertEqual(exw_403.http_status, 403)
        self.assertEqual(
            exw_403.decision_code,
            "UNNORMALIZED_EXW_RAW_PRICE_AWARD_OR_BYPASSED_ERP_BUDGET_ENCUMBRANCE_BLOCKED",
        )

        # 3. Contract poison pill (LoL cap <12m, silent evergreen renewal, or pre-GRN invoice trigger) -> 422 Blocked
        msa_422 = evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy(
            msa_lol_cap_and_no_evergreen_and_post_grn_terms_verified=False,
        )
        self.assertFalse(msa_422.allowed)
        self.assertEqual(msa_422.http_status, 422)
        self.assertEqual(
            msa_422.decision_code,
            "CONTRACT_POISON_PILL_LOL_CAP_AUTO_RENEWAL_OR_PRE_GRN_INVOICE_TERM_BLOCKED",
        )

        # 4. Web IQ detects supplier sanction/litigation risk or collusive bid rigging -> 451 Hold
        san_451 = evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy(
            webiq_supplier_sanction_litigation_and_anticollusion_clean=False,
        )
        self.assertFalse(san_451.allowed)
        self.assertEqual(san_451.http_status, 451)

        # 5. Normalized Landed TCO negotiation & Net-60 working-capital discount saving $36,000 ($144,000 net) -> 409 Confirm
        sav_409 = evaluate_b2b_rfq_sourcing_contract_redline_copilot_policy(
            automated_landed_tco_negotiation_and_net60_savings_cents=3600000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_b2b_rfq_copilot_cents, 14400000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_rfq_sourcing_contract_redline_copilot_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-rfq-sourcing-contract-redline-copilot-sandbox", demo_zh)

    def test_cross_border_multilingual_cs_rma_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cross_border_multilingual_cs_rma_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Web IQ geo-policy + carrier weight scan + human-confirmed OAuth 2.1 refund -> 200 OK ($135,000.00)
        ok_res = evaluate_cross_border_multilingual_cs_rma_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_CROSS_BORDER_MULTILINGUAL_CS_RMA_SETTLED")
        self.assertEqual(ok_res.settled_cross_border_cs_rma_cents, 13500000)

        # 2. Unconfirmed create_refund write call or unverified carrier weight scan on high-ticket RMA -> 403 Blocked
        ref_403 = evaluate_cross_border_multilingual_cs_rma_policy(
            human_confirmed_refund_write_and_carrier_weight_scan_verified=False,
        )
        self.assertFalse(ref_403.allowed)
        self.assertEqual(ref_403.http_status, 403)
        self.assertEqual(
            ref_403.decision_code,
            "UNCONFIRMED_MCP_REFUND_WRITE_OR_UNVERIFIED_CARRIER_WEIGHT_RMA_BLOCKED",
        )

        # 3. Negative reverse-logistics net recovery label waste or summary/terms restocking-fee mismatch -> 422 Blocked
        rec_422 = evaluate_cross_border_multilingual_cs_rma_policy(
            reverse_logistics_net_recovery_and_restock_fee_parity_verified=False,
        )
        self.assertFalse(rec_422.allowed)
        self.assertEqual(rec_422.http_status, 422)
        self.assertEqual(
            rec_422.decision_code,
            "NEGATIVE_REVERSE_LOGISTICS_RECOVERY_LABEL_WASTE_OR_RESTOCK_FEE_MISMATCH",
        )

        # 4. Web IQ /v3/browse HTTP 202 pending, post-Nov 30 sk_live_*, or >180d dormant payout key -> 451 Hold
        def_451 = evaluate_cross_border_multilingual_cs_rma_policy(
            webiq_browse_not_202_and_oauth_active_within_180d_clean=False,
        )
        self.assertFalse(def_451.allowed)
        self.assertEqual(def_451.http_status, 451)

        # 5. Exchange-first bonus retention & returnless Keep-It math saving $28,350 ($106,650 net) -> 409 Confirm
        sav_409 = evaluate_cross_border_multilingual_cs_rma_policy(
            automated_exchange_first_and_returnless_keep_it_savings_cents=2835000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_cross_border_cs_rma_cents, 10665000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cross_border_multilingual_cs_rma_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cross-border-multilingual-cs-rma-sandbox", demo_zh)

    def test_saas_churn_retention_subscription_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_saas_churn_retention_subscription_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant FTC symmetric cancel UI + compute COGS floor + cadence SPT renewal -> 200 OK ($190,000.00)
        ok_res = evaluate_saas_churn_retention_subscription_agent_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_SAAS_CHURN_RETENTION_CADENCE_SPT_SETTLED")
        self.assertEqual(ok_res.settled_saas_churn_retention_cents, 19000000)

        # 2. FTC Click-to-Cancel dark pattern or forbidden setup_future_usage on SPT -> 403 Blocked
        ftc_403 = evaluate_saas_churn_retention_subscription_agent_policy(
            ftc_click_to_cancel_symmetric_ui_and_no_sfu_on_spt_verified=False,
        )
        self.assertFalse(ftc_403.allowed)
        self.assertEqual(ftc_403.http_status, 403)
        self.assertEqual(
            ftc_403.decision_code,
            "FTC_CLICK_TO_CANCEL_DARK_PATTERN_OR_FORBIDDEN_SPT_SETUP_FUTURE_USAGE_BLOCKED",
        )

        # 3. Retention discount below marginal compute COGS or silent renewal price hike above ceiling -> 422 Blocked
        cog_422 = evaluate_saas_churn_retention_subscription_agent_policy(
            retention_offer_above_compute_cogs_and_within_ceiling_verified=False,
        )
        self.assertFalse(cog_422.allowed)
        self.assertEqual(cog_422.http_status, 422)
        self.assertEqual(
            cog_422.decision_code,
            "RETENTION_OFFER_BELOW_COGS_OR_RENEWAL_PRICE_EXCEEDS_INTERVAL_CEILING",
        )

        # 4. off_session=True without recurring_interval or FCB tripped -> 451 Hold
        int_451 = evaluate_saas_churn_retention_subscription_agent_policy(
            webiq_recurring_interval_configured_and_fcb_closed_clean=False,
        )
        self.assertFalse(int_451.allowed)
        self.assertEqual(int_451.http_status, 451)

        # 5. Telemetry pause/right-sizing retention saving $39,900 ($150,100 net) -> 409 Confirm
        sav_409 = evaluate_saas_churn_retention_subscription_agent_policy(
            automated_telemetry_pause_rightsize_retention_savings_cents=3990000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_saas_churn_retention_cents, 15010000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["saas_churn_retention_subscription_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("saas-churn-retention-subscription-agent-sandbox", demo_zh)

    def test_enterprise_erp_crm_idempotent_saga_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_enterprise_erp_crm_idempotent_saga_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant gateway-derived SHA-256 idempotency + Outbox <4s + 2-phase manual pre-auth Saga -> 200 OK ($210,000.00)
        ok_res = evaluate_enterprise_erp_crm_idempotent_saga_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_ENTERPRISE_ERP_CRM_IDEMPOTENT_SAGA_SETTLED")
        self.assertEqual(ok_res.settled_enterprise_erp_crm_saga_cents, 21000000)

        # 2. LLM random idempotency UUID or automatic capture before ERP order confirmation -> 403 Blocked
        idem_403 = evaluate_enterprise_erp_crm_idempotent_saga_policy(
            gateway_derived_idempotency_and_manual_preauth_before_erp_verified=False,
        )
        self.assertFalse(idem_403.allowed)
        self.assertEqual(idem_403.http_status, 403)
        self.assertEqual(
            idem_403.decision_code,
            "LLM_RANDOM_IDEMPOTENCY_KEY_OR_UNBUNDLED_AUTOMATIC_CAPTURE_BEFORE_ERP_BLOCKED",
        )

        # 3. Retry payload SHA-256 hash drift (LLM parameter mutation) or stale Cart ETag -> 422 Blocked
        drf_422 = evaluate_enterprise_erp_crm_idempotent_saga_policy(
            canonical_payload_sha256_match_and_cart_etag_verified=False,
        )
        self.assertFalse(drf_422.allowed)
        self.assertEqual(drf_422.http_status, 422)
        self.assertEqual(
            drf_422.decision_code,
            "IDEMPOTENCY_PAYLOAD_HASH_DRIFT_OR_STALE_CART_ETAG_BLOCKED",
        )

        # 4. Synchronous slow SAP call inside 4,000ms finalize_checkout webhook or stale generation fencing -> 451 Hold
        out_451 = evaluate_enterprise_erp_crm_idempotent_saga_policy(
            webiq_outbox_under_4s_webhook_and_generation_fencing_clean=False,
        )
        self.assertFalse(out_451.allowed)
        self.assertEqual(out_451.http_status, 451)

        # 5. Gateway idempotent dedup & zero-fee pre-auth void Saga saving $42,000 ($168,000 net) -> 409 Confirm
        sav_409 = evaluate_enterprise_erp_crm_idempotent_saga_policy(
            automated_idempotent_dedup_and_zero_fee_void_saga_savings_cents=4200000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_enterprise_erp_crm_saga_cents, 16800000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["enterprise_erp_crm_idempotent_saga_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("enterprise-erp-crm-idempotent-saga-sandbox", demo_zh)

    def test_omnichannel_bopis_ship_from_store_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_omnichannel_bopis_ship_from_store_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant buffered Store ATP + single-node DOM fill + rotating TOTP handover capture -> 200 OK ($170,000.00)
        ok_res = evaluate_omnichannel_bopis_ship_from_store_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_OMNICHANNEL_BOPIS_SHIP_FROM_STORE_SETTLED")
        self.assertEqual(ok_res.settled_omnichannel_bopis_dom_cents, 17000000)

        # 2. Selling phantom store inventory below safety buffer or static QR screenshot pickup -> 403 Blocked
        buf_403 = evaluate_omnichannel_bopis_ship_from_store_policy(
            store_safety_buffer_and_rotating_totp_pickup_verified=False,
        )
        self.assertFalse(buf_403.allowed)
        self.assertEqual(buf_403.http_status, 403)
        self.assertEqual(
            buf_403.decision_code,
            "PHANTOM_STORE_INVENTORY_BELOW_SAFETY_BUFFER_OR_STATIC_QR_PICKUP_BLOCKED",
        )

        # 3. Excessive split-shipment freight bleed (>35% margin) or blind short-pick order cancellation -> 422 Blocked
        spl_422 = evaluate_omnichannel_bopis_ship_from_store_policy(
            split_shipment_freight_cap_and_short_pick_rescue_verified=False,
        )
        self.assertFalse(spl_422.allowed)
        self.assertEqual(spl_422.http_status, 422)
        self.assertEqual(
            spl_422.decision_code,
            "EXCESSIVE_SPLIT_SHIPMENT_FREIGHT_BLEED_OR_SHORT_PICK_BLIND_CANCEL_BLOCKED",
        )

        # 4. Stale store POS sync heartbeat or emergency store closure alert -> 451 Hold
        pos_451 = evaluate_omnichannel_bopis_ship_from_store_policy(
            webiq_store_pos_heartbeat_and_operating_status_clean=False,
        )
        self.assertFalse(pos_451.allowed)
        self.assertEqual(pos_451.http_status, 451)

        # 5. DOM consolidation & short-pick neighbor-store rescue saving $35,700 ($134,300 net) -> 409 Confirm
        sav_409 = evaluate_omnichannel_bopis_ship_from_store_policy(
            automated_dom_consolidation_and_short_pick_rescue_savings_cents=3570000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_omnichannel_bopis_dom_cents, 13430000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["omnichannel_bopis_ship_from_store_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("omnichannel-bopis-ship-from-store-sandbox", demo_zh)

    def test_enterprise_ap_three_way_match_discount_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_enterprise_ap_three_way_match_discount_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant PO-GRN-Invoice line-item match + Vendor Master vault lock + human approval -> 200 OK ($200,000.00)
        ok_res = evaluate_enterprise_ap_three_way_match_discount_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_ENTERPRISE_AP_THREE_WAY_MATCH_SETTLED")
        self.assertEqual(ok_res.settled_enterprise_ap_three_way_cents, 20000000)

        # 2. BEC bank-account change on invoice or unconfirmed send_money treasury call -> 403 Blocked
        bec_403 = evaluate_enterprise_ap_three_way_match_discount_policy(
            vendor_master_bank_vault_match_and_human_treasury_approval_verified=False,
        )
        self.assertFalse(bec_403.allowed)
        self.assertEqual(bec_403.http_status, 403)
        self.assertEqual(
            bec_403.decision_code,
            "BEC_BANK_ACCOUNT_CHANGE_ON_INVOICE_OR_UNCONFIRMED_TREASURY_BLOCKED",
        )

        # 3. Invoice quantity exceeds GRN Accepted Qty or duplicate invoice variant -> 422 Blocked
        grn_422 = evaluate_enterprise_ap_three_way_match_discount_policy(
            line_item_grn_accepted_qty_and_unique_invoice_hash_verified=False,
        )
        self.assertFalse(grn_422.allowed)
        self.assertEqual(grn_422.http_status, 422)
        self.assertEqual(
            grn_422.decision_code,
            "INVOICE_QTY_EXCEEDS_GRN_ACCEPTED_OR_DUPLICATE_INVOICE_VARIATION_BLOCKED",
        )

        # 4. Treasury key dormant > 180 days or vendor tax/sanction alert -> 451 Hold
        key_451 = evaluate_enterprise_ap_three_way_match_discount_policy(
            webiq_treasury_key_active_within_180d_and_vendor_tax_clean=False,
        )
        self.assertFalse(key_451.allowed)
        self.assertEqual(key_451.http_status, 451)

        # 5. Short-ship Debit Memo & 2/10 Net 30 early-pay discount saving $40,000 ($160,000 net) -> 409 Confirm
        sav_409 = evaluate_enterprise_ap_three_way_match_discount_policy(
            automated_short_ship_debit_memo_and_2_10_net30_discount_savings_cents=4000000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_enterprise_ap_three_way_cents, 16000000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["enterprise_ap_three_way_match_discount_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("enterprise-ap-three-way-match-discount-sandbox", demo_zh)

    def test_enterprise_cpq_deal_desk_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_enterprise_cpq_deal_desk_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 100% BOM solver + Pocket Margin >=45% + seller-initiated OCA -> 200 OK ($185,000.00)
        ok_res = evaluate_enterprise_cpq_deal_desk_agent_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_ENTERPRISE_CPQ_DEAL_DESK_OCA_SETTLED")
        self.assertEqual(ok_res.settled_enterprise_cpq_deal_desk_cents, 18500000)

        # 2. Incomplete BOM (mandatory module removed) or channel deal-registration conflict -> 403 Blocked
        bom_403 = evaluate_enterprise_cpq_deal_desk_agent_policy(
            bom_corequisite_complete_and_no_channel_deal_reg_conflict_verified=False,
        )
        self.assertFalse(bom_403.allowed)
        self.assertEqual(bom_403.http_status, 403)
        self.assertEqual(
            bom_403.decision_code,
            "INCOMPLETE_BOM_MANDATORY_MODULE_REMOVED_OR_CHANNEL_DEAL_REG_CONFLICT_BLOCKED",
        )

        # 3. Pocket-margin waterfall breach (<45% after rebates & free PS hours) -> 422 Blocked
        mgn_422 = evaluate_enterprise_cpq_deal_desk_agent_policy(
            pocket_margin_waterfall_above_45pct_floor_verified=False,
        )
        self.assertFalse(mgn_422.allowed)
        self.assertEqual(mgn_422.http_status, 422)
        self.assertEqual(
            mgn_422.decision_code,
            "POCKET_MARGIN_WATERFALL_FLOOR_BREACH_OR_UNAPPROVED_FREE_PS_HOURS_BLOCKED",
        )

        # 4. Buyer-initiated OCA or reviving seller-terminated expired quote -> 451 Hold
        oca_451 = evaluate_enterprise_cpq_deal_desk_agent_policy(
            webiq_oca_seller_initiated_and_no_expired_reinitiation_clean=False,
        )
        self.assertFalse(oca_451.allowed)
        self.assertEqual(oca_451.http_status, 451)

        # 5. Multi-year commitment restructuring & free PS hour cap saving $37,000 ($148,000 net) -> 409 Confirm
        sav_409 = evaluate_enterprise_cpq_deal_desk_agent_policy(
            automated_multiyear_lock_and_ps_cap_margin_savings_cents=3700000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_enterprise_cpq_deal_desk_cents, 14800000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["enterprise_cpq_deal_desk_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("enterprise-cpq-deal-desk-agent-sandbox", demo_zh)

    def test_ecommerce_dynamic_repricing_map_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_ecommerce_dynamic_repricing_map_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Web IQ live GTIN/InStock proof + above MAP/COGS floor + Catalog upsert -> 200 OK ($160,000.00)
        ok_res = evaluate_ecommerce_dynamic_repricing_map_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_ECOMMERCE_DYNAMIC_REPRICING_MAP_SETTLED")
        self.assertEqual(ok_res.settled_ecommerce_dynamic_repricing_cents, 16000000)

        # 2. Forged screenshot, OutOfStock bait price, or refurbished SKU mismatch -> 403 Blocked
        fak_403 = evaluate_ecommerce_dynamic_repricing_map_policy(
            server_side_gtin_in_stock_and_new_condition_verified=False,
        )
        self.assertFalse(fak_403.allowed)
        self.assertEqual(fak_403.http_status, 403)
        self.assertEqual(
            fak_403.decision_code,
            "FAKE_SCREENSHOT_OR_OUT_OF_STOCK_BAIT_OR_REFURBISHED_MISMATCH_BLOCKED",
        )

        # 3. MAP policy floor breach, algorithmic price spiral, or invalid replace mode on pricing feed -> 422 Blocked
        map_422 = evaluate_ecommerce_dynamic_repricing_map_policy(
            above_map_and_cogs_floor_and_upsert_mode_verified=False,
        )
        self.assertFalse(map_422.allowed)
        self.assertEqual(map_422.http_status, 422)
        self.assertEqual(
            map_422.decision_code,
            "MAP_POLICY_FLOOR_BREACH_OR_PRICE_SPIRAL_OR_INVALID_REPLACE_MODE_BLOCKED",
        )

        # 4. Stale competitor crawl cache (liveCrawlSucceeded=false) or expired 300s upload URL -> 451 Hold
        stl_451 = evaluate_ecommerce_dynamic_repricing_map_policy(
            webiq_live_crawl_fresh_and_300s_upload_url_clean=False,
        )
        self.assertFalse(stl_451.allowed)
        self.assertEqual(stl_451.http_status, 451)

        # 5. Server-side GTIN arbitrage block & MAP margin protection saving $33,600 ($126,400 net) -> 409 Confirm
        sav_409 = evaluate_ecommerce_dynamic_repricing_map_policy(
            automated_gtin_arbitrage_block_and_map_margin_savings_cents=3360000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_ecommerce_dynamic_repricing_cents, 12640000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["ecommerce_dynamic_repricing_map_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("ecommerce-dynamic-repricing-map-sandbox", demo_zh)

    def test_creator_affiliate_escrow_clawback_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_creator_affiliate_escrow_clawback_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant authentic creator referral + 30d return-window escrow + Connect separate transfer -> 200 OK ($150,000.00)
        ok_res = evaluate_creator_affiliate_escrow_clawback_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_CREATOR_AFFILIATE_ESCROW_CLAWBACK_SETTLED")
        self.assertEqual(ok_res.settled_creator_affiliate_escrow_cents, 15000000)

        # 2. Bot-inflated SIVT creator or last-second checkout browser extension coupon poaching -> 403 Blocked
        pch_403 = evaluate_creator_affiliate_escrow_clawback_policy(
            sivt_bot_filtered_and_no_last_second_coupon_poaching_verified=False,
        )
        self.assertFalse(pch_403.allowed)
        self.assertEqual(pch_403.http_status, 403)
        self.assertEqual(
            pch_403.decision_code,
            "FAKE_BOT_ENGAGEMENT_SIVT_OR_LAST_SECOND_COUPON_POACHING_BLOCKED",
        )

        # 3. Premature commission payout before 30-day return window or unclawed RMA refund -> 422 Blocked
        clw_422 = evaluate_creator_affiliate_escrow_clawback_policy(
            post_30d_return_window_and_rma_clawback_deducted_verified=False,
        )
        self.assertFalse(clw_422.allowed)
        self.assertEqual(clw_422.http_status, 422)
        self.assertEqual(
            clw_422.decision_code,
            "PREMATURE_PAYOUT_BEFORE_RETURN_WINDOW_OR_UNCLAWED_REFUND_COMMISSION_BLOCKED",
        )

        # 4. Passing Stripe-Account header on Separate Charges without OBO or missing W-9/W-8BEN tax form -> 451 Hold
        tax_451 = evaluate_creator_affiliate_escrow_clawback_policy(
            webiq_connect_no_header_without_obo_and_tax_form_clean=False,
        )
        self.assertFalse(tax_451.allowed)
        self.assertEqual(tax_451.http_status, 451)

        # 5. Anti-poaching attribution lock & RMA commission clawback saving $31,500 ($118,500 net) -> 409 Confirm
        sav_409 = evaluate_creator_affiliate_escrow_clawback_policy(
            automated_anti_poaching_and_rma_clawback_savings_cents=3150000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_creator_affiliate_escrow_cents, 11850000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["creator_affiliate_escrow_clawback_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("creator-affiliate-escrow-clawback-sandbox", demo_zh)

    def test_corporate_expense_audit_double_dip_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_corporate_expense_audit_double_dip_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant cross-source unique receipt + itemized hotel folio + FCPA clean -> 200 OK ($145,000.00)
        ok_res = evaluate_corporate_expense_audit_double_dip_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_CORPORATE_EXPENSE_AUDIT_FOLIO_SETTLED")
        self.assertEqual(ok_res.settled_corporate_expense_audit_cents, 14500000)

        # 2. Card-and-cash double-dip (pre-tip slip + post-tip card charge) or synthetic AI receipt -> 403 Blocked
        dip_403 = evaluate_corporate_expense_audit_double_dip_policy(
            no_card_cash_double_dip_and_authentic_receipt_verified=False,
        )
        self.assertFalse(dip_403.allowed)
        self.assertEqual(dip_403.http_status, 403)
        self.assertEqual(
            dip_403.decision_code,
            "CARD_AND_CASH_DOUBLE_DIP_OR_SYNTHETIC_AI_RECEIPT_FRAUD_BLOCKED",
        )

        # 3. Unitemized hotel slip, hidden minibar alcohol/spa charges, or per-diem breach -> 422 Blocked
        fol_422 = evaluate_corporate_expense_audit_double_dip_policy(
            itemized_hotel_folio_no_alcohol_spa_and_per_diem_verified=False,
        )
        self.assertFalse(fol_422.allowed)
        self.assertEqual(fol_422.http_status, 422)
        self.assertEqual(
            fol_422.decision_code,
            "UNITEMIZED_HOTEL_FOLIO_ALCOHOL_SPA_OR_PER_DIEM_CAP_BREACH_BLOCKED",
        )

        # 4. High-risk disguised entertainment venue or FCPA hospitality violation -> 451 Hold
        fcp_451 = evaluate_corporate_expense_audit_double_dip_policy(
            webiq_merchant_category_and_fcpa_hospitality_clean=False,
        )
        self.assertFalse(fcp_451.allowed)
        self.assertEqual(fcp_451.http_status, 451)

        # 5. Cross-source double-dip block & automated folio personal carve-out saving $30,450 ($114,550 net) -> 409 Confirm
        sav_409 = evaluate_corporate_expense_audit_double_dip_policy(
            automated_double_dip_block_and_folio_carve_out_savings_cents=3045000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_corporate_expense_audit_cents, 11455000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["corporate_expense_audit_double_dip_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("corporate-expense-audit-double-dip-sandbox", demo_zh)

    def test_retail_cpg_autonomous_replenishment_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_retail_cpg_autonomous_replenishment_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Net Inventory Position + A-Class pallet rounding + shelf-life DOS cap + FCB closed -> 200 OK ($175,000.00)
        ok_res = evaluate_retail_cpg_autonomous_replenishment_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_RETAIL_CPG_AUTONOMOUS_REPLENISHMENT_SETTLED")
        self.assertEqual(ok_res.settled_retail_cpg_replenishment_cents, 17500000)

        # 2. Ignored open in-transit POs (double ordering) or bullwhip bulk spike extrapolation -> 403 Blocked
        int_403 = evaluate_retail_cpg_autonomous_replenishment_policy(
            in_transit_po_deducted_and_bullwhip_spike_winsorized_verified=False,
        )
        self.assertFalse(int_403.allowed)
        self.assertEqual(int_403.http_status, 403)
        self.assertEqual(
            int_403.decision_code,
            "IGNORED_IN_TRANSIT_PO_DOUBLE_ORDERING_OR_BULLWHIP_SPIKE_BLOCKED",
        )

        # 3. MOQ pallet padding exceeding shelf-life DOS cap or supplier price ceiling breach -> 422 Blocked
        dos_422 = evaluate_retail_cpg_autonomous_replenishment_policy(
            shelf_life_dos_ceiling_and_a_class_pallet_rounding_verified=False,
        )
        self.assertFalse(dos_422.allowed)
        self.assertEqual(dos_422.http_status, 422)
        self.assertEqual(
            dos_422.decision_code,
            "MOQ_PALLET_PADDING_EXCEEDS_SHELF_LIFE_OR_PRICE_CEILING_BREACH_BLOCKED",
        )

        # 4. Web IQ safety recall trips Financial Circuit Breaker (FCB=OPEN) -> 451 Hold
        rec_451 = evaluate_retail_cpg_autonomous_replenishment_policy(
            webiq_zero_safety_recall_fcb_closed_clean=False,
        )
        self.assertFalse(rec_451.allowed)
        self.assertEqual(rec_451.http_status, 451)

        # 5. Net-position dedup & A-Class pallet spoilage prevention saving $36,750 ($138,250 net) -> 409 Confirm
        sav_409 = evaluate_retail_cpg_autonomous_replenishment_policy(
            automated_net_position_dedup_and_pallet_spoilage_savings_cents=3675000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_retail_cpg_replenishment_cents, 13825000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["retail_cpg_autonomous_replenishment_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("retail-cpg-autonomous-replenishment-sandbox", demo_zh)

    def test_agentic_protocol_stack_interoperability_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_agentic_protocol_stack_interoperability_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 6-protocol stack (MCP + A2A + ACP/UCP + AP2 + SPT/MPP 200-unit aligned) -> 200 OK ($220,000.00)
        ok_res = evaluate_agentic_protocol_stack_interoperability_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_AGENTIC_PROTOCOL_STACK_INTEROPERABILITY_SETTLED")
        self.assertEqual(ok_res.settled_agentic_protocol_stack_cents, 22000000)

        # 2. UCP handler mismatch (Link/GPay on com.stripe.payments) or MPP pay_argv shell injection -> 403 Blocked
        ucp_403 = evaluate_agentic_protocol_stack_interoperability_policy(
            ucp_handler_split_and_mpp_argv_sanitized_verified=False,
        )
        self.assertFalse(ucp_403.allowed)
        self.assertEqual(ucp_403.http_status, 403)
        self.assertEqual(
            ucp_403.decision_code,
            "UCP_HANDLER_MISMATCH_LINK_GPAY_TRAP_OR_MPP_ARGV_INJECTION_BLOCKED",
        )

        # 3. AP2 MandateVC ceiling exceeded or unaligned MPP sub-cent truncation -> 422 Blocked
        ap2_422 = evaluate_agentic_protocol_stack_interoperability_policy(
            ap2_mandate_ceiling_and_200unit_mpp_alignment_verified=False,
        )
        self.assertFalse(ap2_422.allowed)
        self.assertEqual(ap2_422.http_status, 422)
        self.assertEqual(
            ap2_422.decision_code,
            "AP2_MANDATE_CEILING_EXCEEDED_OR_UNALIGNED_MPP_SUBCENT_TRUNCATION_BLOCKED",
        )

        # 4. MCP OAuth 2.1 RFC 9207 iss case mismatch or post-Nov 30 static sk_live_* key -> 451 Hold
        iss_451 = evaluate_agentic_protocol_stack_interoperability_policy(
            webiq_mcp_rfc9207_exact_iss_and_oauth21_clean=False,
        )
        self.assertFalse(iss_451.allowed)
        self.assertEqual(iss_451.http_status, 451)

        # 5. Unified dual-ecosystem adapter (ACP+UCP) & 200-unit zero-truncation MPP saving $44,000 ($176,000 net) -> 409 Confirm
        sav_409 = evaluate_agentic_protocol_stack_interoperability_policy(
            automated_dual_ecosystem_adapter_and_zero_truncation_savings_cents=4400000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_agentic_protocol_stack_cents, 17600000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["agentic_protocol_stack_interoperability_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("agentic-protocol-stack-interoperability-sandbox", demo_zh)

    def test_chargeback_ce30_friendly_fraud_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_chargeback_ce30_friendly_fraud_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant RDR micro-deflection + Visa CE 3.0 120-365d match + AP2 MandateVC signature -> 200 OK ($165,000.00)
        ok_res = evaluate_chargeback_ce30_friendly_fraud_agent_policy()
        self.assertTrue(ok_res.allowed)
        self.assertEqual(ok_res.http_status, 200)
        self.assertEqual(ok_res.decision_code, "VERIFIED_CHARGEBACK_CE30_REPRESENTMENT_SETTLED")
        self.assertEqual(ok_res.settled_chargeback_ce30_agent_cents, 16500000)

        # 2. Forged/hallucinated dispute evidence or missing AP2 MandateVC signature -> 403 Blocked
        frg_403 = evaluate_chargeback_ce30_friendly_fraud_agent_policy(
            unforged_immutable_evidence_and_ap2_mandate_signature_verified=False,
        )
        self.assertFalse(frg_403.allowed)
        self.assertEqual(frg_403.http_status, 403)
        self.assertEqual(
            frg_403.decision_code,
            "FORGED_DISPUTE_EVIDENCE_OR_MISSING_AP2_MANDATE_SIGNATURE_BLOCKED",
        )

        # 3. Invalid Visa CE 3.0 window (<120d / >365d), <2 matched elements, or negative-EV micro-fight -> 422 Blocked
        ce3_422 = evaluate_chargeback_ce30_friendly_fraud_agent_policy(
            ce30_120_to_365d_two_orders_and_positive_ev_fight_verified=False,
        )
        self.assertFalse(ce3_422.allowed)
        self.assertEqual(ce3_422.http_status, 422)
        self.assertEqual(
            ce3_422.decision_code,
            "CE30_HISTORICAL_FOOTPRINT_WINDOW_OR_ELEMENT_COUNT_INVALID_BLOCKED",
        )

        # 4. Merchant VDMP ratio approaching 0.9% ceiling or missing Web IQ policy snapshot hash -> 451 Hold
        vdm_451 = evaluate_chargeback_ce30_friendly_fraud_agent_policy(
            webiq_vdmp_under_09pct_and_policy_snapshot_hash_clean=False,
        )
        self.assertFalse(vdm_451.allowed)
        self.assertEqual(vdm_451.http_status, 451)

        # 5. Automated RDR micro-deflection & Visa CE 3.0 high-ticket recovery saving $34,650 ($130,350 net) -> 409 Confirm
        sav_409 = evaluate_chargeback_ce30_friendly_fraud_agent_policy(
            automated_rdr_micro_deflection_and_ce30_recovery_savings_cents=3465000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_chargeback_ce30_agent_cents, 13035000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["chargeback_ce30_friendly_fraud_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("chargeback-ce30-friendly-fraud-agent-sandbox", demo_zh)

    def test_bnpl_webview_margin_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_bnpl_webview_margin_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant BNPL WebView handover + 0% APR + post-MDR margin safe -> 200 OK
        ok = evaluate_bnpl_webview_margin_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_bnpl_webview_margin_cents, 15500000)

        # 2. Headless browser automation on BNPL WebView or forwarding requires_action -> 403 Forbidden
        aut_403 = evaluate_bnpl_webview_margin_agent_policy(
            no_headless_webview_automation_or_forwarded_requires_action=False,
        )
        self.assertFalse(aut_403.allowed)
        self.assertEqual(aut_403.http_status, 403)

        # 3. 6.5% BNPL MDR wiping out promo margin or 24.99% APR exceeding buyer mandate -> 422 Unprocessable
        mdr_422 = evaluate_bnpl_webview_margin_agent_policy(
            post_mdr_margin_and_buyer_apr_cap_verified=False,
        )
        self.assertFalse(mdr_422.allowed)
        self.assertEqual(mdr_422.http_status, 422)

        # 4. Unattended background task without device control or un-reamortized partial refund -> 451 Hold
        dev_451 = evaluate_bnpl_webview_margin_agent_policy(
            device_navigation_control_and_partial_refund_reamortization_clean=False,
        )
        self.assertFalse(dev_451.allowed)
        self.assertEqual(dev_451.http_status, 451)

        # 5. Dynamic post-MDR margin routing + unattended SPT fallback saving $32,550 ($122,450 net) -> 409 Confirm
        sav_409 = evaluate_bnpl_webview_margin_agent_policy(
            dynamic_mdr_routing_and_spt_fallback_savings_cents=3255000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_bnpl_webview_margin_cents, 12245000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["bnpl_webview_margin_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("bnpl-webview-margin-agent-sandbox", demo_zh)

    def test_cross_border_tax_mor_ddp_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cross_border_tax_mor_ddp_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant VIES verification + DDP duty pre-clearance + landed total within mandate -> 200 OK
        ok = evaluate_cross_border_tax_mor_ddp_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_cross_border_tax_ddp_cents, 18500000)

        # 2. Invalid VIES VAT number or domestic reverse-charge abuse -> 403 Forbidden
        vie_403 = evaluate_cross_border_tax_mor_ddp_agent_policy(
            live_vies_vat_and_cross_border_reverse_charge_verified=False,
        )
        self.assertFalse(vie_403.allowed)
        self.assertEqual(vie_403.http_status, 403)

        # 3. Tax + duty landed total exceeding mandate ceiling or missing HS code -> 422 Unprocessable
        inc_422 = evaluate_cross_border_tax_mor_ddp_agent_policy(
            tax_duty_inclusive_total_within_mandate_and_hs_code_present=False,
        )
        self.assertFalse(inc_422.allowed)
        self.assertEqual(inc_422.http_status, 422)

        # 4. Unregistered Economic Nexus breach or DDU customs refusal risk -> 451 Hold
        nex_451 = evaluate_cross_border_tax_mor_ddp_agent_policy(
            economic_nexus_registered_and_ddp_pre_cleared=False,
        )
        self.assertFalse(nex_451.allowed)
        self.assertEqual(nex_451.http_status, 451)

        # 5. Hybrid core-SoR (Stripe Tax 0.5%) + DDP refusal elimination saving $37,000 ($148,000 net) -> 409 Confirm
        sav_409 = evaluate_cross_border_tax_mor_ddp_agent_policy(
            hybrid_sor_stripe_tax_and_ddp_refusal_savings_cents=3700000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_cross_border_tax_ddp_cents, 14800000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cross_border_tax_mor_ddp_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cross-border-tax-mor-ddp-agent-sandbox", demo_zh)

    def test_grocery_qsr_catch_weight_substitution_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_grocery_qsr_catch_weight_substitution_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant catch-weight scale capture + allergen-safe substitution -> 200 OK
        ok = evaluate_grocery_qsr_catch_weight_substitution_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_grocery_qsr_agent_cents, 14500000)

        # 2. Allergen or religious dietary conflict on substitution -> 403 Forbidden
        alg_403 = evaluate_grocery_qsr_catch_weight_substitution_agent_policy(
            allergen_and_dietary_conflict_zero_verified=False,
        )
        self.assertFalse(alg_403.allowed)
        self.assertEqual(alg_403.http_status, 403)

        # 3. Scale capture exceeding +15% pre-auth tolerance or post-prep cutoff cancel -> 422 Unprocessable
        cwt_422 = evaluate_grocery_qsr_catch_weight_substitution_agent_policy(
            catch_weight_within_15pct_preauth_and_pre_cutoff_state=False,
        )
        self.assertFalse(cwt_422.allowed)
        self.assertEqual(cwt_422.http_status, 422)

        # 4. Web IQ food-safety batch alert or extreme weather suspension -> 451 Hold
        fsa_451 = evaluate_grocery_qsr_catch_weight_substitution_agent_policy(
            webiq_food_safety_lot_and_weather_dispatch_clean=False,
        )
        self.assertFalse(fsa_451.allowed)
        self.assertEqual(fsa_451.http_status, 451)

        # 5. Catch-weight single capture + allergen-safe <=10% upgrade saving $29,000 ($116,000 net) -> 409 Confirm
        sav_409 = evaluate_grocery_qsr_catch_weight_substitution_agent_policy(
            catch_weight_single_capture_and_allergen_safe_upgrade_savings_cents=2900000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_grocery_qsr_agent_cents, 11600000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["grocery_qsr_catch_weight_substitution_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("grocery-qsr-catch-weight-substitution-agent-sandbox", demo_zh)

    def test_recommerce_trade_in_clawback_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_recommerce_trade_in_clawback_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Clean GSMA IMEI + Activation Lock OFF + Grade-A inspection release -> 200 OK
        ok = evaluate_recommerce_trade_in_clawback_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_recommerce_trade_in_cents, 19500000)

        # 2. Stolen GSMA IMEI, iCloud Activation Lock ON, or dummy phone swap -> 403 Forbidden
        lck_403 = evaluate_recommerce_trade_in_clawback_agent_policy(
            gsma_imei_clean_and_activation_lock_off_verified=False,
        )
        self.assertFalse(lck_403.allowed)
        self.assertEqual(lck_403.http_status, 403)

        # 3. Expired 14-day return window or unconsented re-grading clawback -> 422 Unprocessable
        exp_422 = evaluate_recommerce_trade_in_clawback_agent_policy(
            within_14d_window_and_regrading_buyer_consented=False,
        )
        self.assertFalse(exp_422.allowed)
        self.assertEqual(exp_422.http_status, 422)

        # 4. Web IQ launch-week wholesale residual crash (>12%) -> 451 Hold
        res_451 = evaluate_recommerce_trade_in_clawback_agent_policy(
            webiq_wholesale_residual_stable_and_serial_clean=False,
        )
        self.assertFalse(res_451.allowed)
        self.assertEqual(res_451.http_status, 451)

        # 5. Mirror pre-check + secured clawback hold partial capture saving $40,950 ($154,050 net) -> 409 Confirm
        sav_409 = evaluate_recommerce_trade_in_clawback_agent_policy(
            mirror_precheck_and_clawback_hold_recovery_savings_cents=4095000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_recommerce_trade_in_cents, 15405000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["recommerce_trade_in_clawback_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("recommerce-trade-in-clawback-agent-sandbox", demo_zh)

    def test_retail_media_rmn_roas_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_retail_media_rmn_roas_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Buy-Box active + core sizes in stock + contribution-margin iROAS bid -> 200 OK
        ok = evaluate_retail_media_rmn_roas_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_retail_media_rmn_cents, 20500000)

        # 2. Lost Buy Box or core-size stockout ad spend waste -> 403 Forbidden
        buy_403 = evaluate_retail_media_rmn_roas_agent_policy(
            buybox_active_and_core_sizes_in_stock_verified=False,
        )
        self.assertFalse(buy_403.allowed)
        self.assertEqual(buy_403.http_status, 403)

        # 3. Bid exceeding SKU contribution-margin breakeven or brand organic cannibalization -> 422 Unprocessable
        can_422 = evaluate_retail_media_rmn_roas_agent_policy(
            bid_within_contribution_margin_and_no_brand_cannibalization=False,
        )
        self.assertFalse(can_422.allowed)
        self.assertEqual(can_422.http_status, 422)

        # 4. Web IQ midnight click-bot IVT spike or hourly pacing exhaustion -> 451 Hold
        ivt_451 = evaluate_retail_media_rmn_roas_agent_policy(
            webiq_ad_click_ivt_and_hourly_pacing_clean=False,
        )
        self.assertFalse(ivt_451.allowed)
        self.assertEqual(ivt_451.http_status, 451)

        # 5. Stockout auto-pause + brand anti-cannibalization saving $45,100 ($159,900 net) -> 409 Confirm
        sav_409 = evaluate_retail_media_rmn_roas_agent_policy(
            stockout_auto_pause_and_anti_cannibalization_savings_cents=4510000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_retail_media_rmn_cents, 15990000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["retail_media_rmn_roas_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("retail-media-rmn-roas-agent-sandbox", demo_zh)

    def test_b2b_csm_expansion_coterm_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_csm_expansion_coterm_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant zero-incident + co-termed daily proration + Stripe v2 OCA expansion -> 200 OK
        ok = evaluate_b2b_csm_expansion_coterm_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_b2b_csm_expansion_cents, 21500000)

        # 2. Upsell outreach during active P1 incident or re-initiating non-terminal orca_* -> 403 Forbidden
        inc_403 = evaluate_b2b_csm_expansion_coterm_agent_policy(
            no_active_p1_incident_and_oca_non_terminal_reinit_clean=False,
        )
        self.assertFalse(inc_403.allowed)
        self.assertEqual(inc_403.http_status, 403)

        # 3. Non-co-termed billing cycle or overwriting grandfathered base seat rate -> 422 Unprocessable
        cot_422 = evaluate_b2b_csm_expansion_coterm_agent_policy(
            cotermed_daily_proration_and_grandfathered_rate_protected=False,
        )
        self.assertFalse(cot_422.allowed)
        self.assertEqual(cot_422.http_status, 422)

        # 4. Web IQ customer credit downgrade or Blanket PO balance exceeded -> 451 Hold
        crd_451 = evaluate_b2b_csm_expansion_coterm_agent_policy(
            webiq_customer_credit_and_blanket_po_balance_clean=False,
        )
        self.assertFalse(crd_451.allowed)
        self.assertEqual(crd_451.http_status, 451)

        # 5. Incident veto + self-serve co-termed OCA saving $45,150 ($169,850 net) -> 409 Confirm
        sav_409 = evaluate_b2b_csm_expansion_coterm_agent_policy(
            incident_veto_and_self_serve_coterm_oca_savings_cents=4515000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_b2b_csm_expansion_cents, 16985000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_csm_expansion_coterm_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-csm-expansion-coterm-agent-sandbox", demo_zh)

    def test_commercial_model_routing_finops_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_commercial_model_routing_finops_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant L0-L3 cascade routing + partitioned cache + L0 Decimal math -> 200 OK
        ok = evaluate_commercial_model_routing_finops_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_model_routing_finops_cents, 17000000)

        # 2. Unpartitioned cross-tenant/cross-VIP semantic cache or PII caching -> 403 Forbidden
        cac_403 = evaluate_commercial_model_routing_finops_agent_policy(
            semantic_cache_tenant_tier_partitioned_and_pii_free=False,
        )
        self.assertFalse(cac_403.allowed)
        self.assertEqual(cac_403.http_status, 403)

        # 3. Session token spend breaching margin cap or LLM arithmetic hallucination -> 422 Unprocessable
        mth_422 = evaluate_commercial_model_routing_finops_agent_policy(
            session_token_within_margin_cap_and_l0_decimal_math_used=False,
        )
        self.assertFalse(mth_422.allowed)
        self.assertEqual(mth_422.http_status, 422)

        # 4. Slow model on <4,000ms checkout hot path or regional TPM 429 -> 451 Hold
        sla_451 = evaluate_commercial_model_routing_finops_agent_policy(
            checkout_hotpath_under_4s_and_regional_tpm_quota_healthy=False,
        )
        self.assertFalse(sla_451.allowed)
        self.assertEqual(sla_451.http_status, 451)

        # 5. 4-tier cascade (40% L1 cache + 50% L2 SLM + 10% L3) saving $39,100 ($130,900 net) -> 409 Confirm
        sav_409 = evaluate_commercial_model_routing_finops_agent_policy(
            four_tier_cascade_and_prompt_cache_savings_cents=3910000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_model_routing_finops_cents, 13090000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["commercial_model_routing_finops_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("commercial-model-routing-finops-agent-sandbox", demo_zh)

    def test_loyalty_points_giftcard_promo_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_loyalty_points_giftcard_promo_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 2PC split-tender + PENDING_ESCROW points + margin floor safe -> 200 OK
        ok = evaluate_loyalty_points_giftcard_promo_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_loyalty_giftcard_promo_cents, 16000000)

        # 2. Gift-card cash-out laundering or PIN enumeration attack -> 403 Forbidden
        pin_403 = evaluate_loyalty_points_giftcard_promo_agent_policy(
            no_giftcard_cash_out_or_pin_enumeration_attack=False,
        )
        self.assertFalse(pin_403.allowed)
        self.assertEqual(pin_403.http_status, 403)

        # 3. Promo stack margin wipeout or full cash refund after spending bonus points -> 422 Unprocessable
        stk_422 = evaluate_loyalty_points_giftcard_promo_agent_policy(
            post_promo_margin_safe_and_spent_points_clawback_netted=False,
        )
        self.assertFalse(stk_422.allowed)
        self.assertEqual(stk_422.http_status, 422)

        # 4. Web IQ detection of leaked VIP promo code viral abuse -> 451 Hold
        lek_451 = evaluate_loyalty_points_giftcard_promo_agent_policy(
            webiq_promo_code_not_leaked_and_velocity_normal=False,
        )
        self.assertFalse(lek_451.allowed)
        self.assertEqual(lek_451.http_status, 451)

        # 5. 30-day points escrow + promo margin floor + 2PC split-tender saving $33,600 ($126,400 net) -> 409 Confirm
        sav_409 = evaluate_loyalty_points_giftcard_promo_agent_policy(
            pending_points_escrow_and_2pc_split_tender_savings_cents=3360000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_loyalty_giftcard_promo_cents, 12640000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["loyalty_points_giftcard_promo_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("loyalty-points-giftcard-promo-agent-sandbox", demo_zh)

    def test_b2b_trade_credit_factoring_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_trade_credit_factoring_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 3-way KYB + full-pipeline exposure safe + non-recourse factoring -> 200 OK
        ok = evaluate_b2b_trade_credit_factoring_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_b2b_trade_credit_cents, 23000000)

        # 2. Impersonated corporate domain or unverified shipping dock -> 403 Forbidden
        kyb_403 = evaluate_b2b_trade_credit_factoring_agent_policy(
            corporate_kyb_domain_and_registered_dock_verified=False,
        )
        self.assertFalse(kyb_403.allowed)
        self.assertEqual(kyb_403.http_status, 403)

        # 3. Full-pipeline exposure exceeding limit or >15d past-due invoice -> 422 Unprocessable
        exp_422 = evaluate_b2b_trade_credit_factoring_agent_policy(
            full_pipeline_exposure_within_limit_and_zero_past_due=False,
        )
        self.assertFalse(exp_422.allowed)
        self.assertEqual(exp_422.http_status, 422)

        # 4. Web IQ buyer insolvency or tax-lien filing -> 451 Hold
        sol_451 = evaluate_b2b_trade_credit_factoring_agent_policy(
            webiq_buyer_solvency_and_tax_lien_clean=False,
        )
        self.assertFalse(sol_451.allowed)
        self.assertEqual(sol_451.http_status, 451)

        # 5. Anti-impersonation KYB + hybrid non-recourse factoring saving $48,300 ($181,700 net) -> 409 Confirm
        sav_409 = evaluate_b2b_trade_credit_factoring_agent_policy(
            anti_impersonation_and_non_recourse_factoring_savings_cents=4830000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_b2b_trade_credit_cents, 18170000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_trade_credit_factoring_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-trade-credit-factoring-agent-sandbox", demo_zh)


    def test_live_event_ticketing_anti_scalper_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_live_event_ticketing_anti_scalper_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant FIDO2 passkey + contiguous zero-stranding + rotating TOTP pass -> 200 OK
        ok = evaluate_live_event_ticketing_anti_scalper_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_live_event_ticketing_cents, 19000000)

        # 2. Headless scalper bot automation or resale above face value cap -> 403 Forbidden
        bot_403 = evaluate_live_event_ticketing_anti_scalper_agent_policy(
            fido2_human_passkey_and_face_value_resale_cap_verified=False,
        )
        self.assertFalse(bot_403.allowed)
        self.assertEqual(bot_403.http_status, 403)

        # 3. Single-seat stranding in row or hidden drip-fee surprise -> 422 Unprocessable
        str_422 = evaluate_live_event_ticketing_anti_scalper_agent_policy(
            row_bitmap_zero_single_seat_stranding_and_all_in_price_clean=False,
        )
        self.assertFalse(str_422.allowed)
        self.assertEqual(str_422.http_status, 422)

        # 4. Web IQ official event postponement or cancellation -> 451 Hold
        evt_451 = evaluate_live_event_ticketing_anti_scalper_agent_policy(
            webiq_event_schedule_active_and_venue_safe=False,
        )
        self.assertFalse(evt_451.allowed)
        self.assertEqual(evt_451.http_status, 451)

        # 5. Anti-stranding bitmap + closed-loop face-value waitlist saving $39,900 ($150,100 net) -> 409 Confirm
        sav_409 = evaluate_live_event_ticketing_anti_scalper_agent_policy(
            anti_stranding_bitmap_and_face_value_waitlist_savings_cents=3990000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_live_event_ticketing_cents, 15010000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["live_event_ticketing_anti_scalper_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("live-event-ticketing-anti-scalper-agent-sandbox", demo_zh)

    def test_embedded_insurance_fnol_claims_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_embedded_insurance_fnol_claims_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant live parallax capture + SN match + direct B2B repair settlement -> 200 OK
        ok = evaluate_embedded_insurance_fnol_claims_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_embedded_insurance_fnol_cents, 17500000)

        # 2. GenAI inpainted fake damage photo, duplicate pHash, or serial mismatch -> 403 Forbidden
        inp_403 = evaluate_embedded_insurance_fnol_claims_agent_policy(
            live_parallax_no_aigc_inpainting_and_serial_matched=False,
        )
        self.assertFalse(inp_403.allowed)
        self.assertEqual(inp_403.http_status, 403)

        # 3. Pre-existing waiting period claim or repair exceeding 65% replacement value -> 422 Unprocessable
        rep_422 = evaluate_embedded_insurance_fnol_claims_agent_policy(
            waiting_period_clear_and_repair_within_65pct_salvage_cap=False,
        )
        self.assertFalse(rep_422.allowed)
        self.assertEqual(rep_422.http_status, 422)

        # 4. Web IQ unverified carrier disruption or stale (>180d) payout key -> 451 Hold
        key_451 = evaluate_embedded_insurance_fnol_claims_agent_policy(
            webiq_carrier_event_verified_and_payout_key_under_180d=False,
        )
        self.assertFalse(key_451.allowed)
        self.assertEqual(key_451.http_status, 451)

        # 5. Anti-inpainting forensics + repair-vs-replace optimizer saving $38,500 ($136,500 net) -> 409 Confirm
        sav_409 = evaluate_embedded_insurance_fnol_claims_agent_policy(
            anti_inpainting_and_repair_replace_optimizer_savings_cents=3850000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_embedded_insurance_fnol_cents, 13650000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["embedded_insurance_fnol_claims_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("embedded-insurance-fnol-claims-agent-sandbox", demo_zh)

    def test_cross_border_fx_treasury_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cross_border_fx_treasury_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant Like-for-Like native settlement + valid FX quote TTL + historical refund lock -> 200 OK
        ok = evaluate_cross_border_fx_treasury_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_cross_border_fx_treasury_cents, 25000000)

        # 2. NY stablecoin ban or Connect stablecoin split violation -> 403 Forbidden
        nyc_403 = evaluate_cross_border_fx_treasury_agent_policy(
            no_ny_or_connect_stablecoin_violation_and_payee_verified=False,
        )
        self.assertFalse(nyc_403.allowed)
        self.assertEqual(nyc_403.http_status, 403)

        # 3. Expired FX quote TTL or spot-rate return arbitrage -> 422 Unprocessable
        ttl_422 = evaluate_cross_border_fx_treasury_agent_policy(
            fx_quote_within_ttl_and_refund_bound_to_original_charge_rate=False,
        )
        self.assertFalse(ttl_422.allowed)
        self.assertEqual(ttl_422.http_status, 422)

        # 4. Web IQ intraday FX flash crash or stale (>180d) treasury key -> 451 Hold
        vol_451 = evaluate_cross_border_fx_treasury_agent_policy(
            webiq_fx_volatility_normal_and_treasury_key_under_180d=False,
        )
        self.assertFalse(vol_451.allowed)
        self.assertEqual(vol_451.http_status, 451)

        # 5. Like-for-Like natural hedge + wholesale FX sweep saving $52,500 ($197,500 net) -> 409 Confirm
        sav_409 = evaluate_cross_border_fx_treasury_agent_policy(
            like_for_like_natural_hedge_and_wholesale_fx_savings_cents=5250000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_cross_border_fx_treasury_cents, 19750000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cross_border_fx_treasury_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cross-border-fx-treasury-agent-sandbox", demo_zh)

    def test_b2b_punchout_edi_orchestration_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_punchout_edi_orchestration_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant cXML PunchOut cart return + EDI 850/855 UOM match + 856 ASN ack -> 200 OK
        ok = evaluate_b2b_punchout_edi_orchestration_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_b2b_punchout_edi_cents, 26000000)

        # 2. Direct payment capture inside PunchOut session or SFTP inventory mode='replace' -> 403 Forbidden
        pco_403 = evaluate_b2b_punchout_edi_orchestration_agent_policy(
            punchout_disable_checkout_and_sftp_upsert_verified=False,
        )
        self.assertFalse(pco_403.allowed)
        self.assertEqual(pco_403.http_status, 403)

        # 3. EDI 850/855 UOM (EA vs CS) mismatch, price creep, or missing UNSPSC -> 422 Unprocessable
        uom_422 = evaluate_b2b_punchout_edi_orchestration_agent_policy(
            edi_850_855_uom_price_and_unspsc_matched=False,
        )
        self.assertFalse(uom_422.allowed)
        self.assertEqual(uom_422.http_status, 422)

        # 4. Missing EDI 997 acknowledgment on EDI 856 ASN (SSCC-18) -> 451 Hold
        asn_451 = evaluate_b2b_punchout_edi_orchestration_agent_policy(
            edi_856_asn_sscc18_and_997_ack_received=False,
        )
        self.assertFalse(asn_451.allowed)
        self.assertEqual(asn_451.http_status, 451)

        # 5. Touchless cXML/EDI O2C + ASN compliance saving $54,600 ($205,400 net) -> 409 Confirm
        sav_409 = evaluate_b2b_punchout_edi_orchestration_agent_policy(
            touchless_cxml_edi_o2c_and_asn_penalty_savings_cents=5460000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_b2b_punchout_edi_cents, 20540000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_punchout_edi_orchestration_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-punchout-edi-orchestration-agent-sandbox", demo_zh)

    def test_luxury_clienteling_vic_allocation_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_luxury_clienteling_vic_allocation_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant anti-tying outreach + global passport quota safe + Visa VIC + Aura DPP -> 200 OK
        ok = evaluate_luxury_clienteling_vic_allocation_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_luxury_clienteling_vic_cents, 28000000)

        # 2. Illegal pre-spend tying condition, grey-market flipper, or Visa VIC Passkey failure -> 403 Forbidden
        tye_403 = evaluate_luxury_clienteling_vic_allocation_agent_policy(
            no_illegal_tying_and_visa_vic_passkey_cvv2_verified=False,
        )
        self.assertFalse(tye_403.allowed)
        self.assertEqual(tye_403.http_status, 403)

        # 3. Global passport quota exceeded (>2/yr) or counterfeit DPP return swap -> 422 Unprocessable
        dpp_422 = evaluate_luxury_clienteling_vic_allocation_agent_policy(
            global_passport_quota_and_aura_dpp_authentic=False,
        )
        self.assertFalse(dpp_422.allowed)
        self.assertEqual(dpp_422.http_status, 422)

        # 4. Web IQ $10k+ AML/PEP alert or third-party multi-card structuring -> 451 Hold
        aml_451 = evaluate_luxury_clienteling_vic_allocation_agent_policy(
            webiq_high_value_aml_pep_and_same_name_payor_clean=False,
        )
        self.assertFalse(aml_451.allowed)
        self.assertEqual(aml_451.http_status, 451)

        # 5. Global quota lock + Aura DPP anti-swap saving $58,800 ($221,200 net) -> 409 Confirm
        sav_409 = evaluate_luxury_clienteling_vic_allocation_agent_policy(
            global_quota_and_dpp_return_swap_prevention_savings_cents=5880000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_luxury_clienteling_vic_cents, 22120000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["luxury_clienteling_vic_allocation_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("luxury-clienteling-vic-allocation-agent-sandbox", demo_zh)

    def test_cloud_telecom_cud_bill_shock_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_cloud_telecom_cud_bill_shock_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant P20 baseload CUD + bill-shock shield + Cadence SPT -> 200 OK
        ok = evaluate_cloud_telecom_cud_bill_shock_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_cloud_telecom_cud_cents, 21000000)

        # 2. SIM-swap port-out attack or passing setup_future_usage on SPT -> 403 Forbidden
        sim_403 = evaluate_cloud_telecom_cud_bill_shock_agent_policy(
            no_sim_swap_attack_and_spt_setup_future_usage_absent=False,
        )
        self.assertFalse(sim_403.allowed)
        self.assertEqual(sim_403.http_status, 403)

        # 3. Over-committed CUD above baseload or unshielded overage bill shock -> 422 Unprocessable
        cud_422 = evaluate_cloud_telecom_cud_bill_shock_agent_policy(
            cud_sized_to_p20_baseload_and_overage_shielded=False,
        )
        self.assertFalse(cud_422.allowed)
        self.assertEqual(cud_422.http_status, 422)

        # 4. Web IQ confirmed SLA outage missing minimum-commit waiver -> 451 Hold
        sla_451 = evaluate_cloud_telecom_cud_bill_shock_agent_policy(
            webiq_sla_outage_commit_waiver_applied=False,
        )
        self.assertFalse(sla_451.allowed)
        self.assertEqual(sla_451.http_status, 451)

        # 5. Baseload CUD + retroactive tier-cap shield saving $46,200 ($163,800 net) -> 409 Confirm
        sav_409 = evaluate_cloud_telecom_cud_bill_shock_agent_policy(
            baseload_cud_and_retroactive_tier_cap_savings_cents=4620000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_cloud_telecom_cud_cents, 16380000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["cloud_telecom_cud_bill_shock_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("cloud-telecom-cud-bill-shock-agent-sandbox", demo_zh)

    def test_marketplace_seller_kyb_escrow_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_marketplace_seller_kyb_escrow_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant master charge + weight/ZIP verified delivery + 15% rolling reserve -> 200 OK
        ok = evaluate_marketplace_seller_kyb_escrow_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_marketplace_seller_escrow_cents, 29000000)

        # 2. Stripe-Account header on Separate-Charges root call or seller self-dealing -> 403 Forbidden
        hdr_403 = evaluate_marketplace_seller_kyb_escrow_agent_policy(
            no_stripe_account_header_on_root_and_no_self_dealing=False,
        )
        self.assertFalse(hdr_403.allowed)
        self.assertEqual(hdr_403.http_status, 403)

        # 3. 0.02kg empty-envelope fake tracking or insufficient rolling reserve -> 422 Unprocessable
        trk_422 = evaluate_marketplace_seller_kyb_escrow_agent_policy(
            carrier_weight_zip_matched_and_rolling_reserve_funded=False,
        )
        self.assertFalse(trk_422.allowed)
        self.assertEqual(trk_422.http_status, 422)

        # 4. Web IQ seller UBO sanction/insolvency alert or stale (>180d) payout key -> 451 Hold
        ubo_451 = evaluate_marketplace_seller_kyb_escrow_agent_policy(
            webiq_seller_ubo_clean_and_payout_key_under_180d=False,
        )
        self.assertFalse(ubo_451.allowed)
        self.assertEqual(ubo_451.http_status, 451)

        # 5. Delivery escrow + 15% rolling reserve bust-out defense saving $60,900 ($229,100 net) -> 409 Confirm
        sav_409 = evaluate_marketplace_seller_kyb_escrow_agent_policy(
            delivery_escrow_and_rolling_reserve_bust_out_savings_cents=6090000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_marketplace_seller_escrow_cents, 22910000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["marketplace_seller_kyb_escrow_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("marketplace-seller-kyb-escrow-agent-sandbox", demo_zh)


    def test_gaming_digital_goods_webshop_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_gaming_digital_goods_webshop_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant adult/parental consent + BIN region match + D2C WebShop settlement -> 200 OK
        ok = evaluate_gaming_digital_goods_webshop_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_gaming_digital_webshop_cents, 22500000)

        # 2. Minor spend cap breach, missing parental passkey, or broker emulator top-up -> 403 Forbidden
        min_403 = evaluate_gaming_digital_goods_webshop_agent_policy(
            minor_spend_cap_and_parental_passkey_verified=False,
        )
        self.assertFalse(min_403.allowed)
        self.assertEqual(min_403.http_status, 403)

        # 3. Post-gacha spent-currency refund abuse or <72h P2P auction trade hold violation -> 422 Unprocessable
        clw_422 = evaluate_gaming_digital_goods_webshop_agent_policy(
            negative_gem_clawback_and_72h_trade_hold_enforced=False,
        )
        self.assertFalse(clw_422.allowed)
        self.assertEqual(clw_422.http_status, 422)

        # 4. Web IQ regional VPN BIN arbitrage -> 451 Hold
        vpn_451 = evaluate_gaming_digital_goods_webshop_agent_policy(
            webiq_bin_region_matched_and_dma_link_compliant=False,
        )
        self.assertFalse(vpn_451.allowed)
        self.assertEqual(vpn_451.http_status, 451)

        # 5. Official D2C WebShop routing + Apple Consumption telemetry saving $51,750 ($173,250 net) -> 409 Confirm
        sav_409 = evaluate_gaming_digital_goods_webshop_agent_policy(
            d2c_webshop_routing_and_apple_consumption_reply_savings_cents=5175000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_gaming_digital_webshop_cents, 17325000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["gaming_digital_goods_webshop_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("gaming-digital-goods-webshop-agent-sandbox", demo_zh)

    def test_b2b_services_sow_milestone_escrow_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_b2b_services_sow_milestone_escrow_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant sandbox CI pass + within SOW NTE cap + valid W-8BEN/W-9 -> 200 OK
        ok = evaluate_b2b_services_sow_milestone_escrow_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_b2b_services_sow_cents, 23500000)

        # 2. Off-platform circumvention or synthetic mouse-jiggler time fraud -> 403 Forbidden
        cir_403 = evaluate_b2b_services_sow_milestone_escrow_agent_policy(
            no_off_platform_circumvention_and_work_entropy_verified=False,
        )
        self.assertFalse(cir_403.allowed)
        self.assertEqual(cir_403.http_status, 403)

        # 3. Unapproved scope-creep hours exceeding SOW NTE cap or failed CI -> 422 Unprocessable
        nte_422 = evaluate_b2b_services_sow_milestone_escrow_agent_policy(
            within_sow_nte_cap_and_sandbox_ci_passed=False,
        )
        self.assertFalse(nte_422.allowed)
        self.assertEqual(nte_422.http_status, 422)

        # 4. Missing W-8BEN/W-9 tax form, AB5 misclassification risk, or stale key -> 451 Hold
        tax_451 = evaluate_b2b_services_sow_milestone_escrow_agent_policy(
            webiq_w8ben_w9_valid_and_ab5_classification_clean=False,
        )
        self.assertFalse(tax_451.allowed)
        self.assertEqual(tax_451.http_status, 451)

        # 5. Atomic IP-for-escrow swap + NTE lock saving $49,350 ($185,650 net) -> 409 Confirm
        sav_409 = evaluate_b2b_services_sow_milestone_escrow_agent_policy(
            atomic_ip_escrow_swap_and_nte_lock_savings_cents=4935000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_b2b_services_sow_cents, 18565000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["b2b_services_sow_milestone_escrow_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("b2b-services-sow-milestone-escrow-agent-sandbox", demo_zh)

    def test_travel_retail_duty_free_customs_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_travel_retail_duty_free_customs_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 5-way departure identity + customs allowance safe + airside gate capture -> 200 OK
        ok = evaluate_travel_retail_duty_free_customs_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_travel_retail_duty_free_cents, 24500000)

        # 2. Fake-departure ticket cancellation scheme or smuggling mule card sharing -> 403 Forbidden
        smg_403 = evaluate_travel_retail_duty_free_customs_agent_policy(
            five_way_departure_identity_and_no_mule_card_sharing=False,
        )
        self.assertFalse(smg_403.allowed)
        self.assertEqual(smg_403.http_status, 403)

        # 3. Customs allowance/quantity exceeded or connecting-flight >100ml liquid confiscation risk -> 422 Unprocessable
        lag_422 = evaluate_travel_retail_duty_free_customs_agent_policy(
            customs_allowance_qty_and_transit_lags_liquid_safe=False,
        )
        self.assertFalse(lag_422.allowed)
        self.assertEqual(lag_422.http_status, 422)

        # 4. Web IQ flight cancellation or last-minute gate change cutoff -> 451 Hold
        flt_451 = evaluate_travel_retail_duty_free_customs_agent_policy(
            webiq_flight_active_and_gate_sync_within_cutoff=False,
        )
        self.assertFalse(flt_451.allowed)
        self.assertEqual(flt_451.http_status, 451)

        # 5. Dynamic gate re-routing + airside manual capture saving $51,450 ($193,550 net) -> 409 Confirm
        sav_409 = evaluate_travel_retail_duty_free_customs_agent_policy(
            dynamic_gate_rerouting_and_manual_preauth_savings_cents=5145000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_travel_retail_duty_free_cents, 19355000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["travel_retail_duty_free_customs_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("travel-retail-duty-free-customs-agent-sandbox", demo_zh)

    def test_home_furnishing_spatial_white_glove_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_home_furnishing_spatial_white_glove_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant 3D elevator clearance + cabinet cutout match + white-glove anchor proof -> 200 OK
        ok = evaluate_home_furnishing_spatial_white_glove_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_home_furnishing_white_glove_cents, 21500000)

        # 2. Post-cut MTO cancellation or predatory unlisted installer fee -> 403 Forbidden
        mto_403 = evaluate_home_furnishing_spatial_white_glove_agent_policy(
            no_post_cut_mto_cancel_and_no_predatory_install_fee=False,
        )
        self.assertFalse(mto_403.allowed)
        self.assertEqual(mto_403.http_status, 403)

        # 3. 3D elevator/doorway clearance collision or cabinet cutout mismatch -> 422 Unprocessable
        clr_422 = evaluate_home_furnishing_spatial_white_glove_agent_policy(
            elevator_doorway_3d_clearance_and_cabinet_cutout_matched=False,
        )
        self.assertFalse(clr_422.allowed)
        self.assertEqual(clr_422.http_status, 422)

        # 4. Web IQ CPSC STURDY tip-over recall or missing wall-anchor proof -> 451 Hold
        tip_451 = evaluate_home_furnishing_spatial_white_glove_agent_policy(
            webiq_cpsc_sturdy_recall_clean_and_wall_anchor_verified=False,
        )
        self.assertFalse(tip_451.allowed)
        self.assertEqual(tip_451.http_status, 451)

        # 5. Modular split-box switch + pre-install audit saving $47,300 ($167,700 net) -> 409 Confirm
        sav_409 = evaluate_home_furnishing_spatial_white_glove_agent_policy(
            modular_split_box_and_pre_install_audit_savings_cents=4730000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_home_furnishing_white_glove_cents, 16770000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["home_furnishing_spatial_white_glove_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("home-furnishing-spatial-white-glove-agent-sandbox", demo_zh)


    def test_edtech_corporate_lnd_tuition_agent_selection(self) -> None:
        from lab.webiq_commerce_demo import (
            evaluate_edtech_corporate_lnd_tuition_agent_policy,
            render_webiq_live_demo_html,
            run_webiq_commerce_benchmark_suite,
        )

        # 1. Compliant accredited course + OpenBadges Grade >= B + IRS $5,250 split -> 200 OK
        ok = evaluate_edtech_corporate_lnd_tuition_agent_policy()
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.http_status, 200)
        self.assertEqual(ok.settled_edtech_corporate_lnd_cents, 16500000)

        # 2. Hardware kickback tuition fraud or unaccredited diploma mill -> 403 Forbidden
        kck_403 = evaluate_edtech_corporate_lnd_tuition_agent_policy(
            no_hardware_kickback_and_openbadges_accredited_verified=False,
        )
        self.assertFalse(kck_403.allowed)
        self.assertEqual(kck_403.http_status, 403)

        # 3. Unsplit tuition above IRS $5,250 cap, failed grade (<B), or denied pro-rata refund -> 422 Unprocessable
        irs_422 = evaluate_edtech_corporate_lnd_tuition_agent_policy(
            irs_5250_tax_split_and_grade_b_or_prorata_refund_valid=False,
        )
        self.assertFalse(irs_422.allowed)
        self.assertEqual(irs_422.http_status, 422)

        # 4. Web IQ provider accreditation revoked or closure risk -> 451 Hold
        acc_451 = evaluate_edtech_corporate_lnd_tuition_agent_policy(
            webiq_provider_accreditation_active_and_solvent=False,
        )
        self.assertFalse(acc_451.allowed)
        self.assertEqual(acc_451.http_status, 451)

        # 5. 45-day zombie-seat re-harvesting + completion escrow saving $36,300 ($128,700 net) -> 409 Confirm
        sav_409 = evaluate_edtech_corporate_lnd_tuition_agent_policy(
            zombie_seat_reharvesting_and_completion_escrow_savings_cents=3630000,
        )
        self.assertFalse(sav_409.allowed)
        self.assertEqual(sav_409.http_status, 409)
        self.assertEqual(sav_409.settled_edtech_corporate_lnd_cents, 12870000)
        self.assertEqual(sav_409.action_pill, "Confirm")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertTrue(suite["edtech_corporate_lnd_tuition_agent_guards"]["all_passed"])
        demo_zh = render_webiq_live_demo_html(suite, lang="zh")
        self.assertIn("edtech-corporate-lnd-tuition-agent-sandbox", demo_zh)

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


    def test_commercial_agent_observability_audit_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CommercialAgentObservabilityAuditPolicyInput,
            evaluate_commercial_agent_observability_audit_policy,
        )

        happy = evaluate_commercial_agent_observability_audit_policy(
            CommercialAgentObservabilityAuditPolicyInput(
                quarterly_observability_audit_budget_usd=Decimal("125000.00"),
                unredacted_pci_pan_pii_or_secret_in_trace_detected=False,
                golden_eval_regression_failure_or_broken_traceparent_detected=False,
                webiq_data_residency_breach_flag=False,
                restricted_key_age_days=30,
                tail_based_sampling_and_worm_tiering_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "OTEL_EDGE_REDACTED_FULL_FUNNEL_WORM_AUDIT_AUTHORIZED")
        self.assertTrue(str(happy["observability_audit_token"]).startswith("commercial_agent_observability_audit_mandate_"))

        pan_block = evaluate_commercial_agent_observability_audit_policy(
            CommercialAgentObservabilityAuditPolicyInput(
                quarterly_observability_audit_budget_usd=Decimal("125000.00"),
                unredacted_pci_pan_pii_or_secret_in_trace_detected=True,
                golden_eval_regression_failure_or_broken_traceparent_detected=False,
                webiq_data_residency_breach_flag=False,
                restricted_key_age_days=30,
                tail_based_sampling_and_worm_tiering_enabled=False,
            )
        )
        self.assertEqual(pan_block["http_status"], 403)
        self.assertEqual(pan_block["decision"], "UNREDACTED_PCI_PAN_PII_OR_SECRET_LEAK_IN_TRACE_BLOCKED")

        eval_block = evaluate_commercial_agent_observability_audit_policy(
            CommercialAgentObservabilityAuditPolicyInput(
                quarterly_observability_audit_budget_usd=Decimal("125000.00"),
                unredacted_pci_pan_pii_or_secret_in_trace_detected=False,
                golden_eval_regression_failure_or_broken_traceparent_detected=True,
                webiq_data_residency_breach_flag=False,
                restricted_key_age_days=30,
                tail_based_sampling_and_worm_tiering_enabled=False,
            )
        )
        self.assertEqual(eval_block["http_status"], 422)
        self.assertEqual(eval_block["decision"], "GOLDEN_EVAL_REGRESSION_FAILURE_OR_BROKEN_AUDIT_TRACE_BLOCKED")

        residency_hold = evaluate_commercial_agent_observability_audit_policy(
            CommercialAgentObservabilityAuditPolicyInput(
                quarterly_observability_audit_budget_usd=Decimal("125000.00"),
                unredacted_pci_pan_pii_or_secret_in_trace_detected=False,
                golden_eval_regression_failure_or_broken_traceparent_detected=False,
                webiq_data_residency_breach_flag=True,
                restricted_key_age_days=190,
                tail_based_sampling_and_worm_tiering_enabled=False,
            )
        )
        self.assertEqual(residency_hold["http_status"], 451)
        self.assertEqual(residency_hold["decision"], "WEBIQ_DATA_RESIDENCY_BREACH_OR_180D_AUDIT_KEY_HOLD")

        tailsample_confirm = evaluate_commercial_agent_observability_audit_policy(
            CommercialAgentObservabilityAuditPolicyInput(
                quarterly_observability_audit_budget_usd=Decimal("125000.00"),
                unredacted_pci_pan_pii_or_secret_in_trace_detected=False,
                golden_eval_regression_failure_or_broken_traceparent_detected=False,
                webiq_data_residency_breach_flag=False,
                restricted_key_age_days=30,
                tail_based_sampling_and_worm_tiering_enabled=True,
            )
        )
        self.assertEqual(tailsample_confirm["http_status"], 409)
        self.assertEqual(tailsample_confirm["savings_usd"], "32500.00")
        self.assertEqual(tailsample_confirm["approved_budget_usd"], "92500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("commercial_agent_observability_audit_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("commercial-agent-observability-audit-sandbox", html)


    def test_live_shopping_flash_sale_agent_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            LiveShoppingFlashSaleAgentPolicyInput,
            evaluate_live_shopping_flash_sale_agent_policy,
        )

        happy = evaluate_live_shopping_flash_sale_agent_policy(
            LiveShoppingFlashSaleAgentPolicyInput(
                campaign_flash_sale_gmv_usd=Decimal("320000.00"),
                inventory_hoarding_bot_or_address_limit_bypass_detected=False,
                live_verbal_price_cart_mismatch_or_oversell_detected=False,
                webiq_deceptive_anchor_price_flag=False,
                restricted_key_age_days=25,
                short_ttl_waitlist_and_instant_price_drop_refund_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "REDIS_LUA_ATOMIC_180S_LOCK_AND_ASR_PARITY_AUTHORIZED")
        self.assertTrue(str(happy["flash_sale_token"]).startswith("live_shopping_flash_sale_mandate_"))

        hoarding_block = evaluate_live_shopping_flash_sale_agent_policy(
            LiveShoppingFlashSaleAgentPolicyInput(
                campaign_flash_sale_gmv_usd=Decimal("320000.00"),
                inventory_hoarding_bot_or_address_limit_bypass_detected=True,
                live_verbal_price_cart_mismatch_or_oversell_detected=False,
                webiq_deceptive_anchor_price_flag=False,
                restricted_key_age_days=25,
                short_ttl_waitlist_and_instant_price_drop_refund_enabled=False,
            )
        )
        self.assertEqual(hoarding_block["http_status"], 403)
        self.assertEqual(hoarding_block["decision"], "INVENTORY_HOARDING_BOT_OR_ADDRESS_LIMIT_BYPASS_BLOCKED")

        mismatch_block = evaluate_live_shopping_flash_sale_agent_policy(
            LiveShoppingFlashSaleAgentPolicyInput(
                campaign_flash_sale_gmv_usd=Decimal("320000.00"),
                inventory_hoarding_bot_or_address_limit_bypass_detected=False,
                live_verbal_price_cart_mismatch_or_oversell_detected=True,
                webiq_deceptive_anchor_price_flag=False,
                restricted_key_age_days=25,
                short_ttl_waitlist_and_instant_price_drop_refund_enabled=False,
            )
        )
        self.assertEqual(mismatch_block["http_status"], 422)
        self.assertEqual(mismatch_block["decision"], "LIVE_VERBAL_PRICE_CART_MISMATCH_OR_OVERSELL_BLOCKED")

        anchor_hold = evaluate_live_shopping_flash_sale_agent_policy(
            LiveShoppingFlashSaleAgentPolicyInput(
                campaign_flash_sale_gmv_usd=Decimal("320000.00"),
                inventory_hoarding_bot_or_address_limit_bypass_detected=False,
                live_verbal_price_cart_mismatch_or_oversell_detected=False,
                webiq_deceptive_anchor_price_flag=True,
                restricted_key_age_days=192,
                short_ttl_waitlist_and_instant_price_drop_refund_enabled=False,
            )
        )
        self.assertEqual(anchor_hold["http_status"], 451)
        self.assertEqual(anchor_hold["decision"], "WEBIQ_DECEPTIVE_ANCHOR_PRICE_OR_180D_KEY_HOLD")

        pricedrop_confirm = evaluate_live_shopping_flash_sale_agent_policy(
            LiveShoppingFlashSaleAgentPolicyInput(
                campaign_flash_sale_gmv_usd=Decimal("320000.00"),
                inventory_hoarding_bot_or_address_limit_bypass_detected=False,
                live_verbal_price_cart_mismatch_or_oversell_detected=False,
                webiq_deceptive_anchor_price_flag=False,
                restricted_key_age_days=25,
                short_ttl_waitlist_and_instant_price_drop_refund_enabled=True,
            )
        )
        self.assertEqual(pricedrop_confirm["http_status"], 409)
        self.assertEqual(pricedrop_confirm["savings_usd"], "76800.00")
        self.assertEqual(pricedrop_confirm["approved_budget_usd"], "243200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("live_shopping_flash_sale_agent_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("live-shopping-flash-sale-sandbox", html)


    def test_cruise_theme_park_resort_folio_agent_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CruiseThemeParkResortFolioAgentPolicyInput,
            evaluate_cruise_theme_park_resort_folio_agent_policy,
        )

        happy = evaluate_cruise_theme_park_resort_folio_agent_policy(
            CruiseThemeParkResortFolioAgentPolicyInput(
                voyage_or_park_folio_settlement_usd=Decimal("275000.00"),
                minor_wristband_alcohol_cap_or_casino_self_exclusion_detected=False,
                folio_incremental_auth_declined_or_skipped_port_tax_withheld=False,
                webiq_ride_safety_shutdown_or_cdc_outbreak_flag=False,
                restricted_key_age_days=35,
                stepped_incremental_auth_and_auto_rain_check_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "STEPPED_FOLIO_INCREMENTAL_AUTH_AND_SINGLE_CAPTURE_AUTHORIZED")
        self.assertTrue(str(happy["resort_folio_token"]).startswith("cruise_theme_park_resort_folio_mandate_"))

        minor_block = evaluate_cruise_theme_park_resort_folio_agent_policy(
            CruiseThemeParkResortFolioAgentPolicyInput(
                voyage_or_park_folio_settlement_usd=Decimal("275000.00"),
                minor_wristband_alcohol_cap_or_casino_self_exclusion_detected=True,
                folio_incremental_auth_declined_or_skipped_port_tax_withheld=False,
                webiq_ride_safety_shutdown_or_cdc_outbreak_flag=False,
                restricted_key_age_days=35,
                stepped_incremental_auth_and_auto_rain_check_enabled=False,
            )
        )
        self.assertEqual(minor_block["http_status"], 403)
        self.assertEqual(minor_block["decision"], "MINOR_WRISTBAND_ALCOHOL_CAP_OR_CASINO_SELF_EXCLUSION_BLOCKED")

        folio_block = evaluate_cruise_theme_park_resort_folio_agent_policy(
            CruiseThemeParkResortFolioAgentPolicyInput(
                voyage_or_park_folio_settlement_usd=Decimal("275000.00"),
                minor_wristband_alcohol_cap_or_casino_self_exclusion_detected=False,
                folio_incremental_auth_declined_or_skipped_port_tax_withheld=True,
                webiq_ride_safety_shutdown_or_cdc_outbreak_flag=False,
                restricted_key_age_days=35,
                stepped_incremental_auth_and_auto_rain_check_enabled=False,
            )
        )
        self.assertEqual(folio_block["http_status"], 422)
        self.assertEqual(folio_block["decision"], "FOLIO_INCREMENTAL_AUTH_DECLINED_OR_SKIPPED_PORT_TAX_WITHHELD_BLOCKED")

        safety_hold = evaluate_cruise_theme_park_resort_folio_agent_policy(
            CruiseThemeParkResortFolioAgentPolicyInput(
                voyage_or_park_folio_settlement_usd=Decimal("275000.00"),
                minor_wristband_alcohol_cap_or_casino_self_exclusion_detected=False,
                folio_incremental_auth_declined_or_skipped_port_tax_withheld=False,
                webiq_ride_safety_shutdown_or_cdc_outbreak_flag=True,
                restricted_key_age_days=195,
                stepped_incremental_auth_and_auto_rain_check_enabled=False,
            )
        )
        self.assertEqual(safety_hold["http_status"], 451)
        self.assertEqual(safety_hold["decision"], "WEBIQ_RIDE_SAFETY_SHUTDOWN_OR_CDC_OUTBREAK_OR_180D_KEY_HOLD")

        raincheck_confirm = evaluate_cruise_theme_park_resort_folio_agent_policy(
            CruiseThemeParkResortFolioAgentPolicyInput(
                voyage_or_park_folio_settlement_usd=Decimal("275000.00"),
                minor_wristband_alcohol_cap_or_casino_self_exclusion_detected=False,
                folio_incremental_auth_declined_or_skipped_port_tax_withheld=False,
                webiq_ride_safety_shutdown_or_cdc_outbreak_flag=False,
                restricted_key_age_days=35,
                stepped_incremental_auth_and_auto_rain_check_enabled=True,
            )
        )
        self.assertEqual(raincheck_confirm["http_status"], 409)
        self.assertEqual(raincheck_confirm["savings_usd"], "63250.00")
        self.assertEqual(raincheck_confirm["approved_budget_usd"], "211750.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("cruise_theme_park_resort_folio_agent_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("cruise-theme-park-resort-folio-sandbox", html)


    def test_corporate_mice_event_banquet_agent_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CorporateMiceEventBanquetAgentPolicyInput,
            evaluate_corporate_mice_event_banquet_agent_policy,
        )

        happy = evaluate_corporate_mice_event_banquet_agent_policy(
            CorporateMiceEventBanquetAgentPolicyInput(
                conference_master_folio_budget_usd=Decimal("310000.00"),
                event_vendor_bec_wire_fraud_or_missing_coi_detected=False,
                uncredited_resold_room_attrition_or_av_service_fee_padding_detected=False,
                webiq_force_majeure_venue_closure_flag=False,
                restricted_key_age_days=30,
                flight_synced_72h_beo_and_attrition_mitigation_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "COI_VERIFIED_AND_CLEAN_BEO_MASTER_FOLIO_AUTHORIZED")
        self.assertTrue(str(happy["mice_event_token"]).startswith("corporate_mice_event_banquet_mandate_"))

        bec_block = evaluate_corporate_mice_event_banquet_agent_policy(
            CorporateMiceEventBanquetAgentPolicyInput(
                conference_master_folio_budget_usd=Decimal("310000.00"),
                event_vendor_bec_wire_fraud_or_missing_coi_detected=True,
                uncredited_resold_room_attrition_or_av_service_fee_padding_detected=False,
                webiq_force_majeure_venue_closure_flag=False,
                restricted_key_age_days=30,
                flight_synced_72h_beo_and_attrition_mitigation_enabled=False,
            )
        )
        self.assertEqual(bec_block["http_status"], 403)
        self.assertEqual(bec_block["decision"], "EVENT_VENDOR_BEC_WIRE_FRAUD_OR_MISSING_COI_INSURANCE_BLOCKED")

        attrition_block = evaluate_corporate_mice_event_banquet_agent_policy(
            CorporateMiceEventBanquetAgentPolicyInput(
                conference_master_folio_budget_usd=Decimal("310000.00"),
                event_vendor_bec_wire_fraud_or_missing_coi_detected=False,
                uncredited_resold_room_attrition_or_av_service_fee_padding_detected=True,
                webiq_force_majeure_venue_closure_flag=False,
                restricted_key_age_days=30,
                flight_synced_72h_beo_and_attrition_mitigation_enabled=False,
            )
        )
        self.assertEqual(attrition_block["http_status"], 422)
        self.assertEqual(
            attrition_block["decision"],
            "UNCREDITED_RESOLD_ROOM_ATTRITION_OR_AV_SERVICE_FEE_PADDING_BLOCKED",
        )

        fm_hold = evaluate_corporate_mice_event_banquet_agent_policy(
            CorporateMiceEventBanquetAgentPolicyInput(
                conference_master_folio_budget_usd=Decimal("310000.00"),
                event_vendor_bec_wire_fraud_or_missing_coi_detected=False,
                uncredited_resold_room_attrition_or_av_service_fee_padding_detected=False,
                webiq_force_majeure_venue_closure_flag=True,
                restricted_key_age_days=195,
                flight_synced_72h_beo_and_attrition_mitigation_enabled=False,
            )
        )
        self.assertEqual(fm_hold["http_status"], 451)
        self.assertEqual(fm_hold["decision"], "WEBIQ_FORCE_MAJEURE_VENUE_CLOSURE_OR_180D_KEY_HOLD")

        beo_confirm = evaluate_corporate_mice_event_banquet_agent_policy(
            CorporateMiceEventBanquetAgentPolicyInput(
                conference_master_folio_budget_usd=Decimal("310000.00"),
                event_vendor_bec_wire_fraud_or_missing_coi_detected=False,
                uncredited_resold_room_attrition_or_av_service_fee_padding_detected=False,
                webiq_force_majeure_venue_closure_flag=False,
                restricted_key_age_days=30,
                flight_synced_72h_beo_and_attrition_mitigation_enabled=True,
            )
        )
        self.assertEqual(beo_confirm["http_status"], 409)
        self.assertEqual(beo_confirm["savings_usd"], "74400.00")
        self.assertEqual(beo_confirm["approved_budget_usd"], "235600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("corporate_mice_event_banquet_agent_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("corporate-mice-event-banquet-sandbox", html)


    def test_fitness_wellness_subscription_agent_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            FitnessWellnessSubscriptionAgentPolicyInput,
            evaluate_fitness_wellness_subscription_agent_policy,
        )

        happy = evaluate_fitness_wellness_subscription_agent_policy(
            FitnessWellnessSubscriptionAgentPolicyInput(
                quarterly_fitness_subscription_revenue_usd=Decimal("180000.00"),
                ftc_click_to_cancel_violation_or_post_cancel_billing_detected=False,
                backfilled_seat_double_dip_penalty_or_medical_denial_detected=False,
                webiq_studio_closure_insolvency_flag=False,
                restricted_key_age_days=28,
                same_screen_freeze_and_waitlist_backfill_waiver_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "FTC_SYMMETRICAL_CANCEL_AND_FAIR_BACKFILL_BILLING_AUTHORIZED")
        self.assertTrue(str(happy["fitness_subscription_token"]).startswith("fitness_wellness_subscription_mandate_"))

        ftc_block = evaluate_fitness_wellness_subscription_agent_policy(
            FitnessWellnessSubscriptionAgentPolicyInput(
                quarterly_fitness_subscription_revenue_usd=Decimal("180000.00"),
                ftc_click_to_cancel_violation_or_post_cancel_billing_detected=True,
                backfilled_seat_double_dip_penalty_or_medical_denial_detected=False,
                webiq_studio_closure_insolvency_flag=False,
                restricted_key_age_days=28,
                same_screen_freeze_and_waitlist_backfill_waiver_enabled=False,
            )
        )
        self.assertEqual(ftc_block["http_status"], 403)
        self.assertEqual(ftc_block["decision"], "FTC_CLICK_TO_CANCEL_VIOLATION_OR_POST_CANCEL_BILLING_BLOCKED")

        backfill_block = evaluate_fitness_wellness_subscription_agent_policy(
            FitnessWellnessSubscriptionAgentPolicyInput(
                quarterly_fitness_subscription_revenue_usd=Decimal("180000.00"),
                ftc_click_to_cancel_violation_or_post_cancel_billing_detected=False,
                backfilled_seat_double_dip_penalty_or_medical_denial_detected=True,
                webiq_studio_closure_insolvency_flag=False,
                restricted_key_age_days=28,
                same_screen_freeze_and_waitlist_backfill_waiver_enabled=False,
            )
        )
        self.assertEqual(backfill_block["http_status"], 422)
        self.assertEqual(
            backfill_block["decision"],
            "BACKFILLED_SEAT_DOUBLE_DIP_PENALTY_OR_MEDICAL_DENIAL_BLOCKED",
        )

        closure_hold = evaluate_fitness_wellness_subscription_agent_policy(
            FitnessWellnessSubscriptionAgentPolicyInput(
                quarterly_fitness_subscription_revenue_usd=Decimal("180000.00"),
                ftc_click_to_cancel_violation_or_post_cancel_billing_detected=False,
                backfilled_seat_double_dip_penalty_or_medical_denial_detected=False,
                webiq_studio_closure_insolvency_flag=True,
                restricted_key_age_days=191,
                same_screen_freeze_and_waitlist_backfill_waiver_enabled=False,
            )
        )
        self.assertEqual(closure_hold["http_status"], 451)
        self.assertEqual(closure_hold["decision"], "WEBIQ_STUDIO_CLOSURE_INSOLVENCY_OR_180D_KEY_HOLD")

        freeze_confirm = evaluate_fitness_wellness_subscription_agent_policy(
            FitnessWellnessSubscriptionAgentPolicyInput(
                quarterly_fitness_subscription_revenue_usd=Decimal("180000.00"),
                ftc_click_to_cancel_violation_or_post_cancel_billing_detected=False,
                backfilled_seat_double_dip_penalty_or_medical_denial_detected=False,
                webiq_studio_closure_insolvency_flag=False,
                restricted_key_age_days=28,
                same_screen_freeze_and_waitlist_backfill_waiver_enabled=True,
            )
        )
        self.assertEqual(freeze_confirm["http_status"], 409)
        self.assertEqual(freeze_confirm["savings_usd"], "43200.00")
        self.assertEqual(freeze_confirm["approved_budget_usd"], "136800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("fitness_wellness_subscription_agent_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("fitness-wellness-subscription-sandbox", html)


    def test_cross_border_reverse_logistics_drawback_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CrossBorderReverseLogisticsDrawbackPolicyInput,
            evaluate_cross_border_reverse_logistics_drawback_policy,
        )

        happy = evaluate_cross_border_reverse_logistics_drawback_policy(
            CrossBorderReverseLogisticsDrawbackPolicyInput(
                quarterly_reverse_logistics_and_duty_pool_usd=Decimal("240000.00"),
                returnless_refund_arbitrage_ring_or_unverified_drop_off_detected=False,
                missing_cbp_7501_import_entry_or_hts_drawback_mismatch_detected=False,
                webiq_3pl_return_hub_congestion_flag=False,
                restricted_key_age_days=30,
                in_country_3pl_restock_and_99pct_duty_drawback_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "RETURN_BAR_SCAN_VERIFIED_AND_CBP_7501_DRAWBACK_AUTHORIZED")
        self.assertTrue(
            str(happy["reverse_drawback_token"]).startswith("cross_border_reverse_logistics_drawback_mandate_")
        )

        arb_block = evaluate_cross_border_reverse_logistics_drawback_policy(
            CrossBorderReverseLogisticsDrawbackPolicyInput(
                quarterly_reverse_logistics_and_duty_pool_usd=Decimal("240000.00"),
                returnless_refund_arbitrage_ring_or_unverified_drop_off_detected=True,
                missing_cbp_7501_import_entry_or_hts_drawback_mismatch_detected=False,
                webiq_3pl_return_hub_congestion_flag=False,
                restricted_key_age_days=30,
                in_country_3pl_restock_and_99pct_duty_drawback_enabled=False,
            )
        )
        self.assertEqual(arb_block["http_status"], 403)
        self.assertEqual(arb_block["decision"], "RETURNLESS_REFUND_ARBITRAGE_RING_OR_UNVERIFIED_DROP_OFF_BLOCKED")

        cbp_block = evaluate_cross_border_reverse_logistics_drawback_policy(
            CrossBorderReverseLogisticsDrawbackPolicyInput(
                quarterly_reverse_logistics_and_duty_pool_usd=Decimal("240000.00"),
                returnless_refund_arbitrage_ring_or_unverified_drop_off_detected=False,
                missing_cbp_7501_import_entry_or_hts_drawback_mismatch_detected=True,
                webiq_3pl_return_hub_congestion_flag=False,
                restricted_key_age_days=30,
                in_country_3pl_restock_and_99pct_duty_drawback_enabled=False,
            )
        )
        self.assertEqual(cbp_block["http_status"], 422)
        self.assertEqual(
            cbp_block["decision"],
            "MISSING_CBP_7501_IMPORT_ENTRY_OR_HTS_DRAWBACK_MISMATCH_BLOCKED",
        )

        hub_hold = evaluate_cross_border_reverse_logistics_drawback_policy(
            CrossBorderReverseLogisticsDrawbackPolicyInput(
                quarterly_reverse_logistics_and_duty_pool_usd=Decimal("240000.00"),
                returnless_refund_arbitrage_ring_or_unverified_drop_off_detected=False,
                missing_cbp_7501_import_entry_or_hts_drawback_mismatch_detected=False,
                webiq_3pl_return_hub_congestion_flag=True,
                restricted_key_age_days=192,
                in_country_3pl_restock_and_99pct_duty_drawback_enabled=False,
            )
        )
        self.assertEqual(hub_hold["http_status"], 451)
        self.assertEqual(hub_hold["decision"], "WEBIQ_3PL_RETURN_HUB_CONGESTION_OR_180D_KEY_HOLD")

        restock_confirm = evaluate_cross_border_reverse_logistics_drawback_policy(
            CrossBorderReverseLogisticsDrawbackPolicyInput(
                quarterly_reverse_logistics_and_duty_pool_usd=Decimal("240000.00"),
                returnless_refund_arbitrage_ring_or_unverified_drop_off_detected=False,
                missing_cbp_7501_import_entry_or_hts_drawback_mismatch_detected=False,
                webiq_3pl_return_hub_congestion_flag=False,
                restricted_key_age_days=30,
                in_country_3pl_restock_and_99pct_duty_drawback_enabled=True,
            )
        )
        self.assertEqual(restock_confirm["http_status"], 409)
        self.assertEqual(restock_confirm["savings_usd"], "62400.00")
        self.assertEqual(restock_confirm["approved_budget_usd"], "177600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("cross_border_reverse_logistics_drawback_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("cross-border-reverse-logistics-drawback-sandbox", html)

    def test_enterprise_treasury_supplier_portal_ap_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            EnterpriseTreasurySupplierPortalApPolicyInput,
            evaluate_enterprise_treasury_supplier_portal_ap_policy,
        )

        happy = evaluate_enterprise_treasury_supplier_portal_ap_policy(
            EnterpriseTreasurySupplierPortalApPolicyInput(
                quarterly_treasury_ap_portal_pool_usd=Decimal("280000.00"),
                shared_portal_credentials_or_unregistered_tap_agent_detected=False,
                unapproved_buyer_invoice_or_missing_treasury_hitl_detected=False,
                webiq_supplier_portal_domain_spoof_flag=False,
                restricted_key_age_days=30,
                tap_portal_early_discount_and_l3_vcn_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "VISA_TAP_DIRECTORY_VERIFIED_AND_TREASURY_HITL_AUTHORIZED")
        self.assertTrue(
            str(happy["treasury_portal_token"]).startswith("enterprise_treasury_supplier_portal_ap_mandate_")
        )

        cred_block = evaluate_enterprise_treasury_supplier_portal_ap_policy(
            EnterpriseTreasurySupplierPortalApPolicyInput(
                quarterly_treasury_ap_portal_pool_usd=Decimal("280000.00"),
                shared_portal_credentials_or_unregistered_tap_agent_detected=True,
                unapproved_buyer_invoice_or_missing_treasury_hitl_detected=False,
                webiq_supplier_portal_domain_spoof_flag=False,
                restricted_key_age_days=30,
                tap_portal_early_discount_and_l3_vcn_enabled=False,
            )
        )
        self.assertEqual(cred_block["http_status"], 403)
        self.assertEqual(cred_block["decision"], "SHARED_PORTAL_CREDENTIALS_OR_UNREGISTERED_TAP_AGENT_BLOCKED")

        hitl_block = evaluate_enterprise_treasury_supplier_portal_ap_policy(
            EnterpriseTreasurySupplierPortalApPolicyInput(
                quarterly_treasury_ap_portal_pool_usd=Decimal("280000.00"),
                shared_portal_credentials_or_unregistered_tap_agent_detected=False,
                unapproved_buyer_invoice_or_missing_treasury_hitl_detected=True,
                webiq_supplier_portal_domain_spoof_flag=False,
                restricted_key_age_days=30,
                tap_portal_early_discount_and_l3_vcn_enabled=False,
            )
        )
        self.assertEqual(hitl_block["http_status"], 422)
        self.assertEqual(hitl_block["decision"], "UNAPPROVED_BUYER_INVOICE_OR_MISSING_TREASURY_HITL_BLOCKED")

        spoof_hold = evaluate_enterprise_treasury_supplier_portal_ap_policy(
            EnterpriseTreasurySupplierPortalApPolicyInput(
                quarterly_treasury_ap_portal_pool_usd=Decimal("280000.00"),
                shared_portal_credentials_or_unregistered_tap_agent_detected=False,
                unapproved_buyer_invoice_or_missing_treasury_hitl_detected=False,
                webiq_supplier_portal_domain_spoof_flag=True,
                restricted_key_age_days=195,
                tap_portal_early_discount_and_l3_vcn_enabled=False,
            )
        )
        self.assertEqual(spoof_hold["http_status"], 451)
        self.assertEqual(spoof_hold["decision"], "WEBIQ_SUPPLIER_PORTAL_DOMAIN_SPOOF_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_enterprise_treasury_supplier_portal_ap_policy(
            EnterpriseTreasurySupplierPortalApPolicyInput(
                quarterly_treasury_ap_portal_pool_usd=Decimal("280000.00"),
                shared_portal_credentials_or_unregistered_tap_agent_detected=False,
                unapproved_buyer_invoice_or_missing_treasury_hitl_detected=False,
                webiq_supplier_portal_domain_spoof_flag=False,
                restricted_key_age_days=30,
                tap_portal_early_discount_and_l3_vcn_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "67200.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "212800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("enterprise_treasury_supplier_portal_ap_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("enterprise-treasury-supplier-portal-ap-sandbox", html)

    def test_social_search_native_checkout_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            SocialSearchNativeCheckoutPolicyInput,
            evaluate_social_search_native_checkout_policy,
        )

        happy = evaluate_social_search_native_checkout_policy(
            SocialSearchNativeCheckoutPolicyInput(
                quarterly_social_search_checkout_gmv_usd=Decimal("340000.00"),
                walmart_agent_profile_violation_or_missing_safety_warning_detected=False,
                ucp_brand_mor_mismatch_or_unapproved_storefront_checkout_detected=False,
                webiq_ucp_catalog_sale_price_drift_flag=False,
                restricted_key_age_days=30,
                multi_brand_shop_pay_and_ucp_native_checkout_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "UCP_BRAND_MOR_AND_CATALOG_SAFETY_WARNING_CHECKOUT_AUTHORIZED")
        self.assertTrue(
            str(happy["social_search_checkout_token"]).startswith("social_search_native_checkout_ucp_mcp_mandate_")
        )

        profile_block = evaluate_social_search_native_checkout_policy(
            SocialSearchNativeCheckoutPolicyInput(
                quarterly_social_search_checkout_gmv_usd=Decimal("340000.00"),
                walmart_agent_profile_violation_or_missing_safety_warning_detected=True,
                ucp_brand_mor_mismatch_or_unapproved_storefront_checkout_detected=False,
                webiq_ucp_catalog_sale_price_drift_flag=False,
                restricted_key_age_days=30,
                multi_brand_shop_pay_and_ucp_native_checkout_enabled=False,
            )
        )
        self.assertEqual(profile_block["http_status"], 403)
        self.assertEqual(profile_block["decision"], "WALMART_AGENT_PROFILE_VIOLATION_OR_MISSING_SAFETY_WARNING_BLOCKED")

        mor_block = evaluate_social_search_native_checkout_policy(
            SocialSearchNativeCheckoutPolicyInput(
                quarterly_social_search_checkout_gmv_usd=Decimal("340000.00"),
                walmart_agent_profile_violation_or_missing_safety_warning_detected=False,
                ucp_brand_mor_mismatch_or_unapproved_storefront_checkout_detected=True,
                webiq_ucp_catalog_sale_price_drift_flag=False,
                restricted_key_age_days=30,
                multi_brand_shop_pay_and_ucp_native_checkout_enabled=False,
            )
        )
        self.assertEqual(mor_block["http_status"], 422)
        self.assertEqual(mor_block["decision"], "UCP_BRAND_MOR_MISMATCH_OR_UNAPPROVED_STOREFRONT_CHECKOUT_BLOCKED")

        drift_hold = evaluate_social_search_native_checkout_policy(
            SocialSearchNativeCheckoutPolicyInput(
                quarterly_social_search_checkout_gmv_usd=Decimal("340000.00"),
                walmart_agent_profile_violation_or_missing_safety_warning_detected=False,
                ucp_brand_mor_mismatch_or_unapproved_storefront_checkout_detected=False,
                webiq_ucp_catalog_sale_price_drift_flag=True,
                restricted_key_age_days=190,
                multi_brand_shop_pay_and_ucp_native_checkout_enabled=False,
            )
        )
        self.assertEqual(drift_hold["http_status"], 451)
        self.assertEqual(drift_hold["decision"], "WEBIQ_UCP_CATALOG_SALE_PRICE_DRIFT_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_social_search_native_checkout_policy(
            SocialSearchNativeCheckoutPolicyInput(
                quarterly_social_search_checkout_gmv_usd=Decimal("340000.00"),
                walmart_agent_profile_violation_or_missing_safety_warning_detected=False,
                ucp_brand_mor_mismatch_or_unapproved_storefront_checkout_detected=False,
                webiq_ucp_catalog_sale_price_drift_flag=False,
                restricted_key_age_days=30,
                multi_brand_shop_pay_and_ucp_native_checkout_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "71400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "268600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("social_search_native_checkout_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("social-search-native-checkout-sandbox", html)

    def test_ecommerce_pre_purchase_anti_wrong_buy_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            EcommercePrePurchaseAntiWrongBuyPolicyInput,
            evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy,
        )

        happy = evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy(
            EcommercePrePurchaseAntiWrongBuyPolicyInput(
                quarterly_delegated_shopping_pool_usd=Decimal("312000.00"),
                unauthorized_sku_substitution_or_attribute_mismatch_detected=False,
                all_in_landed_budget_exceeded_or_delivery_deadline_missed_detected=False,
                webiq_product_spec_table_contradiction_flag=False,
                restricted_key_age_days=30,
                four_tuple_verifier_and_substitution_card_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "FROZEN_INTENT_FOUR_TUPLE_PRE_PURCHASE_VERIFIED_AUTHORIZED")
        self.assertTrue(
            str(happy["pre_purchase_verifier_token"]).startswith("ecommerce_pre_purchase_anti_wrong_buy_mandate_")
        )

        sub_block = evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy(
            EcommercePrePurchaseAntiWrongBuyPolicyInput(
                quarterly_delegated_shopping_pool_usd=Decimal("312000.00"),
                unauthorized_sku_substitution_or_attribute_mismatch_detected=True,
                all_in_landed_budget_exceeded_or_delivery_deadline_missed_detected=False,
                webiq_product_spec_table_contradiction_flag=False,
                restricted_key_age_days=30,
                four_tuple_verifier_and_substitution_card_enabled=False,
            )
        )
        self.assertEqual(sub_block["http_status"], 403)
        self.assertEqual(sub_block["decision"], "UNAUTHORIZED_SKU_SUBSTITUTION_OR_ATTRIBUTE_MISMATCH_BLOCKED")

        landed_block = evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy(
            EcommercePrePurchaseAntiWrongBuyPolicyInput(
                quarterly_delegated_shopping_pool_usd=Decimal("312000.00"),
                unauthorized_sku_substitution_or_attribute_mismatch_detected=False,
                all_in_landed_budget_exceeded_or_delivery_deadline_missed_detected=True,
                webiq_product_spec_table_contradiction_flag=False,
                restricted_key_age_days=30,
                four_tuple_verifier_and_substitution_card_enabled=False,
            )
        )
        self.assertEqual(landed_block["http_status"], 422)
        self.assertEqual(landed_block["decision"], "ALL_IN_LANDED_BUDGET_EXCEEDED_OR_DELIVERY_DEADLINE_MISSED_BLOCKED")

        spec_hold = evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy(
            EcommercePrePurchaseAntiWrongBuyPolicyInput(
                quarterly_delegated_shopping_pool_usd=Decimal("312000.00"),
                unauthorized_sku_substitution_or_attribute_mismatch_detected=False,
                all_in_landed_budget_exceeded_or_delivery_deadline_missed_detected=False,
                webiq_product_spec_table_contradiction_flag=True,
                restricted_key_age_days=191,
                four_tuple_verifier_and_substitution_card_enabled=False,
            )
        )
        self.assertEqual(spec_hold["http_status"], 451)
        self.assertEqual(spec_hold["decision"], "WEBIQ_PRODUCT_SPEC_TABLE_CONTRADICTION_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_ecommerce_pre_purchase_anti_wrong_buy_policy(
            EcommercePrePurchaseAntiWrongBuyPolicyInput(
                quarterly_delegated_shopping_pool_usd=Decimal("312000.00"),
                unauthorized_sku_substitution_or_attribute_mismatch_detected=False,
                all_in_landed_budget_exceeded_or_delivery_deadline_missed_detected=False,
                webiq_product_spec_table_contradiction_flag=False,
                restricted_key_age_days=30,
                four_tuple_verifier_and_substitution_card_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "78000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "234000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("ecommerce_pre_purchase_anti_wrong_buy_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("ecommerce-pre-purchase-anti-wrong-buy-sandbox", html)

    def test_personal_agent_persistent_intent_poppy_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            PersonalAgentPersistentIntentPoppyPolicyInput,
            evaluate_personal_agent_persistent_intent_poppy_policy,
        )

        happy = evaluate_personal_agent_persistent_intent_poppy_policy(
            PersonalAgentPersistentIntentPoppyPolicyInput(
                quarterly_persistent_intent_budget_pool_usd=Decimal("290000.00"),
                revoked_persistent_intent_or_poppy_dpop_replay_detected=False,
                cumulative_intent_budget_exceeded_or_post_tx_scope_violation_detected=False,
                webiq_recurring_intent_recall_flag=False,
                restricted_key_age_days=30,
                persistent_intent_dip_buy_and_post_tx_price_match_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "POPPY_DPOP_VERIFIED_AND_MCP_PERSISTENT_INTENT_AUTHORIZED")
        self.assertTrue(
            str(happy["persistent_intent_token"]).startswith("personal_agent_persistent_intent_poppy_mandate_")
        )

        dpop_block = evaluate_personal_agent_persistent_intent_poppy_policy(
            PersonalAgentPersistentIntentPoppyPolicyInput(
                quarterly_persistent_intent_budget_pool_usd=Decimal("290000.00"),
                revoked_persistent_intent_or_poppy_dpop_replay_detected=True,
                cumulative_intent_budget_exceeded_or_post_tx_scope_violation_detected=False,
                webiq_recurring_intent_recall_flag=False,
                restricted_key_age_days=30,
                persistent_intent_dip_buy_and_post_tx_price_match_enabled=False,
            )
        )
        self.assertEqual(dpop_block["http_status"], 403)
        self.assertEqual(dpop_block["decision"], "REVOKED_PERSISTENT_INTENT_OR_POPPY_DPOP_REPLAY_BLOCKED")

        cum_block = evaluate_personal_agent_persistent_intent_poppy_policy(
            PersonalAgentPersistentIntentPoppyPolicyInput(
                quarterly_persistent_intent_budget_pool_usd=Decimal("290000.00"),
                revoked_persistent_intent_or_poppy_dpop_replay_detected=False,
                cumulative_intent_budget_exceeded_or_post_tx_scope_violation_detected=True,
                webiq_recurring_intent_recall_flag=False,
                restricted_key_age_days=30,
                persistent_intent_dip_buy_and_post_tx_price_match_enabled=False,
            )
        )
        self.assertEqual(cum_block["http_status"], 422)
        self.assertEqual(
            cum_block["decision"],
            "CUMULATIVE_INTENT_BUDGET_EXCEEDED_OR_POST_TX_SCOPE_VIOLATION_BLOCKED",
        )

        recall_hold = evaluate_personal_agent_persistent_intent_poppy_policy(
            PersonalAgentPersistentIntentPoppyPolicyInput(
                quarterly_persistent_intent_budget_pool_usd=Decimal("290000.00"),
                revoked_persistent_intent_or_poppy_dpop_replay_detected=False,
                cumulative_intent_budget_exceeded_or_post_tx_scope_violation_detected=False,
                webiq_recurring_intent_recall_flag=True,
                restricted_key_age_days=192,
                persistent_intent_dip_buy_and_post_tx_price_match_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(recall_hold["decision"], "WEBIQ_RECURRING_INTENT_RECALL_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_personal_agent_persistent_intent_poppy_policy(
            PersonalAgentPersistentIntentPoppyPolicyInput(
                quarterly_persistent_intent_budget_pool_usd=Decimal("290000.00"),
                revoked_persistent_intent_or_poppy_dpop_replay_detected=False,
                cumulative_intent_budget_exceeded_or_post_tx_scope_violation_detected=False,
                webiq_recurring_intent_recall_flag=False,
                restricted_key_age_days=30,
                persistent_intent_dip_buy_and_post_tx_price_match_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "63800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "226200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("personal_agent_persistent_intent_poppy_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("personal-agent-persistent-intent-poppy-sandbox", html)

    def test_automotive_ev_d2c_checkout_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            AutomotiveEvD2cCheckoutPolicyInput,
            evaluate_automotive_ev_d2c_checkout_policy,
        )

        happy = evaluate_automotive_ev_d2c_checkout_policy(
            AutomotiveEvD2cCheckoutPolicyInput(
                quarterly_automotive_ev_d2c_pool_usd=Decimal("450000.00"),
                agent_bypass_cooling_off_lock_or_hidden_dealer_addon_detected=False,
                unverified_vin_ev_subsidy_or_high_fee_card_final_balance_detected=False,
                webiq_local_ev_subsidy_pool_exhausted_flag=False,
                restricted_key_age_days=30,
                in_transit_vin_match_and_split_rail_a2a_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "COOLING_OFF_DEPOSIT_AND_VIN_SUBSIDY_SPLIT_RAIL_AUTHORIZED")
        self.assertTrue(
            str(happy["automotive_ev_token"]).startswith("automotive_ev_d2c_deposit_lock_subsidy_mandate_")
        )

        lock_block = evaluate_automotive_ev_d2c_checkout_policy(
            AutomotiveEvD2cCheckoutPolicyInput(
                quarterly_automotive_ev_d2c_pool_usd=Decimal("450000.00"),
                agent_bypass_cooling_off_lock_or_hidden_dealer_addon_detected=True,
                unverified_vin_ev_subsidy_or_high_fee_card_final_balance_detected=False,
                webiq_local_ev_subsidy_pool_exhausted_flag=False,
                restricted_key_age_days=30,
                in_transit_vin_match_and_split_rail_a2a_enabled=False,
            )
        )
        self.assertEqual(lock_block["http_status"], 403)
        self.assertEqual(lock_block["decision"], "AGENT_BYPASS_COOLING_OFF_LOCK_OR_HIDDEN_DEALER_ADDON_BLOCKED")

        vin_block = evaluate_automotive_ev_d2c_checkout_policy(
            AutomotiveEvD2cCheckoutPolicyInput(
                quarterly_automotive_ev_d2c_pool_usd=Decimal("450000.00"),
                agent_bypass_cooling_off_lock_or_hidden_dealer_addon_detected=False,
                unverified_vin_ev_subsidy_or_high_fee_card_final_balance_detected=True,
                webiq_local_ev_subsidy_pool_exhausted_flag=False,
                restricted_key_age_days=30,
                in_transit_vin_match_and_split_rail_a2a_enabled=False,
            )
        )
        self.assertEqual(vin_block["http_status"], 422)
        self.assertEqual(
            vin_block["decision"],
            "UNVERIFIED_VIN_EV_SUBSIDY_OR_HIGH_FEE_CARD_FINAL_BALANCE_BLOCKED",
        )

        sub_hold = evaluate_automotive_ev_d2c_checkout_policy(
            AutomotiveEvD2cCheckoutPolicyInput(
                quarterly_automotive_ev_d2c_pool_usd=Decimal("450000.00"),
                agent_bypass_cooling_off_lock_or_hidden_dealer_addon_detected=False,
                unverified_vin_ev_subsidy_or_high_fee_card_final_balance_detected=False,
                webiq_local_ev_subsidy_pool_exhausted_flag=True,
                restricted_key_age_days=193,
                in_transit_vin_match_and_split_rail_a2a_enabled=False,
            )
        )
        self.assertEqual(sub_hold["http_status"], 451)
        self.assertEqual(sub_hold["decision"], "WEBIQ_LOCAL_EV_SUBSIDY_POOL_EXHAUSTED_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_automotive_ev_d2c_checkout_policy(
            AutomotiveEvD2cCheckoutPolicyInput(
                quarterly_automotive_ev_d2c_pool_usd=Decimal("450000.00"),
                agent_bypass_cooling_off_lock_or_hidden_dealer_addon_detected=False,
                unverified_vin_ev_subsidy_or_high_fee_card_final_balance_detected=False,
                webiq_local_ev_subsidy_pool_exhausted_flag=False,
                restricted_key_age_days=30,
                in_transit_vin_match_and_split_rail_a2a_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "94500.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "355500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("automotive_ev_d2c_checkout_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("automotive-ev-d2c-checkout-sandbox", html)

    def test_consumer_healthcare_medspa_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            ConsumerHealthcareMedspaEscrowPolicyInput,
            evaluate_consumer_healthcare_medspa_escrow_policy,
        )

        happy = evaluate_consumer_healthcare_medspa_escrow_policy(
            ConsumerHealthcareMedspaEscrowPolicyInput(
                quarterly_healthcare_package_escrow_pool_usd=Decimal("250000.00"),
                duplicate_udi_counterfeit_scan_or_coerced_clinic_loan_detected=False,
                premature_full_package_payout_or_punitive_refund_deduction_detected=False,
                webiq_clinic_license_suspension_flag=False,
                restricted_key_age_days=30,
                per_session_escrow_and_hsa_fsa_pretax_split_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "FOUR_FACTOR_UDI_VERIFIED_AND_PER_SESSION_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["healthcare_escrow_token"]).startswith("consumer_healthcare_medspa_escrow_mandate_")
        )

        udi_block = evaluate_consumer_healthcare_medspa_escrow_policy(
            ConsumerHealthcareMedspaEscrowPolicyInput(
                quarterly_healthcare_package_escrow_pool_usd=Decimal("250000.00"),
                duplicate_udi_counterfeit_scan_or_coerced_clinic_loan_detected=True,
                premature_full_package_payout_or_punitive_refund_deduction_detected=False,
                webiq_clinic_license_suspension_flag=False,
                restricted_key_age_days=30,
                per_session_escrow_and_hsa_fsa_pretax_split_enabled=False,
            )
        )
        self.assertEqual(udi_block["http_status"], 403)
        self.assertEqual(udi_block["decision"], "DUPLICATE_UDI_COUNTERFEIT_SCAN_OR_COERCED_CLINIC_LOAN_BLOCKED")

        payout_block = evaluate_consumer_healthcare_medspa_escrow_policy(
            ConsumerHealthcareMedspaEscrowPolicyInput(
                quarterly_healthcare_package_escrow_pool_usd=Decimal("250000.00"),
                duplicate_udi_counterfeit_scan_or_coerced_clinic_loan_detected=False,
                premature_full_package_payout_or_punitive_refund_deduction_detected=True,
                webiq_clinic_license_suspension_flag=False,
                restricted_key_age_days=30,
                per_session_escrow_and_hsa_fsa_pretax_split_enabled=False,
            )
        )
        self.assertEqual(payout_block["http_status"], 422)
        self.assertEqual(
            payout_block["decision"],
            "PREMATURE_FULL_PACKAGE_PAYOUT_OR_PUNITIVE_REFUND_DEDUCTION_BLOCKED",
        )

        lic_hold = evaluate_consumer_healthcare_medspa_escrow_policy(
            ConsumerHealthcareMedspaEscrowPolicyInput(
                quarterly_healthcare_package_escrow_pool_usd=Decimal("250000.00"),
                duplicate_udi_counterfeit_scan_or_coerced_clinic_loan_detected=False,
                premature_full_package_payout_or_punitive_refund_deduction_detected=False,
                webiq_clinic_license_suspension_flag=True,
                restricted_key_age_days=191,
                per_session_escrow_and_hsa_fsa_pretax_split_enabled=False,
            )
        )
        self.assertEqual(lic_hold["http_status"], 451)
        self.assertEqual(lic_hold["decision"], "WEBIQ_CLINIC_LICENSE_SUSPENSION_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_consumer_healthcare_medspa_escrow_policy(
            ConsumerHealthcareMedspaEscrowPolicyInput(
                quarterly_healthcare_package_escrow_pool_usd=Decimal("250000.00"),
                duplicate_udi_counterfeit_scan_or_coerced_clinic_loan_detected=False,
                premature_full_package_payout_or_punitive_refund_deduction_detected=False,
                webiq_clinic_license_suspension_flag=False,
                restricted_key_age_days=30,
                per_session_escrow_and_hsa_fsa_pretax_split_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "57500.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "192500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("consumer_healthcare_medspa_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("consumer-healthcare-medspa-escrow-sandbox", html)

    def test_corporate_tmc_lra_unused_ticket_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CorporateTmcLraUnusedTicketPolicyInput,
            evaluate_corporate_tmc_lra_unused_ticket_policy,
        )

        happy = evaluate_corporate_tmc_lra_unused_ticket_policy(
            CorporateTmcLraUnusedTicketPolicyInput(
                quarterly_corporate_travel_tmc_pool_usd=Decimal("320000.00"),
                unapplied_unused_ticket_credit_new_card_charge_detected=False,
                hotel_lra_rate_squatting_or_uncapped_incidentals_vcn_detected=False,
                webiq_travel_duty_of_care_alert_flag=False,
                restricted_key_age_days=30,
                utc_auto_drawdown_and_lra_spend_less_reward_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "UTC_CREDIT_APPLIED_AND_LRA_ROOM_ONLY_VCN_AUTHORIZED")
        self.assertTrue(
            str(happy["corporate_tmc_token"]).startswith("corporate_tmc_lra_unused_ticket_credit_mandate_")
        )

        utc_block = evaluate_corporate_tmc_lra_unused_ticket_policy(
            CorporateTmcLraUnusedTicketPolicyInput(
                quarterly_corporate_travel_tmc_pool_usd=Decimal("320000.00"),
                unapplied_unused_ticket_credit_new_card_charge_detected=True,
                hotel_lra_rate_squatting_or_uncapped_incidentals_vcn_detected=False,
                webiq_travel_duty_of_care_alert_flag=False,
                restricted_key_age_days=30,
                utc_auto_drawdown_and_lra_spend_less_reward_enabled=False,
            )
        )
        self.assertEqual(utc_block["http_status"], 403)
        self.assertEqual(utc_block["decision"], "UNAPPLIED_UNUSED_TICKET_CREDIT_NEW_CARD_CHARGE_BLOCKED")

        lra_block = evaluate_corporate_tmc_lra_unused_ticket_policy(
            CorporateTmcLraUnusedTicketPolicyInput(
                quarterly_corporate_travel_tmc_pool_usd=Decimal("320000.00"),
                unapplied_unused_ticket_credit_new_card_charge_detected=False,
                hotel_lra_rate_squatting_or_uncapped_incidentals_vcn_detected=True,
                webiq_travel_duty_of_care_alert_flag=False,
                restricted_key_age_days=30,
                utc_auto_drawdown_and_lra_spend_less_reward_enabled=False,
            )
        )
        self.assertEqual(lra_block["http_status"], 422)
        self.assertEqual(
            lra_block["decision"],
            "HOTEL_LRA_RATE_SQUATTING_OR_UNCAPPED_INCIDENTALS_VCN_BLOCKED",
        )

        duty_hold = evaluate_corporate_tmc_lra_unused_ticket_policy(
            CorporateTmcLraUnusedTicketPolicyInput(
                quarterly_corporate_travel_tmc_pool_usd=Decimal("320000.00"),
                unapplied_unused_ticket_credit_new_card_charge_detected=False,
                hotel_lra_rate_squatting_or_uncapped_incidentals_vcn_detected=False,
                webiq_travel_duty_of_care_alert_flag=True,
                restricted_key_age_days=192,
                utc_auto_drawdown_and_lra_spend_less_reward_enabled=False,
            )
        )
        self.assertEqual(duty_hold["http_status"], 451)
        self.assertEqual(duty_hold["decision"], "WEBIQ_TRAVEL_DUTY_OF_CARE_ALERT_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_corporate_tmc_lra_unused_ticket_policy(
            CorporateTmcLraUnusedTicketPolicyInput(
                quarterly_corporate_travel_tmc_pool_usd=Decimal("320000.00"),
                unapplied_unused_ticket_credit_new_card_charge_detected=False,
                hotel_lra_rate_squatting_or_uncapped_incidentals_vcn_detected=False,
                webiq_travel_duty_of_care_alert_flag=False,
                restricted_key_age_days=30,
                utc_auto_drawdown_and_lra_spend_less_reward_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "83200.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "236800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("corporate_tmc_lra_unused_ticket_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("corporate-tmc-lra-unused-ticket-sandbox", html)

    def test_franchise_qsr_supply_royalty_split_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            FranchiseQsrSupplyRoyaltySplitPolicyInput,
            evaluate_franchise_qsr_supply_royalty_split_policy,
        )

        happy = evaluate_franchise_qsr_supply_royalty_split_policy(
            FranchiseQsrSupplyRoyaltySplitPolicyInput(
                quarterly_franchise_commissary_royalty_pool_usd=Decimal("390000.00"),
                outside_unauthorized_sourcing_or_ip_merch_scalping_detected=False,
                fefo_shelf_life_overorder_or_royalty_split_bypass_detected=False,
                webiq_ingredient_batch_recall_menu_lock_flag=False,
                restricted_key_age_days=30,
                weather_fefo_auto_ordering_and_pos_royalty_split_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "BOM_MASS_BALANCE_AND_FEFO_POS_ROYALTY_SPLIT_AUTHORIZED")
        self.assertTrue(
            str(happy["franchise_qsr_token"]).startswith("franchise_qsr_supply_royalty_split_mandate_")
        )

        rogue_block = evaluate_franchise_qsr_supply_royalty_split_policy(
            FranchiseQsrSupplyRoyaltySplitPolicyInput(
                quarterly_franchise_commissary_royalty_pool_usd=Decimal("390000.00"),
                outside_unauthorized_sourcing_or_ip_merch_scalping_detected=True,
                fefo_shelf_life_overorder_or_royalty_split_bypass_detected=False,
                webiq_ingredient_batch_recall_menu_lock_flag=False,
                restricted_key_age_days=30,
                weather_fefo_auto_ordering_and_pos_royalty_split_enabled=False,
            )
        )
        self.assertEqual(rogue_block["http_status"], 403)
        self.assertEqual(
            rogue_block["decision"],
            "OUTSIDE_UNAUTHORIZED_SOURCING_OR_IP_MERCH_SCALPING_BLOCKED",
        )

        fefo_block = evaluate_franchise_qsr_supply_royalty_split_policy(
            FranchiseQsrSupplyRoyaltySplitPolicyInput(
                quarterly_franchise_commissary_royalty_pool_usd=Decimal("390000.00"),
                outside_unauthorized_sourcing_or_ip_merch_scalping_detected=False,
                fefo_shelf_life_overorder_or_royalty_split_bypass_detected=True,
                webiq_ingredient_batch_recall_menu_lock_flag=False,
                restricted_key_age_days=30,
                weather_fefo_auto_ordering_and_pos_royalty_split_enabled=False,
            )
        )
        self.assertEqual(fefo_block["http_status"], 422)
        self.assertEqual(
            fefo_block["decision"],
            "FEFO_SHELF_LIFE_OVERORDER_OR_ROYALTY_SPLIT_BYPASS_BLOCKED",
        )

        recall_hold = evaluate_franchise_qsr_supply_royalty_split_policy(
            FranchiseQsrSupplyRoyaltySplitPolicyInput(
                quarterly_franchise_commissary_royalty_pool_usd=Decimal("390000.00"),
                outside_unauthorized_sourcing_or_ip_merch_scalping_detected=False,
                fefo_shelf_life_overorder_or_royalty_split_bypass_detected=False,
                webiq_ingredient_batch_recall_menu_lock_flag=True,
                restricted_key_age_days=191,
                weather_fefo_auto_ordering_and_pos_royalty_split_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(
            recall_hold["decision"],
            "WEBIQ_INGREDIENT_BATCH_RECALL_MENU_LOCK_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_franchise_qsr_supply_royalty_split_policy(
            FranchiseQsrSupplyRoyaltySplitPolicyInput(
                quarterly_franchise_commissary_royalty_pool_usd=Decimal("390000.00"),
                outside_unauthorized_sourcing_or_ip_merch_scalping_detected=False,
                fefo_shelf_life_overorder_or_royalty_split_bypass_detected=False,
                webiq_ingredient_batch_recall_menu_lock_flag=False,
                restricted_key_age_days=30,
                weather_fefo_auto_ordering_and_pos_royalty_split_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "85800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "304200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("franchise_qsr_supply_royalty_split_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("franchise-qsr-supply-royalty-split-sandbox", html)

    def test_ecommerce_abandoned_cart_recovery_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            EcommerceAbandonedCartRecoveryPolicyInput,
            evaluate_ecommerce_abandoned_cart_recovery_policy,
        )

        happy = evaluate_ecommerce_abandoned_cart_recovery_policy(
            EcommerceAbandonedCartRecoveryPolicyInput(
                quarterly_abandoned_cart_promo_pool_usd=Decimal("290000.00"),
                tcpa_quiet_hours_violation_or_revoked_optin_detected=False,
                already_purchased_cross_device_or_coupon_gaming_abuse_detected=False,
                webiq_product_recall_or_messaging_channel_flag=False,
                restricted_key_age_days=30,
                concierge_first_and_rcs_one_tap_checkout_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "DUAL_TZ_TCPA_COMPLIANT_AND_IN_STOCK_CART_RECOVERY_AUTHORIZED")
        self.assertTrue(
            str(happy["abandoned_cart_token"]).startswith("ecommerce_abandoned_cart_recovery_rcs_mandate_")
        )

        tcpa_block = evaluate_ecommerce_abandoned_cart_recovery_policy(
            EcommerceAbandonedCartRecoveryPolicyInput(
                quarterly_abandoned_cart_promo_pool_usd=Decimal("290000.00"),
                tcpa_quiet_hours_violation_or_revoked_optin_detected=True,
                already_purchased_cross_device_or_coupon_gaming_abuse_detected=False,
                webiq_product_recall_or_messaging_channel_flag=False,
                restricted_key_age_days=30,
                concierge_first_and_rcs_one_tap_checkout_enabled=False,
            )
        )
        self.assertEqual(tcpa_block["http_status"], 403)
        self.assertEqual(tcpa_block["decision"], "TCPA_QUIET_HOURS_VIOLATION_OR_REVOKED_OPTIN_BLOCKED")

        gaming_block = evaluate_ecommerce_abandoned_cart_recovery_policy(
            EcommerceAbandonedCartRecoveryPolicyInput(
                quarterly_abandoned_cart_promo_pool_usd=Decimal("290000.00"),
                tcpa_quiet_hours_violation_or_revoked_optin_detected=False,
                already_purchased_cross_device_or_coupon_gaming_abuse_detected=True,
                webiq_product_recall_or_messaging_channel_flag=False,
                restricted_key_age_days=30,
                concierge_first_and_rcs_one_tap_checkout_enabled=False,
            )
        )
        self.assertEqual(gaming_block["http_status"], 422)
        self.assertEqual(
            gaming_block["decision"],
            "ALREADY_PURCHASED_CROSS_DEVICE_OR_COUPON_GAMING_ABUSE_BLOCKED",
        )

        recall_hold = evaluate_ecommerce_abandoned_cart_recovery_policy(
            EcommerceAbandonedCartRecoveryPolicyInput(
                quarterly_abandoned_cart_promo_pool_usd=Decimal("290000.00"),
                tcpa_quiet_hours_violation_or_revoked_optin_detected=False,
                already_purchased_cross_device_or_coupon_gaming_abuse_detected=False,
                webiq_product_recall_or_messaging_channel_flag=True,
                restricted_key_age_days=191,
                concierge_first_and_rcs_one_tap_checkout_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(recall_hold["decision"], "WEBIQ_PRODUCT_RECALL_OR_MESSAGING_CHANNEL_HOLD")

        opt_confirm = evaluate_ecommerce_abandoned_cart_recovery_policy(
            EcommerceAbandonedCartRecoveryPolicyInput(
                quarterly_abandoned_cart_promo_pool_usd=Decimal("290000.00"),
                tcpa_quiet_hours_violation_or_revoked_optin_detected=False,
                already_purchased_cross_device_or_coupon_gaming_abuse_detected=False,
                webiq_product_recall_or_messaging_channel_flag=False,
                restricted_key_age_days=30,
                concierge_first_and_rcs_one_tap_checkout_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "69600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "220400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("ecommerce_abandoned_cart_recovery_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("ecommerce-abandoned-cart-recovery-sandbox", html)

    def test_digital_pharmacy_optical_rx_copay_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            DigitalPharmacyOpticalRxCopayPolicyInput,
            evaluate_digital_pharmacy_optical_rx_copay_policy,
        )

        happy = evaluate_digital_pharmacy_optical_rx_copay_policy(
            DigitalPharmacyOpticalRxCopayPolicyInput(
                quarterly_pharmacy_optical_rx_pool_usd=Decimal("340000.00"),
                expired_unverified_erx_or_optical_bc_pd_mismatch_detected=False,
                cold_chain_weekend_transit_breach_or_severe_ddi_detected=False,
                webiq_fda_ndc_lot_recall_flag=False,
                restricted_key_age_days=30,
                three_rail_copay_optimizer_and_cold_chain_cutoff_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ERX_OPTICAL_PARAMETER_VERIFIED_AND_HIPAA_REDACTED_AUTHORIZED")
        self.assertTrue(
            str(happy["pharmacy_optical_token"]).startswith("digital_pharmacy_optical_rx_copay_mandate_")
        )

        erx_block = evaluate_digital_pharmacy_optical_rx_copay_policy(
            DigitalPharmacyOpticalRxCopayPolicyInput(
                quarterly_pharmacy_optical_rx_pool_usd=Decimal("340000.00"),
                expired_unverified_erx_or_optical_bc_pd_mismatch_detected=True,
                cold_chain_weekend_transit_breach_or_severe_ddi_detected=False,
                webiq_fda_ndc_lot_recall_flag=False,
                restricted_key_age_days=30,
                three_rail_copay_optimizer_and_cold_chain_cutoff_enabled=False,
            )
        )
        self.assertEqual(erx_block["http_status"], 403)
        self.assertEqual(erx_block["decision"], "EXPIRED_UNVERIFIED_ERX_OR_OPTICAL_BC_PD_MISMATCH_BLOCKED")

        cold_block = evaluate_digital_pharmacy_optical_rx_copay_policy(
            DigitalPharmacyOpticalRxCopayPolicyInput(
                quarterly_pharmacy_optical_rx_pool_usd=Decimal("340000.00"),
                expired_unverified_erx_or_optical_bc_pd_mismatch_detected=False,
                cold_chain_weekend_transit_breach_or_severe_ddi_detected=True,
                webiq_fda_ndc_lot_recall_flag=False,
                restricted_key_age_days=30,
                three_rail_copay_optimizer_and_cold_chain_cutoff_enabled=False,
            )
        )
        self.assertEqual(cold_block["http_status"], 422)
        self.assertEqual(
            cold_block["decision"],
            "COLD_CHAIN_WEEKEND_TRANSIT_BREACH_OR_SEVERE_DDI_BLOCKED",
        )

        ndc_hold = evaluate_digital_pharmacy_optical_rx_copay_policy(
            DigitalPharmacyOpticalRxCopayPolicyInput(
                quarterly_pharmacy_optical_rx_pool_usd=Decimal("340000.00"),
                expired_unverified_erx_or_optical_bc_pd_mismatch_detected=False,
                cold_chain_weekend_transit_breach_or_severe_ddi_detected=False,
                webiq_fda_ndc_lot_recall_flag=True,
                restricted_key_age_days=192,
                three_rail_copay_optimizer_and_cold_chain_cutoff_enabled=False,
            )
        )
        self.assertEqual(ndc_hold["http_status"], 451)
        self.assertEqual(ndc_hold["decision"], "WEBIQ_FDA_NDC_LOT_RECALL_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_digital_pharmacy_optical_rx_copay_policy(
            DigitalPharmacyOpticalRxCopayPolicyInput(
                quarterly_pharmacy_optical_rx_pool_usd=Decimal("340000.00"),
                expired_unverified_erx_or_optical_bc_pd_mismatch_detected=False,
                cold_chain_weekend_transit_breach_or_severe_ddi_detected=False,
                webiq_fda_ndc_lot_recall_flag=False,
                restricted_key_age_days=30,
                three_rail_copay_optimizer_and_cold_chain_cutoff_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "74800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "265200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("digital_pharmacy_optical_rx_copay_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("digital-pharmacy-optical-rx-copay-sandbox", html)

    def test_proptech_leasing_deposit_cam_ach_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            ProptechLeasingDepositCamAchPolicyInput,
            evaluate_proptech_leasing_deposit_cam_ach_policy,
        )

        happy = evaluate_proptech_leasing_deposit_cam_ach_policy(
            ProptechLeasingDepositCamAchPolicyInput(
                quarterly_proptech_leasing_rent_pool_usd=Decimal("420000.00"),
                fake_pdf_paystub_fraud_or_commingled_security_deposit_detected=False,
                undepreciated_wear_deduction_or_cam_capex_overcharge_detected=False,
                webiq_municipal_rent_control_cap_breach_flag=False,
                restricted_key_age_days=30,
                balance_preflight_a2a_rent_and_cam_audit_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "OPEN_BANKING_PAYROLL_AND_SEGREGATED_DEPOSIT_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["proptech_leasing_token"]).startswith("proptech_leasing_deposit_cam_ach_mandate_")
        )

        paystub_block = evaluate_proptech_leasing_deposit_cam_ach_policy(
            ProptechLeasingDepositCamAchPolicyInput(
                quarterly_proptech_leasing_rent_pool_usd=Decimal("420000.00"),
                fake_pdf_paystub_fraud_or_commingled_security_deposit_detected=True,
                undepreciated_wear_deduction_or_cam_capex_overcharge_detected=False,
                webiq_municipal_rent_control_cap_breach_flag=False,
                restricted_key_age_days=30,
                balance_preflight_a2a_rent_and_cam_audit_enabled=False,
            )
        )
        self.assertEqual(paystub_block["http_status"], 403)
        self.assertEqual(
            paystub_block["decision"],
            "FAKE_PDF_PAYSTUB_FRAUD_OR_COMMINGLED_SECURITY_DEPOSIT_BLOCKED",
        )

        wear_block = evaluate_proptech_leasing_deposit_cam_ach_policy(
            ProptechLeasingDepositCamAchPolicyInput(
                quarterly_proptech_leasing_rent_pool_usd=Decimal("420000.00"),
                fake_pdf_paystub_fraud_or_commingled_security_deposit_detected=False,
                undepreciated_wear_deduction_or_cam_capex_overcharge_detected=True,
                webiq_municipal_rent_control_cap_breach_flag=False,
                restricted_key_age_days=30,
                balance_preflight_a2a_rent_and_cam_audit_enabled=False,
            )
        )
        self.assertEqual(wear_block["http_status"], 422)
        self.assertEqual(
            wear_block["decision"],
            "UNDEPRECIATED_WEAR_DEDUCTION_OR_CAM_CAPEX_OVERCHARGE_BLOCKED",
        )

        rent_hold = evaluate_proptech_leasing_deposit_cam_ach_policy(
            ProptechLeasingDepositCamAchPolicyInput(
                quarterly_proptech_leasing_rent_pool_usd=Decimal("420000.00"),
                fake_pdf_paystub_fraud_or_commingled_security_deposit_detected=False,
                undepreciated_wear_deduction_or_cam_capex_overcharge_detected=False,
                webiq_municipal_rent_control_cap_breach_flag=True,
                restricted_key_age_days=191,
                balance_preflight_a2a_rent_and_cam_audit_enabled=False,
            )
        )
        self.assertEqual(rent_hold["http_status"], 451)
        self.assertEqual(
            rent_hold["decision"],
            "WEBIQ_MUNICIPAL_RENT_CONTROL_CAP_BREACH_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_proptech_leasing_deposit_cam_ach_policy(
            ProptechLeasingDepositCamAchPolicyInput(
                quarterly_proptech_leasing_rent_pool_usd=Decimal("420000.00"),
                fake_pdf_paystub_fraud_or_commingled_security_deposit_detected=False,
                undepreciated_wear_deduction_or_cam_capex_overcharge_detected=False,
                webiq_municipal_rent_control_cap_breach_flag=False,
                restricted_key_age_days=30,
                balance_preflight_a2a_rent_and_cam_audit_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "96600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "323400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("proptech_leasing_deposit_cam_ach_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("proptech-leasing-deposit-cam-ach-sandbox", html)

    def test_b2b_corporate_gifting_unclaimed_clawback_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bCorporateGiftingUnclaimedClawbackPolicyInput,
            evaluate_b2b_corporate_gifting_unclaimed_clawback_policy,
        )

        happy = evaluate_b2b_corporate_gifting_unclaimed_clawback_policy(
            B2bCorporateGiftingUnclaimedClawbackPolicyInput(
                quarterly_corporate_gifting_rewards_pool_usd=Decimal("220000.00"),
                fcpa_public_official_rfp_blackout_or_survey_bot_detected=False,
                non_refundable_upfront_gift_card_or_unreported_employee_w2_tax_detected=False,
                webiq_recipient_company_gift_policy_cap_flag=False,
                restricted_key_age_days=30,
                pay_on_claim_90d_clawback_and_recipient_choice_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "FCPA_CLEAR_AND_PAY_ON_CLAIM_W2_TAX_SYNC_AUTHORIZED")
        self.assertTrue(
            str(happy["corporate_gifting_token"]).startswith("b2b_corporate_gifting_unclaimed_clawback_mandate_")
        )

        fcpa_block = evaluate_b2b_corporate_gifting_unclaimed_clawback_policy(
            B2bCorporateGiftingUnclaimedClawbackPolicyInput(
                quarterly_corporate_gifting_rewards_pool_usd=Decimal("220000.00"),
                fcpa_public_official_rfp_blackout_or_survey_bot_detected=True,
                non_refundable_upfront_gift_card_or_unreported_employee_w2_tax_detected=False,
                webiq_recipient_company_gift_policy_cap_flag=False,
                restricted_key_age_days=30,
                pay_on_claim_90d_clawback_and_recipient_choice_enabled=False,
            )
        )
        self.assertEqual(fcpa_block["http_status"], 403)
        self.assertEqual(
            fcpa_block["decision"],
            "FCPA_PUBLIC_OFFICIAL_RFP_BLACKOUT_OR_SURVEY_BOT_BLOCKED",
        )

        breakage_block = evaluate_b2b_corporate_gifting_unclaimed_clawback_policy(
            B2bCorporateGiftingUnclaimedClawbackPolicyInput(
                quarterly_corporate_gifting_rewards_pool_usd=Decimal("220000.00"),
                fcpa_public_official_rfp_blackout_or_survey_bot_detected=False,
                non_refundable_upfront_gift_card_or_unreported_employee_w2_tax_detected=True,
                webiq_recipient_company_gift_policy_cap_flag=False,
                restricted_key_age_days=30,
                pay_on_claim_90d_clawback_and_recipient_choice_enabled=False,
            )
        )
        self.assertEqual(breakage_block["http_status"], 422)
        self.assertEqual(
            breakage_block["decision"],
            "NON_REFUNDABLE_UPFRONT_GIFT_CARD_OR_UNREPORTED_EMPLOYEE_W2_TAX_BLOCKED",
        )

        policy_hold = evaluate_b2b_corporate_gifting_unclaimed_clawback_policy(
            B2bCorporateGiftingUnclaimedClawbackPolicyInput(
                quarterly_corporate_gifting_rewards_pool_usd=Decimal("220000.00"),
                fcpa_public_official_rfp_blackout_or_survey_bot_detected=False,
                non_refundable_upfront_gift_card_or_unreported_employee_w2_tax_detected=False,
                webiq_recipient_company_gift_policy_cap_flag=True,
                restricted_key_age_days=191,
                pay_on_claim_90d_clawback_and_recipient_choice_enabled=False,
            )
        )
        self.assertEqual(policy_hold["http_status"], 451)
        self.assertEqual(
            policy_hold["decision"],
            "WEBIQ_RECIPIENT_COMPANY_GIFT_POLICY_CAP_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_b2b_corporate_gifting_unclaimed_clawback_policy(
            B2bCorporateGiftingUnclaimedClawbackPolicyInput(
                quarterly_corporate_gifting_rewards_pool_usd=Decimal("220000.00"),
                fcpa_public_official_rfp_blackout_or_survey_bot_detected=False,
                non_refundable_upfront_gift_card_or_unreported_employee_w2_tax_detected=False,
                webiq_recipient_company_gift_policy_cap_flag=False,
                restricted_key_age_days=30,
                pay_on_claim_90d_clawback_and_recipient_choice_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "52800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "167200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_corporate_gifting_unclaimed_clawback_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-corporate-gifting-unclaimed-clawback-sandbox", html)

    def test_pet_ecommerce_autoship_vet_direct_pay_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            PetEcommerceAutoshipVetDirectPayPolicyInput,
            evaluate_pet_ecommerce_autoship_vet_direct_pay_policy,
        )

        happy = evaluate_pet_ecommerce_autoship_vet_direct_pay_policy(
            PetEcommerceAutoshipVetDirectPayPolicyInput(
                quarterly_pet_autoship_vet_pool_usd=Decimal("170000.00"),
                cross_species_permethrin_toxicity_or_unverified_vet_rx_detected=False,
                puppy_growth_weight_bracket_drift_or_pre_existing_claim_detected=False,
                webiq_fda_pet_food_recall_flag=False,
                restricted_key_age_days=28,
                mer_caloric_cadence_and_5s_vet_direct_pay_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "SPECIES_WEIGHT_SAFE_AND_VET_DIRECT_PAY_AUTHORIZED")
        self.assertTrue(
            str(happy["pet_commerce_token"]).startswith("pet_ecommerce_autoship_vet_direct_pay_mandate_")
        )

        toxic_block = evaluate_pet_ecommerce_autoship_vet_direct_pay_policy(
            PetEcommerceAutoshipVetDirectPayPolicyInput(
                quarterly_pet_autoship_vet_pool_usd=Decimal("170000.00"),
                cross_species_permethrin_toxicity_or_unverified_vet_rx_detected=True,
                puppy_growth_weight_bracket_drift_or_pre_existing_claim_detected=False,
                webiq_fda_pet_food_recall_flag=False,
                restricted_key_age_days=28,
                mer_caloric_cadence_and_5s_vet_direct_pay_enabled=False,
            )
        )
        self.assertEqual(toxic_block["http_status"], 403)
        self.assertEqual(
            toxic_block["decision"],
            "CROSS_SPECIES_PERMETHRIN_TOXICITY_OR_UNVERIFIED_VET_RX_BLOCKED",
        )

        growth_block = evaluate_pet_ecommerce_autoship_vet_direct_pay_policy(
            PetEcommerceAutoshipVetDirectPayPolicyInput(
                quarterly_pet_autoship_vet_pool_usd=Decimal("170000.00"),
                cross_species_permethrin_toxicity_or_unverified_vet_rx_detected=False,
                puppy_growth_weight_bracket_drift_or_pre_existing_claim_detected=True,
                webiq_fda_pet_food_recall_flag=False,
                restricted_key_age_days=28,
                mer_caloric_cadence_and_5s_vet_direct_pay_enabled=False,
            )
        )
        self.assertEqual(growth_block["http_status"], 422)
        self.assertEqual(
            growth_block["decision"],
            "PUPPY_GROWTH_WEIGHT_BRACKET_DRIFT_OR_PRE_EXISTING_CLAIM_BLOCKED",
        )

        recall_hold = evaluate_pet_ecommerce_autoship_vet_direct_pay_policy(
            PetEcommerceAutoshipVetDirectPayPolicyInput(
                quarterly_pet_autoship_vet_pool_usd=Decimal("170000.00"),
                cross_species_permethrin_toxicity_or_unverified_vet_rx_detected=False,
                puppy_growth_weight_bracket_drift_or_pre_existing_claim_detected=False,
                webiq_fda_pet_food_recall_flag=True,
                restricted_key_age_days=191,
                mer_caloric_cadence_and_5s_vet_direct_pay_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(recall_hold["decision"], "WEBIQ_FDA_PET_FOOD_RECALL_OR_180D_KEY_HOLD")

        opt_confirm = evaluate_pet_ecommerce_autoship_vet_direct_pay_policy(
            PetEcommerceAutoshipVetDirectPayPolicyInput(
                quarterly_pet_autoship_vet_pool_usd=Decimal("170000.00"),
                cross_species_permethrin_toxicity_or_unverified_vet_rx_detected=False,
                puppy_growth_weight_bracket_drift_or_pre_existing_claim_detected=False,
                webiq_fda_pet_food_recall_flag=False,
                restricted_key_age_days=28,
                mer_caloric_cadence_and_5s_vet_direct_pay_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "49300.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "120700.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("pet_ecommerce_autoship_vet_direct_pay_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("pet-ecommerce-autoship-vet-direct-pay-sandbox", html)

    def test_coworking_flexible_office_rightsizing_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CoworkingFlexibleOfficeRightSizingPolicyInput,
            evaluate_coworking_flexible_office_rightsizing_policy,
        )

        happy = evaluate_coworking_flexible_office_rightsizing_policy(
            CoworkingFlexibleOfficeRightSizingPolicyInput(
                quarterly_coworking_workspace_pool_usd=Decimal("240000.00"),
                orphaned_ex_employee_pass_or_evergreen_price_hike_rollover_detected=False,
                zombie_dedicated_desk_renewal_or_noshow_room_overage_detected=False,
                webiq_coworking_operator_eviction_risk_flag=False,
                restricted_key_age_days=30,
                badge_telemetry_downsize_and_15m_room_release_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ACTIVE_ROSTER_BADGE_ALIGNED_AND_CAPPED_CREDITS_AUTHORIZED")
        self.assertTrue(
            str(happy["coworking_workspace_token"]).startswith("coworking_flexible_office_rightsizing_mandate_")
        )

        evergreen_block = evaluate_coworking_flexible_office_rightsizing_policy(
            CoworkingFlexibleOfficeRightSizingPolicyInput(
                quarterly_coworking_workspace_pool_usd=Decimal("240000.00"),
                orphaned_ex_employee_pass_or_evergreen_price_hike_rollover_detected=True,
                zombie_dedicated_desk_renewal_or_noshow_room_overage_detected=False,
                webiq_coworking_operator_eviction_risk_flag=False,
                restricted_key_age_days=30,
                badge_telemetry_downsize_and_15m_room_release_enabled=False,
            )
        )
        self.assertEqual(evergreen_block["http_status"], 403)
        self.assertEqual(
            evergreen_block["decision"],
            "ORPHANED_EX_EMPLOYEE_PASS_OR_EVERGREEN_PRICE_HIKE_ROLLOVER_BLOCKED",
        )

        zombie_block = evaluate_coworking_flexible_office_rightsizing_policy(
            CoworkingFlexibleOfficeRightSizingPolicyInput(
                quarterly_coworking_workspace_pool_usd=Decimal("240000.00"),
                orphaned_ex_employee_pass_or_evergreen_price_hike_rollover_detected=False,
                zombie_dedicated_desk_renewal_or_noshow_room_overage_detected=True,
                webiq_coworking_operator_eviction_risk_flag=False,
                restricted_key_age_days=30,
                badge_telemetry_downsize_and_15m_room_release_enabled=False,
            )
        )
        self.assertEqual(zombie_block["http_status"], 422)
        self.assertEqual(
            zombie_block["decision"],
            "ZOMBIE_DEDICATED_DESK_RENEWAL_OR_NOSHOW_ROOM_OVERAGE_BLOCKED",
        )

        evict_hold = evaluate_coworking_flexible_office_rightsizing_policy(
            CoworkingFlexibleOfficeRightSizingPolicyInput(
                quarterly_coworking_workspace_pool_usd=Decimal("240000.00"),
                orphaned_ex_employee_pass_or_evergreen_price_hike_rollover_detected=False,
                zombie_dedicated_desk_renewal_or_noshow_room_overage_detected=False,
                webiq_coworking_operator_eviction_risk_flag=True,
                restricted_key_age_days=191,
                badge_telemetry_downsize_and_15m_room_release_enabled=False,
            )
        )
        self.assertEqual(evict_hold["http_status"], 451)
        self.assertEqual(
            evict_hold["decision"],
            "WEBIQ_COWORKING_OPERATOR_EVICTION_RISK_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_coworking_flexible_office_rightsizing_policy(
            CoworkingFlexibleOfficeRightSizingPolicyInput(
                quarterly_coworking_workspace_pool_usd=Decimal("240000.00"),
                orphaned_ex_employee_pass_or_evergreen_price_hike_rollover_detected=False,
                zombie_dedicated_desk_renewal_or_noshow_room_overage_detected=False,
                webiq_coworking_operator_eviction_risk_flag=False,
                restricted_key_age_days=30,
                badge_telemetry_downsize_and_15m_room_release_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "69600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "170400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("coworking_flexible_office_rightsizing_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("coworking-flexible-office-rightsizing-sandbox", html)

    def test_wealth_cash_sweep_treasury_wash_sale_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            WealthCashSweepTreasuryWashSalePolicyInput,
            evaluate_wealth_cash_sweep_treasury_wash_sale_policy,
        )

        happy = evaluate_wealth_cash_sweep_treasury_wash_sale_policy(
            WealthCashSweepTreasuryWashSalePolicyInput(
                quarterly_wealth_treasury_sweep_pool_usd=Decimal("280000.00"),
                reg_bi_suitability_breach_or_unapproved_leveraged_asset_detected=False,
                irs_61d_wash_sale_index_collision_or_fdic_bank_cap_exceeded_detected=False,
                webiq_partner_bank_rating_downgrade_flag=False,
                restricted_key_age_days=30,
                alternate_index_tlh_and_multibank_fdic_sweep_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "REG_BI_ZERO_WASH_SALE_AND_MULTIBANK_FDIC_SWEEP_AUTHORIZED")
        self.assertTrue(
            str(happy["wealth_treasury_token"]).startswith("wealth_cash_sweep_treasury_wash_sale_mandate_")
        )

        regbi_block = evaluate_wealth_cash_sweep_treasury_wash_sale_policy(
            WealthCashSweepTreasuryWashSalePolicyInput(
                quarterly_wealth_treasury_sweep_pool_usd=Decimal("280000.00"),
                reg_bi_suitability_breach_or_unapproved_leveraged_asset_detected=True,
                irs_61d_wash_sale_index_collision_or_fdic_bank_cap_exceeded_detected=False,
                webiq_partner_bank_rating_downgrade_flag=False,
                restricted_key_age_days=30,
                alternate_index_tlh_and_multibank_fdic_sweep_enabled=False,
            )
        )
        self.assertEqual(regbi_block["http_status"], 403)
        self.assertEqual(
            regbi_block["decision"],
            "REG_BI_SUITABILITY_BREACH_OR_UNAPPROVED_LEVERAGED_ASSET_BLOCKED",
        )

        wash_block = evaluate_wealth_cash_sweep_treasury_wash_sale_policy(
            WealthCashSweepTreasuryWashSalePolicyInput(
                quarterly_wealth_treasury_sweep_pool_usd=Decimal("280000.00"),
                reg_bi_suitability_breach_or_unapproved_leveraged_asset_detected=False,
                irs_61d_wash_sale_index_collision_or_fdic_bank_cap_exceeded_detected=True,
                webiq_partner_bank_rating_downgrade_flag=False,
                restricted_key_age_days=30,
                alternate_index_tlh_and_multibank_fdic_sweep_enabled=False,
            )
        )
        self.assertEqual(wash_block["http_status"], 422)
        self.assertEqual(
            wash_block["decision"],
            "IRS_61D_WASH_SALE_INDEX_COLLISION_OR_FDIC_BANK_CAP_EXCEEDED_BLOCKED",
        )

        bank_hold = evaluate_wealth_cash_sweep_treasury_wash_sale_policy(
            WealthCashSweepTreasuryWashSalePolicyInput(
                quarterly_wealth_treasury_sweep_pool_usd=Decimal("280000.00"),
                reg_bi_suitability_breach_or_unapproved_leveraged_asset_detected=False,
                irs_61d_wash_sale_index_collision_or_fdic_bank_cap_exceeded_detected=False,
                webiq_partner_bank_rating_downgrade_flag=True,
                restricted_key_age_days=191,
                alternate_index_tlh_and_multibank_fdic_sweep_enabled=False,
            )
        )
        self.assertEqual(bank_hold["http_status"], 451)
        self.assertEqual(
            bank_hold["decision"],
            "WEBIQ_PARTNER_BANK_RATING_DOWNGRADE_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_wealth_cash_sweep_treasury_wash_sale_policy(
            WealthCashSweepTreasuryWashSalePolicyInput(
                quarterly_wealth_treasury_sweep_pool_usd=Decimal("280000.00"),
                reg_bi_suitability_breach_or_unapproved_leveraged_asset_detected=False,
                irs_61d_wash_sale_index_collision_or_fdic_bank_cap_exceeded_detected=False,
                webiq_partner_bank_rating_downgrade_flag=False,
                restricted_key_age_days=30,
                alternate_index_tlh_and_multibank_fdic_sweep_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "72800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "207200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("wealth_cash_sweep_treasury_wash_sale_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("wealth-cash-sweep-treasury-wash-sale-sandbox", html)

    def test_digital_media_paywall_ai_crawler_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            DigitalMediaPaywallAiCrawlerPolicyInput,
            evaluate_digital_media_paywall_ai_crawler_policy,
        )

        happy = evaluate_digital_media_paywall_ai_crawler_policy(
            DigitalMediaPaywallAiCrawlerPolicyInput(
                quarterly_digital_media_licensing_pool_usd=Decimal("250000.00"),
                unsigned_scraper_bot_or_enterprise_credential_sharing_detected=False,
                per_article_card_fee_wipeout_or_monthly_fare_cap_exceeded_detected=False,
                webiq_tdm_training_copyright_breach_flag=False,
                restricted_key_age_days=30,
                http402_crawler_licensing_and_fare_cap_bundle_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "WEB_BOT_AUTH_VERIFIED_AND_HTTP402_FARE_CAP_AUTHORIZED")
        self.assertTrue(
            str(happy["digital_media_token"]).startswith("digital_media_paywall_ai_crawler_mandate_")
        )

        scraper_block = evaluate_digital_media_paywall_ai_crawler_policy(
            DigitalMediaPaywallAiCrawlerPolicyInput(
                quarterly_digital_media_licensing_pool_usd=Decimal("250000.00"),
                unsigned_scraper_bot_or_enterprise_credential_sharing_detected=True,
                per_article_card_fee_wipeout_or_monthly_fare_cap_exceeded_detected=False,
                webiq_tdm_training_copyright_breach_flag=False,
                restricted_key_age_days=30,
                http402_crawler_licensing_and_fare_cap_bundle_enabled=False,
            )
        )
        self.assertEqual(scraper_block["http_status"], 403)
        self.assertEqual(
            scraper_block["decision"],
            "UNSIGNED_SCRAPER_BOT_OR_ENTERPRISE_CREDENTIAL_SHARING_BLOCKED",
        )

        fee_block = evaluate_digital_media_paywall_ai_crawler_policy(
            DigitalMediaPaywallAiCrawlerPolicyInput(
                quarterly_digital_media_licensing_pool_usd=Decimal("250000.00"),
                unsigned_scraper_bot_or_enterprise_credential_sharing_detected=False,
                per_article_card_fee_wipeout_or_monthly_fare_cap_exceeded_detected=True,
                webiq_tdm_training_copyright_breach_flag=False,
                restricted_key_age_days=30,
                http402_crawler_licensing_and_fare_cap_bundle_enabled=False,
            )
        )
        self.assertEqual(fee_block["http_status"], 422)
        self.assertEqual(
            fee_block["decision"],
            "PER_ARTICLE_CARD_FEE_WIPEOUT_OR_MONTHLY_FARE_CAP_EXCEEDED_BLOCKED",
        )

        tdm_hold = evaluate_digital_media_paywall_ai_crawler_policy(
            DigitalMediaPaywallAiCrawlerPolicyInput(
                quarterly_digital_media_licensing_pool_usd=Decimal("250000.00"),
                unsigned_scraper_bot_or_enterprise_credential_sharing_detected=False,
                per_article_card_fee_wipeout_or_monthly_fare_cap_exceeded_detected=False,
                webiq_tdm_training_copyright_breach_flag=True,
                restricted_key_age_days=191,
                http402_crawler_licensing_and_fare_cap_bundle_enabled=False,
            )
        )
        self.assertEqual(tdm_hold["http_status"], 451)
        self.assertEqual(
            tdm_hold["decision"],
            "WEBIQ_TDM_TRAINING_COPYRIGHT_BREACH_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_digital_media_paywall_ai_crawler_policy(
            DigitalMediaPaywallAiCrawlerPolicyInput(
                quarterly_digital_media_licensing_pool_usd=Decimal("250000.00"),
                unsigned_scraper_bot_or_enterprise_credential_sharing_detected=False,
                per_article_card_fee_wipeout_or_monthly_fare_cap_exceeded_detected=False,
                webiq_tdm_training_copyright_breach_flag=False,
                restricted_key_age_days=30,
                http402_crawler_licensing_and_fare_cap_bundle_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "62500.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "187500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("digital_media_paywall_ai_crawler_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("digital-media-paywall-ai-crawler-sandbox", html)

    def test_home_services_on_demand_repair_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            HomeServicesOnDemandRepairEscrowPolicyInput,
            evaluate_home_services_on_demand_repair_escrow_policy,
        )

        happy = evaluate_home_services_on_demand_repair_escrow_policy(
            HomeServicesOnDemandRepairEscrowPolicyInput(
                quarterly_home_services_repair_pool_usd=Decimal("290000.00"),
                unlicensed_technician_or_price_book_gouging_cap_breach_detected=False,
                long_dwell_fake_cancel_leakage_or_missing_part_swap_proof_detected=False,
                webiq_contractor_insurance_lapse_flag=False,
                restricted_key_age_days=30,
                nameplate_quote_cap_and_80_20_warranty_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "LICENSED_TECH_PRICE_BOOK_CAPPED_AND_80_20_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["home_services_token"]).startswith("home_services_on_demand_repair_escrow_mandate_")
        )

        gouge_block = evaluate_home_services_on_demand_repair_escrow_policy(
            HomeServicesOnDemandRepairEscrowPolicyInput(
                quarterly_home_services_repair_pool_usd=Decimal("290000.00"),
                unlicensed_technician_or_price_book_gouging_cap_breach_detected=True,
                long_dwell_fake_cancel_leakage_or_missing_part_swap_proof_detected=False,
                webiq_contractor_insurance_lapse_flag=False,
                restricted_key_age_days=30,
                nameplate_quote_cap_and_80_20_warranty_escrow_enabled=False,
            )
        )
        self.assertEqual(gouge_block["http_status"], 403)
        self.assertEqual(
            gouge_block["decision"],
            "UNLICENSED_TECHNICIAN_OR_PRICE_BOOK_GOUGING_CAP_BREACH_BLOCKED",
        )

        leak_block = evaluate_home_services_on_demand_repair_escrow_policy(
            HomeServicesOnDemandRepairEscrowPolicyInput(
                quarterly_home_services_repair_pool_usd=Decimal("290000.00"),
                unlicensed_technician_or_price_book_gouging_cap_breach_detected=False,
                long_dwell_fake_cancel_leakage_or_missing_part_swap_proof_detected=True,
                webiq_contractor_insurance_lapse_flag=False,
                restricted_key_age_days=30,
                nameplate_quote_cap_and_80_20_warranty_escrow_enabled=False,
            )
        )
        self.assertEqual(leak_block["http_status"], 422)
        self.assertEqual(
            leak_block["decision"],
            "LONG_DWELL_FAKE_CANCEL_LEAKAGE_OR_MISSING_PART_SWAP_PROOF_BLOCKED",
        )

        ins_hold = evaluate_home_services_on_demand_repair_escrow_policy(
            HomeServicesOnDemandRepairEscrowPolicyInput(
                quarterly_home_services_repair_pool_usd=Decimal("290000.00"),
                unlicensed_technician_or_price_book_gouging_cap_breach_detected=False,
                long_dwell_fake_cancel_leakage_or_missing_part_swap_proof_detected=False,
                webiq_contractor_insurance_lapse_flag=True,
                restricted_key_age_days=191,
                nameplate_quote_cap_and_80_20_warranty_escrow_enabled=False,
            )
        )
        self.assertEqual(ins_hold["http_status"], 451)
        self.assertEqual(
            ins_hold["decision"],
            "WEBIQ_CONTRACTOR_INSURANCE_LAPSE_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_home_services_on_demand_repair_escrow_policy(
            HomeServicesOnDemandRepairEscrowPolicyInput(
                quarterly_home_services_repair_pool_usd=Decimal("290000.00"),
                unlicensed_technician_or_price_book_gouging_cap_breach_detected=False,
                long_dwell_fake_cancel_leakage_or_missing_part_swap_proof_detected=False,
                webiq_contractor_insurance_lapse_flag=False,
                restricted_key_age_days=30,
                nameplate_quote_cap_and_80_20_warranty_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "66700.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "223300.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("home_services_on_demand_repair_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("home-services-on-demand-repair-escrow-sandbox", html)

    def test_wedding_bespoke_event_milestone_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            WeddingBespokeEventMilestoneEscrowPolicyInput,
            evaluate_wedding_bespoke_event_milestone_escrow_policy,
        )

        happy = evaluate_wedding_bespoke_event_milestone_escrow_policy(
            WeddingBespokeEventMilestoneEscrowPolicyInput(
                quarterly_wedding_event_escrow_pool_usd=Decimal("280000.00"),
                partial_vendor_slot_conflict_or_bait_switch_crew_substitution_detected=False,
                premature_100pct_wedding_payout_or_hidden_venue_vendor_fee_detected=False,
                webiq_outdoor_storm_no_rain_plan_or_180d_spt_flag=False,
                restricted_key_age_days=30,
                five_vendor_slot_saga_and_30_50_20_media_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ALL_VENDOR_SLOTS_LOCKED_AND_30_50_20_GALLERY_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["wedding_event_token"]).startswith("wedding_bespoke_event_milestone_escrow_mandate_")
        )

        slot_block = evaluate_wedding_bespoke_event_milestone_escrow_policy(
            WeddingBespokeEventMilestoneEscrowPolicyInput(
                quarterly_wedding_event_escrow_pool_usd=Decimal("280000.00"),
                partial_vendor_slot_conflict_or_bait_switch_crew_substitution_detected=True,
                premature_100pct_wedding_payout_or_hidden_venue_vendor_fee_detected=False,
                webiq_outdoor_storm_no_rain_plan_or_180d_spt_flag=False,
                restricted_key_age_days=30,
                five_vendor_slot_saga_and_30_50_20_media_escrow_enabled=False,
            )
        )
        self.assertEqual(slot_block["http_status"], 403)
        self.assertEqual(
            slot_block["decision"],
            "PARTIAL_VENDOR_SLOT_CONFLICT_OR_BAIT_SWITCH_CREW_SUBSTITUTION_BLOCKED",
        )

        media_block = evaluate_wedding_bespoke_event_milestone_escrow_policy(
            WeddingBespokeEventMilestoneEscrowPolicyInput(
                quarterly_wedding_event_escrow_pool_usd=Decimal("280000.00"),
                partial_vendor_slot_conflict_or_bait_switch_crew_substitution_detected=False,
                premature_100pct_wedding_payout_or_hidden_venue_vendor_fee_detected=True,
                webiq_outdoor_storm_no_rain_plan_or_180d_spt_flag=False,
                restricted_key_age_days=30,
                five_vendor_slot_saga_and_30_50_20_media_escrow_enabled=False,
            )
        )
        self.assertEqual(media_block["http_status"], 422)
        self.assertEqual(
            media_block["decision"],
            "PREMATURE_100PCT_WEDDING_PAYOUT_OR_HIDDEN_VENUE_VENDOR_FEE_BLOCKED",
        )

        storm_hold = evaluate_wedding_bespoke_event_milestone_escrow_policy(
            WeddingBespokeEventMilestoneEscrowPolicyInput(
                quarterly_wedding_event_escrow_pool_usd=Decimal("280000.00"),
                partial_vendor_slot_conflict_or_bait_switch_crew_substitution_detected=False,
                premature_100pct_wedding_payout_or_hidden_venue_vendor_fee_detected=False,
                webiq_outdoor_storm_no_rain_plan_or_180d_spt_flag=True,
                restricted_key_age_days=191,
                five_vendor_slot_saga_and_30_50_20_media_escrow_enabled=False,
            )
        )
        self.assertEqual(storm_hold["http_status"], 451)
        self.assertEqual(
            storm_hold["decision"],
            "WEBIQ_OUTDOOR_STORM_NO_RAIN_PLAN_OR_180D_SPT_HOLD",
        )

        opt_confirm = evaluate_wedding_bespoke_event_milestone_escrow_policy(
            WeddingBespokeEventMilestoneEscrowPolicyInput(
                quarterly_wedding_event_escrow_pool_usd=Decimal("280000.00"),
                partial_vendor_slot_conflict_or_bait_switch_crew_substitution_detected=False,
                premature_100pct_wedding_payout_or_hidden_venue_vendor_fee_detected=False,
                webiq_outdoor_storm_no_rain_plan_or_180d_spt_flag=False,
                restricted_key_age_days=30,
                five_vendor_slot_saga_and_30_50_20_media_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "67200.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "212800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("wedding_bespoke_event_milestone_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("wedding-bespoke-event-milestone-escrow-sandbox", html)

    def test_influencer_seeding_coupon_poaching_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            InfluencerSeedingCouponPoachingPolicyInput,
            evaluate_influencer_seeding_coupon_poaching_policy,
        )

        happy = evaluate_influencer_seeding_coupon_poaching_policy(
            InfluencerSeedingCouponPoachingPolicyInput(
                quarterly_influencer_seeding_affiliate_pool_usd=Decimal("220000.00"),
                coupon_extension_last_click_poaching_or_fake_influencer_seeding_detected=False,
                premature_commission_before_return_window_or_missing_ftc_ad_tag_detected=False,
                webiq_creator_brand_safety_scandal_flag=False,
                restricted_key_age_days=30,
                stand_down_lock_and_t35_net_commission_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "OAUTH_CREATOR_STAND_DOWN_LOCKED_AND_T35_NET_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["influencer_seeding_token"]).startswith("influencer_seeding_coupon_poaching_escrow_mandate_")
        )

        poach_block = evaluate_influencer_seeding_coupon_poaching_policy(
            InfluencerSeedingCouponPoachingPolicyInput(
                quarterly_influencer_seeding_affiliate_pool_usd=Decimal("220000.00"),
                coupon_extension_last_click_poaching_or_fake_influencer_seeding_detected=True,
                premature_commission_before_return_window_or_missing_ftc_ad_tag_detected=False,
                webiq_creator_brand_safety_scandal_flag=False,
                restricted_key_age_days=30,
                stand_down_lock_and_t35_net_commission_escrow_enabled=False,
            )
        )
        self.assertEqual(poach_block["http_status"], 403)
        self.assertEqual(
            poach_block["decision"],
            "COUPON_EXTENSION_LAST_CLICK_POACHING_OR_FAKE_INFLUENCER_SEEDING_BLOCKED",
        )

        ret_block = evaluate_influencer_seeding_coupon_poaching_policy(
            InfluencerSeedingCouponPoachingPolicyInput(
                quarterly_influencer_seeding_affiliate_pool_usd=Decimal("220000.00"),
                coupon_extension_last_click_poaching_or_fake_influencer_seeding_detected=False,
                premature_commission_before_return_window_or_missing_ftc_ad_tag_detected=True,
                webiq_creator_brand_safety_scandal_flag=False,
                restricted_key_age_days=30,
                stand_down_lock_and_t35_net_commission_escrow_enabled=False,
            )
        )
        self.assertEqual(ret_block["http_status"], 422)
        self.assertEqual(
            ret_block["decision"],
            "PREMATURE_COMMISSION_BEFORE_RETURN_WINDOW_OR_MISSING_FTC_AD_TAG_BLOCKED",
        )

        scandal_hold = evaluate_influencer_seeding_coupon_poaching_policy(
            InfluencerSeedingCouponPoachingPolicyInput(
                quarterly_influencer_seeding_affiliate_pool_usd=Decimal("220000.00"),
                coupon_extension_last_click_poaching_or_fake_influencer_seeding_detected=False,
                premature_commission_before_return_window_or_missing_ftc_ad_tag_detected=False,
                webiq_creator_brand_safety_scandal_flag=True,
                restricted_key_age_days=191,
                stand_down_lock_and_t35_net_commission_escrow_enabled=False,
            )
        )
        self.assertEqual(scandal_hold["http_status"], 451)
        self.assertEqual(
            scandal_hold["decision"],
            "WEBIQ_CREATOR_BRAND_SAFETY_SCANDAL_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_influencer_seeding_coupon_poaching_policy(
            InfluencerSeedingCouponPoachingPolicyInput(
                quarterly_influencer_seeding_affiliate_pool_usd=Decimal("220000.00"),
                coupon_extension_last_click_poaching_or_fake_influencer_seeding_detected=False,
                premature_commission_before_return_window_or_missing_ftc_ad_tag_detected=False,
                webiq_creator_brand_safety_scandal_flag=False,
                restricted_key_age_days=30,
                stand_down_lock_and_t35_net_commission_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "61600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "158400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("influencer_seeding_coupon_poaching_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("influencer-seeding-coupon-poaching-sandbox", html)

    def test_b2b_it_daas_leasing_nist_wipe_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bItDaasLeasingNistWipePolicyInput,
            evaluate_b2b_it_daas_leasing_nist_wipe_policy,
        )

        happy = evaluate_b2b_it_daas_leasing_nist_wipe_policy(
            B2bItDaasLeasingNistWipePolicyInput(
                quarterly_it_daas_lease_pool_usd=Decimal("310000.00"),
                unreleased_abm_mdm_lock_or_missing_nist_800_88_wipe_cert_detected=False,
                post_term_evergreen_rent_bleed_or_normal_wear_penalty_detected=False,
                webiq_battery_swell_air_freight_ban_flag=False,
                restricted_key_age_days=30,
                remote_employee_fmv_buyout_and_t100_eot_guard_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ABM_RELEASED_NIST_WIPED_AND_36M_CAPPED_LEASE_AUTHORIZED")
        self.assertTrue(
            str(happy["it_daas_token"]).startswith("b2b_it_daas_leasing_nist_wipe_mandate_")
        )

        abm_block = evaluate_b2b_it_daas_leasing_nist_wipe_policy(
            B2bItDaasLeasingNistWipePolicyInput(
                quarterly_it_daas_lease_pool_usd=Decimal("310000.00"),
                unreleased_abm_mdm_lock_or_missing_nist_800_88_wipe_cert_detected=True,
                post_term_evergreen_rent_bleed_or_normal_wear_penalty_detected=False,
                webiq_battery_swell_air_freight_ban_flag=False,
                restricted_key_age_days=30,
                remote_employee_fmv_buyout_and_t100_eot_guard_enabled=False,
            )
        )
        self.assertEqual(abm_block["http_status"], 403)
        self.assertEqual(
            abm_block["decision"],
            "UNRELEASED_ABM_MDM_LOCK_OR_MISSING_NIST_800_88_WIPE_CERT_BLOCKED",
        )

        evergreen_block = evaluate_b2b_it_daas_leasing_nist_wipe_policy(
            B2bItDaasLeasingNistWipePolicyInput(
                quarterly_it_daas_lease_pool_usd=Decimal("310000.00"),
                unreleased_abm_mdm_lock_or_missing_nist_800_88_wipe_cert_detected=False,
                post_term_evergreen_rent_bleed_or_normal_wear_penalty_detected=True,
                webiq_battery_swell_air_freight_ban_flag=False,
                restricted_key_age_days=30,
                remote_employee_fmv_buyout_and_t100_eot_guard_enabled=False,
            )
        )
        self.assertEqual(evergreen_block["http_status"], 422)
        self.assertEqual(
            evergreen_block["decision"],
            "POST_TERM_EVERGREEN_RENT_BLEED_OR_NORMAL_WEAR_PENALTY_BLOCKED",
        )

        bat_hold = evaluate_b2b_it_daas_leasing_nist_wipe_policy(
            B2bItDaasLeasingNistWipePolicyInput(
                quarterly_it_daas_lease_pool_usd=Decimal("310000.00"),
                unreleased_abm_mdm_lock_or_missing_nist_800_88_wipe_cert_detected=False,
                post_term_evergreen_rent_bleed_or_normal_wear_penalty_detected=False,
                webiq_battery_swell_air_freight_ban_flag=True,
                restricted_key_age_days=191,
                remote_employee_fmv_buyout_and_t100_eot_guard_enabled=False,
            )
        )
        self.assertEqual(bat_hold["http_status"], 451)
        self.assertEqual(
            bat_hold["decision"],
            "WEBIQ_BATTERY_SWELL_AIR_FREIGHT_BAN_OR_180D_KEY_HOLD",
        )

        opt_confirm = evaluate_b2b_it_daas_leasing_nist_wipe_policy(
            B2bItDaasLeasingNistWipePolicyInput(
                quarterly_it_daas_lease_pool_usd=Decimal("310000.00"),
                unreleased_abm_mdm_lock_or_missing_nist_800_88_wipe_cert_detected=False,
                post_term_evergreen_rent_bleed_or_normal_wear_penalty_detected=False,
                webiq_battery_swell_air_freight_ban_flag=False,
                restricted_key_age_days=30,
                remote_employee_fmv_buyout_and_t100_eot_guard_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "74400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "235600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_it_daas_leasing_nist_wipe_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-it-daas-leasing-nist-wipe-sandbox", html)

    def test_grocery_perishable_markdown_gs1_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            GroceryPerishableMarkdownGs1PolicyInput,
            evaluate_grocery_perishable_markdown_gs1_policy,
        )

        happy = evaluate_grocery_perishable_markdown_gs1_policy(
            GroceryPerishableMarkdownGs1PolicyInput(
                quarterly_perishable_shrink_pool_usd=Decimal("290000.00"),
                expired_lot_ai17_or_markdown_label_swap_detected=False,
                fixed_hour_cannibalization_or_bulk_hoarding_detected=False,
                webiq_fda_class1_food_recall_or_cold_chain_breach_flag=False,
                restricted_key_age_days=30,
                rsl_dynamic_esl_markdown_and_food_rescue_tax_credit_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "GS1_AI17_VALID_ESL_SYNCED_AND_PERISHABLE_CHECKOUT_AUTHORIZED")
        self.assertTrue(
            str(happy["grocery_markdown_token"]).startswith("grocery_perishable_markdown_gs1_mandate_")
        )

        exp_block = evaluate_grocery_perishable_markdown_gs1_policy(
            GroceryPerishableMarkdownGs1PolicyInput(
                quarterly_perishable_shrink_pool_usd=Decimal("290000.00"),
                expired_lot_ai17_or_markdown_label_swap_detected=True,
                fixed_hour_cannibalization_or_bulk_hoarding_detected=False,
                webiq_fda_class1_food_recall_or_cold_chain_breach_flag=False,
                restricted_key_age_days=30,
                rsl_dynamic_esl_markdown_and_food_rescue_tax_credit_enabled=False,
            )
        )
        self.assertEqual(exp_block["http_status"], 403)
        self.assertEqual(
            exp_block["decision"],
            "EXPIRED_LOT_AI17_OR_MARKDOWN_LABEL_SWAP_BLOCKED",
        )

        hoard_block = evaluate_grocery_perishable_markdown_gs1_policy(
            GroceryPerishableMarkdownGs1PolicyInput(
                quarterly_perishable_shrink_pool_usd=Decimal("290000.00"),
                expired_lot_ai17_or_markdown_label_swap_detected=False,
                fixed_hour_cannibalization_or_bulk_hoarding_detected=True,
                webiq_fda_class1_food_recall_or_cold_chain_breach_flag=False,
                restricted_key_age_days=30,
                rsl_dynamic_esl_markdown_and_food_rescue_tax_credit_enabled=False,
            )
        )
        self.assertEqual(hoard_block["http_status"], 422)
        self.assertEqual(
            hoard_block["decision"],
            "FIXED_HOUR_CANNIBALIZATION_OR_BULK_HOARDING_BLOCKED",
        )

        recall_hold = evaluate_grocery_perishable_markdown_gs1_policy(
            GroceryPerishableMarkdownGs1PolicyInput(
                quarterly_perishable_shrink_pool_usd=Decimal("290000.00"),
                expired_lot_ai17_or_markdown_label_swap_detected=False,
                fixed_hour_cannibalization_or_bulk_hoarding_detected=False,
                webiq_fda_class1_food_recall_or_cold_chain_breach_flag=True,
                restricted_key_age_days=191,
                rsl_dynamic_esl_markdown_and_food_rescue_tax_credit_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(
            recall_hold["decision"],
            "WEBIQ_FDA_CLASS1_FOOD_RECALL_OR_COLD_CHAIN_BREACH_HOLD",
        )

        opt_confirm = evaluate_grocery_perishable_markdown_gs1_policy(
            GroceryPerishableMarkdownGs1PolicyInput(
                quarterly_perishable_shrink_pool_usd=Decimal("290000.00"),
                expired_lot_ai17_or_markdown_label_swap_detected=False,
                fixed_hour_cannibalization_or_bulk_hoarding_detected=False,
                webiq_fda_class1_food_recall_or_cold_chain_breach_flag=False,
                restricted_key_age_days=30,
                rsl_dynamic_esl_markdown_and_food_rescue_tax_credit_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "75400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "214600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("grocery_perishable_markdown_gs1_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("grocery-perishable-markdown-gs1-sandbox", html)

    def test_global_eor_contractor_payroll_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            GlobalEorContractorPayrollPolicyInput,
            evaluate_global_eor_contractor_payroll_policy,
        )

        happy = evaluate_global_eor_contractor_payroll_policy(
            GlobalEorContractorPayrollPolicyInput(
                quarterly_global_payroll_pool_usd=Decimal("420000.00"),
                worker_misclassification_ir35_ab5_or_missing_ip_w8ben_detected=False,
                unverified_ghost_timesheet_or_swift_fx_markup_detected=False,
                webiq_sanctioned_jurisdiction_or_183d_tax_residency_flag=False,
                restricted_key_age_days=30,
                contractor_to_eor_shield_and_wholesale_fx_batch_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "EOR_IC_COMPLIANT_DELIVERABLE_VERIFIED_AND_LOCAL_FX_AUTHORIZED")
        self.assertTrue(
            str(happy["global_eor_token"]).startswith("global_eor_contractor_payroll_mandate_")
        )

        mis_block = evaluate_global_eor_contractor_payroll_policy(
            GlobalEorContractorPayrollPolicyInput(
                quarterly_global_payroll_pool_usd=Decimal("420000.00"),
                worker_misclassification_ir35_ab5_or_missing_ip_w8ben_detected=True,
                unverified_ghost_timesheet_or_swift_fx_markup_detected=False,
                webiq_sanctioned_jurisdiction_or_183d_tax_residency_flag=False,
                restricted_key_age_days=30,
                contractor_to_eor_shield_and_wholesale_fx_batch_enabled=False,
            )
        )
        self.assertEqual(mis_block["http_status"], 403)
        self.assertEqual(
            mis_block["decision"],
            "WORKER_MISCLASSIFICATION_IR35_AB5_OR_MISSING_IP_W8BEN_BLOCKED",
        )

        ghost_block = evaluate_global_eor_contractor_payroll_policy(
            GlobalEorContractorPayrollPolicyInput(
                quarterly_global_payroll_pool_usd=Decimal("420000.00"),
                worker_misclassification_ir35_ab5_or_missing_ip_w8ben_detected=False,
                unverified_ghost_timesheet_or_swift_fx_markup_detected=True,
                webiq_sanctioned_jurisdiction_or_183d_tax_residency_flag=False,
                restricted_key_age_days=30,
                contractor_to_eor_shield_and_wholesale_fx_batch_enabled=False,
            )
        )
        self.assertEqual(ghost_block["http_status"], 422)
        self.assertEqual(
            ghost_block["decision"],
            "UNVERIFIED_GHOST_TIMESHEET_OR_SWIFT_FX_MARKUP_BLOCKED",
        )

        pe_hold = evaluate_global_eor_contractor_payroll_policy(
            GlobalEorContractorPayrollPolicyInput(
                quarterly_global_payroll_pool_usd=Decimal("420000.00"),
                worker_misclassification_ir35_ab5_or_missing_ip_w8ben_detected=False,
                unverified_ghost_timesheet_or_swift_fx_markup_detected=False,
                webiq_sanctioned_jurisdiction_or_183d_tax_residency_flag=True,
                restricted_key_age_days=191,
                contractor_to_eor_shield_and_wholesale_fx_batch_enabled=False,
            )
        )
        self.assertEqual(pe_hold["http_status"], 451)
        self.assertEqual(
            pe_hold["decision"],
            "WEBIQ_SANCTIONED_JURISDICTION_OR_183D_TAX_RESIDENCY_HOLD",
        )

        opt_confirm = evaluate_global_eor_contractor_payroll_policy(
            GlobalEorContractorPayrollPolicyInput(
                quarterly_global_payroll_pool_usd=Decimal("420000.00"),
                worker_misclassification_ir35_ab5_or_missing_ip_w8ben_detected=False,
                unverified_ghost_timesheet_or_swift_fx_markup_detected=False,
                webiq_sanctioned_jurisdiction_or_183d_tax_residency_flag=False,
                restricted_key_age_days=30,
                contractor_to_eor_shield_and_wholesale_fx_batch_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "96600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "323400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("global_eor_contractor_payroll_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("global-eor-contractor-payroll-sandbox", html)

    def test_luxury_watch_jewelry_memo_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            LuxuryWatchJewelryMemoEscrowPolicyInput,
            evaluate_luxury_watch_jewelry_memo_escrow_policy,
        )

        happy = evaluate_luxury_watch_jewelry_memo_escrow_policy(
            LuxuryWatchJewelryMemoEscrowPolicyInput(
                quarterly_luxury_consignment_memo_pool_usd=Decimal("480000.00"),
                stolen_watch_register_or_frankenwatch_synthetic_gia_swap_detected=False,
                below_consignor_reserve_floor_or_expired_memo_unpaid_detected=False,
                webiq_kimberley_conflict_diamond_or_fincen_aml_flag=False,
                restricted_key_age_days=30,
                authentication_hub_nfc_seal_and_armored_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "GIA_MOVEMENT_VERIFIED_RESERVE_PROTECTED_AND_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["luxury_memo_token"]).startswith("luxury_watch_jewelry_memo_escrow_mandate_")
        )

        franken_block = evaluate_luxury_watch_jewelry_memo_escrow_policy(
            LuxuryWatchJewelryMemoEscrowPolicyInput(
                quarterly_luxury_consignment_memo_pool_usd=Decimal("480000.00"),
                stolen_watch_register_or_frankenwatch_synthetic_gia_swap_detected=True,
                below_consignor_reserve_floor_or_expired_memo_unpaid_detected=False,
                webiq_kimberley_conflict_diamond_or_fincen_aml_flag=False,
                restricted_key_age_days=30,
                authentication_hub_nfc_seal_and_armored_escrow_enabled=False,
            )
        )
        self.assertEqual(franken_block["http_status"], 403)
        self.assertEqual(
            franken_block["decision"],
            "STOLEN_WATCH_REGISTER_OR_FRANKENWATCH_SYNTHETIC_GIA_SWAP_BLOCKED",
        )

        reserve_block = evaluate_luxury_watch_jewelry_memo_escrow_policy(
            LuxuryWatchJewelryMemoEscrowPolicyInput(
                quarterly_luxury_consignment_memo_pool_usd=Decimal("480000.00"),
                stolen_watch_register_or_frankenwatch_synthetic_gia_swap_detected=False,
                below_consignor_reserve_floor_or_expired_memo_unpaid_detected=True,
                webiq_kimberley_conflict_diamond_or_fincen_aml_flag=False,
                restricted_key_age_days=30,
                authentication_hub_nfc_seal_and_armored_escrow_enabled=False,
            )
        )
        self.assertEqual(reserve_block["http_status"], 422)
        self.assertEqual(
            reserve_block["decision"],
            "BELOW_CONSIGNOR_RESERVE_FLOOR_OR_EXPIRED_MEMO_UNPAID_BLOCKED",
        )

        aml_hold = evaluate_luxury_watch_jewelry_memo_escrow_policy(
            LuxuryWatchJewelryMemoEscrowPolicyInput(
                quarterly_luxury_consignment_memo_pool_usd=Decimal("480000.00"),
                stolen_watch_register_or_frankenwatch_synthetic_gia_swap_detected=False,
                below_consignor_reserve_floor_or_expired_memo_unpaid_detected=False,
                webiq_kimberley_conflict_diamond_or_fincen_aml_flag=True,
                restricted_key_age_days=191,
                authentication_hub_nfc_seal_and_armored_escrow_enabled=False,
            )
        )
        self.assertEqual(aml_hold["http_status"], 451)
        self.assertEqual(
            aml_hold["decision"],
            "WEBIQ_KIMBERLEY_CONFLICT_DIAMOND_OR_FINCEN_AML_HOLD",
        )

        opt_confirm = evaluate_luxury_watch_jewelry_memo_escrow_policy(
            LuxuryWatchJewelryMemoEscrowPolicyInput(
                quarterly_luxury_consignment_memo_pool_usd=Decimal("480000.00"),
                stolen_watch_register_or_frankenwatch_synthetic_gia_swap_detected=False,
                below_consignor_reserve_floor_or_expired_memo_unpaid_detected=False,
                webiq_kimberley_conflict_diamond_or_fincen_aml_flag=False,
                restricted_key_age_days=30,
                authentication_hub_nfc_seal_and_armored_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "129600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "350400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("luxury_watch_jewelry_memo_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("luxury-watch-jewelry-memo-escrow-sandbox", html)

    def test_clinical_trial_stipend_ecoa_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            ClinicalTrialStipendEcoaPolicyInput,
            evaluate_clinical_trial_stipend_ecoa_policy,
        )

        happy = evaluate_clinical_trial_stipend_ecoa_policy(
            ClinicalTrialStipendEcoaPolicyInput(
                quarterly_clinical_trial_stipend_pool_usd=Decimal("340000.00"),
                duplicate_trial_enrollment_or_uncompleted_ecoa_visit_detected=False,
                irb_stipend_cap_breach_or_unreceipted_travel_reimbursement_detected=False,
                webiq_fda_debarred_investigator_or_hipaa_ssn_sponsor_leak_flag=False,
                restricted_key_age_days=30,
                tax_blind_clincard_split_and_uber_health_voucher_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ECOA_VERIFIED_IRB_CAPPED_AND_TAX_BLIND_STIPEND_AUTHORIZED")
        self.assertTrue(
            str(happy["clinical_stipend_token"]).startswith("clinical_trial_stipend_ecoa_mandate_")
        )

        dup_block = evaluate_clinical_trial_stipend_ecoa_policy(
            ClinicalTrialStipendEcoaPolicyInput(
                quarterly_clinical_trial_stipend_pool_usd=Decimal("340000.00"),
                duplicate_trial_enrollment_or_uncompleted_ecoa_visit_detected=True,
                irb_stipend_cap_breach_or_unreceipted_travel_reimbursement_detected=False,
                webiq_fda_debarred_investigator_or_hipaa_ssn_sponsor_leak_flag=False,
                restricted_key_age_days=30,
                tax_blind_clincard_split_and_uber_health_voucher_enabled=False,
            )
        )
        self.assertEqual(dup_block["http_status"], 403)
        self.assertEqual(
            dup_block["decision"],
            "DUPLICATE_TRIAL_ENROLLMENT_OR_UNCOMPLETED_ECOA_VISIT_BLOCKED",
        )

        irb_block = evaluate_clinical_trial_stipend_ecoa_policy(
            ClinicalTrialStipendEcoaPolicyInput(
                quarterly_clinical_trial_stipend_pool_usd=Decimal("340000.00"),
                duplicate_trial_enrollment_or_uncompleted_ecoa_visit_detected=False,
                irb_stipend_cap_breach_or_unreceipted_travel_reimbursement_detected=True,
                webiq_fda_debarred_investigator_or_hipaa_ssn_sponsor_leak_flag=False,
                restricted_key_age_days=30,
                tax_blind_clincard_split_and_uber_health_voucher_enabled=False,
            )
        )
        self.assertEqual(irb_block["http_status"], 422)
        self.assertEqual(
            irb_block["decision"],
            "IRB_STIPEND_CAP_BREACH_OR_UNRECEIPTED_TRAVEL_REIMBURSEMENT_BLOCKED",
        )

        hipaa_hold = evaluate_clinical_trial_stipend_ecoa_policy(
            ClinicalTrialStipendEcoaPolicyInput(
                quarterly_clinical_trial_stipend_pool_usd=Decimal("340000.00"),
                duplicate_trial_enrollment_or_uncompleted_ecoa_visit_detected=False,
                irb_stipend_cap_breach_or_unreceipted_travel_reimbursement_detected=False,
                webiq_fda_debarred_investigator_or_hipaa_ssn_sponsor_leak_flag=True,
                restricted_key_age_days=191,
                tax_blind_clincard_split_and_uber_health_voucher_enabled=False,
            )
        )
        self.assertEqual(hipaa_hold["http_status"], 451)
        self.assertEqual(
            hipaa_hold["decision"],
            "WEBIQ_FDA_DEBARRED_INVESTIGATOR_OR_HIPAA_SSN_SPONSOR_LEAK_HOLD",
        )

        opt_confirm = evaluate_clinical_trial_stipend_ecoa_policy(
            ClinicalTrialStipendEcoaPolicyInput(
                quarterly_clinical_trial_stipend_pool_usd=Decimal("340000.00"),
                duplicate_trial_enrollment_or_uncompleted_ecoa_visit_detected=False,
                irb_stipend_cap_breach_or_unreceipted_travel_reimbursement_detected=False,
                webiq_fda_debarred_investigator_or_hipaa_ssn_sponsor_leak_flag=False,
                restricted_key_age_days=30,
                tax_blind_clincard_split_and_uber_health_voucher_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "85000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "255000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("clinical_trial_stipend_ecoa_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("clinical-trial-stipend-ecoa-sandbox", html)

    def test_commercial_cre_percentage_rent_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CommercialCrePercentageRentPolicyInput,
            evaluate_commercial_cre_percentage_rent_policy,
        )

        happy = evaluate_commercial_cre_percentage_rent_policy(
            CommercialCrePercentageRentPolicyInput(
                quarterly_mall_percentage_rent_ti_pool_usd=Decimal("520000.00"),
                missing_subcontractor_lien_waiver_or_pos_percentage_rent_skimming_detected=False,
                controllable_cam_cap_breach_or_cross_store_return_deduction_abuse_detected=False,
                webiq_lapsed_acord25_coi_insurance_or_fire_health_permit_flag=False,
                restricted_key_age_days=30,
                pos_breakpoint_auto_sweep_and_digital_lien_waiver_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "POS_VERIFIED_LIEN_WAIVED_AND_PERCENTAGE_RENT_AUTHORIZED")
        self.assertTrue(
            str(happy["cre_percentage_rent_token"]).startswith("commercial_cre_percentage_rent_mandate_")
        )

        skim_block = evaluate_commercial_cre_percentage_rent_policy(
            CommercialCrePercentageRentPolicyInput(
                quarterly_mall_percentage_rent_ti_pool_usd=Decimal("520000.00"),
                missing_subcontractor_lien_waiver_or_pos_percentage_rent_skimming_detected=True,
                controllable_cam_cap_breach_or_cross_store_return_deduction_abuse_detected=False,
                webiq_lapsed_acord25_coi_insurance_or_fire_health_permit_flag=False,
                restricted_key_age_days=30,
                pos_breakpoint_auto_sweep_and_digital_lien_waiver_escrow_enabled=False,
            )
        )
        self.assertEqual(skim_block["http_status"], 403)
        self.assertEqual(
            skim_block["decision"],
            "MISSING_SUBCONTRACTOR_LIEN_WAIVER_OR_POS_PERCENTAGE_RENT_SKIMMING_BLOCKED",
        )

        boris_block = evaluate_commercial_cre_percentage_rent_policy(
            CommercialCrePercentageRentPolicyInput(
                quarterly_mall_percentage_rent_ti_pool_usd=Decimal("520000.00"),
                missing_subcontractor_lien_waiver_or_pos_percentage_rent_skimming_detected=False,
                controllable_cam_cap_breach_or_cross_store_return_deduction_abuse_detected=True,
                webiq_lapsed_acord25_coi_insurance_or_fire_health_permit_flag=False,
                restricted_key_age_days=30,
                pos_breakpoint_auto_sweep_and_digital_lien_waiver_escrow_enabled=False,
            )
        )
        self.assertEqual(boris_block["http_status"], 422)
        self.assertEqual(
            boris_block["decision"],
            "CONTROLLABLE_CAM_CAP_BREACH_OR_CROSS_STORE_RETURN_DEDUCTION_ABUSE_BLOCKED",
        )

        coi_hold = evaluate_commercial_cre_percentage_rent_policy(
            CommercialCrePercentageRentPolicyInput(
                quarterly_mall_percentage_rent_ti_pool_usd=Decimal("520000.00"),
                missing_subcontractor_lien_waiver_or_pos_percentage_rent_skimming_detected=False,
                controllable_cam_cap_breach_or_cross_store_return_deduction_abuse_detected=False,
                webiq_lapsed_acord25_coi_insurance_or_fire_health_permit_flag=True,
                restricted_key_age_days=191,
                pos_breakpoint_auto_sweep_and_digital_lien_waiver_escrow_enabled=False,
            )
        )
        self.assertEqual(coi_hold["http_status"], 451)
        self.assertEqual(
            coi_hold["decision"],
            "WEBIQ_LAPSED_ACORD25_COI_INSURANCE_OR_FIRE_HEALTH_PERMIT_HOLD",
        )

        opt_confirm = evaluate_commercial_cre_percentage_rent_policy(
            CommercialCrePercentageRentPolicyInput(
                quarterly_mall_percentage_rent_ti_pool_usd=Decimal("520000.00"),
                missing_subcontractor_lien_waiver_or_pos_percentage_rent_skimming_detected=False,
                controllable_cam_cap_breach_or_cross_store_return_deduction_abuse_detected=False,
                webiq_lapsed_acord25_coi_insurance_or_fire_health_permit_flag=False,
                restricted_key_age_days=30,
                pos_breakpoint_auto_sweep_and_digital_lien_waiver_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "124800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "395200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("commercial_cre_percentage_rent_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("commercial-cre-percentage-rent-sandbox", html)

    def test_childcare_preschool_camp_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            ChildcarePreschoolCampEscrowPolicyInput,
            evaluate_childcare_preschool_camp_escrow_policy,
        )

        happy = evaluate_childcare_preschool_camp_escrow_policy(
            ChildcarePreschoolCampEscrowPolicyInput(
                quarterly_childcare_camp_tuition_pool_usd=Decimal("260000.00"),
                staff_child_ratio_breach_or_missing_immunization_pickup_auth_detected=False,
                prepaid_tuition_cap_breach_or_overnight_camp_fsa_ineligible_detected=False,
                webiq_expired_staff_background_check_or_licensing_flag=False,
                restricted_key_age_days=30,
                ccdf_fsa_copay_split_and_monthly_escrow_release_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "RATIO_COMPLIANT_IMMUNIZATION_VERIFIED_AND_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["childcare_camp_token"]).startswith("childcare_preschool_camp_escrow_mandate_")
        )

        ratio_block = evaluate_childcare_preschool_camp_escrow_policy(
            ChildcarePreschoolCampEscrowPolicyInput(
                quarterly_childcare_camp_tuition_pool_usd=Decimal("260000.00"),
                staff_child_ratio_breach_or_missing_immunization_pickup_auth_detected=True,
                prepaid_tuition_cap_breach_or_overnight_camp_fsa_ineligible_detected=False,
                webiq_expired_staff_background_check_or_licensing_flag=False,
                restricted_key_age_days=30,
                ccdf_fsa_copay_split_and_monthly_escrow_release_enabled=False,
            )
        )
        self.assertEqual(ratio_block["http_status"], 403)
        self.assertEqual(
            ratio_block["decision"],
            "STAFF_CHILD_RATIO_BREACH_OR_MISSING_IMMUNIZATION_PICKUP_AUTH_BLOCKED",
        )

        fsa_block = evaluate_childcare_preschool_camp_escrow_policy(
            ChildcarePreschoolCampEscrowPolicyInput(
                quarterly_childcare_camp_tuition_pool_usd=Decimal("260000.00"),
                staff_child_ratio_breach_or_missing_immunization_pickup_auth_detected=False,
                prepaid_tuition_cap_breach_or_overnight_camp_fsa_ineligible_detected=True,
                webiq_expired_staff_background_check_or_licensing_flag=False,
                restricted_key_age_days=30,
                ccdf_fsa_copay_split_and_monthly_escrow_release_enabled=False,
            )
        )
        self.assertEqual(fsa_block["http_status"], 422)
        self.assertEqual(
            fsa_block["decision"],
            "PREPAID_TUITION_CAP_BREACH_OR_OVERNIGHT_CAMP_FSA_INELIGIBLE_BLOCKED",
        )

        bgc_hold = evaluate_childcare_preschool_camp_escrow_policy(
            ChildcarePreschoolCampEscrowPolicyInput(
                quarterly_childcare_camp_tuition_pool_usd=Decimal("260000.00"),
                staff_child_ratio_breach_or_missing_immunization_pickup_auth_detected=False,
                prepaid_tuition_cap_breach_or_overnight_camp_fsa_ineligible_detected=False,
                webiq_expired_staff_background_check_or_licensing_flag=True,
                restricted_key_age_days=191,
                ccdf_fsa_copay_split_and_monthly_escrow_release_enabled=False,
            )
        )
        self.assertEqual(bgc_hold["http_status"], 451)
        self.assertEqual(
            bgc_hold["decision"],
            "WEBIQ_EXPIRED_STAFF_BACKGROUND_CHECK_OR_LICENSING_HOLD",
        )

        opt_confirm = evaluate_childcare_preschool_camp_escrow_policy(
            ChildcarePreschoolCampEscrowPolicyInput(
                quarterly_childcare_camp_tuition_pool_usd=Decimal("260000.00"),
                staff_child_ratio_breach_or_missing_immunization_pickup_auth_detected=False,
                prepaid_tuition_cap_breach_or_overnight_camp_fsa_ineligible_detected=False,
                webiq_expired_staff_background_check_or_licensing_flag=False,
                restricted_key_age_days=30,
                ccdf_fsa_copay_split_and_monthly_escrow_release_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "59800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "200200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("childcare_preschool_camp_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("childcare-preschool-camp-escrow-sandbox", html)

    def test_shared_powerbank_smart_vending_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            SharedPowerbankSmartVendingPolicyInput,
            evaluate_shared_powerbank_smart_vending_policy,
        )

        happy = evaluate_shared_powerbank_smart_vending_policy(
            SharedPowerbankSmartVendingPolicyInput(
                quarterly_shared_rental_vending_pool_usd=Decimal("230000.00"),
                fake_powerbank_shell_insertion_or_smart_cooler_weight_vision_spoof_detected=False,
                zombie_slot_offline_overbilling_or_pick_up_put_back_false_charge_detected=False,
                webiq_bms_thermal_runaway_lock_or_cooler_temp_breach_flag=False,
                restricted_key_age_days=30,
                deposit_free_credit_score_hold_and_ble_instant_return_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "CRYPTO_SLOT_VERIFIED_VISION_WEIGHT_MATCHED_AND_SETTLE_AUTHORIZED")
        self.assertTrue(
            str(happy["shared_vending_token"]).startswith("shared_powerbank_smart_vending_mandate_")
        )

        fake_block = evaluate_shared_powerbank_smart_vending_policy(
            SharedPowerbankSmartVendingPolicyInput(
                quarterly_shared_rental_vending_pool_usd=Decimal("230000.00"),
                fake_powerbank_shell_insertion_or_smart_cooler_weight_vision_spoof_detected=True,
                zombie_slot_offline_overbilling_or_pick_up_put_back_false_charge_detected=False,
                webiq_bms_thermal_runaway_lock_or_cooler_temp_breach_flag=False,
                restricted_key_age_days=30,
                deposit_free_credit_score_hold_and_ble_instant_return_enabled=False,
            )
        )
        self.assertEqual(fake_block["http_status"], 403)
        self.assertEqual(
            fake_block["decision"],
            "FAKE_POWERBANK_SHELL_INSERTION_OR_SMART_COOLER_WEIGHT_VISION_SPOOF_BLOCKED",
        )

        zombie_block = evaluate_shared_powerbank_smart_vending_policy(
            SharedPowerbankSmartVendingPolicyInput(
                quarterly_shared_rental_vending_pool_usd=Decimal("230000.00"),
                fake_powerbank_shell_insertion_or_smart_cooler_weight_vision_spoof_detected=False,
                zombie_slot_offline_overbilling_or_pick_up_put_back_false_charge_detected=True,
                webiq_bms_thermal_runaway_lock_or_cooler_temp_breach_flag=False,
                restricted_key_age_days=30,
                deposit_free_credit_score_hold_and_ble_instant_return_enabled=False,
            )
        )
        self.assertEqual(zombie_block["http_status"], 422)
        self.assertEqual(
            zombie_block["decision"],
            "ZOMBIE_SLOT_OFFLINE_OVERBILLING_OR_PICK_UP_PUT_BACK_FALSE_CHARGE_BLOCKED",
        )

        thermal_hold = evaluate_shared_powerbank_smart_vending_policy(
            SharedPowerbankSmartVendingPolicyInput(
                quarterly_shared_rental_vending_pool_usd=Decimal("230000.00"),
                fake_powerbank_shell_insertion_or_smart_cooler_weight_vision_spoof_detected=False,
                zombie_slot_offline_overbilling_or_pick_up_put_back_false_charge_detected=False,
                webiq_bms_thermal_runaway_lock_or_cooler_temp_breach_flag=True,
                restricted_key_age_days=191,
                deposit_free_credit_score_hold_and_ble_instant_return_enabled=False,
            )
        )
        self.assertEqual(thermal_hold["http_status"], 451)
        self.assertEqual(
            thermal_hold["decision"],
            "WEBIQ_BMS_THERMAL_RUNAWAY_LOCK_OR_COOLER_TEMP_BREACH_HOLD",
        )

        opt_confirm = evaluate_shared_powerbank_smart_vending_policy(
            SharedPowerbankSmartVendingPolicyInput(
                quarterly_shared_rental_vending_pool_usd=Decimal("230000.00"),
                fake_powerbank_shell_insertion_or_smart_cooler_weight_vision_spoof_detected=False,
                zombie_slot_offline_overbilling_or_pick_up_put_back_false_charge_detected=False,
                webiq_bms_thermal_runaway_lock_or_cooler_temp_breach_flag=False,
                restricted_key_age_days=30,
                deposit_free_credit_score_hold_and_ble_instant_return_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "59800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "170200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("shared_powerbank_smart_vending_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("shared-powerbank-smart-vending-sandbox", html)

    def test_agri_inputs_produce_paca_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            AgriInputsProducePacaEscrowPolicyInput,
            evaluate_agri_inputs_produce_paca_escrow_policy,
        )

        happy = evaluate_agri_inputs_produce_paca_escrow_policy(
            AgriInputsProducePacaEscrowPolicyInput(
                quarterly_agri_produce_paca_pool_usd=Decimal("390000.00"),
                unapproved_seed_zone_mismatch_or_unlicensed_rup_pesticide_detected=False,
                unverified_produce_spoilage_deduction_or_evaded_crop_lien_detected=False,
                webiq_aphis_quarantine_zone_or_banned_agrochemical_flag=False,
                restricted_key_age_days=30,
                paca_trust_waterfall_and_parametric_weather_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ZONE_VERIFIED_PACA_TRUST_PROTECTED_AND_WATERFALL_AUTHORIZED")
        self.assertTrue(
            str(happy["agri_paca_token"]).startswith("agri_inputs_produce_paca_escrow_mandate_")
        )

        zone_block = evaluate_agri_inputs_produce_paca_escrow_policy(
            AgriInputsProducePacaEscrowPolicyInput(
                quarterly_agri_produce_paca_pool_usd=Decimal("390000.00"),
                unapproved_seed_zone_mismatch_or_unlicensed_rup_pesticide_detected=True,
                unverified_produce_spoilage_deduction_or_evaded_crop_lien_detected=False,
                webiq_aphis_quarantine_zone_or_banned_agrochemical_flag=False,
                restricted_key_age_days=30,
                paca_trust_waterfall_and_parametric_weather_escrow_enabled=False,
            )
        )
        self.assertEqual(zone_block["http_status"], 403)
        self.assertEqual(
            zone_block["decision"],
            "UNAPPROVED_SEED_ZONE_MISMATCH_OR_UNLICENSED_RUP_PESTICIDE_BLOCKED",
        )

        spoilage_block = evaluate_agri_inputs_produce_paca_escrow_policy(
            AgriInputsProducePacaEscrowPolicyInput(
                quarterly_agri_produce_paca_pool_usd=Decimal("390000.00"),
                unapproved_seed_zone_mismatch_or_unlicensed_rup_pesticide_detected=False,
                unverified_produce_spoilage_deduction_or_evaded_crop_lien_detected=True,
                webiq_aphis_quarantine_zone_or_banned_agrochemical_flag=False,
                restricted_key_age_days=30,
                paca_trust_waterfall_and_parametric_weather_escrow_enabled=False,
            )
        )
        self.assertEqual(spoilage_block["http_status"], 422)
        self.assertEqual(
            spoilage_block["decision"],
            "UNVERIFIED_PRODUCE_SPOILAGE_DEDUCTION_OR_EVADED_CROP_LIEN_BLOCKED",
        )

        aphis_hold = evaluate_agri_inputs_produce_paca_escrow_policy(
            AgriInputsProducePacaEscrowPolicyInput(
                quarterly_agri_produce_paca_pool_usd=Decimal("390000.00"),
                unapproved_seed_zone_mismatch_or_unlicensed_rup_pesticide_detected=False,
                unverified_produce_spoilage_deduction_or_evaded_crop_lien_detected=False,
                webiq_aphis_quarantine_zone_or_banned_agrochemical_flag=True,
                restricted_key_age_days=191,
                paca_trust_waterfall_and_parametric_weather_escrow_enabled=False,
            )
        )
        self.assertEqual(aphis_hold["http_status"], 451)
        self.assertEqual(
            aphis_hold["decision"],
            "WEBIQ_APHIS_QUARANTINE_ZONE_OR_BANNED_AGROCHEMICAL_HOLD",
        )

        opt_confirm = evaluate_agri_inputs_produce_paca_escrow_policy(
            AgriInputsProducePacaEscrowPolicyInput(
                quarterly_agri_produce_paca_pool_usd=Decimal("390000.00"),
                unapproved_seed_zone_mismatch_or_unlicensed_rup_pesticide_detected=False,
                unverified_produce_spoilage_deduction_or_evaded_crop_lien_detected=False,
                webiq_aphis_quarantine_zone_or_banned_agrochemical_flag=False,
                restricted_key_age_days=30,
                paca_trust_waterfall_and_parametric_weather_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "97500.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "292500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("agri_inputs_produce_paca_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("agri-inputs-produce-paca-escrow-sandbox", html)

    def test_laundry_luxury_care_rfid_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            LaundryLuxuryCareRfidEscrowPolicyInput,
            evaluate_laundry_luxury_care_rfid_escrow_policy,
        )

        happy = evaluate_laundry_luxury_care_rfid_escrow_policy(
            LaundryLuxuryCareRfidEscrowPolicyInput(
                quarterly_laundry_luxury_care_pool_usd=Decimal("210000.00"),
                do_not_wash_cashmere_in_bulk_bag_or_unconfirmed_pre_existing_damage_detected=False,
                uninsured_luxury_garment_or_commercial_linen_subscription_abuse_detected=False,
                webiq_epa_perc_solvent_ban_or_sanitation_violation_flag=False,
                restricted_key_age_days=30,
                rfid_garment_twin_and_offpeak_locker_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "CARE_LABEL_SAFE_DEFECT_SIGNED_AND_RFID_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["laundry_rfid_token"]).startswith("laundry_luxury_care_rfid_escrow_mandate_")
        )

        cashmere_block = evaluate_laundry_luxury_care_rfid_escrow_policy(
            LaundryLuxuryCareRfidEscrowPolicyInput(
                quarterly_laundry_luxury_care_pool_usd=Decimal("210000.00"),
                do_not_wash_cashmere_in_bulk_bag_or_unconfirmed_pre_existing_damage_detected=True,
                uninsured_luxury_garment_or_commercial_linen_subscription_abuse_detected=False,
                webiq_epa_perc_solvent_ban_or_sanitation_violation_flag=False,
                restricted_key_age_days=30,
                rfid_garment_twin_and_offpeak_locker_escrow_enabled=False,
            )
        )
        self.assertEqual(cashmere_block["http_status"], 403)
        self.assertEqual(
            cashmere_block["decision"],
            "DO_NOT_WASH_CASHMERE_IN_BULK_BAG_OR_UNCONFIRMED_PRE_EXISTING_DAMAGE_BLOCKED",
        )

        linen_block = evaluate_laundry_luxury_care_rfid_escrow_policy(
            LaundryLuxuryCareRfidEscrowPolicyInput(
                quarterly_laundry_luxury_care_pool_usd=Decimal("210000.00"),
                do_not_wash_cashmere_in_bulk_bag_or_unconfirmed_pre_existing_damage_detected=False,
                uninsured_luxury_garment_or_commercial_linen_subscription_abuse_detected=True,
                webiq_epa_perc_solvent_ban_or_sanitation_violation_flag=False,
                restricted_key_age_days=30,
                rfid_garment_twin_and_offpeak_locker_escrow_enabled=False,
            )
        )
        self.assertEqual(linen_block["http_status"], 422)
        self.assertEqual(
            linen_block["decision"],
            "UNINSURED_LUXURY_GARMENT_OR_COMMERCIAL_LINEN_SUBSCRIPTION_ABUSE_BLOCKED",
        )

        perc_hold = evaluate_laundry_luxury_care_rfid_escrow_policy(
            LaundryLuxuryCareRfidEscrowPolicyInput(
                quarterly_laundry_luxury_care_pool_usd=Decimal("210000.00"),
                do_not_wash_cashmere_in_bulk_bag_or_unconfirmed_pre_existing_damage_detected=False,
                uninsured_luxury_garment_or_commercial_linen_subscription_abuse_detected=False,
                webiq_epa_perc_solvent_ban_or_sanitation_violation_flag=True,
                restricted_key_age_days=191,
                rfid_garment_twin_and_offpeak_locker_escrow_enabled=False,
            )
        )
        self.assertEqual(perc_hold["http_status"], 451)
        self.assertEqual(
            perc_hold["decision"],
            "WEBIQ_EPA_PERC_SOLVENT_BAN_OR_SANITATION_VIOLATION_HOLD",
        )

        opt_confirm = evaluate_laundry_luxury_care_rfid_escrow_policy(
            LaundryLuxuryCareRfidEscrowPolicyInput(
                quarterly_laundry_luxury_care_pool_usd=Decimal("210000.00"),
                do_not_wash_cashmere_in_bulk_bag_or_unconfirmed_pre_existing_damage_detected=False,
                uninsured_luxury_garment_or_commercial_linen_subscription_abuse_detected=False,
                webiq_epa_perc_solvent_ban_or_sanitation_violation_flag=False,
                restricted_key_age_days=30,
                rfid_garment_twin_and_offpeak_locker_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "50400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "159600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("laundry_luxury_care_rfid_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("laundry-luxury-care-rfid-escrow-sandbox", html)

    def test_car_rental_mobility_toll_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            CarRentalMobilityTollEscrowPolicyInput,
            evaluate_car_rental_mobility_toll_escrow_policy,
        )

        happy = evaluate_car_rental_mobility_toll_escrow_policy(
            CarRentalMobilityTollEscrowPolicyInput(
                quarterly_car_rental_mobility_pool_usd=Decimal("320000.00"),
                pre_existing_scratch_diff_mismatch_or_unverified_damage_claim_detected=False,
                duplicate_cdw_upsell_or_telematics_fuel_soc_parity_breach_detected=False,
                webiq_nhtsa_vin_recall_or_expired_toll_settlement_window_flag=False,
                restricted_key_age_days=30,
                instant_0420_deposit_release_and_bounded_toll_sub_mandate_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "RENTAL_VISION_SOC_PARITY_AND_TOLL_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["car_rental_escrow_token"]).startswith("car_rental_mobility_toll_escrow_mandate_")
        )

        scratch_block = evaluate_car_rental_mobility_toll_escrow_policy(
            CarRentalMobilityTollEscrowPolicyInput(
                quarterly_car_rental_mobility_pool_usd=Decimal("320000.00"),
                pre_existing_scratch_diff_mismatch_or_unverified_damage_claim_detected=True,
                duplicate_cdw_upsell_or_telematics_fuel_soc_parity_breach_detected=False,
                webiq_nhtsa_vin_recall_or_expired_toll_settlement_window_flag=False,
                restricted_key_age_days=30,
                instant_0420_deposit_release_and_bounded_toll_sub_mandate_enabled=False,
            )
        )
        self.assertEqual(scratch_block["http_status"], 403)
        self.assertEqual(
            scratch_block["decision"],
            "PRE_EXISTING_SCRATCH_DIFF_MISMATCH_OR_UNVERIFIED_DAMAGE_CLAIM_BLOCKED",
        )

        cdw_block = evaluate_car_rental_mobility_toll_escrow_policy(
            CarRentalMobilityTollEscrowPolicyInput(
                quarterly_car_rental_mobility_pool_usd=Decimal("320000.00"),
                pre_existing_scratch_diff_mismatch_or_unverified_damage_claim_detected=False,
                duplicate_cdw_upsell_or_telematics_fuel_soc_parity_breach_detected=True,
                webiq_nhtsa_vin_recall_or_expired_toll_settlement_window_flag=False,
                restricted_key_age_days=30,
                instant_0420_deposit_release_and_bounded_toll_sub_mandate_enabled=False,
            )
        )
        self.assertEqual(cdw_block["http_status"], 422)
        self.assertEqual(
            cdw_block["decision"],
            "DUPLICATE_CDW_UPSELL_OR_TELEMATICS_FUEL_SOC_PARITY_BREACH_BLOCKED",
        )

        recall_hold = evaluate_car_rental_mobility_toll_escrow_policy(
            CarRentalMobilityTollEscrowPolicyInput(
                quarterly_car_rental_mobility_pool_usd=Decimal("320000.00"),
                pre_existing_scratch_diff_mismatch_or_unverified_damage_claim_detected=False,
                duplicate_cdw_upsell_or_telematics_fuel_soc_parity_breach_detected=False,
                webiq_nhtsa_vin_recall_or_expired_toll_settlement_window_flag=True,
                restricted_key_age_days=191,
                instant_0420_deposit_release_and_bounded_toll_sub_mandate_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(
            recall_hold["decision"],
            "WEBIQ_NHTSA_VIN_RECALL_OR_EXPIRED_TOLL_SETTLEMENT_WINDOW_HOLD",
        )

        opt_confirm = evaluate_car_rental_mobility_toll_escrow_policy(
            CarRentalMobilityTollEscrowPolicyInput(
                quarterly_car_rental_mobility_pool_usd=Decimal("320000.00"),
                pre_existing_scratch_diff_mismatch_or_unverified_damage_claim_detected=False,
                duplicate_cdw_upsell_or_telematics_fuel_soc_parity_breach_detected=False,
                webiq_nhtsa_vin_recall_or_expired_toll_settlement_window_flag=False,
                restricted_key_age_days=30,
                instant_0420_deposit_release_and_bounded_toll_sub_mandate_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "73600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "246400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("car_rental_mobility_toll_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("car-rental-mobility-toll-escrow-sandbox", html)

    def test_home_remodeling_cad_milestone_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            HomeRemodelingCadMilestoneEscrowPolicyInput,
            evaluate_home_remodeling_cad_milestone_escrow_policy,
        )

        happy = evaluate_home_remodeling_cad_milestone_escrow_policy(
            HomeRemodelingCadMilestoneEscrowPolicyInput(
                quarterly_home_remodeling_cabinetry_pool_usd=Decimal("420000.00"),
                unverified_lidar_cad_or_mep_collision_custom_millwork_detected=False,
                predatory_change_order_surcharge_or_incomplete_boq_bait_detected=False,
                webiq_contractor_license_lapse_or_unwaived_supplier_lien_flag=False,
                restricted_key_age_days=30,
                stage_gated_30_30_30_10_escrow_and_factory_direct_split_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "LIDAR_CAD_BOQ_COMPLETE_AND_MILESTONE_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["home_remodeling_escrow_token"]).startswith("home_remodeling_cad_milestone_escrow_mandate_")
        )

        lidar_block = evaluate_home_remodeling_cad_milestone_escrow_policy(
            HomeRemodelingCadMilestoneEscrowPolicyInput(
                quarterly_home_remodeling_cabinetry_pool_usd=Decimal("420000.00"),
                unverified_lidar_cad_or_mep_collision_custom_millwork_detected=True,
                predatory_change_order_surcharge_or_incomplete_boq_bait_detected=False,
                webiq_contractor_license_lapse_or_unwaived_supplier_lien_flag=False,
                restricted_key_age_days=30,
                stage_gated_30_30_30_10_escrow_and_factory_direct_split_enabled=False,
            )
        )
        self.assertEqual(lidar_block["http_status"], 403)
        self.assertEqual(
            lidar_block["decision"],
            "UNVERIFIED_LIDAR_CAD_OR_MEP_COLLISION_CUSTOM_MILLWORK_BLOCKED",
        )

        boq_block = evaluate_home_remodeling_cad_milestone_escrow_policy(
            HomeRemodelingCadMilestoneEscrowPolicyInput(
                quarterly_home_remodeling_cabinetry_pool_usd=Decimal("420000.00"),
                unverified_lidar_cad_or_mep_collision_custom_millwork_detected=False,
                predatory_change_order_surcharge_or_incomplete_boq_bait_detected=True,
                webiq_contractor_license_lapse_or_unwaived_supplier_lien_flag=False,
                restricted_key_age_days=30,
                stage_gated_30_30_30_10_escrow_and_factory_direct_split_enabled=False,
            )
        )
        self.assertEqual(boq_block["http_status"], 422)
        self.assertEqual(
            boq_block["decision"],
            "PREDATORY_CHANGE_ORDER_SURCHARGE_OR_INCOMPLETE_BOQ_BAIT_BLOCKED",
        )

        lien_hold = evaluate_home_remodeling_cad_milestone_escrow_policy(
            HomeRemodelingCadMilestoneEscrowPolicyInput(
                quarterly_home_remodeling_cabinetry_pool_usd=Decimal("420000.00"),
                unverified_lidar_cad_or_mep_collision_custom_millwork_detected=False,
                predatory_change_order_surcharge_or_incomplete_boq_bait_detected=False,
                webiq_contractor_license_lapse_or_unwaived_supplier_lien_flag=True,
                restricted_key_age_days=191,
                stage_gated_30_30_30_10_escrow_and_factory_direct_split_enabled=False,
            )
        )
        self.assertEqual(lien_hold["http_status"], 451)
        self.assertEqual(
            lien_hold["decision"],
            "WEBIQ_CONTRACTOR_LICENSE_LAPSE_OR_UNWAIVED_SUPPLIER_LIEN_HOLD",
        )

        opt_confirm = evaluate_home_remodeling_cad_milestone_escrow_policy(
            HomeRemodelingCadMilestoneEscrowPolicyInput(
                quarterly_home_remodeling_cabinetry_pool_usd=Decimal("420000.00"),
                unverified_lidar_cad_or_mep_collision_custom_millwork_detected=False,
                predatory_change_order_surcharge_or_incomplete_boq_bait_detected=False,
                webiq_contractor_license_lapse_or_unwaived_supplier_lien_flag=False,
                restricted_key_age_days=30,
                stage_gated_30_30_30_10_escrow_and_factory_direct_split_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "92400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "327600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("home_remodeling_cad_milestone_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("home-remodeling-cad-milestone-escrow-sandbox", html)

    def test_b2b_packaging_print_preflight_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bPackagingPrintPreflightEscrowPolicyInput,
            evaluate_b2b_packaging_print_preflight_escrow_policy,
        )

        happy = evaluate_b2b_packaging_print_preflight_escrow_policy(
            B2bPackagingPrintPreflightEscrowPolicyInput(
                quarterly_b2b_packaging_print_pool_usd=Decimal("290000.00"),
                pdfx4_preflight_bleed_dpi_fail_or_unsigned_3d_dieline_proof_detected=False,
                duplicate_dieline_tooling_charge_or_overrun_tolerance_breach_detected=False,
                webiq_food_contact_ink_hazard_or_fsc_cert_revocation_flag=False,
                restricted_key_age_days=30,
                gang_run_imposition_and_spectrophotometer_delta_e_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "PDFX4_PREFLIGHT_DIELINE_AND_COLOR_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["packaging_print_escrow_token"]).startswith("b2b_packaging_print_preflight_escrow_mandate_")
        )

        pdf_block = evaluate_b2b_packaging_print_preflight_escrow_policy(
            B2bPackagingPrintPreflightEscrowPolicyInput(
                quarterly_b2b_packaging_print_pool_usd=Decimal("290000.00"),
                pdfx4_preflight_bleed_dpi_fail_or_unsigned_3d_dieline_proof_detected=True,
                duplicate_dieline_tooling_charge_or_overrun_tolerance_breach_detected=False,
                webiq_food_contact_ink_hazard_or_fsc_cert_revocation_flag=False,
                restricted_key_age_days=30,
                gang_run_imposition_and_spectrophotometer_delta_e_escrow_enabled=False,
            )
        )
        self.assertEqual(pdf_block["http_status"], 403)
        self.assertEqual(
            pdf_block["decision"],
            "PDFX4_PREFLIGHT_BLEED_DPI_FAIL_OR_UNSIGNED_3D_DIELINE_PROOF_BLOCKED",
        )

        die_block = evaluate_b2b_packaging_print_preflight_escrow_policy(
            B2bPackagingPrintPreflightEscrowPolicyInput(
                quarterly_b2b_packaging_print_pool_usd=Decimal("290000.00"),
                pdfx4_preflight_bleed_dpi_fail_or_unsigned_3d_dieline_proof_detected=False,
                duplicate_dieline_tooling_charge_or_overrun_tolerance_breach_detected=True,
                webiq_food_contact_ink_hazard_or_fsc_cert_revocation_flag=False,
                restricted_key_age_days=30,
                gang_run_imposition_and_spectrophotometer_delta_e_escrow_enabled=False,
            )
        )
        self.assertEqual(die_block["http_status"], 422)
        self.assertEqual(
            die_block["decision"],
            "DUPLICATE_DIELINE_TOOLING_CHARGE_OR_OVERRUN_TOLERANCE_BREACH_BLOCKED",
        )

        fsc_hold = evaluate_b2b_packaging_print_preflight_escrow_policy(
            B2bPackagingPrintPreflightEscrowPolicyInput(
                quarterly_b2b_packaging_print_pool_usd=Decimal("290000.00"),
                pdfx4_preflight_bleed_dpi_fail_or_unsigned_3d_dieline_proof_detected=False,
                duplicate_dieline_tooling_charge_or_overrun_tolerance_breach_detected=False,
                webiq_food_contact_ink_hazard_or_fsc_cert_revocation_flag=True,
                restricted_key_age_days=191,
                gang_run_imposition_and_spectrophotometer_delta_e_escrow_enabled=False,
            )
        )
        self.assertEqual(fsc_hold["http_status"], 451)
        self.assertEqual(
            fsc_hold["decision"],
            "WEBIQ_FOOD_CONTACT_INK_HAZARD_OR_FSC_CERT_REVOCATION_HOLD",
        )

        opt_confirm = evaluate_b2b_packaging_print_preflight_escrow_policy(
            B2bPackagingPrintPreflightEscrowPolicyInput(
                quarterly_b2b_packaging_print_pool_usd=Decimal("290000.00"),
                pdfx4_preflight_bleed_dpi_fail_or_unsigned_3d_dieline_proof_detected=False,
                duplicate_dieline_tooling_charge_or_overrun_tolerance_breach_detected=False,
                webiq_food_contact_ink_hazard_or_fsc_cert_revocation_flag=False,
                restricted_key_age_days=30,
                gang_run_imposition_and_spectrophotometer_delta_e_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "60900.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "229100.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_packaging_print_preflight_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-packaging-print-preflight-escrow-sandbox", html)

    def test_ecommerce_tbyb_preauth_wardrobing_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            EcommerceTbybPreauthWardrobingPolicyInput,
            evaluate_ecommerce_tbyb_preauth_wardrobing_policy,
        )

        happy = evaluate_ecommerce_tbyb_preauth_wardrobing_policy(
            EcommerceTbybPreauthWardrobingPolicyInput(
                quarterly_ecommerce_tbyb_trial_pool_usd=Decimal("260000.00"),
                prepaid_bin_tbyb_abuse_or_excessive_size_bracketing_detected=False,
                post_dropoff_scan_capture_race_or_broken_security_ribbon_detected=False,
                expired_card_auth_window_or_missing_carrier_scan_flag=False,
                restricted_key_age_days=30,
                delivery_triggered_spt_auth_and_keep_bundle_incentive_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "TBYB_PREAUTH_AND_PARTIAL_KEEP_CAPTURE_AUTHORIZED")
        self.assertTrue(
            str(happy["tbyb_trial_escrow_token"]).startswith("ecommerce_tbyb_preauth_wardrobing_mandate_")
        )

        bin_block = evaluate_ecommerce_tbyb_preauth_wardrobing_policy(
            EcommerceTbybPreauthWardrobingPolicyInput(
                quarterly_ecommerce_tbyb_trial_pool_usd=Decimal("260000.00"),
                prepaid_bin_tbyb_abuse_or_excessive_size_bracketing_detected=True,
                post_dropoff_scan_capture_race_or_broken_security_ribbon_detected=False,
                expired_card_auth_window_or_missing_carrier_scan_flag=False,
                restricted_key_age_days=30,
                delivery_triggered_spt_auth_and_keep_bundle_incentive_enabled=False,
            )
        )
        self.assertEqual(bin_block["http_status"], 403)
        self.assertEqual(
            bin_block["decision"],
            "PREPAID_BIN_TBYB_ABUSE_OR_EXCESSIVE_SIZE_BRACKETING_BLOCKED",
        )

        ribbon_block = evaluate_ecommerce_tbyb_preauth_wardrobing_policy(
            EcommerceTbybPreauthWardrobingPolicyInput(
                quarterly_ecommerce_tbyb_trial_pool_usd=Decimal("260000.00"),
                prepaid_bin_tbyb_abuse_or_excessive_size_bracketing_detected=False,
                post_dropoff_scan_capture_race_or_broken_security_ribbon_detected=True,
                expired_card_auth_window_or_missing_carrier_scan_flag=False,
                restricted_key_age_days=30,
                delivery_triggered_spt_auth_and_keep_bundle_incentive_enabled=False,
            )
        )
        self.assertEqual(ribbon_block["http_status"], 422)
        self.assertEqual(
            ribbon_block["decision"],
            "POST_DROPOFF_SCAN_CAPTURE_RACE_OR_BROKEN_SECURITY_RIBBON_BLOCKED",
        )

        expiry_hold = evaluate_ecommerce_tbyb_preauth_wardrobing_policy(
            EcommerceTbybPreauthWardrobingPolicyInput(
                quarterly_ecommerce_tbyb_trial_pool_usd=Decimal("260000.00"),
                prepaid_bin_tbyb_abuse_or_excessive_size_bracketing_detected=False,
                post_dropoff_scan_capture_race_or_broken_security_ribbon_detected=False,
                expired_card_auth_window_or_missing_carrier_scan_flag=True,
                restricted_key_age_days=191,
                delivery_triggered_spt_auth_and_keep_bundle_incentive_enabled=False,
            )
        )
        self.assertEqual(expiry_hold["http_status"], 451)
        self.assertEqual(
            expiry_hold["decision"],
            "EXPIRED_CARD_AUTH_WINDOW_OR_MISSING_CARRIER_SCAN_HOLD",
        )

        opt_confirm = evaluate_ecommerce_tbyb_preauth_wardrobing_policy(
            EcommerceTbybPreauthWardrobingPolicyInput(
                quarterly_ecommerce_tbyb_trial_pool_usd=Decimal("260000.00"),
                prepaid_bin_tbyb_abuse_or_excessive_size_bracketing_detected=False,
                post_dropoff_scan_capture_race_or_broken_security_ribbon_detected=False,
                expired_card_auth_window_or_missing_carrier_scan_flag=False,
                restricted_key_age_days=30,
                delivery_triggered_spt_auth_and_keep_bundle_incentive_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "65000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "195000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("ecommerce_tbyb_preauth_wardrobing_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("ecommerce-tbyb-preauth-wardrobing-sandbox", html)

    def test_b2b_data_marketplace_cleanroom_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bDataMarketplaceCleanroomEscrowPolicyInput,
            evaluate_b2b_data_marketplace_cleanroom_escrow_policy,
        )

        happy = evaluate_b2b_data_marketplace_cleanroom_escrow_policy(
            B2bDataMarketplaceCleanroomEscrowPolicyInput(
                quarterly_b2b_data_marketplace_pool_usd=Decimal("380000.00"),
                unverified_data_sample_completeness_or_stale_timestamp_detected=False,
                unbounded_query_row_explosion_or_redistribution_license_breach_detected=False,
                webiq_sec_mnpi_compliance_risk_or_unconsented_pii_data_flag=False,
                restricted_key_age_days=30,
                zero_copy_cleanroom_and_x402_delta_row_metering_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "CLEANROOM_SAMPLE_VERIFIED_AND_DELTA_API_AUTHORIZED")
        self.assertTrue(
            str(happy["data_marketplace_escrow_token"]).startswith("b2b_data_marketplace_cleanroom_mandate_")
        )

        sample_block = evaluate_b2b_data_marketplace_cleanroom_escrow_policy(
            B2bDataMarketplaceCleanroomEscrowPolicyInput(
                quarterly_b2b_data_marketplace_pool_usd=Decimal("380000.00"),
                unverified_data_sample_completeness_or_stale_timestamp_detected=True,
                unbounded_query_row_explosion_or_redistribution_license_breach_detected=False,
                webiq_sec_mnpi_compliance_risk_or_unconsented_pii_data_flag=False,
                restricted_key_age_days=30,
                zero_copy_cleanroom_and_x402_delta_row_metering_enabled=False,
            )
        )
        self.assertEqual(sample_block["http_status"], 403)
        self.assertEqual(
            sample_block["decision"],
            "UNVERIFIED_DATA_SAMPLE_COMPLETENESS_OR_STALE_TIMESTAMP_BLOCKED",
        )

        scan_block = evaluate_b2b_data_marketplace_cleanroom_escrow_policy(
            B2bDataMarketplaceCleanroomEscrowPolicyInput(
                quarterly_b2b_data_marketplace_pool_usd=Decimal("380000.00"),
                unverified_data_sample_completeness_or_stale_timestamp_detected=False,
                unbounded_query_row_explosion_or_redistribution_license_breach_detected=True,
                webiq_sec_mnpi_compliance_risk_or_unconsented_pii_data_flag=False,
                restricted_key_age_days=30,
                zero_copy_cleanroom_and_x402_delta_row_metering_enabled=False,
            )
        )
        self.assertEqual(scan_block["http_status"], 422)
        self.assertEqual(
            scan_block["decision"],
            "UNBOUNDED_QUERY_ROW_EXPLOSION_OR_REDISTRIBUTION_LICENSE_BREACH_BLOCKED",
        )

        mnpi_hold = evaluate_b2b_data_marketplace_cleanroom_escrow_policy(
            B2bDataMarketplaceCleanroomEscrowPolicyInput(
                quarterly_b2b_data_marketplace_pool_usd=Decimal("380000.00"),
                unverified_data_sample_completeness_or_stale_timestamp_detected=False,
                unbounded_query_row_explosion_or_redistribution_license_breach_detected=False,
                webiq_sec_mnpi_compliance_risk_or_unconsented_pii_data_flag=True,
                restricted_key_age_days=191,
                zero_copy_cleanroom_and_x402_delta_row_metering_enabled=False,
            )
        )
        self.assertEqual(mnpi_hold["http_status"], 451)
        self.assertEqual(
            mnpi_hold["decision"],
            "WEBIQ_SEC_MNPI_COMPLIANCE_RISK_OR_UNCONSENTED_PII_DATA_HOLD",
        )

        opt_confirm = evaluate_b2b_data_marketplace_cleanroom_escrow_policy(
            B2bDataMarketplaceCleanroomEscrowPolicyInput(
                quarterly_b2b_data_marketplace_pool_usd=Decimal("380000.00"),
                unverified_data_sample_completeness_or_stale_timestamp_detected=False,
                unbounded_query_row_explosion_or_redistribution_license_breach_detected=False,
                webiq_sec_mnpi_compliance_risk_or_unconsented_pii_data_flag=False,
                restricted_key_age_days=30,
                zero_copy_cleanroom_and_x402_delta_row_metering_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "106400.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "273600.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_data_marketplace_cleanroom_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-data-marketplace-cleanroom-escrow-sandbox", html)

    def test_local_o2o_voucher_dynamic_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            LocalO2oVoucherDynamicEscrowPolicyInput,
            evaluate_local_o2o_voucher_dynamic_escrow_policy,
        )

        happy = evaluate_local_o2o_voucher_dynamic_escrow_policy(
            LocalO2oVoucherDynamicEscrowPolicyInput(
                quarterly_local_o2o_voucher_pool_usd=Decimal("310000.00"),
                static_voucher_screenshot_replay_or_peak_blackout_mismatch_detected=False,
                merchant_wash_redemption_subsidy_fraud_or_bundled_surcharge_detected=False,
                webiq_health_inspection_closure_or_escrow_reserve_deficit_flag=False,
                restricted_key_age_days=30,
                per_punch_escrow_release_and_expired_auto_refund_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "DYNAMIC_TOTP_LBS_AND_POS_REDEMPTION_AUTHORIZED")
        self.assertTrue(
            str(happy["local_o2o_voucher_token"]).startswith("local_o2o_voucher_dynamic_escrow_mandate_")
        )

        screenshot_block = evaluate_local_o2o_voucher_dynamic_escrow_policy(
            LocalO2oVoucherDynamicEscrowPolicyInput(
                quarterly_local_o2o_voucher_pool_usd=Decimal("310000.00"),
                static_voucher_screenshot_replay_or_peak_blackout_mismatch_detected=True,
                merchant_wash_redemption_subsidy_fraud_or_bundled_surcharge_detected=False,
                webiq_health_inspection_closure_or_escrow_reserve_deficit_flag=False,
                restricted_key_age_days=30,
                per_punch_escrow_release_and_expired_auto_refund_enabled=False,
            )
        )
        self.assertEqual(screenshot_block["http_status"], 403)
        self.assertEqual(
            screenshot_block["decision"],
            "STATIC_VOUCHER_SCREENSHOT_REPLAY_OR_PEAK_BLACKOUT_MISMATCH_BLOCKED",
        )

        wash_block = evaluate_local_o2o_voucher_dynamic_escrow_policy(
            LocalO2oVoucherDynamicEscrowPolicyInput(
                quarterly_local_o2o_voucher_pool_usd=Decimal("310000.00"),
                static_voucher_screenshot_replay_or_peak_blackout_mismatch_detected=False,
                merchant_wash_redemption_subsidy_fraud_or_bundled_surcharge_detected=True,
                webiq_health_inspection_closure_or_escrow_reserve_deficit_flag=False,
                restricted_key_age_days=30,
                per_punch_escrow_release_and_expired_auto_refund_enabled=False,
            )
        )
        self.assertEqual(wash_block["http_status"], 422)
        self.assertEqual(
            wash_block["decision"],
            "MERCHANT_WASH_REDEMPTION_SUBSIDY_FRAUD_OR_BUNDLED_SURCHARGE_BLOCKED",
        )

        health_hold = evaluate_local_o2o_voucher_dynamic_escrow_policy(
            LocalO2oVoucherDynamicEscrowPolicyInput(
                quarterly_local_o2o_voucher_pool_usd=Decimal("310000.00"),
                static_voucher_screenshot_replay_or_peak_blackout_mismatch_detected=False,
                merchant_wash_redemption_subsidy_fraud_or_bundled_surcharge_detected=False,
                webiq_health_inspection_closure_or_escrow_reserve_deficit_flag=True,
                restricted_key_age_days=191,
                per_punch_escrow_release_and_expired_auto_refund_enabled=False,
            )
        )
        self.assertEqual(health_hold["http_status"], 451)
        self.assertEqual(
            health_hold["decision"],
            "WEBIQ_HEALTH_INSPECTION_CLOSURE_OR_ESCROW_RESERVE_DEFICIT_HOLD",
        )

        opt_confirm = evaluate_local_o2o_voucher_dynamic_escrow_policy(
            LocalO2oVoucherDynamicEscrowPolicyInput(
                quarterly_local_o2o_voucher_pool_usd=Decimal("310000.00"),
                static_voucher_screenshot_replay_or_peak_blackout_mismatch_detected=False,
                merchant_wash_redemption_subsidy_fraud_or_bundled_surcharge_detected=False,
                webiq_health_inspection_closure_or_escrow_reserve_deficit_flag=False,
                restricted_key_age_days=30,
                per_punch_escrow_release_and_expired_auto_refund_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "68200.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "241800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("local_o2o_voucher_dynamic_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("local-o2o-voucher-dynamic-escrow-sandbox", html)

    def test_warranty_advanced_rma_collateral_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            WarrantyAdvancedRmaCollateralPolicyInput,
            evaluate_warranty_advanced_rma_collateral_policy,
        )

        happy = evaluate_warranty_advanced_rma_collateral_policy(
            WarrantyAdvancedRmaCollateralPolicyInput(
                quarterly_warranty_advanced_rma_pool_usd=Decimal("340000.00"),
                post_purchase_warranty_without_remote_diagnostic_attestation_detected=False,
                uncollateralized_advanced_rma_or_repair_part_padding_detected=False,
                webiq_manufacturer_recall_free_repair_precedence_flag=False,
                restricted_key_age_days=30,
                collateralized_advanced_rma_and_salvage_replacement_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "DIAGNOSTIC_VERIFIED_AND_COLLATERAL_RMA_AUTHORIZED")
        self.assertTrue(
            str(happy["warranty_rma_escrow_token"]).startswith("warranty_advanced_rma_collateral_mandate_")
        )

        crash_block = evaluate_warranty_advanced_rma_collateral_policy(
            WarrantyAdvancedRmaCollateralPolicyInput(
                quarterly_warranty_advanced_rma_pool_usd=Decimal("340000.00"),
                post_purchase_warranty_without_remote_diagnostic_attestation_detected=True,
                uncollateralized_advanced_rma_or_repair_part_padding_detected=False,
                webiq_manufacturer_recall_free_repair_precedence_flag=False,
                restricted_key_age_days=30,
                collateralized_advanced_rma_and_salvage_replacement_enabled=False,
            )
        )
        self.assertEqual(crash_block["http_status"], 403)
        self.assertEqual(
            crash_block["decision"],
            "POST_PURCHASE_WARRANTY_WITHOUT_REMOTE_DIAGNOSTIC_ATTESTATION_BLOCKED",
        )

        pad_block = evaluate_warranty_advanced_rma_collateral_policy(
            WarrantyAdvancedRmaCollateralPolicyInput(
                quarterly_warranty_advanced_rma_pool_usd=Decimal("340000.00"),
                post_purchase_warranty_without_remote_diagnostic_attestation_detected=False,
                uncollateralized_advanced_rma_or_repair_part_padding_detected=True,
                webiq_manufacturer_recall_free_repair_precedence_flag=False,
                restricted_key_age_days=30,
                collateralized_advanced_rma_and_salvage_replacement_enabled=False,
            )
        )
        self.assertEqual(pad_block["http_status"], 422)
        self.assertEqual(
            pad_block["decision"],
            "UNCOLLATERALIZED_ADVANCED_RMA_OR_REPAIR_PART_PADDING_BLOCKED",
        )

        recall_hold = evaluate_warranty_advanced_rma_collateral_policy(
            WarrantyAdvancedRmaCollateralPolicyInput(
                quarterly_warranty_advanced_rma_pool_usd=Decimal("340000.00"),
                post_purchase_warranty_without_remote_diagnostic_attestation_detected=False,
                uncollateralized_advanced_rma_or_repair_part_padding_detected=False,
                webiq_manufacturer_recall_free_repair_precedence_flag=True,
                restricted_key_age_days=191,
                collateralized_advanced_rma_and_salvage_replacement_enabled=False,
            )
        )
        self.assertEqual(recall_hold["http_status"], 451)
        self.assertEqual(
            recall_hold["decision"],
            "WEBIQ_MANUFACTURER_RECALL_FREE_REPAIR_PRECEDENCE_HOLD",
        )

        opt_confirm = evaluate_warranty_advanced_rma_collateral_policy(
            WarrantyAdvancedRmaCollateralPolicyInput(
                quarterly_warranty_advanced_rma_pool_usd=Decimal("340000.00"),
                post_purchase_warranty_without_remote_diagnostic_attestation_detected=False,
                uncollateralized_advanced_rma_or_repair_part_padding_detected=False,
                webiq_manufacturer_recall_free_repair_precedence_flag=False,
                restricted_key_age_days=30,
                collateralized_advanced_rma_and_salvage_replacement_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "81600.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "258400.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("warranty_advanced_rma_collateral_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("warranty-advanced-rma-collateral-sandbox", html)

    def test_ecommerce_preorder_ftc_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            EcommercePreorderFtcEscrowPolicyInput,
            evaluate_ecommerce_preorder_ftc_escrow_policy,
        )

        happy = evaluate_ecommerce_preorder_ftc_escrow_policy(
            EcommercePreorderFtcEscrowPolicyInput(
                quarterly_ecommerce_preorder_pool_usd=Decimal("350000.00"),
                preorder_batch_capacity_exceeded_without_delivery_date_step_detected=False,
                ftc_mail_order_delay_without_explicit_buyer_optin_or_auto_refund_detected=False,
                preorder_upfront_capture_chargeback_reserve_risk_flag=False,
                restricted_key_age_days=30,
                vaulted_180d_spt_capture_at_warehouse_allocation_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "BATCH_ALLOCATED_AND_FTC_PREORDER_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["preorder_ftc_escrow_token"]).startswith("preorder_ftc_mail_order_escrow_mandate_")
        )

        batch_block = evaluate_ecommerce_preorder_ftc_escrow_policy(
            EcommercePreorderFtcEscrowPolicyInput(
                quarterly_ecommerce_preorder_pool_usd=Decimal("350000.00"),
                preorder_batch_capacity_exceeded_without_delivery_date_step_detected=True,
                ftc_mail_order_delay_without_explicit_buyer_optin_or_auto_refund_detected=False,
                preorder_upfront_capture_chargeback_reserve_risk_flag=False,
                restricted_key_age_days=30,
                vaulted_180d_spt_capture_at_warehouse_allocation_enabled=False,
            )
        )
        self.assertEqual(batch_block["http_status"], 403)
        self.assertEqual(
            batch_block["decision"],
            "PREORDER_BATCH_CAPACITY_EXCEEDED_WITHOUT_DELIVERY_DATE_STEP_BLOCKED",
        )

        ftc_block = evaluate_ecommerce_preorder_ftc_escrow_policy(
            EcommercePreorderFtcEscrowPolicyInput(
                quarterly_ecommerce_preorder_pool_usd=Decimal("350000.00"),
                preorder_batch_capacity_exceeded_without_delivery_date_step_detected=False,
                ftc_mail_order_delay_without_explicit_buyer_optin_or_auto_refund_detected=True,
                preorder_upfront_capture_chargeback_reserve_risk_flag=False,
                restricted_key_age_days=30,
                vaulted_180d_spt_capture_at_warehouse_allocation_enabled=False,
            )
        )
        self.assertEqual(ftc_block["http_status"], 422)
        self.assertEqual(
            ftc_block["decision"],
            "FTC_MAIL_ORDER_DELAY_WITHOUT_EXPLICIT_BUYER_OPTIN_OR_AUTO_REFUND_BLOCKED",
        )

        reserve_hold = evaluate_ecommerce_preorder_ftc_escrow_policy(
            EcommercePreorderFtcEscrowPolicyInput(
                quarterly_ecommerce_preorder_pool_usd=Decimal("350000.00"),
                preorder_batch_capacity_exceeded_without_delivery_date_step_detected=False,
                ftc_mail_order_delay_without_explicit_buyer_optin_or_auto_refund_detected=False,
                preorder_upfront_capture_chargeback_reserve_risk_flag=True,
                restricted_key_age_days=191,
                vaulted_180d_spt_capture_at_warehouse_allocation_enabled=False,
            )
        )
        self.assertEqual(reserve_hold["http_status"], 451)
        self.assertEqual(
            reserve_hold["decision"],
            "PREORDER_UPFRONT_CAPTURE_CHARGEBACK_RESERVE_RISK_HOLD",
        )

        opt_confirm = evaluate_ecommerce_preorder_ftc_escrow_policy(
            EcommercePreorderFtcEscrowPolicyInput(
                quarterly_ecommerce_preorder_pool_usd=Decimal("350000.00"),
                preorder_batch_capacity_exceeded_without_delivery_date_step_detected=False,
                ftc_mail_order_delay_without_explicit_buyer_optin_or_auto_refund_detected=False,
                preorder_upfront_capture_chargeback_reserve_risk_flag=False,
                restricted_key_age_days=30,
                vaulted_180d_spt_capture_at_warehouse_allocation_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "91000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "259000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("ecommerce_preorder_ftc_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("ecommerce-preorder-ftc-escrow-sandbox", html)

    def test_b2b_media_buying_mfa_rebate_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bMediaBuyingMfaRebateEscrowPolicyInput,
            evaluate_b2b_media_buying_mfa_rebate_escrow_policy,
        )

        happy = evaluate_b2b_media_buying_mfa_rebate_escrow_policy(
            B2bMediaBuyingMfaRebateEscrowPolicyInput(
                quarterly_b2b_media_buying_pool_usd=Decimal("450000.00"),
                mfa_slop_inventory_or_adstxt_spoofing_placement_detected=False,
                undisclosed_agency_rebate_or_unverified_impression_billing_detected=False,
                webiq_brand_safety_crisis_or_regulatory_ad_compliance_flag=False,
                restricted_key_age_days=30,
                spo_direct_path_pruning_and_net_of_rebate_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "MRC_VIEWABLE_AND_NET_REBATE_MEDIA_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["media_buying_escrow_token"]).startswith("b2b_media_buying_mfa_rebate_escrow_mandate_")
        )

        mfa_block = evaluate_b2b_media_buying_mfa_rebate_escrow_policy(
            B2bMediaBuyingMfaRebateEscrowPolicyInput(
                quarterly_b2b_media_buying_pool_usd=Decimal("450000.00"),
                mfa_slop_inventory_or_adstxt_spoofing_placement_detected=True,
                undisclosed_agency_rebate_or_unverified_impression_billing_detected=False,
                webiq_brand_safety_crisis_or_regulatory_ad_compliance_flag=False,
                restricted_key_age_days=30,
                spo_direct_path_pruning_and_net_of_rebate_escrow_enabled=False,
            )
        )
        self.assertEqual(mfa_block["http_status"], 403)
        self.assertEqual(
            mfa_block["decision"],
            "MFA_SLOP_INVENTORY_OR_ADSTXT_SPOOFING_PLACEMENT_BLOCKED",
        )

        rebate_block = evaluate_b2b_media_buying_mfa_rebate_escrow_policy(
            B2bMediaBuyingMfaRebateEscrowPolicyInput(
                quarterly_b2b_media_buying_pool_usd=Decimal("450000.00"),
                mfa_slop_inventory_or_adstxt_spoofing_placement_detected=False,
                undisclosed_agency_rebate_or_unverified_impression_billing_detected=True,
                webiq_brand_safety_crisis_or_regulatory_ad_compliance_flag=False,
                restricted_key_age_days=30,
                spo_direct_path_pruning_and_net_of_rebate_escrow_enabled=False,
            )
        )
        self.assertEqual(rebate_block["http_status"], 422)
        self.assertEqual(
            rebate_block["decision"],
            "UNDISCLOSED_AGENCY_REBATE_OR_UNVERIFIED_IMPRESSION_BILLING_BLOCKED",
        )

        garm_hold = evaluate_b2b_media_buying_mfa_rebate_escrow_policy(
            B2bMediaBuyingMfaRebateEscrowPolicyInput(
                quarterly_b2b_media_buying_pool_usd=Decimal("450000.00"),
                mfa_slop_inventory_or_adstxt_spoofing_placement_detected=False,
                undisclosed_agency_rebate_or_unverified_impression_billing_detected=False,
                webiq_brand_safety_crisis_or_regulatory_ad_compliance_flag=True,
                restricted_key_age_days=191,
                spo_direct_path_pruning_and_net_of_rebate_escrow_enabled=False,
            )
        )
        self.assertEqual(garm_hold["http_status"], 451)
        self.assertEqual(
            garm_hold["decision"],
            "WEBIQ_BRAND_SAFETY_CRISIS_OR_REGULATORY_AD_COMPLIANCE_HOLD",
        )

        opt_confirm = evaluate_b2b_media_buying_mfa_rebate_escrow_policy(
            B2bMediaBuyingMfaRebateEscrowPolicyInput(
                quarterly_b2b_media_buying_pool_usd=Decimal("450000.00"),
                mfa_slop_inventory_or_adstxt_spoofing_placement_detected=False,
                undisclosed_agency_rebate_or_unverified_impression_billing_detected=False,
                webiq_brand_safety_crisis_or_regulatory_ad_compliance_flag=False,
                restricted_key_age_days=30,
                spo_direct_path_pruning_and_net_of_rebate_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "103500.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "346500.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_media_buying_mfa_rebate_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-media-buying-mfa-rebate-escrow-sandbox", html)

    def test_lifesciences_sunshine_gpo_udi_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            LifesciencesSunshineGpoUdiPolicyInput,
            evaluate_lifesciences_sunshine_gpo_udi_policy,
        )

        happy = evaluate_lifesciences_sunshine_gpo_udi_policy(
            LifesciencesSunshineGpoUdiPolicyInput(
                quarterly_lifesciences_gpo_rebate_pool_usd=Decimal("480000.00"),
                hcp_meal_cap_breach_or_missing_npi_sunshine_act_attestation_detected=False,
                gpo_contract_diversion_or_unverified_udi_consumption_rebate_detected=False,
                webiq_oig_leie_exclusion_or_fda_device_recall_flag=False,
                restricted_key_age_days=30,
                or_rfid_udi_consignment_billing_and_edi849_rebate_netting_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "SUNSHINE_NPI_VERIFIED_AND_GPO_UDI_REBATE_AUTHORIZED")
        self.assertTrue(
            str(happy["lifesciences_gpo_token"]).startswith("lifesciences_sunshine_gpo_udi_mandate_")
        )

        npi_block = evaluate_lifesciences_sunshine_gpo_udi_policy(
            LifesciencesSunshineGpoUdiPolicyInput(
                quarterly_lifesciences_gpo_rebate_pool_usd=Decimal("480000.00"),
                hcp_meal_cap_breach_or_missing_npi_sunshine_act_attestation_detected=True,
                gpo_contract_diversion_or_unverified_udi_consumption_rebate_detected=False,
                webiq_oig_leie_exclusion_or_fda_device_recall_flag=False,
                restricted_key_age_days=30,
                or_rfid_udi_consignment_billing_and_edi849_rebate_netting_enabled=False,
            )
        )
        self.assertEqual(npi_block["http_status"], 403)
        self.assertEqual(
            npi_block["decision"],
            "HCP_MEAL_CAP_BREACH_OR_MISSING_NPI_SUNSHINE_ACT_ATTESTATION_BLOCKED",
        )

        gpo_block = evaluate_lifesciences_sunshine_gpo_udi_policy(
            LifesciencesSunshineGpoUdiPolicyInput(
                quarterly_lifesciences_gpo_rebate_pool_usd=Decimal("480000.00"),
                hcp_meal_cap_breach_or_missing_npi_sunshine_act_attestation_detected=False,
                gpo_contract_diversion_or_unverified_udi_consumption_rebate_detected=True,
                webiq_oig_leie_exclusion_or_fda_device_recall_flag=False,
                restricted_key_age_days=30,
                or_rfid_udi_consignment_billing_and_edi849_rebate_netting_enabled=False,
            )
        )
        self.assertEqual(gpo_block["http_status"], 422)
        self.assertEqual(
            gpo_block["decision"],
            "GPO_CONTRACT_DIVERSION_OR_UNVERIFIED_UDI_CONSUMPTION_REBATE_BLOCKED",
        )

        oig_hold = evaluate_lifesciences_sunshine_gpo_udi_policy(
            LifesciencesSunshineGpoUdiPolicyInput(
                quarterly_lifesciences_gpo_rebate_pool_usd=Decimal("480000.00"),
                hcp_meal_cap_breach_or_missing_npi_sunshine_act_attestation_detected=False,
                gpo_contract_diversion_or_unverified_udi_consumption_rebate_detected=False,
                webiq_oig_leie_exclusion_or_fda_device_recall_flag=True,
                restricted_key_age_days=191,
                or_rfid_udi_consignment_billing_and_edi849_rebate_netting_enabled=False,
            )
        )
        self.assertEqual(oig_hold["http_status"], 451)
        self.assertEqual(
            oig_hold["decision"],
            "WEBIQ_OIG_LEIE_EXCLUSION_OR_FDA_DEVICE_RECALL_HOLD",
        )

        opt_confirm = evaluate_lifesciences_sunshine_gpo_udi_policy(
            LifesciencesSunshineGpoUdiPolicyInput(
                quarterly_lifesciences_gpo_rebate_pool_usd=Decimal("480000.00"),
                hcp_meal_cap_breach_or_missing_npi_sunshine_act_attestation_detected=False,
                gpo_contract_diversion_or_unverified_udi_consumption_rebate_detected=False,
                webiq_oig_leie_exclusion_or_fda_device_recall_flag=False,
                restricted_key_age_days=30,
                or_rfid_udi_consignment_billing_and_edi849_rebate_netting_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "100800.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "379200.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("lifesciences_sunshine_gpo_udi_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("lifesciences-sunshine-gpo-udi-sandbox", html)

    def test_highered_tuition_fx_aml_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            HigheredTuitionFxAmlEscrowPolicyInput,
            evaluate_highered_tuition_fx_aml_escrow_policy,
        )

        happy = evaluate_highered_tuition_fx_aml_escrow_policy(
            HigheredTuitionFxAmlEscrowPolicyInput(
                quarterly_highered_tuition_fx_pool_usd=Decimal("520000.00"),
                third_party_unverified_card_tuition_proxy_fraud_detected=False,
                non_source_refund_laundering_or_ineligible_529_expense_detected=False,
                webiq_fx_declaration_or_title_iv_r2t4_statutory_flag=False,
                restricted_key_age_days=30,
                student_id_bound_wholesale_fx_and_return_to_source_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "STUDENT_KYC_FX_AND_529_QHEE_TUITION_AUTHORIZED")
        self.assertTrue(
            str(happy["highered_tuition_token"]).startswith("highered_tuition_fx_aml_escrow_mandate_")
        )

        proxy_block = evaluate_highered_tuition_fx_aml_escrow_policy(
            HigheredTuitionFxAmlEscrowPolicyInput(
                quarterly_highered_tuition_fx_pool_usd=Decimal("520000.00"),
                third_party_unverified_card_tuition_proxy_fraud_detected=True,
                non_source_refund_laundering_or_ineligible_529_expense_detected=False,
                webiq_fx_declaration_or_title_iv_r2t4_statutory_flag=False,
                restricted_key_age_days=30,
                student_id_bound_wholesale_fx_and_return_to_source_enabled=False,
            )
        )
        self.assertEqual(proxy_block["http_status"], 403)
        self.assertEqual(
            proxy_block["decision"],
            "THIRD_PARTY_UNVERIFIED_CARD_TUITION_PROXY_FRAUD_BLOCKED",
        )

        aml_block = evaluate_highered_tuition_fx_aml_escrow_policy(
            HigheredTuitionFxAmlEscrowPolicyInput(
                quarterly_highered_tuition_fx_pool_usd=Decimal("520000.00"),
                third_party_unverified_card_tuition_proxy_fraud_detected=False,
                non_source_refund_laundering_or_ineligible_529_expense_detected=True,
                webiq_fx_declaration_or_title_iv_r2t4_statutory_flag=False,
                restricted_key_age_days=30,
                student_id_bound_wholesale_fx_and_return_to_source_enabled=False,
            )
        )
        self.assertEqual(aml_block["http_status"], 422)
        self.assertEqual(
            aml_block["decision"],
            "NON_SOURCE_REFUND_LAUNDERING_OR_INELIGIBLE_529_EXPENSE_BLOCKED",
        )

        titleiv_hold = evaluate_highered_tuition_fx_aml_escrow_policy(
            HigheredTuitionFxAmlEscrowPolicyInput(
                quarterly_highered_tuition_fx_pool_usd=Decimal("520000.00"),
                third_party_unverified_card_tuition_proxy_fraud_detected=False,
                non_source_refund_laundering_or_ineligible_529_expense_detected=False,
                webiq_fx_declaration_or_title_iv_r2t4_statutory_flag=True,
                restricted_key_age_days=191,
                student_id_bound_wholesale_fx_and_return_to_source_enabled=False,
            )
        )
        self.assertEqual(titleiv_hold["http_status"], 451)
        self.assertEqual(
            titleiv_hold["decision"],
            "WEBIQ_FX_DECLARATION_OR_TITLE_IV_R2T4_STATUTORY_HOLD",
        )

        opt_confirm = evaluate_highered_tuition_fx_aml_escrow_policy(
            HigheredTuitionFxAmlEscrowPolicyInput(
                quarterly_highered_tuition_fx_pool_usd=Decimal("520000.00"),
                third_party_unverified_card_tuition_proxy_fraud_detected=False,
                non_source_refund_laundering_or_ineligible_529_expense_detected=False,
                webiq_fx_declaration_or_title_iv_r2t4_statutory_flag=False,
                restricted_key_age_days=30,
                student_id_bound_wholesale_fx_and_return_to_source_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "104000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "416000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("highered_tuition_fx_aml_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("highered-tuition-fx-aml-escrow-sandbox", html)

    def test_fintech_credit_regf_hardship_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            FintechCreditRegfHardshipPolicyInput,
            evaluate_fintech_credit_regf_hardship_policy,
        )

        happy = evaluate_fintech_credit_regf_hardship_policy(
            FintechCreditRegfHardshipPolicyInput(
                quarterly_fintech_credit_portfolio_pool_usd=Decimal("560000.00"),
                ecoa_prohibited_proxy_feature_or_synthetic_bustout_cycling_detected=False,
                cfpb_reg_f_7in7_frequency_breach_or_bankruptcy_stay_violation_detected=False,
                webiq_scra_6pct_cap_or_fema_disaster_forbearance_flag=False,
                restricted_key_age_days=30,
                open_banking_revenue_sweep_and_zero_fee_hardship_restructure_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "ECOA_FAIR_CREDIT_AND_REGF_SERVICING_AUTHORIZED")
        self.assertTrue(
            str(happy["fintech_credit_token"]).startswith("fintech_credit_regf_hardship_mandate_")
        )

        ecoa_block = evaluate_fintech_credit_regf_hardship_policy(
            FintechCreditRegfHardshipPolicyInput(
                quarterly_fintech_credit_portfolio_pool_usd=Decimal("560000.00"),
                ecoa_prohibited_proxy_feature_or_synthetic_bustout_cycling_detected=True,
                cfpb_reg_f_7in7_frequency_breach_or_bankruptcy_stay_violation_detected=False,
                webiq_scra_6pct_cap_or_fema_disaster_forbearance_flag=False,
                restricted_key_age_days=30,
                open_banking_revenue_sweep_and_zero_fee_hardship_restructure_enabled=False,
            )
        )
        self.assertEqual(ecoa_block["http_status"], 403)
        self.assertEqual(
            ecoa_block["decision"],
            "ECOA_PROHIBITED_PROXY_FEATURE_OR_SYNTHETIC_BUSTOUT_CYCLING_BLOCKED",
        )

        regf_block = evaluate_fintech_credit_regf_hardship_policy(
            FintechCreditRegfHardshipPolicyInput(
                quarterly_fintech_credit_portfolio_pool_usd=Decimal("560000.00"),
                ecoa_prohibited_proxy_feature_or_synthetic_bustout_cycling_detected=False,
                cfpb_reg_f_7in7_frequency_breach_or_bankruptcy_stay_violation_detected=True,
                webiq_scra_6pct_cap_or_fema_disaster_forbearance_flag=False,
                restricted_key_age_days=30,
                open_banking_revenue_sweep_and_zero_fee_hardship_restructure_enabled=False,
            )
        )
        self.assertEqual(regf_block["http_status"], 422)
        self.assertEqual(
            regf_block["decision"],
            "CFPB_REG_F_7IN7_FREQUENCY_BREACH_OR_BANKRUPTCY_STAY_VIOLATION_BLOCKED",
        )

        scra_hold = evaluate_fintech_credit_regf_hardship_policy(
            FintechCreditRegfHardshipPolicyInput(
                quarterly_fintech_credit_portfolio_pool_usd=Decimal("560000.00"),
                ecoa_prohibited_proxy_feature_or_synthetic_bustout_cycling_detected=False,
                cfpb_reg_f_7in7_frequency_breach_or_bankruptcy_stay_violation_detected=False,
                webiq_scra_6pct_cap_or_fema_disaster_forbearance_flag=True,
                restricted_key_age_days=191,
                open_banking_revenue_sweep_and_zero_fee_hardship_restructure_enabled=False,
            )
        )
        self.assertEqual(scra_hold["http_status"], 451)
        self.assertEqual(
            scra_hold["decision"],
            "WEBIQ_SCRA_6PCT_CAP_OR_FEMA_DISASTER_FORBEARANCE_HOLD",
        )

        opt_confirm = evaluate_fintech_credit_regf_hardship_policy(
            FintechCreditRegfHardshipPolicyInput(
                quarterly_fintech_credit_portfolio_pool_usd=Decimal("560000.00"),
                ecoa_prohibited_proxy_feature_or_synthetic_bustout_cycling_detected=False,
                cfpb_reg_f_7in7_frequency_breach_or_bankruptcy_stay_violation_detected=False,
                webiq_scra_6pct_cap_or_fema_disaster_forbearance_flag=False,
                restricted_key_age_days=30,
                open_banking_revenue_sweep_and_zero_fee_hardship_restructure_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "140000.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "420000.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("fintech_credit_regf_hardship_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("fintech-credit-regf-hardship-sandbox", html)

    def test_floral_bakery_time_window_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            FloralBakeryTimeWindowEscrowPolicyInput,
            evaluate_floral_bakery_time_window_escrow_policy,
        )

        happy = evaluate_floral_bakery_time_window_escrow_policy(
            FloralBakeryTimeWindowEscrowPolicyInput(
                quarterly_floral_bakery_gifting_pool_usd=Decimal("230000.00"),
                unauthorized_stem_downgrade_substitution_or_missing_pre_dispatch_photo_detected=False,
                occasion_time_window_sla_breach_or_fake_courier_pod_detected=False,
                webiq_feline_toxic_lily_hazard_or_ambient_cream_cake_melt_flag=False,
                restricted_key_age_days=30,
                hourly_florist_capacity_slot_and_pre_dispatch_vision_escrow_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "PRE_DISPATCH_VISION_AND_OCCASION_SLA_ESCROW_AUTHORIZED")
        self.assertTrue(
            str(happy["floral_bakery_escrow_token"]).startswith("floral_bakery_time_window_escrow_mandate_")
        )

        stem_block = evaluate_floral_bakery_time_window_escrow_policy(
            FloralBakeryTimeWindowEscrowPolicyInput(
                quarterly_floral_bakery_gifting_pool_usd=Decimal("230000.00"),
                unauthorized_stem_downgrade_substitution_or_missing_pre_dispatch_photo_detected=True,
                occasion_time_window_sla_breach_or_fake_courier_pod_detected=False,
                webiq_feline_toxic_lily_hazard_or_ambient_cream_cake_melt_flag=False,
                restricted_key_age_days=30,
                hourly_florist_capacity_slot_and_pre_dispatch_vision_escrow_enabled=False,
            )
        )
        self.assertEqual(stem_block["http_status"], 403)
        self.assertEqual(
            stem_block["decision"],
            "UNAUTHORIZED_STEM_DOWNGRADE_SUBSTITUTION_OR_MISSING_PRE_DISPATCH_PHOTO_BLOCKED",
        )

        sla_block = evaluate_floral_bakery_time_window_escrow_policy(
            FloralBakeryTimeWindowEscrowPolicyInput(
                quarterly_floral_bakery_gifting_pool_usd=Decimal("230000.00"),
                unauthorized_stem_downgrade_substitution_or_missing_pre_dispatch_photo_detected=False,
                occasion_time_window_sla_breach_or_fake_courier_pod_detected=True,
                webiq_feline_toxic_lily_hazard_or_ambient_cream_cake_melt_flag=False,
                restricted_key_age_days=30,
                hourly_florist_capacity_slot_and_pre_dispatch_vision_escrow_enabled=False,
            )
        )
        self.assertEqual(sla_block["http_status"], 422)
        self.assertEqual(
            sla_block["decision"],
            "OCCASION_TIME_WINDOW_SLA_BREACH_OR_FAKE_COURIER_POD_BLOCKED",
        )

        lily_hold = evaluate_floral_bakery_time_window_escrow_policy(
            FloralBakeryTimeWindowEscrowPolicyInput(
                quarterly_floral_bakery_gifting_pool_usd=Decimal("230000.00"),
                unauthorized_stem_downgrade_substitution_or_missing_pre_dispatch_photo_detected=False,
                occasion_time_window_sla_breach_or_fake_courier_pod_detected=False,
                webiq_feline_toxic_lily_hazard_or_ambient_cream_cake_melt_flag=True,
                restricted_key_age_days=191,
                hourly_florist_capacity_slot_and_pre_dispatch_vision_escrow_enabled=False,
            )
        )
        self.assertEqual(lily_hold["http_status"], 451)
        self.assertEqual(
            lily_hold["decision"],
            "WEBIQ_FELINE_TOXIC_LILY_HAZARD_OR_AMBIENT_CREAM_CAKE_MELT_HOLD",
        )

        opt_confirm = evaluate_floral_bakery_time_window_escrow_policy(
            FloralBakeryTimeWindowEscrowPolicyInput(
                quarterly_floral_bakery_gifting_pool_usd=Decimal("230000.00"),
                unauthorized_stem_downgrade_substitution_or_missing_pre_dispatch_photo_detected=False,
                occasion_time_window_sla_breach_or_fake_courier_pod_detected=False,
                webiq_feline_toxic_lily_hazard_or_ambient_cream_cake_melt_flag=False,
                restricted_key_age_days=30,
                hourly_florist_capacity_slot_and_pre_dispatch_vision_escrow_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "55200.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "174800.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("floral_bakery_time_window_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("floral-bakery-time-window-escrow-sandbox", html)

    def test_b2b_creative_ip_spdx_c2pa_escrow_selection(self) -> None:
        from decimal import Decimal
        from lab.webiq_commerce_demo import (
            B2bCreativeIpSpdxC2paEscrowPolicyInput,
            evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy,
        )

        happy = evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy(
            B2bCreativeIpSpdxC2paEscrowPolicyInput(
                quarterly_b2b_creative_ip_licensing_pool_usd=Decimal("270000.00"),
                eula_deployment_channel_mismatch_or_missing_model_release_detected=False,
                agpl_copyleft_contamination_or_editorial_asset_commercial_misuse_detected=False,
                webiq_unindemnified_genai_asset_or_dmca_takedown_flag=False,
                restricted_key_age_days=30,
                enterprise_dam_deduplication_and_sil_ofl_font_substitution_enabled=False,
            )
        )
        self.assertEqual(happy["http_status"], 200)
        self.assertEqual(happy["decision"], "EULA_SCOPE_SPDX_AND_C2PA_INDEMNITY_AUTHORIZED")
        self.assertTrue(
            str(happy["creative_ip_escrow_token"]).startswith("b2b_creative_ip_spdx_c2pa_escrow_mandate_")
        )

        eula_block = evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy(
            B2bCreativeIpSpdxC2paEscrowPolicyInput(
                quarterly_b2b_creative_ip_licensing_pool_usd=Decimal("270000.00"),
                eula_deployment_channel_mismatch_or_missing_model_release_detected=True,
                agpl_copyleft_contamination_or_editorial_asset_commercial_misuse_detected=False,
                webiq_unindemnified_genai_asset_or_dmca_takedown_flag=False,
                restricted_key_age_days=30,
                enterprise_dam_deduplication_and_sil_ofl_font_substitution_enabled=False,
            )
        )
        self.assertEqual(eula_block["http_status"], 403)
        self.assertEqual(
            eula_block["decision"],
            "EULA_DEPLOYMENT_CHANNEL_MISMATCH_OR_MISSING_MODEL_RELEASE_BLOCKED",
        )

        agpl_block = evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy(
            B2bCreativeIpSpdxC2paEscrowPolicyInput(
                quarterly_b2b_creative_ip_licensing_pool_usd=Decimal("270000.00"),
                eula_deployment_channel_mismatch_or_missing_model_release_detected=False,
                agpl_copyleft_contamination_or_editorial_asset_commercial_misuse_detected=True,
                webiq_unindemnified_genai_asset_or_dmca_takedown_flag=False,
                restricted_key_age_days=30,
                enterprise_dam_deduplication_and_sil_ofl_font_substitution_enabled=False,
            )
        )
        self.assertEqual(agpl_block["http_status"], 422)
        self.assertEqual(
            agpl_block["decision"],
            "AGPL_COPYLEFT_CONTAMINATION_OR_EDITORIAL_ASSET_COMMERCIAL_MISUSE_BLOCKED",
        )

        c2pa_hold = evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy(
            B2bCreativeIpSpdxC2paEscrowPolicyInput(
                quarterly_b2b_creative_ip_licensing_pool_usd=Decimal("270000.00"),
                eula_deployment_channel_mismatch_or_missing_model_release_detected=False,
                agpl_copyleft_contamination_or_editorial_asset_commercial_misuse_detected=False,
                webiq_unindemnified_genai_asset_or_dmca_takedown_flag=True,
                restricted_key_age_days=191,
                enterprise_dam_deduplication_and_sil_ofl_font_substitution_enabled=False,
            )
        )
        self.assertEqual(c2pa_hold["http_status"], 451)
        self.assertEqual(
            c2pa_hold["decision"],
            "WEBIQ_UNINDEMNIFIED_GENAI_ASSET_OR_DMCA_TAKEDOWN_HOLD",
        )

        opt_confirm = evaluate_b2b_creative_ip_spdx_c2pa_escrow_policy(
            B2bCreativeIpSpdxC2paEscrowPolicyInput(
                quarterly_b2b_creative_ip_licensing_pool_usd=Decimal("270000.00"),
                eula_deployment_channel_mismatch_or_missing_model_release_detected=False,
                agpl_copyleft_contamination_or_editorial_asset_commercial_misuse_detected=False,
                webiq_unindemnified_genai_asset_or_dmca_takedown_flag=False,
                restricted_key_age_days=30,
                enterprise_dam_deduplication_and_sil_ofl_font_substitution_enabled=True,
            )
        )
        self.assertEqual(opt_confirm["http_status"], 409)
        self.assertEqual(opt_confirm["savings_usd"], "72900.00")
        self.assertEqual(opt_confirm["approved_budget_usd"], "197100.00")

        suite = run_webiq_commerce_benchmark_suite()
        self.assertIn("b2b_creative_ip_spdx_c2pa_escrow_guard", suite)
        html = render_webiq_live_demo_html(suite)
        self.assertIn("b2b-creative-ip-spdx-c2pa-escrow-sandbox", html)


if __name__ == "__main__":
    unittest.main()
