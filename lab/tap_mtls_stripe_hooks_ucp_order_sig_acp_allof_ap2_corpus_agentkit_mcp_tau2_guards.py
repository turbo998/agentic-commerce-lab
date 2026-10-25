"""Stage 252 deterministic protocol & security guards (`PR-01..PR-16`).

Covers 35 non-overlapping primary-source PRs across:
- `visa/trusted-agent-protocol` (`#20`, `#9`, `#6`, `#3`):
  - `PR-01`: Port `9002` parity in `agent-registry/populate_sample_data.py`, deduplicated
    CORS `allow_origins` in `merchant-backend/app/main.py` (`#20`), mTLS client-certificate
    binding (`#9`), PEM/raw-base64 registry key parity (`#6`), and replay-prevention nonce
    window validation (`#3`).
- `stripe/agent-toolkit` (`#576`, `#560`, `#552`, `#550`, `#544`, `#543`, `#541`, `#540`) & Stripe MCP `2026-10-31` cutoff:
  - `PR-02`: Cursor lifecycle hooks (`PostToolUse`, `PostToolUseFailure`, `SessionStart`,
    `beforeSubmitPrompt`, `#576`), full 51-test discovery via `python -m pytest` +
    `pytest-asyncio>=0.21.0` (`#560`, `#550`), and Stripe MCP `2026-10-31` `rak_*` +
    `Stripe-Version: 2026-03-04.preview` readiness.
  - `PR-03`: 40-hex commit SHA pinning on `sync-agent-plugin` workflow (`#552` / `SAT-31061`),
    repointed Claude hook test paths + `/stripe|metronome/i` mention pattern (`#544`, `#543`),
    `strands-agents>=1.0.0` extra (`#541`), and `mcp>=1.0.0,<2.0.0` + `openai-agents`
    dependency bounds (`#540`).
- `Universal-Commerce-Protocol/ucp` (`#988`, `#987`, `#980`, `#979`):
  - `PR-04`: Order MCP binding (`get_order`) RFC 9421 / Detached JWS message signing parity
    with Order REST (`#988`) and per-candidate identity-linking discovery steps 1–3 before
    Selection (`#980`).
  - `PR-05`: Split payments across deferred schedules with `completion_only` instrument
    charge-timing declarations (`#987`) and 5 standardized `fulfillment.events[].type`
    values (`processing`, `shipped`, `in_transit`, `delivered`, `canceled`) + mandatory
    non-empty `description` on custom event types (`#979`).
- `agentic-commerce-protocol/agentic-commerce-protocol` (`#290`, `#284`):
  - `PR-06`: `CheckoutSessionWithOrder` (`allOf: [CheckoutSessionBase, {order}]`) sibling
    `order` property allowance under `additionalProperties: false` (`#290`) and
    `PaymentHandler.display_order` nested inside `properties:` (`#284`).
- `google-agentic-commerce/AP2` (`#371`, `#369`, `#365`, `#364`, `#363`, `#359`, `#355`, `#352`, `#351`, `#349`, `#347`, `#342`):
  - `PR-07`: Signed `sd_jwt` / `kb_sd_jwt` mandate conformance corpus (`contrib/mandate-corpus/`)
    with cross-language verifier rejecting hardcoded `FakeJWT` (`#371`, `#369`) and
    `JWK.from_pyca` EC public-key normalization in `ReceiptClient.verify_receipt` (`#365`).
  - `PR-08`: Redaction of sensitive payment payloads from FastMCP/A2A/Go logs (`#364`),
    multi-hop `~~` delegation chain terminal-hop isolation in `MandateClient.present()`
    (`#363`), and mandatory `H(checkout_jwt) == closed_mandate.checkout_hash` verification
    in `CheckoutMandateChain.verify()` (`#359`).
  - `PR-09`: `mode="json"` enum serialization in `delegate_claims_from_model()` (`#355`),
    `~~`-first splitting in `sdJwtDecoder.ts` (`#351`), post-transaction dispute resolver
    chain binding (`#352`), exact versioned `vct` constants (`#349`), atomic SQLite
    `BEGIN IMMEDIATE` mandate/transaction reservation (`#347`), and mandatory string
    terminal `aud` + `nonce` in KB-SD-JWT (`#342`).
- `google-agentic-commerce/a2a-x402` (`#185`, `#172`, `#137`, `#134`):
  - `PR-10`: `scheme_exact_mist` optimistic batch settlement with escrow bond & 6-hour
    challenge window (`#172`), `provenance-notarization` post-payment output notarization
    (`#137`), `InterlineExecutor` non-custodial direct buyer-to-merchant settlement (`#134`),
    and `exact-nano-mainnet` BLAKE2b + Ed25519 + PoW v2 threshold validation (`#185`).
- `coinbase/agentkit` (`#1586`, `#1583`, `#1581`, `#1580`, `#1571`, `#1570`, `#1569`, `#1567`, `#1566`):
  - `PR-11`: `SwapChan` ranked route selection + ERC-20 approval receipt wait (`#1586`) and
    `Chord` curated token check + deterministic router `0x1b1fee89a381e595fe6536b99ba91f3e16e9601a`
    + slippage floor (`#1566`).
  - `PR-12`: Python AgentKit MCP framework extension with explicit action allowlisting,
    input validation, and sanitized errors (`#1583`) plus `viem` `^2.47.4` (`>=2.47.4 <3`)
    single-copy `ViemWalletProvider` compatibility (`#1581`).
  - `PR-13`: `tapLabsActionProvider` pre-trade x402-paid `check_token_safety` ($0.01 USDC)
    & `check_transaction` ($0.02 USDC Wallet Firewall, `#1580`) and `ncryptedActionProvider`
    client-side `AES-256-GCM` + `HKDF-SHA256` one-time secret links with 5m–7d TTL (`#1567`).
  - `PR-14`: `Triqee` $0.001 USDC x402 lead-lag/FlashFlow guard (`#1571`), `CrewPay`
    60%/15%/25% fee-routing split verification (`#1570`), and `HirePulse` 5/day/IP free
    quota + wallet-less 402 challenge separation (`#1569`).
- `sierra-research/tau2-bench` (`#673`, `#671`, `#668`, `#667`, `#666`, `#665`):
  - `PR-15`: `voice-v1` `canonical_tasks=True` reload in `reload_call_language` during
    `run_simulation` and `tau2 evaluate-trajs` (`#673`) and `.gitattributes` LF line-ending
    preservation preventing Windows `core.autocrlf=true` digest drift on `airline_50` (`#671`).
  - `PR-16`: Retail `exchange_delivered_order_items` rejection when `new_item_id == item_id`
    (`#667`), telecom `can_send_mms` treating `mmsc_url=""` as unconfigured (`#666`), and
    bipartite one-to-one gold-action matching in `_check_actions` (`#665`) + Cortex 0.1
    97x4 `banking_knowledge` trial accounting (`#668`).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Callable, Mapping

WELL_KNOWN_FULFILLMENT_EVENTS = frozenset(
    {"processing", "shipped", "in_transit", "delivered", "canceled"}
)
CHORD_ROUTER_ADDRESS = "0x1b1fee89a381e595fe6536b99ba91f3e16e9601a"
HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")
EXACT_AP2_VCTS = frozenset(
    {
        "https://ap2.dev/vct/open-checkout-mandate/v1",
        "https://ap2.dev/vct/closed-checkout-mandate/v1",
        "https://ap2.dev/vct/open-payment-mandate/v1",
        "https://ap2.dev/vct/closed-payment-mandate/v1",
    }
)


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result returned by a Stage 252 guard evaluator."""

    pr_id: str
    passed: bool
    action: str
    reason: str
    remediation: str
    upstream_pr: str
    details: Mapping[str, Any]


