# 2026-10-31：Stage 1687 —— source-monitor 报告 schema 版本标识

[English](2026-10-31-source-monitor-schema-version.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1681–1686 连续扩展了 `source_monitor` 报告字段。  
为避免下游消费方在字段演进中产生兼容性歧义，需提供显式 schema 版本锚点。

Stage 1687 新增报告级 `schema_version`，用于稳定声明当前 JSON 输出契约版本。

## 实现

### `scripts/source_monitor.py`

- 新增常量：
  - `REPORT_SCHEMA_VERSION = "source-monitor-report-v1"`
- 在报告顶层新增字段：
  - `schema_version`

### `tests/test_source_monitor.py`

- 在 `main()` 报告路径断言 `schema_version` 等于 `REPORT_SCHEMA_VERSION`。
- 新增 `test_report_schema_version_is_stable`，固定 schema 版本常量基线。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `28/28` 通过；
- 聚焦回归：`52/52` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 顶层包含
  `"schema_version": "source-monitor-report-v1"`。

## 架构影响

1. **兼容性更可控**：消费方可先按 `schema_version` 选择解析策略。  
2. **演进更安全**：后续字段调整可伴随版本升级，减少隐式破坏。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行与账号权限。
