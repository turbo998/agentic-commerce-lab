# 2026-10-31: Stage 1684 — Source monitor cross-source status index

[中文](2026-10-31-source-monitor-cross-source-status-index.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

`cross_source_checks` already carries full check details, but many automation consumers only need
the current status for each `check_id`. Previously, each consumer had to scan the array and build
its own mapping.

Stage 1684 adds report-level `cross_source_statuses` as a stable `check_id -> status` index.

## Implementation

### `scripts/source_monitor.py`

- Added `index_cross_source_statuses(checks)`:
  - accepts only valid dict entries with `check_id` and `status`;
  - returns a stable map: `{ "<check_id>": "<status>" }`.
- Added report field in `main()`:
  - `cross_source_statuses`
- Existing gate and exit semantics remain unchanged.

### `tests/test_source_monitor.py`

- Added `test_index_cross_source_statuses_returns_stable_map`.
- Extended error and mismatch paths to assert `cross_source_statuses` is present and consistent.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `25/25` passing;
- focused regression: `49/49` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes
  `cross_source_statuses`, currently:
  - `stripe-spt-country-list-parity=consistent`
  - `stripe-spt-connect-required-markers=consistent`
  - `stripe-spt-parser-version-parity=consistent`

## Architecture impact

1. **Simpler consumption path**: downstream automation can read check status in O(1) without array scans.  
2. **Stable semantics**: no change to blocking boundaries or gate behavior.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
