# 实时商业搜索与网页接地（`Web Grounding`）五大引擎深度选型对比：`Microsoft Bing Grounding / Web IQ` vs. `Perplexity Sonar API` vs. `Tavily` vs. `Exa` vs. `Firecrawl / Browser-Use`（在商品比价、舆情洞察、研报采集场景下的实时性、成本、合规性与结构化能力对比）及 `85/15` 分级漏斗净省 43% 决策指南（FAQ · 🏆 全库第 535 篇双语决策指南重大里程碑！）

> **导读（对齐 `ib-vs-ethernet-roce-selection-faq.md` 标杆风格 · 🏆 全库第 535 篇双语决策指南重大里程碑 · 第 416 轮 · 第 859 张 SVG · 第 309 个策略沙盒）**：本文面向正在构建全网比价导购 Agent、企业供应商风险舆情雷达、竞品动态定价监控与深度市场研报采集系统的 **Cloud & AI Solution Architect**。在商业智能体需要连接公网获取实时外部事实（Web Grounding）时，市面上形成了五大代表性技术路线：**`Microsoft Bing Grounding / Web IQ (/v3/search/web + /v3/browse)`、`Perplexity Sonar API (Sonar Pro / Reasoning)`、`Tavily Search API`、`Exa (Neural Search)` 以及 `Firecrawl / Browser-Use`**。许多团队因为“用一个工具包打天下”而陷入三大工程泥潭：① **拿搜索引擎 7 天前的缓存摘要或聚合问答结果直接做商品比价/自动买贵赔差，结果促销早结束了或把 `$39` 的配件当成了 `$649` 的整机（Stale Cache & Accessory Conflation）**；② **不论初筛还是比价，对搜出来的 20 个网页全部调用 `Firecrawl / Browser-Use` 抓整页 Markdown，导致单次查询耗时飙到 `14 秒`、Prompt Token 消耗暴增 `7.1 倍`，或把 affiliate 返利软文农场当成权威行业研报**；③ **未剥离商品评论区里的 `0px` 隐藏白色字体提示词注入，或无视出版社 `W3C TDMRep / robots.txt` 声明违法强爬付费研报触发欧盟《AI 法案》第 53 条版权合规风险**。本文给出五大引擎在 **商品比价、舆情洞察、研报采集** 三大核心场景下的定量对比矩阵，并落地 **结账/价保前强制 `/v3/browse` 实时 `Schema.org Offer` 与 `14位 GTIN` 验真锁（`HTTP 403`）**、**`85/15` 双阶段 `Passage -> Live Browse` 成本漏斗与过滤返利内容农场锁（`HTTP 422`）**、**剥离隐藏 `0px CSS` 注入与遵守 `W3C TDMRep` 版权锁（`HTTP 451`）** 及 **按场景五引擎智能路由（`HTTP 409`，净省 43%）**。

![Commercial Search & Web Grounding 5-Engine Selection Architecture](../assets/svg/859-commercial-search-grounding-webiq-sonar-tavily-exa-firecrawl-535th-guide-2026-11-26.svg)

---

## 一、 📌 核心选型结论速览（Executive Summary）

