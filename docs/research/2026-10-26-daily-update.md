# 2026-10-26 技术资产与架构更新索引（Stages 266–281+ · 达成 280 阶段里程碑 & 全仓 `976/976` 单测全绿！）

🌐 **Language / 语言导航**: **中文更新索引 (当前)** | **[English Update Index (`2026-10-26-daily-update.en.md`)](2026-10-26-daily-update.en.md)** | **[2026-10-26 每日研究 (`research/daily/2026-10-26.md`)](../../research/daily/2026-10-26.md)** | **[English Daily Research (`research/daily/2026-10-26.en.md`)](../../research/daily/2026-10-26.en.md)**

---

## Stage 280–281（达成 280 阶段里程碑 & 全仓 `976/976` 单测全绿 · 40 仓库 293 项零重叠一手 PR 覆盖！）：Coinbase x402 流式请求克隆与 AgentKit CDP `idempotencyKey`、AP2 dSD-JWT 终端绑定与 Visa TAP `Ed25519+ML-DSA-65` 后量子混合验签、UCP `304 Not Modified` Profile 缓存命中与 `requires_escalation` `continue_url`、ACP OpenAPI 内联 `$ref` 校验与整数最小单位退单、A2A 推送故障隔离与多端流式路由、Stripe `tulip` 准入门禁与七端 SDK 账户作用域、Sierra $\tau$-bench 2.0 知识库沙箱与双射动作匹配，以及 MCP 十一语言 SDK / Conformance / Inspector / Registry 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（40 个上游仓库 293 项零重叠 PR，`PR-01..PR-16`）**：
  - `PR-01`（`coinbase/x402#312`、`#306`、`#297`、`#283`、`#277`、`#257`、`#412`、`#408`、`#391`、`#390` & `coinbase/agentkit#1530`、`#1507`、`#1468`、`#1469`、`#1545`、`#1552`、`#1554`、`#1491`）：`x402-fetch` 在 `402` 重试前克隆流式请求体、跳过不可解析的 `accepts[]` 条目、EVM 签名器缺失地址快速失败、AgentKit CDP 资金操作透传 `idempotencyKey`、大小写无关 EVM 地址比对与 x402 报价/结算身份及自动付款限额绑定。
  - `PR-02`（`google-agentic-commerce/AP2#384`、`#383`、`#378`、`#377`、`#368`、`#365`、`#363`、`#359`、`#351`、`#347`、`#342`、`#335`、`#330`、`#326`、`#324`、`#318` & `visa/trusted-agent-protocol#18`、`#9`）：`verify_receipt` 回调判空、JSON 模式序列化 `cnf.jwk`、ISO 8601 执行日期窗口、JPY 等零小数位币种预算上限、dSD-JWT 终端跳 `aud`/`nonce`、闭合结账绑定与授权令原子单次消耗，以及 Visa TAP DID `key_id` 解析、`Ed25519+ML-DSA-65` 后量子混合签名与 mTLS 客户端证书鉴权。
  - `PR-03`（`Universal-Commerce-Protocol/ucp#939`..`#908`）：Profile 拉取将 HTTP `304 Not Modified` 视为缓存命中而非重定向错误、`requires_escalation` 状态强制 `continue_url`、`complete_checkout` 移除 `cart_id`、递延账期允许空 `payment: {}` 对象，以及凭据提供商签发 PSP 令牌前验签 AP2 授权令。
  - `PR-04`（`Universal-Commerce-Protocol/python-sdk#98`..`#52`）：声明类作用域 `uniqueItems` 校验器、生成数组字段 `uniqueItems` 与 `contains`/`minContains`/`maxContains`、对象 `minProperties` 及从 `$defs` 推导含 `catalog` 的 `UcpMetadata` 联合类型。
  - `PR-05`（`Universal-Commerce-Protocol/conformance#93`..`#73` & `samples#243`..`#214`）：通过发现端点路由 `invalid_input` 订单探测、结账创建兼容 `200`/`201`、行项目数量 $>0$ 校验、移除未设置可选订单字段的 `null` 填充，以及缺失订单返回标准 UCP 错误信封。
  - `PR-06`（`agentic-commerce-protocol/agentic-commerce-protocol#309`..`#219`）：OpenAPI 内联 `example` 针对 `$ref` Schema 校验、解包 `delegate_payment` 错误示例冗余外层包装、强制正整数最小货币单位退款金额与 `session_context` 遥测字段。
  - `PR-07`（`a2aproject/A2A#2384..#2285` & `a2a-python#1348..#1287`）：推送通知失败与任务生命周期隔离、直接 `Message` 响应后释放 `ActiveTask`、执行器重发当前任务保留后续消息、畸形 JSON-RPC 静默 stderr 与非 `google.rpc.Status` REST 错误处理。
  - `PR-08`（`a2a-js#764..#744`、`a2a-go#467..#437`、`a2a-java#1199..#1184`、`a2a-dotnet#572..#568` & `a2a-inspector#213`）：JS JSON-RPC 错误 HTTP `200`、`defaultInputModes` 媒体类型校验与拒绝未应用迁移降级；Go 流式错误透传与保留含下划线任务 ID 的分页令牌；Java 终态入队恢复与多租户路由器；.NET 回环推送目标显式开启门禁。
  - `PR-09`（`stripe/agent-toolkit#560..#464`、`stripe-cli#2149..#2082` & 七语言 SDK）：四大框架适配器 `run_tool()` 接入 `tulip` 准入门禁、`getDefaultMaxTokens` 支持点号与连字符模型 ID、CLI 仅允许已知插件后端自动安装、Python/Java/PHP 事件处理器透传账户作用域与 PHP 忽略畸形 Webhook 签名头分段。
  - `PR-10`（`sierra-research/tau2-bench#677..#632`）：拒绝知识库根目录外沙箱读取、最小环境变量运行沙箱 Shell、黄金动作与工具调用 1 对 1 双射匹配、零售域拒绝同商品换货与电信域空 `mmsc_url` 判未配置。
  - `PR-11..PR-16`（MCP TS/Python/Go/Rust/C#/Java/Kotlin/Swift/Ruby/PHP/Conformance/Inspector/Registry）：TS URI 模板排除 `#` 片段与重启前清空陈旧 stdio 帧 + Python RFC 9449 DPoP 证明、`bytes` Base64 输出与补全分页（`>100`）；Go `initialize` 前请求返回 `-32600`、ID 复用前取消绑定与元数据凭据脱敏 + Rust `2026-07-28` 会话禁服务端下行请求與拒绝多行密钥；C# `ID-JAG` 发现 Issuer 受众绑定 + Java 裸 `\r` 防截断 + Kotlin RFC 3986 SSE 端点解析；Swift PKCE 模偏差字节剔除、保留省略的刷新令牌、头部 Base64 识别与无状态在途 ID 冲突拦截；Ruby 传输错误脱敏 `Authorization` 与非 UTF-8 键 `-32700` + PHP 并行 Elicitation 隔离与不可达会话存储 `503`；以及 Conformance SEP-2243 (`-32020`)、SEP-1932 DPoP 绑定与防降级、全拒绝服务端防虚高绿灯、Inspector 剥离 `npm_config_allow_scripts` 与目录读取缓存作用域及 Registry 可验证数据库备份。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_guards.py`](../../lab/x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_guards.py)
  - 基准生成器：[`lab/x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_bench.py`](../../lab/x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_bench.py)
  - 单元测试：[`tests/test_x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp.py`](../../tests/test_x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp.py)（全仓 **`976/976` 单测通过！**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-stream-clone-ap2-sdjwt-ucp-304-acp-openapi-a2a-stripe-tau2-mcp-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-stream-clone-ap2-sdjwt-ucp-304-acp-openapi-a2a-stripe-tau2-mcp-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-stream-clone-ap2-sdjwt-ucp-304-acp-openapi-a2a-stripe-tau2-mcp-bench/report.json)

