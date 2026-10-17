"""Offline verifier for Personal Agent Protocol (Poppy v0.1) and Sierra retail mutation guards.

Models three deterministic control planes without external dependencies, network calls, or funds:
1. Poppy v0.1 discovery (`/.well-known/poppy.json`) and mutual OAuth `poppy_domains` verification.
2. Channel-aware token verification: DPoP proof-of-possession (RFC 9449) on OpenAPI/Conversations/
   Operations vs resource-bound Bearer tokens (RFC 8707) on MCP endpoints, plus sign-in scope caps.
3. Sierra Defense-in-Depth + tau2/tau3-bench retail post-purchase order-mutation invariants combined
   with Poppy's `operations` extension (v1) two-phase propose/revise/confirm state machine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit


FORBIDDEN_DPOP_ALGS = frozenset({"none", "HS256", "HS384", "HS512"})
RESERVED_POPPY_SCOPES = frozenset({"poppy:read", "poppy:write"})
URL_SAFE_BASE64_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def _normalize_domain(host: str) -> str:
    """Normalize domain per Poppy v0.1 #37 (efc12168): compare ignoring case, and nothing else."""
    return host.lower().strip()


def _canonical_htu(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}"


def sha256_token(token: str) -> str:
    """Return hex SHA-256 digest used for deterministic DPoP `ath` simulation."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DiscoveryCheckResult:
    allowed: bool
    reason: str
    protocol_version: str | None = None
    organization_domain: str | None = None
    issuer: str | None = None


def verify_poppy_discovery(
    requested_well_known_url: str,
    poppy_doc: dict[str, Any],
    oauth_metadata: dict[str, Any],
    *,
    final_well_known_url: str | None = None,
) -> DiscoveryCheckResult:
    """Verify Poppy v0.1 discovery document and mutual OAuth server `poppy_domains` binding.

    Per commit efc12168 (#37), `organization.domain` MUST match the host that serves
    `poppy.json` after any redirects (`final_well_known_url` when redirected), compared
    ignoring case and nothing else (no `www.` stripping). Per commit 46dafba3 (#36),
    OAuth metadata `dpop_signing_alg_values_supported` (when present) MUST include `"ES256"`.
    """
    serving_url = final_well_known_url or requested_well_known_url
    parsed_req = urlsplit(serving_url)
    if parsed_req.scheme != "https" or not parsed_req.hostname:
        return DiscoveryCheckResult(False, "https_well_known_required")
    if parsed_req.path != "/.well-known/poppy.json":
        return DiscoveryCheckResult(False, "invalid_well_known_path")

    version = str(poppy_doc.get("protocol_version", ""))
    parts = version.split(".")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return DiscoveryCheckResult(False, "malformed_protocol_version", protocol_version=version)
    if parts[0] != "0":
        return DiscoveryCheckResult(False, "unsupported_major_version", protocol_version=version)

    org = poppy_doc.get("organization") or {}
    org_domain = _normalize_domain(str(org.get("domain", "")))
    if not org_domain or _normalize_domain(parsed_req.hostname) != org_domain:
        return DiscoveryCheckResult(
            False,
            "organization_domain_mismatch",
            protocol_version=version,
            organization_domain=org_domain or None,
        )

    auth = poppy_doc.get("auth") or {}
    issuer = str(auth.get("issuer", "")).strip()
    if not issuer or not issuer.startswith("https://"):
        return DiscoveryCheckResult(
            False,
            "invalid_auth_issuer",
            protocol_version=version,
            organization_domain=org_domain,
        )

    meta_issuer = str(oauth_metadata.get("issuer", "")).strip()
    if meta_issuer != issuer:
        return DiscoveryCheckResult(
            False,
            "oauth_issuer_mismatch",
            protocol_version=version,
            organization_domain=org_domain,
            issuer=issuer,
        )

    if "dpop_signing_alg_values_supported" in oauth_metadata:
        dpop_algs = oauth_metadata.get("dpop_signing_alg_values_supported")
        if not isinstance(dpop_algs, list) or "ES256" not in dpop_algs:
            return DiscoveryCheckResult(
                False,
                "dpop_es256_unsupported",
                protocol_version=version,
                organization_domain=org_domain,
                issuer=issuer,
            )

    poppy_domains = {
        _normalize_domain(str(d))
        for d in (oauth_metadata.get("poppy_domains") or [])
        if isinstance(d, str) and d.strip()
    }
    if org_domain not in poppy_domains:
        return DiscoveryCheckResult(
            False,
            "issuer_domain_unverified",
            protocol_version=version,
            organization_domain=org_domain,
            issuer=issuer,
        )

    return DiscoveryCheckResult(
        True,
        "verified",
        protocol_version=version,
        organization_domain=org_domain,
        issuer=issuer,
    )


def build_rfc8414_metadata_url(issuer: str) -> str:
    """Build RFC 8414 Section 3.1 OAuth Authorization Server Metadata URL for an `auth.issuer`.

    Per RFC 8414 §3.1 and Poppy v0.1 Section 3.2 (and multi-tenant hosted platform guidance),
    when an issuer identifier contains a path component (e.g., `https://auth.platform.example/outfitters`),
    the well-known suffix `/.well-known/oauth-authorization-server` MUST be inserted between the
    host component and the path component rather than appended to the end.
    """
    raw = issuer.strip()
    parsed = urlsplit(raw)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or raw.endswith("/")
    ):
        raise ValueError("invalid_oauth_issuer_identifier")
    clean_path = parsed.path.rstrip("/")
    return f"https://{parsed.netloc.lower()}/.well-known/oauth-authorization-server{clean_path}"


def verify_hosted_company_isolation(
    *,
    token_issuer: str,
    target_company_issuer: str,
    target_storefront_domain: str,
    target_oauth_metadata: dict[str, Any],
    agent_user_id: str,
    known_user_ids_by_issuer: dict[str, str],
) -> DiscoveryCheckResult:
    """Verify multi-tenant hosted commerce platform company isolation (Poppy v0.1 §3.2 & §4.2).

    A Company is identified by its full `auth.issuer` URL (including path), not by its hosting
    provider hostname. Storefronts that share the exact same `auth.issuer` and appear in its
    `poppy_domains` share one Company identity; storefronts with different `auth.issuer` paths
    on the same platform host are separate Companies and MUST NOT share Session/Account Tokens
    or Personal Agent opaque User IDs.
    """
    tok_iss = token_issuer.strip()
    tgt_iss = target_company_issuer.strip()
    if not tok_iss.startswith("https://") or not tgt_iss.startswith("https://"):
        return DiscoveryCheckResult(False, "invalid_auth_issuer")

    meta_iss = str(target_oauth_metadata.get("issuer", "")).strip()
    if meta_iss != tgt_iss:
        return DiscoveryCheckResult(False, "oauth_issuer_mismatch", issuer=tgt_iss)

    norm_domain = _normalize_domain(target_storefront_domain)
    poppy_domains = {
        _normalize_domain(str(d))
        for d in (target_oauth_metadata.get("poppy_domains") or [])
        if isinstance(d, str) and d.strip()
    }
    if norm_domain not in poppy_domains:
        return DiscoveryCheckResult(
            False,
            "issuer_domain_unverified",
            organization_domain=norm_domain,
            issuer=tgt_iss,
        )

    if tok_iss != tgt_iss:
        return DiscoveryCheckResult(
            False,
            "cross_company_token_rejected",
            organization_domain=norm_domain,
            issuer=tgt_iss,
        )

    for other_issuer, other_user_id in known_user_ids_by_issuer.items():
        if other_issuer.strip() != tgt_iss and other_user_id == agent_user_id:
            return DiscoveryCheckResult(
                False,
                "cross_company_user_id_reuse_forbidden",
                organization_domain=norm_domain,
                issuer=tgt_iss,
            )

    return DiscoveryCheckResult(
        True,
        "verified",
        organization_domain=norm_domain,
        issuer=tgt_iss,
    )


@dataclass(frozen=True)
class SessionToken:
    access_token: str
    token_type: str  # "DPoP" or "Bearer"
    session_id: str
    client_id: str
    user_id: str
    signed_in: bool
    account_id: str | None
    scopes: frozenset[str]
    sign_in_method: str | None = None  # "direct", "device", "mediated", or None
    jwk_thumbprint: str | None = None
    resource: str | None = None
    expires_at: int = 0


@dataclass(frozen=True)
class DPoPProof:
    jti: str
    htm: str
    htu: str
    iat: int
    ath: str
    jwk_thumbprint: str
    typ: str = "dpop+jwt"
    alg: str = "ES256"
    nonce: str | None = None
    has_private_key_material: bool = False


@dataclass(frozen=True)
class TokenCheckResult:
    allowed: bool
    error: str | None
    http_status: int


def verify_poppy_assertion_audience(
    aud: Any,
    *,
    auth_issuer: str,
) -> TokenCheckResult:
    """Verify Poppy v0.1 #50 (483c3cea): client and Session assertions MUST set `aud`
    to the Company's `auth.issuer` as a single string (never `token_endpoint` or an array).
    """
    expected = auth_issuer.strip()
    if type(aud) is not str or not expected or aud != expected:
        return TokenCheckResult(False, "invalid_client_or_session_assertion_aud", 400)
    return TokenCheckResult(True, None, 200)


@dataclass(frozen=True)
class SessionAssertionClaims:
    """Decoded claims from a Poppy Session assertion (`poppy-session+jwt`) or Browser assertion (`poppy-browser+jwt`)."""

    typ: str
    iss: str
    sub: str
    aud: Any
    iat: int
    exp: int
    jti: str
    session_id: str | None = None
    return_to: str | None = None


@dataclass(frozen=True)
class BrowserSessionResult:
    """Result of exchanging a Browser assertion at `web.browser_session_endpoint` (#35, Section 5)."""

    allowed: bool
    http_status: int
    error: str | None
    redirect_location: str | None = None
    cookie_attributes: dict[str, Any] | None = None


@dataclass(frozen=True)
class MCPProtectedResourceResult:
    """Result of verifying Poppy MCP server 401 challenge and RFC 9728 Protected Resource Metadata (#35)."""

    allowed: bool
    error: str | None
    resource: str | None = None


def verify_poppy_session_assertion(
    assertion: SessionAssertionClaims,
    *,
    auth_issuer: str,
    now: int,
    seen_jti: set[str],
    active_sessions: dict[str, tuple[str, str]] | None = None,
) -> TokenCheckResult:
    """Verify a Session assertion at the Token Endpoint (`kit/company/validate/checks/session.ts`, #35).

    Enforces:
    - `session.browser-assertion-rejected`: `typ: "poppy-browser+jwt"` presented at the token endpoint
      MUST be rejected with HTTP 400 `invalid_grant`.
    - `session.assertion-replay`: replayed `jti` or `len(jti) < 22` MUST be rejected with 400 `invalid_grant`.
    - `session.unknown-session`: unknown `session_id` on renewal MUST return 400 `invalid_session`.
    """
    if assertion.typ != "poppy-session+jwt":
        return TokenCheckResult(False, "invalid_grant", 400)
    aud_check = verify_poppy_assertion_audience(assertion.aud, auth_issuer=auth_issuer)
    if not aud_check.allowed:
        return TokenCheckResult(False, "invalid_grant", 400)
    if (
        not isinstance(assertion.jti, str)
        or len(assertion.jti) < 22
        or assertion.exp <= assertion.iat
        or not (assertion.iat <= now < assertion.exp)
    ):
        return TokenCheckResult(False, "invalid_grant", 400)
    if assertion.jti in seen_jti:
        return TokenCheckResult(False, "invalid_grant", 400)
    seen_jti.add(assertion.jti)

    if assertion.session_id is not None and active_sessions is not None:
        owner = active_sessions.get(assertion.session_id)
        if owner is None:
            return TokenCheckResult(False, "invalid_session", 400)
        if owner != (assertion.iss, assertion.sub):
            return TokenCheckResult(False, "invalid_grant", 400)

    return TokenCheckResult(True, None, 200)


def verify_poppy_browser_session_exchange(
    assertion: SessionAssertionClaims,
    *,
    browser_session_endpoint: str,
    organization_domain: str,
    now: int,
    seen_jti: set[str],
    active_sessions: dict[str, SessionToken],
    cookie_same_site: str = "Lax",
) -> BrowserSessionResult:
    """Verify a Browser assertion at `web.browser_session_endpoint` (`patterns/web-browsing.md`, #35).

    Enforces `typ == "poppy-browser+jwt"`, `aud == browser_session_endpoint`, `0 < exp - iat <= 60`,
    `len(jti) >= 22` with replay cache, active Session owned by `(iss, sub)`, URL-parsed `return_to`
    hostname matching `organization.domain` (never string-prefix matched), and `303 See Other` with
    `Secure; HttpOnly; SameSite=Lax|None` (never `SameSite=Strict`).
    """
    if assertion.typ != "poppy-browser+jwt":
        return BrowserSessionResult(False, 400, "invalid_browser_assertion_typ")
    if (
        type(assertion.aud) is not str
        or not browser_session_endpoint.strip()
        or _canonical_htu(assertion.aud) != _canonical_htu(browser_session_endpoint)
    ):
        return BrowserSessionResult(False, 400, "invalid_browser_assertion_aud")
    lifetime = assertion.exp - assertion.iat
    if lifetime <= 0 or lifetime > 60 or not (assertion.iat <= now < assertion.exp):
        return BrowserSessionResult(False, 400, "invalid_browser_assertion_lifetime")
    if not isinstance(assertion.jti, str) or len(assertion.jti) < 22 or assertion.jti in seen_jti:
        return BrowserSessionResult(False, 400, "browser_assertion_replayed_or_invalid_jti")
    seen_jti.add(assertion.jti)

    if not assertion.session_id or assertion.session_id not in active_sessions:
        return BrowserSessionResult(False, 400, "invalid_session")
    session = active_sessions[assertion.session_id]
    if now >= session.expires_at or (session.client_id, session.user_id) != (assertion.iss, assertion.sub):
        return BrowserSessionResult(False, 400, "session_owner_or_expiry_mismatch")

    if not assertion.return_to or not isinstance(assertion.return_to, str):
        return BrowserSessionResult(False, 400, "missing_return_to")
    parsed_ret = urlsplit(assertion.return_to)
    if (
        parsed_ret.scheme.lower() != "https"
        or not parsed_ret.hostname
        or _normalize_domain(parsed_ret.hostname) != _normalize_domain(organization_domain)
    ):
        return BrowserSessionResult(False, 400, "return_to_domain_mismatch")

    if cookie_same_site not in {"Lax", "None"}:
        return BrowserSessionResult(False, 400, "samesite_strict_breaks_cross_site_redirect")

    return BrowserSessionResult(
        True,
        303,
        None,
        redirect_location=assertion.return_to,
        cookie_attributes={
            "Secure": True,
            "HttpOnly": True,
            "SameSite": cookie_same_site,
            "session_id": session.session_id,
            "signed_in": session.signed_in,
            "account_id": session.account_id,
            "scopes": sorted(session.scopes),
        },
    )


def verify_poppy_mcp_protected_resource(
    *,
    mcp_server_url: str,
    auth_issuer: str,
    unauthenticated_http_status: int,
    www_authenticate_header: str,
    protected_resource_metadata: dict[str, Any],
) -> MCPProtectedResourceResult:
    """Verify Poppy MCP server 401 discovery challenge and RFC 9728 Protected Resource Metadata (#35)."""
    if unauthenticated_http_status != 401:
        return MCPProtectedResourceResult(False, "mcp_unauthenticated_must_return_401")
    header = (www_authenticate_header or "").strip()
    if not header.lower().startswith("bearer") or "resource_metadata=" not in header:
        return MCPProtectedResourceResult(False, "missing_resource_metadata_challenge")

    resource = str(protected_resource_metadata.get("resource", "")).strip()
    if not resource or _canonical_htu(resource) != _canonical_htu(mcp_server_url):
        return MCPProtectedResourceResult(False, "protected_resource_mismatch")

    auth_servers = protected_resource_metadata.get("authorization_servers")
    if not isinstance(auth_servers, list) or auth_issuer.strip() not in auth_servers:
        return MCPProtectedResourceResult(False, "auth_issuer_missing_from_authorization_servers")

    return MCPProtectedResourceResult(True, None, resource=resource)


def verify_poppy_request_token(
    *,
    token: SessionToken,
    channel: str,  # "token", "openapi", "conversation", "operations", or "mcp"
    http_method: str,
    target_url: str,
    now: int,
    poppy_auth_config: dict[str, Any],
    required_scopes: set[str] | None = None,
    dpop_proof: DPoPProof | None = None,
    seen_jti: set[str] | None = None,
    max_proof_age_seconds: int = 60,
    dpop_signing_algs_supported: set[str] | None = None,
    expected_dpop_nonce: str | None = None,
) -> TokenCheckResult:
    """Verify Poppy v0.1 Session Token transport (DPoP vs MCP Bearer) and sign-in scope caps."""
    if now >= token.expires_at:
        return TokenCheckResult(False, "invalid_token", 401)

    # Check sign-in method scope ceiling declared in poppy.json `auth`
    if any(s.startswith("poppy:") and s not in RESERVED_POPPY_SCOPES for s in token.scopes):
        return TokenCheckResult(False, "invalid_scope", 403)
    if token.signed_in:
        if not token.sign_in_method or token.sign_in_method not in {"direct", "device", "mediated"}:
            return TokenCheckResult(False, "invalid_grant", 401)
        method_cfg = poppy_auth_config.get(token.sign_in_method) or {}
        allowed_method_scopes = set(method_cfg.get("scopes") or [])
        if not token.scopes.issubset(allowed_method_scopes):
            return TokenCheckResult(False, "invalid_scope", 403)
    elif token.scopes:
        return TokenCheckResult(False, "invalid_token", 401)

    if channel == "mcp":
        if token.token_type != "Bearer":
            return TokenCheckResult(False, "bearer_required_for_mcp", 401)
        if not token.resource or _canonical_htu(token.resource) != _canonical_htu(target_url):
            return TokenCheckResult(False, "resource_mismatch", 401)
    elif channel in {"token", "openapi", "conversation", "operations"}:
        # Per #36 (46dafba3): DPoP errors return 400 at token endpoint and 401 at APIs/conversations
        dpop_err_status = 400 if channel == "token" else 401
        supported_algs = dpop_signing_algs_supported or {"ES256"}
        if token.token_type != "DPoP":
            return TokenCheckResult(False, "dpop_required", dpop_err_status)
        if dpop_proof is None:
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if (
            dpop_proof.typ.lower() != "dpop+jwt"
            or dpop_proof.alg in FORBIDDEN_DPOP_ALGS
            or dpop_proof.alg not in supported_algs
            or dpop_proof.has_private_key_material
        ):
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if not token.jwk_thumbprint or dpop_proof.jwk_thumbprint != token.jwk_thumbprint:
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if dpop_proof.htm.upper() != http_method.upper():
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if _canonical_htu(dpop_proof.htu) != _canonical_htu(target_url):
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if abs(now - dpop_proof.iat) > max_proof_age_seconds:
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if channel != "token" and dpop_proof.ath != sha256_token(token.access_token):
            return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
        if expected_dpop_nonce is not None and dpop_proof.nonce != expected_dpop_nonce:
            return TokenCheckResult(False, "use_dpop_nonce", dpop_err_status)
        if seen_jti is not None:
            if dpop_proof.jti in seen_jti:
                return TokenCheckResult(False, "invalid_dpop_proof", dpop_err_status)
            seen_jti.add(dpop_proof.jti)
    else:
        return TokenCheckResult(False, "unsupported_channel", 400)

    needed = required_scopes or set()
    if needed and not token.signed_in:
        return TokenCheckResult(False, "sign_in_required", 401)
    if not needed.issubset(token.scopes):
        return TokenCheckResult(False, "insufficient_scope", 403)

    return TokenCheckResult(True, None, 200)


@dataclass
class CatalogVariant:
    item_id: str
    product_id: str
    name: str
    price_cents: int
    available_stock: int


@dataclass
class PaymentInstrument:
    payment_method_id: str
    kind: str  # "card", "gift_card", "paypal"
    balance_cents: int = 0


@dataclass
class RetailOrder:
    order_id: str
    customer_id: str
    status: str  # "pending", "pending (items modified)", "delivered", "cancelled"
    items: dict[str, str]  # line_key -> item_id
    original_payment_method_id: str
    exchanged_items: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StandingPermission:
    company_domain: str
    account_id: str
    allowed_actions: frozenset[str]
    max_price_difference_cents: int
    expires_at: int


@dataclass
class OperationRecord:
    operation_id: str
    session_id: str
    client_id: str
    user_id: str
    account_id: str
    revision: int
    state: str  # "proposed", "succeeded", "cancelled", "expired"
    summary: str
    terms: dict[str, Any]
    expires_at: int
    user_approval_required: bool
    confirmation: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    code: str
    http_status: int
    operation: dict[str, Any] | None = None


def verify_cross_company_content_boundary(
    *,
    source_company_domain: str,
    target_company_domain: str,
    triggered_by_company_content: bool,
    explicit_user_target_domains: set[str],
) -> GuardDecision:
    """Enforce Poppy v0.1 Section 8.1 (#51, e910c866): Company content is untrusted data.

    A Personal Agent MUST NOT act at Company B or send it data because Company A's
    content (messages, tool descriptions/results, web pages, operation summaries) asked it to.
    """
    src = _normalize_domain(source_company_domain)
    dst = _normalize_domain(target_company_domain)
    allowed_targets = {_normalize_domain(d) for d in explicit_user_target_domains}
    if triggered_by_company_content and src != dst and dst not in allowed_targets:
        return GuardDecision(False, "cross_company_prompt_injection_blocked", 403)
    return GuardDecision(True, "allowed", 200)


class RetailOrderMutationGuard:
    """Combines Sierra Defense-in-Depth / tau3-bench retail rules with Poppy `operations` v1."""

    def __init__(
        self,
        *,
        company_domain: str,
        catalog: dict[str, CatalogVariant],
        orders: dict[str, RetailOrder],
        payment_methods: dict[str, dict[str, PaymentInstrument]],
    ) -> None:
        self.company_domain = company_domain
        self.catalog = catalog
        self.orders = orders
        self.payment_methods = payment_methods
        self.session_accounts: dict[str, str] = {}
        self.signed_out_sessions: set[str] = set()
        self.revoked_sessions: set[str] = set()
        self.operations: dict[str, OperationRecord] = {}
        self._op_seq = 0

    def sign_out_session(self, session_id: str, *, revoked: bool = False) -> None:
        """Sign out a Session while keeping its persistent account binding (#41, #49, #53)."""
        self.signed_out_sessions.add(session_id)
        if revoked:
            self.revoked_sessions.add(session_id)

    def authenticate_session_account(
        self,
        *,
        session_id: str,
        account_id: str,
        sign_in_method: str,
        stored_credentials_used: bool = False,
        user_initiated: bool = True,
    ) -> GuardDecision:
        """Enforce persistent Session-to-account binding (#41, #49) and post-revocation mediated rule (#53)."""
        if sign_in_method not in {"direct", "device", "mediated", "account_token"}:
            return GuardDecision(False, "unsupported_sign_in_method", 400)
        if (
            session_id in self.revoked_sessions
            and sign_in_method == "mediated"
            and stored_credentials_used
            and not user_initiated
        ):
            return GuardDecision(False, "auto_resignin_after_revocation_forbidden", 403)
        bound = self.session_accounts.get(session_id)
        if bound is not None and bound != account_id:
            return GuardDecision(False, "account_mismatch", 400)
        self.session_accounts[session_id] = account_id
        self.signed_out_sessions.discard(session_id)
        if user_initiated:
            self.revoked_sessions.discard(session_id)
        return GuardDecision(True, "signed_in", 200)

    def _check_session_and_scope(
        self,
        token: SessionToken,
        target_customer_id: str,
        required_scope: str,
    ) -> GuardDecision | None:
        if not token.signed_in or not token.account_id:
            return GuardDecision(False, "sign_in_required", 401)
        bound = self.session_accounts.get(token.session_id)
        if bound is not None and bound != token.account_id:
            return GuardDecision(False, "account_mismatch", 403)
        self.session_accounts[token.session_id] = token.account_id
        if token.account_id != target_customer_id:
            return GuardDecision(False, "account_mismatch", 403)
        if required_scope not in token.scopes:
            return GuardDecision(False, "insufficient_scope", 403)
        return None

    def _validate_item_change_terms(
        self,
        *,
        order: RetailOrder,
        action: str,
        current_item_id: str,
        replacement_item_id: str,
        payment_method_id: str,
    ) -> tuple[GuardDecision | None, int]:
        if action == "modify_pending_order_items":
            if order.status == "pending (items modified)":
                return GuardDecision(False, "one_time_modification_limit_exceeded", 409), 0
            if order.status != "pending":
                return GuardDecision(False, "invalid_order_status", 409), 0
        elif action == "exchange_delivered_order_items":
            if order.status != "delivered":
                return GuardDecision(False, "invalid_order_status", 409), 0
        else:
            return GuardDecision(False, "unsupported_action", 400), 0

        if current_item_id not in order.items.values():
            return GuardDecision(False, "order_item_not_found", 404), 0
        if current_item_id == replacement_item_id:
            return GuardDecision(False, "same_variant_swap_forbidden", 422), 0

        current_var = self.catalog.get(current_item_id)
        replacement_var = self.catalog.get(replacement_item_id)
        if current_var is None or replacement_var is None:
            return GuardDecision(False, "catalog_item_not_found", 404), 0
        if current_var.product_id != replacement_var.product_id:
            return GuardDecision(False, "cross_product_swap_forbidden", 422), 0
        if replacement_var.available_stock <= 0:
            return GuardDecision(False, "out_of_stock", 409), 0

        customer_methods = self.payment_methods.get(order.customer_id) or {}
        instrument = customer_methods.get(payment_method_id)
        if instrument is None:
            return GuardDecision(False, "payment_method_not_found", 404), 0

        # tau2/tau3-bench retail policy: payment/refund must use original payment method or gift card
        if (
            payment_method_id != order.original_payment_method_id
            and instrument.kind != "gift_card"
        ):
            return GuardDecision(False, "unsupported_payment_method", 422), 0

        price_diff = replacement_var.price_cents - current_var.price_cents
        if price_diff > 0 and instrument.kind == "gift_card":
            if instrument.balance_cents < price_diff:
                return GuardDecision(False, "insufficient_gift_card_balance", 422), 0

        return None, price_diff

    def propose_item_change(
        self,
        *,
        token: SessionToken,
        order_id: str,
        action: str,
        current_item_id: str,
        replacement_item_id: str,
        payment_method_id: str,
        now: int,
        ttl_seconds: int = 900,
        user_approval_required: bool = False,
    ) -> GuardDecision:
        """Validate retail policy invariants and return a Poppy `operations` v1 proposal (HTTP 202)."""
        order = self.orders.get(order_id)
        if order is None:
            return GuardDecision(False, "order_not_found", 404)

        session_err = self._check_session_and_scope(token, order.customer_id, "poppy:write")
        if session_err is not None:
            return session_err

        policy_err, price_diff = self._validate_item_change_terms(
            order=order,
            action=action,
            current_item_id=current_item_id,
            replacement_item_id=replacement_item_id,
            payment_method_id=payment_method_id,
        )
        if policy_err is not None:
            return policy_err

        self._op_seq += 1
        op_id = f"op_ret_{self._op_seq:04d}"
        cur_name = self.catalog[current_item_id].name
        rep_name = self.catalog[replacement_item_id].name
        summary = (
            f"{action} on order {order_id}: replace {cur_name} ({current_item_id}) "
            f"with {rep_name} ({replacement_item_id}), price_difference_cents={price_diff}, "
            f"payment_method_id={payment_method_id}."
        )
        record = OperationRecord(
            operation_id=op_id,
            session_id=token.session_id,
            client_id=token.client_id,
            user_id=token.user_id,
            account_id=order.customer_id,
            revision=1,
            state="proposed",
            summary=summary,
            terms={
                "action": action,
                "order_id": order_id,
                "current_item_id": current_item_id,
                "replacement_item_id": replacement_item_id,
                "price_difference_cents": price_diff,
                "payment_method_id": payment_method_id,
            },
            expires_at=now + ttl_seconds,
            user_approval_required=user_approval_required,
        )
        self.operations[op_id] = record
        return GuardDecision(True, "proposed", 202, asdict(record))

    def revise_operation(
        self,
        *,
        token: SessionToken,
        operation_id: str,
        replacement_item_id: str,
        payment_method_id: str,
        now: int,
        ttl_seconds: int = 900,
    ) -> GuardDecision:
        """Issue a new immutable revision of a proposed operation when terms change."""
        op = self.operations.get(operation_id)
        if op is None or op.client_id != token.client_id or op.user_id != token.user_id:
            return GuardDecision(False, "operation_not_found", 404)

        session_err = self._check_session_and_scope(token, op.account_id, "poppy:write")
        if session_err is not None:
            return session_err
        if op.state != "proposed":
            return GuardDecision(False, "operation_not_modifiable", 409, asdict(op))

        order = self.orders[op.terms["order_id"]]
        policy_err, price_diff = self._validate_item_change_terms(
            order=order,
            action=op.terms["action"],
            current_item_id=op.terms["current_item_id"],
            replacement_item_id=replacement_item_id,
            payment_method_id=payment_method_id,
        )
        if policy_err is not None:
            return policy_err

        op.revision += 1
        op.expires_at = now + ttl_seconds
        op.terms = {
            **op.terms,
            "replacement_item_id": replacement_item_id,
            "price_difference_cents": price_diff,
            "payment_method_id": payment_method_id,
        }
        cur_name = self.catalog[op.terms["current_item_id"]].name
        rep_name = self.catalog[replacement_item_id].name
        op.summary = (
            f"{op.terms['action']} on order {order.order_id}: replace {cur_name} "
            f"({op.terms['current_item_id']}) with {rep_name} ({replacement_item_id}), "
            f"price_difference_cents={price_diff}, payment_method_id={payment_method_id}."
        )
        return GuardDecision(True, "revised", 200, asdict(op))

    def handle_conversation_message(
        self,
        *,
        operation_id: str,
        sender: str,
        text: str,
    ) -> GuardDecision:
        """Enforce Poppy operations §4.3: a conversation message never confirms an operation."""
        op = self.operations.get(operation_id)
        return GuardDecision(
            False,
            "conversation_message_cannot_confirm",
            409,
            asdict(op) if op else None,
        )

    def confirm_operation(
        self,
        *,
        token: SessionToken,
        operation_id: str,
        revision: int,
        approved_by: str,  # "user" or "permission"
        now: int,
        standing_permission: StandingPermission | None = None,
    ) -> GuardDecision:
        """Confirm a specific revision of a proposed operation and execute at most once."""
        op = self.operations.get(operation_id)
        if op is None or op.client_id != token.client_id or op.user_id != token.user_id:
            return GuardDecision(False, "operation_not_found", 404)

        session_err = self._check_session_and_scope(token, op.account_id, "poppy:write")
        if session_err is not None:
            return session_err

        # At-most-once idempotency on repeated confirmation
        if op.state != "proposed":
            return GuardDecision(True, "already_final", 200, asdict(op))

        if now >= op.expires_at:
            op.state = "expired"
            return GuardDecision(False, "expired", 409, asdict(op))

        if revision != op.revision:
            return GuardDecision(False, "terms_changed", 409, asdict(op))

        # Per #51 (e910c866) Section 8.1 & operations §3.1: verify Company `summary` agrees with
        # material `terms` values (order_id, replacement_item_id, price_difference_cents, payment_method_id)
        expected_fragments = (
            f"order {op.terms['order_id']}",
            f"({op.terms['replacement_item_id']})",
            f"price_difference_cents={op.terms['price_difference_cents']}",
            f"payment_method_id={op.terms['payment_method_id']}",
        )
        if any(fragment not in op.summary for fragment in expected_fragments):
            return GuardDecision(False, "summary_terms_mismatch", 409, asdict(op))

        if approved_by == "permission":
            if op.user_approval_required or standing_permission is None:
                return GuardDecision(False, "user_approval_required", 403, asdict(op))
            if (
                _normalize_domain(standing_permission.company_domain) != _normalize_domain(self.company_domain)
                or standing_permission.account_id != op.account_id
                or now >= standing_permission.expires_at
                or op.terms["action"] not in standing_permission.allowed_actions
                or op.terms["price_difference_cents"]
                > standing_permission.max_price_difference_cents
            ):
                return GuardDecision(False, "user_approval_required", 403, asdict(op))
        elif approved_by != "user":
            return GuardDecision(False, "invalid_approved_by", 400, asdict(op))

        order = self.orders[op.terms["order_id"]]
        policy_err, price_diff = self._validate_item_change_terms(
            order=order,
            action=op.terms["action"],
            current_item_id=op.terms["current_item_id"],
            replacement_item_id=op.terms["replacement_item_id"],
            payment_method_id=op.terms["payment_method_id"],
        )
        if policy_err is not None:
            return policy_err

        # Execute deterministic state transition
        cur_item = op.terms["current_item_id"]
        rep_item = op.terms["replacement_item_id"]
        self.catalog[cur_item].available_stock += 1
        self.catalog[rep_item].available_stock -= 1

        instrument = self.payment_methods[order.customer_id][op.terms["payment_method_id"]]
        if instrument.kind == "gift_card":
            instrument.balance_cents -= price_diff

        if op.terms["action"] == "modify_pending_order_items":
            for line_key, val in order.items.items():
                if val == cur_item:
                    order.items[line_key] = rep_item
                    break
            order.status = "pending (items modified)"
        else:
            order.exchanged_items[cur_item] = rep_item

        op.state = "succeeded"
        op.confirmation = {
            "revision": revision,
            "approved_by": approved_by,
            "confirmed_at": now,
        }
        op.result = {
            "summary": f"Completed {op.terms['action']} on {order.order_id}.",
            "data": {
                "order_id": order.order_id,
                "order_status": order.status,
                "replacement_item_id": rep_item,
                "price_difference_cents": price_diff,
            },
        }
        return GuardDecision(True, "succeeded", 200, asdict(op))


@dataclass
class _ConversationState:
    conversation_id: str
    client_id: str
    user_id: str
    account_id: str | None
    status: str  # "idle", "working", "queued", "closed"
    responder: str  # "agent", "human"
    first_message_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    open_direct_conversation_id: str | None = None
    direct_messages: list[dict[str, Any]] = field(default_factory=list)


class PoppyConversationGuard:
    """Poppy v0.1 Section 7 (`spec#conversations`) & Milestone 2 conversation adapter guard (#35).

    Enforces the 19 deterministic `conversations.*` conformance invariants from
    `kit/company/validate/checks/conversations.ts` and `kit/company/patterns/conversations.md`:
    - Per-user `(client_id, user_id)` message ID deduplication and content-hash conflict (`409 message_id_conflict`).
    - URL-safe base64 alphabet IDs (`^[A-Za-z0-9_-]{1,256}$`) and non-empty message (`text`, `data`, or `context`).
    - Ownership isolation returning `404 conversation_not_found` for unknown or cross-user conversations.
    - Ordered Company event log (`cursor`, `has_more`, `status`, `responder` always present), strict cursor
      validation (`400 invalid_cursor`), and whole-number `wait` validation (`400 invalid_request`).
    - Idempotent close (`200 OK`, single `state: "closed"` event on first close, zero extra events on repeat close)
      and post-close write/handoff lock (`409 conversation_closed`).
    - Section 7.10 Direct Conversation isolation: at most one open Direct Conversation per parent, parent records
      only `direct_opened` / `direct_closed` state events, and direct customer messages are never returned to the
      Personal Agent's parent `GET /events` feed.
    """

    def __init__(self) -> None:
        self._conversations: dict[str, _ConversationState] = {}
        # Scoped per (client_id, user_id) -> message_id -> (content_hash, conversation_id, is_first, response_payload)
        self._accepted_messages: dict[tuple[str, str], dict[str, tuple[str, str, bool, dict[str, Any]]]] = {}
        self._conv_seq = 0
        self._event_seq = 0

    @staticmethod
    def _valid_id(value: str) -> bool:
        return bool(isinstance(value, str) and URL_SAFE_BASE64_ID_RE.match(value))

    @staticmethod
    def _validate_message_payload(message: dict[str, Any] | None) -> tuple[bool, str, str]:
        if not isinstance(message, dict):
            return False, "invalid_request", ""
        msg_id = message.get("id")
        if not isinstance(msg_id, str) or not PoppyConversationGuard._valid_id(msg_id):
            return False, "invalid_request", ""
        sender = message.get("sender")
        if sender not in {"agent", "human"}:
            return False, "invalid_request", ""
        has_text = isinstance(message.get("text"), str) and bool(message.get("text").strip())
        has_data = message.get("data") is not None
        has_context = message.get("context") is not None
        if not (has_text or has_data or has_context):
            return False, "invalid_request", ""
        canonical = json.dumps(
            {
                "sender": sender,
                "text": message.get("text"),
                "data": message.get("data"),
                "context": message.get("context"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return True, msg_id, content_hash

    def _next_event_id(self) -> str:
        self._event_seq += 1
        return f"evt_{self._event_seq:04d}"

    def _check_ownership(self, token: SessionToken, conversation_id: str) -> _ConversationState | None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            return None
        if conv.client_id != token.client_id or conv.user_id != token.user_id:
            return None
        if conv.account_id is not None and token.account_id is not None and conv.account_id != token.account_id:
            return None
        return conv

    def start_conversation(
        self,
        *,
        token: SessionToken,
        message: dict[str, Any] | None,
        now: str = "2026-10-17T00:00:00Z",
    ) -> tuple[int, dict[str, Any]]:
        """Handle `POST /conversations` (`conversations.start`, `retry-same-id`, `message-id-conflict`)."""
        ok, msg_id_or_err, content_hash = self._validate_message_payload(message)
        if not ok:
            return 400, {"error": msg_id_or_err}
        msg_id = msg_id_or_err
        user_scope = (token.client_id, token.user_id)
        user_msgs = self._accepted_messages.setdefault(user_scope, {})

        existing = user_msgs.get(msg_id)
        if existing is not None:
            prev_hash, prev_conv_id, is_first, prev_resp = existing
            if prev_hash != content_hash or not is_first:
                return 409, {"error": "message_id_conflict"}
            conv = self._conversations[prev_conv_id]
            return 201, {
                "conversation_id": conv.conversation_id,
                "status": conv.status,
                "responder": conv.responder,
            }

        self._conv_seq += 1
        conv_id = f"cnv_{self._conv_seq:04d}"
        conv = _ConversationState(
            conversation_id=conv_id,
            client_id=token.client_id,
            user_id=token.user_id,
            account_id=token.account_id if token.signed_in else None,
            status="idle",
            responder="agent",
            first_message_id=msg_id,
        )
        recorded_msg = dict(message)  # type: ignore[arg-type]
        recorded_msg["role"] = "user"
        conv.events.append(
            {
                "id": self._next_event_id(),
                "type": "message",
                "created_at": now,
                "message": recorded_msg,
            }
        )
        self._conversations[conv_id] = conv
        resp = {
            "conversation_id": conv_id,
            "status": conv.status,
            "responder": conv.responder,
        }
        user_msgs[msg_id] = (content_hash, conv_id, True, resp)
        return 201, resp

    def post_message(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        message: dict[str, Any] | None,
        now: str = "2026-10-17T00:00:01Z",
    ) -> tuple[int, dict[str, Any]]:
        """Handle `POST /conversations/{id}/messages` (`conversations.follow-up`, `closed-message`)."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}
        if conv.status == "closed":
            return 409, {"error": "conversation_closed"}

        ok, msg_id_or_err, content_hash = self._validate_message_payload(message)
        if not ok:
            return 400, {"error": msg_id_or_err}
        msg_id = msg_id_or_err
        user_scope = (token.client_id, token.user_id)
        user_msgs = self._accepted_messages.setdefault(user_scope, {})

        existing = user_msgs.get(msg_id)
        if existing is not None:
            prev_hash, prev_conv_id, is_first, _ = existing
            if prev_hash != content_hash or prev_conv_id != conversation_id or is_first:
                return 409, {"error": "message_id_conflict"}
            return 202, {"status": conv.status, "responder": conv.responder}

        if token.signed_in and token.account_id and conv.account_id is None:
            conv.account_id = token.account_id

        recorded_msg = dict(message)  # type: ignore[arg-type]
        recorded_msg["role"] = "user"
        conv.events.append(
            {
                "id": self._next_event_id(),
                "type": "message",
                "created_at": now,
                "message": recorded_msg,
            }
        )
        resp = {"status": conv.status, "responder": conv.responder}
        user_msgs[msg_id] = (content_hash, conversation_id, False, resp)
        return 202, resp

    def read_events(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        cursor: str | None = None,
        wait: str | int | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Handle `GET /conversations/{id}/events` (`events-read`, `unknown-cursor`, `invalid-wait`)."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}

        if wait is not None:
            if isinstance(wait, bool):
                return 400, {"error": "invalid_request"}
            if isinstance(wait, int):
                if wait < 0:
                    return 400, {"error": "invalid_request"}
            elif isinstance(wait, str):
                if not wait.isdigit():
                    return 400, {"error": "invalid_request"}
            else:
                return 400, {"error": "invalid_request"}

        start_idx = 0
        if cursor is not None:
            if not self._valid_id(cursor):
                return 400, {"error": "invalid_cursor"}
            found_idx = None
            for idx, ev in enumerate(conv.events):
                if ev["id"] == cursor:
                    found_idx = idx + 1
                    break
            if found_idx is None:
                return 400, {"error": "invalid_cursor"}
            start_idx = found_idx

        sliced = list(conv.events[start_idx:])
        new_cursor = conv.events[-1]["id"] if conv.events else cursor
        return 200, {
            "events": sliced,
            "cursor": new_cursor,
            "has_more": False,
            "status": conv.status,
            "responder": conv.responder,
        }

    def request_handoff(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        live_agent_joined: bool = False,
        now: str = "2026-10-17T00:00:02Z",
    ) -> tuple[int, dict[str, Any]]:
        """Handle `POST /conversations/{id}/handoff` (`spec#handoff`, `closed-handoff`)."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}
        if conv.status == "closed":
            return 409, {"error": "conversation_closed"}

        conv.status = "idle" if live_agent_joined else "queued"
        conv.responder = "human" if live_agent_joined else "agent"
        conv.events.append(
            {
                "id": self._next_event_id(),
                "type": "state",
                "created_at": now,
                "status": conv.status,
                "responder": conv.responder,
            }
        )
        return 200, {"status": conv.status, "responder": conv.responder}

    def open_direct_conversation(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        direct_customer_message: str,
        now: str = "2026-10-17T00:00:03Z",
    ) -> tuple[int, dict[str, Any]]:
        """Open a Section 7.10 Direct Conversation without leaking direct messages to the Personal Agent."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}
        if conv.status == "closed":
            return 409, {"error": "conversation_closed"}
        if conv.open_direct_conversation_id is not None:
            return 409, {"error": "direct_conversation_already_open"}

        direct_id = f"dir_{conv.conversation_id}"
        conv.open_direct_conversation_id = direct_id
        conv.direct_messages.append({"role": "user", "sender": "human", "text": direct_customer_message})
        conv.events.append(
            {
                "id": self._next_event_id(),
                "type": "state",
                "created_at": now,
                "direct": "direct_opened",
                "status": conv.status,
                "responder": conv.responder,
            }
        )
        return 201, {"direct_conversation_id": direct_id, "status": conv.status}

    def close_direct_conversation(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        now: str = "2026-10-17T00:00:04Z",
    ) -> tuple[int, dict[str, Any]]:
        """Close an open Section 7.10 Direct Conversation and record `direct_closed` on the parent."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}
        if conv.open_direct_conversation_id is None:
            return 409, {"error": "no_open_direct_conversation"}

        conv.open_direct_conversation_id = None
        conv.events.append(
            {
                "id": self._next_event_id(),
                "type": "state",
                "created_at": now,
                "direct": "direct_closed",
                "status": conv.status,
                "responder": conv.responder,
            }
        )
        return 200, {"status": conv.status, "responder": conv.responder}

    def close_conversation(
        self,
        *,
        token: SessionToken,
        conversation_id: str,
        now: str = "2026-10-17T00:00:05Z",
    ) -> tuple[int, dict[str, Any]]:
        """Handle `POST /conversations/{id}/close` (`close`, `close-event`, `close-again`)."""
        conv = self._check_ownership(token, conversation_id)
        if conv is None:
            return 404, {"error": "conversation_not_found"}

        if conv.status != "closed":
            conv.status = "closed"
            conv.open_direct_conversation_id = None
            conv.events.append(
                {
                    "id": self._next_event_id(),
                    "type": "state",
                    "created_at": now,
                    "status": "closed",
                    "responder": conv.responder,
                }
            )
        return 200, {"status": conv.status, "responder": conv.responder}


def run_demo() -> dict[str, Any]:
    """Run an offline end-to-end verification scenario for CLI inspection."""
    poppy_doc = {
        "protocol_version": "0.1",
        "organization": {"name": "Manzanita Supply", "domain": "manzanitasupply.example"},
        "auth": {
            "issuer": "https://auth.manzanitasupply.example",
            "direct": {"scopes": ["poppy:read", "poppy:write"]},
            "mediated": {"scopes": ["poppy:read"]},
        },
    }
    oauth_meta = {
        "issuer": "https://auth.manzanitasupply.example",
        "poppy_domains": ["manzanitasupply.example"],
    }
    discovery = verify_poppy_discovery(
        "https://manzanitasupply.example/.well-known/poppy.json",
        poppy_doc,
        oauth_meta,
    )

    guard = RetailOrderMutationGuard(
        company_domain="manzanitasupply.example",
        catalog={
            "jkt-storm-m": CatalogVariant("jkt-storm-m", "prod-storm", "Stormline Jacket (M)", 12000, 3),
            "jkt-storm-l": CatalogVariant("jkt-storm-l", "prod-storm", "Stormline Jacket (L)", 12500, 2),
            "jkt-storm-xl": CatalogVariant("jkt-storm-xl", "prod-storm", "Stormline Jacket (XL)", 14000, 1),
        },
        orders={
            "ord_7Hk2": RetailOrder(
                order_id="ord_7Hk2",
                customer_id="cust_alice",
                status="pending",
                items={"line_1": "jkt-storm-m"},
                original_payment_method_id="card_4242",
            )
        },
        payment_methods={
            "cust_alice": {
                "card_4242": PaymentInstrument("card_4242", "card"),
                "gc_100": PaymentInstrument("gc_100", "gift_card", balance_cents=1000),
            }
        },
    )

    token = SessionToken(
        access_token="tok_dpop_alice",
        token_type="DPoP",
        session_id="ses_2Lm0",
        client_id="https://agent.example/agent.json",
        user_id="usr_Q7c1vK",
        signed_in=True,
        account_id="cust_alice",
        scopes=frozenset({"poppy:read", "poppy:write"}),
        sign_in_method="direct",
        jwk_thumbprint="jkt_p256_alice",
        expires_at=2000,
    )

    proposal = guard.propose_item_change(
        token=token,
        order_id="ord_7Hk2",
        action="modify_pending_order_items",
        current_item_id="jkt-storm-m",
        replacement_item_id="jkt-storm-l",
        payment_method_id="gc_100",
        now=1000,
    )
    op_id = proposal.operation["operation_id"]  # type: ignore[index]
    chat_attempt = guard.handle_conversation_message(
        operation_id=op_id,
        sender="human",
        text="Yes, confirm!",
    )
    confirmed = guard.confirm_operation(
        token=token,
        operation_id=op_id,
        revision=1,
        approved_by="user",
        now=1010,
    )
    second_modify = guard.propose_item_change(
        token=token,
        order_id="ord_7Hk2",
        action="modify_pending_order_items",
        current_item_id="jkt-storm-l",
        replacement_item_id="jkt-storm-xl",
        payment_method_id="card_4242",
        now=1020,
    )

    return {
        "discovery_verified": discovery.allowed,
        "proposal_code": proposal.code,
        "chat_confirm_blocked": chat_attempt.code,
        "confirmed_state": confirmed.operation["state"] if confirmed.operation else None,
        "order_status_after_confirm": guard.orders["ord_7Hk2"].status,
        "second_pending_modify_blocked": second_modify.code,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
