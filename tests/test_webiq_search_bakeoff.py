import unittest

from lab.webiq_search_bakeoff import (
    assert_not_fabricated,
    grounding_architecture_comparison,
    summarize,
)


class WebIQSearchBakeoffTests(unittest.TestCase):
    def test_missing_credentials_stay_not_measured(self):
        report = summarize({})
        self.assertFalse(report["measured"])
        self.assertEqual(len(report["queries"]), 3)
        self.assertEqual(
            [row["provider"] for row in report["providers"]],
            ["webiq", "brightdata", "exa", "tavily", "parallel"],
        )
        for row in report["providers"]:
            self.assertEqual(row["credential"], "absent")
            self.assertEqual(row["latency"], "not_measured")
            self.assertNotIn("latency_ms", row)
        assert_not_fabricated(report)

    def test_present_key_is_not_called_and_not_scored(self):
        report = summarize({"WEBIQ_API_KEY": "present-but-not-used", "EXA_API_KEY": "x"})
        by_name = {row["provider"]: row for row in report["providers"]}
        self.assertEqual(by_name["webiq"]["credential"], "present")
        self.assertEqual(by_name["exa"]["credential"], "present")
        self.assertEqual(by_name["webiq"]["call"], "not_called")
        self.assertEqual(by_name["webiq"]["latency"], "not_measured")
        self.assertEqual(by_name["brightdata"]["credential"], "absent")
        self.assertNotIn("latency_ms", report["official_list_price"]["webiq"])
        self.assertEqual(report["official_list_price"]["webiq"]["per_1k_usd"]["web"], 7.0)
        self.assertEqual(report["official_list_price"]["brightdata"]["payg_usd_per_1k_successful"], 1.5)
        self.assertEqual(report["seven_card"], "withheld_until_measured_latency_exists")

    def test_blank_key_is_absent(self):
        report = summarize({"WEBIQ_API_KEY": "   "})
        self.assertEqual(report["providers"][0]["credential"], "absent")

    def test_grounding_architecture_comparison_distinguishes_caller_visible_passages(self):
        arch = grounding_architecture_comparison()
        by_provider = {row["provider"]: row for row in arch}
        self.assertTrue(by_provider["webiq"]["caller_receives_raw_passages"])
        self.assertTrue(by_provider["webiq"]["pre_llm_deterministic_sanitization"])
        self.assertFalse(by_provider["foundry_bing_grounding"]["caller_receives_raw_passages"])
        self.assertFalse(by_provider["foundry_bing_grounding"]["pre_llm_deterministic_sanitization"])

    def test_scenario_routes_are_guidance_not_latency(self):
        report = summarize({})
        routes = report["scenario_routes"]
        self.assertEqual(routes["price_evidence"]["primary"], "webiq")
        self.assertEqual(routes["recall_news"]["calls"], ("POST /v3/search/news",))
        self.assertEqual(routes["serp_monitor"]["primary"], "brightdata")
        self.assertEqual(routes["blocked_html"]["primary"], "brightdata_unlocker")
        unlocker = report["official_list_price"]["brightdata_unlocker"]
        serp = report["official_list_price"]["brightdata"]
        self.assertEqual(unlocker["scale_included_requests"], 383000)
        self.assertEqual(serp["scale_included_requests"], 380000)
        self.assertNotEqual(unlocker["scale_included_requests"], serp["scale_included_requests"])
        self.assertEqual(report["official_list_price"]["brightdata_scraper"]["scale_included_records"], 384000)
        self.assertEqual(report["official_list_price"]["brightdata_browser"]["payg_usd_per_gb"], 8.0)
        self.assertEqual(report["official_list_price"]["perplexity_search"]["per_1k_successful_requests_usd"]["search_fast"], 1.0)
        self.assertEqual(report["official_list_price"]["google_grounding"]["per_1k_grounding_queries_usd"], 14.0)
        bing = report["official_list_price"]["bing_grounding"]
        self.assertEqual(bing["label"], "official_list_price")
        self.assertEqual(bing["per_1k_transactions_usd"], 14.0)
        self.assertEqual(bing["source"], "https://www.microsoft.com/en-us/bing/apis")
        self.assertNotIn("latency_ms", bing)
        you = report["official_list_price"]["you_com"]
        self.assertEqual(you["label"], "official_list_price")
        self.assertEqual(you["web_search_standard_per_1k_calls_usd"], 5.0)
        self.assertEqual(you["contents_per_1k_pages_usd"], 1.0)
        self.assertEqual(you["research_per_1k_calls_usd"]["frontier"], 1200.0)
        self.assertNotIn("latency_ms", you)
        linkup = report["official_list_price"]["linkup"]
        self.assertEqual(linkup["search_usd"]["deep_search_results"], 0.05)
        self.assertEqual(linkup["research_usd"]["XL"], 2.50)
        firecrawl = report["official_list_price"]["firecrawl"]
        self.assertEqual(firecrawl["monthly_usd"]["scale"], 749.0)
        self.assertEqual(firecrawl["search_credits_per_10_results"], 2)
        self.assertNotIn("per_call_usd", firecrawl)
        self.assertEqual(report["official_list_price"]["serpapi"]["plans_usd_per_month"]["starter"], 25.0)
        self.assertEqual(report["official_list_price"]["brave_search"]["label"], "not_verified")
        self.assertEqual(report["official_list_price"]["serper"]["label"], "not_verified")
        self.assertEqual(report["official_list_price"]["jina_reader"]["label"], "not_verified")
        self.assertEqual(report["official_list_price"]["jina_reader"]["search_token_floor"], 10000)
        cse = report["official_list_price"]["google_custom_search"]
        self.assertEqual(cse["per_1k_queries_usd"], 5.0)
        self.assertEqual(cse["discontinued_on"], "2027-01-01")
        self.assertEqual(report["official_list_price"]["anthropic_web_search"]["per_1k_searches_usd"], 10.0)
        self.assertEqual(
            report["official_list_price"]["perplexity_search"]["agent_tool_usd_per_invocation"]["web_search"],
            0.0025,
        )
        openai = report["official_list_price"]["openai_web_search"]
        self.assertEqual(openai["per_1k_calls_usd"]["web_search"], 10.0)
        self.assertEqual(openai["per_1k_calls_usd"]["preview_non_reasoning"], 25.0)
        self.assertNotIn("latency_ms", openai)
        self.assertEqual(report["official_list_price"]["searchapi"]["published_usd_per_1k"]["developer"], 4.0)
        self.assertEqual(report["official_list_price"]["dataforseo_google_organic"]["per_1k_serp_usd"]["live"], 2.0)
        self.assertEqual(report["official_list_price"]["scrapingbee"]["plans_usd_per_month"]["startup"], 99.0)
        self.assertEqual(report["official_list_price"]["scrapingbee"]["google_search_credits"]["normal"], 15)
        self.assertEqual(report["official_list_price"]["scrapingbee"]["agentic_search_credits"], 3750)
        self.assertNotIn("per_call_usd", report["official_list_price"]["scrapingbee"])
        self.assertEqual(report["official_list_price"]["kagi"]["search_per_1k_requests_usd"], 12.0)
        self.assertEqual(report["official_list_price"]["kagi"]["extract_per_1k_pages_usd"], 4.0)
        self.assertEqual(report["official_list_price"]["zyte"]["payg_http_per_1k_usd"]["simple"], 0.13)
        self.assertNotEqual(report["official_list_price"]["zyte"]["payg_http_per_1k_usd"]["advanced"], 0.06)
        self.assertEqual(report["official_list_price"]["oxylabs"]["label"], "not_verified")
        brave = report["official_list_price"]["brave_search"]
        self.assertEqual(brave["label"], "not_verified")
        self.assertEqual(brave["tokens_default"], 8192)
        self.assertEqual(brave["tokens_max"], 32768)
        self.assertNotIn("per_1k_usd", brave)
        self.assertEqual(report["official_list_price"]["browserbase"]["default_search_overage_usd_per_1k"], 5.0)
        self.assertEqual(report["official_list_price"]["browserbase"]["search_options_usd_per_1k"]["exa_deep"], 12.0)
        self.assertEqual(report["official_list_price"]["spider"]["bandwidth_usd_per_gb"], 1.0)
        self.assertNotIn("per_search_usd", report["official_list_price"]["spider"])
        self.assertEqual(report["official_list_price"]["scale_serp"]["billing_view"], "annual")
        self.assertEqual(report["official_list_price"]["scale_serp"]["overage_usd_per_search"]["searches_10000"], 0.0118)
        prices = report["official_list_price"]
        self.assertEqual(prices["webiq"]["per_1k_usd"]["browse"], 1.0)
        self.assertEqual(prices["exa"]["per_1k_usd"]["deep_reasoning"], 15.0)
        self.assertEqual(prices["exa"]["agent_fixed_effort_usd"]["xhigh"], 1.00)
        self.assertEqual(prices["tavily"]["plan_usd_per_credit"]["growth"], 0.005)
        self.assertEqual(prices["tavily"]["credits"]["ultra_fast_search"], 1)
        self.assertEqual(prices["tavily"]["max_results_max"], 20)
        self.assertEqual(prices["exa"]["include_domains_max"], 1200)
        self.assertEqual(prices["parallel"]["eu_search_modes"], ["basic"])
        self.assertEqual(prices["parallel"]["per_1k_usd"]["task_ultra8x"], 2400.0)
        self.assertNotIn("latency_ms", prices["exa"])
        self.assertNotIn("latency_ms", prices["parallel"])
        for route in routes.values():
            self.assertEqual(route["label"], "architecture_guidance")
            self.assertNotIn("latency_ms", route)


if __name__ == "__main__":
    unittest.main()
