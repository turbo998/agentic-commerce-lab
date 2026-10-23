"""Stage 184 deterministic guardrails for 2026-10-23 overnight updates:

1. Google UCP PR #618 (`docs(ap2): clarify ES512 signature scope`, closes #571):
   - Separates AP2 Checkout JWS algorithm rules (`ap2.merchant_authorization`:
     `ES256`/`P-256`, `ES384`/`P-384`, `ES512`/`P-521`) from UCP HTTP Message Signatures.
   - Enforces `assert_alg_bound_to_key(public_key, alg)` per RFC 8725 §3.1:
     `kty == "EC"`, `crv` in `{"P-256", "P-384", "P-521"}`, `alg == curve_algorithms[crv]`,
     and when `public_key` includes `"alg"`, `public_key.alg == alg` (missing JWK `alg`
     alone is valid).
   - Enforces `header.alg in verifier_allowed_algorithms` (verifier's independently
     configured policy; rejects `Ed25519` or unsupported algorithms under AP2 v0.2).
   - Enforces RFC 7518 §3.4 fixed-width raw `R || S` signature byte lengths (`64`, `96`,
     `132` bytes for `ES256`, `ES384`, `ES512`) and rejects ASN.1 DER (`0x30`) signatures.
   - Ensures an unsupported `P-521` candidate in UCP HTTP Message Signatures fails only
     that candidate (`algorithm_unsupported`) and falls back to other valid candidates
     rather than rejecting the entire `/.well-known/ucp` `keys[]` set.

2. Model Context Protocol (MCP) Streamable HTTP Error Precedence (#3449), MRTR
   Namespaced `inputRequests`/`inputResponses` (#2919), and Client-Side RFC 8785
   Tool Definition Digest Pinning (#1766):
   - Version-first precedence with mismatch exception (#3449):
     * Missing/malformed `MCP-Protocol-Version` or mismatch with body
       `_meta["io.modelcontextprotocol/protocolVersion"]` -> `-32020 HeaderMismatch`.
     * Unsupported `MCP-Protocol-Version` -> `-32022 UnsupportedProtocolVersionError`
       with `data.supported` and `data.requested` BEFORE checking `Mcp-Method`/`Mcp-Name`
       or missing `_meta` fields.
     * Supported version with missing `Mcp-Method`/`Mcp-Name` -> `-32020 HeaderMismatch`.
   - MRTR namespaced interaction (#2919): allows reverse-DNS-namespaced methods alongside
     reserved `{"elicitation/create", "sampling/createMessage", "roots/list"}` only when
     client advertised the namespace, preserves `origin_request_id` on resume, and
     forbids `outcome == "expired"` from claiming a human `decided_by`.
   - Client-side tool definition pinning (#1766): SHA-256 over RFC 8785 JCS canonical
     form of `Tool` object with top-level `_meta` removed.

3. x402 `solidarity` Extension (`coinbase/x402` PR #419):
   - Evaluates owner-consented humanitarian share (`rate <= 0.01`, `amount == floor(purchase * rate)`
     capped by remaining monthly `cap`, allow-listed `fund`, `policy` JCS SHA-256, and
     separate scheme authorization).
   - Enforces never-in-the-way isolation: any invalid/failed solidarity share is skipped
     (`status="skipped"`, `reason`) without blocking or altering the main purchase settlement.
   - Computes unlinkable monthly `owner_pseudonym = sha256(policy || period)` and verifies
     RFC 6962 Merkle tree leaf (`0x00`) and internal node (`0x01`) hashes (including the
     official 8-leaf RFC 6962 test vector root `5dc9da79...04328`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


AP2_CURVE_ALGORITHMS = {
    "P-256": "ES256",
    "P-384": "ES384",
    "P-521": "ES512",
}
AP2_RAW_SIGNATURE_LENGTHS = {
    "ES256": 64,
    "ES384": 96,
    "ES512": 132,
}
STANDARD_MRTR_METHODS = frozenset({
    "elicitation/create",
    "sampling/createMessage",
    "roots/list",
})
NAMESPACED_MRTR_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+/[a-zA-Z0-9_./-]+$")
SHA256_POLICY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC6962_EIGHT_LEAF_REFERENCE_ROOT = (
    "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328"
)


def _jcs_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class UcpAp2Es512SignatureScopeGuardResult:
    allowed: bool
    reason_code: str
    bound_alg: str
    http_signature_verified_kid: str


def evaluate_ucp_ap2_es512_signature_scope_guard(
    *,
    jws_header_alg: str,
    jws_header_kid: str,
    verifier_allowed_algorithms: Sequence[str],
    published_keys: Sequence[Mapping[str, Any]],
    raw_signature_bytes_len: int,
    is_asn1_der_encoded: bool,
    http_candidate_kids: Sequence[str],
    http_supported_curves: Sequence[str] = ("P-256", "Ed25519"),
) -> UcpAp2Es512SignatureScopeGuardResult:
    """Validate UCP PR #618 AP2 Checkout JWS ES256/ES384/ES512 key binding & HTTP fallback."""
    if jws_header_alg not in AP2_RAW_SIGNATURE_LENGTHS:
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_ap2_jws_alg_not_permitted_by_ap2_v02",
            bound_alg="",
            http_signature_verified_kid="",
        )

    if jws_header_alg not in set(verifier_allowed_algorithms):
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_ap2_jws_alg_not_in_verifier_policy",
            bound_alg="",
            http_signature_verified_kid="",
        )

    selected_key: Mapping[str, Any] | None = None
    for key in published_keys:
        if str(key.get("kid", "")) == jws_header_kid:
            selected_key = key
            break

    if selected_key is None:
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_ap2_jws_kid_not_found",
            bound_alg="",
            http_signature_verified_kid="",
        )

    kty = str(selected_key.get("kty", ""))
    crv = str(selected_key.get("crv", ""))
    expected_alg = AP2_CURVE_ALGORITHMS.get(crv, "")
    jwk_alg = selected_key.get("alg")
    if (
        kty != "EC"
        or not expected_alg
        or jws_header_alg != expected_alg
        or (jwk_alg is not None and str(jwk_alg) != jws_header_alg)
    ):
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_ap2_jws_alg_curve_or_jwk_alg_mismatch",
            bound_alg="",
            http_signature_verified_kid="",
        )

    if is_asn1_der_encoded or raw_signature_bytes_len != AP2_RAW_SIGNATURE_LENGTHS[jws_header_alg]:
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_ap2_jws_signature_der_or_length_invalid",
            bound_alg=jws_header_alg,
            http_signature_verified_kid="",
        )

    key_map = {str(k.get("kid", "")): k for k in published_keys}
    supported_curve_set = set(http_supported_curves)
    verified_http_kid = ""
    for cand_kid in http_candidate_kids:
        cand_key = key_map.get(cand_kid)
        if cand_key is None:
            continue
        if str(cand_key.get("crv", "")) in supported_curve_set:
            verified_http_kid = cand_kid
            break

    if http_candidate_kids and not verified_http_kid:
        return UcpAp2Es512SignatureScopeGuardResult(
            allowed=False,
            reason_code="ucp_http_sig_no_supported_candidate_key",
            bound_alg=jws_header_alg,
            http_signature_verified_kid="",
        )

    return UcpAp2Es512SignatureScopeScopeSuccess(
        bound_alg=jws_header_alg,
        http_signature_verified_kid=verified_http_kid,
    )


