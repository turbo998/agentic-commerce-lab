# 2026-10-31: Stage 1686 — Source monitor gate-health blocking check IDs

[中文](2026-10-31-source-monitor-gate-health-blocking-checks.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1685 already added `cross_source_partitions`, including mismatch check IDs.  
However, run-level gate consumers reading only `gate_health` still needed cross-field joins to identify which checks were blocking.

Stage 1686 surfaces blocking check IDs directly in `gate_health`.

## Implementation

### `scripts/source_monitor.py`

- Extended `summarize_gate_health(...)` to accept `cross_source_partitions`.
- Added new `gate_health` field:
  - `cross_source_blocking_checks` (currently equals `cross_source_partitions.mismatch`)
- Existing blocking semantics remain unchanged.

### `tests/test_source_monitor.py`

- Extended failure-path assertions to verify `cross_source_blocking_checks` exists and can be empty.
- Extended parser-version mismatch path to verify `cross_source_blocking_checks` contains
  `stripe-spt-parser-version-parity`.
- Added `test_summarize_gate_health_includes_cross_source_blocking_checks`.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `27/27` passing;
- focused regression: `51/51` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `gate_health.cross_source_blocking_checks` (currently an empty list).

## Architecture impact

1. **Direct run-level routing**: consumers can route blockers from `gate_health` alone.  
2. **Lower consumer coupling**: fewer cross-field joins between `gate_health` and `cross_source_partitions`.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
