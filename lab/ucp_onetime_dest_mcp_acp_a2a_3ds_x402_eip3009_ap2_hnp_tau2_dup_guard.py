"""Stage 84 deterministic guardrails for UCP one-time shipping destinations & MCP schema macros,
ACP account-to-account push payments & 3DS outcomes, Coinbase x402 EIP-3009 error mapping &
Google AP2 human-not-present SessionAuthorization/SpendingRuleSet, and Sierra tau2-bench
banking duplicate transaction posting_sequence disambiguation & multi-card fraud closure.

Primary-source references:
- Universal-Commerce-Protocol/ucp#435: shipping_destination.one_time_use boolean hint & retention guard
- Universal-Commerce-Protocol/ucp#444: checkout-mcp.md & order-mcp.md schema_fields macro & protocol-errors alignment
- agentic-commerce-protocol/agentic-commerce-protocol#30: dev.acp.account_to_account BankInstructions & BankTransferConfirmation
- agentic-commerce-protocol/agentic-commerce-protocol#78: 3DS authentication_result outcomes (denied vs attempt_acknowledged)
- coinbase/x402#70: verifyEIP3009 ErrEip3009SimulationFailed & parseEIP3009TransferError revert reason mapping
- google-agentic-commerce/AP2#74: Human-not-present IntentMandate, SessionAuthorization, and SpendingRuleSet
- sierra-research/tau2-bench#380: Banking duplicate transaction disambiguation via posting_sequence
- sierra-research/tau2-bench#413: Banking multi-card confirmed fraud close_debit_card_4721 completeness (T082)
"""

from __future__ import annotations

from typing import Any


VALID_3DS_ECIS = {"01", "02", "05", "06", "07"}
VALID_A2A_CONFIRMATION_STATUSES = {"pending", "received", "expired", "failed"}
FRAUD_CLOSE_REQUIRED_CATEGORIES = {"card_present_fraud", "card_not_present_fraud"}


def validate_ucp_onetime_destination_and_mcp_binding_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #435 one_time_use shipping destination privacy and UCP #444 MCP doc/schema contract."""
    violations: list[str] = []

    req_dest = payload.get("request_shipping_destination") or {}
    resp_dest = payload.get("response_shipping_destination") or {}

    one_time_use = req_dest.get("one_time_use", False)
    if not isinstance(one_time_use, bool):
        violations.append("shipping_destination.one_time_use must be a boolean when provided")
        one_time_use = False

    if one_time_use:
        if resp_dest.get("one_time_use") is not True:
            violations.append(
                "response_shipping_destination must echo one_time_use=true so platform can verify hint preservation"
            )
        if payload.get("saved_to_address_book", False):
            violations.append(
                "one_time_use=true shipping destination must not be persisted to buyer's saved address book"
            )
        if payload.get("used_for_profile_enrichment", False):
            violations.append(
                "one_time_use=true shipping destination must not enrich recommendations, audiences, or marketing profiles (even when buyer_consent.marketing=true)"
            )

    mcp_doc = payload.get("mcp_binding_doc") or {}
    if not mcp_doc.get("uses_schema_fields_macro", False):
        violations.append(
            "checkout-mcp.md and order-mcp.md must render schemas via {{ schema_fields(...) }} macro instead of hand-maintained inline lists"
        )
    if mcp_doc.get("duplicate_per_op_meta", False):
        violations.append(
            "MCP per-operation Input Schemas must not duplicate top-level meta field (documented once in Request Metadata)"
        )
    if not mcp_doc.get("has_protocol_errors_section", False):
        violations.append(
            "order-mcp.md must include standard protocol-errors envelope documentation"
        )

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "UCP_ONETIME_DEST_AND_MCP_OK"
            if allowed
            else "UCP_ONETIME_DEST_OR_MCP_VIOLATION"
        ),
        "violations": violations,
    }


