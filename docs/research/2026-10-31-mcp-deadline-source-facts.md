# 2026-10-31：Stage 1675 —— 基于 source facts 的 Stripe MCP 截止日仿真

[English](2026-10-31-mcp-deadline-source-facts.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

在 `scripts/source_monitor.py` 已可提取 `stripe-mcp` selected facts（含 `deadline`）后，`lab.mcp_migration` 仍使用硬编码截止日。  
Stage 1675 的目标是：**在不增加任何真实账户访问/密钥调用前提下**，允许迁移仿真工具从当日来源快照读取截止日，减少“监测事实”与“离线仿真”之间的手工同步误差。

## 实现

### 1) `lab/mcp_migration.py`

- 新增 `load_deadline_from_source_report(path)`：
  - 仅解析离线 JSON 快照；
  - 要求存在且仅存在一条成功的 `stripe-mcp` selected-facts 行；
  - 要求 `parser_version=stripe-mcp-auth-notice-v1`，并校验 `deadline` 为 ISO 日期。
- `assess(...)` 新增 `deadline` 参数（默认仍为现有基线常量），使状态判定可被来源事实驱动。
- CLI 新增 `--source-report <daily-sources.json>`：
  - 传入时，使用快照中的 `deadline` 与 `checked_at`；
  - 输出新增 `deadline_source`、`deadline_parser_version` 字段，明确截止日来源。

### 2) `tests/test_mcp_migration.py`

- 扩展 CLI 测试入口，支持注入 `--source-report`。
- 新增覆盖：
  - 来源快照覆盖截止日后，`migration_required`/`blocked_by_documented_policy` 边界随之变化；
  - 缺失或不匹配 parser 的快照会显式失败（`invalid_inventory`），避免“静默回退 + 成功形态”。

## 验证

在北京时间夜间窗口执行：

```bash
python -m unittest tests.test_mcp_migration -v
```

结果：`12/12` 通过。

## 架构影响

1. **监测与仿真解耦但可对齐**：source monitor 负责“官方文本事实提取”，migration 工具负责“离线边界仿真”，通过快照文件进行弱耦合。  
2. **仍保持无支付权限**：新增能力只读取本地 JSON 元数据，不触发 Stripe API、不读取密钥、不验证账户真实性。  
3. **截止日变更更可审计**：输出中明确 `deadline_source` 与 parser 版本，便于回溯“为何当日仿真边界发生变化”。
