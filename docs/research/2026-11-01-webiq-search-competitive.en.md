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
| Exa | Lite / instant search $4 per 1,000 for up to 10 results; auto / fast $7 per 1,000; contents $1 per 1,000 pages; extra results $1 per 1,000. | [Pricing](https://exa.ai/pricing) | No latency from this run. |
| Tavily | Basic search 1 credit, advanced search 2 credits; pay as you go $0.008 per credit; 1,000 free credits per month. | [API credits](https://docs.tavily.com/documentation/api-credits) | No latency from this run. |
| Parallel | Turbo / fast $1 per 1,000 including 10 results; basic / advanced $5 per 1,000; extract $1 per 1,000 URLs. | [Pricing](https://docs.parallel.ai/getting-started/pricing) | The page's 200 ms–3 s range is `vendor_stated`, not a measurement from this repo. |

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
| Perplexity Search API | Ranked results plus snippets, not a generated answer | Standard $5/1k successful requests; fast $1/1k. Up to five queries in one request are still one unit | Sonar Chat Completions support ended 2026-09-27. An empty snippet cannot change a price |
| Brave Search | Own index. Web, LLM Context, images, news, videos | $5/1k requests, with $5 of credits per month. Answers are $4/1k plus tokens | A direct fetch of the pricing dashboard returned a shell. This $5 comes from that official pricing URL and was not re-rendered in this session |
| Grounding with Google Search | A Gemini tool over the public web, not a raw SERP | 5,000 free Grounding Queries per month, then $14/1k. One prompt can create more than one billable query | Sample `uri` values can be Google Search URLs. That is not the retailer page |
| Grounding with Bing | The model searches Bing and returns a cited answer. Developers do not receive the raw Bing payload | Unit price not re-verified on the how-to page fetched here. Do not copy Google's $14 onto Bing. Bing Search APIs retired 2025-08-11 | This is not Web IQ. The FAQ does not map the two products together |
| You.com Web Search | Index plus optional full page | Web Search $5/1k for up to 100 results. Full-page live crawl $1/1k pages. Cache hits are free | Cite Contents or `full_page` before a price change. Do not stop at Answer |
| Linkup | Index retrieval, optional scrape and answer | flash/fast/standard `searchResults` are $0.005 per successful call. Deep `searchResults` is $0.05. Failures are not billed | `sourcedAnswer` is model-written. It is not the decision record |
| SerpAPI | Parsed Google result pages | Monthly plans. No published per-search unit rate. Do not divide a plan into a fake unit price. Cached searches are free | Use it to find the official URL, then fetch that page |
| Serper | Google result pages | Prepaid packs from $1.00/1k credits at 50k down to $0.30/1k at 12.5M. The public parameter reference returned 404 | Same limit as SerpAPI. Not a policy page |
| Firecrawl | Search with optional page extract | Search is 2 credits per 10 results, rounded up. Scrape credits are extra. Credits are not converted here into an unpublished dollar unit | A snippet cannot decide replenishment or a return window |

## Still not measured

The portal had no eval key that this research is allowed to use for metrics, and competitor keys are not in the environment. All five providers remain `not_measured`. The published 164 ms, under 1 second, under 5 sec, and 200 ms–3 s figures stay out of this repo's latency chart. The 7-card stays withheld.
