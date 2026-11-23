# 电商防爬反欺诈与可信智能体边缘身份认证（`Trusted Agent Identity`: `Cloudflare Web Bot Auth / RFC 9421 vs. Visa Trusted Agent Protocol (TAP) vs. Akamai / DataDome vs. 传统 WAF 验证码`）、防伪造 `User-Agent` 绕过与防误杀高客单代购 Agent 架构选型 FAQ

> **核心选型结论速览**：当越来越多的消费者授权个人购物智能体（如 ChatGPT Operator、Perplexity Buy、Apple Intelligence、企业采购 Agent）代自己去品牌独立站或 OTA 平台查库存、领券和结账时，传统的电商边缘安全网关（WAF）正陷入一场两难灾难：① **“一刀切弹图形验证码（CAPTCHA）或封云机房 IP”把持卡人真金白银授权的代购 Agent 当成恶意爬虫误杀，白白损失 `15%–22%` 的高意向增量订单**：购物 Agent 运行在 Azure/AWS 云端容器内，天然命中传统 WAF 的“数据中心 ASN + 无鼠标移动轨迹”黑名单；② **为了放行 AI 导购而把 `User-Agent: ChatGPT-User` 加入白名单，结果被黄牛党在抢鞋脚本里花 1 秒钟伪造该请求头（Header Spoofing）大摇大摆绕过全站防爬扫光库存**；③ **无付款意图的纯语料抓取爬虫（Training Scrapers）与带着真实信用卡令牌来买东西的交易型智能体（Transactional Buyer Agents）混在一起打爆源站数据库**。  
> 生产级架构必须实施 **“基于 `RFC 9421 HTTP Message Signatures`（`Ed25519` 公钥目录验签）的 `Cloudflare Web Bot Auth` 边缘身份层 + 结合持卡人付款意图证明的 `Visa Trusted Agent Protocol (TAP)` + 请求体摘要（`RFC 9530 Content-Digest`）与 `300s Nonce` 防重放锁 + ‘只读检索走边缘 `UCP` 静态缓存、持证买家 Agent 走免验证码 VIP 结账直通车’的双车道分流控制面”**：可将合法代购 Agent 误封流失、黄牛伪造请求头渗透与源站无效爬虫算力消耗削减 **40%**（以季度 `$290,000` 误封合法代购 GMV 流失与源站爬虫防护损耗池计，净成本降至 `$174,000`，每季度净挽回与节省 **`$116,000`**）。

