"""Stage 58 protocol & benchmark guards.

Covers primary-source specifications and reference implementations from:
1. Universal Commerce Protocol (UCP):
   - PR #901: Purchase Options extension (`dev.ucp.shopping.purchase_options`),
     response-only `purchase_options[]` (`ucp_request: "omit"`), `selected_purchase_option_id`
     co-presence (`dependentRequired`), omission on `complete`, `purchase_option_changed`
     warning on stale selection fallback, deferred-trial zero-price prohibition,
     and frozen `{id, title}` `purchase_option` on Order lines.
   - PR #811: Per-seller `offers[]` attribution on catalog variants (`offers[].seller.domain`
     Merchant of Record bare hostname, `offers[].item_id` replacing `variant.id` at checkout,
     and `offers[].price` authoritative over display-only `variant.price`).
   - PR #933 & PR #831: Profile/JWKS/CIMD HTTP `304 Not Modified` conditional cache revalidation
     vs forbidden `301`/`302`/`303`/`307`/`308` redirects, and MCP tool-call schema `$defs/agent`
     replacing reserved `ucp_`-prefixed `$defs/ucp_agent` (`W007`).
2. Agentic Commerce Protocol (ACP):
   - PR #281 (SEP #280): Optional `url` (`format: uri`) on request-side checkout `Item`
     for deterministic storefront/brand disambiguation on cross-listed SKUs.
   - PR #256 & PR #241: Product Feed API agent-hosted server origin (`https://agent.example.com`),
     `minItems: 1` bounds on `UpsertProductsRequest.products` and `Product.variants`,
     and `UpsertProductsResponse` (`{id, accepted}`) schema bundle validation.
3. Google Agent Payments Protocol (AP2):
   - PR #363: Multi-hop `~~` delegation chain isolation in `MandateClient.present()`
     (redacting only the final hop while preserving earlier hops and computing `sd_hash`
     over the post-redaction hop).
   - PR #359: Mandatory `checkout_hash` derivation from the presented `checkout_jwt` in
     `CheckoutMandateChain.verify()` even when `expected_checkout_hash` is omitted.
   - PR #347: Atomic consume-once SQLite (`BEGIN IMMEDIATE`, `synchronous=FULL`) reservation
     for closed Payment Mandates and Checkout transaction IDs with legacy token-store
     check and fail-closed `replay_state_unavailable` / `mandate_already_used`.
4. Sierra tau2-bench:
   - PR #637: Six-language (`en`, `es`, `pt`, `hi`, `zh`, `ko`) `voice-v2-banking`
     (`banking_knowledge_97`, 582 calls) and `voice-v2-entity` (`intake_200`, 1,200 calls,
     240s call limit) benchmarks with per-cell `binding_revision` pins.
   - PR #639: Crossed Pass^3 `voice-v2-rcs-v3` whole-run seeds `(42, 401, 16319)`,
     read-only seed-42 `--regular-results` reuse, and `google-genai >= 2.26` check.
   - PR #620: Judged `voice-v2` submission package gate (`tau2 submit prepare/validate`)
     requiring zero missing/errored/unscored calls, complete judge verdicts across all
     applicable measures, and verified `benchmark-diagnostics.json` verdict fingerprints.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import re
from typing import Any
from urllib.parse import urlparse


FORBIDDEN_HTTP_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
BARE_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
TAU2_VOICE_V2_LANGUAGES = ("en", "es", "pt", "hi", "zh", "ko")
TAU2_RCS_V3_SEEDS = (42, 401, 16319)
TAU2_LEGACY_RCS_SEEDS = (9401, 9402, 9403)


def compute_sha256_b64url(text: str) -> str:
    """Return unpadded base64url-encoded SHA-256 digest of UTF-8 text."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


@dataclass(frozen=True)
class UcpPurchaseOptionsAndOffersGuardResult:
    allowed: bool
    decision_code: str
    resolved_purchase_option_id: str | None
    resolved_line_price_minor: int | None
    emitted_warnings: tuple[str, ...]
    order_purchase_option_snapshot: dict[str, str] | None
    resolved_mor_domain: str | None
    resolved_checkout_item_id: str | None


