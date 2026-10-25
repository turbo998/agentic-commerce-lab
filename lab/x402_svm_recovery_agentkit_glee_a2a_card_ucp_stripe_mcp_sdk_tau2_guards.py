"""Stage 254 deterministic runtime guards (255-Stage Milestone!).

Covers 42 non-overlapping primary-source PRs across:
- x402 Foundation (`x402-foundation/x402` #3933, #3932, #3931, #3913, #3863, #3839, #3836, #3832)
- Coinbase AgentKit (`coinbase/agentkit` #1588, #1561, #1560, #1559, #1557, #1556, #1554, #1553, #1552, #1551, #1550, #1549)
- Agent2Agent Protocol (`a2aproject/A2A` #2382, #2380, #2378, #2375, #2369, #2364, #2362, #2352)
- Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp` #990, #989, #984, #920, #892, #884 & `samples` #209)
- Stripe Agent Toolkit (`stripe/agent-toolkit` #539, #475, #427 + Stripe MCP 2026-10-31 key cutoff)
- Model Context Protocol SDKs & Spec (`typescript-sdk` #3098, #3099, #3086, #3052, #3048; `go-sdk` #1433, #1402, #1357, #1355, #1381; `rust-sdk` #1369, #1331, #1380, #1329; `ruby-sdk` #539, #475; `php-sdk` #539, #437; `conformance` #416; `ext-apps` #777, #733, #718, #768; `modelcontextprotocol` #3447, #3446, #3439)
- Sierra tau2-bench (`sierra-research/tau2-bench` #656, #648, #643, #539)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class GuardEvaluationResult:
    guard_id: str
    passed: bool
    action: str
    reason: str
    rule_ref: str
    checked_fields: List[str]


def evaluate_x402_svm_pending_store_recovery_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-01: x402-foundation/x402 #3933 — SVM pending-store read error recovery."""
    checked = [
        "pending_store_read_error",
        "go_lookup_error_returned_before_settlement",
        "ts_duplicate_entry_released_only_if_owned",
        "existing_pending_records_preserved",
        "settlement_allowed_on_unknown_pending_state",
    ]
    read_err = bool(payload.get("pending_store_read_error", False))
    go_err_returned = bool(payload.get("go_lookup_error_returned_before_settlement", False))
    ts_released_owned = bool(payload.get("ts_duplicate_entry_released_only_if_owned", False))
    preserved = bool(payload.get("existing_pending_records_preserved", False))
    settled_blindly = bool(payload.get("settlement_allowed_on_unknown_pending_state", True))

    if read_err and settled_blindly:
        return GuardEvaluationResult(
            guard_id="PR-01",
            passed=False,
            action="BLOCK_BLIND_SVM_SETTLEMENT_ON_PENDING_READ_ERROR",
            reason="Go exact/upto discarded pending-store Get errors and proceeded with settlement without knowing if a prior tx is pending (#3933)",
            rule_ref="x402-foundation/x402#3933",
            checked_fields=checked,
        )
    if not (go_err_returned and ts_released_owned and preserved):
        return GuardEvaluationResult(
            guard_id="PR-01",
            passed=False,
            action="REJECT_STALE_DUPLICATE_LOCK_OR_UNRETURNED_LOOKUP_ERR",
            reason="Must return Go lookup error before reconciliation and release TS duplicate entry only when owned by current invocation (#3933)",
            rule_ref="x402-foundation/x402#3933",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-01",
        passed=True,
        action="ALLOW_RECOVERABLE_SVM_PENDING_STORE_HANDLING",
        reason="SVM facilitator returns pending-store lookup errors pre-settlement and releases only invocation-owned duplicate entries",
        rule_ref="x402-foundation/x402#3933",
        checked_fields=checked,
    )


def evaluate_x402_svm_go_exact_mint_token_program_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-02: x402-foundation/x402 #3932 — Go exact payments respect mint token program (Token-2022)."""
    checked = [
        "mint_token_program",
        "source_ata_token_program",
        "dest_ata_token_program",
        "transfer_checked_token_program",
        "shared_mutable_program_state",
    ]
    mint_prog = str(payload.get("mint_token_program", ""))
    src_prog = str(payload.get("source_ata_token_program", ""))
    dst_prog = str(payload.get("dest_ata_token_program", ""))
    tx_prog = str(payload.get("transfer_checked_token_program", ""))
    shared_mutable = bool(payload.get("shared_mutable_program_state", True))

    if not mint_prog or src_prog != mint_prog or dst_prog != mint_prog or tx_prog != mint_prog:
        return GuardEvaluationResult(
            guard_id="PR-02",
            passed=False,
            action="BLOCK_LEGACY_SPL_PROGRAM_MISMATCH_FOR_TOKEN2022",
            reason="Go exact client derived ATAs or built TransferChecked with legacy SPL program instead of mint's Token-2022 program (#3932)",
            rule_ref="x402-foundation/x402#3932",
            checked_fields=checked,
        )
    if shared_mutable:
        return GuardEvaluationResult(
            guard_id="PR-02",
            passed=False,
            action="REJECT_SHARED_MUTABLE_TOKEN_PROGRAM_STATE",
            reason="Token program selection must stay local to the instruction so mixed-token clients do not share mutable state (#3932)",
            rule_ref="x402-foundation/x402#3932",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-02",
        passed=True,
        action="ALLOW_MINT_SCOPED_SVM_EXACT_PAYMENT",
        reason="Go exact client derives source/destination ATAs and TransferChecked with the mint's token program without shared mutable state",
        rule_ref="x402-foundation/x402#3932",
        checked_fields=checked,
    )


