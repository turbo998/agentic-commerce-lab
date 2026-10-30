# 2026-10-31: Stage 1677 — SPT seller/connect parity cross-check in source monitor

[中文](2026-10-31-spt-parity-cross-check.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1676 introduced selected facts for both seller (`stripe-spt`) and connect (`stripe-spt-connect`) views.  
Stage 1677 adds a **cross-source parity check** so the monitor can compare both views’ country-list summaries before interpretation.

## Implementation

### 1) `scripts/source_monitor.py`

- Added `spt_country_list_check(observations)` returning a report-level check object:
  - `check_id="stripe-spt-country-list-parity"`
  - `status ∈ {consistent, mismatch, unavailable}`
- Check behavior:
  - compares only when both seller/connect observations are `ok` with usable selected facts;
  - compares `supported_country_count` and `supported_country_codes_sha256`;
  - returns explicit `unavailable` reason when data is missing/unusable.
- `main()` now emits `cross_source_checks` while preserving the boundary that fact checks are not product-release claims.

### 2) `tests/test_source_monitor.py`

Added tests for:
- consistent parity (`status="consistent"`),
- mismatched parity (`status="mismatch"`),
- unavailable parity (`status="unavailable"`),
- and `main()` failure-path coverage that still writes `cross_source_checks`.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `17/17` passing;
- focused regression: `41/41` passing;
- refreshed `research/daily/2026-10-31-sources.json` at
  `checked_at=2026-10-31T02:14:58.884908+08:00`, including
  `cross_source_checks[0].status="consistent"`.

## Architecture impact

1. **Adds a mutual-validation layer across seller/connect views** instead of treating each selected-facts stream in isolation.
2. **Makes uncertainty explicit** via `unavailable` rather than silently treating missing data as consistent.
3. **Boundary unchanged**: public-document parsing and local comparison only, with no account/key/payment operations.
