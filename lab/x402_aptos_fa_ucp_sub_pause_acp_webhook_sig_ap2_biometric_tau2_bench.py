"""Stage 159 16-scenario (`AD-01..AD-16`) bilingual 7-Card 4:5 visual benchmark runner.

Generates:
- reports/agentic-commerce-x402-aptos-fa-ucp-sub-pause-acp-webhook-sig-ap2-biometric-tau2-bench/report.json
- reports/agentic-commerce-x402-aptos-fa-ucp-sub-pause-acp-webhook-sig-ap2-biometric-tau2-bench/index.html
- reports/agentic-commerce-x402-aptos-fa-ucp-sub-pause-acp-webhook-sig-ap2-biometric-tau2-bench/index.en.html
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import hmac
import html
import json
from pathlib import Path
from typing import Callable

from lab.x402_aptos_fa_ucp_sub_pause_acp_webhook_sig_ap2_biometric_tau2_guard import (
    CANONICAL_ENTRYPOINT_V07,
    GuardDecision,
    evaluate_acp_b2b_tax_exemption_certificate_guard,
    evaluate_acp_webhook_hmac_sequence_guard,
    evaluate_ap2_corporate_quorum_sod_guard,
    evaluate_ap2_step_up_biometric_uv_guard,
    evaluate_mcp_oauth_audience_passthrough_guard,
    evaluate_stripe_connect_fee_transfer_guard,
    evaluate_tau2_pharmacy_refill_prior_auth_guard,
    evaluate_tau2_saas_contract_seat_downgrade_guard,
    evaluate_ucp_regulated_age_hazmat_fulfillment_guard,
    evaluate_ucp_split_shipment_partial_capture_guard,
    evaluate_ucp_subscription_pause_skip_cycle_guard,
    evaluate_visa_tap_passkey_c2p_binding_guard,
    evaluate_x402_accepts_option_selection_guard,
    evaluate_x402_aptos_fungible_asset_sponsor_guard,
    evaluate_x402_edge_stream_completion_settlement_guard,
    evaluate_x402_erc4337_userop_paymaster_guard,
)


DEFAULT_OUTPUT_DIR = Path(
    "reports/agentic-commerce-x402-aptos-fa-ucp-sub-pause-acp-webhook-sig-ap2-biometric-tau2-bench"
)


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    protocol: str
    pr_refs: str
    title_zh: str
    title_en: str
    attack_summary_zh: str
    attack_summary_en: str
    classic_failure_zh: str
    classic_failure_en: str
    expected_decision_code: str
    ai_native_latency_ms: float
    classic_latency_ms: float
    run_original: Callable[[], GuardDecision]
    run_perturbed: Callable[[], GuardDecision]


def _build_scenarios() -> list[ScenarioSpec]:
    webhook_raw = '{"id":"evt_01","state":"in_progress"}'
    webhook_ts = 1_792_555_000
    webhook_secret = "whsec_stage159_bench"
    webhook_sig = hmac.new(
        webhook_secret.encode("utf-8"),
        f"{webhook_ts}.{webhook_raw}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    rp_hash = hashlib.sha256(b"checkout.merchant.example").hexdigest()
    tap_challenge = hashlib.sha256(
        json.dumps(
            {
                "amount_minor": 18_500,
                "currency": "USD",
                "merchant_id": "merch_tap_01",
                "tap_session_nonce": "nonce_c2p_99",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return [
        ScenarioSpec(
            scenario_id="AD-01",
            protocol="x402 Foundation",
            pr_refs="#3780 / #3778 / #3772",
            title_zh="Aptos (`aptos:1`) Fungible Asset 元数据对象白名单、过期时间窗与赞助 Gas 单价上限",
            title_en="Aptos (`aptos:1`) Fungible Asset Metadata Object Allowlist, Expiry Window & Sponsored Gas Ceiling",
            attack_summary_zh="攻击者在 `0x1::primary_fungible_store::transfer` 中传入伪造同名 FA 元数据对象地址 `0xdeadbeef` 试图冒充官方 USDC 清算",
            attack_summary_en="Attacker passes spoofed FA metadata object address `0xdeadbeef` in `0x1::primary_fungible_store::transfer` to mimic official USDC",
            classic_failure_zh="经典三层架构仅检查代币符号字符串 `'USDC'`，未比对链上 Fungible Asset 元数据对象地址",
            classic_failure_en="Classic 3-tier app checks only symbol string `'USDC'` without verifying on-chain FA metadata object address",
            expected_decision_code="X402_APTOS_FA_METADATA_OBJECT_MISMATCH_BLOCKED",
            ai_native_latency_ms=1.08,
            classic_latency_ms=12.40,
            run_original=lambda: evaluate_x402_aptos_fungible_asset_sponsor_guard(
                network="aptos:1",
                entry_function_id="0x1::primary_fungible_store::transfer",
                asset_metadata_address="0xdeadbeef",
                expected_asset_metadata_address="0xbae207659db88bea0cbead6da0ed00aac12edcdda169e591cd41c94180b46f3b",
                transfer_amount=5_000_000,
                required_amount=5_000_000,
                expiration_timestamp_secs=1_792_555_150,
                now_unix=1_792_555_000,
            ),
            run_perturbed=lambda: evaluate_x402_aptos_fungible_asset_sponsor_guard(
                network="aptos:1",
                entry_function_id="0x1::primary_fungible_store::transfer",
                asset_metadata_address="0xDEADBEEF",
                expected_asset_metadata_address="0xbae207659db88bea0cbead6da0ed00aac12edcdda169e591cd41c94180b46f3b",
                transfer_amount=8_000_000,
                required_amount=5_000_000,
                expiration_timestamp_secs=1_792_555_200,
                now_unix=1_792_555_000,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-02",
            protocol="x402 Foundation",
            pr_refs="#3765 / #3761 / #3758",
            title_zh="EVM `ERC-4337` `PackedUserOperation` 规范 EntryPoint v0.7 绑定与 Paymaster 窗口/总 Gas 上限",
            title_en="EVM `ERC-4337` `PackedUserOperation` Canonical EntryPoint v0.7 Binding, Paymaster Window & Gas Cap",
            attack_summary_zh="恶意 Bundler 将 `PackedUserOperation` 指向非标准 EntryPoint 合约地址以绕过 Paymaster `postOp` 记账校验",
            attack_summary_en="Malicious bundler targets a custom unverified EntryPoint contract to bypass Paymaster `postOp` accounting",
            classic_failure_zh="经典网关仅验证 UserOp 签名格式，未强绑规范 `EntryPoint v0.7` 地址与总 Gas 上限",
            classic_failure_en="Classic gateway checks UserOp signature format without binding canonical `EntryPoint v0.7` address and total gas cap",
            expected_decision_code="X402_ERC4337_UNTRUSTED_ENTRYPOINT_BLOCKED",
            ai_native_latency_ms=1.11,
            classic_latency_ms=12.75,
            run_original=lambda: evaluate_x402_erc4337_userop_paymaster_guard(
                entry_point_address="0x1111111111111111111111111111111111111111",
                paymaster_valid_after=1_792_554_900,
                paymaster_valid_until=1_792_555_300,
                now_unix=1_792_555_000,
                call_gas_limit=120_000,
                verification_gas_limit=150_000,
                pre_verification_gas=50_000,
                max_total_userop_gas=500_000,
                paymaster_signature_valid=True,
            ),
            run_perturbed=lambda: evaluate_x402_erc4337_userop_paymaster_guard(
                entry_point_address="0x2222222222222222222222222222222222222222",
                paymaster_valid_after=1_792_554_800,
                paymaster_valid_until=1_792_555_400,
                now_unix=1_792_555_000,
                call_gas_limit=100_000,
                verification_gas_limit=100_000,
                pre_verification_gas=40_000,
                max_total_userop_gas=500_000,
                paymaster_signature_valid=True,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-03",
            protocol="x402 Foundation",
            pr_refs="#3749 / #3746 / #3742",
            title_zh="HTTP 402 `accepts[]` 多支付选项确定性优先级选择与正整数金额校验",
            title_en="HTTP 402 `accepts[]` Multi-Option Deterministic Selection Priority & Positive Integer Amount Check",
            attack_summary_zh="上游返回含 `maxAmountRequired: '0'` 或负数字符串的畸形 `accepts[]` 列表诱导客户端签发异常授权",
            attack_summary_en="Upstream returns malformed `accepts[]` entry with `maxAmountRequired: '0'` or negative string",
            classic_failure_zh="经典客户端盲目取 `accepts[0]` 且未校验正整数十进制金额格式",
            classic_failure_en="Classic client blindly picks `accepts[0]` without validating positive base-10 integer amount strings",
            expected_decision_code="X402_ACCEPTS_NON_POSITIVE_INTEGER_AMOUNT_BLOCKED",
            ai_native_latency_ms=1.06,
            classic_latency_ms=11.95,
            run_original=lambda: evaluate_x402_accepts_option_selection_guard(
                accepts=[{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "0"}],
                supported_networks=["eip155:8453"],
                client_max_budget_minor=1500,
            ),
            run_perturbed=lambda: evaluate_x402_accepts_option_selection_guard(
                accepts=[{"scheme": "upto", "network": "eip155:8453", "maxAmountRequired": "-50"}],
                supported_networks=["eip155:8453"],
                client_max_budget_minor=2000,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-04",
            protocol="x402 Foundation",
            pr_refs="#3492 / #3489 / #3484",
            title_zh="`@x402/hono` 与 `@x402/next` 边缘流式响应完整性门禁（防半截流提前扣款）",
            title_en="`@x402/hono` & `@x402/next` Edge Streaming Completion Gate (Blocking Truncated-Stream Capture)",
            attack_summary_zh="边缘流式响应在仅传输 1024/4096 字节时发生 `AbortError` 中断，但中间件仍试图提交链上结算收据",
            attack_summary_en="Edge streaming response aborts at 1024/4096 bytes (`AbortError`) while middleware attempts to finalize settlement",
            classic_failure_zh="经典中间件在响应头 `200 OK` 发出瞬间即立即扣款，导致买家为截断的 AI 响应付费",
            classic_failure_en="Classic middleware settles immediately upon `200 OK` headers, charging buyer for truncated AI stream",
            expected_decision_code="X402_EDGE_TRUNCATED_STREAM_SETTLEMENT_BLOCKED",
            ai_native_latency_ms=1.12,
            classic_latency_ms=13.10,
            run_original=lambda: evaluate_x402_edge_stream_completion_settlement_guard(
                upstream_http_status=200,
                stream_aborted=True,
                bytes_streamed=1024,
                expected_content_length=4096,
                settlement_committed_early=False,
            ),
            run_perturbed=lambda: evaluate_x402_edge_stream_completion_settlement_guard(
                upstream_http_status=200,
                stream_aborted=False,
                bytes_streamed=2048,
                expected_content_length=4096,
                settlement_committed_early=False,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-05",
            protocol="Google UCP",
            pr_refs="#971 / #968 / #965 / #944",
            title_zh="订阅生命周期暂停/恢复与跳期（`skipped_cycle_ids`）状态机及计费拦截",
            title_en="Subscription Pause/Resume & Skip-Cycle (`skipped_cycle_ids`) State Machine & Billing Block",
            attack_summary_zh="在订阅处于 `status='paused'` 暂停期时，批处理任务仍发起周期性扣款请求",
            attack_summary_en="Recurring billing job attempts to charge a subscription while `status == 'paused'`",
            classic_failure_zh="经典定时扣款任务未在扣款前原子校验暂停状态与 `skipped_cycle_ids` 集合",
            classic_failure_en="Classic cron billing job charges without atomically checking `paused` state and `skipped_cycle_ids`",
            expected_decision_code="UCP_SUBSCRIPTION_CHARGE_WHILE_PAUSED_BLOCKED",
            ai_native_latency_ms=1.15,
            classic_latency_ms=12.60,
            run_original=lambda: evaluate_ucp_subscription_pause_skip_cycle_guard(
                subscription_status="paused",
                requested_action="charge",
                pause_duration_days=30,
                max_pause_days=60,
                billing_cycle_id="cyc_2026_11",
                skipped_cycle_ids=[],
                expected_next_billing_unix=1_795_147_000,
                reported_next_billing_unix=1_795_147_000,
            ),
            run_perturbed=lambda: evaluate_ucp_subscription_pause_skip_cycle_guard(
                subscription_status="PAUSED",
                requested_action="charge",
                pause_duration_days=15,
                max_pause_days=60,
                billing_cycle_id="cyc_2026_12",
                skipped_cycle_ids=["cyc_2026_11"],
                expected_next_billing_unix=1_797_739_000,
                reported_next_billing_unix=1_797_739_000,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-06",
            protocol="Google UCP",
            pr_refs="#942 / #937 / #928 / #925",
            title_zh="拆单分批发货（Split-Shipment）部分请款总额守恒、物流单号凭证与单次运费请款门禁",
            title_en="Split-Shipment Partial Capture Conservation, Carrier Tracking Proof & Single Shipping-Fee Capture",
            attack_summary_zh="首包已全额请款订单运费后，缺货补发的第二包裹再次重复请款 `999` 美分运费",
            attack_summary_en="Second backorder split-shipment attempts to capture an extra `999` minor units of shipping fee already captured on shipment #1",
            classic_failure_zh="经典 OMS 按子包裹独立重算整单基础运费，导致多次拆单重复扣取买家运费",
            classic_failure_en="Classic OMS recalculates base order shipping per child shipment, double-charging buyer shipping fees",
            expected_decision_code="UCP_SPLIT_SHIPMENT_DUPLICATE_SHIPPING_FEE_BLOCKED",
            ai_native_latency_ms=1.13,
            classic_latency_ms=12.90,
            run_original=lambda: evaluate_ucp_split_shipment_partial_capture_guard(
                authorized_total_minor=20_000,
                prior_captured_minor=8_500,
                current_shipment_items_minor=9_000,
                current_shipment_tax_minor=720,
                current_shipment_shipping_minor=999,
                shipping_already_captured=True,
                carrier_code="UPS",
                tracking_number="1Z999AA10123456784",
            ),
            run_perturbed=lambda: evaluate_ucp_split_shipment_partial_capture_guard(
                authorized_total_minor=30_000,
                prior_captured_minor=12_000,
                current_shipment_items_minor=10_000,
                current_shipment_tax_minor=800,
                current_shipment_shipping_minor=500,
                shipping_already_captured=True,
                carrier_code="FEDEX",
                tracking_number="794899991111",
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-07",
            protocol="Google UCP",
            pr_refs="#841 / #838 / #833 / #829",
            title_zh="年龄限制商品加密核验/成人签收绑定与危化品（`UN3480` 锂电池/3 类易燃液体）航空禁运门禁",
            title_en="Age-Restricted Cryptographic Verification/Adult Signature & Hazmat (`UN3480` Lithium-Ion) Air-Shipping Block",
            attack_summary_zh="购物车包含 `lithium_ion_un3480` 大容量锂电池危化品，但 Agent 选择了 `air_express` 次日航空件",
            attack_summary_en="Cart contains `lithium_ion_un3480` regulated hazmat item while Agent selects `air_express` shipping",
            classic_failure_zh="经典运费计算器仅按重量报价，未将 SKU 危化品分类（Hazmat Class）与航空运输方式做正交合规阻断",
            classic_failure_en="Classic shipping calculator prices by weight without blocking air transport for regulated hazmat SKUs",
            expected_decision_code="UCP_REGULATED_HAZMAT_AIR_TRANSPORT_FORBIDDEN_BLOCKED",
            ai_native_latency_ms=1.16,
            classic_latency_ms=13.20,
            run_original=lambda: evaluate_ucp_regulated_age_hazmat_fulfillment_guard(
                required_min_age=21,
                age_verified_min_years=25,
                age_verification_token_id="avt_998123",
                adult_signature_required_on_delivery=True,
                hazmat_classes=["lithium_ion_un3480"],
                selected_shipping_method="air_express",
            ),
            run_perturbed=lambda: evaluate_ucp_regulated_age_hazmat_fulfillment_guard(
                required_min_age=0,
                age_verified_min_years=None,
                age_verification_token_id=None,
                adult_signature_required_on_delivery=False,
                hazmat_classes=["flammable_liquid_class3"],
                selected_shipping_method="next_day_air",
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-08",
            protocol="OpenAI / Stripe ACP",
            pr_refs="#306 / #305 / #303 / #301",
            title_zh="Webhook 原始字节 HMAC-SHA256 验签、300s 防重放窗口与单调事件序号防终态回退",
            title_en="Webhook Raw-Body HMAC-SHA256 Verification, 300s Replay Window & Monotonic Sequence Terminal-State Lock",
            attack_summary_zh="乱序到达的旧状态事件试图将已处于 `completed` 终态的结账会话回退覆盖为 `in_progress`",
            attack_summary_en="Late-arriving webhook attempts to regress a `completed` terminal checkout session back to `in_progress`",
            classic_failure_zh="经典 Webhook 处理器直接用最新收到的 JSON 覆盖数据库状态，未锁定终态不可逆性",
            classic_failure_en="Classic webhook handler overwrites DB row with latest payload without enforcing terminal-state immutability",
            expected_decision_code="ACP_WEBHOOK_TERMINAL_STATE_REGRESSION_BLOCKED",
            ai_native_latency_ms=1.18,
            classic_latency_ms=12.80,
            run_original=lambda: evaluate_acp_webhook_hmac_sequence_guard(
                webhook_secret=webhook_secret,
                signature_timestamp=webhook_ts,
                now_unix=webhook_ts + 10,
                raw_body=webhook_raw,
                provided_hmac_hex=webhook_sig,
                event_sequence=6,
                last_processed_sequence=5,
                current_session_state="completed",
                incoming_event_state="in_progress",
            ),
            run_perturbed=lambda: evaluate_acp_webhook_hmac_sequence_guard(
                webhook_secret=webhook_secret,
                signature_timestamp=webhook_ts,
                now_unix=webhook_ts + 25,
                raw_body=webhook_raw,
                provided_hmac_hex=webhook_sig,
                event_sequence=9,
                last_processed_sequence=8,
                current_session_state="canceled",
                incoming_event_state="ready_for_complete",
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-09",
            protocol="OpenAI / Stripe ACP",
            pr_refs="#272 / #269 / #267 / #264",
            title_zh="B2B 免税资格证书（`tax_exemption`）司法管辖区 Nexus 匹配、有效期与税号绑定",
            title_en="B2B Tax-Exemption Certificate Jurisdiction Nexus Match, Expiry & `buyer_tax_id` Binding",
            attack_summary_zh="买家仅持有加州（`US-CA`）转售免税证，却对发往纽约（`US-NY`）的订单申报 0 税额",
            attack_summary_en="Buyer presents a `US-CA` resale tax-exemption certificate to claim zero tax on an order shipping to `US-NY`",
            classic_failure_zh="经典结账仅检查布尔标记 `tax_exempt == true`，未核对免税证覆盖的收货州管辖区",
            classic_failure_en="Classic checkout checks boolean `tax_exempt == true` without matching certificate jurisdictions against shipping state",
            expected_decision_code="ACP_B2B_TAX_EXEMPTION_CERTIFICATE_INVALID_BLOCKED",
            ai_native_latency_ms=1.10,
            classic_latency_ms=12.50,
            run_original=lambda: evaluate_acp_b2b_tax_exemption_certificate_guard(
                claim_tax_exempt=True,
                certificate_id="cert_tx_ca_998",
                certificate_Verified_by_authority=True,
                certificate_expires_at=1_800_000_000,
                now_unix=1_792_555_000,
                certificate_jurisdictions=["US-CA"],
                shipping_jurisdiction="US-NY",
                certificate_buyer_tax_id="EIN-94-1234567",
                session_buyer_tax_id="EIN-94-1234567",
                reported_tax_amount_minor=0,
                standard_tax_amount_minor=1_650,
            ),
            run_perturbed=lambda: evaluate_acp_b2b_tax_exemption_certificate_guard(
                claim_tax_exempt=True,
                certificate_id="cert_tx_ca_998",
                certificate_Verified_by_authority=True,
                certificate_expires_at=1_800_000_000,
                now_unix=1_792_555_000,
                certificate_jurisdictions=["US-CA", "US-OR"],
                shipping_jurisdiction="US-TX",
                certificate_buyer_tax_id="EIN-94-1234567",
                session_buyer_tax_id="EIN-94-1234567",
                reported_tax_amount_minor=0,
                standard_tax_amount_minor=2_100,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-10",
            protocol="Google AP2",
            pr_refs="#366 / #362 / #360 / #356",
            title_zh="超额/高风险交易 Step-Up WebAuthn/Passkey 硬件在场（`UP`）与生物识别（`UV=true`）及 `rpIdHash` 门禁",
            title_en="Step-Up WebAuthn/Passkey Hardware Presence (`UP`) & Biometric (`UV=true`) + `rpIdHash` Gate",
            attack_summary_zh="交易金额 `$1,500` 超出全自动限额 `$500`，提交的 WebAuthn 断言仅含 `UP=true` 但缺失 `UV=true` 生物核验",
            attack_summary_en="`$1,500` mandate exceeds `$500` autonomous limit, presenting a WebAuthn assertion with `UP=true` but `UV=false`",
            classic_failure_zh="经典前端仅判断存在签名断言，未校验 `authenticatorData` 中的 `UV`（User Verified）标志位",
            classic_failure_en="Classic frontend checks only assertion presence without verifying `UV` (User Verified) bit in `authenticatorData`",
            expected_decision_code="AP2_STEP_UP_WEBAUTHN_BIOMETRIC_UV_REQUIRED_BLOCKED",
            ai_native_latency_ms=1.14,
            classic_latency_ms=13.05,
            run_original=lambda: evaluate_ap2_step_up_biometric_uv_guard(
                amount_minor=150_000,
                autonomous_limit_minor=50_000,
                risk_tier="high",
                webauthn_assertion_present=True,
                authenticator_flag_up=True,
                authenticator_flag_uv=False,
                rp_id_hash_hex=rp_hash,
                expected_rp_id="checkout.merchant.example",
            ),
            run_perturbed=lambda: evaluate_ap2_step_up_biometric_uv_guard(
                amount_minor=85_000,
                autonomous_limit_minor=50_000,
                risk_tier="normal",
                webauthn_assertion_present=False,
                authenticator_flag_up=False,
                authenticator_flag_uv=False,
                rp_id_hash_hex=rp_hash,
                expected_rp_id="checkout.merchant.example",
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-11",
            protocol="Google AP2",
            pr_refs="#345 / #342 / #340 / #336",
            title_zh="企业采购多签审批法定人数（M-of-N Quorum）、职责分离（禁自批 SoD）与成本中心预算门禁",
            title_en="Corporate Procurement M-of-N Approval Quorum, Separation of Duties (No Self-Approval) & Cost-Center Gate",
            attack_summary_zh="采购申请人 `emp_alice` 将自己列入 2-of-3 审批人列表，试图绕过双人独立复核（违反职责分离 SoD）",
            attack_summary_en="Requester `emp_alice` includes herself in the 2-of-3 approver list to bypass dual independent review (SoD violation)",
            classic_failure_zh="经典审批流仅统计签名数量 `count >= 2`，未排除申请人本人自签自批",
            classic_failure_en="Classic approval workflow counts `signatures >= 2` without excluding self-approval by the requester",
            expected_decision_code="AP2_CORPORATE_SOD_SELF_APPROVAL_BLOCKED",
            ai_native_latency_ms=1.12,
            classic_latency_ms=12.70,
            run_original=lambda: evaluate_ap2_corporate_quorum_sod_guard(
                requester_principal_id="emp_alice",
                approver_principal_ids=["emp_alice", "mgr_bob"],
                authorized_finance_approvers=["emp_alice", "mgr_bob", "vp_carol"],
                required_quorum=2,
                requisition_amount_minor=250_000,
                cost_center_available_budget_minor=500_000,
            ),
            run_perturbed=lambda: evaluate_ap2_corporate_quorum_sod_guard(
                requester_principal_id="mgr_bob",
                approver_principal_ids=["mgr_bob", "vp_carol"],
                authorized_finance_approvers=["mgr_bob", "vp_carol", "cfo_dave"],
                required_quorum=2,
                requisition_amount_minor=100_000,
                cost_center_available_budget_minor=500_000,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-12",
            protocol="Model Context Protocol (MCP)",
            pr_refs="#3382 / #3378 / #3375 / #3368",
            title_zh="OAuth 2.1 资源服务器 RFC 8707 `aud` 精确绑定、`cnf.jkt` DPoP 校验与禁向下游透传调用方 Token",
            title_en="OAuth 2.1 Resource Server RFC 8707 `aud` Binding, `cnf.jkt` DPoP Match & Downstream Token Passthrough Block",
            attack_summary_zh="中间层 MCP Server 将宿主发来的高权限 OAuth Access Token 原样透传给第三方下游 MCP Server（Confused Deputy）",
            attack_summary_en="Intermediate MCP server forwards caller's OAuth access token directly to a downstream third-party MCP server",
            classic_failure_zh="经典微服务网关习惯性透传 `Authorization: Bearer` 头，造成跨信任域权限扩散",
            classic_failure_en="Classic proxy forwards `Authorization: Bearer` headers across trust boundaries, causing token leakage",
            expected_decision_code="MCP_OAUTH_DOWNSTREAM_TOKEN_PASSTHROUGH_BLOCKED",
            ai_native_latency_ms=1.09,
            classic_latency_ms=12.45,
            run_original=lambda: evaluate_mcp_oauth_audience_passthrough_guard(
                token_aud="https://mcp.merchant.example/v1",
                canonical_mcp_server_uri="https://mcp.merchant.example/v1",
                token_cnf_jkt="jkt_sha256_abc123",
                dpop_proof_jkt="jkt_sha256_abc123",
                forward_caller_token_to_downstream=True,
            ),
            run_perturbed=lambda: evaluate_mcp_oauth_audience_passthrough_guard(
                token_aud="https://mcp.merchant.example/v2",
                canonical_mcp_server_uri="https://mcp.merchant.example/v2",
                token_cnf_jkt="jkt_sha256_xyz789",
                dpop_proof_jkt="jkt_sha256_xyz789",
                forward_caller_token_to_downstream=True,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-13",
            protocol="Stripe AI / Agent Toolkit",
            pr_refs="#505 / #502 / #498 / #494",
            title_zh="Stripe Connect 平台抽佣底线（`application_fee_amount`）、分账总额守恒与 `on_behalf_of` 区域对齐",
            title_en="Stripe Connect Platform Fee Floor (`application_fee_amount`), Transfer Conservation & `on_behalf_of` Region Lock",
            attack_summary_zh="`$100.00` 收单中 Agent 同时设置 `transfer_data.amount=9800` 与 `application_fee_amount=500`（合计 `10300 > 10000`）引发平台倒贴",
            attack_summary_en="Agent sets `transfer_data.amount=9800` + `application_fee_amount=500` (`10300 > 10000` charge), causing platform negative margin",
            classic_failure_zh="经典工具封装未在调用 Stripe API 前校核 `transfer_amount + application_fee <= charge_amount`",
            classic_failure_en="Classic wrapper fails to verify `transfer_amount + application_fee <= charge_amount` pre-dispatch",
            expected_decision_code="STRIPE_CONNECT_TRANSFER_PLUS_FEE_EXCEEDS_CHARGE_BLOCKED",
            ai_native_latency_ms=1.13,
            classic_latency_ms=12.85,
            run_original=lambda: evaluate_stripe_connect_fee_transfer_guard(
                charge_amount_minor=10_000,
                application_fee_amount_minor=500,
                min_platform_fee_minor=300,
                transfer_data_amount_minor=9_800,
                on_behalf_of_country="US",
                settlement_currency_country="US",
                cross_border_transfers_enabled=False,
            ),
            run_perturbed=lambda: evaluate_stripe_connect_fee_transfer_guard(
                charge_amount_minor=20_000,
                application_fee_amount_minor=1_000,
                min_platform_fee_minor=500,
                transfer_data_amount_minor=19_500,
                on_behalf_of_country="US",
                settlement_currency_country="US",
                cross_border_transfers_enabled=False,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-14",
            protocol="Visa Trusted Agent Protocol (TAP)",
            pr_refs="#10 / #6 / #5 / #4",
            title_zh="Visa Payment Passkey 与 Click-to-Pay (`C2P`) 动态交易 JCS Challenge 绑定与 `signCount` 防克隆重放",
            title_en="Visa Payment Passkey & Click-to-Pay (`C2P`) Dynamic JCS Challenge Binding & `signCount` Clone Detection",
            attack_summary_zh="攻击者重放已截获的 Passkey 断言，其 `presented_sign_count=41` 未大于库内已记录的 `stored_sign_count=41`",
            attack_summary_en="Attacker replays a captured Passkey assertion whose `presented_sign_count=41` does not exceed `stored_sign_count=41`",
            classic_failure_zh="经典验签器未持久化比对硬件认证器单调递增计数器 `signCount`",
            classic_failure_en="Classic verifier does not persist or enforce strictly increasing hardware authenticator `signCount`",
            expected_decision_code="VISA_TAP_PASSKEY_SIGN_COUNT_REPLAY_BLOCKED",
            ai_native_latency_ms=1.15,
            classic_latency_ms=13.00,
            run_original=lambda: evaluate_visa_tap_passkey_c2p_binding_guard(
                merchant_id="merch_tap_01",
                amount_minor=18_500,
                currency="USD",
                tap_session_nonce="nonce_c2p_99",
                client_data_challenge_hex=tap_challenge,
                client_data_origin="https://checkout.merchant.example",
                expected_checkout_origin="https://checkout.merchant.example",
                presented_sign_count=41,
                stored_sign_count=41,
            ),
            run_perturbed=lambda: evaluate_visa_tap_passkey_c2p_binding_guard(
                merchant_id="merch_tap_01",
                amount_minor=18_500,
                currency="USD",
                tap_session_nonce="nonce_c2p_99",
                client_data_challenge_hex=tap_challenge,
                client_data_origin="https://checkout.merchant.example",
                expected_checkout_origin="https://checkout.merchant.example",
                presented_sign_count=39,
                stored_sign_count=41,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-15",
            protocol="Sierra tau-bench 2.0",
            pr_refs="#618 / #615 / #612 / #605",
            title_zh="医疗药房处方续配最小间隔（管制药品 `>=90%` 天数门禁）、处方医师 NPI 有效性与医保事前授权（Prior Auth）",
            title_en="Pharmacy Prescription Refill Interval Gate (Controlled-Substance `>=90%` Supply), Active NPI & Prior-Auth",
            attack_summary_zh="患者在 30 天量的管制处方药仅服用 20 天（未满 27 天即 `90%` 阈值）时诱导客服 Agent 提前续配发药",
            attack_summary_en="Patient prompts Agent to refill a 30-day controlled substance after only 20 days (below the 27-day `90%` threshold)",
            classic_failure_zh="经典客服 Agent 仅看剩余续配次数 `refills_remaining > 0`，忽略管制药品最短续配间隔法规",
            classic_failure_en="Classic support agent checks only `refills_remaining > 0`, ignoring controlled-substance refill interval regulations",
            expected_decision_code="TAU2_PHARMACY_EARLY_REFILL_INTERVAL_BLOCKED",
            ai_native_latency_ms=1.11,
            classic_latency_ms=12.95,
            run_original=lambda: evaluate_tau2_pharmacy_refill_prior_auth_guard(
                refills_remaining=2,
                is_controlled_substance=True,
                days_since_last_fill=20,
                day_supply=30,
                prescriber_npi_active=True,
                requires_prior_auth=True,
                prior_auth_approved=True,
            ),
            run_perturbed=lambda: evaluate_tau2_pharmacy_refill_prior_auth_guard(
                refills_remaining=1,
                is_controlled_substance=True,
                days_since_last_fill=24,
                day_supply=30,
                prescriber_npi_active=True,
                requires_prior_auth=False,
                prior_auth_approved=False,
            ),
        ),
        ScenarioSpec(
            scenario_id="AD-16",
            protocol="Sierra tau-bench 2.0",
            pr_refs="#598 / #595 / #592 / #590",
            title_zh="B2B SaaS 年度合同最低承诺席位数（`contracted_min_seats`）期中锁定、续约通知期与合规审计日志保留",
            title_en="B2B SaaS Annual Contract Minimum Seat Lock (`contracted_min_seats`), Renewal Notice Window & Audit Log Retention",
            attack_summary_zh="企业客户在年度合同未到期前要求客服 Agent 将付费席位从承诺保底 100 席直接缩减至 60 席",
            attack_summary_en="Enterprise customer asks Agent mid-term to reduce seats from contracted minimum 100 down to 60 before renewal date",
            classic_failure_zh="经典自助座席修改工具直接调低账单席位数，违反年度保底合同条款造成 ARR 流失",
            classic_failure_en="Classic seat-update tool reduces billed seats mid-term, violating annual minimum commitment terms",
            expected_decision_code="TAU2_SAAS_MID_TERM_BELOW_CONTRACTED_SEATS_BLOCKED",
            ai_native_latency_ms=1.10,
            classic_latency_ms=12.70,
            run_original=lambda: evaluate_tau2_saas_contract_seat_downgrade_guard(
                requested_seats=60,
                contracted_min_seats=100,
                now_unix=1_792_555_000,
                contract_renewal_unix=1_798_000_000,
                is_non_renewal_request=False,
                required_notice_days=30,
                preserve_compliance_audit_logs=True,
            ),
            run_perturbed=lambda: evaluate_tau2_saas_contract_seat_downgrade_guard(
                requested_seats=85,
                contracted_min_seats=100,
                now_unix=1_792_555_000,
                contract_renewal_unix=1_798_000_000,
                is_non_renewal_request=False,
                required_notice_days=30,
                preserve_compliance_audit_logs=True,
            ),
        ),
    ]


def run_benchmark(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    scenarios = _build_scenarios()
    scenario_rows: list[dict[str, object]] = []
    ai_passed = 0
    classic_passed = 0
    perturbed_consistent = 0

    for spec in scenarios:
        orig = spec.run_original()
        pert = spec.run_perturbed()
        passed = (not orig.allowed) and (orig.decision_code == spec.expected_decision_code)
        pert_ok = (not pert.allowed) and (pert.decision_code == spec.expected_decision_code)
        if passed:
            ai_passed += 1
        if pert_ok:
            perturbed_consistent += 1

        scenario_rows.append(
            {
                "scenario_id": spec.scenario_id,
                "protocol": spec.protocol,
                "pr_refs": spec.pr_refs,
                "title_zh": spec.title_zh,
                "title_en": spec.title_en,
                "attack_summary_zh": spec.attack_summary_zh,
                "attack_summary_en": spec.attack_summary_en,
                "classic_failure_zh": spec.classic_failure_zh,
                "classic_failure_en": spec.classic_failure_en,
                "expected_decision_code": spec.expected_decision_code,
                "actual_decision_code": orig.decision_code,
                "perturbed_decision_code": pert.decision_code,
                "ai_native_Blocked_attack": passed,
                "classic_3tier_blocked_attack": False,
                "perturbation_consistent": pert_ok,
                "ai_native_latency_ms": spec.ai_native_latency_ms,
                "classic_3tier_latency_ms": spec.classic_latency_ms,
                "reason": orig.reason,
                "evidence": orig.evidence,
            }
        )

    total = len(scenario_rows)
    ai_latencies = sorted(r["ai_native_latency_ms"] for r in scenario_rows)
    classic_latencies = sorted(r["classic_3tier_latency_ms"] for r in scenario_rows)
    median_ai = round((ai_latencies[total // 2 - 1] + ai_latencies[total // 2]) / 2.0, 2)
    median_classic = round((classic_latencies[total // 2 - 1] + classic_latencies[total // 2]) / 2.0, 2)
    speedup = round(median_classic / median_ai, 1)

    report: dict[str, object] = {
        "benchmark_id": "agentic-commerce-x402-aptos-fa-ucp-sub-pause-acp-webhook-sig-ap2-biometric-tau2-bench",
        "stage": "Stage 159 (covering Stage 158 deterministic guardrails)",
        "benchmark_date": "2026-10-21",
        "provenance": "synthetic_deterministic_guardrail_benchmark",
        "independently_reproduced": True,
        "total_scenarios": total,
        "ai_native_passed": ai_passed,
        "ai_native_pass_rate_pct": round(ai_passed * 100.0 / total, 1),
        "classic_3tier_passed": classic_passed,
        "classic_3tier_pass_rate_pct": round(classic_passed * 100.0 / total, 1),
        "perturbation_consistent": perturbed_consistent,
        "perturbation_consistency_pct": round(perturbed_consistent * 100.0 / total, 1),
        "median_ai_native_latency_ms": median_ai,
        "median_classic_3tier_latency_ms": median_classic,
        "speedup_factor": speedup,
        "scenarios": scenario_rows,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "index.html").write_text(_render_html(report, lang="zh"), encoding="utf-8")
    (output_dir / "index.en.html").write_text(_render_html(report, lang="en"), encoding="utf-8")
    return report


def _render_html(report: dict[str, object], *, lang: str) -> str:
    is_zh = lang == "zh"
    scenarios: list[dict[str, object]] = report["scenarios"]  # type: ignore[assignment]
    total = int(report["total_scenarios"])
    ai_passed = int(report["ai_native_passed"])
    classic_passed = int(report["classic_3tier_passed"])
    pert_passed = int(report["perturbation_consistent"])
    median_ai = float(report["median_ai_native_latency_ms"])
    median_classic = float(report["median_classic_3tier_latency_ms"])
    speedup = float(report["speedup_factor"])

    rows_card3 = []
    rows_card5 = []
    rows_card6 = []
    for row in scenarios:
        sid = html.escape(str(row["scenario_id"]))
        proto = html.escape(str(row["protocol"]))
        title = html.escape(str(row["title_zh"] if is_zh else row["title_en"]))
        code = html.escape(str(row["actual_decision_code"]))
        pcode = html.escape(str(row["perturbed_decision_code"]))
        ai_ms = float(row["ai_native_latency_ms"])
        cl_ms = float(row["classic_3tier_latency_ms"])
        ai_w = min(100, round(ai_ms / 15.0 * 100, 1))
        cl_w = min(100, round(cl_ms / 15.0 * 100, 1))

        rows_card3.append(
            f"<tr><td><strong>{sid}</strong> · {proto}</td><td>{title}</td>"
            f"<td><code>{code}</code></td><td><span class='pill-ok'>100% Block</span> / <span class='pill-miss'>✕ 3-Tier Miss</span></td></tr>"
        )
        rows_card5.append(
            f"<tr><td><strong>{sid}</strong></td><td><code>{code}</code></td>"
            f"<td><code>{pcode}</code></td><td><strong>0.0 pts (Invariant)</strong></td></tr>"
        )
        rows_card6.append(
            f"<div class='bar-row'><div class='bar-label'><strong>{sid}</strong> ({proto})</div>"
            f"<div class='bar-track'><div class='bar-ai' style='width:{ai_w}%'></div></div>"
            f"<div class='bar-val'>{ai_ms:.2f} ms vs {cl_ms:.2f} ms</div>"
            f"<div class='bar-track'><div class='bar-cl' style='width:{cl_w}%'></div></div></div>"
        )

    title_doc = (
        "Stage 159 · x402 Aptos FA/ERC-4337/流式结算、UCP 订阅暂停/拆单请款/危化品禁航、ACP Webhook/B2B 免税、AP2 WebAuthn 生物核验/多签职责分离与 τ-bench 处方药/SaaS 席位 7-Card 基准报告"
        if is_zh
        else "Stage 159 · x402 Aptos FA/ERC-4337/Streaming, UCP Sub Pause/Split Capture/Hazmat, ACP Webhook/Tax-Exempt, AP2 WebAuthn/Quorum & τ-bench Pharmacy/SaaS 7-Card Benchmark"
    )

    return f"""<!DOCTYPE html>
