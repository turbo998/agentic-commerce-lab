<!-- markdownlint-disable-file -->
# Stage 1653 planning log

## Discrepancy Log
DR-1: Provider lifecycle "payment failed" can mean requires_payment_method,
which is retryable, not terminal. Resolution: keep unknown; no new dispatch.
DR-2: PaymentIntent JSON does not authenticate account context. Resolution:
require externally trusted retrieval account; do not trust metadata claims.
DR-3: Main checkout is outside this session's access scope. Resolution:
request controller-owned synchronization after the verified final push.

## Validator Findings
Inline bounded-plan validation: no Critical/High findings. No custom validator
is configured; retain this single continuous source-to-code trace inline.
Checked amount/type/mode/account/reference binding, pending states, full-amount
policy, routing exclusions, unchanged generic journal behavior and final checks.

## Implementation Paths Considered
Selected pure readback gate using the existing journal's prebound reference.
Rejected new SDK/network payment, generic webhook parsing, metadata-based
authentication, and automatic approval or dispatch retry.

## Validation Coverage and Follow-On Work
Targeted state and adversarial input tests plus full repository checks.
Production authenticated retrieval, fresh readback and ID recovery, signed
webhooks, partial capture, destination charges and settlement remain deferred.

Final local evidence: 16 new tests, 46 targeted tests and all 3,771 repository
tests passed. compileall and both existing demos passed. Both bilingual
examples executed; 26 changed/new local links passed. README/assets remain
identical to 1d9273d. No unrelated report regeneration is included.
The source and plan boundaries remain unchanged; no Critical/High discrepancy.
Origin/main publication, final CI and controller-owned canonical synchronization
are final runtime gates; no direct access to the canonical checkout is allowed.
