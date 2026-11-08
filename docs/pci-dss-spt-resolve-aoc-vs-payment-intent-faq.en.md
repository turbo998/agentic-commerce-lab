# PCI-DSS Scope Isolation & Multi-PSP Routing Architecture: Standard `PaymentIntent` SPT Consumption (`SAQ-A`) vs. External PSP SPT `Resolve` API (`PCI AoC` + RSA `encryption_block` Byte-Slice Wrapping & Mutual-Exclusivity Lock) Selection & First-Principles FAQ

> **Document Purpose**: Written for AI Solution Architects, payment orchestration architects, and enterprise security/compliance leaders (CISOs / QSAs), this guide uses plain language and first principles to explain: when an enterprise runs Multi-PSP Orchestration (e.g., routing European volume to Adyen, LATAM to dLocal, and US to Stripe) and wants to accept AI Agent orders carrying a **Stripe Shared Payment Token (`SPT`)**, **why 95% of merchants should consume SPTs directly via standard `PaymentIntent` (preserving the lightest `PCI SAQ-A` boundary), when it is permissible to call the SPT `Resolve` endpoint to extract underlying Network Tokens + Cryptograms for an external PSP, why a resolved SPT is permanently locked against `PaymentIntent` consumption (`HTTP 409` mutual-exclusivity lock), and how RSA `encryption_block` byte-slice wrapping (`start_index` / `end_index`) plus Microsoft Web IQ PSP status grounding eliminate raw credential exposure.**
>
> **Provenance & As-Of Scope Declaration**:
> - **`official_doc_snapshot` (`as_of: 2026-11-08`)**: Stripe Shared Payment Token (SPT v2) mutually exclusive consumption paths (`POST /v1/payment_intents` with `shared_payment_granted_token` vs. `POST /v1/shared_payment/granted_tokens/{id}/resolve`), the requirement to hold a verified **PCI-DSS Level 1 Attestation of Compliance (`PCI AoC`)** and a scoped Restricted API Key (`rk_live_...`) for production `Resolve` access, the strict **one-way Mutual-Exclusivity Lock** between `Resolve` and `PaymentIntent`, and in-flight RSA `encryption_certificate` + `encryption_block` (`start_index` / `end_index`) byte-slice wrapping are modeled from official specification snapshots as of `2026-11-08`.
> - **`synthetic_policy` (Reference Enterprise Security Guardrails)**: Blocking `Resolve` calls lacking a valid `PCI AoC` or using unscoped `sk_live_...` keys (`HTTP 403 pci_aoc_required_for_spt_resolve`) and pre-verifying external PSP operational status and certificate fingerprints via Microsoft Web IQ `/v3/browse` before invoking `Resolve` are explicitly labeled as **`synthetic_policy`** reference rules.
> - **`deterministic_offline_simulation` vs. `not_measured`**: Gateway latencies (`320 ms` / `385 ms`), raw card bytes exposed in application memory (`0 bytes`), and double-charge interception rates (`100%`) come from deterministic offline simulation in `lab/webiq_commerce_demo.py` (`33 passed`). Live third-party external PSP (Adyen / Braintree / Worldpay / Checkout.com) acquiring settlement latency and hardware HSM decryption latency are explicitly labeled **`not_measured`**.

![PCI-DSS Scope Isolation & Multi-PSP Routing: PaymentIntent vs. External PSP SPT Resolve Architecture Visual Summary](../assets/svg/14-pci-dss-spt-resolve-aoc-vs-pi-2026-11-08.svg)

---

## ① 📌 Executive Summary

