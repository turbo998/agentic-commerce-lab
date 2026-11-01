# Web IQ 搜索竞品矩阵（2026-11-01）

🌐 **Language / 语言导航**: **中文 (当前)** | **[English](2026-11-01-webiq-search-competitive.en.md)** | **[Browse passage 笔记](2026-11-01-webiq-azure-browse-passage.md)**

![状态卡：账户已创建，延迟未测](webiq-search-competitive-2026-11-01.svg)

## 发现

实验室付费订阅已能创建 Web IQ 账户。G3 账户 `webiq-qichen2-bench`（`Microsoft.WebIQ/accounts@2026-06-01-preview`，`location=global`，`kind=WebIQ.Grounding`，`statisticsEnabled=false`）在 2026-11-01 创建成功。API 密钥尚未绑定，Bright Data、Exa、Tavily、Parallel 的密钥也不在本机环境里。因此五家供应商全部标记为 `not_measured`。缺失延迟没有写成 0。7-card 延迟卡在出现真实 `summary.json` 之前不下发。

2026-10-26 密封数字（P95 240ms、18/18、12/12、1.52s vs 4.18s）仍是 `sealed_demo`，不是这次 bake-off。

## 账户状态

- 资源组 `rg-webiq-bench`，区域 `southeastasia`。账户位置是 `global`。
- `provisioningState=Succeeded`。
- 没有把订阅 ID、内部 ID、网关主机名或登录邮箱写入本笔记。
- 门户 https://webiq.microsoft.ai/profiles 才能签发 `x-apikey`。Azure CLI 不能为 `https://api.microsoft.ai/.default` 取令牌。
- Browse 仍是 AppID 按申请开通。Auto 在 beta 期间不计费。
- 没有创建 Bright Data、Exa、Tavily 或 Parallel 账户。

同日早些时候的 [Browse passage 笔记](2026-11-01-webiq-azure-browse-passage.md) 记录的是当时只读清点「0 个账户」。那条 Azure 状态被本笔记取代。密封演示数字不改。

## 官方标价，不是分数

标签一律是 `official_list_price`。核验日 2026-11-01。这些数字不能画成延迟条。

