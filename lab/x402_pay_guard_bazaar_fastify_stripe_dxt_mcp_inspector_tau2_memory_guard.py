"""Stage 124 deterministic guardrails:
1. x402 Foundation (#3851, #3845, #3816, #3815, #3842, #3834, #3828, #3825, #3790, #3820):
   - Pre-sign `onBeforePaymentCreation` multi-layer pay guard:
     * Factline (#3851) & anchor-x402-safe-pay (#3845): OFAC SDN sanctions + address reputation
       (drainer, phishing, mixer) + seller uptime/price sanity, fail-closed on unknown/failed/review/block.
     * Tanilo x402 Guard (#3816): `contract-price-match/v0.1` and `spend-cap/v0.1` checks before signing;
       contradicted price/cap or indeterminate/unavailable signed response blocks by default.
     * UTA Trust Kit (#3815): Agent Trust Card (`ATC/1.0`) Ed25519 verification + solvency/risk check.
   - Python async Bazaar discovery (#3842) via `_get_async_client()` + non-empty search query check.
   - Fastify `onSend` settlement-failure body serialization (#3834): send string bodies unchanged unless
     media type ends in `/json` or `+json` (case-insensitive, parameters ignored).
   - Scheme-specific v2 amount format (#3828): digit-only ASCII strings for atomic units or explicit
     network decimal ledger format (XRPL IOU) with zero client-side rounding/rescaling.
   - Go wrapped `*x402.SettleError` HTTP 200 preservation (#3825) & Cardano CIP-30 Paywall `exact` scheme
     (`ADA`/`USDM`, rejecting `script`/`masumi`, min-UTxO + multi-tab lock, #3790).
2. Stripe AI (#480, #515, #543, #552, #560, #550):
   - `@stripe/mcp` DXT manifest 23-tool descriptions & explicit safety notes on the 6 money-moving /
     billing-mutating tools (`create_payment_link`, `finalize_invoice`, `create_refund`,
     `cancel_subscription`, `update_subscription`, `update_dispute`, #480).
   - Claude lifecycle hooks `/stripe|metronome/i` pattern matching (#515, #543), 40-hex commit SHA
     pinning on `sync-agent-plugin` workflow (#552), and `pytest` + `pytest-asyncio` full 51-test
     discovery guard (#560, #550).
3. MCP Inspector v2.10.0 & SEP-3398/3440 (#3418, #3398, #3440) + Sierra tau2-bench (#607, #604, #601, #597):
   - MCP Inspector v2.10.0 threat model (#3418): block `DANGEROUSLY_OMIT_AUTH`, block `0.0.0.0` binding
     without auth token, and prevent `GET /` token leakage or unencrypted volume secret exposure.
   - MCP SEP-3398 March/September 8-month release cycle & SEP-3440 Tasks and Events WG validation.
   - Sierra tau2-bench Policy Harness (#607), Ampup Scoped Memory (`no permissive replay grades`, #604),
     and Salesforce Launa v1 full-duplex voice tick adapter (#601).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

MONEY_MOVING_STRIPE_TOOLS: frozenset[str] = frozenset(
    {
        "create_payment_link",
        "finalize_invoice",
        "create_refund",
        "cancel_subscription",
        "update_subscription",
        "update_dispute",
    }
)

REPUTATION_BAD_TAGS: frozenset[str] = frozenset({"ofac_sdn", "drainer", "phishing", "mixer", "sanctioned"})
CARDANO_ALLOWED_TOKENS: frozenset[str] = frozenset({"ADA", "USDM"})
CARDANO_FORBIDDEN_METHODS: frozenset[str] = frozenset({"script", "masumi"})
ASCII_DIGITS_RE = re.compile(r"^[0-9]+$")
XRPL_DECIMAL_RE = re.compile(r"^[0-9]+(\.[0-9]{1,15})?$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
STRIPE_METRONOME_RE = re.compile(r"(stripe|metronome)", re.IGNORECASE)


@dataclass(frozen=True)
class X402PayGuardBazaarFastifyDecision:
    allowed: bool
    decision_code: str
    serialized_failure_body: str
    http_status_on_settle_error: int
    reason: str


@dataclass(frozen=True)
class StripeDxtHooksPytestDecision:
    allowed: bool
    decision_code: str
    nudge_eligible: bool
    discovered_tests: int
    reason: str


@dataclass(frozen=True)
class McpInspectorReleaseTau2MemoryDecision:
    allowed: bool
    decision_code: str
    policy_harness_pass1_uplift_pts: float
    reason: str


def evaluate_x402_pay_guard_bazaar_fastify(
    payload: Mapping[str, Any],
) -> X402PayGuardBazaarFastifyDecision:
    """Validate x402 #3851/#3845/#3816/#3815, #3842, #3834, #3828, #3825, and #3790."""
    # 1. Pre-sign Factline (#3851) & anchor-x402-safe-pay (#3845) screening
    screening_verdict = str(payload.get("safe_pay_verdict", "allow")).lower()
    reputation_tags = {str(t).lower() for t in (payload.get("reputation_tags") or [])}
    seller_uptime_pct = float(payload.get("seller_uptime_pct", 99.9))

    if screening_verdict != "allow" or (reputation_tags & REPUTATION_BAD_TAGS) or seller_uptime_pct < 90.0:
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_SAFE_PAY_SANCTIONS_OR_REPUTATION_BLOCKED",
            serialized_failure_body="",
            http_status_on_settle_error=402,
            reason="Pre-sign pay guard blocked signing due to OFAC/drainer/phishing verdict or fail-closed screen (#3851/#3845).",
        )

    # 2. Tanilo x402 Guard (#3816): contract-price-match/v0.1 & spend-cap/v0.1
    required_amount_minor = int(payload.get("required_amount_minor", 100))
    contract_price_minor = int(payload.get("contract_price_minor", 100))
    spend_cap_minor = int(payload.get("spend_cap_minor", 500))
    tanilo_eval_state = str(payload.get("tanilo_eval_state", "evaluated_ok"))

    if (
        required_amount_minor > contract_price_minor
        or required_amount_minor > spend_cap_minor
        or tanilo_eval_state in {"indeterminate", "signed_response_unavailable", "contradicted"}
    ):
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_TANILO_PRICE_CAP_OR_INDETERMINATE_BLOCKED",
            serialized_failure_body="",
            http_status_on_settle_error=402,
            reason="Tanilo pre-sign guard rejected contradicted contract price, spend cap, or indeterminate receipt (#3816).",
        )

    # 3. UTA Trust Kit (#3815): ATC/1.0 Ed25519 Agent Trust Card
    if payload.get("require_atc_card", False):
        atc_verified = bool(payload.get("atc_ed25519_verified", False))
        atc_version = str(payload.get("atc_version", ""))
        agent_solvent = bool(payload.get("agent_solvent", False))
        if not (atc_verified and atc_version == "ATC/1.0" and agent_solvent):
            return X402PayGuardBazaarFastifyDecision(
                allowed=False,
                decision_code="X402_UTA_AGENT_TRUST_CARD_REJECTED",
                serialized_failure_body="",
                http_status_on_settle_error=402,
                reason="UTA Trust Kit rejected caller without Ed25519-verified ATC/1.0 card and solvency proof (#3815).",
            )

    # 4. Python async Bazaar discovery (#3842)
    bazaar_client_mode = str(payload.get("bazaar_client_mode", "async_get_async_client"))
    bazaar_search_query = str(payload.get("bazaar_search_query", "weather"))
    if bazaar_client_mode == "sync_missing_get_client" or not bazaar_search_query.strip():
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_BAZAAR_ASYNC_CLIENT_OR_EMPTY_QUERY_ERROR",
            serialized_failure_body="",
            http_status_on_settle_error=400,
            reason="Bazaar discovery requires async _get_async_client() and non-empty search query before HTTP (#3842).",
        )

    # 5. Fastify onSend settlement-failure body serialization (#3834)
    media_type_raw = str(payload.get("settlement_failure_content_type", "text/plain; charset=utf-8"))
    failure_body = payload.get("settlement_failure_body", "Settlement failed: insufficient balance")
    already_json_quoted_plain = bool(payload.get("double_json_encoded_plain_string", False))
    base_media_type = media_type_raw.split(";", 1)[0].strip().lower()
    is_json_media = base_media_type.endswith("/json") or base_media_type.endswith("+json")

    if isinstance(failure_body, str) and not is_json_media and already_json_quoted_plain:
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_FASTIFY_NON_JSON_STRING_DOUBLE_ENCODED",
            serialized_failure_body="",
            http_status_on_settle_error=402,
            reason="Fastify onSend must send non-JSON string settlement-failure bodies as-is without JSON quoting (#3834).",
        )
    serialized_body = failure_body if isinstance(failure_body, str) else str(failure_body)

    # 6. Scheme-specific v2 payment amount format (#3828)
    amount_scheme = str(payload.get("amount_network_scheme", "atomic_uint"))
    amount_str = str(payload.get("amount_value_str", "1000000"))
    client_rescaled = bool(payload.get("client_rounded_or_rescaled", False))
    if client_rescaled:
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_V2_AMOUNT_CLIENT_RESCALE_FORBIDDEN",
            serialized_failure_body=serialized_body,
            http_status_on_settle_error=402,
            reason="x402 v2 clients must validate scheme-specific amount representations rather than round or rescale (#3828).",
        )
    if amount_scheme == "xrpl_iou_decimal":
        if not XRPL_DECIMAL_RE.match(amount_str):
            return X402PayGuardBazaarFastifyDecision(
                allowed=False,
                decision_code="X402_V2_AMOUNT_INVALID_XRPL_DECIMAL",
                serialized_failure_body=serialized_body,
                http_status_on_settle_error=402,
                reason="Invalid XRPL IOU decimal ledger amount format (#3828).",
            )
    else:
        if not ASCII_DIGITS_RE.match(amount_str):
            return X402PayGuardBazaarFastifyDecision(
                allowed=False,
                decision_code="X402_V2_AMOUNT_NON_ASCII_DIGIT_ATOMIC",
                serialized_failure_body=serialized_body,
                http_status_on_settle_error=402,
                reason="Atomic-unit v2 amounts must be digit-only ASCII strings (#3828).",
            )

    # 7. Go wrapped *x402.SettleError preservation (#3825) & Cardano CIP-30 Paywall (#3790)
    is_wrapped_settle_error = bool(payload.get("is_wrapped_settle_error", False))
    settle_error_http_status = int(payload.get("settle_error_http_status", 200))
    tx_hash_preserved = bool(payload.get("settle_error_tx_hash_preserved", True))
    if is_wrapped_settle_error and (settle_error_http_status != 200 or not tx_hash_preserved):
        return X402PayGuardBazaarFastifyDecision(
            allowed=False,
            decision_code="X402_GO_WRAPPED_SETTLE_ERROR_LOST",
            serialized_failure_body=serialized_body,
            http_status_on_settle_error=settle_error_http_status,
            reason="Wrapped *x402.SettleError must map to HTTP 200 SettleResponse preserving transaction hash (#3825).",
        )

    if payload.get("network_family") == "cardano":
        transfer_method = str(payload.get("cardano_transfer_method", "default"))
        cardano_token = str(payload.get("cardano_token", "ADA"))
        min_utxo_satisfied = bool(payload.get("cardano_min_utxo_satisfied", True))
        multi_tab_lock_ok = bool(payload.get("cardano_multi_tab_lock_ok", True))
        if (
            transfer_method in CARDANO_FORBIDDEN_METHODS
            or cardano_token not in CARDANO_ALLOWED_TOKENS
            or not min_utxo_satisfied
            or not multi_tab_lock_ok
        ):
            return X402PayGuardBazaarFastifyDecision(
                allowed=False,
                decision_code="X402_CARDANO_CIP30_PAYWALL_VIOLATION",
                serialized_failure_body=serialized_body,
                http_status_on_settle_error=402,
                reason="Cardano CIP-30 paywall only supports exact default transfer in ADA/USDM with min-UTxO & tab lock (#3790).",
            )

    return X402PayGuardBazaarFastifyDecision(
        allowed=True,
        decision_code="X402_PAY_GUARD_BAZAAR_FASTIFY_OK",
        serialized_failure_body=serialized_body,
        http_status_on_settle_error=200,
        reason="All x402 pre-sign pay guards, async Bazaar, Fastify raw body, v2 amount, and Cardano CIP-30 checks passed.",
    )