---

## Stage 278–279（`972/972` 单测全绿 · 238 项零重叠一手 PR 覆盖！）：Coinbase x402 `eip3009` EIP-712 域映射与 `SAR` 结算见证收据、AgentKit Python ERC-20 整数收据状态与 `cbBTC` 8 位小数及 SPL 整数舍入、UCP RFC 9421 §3.3.3 64 字节 `r||s` ECDSA 与 Python SDK 条件 Schema 及 Conformance HTTPS 发现白名单、ACP 结账变更 `Idempotency-Key` 与 `delegate_payment` 签名强制、A2A RFC 6598 CGNAT (`100.64.0.0/10`) SSRF 防护与 Go 尾随 JSON 拦截、Stripe 七端 SDK 空密钥拦截与 CLI 位置 ID 转义，以及 MCP 九端 SDK 与 Inspector/Registry 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（238 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`coinbase/x402#420`、`#419`、`#414`、`#413`、`#346`、`#334`、`#324`、`#323`、`#322`、`#317`、`#50`、`#48`、`#46`、`#44`）：`exact/evm` `eip3009` 绑定 `PaymentRequirements.extra` EIP-712 `domain.name`/`version`、`SAR` 结算见证收据校验、`no-wallet` 代金券有效期与 `solidarity` 分润基点上限（$\le 10000\text{ bps}$）。
  - `PR-02`（`coinbase/agentkit#1598`、`#1597`、`#1593`、`#1591`、`#1590`、`#1589`、`#1581`、`#1579`、`#1575`、`#1572`、`#1567`、`#1564`、`#1563`、`#1559`、`#1557`、`#1550`）：Python ERC-20 整数收据 `status == 1`、CDP 智能钱包批量子调用回滚拦截、Moonwell `cbBTC` 8 位小数解析、SPL/Jupiter 整数最小单位舍入与 `prePaymentCheck`/`CanaryGuard`/`token_verdict`。
  - `PR-03`（`Universal-Commerce-Protocol/ucp#984`、`#982`、`#981`、`#980`、`#979`、`#977`、`#976`、`#975`、`#974`、`#966`、`#964`、`#963`、`#948`、`#946`、`#945`、`#940`）：RFC 9421 §3.3.3 原始 64 字节 `r||s` ECDSA P-256 签名（拒绝 ASN.1 DER）、显式退货政策窗口与费用、标准履约事件集合及禁根数组 Schema。
  - `PR-04`（`Universal-Commerce-Protocol/python-sdk#101`、`#100`、`#99`、`#96`、`#94`、`#91`、`#89`、`#87`、`#83`、`#76`、`#74`、`#70`、`#69`、`#68`、`#66`、`#64`）：`dependentRequired`、EC JWK `crv`/`x`/`y` 条件规则、`maxProperties`、`additionalProperties: false` 与移除生成 `datetime` 字段的冲突正则。
  - `PR-05`（`Universal-Commerce-Protocol/conformance#113`..`#76` & `samples#253`..`#226`）：严格 HTTPS 商家发现白名单、基于签名负载 `order.id` 的 Webhook 事件身份（拒绝未签名 `X-Event-Type`）、规范顶层 `signing_keys[]` 路径与单支付工具完成校验。
  - `PR-06`（`agentic-commerce-protocol/agentic-commerce-protocol#314`、`#310`、`#305`、`#296`、`#289`、`#288`、`#287`、`#285`、`#284`、`#281`、`#275`、`#266`、`#262`、`#260`、`#256`、`#254`）：变更类结账 MCP 工具强制非空 `Idempotency-Key`、`delegate_payment`/`delegate_authentication` 强制 `Signature`+`Timestamp`、宿主侧支出确认与 Schema ↔ OpenAPI 漂移门禁。
  - `PR-07`（`a2aproject/A2A#2378..#2319` & `a2a-python#1364..#1326`）：RFC 6598 CGNAT (`100.64.0.0/10`) SSRF 拦截、JCS 签名前保留显式默认字段、终态自动补齐 `status.timestamp` 与挂起中断任务驻留超时。
  - `PR-08`（`a2a-js#778..#774`、`a2a-go#453..#434`、`a2a-java#1233..#1224`、`a2a-dotnet#545..#536` & `a2a-inspector#139..#123`）：Go 拒绝尾随 JSON 与孤立代理项签名输入、.NET 拦截负载覆盖认证租户与 JS 删除推送配置非空 ID 校验。
  - `PR-09..PR-10`（Stripe Agent-Toolkit/CLI & 七端 SDK）：CLI 位置资源 ID URL 转义（`#2125`）、回收同级孤儿插件（`#2150`）、跨主版本自动升级拦截（`#2141`）、Toolkit 转发错误即刻返回（`#542`）与切断废弃计量流（`#509`）；五端 SDK 拦截空白 Webhook 密钥、Node `DEFAULT_TOLERANCE`、PHP 客户端重试保留 `Idempotency-Key`（`#2175`）、.NET 序号路径比较（`#3466`）与 Ruby `SingletonAPIResource` v2 守卫（`#1992`）。
  - `PR-11..PR-16`（MCP TS/Python/Go/C#/Rust/Java/Kotlin/Inspector/Registry）：TS `Object.create(null)` 注册表（`#3040`）、丢弃重连前过期 `listTools` 缓存写入（`#3092`）、`Mcp-Param`/`Mcp-Name` 字符校验（`#3063`）与握手超时（`#3079`）；Python 拒绝非 UTF-8 `UriTemplate` 百分号序列（`#3750`）、`now >= expires_at` 精确过期（`#3730`）、SSE 响应头列表深拷贝（`#3726`）与未知工具 `-32602`（`#3697`）；Go `ID-JAG` 仅发往 AS（`#1438`）、发现认证失败禁降级免认证 `initialize`（`#1425`）、精确整数 JSON-RPC ID（`#1441`）与错误结果省略 `structuredContent`（`#1397`）；C# OAuth `S256` PKCE 与大小写敏感属性绑定（`#1949`/`#1934`）+ Rust 无会话非 `initialize` POST `400` 与 `401`/`403` 透传（`#1377`/`#1341`）；Java 异常链脱敏与 `application/json` POST（`#1184`/`#1207`）+ Kotlin 拒绝空白 URI 与越界模板捕获（`#1117`）；以及 Inspector 跨客户端 DCR 密钥隔离、非回环绑定与 Vite CORS 限制、超大错误转发明文帧头清洗及 Registry `*.gitlab.io` 共享域名拦截与 `repository.id` 锁定（`inspector#2792..#2739`、`registry#1574`/`#1570`）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_guards.py`](../../lab/x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_guards.py)
  - 基准生成器：[`lab/x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_bench.py`](../../lab/x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_bench.py)
  - 单元测试：[`tests/test_x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp.py`](../../tests/test_x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp.py)（全仓 **`972/972` 单测通过！**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-eip3009-sar-ucp-rfc9421-acp-idempotency-a2a-cgnat-stripe-mcp-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-eip3009-sar-ucp-rfc9421-acp-idempotency-a2a-cgnat-stripe-mcp-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-eip3009-sar-ucp-rfc9421-acp-idempotency-a2a-cgnat-stripe-mcp-bench/report.json)

