# Stage 1674：`source_monitor` 增加 Stripe SPT 稳定事实提取

[English](2026-10-31-stripe-spt-facts.en.md) |
[当日日报](../../research/daily/2026-10-31.md) |
[上一阶段](2026-10-31-source-monitor-noise-filter.md)

**结论：**在 [`scripts/source_monitor.py`](../../scripts/source_monitor.py) 增加
`stripe_spt_facts(body)`，为 `stripe-spt` 来源提取可复核的稳定事实并写入 `policy_facts` /
`policy_change`，将“正文协议信号”与“内容哈希漂移”分层观测，避免把单纯 hash 变化直接视作发布变化。

## 1. 为什么需要这一步

Stage 1673 已处理 `expires_at` 秒级抖动噪声，但仍有“hash changed”与“是否协议变化”的解释空档。
Stage 1674 补齐 selected-facts 层，让 `stripe-spt` 与 `stripe-mcp` 一样具备结构化事实对比：

- `api_version`（如 `2026-09-30.preview`）
- 支持国家列表规模与内容摘要（`supported_country_count` + `supported_country_codes_sha256`）
- 关键能力标记（`recurring_interval`、`shared_payment.granted_token.deactivated`）

## 2. 代码变化

1. 新增 `stripe_spt_facts(body)`：
   - 校验文档中 `Stripe-Version` 预览版本标记且必须唯一；
   - 解析 `### View all supported countries` 列表；
   - 产出 `parser_version="stripe-spt-facts-v1"` 与稳定事实字段。
2. 新增 `previous_source_facts(...)`，按 `source_id + parser_version` 回溯上一份可用事实；
   `previous_policy_facts(...)` 保留为 `stripe-mcp` 包装器，兼容既有调用。
3. `main()` 现在同时为 `stripe-mcp` 与 `stripe-spt` 注入上一期 facts 对照，
   统一写入 `policy_change`（`baseline/unchanged/changed/unknown`）。
4. `policy_scope` 文案更新为同时覆盖 MCP 与 SPT selected facts。

## 3. 测试与验证

- 更新 [`tests/test_source_monitor.py`](../../tests/test_source_monitor.py)：
  - 新增 `stripe_spt_facts` 正向提取与缺失字段拒绝测试；
  - 新增 `previous_source_facts` 的 source/parser 精确匹配测试。
- 通过：
  - `python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts -v`（`24/24`）
  - Stage 1652–1674 回归（`529/529`）。

## 4. 当日快照结果（01:07 BJT）

`research/daily/2026-10-31-sources.json` 最新结果：

- `stripe-spt` 仍可见 `change="changed"`（相对前一日 hash 基线），但 selected facts 首次落盘：
  - `api_version=2026-09-30.preview`
  - `supported_country_count=34`
  - `supported_country_codes_sha256=6ae0a508...054133`
  - `has_recurring_interval=true`
  - `has_deactivated_webhook_event=true`
- `policy_change="baseline"`（首日建立 SPT facts 基线），后续可据此识别真正事实变化。

