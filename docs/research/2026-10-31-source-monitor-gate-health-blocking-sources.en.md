# 2026-10-31: Stage 1691 — Source monitor gate_health blocking-sources telemetry

[中文](2026-10-31-source-monitor-gate-health-blocking-sources.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1690 added `observation_error_sources` and `policy_error_sources` to `gate_health`.  
Consumers still needed to merge and deduplicate both lists when a single blocker-source set was required.

Stage 1691 adds `blocking_sources`, a directly consumable deduplicated blocker source-ID set.

## Implementation

### `scripts/source_monitor.py`

- Extended `summarize_gate_health(...)` with:
  - `blocking_sources = unique(observation_error_sources + policy_error_sources)`
- Ordering rule: preserve source order from observations, taking `observation_error_sources` first and then unseen `policy_error_sources`.

### `tests/test_source_monitor.py`

- Extended failure-path assertions for:
  - `gate_health.blocking_sources`
- Updated `test_summarize_gate_health_counts_and_blocking` to validate ordering and dedup behavior.

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
  `gate_health.blocking_sources` (empty in the current successful run).

## Architecture impact

1. **Further convergence for blocker routing**: consumers can use one `blocking_sources` field directly.  
2. **Clearer gate object semantics**: `gate_health` now exposes both granular lists and the unified set.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