---

## Stage 276–277（`968/968` 单测全绿 · 203 项零重叠一手 PR 覆盖！）：x402 Starknet 付款人范围 `Transfer` 与 Hedera 共识记录净入账及 Go 任意精度覆盖金额、UCP 事实准确性审计与 MCP 受保护工作流环境、A2A §5.4 6 处错误状态码修正与多方案 `AND` 授权及映射 IPv6 SSRF 防护、Stripe Node-AWS 工作负载身份试点与 Python `.pre_handle` 及 CLI 24h 升级冷静期、AgentKit `uploadMedia` `cwd` 禁锢与 `ActionRefVerify`，以及 MCP 六端 SDK 与 Inspector 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（203 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3126`、`#3124`、`#3122`、`#3120`、`#3115`、`#3114`、`#3105`、`#3101`）：Starknet `exact` 付款人范围 `Transfer`（`from == payer`）校验、TS `spendControls` 默认 `$1 USD` 上限、SVM 智能钱包 `ComputeBudget` 与算子算力价格上限、XRPL 解码字段白名单与规范字节校验，以及 EVM 模拟回滚（不可重试）与 RPC 故障（可重试）分离。
  - `PR-02`（`x402-foundation/x402#3067`、`#3061`、`#3060`、`#3058`、`#3055`、`#3053`、`#3036`、`#3033`、`#3032`、`#3031`）：Hedera HTS 共识记录收款方净入账校验、MCP `SettleResponse.success === false` 扣留工具结果、Go `permit2` 与 Python `eip3009` 结算后 `Transfer` 日志校验、通配路由 `DOTALL` 换行绕过防御，以及 MCP 402 恢复重签前重跑审批钩子。
  - `PR-03`（`x402-foundation/x402#3027`、`#3026`、`#3022`、`#2987`、`#2985`、`#2984`、`#2981`、`#2974`、`#2964`、`#2962`、`#2957`、`#2933`、`#2923`、`#2917`、`#2914`、`#2912`）：服务端/客户端 `builder-code` `s` 数组合并（上限 5 项）、Go 钩子错误传播与 `512 KB` 响应体上限、JSON 402 `Cache-Control: no-store`、未匹配网络故障关闭、Go 任意精度覆盖金额算术、SVM SIWx 小阶公钥拦截与 Go 重试请求体保留。
  - `PR-04`（`Universal-Commerce-Protocol/ucp#874`、`#734`、`#683` & `modelcontextprotocol/modelcontextprotocol#3426`、`#3406`、`#3404`、`#3390`、`#3386`、`#3385`、`#3383`、`#3380`）：UCP 事实准确性审计、Food TC 公告与领域轮播资源，以及 MCP 规范受保护工作流环境隔离、基础设施工作组章程与首页安全策略入口。
  - `PR-05`（`a2aproject/A2A#2237`、`#2232`、`#2230`、`#2227`、`#2226`、`#2225`、`#2224`、`#2223`、`#2222`、`#2219`、`#2205`、`#2204`）：A2A `v1.0.1` §5.4 错误映射表 6 处 HTTP/gRPC 状态码修正、`jcs_edge_v1` 孤立代理项拒绝与 `-0.0` 归零，以及 A2A vs. MCP 授权发现对比。
  - `PR-06`（`a2aproject/a2a-python#1144`、`#1143`、`#1142`、`#1140`、`#1139`、`#1137`、`#1127`、`#1126`、`#1125`、`#1116`、`#1115`、`#1114`）：多方案安全要求强制 `AND` 语义、REST 路径参数（`task_id`/`push_id`）防穿越清洗、推送通知 `Authorization` 头、满队列慢订阅者驱逐与 `ActiveTask.cancel()` 上下文恢复。
  - `PR-07`（`a2aproject/a2a-java#1109`、`#1104`、`#1099`、`#1098`、`#1097`、`#1096`、`#1095`、`#1090`、`#1088`、`#1085` & `a2a-js#781`、`#779`、`#702`、`#693`）：`DefaultRequestHandler` 故障关闭任务授权、`AuthInterceptor` 头白名单/CRLF/禁用重定向（`GHSA-9rhm-2h4x-jwmx`）与 `PushNotificationUrlValidator` 映射 IPv6（`::ffff:127.0.0.1`、`::ffff:169.254.169.254`）SSRF 拦截。
  - `PR-08..PR-10`（Stripe Node/Python/Go/CLI）：Node-AWS 工作负载身份短期令牌试点（`#2846`）、从 `Stripe.V2List<T>` 移除 V1 遗留字段（`#2856`）与回调上下文隔离（`#2855`）；Python `EventNotificationHandler` `.pre_handle` 前置钩子与异步事件处理（`#1881`、`#1888`）；Go `ConstructEvent` 拒绝空密钥（`#2429`）与 CLI 空格布尔参数（`#2105`）及 24 小时升级冷静期（`#2095`）。
  - `PR-11`（`coinbase/agentkit#1459`、`#1458`、`#1457`、`#1455`、`#1454`、`#1453`、`#1452`、`#1448`、`#1444`、`#1431`、`#1430`、`#1426`）：`uploadMedia` `realpath` 工作目录禁锢、x402 `beforePayment` 收款方筛查、`ActionRefVerify` 内容寻址 `aref_` 校验、`Beaver Knight` 信任评分与只读 `TaskMarket`。
  - `PR-12..PR-16`（MCP Go/Rust/Python/TS/C#/Java/Inspector）：Go `oauthex` DCR 1 MiB 上限（`#1219`）、版本白名单（`#1216`）、`subscriptions/listen` 清理（`#1203`）与 `SSEServerTransport` 关流排空（`#1199`）；Rust 退役会话晚到回复拦截（`#1217`）、严格 `Origin` `403`（`#1216`）与无会话 `server/discover` 回退（`#1221`）；Python `Host`/`Origin` 大小写无关校验（`#3450`）、自定义 `request_id` 计数器推进（`#3438`）、`NaN`/`Infinity` 归一为 `null`（`#3433`）与空闲会话淘汰（`#3445`）；TS `InMemoryTransport` 队列保序与关闭清空（`#2982`/`#2981`）、`listTools` 失败保留缓存（`#2984`）、同块进度先于结果（`#2983`）与 `ReadBuffer` 线性扩容（`#2976`）；以及 C# 整数 `ProgressToken` 与探测超时保活（`#1834`/`#1832`）、Java `200` 非法 JSON 报错与 `U+2028` 防截断（`#1161`/`#1150`/`#1138`）及 Inspector `400` 纪元回退与机密客户端密钥保留（`#2684`/`#2678`/`#2671`）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_guards.py`](../../lab/x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_guards.py)
  - 基准生成器：[`lab/x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_bench.py`](../../lab/x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_bench.py)
  - 单元测试：[`tests/test_x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp.py`](../../tests/test_x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp.py)（全仓 **`968/968` 单测通过！**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-starknet-hedera-ucp-a2a-and-auth-stripe-aws-agentkit-mcp-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-starknet-hedera-ucp-a2a-and-auth-stripe-aws-agentkit-mcp-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-starknet-hedera-ucp-a2a-and-auth-stripe-aws-agentkit-mcp-bench/report.json)

