# 每日研究维护与完整性校验

## 用途

将每日原创研究形成可追溯资产，而不是每日重复公告或复制第三方资料。复用仓库已有 Node.js Personal Agent 实验；本次新增的 Python 工具只负责研究登记与引用完整性。

## 前提与运行

研究工具需要 Python 3.11+ 标准库，不需要安装依赖、密钥或网络。已有模拟实验需要 Node.js 22+，运行步骤见 [仓库主页](../README.md) 和 [实验架构](architecture.md)。

```powershell
python -m lab.check_research
python -m unittest discover -s tests -v
npm run check
```

GitHub Actions 对提交和 PR 执行上述离线回归，不进行真实支付、不部署云资源，也不自动合并。

## 每日流程

1. 从主分支及已有未合并研究 PR 确认资产基线；避免重新构建已存在的实验。叠加 PR 要标明父分支，不覆盖另一会话的工作。
2. 直接访问 Visa、Stripe 官方公告、开发文档和协议仓库；搜索结果只用于发现链接，不作为事实依据。
3. 在 `research/sources.json` 登记来源 ID、URL、类型和原创观察，分开记录 `published_on` 与 `reviewed_on`。无法核实发布日期用 `null`，不能填复核日。代码/规范使用固定 revision；未固定版本的滚动文档明确作为当日观察。
4. 在 `research/daily/YYYY-MM-DD.md` 追加当日研究，包含新增或变更、可用性/证据等级、架构影响、Agent 场景、资产变化、未解决问题与下一轮可执行主题。没有可确认新发布时如实说明。
5. 增量开发针对性资产并运行回归；不得把 mock/模拟描述成供应商 sandbox、conformance 或真实资金结果。
6. 核查公开内容只含原创总结、合成数据与合法引用；不上传原始第三方页面、内部材料、PII、账户信息或密钥。
7. 提交并推送研究分支，通过 PR 进入主分支；默认不自动合并，也不重新创建已有每日研究自动化。

## 来源字段

| 字段 | 含义 |
|---|---|
| `reviewed_on` | 最新一轮基线复核日期，不是所有来源的发布日期 |
| `timezone` | 日报日期采用的时区 |
| `id` | 唯一 `Snn` 编号，供日报及文档引用 |
| `kind` | announcement / documentation / specification / reference-code |
| `published_on` | 已核实发布日期；无法确认用 `null` |
| `revision` | 可选，固定 Git commit SHA；不是认证标签 |
| `spec_version` / `api_version` | 被观察的日期版规范 / API 示例版本 |
| `observation` | 原创摘要与证据边界；不得存放整页副本 |

## 校验行为与限制

`python -m lab.check_research` 检查来源 ID 唯一、HTTPS URL、日期格式和先后顺序、revision 格式、日报标题/日期以及文档来源引用；失败以非零退出码显式报告。`python -m unittest discover -s tests -v` 验证正常登记和异常登记拒绝。

校验器不访问网络，不验证 URL 可达性，不证明摘要正确，也不保证供应商账户有接入资格。事实需直接重访原始页面，分清 release-day 公告、当前文档、preview、pilot、GA 和 reference code。

既有 Copilot App 每日 22:00 研究自动化保持不变，其执行依赖 App、本机联网且未休眠。GitHub Actions 只进行资产检查，不能保证每日生成原创研究。

本文由 AI 辅助撰写；生产选型和涉及资金、合规的判断必须人工及供应商复核。
