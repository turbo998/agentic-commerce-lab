"""Offline, metadata-only UCP handler preflight; never authorize or send payments."""

import argparse
import base64
import copy
import json
import posixpath
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, quote, unquote, urlsplit

POLICY_CHECKED_ON = date(2026, 10, 19)
SOURCE_URL = "https://docs.stripe.com/agentic-commerce/protocols/ucp/stripe-payments-handler"
REVIEWED_UCP_VERSION = "2026-04-08"
REVIEWED_HANDLER_VERSION = "2026-06-25"
STRIPE_HANDLER = "com.stripe.payments"
INSTRUMENTS = frozenset({"card", "apple_pay", "link", "google_pay"})
UCP_SIGN_IF_PRESENT_HEADERS = frozenset({
    "ucp-agent",
    "signature-agent",
    "idempotency-key",
    "webhook-id",
    "webhook-timestamp",
})
FORBIDDEN_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
UCP_RAW_ITEM_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")
UCP_BASE64URL_NOPAD_RE = re.compile(r"^[A-Za-z0-9_-]+$")
UCP_POSITIVE_QUANTITY_RE = re.compile(r"^[1-9][0-9]*$")
UCP_SERVER_OWNED_ROOTS = frozenset({
    "totals",
    "presentment_currency",
    "status",
    "id",
    "identifiers",
    "order",
})
UCP_FORBIDDEN_PERMALINK_SECRET_KEYS = frozenset({
    "access_token",
    "api_key",
    "bearer_token",
    "card_number",
    "client_secret",
    "cvv",
    "mandate",
    "pan",
    "payment_credential",
    "payment_instrument_token",
    "refresh_token",
    "secret",
    "session_cookie",
    "shared_payment_granted_token",
    "spt",
    "token",
})
Environment = Literal["sandbox", "production"]
Relationship = Literal["confirmed", "missing", "unknown"]


def calendar_version(value: str) -> str:
    """Require a canonical date, not a moving latest/main alias or guessed version."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Version must be a YYYY-MM-DD date; aliases are not accepted.")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("Version must be a valid calendar date.") from None
    return value


@dataclass(frozen=True)
class HandlerMetadata:
    """Operator-declared metadata, not a parsed or authenticated UCP wire profile."""

    ucp_version: str
    handler_name: str
    handler_version: str
    environment: Environment
    instruments: tuple[str, ...]

    def __post_init__(self) -> None:
        calendar_version(self.ucp_version)
        calendar_version(self.handler_version)
        if not isinstance(self.handler_name, str) or not re.fullmatch(
            r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){2,}", self.handler_name
        ):
            raise ValueError("Handler name must be a reverse-domain metadata name, not a URL.")
        if not isinstance(self.environment, str) or self.environment not in {
            "sandbox", "production",
        }:
            raise ValueError("UCP environment must be sandbox or production, not MCP live.")
        if (
            type(self.instruments) is not tuple
            or any(not isinstance(item, str) or item not in INSTRUMENTS for item in self.instruments)
            or len(set(self.instruments)) != len(self.instruments)
        ):
            raise ValueError("Instruments must be a tuple of unique known metadata categories.")


@dataclass(frozen=True)
class Decision:
    """Compatibility only: even a candidate has no payment authority or verified access."""

    status: Literal["candidate_unverified", "blocked"]
    reasons: tuple[str, ...]
    credential_path: str | None
    payment_authorized: bool = False
    provider_verification: str = "not_performed"


def assess(
    platform: HandlerMetadata, business: HandlerMetadata, *,
    instrument: str, relationship: Relationship,
) -> Decision:
    """Check only the reviewed Stripe handler fixture; reject unknowns without fallback."""
    if not isinstance(platform, HandlerMetadata) or not isinstance(business, HandlerMetadata):
        raise ValueError("Preflight requires platform and business HandlerMetadata.")
    if not isinstance(instrument, str) or instrument not in INSTRUMENTS:
        raise ValueError("Select a known instrument category, never a credential.")
    if not isinstance(relationship, str) or relationship not in {"confirmed", "missing", "unknown"}:
        raise ValueError("Relationship must be confirmed, missing or unknown metadata.")

    reasons: list[str] = []
    if platform.ucp_version != business.ucp_version:
        reasons.append("ucp_version_mismatch")
    if any(profile.ucp_version != REVIEWED_UCP_VERSION for profile in (platform, business)):
        reasons.append("ucp_version_not_reviewed_locally")
    if platform.handler_name != business.handler_name:
        reasons.append("handler_name_mismatch")
    if any(profile.handler_name != STRIPE_HANDLER for profile in (platform, business)):
        reasons.append("handler_not_reviewed_locally")
    if platform.handler_version != business.handler_version:
        reasons.append("handler_version_mismatch")
    if any(profile.handler_version != REVIEWED_HANDLER_VERSION for profile in (platform, business)):
        reasons.append("handler_version_not_reviewed_locally")
    if any(instrument not in profile.instruments for profile in (platform, business)):
        reasons.append("instrument_not_advertised_by_both")
    if instrument == "link":
        reasons.append("link_instrument_not_accepted_by_current_complete")
    if instrument == "google_pay":
        reasons.append("google_pay_requires_separately_reviewed_com_google_pay_handler")
    if instrument == "card":
        if platform.environment != business.environment:
            reasons.append("card_tokenize_environment_mismatch")
        if relationship != "confirmed":
            reasons.append("card_tokenize_commerce_relationship_unconfirmed")
    if reasons:
        return Decision("blocked", tuple(reasons), None)
    path = "card_tokenize_to_spt" if instrument == "card" else "apple_pay_direct_to_complete"
    return Decision("candidate_unverified", (), path)


@dataclass(frozen=True)
class SigningGateDecision:
    """Offline UCP RFC 9421 closed 'sign-if-present' covered-component gate (#659, #795)."""

    accepted: bool
    reason: str
    missing_components: tuple[str, ...] = ()


def verify_ucp_signing_gate(
    *,
    has_query: bool,
    has_body: bool,
    present_headers: set[str] | frozenset[str],
    covered_components: tuple[str, ...],
) -> SigningGateDecision:
    """Verify UCP IRA step 5 closed covered-components set for signed HTTP requests/webhooks.

    Always required: `@method`, `@authority`, `@path`.
    Required when present: `@query` (if URL has query), `content-digest` & `content-type`
    (if HTTP body present), plus `ucp-agent`, `signature-agent`, `idempotency-key`,
    `webhook-id`, and `webhook-timestamp` (#659, #795).
    """
    normalized_headers = {h.lower().strip() for h in present_headers}
    covered_set = {c.lower().strip() for c in covered_components}

    if has_body and not {"content-digest", "content-type"}.issubset(normalized_headers):
        return SigningGateDecision(
            False,
            "missing_required_body_headers",
            tuple(sorted({"content-digest", "content-type"} - normalized_headers)),
        )

    required: list[str] = ["@method", "@authority", "@path"]
    if has_query:
        required.append("@query")
    if has_body:
        required.extend(["content-digest", "content-type"])
    for header in sorted(UCP_SIGN_IF_PRESENT_HEADERS):
        if header in normalized_headers:
            required.append(header)

    missing = tuple(comp for comp in required if comp not in covered_set)
    if missing:
        return SigningGateDecision(False, "closed_sign_if_present_violation", missing)
    return SigningGateDecision(True, "verified", ())


@dataclass(frozen=True)
class DiscoveryStatusDecision:
    """Offline UCP profile/JWKS/CIMD HTTP status check (#933: 304 allowed, 3xx redirects forbidden)."""

    accepted: bool
    reason: str


def verify_ucp_discovery_response_status(
    http_status: int,
    *,
    conditional_request: bool = False,
    has_cached_entry: bool = False,
) -> DiscoveryStatusDecision:
    """Enforce UCP #933 (5021fa83a652): redirects are forbidden, conditional 304 is allowed."""
    if http_status == 200:
        return DiscoveryStatusDecision(True, "ok_fresh")
    if http_status == 304:
        if conditional_request and has_cached_entry:
            return DiscoveryStatusDecision(True, "ok_not_modified_cache_valid")
        return DiscoveryStatusDecision(False, "unsolicited_or_uncached_304")
    if http_status in FORBIDDEN_REDIRECT_STATUSES or 300 <= http_status < 400:
        return DiscoveryStatusDecision(False, "redirect_forbidden")
    return DiscoveryStatusDecision(False, f"unexpected_http_status_{http_status}")


@dataclass(frozen=True)
class PermalinkRedirectDecision:
    """Offline UCP permalink 303 redirect header check (#913, 3ab41043b793)."""

    accepted: bool
    reason: str
    missing_headers: tuple[str, ...] = ()


def verify_ucp_permalink_redirect(
    http_status: int,
    headers: dict[str, str],
) -> PermalinkRedirectDecision:
    """Enforce UCP #913 (3ab41043b793): permalink 303 redirect MUST carry Location,
    Cache-Control: no-store, and Referrer-Policy: no-referrer to prevent buyer PII leakage.
    """
    if http_status != 303:
        return PermalinkRedirectDecision(False, "permalink_redirect_requires_303")

    normalized = {
        str(k).lower().strip(): str(v).strip()
        for k, v in (headers or {}).items()
        if isinstance(k, str) and isinstance(v, str) and v.strip()
    }
    required = ("location", "cache-control", "referrer-policy")
    missing = tuple(h for h in required if h not in normalized)
    if missing:
        return PermalinkRedirectDecision(False, "missing_mandated_permalink_headers", missing)

    loc = normalized["location"]
    parsed_loc = urlsplit(loc)
    if parsed_loc.scheme.lower() != "https" or not parsed_loc.hostname or any(c.isspace() for c in loc):
        return PermalinkRedirectDecision(False, "invalid_location_url")

    cc_directives = {
        token.strip().lower()
        for token in normalized["cache-control"].split(",")
        if token.strip()
    }
    if "no-store" not in cc_directives:
        return PermalinkRedirectDecision(False, "cache_control_must_include_no_store")

    ref_tokens = [
        token.strip().lower()
        for token in normalized["referrer-policy"].split(",")
        if token.strip()
    ]
    if not ref_tokens or ref_tokens[-1] != "no-referrer":
        return PermalinkRedirectDecision(False, "referrer_policy_must_be_no_referrer")

    return PermalinkRedirectDecision(True, "ok_permalink_303_no_store_no_referrer", ())


@dataclass(frozen=True)
class PermalinkInputValidationDecision:
    """Offline UCP `dev.ucp.shopping.permalink` untrusted GET input validator (`permalink.md`, #913)."""

    accepted: bool
    reason: str
    resolved_line_items: tuple[dict[str, Any], ...] = ()
    resolved_continue_to: str = "/"
    applied_ucp_fields: dict[str, str] | None = None
    non_ucp_params: dict[str, str] | None = None


def encode_ucp_item_id_token(item_id: str) -> str:
    """Encode an item identifier per UCP `permalink.md` (#Item ID Token).

    Raw tokens matching `^[A-Za-z0-9._-]+$` may be used directly; any other identifier MUST be
    encoded as `"~" + base64url_no_padding(utf8(item_identifier))` (never percent-encoded).
    """
    if not isinstance(item_id, str) or not item_id or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in item_id):
        raise ValueError("item_id must be a non-empty string without control characters")
    if UCP_RAW_ITEM_TOKEN_RE.match(item_id):
        return item_id
    encoded = base64.urlsafe_b64encode(item_id.encode("utf-8")).decode("ascii").rstrip("=")
    return f"~{encoded}"