---

## Stage 274–275（达成 275 阶段里程碑 · `964/964` 单测全绿！）：x402 SVM `TransferChecked` 鉴别器与 Go `spendControls` 及 `offer-receipt` v2 交付证明哈希、UCP 站外链接识别与 `gh-pages` 串行超时、A2A Webhook SSRF 防护与终态逃逸拦截及 Java 默认禁重定向、Stripe Python `APIRequestor` 恶意 URL 防护、AgentKit ERC-20 提示词注入清洗与 x402 报价绑定，以及 MCP 七端 SDK 与 Inspector `SEP-2663` 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（137 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3132`、`#3133`、`#3153`、`#3180`）：TS SVM `exact` 强制 `data[0] === 12`（`TransferChecked` 鉴别器）、TS SIWX 客户端挑战绑定 402 响应 Origin、Monad USDC v1 EIP-712 `domain.name = "USDC"`，以及缺失/空 `accepted` 返回稳定协议错误而非抛出 `TypeError`。
  - `PR-02`（`x402-foundation/x402#3156`、`#3155`、`#3164`、`#3183`、`#3190`）：Go SDK 买方 `spendControls`（单次上限、累计上限、收款白名单）、TS SVM `upto` `ComputeBudget` 指令、SVM `batch-settlement` 方案与注入式 RPC 客户端。
  - `PR-03`（`x402-foundation/x402#3186`、`#3131`、`#3241`、`#3255`、`#3274`、`#3315`）：`offer-receipt` v2 交付证明 `responseHash` 绑定、实验性 `shared-payment-token` (`spt`) 固定价格方案、多语言默认资产对齐与 `builder-code` `a` 字段校验。
  - `PR-04`（`Universal-Commerce-Protocol/ucp#889`、`#888`、`#886`、`#885`、`#878`、`#851`、`#772`、`#704`、`#700`）：`check_links.py` 站外/协议相对链接识别、`gh-pages` 部署并发串行与超时、通过 `uv` 运行 pre-commit 校验器与最新规范链接对齐。
  - `PR-05`（`a2aproject/A2A#2322`、`#2319`、`#2310`、`#2270`、`#2246`、`#2240`）：`SendMessageRequest` 客户端写入 `artifacts`、`TASK_STATE_INPUT_REQUIRED`/`AUTH_REQUIRED` 非终态中断语义、`jcs_depth_v1` 128 层嵌套上限与 `Message.sender` 归属。
  - `PR-06`（`a2aproject/a2a-python#1164`、`#1218`、`#1220`、`#1222`、`#1225`、`#1243`）：推送通知派发前 Webhook URL SSRF 拦截（阻断 `169.254.169.254`/内网/回环）、内存推送配置深拷贝防外部篡改、越界 `datetime` 任务排序防护、SSE 关闭宽限期与 `A2A-Version` 次版本校验。
  - `PR-07`（`a2aproject/a2a-python#1183`、`#1182`、`#1180`、`#1177`、`#1176`、`#1167`、`#1165`、`#1158`、`#1153`）：拦截终态任务回退至 `WORKING`、JSON-RPC/gRPC 内部异常脱敏、`history_length` 上限、任务 ID 长度与消息内容非空校验，以及 TCK `Task` 先于状态更新入队。
  - `PR-08`（`a2aproject/a2a-java#1141`、`#1148`、`#1149`、`#1156`、`#1163`、`#1124`、`#1112` & `a2aproject/a2a-js#743`）：`PostBuilder.followRedirects` 默认 `false` 防跨域凭据泄露、`SSEParserConfig` 1 MB 单行上限、单任务推送保序与未知租户公共 AgentCard 返回 `404`。
  - `PR-09..PR-11`（Stripe Node/Python/Go/CLI）：Node 移除顶层 `constructEventWithoutVerification`（`#2862`）与 `ErrorType` 导出（`#2865`）并要求 Node $\ge 20$（`#2871`）；Python `APIRequestor` 拦截恶意跨站/穿越资源 URL 防止 `fetch_related_object()` 泄露 API Key（`#1896`）并移除 `StripeObject.request`（`#1914`）；Go 精确十进制字符串类型（`#2442`/`#2455`）、动态 Map（`#2440`/`#2451`）、Go $\ge 1.24$（`#2453`）与 CLI 自定义安装目录保留（`#2111`）。
  - `PR-12`（`coinbase/agentkit#1480`、`#1468`、`#1481`、`#1479`、`#1474`、`#1473`、`#1464`、`#1462`）：ERC-20 代币元数据间接提示词注入清洗、x402 一次性报价与结算身份及 `maxPaymentUsdc` 绑定、`merona` 卖方预检、`TruthBear`、`DefiLlama` 与 `Taskmarket`。
  - `PR-13..PR-16`（MCP Go/Rust/Python/TS/C#/Java/Kotlin/Inspector）：Go 旧版传输请求体大小限制（`#1224`）、CORS 禁 `OPTIONS`（`#1223`）、`json.Number` 精度保留（`#1244`）与 Rust SSE 重连指数退避饱和封顶防溢出 panic（`#1231`）；Python 逐字节保留无路径 OAuth `resource` 标识符（`#3462`）与回放缓冲（`#3541`）+ TS 多 `Set-Cookie` 数组独立转发（`#2990`）与重启清空残留 stdio 帧（`#2993`）；C# `SseClientSessionTransport` 释放 POST 响应（`#1841`）与 CIMD `none` 认证（`#1845`）+ Java 非法请求体返回 `400`（`#1168`）+ Kotlin `SEP-986` 工具名校验（`#695`）；以及 Inspector 在 `2026-07-28` 连接隐藏 `'Run as task'`（`#2687`）、全模式 `--version`（`#2695`）与 TUI `Esc` 清除过滤词（`#2693`）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp_guards.py`](../../lab/x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp_guards.py)
  - 基准生成器：[`lab/x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp_bench.py`](../../lab/x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp_bench.py)
  - 单元测试：[`tests/test_x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp.py`](../../tests/test_x402_transfer_checked_ucp_a2a_ssrf_stripe_requestor_agentkit_mcp.py)（全仓 **`964/964` 单测通过，达成 275 阶段里程碑！**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-transfer-checked-ucp-a2a-ssrf-stripe-requestor-agentkit-mcp-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-transfer-checked-ucp-a2a-ssrf-stripe-requestor-agentkit-mcp-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-transfer-checked-ucp-a2a-ssrf-stripe-requestor-agentkit-mcp-bench/report.json)

