# Stage 1653: Five intermediate PaymentIntent states must not close an unknown payment

[中文](2026-10-28-stripe-observation.md) | [Daily research](../../research/daily/2026-10-28.en.md) |
[Stage 1652](2026-10-28-authority-recovery.en.md)

**Verified 2026-10-28, Asia/Shanghai, starting 23:40; baseline `83d4e5e`.**
This is `synthetic` offline policy research and testing, not a product release,
Stripe SDK, live payment integration, model benchmark, or vendor certification.
The user's README and assets remain unchanged.

## 1. Primary evidence: a failed attempt does not make the entire Intent terminal

The [Stripe lifecycle](https://docs.stripe.com/payments/paymentintents/lifecycle)
describes failed attempts returning to `requires_payment_method` for later
retry. `requires_capture` still awaits capture; `processing` can last days.
A generic failure flag, successful tool call, or HTTP 200 cannot establish the
final economic outcome.

| Stripe `status` | This asset's mapping | Invalid inference |
|---|---|---|
| `requires_payment_method` | `pending → unknown` | A decline terminally closes the Intent and grants new spending authority |
| `requires_confirmation` | `pending → unknown` | Ready for confirmation means paid |
| `requires_action` | `pending → unknown` | Required consumer action can be skipped |
| `processing` | `pending → unknown` | Asynchronous processing means success |
| `requires_capture` | `pending → unknown` | A hold or `amount_capturable` means collected funds |
| `succeeded` | `succeeded` only if `amount_received` equals the approved amount | Partial collection is enough, or payment implies bank payout/fulfillment |
| `canceled` | Local `failed` only with `amount_received=0` | Cancellation grants new approval or proves every external money consequence is cleared |

The final two rows are a **strict local amount policy**, not the full Stripe
state definition. Partial/overcapture, multicapture, and refunds need separate
business states. No status grants another dispatch decision; Stage 1652's
single-use approval constraint is unchanged.

The [PaymentIntent object](https://docs.stripe.com/api/payment_intents/object)
distinguishes `amount`, `amount_received`, `currency`, `livemode`, `id`,
`object`, and `status`. [Connect account context](https://docs.stripe.com/api/connected-accounts)
is request-scoped via `Stripe-Account`; arbitrary `metadata.account` is not proof
of the account under which an object was retrieved. These sources were read
again this round; observation dates are not publication dates. No new Visa/Sierra
release verification was performed; cross-vendor boundaries retain the explicit
Stage 1652 evidence and limitations.

## 2. Bind subject, account, mode, and amount before reconciliation

New [`lab/stripe_observation.py`](../../lab/stripe_observation.py) uses existing
`PaymentAttemptJournal.read/reconcile`, without changing schema or approval:

- Require an already trusted, persisted `pi_` reference; never claim an Intent
  based solely on incoming JSON.
- Match the trusted retrieval account exactly to `provider_account`.
  `stripe:test` / `stripe:live` are **local namespace conventions** binding mode
  into the existing immutable operation fingerprint.
- Require matching object type, ID, currency, integer amount, and boolean mode.
  A boolean cannot masquerade as money, nor a float as an integer amount.
- Explicitly require `transfer_data=null` and `on_behalf_of=null`. This stage
  supports direct-account readbacks only; destination/on-behalf-of routing is
  rejected rather than silently downgraded.
- Reject unknown states, omitted fields, reference conflicts, and mismatched
  amounts without changing journal outcomes. Existing terminal monotonicity
  prevents an old `processing` snapshot overwriting confirmed success.
- Never return or persist the raw payload, `client_secret`, description, or
  metadata.

**Trusted input is not automatic verification.** The caller must authenticate
retrieval, credentials, API version, freshness, merchant/account mapping, and
initial association. This function performs no networking or webhook signature
checks, verifies no real Stripe object's existence, and does not infer a real
payment from structurally valid JSON.

## 3. Runnable synthetic example

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import reconcile_stripe_intent

with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "attempts.sqlite3")
    op = PaymentOperation("tenant", "op", "approval", "stripe:test",
                          "acct_synthetic", "key", Checkout("shop", "USD", "sku", 1, 1000))
    journal.reserve(op)
    # Trusted synthetic association, not inferred from an incoming event.
    journal.reconcile(op, observation="pending", provider_reference="pi_synthetic")
    payload = {"object": "payment_intent", "id": "pi_synthetic", "livemode": False,
               "amount": 1000, "amount_received": 0, "currency": "usd",
               "status": "requires_capture", "transfer_data": None, "on_behalf_of": None}
    result = reconcile_stripe_intent(journal, op, retrieved_account="acct_synthetic",
                                    intent=payload)
    assert result.outcome == "unknown"
    assert not journal.reserve(op).dispatch_allowed
```

```powershell
python -m unittest tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

Tests cover state mapping, missing fields, amount/currency/ID/account/mode
substitution, terminal persistence, routing exclusions, and sensitive-field
exclusion. No model calls, real payments, latency coordinates, or readiness scores.

## 4. Architecture conclusion and remaining boundaries

Well-Architected reliability becomes a **provider-semantic adaptation boundary**:
trusted transport, object ownership, and business terminality are separate gates,
not financial states chosen by a model from prose. A modular monolith can enforce
them without more payment agents. Authoritative unknown-ID recovery, signed-event
ingress, Connect routing, partial capture, and settlement need separate contracts
and acceptance checks; this stage does not claim to implement them.
