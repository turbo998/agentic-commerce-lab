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
        "note": "Page says displayed prices can be local-currency estimates and USD is binding.",
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
