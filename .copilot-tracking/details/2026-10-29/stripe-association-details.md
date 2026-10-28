<!-- markdownlint-disable-file -->
# Stage 1663 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/stripe-association-research.md
Controllers 278/269 request one Stage 1663 from df5f6b5; canonical sync269.
Bilingual/main/full tests/CI, protected README/assets and nightly window unchanged.

## Phase 1: bounded association gate
Modify lab/stripe_observation.py: add associate_stripe_intent requiring trusted
journal/operation/account/expected_reference and complete trusted readback mapping.
Inside BEGIN IMMEDIATE find existing bound attempt, reuse validate_stripe_intent
against transient expected-reference view, reject changed association and bind
only unassociated unknown attempt using _reconcile_in_transaction(pending).
Same-reference retries return previous state without downgrading or new dispatch.
Missing reservation/unassociated terminal state reject; old APIs stay unchanged.
No inferred correlation from metadata/amount, no new authentication/provider calls.

## Phase 2: focused proof
Create tests/test_stripe_association.py: full field/status/context validation before
first reference write, explicit expected reference, reservation requirement,
strict scalar types, metadata non-authority, idempotency/terminal preservation.
Test provider/account uniqueness, both concurrent races, fresh process and actual
post-update/commit rollback. Preserve existing observation/atomic-readback/journal.
Acceptance: no new dispatch/outcome inferred, previous state unchanged on rejection.

## Phase 3: archive and integrated validation
Create bilingual docs/research/2026-10-29-stripe-association pair; append daily pair
and stage index. Explain adapter correlation and Checkout Sessions recommendation.
Full unittest discover, compileall lab scripts, both demos, executable bilingual
examples/local links; restore generated reports and verify protected paths.
Fix introduced failures, exact-file commit, non-force main publication.
Final-SHA CI and controller canonical clean/zero-lock/protected receipt gate completion.