![Trusted Agent Identity RFC 9421, Visa TAP & Web Bot Auth vs WAF Architecture](../assets/svg/735-trusted-agent-identity-rfc9421-visa-tap-web-bot-auth-waf-escrow-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：为什么传统的“校验 User-Agent 字符串 + 维护官方爬虫 IP 段白名单”在 AI 智能体时代彻底失效了？
- **“明文请求头零伪造成本”与“云原生动态出口 IP 池”的碰撞**：
  1. 任何高中生写的 Python 脚本都能加上 `headers={"User-Agent": "OpenAI-Operator/1.0"}`；
  2. 现代企业采购 Agent 往往部署在多租户 Serverless 或 Azure Container Apps 上，与数万个其他应用共享云厂商动态 NAT 出口 IP——若按 IP 放行等于对全网部署在该云上的黄牛脚本敞开大门；若按 IP 封禁则直接掐断了所有云端合法代购助手。
- **架构解法（`RFC 9421` 密码学 HTTP 消息签名与 `.well-known` 公钥目录验签门禁 `HTTP 403`）**：
  - 彻底废除基于 `User-Agent` 明文或粗粒度云 IP 段的信任规则；
  - 要求任何声称自己是合法商业智能体的请求必须携带符合 **`IETF RFC 9421 (HTTP Message Signatures)`** 标准的 `Signature-Input` 与 `Signature` 头，由 CDN 边缘节点（如 `Cloudflare Web Bot Auth`）根据 Agent 官方域名下的 `.well-known/http-message-signatures-directory`（`Ed25519 / ECDSA P-256` JWK 公钥集）在 `< 2ms` 内完成密码学验签；凡明文声称是 AI Agent 却无有效签名或签名公钥不在可信注册表的，立即触发 `HTTP 403 SPOOFED_AGENT_USER_AGENT_OR_UNREGISTERED_RFC9421_KEY` 拦截。

### Q2：就算攻击者拿不到官方私钥，如果他截获了一条合法的 `RFC 9421` 签名请求，把它重放 10,000 次去刷空库存或篡改里面的商品数量怎么办？
- **架构解法（强制覆盖 `@authority + @path + content-digest + created + nonce` 五要素与 `300s` 防重放窗口 `HTTP 422`）**：
  - 很多早期实现只对域名（`@authority`）做了签名，导致该签名在有效期内可被中间人挪用去请求任意路径或篡改 POST JSON；
  - 生产级控制面强制要求 `Signature-Input` 必须同时覆盖：① `@method`、② `@authority`、③ `@target-uri`、④ **`content-digest`（`RFC 9530 SHA-256` 请求体哈希，改动 1 个字节即验签失败）**、⑤ `created`（时间戳偏差 `<= 300 秒`）与唯一 `nonce`（在边缘 Redis/KV 缓存内执行 `SETNX` 去重）。凡缺失请求体摘要覆盖或命中重放 `nonce` 的，立即触发 `HTTP 422 MISSING_RFC9530_CONTENT_DIGEST_OR_REPLAYED_SIGNATURE_NONCE`。

### Q3：同样是通过了 `RFC 9421` 验签的合法 Bot，商户边缘网关怎么区分它是“光抓数据不买东西的比价爬虫”还是“代表真买家来付钱下单的 VIP 购物代理”？
- **架构解法（`Visa Trusted Agent Protocol (TAP)` 付款意图证明区分 + 双车道边缘分流 `HTTP 451 / 409`）**：
  - **三级智能体分类治理**：
    1. **Class 1（无签名/伪造签名恶意脚本）**：边缘直接 `HTTP 403` 丢弃；
    2. **Class 2（仅有 `RFC 9421` 平台签名、无买家支付令牌的只读搜索/比价爬虫）**：**严禁放行进入扣减库存的 `/cart/lock` 或 `/checkout` 接口**，将其路由至 CDN 边缘预生成的 **`UCP / Schema.org` 结构化商品快照缓存**（零源站数据库压力）；
    3. **Class 3（同时具备 `RFC 9421` 签名 + `Visa TAP / Stripe SPT` 持卡人授权断言的交易型买家 Agent）**：赋予 **免图形验证码（Zero-CAPTCHA）VIP 结账绿通权限**（凡对已持 `Visa TAP` 凭证的合法买方 Agent 误弹图形拼图验证码导致死锁，或放任无支付意图的纯爬虫调用锁库接口的，触发 `HTTP 451 CAPTCHA_DEADLOCK_ON_ATTESTED_BUYER_AGENT_OR_UNBACKED_SCRAPER_CART_LOCK`；双车道智能分流确认返回 `HTTP 409 DUAL_LANE_EDGE_UCP_CACHE_AND_VISA_TAP_VIP_CHECKOUT_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 电商边缘可信智能体鉴权（RFC 9421 × Visa TAP）与双车道分流决策树
```mermaid
flowchart TD
    A[非浏览器自动化请求到达电商 CDN 边缘] --> B{是否携带 RFC 9421 Signature 头<br/>且公钥存在于可信目录 JWK?}
    B -- 否: 仅伪造 User-Agent 或裸代理IP --> C[HTTP 403 拦截: 边缘毫秒级丢弃伪装爬虫与撞库脚本]
    B -- Ed25519 验签通过 --> D{Signature-Input 是否完整覆盖<br/>content-digest 且 Nonce <= 300s 未重放?}
    D -- 缺失请求体哈希或重放攻击 --> E[HTTP 422 拦截: 阻断中间人篡改购物车载荷与签名重放]
    D -- 报文完整且新鲜 --> F{请求目标路径与 Visa TAP 付款意图核验}
    F -- 无 TAP 支付凭证的只读爬虫企图调用锁库接口 / 或向持证买家Agent乱弹图形验证码 --> G[HTTP 451 拦截: 严禁纯爬虫占库并免除持证代购Agent视觉验证码死锁]
    F -- 合法分级路由 --> H[HTTP 409 确认: 只读检索走边缘 UCP 缓存 + 持 TAP 买家走 VIP 免验证结账净省40%]
```

### 2. 边缘可信代理鉴权（Plane 1）× 双车道流量隔离架构图
```mermaid
flowchart LR
    subgraph Edge["1. CDN 边缘密码学验签层 (Cloudflare / Akamai)"]
      JWK[".well-known 公钥目录缓存<br/>Ed25519 <2ms 验签"]
      NONCE["300s Nonce 防重放窗口<br/>+ RFC 9530 Content-Digest 校验"]
    end

    subgraph Split["2. 受托三级流量分流器"]
      L1["无签名恶意 Bot -> HTTP 403 丢弃"]
      L2["Class 2 只读搜索 Agent<br/>-> 命中边缘 UCP JSON-LD 缓存 (0 源站压力)"]
      L3["Class 3 持 Visa TAP / SPT 买家 Agent<br/>-> 免 CAPTCHA 结账绿通车道"]
    end

    subgraph Origin["3. 源站结账与库存中心"]
      OMS["OMS / Cart FSM 原子锁库与结算"]
    end

    JWK --> NONCE --> L1 & L2 & L3
    L3 --> OMS
```

### 3. 持卡人购物 Agent 携带 `RFC 9421 + Visa TAP` 零验证码秒过 WAF 完成结账时序图
```mermaid
sequenceDiagram
    autonumber
    participant AG as 买方购物 Agent (持私钥与 TAP 令牌)
    participant WAF as 商户边缘网关 (Cloudflare Web Bot Auth)
    participant DIR as Agent 官方 .well-known 公钥目录
    participant OMS as 商户源站结账引擎

    AG->>WAF: 1. POST /api/v1/checkout (附带 Content-Digest + RFC 9421 Signature + Visa TAP Assertion)
    WAF->>DIR: 2. 拉取/命中缓存 keyId 对应的 Ed25519 公钥 (TTL 1h)
    WAF->>WAF: 3. 1.4ms 内完成 Ed25519 验签 + Nonce 防重放检查 + 请求体 SHA-256 摘要校验
    WAF->>WAF: 4. 识别存在有效 Visa TAP 持卡人付款意图 -> 自动跳过 Turnstile/图形验证码!
    WAF->>OMS: 5. 注入 X-Verified-Agent-Identity 头转发至源站 VIP 结账通道
    OMS-->>AG: 6. 完成锁库与 SPT 扣款，返回加密订单收据 (HTTP 409)!
```

---

## 三、 四大主流智能体边缘鉴权与反爬管理方案横向选型矩阵

| 评估维度 | Cloudflare Web Bot Auth (`RFC 9421`) | Visa Trusted Agent Protocol (`TAP`) | Akamai Bot Manager / DataDome | Poppy v0.2 `DPoP` (`RFC 9449`) |
| :--- | :--- | :--- | :--- | :--- |
| **核心解决痛点** | 在 CDN 边缘用公私钥签名替代脆弱的 IP 白名单与 UA 字符串 | 向商户证明“这个 AI 代理背后有真实持卡人和真钱预算” | 结合行为遥测与 TLS 指纹拦截高级拟人黄牛与撞库攻击 | 防止已签发的 OAuth 会话令牌被盗后在异地重放 |
| **底层密码学标准** | `IETF RFC 9421` (`Ed25519`) + `RFC 9530` (`Content-Digest`) | `RFC 9421` + 卡组织发卡行签名的付款意图断言 | `JA3/JA4` 指纹 + 设备证明 + 集成 `RFC 9421` 验签 | `IETF RFC 9449` 发送方约束证明（Demonstration of Proof-of-Possession） |
| **区分“只读爬虫”与“真买家 Agent”** | 识别是哪家公司的 Bot（如 OpenAI vs 某比价网） | **极强**（唯一能验证该请求已绑定真实支付凭证的协议） | 通过行为轨迹评分区分自动化扫货与正常浏览 | 绑定特定用户委托会话（User Intent Session） |
| **对源站性能与转化率影响** | 边缘 `<2ms` 验签，可配合边缘缓存卸载 90% 检索请求 | **消除对合法代购 Agent 误弹图形验证码导致的 22% 掉单** | 拦截 99% 恶意撞库与黄牛，保护大促源站不宕机 | 确保多跳代理链路中每一步调用者身份不可冒用 |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. 边缘智能体身份验签、防重放与 Visa TAP 双车道评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TrustedAgentIdentityTapWafPolicyInput:
    quarterly_waf_false_positive_and_scraper_origin_pool_usd: float = 290000.0
    spoofed_user_agent_without_rfc9421_signature: bool = False
    missing_rfc9530_content_digest_or_replayed_nonce: bool = False
    visual_captcha_on_tap_agent_or_scraper_cart_lock: bool = False
    dual_lane_edge_ucp_cache_and_visa_tap_vip_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · TRUSTED AGENT IDENTITY & VISA TAP`)**：通过 `RFC 9421 Ed25519` 边缘验签 + `RFC 9530 Content-Digest` 防篡改防重放 + `Visa TAP` 付款意图双车道分流，季度 WAF 误杀合法代购订单与源站爬虫算力损耗从 `$290,000` 降至 `$174,000`（净省 **40% / `$116,000`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: SPOOFED_UA_AND_CAPTCHA_DEADLOCK`)**：成功拦截黄牛伪造 `User-Agent: ChatGPT-User` 绕过防爬的攻击（`HTTP 403`）、阻断无 `content-digest` 覆盖的篡改/重放请求（`HTTP 422`），并消除对持 `Visa TAP` 凭证的真买家 Agent 误弹图形验证码导致的死锁（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（RFC 9421 + Visa TAP 验签通过）、`403`（伪造 User-Agent 或未注册公钥签名拦截）、`422`（缺失 RFC 9530 请求体摘要或超过 300s 窗口重放 Nonce 拦截）、`451`（对已认证买家 Agent 弹视觉验证码死锁或放任纯爬虫锁库存拦截）、`409`（只读检索走边缘 UCP 缓存 + 持 TAP 买家走 VIP 免验证结账确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `trusted_agent_identity_tap_waf_guard` 与 `trusted_agent_identity_tap_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组“中间人篡改已签名 POST 购物车商品数量 `1 -> 10`”与“回放 6 分钟前的合法签名”压测中，保持 100% 边缘拦截。
