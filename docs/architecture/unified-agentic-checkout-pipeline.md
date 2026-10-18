# 7-Gate End-to-End Unified Agentic Checkout Pipeline & Chaos Resilience Architecture

> **Verification Date**: `2026-10-19` (`Asia/Shanghai`)  
> **Executable Orchestrator**: `lab/unified_checkout_pipeline.py` (`python -m lab.unified_checkout_pipeline`)  
> **7-Card 4:5 Resilience Report**: [`reports/agentic-commerce-resilience-bench/index.html`](../../reports/agentic-commerce-resilience-bench/index.html) & [`report.json`](../../reports/agentic-commerce-resilience-bench/report.json)

---

## 1. Architectural Motivation: Why Sequential Fail-Fast Gating Is Mandatory

In an AI-Native Agentic Commerce system, each downstream operation carries escalating cost and irreversibility:
1. **WAF/Edge Verification (`~0.02 ms`, $0 cost)**: Pure cryptographic verification of RFC 9421 headers, Visa TAP / Stripe Directory key liveness, and in-memory `(principal_did, sku_id)` scarcity counters.
2. **Catalog & Policy Broker Verification (`~0.03 ms`, $0 external cost)**: Verifying RFC 9530 `sha-256` shard digests and `summary == terms` structural agreement before touching external APIs.
3. **Customs & FinOps Envelope Evaluation (`~0.05 ms`, prevents negative margin)**: Checking `DDP`/WCO 6-digit `HS` locks and `stripe-token-billing` + payment rail margin against AP2 `PR #165` `COST_ENVELOPE_EXCEEDED` before locking supplier inventory.
4. **Supplier Hold Saga & Connect SPT Settlement (`~0.08 ms`, financial state mutation)**: Executing two-phase `manual` capture holds across GDS/PMS/Compute providers and Stripe Connect `separate_charges_and_transfers` with single-use `SPT Resolve`.
5. **CE 3.0 Cryptographic Evidence Sealing & EOD Reconciliation (`~0.09 ms`, immutable audit trail)**: Compiling the 4-pillar Merkle root across all 17 ACP `PR #316` Appendix C gateways and verifying the `00:00 UTC` three-way SFTP × MPP Tempo × Metronome ledger equation.

By ordering the 7 gates strictly from **cheapest/stateless** to **stateful/financial**, any adversarial or malformed request short-circuits at the earliest possible gate with zero downstream side effects.

---

## 2. The 7-Gate Deterministic Pipeline Specification

```text
Incoming Agent HTTP Request
  │
  ├─► [Gate 1: Edge RFC 9421 Attestation & Principal Anti-Sybil Quota]
  │     • Verifies 6 mandatory signed components, Content-Digest, <=60s TTL, single-use nonce
  │     • Verifies Visa TAP / Stripe Agent Directory key status == "active" & WebMCP same-origin
  │     • Enforces (principal_did, sku_id) scarcity quota & max_distinct_agents_per_principal
  │
  ├─► [Gate 2: UCP PR #866 Catalog sha-256 Barrier & Policy Broker]
  │     • Verifies RFC 9530 Repr-Digest on catalog shards & rejects truncated deletes
  │     • Enforces natural-language summary == structured terms amount & consequential confirmation
  │
  ├─► [Gate 3: Cross-Border Incoterms DDP & WCO 6-Digit HS Tariff Lock]
  │     • Blocks silent DDP -> DAP/DDU incoterm downgrades & HS6 subheading hallucination
  │
  ├─► [Gate 4: Token Burn + Payment Rail Margin & AP2 Fiduciary Circuit Breaker]
  │     • Trips AP2 PR #165 COST_ENVELOPE_EXCEEDED if Token Burn + Rail Fee > Platform Take
  │
  ├─► [Gate 5: Multi-Leg Booking Two-Phase Hold Saga]
  │     • Requires capture_method="manual", commit <= min(TTL) - 15s, and valid refund cutoff
  │
  ├─► [Gate 6: Connect Multi-Seller Split Conservation & Single-Use SPT Resolve]
  │     • Enforces Separate Charges conservation, FX slippage <= 50 bps, reverse_transfer=true,
  │       and single-use /v1/shared_payment/granted_tokens/{id}/resolve
  │
  └─► [Gate 7: 17-Gateway CE 3.0 Dispute Bundle & 00:00 UTC 3-Way SFTP Reconciliation]
        • Seals 4-pillar CE 3.0 Merkle root and verifies SFTP + MPP Tempo + Metronome EOD balance
```

