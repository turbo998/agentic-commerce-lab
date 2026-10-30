# Stage 1673：`source_monitor` 的 Stripe SPT 动态示例时间戳降噪

[English](2026-10-31-source-monitor-noise-filter.en.md) |
[当日日报](../../research/daily/2026-10-31.md) |
[上一阶段](2026-10-31-stripe-claim-read.md)

**结论：**在 [`scripts/source_monitor.py`](../../scripts/source_monitor.py) 引入
source-specific 归一化 `_normalize_source_noise(source_id, text)`，对 `source_id=="stripe-spt"`
时将示例 JSON 中波动的 `"expires_at": <unix-seconds>` 统一替换为固定占位符后再计算哈希。
这样保留正文变化检测能力，同时避免把秒级动态示例值当作产品发布证据。

## 1. 背景证据（2026-10-31 00:06–00:44 BJT）

- 当日首次 `source_monitor` 快照（`00:06`）显示唯一 `change="changed"` 源为 `stripe-spt`。
- 对同一 URL 连续抓取并做 unified diff，发现差异仅在示例字段：
  `"expires_at": 1795968579` 与 `"expires_at": 1795968581` 的秒级抖动。
- 这类变化不应直接触发“新协议发布”结论，需要在哈希层做最小、可审计、source-specific 的降噪处理。

## 2. 代码变更

在 `scripts/source_monitor.py`：

1. 新增 `_normalize_source_noise(source_id, text)`：
   - 当前仅针对 `stripe-spt` 生效；
   - 正则替换 `"expires_at": 10-13 位数字` 为固定标记
     `"expires_at": <dynamic-unix-timestamp>`。
2. `fingerprint` 签名扩展为
   `fingerprint(body, content_type, *, source_id: str | None = None)`，
   在 HTML 可见文本抽取后、空白折叠前应用 source-specific 归一化。
3. `observe` 在计算 `digest` 时显式传入 `source.id`。
4. 报告元数据 `normalization` 升级为
   `utf8-visible-html-text-or-markdown-whitespace-v2-with-source-noise-filters`。

## 3. 测试与验证

- 更新 [`tests/test_source_monitor.py`](../../tests/test_source_monitor.py)：
  - `stripe-spt` 场景下，不同 `expires_at` 秒值经归一化后哈希一致；
  - `observe` 在 `stripe-spt` 二次抓取的动态 `expires_at` 变化下返回 `change="unchanged"`。
- 通过：
  - `python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts -v`（`21/21`）
  - Stage 1652–1673 聚焦回归（`526/526`）。

## 4. 边界与后续

1. 该降噪是**按来源定点**处理，不影响其它来源哈希语义。
2. 仅替换波动样例时间戳，不替换协议正文、状态码、路径、参数名等关键文本。
3. `2026-10-31` 当日相对 `2026-10-30` 仍可能出现一次性哈希重基线（归一化版本升级导致），
   属可解释的监测语义升级，而非协议发布本身。

