# 每日研究与资产发布

## 两条不同流水线

应用内已有启用的 **Agentic Commerce研究** 自动任务，按每日 22:00 的配置以 autopilot/worktree 模式执行解决方案架构研究、开发资产并上传 GitHub；本次是该任务的一轮执行。它由应用调度，不依赖 GitHub cron，且每轮有独立工作分支。主分支尚未接受的成果需要从对应 PR 查阅，后续任务不得重复覆盖未合并成果。

**技术研究**保存为 `research/daily/YYYY-MM-DD.md`：核实官方来源，给出原创中文判断、架构影响、场景价值、当天资产变化、证据和未验证边界。初始成果为 [2026-10-10](../research/daily/2026-10-10.md)。

**自动资料监测**保存为 `research/observations/YYYY-MM-DD.md` 和 `.json`：只观察 `sources.json` 已登记 URL 的 normalized SHA-256、changed/unchanged/new_baseline/error。它不是 AI 研究代理，不理解发布内容、不搜集所有新闻、不会自行修改产品事实，也不生成每天“无新发布”的结论。

## 日常节奏

| 时间/步骤 | 内容 | 输出 |
| --- | --- | --- |
| 每日约北京时间 08:20 | GitHub Actions cron `20 0 * * *`，UTC | artifact + 独立观察分支/PR |
| 研究审核 | 对 changed 来源核实正文、作者、发布日期、版本、地区、preview 与账户资格 | 中文当日研究；无新证据也记录复查范围而不是虚构新闻 |
| 技术资产增量 | 为明确需求新增 adapter、合成场景、测试、版本契约或运行指南 | 与研究结论直接关联的可运行资产 |
| 发布审核 | CI 通过、公开内容脱敏、事实/判断区分、许可边界 | 接受观察基线和研究 PR；不自动合并 |

GitHub 的 cron 不保证精确准点，默认分支上的 workflow 才会被调度；public repo 长时间无活动可能停用 schedule。仓库 Actions 必须允许执行，且 “Allow GitHub Actions to create and approve pull requests” 设置须允许创建 PR。若 PR 创建被策略禁止，run 会失败但 artifact 和已推送观察分支仍可检查。`GITHUB_TOKEN` 创建的后续事件通常不会再触发普通 CI，研究审核时需确保人工触发/更新后的 CI 或本地检查完成。

**初始发布在工作分支/PR；合入默认分支前，GitHub 监测定时任务不会自动运行。** 本脚本没有付费模型调用；无人值守的深度研究由应用已有自动任务执行，费用与可用性遵循应用配置，不能把 hash 监测当作已完成该能力。

本次检查仓库 Actions 设置，`can_approve_pull_request_reviews` 为 `false`。因此目前不能假定 `GITHUB_TOKEN` 可创建观察 PR；监测会保留 artifact 和已推送观察分支，并显式报告发布失败。需要仓库维护者决定是否开放 Actions 创建 PR，本次不改变仓库级权限。

## 本地监测

```powershell
python -m scripts.daily_monitor --date 2026-10-10
```

使用 UTC 默认日期用于机器观察，中文人工研究可明确 Asia/Shanghai。`--date` 可指定归档日期，不表示页面在该历史日期的内容；首次观察为 baseline 而不是 release。state 中的 hash 是本次归一化正文指纹，不是第三方签名证据；GitHub reference code 另存的 revision 是研究代码锚点。

脚本每 URL 最多读取 2 MB、超时 25 秒，跳过 HTML script/style/noscript，合并空白，不保存页面副本。live docs、导航、时间戳和 bot challenge 可能造成噪声；需要人工比对。单个 URL 获取失败仅发布错误类型/HTTP code，保留旧 hash，继续其他来源并最终返回非零状态。不能把 403、空页、网络失败当成“无变化”。

工作流失败也上传 30 天保留的 artifact；会尝试保存观察到 Git 分支/PR，同时 run 保持失败以显式提示问题。每天采用 unique run branch，合并接受的 state 才会更新下一轮默认分支基线。未合并的观察不会被下一日当作已接受证据。

## 新增来源和事实

`sources.json` 每条包括稳定 `id`、vendor、kind、HTTPS url、可选 monitor_url、published_date、checked_on、notes；代码证据可带 revision/selected_version。published_date 不确定时为 `null`，不能拿 checked_on 替代。

仅使用公开官方来源及合法的开放规范/代码。公告、实时文档、规范和样例的证据强度不同；不复制全文、截图或第三方源代码。AI 辅助原创研究须标识未经认证的判断；生产、合规或产品承诺需人工审核。任何真实卡号、token、客户数据、内部 URL 或账户凭据均不得进入公共 repo、Actions artifact 和日志。