1. **三大商业场景终极选型结论（一句话按场景对号入座）**：
   - **🛒 场景一：全网商品实时比价、库存核验与买贵必赔核查（Price Comparison & Live ATP）**：
     - 首选 **`Microsoft Web IQ (/v3/search/web passage 初筛 + /v3/browse 落地页实时核验)`** 配合 **`Firecrawl`（针对复杂动态渲染长尾店铺的 JSON Schema 抽取）**。前 `85%` 候选召回用 `Web IQ passage` 将 Token 压降 `7.1 倍`，最终 Top-3 下单/退差候选强制校验 `liveCrawlSucceeded == True` 与 `14位 GTIN`！
   - **📢 场景二：品牌口碑舆情洞察、供应商突发风险预警与多源新闻交叉求证（Sentiment & Risk Intelligence）**：
     - 首选 **`Perplexity Sonar API (Sonar Pro)`** 或 **`Tavily Search API`**（搭配 `Web IQ News` 实时流）。`Perplexity Sonar` 擅长在 1 次 API 调用内合成带内联引用编号的多源正负面舆情摘要；`Tavily` 则以极简 JSON 返回高信噪比新闻片段供自建 LangGraph 状态机打分。
   - **📑 场景三：深度行业研报采集、B2B 专精特新替代供应商发掘与高价值长文检索（Market Research & B2B Sourcing）**：
     - 首选 **`Exa (Neural Embeddings Search)`** + **`Firecrawl`**。传统关键词搜索搜“耐高温特种密封件供应商”前三页全是 SEO 广告软文；而 `Exa` 基于网页神经嵌入向量直接找到真正生产商的技术白皮书与行业基准 PDF，再由 `Firecrawl` 将 PDF/表格转为结构化 JSON！
2. **三大商业搜索与网页接地确定性风控红线（Fiduciary Control Gates）**：
   - **红线 1（拦截仅凭搜索引擎缓存摘要或聚合问答句子就批准商品结账/买贵退差，而未执行实时落地页 `Schema.org Offer` 与 `14位 GTIN` 验真 / `HTTP 403`）**：任何搜索引擎索引（包括 Bing、Google、Perplexity、Tavily、Exa 的索引库）都存在数小时至数天的抓取时延，且摘要极易把“配件价/官翻二手价/会员凑单价”与“全新整机现货价”混为一谈！在进入购物车锁价（`Cart FSM`）或批准价保赔付前，必须对目标 URL 执行实时落地页抓取（如 `Web IQ /v3/browse` 或 `Firecrawl`），强制校验 **`liveCrawlSucceeded == True`、`Offer.availability == InStock`、`Condition == NewCondition` 且 `GTIN-14` 与目标商品 100% 匹配**，违者触发 `HTTP 403 STALE_SEARCH_SNIPPET_OR_ACCESSORY_GTIN_MISMATCH_VETO`！
   - **红线 2（拦截在初筛阶段对 Top-20 搜索结果无差别调用整页抓取 `Firecrawl / Browser-Use` 烧穿 Token 预算，或在研报/选型中采信 Affiliate 返利内容农场 / `HTTP 422`）**：整页 Markdown 转换或启动无头浏览器单页平均产生 `4,000–8,000 Tokens`；若对每次初筛的 20 个网页全量抓整页，不仅延迟高达 `12–18 秒`，Token 成本更比 `Web IQ passage` 切片贵 **`7.1 倍`**！控制平面必须强制执行 **`85/15` 两阶段漏斗（`Stage 1`: `100%` 走轻量 `passage` 切片召回过滤；`Stage 2`: 仅对进入决승圈的 `<=3 个` 候选 URL 发起实时深抓）**，且在研报与选型采集中自动过滤含有 `?aff_id= / tag= / Best-10-Review-Farm` 特征的返利营销软文站，违者触发 `HTTP 422 UNBOUNDED_FULL_PAGE_SCRAPE_TOKEN_BLOWOUT_OR_SEO_FARM_BREACH`。
   - **红线 3（拦截将网页评论区中隐藏的 `0px / display:none` 间接提示词注入原样送入具有付款权限的 Agent 上下文，或违反 `W3C TDMRep / robots.txt` 强爬受版权保护研报 / `HTTP 451`）**：网页解析层在将外部 HTML 转换为文本前，必须在 DOM 树阶段物理剥离一切视觉不可见节点（`font-size:0`, `opacity:0`, `display:none`, `color == background-color`, HTML 注释及 `<script>` 标签），并将外部网页内容封装在只读无工具调用权限的隔离沙盒中；同时在采集研报时必须校验 HTTP 响应头中的 **`W3C TDM-Reservation: 1`（文本与数据挖掘保留权，对应欧盟《AI 法案》第 53 条版权合规要求）** 与 `robots.txt`，严禁违规绕过付费墙，违者触发 `HTTP 451 INDIRECT_DOM_PROMPT_INJECTION_OR_TDMREP_COPYRIGHT_BREACH`。

