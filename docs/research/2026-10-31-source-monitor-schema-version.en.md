# 2026-10-31: Stage 1687 — Source monitor report schema versioning

[中文](2026-10-31-source-monitor-schema-version.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stages 1681–1686 continuously expanded `source_monitor` report fields.  
To avoid consumer ambiguity while fields evolve, the report needs an explicit schema anchor.

Stage 1687 adds a top-level `schema_version` to declare the current JSON contract version.

## Implementation

### `scripts/source_monitor.py`

- Added constant:
  - `REPORT_SCHEMA_VERSION = "source-monitor-report-v1"`
- Added top-level report field:
  - `schema_version`

### `tests/test_source_monitor.py`

- Extended `main()` report assertions to verify `schema_version == REPORT_SCHEMA_VERSION`.
- Added `test_report_schema_version_is_stable` to pin the schema baseline.

## Validation

Executed during the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `28/28` passing;
- focused regression: `52/52` passing;
- refreshed `research/daily/2026-10-31-sources.json` now includes top-level
  `"schema_version": "source-monitor-report-v1"`.

## Architecture impact

1. **Better compatibility control**: consumers can select parsing strategy by `schema_version`.  
2. **Safer evolution**: future field changes can be versioned explicitly instead of silently breaking consumers.  
3. **Boundary unchanged**: still public-source retrieval and offline aggregation, with no payment execution or account authority.
