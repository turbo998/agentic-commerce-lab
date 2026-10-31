# 2026-10-31: Stage 1712 — Source monitor gate_health blocking-reasons delta counts telemetry

[中文](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-counts.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1711 already introduced `blocking_reasons_delta_payload_id` for single-value routing and deduplication.  
For monitoring and analytics, downstream systems still had to expand `previous/current/added/removed` arrays and count lengths manually.

Stage 1712 adds `blocking_reasons_delta_counts` for direct reason-delta count summaries.

## Implementation

### `scripts/source_monitor.py`

- Added field:
  - `gate_health.blocking_reasons_delta_counts`
- Semantics:
  - emits `null` when no prior reasons exist (`previous_blocking_reasons is None`);
  - otherwise emits:
    - `previous`: count of prior reasons
    - `current`: count of current reasons
    - `added`: count of added reasons
    - `removed`: count of removed reasons

### `tests/test_source_monitor.py`

- Baseline assertion: `blocking_reasons_delta_counts is None`;
- Changed assertion: counts equal `{previous:0,current:1,added:1,removed:0}`;
- Unchanged assertion: counts equal `{previous:0,current:0,added:0,removed:0}`;
- Remaining regression remains green.

## Visual map (delta-count aggregation)

```mermaid
flowchart LR
    A[previous/current/added/removed arrays] --> B{prior exists?}
    B -->|no| C[counts = null]
    B -->|yes| D[counts.previous = len(previous)]
    B --> E[counts.current = len(current)]
    B --> F[counts.added = len(added)]
    B --> G[counts.removed = len(removed)]
```

## Validation

Executed during the user-authorized daytime window:

```bash
python -m pytest tests/test_source_monitor.py -q
python -m pytest -q
python scripts/source_monitor.py --registry research/sources.json --output-dir research/daily
```

Results:
- `tests/test_source_monitor.py`: `43 passed, 6 subtests passed`;
- full regression: `4267 passed, 1089 subtests passed`;
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `gate_health.blocking_reasons_delta_counts` (current baseline run: `null`).

## Architecture impact

1. **Lower aggregation overhead:** downstream systems can consume delta counts directly without array expansion.  
2. **Improved analytics consistency:** canonical count fields reduce cross-service metric drift.  
3. **Boundary unchanged:** still public-source retrieval and offline aggregation, with no payment execution or account authority.