def verify_ucp_purchase_options_and_seller_offers_guard(
    *,
    operation: str,
    request_line_item: dict[str, Any],
    catalog_variant: dict[str, Any],
    response_line_item: dict[str, Any] | None = None,
    response_warnings: list[str] | tuple[str, ...] = (),
    order_line_item: dict[str, Any] | None = None,
    selected_offer_seller_domain: str | None = None,
    profile_http_status: int = 200,
    is_conditional_request: bool = False,
    profile_cache_max_age_sec: int = 300,
    mcp_tool_schema_defs: dict[str, Any] | None = None,
    mcp_ucp_agent_ref: str = "#/$defs/agent",
) -> UcpPurchaseOptionsAndOffersGuardResult:
    """Verify UCP PR #901, PR #811, PR #933, and PR #831 deterministic guards."""
    # 1. PR #933: HTTP 304 Not Modified vs forbidden 3xx redirects on profile/JWKS/CIMD
    if profile_http_status in FORBIDDEN_HTTP_REDIRECT_CODES:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_FORBIDDEN_HTTP_REDIRECT",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=None,
            resolved_checkout_item_id=None,
        )
    if profile_http_status == 304 and not is_conditional_request:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_UNSOLICITED_304_WITHOUT_CONDITIONAL_REQUEST",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=None,
            resolved_checkout_item_id=None,
        )
    if profile_cache_max_age_sec < 60:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_PROFILE_CACHE_TTL_BELOW_60S_FLOOR",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=None,
            resolved_checkout_item_id=None,
        )

    # 2. PR #831: MCP tool call schema $defs/agent vs reserved ucp_ prefix (W007)
    if mcp_tool_schema_defs is not None:
        for def_name in mcp_tool_schema_defs:
            if str(def_name).startswith("ucp_"):
                return UcpPurchaseOptionsAndOffersGuardResult(
                    allowed=False,
                    decision_code="UCP_SCHEMA_W007_RESERVED_UCP_PREFIX_IN_DEFS",
                    resolved_purchase_option_id=None,
                    resolved_line_price_minor=None,
                    emitted_warnings=(),
                    order_purchase_option_snapshot=None,
                    resolved_mor_domain=None,
                    resolved_checkout_item_id=None,
                )
        if mcp_ucp_agent_ref != "#/$defs/agent" or "agent" not in mcp_tool_schema_defs:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_MCP_AGENT_DEF_REF_INVALID",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=None,
                resolved_checkout_item_id=None,
            )

    # 3. PR #811: Per-seller offers[] attribution on catalog variants
    variant_id = str(catalog_variant.get("id") or "").strip()
    variant_price = catalog_variant.get("price")
    offers = catalog_variant.get("offers")
    resolved_mor_domain = str(catalog_variant.get("serving_business_domain") or "catalog.example.com").strip()
    resolved_checkout_item_id = variant_id
    authoritative_base_price = variant_price

    req_item = request_line_item.get("item") if isinstance(request_line_item.get("item"), dict) else {}
    req_item_id = str(req_item.get("id") or request_line_item.get("item_id") or "").strip()

    if offers is not None:
        if not isinstance(offers, list) or len(offers) < 1:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_VARIANT_OFFERS_EMPTY_OR_INVALID",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=None,
                resolved_checkout_item_id=None,
            )
        matched_offer: dict[str, Any] | None = None
        for offer in offers:
            if not isinstance(offer, dict):
                return UcpPurchaseOptionsAndOffersGuardResult(
                    allowed=False,
                    decision_code="UCP_OFFER_ENTRY_NOT_OBJECT",
                    resolved_purchase_option_id=None,
                    resolved_line_price_minor=None,
                    emitted_warnings=(),
                    order_purchase_option_snapshot=None,
                    resolved_mor_domain=None,
                    resolved_checkout_item_id=None,
                )
            seller = offer.get("seller")
            seller_domain = str(seller.get("domain") or "").strip() if isinstance(seller, dict) else ""
            offer_item_id = str(offer.get("item_id") or "").strip()
            offer_price = offer.get("price")
            if not seller_domain or not BARE_DOMAIN_RE.match(seller_domain):
                return UcpPurchaseOptionsAndOffersGuardResult(
                    allowed=False,
                    decision_code="UCP_OFFER_SELLER_DOMAIN_NOT_BARE_HOSTNAME",
                    resolved_purchase_option_id=None,
                    resolved_line_price_minor=None,
                    emitted_warnings=(),
                    order_purchase_option_snapshot=None,
                    resolved_mor_domain=None,
                    resolved_checkout_item_id=None,
                )
            if not offer_item_id or not isinstance(offer_price, int) or offer_price < 0:
                return UcpPurchaseOptionsAndOffersGuardResult(
                    allowed=False,
                    decision_code="UCP_OFFER_MISSING_ITEM_ID_OR_PRICE",
                    resolved_purchase_option_id=None,
                    resolved_line_price_minor=None,
                    emitted_warnings=(),
                    order_purchase_option_snapshot=None,
                    resolved_mor_domain=None,
                    resolved_checkout_item_id=None,
                )
            if selected_offer_seller_domain and seller_domain == selected_offer_seller_domain:
                matched_offer = offer
        if req_item_id == variant_id:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_MULTI_SELLER_VARIANT_ID_USED_AT_CHECKOUT",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=None,
                resolved_checkout_item_id=None,
            )
        if matched_offer is None:
            for offer in offers:
                if offer.get("item_id") == req_item_id:
                    matched_offer = offer
                    break
        if matched_offer is None:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_OFFER_SELECTION_UNRESOLVED",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=None,
                resolved_checkout_item_id=None,
            )
        resolved_mor_domain = str(matched_offer["seller"]["domain"])
        resolved_checkout_item_id = str(matched_offer["item_id"])
        authoritative_base_price = int(matched_offer["price"])
        if req_item_id != resolved_checkout_item_id:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_CHECKOUT_ITEM_ID_DOES_NOT_MATCH_SELLER_OFFER",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )

    # 4. PR #901: Purchase Options (`dev.ucp.shopping.purchase_options`)
    if "purchase_options" in request_line_item:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_PURCHASE_OPTIONS_RESPONSE_ONLY_FIELD_IN_REQUEST",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=resolved_mor_domain,
            resolved_checkout_item_id=resolved_checkout_item_id,
        )
    if operation == "complete" and "selected_purchase_option_id" in request_line_item:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_SELECTED_PURCHASE_OPTION_OMIT_ON_COMPLETE",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=resolved_mor_domain,
            resolved_checkout_item_id=resolved_checkout_item_id,
        )

    variant_options = catalog_variant.get("purchase_options")
    if variant_options is None:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=True,
            decision_code="UCP_STANDARD_VARIANT_AND_OFFER_VERIFIED",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=int(authoritative_base_price or 0),
            emitted_warnings=tuple(response_warnings),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=resolved_mor_domain,
            resolved_checkout_item_id=resolved_checkout_item_id,
        )

    if not isinstance(variant_options, list) or len(variant_options) < 1:
        return UcpPurchaseOptionsAndOffersGuardResult(
            allowed=False,
            decision_code="UCP_PURCHASE_OPTIONS_ARRAY_EMPTY",
            resolved_purchase_option_id=None,
            resolved_line_price_minor=None,
            emitted_warnings=(),
            order_purchase_option_snapshot=None,
            resolved_mor_domain=resolved_mor_domain,
            resolved_checkout_item_id=resolved_checkout_item_id,
        )

    options_by_id: dict[str, dict[str, Any]] = {}
    for idx, opt in enumerate(variant_options):
        if not isinstance(opt, dict):
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_PURCHASE_OPTION_NOT_OBJECT",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        opt_id = str(opt.get("id") or "").strip()
        opt_title = str(opt.get("title") or "").strip()
        opt_desc = str(opt.get("description") or "").strip()
        opt_price = opt.get("price")
        opt_list_price = opt.get("list_price")
        if not opt_id or not opt_title or not isinstance(opt_price, int) or opt_price < 0:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_PURCHASE_OPTION_MISSING_REQUIRED_FIELDS",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        if opt_desc and opt_desc.casefold() == opt_title.casefold():
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_PURCHASE_OPTION_DESCRIPTION_REPEATS_TITLE",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        if opt.get("is_deferred_payment_trial") and opt_price == 0:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_DEFERRED_TRIAL_MUST_NOT_USE_ZERO_OPTION_PRICE",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        if opt_list_price is not None and (not isinstance(opt_list_price, int) or opt_list_price <= opt_price):
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_PURCHASE_OPTION_LIST_PRICE_NOT_GREATER_THAN_PRICE",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        if idx == 0 and offers is None and variant_price is not None and opt_price != variant_price:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_DEFAULT_PURCHASE_OPTION_PRICE_MISMATCHES_VARIANT_PRICE",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=(),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        options_by_id[opt_id] = opt

    default_opt = variant_options[0]
    requested_opt_id = request_line_item.get("selected_purchase_option_id")
    warnings = list(response_warnings)
    if requested_opt_id is None:
        selected_opt = default_opt
    elif str(requested_opt_id) in options_by_id:
        selected_opt = options_by_id[str(requested_opt_id)]
    else:
        if "purchase_option_changed" not in warnings:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_STALE_PURCHASE_OPTION_SILENT_SUBSTITUTION_FORBIDDEN",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=tuple(warnings),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        selected_opt = default_opt

    if response_line_item is not None:
        has_resp_opts = "purchase_options" in response_line_item
        has_resp_sel = "selected_purchase_option_id" in response_line_item
        if has_resp_opts != has_resp_sel:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_LINE_ITEM_PURCHASE_OPTIONS_DEPENDENT_REQUIRED_VIOLATION",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=tuple(warnings),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        if has_resp_sel and response_line_item.get("selected_purchase_option_id") != selected_opt["id"]:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_RESPONSE_SELECTED_PURCHASE_OPTION_MISMATCH",
                resolved_purchase_option_id=None,
                resolved_line_price_minor=None,
                emitted_warnings=tuple(warnings),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )
        resp_item = response_line_item.get("item") if isinstance(response_line_item.get("item"), dict) else {}
        if "price" in resp_item and resp_item.get("price") != selected_opt["price"]:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_LINE_ITEM_PRICE_MISMATCHES_SELECTED_PURCHASE_OPTION",
                resolved_purchase_option_id=str(selected_opt["id"]),
                resolved_line_price_minor=int(selected_opt["price"]),
                emitted_warnings=tuple(warnings),
                order_purchase_option_snapshot=None,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )

    order_snapshot = {"id": str(selected_opt["id"]), "title": str(selected_opt["title"])}
    if order_line_item is not None:
        order_po = order_line_item.get("purchase_option")
        if not isinstance(order_po, dict) or order_po.get("id") != order_snapshot["id"] or order_po.get("title") != order_snapshot["title"]:
            return UcpPurchaseOptionsAndOffersGuardResult(
                allowed=False,
                decision_code="UCP_ORDER_LINE_PURCHASE_OPTION_SNAPSHOT_MISMATCH",
                resolved_purchase_option_id=str(selected_opt["id"]),
                resolved_line_price_minor=int(selected_opt["price"]),
                emitted_warnings=tuple(warnings),
                order_purchase_option_snapshot=order_snapshot,
                resolved_mor_domain=resolved_mor_domain,
                resolved_checkout_item_id=resolved_checkout_item_id,
            )

    return UcpPurchaseOptionsAndOffersGuardResult(
        allowed=True,
        decision_code="UCP_PURCHASE_OPTIONS_AND_SELLER_OFFERS_VERIFIED",
        resolved_purchase_option_id=str(selected_opt["id"]),
        resolved_line_price_minor=int(selected_opt["price"]),
        emitted_warnings=tuple(warnings),
        order_purchase_option_snapshot=order_snapshot,
        resolved_mor_domain=resolved_mor_domain,
        resolved_checkout_item_id=resolved_checkout_item_id,
    )


