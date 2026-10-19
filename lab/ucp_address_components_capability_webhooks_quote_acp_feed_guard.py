"""Stage 50 deterministic guards for UCP Address Line Components (#981), Identity-Linking Candidate Selection (#980), Capability Event Webhooks (#938), Quote & Declared Fields (#930/#915), and ACP Host Gate / Server-Timing / Feed Update Provenance (#314/#273/#260).

Covers:
1. UCP PR #981 (`dev.shopify.common.address_line_components`):
   - Destination scope enforcement: allowed on Checkout `shipping_address` destinations
     (including shipping destinations omitting optional `type`), Checkout
     `payment.instruments[].billing_address`, and Order `fulfillment.expectations[].destination`.
     Forbidden on non-shipping destinations (`business_location` pickup) and on Cart.
   - Full-replacement & precedence rules:
     * Components win over flat lines (`street_name`/`street_number` -> `street_address`;
       `additional_information`/`district`/`subdistrict` -> `extended_address`).
     * Business never splits a flat line to manufacture structured components and never
       inserts invisible separators (`\\u200b`, `\\u2060`, `\\ufeff`, `\\u00ad`) into flat lines.
     * `address_code` is never composed into `street_address` or `extended_address`.
     * Clearing is by omission or `{}`; `null` (`None`) on `address_line_components`,
       any component field, or `address_code` is invalid.
2. UCP PR #980 (Identity-Linking 3-Step Discovery & Selection) & PR #938 (Capability Event Webhooks):
   - Candidate AS evaluation: RFC 8414 §3.1 well-known path insertion; fallback to OIDC
     Discovery ONLY on HTTP `404`; byte-for-byte `issuer` match; discarded candidates are
     surfaced/logged; every listed `authorization_servers` entry must be acceptable to the
     business because array order is a preference, not a security boundary.
   - Capability Event Webhooks (`{capability}:{name}`):
     * Subscriptions created only for pre-approved recognized platforms and signed requests.
     * Shared/broadcast capabilities (`dev.ucp.common.location.lookup`, `dev.ucp.common.directory`)
       must use thin `event.json` envelopes (`ucp`, `type`, `occurred_at`, `data` with IDs and
       `changed_sections`), never full access-controlled state, and platforms must read back
       via unfiltered `lookup_locations` before delisting on `:removed`.
     * Webhook `POST` RFC 9421 `Signature-Input` must cover `webhook-id`, `webhook-timestamp`
       (delivery attempt time within 300s window), and `ucp-agent`, and the signer must own
       the referenced resource IDs.
3. UCP PR #930 (`dev.ucp.common.quote`) & PR #915 (`declared_fields` for Checkout):
   - Quote extension: accepted quote reflected as at most/exactly one `totals[]` entry with
     `type == "quote"` and non-empty `display_text`; `proposal` and `accepted_id` omitted on
     `complete_checkout`; expired quotes (`now > expires_at`) cannot be accepted or polled;
     Order projection retains `{id, subtotal}`.
   - Declared fields: Reverse-DNS keys (`^[a-z][a-z0-9_]*(\\.[a-z0-9_]+)+$`) in response-only
     `checkout.config`; unique `required_declared_fields` at Checkout or line-item scope;
     submitted `declared_fields` must match the exact scope without cross-scope movement;
     `config`, `required_declared_fields`, and `declared_fields` must be omitted on
     `complete_checkout`.
4. ACP PR #314 (Optional Host-Side Spend Gate), PR #273 (`Server-Timing: acp;dur=<ms>`),
   and PR #260 (`feed_update_id` / `Product.last_update_id` -> `suggested_price.source`):
   - Host-side spend gate fails closed when enabled and never replaces ACP `Authorization`,
     `Signature`, `Timestamp`, or `Idempotency-Key` headers or leaks API keys into prompts.
   - `Server-Timing` uses `acp;dur=<ms>` without leaking internal topology/SQL/table identifiers.
   - Accepted product feed upserts propagate `feed_update_id` to `Product.last_update_id` on
     touched items and verify against `suggested_price.source` at checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

INVISIBLE_SEPARATOR_CHARS: tuple[str, ...] = ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad")
STREET_COMPONENT_KEYS: frozenset[str] = frozenset({"street_name", "street_number"})
EXTENDED_COMPONENT_KEYS: frozenset[str] = frozenset({"additional_information", "district", "subdistrict"})
ALL_ADDRESS_COMPONENT_KEYS: frozenset[str] = STREET_COMPONENT_KEYS | EXTENDED_COMPONENT_KEYS

CAPABILITY_EVENT_TYPE_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9_]+)+:[a-z0-9_]+$")
REVERSE_DNS_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
SERVER_TIMING_ACP_RE = re.compile(r"^acp;dur=\d+(?:\.\d+)?$")
FORBIDDEN_SERVER_TIMING_LEAK_TOKENS: tuple[str, ...] = (
    "sql",
    "postgres",
    "redis",
    "internal",
    "shard",
    "pod-",
    "vpc-",
)


@dataclass(frozen=True)
class UCPAddressLineComponentsGuardResult:
    admitted: bool
    decision_code: str
    destination_scope_valid: bool
    null_free_valid: bool
    component_precedence_valid: bool
    no_manufactured_components: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class UCPIdentitySelectionAndCapabilityWebhookGuardResult:
    admitted: bool
    decision_code: str
    identity_selection_valid: bool
    discarded_issuers_surfaced: bool
    webhook_subscription_valid: bool
    webhook_delivery_valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class UCPQuoteAndDeclaredFieldsGuardResult:
    admitted: bool
    decision_code: str
    quote_valid: bool
    declared_fields_valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ACPHostGateServerTimingFeedUpdateGuardResult:
    admitted: bool
    decision_code: str
    host_spend_gate_valid: bool
    server_timing_valid: bool
    feed_update_provenance_valid: bool
    reasons: tuple[str, ...]


def evaluate_ucp_address_line_components_guard(
    context: Mapping[str, Any],
) -> UCPAddressLineComponentsGuardResult:
    """Enforce UCP PR #981 (`dev.shopify.common.address_line_components`) rules."""
    reasons: list[str] = []
    destination_scope_valid = True
    null_free_valid = True
    component_precedence_valid = True
    no_manufactured_components = True

    capability_target = str(context.get("capability_target", "checkout")).strip().lower()
    destination_type = str(context.get("destination_type", "shipping_address")).strip().lower()
    method_type = str(context.get("method_type", "shipping")).strip().lower()
    has_extension_fields = (
        "address_line_components" in context or "address_code" in context
    )

    # 1. Scope check: Cart is not extended; pickup / business_location must not carry extension properties
    if capability_target == "cart" and has_extension_fields:
        destination_scope_valid = False
        reasons.append(
            "ADDRESS_COMPONENTS_ON_CART_FORBIDDEN: Cart has no address-bearing member and must not carry `address_line_components` or `address_code`"
        )
    if (
        destination_type in {"business_location", "pickup_location"}
        or method_type == "pickup"
    ) and has_extension_fields:
        destination_scope_valid = False
        reasons.append(
            f"ADDRESS_COMPONENTS_NON_SHIPPING_DESTINATION_FORBIDDEN: destination_type='{destination_type}' / method_type='{method_type}' must not carry `address_line_components` or `address_code`"
        )

    # 2. Null check: clearing is by omission or `{}`, never `None`
    if "address_code" in context and context.get("address_code") is None:
        null_free_valid = False
        reasons.append("ADDRESS_CODE_NULL_FORBIDDEN: `address_code` must be omitted to clear; `null` is invalid")

    raw_components = context.get("address_line_components", {})
    if "address_line_components" in context and raw_components is None:
        null_free_valid = False
        reasons.append(
            "ADDRESS_LINE_COMPONENTS_NULL_WRAPPER_FORBIDDEN: `address_line_components` wrapper does not accept `null`"
        )
    elif isinstance(raw_components, Mapping):
        for k, v in raw_components.items():
            if k not in ALL_ADDRESS_COMPONENT_KEYS:
                null_free_valid = False
                reasons.append(f"ADDRESS_COMPONENT_UNKNOWN_KEY_FORBIDDEN: unknown key '{k}'")
            elif v is None or not isinstance(v, str):
                null_free_valid = False
                reasons.append(
                    f"ADDRESS_COMPONENT_NULL_OR_NON_STRING_FORBIDDEN[{k}]: component values must be strings, never `null`"
                )

    # 3. Precedence & non-inference rules
    if bool(context.get("business_split_flat_line_to_infer_components", False)):
        no_manufactured_components = False
        reasons.append(
            "ADDRESS_FLAT_LINE_SPLITTING_INFERENCE_FORBIDDEN: business must not split flat `street_address` or `extended_address` to manufacture structured components"
        )

    composed_street = str(context.get("composed_street_address", ""))
    composed_extended = str(context.get("composed_extended_address", ""))
    address_code_val = str(context.get("address_code") or "").strip()

    if any(ch in composed_street or ch in composed_extended for ch in INVISIBLE_SEPARATOR_CHARS):
        component_precedence_valid = False
        reasons.append(
            "ADDRESS_INVISIBLE_SEPARATOR_IN_FLAT_LINE_FORBIDDEN: returned flat lines must not contain legacy invisible separator characters"
        )

    if address_code_val and bool(context.get("address_code_composed_into_flat_line", False)):
        component_precedence_valid = False
        reasons.append(
            "ADDRESS_CODE_COMPOSED_INTO_STREET_LINE_FORBIDDEN: `address_code` identifies the delivery point independently and must never be composed into flat street lines"
        )

    if bool(context.get("flat_line_overrode_submitted_components", False)):
        component_precedence_valid = False
        reasons.append(
            "ADDRESS_COMPONENTS_PRECEDENCE_VIOLATED: when components are sent alongside a flat line for the same group, components must win"
        )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "UCP_ADDRESS_LINE_COMPONENTS_VERIFIED"
    elif not destination_scope_valid:
        decision_code = "ADDRESS_COMPONENTS_NON_SHIPPING_OR_CART_SCOPE_BLOCKED"
    elif not null_free_valid:
        decision_code = "ADDRESS_COMPONENTS_NULL_VALUE_OR_UNKNOWN_KEY_BLOCKED"
    elif not no_manufactured_components:
        decision_code = "ADDRESS_FLAT_LINE_SPLITTING_INFERENCE_BLOCKED"
    else:
        decision_code = "ADDRESS_COMPONENTS_PRECEDENCE_OR_SEPARATOR_VIOLATION"

    return UCPAddressLineComponentsGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        destination_scope_valid=destination_scope_valid,
        null_free_valid=null_free_valid,
        component_precedence_valid=component_precedence_valid,
        no_manufactured_components=no_manufactured_components,
        reasons=tuple(reasons),
    )


