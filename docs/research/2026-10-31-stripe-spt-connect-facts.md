# 2026-10-31：Stage 1676 —— source-monitor 的 Stripe SPT Connect 稳定事实提取

[English](2026-10-31-stripe-spt-connect-facts.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1674 已为 `stripe-spt`（seller 视图）建立 selected facts，但 `stripe-spt-connect` 仍仅依赖正文 hash。  
为避免 Connect 页面对示例文本或排版微调造成误判，Stage 1676 在保持离线监测边界下补充 **Connect 视图 parser-backed facts**。

## 实现

### 1) `scripts/source_monitor.py`

- 抽取公共国家列表逻辑 `_extract_supported_country_codes(text)`，供 seller/connect 复用。
- 新增 `stripe_spt_connect_facts(body)`，提取：
  - `supported_country_count` / `supported_country_codes_sha256`
  - `has_connect_platforms_section`
  - `has_network_business_profile`
  - `has_shared_payment_granted_token`
  - `has_stripe_account_header`
  - `covers_direct_destination_separate_charges`
- 在 `observe(...)` 中为 `source.id == "stripe-spt-connect"` 增加 facts 与 `policy_change` 计算。
- 在 `main()` 中将 `stripe-spt-connect` 纳入 `previous_source_facts` 比对，并更新 `policy_scope` 描述。

### 2) `tests/test_source_monitor.py`

新增/扩展测试：
- `stripe_spt_connect_facts` 正向提取与必需国家列表校验；
- `observe` 对 `stripe-spt-connect` 的 facts 基线写入与错误为空断言。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `15/15` 通过；
- 聚焦回归：`39/39` 通过；
- `source_monitor` 成功刷新 `research/daily/2026-10-31-sources.json`
  （`checked_at=2026-10-31T02:07:43.239151+08:00`，抓取未失败）。

## 架构影响

1. **seller/connect 双视图事实对齐**：SPT 观测从 seller-only 扩展到 connect 视图，减少 hash-only 判读噪声。  
2. **事实与发布结论分离**：`policy_change` 仅表示 selected facts 漂移，不等同于产品发布结论。  
3. **权限边界不变**：全流程仅抓取公开文档与本地解析，不接触支付凭据、账户状态或真实资金流。