@dataclass(frozen=True)
class AcpItemUrlAndFeedUpsertGuardResult:
    allowed: bool
    decision_code: str
    resolved_brand_storefront: str | None
    validated_product_count: int
    validated_variant_count: int


def verify_acp_item_url_and_feed_upsert_guard(
    *,
    checkout_items: list[dict[str, Any]],
    cross_listed_sku_storefronts: dict[str, set[str]] | None = None,
    feed_server_url: str = "https://agent.example.com",
    upsert_products_request: dict[str, Any] | None = None,
    upsert_products_response: dict[str, Any] | None = None,
) -> AcpItemUrlAndFeedUpsertGuardResult:
    """Verify ACP PR #281 (SEP #280), PR #256, and PR #241 deterministic guards."""
    storefront_map = cross_listed_sku_storefronts or {}
    resolved_storefront: str | None = None

    for item in checkout_items:
        item_id = str(item.get("id") or "").strip()
        item_url = item.get("url")
        known_hosts = storefront_map.get(item_id, set())

        if item_url is not None:
            if not isinstance(item_url, str) or not item_url.strip():
                return AcpItemUrlAndFeedUpsertGuardResult(
                    allowed=False,
                    decision_code="ACP_ITEM_URL_EMPTY_OR_NOT_STRING",
                    resolved_brand_storefront=None,
                    validated_product_count=0,
                    validated_variant_count=0,
                )
            parsed = urlparse(item_url)
            if parsed.scheme != "https" or not parsed.netloc or not parsed.path or parsed.path == "/":
                return AcpItemUrlAndFeedUpsertGuardResult(
                    allowed=False,
                    decision_code="ACP_ITEM_URL_INVALID_HTTPS_PRODUCT_URI",
                    resolved_brand_storefront=None,
                    validated_product_count=0,
                    validated_variant_count=0,
                )
            host = parsed.netloc.lower()
            if known_hosts and host not in known_hosts:
                return AcpItemUrlAndFeedUpsertGuardResult(
                    allowed=False,
                    decision_code="ACP_ITEM_URL_STOREFRONT_MISMATCH",
                    resolved_brand_storefront=host,
                    validated_product_count=0,
                    validated_variant_count=0,
                )
            resolved_storefront = host
        elif len(known_hosts) > 1:
            return AcpItemUrlAndFeedUpsertGuardResult(
                allowed=False,
                decision_code="ACP_CROSS_LISTED_SKU_REQUIRES_ITEM_URL",
                resolved_brand_storefront=None,
                validated_product_count=0,
                validated_variant_count=0,
            )

    parsed_feed = urlparse(feed_server_url)
    if parsed_feed.scheme != "https" or not parsed_feed.netloc or "merchant." in parsed_feed.netloc.lower():
        return AcpItemUrlAndFeedUpsertGuardResult(
            allowed=False,
            decision_code="ACP_FEED_SERVER_MUST_BE_AGENT_HOSTED",
            resolved_brand_storefront=resolved_storefront,
            validated_product_count=0,
            validated_variant_count=0,
        )

    total_products = 0
    total_variants = 0
    if upsert_products_request is not None:
        products = upsert_products_request.get("products")
        if not isinstance(products, list) or len(products) < 1:
            return AcpItemUrlAndFeedUpsertGuardResult(
                allowed=False,
                decision_code="ACP_FEED_UPSERT_PRODUCTS_MIN_ITEMS_1_VIOLATION",
                resolved_brand_storefront=resolved_storefront,
                validated_product_count=0,
                validated_variant_count=0,
            )
        total_products = len(products)
        for prod in products:
            variants = prod.get("variants") if isinstance(prod, dict) else None
            if not isinstance(variants, list) or len(variants) < 1:
                return AcpItemUrlAndFeedUpsertGuardResult(
                    allowed=False,
                    decision_code="ACP_FEED_PRODUCT_VARIANTS_MIN_ITEMS_1_VIOLATION",
                    resolved_brand_storefront=resolved_storefront,
                    validated_product_count=total_products,
                    validated_variant_count=total_variants,
                )
            total_variants += len(variants)

    if upsert_products_response is not None:
        resp_id = upsert_products_response.get("id")
        accepted = upsert_products_response.get("accepted")
        if not isinstance(resp_id, str) or not resp_id.strip() or not isinstance(accepted, bool):
            return AcpItemUrlAndFeedUpsertGuardResult(
                allowed=False,
                decision_code="ACP_UPSERT_PRODUCTS_RESPONSE_SCHEMA_INVALID",
                resolved_brand_storefront=resolved_storefront,
                validated_product_count=total_products,
                validated_variant_count=total_variants,
            )

    return AcpItemUrlAndFeedUpsertGuardResult(
        allowed=True,
        decision_code="ACP_ITEM_URL_AND_FEED_UPSERT_VERIFIED",
        resolved_brand_storefront=resolved_storefront,
        validated_product_count=total_products,
        validated_variant_count=total_variants,
    )


