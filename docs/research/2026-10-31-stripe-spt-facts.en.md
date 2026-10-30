# Stage 1674: Stripe SPT Selected-Facts Extraction in `source_monitor`

[中文](2026-10-31-stripe-spt-facts.md) |
[Daily report](../../research/daily/2026-10-31.en.md) |
[Previous stage](2026-10-31-source-monitor-noise-filter.en.md)

**Finding:** We added `stripe_spt_facts(body)` to
[`scripts/source_monitor.py`](../../scripts/source_monitor.py), so `stripe-spt` now emits
reviewable selected facts through `policy_facts` / `policy_change`. This separates
“contract-level signal” from raw markdown hash drift and avoids treating hash changes as release claims by default.

## 1. Why this stage is needed

Stage 1673 filtered second-level `expires_at` jitter, but there was still an interpretation gap between
`change="changed"` and “did protocol facts really change.” Stage 1674 closes that gap with structured facts,
aligned with the existing Stripe MCP facts flow:

- `api_version` marker (for example `2026-09-30.preview`)
- supported-country footprint (`supported_country_count` + `supported_country_codes_sha256`)
- key capability markers (`recurring_interval`, `shared_payment.granted_token.deactivated`)

## 2. Code changes

1. Added `stripe_spt_facts(body)`:
   - requires exactly one `Stripe-Version` preview marker;
   - parses `### View all supported countries` list;
   - emits `parser_version="stripe-spt-facts-v1"` plus stable fact fields.
2. Added `previous_source_facts(...)` to recover prior successful facts by
   `source_id + parser_version`; kept `previous_policy_facts(...)` as the MCP wrapper for compatibility.
3. Updated `main()` to inject prior-facts context for both `stripe-mcp` and `stripe-spt`,
   producing consistent `policy_change` values (`baseline/unchanged/changed/unknown`).
4. Updated `policy_scope` text to cover both MCP and SPT selected facts.

## 3. Tests and validation

- Updated [`tests/test_source_monitor.py`](../../tests/test_source_monitor.py):
  - positive extraction and required-field rejection tests for `stripe_spt_facts`;
  - source/parser-precise matching tests for `previous_source_facts`.
- Passed:
  - `python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts -v` (`24/24`)
  - Stage 1652–1674 focused regression (`529/529`).

## 4. Snapshot outcome at 01:07 BJT

Latest `research/daily/2026-10-31-sources.json` records:

- `stripe-spt` still reports `change="changed"` versus prior-day hash baseline, but now has first selected-facts baseline:
  - `api_version=2026-09-30.preview`
  - `supported_country_count=34`
  - `supported_country_codes_sha256=6ae0a508...054133`
  - `has_recurring_interval=true`
  - `has_deactivated_webhook_event=true`
- `policy_change="baseline"` (first-day fact baseline), enabling future fact-level drift detection.

