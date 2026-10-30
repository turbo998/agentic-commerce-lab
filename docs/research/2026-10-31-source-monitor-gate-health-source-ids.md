# 2026-10-31：Stage 1690 —— source-monitor gate_health 源 ID 信号

[English](2026-10-31-source-monitor-gate-health-source-ids.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

当前 `gate_health` 已提供阻塞计数（`observation_errors`、`policy_errors`），  
但消费方仍需回扫 `observations` 才能定位具体是哪些 source 触发阻塞。

Stage 1690 在 `gate_health` 中直接补齐 source ID 列表，降低阻塞定位成本。

## 实现

### `scripts/source_monitor.py`

- 在 `summarize_gate_health(...)` 中新增：
  - `observation_error_sources`: `status="error"` 的 source ID 列表
  - `policy_error_sources`: `policy_error` 非空的 source ID 列表
- 保留既有计数与阻塞语义不变，仅增加机读定位字段。

### `tests/test_source_monitor.py`

- 失败路径报告断言新增：
  - `gate_health.observation_error_sources`
  - `gate_health.policy_error_sources`
- 更新 `test_summarize_gate_health_counts_and_blocking`，校验新增 source ID 列表。

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
- 刷新后的 `research/daily/2026-10-31-sources.json` 中，
  `gate_health` 已包含 `observation_error_sources` 与 `policy_error_sources`（当前均为空数组）。

## 架构影响

1. **阻塞定位一步到位**：无需二次扫描 `observations` 即可定位抓取或事实解析异常来源。  
2. **门禁信号层次更完整**：`gate_health` 同时包含计数、原因分类与 source ID 明细。  
3. **边界保持不变**：仍是公开来源抓取与离线聚合，不涉及支付执行或账户权限。
