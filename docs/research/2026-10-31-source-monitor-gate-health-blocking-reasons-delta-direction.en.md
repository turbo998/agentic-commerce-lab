# 2026-10-31: Stage 1714 — Source monitor gate_health blocking-reasons delta direction telemetry

[中文](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-direction.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1713 already provides single-value `blocking_reasons_delta_total_changes`.  
Downstream systems still had to derive direction semantics themselves (increase/decrease/mixed/none).

Stage 1714 adds `blocking_reasons_delta_direction` with stable direction enums.

## Implementation

### `scripts/source_monitor.py`

- Added field:
  - `gate_health.blocking_reasons_delta_direction`
- Semantics:
  - emits `null` when no prior reasons exist (`previous_blocking_reasons is None`);
  - with prior reasons:
    - `none`: no additions/removals;
    - `increase`: additions only;
    - `decrease`: removals only;
    - `mixed`: both additions and removals.

### `tests/test_source_monitor.py`

- Baseline assertion: `blocking_reasons_delta_direction is None`;
- Changed assertion: direction is `increase`;
- Unchanged assertion: direction is `none`;
- Remaining regression remains green.

## Visual map (direction derivation)

```mermaid
flowchart LR
    A[added[]] --> D{added?}
    B[removed[]] --> E{removed?}
    D -->|no| F
    D -->|yes| G
    E -->|no| F
    E -->|yes| H
    F[none or decrease]
    G[increase or mixed]
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
  `gate_health.blocking_reasons_delta_direction` (current baseline run: `null`).

## Architecture impact

1. **Direct direction-based routing:** downstream systems can route on enum values without recomputation.  
2. **More stable consumer logic:** canonical direction semantics reduce cross-service branching drift.  
3. **Boundary unchanged:** still public-source retrieval and offline aggregation, with no payment execution or account authority.
