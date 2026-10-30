# 2026-10-31：Stage 1680 —— SPT 解析器版本一致性门禁

[English](2026-10-31-spt-parser-version-parity.en.md) | [阶段索引](../stage-archive-index.md)

## 背景与目标

Stage 1679 已建立 seller/connect 的内容一致性与必需标记门禁。  
Stage 1680 继续收紧可审计性：新增 **解析器版本一致性检查**，确保 selected facts 来自已审阅 parser 语法版本。

## 实现

### `scripts/source_monitor.py`

- 新增 `spt_parser_version_check(observations)`：
  - `check_id="stripe-spt-parser-version-parity"`
  - 校验期望版本：
    - `stripe-spt` → `stripe-spt-facts-v1`
    - `stripe-spt-connect` → `stripe-spt-connect-facts-v1`
  - 输出 `status ∈ {consistent, mismatch, unavailable}`，并在 mismatch 时附 `expected/actual`。
- `cross_source_checks` 扩展为三项：
  1) 国家列表 parity  
  2) connect 必需标记  
  3) parser version parity
- 复用既有门禁：任一 check 为 `mismatch` 即非零退出。

### `tests/test_source_monitor.py`

新增测试：
- parser-version 检查的 `consistent/mismatch/unavailable` 三态；
- `main()` 在 parser 版本 mismatch 时返回非零并写入对应 check。

## 验证

北京时间窗口内执行：

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

结果：
- `tests.test_source_monitor`: `22/22` 通过；
- 聚焦回归：`46/46` 通过；
- `sources` 快照更新到 `checked_at=2026-10-31T03:42:06.083179+08:00`，
  三项 cross-source checks 当前均为 `consistent`。

## 架构影响

1. **语法版本漂移可阻断**：避免在未审阅 parser 版本下继续输出“看似成功”的 selected facts。  
2. **变更定位更直接**：`expected/actual` 差异直接指出是 seller 还是 connect parser 偏离。  
3. **离线边界不变**：仍为公开文档事实抽取与本地比对，不触达支付账户或密钥。
