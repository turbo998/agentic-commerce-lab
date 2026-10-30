# 2026-10-31: Stage 1679 — SPT Connect required-markers cross-check

[中文](2026-10-31-spt-connect-marker-check.md) | [Stage archive index](../stage-archive-index.md)

## Background and objective

Stage 1678 escalated seller/connect country-list divergence to a nonzero gate.  
Stage 1679 extends integrity checks for the Connect view by adding a **required-markers cross-check** so key Connect semantics must remain present.

## Implementation

### `scripts/source_monitor.py`

- Added `spt_connect_marker_check(observations)` producing:
  - `check_id="stripe-spt-connect-required-markers"`
  - `status ∈ {consistent, mismatch, unavailable}`
- Validates these markers remain `true`:
  - `has_connect_platforms_section`
  - `has_network_business_profile`
  - `has_shared_payment_granted_token`
  - `has_stripe_account_header`
  - `covers_direct_destination_separate_charges`
- `main()` now emits two `cross_source_checks`:
  1) seller/connect country-list parity  
  2) connect required-markers check
- Existing gate behavior applies: any check with `status="mismatch"` returns nonzero.

### `tests/test_source_monitor.py`

Added tests for:
- `consistent/mismatch/unavailable` states of `spt_connect_marker_check`;
- `main()` nonzero exit when connect markers mismatch.

## Validation

Executed in the Beijing night window:

```bash
python -m unittest tests.test_source_monitor -v
python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts tests.test_mcp_migration -q
python scripts/source_monitor.py
```

Results:
- `tests.test_source_monitor`: `20/20` passing;
- focused regression: `44/44` passing;
- source snapshot refreshed to `checked_at=2026-10-31T03:04:34.643161+08:00`,
  with both cross-source checks currently `consistent`.

## Architecture impact

1. **Cross-source validation now covers semantic presence**, not only country-list parity.
2. **Mismatch output is actionable** via explicit missing-marker lists.
3. **Boundary unchanged**: public-source retrieval + local fact comparison only, no live payment/account operations.
