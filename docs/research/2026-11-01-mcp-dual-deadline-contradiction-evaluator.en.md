# Stripe MCP Dual-Deadline Contradiction Window Evaluator (`2026-10-31` vs. `2026-11-30`) and Zero-Grace Gating (Stage 1742)

> **中文对应版**: [2026-11-01-mcp-dual-deadline-contradiction-evaluator.md](2026-11-01-mcp-dual-deadline-contradiction-evaluator.md)  
> **Verification Date (Beijing Time)**: `2026-11-01`  
> **Related Artifacts**: [`lab/mcp_migration.py`](../../lab/mcp_migration.py) · [`tests/test_mcp_migration.py`](../../tests/test_mcp_migration.py)

---

## 1. Background & Problem Statement

On `2026-11-01` (the first calendar day after Stripe's originally documented `2026-10-31` key migration deadline), live verification of `https://docs.stripe.com/mcp` confirms that the official documentation still exhibits a dual-deadline contradiction:

1. **Earlier Documented Cutoff (`PREVIOUS_DEADLINE = 2026-10-31`)**: Multiple migration passages state that full-access secret keys (`full_access_secret`) and restricted API keys without the `agent` tag (`restricted_without_agent_tag`) must be migrated to OAuth or scoped Agent Keys before `2026-10-31` (ending support after November 1, 2026).
2. **Primary Notice Banner Cutoff (`DEADLINE = 2026-11-30`, `ENFORCEMENT_STARTS = 2026-12-01`)**: The `#### Update API key authentication by November 30, 2026` section states: `Migrate by November 30, 2026. Starting in December, Stripe MCP will stop accepting full-access secret keys and restricted API keys without the Agent tag.`

Prior to Stage 1742, `lab/mcp_migration.py` had three architectural gaps:

1. **Unmodeled Dual-Deadline Contradiction Window (`[2026-10-31, 2026-11-30)`) in Programmatic Assessment**: `assess(client, as_of=...)` only compared `as_of < deadline` (`2026-11-30` by default). Consequently, evaluating a legacy key on `2026-10-31` or `2026-11-01` returned the exact same `"migration_required"` status as `2026-10-16`, giving programmatic callers no structured signal that the earlier `2026-10-31` cutoff had already elapsed.
2. **Missing Zero-Grace CLI Enforcement Flag (`--strict-previous-deadline`)**: While the CLI report included a static `"previous_deadline": "2026-10-31"` string, it did not compute `previous_deadline_elapsed`, `calendar_days_until_previous_deadline`, `deadline_window_phase`, or `contradiction_exposed_count`, nor did it provide a `--strict-previous-deadline` flag to enforce zero-grace blocking (`"blocked_by_documented_policy"`) on `2026-10-31` / `2026-11-01`.
3. **Unvalidated `Finding` Dataclass & Missing Input Type Guards**: `Finding` lacked `__post_init__` validation—allowing contradictory combinations such as `auth_method="oauth"` with `status="blocked_by_documented_policy"` or `auth_method="full_access_secret"` with `status="recorded_supported_unverified"`—and `assess()`, `load_inventory()`, and `load_deadline_from_source_report()` did not raise `ValueError` on non-`Client` / non-`Path` arguments.

---

## 2. Architectural Design & Invariants (Stage 1742)

### 2.1 Three-Phase Deadline Window Classification (`classify_deadline_window`)

Added `DeadlineWindowPhase = Literal["before_previous_deadline", "contradiction_window", "on_or_after_deadline"]` and `classify_deadline_window(*, as_of, deadline=DEADLINE, previous_deadline=PREVIOUS_DEADLINE)`:

- `as_of < previous_deadline` (e.g., `2026-10-30`): `"before_previous_deadline"`.
- `previous_deadline <= as_of < deadline` (e.g., `2026-10-31` and `2026-11-01` through `2026-11-29`): `"contradiction_window"` (the earlier `2026-10-31` cutoff has elapsed while the `2026-11-30` notice has not yet arrived).
- `as_of >= deadline` (e.g., `2026-11-30` and `2026-12-01`): `"on_or_after_deadline"`.

### 2.2 Dual-Deadline Evaluation Model (`DualDeadlineFinding` & `assess_dual_deadline`)

Added frozen `DualDeadlineFinding` and `assess_dual_deadline(client, *, as_of, deadline=DEADLINE, previous_deadline=PREVIOUS_DEADLINE)`:

- Evaluates both `primary_status` (against `deadline`) and `strict_previous_status` (against `previous_deadline`).
- Sets `contradiction_exposed = (primary_status != strict_previous_status)`, which is `True` specifically when a legacy key (`full_access_secret` or `restricted_without_agent_tag`) is evaluated during `[2026-10-31, 2026-11-30)` (`primary_status == "migration_required"` while `strict_previous_status == "blocked_by_documented_policy"`).
- Supported authentication classes (`oauth`, `agent_key`) remain `"recorded_supported_unverified"` with `contradiction_exposed == False` across all dates, never claiming live account verification.

### 2.3 CLI Zero-Grace Flag (`--strict-previous-deadline`) & Fail-Closed Dataclass Invariants

- Added `--strict-previous-deadline` to the CLI: when enabled, `effective_deadline = min(deadline, PREVIOUS_DEADLINE)` is used so legacy keys are immediately reported as `"blocked_by_documented_policy"` on `2026-10-31` and `2026-11-01`.
- Extended the CLI JSON report with `effective_deadline`, `strict_previous_deadline_enforced`, `previous_deadline_elapsed`, `calendar_days_until_previous_deadline`, `deadline_window_phase`, and `contradiction_exposed_count`.
- Enforced fail-closed `__post_init__` invariants on `Finding` and `DualDeadlineFinding`, plus explicit `ValueError` guards on `assess()`, `assess_dual_deadline()`, `load_inventory()`, and `load_deadline_from_source_report()`.

---

## 3. Regression Validation

Ran `python -m pytest tests/test_mcp_migration.py tests/test_checkout_admission.py -q`:
- **`45 passed, 156 subtests passed`**.
