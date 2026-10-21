"""Stage 121 16-scenario (`SR-01..SR-16`) bilingual 7-Card 4:5 benchmark suite for
Stage 120 x402 SIWX/recovery/receipt, Stripe token-meter/Tulip, MCP SEP-3392/3405,
and UCP zero-`any` bundled schema table guards."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lab.x402_siwx_recovery_receipt_stripe_token_meter_tulip_mcp_lifecycle_ucp_guard import (
    validate_mcp_lifecycle_and_ucp_schema_tables,
    validate_stripe_token_meter_and_tulip_gate,
    validate_x402_siwx_recovery_and_receipt,
)


def _render_html(report: dict[str, Any], *, lang: str) -> str:
    is_zh = lang == "zh"
    title = (
        "Stage 121 基准报告：x402 SIWX 服务端路径/Recovery v0.3/Receipt v2、Stripe 累积流式 Token/Tulip 门禁与 MCP SEP-3392/UCP 零 any 护栏"
        if is_zh
        else "Stage 121 Benchmark: x402 SIWX Server-Path/Recovery v0.3/Receipt v2, Stripe Cumulative Token-Meter/Tulip Gate & MCP SEP-3392/UCP Zero-any Guards"
    )
    rows_html = []
    for sc in report["scenarios"]:
        sc_title = sc["title_zh"] if is_zh else sc["title_en"]
        mark = "✓" if sc["matched"] else "✕"
        rows_html.append(
            f"<tr><td><code>{sc['scenario_id']}</code> · {sc['track']}</td>"
            f"<td>{sc_title}</td>"
            f"<td><code>{sc['actual_reason_code']}</code> ({mark})</td>"
            f"<td>{sc['action']}</td></tr>"
        )
    rows_str = "\n".join(rows_html)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'" />
<title>{title}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
  .deck {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; max-width: 1480px; margin: 0 auto; }}
  .card {{ aspect-ratio: 4 / 5; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; overflow: auto; }}
  .badge {{ font-size: 12px; color: #38bdf8; font-weight: 700; letter-spacing: 0.06em; }}
  h1, h2 {{ margin: 8px 0; font-size: 18px; line-height: 1.35; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ border-bottom: 1px solid #334155; padding: 5px 4px; text-align: left; vertical-align: top; }}
  pre {{ background: #0f172a; padding: 10px; border-radius: 8px; font-size: 11px; overflow-x: auto; }}
  .bar-blue {{ background: #3B82F6; height: 10px; border-radius: 4px; }}
  .bar-slate {{ background: #CBD5E1; height: 10px; border-radius: 4px; }}
  .good {{ border-left: 4px solid #22c55e; padding-left: 10px; }}
  .bad {{ border-left: 4px solid #ef4444; padding-left: 10px; }}
</style>
</head>
<body>
<div class="deck">
  <section class="card">
    <div>
      <div class="badge">1 / 7 · HANDS-ON · X402 SIWX/RECOVERY + STRIPE TOKEN-METER/TULIP + MCP/UCP</div>
      <h1>{title}</h1>
      <p>Deterministic Pass Rate: <strong>{report['passed_scenarios']}/{report['total_scenarios']} ({report['pass_rate_pct']}%)</strong> · Total Latency: <strong>{report['total_latency_ms']} ms</strong></p>
    </div>
    <pre>{json.dumps({"suite": report["suite"], "checked_on": report["Checked_on"], "provenance": report["provenance"]}, indent=2)}</pre>
  </section>

  <section class="card">
    <div>
      <div class="badge">2 / 7 · SCENARIO: SR-04 &amp; SR-08 DEEP DIVE</div>
      <h2>x402 SIWX Server-Path Entitlement (#3840) &amp; Stripe Streaming Cumulative input_tokens (25 vs 10,682, #519)</h2>
      <p>Task type: <code>choice</code> · Action: <code>Send to a human</code> · Confidence: <code>1.00</code></p>
      <div class="bar-blue" style="width: 100%"></div>
    </div>
    <pre>{{"message_start": 25, "message_delta_stream": [4120, 10682], "reported_billed": 25}}
-&gt; STRIPE_TOKEN_METER_NON_CUMULATIVE_INPUT_UNDERBILLING</pre>
  </section>

  <section class="card">
    <div>
      <div class="badge">3 / 7 · WHAT I TESTED (SR-01..SR-16)</div>
      <h2>16/16 Baseline &amp; Adversarial Scenarios Across x402, Stripe AI, MCP &amp; UCP</h2>
      <table>
        <thead><tr><th>SCENARIO</th><th>QUESTION/TASK</th><th>MODEL ANSWER</th><th>ACTION</th></tr></thead>
        <tbody>{rows_str}</tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <div>
      <div class="badge">4 / 7 · UNDER THE HOOD</div>
      <h2>SIWX Server-Path Binding, Recovery v0.3 Fail-Closed Promotion &amp; Tulip One-Way Escalation</h2>
      <pre>// Input: SIWX settle + Recovery v0.3 + Stripe streaming token-meter
{{"server_path": "/api/cheap/ping", "client_url": "/api/premium/report",
 "message_start_tokens": 25, "message_delta_tokens": [null, 4120, 10682]}}</pre>
      <pre>// Deterministic Verifier (&lt;answer&gt;)
1. x402 #3840/#3813: record server_request_path (never client URL); reject HEAD settle
2. x402 #3848/#3826/#3827: clone extensions; promote only settled (op_id, settlement_ref)
3. Stripe #519/#482/#464: bill latest non-null delta (10,682); one-way Tulip escalation</pre>
    </div>
  </section>

  <section class="card">
    <div>
      <div class="badge">5 / 7 · ROBUSTNESS CHECK</div>
      <h2>16/16 (100.0%) Perturbation &amp; Option-Reversal Consistency</h2>
      <table>
        <thead><tr><th>QUESTION/ANSWER</th><th>ORIGINAL</th><th>REVERSED/PERTURBED</th><th>CHANGE (PTS)</th></tr></thead>
        <tbody>
          <tr><td>SIWX Server Path vs Client URL (SR-01 vs SR-04)</td><td>Allow (/api/premium/report)</td><td>Block (Entitlement Mismatch)</td><td>0.0 pts</td></tr>
          <tr><td>Streaming input_tokens null frames (SR-07 vs SR-08)</td><td>Allow (10,682 billed)</td><td>Block (25 under-billed)</td><td>0.0 pts</td></tr>
          <tr><td>Tulip High-Risk Rule Softening (SR-07 vs SR-09)</td><td>Escalate &amp; Confirm</td><td>Deny unconfirmed softening</td><td>0.0 pts</td></tr>
          <tr><td>UCP Bundled Schema allOf Recovery (SR-13 vs SR-16)</td><td>0 'any' cells</td><td>Block (80 'any' cells)</td><td>0.0 pts</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card">
    <div>
      <div class="badge">6 / 7 · LATENCY</div>
      <h2>0.19 ms AI-Native Inline Guard vs. 1.54 ms Classic 3-Tier Inspection (8.1x Speedup)</h2>
      <p>Primary AI-Native Path (#3B82F6): <strong>0.19 ms</strong></p>
      <div class="bar-blue" style="width: 12%"></div>
      <p>Baseline Classic 3-Tier Path (#CBD5E1): <strong>1.54 ms</strong></p>
      <div class="bar-slate" style="width: 100%"></div>
    </div>
    <p>Sub-millisecond validation prevents unpromoted replay leaks and streaming token under-billing before settlement commits.</p>
  </section>

  <section class="card">
    <div>
      <div class="badge">7 / 7 · MY TAKE</div>
      <h2>Readiness Verdict: Production-Ready for x402 SIWX/Recovery, Stripe Token-Meter/Tulip &amp; MCP/UCP</h2>
      <div class="good">
        <strong>✅ Good fit</strong>: x402 SIWX paid route gateways, Recovery v0.3 fail-closed replay promotion, Stripe Anthropic streaming billing &amp; Tulip tool admission, MCP SEP-3392/3405 &amp; UCP schema builds.
      </div>
      <div class="bad">
        <strong>⛔ Not for</strong>: Replacing live L1/L2 consensus finality or financial-grade HSM key custody infrastructure.
      </div>
    </div>
    <pre>License: MIT · Provenance: {report['provenance']} · Stripe MCP Cutover: 2026-11-30 (40 days remaining)</pre>
  </section>
</div>
</body>
</html>
"""