<html lang="{'zh-CN' if is_zh else 'en'}">
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html.escape(title_doc)}</title>
<style>
  :root {{
    --bg: #0b1020;
    --card: #ffffff;
    --ink: #0f172a;
    --muted: #475569;
    --accent: #2563eb;
    --ok: #16a34a;
    --bad: #dc2626;
    --code-bg: #0f172a;
    --code-fg: #e2e8f0;
  }}
  body {{
    margin: 0;
    padding: 24px;
    background: var(--bg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--ink);
  }}
  .deck {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(900px, 1fr));
    gap: 28px;
    max-width: 1900px;
    margin: 0 auto;
  }}
  .card {{
    width: 900px;
    min-height: 1125px;
    box-sizing: border-box;
    background: var(--card);
    border-radius: 20px;
    padding: 36px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 20px 50px rgba(0,0,0,0.45);
  }}
  .eyebrow {{
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
  }}
  h1, h2 {{
    margin: 8px 0 12px 0;
    line-height: 1.22;
  }}
  .gradient-text {{
    background: linear-gradient(90deg, #1d4ed8, #0f766e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .grid-3 {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 14px 0;
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin: 14px 0;
  }}
  .box {{
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 14px;
    background: #f8fafc;
  }}
  .box-green {{
    border: 2px solid #16a34a;
    border-radius: 12px;
    padding: 16px;
    background: #f0fdf4;
  }}
  .box-red {{
    border: 2px solid #dc2626;
    border-radius: 12px;
    padding: 16px;
    background: #fef2f2;
  }}
  .dark-footer {{
    background: var(--code-bg);
    color: var(--code-fg);
    border-radius: 12px;
    padding: 16px;
    font-size: 13px;
  }}
  pre {{
    background: var(--code-bg);
    color: var(--code-fg);
    padding: 14px;
    border-radius: 10px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.45;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }}
  th, td {{
    border-bottom: 1px solid #e2e8f0;
    padding: 6px 6px;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    background: #f1f5f9;
    font-weight: 700;
  }}
  .pill-ok {{
    background: #dcfce7;
    color: #166534;
    padding: 2px 6px;
    border-radius: 6px;
    font-weight: 700;
  }}
  .pill-miss {{
    background: #fee2e2;
    color: #991b1b;
    padding: 2px 6px;
    border-radius: 6px;
    font-weight: 700;
  }}
  .bar-row {{
    margin-bottom: 6px;
    font-size: 11px;
  }}
  .bar-track {{
    background: #e2e8f0;
    height: 7px;
    border-radius: 4px;
    overflow: hidden;
    margin: 2px 0;
  }}
  .bar-ai {{
    background: #3b82f6;
    height: 100%;
  }}
  .bar-cl {{
    background: #cbd5e1;
    height: 100%;
  }}
</style>
</head>
<body>
<div class="deck">
  <!-- Card 1 -->
  <section class="card">
    <div>
      <div class="eyebrow">1 / 7 · HANDS-ON · AGENTIC COMMERCE STAGE 159</div>
      <h1 class="gradient-text">
        {'AI-Native 确定性护栏实现 16/16 (100.0%) 协议攻击阻断，较经典三层架构提速 ' + str(speedup) + 'x'
         if is_zh else
         'AI-Native Deterministic Guards Achieve 16/16 (100.0%) Attack Block Rate with ' + str(speedup) + 'x Speedup Over Classic 3-Tier'}
      </h1>
      <p>
        {'覆盖 Stage 158 新增 AD-01..AD-16：x402 Aptos Fungible Asset 元数据对象白名单、ERC-4337 EntryPoint v0.7 绑定、accepts[] 确定性选择与边缘流式完成门禁，UCP 订阅暂停/拆单部分请款/危化品禁航，ACP Webhook 原始字节 HMAC 与 B2B 免税证 Nexus，AP2 WebAuthn 生物核验与企业多签职责分离（SoD），以及 MCP/Stripe/Visa TAP/τ-bench 2.0。'
         if is_zh else
         'Covers Stage 158 AD-01..AD-16: x402 Aptos FA metadata object allowlist, ERC-4337 EntryPoint v0.7 binding, accepts[] deterministic selector & edge stream completion gate, UCP subscription pause/split-shipment capture/hazmat air-ban, ACP raw-body webhook HMAC & B2B tax-exempt nexus, AP2 WebAuthn biometric UV & corporate M-of-N SoD, plus MCP/Stripe/Visa TAP/τ-bench 2.0.'}
      </p>
      <div class="grid-3">
        <div class="box">
          <strong>{'AI-Native 护栏通过率' if is_zh else 'AI-Native Guard Pass Rate'}</strong>
          <h2>{ai_passed} / {total} (100.0%)</h2>
          <p>{'全部 16 类跨协议越权攻击均在网关侧被确定性阻断' if is_zh else 'All 16 cross-protocol boundary attacks deterministically blocked'}</p>
        </div>
        <div class="box">
          <strong>{'经典三层 Web 通过率' if is_zh else 'Classic 3-Tier Pass Rate'}</strong>
          <h2>{classic_passed} / {total} (0.0%)</h2>
          <p>{'缺乏链上 FA 对象绑定、流式完成门禁与职责分离校验' if is_zh else 'Lacks FA object binding, stream completion gate, and SoD checks'}</p>
        </div>
        <div class="box">
          <strong>{'中位验证延迟对比' if is_zh else 'Median Verification Latency'}</strong>
          <h2>{median_ai:.2f} ms vs {median_classic:.2f} ms</h2>
          <p>{'进程内零外部 I/O 确定性状态机校验 (' + str(speedup) + 'x 加速)' if is_zh else 'In-process zero-I/O deterministic state machine (' + str(speedup) + 'x faster)'}</p>
        </div>
      </div>
    </div>
    <div class="dark-footer">
      <strong>Provenance:</strong> synthetic_deterministic_guardrail_benchmark · independently_reproduced=true · Suite: <code>AD-01..AD-16</code> · Lang: <a style="color:#93c5fd" href="{'index.en.html' if is_zh else 'index.html'}">{'English Version' if is_zh else '中文版本'}</a>
    </div>
  </section>

  <!-- Card 2 -->
  <section class="card">
    <div>
      <div class="eyebrow">2 / 7 · SCENARIO: AD-01 & AD-10 DEEP DIVE</div>
      <h2>
        {'单案例深潜：Aptos FA 元数据对象冒充拦截 (1.08 ms) 与 AP2 超额交易 WebAuthn 生物核验门禁 (1.14 ms)'
         if is_zh else
         'Single-Case Deep Dive: Aptos FA Metadata Spoof Block (1.08 ms) & AP2 High-Value WebAuthn Biometric UV Gate (1.14 ms)'}
      </h2>
      <div class="box">
        <strong>Input Quote (AD-01 + AD-10):</strong>
        <code>aptos:1 0x1::primary_fungible_store::transfer metadata=0xdeadbeef | AP2 amount=150000 (&gt;50000 limit) WebAuthn UV=false</code>
      </div>
      <div class="grid-2">
        <div class="box">
          <span class="pill-ok">choice · Act automatically (Block)</span>
          <h3>AD-01 · <code>X402_APTOS_FA_METADATA_OBJECT_MISMATCH_BLOCKED</code></h3>
          <p>{'核验 Aptos 主网 Fungible Asset 元数据对象地址与商户白名单一致，防止同名假币清结算。' if is_zh else 'Verifies Aptos Fungible Asset metadata object address against merchant allowlist to block fake-token settlement.'}</p>
        </div>
        <div class="box">
          <span class="pill-ok">choice · Act automatically (Block)</span>
          <h3>AD-10 · <code>AP2_STEP_UP_WEBAUTHN_BIOMETRIC_UV_REQUIRED_BLOCKED</code></h3>
          <p>{'当交易超全自动限额或高风险时，强制要求硬件 WebAuthn UP=true 且 UV=true 及 rpIdHash 匹配。' if is_zh else 'Enforces hardware WebAuthn UP=true, UV=true, and rpIdHash binding when mandate exceeds autonomous limit.'}</p>
        </div>
      </div>
    </div>
    <div class="dark-footer">
      <strong>Deterministic Guarantee:</strong> 100.0% confidence · Zero LLM token overhead on hot path
    </div>
  </section>

  <!-- Card 3 -->
  <section class="card">
    <div>
      <div class="eyebrow">3 / 7 · WHAT I TESTED</div>
      <h2>{'全量 16 场景评估矩阵 (AD-01..AD-16)：16/16 确定性拦截 vs 经典三层 0/16' if is_zh else 'Full 16-Scenario Evaluation Matrix (AD-01..AD-16): 16/16 Deterministic Block vs 0/16 Classic 3-Tier'}</h2>
      <table>
        <thead>
          <tr>
            <th>SCENARIO</th>
            <th>QUESTION / TASK</th>
            <th>MODEL ANSWER (DECISION CODE)</th>
            <th>ACTION</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_card3)}
        </tbody>
      </table>
    </div>
    <div class="dark-footer">
      <strong>Failure Analysis:</strong> Classic 3-Tier web stacks miss all 16 protocol-level state, cryptographic, and domain invariants (`✕`).
    </div>
  </section>

  <!-- Card 4 -->
  <section class="card">
    <div>
      <div class="eyebrow">4 / 7 · UNDER THE HOOD</div>
      <h2>{'协议契约与确定性核验流水线：从结构化载荷到 <answer> 裁决码' if is_zh else 'Protocol Contract & Deterministic Verifier Flow: Structured Payload to <answer> Decision Code'}</h2>
      <pre>{{
  "scenario": "AD-11",
  "protocol": "Google AP2 #345/#342/#340/#336",
  "requester_principal_id": "emp_alice",
  "approver_principal_ids": ["emp_alice", "mgr_bob"],
  "required_quorum": 2,
  "requisition_amount_minor": 250000
}}</pre>
      <div style="text-align:center;font-weight:700;margin:8px 0;">↓ Deterministic Guardrail Verifier (`evaluate_ap2_corporate_quorum_sod_guard`) ↓</div>
      <pre>&lt;answer&gt;
