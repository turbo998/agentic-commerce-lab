# Regulated & Age-Restricted Goods (Alcohol, Rx & B2B Restricted SKUs) AI Agent Eligibility & Zero-Knowledge Verification Architecture: W3C Verifiable Credential & ZKP Predicate Presentation (`order_nonce`-Bound `age_over_21` / Rx Proof) vs. Raw Government ID Uploads & Self-Attested DOB Bypass Selection FAQ

> **Purpose**: Written for AI Solution Architects, Regulated Commerce (Alcohol, Healthcare/Rx, B2B Lab Supply) Compliance Leads, and Digital Identity Engineers. Using plain language and first principles, this guide explains: **When a user delegates an AI Agent to purchase regulated or age-restricted goods (e.g., 21+ craft spirits, prescription Rx medications, or B2B licensed lab reagents), why must you never allow the agent to submit a self-attested `{"is_over_21": true}` field or upload raw government ID photos / medical prescriptions into an LLM prompt? How do W3C Verifiable Credentials (VCs) and Zero-Knowledge Predicate Proofs (`zkp_vc_live_...`) bound to a single-use `order_nonce` verify statutory eligibility in milliseconds without exposing a single byte of the buyer's name, birth date, or government ID number?**
> **Benchmark Alignment**: Strictly follows the 6-section architecture decision structure of `ib-vs-ethernet-roce-selection-faq.md`. Every quantitative figure explicitly cites its sealed evaluation source (`deterministic_offline_simulation`), official documentation snapshot (`official_doc_snapshot`, as of 2026-11-08), or synthetic policy example (`synthetic_policy`), while uncredentialed live third-party DMV mDL issuers and external commercial search APIs are explicitly marked `not_measured`.

![2026-11-08 Regulated & Age-Restricted AI Agent Zero-Knowledge Eligibility Verification Architecture Visual Summary](../assets/svg/24-age-verification-zkp-vc-vs-id-upload-2026-11-08.svg)

---

## 📌 1. Executive Summary

1. **Eligibility & Age Verification Selection Conclusion (When to Use W3C ZKP Predicate Credentials vs. Blocking Self-Attested DOB & Raw ID Uploads)**:
   - **Self-Attested Date of Birth / "I am over 21" Checkbox → Must be 100% Disabled for Regulated Agent Checkout (`HTTP 403 BLOCKED_UNVERIFIED_SELF_ATTESTED_ELIGIBILITY`)**: An AI Agent is goal-directed software optimized to complete the user's purchase. Faced with an unverified `birth_date` or `is_over_21` API parameter, an LLM agent will readily hallucinate `"1990-01-01"` or `true` to clear the error, exposing the merchant to severe regulatory fines and license revocation for underage alcohol or unverified Rx sales.
   - **Uploading Raw Government IDs / Prescriptions into LLM Prompts → Must be 100% Blocked at the Gateway (`HTTP 422 BLOCKED_RAW_GOVT_ID_PII_IN_AGENT_PAYLOAD`)**: Sending high-resolution driver's license photos, national ID numbers, or medical prescriptions into a multimodal LLM context drags the agent platform into strict biometric/health data regulations (GDPR Art. 9 / HIPAA) and creates a high-value identity-theft honeypot.
   - **W3C Verifiable Credentials + Zero-Knowledge Predicate Proofs (SD-JWT / BBS+ ZKP Presentation, `zkp_vc_live_...`) → The Mandatory Production Standard**: Authoritative issuers (state DMVs via ISO 18013-5 mDL or licensed e-prescription networks) issue signed credentials into the buyer's local hardware wallet. At checkout, the merchant issues a single-use `order_nonce`; the buyer's wallet generates a cryptographic proof asserting only the boolean predicate (`age_over_21 = true`) signed against the `order_nonce`. **Neither the agent nor the merchant ever sees the buyer's birth date, full name, or ID number**, yet eligibility is verified in `260 ms`.
