# 2026-10-31: Stage 1689 — Source monitor observation partitions telemetry

[中文](2026-10-31-source-monitor-observation-partitions.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1688 introduced `observation_summary` counters for quick fetch-health visibility.  
However, consumers still had to scan full `observations` to identify which sources were `changed`, `unknown`, or `error`.

Stage 1689 adds `observation_partitions`, grouping source IDs by fetch status and change class for deterministic downstream routing.

## Implementation

### `scripts/source_monitor.py`

- Added `partition_observations(observations)` returning:
  - `ok` / `error`
  - `baseline` / `unchanged` / `changed` / `unknown`
  - each key maps to an ordered source-ID list.
- Added top-level report field:
  - `observation_partitions`

### `tests/test_source_monitor.py`

- Extended failure-path report assertions for:
  - `observation_partitions.error`
  - `observation_partitions.unknown`
- Added `test_partition_observations_groups_source_ids` to verify grouping content and order.

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
  `observation_partitions` (source-ID partition index).

## Architecture impact

1. **Lower drift triage cost**: consumers can directly read source lists for `changed/unknown/error`.  
2. **Stronger gate interoperability**: complements `gate_health` and `observation_summary` with explicit list-level routing signals.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
