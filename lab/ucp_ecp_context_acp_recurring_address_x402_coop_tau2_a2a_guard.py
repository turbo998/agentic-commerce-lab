"""Stage 90 deterministic guardrails across UCP, ACP, Coinbase x402, and Sierra tau2-bench.

Covers:
1. UCP PRs `#80`, `#62`, `#58`, `#86`:
   - `#80`: Two-level ECP (`embedded` transport) discovery & per-checkout `ucp.services["dev.ucp.shopping"][].config.delegations` enforcement
   - `#62`: Output-only `currency` (forbidden in client request input) and `context` (`country`, `region`, `postal_code`) allowed on `create`/`update` but forbidden on `complete`
   - `#58`: Removal of `full_name` across UCP objects in favor of `first_name` / `last_name`
   - `#86`: Capability maturity levels (`Working Draft` -> no version, `Candidate` -> `"Candidate"`, `Stable` -> `YYYY-MM-DD`)
2. ACP PRs `#73`, `#10`, `#45`:
   - `#73`: Recurring payment `Allowance` (`reason in {"one_time", "recurring", "subscription"}`, required `billing_cycle` and `amount_per_cycle` for recurring/subscription, and cumulative `max_amount` exposure cap)
   - `#10`: Split `BillingAddress` (`country`, `postal_code` required; no fabricated placeholder street required) vs. `FulfillmentAddress` (`name`, `line_one`, `city`, `state`, `country`, `postal_code` required)
   - `#45`: Lodging vertical 4-layer rate hydration (`quote_token`, `nightly_breakdown`, `cancellation_deadline`, `payment_model` required at checkout; static catalog base price forbidden without hydration)
3. Coinbase x402 PR `#44` (`spec v1.2`):
   - Removal of legacy `finalizeWithdraw` / `finalizeWithdrawWithSignature`
   - `cooperativeWithdraw` strictly `msg.sender`-gated vs. `cooperativeWithdrawWithSignature` requiring valid cryptographic signature
4. Sierra tau2-bench PRs `#83`, `#93`:
   - `#83`: A2A Agentified evaluation Green Agent vs. White Agent isolation (White Agent must not access Green Agent scoring/gold DB or know benchmark internals)
   - `#93`: Gemini 3 Pro multi-turn function-calling `thought_signature` preservation across assistant tool-call turns
"""

from __future__ import annotations

import re
from typing import Any


DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VALID_INTERVALS = {"day", "week", "month", "year"}
VALID_LODGING_PAYMENT_MODELS = {"prepaid", "guarantee", "pay_at_property"}
PLACEHOLDER_TOKENS = {"n/a", "na", "none", "null", "placeholder", "tbd", "unknown", "00000"}