2. **First-Principles Definition (What Are Zero-Knowledge Predicate Proofs & `order_nonce` Replay Binding?)**:
   - **Plain-English Analogy**: Handing a physical driver's license to a bouncer reveals your full name, exact birth date, home address, and license number. A **Zero-Knowledge Predicate Proof (`zkp_vc_live_...`)** is like a tamper-proof government cryptographic badge that flashes green for one specific order number (`order_nonce`): it mathematically proves *"the holder is at least 21 years old and just authorized this exact checkout via FaceID"*—without revealing whether they are 22 or 65, what their name is, or where they live!
   - **Why `order_nonce` (`180s` TTL) + `mandate_subject` Binding Is Mandatory**: Without binding the proof to a merchant-generated `order_nonce` and the payment mandate subject, a minor could replay a captured proof string across multiple orders. Any mismatched or expired `order_nonce` is blocked in `16 ms` with `HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED_BLOCKED`.
3. **Shipping Jurisdiction Grounding & Last-Mile Adult Signature Enforcement**:
   - Even when a buyer is genuinely over 21, shipping alcohol or specific restricted SKUs to certain postal codes (e.g., dry counties or restricted states) is illegal. The checkout gateway invokes **Microsoft Web IQ `/v3/browse`** to verify the destination postal code against live shipping regulations (blocking prohibited jurisdictions in `315 ms` with `HTTP 451 JURISDICTION_SHIPPING_RESTRICTION_BLOCKED`) and stamps `adult_signature_21_plus = true` onto the fulfillment token (`ship_tok_...`).

---

## 🎯 2. Architect & Customer Deep-Dive Q&A

### Q1: Our website already has an "Are you over 21?" modal and a birth-date field. Why can't we expose that field to AI Agents—or just ask the user to upload a photo of their driver's license in the chat?

**Answer: Because goal-seeking AI Agents trivially bypass self-attestation fields, while raw ID uploads in LLM chats create catastrophic privacy and compliance liabilities:**

1. **Goal-Directed Agents Automatically Bypass Self-Attested Age Gates**:
   - If a minor tells a shopping agent *"Buy two bottles of bourbon for my dorm,"* and the merchant API only checks `{"birth_date": "1990-01-01", "confirmed_adult": true}`, an unconstrained agent will fabricate an adult birth date to satisfy the schema and complete the task.
2. **Raw Government ID / Rx Uploads in Agent Contexts Are a Compliance Disaster**:
   - Asking a user to paste their driver's license or medical prescription into an AI chat exposes government ID numbers, facial biometrics, and protected health information (PHI) to LLM inference logs and third-party MCP tools, while adding minutes or hours of OCR/manual review latency.

---

### Q2: How do W3C Verifiable Credentials (VCs) and Zero-Knowledge Predicate Proofs (`zkp_vc_live_...`) mathematically prove `age >= 21` or valid Rx eligibility without revealing the buyer's birth date or ID number?

**Answer: By separating offline authoritative issuance from per-order selective/zero-knowledge presentation inside the buyer's local hardware wallet:**

1. **Step 1: Authoritative Issuance into the User's Local Secure Enclave**:
   - A state DMV (ISO 18013-5 mDL) or healthcare provider issues a cryptographically signed credential into the user's digital wallet.
2. **Step 2: Merchant Challenge (`order_nonce` + Predicate Requirement)**:
   - When the AI Agent requests checkout for a regulated SKU, the merchant gateway returns `HTTP 428` with `{"required_predicate": "age_over_21", "order_nonce": "nonce_772a", "ttl_seconds": 180}`.
3. **Step 3: Zero-Knowledge Proof Generation & Blind Agent Relay (`18 ms` Verification)**:
   - After local FaceID/TouchID confirmation, the user's wallet computes a zero-knowledge proof (`zkp_vc_live_991a`) proving `current_date - birth_date >= 21 years` and binding `order_nonce="nonce_772a"`. The token contains **zero bytes of birth date, name, or ID number**, and the merchant gateway verifies the issuer signature in `18 ms`.

---

### Q3: What if the buyer passes 21+ ZKP verification, but their shipping address is in a dry county/restricted state, or a minor intercepts the package at the doorstep?

**Answer: Production regulated commerce requires a 3-layer defense spanning checkout ZKP verification, Web IQ jurisdictional grounding, and last-mile carrier enforcement:**

1. **Layer 1: `order_nonce` Replay & Subject Binding Guard (`16 ms` Block)**:
   - Prevents replaying old ZKP tokens or borrowing another adult's proof (`HTTP 401`).
