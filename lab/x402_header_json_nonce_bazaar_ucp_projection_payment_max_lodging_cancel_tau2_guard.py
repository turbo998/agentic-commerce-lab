"""Stage 200 (200-Stage Milestone!) deterministic guardrails (`2026-10-23`):

1. **x402 Non-Object JSON Header Decode Gate (`#3908`), Seller-Issued 32-Byte EIP-3009
   Resource-Bound Nonce (`#3873`), Bazaar Origin Liveness & 530 Pruning (`#3844`),
   Bazaar Single-Key-Per-Parameter Input Example (`#3841`), & `offer-receipt`
   `includeTxHash` Preservation (`#3824`)**:
   - `#3908`: `decode_payment_signature_header` / `decode_payment_required_header`
     must verify `isinstance(decoded_json, dict)` before calling `.get("x402Version", 2)`,
     returning a typed `400`/`402` error on JSON arrays, strings, numbers, or `null`
     instead of raising `AttributeError` (HTTP 5xx).
   - `#3873`: Variable-query resources requiring payer-authenticated resource binding
     issue a negotiated 32-byte `0x`-prefixed seller nonce bound via HMAC-SHA256 to
     `(method, canonical_path_query, resource_id, network, asset, payTo, amount,
     offer_id, challenge, expires_at)` and reject random unbound nonces or cross-query
     replay (`?target=A` -> `?target=B`).
   - `#3844`: Bazaar discovery enforces pre-listing `402` shape verification, prunes
     resources returning Cloudflare `530` (`error code: 1033`) or failing `>= 3`
     consecutive probes, and caps single-host unverified burst additions.
   - `#3841`: `info.input.body` and `info.input.queryParams` examples must contain at
     most one key per logical parameter alias group, retaining only the canonical
     primary key read first by the handler.
   - `#3824`: `ResourceServer.enrichExtensions` must preserve route-level declaration
     flags (`includeTxHash: True`) across `enrichDeclaration` so `enrichSettlementResponse`
     includes the settlement `transaction` hash in the signed receipt.

2. **UCP Cross-Boundary Carrier Projection (`#827`), Checkout `amount_finality` &
   `payment.maximum_amount` / Order Summaries (`#815`), Payment Processing Ledger
   (`#820`), Deterministic Lodging Cancellation `schedule` (`#807`), Request-Time
   Capability Enforcement (`#805`), & Lodging DTC Signed Pre-Session Quote (`#986`)**:
   - `#827`: Persistence-sensitive carriers crossing `Cart -> Checkout` must declare
     `projection: {identity, preserves, drops, on_unpreserved, reattest}` with disjoint
     `preserves`/`drops`, failing closed when an authorization-bearing carrier is
     unpreserved (`on_unpreserved == "fail_closed"`) or un-reattested (`reattest == "required"`).
   - `#815`: Only `totals[]` with `type == "total"` may set `amount_finality` (default
     `"final"`). `"provisional"` requires `payment.maximum_amount >= total.amount`;
     `"final"` forbids `payment.maximum_amount`. Order instruments report
     `authorized_amount` and gross `captured_amount`, omit `credential`/`handler_id`/`selected`,
     and forbid inferring remaining capture capacity by subtraction.
   - `#820`: Checkout capture policy (`"automatic"`/`"manual"`) is omitted/immutable on
     `Complete Checkout`; `approvals[]` records total ceilings (never deltas);
     `attempts[]` sum to parent instrument summaries; pending entries resolve via an
     append-only entry with `resolves_entry_id`; and pruned history sets
     `entries_complete: False` while keeping pending/referenced entries.
   - `#807`: `dev.ucp.lodging.policy.cancellation.schedule` requires atomic
     `(anchor, non-empty tiers[], after_last_tier)`, RFC 3339 `anchor`/`at` with `Z` or
     explicit offset and no `:60` leap second, strictly decreasing `tiers[].until`
     in POSIX seconds (`1D == 86400s`, no duplicate equivalents like `P1D` and `PT24H`),
     half-open evaluation (`at < anchor - until`), and no fabricated cash conversion
     for `percentage`/`unit_deduction` without an explicit price basis.
   - `#805`: Request-time capability validation must return `capabilities_incompatible`
     whenever a capability required by the requested operation has no mutually
     supported version, even on unsigned requests without `Signature-Input`.
   - `#986`: Direct-to-consumer (`/.well-known/ucp`) origin-minted `stay.id` quotes
     must be signed by a key in the Business profile's `keys[]` and unexpired.

3. **MCP Verifiable Tool Results (`#3354`), Channel-Policy Per-Send Attestation
   (`#3337`), `browser-automation` Safety Invariants (`#3305`), & Sierra $\\tau$-bench 2.0
   Uninvolved Customer Write Isolation (`#459`) & Smallest-Sufficient Gift Card (`#664`)**:
   - `#3354`: `tools/call` results carrying `_meta["io.modelcontextprotocol/verifiable-result"]`
     must verify `(program_digest, canonical_input_digest, canonical_output_digest,
     freshness_nonce)` before client action.
   - `#3337`: External messaging/egress tool calls must carry a verified channel-policy
     per-send attestation receipt binding `body_sha256`, `channel_id`, `policy_id`, and
     DLP redaction status.
   - `#3305`: `browser-automation` capability must declare all 6 safety invariants
     (`origin_scoped_credentials`, `verified_actions`, `human_approval_gates`,
     `sandboxed_renderer`, `no_identity_cookie_cloning`, `audit_logging`) and provide
     before/after state evidence on mutating actions.
   - `#459`: Write tools in `telecom` evaluations must not mutate uninvolved customer
     records (`C1001/L1001`) outside the task's authorized target set; any collateral
     write forces `reward = 0.0`.
   - `#664`: Single-instrument "smallest balance" gift-card selection resolves to the
     smallest balance sufficient to cover the required charge (`$113` for a `$59`
     change when cards are `$157, $113, $6`) and requires localized bundle hash parity.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from typing import Any, Mapping, Sequence


_HEX32_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
_RFC3339_OFFSET_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
_ISO_DURATION_DHMS_RE = re.compile(
    r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$"
)
_REQUIRED_BROWSER_INVARIANTS = frozenset(
    {
        "origin_scoped_credentials",
        "verified_actions",
        "human_approval_gates",
        "sandboxed_renderer",
        "no_identity_cookie_cloning",
        "audit_logging",
    }
)


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    http_status: int
    details: dict[str, Any]


# ---------------------------------------------------------------------------
# 1. x402 #3908, #3873, #3844, #3841, #3824
# ---------------------------------------------------------------------------

def validate_x402_header_json_object_decode(
    encoded_header: str,
    *,
    header_kind: str = "PAYMENT-SIGNATURE",
) -> GuardDecision:
    """x402 Issue #3908: reject valid JSON that is not a dict before `.get(...)`."""
    status_on_err = 402 if header_kind == "PAYMENT-SIGNATURE" else 400
    if not isinstance(encoded_header, str) or not encoded_header.strip():
        return GuardDecision(
            allowed=False,
            decision_code="X402_HEADER_EMPTY_REJECTED",
            http_status=status_on_err,
            details={"header_kind": header_kind},
        )
    try:
        padded = encoded_header + "=" * (-len(encoded_header) % 4)
        raw_bytes = base64.b64decode(padded, validate=False)
        decoded = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        return GuardDecision(
            allowed=False,
            decision_code="X402_HEADER_MALFORMED_JSON_REJECTED",
            http_status=status_on_err,
            details={"header_kind": header_kind, "error": type(exc).__name__},
        )
    if not isinstance(decoded, dict):
        return GuardDecision(
            allowed=False,
            decision_code="X402_HEADER_JSON_NOT_OBJECT_REJECTED",
            http_status=status_on_err,
            details={
                "header_kind": header_kind,
                "decoded_type": type(decoded).__name__,
            },
        )
    version = decoded.get("x402Version", 2)
    if version not in (1, 2):
        return GuardDecision(
            allowed=False,
            decision_code="X402_HEADER_UNSUPPORTED_VERSION",
            http_status=status_on_err,
            details={"x402Version": version},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_HEADER_JSON_OBJECT_VALIDATED",
        http_status=200,
        details={"header_kind": header_kind, "x402Version": version},
    )


