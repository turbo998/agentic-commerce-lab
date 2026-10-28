# Stage 1652: Restarting after a lost payment response must not authorize another charge

[中文](2026-10-28-authority-recovery.md) | [Daily research](../../research/daily/2026-10-28.en.md)

**Verified on 2026-10-28, Asia/Shanghai; nightly increment from `1d9273d`.**
This delivers public-source research and an offline recovery reference, not a
vendor release, interoperability certification, live payment integration, or
model benchmark. The user's README/SVG refactor remains unchanged. Inherited
PR/repository totals and performance claims are not independently reproduced here.

## Current primary evidence: five authority domains are not one `authorized=true`

| Product/protocol | Directly verified observation | Invalid inference |
|---|---|---|
| Visa TAP | RFC 9421 signatures convey trusted agent, intent, consumer recognition, and optional payment information; the [official sample](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/routes/cart.py#L248-L270) explicitly uses mock payment processing | Signature verification or sample `processed` is not issuer approval, a real charge, or settlement evidence |
| Sierra Poppy | Account/Session Tokens and OAuth scopes govern account access; Draft 0.3 `auth.scope_hints` declares `changes` and `personal_data`, explicitly company assertions, not user approval | Chat instructions, `changes=none`, or `personal_data=false` do not authorize an account action |
| Stripe MCP | Merchant-account OAuth / Agent API key permissions; current docs confirm migration **by 2026-11-30**, with full-access secret keys and restricted keys lacking the Agent tag rejected starting in December | This is not a cutoff for all Stripe API keys or consumer purchase consent |
| Stripe SPT | Payment-method access is bounded by receiving merchant, amount, currency, and expiry; recurring SPTs exist while third-party Resolve remains single-use | `active`, Resolve, or credential possession is not PaymentIntent success or settlement |
| Payment result / balance | PaymentIntents distinguish `requires_action`, `processing`, `requires_capture`, and `succeeded`; balances separately distinguish `pending` / `available` | Payment completion does not mean funds reached a merchant bank or goods were fulfilled |

Sources and version boundaries:

1. Visa [TAP developer docs](https://developer.visa.com/docs/trusted-agent-protocol),
   [TAP announcement](https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-unveils-trusted-agent-protocol-for-ai-commerce.html),
   and [Intelligent Commerce announcement](https://corporate.visa.com/en/sites/visa-perspectives/newsroom/product-drop-intelligent-commerce.html).
   Separate VIC consumer-control/network capabilities from TAP trusted
   communication. The detailed VIC developer page returned **403**; full API,
   production eligibility, and settlement contracts were not verified.
2. Sierra [announced Personal Agent Protocol](https://sierra.ai/blog/introducing-personal-agent-protocol)
   on **2026-10-06** and [introduced the Poppy initial draft](https://sierra.ai/blog/poppy)
   on **2026-10-09**. The pinned
   [version registry](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
   records 0.2 published **2026-10-24**, while the
   [changelog](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/shared/changelog.mdx#L3-L11)
   labels 0.3 **In progress**, not a stable release.
   [Scope hints](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L772-L808)
   and the [chat authorization boundary](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L1913-L1915)
   use a pinned working-draft snapshot, not an asserted published standard.
3. Stripe [MCP authentication](https://docs.stripe.com/mcp),
   [Agent keys](https://docs.stripe.com/keys#agent-keys), and SPT docs for the
   [agent](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=agent)
   and [seller](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller).
   Example API version `2026-09-30.preview` is not a release date or GA evidence.
   Agent-key approval rules govern merchant operations, not consumer consent.
4. Stripe [PaymentIntent lifecycle](https://docs.stripe.com/payments/paymentintents/lifecycle)
   and [balance / settlement states](https://docs.stripe.com/payments/balances#balance-states).
   Do not extrapolate these state mappings to another payment rail without
   rail-specific evidence.

## 1. Three-tier topology is not Well-Architected; AI-native does not require more agents

The [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
evaluates architecture qualities and trade-offs, rather than prescribing one
presentation/application/database topology.
Its [Generative AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html)
already addresses excessive agency, traceability, reliable communication,
failure handling, and artifact versioning. Neither framework is inherently
incompatible with AI; "three-tier systems duplicate charges" is not a measured
baseline in this increment.

Commerce specializes these principles into **economic side-effect invariants**:

| Boundary | Possible gap, not an inevitable three-tier defect | Commerce workload requirement |
|---|---|---|
| Reasoning / execution | Model paraphrases a retry into a new operation | Trusted execution persists logical identity and immutable request bindings |
| Identity / consent | Authenticated agent is treated as approved consumer intent | Verify agent identity, consumer approval, and payment scope separately |
| Tools / spending authority | Callable tool or scope hint is treated as payment permission | Check final amount, merchant, purpose, expiry, and revocation at execution |
| Local transaction / remote payment | Missing local receipt is assumed to mean no charge | Persist before send; retain unknown outcomes instead of creating another charge |
| Payment / fulfillment | Payment confirmation is treated as delivery, settlement, or completed refund | Model and reconcile payment, order, fulfillment, and refund independently |

These are logical boundaries that can start in a modular monolith, not a mandate
for six microservices. Model failover must not silently change the payee,
payment credential, or provider idempotency key.

## 2. Persist recovery facts instead of only checking retry arguments

Existing [`CheckoutStore`](../../lab/checkout.py) atomically consumes a local
simulated approval and returns a `simulated` receipt. It cannot atomically
commit a remote payment. The existing
[lost-response guard](../../lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py)
checks supplied retry facts but does not persist dispatch.

New [`PaymentAttemptJournal`](../../lab/payment_attempts.py) reuses `Checkout`
integer minor units and local cart digests, while independently persisting:

- Immutable tenant, logical operation, approval reference, provider/account,
  provider idempotency key, and cart binding.
- One local dispatch decision inside `BEGIN IMMEDIATE`, committing `unknown`
  before a possible send.
- No renewed dispatch after restart, timeout, duplicate request, or confirmed
  failure; a new operation/key cannot reuse the same approval in a tenant.
- Provider/account-scoped idempotency keys and payment references, preventing
  cross-tenant rebinding of the same provider request or payment.
- Trusted reconciliation mapping `pending` to `unknown`, or recording
  `succeeded` / `failed`; contradictory terminal results and changed provider
  references raise explicit errors.

Local transitions:

```text
no record -- trusted reserve + commit --> unknown [one dispatch decision]
unknown  -- no response / pending -----> unknown [no new dispatch]
unknown  -- trusted provider result ---> succeeded | failed
terminal -- identical result ---------> same terminal [no new dispatch]
terminal -- contradictory result -----> explicit AttemptConflict
```

**Safety/liveness trade-off:** A crash after commit but before send also leaves
`unknown`, potentially requiring human investigation of an unsent operation.
This illustration deliberately does not recover by sending under a fresh key.
One SQLite dispatch decision is not remote exactly-once delivery and cannot
stop a malicious caller replaying a previously obtained decision. A real adapter
must separately enforce authentication, approval expiry/revocation, provider
idempotency retention, authoritative status lookup, and signed webhook checks.

[Stripe low-level error handling](https://docs.stripe.com/error-low-level#network-errors)
says network errors do not establish non-execution; HTTP 500 can also leave an
indeterminate outcome. Its [POST/idempotency guidance](https://docs.stripe.com/error-low-level#post-requests)
permits retries using the **same persisted key**, including across process
restarts, under provider-specific rules. This asset's one-dispatch decision is
a **stricter local policy, not a Stripe requirement**. API v1 idempotent results
are retained for at least 24 hours; reuse after pruning can create a new request.
Long-unresolved operations require lookup/reconciliation, not automatic replay.
API v2 has different semantics; v1 retention is not a universal Stripe API rule.

## 3. Runnable asset and acceptance boundaries

```powershell
python -m lab.payment_attempts
python -m unittest tests.test_payment_attempts tests.test_checkout -q
```

The demo explicitly emits `synthetic=true`, `real_payments=false`,
`after_restart.dispatch_allowed=false`, and `outcome=unknown`. Only trusted
synthetic reconciliation yields `succeeded`; `settlement_verified=false`
remains explicit. Tests are in
[`tests/test_payment_attempts.py`](../../tests/test_payment_attempts.py).

Use this as a **recovery-design exercise** for procurement, replenishment, or
post-purchase mutations. It is not a TAP/SPT/Poppy wire-format implementation
and does not verify approval origin, OAuth scope, signatures, settlement finality,
or inventory fulfillment. `approval_id` is an externally trusted single-use
approval reference, not a self-approval interface for a model.

## 4. Evidence limits and next work

Observation dates are not publication dates. Documentation availability does
not establish account, region, or preview eligibility. Historical release dates,
migration cutoffs, and protocol versions need current primary-source checks.
This increment generates no model evaluation report, latency coordinates, or
production-readiness score. Production follow-up includes an independent approval
service, signed-event ingress, distributed outbox/recovery workers, provider
status mappings, and tamper-evident audit, not more self-authorizing agents.