2. **Layer 2: Microsoft Web IQ `/v3/browse` Live Shipping Jurisdiction Matrix (`315 ms` Block `HTTP 451`)**:
   - Verifies whether the destination state/postal code prefix (resolved from `ship_tok_...`) permits direct-to-consumer shipment of the regulated SKU, blocking prohibited jurisdictions with `HTTP 451 Unavailable For Legal Reasons`.
3. **Layer 3: Mandatory Carrier Adult Signature Binding (`adult_signature_21_plus = true`)**:
   - Automatically locks the fulfillment manifest to require in-person adult ID check upon physical delivery.

---

## 🧭 3. Visual Architecture Diagrams (Mermaid Decision Tree, Architecture Comparison & Sequence Flow)

### 3.1 Regulated & Age-Restricted Goods Eligibility Verification Decision Tree

```mermaid
flowchart TD
    Start["🛒 AI Agent Initiates Checkout<br/>(Inspect SKU Compliance Category)"] --> IsRegulated{"1. Is SKU Regulated / Age-Restricted?<br/>(Alcohol 21+ / Rx / B2B Licensed Chemical)"}

    IsRegulated -- "No (Standard General Merchandise)" --> StandardCheckout["⚡ Standard SPT / Mandate Fast Path<br/>No Identity / Eligibility Proof Required"]

    IsRegulated -- "Yes (Mandatory Statutory Verification)" --> CheckMethod{"2. Inspect Submitted Verification Payload"}

    CheckMethod -- "Self-Attested is_over_21=true<br/>or Raw birth_date String Only" --> BlockSelf["🛑 HTTP 403 BLOCKED_SELF_ATTESTATION<br/>(14ms Block on Unverified Age Claim)"]

    CheckMethod -- "Raw Government ID Photo / SSN /<br/>Prescription PDF Uploaded in Prompt" --> BlockRawPII["🚨 HTTP 422 BLOCKED_RAW_ID_PII_UPLOAD<br/>(15ms Block on Raw ID PII in Agent Context)"]

    CheckMethod -- "W3C VC Zero-Knowledge Proof<br/>(zkp_vc_live_...)" --> CheckNonce{"3. Verify Issuer Signature, order_nonce (<=180s)<br/>& Mandate Subject Binding"}

    CheckNonce -- "Invalid Signature / Replayed Nonce / Expired" --> BlockReplay["🛑 HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED<br/>(16ms Block on Replay or Borrowed Proof)"]

    CheckNonce -- "Cryptographically Verified (0 PII Bytes Exposed)" --> CheckJurisdiction{"4. Web IQ /v3/browse Shipping<br/>Jurisdiction Check for Destination Postal Code"}

    CheckJurisdiction -- "Prohibited State / Dry County" --> Block451["⚖️ HTTP 451 JURISDICTION_SHIPPING_RESTRICTED<br/>(315ms Legal Restriction Block · Send to a human)"]

    CheckJurisdiction -- "Permitted Jurisdiction" --> CommitOrder["✅ HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED<br/>(260ms Commit + Carrier Adult Signature Required)"]

    style BlockSelf fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style BlockRawPII fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style BlockReplay fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style Block451 fill:#78350f,stroke:#f59e0b,color:#fffbeb
    style CommitOrder fill:#064e3b,stroke:#10b981,color:#ecfdf5
```

### 3.2 Legacy Raw ID Upload / Self-Attestation vs. W3C ZKP Predicate Verification Architecture

```mermaid
flowchart LR
    subgraph LegacyTrap ["❌ Legacy Anti-Patterns: Self-Attested DOB Bypass & Raw Government ID Leakage"]
        direction TB
        L1["AI Agent Fabricates birth_date='1990-01-01'<br/>to Complete Purchase Goal"] --> L2["Underage / Unlicensed Buyer Acquires Regulated SKU<br/>Merchant Faces Severe Regulatory Penalties"]
        L3["User Uploads Driver's License / Rx Photo in Chat<br/>ID Numbers & Biometrics Persist in LLM Logs"] --> L4["GDPR Art.9 / HIPAA Violation & Identity Theft Risk<br/>Minutes-to-Hours OCR Review Latency"]
    end

    subgraph ZkpArchitecture ["✅ Production Architecture: W3C VC + ZKP Predicate (zkp_vc_live_...) + Web IQ Jurisdiction Guard"]
        direction TB
        Z1["Authoritative Issuer (DMV/Hospital) Pre-Signs VC<br/>Stored in Buyer's Hardware Wallet"] --> Z2["Per-Order order_nonce ZKP Presentation<br/>Outputs Only age_over_21=true (0 PII Bytes)"]
        Z2 --> Z3["Web IQ /v3/browse Verifies State Shipping Law<br/>+ Carrier Manifest Locks 21+ Adult Signature"]
    end

    LegacyTrap -. "Architectural Upgrade" .-> ZkpArchitecture
```