def compute_seller_resource_bound_nonce(
    *,
    secret: str,
    method: str,
    canonical_path_query: str,
    resource_id: str,
    network: str,
    asset: str,
    pay_to: str,
    amount: str,
    offer_id: str,
    challenge: str,
    expires_at: int,
) -> str:
    payload = "|".join(
        [
            "x402-seller-nonce-v1",
            method.upper().strip(),
            canonical_path_query.strip(),
            resource_id.strip(),
            network.strip(),
            asset.lower().strip(),
            pay_to.lower().strip(),
            str(amount).strip(),
            offer_id.strip(),
            challenge.strip(),
            str(expires_at),
        ]
    )
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"0x{digest}"


def validate_x402_seller_issued_eip3009_nonce(
    *,
    requires_resource_bound_nonce: bool,
    client_supports_seller_nonce: bool,
    signed_nonce: str,
    secret: str,
    method: str,
    canonical_path_query: str,
    resource_id: str,
    network: str,
    asset: str,
    pay_to: str,
    amount: str,
    offer_id: str,
    challenge: str,
    expires_at: int,
    now_epoch: int,
    consumed_nonces: set[str] | frozenset[str] = frozenset(),
) -> GuardDecision:
    """x402 Issue #3873: verify optional negotiated seller-issued 32-byte EIP-3009 nonce."""
    if not isinstance(signed_nonce, str) or not _HEX32_RE.match(signed_nonce):
        return GuardDecision(
            allowed=False,
            decision_code="X402_EIP3009_NONCE_FORMAT_INVALID",
            http_status=402,
            details={"signed_nonce": signed_nonce},
        )
    normalized_nonce = signed_nonce.lower()
    if normalized_nonce in {n.lower() for n in consumed_nonces}:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EIP3009_NONCE_REPLAY_BLOCKED",
            http_status=402,
            details={"signed_nonce": normalized_nonce},
        )
    if not requires_resource_bound_nonce:
        return GuardDecision(
            allowed=True,
            decision_code="X402_CLIENT_RANDOM_NONCE_ADMITTED",
            http_status=200,
            details={"signed_nonce": normalized_nonce, "mode": "client_random"},
        )
    if not client_supports_seller_nonce:
        return GuardDecision(
            allowed=False,
            decision_code="X402_SELLER_NONCE_DOWNGRADE_BLOCKED",
            http_status=402,
            details={"reason": "client_did_not_negotiate_seller_nonce"},
        )
    if now_epoch > expires_at:
        return GuardDecision(
            allowed=False,
            decision_code="X402_SELLER_NONCE_CHALLENGE_EXPIRED",
            http_status=402,
            details={"now_epoch": now_epoch, "expires_at": expires_at},
        )
    expected_nonce = compute_seller_resource_bound_nonce(
        secret=secret,
        method=method,
        canonical_path_query=canonical_path_query,
        resource_id=resource_id,
        network=network,
        asset=asset,
        pay_to=pay_to,
        amount=amount,
        offer_id=offer_id,
        challenge=challenge,
        expires_at=expires_at,
    ).lower()
    if not hmac.compare_digest(normalized_nonce, expected_nonce):
        return GuardDecision(
            allowed=False,
            decision_code="X402_SELLER_NONCE_RESOURCE_MISMATCH_BLOCKED",
            http_status=402,
            details={
                "signed_nonce": normalized_nonce,
                "expected_nonce": expected_nonce,
                "canonical_path_query": canonical_path_query,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_SELLER_RESOURCE_BOUND_NONCE_VERIFIED",
        http_status=200,
        details={"signed_nonce": normalized_nonce, "canonical_path_query": canonical_path_query},
    )


def validate_x402_bazaar_origin_liveness_and_pruning(
    *,
    host: str,
    probe_http_status: int,
    probe_body: str,
    has_valid_402_shape: bool,
    consecutive_non_402_checks: int,
    max_consecutive_non_402: int = 3,
    host_listed_count: int = 1,
    total_catalogue_count: int = 100,
    max_single_host_share: float = 0.25,
) -> GuardDecision:
    """x402 Issue #3844: prune Cloudflare 530 / error 1033 dead origins and non-402 floods."""
    if probe_http_status == 530 or "error code: 1033" in (probe_body or "").lower():
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_DEAD_ORIGIN_530_PRUNED",
            http_status=503,
            details={"host": host, "probe_http_status": probe_http_status},
        )
    if probe_http_status != 402 or not has_valid_402_shape:
        new_streak = consecutive_non_402_checks + 1
        code = (
            "X402_BAZAAR_CONSECUTIVE_NON_402_PRUNED"
            if new_streak >= max_consecutive_non_402
            else "X402_BAZAAR_PROBE_NOT_PAYABLE_402_QUARANTINED"
        )
        return GuardDecision(
            allowed=False,
            decision_code=code,
            http_status=422,
            details={
                "host": host,
                "probe_http_status": probe_http_status,
                "consecutive_non_402_checks": new_streak,
            },
        )
    host_share = host_listed_count / max(total_catalogue_count, 1)
    if total_catalogue_count >= 20 and host_share > max_single_host_share:
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_SINGLE_HOST_CONCENTRATION_CAPPED",
            http_status=429,
            details={"host": host, "host_share": round(host_share, 4)},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_BAZAAR_PAYABLE_402_RESOURCE_ADMITTED",
        http_status=200,
        details={"host": host, "probe_http_status": probe_http_status},
    )


