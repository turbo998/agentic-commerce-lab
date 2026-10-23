"""Stage 220 (220-Stage Milestone!) deterministic protocol security guards.

Covers 16 primary-source PRs across Universal Commerce Protocol (UCP Samples & Python SDK),
Stripe AI / MCP / Agent Toolkit, and Model Context Protocol (Go, Rust, C#, and Java SDKs):

- PR-01 (Universal-Commerce-Protocol/samples#258 & #248):
  UCP Complete Checkout atomic single-SQLite-transaction execution (inventory reservation,
  `saveOrder`, `saveCheckout` rolled back together; webhook I/O outside transaction lock) &
  deleted-product fail-closed rollback (`400 INVALID_REQUEST`, no order or idempotency record).
- PR-02 (Universal-Commerce-Protocol/samples#257 & #247):
  UCP REST Python reachable client fault normalization (`platform`/`ap2` exclusion on create,
  `UcpConfig(HttpUrl)` webhook gate, non-string card `number` -> `400 INVALID_REQUEST`,
  reused `destination.id` in-place update -> `200 OK`) & simulated shipment quantity sync
  (`delta_fulfilled == event_line_qty >= 1`, zero-total lines marked `removed`).
- PR-03 (Universal-Commerce-Protocol/samples#254, #253, #249, & #246):
  UCP shared `hasFulfillmentSelection` readiness gate (`ready_for_complete` iff all fulfillment
  methods have selected destination and all groups have selected option), A2A
  `a2a.ucp.checkout.payment` canonical DataPart & display adaptation, and single-instrument
  completion check (`len(instruments) > 1` -> `402 payment_failed`).
- PR-04 (Universal-Commerce-Protocol/python-sdk#102, #101, #100, & #96):
  UCP Python SDK `ucp-schema generate-types` codegen pipeline, removal of string regex
  `pattern` from generated `datetime` fields, and `dependentRequired` field validation.
- PR-05 (stripe/ai#584 & #542):
  Stripe MCP local proxy remote tool metadata preservation (`title` + `annotations`:
  `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) & immediate
  `-32603` JSON-RPC forwarding error response for requests (no reply for notifications).
- PR-06 (stripe/ai#581 & #559):
  Stripe Agent Toolkit worker-thread sync tool execution (`asyncio.get_running_loop()` vs.
  `asyncio.run()` fallback) & deprecated v0.6.x `actions` fail-open configuration rejection.
- PR-07 (modelcontextprotocol/go-sdk#1443 & #1441):
  MCP Go SDK Windows drive-letter `file://` root URI conversion (`RFC 8089` Appendix E.2
  `/C:/...` -> `C:\\...`) & strict `int64` JSON-RPC numeric ID validation (`ErrParse` on
  fractional, out-of-range, `NaN`, or `Inf` IDs).
- PR-08 (modelcontextprotocol/go-sdk#1442 & #1438):
  MCP Go SDK `PerformOIDCLogin` `RFC 9207` authorization response `iss` mix-up defense &
  `EnterpriseHandler.Authorize` `urn:ietf:params:oauth:token-type:id-jag` token type check.
- PR-09 (modelcontextprotocol/go-sdk#1440, #1425, & #1421):
  MCP Go SDK same-origin HTTP redirect restriction, `server/discover` single-authorization
  failure termination (no duplicate `initialize` auth flow), and `403 StatusForbidden`
  `WWW-Authenticate` `insufficient_scope` challenge header.
- PR-10 (modelcontextprotocol/go-sdk#1411):
  MCP Go SDK `jsonrpc2` response retirement queued behind preceding notifications on
  `handlerQueue` while bypassing queue for re-entrant nested calls from active sync handlers.
- PR-11 (modelcontextprotocol/rust-sdk#1392 & #1385):
  MCP Rust SDK SEP-2640 `io.modelcontextprotocol/skills` protocol surface (`skills/list`,
  `skills/get`, `resources/directory/read`) & OIDC `id_token` subject enterprise exchange.
- PR-12 (modelcontextprotocol/rust-sdk#1390 & #1382):
  MCP Rust SDK exact response media-type essence matching (rejecting `application/jsonx` /
  `text/event-streaming`, preserving JSON 503 errors) & RFC 9110 `Accept` quality weight
  (`q=0` rejection and quoted-string delimiter tolerance).
- PR-13 (modelcontextprotocol/rust-sdk#1383, #1377, & #1375):
  MCP Rust SDK URL-mode elicitation optional `elicitationId`, stateful session-less
  non-`initialize` POST `400 Bad Request`, and method-dispatched `ClientRequest` returning
  `-32602 INVALID_PARAMS` on known served methods with malformed params.
- PR-14 (modelcontextprotocol/rust-sdk#1379 & modelcontextprotocol/java-sdk#1257):
  MCP Rust & Java SDKs bounded child-process shutdown (`stdin` EOF -> wait -> `SIGTERM` /
  `destroy()` -> bounded timeout -> `SIGKILL` / `destroyForcibly()`, retaining cleanup guard).
- PR-15 (modelcontextprotocol/csharp-sdk#1953, #1952, & #1949):
  MCP C# SDK RFC 9728 `resource_indicators_supported` server-advertised RFC 8707 opt-out,
  default-off `AllowLegacyOAuthMetadataFallback` switch, required `S256` PKCE metadata, and
  exact ordinal `issuer` match.
- PR-16 (modelcontextprotocol/csharp-sdk#1945, #1934, & modelcontextprotocol/java-sdk#1266):
  MCP C# SDK case-sensitive `ProtocolOptions` (rejecting `{"Name":"echo"}` while keeping
  user argument DTOs case-insensitive), `FunctionResultContent.Result` unwrap serialization,
  and Java SDK `removeResourceTemplate` conditional `notifications/resources/list_changed`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Mapping
from urllib.parse import unquote, urlparse


INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
ID_JAG_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id-jag"
ALLOWED_SUBJECT_TOKEN_TYPES = {
    "urn:ietf:params:oauth:token-type:id_token",
    "urn:ietf:params:oauth:token-type:refresh_token",
}
REQUIRED_STRIPE_ANNOTATION_KEYS = {
    "readOnlyHint",
    "destructiveHint",
    "idempotentHint",
    "openWorldHint",
}
SKILLS_EXTENSION_ID = "io.modelcontextprotocol/skills"
SKILLS_ALLOWED_METHODS = {
    "skills/list",
    "skills/get",
    "resources/directory/read",
}
WIN_DRIVE_RE = re.compile(r"^/([a-zA-Z]:/.*)$")


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    action: str
    code: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/samples#258 & #248
# ---------------------------------------------------------------------------
def evaluate_ucp_complete_checkout_atomic_tx_and_deleted_product_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce single SQLite transaction on Complete Checkout (`samples#258`) and
    fail-closed rollback when a line item's product was deleted (`samples#248`).
    """
    single_sqlite_tx = bool(payload.get("single_sqlite_transaction", False))
    webhook_outside_tx = bool(payload.get("webhook_outside_transaction", False))
    write_fault_step = str(payload.get("write_fault_step", "none"))
    stock_before = int(payload.get("stock_before", 100))
    stock_after = int(payload.get("stock_after", 100))
    orphan_order_rows = int(payload.get("orphan_order_rows", 0))
    all_products_exist = bool(payload.get("all_products_exist", True))
    deleted_product_status = int(payload.get("deleted_product_http_status", 200))
    idempotency_committed_on_error = bool(
        payload.get("idempotency_committed_on_error", False)
    )

    if not single_sqlite_tx or not webhook_outside_tx:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_checkout_non_atomic_completion_or_webhook_in_tx",
            reason=(
                "Complete Checkout must execute inventory reservation, saveOrder, and "
                "saveCheckout in one SQLite transaction while keeping webhook I/O outside "
                "the write lock (samples#258)."
            ),
            evidence={
                "single_sqlite_transaction": single_sqlite_tx,
                "webhook_outside_transaction": webhook_outside_tx,
            },
        )

    if write_fault_step != "none":
        if stock_after != stock_before or orphan_order_rows > 0:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="ucp_checkout_partial_write_stock_or_order_leak",
                reason=(
                    f"Fault during '{write_fault_step}' left unrolled stock "
                    f"({stock_before} -> {stock_after}) or {orphan_order_rows} orphan order rows (samples#258)."
                ),
                evidence={
                    "write_fault_step": write_fault_step,
                    "stock_before": stock_before,
                    "stock_after": stock_after,
                    "orphan_order_rows": orphan_order_rows,
                },
            )

    if not all_products_exist:
        if (
            deleted_product_status != 400
            or stock_after != stock_before
            or orphan_order_rows > 0
            or idempotency_committed_on_error
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="ucp_deleted_product_silent_order_creation",
                reason=(
                    "Deleted product during complete_checkout must roll back prior line "
                    "reservations, return 400 INVALID_REQUEST, create no order, and leave "
                    "no committed idempotency record (samples#248)."
                ),
                evidence={
                    "deleted_product_http_status": deleted_product_status,
                    "stock_before": stock_before,
                    "stock_after": stock_after,
                    "idempotency_committed_on_error": idempotency_committed_on_error,
                },
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="ucp_complete_checkout_atomic_tx_and_product_verified",
        reason="Complete Checkout transaction atomicity and product existence checks verified.",
        evidence={
            "single_sqlite_transaction": single_sqlite_tx,
            "all_products_exist": all_products_exist,
            "stock_after": stock_after,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/samples#257 & #247
# ---------------------------------------------------------------------------
def evaluate_ucp_reachable_fault_4xx_and_shipment_sync_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce 4xx/2xx handling on 5 client-reachable Python REST faults (`samples#257`)
    and simulated shipment quantity synchronization (`samples#247`).
    """
    excluded_create_members = set(payload.get("excluded_create_members", ()))
    webhook_url = str(payload.get("agent_profile_webhook_url", "https://agent.example/hook"))
    malformed_webhook_dropped = bool(payload.get("malformed_webhook_dropped", True))
    card_number_value = payload.get("card_number", "4242")
    card_error_status = int(payload.get("card_error_http_status", 200))
    reused_dest_status = int(payload.get("reused_destination_id_http_status", 200))
    reused_dest_echoed = bool(payload.get("reused_destination_id_echoed_unchanged", True))

    if not {"platform", "ap2"}.issubset(excluded_create_members):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_create_checkout_unexcluded_platform_or_ap2_500",
            reason=(
                "create_checkout must exclude client-sent 'platform' and 'ap2' members "
                "to prevent 500 TypeError/ValidationError crashes (samples#257)."
            ),
            evidence={"excluded_create_members": sorted(excluded_create_members)},
        )

    parsed_hook = urlparse(webhook_url)
    is_valid_http_url = parsed_hook.scheme in {"http", "https"} and bool(parsed_hook.netloc)
    if not is_valid_http_url and not malformed_webhook_dropped:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_malformed_profile_webhook_unhandled_500",
            reason=(
                "Non-HTTP(S) agent profile webhook_url must be gated by UcpConfig(HttpUrl) "
                "and dropped without raising a 500 ValidationError (samples#257)."
            ),
            evidence={"agent_profile_webhook_url": webhook_url},
        )

    if not isinstance(card_number_value, str) and card_error_status != 400:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_non_string_card_number_unhandled_type_error",
            reason=(
                "Non-string card number on complete must return 400 INVALID_REQUEST "
                "instead of 500 TypeError on slice (samples#257)."
            ),
            evidence={
                "card_number_type": type(card_number_value).__name__,
                "card_error_http_status": card_error_status,
            },
        )

    if reused_dest_status != 200 or not reused_dest_echoed:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_reused_destination_id_integrity_error_or_id_drift",
            reason=(
                "Reusing a destination id on update must update in place (or re-key cross-customer) "
                "and return 200 with the platform-supplied id echoed unchanged (samples#257)."
            ),
            evidence={
                "reused_destination_id_http_status": reused_dest_status,
                "reused_destination_id_echoed_unchanged": reused_dest_echoed,
            },
        )

    remaining_qty = int(payload.get("remaining_unfulfilled_qty", 2))
    event_emitted = bool(payload.get("shipment_event_emitted", True))
    event_qty = int(payload.get("shipment_event_qty", 2))
    fulfilled_delta = int(payload.get("order_fulfilled_delta", 2))
    zero_total_included_in_event = bool(payload.get("zero_total_line_in_event", False))
    zero_total_marked_removed = bool(payload.get("zero_total_line_marked_removed", True))

    if zero_total_included_in_event or not zero_total_marked_removed:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_simulate_shipping_zero_total_line_violation",
            reason=(
                "Zero-total lines must be marked 'removed' and excluded from shipment "
                "events whose schema requires quantity >= 1 (samples#247)."
            ),
            evidence={
                "zero_total_line_in_event": zero_total_included_in_event,
                "zero_total_line_marked_removed": zero_total_marked_removed,
            },
        )

    if remaining_qty == 0 and event_emitted:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_simulate_shipping_empty_remaining_event_emitted",
            reason="simulate-shipping with 0 remaining units must emit no shipment event (samples#247).",
            evidence={"remaining_unfulfilled_qty": remaining_qty},
        )

    if remaining_qty > 0 and (
        not event_emitted or event_qty != remaining_qty or fulfilled_delta != remaining_qty
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_simulate_shipping_fulfilled_counter_desync",
            reason=(
                "simulate-shipping event quantity must equal remaining unfulfilled units "
                "and increment quantity.fulfilled identically (samples#247)."
            ),
            evidence={
                "remaining_unfulfilled_qty": remaining_qty,
                "shipment_event_qty": event_qty,
                "order_fulfilled_delta": fulfilled_delta,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="ucp_reachable_faults_and_shipment_sync_verified",
        reason="UCP REST Python fault envelopes and simulated shipment counter sync verified.",
        evidence={
            "excluded_create_members": sorted(excluded_create_members),
            "shipment_event_qty": event_qty,
        },
    )


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/samples#254, #253, #249, & #246
# ---------------------------------------------------------------------------
def evaluate_ucp_ready_for_complete_a2a_payment_and_single_instrument_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce `ready_for_complete` fulfillment gate (`samples#254`, `#253`),
    A2A `a2a.ucp.checkout.payment` contract (`samples#249`), and single payment
    instrument completion (`samples#246`).
    """
    methods_have_dest = bool(payload.get("all_methods_have_selected_destination", True))
    groups_have_option = bool(payload.get("all_groups_have_selected_option", True))
    reported_status = str(payload.get("checkout_status", "ready_for_complete"))
    complete_attempted = bool(payload.get("complete_checkout_attempted", True))
    complete_allowed = bool(payload.get("complete_checkout_allowed", True))

    expected_status = (
        "ready_for_complete"
        if (methods_have_dest and groups_have_option)
        else "incomplete"
    )
    if reported_status != expected_status:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_checkout_readiness_status_fulfillment_mismatch",
            reason=(
                f"Checkout reported status '{reported_status}' but fulfillment selection "
                f"gate requires '{expected_status}' (samples#254, samples#253)."
            ),
            evidence={
                "reported_status": reported_status,
                "expected_status": expected_status,
                "all_methods_have_selected_destination": methods_have_dest,
                "all_groups_have_selected_option": groups_have_option,
            },
        )

    if complete_attempted and expected_status != "ready_for_complete" and complete_allowed:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_incomplete_checkout_allowed_to_complete",
            reason=(
                "complete_checkout() must reject sessions whose status is not "
                "'ready_for_complete' before invoking payment (samples#249, samples#253)."
            ),
            evidence={"checkout_status": reported_status},
        )

    a2a_datapart_key = str(payload.get("a2a_payment_datapart_key", "a2a.ucp.checkout.payment"))
    display_adapted = bool(payload.get("a2a_display_top_level_adapted", True))
    missing_risk_signals_ok = bool(payload.get("a2a_missing_risk_signals_tolerated", True))
    if (
        a2a_datapart_key != "a2a.ucp.checkout.payment"
        or not display_adapted
        or not missing_risk_signals_ok
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_a2a_confirm_purchase_contract_drift",
            reason=(
                "A2A Confirm Purchase must use 'a2a.ucp.checkout.payment', adapt display "
                "fields (brand/last_digits), and allow optional risk_signals (samples#249)."
            ),
            evidence={
                "a2a_payment_datapart_key": a2a_datapart_key,
                "a2a_display_top_level_adapted": display_adapted,
                "a2a_missing_risk_signals_tolerated": missing_risk_signals_ok,
            },
        )

    instrument_count = int(payload.get("payment_instrument_count", 1))
    multi_instrument_status = int(payload.get("multi_instrument_http_status", 200))
    if instrument_count != 1:
        if instrument_count > 1 and multi_instrument_status != 402:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="ucp_multiple_payment_instruments_silently_ignored",
                reason=(
                    f"Completion with {instrument_count} payment instruments must be rejected "
                    "with HTTP 402 payment_failed instead of ignoring instruments[1:] (samples#246)."
                ),
                evidence={
                    "payment_instrument_count": instrument_count,
                    "multi_instrument_http_status": multi_instrument_status,
                },
            )
        if instrument_count < 1:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="ucp_empty_payment_instruments_rejected",
                reason="Completion requires exactly one payment instrument (samples#246).",
                evidence={"payment_instrument_count": instrument_count},
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="ucp_readiness_a2a_and_single_instrument_verified",
        reason="UCP ready_for_complete gate, A2A payment DataPart, and single-instrument rules verified.",
        evidence={
            "checkout_status": reported_status,
            "payment_instrument_count": instrument_count,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/python-sdk#102, #101, #100, & #96
# ---------------------------------------------------------------------------
def evaluate_ucp_python_sdk_codegen_datetime_and_dependent_required_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce `ucp-schema generate-types` codegen (`python-sdk#102`, `#101`),
    no regex `pattern` on generated `datetime` fields (`python-sdk#100`), and
    `dependentRequired` field validation (`python-sdk#96`).
    """
    generator_tool = str(payload.get("codegen_pipeline", "ucp-schema generate-types"))
    legacy_postprocessor_used = bool(payload.get("uses_preprocess_schemas_py", False))
    datetime_has_regex_pattern = bool(payload.get("datetime_field_has_regex_pattern", False))
    dependent_required_map: Mapping[str, list[str]] = payload.get(
        "dependent_required", {}
    )
    present_fields = set(payload.get("present_fields", ()))

    if generator_tool != "ucp-schema generate-types" or legacy_postprocessor_used:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_python_sdk_legacy_preprocess_pipeline",
            reason=(
                "UCP Python SDK models must be generated via 'ucp-schema generate-types' "
                "against the pinned spec without legacy preprocess_schemas.py (python-sdk#101, #102)."
            ),
            evidence={
                "codegen_pipeline": generator_tool,
                "uses_preprocess_schemas_py": legacy_postprocessor_used,
            },
        )

    if datetime_has_regex_pattern:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_python_sdk_datetime_regex_pattern_crash",
            reason=(
                "Generated datetime fields must not carry string regex patterns that "
                "fail on parsed datetime objects in Pydantic (python-sdk#100)."
            ),
            evidence={"datetime_field_has_regex_pattern": datetime_has_regex_pattern},
        )

    missing_dependents: dict[str, list[str]] = {}
    for trigger_field, required_siblings in dependent_required_map.items():
        if trigger_field in present_fields:
            missing = [req for req in required_siblings if req not in present_fields]
            if missing:
                missing_dependents[trigger_field] = missing

    if missing_dependents:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="ucp_python_sdk_dependent_required_violation",
            reason=(
                f"Model instance violated dependentRequired constraints: {missing_dependents} "
                "(python-sdk#96)."
            ),
            evidence={"missing_dependents": missing_dependents},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="ucp_python_sdk_codegen_and_constraints_verified",
        reason="UCP Python SDK generate-types pipeline, datetime fields, and dependentRequired verified.",
        evidence={"codegen_pipeline": generator_tool},
    )


# ---------------------------------------------------------------------------
# PR-05: stripe/ai#584 & #542
# ---------------------------------------------------------------------------
def evaluate_stripe_mcp_proxy_metadata_and_forwarding_error_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce remote MCP tool metadata preservation (`title` + `annotations`,
    `stripe/ai#584`) and immediate `-32603` JSON-RPC forwarding error response
    for requests (`stripe/ai#542`).
    """
    remote_title = str(payload.get("remote_tool_title", "Create Refund"))
    proxied_title = payload.get("proxied_tool_title")
    proxied_annotations = payload.get("proxied_tool_annotations") or {}

    if proxied_title != remote_title or not REQUIRED_STRIPE_ANNOTATION_KEYS.issubset(
        proxied_annotations.keys()
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="stripe_mcp_proxy_tool_metadata_stripped",
            reason=(
                "Local @stripe/mcp proxy must preserve remote tool 'title' and all "
                "canonical 'annotations' (readOnlyHint, destructiveHint, idempotentHint, "
                "openWorldHint) via registerTool (stripe/ai#584)."
            ),
            evidence={
                "remote_tool_title": remote_title,
                "proxied_tool_title": proxied_title,
                "proxied_annotation_keys": sorted(proxied_annotations.keys()),
            },
        )

    forwarding_failed = bool(payload.get("forwarding_failed", False))
    message_kind = str(payload.get("jsonrpc_message_kind", "request"))
    request_id = payload.get("jsonrpc_id", 1)
    proxy_reply = payload.get("proxy_error_reply")

    if forwarding_failed:
        if message_kind == "request":
            if not isinstance(proxy_reply, Mapping):
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    code="stripe_mcp_proxy_request_forwarding_error_dropped",
                    reason=(
                        "When forwarding a JSON-RPC request to mcp.stripe.com fails, the "
                        "stdio proxy must immediately reply with a -32603 error instead "
                        "of dropping the request until client timeout (stripe/ai#542)."
                    ),
                    evidence={"jsonrpc_id": request_id, "proxy_error_reply": proxy_reply},
                )
            error_obj = proxy_reply.get("error") or {}
            msg = str(error_obj.get("message", ""))
            if (
                proxy_reply.get("id") != request_id
                or error_obj.get("code") != -32603
                or not msg.startswith(
                    "Error forwarding request to the Stripe MCP server:"
                )
            ):
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    code="stripe_mcp_proxy_malformed_forwarding_error_reply",
                    reason=(
                        "Forwarding error reply must preserve request id, use code -32603, "
                        "and prefix 'Error forwarding request to the Stripe MCP server:' (stripe/ai#542)."
                    ),
                    evidence={"proxy_error_reply": dict(proxy_reply)},
                )
        else:
            if proxy_reply is not None:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    code="stripe_mcp_proxy_replied_to_notification_or_response",
                    reason=(
                        f"JSON-RPC proxy must not send an error reply for a '{message_kind}' "
                        "when forwarding fails (stripe/ai#542)."
                    ),
                    evidence={
                        "jsonrpc_message_kind": message_kind,
                        "proxy_error_reply": proxy_reply,
                    },
                )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="stripe_mcp_proxy_metadata_and_forwarding_verified",
        reason="Stripe MCP proxy tool metadata preservation and forwarding error reply verified.",
        evidence={
            "proxied_tool_title": proxied_title,
            "forwarding_failed": forwarding_failed,
        },
    )


