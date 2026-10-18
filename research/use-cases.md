# Agent 使用场景与方案验收

验证日期：2026-10-11。以下是原创场景设计；产品对应关系不代表商业准入已完成。

| 场景 | Agent 职责与价值 | 授权/系统边界 | 候选技术与验收 |
|---|---|---|---|
| 对话式零售购买与嵌入式结账 | 需求澄清、商品比较、报价、发起 checkout、追踪履约；通过 SFTP 摄取百万级目录或通过 WebMCP 辅助浏览器结账 | 用户批准最终 SKU/数量/总价/商户；SFTP 以 `manifest.json` 为完成屏障，`disable_checkout=true` 仅跳转 `link`；OCA 仅卖家发起且终止后仅终止方重发起；WebMCP 切换支付方式后必须重发现 Schema，带 `consequentialHint` 工具须先获用户确认，Affirm WebView 严禁 Agent 编程点击 | ACP/UCP/Suite Embedded（OCA `2026-09-30.preview` + `RequestedSession` `2026-04-22.preview`）+ SPT/VIC/Mastercard Agent Pay + WebMCP；见 `lab/ucp_preflight.py` |
| Personal Agent 补货 | 在库存/价格条件满足时提出或执行补货 | 需可信 Open Mandate、周期/累计预算、允许商户、撤销、有效期和替代商品规则 | AP2/VIC 指令机制候选；默认先人工批准。当前 demo 仅 Closed-style final-cart binding，不实现自主循环补货 |
| 旅行与本地服务预订（Service Bookings） | 检索可用时段（`search_availability`）、锁定预订（`create_booking`）、展示取消条款并完成付款（`complete_booking`） | 时段冲突返回 `409 slot_unavailable` 触发重选；`Idempotency-Key` 保留 $\ge 24$h（同键异体返回 `409 Conflict`）；SPT 有效期最长 180 天以覆盖远期入住/服务结算 | Stripe Service Bookings（Muse/Instinct 模式）+ UCP Lodging Booking Draft + `com.stripe.payments`（`2026-06-25`）+ SPT（`2026-09-30.preview`） |
| B2B 发票、目录发现与企业账上划转 | 将工单转成发票、通过 Stripe Directory 发现已验证商户/服务、向 `@handle` 发起 B2B 资金划转 | 创建发票和实际支付分别授权；`stripe directory search` 优先于开放网页搜索；`stripe pay` 要求双方具备 Stripe Profile 与合格资金账户，必须先以 `--agent`/`--json` 预览并在用户确认后才可加 `--yes` | Visa Acceptance Toolkit pilot；Stripe Directory（Preview）+ `stripe pay` CLI plugin |
| 开发 Agent 购买 API/数据 | 选择资源、估算成本、按请求或 session 付费 | 资源/单次/累计预算、网络与钱包隔离、收款地址、challenge freshness、付费后交付 | MPP、x402；402 不能仅以存在付款头放行；结算失败不得交付，已结算记账失败不得再次付款 |
| 商户售后 Agent | 查询订单/物流、提出换货/改单/退款、解释争议 | 查询和修改/退款不同权限；未鉴权不暴露修改工具；单会话跨登出终身绑定单客户（`#49`）；待发货订单商品修改仅限一次；确认前核对 `summary` 与 `terms` 一致（`#51`）；跨通道相同 `terms` 提案去重、下游超时保持 `in_progress` + `Retry-After` 不误报失败（`operations` §§4, 6, 7）；平台不自算退货截止日（UCP `#966`） | Sierra Defense-in-Depth + $\tau^3$-bench 零售策略 + Poppy `operations` v1 两阶段 `revision` 确认 + UCP `policy.return` 预检；见 `lab/poppy_guard.py`、`lab/ucp_preflight.py` |
| 跨渠道个人代理接入企业客服与网页交接（Poppy） | 通过 `/.well-known/poppy.json` 发现企业 API/MCP/对话入口，先只读咨询，必要时升级 OAuth 代客改单或通过 `browser_session_endpoint` 交接至用户浏览器 | 重定向后主机名精确匹配 `organization.domain`（`#37`）；断言 `aud == auth.issuer`（`#50`）；令牌端点拒收 `poppy-browser+jwt`、浏览器交接强制 URL 解析 `return_to` 主机名并用 `SameSite=Lax|None` Cookie（`#35`）；吊销后禁止受托凭证自动重登（`#53`）；阻断跨企业内容注入（`#51`） | Poppy `v0.1` 草案 + `operations` v1 + Company Implementation Kit（`#35`）；Payments 仍为 Open Topic，付款需桥接 UCP/ACP + SPT/VIC |
| 企业语音客服来电核身与收款 | 实时语音接待、识别来电是否为个人 AI Agent、在通话中完成账单或订单尾款支付 | 声学检测（`fleming-1`）仅作阶梯核身信号而不直接拒付；采集卡号时切出 LLM 进入服务端 Level 1 PCI 流 | Sierra Tandem Voice + `fleming-1` + Sierra Payments / Stripe App |
| 财务洞察与采购建议 | 经授权读取交易、余额，建议预算或采购 | Financial insights scope 不包含 spend scope；模型看脱敏数据，敏感原文不写 GitHub | Link Agent Wallet / permissioned accounts；拒绝读取未授权账户，支付仍须独立同意 |

## 第一阶段可运行资产

离线合成商户的最终报价批准与执行最适合作为基线：无需商业准入即可验证核心权限边界，后续将真实 adapter 插入确定性执行层。`python -m lab.demo` 输出 `status=simulated`，并演示进程重建后的同键重试与金额篡改阻断。

## 后续开发优先级

1. 固定 ACP `2026-04-17` 的 OpenAPI/JSON Schema，做自建 merchant stub 与 schema contract tests；实现前审阅许可，不搬运第三方全文。
2. 增加 payment-pending/unknown 状态和故障注入：支付成功但响应丢失、webhook 重复与乱序、库存失败后的补偿。
3. 明确 TAP 签名组件/公钥来源/nonce 存储，做隔离验签实验；不把本地 cart hash 当作 HTTP Message Signature。
4. 在获得账户准入和用户明确批准后，才做 Stripe sandbox SPT/PaymentIntent 集成；固定 preview version，并分别验证 Link OAuth 与 Stripe API 权限。
5. 最后评估 Open Mandate 自主补货与机器钱包，加入累计预算、并发消费、撤销和跨商户部分成功策略。