def _fail(
    pr_id: str,
    upstream_pr: str,
    reason: str,
    remediation: str,
    **details: Any,
) -> GuardEvaluation:
    return GuardEvaluation(
        pr_id=pr_id,
        passed=False,
        action="block",
        reason=reason,
        remediation=remediation,
        upstream_pr=upstream_pr,
        details=details,
    )


def _pass(
    pr_id: str,
    upstream_pr: str,
    reason: str,
    **details: Any,
) -> GuardEvaluation:
    return GuardEvaluation(
        pr_id=pr_id,
        passed=True,
        action="allow",
        reason=reason,
        remediation="none",
        upstream_pr=upstream_pr,
        details=details,
    )


def evaluate_visa_tap_port_cors_mtls_and_nonce_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-01: visa/trusted-agent-protocol#20, #9, #6, & #3."""
    pr_id = "PR-01"
    upstream_pr = "visa/trusted-agent-protocol#20, #9, #6, #3"

    base_url_port = int(payload.get("base_url_port", 9002))
    error_message_port = int(payload.get("error_message_port", 0))
    cors_origins = list(payload.get("cors_allow_origins", []))
    mtls_verified = bool(payload.get("mtls_client_cert_verified", False))
    cert_subject_agent_id = str(payload.get("cert_subject_agent_id", ""))
    claimed_agent_id = str(payload.get("claimed_agent_id", ""))
    nonce = str(payload.get("nonce", ""))
    seen_nonces = set(payload.get("seen_nonces", []))
    nonce_age_seconds = int(payload.get("nonce_age_seconds", 9999))
    max_nonce_ttl_seconds = int(payload.get("max_nonce_ttl_seconds", 300))
    registry_key_raw_b64 = bool(payload.get("registry_key_raw_b64", False))

    if base_url_port != 9002 or error_message_port != base_url_port:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                f"TAP populate_sample_data.py error message port ({error_message_port}) "
                f"must match BASE_URL port 9002 (trusted-agent-protocol#20)."
            ),
            remediation="Align error diagnostic port with BASE_URL port 9002 and deduplicate CORS origins.",
            base_url_port=base_url_port,
            error_message_port=error_message_port,
        )

    if len(cors_origins) != len(set(cors_origins)) or not cors_origins:
        return _fail(
            pr_id,
            upstream_pr,
            reason="TAP merchant-backend CORS allow_origins contains duplicate or empty entries (trusted-agent-protocol#20).",
            remediation="Remove duplicate http://localhost:3001 entries from CORS allow_origins.",
            cors_allow_origins=cors_origins,
        )

    if not mtls_verified or not cert_subject_agent_id or cert_subject_agent_id != claimed_agent_id:
        return _fail(
            pr_id,
            upstream_pr,
            reason="TAP mTLS client certificate missing or subject does not match claimed agent_id (trusted-agent-protocol#9).",
            remediation="Verify mTLS client certificate and bind subject SAN/CN to the active agent_id.",
            mtls_verified=mtls_verified,
            cert_subject_agent_id=cert_subject_agent_id,
            claimed_agent_id=claimed_agent_id,
        )

    if not nonce or nonce in seen_nonces or nonce_age_seconds < 0 or nonce_age_seconds > max_nonce_ttl_seconds:
        return _fail(
            pr_id,
            upstream_pr,
            reason="TAP request nonce is missing, replayed, or outside the allowed freshness window (trusted-agent-protocol#3).",
            remediation="Require a fresh, single-use cryptographic nonce within the TTL window.",
            nonce=nonce,
            replayed=nonce in seen_nonces,
            nonce_age_seconds=nonce_age_seconds,
        )

    if not registry_key_raw_b64:
        return _fail(
            pr_id,
            upstream_pr,
            reason="TAP registry database must store compact raw base64 public keys synchronized from PEM config (trusted-agent-protocol#6).",
            remediation="Synchronize PEM keys across components and store raw base64 public keys in registry DB.",
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="Visa TAP port 9002 parity, deduplicated CORS, mTLS client-cert binding, and nonce anti-replay verified.",
        agent_id=claimed_agent_id,
        nonce=nonce,
    )


