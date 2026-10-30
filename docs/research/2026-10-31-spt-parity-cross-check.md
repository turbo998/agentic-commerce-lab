# 2026-10-31：Stage 1677 —— source-monitor 的 SPT seller/connect 一致性检查

[English](2026-10-31-spt-parity-cross-check.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1676 已把 `stripe-spt`（seller）与 `stripe-spt-connect`（connect）都转为 selected facts 观测。  
Stage 1677 在此基础上补齐 **跨来源一致性检查**：比较两者国家列表摘要是否一致，避免仅凭单源漂移做过早判断。

## 实现

### 1) `scripts/source_monitor.py`

- 新增 `spt_country_list_check(observations)`，输出报告级检查对象：
  - `check_id="stripe-spt-country-list-parity"`
  - `status ∈ {consistent, mismatch, unavailable}`
- 检查逻辑：
  - 仅在 seller/connect 均 `status=ok` 且 selected facts 可用时比较；
  - 比较字段：`supported_country_count` 与 `supported_country_codes_sha256`；
  - 字段缺失或来源失败时返回 `unavailable`（显式原因）。
- `main()` 报告新增 `cross_source_checks` 字段，保留“事实检查 ≠ 产品发布结论”的边界。

### 2) `tests/test_source_monitor.py`

新增测试：
- 一致场景返回 `status="consistent"`；
- 不一致场景返回 `status="mismatch"`；
- 来源不可用场景返回 `status="unavailable"`；
- 同时校验 `main()` 失败路径仍会写入 `cross_source_checks`。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `17/17` 通过；
- 聚焦回归：`41/41` 通过；
- `research/daily/2026-10-31-sources.json` 刷新至
  `checked_at=2026-10-31T02:14:58.884908+08:00`，并包含：
  `cross_source_checks[0].status="consistent"`。

## 架构影响

1. **双视图事实增加互证层**：seller/connect 不再各自孤立，只要 selected facts 可用就会做一致性校验。  
2. **不确定性显式化**：来源失败或字段缺失时输出 `unavailable`，避免“静默视为一致”。  
3. **权限边界不变**：仍是公开文档解析与本地比较，不触发账户、密钥或支付动作。
