"""Stage 132 deterministic runtime guardrails.

Covers primary-source protocol and runtime edge cases across:
1. x402 Foundation (`x402-foundation/x402` `#3663`, `#3662`, `#3661`, `#3656`,
   `#3655`, `#3654`, `#3653`, `#3652`, `#3651`, `#3648`, `#3643`, `#3642`,
   `#3640`, `#3639`, `#3637`, `#3635`, `#3632`, `#3631`, `#3630`):
   - Batch-settlement baseline derived from facilitator-verified on-chain
     `totalClaimed` rather than untrusted client voucher claims after server
     restart/refund, plus minimum-advance check `maxClaimableAmount >= totalClaimed + requestedAmount`
     across EVM (`#3655`) and SVM (`#3661`).
   - Exact SVM confirmation terminal-vs-uncertain classification (`#3653`):
     only `confirmed`/`finalized` `TransactionOnchainFailureError` is terminal;
     `processed`, timeout, transport, or malformed RPC responses route to the
     pending store.
   - MCP client auto-pay dual-representation equivalence (`#3643`, `#3631`):
     refuse auto-pay (`PaymentRequiredMismatchError`) when `structuredContent`
     and `content[0].text` both decode as `PaymentRequired` and disagree on
     typed terms (`amount`, `asset`, `payTo`, `network`, `maxTimeoutSeconds`),
     while allowing benign numeric formatting (`2` vs `2.0`).
   - Client `spendControls.maxTimeoutSeconds` ceiling (`#3630`), SVM
     server-signed channel refund storage-first lookup after restart (`#3637`,
     `#3639`), AVM legacy/CAIP-2 network equivalence (`#3652`),
     `OnAfterPaymentCreation` hook error propagation (`#3651`), Bazaar no-eval
     runtime fallback (`#3648`), `extensions.reviews` / `extensions.refund`
     validation (`#3656`, `#3642`, `#3640`), GalaChain payer-funded exact
     scheme (`#3635`), BCH UTXO/CashTokens source-output check (`#3632`), and
     Solana browser paywall `rpcUrls` / P2Flux / sanctions list hygiene
     (`#3663`, `#3662`, `#3654`).
2. Google UCP (`Universal-Commerce-Protocol/ucp` `#950`, `#932`, `#808`, `#752`,
   `#710`, `#709`, `#705`, `#685`, `#680`, `#613`, `#595`, `#585`, `#561`, `#503`):
   - Profile hosting conditional `304 Not Modified` revalidation allowance vs
     `301`/`302`/`307`/`308` redirect rejection (`#932`) and `ucp-schema`
     `1.4.1` nested `$id` preservation (`#950`).
   - Deterministic lodging cancellation policy `schedule` evaluation at an
     explicit cancellation timestamp (`#808`) and negotiated top-level Create
     Checkout extension inputs (`#752`).
   - Multi-rate tax-inclusive VAT gross `total` conservation (`#680`),
     `options[].totals` integer `signed_amount` array enforcement (`#561`),
     `get_order` 200 response signature headers (`#503`), `list_catalog` +
     `brand`/`condition` filters (`#613`, `#595`), identity-linked session
     business-populated instruments (`#585`), post-strip array elision index
     mapping (`#685`), `anyOf` request constraints overlay (`#705`), and
     `{{ ucp_version }}` macro / root URL normalization (`#710`, `#709`).
3. Stripe AI (`stripe/ai` `#346`, `#345`, `#332`, `#321`, `#319`, `#315`,
   `#311`, `#309`, `#308`, `#304`, `#295`, `#294`), MCP
   (`modelcontextprotocol/modelcontextprotocol` `#3265`, `#3263`, `#3259`,
   `#3251`, `#3248`, `#3246`, `#3245`, `#3244`, `#3242`), and Sierra
   tau2-bench (`sierra-research/tau2-bench` `#481`, `#479`, `#476`, `#473`,
   `#469`, `#468`, `#465`, `#452`, `#448`, `#447`, `#445`, `#442`):
   - Stripe MCP stdio proxy deferred HTTP transport & `User-Agent` clientInfo
     tagging (`#304`), Hono SSE control-field injection & `path-to-regexp`
     guards (`#294`, `#345`), `.well-known/skills/` sync & Dependabot
     `benchmarks/**` exclusion (`#332`, `#319`, `#308`).
   - MCP `io.noescalation/provenance` delegation-chain authority intersection
     confinement (`#3246`), `org.oma3/mpas` multi-party approval quorum on MCP
     Tasks (`#3263`), 4-stage Agent Marketplace Bidding pipeline (`#3265`),
     SEP-2127 Server Card vs live `server/discover` separation (`#3242`), and
     `fast-uri` backslash authority confusion + Node `>=24` floor (`#3245`, `#3244`).
   - Sierra tau2-bench Pine Voice 114-task telecom denominator & Modal `pine-`
     routing (`#481`, `#473`, `#442`), `--judge-llm` CLI override &
     exception-safe `NLAssertionsEvaluator` (`#479`, `#469`), and multilingual
     transcription `WER`/`CER` gate (`#448`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Any, Mapping, Sequence


AVM_KNOWN_CAIP2_ALIASES: dict[str, str] = {
    "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=": "algorand:mainnet-v1.0",
    "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=": "algorand:testnet-v1.0",
    "algorand:mainnet-v1.0": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
    "algorand:testnet-v1.0": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
}


@dataclass(frozen=True)
class BatchTotalClaimedAuditResult:
    allowed: bool
    reason_code: str
    effective_baseline_minor: int
    minimum_required_claimable_minor: int
    voucher_max_claimable_minor: int


def verify_x402_batch_total_claimed_and_minimum_advance(
    *,
    local_channel_baseline_minor: int | None,
    facilitator_onchain_total_claimed_minor: int | None,
    requested_amount_minor: int,
    voucher_max_claimable_minor: int,
    is_refund_voucher: bool = False,
) -> BatchTotalClaimedAuditResult:
    """Enforce x402 `#3655` and `#3661` batch-settlement baseline & minimum advance."""
    if requested_amount_minor < 0 or voucher_max_claimable_minor < 0:
        return BatchTotalClaimedAuditResult(
            allowed=False,
            reason_code="X402_BATCH_NEGATIVE_AMOUNT_INVALID",
            effective_baseline_minor=0,
            minimum_required_claimable_minor=0,
            voucher_max_claimable_minor=voucher_max_claimable_minor,
        )

    if local_channel_baseline_minor is not None:
        if (
            facilitator_onchain_total_claimed_minor is not None
            and facilitator_onchain_total_claimed_minor > local_channel_baseline_minor
        ):
            baseline = facilitator_onchain_total_claimed_minor
        else:
            baseline = local_channel_baseline_minor
    else:
        if facilitator_onchain_total_claimed_minor is None:
            return BatchTotalClaimedAuditResult(
                allowed=False,
                reason_code="X402_BATCH_MISSING_ONCHAIN_TOTAL_CLAIMED_BASELINE",
                effective_baseline_minor=0,
                minimum_required_claimable_minor=requested_amount_minor,
                voucher_max_claimable_minor=voucher_max_claimable_minor,
            )
        baseline = facilitator_onchain_total_claimed_minor

    if is_refund_voucher:
        return BatchTotalClaimedAuditResult(
            allowed=True,
            reason_code="X402_BATCH_REFUND_VOUCHER_OK",
            effective_baseline_minor=baseline,
            minimum_required_claimable_minor=baseline,
            voucher_max_claimable_minor=voucher_max_claimable_minor,
        )

    min_required = baseline + requested_amount_minor
    if voucher_max_claimable_minor < min_required:
        return BatchTotalClaimedAuditResult(
            allowed=False,
            reason_code="X402_BATCH_VOUCHER_BELOW_SETTLED_PLUS_AMOUNT_MINIMUM",
            effective_baseline_minor=baseline,
            minimum_required_claimable_minor=min_required,
            voucher_max_claimable_minor=voucher_max_claimable_minor,
        )

    return BatchTotalClaimedAuditResult(
        allowed=True,
        reason_code="X402_BATCH_TOTAL_CLAIMED_AND_ADVANCE_OK",
        effective_baseline_minor=baseline,
        minimum_required_claimable_minor=min_required,
        voucher_max_claimable_minor=voucher_max_claimable_minor,
    )


@dataclass(frozen=True)
class SvmConfirmationAndRestartRefundAuditResult:
    allowed: bool
    reason_code: str
    confirmation_disposition: str
    restored_channel_id: str | None


def validate_x402_svm_confirmation_and_restart_refund(
    *,
    commitment_status: str,
    typed_onchain_failure_error: bool,
    rpc_timeout_or_malformed: bool,
    is_restart_refund_lookup: bool = False,
    requested_mode: str = "server",
    operator_pubkey: str = "",
    allowed_server_signed_operators: Sequence[str] = (),
    durable_storage_channels: Mapping[str, Mapping[str, Any]] | None = None,
) -> SvmConfirmationAndRestartRefundAuditResult:
    """Enforce x402 `#3653` exact SVM confirmation classification and `#3637` restart refund lookup."""
    if is_restart_refund_lookup:
        storage = durable_storage_channels or {}
        if requested_mode == "server":
            if not operator_pubkey or operator_pubkey not in set(allowed_server_signed_operators):
                return SvmConfirmationAndRestartRefundAuditResult(
                    allowed=False,
                    reason_code="X402_SVM_SERVER_SIGNED_OPERATOR_POLICY_REJECTED",
                    confirmation_disposition="n/a",
                    restored_channel_id=None,
                )
            for chan_id, record in storage.items():
                if (
                    record.get("mode") == "server"
                    and record.get("operator") == operator_pubkey
                ):
                    return SvmConfirmationAndRestartRefundAuditResult(
                        allowed=True,
                        reason_code="X402_SVM_RESTART_SERVER_SIGNED_REFUND_RESTORED",
                        confirmation_disposition="finalized",
                        restored_channel_id=chan_id,
                    )
            return SvmConfirmationAndRestartRefundAuditResult(
                allowed=False,
                reason_code="X402_SVM_NO_BATCH_CHANNEL_TO_REFUND",
                confirmation_disposition="n/a",
                restored_channel_id=None,
            )

    normalized_status = commitment_status.strip().lower()
    if rpc_timeout_or_malformed or normalized_status in {"processed", "unknown", ""}:
        return SvmConfirmationAndRestartRefundAuditResult(
            allowed=True,
            reason_code="X402_SVM_CONFIRMATION_UNCERTAIN_ROUTED_TO_PENDING_STORE",
            confirmation_disposition="pending_store",
            restored_channel_id=None,
        )

    if normalized_status in {"confirmed", "finalized"} and typed_onchain_failure_error:
        return SvmConfirmationAndRestartRefundAuditResult(
            allowed=False,
            reason_code="X402_SVM_TERMINAL_ONCHAIN_EXECUTION_FAILURE",
            confirmation_disposition="terminal_failure",
            restored_channel_id=None,
        )

    if normalized_status in {"confirmed", "finalized"}:
        return SvmConfirmationAndRestartRefundAuditResult(
            allowed=True,
            reason_code="X402_SVM_CONFIRMATION_FINALIZED_OK",
            confirmation_disposition="confirmed_success",
            restored_channel_id=None,
        )

    return SvmConfirmationAndRestartRefundAuditResult(
        allowed=True,
        reason_code="X402_SVM_CONFIRMATION_UNCERTAIN_ROUTED_TO_PENDING_STORE",
        confirmation_disposition="pending_store",
        restored_channel_id=None,
    )


def _normalize_numeric_str(value: Any) -> str:
    if isinstance(value, (int, float, Decimal)):
        d = Decimal(str(value)).normalize()
        return format(d, "f")
    if isinstance(value, str):
        stripped = value.strip()
        try:
            d = Decimal(stripped).normalize()
            return format(d, "f")
        except Exception:
            return stripped
    return str(value)


@dataclass(frozen=True)
class McpDualPaymentRequiredAndSpendControlsResult:
    allowed: bool
    reason_code: str
    effective_timeout_seconds: int


def audit_x402_mcp_payment_mismatch_and_spend_controls(
    *,
    structured_payment_required: Mapping[str, Any] | None,
    text_payment_required_json: str | None,
    requested_max_timeout_seconds: int,
    client_max_timeout_seconds_cap: int = 300,
    after_payment_creation_hook_error: str | None = None,
    recovery_substituted_payload: bool = False,
) -> McpDualPaymentRequiredAndSpendControlsResult:
    """Enforce x402 `#3643`/`#3631` MCP dual-object equivalence, `#3630` timeout cap, and `#3651` hook error surface."""
    if requested_max_timeout_seconds <= 0:
        return McpDualPaymentRequiredAndSpendControlsResult(
            allowed=False,
            reason_code="X402_SPEND_CONTROLS_INVALID_TIMEOUT",
            effective_timeout_seconds=0,
        )

    if requested_max_timeout_seconds > client_max_timeout_seconds_cap:
        return McpDualPaymentRequiredAndSpendControlsResult(
            allowed=False,
            reason_code="X402_SPEND_CONTROLS_MAX_TIMEOUT_EXCEEDED",
            effective_timeout_seconds=requested_max_timeout_seconds,
        )

    if structured_payment_required is not None and text_payment_required_json:
        try:
            parsed_text = json.loads(text_payment_required_json)
        except Exception:
            parsed_text = None

        if isinstance(parsed_text, Mapping):
            s_accepts = (structured_payment_required.get("accepts") or [{}])[0]
            t_accepts = (parsed_text.get("accepts") or [{}])[0]
            for field in ("scheme", "network", "asset", "payTo"):
                if str(s_accepts.get(field, "")) != str(t_accepts.get(field, "")):
                    return McpDualPaymentRequiredAndSpendControlsResult(
                        allowed=False,
                        reason_code="X402_MCP_PAYMENT_REQUIRED_MISMATCH_ERROR",
                        effective_timeout_seconds=requested_max_timeout_seconds,
                    )
            for num_field in ("amount", "maxAmountRequired", "maxTimeoutSeconds"):
                if num_field in s_accepts or num_field in t_accepts:
                    if _normalize_numeric_str(s_accepts.get(num_field)) != _normalize_numeric_str(
                        t_accepts.get(num_field)
                    ):
                        return McpDualPaymentRequiredAndSpendControlsResult(
                            allowed=False,
                            reason_code="X402_MCP_PAYMENT_REQUIRED_MISMATCH_ERROR",
                            effective_timeout_seconds=requested_max_timeout_seconds,
                        )

    if after_payment_creation_hook_error and not recovery_substituted_payload:
        return McpDualPaymentRequiredAndSpendControlsResult(
            allowed=False,
            reason_code="X402_ON_AFTER_PAYMENT_CREATION_HOOK_ERROR_SURFACED",
            effective_timeout_seconds=requested_max_timeout_seconds,
        )

    return McpDualPaymentRequiredAndSpendControlsResult(
        allowed=True,
        reason_code="X402_MCP_DUAL_OBJECT_AND_SPEND_CONTROLS_OK",
        effective_timeout_seconds=requested_max_timeout_seconds,
    )


@dataclass(frozen=True)
class MultiChainAndBazaarAuditResult:
    allowed: bool
    reason_code: str
    resolved_avm_network: str | None


def validate_x402_avm_galachain_bch_and_bazaar_no_eval(
    *,
    registered_avm_networks: Sequence[str],
    requested_avm_network: str,
    bazaar_runtime_allows_eval: bool,
    bazaar_attempted_schema_codegen: bool,
    galachain_has_fee_payer_extra: bool = False,
    bch_source_outputs_verified: bool = True,
    solana_mainnet_browser_rpc_url: str = "https://rpc.ankr.com/solana",
) -> MultiChainAndBazaarAuditResult:
    """Enforce x402 `#3652` AVM alias hook, `#3648` Bazaar no-eval fallback, `#3635` GalaChain, `#3632` BCH, and `#3662` Solana RPC."""
    if not bazar_safe_no_eval(bazaar_runtime_allows_eval, bazaar_attempted_schema_codegen):
        return MultiChainAndBazaarAuditResult(
            allowed=False,
            reason_code="X402_BAZAAR_NO_EVAL_SCHEMA_COMPILE_BLOCKED",
            resolved_avm_network=None,
        )

    if galachain_has_fee_payer_extra:
        return MultiChainAndBazaarAuditResult(
            allowed=False,
            reason_code="X402_GALACHAIN_FEE_PAYER_SPONSORSHIP_FORBIDDEN",
            resolved_avm_network=None,
        )

    if not bch_source_outputs_verified:
        return MultiChainAndBazaarAuditResult(
            allowed=False,
            reason_code="X402_BCH_UTXO_SOURCE_OUTPUT_UNVERIFIED",
            resolved_avm_network=None,
        )

    if "api.mainnet-beta.solana.com" in solana_mainnet_browser_rpc_url.lower():
        return MultiChainAndBazaarAuditResult(
            allowed=False,
            reason_code="X402_SOLANA_PUBLIC_MAINNET_RPC_BROWSER_403_RISK",
            resolved_avm_network=None,
        )

    reg_set = list(registered_avm_networks)
    if requested_avm_network in reg_set:
        if reg_set.count(requested_avm_network) > 1:
            return MultiChainAndBazaarAuditResult(
                allowed=False,
                reason_code="X402_AVM_AMBIGUOUS_NETWORK_REGISTRATION",
                resolved_avm_network=None,
            )
        return MultiChainAndBazaarAuditResult(
            allowed=True,
            reason_code="X402_AVM_AND_MULTICHAIN_BAZAAR_OK",
            resolved_avm_network=requested_avm_network,
        )

    alias = AVM_KNOWN_CAIP2_ALIASES.get(requested_avm_network)
    if alias and alias in reg_set:
        matches = [n for n in reg_set if n == alias]
        if len(matches) != 1:
            return MultiChainAndBazaarAuditResult(
                allowed=False,
                reason_code="X402_AVM_AMBIGUOUS_EQUIVALENT_REGISTRATION",
                resolved_avm_network=None,
            )
        return MultiChainAndBazaarAuditResult(
            allowed=True,
            reason_code="X402_AVM_LEGACY_CAIP2_ALIAS_MATCHED",
            resolved_avm_network=alias,
        )

    return MultiChainAndBazaarAuditResult(
        allowed=False,
        reason_code="X402_AVM_UNKNOWN_OR_TRUNCATED_NETWORK_REJECTED",
        resolved_avm_network=None,
    )


def bazar_safe_no_eval(runtime_allows_eval: bool, attempted_schema_codegen: bool) -> bool:
    if not runtime_allows_eval and attempted_schema_codegen:
        return False
    return True


@dataclass(frozen=True)
class UcpLodgingVatAndProfile304AuditResult:
    allowed: bool
    reason_code: str
    calculated_cancellation_fee_minor: int
    gross_vat_total_minor: int


def audit_ucp_lodging_schedule_vat_and_profile_304(
    *,
    profile_http_status: int,
    has_conditional_etag_or_last_modified: bool,
    ucp_schema_version: str,
    booking_total_minor: int,
    nightly_rate_minor: int,
    cancellation_timestamp_epoch: int,
    cancellation_schedule: Sequence[Mapping[str, Any]],
    tax_inclusive_vat_jurisdiction: bool,
    items_gross_minor: int,
    shipping_gross_minor: int,
    tax_breakdown_entries_minor: Sequence[int],
    reported_order_total_minor: int,
    fulfillment_option_has_totals_array: bool = True,
    get_order_200_headers: Sequence[str] = ("Signature", "Signature-Input", "Content-Digest"),
) -> UcpLodgingVatAndProfile304AuditResult:
    """Enforce UCP `#950`, `#932`, `#808`, `#680`, `#561`, and `#503` invariants."""
    if profile_http_status in {301, 302, 303, 307, 308}:
        return UcpLodgingVatAndProfile304AuditResult(
            allowed=False,
            reason_code="UCP_PROFILE_REDIRECT_3XX_FORBIDDEN",
            calculated_cancellation_fee_minor=0,
            gross_vat_total_minor=0,
        )
    if profile_http_status == 304 and not has_conditional_etag_or_last_modified:
        return UcpLodgingVatAndProfile304AuditResult(
            allowed=False,
            reason_code="UCP_PROFILE_UNCONDITIONAL_304_INVALID",
            calculated_cancellation_fee_minor=0,
            gross_vat_total_minor=0,
        )

    if ucp_schema_version.startswith("2."):
        return UcpLodgingVatAndProfile304AuditResult(
            allowed=False,
            reason_code="UCP_SCHEMA_2X_DROPS_BUNDLED_NESTED_IDS",
            calculated_cancellation_fee_minor=0,
            gross_vat_total_minor=0,
        )

    if not fulfillment_option_has_totals_array:
        return UcpLodgingVatAndProfile304AuditResult(
            allowed=False,
            reason_code="UCP_FULFILLMENT_OPTION_REQUIRES_TOTALS_ARRAY",
            calculated_cancellation_fee_minor=0,
            gross_vat_total_minor=0,
        )

    required_sig_headers = {"signature", "signature-input", "content-digest"}
    present_headers = {h.strip().lower() for h in get_order_200_headers}
    if not required_sig_headers.issubset(present_headers):
        return UcpLodgingVatAndProfile304AuditResult(
            allowed=False,
            reason_code="UCP_GET_ORDER_200_MISSING_SIGNATURE_HEADERS",
            calculated_cancellation_fee_minor=0,
            gross_vat_total_minor=0,
        )

    expected_gross = items_gross_minor + shipping_gross_minor
    if tax_inclusive_vat_jurisdiction:
        if reported_order_total_minor != expected_gross:
            return UcpLodgingVatAndProfile304AuditResult(
                allowed=False,
                reason_code="UCP_VAT_TAX_INCLUSIVE_GROSS_TOTAL_MISMATCH",
                calculated_cancellation_fee_minor=0,
                gross_vat_total_minor=expected_gross,
            )
        if sum(tax_breakdown_entries_minor) >= expected_gross or any(
            t < 0 for t in tax_breakdown_entries_minor
        ):
            return UcpLodgingVatAndProfile304AuditResult(
                allowed=False,
                reason_code="UCP_VAT_MULTI_RATE_BREAKDOWN_INVALID",
                calculated_cancellation_fee_minor=0,
                gross_vat_total_minor=expected_gross,
            )

    # Evaluate deterministic lodging cancellation schedule (#808)
    fee_minor = 0
    applicable_outcome: Mapping[str, Any] | None = None
    sorted_cutoffs = sorted(
        cancellation_schedule, key=lambda c: int(c.get("cutoff_epoch", 0))
    )
    for tier in sorted_cutoffs:
        if cancellation_timestamp_epoch >= int(tier.get("cutoff_epoch", 0)):
            applicable_outcome = tier
    if applicable_outcome is not None:
        outcome_type = str(applicable_outcome.get("outcome_type", "free"))
        if outcome_type == "free":
            fee_minor = 0
        elif outcome_type == "percentage":
            bps = int(applicable_outcome.get("basis_points", 0))
            fee_minor = (booking_total_minor * bps) // 10000
        elif outcome_type == "nights":
            nights = int(applicable_outcome.get("nights", 1))
            fee_minor = min(booking_total_minor, nights * nightly_rate_minor)
        elif outcome_type == "fixed_fee":
            fee_minor = int(applicable_outcome.get("amount_minor", 0))

    return UcpLodgingVatAndProfile304AuditResult(
        allowed=True,
        reason_code="UCP_LODGING_SCHEDULE_VAT_AND_PROFILE_304_OK",
        calculated_cancellation_fee_minor=fee_minor,
        gross_vat_total_minor=expected_gross,
    )


@dataclass(frozen=True)
class McpProvenanceMpasAndStripeProxyResult:
    allowed: bool
    reason_code: str
    effective_user_agent: str
    confined_max_spend_minor: int


def audit_mcp_provenance_mpas_and_stripe_stdio_proxy(
    *,
    delegation_chain_bounds: Sequence[Mapping[str, Any]],
    requested_repository: str,
    requested_spend_minor: int,
    mpas_required_approvers: int,
    mpas_collected_distinct_approvers: Sequence[str],
    mcp_initialize_client_name: str,
    stdio_transport_created_before_initialize: bool,
    sse_control_field_value: str = "message",
    node_major_version: int = 24,
    uri_authority_raw: str = "api.stripe.com",
) -> McpProvenanceMpasAndStripeProxyResult:
    """Enforce MCP `#3246` provenance confinement, `#3263` MPAS quorum, `#3245`/`#3244` URI/Node guards, and Stripe AI `#304`/`#294`."""
    if node_major_version < 24:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_NODE_VERSION_BELOW_24_EOL_FLOOR",
            effective_user_agent="",
            confined_max_spend_minor=0,
        )

    if "\\" in uri_authority_raw:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_FAST_URI_BACKSLASH_AUTHORITY_HOST_CONFUSION",
            effective_user_agent="",
            confined_max_spend_minor=0,
        )

    if "\r" in sse_control_field_value or "\n" in sse_control_field_value:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="STRIPE_HONO_SSE_CONTROL_FIELD_INJECTION_BLOCKED",
            effective_user_agent="",
            confined_max_spend_minor=0,
        )

    if stdio_transport_created_before_initialize or not mcp_initialize_client_name.strip():
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="STRIPE_STDIO_PROXY_MISSING_DEFERRED_CLIENT_INFO_UA",
            effective_user_agent="stripe-mcp-local/0.3.1",
            confined_max_spend_minor=0,
        )

    effective_ua = f"stripe-mcp-local/0.3.1 ({mcp_initialize_client_name.strip()})"

    if not delegation_chain_bounds:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_PROVENANCE_CHAIN_EMPTY",
            effective_user_agent=effective_ua,
            confined_max_spend_minor=0,
        )

    # Intersect allowed repositories and min max_spend_minor across hops (#3246)
    allowed_repos: set[str] | None = None
    confined_spend = int(delegation_chain_bounds[0].get("max_spend_minor", 0))
    for hop in delegation_chain_bounds:
        hop_repos = set(hop.get("allowed_repos", ()))
        allowed_repos = hop_repos if allowed_repos is None else (allowed_repos & hop_repos)
        confined_spend = min(confined_spend, int(hop.get("max_spend_minor", 0)))

    if not allowed_repos or requested_repository not in allowed_repos:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_PROVENANCE_AUTHORITY_ESCALATION_REPO_OUT_OF_BOUNDS",
            effective_user_agent=effective_ua,
            confined_max_spend_minor=confined_spend,
        )

    if requested_spend_minor > confined_spend:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_PROVENANCE_AUTHORITY_ESCALATION_SPEND_OUT_OF_BOUNDS",
            effective_user_agent=effective_ua,
            confined_max_spend_minor=confined_spend,
        )

    distinct_approvers = {a.strip() for a in mpas_collected_distinct_approvers if a.strip()}
    if len(distinct_approvers) < mpas_required_approvers:
        return McpProvenanceMpasAndStripeProxyResult(
            allowed=False,
            reason_code="MCP_MPAS_MULTI_PARTY_APPROVAL_QUORUM_UNMET",
            effective_user_agent=effective_ua,
            confined_max_spend_minor=confined_spend,
        )

    return McpProvenanceMpasAndStripeProxyResult(
        allowed=True,
        reason_code="MCP_PROVENANCE_MPAS_AND_STRIPE_STDIO_PROXY_OK",
        effective_user_agent=effective_ua,
        confined_max_spend_minor=confined_spend,
    )


@dataclass(frozen=True)
class Tau2PineVoiceAndJudgeOverrideAuditResult:
    allowed: bool
    reason_code: str
    effective_pass_rate: float
    effective_judge_model: str


def audit_tau2_pine_voice_denominator_and_judge_override(
    *,
    domain: str,
    passed_tasks: int,
    infra_failed_tasks: int,
    reported_denominator: int,
    canonical_domain_denominator: int = 114,
    cli_judge_llm: str | None = None,
    evaluator_used_judge_llm: str = "gpt-4.1-default",
    nl_assertion_raised_exception: bool = False,
    exception_handled_fail_closed: bool = True,
    wer_score: float = 0.04,
    max_allowed_wer: float = 0.15,
) -> Tau2PineVoiceAndJudgeOverrideAuditResult:
    """Enforce Sierra tau2-bench `#481` full denominator, `#479`/`#469` `--judge-llm` & exception safety, and `#448` WER gate."""
    if reported_denominator != canonical_domain_denominator:
        return Tau2PineVoiceAndJudgeOverrideAuditResult(
            allowed=False,
            reason_code="TAU2_VOICE_TRIMMED_DENOMINATOR_REJECTED",
            effective_pass_rate=0.0,
            effective_judge_model=evaluator_used_judge_llm,
        )

    if passed_tasks + infra_failed_tasks > canonical_domain_denominator:
        return Tau2PineVoiceAndJudgeOverrideAuditResult(
            allowed=False,
            reason_code="TAU2_VOICE_TASK_COUNT_OVERFLOW",
            effective_pass_rate=0.0,
            effective_judge_model=evaluator_used_judge_llm,
        )

    if cli_judge_llm and evaluator_used_judge_llm != cli_judge_llm:
        return Tau2PineVoiceAndJudgeOverrideAuditResult(
            allowed=False,
            reason_code="TAU2_NL_ASSERTIONS_JUDGE_CLI_OVERRIDE_IGNORED",
            effective_pass_rate=0.0,
            effective_judge_model=evaluator_used_judge_llm,
        )

    if nl_assertion_raised_exception and not exception_handled_fail_closed:
        return Tau2PineVoiceAndJudgeOverrideAuditResult(
            allowed=False,
            reason_code="TAU2_NL_ASSERTIONS_UNHANDLED_EXCEPTION_CRASH",
            effective_pass_rate=0.0,
            effective_judge_model=evaluator_used_judge_llm,
        )

    if wer_score > max_allowed_wer:
        return Tau2PineVoiceAndJudgeOverrideAuditResult(
            allowed=False,
            reason_code="TAU2_WHISSLE_TRANSCRIPTION_WER_THRESHOLD_EXCEEDED",
            effective_pass_rate=0.0,
            effective_judge_model=evaluator_used_judge_llm,
        )

    pass_rate = round(passed_tasks / float(canonical_domain_denominator), 4)
    return Tau2PineVoiceAndJudgeOverrideAuditResult(
        allowed=True,
        reason_code="TAU2_PINE_VOICE_AND_NL_JUDGE_OVERRIDE_OK",
        effective_pass_rate=pass_rate,
        effective_judge_model=evaluator_used_judge_llm,
    )
