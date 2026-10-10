# Agent 场景、职责与验收

所有商品、商户和金额均为合成例子。实际付款与高风险动作默认要求明确授权；下表不是厂商已交付能力声明。

| 场景 | Agent 价值 | 人工/策略边界 | 相关产品或协议 | 本仓库验证状态 |
| --- | --- | --- | --- | --- |
| 日常补货 Personal Agent | 比较咖啡规格、价格和库存，建议固定商品补货 | merchant/sku、数量、最终总价、币种、有效期；换商品要重新批准 | ACP/UCP、SPT 或获资格的 Visa token | **离线已实现**：单次 checkout、明确授权范围、幂等、撤销、expiry |
| 旅行组合预订 | 搜索航班+酒店，解释退改条件和总成本 | 不把两家商户扣款视为原子事务；部分成功需人工/补偿 | 多商户 checkout、AP2 意图证据、payment adapters | 设计场景；未实现真实库存、跨商户 saga |
| B2B 自动采购 | 根据库存阈值提出采购，匹配合同 SKU | supplier allowlist、采购单审批、税务、累计预算、职责分离 | ACP/UCP + 企业授权系统 | 设计场景；实验无多订单累计预算 |
| Agent 购买付费 API | 识别 HTTP 402，比较资源价值，消费请求预算 | 每调用/累计上限、凭证不跨 endpoint、幂等 receipt 和 entitlement | Stripe MPP 或 x402 | 已研究官方流程；未实现 wire protocol/真实付费 |
| 商户服务 Agent | 更新 catalog、解释退款、查询订单 | 客服建议不直接退款；provider event 校验，退款权限单独设置 | Suite、ACP/UCP orders/webhooks、Stripe MCP | 设计场景；无真实退款/fulfillment |
| 财务运营 Agent | 查账、解释现金流和支付失败 | 先只读；创建卡、转账、付款须独立权限和人工批准 | Stripe MCP/skills，Sessions 公告中的 agent-ready Treasury | 研究场景；公告不能推定任意企业可用 |

## 离线实验验收不变式

`python -m unittest discover -s tests -v` 检查：金额恰好等于上限可执行；超过一 minor unit 拒绝；跨 merchant、商品、数量或币种拒绝；quote/delegation 在 `now == expires_at` 失效；批准后 quote 改变拒绝且不消费授权；撤销后拒绝；相同 key+payload 返回同一订单；相同 key 不同 payload 拒绝；同一 grant 换 key 不再消费；数据库关闭重开后幂等结果仍在；event 插入失败使整个模拟事务回滚。

测试不能证明真实 provider 的幂等实现、分布式事务、TAP 签名安全、AP2 证据效力、累计预算控制或符合 PCI/SCA。本地可信对象传入 `Checkout` 不允许直接转用于生产。

## 示例运行

从仓库根目录运行，Python 3.12，仅标准库：

```powershell
python -m lab.commerce
python -m lab.commerce --database .\demo.sqlite3
python -m unittest discover -s tests -v
```

输出包含 `mode: offline_simulation`、`status: simulated_order`、`real_payment: false` 和 `retry_same_order: true`。持久数据库运行每次生成独立演示订单，但同一次演示内重试不重复下单。不提供网络端点、真实支付 token 或卡号。
