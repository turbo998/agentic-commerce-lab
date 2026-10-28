---
applyTo: '.copilot-tracking/changes/2026-10-29/checkout-admission-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1660 plan: signed checkout admission

## Context and requirements
Continue from 779ebe6 under controller 269's 02:45 BJT instruction, unchanged
permissions/model, bilingual documentation, tests/main and protected README/assets.
23:00-06:00 only; from 05:30 no new phase, only safe closeout.
Research: .copilot-tracking/research/2026-10-29/checkout-admission-research.md
Details: .copilot-tracking/details/2026-10-29/checkout-admission-details.md

## Phases and dependencies
- [x] Implement semantic admission, shared duplicate hook and focused regressions.
  Details lines 9-22.
- [x] Archive bilingual evidence/examples and daily/index navigation.
  Depends on phase 1; details lines 24-28.
- [x] Complete integrated local validation/fix iteration and release preparation.
  Depends on phase 2; details lines 30-37.

## Risks and mitigation
Do not let authenticated client prices become authoritative: exact comparison to
trusted immutable Checkout, not construction of approval from JSON.
Duplicate last-wins and bool/int equality: unique_members plus exact numeric types.
Parser resources: existing 1 MiB binding cap, bounded integer tokens and explicit
decode/recursion failures. No general JSON canonicalizer or custom parser.
Retain migration hook's public import/error behavior; old inventory rules unchanged.
Consent/revocation/time validity remain trusted caller preconditions, not atomically
enforced by this facade. No actual provider invocation or fresh-key retry.

## Success and runtime gates
Failed gates do not call reserve; valid first admission returns existing decision,
semantic retries never gain another dispatch. Targeted/full suites and old demos,
examples/links/protected paths pass. Runtime final-SHA CI, controller canonical receipt,
clean refs/main..HEAD and unrelated-branch preservation are required before completion.
