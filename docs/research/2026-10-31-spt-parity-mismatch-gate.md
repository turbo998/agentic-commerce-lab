# 2026-10-31：Stage 1678 —— SPT 一致性不匹配显式失败门禁

[English](2026-10-31-spt-parity-mismatch-gate.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1677 已输出 `cross_source_checks`，但 seller/connect 不一致仅作为报告信号。  
Stage 1678 将该不一致升级为 **显式非零退出门禁**，确保监控流水线把事实分歧作为阻塞审查信号处理。

## 实现

### `scripts/source_monitor.py`

- 保留 Stage 1677 的 `spt_country_list_check(...)` 报告输出。
- `main()` 退出码规则扩展为：
  - 任一 `observation.status == "error"` 或 `policy_error` → 非零；
  - 任一 `cross_source_checks[].status == "mismatch"` → 非零。
- `consistent`/`unavailable` 语义不变：
  - `consistent`：通过；
  - `unavailable`：仍由来源抓取/解析状态决定，不引入“成功形态兜底”。

### `tests/test_source_monitor.py`

新增 `test_main_returns_nonzero_on_cross_source_mismatch`，验证：
- 在 seller/connect 两条 observation 均 `ok` 但国家摘要不一致时，
  `main()` 返回 `1`，且报告中 `cross_source_checks[0].status == "mismatch"`。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `18/18` 通过；
- 聚焦回归：`42/42` 通过；
- `sources` 快照刷新到 `checked_at=2026-10-31T02:54:19.488213+08:00`，
  当前 parity 检查为 `consistent`，因此监控仍返回成功。

## 架构影响

1. **从“提示”升级到“门禁”**：跨来源事实冲突会显式阻断，避免误把冲突状态继续传播。  
2. **仍保持可解释输出**：失败同时保留 `cross_source_checks` 证据字段，便于人工溯源。  
3. **权限边界不变**：仅公开文档抓取与本地事实比对，无真实支付/账户操作。
