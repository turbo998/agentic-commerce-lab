# Web IQ search competitive matrix (2026-11-02)

🌐 **Language / 语言导航**: **[中文](2026-11-02-webiq-search-competitive.md)** | **English (current)** | **[2026-11-01 note](2026-11-01-webiq-search-competitive.en.md)** | **[Browse passage note](2026-11-01-webiq-azure-browse-passage.en.md)**

![Status card: account exists, latency not measured](webiq-search-competitive-2026-11-02.svg)

## Findings (Verified 2026-11-02)

1. **Live measurement status stays strictly `not_measured`**: Although the G3 account `webiq-lab-bench` (`Microsoft.WebIQ/accounts@2026-06-01-preview`, `location=global`, `kind=WebIQ.Grounding`, `statisticsEnabled=false`) exists in the paid lab subscription (`rg-webiq-bench`), no automation-eligible `WEBIQ_API_KEY` is bound in the local environment, and `BRIGHTDATA_API_KEY`, `EXA_API_KEY`, `TAVILY_API_KEY`, and `PARALLEL_API_KEY` are also absent (`credential="absent"`). All five providers remain `call="not_called"`, `latency="not_measured"`, `success="not_measured"`, and `citation_check="not_measured"`. Missing latencies are never coerced to `0`. The cross-provider 7-card latency deck remains withheld (`withheld_until_measured_latency_exists`) until a real measured `summary.json` exists.
2. **Strict separation from sealed replay baseline**: The `2026-10-26.stage1746` / `2026-11-02.stage1753` figures (Web IQ `/v3/search/web` P95 `240ms`, task success `18/18`, injection block `12/12`, batched concurrency `1.52s vs 4.18s`) belong strictly to the `sealed_demo` deterministic replay suite and are never mixed into this live cross-provider bake-off matrix.
3. **2026-11-02 Architectural Coupling Insight (Web IQ Grounding × Stripe SFTP Hybrid Catalog Feed × Seller Checkout Hooks)**:
   - Today's primary-source verification of Stripe SFTP Catalog Ingestion (`Product Master` every 24h + `Delta` every 1h, `manifest.json` atomic barrier, `disable_checkout=true` discovery-only gate) and Seller Checkout Hooks (`delegated_commerce.product_price_availability` real-time quote callback + `v1.delegated_checkout.finalize_checkout` **4,000 ms hard timeout**) defines a **three-tier grounding architecture** for enterprise commerce agents:
     1. **Open-Web & Long-Tail Discovery (T-0 Discovery Layer)**: For merchants not yet onboarded to SFTP feeds or SKUs marked `disable_checkout=true` (e.g., prescription goods, custom B2B quotes, external `link` redirect items), use **Microsoft Web IQ `POST /v3/search/web` (`$7/1k`, `contentFormat="passage"`)** for discovery, followed by **`POST /v3/browse` (`$1/1k`, default $\le 3000$ chars)** on known policy/product URLs with deterministic pre-LLM prompt-injection scrubbing (`PROMPT_INJECTION_RE`).
     2. **Structured Merchant Catalog Sync (T-1 Hourly Delta Layer)**: Onboarded Stripe Catalog merchants synchronize via **SFTP `Delta` feeds (every 1h) + `manifest.json` atomic barriers**; rows with `delete=true` ignore all columns except `id` and `delete`.
     3. **Millisecond Pre-Checkout Authority Gate (T-2 Checkout Signing Layer)**: Before completing a `RequestedSession` or `UCP` checkout, an agent must never treat any search snippet (Web IQ, Bright Data SERP, Exa, Tavily, or Parallel) as final settlement authority. It must verify real-time inventory and SHA-256 price digests against `delegated_commerce.product_price_availability`, and `v1.delegated_checkout.finalize_checkout` must return `2xx` within **4,000 ms** (non-`2xx` maps to `HTTP 424 Failed Dependency` for the agent).

## Account status

