# 2026-10-31: Stage 1678 — SPT parity mismatch fail-fast gate

[中文](2026-10-31-spt-parity-mismatch-gate.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1677 emitted `cross_source_checks`, but seller/connect divergence was only a reported signal.  
Stage 1678 promotes that divergence to an **explicit nonzero exit gate**, so parity conflicts are treated as blocking review signals.

## Implementation

### `scripts/source_monitor.py`

- Keeps Stage 1677 `spt_country_list_check(...)` report output.
- Extends `main()` exit logic:
  - any observation fetch/parse failure (`status == "error"` or `policy_error`) => nonzero;
  - any `cross_source_checks[].status == "mismatch"` => nonzero.
- `consistent`/`unavailable` semantics remain explicit:
  - `consistent`: pass;
  - `unavailable`: governed by underlying fetch/parse state, with no success-shaped fallback.

### `tests/test_source_monitor.py`

Added `test_main_returns_nonzero_on_cross_source_mismatch` to verify:
- when seller/connect observations are both `ok` but country summaries diverge,
  `main()` returns `1` and writes `cross_source_checks[0].status == "mismatch"`.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `18/18` passing;
- focused regression: `42/42` passing;
- source snapshot refreshed to `checked_at=2026-10-31T02:54:19.488213+08:00`,
  and current parity status is `consistent`, so monitor exits successfully.

## Architecture impact

1. **Escalates from warning to gate:** cross-source fact conflicts now block the monitor outcome.
2. **Preserves explainability:** failure still carries explicit `cross_source_checks` evidence for review.
3. **Boundary unchanged:** public-source fetch and local fact comparison only, with no live payment/account authority.