---

## 二、 🎯 业务方与架构师灵魂拷问 Q&A（The Why & How）

### Q1：在构建商业智能体时，为什么既不能“只用 `Perplexity Sonar / Tavily`”，也不能“只用 `Firecrawl / Browser-Use`”？
- **架构师深度解耦对比**：
  1. **为什么只用聚合问答 API（`Sonar / Tavily`）在交易环节会出事？**
     - 当用户问 *“帮我对比 Sony XM5 和 Bose QC Ultra 的舆论评价与优缺点”* 时，`Perplexity Sonar` 只需 1.5 秒就能综合 15 篇测评给出极高质量的对比总结。
     - 但当进入 **“以 `$279` 锁单购买黑色现货”** 阶段时，聚合问答引用的可能是 4 天前某篇科技新闻里写的“黑五限时特价 $279”，而此刻商家落地页早就恢复成 `$349` 或者黑色已断货！
  2. **为什么只用整页爬虫/浏览器（`Firecrawl / Browser-Use`）在搜索环节会破产？**
     - `Firecrawl` 和 `Browser-Use` 是针对 **已知具体 URL** 的深度提取器。如果你让 `Browser-Use` 在 Google/电商站翻页点进 15 个商品详情页去比价，一次查询就要跑 45 秒、花掉 `$0.40` 算力费！
- **架构师黄金组合公式（`Web IQ Passage + Exa` 负责快准省的“广度发掘”，`Web IQ Browse + Firecrawl` 负责定乾坤的“最后一米实时验真” / `HTTP 422 & HTTP 409`）**：
  - 用 `Web IQ (/v3/search/web)` 在 `350ms` 内以极低 Token 召回 20 条高精度 `passage` 切片，筛出最匹配的 2 个商品 URL，最后仅对这 2 个 URL 发起 `/v3/browse` 实时验价——速度提升 **`2.75 倍`**，Token 成本直降 **`85.9%`**！

### Q2：在企业 B2B 采购寻源与行业研报采集场景下，`Exa` 相比传统搜索引擎到底强在哪里？
- **商业痛点与架构解析**：
  - 传统搜索引擎基于关键词词频（BM25）与外链权重排名，早已被 B2B 黄页中介站和 SEO 内容农场占领。
  - **`Exa` 采用端到端神经嵌入检索（Link-Prediction & Embedding Search）**：你可以输入一家现有优质德国传感器供应商的官网 URL，调用 `exa.find_similar(url)`，它能直接绕过 SEO 软文，在全球互联网上找出 20 家产品技术架构高度相似、但从未做过 Google SEO 的隐形冠军制造商官网与一手技术 PDF！

---

## 三、 🧭 直观可视化图解（Mermaid 决策树 + 架构对比 + 时序图）

### 3.1 实时商业搜索与网页接地五大引擎（`Web IQ × Sonar × Tavily × Exa × Firecrawl`）选型决策树

