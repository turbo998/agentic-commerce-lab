# 2026-10-31: Stage 1682 — Source monitor gate-health summary telemetry

[中文](2026-10-31-source-monitor-gate-health-summary.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1681 added `cross_source_summary` for mismatch visibility across cross-source checks.  
However, `source_monitor` nonzero exits also include fetch failures and selected-facts parse failures, which still required downstream automation to inspect `observations` in detail.

Stage 1682 adds a unified `gate_health` summary so blocking status and blocking origin are directly machine-readable.

## Implementation

### `scripts/source_monitor.py`

- Added `summarize_gate_health(observations, cross_source_summary)` that returns:
  - `observation_errors` (count of `status="error"`)
  - `policy_errors` (count of non-empty `policy_error`)
  - `cross_source_mismatch` (from `cross_source_summary.mismatch`)
  - `blocking` (`true` when any of the above gates is nonzero)
- Added report-level `gate_health`.
- Exit code now directly reuses `gate_health.blocking`, preserving fail-fast behavior while improving observability.

### `tests/test_source_monitor.py`

- Added `test_summarize_gate_health_counts_and_blocking`.
- Extended failure and parser-version mismatch paths to assert `gate_health` fields and counts.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `24/24` passing;
- focused regression: `48/48` passing;
- refreshed source snapshot now includes
  `gate_health={"observation_errors":0,"policy_errors":0,"cross_source_mismatch":0,"blocking":false}`.

## Architecture impact

1. **Gate interpretability improved**: automation can classify blocking causes without combining exit-code and per-observation scans.  
2. **Complementary to Stage 1681**: `cross_source_summary` reports cross-source consistency, while `gate_health` reports run-level gate status.  
3. **Boundary unchanged**: still public-source retrieval plus offline aggregation, with no payment execution or account-authority changes.
