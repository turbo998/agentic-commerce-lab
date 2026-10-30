# 2026-10-31: Stage 1683 — Source monitor gate-health blocking reasons

[中文](2026-10-31-source-monitor-gate-health-reasons.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1682 introduced unified `gate_health` telemetry with a `blocking` flag.  
However, downstream automation still had to infer the specific blocking cause by inspecting multiple counters.

Stage 1683 keeps gate semantics unchanged and adds ordered `blocking_reasons` so blocking causes are directly consumable.

## Implementation

### `scripts/source_monitor.py`

- Extended `summarize_gate_health(...)` with:
  - `blocking_reasons` (ordered list, fixed order:
    `observation_errors` → `policy_errors` → `cross_source_mismatch`)
- Reasons are included only when the corresponding counter is greater than 0.
- `blocking` semantics are unchanged (any gate counter > 0 still blocks).

### `tests/test_source_monitor.py`

- Added assertions in failure paths that `blocking_reasons` includes `observation_errors`.
- Added parser-version mismatch assertions that `blocking_reasons` includes `cross_source_mismatch`.
- Extended `test_summarize_gate_health_counts_and_blocking` to validate reason ordering and content.

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
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `gate_health.blocking_reasons` (currently `[]`, meaning no blocking causes).

## Architecture impact

1. **Gate diagnosability improved**: automation can classify blocking causes without rescanning observation-level details.  
2. **Semantics unchanged**: fail-fast boundaries and exit conditions remain stable.  
3. **Boundary unchanged**: still public-source retrieval plus offline aggregation, with no payment or account authority changes.