def evaluate_x402_cryptonly_facilitator_v2_spec_express_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-03: x402-foundation/x402 #3931, #3913, #3863, #3839, #3836, #3832."""
    checked = [
        "facilitator_tenant_api_key_header_present",
        "sanctions_screened_before_settlement",
        "express_middleware_symbol",
        "v2_spec_markdown_headings_normalized",
    ]
    tenant_key = bool(payload.get("facilitator_tenant_api_key_header_present", False))
    sanctions_ok = bool(payload.get("sanctions_screened_before_settlement", False))
    express_sym = str(payload.get("express_middleware_symbol", ""))
    headings_ok = bool(payload.get("v2_spec_markdown_headings_normalized", False))

    if express_sym != "paymentMiddleware":
        return GuardEvaluationResult(
            guard_id="PR-03",
            passed=False,
            action="REJECT_STALE_REQUIRE_PAYMENT_EXPRESS_API",
            reason="v2 Express SDK exports paymentMiddleware(), not stale require_payment() (#3839)",
            rule_ref="x402-foundation/x402#3931,#3839,#3863,#3913,#3836,#3832",
            checked_fields=checked,
        )
    if not (tenant_key and sanctions_ok and headings_ok):
        return GuardEvaluationResult(
            guard_id="PR-03",
            passed=False,
            action="BLOCK_UNAUTHENTICATED_OR_UNSCREENED_FACILITATOR",
            reason="Cryptonly facilitator requires X-Tenant-Api-Key header, pre-settlement sanctions screening, and normalized v2 spec anchors (#3931, #3863)",
            rule_ref="x402-foundation/x402#3931,#3839,#3863,#3913,#3836,#3832",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-03",
        passed=True,
        action="ALLOW_CRYPTONLY_FACILITATOR_AND_V2_EXPRESS_MIDDLEWARE",
        reason="Cryptonly X-Tenant-Api-Key + sanctions screening and @x402/express paymentMiddleware() verified",
        rule_ref="x402-foundation/x402#3931,#3839,#3863,#3913,#3836,#3832",
        checked_fields=checked,
    )


def evaluate_agentkit_erc20_unconfirmed_receipt_pre_payment_hook_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-04: coinbase/agentkit #1556, #1550 — ERC20 unconfirmed receipt state & x402 prePaymentCheck hook."""
    checked = [
        "tx_sent_hash_present",
        "receipt_lookup_failed",
        "reported_transfer_state",
        "tx_hash_retained_in_response",
        "pre_payment_check_allowed",
        "signature_created_after_hook_denial",
    ]
    tx_sent = bool(payload.get("tx_sent_hash_present", False))
    receipt_failed = bool(payload.get("receipt_lookup_failed", False))
    state = str(payload.get("reported_transfer_state", ""))
    hash_retained = bool(payload.get("tx_hash_retained_in_response", False))
    hook_allowed = bool(payload.get("pre_payment_check_allowed", True))
    signed_after_denial = bool(payload.get("signature_created_after_hook_denial", False))

    if tx_sent and receipt_failed and (state != "UNCONFIRMED" or not hash_retained):
        return GuardEvaluationResult(
            guard_id="PR-04",
            passed=False,
            action="BLOCK_FALSE_FAILURE_DUPLICATE_ERC20_TRANSFER",
            reason="Sent ERC20 transfer/approve with failed receipt lookup must report UNCONFIRMED with tx hash to prevent duplicate agent retries (#1556)",
            rule_ref="coinbase/agentkit#1556,#1550",
            checked_fields=checked,
        )
    if (not hook_allowed) and signed_after_denial:
        return GuardEvaluationResult(
            guard_id="PR-04",
            passed=False,
            action="BLOCK_X402_SIGNING_AFTER_PRE_PAYMENT_HOOK_DENIAL",
            reason="prePaymentCheck returning {allow: false} must abort x402 signing before any payment signature is created (#1550)",
            rule_ref="coinbase/agentkit#1556,#1550",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-04",
        passed=True,
        action="ALLOW_SAFE_ERC20_UNCONFIRMED_AND_PRE_PAYMENT_HOOK",
        reason="ERC20 receipt timeout preserves tx hash in UNCONFIRMED state and x402 prePaymentCheck gates pre-signing",
        rule_ref="coinbase/agentkit#1556,#1550",
        checked_fields=checked,
    )