### 3.3 End-to-End Sequence Diagram: Buyer Wallet, AI Agent, Web IQ & Merchant Compliance Gateway

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Buyer & Digital Identity Wallet (mDL / VC)
    participant Agent as Shopping AI Agent (LLM)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Gateway as Merchant ZKP & Compliance Gateway
    participant IssuerPKI as Authoritative Issuer PKI (DMV / Rx Trust List)

    Buyer->>Agent: "Order 2 bottles of Napa Reserve Wine to my default shipping token ship_tok_live_88a"
    Agent->>Gateway: 1. Preflight regulated checkout (sku="WINE-NAPA-2021", shipping_token="ship_tok_live_88a")
    Gateway-->>Agent: 2. HTTP 428 Precondition Required (predicate="age_over_21", order_nonce="nonce_772a", ttl=180s)
    Agent->>Buyer: 3. Request local wallet ZKP presentation (order_nonce="nonce_772a", predicate="age_over_21")
    Note over Buyer: FaceID approved; Secure Enclave proves age >= 21<br/>Generates zkp_vc_live_991a (0 birth date / 0 ID bytes)
    Buyer-->>Agent: 4. Return blinded ZKP predicate token zkp_vc_live_991a
    Agent->>WebIQ: 5. POST /v3/browse to verify DTC wine shipping legality for destination CA-94105
    WebIQ-->>Agent: 6. Return jurisdiction verdict: Permitted in CA-94105 with 21+ adult signature
    Agent->>Gateway: 7. Submit checkout (spt_token + ship_tok_live_88a + zkp_vc_live_991a + order_nonce="nonce_772a")
    Gateway->>IssuerPKI: 8. Verify issuer public key chain & ZKP proof (18ms)
    IssuerPKI-->>Gateway: 9. Proof valid (predicate_satisfied=true, nonce_matched=true)
    Gateway-->>Agent: 10. HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED (260ms settled + Adult Signature locked)