def decode_ucp_item_id_token(token: str) -> str:
    """Decode and validate a UCP compact-path `item_id_token` (`permalink.md` #Item ID Token)."""
    if not isinstance(token, str) or not token:
        raise ValueError("empty_item_id_token")
    if "%" in token:
        raise ValueError("percent_encoded_item_token_forbidden")
    if token.startswith("~"):
        b64_part = token[1:]
        if not b64_part or "=" in b64_part or not UCP_BASE64URL_NOPAD_RE.match(b64_part):
            raise ValueError("non_canonical_tilde_base64url")
        padding = "=" * ((4 - (len(b64_part) % 4)) % 4)
        try:
            raw_bytes = base64.urlsafe_b64decode(b64_part + padding)
            decoded = raw_bytes.decode("utf-8")
        except Exception as exc:
            raise ValueError("invalid_tilde_base64url_utf8") from exc
        # Verify canonical base64url without padding (reject non-zero trailing pad bits)
        reencoded = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
        if reencoded != b64_part or not decoded:
            raise ValueError("non_canonical_tilde_base64url")
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in decoded):
            raise ValueError("control_character_in_decoded_item_id")
        return decoded
    if not UCP_RAW_ITEM_TOKEN_RE.match(token):
        raise ValueError("invalid_raw_item_id_token")
    return token


def validate_ucp_continue_to(
    raw_continue_to: str | None,
    *,
    default_destination: str = "/checkout",
) -> tuple[str, bool]:
    """Validate `continue_to` in strict 5-step order (`permalink.md` #Destination Preference).

    Returns `(canonical_reencoded_path, used_fallback)`. Any value failing the 5 steps falls back
    to `default_destination` rather than reflecting untrusted input or allowing open redirect/CRLF.
    """
    if raw_continue_to is None or not isinstance(raw_continue_to, str) or not raw_continue_to:
        return default_destination, False
    # Step 1: Percent-decode once
    decoded = unquote(raw_continue_to)
    # Step 2: Must start with single `/` (not `//`), no scheme, backslash, whitespace, or control chars
    if (
        not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or "://" in decoded
        or any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in decoded)
    ):
        return default_destination, True
    parsed = urlsplit(decoded)
    if parsed.scheme or parsed.netloc:
        return default_destination, True
    # Step 3 & 4: Apply dot-segment removal and verify same-origin relative path
    norm_path = posixpath.normpath(parsed.path)
    if not norm_path.startswith("/") or norm_path.startswith("//"):
        return default_destination, True
    if parsed.path.endswith("/") and norm_path != "/":
        norm_path += "/"
    # Step 5: Emit re-encoded canonical path without control characters
    reencoded_path = quote(norm_path, safe="/:@!$&'()*+,;=-._~")
    if parsed.query:
        reencoded_query = quote(parsed.query, safe="=&/:@!$'()*+,;-._~")
        reencoded_path = f"{reencoded_path}?{reencoded_query}"
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in reencoded_path):
        return default_destination, True
    return reencoded_path, False


def validate_ucp_permalink_request(
    permalink_url: str,
    *,
    configured_endpoint: str = "https://merchant.example/buy",
    allowed_ucp_roots: frozenset[str] = frozenset({"buyer", "context", "attribution", "discounts", "line_items"}),
    default_destination: str = "/checkout",
    max_url_octets: int = 2048,
) -> PermalinkInputValidationDecision:
    """Validate an untrusted UCP `dev.ucp.shopping.permalink` GET URL (`permalink.md`, #913).

    Enforces:
    - UTF-8 octet budget (`max_url_octets`, default 2,048 octets per `permalink.md` #URL Budget).
    - Compact item path (`{item_id_token}:{quantity}`) with raw vs `~`-base64url decoding and positive
      base-10 integer quantities without leading zeros.
    - Query parameter classification, canonical JSON Pointer normalization (`/buyer/email` == `buyer/email`),
      duplicate pointer collision rejection, and duplicate `continue_to` rejection.
    - Compact-path authority over `line_items/{i}/id` and `line_items/{i}/quantity` (query parameters
      targeting path-created item IDs or quantities cannot override them, while extension fields like
      `line_items/0/selling_plan` are allowed).
    - Rejection of server-owned fields (`totals`, `status`, `order`, `presentment_currency`) and
      prohibition of payment credentials, mandates, or secrets in permalink URLs.
    """
    if not isinstance(permalink_url, str) or not permalink_url.strip():
        return PermalinkInputValidationDecision(False, "empty_permalink_url")
    if len(permalink_url.encode("utf-8")) > max_url_octets:
        return PermalinkInputValidationDecision(False, "url_budget_exceeded")

    ep = urlsplit(configured_endpoint.rstrip("/"))
    u = urlsplit(permalink_url)
    if (
        u.scheme.lower() != "https"
        or u.netloc.lower() != ep.netloc.lower()
        or u.username
        or u.password
        or "\\" in permalink_url
        or any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in permalink_url)
    ):
        return PermalinkInputValidationDecision(False, "invalid_permalink_endpoint_origin")

    base_path = ep.path.rstrip("/")
    if u.path == base_path or u.path == f"{base_path}/":
        compact_segment = ""
    elif u.path.startswith(f"{base_path}/"):
        compact_segment = u.path[len(base_path) + 1 :]
        if "/" in compact_segment or "%2f" in compact_segment.lower():
            return PermalinkInputValidationDecision(False, "invalid_compact_item_path")
    else:
        return PermalinkInputValidationDecision(False, "permalink_path_mismatch")

    line_items: list[dict[str, Any]] = []
    if compact_segment:
        for pair_str in compact_segment.split(","):
            if ":" not in pair_str:
                return PermalinkInputValidationDecision(False, "malformed_item_pair")
            token_part, qty_part = pair_str.split(":", 1)
            if not UCP_POSITIVE_QUANTITY_RE.match(qty_part):
                return PermalinkInputValidationDecision(False, "invalid_item_quantity")
            try:
                decoded_item_id = decode_ucp_item_id_token(token_part)
            except ValueError as err:
                return PermalinkInputValidationDecision(False, str(err))
            line_items.append({"item": {"id": decoded_item_id}, "quantity": int(qty_part)})

    raw_pairs = parse_qsl(u.query, keep_blank_values=True)
    continue_to_values: list[str] = []
    ucp_fields: dict[str, str] = {}
    non_ucp_params: dict[str, str] = {}

    for raw_key, raw_val in raw_pairs:
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in raw_key) or any(
            ord(ch) < 0x20 or ord(ch) == 0x7F for ch in raw_val
        ):
            return PermalinkInputValidationDecision(False, "control_character_in_query")

        if raw_key == "continue_to":
            continue_to_values.append(raw_val)
            continue

        norm_pointer = "/" + raw_key.lstrip("/")
        tokens = [t for t in norm_pointer.split("/") if t]
        if not tokens:
            return PermalinkInputValidationDecision(False, "empty_query_key")

        # Enforce Privacy rule: permalinks MUST NOT contain payment credentials, mandates, or secrets
        lowered_tokens = {t.lower() for t in tokens}
        if lowered_tokens & UCP_FORBIDDEN_PERMALINK_SECRET_KEYS:
            return PermalinkInputValidationDecision(False, "forbidden_secret_or_credential_in_permalink")

        root = tokens[0]
        if root in UCP_SERVER_OWNED_ROOTS:
            return PermalinkInputValidationDecision(False, "server_owned_field_forbidden")

        if root in allowed_ucp_roots:
            if norm_pointer in ucp_fields:
                return PermalinkInputValidationDecision(False, "duplicate_ucp_pointer_collision")
            # Merge rule: compact item path is authoritative for line_items IDs and quantities
            if root == "line_items" and len(tokens) >= 3 and tokens[1].isdigit():
                idx = int(tokens[1])
                leaf = "/".join(tokens[2:])
                if idx < len(line_items) and leaf in {"quantity", "item/id", "id"}:
                    # Compact path stays authoritative; ignore query override of path item ID/quantity
                    ucp_fields[norm_pointer] = str(
                        line_items[idx]["quantity"] if leaf == "quantity" else line_items[idx]["item"]["id"]
                    )
                    continue
            ucp_fields[norm_pointer] = raw_val
        else:
            if raw_key in non_ucp_params:
                return PermalinkInputValidationDecision(False, "duplicate_query_parameter")
            non_ucp_params[raw_key] = raw_val

    if len(continue_to_values) > 1:
        return PermalinkInputValidationDecision(False, "duplicate_continue_to_collision")

    resolved_dest, _ = validate_ucp_continue_to(
        continue_to_values[0] if continue_to_values else None,
        default_destination=default_destination,
    )
    return PermalinkInputValidationDecision(
        accepted=True,
        reason="ok_permalink_validated",
        resolved_line_items=tuple(line_items),
        resolved_continue_to=resolved_dest,
        applied_ucp_fields=ucp_fields,
        non_ucp_params=non_ucp_params,
    )