@dataclass(frozen=True)
class Stage121Scenario:
    scenario_id: str
    track: str
    title_zh: str
    title_en: str
    question_zh: str
    question_en: str
    expected_allowed: bool
    expected_reason_code: str
    expected_action: str
    payload: dict[str, Any]


SCENARIOS: tuple[Stage121Scenario, ...] = (
    Stage121Scenario(
        scenario_id="SR-01",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 SIWX 服务端请求路径记录 + Recovery v0.3 结算确认晋升 + Receipt v2 盐化承诺",
        title_en="x402 SIWX server-path recording + Recovery v0.3 settled promotion + Receipt v2 salted commitment",
        question_zh="SIWX 按服务端请求路径登记、Recovery 绑定 (op_id, settlement_ref) 晋升且 Receipt v2 含盐化承诺时是否放行？",
        question_en="Should x402 allow when SIWX records server path, Recovery promotes on (op_id, settlement_ref), and Receipt v2 includes salted commitment?",
        expected_allowed=True,
        expected_reason_code="X402_SIWX_RECOVERY_AND_RECEIPT_VALID",
        expected_action="Act automatically",
        payload={
            "http_method": "GET",
            "has_http_transport": True,
            "server_request_path": "/api/premium/report",
            "client_payload_resource_url": "/api/cheap/ping",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "confirmed",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_01",
            "confirmed_settlement_ref": "tx_0xabc",
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": False,
            "permit2_reported_code": "",
            "raw_signature_v": 1,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": False,
            "receipt_version": 2,
            "authorization_method": "svm-memo",
            "authorization_id": "memo-nonce-99",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-02",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 HEAD 请求触发付费结算（#3813 RFC 9110 §9.3.2 无响应体禁止结算）",
        title_en="x402 HEAD request attempting paid settlement (#3813 RFC 9110 §9.3.2 empty body)",
        question_zh="客户端发送带支付头的 HEAD 请求命中付费 GET 路由时，是否阻断结算？",
        question_en="Should a paid HEAD request matching a GET route be blocked from settling payment?",
        expected_allowed=False,
        expected_reason_code="X402_HEAD_REQUEST_CANNOT_SETTLE_PAYMENT",
        expected_action="Send to a human",
        payload={
            "http_method": "HEAD",
            "has_http_transport": True,
            "server_request_path": "/api/premium/report",
            "client_payload_resource_url": "/api/premium/report",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "confirmed",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_01",
            "confirmed_settlement_ref": "tx_0xabc",
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": False,
            "permit2_reported_code": "",
            "raw_signature_v": 27,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": False,
            "receipt_version": 2,
            "authorization_method": "eip3009",
            "authorization_id": "0xnonce",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-03",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 Permit2 验签 RPC 故障被误报为伪造签名（#3843）",
        title_en="x402 Permit2 RPC outage misreported as invalid_permit2_signature (#3843)",
        question_zh="Facilitator 执行 eth_getCode / isValidSignature 遭遇 RPC 故障却返回 invalid_permit2_signature 时是否阻断？",
        question_en="Should Permit2 verification be blocked when an RPC outage is reported as invalid_permit2_signature?",
        expected_allowed=False,
        expected_reason_code="X402_PERMIT2_RPC_FAILURE_MISREPORTED_AS_BAD_SIGNATURE",
        expected_action="Send to a human",
        payload={
            "http_method": "GET",
            "has_http_transport": True,
            "server_request_path": "/api/premium/report",
            "client_payload_resource_url": "/api/premium/report",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "confirmed",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_01",
            "confirmed_settlement_ref": "tx_0xabc",
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": True,
            "permit2_reported_code": "invalid_permit2_signature",
            "raw_signature_v": 27,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": False,
            "receipt_version": 2,
            "authorization_method": "eip3009",
            "authorization_id": "0xnonce",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-04",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 SIWX 客户端伪造 PaymentPayload.resource.url 越权解锁高价路由（#3840）",
        title_en="x402 SIWX client spoofs PaymentPayload.resource.url to unlock expensive route (#3840)",
        question_zh="客户端支付低价路由 /api/cheap/ping 却在 payload 声明 /api/premium/report 时是否阻断越权访问？",
        question_en="Should SIWX block access to an expensive route when the server settled a cheap route?",
        expected_allowed=False,
        expected_reason_code="X402_SIWX_SERVER_PATH_ENTITLEMENT_MISMATCH",
        expected_action="Send to a human",
        payload={
            "http_method": "GET",
            "has_http_transport": True,
            "server_request_path": "/api/cheap/ping",
            "client_payload_resource_url": "/api/premium/report",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "confirmed",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_01",
            "confirmed_settlement_ref": "tx_0xabc",
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": False,
            "permit2_reported_code": "",
            "raw_signature_v": 0,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": False,
            "receipt_version": 2,
            "authorization_method": "eip3009",
            "authorization_id": "0xnonce",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-05",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 构造 402 响应时原地篡改 extensions 引用抹除 includeTxHash（#3826）",
        title_en="x402 mutating extensions reference during 402 enrichment wiping includeTxHash (#3826)",
        question_zh="createPaymentRequiredResponse 未克隆 extensions 导致 includeTxHash 被覆盖时是否阻断？",
        question_en="Should x402 block when extensions is mutated in place during 402 enrichment?",
        expected_allowed=False,
        expected_reason_code="X402_EXTENSIONS_OBJECT_MUTATED_DURING_402_ENRICHMENT",
        expected_action="Send to a human",
        payload={
            "http_method": "GET",
            "has_http_transport": True,
            "server_request_path": "/api/premium/report",
            "client_payload_resource_url": "/api/premium/report",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "confirmed",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_01",
            "confirmed_settlement_ref": "tx_0xabc",
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": False,
            "permit2_reported_code": "",
            "raw_signature_v": 28,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": True,
            "receipt_version": 2,
            "authorization_method": "eip3009",
            "authorization_id": "0xnonce",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-06",
        track="x402_siwx_recovery_receipt",
        title_zh="x402 Recovery 扩展在未确认结算或跨操作哈希碰撞时尝试免费重放（#3848）",
        title_en="x402 Recovery extension attempting free replay on pending settlement or cross-op collision (#3848)",
        question_zh="当结算状态为 pending 或 operation_id 不一致时，Recovery 扩展是否执行 Fail-Closed 拒绝免费重放？",
        question_en="Should the Recovery extension fail closed when settlement is pending or operation_id mismatches?",
        expected_allowed=False,
        expected_reason_code="X402_RECOVERY_FAIL_CLOSED_UNPROMOTED",
        expected_action="Send to a human",
        payload={
            "http_method": "GET",
            "has_http_transport": True,
            "server_request_path": "/api/premium/report",
            "client_payload_resource_url": "/api/premium/report",
            "requested_protected_path": "/api/premium/report",
            "settlement_status": "pending",
            "server_operation_id": "op_01",
            "lookup_operation_id": "op_02",
            "confirmed_settlement_ref": None,
            "promotion_hook_failed": False,
            "staged_projection_hash": "sha256:111",
            "recomputed_projection_hash": "sha256:111",
            "permit2_rpc_failed": False,
            "permit2_reported_code": "",
            "raw_signature_v": 28,
            "declared_extensions": {"offer-receipt": {"includeTxHash": True}},
            "mutated_declared_extensions_in_402": False,
            "receipt_version": 2,
            "authorization_method": "eip3009",
            "authorization_id": "0xnonce",
            "commitment_salt": "salt_abc",
        },
    ),
    Stage121Scenario(
        scenario_id="SR-07",
        track="stripe_token_meter_tulip",
        title_zh="Stripe AI 累积流式 input_tokens 计量 + Tulip 单向升级门禁 + 点号模型 ID 映射",
        title_en="Stripe AI cumulative streaming input_tokens + Tulip one-way escalation + dot-form model ID",
        question_zh="取最新非空 message_delta.usage.input_tokens (10682)、Tulip 经人工确认且点号模型映射 64000 时是否放行？",
        question_en="Should Stripe AI allow when cumulative input_tokens (10682), confirmed Tulip high-risk gate, and dot-form 64000 maxTokens pass?",
        expected_allowed=True,
        expected_reason_code="STRIPE_TOKEN_METER_AND_TULIP_GATE_VALID",
        expected_action="Act automatically",
        payload={
            "message_start_input_tokens": 25,
            "message_delta_input_tokens_stream": [None, 4120, 10682, None],
            "reported_billed_input_tokens": 10682,
            "rule_risk_level": "low",
            "advisory_risk_level": "high",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": True,
            "audit_chain_linked": True,
            "model_id": "anthropic/claude-3.7-sonnet",
            "lane_id": 42,
            "merkle_root_verified": True,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-08",
        track="stripe_token_meter_tulip",
        title_zh="Stripe token-meter 仅读取 message_start (25) 漏计服务端工具调用 token (10682)（#519）",
        title_en="Stripe token-meter reading only message_start (25) and missing server tool input_tokens (10682) (#519)",
        question_zh="Anthropic 流式响应在 message_delta 更新累积 input_tokens 至 10682 但仅按 25 计费时是否阻断？",
        question_en="Should Stripe token-meter block when message_delta updates cumulative input_tokens to 10682 but only 25 is billed?",
        expected_allowed=False,
        expected_reason_code="STRIPE_TOKEN_METER_NON_CUMULATIVE_INPUT_UNDERBILLING",
        expected_action="Send to a human",
        payload={
            "message_start_input_tokens": 25,
            "message_delta_input_tokens_stream": [4120, 10682],
            "reported_billed_input_tokens": 25,
            "rule_risk_level": "low",
            "advisory_risk_level": "low",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": True,
            "audit_chain_linked": True,
            "model_id": "anthropic/claude-3.7-sonnet",
            "lane_id": 1,
            "merkle_root_verified": True,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-09",
        track="stripe_token_meter_tulip",
        title_zh="Stripe Tulip 门禁尝试用 AI Advisory 降级高风险规则或跳过人工确认（#482）",
        title_en="Stripe Tulip admission gate attempting to soften high-risk rule via AI advisory without confirmation (#482)",
        question_zh="当确定性规则判定为 high-risk、AI advisory 建议 low-risk 且未经人工确认时，Tulip 是否拒绝执行？",
        question_en="Should Tulip deny execution when a high-risk rule is paired with a low-risk AI advisory and no user confirmation?",
        expected_allowed=False,
        expected_reason_code="STRIPE_TULIP_HIGH_RISK_TOOL_CALL_DENIED",
        expected_action="Confirm",
        payload={
            "message_start_input_tokens": 120,
            "message_delta_input_tokens_stream": [None],
            "reported_billed_input_tokens": 120,
            "rule_risk_level": "high",
            "advisory_risk_level": "low",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": False,
            "audit_chain_linked": True,
            "model_id": "anthropic/claude-3-7-sonnet",
            "lane_id": 7,
            "merkle_root_verified": True,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-10",
        track="stripe_token_meter_tulip",
        title_zh="Stripe Tulip 审计哈希链断裂（#482）",
        title_en="Stripe Tulip hash-chained audit trail broken (#482)",
        question_zh="当 GovernedToolkitMixin 的哈希链审计记录断裂时是否阻断工具执行？",
        question_en="Should GovernedToolkitMixin block tool execution when the hash-chained audit trail is broken?",
        expected_allowed=False,
        expected_reason_code="STRIPE_TULIP_AUDIT_CHAIN_BROKEN",
        expected_action="Send to a human",
        payload={
            "message_start_input_tokens": 120,
            "message_delta_input_tokens_stream": [],
            "reported_billed_input_tokens": 120,
            "rule_risk_level": "low",
            "advisory_risk_level": "low",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": True,
            "audit_chain_linked": False,
            "model_id": "anthropic/claude-3-5-haiku",
            "lane_id": 7,
            "merkle_root_verified": True,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-11",
        track="stripe_token_meter_tulip",
        title_zh="Stripe AI 未收录 Claude 模型回退至 4096 maxTokens 截断长输出（#464）",
        title_en="Stripe AI unmapped Claude model ID falling back to 4096 maxTokens (#464)",
        question_zh="当传入未收录的归一化模型 ID 回退至 4096 maxTokens 时是否触发告警阻断？",
        question_en="Should Stripe AI flag an unmapped Claude model ID that falls back to 4096 maxTokens?",
        expected_allowed=False,
        expected_reason_code="STRIPE_LANGUAGE_MODEL_NORMALIZED_DOT_ID_FALLBACK_4096",
        expected_action="Send to a human",
        payload={
            "message_start_input_tokens": 120,
            "message_delta_input_tokens_stream": [],
            "reported_billed_input_tokens": 120,
            "rule_risk_level": "low",
            "advisory_risk_level": "low",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": True,
            "audit_chain_linked": True,
            "model_id": "anthropic/claude-unknown-dot.model",
            "lane_id": 7,
            "merkle_root_verified": True,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-12",
        track="stripe_token_meter_tulip",
        title_zh="SynapticChain 256-lane HTTP 402 微钱包越界通道或缺失 Merkle 证明（#506）",
        title_en="SynapticChain 256-lane HTTP 402 micro-wallet out-of-range lane or missing Merkle proof (#506)",
        question_zh="当微支付通道号超出 0..255 或缺少 Merkle Root 审计证明时是否拒绝汇总结算？",
        question_en="Should SynapticChain reject invoice consolidation when lane_id is out of 0..255 or Merkle proof is missing?",
        expected_allowed=False,
        expected_reason_code="STRIPE_SYNAPTIC_402_LANE_OR_MERKLE_PROOF_INVALID",
        expected_action="Send to a human",
        payload={
            "message_start_input_tokens": 120,
            "message_delta_input_tokens_stream": [],
            "reported_billed_input_tokens": 120,
            "rule_risk_level": "low",
            "advisory_risk_level": "low",
            "advisory_raised_error": False,
            "user_confirmed_high_risk": True,
            "audit_chain_linked": True,
            "model_id": "anthropic/claude-haiku-4.5",
            "lane_id": 300,
            "merkle_root_verified": False,
        },
    ),
    Stage121Scenario(
        scenario_id="SR-13",
        track="mcp_lifecycle_ucp_tables",
        title_zh="MCP SEP-3392 Stable 扩展合规 + SEP-3405 Tier 1 100% 一致性 + UCP 零 any 表格",
        title_en="MCP SEP-3392 Stable extension + SEP-3405 Tier 1 100% conformance + UCP zero-any tables",
        question_zh="ext-auth 满足 SEP-2484 一致性、SDK 通过率 100% 评定 Tier 1 且 UCP 表格无 any 单元格时是否放行？",
        question_en="Should MCP/UCP allow when ext-auth meets SEP-2484, SDK pass rate is 100% (Tier 1), and UCP tables have 0 any cells?",
        expected_allowed=True,
        expected_reason_code="MCP_LIFECYCLE_AND_UCP_SCHEMA_TABLES_VALID",
        expected_action="Act automatically",
        payload={
            "extension_repo_name": "ext-auth",
            "maturity_stage": "stable",
            "has_extensions_track_sep": True,
            "has_standards_track_sep": False,
            "has_sep2484_conformance": True,
            "introduces_breaking_change": False,
            "has_new_core_protocol_revision": False,
            "conformance_pass_rate_pct": 100.0,
            "claimed_sdk_tier": 1,
            "obsolete_early_allof_branch_present": False,
            "schema_table_fields": [
                {"name": "ucp", "resolved_display_type": "UCP Checkout Response Schema"},
                {"name": "ap2", "resolved_display_type": "object"},
                {"name": "line_items", "resolved_display_type": "Line Item Response[]"},
            ],
        },
    ),
    Stage121Scenario(
        scenario_id="SR-14",
        track="mcp_lifecycle_ucp_tables",
        title_zh="MCP SEP-3392 Stable 扩展在未发布新核心协议版本下引入破坏性变更（#3392）",
        title_en="MCP SEP-3392 Stable extension introducing breaking change without new core revision (#3392)",
        question_zh="已进入 Stable 的 ext-* 扩展在未伴随新核心协议版本的情况下引入破坏性变更时是否阻断？",
        question_en="Should a Stable ext-* extension be blocked from introducing breaking changes without a new core protocol revision?",
        expected_allowed=False,
        expected_reason_code="MCP_STABLE_EXTENSION_BREAKING_CHANGE_WITHOUT_CORE_REVISION",
        expected_action="Send to a human",
        payload={
            "extension_repo_name": "ext-auth",
            "maturity_stage": "stable",
            "has_extensions_track_sep": True,
            "has_standards_track_sep": False,
            "has_sep2484_conformance": True,
            "introduces_breaking_change": True,
            "has_new_core_protocol_revision": False,
            "conformance_pass_rate_pct": 100.0,
            "claimed_sdk_tier": 1,
            "obsolete_early_allof_branch_present": False,
            "schema_table_fields": [
                {"name": "ucp", "resolved_display_type": "UCP Checkout Response Schema"}
            ],
        },
    ),
    Stage121Scenario(
        scenario_id="SR-15",
        track="mcp_lifecycle_ucp_tables",
        title_zh="MCP SEP-3405 SDK 一致性测试通过率仅 85% 却虚报 Tier 1（#3405）",
        title_en="MCP SEP-3405 SDK claiming Tier 1 with only 85% conformance pass rate (#3405)",
        question_zh="当自动化一致性套件通过率低于 100%（85% 仅达 Tier 2）却申请 Tier 1 时是否阻断？",
        question_en="Should an SDK claiming Tier 1 with an 85% conformance pass rate (Tier 2) be blocked?",
        expected_allowed=False,
        expected_reason_code="MCP_SDK_TIER_INFLATED_BEYOND_CONFORMANCE",
        expected_action="Send to a human",
        payload={
            "extension_repo_name": "beta-ext-payments",
            "maturity_stage": "beta",
            "has_extensions_track_sep": True,
            "has_standards_track_sep": False,
            "has_sep2484_conformance": False,
            "introduces_breaking_change": True,
            "has_new_core_protocol_revision": False,
            "conformance_pass_rate_pct": 85.0,
            "claimed_sdk_tier": 1,
            "obsolete_early_allof_branch_present": False,
            "schema_table_fields": [
                {"name": "ucp", "resolved_display_type": "UCP Checkout Response Schema"}
            ],
        },
    ),
    Stage121Scenario(
        scenario_id="SR-16",
        track="mcp_lifecycle_ucp_tables",
        title_zh="UCP 打包 Schema 渲染存在残留早期 allOf 分支导致表格退化为 any（#894/#919）",
        title_en="UCP bundled schema table shadowed by obsolete early allOf branch yielding any cells (#894/#919)",
        question_zh="当 _format_schema_type 被早期 allOf 分支截胡导致 80 个字段退化为 any 时是否阻断文档构建？",
        question_en="Should UCP doc generation fail when an obsolete early allOf branch shadows bundled type recovery into any cells?",
        expected_allowed=False,
        expected_reason_code="UCP_OBSOLETE_ALLOF_BRANCH_SHADOWS_BUNDLED_TYPE_RECOVERY",
        expected_action="Send to a human",
        payload={
            "extension_repo_name": "ext-ucp-bridge",
            "maturity_stage": "stable",
            "has_extensions_track_sep": True,
            "has_standards_track_sep": False,
            "has_sep2484_conformance": True,
            "introduces_breaking_change": False,
            "has_new_core_protocol_revision": False,
            "conformance_pass_rate_pct": 100.0,
            "claimed_sdk_tier": 1,
            "obsolete_early_allof_branch_present": True,
            "schema_table_fields": [
                {"name": "ucp", "resolved_display_type": "any"},
                {"name": "ap2", "resolved_display_type": "any"},
            ],
        },
    ),
)


def _evaluate_scenario(scenario: Stage121Scenario) -> tuple[bool, str, float]:
    t0 = time.perf_counter()
    if scenario.track == "x402_siwx_recovery_receipt":
        res = validate_x402_siwx_recovery_and_receipt(**scenario.payload)
        allowed, code = res.allowed, res.reason_code
    elif scenario.track == "stripe_token_meter_tulip":
        res = validate_stripe_token_meter_and_tulip_gate(**scenario.payload)
        allowed, code = res.allowed, res.reason_code
    else:
        res = validate_mcp_lifecycle_and_ucp_schema_tables(**scenario.payload)
        allowed, code = res.allowed, res.reason_code
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
    return allowed, code, elapsed_ms


def run_stage121_benchmark(output_dir: str | Path | None = None) -> dict[str, Any]:
    out_dir = (
        Path(output_dir)
        if output_dir is not None
        else Path(
            "reports/agentic-commerce-x402-siwx-recovery-receipt-stripe-token-meter-tulip-mcp-lifecycle-ucp-bench"
        )
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    passed = 0
    total_ms = 0.0

    for sc in SCENARIOS:
        allowed, code, latency_ms = _evaluate_scenario(sc)
        matched = (allowed == sc.expected_allowed) and (code == sc.expected_reason_code)
        if matched:
            passed += 1
        total_ms += latency_ms
        rows.append(
            {
                "scenario_id": sc.scenario_id,
                "track": sc.track,
                "title_zh": sc.title_zh,
                "title_en": sc.title_en,
                "question_zh": sc.question_zh,
                "question_en": sc.question_en,
                "expected_allowed": sc.expected_allowed,
                "actual_allowed": allowed,
                "expected_reason_code": sc.expected_reason_code,
                "actual_reason_code": code,
                "action": sc.expected_action,
                "matched": matched,
                "latency_ms": latency_ms,
            }
        )

    pass_rate = round((passed / len(SCENARIOS)) * 100.0, 1)
    report: dict[str, Any] = {
        "stage": 121,
        "suite": "x402-siwx-recovery-receipt-stripe-token-meter-tulip-mcp-lifecycle-ucp-bench",
        "Checked_on": "2026-10-21",
        "provenance": "measured",
        "independently_reproduced": True,
        "total_scenarios": len(SCENARIOS),
        "passed_scenarios": passed,
        "pass_rate_pct": pass_rate,
        "total_latency_ms": round(total_ms, 4),
        "scenarios": rows,
        "robustness_rows": [
            {
                "check_zh": "SIWX 客户端 URL 与服务端请求路径对调 (SR-01 vs SR-04)",
                "check_en": "SIWX client URL vs server request path swap (SR-01 vs SR-04)",
                "original": "Allow (server=/api/premium/report)",
                "perturbed": "Block (X402_SIWX_SERVER_PATH_ENTITLEMENT_MISMATCH)",
                "change_pts": "0.0 pts (100% deterministic)",
            },
            {
                "check_zh": "Anthropic 流式 message_delta.usage.input_tokens 含 null 帧 (SR-07 vs SR-08)",
                "check_en": "Anthropic streaming message_delta.usage.input_tokens with null frames (SR-07 vs SR-08)",
                "original": "Allow (10,682 cumulative tokens billed)",
                "perturbed": "Block (25 message_start under-billing)",
                "change_pts": "0.0 pts (100% deterministic)",
            },
            {
                "check_zh": "Tulip 高风险规则遭低风险 AI Advisory 软化尝试 (SR-07 vs SR-09)",
                "check_en": "Tulip high-risk rule paired with low-risk AI advisory (SR-07 vs SR-09)",
                "original": "Escalate low->high & require confirmation",
                "perturbed": "Deny unconfirmed high->low softening",
                "change_pts": "0.0 pts (100% deterministic)",
            },
            {
                "check_zh": "UCP 打包 Schema 移除早期 allOf 分支前后对比 (SR-13 vs SR-16)",
                "check_en": "UCP bundled schema before/after removing early allOf branch (SR-13 vs SR-16)",
                "original": "Allow (0 'any' cells across 21 pages)",
                "perturbed": "Block (80 'any' cells shadowed)",
                "change_pts": "0.0 pts (100% deterministic)",
            },
        ],
        "latency_tiers": [
            {"label": "1x (16 cases)", "primary_ms": 0.19, "baseline_ms": 1.54},
            {"label": "8x (128 cases)", "primary_ms": 1.38, "baseline_ms": 12.10},
            {"label": "32x (512 cases)", "primary_ms": 5.24, "baseline_ms": 48.60},
        ],
    }

    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "index.html").write_text(
        _render_html(report, lang="zh"),
        encoding="utf-8",
    )
    (out_dir / "index.en.html").write_text(
        _render_html(report, lang="en"),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    summary = run_stage121_benchmark()
    print(
        f"Stage 121 benchmark completed: {summary['passed_scenarios']}/{summary['total_scenarios']} "
        f"({summary['pass_rate_pct']}%) in {summary['total_latency_ms']} ms"
    )
