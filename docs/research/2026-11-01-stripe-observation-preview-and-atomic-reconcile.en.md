# Stage 1741: Single-Transaction Stripe PaymentIntent Reconciliation, Strict Reference Regex Parity, and Lock-Free Observation Preview (`StripeObservationPreview`)

> 中文版: [2026-11-01-stripe-observation-preview-and-atomic-reconcile.md](2026-11-01-stripe-observation-preview-and-atomic-reconcile.md)

## Executive Summary

Within the Agentic Commerce Stripe `PaymentIntent` observation and reconciliation layer (`lab/stripe_observation.py`), Stage 1741 identifies and closes three architectural gaps:

1. **Two-Connection TOCTOU Window in `reconcile_stripe_intent()`**: Previously, `reconcile_stripe_intent()` opened a first read-only SQLite connection via `journal.read(operation)`, validated the `PaymentIntent` mapping outside any transaction, and then opened a second `BEGIN IMMEDIATE` connection via `journal.reconcile(...)`. Unlike `associate_stripe_intent()` and `accept_stripe_readback()`, this split execution across two connections. Stage 1741 consolidates `reconcile_stripe_intent()` into a single `BEGIN IMMEDIATE` transaction (`journal._find()` + `validate_stripe_intent()` + `journal._reconcile_in_transaction()`).
2. **Strict `pi_[A-Za-z0-9_]+` Regex Parity in `validate_stripe_intent()`**: Previously, `associate_stripe_intent()` enforced `re.fullmatch(r"pi_[A-Za-z0-9_]+", expected_reference)`, whereas `validate_stripe_intent()` only checked `previous.provider_reference.startswith("pi_")`, allowing malformed references such as `"pi_"` or `"pi_secret/value"` persisted via `journal.reconcile()` to pass validation. Both paths now enforce `_PI_RE.fullmatch(...)`.
3. **Lock-Free Single-Snapshot Reconciliation Preview (`StripeObservationPreview`)**: Added `StripeObservationPreview`, `find_stripe_observation_preview()`, and `read_stripe_observation_preview()` so dry-run reconciliation and post-incident auditing can evaluate a retrieved `PaymentIntent` against `payment_attempts`—including denormalized binding parity, terminal transition rules, and cross-operation `provider_reference` uniqueness—in a single lock-free `SELECT` query (`would_advance` / `is_terminal`).

---

## Architecture Comparison: Two-Connection Reconciliation vs. Single-Transaction Reconcile & Lock-Free Preview

| Dimension | Prior Baseline (Stage 1653) | Hardened Agentic Commerce Design (Stage 1741) |
|---|---|---|
| `reconcile_stripe_intent()` transaction boundary | 2 SQLite connections (`journal.read` + `journal.reconcile`) | 1 `BEGIN IMMEDIATE` connection (`_find` + `validate_stripe_intent` + `_reconcile_in_transaction`) |
| `provider_reference` format gate | `associate` enforced `pi_[A-Za-z0-9_]+`; `validate` only checked `.startswith("pi_")` | Uniform `_PI_RE.fullmatch(r"pi_[A-Za-z0-9_]+")` across all observation paths |
| Dry-run / forensic preview | In-memory `validate_stripe_intent` only; did not check persisted terminal conflicts or cross-operation reference uniqueness | `find_stripe_observation_preview` / `read_stripe_observation_preview` evaluate all storage and semantic gates in one `SELECT` |

---

## Verification

- `python -m pytest tests/test_stripe_observation.py tests/test_stripe_association.py tests/test_stripe_readback.py -q`: `69 passed, 133 subtests passed`.
