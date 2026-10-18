# Cryptographic Agent Identity Attestation (RFC 9421 × Visa TAP × Stripe Agent Directory) and Anti-Scalping Scarcity Quotas

> **Verification Date**: `2026-10-19` (`Asia/Shanghai`)  
> **Primary Sources**: Visa Trusted Agent Protocol (TAP, RFC 9421 HTTP Message Signatures + Cloudflare Verified Bots), Stripe Agentic Commerce Suite (`agent_directory` + `WebMCP`), Google AP2 `IntentMandate` (`principal_did`), UCP `/.well-known/ucp` Signed Agent Requests (`RFC 9421` + `RFC 9530` `Content-Digest`)  
> **Executable Guard**: `lab/agent_identity_attestation_guard.py` (`python -m lab.agent_identity_attestation_guard`)

---

## 1. The WAF/CDN Paradox in Agentic Commerce

When a merchant publishes `/.well-known/ucp` and exposes high-velocity agent checkout endpoints (`/ucp/v1/checkout/sessions`) or browser-native `WebMCP` tools:
1. **Classic Bot Management Fails**: Traditional WAF heuristics (TLS JA3/JA4 fingerprints, residential IP reputation, Turnstile/CAPTCHA challenges, mouse-movement telemetry) block legitimate headless shopping agents (ChatGPT, Claude, Copilot, Perplexity, Visa TAP agents) while failing to stop residential-proxy scalping swarms.
2. **Sybil Fan-Out Scalping**: During high-scarcity drops (e.g., H200 GPU reservations, concert tickets, limited sneaker releases), a single human scalper can delegate 50 distinct registered agent instances across different cloud providers to bypass per-IP or per-agent rate limits.

An AI-Native Edge Gateway replaces heuristic bot scoring with **3-Layer Cryptographic Agent Attestation and Principal-Bound Scarcity Quotas**.

---

## 2. Layer 1: Mandatory RFC 9421 HTTP Message Signature Profile

Every mutating agent request MUST carry an RFC 9421 `Signature-Input` and `Signature` header together with an RFC 9530 `Content-Digest` header:

```text
Content-Digest: sha-256=:<base64(sha256(raw_body))>:
Signature-Input: sig1=("@method" "@authority" "@path" "content-digest" "x-ucp-idempotency-key" "x-ap2-mandate-digest");created=1792368000;expires=1792368030;nonce="nonce_stage7_01";keyid="tap_kid_visa_2026_10";alg="hmac-sha256"
```

### Deterministic Edge Gate Invariants (`lab/agent_identity_attestation_guard.py`)
1. **Mandatory Covered Components (`RFC9421_MISSING_COVERED_COMPONENTS`)**:
   - The signature base MUST cover all 6 components: `@method`, `@authority`, `@path`, `content-digest`, `x-ucp-idempotency-key`, and `x-ap2-mandate-digest`. Omitting `x-ap2-mandate-digest` or `content-digest` returns `HTTP 401`.
2. **Payload Digest Pinning (`RFC9530_CONTENT_DIGEST_MISMATCH`)**:
   - Recomputes `sha-256` over raw request bytes and verifies constant-time equality with `Content-Digest`. Any mid-flight proxy or prompt-injected payload mutation returns `HTTP 400`.
3. **Bounded Clock Window & Single-Use Nonce (`RFC9421_SIGNATURE_WINDOW_INVALID` / `RFC9421_NONCE_REPLAYED`)**:
   - Requires `0 < expires - created <= 60s`, `created <= now + 5s`, and `now < expires`.
   - Caches `nonce` in a distributed TTL store for at least `expires - created + 5s`. Replayed nonces return `HTTP 409`.

---

## 3. Layer 2: Joint Directory Key Liveness & WebMCP Same-Origin Binding

1. **Visa TAP / Stripe Agent Directory / Cloudflare Verified Bot Registry Lookup**:
   - Resolves `keyid` against the federated JWKS directory. Unknown keys (`AGENT_DIRECTORY_KEY_UNKNOWN`) or rotated/compromised keys (`status != "active"` -> `AGENT_DIRECTORY_KEY_REVOKED`) are rejected at the CDN edge (`HTTP 403`) before touching origin compute.
2. **WebMCP Same-Origin Enforcement (`WEBMCP_CROSS_ORIGIN_VIOLATION`)**:
   - When an agent invokes imperative or declarative `navigator.modelContext` (`WebMCP`) tools inside a user's browser session, the browser `Origin` header (`webmcp_origin`) MUST strictly equal `https://<@authority>`. Cross-origin iframe or third-party script invocations are blocked (`HTTP 403`).

---

## 4. Layer 3: Principal-Bound Anti-Sybil Scarcity Quota (`principal_did`)

To defeat multi-agent Sybil scalping without penalizing shared commercial agent platforms (where thousands of buyers share the same Visa TAP or OpenAI/Stripe agent `keyid`):
- Rate limits and scarcity quotas are keyed on the **cryptographically attested human or enterprise principal** `(principal_did, sku_id)` extracted from the verified AP2 `IntentMandate`, **never** on the shared platform IP or agent `keyid` alone.
- **Dual Scarcity Guard**:
  1. **Agent Fan-Out Cap (`SYBIL_SWARM_AGENT_FANOUT_EXCEEDED`)**: Caps the number of distinct `agent_instance_id`s a single `principal_did` can concurrently enlist for the same scarce SKU (`max_distinct_agents_per_principal = 3`).
  2. **Cumulative Principal Allocation Cap (`PRINCIPAL_SCARCITY_QUOTA_EXCEEDED`)**: Enforces `allocated_qty(principal_did, sku_id) + requested_qty <= max_qty_per_principal_per_sku` across all agent sessions combined (`HTTP 429`).