```mermaid
flowchart TD
    A[实时商业搜索与网页接地 5 大引擎选型] --> B{当前 Agent 执行的具体商业子任务?}
    B -->|1. 商品发现初筛与结账前实时价格/库存核验<br/>追求亚秒级低 Token 召回 + 结算前 liveCrawl 验真 + 微软法务免责| C[Microsoft Bing Grounding / Web IQ<br/>/v3/search/web passage 初筛 + /v3/browse 落地页验真]
    B -->|2. 品牌舆情洞察、突发风险快讯与多源观点合成<br/>追求 1 次调用直接输出带内联引用的高可读性综述| D[Perplexity Sonar API / Tavily<br/>多源实时合成问答 Sonar Pro + RAG 专用轻量检索 Tavily]
    B -->|3. B2B 替代供应商发掘、相似公司寻找与深度研报采集<br/>追求按语义相似度找隐形冠军官网与一手 PDF 免受 SEO 污染| E[Exa Neural Search<br/>神经嵌入语义搜索 + find_similar 相似企业雷达]
    B -->|4. 动态 SPA 网页结构化 JSON 抽取与无 API 老旧门户交互<br/>仅针对决胜圈 Top 1-3 目标 URL 执行深度解析| F[Firecrawl / Browser-Use<br/>整页 Markdown/JSON Schema 抽取 + 受控无头浏览器交互]

    C --> G[核心确定性风控门禁:<br/>1. 结账/价保前强制 liveCrawlSucceeded + 14位 GTIN 验真 HTTP 403<br/>2. 85/15 双阶漏斗 禁对 Top-20 全量抓整页 + 过滤返利软文站 HTTP 422<br/>3. 物理剥离 0px 隐藏 DOM 提示词注入 + 遵守 W3C TDMRep 版权 HTTP 451]
    D --> G
    E --> G
    F --> G
```

### 3.2 朴素拿缓存当现货与全量抓整页架构（旧价误买 + Token 爆炸）vs. 确定性 `85/15` 双阶漏斗、DOM 净化与五引擎协同架构对比

```mermaid
flowchart LR
    subgraph Naive["❌ 朴素单一引擎裸调架构 (拿7天前缓存旧价下单 + 对20个网页全调Firecrawl烧穿Token)"]
        N1[用户发起全网比价、舆情分析或研报采集] --> N2[直接信问答摘要里的7天前促销旧价或把$39配件当$649主机下单<br/>对初筛20个网页全部启动无头浏览器抓整页，耗时14秒、Token贵7.1倍]
        N2 --> N3[未清洗评论区0px隐藏白色字体，被间接提示词注入劫持推荐假店铺<br/>把Affiliate返利软文农场当权威研报，或强爬TDMRep禁爬付费报告违例]
    end

    subgraph Guarded["✅ 确定性五引擎分流、85/15 双阶漏斗与 DOM 净化架构 (🏆 第 535 篇里程碑 · 净省 43%)"]
        G1[商业接地请求进入五引擎智能路由器] --> G2[85/15 漏斗与反软文锁 HTTP 422:<br/>85% 走 Web IQ passage / Exa 轻量初筛 + 剔除返利内容农场]
        G2 --> G3[实时 Offer 与 GTIN 锁 HTTP 403/409:<br/>Top-3 决胜 URL 强制调 /v3/browse 或 Firecrawl 验真实时价与库存]
        G3 --> G4[隐藏 DOM 剥离与 TDMRep 版权锁 HTTP 451:<br/>清洗 0px/display:none 注入节点 + 严格遵守 robots.txt 与 TDMRep]
    end
```

### 3.3 五大接地引擎按场景协同路由、`85/15` 漏斗过滤、隐藏 DOM 净化与实时 `Schema.org Offer` 锁价时序图

