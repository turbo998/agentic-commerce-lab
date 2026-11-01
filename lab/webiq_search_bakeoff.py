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
        "note": "Auto is not charged while in beta. Browse is AppID-gated.",
    },
    "exa": {
        "label": "official_list_price",
        "source": "https://exa.ai/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_usd": {"search_lite_or_instant": 4.0, "search_auto_or_fast": 7.0, "contents": 1.0},
        "note": "Base price includes up to 10 results. Extra results are $1 per 1,000.",
    },
    "tavily": {
        "label": "official_list_price",
        "source": "https://docs.tavily.com/documentation/api-credits",
        "verified_on": VERIFIED_ON,
        "payg_usd_per_credit": 0.008,
        "credits": {"basic_search": 1, "advanced_search": 2},
        "note": "Free tier is 1,000 credits per month.",
    },
    "parallel": {
        "label": "official_list_price",
        "source": "https://docs.parallel.ai/getting-started/pricing",
        "verified_on": VERIFIED_ON,
        "per_1k_usd": {"search_turbo_or_fast": 1.0, "search_basic_or_advanced": 5.0, "extract": 1.0},
        "vendor_stated_timing": "200 ms-3 s",
        "note": "Vendor-stated timing is not a measurement from this harness.",
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
        "note": "Page says displayed prices can be local-currency estimates and USD is binding. This row is SERP, not Web Unlocker.",
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
        "note": "One POST /search with up to five queries is one billing unit. Not called.",
    },
    "google_grounding": {
        "label": "official_list_price",
        "source": "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing",
        "verified_on": VERIFIED_ON,
        "free_grounding_queries_per_month": 5000,
        "per_1k_grounding_queries_usd": 14.0,
        "note": "One prompt can create more than one billable query. Not a raw SERP price. Not called.",
    },
    "bing_grounding": {
        "label": "official_list_price",
        "source": "https://learn.microsoft.com/en-us/azure/foundry-classic/agents/how-to/tools-classic/bing-grounding",
        "verified_on": VERIFIED_ON,
        "per_1k_transactions_usd": 14.0,
        "note": "Bing Search APIs retired 2025-08-11. This is not Web IQ. Not called.",
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
        if price.get("label") != "official_list_price":
            raise AssertionError("list price must stay labeled")
        if "latency_ms" in price:
            raise AssertionError("list price must not be stored as latency")
    for route in report.get("scenario_routes", {}).values():
        if route.get("label") != "architecture_guidance":
            raise AssertionError("scenario route must stay guidance, not a measured winner")
        if "latency_ms" in route or route.get("latency") in (0, 0.0):
            raise AssertionError("scenario route must not invent latency")
