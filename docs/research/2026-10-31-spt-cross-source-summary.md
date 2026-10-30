# 2026-10-31：Stage 1681 —— SPT 跨来源检查摘要信号

[English](2026-10-31-spt-cross-source-summary.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1680 已把 SPT 跨来源检查扩展到三项门禁。  
Stage 1681 增加结构化摘要 `cross_source_summary`，把多项 check 结果压缩为稳定计数与阻塞标记，方便日报与自动化消费。

## 实现

### `scripts/source_monitor.py`

- 新增 `summarize_cross_source_checks(checks)`，输出：
  - `total`
  - `consistent`
  - `mismatch`
  - `unavailable`
  - `blocking`（`mismatch > 0`）
- `main()` 在报告中新增 `cross_source_summary` 字段。
- 退出条件改为复用 `cross_source_summary.blocking`，与原 fail-fast 语义保持一致。

### `tests/test_source_monitor.py`

新增与扩展：
- `test_summarize_cross_source_checks_counts_and_blocking`
- 在 `main()` 失败路径与 parser-mismatch 路径中断言 `cross_source_summary` 字段存在且计数正确。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `23/23` 通过；
- 聚焦回归：`47/47` 通过；
- `sources` 快照刷新到 `checked_at=2026-10-31T03:45:59.910880+08:00`，
  且 `cross_source_summary={"total":3,"mismatch":0,"blocking":false,...}`。

## 架构影响

1. **门禁状态可观测性增强**：从“看三条 check”提升为稳定摘要指标，便于自动阈值判断。  
2. **语义不变**：`blocking` 仍由 `mismatch` 驱动，不改变既有失败边界。  
3. **离线边界不变**：仅公开文档抓取 + 本地解析/聚合，无支付或账户权限扩展。