@dataclass(frozen=True)
class UCPOrderWebhookDelivery:
    """Synthetic UCP order webhook delivery carrying full current order state (#659)."""

    webhook_id: str
    webhook_timestamp: str
    order_id: str
    order_state: dict[str, Any]
    present_headers: frozenset[str]
    covered_components: tuple[str, ...]


@dataclass(frozen=True)
class WebhookConvergenceResult:
    converged_order_state: dict[str, Any] | None
    applied_webhook_ids: tuple[str, ...]
    deduplicated_retry_ids: tuple[str, ...]
    rejected_deliveries: tuple[tuple[str, str], ...]


def converge_ucp_order_webhooks(
    deliveries: list[UCPOrderWebhookDelivery],
) -> WebhookConvergenceResult:
    """Deduplicate by `Webhook-Id` and converge full-state order webhooks by `Webhook-Timestamp` (#659)."""
    seen_events: dict[str, tuple[datetime, UCPOrderWebhookDelivery]] = {}
    deduplicated: list[str] = []
    rejected: list[tuple[str, str]] = []

    for delivery in deliveries:
        headers_lower = {h.lower().strip() for h in delivery.present_headers}
        if not {"webhook-id", "webhook-timestamp"}.issubset(headers_lower):
            rejected.append((delivery.webhook_id, "missing_webhook_identity_headers"))
            continue
        gate = verify_ucp_signing_gate(
            has_query=False,
            has_body=True,
            present_headers=headers_lower,
            covered_components=delivery.covered_components,
        )
        if not gate.accepted:
            rejected.append((delivery.webhook_id, gate.reason))
            continue
        try:
            ts = datetime.fromisoformat(delivery.webhook_timestamp.replace("Z", "+00:00"))
        except ValueError:
            rejected.append((delivery.webhook_id, "invalid_webhook_timestamp"))
            continue

        existing = seen_events.get(delivery.webhook_id)
        if existing is not None:
            if existing[0] != ts:
                rejected.append((delivery.webhook_id, "webhook_timestamp_mutated_on_retry"))
            else:
                deduplicated.append(delivery.webhook_id)
            continue
        seen_events[delivery.webhook_id] = (ts, delivery)

    ordered = sorted(seen_events.values(), key=lambda pair: (pair[0], pair[1].webhook_id))
    latest_state = dict(ordered[-1][1].order_state) if ordered else None
    return WebhookConvergenceResult(
        converged_order_state=latest_state,
        applied_webhook_ids=tuple(pair[1].webhook_id for pair in ordered),
        deduplicated_retry_ids=tuple(deduplicated),
        rejected_deliveries=tuple(rejected),
    )


@dataclass(frozen=True)
class IdentityDiscoveryResult:
    selected_issuer: str | None
    reason: str
    discarded_entries: tuple[tuple[str, str], ...]


def select_ucp_identity_authorization_server(
    *,
    protected_resource_metadata: dict[str, Any],
    expected_resource: str,
    oauth_metadata_by_entry: dict[str, dict[str, Any]],
    usable_client_issuers: set[str],
) -> IdentityDiscoveryResult:
    """Evaluate multi-entry RFC 9728 `authorization_servers` with RFC 8414 §3.3 exact `issuer` match.

    Models UCP `dev.ucp.common.identity_linking` multi-entry evaluation (RFC 9728 / RFC 8414 §3.3;
    clarified in UCP PR #891):
    - Every candidate in `authorization_servers` must have discovered OAuth metadata whose `issuer`
      is byte-for-byte identical to the entry (a custom storefront vanity domain whose metadata
      reports a different provider URI fails Step 2 and is discarded without aborting discovery).
    - Entries where the platform holds no usable client identity are discarded.
    - Among remaining entries, the first valid entry in array order is selected; discovery fails
      only when no valid entry remains.
    """
    resource = str(protected_resource_metadata.get("resource", "")).strip()
    if resource != expected_resource.strip():
        return IdentityDiscoveryResult(None, "resource_mismatch", ())

    entries = protected_resource_metadata.get("authorization_servers")
    if not isinstance(entries, list) or not entries:
        return IdentityDiscoveryResult(None, "missing_authorization_servers", ())

    discarded: list[tuple[str, str]] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, str) or not raw_entry.strip().startswith("https://"):
            discarded.append((str(raw_entry), "invalid_issuer_uri"))
            continue
        entry = raw_entry.strip()
        meta = oauth_metadata_by_entry.get(entry)
        if not isinstance(meta, dict):
            discarded.append((entry, "metadata_unavailable"))
            continue
        meta_issuer = str(meta.get("issuer", "")).strip()
        if meta_issuer != entry:
            discarded.append((entry, "issuer_mismatch"))
            continue
        if entry not in usable_client_issuers:
            discarded.append((entry, "no_usable_client_identity"))
            continue
        return IdentityDiscoveryResult(entry, "selected", tuple(discarded))

    return IdentityDiscoveryResult(None, "no_valid_authorization_server", tuple(discarded))


@dataclass(frozen=True)
class MandateAdmissionResult:
    admitted: bool
    checkout_status: str  # "complete_in_progress", "completed", or "canceled"
    error_code: str | None
    admission_evidence: dict[str, Any]


def evaluate_ucp_mandate_admission(
    *,
    reference: str,
    checkout_id: str,
    mandate_exp: int,
    evaluated_at: int,
    settlement_completed_at: int | None = None,
) -> MandateAdmissionResult:
    """Evaluate AP2 mandate liveness once at Complete Checkout admission (UCP #512 / draft PR #540).

    Enforces the admission-time boundary shared with `lab/checkout.py`:
    - Mandate TTL is evaluated **once** at admission (`evaluated_at <= mandate_exp`).
    - If expired at admission (`evaluated_at > mandate_exp`), checkout MUST NOT enter
      `complete_in_progress` and terminates `canceled` with `mandate_expired`.
    - If valid at admission, authorization is frozen for settlement: entering `complete_in_progress`
      and settling at `settlement_completed_at > mandate_exp` MUST NOT abort or emit `mandate_expired`.
    """
    if not reference.strip() or not checkout_id.strip():
        raise ValueError("reference and checkout_id are required")
    if evaluated_at <= 0 or mandate_exp <= 0:
        raise ValueError("timestamps must be positive Unix epoch seconds")

    if evaluated_at > mandate_exp:
        return MandateAdmissionResult(
            admitted=False,
            checkout_status="canceled",
            error_code="mandate_expired",
            admission_evidence={
                "reference": reference,
                "checkout_id": checkout_id,
                "evaluated_at": evaluated_at,
                "mandate_exp": mandate_exp,
                "result": "expired_at_admission",
            },
        )

    terminal_status = "completed" if settlement_completed_at is not None else "complete_in_progress"
    return MandateAdmissionResult(
        admitted=True,
        checkout_status=terminal_status,
        error_code=None,
        admission_evidence={
            "reference": reference,
            "checkout_id": checkout_id,
            "evaluated_at": evaluated_at,
            "mandate_exp": mandate_exp,
            "result": "admitted",
        },
    )