def evaluate_agentkit_glee_receipt_canaryguard_bazaar_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-05: coinbase/agentkit #1560, #1559, #1557 — GLEE Ed25519 receipt, CanaryGuard <5ms firewall & x402 Bazaar."""
    checked = [
        "glee_trusted_pay_to_pinned",
        "glee_receipt_ed25519_verified",
        "glee_atomic_usdc_amount",
        "canary_guard_inspection_ms",
        "canary_guard_wallet_drain_detected",
        "bazaar_facilitator_registered",
    ]
    pay_to_pinned = bool(payload.get("glee_trusted_pay_to_pinned", False))
    ed25519_ok = bool(payload.get("glee_receipt_ed25519_verified", False))
    atomic_usdc = int(payload.get("glee_atomic_usdc_amount", 0))
    canary_ms = float(payload.get("canary_guard_inspection_ms", 999.0))
    drain_detected = bool(payload.get("canary_guard_wallet_drain_detected", True))
    bazaar_ok = bool(payload.get("bazaar_facilitator_registered", False))

    if not pay_to_pinned or not ed25519_ok or atomic_usdc != 50000:
        return GuardEvaluationResult(
            guard_id="PR-05",
            passed=False,
            action="REJECT_UNVERIFIED_GLEE_PATCH_RECEIPT_OR_PRICE",
            reason="GLEE verifier requires pinned trustedPayTo, 50,000 atomic USDC ($0.05) price check, and verified glee.acceptance_receipt.v0 Ed25519 receipt (#1560)",
            rule_ref="coinbase/agentkit#1560,#1559,#1557",
            checked_fields=checked,
        )
    if drain_detected or canary_ms > 5.0 or not bazaar_ok:
        return GuardEvaluationResult(
            guard_id="PR-05",
            passed=False,
            action="BLOCK_CANARYGUARD_DRAIN_OR_UNREGISTERED_BAZAAR",
            reason="CanaryGuard must block wallet-draining prompt injections in <=5ms (#1559) with registered x402 Bazaar facilitator (#1557)",
            rule_ref="coinbase/agentkit#1560,#1559,#1557",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-05",
        passed=True,
        action="ALLOW_VERIFIED_GLEE_CANARYGUARD_BAZAAR_FLOW",
        reason="GLEE Ed25519 acceptance receipt, CanaryGuard <5ms firewall, and x402 Bazaar discovery verified",
        rule_ref="coinbase/agentkit#1560,#1559,#1557",
        checked_fields=checked,
    )


def evaluate_agentkit_finance_graph_agentsvc_risk_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-06: coinbase/agentkit #1588, #1561, #1554, #1553, #1552, #1551, #1549."""
    checked = [
        "erc8004_liveness_level",
        "statement_merkle_ed25519_root_verified",
        "agentsvc_asset_is_usdc",
        "agentsvc_network_matches_wallet",
        "counterparty_has_open_incident_flags",
    ]
    liveness = str(payload.get("erc8004_liveness_level", ""))
    merkle_ok = bool(payload.get("statement_merkle_ed25519_root_verified", False))
    usdc_ok = bool(payload.get("agentsvc_asset_is_usdc", False))
    net_ok = bool(payload.get("agentsvc_network_matches_wallet", False))
    open_flags = bool(payload.get("counterparty_has_open_incident_flags", True))

    if liveness not in {"L7", "L8", "L9"} or not merkle_ok or open_flags:
        return GuardEvaluationResult(
            guard_id="PR-06",
            passed=False,
            action="BLOCK_UNPROVEN_ERC8004_COUNTERPARTY_PAYMENT",
            reason="Agentic Finance Graph requires L7-L9 observed payment liveness, verified Merkle statement against Ed25519 root, and zero open incident flags (#1553)",
            rule_ref="coinbase/agentkit#1553,#1552,#1561,#1588,#1554,#1551,#1549",
            checked_fields=checked,
        )
    if not (usdc_ok and net_ok):
        return GuardEvaluationResult(
            guard_id="PR-06",
            passed=False,
            action="REJECT_NON_USDC_OR_CROSS_NETWORK_AGENTSVC_CALL",
            reason="agentsvc pay-per-call safety checks allow only USDC on the wallet's own network (#1552)",
            rule_ref="coinbase/agentkit#1553,#1552,#1561,#1588,#1554,#1551,#1549",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-06",
        passed=True,
        action="ALLOW_FINANCE_GRAPH_AND_AGENTSVC_CHECKED_PAYMENT",
        reason="ERC-8004 counterparty liveness/Merkle statement and agentsvc same-network USDC safety checks passed",
        rule_ref="coinbase/agentkit#1553,#1552,#1561,#1588,#1554,#1551,#1549",
        checked_fields=checked,
    )