def validate_x402_bazaar_canonical_input_example(
    *,
    example_fields: Mapping[str, Any],
    parameter_alias_groups: Sequence[Sequence[str]],
    surface: str = "body",
) -> GuardDecision:
    """x402 Issue #3841: forbid multiple aliases for one logical parameter in examples."""
    if not isinstance(example_fields, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="X402_BAZAAR_INPUT_EXAMPLE_NOT_OBJECT",
            http_status=400,
            details={"surface": surface},
        )
    present_keys = set(example_fields.keys())
    for group in parameter_alias_groups:
        if not group:
            continue
        canonical_first = group[0]
        matched = [alias for alias in group if alias in present_keys]
        if len(matched) > 1:
            return GuardDecision(
                allowed=False,
                decision_code="X402_BAZAAR_INPUT_EXAMPLE_DUPLICATE_ALIAS_BLOCKED",
                http_status=400,
                details={
                    "surface": surface,
                    "canonical_key": canonical_first,
                    "matched_aliases": matched,
                },
            )
        if len(matched) == 1 and matched[0] != canonical_first:
            return GuardDecision(
                allowed=False,
                decision_code="X402_BAZAAR_INPUT_EXAMPLE_NON_PRIMARY_ALIAS_BLOCKED",
                http_status=400,
                details={
                    "surface": surface,
                    "canonical_key": canonical_first,
                    "used_alias": matched[0],
                },
            )
    return GuardDecision(
        allowed=True,
        decision_code="X402_BAZAAR_INPUT_EXAMPLE_CANONICAL_VERIFIED",
        http_status=200,
        details={"surface": surface, "keys": sorted(present_keys)},
    )