def evaluate_ucp_identity_selection_and_capability_webhook_guard(
    context: Mapping[str, Any],
) -> UCPIdentitySelectionAndCapabilityWebhookGuardResult:
    """Enforce UCP PR #980 (Identity-Linking Discovery/Selection) and PR #938 (Capability Event Webhooks)."""
    reasons: list[str] = []
    identity_selection_valid = True
    discarded_issuers_surfaced = True
    webhook_subscription_valid = True
    webhook_delivery_valid = True

    # 1. Identity-Linking Discovery & Selection (UCP PR #980)
    candidates = context.get("candidate_authorization_servers", ())
    surfaced_discarded = {str(x) for x in context.get("surfaced_discarded_issuers", ())}
    valid_candidates: list[str] = []

    if isinstance(candidates, (list, tuple)) and candidates:
        for idx, cand in enumerate(candidates):
            if not isinstance(cand, Mapping):
                continue
            issuer_url = str(cand.get("candidate_issuer", "")).strip()
            metadata_issuer = str(cand.get("metadata_issuer", "")).strip()
            oauth_well_known_status = int(cand.get("oauth_well_known_status", 200))
            fell_back_to_oidc = bool(cand.get("fell_back_to_oidc", False))
            has_client_registration = bool(cand.get("has_client_registration", True))
            business_accepts_tokens_from_as = bool(cand.get("business_accepts_tokens_from_as", True))

            if not business_accepts_tokens_from_as:
                identity_selection_valid = False
                reasons.append(
                    f"IDENTITY_SELECTION_UNACCEPTED_AS_IN_LIST_BLOCKED[{issuer_url}]: array order is a preference, not a security boundary; business must only list authorization servers it accepts"
                )
            if fell_back_to_oidc and oauth_well_known_status != 404:
                identity_selection_valid = False
                reasons.append(
                    f"IDENTITY_DISCOVERY_OIDC_FALLBACK_ON_NON_404_BLOCKED[{issuer_url}]: OIDC discovery fallback is only permitted on HTTP 404, not {oauth_well_known_status}"
                )

            step_ok = (
                oauth_well_known_status in {200, 404}
                and issuer_url == metadata_issuer
                and has_client_registration
            )
            if step_ok:
                valid_candidates.append(issuer_url)
            else:
                if issuer_url not in surfaced_discarded:
                    discarded_issuers_surfaced = False
                    reasons.append(
                        f"IDENTITY_DISCOVERY_DISCARDED_CANDIDATE_SILENTLY_SKIPPED[{issuer_url}]: discarded candidate AS entries must be surfaced/logged to the operator"
                    )

        if bool(context.get("aborted_discovery_on_first_failed_candidate", False)) and len(valid_candidates) > 0:
            identity_selection_valid = False
            reasons.append(
                "IDENTITY_DISCOVERY_PREMATURE_ABORT_BLOCKED: a single failed candidate must be discarded without failing overall discovery when valid candidates remain"
            )

    # 2. Capability Event Webhooks (UCP PR #938)
    webhook_ctx = context.get("capability_webhook")
    if isinstance(webhook_ctx, Mapping):
        platform_recognized = bool(webhook_ctx.get("platform_recognized", True))
        subscription_request_signed = bool(webhook_ctx.get("subscription_request_signed", True))
        webhook_url = str(webhook_ctx.get("webhook_url", "https://platform.example/webhooks/ucp")).strip()
        webhook_url_resolves_private_ip = bool(webhook_ctx.get("webhook_url_resolves_private_ip", False))
        webhook_url_redirects = bool(webhook_ctx.get("webhook_url_redirects", False))

        if not platform_recognized or not subscription_request_signed:
            webhook_subscription_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_UNRECOGNIZED_OR_UNSIGNED_SUBSCRIPTION_BLOCKED: business creates webhook subscriptions only for recognized platforms and signed requests"
            )
        if not webhook_url.startswith("https://") or webhook_url_resolves_private_ip or webhook_url_redirects:
            webhook_subscription_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_UNSAFE_URL_BLOCKED: `config.webhook.url` must be HTTPS without redirects or special-use/private IPs"
            )

        event_type = str(webhook_ctx.get("event_type", "")).strip()
        if event_type and not CAPABILITY_EVENT_TYPE_RE.match(event_type):
            webhook_delivery_valid = False
            reasons.append(
                f"CAPABILITY_WEBHOOK_EVENT_TYPE_FORMAT_INVALID: '{event_type}' must match `{{capability}}:{{name}}`"
            )

        is_shared_broadcast_capability = bool(webhook_ctx.get("is_shared_broadcast_capability", False))
        payload_is_thin_notification = bool(webhook_ctx.get("payload_is_thin_notification", True))
        platform_mutated_state_without_readback = bool(
            webhook_ctx.get("platform_mutated_state_without_readback", False)
        )
        delisted_on_removed_without_unfiltered_lookup = bool(
            webhook_ctx.get("delisted_on_removed_without_unfiltered_lookup", False)
        )

        if is_shared_broadcast_capability and not payload_is_thin_notification:
            webhook_delivery_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_BROADCAST_FULL_SNAPSHOT_FORBIDDEN: shared/broadcast capabilities must send thin `event.json` notifications, not full entity state"
            )
        if is_shared_broadcast_capability and platform_mutated_state_without_readback:
            webhook_delivery_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_THIN_EVENT_TREATED_AS_STATE_BLOCKED: thin events signal a read; platforms must read back authoritative state before mutating"
            )
        if delisted_on_removed_without_unfiltered_lookup:
            webhook_delivery_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_REMOVED_DELIST_WITHOUT_UNFILTERED_LOOKUP_BLOCKED: platform must confirm `:removed` via an unfiltered `lookup_locations` call before delisting"
            )

        covered = {str(c).lower() for c in webhook_ctx.get("covered_components", ("webhook-id", "webhook-timestamp", "ucp-agent"))}
        required_covered = {"webhook-id", "webhook-timestamp", "ucp-agent"}
        if not required_covered.issubset(covered):
            webhook_delivery_valid = False
            reasons.append(
                f"CAPABILITY_WEBHOOK_MISSING_COVERED_COMPONENTS: Signature-Input must cover {sorted(required_covered)}"
            )

        delivery_skew_seconds = abs(int(webhook_ctx.get("delivery_timestamp_skew_seconds", 0)))
        signer_owns_resource_ids = bool(webhook_ctx.get("signer_owns_resource_ids", True))
        if delivery_skew_seconds > 300 or not signer_owns_resource_ids:
            webhook_delivery_valid = False
            reasons.append(
                "CAPABILITY_WEBHOOK_TIMESTAMP_OR_SIGNER_OWNERSHIP_INVALID: `Webhook-Timestamp` must be within 300s delivery window and signer must own the referenced IDs"
            )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "UCP_IDENTITY_SELECTION_AND_CAPABILITY_WEBHOOK_VERIFIED"
    elif not identity_selection_valid or not discarded_issuers_surfaced:
        decision_code = "UCP_IDENTITY_DISCOVERY_SELECTION_OR_SILENT_SKIP_BLOCKED"
    elif not webhook_subscription_valid:
        decision_code = "CAPABILITY_WEBHOOK_SUBSCRIPTION_SECURITY_BLOCKED"
    else:
        decision_code = "CAPABILITY_WEBHOOK_DELIVERY_OR_THIN_READBACK_BLOCKED"

    return UCPIdentitySelectionAndCapabilityWebhookGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        identity_selection_valid=identity_selection_valid,
        discarded_issuers_surfaced=discarded_issuers_surfaced,
        webhook_subscription_valid=webhook_subscription_valid,
        webhook_delivery_valid=webhook_delivery_valid,
        reasons=tuple(reasons),
    )


