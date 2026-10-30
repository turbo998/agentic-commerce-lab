# 2026-10-31：Stage 1686 —— source-monitor gate_health 阻塞检查 ID 信号

[English](2026-10-31-source-monitor-gate-health-blocking-checks.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1685 已新增 `cross_source_partitions`，可看到 mismatch check 列表。  
但 run-level 门禁消费方若只读取 `gate_health`，仍需跨字段再拼接一次阻塞 check_id。

Stage 1686 将阻塞检查 ID 直接下沉到 `gate_health`，减少消费端跨字段关联。

## 实现

### `scripts/source_monitor.py`

- 扩展 `summarize_gate_health(...)` 入参，接收 `cross_source_partitions`。
- 在 `gate_health` 新增：
  - `cross_source_blocking_checks`（当前等于 `cross_source_partitions.mismatch`）
- 其余 blocking 语义保持不变。

### `tests/test_source_monitor.py`

- 在 `main()` 失败路径中断言 `cross_source_blocking_checks` 存在且可为空。
- 在 parser-version mismatch 路径中断言 `cross_source_blocking_checks` 包含
  `stripe-spt-parser-version-parity`。
- 新增 `test_summarize_gate_health_includes_cross_source_blocking_checks`。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `27/27` 通过；
- 聚焦回归：`51/51` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 含
  `gate_health.cross_source_blocking_checks`（当前为空列表）。

## 架构影响

1. **run-level 门禁可直接路由**：只读取 `gate_health` 即可得到阻塞 check_id。  
2. **消费耦合降低**：减少 `gate_health` 与 `cross_source_partitions` 的跨字段拼接。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行与账号权限。