def evaluate_a2a_agent_card_media_type_root_operation_v1_header_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-07: a2aproject/A2A #2380, #2378, #2375 — Agent Card media type, GetAgentCard root op & A2A-Version 1.0."""
    checked = [
        "agent_card_media_type",
        "protocol_message_media_type",
        "root_get_agent_card_operation_bound",
        "request_body_version",
        "a2a_version_header",
    ]
    card_mime = str(payload.get("agent_card_media_type", ""))
    msg_mime = str(payload.get("protocol_message_media_type", ""))
    root_op = bool(payload.get("root_get_agent_card_operation_bound", False))
    body_ver = str(payload.get("request_body_version", ""))
    hdr_ver = str(payload.get("a2a_version_header", ""))

    if card_mime != "application/a2a-agent-card+json" or msg_mime != "application/a2a+json" or not root_op:
        return GuardEvaluationResult(
            guard_id="PR-07",
            passed=False,
            action="REJECT_INVALID_A2A_AGENT_CARD_MIME_OR_ROOT_OP",
            reason="Agent Card documents must use application/a2a-agent-card+json distinct from application/a2a+json and bind GetAgentCard at root (#2380, #2378)",
            rule_ref="a2aproject/A2A#2380,#2378,#2375",
            checked_fields=checked,
        )
    if body_ver == "1.0" and hdr_ver != "1.0":
        return GuardEvaluationResult(
            guard_id="PR-07",
            passed=False,
            action="REJECT_A2A_V03_HEADER_ON_V10_REQUEST_BODY",
            reason="Sending A2A-Version: 0.3 with v1.0 request bodies triggers VersionNotSupportedError (-32009 / HTTP 400); must send A2A-Version: 1.0 (#2375)",
            rule_ref="a2aproject/A2A#2380,#2378,#2375",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-07",
        passed=True,
        action="ALLOW_CONFORMANT_A2A_V10_CARD_AND_REQUEST",
        reason="A2A Agent Card MIME type, GetAgentCard root operation, and A2A-Version: 1.0 header match specification",
        rule_ref="a2aproject/A2A#2380,#2378,#2375",
        checked_fields=checked,
    )


def evaluate_a2a_rfc8785_es256_card_sig_pascal_method_fresh_auth_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-08: a2aproject/A2A #2369, #2364, #2362, #2352, #2382."""
    checked = [
        "card_signature_rfc8785_es256_verified",
        "signatures_excluded_from_canonical_payload",
        "jsonrpc_method_name",
        "agent_card_security_field_name",
        "auth_required_retrieved_on_fresh_connection",
    ]
    sig_ok = bool(payload.get("card_signature_rfc8785_es256_verified", False))
    sig_excl = bool(payload.get("signatures_excluded_from_canonical_payload", False))
    method_name = str(payload.get("jsonrpc_method_name", ""))
    sec_field = str(payload.get("agent_card_security_field_name", ""))
    fresh_conn = bool(payload.get("auth_required_retrieved_on_fresh_connection", False))

    if not (sig_ok and sig_excl):
        return GuardEvaluationResult(
            guard_id="PR-08",
            passed=False,
            action="REJECT_UNVERIFIABLE_A2A_CARD_SIGNATURE",
            reason="SPEC 8.4.2/8.5 requires deterministic RFC 6979 ES256 signature over RFC 8785 canonicalized card with signatures excluded (#2369)",
            rule_ref="a2aproject/A2A#2369,#2364,#2362,#2352,#2382",
            checked_fields=checked,
        )
    if "/" in method_name or method_name != "SendMessage" or sec_field != "securityRequirements" or not fresh_conn:
        return GuardEvaluationResult(
            guard_id="PR-08",
            passed=False,
            action="REJECT_LEGACY_A2A_METHOD_OR_SECURITY_FIELD",
            reason="A2A v1.0 requires PascalCase JSON-RPC methods ('SendMessage' #2364), AgentCard.securityRequirements (#2362), and fresh-connection AUTH_REQUIRED retrieval (#2352)",
            rule_ref="a2aproject/A2A#2369,#2364,#2362,#2352,#2382",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-08",
        passed=True,
        action="ALLOW_VERIFIED_A2A_CARD_SIG_AND_V1_SCHEMA",
        reason="RFC 8785 ES256 Agent Card signature, PascalCase SendMessage, securityRequirements, and fresh AUTH_REQUIRED connection verified",
        rule_ref="a2aproject/A2A#2369,#2364,#2362,#2352,#2382",
        checked_fields=checked,
    )


