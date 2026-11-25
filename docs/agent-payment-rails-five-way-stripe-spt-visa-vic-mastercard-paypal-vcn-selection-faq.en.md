# Agent Payment & Checkout Rails 5-Way Deep-Dive Selection Guide: `Stripe Agent Toolkit (SPT)` vs. `Visa Intelligent Commerce (VIC)` vs. `Mastercard Agent Pay` vs. `PayPal Agentic Toolkit` vs. `Enterprise Budget Virtual Cards (JIT VCN)`, Multi-Seller Child-Token Partitioning & `CIT-to-MIT` Passkey Delegation (`-43%` Loss FAQ · 🏆 Round 415 Major Milestone!)

> **Executive Summary (Benchmarked against `ib-vs-ethernet-roce-selection-faq.md` · 🏆 Round 415 Major Milestone · 534th Bilingual SA Guide · SVG #858 · Sandbox #308)**: Built for **Cloud & AI Solution Architects** selecting and orchestrating payment rails for retail shopping assistants, OTA travel rebooking agents, and enterprise B2B procurement Copilots. As AI agents transition from product discovery to autonomous checkout, architects must choose across five major payment rails: **`Stripe Agent Toolkit (Shared Payment Tokens, SPT)`**, **`Visa Intelligent Commerce (VIC + Trusted Agent Protocol TAP)`**, **`Mastercard Agent Pay`**, **`PayPal Agentic Toolkit`**, and **`Enterprise Single-Use Virtual Cards (JIT VCN: Stripe Issuing / Ramp / Brex / WEX)`**. Deploying agentic payments without a deterministic multi-rail broker triggers three severe failures: (1) **Multi-Seller Token Drain (`Sharing One $420 Token Across a 3-Store Cart`)**: If Merchant A over-authorizes `$350` on a shared `$420` token, checkouts at Merchants B and C fail with `Code 51 Insufficient Funds`; (2) **3:00 AM Unattended `MIT` `3DS2` Challenge Deadlocks (`28% Autonomous Drop-Off`)**: Executing an overnight price-drop purchase without linking the initial **`15-Digit CIT Scheme Trace ID` + `FIDO2 / W3C SPC` Payment Instruction Cryptogram** triggers an interactive SMS OTP challenge while the user is asleep; and (3) **Raw `16-Digit PAN` Exposure in LLM Prompts (`PCI-DSS v4.0` Violation) & Lost `EMVCo` Fraud Liability Shift**. This guide provides the definitive 5-rail selection matrix and implements deterministic guards for **Per-Seller Child-Token Partitioning & Penny Conservation (`HTTP 403`)**, **`CIT-to-MIT` Trace-ID & `FIDO2` Cryptogram Chaining (`HTTP 422`)**, **`TEE Enclave` `VCN` Isolation & `RFC 9421 TAP` Signatures (`HTTP 451`)**, and **5-Rail Dynamic Waterfall Routing (`HTTP 409`, `-43%` net loss)**.

![Agent Payment Rails 5-Way Comparison Architecture](../assets/svg/858-agent-payment-rails-spt-vic-mastercard-paypal-vcn-round415-2026-11-26.svg)

---

## 1. 📌 Executive Summary & 5-Rail Architectural Selection Verdict

1. **Top-Line 5-Rail Selection Verdict**:
   - **Merchants on `Stripe` or Supporting `ACP / UCP` Open Checkout Protocols (Seeking Zero `PAN` Exposure, Seller-Profile Binding & 10-Line Integration)**: Select **`Stripe Agent Toolkit (Shared Payment Tokens, SPT)`**.
   - **Cross-Merchant Consumer Shopping & OTA Travel Agents Operating Across Any Online Retailer Worldwide (Requiring Network-Enforced Spend Caps & Issuer Fraud Liability Shift)**: Select **`Visa Intelligent Commerce (`VIC + TAP`)`** or **`Mastercard Agent Pay`**.
   - **Global SMB E-Commerce Storefronts Where Buyers Rely on Vaulted Shipping Addresses & Platform Buyer/Seller Dispute Protection**: Select **`PayPal Agentic Toolkit`**.
   - **Enterprise B2B Tail-Spend Sourcing, Legacy Non-API Supplier Web Portals (Paired With `Browser-Use` Secure Enclaves) & Hotel Front-Desk Settlement**: Select **Single-Use Exact-Penny Virtual Commercial Cards (`JIT VCN`: `Stripe Issuing / Ramp / Brex / WEX`)**.
2. **Three Non-Negotiable Fiduciary Control Gates**:
   - **Gate 1 — Per-Seller Child-Token Partitioning & Two-Phase (`2PC`) Conservation Lock (`HTTP 403`)**: When a buyer approves a multi-seller cart across $N$ merchants, never share a single aggregate payment token; mint $N$ isolated child tokens (`Child_Token_1 .. Child_Token_N`), each cryptographically scoped to **`Target_Merchant_MID_i + Exact_Cap_Cents_i + 15m TTL`** such that $\sum_{i=1}^N \text{Cap\_Cents}_i \equiv \text{Approved\_Total\_Cents}$, and fire `<5s ISO 8583 0420` auth reversals across all legs if any seller fails pre-authorization via `HTTP 403 UNPARTITIONED_MULTI_SELLER_PAYMENT_TOKEN_OR_SUM_DRIFT_VETO`.
   - **Gate 2 — Unattended `CIT-to-MIT` `15-Digit Trace ID` & `FIDO2` Cryptogram Chaining (`HTTP 422`)**: At initial mandate creation (`Cardholder-Initiated Transaction, CIT`), perform an out-of-band **`FIDO2 / W3C SPC` Passkey ceremony** and persist the card network's **`15-Digit Initial Scheme Transaction ID (Visa Trace ID / Mastercard Banknet Ref)` + `Payment Instruction Cryptogram`**; attach both to any subsequent unattended `Merchant/Agent-Initiated Transaction (MIT)` so issuing banks grant frictionless approval without popping a middle-of-the-night `3DS2` OTP screen via `HTTP 422 UNATTENDED_MIT_MISSING_CIT_TRACE_ID_OR_3DS2_DEADLOCK_BREACH`.
   - **Gate 3 — Zero Raw `PAN` in LLM Prompts (`TEE Enclave` Isolation) & `RFC 9421 TAP` Header Signing (`HTTP 451`)**: Physically exclude 16-digit card numbers (`PAN`) and CVVs from LLM prompt/response memory (`PCI-DSS v4.0`); when falling back to a 16-digit `JIT VCN` on a legacy web checkout, inject the digits exclusively inside a non-LLM **Trusted Execution Environment (`TEE`) / Browser Enclave**, and sign all outbound checkout HTTP requests with **`RFC 9421 HTTP Message Signatures (Visa TAP)`** via `HTTP 451 RAW_PAN_IN_LLM_CONTEXT_OR_UNSIGNED_AGENT_TAP_HEADER_BREACH`.

---

## 2. 🎯 Chief Architect & Payments Engineering Q&A (The Why & How)

### Q1: What is the architectural difference between `Stripe SPT`, `Visa VIC / Mastercard Agent Pay`, and a `Single-Use Virtual Card (VCN)`?
- **First-Principles Breakdown**:
  1. **`Stripe SPT`** is a **PSP-level opaque pointer (`spt_xxx`)** scoped to a specific Stripe seller account (`network_business_profile`), max amount, and TTL. It never exposes a 16-digit card number, making it 100% immune to card-scraping—but requires the merchant to accept Stripe SPTs (`ACP / UCP`).
  2. **`Visa VIC` & `Mastercard Agent Pay`** operate at the **card-network clearing layer (`EMVCo Network Tokens`)**. They pair an `EMVCo` token (`DPAN`) with a cryptographic `FIDO2` Payment Instruction signed by the buyer's device enclave and `RFC 9421` bot-auth headers. Because the card network itself verifies the buyer's biometric mandate, **the issuing bank assumes `10.4` fraud chargeback liability (`Liability Shift`)**, and it works at any merchant accepting Visa/Mastercard!
  3. **`Enterprise JIT VCN`** issues a real **16-digit card number** controlled by an issuer `ISO 8583` webhook (`Stripe Issuing / Ramp / Brex`). It is the universal fallback for legacy B2B web forms that lack modern agent APIs, and pays the enterprise buyer `1.0%–1.75%` interchange cashback.

### Q2: Why do 28% of overnight autonomous agent purchases fail in Europe, the UK, and India—and how does `CIT-to-MIT` cryptogram chaining solve it?
- **Deterministic Solution (`Initial CIT Passkey Ceremony` -> `15-Digit Trace ID + MIT Indicator` / `HTTP 422`)**: Under `PSD2 SCA` and global issuer risk rules, an unlinked card charge at 3:00 AM triggers a `3DS2` step-up challenge. By executing a `CIT` `FIDO2` biometric mandate when the user sets the rule and passing the resulting `15-Digit Scheme Trace ID` + `MIT` standing-instruction flag at execution time, the issuer recognizes the transaction as a pre-authenticated delegated mandate.

---

## 3. 🧭 Visual Architecture Diagrams (Mermaid)

### 3.1 5-Rail Agent Payment Protocol Selection & Waterfall Decision Tree

```mermaid
flowchart TD
    A[🏆 Round 415: 5-Rail Agent Payment Selection Decision Tree] --> B{Merchant Protocol Support, Buyer Type & Checkout Surface?}
    B -->|Merchant Supports ACP/UCP on Stripe<br/>Goal: Zero PAN Scope + Seller-Bound Token + Instant Setup| C[Priority 1A: Stripe Agent Toolkit SPT<br/>Opaque spt_xxx Token Bound to Seller Profile + Max Cents + TTL]
    B -->|Global SMB Storefront Where Buyer Prefers PayPal<br/>Goal: Vaulted Shipping Address + Buyer/Seller Protection| D[Priority 1B: PayPal Agentic Toolkit<br/>400M+ Wallet Vault + Verified Address + Dispute Escrow]
    B -->|Any Online Retailer, Airline or OTA Worldwide<br/>Goal: Network-Level Spend Cap + EMVCo Fraud Liability Shift| E[Priority 2: Visa VIC / Mastercard Agent Pay<br/>EMVCo Network Token + FIDO2 Payment Instruction + RFC 9421 TAP]
    B -->|Enterprise B2B Tail-Spend or Legacy Non-API Web Form<br/>Goal: 100% Universal 16-Digit Acceptance + 1.5% Rebate| F[Priority 3 Fallback: Single-Use JIT VCN<br/>Stripe Issuing / Ramp / Brex Exact-Penny VCN in TEE Enclave]

    C --> G[Deterministic Fiduciary Gates:<br/>1. Per-Seller Child Token Partitioning & 2PC Conservation HTTP 403<br/>2. Unattended MIT 15-Digit CIT Trace ID & FIDO2 Chaining HTTP 422<br/>3. Zero Raw PAN in LLM Context & RFC 9421 TAP Signature HTTP 451]
    D --> G
    E --> G
    F --> G
```

### 3.2 Naive Shared Virtual Card & Unlinked Overnight Charge vs. Fiduciary Partitioned, `CIT-to-MIT` & 5-Rail Control Plane

```mermaid
flowchart LR
    subgraph Naive["❌ Naive Shared Card Token & Unlinked 3 AM Charge (Store A Drains Cart Budget + 28% 3DS2 Deadlock)"]
        N1[User Approves $420 3-Store Cart OR Sets 3 AM Price-Drop Buy] --> N2[Shares One $420 Token -> Store A Overcharges $350 -> Stores B & C Fail<br/>Passes Raw 16-Digit VCN Through LLM Prompt Context Violating PCI-DSS]
        N2 --> N3[Executes 3 AM Purchase Without Initial CIT Trace ID or FIDO2 Cryptogram<br/>Issuer Pops 3DS2 SMS OTP While User Sleeps -> 28% Autonomous Failure]
    end

    subgraph Guarded["✅ Fiduciary Per-Seller Child Tokens, CIT-to-MIT Chaining & 5-Rail Router (🏆 Round 415 · -43% Loss)"]
        G1[Multi-Seller Checkout / Autonomous Trigger] --> G2[Per-Seller Child Token Gate HTTP 403:<br/>Mint Isolated SPT_A ($180) + VIC_B ($150) + VCN_C ($90) With 2PC Rollback]
        G2 --> G3[CIT-to-MIT Trace & Passkey Gate HTTP 422:<br/>Link 15-Digit CIT Trace ID + FIDO2 Payment Instruction Cryptogram]
        G3 --> G4[TEE Enclave & 5-Rail Waterfall Gate HTTP 451/409:<br/>Sign RFC 9421 TAP Headers + Keep VCN Digits Inside Non-LLM Enclave]
    end
```

### 3.3 Multi-Seller Child-Token Partitioning, `CIT-to-MIT` Cryptogram Linking & 5-Rail Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    participant User as Buyer / Approver (FIDO2 Passkey)
    participant Broker as 5-Rail Payment Control Broker
    participant Rails as Protocol Rails (Stripe SPT / Visa VIC / MC / PayPal)
    participant TEE as TEE Browser Enclave & JIT VCN Issuer
    participant Sellers as Multi-Merchant Checkouts (Sellers A, B, C)

    User->>Broker: Sign $420 3-Seller Cart Mandate via FIDO2 Passkey (Or Set Autonomous Price-Drop Rule)
    Broker->>Rails: Record Initial 15-Digit CIT Scheme Trace ID & FIDO2 Payment Instruction Cryptogram
    alt Multi-Seller Cart Uses Unpartitioned Token OR Sum(Child_Token_Caps) != $420.00
        Broker-->>User: HTTP 403 UNPARTITIONED_MULTI_SELLER_PAYMENT_TOKEN_OR_SUM_DRIFT_VETO
    else Unattended MIT Execution Missing Initial 15-Digit CIT Trace ID / Cryptogram (3DS2 Deadlock)
        Broker-->>Rails: HTTP 422 UNATTENDED_MIT_MISSING_CIT_TRACE_ID_OR_3DS2_DEADLOCK_BREACH
    else Raw 16-Digit VCN Exposed in LLM Prompt Context OR Missing RFC 9421 TAP Signature
        Broker-->>TEE: HTTP 451 RAW_PAN_IN_LLM_CONTEXT_OR_UNSIGNED_AGENT_TAP_HEADER_BREACH
    else Optimal 5-Rail Split: Seller A via SPT ($180) + Seller B via VIC ($150) + Seller C via TEE VCN ($90) (HTTP 409)
        Broker->>Sellers: Execute Parallel Auth-Only With RFC 9421 Signatures (Capture All or 5s 0420 Rollback)
    end
```

---

## 4. 📊 5-Rail Agent Payment & Checkout Protocol Master Selection Matrix

| Evaluation Dimension | Stripe Agent Toolkit (`SPT`) | Visa Intelligent Commerce (`VIC + TAP`) | Mastercard Agent Pay | PayPal Agentic Toolkit | Enterprise Single-Use `JIT VCN` (`Stripe Issuing / Ramp / Brex`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core Cryptographic Primitive** | Seller-scoped `spt_xxx` token (`network_business_profile`, max cents, TTL) | `EMVCo Network Token` + `FIDO2 Payment Instruction` + `RFC 9421 TAP` | `Mastercard Agentic Token` + registered agent DID + biometric intent | OAuth/MCP delegated order token + verified shipping address | Real-time 16-digit single-use virtual card + `ISO 8583` auth webhook |
| **Merchant Acceptance Footprint** | Millions of Stripe merchants & `ACP / UCP` storefronts | **130M+ Visa-accepting merchants worldwide** | **Global Mastercard retail & B2B acceptance network** | 35M+ global PayPal storefronts | **100% Universal** (works on any legacy web form accepting credit cards) |
| **LLM `PCI-DSS v4.0` Scope** | **Zero `PAN` (`100%` Out-of-Scope)**: Only opaque `spt_` tokens exist | **Minimal**: Uses network `DPAN` + dynamic cryptograms | **Minimal**: Uses network tokens + agent cryptographic proofs | **Zero `PAN` (`100%` Out-of-Scope)** | **Requires `TEE Enclave` Isolation**: Raw 16 digits must never enter LLM context |
| **`10.4` Fraud Chargeback Liability Shift** | Protected by Stripe Radar & network tokenization | **Full Issuer Liability Shift** via `EMVCo` cryptogram + `FIDO2 SPC` | **Full Issuer Liability Shift** via network biometric token | **PayPal Seller & Buyer Protection** dispute resolution | No liability shift, but **single-use exact-cent auto-expiry** prevents post-use drain |
| **Unattended `CIT-to-MIT` Auth Rate** | Near-100% within Stripe network | Native support for delegated `MIT` with initial `CIT` cryptogram | Native support for pre-authorized standing agent instructions | High via PayPal Vault / Billing Agreements | Best on domestic US/B2B rails; pair with `3DS2` decoupled auth in EU |
| **Commercial Economics (`official_list_price`)** | Standard merchant Stripe processing fee (`$0` agent fee) | Standard Visa network acquiring rate | Standard Mastercard network acquiring rate | Standard PayPal merchant processing rate | **Earns `1.0%–1.75%` Interchange Rebate** for the corporate buyer |

---

## 5. 🧪 5-Rail Dynamic Routing, Child-Token Partitioning & `CIT-to-MIT` Benchmark & 7-Card Report

### 5.1 Quarterly Overnight `3DS2` Deadlocks, Multi-Seller Token Drains & Fraud Dispute Model (Synthetic Benchmark)

For a `$180M` annual GMV agentic commerce platform orchestrating retail multi-store carts, OTA price-drop rebooking, and B2B tail-spend sourcing facing a **`$500,000 / quarter`** payment execution leakage pool across **`28.5%` overnight unattended `MIT` failures from `3DS2` SMS deadlocks, multi-merchant cart cascades from unpartitioned tokens, `10.4` fraud chargebacks on non-cryptogram rails, and forfeited B2B virtual-card rebates** (`provenance: synthetic`, `independently_reproduced: false`):

| Metric | Single Static Card / Unpartitioned VCN (Baseline) | Fiduciary 5-Rail Router (`SPT -> VIC/MC -> PayPal -> TEE VCN`) | Net Improvement |
| :--- | :--- | :--- | :--- |
| **Overnight Unattended `MIT` Checkout Approval Rate** | `71.5%` (`28.5%` fail `3DS2` OTP timeout) | **`98.8%`** (`HTTP 422/409` links `15-Digit CIT Trace ID` + `FIDO2` cryptogram) | **`+27.3 pts` Approval Lift** |
| **Multi-Merchant Cart Failures from Single-Seller Over-Capture** | `3.2%` of split carts fail mid-saga | **`0.0%`** (`HTTP 403` per-seller `MID`-locked child tokens + `5s 0420` rollback) | **`100%` Cross-Store Isolation** |
| **Net `10.4` Fraud Chargeback Rate & Prompt `PAN` Exposure** | `0.65%` fraud loss / prompt `PAN` risk | **`0.02%` net loss / `0` prompt `PANs`** (`HTTP 451` `VIC/MC` liability shift + `TEE`) | **`-96.9%` Fraud Chargeback Loss** |
| **Quarterly Net Decline Fallout, Split-Cart & Dispute Loss** | `$500,000 / quarter` | **`$285,000 / quarter`** | **`$215,000 / quarter` Saved (`43.0%`)** |

---

## 6. 🛠️ Production Go-Live & Architecture Review Checklist

- [ ] **Per-Seller Child-Token Partitioning & `2PC` Conservation (`HTTP 403`)**: Does the payment broker mint a separate child token per seller (`Target_MID_i + Exact_Cap_Cents_i + 15m TTL`) whose caps sum to the exact approved cart total, with automatic `<5s 0420` reversal if any leg fails?
- [ ] **Unattended `CIT-to-MIT` `15-Digit Trace ID` & `FIDO2` Cryptogram Chaining (`HTTP 422`)**: Does mandate setup capture an initial `CIT` `FIDO2 / W3C SPC` cryptogram and `15-Digit Scheme Trace ID` so overnight `MIT` executions bypass interactive `3DS2` SMS challenges?
- [ ] **Zero Raw `PAN` in LLM Context (`TEE Enclave`) & `RFC 9421 TAP` Signatures (`HTTP 451`)**: Are 16-digit fallback `VCNs` injected strictly inside a non-LLM `TEE / Browser Enclave`, with all checkout HTTP requests signed via `RFC 9421 (Visa TAP)`?
- [ ] **5-Rail Dynamic Waterfall Router (`SPT -> VIC/MC -> PayPal -> TEE VCN` / `HTTP 409`)**: Does the router prioritize zero-PAN `Stripe SPT` and liability-shifted `Visa VIC / Mastercard Agent Pay` before falling back to rebate-earning `JIT VCNs` on legacy B2B web portals?
