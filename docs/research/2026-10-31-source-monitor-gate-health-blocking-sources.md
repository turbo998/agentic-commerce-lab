# 2026-10-31：Stage 1691 —— source-monitor gate_health 阻塞源集合信号

[English](2026-10-31-source-monitor-gate-health-blocking-sources.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1690 已将 `observation_error_sources` 与 `policy_error_sources` 下沉到 `gate_health`。  
消费方若需要“单一阻塞源集合”仍需合并与去重两个列表。

Stage 1691 新增 `blocking_sources`，提供可直接消费的阻塞 source ID 去重集合。

## 实现

### `scripts/source_monitor.py`

- 在 `summarize_gate_health(...)` 中新增：
  - `blocking_sources = unique(observation_error_sources + policy_error_sources)`
- 顺序策略：保持来源顺序，先 `observation_error_sources`，后补充未出现的 `policy_error_sources`。

### `tests/test_source_monitor.py`

- 失败路径断言新增：
  - `gate_health.blocking_sources`
- 更新 `test_summarize_gate_health_counts_and_blocking`，验证集合顺序与去重结果。

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
- 刷新的 `research/daily/2026-10-31-sources.json` 中，
  `gate_health.blocking_sources` 已落地（当前成功抓取 run 为 `[]`）。

## 架构影响

1. **阻塞路由字段进一步收敛**：消费方可直接读取单一 `blocking_sources` 字段。  
2. **门禁对象可读性提升**：`gate_health` 同时保留分列明细与聚合集合。  
3. **边界保持不变**：仍是公开来源抓取与离线聚合，不涉及支付执行或账户权限。
