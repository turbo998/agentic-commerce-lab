# 2026-10-31：Stage 1688 —— source-monitor 来源观察摘要信号

[English](2026-10-31-source-monitor-observation-summary.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

当前报告已包含逐条 `observations` 明细与多个门禁聚合。  
但在运行看板场景中，消费方仍需扫描数组才能判断“本次抓取层整体健康度与漂移形态”。

Stage 1688 新增 `observation_summary`，将来源抓取层状态与 change 分布聚合为稳定计数。

## 实现

### `scripts/source_monitor.py`

- 新增 `summarize_observation_changes(observations)`，输出：
  - `total` / `ok` / `error`
  - `baseline` / `unchanged` / `changed` / `unknown`
- 在报告顶层新增：
  - `observation_summary`

### `tests/test_source_monitor.py`

- 在 `main()` 失败路径新增 `observation_summary` 断言（`total/error/unknown`）。
- 新增 `test_summarize_observation_changes_counts`，校验计数逻辑。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `29/29` 通过；
- 聚焦回归：`53/53` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 包含
  `observation_summary`（含 `ok/error` 与 `baseline/unchanged/changed/unknown` 计数）。

## 架构影响

1. **抓取层健康度可直读**：无需遍历明细即可判断采集成功率与漂移分布。  
2. **监控维度更完整**：将“门禁状态”与“抓取状态”解耦并并行暴露。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行与账号权限。
