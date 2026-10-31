# 本地结账授权（`mandates`）与幂等收据（`receipts`）耦合溯源只读读取模型与存储行不变量（Stage 1737）

> ** English Version**: [2026-11-01-checkout-provenance.en.md](./2026-11-01-checkout-provenance.en.md)  
> **验证日期**：2026-11-01（北京时间 `UTC+08:00`）  
> **关联模块**：`lab/checkout.py`、`tests/test_checkout_provenance.py`、`tests/test_checkout.py`  
> **前序阶段**：[Stage 1736 (`2026-11-01-stripe-readback-provenance.md`)](./2026-11-01-stripe-readback-provenance.md)

---

## 1. 背景与架构问题

在 `agentic-commerce-lab` 的确定性本地结账存储 `CheckoutStore`（`lab/checkout.py`）中，授权记录与消费收据分别持久化于两张通过 `UNIQUE REFERENCES mandates(id)` 关联的 SQLite 表：

1. **`mandates`**：记录由可信操作员签发的单次结账授权上限（`id`、`merchant`、`currency`、`cart_digest`、`max_amount`、`expires_at`、`revoked`）；
2. **`receipts`**：记录由 `CheckoutStore.execute(...)` 在 `BEGIN IMMEDIATE` 写事务中原子签发的本地模拟收据（`request_key`、`fingerprint`、`mandate_id`、`order_id`、`amount`、`currency`）。

在 Stage 1737 之前，`CheckoutStore` 存在四个关键的读写不对称与存储完整性缺口：

1. **缺乏无锁、无时钟的只读溯源检查接口**：`CheckoutStore` 仅提供写路径（`approve`、`revoke`、`execute`），没有任何只读方法（`read_mandate`、`read_receipt`、`find_provenance`、`read_provenance`）。审计与对账流程若要检查某笔 `mandate_id` 当前是未消费（`active` / `revoked`）还是已消费（含绑定的 `request_key` 与 `Receipt`），不得不直接查询底层 SQLite 或触发带时钟与写锁的 `execute()`。
2. **幂等重放路径（`execute`）未校验持久化 `receipts` 行与父表 `mandates` 行的完整不变式**：
   - 当 `SELECT * FROM receipts WHERE request_key=?` 命中已有记录时，旧实现仅比较 `previous["fingerprint"] != fingerprint`，既未校验 `previous["fingerprint"]` 是否为合法的 64 位小写十六进制 SHA-256 摘要，也未校验 `previous["mandate_id"] == mandate_id`、`previous["order_id"] == f"sim_{fingerprint[:24]}"`、`previous["amount"] == checkout.amount`、`previous["currency"] == checkout.currency`；
   - 若底层 SQLite 中的 `receipts.amount`、`receipts.currency` 或 `receipts.order_id` 被篡改，或父表 `mandates` 行在 `PRAGMA foreign_keys = OFF` 下被删除（孤儿收据），幂等重放会静默返回失真收据。
3. **`Receipt` 值对象缺乏构造期不变量校验**：`Receipt` 原先未定义 `__post_init__`，允许构造含非法 `order_id`（非 `sim_<24-hex>`）、非正 64 位整数 `amount`、非法币种代码或非 `"simulated"` 状态的伪造收据对象。
4. **`revoke()` 与 `execute()` 未对损坏的 `mandates` 存储列故障闭合**：
   - `CheckoutStore.revoke(mandate_id)` 原先直接执行 `UPDATE mandates SET revoked=1 WHERE id=?`，当存储行的 `revoked`（如 `2`、`'-1'`、`'active'`）、`expires_at`、`max_amount`、`cart_digest`、`currency` 或 `merchant` 已损坏时，会静默覆盖 `revoked = 1` 并掩盖存储篡改；
   - `CheckoutStore.execute(...)` 原先通过 Python 真值判断 `if mandate["revoked"]:` 检查吊销状态，将损坏的 `revoked = 2` 误报为 `"Mandate is revoked or expired; obtain new approval."`。

---

## 2. 经典 Web 三层架构 vs. AI-Native Agentic Commerce 架构对比