@dataclass(frozen=True)
class Ap2MultihopAndAtomicConsumptionGuardResult:
    allowed: bool
    decision_code: str
    hop_count: int
    last_hop_sd_hash: str | None
    derived_checkout_hash: str | None
    wire_presentation_token: str | None


def verify_ap2_multihop_present_and_atomic_consumption_guard(
    *,
    mandate_chain_token: str,
    claims_to_disclose: set[str] | None,
    new_presentation_jwt: str,
    expected_prior_hop_digests: dict[int, str] | None = None,
    presented_checkout_jwt: str,
    closed_mandate_checkout_hash: str,
    expected_checkout_hash_arg: str | None = None,
    payment_mandate_hash: str,
    checkout_transaction_id: str,
    reserved_keys: set[str],
    legacy_token_store_keys: set[str] | None = None,
    reservation_store_healthy: bool = True,
) -> Ap2MultihopAndAtomicConsumptionGuardResult:
    """Verify Google AP2 PR #363, PR #359, and PR #347 deterministic guards."""
    if not mandate_chain_token or not mandate_chain_token.strip():
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_EMPTY_MANDATE_CHAIN_TOKEN",
            hop_count=0,
            last_hop_sd_hash=None,
            derived_checkout_hash=None,
            wire_presentation_token=None,
        )

    # 1. PR #363: Isolate last hop in `~~`-joined delegation chain
    hops = mandate_chain_token.split("~~")
    if any(not h.strip() for h in hops):
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_MALFORMED_DELEGATION_CHAIN_HOP",
            hop_count=len(hops),
            last_hop_sd_hash=None,
            derived_checkout_hash=None,
            wire_presentation_token=None,
        )

    if expected_prior_hop_digests:
        for hop_idx, expected_digest in expected_prior_hop_digests.items():
            if hop_idx < 0 or hop_idx >= len(hops) - 1:
                return Ap2MultihopAndAtomicConsumptionGuardResult(
                    allowed=False,
                    decision_code="AP2_PRIOR_HOP_INDEX_OUT_OF_RANGE",
                    hop_count=len(hops),
                    last_hop_sd_hash=None,
                    derived_checkout_hash=None,
                    wire_presentation_token=None,
                )
            actual_digest = compute_sha256_b64url(hops[hop_idx].removesuffix("~"))
            if actual_digest != expected_digest:
                return Ap2MultihopAndAtomicConsumptionGuardResult(
                    allowed=False,
                    decision_code="AP2_PRIOR_HOP_DISCLOSURE_TAMPERED",
                    hop_count=len(hops),
                    last_hop_sd_hash=None,
                    derived_checkout_hash=None,
                    wire_presentation_token=None,
                )

    prior_hops, separator, last_hop = mandate_chain_token.rpartition("~~")
    if not separator:
        last_hop = mandate_chain_token

    parts = [p for p in last_hop.split("~") if p]
    if not parts:
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_LAST_HOP_JWT_MISSING",
            hop_count=len(hops),
            last_hop_sd_hash=None,
            derived_checkout_hash=None,
            wire_presentation_token=None,
        )
    jwt_part = parts[0]
    disclosures = parts[1:]

    if claims_to_disclose is not None:
        selected_disclosures: list[str] = []
        for disc in disclosures:
            # Disclosure format in test/fixture vectors: `<key>:<val>` or raw disclosure
            key = disc.split(":", 1)[0] if ":" in disc else disc
            if key == "cnf" or key in claims_to_disclose:
                selected_disclosures.append(disc)
        if selected_disclosures:
            redacted_last_hop = jwt_part + "~" + "~".join(selected_disclosures) + "~"
        else:
            redacted_last_hop = jwt_part + "~"
        prev_token_for_binding = redacted_last_hop
    else:
        prev_token_for_binding = last_hop if last_hop.endswith("~") else last_hop + "~"

    previous_hop_to_join = prev_token_for_binding.removesuffix("~")
    last_hop_sd_hash = compute_sha256_b64url(previous_hop_to_join)
    if separator:
        wire_token = f"{prior_hops}~~{previous_hop_to_join}~~{new_presentation_jwt}"
    else:
        wire_token = f"{previous_hop_to_join}~~{new_presentation_jwt}"

    # 2. PR #359: Always derive `checkout_hash` from presented `checkout_jwt`
    derived_checkout_hash = compute_sha256_b64url(presented_checkout_jwt)
    if derived_checkout_hash != closed_mandate_checkout_hash:
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_PRESENTED_CHECKOUT_HASH_MISMATCH",
            hop_count=len(hops) + 1,
            last_hop_sd_hash=last_hop_sd_hash,
            derived_checkout_hash=derived_checkout_hash,
            wire_presentation_token=wire_token,
        )
    if expected_checkout_hash_arg is not None and expected_checkout_hash_arg != closed_mandate_checkout_hash:
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_EXPECTED_CHECKOUT_HASH_ASSERTION_MISMATCH",
            hop_count=len(hops) + 1,
            last_hop_sd_hash=last_hop_sd_hash,
            derived_checkout_hash=derived_checkout_hash,
            wire_presentation_token=wire_token,
        )

    # 3. PR #347: Atomic reservation store for Payment Mandate & Checkout transaction ID
    if not reservation_store_healthy:
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="replay_state_unavailable",
            hop_count=len(hops) + 1,
            last_hop_sd_hash=last_hop_sd_hash,
            derived_checkout_hash=derived_checkout_hash,
            wire_presentation_token=wire_token,
        )
    if not payment_mandate_hash.strip() or not checkout_transaction_id.strip():
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="AP2_RESERVATION_KEY_EMPTY",
            hop_count=len(hops) + 1,
            last_hop_sd_hash=last_hop_sd_hash,
            derived_checkout_hash=derived_checkout_hash,
            wire_presentation_token=wire_token,
        )

    legacy_keys = legacy_token_store_keys or set()
    mandate_key = f"mandate:{payment_mandate_hash}"
    tx_key = f"tx:{checkout_transaction_id}"
    if (
        mandate_key in reserved_keys
        or tx_key in reserved_keys
        or payment_mandate_hash in legacy_keys
        or checkout_transaction_id in legacy_keys
    ):
        return Ap2MultihopAndAtomicConsumptionGuardResult(
            allowed=False,
            decision_code="mandate_already_used",
            hop_count=len(hops) + 1,
            last_hop_sd_hash=last_hop_sd_hash,
            derived_checkout_hash=derived_checkout_hash,
            wire_presentation_token=wire_token,
        )

    reserved_keys.add(mandate_key)
    reserved_keys.add(tx_key)

    return Ap2MultihopAndAtomicConsumptionGuardResult(
        allowed=True,
        decision_code="AP2_MULTIHOP_BINDING_AND_ATOMIC_CONSUMPTION_VERIFIED",
        hop_count=len(hops) + 1,
        last_hop_sd_hash=last_hop_sd_hash,
        derived_checkout_hash=derived_checkout_hash,
        wire_presentation_token=wire_token,
    )


