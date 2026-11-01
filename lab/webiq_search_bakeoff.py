"""Offline contract for the Web IQ vs web-search bake-off.

This module never opens a network connection. A missing credential stays
``not_measured``. Missing latency is never coerced to zero, and official list
prices are never copied into latency fields.
"""

from __future__ import annotations

import os
from typing import Mapping

SCHEMA = "webiq-search-bakeoff/v1"
VERIFIED_ON = "2026-11-01"

SEALED_QUERIES = (
    {
        "id": "return-window",
        "query": "What return window does the retailer's public return-policy page state?",
    },
    {
        "id": "price-evidence",
        "query": "Which public page states the current price for this SKU, and what URL can be cited?",
    },
    {
        "id": "recall-news",
        "query": "Is there a current public recall or safety notice that should stop replenishment?",
    },
)

ENV_KEYS = {
    "webiq": ("WEBIQ_API_KEY",),
    "brightdata": ("BRIGHTDATA_API_TOKEN", "BRIGHT_DATA_API_KEY"),
    "exa": ("EXA_API_KEY",),
    "tavily": ("TAVILY_API_KEY",),
    "parallel": ("PARALLEL_API_KEY",),
}

OFFICIAL_LIST_PRICE = {
    "webiq": {
        "label": "official_list_price",
        "source": "https://learn.microsoft.com/en-us/web-iq/resources/pricing",
        "verified_on": VERIFIED_ON,
        "effective": "2026-10-16",
        "per_1k_usd": {"web": 7.0, "browse": 1.0, "video": 7.0, "news": 7.0, "images": 7.0},
        "note": "Re-fetched 2026-11-01. Prices take effect 2026-10-16. Auto is not charged while in beta. Browse is AppID-gated. Not called.",
    },
    "exa": {
        "label": "official_list_price",
        "source": "https://exa.ai/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_usd": {
            "search_lite_or_instant": 4.0,
            "search_auto_or_fast": 7.0,
            "contents": 1.0,
            "answer": 5.0,
            "monitors": 15.0,
            "deep_or_deep_lite": 12.0,
            "deep_reasoning": 15.0,
            "extra_results": 1.0,
        },
        "free_credit_usd": 10.0,
        "free_lite_searches_cap": 2500,
        "agent_fixed_effort_usd": {"minimal": 0.012, "low": 0.025, "medium": 0.10, "high": 0.50, "xhigh": 1.00},
        "parameter_source": "https://docs.exa.ai/reference/search",
        "include_domains_max": 1200,
        "exclude_domains_max": 1200,
        "note": "Fetched 2026-11-01. Free balance resets to $10 on the first of each month. Contents bills each content type separately. The 2026-11-02 search reference says domain filters replace a site: operator and cap each list at 1,200. Deep-search seconds are vendor-stated and are not stored as latency. Not called.",
    },
    "tavily": {
        "label": "official_list_price",
        "source": "https://docs.tavily.com/documentation/api-credits",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_credit": 0.008,
        "credits": {"basic_search": 1, "fast_search": 1, "ultra_fast_search": 1, "advanced_search": 2},
        "parameter_source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
        "max_results_default": 10,
        "max_results_max": 20,
        "chunks_per_source_max": 3,
        "plan_usd_per_credit": {"project": 0.0075, "bootstrap": 0.0067, "startup": 0.0058, "growth": 0.005},
        "plan_usd_per_month": {"project": 30.0, "bootstrap": 100.0, "startup": 220.0, "growth": 500.0},
        "research_credits": {"pro_min": 15, "pro_max": 250, "mini_min": 4, "mini_max": 110},
        "note": "Fetched 2026-11-01. The price-per-credit column is published on the docs page. The 2026-11-02 search reference says fast and ultra-fast also cost 1 credit. max_results is 0-20, default 10. chunks_per_source is 1-3. Failed extractions and failed map requests are not billed. Not called.",
    },
    "parallel": {
        "label": "official_list_price",
        "source": "https://docs.parallel.ai/getting-started/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_usd": {
            "search_turbo_or_fast": 1.0,
            "search_basic_or_advanced": 5.0,
            "additional_results": 1.0,
            "extract": 1.0,
            "decisions_fast": 1.0,
            "task_lite": 5.0,
            "task_ultra8x": 2400.0,
            "responses_medium": 50.0,
        },
        "vendor_stated_timing": "200 ms-3 s",
        "parameter_source": "https://docs.parallel.ai/api-reference/search/search",
        "eu_base_url": "https://eu.parallel.ai",
        "eu_search_modes": ["basic"],
        "note": "Fetched 2026-11-01. Search base includes 10 results. Task charges successful runs only, per run not per field. The 2026-11-02 search reference says the EU base URL supports only basic mode. Image Search documents advanced as its own default. Page timing is vendor-stated, not a measurement. Not called.",
    },
    "brightdata": {
        "label": "official_list_price",
        "source": "https://brightdata.com/pricing/serp",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_1k_successful": 1.5,
        "scale_usd_per_month": 499,
        "scale_included_requests": 380000,
        "scale_additional_usd_per_1k": 1.3,
        "free_requests_per_month": 5000,
        "parameter_source": "https://docs.brightdata.com/products/serp-api/introduction.md",
        "request_endpoint": "POST https://api.brightdata.com/request",
        "note": "Page says displayed prices can be local-currency estimates and USD is binding. This row is SERP, not Web Unlocker. The 2026-11-02 introduction says pay only for successful delivery. Its under-1-second sentence is vendor-stated and is not stored.",
    },
    "brightdata_unlocker": {
        "label": "official_list_price",
        "source": "https://brightdata.com/pricing/web-unlocker",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_1k_successful": 1.5,
        "scale_usd_per_month": 499,
        "scale_included_requests": 383000,
        "scale_additional_usd_per_1k": 1.3,
        "free_requests_per_month": 5000,
        "note": "Unlocker Scale includes 383,000 requests. Do not copy SERP's 380,000 onto this row.",
    },
    "brightdata_browser": {
        "label": "official_list_price",
        "source": "https://brightdata.com/pricing/scraping-browser",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_gb": 8.0,
        "scale_usd_per_month": 499,
        "scale_included_gb": 71,
        "note": "Scale overage per GB was not in the static page. Not a request price.",
    },
    "brightdata_scraper": {
        "label": "official_list_price",
        "source": "https://brightdata.com/pricing/web-scraper",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_1k_records": 1.5,
        "scale_usd_per_month": 499,
        "scale_included_records": 384000,
        "scale_additional_usd_per_1k": 1.3,
        "note": "384,000 included records. Not SERP 380,000 or Unlocker 383,000.",
    },
    "perplexity_search": {
        "label": "official_list_price",
        "source": "https://docs.perplexity.ai/docs/getting-started/pricing.md",
        "verified_on": VERIFIED_ON,
        "per_1k_successful_requests_usd": {"search": 5.0, "search_fast": 1.0},
        "agent_tool_usd_per_invocation": {
            "web_search": 0.0025,
            "web_search_fast": 0.001,
            "image_search_successful": 0.0025,
            "fetch_url": 0.0005,
            "people_search": 0.005,
            "finance_search": 0.005,
        },
        "sandbox_usd_per_session": 0.03,
        "parameter_source": "https://docs.perplexity.ai/docs/search/overview",
        "search_endpoint": "POST https://api.perplexity.ai/search",
        "max_queries_per_request": 5,
        "web_max_results": 20,
        "web_max_results_default": 10,
        "people_max_results": 50,
        "max_tokens_min": 1,
        "max_tokens_max": 1000000,
        "domain_filter_max": 20,
        "language_filter_max": 20,
        "search_type_default": "web",
        "note": "One POST /search with up to five queries is one billing unit, but the 2026-11-02 overview says it uses one rate-limit unit per query. A successful empty result is billed. Token caps change the payload, not the Search API price. People search max_results is 50. Agent tool fees are separate. Not called.",
    },
    "google_grounding": {
        "label": "official_list_price",
        "source": "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing",
        "verified_on": VERIFIED_ON,
        "free_grounding_queries_per_month": 5000,
        "per_1k_grounding_queries_usd": 14.0,
        "note": "One prompt can create more than one billable query. Not a raw SERP price. Not called.",
    },
    "you_com": {
        "label": "official_list_price",
        "source": "https://you.com/pricing",
        "verified_on": VERIFIED_ON,
        "web_search_standard_per_1k_calls_usd": 5.0,
        "contents_per_1k_pages_usd": 1.0,
        "free_mcp_queries_per_day": 100,
        "free_credit_usd": 10.0,
        "free_credit_searches": 2000,
        "research_per_1k_calls_usd": {
            "lite": 12.0,
            "standard": 50.0,
            "deep": 100.0,
            "exhaustive": 450.0,
            "frontier": 1200.0,
        },
        "finance_research_per_1k_calls_usd": {"deep": 110.0, "exhaustive": 500.0},
        "parameter_source": "https://you.com/docs/api-reference/search/v1-search",
        "search_endpoint": "POST https://ydc-index.io/v1/search",
        "count_default": 10,
        "count_min": 1,
        "count_max": 100,
        "highlights_count_max": 50,
        "offset_max": 9,
        "include_domains_max": 500,
        "exclude_domains_max": 5000,
        "boost_domains_max": 500,
        "note": "Fetched from the pricing page. One Web Search call is one unit whether it returns 1 or 100 results. The 2026-11-02 search reference caps highlights at 50 and returns 422 above that. include_domains and exclude_domains cannot be combined. Contents is billed per page returned. Card latency is vendor-stated and is not a measurement. Not called.",
    },
    "linkup": {
        "label": "official_list_price",
        "source": "https://docs.linkup.so/pages/documentation/platform/pricing",
        "verified_on": VERIFIED_ON,
        "search_usd": {
            "flash_fast_standard_search_results": 0.005,
            "flash_fast_standard_sourced_or_structured": 0.006,
            "deep_search_results": 0.05,
            "deep_sourced_or_structured": 0.055,
        },
        "fetch_standard_no_js_usd": 0.001,
        "research_usd": {"S": 0.25, "M": 0.50, "L": 1.50, "XL": 2.50},
        "professional_monthly_topup_usd": 20.0,
        "x402_minimum_usd_per_request": 0.01,
        "parameter_source": "https://docs.linkup.so/pages/documentation/get-started/quickstart",
        "search_endpoint": "https://api.linkup.so/v1/search",
        "note": "Failed requests are not billed. sourcedAnswer is model-written. Extract is closed beta. The 2026-11-02 quickstart shows depth and outputType on this endpoint. Not called.",
    },
    "firecrawl": {
        "label": "official_list_price",
        "source": "https://www.firecrawl.dev/pricing.md",
        "verified_on": VERIFIED_ON,
        "monthly_usd": {"free": 0.0, "hobby": 19.0, "standard": 99.0, "growth": 399.0, "scale": 749.0},
        "annual_equivalent_monthly_usd": {"hobby": 16.0, "standard": 83.0, "growth": 333.0, "scale": 599.0},
        "monthly_credits": {"free": 1000, "hobby": 5000, "standard": 100000, "growth": 500000, "scale": 1000000},
        "search_credits_per_10_results": 2,
        "scrape_credits_per_page": 1,
        "parameter_source": "https://docs.firecrawl.dev/api-reference/endpoint/search.md",
        "country_default": "US",
        "search_categories": ["research", "pdf", "developer", "gov"],
        "note": "Do not divide a plan into a per-call list price. pricing.md says Interact is 2 credits per browser minute; the billing page says 2-7, with prompt sessions at 7. Both stand. The 2026-11-02 search reference says highlights are on by default and the research category changes on 2026-11-16. gov cannot be combined with other categories. Not called.",
    },
    "serpapi": {
        "label": "official_list_price",
        "source": "https://serpapi.com/pricing",
        "verified_on": VERIFIED_ON,
        "plans_usd_per_month": {
            "free": 0.0,
            "starter": 25.0,
            "developer": 75.0,
            "production": 150.0,
            "cloud_1m": 3750.0,
        },
        "plan_searches_per_month": {
            "free": 250,
            "starter": 1000,
            "developer": 5000,
            "production": 15000,
            "cloud_1m": 1000000,
        },
        "note": "Monthly plans only. The page continues past Cloud 1M. Do not divide into a unit price. Not called.",
    },
    "google_custom_search": {
        "label": "official_list_price",
        "source": "https://developers.google.com/custom-search/v1/overview",
        "verified_on": VERIFIED_ON,
        "free_queries_per_day": 100,
        "per_1k_queries_usd": 5.0,
        "daily_paid_cap_queries": 10000,
        "discontinued_on": "2027-01-01",
        "note": "Existing customers only. Not available for new customers. JSON web or image results. Not called.",
    },
    "anthropic_web_search": {
        "label": "official_list_price",
        "source": "https://platform.claude.com/docs/en/about-claude/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_searches_usd": 10.0,
        "web_fetch_extra_usd": 0.0,
        "note": "Claude API price, plus token costs. Each search is one use regardless of result count. Errors are not billed. Web fetch has no extra charge beyond tokens. Microsoft Foundry supports only web_search_20250305, without dynamic filtering. Not called.",
    },
    "openai_web_search": {
        "label": "official_list_price",
        "source": "https://developers.openai.com/api/docs/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_calls_usd": {
            "web_search": 10.0,
            "image_web_search": 10.0,
            "preview_reasoning": 10.0,
            "preview_non_reasoning": 25.0,
        },
        "mini_search_content_input_tokens": 8000,
        "note": "Fetched from pricing.md. Search content tokens are extra at model rates, except preview on non-reasoning models, where those tokens are free. gpt-4o-mini and gpt-4.1-mini non-preview bill search content as a fixed 8,000 input tokens. This is a cited model answer, not a raw passage. Not called.",
    },
    "searchapi": {
        "label": "official_list_price",
        "source": "https://www.searchapi.io/pricing",
        "verified_on": VERIFIED_ON,
        "free_requests": 100,
        "published_usd_per_1k": {
            "developer": 4.0,
            "production": 3.0,
            "bigdata": 2.5,
            "scale": 2.0,
            "octo_500k": 1.8,
            "octo_1m": 1.5,
            "octo_2m": 1.4,
            "octo_5m": 1.0,
        },
        "plans_usd_per_month": {
            "developer": 40.0,
            "production": 100.0,
            "bigdata": 250.0,
            "scale": 500.0,
            "octo_500k": 900.0,
            "octo_1m": 1500.0,
            "octo_2m": 2800.0,
            "octo_5m": 5000.0,
        },
        "plan_searches": {
            "developer": 10000,
            "production": 35000,
            "bigdata": 100000,
            "scale": 250000,
            "octo_500k": 500000,
            "octo_1m": 1000000,
            "octo_2m": 2000000,
            "octo_5m": 5000000,
        },
        "note": "The per-1k figures are printed on the plan cards, not divided here. Only HTTP 200 searches are billed. At most 20 percent of plan credits each hour. The 99.9 percent SLA is not a latency measurement. Not called.",
    },
    "dataforseo_google_organic": {
        "label": "official_list_price",
        "source": "https://dataforseo.com/pricing/google-serp/google-organic-serp-api",
        "verified_on": VERIFIED_ON,
        "per_serp_usd": {"standard": 0.0006, "priority": 0.0012, "live": 0.002},
        "per_1k_serp_usd": {"standard": 0.60, "priority": 1.20, "live": 2.00},
        "note": "One SERP is up to 10 organic results. The page also prints the per-1k rates. Turnaround sentences are vendor-stated averages, not a measurement. Each search operator multiplies the base by 5. The $50 minimum top-up is on https://dataforseo.com/pricing, not a monthly plan. Not called.",
    },
    "scrapingbee": {
        "label": "official_list_price",
        "source": "https://www.scrapingbee.com/pricing/",
        "verified_on": VERIFIED_ON,
        "free_credits": 1000,
        "plans_usd_per_month": {
            "hobby": 19.0,
            "freelance": 49.0,
            "startup": 99.0,
            "business": 249.0,
            "business_plus": 599.0,
        },
        "plan_credits": {
            "hobby": 75000,
            "freelance": 250000,
            "startup": 1000000,
            "business": 3000000,
            "business_plus": 8000000,
        },
        "credit_source": "https://help.scrapingbee.com/en/article/credit-system-explained-1h2ackp/",
        "google_search_credits": {"light": 10, "normal": 15},
        "fast_search_credits": 10,
        "agentic_search_credits": 3750,
        "html_google_url_credits": {"classic_or_premium": 15, "stealth": 75},
        "note": "Prices exclude VAT. Enterprise cards continue from $999 for 14 million credits to $5,799 for 120 million. Credit costs were fetched 2026-11-02 from the help article updated 2026-08-07. Do not divide a plan into a per-call dollar price. Not called.",
    },
    "kagi": {
        "label": "official_list_price",
        "source": "https://kagi.com/api/pricing",
        "verified_on": VERIFIED_ON,
        "search_per_1k_requests_usd": 12.0,
        "extract_per_1k_pages_usd": 4.0,
        "extract_urls_per_request_max": 10,
        "invoice_threshold_usd": 100.0,
        "search_endpoint": "POST https://kagi.com/api/v1/search",
        "mcp_url": "https://mcp.kagi.com/mcp",
        "note": "Fetched 2026-11-02. Search covers web, images, news, videos, and podcasts. Invoices every 30 days or at $100. Enterprise is quote-only. The docs page did not print numeric query limits. Not called.",
    },
    "zyte": {
        "label": "official_list_price",
        "source": "https://www.zyte.com/pricing/",
        "verified_on": VERIFIED_ON,
        "payg_http_per_1k_usd": {"simple": 0.13, "easy": 0.23, "moderate": 0.44, "complex": 0.70, "advanced": 1.27},
        "payg_browser_per_1k_usd": {"simple": 1.01, "easy": 2.01, "moderate": 4.02, "complex": 8.04, "advanced": 16.08},
        "commitment_500_http_simple_per_1k_usd": 0.06,
        "free_credit_usd": 5.0,
        "standard_rpm": 3000,
        "note": "The headline from-$0.06 is the $500-commitment HTTP simple floor, not a flat rate. Tier depends on the target site. Docs say only successful responses are billed. PAYG spending limit is $100/month. Not called.",
    },
    "browserbase": {
        "label": "official_list_price",
        "source": "https://www.browserbase.com/pricing",
        "verified_on": VERIFIED_ON,
        "plans_usd_per_month": {"free": 0.0, "developer": 20.0, "startup": 99.0},
        "included_search_calls": {"free": 1000, "developer": 1000, "startup": 1000},
        "default_search_overage_usd_per_1k": 5.0,
        "search_options_usd_per_1k": {
            "parallel_fast": 1.0,
            "parallel_advanced": 5.0,
            "exa_fast": 7.0,
            "exa_deep": 12.0,
        },
        "note": "Fetched 2026-11-02. Developer and Startup print these search options after 1,000 included calls. They are Browserbase pass-through rates, not a replacement for Parallel or Exa list prices. Search RPS is 2 per project on the listed plans. Not called.",
    },
    "spider": {
        "label": "official_list_price",
        "source": "https://spider.cloud/pricing/",
        "verified_on": VERIFIED_ON,
        "bandwidth_usd_per_gb": 1.0,
        "compute_usd_per_cpu_minute": 0.0001,
        "failed_request_usd": 0.0,
        "unlimited_concurrency_floor_usd_per_month": 40.0,
        "note": "PAYG is bandwidth plus compute, not a per-search list price. Failed requests cost $0. Unlimited bills concurrency and does not include Google search. Zero data retention is 2.5x. Not called.",
    },
    "scale_serp": {
        "label": "official_list_price",
        "source": "https://trajectdata.com/serp/scale-serp-api/pricing/",
        "verified_on": VERIFIED_ON,
        "billing_view": "annual",
        "annual_plans_usd_per_month": {
            "searches_1000": 23.0,
            "searches_10000": 66.0,
            "searches_50000": 199.0,
            "searches_250000": 599.0,
            "searches_1000000": 1699.0,
            "searches_5000000": 4999.0,
        },
        "overage_usd_per_search": {
            "searches_1000": 0.038,
            "searches_10000": 0.0118,
            "searches_50000": 0.00796,
            "searches_250000": 0.004792,
            "searches_1000000": 0.003398,
            "searches_5000000": 0.001999,
        },
        "free_searches_per_month": 125,
        "note": "scaleserp.com/pricing redirected here. These are the annual-billed monthly figures on the page. The monthly toggle was not in this fetch. Only successful Search API calls count. The page says Traject Data joins ScraperAPI. Not called.",
    },
    "oxylabs": {
        "label": "not_verified",
        "source": "https://oxylabs.io/products/serp-scraper-api/pricing",
        "verified_on": VERIFIED_ON,
        "note": "The pricing URL failed at TLS on 2026-11-02. Do not copy a third-party extract as a list price.",
    },
    "jina_reader": {
        "label": "not_verified",
        "source": "https://jina.ai/contact-sales/",
        "verified_on": VERIFIED_ON,
        "reader_rpm_without_key": 20,
        "reader_rpm_free_or_paid": 500,
        "reader_rpm_premium": 5000,
        "search_rpm_free_or_paid": 100,
        "search_rpm_premium": 1000,
        "search_token_floor": 10000,
        "note": "Rate-limit table was visible. Dollar top-up was not on the fetched page, so the price stays unverified. Vendor-stated 7.9s and 2.5s are not stored. Not called.",
    },
    "brave_search": {
        "label": "not_verified",
        "source": "https://api-dashboard.search.brave.com/api-reference/ai/llm_context/get",
        "verified_on": VERIFIED_ON,
        "llm_context_path": "GET /v1/llm/context",
        "query_max_characters": 600,
        "query_max_words": 75,
        "count_default": 20,
        "count_max": 50,
        "tokens_default": 8192,
        "tokens_min": 1024,
        "tokens_max": 32768,
        "tokens_per_url_default": 4096,
        "tokens_per_url_max": 8192,
        "urls_max": 50,
        "goggles_max": 3,
        "context_threshold_modes": ["disabled", "strict", "lenient", "balanced"],
        "freshness": ["pd", "pw", "pm", "py", "YYYY-MM-DDtoYYYY-MM-DD"],
        "note": "Fetched 2026-11-02 from the LLM Context reference. Price is still not_verified: the pricing dashboard was a shell and this reference has no unit price. AIMultiple milliseconds on the marketing page are not stored. Not called.",
    },
    "serper": {
        "label": "not_verified",
        "source": "https://serper.dev/pricing",
        "verified_on": VERIFIED_ON,
        "note": "Pricing URL returned 404. Homepage fetch did not show a unit price.",
    },
    "bing_grounding": {
        "label": "official_list_price",
        "source": "https://www.microsoft.com/en-us/bing/apis",
        "verified_on": VERIFIED_ON,
        "per_1k_transactions_usd": 14.0,
        "custom_search_per_1k_transactions_usd": 14.0,
        "max_transactions_per_second": 150,
        "max_transactions_per_day": 1000000,
        "note": "Seen on the product page, not copied from Google. The Learn how-to page does not list this price and links here. Outputs are not directly accessible. Not Web IQ. Not called.",
    },
}