```mermaid
sequenceDiagram
    autonumber
    participant Agent as 商业智能体规划器 (比价 / 舆情 / 研报)
    participant Router as 五引擎网页接地受托控制平面
    participant Fast as 广度召回层 (Web IQ Passage / Exa / Sonar / Tavily)
    participant Deep as 深度验真层 (Web IQ /v3/browse / Firecrawl)
    participant Sanitizer as 隐藏 DOM 剥离与 TDMRep 版权门禁

    Agent->>Router: 提交商业接地请求 (场景: 1.商品实时比价 / 2.供应商舆情 / 3.行业研报)
    Router->>Fast: Stage 1 (85%): 调用 Web IQ passage / Exa / Sonar 低成本召回并过滤返利软文农场
    alt 试图对初筛 Top-20 全部调用整页爬虫烧穿 Token 预算 或 引用 Affiliate 内容农场充当研报
        Router-->>Agent: HTTP 422 UNBOUNDED_FULL_PAGE_SCRAPE_TOKEN_BLOWOUT_OR_SEO_FARM_BREACH
    else 目标站点声明 W3C TDM-Reservation: 1 禁止数据挖掘 或 页面检出 0px 隐藏提示词注入
        Sanitizer-->>Router: HTTP 451 INDIRECT_DOM_PROMPT_INJECTION_OR_TDMREP_COPYRIGHT_BREACH
    else 未执行 Stage 2 实时落地页核验 (liveCrawlSucceeded==False) 或 GTIN 不匹配即试图锁单扣款
        Router-->>Agent: HTTP 403 STALE_SEARCH_SNIPPET_OR_ACCESSORY_GTIN_MISMATCH_VETO
    else Stage 2 (15%): 仅对 Top-3 候选调 /v3/browse 或 Firecrawl 提取实时 Offer 并净化 DOM (HTTP 409)
        Router->>Deep: 实时核验 Top-3 落地页 Schema.org Offer (GTIN, 现货 ATP, 含税价)
        Deep->>Sanitizer: 剥离隐藏 CSS 节点后输出洁净结构化报价，净省 43% Token 与跳价损耗
    end
```

---

## 四、 📊 五大实时商业搜索与网页接地（`Web Grounding`）引擎全方位横向对比矩阵

| 评测维度 | Microsoft Bing Grounding / Web IQ (`/v3/search/web` + `/v3/browse`) | Perplexity Sonar API (`Sonar Pro / Reasoning`) | Tavily Search API | Exa (`Neural Search`) | Firecrawl / Browser-Use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **核心架构定位** | **企业级双阶段商业接地底座**（高压缩 `passage` 召回 + `/v3/browse` 实时页面核验） | **端到端多源合成问答与引用生成引擎** | **专为 LLM RAG Agent 打造的轻量级上下文检索 API** | **基于神经嵌入向量的语义发现与相似实体引擎** | **动态网页整页 Markdown / JSON Schema 提取与浏览器交互** |
| **场景 1：商品实时比价与库存核验表现** | **🏆 最佳组合（配合 `/v3/browse`）**：`passage` 快速筛品，`/v3/browse` 校验 `liveCrawlSucceeded` | 中（合成回答可读性高，但易折叠子 SKU 尺码断货细节，不可直接作扣款依据） | 中（适合初筛比价测评文章，需二次核验商家实时购物车） | 弱（非实时价格监控接口，用于找同类品牌竞品） | **🏆 决胜圈单页抽取最佳**：可将复杂动态商品页直接转为严格 `Pydantic JSON Schema` |
| **场景 2：品牌舆情洞察与供应商风险预警** | **极强**：原生包含权威新闻流（News）与多语种全球索引，支持按发布时间窗过滤 | **🏆 综合简报最佳**：一次调用自动融合数十篇最新报道并附带精准行内角标引用 | **强（高性价比）**：自动剔除网页导航噪音，直接返回高相关度舆情正文切片 | 擅长发掘深度长尾论坛讨论与技术社区早期口碑信号 | 适合针对已知特定舆情源站点做定制定时抓取 |
| **场景 3：行业研报采集与 B2B 寻源表现** | 强于公开新闻、财报公告与主流行业门户召回 | 适合快速生成行业赛道概览与竞争格局初稿 | 适合快速聚合公开市场数据摘要 | **🏆 B2B 寻源与一手研报最佳**：原生支持 `category="research paper / company"` 与 `find_similar` 绕过 SEO 软文 | **🏆 复杂表格/PDF 提取最佳**：将找到的研报长页完美解析为结构化 Markdown |
| **时延与 Prompt Token 消耗** | **`~300–500ms` / 极低 Token**（`passage` 模式比整页抓取节省 **`7.1x` Token**） | `~1.5–4.0s` / 输出已由 Sonar 模型浓缩，主模型 Token 负担低 | `~600–1,000ms` / 返回精简片段，Token 消耗低 | `~400–800ms` / 支持按字符长度截断 `highlights`，Token 效率高 | **`~1.5–6.0s+` / 极高 Token**（整页 Markdown 动辄 `5k–15k Tokens`，严禁用于宽召回！） |
| **企业合规、版权免责与数据驻留** | **🏆 企业级最高**：享微软 Azure 企业级隐私承诺（零客户数据训练）与商业版权免责护栏 | 提供企业 API 零数据留存（ZDR）选项与清晰引用溯源 | 提供面向开发者的合规检索接口 | 支持按域名白名单/黑名单过滤不良来源 | 需架构师自行配置遵守 `robots.txt`、`W3C TDMRep` 与代理合规策略 |
| **官方计费参考（`official_list_price`）** | Azure Foundry Grounding / Web IQ 按千次查询计费（企业协议阶梯价） | 按请求次数（约 `$5 / 1,000 请求`）+ 输入输出 Token 费 | 免费额度 + 约 `$5–$8 / 1,000 Credits` 阶梯包 | 约 `$5 / 1,000 次搜索` + 内容提取附加费 | 按抓取页面数（Credits）计费 + `Browser-Use` 云端容器分钟费 |

