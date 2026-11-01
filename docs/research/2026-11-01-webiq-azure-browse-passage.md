# Web IQ Browse passage 与 Azure 账户模板（2026-11-01）

🌐 **Language / 语言导航**: **中文 (当前)** | **[English](2026-11-01-webiq-azure-browse-passage.en.md)** | **[2026-10-26 密封演示](2026-10-26-webiq-agentic-commerce-demo.md)**

> **状态更新（同日）**：实验室订阅后来创建了 `webiq-qichen2-bench`。本节「0 个账户 / 未创建资源」只描述当时的只读清点，Azure 状态已被 [Web IQ 搜索竞品矩阵](2026-11-01-webiq-search-competitive.md) 取代。密封指标不改。

## 发现

已有的 Agentic Commerce × Web IQ 演示（`lab/webiq_commerce_demo.py`，密封于 2026-10-26）继续作为可运行工作台。本笔记只补齐官方 Browse 契约，并给出按需部署模板。写本笔记时没有创建 Azure 资源，也没有重测密封指标。

官方 [Browse REST API](https://learn.microsoft.com/en-us/web-iq/reference/browse)（文档日期 2026-10-30）把 `contentFormat=passage` 定为推荐接地格式。`passage` 必须带 1..1000 字符、非空白的 `query`。`text` / `html` / `markdown` 仍是全文格式，需要全文权限。Browse 本身仍是 AppID 按申请开通，不是自助默认能力。

## Azure

只读 Resource Graph 查询当时登录的 Microsoft 租户，结果是 **0 个** `Microsoft.WebIQ/accounts`。Web IQ 需要付费订阅，Azure credits 不能用于创建账户。因此本次没有执行 `az resource create`，也没有把订阅 ID 写进模板。

按需模板：[`infra/webiq-account.bicep`](../../infra/webiq-account.bicep)

- 类型：`Microsoft.WebIQ/accounts@2026-06-01-preview`
- `location=global`，`kind=WebIQ.Grounding`，`sku=G3`
- `properties.statisticsEnabled=false`
- 账户名在部署时传入

干跑脚本 [`scripts/webiq-account-dry-run.ps1`](../../scripts/webiq-account-dry-run.ps1) 只打印契约，不创建资源。

## 引擎增量

- `BROWSE_CONTENT_FORMATS` 增加 `passage`。
- `browse(..., query=)`：`passage` 拒绝空白 query；任何格式拒绝超过 1000 字符的 query。
- 离线夹具按 query 截取 passage，不把缺失证据编造成退货期限。
- 新增 `ground_return_policy_passage()`，用于退货政策场景的 passage 接地。
- 既有全文 Browse 默认值保持 `markdown`，2026-10-26 密封场景不改口径。

密封指标（P95 240ms、18/18、12/12、1.52s vs 4.18s）仍标记为 `sealed_demo` / 2026-10-26，不是本次重测。

## 发布

个人站新增独立路径，不改首页：`workshops/webiq-azure/`。实时调用仍是可选的 `--live` + `WEBIQ_API_KEY`，默认离线夹具可运行。