def evaluate_ucp_python311_pillow13_schema_type_links_postal_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-09: Universal-Commerce-Protocol/ucp #990, #989, #984, #920, #892, #884 & samples #209."""
    checked = [
        "python_version_tuple",
        "pillow_major_version",
        "bundled_schema_type_links_restored",
        "pages_url_fallback_enabled",
        "postal_address_attribute_case",
    ]
    py_ver = payload.get("python_version_tuple", [0, 0])
    pillow_major = int(payload.get("pillow_major_version", 0))
    links_ok = bool(payload.get("bundled_schema_type_links_restored", False))
    pages_fb = bool(payload.get("pages_url_fallback_enabled", False))
    postal_case = str(payload.get("postal_address_attribute_case", ""))

    py_ok = isinstance(py_ver, list) and len(py_ver) >= 2 and (int(py_ver[0]), int(py_ver[1])) >= (3, 11)
    if not py_ok or pillow_major < 13:
        return GuardEvaluationResult(
            guard_id="PR-09",
            passed=False,
            action="REJECT_LEGACY_UCP_PYTHON_OR_PILLOW_RUNTIME",
            reason="UCP requires Python >= 3.11 and Pillow >= 13.0.0 (#989)",
            rule_ref="Universal-Commerce-Protocol/ucp#989,#990,#984,#920,#884,samples#209",
            checked_fields=checked,
        )
    if not (links_ok and pages_fb) or postal_case != "snake_case":
        return GuardEvaluationResult(
            guard_id="PR-09",
            passed=False,
            action="REJECT_BROKEN_UCP_SCHEMA_LINKS_OR_CAMEL_POSTAL",
            reason="Must restore bundled schema table type links (#884), enable Pages URL fallback (#984), and use snake_case PostalAddress attributes (samples #209)",
            rule_ref="Universal-Commerce-Protocol/ucp#989,#990,#984,#920,#884,samples#209",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-09",
        passed=True,
        action="ALLOW_UCP_PY311_PILLOW13_AND_SNAKE_POSTAL",
        reason="UCP Python >=3.11, Pillow >=13.0.0, bundled schema type links, Pages fallback, and snake_case PostalAddress verified",
        rule_ref="Universal-Commerce-Protocol/ucp#989,#990,#984,#920,#884,samples#209",
        checked_fields=checked,
    )