UCP_CONSENT_SOURCES = frozenset({"business", "platform"})


@dataclass(frozen=True)
class ConsentValidationResult:
    """Offline UCP `dev.ucp.shopping.buyer_consent` state & replacement-carve-out decision."""

    accepted: bool
    reason: str
    effective_consent: dict[str, dict[str, Any]]
    missing_dependency_codes: tuple[str, ...] = ()


def validate_and_merge_ucp_buyer_consent(
    *,
    advertised_consent: dict[str, dict[str, Any]],
    prior_consent: dict[str, dict[str, Any]] | None,
    submitted_consent: dict[str, dict[str, Any]] | None,
    operation: Literal["create", "update", "complete"],
    buyer_stated_keys: set[str] | frozenset[str] = frozenset(),
    buyer_info: dict[str, Any] | None = None,
    required_buyer_fields_by_key: dict[str, str] | None = None,
) -> ConsentValidationResult:
    """Validate UCP `dev.ucp.shopping.buyer_consent` normative rules & full-replacement carve-out (#660).

    Enforces:
    1. Full-replacement carve-out (#660): omitting `buyer.consent` on `update` or `complete` MUST NOT
       clear previously captured consent (`prior_consent` is preserved rather than reset to defaults).
    2. Confirm completeness (Normative Rule 2): when `submitted_consent` is provided, every advertised
       purpose and segment key MUST be included with both `granted` (bool) and `source` (`business` or `platform`);
       omitting an advertised key inside a submitted `consent` map is rejected.
    3. Advertised set is authoritative (Normative Rule 3): unadvertised purposes/segments are ignored.
    4. Source attribution (Normative Rule 5): a platform MAY change `source` from `"business"` to
       `"platform"` only when the key is in `buyer_stated_keys`; otherwise it MUST echo the prior/advertised
       `granted` and `source` unchanged.
    5. Data dependencies: if a confirmed `granted: True` choice requires a buyer field (e.g.,
       `dev.ucp.consent.marketing.sms` requires `phone_number`) that is missing, `create`/`update`
       records a `missing_consent_data` warning code while `complete` is blocked from completing.
    """
    baseline = copy.deepcopy(prior_consent) if prior_consent is not None else copy.deepcopy(advertised_consent)
    deps = required_buyer_fields_by_key or {
        "dev.ucp.consent.marketing.sms": "phone_number",
    }
    buyer_data = buyer_info or {}

    if submitted_consent is None:
        effective = baseline
    else:
        if not isinstance(submitted_consent, dict):
            return ConsentValidationResult(False, "invalid_consent_map", baseline)
        effective = {}
        for purpose_key, adv_purpose in advertised_consent.items():
            if purpose_key not in submitted_consent:
                return ConsentValidationResult(
                    False, f"missing_advertised_purpose:{purpose_key}", baseline
                )
            sub_purpose = submitted_consent[purpose_key]
            if (
                not isinstance(sub_purpose, dict)
                or type(sub_purpose.get("granted")) is not bool
                or sub_purpose.get("source") not in UCP_CONSENT_SOURCES
            ):
                return ConsentValidationResult(
                    False, f"invalid_purpose_entry:{purpose_key}", baseline
                )
            base_purpose = baseline.get(purpose_key, adv_purpose)
            if purpose_key not in buyer_stated_keys:
                if (
                    sub_purpose["granted"] != base_purpose.get("granted")
                    or sub_purpose["source"] != base_purpose.get("source")
                ):
                    return ConsentValidationResult(
                        False, f"unauthored_consent_mutation:{purpose_key}", baseline
                    )
            else:
                if sub_purpose["source"] != "platform":
                    return ConsentValidationResult(
                        False, f"buyer_preference_requires_platform_source:{purpose_key}", baseline
                    )

            merged_purpose: dict[str, Any] = {
                "granted": sub_purpose["granted"],
                "source": sub_purpose["source"],
            }
            if "description" in adv_purpose:
                merged_purpose["description"] = adv_purpose["description"]

            adv_segments = adv_purpose.get("segments")
            if isinstance(adv_segments, dict) and adv_segments:
                sub_segments = sub_purpose.get("segments")
                if not isinstance(sub_segments, dict):
                    return ConsentValidationResult(
                        False, f"missing_advertised_segments:{purpose_key}", baseline
                    )
                base_segments = base_purpose.get("segments") or adv_segments
                merged_segments: dict[str, dict[str, Any]] = {}
                for seg_key, adv_seg in adv_segments.items():
                    if seg_key not in sub_segments:
                        return ConsentValidationResult(
                            False, f"missing_advertised_segment:{seg_key}", baseline
                        )
                    sub_seg = sub_segments[seg_key]
                    if (
                        not isinstance(sub_seg, dict)
                        or type(sub_seg.get("granted")) is not bool
                        or sub_seg.get("source") not in UCP_CONSENT_SOURCES
                    ):
                        return ConsentValidationResult(
                            False, f"invalid_segment_entry:{seg_key}", baseline
                        )
                    base_seg = base_segments.get(seg_key, adv_seg)
                    full_seg_id = f"{purpose_key}.{seg_key}" if not seg_key.startswith(purpose_key) else seg_key
                    stated = seg_key in buyer_stated_keys or full_seg_id in buyer_stated_keys
                    if not stated:
                        if (
                            sub_seg["granted"] != base_seg.get("granted")
                            or sub_seg["source"] != base_seg.get("source")
                        ):
                            return ConsentValidationResult(
                                False, f"unauthored_segment_mutation:{seg_key}", baseline
                            )
                    else:
                        if sub_seg["source"] != "platform":
                            return ConsentValidationResult(
                                False, f"buyer_preference_requires_platform_source:{seg_key}", baseline
                            )
                    merged_seg: dict[str, Any] = {
                        "granted": sub_seg["granted"],
                        "source": sub_seg["source"],
                    }
                    if "description" in adv_seg:
                        merged_seg["description"] = adv_seg["description"]
                    merged_segments[seg_key] = merged_seg
                merged_purpose["segments"] = merged_segments
            effective[purpose_key] = merged_purpose

    missing_deps: list[str] = []
    for purpose_key, p_val in effective.items():
        if p_val.get("granted") is True and purpose_key in deps:
            field_name = deps[purpose_key]
            if not str(buyer_data.get(field_name, "")).strip():
                missing_deps.append(f"{purpose_key}->$.buyer.{field_name}")
        for seg_key, s_val in (p_val.get("segments") or {}).items():
            if s_val.get("granted") is True and seg_key in deps:
                field_name = deps[seg_key]
                if not str(buyer_data.get(field_name, "")).strip():
                    missing_deps.append(f"{seg_key}->$.buyer.{field_name}")

    if missing_deps and operation == "complete":
        return ConsentValidationResult(
            False,
            "missing_consent_data_blocks_complete",
            effective,
            tuple(missing_deps),
        )
    return ConsentValidationResult(
        True,
        "verified_with_warnings" if missing_deps else "verified",
        effective,
        tuple(missing_deps),
    )


def resolve_ucp_effective_consent(
    consent_map: dict[str, dict[str, Any]],
    *,
    purpose: str,
    segment: str | None = None,
) -> bool | None:
    """Resolve effective `granted` boolean where segment overrides parent purpose (Normative Rule 4)."""
    p_obj = consent_map.get(purpose)
    if not isinstance(p_obj, dict):
        return None
    if segment is not None:
        seg_map = p_obj.get("segments")
        if isinstance(seg_map, dict) and segment in seg_map:
            seg_val = seg_map[segment].get("granted")
            if type(seg_val) is bool:
                return seg_val
    val = p_obj.get("granted")
    return val if type(val) is bool else None


@dataclass(frozen=True)
class EscalationContractDecision:
    """Offline UCP `requires_escalation` -> `continue_url` contract check (checkout/index.md & PR #912)."""

    accepted: bool
    reason: str


def verify_ucp_checkout_escalation_contract(
    checkout_payload: dict[str, Any],
    *,
    direction: Literal["request", "response"] = "response",
) -> EscalationContractDecision:
    """Verify UCP checkout `requires_escalation` contract (checkout/index.md L949/L1022 & PR #912).

    - Requests MUST omit response-only `status` and `continue_url` (`ucp_request: omit`).
    - Responses with `status == "requires_escalation"` MUST provide a valid HTTPS `continue_url`
      for buyer handoff.
    """
    if direction == "request":
        if "status" in checkout_payload or "continue_url" in checkout_payload:
            return EscalationContractDecision(False, "response_only_escalation_fields_in_request")
        return EscalationContractDecision(True, "verified")

    status = checkout_payload.get("status")
    if status == "requires_escalation":
        continue_url = checkout_payload.get("continue_url")
        if not isinstance(continue_url, str) or not continue_url.strip():
            return EscalationContractDecision(False, "missing_continue_url_on_requires_escalation")
        parsed = urlsplit(continue_url.strip())
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            return EscalationContractDecision(False, "invalid_https_continue_url")
    return EscalationContractDecision(True, "verified")