---

## Stage 272–273（`960/960` 单测全绿！）：x402 离线 `authority` 支出授权令与请求指纹绑定 `payment-identifier` (409) 及 Bazaar 不动点 URL 解码、UCP 购物扩展嵌套目录与 `#fragment` 链接保留、A2A Python/Go/JS/Java/.NET 五端流式与状态恢复防线、Stripe API v2 Search POST 分页重放与 Agent Toolkit 256 通道 402 微钱包、AgentKit `x402receipts` 与 `RsoftBank` 借贷，以及 MCP 六端 SDK 与 Inspector Skills 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（86 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3220`、`#3218`、`#3192`）：离线可验证 `authority` 支出授权令（委托人身份与金额上限校验）、`payment-identifier` 缓存绑定 HTTP 请求指纹（篡改或并发冲突返回 `409 Conflict`）与 Python SIWX 挑战绑定请求 `Origin`。
  - `PR-02`（`x402-foundation/x402#3213`、`#3214`、`#3205`）：Bazaar `routeTemplate` 循环不动点 `decodeURIComponent` 解码阻断 `%252e%252e` 穿越、已广播超时交易 `settlement_pending` 自动恢复保留 `txHash`，以及 Hedera `transferExecutor` 授权校验。
  - `PR-03`（`x402-foundation/x402#3233`、`#3228`、`#3227`、`#3203`、`#3197`）：Python `FacilitatorWeb3Signer` 可配置 `gas_limit`、按 `--families` 派生 EVM/SVM 签名器、Sei 主网/测试网默认原生 USDC，以及 `auth-capture` v1.1 预授权与部分捕获。
  - `PR-04`（`Universal-Commerce-Protocol/ucp#761`、`#759`、`#726`、`#720`、`#607`、`#465`）：购物扩展归入 `shopping/extensions/`、根规范链接保留 `#fragment`、`build_local.sh` 缺失 `ucp-schema` 快速失败、`llms.txt` 索引分单支付与术语表、`line_item.note`（$\le 500$ 字符）与参考页渲染 `response_catalog_schema`。
  - `PR-05`（`a2aproject/a2a-python#1365`、`#1362`、`#1360`、`#1358`、`#1357`）：`TaskUpdater` 状态事件校验通过前不锁死终态、v0.3 未设置 `status.update`/`provider` 保持 `None`、AgentCard JCS 签名前保留显式默认字段、每客户端独立 `httpx` 实例与集群表惰性创建。
  - `PR-06`（`a2aproject/a2a-go#480`、`#479`、`#474`、`#471`、`#468`、`#463`）：REST 端点保留自带查询参数、`ServiceParams` 键统一小写、`Typed.MarshalJSON` 空 Map 防 panic、非 A2A 网关错误按状态码映射、`application/a2a+json` 协商与流式首包前错误直接返回。
  - `PR-07`（`a2aproject/a2a-js#791`、`#788`、`#787`、`#770` & `a2a-java#1209`、`#1202`）：gRPC 首包事件后发送含动态扩展的响应元数据、SSE 错误事件直接抛出类型化错误、亚毫秒 `statusTimestampAfter` 精度保留、跳过未知流负载，以及 Java REST SSE 正常完成回调与 `close()` 取消在途 Future。
  - `PR-08`（`a2aproject/a2a-dotnet#554`、`#553`、`#552`、`#548`、`#546`）：`ContinueTaskAsync` 主动续跑、统一上下文感知 `IA2ARequestHandler`、非 `text/event-stream` 流式响应报错、注册表扩展协商与 JSON-RPC 重复键递归拒绝。
  - `PR-09..PR-11`（Stripe Node/Python/Go/CLI/Agent Toolkit）：API v2 Search POST 原始请求体分页重放（`stripe-node#2884`、`stripe-go#2464`）、`V2SearchResult` CJS 导出（`#2900`）、异步通知验签与 Fetch 未读流释放（`#2896`）、`OPENAPI_VERSION` 锁定 `stripe-mock`（`stripe-python#1927`、`stripe-go#2452`）、Python 仅位置重载路径参数（`#1924`）、CLI 插件 `AdditionalInfo` 版本（`#2133`）与 `install.ps1` 版本固定（`#2127`）及文档遥测状态码区分（`#2123`）、Agent Toolkit 未知配置键告警（`#525`）、空 `choices` `NoContentGeneratedError`（`#500`）、Agent Plugins 1.0（`#487`）、Claude 钩子（`#515`）与 256 通道 402 微钱包（`#506`）。
  - `PR-12`（`coinbase/agentkit#1523`、`#1501`、`#1489`、`#1488`、`#1482`）：`x402receipts` 可审计支出对账、CDP `sendTransaction`/`sendUserOperation` `idempotencyKey` 透传、只读 `AssetFare` 报价、`RsoftBankActionProvider` Base USDC 借贷与 `solana>=0.36.6,<0.37`。
  - `PR-13..PR-16`（MCP Go/Rust/Python/TS/C#/Inspector）：Go `Tool.Execution.TaskSupport` 与 `Task` 类型保真（`go-sdk#1336`/`#1335`）、Rust 重复 `SEP-2243` 头拒绝与旧版服务器拒绝 `server/discover` 及传输关闭取消（`rust-sdk#1365`/`#1324`/`#1286`/`#1280`/`#1274`/`#1269`/`#1267`）、Python Skills `%2e%2e` 穿越解码与 RFC 6749/7009 错误码对齐及 `stdio_client` O(N) 分块读取（`python-sdk#3733`/`#3731`/`#3722`/`#3705`/`#3703`）、TS 资源标题实时更新与无状态 405 `Allow: POST` 及按需编译输出校验器 + C# 端点授权与 Native AOT `List<object>`（`typescript-sdk#3006`/`#3005`/`#3002`/`#2998`、`csharp-sdk#1880`/`#1872`/`#1870`），以及 Inspector `skills/get` 实时重读文件、按客户端表面预算提示、`-q` 静默 `--output` 与 `--completion` `EPIPE` 防护（`inspector#2708`/`#2706`/`#2702`/`#2700`/`#2698`/`#2694`）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_guards.py`](../../lab/x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_guards.py)
  - 基准生成器：[`lab/x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_bench.py`](../../lab/x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_bench.py)
  - 单元测试：[`tests/test_x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills.py`](../../tests/test_x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills.py)（全仓 **`960/960` 单测通过**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-authority-ucp-a2a-rest-stripe-v2-search-agentkit-mcp-skills-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-authority-ucp-a2a-rest-stripe-v2-search-agentkit-mcp-skills-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-authority-ucp-a2a-rest-stripe-v2-search-agentkit-mcp-skills-bench/report.json)

