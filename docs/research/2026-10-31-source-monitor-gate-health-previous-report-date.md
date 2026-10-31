# 2026-10-31：Stage 1698 —— source-monitor gate_health 前态报告日期信号

[English](2026-10-31-source-monitor-gate-health-previous-report-date.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1697 已提供前态 `checked_at`。  
但一些消费方按“日报维度”编排，不希望再从时间戳反推日期。

Stage 1698 新增前态报告日期字段，直接输出前态来源的 `YYYY-MM-DD`。

## 实现

### `scripts/source_monitor.py`

- `previous_blocking_state_snapshot(...)` 新增返回：
  - `report_date = <snapshot filename[:10]>`
- `summarize_gate_health(...)` 新增入参与字段：
  - 入参：`previous_blocking_report_date`
  - 返回：`gate_health.blocking_state_previous_report_date`
- `main()` 将 prior snapshot 的 `report_date` 注入 gate-health 汇总流程。

### `tests/test_source_monitor.py`

- prior snapshot 读取测试新增 `report_date` 校验；
- baseline 断言新增 `blocking_state_previous_report_date is None`；
- `changed/unchanged` 迁移测试新增前态日期断言。

## 图示（前态日期锚定）

```mermaid
flowchart LR
    A[previous snapshot filename] --> B[YYYY-MM-DD]
    B --> C[blocking_state_previous_report_date]
    C --> D[gate_health transition metadata]
```

## 验证

北京时间白天授权窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `36/36` 通过；
- 聚焦回归：`60/60` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 已包含
  `gate_health.blocking_state_previous_report_date`（当前 run 为 `null`，表示当日之前无前态）。

## 架构影响

1. **日报级路由更直接**：消费方可按日期维度直接关联前态来源，无需解析时间戳。  
2. **迁移元数据更完整**：前态 `state_id + checked_at + report_date` 形成可读、可审计的三元锚点。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行或账户权限。
