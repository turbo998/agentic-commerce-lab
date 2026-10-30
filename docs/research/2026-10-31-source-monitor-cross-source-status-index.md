# 2026-10-31：Stage 1684 —— source-monitor 跨来源检查状态索引

[English](2026-10-31-source-monitor-cross-source-status-index.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

`cross_source_checks` 已包含完整检查详情，但自动化侧常只需要快速判断每个 `check_id` 当前状态。  
此前消费方需要遍历数组并自行构造映射，易出现实现分歧。

Stage 1684 新增报告级 `cross_source_statuses`，将状态归一为稳定的 `check_id -> status` 索引。

## 实现

### `scripts/source_monitor.py`

- 新增 `index_cross_source_statuses(checks)`：
  - 仅接收合法字典项中的 `check_id` 与 `status` 字段；
  - 输出稳定映射：`{ "<check_id>": "<status>" }`。
- 在 `main()` 报告新增：
  - `cross_source_statuses`
- 其余门禁与退出语义保持不变。

### `tests/test_source_monitor.py`

- 新增 `test_index_cross_source_statuses_returns_stable_map`。
- 在 `main()` 错误路径与 mismatch 路径新增 `cross_source_statuses` 断言，确保报告一致输出该索引。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `25/25` 通过；
- 聚焦回归：`49/49` 通过；
- 刷新后的 `research/daily/2026-10-31-sources.json` 含
  `cross_source_statuses`，当前为：
  - `stripe-spt-country-list-parity=consistent`
  - `stripe-spt-connect-required-markers=consistent`
  - `stripe-spt-parser-version-parity=consistent`

## 架构影响

1. **消费路径简化**：下游自动化可 O(1) 读取检查状态，不必遍历数组。  
2. **语义保持稳定**：不改变门禁边界与阻塞判定。  
3. **边界不变**：仍是公开来源抓取与离线聚合，不涉及支付执行与账号权限。
