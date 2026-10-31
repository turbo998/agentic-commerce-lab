# 2026-10-31：Stage 1727 — `MerchantSignerStore.read_permission` 作用域签名密钥权限只读查询与权限边界

[English](2026-10-31-merchant-signer-permission-read.en.md) | [阶段索引](../stage-archive-index.md) | [当日日报](../../research/daily/2026-10-31.md)

## 1. 背景与问题定义

在 Visa Trusted Agent Protocol（TAP，基于 RFC 9421 HTTP Message Signatures）与本地商家执行面协同架构中，[`lab/merchant_signers.py`](../../lab/merchant_signers.py) 的 `MerchantSignerStore` 负责对 `(tenant_id, merchant, target_uri, key_id)` 四维 `MerchantSignerScope` 进行本地允许（`allow`）与撤销（`revoke`）围栏控制，并在 `admit()` 中与 `PaymentApprovalStore`、`PaymentAttemptJournal` 共同参与单事务准入。

在 Stage 1727 之前：
- `MerchantSignerStore.read_timed_admission(operation)` 仅能读取**已完成首次含时窗签名准入**的 `merchant_timed_admissions` 历史记录；
- `_permission(db, scope)` 是内部私有辅助方法，且在未注册时直接抛出 `MerchantSignerError`；
- 运维巡检、密钥轮换审计（例如 Visa Agentic Key Directory 密钥撤销核对或 Stripe/商家路由密钥隔离检查）缺少一个**不加写锁、不触发签名校验或时钟采样、不产生准入副作用**的公开只读接口，无法区分“该 `(tenant_id, merchant, target_uri, key_id)` 尚未登记（`None`）”“已登记且处于允许状态（`active`）”与“已被撤销（`revoked`）”。

## 2. AI-Native 架构与经典三层 Web / 云服务商 WAF 的辩证对比

| 维度 | 经典三层 Web 架构 / 云厂商 WAF | Agentic Commerce AI-Native 架构（Stage 1727） |
|---|---|---|
| **密钥与路由权限粒度** | API Gateway / IAM Role 通常按服务账号或粗粒度路径授权，内存缓存 TTL 内默认放行 | 签名密钥权限严格绑定 `(tenant_id, merchant, target_uri, key_id)` 四维精确 `MerchantSignerScope`，跨租户、跨商户、跨 URI 查询参数或跨 `key_id` 完全隔离 |
| **权限状态观测 vs. 签名准入** | 常将“查询密钥在白名单内”等同于请求可放行，或只能在发起真实交易请求时顺带探测权限状态 | `read_permission` 仅执行只读 `SELECT` 返回持久化策略状态（`None` / `"active"` / `"revoked"`）；既不证明 RFC 9421 签名有效性，也不替代 `admit()` 事务中的时窗校验、审批校验与尝试预留 |
| **读写锁与故障隔离** | 权限查询若复用写路径或隐式初始化记录，会在高频巡检下造成写锁竞争与审计污染 | `read_permission` 在打开 SQLite 连接前完成 `MerchantSignerScope` 类型校验，不开启 `BEGIN IMMEDIATE` 写事务，回滚的 `allow`/`revoke` 绝不可见，且对损坏的 `revoked` 存储值显式失败 |

## 3. 代码实现（[`lab/merchant_signers.py`](../../lab/merchant_signers.py)）

1. 新增状态字面量与只读返回模型：
   - `SignerPermissionState = Literal["active", "revoked"]`
   - 冻结数据类 `MerchantSignerPermissionStatus(scope: MerchantSignerScope, state: SignerPermissionState)`，在 `__post_init__` 中强校验 `scope` 类型与 `state in ("active", "revoked")`。
2. 在 `MerchantSignerStore` 新增 `read_permission(self, scope: MerchantSignerScope) -> MerchantSignerPermissionStatus | None`：
   - 先调用 `self._require_scope(scope)`，非法入参在打开数据库连接前即被拦截；
   - 使用只读 `SELECT revoked FROM merchant_signer_permissions WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?` 查询，不执行 `BEGIN IMMEDIATE`；
   - 若记录不存在返回 `None`；
   - 严格校验 `type(revoked) is int and revoked in (0, 1)`，防止损坏行被静默解释为合法状态；
   - 返回 `MerchantSignerPermissionStatus(scope, "revoked" if revoked else "active")`。

## 4. 验证证据（[`tests/test_merchant_signer_permission_read.py`](../../tests/test_merchant_signer_permission_read.py)）

新增 10 项单元测试（18 个子测试），验证：
- 未登记 `scope` 返回 `None`，且不向 `merchant_signer_permissions`、`merchant_timed_admissions`、`payment_approvals`、`payment_attempts` 写入任何记录；
- `allow()` 后返回 `state="active"`，跨重新打开与跨新进程一致；
- `MerchantSignerPermissionStatus` 为 `frozen=True` 且构造时拒绝非法 `scope` 或 `state`；
- 幂等 `revoke()` 后返回 `state="revoked"`，同时保留既有 `read_timed_admission(operation)` 历史且阻断后续 `admit()`；
- `state="active"` 仅表达本地密钥策略未撤销，若缺少 `PaymentApprovalStore` 审批记录，`admit()` 依然显式拒绝；
- `(tenant_id, merchant, target_uri, key_id)` 四维隔离；
- 非法 `scope` 在 `_connect()` 之前抛出 `MerchantSignerError`；
- 提交失败回滚的 `allow`/`revoke` 不会被读取；
- 损坏的 `revoked` 字段值显式抛出 `MerchantSignerError`；
- SQL trace 证明仅执行 `SELECT`，不含 `BEGIN IMMEDIATE`。

执行命令与结果：
- `python -m pytest tests/test_merchant_signer_permission_read.py -q`：`10 passed, 18 subtests passed`
- `python -m pytest -q`：`4287 passed, 1122 subtests passed`