def validate_x402_offer_receipt_include_tx_hash_preservation(
    *,
    route_declaration: Mapping[str, Any],
    enriched_declaration: Mapping[str, Any],
    settlement_tx_hash: str,
    signed_receipt_payload: Mapping[str, Any],
) -> GuardDecision:
    """x402 Issue #3824: preserve `includeTxHash: True` across `enrichExtensions` into settlement."""
    route_wants_tx = route_declaration.get("includeTxHash") is True
    enriched_preserved_flag = enriched_declaration.get("includeTxHash") is True
    receipt_tx = signed_receipt_payload.get("transaction")

    if route_wants_tx and not enriched_preserved_flag:
        return GuardDecision(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_INCLUDE_TX_HASH_DROPPED_BLOCKED",
            http_status=500,
            details={"reason": "enrichExtensions_overwrote_includeTxHash"},
        )
    if route_wants_tx and (not isinstance(receipt_tx, str) or receipt_tx != settlement_tx_hash):
        return GuardDecision(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_MISSING_SETTLEMENT_TX_HASH",
            http_status=500,
            details={"expected_tx": settlement_tx_hash, "receipt_tx": receipt_tx},
        )
    if not route_wants_tx and receipt_tx is not None:
        return GuardDecision(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_UNREQUESTED_TX_HASH_LEAKED",
            http_status=400,
            details={"receipt_tx": receipt_tx},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_OFFER_RECEIPT_TX_HASH_POLICY_VERIFIED",
        http_status=200,
        details={"includeTxHash": route_wants_tx, "transaction": receipt_tx},
    )


# ---------------------------------------------------------------------------
# 2. UCP #827, #815, #820, #807, #805, #986
# ---------------------------------------------------------------------------

def validate_ucp_cross_boundary_carrier_projection(
    *,
    carrier_name: str,
    persistence_sensitive: bool,
    crosses_boundary: bool,
    projection: Mapping[str, Any] | None,
    carrier_present_at_target: bool,
    freshly_reattested: bool,
) -> GuardDecision:
    """UCP Issue #827: cross-boundary projection contract (`Cart -> Checkout`)."""
    if not persistence_sensitive or not crosses_boundary:
        return GuardDecision(
            allowed=True,
            decision_code="UCP_SINGLE_STAGE_CARRIER_EXEMPT",
            http_status=200,
            details={"carrier_name": carrier_name},
        )
    if not isinstance(projection, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PROJECTION_CONTRACT_MISSING_BLOCKED",
            http_status=400,
            details={"carrier_name": carrier_name},
        )
    identity = projection.get("identity")
    preserves = projection.get("preserves")
    drops = projection.get("drops")
    on_unpreserved = projection.get("on_unpreserved")
    reattest = projection.get("reattest")

    if (
        not isinstance(identity, str)
        or not identity.strip()
        or not isinstance(preserves, list)
        or not isinstance(drops, list)
        or on_unpreserved not in ("recover", "degrade", "fail_closed")
        or reattest not in ("required", "not_required")
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PROJECTION_SCHEMA_INVALID",
            http_status=400,
            details={"carrier_name": carrier_name},
        )
    overlap = set(preserves) & set(drops)
    if overlap:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PROJECTION_PRESERVES_DROPS_OVERLAP_BLOCKED",
            http_status=400,
            details={"carrier_name": carrier_name, "overlap": sorted(overlap)},
        )
    if not carrier_present_at_target and on_unpreserved == "fail_closed":
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PROJECTION_UNPRESERVED_OR_REATTEST_REQUIRED_BLOCKED",
            http_status=409,
            details={"carrier_name": carrier_name, "reason": "missing_fail_closed_carrier"},
        )
    if reattest == "required" and not freshly_reattested:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PROJECTION_UNPRESERVED_OR_REATTEST_REQUIRED_BLOCKED",
            http_status=409,
            details={"carrier_name": carrier_name, "reason": "reattest_required"},
        )
    outcome = (
        "PRESERVED"
        if carrier_present_at_target
        else ("RECOVERED" if on_unpreserved == "recover" else "DEGRADED")
    )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_PROJECTION_CONTRACT_VERIFIED",
        http_status=200,
        details={"carrier_name": carrier_name, "outcome": outcome},
    )


