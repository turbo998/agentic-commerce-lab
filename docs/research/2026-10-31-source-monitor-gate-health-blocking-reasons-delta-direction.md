# 2026-10-31：Stage 1714 —— source-monitor gate_health 阻塞原因增量方向信号

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-direction.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1713 已提供 `blocking_reasons_delta_total_changes` 单值变化幅度。  
下游若要区分“新增主导、移除主导、混合变化、无变化”，仍需自行推导方向。

Stage 1714 新增 `blocking_reasons_delta_direction`，直接输出稳定方向枚举。

## 实现

### `scripts/source_monitor.py`

- 新增字段：
  - `gate_health.blocking_reasons_delta_direction`
- 语义：
  - 若无前态原因（`previous_blocking_reasons is None`），输出 `null`；
  - 若有前态原因：
    - `none`：无增删变化；
    - `increase`：仅新增；
    - `decrease`：仅移除；
    - `mixed`：同时新增与移除。

### `tests/test_source_monitor.py`

- baseline 场景断言 `blocking_reasons_delta_direction is None`；
- changed 场景断言方向为 `increase`；
- unchanged 场景断言方向为 `none`；
- 其余回归保持通过。

## 图示（方向判定）

```mermaid
flowchart LR
    A[added[]] --> D{added?}
    B[removed[]] --> E{removed?}
    D -->|no| F
    D -->|yes| G
    E -->|no| F
    E -->|yes| H
    F[none or decrease]
    G[increase or mixed]
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
  `gate_health.blocking_reasons_delta_direction`（当前 baseline run 为 `null`）。

## 架构影响

1. **方向分流更直接**：下游可按枚举值直接路由，不必重复推导方向。  
2. **消费逻辑更稳定**：统一方向语义减少跨服务条件分支漂移。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