1. **PCI Scope & Multi-PSP Routing Decision (When to Pick Standard `PaymentIntent` `SAQ-A` vs. External PSP SPT `Resolve` `PCI AoC`)**:
   - **Single-PSP or Stripe-Acquired Traffic (95% of AI Commerce & SaaS Workloads)**: **Always choose Standard `PaymentIntent` Consumption (`POST /v1/payment_intents` with `shared_payment_granted_token=spt_...`)** (`official_doc_snapshot`). Both the AI Agent and the merchant backend handle only the opaque `spt_...` token handle; the underlying Primary Account Number (`PAN`), EMVCo Network Token, and dynamic cryptogram never leave Stripe's PCI Level 1 vault. The merchant stays in the lightest **`PCI-DSS SAQ-A` / `SAQ-A-EP` compliance tier** (`0 bytes` of raw card data in merchant memory, `320 ms` simulated gateway latency, `deterministic_offline_simulation`).
   - **Large Multi-PSP Enterprises Routing Specific Geographies/Currencies to Non-Stripe Acquirers (Adyen / Worldpay / Braintree) Inside a Certified PCI Level 1 Vault**: **Choose the SPT `Resolve` External Routing Path (`POST /v1/shared_payment/granted_tokens/{id}/resolve`)** (`official_doc_snapshot`). The merchant must file a verified **`PCI-DSS Level 1 AoC` (Attestation of Compliance)** with Stripe and authenticate with a dedicated Restricted API Key (`rk_live_...`) scoped solely to `shared_payment_granted_tokens:resolve`. Standard application servers without `PCI AoC` or using unscoped `sk_live_...` keys are hard-blocked (`HTTP 403 pci_aoc_required_for_spt_resolve`, `synthetic_policy`).
2. **First Principles of the One-Way Mutual-Exclusivity Lock (Why Can a Resolved SPT Never Be Passed to `PaymentIntent`?)**:
   - In multi-PSP failover architectures, the most dangerous financial bug is **cross-PSP double charging**: a merchant router calls `Resolve` to extract the Network Token and sends it to External PSP B; PSP B's response times out over the network (even though the charge succeeded), and the merchant's retry logic falls back by passing the same `spt_...` to Stripe `PaymentIntent.create`, charging the buyer a second time.
   - To make cross-PSP double charging mathematically impossible, Stripe SPT v2 enforces a **strict One-Way Mutual-Exclusivity Lock** (`official_doc_snapshot`): an `spt_...` token can **either** be consumed by a Stripe `PaymentIntent` **or** resolved via `/resolve` for an external PSP—never both. Once `/resolve` succeeds on `spt_...`, any subsequent call to `PaymentIntent.create(shared_payment_granted_token=spt_...)` is rejected with **`HTTP 409 spt_already_resolved_for_external_psp`** (and vice versa: calling `/resolve` on a token already consumed by a `PaymentIntent` returns **`HTTP 409 spt_already_consumed_by_payment_intent`**), guaranteeing **`0.0%` cross-PSP double charges** (`deterministic_offline_simulation`).
3. **Zero Raw Memory Exposure via RSA `encryption_block` Byte-Slice Wrapping (`start_index` / `end_index`) & Web IQ Pre-Resolve Grounding**:
   - Even with a valid `PCI AoC`, deserializing raw JSON PANs or cryptograms in microservice memory risks catastrophic PCI data leaks via APM tracers or error logs.
   - **Architectural Golden Rule**: When calling `/resolve`, pass the target external PSP's (or enterprise HSM's) X.509 public key certificate (`encryption_certificate`) and the exact byte-slice coordinates (`encryption_block.start_index` / `end_index`) (`official_doc_snapshot`). Stripe encrypts the sensitive credential slice *inside* its PCI boundary before returning the payload (`0 bytes` of raw plaintext PAN in merchant memory). Furthermore, before invoking `/resolve` (before consuming the mutual-exclusivity lock), use **Microsoft Web IQ `/v3/browse`** to ground the external PSP's official status page and certificate rotation bulletin (`synthetic_policy`, `385 ms` end-to-end): if the external PSP is degraded, fail over to Stripe `PaymentIntent` *before* calling `/resolve`.

---

## ② 🎯 Customer & Architect Soul-Searching Q&A (FAQ-Driven)

### Q1: We already operate a Multi-PSP payment router (e.g., EU orders go to Adyen, US orders go to Stripe). When an AI Agent checks out with an `spt_...` token, can our regular checkout microservice simply call `Resolve` to grab the card number and forward it to Adyen?

**Plain-language answer: No! Unless the calling service runs inside an audited `PCI-DSS Level 1 AoC` Cardholder Data Environment (CDE), calling `Resolve` is strictly prohibited. The API will reject unauthorized calls, and touching raw card or network token bytes in a regular microservice contaminates your entire AI and application cluster with full PCI-DSS audit scope.**

Let's compare the two paths from first principles:

1. **Path A: Standard `PaymentIntent` Consumption (`SAQ-A` Zero-Contamination Boundary)**
   - When your backend calls `POST /v1/payment_intents` with `shared_payment_granted_token="spt_..."`:
     - Your application servers, AI Agent orchestrators, logs, and databases only ever see the `spt_...` handle;
     - The 16-digit PAN or EMVCo Network Token and one-time cryptogram never leave Stripe's hardware security modules (HSMs);
     - Your system remains eligible for the lightweight **`PCI-DSS SAQ-A` / `SAQ-A-EP` compliance posture**.
