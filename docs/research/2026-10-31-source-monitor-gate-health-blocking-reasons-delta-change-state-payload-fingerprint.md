# 2026-10-31：Stage 1722 —— source-monitor gate_health 阻塞原因增量变化状态载荷指纹

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1721 已输出 `blocking_reasons_delta_change_state_payload` 结构化对象。  
下游若要进行单值去重、审计对比或缓存键化，仍需自行计算 payload 指纹。

Stage 1722 新增 `blocking_reasons_delta_change_state_payload_fingerprint`，直接输出稳定 SHA-256 指纹。

## 实现

### `scripts/source_monitor.py`

- 新增字段：
  - `gate_health.blocking_reasons_delta_change_state_payload_fingerprint`
- 语义：
  - 若 payload 为空（baseline），输出 `null`；
  - 若 payload 存在，对 payload 的 canonical JSON
    （`sort_keys=True`, `separators=(",", ":")`）计算 SHA-256。

### `tests/test_source_monitor.py`

- baseline 场景断言 `...payload_fingerprint is None`；
- changed/unchanged 场景分别断言：
  `...payload_fingerprint == sha256(canonical_json(payload))`；
- 其余回归保持通过。

## 图示（载荷指纹计算）

```mermaid
flowchart LR
    P[change_state_payload] --> J[canonical JSON]
    J --> H[sha256]
    H --> F[payload_fingerprint]
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
  `gate_health.blocking_reasons_delta_change_state_payload_fingerprint`。

## 架构影响

1. **单值对账更高效**：下游可直接使用指纹做去重和快速相等性判断。  
2. **审计可回放**：结构化 payload 与指纹并存，兼顾可读性与机器比对。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