@dataclass(frozen=True)
class Tau2VoiceV2SubmissionAndPass3GuardResult:
    allowed: bool
    decision_code: str
    total_expected_calls: int
    verified_cell_count: int
    diagnostics_fingerprint_sha256: str | None


def verify_tau2_voice_v2_banking_entity_and_crossed_pass3_guard(
    *,
    benchmark_version: str,
    task_subset_name: str,
    cells: list[dict[str, Any]],
    expected_binding_revisions: dict[str, str],
    max_call_duration_sec: float,
    pass3_mode: str = "crossed",
    pass3_seeds: tuple[int, ...] = TAU2_RCS_V3_SEEDS,
    reused_regular_seed: int | None = 42,
    regular_results_read_only: bool = True,
    gemini_38_extended_thinking: bool = False,
    google_genai_version: tuple[int, int] = (2, 26),
    has_benchmark_diagnostics_json: bool = True,
    recorded_verdict_fingerprints: dict[str, str] | None = None,
    recomputed_verdict_fingerprints: dict[str, str] | None = None,
) -> Tau2VoiceV2SubmissionAndPass3GuardResult:
    """Verify Sierra tau2-bench PR #637, PR #639, and PR #620 deterministic guards."""
    # 1. PR #637: voice-v2-banking (97 * 6 = 582) and voice-v2-entity (200 * 6 = 1200, <= 240s)
    if benchmark_version == "voice-v2-banking":
        if task_subset_name != "banking_knowledge_97":
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_BANKING_VOICE_SUBSET_MISMATCH",
                total_expected_calls=582,
                verified_cell_count=0,
                diagnostics_fingerprint_sha256=None,
            )
        expected_calls_per_cell = 97
    elif benchmark_version == "voice-v2-entity":
        if task_subset_name != "intake_200":
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_ENTITY_VOICE_SUBSET_MISMATCH",
                total_expected_calls=1200,
                verified_cell_count=0,
                diagnostics_fingerprint_sha256=None,
            )
        if max_call_duration_sec > 240.0:
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_ENTITY_INTAKE_240S_CALL_LIMIT_EXCEEDED",
                total_expected_calls=1200,
                verified_cell_count=0,
                diagnostics_fingerprint_sha256=None,
            )
        expected_calls_per_cell = 200
    else:
        return Tau2VoiceV2SubmissionAndPass3GuardResult(
            allowed=False,
            decision_code="TAU2_UNSUPPORTED_VOICE_V2_BENCHMARK_VERSION",
            total_expected_calls=0,
            verified_cell_count=0,
            diagnostics_fingerprint_sha256=None,
        )

    total_expected_calls = expected_calls_per_cell * len(TAU2_VOICE_V2_LANGUAGES)
    cell_langs = [str(c.get("language") or "") for c in cells]
    if tuple(cell_langs) != TAU2_VOICE_V2_LANGUAGES:
        return Tau2VoiceV2SubmissionAndPass3GuardResult(
            allowed=False,
            decision_code="TAU2_SIX_LANGUAGE_MATRIX_INCOMPLETE_OR_REORDERED",
            total_expected_calls=total_expected_calls,
            verified_cell_count=len(cells),
            diagnostics_fingerprint_sha256=None,
        )

    for cell in cells:
        lang = str(cell.get("language"))
        if cell.get("binding_revision") != expected_binding_revisions.get(lang):
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_CELL_BINDING_REVISION_PIN_MISMATCH",
                total_expected_calls=total_expected_calls,
                verified_cell_count=len(cells),
                diagnostics_fingerprint_sha256=None,
            )
        # PR #620: Refuse incomplete cell rewards or missing applicable judge verdicts
        missing = int(cell.get("missing_rewards", 0))
        errored = int(cell.get("errored_rewards", 0))
        unscored = int(cell.get("unscored_rewards", 0))
        scored = int(cell.get("scored_calls", 0))
        if missing > 0 or errored > 0 or unscored > 0 or scored != expected_calls_per_cell:
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_SUBMIT_INCOMPLETE_MATRIX_REWARDS_REFUSED",
                total_expected_calls=total_expected_calls,
                verified_cell_count=len(cells),
                diagnostics_fingerprint_sha256=None,
            )
        unjudged = int(cell.get("unjudged_applicable_measures", 0))
        if unjudged > 0:
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_SUBMIT_MISSING_APPLICABLE_JUDGE_VERDICTS_REFUSED",
                total_expected_calls=total_expected_calls,
                verified_cell_count=len(cells),
                diagnostics_fingerprint_sha256=None,
            )

    # 2. PR #639: Crossed Pass^3 `voice-v2-rcs-v3` seeds (42, 401, 16319), seed-42 reuse & google-genai>=2.26
    if pass3_mode == "crossed":
        if tuple(pass3_seeds) != TAU2_RCS_V3_SEEDS:
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_CROSSED_PASS3_SEEDS_MUST_MATCH_RCS_V3",
                total_expected_calls=total_expected_calls,
                verified_cell_count=len(cells),
                diagnostics_fingerprint_sha256=None,
            )
        if reused_regular_seed is not None and (reused_regular_seed != 42 or not regular_results_read_only):
            return Tau2VoiceV2SubmissionAndPass3GuardResult(
                allowed=False,
                decision_code="TAU2_REGULAR_RESULTS_REUSE_REQUIRES_READONLY_SEED_42",
                total_expected_calls=total_expected_calls,
                verified_cell_count=len(cells),
                diagnostics_fingerprint_sha256=None,
            )
    if gemini_38_extended_thinking and google_genai_version < (2, 26):
        return Tau2VoiceV2SubmissionAndPass3GuardResult(
            allowed=False,
            decision_code="TAU2_GEMINI_38_EXTENDED_THINKING_REQUIRES_GENAI_2_26",
            total_expected_calls=total_expected_calls,
            verified_cell_count=len(cells),
            diagnostics_fingerprint_sha256=None,
        )

    # 3. PR #620: `benchmark-diagnostics.json` presence and verdict fingerprint recomputation
    if not has_benchmark_diagnostics_json:
        return Tau2VoiceV2SubmissionAndPass3GuardResult(
            allowed=False,
            decision_code="TAU2_VOICE_V2_MISSING_BENCHMARK_DIAGNOSTICS_JSON",
            total_expected_calls=total_expected_calls,
            verified_cell_count=len(cells),
            diagnostics_fingerprint_sha256=None,
        )
    rec = recorded_verdict_fingerprints or {}
    recomp = recomputed_verdict_fingerprints or {}
    if not rec or rec != recomp:
        return Tau2VoiceV2SubmissionAndPass3GuardResult(
            allowed=False,
            decision_code="TAU2_JUDGE_VERDICT_FINGERPRINT_RECOMPUTATION_MISMATCH",
            total_expected_calls=total_expected_calls,
            verified_cell_count=len(cells),
            diagnostics_fingerprint_sha256=None,
        )

    canonical_fp = hashlib.sha256(
        "|".join(f"{k}:{rec[k]}" for k in sorted(rec)).encode("utf-8")
    ).hexdigest()

    return Tau2VoiceV2SubmissionAndPass3GuardResult(
        allowed=True,
        decision_code="TAU2_VOICE_V2_SUBMISSION_AND_CROSSED_PASS3_VERIFIED",
        total_expected_calls=total_expected_calls,
        verified_cell_count=len(cells),
        diagnostics_fingerprint_sha256=canonical_fp,
    )