def evaluate_ucp_quote_and_declared_fields_guard(
    context: Mapping[str, Any],
) -> UCPQuoteAndDeclaredFieldsGuardResult:
    """Enforce UCP PR #930 (`dev.ucp.common.quote`) and PR #915 (`declared_fields`)."""
    reasons: list[str] = []
    quote_valid = True
    declared_fields_valid = True

    # 1. UCP PR #930 Quote extension checks
    quote_ctx = context.get("quote_context")
    if isinstance(quote_ctx, Mapping):
        quote_accepted = bool(quote_ctx.get("quote_accepted", False))
        quote_expired = bool(quote_ctx.get("quote_expired", False))
        polled_after_expires_at = bool(quote_ctx.get("polled_after_expires_at", False))
        complete_request_has_proposal_or_accepted_id = bool(
            quote_ctx.get("complete_request_has_proposal_or_accepted_id", False)
        )
        quote_totals_entries = quote_ctx.get("quote_totals_entries", ())

        if quote_accepted and quote_expired:
            quote_valid = False
            reasons.append("UCP_QUOTE_EXPIRED_ACCEPTANCE_BLOCKED: an expired quotation cannot be accepted")
        if polled_after_expires_at:
            quote_valid = False
            reasons.append("UCP_QUOTE_POLLING_PAST_EXPIRY_BLOCKED: asynchronous quote polling must stop at `expires_at`")
        if complete_request_has_proposal_or_accepted_id:
            quote_valid = False
            reasons.append(
                "UCP_QUOTE_BUYER_FIELDS_ON_COMPLETE_FORBIDDEN: `proposal` and `accepted_id` must be omitted on `complete_checkout`"
            )
        if quote_accepted and isinstance(quote_totals_entries, (list, tuple)):
            if len(quote_totals_entries) != 1:
                quote_valid = False
                reasons.append(
                    f"UCP_QUOTE_TOTALS_CARDINALITY_INVALID: accepted quote must be reflected as exactly 1 `type: 'quote'` entry in `totals[]`, got {len(quote_totals_entries)}"
                )
            else:
                entry = quote_totals_entries[0]
                if not isinstance(entry, Mapping) or not str(entry.get("display_text", "")).strip():
                    quote_valid = False
                    reasons.append(
                        "UCP_QUOTE_TOTAL_MISSING_DISPLAY_TEXT: `type: 'quote'` entry in `totals[]` requires non-empty `display_text`"
                    )

    # 2. UCP PR #915 Declared Fields checks
    df_ctx = context.get("declared_fields_context")
    if isinstance(df_ctx, Mapping):
        config_keys = tuple(str(k) for k in df_ctx.get("config_keys", ()))
        config_Set = set(config_keys)
        checkout_required = tuple(str(k) for k in df_ctx.get("checkout_required_declared_fields", ()))
        checkout_submitted = tuple(str(k) for k in df_ctx.get("checkout_declared_fields", ()))
        line_item_required = tuple(str(k) for k in df_ctx.get("line_item_required_declared_fields", ()))
        line_item_submitted = tuple(str(k) for k in df_ctx.get("line_item_declared_fields", ()))
        checkout_status = str(df_ctx.get("checkout_status", "incomplete")).strip()
        is_complete_checkout_request = bool(df_ctx.get("is_complete_checkout_request", False))
        complete_request_includes_declared_fields = bool(
            df_ctx.get("complete_request_includes_declared_fields", False)
        )
        schema_validation_passed = bool(df_ctx.get("schema_validation_passed", True))

        for key in (*config_keys, *checkout_required, *checkout_submitted, *line_item_required, *line_item_submitted):
            if not REVERSE_DNS_KEY_RE.match(key):
                declared_fields_valid = False
                reasons.append(f"UCP_DECLARED_FIELDS_INVALID_REVERSE_DNS_KEY[{key}]: must use Reverse-DNS format")

        if len(checkout_required) != len(set(checkout_required)) or len(line_item_required) != len(set(line_item_required)):
            declared_fields_valid = False
            reasons.append("UCP_DECLARED_FIELDS_DUPLICATE_REQUIRED_KEYS_BLOCKED: `required_declared_fields` must not contain duplicates")

        for req_key in (*checkout_required, *line_item_required):
            if req_key not in config_Set:
                declared_fields_valid = False
                reasons.append(
                    f"UCP_DECLARED_FIELDS_MISSING_CONFIG_SCHEMA[{req_key}]: every key in `required_declared_fields` must exist in `checkout.config`"
                )

        # Scope matching: submitted keys must match required_declared_fields at the same scope (no cross-scope movement)
        if set(checkout_submitted) != set(checkout_required) or set(line_item_submitted) != set(line_item_required):
            declared_fields_valid = False
            reasons.append(
                "UCP_DECLARED_FIELDS_SCOPE_MISMATCH_OR_MISSING_BLOCKED: submitted `declared_fields` keys must match `required_declared_fields` at the exact scope without moving between checkout and line_item"
            )

        if checkout_status == "ready_for_complete" and not schema_validation_passed:
            declared_fields_valid = False
            reasons.append(
                "UCP_DECLARED_FIELDS_READY_FOR_COMPLETE_WITHOUT_VALID_FIELDS_BLOCKED: all required declared fields must pass schema validation before `ready_for_complete`"
            )

        if is_complete_checkout_request and complete_request_includes_declared_fields:
            declared_fields_valid = False
            reasons.append(
                "UCP_DECLARED_FIELDS_ON_COMPLETE_REQUEST_FORBIDDEN: `config`, `required_declared_fields`, and `declared_fields` must be omitted from `complete_checkout` requests"
            )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "UCP_QUOTE_AND_DECLARED_FIELDS_VERIFIED"
    elif not quote_valid:
        decision_code = "UCP_QUOTE_EXPIRY_OR_TOTALS_CONTRACT_BLOCKED"
    else:
        decision_code = "UCP_DECLARED_FIELDS_SCOPE_OR_LIFECYCLE_BLOCKED"

    return UCPQuoteAndDeclaredFieldsGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        quote_valid=quote_valid,
        declared_fields_valid=declared_fields_valid,
        reasons=tuple(reasons),
    )