# Architecture guidance only. These routes are not a measured winner.
SCENARIO_ROUTES = {
    "price_evidence": {
        "label": "architecture_guidance",
        "primary": "webiq",
        "calls": ("POST /v3/search/web contentFormat=passage", "POST /v3/browse on the cited URL"),
        "do_not": "Do not change an authorized amount from a SERP snippet.",
    },
    "return_policy": {
        "label": "architecture_guidance",
        "primary": "webiq",
        "calls": ("POST /v3/browse passage plus non-blank query",),
        "do_not": "Do not buy a SERP call for one known policy URL.",
    },
    "recall_news": {
        "label": "architecture_guidance",
        "primary": "webiq",
        "calls": ("POST /v3/search/news",),
        "do_not": "Web has no date filter. Do not treat an old web passage as no recall today.",
    },
    "serp_monitor": {
        "label": "architecture_guidance",
        "primary": "brightdata",
        "calls": ("SERP API with gl and hl on the engine URL",),
        "do_not": "Do not treat a result page as the publisher page.",
    },
    "blocked_html": {
        "label": "architecture_guidance",
        "primary": "brightdata_unlocker",
        "calls": ("Web Unlocker for raw HTML", "or Exa /contents, Tavily Extract, Parallel Extract for page text"),
        "do_not": "Unlocker is not a click-through checkout browser.",
    },
    "browser_interaction": {
        "label": "architecture_guidance",
        "primary": "brightdata",
        "calls": ("Browser API",),
        "do_not": "Browse renderDynamicPages only renders when liveCrawl is fallback. It does not submit forms.",
    },
}


