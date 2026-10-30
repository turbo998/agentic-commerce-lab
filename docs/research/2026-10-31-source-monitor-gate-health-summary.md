# 2026-10-31：Stage 1682 —— source-monitor 运行门禁健康摘要信号

[English](2026-10-31-source-monitor-gate-health-summary.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1681 已提供 `cross_source_summary`，可快速判断跨来源检查是否存在 `mismatch`。  
但 `source_monitor` 的非零退出还包括抓取失败与 facts 解析失败，自动化侧仍需额外遍历 `observations` 才能还原完整阻塞原因。

Stage 1682 增加统一 `gate_health` 摘要，让“本次是否阻塞、阻塞来自哪里”可直接机器读取。

## 实现

### `scripts/source_monitor.py`

- 新增 `summarize_gate_health(observations, cross_source_summary)`，输出：
  - `observation_errors`（`status="error"` 计数）
  - `policy_errors`（`policy_error` 非空计数）
  - `cross_source_mismatch`（沿用 `cross_source_summary.mismatch`）
  - `blocking`（三类门禁任一非零即 `true`）
- `main()` 在报告中新增 `gate_health` 字段。
- 退出码改为直接复用 `gate_health.blocking`，与既有 fail-fast 语义等价，但输出更可观测。

### `tests/test_source_monitor.py`

- 新增 `test_summarize_gate_health_counts_and_blocking`。
- 在 `main()` 失败路径与 parser-version mismatch 路径断言 `gate_health` 字段及关键计数。

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
- `sources` 快照刷新后包含
  `gate_health={"observation_errors":0,"policy_errors":0,"cross_source_mismatch":0,"blocking":false}`。

## 架构影响

1. **门禁可解释性增强**：自动化不再需要同时解析退出码与明细列表才能判断阻塞来源。  
2. **与 Stage 1681 互补**：`cross_source_summary` 描述跨来源一致性，`gate_health` 描述整次运行的总门禁状态。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不引入支付执行或账户权限变更。