def evaluate_stripe_dxt_hooks_pytest_guard(
    payload: Mapping[str, Any],
) -> StripeDxtHooksPytestDecision:
    """Validate Stripe AI #480, #515, #543, #552, and #560/#550."""
    # 1. @stripe/mcp DXT manifest tool descriptions & safety notes (#480)
    manifest_tools: Sequence[Mapping[str, Any]] = payload.get("dxt_manifest_tools") or []
    if manifest_tools:
        for tool in manifest_tools:
            name = str(tool.get("name", "")).strip()
            desc = str(tool.get("description", "")).strip()
            if not desc:
                return StripeDxtHooksPytestDecision(
                    allowed=False,
                    decision_code="STRIPE_DXT_MANIFEST_MISSING_DESCRIPTION",
                    nudge_eligible=False,
                    discovered_tests=0,
                    reason=f"DXT manifest tool '{name}' is missing description before first tools/list (#480).",
                )
            if name in MONEY_MOVING_STRIPE_TOOLS:
                lower_desc = desc.lower()
                has_safety_signal = any(
                    kw in lower_desc
                    for kw in (
                        "safety",
                        "real money",
                        "moves money",
                        "billing state",
                        "customer-visible",
                        "immediate refund or credit",
                    )
                )
                if not has_safety_signal:
                    return StripeDxtHooksPytestDecision(
                        allowed=False,
                        decision_code="STRIPE_DXT_MONEY_TOOL_SAFETY_NOTE_MISSING",
                        nudge_eligible=False,
                        discovered_tests=0,
                        reason=f"Money-moving tool '{name}' lacks an explicit billing/money safety note in DXT manifest (#480).",
                    )

    # 2. Workflow action SHA pinning (#552)
    action_refs: Sequence[str] = payload.get("workflow_action_refs") or []
    for ref in action_refs:
        if "@" not in ref:
            return StripeDxtHooksPytestDecision(
                allowed=False,
                decision_code="STRIPE_WORKFLOW_ACTION_UNPINNED",
                nudge_eligible=False,
                discovered_tests=0,
                reason="sync-agent-plugin workflow action lacks @commit_sha pin (#552).",
            )
        _, sha = ref.rsplit("@", 1)
        if not SHA40_RE.match(sha):
            return StripeDxtHooksPytestDecision(
                allowed=False,
                decision_code="STRIPE_WORKFLOW_ACTION_MUTABLE_TAG_REJECTED",
                nudge_eligible=False,
                discovered_tests=0,
                reason="sync-agent-plugin workflow must pin actions to 40-hex commit SHAs per SAT-31061 (#552).",
            )

    # 3. Claude feedback hooks & Metronome mention detection (#515, #543)
    transcript_text = str(payload.get("transcript_text", "Integrating Stripe and Metronome usage billing"))
    nudge_eligible = bool(STRIPE_METRONOME_RE.search(transcript_text))
    expected_nudge = payload.get("require_metronome_nudge", False)
    if expected_nudge and not nudge_eligible:
        return StripeDxtHooksPytestDecision(
            allowed=False,
            decision_code="STRIPE_METRONOME_FEEDBACK_HOOK_MISSED",
            nudge_eligible=False,
            discovered_tests=0,
            reason="Claude lifecycle feedback hook failed to recognize Metronome/Stripe work (#515/#543).",
        )

    # 4. Python test runner discovery (#560, #550)
    test_runner = str(payload.get("python_test_runner", "pytest"))
    has_pytest_asyncio = bool(payload.get("has_pytest_asyncio", True))
    discovered_tests = int(payload.get("discovered_tests", 51))
    total_expected_tests = int(payload.get("total_expected_tests", 51))

    if test_runner == "unittest_discover" or not has_pytest_asyncio or discovered_tests < total_expected_tests:
        return StripeDxtHooksPytestDecision(
            allowed=False,
            decision_code="STRIPE_PYTHON_SILENT_TEST_SKIP_BLOCKED",
            nudge_eligible=nudge_eligible,
            discovered_tests=discovered_tests,
            reason="Python toolkit must run pytest with pytest-asyncio so all 51 tests execute without silent skip (#560/#550).",
        )

    return StripeDxtHooksPytestDecision(
        allowed=True,
        decision_code="STRIPE_DXT_HOOKS_PYTEST_OK",
        nudge_eligible=nudge_eligible,
        discovered_tests=discovered_tests,
        reason="Stripe DXT manifest safety notes, SHA-pinned workflows, Metronome hooks, and pytest discovery verified.",
    )


