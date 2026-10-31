# 2026-10-31：Stage 1713 —— source-monitor gate_health 阻塞原因增量总变化数信号

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-total-changes.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1712 已输出 `blocking_reasons_delta_counts` 四元计数摘要。  
下游做阈值分流时仍需自行计算 `added + removed` 总变化数。

Stage 1713 新增 `blocking_reasons_delta_total_changes`，直接输出单值变化幅度。

## 实现

### `scripts/source_monitor.py`

- 新增字段：
  - `gate_health.blocking_reasons_delta_total_changes`
- 语义：
  - 若无前态原因（`previous_blocking_reasons is None`），输出 `null`；
  - 若存在前态原因，输出 `len(added) + len(removed)`。

### `tests/test_source_monitor.py`

- baseline 场景断言 `blocking_reasons_delta_total_changes is None`；
- changed 场景断言总变化数为 `1`；
- unchanged 场景断言总变化数为 `0`；
- 其余回归保持通过。

## 图示（总变化数）

```mermaid
flowchart LR
    A[added[]] --> C[total_changes]
    B[removed[]] --> C
    C --> D[len(added) + len(removed)]
```

## 验证

北京时间白天授权窗口内执行：

```bash
python -m pytest tests/test_source_monitor.py -q
python -m pytest -q
python scripts/source_monitor.py --registry research/sources.json --output-dir research/daily
```

结果：
- `tests/test_source_monitor.py`：`43 passed, 6 subtests passed`；
- 全量回归：`4267 passed, 1089 subtests passed`；
- 刷新后的 `research/daily/2026-10-31-sources.json` 已包含
  `gate_health.blocking_reasons_delta_total_changes`（当前 baseline run 为 `null`）。

## 架构影响

1. **阈值分流更直接**：下游可直接按单值变化幅度配置告警或路由策略。  
2. **消费计算更轻量**：减少下游重复计数逻辑与数组展开开销。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