def evaluate_stripe_cursor_hooks_pytest_async_and_mcp_cutoff_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-02: stripe/agent-toolkit#576, #560, #550 & Stripe MCP 2026-10-31 cutoff."""
    pr_id = "PR-02"
    upstream_pr = "stripe/agent-toolkit#576, #560, #550; docs.stripe.com/mcp.md"

    cursor_hooks = set(payload.get("cursor_hooks", []))
    required_hooks = {"PostToolUse", "PostToolUseFailure", "SessionStart", "beforeSubmitPrompt"}
    test_runner = str(payload.get("python_test_runner", ""))
    pytest_asyncio_installed = bool(payload.get("pytest_asyncio_installed", False))
    discovered_tests = int(payload.get("discovered_tests", 0))
    async_tests_executed = int(payload.get("async_tests_executed", 0))
    mcp_key_prefix = str(payload.get("stripe_mcp_key_prefix", ""))
    stripe_version = str(payload.get("stripe_version_header", ""))
    cutoff_date = str(payload.get("cutoff_date", ""))

    if not required_hooks.issubset(cursor_hooks):
        return _fail(
            pr_id,
            upstream_pr,
            reason="Cursor plugin must register PostToolUse, PostToolUseFailure, SessionStart, and beforeSubmitPrompt hooks (agent-toolkit#576).",
            remediation="Register all 4 Cursor lifecycle hooks for feedback injection, skill telemetry, and CLI guidance.",
            missing_hooks=sorted(required_hooks - cursor_hooks),
        )

    if "pytest" not in test_runner or not pytest_asyncio_installed or discovered_tests < 51 or async_tests_executed < 8:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "tools/python test suite must run via pytest with pytest-asyncio>=0.21.0 so all 51 tests "
                "(including 8 async tests) execute instead of unittest discover skipping 48 tests (agent-toolkit#560, #550)."
            ),
            remediation="Switch Makefile test target to python -m pytest and add pytest-asyncio>=0.21.0.",
            python_test_runner=test_runner,
            discovered_tests=discovered_tests,
            async_tests_executed=async_tests_executed,
        )

    if mcp_key_prefix != "rak_" or stripe_version != "2026-03-04.preview" or cutoff_date != "2026-10-31":
        return _fail(
            pr_id,
            upstream_pr,
            reason="Stripe MCP requests must use Restricted API Keys (rak_*) and Stripe-Version: 2026-03-04.preview ahead of 2026-10-31 cutoff.",
            remediation="Migrate legacy sk_live_*/rk_live_* keys to rak_* before 2026-10-31.",
            mcp_key_prefix=mcp_key_prefix,
            stripe_version=stripe_version,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="Stripe Cursor lifecycle hooks, 51-test pytest-asyncio discovery, and 2026-10-31 rak_* MCP readiness verified.",
        discovered_tests=discovered_tests,
        async_tests_executed=async_tests_executed,
    )


def evaluate_stripe_workflow_sha_strands_and_mcp_v1_cap_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-03: stripe/agent-toolkit#552, #544, #543, #541, & #540."""
    pr_id = "PR-03"
    upstream_pr = "stripe/agent-toolkit#552, #544, #543, #541, #540"

    workflow_action_refs = list(payload.get("workflow_action_refs", []))
    claude_hook_test_target = str(payload.get("claude_hook_test_target", ""))
    mention_regex = str(payload.get("mention_regex", ""))
    strands_dep = str(payload.get("strands_extra_dep", ""))
    mcp_dep_spec = str(payload.get("mcp_dep_spec", ""))
    openai_extra_dep = str(payload.get("openai_extra_dep", ""))

    if not workflow_action_refs or any(not HEX_40_RE.match(str(ref)) for ref in workflow_action_refs):
        return _fail(
            pr_id,
            upstream_pr,
            reason="sync-agent-plugin workflow must pin GitHub Actions to 40-hex commit SHAs per SAT-31061 (agent-toolkit#552).",
            remediation="Replace mutable version tags with full 40-character commit SHAs in workflow files.",
            workflow_action_refs=workflow_action_refs,
        )

    if "providers/claude/plugin/scripts" not in claude_hook_test_target or "metronome" not in mention_regex.lower():
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "Claude hook tests must resolve providers/claude/plugin/scripts/ and match "
                "/stripe|metronome/i in feedback hooks (agent-toolkit#544, #543)."
            ),
            remediation="Repoint moved Claude hook test paths and use STRIPE_MENTION_PATTERN = /stripe|metronome/i.",
            claude_hook_test_target=claude_hook_test_target,
            mention_regex=mention_regex,
        )

    if not strands_dep.startswith("strands-agents") or "<2" not in mcp_dep_spec or not openai_extra_dep.startswith("openai-agents"):
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "pyproject.toml must depend on strands-agents (not the physics package 'strands'), "
                "cap mcp>=1.0.0,<2.0.0 to retain streamablehttp_client, and use openai-agents (agent-toolkit#541, #540)."
            ),
            remediation="Set strands extra to strands-agents>=1.0.0, mcp>=1.0.0,<2.0.0, and openai extra to openai-agents.",
            strands_dep=strands_dep,
            mcp_dep_spec=mcp_dep_spec,
            openai_extra_dep=openai_extra_dep,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="Stripe workflow 40-hex SHA pinning, Metronome hook matching, strands-agents extra, and mcp<2.0.0 cap verified.",
        mcp_dep_spec=mcp_dep_spec,
    )


def evaluate_ucp_order_mcp_signing_and_identity_discovery_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-04: Universal-Commerce-Protocol/ucp#988 & #980."""
    pr_id = "PR-04"
    upstream_pr = "Universal-Commerce-Protocol/ucp#988, #980"

    binding = str(payload.get("order_binding", "mcp"))
    request_signed = bool(payload.get("get_order_request_signed", False))
    response_signed = bool(payload.get("get_order_response_signed", False))
    signature_bound_to_jsonrpc_id = bool(payload.get("signature_bound_to_jsonrpc_id", False))
    candidates = list(payload.get("identity_candidates", []))
    evaluated_all_before_selection = bool(payload.get("evaluated_all_candidates_before_selection", False))
    selected_issuer = str(payload.get("selected_issuer", ""))

    if binding == "mcp" and (not request_signed or not response_signed or not signature_bound_to_jsonrpc_id):
        return _fail(
            pr_id,
            upstream_pr,
            reason="UCP Order MCP binding (get_order) must sign requests and business responses with JSON-RPC id/params binding matching Order REST (ucp#988).",
            remediation="Attach Detached JWS / RFC 9421 signature metadata on Order MCP get_order requests and responses.",
            request_signed=request_signed,
            response_signed=response_signed,
            signature_bound_to_jsonrpc_id=signature_bound_to_jsonrpc_id,
        )

    valid_issuers = [
        str(c.get("issuer"))
        for c in candidates
        if isinstance(c, Mapping)
        and c.get("step1_resolved")
        and c.get("step2_metadata_valid")
        and c.get("step3_capabilities_matched")
    ]
    if not evaluated_all_before_selection or not valid_issuers or selected_issuer not in valid_issuers:
        return _fail(
            pr_id,
            upstream_pr,
            reason="UCP identity-linking Discovery Steps 1-3 must evaluate every candidate issuer before Selection picks a winner (ucp#980).",
            remediation="Run Discovery Steps 1-3 per candidate entry and perform Selection only over fully validated candidates.",
            evaluated_all_before_selection=evaluated_all_before_selection,
            selected_issuer=selected_issuer,
            valid_issuers=valid_issuers,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="UCP Order MCP message signing and per-candidate identity-linking Discovery-before-Selection verified.",
        selected_issuer=selected_issuer,
    )


