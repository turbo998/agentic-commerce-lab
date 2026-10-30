# 2026-10-31: Stage 1688 — Source monitor observation summary telemetry

[中文](2026-10-31-source-monitor-observation-summary.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

The report already includes per-source `observations` and multiple gate-level aggregations.  
For dashboard consumers, source-fetch health and drift shape still required scanning the full observations array.

Stage 1688 adds `observation_summary` to expose stable run-level counters for source-fetch outcomes and change distribution.

## Implementation

### `scripts/source_monitor.py`

- Added `summarize_observation_changes(observations)` returning:
  - `total` / `ok` / `error`
  - `baseline` / `unchanged` / `changed` / `unknown`
- Added top-level report field:
  - `observation_summary`

### `tests/test_source_monitor.py`

- Extended failure-path report assertions to validate `observation_summary` (`total/error/unknown`).
- Added `test_summarize_observation_changes_counts` for counting logic.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `29/29` passing;
- focused regression: `53/53` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `observation_summary` with `ok/error` and `baseline/unchanged/changed/unknown` counts.

## Architecture impact

1. **Direct source-fetch health readout**: no full-array scan required to estimate collection health and drift shape.  
2. **More complete monitoring surface**: gate-level and fetch-level telemetry are now explicitly separated.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
