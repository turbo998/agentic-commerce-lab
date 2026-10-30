# 2026-10-31: Stage 1680 — SPT parser-version parity gate

[中文](2026-10-31-spt-parser-version-parity.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1679 established content and marker gates for seller/connect SPT facts.  
Stage 1680 tightens auditability by adding a **parser-version parity check**, ensuring selected facts come from reviewed parser grammars.

## Implementation

### `scripts/source_monitor.py`

- Added `spt_parser_version_check(observations)`:
  - `check_id="stripe-spt-parser-version-parity"`
  - expected versions:
    - `stripe-spt` → `stripe-spt-facts-v1`
    - `stripe-spt-connect` → `stripe-spt-connect-facts-v1`
  - returns `status ∈ {consistent, mismatch, unavailable}` and includes `expected/actual` on mismatch.
- `cross_source_checks` now includes three gates:
  1) country-list parity  
  2) connect required markers  
  3) parser-version parity
- Existing fail-fast rule remains: any `mismatch` makes monitor exit nonzero.

### `tests/test_source_monitor.py`

Added tests for:
- `consistent/mismatch/unavailable` parser-version states;
- nonzero `main()` exit on parser-version mismatch.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `22/22` passing;
- focused regression: `46/46` passing;
- source snapshot refreshed to `checked_at=2026-10-31T03:42:06.083179+08:00`,
  with all three cross-source checks currently `consistent`.

## Architecture impact

1. **Parser-grammar drift is now blocking**, preventing success-shaped output under unreviewed versions.
2. **Mismatch diagnostics are explicit** via `expected/actual` parser-version fields.
3. **Boundary unchanged**: public-source extraction and local comparison only; no payment-account or key operations.