def evaluate_ucp_split_deferred_payments_and_fulfillment_events_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-05: Universal-Commerce-Protocol/ucp#987 & #979."""
    pr_id = "PR-05"
    upstream_pr = "Universal-Commerce-Protocol/ucp#987, #979"

    schedules = list(payload.get("payment_schedules", []))
    instruments = {
        str(inst.get("id")): inst
        for inst in payload.get("payment_instruments", [])
        if isinstance(inst, Mapping) and inst.get("id")
    }
    events = list(payload.get("fulfillment_events", []))

    if not schedules or not instruments:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Split payment terms require non-empty payment_schedules and payment_instruments (ucp#987).",
            remediation="Provide explicit schedule allocations and instrument charge_timing capabilities.",
        )

    for sched in schedules:
        if not isinstance(sched, Mapping):
            return _fail(pr_id, upstream_pr, "Invalid schedule entry.", "Use object entries.")
        timing = str(sched.get("timing", ""))
        inst_id = str(sched.get("instrument_id", ""))
        inst = instruments.get(inst_id)
        if inst is None:
            return _fail(
                pr_id,
                upstream_pr,
                reason=f"Schedule references unknown payment instrument '{inst_id}' (ucp#987).",
                remediation="Bind every payment schedule to an advertised payment instrument.",
            )
        inst_charge_timing = str(inst.get("charge_timing", "any_schedule"))
        if timing == "deferred" and inst_charge_timing == "completion_only":
            return _fail(
                pr_id,
                upstream_pr,
                reason=(
                    f"Instrument '{inst_id}' is declared charge_timing='completion_only' and "
                    "cannot fund a deferred payment schedule (ucp#987)."
                ),
                remediation="Assign completion_only instruments exclusively to immediate completion charges and fund deferred schedules with schedule-capable instruments.",
                instrument_id=inst_id,
                schedule_timing=timing,
            )

    if not events:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Order fulfillment must contain at least one fulfillment event (ucp#979).",
            remediation="Emit standardized fulfillment.events[].type values.",
        )

    for ev in events:
        if not isinstance(ev, Mapping):
            return _fail(pr_id, upstream_pr, "Invalid fulfillment event.", "Use object entries.")
        ev_type = str(ev.get("type", "")).strip()
        semantic_stage = str(ev.get("semantic_stage", "")).strip()
        description = str(ev.get("description", "")).strip()
        if not ev_type:
            return _fail(pr_id, upstream_pr, "Fulfillment event type is empty (ucp#979).", "Set event.type.")
        if semantic_stage in WELL_KNOWN_FULFILLMENT_EVENTS and ev_type != semantic_stage:
            return _fail(
                pr_id,
                upstream_pr,
                reason=(
                    f"Fulfillment event with well-known semantics '{semantic_stage}' MUST use the "
                    f"standardized type '{semantic_stage}', not '{ev_type}' (ucp#979)."
                ),
                remediation="Use processing, shipped, in_transit, delivered, or canceled when semantics match.",
                ev_type=ev_type,
                semantic_stage=semantic_stage,
            )
        if ev_type not in WELL_KNOWN_FULFILLMENT_EVENTS and not description:
            return _fail(
                pr_id,
                upstream_pr,
                reason=f"Custom fulfillment event type '{ev_type}' MUST include a non-empty description (ucp#979).",
                remediation="Add a customer-facing description to custom fulfillment event types.",
                ev_type=ev_type,
            )

    return _pass(
        pr_id,
        upstream_pr,
        reason="UCP split payments across deferred schedules and standardized fulfillment event types verified.",
        schedule_count=len(schedules),
        event_count=len(events),
    )


def evaluate_acp_checkout_with_order_allof_and_display_order_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-06: agentic-commerce-protocol/agentic-commerce-protocol#290 & #284."""
    pr_id = "PR-06"
    upstream_pr = "agentic-commerce-protocol/agentic-commerce-protocol#290, #284"

    base_blocks_sibling_order = bool(payload.get("base_additional_properties_blocks_order", False))
    checkout_with_order_allows_order = bool(payload.get("checkout_with_order_allows_order", False))
    order_present = isinstance(payload.get("order"), Mapping) and bool(payload.get("order"))
    display_order_under_properties = bool(payload.get("payment_handler_display_order_under_properties", False))
    display_order_value = payload.get("display_order")

    if base_blocks_sibling_order or not checkout_with_order_allows_order or not order_present:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "CheckoutSessionWithOrder must allow the sibling 'order' field without "
                "CheckoutSessionBase additionalProperties: false rejecting it (acp#290)."
            ),
            remediation="Use unevaluatedProperties: false or explicit order property allowance on CheckoutSessionWithOrder.",
            base_blocks_sibling_order=base_blocks_sibling_order,
            checkout_with_order_allows_order=checkout_with_order_allows_order,
        )

    if not display_order_under_properties or not isinstance(display_order_value, int) or isinstance(display_order_value, bool) or display_order_value < 0:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "PaymentHandler.display_order must be nested inside 'properties:' in "
                "openapi.agentic_checkout.yaml so additionalProperties: false accepts integer display_order (acp#284)."
            ),
            remediation="Indent display_order under PaymentHandler.properties in both dated and unreleased OpenAPI specs.",
            display_order_under_properties=display_order_under_properties,
            display_order=display_order_value,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="ACP CheckoutSessionWithOrder 'order' allowance and PaymentHandler.properties.display_order nesting verified.",
        display_order=display_order_value,
    )


def evaluate_ap2_mandate_conformance_corpus_and_ec_receipt_key_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-07: google-agentic-commerce/AP2#371, #369, & #365."""
    pr_id = "PR-07"
    upstream_pr = "google-agentic-commerce/AP2#371, #369, #365"

    token = str(payload.get("mandate_token", ""))
    has_corpus_fixtures = bool(payload.get("has_signed_mandate_corpus", False))
    second_language_verified = bool(payload.get("second_language_verifier_passed", False))
    receipt_key_kind = str(payload.get("receipt_public_key_kind", ""))
    normalized_via_from_pyca = bool(payload.get("normalized_via_jwk_from_pyca", False))

    if not token or "FakeJWT" in token or token.startswith("eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0"):
        return _fail(
            pr_id,
            upstream_pr,
            reason="Hardcoded FakeJWT or unsigned placeholder mandate tokens are forbidden (AP2#371, #369).",
            remediation="Sign mandates with sd_jwt.create / kb_sd_jwt.create and verify against contrib/mandate-corpus/ fixtures.",
            mandate_token=token[:32],
        )

    if not has_corpus_fixtures or not second_language_verified:
        return _fail(
            pr_id,
            upstream_pr,
            reason="AP2 mandate conformance requires signed corpus fixtures verified by an independent second-language verifier (AP2#371, #369).",
            remediation="Validate signed SD-JWT+kb mandate fixtures across Python and the independent cross-language verifier.",
            has_corpus_fixtures=has_corpus_fixtures,
            second_language_verified=second_language_verified,
        )

    if receipt_key_kind == "pyca_ec" and not normalized_via_from_pyca:
        return _fail(
            pr_id,
            upstream_pr,
            reason="ReceiptClient.verify_receipt must normalize cryptography EC public keys via JWK.from_pyca before JWT verification (AP2#365).",
            remediation="Call JWK.from_pyca(public_key) when verify_receipt receives a cryptography EllipticCurvePublicKey.",
            receipt_key_kind=receipt_key_kind,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AP2 signed mandate conformance corpus, cross-language verifier, and JWK.from_pyca EC receipt verification verified.",
        receipt_key_kind=receipt_key_kind,
    )


