# Stage 25: Autonomous EV ISO 15118 Plug-&-Charge / V2G Net-Metering, DePIN GPU Goodput SLA Escrow & Carbon Retirement Guard

**Verification Date:** `2026-10-19` (`Asia/Shanghai`)  
**Executable Modules:** `lab/energy_v2g_compute_carbon_guard.py` · `lab/vertical_domain_clearing_bench.py`  
**7-Card 4:5 Benchmark Reports:** `reports/agentic-commerce-vertical-domain-bench/index.html` & `reports/agentic-commerce-vertical-clearing-bench/index.html`  
**Unit Test Suite:** `tests/test_energy_v2g_compute_carbon_guard.py`

---

## 1. Architectural Problem Statement: M2M Energy, V2G Mobility & Green Compute Clearing

When autonomous fleet agents, microgrid brokers, and AI training orchestrators settle high-frequency machine-to-machine (`M2M`) energy and compute transactions, Classic 3-Tier Web architectures fail across three physical-to-financial boundaries:

1. **Unsigned EV Charger Telemetry & Battery Depletion**: Accepting unauthenticated JSON kWh readings from compromised charging stations enables phantom energy billing (`UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED`), while unguarded Vehicle-to-Grid (`V2G`) arbitrage can drain an EV below the driver's minimum departure State-of-Charge (`V2G_DISCHARGE_BELOW_SOC_FLOOR_BLOCKED`).
2. **DePIN GPU Spot Thermal Throttling & Uncheckpointed Preemption**: Decentralized GPU providers may advertise `1,000 TFLOPS` FP16 capacity while thermal-throttling or PCIe-bottlenecking effective training throughput (`Goodput`), or preempting spot nodes before a training checkpoint is committed to durable object storage.
3. **Carbon Credit Double-Counting (Greenwashing)**: Reusing a single retired Verra `VCS` or Gold Standard serial number across multiple green-compute invoices violates additionality and retirement uniqueness.

---

## 2. Formal Invariants & Deterministic Guard Mechanics

### 2.1 ISO 15118-20 Plug & Charge / OCMF & V2G Bidirectional Settlement (`evaluate_ev_iso15118_v2g_energy_settlement`)

- **Hardware OCMF Signature Gate**: Requires `iso15118_contract_cert_valid == True` and `ocmf_signature_valid == True`; otherwise blocks settlement (`UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED`).
- **Battery Reserve Floor**: For any V2G export ($E_{\text{dis}} > 0$), enforces $\text{SoC}_{\text{post}} \ge \text{SoC}_{\text{floor}}$ (`V2G_DISCHARGE_BELOW_SOC_FLOOR_BLOCKED`).
- **Bidirectional Net-Metering**:
  $$S_{\text{net}} = \text{round}(E_{\text{chg}} \cdot R_{\text{ToU}}) - \text{round}(E_{\text{dis}} \cdot R_{\text{FiT}})$$
  Settled with a canonical SHA-256 OCMF settlement digest (`V2G_BIDIRECTIONAL_NET_METER_SETTLED`).

### 2.2 DePIN GPU Goodput SLA Escrow & Carbon Retirement (`evaluate_gpu_spot_compute_sla_and_carbon_retirement`)

- **Carbon Uniqueness**: Rejects any compute settlement whose attached carbon serial is already retired (`CARBON_CREDIT_DOUBLE_COUNTING_RETIREMENT_BLOCKED`).
- **Uncheckpointed Preemption Void**: If a spot worker is preempted prior to durable checkpoint commit (`preempted_before_checkpoint == True`), voids 100% of provider payout and refunds the buyer (`UNCHECKPOINTED_PREEMPTION_CHARGE_VOIDED`).
- **Goodput SLA Penalty Slash**: When $\eta = \frac{G_{\text{measured}}}{G_{\text{promised}}} < 0.85$, slashes escrow by `sla_slash_bps` (`COMPUTE_GOODPUT_SLA_BREACH_ESCROW_SLASHED`).