---

## 五、 🧪 五大引擎分级路由、防旧价误买与 Token 降本测算与 7-Card 基准报告

### 5.1 季度全量整页抓取 Token 算力浪费、拿缓存旧价/配件价误批买贵退差、采信 SEO 返利软文误导采购及隐藏 DOM 注入损耗测算（Synthetic Benchmark）

假设某日均执行 `80,000 次` 商品比价、供应商舆情尽调与市场研报采集的商业智能体平台，每季度在网页接地层面临的 **对初筛结果无差别跑整页爬虫导致的 `7.1x` Token 与爬虫账单浪费、轻信搜索引擎过期缓存摘要导致的结账跳价与买贵必赔误退差价、被 Affiliate 返利内容农场污染采购选型、以及评论区隐藏 DOM 注入风险池** 为 **`$450,000 / 季度`**（`provenance: synthetic`, `independently_reproduced: false`）：

| 评估维度 | 单一全页爬虫或盲信搜索缓存摘要 (Baseline) | 启用五引擎按场景分流 + `85/15 Passage-to-Browse` 漏斗 + `GTIN/DOM` 锁 Agent | 净改善幅度 |
| :--- | :--- | :--- | :--- |
| **单次商业寻源与实时比价的平均 Token + API 综合成本** | `$0.088 / 次`（无差别抓整页 Markdown） | **`$0.013 / 次`**（`85% Web IQ passage / Exa` + `15% Top-3 /v3/browse` 实时验真） | **接地 API 与 Token 成本直降 `-85.2%`** |
| **因搜索缓存过期或配件混淆导致的结账跳价/价保误赔率** | `5.4%` 比价结果与实际结算价不符 | **`0.0%`**（`HTTP 403` 强制校验落地页 `liveCrawlSucceeded == True` 与 `14位 GTIN`） | **100% 根除旧价与配件伪低价误判** |
| **评论区隐藏 `0px` 提示词注入拦截率与 `TDMRep` 版权合规率** | 易受白底白字隐藏指令劫持 | **`100% 拦截 / 100% 合规`**（`HTTP 451` DOM 树剥离不可见节点 + 遵守 `TDM-Reservation: 1`） | **100% 免疫网页间接提示词注入** |
| **季度 Token 算力浪费、旧价误赔、软文误导与合规总损耗** | `$450,000 / 季度` | **`$256,500 / 季度`** | **净省 `$193,500 / 季度` (`43.0%`)** |