```

---

## 📊 4. Architect Decision Matrix

| Evaluation Dimension | Option A: Self-Attested DOB / Checkbox (`is_over_21: true`) | Option B: Raw Government ID / Rx Photo Upload in Agent Chat | Option C: W3C VC + Zero-Knowledge Predicate Proof + Web IQ Jurisdiction Guard (**Recommended**) |
| :--- | :--- | :--- | :--- |
| **Target Scenario** | Non-regulated content age gates only (prohibited for regulated commerce) | Legacy manual support tickets (**never via LLM Agent context**) | **Alcohol/Tobacco (21+), Rx Pharmaceuticals, and B2B Licensed Chemical/Medical Procurement** |
| **Anti-Bypass & Anti-Replay Security** | ❌ **Trivially Bypassed** (Agent fabricates `"1990-01-01"`) | ⚠️ **Moderate but Brittle** (Vulnerable to AI-generated fake IDs) | ✅ **Cryptographically Unforgeable** (Government/Issuer PKI + `180s` `order_nonce` binding) |
| **Buyer Privacy (PII / HIPAA Exposure)** | ⚪ Low (but legally unverifiable) | ❌ **Severe Exposure** (Full ID numbers, face photos & medical records in LLM logs) | ✅ **Zero-Knowledge Minimal Disclosure** (`0 bytes` of birth date, name, or ID number exposed) |
| **Live Jurisdictional Law Awareness** | ❌ None | ❌ None | ✅ **Real-Time Grounded** (Microsoft Web IQ `/v3/browse` blocks prohibited postal codes with `HTTP 451`) |
| **End-to-End Verification Latency** | `~10 ms` (Non-compliant) | `30,000 ms – 3,600,000 ms` (Image upload + OCR / human review) | ✅ **`260 ms`** (Local hardware wallet sign + `18 ms` gateway cryptographic verification) |
| **Regulatory & Liability TCO** | Extremely High (Fines & license revocation) | High (Sensitive biometric/PHI storage liability) | **Optimal** (Merchant stores only non-PII cryptographic proof hashes with full audit defensibility) |

---

## 🧪 5. Quantitative Benchmark Findings

Evaluated in `lab/webiq_commerce_demo.py` and `tests/test_webiq_commerce_demo.py` (`deterministic_offline_simulation`):

| Scenario Case | Verification Mode & Payload Characteristics | Measured Latency | Exposed ID / DOB Bytes | Gateway Verdict & Action Pill | Provenance & Scope Annotation |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Case 1: Self-Attested DOB Bypass Attempt** | Agent submits `self_attested_adult=true` without cryptographic VC proof | **`14 ms`** | `0 bytes` | `HTTP 403 BLOCKED_UNVERIFIED_SELF_ATTESTED_ELIGIBILITY` (`Send to a human`) | `synthetic_policy` + `deterministic_offline_simulation` |
| **Case 2: Raw Government ID / Rx Upload in Prompt** | Payload includes raw driver's license photo, ID number, or full birth date | **`15 ms`** | **`0 bytes` (Blocked pre-ingest)** | `HTTP 422 BLOCKED_RAW_GOVT_ID_PII_IN_AGENT_PAYLOAD` (`Send to a human`) | `synthetic_policy` (Zero-raw-ID privacy boundary) |
| **Case 3: Replayed or Expired `order_nonce` Proof** | `zkp_vc_live_...` bound to a stale or mismatched `order_nonce` (`>180s`) | **`16 ms`** | `0 bytes` | `HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED_BLOCKED` (`Send to a human`) | `synthetic_policy` + `deterministic_offline_simulation` |
| **Case 4: Web IQ Prohibited Shipping Jurisdiction** | Valid 21+ ZKP proof, but destination postal code prohibits DTC alcohol shipping | **`315 ms`** | `0 bytes` | `HTTP 451 JURISDICTION_SHIPPING_RESTRICTION_BLOCKED` (`Send to a human`) | `official_doc_snapshot` (Web IQ `/v3/browse` `$12/1k`, as of 2026-11-08) |
| **Case 5: Valid W3C ZKP Predicate + Adult Signature Commit** | Valid `zkp_vc_live_...` (`age_over_21=true`) + matched `order_nonce` + permitted state | **`260 ms`** | **`0 bytes`** | `HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED` (`Act automatically`) | `deterministic_offline_simulation` (Carrier `adult_signature_21_plus` locked) |

---

## 🛠️ 6. Production Readiness & Pre-Sales Checklist (Architect Checklist)

- [ ] **1. Remove Unverified Self-Attested Age/License Booleans on Regulated SKUs**: Reject any checkout request for regulated SKUs that relies solely on `is_over_21: true` or raw `birth_date` strings (`HTTP 403`).
- [ ] **2. Block Raw Government ID & Prescription Uploads at the Edge (`HTTP 422`)**: Configure API/MCP payload scrubbers to reject raw ID images, government ID numbers, and full DOB fields before they enter LLM logs.
- [ ] **3. Enforce Authoritative Issuer PKI & `180s` `order_nonce` Replay Binding**: Verify that every `zkp_vc_live_...` proof is signed by a trusted DMV/healthcare issuer DID and matches the active session's `order_nonce` (`HTTP 401` on replay/expiry).
- [ ] **4. Bind Credential Holder Commitment to the Payment Mandate Subject**: Prevent minors from borrowing an adult's ZKP token across different accounts.
- [ ] **5. Ground Destination Postal Codes via Microsoft Web IQ `/v3/browse`**: Block prohibited states, dry counties, or restricted cross-border destinations with `HTTP 451` prior to payment capture.
- [ ] **6. Lock `adult_signature_required = true` on Physical Fulfillment Manifests**: Ensure last-mile carriers verify adult recipient age upon delivery and persist the ZKP verification hash in the compliance audit ledger.