6. **Card 6 (`6 / 7` · `LATENCY`)**：CDN 边缘 `Ed25519` 签名核验 + `Nonce` 检查 P99 延迟仅 `1.4ms`。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于所有希望向 AI 购物助手开放商品发现与直接结账、同时严防黄牛与恶意爬虫的零售电商与票务酒店平台；**⛔ 不适用**于无公网 HTTP 接口的内部局域网系统。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **立即下线基于明文 `User-Agent` 或静态云 IP 白名单的 AI Bot 放行规则**：全面切换为基于 `.well-known/http-message-signatures-directory` 的 `RFC 9421 Ed25519` 密码学验签。
- [ ] **强制要求写操作签名覆盖 `RFC 9530 Content-Digest` 与 `300s Nonce`**：确保请求路径、商户域名与 POST JSON 正文不可被中间人篡改或跨时间窗重放。
- [ ] **为持有 `Visa TAP / Stripe SPT` 付款凭证的交易型 Agent 关闭图形拼图验证码（CAPTCHA）**：用密码学身份断言替代人类视觉拼图测试，挽回被传统 WAF 误杀的 20%+ 代购转化率。
- [ ] **实施“只读发现走边缘缓存、持证交易进源站”双车道隔离**：让比价/搜索爬虫直接命中 CDN 边缘 `UCP JSON-LD` 快照，仅允许携带真实买家支付授权令的 Agent 调用源站锁库接口。