---

## 3. 14-Scenario Chaos Resilience Benchmark Summary (`R01`–`R14`)

| ID | Gate Tested | Chaos / Adversarial Fault Injected | AI-Native Result | Classic 3-Tier Result |
|---|---|---|---|---|
| `R01` | All 7 Gates | Golden end-to-end 7-gate checkout & CE 3.0 seal | **PASS** (`UNIFIED_PIPELINE_COMMITTED`) | PASS |
| `R02` | Gate 1 | Revoked Visa TAP / Stripe Directory key (`tap_kid_revoked_99`) | **PASS** (`GATE1_AGENT_DIRECTORY_KEY_REVOKED`) | FAIL |
| `R03` | Gate 1 | Principal scarcity quota exceeded (`principal_did` scalping) | **PASS** (`GATE1_PRINCIPAL_SCARCITY_QUOTA_EXCEEDED`) | FAIL |
| `R04` | Gate 1 | WebMCP cross-origin iframe tool invocation | **PASS** (`GATE1_WEBMCP_CROSS_ORIGIN_VIOLATION`) | FAIL |
| `R05` | Gate 2 | Corrupted UCP catalog shard (`sha-256` mismatch) | **PASS** (`GATE2_SHARD_DIGEST_MISMATCH`) | FAIL |
| `R06` | Gate 2 | Prompt-injected summary ($199) vs terms ($273) mismatch | **PASS** (`GATE2_SUMMARY_TERMS_AMOUNT_MISMATCH`) | FAIL |
| `R07` | Gate 3 | Silent `DDP` to `DAP` incoterm downgrade stripping $38 duty | **PASS** (`GATE3_INCOTERM_DOWNGRADE_FROM_DDP_FORBIDDEN`) | FAIL |
| `R08` | Gate 3 | WCO 6-digit `HS` code tariff reclassification (`847130` -> `392690`) | **PASS** (`GATE3_HS_CODE_SUBHEADING_MISMATCH`) | FAIL |
| `R09` | Gate 4 | 80k input tokens + `$0.30` card fee erodes `$2.00` order margin | **PASS** (`GATE4_COST_ENVELOPE_EXCEEDED`) | FAIL |
| `R10` | Gate 5 | GDS flight hold expires inside 15s safety buffer (`1170 > 1165`) | **PASS** (`GATE5_SAGA_HOLD_TTL_EXPIRED_OR_WITHIN_SAFETY_BUFFER`) | FAIL |
| `R11` | Gate 5 | Premature `capture_method="automatic"` on multi-leg itinerary | **PASS** (`GATE5_PREMATURE_AUTOMATIC_CAPTURE_FORBIDDEN:FLIGHT_GDS`) | FAIL |
| `R12` | Gate 6 | Partial refund without `reverse_transfer=true` | **PASS** (`GATE6_PARTIAL_REFUND_WITHOUT_REVERSE_TRANSFER_CAUSES_PLATFORM_DEFICIT`) | FAIL |
| `R13` | Gate 6 | Replayed single-use `spt_golden_01` resolve token | **PASS** (`GATE6_SPT_RESOLVE_REPLAY_BLOCKED`) | FAIL |
| `R14` | Gate 7 | SFTP vs bank payout EOD variance (`$250.00` vs `$264.84`) | **PASS** (`GATE7_UNEXPLAINED_PAYOUT_VARIANCE`) | FAIL |
