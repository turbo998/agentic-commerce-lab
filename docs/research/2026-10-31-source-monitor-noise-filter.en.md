# Stage 1673: Stripe SPT Dynamic-Timestamp Noise Filter in `source_monitor`

[中文](2026-10-31-source-monitor-noise-filter.md) |
[Daily report](../../research/daily/2026-10-31.en.md) |
[Previous stage](2026-10-31-stripe-claim-read.en.md)

**Finding:** We added source-specific normalization in
[`scripts/source_monitor.py`](../../scripts/source_monitor.py) via
`_normalize_source_noise(source_id, text)`. For `source_id=="stripe-spt"`, volatile sample
`"expires_at": <unix-seconds>` values are redacted to a fixed placeholder before hashing.
This preserves detection of substantive text drift while preventing second-level sample jitter
from being misread as release evidence.

## 1. Evidence background (2026-10-31 00:06–00:44 BJT)

- The first `source_monitor` snapshot (`00:06`) showed one `change="changed"` source: `stripe-spt`.
- Consecutive fetches + unified diff on the same URL showed only this sample-field drift:
  `"expires_at": 1795968579` vs `"expires_at": 1795968581`.
- This type of drift should not be treated as protocol-release evidence; the hash layer needs a minimal,
  auditable, source-specific noise filter.

## 2. Code changes

In `scripts/source_monitor.py`:

1. Added `_normalize_source_noise(source_id, text)`:
   - currently applied only to `stripe-spt`;
   - replaces `"expires_at": <10-13 digit number>` with
     `"expires_at": <dynamic-unix-timestamp>`.
2. Extended `fingerprint` signature to
   `fingerprint(body, content_type, *, source_id: str | None = None)`,
   applying source-specific normalization after HTML visible-text extraction and before whitespace collapse.
3. Updated `observe` to pass `source.id` into `fingerprint`.
4. Bumped report metadata `normalization` to
   `utf8-visible-html-text-or-markdown-whitespace-v2-with-source-noise-filters`.

## 3. Tests and validation

- Updated [`tests/test_source_monitor.py`](../../tests/test_source_monitor.py):
  - under `stripe-spt`, hashes remain equal across different `expires_at` seconds after normalization;
  - `observe` returns `change="unchanged"` for dynamic `expires_at` drift in a second fetch.
- Passed:
  - `python -m unittest tests.test_source_monitor tests.test_mcp_policy_facts -v` (`21/21`)
  - Stage 1652–1673 focused regression (`526/526`).

## 4. Boundaries and follow-ups

1. The filter is **source-targeted**, so other source hashes keep their prior semantics.
2. Only volatile sample timestamps are redacted; protocol-critical wording (paths, status codes, parameters)
   is not normalized away.
3. A one-time hash rebaseline can still appear on `2026-10-31` vs `2026-10-30` because the
   normalization version changed; this reflects monitoring-semantics evolution, not a protocol release by itself.