def validate_ucp_checkout_payment_maximum_and_order_summaries(
    *,
    checkout_totals: Sequence[Mapping[str, Any]],
    checkout_payment: Mapping[str, Any],
    order_payment: Mapping[str, Any],
    client_inferred_remaining_capacity: int | None = None,
) -> GuardDecision:
    """UCP Issue #815: `amount_finality`, `payment.maximum_amount`, and Order instrument summaries."""
    total_entry: Mapping[str, Any] | None = None
    for item in checkout_totals:
        t_type = item.get("type")
        if t_type != "total" and "amount_finality" in item:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_NON_TOTAL_ENTRY_AMOUNT_FINALITY_FORBIDDEN",
                http_status=400,
                details={"type": t_type},
            )
        if t_type == "total":
            total_entry = item
    if total_entry is None or not isinstance(total_entry.get("amount"), int):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CHECKOUT_AGGREGATE_TOTAL_MISSING",
            http_status=400,
            details={},
        )
    total_amount = total_entry["amount"]
    finality = total_entry.get("amount_finality", "final")
    has_max = "maximum_amount" in checkout_payment
    checkout_max = checkout_payment.get("maximum_amount")

    if finality == "provisional":
        if not isinstance(checkout_max, int) or checkout_max < total_amount:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CHECKOUT_FINALITY_MAXIMUM_AMOUNT_VIOLATION",
                http_status=400,
                details={"finality": finality, "total_amount": total_amount, "maximum_amount": checkout_max},
            )
        approved_maximum = checkout_max
    elif finality == "final":
        if has_max:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CHECKOUT_FINALITY_MAXIMUM_AMOUNT_VIOLATION",
                http_status=400,
                details={"finality": "final", "reason": "final_total_forbids_maximum_amount"},
            )
        approved_maximum = total_amount
    else:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CHECKOUT_UNKNOWN_AMOUNT_FINALITY",
            http_status=400,
            details={"finality": finality},
        )

    if order_payment.get("maximum_amount") != approved_maximum:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ORDER_MAXIMUM_AMOUNT_DRIFT_BLOCKED",
            http_status=400,
            details={
                "expected_maximum_amount": approved_maximum,
                "order_maximum_amount": order_payment.get("maximum_amount"),
            },
        )
    if client_inferred_remaining_capacity is not None:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_INFERRED_REMAINING_CAPTURE_CAPACITY_FORBIDDEN",
            http_status=400,
            details={"inferred": client_inferred_remaining_capacity},
        )

    instruments = order_payment.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ORDER_PAYMENT_INSTRUMENTS_MISSING",
            http_status=400,
            details={},
        )
    for inst in instruments:
        forbidden = {"credential", "handler_id", "selected"} & set(inst.keys())
        if forbidden or "display" not in inst:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ORDER_INSTRUMENT_FORBIDDEN_FIELD_OR_MISSING_DISPLAY",
                http_status=400,
                details={"forbidden": sorted(forbidden)},
            )
        auth_amt = inst.get("authorized_amount", 0)
        cap_amt = inst.get("captured_amount", 0)
        if not isinstance(auth_amt, int) or not isinstance(cap_amt, int) or auth_amt < 0 or cap_amt < 0:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ORDER_INSTRUMENT_SUMMARY_INVALID",
                http_status=400,
                details={"authorized_amount": auth_amt, "captured_amount": cap_amt},
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_CHECKOUT_MAX_AND_ORDER_SUMMARIES_VERIFIED",
        http_status=200,
        details={"approved_maximum": approved_maximum, "finality": finality},
    )


def validate_ucp_payment_processing_policy_and_reporting(
    *,
    complete_checkout_request: Mapping[str, Any],
    order_maximum_amount: int,
    completed_checkout_policy: str,
    instrument_summary: Mapping[str, int],
    processing: Mapping[str, Any],
    mutated_pending_entry_in_place: bool = False,
) -> GuardDecision:
    """UCP Issue #820: capture policy, approvals[], attempts[], and append-only entries[]."""
    if "policy" in complete_checkout_request or "capture_policy" in complete_checkout_request:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"reason": "capture_policy_forbidden_on_complete_checkout"},
        )
    if completed_checkout_policy not in ("automatic", "manual"):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"reason": "invalid_checkout_capture_policy"},
        )
    if mutated_pending_entry_in_place:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"reason": "pending_entry_mutated_instead_of_resolves_entry_id"},
        )
    approvals = processing.get("approvals")
    attempts = processing.get("attempts")
    if not isinstance(approvals, list) or not approvals or not isinstance(attempts, list) or not attempts:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"reason": "missing_approvals_or_attempts"},
        )
    first_app = approvals[0]
    if (
        first_app.get("type") != "checkout"
        or first_app.get("maximum_amount") != order_maximum_amount
        or first_app.get("policy") != completed_checkout_policy
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"reason": "first_approval_mismatch"},
        )
    for app in approvals[1:]:
        if app.get("type") == "order_change" and (
            not app.get("adjustment_id") or app.get("is_delta") is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
                http_status=400,
                details={"reason": "order_change_approval_must_record_new_ceiling_with_adjustment_ref"},
            )

    sum_auth = sum(int(a.get("authorized_amount", 0)) for a in attempts)
    sum_cap = sum(int(a.get("captured_amount", 0)) for a in attempts)
    if (
        sum_auth != instrument_summary.get("authorized_amount", 0)
        or sum_cap != instrument_summary.get("captured_amount", 0)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
            http_status=400,
            details={"sum_auth": sum_auth, "sum_cap": sum_cap, "instrument": dict(instrument_summary)},
        )

    for att in attempts:
        entries = att.get("entries", [])
        entries_complete = att.get("entries_complete", True)
        pruned_count = int(att.get("pruned_terminal_entries_count", 0))
        if pruned_count > 0 and entries_complete is not False:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
                http_status=400,
                details={"reason": "pruned_history_must_set_entries_complete_false"},
            )
        entry_ids = {e.get("id") for e in entries if e.get("id")}
        for e in entries:
            ref_id = e.get("resolves_entry_id")
            if ref_id and ref_id not in entry_ids:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION",
                    http_status=400,
                    details={"reason": "pruned_referenced_pending_entry", "resolves_entry_id": ref_id},
                )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_PAYMENT_PROCESSING_LEDGER_VERIFIED",
        http_status=200,
        details={"approvals_count": len(approvals), "attempts_count": len(attempts)},
    )


