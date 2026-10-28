<!-- markdownlint-disable-file -->
# Primary-source evidence: Visa, Stripe, Sierra

Recorded by the parent from research agent `commerce-primary-evidence`'s
completed report. The agent returned evidence in conversation, not a file.
Research ran 2026-10-28 23:10-23:22 Asia/Shanghai, within the permitted window.
No vendor conformance or real payment execution was tested.

## Evidence and findings

1. Visa TAP uses RFC 9421 signatures for agent/request/intent verification.
   Optional payment information is not settlement proof:
   https://developer.visa.com/docs/trusted-agent-protocol
   https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-unveils-trusted-agent-protocol-for-ai-commerce.html
2. Official Visa cart processing explicitly mocks payments:
   https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/routes/cart.py#L248-L270
   A sample processed/confirmed status is not a real charge.
3. VIC consumer controls and payment-network capabilities are distinct from
   TAP trusted communication:
   https://corporate.visa.com/en/sites/visa-perspectives/newsroom/product-drop-intelligent-commerce.html
   Detailed VIC developer page returned 403. Full API, production eligibility,
   and settlement contracts remain unverified. Reliable announcement dates
   were not exposed, so no Visa publication date is inferred.
4. Stripe MCP migration is by November 30, 2026, with incompatible key
   rejection starting in December. This is MCP-specific, not all Stripe APIs:
   https://docs.stripe.com/mcp
   Agent-tagged keys and approval rules govern merchant-account operations:
   https://docs.stripe.com/keys#agent-keys
5. SPT binds merchant, amount, currency, expiry. Recurring SPT and single-use
   third-party Resolve are distinct; active is not payment success:
   https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=agent
   https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller
   Example API version 2026-09-30.preview is not release/GA evidence.
6. Sierra announcement dates checked in official page metadata: Personal Agent
   Protocol 2026-10-06, initial Poppy draft 2026-10-09:
   https://sierra.ai/blog/introducing-personal-agent-protocol
   https://sierra.ai/blog/poppy
7. Pinned protocol snapshot a95b757872533a6ef1e1a9bcf29802857d2e5ff4 records
   version 0.2 published 2026-10-24; 0.3 remains In progress:
   https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json
   https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/shared/changelog.mdx#L3-L11
8. Draft 0.3 scope hints are company assertions, not user approval. Messaging
   does not itself authorize an account action:
   https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L772-L808
   https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L1913-L1915
   Account/Session Token definitions: same spec, lines 319-350.
9. Stripe network and server errors can leave indeterminate side effects.
   Persisted provider keys support cross-process retries under provider rules;
   API v1 retention is at least 24 hours, unlike API v2 semantics:
   https://docs.stripe.com/error-low-level#network-errors
   https://docs.stripe.com/error-low-level#server-errors
   https://docs.stripe.com/error-low-level#post-requests
   The journal's no-redispatch policy is locally stricter, not vendor-mandated.
10. PaymentIntent succeeded, balance available, and bank payout completion are
    separate facts:
    https://docs.stripe.com/payments/paymentintents/lifecycle
    https://docs.stripe.com/payments/balances#balance-states
    https://docs.stripe.com/payments/balances#settlement-time

## Recommendations, gaps, and handoff

Separate identity, user consent, merchant operations, scoped payment-method
access, payment results, and settlement. The local journal should persist
unknown outcomes and avoid remote exactly-once claims. No evidence requires
SQLite or one local dispatch. Production adapter/rail semantics, authenticated
consent, and trusted provider observations remain outside this research.
No clarification is required for the bounded offline asset.