2. **Path B: External PSP `Resolve` Extraction (`PCI Level 1 AoC` CDE Enclave)**
   - When you call `POST /v1/shared_payment/granted_tokens/{id}/resolve` to route a charge to Adyen or Worldpay:
     - The endpoint returns **live charge-capable payment credentials** (`network_token` or `card.number`, `exp_month`, `exp_year`, and the dynamic transaction `cryptogram`) (`official_doc_snapshot`);
     - Every server, load balancer, or log collector touching those fields immediately enters your **Cardholder Data Environment (CDE)**;
     - Consequently, production `/resolve` access enforces three hard gates (`official_doc_snapshot` + `synthetic_policy`):
       1. Verified **`PCI-DSS Level 1 AoC` (Attestation of Compliance)** on file;
       2. A dedicated **Restricted API Key (`rk_live_...`)** granted only `shared_payment_granted_tokens:resolve` permission (standard `sk_live_...` keys are rejected);
       3. Execution strictly inside an isolated PCI Vault Enclave (calls from non-AoC services return **`HTTP 403 pci_aoc_required_for_spt_resolve`**).

---

### Q2: What is the SPT "One-Way Mutual-Exclusivity Lock"? If our Multi-PSP router calls `Resolve` to send a transaction to an external PSP, and that external PSP times out, can we fall back and pass the same `spt_...` to Stripe `PaymentIntent`?

**No—you can never pass an already-resolved `spt_...` back to `PaymentIntent`! Once `/resolve` succeeds, the `PaymentIntent` path for that token is permanently locked (`HTTP 409`).**

Why does the protocol enforce such an unforgiving lock? Consider what happens in a distributed payment router without it:

- **The "Timeout Double-Charge Nightmare" Without Mutual Exclusivity**:
  1. At `t = 0 ms`, the merchant router takes `spt_123`, calls `/resolve` to extract the Network Token + Cryptogram, and sends the charge request to External PSP B;
  2. At `t = 2,500 ms`, External PSP B actually succeeds in charging the cardholder `$500`, but the HTTP response drops due to a network blip;
  3. At `t = 2,600 ms`, the router's automatic fallback logic assumes the charge failed and passes the exact same `spt_123` to Stripe `POST /v1/payment_intents`;
  4. Result: The buyer's card is **double-charged `$1,000` across two separate acquirers**!

- **How Stripe SPT v2's One-Way Mutual-Exclusivity Lock Works (`official_doc_snapshot`)**:
  - Every `spt_...` token can transition into **at most one consumption mode**:
    - **Lock State 1 (`RESOLVED_EXTERNAL`)**: Once `/resolve` is called on `spt_...`, Stripe atomically marks `resolved_for_external_psp = true`. Any later attempt to pass `spt_...` into `PaymentIntent.create` is rejected with **`HTTP 409 spt_already_resolved_for_external_psp`**;
    - **Lock State 2 (`CONSUMED_STRIPE_PI`)**: Conversely, once `spt_...` is passed to `PaymentIntent.create`, any later attempt to call `/resolve` on that token is rejected with **`HTTP 409 spt_already_consumed_by_payment_intent`**.
  - **How do you safely fail over if an external PSP is down?**
    - **Pre-Resolve Health Gate**: Check external PSP health and ground its live status/certificate page via **Microsoft Web IQ `/v3/browse`** *before* calling `/resolve` (`synthetic_policy`). If External PSP B is degraded, route the untouched `spt_...` directly to Stripe `PaymentIntent` before the mutual-exclusivity lock is triggered!

---

### Q3: When we must call `Resolve` for an external PSP, how does RSA `encryption_block` byte-slice wrapping (`start_index` / `end_index`) work, and how does it keep `0 bytes` of plaintext card data out of our memory?

**Plain-language answer: Before Stripe sends the resolved credentials back to your PCI proxy, Stripe uses your external PSP's (or HSM's) RSA public key to encrypt the exact sensitive byte slice (`[start_index, end_index]`) inside Stripe's own vault. Your proxy acts purely as a "sealed-envelope courier" that doesn't even possess the private decryption key!**