---

## Stage 270–271（达成 270 阶段里程碑 · `956/956` 单测全绿！）：x402 `EXTENSION-RESPONSES` 内部侧信道剥离与 Upto Permit2 CREATE2 恢复 / Batch-Settlement 客户端本地通道派生与 Upfront Exact 免 402 流程、A2A Go `Accept` 协商与 UTC `.sssZ` 及终态 `ErrUnsupportedOperation` / Java 原子单次终态 SSE 与空 ID 归一化及 RFC 3986 重定向 / .NET 解析脱敏与 Python 纳秒整数排序、Stripe Node 截断响应体归类与 ESM 构造导出 / Python 30 字节 CSPRNG Multipart 与 Header 转义 / CLI Profile OAuth 同步与 Windows 重命名重试、AgentKit `x402Scraper` / `SapienVault` / Solana 延迟加载，以及 MCP 八端 SDK 与 Inspector 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（53 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3278`、`#3275`）：`@x402/core` 将 Facilitator `EXTENSION-RESPONSES` 解码至服务端专属 `extensionResponses` 侧信道并在编码买方 `PAYMENT-RESPONSE` 前剥离；恢复 `x402UptoPermit2Proxy` 规范 CREATE2 地址 `0x4020A4f3b7b90ccA423B9fabCc0CE57C6C240002`。
  - `PR-02`（`x402-foundation/x402#3251`、`#3240`）：Batch-Settlement 客户端从本地状态派生 `local_cumulative + min(chargedAmount, maxAllowed) + clientSignedDeposit`，服务端 `chargedCumulativeAmount` 不匹配时拒绝覆写本地存储，退款封顶于本地可退余额，并支持 Upfront Exact 免 402 流程。
  - `PR-03`（`a2aproject/a2a-go#465`、`#452`、`#442`）：按 `Accept` 协商 `application/a2a+json`、`TaskStatus.Timestamp` 统一格式化为 UTC `.sssZ` 毫秒精度，且对已落盘终态任务返回 `ErrUnsupportedOperation`。
  - `PR-04`（`a2aproject/a2a-java#1181`、`#1179`、`#1174`、`#1173`、`#1172`、`#1162`）：`AbstractSSEEventListener` 共享 `AtomicBoolean` 保证单次终态回调、空字符串 `taskId`/`contextId` 归一化为 `null`、`URI.create(url).resolve(location)` 解析相对重定向、`A2ACardResolver` 回退 URL 与 gRPC 显式 JSON `null`。
  - `PR-05`（`a2aproject/a2a-dotnet#452`、`a2a-js#737`/`#726`、`a2a-python#1233`）：`A2AJsonRpcProcessor` 解析错误脱敏为 `"Invalid JSON payload"`（`CWE-209`）、v0.3 推送转 v1.0 `StreamResponse` 与自定义 SQL 表名校验，以及 `InMemoryTaskStore.list()` 改用 `ToNanoseconds()` 整数排序。
  - `PR-06`（`stripe/stripe-node#2888`、`#2868`、`#2867`）：中途截断响应体归类为可重试 `StripeConnectionError`、`NodeHttpClient` 立即 `write`/`end` 避免 Nock 14 / MSW 挂起，并导出可构造 ESM `Stripe` 类。
  - `PR-07`（`stripe/stripe-python#1904`、`#1902`、`#1898`）：`secrets.token_hex(30)` 240-bit CSPRNG Multipart boundary、`Content-Disposition` `"`/`\r`/`\n` 转义防参数注入、支持 `id=None` 的 v2 单例 `RelatedObject` 与非空 Webhook 密钥校验。
  - `PR-08`（`stripe/stripe-cli#2128`、`#2126`、`#2116`）：同步 `-p / --project-name` Profile 与 OAuth 活跃上下文，以及 Windows `replaceBinary` 文件共享冲突重试。
  - `PR-09`（`coinbase/agentkit#1495`、`#1493`、`#1490`）：`CdpSolanaWalletProvider` 延迟导入 Solana 依赖、`SapienVaultActionProvider` Base 主网（`8453`）金库校验与 `x402ScraperActionProvider` 双轨 Base USDC 结算。
  - `PR-10..PR-11`（`modelcontextprotocol/go-sdk#1316`、`#1278`、`#1267`、`#1255`、`#1246`、`#1245`）：`IsLoopback` 大小写无关匹配 `"localhost"`、延迟构建 `defaultDiscoveryTransport` 尊重 `HTTPS_PROXY`、`2026-07-28` Stdio 已取消请求静默不回包、取消原因注入 `context.Cause`、非安全 `Mcp-Name` Base64 编码与 OAuth Issuer 尾斜杠剥离。
  - `PR-12`（`modelcontextprotocol/rust-sdk#1318`、`#1264`、`#1248`）：`.well-known` 401 中的 `resource_metadata` 指针归类为 `WellKnownGuess` 保留候选回退、`server/discover` 保持引导中立，以及免 `macros` 导出 `object!`。
  - `PR-13..PR-16`（MCP Java/C#/Kotlin/PHP/Conformance/Inspector）：`java-sdk#1179`/`#1178`/`#1175`（`Boolean.TRUE.equals(listChanged)` 空安全与 `listXyz` `Mono.defer` 订阅隔离）、`csharp-sdk#1855`/`#1852`/`#1844`（`server/discover` 400/404 跳过 SSE 回退、旧版会话忽略新 `_meta` 与 400 解析详情）、`kotlin-sdk#1092`/`#1089` & `php-sdk#465` & `conformance#447`/`#442`（`pluginOrNull(SSE)`、`Task.ttl` 显式 `null` 与 PHP 可变参数逐元素强转），以及 `inspector#2696`/`#2692`/`#2691`/`#2690`（OAuth 新锁竞争 `renameSync` 恢复、无 `WWW-Authenticate` 403 非挑战识别、无元数据端点覆盖与 TUI 临时令牌文件退出清理）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_guards.py`](../../lab/x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_guards.py)
  - 基准生成器：[`lab/x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_bench.py`](../../lab/x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_bench.py)
  - 单元测试：[`tests/test_x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio.py`](../../tests/test_x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio.py)（全仓 **`956/956` 单测通过**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-ext-sidechannel-a2a-utc-stripe-multipart-agentkit-mcp-stdio-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-ext-sidechannel-a2a-utc-stripe-multipart-agentkit-mcp-stdio-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-ext-sidechannel-a2a-utc-stripe-multipart-agentkit-mcp-stdio-bench/report.json)

