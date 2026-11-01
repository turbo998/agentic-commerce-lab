# Web IQ search competitive matrix (2026-11-01)

🌐 **Language / 语言导航**: **[中文](2026-11-01-webiq-search-competitive.md)** | **English (current)** | **[Browse passage note](2026-11-01-webiq-azure-browse-passage.en.md)**

![Status card: account exists, latency not measured](webiq-search-competitive-2026-11-01.svg)

## Finding

The lab paid subscription can create a Web IQ account. G3 account `webiq-qichen2-bench` (`Microsoft.WebIQ/accounts@2026-06-01-preview`, `location=global`, `kind=WebIQ.Grounding`, `statisticsEnabled=false`) was created on 2026-11-01. The API key is not bound, and Bright Data, Exa, Tavily, and Parallel keys are not in the local environment. All five providers stay `not_measured`. Missing latency is not written as zero. The 7-card latency deck stays withheld until a real `summary.json` exists.

The 2026-10-26 sealed figures (P95 240ms, 18/18, 12/12, 1.52s vs 4.18s) remain `sealed_demo`. They are not this bake-off.

## Account status

- Resource group `rg-webiq-bench` in `southeastasia`. The account location is `global`.
- `provisioningState=Succeeded`.
- This note does not publish the subscription ID, internal ID, gateway hostname, or sign-in email.
- https://webiq.microsoft.ai/profiles is where an `x-apikey` is minted. Azure CLI cannot acquire a token for `https://api.microsoft.ai/.default`.
- Browse remains AppID-gated. Auto is not charged while in beta.
- No Bright Data, Exa, Tavily, or Parallel account was created.

The earlier [Browse passage note](2026-11-01-webiq-azure-browse-passage.en.md) recorded a read-only inventory of zero accounts. That Azure status is superseded here. The sealed demo numbers are unchanged.

## Official list prices, not scores

Every row is labeled `official_list_price`. Verified 2026-11-01. These numbers are not latency bars.