Here is the three-step mechanism (`official_doc_snapshot` + `synthetic_policy`):

1. **Supply `encryption_certificate` and Byte-Slice Coordinates (`encryption_block`)**:
   - In the `POST /v1/shared_payment/granted_tokens/{id}/resolve` request, the caller provides:
     - `encryption_certificate`: The target external PSP's or enterprise HSM's PEM-encoded X.509 public certificate;
     - `encryption_block`: The byte-offset range to wrap, e.g., `{"start_index": 0, "end_index": 64}` (must satisfy `0 <= start_index < end_index <= payload_length`, otherwise the gateway rejects with `HTTP 400 invalid_encryption_block_slice`).
2. **In-Boundary Cryptographic Wrapping**:
   - Stripe serializes the credential structure inside its PCI Level 1 boundary and encrypts bytes `[start_index, end_index]` (covering the PAN/Network Token and Cryptogram) using the public key from `encryption_certificate`;
   - The HTTP response returned to the merchant's CDE proxy contains ciphertext for the sensitive slice, leaving **`0 bytes` of raw plaintext PAN exposed in merchant application memory** (`deterministic_offline_simulation`).
3. **Pre-Flight Certificate & Status Grounding via Microsoft Web IQ `/v3/browse`**:
   - To prevent encrypting a one-time SPT credential with a stale external PSP public key or sending it to an acquirer experiencing an outage, the router first calls **Microsoft Web IQ `/v3/browse`** against the external PSP's status and key-rotation bulletin (`synthetic_policy`), confirming `psp_status == "operational"` and `cert_fingerprint_matched == True` before executing `/resolve`.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + PCI Boundary Comparison + Sequence Diagram)

### Figure 1: `PaymentIntent` (`SAQ-A`) vs. External PSP SPT `Resolve` (`PCI AoC`) Selection Decision Tree (`flowchart TD`)

```mermaid
flowchart TD
    Start(["AI Agent Submits Checkout with spt_..."]) --> Q_Route{"Target Acquiring Route?"}

    Q_Route -- "Stripe Native Acquiring<br/>(95% Default Workloads)" --> PathA["Select: Standard PaymentIntent Path<br/>POST /v1/payment_intents<br/>shared_payment_granted_token = spt_..."]
    PathA --> CheckLockA{"Was spt_... Already Resolved?"}
    CheckLockA -- "No (Untouched Token)" --> ExecPI["Cleared Inside Stripe PCI Vault<br/>0 Raw Bytes in Merchant Memory · PCI SAQ-A (320 ms)"]
    CheckLockA -- "Yes (Already Resolved)" --> Err409A["HTTP 409 spt_already_resolved_for_external_psp<br/>Mutual-Exclusivity Lock Blocks Cross-PSP Double Charge"]

    Q_Route -- "External Third-Party PSP<br/>(Adyen / Worldpay / Braintree)" --> CheckHealth{"Pre-Resolve Gate: Web IQ /v3/browse<br/>External PSP Operational & Cert Matched?"}
    CheckHealth -- "External PSP Degraded / Cert Mismatch<br/>(Fail Over BEFORE Calling Resolve!)" --> PathA

    CheckHealth -- "External PSP Healthy" --> CheckAoC{"Compliance Gate: Valid PCI Level 1 AoC<br/>+ Scoped rk_live_... Key?"}
    CheckAoC -- "Missing AoC or Unscoped sk_live_..." --> Err403["HTTP 403 pci_aoc_required_for_spt_resolve<br/>Credential Export Blocked"]

    CheckAoC -- "AoC Verified (CDE Enclave)" --> CheckSlice{"Valid encryption_certificate +<br/>encryption_block [start_index, end_index]?"}
    CheckSlice -- "start_index >= end_index or Out of Bounds" --> Err400["HTTP 400 invalid_encryption_block_slice<br/>Malformed Byte-Slice Blocked"]
    CheckSlice -- "Valid Slice [0..64]" --> ExecResolve["Call POST .../granted_tokens/{id}/resolve<br/>Lock State = RESOLVED_EXTERNAL<br/>Forward RSA-Wrapped Ciphertext to External PSP (385 ms)"]

    style PathA fill:#dcfce7,stroke:#16a34a,stroke-width:2px
    style ExecPI fill:#dcfce7,stroke:#16a34a,stroke-width:2px
    style ExecResolve fill:#dbeafe,stroke:#2563eb,stroke-width:2px
    style Err409A fill:#fee2e2,stroke:#dc2626,stroke-width:2px
    style Err403 fill:#fee2e2,stroke:#dc2626,stroke-width:2px
    style Err400 fill:#fef3c7,stroke:#d97706,stroke-width:2px
```

