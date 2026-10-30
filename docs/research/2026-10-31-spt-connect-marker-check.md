# 2026-10-31：Stage 1679 —— SPT Connect 必需标记互证检查

[English](2026-10-31-spt-connect-marker-check.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1678 已将 seller/connect 国家列表不一致升级为非零门禁。  
Stage 1679 进一步补齐 Connect 视图完整性：增加 **必需标记检查**，确保关键 Connect 语义字段持续存在。

## 实现

### `scripts/source_monitor.py`

- 新增 `spt_connect_marker_check(observations)`，输出：
  - `check_id="stripe-spt-connect-required-markers"`
  - `status ∈ {consistent, mismatch, unavailable}`
- 校验目标（均要求为 `true`）：
  - `has_connect_platforms_section`
  - `has_network_business_profile`
  - `has_shared_payment_granted_token`
  - `has_stripe_account_header`
  - `covers_direct_destination_separate_charges`
- `main()` 的 `cross_source_checks` 扩展为两项：
  1) seller/connect 国家列表 parity  
  2) connect 必需标记检查
- 现有门禁规则复用：任一 check 为 `mismatch` 即非零退出。

### `tests/test_source_monitor.py`

新增测试：
- `spt_connect_marker_check` 的 `consistent/mismatch/unavailable` 三态；
- `main()` 在 connect 标记缺失时返回非零并输出对应 check 的 `mismatch`。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `20/20` 通过；
- 聚焦回归：`44/44` 通过；
- `sources` 快照刷新为 `checked_at=2026-10-31T03:04:34.643161+08:00`，
  两项 cross-source check 当前均为 `consistent`。

## 架构影响

1. **互证从“列表一致”扩展到“语义存在性”**：不仅看国家列表，也看 Connect 关键接入语义是否仍在。  
2. **失败可定位**：`mismatch` 输出缺失标记清单，便于快速定位上游文档变更点。  
3. **离线边界不变**：仍为公开文档抓取 + 本地事实比较，不触及真实支付与账户操作。
