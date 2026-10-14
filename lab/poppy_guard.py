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
from typing import Any
from urllib.parse import urlsplit


def _strip_www(host: str) -> str:
    host = host.lower().strip()
    return host[4:] if host.startswith("www.") else host


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
) -> DiscoveryCheckResult:
    """Verify Poppy v0.1 discovery document and mutual OAuth server `poppy_domains` binding."""
    parsed_req = urlsplit(requested_well_known_url)
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
    org_domain = str(org.get("domain", "")).lower().strip()
    if not org_domain or _strip_www(parsed_req.hostname) != _strip_www(org_domain):
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

    poppy_domains = {
        _strip_www(str(d))
        for d in (oauth_metadata.get("poppy_domains") or [])
        if isinstance(d, str) and d.strip()
    }
    if _strip_www(org_domain) not in poppy_domains:
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


@dataclass(frozen=True)
class TokenCheckResult:
    allowed: bool
    error: str | None
    http_status: int


def verify_poppy_request_token(
    *,
    token: SessionToken,
    channel: str,  # "openapi", "conversation", "operations", or "mcp"
    http_method: str,
    target_url: str,
    now: int,
    poppy_auth_config: dict[str, Any],
    required_scopes: set[str] | None = None,
    dpop_proof: DPoPProof | None = None,
    seen_jti: set[str] | None = None,
    max_proof_age_seconds: int = 60,
) -> TokenCheckResult:
    """Verify Poppy v0.1 Session Token transport (DPoP vs MCP Bearer) and sign-in scope caps."""
    if now >= token.expires_at:
        return TokenCheckResult(False, "invalid_token", 401)

    # Check sign-in method scope ceiling declared in poppy.json `auth`
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
    elif channel in {"openapi", "conversation", "operations"}:
        if token.token_type != "DPoP":
            return TokenCheckResult(False, "dpop_required", 401)
        if dpop_proof is None:
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if not token.jwk_thumbprint or dpop_proof.jwk_thumbprint != token.jwk_thumbprint:
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if dpop_proof.htm.upper() != http_method.upper():
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if _canonical_htu(dpop_proof.htu) != _canonical_htu(target_url):
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if abs(now - dpop_proof.iat) > max_proof_age_seconds:
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if dpop_proof.ath != sha256_token(token.access_token):
            return TokenCheckResult(False, "invalid_dpop_proof", 401)
        if seen_jti is not None:
            if dpop_proof.jti in seen_jti:
                return TokenCheckResult(False, "invalid_dpop_proof", 401)
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
        self.operations: dict[str, OperationRecord] = {}
        self._op_seq = 0

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

        if approved_by == "permission":
            if op.user_approval_required or standing_permission is None:
                return GuardDecision(False, "user_approval_required", 403, asdict(op))
            if (
                _strip_www(standing_permission.company_domain) != _strip_www(self.company_domain)
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