def evaluate_mcp_inspector_release_tau2_memory_guard(
    payload: Mapping[str, Any],
) -> McpInspectorReleaseTau2MemoryDecision:
    """Validate MCP #3418, #3398, #3440 and Sierra tau2-bench #607, #604, #601, #597."""
    # 1. MCP Inspector v2.10.0 security threat model (#3418)
    dangerously_omit_auth = bool(payload.get("inspector_dangerously_omit_auth", False))
    bind_host = str(payload.get("inspector_bind_host", "127.0.0.1"))
    api_token_present = bool(payload.get("inspector_api_token_present", True))
    root_get_discloses_token = bool(payload.get("inspector_root_get_discloses_token", False))

    if (
        dangerously_omit_auth
        or (bind_host != "127.0.0.1" and bind_host != "::1" and not api_token_present)
        or root_get_discloses_token
    ):
        return McpInspectorReleaseTau2MemoryDecision(
            allowed=False,
            decision_code="MCP_INSPECTOR_SECURITY_THREAT_BLOCKED",
            policy_harness_pass1_uplift_pts=0.0,
            reason="MCP Inspector v2.10.0 forbids DANGEROUSLY_OMIT_AUTH, unauthenticated 0.0.0.0 binding, or GET / token leak (#3418).",
        )

    # 2. MCP SEP-3398 Release Cycle & SEP-3440 Tasks and Events WG (#3398, #3440)
    release_months = tuple(payload.get("sep3398_release_months", (3, 9)))
    cycle_months = int(payload.get("sep3398_cycle_duration_months", 8))
    tasks_events_wg_unified = bool(payload.get("sep3440_tasks_events_wg_unified", True))
    if release_months != (3, 9) or cycle_months != 8 or not tasks_events_wg_unified:
        return McpInspectorReleaseTau2MemoryDecision(
            allowed=False,
            decision_code="MCP_RELEASE_CYCLE_OR_WG_GOVERNANCE_DRIFT",
            policy_harness_pass1_uplift_pts=0.0,
            reason="SEP-3398 requires March/September releases with 8-month overlapping cycles and SEP-3440 Tasks & Events WG (#3398/#3440).",
        )

    # 3. Sierra tau2-bench Policy Harness (#607), Ampup Scoped Memory (#604), and Launa Voice (#601)
    standard_pass1 = float(payload.get("tau2_standard_pass1", 49.48))
    policy_harness_pass1 = float(payload.get("tau2_policy_harness_pass1", 57.22))
    uplift = round(policy_harness_pass1 - standard_pass1, 2)

    uses_permissive_replay_grades = bool(payload.get("tau2_permissive_replay_grades", False))
    bm25_scoped_to_opened_links = bool(payload.get("ampup_bm25_scoped_to_opened_links", True))
    launa_tick_lifecycle_synced = bool(payload.get("launa_voice_tick_lifecycle_synced", True))

    if uses_permissive_replay_grades or not bm25_scoped_to_opened_links or not launa_tick_lifecycle_synced or uplift < 0.0:
        return McpInspectorReleaseTau2MemoryDecision(
            allowed=False,
            decision_code="TAU2_MEMORY_REPLAY_OR_VOICE_TICK_VIOLATION",
            policy_harness_pass1_uplift_pts=uplift,
            reason="tau2-bench rejects permissive replay grades, unscoped BM25 memory search, or desynced voice tick adapters (#607/#604/#601).",
        )

    return McpInspectorReleaseTau2MemoryDecision(
        allowed=True,
        decision_code="MCP_INSPECTOR_RELEASE_TAU2_MEMORY_OK",
        policy_harness_pass1_uplift_pts=uplift,
        reason="MCP Inspector v2.10.0 threat model, SEP-3398/3440 governance, and tau2-bench Policy Harness/Ampup memory verified.",
    )