def _parse_rfc3339_posix(ts: str) -> int | None:
    if not isinstance(ts, str):
        return None
    m = _RFC3339_OFFSET_RE.match(ts)
    if not m:
        return None
    sec = int(m.group(6))
    if sec > 59:  # leap second :60 unsupported per UCP #807
        return None
    normalized = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return int(dt.astimezone(timezone.utc).timestamp())


def _parse_until_seconds(duration: str) -> int | None:
    if not isinstance(duration, str) or duration in ("P", "PT"):
        return None
    m = _ISO_DURATION_DHMS_RE.match(duration)
    if not m:
        return None
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total if total > 0 else None


def evaluate_ucp_lodging_cancellation_schedule(
    *,
    schedule: Mapping[str, Any],
    at: str,
    attempt_cash_conversion_without_price_basis: bool = False,
) -> GuardDecision:
    """UCP Issue #807: deterministic lodging cancellation `schedule` evaluation."""
    if not isinstance(schedule, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
            http_status=400,
            details={"reason": "schedule_not_object"},
        )
    anchor_str = schedule.get("anchor")
    tiers = schedule.get("tiers")
    after_last_tier = schedule.get("after_last_tier")
    if (
        not isinstance(anchor_str, str)
        or not isinstance(tiers, list)
        or len(tiers) == 0
        or not isinstance(after_last_tier, Mapping)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
            http_status=400,
            details={"reason": "missing_atomic_anchor_tiers_or_after_last_tier"},
        )
    anchor_posix = _parse_rfc3339_posix(anchor_str)
    at_posix = _parse_rfc3339_posix(at)
    if anchor_posix is None or at_posix is None:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
            http_status=400,
            details={"reason": "invalid_or_leap_second_timestamp", "anchor": anchor_str, "at": at},
        )

    prev_until_sec: int | None = None
    parsed_tiers: list[tuple[int, Mapping[str, Any]]] = []
    for idx, tier in enumerate(tiers):
        if not isinstance(tier, Mapping):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={"reason": "tier_not_object", "index": idx},
            )
        until_sec = _parse_until_seconds(str(tier.get("until", "")))
        outcome = tier.get("outcome")
        if until_sec is None or not isinstance(outcome, Mapping):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={"reason": "invalid_until_duration_or_outcome", "index": idx},
            )
        if prev_until_sec is not None and until_sec >= prev_until_sec:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={
                    "reason": "tiers_not_strictly_decreasing_or_duplicate_cutoff",
                    "prev_seconds": prev_until_sec,
                    "curr_seconds": until_sec,
                },
            )
        prev_until_sec = until_sec
        parsed_tiers.append((until_sec, outcome))

    selected_outcome: Mapping[str, Any] = after_last_tier
    selected_stage = "after_last_tier"
    for idx, (until_sec, outcome) in enumerate(parsed_tiers):
        cutoff_posix = anchor_posix - until_sec
        # Half-open interval: strictly earlier (`at < anchor - until`)
        if at_posix < cutoff_posix:
            selected_outcome = outcome
            selected_stage = f"tier[{idx}]"
            break

    kind = selected_outcome.get("kind")
    if kind in ("percentage", "unit_deduction") and attempt_cash_conversion_without_price_basis:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_SYMBOLIC_OUTCOME_CASH_CONVERSION_BLOCKED",
            http_status=400,
            details={"kind": kind, "selected_stage": selected_stage},
        )
    if kind == "percentage":
        bps = selected_outcome.get("buyer_bps")
        if not isinstance(bps, int) or bps < 0 or bps > 10000:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={"reason": "invalid_buyer_bps", "buyer_bps": bps},
            )
    elif kind == "fixed_fee":
        amt = (selected_outcome.get("penalty") or {}).get("amount")
        if not isinstance(amt, int) or amt < 0:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={"reason": "invalid_fixed_fee_amount"},
            )
    elif kind == "unit_deduction":
        measure = (selected_outcome.get("penalty") or {}).get("measure") or {}
        if (
            not isinstance(measure.get("value"), int)
            or measure.get("value", 0) <= 0
            or not measure.get("unit")
            or not measure.get("display_text")
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_INVALID",
                http_status=400,
                details={"reason": "invalid_unit_deduction_measure"},
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_LODGING_CANCELLATION_SCHEDULE_EVALUATED",
        http_status=200,
        details={"selected_stage": selected_stage, "outcome": dict(selected_outcome)},
    )