---

### Figure 2: Legacy Unisolated Raw PAN Exposure vs. SPT v2 Dual-Track PCI Isolation (`flowchart LR`)

```mermaid
flowchart LR
    subgraph Legacy["❌ Anti-Pattern: Unisolated Raw Credential Export (Full-Stack PCI Contamination)"]
        direction TB
        L1["Standard Microservice Calls Resolve with sk_live_..."] --> L2["Plaintext JSON PAN / Cryptogram Enters App Memory"]
        L2 --> L3["APM/Logs Leak Raw PAN + Timeout Retry Calls PaymentIntent (Double Charge!)"]
    end

    subgraph Modern["✅ Best Practice: SPT v2 Dual-Track Isolation + RSA encryption_block Wrapping"]
        direction TB
        M1["Track A (Default): POST /v1/payment_intents (spt_...)<br/>Handle-Only · 0 Raw Bytes · Lightweight PCI SAQ-A"] --> M2["Track B (Multi-PSP): Web IQ Pre-Resolve Health Check<br/>Fail Over to Track A Before Consuming Resolve Lock"]
        M2 --> M3["Isolated CDE Proxy: PCI AoC + rk_live_... Key<br/>RSA encryption_block[0..64] Wrapping + HTTP 409 Mutual-Exclusivity Lock"]
    end

    style Legacy fill:#fff1f2,stroke:#e11d48,stroke-width:2px
    style Modern fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
```

---

### Figure 3: Multi-PSP Routing, Web IQ Status Grounding, RSA `encryption_block` Wrapping & Mutual-Exclusivity Lock Sequence (`sequenceDiagram`)

```mermaid
sequenceDiagram
    autonumber
    participant Agent as AI Shopping Agent
    participant Router as Multi-PSP Router (SAQ-A Boundary)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Vault as Merchant PCI Level 1 CDE Proxy
    participant Stripe as Stripe SPT v2 Gateway
    participant ExtPSP as External PSP (Adyen / Worldpay)

    Agent->>Router: 1. Submit Checkout (spt_eu_889, €420.00, target_psp=ExtPSP)
    Router->>WebIQ: 2. POST /v3/browse ground ExtPSP status page & RSA cert fingerprint
    WebIQ-->>Router: 3. Return psp_status="operational", cert_fingerprint_matched=true

    alt Case A: Pre-Resolve Check Detects ExtPSP Outage (Mutual-Exclusivity Lock Not Yet Consumed)
        Router->>Stripe: 4a. Lossless Failover -> POST /v1/payment_intents (shared_payment_granted_token=spt_eu_889)
        Stripe-->>Router: 4b. Lock State = CONSUMED_STRIPE_PI · Charge Settled Directly (320 ms)
    else Case B: ExtPSP Healthy + Valid PCI Level 1 AoC + Scoped rk_live_... Key
        Router->>Vault: 5a. Dispatch spt_eu_889 to Isolated CDE Proxy
        Vault->>Stripe: 5b. POST /v1/shared_payment/granted_tokens/spt_eu_889/resolve<br/>Header: Authorization Bearer rk_live_...<br/>Body: encryption_certificate + encryption_block{start_index:0, end_index:64}
        Stripe->>Stripe: 5c. Verify PCI AoC -> Lock spt_eu_889 = RESOLVED_EXTERNAL<br/>RSA-Encrypt Credential Byte Slice [0..64]
        Stripe-->>Vault: 5d. Return Wrapped Ciphertext (raw_pan_bytes_exposed = 0)
        Vault->>ExtPSP: 6a. Forward Wrapped Credential Payload for External Settlement (385 ms sandbox)
        Note over Router,Stripe: Defense Check: Any later attempt to pass spt_eu_889 to PaymentIntent.create is immediately blocked with HTTP 409 spt_already_resolved_for_external_psp!
    end
```

---

## ④ 📊 Architect Decision Matrix