def UcpAp2Es512SignatureScopeScopeSuccess(
    *,
    bound_alg: str,
    http_signature_verified_kid: str,
) -> UcpAp2Es512SignatureScopeGuardResult:
    return UcpAp2Es512SignatureScopeGuardResult(
        allowed=True,
        reason_code="ok",
        bound_alg=bound_alg,
        http_signature_verified_kid=http_signature_verified_kid,
    )


@dataclass(frozen=True)
class McpHttpPrecedenceMrtrToolPinGuardResult:
    allowed: bool
    reason_code: str
    http_jsonrpc_error_code: int
    supported_versions_disclosed: tuple[str, ...]
    computed_tool_jcs_digest: str


def compute_mcp_tool_jcs_digest(tool_definition: Mapping[str, Any]) -> str:
    """Compute SHA-256 over RFC 8785 JCS form of Tool with top-level `_meta` stripped (#1766)."""
    stripped = {k: v for k, v in tool_definition.items() if k != "_meta"}
    return "sha256:" + hashlib.sha256(_jcs_bytes(stripped)).hexdigest()


def evaluate_mcp_http_precedence_mrtr_tool_pin_guard(
    *,
    mcp_protocol_version_header: str | None,
    body_meta_protocol_version: str | None,
    server_supported_versions: Sequence[str],
    has_mcp_method_header: bool,
    has_mcp_name_header: bool,
    mrtr_method: str,
    client_advertised_namespaces: Sequence[str],
    origin_request_id: str,
    resume_request_id: str,
    approval_outcome: str,
    decided_by: str,
    tool_definition: Mapping[str, Any],
    pinned_tool_jcs_digest: str,
) -> McpHttpPrecedenceMrtrToolPinGuardResult:
    """Validate MCP #3449 HTTP version precedence, #2919 MRTR namespacing, and #1766 tool pinning."""
    supported_tuple = tuple(server_supported_versions)
    computed_digest = compute_mcp_tool_jcs_digest(tool_definition)

    # 1. Step 1 (#3449 mismatch exception): missing/malformed version header or body _meta disagreement -> -32020
    if not mcp_protocol_version_header or not mcp_protocol_version_header.strip():
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_http_missing_protocol_version_header_32020",
            http_jsonrpc_error_code=-32020,
            supported_versions_disclosed=(),
            computed_tool_jcs_digest=computed_digest,
        )

    if (
        body_meta_protocol_version is not None
        and body_meta_protocol_version != mcp_protocol_version_header
    ):
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_http_header_body_version_mismatch_32020",
            http_jsonrpc_error_code=-32020,
            supported_versions_disclosed=(),
            computed_tool_jcs_digest=computed_digest,
        )

    # 2. Step 2 (#3449 version-first rule): judge version BEFORE checking Mcp-Method / Mcp-Name -> -32022
    if mcp_protocol_version_header not in set(server_supported_versions):
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_http_unsupported_version_precedence_32022",
            http_jsonrpc_error_code=-32022,
            supported_versions_disclosed=supported_tuple,
            computed_tool_jcs_digest=computed_digest,
        )

    # 3. Step 3: supported version missing required modern headers -> -32020
    if not has_mcp_method_header or not has_mcp_name_header:
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_http_missing_required_header_on_supported_version_32020",
            http_jsonrpc_error_code=-32020,
            supported_versions_disclosed=(),
            computed_tool_jcs_digest=computed_digest,
        )

    # 4. MRTR (#2919): standard 3 methods or capability-negotiated reverse-DNS method
    if mrtr_method not in STANDARD_MRTR_METHODS:
        if not NAMESPACED_MRTR_RE.match(mrtr_method):
            return McpHttpPrecedenceMrtrToolPinGuardResult(
                allowed=False,
                reason_code="mcp_mrtr_method_not_standard_or_reverse_dns",
                http_jsonrpc_error_code=0,
                supported_versions_disclosed=supported_tuple,
                computed_tool_jcs_digest=computed_digest,
            )
        namespace = mrtr_method.split("/", 1)[0]
        if namespace not in set(client_advertised_namespaces):
            return McpHttpPrecedenceMrtrToolPinGuardResult(
                allowed=False,
                reason_code="mcp_mrtr_unadvertised_namespace_emitted",
                http_jsonrpc_error_code=0,
                supported_versions_disclosed=supported_tuple,
                computed_tool_jcs_digest=computed_digest,
            )

    if origin_request_id != resume_request_id:
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_mrtr_resume_origin_request_id_mismatch",
            http_jsonrpc_error_code=0,
            supported_versions_disclosed=supported_tuple,
            computed_tool_jcs_digest=computed_digest,
        )

    if approval_outcome == "expired" and decided_by != "expiry":
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_mrtr_expiry_masquerading_as_human_approval",
            http_jsonrpc_error_code=0,
            supported_versions_disclosed=supported_tuple,
            computed_tool_jcs_digest=computed_digest,
        )

    # 5. Client-side RFC 8785 JCS tool definition digest pin (#1766)
    if computed_digest != pinned_tool_jcs_digest:
        return McpHttpPrecedenceMrtrToolPinGuardResult(
            allowed=False,
            reason_code="mcp_tool_jcs_digest_pin_mismatch",
            http_jsonrpc_error_code=0,
            supported_versions_disclosed=supported_tuple,
            computed_tool_jcs_digest=computed_digest,
        )

    return McpHttpPrecedenceMrtrToolPinGuardResult(
        allowed=True,
        reason_code="ok",
        http_jsonrpc_error_code=0,
        supported_versions_disclosed=supported_tuple,
        computed_tool_jcs_digest=computed_digest,
    )


