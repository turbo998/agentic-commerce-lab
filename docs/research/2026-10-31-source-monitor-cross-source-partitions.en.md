# 2026-10-31: Stage 1685 — Source monitor cross-source status partitions

[中文](2026-10-31-source-monitor-cross-source-partitions.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1684 added `cross_source_statuses` (`check_id -> status`).  
For alert-routing workflows, consumers still needed another pass to group checks by status and identify active `mismatch` or `unavailable` blockers.

Stage 1685 adds `cross_source_partitions`, directly exposing status-grouped check-ID lists.

## Implementation

### `scripts/source_monitor.py`

- Added `partition_cross_source_checks(checks)`:
  - returns:
    - `consistent`: `list[check_id]`
    - `mismatch`: `list[check_id]`
    - `unavailable`: `list[check_id]`
  - ignores malformed/non-dict entries for stable output shape.
- Added report field in `main()`:
  - `cross_source_partitions`
- Existing gate and exit semantics remain unchanged.

### `tests/test_source_monitor.py`

- Added `test_partition_cross_source_checks_groups_check_ids`.
- Extended failure and mismatch paths to assert `cross_source_partitions` consistency with `cross_source_statuses`.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `26/26` passing;
- focused regression: `50/50` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes:
  - `cross_source_partitions.consistent` (currently 3 items)
  - `cross_source_partitions.mismatch` (currently empty)
  - `cross_source_partitions.unavailable` (currently empty)

## Architecture impact

1. **More direct alert routing**: consumers can directly read mismatch/unavailable check IDs.  
2. **Higher consumption consistency**: partition logic is standardized in producer output.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
