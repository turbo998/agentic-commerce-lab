# 2026-10-31：Stage 1712 —— source-monitor gate_health 阻塞原因增量计数信号

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-counts.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1711 已提供 `blocking_reasons_delta_payload_id`，用于单值路由与去重。  
下游做监控统计时仍需展开 `previous/current/added/removed` 数组后再计数。

Stage 1712 新增 `blocking_reasons_delta_counts`，直接提供阻塞原因增量计数摘要。

## 实现

### `scripts/source_monitor.py`

- 新增字段：
  - `gate_health.blocking_reasons_delta_counts`
- 语义：
  - 若无前态原因（`previous_blocking_reasons is None`），输出 `null`；
  - 若存在前态原因，输出对象：
    - `previous`：前态原因数
    - `current`：当前原因数
    - `added`：新增原因数
    - `removed`：移除原因数

### `tests/test_source_monitor.py`

- baseline 场景断言 `blocking_reasons_delta_counts is None`；
- changed 场景断言计数为 `{previous:0,current:1,added:1,removed:0}`；
- unchanged 场景断言计数为 `{previous:0,current:0,added:0,removed:0}`；
- 其余回归保持通过。

## 图示（增量计数汇总）

```mermaid
flowchart LR
    A[previous/current/added/removed arrays] --> B{prior exists?}
    B -->|no| C[counts = null]
    B -->|yes| D[counts.previous = len(previous)]
    B --> E[counts.current = len(current)]
    B --> F[counts.added = len(added)]
    B --> G[counts.removed = len(removed)]
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
  `gate_health.blocking_reasons_delta_counts`（当前 baseline run 为 `null`）。

## 架构影响

1. **统计开销降低**：下游无需展开数组即可直接消费增量计数。  
2. **聚合一致性提升**：统一计数字段减少跨服务统计口径差异。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