def validate_acp_a2a_push_payment_and_3ds_outcome_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #30 dev.acp.account_to_account push payment lifecycle and ACP #78 3DS authentication outcome."""
    violations: list[str] = []

    flow_type = str(payload.get("flow_type", "account_to_account"))

    if flow_type == "account_to_account":
        handler = payload.get("handler") or {}
        if handler.get("name") != "dev.acp.account_to_account":
            violations.append("A2A payment handler name must be 'dev.acp.account_to_account'")
        if handler.get("requires_delegate_payment") is not False:
            violations.append("dev.acp.account_to_account push handler requires_delegate_payment must be false")
        if handler.get("requires_pci_compliance") is not False:
            violations.append("dev.acp.account_to_account push handler requires_pci_compliance must be false")

        payment_data = payload.get("payment_data") or {}
        if not payment_data.get("handler_id"):
            violations.append("A2A payment_data must specify handler_id")
        if "token" in payment_data or "card_number" in payment_data:
            violations.append("A2A push payment_data must be handler-only without card instrument token")

        session_status = payload.get("checkout_session_status")
        order = payload.get("order") or {}
        bank_inst = order.get("bank_instructions") or {}
        confirmation = order.get("bank_transfer_confirmation") or {}
        conf_status = confirmation.get("status")

        if conf_status not in VALID_A2A_CONFIRMATION_STATUSES:
            violations.append(
                f"bank_transfer_confirmation.status '{conf_status}' must be one of {sorted(VALID_A2A_CONFIRMATION_STATUSES)}"
            )

        for req_field in ("account_address", "bank_name", "reference", "expires_at"):
            val = bank_inst.get(req_field)
            if not isinstance(val, str) or not val.strip():
                violations.append(f"order.bank_instructions.{req_field} must be a non-empty string")

        if conf_status == "pending":
            if session_status != "complete_in_progress":
                violations.append(
                    "checkout_session_status must be 'complete_in_progress' while bank_transfer_confirmation.status is 'pending'"
                )
            if payload.get("allow_fulfillment_release", False):
                violations.append(
                    "fulfillment must not be released while A2A bank_transfer_confirmation.status is 'pending'"
                )
        elif conf_status == "received":
            received_at = confirmation.get("received_at")
            expires_at = bank_inst.get("expires_at")
            if not isinstance(received_at, str) or not received_at.strip():
                violations.append(
                    "bank_transfer_confirmation.received_at is required when status is 'received'"
                )
            elif isinstance(expires_at, str) and expires_at.strip() and received_at > expires_at:
                violations.append(
                    "bank_transfer_confirmation.received_at exceeds bank_instructions.expires_at window"
                )
        elif conf_status in {"expired", "failed"}:
            if payload.get("allow_fulfillment_release", False) or order.get("status") == "fulfilled":
                violations.append(
                    f"A2A order must not be fulfilled when bank_transfer_confirmation.status is '{conf_status}'"
                )

    elif flow_type == "three_ds":
        requires_3ds = bool(payload.get("requires_3ds", True))
        auth_result = payload.get("authentication_result")
        allow_settlement = bool(payload.get("allow_settlement", False))

        if requires_3ds and not isinstance(auth_result, dict):
            violations.append("Checkout session with requires_3ds must include authentication_result")
        elif isinstance(auth_result, dict):
            outcome = auth_result.get("outcome")
            details = auth_result.get("outcome_details") or {}
            if not details.get("transaction_id") or not details.get("version"):
                violations.append(
                    "authentication_result.outcome_details must include transaction_id and version"
                )
            if outcome == "denied":
                if allow_settlement:
                    violations.append(
                        "authentication_result with outcome='denied' must not proceed to payment settlement"
                    )
            elif outcome == "attempt_acknowledged":
                cryptogram = details.get("three_ds_cryptogram")
                eci = details.get("electronic_commerce_indicator")
                if not isinstance(cryptogram, str) or not cryptogram.strip():
                    violations.append(
                        "frictionless outcome='attempt_acknowledged' requires non-empty three_ds_cryptogram"
                    )
                if eci not in VALID_3DS_ECIS:
                    violations.append(
                        f"frictionless outcome='attempt_acknowledged' requires valid electronic_commerce_indicator in {sorted(VALID_3DS_ECIS)}"
                    )
            else:
                violations.append(f"Unsupported 3DS authentication_result.outcome '{outcome}'")
    else:
        violations.append(f"Unsupported ACP flow_type '{flow_type}'")

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "ACP_A2A_AND_3DS_OK" if allowed else "ACP_A2A_OR_3DS_VIOLATION"
        ),
        "violations": violations,
    }