---

## Stage 268–269（突破 950+ 单测里程碑 · `952/952` 单测全绿！）：`@x402/next` 空查询保留与 `req.clone().json()` / `@x402/axios` `getUri` 与签后超时对账、A2A AgentCard 剥离签名弱 `ETag` (`W/"..."`) / 执行前 `contextId` 绑定与终态任务拦截 / `validate_input_modes` 与 Java REST `%d` 及 `id:null`、Stripe Node 空白 Webhook 密钥与空值合并容差 / Stripe Python 事件上下文隔离 / Stripe CLI 路径段转义与显式 `HookBaseURLs`、AgentKit `dexter` / `WalletForge` / `HCRB`，以及 MCP Go/Rust/Java/C#/Inspector 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（29 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3456`、`#3451`）：`@x402/next` 使用 `if (existing !== undefined)` 保留 `?tag=&tag=b` 前导空字符串，并通过 `this.req.clone().json()` 读取请求体防止吞噬下游路由请求流。
  - `PR-02`（`x402-foundation/x402#3454`、`#3387`）：`@x402/axios` 使用 `new URL(axiosInstance.getUri(config)).href` 保留 `baseURL` 路径段与 `params`，并在 `PAYMENT-SIGNATURE` 发出后遇超时或 `settlement_pending` 时禁止盲目自动重付。
  - `PR-03`（`a2aproject/a2a-python#1272`）：AgentCard 弱 `ETag` (`W/"<sha256>"`) 计算前剔除 `signatures` 字段，消除随机 `ECDSA_SHA_256` 签名导致的缓存失效并支持 RFC 9110 §8.2.2 `304 Not Modified`。
  - `PR-04`（`a2aproject/a2a-python#1270`、`#1268`）：在 `executor.execute` 启动前校验 `message.context_id == task.context_id`（不匹配抛 `InvalidParamsError`），并对终态任务操作抛出 `UnsupportedOperationError`（取消抛 `TaskNotCancelableError`）。
  - `PR-05`（`a2aproject/a2a-python#1269` & `a2a-java#1200`、`#1198`）：`@validate_input_modes` 校验 `default_input_modes ∪ skill.input_modes`、Java REST `/tasks/%s?historyLength=%d` 消除 `%2d` 空格，以及 `JsonUtil.writeJsonRpcId` 强制输出 `"id": null`。
  - `PR-06`（`stripe/stripe-node#2885`、`#2876`）：`isBlankWebhookSecret` 拦截全空白 Webhook 密钥，且 `verifyHeader`/`verifyHeaderAsync` 使用 `tolerance ?? Webhook.DEFAULT_TOLERANCE`（默认 300s，`0` 显式跳过）。
  - `PR-07`（`stripe/stripe-python#1920`、`#1911`）：`StripeClient.with_stripe_context` 在 `parse_event_notification` 回调中不继承父级 `stripe_account`，且服务路径参数强制仅限位置传入（`/`）。
  - `PR-08`（`stripe/stripe-cli#2134`、`#2125`、`#2124`）：`EscapePathSegment` 拒绝 `""`/`.`/`..`、`formatURL` 对位置 ID 执行 `url.PathEscape`，且插件 `Install`/`Upgrade` 仅转发显式 `HookBaseURLs`。
  - `PR-09`（`coinbase/agentkit#1487`、`#1491`、`#1492`）：`KNOWN_FACILITATORS` 新增 `dexter`（`https://x402.dexter.cash`）、`WalletForgeActionProvider` Base USDC 限价（`$0.05`/`$0.01`）与 `HcrbActionProvider` Base 链 ID 门禁（`8453`/`84532`）。
  - `PR-10..PR-11`（`modelcontextprotocol/go-sdk#1289`、`#1283`、`#1277`、`#1268`）：区分存在但为空的 `Mcp-Param-*` 头与缺失头、`ClientSession.resourceSubs` 单调代次 `gen uint64`、Stdio 批处理仅追踪 `req.IsCall()`，以及 `_meta.protocolVersion` 集合成员校验。
  - `PR-12..PR-13`（`modelcontextprotocol/rust-sdk#1270`、`#1263`、`#1262`）：`AllowedPort::Exact` 归一化 `Origin` 默认端口（`80`/`443`）、免握手会话首包进入 `serve_inner` `batch_messages` 防死锁，以及 `notifications/cancelled` 按 `is_subscription` 路由。
  - `PR-14..PR-16`（MCP Java/C#/Inspector）：`java-sdk#1185`/`#1184`（按 `sessionSweepInterval` 清扫闲置无流会话并剥离 `JSONRPCError.data` 内部异常链）、`csharp-sdk#1860`/`#1856`（`_serverLifetimeCts` 先取消 + 发布后复检消除 MRTR 释放竞态，以及拒绝文档软链）、`inspector#2701`/`#2699`（拦截位置目标/`--server-url`/`stdio` 冲突并自动路由 `taskSupport == "required"` 至任务流）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_guards.py`](../../lab/x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_guards.py)
  - 基准生成器：[`lab/x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_bench.py`](../../lab/x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_bench.py)
  - 单元测试：[`tests/test_x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep.py`](../../tests/test_x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep.py)（全仓 **`952/952` 单测通过**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-next-axios-a2a-etag-stripe-webhook-agentkit-mcp-sweep-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-next-axios-a2a-etag-stripe-webhook-agentkit-mcp-sweep-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-next-axios-a2a-etag-stripe-webhook-agentkit-mcp-sweep-bench/report.json)

---

