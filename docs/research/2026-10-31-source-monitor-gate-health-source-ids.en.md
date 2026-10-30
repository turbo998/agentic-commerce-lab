# 2026-10-31: Stage 1690 — Source monitor gate_health source-ID telemetry

[中文](2026-10-31-source-monitor-gate-health-source-ids.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

`gate_health` already reports blocker counts (`observation_errors`, `policy_errors`).  
Consumers still had to rescan `observations` to identify which sources caused those blockers.

Stage 1690 adds source-ID lists directly into `gate_health` for deterministic blocker localization.

## Implementation

### `scripts/source_monitor.py`

- Extended `summarize_gate_health(...)` with:
  - `observation_error_sources`: source IDs where `status="error"`
  - `policy_error_sources`: source IDs with non-empty `policy_error`
- Existing gate counts and blocking semantics remain unchanged.

### `tests/test_source_monitor.py`

- Extended failure-path report assertions for:
  - `gate_health.observation_error_sources`
  - `gate_health.policy_error_sources`
- Updated `test_summarize_gate_health_counts_and_blocking` to verify new source-ID lists.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `30/30` passing;
- focused regression: `54/54` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `observation_error_sources` and `policy_error_sources` under `gate_health`
  (both empty in the current successful run).

## Architecture impact

1. **One-step blocker localization**: no second pass over `observations` is needed to pinpoint fetch or facts-parse failures.  
2. **More complete gate surface**: `gate_health` now carries counts, reason classes, and source-ID details together.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