def validate_ucp_request_time_capability_enforcement(
    *,
    required_capability: str,
    platform_declared_capabilities: Mapping[str, Sequence[str]],
    business_supported_capabilities: Mapping[str, Sequence[str]],
    has_signature_input_header: bool = False,
) -> GuardDecision:
    """UCP Issue #805: enforce `capabilities_incompatible` on every request regardless of `Signature-Input`."""
    plat_versions = set(platform_declared_capabilities.get(required_capability, ()))
    biz_versions = set(business_supported_capabilities.get(required_capability, ()))
    mutual = sorted(plat_versions & biz_versions)
    if not mutual:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CAPABILITIES_INCOMPATIBLE_OPERATION_REJECTED",
            http_status=400,
            details={
                "error": "capabilities_incompatible",
                "required_capability": required_capability,
                "has_signature_input_header": has_signature_input_header,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_REQUEST_CAPABILITY_NEGOTIATED",
        http_status=200,
        details={
            "required_capability": required_capability,
            "negotiated_version": mutual[-1],
        },
    )


def validate_ucp_lodging_dtc_signed_stay_quote(
    *,
    business_origin: str,
    stay_origin: str,
    published_key_ids: set[str] | frozenset[str],
    quote_key_id: str,
    quote_signature_valid: bool,
    quote_expires_at: int,
    now_epoch: int,
    stay_id: str,
) -> GuardDecision:
    """UCP Issue #986: validate DTC origin-minted `stay.id` and Business-signed pre-session quote."""
    if not stay_id.strip() or business_origin.rstrip("/").lower() != stay_origin.rstrip("/").lower():
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_DTC_ORIGIN_MISMATCH_BLOCKED",
            http_status=400,
            details={"business_origin": business_origin, "stay_origin": stay_origin},
        )
    if (
        quote_key_id not in published_key_ids
        or not quote_signature_valid
        or now_epoch > quote_expires_at
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_LODGING_DTC_UNSIGNED_OR_EXPIRED_QUOTE_BLOCKED",
            http_status=401,
            details={
                "quote_key_id": quote_key_id,
                "quote_signature_valid": quote_signature_valid,
                "expired": now_epoch > quote_expires_at,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_LODGING_DTC_SIGNED_QUOTE_VERIFIED",
        http_status=200,
        details={"stay_id": stay_id, "quote_key_id": quote_key_id},
    )


# ---------------------------------------------------------------------------
# 3. MCP #3354, #3337, #3305 & Sierra tau2-bench #459, #664
# ---------------------------------------------------------------------------

def validate_mcp_verifiable_tool_result(
    *,
    expected_program_digest: str,
    canonical_input_digest: str,
    canonical_output_digest: str,
    expected_nonce: str,
    verifiable_meta: Mapping[str, Any] | None,
) -> GuardDecision:
    """MCP Issue #3354: verify ZK proof / TEE attestation execution integrity before acting."""
    if not isinstance(verifiable_meta, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_VERIFIABLE_TOOL_RESULT_PROOF_INVALID",
            http_status=403,
            details={"reason": "missing_verifiable_result_metadata"},
        )
    proof_type = verifiable_meta.get("proof_type")
    if proof_type not in ("zk_snark", "tee_attestation", "signed_commitment"):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_VERIFIABLE_TOOL_RESULT_PROOF_INVALID",
            http_status=403,
            details={"reason": "unsupported_proof_type", "proof_type": proof_type},
        )
    if (
        verifiable_meta.get("program_digest") != expected_program_digest
        or verifiable_meta.get("input_digest") != canonical_input_digest
        or verifiable_meta.get("output_digest") != canonical_output_digest
        or verifiable_meta.get("freshness_nonce") != expected_nonce
        or verifiable_meta.get("cryptographic_proof_valid") is not True
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_VERIFIABLE_TOOL_RESULT_PROOF_INVALID",
            http_status=403,
            details={"proof_type": proof_type},
        )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_VERIFIABLE_TOOL_RESULT_INTEGRITY_VERIFIED",
        http_status=200,
        details={"proof_type": proof_type, "program_digest": expected_program_digest},
    )