## Stage 266–267（`948/948` 单测全绿！）：x402 SVM Exact `SettlementResponse.payer` 买家权限归因 / Cardano 托管回调解耦 / Python `solana<0.40` 封顶 / `verify:exports` 故障关闭、A2A Python REST `{path_prefix}/{tenant}` 挂载 / JSON-RPC 畸形包与扩展错误映射 / 跨四端 SDK AgentCard 签名互操作、Stripe CLI 跨主版本升级拦截与 Node/Go SDK 重试流销毁及空页死循环护栏、Coinbase AgentKit `x402Guard` / `KeeperHub` 幂等重放，以及 MCP 五语言 SDK 确定性门禁与 7-Card 基准报告

- **一手协议覆盖（29 项零重叠上游 PR，`PR-01..PR-16`）**：
  - `PR-01`（`x402-foundation/x402#3941`）：对齐 `scheme_exact_svm.md` 中 `SettlementResponse.payer` 规范定义，强制校验其为买家钱包 Base58 地址（SPL 转账指令 `transferIx.accounts[3]` 签名授权方），拦截误返回 Facilitator 手续费代付方（`transactionMessage.feePayer` / `accountKeys[0]`）的结算响应。
  - `PR-02`（`x402-foundation/x402#3594`）：`e2e/src/mechanisms.ts` 移除构建前对 `@x402/cardano` 的直接导入，通过注入 `masumiEscrowAddress?: (network: string) => string` 回调动态解析 `cardano:*` 收款地址。
  - `PR-03`（`x402-foundation/x402#3573`）：Python `x402[svm]` 显式封顶 `solana>=0.36.0,<0.40`，阻断 `solana 0.40.0` 移除 `solana.rpc.api` 导致的 `KeypairSigner` 导入崩溃。
  - `PR-04`（`x402-foundation/x402#3550`、`#3540`）：TypeScript 发布流水线 `verify-package-exports.mjs` 在 `checkedCount === 0`（除非显式设置 `VERIFY_EXPORTS_ALLOW_EMPTY=1`）或任一声明导出目标文件缺失时以 `process.exit(1)` 故障关闭；并涵盖 `socseal-verify` `ML-DSA-87` 已确认区块高度（`height > 0`）验证。
  - `PR-05`（`a2aproject/a2a-python#1377`）：REST 多租户路由挂载于 `f'{path_prefix}/{{tenant}}'`（而非 `/{tenant}{path_prefix}`），保障 `/a2a/rest/my-tenant/message:send` 正确匹配并提取 `context.tenant`。
  - `PR-06`（`a2aproject/a2a-python#1375`）：`JsonRpcTransport` 拦截非字典 JSON、同时缺失 `result`/`error` 或非整数 `error.code` 并抛出 `A2AClientError`，且在含扩展字段（如 `reason`）时仍通过 `_ERROR_CODE_MAP` 将 `-32001` 精确映射为 `TaskNotFoundError`（含 `delete_task_push_notification_config`）。
  - `PR-07`（`a2aproject/a2a-python#1286`、`#1277`、`#1274`、`#1273`）：跨 Python/JS/Go/参考签名器的 `ES256` AgentCard 签名互操作向量（`S0-001..S0-004` `MUST-ACCEPT`，`S0-REJECT-005` `MUST-REJECT`）、REST 响应 `Content-Type: application/a2a+json`、`ParseDict(..., ignore_unknown_fields=True)` 前向兼容与结构错误 `google.rpc.ErrorInfo` 数组，以及 `v0_3/proto_utils.py` 字段保真。
  - `PR-08`（`stripe/stripe-cli#2155`、`#2143`、`#2141`）：`isMajorPluginUpgrade` 拦截跨主版本（`1.x` $\to$ `2.x`）插件静默自动升级、`explainPinnedVersionNotFound` 二次查询区分 OS/Arch 构建缺失与版本不存在，以及 `release.yml` 向 GoReleaser 注入全部 5 项 macOS 签名与公证密钥。
  - `PR-09`（`stripe/stripe-node#2895` & `stripe/stripe-go#2457`）：`RequestSender` 重试前调用 `res.dispose?.()` 取消/销毁未读响应流、`StripeEventNotificationHandler.handle()` 改用 `parseEventNotificationAsync` 支持异步 Web Crypto，以及 Go `Iter`/`V1List` 拦截 `len(data) == 0 && has_more && !single` 空页死循环（`errEmptyPageWithHasMore`）。
  - `PR-10`（`coinbase/agentkit#1510`、`#1508`、`#1504`）：`x402Guard` 付款前校验 EIP-712 签名的 Bazaar 卖家信誉裁决（拦截 `avoid` 端点），以及 `KeeperHub` 强制 `simulate: true` 预演与基于 `taskId` 的丢包超时幂等重放（消除重复转账）。
  - `PR-11..PR-12`（`modelcontextprotocol/python-sdk#3761`、`#3625`、`#3619`、`#3618`）：`identity_assertion.py` 与 `oauth2.py` 采用严格 `time.time() < self._expiry` 过期边界（RFC 7519 §4.1.4）、内部流探测使用非整数 ID `listen-1`、自定义 `httpx2.AsyncClient` 强制 `read=300.0` 超时，以及 `anyio.move_on_after(5, shield=True)` 取消清理与 `stateless_http=True` 边界。
  - `PR-13..PR-16`（MCP Go/Rust/Java/C# SDK 与 Ext-Apps）：`go-sdk#1293`/`#1292`/`#1290`（每次流写入顺延 `2 * keepAliveInterval` `WriteDeadline`、SSE 放行 `AddReceivingCustomMethod` 自定义方法、`complete`/`getPrompt` 空切片归一化为 `[]`）、`rust-sdk#1285`（仅在 `invalid_grant` 时调用 `on_refresh_token_rejected`）、`java-sdk#1210`/`#1201`（流式每订阅 `notifierFactory` 判空保护与结构化 `LoggingMessageNotification.data` 字符串转义），以及 `csharp-sdk#1878`/`#1874` & `ext-apps#720`（MCP Apps `2026-01-26` 握手、`Clone()` 保留 `MarshalResult` 与 SDK v2 客户端/服务端角色依赖隔离）。
- **新增代码、单测与报告**：
  - 守卫模块：[`lab/x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_guards.py`](../../lab/x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_guards.py)
  - 基准生成器：[`lab/x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_bench.py`](../../lab/x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_bench.py)
  - 单元测试：[`tests/test_x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth.py`](../../tests/test_x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth.py)（全仓 **`948/948` 单测通过**）
  - 7-Card 4:5 视觉基准报告：[`index.html`（中文）](../../reports/agentic-commerce-x402-svm-payer-a2a-tenant-stripe-plugin-agentkit-mcp-auth-bench/index.html) · [`index.en.html`（EN）](../../reports/agentic-commerce-x402-svm-payer-a2a-tenant-stripe-plugin-agentkit-mcp-auth-bench/index.en.html) · [`report.json`](../../reports/agentic-commerce-x402-svm-payer-a2a-tenant-stripe-plugin-agentkit-mcp-auth-bench/report.json)