| Evaluation Dimension | Option A: Standard `PaymentIntent` Consumption (Recommended Default) | Option B: External PSP SPT `Resolve` + RSA `encryption_block` Wrapping | Option C: External PSP SPT `Resolve` Unwrapped Plaintext JSON (High Risk) | Anti-Pattern: Uncertified `Resolve` or Post-Resolve `PaymentIntent` Retry |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Use Case** | **All B2C/B2B AI commerce & SaaS workloads cleared via Stripe acquiring (~95% of traffic)** | **Multi-PSP enterprises routing regional volume to Adyen/Worldpay with public-key encryption** | **Licensed Tier-1 institutions with dedicated hardware HSMs and closed CDE vaults** | Calling `Resolve` from standard app servers or retrying a resolved SPT on `PaymentIntent` |
| **PCI-DSS Compliance Requirement** | **`SAQ-A` / `SAQ-A-EP` (Lightest Tier)** (`official_doc_snapshot`) | **`PCI-DSS Level 1 AoC` (Verified on file with Stripe)** + ciphertext transit hygiene | **`PCI-DSS Level 1 AoC` (Full end-to-end CDE audit scope)** | ❌ **Severe Violation**: Blocked at API gate or contaminates entire microservice fleet |
| **API Key Privilege Isolation** | Standard or scoped `PaymentIntent` write key | **Dedicated Restricted Key `rk_live_...` (`shared_payment_granted_tokens:resolve` only)** | Dedicated `rk_live_...` + hardware IP allowlisting | ❌ Using unscoped `sk_live_...` keys capable of mass credential extraction if leaked |
| **Raw PAN Bytes in App Memory** | **`0 bytes`** (only `spt_...` handle seen) | **`0 bytes`** (`[start_index, end_index]` encrypted inside Stripe boundary) | **> 0 bytes (High Risk)**: Plaintext Network Token / PAN + Cryptogram in RAM | ❌ Plaintext PAN leaked into APM traces / crash dumps |
| **Failover & Double-Charge Protection** | Native Stripe `Idempotency-Key` protection | **Web IQ Pre-Resolve Failover (before lock)** + **Post-Resolve `HTTP 409` Mutual-Exclusivity Lock** | Relies on custom distributed locks; `HTTP 409` blocks PI fallback | ❌ Post-Resolve timeout retry hits `HTTP 409` or double-charges buyer |
| **End-to-End Gateway Latency** | **`320 ms`** (`deterministic_offline_simulation`) | **`385 ms`** (includes Web IQ PSP status check + RSA slice wrapping, `deterministic_offline_simulation`) | **`355 ms`** (sandbox gateway; live external acquirer latency is `not_measured`) | ❌ Fails with `HTTP 403` / `HTTP 409` |

---

## ⑤ 🧪 Quantitative Benchmark & 7-Card Core Findings

We evaluated **5 representative Multi-PSP routing and PCI compliance boundary scenarios** in our deterministic test suite (`lab/webiq_commerce_demo.py` and `tests/test_webiq_commerce_demo.py`):

