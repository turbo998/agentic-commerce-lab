# 2026-10-31：Stage 1683 —— source-monitor 运行门禁阻塞原因信号

[English](2026-10-31-source-monitor-gate-health-reasons.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1682 已新增 `gate_health` 统一门禁摘要，并给出 `blocking` 布尔值。  
但自动化侧若要判断“具体因何阻塞”，仍需额外读取多个计数字段并自行归因。

Stage 1683 在保持现有门禁语义不变的前提下，新增有序 `blocking_reasons`，提供可直接消费的阻塞原因列表。

## 实现

### `scripts/source_monitor.py`

- 扩展 `summarize_gate_health(...)` 输出字段：
  - `blocking_reasons`（有序列表，当前顺序固定为：
    `observation_errors` → `policy_errors` → `cross_source_mismatch`）
- 仅当对应计数大于 0 时写入该原因；无阻塞时输出空列表 `[]`。
- `blocking` 判定保持不变（任一门禁计数非零即阻塞）。

### `tests/test_source_monitor.py`

- 在 `main()` 失败路径中断言 `blocking_reasons` 包含 `observation_errors`。
- 在 parser-version mismatch 路径中断言 `blocking_reasons` 包含 `cross_source_mismatch`。
- 扩展 `test_summarize_gate_health_counts_and_blocking`，校验多重阻塞时原因列表顺序与内容。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `24/24` 通过；
- 聚焦回归：`48/48` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 包含
  `gate_health.blocking_reasons` 字段（当前为 `[]`，表示无阻塞原因）。

## 架构影响

1. **门禁可诊断性增强**：下游自动化可直接读取阻塞原因，不必重复解析明细。  
2. **语义稳定**：未改变 fail-fast 边界与退出码条件。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不引入支付或账户权限操作。