def compute_rfc6962_merkle_root(leaves: Sequence[bytes]) -> str:
    """Compute RFC 6962 §2.1 Merkle tree root without duplicating odd nodes."""
    if not leaves:
        return hashlib.sha256(b"").hexdigest()
    if len(leaves) == 1:
        return hashlib.sha256(b"\x00" + leaves[0]).hexdigest()
    # Largest power of two less than len(leaves)
    k = 1
    while (k << 1) < len(leaves):
        k <<= 1
    left = bytes.fromhex(compute_rfc6962_merkle_root(leaves[:k]))
    right = bytes.fromhex(compute_rfc6962_merkle_root(leaves[k:]))
    return hashlib.sha256(b"\x01" + left + right).hexdigest()


@dataclass(frozen=True)
class X402SolidarityExtensionGuardResult:
    allowed: bool
    reason_code: str
    purchase_settled: bool
    solidarity_status: str
    solidarity_skip_reason: str
    owner_pseudonym: str
    ledger_line: str
    rfc6962_merkle_root: str


def evaluate_x402_solidarity_extension_guard(
    *,
    purchase_amount_atomic: int,
    purchase_valid: bool,
    facilitator_supports_solidarity: bool,
    rate_str: str,
    share_amount_atomic: int,
    monthly_accumulated_atomic: int,
    monthly_cap_atomic: int,
    fund_caip10: str,
    allowlisted_funds: Sequence[str],
    policy_doc: Mapping[str, Any],
    claimed_policy_hash: str,
    period: str,
    auth_to_fund_valid: bool,
    payment_id: str,
    facilitator_id: str,
    purchase_Attempted_blocked_by_share_failure: bool = False,
    merkle_leaves_override: Sequence[bytes] | None = None,
) -> X402SolidarityExtensionGuardResult:
    """Validate coinbase/x402 PR #419 `solidarity` extension & RFC 6962 Merkle batching."""
    if not purchase_valid:
        return X402SolidarityExtensionGuardResult(
            allowed=False,
            reason_code="x402_purchase_invalid",
            purchase_settled=False,
            solidarity_status="skipped",
            solidarity_skip_reason="purchase-failed",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if purchase_Attempted_blocked_by_share_failure:
        return X402SolidarityExtensionGuardResult(
            allowed=False,
            reason_code="x402_solidarity_failure_must_not_block_purchase",
            purchase_settled=False,
            solidarity_status="skipped",
            solidarity_skip_reason="blocked-purchase-violation",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if not facilitator_supports_solidarity:
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="unsupported",
            solidarity_skip_reason="unsupported",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    rate = Decimal(rate_str)
    expected_policy_hash = "sha256:" + hashlib.sha256(_jcs_bytes(policy_doc)).hexdigest()
    if not SHA256_POLICY_RE.match(claimed_policy_hash) or claimed_policy_hash != expected_policy_hash:
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="bad-policy-hash",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if rate <= Decimal("0") or rate > Decimal("0.01"):
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="over-rate",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    floored_max_share = int((Decimal(purchase_amount_atomic) * rate).to_integral_value(rounding=ROUND_FLOOR))
    remaining_cap = max(0, monthly_cap_atomic - monthly_accumulated_atomic)
    allowed_share = min(floored_max_share, remaining_cap)

    if share_amount_atomic <= 0 or share_amount_atomic > floored_max_share:
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="over-rate",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if share_amount_atomic > remaining_cap:
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="cap-reached",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if fund_caip10 not in set(allowlisted_funds):
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="fund-not-allowed",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    if not auth_to_fund_valid:
        return X402SolidarityExtensionGuardResult(
            allowed=True,
            reason_code="ok",
            purchase_settled=True,
            solidarity_status="skipped",
            solidarity_skip_reason="bad-authorization",
            owner_pseudonym="",
            ledger_line="",
            rfc6962_merkle_root="",
        )

    owner_pseudonym = hashlib.sha256(f"{claimed_policy_hash}{period}".encode("utf-8")).hexdigest()
    ledger_line = f"{payment_id}|{facilitator_id}|{owner_pseudonym}|{allowed_share}"
    leaves = (
        list(merkle_leaves_override)
        if merkle_leaves_override is not None
        else [ledger_line.encode("utf-8")]
    )
    merkle_root = compute_rfc6962_merkle_root(leaves)

    return X402SolidarityExtensionGuardResult(
        allowed=True,
        reason_code="ok",
        purchase_settled=True,
        solidarity_status="recorded",
        solidarity_skip_reason="",
        owner_pseudonym=owner_pseudonym,
        ledger_line=ledger_line,
        rfc6962_merkle_root=merkle_root,
    )