| Case ID & Scenario | Target Route & PCI Posture (`has_pci_aoc` / `api_key_type`) | `encryption_block` Slice & Pre-Flight Status | Gateway Decision & HTTP Status | Raw PAN Bytes Exposed (`raw_pan_bytes`) | End-to-End Latency (`deterministic_offline_simulation`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1: Standard Stripe Native Acquiring via `PaymentIntent`** | `target_psp="stripe_native"` · No `PCI AoC` needed (`SAQ-A`) | Direct `PaymentIntent.create` without `Resolve` | ✅ **`Act automatically` (`CONSUMED_STRIPE_PI`, `HTTP 200`)** | **`0 bytes`** | **`320 ms`** |
| **Case 2: Certified Multi-PSP Enterprise Resolving SPT with RSA `encryption_block` for Adyen** | `target_psp="adyen_eu"` · `has_pci_aoc=True` · `rk_live_resolve_only` | Valid `encryption_certificate` + `slice=[0, 64]` + Web IQ confirms PSP healthy | ✅ **`Act automatically` (`RESOLVED_EXTERNAL_ENCRYPTED`, `HTTP 200`)** | **`0 bytes` (Ciphertext Transit)** | **`385 ms`** |
| **Case 3: Uncertified Service or Unscoped `sk_live_...` Key Attempting `Resolve`** | `target_psp="adyen_eu"` · `has_pci_aoc=False` or `sk_live_full` | Attempts to export underlying Network Token / PAN | 🛡️ **`Block` (`HTTP 403 pci_aoc_required_for_spt_resolve`)** | **`0 bytes` (Blocked)** | **`42 ms`** |
| **Case 4: Post-Resolve Timeout Retry Attempting to Pass Same `spt_...` to `PaymentIntent`** | `already_resolved_external=True` -> retries `stripe_native` `PaymentIntent` | Attempts cross-PSP double consumption of same `spt_...` | 🛡️ **`Block` (`HTTP 409 spt_already_resolved_for_external_psp`)** | **`0 bytes` (Double-Charge Blocked)** | **`38 ms`** |
| **Case 5: Pre-Resolve Web IQ `/v3/browse` Detects External PSP Outage & Fails Over to `PaymentIntent`** | `target_psp="worldpay_uk"` · Web IQ detects `psp_status="degraded"` | **Before calling `Resolve`** (lock untouched), routes to Stripe `PaymentIntent` | 🔄 **`Act automatically` (`PRE_RESOLVE_FAILOVER_TO_PI`, `HTTP 200`)** | **`0 bytes`** | **`360 ms`** |

> 💡 **7-Card Report Key Insights**:
> 1. **Why Pre-Resolve Health Grounding Is the Only Lossless Multi-PSP Failover Point**: Comparing Case 4 and Case 5 proves a critical architectural invariant—once `/resolve` is invoked, the one-way mutual-exclusivity lock is set (`already_resolved_external=True`), permanently barring `PaymentIntent` fallback (`HTTP 409`). By grounding the external PSP's live status and certificate fingerprint via **Microsoft Web IQ `/v3/browse`** *before* invoking `/resolve` (Case 5), the router can divert degraded third-party routes to Stripe `PaymentIntent` with `100%` order completion and zero double-charge risk.
> 2. **Live External Acquirer Boundary (`not_measured`)**: The `320 ms`–`385 ms` latencies above measure deterministic local gateway validation and RSA byte-slice wrapping (`deterministic_offline_simulation`); live production settlement round-trips to external acquirers (Adyen / Braintree / Worldpay) and hardware HSM decryption latency are strictly labeled **`not_measured`**.

---

## ⑥ 🛠️ Appendix: Production Launch & Presales Architect Checklist

When reviewing Agentic Commerce payment architectures for multi-PSP enterprises, global retailers, or regulated financial institutions, verify these 6 items:

- [ ] **1. Default to Standard `PaymentIntent` Consumption (`SAQ-A` Preservation)**: Ensure 100% of Stripe-acquired traffic consumes `spt_...` via `POST /v1/payment_intents` (`shared_payment_granted_token`), and never calls `/resolve` merely to inspect card metadata.
- [ ] **2. Enforce `PCI-DSS Level 1 AoC` & Scoped `rk_live_...` Keys for `/resolve`**: Confirm that any `/resolve` caller has a verified `PCI Level 1 AoC` on file with Stripe, runs inside an isolated CDE enclave, and authenticates exclusively with a Restricted API Key (`rk_live_...` scoped to `shared_payment_granted_tokens:resolve`), hard-blocking unscoped `sk_live_...` keys with `HTTP 403`.
- [ ] **3. Mandate RSA `encryption_block` Byte-Slice Wrapping (`0 bytes` Plaintext in RAM)**: Require every `/resolve` call to include the target PSP/HSM `encryption_certificate` and valid `encryption_block` coordinates (`0 <= start_index < end_index <= payload_length`) so raw PAN/Network Token/Cryptogram bytes never appear in plaintext in proxy memory.
- [ ] **4. Model `RESOLVED_EXTERNAL` and `CONSUMED_STRIPE_PI` as Mutually Exclusive Terminal States**: Ensure router retry logic never passes an `spt_...` in `RESOLVED_EXTERNAL` state back to `PaymentIntent.create` (and alerts immediately on `HTTP 409 spt_already_resolved_for_external_psp`).
- [ ] **5. Execute Multi-PSP Failover *Before* Calling `/resolve` via Web IQ Grounding**: Verify external PSP health and certificate fingerprints via **Microsoft Web IQ `/v3/browse`** *prior* to invoking `/resolve`, enabling lossless failover to Stripe `PaymentIntent` while the token is still untouched.
- [ ] **6. Maintain Strict Provenance Disclosure (`not_measured`)**: Present deterministic simulation results (`deterministic_offline_simulation`) alongside `official_doc_snapshot` protocol locks, while labeling uncredentialed third-party external PSP settlement and hardware HSM latencies as `not_measured`.