| 架构维度 | 经典 Web App / Well-Architected 三层架构 | AI-Native Agentic Commerce 架构（Stage 1737） |
| :--- | :--- | :--- |
| **幂等缓存命中（`receipts`）信任边界** | 命中 `request_key` 且哈希匹配即直接把数据库列组装为响应返回 | 幂等重放与只读读取均通过 `_parse_receipt_row()` 强制复核 64 位 `fingerprint`、`mandate_id`、`sim_<24-hex>` `order_id`、精确 `amount`/`currency` 以及父表 `mandates` 绑定关系 |
| **授权与收据状态巡检** | 复用写接口或分多次查询 `mandates` 与 `receipts` | `CheckoutStore.find_provenance()` / `read_provenance()` 通过单条只读 `SELECT ... FROM (SELECT 1) LEFT JOIN mandates ... LEFT JOIN receipts ...` 在同一读快照内无锁、无时钟地返回 `CheckoutProvenance` |
| **父表授权行删除或列损坏** | 外键关闭删除父行后，幂等重放仍从子表返回孤儿收据；`revoke()` 直接 `UPDATE` 掩盖列损坏 | 父表 `mandates` 缺失时在 `read_receipt()`、`find_provenance()` 与 `execute()` 中统一抛出 `AuthorizationError("Orphan receipt exists without a recorded mandate.")`；`revoke()` 在 `BEGIN IMMEDIATE` 下先执行 `_parse_mandate_row()` 再更新状态 |

---

## 3. Stage 1737 核心实现设计

### 3.1 `MandateStatus`、`Receipt` 与 `CheckoutProvenance` 不可变值对象

在 `lab/checkout.py` 中新增/加固三个冻结数据类：

1. **`MandateStatus`**：
   - 字段：`mandate_id: str`、`merchant: str`、`currency: str`、`cart_digest: str`、`max_amount: int`、`expires_at: int`、`state: Literal["active", "revoked"]`。
   - `__post_init__` 强校验非空 `mandate_id`/`merchant`、3 位大写 ASCII 字母 `currency`、64 位小写十六进制 `cart_digest`、正 64 位有符号整数 `max_amount`/`expires_at`，以及精确枚举 `state in ("active", "revoked")`。
2. **`Receipt`**：
   - `__post_init__` 强制 `order_id` 匹配 `r"sim_[0-9a-f]{24}"`、`amount` 为正 64 位有符号整数、`currency` 为 3 位大写 ASCII 字母、`status == "simulated"`。
3. **`CheckoutProvenance`**：
   - 字段：`mandate_id: str`、`fingerprint: str`、`mandate_status: MandateStatus | None`、`request_key: str | None`、`receipt: Receipt | None`。
   - `__post_init__` 强校验：
     - `mandate_status.mandate_id == mandate_id`；
     - `receipt is None` 时 `request_key` 必须为 `None`，`receipt is not None` 时 `request_key` 必须为非空字符串；
     - `receipt` 存在时 `mandate_status` 不可为 `None`（拒绝孤儿收据），且 `receipt.order_id == f"sim_{fingerprint[:24]}"`、`receipt.currency == mandate_status.currency`、`receipt.amount <= mandate_status.max_amount`。

### 3.2 单查询只读快照与写路径对称加固

1. **`CheckoutStore.read_mandate(mandate_id, checkout) -> MandateStatus | None`**：
   - 无锁、无时钟读取 `mandates` 行并执行 `_parse_mandate_row()` 与 `_verify_mandate_binding()`。
2. **`CheckoutStore.read_receipt(mandate_id, checkout, *, request_key) -> Receipt | None`**：
   - 通过单条 `SELECT ... FROM receipts r LEFT JOIN mandates m ON m.id = r.mandate_id WHERE r.request_key = ?` 同时校验收据行完整性与父表 `mandates` 绑定。
3. **`CheckoutStore.find_provenance(mandate_id, checkout, *, request_key=None)` 与 `read_provenance(...)`**：
   - 通过单条 `FROM (SELECT 1) LEFT JOIN mandates m ON m.id = ? LEFT JOIN receipts rm ON rm.mandate_id = ? LEFT JOIN receipts rk ON ? IS NOT NULL AND rk.request_key = ?` 在同一只读快照中覆盖未批准、已批准未消费（`active`/`revoked`）、已消费、跨单重用 `request_key` 冲突、同一授权更换 `request_key` 重试，以及孤儿收据检测。

---

## 4. 验证结果

- 新增单元测试 `tests/test_checkout_provenance.py`（`4 passed, 46 subtests passed`），连同 `tests/test_checkout.py` 共 `15 passed, 61 subtests passed`。
- 全仓回归测试（`python -m pytest -q`）`4341 passed, 1561 subtests passed`。