| Provider | Official list price | Source | Statement that is not a measurement |
|---|---|---|---|
| Web IQ | `/web`, `/video`, `/news`, `/images` $7 per 1,000; `/browse` $1 per 1,000. Effective 2026-10-16; page updated 2026-10-29. | [Pricing](https://learn.microsoft.com/en-us/web-iq/resources/pricing) | Uncharged Auto beta is not a latency figure. |
| Bright Data SERP | 5,000 free requests per month; pay as you go $1.50 per 1,000 successful requests; Scale $499/month includes 380,000, then $1.30 per 1,000. The page says displayed prices can be local-currency estimates and USD is binding. | [SERP pricing](https://brightdata.com/pricing/serp) | "Under 1 second" is marketing, not a measurement. |
| Exa | Lite/instant $4/1k, auto/fast $7/1k, contents $1/1k pages per content type, answer $5/1k, monitors $15/1k. deep-lite/deep $12/1k, deep-reasoning $15/1k. Fixed Agent effort is $0.012–$1.00 per request. Free credit is $10 and resets on the first of each month. | [Pricing](https://exa.ai/pricing) | The [search reference](https://docs.exa.ai/reference/search) caps include and exclude domain lists at 1,200 each and says to use those filters instead of a `site:` operator. Seconds on the pricing page stay out of the latency chart. |
| Tavily | Basic, fast, and ultra-fast are 1 credit. Advanced is 2. Pay as you go is $0.008/credit. The docs table publishes Project $0.0075, Bootstrap $0.0067, Startup $0.0058, Growth $0.005 per credit. Research pro is 15–250 credits, mini is 4–110. 1,000 free credits per month. | [API credits](https://docs.tavily.com/documentation/api-credits) | The [search reference](https://docs.tavily.com/documentation/api-reference/endpoint/search) says `max_results` defaults to 10 and maxes at 20. `chunks_per_source` is 1–3. Failed extractions and failed map requests are not billed. No latency from this run. |
| Parallel | Turbo/fast $1/1k, basic/advanced $5/1k, extra results $1/1k. Extract $1/1k URLs. Task lite $5/1k successful runs, ultra8x $2,400/1k. Responses medium $50/1k. | [Pricing](https://docs.parallel.ai/getting-started/pricing) | The [search reference](https://docs.parallel.ai/api-reference/search/search) says `https://eu.parallel.ai` supports only basic mode. Image Search documents advanced as its own default. Do not copy that onto web search. The 200 ms–3 s range stays `vendor_stated`. |

## Offline contract

[`lab/webiq_search_bakeoff.py`](../../lab/webiq_search_bakeoff.py) never opens a network connection. Three sealed questions cover the return window, a citable price page, and whether a public recall should stop replenishment. When a key is missing, `latency`, `success`, and `citation_check` are `not_measured`. When a key is present, the row records `credential=present` and `call=not_called`. It still does not make a paid call.

The daily research task now has a mandatory pillar: Web IQ versus Bright Data, Exa, and mainstream web search. The night-manager check must verify that pillar. Missing credentials stay `not_measured`.

## Architectural boundary: Microsoft Web IQ caller-visible passages vs. Foundry Grounding with Bing Search

Verified on 2026-11-01 against official Microsoft Learn documentation ([Web IQ Browse Reference](https://learn.microsoft.com/en-us/web-iq/reference/browse), [Web IQ Error Handling](https://learn.microsoft.com/en-us/web-iq/reference/error-handling), and [Foundry Agents Web Grounding Overview](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-overview)):

| Dimension | Microsoft Web IQ (`/v3/search/web`, `/v3/browse`) | Microsoft Foundry Grounding with Bing Search | Agentic Commerce Architectural Impact |
|---|---|---|---|
| **Caller visibility of raw retrieved passages** | **Returned directly to caller code** (`results[].content`, `contentFormat="passage"` default $\le 3000$ chars) | **Hidden from caller code** (raw search chunks stay inside the managed Foundry boundary; caller only receives the model synthesis + citation URLs) | Deterministic pre-LLM prompt-injection scrubbing (`PROMPT_INJECTION_RE`) and SHA-256 price digest verification (`CheckoutStore`) require **Web IQ** rather than opaque model-only grounding |
| **Dual-format `retryAfter` contract** | `AuthUserThrottled` (429) & `InternalServerError` (500) emit duration strings (`"60s"`), whereas `Browse 202` and `TooManyOnDemandCrawls` (**also HTTP 429!**), `520`, `523`, and `524` emit ISO-8601 UTC timestamps (`"2026-10-30T01:01:00Z"`) | Abstracted inside the managed Foundry tool | Callers cannot infer `retryAfter` syntax from `status == 429` alone; enforced by `parse_webiq_retry_after()` and `classify_webiq_error_response()` in `lab/webiq_commerce_demo.py` |

## How to read the numbers

| Label | Meaning |
|---|---|
| `official_list_price` | Unit price on the vendor's pricing page. Not latency and not a quality score. |
| `vendor_published_benchmark` | A comparison the vendor published, with competitors anonymized. `independently_reproduced=false`. |
| `vendor_stated` | A speed or success sentence in docs or marketing, without a reproducible query set. |
| `not_measured` | This repo did not make the call. A missing value is not zero. |

The sealed 2026-10-26 demo figures stay with that demo. They are not rows in this matrix.

## Four product classes

| Class | Returns | Commerce step it fits | Does not fit |
|---|---|---|---|
| Index grounding | Ranked passages, citation URLs, crawl time | Find evidence when the URL is unknown | Treating the snippet as the retailer's price |
| URL extract | Passage or document for a known URL | Policy page or product page you already have | Discovering a new recall |
| SERP scrape | Ads, organic results, shopping units from a search engine | Monitor how a market's search page presents an offer | Sole authority for a price or return-window change |
| Answer API | A model-written answer plus citations | Low-risk summary | Checkout authority. Money decisions stay in this repo's authority layer |

## Web IQ public contract

Verified 2026-11-01. REST base `https://api.microsoft.ai/v3`. MCP is `https://api.microsoft.ai/v3/mcp` with tools `web`, `news`, `images`, `videos`, and `browse`. Tool parameters match the REST reference. The tool list follows the AppID allow-list.

The Azure resource meters and bills. It is not in the request path. The application calls `api.microsoft.ai`. Identity is the Web IQ AppID. A production AppID starts at 15 QPS. Key creation is free; keys and bound Entra apps share that quota. Entra client credentials are the production recommendation; `x-apikey` is the prototype path. Private Link, VNet integration, and IP allowlists are not supported. The terms exclude the Microsoft Products and Services Data Protection Addendum, and there is no regional data-residency commitment. Query text is logged for operations by default. Zero Query Logging is not self-serve. Response content must not be cached to build a derivative dataset. Inbound queries are not PII-masked.

Web IQ does not generate the final answer and does not execute instructions found in a page. Indirect prompt injection remains the model's and this repo's authority-layer problem. Index normalization is not a guarantee that prompt-like text was removed. LinkedIn results are currently excluded. Browse returns HTTP 403 for an excluded URL.

### Endpoints and parameters

| Endpoint | Status | Parameters that change the call | Limits | Grounding fields |
|---|---|---|---|---|
| `POST /v3/search/web` | GA | `query`, `maxResults`, `language`, `region`, `location`, `contentFormat`, `maxLength`, `safeSearch` | query 1000 characters; `maxResults` default 10, max 50 | `url`, `content`, `crawledAt`, `lastUpdatedAt`, `contentTier`, plus `querySignals.freshness` and `riskLevel` |
| `POST /v3/search/news` | GA | same family, no `safeSearch` | `maxResults` max 20 | `source`, `url`, `content`, `crawledAt`, `lastUpdatedAt` |
| `POST /v3/search/images` | GA | `aspectRatio`, `color`, `imageSize`, `watermarkFree`, pixel bounds, `safeSearch` | `maxResults` default and max 30 | `url`, `hostPageUrl`, `caption`. The pricing page says licensing info is included; the field table fetched here has no separate license field |
| `POST /v3/search/videos` | GA | `freshness`, `resolution`, `duration`, `embeddable`, `enablePlaylist`, `safeSearch` | `maxResults` default and max 30 | `summary`, `moments`, `publishedBy`, `viewCount` |
| `POST /v3/browse` | GA, AppID on request | `url` required; `query` required for `passage`; `liveCrawl` `none` or `fallback`; `renderDynamicPages` only with fallback | query 1000 characters; content capped at 3000 characters without full-document access | One page's `content`. Segments are relevance-selected, returned in page order, joined with `...`, and may split mid-sentence |
| `POST /v3/auto` | Beta, not charged, AppID on request | `mode` `fast` or `advanced`; `responseFilter` `web/news/timezone/weather/images/videos`; `maxResponseLength` default 30000, clamped to 1500..500000 | Contract can change | Typed evidence with citations scoped to that result |

`contentFormat=passage` is the grounding recommendation. Without full-document access, `text`, `html`, and `markdown` return HTTP 403 `AuthContentFormatForbidden`. With that access, Web defaults to `html`, News defaults to `text`, and `maxLength` can reach 500000. Web does not return a separate `snippet`. Web has no date filter. The FAQ says a hard date filter usually costs relevance, and news scenarios should use News rather than filtering Web. `site:` and `-site:` work, reduce relevance, and `site:` can return adult content regardless of `safeSearch`. Larger domain allow or deny lists are not a customer-managed feature.

`contentTier` is `standard`, `entitled` (bring-your-own publisher license), or `premium` (beyond the standard offer and subject to billing). A commerce agent has to read that field. The $7 per 1,000 calls does not by itself include premium content.

`liveCrawl=none` returns indexed content only and 404s if the URL is absent. `fallback` is the live-crawl path. Dynamic rendering is not the default.

### Vendor-published benchmark, not reproduced here

The [Learn benchmarks page](https://learn.microsoft.com/en-us/web-iq/concepts/benchmarks) (updated 2026-10-13) publishes:

- Grounding satisfaction: Web IQ 79.05; anonymized competitors 75.70, 75.61, 73.96, 72.89, 67.53, 64.71. 3,000 global blind queries, 10 results, 10,000 characters or equivalent.
- P95: Web IQ 164 ms; next service 406 ms; slowest 2,090 ms. Averaged across five datacenters, unique queries to avoid cache hits, same 10-result / 10,000-character configuration.

Competitors are not named. Do not map them to Bright Data or Exa. Label: `vendor_published_benchmark`, `independently_reproduced=false`. This repo does not draw those bars as its own 7-card.

### Portal observation, sanitized

On 2026-11-01 the signed-in portal showed a trial profile expiring 2028-02-01, with a 100 QPS quota. Allowed verticals included Web, Videos, Browse, News, Images, Classic, and beta verticals Places, Auto, Commerce, Finance, Sports, and AutoSuggest. No API key was present, and none was created. The UI says eval keys are for light personal use only and must not be used for internal services, automation, or metrics collection. The Commerce beta vertical is therefore not a license to run this bake-off on an eval key.

The public FAQ still says there is no dedicated finance, sports, or weather API today. Portal beta names are not the public REST contract. Commerce is not in the public endpoint index.

## Bright Data: pick the product before the price

The [product selector](https://docs.brightdata.com/product-selector) splits search from page fetch:

| Goal | Product | Returns |
|---|---|---|
| Google, Bing, Yandex, DuckDuckGo, and related result pages | SERP API | Parsed organic results, ads, hotels, flights. The body is `zone` plus an engine URL. `format` can be `raw`; `data_format` can be `parsed_light` or markdown |
| HTML for a known URL, no clicks | Web Unlocker | Raw HTML. Docs say it is not a Playwright or Puppeteer interaction product |
| Clicks, forms, screenshots | Browser API | A browser session |
| Structured products from a covered site such as Amazon | Web Scraper API | Prebuilt JSON, not general web search |

SERP docs list Google, Bing, DuckDuckGo, Yandex, Baidu, Yahoo, and Naver. Geo and device parameters live on the engine URL (`hl`, `gl`), not in one shared `region` field. In async mode only the send is billed. The pricing FAQ says response time under 5 sec. The introduction separately says under 1 second and says Fast SERP requires an account manager. Both sentences are `vendor_stated`. They are not one measurement.

List prices fetched 2026-11-01. USD is binding; displayed prices can be local-currency estimates.

| Product | Free | Pay as you go | Scale |
|---|---|---|---|
| SERP | 5,000 requests/month | $1.50 / 1,000 successful requests | $499/month includes 380,000, then $1.30 / 1,000 |
| Web Unlocker | 5,000 requests/month | $1.50 / 1,000 successful requests | $499/month includes 383,000, then $1.30 / 1,000 |

Do not copy SERP's 380,000 included requests onto Unlocker.

## Exa, Tavily, Parallel

Exa's pricing page is prepaid, with no subscription. Search base price includes up to 10 results. `lite` / `instant` are $4/1k; `auto` / `fast` are $7/1k; results above 10 are $1/1k; `/contents` is $1/1k pages and bills `text`, `highlights`, and `summary` as separate content types. `/answer` is $5/1k. Deep Search: `deep-lite` and `deep` $12/1k, with page-stated latency of about 4 seconds and 4–15 seconds; `deep-reasoning` $15/1k and 12–40 seconds. Those seconds are `vendor_stated`. The free tier resets to $10 of credits each month. `includeDomains` and `excludeDomains` allow up to 1,200 entries; the search reference says to use those fields instead of a `site:` operator. MCP is `https://mcp.exa.ai/mcp`.

Tavily bills credits. Pay as you go is $0.008/credit, with 1,000 free credits per month. Search `basic` is 1 credit and `advanced` is 2. Extract bills successful URLs only: basic is 1 credit per 5 URLs, advanced is 2 credits per 5. Map is 1 credit per 10 pages, or 2 with `instructions`. Crawl equals map plus extract. Research `mini` is 4–110 credits per request; `pro` is 15–250. Monthly plans run from Project at $30 / 4,000 credits to Growth at $500 / 100,000 credits.

Parallel's current integration path is `/v1/search` and `/v1/extract`. Search `turbo`/`fast` is $1/1k including 10 results; `basic`/`advanced` is $5/1k; extra results are $1/1k. The page states 200 ms–3 s for Search, labeled `vendor_stated`. Extract is $1/1k URLs, stated 1–20 s. Decisions `fast` is $1/1k for up to 100 questions, stated 200 ms–1 s. Image Search is $1/1k for `fast` and $5/1k for `advanced`, up to 20 results. Task processors run from `lite` at $5/1k successful runs to `ultra8x` at $2,400/1k. Failed runs are not billed. Responses tiers are $10, $50, and $250 per 1,000 successful requests.

## How a commerce agent should route

This is architecture guidance, not a measured winner.

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

Checkout amount, return window, and replenishment stop stay in this repo's authority layer. Retrieval only supplies citable evidence. If sources conflict, or `content` is split by `...`, do not confirm a deadline and do not change the authorization.

## Parameter appendix, official docs, 2026-11-01

These fields come from public references. This repo did not call them.

Exa `POST /search`: current `type` values are `auto`, `lite`, `deep-lite`, and `deep`, with legacy `instant`, `fast`, and `deep-reasoning`. `numResults` defaults to 10 and the public maximum is 100. Domain filters are `includeDomains` and `excludeDomains`, 1,200 each. Do not put `site:` in the query. Dates are `startPublishedDate` and `endPublishedDate`. `category` includes `news`, `company`, and `people`. Freshness is `contents.maxAgeHours`: omit means cache if present, otherwise live; `0` is always live; `-1` is cache only; a positive value caps at 720 hours. `lite` cannot live-fetch. Seconds on the pricing page and quickstart are `vendor_stated`: `lite` about 450 ms, `auto` about 1 second, `deep-lite` about 4 seconds, `deep` 4–15 seconds, `deep-reasoning` 12–40 seconds. No p95 SLA is published. Agent fixed `effort` is $0.012, $0.025, $0.10, $0.50, and $1.00 per request for `minimal` through `xhigh`.

Tavily `POST /search`: `search_depth` is `ultra-fast`, `fast`, `basic`, or `advanced`. The credits overview names only basic at 1 credit and advanced at 2. The OpenAPI marks `fast` and `ultra-fast` as 1 credit as well. `max_results` max is 20. `topic` is `general`, `news`, or `finance`. `time_range` plus `start_date` / `end_date` is the news window. `max_age_hours` follows the same shape as Exa: `0` live, `-1` never live. `include_domains` max 300, `exclude_domains` max 150. A non-paying plan that sets `max_age_hours` can receive HTTP 434. No reproducible latency number is published, only a qualitative order.

Parallel's current path is `/v1/search` and `/v1/extract`. `mode` defaults to `advanced`, the $5/1k tier, not `fast`. Public modes reduce `max_results` above 20 down to 20. `source_policy` include and exclude domains share a 200-entry cap. `after_date` belongs to Search only. Live fetch `max_age_seconds` minimum is 600. The EU endpoint `https://eu.parallel.ai` supports only `basic`. `turbo` is English and Japanese only. Mode times are `vendor_stated`: `turbo` about 200 ms, `fast` about 700 ms, `basic` about 1 second, `advanced` about 3 seconds.

Perplexity Search API, official pricing page fetched 2026-11-01: standard `POST /search` is $5 per 1,000 successful requests; `search_type: "fast"` is $1 per 1,000. One request with up to five queries is still one billing unit. Failures and HTTP 429 are not billed. This returns ranked results and snippets, not a generated answer. The Agent API `web_search` tool is a separate meter: $0.0025 standard or $0.001 Fast Search, plus model tokens. This repo did not call it.

Brave's marketing page cites a third-party AIMultiple latency table. That is not a Brave list price and not a measurement from this repo, so it is not plotted. The official pricing dashboard did not return a parseable price table on this fetch, so no Brave unit price is copied.

## Bright Data boundaries added

Each pricing card shows 5,000 requests per month. The billing docs separately describe one shared 5,000-credit pool: Unlocker, SERP, and Scraper API cost 1 credit per request or record, and Browser costs 5 credits per MB. Both are official pages. This note does not collapse them into one number. Once custom headers or cookies are enabled, failed requests are billed too.

Browser API list price: $8/GB pay as you go; Scale is $499/month and includes 71 GB. The overage rate was not in the static HTML fetched here. Web Scraper API is $1.50/1k records pay as you go, and Scale includes 384,000 records. That is not SERP's 380,000 or Unlocker's 383,000. Google `num` no longer sets the result count. Shopping is `udm=28` on the engine URL. News is `tbm=nws`. Password entry is off by default. Personalized prices behind login are outside the default allowed use. Fast SERP has no published unit price.

## Display and storage limits

These are public terms, not measurements from this repo.

- Exhibit A caps displayed grounding text at the lesser of 200 characters or the webmaster maximum, per source. The citation link has to sit near the model output. Do not paste a full Browse passage onto a checkout page.
- Image and video bytes must not be sent into the model for grounding and must not be turned into derivatives. Metadata and alt text may be used. Display only through the returned URL.
- Do not cache responses into a price database or training set. The FAQ says per-user chat history may be kept up to 30 days. The terms text fetched here says storage lasts for the period applicable law allows, not the same "30 days" sentence. Where they differ, the terms control. Treat 30 days as FAQ text.
- `AuthUserDailyUsageExceeded` exists and resets at 00:00 UTC. The numeric daily quota is not published.
- Azure credits do not pay for Web IQ. A paid subscription is required. News-publisher licensing fees are the customer's, not part of the $7/1k call price.
- The published MCP tool list has no Auto tool. Auto is REST beta only.
- The image reference has no field named `license`. The pricing page's "licensing info" line does not name a published field.

## Peer retrieval APIs, official pages, 2026-11-01

These unit prices come from public pricing pages. This repo did not call them. Latency sentences stay `vendor_stated` and are not plotted.

| Product | Role | official_list_price | Commerce constraint |
|---|---|---|---|
| Perplexity Search API | Ranked results plus snippets, not a generated answer | Standard $5/1k successful requests; fast $1/1k. Up to five queries in one request are still one unit. Agent tools are separate: web_search $0.0025, fast $0.001, fetch_url $0.0005, sandbox $0.03 per session | A successful empty result is still billed. Extracted text length does not change the Search API price. An empty snippet cannot change a price. The [overview](https://docs.perplexity.ai/docs/search/overview) says billing stays one request, but each query uses one rate-limit unit. People `max_results` maxes at 50. `max_tokens` caps at 1,000,000 and does not change the price |
| Brave Search | Own index. Web Search is for people. LLM Context is for agents | The unit price stays `not_verified`. Fetched 2026-11-02 from the [LLM Context reference](https://api-dashboard.search.brave.com/api-reference/ai/llm_context/get): `GET /v1/llm/context`. `q` is at most 600 characters and 75 words. `count` defaults to 20 and maxes at 50. `maximum_number_of_tokens` defaults to 8192, range 1024–32768. Per URL the default is 4096 and the max is 8192. At most 50 URLs. At most 3 Goggles. `context_threshold_mode` is disabled, strict, lenient, or balanced. `freshness` is pd, pw, pm, py, or `YYYY-MM-DDtoYYYY-MM-DD`. The Web Search getting-started page also says `extra_snippets=true` returns up to 5 extra excerpts per result | The pricing dashboard is still a shell, and this reference has no unit price. Web Search `count` maxes at 20. Do not mix that with the LLM Context cap of 50. The AIMultiple millisecond table on the marketing page stays out of the latency chart. Brave's claim that Bing Search APIs are retired does not override the Bing grounding price still printed on Microsoft's product page |
| Grounding with Google Search | A Gemini tool over the public web, not a raw SERP | 5,000 free Grounding Queries per month, then $14/1k. One prompt can create more than one billable query | Sample `uri` values can be Google Search URLs. That is not the retailer page |
| Grounding with Bing | The model searches Bing and returns a cited answer. Developers do not receive the raw Bing payload | Fetched from [microsoft.com/en-us/bing/apis](https://www.microsoft.com/en-us/bing/apis) on 2026-11-01: Search and Custom Search are both $14 per 1,000 transactions, 150 TPS, 1 million transactions per day. The Learn how-to page has no unit price and links here. This was not copied from Google | This is not Web IQ. Outputs are not directly accessible for other programs |
| You.com | Index search, per-page extract, and tiered research are three billing units | Fetched from [you.com/pricing](https://you.com/pricing) on 2026-11-01: Web Search Standard $5/1k calls; Contents $1/1k pages; free MCP is 100 queries/day; $10 credit = 2,000 searches. Research Lite/Standard/Deep/Exhaustive/Frontier = $12 / $50 / $100 / $450 / $1,200 per 1k. Finance Deep $110, Exhaustive $500. Latency on those cards is vendor-stated and stays out of the latency chart. “Cache hits are free” was not on this fetch | One Web Search call costs the same whether it returns 1 or 100 results. The [search reference](https://you.com/docs/api-reference/search/v1-search) says `count` is 1–100, but highlights above 50 return 422. `include_domains` maxes at 500 and `exclude_domains` at 5,000. They cannot be sent together. Contents is billed per page returned. A research tier is not a search call |
| Linkup | Search, Fetch, Research, and Extract, billed per successful call | Fetched from the [pricing page](https://docs.linkup.so/pages/documentation/platform/pricing): flash/fast/standard + `searchResults` $0.005, `sourcedAnswer`/`structured` $0.006; deep is $0.05 / $0.055. Fetch standard with no JS is $0.001, plus $0.001 with a schema. Research S/M/L/XL = $0.25 / $0.50 / $1.50 / $2.50. A professional email is topped back up to $20 each month. Failures are not billed. x402 minimum is $0.01 per request | `sourcedAnswer` is model-written. Extract is still closed beta; most completed tasks are $2–10, and `creditsUsed` in the response is the charge |
| SerpAPI | Parsed Google result pages. Monthly plans only | Fetched from [serpapi.com/pricing](https://serpapi.com/pricing): Free $0/250, Starter $25/1,000, Developer $75/5,000, Production $150/15,000, Cloud 1M $3,750/1,000,000. The page continues with higher Cloud monthly tiers. No per-search unit rate. “Cached searches are free” was not on this fetch | Do not divide a monthly plan into a fake unit price |
| Serper | Google result pages | `https://serper.dev/pricing` returned 404. The homepage fetch showed no list price. The earlier $1.00/1k and $0.30/1k figures are now `not_verified` | Not a policy page |
| Firecrawl | Credit-metered scrape and search, not a raw SERP unit price | Fetched from [pricing.md](https://www.firecrawl.dev/pricing.md): Free 1,000 credits/$0; Hobby $19 or $16/month billed annually; Standard $99 or $83; Growth $399 or $333; Scale $749 or $599. Search is 2 credits per 10 results; Scrape and Crawl are 1 credit per page. pricing.md says Interact is 2 credits per browser minute; the [billing page](https://docs.firecrawl.dev/billing) says 2–7, with prompt sessions at 7. Both stand | Search and scrape share one credit balance. Do not divide a plan into a per-call list price. The [search reference](https://docs.firecrawl.dev/api-reference/endpoint/search.md) defaults `country` to US. The `research` category changes to the Research Index on 2026-11-16. `gov` cannot be combined with other categories |
| Google Custom Search JSON API | JSON web or image results from a Programmable Search Engine | Fetched from the [overview](https://developers.google.com/custom-search/v1/overview): existing customers only, discontinued 2027-01-01. 100 free queries per day, then $5 per 1,000, capped at 10,000 queries per day. Not available to new customers | Not Gemini Grounding, and not a raw SERP |
| Claude web search | The model decides when to search. The caller receives a cited answer | Fetched from the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing): $10 per 1,000 searches on the Claude API, plus token costs. Each search is one use regardless of result count. Errors are not billed. Web fetch has no extra charge beyond tokens. Foundry supports only `web_search_20250305`, without dynamic filtering | This is not a cacheable raw passage. A model answer is not checkout authority |
| Jina Reader / Search | URL-to-Markdown, or search then Markdown | The [contact-sales](https://jina.ai/contact-sales/) page showed limits only: Reader 20 RPM without a key, 500 on free or paid, 5,000 on Premium. Search is 100 RPM on free or paid and 1,000 on Premium. Each search starts at 10,000 tokens. The dollar top-up was not on this fetch | The 7.9s and 2.5s figures are vendor-stated and stay out of the latency chart. The unit price stays `not_verified` |
| OpenAI web search | The model searches and returns a cited answer | Fetched from [pricing.md](https://developers.openai.com/api/docs/pricing): web search and image web search are $10 per 1,000 calls for all models, plus search-content tokens at model rates. Preview is $10/1k on reasoning models. Preview on non-reasoning models is $25/1k and those search-content tokens are free. gpt-4o-mini and gpt-4.1-mini non-preview bill search content as a fixed 8,000 input tokens | This is not a cacheable raw passage. A model answer is not checkout authority |
| SearchAPI | Parsed result pages. Plan cards print their own per-1k rate | Fetched from [searchapi.io/pricing](https://www.searchapi.io/pricing): 100 free requests on signup. Developer $40/10,000 and the card says $4/1k; Production $100/35,000 and $3/1k; BigData $250/100,000 and $2.5/1k; Scale $500/250,000 and $2/1k. Octo 500K through 5M is $900/$1.8, $1,500/$1.5, $2,800/$1.4, and $5,000/$1. Only HTTP 200 searches are billed. At most 20 percent of plan credits each hour | The per-1k figures are printed on the cards, not divided here. The 99.9 percent SLA stays out of the latency chart |
| DataForSEO Google Organic | SERP-priced Google organic results, not a model answer | Fetched from the [organic pricing page](https://dataforseo.com/pricing/google-serp/google-organic-serp-api): one SERP is up to 10 results. Standard $0.0006 / $0.60 per 1k; Priority $0.0012 / $1.20; Live $0.002 / $2.00. Each search operator multiplies the base by 5. The $50 minimum top-up is on the [pricing index](https://dataforseo.com/pricing), and the balance does not expire | Minute and second figures on the page are vendor-stated averages and stay out of the latency chart |
| ScrapingBee | Monthly credit plans, with a separate Google SERP endpoint | Fetched from [pricing](https://www.scrapingbee.com/pricing/): 1,000 free credits. Hobby $19/75,000; Freelance $49/250,000; Startup $99/1,000,000; Business $249/3,000,000; Business+ $599/8,000,000. Enterprise cards run from $999/14 million to $5,799/120 million. Prices exclude VAT. The [credit article](https://help.scrapingbee.com/en/article/credit-system-explained-1h2ackp/), updated 2026-08-07, says Google and Walmart light requests cost 10 credits and normal requests cost 15. Fast search is 10. Agentic search is 3,750. An HTML API call to a Google URL is 15 on classic or premium proxies and 75 on stealth | These are credits, not a dollar unit price. Do not divide a plan into a per-call list price |
| Kagi | Own-index search plus per-page extract | Fetched from [kagi.com/api/pricing](https://kagi.com/api/pricing): Search $12 per 1,000 requests; Extract $4 per 1,000 pages, up to 10 URLs per request. Invoices every 30 days or when usage reaches $100. Enterprise is quote-only | Search covers web, images, news, videos, and podcasts. Not a checkout authority page |
| Zyte | Site-tiered successful-response prices, not one unit price | Fetched from [zyte.com/pricing](https://www.zyte.com/pricing/): PAYG HTTP tiers are $0.13 / $0.23 / $0.44 / $0.70 / $1.27 per 1,000. Browser rendering runs from $1.01 to $16.08. The headline “from $0.06” is only the $500-commitment HTTP simple floor. The [docs](https://docs.zyte.com/zyte-api/pricing.html) say only successful responses are billed, standard plans are 3,000 RPM, PAYG spending is capped at $100/month, and the trial credit is $5 | The tier depends on the target site. Do not treat $0.06 as the price of every request |
| Oxylabs | SERP scraping | The `oxylabs.io` pricing URL failed at TLS on this fetch. No third-party extract was copied | The unit price stays `not_verified` |
| Browserbase | Browser infrastructure. Search is a pass-through option | Fetched from [browserbase.com/pricing](https://www.browserbase.com/pricing): Free is $0 and includes 1,000 searches. Developer $20 and Startup $99 also include 1,000, then $5/1k by default. The comparison table also prints Parallel Fast $1, Parallel Advanced $5, Exa Fast $7, and Exa Deep $12, each per 1,000. Search RPS is 2 per project on those three plans | These are pass-through rates on the Browserbase page. They do not replace Parallel or Exa list prices |
| Spider | Bandwidth plus CPU scrape pricing | Fetched from [spider.cloud/pricing](https://spider.cloud/pricing/): bandwidth $1/GB, CPU $0.0001 per minute. Failed requests cost $0. Unlimited bills concurrency, starting at $40/month for 2. Google search is not on Unlimited and stays on pay as you go | There is no per-search list price. Zero data retention is 2.5x. 10,000 RPM is a limit, not a latency |
| Scale SERP | Monthly search plans now hosted by Traject Data | `scaleserp.com/pricing` redirected to the [Traject Data pricing page](https://trajectdata.com/serp/scale-serp-api/pricing/). This fetch saw the annual view: 1,000 searches at $23/month, overage $0.038; 10,000 at $66, overage $0.0118; 50,000 at $199, overage $0.00796; 250,000 at $599, overage $0.004792; 1 million at $1,699, overage $0.003398; 5 million at $4,999, overage $0.001999. The free tier is 125 successful searches per month | The monthly-toggle prices were not in this fetch. Do not treat the annual monthly figure as the month-to-month price. The page says Traject Data joins ScraperAPI |

## Still not measured

The portal had no eval key that this research is allowed to use for metrics, and competitor keys are not in the environment. All five providers remain `not_measured`. The published 164 ms, under 1 second, under 5 sec, and 200 ms–3 s figures stay out of this repo's latency chart. The 7-card stays withheld.

Corrected 2026-11-01 23:50 +08: the Bing grounding $14/1k price was seen on [microsoft.com/en-us/bing/apis](https://www.microsoft.com/en-us/bing/apis), so it is no longer unverified. Bright Data SERP and Unlocker $1.50/$499 inclusion counts were re-fetched on their pricing pages and matched. The Brave marketing page showed no unit price. Its AIMultiple millisecond table stays out of the latency chart. The personal site remains untouched while the publish window is closed.

2026-11-02 00:05 +08: Google Custom Search JSON API and Claude web search unit prices were copied from their official pages. Jina showed RPM only, so its dollar price stays `not_verified`. `serper.dev/pricing` returned 404 again. The Brave docs pricing URL returned 403 and stays unverified.

2026-11-02 00:12 +08: OpenAI web search, SearchAPI card rates, DataForSEO Google Organic queue prices, and ScrapingBee monthly plans were copied from official pages. Monthly totals were not divided into unpublished per-call prices.

2026-11-02 00:35 +08: Kagi and Zyte official prices were recorded. Zyte's $0.06 figure is only a commitment-tier floor. The Oxylabs pricing page failed at TLS and stays `not_verified`. The site publish window is lifted and both mains are `ad980647`. This pass still does not push the site.

2026-11-02 00:40 +08: Browserbase, Spider, and the Scale SERP annual view were copied from official pages. The Scale SERP monthly toggle was not visible. The site is still not pushed.

2026-11-02 00:45 +08: Brave LLM Context parameters were copied from the official reference. The unit price is still unverified. The marketing latency table was not stored. The site is still not pushed.

2026-11-02 00:50 +08: ScrapingBee Google-search credit costs were copied from the official help article. Monthly plans are still not divided into a dollar unit price. The Serper homepage still has no list price. Oxylabs still fails at TLS. The site is still not pushed.

2026-11-02 00:55 +08: Exa, Tavily, and Parallel search-reference parameters were recorded. Tavily fast and ultra-fast are also 1 credit. The site is still not pushed.

2026-11-02 01:00 +08: The You.com search reference says `count` is 1–100, and highlights above 50 return 422. `include_domains` maxes at 500 and `exclude_domains` at 5,000. They cannot be sent together. The Firecrawl search reference defaults `country` to US and says the `research` category changes to the Research Index on 2026-11-16. Kagi docs confirm `POST /api/v1/search` and MCP at `https://mcp.kagi.com/mcp`, with no printed query-length cap. The site is still not pushed.

2026-11-02 01:35 +08: The Perplexity Search overview says one request can hold 5 queries and is still billed once, but each query uses one rate-limit unit. Web `max_results` is 1–20. People search maxes at 50. `max_tokens` and `max_tokens_per_page` are each 1 to 1,000,000 and change the payload, not the price. Bright Data's “under 1 second” sentence was not stored. The Linkup quickstart confirms `https://api.linkup.so/v1/search`. The site is still not pushed.

2026-11-02 02:35 +08: The Brave Web Search reference says `count` defaults to 20 and maxes at 20, and it applies only to web results. LLM Context count still maxes at 50. `offset` maxes at 9, and pages can overlap. `extra_snippets` adds up to 5 excerpts. The unit price stays unverified. Tavily Extract accepts up to 20 URLs. Basic extract is 1 credit per 5 successful URLs. Advanced is 2. HTTP 200 can still include `failed_results`. The Exa quickstart says the default is 10 results, `numResults` maxes at 100, and search has no pagination. The site is still not pushed.
