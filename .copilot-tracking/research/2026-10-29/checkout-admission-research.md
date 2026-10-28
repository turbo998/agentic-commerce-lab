<!-- markdownlint-disable-file -->
# Stage 1660 research: signed JSON to trusted checkout admission

## Scope and request
Controller 269 requests normal progression from 779ebe6 at 02:45 BJT.
Preserve README/assets from 1d9273d, bilingual/main/full tests/CI, model/permissions.
Night-only 23:00-06:00; no new phase from 05:30.
Close the explicit Stage 1659 gap: signed bytes are not valid checkout semantics.

## Dated evidence and continuous trace
Research 02:46-02:49 BJT, inline: configured Researcher Subagent absent, and this
is one bounded trace rather than independent research threads.
- https://docs.stripe.com/payments/advanced/dynamically-update-amounts.md?payment-ui=elements
  retrieved 02:47: server recalculates totals, does not trust client prices/totals,
  authorizes updates by business rules and restricts mutable payment state.
  This is guidance, not a newly dated product release or permission to update.
- https://www.rfc-editor.org/rfc/rfc8259.html sections 4/6/8/9:
  duplicate-name behavior varies; nonfinite numbers are outside the grammar;
  UTF-8 and Unicode comparison/limits matter. Duplicate rejection is a local policy,
  not an assertion that the RFC grammar universally forbids duplicate names.
- https://docs.python.org/3.12/library/json.html#repeated-names-within-an-object
  retrieved 02:48: default decoder uses last duplicate and accepts NaN/Infinity;
  object_pairs_hook/parse_constant allow explicit rejection.
- lab/checkout.py Checkout validates immutable positive signed-64-bit amount/
  quantity and uppercase currency, with amount representing total including tax/
  shipping, not unit price. Do not recalculate quantity*amount.
- lab/payment_attempts.py PaymentOperation is trusted/already-approved;
  reserve owns durable one-dispatch/unknown behavior, not consent verification.
- lab/request_binding.py already enforces one-signature/current-value/raw-byte
  binding and 1 MiB. Reuse it before JSON parsing; do not normalize before digest.
- lab/mcp_migration.py unique_members is a reusable duplicate hook. Extract the
  existing pure hook to lab/json_members.py and re-export the same name at the old
  module to preserve error/API behavior. Stripe inbox keeps its separate error
  contract unchanged; do not rewrite historical synthetic pipeline/benchmarks.

## Selected local profile and scenario
Opt-in checkout admission facade: trusted journal, PaymentOperation and configured
exact route URI, plus trusted Stage 1659 signature snapshot and current ingress.
Require POST on configured route, bind bytes, then decode one UTF-8 object with
exact merchant/currency/sku/quantity/amount keys. Reject decoded duplicate names,
floats/exponents/nonfinite literals, boolean quantities, unknown keys and mismatches.
Compare semantic fields exactly to existing trusted Checkout, never calculate a
trusted price/approval/provider/key from request JSON. Reject unpaired surrogates.
Bound integer token length before conversion; rely on trusted Checkout bounds
and exact comparison. Return existing DispatchDecision from journal.reserve only
after all gates. No HTTP, real signature verifier, provider call or authorization.

## Alternatives and unresolved boundaries
Rejected: json.loads defaults, parsed dict as original evidence, signed client
totals as pricing authority, silently coercing bool/float/currency, raw-body hash as
business idempotency, issuing new operation IDs on retry and building a new journal.
Different signed whitespace/key order may describe the same operation; journal
identity remains authoritative. Failures must not consume first dispatch.
Consent/expiry/revocation and operation lookup are trusted caller prerequisites,
not made atomic with reserve here. Full signature adapter and production schema,
pricing/tax engine, multi-item carts, replay and provider wire mapping remain outside.
No new Visa/Sierra release verification. No blocking evidence gap.

## Validation and handoff self-check
Test gate ordering, duplicate escaped names, exact field/types, parser limits,
route/body tampering, unchanged existing unknown state, persistence, concurrency
and one dispatch across semantically equal but differently signed JSON.
Full suite, old migration/checkout/journal/binding regressions, demos, examples,
links and protected-path comparison; final SHA CI and controller canonical receipt.
Checked scope/request, dated evidence/prior art, alternatives/scenarios, risks,
open boundaries and handoff. Proceed /rpi-plan with this research.
