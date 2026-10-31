# 2026-10-31：Stage 1715 —— source-monitor gate_health 阻塞原因增量净变化信号

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-net-change.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1714 已提供 `blocking_reasons_delta_direction` 方向枚举。  
下游若要设置“净增减阈值”（例如大于 1 才触发升级告警）仍需自行计算净变化值。

Stage 1715 新增 `blocking_reasons_delta_net_change`，直接输出阻塞原因集合的净增减幅度。

## 实现

### `scripts/source_monitor.py`

- 新增字段：
  - `gate_health.blocking_reasons_delta_net_change`
- 语义：
  - 若无前态原因（`previous_blocking_reasons is None`），输出 `null`；
  - 若有前态原因，输出 `len(current_blocking_reasons) - len(previous_blocking_reasons)`。

### `tests/test_source_monitor.py`

- baseline 场景断言 `blocking_reasons_delta_net_change is None`；
- changed 场景断言净变化值为 `1`；
- unchanged 场景断言净变化值为 `0`；
- 其余回归保持通过。

## 图示（净变化计算）

```mermaid
flowchart LR
    P[previous count] --> D[net_change = current - previous]
    C[current count] --> D
    D --> R{net_change}
    R -->|> 0| U[increase tendency]
    R -->|= 0| N[stable]
    R -->|< 0| L[decrease tendency]
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
  `gate_health.blocking_reasons_delta_net_change`（当前 baseline run 为 `null`）。

## 架构影响

1. **阈值路由更直接**：下游可按净变化值直接触发分层处理。  
2. **聚合成本更低**：无需在消费端重复计算 `current-previous`。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