# ---------------------------------------------------------------------------
# PR-06: stripe/ai#581 & #559
# ---------------------------------------------------------------------------
def evaluate_stripe_toolkit_event_loop_and_deprecated_actions_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce `asyncio.get_running_loop()` worker-thread sync tool execution
    (`stripe/ai#581`) and deprecated `actions` / unknown config key protection
    (`stripe/ai#559`).
    """
    uses_get_event_loop = bool(payload.get("uses_deprecated_get_event_loop", False))
    running_loop_present = bool(payload.get("running_loop_present", False))
    execution_strategy = str(payload.get("sync_execution_strategy", "asyncio_run"))
    config_keys = set(payload.get("toolkit_config_keys", ("context",)))
    fail_open_actions_ignored = bool(payload.get("fail_open_actions_silently_ignored", False))

    if uses_get_event_loop:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="stripe_toolkit_get_event_loop_worker_thread_crash",
            reason=(
                "StripeTool._run must use asyncio.get_running_loop() rather than "
                "asyncio.get_event_loop() which raises RuntimeError in worker threads "
                "and Python 3.14 (stripe/ai#581)."
            ),
            evidence={"uses_deprecated_get_event_loop": uses_get_event_loop},
        )

    expected_strategy = "separate_thread" if running_loop_present else "asyncio_run"
    if execution_strategy != expected_strategy:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="stripe_toolkit_sync_loop_dispatch_mismatch",
            reason=(
                f"When running_loop_present={running_loop_present}, StripeTool._run must "
                f"use '{expected_strategy}', got '{execution_strategy}' (stripe/ai#581)."
            ),
            evidence={
                "running_loop_present": running_loop_present,
                "sync_execution_strategy": execution_strategy,
            },
        )

    unknown_or_deprecated = config_keys - {"context"}
    if unknown_or_deprecated and fail_open_actions_ignored:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="stripe_toolkit_deprecated_actions_fail_open",
            reason=(
                f"ToolkitCore configuration contains unsupported/deprecated keys "
                f"{sorted(unknown_or_deprecated)} (such as v0.6.x 'actions') that must not "
                "be silently ignored in a fail-open state (stripe/ai#559)."
            ),
            evidence={
                "unsupported_config_keys": sorted(unknown_or_deprecated),
                "fail_open_actions_silently_ignored": fail_open_actions_ignored,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="stripe_toolkit_loop_and_config_verified",
        reason="Stripe Agent Toolkit sync event-loop dispatch and config key validation verified.",
        evidence={
            "sync_execution_strategy": execution_strategy,
            "toolkit_config_keys": sorted(config_keys),
        },
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/go-sdk#1443 & #1441
# ---------------------------------------------------------------------------
def evaluate_mcp_go_windows_file_root_and_int64_id_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce Windows drive-letter `file://` root resolution (`go-sdk#1443`)
    and strict `int64` JSON-RPC numeric ID parsing (`go-sdk#1441`).
    """
    os_platform = str(payload.get("os_platform", "windows")).lower()
    file_uri = str(payload.get("file_root_uri", "file:///C:/Users/me/project"))
    resolved_root = str(payload.get("resolved_file_root", r"C:\Users\me\project"))

    parsed = urlparse(file_uri)
    decoded_path = unquote(parsed.path or "")
    if os_platform == "windows":
        drive_match = WIN_DRIVE_RE.match(decoded_path)
        if not drive_match or ".." in decoded_path.split("/"):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_go_windows_invalid_or_driveless_file_root",
                reason=(
                    f"Windows file root URI '{file_uri}' must contain an explicit drive "
                    "letter without '..' traversal (go-sdk#1443)."
                ),
                evidence={"file_root_uri": file_uri, "decoded_path": decoded_path},
            )
        expected_win_path = drive_match.group(1).replace("/", "\\")
        if resolved_root.startswith("\\") or resolved_root.lower() != expected_win_path.lower():
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_go_windows_leading_slash_drive_root_bug",
                reason=(
                    f"Windows fileURIPath must strip leading slash before drive letter "
                    f"(expected '{expected_win_path}', got '{resolved_root}') (go-sdk#1443)."
                ),
                evidence={
                    "file_root_uri": file_uri,
                    "resolved_file_root": resolved_root,
                    "expected_win_path": expected_win_path,
                },
            )

    raw_id = payload.get("jsonrpc_id", 42)
    if isinstance(raw_id, bool):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_jsonrpc_bool_id_rejected",
            reason="JSON-RPC ID must not be a boolean (go-sdk#1441).",
            evidence={"jsonrpc_id": raw_id},
        )
    if isinstance(raw_id, (int, float)):
        if isinstance(raw_id, float) and (
            math.isnan(raw_id) or math.isinf(raw_id) or not raw_id.is_integer()
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_go_jsonrpc_fractional_or_nonfinite_id_rejected",
                reason=(
                    f"JSON-RPC numeric ID {raw_id!r} is not an exact integer and must fail "
                    "with ErrParse instead of truncating (go-sdk#1441)."
                ),
                evidence={"jsonrpc_id": str(raw_id)},
            )
        int_val = int(raw_id)
        if int_val < INT64_MIN or int_val > INT64_MAX:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_go_jsonrpc_out_of_int64_range_id_rejected",
                reason=(
                    f"JSON-RPC numeric ID {raw_id!r} exceeds int64 bounds and must fail "
                    "with ErrParse instead of wrapping (go-sdk#1441)."
                ),
                evidence={"jsonrpc_id": str(raw_id)},
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_go_windows_root_and_int64_id_verified",
        reason="MCP Go SDK Windows drive-letter root path and int64 JSON-RPC ID verified.",
        evidence={"resolved_file_root": resolved_root, "jsonrpc_id": raw_id},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/go-sdk#1442 & #1438