def evaluate_ap2_log_redaction_multihop_present_and_checkout_hash_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-08: google-agentic-commerce/AP2#364, #363, & #359."""
    pr_id = "PR-08"
    upstream_pr = "google-agentic-commerce/AP2#364, #363, #359"

    fastmcp_include_payloads = bool(payload.get("fastmcp_logging_include_payloads", True))
    logged_fields = set(payload.get("logged_fields", []))
    forbidden_log_fields = {"payment_token", "post_payload", "checkout_mandate", "risk_data", "raw_request_body"}

    chain = str(payload.get("sd_jwt_chain", ""))
    prior_hop_tampered = bool(payload.get("prior_hop_disclosure_tampered", False))
    terminal_hop_isolated = bool(payload.get("terminal_hop_isolated_in_present", False))

    presented_checkout_jwt = str(payload.get("presented_checkout_jwt", ""))
    closed_mandate_checkout_hash = str(payload.get("closed_mandate_checkout_hash", ""))

    if fastmcp_include_payloads or (logged_fields & forbidden_log_fields):
        return _fail(
            pr_id,
            upstream_pr,
            reason="AP2 servers and processors must not log sensitive payment payloads, tokens, mandates, or risk_data (AP2#364).",
            remediation="Disable include_payloads=True on FastMCP LoggingMiddleware and log only body-free status/count diagnostics.",
            leaked_fields=sorted(logged_fields & forbidden_log_fields),
        )

    hops = [h for h in chain.split("~~") if h]
    if len(hops) < 2 or not terminal_hop_isolated or prior_hop_tampered:
        return _fail(
            pr_id,
            upstream_pr,
            reason="MandateClient.present() must split multi-hop chains on '~~', isolate the terminal hop for hash binding/redaction, and reject tampered prior hops (AP2#363).",
            remediation="Isolate the last SD-JWT hop in MandateClient.present() while preserving and verifying all earlier hops.",
            hop_count=len(hops),
            prior_hop_tampered=prior_hop_tampered,
        )

    computed_hash = hashlib.sha256(presented_checkout_jwt.encode("utf-8")).hexdigest() if presented_checkout_jwt else ""
    if not computed_hash or computed_hash != closed_mandate_checkout_hash:
        return _fail(
            pr_id,
            upstream_pr,
            reason="CheckoutMandateChain.verify() must always compute H(presented_checkout_jwt) and match closed_mandate.checkout_hash even when expected_checkout_hash is omitted (AP2#359).",
            remediation="Derive SHA-256 digest from presented checkout_jwt and enforce equality with closed_mandate.checkout_hash.",
            computed_hash=computed_hash,
            closed_mandate_checkout_hash=closed_mandate_checkout_hash,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AP2 payment log redaction, multi-hop ~~ delegation isolation, and mandatory closed_mandate.checkout_hash binding verified.",
        hop_count=len(hops),
        checkout_hash=computed_hash,
    )


def evaluate_ap2_enum_json_dispute_vct_atomic_consume_and_kb_claims_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-09: google-agentic-commerce/AP2#355, #352, #351, #349, #347, & #342."""
    pr_id = "PR-09"
    upstream_pr = "google-agentic-commerce/AP2#355, #352, #351, #349, #347, #342"

    recurrence_frequency_value = payload.get("recurrence_frequency_serialized")
    decoder_splits_double_tilde_first = bool(payload.get("decoder_splits_double_tilde_first", False))
    mandate_vct = str(payload.get("mandate_vct", ""))
    atomic_sqlite_immediate = bool(payload.get("atomic_sqlite_begin_immediate", False))
    already_consumed = bool(payload.get("mandate_or_tx_already_consumed", False))
    terminal_aud = payload.get("terminal_kb_aud")
    terminal_nonce = payload.get("terminal_kb_nonce")
    dispute_references_match = bool(payload.get("dispute_chain_references_match", False))

    if not isinstance(recurrence_frequency_value, str) or not recurrence_frequency_value:
        return _fail(
            pr_id,
            upstream_pr,
            reason="delegate_claims_from_model() must use model_dump(mode='json') so Frequency enums serialize as strings instead of raising TypeError (AP2#355).",
            remediation="Dump Pydantic mandate claim models with mode='json' before SD-JWT disclosure hashing.",
        )

    if not decoder_splits_double_tilde_first:
        return _fail(
            pr_id,
            upstream_pr,
            reason="sdJwtDecoder.ts must split on '~~' before '~' so second-hop disclosures are not misread as a trailing KB-JWT (AP2#351).",
            remediation="Split multi-hop dSD-JWT strings on '~~' first and decode each hop independently.",
        )

    if mandate_vct not in EXACT_AP2_VCTS:
        return _fail(
            pr_id,
            upstream_pr,
            reason=f"Mandate VCT '{mandate_vct}' does not match an exact versioned AP2 VCT constant (AP2#349).",
            remediation="Use exact versioned VCT URIs (e.g. https://ap2.dev/vct/closed-payment-mandate/v1).",
            mandate_vct=mandate_vct,
        )

    if not atomic_sqlite_immediate or already_consumed:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Accepted Payment Mandate hash and Checkout transaction_id must be reserved atomically via SQLite BEGIN IMMEDIATE (AP2#347).",
            remediation="Reserve mandate hash and checkout transaction_id in an immediate SQLite transaction with a unique constraint.",
            atomic_sqlite_immediate=atomic_sqlite_immediate,
            already_consumed=already_consumed,
        )

    if not isinstance(terminal_aud, str) or not terminal_aud.strip() or not isinstance(terminal_nonce, str) or not terminal_nonce.strip():
        return _fail(
            pr_id,
            upstream_pr,
            reason="Terminal KB-SD-JWT verification requires non-empty string 'aud' and 'nonce' claims per RFC 9901 §4.3 (AP2#342).",
            remediation="Reject terminal KB-SD-JWTs with missing, empty, or non-string aud or nonce claims.",
            terminal_aud=terminal_aud,
            terminal_nonce=terminal_nonce,
        )

    if not dispute_references_match:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Post-transaction AP2 dispute resolver requires payment_mandate.transaction_id and both receipts' reference to match closed_mandate (AP2#352).",
            remediation="Verify full authorization chain binding across checkout mandate, payment mandate, and receipts.",
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AP2 JSON-mode enum serialization, dSD-JWT ~~ decoder, exact VCT, atomic SQLite reservation, terminal aud/nonce, and dispute chain verified.",
        mandate_vct=mandate_vct,
    )