def validate_ucp_ecp_delegations_and_context_currency_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #80 per-checkout ECP delegations, #62 context/output-only currency, #58 no full_name, and #86 maturity levels."""
    violations: list[str] = []

    ecp = payload.get("ecp_session", {})
    service_supports_ecp = bool(ecp.get("service_level_embedded_supported", False))
    checkout_services = ecp.get("checkout_ucp_services", {}).get("dev.ucp.shopping", [])
    requested_delegations = ecp.get("requested_delegations", [])

    confirmed_delegations: set[str] = set()
    checkout_confirms_ecp = False
    for svc in checkout_services:
        if svc.get("transport") == "embedded":
            checkout_confirms_ecp = True
            cfg = svc.get("config", {})
            for d in cfg.get("delegations", []):
                if isinstance(d, str):
                    confirmed_delegations.add(d)

    if ecp.get("use_embedded_checkout", False):
        if not service_supports_ecp or not checkout_confirms_ecp:
            violations.append("UCP_ECP_SESSION_TRANSPORT_NOT_CONFIRMED")
        for req_del in requested_delegations:
            if req_del not in confirmed_delegations:
                violations.append(f"UCP_ECP_UNCONFIRMED_DELEGATION:{req_del}")

    req = payload.get("checkout_request", {})
    op = req.get("operation", "create")
    body = req.get("body", {})
    if "currency" in body:
        violations.append("UCP_CLIENT_INPUT_CURRENCY_FORBIDDEN")

    if "context" in body:
        if op == "complete":
            violations.append("UCP_CONTEXT_FORBIDDEN_ON_COMPLETE")
        else:
            ctx = body.get("context", {})
            if not isinstance(ctx, dict) or not any(
                k in ctx for k in ("country", "region", "postal_code")
            ):
                violations.append("UCP_CONTEXT_INVALID_SIGNALS")

    for actor_key in ("buyer", "recipient", "billing_contact"):
        actor = body.get(actor_key, {})
        if isinstance(actor, dict) and "full_name" in actor:
            violations.append(f"UCP_LEGACY_FULL_NAME_FORBIDDEN:{actor_key}")

    maturity = payload.get("capability_maturity", {})
    stage = maturity.get("level")
    version = maturity.get("version")
    if stage == "Working Draft":
        if version not in (None, ""):
            violations.append("UCP_MATURITY_WORKING_DRAFT_MUST_OMIT_VERSION")
    elif stage == "Candidate":
        if version != "Candidate":
            violations.append(f"UCP_MATURITY_CANDIDATE_VERSION_MISMATCH:{version}")
    elif stage == "Stable":
        if not isinstance(version, str) or not DATE_VERSION_RE.match(version):
            violations.append(f"UCP_MATURITY_STABLE_DATE_VERSION_REQUIRED:{version}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_recurring_allowance_address_and_lodging_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #73 recurring Allowance, #10 split BillingAddress/FulfillmentAddress, and #45 Lodging rate hydration."""
    violations: list[str] = []

    allowance = payload.get("allowance", {})
    reason = allowance.get("reason", "one_time")
    max_amount = allowance.get("max_amount", 0)
    if reason not in {"one_time", "recurring", "subscription"}:
        violations.append(f"ACP_ALLOWANCE_INVALID_REASON:{reason}")
    elif reason in {"recurring", "subscription"}:
        cycle = allowance.get("billing_cycle")
        amt_per_cycle = allowance.get("amount_per_cycle")
        if not isinstance(cycle, dict):
            violations.append("ACP_RECURRING_BILLING_CYCLE_REQUIRED")
        else:
            interval = cycle.get("interval")
            interval_count = cycle.get("interval_count", 0)
            if interval not in VALID_INTERVALS or not isinstance(interval_count, int) or interval_count <= 0:
                violations.append("ACP_RECURRING_BILLING_CYCLE_INVALID")
        if not isinstance(amt_per_cycle, int) or amt_per_cycle <= 0:
            violations.append("ACP_RECURRING_AMOUNT_PER_CYCLE_REQUIRED")
        else:
            if isinstance(max_amount, int) and max_amount > 0 and amt_per_cycle > max_amount:
                violations.append("ACP_RECURRING_CYCLE_EXCEEDS_MAX_AMOUNT")
            max_cycles = allowance.get("max_cycles")
            trial_amount = allowance.get("trial_amount", 0) or 0
            if isinstance(max_cycles, int) and max_cycles > 0 and isinstance(max_amount, int) and max_amount > 0:
                total_scheduled = amt_per_cycle * max_cycles + trial_amount
                if total_scheduled > max_amount:
                    violations.append(
                        f"ACP_RECURRING_CUMULATIVE_EXPOSURE_EXCEEDS_MAX:{total_scheduled}>{max_amount}"
                    )

    addresses = payload.get("addresses", {})
    billing = addresses.get("billing_address", {})
    fulfillment = addresses.get("fulfillment_address", {})

    for req_field in ("country", "postal_code"):
        val = str(billing.get(req_field, "")).strip()
        if not val or val.lower() in PLACEHOLDER_TOKENS:
            violations.append(f"ACP_BILLING_ADDRESS_MISSING_OR_PLACEHOLDER:{req_field}")
    for opt_field in ("name", "line_one", "city", "state"):
        if opt_field in billing:
            val = str(billing.get(opt_field, "")).strip().lower()
            if val in PLACEHOLDER_TOKENS:
                violations.append(f"ACP_BILLING_ADDRESS_FABRICATED_PLACEHOLDER:{opt_field}")

    for req_field in ("name", "line_one", "city", "state", "country", "postal_code"):
        val = str(fulfillment.get(req_field, "")).strip()
        if not val or val.lower() in PLACEHOLDER_TOKENS:
            violations.append(f"ACP_FULFILLMENT_ADDRESS_INCOMPLETE:{req_field}")

    lodging = payload.get("lodging_checkout")
    if isinstance(lodging, dict):
        if lodging.get("used_static_feed_base_price_directly", False):
            violations.append("ACP_LODGING_NON_BINDING_BASE_PRICE_USED_AT_CHECKOUT")
        if not lodging.get("quote_token"):
            violations.append("ACP_LODGING_HYDRATED_QUOTE_TOKEN_REQUIRED")
        if not lodging.get("cancellation_deadline"):
            violations.append("ACP_LODGING_CANCELLATION_DEADLINE_REQUIRED")
        payment_model = lodging.get("payment_model")
        if payment_model not in VALID_LODGING_PAYMENT_MODELS:
            violations.append(f"ACP_LODGING_INVALID_PAYMENT_MODEL:{payment_model}")
        nightly = lodging.get("nightly_breakdown", [])
        quoted_room_total = lodging.get("quoted_room_subtotal", 0)
        if not isinstance(nightly, list) or len(nightly) == 0:
            violations.append("ACP_LODGING_NIGHTLY_BREAKDOWN_REQUIRED")
        elif sum(int(n.get("rate", 0)) for n in nightly) != quoted_room_total:
            violations.append("ACP_LODGING_NIGHTLY_BREAKDOWN_SUM_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_x402_v12_cooperative_withdraw_and_claim_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 PR #44 (spec v1.2) withdrawal and claim method gating."""
    violations: list[str] = []

    fn_name = payload.get("function_name", "")
    msg_sender = str(payload.get("msg_sender", "")).lower()
    authorized_withdrawer = str(payload.get("authorized_withdrawer", "")).lower()
    has_valid_signature = bool(payload.get("has_valid_signature", False))
    signer = str(payload.get("recovered_signer", "")).lower()

    if fn_name in {"finalizeWithdraw", "finalizeWithdrawWithSignature"}:
        violations.append(f"X402_V12_REMOVED_WITHDRAW_FUNCTION_FORBIDDEN:{fn_name}")
    elif fn_name == "cooperativeWithdraw":
        if not msg_sender or msg_sender != authorized_withdrawer:
            violations.append("X402_V12_COOPERATIVE_WITHDRAW_MSG_SENDER_MISMATCH")
    elif fn_name == "cooperativeWithdrawWithSignature":
        if not has_valid_signature or not signer or signer != authorized_withdrawer:
            violations.append("X402_V12_COOPERATIVE_WITHDRAW_SIGNATURE_INVALID")
    elif fn_name == "claim":
        beneficiary = str(payload.get("beneficiary", authorized_withdrawer)).lower()
        if not msg_sender or msg_sender != beneficiary:
            violations.append("X402_V12_CLAIM_MSG_SENDER_MISMATCH")
    elif fn_name == "claimWithSignature":
        beneficiary = str(payload.get("beneficiary", authorized_withdrawer)).lower()
        if not has_valid_signature or not signer or signer != beneficiary:
            violations.append("X402_V12_CLAIM_WITH_SIGNATURE_INVALID")
    else:
        violations.append(f"X402_V12_UNKNOWN_ESCROW_FUNCTION:{fn_name}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_a2a_green_white_isolation_and_thought_signature_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #83 A2A Green/White agent isolation and #93 Gemini 3 Pro thought_signature."""
    violations: list[str] = []

    a2a = payload.get("a2a_eval", {})
    if a2a.get("white_agent_accessed_gold_db", False):
        violations.append("TAU2_A2A_WHITE_AGENT_GOLD_DB_LEAK")
    if a2a.get("white_agent_received_benchmark_rubric", False):
        violations.append("TAU2_A2A_WHITE_AGENT_RUBRIC_LEAK")
    if not a2a.get("green_agent_manages_environment", True):
        violations.append("TAU2_A2A_GREEN_AGENT_ENV_ORCHESTRATION_REQUIRED")

    gemini = payload.get("gemini3_turns", {})
    model = str(gemini.get("model", ""))
    turns = gemini.get("assistant_tool_turns", [])
    if "gemini-3" in model:
        for idx, turn in enumerate(turns):
            if turn.get("has_tool_call", False):
                sig = turn.get("thought_signature")
                if not isinstance(sig, str) or not sig.strip():
                    violations.append(f"TAU2_GEMINI3_THOUGHT_SIGNATURE_MISSING:turn_{idx}")
                elif not turn.get("thought_signature_echoed_in_history", True):
                    violations.append(f"TAU2_GEMINI3_THOUGHT_SIGNATURE_DROPPED_IN_HISTORY:turn_{idx}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
