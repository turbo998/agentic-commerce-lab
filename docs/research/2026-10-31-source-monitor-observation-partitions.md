# 2026-10-31：Stage 1689 —— source-monitor 来源观察分组信号

[English](2026-10-31-source-monitor-observation-partitions.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1688 已提供 `observation_summary` 计数，能够快速判断抓取健康度。  
但消费方若要定位“哪些 source 触发 changed/unknown/error”，仍需遍历完整 `observations`。

Stage 1689 新增 `observation_partitions`，将 source ID 按抓取状态与变化类型稳定分组，减少下游重复扫描逻辑。

## 实现

### `scripts/source_monitor.py`

- 新增 `partition_observations(observations)`，输出：
  - `ok` / `error`
  - `baseline` / `unchanged` / `changed` / `unknown`
  - 每个键对应 source ID 列表（保持观测顺序）。
- 在报告顶层新增：
  - `observation_partitions`

### `tests/test_source_monitor.py`

- 失败路径报告断言增加：
  - `observation_partitions.error`
  - `observation_partitions.unknown`
- 新增 `test_partition_observations_groups_source_ids`，校验分组输出内容与顺序。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `30/30` 通过；
- 聚焦回归：`54/54` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 包含
  `observation_partitions`（source ID 分组索引）。

## 架构影响

1. **变更定位成本降低**：可直接读取 `changed/unknown/error` 对应 source 列表。  
2. **门禁联动更直接**：与 `gate_health`、`observation_summary` 形成“计数 + 列表”双层信号。  
3. **边界保持不变**：仍是公开来源抓取与离线聚合，不涉及支付执行或账户权限。