def evaluate_stripe_skills_sync_authoritative_guard_and_key_cutoff(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-10: stripe/agent-toolkit #539, #475, #427 + Stripe MCP 2026-10-31 API key cutoff."""
    checked = [
        "manual_synced_skill_dir_edit_detected",
        "target_dir_cleaned_before_skills_sync",
        "claude_plugin_test_path_prefix",
        "stripe_credential_kind",
        "evaluation_date",
    ]
    manual_edit = bool(payload.get("manual_synced_skill_dir_edit_detected", True))
    cleaned_before_sync = bool(payload.get("target_dir_cleaned_before_skills_sync", False))
    test_prefix = str(payload.get("claude_plugin_test_path_prefix", ""))
    cred_kind = str(payload.get("stripe_credential_kind", ""))
    eval_date = str(payload.get("evaluation_date", "2026-11-01"))

    if manual_edit or not cleaned_before_sync or test_prefix != "tests/":
        return GuardEvaluationResult(
            guard_id="PR-10",
            passed=False,
            action="BLOCK_MANUAL_SKILL_EDIT_OR_STALE_SYNC_DIR",
            reason="guard-skills.yml blocks manual edits to synced skill directories, scripts/sync.js must clean target dirs first (#427, #475), and plugin tests reside under tests/ (#539)",
            rule_ref="stripe/agent-toolkit#427,#475,#539+MCP-2026-10-31",
            checked_fields=checked,
        )
    if eval_date >= "2026-10-31" and cred_kind not in {"rk_restricted", "oauth_token"}:
        return GuardEvaluationResult(
            guard_id="PR-10",
            passed=False,
            action="BLOCK_DEPRECATED_STRIPE_KEY_PAST_2026_10_31",
            reason="Stripe MCP cutoff (2026-10-31 / 2026-11-30) rejects legacy sk_live/sk_test keys in favor of rk_* or OAuth tokens",
            rule_ref="stripe/agent-toolkit#427,#475,#539+MCP-2026-10-31",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-10",
        passed=True,
        action="ALLOW_AUTHORITATIVE_SKILL_SYNC_AND_RK_OAUTH",
        reason="Stripe authoritative scripts/sync.js clean sync, guard-skills.yml check, and post-2026-10-31 rk_*/OAuth credential verified",
        rule_ref="stripe/agent-toolkit#427,#475,#539+MCP-2026-10-31",
        checked_fields=checked,
    )


def evaluate_mcp_ts_cancelled_late_response_logging_cap_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-11: modelcontextprotocol/typescript-sdk #3098, #3099, #3086, #3052, #3048."""
    checked = [
        "request_was_cancelled",
        "late_response_count_for_id",
        "cancelled_id_set_size",
        "onerror_fired_for_first_late_response",
        "logging_capability_declared",
        "replayed_pre_stream_notification_without_last_event_id",
    ]
    was_cancelled = bool(payload.get("request_was_cancelled", False))
    late_count = int(payload.get("late_response_count_for_id", 1))
    set_size = int(payload.get("cancelled_id_set_size", 0))
    onerror_fired = bool(payload.get("onerror_fired_for_first_late_response", True))
    logging_cap = bool(payload.get("logging_capability_declared", False))
    replayed_without_id = bool(payload.get("replayed_pre_stream_notification_without_last_event_id", True))

    if was_cancelled and late_count == 1 and (onerror_fired or set_size > 512):
        return GuardEvaluationResult(
            guard_id="PR-11",
            passed=False,
            action="REJECT_ONERROR_ON_CANCELLED_REQUEST_LATE_RESPONSE",
            reason="First response arriving after request cancellation must be ignored without firing onerror, with cancelled ID set capped at 512 (#3098)",
            rule_ref="modelcontextprotocol/typescript-sdk#3098,#3052,#3048,#3099,#3086",
            checked_fields=checked,
        )
    if not logging_cap or replayed_without_id:
        return GuardEvaluationResult(
            guard_id="PR-11",
            passed=False,
            action="REJECT_UNDECLARED_LOGGING_OR_PRE_STREAM_REPLAY",
            reason="sendLoggingMessage requires declared logging capability and initial GET without Last-Event-ID cannot replay prior notifications (#3052)",
            rule_ref="modelcontextprotocol/typescript-sdk#3098,#3052,#3048,#3099,#3086",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-11",
        passed=True,
        action="ALLOW_CANCELLED_RESPONSE_DROP_AND_LOGGING_CAP",
        reason="Cancelled request late response dropped cleanly (cap <=512) and logging capability / Last-Event-ID rules verified",
        rule_ref="modelcontextprotocol/typescript-sdk#3098,#3052,#3048,#3099,#3086",
        checked_fields=checked,
    )


def evaluate_mcp_go_internal_error_code_token68_www_auth_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-12: modelcontextprotocol/go-sdk #1433, #1402, #1357, #1355, #1381."""
    checked = [
        "plain_handler_error_wire_code",
        "www_authenticate_token68_parsed",
        "token68_padding_misread_as_kv_param",
        "client_credentials_conformance_passed",
    ]
    wire_code = int(payload.get("plain_handler_error_wire_code", 0))
    token68_ok = bool(payload.get("www_authenticate_token68_parsed", False))
    misread_kv = bool(payload.get("token68_padding_misread_as_kv_param", True))
    cc_ok = bool(payload.get("client_credentials_conformance_passed", False))

    if wire_code != -32603:
        return GuardEvaluationResult(
            guard_id="PR-12",
            passed=False,
            action="REJECT_ZERO_ERROR_CODE_FOR_PLAIN_GO_ERROR",
            reason="Plain Go handler errors without a JSON-RPC code must be answered with -32603 (Internal error) instead of code 0 (#1402)",
            rule_ref="modelcontextprotocol/go-sdk#1402,#1357,#1433,#1355,#1381",
            checked_fields=checked,
        )
    if not token68_ok or misread_kv or not cc_ok:
        return GuardEvaluationResult(
            guard_id="PR-12",
            passed=False,
            action="REJECT_BROKEN_TOKEN68_WWW_AUTHENTICATE_PARSE",
            reason="oauthex must accept RFC 9110 §11.6.1 token68 challenges (with '=' padding) in WWW-Authenticate without misparsing as key=value (#1357, #1433)",
            rule_ref="modelcontextprotocol/go-sdk#1402,#1357,#1433,#1355,#1381",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-12",
        passed=True,
        action="ALLOW_GO_INTERNAL_ERROR_CODE_AND_TOKEN68_AUTH",
        reason="Go SDK wraps plain errors as -32603 and parses token68 WWW-Authenticate challenges cleanly",
        rule_ref="modelcontextprotocol/go-sdk#1402,#1357,#1433,#1355,#1381",
        checked_fields=checked,
    )


def evaluate_mcp_rust_oauth_refresh_granted_scopes_local_http_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-13: modelcontextprotocol/rust-sdk #1369, #1331, #1380, #1329."""
    checked = [
        "stored_grant_scopes",
        "refresh_request_scopes",
        "local_streamable_http_futures_supported",
        "failure_log_command_output_redacted",
    ]
    granted = list(payload.get("stored_grant_scopes", []))
    refresh_scopes = list(payload.get("refresh_request_scopes", []))
    local_http = bool(payload.get("local_streamable_http_futures_supported", False))
    redacted = bool(payload.get("failure_log_command_output_redacted", False))

    if not granted or refresh_scopes != granted:
        return GuardEvaluationResult(
            guard_id="PR-13",
            passed=False,
            action="BLOCK_UNGRANTED_SCOPE_INJECTION_ON_OAUTH_REFRESH",
            reason="OAuth token refresh must send only the scopes recorded in the stored grant (#1331)",
            rule_ref="modelcontextprotocol/rust-sdk#1331,#1369,#1380,#1329",
            checked_fields=checked,
        )
    if not (local_http and redacted):
        return GuardEvaluationResult(
            guard_id="PR-13",
            passed=False,
            action="REJECT_MISSING_LOCAL_HTTP_FUTURE_OR_UNREDACTED_LOGS",
            reason="Rust SDK must support local !Send streamable HTTP futures on LocalSet/WASI (#1369) and redact failure command logs (#1380)",
            rule_ref="modelcontextprotocol/rust-sdk#1331,#1369,#1380,#1329",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-13",
        passed=True,
        action="ALLOW_GRANTED_SCOPE_REFRESH_AND_LOCAL_HTTP",
        reason="Rust SDK refreshes strictly with stored grant scopes and supports local streamable HTTP futures with log redaction",
        rule_ref="modelcontextprotocol/rust-sdk#1331,#1369,#1380,#1329",
        checked_fields=checked,
    )


def evaluate_mcp_ruby_php_sep2575_envelope_sse_negotiated_version_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-14: ruby-sdk #539, #475; php-sdk #539, #437; conformance #416."""
    checked = [
        "sep2575_meta_envelope_version_supported",
        "embedding_app_authorized_request",
        "php_empty_nested_object_preserved_as_object",
        "elicitation_schema_omitted_title_allowed",
        "sse_polling_followup_protocol_version",
        "negotiated_protocol_version",
    ]
    env_ok = bool(payload.get("sep2575_meta_envelope_version_supported", False))
    app_auth = bool(payload.get("embedding_app_authorized_request", False))
    empty_obj_ok = bool(payload.get("php_empty_nested_object_preserved_as_object", False))
    title_opt_ok = bool(payload.get("elicitation_schema_omitted_title_allowed", False))
    followup_ver = str(payload.get("sse_polling_followup_protocol_version", ""))
    neg_ver = str(payload.get("negotiated_protocol_version", ""))

    if not (env_ok and app_auth and empty_obj_ok and title_opt_ok):
        return GuardEvaluationResult(
            guard_id="PR-14",
            passed=False,
            action="REJECT_SEP2575_ENVELOPE_OR_PHP_SCHEMA_MISMATCH",
            reason="Requires SEP-2575 _meta triple validation (-32022 on mismatch) + app auth check (ruby #475, #539) and PHP empty-object/optional-title conformance (php #539, #437)",
            rule_ref="mcp/ruby-sdk#539,#475;php-sdk#539,#437;conformance#416",
            checked_fields=checked,
        )
    if not neg_ver or followup_ver != neg_ver:
        return GuardEvaluationResult(
            guard_id="PR-14",
            passed=False,
            action="REJECT_HARDCODED_2025_11_25_SSE_POLLING_VERSION",
            reason="server-sse-polling raw POST/GET follow-ups must send negotiated mcp-protocol-version instead of hard-coded 2025-11-25 (conformance #416)",
            rule_ref="mcp/ruby-sdk#539,#475;php-sdk#539,#437;conformance#416",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-14",
        passed=True,
        action="ALLOW_SEP2575_ENVELOPE_AND_NEGOTIATED_SSE_VERSION",
        reason="Ruby SEP-2575 envelope + app auth, PHP structuredContent/elicitation schema, and negotiated SSE polling version verified",
        rule_ref="mcp/ruby-sdk#539,#475;php-sdk#539,#437;conformance#416",
        checked_fields=checked,
    )


def evaluate_mcp_ext_apps_single_sandbox_elicitation_postmessage_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-15: modelcontextprotocol/ext-apps #777, #733, #718, #768 & modelcontextprotocol #3447, #3446, #3439."""
    checked = [
        "postmessage_source_window_validated",
        "host_iframe_architecture",
        "ui_extension_elicitation_capability_negotiated",
        "sep2640_sep2133_link_valid",
    ]
    src_ok = bool(payload.get("postmessage_source_window_validated", False))
    iframe_arch = str(payload.get("host_iframe_architecture", ""))
    elicit_cap = bool(payload.get("ui_extension_elicitation_capability_negotiated", False))
    link_ok = bool(payload.get("sep2640_sep2133_link_valid", False))

    if not src_ok or iframe_arch != "single_sandboxed_iframe":
        return GuardEvaluationResult(
            guard_id="PR-15",
            passed=False,
            action="BLOCK_UNVALIDATED_POSTMESSAGE_OR_LEGACY_DOUBLE_IFRAME",
            reason="PostMessageTransport must validate message.source when using wildcard origin (#777) under single sandboxed iframe architecture (#718)",
            rule_ref="modelcontextprotocol/ext-apps#777,#733,#718,#768;spec#3447,#3446,#3439",
            checked_fields=checked,
        )
    if not (elicit_cap and link_ok):
        return GuardEvaluationResult(
            guard_id="PR-15",
            passed=False,
            action="REJECT_UNNEGOTIATED_UI_ELICITATION_OR_BROKEN_SEP_LINK",
            reason="App-rendered form elicitations must negotiate elicitation: {} inside io.modelcontextprotocol/ui (#733) with valid SEP-2640/2133 links (#3439)",
            rule_ref="modelcontextprotocol/ext-apps#777,#733,#718,#768;spec#3447,#3446,#3439",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-15",
        passed=True,
        action="ALLOW_VERIFIED_EXT_APPS_SANDBOX_AND_UI_ELICITATION",
        reason="PostMessage source validation, single sandboxed iframe, io.modelcontextprotocol/ui elicitation negotiation, and SEP links verified",
        rule_ref="modelcontextprotocol/ext-apps#777,#733,#718,#768;spec#3447,#3446,#3439",
        checked_fields=checked,
    )


def evaluate_tau2_v2_release_banking_airline_multilingual_guard(payload: Dict[str, Any]) -> GuardEvaluationResult:
    """PR-16: sierra-research/tau2-bench #656, #648, #643, #539."""
    checked = [
        "tau2_v2_release_date",
        "banking_1x_custom_domain_tagged",
        "airline_glm_submission_schema_valid",
        "tau_multilingual_citation_present",
    ]
    rel_date = str(payload.get("tau2_v2_release_date", ""))
    banking_ok = bool(payload.get("banking_1x_custom_domain_tagged", False))
    airline_ok = bool(payload.get("airline_glm_submission_schema_valid", False))
    multi_ok = bool(payload.get("tau_multilingual_citation_present", False))

    if rel_date != "2026-10-19" or not (banking_ok and airline_ok and multi_ok):
        return GuardEvaluationResult(
            guard_id="PR-16",
            passed=False,
            action="REJECT_UNSEALED_TAU2_V2_RELEASE_OR_DOMAIN_PROVENANCE",
            reason="tau2-bench v2.0.0 release date must match 2026-10-19 (#643) with tagged banking 1.x (#656), airline GLM-5.3-Flash (#648), and tau-Multilingual citation (#539)",
            rule_ref="sierra-research/tau2-bench#643,#656,#648,#539",
            checked_fields=checked,
        )
    return GuardEvaluationResult(
        guard_id="PR-16",
        passed=True,
        action="ALLOW_SEALED_TAU2_V2_RELEASE_AND_DOMAIN_RESULTS",
        reason="tau2-bench v2.0.0 release date (2026-10-19) and banking/airline/multilingual evaluation provenance verified",
        rule_ref="sierra-research/tau2-bench#643,#656,#648,#539",
        checked_fields=checked,
    )


STAGE254_GUARD_EVALUATORS: Dict[str, Callable[[Dict[str, Any]], GuardEvaluationResult]] = {
    "PR-01": evaluate_x402_svm_pending_store_recovery_guard,
    "PR-02": evaluate_x402_svm_go_exact_mint_token_program_guard,
    "PR-03": evaluate_x402_cryptonly_facilitator_v2_spec_express_guard,
    "PR-04": evaluate_agentkit_erc20_unconfirmed_receipt_pre_payment_hook_guard,
    "PR-05": evaluate_agentkit_glee_receipt_canaryguard_bazaar_guard,
    "PR-06": evaluate_agentkit_finance_graph_agentsvc_risk_guard,
    "PR-07": evaluate_a2a_agent_card_media_type_root_operation_v1_header_guard,
    "PR-08": evaluate_a2a_rfc8785_es256_card_sig_pascal_method_fresh_auth_guard,
    "PR-09": evaluate_ucp_python311_pillow13_schema_type_links_postal_guard,
    "PR-10": evaluate_stripe_skills_sync_authoritative_guard_and_key_cutoff,
    "PR-11": evaluate_mcp_ts_cancelled_late_response_logging_cap_guard,
    "PR-12": evaluate_mcp_go_internal_error_code_token68_www_auth_guard,
    "PR-13": evaluate_mcp_rust_oauth_refresh_granted_scopes_local_http_guard,
    "PR-14": evaluate_mcp_ruby_php_sep2575_envelope_sse_negotiated_version_guard,
    "PR-15": evaluate_mcp_ext_apps_single_sandbox_elicitation_postmessage_guard,
    "PR-16": evaluate_tau2_v2_release_banking_airline_multilingual_guard,
}


def evaluate_stage254_guards(scenario_payloads: Dict[str, Dict[str, Any]]) -> Dict[str, GuardEvaluationResult]:
    results: Dict[str, GuardEvaluationResult] = {}
    for guard_id, evaluator in STAGE254_GUARD_EVALUATORS.items():
        payload = scenario_payloads.get(guard_id, {})
        results[guard_id] = evaluator(payload)
    return results
