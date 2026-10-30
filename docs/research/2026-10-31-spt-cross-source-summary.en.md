# 2026-10-31: Stage 1681 — Cross-source summary telemetry for SPT checks

[中文](2026-10-31-spt-cross-source-summary.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1680 expanded SPT cross-source gating to three checks.  
Stage 1681 adds structured `cross_source_summary` telemetry so those checks can be consumed as stable counters and a blocking flag.

## Implementation

### `scripts/source_monitor.py`

- Added `summarize_cross_source_checks(checks)` returning:
  - `total`
  - `consistent`
  - `mismatch`
  - `unavailable`
  - `blocking` (`mismatch > 0`)
- Added report-level `cross_source_summary`.
- Updated exit logic to use `cross_source_summary.blocking`, preserving existing fail-fast semantics.

### `tests/test_source_monitor.py`

Added/updated:
- `test_summarize_cross_source_checks_counts_and_blocking`
- assertions for `cross_source_summary` in failure and parser-mismatch paths.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `23/23` passing;
- focused regression: `47/47` passing;
- source snapshot refreshed to `checked_at=2026-10-31T03:45:59.910880+08:00`,
  with `cross_source_summary={"total":3,"mismatch":0,"blocking":false,...}`.

## Architecture impact

1. **Gate observability improved** with compact machine-friendly summary metrics.
2. **Semantics unchanged**: `blocking` still derives from mismatches only.
3. **Boundary unchanged**: public-source retrieval and local aggregation only, with no payment/account authority.