- Resource group `rg-webiq-bench` in `southeastasia`. The account location is `global`.
- `provisioningState=Succeeded`.
- This note does not publish the subscription ID, internal ID, gateway hostname, or sign-in email.
- https://webiq.microsoft.ai/profiles is where an `x-apikey` is minted. Azure CLI cannot acquire a token for `https://api.microsoft.ai/.default`.
- Browse remains AppID-gated. Auto is not charged while in beta.
- No Bright Data, Exa, Tavily, or Parallel account was created.

## Official list prices, not scores

Every row is labeled `official_list_price`. Verified 2026-11-02. These numbers are not latency bars.

| Provider | Official list price | Source | Statement that is not a measurement |
|---|---|---|---|
| Web IQ | `/web`, `/video`, `/news`, `/images` $7 per 1,000; `/browse` $1 per 1,000. Effective 2026-10-16; page updated 2026-10-29. | [Pricing](https://learn.microsoft.com/en-us/web-iq/resources/pricing) | Uncharged Auto beta is not a latency figure. |
| Bright Data SERP | 5,000 free requests per month; pay as you go $1.50 per 1,000 successful requests; Scale $499/month includes 380,000, then $1.30 per 1,000. The page says displayed prices can be local-currency estimates and USD is binding. | [SERP pricing](https://brightdata.com/pricing/serp) | "Under 1 second" is marketing, not a measurement. |
| Exa | Lite/instant $4/1k, auto/fast $7/1k, contents $1/1k pages per content type, answer $5/1k, monitors $15/1k. deep-lite/deep $12/1k, deep-reasoning $15/1k. Fixed Agent effort is $0.012–$1.00 per request. Free credit is $10 and resets on the first of each month. | [Pricing](https://exa.ai/pricing) | The [search reference](https://docs.exa.ai/reference/search) caps include and exclude domain lists at 1,200 each and says to use those filters instead of a `site:` operator. Seconds on the pricing page stay out of the latency chart. |
| Tavily | Basic, fast, and ultra-fast are 1 credit. Advanced is 2. Pay as you go is $0.008/credit. The docs table publishes Project $0.0075, Bootstrap $0.0067, Startup $0.0058, Growth $0.005 per credit. Research pro is 15–250 credits, mini is 4–110. 1,000 free credits per month. | [API credits](https://docs.tavily.com/documentation/api-credits) | The [search reference](https://docs.tavily.com/documentation/api-reference/endpoint/search) says `max_results` defaults to 10 and maxes at 20. `chunks_per_source` is 1–3. Failed extractions and failed map requests are not billed. No latency from this run. |
| Parallel | Turbo/fast $1/1k, basic/advanced $5/1k, extra results $1/1k. Extract $1/1k URLs. Task lite $5/1k successful runs, ultra8x $2,400/1k. Responses medium $50/1k. | [Pricing](https://docs.parallel.ai/getting-started/pricing) | The [search reference](https://docs.parallel.ai/api-reference/search/search) says `https://eu.parallel.ai` supports only basic mode. Image Search documents advanced as its own default. Do not copy that onto web search. The 200 ms–3 s range stays `vendor_stated`. |

## Offline contract

[`lab/webiq_search_bakeoff.py`](../../lab/webiq_search_bakeoff.py) (`VERIFIED_ON = "2026-11-02"`) never opens a network connection. Three sealed questions cover the return window, a citable price page, and whether a public recall should stop replenishment. When a key is missing, `latency`, `success`, and `citation_check` are `not_measured`. When a key is present, the row records `credential=present` and `call=not_called`. It still does not make a paid call.

## Architectural boundary: Microsoft Web IQ caller-visible passages vs. Foundry Grounding with Bing Search vs. Stripe SFTP/Hooks

Verified on 2026-11-02 against official Microsoft Learn documentation ([Web IQ Browse Reference](https://learn.microsoft.com/en-us/web-iq/reference/browse), [Web IQ Error Handling](https://learn.microsoft.com/en-us/web-iq/reference/error-handling), and [Foundry Agents Web Grounding Overview](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-overview)) and Stripe Agentic Commerce documentation:

| Dimension | Microsoft Web IQ (`/v3/search/web`, `/v3/browse`) | Microsoft Foundry Grounding with Bing Search | Stripe SFTP Feed + Seller Checkout Hooks | Agentic Commerce Architectural Impact |
|---|---|---|---|---|
| **Caller visibility of raw retrieved passages** | **Returned directly to caller code** (`results[].content`, `contentFormat="passage"` default $\le 3000$ chars) | **Hidden from caller code** (raw search chunks stay inside the managed Foundry boundary; caller only receives the model synthesis + citation URLs) | Structured CSV/JSON/XML catalog fields + `delegated_commerce.product_price_availability` JSON callback | Deterministic pre-LLM prompt-injection scrubbing (`PROMPT_INJECTION_RE`) and SHA-256 price digest verification (`CheckoutStore`) require **Web IQ** for open-web grounding rather than opaque model-only grounding |
| **`retryAfter` & timeout contract** | `AuthUserThrottled` (429) & `InternalServerError` (500) emit duration strings (`"60s"`), whereas `Browse 202` and `TooManyOnDemandCrawls` (**also HTTP 429!**), `520`, `523`, and `524` emit ISO-8601 UTC timestamps | Abstracted inside the managed Foundry tool | `v1.delegated_checkout.finalize_checkout` enforces a **4,000 ms hard timeout**; non-`2xx` maps to **`HTTP 424`** for the agent | Retrieval layer must parse dual-format `retryAfter` by `error.code`; checkout layer must never chain slow live web crawls (`liveCrawl=fallback` + `renderDynamicPages=true`) inside synchronous `finalize_checkout` hooks |

## How a commerce agent should route

This is architecture guidance (`label="architecture_guidance"`), not a measured winner.

| Scenario | Call first | Why | Do not |
|---|---|---|---|
| Current price, URL unknown | Web IQ `/web` with `contentFormat=passage`, optional `site:` on the retailer, then `/browse` on the returned URL | Search discovers; Browse reads the page. Use `crawledAt` to judge age | Change an authorized amount from a SERP snippet |
| Return policy, URL known | Web IQ `/browse`, `passage` plus a non-blank `query`. Use `liveCrawl=fallback` only after an index 404 | $1/1k and the passage is query-targeted. Without full-document access, content stops at 3000 characters | Buy a SERP call for one known policy page |
| Recall or safety news that should stop replenishment | Web IQ `/news`, then read `source`, `lastUpdatedAt`, and `crawledAt` | Web has no date filter; the FAQ sends news scenarios to News | Treat an old web passage as "no recall today" |
| Product image or embeddable video | `/images` or `/videos` | Host page, size, watermark, and embed fields exist | Use an image result as price evidence |
| Several questions in one user turn | Split into separate `/web` or `/news` calls. Auto beta can return typed evidence, but it is uncharged and the contract can change | The FAQ says one Web request handles one query | Stuff the whole utterance into one 1000-character query |
| Google shopping units, ads, or rank in a country | Bright Data SERP, with `gl` / `hl` on the engine URL | Official use cases include price comparison and rank tracking | Treat it as the publisher page |
| Known URL blocked, raw HTML needed | Bright Data Web Unlocker, or Exa `/contents`, Tavily Extract, Parallel Extract | Unlocker is the unblocker. The others sell page text. Units differ | Use Unlocker for click-through checkout. Docs say it is not browser interaction |
| Clicks, logged-in pages, screenshots | Bright Data Browser API | Explicit product-selector boundary | Pretend Browse `renderDynamicPages` submits forms. It only renders when live crawl is fallback |

For the full 37-entry official pricing and parameter appendix, see [`lab/webiq_search_bakeoff.py`](../../lab/webiq_search_bakeoff.py) and the [2026-11-01 detailed matrix](2026-11-01-webiq-search-competitive.en.md).
