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
| Exa | lite / instant 搜索每 1,000 次 $4，最多 10 条结果；auto / fast 每 1,000 次 $7；contents 每 1,000 页 $1；额外结果每 1,000 条 $1。 | [定价](https://exa.ai/pricing) | 无本次延迟。 |
| Tavily | basic search 1 credit，advanced search 2 credits；按量 $0.008/credit；每月 1,000 免费 credits。 | [API credits](https://docs.tavily.com/documentation/api-credits) | 无本次延迟。 |
| Parallel | turbo / fast 每 1,000 次 $1，含 10 条结果；basic / advanced 每 1,000 次 $5；extract 每 1,000 个 URL $1。 | [定价](https://docs.parallel.ai/getting-started/pricing) | 页面上的 200 ms–3 s 标为 `vendor_stated`，不是本仓库测量。 |

## 离线契约

[`lab/webiq_search_bakeoff.py`](../../lab/webiq_search_bakeoff.py) 不打开网络。三条密封问题覆盖退货窗口、可引用价格页、以及是否存在应停止补货的公开召回。缺密钥时 `latency` / `success` / `citation_check` 都是 `not_measured`。密钥存在时记录 `credential=present`、`call=not_called`，仍然不打付费请求。

每日研究任务已加入强制支柱：Web IQ 对比 Bright Data、Exa 与主流网页搜索。夜班检查要核验这一支柱。缺凭证必须保持 `not_measured`。

## 未测

实时 bake-off 仍被挡住：Web IQ 密钥要在门户绑定；竞品密钥不在环境变量里。在此之前不下发延迟 7-card。