# ---------------------------------------------------------------------------
def evaluate_mcp_go_oidc_rfc9207_iss_and_id_jag_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce RFC 9207 `iss` validation in `PerformOIDCLogin` (`go-sdk#1442`)
    and `urn:ietf:params:oauth:token-type:id-jag` check in `EnterpriseHandler`
    (`go-sdk#1438`).
    """
    state_matches = bool(payload.get("oauth_state_matches", True))
    idp_issuer = str(payload.get("idp_metadata_issuer", "https://idp.example.com"))
    iss_supported = bool(
        payload.get("authorization_response_iss_parameter_supported", True)
    )
    response_iss = payload.get("authorization_response_iss")
    issued_token_type = str(payload.get("exchange_issued_token_type", ID_JAG_TOKEN_TYPE))

    if not state_matches:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_oidc_state_mismatch",
            reason="OIDC authorization response state parameter mismatch (go-sdk#1442).",
            evidence={"oauth_state_matches": state_matches},
        )

    if iss_supported and not response_iss:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_oidc_rfc9207_missing_required_iss",
            reason=(
                "IdP advertises authorization_response_iss_parameter_supported=true but "
                "authorization response omitted 'iss' (go-sdk#1442)."
            ),
            evidence={
                "idp_metadata_issuer": idp_issuer,
                "authorization_response_iss": response_iss,
            },
        )

    if response_iss is not None and str(response_iss) != idp_issuer:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_oidc_rfc9207_foreign_iss_mixup",
            reason=(
                f"Authorization response 'iss' ({response_iss!r}) does not match IdP "
                f"metadata issuer ({idp_issuer!r}), blocking mix-up attack (go-sdk#1442)."
            ),
            evidence={
                "idp_metadata_issuer": idp_issuer,
                "authorization_response_iss": response_iss,
            },
        )

    if issued_token_type != ID_JAG_TOKEN_TYPE:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_extauth_non_id_jag_token_forwarding_blocked",
            reason=(
                f"EnterpriseHandler.Authorize must refuse RFC 8693 token exchange response "
                f"with issued_token_type={issued_token_type!r} (expected {ID_JAG_TOKEN_TYPE!r}) "
                "to prevent forwarding IdP access tokens to the MCP AS (go-sdk#1438)."
            ),
            evidence={"exchange_issued_token_type": issued_token_type},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_go_oidc_rfc9207_and_id_jag_verified",
        reason="MCP Go SDK PerformOIDCLogin RFC 9207 iss and Enterprise ID-JAG token type verified.",
        evidence={
            "idp_metadata_issuer": idp_issuer,
            "exchange_issued_token_type": issued_token_type,
        },
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/go-sdk#1440, #1425, & #1421
# ---------------------------------------------------------------------------
def evaluate_mcp_go_redirect_origin_discover_auth_and_403_scope_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce same-origin HTTP client redirects (`go-sdk#1440`), no fallback to
    `initialize` when `server/discover` fails authorization (`go-sdk#1425`), and
    `insufficient_scope` in `403 StatusForbidden` `WWW-Authenticate` (`go-sdk#1421`).
    """
    endpoint_url = str(payload.get("endpoint_url", "https://mcp.example.com/v1/mcp"))
    redirect_url = payload.get("redirect_target_url")
    if redirect_url:
        ep = urlparse(endpoint_url)
        rd = urlparse(str(redirect_url))
        if (ep.scheme.lower(), ep.netloc.lower()) != (rd.scheme.lower(), rd.netloc.lower()):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_go_cross_origin_redirect_blocked",
                reason=(
                    f"HTTP client transport must reject cross-origin redirect from "
                    f"'{ep.scheme}://{ep.netloc}' to '{rd.scheme}://{rd.netloc}' (go-sdk#1440)."
                ),
                evidence={
                    "endpoint_url": endpoint_url,
                    "redirect_target_url": redirect_url,
                },
            )

    discover_auth_failed = bool(payload.get("discover_authorization_failed", False))
    fell_back_to_init = bool(payload.get("fell_back_to_initialize", False))
    oauth_authorize_runs = int(payload.get("oauth_authorize_invocations", 1))
    if discover_auth_failed and (fell_back_to_init or oauth_authorize_runs > 1):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_discover_auth_failure_duplicate_initialize_fallback",
            reason=(
                "Client.Connect must terminate immediately when server/discover fails "
                "authorization instead of falling back to initialize and running OAuth "
                "Authorize a second time (go-sdk#1425)."
            ),
            evidence={
                "discover_authorization_failed": discover_auth_failed,
                "fell_back_to_initialize": fell_back_to_init,
                "oauth_authorize_invocations": oauth_authorize_runs,
            },
        )

    http_status = int(payload.get("server_http_status", 200))
    www_authenticate = str(payload.get("www_authenticate_header", ""))
    if http_status == 403 and 'error="insufficient_scope"' not in www_authenticate:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_403_missing_insufficient_scope_www_authenticate",
            reason=(
                "HTTP 403 StatusForbidden response must include error=\"insufficient_scope\" "
                "in WWW-Authenticate header (go-sdk#1421)."
            ),
            evidence={
                "server_http_status": http_status,
                "www_authenticate_header": www_authenticate,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_go_redirect_discover_and_403_scope_verified",
        reason="MCP Go SDK same-origin redirect, discover auth termination, and 403 challenge verified.",
        evidence={
            "endpoint_url": endpoint_url,
            "oauth_authorize_invocations": oauth_authorize_runs,
        },
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/go-sdk#1411
# ---------------------------------------------------------------------------
def evaluate_mcp_go_jsonrpc_preceding_notifications_order_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce FIFO retirement of responses behind preceding notifications on
    `handlerQueue` while allowing immediate retirement for re-entrant nested
    calls from an active synchronous handler (`go-sdk#1411`).
    """
    preceding_notifications = int(payload.get("preceding_notifications_sent", 3))
    notifications_handled_before_return = int(
        payload.get("notifications_handled_before_call_return", 3)
    )
    is_nested_sync_call = bool(payload.get("is_nested_call_from_active_sync_handler", False))
    nested_call_queued_on_handler_queue = bool(
        payload.get("nested_call_queued_on_handler_queue", False)
    )

    if is_nested_sync_call and nested_call_queued_on_handler_queue:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_jsonrpc_nested_sync_handler_deadlock",
            reason=(
                "A nested Call issued by the active synchronous notification handler "
                "(activeSyncReleaser) must retire immediately instead of queuing behind "
                "its own handlerQueue slot (go-sdk#1411)."
            ),
            evidence={
                "is_nested_call_from_active_sync_handler": is_nested_sync_call,
                "nested_call_queued_on_handler_queue": nested_call_queued_on_handler_queue,
            },
        )

    if not is_nested_sync_call and notifications_handled_before_return < preceding_notifications:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_go_jsonrpc_early_response_retirement_dropped_progress",
            reason=(
                f"CallTool returned after only {notifications_handled_before_return}/"
                f"{preceding_notifications} preceding notifications were handled; response "
                "retirement must queue on handlerQueue behind preceding notifications (go-sdk#1411)."
            ),
            evidence={
                "preceding_notifications_sent": preceding_notifications,
                "notifications_handled_before_call_return": notifications_handled_before_return,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_go_jsonrpc_notification_ordering_verified",
        reason="MCP Go SDK preceding notification FIFO retirement and nested sync-call bypass verified.",
        evidence={
            "preceding_notifications_sent": preceding_notifications,
            "notifications_handled_before_call_return": notifications_handled_before_return,
            "is_nested_call_from_active_sync_handler": is_nested_sync_call,
        },
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/rust-sdk#1392 & #1385
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_skills_extension_and_oidc_id_token_exchange_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce SEP-2640 `io.modelcontextprotocol/skills` protocol surface
    (`rust-sdk#1392`) and OIDC `id_token` enterprise token exchange (`rust-sdk#1385`).
    """
    extension_id = str(payload.get("extension_id", SKILLS_EXTENSION_ID))
    requested_method = str(payload.get("skills_method", "skills/list"))
    dir_read_enabled = bool(payload.get("directory_read_capability_enabled", True))

    if extension_id != SKILLS_EXTENSION_ID or requested_method not in SKILLS_ALLOWED_METHODS:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_skills_invalid_extension_or_method",
            reason=(
                f"SEP-2640 Skills extension requires id '{SKILLS_EXTENSION_ID}' and "
                f"method in {sorted(SKILLS_ALLOWED_METHODS)} (rust-sdk#1392)."
            ),
            evidence={
                "extension_id": extension_id,
                "skills_method": requested_method,
            },
        )

    if requested_method == "resources/directory/read" and not dir_read_enabled:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_skills_directory_read_not_advertised",
            reason=(
                "resources/directory/read is optional in SEP-2640 and must be rejected "
                "when the server has not enabled directory read support (rust-sdk#1392)."
            ),
            evidence={"skills_method": requested_method, "directory_read_capability_enabled": dir_read_enabled},
        )

    subject_token_type = str(
        payload.get(
            "ema_subject_token_type", "urn:ietf:params:oauth:token-type:id_token"
        )
    )
    requested_token_type = str(
        payload.get("ema_requested_token_type", ID_JAG_TOKEN_TYPE)
    )
    resource_bound = bool(payload.get("ema_resource_bound_redemption", True))

    if (
        subject_token_type not in ALLOWED_SUBJECT_TOKEN_TYPES
        or requested_token_type != ID_JAG_TOKEN_TYPE
        or not resource_bound
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_ema_invalid_subject_or_unbound_exchange",
            reason=(
                "EmaExchangeRequest must use a valid id_token or refresh_token subject, "
                "request an ID-JAG token, and enforce resource-bound redemption (rust-sdk#1385)."
            ),
            evidence={
                "ema_subject_token_type": subject_token_type,
                "ema_requested_token_type": requested_token_type,
                "ema_resource_bound_redemption": resource_bound,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_rust_skills_and_ema_id_token_verified",
        reason="MCP Rust SDK SEP-2640 Skills surface and OIDC ID-token EMA exchange verified.",
        evidence={
            "extension_id": extension_id,
            "skills_method": requested_method,
            "ema_subject_token_type": subject_token_type,
        },
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/rust-sdk#1390 & #1382
# ---------------------------------------------------------------------------
def _split_outside_quotes(header_value: str, sep: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_quotes = False
    escaped = False
    for ch in header_value:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
            continue
        if ch == sep and not in_quotes:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _extract_essence(content_type: str) -> str:
    # Reject comma-joined essences outside quotes
    comma_parts = _split_outside_quotes(content_type, ",")
    if len(comma_parts) != 1:
        return ""
    semi_parts = _split_outside_quotes(comma_parts[0], ";")
    if not semi_parts:
        return ""
    essence = semi_parts[0].strip().lower()
    if not all(ord(c) < 128 for c in essence):
        return ""
    return essence


def _accept_supports_essence(accept_headers: list[str], target_essence: str) -> bool:
    target = target_essence.lower()
    for hdr in accept_headers:
        for item in _split_outside_quotes(hdr, ","):
            segments = _split_outside_quotes(item, ";")
            if not segments:
                continue
            essence = segments[0].strip().lower()
            if essence != target:
                continue
            q_val = 1.0
            for param in segments[1:]:
                if "=" in param:
                    k, v = param.split("=", 1)
                    if k.strip().lower() == "q":
                        try:
                            q_val = float(v.strip())
                        except ValueError:
                            q_val = 0.0
            if q_val > 0.0:
                return True
    return False


def evaluate_mcp_rust_exact_media_type_and_accept_q_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce exact response media-type essence matching (`rust-sdk#1390`) and
    RFC 9110 `Accept` quality-value parsing (`rust-sdk#1382`).
    """
    response_ct = str(payload.get("response_content_type", "Application/JSON; charset=utf-8"))
    response_essence = _extract_essence(response_ct)
    if response_essence not in {"application/json", "text/event-stream"}:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_invalid_or_suffixed_response_media_type",
            reason=(
                f"Response Content-Type {response_ct!r} does not have an exact "
                "'application/json' or 'text/event-stream' essence (rust-sdk#1390)."
            ),
            evidence={"response_content_type": response_ct, "essence": response_essence},
        )

    request_ct = str(payload.get("request_content_type", "application/json"))
    request_essence = _extract_essence(request_ct)
    if request_essence != "application/json":
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_invalid_or_suffixed_request_content_type",
            reason=(
                f"Request Content-Type {request_ct!r} must have exact essence "
                "'application/json' (rejecting prefix matches like application/jsonx) (rust-sdk#1382)."
            ),
            evidence={"request_content_type": request_ct, "essence": request_essence},
        )

    accept_headers = list(
        payload.get("accept_headers", ["application/json, text/event-stream"])
    )
    if not (
        _accept_supports_essence(accept_headers, "application/json")
        and _accept_supports_essence(accept_headers, "text/event-stream")
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_accept_missing_or_zero_quality_media_type",
            reason=(
                "Streamable HTTP POST requires both 'application/json' and "
                "'text/event-stream' in Accept with q > 0 (rust-sdk#1382)."
            ),
            evidence={"accept_headers": accept_headers},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_rust_media_type_and_accept_q_verified",
        reason="MCP Rust SDK exact media-type essence matching and RFC 9110 Accept q-weights verified.",
        evidence={
            "response_essence": response_essence,
            "request_essence": request_essence,
        },
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/rust-sdk#1383, #1377, & #1375
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_url_elicitation_sessionless_400_and_32602_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce URL elicitation without `elicitationId` (`rust-sdk#1383`),
    session-less non-`initialize` POST returning `400 Bad Request` (`rust-sdk#1377`),
    and known-method invalid params returning `-32602` (`rust-sdk#1375`).
    """
    elicitation_mode = str(payload.get("elicitation_mode", "url"))
    elicitation_id = payload.get("elicitation_id")
    elicitation_fell_through = bool(payload.get("elicitation_fell_through_to_custom", False))
    serialized_empty_id = bool(payload.get("serialized_empty_elicitation_id", False))

    if elicitation_mode == "url" and not elicitation_id:
        if elicitation_fell_through or serialized_empty_id:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_rust_url_elicitation_missing_id_regression",
                reason=(
                    "2026-07-28 URL elicitation without elicitationId must parse cleanly "
                    "(empty string in memory, omitted when serialized) without falling "
                    "through to CustomResult (rust-sdk#1383)."
                ),
                evidence={
                    "elicitation_fell_through_to_custom": elicitation_fell_through,
                    "serialized_empty_elicitation_id": serialized_empty_id,
                },
            )

    stateful_mode = bool(payload.get("stateful_http_mode", True))
    has_session_id = bool(payload.get("has_mcp_session_id", True))
    method = str(payload.get("jsonrpc_method", "tools/call"))
    http_status = int(payload.get("sessionless_post_http_status", 400))

    if stateful_mode and not has_session_id and method not in {"initialize", "server/discover"}:
        if http_status != 400:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_rust_sessionless_post_non_400_status",
                reason=(
                    f"Stateful Streamable HTTP server must respond to session-less "
                    f"non-initialize POST ('{method}') with 400 Bad Request, not {http_status} (rust-sdk#1377)."
                ),
                evidence={"jsonrpc_method": method, "sessionless_post_http_status": http_status},
            )

    method_known = bool(payload.get("method_defined_by_sdk", True))
    method_served_in_lifecycle = bool(payload.get("method_served_in_lifecycle", True))
    params_valid = bool(payload.get("params_valid", True))
    jsonrpc_error_code = payload.get("jsonrpc_error_code")

    if method_known and not method_served_in_lifecycle:
        if jsonrpc_error_code != -32601:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_rust_unserved_lifecycle_method_wrong_error_code",
                reason=(
                    f"Method '{method}' not served in the active lifecycle must return "
                    f"-32601 METHOD_NOT_FOUND, got {jsonrpc_error_code} (rust-sdk#1375)."
                ),
                evidence={"jsonrpc_method": method, "jsonrpc_error_code": jsonrpc_error_code},
            )
    elif method_known and method_served_in_lifecycle and not params_valid:
        if jsonrpc_error_code != -32602:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_rust_known_method_invalid_params_returned_32601",
                reason=(
                    f"Known served method '{method}' with invalid params must return "
                    f"-32602 INVALID_PARAMS instead of falling through to -32601 (rust-sdk#1375)."
                ),
                evidence={"jsonrpc_method": method, "jsonrpc_error_code": jsonrpc_error_code},
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_rust_elicitation_sessionless_400_and_32602_verified",
        reason="MCP Rust SDK URL elicitation, session-less 400 POST, and -32602 dispatch verified.",
        evidence={"jsonrpc_method": method, "http_status": http_status},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/rust-sdk#1379 & modelcontextprotocol/java-sdk#1257
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_java_bounded_child_shutdown_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce `SIGTERM` before `SIGKILL` + `ChildWithCleanup` retention in Rust
    (`rust-sdk#1379`) and bounded `processTerminationTimeout` + `destroyForcibly()`
    in Java (`java-sdk#1257`).
    """
    exits_on_stdin_eof = bool(payload.get("child_exits_on_stdin_eof", False))
    sigterm_sent_before_kill = bool(payload.get("sigterm_sent_before_sigkill", True))
    kept_in_cleanup_guard = bool(payload.get("kept_in_cleanup_guard_until_exit", True))
    java_timeout_ns = int(payload.get("java_process_termination_timeout_ns", 10_000_000_000))
    ignores_sigterm = bool(payload.get("child_ignores_sigterm", False))
    destroy_forcibly_called = bool(payload.get("destroy_forcibly_called_on_timeout", True))

    if not kept_in_cleanup_guard:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_child_removed_from_cleanup_guard_early",
            reason=(
                "Child process must stay inside ChildWithCleanup until exited or killed "
                "so cancelled shutdown futures still clean up on drop (rust-sdk#1379)."
            ),
            evidence={"kept_in_cleanup_guard_until_exit": kept_in_cleanup_guard},
        )

    if not exits_on_stdin_eof and not sigterm_sent_before_kill:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_rust_child_killed_without_sigterm",
            reason=(
                "Graceful stdio shutdown on Unix must send SIGTERM and wait before "
                "falling back to SIGKILL when stdin EOF times out (rust-sdk#1379)."
            ),
            evidence={
                "child_exits_on_stdin_eof": exits_on_stdin_eof,
                "sigterm_sent_before_sigkill": sigterm_sent_before_kill,
            },
        )

    if java_timeout_ns <= 0 or java_timeout_ns > INT64_MAX:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_java_invalid_process_termination_timeout",
            reason=(
                f"ServerParameters.processTerminationTimeout ({java_timeout_ns} ns) must "
                "be positive and <= Long.MAX_VALUE nanoseconds (java-sdk#1257)."
            ),
            evidence={"java_process_termination_timeout_ns": java_timeout_ns},
        )

    if ignores_sigterm and not destroy_forcibly_called:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_java_unbounded_wait_on_term_ignoring_child",
            reason=(
                "StdioClientTransport.closeGracefully() must bound onExit() by "
                "processTerminationTimeout and call destroyForcibly() on timeout (java-sdk#1257)."
            ),
            evidence={
                "child_ignores_sigterm": ignores_sigterm,
                "destroy_forcibly_called_on_timeout": destroy_forcibly_called,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_rust_java_bounded_child_shutdown_verified",
        reason="MCP Rust and Java SDKs bounded SIGTERM -> SIGKILL/destroyForcibly shutdown verified.",
        evidence={
            "sigterm_sent_before_sigkill": sigterm_sent_before_kill,
            "java_process_termination_timeout_ns": java_timeout_ns,
        },
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/csharp-sdk#1953, #1952, & #1949
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_resource_indicators_and_oauth_fallback_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce RFC 9728 `resource_indicators_supported` delegation (`csharp-sdk#1953`),
    default-off `AllowLegacyOAuthMetadataFallback` (`csharp-sdk#1952`), and strict
    `S256` PKCE + exact ordinal `issuer` validation (`csharp-sdk#1949`).
    """
    # null / None means spec-conformant default (True)
    res_ind_supported = payload.get("resource_indicators_supported", None)
    effective_res_ind = True if res_ind_supported is None else bool(res_ind_supported)
    client_sent_resource = bool(payload.get("client_sent_resource_param", True))
    scope_bound_warning_logged = bool(payload.get("scope_bound_warning_logged", False))

    if effective_res_ind and not client_sent_resource:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_csharp_unilateral_resource_parameter_omission",
            reason=(
                "Client must include RFC 8707 'resource' parameter unless protected "
                "resource metadata explicitly sets resource_indicators_supported=false (csharp-sdk#1953)."
            ),
            evidence={
                "resource_indicators_supported": res_ind_supported,
                "client_sent_resource_param": client_sent_resource,
            },
        )

    if not effective_res_ind and (client_sent_resource or not scope_bound_warning_logged):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_csharp_resource_indicator_sent_when_unsupported",
            reason=(
                "When protected resource metadata sets resource_indicators_supported=false, "
                "client must omit the 'resource' parameter and log a scope-binding warning (csharp-sdk#1953)."
            ),
            evidence={
                "resource_indicators_supported": res_ind_supported,
                "client_sent_resource_param": client_sent_resource,
                "scope_bound_warning_logged": scope_bound_warning_logged,
            },
        )

    prm_available = bool(payload.get("protected_resource_metadata_available", True))
    as_metadata_discovered = bool(payload.get("as_metadata_discovered", True))
    allow_legacy_switch = bool(
        payload.get("allow_legacy_oauth_metadata_fallback_switch", False)
    )
    code_methods = list(payload.get("code_challenge_methods_supported", ["S256"]))
    selected_as_id = str(
        payload.get("selected_as_identifier", "https://auth.example.com/tenant1")
    )
    metadata_issuer = payload.get(
        "as_metadata_issuer", "https://auth.example.com/tenant1"
    )

    if not as_metadata_discovered:
        if prm_available or not allow_legacy_switch:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_csharp_unopted_legacy_oauth_metadata_fallback",
                reason=(
                    "Synthetic legacy OAuth endpoint fallback is disabled by default; "
                    "requires resourceUri==null and explicit AllowLegacyOAuthMetadataFallback=true (csharp-sdk#1952)."
                ),
                evidence={
                    "protected_resource_metadata_available": prm_available,
                    "as_metadata_discovered": as_metadata_discovered,
                    "allow_legacy_oauth_metadata_fallback_switch": allow_legacy_switch,
                },
            )
    else:
        if "S256" not in code_methods:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_csharp_discovered_metadata_missing_s256_pkce",
                reason=(
                    "Discovered authorization server metadata must advertise 'S256' in "
                    "code_challenge_methods_supported regardless of fallback switch (csharp-sdk#1949, #1952)."
                ),
                evidence={"code_challenge_methods_supported": code_methods},
            )
        if prm_available and (
            not isinstance(metadata_issuer, str) or metadata_issuer != selected_as_id
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                code="mcp_csharp_as_metadata_issuer_ordinal_mismatch",
                reason=(
                    f"Authorization server metadata issuer ({metadata_issuer!r}) must "
                    f"match selected AS identifier ({selected_as_id!r}) with exact ordinal "
                    "comparison when protected resource metadata is present (csharp-sdk#1949)."
                ),
                evidence={
                    "selected_as_identifier": selected_as_id,
                    "as_metadata_issuer": metadata_issuer,
                },
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_csharp_resource_indicators_and_oauth_verified",
        reason="MCP C# SDK resource_indicators_supported, PKCE S256, and OAuth metadata rules verified.",
        evidence={
            "effective_resource_indicators_supported": effective_res_ind,
            "as_metadata_discovered": as_metadata_discovered,
        },
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/csharp-sdk#1945, #1934, & java-sdk#1266
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_case_sensitive_protocol_and_java_template_notify_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Enforce case-sensitive `ProtocolOptions` (`csharp-sdk#1934`), unwrapped
    `FunctionResultContent.Result` serialization (`csharp-sdk#1945`), and Java SDK
    `removeResourceTemplate` conditional `list_changed` notification (`java-sdk#1266`).
    """
    raw_params: Mapping[str, Any] = payload.get(
        "tools_call_params", {"name": "echo", "arguments": {"text": "hi"}}
    )
    bound_tool_name = payload.get("bound_tool_name", raw_params.get("name"))
    bound_arguments = payload.get("bound_arguments", raw_params.get("arguments"))

    # Under ProtocolOptions, only exact canonical "name" and "arguments" bind
    canonical_name = raw_params.get("name")
    canonical_args = raw_params.get("arguments")
    if canonical_name is None or bound_tool_name != canonical_name:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_csharp_case_insensitive_protocol_name_bypass",
            reason=(
                "ProtocolOptions must match 'params.name' case-sensitively; alternate "
                "casing like 'Name' must not dispatch a tool or override canonical 'name' (csharp-sdk#1934)."
            ),
            evidence={
                "tools_call_params_keys": list(raw_params.keys()),
                "canonical_name": canonical_name,
                "bound_tool_name": bound_tool_name,
            },
        )

    if bound_arguments != canonical_args:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_csharp_case_insensitive_protocol_arguments_bind",
            reason=(
                "ProtocolOptions must match 'params.arguments' case-sensitively; "
                "'Arguments' must not bind as protocol arguments (csharp-sdk#1934)."
            ),
            evidence={
                "canonical_args": canonical_args,
                "bound_arguments": bound_arguments,
            },
        )

    serialized_block_text = str(
        payload.get("to_content_block_serialized_text", '{"temp":"20C"}')
    )
    if '"$type":"functionResult"' in serialized_block_text or '"callId":' in serialized_block_text:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_csharp_to_content_block_leaked_wrapper_envelope",
            reason=(
                "ToContentBlock on FunctionResultContent must serialize resultContent.Result "
                "instead of the outer FunctionResultContent wrapper ($type, callId) (csharp-sdk#1945)."
            ),
            evidence={"to_content_block_serialized_text": serialized_block_text},
        )

    list_changed_cap = bool(payload.get("resources_list_changed_capability", True))
    template_existed = bool(payload.get("removed_template_existed", True))
    notification_sent = bool(payload.get("resources_list_changed_notified", True))
    expected_notify = list_changed_cap and template_existed

    if notification_sent != expected_notify:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            code="mcp_java_remove_resource_template_notification_mismatch",
            reason=(
                f"McpAsyncServer.removeResourceTemplate notification_sent={notification_sent} "
                f"must equal (resources.listChanged && template_existed)={expected_notify} (java-sdk#1266)."
            ),
            evidence={
                "resources_list_changed_capability": list_changed_cap,
                "removed_template_existed": template_existed,
                "resources_list_changed_notified": notification_sent,
            },
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        code="mcp_csharp_protocol_case_and_java_template_notify_verified",
        reason="MCP C# case-sensitive ProtocolOptions, ToContentBlock unwrap, and Java template notify verified.",
        evidence={
            "bound_tool_name": bound_tool_name,
            "resources_list_changed_notified": notification_sent,
        },
    )


GUARD_REGISTRY = {
    "PR-01": evaluate_ucp_complete_checkout_atomic_tx_and_deleted_product_guard,
    "PR-02": evaluate_ucp_reachable_fault_4xx_and_shipment_sync_guard,
    "PR-03": evaluate_ucp_ready_for_complete_a2a_payment_and_single_instrument_guard,
    "PR-04": evaluate_ucp_python_sdk_codegen_datetime_and_dependent_required_guard,
    "PR-05": evaluate_stripe_mcp_proxy_metadata_and_forwarding_error_guard,
    "PR-06": evaluate_stripe_toolkit_event_loop_and_deprecated_actions_guard,
    "PR-07": evaluate_mcp_go_windows_file_root_and_int64_id_guard,
    "PR-08": evaluate_mcp_go_oidc_rfc9207_iss_and_id_jag_guard,
    "PR-09": evaluate_mcp_go_redirect_origin_discover_auth_and_403_scope_guard,
    "PR-10": evaluate_mcp_go_jsonrpc_preceding_notifications_order_guard,
    "PR-11": evaluate_mcp_rust_skills_extension_and_oidc_id_token_exchange_guard,
    "PR-12": evaluate_mcp_rust_exact_media_type_and_accept_q_guard,
    "PR-13": evaluate_mcp_rust_url_elicitation_sessionless_400_and_32602_guard,
    "PR-14": evaluate_mcp_rust_java_bounded_child_shutdown_guard,
    "PR-15": evaluate_mcp_csharp_resource_indicators_and_oauth_fallback_guard,
    "PR-16": evaluate_mcp_csharp_case_sensitive_protocol_and_java_template_notify_guard,
}


def evaluate_stage220_scenario(scenario_id: str, payload: Mapping[str, Any]) -> GuardDecision:
    evaluator = GUARD_REGISTRY.get(scenario_id)
    if evaluator is None:
        raise KeyError(f"Unknown Stage 220 scenario_id: {scenario_id}")
    return evaluator(payload)