def _present(env: Mapping[str, str], names: tuple[str, ...]) -> bool:
    return any(str(env.get(name) or "").strip() for name in names)


def provider_row(name: str, env: Mapping[str, str]) -> dict:
    present = _present(env, ENV_KEYS[name])
    row = {
        "provider": name,
        "credential": "present" if present else "absent",
        "call": "not_called",
        "latency": "not_measured",
        "success": "not_measured",
        "citation_check": "not_measured",
    }
    return row


def summarize(env: Mapping[str, str] | None = None) -> dict:
    source = os.environ if env is None else env
    report = {
        "schema": SCHEMA,
        "verified_on": VERIFIED_ON,
        "measured": False,
        "queries": [dict(item) for item in SEALED_QUERIES],
        "providers": [provider_row(name, source) for name in ENV_KEYS],
        "official_list_price": OFFICIAL_LIST_PRICE,
        "scenario_routes": SCENARIO_ROUTES,
        "seven_card": "withheld_until_measured_latency_exists",
    }
    assert_not_fabricated(report)
    return report


def assert_not_fabricated(report: dict) -> None:
    if report.get("measured") is not False:
        raise AssertionError("this offline contract cannot claim a live measurement")
    for row in report["providers"]:
        if "latency_ms" in row or row.get("latency") in (0, 0.0):
            raise AssertionError("missing latency must not be coerced to zero")
        if row.get("success") in (0, 0.0, "0/0"):
            raise AssertionError("missing success must not be coerced to zero")
    for price in report["official_list_price"].values():
        if price.get("label") not in ("official_list_price", "not_verified"):
            raise AssertionError("list price must stay labeled")
        if price.get("label") == "not_verified" and any(
            key.endswith("_usd") or key.startswith("per_1k") for key in price
        ):
            raise AssertionError("an unverified row must not carry a unit price")
        if "latency_ms" in price:
            raise AssertionError("list price must not be stored as latency")
    for route in report.get("scenario_routes", {}).values():
        if route.get("label") != "architecture_guidance":
            raise AssertionError("scenario route must stay guidance, not a measured winner")
        if "latency_ms" in route or route.get("latency") in (0, 0.0):
            raise AssertionError("scenario route must not invent latency")


def grounding_architecture_comparison() -> list[dict]:
    """Compare caller-visible evidence visibility and anti-injection boundaries across grounding products."""
    return [
        {
            "provider": "webiq",
            "caller_receives_raw_passages": True,
            "pre_llm_deterministic_sanitization": True,
            "browse_passage_default_3000_chars": True,
            "dual_format_retry_after": "duration_seconds ('60s') + iso8601_utc_timestamp ('2026-10-30T01:01:00Z')",
            "source_url": "https://learn.microsoft.com/en-us/web-iq/reference/browse",
            "verified_on": VERIFIED_ON,
        },
        {
            "provider": "foundry_bing_grounding",
            "caller_receives_raw_passages": False,
            "pre_llm_deterministic_sanitization": False,
            "browse_passage_default_3000_chars": False,
            "dual_format_retry_after": "managed_inside_foundry_service_boundary",
            "source_url": "https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-overview",
            "verified_on": VERIFIED_ON,
        },
    ]

