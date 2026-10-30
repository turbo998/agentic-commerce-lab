# 2026-10-31：Stage 1685 —— source-monitor 跨来源检查状态分组

[English](2026-10-31-source-monitor-cross-source-partitions.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1684 已新增 `cross_source_statuses`（`check_id -> status`）。  
但在告警路由场景中，消费方仍需再做一轮状态分组，才能直接拿到“哪些 check 正在 mismatch 或 unavailable”。

Stage 1685 在报告中新增分组视图 `cross_source_partitions`，直接输出按状态归类的 check_id 列表。

## 实现

### `scripts/source_monitor.py`

- 新增 `partition_cross_source_checks(checks)`：
  - 输出：
    - `consistent`: `list[check_id]`
    - `mismatch`: `list[check_id]`
    - `unavailable`: `list[check_id]`
  - 忽略非字典项与不完整项，保证输出结构稳定。
- `main()` 在报告中新增：
  - `cross_source_partitions`
- 现有门禁和退出语义保持不变。

### `tests/test_source_monitor.py`

- 新增 `test_partition_cross_source_checks_groups_check_ids`。
- 扩展 `main()` 错误路径和 mismatch 路径，断言报告中 `cross_source_partitions` 与 `cross_source_statuses` 一致。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `26/26` 通过；
- 聚焦回归：`50/50` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 包含：
  - `cross_source_partitions.consistent`（当前 3 项）
  - `cross_source_partitions.mismatch`（当前空）
  - `cross_source_partitions.unavailable`（当前空）

## 架构影响

1. **告警路由更直接**：可直接读取 mismatch/unavailable check 列表，无需额外分组代码。  
2. **消费一致性提升**：统一分组逻辑由生产端给出，减少各消费端实现偏差。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行或账户权限。
