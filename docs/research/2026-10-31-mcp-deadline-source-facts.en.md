# 2026-10-31: Stage 1675 — Source-fact-driven Stripe MCP deadline simulation

[中文](2026-10-31-mcp-deadline-source-facts.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

After `scripts/source_monitor.py` started extracting `stripe-mcp` selected facts (including `deadline`),
`lab.mcp_migration` was still using a hardcoded deadline.  
Stage 1675 closes that gap by allowing the offline migration simulator to read the deadline from the
daily monitored snapshot, **without adding any live account access or key usage**.

## Implementation

### 1) `lab/mcp_migration.py`

- Added `load_deadline_from_source_report(path)`:
  - parses only local JSON snapshot metadata;
  - requires exactly one successful `stripe-mcp` selected-facts row;
  - requires `parser_version=stripe-mcp-auth-notice-v1` and ISO `deadline`.
- Extended `assess(...)` with a `deadline` parameter (defaulting to the existing baseline constant),
  so boundary status can be driven by observed source facts.
- Added CLI option `--source-report <daily-sources.json>`:
  - when present, uses snapshot `deadline` and `checked_at`;
  - emits `deadline_source` and `deadline_parser_version` for explicit provenance.

### 2) `tests/test_mcp_migration.py`

- Extended CLI harness to support `--source-report`.
- Added tests for:
  - boundary status changes when source-fact deadline overrides the baseline;
  - explicit failure on missing/mismatched parser facts (no silent success-shaped fallback).

## Validation

Executed within the Beijing night window:

```bash
python -m unittest tests.test_mcp_migration -v
```

Result: `12/12` passing.

## Architecture impact

1. **Monitor/simulator alignment without runtime coupling**: source monitor owns “official text fact extraction,” while migration simulation consumes snapshot facts through a file contract.
2. **No new payment authority**: the feature reads local metadata only—no Stripe API calls, key material handling, or account verification.
3. **Auditable boundary shifts**: outputs now expose `deadline_source` and parser version, making deadline-driven behavior changes traceable.