def _map_eip3009_revert_message(msg: str) -> str:
    lower = msg.lower()
    if "authorization is expired" in lower or "authorizationexpired" in lower or "valid before" in lower:
        return "ErrValidBeforeExpired"
    if "authorization is not yet valid" in lower or "authorizationnotyetvalid" in lower:
        return "ErrValidAfterInFuture"
    if (
        "authorization is used" in lower
        or "authorizationalreadyused" in lower
        or "authorizationusedorcanceled" in lower
    ):
        return "ErrNonceAlreadyUsed"
    if (
        "transfer amount exceeds balance" in lower
        or "insufficient balance" in lower
        or "erc20insufficientbalance" in lower
    ):
        return "ErrInsufficientBalance"
    if (
        "invalid signature" in lower
        or "signermismatch" in lower
        or "invalidsignaturev" in lower
        or "invalidsignatures" in lower
    ):
        return "ErrInvalidSignature"
    return "ErrFailedToExecuteTransfer"


def validate_x402_eip3009_error_and_ap2_hnp_session_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 #70 EIP-3009 simulation/settlement error mapping and AP2 #74 HNP SessionAuthorization/SpendingRuleSet."""
    violations: list[str] = []

    eip3009 = payload.get("x402_eip3009") or {}
    phase = eip3009.get("phase", "verify")
    reported_error_code = eip3009.get("reported_error_code")

    if phase == "verify_simulation_rpc_error":
        if reported_error_code != "ErrEip3009SimulationFailed":
            violations.append(
                f"verifyEIP3009 simulation RPC failure must map to 'ErrEip3009SimulationFailed', got '{reported_error_code}'"
            )
    elif phase == "settle_revert":
        raw_revert = str(eip3009.get("revert_message", ""))
        expected_code = _map_eip3009_revert_message(raw_revert)
        if reported_error_code != expected_code:
            violations.append(
                f"settleEIP3009 revert '{raw_revert}' must map to '{expected_code}', got '{reported_error_code}'"
            )

    ap2 = payload.get("ap2_hnp_mandate") or {}
    user_cart_confirmation_required = ap2.get("user_cart_confirmation_required", False)

    if not user_cart_confirmation_required:
        agent_did = str(ap2.get("agent_did", ""))
        if not agent_did.startswith("did:") or len(agent_did.split(":")) < 3:
            violations.append(
                "Human-not-present IntentMandate requires valid 3-segment agent_did starting with 'did:'"
            )

        session_auth = ap2.get("session_authorization") or {}
        if session_auth.get("status") != "active":
            violations.append("SessionAuthorization.status must be 'active' for HNP execution")
        now_iso = str(ap2.get("now_iso", ""))
        expires_at = str(session_auth.get("expires_at", ""))
        if not expires_at or (now_iso and expires_at <= now_iso):
            violations.append("SessionAuthorization is expired or missing expires_at")
        if not session_auth.get("session_public_key"):
            violations.append("SessionAuthorization requires cryptographic session_public_key")

        rule_set = ap2.get("spending_rule_set") or {}
        eval_mode = rule_set.get("evaluation_mode", "all")
        if eval_mode not in {"all", "any"}:
            violations.append(f"SpendingRuleSet.evaluation_mode '{eval_mode}' must be 'all' or 'any'")
        else:
            rules = sorted(
                rule_set.get("rules") or [],
                key=lambda r: int(r.get("priority", 100)),
            )
            tx_ctx = ap2.get("transaction_context") or {}
            results: list[bool] = []
            for r in rules:
                if not r.get("enabled", True):
                    continue
                rtype = r.get("rule_type")
                if rtype == "frequency_constraint":
                    max_tx = int(r.get("max_transactions", 0))
                    count_key = (
                        "merchant_transaction_count_in_window"
                        if r.get("merchant_specific", False)
                        else "total_transaction_count_in_window"
                    )
                    current_count = int(tx_ctx.get(count_key, 0))
                    passed = max_tx >= 1 and current_count < max_tx
                    results.append(passed)
                elif rtype == "category_constraint":
                    cats = set(r.get("categories") or [])
                    item_cats = list(tx_ctx.get("item_categories") or [])
                    ctype = r.get("constraint_type", "allow")
                    if not item_cats:
                        passed = ctype == "deny"
                    else:
                        has_match = any(c in cats for c in item_cats)
                        passed = has_match if ctype == "allow" else not has_match
                    results.append(passed)
                elif rtype == "amount_constraint":
                    max_amt = float(r.get("max_amount", 0.0))
                    tx_amt = float(tx_ctx.get("amount", 0.0))
                    results.append(tx_amt <= max_amt)

            if results:
                overall = all(results) if eval_mode == "all" else any(results)
                if not overall:
                    violations.append(
                        f"SpendingRuleSet evaluation failed under evaluation_mode='{eval_mode}'"
                    )

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "X402_EIP3009_AND_AP2_HNP_OK"
            if allowed
            else "X402_EIP3009_OR_AP2_HNP_VIOLATION"
        ),
        "violations": violations,
    }