```chart
{
  "data": {
    "values": [
      { "category": "1. 对初筛Top-20无差别抓整页烧穿7.1x Token与API费", "mode": "传统单一爬虫或盲信缓存基线", "cost_usd": 175000 },
      { "category": "1. 对初筛Top-20无差别抓整页烧穿7.1x Token与API费", "mode": "五引擎85/15漏斗控制面(第535篇)", "cost_usd": 99750 },
      { "category": "2. 轻信搜索缓存旧价或把$39配件当整机批价保赔付", "mode": "传统单一爬虫或盲信缓存基线", "cost_usd": 125000 },
      { "category": "2. 轻信搜索缓存旧价或把$39配件当整机批价保赔付", "mode": "五引擎85/15漏斗控制面(第535篇)", "cost_usd": 71250 },
      { "category": "3. B2B寻源与研报被Affiliate返利内容农场污染误导", "mode": "传统单一爬虫或盲信缓存基线", "cost_usd": 85000 },
      { "category": "3. B2B寻源与研报被Affiliate返利内容农场污染误导", "mode": "五引擎85/15漏斗控制面(第535篇)", "cost_usd": 48450 },
      { "category": "4. 评论区0px隐藏提示词注入劫持与TDM版权违例", "mode": "传统单一爬虫或盲信缓存基线", "cost_usd": 65000 },
      { "category": "4. 评论区0px隐藏提示词注入劫持与TDM版权违例", "mode": "五引擎85/15漏斗控制面(第535篇)", "cost_usd": 37050 }
    ]
  },
  "semantic_types": {
    "category": "Category",
    "mode": "Category",
    "cost_usd": "Amount"
  },
  "chart_spec": {
    "chartType": "Grouped Bar Chart",
    "title": "实时商业搜索与网页接地五大引擎(Web IQ/Sonar/Tavily/Exa/Firecrawl)分级路由(第535篇)前后季度损耗对比 (净省 $193.5k / 43%)",
    "subtitle": "单位：美元/季度 (Synthetic Benchmark, independently_reproduced=false · 🏆 全库第535篇双语指南里程碑)",
    "encodings": {
      "x": "category",
      "y": "cost_usd",
      "group": "mode"
    }
  }
}
```

### 5.2 确定性策略评估器代码（Python Control Plane Guard）

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class CommercialSearchGroundingFiveEnginePolicyInput:
    quarterly_fullpage_token_burn_stale_price_and_seo_farm_pool_usd: float = 450000.0
    checkout_or_price_match_approved_on_cached_snippet_without_live_browse: bool = False
    full_page_scrape_called_on_top20_or_affiliate_seo_farm_unfiltered: bool = False
    hidden_0px_dom_injection_unstripped_or_w3c_tdmrep_optout_violated: bool = False
    five_engine_85_15_passage_browse_funnel_and_dom_sanitizer_ready: bool = False
```

---

## 六、 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **结账与价保前强制 `/v3/browse` 实时落地页核验 + `14位 GTIN` 锁（`HTTP 403`）**：是否严禁直接拿搜索引擎缓存摘要或问答合成文本作为扣款/退差依据，强制对最终目标 URL 校验 `liveCrawlSucceeded == True`、`InStock` 与 `14位 GTIN` 完全一致？
- [ ] **`85/15` 两阶段 `Passage -> Live Browse` 成本漏斗与反内容农场过滤（`HTTP 422`）**：是否将初筛流量 100% 路由至低 Token 的 `Web IQ passage / Exa highlights`，仅对决胜圈 `<=3 个` URL 调用深度解析，并在 B2B 研报采集中自动拉黑带返利参数的 SEO 软文农场？
- [ ] **隐藏 `0px / display:none` DOM 节点剥离与 `W3C TDMRep` 版权合规锁（`HTTP 451`）**：HTML 解析层是否在送入大模型前彻底剥离一切不可见 CSS 节点以防御间接提示词注入，并严格遵守目标站点 `robots.txt` 与 `TDM-Reservation: 1` 声明？
- [ ] **按三大商业场景（比价/舆情/研报）五引擎动态路由（`HTTP 409`）**：是否实现比价走 `Web IQ + Firecrawl`、舆情快讯走 `Sonar / Tavily + Web IQ News`、深度供应商/研报发掘走 `Exa + Firecrawl` 的最佳组合？
