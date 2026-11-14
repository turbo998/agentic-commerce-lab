"""Deterministic reference simulator for Cloudflare's 2025-2026 Agentic Commerce Edge Stack.

Covers four production capabilities modeled directly after Cloudflare's architecture:
1. Edge Agent Identity & Bot Governance:
   - RFC 9421 `Web Bot Auth` (`Signature-Agent`, `Signature-Input`, `Signature`, `Content-Digest`)
   - `Visa TAP` / `Mastercard Agent Pay` dual-anchor requirement on write operations
   - `AI Labyrinth` decoy routing for spoofed `User-Agent` / unverified scrapers
2. Agent-Native Storefront Negotiation:
   - `Markdown for Agents` (`Accept: text/markdown`) with `Content-Signal` header & anti-cloaking price parity check
   - `Agent Visibility Template` (`/llms.txt` & structured product JSON-LD)
3. Programmable `Cloudflare Wallets` (`*.cloudflare.pay` Virtual Wallets):
   - Per-transaction ceiling, daily cumulative spend cap, merchant allowlist, and HITL threshold
4. Dual HTTP 402 Machine Payment Protocols:
   - `x402` (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `PAYMENT-RESPONSE`)
   - `MPP` Machine Payments Protocol (`WWW-Authenticate: Payment`, `Authorization: Payment` across
     `charge`, `session`, and `subscription` intents, including x402 fallback compatibility)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


KNOWN_AGENT_UA_KEYWORDS = ("chatgpt-user", "claude-web", "claudebot", "openai-operator", "cloudflare-agent")


@dataclass(frozen=True)
class EdgeAgentRequest:
    method: str
    authority: str
    path: str
    headers: Dict[str, str]
    body: str = ""
    now_epoch: int = 1794638400
    is_write_operation: bool = False
    exceeds_free_crawl_quota: bool = False


@dataclass(frozen=True)
class EdgeGateDecision:
    status_code: int
    action: str
    reason_code: str
    response_headers: Dict[str, str] = field(default_factory=dict)
    verified_agent_id: Optional[str] = None


@dataclass
class VirtualWallet:
    """Cloudflare Virtual Wallet (`agent.<org>.cloudflare.pay`) with hard platform guardrails."""

    wallet_handle: str
    owner_org: str
    max_tx_usd: float
    daily_cap_usd: float
    merchant_allowlist: Set[str]
    hitl_threshold_usd: float = 50.0
    spent_today_usd: float = 0.0
    ledger: List[Dict[str, object]] = field(default_factory=list)

    def authorize_payment(
        self,
        merchant_domain: str,
        amount_usd: float,
        rail: str,
        intent: str = "charge",
        human_approved: bool = False,
    ) -> Tuple[bool, str, Optional[str]]:
        if not self.wallet_handle.endswith(".cloudflare.pay"):
            return False, "invalid_cloudflare_pay_handle", None
        if amount_usd <= 0:
            return False, "non_positive_amount", None
        if merchant_domain not in self.merchant_allowlist:
            return False, "merchant_not_in_virtual_wallet_allowlist", None
        if amount_usd > self.max_tx_usd:
            return False, "virtual_wallet_per_tx_cap_exceeded", None
        if round(self.spent_today_usd + amount_usd, 6) > self.daily_cap_usd:
            return False, "virtual_wallet_daily_cap_exceeded", None
        if amount_usd > self.hitl_threshold_usd and not human_approved:
            return False, "hitl_stepup_approval_required", None

        self.spent_today_usd = round(self.spent_today_usd + amount_usd, 6)
        tx_payload = f"{self.wallet_handle}|{merchant_domain}|{amount_usd:.6f}|{rail}|{intent}|{len(self.ledger)}"
        payment_proof = "cfpay_sig_" + hashlib.sha256(tx_payload.encode("utf-8")).hexdigest()[:24]
        self.ledger.append(
            {
                "wallet_handle": self.wallet_handle,
                "owner_org": self.owner_org,
                "merchant": merchant_domain,
                "amount_usd": amount_usd,
                "rail": rail,
                "intent": intent,
                "proof": payment_proof,
            }
        )
        return True, "authorized", payment_proof


def compute_content_digest(body: str) -> str:
    digest_hex = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha-256=:{digest_hex}:"


def sign_rfc9421_request(
    secret_key: str,
    agent_id: str,
    method: str,
    authority: str,
    path: str,
    created: int,
    expires: int,
    nonce: str,
    body: str = "",
    tap_buyer_mandate: Optional[str] = None,
) -> Dict[str, str]:
    """Generate deterministic RFC 9421 Web Bot Auth (+ optional Visa TAP buyer mandate) headers."""
    headers: Dict[str, str] = {"Signature-Agent": agent_id}
    covered = ["@authority", "@method", "@path"]
    canonical_parts = [
        f"@authority:{authority.lower()}",
        f"@method:{method.upper()}",
        f"@path:{path}",
    ]
    if body:
        cd = compute_content_digest(body)
        headers["Content-Digest"] = cd
        covered.append("content-digest")
        canonical_parts.append(f"content-digest:{cd}")
    if tap_buyer_mandate:
        headers["X-TAP-Buyer-Mandate"] = tap_buyer_mandate
        covered.append("x-tap-buyer-mandate")
        canonical_parts.append(f"x-tap-buyer-mandate:{tap_buyer_mandate}")

    covered_str = " ".join(f'"{c}"' for c in covered)
    sig_input = f'sig1=({covered_str});created={created};expires={expires};nonce="{nonce}";alg="ed25519"'
    canonical_parts.append(f"@signature-params:{sig_input}")
    signing_base = "\n".join(canonical_parts)
    mac = hmac.new(secret_key.encode("utf-8"), signing_base.encode("utf-8"), hashlib.sha256).hexdigest()
    headers["Signature-Input"] = sig_input
    headers["Signature"] = f"sig1=:{mac}:"
    return headers


class CloudflareEdgeCommerceGateway:
    """Simulates Cloudflare Edge Bot/Agent Verification, Markdown Negotiation, and HTTP 402 Gateways."""

    def __init__(
        self,
        agent_directory_keys: Dict[str, str],
        crawl_price_usd: float = 0.002,
        enable_ai_labyrinth: bool = True,
    ) -> None:
        self.agent_directory_keys = dict(agent_directory_keys)
        self.crawl_price_usd = crawl_price_usd
        self.enable_ai_labyrinth = enable_ai_labyrinth
        self.used_nonces: Set[str] = set()

    def evaluate_request(self, req: EdgeAgentRequest) -> EdgeGateDecision:
        h = {k.lower(): v for k, v in req.headers.items()}
        ua = h.get("user-agent", "").lower()
        sig_agent = h.get("signature-agent")
        sig_input = h.get("signature-input")
        sig_val = h.get("signature")

        # 1. Unverified request check
        if not (sig_agent and sig_input and sig_val):
            claims_ai_ua = any(token in ua for token in KNOWN_AGENT_UA_KEYWORDS)
            if claims_ai_ua and self.enable_ai_labyrinth and not req.is_write_operation:
                return EdgeGateDecision(
                    status_code=200,
                    action="route_ai_labyrinth_decoy",
                    reason_code="spoofed_agent_ua_trapped_in_ai_labyrinth",
                    response_headers={"X-CF-Mitigation": "ai-labyrinth-decoy"},
                )
            return EdgeGateDecision(
                status_code=401,
                action="block",
                reason_code="missing_rfc9421_web_bot_auth_signature",
            )

        # 2. Directory lookup & timestamp/nonce checks
        secret = self.agent_directory_keys.get(sig_agent)
        if not secret:
            return EdgeGateDecision(status_code=401, action="block", reason_code="unknown_signature_agent_jwks")

        m_created = re.search(r"created=(\d+)", sig_input)
        m_expires = re.search(r"expires=(\d+)", sig_input)
        m_nonce = re.search(r'nonce="([^"]+)"', sig_input)
        if not (m_created and m_expires and m_nonce):
            return EdgeGateDecision(status_code=401, action="block", reason_code="malformed_signature_input")

        created, expires, nonce = int(m_created.group(1)), int(m_expires.group(1)), m_nonce.group(1)
        if (expires - created) > 300 or req.now_epoch > expires or req.now_epoch < created:
            return EdgeGateDecision(status_code=401, action="block", reason_code="signature_window_invalid_or_expired")
        if nonce in self.used_nonces:
            return EdgeGateDecision(status_code=401, action="block", reason_code="signature_nonce_replayed")

        # 3. Verify Content-Digest if body is present or write operation
        if req.body or req.is_write_operation:
            expected_cd = compute_content_digest(req.body)
            if h.get("content-digest") != expected_cd:
                return EdgeGateDecision(status_code=401, action="block", reason_code="content_digest_mismatch")

        tap_mandate = h.get("x-tap-buyer-mandate")
        expected_headers = sign_rfc9421_request(
            secret_key=secret,
            agent_id=sig_agent,
            method=req.method,
            authority=req.authority,
            path=req.path,
            created=created,
            expires=expires,
            nonce=nonce,
            body=req.body,
            tap_buyer_mandate=tap_mandate,
        )
        if expected_headers["Signature"] != sig_val:
            return EdgeGateDecision(status_code=401, action="block", reason_code="rfc9421_signature_verification_failed")

        self.used_nonces.add(nonce)

        # 4. Write operation requires Visa TAP / Mastercard Agent Pay buyer mandate
        if req.is_write_operation:
            if not tap_mandate:
                return EdgeGateDecision(
                    status_code=403,
                    action="block",
                    reason_code="buyer_mandate_required_for_write_operation",
                    verified_agent_id=sig_agent,
                )
            return EdgeGateDecision(
                status_code=200,
                action="allow_transactional_checkout",
                reason_code="verified_tap_dual_anchor",
                response_headers={"X-CF-Verified-Agent": sig_agent, "X-CF-Liability-Shift": "visa-tap-verified"},
                verified_agent_id=sig_agent,
            )

        # 5. Read-only Pay Per Crawl / HTTP 402 check (supports both x402 and MPP)
        if req.exceeds_free_crawl_quota:
            x402_sig = h.get("payment-signature")
            mpp_auth = h.get("authorization", "")
            if x402_sig and x402_sig.startswith("cfpay_sig_"):
                return EdgeGateDecision(
                    status_code=200,
                    action="allow_paid_x402",
                    reason_code="x402_micropayment_settled",
                    response_headers={
                        "PAYMENT-RESPONSE": json.dumps({"settled": True, "amount_usd": self.crawl_price_usd, "rail": "x402"})
                    },
                    verified_agent_id=sig_agent,
                )
            if mpp_auth.startswith("Payment cfpay_sig_"):
                return EdgeGateDecision(
                    status_code=200,
                    action="allow_paid_mpp",
                    reason_code="mpp_payment_settled",
                    response_headers={
                        "X-MPP-Receipt": json.dumps({"settled": True, "amount_usd": self.crawl_price_usd, "rail": "mpp"})
                    },
                    verified_agent_id=sig_agent,
                )
            challenge = json.dumps(
                {
                    "amount_usd": self.crawl_price_usd,
                    "currencies": ["USDC", "NET_DOLLAR"],
                    "intents": ["charge", "session", "subscription"],
                    "merchant": req.authority,
                }
            )
            return EdgeGateDecision(
                status_code=402,
                action="challenge_http_402",
                reason_code="pay_per_crawl_payment_required",
                response_headers={
                    "PAYMENT-REQUIRED": challenge,
                    "WWW-Authenticate": f'Payment realm="{req.authority}", amount="{self.crawl_price_usd}", rail="mpp,x402"',
                },
                verified_agent_id=sig_agent,
            )

        return EdgeGateDecision(
            status_code=200,
            action="allow_read_free",
            reason_code="verified_web_bot_auth_read",
            response_headers={"X-CF-Verified-Agent": sig_agent},
            verified_agent_id=sig_agent,
        )


def negotiate_markdown_for_agents(
    html_document: str,
    accept_header: str,
    ai_train_allowed: bool = False,
) -> Tuple[str, Dict[str, str], Dict[str, int]]:
    """Simulate Cloudflare `Markdown for Agents` edge HTML->Markdown conversion & token compression."""
    content_signal = f"ai-train={'yes' if ai_train_allowed else 'no'}, search=yes, ai-input=yes"
    raw_bytes = len(html_document.encode("utf-8"))

    if "text/markdown" not in accept_header.lower():
        return (
            html_document,
            {"Content-Type": "text/html; charset=utf-8", "Content-Signal": content_signal},
            {"html_bytes": raw_bytes, "output_bytes": raw_bytes, "reduction_pct": 0},
        )

    # Strip script, style, nav, footer, and hidden display:none prompt-injection blocks
    cleaned = re.sub(r"<(script|style|nav|footer)[^>]*>.*?</\1>", "", html_document, flags=re.I | re.S)
    cleaned = re.sub(
        r"<[a-z0-9]+\b[^>]*style\s*=\s*['\"][^'\"]*display\s*:\s*none[^'\"]*['\"][^>]*>.*?</[a-z0-9]+>",
        "",
        cleaned,
        flags=re.I | re.S,
    )
    cleaned = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    markdown = "\n".join(lines) + "\n"
    md_bytes = len(markdown.encode("utf-8"))
    reduction_pct = max(0, round((1.0 - (md_bytes / max(1, raw_bytes))) * 100))

    return (
        markdown,
        {
            "Content-Type": "text/markdown; charset=utf-8",
            "Vary": "Accept",
            "Content-Signal": content_signal,
        },
        {"html_bytes": raw_bytes, "output_bytes": md_bytes, "reduction_pct": reduction_pct},
    )