def validate_tau2_duplicate_posting_seq_and_multicard_fraud_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #380 duplicate transaction posting_sequence disambiguation and #413 multi-card fraud closure."""
    violations: list[str] = []

    dup_group = payload.get("duplicate_transactions") or []
    disputed_tx_id = payload.get("disputed_transaction_id")

    if len(dup_group) >= 2:
        seqs: list[int] = []
        earliest_tx_id: str | None = None
        min_seq: int | None = None

        for tx in dup_group:
            seq = tx.get("posting_sequence")
            if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
                violations.append(
                    f"Duplicate transaction '{tx.get('transaction_id')}' is missing positive integer posting_sequence"
                )
            else:
                seqs.append(seq)
                if min_seq is None or seq < min_seq:
                    min_seq = seq
                    earliest_tx_id = tx.get("transaction_id")

        if len(seqs) == len(dup_group) and len(set(seqs)) != len(seqs):
            violations.append("Duplicate transaction group contains colliding posting_sequence values")

        if earliest_tx_id is not None and disputed_tx_id != earliest_tx_id:
            violations.append(
                f"Disputed transaction '{disputed_tx_id}' is not the earliest duplicate charge ('{earliest_tx_id}' with posting_sequence={min_seq})"
            )

    disputes = payload.get("filed_disputes") or []
    closed_cards = {
        c.get("card_id"): c.get("reason")
        for c in (payload.get("closed_debit_cards") or [])
        if isinstance(c, dict) and c.get("card_id")
    }
    card_states = payload.get("final_card_statuses") or {}

    for d in disputes:
        category = d.get("category")
        card_action = d.get("card_action")
        card_id = d.get("card_id")
        if category in FRAUD_CLOSE_REQUIRED_CATEGORIES or card_action == "close_and_reissue":
            if card_id not in closed_cards:
                violations.append(
                    f"Fraud-affected card '{card_id}' (category='{category}', card_action='{card_action}') was not closed via close_debit_card_4721"
                )
            elif closed_cards.get(card_id) != "fraud_suspected":
                violations.append(
                    f"close_debit_card_4721 on '{card_id}' must use reason='fraud_suspected', got '{closed_cards.get(card_id)}'"
                )
            if str(card_states.get(card_id, "")).upper() == "ACTIVE":
                violations.append(
                    f"Fraud-confirmed card '{card_id}' must not remain ACTIVE after dispute filing"
                )

    allowed = len(violations) == 0
    return {
        "allowed": allowed,
        "decision_code": (
            "TAU2_DUP_SEQ_AND_MULTICARD_FRAUD_OK"
            if allowed
            else "TAU2_DUP_SEQ_OR_MULTICARD_FRAUD_VIOLATION"
        ),
        "violations": violations,
    }