def evaluate_a2a_x402_mist_batch_provenance_interline_and_nano_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-10: google-agentic-commerce/a2a-x402#185, #172, #137, & #134."""
    pr_id = "PR-10"
    upstream_pr = "google-agentic-commerce/a2a-x402#185, #172, #137, #134"

    mist_bond_covered = bool(payload.get("mist_operator_bond_covers_epoch_total", False))
    mist_challenge_hours = int(payload.get("mist_challenge_window_hours", 0))
    provenance_notarized = bool(payload.get("provenance_output_hash_bound_to_payment_tx", False))
    interline_non_custodial = bool(payload.get("interline_direct_buyer_to_merchant_settlement", False))
    interline_holds_keys = bool(payload.get("interline_router_holds_merchant_keys", True))
    nano_work_threshold = int(payload.get("nano_work_threshold", 0))
    min_nano_work = 0xFFFFFFF800000000

    if not mist_bond_covered or mist_challenge_hours < 6:
        return _fail(
            pr_id,
            upstream_pr,
            reason="scheme_exact_mist batch settlement requires operator escrow bond >= epoch net total and >= 6-hour challenge window before bond release (a2a-x402#172).",
            remediation="Enforce operator bond collateralization and a minimum 6-hour challenge window on Base batch epochs.",
            mist_bond_covered=mist_bond_covered,
            mist_challenge_hours=mist_challenge_hours,
        )

    if not provenance_notarized:
        return _fail(
            pr_id,
            upstream_pr,
            reason="provenance-notarization requires post-payment merchant signature over (output_hash, timestamp, payment_tx_hash) (a2a-x402#137).",
            remediation="Notarize merchant output hash against the settling x402 transaction hash and timestamp.",
        )

    if not interline_non_custodial or interline_holds_keys:
        return _fail(
            pr_id,
            upstream_pr,
            reason="InterlineExecutor must settle funds directly buyer -> merchant wallet without holding merchant keys or custody (a2a-x402#134).",
            remediation="Verify neutral router settles directly to merchant payTo address with zero custodial key retention.",
        )

    if nano_work_threshold < min_nano_work:
        return _fail(
            pr_id,
            upstream_pr,
            reason="exact-nano-mainnet requires BLAKE2b + Ed25519 + PoW v2 work_threshold >= 0xfffffff800000000 (a2a-x402#185).",
            remediation="Reject Nano mainnet blocks below the 0xfffffff800000000 work threshold.",
            nano_work_threshold=hex(nano_work_threshold),
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="A2A-x402 Mist batch escrow/challenge, post-payment provenance notarization, non-custodial Interline router, and Nano PoW v2 verified.",
        mist_challenge_hours=mist_challenge_hours,
    )


def evaluate_agentkit_swapchan_and_chord_router_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-11: coinbase/agentkit#1586 & #1566."""
    pr_id = "PR-11"
    upstream_pr = "coinbase/agentkit#1586, #1566"

    swapchan_routes_count = int(payload.get("swapchan_ranked_routes_count", 0))
    approval_required = bool(payload.get("swapchan_approval_required", False))
    approval_receipt_confirmed = bool(payload.get("swapchan_approval_receipt_confirmed", False))
    chord_router = str(payload.get("chord_router_address", "")).lower()
    chord_token_curated = bool(payload.get("chord_token_on_curated_list", False))
    expected_out = int(payload.get("chord_expected_output", 0))
    min_out = int(payload.get("chord_minimum_output", 0))

    if swapchan_routes_count < 1 or swapchan_routes_count > 5:
        return _fail(
            pr_id,
            upstream_pr,
            reason="SwapChan quote action must rank between 1 and 5 routes by net output (agentkit#1586).",
            remediation="Bound get_swap_quote_from_swapchan to 1..5 net-output-ranked routes.",
            swapchan_routes_count=swapchan_routes_count,
        )

    if approval_required and not approval_receipt_confirmed:
        return _fail(
            pr_id,
            upstream_pr,
            reason="execute_swap_on_swapchan must wait for the ERC-20 approval transaction receipt before broadcasting the swap transaction (agentkit#1586).",
            remediation="Await approval receipt confirmation before submitting the swap transaction via EvmWalletProvider.",
        )

    if chord_router != CHORD_ROUTER_ADDRESS or not chord_token_curated or min_out <= 0 or expected_out < min_out:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "Chord swap must settle through router 0x1b1fee89a381e595fe6536b99ba91f3e16e9601a, "
                "verify curated token index status, and enforce expected_output >= minimum_output > 0 (agentkit#1566)."
            ),
            remediation="Pin Chord router address, require curated token verification, and enforce minimum_output slippage floor.",
            chord_router=chord_router,
            chord_token_curated=chord_token_curated,
            expected_out=expected_out,
            min_out=min_out,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AgentKit SwapChan approval-receipt ordering and Chord router/curated-token/slippage invariants verified.",
        chord_router=chord_router,
    )


def evaluate_agentkit_python_mcp_extension_and_viem_range_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-12: coinbase/agentkit#1583 & #1581."""
    pr_id = "PR-12"
    upstream_pr = "coinbase/agentkit#1583, #1581"

    allowlisted_actions = set(payload.get("mcp_allowlisted_actions", []))
    requested_action = str(payload.get("requested_mcp_action", ""))
    input_schema_validated = bool(payload.get("mcp_input_schema_validated", False))
    error_sanitized = bool(payload.get("mcp_error_response_sanitized", False))
    viem_specifier = str(payload.get("viem_dependency_specifier", ""))
    duplicate_viem_copies = int(payload.get("duplicate_viem_copies", 2))

    if not allowlisted_actions or requested_action not in allowlisted_actions or not input_schema_validated or not error_sanitized:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "Python AgentKit MCP extension must enforce explicit action allowlisting, "
                "input schema validation, and sanitized error responses (agentkit#1583)."
            ),
            remediation="Reject non-allowlisted AgentKit actions over MCP, validate tool inputs, and scrub raw tracebacks from error responses.",
            requested_action=requested_action,
            allowlisted=requested_action in allowlisted_actions,
        )

    if viem_specifier != "^2.47.4" or duplicate_viem_copies != 1:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "@coinbase/agentkit must specify viem as '^2.47.4' (>=2.47.4 <3) rather than exact '2.47.4' "
                "so newer viem 2.x projects share 1 copy without TS2345 ViemWalletProvider type splits (agentkit#1581)."
            ),
            remediation="Widen viem dependency specifier to '^2.47.4' and deduplicate lockfile copies.",
            viem_specifier=viem_specifier,
            duplicate_viem_copies=duplicate_viem_copies,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AgentKit Python MCP extension allowlist/sanitization and viem ^2.47.4 single-copy compatibility verified.",
        requested_action=requested_action,
    )