| 供应商 | 官方标价 | 来源 | 不计入测量的说法 |
|---|---|---|---|
| Web IQ | `/web`、`/video`、`/news`、`/images` 每 1,000 次 $7；`/browse` 每 1,000 次 $1。生效日 2026-10-16，页面更新 2026-10-29。 | [定价](https://learn.microsoft.com/en-us/web-iq/resources/pricing) | Auto beta 不计费，不是延迟。 |
| Bright Data SERP | 每月 5,000 次免费；按量每 1,000 次成功请求 $1.50；Scale $499/月含 380,000 次，超出每 1,000 次 $1.30。页面写明展示价可能是本币估算，USD 为结算价。 | [SERP 定价](https://brightdata.com/pricing/serp) | 「under 1 second」是营销句，不是测量。 |
| Exa | lite/instant $4/1k，auto/fast $7/1k，contents 每种内容 $1/1k 页，answer $5/1k，monitors $15/1k。deep-lite/deep $12/1k，deep-reasoning $15/1k。Agent 固定档 $0.012–$1.00/次。免费额度 $10，每月 1 日重置。 | [定价](https://exa.ai/pricing) | 页面上的秒数是厂商自述，不进延迟图。 |
| Tavily | basic search 1 credit，advanced 2 credits。按量 $0.008/credit。文档表自带单价：Project $0.0075，Bootstrap $0.0067，Startup $0.0058，Growth $0.005。Research pro 15–250 credits，mini 4–110。每月 1,000 免费 credits。 | [API credits](https://docs.tavily.com/documentation/api-credits) | 失败的抽取和 Map 不计费。无本次延迟。 |
| Parallel | turbo/fast $1/1k，basic/advanced $5/1k，额外结果 $1/1k。extract $1/1k URL。Task lite $5/1k 成功运行，ultra8x $2,400/1k。Responses medium $50/1k。 | [定价](https://docs.parallel.ai/getting-started/pricing) | 页面上的 200 ms–3 s 是 `vendor_stated`。本次抓取没有看到请求默认 mode。 |

## 离线契约

[`lab/webiq_search_bakeoff.py`](../../lab/webiq_search_bakeoff.py) 不打开网络。三条密封问题覆盖退货窗口、可引用价格页、以及是否存在应停止补货的公开召回。缺密钥时 `latency` / `success` / `citation_check` 都是 `not_measured`。密钥存在时记录 `credential=present`、`call=not_called`，仍然不打付费请求。

每日研究任务已加入强制支柱：Web IQ 对比 Bright Data、Exa 与主流网页搜索。夜班检查要核验这一支柱。缺凭证必须保持 `not_measured`。

## 架构边界对比：Microsoft Web IQ 原始 Passage 返回 vs. Foundry Grounding with Bing Search

根据 2026-11-01 核验的 Microsoft Learn 官方文档（[Web IQ Browse Reference](https://learn.microsoft.com/en-us/web-iq/reference/browse)、[Web IQ Error Handling](https://learn.microsoft.com/en-us/web-iq/reference/error-handling) 与 [Foundry Agents Web Grounding Overview](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-overview)）：

| 维度 | Microsoft Web IQ (`/v3/search/web`, `/v3/browse`) | Microsoft Foundry Grounding with Bing Search | 对 Agentic Commerce 的架构含义 |
|---|---|---|---|
| **检索正文对调用方代码可见性** | **直接返回给调用方代码**（`results[].content` / `contentFormat="passage"` 默认 $\le 3000$ 字符） | **不对开发者返回原始检索块**（仅在微软托管边界内把检索结果喂给模型，只向调用方返回最终回答与引用链接） | 高保障商业智能体必须在进入 LLM 前做确定性提示词注入清洗（`PROMPT_INJECTION_RE`）与价格摘要哈希比对（`CheckoutStore`），因此**必须使用 Web IQ** 而非黑盒 Grounding |
| **`retryAfter` 双格式契约** | `AuthUserThrottled` (429) / `InternalServerError` (500) 返回相对时长 `"60s"`；而 `Browse 202` 与 `TooManyOnDemandCrawls` (**同样是 HTTP 429!**) / `520` / `523` / `524` 返回 ISO-8601 UTC 时间戳 `"2026-10-30T01:01:00Z"` | 托管在 Foundry Agent 服务内部 | 调用方绝不能仅凭 `status == 429` 假设 `retryAfter` 格式；已由 `lab/webiq_commerce_demo.py` 的 `parse_webiq_retry_after()` 与 `classify_webiq_error_response()` 强制校验 |

## 读法

数字分四类，不能混用。

| 标签 | 含义 |
|---|---|
| `official_list_price` | 官方标价页上的单价。不是延迟，也不是质量分。 |
| `vendor_published_benchmark` | 厂商自己公布、对手匿名的对比。`independently_reproduced=false`。 |
| `vendor_stated` | 营销或文档里的速度/成功率句子，没有可复现的查询集。 |
| `not_measured` | 本仓库没有打这笔调用。缺失值不是 0。 |

本仓库 2026-10-26 密封数字仍只属于当时的离线演示，不进入这张竞品表。

## 四类产品，不要当成同一种搜索

| 类型 | 返回什么 | 适合商业代理的哪一步 | 不适合 |
|---|---|---|---|
| 索引接地 | 排序后的 passage、引用 URL、抓取时间 | 不知道 URL 时找证据，再交给模型 | 把摘要本身当成零售商标价 |
| URL 抽取 | 指定页面的 passage 或全文 | 已经有政策页、商品页 URL | 发现新召回新闻 |
| SERP 抓取 | 搜索引擎结果页的广告、自然结果、购物位 | 监控某市场的搜索展示和比价入口 | 作为改价或退货期限的唯一权威 |
| 答案 API | 模型已经写好的答案加引用 | 低风险摘要 | 结账授权。商业裁决必须留在本仓库的 authority 层 |

## Web IQ：公开契约

来源核验日 2026-11-01。REST 基址 `https://api.microsoft.ai/v3`。MCP 为 `https://api.microsoft.ai/v3/mcp`，工具名 `web`、`news`、`images`、`videos`、`browse`，参数与对应 REST 相同。工具列表随 AppID 允许的服务变化。

Azure 资源只做计量和账单，不在请求路径上。应用调用的是 `api.microsoft.ai`。身份是 Web IQ AppID，不是资源本身。生产 AppID 默认 15 QPS，提额要走支持单。密钥创建不收费，同一 AppID 的密钥和 Entra 绑定共享配额。Entra 客户端凭证是生产推荐；`x-apikey` 适合原型。没有 Private Link、VNet 或 IP 允许名单。条款把服务排除在 Microsoft 产品和服务数据处理附录之外，也没有区域数据驻留承诺。查询文本默认进运维日志；Zero Query Logging 不是自助开关。响应内容不能缓存来建衍生数据集。入站查询不做 PII 脱敏，含个人信息的工作负载要在调用前清洗。

Web IQ 不生成最终答案，也不执行页面里的指令。间接提示注入仍要由模型、Prompt Shields 和本仓库的商业裁决层处理。索引归一化不保证去掉隐藏指令。LinkedIn 结果目前被排除。Browse 命中排除 URL 时返回 HTTP 403。

### 端点与参数

| 端点 | 状态 | 关键参数 | 上限 | 接地字段 |
|---|---|---|---|---|
| `POST /v3/search/web` | GA | `query`、`maxResults`、`language`、`region`、`location`、`contentFormat`、`maxLength`、`safeSearch` | query 1000 字符；`maxResults` 默认 10、最大 50 | `webResults[].url/content/crawledAt/lastUpdatedAt/contentTier`，另有 `querySignals.freshness`、`riskLevel` |
| `POST /v3/search/news` | GA | 同上，无 `safeSearch` | `maxResults` 最大 20 | `newsResults[].source/url/content/crawledAt/lastUpdatedAt` |
| `POST /v3/search/images` | GA | `aspectRatio`、`color`、`imageSize`、`watermarkFree`、像素边界、`safeSearch` | `maxResults` 默认且最大 30 | `url`、`hostPageUrl`、`caption`。定价页写有许可信息；本次抓到的字段表没有单独的 license 字段 |
| `POST /v3/search/videos` | GA | `freshness`、`resolution`、`duration`、`embeddable`、`enablePlaylist`、`safeSearch` | `maxResults` 默认且最大 30 | `summary`、`moments`、`publishedBy`、`viewCount` |
| `POST /v3/browse` | GA，AppID 按申请 | `url` 必填；`passage` 时 `query` 必填；`liveCrawl`=`none`\|`fallback`；`renderDynamicPages` 只在 fallback 时生效 | query 1000 字符；无全文权限时 content 最多 3000 字符 | 单页 `content`。段落按相关度选取，按原页顺序用 `...` 拼接，可在句中截断 |
| `POST /v3/auto` | Beta，未计费，AppID 按申请 | `mode`=`fast`\|`advanced`；`responseFilter`=`web/news/timezone/weather/images/videos`；`maxResponseLength` 默认 30000，夹紧到 1500..500000 | 契约可能变 | 分类型 evidence 加该条自己的 citations |

`contentFormat=passage` 是接地推荐值。没有全文权限时，`text` / `html` / `markdown` 返回 HTTP 403 `AuthContentFormatForbidden`。有全文权限时，Web 默认 `html`，News 默认 `text`，`maxLength` 最大 500000。Web 不返回独立 `snippet`。Web 没有日期过滤；FAQ 明确说硬日期过滤通常损害相关度，新闻场景应改用 News，而不是在 Web 上滤日期。`site:` / `-site:` 可用，但会降低相关度，而且 `site:` 可能绕过 SafeSearch 的成人过滤。更大的域名允许/拒绝名单不是客户自助功能。

`contentTier` 有三档：`standard`、`entitled`（客户自带出版商许可）、`premium`（超出标准服务、可能另计费）。商业代理在采纳证据前要读这一字段，不能假设每次 $7/1k 已包含 premium 内容。

`liveCrawl=none` 只返回索引；URL 不在索引中则 Browse 404。`fallback` 才会现抓。动态渲染不是默认能力。

### 厂商公布的基准，不是本仓库复现

[Learn benchmarks](https://learn.microsoft.com/en-us/web-iq/concepts/benchmarks)（页面更新 2026-10-13）公布：

- 接地满意度：Web IQ 79.05；匿名对手 75.70、75.61、73.96、72.89、67.53、64.71。3000 条全球盲测，10 条结果，每条 10000 字符或等价配置。
- P95：Web IQ 164 ms；下一档 406 ms；最慢 2090 ms。五个数据中心平均值，独立查询以避免缓存，同样是 10 条 / 10000 字符。

对手没有点名，不能映射成 Bright Data 或 Exa。这组数字标签是 `vendor_published_benchmark`，`independently_reproduced=false`。本仓库不下发把它画成自己的 7-card。

### 门户观察（已脱敏）

2026-11-01 已登录的门户是试用档，到期日显示 2028-02-01，配额 100 QPS。允许的垂直域包括 Web、Videos、Browse、News、Images、Classic，以及 beta：Places、Auto、Commerce、Finance、Sports、AutoSuggest。当时没有 API 密钥，本轮也没有创建。界面写明评测密钥只供轻度个人使用，不能用于内部服务、自动化或指标采集。因此即使垂直域里有 Commerce beta，也不用这把评测密钥跑 bake-off。

公开 FAQ 仍写：今天没有独立的 finance、sports、weather API，这些主题走 Web Search。门户 beta 名称不是公开 REST 契约。公开端点索引里没有 Commerce。

## Bright Data：先选产品，再谈价格

[产品选择页](https://docs.brightdata.com/product-selector) 把搜索和抓页拆开：

| 目标 | 产品 | 返回 |
|---|---|---|
| Google、Bing、Yandex、DuckDuckGo 等结果页 | SERP API | 解析后的自然结果、广告、酒店、航班等。请求体是 `zone` + 搜索引擎 URL，`format` 为 `raw`，`data_format` 可为 `parsed_light` 或 markdown |
| 已知 URL 的 HTML，无点击 | Web Unlocker | 原始 HTML。文档写明它不是 Playwright/Puppeteer 交互产品 |
| 点击、表单、截图 | Browser API | 浏览器会话 |
| Amazon 等已有爬虫的结构化商品 | Web Scraper API | 预建 JSON，不是通用搜索 |

SERP 官方文档写支持 Google、Bing、DuckDuckGo、Yandex、Baidu、Yahoo、Naver。地理和设备参数在引擎 URL 上（如 `hl`、`gl`），不是一个统一的 `region` 字段。异步模式下只对发送请求计费，取回响应不计。定价页 FAQ 写响应时间 under 5 sec。介绍页另写 under 1 second，并指出 Fast SERP 要向客户经理申请。两句都标 `vendor_stated`，互相不能当成同一次测量。

标价，2026-11-01 抓取，USD 为结算价，页面展示价可能是本币估算：

| 产品 | 免费 | 按量 | Scale |
|---|---|---|---|
| SERP | 每月 5,000 次 | $1.50 / 1,000 次成功请求 | $499/月含 380,000 次，超出 $1.30 / 1,000 |
| Web Unlocker | 每月 5,000 次 | $1.50 / 1,000 次成功请求 | $499/月含 383,000 次，超出 $1.30 / 1,000 |

SERP 与 Unlocker 的包含量不同，不能抄成同一个 380,000。

## Exa、Tavily、Parallel

Exa 官方标价页：无订阅、预充值。搜索基础价含最多 10 条。`lite` / `instant` $4/1k；`auto` / `fast` $7/1k；超出 10 条每 1,000 条 $1；`/contents` $1/1k 页，且 `text`、`highlights`、`summary` 分内容类型计费。`/answer` $5/1k。Deep Search：`deep-lite` 与 `deep` $12/1k，文档写延迟约 4 秒和 4–15 秒；`deep-reasoning` $15/1k，12–40 秒。这些秒数是定价页上的 `vendor_stated`。免费档每月重置 $10 额度。Search 的 `includeDomains` / `excludeDomains` 最多 1200 项，文档要求用这两个字段而不是在 query 里写 `site:`。MCP 在 `https://mcp.exa.ai/mcp`。

Tavily 按 credit。按量 $0.008/credit；每月 1,000 免费 credits。Search `basic` 1 credit，`advanced` 2 credits。Extract 按成功 URL 计，失败不收费：basic 每 5 个成功 URL 1 credit，advanced 每 5 个 2 credits。Map 每 10 页 1 credit，带 `instructions` 为 2。Crawl = Map + Extract。Research `mini` 每次 4–110 credits，`pro` 每次 15–250 credits。月费档从 Project $30 / 4,000 credits 到 Growth $500 / 100,000 credits。

Parallel 新集成要用 `/v1/search` 和 `/v1/extract`。Search `turbo`/`fast` $1/1k，含 10 条；`basic`/`advanced` $5/1k；额外结果 $1/1k。文档把 Search 时间写成 200 ms–3 s，标 `vendor_stated`。Extract $1/1k URL，文档时间 1–20 s。Decisions `fast` $1/1k，最多 100 个问题，文档时间 200 ms–1 s。Image Search `fast` $1/1k、`advanced` $5/1k，最多 20 条。Task 按 processor，从 `lite` $5/1k 次成功运行到 `ultra8x` $2400/1k，失败不收费。Responses 按推理档 $10 / $50 / $250 每 1,000 次成功请求。

## 商业代理怎么选

这是架构建议，不是实测胜负。

| 场景 | 先调用 | 原因 | 不要 |
|---|---|---|---|
| 不知道商品页在哪，要可引用的现价 | Web IQ `/web`，`contentFormat=passage`，必要时 `site:` 零售商域；再对返回 URL 调 `/browse` | 搜索负责发现，Browse 负责页内证据。`crawledAt` 用来判断证据新旧 | 用 SERP 摘要直接改授权金额 |
| 已经有退货政策 URL | Web IQ `/browse`，`passage` + 非空 `query`，`liveCrawl=fallback` 仅当索引 404 | $1/1k，且段落按问题截取。无全文权限时最多 3000 字符 | 为了一页政策去买 SERP |
| 召回或安全新闻，决定是否停止补货 | Web IQ `/news`，读 `source`、`lastUpdatedAt`、`crawledAt` | Web 没有日期过滤；FAQ 要求新闻走 News | 把旧网页 passage 当成“今天没有召回” |
| 商品图、是否可嵌视频 | `/images`、`/videos` | 有宿主页、尺寸、水印和嵌入字段 | 用图片结果代替价格证据 |
| 多意图问题 | 拆成多次 `/web` 或 `/news`。Auto beta 可做分类型 evidence，但未计费且契约会变 | FAQ：一次 Web 请求只处理一个查询 | 把整段用户话术塞进一个 1000 字符 query |
| 要看某国 Google 购物位、广告、排名 | Bright Data SERP，`gl`/`hl` 放在引擎 URL | 这是结果页监控，官方用例包含 price comparison | 把它当成出版商页面的全文 |
| 已知 URL 但被拦截，要原始 HTML | Bright Data Web Unlocker，或 Exa `/contents`、Tavily Extract、Parallel Extract | Unlocker 解决抓取；Exa/Tavily/Parallel 卖的是页面文本。价格单位不同 | 用 Unlocker 做点击式结账。文档写明它不是浏览器交互 |
| 要点击、登录后页面、截图 | Bright Data Browser API | 产品选择页的明确边界 | 用 Browse `renderDynamicPages` 假装能完成表单。它只在 liveCrawl fallback 时做动态渲染 |

结账金额、退货期限、补货熔断仍由本仓库的 authority 层决定。检索层只提供可引用证据。证据冲突或 `content` 被 `...` 截断时，不确认期限、不改授权。

## 参数附录（官方文档，2026-11-01）

这些字段来自各家公开参考，不是本仓库调用结果。

Exa `POST /search`：`type` 当前值为 `auto`、`lite`、`deep-lite`、`deep`，遗留值 `instant`、`fast`、`deep-reasoning`。`numResults` 默认 10，公开最大 100。域名过滤用 `includeDomains` / `excludeDomains`，各最多 1200，不要在 query 里写 `site:`。日期用 `startPublishedDate` / `endPublishedDate`。`category` 包括 `news`、`company`、`people`。新鲜度用 `contents.maxAgeHours`：省略则有缓存用缓存，否则现抓；`0` 总是现抓；`-1` 只读缓存；正数最大 720 小时。`lite` 不能现抓。定价页和快速入门的秒数是 `vendor_stated`：`lite` 约 450 ms，`auto` 约 1 秒，`deep-lite` 约 4 秒，`deep` 4–15 秒，`deep-reasoning` 12–40 秒。没有公布 p95 SLA。Agent 固定 `effort`：`minimal` $0.012、`low` $0.025、`medium` $0.10、`high` $0.50、`xhigh` $1.00 每次请求。

Tavily `POST /search`：`search_depth` 为 `ultra-fast`、`fast`、`basic`、`advanced`。积分总览只写 basic 1、advanced 2；OpenAPI 把 `fast` 和 `ultra-fast` 也标成 1 credit。`max_results` 最大 20。`topic` 为 `general`、`news`、`finance`。`time_range` 和 `start_date` / `end_date` 是新闻窗口。`max_age_hours` 语义与 Exa 同类：`0` 现抓，`-1` 不现抓。`include_domains` 最多 300，`exclude_domains` 最多 150。未付费计划设置 `max_age_hours` 可能返回 434。文档没有公布可复现的延迟数字，只有定性排序。

Parallel 新集成必须用 `/v1/search` 和 `/v1/extract`。`mode` 默认是 `advanced`，也就是 $5/1k 那一档，不是 $1 的 `fast`。公开模式 `max_results` 超过 20 会被降到 20。`source_policy` 的包含和排除合计最多 200 个域。`after_date` 只属于 Search。现抓的 `max_age_seconds` 最小 600。欧盟端点 `https://eu.parallel.ai` 只支持 `basic`。`turbo` 只支持英语和日语。模式时间是 `vendor_stated`：`turbo` 约 200 ms，`fast` 约 700 ms，`basic` 约 1 秒，`advanced` 约 3 秒。

Perplexity Search API，官方定价页 2026-11-01：标准 `POST /search` $5/1k 成功请求；`search_type: "fast"` $1/1k。一次请求里最多 5 个 query 仍算 1 个计费单位。失败和 429 不计费。这是索引结果加 snippet，不是生成答案。Agent API 的 `web_search` 工具是另计：$0.0025/次标准，$0.001/次 Fast Search，再加模型 token。本仓库没有调用。

Brave 营销页引用了第三方 AIMultiple 延迟表。那不是 Brave 标价，也不是本仓库测量，不进入延迟图。官方定价仪表盘本次没有返回可解析的价目表，所以 Brave 单价保持未抄录。

## Bright Data 补充边界

定价卡片各自写每月 5,000 次。计费文档另写一个共享的 5,000 credit 池，Unlocker、SERP、Scraper API 各 1 credit 一次，Browser 按 5 credits/MB。两处都是官方页，本次不把它们合成一个数字。自定义 header 或 cookie 打开后，失败请求也计费。

Browser API 标价：按量 $8/GB；Scale $499/月含 71 GB。超出单价本次没有从静态页解析到。Web Scraper API 按量 $1.50/1k 记录，Scale 含 384,000 条，与 SERP 的 380,000、Unlocker 的 383,000 都不同。Google `num` 已不能设定结果条数。购物位是 URL 上的 `udm=28`，新闻是 `tbm=nws`。密码输入默认关闭。登录后的个性化价格不在默认可采集范围。Fast SERP 单价没有公布。

## 展示与存储限制

Learn FAQ 与条款还有几条商业代理必须遵守的边界，标签是公开条款，不是本仓库测量。

- 展示给用户的接地文本，条款 Exhibit A 写的是每条来源不超过 200 字符或站长允许的更短上限。引用链接要靠近模型输出。不能把整段 Browse passage 原样贴进结账页。
- 图片和视频本体不能送进模型做接地，也不能做成衍生图。可用的是元数据和 alt 文本。展示只能用返回的 URL。
- 不能把响应缓存成价格库或训练数据。FAQ 写每用户聊天记录最多 30 天；本次抓到的条款正文写的是适用法律允许的期限，不是同一句 “30 天”。两处不一致时，以条款为准，30 天只当 FAQ 表述。
- 有每日用量错误 `AuthUserDailyUsageExceeded`，UTC 零点重置。具体每日配额没有公布。
- Azure 额度不能支付 Web IQ。需要付费订阅。新闻出版商许可费由客户支付，不在 $7/1k 里。
- MCP 已公布的工具没有 Auto。Auto 只在 REST beta。
- 参考里没有名为 `license` 的图片字段。定价页的 “licensing info” 没有对应到已公布字段名。

## 同级检索 API（官方页，2026-11-01）

这些单价来自各家公开定价页，本仓库没有调用。延迟句子仍是 `vendor_stated`，不进图。

| 产品 | 角色 | official_list_price | 商业代理注意 |
|---|---|---|---|
| Perplexity Search API | 排序结果加 snippet，不是生成答案 | 标准 $5/1k 成功请求；fast $1/1k。一次最多 5 个 query 仍算 1 次。Agent 工具另计：web_search $0.0025，fast $0.001，fetch_url $0.0005，sandbox $0.03/会话 | 成功但空结果仍计费。抽取长度不改变 Search API 价格。空 snippet 不能改价 |
| Brave Search | 自有索引。仪表盘未渲染出价格 | 2026-11-01 再次抓取定价仪表盘仍是空壳。先前的 $5/1k 与 Answers $4/1k 降为 `not_verified` | 不要把研究提取当成标价 |
| Grounding with Google Search | Gemini 的公开网页接地工具，不是原始 SERP | 每月 5,000 次免费，之后 $14/1k Grounding Queries。一次 prompt 可以产生多次计费查询 | 样本里的 `uri` 可以是 Google 搜索 URL。不能当零售商页面 |
| Grounding with Bing | 模型搜 Bing 后返回带引用的答案。开发者拿不到原始 Bing 载荷 | 2026-11-01 直接抓取 [microsoft.com/en-us/bing/apis](https://www.microsoft.com/en-us/bing/apis)：Search 与 Custom Search 都是 $14/1,000 transactions，150 TPS，每天 100 万次。Learn how-to 页没有单价，链接指向该页。不是从 Google 抄来的 | 这不是 Web IQ。输出不能直接拿去别的程序用 |
| You.com | 索引检索、按页抽取、分层研究，三种计费单位 | 2026-11-01 直接抓取 [you.com/pricing](https://you.com/pricing)：Web Search Standard $5/1k calls；Contents $1/1k pages；免费 MCP 每天 100 次；$10 额度 = 2,000 次搜索。Research Lite/Standard/Deep/Exhaustive/Frontier = $12 / $50 / $100 / $450 / $1,200 per 1k。Finance Deep $110、Exhaustive $500。卡片上的延迟是厂商自述，不进延迟图。先前“缓存命中不计”本次页面未见 | 一次 Web Search 返回 1 条或 100 条都算 1 次。Contents 按返回页计费。研究档不是搜索档 |
| Linkup | Search / Fetch / Research / Extract，按成功请求扣余额 | 直接抓取 [定价页](https://docs.linkup.so/pages/documentation/platform/pricing)：flash/fast/standard + `searchResults` $0.005，`sourcedAnswer`/`structured` $0.006；deep 为 $0.05 / $0.055。Fetch standard 无 JS $0.001，schema 再加 $0.001。Research S/M/L/XL = $0.25 / $0.50 / $1.50 / $2.50。职业邮箱每月补到 $20。失败不扣费。x402 最低 $0.01/请求 | `sourcedAnswer` 是模型写的。Extract 仍是 closed beta，多数完成任务 $2–10，以返回的 `creditsUsed` 为准 |
| SerpAPI | Google 结果页解析，只有月费档 | 直接抓取 [serpapi.com/pricing](https://serpapi.com/pricing)：Free $0/250 次，Starter $25/1,000，Developer $75/5,000，Production $150/15,000，Cloud 1M $3,750/1,000,000。页面继续列出更高 Cloud 月费档。没有单次单价。先前“缓存免费”本次未见 | 不要把月费除以次数当成标价 |
| Serper | Google 结果页 | `https://serper.dev/pricing` 本次 404。首页抓取没有标价。先前 $1.00/1k 与 $0.30/1k 降为 `not_verified` | 不能当政策页 |
| Firecrawl | 按 credit 的抓取和搜索，不是原始 SERP 单价 | 直接抓取 [pricing.md](https://www.firecrawl.dev/pricing.md)：Free 1,000 credits/$0；Hobby $19 或年付折合 $16/月；Standard $99 或 $83；Growth $399 或 $333；Scale $749 或 $599。Search 2 credits/10 条；Scrape/Crawl 1 credit/页。定价表写 Interact 2 credits/浏览器分钟，[计费文档](https://docs.firecrawl.dev/billing) 写 2–7，prompt 会话为 7。两页并存，不合并 | 搜索和抓取共用一个 credit 余额。不要把月费除成单次标价 |
| Google Custom Search JSON API | 可编程搜索的 JSON 网页或图片结果 | 直接抓取 [overview](https://developers.google.com/custom-search/v1/overview)：仅存量客户，2027-01-01 停服。每天 100 次免费，超出 $5/1,000 次，付费上限每天 10,000 次。新客户不可开通 | 不是 Gemini Grounding，也不是原始 SERP |
| Claude web search | 模型决定何时搜索，调用方拿到带引用的答案 | 直接抓取 [定价页](https://platform.claude.com/docs/en/about-claude/pricing)：Claude API 每 1,000 次搜索 $10，另加 token。无论返回几条都算 1 次。出错不计费。web fetch 没有额外费用，只计 token。Foundry 只支持 `web_search_20250305`，没有 dynamic filtering | 这不是可缓存的原始 passage。不能把模型答案当成结账依据 |
| Jina Reader / Search | URL 转 Markdown，或搜索后转 Markdown | [contact-sales](https://jina.ai/contact-sales/) 只看到限额：Reader 无密钥 20 RPM，免费/付费 500，Premium 5,000。Search 免费/付费 100 RPM，Premium 1,000。Search 每次至少 10,000 tokens。美元充值价本次页面没有 | 7.9s 与 2.5s 是厂商自述，不进延迟图。单价保持 `not_verified` |

## 仍未测

门户没有可用的评测密钥，竞品密钥也不在环境里。五家调用状态仍是 `not_measured`。厂商公布的 164 ms、under 1 second、under 5 sec、200 ms–3 s 都不进入本仓库延迟图。7-card 继续暂缓。

2026-11-01 23:50 +08 更正：Bing grounding 的 $14/1k 已在 [microsoft.com/en-us/bing/apis](https://www.microsoft.com/en-us/bing/apis) 看到，不再是未复核。Bright Data SERP 与 Unlocker 的 $1.50/$499 包含量也在官方定价页再次确认。Brave 营销页没有单价，其上的 AIMultiple 毫秒表不进延迟图。个人站发布窗口仍未解除，不改站点。

2026-11-02 00:05 +08：Google Custom Search JSON API 与 Claude web search 的单价已从官方页写入。Jina 只核到 RPM，美元充值价仍是 `not_verified`。`serper.dev/pricing` 再次 404。Brave 文档定价 URL 返回 403，维持未复核。
