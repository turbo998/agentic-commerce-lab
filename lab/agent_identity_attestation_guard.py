"""Stage 7: Cryptographic Agent Identity Attestation (RFC 9421 × Visa TAP × Stripe Agent Directory)
and Principal-Bound Anti-Scalping / Anti-Sybil Scarcity Quota Guard.

Covers:
1. RFC 9421 HTTP Message Signatures Mandatory Covered Components:
   - Requires `@method`, `@authority`, `@path`, `content-digest`, `x-ucp-idempotency-key`,
     `x-ap2-mandate-digest` in `Signature-Input`, plus `created`, `expires` (`expires - created <= 60s`),
     and single-use `nonce` anti-replay window.
   - Verifies RFC 9530 `Content-Digest: sha-256=:<base64>:` against the raw request payload.
2. Joint Directory & Key Liveness Attestation (Visa TAP / Cloudflare Verified Bots / Stripe Agent Directory):
   - Verifies that `agent_directory_kid` is registered and `status == "active"` (rejecting revoked,
     expired, or unverified scraper keys).
   - For browser-mediated `WebMCP` calls, enforces strict same-origin binding between `webmcp_origin`
     and `https://<@authority>`.
3. Principal-Bound Anti-Sybil Scarcity Quota (`principal_did` Token Bucket):
   - Prevents a single human buyer (`principal_did`) from spawning N distinct agent identities
     (`agent_id_1..N`) to bypass per-IP or per-agent rate limits during high-demand drops
     (GPU reservations, concert tickets, limited-edition launches).

Pure Python standard library (`hashlib`, `hmac`, `base64`, `dataclasses`); zero external dependencies.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any


REQUIRED_RFC9421_COMPONENTS: tuple[str, ...] = (
    "@method",
    "@authority",
    "@path",
    "content-digest",
    "x-ucp-idempotency-key",
    "x-ap2-mandate-digest",
)

MAX_SIGNATURE_TTL_SECONDS = 60
MAX_CLOCK_SKEW_SECONDS = 5


@dataclass(frozen=True)
class DirectoryKeyEntry:
    kid: str
    agent_provider: str  # e.g. "visa_tap", "stripe_agent_directory", "cloudflare_verified_bot"
    status: str  # "active" | "revoked" | "suspended"
    shared_verify_secret: str  # deterministic simulation secret for HMAC-SHA256 verification
    allowed_origins: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentHttpSignedRequest:
    method: str
    authority: str
    path: str
    body_bytes: bytes
    content_digest_header: str
    idempotency_key: str
    ap2_mandate_digest: str
    covered_components: tuple[str, ...]
    created_epoch: int
    expires_epoch: int
    nonce: str
    key_id: str
    signature_hex: str
    is_webmcp_browser_call: bool
    webmcp_origin: str | None
    principal_did: str
    agent_instance_id: str
    sku_id: str
    requested_qty: int


@dataclass(frozen=True)
class AgentAttestationQuotaResult:
    allowed: bool
    http_status: int
    decision_code: str
    reason: str
    principal_did: str
    sku_id: str
    principal_allocated_qty: int
    distinct_agents_for_principal: int
    canonical_signature_base_sha256: str


def compute_rfc9530_content_digest(body_bytes: bytes) -> str:
    digest_b64 = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode("ascii")
    return f"sha-256=:{digest_b64}:"


def build_rfc9421_signature_base(
    *,
    method: str,
    authority: str,
    path: str,
    content_digest_header: str,
    idempotency_key: str,
    ap2_mandate_digest: str,
    covered_components: tuple[str, ...],
    created_epoch: int,
    expires_epoch: int,
    nonce: str,
    key_id: str,
) -> str:
    component_map = {
        "@method": method.upper(),
        "@authority": authority.lower(),
        "@path": path,
        "content-digest": content_digest_header,
        "x-ucp-idempotency-key": idempotency_key,
        "x-ap2-mandate-digest": ap2_mandate_digest,
    }
    lines: list[str] = []
    for comp in covered_components:
        val = component_map.get(comp, "")
        lines.append(f'"{comp}": {val}')
    comp_list_str = " ".join(f'"{c}"' for c in covered_components)
    sig_params = (
        f'({comp_list_str});created={created_epoch};expires={expires_epoch}'
        f';nonce="{nonce}";keyid="{key_id}";alg="hmac-sha256"'
    )
    lines.append(f'"@signature-params": {sig_params}')
    return "\n".join(lines)


def sign_rfc9421_request(
    *,
    method: str,
    authority: str,
    path: str,
    body_bytes: bytes,
    idempotency_key: str,
    ap2_mandate_digest: str,
    covered_components: tuple[str, ...],
    created_epoch: int,
    expires_epoch: int,
    nonce: str,
    key_id: str,
    shared_secret: str,
) -> tuple[str, str]:
    content_digest = compute_rfc9530_content_digest(body_bytes)
    sig_base = build_rfc9421_signature_base(
        method=method,
        authority=authority,
        path=path,
        content_digest_header=content_digest,
        idempotency_key=idempotency_key,
        ap2_mandate_digest=ap2_mandate_digest,
        covered_components=covered_components,
        created_epoch=created_epoch,
        expires_epoch=expires_epoch,
        nonce=nonce,
        key_id=key_id,
    )
    sig_hex = hmac.new(
        shared_secret.encode("utf-8"),
        sig_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return content_digest, sig_hex


def verify_rfc9421_agent_attestation_and_quota(
    request: AgentHttpSignedRequest,
    *,
    now_epoch: int,
    directory_registry: dict[str, DirectoryKeyEntry],
    seen_nonces: set[str],
    principal_sku_ledger: dict[tuple[str, str], int],
    principal_agent_set: dict[tuple[str, str], set[str]],
    max_qty_per_principal_per_sku: int = 2,
    max_distinct_agents_per_principal: int = 3,
) -> AgentAttestationQuotaResult:
    """Verify RFC 9421 message signature, TAP/Stripe directory status, WebMCP origin, and Sybil quota."""
    sig_base = build_rfc9421_signature_base(
        method=request.method,
        authority=request.authority,
        path=request.path,
        content_digest_header=request.content_digest_header,
        idempotency_key=request.idempotency_key,
        ap2_mandate_digest=request.ap2_mandate_digest,
        covered_components=request.covered_components,
        created_epoch=request.created_epoch,
        expires_epoch=request.expires_epoch,
        nonce=request.nonce,
        key_id=request.key_id,
    )
    sig_base_sha256 = hashlib.sha256(sig_base.encode("utf-8")).hexdigest()
    ledger_key = (request.principal_did, request.sku_id)
    current_qty = principal_sku_ledger.get(ledger_key, 0)
    current_agents = principal_agent_set.get(ledger_key, set())

    # 1. Mandatory RFC 9421 covered components
    missing = [c for c in REQUIRED_RFC9421_COMPONENTS if c not in request.covered_components]
    if missing:
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=401,
            decision_code="RFC9421_MISSING_COVERED_COMPONENTS",
            reason=f"Missing mandatory RFC 9421 signed components: {','.join(missing)}",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # 2. Content-Digest integrity check
    expected_digest = compute_rfc9530_content_digest(request.body_bytes)
    if not hmac.compare_digest(expected_digest, request.content_digest_header):
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=400,
            decision_code="RFC9530_CONTENT_DIGEST_MISMATCH",
            reason="Request body does not match RFC 9530 Content-Digest header",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # 3. Timestamp window & Nonce replay check
    ttl = request.expires_epoch - request.created_epoch
    if (
        ttl <= 0
        or ttl > MAX_SIGNATURE_TTL_SECONDS
        or request.created_epoch > now_epoch + MAX_CLOCK_SKEW_SECONDS
        or now_epoch >= request.expires_epoch
    ):
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=401,
            decision_code="RFC9421_SIGNATURE_WINDOW_INVALID",
            reason=f"Signature window invalid or expired (created={request.created_epoch}, expires={request.expires_epoch}, now={now_epoch})",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    if request.nonce in seen_nonces:
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=409,
            decision_code="RFC9421_NONCE_REPLAYED",
            reason=f"Replay detected for single-use signature nonce '{request.nonce}'",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # 4. Visa TAP / Stripe Agent Directory key lookup & revocation check
    key_entry = directory_registry.get(request.key_id)
    if key_entry is None:
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=403,
            decision_code="AGENT_DIRECTORY_KEY_UNKNOWN",
            reason=f"Key ID '{request.key_id}' is not registered in Visa TAP / Stripe Agent Directory",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    if key_entry.status != "active":
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=403,
            decision_code="AGENT_DIRECTORY_KEY_REVOKED",
            reason=f"Directory key '{request.key_id}' status is '{key_entry.status}'",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # 5. Cryptographic signature verification
    expected_sig = hmac.new(
        key_entry.shared_verify_secret.encode("utf-8"),
        sig_base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, request.signature_hex):
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=401,
            decision_code="RFC9421_SIGNATURE_VERIFICATION_FAILED",
            reason="Cryptographic signature verification failed against directory public key",
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(current_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # 6. WebMCP Same-Origin Enforcement
    expected_origin = f"https://{request.authority.lower()}"
    if request.is_webmcp_browser_call:
        if not request.webmcp_origin or request.webmcp_origin.lower() != expected_origin:
            return AgentAttestationQuotaResult(
                allowed=False,
                http_status=403,
                decision_code="WEBMCP_CROSS_ORIGIN_VIOLATION",
                reason=f"WebMCP origin '{request.webmcp_origin}' does not match authority '{expected_origin}'",
                principal_did=request.principal_did,
                sku_id=request.sku_id,
                principal_allocated_qty=current_qty,
                distinct_agents_for_principal=len(current_agents),
                canonical_signature_base_sha256=sig_base_sha256,
            )

    # 7. Principal-Bound Anti-Sybil Scarcity Quota (`principal_did`)
    prospective_agents = set(current_agents)
    prospective_agents.add(request.agent_instance_id)
    if len(prospective_agents) > max_distinct_agents_per_principal:
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=429,
            decision_code="SYBIL_SWARM_AGENT_FANOUT_EXCEEDED",
            reason=(
                f"Principal '{request.principal_did}' spawned {len(prospective_agents)} distinct agents "
                f"for SKU '{request.sku_id}' (max {max_distinct_agents_per_principal})"
            ),
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(prospective_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    if request.requested_qty <= 0 or current_qty + request.requested_qty > max_qty_per_principal_per_sku:
        return AgentAttestationQuotaResult(
            allowed=False,
            http_status=429,
            decision_code="PRINCIPAL_SCARCITY_QUOTA_EXCEEDED",
            reason=(
                f"Principal '{request.principal_did}' requested {request.requested_qty} units of '{request.sku_id}' "
                f"(already allocated {current_qty}, max {max_qty_per_principal_per_sku})"
            ),
            principal_did=request.principal_did,
            sku_id=request.sku_id,
            principal_allocated_qty=current_qty,
            distinct_agents_for_principal=len(prospective_agents),
            canonical_signature_base_sha256=sig_base_sha256,
        )

    # Commit state
    seen_nonces.add(request.nonce)
    principal_sku_ledger[ledger_key] = current_qty + request.requested_qty
    principal_agent_set[ledger_key] = prospective_agents

    return AgentAttestationQuotaResult(
        allowed=True,
        http_status=200,
        decision_code="ATTESTED_AGENT_ADMITTED",
        reason="RFC 9421 signature, TAP/Stripe directory key, and principal scarcity quota verified",
        principal_did=request.principal_did,
        sku_id=request.sku_id,
        principal_allocated_qty=principal_sku_ledger[ledger_key],
        distinct_agents_for_principal=len(prospective_agents),
        canonical_signature_base_sha256=sig_base_sha256,
    )


def run_demo() -> dict[str, Any]:
    registry = {
        "tap_kid_visa_2026_10": DirectoryKeyEntry(
            kid="tap_kid_visa_2026_10",
            agent_provider="visa_tap",
            status="active",
            shared_verify_secret="tap_secret_active_key_01",
            allowed_origins=("https://shop.merchant.example",),
        ),
        "tap_kid_revoked_09": DirectoryKeyEntry(
            kid="tap_kid_revoked_09",
            agent_provider="stripe_agent_directory",
            status="revoked",
            shared_verify_secret="tap_secret_revoked_key_09",
        ),
    }
    seen_nonces: set[str] = set()
    principal_ledger: dict[tuple[str, str], int] = {}
    principal_agents: dict[tuple[str, str], set[str]] = {}

    body = b'{"sku":"gpu_h200_spot_block","qty":1}'
    digest, sig = sign_rfc9421_request(
        method="POST",
        authority="shop.merchant.example",
        path="/ucp/v1/checkout/sessions",
        body_bytes=body,
        idempotency_key="idem_stage7_01",
        ap2_mandate_digest="sha-256=:mandate_h200_01:",
        covered_components=REQUIRED_RFC9421_COMPONENTS,
        created_epoch=1792368000,
        expires_epoch=1792368030,
        nonce="nonce_stage7_01",
        key_id="tap_kid_visa_2026_10",
        shared_secret="tap_secret_active_key_01",
    )

    valid_req = AgentHttpSignedRequest(
        method="POST",
        authority="shop.merchant.example",
        path="/ucp/v1/checkout/sessions",
        body_bytes=body,
        content_digest_header=digest,
        idempotency_key="idem_stage7_01",
        ap2_mandate_digest="sha-256=:mandate_h200_01:",
        covered_components=REQUIRED_RFC9421_COMPONENTS,
        created_epoch=1792368000,
        expires_epoch=1792368030,
        nonce="nonce_stage7_01",
        key_id="tap_kid_visa_2026_10",
        signature_hex=sig,
        is_webmcp_browser_call=True,
        webmcp_origin="https://shop.merchant.example",
        principal_did="did:web:buyer.example:alice",
        agent_instance_id="agent_alice_01",
        sku_id="gpu_h200_spot_block",
        requested_qty=2,
    )
    ok_res = verify_rfc9421_agent_attestation_and_quota(
        valid_req,
        now_epoch=1792368010,
        directory_registry=registry,
        seen_nonces=seen_nonces,
        principal_sku_ledger=principal_ledger,
        principal_agent_set=principal_agents,
    )

    # Attempt Sybil scalping with a second agent instance exceeding Alice's 2-unit quota
    digest2, sig2 = sign_rfc9421_request(
        method="POST",
        authority="shop.merchant.example",
        path="/ucp/v1/checkout/sessions",
        body_bytes=body,
        idempotency_key="idem_stage7_02",
        ap2_mandate_digest="sha-256=:mandate_h200_02:",
        covered_components=REQUIRED_RFC9421_COMPONENTS,
        created_epoch=1792368005,
        expires_epoch=1792368035,
        nonce="nonce_stage7_02",
        key_id="tap_kid_visa_2026_10",
        shared_secret="tap_secret_active_key_01",
    )
    sybil_req = AgentHttpSignedRequest(
        method="POST",
        authority="shop.merchant.example",
        path="/ucp/v1/checkout/sessions",
        body_bytes=body,
        content_digest_header=digest2,
        idempotency_key="idem_stage7_02",
        ap2_mandate_digest="sha-256=:mandate_h200_02:",
        covered_components=REQUIRED_RFC9421_COMPONENTS,
        created_epoch=1792368005,
        expires_epoch=1792368035,
        nonce="nonce_stage7_02",
        key_id="tap_kid_visa_2026_10",
        signature_hex=sig2,
        is_webmcp_browser_call=False,
        webmcp_origin=None,
        principal_did="did:web:buyer.example:alice",
        agent_instance_id="agent_alice_sybil_02",
        sku_id="gpu_h200_spot_block",
        requested_qty=1,
    )
    sybil_res = verify_rfc9421_agent_attestation_and_quota(
        sybil_req,
        now_epoch=1792368012,
        directory_registry=registry,
        seen_nonces=seen_nonces,
        principal_sku_ledger=principal_ledger,
        principal_agent_set=principal_agents,
    )

    return {
        "stage": "stage7-agent-identity-attestation-guard",
        "attested_agent_admitted": ok_res.allowed,
        "sybil_over_quota_blocked": not sybil_res.allowed,
        "sybil_decision_code": sybil_res.decision_code,
        "principal_allocated_qty": ok_res.principal_allocated_qty,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 7 RFC 9421 Agent Identity Attestation & Anti-Scalping Guard."
    )
    parser.parse_args(argv)
    summary = run_demo()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