def evaluate_agentkit_tap_labs_firewall_and_ncrypted_secret_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-13: coinbase/agentkit#1580 & #1567."""
    pr_id = "PR-13"
    upstream_pr = "coinbase/agentkit#1580, #1567"

    token_safety_passed = bool(payload.get("tap_labs_token_safety_passed", False))
    tx_firewall_passed = bool(payload.get("tap_labs_tx_firewall_passed", False))
    ofac_clear = bool(payload.get("tap_labs_ofac_clear", False))
    safety_fee_usdc = float(payload.get("tap_labs_safety_fee_usdc", 0.0))
    firewall_fee_usdc = float(payload.get("tap_labs_firewall_fee_usdc", 0.0))

    secret_cipher = str(payload.get("ncrypted_cipher", ""))
    secret_kdf = str(payload.get("ncrypted_kdf", ""))
    ttl_seconds = int(payload.get("ncrypted_ttl_seconds", 0))
    one_time_read = bool(payload.get("ncrypted_destroyed_after_first_read", False))
    plaintext_in_chat_or_log = bool(payload.get("plaintext_secret_in_chat_or_log", True))

    if not token_safety_passed or not tx_firewall_passed or not ofac_clear or safety_fee_usdc > 0.01 or firewall_fee_usdc > 0.02:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "tapLabsActionProvider requires pre-trade check_token_safety (<= $0.01 USDC), "
                "check_transaction Wallet Firewall (<= $0.02 USDC), and OFAC/scam clearance before execution (agentkit#1580)."
            ),
            remediation="Run TAP Labs Safety Check and Wallet Firewall before signing trades and block OFAC/honeypot targets.",
            token_safety_passed=token_safety_passed,
            tx_firewall_passed=tx_firewall_passed,
            ofac_clear=ofac_clear,
        )

    if (
        secret_cipher != "AES-256-GCM"
        or secret_kdf != "HKDF-SHA256"
        or ttl_seconds < 300
        or ttl_seconds > 604800
        or not one_time_read
        or plaintext_in_chat_or_log
    ):
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "ncryptedActionProvider must encrypt secrets locally with AES-256-GCM + HKDF-SHA256, "
                "bound TTL to 300..604800s (5m..7d), destroy on first read, and never expose plaintext in chat/logs (agentkit#1567)."
            ),
            remediation="Use client-side AES-256-GCM/HKDF-SHA256 one-time links with 5m-7d TTL instead of logging secrets.",
            secret_cipher=secret_cipher,
            ttl_seconds=ttl_seconds,
            plaintext_in_chat_or_log=plaintext_in_chat_or_log,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AgentKit TAP Labs pre-trade Wallet Firewall and ncrypted AES-256-GCM one-time secret links verified.",
        ttl_seconds=ttl_seconds,
    )


def evaluate_agentkit_triqee_crewpay_and_hirepulse_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-14: coinbase/agentkit#1571, #1570, & #1569."""
    pr_id = "PR-14"
    upstream_pr = "coinbase/agentkit#1571, #1570, #1569"

    triqee_leadlag_fee_usdc = float(payload.get("triqee_leadlag_fee_usdc", 1.0))
    triqee_flashflow_simulated = bool(payload.get("triqee_flashflow_simulated_before_route", False))
    crew_pct = int(payload.get("crewpay_crew_fee_pct", 0))
    agent_pct = int(payload.get("crewpay_agent_fee_pct", 0))
    treasury_pct = int(payload.get("crewpay_treasury_fee_pct", 0))
    hirepulse_accesses_wallet = bool(payload.get("hirepulse_provider_accesses_wallet", True))
    hirepulse_free_daily_lookups = int(payload.get("hirepulse_free_daily_lookups_used", 0))
    hirepulse_402_challenge_returned = bool(payload.get("hirepulse_402_challenge_returned_when_over_quota", False))

    if triqee_leadlag_fee_usdc > 0.001 or not triqee_flashflow_simulated:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Triqee get_leadlag_divergence x402 fee must be <= $0.001 USDC on Base and simulate_flashflow must run before routing (agentkit#1571).",
            remediation="Cap Triqee lead-lag x402 micropayment at $0.001 USDC and require FlashFlow pre-trade simulation.",
            triqee_leadlag_fee_usdc=triqee_leadlag_fee_usdc,
        )

    if (crew_pct, agent_pct, treasury_pct) != (60, 15, 25):
        return _fail(
            pr_id,
            upstream_pr,
            reason=f"CrewPay fee split must route exactly 60% crew / 15% agent / 25% treasury, got {crew_pct}/{agent_pct}/{treasury_pct} (agentkit#1570).",
            remediation="Verify CrewPay fee map matches 60/15/25 before launching a token on Base.",
            fee_split=(crew_pct, agent_pct, treasury_pct),
        )

    if hirepulse_accesses_wallet or (hirepulse_free_daily_lookups > 5 and not hirepulse_402_challenge_returned):
        return _fail(
            pr_id,
            upstream_pr,
            reason="HirePulse provider must never access a wallet or sign payments directly, and must emit an x402 challenge after 5 free daily lookups per IP (agentkit#1569).",
            remediation="Keep HirePulse action provider wallet-less and delegate 402 challenges to a separate payment client.",
            hirepulse_accesses_wallet=hirepulse_accesses_wallet,
            hirepulse_free_daily_lookups=hirepulse_free_daily_lookups,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="AgentKit Triqee $0.001 x402 + FlashFlow simulation, CrewPay 60/15/25 fee split, and HirePulse wallet-less 402 separation verified.",
        fee_split=(crew_pct, agent_pct, treasury_pct),
    )


