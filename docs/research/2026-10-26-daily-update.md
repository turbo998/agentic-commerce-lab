# 2026-10-26 技术资产与架构更新索引（Stages 266–273+）

🌐 **Language / 语言导航**: **中文更新索引 (当前)** | **[English Update Index (`2026-10-26-daily-update.en.md`)](2026-10-26-daily-update.en.md)** | **[2026-10-26 每日研究 (`research/daily/2026-10-26.md`)](../../research/daily/2026-10-26.md)** | **[English Daily Research (`research/daily/2026-10-26.en.md`)](../../research/daily/2026-10-26.en.md)**

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