def validate_mcp_channel_policy_per_send_attestation(
    *,
    message_body: str,
    target_channel_id: str,
    attestation: Mapping[str, Any] | None,
) -> GuardDecision:
    """MCP Issue #3337 (IG #2626): require per-send channel-policy attestation receipt."""
    if not isinstance(attestation, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_CHANNEL_POLICY_PER_SEND_ATTESTATION_MISSING",
            http_status=403,
            details={"target_channel_id": target_channel_id},
        )
    expected_sha = hashlib.sha256(message_body.encode("utf-8")).hexdigest()
    if (
        attestation.get("channel_id") != target_channel_id
        or not attestation.get("policy_id")
        or attestation.get("recipient_scope_allowed") is not True
        or attestation.get("dlp_redaction_passed") is not True
        or attestation.get("body_sha256") != expected_sha
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_CHANNEL_POLICY_PER_SEND_ATTESTATION_MISSING",
            http_status=403,
            details={"target_channel_id": target_channel_id, "expected_sha": expected_sha},
        )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_CHANNEL_POLICY_PER_SEND_ATTESTED",
        http_status=200,
        details={"channel_id": target_channel_id, "policy_id": attestation.get("policy_id")},
    )


def validate_mcp_browser_automation_capability_contract(
    *,
    advertised_invariants: Sequence[str],
    is_mutating_action: bool,
    has_before_after_state_evidence: bool,
    cloned_user_profile_cookies: bool = False,
) -> GuardDecision:
    """MCP Issue #3305: enforce `browser-automation` safety invariants contract."""
    missing = sorted(_REQUIRED_BROWSER_INVARIANTS - set(advertised_invariants))
    if missing or cloned_user_profile_cookies:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_BROWSER_AUTOMATION_SAFETY_INVARIANT_MISSING",
            http_status=403,
            details={
                "missing_invariants": missing,
                "cloned_user_profile_cookies": cloned_user_profile_cookies,
            },
        )
    if is_mutating_action and not has_before_after_state_evidence:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_BROWSER_AUTOMATION_UNVERIFIED_MUTATION_BLOCKED",
            http_status=403,
            details={"reason": "missing_before_after_state_evidence"},
        )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_BROWSER_AUTOMATION_CONTRACT_VERIFIED",
        http_status=200,
        details={"invariants_count": len(advertised_invariants)},
    )


def validate_tau2_telecom_uninvolved_customer_write_guard(
    *,
    authorized_customer_ids: set[str] | frozenset[str],
    authorized_line_ids: set[str] | frozenset[str],
    write_tool_calls: Sequence[Mapping[str, str]],
    env_assertion_passed: bool,
) -> GuardDecision:
    """Sierra tau2-bench Issue #459: zero reward if a write tool mutates an uninvolved customer/line."""
    for call in write_tool_calls:
        cust_id = call.get("customer_id", "")
        line_id = call.get("line_id", "")
        if cust_id not in authorized_customer_ids or line_id not in authorized_line_ids:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_UNINVOLVED_CUSTOMER_WRITE_MUTATION_BLOCKED",
                http_status=400,
                details={
                    "tool": call.get("tool"),
                    "unauthorized_customer_id": cust_id,
                    "unauthorized_line_id": line_id,
                    "reward": 0.0,
                    "db_match": False,
                },
            )
    reward = 1.0 if env_assertion_passed else 0.0
    return GuardDecision(
        allowed=env_assertion_passed,
        decision_code="TAU2_TELECOM_SCOPED_WRITE_AND_DB_VERIFIED",
        http_status=200 if env_assertion_passed else 400,
        details={"reward": reward, "db_match": True},
    )


def validate_tau2_airline_smallest_sufficient_gift_card(
    *,
    gift_cards: Sequence[Mapping[str, Any]],
    required_amount: int,
    selected_payment_id: str,
    multilingual_bundle_hashes_synced: bool = True,
) -> GuardDecision:
    """Sierra tau2-bench Issue #664: select smallest gift card balance that covers `required_amount`."""
    if not multilingual_bundle_hashes_synced:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_MULTILINGUAL_BUNDLE_HASH_DRIFT_BLOCKED",
            http_status=409,
            details={"reason": "localized_task_bundles_out_of_sync"},
        )
    sufficient = [
        c for c in gift_cards if isinstance(c.get("balance"), int) and c["balance"] >= required_amount
    ]
    if not sufficient:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_NO_SUFFICIENT_GIFT_CARD_AVAILABLE",
            http_status=400,
            details={"required_amount": required_amount},
        )
    best = min(sufficient, key=lambda c: (c["balance"], str(c.get("id", ""))))
    if selected_payment_id != best.get("id"):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_GIFT_CARD_INSUFFICIENT_OR_NON_MINIMAL_SUFFICIENT_BLOCKED",
            http_status=400,
            details={
                "selected_payment_id": selected_payment_id,
                "expected_payment_id": best.get("id"),
                "expected_balance": best.get("balance"),
                "required_amount": required_amount,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_SMALLEST_SUFFICIENT_GIFT_CARD_VERIFIED",
        http_status=200,
        details={
            "selected_payment_id": best["id"],
            "selected_balance": best["balance"],
            "required_amount": required_amount,
        },
    )
