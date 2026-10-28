<!-- markdownlint-disable-file -->
# Stage 1660 details

## Context
Research: .copilot-tracking/research/2026-10-29/checkout-admission-research.md
User-directed continuation via controller 269 from 779ebe6, 02:45 BJT.
Bilingual/main/full tests/CI, protected README/assets and nighttime gates unchanged.

## Phase 1: semantic admission before durable dispatch
Extract existing unique_members into lab/json_members.py; import it from
lab/mcp_migration.py to retain the same public name and errors. No inventory policy
or Stripe inbox behavior changes.
Add lab/checkout_admission.py: require trusted journal/operation/exact route config;
reuse require_bound_json_mutation before parsing, require POST, strict UTF-8 object,
exact Checkout keys, duplicate rejection, bounded integer tokens, no floats/
nonfinite constants or surrogate strings. Match trusted quote, then call reserve.
Do not compute prices from client fields or multiply quantity by total amount.
Use existing DispatchDecision/unknown/retry/conflict behavior; no new DB schema.
Add tests/test_checkout_admission.py for gate order, duplicate escaped names,
scalar/schema errors, resource limits, route changes, no failed-request reservation,
restart/concurrency, semantically identical differently signed bodies and terminal
retry behavior. Test legacy unique_members import compatibility explicitly.

## Phase 2: bilingual boundary research and navigation
Create docs/research/2026-10-29-checkout-admission.md and .en.md with primary Stripe/
RFC/Python evidence, synthetic executable example and explicit authority boundaries.
Append daily bilingual records and near-top stage archive index, never README/assets.
Explain bytes vs decoded semantics vs trusted quote vs consent vs journal identity.

## Phase 3: integrated validation and release preparation
Focused admission/migration/checkout/payment-attempt/binding tests, then full suite.
Compile lab/scripts, run both existing demos, execute bilingual examples and check
changed public local links; protected content stays identical to 1d9273d.
Restore only generated historical reports and fix introduced failures.
Commit with coauthor/non-force push main. Final-SHA CI and controller canonical
clean/lock/protected-path receipt are post-commit runtime gates. Verify final clean
refs, main..HEAD and branch hygiene without touching canonical files directly.
