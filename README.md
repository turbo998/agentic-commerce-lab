# Agentic Commerce Lab

面向 Personal Agent 的 Agentic Commerce 研究与可运行模拟实验：聚焦商业场景、AI 职责、授权与支付原生架构。

本仓库将研究 Stripe Sessions 2026、Visa Intelligent Commerce / Trusted Agent Protocol、Sierra Agent OS / Personal Agent Protocol（"Poppy" `v0.1` 草案）与公开的 AWS Shopping Concierge 示例，并记录来源、发布日期、适用范围和证据等级。研究内容会区分产品公告、当前文档、协议规范、代码观察和本地模拟，不把演示结果描述为供应商认证或真实支付结算。

## 目标

- 研究 Agent 参与发现、比较、委托、批准、支付、履约和售后的商业价值链。
- 设计把用户同意、交易约束、支付凭证隔离、持久状态和恢复流程放在确定性权限层中的 Personal Agent 架构。
- 提供无需支付账户、真实资金或云资源即可运行的合成购物与支付模拟。
- 将可选模型推理与支付执行隔离；模型只能提出建议和动作请求，不能批准或扩大权限。

默认实验是离线模拟。真实商户支付、账户连接、付费模型调用及云部署均不属于默认能力。请勿输入真实卡号、账户凭证或个人财务数据。

## 研究边界

本仓库只发布原创说明、合成数据和经许可审核的代码；不托管内部材料、客户信息、支付秘密或第三方资料副本。各能力的集成与验证状态会明确标记。

## 研究与技术资产

