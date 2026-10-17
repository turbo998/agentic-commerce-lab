"""Offline, metadata-only UCP handler preflight; never authorize or send payments."""

import argparse
import base64
import json
import posixpath
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, quote, unquote, urlsplit

POLICY_CHECKED_ON = date(2026, 10, 17)
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