def evaluate_tau2_voice_canonical_tasks_and_windows_lf_hash_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-15: sierra-research/tau2-bench#673 & #671."""
    pr_id = "PR-15"
    upstream_pr = "sierra-research/tau2-bench#673, #671"

    benchmark_name = str(payload.get("benchmark", "voice-v1"))
    reload_canonical_tasks = bool(payload.get("reload_call_language_canonical_tasks", False))
    evaluate_trajs_canonical_tasks = bool(payload.get("evaluate_trajs_canonical_tasks", False))
    gitattributes_lf_enforced = bool(payload.get("gitattributes_text_lf_enforced", False))
    subset_line_endings = str(payload.get("subset_file_line_endings", "CRLF"))
    recorded_sha256 = str(payload.get("recorded_subset_sha256", ""))
    computed_sha256 = str(payload.get("computed_subset_sha256", ""))

    if benchmark_name == "voice-v1" and (not reload_canonical_tasks or not evaluate_trajs_canonical_tasks):
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "voice-v1 reload_call_language (in run_simulation and tau2 evaluate-trajs) must pass "
                "canonical_tasks=True so English retail/telecom pins match canonical registry tasks (tau2-bench#673)."
            ),
            remediation="Pass canonical_tasks=True when reloading voice-v1 language bindings and exports.",
            reload_canonical_tasks=reload_canonical_tasks,
            evaluate_trajs_canonical_tasks=evaluate_trajs_canonical_tasks,
        )

    if not gitattributes_lf_enforced or subset_line_endings != "LF" or not recorded_sha256 or recorded_sha256 != computed_sha256:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "Frozen benchmark subset files (e.g. airline_50) must stay at LF via .gitattributes "
                "so Windows core.autocrlf=true checkouts do not fail SHA-256 pin verification (tau2-bench#671)."
            ),
            remediation="Enforce LF line endings in .gitattributes and verify frozen subset SHA-256 digests match.",
            subset_line_endings=subset_line_endings,
            recorded_sha256=recorded_sha256,
            computed_sha256=computed_sha256,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="tau2-bench voice-v1 canonical_tasks=True reload and Windows LF frozen-subset SHA-256 integrity verified.",
        computed_sha256=computed_sha256,
    )


def evaluate_tau2_retail_same_item_mms_empty_url_and_bipartite_gold_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-16: sierra-research/tau2-bench#668, #667, #666, & #665."""
    pr_id = "PR-16"
    upstream_pr = "sierra-research/tau2-bench#668, #667, #666, #665"

    old_item_id = str(payload.get("exchange_old_item_id", ""))
    new_item_id = str(payload.get("exchange_new_item_id", ""))
    same_item_rejected = bool(payload.get("same_item_exchange_rejected", False))

    mmsc_url = payload.get("apn_mmsc_url")
    can_send_mms_result = bool(payload.get("can_send_mms_result", True))

    gold_action_repeats = int(payload.get("repeated_gold_action_count", 1))
    distinct_predicted_matches = int(payload.get("distinct_predicted_tool_calls_matched", 0))
    one_to_one_enforced = bool(payload.get("bipartite_one_to_one_matching", False))

    if old_item_id == new_item_id and not same_item_rejected:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                "exchange_delivered_order_items must reject new_item_id == item_id with "
                "'The new item id should be different from the old item id' (tau2-bench#667)."
            ),
            remediation="Reject same-item exchanges in exchange_delivered_order_items matching modify_pending_order_items.",
            old_item_id=old_item_id,
            new_item_id=new_item_id,
        )

    mmsc_configured = bool(mmsc_url and str(mmsc_url).strip())
    if can_send_mms_result != mmsc_configured:
        return _fail(
            pr_id,
            upstream_pr,
            reason="Telecom can_send_mms must treat empty string mmsc_url='' as unconfigured via bool(self.mmsc_url) (tau2-bench#666).",
            remediation="Use APNSettings.is_mms_basic_configured() (bool(self.mmsc_url)) in _can_send_mms.",
            mmsc_url=mmsc_url,
            can_send_mms_result=can_send_mms_result,
        )

    if not one_to_one_enforced or distinct_predicted_matches < gold_action_repeats:
        return _fail(
            pr_id,
            upstream_pr,
            reason=(
                f"_check_actions must match repeated gold actions one-to-one against distinct predicted tool calls "
                f"({distinct_predicted_matches} distinct calls < {gold_action_repeats} required) (tau2-bench#665)."
            ),
            remediation="Consume each matched predicted tool call index once when evaluating repeated gold actions.",
            gold_action_repeats=gold_action_repeats,
            distinct_predicted_matches=distinct_predicted_matches,
        )

    return _pass(
        pr_id,
        upstream_pr,
        reason="tau2-bench same-item exchange rejection, empty MMSC URL check, and one-to-one gold-action matching verified.",
        gold_action_repeats=gold_action_repeats,
        distinct_predicted_matches=distinct_predicted_matches,
    )


STAGE252_GUARD_EVALUATORS: Mapping[str, Callable[[Mapping[str, Any]], GuardEvaluation]] = {
    "PR-01": evaluate_visa_tap_port_cors_mtls_and_nonce_guard,
    "PR-02": evaluate_stripe_cursor_hooks_pytest_async_and_mcp_cutoff_guard,
    "PR-03": evaluate_stripe_workflow_sha_strands_and_mcp_v1_cap_guard,
    "PR-04": evaluate_ucp_order_mcp_signing_and_identity_discovery_guard,
    "PR-05": evaluate_ucp_split_deferred_payments_and_fulfillment_events_guard,
    "PR-06": evaluate_acp_checkout_with_order_allof_and_display_order_guard,
    "PR-07": evaluate_ap2_mandate_conformance_corpus_and_ec_receipt_key_guard,
    "PR-08": evaluate_ap2_log_redaction_multihop_present_and_checkout_hash_guard,
    "PR-09": evaluate_ap2_enum_json_dispute_vct_atomic_consume_and_kb_claims_guard,
    "PR-10": evaluate_a2a_x402_mist_batch_provenance_interline_and_nano_guard,
    "PR-11": evaluate_agentkit_swapchan_and_chord_router_guard,
    "PR-12": evaluate_agentkit_python_mcp_extension_and_viem_range_guard,
    "PR-13": evaluate_agentkit_tap_labs_firewall_and_ncrypted_secret_guard,
    "PR-14": evaluate_agentkit_triqee_crewpay_and_hirepulse_guard,
    "PR-15": evaluate_tau2_voice_canonical_tasks_and_windows_lf_hash_guard,
    "PR-16": evaluate_tau2_retail_same_item_mms_empty_url_and_bipartite_gold_guard,
}


def evaluate_stage252_guards(
    scenarios: Mapping[str, Mapping[str, Any]],
) -> dict[str, GuardEvaluation]:
    """Run all 16 Stage 252 deterministic guards across a scenario map."""
    results: dict[str, GuardEvaluation] = {}
    for pr_id, evaluator in STAGE252_GUARD_EVALUATORS.items():
        results[pr_id] = evaluator(scenarios.get(pr_id, {}))
    return results
