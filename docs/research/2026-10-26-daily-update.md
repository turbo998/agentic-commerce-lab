# 2026-10-26 技术资产与架构更新索引（Stages 266–267+）

🌐 **Language / 语言导航**: **中文更新索引 (当前)** | **[English Update Index (`2026-10-26-daily-update.en.md`)](2026-10-26-daily-update.en.md)** | **[2026-10-26 每日研究 (`research/daily/2026-10-26.md`)](../../research/daily/2026-10-26.md)** | **[English Daily Research (`research/daily/2026-10-26.en.md`)](../../research/daily/2026-10-26.en.md)**

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