def evaluate_acp_host_gate_server_timing_and_feed_update_guard(
    context: Mapping[str, Any],
) -> ACPHostGateServerTimingFeedUpdateGuardResult:
    """Enforce ACP PR #314 (Host Spend Gate), PR #273 (Server-Timing), and PR #260 (Feed Update ID)."""
    reasons: list[str] = []
    host_spend_gate_valid = True
    server_timing_valid = True
    feed_update_provenance_valid = True

    # 1. ACP PR #314 Host-side authorization before sensitive spend steps
    host_gate = context.get("host_spend_gate")
    if isinstance(host_gate, Mapping):
        is_sensitive_spend_step = bool(host_gate.get("is_sensitive_spend_step", True))
        gate_enabled = bool(host_gate.get("gate_enabled", True))
        gate_decision_verified = bool(host_gate.get("gate_decision_verified", True))
        gate_allowed = bool(host_gate.get("gate_allowed", True))
        bypassed_acp_wire_auth_headers = bool(host_gate.get("bypassed_acp_wire_auth_headers", False))
        leaked_gate_api_key_in_model_prompt = bool(
            host_gate.get("leaked_gate_api_key_in_model_prompt", False)
        )

        if is_sensitive_spend_step and gate_enabled and (not gate_decision_verified or not gate_allowed):
            host_spend_gate_valid = False
            reasons.append(
                "ACP_HOST_SPEND_GATE_FAIL_CLOSED_DENIED: host-side spend gate denied or failed local signature verification before ACP tool call"
            )
        if bypassed_acp_wire_auth_headers or leaked_gate_api_key_in_model_prompt:
            host_spend_gate_valid = False
            reasons.append(
                "ACP_HOST_SPEND_GATE_AUTH_REPLACEMENT_OR_PROMPT_SECRET_LEAK_BLOCKED: host gate must never replace ACP wire auth headers or expose secrets in model prompts"
            )

    # 2. ACP PR #273 Server-Timing header hygiene
    server_timing = context.get("server_timing_header")
    if server_timing is not None:
        st_str = str(server_timing).strip()
        lowered_st = st_str.lower()
        if not SERVER_TIMING_ACP_RE.match(st_str) or any(
            tok in lowered_st for tok in FORBIDDEN_SERVER_TIMING_LEAK_TOKENS
        ):
            server_timing_valid = False
            reasons.append(
                f"ACP_SERVER_TIMING_METRIC_OR_TOPOLOGY_LEAK_BLOCKED: `Server-Timing` '{st_str}' must use `acp;dur=<ms>` without exposing internal topology/query details"
            )
        if bool(context.get("used_server_timing_as_sole_client_sla", False)):
            server_timing_valid = False
            reasons.append(
                "ACP_SERVER_TIMING_SOLE_SLA_MISUSE_BLOCKED: `Server-Timing` excludes network time and must not replace independent client-observed latency measurement"
            )

    # 3. ACP PR #260 Feed Update ID & Product.last_update_id -> suggested_price.source provenance
    feed_ctx = context.get("feed_update_context")
    if isinstance(feed_ctx, Mapping):
        upsert_accepted = bool(feed_ctx.get("upsert_accepted", True))
        versioning_supported = bool(feed_ctx.get("versioning_supported", True))
        feed_update_id = str(feed_ctx.get("feed_update_id", "")).strip()
        touched_products_last_update_ids = tuple(
            str(x).strip() for x in feed_ctx.get("touched_products_last_update_ids", ())
        )
        checkout_suggested_price_source_id = str(
            feed_ctx.get("checkout_suggested_price_source_id", "")
        ).strip()
        known_feed_update_ids = {str(x).strip() for x in feed_ctx.get("known_feed_update_ids", ())}

        if upsert_accepted and versioning_supported:
            if not feed_update_id:
                feed_update_provenance_valid = False
                reasons.append(
                    "ACP_FEED_UPDATE_ID_MISSING_ON_ACCEPTED_UPSERT: agent supporting feed versioning must return a non-empty `feed_update_id`"
                )
            elif any(pid != feed_update_id for pid in touched_products_last_update_ids):
                feed_update_provenance_valid = False
                reasons.append(
                    "ACP_PRODUCT_LAST_UPDATE_ID_READBACK_MISMATCH: every product touched by the upsert must reflect `last_update_id == feed_update_id`"
                )

        if checkout_suggested_price_source_id and known_feed_update_ids:
            if checkout_suggested_price_source_id not in known_feed_update_ids:
                feed_update_provenance_valid = False
                reasons.append(
                    f"ACP_CHECKOUT_SUGGESTED_PRICE_SOURCE_UNKNOWN_FEED_VERSION[{checkout_suggested_price_source_id}]: `suggested_price.source` does not match any verified `feed_update_id`"
                )

    admitted = len(reasons) == 0
    if admitted:
        decision_code = "ACP_HOST_GATE_SERVER_TIMING_AND_FEED_UPDATE_VERIFIED"
    elif not host_spend_gate_valid:
        decision_code = "ACP_HOST_SPEND_GATE_DENIED_OR_MISCONFIGURED"
    elif not server_timing_valid:
        decision_code = "ACP_SERVER_TIMING_HEADER_LEAK_OR_MISUSE_BLOCKED"
    else:
        decision_code = "ACP_FEED_UPDATE_ID_PROVENANCE_MISMATCH_BLOCKED"

    return ACPHostGateServerTimingFeedUpdateGuardResult(
        admitted=admitted,
        decision_code=decision_code,
        host_spend_gate_valid=host_spend_gate_valid,
        server_timing_valid=server_timing_valid,
        feed_update_provenance_valid=feed_update_provenance_valid,
        reasons=tuple(reasons),
    )
