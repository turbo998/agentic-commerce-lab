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