UCP_RETURN_ELIGIBILITY_TYPES = frozenset({"window", "unlimited", "not_accepted"})
UCP_RETURN_ANCHORS = frozenset({"purchased", "fulfilled", "delivered"})
UCP_WELL_KNOWN_RETURN_FEES = frozenset({
    "dev.ucp.shopping.fee.restocking",
    "dev.ucp.shopping.fee.return_shipping",
    "dev.ucp.shopping.fee.handling",
})
UCP_ISO8601_DURATION_RE = re.compile(
    r"^P(?:[1-9]\d*[YMWD])+(?:T(?:[1-9]\d*[HMS])+)?$|^PT(?:[1-9]\d*[HMS])+$"
)
REVERSE_DOMAIN_FEE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}$")


@dataclass(frozen=True)
class ReturnPolicyEvaluation:
    """Offline UCP `dev.ucp.shopping.policy.return` schema & platform no-date-math check (PR #966)."""

    valid_schema: bool
    reason: str
    eligibility_status: Literal[
        "window_open",
        "window_floor_lapsed_not_prohibited",
        "window_terms_only_no_platform_date_math",
        "unlimited_time_bound",
        "not_accepted",
        "unstructured_or_unknown_no_inference",
        "invalid_policy",
    ]
    authoritative_expires_at: str | None = None


def evaluate_ucp_return_policy(
    policy: dict[str, Any],
    *,
    now_iso: str | None = None,
    platform_computed_expires_at: str | None = None,
) -> ReturnPolicyEvaluation:
    """Validate UCP `dev.ucp.shopping.policy.return` invariants and platform responsibilities (PR #966).

    Enforces:
    1. Platform MUST NOT perform date math to synthesize a return deadline from `duration` + `anchor`
       when the business has not resolved `expires_at` (`platform_computed_expires_at` is rejected).
    2. Omitted `eligibility` or unknown `eligibility.type` means not stated structurally; platforms
       MUST NOT infer `unlimited` or `not_accepted`.
    3. `window` requires valid positive ISO 8601 `duration` and `anchor`; `unlimited` and `not_accepted`
       MUST NOT carry `duration`, `anchor`, or `expires_at`.
    4. When `eligibility.type == "not_accepted"`, `supported_resolutions`, `methods`, and `fees` MUST be omitted.
    5. Each `fees[]` entry enforces mutual exclusion of `amount` and `basis_points`, `max_amount` requiring
       `basis_points`, and mandatory `display_text` when `type` is a vendor fee or when neither `amount`
       nor `basis_points` is present.
    6. `window` expiry is a guaranteed minimum floor, not a prohibition ceiling (`window_floor_lapsed_not_prohibited`).
    """
    if platform_computed_expires_at is not None:
        return ReturnPolicyEvaluation(
            False,
            "platform_date_math_forbidden",
            "invalid_policy",
        )
    if not isinstance(policy, dict) or policy.get("type") != "dev.ucp.shopping.policy.return":
        return ReturnPolicyEvaluation(False, "invalid_policy_type", "invalid_policy")

    eligibility = policy.get("eligibility")
    if eligibility is not None and not isinstance(eligibility, dict):
        return ReturnPolicyEvaluation(False, "invalid_eligibility_object", "invalid_policy")

    elig_type: str | None = None
    if isinstance(eligibility, dict):
        raw_type = eligibility.get("type")
        if not isinstance(raw_type, str) or not raw_type.strip():
            return ReturnPolicyEvaluation(False, "missing_eligibility_type", "invalid_policy")
        elig_type = raw_type.strip()

        if elig_type == "window":
            duration = eligibility.get("duration")
            anchor = eligibility.get("anchor")
            if not isinstance(duration, str) or not UCP_ISO8601_DURATION_RE.match(duration):
                return ReturnPolicyEvaluation(False, "invalid_window_duration", "invalid_policy")
            if not isinstance(anchor, str) or not anchor.strip():
                return ReturnPolicyEvaluation(False, "missing_window_anchor", "invalid_policy")
            exp_raw = eligibility.get("expires_at")
            if exp_raw is not None:
                if not isinstance(exp_raw, str):
                    return ReturnPolicyEvaluation(False, "invalid_expires_at", "invalid_policy")
                try:
                    datetime.fromisoformat(exp_raw.replace("Z", "+00:00"))
                except ValueError:
                    return ReturnPolicyEvaluation(False, "invalid_expires_at", "invalid_policy")
        elif elig_type in {"unlimited", "not_accepted"}:
            if any(k in eligibility for k in ("duration", "anchor", "expires_at")):
                return ReturnPolicyEvaluation(
                    False, f"window_fields_forbidden_on_{elig_type}", "invalid_policy"
                )
            if elig_type == "not_accepted" and any(
                k in policy for k in ("supported_resolutions", "methods", "fees")
            ):
                return ReturnPolicyEvaluation(
                    False, "resolutions_methods_fees_forbidden_on_not_accepted", "invalid_policy"
                )

    fees = policy.get("fees")
    if fees is not None:
        if not isinstance(fees, list) or not fees:
            return ReturnPolicyEvaluation(False, "invalid_fees_list", "invalid_policy")
        for fee in fees:
            if not isinstance(fee, dict):
                return ReturnPolicyEvaluation(False, "invalid_fee_entry", "invalid_policy")
            fee_type = fee.get("type")
            if not isinstance(fee_type, str) or not REVERSE_DOMAIN_FEE_RE.match(fee_type):
                return ReturnPolicyEvaluation(False, "invalid_fee_type", "invalid_policy")
            has_amount = "amount" in fee
            has_bps = "basis_points" in fee
            if has_amount and has_bps:
                return ReturnPolicyEvaluation(
                    False, "fee_amount_and_basis_points_mutually_exclusive", "invalid_policy"
                )
            if "max_amount" in fee and not has_bps:
                return ReturnPolicyEvaluation(
                    False, "fee_max_amount_requires_basis_points", "invalid_policy"
                )
            if has_amount and (type(fee["amount"]) is not int or fee["amount"] < 0):
                return ReturnPolicyEvaluation(False, "invalid_fee_amount", "invalid_policy")
            if has_bps and (
                type(fee["basis_points"]) is not int or not (1 <= fee["basis_points"] <= 10000)
            ):
                return ReturnPolicyEvaluation(False, "invalid_fee_basis_points", "invalid_policy")
            needs_display = (fee_type not in UCP_WELL_KNOWN_RETURN_FEES) or (
                not has_amount and not has_bps
            )
            if needs_display and (
                not isinstance(fee.get("display_text"), str) or not fee["display_text"].strip()
            ):
                return ReturnPolicyEvaluation(
                    False, "missing_required_fee_display_text", "invalid_policy"
                )

    if elig_type is None or elig_type not in UCP_RETURN_ELIGIBILITY_TYPES:
        return ReturnPolicyEvaluation(
            True, "verified", "unstructured_or_unknown_no_inference"
        )
    if elig_type == "not_accepted":
        return ReturnPolicyEvaluation(True, "verified", "not_accepted")
    if elig_type == "unlimited":
        return ReturnPolicyEvaluation(True, "verified", "unlimited_time_bound")

    assert isinstance(eligibility, dict)
    exp_str = eligibility.get("expires_at")
    if not exp_str:
        return ReturnPolicyEvaluation(
            True, "verified", "window_terms_only_no_platform_date_math"
        )
    if now_iso is not None:
        exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
        now_dt = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
        if now_dt > exp_dt:
            return ReturnPolicyEvaluation(
                True,
                "verified",
                "window_floor_lapsed_not_prohibited",
                authoritative_expires_at=exp_str,
            )
    return ReturnPolicyEvaluation(
        True, "verified", "window_open", authoritative_expires_at=exp_str
    )


@dataclass(frozen=True)
class CheckoutItemSourceDecision:
    """Offline UCP `create_checkout` item source disjunction & precedence check (PR #940)."""

    accepted: bool
    reason: str
    effective_source: Literal["cart_id", "line_items", "none"] = "none"
    resolved_items: tuple[dict[str, Any], ...] = ()


