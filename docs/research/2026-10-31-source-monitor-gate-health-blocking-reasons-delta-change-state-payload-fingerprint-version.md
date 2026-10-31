# 2026-10-31：Stage 1723 —— source-monitor gate_health 阻塞原因增量变化状态载荷指纹版本契约

[English](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-version.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1722 已提供 `blocking_reasons_delta_change_state_payload_fingerprint`。  
为避免未来指纹算法或序列化策略演进时的静默不兼容，需要显式暴露指纹版本。

Stage 1723 新增 `blocking_reasons_delta_change_state_payload_fingerprint_version`。

## 实现

### `scripts/source_monitor.py`

- 新增常量：
  - `BLOCKING_REASONS_DELTA_CHANGE_STATE_PAYLOAD_FINGERPRINT_VERSION = "sha256-change-state-payload-v1"`
- 新增字段：
  - `gate_health.blocking_reasons_delta_change_state_payload_fingerprint_version`
- 语义：
  - 所有场景固定输出 `sha256-change-state-payload-v1`；
  - 与 `...payload_fingerprint` 配合，形成版本化单值对账契约。

### `tests/test_source_monitor.py`

- baseline / changed / unchanged 场景均断言：
  `...payload_fingerprint_version == "sha256-change-state-payload-v1"`；
- 并保持既有 `...payload_fingerprint` 断言不变；
- 其余回归保持通过。

## 图示（指纹版本化）

```mermaid
flowchart LR
    V[fingerprint_version] --> C[fingerprint]
    C --> R[reconciliation & cache key]
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
  `gate_health.blocking_reasons_delta_change_state_payload_fingerprint_version`。

## 架构影响

1. **对账契约可演进**：下游可按版本切换比较逻辑，降低协议升级风险。  
2. **机器消费更稳健**：指纹值与版本绑定，避免跨版本误判。  
3. **边界不变**：仍为公开来源抓取与离线聚合，不涉及支付执行或账户权限。