| 入口 | 内容 |
|---|---|
| [2026-10-19 每日研究](research/daily/2026-10-19.md) | 50 来源监控与 Stripe SPT 三角色变体（Connect 档案路由、单次 `SPT Resolve`、三大卡组织凭证）、MPP Tempo 流式会话亚美分尾差没收与 Token 计费、AP2 `#165` 受托熔断器、UCP `#866` 批量目录摘要屏障、ACP `#316` Appendix C 17 网关映射、AI-Native vs 经典三层六平面重构及 Stripe MCP 42 日核验 |
| [2026-10-18 每日研究](research/daily/2026-10-18.md) | Stripe WebMCP/Booking/Embedded(OCA & RequestedSession)/SFTP Feed/Directory 新文档核验、Poppy `operations` v1 超时 `in_progress`/取消/去重、UCP `#940`/`#970`/`#660`/`#966` 与 ACP ATDRP §7.4a、Stripe MCP 43 日核验 |
| [2026-10-17 每日研究](research/daily/2026-10-17.md) | Poppy `#35` 企业实现套件/18 份 Schema/改造前后架构对照、UCP `#913` Permalink `303` 安全头、Stripe MCP 英式日期核验 |
| [2026-10-16 每日研究](research/daily/2026-10-16.md) | Stripe MCP 迁移延期至 `2026-11-30`、Poppy `v0.1` 17 项安全/DPoP/会话提交、UCP Webhook 签名门禁（`#659`） |
| [2026-10-14 每日研究](research/daily/2026-10-14.md) | Sierra 与 Poppy `v0.1` 草案/当日建仓核验、TAP 迁移、UCP 扩展修复、MCP 告示监测及 17 日窗口 |
| [2026-10-13 每日研究](research/daily/2026-10-13.md) | 官方 skills 增量、可执行能力边界、UCP 离线预检及 MCP 18 日迁移窗口 |
| [2026-10-12 每日研究](research/daily/2026-10-12.md) | 官方证据增量、AI Native 与 WAF 辩证比较、UCP handler 边界及 MCP 迁移盘点 |
| [2026-10-11 研究基线](research/daily/2026-10-11.md) | 发布事实纠错、已有技术资产、证据缺口与日更机制 |
| [协议与产品分层](research/protocols.md) | Visa VIC/TAP/MCP/Toolkit；Stripe ACP/UCP/Suite/SPT/Link/MPP/x402/MCP；Sierra & Poppy `v0.1` |
| [Personal Agent 参考架构](research/architecture.md) | 信任边界、六平面 AI-Native 重构、审批、幂等、异步支付恢复、Sierra 纵深防御与非功能取舍 |
| [Agent 使用场景](research/use-cases.md) | 零售、补货、预订、B2B 开票、API 付费/流式微支付、售后改单（Poppy/Sierra）与财务洞察 |
| [官方来源注册表](research/sources.json) | 50 个来源、验证日期、发布日期、版本与证据边界 |
| [离线 checkout 实验](lab/checkout.py) | 合成报价授权、购物车绑定、单次消费、持久幂等及并发保护 |
| [离线 MCP 迁移盘点](lab/mcp_migration.py) | Stripe MCP `2026-11-30`（原 `2026-10-31`）auth 类别期限检查；只接受无密钥元数据，不验证账户 |
| [离线 UCP handler 与协议边界预检](lab/ucp_preflight.py) | 版本/宣告 instrument/card tokenize 前置条件、RFC 9421 闭合必签门禁（`#659`/`#795`）、Permalink `303` 安全头与不可信 GET 输入校验（`#913`）、RFC 9728 多条目身份发现与 Accelerated IdP 单用户换票绑定（`#783`/`#970`）、Cart-to-Checkout 互斥与优先级（`#940`）、`buyer.consent` 全量替换豁免（`#660`）、退货政策禁算日校验（`#966`）、Stripe OCA/SFTP/WebMCP 护栏及 ACP ATDRP §7.4a 证据包准入（`#316`） |
| [离线 Poppy & Sierra 零售护栏](lab/poppy_guard.py) | Poppy `v0.1` 发现/RFC 8414 §3.1 路径多租户隔离/DPoP/跨上下文断言防混淆与浏览器交接/Milestone 2 `conversations.*` 与 Milestone 3 Sign-In & Account Token 生命周期及脱敏（`#35`）、`operations` v1 扩展协商/跨通道去重/下游超时 `in_progress` 驻留/取消与 $\tau^3$-bench 零售改单护栏 |
| [离线六平面 AI-Native 负载架构基准](lab/workload_arch_bench.py) | Connect SPT 档案路由、单次 `SPT Resolve` + RSA 切片、SPT 3DS 状态机与 AP2 §7.4 受托熔断器（`#165`）、Policy Broker、UCP RFC 9530 批量目录摘要屏障（`#866`）、ATDRP Appendix C 17 网关兜底证据编译（`#316`）、MPP Tempo 亚美分尾差没收审计及 [7-Card 4:5 视觉报告](reports/agentic-commerce-6plane-bench/index.html) |
| [离线跨境多卖家分账、Token 毛利熔断与关税条款护栏](lab/cross_border_b2b_guard.py) | Connect 多卖家跨境拆单守恒与逆向退费 `reverse_transfer` 防垫付赤字、LLM Token 成本 + 支付通道费穿底触发 AP2 `COST_ENVELOPE_EXCEEDED`、`DDP` vs `DDU`/`DAP` 完税交货与 WCO 6 位 `HS` 编码防篡改校验（配套架构深潜见 [`docs/architecture/cross-border-b2b-settlement.md`](docs/architecture/cross-border-b2b-settlement.md) 与 [2026-10-19 更新索引](docs/research/2026-10-19-daily-update.md)） |
| [离线跨协议 CE 3.0 争议证据编译与 17 网关抗辩回放](lab/dispute_evidence_replay.py) | 串联 AP2 Mandate JWS + SPT 商户绑定/卡组密文 + UCP RFC 9530 `sha-256` 目录快照 + 跨境 `DDP`/HS6 守恒证明，映射 ACP `PR #316` Appendix C 17 网关抗辩载荷与三方责任定界（配套文档 [`docs/architecture/dispute-evidence-and-cryptographic-nonrepudiation.md`](docs/architecture/dispute-evidence-and-cryptographic-nonrepudiation.md) 及 [7-Card B2B/争议基准报告](reports/agentic-commerce-b2b-settlement-bench/index.html)） |
| [离线企业级全链路协议就绪度审计与交互式 H5 工作台](lab/protocol_readiness_auditor.py) | 串联 Phase A（MCP `2026-11-30` 42 天倒计时认证迁移 + Connect SPT 拆单）、Phase B（UCP RFC 9530 目录摘要屏障 + Policy Broker）与 Phase C（AP2 毛利熔断 + `DDP`/HS6 + 17 网关 CE 3.0 抗辩）端到端评分，配套 [企业割接手册](docs/architecture/enterprise-deployment-and-migration-playbook.md) 与 [自包含 H5 架构师工作台](reports/agentic-commerce-workbench/index.html) |
| [离线多段联程预订两阶段 Hold Saga 与 SFTP 三方日终对账护栏](lab/booking_sftp_reconciliation_guard.py) | 机票+酒店+算力异构 TTL 两阶段手动预授权原子捕获/撤单防孤儿单，以及 Stripe SFTP × MPP Tempo 亚美分尾差 × Metronome Token 账单 `00:00 UTC` 三方平账校验（配套架构深潜 [`docs/architecture/booking-hold-and-sftp-reconciliation.md`](docs/architecture/booking-hold-and-sftp-reconciliation.md)） |
| [离线 RFC 9421 Agent 身份证明与委托人反女巫限购配额护栏](lab/agent_identity_attestation_guard.py) | RFC 9421 强制签名域（`@method`/`@authority`/`@path`/`content-digest`/`x-ucp-idempotency-key`/`x-ap2-mandate-digest`、60s 窗口与单次 `nonce`）、Visa TAP / Stripe Agent Directory 密钥状态与 WebMCP 同源校验、基于 `principal_did` 的防黄牛/防女巫并发配额（配套架构深潜 [`docs/architecture/agent-identity-and-anti-scalping-attestation.md`](docs/architecture/agent-identity-and-anti-scalping-attestation.md)） |
| [离线 7 道门禁全链路统一结账编排器与混沌韧性 7-Card 基准报告](lab/unified_checkout_pipeline.py) | 串联 Gate 1–7 确定性护栏支持 Fail-Fast 短路阻断与微秒级延迟计量，覆盖 14 个混沌故障注入场景（14/14 vs 1/14），生成自包含 [7-Card 混沌韧性基准报告](reports/agentic-commerce-resilience-bench/index.html)（配套架构深潜 [`docs/architecture/unified-agentic-checkout-pipeline.md`](docs/architecture/unified-agentic-checkout-pipeline.md)） |
| [离线周期订阅免费试用陷阱拦截、TCCV 边界与三层原子吊销护栏](lab/recurring_subscription_guard.py) | 校验免费试用自动转付费暗黑模式（Negative-Option Billing）、总承诺合同价值 `TCCV` 预算上限、48h 退订窗口门禁与 AP2 + SPT/Network Token + Stripe Billing 三层原子撤权级联及僵尸 MIT 扣款拦截（Visa `13.5` / MC `4841`）（配套架构深潜 [`docs/architecture/recurring-mandates-and-subscription-guard.md`](docs/architecture/recurring-mandates-and-subscription-guard.md)） |
| [离线企业级 B2B 三单匹配、分批履约托管、BEC 防劫持与 2/10 Net 30 动态贴现护栏](lab/b2b_three_way_match_guard.py) | 校验 `PO Mandate == GRN == e-Invoice` 三单匹配、分批发货按实收合格量按比例 Capture（阻断缺货行提前请款）、KYB 收款账户防篡改/OFAC 制裁筛查与 `2/10 Net 30` 动态贴现隐含年化收益率（37.24% APR）精算（配套架构深潜 [`docs/architecture/b2b-three-way-match-and-escrow.md`](docs/architecture/b2b-three-way-match-and-escrow.md)） |
| [离线密封二价反向竞标 (Vickrey RFQ)、跨境 B2B VAT 逆向征税与售后 RMA 双向护栏](lab/reverse_auction_tax_returns_guard.py) | 校验多卖家 Commit-Reveal 二价反向询价与 Checkout 防加价（Anti-Bait-and-Switch）、跨境 B2B VAT `0%` 逆向征税与税务联结资质、以及售后 RMA 退货硬件序列号/净重防掉包与质量缺陷零整新费保护（配套架构深潜 [`docs/architecture/reverse-auction-tax-and-returns-guard.md`](docs/architecture/reverse-auction-tax-and-returns-guard.md)） |
| [离线混合支付瀑布流反套现、企业多成本中心预占分摊与 12 场景企业采购 7-Card 基准报告](lab/split_tender_finops_guard.py) | 校验促销券+储值卡/积分+开环卡/USDC 混合支付逆向退费上限（阻断闭环余额洗钱套现与先赚积分后退货双花）、企业多成本中心并发预算预占（Encumbrance）与包含 LLM Token 杂费的平衡 GL 总账分录，生成 [7-Card 企业采购基准报告](reports/agentic-commerce-enterprise-procurement-bench/index.html)（配套架构深潜 [`docs/architecture/split-tender-and-finops-chargeback.md`](docs/architecture/split-tender-and-finops-chargeback.md)） |
| [离线 x402 EIP-3009 最终性门禁、稳定币脱锚熔断与 Gas 拥堵 MPP Tempo 自动路由护栏](lab/onchain_finality_peg_guard.py) | 校验 `x402` EIP-3009 授权有效窗（`<= 300s`）、官方 USDC 合约白名单与 `32-byte nonce` 防重放，按交易金额与不可逆交付分级强制 L2/L1 区块最终性，监控预言机陈旧度与 `50 bps` 稳定币脱锚熔断，并在 Gas/价值比 `> 15%` 时自动聚合至 `Stripe MPP Tempo` 流式状态通道（配套架构深潜 [`docs/architecture/onchain-settlement-finality-and-peg-guard.md`](docs/architecture/onchain-settlement-finality-and-peg-guard.md)） |
| [离线多方撮合平台分账清结算、子商户 KYB 滚动保证金与逆向追偿护栏](lab/marketplace_split_settlement_guard.py) | 基于最大余数法（Largest Remainder Method）消除多子商户按比例分账的 `±1 cent` 舍入漂移并强制分账守恒，按子商户 Visa VAMP 争议率（`>0.65%`）与 30 日 GMV 突增倍数（`>3.5x`）将滚动保证金从 `5%` 动态上调至 `15%–25%` 并冻结 `T+0` 极速提现，以及在子商户违约负余额时按四级追偿瀑布流执行确定性冲正（配套架构深潜 [`docs/architecture/marketplace-split-settlement-and-reserve-guard.md`](docs/architecture/marketplace-split-settlement-and-reserve-guard.md) 与 [全栈参考架构 §20](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线跨境实时锁汇 (FX Quote Lock)、多币种资金池自然轧差与 ISO 20022 `pacs.008` 清算合规护栏](lab/fx_treasury_iso20022_guard.py) | 校验有界锁汇 TTL（`<= 120s`）、中间价点差上限与三区波动率领口（点差缓冲池冲抵或安全重报价），在 `USD/EUR/GBP/JPY/SGD` 多币种子账本间执行同币种自然轧差（将双向零售汇兑损耗降至 `<12 bps`），并校验 ISO 20022 `pacs.008` SWIFT gpi `UETR`、监管贸易用途码、`DEBT` 全额到账及代理行截单窗（配套架构深潜 [`docs/architecture/fx-treasury-netting-and-iso20022-guard.md`](docs/architecture/fx-treasury-netting-and-iso20022-guard.md) 与 [全栈参考架构 §21](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线跨境海关 HS-Code 完税价格 (DDP/De-Minimis/CBAM)、冷链物联网 MKT 托管自动理赔与 Scope 3 低碳路由护栏](lab/green_logistics_customs_sla_guard.py) | 核算 `CIF + 关税 + 附加税 + CBAM 碳边境税 + 进口增值税` 并拦截拆单逃税（Structuring）与低报货值（`<70%` 公允价），基于阿伦尼乌斯平均动力学温度（`MKT`）与超温时长（`>15 min` 或 `MKT > 8.0°C`）自动冻结尾款并触发托管理赔，以及在满足 SLA 与预算前提下优选每吨公里碳排最低的多式联运路径（配套架构深潜 [`docs/architecture/green-logistics-customs-and-cold-chain-sla.md`](docs/architecture/green-logistics-customs-and-cold-chain-sla.md) 与 [全栈参考架构 §22](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线零知识选择性披露资格核验 (`SD-JWT`/`zk-VC`)、PCI-DSS v4.0.1 敏感卡号/密钥脱敏防火墙与 GDPR 密码学粉碎墓碑护栏](lab/zk_eligibility_privacy_redaction_guard.py) | 校验年龄/属地/专业资质零知识布尔谓词证明并拦截过度索取原始 PII（SSN/生日/护照号，`OVERPRIVILEGED_PII_HARVESTING_BLOCKED`），在进入 LLM 上下文前拦截并脱敏 Luhn 银行卡号（PAN）、CVV 与 `sk_live_*` 密钥（`PCI_RAW_PAN_OR_CVV_LEAK_BLOCKED`），并通过销毁每用户 KMS 内容加密密钥（CEK）同时满足 GDPR Art. 17 被遗忘权与 ACP ATDRP Merkle 审计树根哈希不可篡改性（配套架构深潜 [`docs/architecture/zk-eligibility-pci-redaction-and-crypto-shredding.md`](docs/architecture/zk-eligibility-pci-redaction-and-crypto-shredding.md) 与 [全栈参考架构 §23](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线 Agentic 订阅生命周期、用量计费水位线幂等与 FTC Click-to-Cancel / PSD3 周期性扣款授权护栏](lab/subscription_metering_click_to_cancel_guard.py) | 校验高频 Token/API 用量事件 UUIDv7 幂等去重、迟到水位线拒止（`<= 300s`，`USAGE_EVENT_LATE_WATERMARK_EXPIRED`）与硬预算熔断（`SPEND_CAP_HARD_LIMIT_REACHED_THROTTLED`），执行 PSD3/RBI 周期性扣款提前 48h 通知与涨幅 `> 5%` 重授权拦截（`RECURRING_PRICE_ESCALATION_RECONSENT_REQUIRED`），并强制执行 FTC Click-to-Cancel 对称退订（`<= 2` 步、拦截挽留暗黑模式 `DARK_PATTERN_RETENTION_WALL_BLOCKED`、按比例退费 `PRO_RATA_REFUND_ISSUED` 与 SPT 令牌吊销；配套架构深潜 [`docs/architecture/subscription-metering-and-click-to-cancel-guard.md`](docs/architecture/subscription-metering-and-click-to-cancel-guard.md)、[全栈参考架构 §24](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md) 与 [15 场景全球清算/隐私 7-Card 报告](reports/agentic-commerce-global-clearing-privacy-bench/index.html)） |
| [离线 Agentic 促销优惠券叠加防套利、加密联盟归因防劫持与积分/返现退货追回护栏](lab/loyalty_affiliate_promo_stacking_guard.py) | 防御并发枚举优惠券击穿毛利底线（`PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED`）、排他活动组冲突（`EXCLUSIVITY_GROUP_CONFLICT`）与女巫自推荐刷单环（`SELF_REFERRAL_SYBIL_RING_BLOCKED`），校验多跳导购 JWS 签名归因链并拦截末 5 秒归因劫持（`LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED`），以及锁定退货窗口期积分托管并在退货时抵扣已消费返现差额（`CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND`；配套架构深潜 [`docs/architecture/loyalty-affiliate-and-promo-stacking-guard.md`](docs/architecture/loyalty-affiliate-and-promo-stacking-guard.md) 与 [全栈参考架构 §25](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线 Agentic 嵌入式分期/商业信用授信 (BNPL / Net-Terms)、参数化微保险自动理赔与应收账款保理防重复质押护栏](lab/embedded_bnpl_parametric_insurance_guard.py) | 校验偿债覆盖率（`dscr >= 1.35`）、开放银行现金缓冲与跨平台并发分期负债率（拦截多平台隐形分期叠加 `MULTI_ISSUER_BNPL_STACKING_BLOCKED`）并以最大余数法生成零误差分期计划，校验多源预言机法定人数签名触发毫秒级参数化微保险理赔（`PARAMETRIC_INSTANT_PAYOUT_SETTLED`）并拦截与商户退费的双重获利（`DOUBLE_DIP_INDEMNITY_BLOCKED`），以及通过发票哈希登记簿与转让通知锁拦截“一票多融”重复质押（`INVOICE_DOUBLE_PLEDGING_BLOCKED`；配套架构深潜 [`docs/architecture/embedded-bnpl-and-parametric-insurance-guard.md`](docs/architecture/embedded-bnpl-and-parametric-insurance-guard.md) 与 [全栈参考架构 §26](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线欧盟数字产品护照 (EU ESPR DPP) 防伪溯源、二手流转检定托管分账与以旧换新 (Trade-In) 防压价护栏](lab/resale_dpp_authenticity_escrow_guard.py) | 校验欧盟 ESPR 数字产品护照 GS1 Digital Link、品牌方硬件签名、维修 Merkle 根与失窃/召回黑名单（`STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED`），编排“卖家 -> 权威检定中心 -> 买家”双跳鉴真托管与品牌方二道流转版税最大余数分账（假货全额退还买家并罚没卖家保证金 `COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED`），并拦截以旧换新收货后超 `5%` 单方面恶意压价扣款（`UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED`；配套架构深潜 [`docs/architecture/resale-dpp-authenticity-and-trade-in-guard.md`](docs/architecture/resale-dpp-authenticity-and-trade-in-guard.md)、[全栈参考架构 §27](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md) 与 [16 场景生命周期金融/循环经济 7-Card 报告](reports/agentic-commerce-lifecycle-finance-bench/index.html)） |
| [离线跨协议智能体实时拍卖/逆向竞标清算 (Vickrey / Reverse RFQ)、团购联盟动态阶梯托管与反围标/弃标罚没护栏](lab/agentic_auction_consortium_clearing_guard.py) | 实现 Vickrey 次价激励相容清算（`VICKREY_INCENTIVE_COMPATIBLE_CLEARED`）、距截止 `<= 15s` 防狙击 `+30s` 软延时（`ANTI_SNIPING_SOFT_CLOSE_EXTENDED`）与围标/托儿串谋拦截（`BID_RIGGING_OR_SHILL_COLLUSION_BLOCKED`），核算多买方拼单集采阶梯价解锁与早鸟差价退还守恒（`GROUP_TIER_UNLOCKED_REBATE_SETTLED` / 未达 MOQ 自动解冻 `MOQ_NOT_MET_ESCROW_AUTO_RELEASED`），并在中标违约时自动罚没保证金（`WINNER_DEFAULT_EARNEST_BOND_SLASHED`）顺延次优竞标者（`SECOND_PRICE_FALLBACK_AWARDED`；配套架构深潜 [`docs/architecture/agentic-auction-and-consortium-clearing-guard.md`](docs/architecture/agentic-auction-and-consortium-clearing-guard.md) 与 [全栈参考架构 §28](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线数字商品/SaaS 席位 DRM 防盗刷吊销、二级票务反黄牛动态旋转码托管与 C2PA 生成式数字资产版权微版税分账护栏](lab/digital_goods_ticketing_ip_royalty_guard.py) | 拦截已退款/拒付订单激活码白嫖（`REFUNDED_LICENSE_KEY_REVOKED_BLOCKED`）、机房代理批量扫号（`DATACENTER_BULK_KEY_HARVESTING_BLOCKED`）与 TPM/Enclave 并发席位超限（`SEAT_CONCURRENCY_LIMIT_EXCEEDED`），强制二级票务溢价上限（`RESALE_MARKUP_CAP_EXCEEDED_SCALPING_BLOCKED`）、`<= 15s` TOTP 动态旋转二维码防静态截图（`STATIC_SCREENSHOT_QR_EXPIRED_BLOCKED`）与场馆闸机核验放款（`VENUE_CHECKIN_VERIFIED_ESCROW_RELEASED`），并以最大余数法零漂移切分 C2PA 生成式资产多创作者微版税（`C2PA_ROYALTY_MICRO_SPLIT_SETTLED`；配套架构深潜 [`docs/architecture/digital-goods-ticketing-and-ip-royalty-guard.md`](docs/architecture/digital-goods-ticketing-and-ip-royalty-guard.md) 与 [全栈参考架构 §29](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线医疗健康/医药电商 FSA/HSA 税优账户 SIGIS IIAS 自动分单、NCPDP/DEA 电子处方防重复配药与 HIPAA 账单摘要零 PHI 泄露护栏](lab/healthcare_fsa_rx_hipaa_guard.py) | 依据 IRS §213(d) 与 SIGIS IIAS 规范自动切分合格医疗 SKU（Rx/OTC）、缺 LMN 证明自动路由备用卡的双用途 SKU（`DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP`）与普通日化 SKU（`SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED`，`conservation_delta_minor == 0`），校验 NCPDP/DEA 处方硬件签名与 PDMP 跨药房防重复配药（`DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED`）及 `80%` 服用周期提前囤药拦截（`EARLY_REFILL_ACCUMULATION_BLOCKED`），并按 HIPAA §164.502(b) 抹除账单摘要中的 `ICD-10` 诊断码与 `NDC` 药品名（`HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC`；配套架构深潜 [`docs/architecture/healthcare-fsa-rx-and-hipaa-settlement-guard.md`](docs/architecture/healthcare-fsa-rx-and-hipaa-settlement-guard.md) 与 [全栈参考架构 §30](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线车网互动 ISO 15118 Plug-&-Charge / V2G 双向电能净计量、DePIN GPU 算力有效吞吐 (Goodput) 托管核减与碳信用防洗绿护栏](lab/energy_v2g_compute_carbon_guard.py) | 校验 ISO 15118-20 合约证书与充电桩 OCMF 硬件签名（拦截无签名电表伪造 `UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED`）、拦截跌破电池安全保底 SoC 的过度反向放电（`V2G_DISCHARGE_BELOW_SOC_FLOOR_BLOCKED`）并精确核算分时电价 ToU 与上网补贴 FiT 双向净结算（`V2G_BIDIRECTIONAL_NET_METER_SETTLED`）；校验 GPU 算力实测 Goodput（`<85%` 自动核减托管款 `COMPUTE_GOODPUT_SLA_BREACH_ESCROW_SLASHED`）、免除未落盘 Checkpoint 抢占驱逐计费（`UNCHECKPOINTED_PREEMPTION_CHARGE_VOIDED`）并阻断碳信用序列号重复核销（`CARBON_CREDIT_DOUBLE_COUNTING_RETIREMENT_BLOCKED`；配套架构深潜 [`docs/architecture/energy-v2g-compute-and-carbon-settlement-guard.md`](docs/architecture/energy-v2g-compute-and-carbon-settlement-guard.md)、[全栈参考架构 §31](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md) 与 [16 场景垂直行业清算 7-Card 报告](reports/agentic-commerce-vertical-domain-bench/index.html)） |
| [离线海运贸易金融 MLETR 电子提单 (eBL) 唯一物权交割、eUCP 600 电子信用证自动审单与集装箱滞期费参数化托管护栏](lab/trade_finance_ebl_lc_demurrage_guard.py) | 强制校验 UNCITRAL MLETR / DCSA eBL 3.0 唯一控制权令牌（拦截一单多押重复质押 `EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED`）与托管确认后原子物权背书（`MLETR_EBL_ATOMIC_TITLE_TRANSFERRED`）；按 ICC eUCP 600 Art. 30 校验装运期与 `±5%` 数量容差（拦截不符点交单 `EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH`）；按 FMC OSRA 规则剔除船东塞港/海关查验免责时长后结算有上限的集装箱滞期费（`PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED` / `MARINE_DEMURRAGE_CAPPED_SETTLED`；配套架构深潜 [`docs/architecture/trade-finance-ebl-lc-and-demurrage-guard.md`](docs/architecture/trade-finance-ebl-lc-and-demurrage-guard.md) 与 [全栈参考架构 §32](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |
| [离线实时广告竞价 (RTB) 无效流量 (SIVT) 托管拒付、主权 AI 算力硬件地理围栏出口管制与云 SLA 违约贷项通知单自动冲抵护栏](lab/rtb_ad_fraud_sovereign_compute_guard.py) | 校验 IAB `ads.cert` 2.0 曝光签名并在机器人点击农场无效流量（SIVT）超标时自动冻结扣减广告预算（`RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD`）；校验 TPM 2.0 + PTP 时延三角定位防伪（`HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED`）与主权 AI 出口管制/数据驻留围栏（`EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED`）；并在云/API 可用性跌破 SLA 承诺时按阶梯自动生成贷项通知单冲抵账单（`SLA_BREACH_CREDIT_NOTE_AUTO_NETTED`；配套 [全栈参考架构 §33](docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md)） |

## 本地运行

要求 Python 3.12+；只使用标准库，无需支付账户、模型密钥、联网或安装依赖：

```powershell
python -m lab.demo
python -m unittest discover -s tests -v
```

demo 使用自动清理的临时 SQLite 数据库，输出 `status=simulated`。可信调用方预置批准与时钟；生产需要独立用户认证/同意与支付 broker。此实验**不是** ACP/AP2/TAP/SPT 协议实现、真实支付或认证结果。

### Stripe MCP 迁移盘点（不读取密钥）

```powershell
python -m lab.mcp_migration --as-of 2026-10-16
python -m lab.mcp_migration --as-of 2026-11-30
```

默认读取 [合成客户端清单](lab/mcp_inventory.example.json)；`--inventory` 可指定仅含 alias、环境和 auth 类别的 JSON。禁止填入实际 key、账户 ID 或个人数据；不传 `--as-of` 时使用北京时间当天日期。示例含两种旧认证类别，两个命令都**预期 exit 1**，分别输出 `migration_required` / `blocked_by_documented_policy`；空/无效输入 exit 2。全部记录为 OAuth/Agent Key 时 exit 0 只表示元数据类别匹配，始终 `account_verification=not_performed`，不是已迁移或已获付款权限。

Stripe 文档未说明 cutoff 的具体时刻/时区，本工具只做日期模拟，不检测服务器 401。10-16 再核验发现官方通告已将迁移截止日从 `2026-10-31` 延后至 **`2026-11-30`**（`Migrate by November 30, 2026. Starting in December, Stripe MCP will stop accepting...`），距 10-16 剩余 45 个日历日；依据是 [MCP 官方正文](https://docs.stripe.com/mcp)，人工迁移 runbook 见 [10-12 研究](research/daily/2026-10-12.md)，延期核验见 [10-16 研究](research/daily/2026-10-16.md)。工具无网络调用，不创建、轮换或撤销实际凭证；来源监测发现变化也不会自动更新本工具的规则，必须经人工审阅后显式更新。

### UCP handler 兼容性预检（不获取凭证）

```powershell
python -m lab.ucp_preflight
python -m lab.ucp_preflight --instrument card --relationship confirmed
python -m lab.ucp_preflight --instrument apple_pay
```

默认用完全合成的双方宣告测试 `link`，**预期 exit 1**：当前 Stripe `/complete` 不接受该 instrument。后两条 exit 0 仅为 `candidate_unverified`，始终 `payment_authorized=false`、`provider_verification=not_performed`。Google Pay 在本预检中拒绝，不自动转到 `com.google.pay`、转换 instrument 或降级到浏览器付款。

本地只审阅 UCP `2026-04-08` / Stripe handler `2026-06-25` 文档示例，匹配但未经本地审阅的版本也拒绝；这不是声明其他版本被供应商禁止。卡 tokenize 才检查双方 `sandbox/production` 环境一致和关系已确认，不能把该条件套到 Apple Pay wallet 路径。`--business-ucp-version` / `--business-handler-version` 可模拟版本漂移；无效日期 exit 2。所有参数只是元数据声明，不读取实际 UCP profile、key、PAN、SPT 或钱包数据，也不验证客户同意、Apple Pay 商户配置、地域/账户资格或支付结果。此工具不是 UCP wire-format/conformance 实现，更不是 checkout 的授权层。

### Poppy `v0.1` 发现与 Sierra 零售售后确定性护栏（离线模拟）

```powershell
python -m lab.poppy_guard
```

演练 Personal Agent Protocol（"Poppy" `v0.1` 草案）的 `/.well-known/poppy.json` 发现与 OAuth `poppy_domains` 双向防伪校验、令牌端点 `poppy-session+jwt` 与浏览器会话端点 `poppy-browser+jwt` 跨上下文防混淆校验（`#35`）、OpenAPI/Operations `DPoP`（封禁 `HS*` 对称算法）vs MCP 单一 `resource` 绑定 `Bearer` 与 RFC 9728 元数据验证，以及结合 Sierra Defense-in-Depth 与 $\tau^2/\tau^3$-bench 零售策略的两阶段 `operations` v1 订单修改确认：拒绝用对话消息（含 `sender: "human"`）确认操作、核对企业 `summary` 与结构化 `terms` 一致（`#51`）、对最新不可变 `revision` 幂等确认执行，并拦截同一待发货订单的二次商品修改。此模块仅使用合成内存数据，不发起真实网络请求或支付调用。

### 六平面 AI-Native vs. 经典三层 Web 架构基准与 7-Card 报告生成（离线模拟）

```powershell
python -m lab.workload_arch_bench --output-dir reports/agentic-commerce-6plane-bench
```

运行覆盖六大架构平面的 12 个对抗性评测场景（Stripe Connect SPT 档案路由、单次 `SPT Resolve` 重放拦截与 RSA 切片提取、SPT 3DS 非线性状态机、Google AP2 §7.4 四态受托熔断器、Policy Broker `summary`-vs-`terms` 校验、UCP `dev.ucp.common.feed` RFC 9530 分片摘要屏障与变体按 `id` 合并、ACP ATDRP Appendix C 17 网关争议证据兜底编译、Stripe MPP Tempo 流式会话亚美分尾差没收审计），并输出确定性评估数据 [`reports/agentic-commerce-6plane-bench/report.json`](reports/agentic-commerce-6plane-bench/report.json) 与自包含 7-Card 4:5 视觉基准报告 [`reports/agentic-commerce-6plane-bench/index.html`](reports/agentic-commerce-6plane-bench/index.html)。

### 跨境多卖家分账、Token 毛利穿底熔断与关税条款护栏（离线模拟）

```powershell
python -m lab.cross_border_b2b_guard
```

演练 Stripe Connect 跨境多卖家拆单守恒（强制 `separate_charges_and_transfers`、FX 锁汇报价 TTL/滑点走廊、部分退货 `reverse_transfer=true` 防赤字）、`stripe-token-billing` + 三类支付通道（`stripe_spt_card` / `x402_base_usdc` / `mpp_tempo_session`）毛利穿底触发 Google AP2 `COST_ENVELOPE_EXCEEDED` 受托熔断器，以及跨境贸易条款（`DDP` vs `DDU`/`DAP`）与 WCO 6 位 `HS` 商品编码防幻觉篡改校验。架构推导见 [`docs/architecture/cross-border-b2b-settlement.md`](docs/architecture/cross-border-b2b-settlement.md)。

### 跨协议 CE 3.0 争议证据链编译与 17 网关抗辩 7-Card 报告生成（离线模拟）

```powershell
python -m lab.dispute_evidence_replay --output-dir reports/agentic-commerce-b2b-settlement-bench
```

针对 Visa `10.4`/`13.3` 与 Mastercard `4837`/`4853` 拒付争议，编译四支柱密码学证据包（AP2 Mandate JWS + Stripe SPT/卡组密文 + UCP RFC 9530 `sha-256` 目录快照 + 跨境 `DDP`/HS6 与 Connect 守恒证明），校验篡改并做三方定责（Buyer / Agent Platform / Merchant），映射 ACP `PR #316` Appendix C 全部 17 家网关字段，并生成 [`reports/agentic-commerce-b2b-settlement-bench/report.json`](reports/agentic-commerce-b2b-settlement-bench/report.json) 与自包含 7-Card 4:5 视觉基准报告 [`reports/agentic-commerce-b2b-settlement-bench/index.html`](reports/agentic-commerce-b2b-settlement-bench/index.html)。架构说明见 [`docs/architecture/dispute-evidence-and-cryptographic-nonrepudiation.md`](docs/architecture/dispute-evidence-and-cryptographic-nonrepudiation.md)。

### 企业级全链路协议就绪度审计与交互式 H5 架构师工作台（离线模拟）

```powershell
python -m lab.protocol_readiness_auditor --output-dir reports/agentic-commerce-workbench
```

面向 `2026-11-30` Stripe MCP 42 天割接倒计时，串联 Phase A（MCP OAuth/Agent Key 认证 + Connect 拆单守恒）、Phase B（UCP RFC 9530 `sha-256` 目录屏障 + Policy Broker）与 Phase C（AP2 毛利熔断 + `DDP`/HS6 + 17 网关 CE 3.0 抗辩）输出 0–100 分就绪度评估与阻断项清单，并生成自包含交互式 H5 架构师工作台 [`reports/agentic-commerce-workbench/index.html`](reports/agentic-commerce-workbench/index.html)。割接蓝图见 [`docs/architecture/enterprise-deployment-and-migration-playbook.md`](docs/architecture/enterprise-deployment-and-migration-playbook.md)。

### 多段联程预订两阶段 Hold Saga 与 SFTP 三方日终对账护栏（离线模拟）

```powershell
python -m lab.booking_sftp_reconciliation_guard
```

演练异构供应方（GDS 机票 + PMS 酒店 + 算力）两阶段手动预授权 `HOLD_ALL -> VERIFY -> ATOMIC_CAPTURE_OR_REVERSE` 防孤儿单护栏，以及跨 `00:00 UTC` 日切窗口的 Stripe SFTP 批量结算单 × MPP Tempo 亚美分尾差没收 × Metronome Token 账单三方平账方程。架构推导见 [`docs/architecture/booking-hold-and-sftp-reconciliation.md`](docs/architecture/booking-hold-and-sftp-reconciliation.md)。

### 密码学 Agent 身份证明（RFC 9421 × Visa TAP × Stripe Directory）与防女巫并发配额护栏（离线模拟）

```powershell
python -m lab.agent_identity_attestation_guard
```

演练 WAF/CDN 边缘层的 RFC 9421 强制 6 组件签名校验、RFC 9530 `Content-Digest` 防篡改、60s 时间窗与单次 `nonce` 防重放、Visa TAP / Stripe Agent Directory 密钥吊销拦截、WebMCP 同源校验，以及基于人类委托人 `principal_did` 的反女巫（Anti-Sybil）并发代理扇出与稀缺库存限购配额。架构推导见 [`docs/architecture/agent-identity-and-anti-scalping-attestation.md`](docs/architecture/agent-identity-and-anti-scalping-attestation.md)。

### 7 道门禁全链路统一智能体结账流水线与混沌韧性 7-Card 报告生成（离线模拟）

```powershell
python -m lab.unified_checkout_pipeline --output-dir reports/agentic-commerce-resilience-bench
```

将 Gate 1（边缘 RFC 9421 签名与防女巫配额）、Gate 2（UCP RFC 9530 目录摘要屏障与 Policy Broker）、Gate 3（跨境 `DDP` 与 WCO 6 位 `HS` 锁定）、Gate 4（Token 毛利与 AP2 受托熔断）、Gate 5（多航段 Booking 两阶段 Hold Saga）、Gate 6（Connect 多卖家拆单守恒与单次 SPT Resolve）与 Gate 7（17 网关 CE 3.0 证据包 Merkle 密封与 `00:00 UTC` SFTP 三方对账）串联为支持 Fail-Fast 短路阻断的统一生产编排器，运行 14 个混沌故障注入基准并生成 [`reports/agentic-commerce-resilience-bench/report.json`](reports/agentic-commerce-resilience-bench/report.json) 与自包含 7-Card 4:5 视觉报告 [`reports/agentic-commerce-resilience-bench/index.html`](reports/agentic-commerce-resilience-bench/index.html)。架构推导见 [`docs/architecture/unified-agentic-checkout-pipeline.md`](docs/architecture/unified-agentic-checkout-pipeline.md)。

### 周期订阅免费试用陷阱拦截、TCCV 边界与三层原子吊销护栏（离线模拟）

```powershell
python -m lab.recurring_subscription_guard --json
```

演练免费试用自动转付费暗黑模式（Negative-Option Billing）拦截、最坏情况总承诺合同价值 $\text{TCCV} = C_{\text{initial}} + \max(N_{\text{min\_commit}}, 1) \times C_{\text{recurring}} + F_{\text{ETF}}$ 预算校验、掠夺性提前退订截止窗拦截，以及 AP2 `MandateRevocation` + Stripe SPT/卡组 Network Token 失活 + 商户 Stripe Billing 订阅取消三层原子撤权级联与僵尸 MIT 扣款拦截（自动生成 Visa `13.5` / Mastercard `4841` 抗辩载荷）。架构推导见 [`docs/architecture/recurring-mandates-and-subscription-guard.md`](docs/architecture/recurring-mandates-and-subscription-guard.md)。

### 企业级 B2B 三单匹配（`PO == GRN == Invoice`）、分批履约托管与 `2/10 Net 30` 动态贴现护栏（离线模拟）

```powershell
python -m lab.b2b_three_way_match_guard --json
```

演练企业级 B2B 分批发货按实收合格量（`qty_delivered - qty_rejected_damaged`）按比例请款（拦截缺货未发行的提前全额 Capture）、`PO == GRN == e-Invoice` 零正单价漂移校验、供应商收款终端被篡改（BEC）与 OFAC 制裁名单秒级熔断，以及 `2/10 Net 30` 提前付款贴现隐含年化收益率（$37.2449\%$ APR）精算。架构推导见 [`docs/architecture/b2b-three-way-match-and-escrow.md`](docs/architecture/b2b-three-way-match-and-escrow.md)。

### 密封二价反向竞标（Commit-Reveal Vickrey RFQ）、跨境 B2B VAT 逆向征税与售后 RMA 双向护栏（离线模拟）

```powershell
python -m lab.reverse_auction_tax_returns_guard --json
```

演练多卖家 `Commit-Reveal` 二价反向询价（Vickrey 激励相容定价）与结账防加价（`BAIT_SWITCH_SURCHARGE_INJECTION`）、跨境 B2B VAT `0%` 逆向征税（`INVALID_B2B_VAT_REVERSE_CHARGE_OVERCOLLECTION`）及无税务联结违规收税拦截（`UNREGISTERED_TAX_COLLECTION_BLOCKED`），以及售后 RMA 质量缺陷零整新费保护（`ILLEGAL_SNAD_RESTOCKING_FEE_BLOCKED`）与退货序列号/净重掉包欺诈阻断（`RMA_SERIAL_OR_WEIGHT_FRAUD_BLOCKED`）。架构推导见 [`docs/architecture/reverse-auction-tax-and-returns-guard.md`](docs/architecture/reverse-auction-tax-and-returns-guard.md)。


## 每日研究

已有 Copilot App 自动化每日 22:00 执行研究，已补充官方来源核验、检查未合并分支、按日期增量研究、相关测试、提交推送与 PR 的要求。日更依赖本机 App/执行主机可用；GitHub Actions 目前仅执行 CI，不负责生成研究。

需要联网的公开来源跟踪命令：

```powershell
python -m scripts.source_monitor
```

生成 `research/daily/YYYY-MM-DD-sources.json`（北京时间），只记录 URL、哈希、错误和选定结构化事实，不保存第三方全文。任何抓取失败返回非零退出码；同日重跑仍对比此前日期的最后成功结果。HTML 导航或文案变化也可能改变哈希，**不能据此判断产品发布或标准升级**。专家研究写入同日 `.md`，将最新官方正文与公告日期、准入限制分开。

10-14 起，对 `stripe-mcp` 的已审阅 Markdown 迁移告示额外输出 `policy_facts` / `policy_change` / `policy_error`：截止日期、两类被拒绝 key、OAuth/Agent Key 替代路径、文档所述 401/OAuth discovery，以及未知的截止时刻/时区。首次提取为 `baseline`，不回填历史；`policy_change=unchanged` 只表示这些字段相同，不是整个政策、tool/schema 或实际账户权限未变。

提取器仅识别固定的短告示语法，忽略 fenced code 中的示例。缺失/重复告示、日期矛盾或措辞变化均 `unknown` 并返回非零，不猜测新语义、不退回旧事实冒充本日成功。正文抓取成功但解析失败时 `status=ok` 与 `policy_error` 同时记录；fetch 失败则 `status=error`。两种失败都保留此前日期最后成功基线。当前可识别语法之外的合理文案变化也会要求人工审阅，这是保守的监测取舍，不是 Stripe 拒绝该政策。

研究上传当前会话分支并通过 PR 汇总；未合并前不代表默认分支已更新。尚未验证的能力会明确标注，不能据此推断生产可用性。

## 公开参考

- [Stripe: Sessions 2026 announcements](https://stripe.com/blog/everything-we-announced-at-sessions-2026)
- [Stripe: Agentic commerce](https://docs.stripe.com/agentic-commerce)
- [Visa: Intelligent Commerce](https://www.visa.com/en-us/solutions/intelligent-commerce)
- [Visa: Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)
- [AWS AgentCore Shopping Concierge sample](https://github.com/awslabs/agentcore-samples/tree/main/05-blueprints/shopping-concierge-agent)