def validate_ucp_checkout_item_source(
    payload: dict[str, Any],
    *,
    operation: Literal["create", "update", "complete", "response"],
    cart_capability_negotiated: bool = False,
    cart_items: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> CheckoutItemSourceDecision:
    """Enforce UCP PR #940 (`allow cart-only checkout creation`):

    1. `cart_id` is create-only input (`ucp_request: {create: optional, update: omit, complete: omit}`
       and omitted from responses).
    2. On `create`, at least one of `line_items` or `cart_id` is required (`anyOf`).
    3. If `cart_id` is provided when `dev.ucp.shopping.cart` capability is NOT negotiated, the
       Business MUST reject the request and MUST NOT silently fall back to inline `line_items`.
    4. When both `cart_id` and `line_items` are present on `create` and Cart capability is negotiated,
       Cart contents take precedence.
    """
    if not isinstance(payload, dict):
        return CheckoutItemSourceDecision(False, "invalid_checkout_payload")

    has_cart_id = "cart_id" in payload and payload["cart_id"] is not None
    has_line_items = "line_items" in payload and payload["line_items"] is not None

    if operation != "create" and has_cart_id:
        return CheckoutItemSourceDecision(False, "cart_id_only_allowed_on_create")

    if operation == "create":
        if not has_cart_id and not has_line_items:
            return CheckoutItemSourceDecision(False, "missing_line_items_and_cart_id")
        if has_cart_id:
            raw_cart_id = payload["cart_id"]
            if not isinstance(raw_cart_id, str) or not raw_cart_id.strip():
                return CheckoutItemSourceDecision(False, "invalid_cart_id")
            if not cart_capability_negotiated:
                return CheckoutItemSourceDecision(False, "cart_capability_not_negotiated")
            if cart_items is None or not len(cart_items):
                return CheckoutItemSourceDecision(False, "cart_not_found_or_empty")
            return CheckoutItemSourceDecision(
                True,
                "verified_cart_precedence" if has_line_items else "verified_cart_only",
                "cart_id",
                tuple(cart_items),
            )
        line_items = payload.get("line_items")
        if not isinstance(line_items, list) or not line_items:
            return CheckoutItemSourceDecision(False, "empty_or_invalid_line_items")
        return CheckoutItemSourceDecision(
            True, "verified_inline_line_items", "line_items", tuple(line_items)
        )

    if has_line_items:
        line_items = payload.get("line_items")
        if not isinstance(line_items, list):
            return CheckoutItemSourceDecision(False, "empty_or_invalid_line_items")
        return CheckoutItemSourceDecision(
            True, "verified", "line_items", tuple(line_items)
        )
    return CheckoutItemSourceDecision(True, "verified", "none", ())


@dataclass(frozen=True)
class AcceleratedIdPSubjectTokenDecision:
    """Offline UCP Accelerated IdP `subject_token` user-binding & claim-scope check (#783, #970)."""

    accepted: bool
    reason: str
    fallback_to_direct_oauth: bool
    missing_claims: tuple[str, ...] = ()


def validate_ucp_accelerated_idp_subject_token(
    *,
    acting_session_user_id: str | None,
    token_subject_user_id: str | None,
    is_service_account_token: bool = False,
    token_scopes: set[str] | frozenset[str] = frozenset(),
    required_claims: set[str] | frozenset[str] = frozenset(),
    user_idp_consent_granted: bool = False,
) -> AcceleratedIdPSubjectTokenDecision:
    """Enforce UCP PR #783 & Issue #970 (`Subject Token User Binding` in Accelerated IdP Flow):

    1. The `subject_token` submitted in RFC 8693 token exchange MUST represent the user currently
       acting in the platform session (`token_subject_user_id == acting_session_user_id`).
    2. Platforms MUST NOT substitute or reuse a token belonging to a different user, nor use a
       shared/service-account token.
    3. The user MUST have granted IdP consent (platform-level or per-business), and the token scopes
       MUST cover all business-declared `required_claims` (e.g., `email`, `profile`).
    4. When no suitable token exists for the current user, the platform MUST fall back to the
       standard OAuth authorization code flow (`fallback_to_direct_oauth=True`).
    """
    if not isinstance(acting_session_user_id, str) or not acting_session_user_id.strip():
        return AcceleratedIdPSubjectTokenDecision(False, "missing_acting_session_user", True)
    if is_service_account_token:
        return AcceleratedIdPSubjectTokenDecision(False, "service_account_token_forbidden", True)
    if not isinstance(token_subject_user_id, str) or not token_subject_user_id.strip():
        return AcceleratedIdPSubjectTokenDecision(False, "no_subject_token_for_user", True)
    if token_subject_user_id.strip() != acting_session_user_id.strip():
        return AcceleratedIdPSubjectTokenDecision(
            False, "cross_user_token_substitution_forbidden", True
        )
    if not user_idp_consent_granted:
        return AcceleratedIdPSubjectTokenDecision(False, "missing_user_idp_consent", True)

    missing = tuple(sorted(set(required_claims) - set(token_scopes)))
    if missing:
        return AcceleratedIdPSubjectTokenDecision(
            False, "missing_required_claim_scopes", True, missing
        )
    return AcceleratedIdPSubjectTokenDecision(
        True, "verified_user_bound_subject_token", False, ()
    )


@dataclass(frozen=True)
class StripeOCATransitionDecision:
    """Offline Stripe Orchestrated Commerce Agreement (`/v2/orchestrated_commerce/agreements`) state check."""

    accepted: bool
    reason: str
    next_state: Literal["none", "created", "partially_confirmed", "confirmed", "terminated"]
    terminated_by: Literal["seller", "agent"] | None = None


def validate_stripe_oca_transition(
    *,
    current_state: Literal["none", "created", "partially_confirmed", "confirmed", "terminated"],
    action: Literal["initiate", "confirm", "terminate"],
    actor: Literal["seller", "agent"],
    terminated_by: Literal["seller", "agent"] | None = None,
    seller_verified_by_agent: bool = False,
) -> StripeOCATransitionDecision:
    """Enforce Stripe Embedded Commerce OCA lifecycle rules (`docs.stripe.com/agentic-commerce/agents/embedded.md`):

    1. Only a seller can initiate a brand-new OCA (`current_state == "none"`).
    2. Once an OCA reaches `partially_confirmed`, the agent must verify the seller (`seller_verified_by_agent`)
       before calling `/v2/orchestrated_commerce/agreements/{id}/confirm` to reach `confirmed`.
    3. Either the seller or the agent can call `/terminate` on an existing agreement.
    4. After termination (`current_state == "terminated"`), ONLY the party that terminated the OCA
       can initiate a new agreement (`actor == terminated_by`).
    """
    if action == "initiate":
        if current_state == "none":
            if actor != "seller":
                return StripeOCATransitionDecision(
                    False, "agent_cannot_initiate_initial_oca", current_state, terminated_by
                )
            return StripeOCATransitionDecision(
                True, "ok_seller_initiated_oca", "partially_confirmed", None
            )
        if current_state == "terminated":
            if terminated_by not in {"seller", "agent"} or actor != terminated_by:
                return StripeOCATransitionDecision(
                    False,
                    "only_terminating_party_can_reinitiate_oca",
                    current_state,
                    terminated_by,
                )
            return StripeOCATransitionDecision(
                True, "ok_reinitiated_by_terminating_party", "partially_confirmed", None
            )
        return StripeOCATransitionDecision(
            False, "oca_already_active", current_state, terminated_by
        )

    if action == "confirm":
        if current_state != "partially_confirmed":
            return StripeOCATransitionDecision(
                False, "confirm_requires_partially_confirmed_state", current_state, terminated_by
            )
        if actor != "agent":
            return StripeOCATransitionDecision(
                False, "only_agent_can_confirm_partially_confirmed_oca", current_state, terminated_by
            )
        if not seller_verified_by_agent:
            return StripeOCATransitionDecision(
                False, "seller_verification_required_before_confirm", current_state, terminated_by
            )
        return StripeOCATransitionDecision(True, "ok_oca_confirmed", "confirmed", None)

    if action == "terminate":
        if current_state not in {"created", "partially_confirmed", "confirmed"}:
            return StripeOCATransitionDecision(
                False, "cannot_terminate_inactive_oca", current_state, terminated_by
            )
        return StripeOCATransitionDecision(
            True, "ok_oca_terminated", "terminated", actor
        )

    return StripeOCATransitionDecision(False, "unknown_oca_action", current_state, terminated_by)


@dataclass(frozen=True)
class StripeSFTPBatchAndItemDecision:
    """Offline Stripe SFTP catalog ingestion manifest barrier & `disable_checkout` guard."""

    batch_ready: bool
    checkout_allowed: bool
    reason: str
    redirect_url: str | None = None


def validate_stripe_sftp_batch_and_checkout_eligibility(
    *,
    manifest: dict[str, Any] | None,
    present_shard_filenames: set[str] | frozenset[str],
    feed_type: Literal["master", "delta"],
    item_row: dict[str, Any],
    attempt_delegated_checkout: bool = False,
) -> StripeSFTPBatchAndItemDecision:
    """Enforce Stripe SFTP Catalog Ingestion & Embedded Checkout rules (`sftp-catalog-ingestion.md`):

    1. `manifest.json` MUST be uploaded last and acts as the batch completion barrier; shards MUST NOT
       be ingested if `manifest` is missing or any listed shard in `shards` is absent.
    2. If `item_row.get("delete") is True`, the product is marked deleted and cannot enter checkout.
    3. If `item_row.get("disable_checkout") is True`, the product is discovery-only; attempting to
       create a Delegated Checkout `RequestedSession` is forbidden and the agent MUST redirect the
       buyer to `item_row["link"]`.
    """
    if not isinstance(manifest, dict):
        return StripeSFTPBatchAndItemDecision(
            False, False, "missing_manifest_completion_barrier"
        )
    shards = manifest.get("shards")
    total_shards = manifest.get("total_shards")
    if (
        not isinstance(shards, list)
        or not shards
        or type(total_shards) is not int
        or total_shards != len(shards)
    ):
        return StripeSFTPBatchAndItemDecision(False, False, "invalid_manifest_shard_count")
    for shard in shards:
        fname = shard.get("filename") if isinstance(shard, dict) else None
        if not isinstance(fname, str) or fname not in present_shard_filenames:
            return StripeSFTPBatchAndItemDecision(False, False, "incomplete_shard_upload")

    if feed_type not in {"master", "delta"}:
        return StripeSFTPBatchAndItemDecision(False, False, "invalid_feed_type")

    if item_row.get("delete") is True:
        return StripeSFTPBatchAndItemDecision(True, False, "item_explicitly_deleted")

    if item_row.get("disable_checkout") is True:
        link_url = item_row.get("link")
        if attempt_delegated_checkout:
            return StripeSFTPBatchAndItemDecision(
                True,
                False,
                "discovery_only_item_must_redirect_to_link",
                redirect_url=link_url if isinstance(link_url, str) else None,
            )
        return StripeSFTPBatchAndItemDecision(
            True,
            False,
            "discovery_only_redirect_ready",
            redirect_url=link_url if isinstance(link_url, str) else None,
        )

    return StripeSFTPBatchAndItemDecision(True, True, "eligible_for_delegated_checkout")


@dataclass(frozen=True)
class WebMCPToolCallDecision:
    """Offline Stripe WebMCP browser payment tool guard (`docs.stripe.com/agentic-commerce/agents/webmcp.md`)."""

    allowed: bool
    reason: str


def validate_webmcp_payment_tool_call(
    *,
    tool_name: str,
    has_consequential_hint: bool,
    user_confirmed_after_final_amount: bool,
    schema_epoch_at_discovery: int,
    current_form_schema_epoch: int,
    is_affirm_webview_automation: bool = False,
) -> WebMCPToolCallDecision:
    """Enforce Stripe WebMCP & Embedded Checkout browser agent safety rules (`webmcp.md`, `embedded.md`):

    1. Agents MUST NOT programmatically interact with the Affirm loan application UI inside the webview
       (`affirm_webview_programmatic_interaction_forbidden`).
    2. Selecting a payment method or mutating the form changes required fields; if `schema_epoch_at_discovery`
       does not match `current_form_schema_epoch`, the agent MUST re-discover tools before invoking
       (`stale_tool_schema_rediscovery_required`).
    3. Tools marked with `consequentialHint` submit payments or mutate irreversible state; the hint itself
       is NOT user confirmation, and the agent MUST obtain explicit user confirmation after displaying
       the final amount (`consequential_tool_requires_explicit_user_confirmation`).
    """
    if not isinstance(tool_name, str) or not tool_name.strip():
        return WebMCPToolCallDecision(False, "invalid_tool_name")
    if is_affirm_webview_automation:
        return WebMCPToolCallDecision(
            False, "affirm_webview_programmatic_interaction_forbidden"
        )
    if schema_epoch_at_discovery != current_form_schema_epoch:
        return WebMCPToolCallDecision(False, "stale_tool_schema_rediscovery_required")
    if has_consequential_hint and not user_confirmed_after_final_amount:
        return WebMCPToolCallDecision(
            False, "consequential_tool_requires_explicit_user_confirmation"
        )
    return WebMCPToolCallDecision(True, "verified_webmcp_tool_call")


@dataclass(frozen=True)
class ATDRPEvidencePackDecision:
    """Offline ACP ATDRP Section 7.4a evidence-pack admissibility decision (PR #316)."""

    admissibility: Literal[
        "admissible_verified",
        "inadmissible_tamper",
        "pending_key_resolution",
        "mandate_signed_facts_only",
        "consistency_check_only",
        "insufficient_for_expiry_without_independent_timestamp",
        "uncorroborated_self_assertion",
        "not_responded_silence_is_not_acceptance",
        "work_acceptance_insufficient",
    ]
    can_overturn: bool


def evaluate_atdrp_evidence_pack_admissibility(
    verification_summary: dict[str, Any],
    *,
    claim_type: Literal["general", "expiry", "work_acceptance"] = "general",
    issuer_key_matched_out_of_band: bool = False,
    has_independent_network_timestamp: bool = False,
    work_acceptance: dict[str, Any] | None = None,
) -> ATDRPEvidencePackDecision:
    """Enforce ACP PR #316 Section 7.4a (`Evidence-pack verdicts / admissibility`) fail-closed rules:

    1. `digest_ok: False` or `rfc3161_verified: False` -> `inadmissible_tamper` (never supports `overturn`).
    2. `verification_status == "key_unresolved"` -> `pending_key_resolution` (distinct from `signature_invalid`).
    3. `producer_present: False` -> `mandate_signed_facts_only`.
    4. `producer_trusted: False` -> `consistency_check_only` (cannot be sole basis for `overturn`).
    5. `claim_type == "expiry"` with `anchors_verified == 0` and `rfc3161_claimed == False` requires an
       independent PSP/network timestamp (`insufficient_for_expiry_without_independent_timestamp`).
    6. `self_asserted_only: True` requires out-of-band issuer key confirmation (`uncorroborated_self_assertion`).
    7. For `work_acceptance`, `no_record: True` maps to `not_responded_silence_is_not_acceptance`
       (buyer silence is never positive acceptance); otherwise requires `pre_committed_criteria`,
       `checker_key != producer_key`, and `not_evaluated_count == 0`.
    """
    if (
        verification_summary.get("digest_ok") is False
        or verification_summary.get("rfc3161_verified") is False
    ):
        return ATDRPEvidencePackDecision("inadmissible_tamper", False)

    if verification_summary.get("verification_status") == "key_unresolved":
        return ATDRPEvidencePackDecision("pending_key_resolution", False)

    if verification_summary.get("producer_present") is False:
        return ATDRPEvidencePackDecision("mandate_signed_facts_only", False)

    if verification_summary.get("producer_trusted") is False:
        return ATDRPEvidencePackDecision("consistency_check_only", False)

    if (
        claim_type == "expiry"
        and verification_summary.get("anchors_verified", 0) == 0
        and not verification_summary.get("rfc3161_claimed", False)
        and not has_independent_network_timestamp
    ):
        return ATDRPEvidencePackDecision(
            "insufficient_for_expiry_without_independent_timestamp", False
        )

    if verification_summary.get("self_asserted_only") is True and not issuer_key_matched_out_of_band:
        return ATDRPEvidencePackDecision("uncorroborated_self_assertion", False)

    if claim_type == "work_acceptance" or work_acceptance is not None:
        wa = work_acceptance or {}
        if wa.get("no_record") is True:
            return ATDRPEvidencePackDecision(
                "not_responded_silence_is_not_acceptance", False
            )
        checker_key = wa.get("checker_key")
        producer_key = wa.get("producer_key")
        if (
            wa.get("pre_committed_criteria") is not True
            or not isinstance(checker_key, str)
            or not checker_key.strip()
            or checker_key == producer_key
            or wa.get("not_evaluated_count", 0) != 0
        ):
            return ATDRPEvidencePackDecision("work_acceptance_insufficient", False)

    return ATDRPEvidencePackDecision("admissible_verified", True)


@dataclass(frozen=True)
class UCPDeferredPaymentAndTotalsDecision:
    """Result of verifying UCP Oct 19 commits (#881, #755, #681) and PR #912."""

    allowed: bool
    reason: str


def verify_ucp_deferred_payment_terms_and_totals(
    *,
    is_fully_deferred_payment_term: bool,
    selected_term_id: str | None,
    payment_object: dict[str, Any] | None,
    subtotal_minor: int,
    shipping_cost_minor: int,
    totals_fulfillment_minor: int,
    totals_discount_minor: int,
    totals_total_minor: int,
    applied_discounts: list[dict[str, Any]] | None = None,
    checkout_status: str = "ready_for_complete",
    continue_url: str | None = None,
) -> UCPDeferredPaymentAndTotalsDecision:
    """Enforce UCP Oct 19 commits (#881 c1306fe3760e, #755 6f7ccabc8e9e) and PR #912:

    1. `#881` (`payment-terms.md`): When completing a checkout under a fully deferred payment term
       requiring no upfront capture or instrument guarantee, `selected_term_id` is omitted and the
       Platform MUST provide an empty payment object (`"payment": {}`) in the complete request.
    2. `#755` (`discount.md`): When a free-shipping or shipping discount (`totals_discount_minor > 0`)
       is applied to `shipping_cost_minor > 0`, `totals` MUST set `fulfillment == shipping_cost_minor`
       alongside the negative `discount` adjustment rather than zeroing `fulfillment` and subtracting
       the discount a second time (`free_shipping_double_counted_in_totals`). Furthermore, for each
       `applied_discount` in `applied_discounts`, if `allocations` is present, the sum of
       `allocations[].amount` MUST equal `applied_discount["amount"]` (`discount_allocations_sum_mismatch`).
    3. `PR #912` (`checkout_resp.json`): When `checkout_status == "requires_escalation"`, `continue_url`
       MUST be present and use `https://` (`missing_continue_url_on_requires_escalation`).
    """
    if checkout_status == "requires_escalation":
        parsed_cont = urlsplit((continue_url or "").strip())
        if parsed_cont.scheme.lower() != "https" or not parsed_cont.hostname:
            return UCPDeferredPaymentAndTotalsDecision(
                False, "missing_continue_url_on_requires_escalation"
            )

    if is_fully_deferred_payment_term:
        if selected_term_id is not None or payment_object != {}:
            return UCPDeferredPaymentAndTotalsDecision(
                False, "deferred_term_requires_empty_payment_object"
            )

    if shipping_cost_minor > 0 and totals_discount_minor > 0:
        if totals_fulfillment_minor == 0:
            return UCPDeferredPaymentAndTotalsDecision(
                False, "free_shipping_double_counted_in_totals"
            )
    expected_total = subtotal_minor + totals_fulfillment_minor - totals_discount_minor
    if totals_total_minor != expected_total:
        return UCPDeferredPaymentAndTotalsDecision(False, "totals_conservation_mismatch")

    for disc in applied_discounts or []:
        if "allocations" in disc and disc["allocations"] is not None:
            allocs = disc["allocations"]
            if not isinstance(allocs, list):
                return UCPDeferredPaymentAndTotalsDecision(
                    False, "discount_allocations_sum_mismatch"
                )
            alloc_sum = sum(int(item.get("amount", 0)) for item in allocs if isinstance(item, dict))
            if alloc_sum != int(disc.get("amount", 0)):
                return UCPDeferredPaymentAndTotalsDecision(
                    False, "discount_allocations_sum_mismatch"
                )

    return UCPDeferredPaymentAndTotalsDecision(True, "verified_ucp_deferred_payment_and_totals")


def verify_ucp_identity_grant_and_location_headers(
    *,
    grant_iat: int,
    grant_exp: int,
    grant_jti: str,
    grant_aud: Any,
    expected_token_endpoint: str,
    now: int,
    seen_grant_jti: set[str],
    is_grant_relayed_or_stored: bool = False,
    location_rest_headers: dict[str, str] | None = None,
    ecdsa_alg: Literal["ES256", "ES384"] = "ES256",
    ecdsa_signature_bytes: bytes = b"\x01" * 64,
) -> UCPDeferredPaymentAndTotalsDecision:
    """Enforce UCP Oct 19 commits (#731 bb92f113a053, #784 0cccc20f7801) and PR #963:

    1. `#731` (`identity-linking.md`): JWT authorization grants SHOULD have `0 < exp - iat <= 60`
       (`jwt_grant_lifetime_exceeds_60s`), MUST enforce single-use via `jti` tracking within the
       validity window (`jwt_grant_jti_replayed_or_missing`), and MUST NOT be stored, forwarded, or
       relayed across audiences (`jwt_grant_relay_or_audience_mismatch`).
    2. `#784` (`location.md`): Location REST binding (`search_locations`, `lookup_locations`) MUST
       include `Request-Id` and `UCP-Agent` headers (`missing_location_rest_headers`).
    3. `PR #963` (`signing-reference.md`): RFC 9421 §3.3.4 (`ecdsa-p256-sha256` / `ES256`) and §3.3.5
       (`ecdsa-p384-sha384` / `ES384`) use fixed-length raw `r || s` concatenation (64 bytes for P-256,
       96 bytes for P-384), forbidding variable-length ASN.1 DER sequences (`0x30 ...`).
    """
    if is_grant_relayed_or_stored or type(grant_aud) is not str or grant_aud != expected_token_endpoint:
        return UCPDeferredPaymentAndTotalsDecision(
            False, "jwt_grant_relay_or_audience_mismatch"
        )
    lifetime = grant_exp - grant_iat
    if lifetime <= 0 or lifetime > 60 or not (grant_iat <= now < grant_exp):
        return UCPDeferredPaymentAndTotalsDecision(False, "jwt_grant_lifetime_exceeds_60s")
    if not isinstance(grant_jti, str) or len(grant_jti.strip()) < 8 or grant_jti in seen_grant_jti:
        return UCPDeferredPaymentAndTotalsDecision(
            False, "jwt_grant_jti_replayed_or_missing"
        )

    if location_rest_headers is not None:
        lower_hdrs = {k.lower(): v.strip() for k, v in location_rest_headers.items() if isinstance(v, str)}
        req_id = lower_hdrs.get("request-id", "")
        ucp_agent = lower_hdrs.get("ucp-agent", "")
        if not req_id or "profile=" not in ucp_agent:
            return UCPDeferredPaymentAndTotalsDecision(False, "missing_location_rest_headers")

    expected_len = 64 if ecdsa_alg == "ES256" else 96
    if len(ecdsa_signature_bytes) != expected_len:
        if len(ecdsa_signature_bytes) in {70, 71, 72, 102, 103, 104} and ecdsa_signature_bytes[:1] == b"\x30":
            return UCPDeferredPaymentAndTotalsDecision(
                False, "asn1_der_ecdsa_encoding_forbidden_use_raw_r_s"
            )
        return UCPDeferredPaymentAndTotalsDecision(
            False, "invalid_rfc9421_ecdsa_raw_signature_length"
        )

    seen_grant_jti.add(grant_jti)
    return UCPDeferredPaymentAndTotalsDecision(True, "verified_ucp_grant_headers_and_ecdsa")


def verify_ap2_sd_jwt_kb_terminal_chain(
    *,
    root_has_visible_cnf: bool,
    root_sd_hidden_keys: set[str] | frozenset[str],
    terminal_typ: str,
    terminal_aud: str | None,
    terminal_nonce: str | None,
    expected_aud: str,
    expected_nonce: str,
) -> UCPDeferredPaymentAndTotalsDecision:
    """Enforce Google AP2 PR #369 (`tests/mandates/test_conformance.py`) SD-JWT+KB delegation invariants:

    1. The root human-signed SD-JWT MUST bind the agent public key in a top-level visible `cnf` claim
       and MUST NOT conceal `cnf` inside `_sd` disclosures (`root_sd_jwt_cnf_hidden_in_sd_forbidden`).
    2. In `kb_sd_jwt`, a token carrying `cnf` receives `typ="kb+sd-jwt+kb"` (`TYP_INTERMEDIATE`).
       A verifier that only enforces `expected_aud` and `expected_nonce` when `typ == "kb+sd-jwt"`
       silently skips audience and nonce verification on the terminal hop when `cnf` is present.
       The verifier MUST enforce `terminal_aud == expected_aud` and `terminal_nonce == expected_nonce`
       on the final token in the chain regardless of whether `terminal_typ` is `"kb+sd-jwt"` or
       `"kb+sd-jwt+kb"` (`kb_sd_jwt_terminal_aud_nonce_bypass_blocked`).
    """
    if not root_has_visible_cnf or "cnf" in root_sd_hidden_keys:
        return UCPDeferredPaymentAndTotalsDecision(
            False, "root_sd_jwt_cnf_hidden_in_sd_forbidden"
        )
    if terminal_typ not in {"kb+sd-jwt", "kb+sd-jwt+kb"}:
        return UCPDeferredPaymentAndTotalsDecision(False, "invalid_sd_jwt_kb_terminal_typ")
    if terminal_aud != expected_aud or terminal_nonce != expected_nonce:
        return UCPDeferredPaymentAndTotalsDecision(
            False, "kb_sd_jwt_terminal_aud_nonce_bypass_blocked"
        )
    return UCPDeferredPaymentAndTotalsDecision(True, "verified_ap2_sd_jwt_kb_terminal_chain")


def main() -> int:
    """Assess synthetic declarations; exit 1 for blocked and 2 for invalid metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument", choices=sorted(INSTRUMENTS), default="link")
    parser.add_argument("--platform-environment", choices=["sandbox", "production"], default="sandbox")
    parser.add_argument("--business-environment", choices=["sandbox", "production"], default="sandbox")
    parser.add_argument("--relationship", choices=["confirmed", "missing", "unknown"], default="unknown")
    parser.add_argument("--business-ucp-version", default=REVIEWED_UCP_VERSION)
    parser.add_argument("--business-handler-version", default=REVIEWED_HANDLER_VERSION)
    args = parser.parse_args()
    try:
        platform = HandlerMetadata(
            REVIEWED_UCP_VERSION, STRIPE_HANDLER, REVIEWED_HANDLER_VERSION,
            args.platform_environment, tuple(sorted(INSTRUMENTS)),
        )
        business = HandlerMetadata(
            args.business_ucp_version, STRIPE_HANDLER, args.business_handler_version,
            args.business_environment, tuple(sorted(INSTRUMENTS)),
        )
        decision = assess(
            platform, business, instrument=args.instrument, relationship=args.relationship,
        )
    except ValueError as error:
        print(json.dumps({"status": "invalid_metadata", "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({
        "kind": "offline-synthetic-metadata-preflight",
        "policy_checked_on": POLICY_CHECKED_ON.isoformat(),
        "policy_source": SOURCE_URL,
        "reviewed_versions_are": "documentation examples, not universal latest versions",
        "platform": asdict(platform),
        "business": asdict(business),
        "instrument": args.instrument,
        "relationship": args.relationship,
        "decision": asdict(decision),
        "remaining_checks": [
            "authenticated discovery and merchant configuration",
            "region, account access and provider credentials",
            "customer consent, final quote, limits, expiry and revocation",
            "payment result, reconciliation and fulfillment",
        ],
        "real_payments": False,
    }, indent=2))
    return int(decision.status == "blocked")


if __name__ == "__main__":
    raise SystemExit(main())
