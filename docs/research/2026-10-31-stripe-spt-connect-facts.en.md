# 2026-10-31: Stage 1676 — Stripe SPT Connect selected-facts extraction in source monitor

[中文](2026-10-31-stripe-spt-connect-facts.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1674 added selected facts for seller-view `stripe-spt`, but `stripe-spt-connect` was still hash-only.  
To reduce false drift signals from Connect-page wording/layout edits, Stage 1676 adds **parser-backed facts for the Connect view** while preserving offline monitoring boundaries.

## Implementation

### 1) `scripts/source_monitor.py`

- Added shared country-list extractor `_extract_supported_country_codes(text)` for seller/connect reuse.
- Added `stripe_spt_connect_facts(body)` extracting:
  - `supported_country_count` / `supported_country_codes_sha256`
  - `has_connect_platforms_section`
  - `has_network_business_profile`
  - `has_shared_payment_granted_token`
  - `has_stripe_account_header`
  - `covers_direct_destination_separate_charges`
- Extended `observe(...)` to compute facts + `policy_change` for `source.id == "stripe-spt-connect"`.
- Extended `main()` previous-facts lookup for `stripe-spt-connect` and updated `policy_scope`.

### 2) `tests/test_source_monitor.py`

Added tests for:
- positive extraction and required country-list validation for `stripe_spt_connect_facts`;
- `observe` baseline fact capture for `stripe-spt-connect`.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `15/15` passing;
- focused regression: `39/39` passing;
- source monitor refreshed `research/daily/2026-10-31-sources.json`
  (`checked_at=2026-10-31T02:07:43.239151+08:00`) with no fetch failures.

## Architecture impact

1. **Seller/connect parity in facts monitoring:** SPT monitoring now covers both seller and connect perspectives.
2. **Facts vs. release claim separation:** `policy_change` remains a selected-facts drift signal, not a product-release conclusion.
3. **Boundary unchanged:** public-document fetch + local parsing only; no credentials, account introspection, or payment authority.
