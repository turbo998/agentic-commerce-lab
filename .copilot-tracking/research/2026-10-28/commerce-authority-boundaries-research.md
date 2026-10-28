<!-- markdownlint-disable-file -->
# Task Research: Commerce authority boundaries

## Scope and Success Criteria

Continue from commit `1d9273d` and saved Stage 1651, preserving the user's
README and SVG changes byte-for-byte. Research Visa, Stripe, and Sierra using
public primary sources, separate observations from historical claims, and
identify one useful executable architecture asset. Work only during the
23:00-06:00 Asia/Shanghai window; start no new substantial phase after 05:30.

## Task Research Requests

The user requests bilingual daily research, architecture analysis contrasting
AI-native commerce with conventional web architecture and Well-Architected
guidance, technical assets, validation, and integration into origin/main.
Do not inflate stage, repository, PR, performance, or protocol-adoption counts.

## Research Executed

Initial repository inspection found existing bilingual daily reports and
Python unittest-based assets. Historical totals are inherited assertions,
not independently reproduced evidence for this session.
Primary-source research was delegated to a bounded research subagent.
Its complete findings are recorded at
.copilot-tracking/research/subagents/2026-10-28/commerce-primary-evidence-research.md.

## Evidence Log

- `README.md`: user-refactored executive overview and diagram navigation;
  excluded from edits.
- `research/daily/2026-10-28.md`: existing Stage 1651 resume boundary; append
  only a clearly dated incremental section.
- Baseline: `1d9273d`, clean working tree at 23:09 +08:00.
- Primary sources: Visa official docs/sample, Stripe MCP/SPT/error handling,
  Sierra official announcements and pinned Poppy spec/changelog, as recorded
  in the subagent evidence artifact.

## Key Discoveries

An agent's authenticated identity, user consent, payment authorization, and
successful settlement must not be treated as interchangeable claims.

- Stripe MCP migration by 2026-11-30 is verified and limited to MCP.
- Poppy Draft 0.3 scope hints are verified, but are company declarations rather
  than user approval; 0.3 is still In progress.
- Stripe explicitly documents indeterminate network/server errors and
  persisted same-key retries. The selected no-redispatch journal is stricter
  local policy, not a vendor requirement.
- Visa's official sample mocks payment; VIC detailed developer access returned
  403. No real network payment or settlement claim follows from the sample.
- `lab/checkout.py:52-153` provides atomic local simulated receipts, not an
  external payment attempt journal. Its behavior should remain unchanged.
- `lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py:80-164`
  checks supplied retry facts but does not persist dispatch or reconciliation.
- `research/architecture.md` already says that unknown payment outcomes must
  not trigger a new payment; a durable executable illustration is missing.
- AWS Well-Architected describes trade-off assessment, not mandatory three-tier
  topology: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
  (retrieved 2026-10-28).
- AWS Generative AI Lens already covers excessive agency, artifact versioning,
  failure handling, and traceability:
  https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html
  (retrieved 2026-10-28). Commerce invariants specialize these principles rather
  than replacing them or claiming all conventional architectures lack them.

## Technical Scenarios and Alternatives

Selected candidate: a separate SQLite-backed synthetic payment-attempt
journal. Reuse `Checkout` for validated minor-unit amounts and local cart
digests; do not make `CheckoutStore` simulate real PSP atomicity. Persist an
immutable operation binding before possible dispatch, grant a single local
dispatch decision, retain unknown outcomes after restart, and accept terminal
results only through a documented trusted reconciliation entry point.

This is a local recovery illustration, not payment authorization, a vendor
adapter, exactly-once remote delivery, or a cryptographic proof verifier.
Unknown outcomes may require human reconciliation; liveness is intentionally
not recovered by issuing fresh charges.

Alternative: continue generating unrelated upstream PR/stage totals.
Rejected because quantity is not evidence of commerce interoperability.

## Open Questions and Risks

Public documentation may differ from inherited daily-report claims.
Unavailable sources must remain explicit gaps, not successful checks.
Do not describe a local policy illustration as a vendor-certified adapter.
The existing full test suite passes 3,736 tests but regenerates tracked report
files. Restore only outputs changed by this session's test runs and refresh
content-equivalent index flags; do not commit regenerated historical reports.
The canonical main checkout is outside this session's access boundary.
Request its synchronization from the controlling session after origin/main
integration; do not access that checkout directly.

## Potential Next Research

Inspect primary sources and existing guards to select a non-duplicative
increment; evaluate consent, payment scope, and reconciliation boundaries.

## Planning Handoff

Local-code evidence and completed primary-source verification support the
recovery asset and bilingual synthesis. Handoff to the dated
commerce-authority-boundaries plan and details artifacts.
No implementation occurred during the research phase.

## Artifact Self-Check

Scope, request, evidence, discoveries, alternatives, risks, next research,
and handoff status checked. Known limitations include the VIC 403, evolving
working draft, and provider-specific production semantics. All evidence is
summarized, not reproduced as third-party source content.
