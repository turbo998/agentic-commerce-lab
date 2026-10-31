# 2026-10-31: Stage 1713 — Source monitor gate_health blocking-reasons delta total-changes telemetry

[中文](2026-10-31-source-monitor-gate-health-blocking-reasons-delta-total-changes.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1712 already emits the four-part `blocking_reasons_delta_counts` summary.  
For threshold-based branching, downstream consumers still had to compute `added + removed` themselves.

Stage 1713 adds `blocking_reasons_delta_total_changes` as a direct single-value change magnitude.

## Implementation

### `scripts/source_monitor.py`

- Added field:
  - `gate_health.blocking_reasons_delta_total_changes`
- Semantics:
  - emits `null` when no prior reasons exist (`previous_blocking_reasons is None`);
  - otherwise emits `len(added) + len(removed)`.

### `tests/test_source_monitor.py`

- Baseline assertion: `blocking_reasons_delta_total_changes is None`;
- Changed assertion: total changes equals `1`;
- Unchanged assertion: total changes equals `0`;
- Remaining regression remains green.

## Visual map (total change magnitude)

```mermaid
flowchart LR
    A[added[]] --> C[total_changes]
    B[removed[]] --> C
    C --> D[len(added) + len(removed)]
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
  `gate_health.blocking_reasons_delta_total_changes` (current baseline run: `null`).

## Architecture impact

1. **Direct threshold branching:** downstream pipelines can route/alert on single-value change magnitude without recomputing counts.  
2. **Lower consumer overhead:** fewer repeated array-expansion/count operations downstream.  
3. **Boundary unchanged:** still public-source retrieval and offline aggregation, with no payment execution or account authority.