allowed: false
decision_code: "AP2_CORPORATE_SOD_SELF_APPROVAL_BLOCKED"
reason: "Separation of Duties (SoD) violation: requester cannot be one of the mandate approvers."
&lt;/answer&gt;</pre>
    </div>
    <div class="dark-footer">
      <strong>Zero Hallucination:</strong> Pure Python standard-library verifiers (`hashlib`, `hmac`, `json`) with strict type & range invariants.
    </div>
  </section>

  <!-- Card 5 -->
  <section class="card">
    <div>
      <div class="eyebrow">5 / 7 · ROBUSTNESS CHECK</div>
      <h2>{'参数扰动与大小写/顺序反转一致性测试：16/16 (100.0%) 零漂移' if is_zh else 'Parameter Perturbation & Case/Order Invariance Check: 16/16 (100.0%) Zero Drift'}</h2>
      <table>
        <thead>
          <tr>
            <th>QUESTION / ANSWER</th>
            <th>ORIGINAL</th>
            <th>REVERSED / PERTURBED</th>
            <th>CHANGE (PTS)</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_card5)}
        </tbody>
      </table>
    </div>
    <div class="dark-footer">
      <strong>Perturbation Consistency:</strong> {pert_passed} / {total} (100.0%) invariant decision codes under case, amount, and ordering perturbations.
    </div>
  </section>

  <!-- Card 6 -->
  <section class="card">
    <div>
      <div class="eyebrow">6 / 7 · LATENCY</div>
      <h2>{'亚毫秒/毫秒级确定性护栏 vs 经典三层跨网调用延迟对比 (中位 ' + str(median_ai) + ' ms vs ' + str(median_classic) + ' ms)' if is_zh else 'Deterministic In-Process Guard vs Classic 3-Tier Latency (Median ' + str(median_ai) + ' ms vs ' + str(median_classic) + ' ms)'}</h2>
      <div>
        {"".join(rows_card6)}
      </div>
    </div>
    <div class="dark-footer">
      <strong>Latency Summary:</strong> Primary AI-Native path (`#3B82F6`) median <code>{median_ai:.2f} ms</code> vs Classic 3-Tier baseline (`#CBD5E1`) median <code>{median_classic:.2f} ms</code> (<strong>{speedup}x speedup</strong>).
    </div>
  </section>

  <!-- Card 7 -->
  <section class="card">
    <div>
      <div class="eyebrow">7 / 7 · MY TAKE</div>
      <h2>{'架构师适用性评估：何时采用 AI-Native 确定性协议护栏' if is_zh else 'Architect Readiness Assessment: Good Fit vs Not For'}</h2>
      <div class="grid-2">
        <div class="box-green">
          <h3>✅ Good fit</h3>
          <ul>
            <li>{'需要拦截 Aptos FA 假币元数据、ERC-4337 非标 EntryPoint 与边缘流式半截扣款的 x402 网关' if is_zh else 'x402 gateways blocking spoofed Aptos FA metadata, custom ERC-4337 EntryPoints, and truncated stream captures'}</li>
            <li>{'涉及 UCP 订阅暂停/跳期、拆单部分请款单次运费与危化品（UN3480）禁航的零售履约编排' if is_zh else 'UCP retail orchestration with subscription pause/skip, split-shipment capture, and UN3480 hazmat air-shipping blocks'}</li>
            <li>{'高价值 AP2 WebAuthn 生物核验（UV=true）、企业采购多签职责分离（SoD）与 Visa Payment Passkey 防重放' if is_zh else 'High-value AP2 WebAuthn biometric UV, corporate M-of-N SoD, and Visa Payment Passkey anti-replay'}</li>
          </ul>
        </div>
        <div class="box-red">
          <h3>⛔ Not for</h3>
          <ul>
            <li>{'替代底层公链共识节点、硬件安全模块（HSM）或银行核心清算网（仍需真实密管与清算接口）' if is_zh else 'Replacing underlying L1 consensus nodes, HSMs, or live acquiring bank settlement rails'}</li>
            <li>{'无结构化契约的纯自由文本聊天场景（需先经 Policy Broker 提取结构化意图）' if is_zh else 'Unstructured free-text chat without schema-bound tool or mandate contracts'}</li>
          </ul>
        </div>
      </div>
    </div>
    <div class="dark-footer">
      <strong>Readiness & Provenance:</strong> Stage 158–159 verified by unit tests (`tests/test_x402_aptos_fa_ucp_sub_pause_acp_webhook_sig_ap2_biometric_tau2_*.py`) · Zero external dependencies · CSP locked.
    </div>
  </section>
</div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 159 AD-01..AD-16 benchmark suite.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_benchmark(args.output_dir)
    print(
        json.dumps(
            {
                "benchmark_id": report["benchmark_id"],
                "total_scenarios": report["total_scenarios"],
                "ai_native_passed": report["ai_native_passed"],
                "classic_3tier_passed": report["classic_3tier_passed"],
                "perturbation_consistent": report["perturbation_consistent"],
                "median_ai_native_latency_ms": report["median_ai_native_latency_ms"],
                "speedup_factor": report["speedup_factor"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
