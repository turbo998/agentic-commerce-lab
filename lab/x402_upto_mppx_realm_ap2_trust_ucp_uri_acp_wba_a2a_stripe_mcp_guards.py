"""Stage 288 deterministic guard suite across 54 upstream repositories and 448 zero-overlap PRs.

Covers PR-01..PR-16 (28 primary-source PRs per group = 448 zero-overlap PRs):
- PR-01: x402-rs V2 EIP-155 upto Permit2 & decimal authorization.value + a2a-x402 payment binding
- PR-02: wevm/mppx session-close isolation, 15s-60s validBefore & cross-realm proof rejection + Tempo AA nonce receipts
- PR-03: AP2 Trust Query / Settlement / PSD2 Refund / Compliance Receipt envelopes + CAIP-373 & ERC-2108/2107/2104
- PR-04: UCP JS SDK discovery/warning URI & version constraints, unit price number preservation & collapsed union fields
- PR-05: ACP 11 session states, intervention_required, MCP checkout binding & Cloudflare WBA RFC 9421 future-created block
- PR-06: A2A published schema fallback, Inspector DOMPurify 3.4.13 sanitization & ADK MCP 1.30.0 / aiohttp 3.14.4 floor
- PR-07: a2a-python v0.3 JSON-RPC error codes, executor failure recording & per-client httpx + a2a-js gRPC streaming gate
- PR-08: a2a-java blank push config ID rejection & payload masking + a2a-dotnet event-stream enforcement & extension registry
- PR-09: Stripe AI tulip run_tool() admission gate, Agent Toolkit local skills carve-out removal & CLI sandbox boundary
- PR-10: Stripe 9-Language SDK extra headers, API v2 Search, PMME currencies & WeChat Pay mobile_web validation
- PR-11: Coinbase AgentKit pre-spend provider selection & Fodda x402 + CDP SDK Python JWT iat/aud & custodial no-wallet-auth
- PR-12: Sierra tau2-bench banking task sync, lowercase airline user_id, telecom grounding, NL-judge cost & model path sanitization
- PR-13: MCP SEP-646/990 Enterprise Auth, SEP-1046/1502 Client Credentials, mcpdo load thresholds & fetch host verification
- PR-14: MCP TS sampling.context gate & invalidated cache discard + Python non-UTF-8 URI template reject & RFC 8707 resource
- PR-15: MCP Go SSE stream detach & oauthex parent-path resource + Rust nested x-mcp-header & DCR auth method selection
- PR-16: MCP Swift MCPError.paymentRequired (MPP), Kotlin MCP-Protocol-Version, PHP unanswered fail-fast & Ruby listen bounds
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STAGE288_PR_GROUPS: dict[str, list[str]] = {
    "PR-01": [
        "coinbase/x402#422",
        "x402-rs/x402-rs#70",
        "google-agentic-commerce/a2a-x402#114",
        "coinbase/x402#421",
        "x402-rs/x402-rs#69",
        "google-agentic-commerce/a2a-x402#113",
        "coinbase/x402#418",
        "x402-rs/x402-rs#68",
        "google-agentic-commerce/a2a-x402#112",
        "coinbase/x402#417",
        "x402-rs/x402-rs#67",
        "google-agentic-commerce/a2a-x402#111",
        "coinbase/x402#416",
        "x402-rs/x402-rs#64",
        "google-agentic-commerce/a2a-x402#110",
        "coinbase/x402#415",
        "x402-rs/x402-rs#63",
        "google-agentic-commerce/a2a-x402#109",
        "coinbase/x402#411",
        "x402-rs/x402-rs#62",
        "google-agentic-commerce/a2a-x402#108",
        "coinbase/x402#409",
        "x402-rs/x402-rs#61",
        "google-agentic-commerce/a2a-x402#107",
        "coinbase/x402#407",
        "x402-rs/x402-rs#60",
        "google-agentic-commerce/a2a-x402#106",
        "coinbase/x402#406"
    ],
    "PR-02": [
        "wevm/mppx#1101",
        "tempoxyz/tempo#8663",
        "wevm/mppx#1100",
        "tempoxyz/tempo#8662",
        "wevm/mppx#1099",
        "tempoxyz/tempo#8661",
        "wevm/mppx#1098",
        "tempoxyz/tempo#8660",
        "wevm/mppx#1097",
        "tempoxyz/tempo#8659",
        "wevm/mppx#1096",
        "tempoxyz/tempo#8658",
        "wevm/mppx#1095",
        "tempoxyz/tempo#8657",
        "wevm/mppx#1094",
        "tempoxyz/tempo#8656",
        "wevm/mppx#1087",
        "tempoxyz/tempo#8655",
        "wevm/mppx#1086",
        "tempoxyz/tempo#8654",
        "wevm/mppx#1085",
        "tempoxyz/tempo#8653",
        "wevm/mppx#1084",
        "tempoxyz/tempo#8652",
        "wevm/mppx#1083",
        "tempoxyz/tempo#8649",
        "wevm/mppx#1082",
        "tempoxyz/tempo#8648"
    ],
    "PR-03": [
        "google-agentic-commerce/AP2#272",
        "openwallet-foundation/sd-jwt-js#363",
        "ChainAgnostic/CAIPs#374",
        "ethereum/ERCs#2108",
        "google-agentic-commerce/AP2#271",
        "openwallet-foundation/sd-jwt-js#362",
        "ChainAgnostic/CAIPs#373",
        "ethereum/ERCs#2107",
        "google-agentic-commerce/AP2#270",
        "openwallet-foundation/sd-jwt-js#361",
        "ChainAgnostic/CAIPs#372",
        "ethereum/ERCs#2106",
        "google-agentic-commerce/AP2#269",
        "openwallet-foundation/sd-jwt-js#359",
        "ChainAgnostic/CAIPs#371",
        "ethereum/ERCs#2105",
        "google-agentic-commerce/AP2#267",
        "openwallet-foundation/sd-jwt-js#358",
        "ChainAgnostic/CAIPs#370",
        "ethereum/ERCs#2104",
        "google-agentic-commerce/AP2#261",
        "openwallet-foundation/sd-jwt-js#357",
        "ChainAgnostic/CAIPs#369",
        "ethereum/ERCs#2103",
        "google-agentic-commerce/AP2#260",
        "openwallet-foundation/sd-jwt-js#356",
        "ChainAgnostic/CAIPs#368",
        "ethereum/ERCs#2102"
    ],
    "PR-04": [
        "Universal-Commerce-Protocol/ucp#990",
        "Universal-Commerce-Protocol/js-sdk#59",
        "Universal-Commerce-Protocol/python-sdk#40",
        "Universal-Commerce-Protocol/samples#219",
        "Universal-Commerce-Protocol/ucp#978",
        "Universal-Commerce-Protocol/js-sdk#58",
        "Universal-Commerce-Protocol/python-sdk#39",
        "Universal-Commerce-Protocol/samples#217",
        "Universal-Commerce-Protocol/ucp#968",
        "Universal-Commerce-Protocol/js-sdk#57",
        "Universal-Commerce-Protocol/python-sdk#38",
        "Universal-Commerce-Protocol/samples#216",
        "Universal-Commerce-Protocol/ucp#962",
        "Universal-Commerce-Protocol/js-sdk#56",
        "Universal-Commerce-Protocol/python-sdk#35",
        "Universal-Commerce-Protocol/samples#215",
        "Universal-Commerce-Protocol/ucp#950",
        "Universal-Commerce-Protocol/js-sdk#55",
        "Universal-Commerce-Protocol/python-sdk#33",
        "Universal-Commerce-Protocol/samples#213",
        "Universal-Commerce-Protocol/ucp#942",
        "Universal-Commerce-Protocol/js-sdk#54",
        "Universal-Commerce-Protocol/python-sdk#32",
        "Universal-Commerce-Protocol/samples#212",
        "Universal-Commerce-Protocol/ucp#941",
        "Universal-Commerce-Protocol/js-sdk#52",
        "Universal-Commerce-Protocol/python-sdk#29",
        "Universal-Commerce-Protocol/samples#211"
    ],
    "PR-05": [
        "agentic-commerce-protocol/agentic-commerce-protocol#150",
        "cloudflare/web-bot-auth#135",
        "agentic-commerce-protocol/agentic-commerce-protocol#149",
        "cloudflare/web-bot-auth#134",
        "agentic-commerce-protocol/agentic-commerce-protocol#144",
        "cloudflare/web-bot-auth#133",
        "agentic-commerce-protocol/agentic-commerce-protocol#143",
        "cloudflare/web-bot-auth#132",
        "agentic-commerce-protocol/agentic-commerce-protocol#140",
        "cloudflare/web-bot-auth#131",
        "agentic-commerce-protocol/agentic-commerce-protocol#139",
        "cloudflare/web-bot-auth#130",
        "agentic-commerce-protocol/agentic-commerce-protocol#138",
        "cloudflare/web-bot-auth#129",
        "agentic-commerce-protocol/agentic-commerce-protocol#137",
        "cloudflare/web-bot-auth#128",
        "agentic-commerce-protocol/agentic-commerce-protocol#133",
        "cloudflare/web-bot-auth#127",
        "agentic-commerce-protocol/agentic-commerce-protocol#132",
        "cloudflare/web-bot-auth#125",
        "agentic-commerce-protocol/agentic-commerce-protocol#131",
        "cloudflare/web-bot-auth#124",
        "agentic-commerce-protocol/agentic-commerce-protocol#130",
        "cloudflare/web-bot-auth#123",
        "agentic-commerce-protocol/agentic-commerce-protocol#129",
        "cloudflare/web-bot-auth#122",
        "agentic-commerce-protocol/agentic-commerce-protocol#128",
        "cloudflare/web-bot-auth#121"
    ],
    "PR-06": [
        "a2aproject/A2A#2382",
        "a2aproject/a2a-inspector#191",
        "a2aproject/a2a-samples#733",
        "a2aproject/A2A#2379",
        "a2aproject/a2a-inspector#190",
        "a2aproject/a2a-samples#732",
        "a2aproject/A2A#2373",
        "a2aproject/a2a-inspector#189",
        "a2aproject/a2a-samples#731",
        "a2aproject/A2A#2368",
        "a2aproject/a2a-inspector#188",
        "a2aproject/a2a-samples#730",
        "a2aproject/A2A#2347",
        "a2aproject/a2a-inspector#187",
        "a2aproject/a2a-samples#729",
        "a2aproject/A2A#2345",
        "a2aproject/a2a-inspector#186",
        "a2aproject/a2a-samples#728",
        "a2aproject/A2A#2343",
        "a2aproject/a2a-inspector#185",
        "a2aproject/a2a-samples#727",
        "a2aproject/A2A#2340",
        "a2aproject/a2a-inspector#184",
        "a2aproject/a2a-samples#726",
        "a2aproject/A2A#2338",
        "a2aproject/a2a-inspector#183",
        "a2aproject/a2a-samples#725",
        "a2aproject/A2A#2328"
    ],
    "PR-07": [
        "a2aproject/a2a-python#1373",
        "a2aproject/a2a-js#750",
        "a2aproject/a2a-python#1370",
        "a2aproject/a2a-js#746",
        "a2aproject/a2a-python#1369",
        "a2aproject/a2a-js#742",
        "a2aproject/a2a-python#1367",
        "a2aproject/a2a-js#741",
        "a2aproject/a2a-python#1366",
        "a2aproject/a2a-js#740",
        "a2aproject/a2a-python#1362",
        "a2aproject/a2a-js#738",
        "a2aproject/a2a-python#1360",
        "a2aproject/a2a-js#737",
        "a2aproject/a2a-python#1359",
        "a2aproject/a2a-js#736",
        "a2aproject/a2a-python#1358",
        "a2aproject/a2a-js#733",
        "a2aproject/a2a-python#1357",
        "a2aproject/a2a-js#732",
        "a2aproject/a2a-python#1353",
        "a2aproject/a2a-js#731",
        "a2aproject/a2a-python#1352",
        "a2aproject/a2a-js#730",
        "a2aproject/a2a-python#1337",
        "a2aproject/a2a-js#729",
        "a2aproject/a2a-python#1334",
        "a2aproject/a2a-js#728"
    ],
    "PR-08": [
        "a2aproject/a2a-go#427",
        "a2aproject/a2a-dotnet#553",
        "a2aproject/a2a-java#1242",
        "a2aproject/a2a-go#425",
        "a2aproject/a2a-dotnet#552",
        "a2aproject/a2a-java#1241",
        "a2aproject/a2a-go#424",
        "a2aproject/a2a-dotnet#549",
        "a2aproject/a2a-java#1238",
        "a2aproject/a2a-go#423",
        "a2aproject/a2a-dotnet#548",
        "a2aproject/a2a-java#1237",
        "a2aproject/a2a-go#422",
        "a2aproject/a2a-dotnet#546",
        "a2aproject/a2a-java#1236",
        "a2aproject/a2a-go#421",
        "a2aproject/a2a-dotnet#545",
        "a2aproject/a2a-java#1235",
        "a2aproject/a2a-go#419",
        "a2aproject/a2a-dotnet#544",
        "a2aproject/a2a-java#1232",
        "a2aproject/a2a-go#418",
        "a2aproject/a2a-dotnet#543",
        "a2aproject/a2a-java#1231",
        "a2aproject/a2a-go#417",
        "a2aproject/a2a-dotnet#542",
        "a2aproject/a2a-java#1230",
        "a2aproject/a2a-go#416"
    ],
    "PR-09": [
        "stripe/ai#498",
        "stripe/agent-toolkit#472",
        "stripe/stripe-cli#2080",
        "stripe/ai#496",
        "stripe/agent-toolkit#470",
        "stripe/stripe-cli#2079",
        "stripe/ai#495",
        "stripe/agent-toolkit#468",
        "stripe/stripe-cli#2078",
        "stripe/ai#489",
        "stripe/agent-toolkit#467",
        "stripe/stripe-cli#2077",
        "stripe/ai#488",
        "stripe/agent-toolkit#466",
        "stripe/stripe-cli#2076",
        "stripe/ai#487",
        "stripe/agent-toolkit#465",
        "stripe/stripe-cli#2074",
        "stripe/ai#486",
        "stripe/agent-toolkit#463",
        "stripe/stripe-cli#2073",
        "stripe/ai#482",
        "stripe/agent-toolkit#462",
        "stripe/stripe-cli#2072",
        "stripe/ai#480",
        "stripe/agent-toolkit#460",
        "stripe/stripe-cli#2071",
        "stripe/ai#478"
    ],
    "PR-10": [
        "stripe/stripe-python#1933",
        "stripe/stripe-node#2886",
        "stripe/stripe-go#2459",
        "stripe/stripe-ruby#1988",
        "stripe/stripe-java#2308",
        "stripe/stripe-dotnet#3471",
        "stripe/stripe-php#2162",
        "stripe/stripe-js#999",
        "stripe/react-stripe-js#722",
        "stripe/stripe-python#1932",
        "stripe/stripe-node#2884",
        "stripe/stripe-go#2458",
        "stripe/stripe-ruby#1987",
        "stripe/stripe-java#2307",
        "stripe/stripe-dotnet#3470",
        "stripe/stripe-php#2161",
        "stripe/stripe-js#997",
        "stripe/react-stripe-js#721",
        "stripe/stripe-python#1931",
        "stripe/stripe-node#2883",
        "stripe/stripe-go#2456",
        "stripe/stripe-ruby#1986",
        "stripe/stripe-java#2306",
        "stripe/stripe-dotnet#3469",
        "stripe/stripe-php#2160",
        "stripe/stripe-js#995",
        "stripe/react-stripe-js#720",
        "stripe/stripe-python#1930"
    ],
    "PR-11": [
        "coinbase/agentkit#1588",
        "coinbase/cdp-sdk#858",
        "coinbase/agentkit#1570",
        "coinbase/cdp-sdk#814",
        "coinbase/agentkit#1569",
        "coinbase/cdp-sdk#812",
        "coinbase/agentkit#1566",
        "coinbase/cdp-sdk#811",
        "coinbase/agentkit#1561",
        "coinbase/cdp-sdk#810",
        "coinbase/agentkit#1551",
        "coinbase/cdp-sdk#809",
        "coinbase/agentkit#1549",
        "coinbase/cdp-sdk#808",
        "coinbase/agentkit#1541",
        "coinbase/cdp-sdk#807",
        "coinbase/agentkit#1540",
        "coinbase/cdp-sdk#805",
        "coinbase/agentkit#1538",
        "coinbase/cdp-sdk#804",
        "coinbase/agentkit#1537",
        "coinbase/cdp-sdk#803",
        "coinbase/agentkit#1536",
        "coinbase/cdp-sdk#802",
        "coinbase/agentkit#1529",
        "coinbase/cdp-sdk#801",
        "coinbase/agentkit#1528",
        "coinbase/cdp-sdk#800"
    ],
    "PR-12": [
        "sierra-research/tau2-bench#606",
        "sierra-research/tau-bench#72",
        "sierra-research/tau2-bench#605",
        "sierra-research/tau-bench#69",
        "sierra-research/tau2-bench#604",
        "sierra-research/tau-bench#68",
        "sierra-research/tau2-bench#603",
        "sierra-research/tau-bench#67",
        "sierra-research/tau2-bench#602",
        "sierra-research/tau-bench#64",
        "sierra-research/tau2-bench#601",
        "sierra-research/tau-bench#62",
        "sierra-research/tau2-bench#600",
        "sierra-research/tau-bench#60",
        "sierra-research/tau2-bench#598",
        "sierra-research/tau-bench#59",
        "sierra-research/tau2-bench#597",
        "sierra-research/tau-bench#55",
        "sierra-research/tau2-bench#596",
        "sierra-research/tau-bench#54",
        "sierra-research/tau2-bench#595",
        "sierra-research/tau-bench#53",
        "sierra-research/tau2-bench#594",
        "sierra-research/tau-bench#52",
        "sierra-research/tau2-bench#593",
        "sierra-research/tau-bench#50",
        "sierra-research/tau2-bench#591",
        "sierra-research/tau-bench#49"
    ],
    "PR-13": [
        "modelcontextprotocol/modelcontextprotocol#3451",
        "modelcontextprotocol/ext-auth#5",
        "modelcontextprotocol/inspector#2807",
        "modelcontextprotocol/registry#1736",
        "modelcontextprotocol/servers#5245",
        "modelcontextprotocol/modelcontextprotocol#3450",
        "modelcontextprotocol/ext-auth#4",
        "modelcontextprotocol/inspector#2806",
        "modelcontextprotocol/registry#1698",
        "modelcontextprotocol/servers#5244",
        "modelcontextprotocol/modelcontextprotocol#3447",
        "modelcontextprotocol/ext-auth#3",
        "modelcontextprotocol/inspector#2803",
        "modelcontextprotocol/registry#1697",
        "modelcontextprotocol/servers#5242",
        "modelcontextprotocol/modelcontextprotocol#3446",
        "modelcontextprotocol/ext-auth#2",
        "modelcontextprotocol/inspector#2799",
        "modelcontextprotocol/registry#1696",
        "modelcontextprotocol/servers#5241",
        "modelcontextprotocol/modelcontextprotocol#3445",
        "modelcontextprotocol/ext-auth#1",
        "modelcontextprotocol/inspector#2798",
        "modelcontextprotocol/registry#1695",
        "modelcontextprotocol/servers#5240",
        "modelcontextprotocol/modelcontextprotocol#3444",
        "modelcontextprotocol/inspector#2791",
        "modelcontextprotocol/registry#1690"
    ],
    "PR-14": [
        "modelcontextprotocol/typescript-sdk#3099",
        "modelcontextprotocol/python-sdk#3752",
        "modelcontextprotocol/typescript-sdk#3089",
        "modelcontextprotocol/python-sdk#3751",
        "modelcontextprotocol/typescript-sdk#3088",
        "modelcontextprotocol/python-sdk#3749",
        "modelcontextprotocol/typescript-sdk#3086",
        "modelcontextprotocol/python-sdk#3748",
        "modelcontextprotocol/typescript-sdk#3085",
        "modelcontextprotocol/python-sdk#3743",
        "modelcontextprotocol/typescript-sdk#3084",
        "modelcontextprotocol/python-sdk#3741",
        "modelcontextprotocol/typescript-sdk#3080",
        "modelcontextprotocol/python-sdk#3740",
        "modelcontextprotocol/typescript-sdk#3073",
        "modelcontextprotocol/python-sdk#3739",
        "modelcontextprotocol/typescript-sdk#3072",
        "modelcontextprotocol/python-sdk#3738",
        "modelcontextprotocol/typescript-sdk#3069",
        "modelcontextprotocol/python-sdk#3731",
        "modelcontextprotocol/typescript-sdk#3068",
        "modelcontextprotocol/python-sdk#3727",
        "modelcontextprotocol/typescript-sdk#3066",
        "modelcontextprotocol/python-sdk#3724",
        "modelcontextprotocol/typescript-sdk#3065",
        "modelcontextprotocol/python-sdk#3722",
        "modelcontextprotocol/typescript-sdk#3064",
        "modelcontextprotocol/python-sdk#3719"
    ],
    "PR-15": [
        "modelcontextprotocol/go-sdk#1452",
        "modelcontextprotocol/rust-sdk#1388",
        "modelcontextprotocol/csharp-sdk#1950",
        "modelcontextprotocol/go-sdk#1446",
        "modelcontextprotocol/rust-sdk#1387",
        "modelcontextprotocol/csharp-sdk#1947",
        "modelcontextprotocol/go-sdk#1433",
        "modelcontextprotocol/rust-sdk#1384",
        "modelcontextprotocol/csharp-sdk#1944",
        "modelcontextprotocol/go-sdk#1415",
        "modelcontextprotocol/rust-sdk#1369",
        "modelcontextprotocol/csharp-sdk#1942",
        "modelcontextprotocol/go-sdk#1409",
        "modelcontextprotocol/rust-sdk#1368",
        "modelcontextprotocol/csharp-sdk#1940",
        "modelcontextprotocol/go-sdk#1403",
        "modelcontextprotocol/rust-sdk#1365",
        "modelcontextprotocol/csharp-sdk#1939",
        "modelcontextprotocol/go-sdk#1395",
        "modelcontextprotocol/rust-sdk#1359",
        "modelcontextprotocol/csharp-sdk#1938",
        "modelcontextprotocol/go-sdk#1386",
        "modelcontextprotocol/rust-sdk#1358",
        "modelcontextprotocol/csharp-sdk#1937",
        "modelcontextprotocol/go-sdk#1385",
        "modelcontextprotocol/rust-sdk#1352",
        "modelcontextprotocol/csharp-sdk#1936",
        "modelcontextprotocol/go-sdk#1384"
    ],
    "PR-16": [
        "modelcontextprotocol/java-sdk#1267",
        "modelcontextprotocol/kotlin-sdk#1099",
        "modelcontextprotocol/swift-sdk#251",
        "modelcontextprotocol/php-sdk#577",
        "modelcontextprotocol/ruby-sdk#588",
        "modelcontextprotocol/java-sdk#1263",
        "modelcontextprotocol/kotlin-sdk#1098",
        "modelcontextprotocol/swift-sdk#250",
        "modelcontextprotocol/php-sdk#575",
        "modelcontextprotocol/ruby-sdk#587",
        "modelcontextprotocol/java-sdk#1262",
        "modelcontextprotocol/kotlin-sdk#1097",
        "modelcontextprotocol/swift-sdk#249",
        "modelcontextprotocol/php-sdk#574",
        "modelcontextprotocol/ruby-sdk#586",
        "modelcontextprotocol/java-sdk#1261",
        "modelcontextprotocol/kotlin-sdk#1096",
        "modelcontextprotocol/swift-sdk#248",
        "modelcontextprotocol/php-sdk#573",
        "modelcontextprotocol/ruby-sdk#584",
        "modelcontextprotocol/java-sdk#1256",
        "modelcontextprotocol/kotlin-sdk#1095",
        "modelcontextprotocol/swift-sdk#229",
        "modelcontextprotocol/php-sdk#571",
        "modelcontextprotocol/ruby-sdk#582",
        "modelcontextprotocol/java-sdk#1255",
        "modelcontextprotocol/kotlin-sdk#1091",
        "modelcontextprotocol/swift-sdk#227"
    ]
}


@dataclass(frozen=True)
class Stage288GuardVerdict:
    scenario_id: str
    pr_group: str
    passed: bool
    decision_code: str
    action: str
    confidence: float
    remediation: str
    covered_prs: tuple[str, ...]


def evaluate_x402_v2_upto_permit2_and_decimal_value_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-01: x402-rs#70 V2 EIP-155 upto Permit2, #63 decimal authorization.value & a2a-x402#107 payment binding."""
    prs = tuple(STAGE288_PR_GROUPS["PR-01"])
    auth_value = str(payload.get("authorization_value", ""))
    scheme = str(payload.get("scheme", "v2-eip155-upto"))
    max_upto_minor = int(payload.get("max_upto_minor", 0))
    settled_minor = int(payload.get("settled_minor", 0))
    payment_task_bound = bool(payload.get("payment_task_bound", False))

    if auth_value.startswith(("0x", "0X")) or not auth_value.isdigit():
        return Stage288GuardVerdict(
            scenario_id="PR-01",
            pr_group="PR-01",
            passed=False,
            decision_code="X402_HEX_AUTHORIZATION_VALUE_BLOCKED",
            action="BLOCK_AND_REQUIRE_DECIMAL_AUTHORIZATION_VALUE",
            confidence=0.99,
            remediation="Serialize authorization.value as a base-10 decimal string instead of hex per x402-rs#63.",
            covered_prs=prs,
        )
    if scheme == "v2-eip155-upto" and (max_upto_minor <= 0 or settled_minor > max_upto_minor):
        return Stage288GuardVerdict(
            scenario_id="PR-01",
            pr_group="PR-01",
            passed=False,
            decision_code="X402_V2_UPTO_PERMIT2_CEILING_EXCEEDED",
            action="BLOCK_OVER_CEILING_UPTO_SETTLEMENT",
            confidence=0.98,
            remediation="Enforce settled_minor <= max_upto_minor under V2 EIP-155 upto Permit2 per x402-rs#70/#60.",
            covered_prs=prs,
        )
    if not payment_task_bound:
        return Stage288GuardVerdict(
            scenario_id="PR-01",
            pr_group="PR-01",
            passed=False,
            decision_code="A2A_X402_UNBOUND_PAYMENT_PROOF_REJECTED",
            action="BLOCK_UNBOUND_A2A_PAYMENT_PROOF",
            confidence=0.98,
            remediation="Bind x402 payment proof to the target A2A task/order context per a2a-x402#107.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-01",
        pr_group="PR-01",
        passed=True,
        decision_code="X402_V2_UPTO_DECIMAL_AND_BINDING_VERIFIED",
        action="ALLOW_BOUND_V2_UPTO_SETTLEMENT",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_mppx_realm_session_and_tempo_aa_nonce_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-02: mppx#1101 session close isolation, #1099 15s-60s validBefore, #1097 cross-realm proof & tempo#8661/#8657."""
    prs = tuple(STAGE288_PR_GROUPS["PR-02"])
    session_close_isolated = bool(payload.get("session_close_isolated", False))
    valid_before_sec = int(payload.get("sponsored_valid_before_sec", 0))
    proof_realm = str(payload.get("proof_realm", ""))
    expected_realm = str(payload.get("expected_realm", ""))
    mined_tx_skipped = bool(payload.get("mined_tx_skipped", False))
    aa_create_from_nonce = bool(payload.get("aa_create_from_nonce", False))

    if not session_close_isolated:
        return Stage288GuardVerdict(
            scenario_id="PR-02",
            pr_group="PR-02",
            passed=False,
            decision_code="MPPX_SESSION_CLOSE_MUTATES_RESOURCE_REQUEST",
            action="ISOLATE_SESSION_CLOSE_FROM_RESOURCE_REQUEST",
            confidence=0.99,
            remediation="Isolate Tempo session close from active resource request state per mppx#1101/#1100.",
            covered_prs=prs,
        )
    if valid_before_sec < 15 or valid_before_sec > 60:
        return Stage288GuardVerdict(
            scenario_id="PR-02",
            pr_group="PR-02",
            passed=False,
            decision_code="MPPX_SPONSORED_VALID_BEFORE_OUT_OF_WINDOW",
            action="ENFORCE_15S_TO_60S_VALID_BEFORE_WINDOW",
            confidence=0.98,
            remediation="Enforce the 15s issuance floor and 60s sponsored validBefore window per mppx#1099.",
            covered_prs=prs,
        )
    if not proof_realm or proof_realm != expected_realm:
        return Stage288GuardVerdict(
            scenario_id="PR-02",
            pr_group="PR-02",
            passed=False,
            decision_code="MPPX_CROSS_REALM_TEMPO_PROOF_REJECTED",
            action="REJECT_CROSS_REALM_TEMPO_PROOF",
            confidence=0.99,
            remediation="Reject Tempo payment proofs issued for a different realm per mppx#1097.",
            covered_prs=prs,
        )
    if not mined_tx_skipped or not aa_create_from_nonce:
        return Stage288GuardVerdict(
            scenario_id="PR-02",
            pr_group="PR-02",
            passed=False,
            decision_code="TEMPO_UNPRUNED_MINED_TX_OR_AA_RECEIPT_DRIFT",
            action="SKIP_MINED_TX_AND_DERIVE_AA_CREATE_FROM_NONCE",
            confidence=0.98,
            remediation="Skip unpruned mined pool txs and derive AA CREATE receipt addresses from account nonces per tempo#8661/#8657.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-02",
        pr_group="PR-02",
        passed=True,
        decision_code="MPPX_REALM_VALID_BEFORE_AND_TEMPO_AA_VERIFIED",
        action="ALLOW_ISOLATED_TEMPO_PAYMENT_FLOW",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_ap2_trust_compliance_and_erc_credit_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-03: AP2#272/#271/#270/#269/#267 Trust/Settlement/PSD2/Compliance envelopes, CAIP-373 & ERC-2108/2104."""
    prs = tuple(STAGE288_PR_GROUPS["PR-03"])
    compliance_receipt_bound = bool(payload.get("compliance_receipt_bound", False))
    psd2_refund_envelope_valid = bool(payload.get("psd2_refund_envelope_valid", False))
    pii_sanitized_for_x402 = bool(payload.get("pii_sanitized_for_x402", False))
    caip373_call_ref_valid = bool(payload.get("caip373_call_ref_valid", False))
    repay_first_payee_enforced = bool(payload.get("repay_first_payee_enforced", False))

    if not compliance_receipt_bound or not psd2_refund_envelope_valid:
        return Stage288GuardVerdict(
            scenario_id="PR-03",
            pr_group="PR-03",
            passed=False,
            decision_code="AP2_UNBOUND_COMPLIANCE_OR_PSD2_ENVELOPE",
            action="REQUIRE_MANDATE_BOUND_COMPLIANCE_AND_PSD2_ATTESTATION",
            confidence=0.99,
            remediation="Bind Compliance Receipt and PSD2 Art. 64/89 lifecycle envelopes to Mandate hashes per AP2#272/#271/#270/#269.",
            covered_prs=prs,
        )
    if not pii_sanitized_for_x402:
        return Stage288GuardVerdict(
            scenario_id="PR-03",
            pr_group="PR-03",
            passed=False,
            decision_code="AP2_X402_UNSANITIZED_PII_LEAK_BLOCKED",
            action="SANITIZE_PII_BEFORE_X402_SETTLEMENT",
            confidence=0.99,
            remediation="Strip buyer PII via TrustBoost sanitization before x402 broadcast per AP2#267.",
            covered_prs=prs,
        )
    if not caip373_call_ref_valid or not repay_first_payee_enforced:
        return Stage288GuardVerdict(
            scenario_id="PR-03",
            pr_group="PR-03",
            passed=False,
            decision_code="CAIP373_OR_ERC2108_REPAY_FIRST_VIOLATION",
            action="ENFORCE_CAIP373_REF_AND_AGENT_REPAY_FIRST_WATERFALL",
            confidence=0.98,
            remediation="Validate CAIP-373 contract call reference and ERC-2108/2104 agent repay-first credit rules.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-03",
        pr_group="PR-03",
        passed=True,
        decision_code="AP2_ATTESTATION_ENVELOPES_AND_ERC_CREDIT_VERIFIED",
        action="ALLOW_ATTESTED_MANDATE_EXECUTION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_ucp_uri_version_and_variant_union_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-04: ucp js-sdk#59/#58/#57/#56/#52 URI/version/measure/union constraints & python-sdk#35/#29."""
    prs = tuple(STAGE288_PR_GROUPS["PR-04"])
    discovery_uri_valid = bool(payload.get("discovery_uri_valid", False))
    warning_uri_valid = bool(payload.get("warning_uri_valid", False))
    discovery_version_valid = bool(payload.get("discovery_version_valid", False))
    unit_price_is_number = isinstance(payload.get("unit_price_measure"), (int, float)) and not isinstance(
        payload.get("unit_price_measure"), bool
    )
    variant_required_fields_present = bool(payload.get("variant_required_fields_present", False))

    if not discovery_uri_valid or not warning_uri_valid or not discovery_version_valid:
        return Stage288GuardVerdict(
            scenario_id="PR-04",
            pr_group="PR-04",
            passed=False,
            decision_code="UCP_DISCOVERY_OR_WARNING_URI_VERSION_INVALID",
            action="REJECT_INVALID_UCP_URI_OR_VERSION",
            confidence=0.99,
            remediation="Enforce discovery URI, warning message URI, and version constraints per ucp js-sdk#59/#57/#56.",
            covered_prs=prs,
        )
    if not unit_price_is_number or not variant_required_fields_present:
        return Stage288GuardVerdict(
            scenario_id="PR-04",
            pr_group="PR-04",
            passed=False,
            decision_code="UCP_UNIT_PRICE_TYPE_OR_UNION_VARIANT_INCOMPLETE",
            action="ENFORCE_NUMERIC_MEASURE_AND_VARIANT_REQUIRED_FIELDS",
            confidence=0.98,
            remediation="Preserve numeric unit price measure and enforce per-variant required fields on collapsed unions per js-sdk#58/#52.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-04",
        pr_group="PR-04",
        passed=True,
        decision_code="UCP_URI_VERSION_AND_UNION_VARIANTS_VERIFIED",
        action="ALLOW_UCP_SCHEMA_PROJECTION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_acp_intervention_states_and_wba_future_created_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-05: ACP#150/#144/#143/#139 intervention_required, 11 session states, MCP checkout & WBA#135/#127 future created."""
    prs = tuple(STAGE288_PR_GROUPS["PR-05"])
    valid_states = {
        "created",
        "negotiating",
        "ready_for_payment",
        "intervention_required",
        "authenticating",
        "authorized",
        "capturing",
        "completed",
        "cancelled",
        "expired",
        "failed",
    }
    session_state = str(payload.get("session_state", "")).lower()
    wallet_intervention_handled = bool(payload.get("wallet_intervention_handled", False))
    wba_created_ts = int(payload.get("wba_created_ts", 0))
    now_ts = int(payload.get("now_ts", 0))
    rfc9421_explicit_api = bool(payload.get("rfc9421_explicit_api", False))

    if session_state not in valid_states or not wallet_intervention_handled:
        return Stage288GuardVerdict(
            scenario_id="PR-05",
            pr_group="PR-05",
            passed=False,
            decision_code="ACP_UNKNOWN_SESSION_STATE_OR_UNHANDLED_INTERVENTION",
            action="ENFORCE_11_ACP_SESSION_STATES_AND_INTERVENTION_REQUIRED",
            confidence=0.99,
            remediation="Validate against the 11 canonical ACP session states and handle intervention_required wallet flows per ACP#150/#144/#143.",
            covered_prs=prs,
        )
    if wba_created_ts > now_ts or not rfc9421_explicit_api:
        return Stage288GuardVerdict(
            scenario_id="PR-05",
            pr_group="PR-05",
            passed=False,
            decision_code="WBA_FUTURE_CREATED_TIMESTAMP_FAIL_CLOSED",
            action="REJECT_FUTURE_CREATED_RFC9421_SIGNATURE",
            confidence=0.99,
            remediation="Fail closed when HTTP message signature created timestamp is in the future per web-bot-auth#135/#127.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-05",
        pr_group="PR-05",
        passed=True,
        decision_code="ACP_SESSION_INTERVENTION_AND_WBA_TIMESTAMP_VERIFIED",
        action="ALLOW_ACP_WBA_VERIFIED_SESSION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_a2a_schema_fallback_and_inspector_dompurify_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-06: A2A#2382 published schema fallback, a2a-inspector#188 DOMPurify >=3.4.13 & a2a-samples#727 MCP >=1.30.0."""
    prs = tuple(STAGE288_PR_GROUPS["PR-06"])
    published_schema_fallback = bool(payload.get("published_schema_fallback", False))
    dompurify_sanitized = bool(payload.get("dompurify_3_4_13_sanitized", False))
    sample_mcp_version = tuple(int(x) for x in str(payload.get("sample_mcp_version", "0.0.0")).split(".")[:3])

    if not published_schema_fallback or not dompurify_sanitized:
        return Stage288GuardVerdict(
            scenario_id="PR-06",
            pr_group="PR-06",
            passed=False,
            decision_code="A2A_MISSING_SCHEMA_FALLBACK_OR_UNSANITIZED_DOM",
            action="ENFORCE_PUBLISHED_SCHEMA_FALLBACK_AND_DOMPURIFY_3_4_13",
            confidence=0.99,
            remediation="Provide published schema fallback and sanitize Inspector frontend HTML with DOMPurify >=3.4.13 per A2A#2382 & a2a-inspector#188.",
            covered_prs=prs,
        )
    if sample_mcp_version < (1, 30, 0):
        return Stage288GuardVerdict(
            scenario_id="PR-06",
            pr_group="PR-06",
            passed=False,
            decision_code="A2A_SAMPLE_AGENT_VULNERABLE_MCP_DEPENDENCY",
            action="UPGRADE_A2A_SAMPLE_MCP_TO_1_30_0",
            confidence=0.98,
            remediation="Upgrade ADK and frameworkless sample agents to mcp >= 1.30.0 and aiohttp >= 3.14.4 per a2a-samples#729..#725.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-06",
        pr_group="PR-06",
        passed=True,
        decision_code="A2A_SCHEMA_FALLBACK_AND_INSPECTOR_DOMPURIFY_VERIFIED",
        action="ALLOW_A2A_INSPECTOR_AND_SAMPLE_EXECUTION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_a2a_python_compat_and_js_grpc_streaming_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-07: a2a-python#1369/#1366/#1360/#1358 & a2a-js#741/#740 gRPC streaming capability & REST push taskId."""
    prs = tuple(STAGE288_PR_GROUPS["PR-07"])
    v03_a2a_error_codes = bool(payload.get("v03_a2a_error_codes", False))
    executor_failure_recorded = bool(payload.get("executor_failure_recorded", False))
    isolated_httpx_client = bool(payload.get("isolated_httpx_client", False))
    grpc_streaming_capability_checked = bool(payload.get("grpc_streaming_capability_checked", False))
    rest_push_task_id_from_path = bool(payload.get("rest_push_task_id_from_path", False))

    if not v03_a2a_error_codes or not executor_failure_recorded or not isolated_httpx_client:
        return Stage288GuardVerdict(
            scenario_id="PR-07",
            pr_group="PR-07",
            passed=False,
            decision_code="A2A_PYTHON_COMPAT_OR_EXECUTOR_FAILURE_DROP",
            action="PRESERVE_A2A_ERRORS_RECORD_FAILURES_AND_ISOLATE_HTTPX",
            confidence=0.99,
            remediation="Return canonical A2A error codes in v0.3 adapter, record executor failures in consumer, and isolate httpx clients per a2a-python#1369/#1366/#1358.",
            covered_prs=prs,
        )
    if not grpc_streaming_capability_checked or not rest_push_task_id_from_path:
        return Stage288GuardVerdict(
            scenario_id="PR-07",
            pr_group="PR-07",
            passed=False,
            decision_code="A2A_JS_UNCHECKED_GRPC_STREAMING_OR_PUSH_TASK_ID_DRIFT",
            action="ENFORCE_GRPC_STREAMING_CAPABILITY_AND_PATH_TASK_ID",
            confidence=0.98,
            remediation="Enforce streaming capability on gRPC sendStreamingMessage and bind REST push config taskId from path per a2a-js#741/#740.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-07",
        pr_group="PR-07",
        passed=True,
        decision_code="A2A_PYTHON_AND_JS_RUNTIME_GUARDS_VERIFIED",
        action="ALLOW_A2A_PYTHON_JS_INTEROP",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_a2a_java_push_id_and_dotnet_event_stream_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-08: a2a-java#1242/#1238 blank push config ID & payload masking + a2a-dotnet#552/#548/#546 + a2a-go#425."""
    prs = tuple(STAGE288_PR_GROUPS["PR-08"])
    push_config_id = str(payload.get("push_config_id", "")).strip()
    payload_log_masked = bool(payload.get("payload_log_masked", False))
    streaming_returns_event_stream = bool(payload.get("streaming_returns_event_stream", False))
    registry_extension_negotiated = bool(payload.get("registry_extension_negotiated", False))
    list_tasks_timestamp_aligned = bool(payload.get("list_tasks_timestamp_aligned", False))

    if not push_config_id or not payload_log_masked:
        return Stage288GuardVerdict(
            scenario_id="PR-08",
            pr_group="PR-08",
            passed=False,
            decision_code="A2A_JAVA_BLANK_PUSH_ID_OR_UNMASKED_PAYLOAD_LOG",
            action="REJECT_BLANK_PUSH_ID_AND_MASK_STRUCTURED_LOGS",
            confidence=0.99,
            remediation="Handle blank push notification config IDs and mask sensitive fields in structured logs per a2a-java#1242/#1238.",
            covered_prs=prs,
        )
    if not streaming_returns_event_stream or not registry_extension_negotiated or not list_tasks_timestamp_aligned:
        return Stage288GuardVerdict(
            scenario_id="PR-08",
            pr_group="PR-08",
            passed=False,
            decision_code="A2A_DOTNET_NON_EVENT_STREAM_OR_GO_TIMESTAMP_MISMATCH",
            action="RAISE_ON_NON_EVENT_STREAM_AND_ALIGN_LIST_TASKS_QUERY",
            confidence=0.98,
            remediation="Raise error when streaming call lacks text/event-stream, negotiate extensions via registry, and align ListTasks timestamp per a2a-dotnet#552/#548 & a2a-go#425.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-08",
        pr_group="PR-08",
        passed=True,
        decision_code="A2A_JAVA_DOTNET_GO_GUARDS_VERIFIED",
        action="ALLOW_A2A_ENTERPRISE_STREAM_AND_PUSH",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_stripe_tulip_admission_and_sandbox_boundary_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-09: stripe/ai#482 tulip run_tool() admission gate, agent-toolkit#468 local carve-out removal & stripe-cli#2080/#2072."""
    prs = tuple(STAGE288_PR_GROUPS["PR-09"])
    tulip_admission_passed = bool(payload.get("tulip_admission_passed", False))
    local_skills_carveout_removed = bool(payload.get("local_skills_carveout_removed", False))
    sandbox_context_isolated = bool(payload.get("sandbox_context_isolated", False))
    actions_sha_pinned = bool(payload.get("actions_sha_pinned", False))

    if not tulip_admission_passed or not local_skills_carveout_removed:
        return Stage288GuardVerdict(
            scenario_id="PR-09",
            pr_group="PR-09",
            passed=False,
            decision_code="STRIPE_TULIP_RUN_TOOL_DENIED_OR_LOCAL_CARVEOUT_BYPASS",
            action="ENFORCE_TULIP_RUN_TOOL_GATE_AND_UNIFORM_SKILL_POLICY",
            confidence=0.99,
            remediation="Enforce tulip admission gate on run_tool() across all 4 adapters and remove local skills carve-out per stripe/ai#482 & agent-toolkit#468.",
            covered_prs=prs,
        )
    if not sandbox_context_isolated or not actions_sha_pinned:
        return Stage288GuardVerdict(
            scenario_id="PR-09",
            pr_group="PR-09",
            passed=False,
            decision_code="STRIPE_SANDBOX_CONTEXT_LEAK_OR_UNPINNED_WORKFLOW",
            action="ISOLATE_CLI_SANDBOX_CONTEXT_AND_PIN_ACTION_SHAS",
            confidence=0.98,
            remediation="Harden sandbox context boundary in stripe-cli and pin GitHub Actions to immutable SHAs per stripe-cli#2080/#2072 & stripe/ai#495.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-09",
        pr_group="PR-09",
        passed=True,
        decision_code="STRIPE_TULIP_GATE_AND_SANDBOX_BOUNDARY_VERIFIED",
        action="ALLOW_GATED_STRIPE_TOOL_EXECUTION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_stripe_multi_sdk_extra_headers_and_pmme_currency_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-10: stripe-node#2886/#2884 extra header runtime & v2 Search, stripe-js#999/#997 PMME currency & WeChat mobile_web."""
    prs = tuple(STAGE288_PR_GROUPS["PR-10"])
    extra_headers_allowlisted = bool(payload.get("extra_headers_allowlisted", False))
    v2_search_typed_contract = bool(payload.get("v2_search_typed_contract", False))
    pmme_currency = str(payload.get("pmme_currency", "")).upper()
    supported_pmme_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "SGD", "NZD", "CHF", "SEK", "NOK", "DKK"}
    wechat_mobile_web_validated = bool(payload.get("wechat_mobile_web_validated", False))

    if not extra_headers_allowlisted or not v2_search_typed_contract:
        return Stage288GuardVerdict(
            scenario_id="PR-10",
            pr_group="PR-10",
            passed=False,
            decision_code="STRIPE_SDK_UNSAFE_EXTRA_HEADER_OR_V2_SEARCH_DRIFT",
            action="VALIDATE_GENERATED_EXTRA_HEADERS_AND_V2_SEARCH",
            confidence=0.99,
            remediation="Validate generated extra headers at runtime and enforce API v2 Search contracts per stripe-node#2886/#2884.",
            covered_prs=prs,
        )
    if pmme_currency not in supported_pmme_currencies or not wechat_mobile_web_validated:
        return Stage288GuardVerdict(
            scenario_id="PR-10",
            pr_group="PR-10",
            passed=False,
            decision_code="STRIPE_JS_UNSUPPORTED_PMME_CURRENCY_OR_WECHAT_OPTION",
            action="ENFORCE_PMME_CURRENCY_ALLOWLIST_AND_WECHAT_MOBILE_WEB",
            confidence=0.98,
            remediation="Restrict PMME to supported currencies and validate WeChat Pay mobile_web client options per stripe-js#999/#997.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-10",
        pr_group="PR-10",
        passed=True,
        decision_code="STRIPE_9SDK_HEADERS_V2_SEARCH_AND_PMME_VERIFIED",
        action="ALLOW_STRIPE_SDK_REQUEST",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_agentkit_prespend_selection_and_cdp_jwt_claims_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-11: agentkit#1541/#1538/#1537 pre-spend provider selection + cdp-sdk#808/#807/#805 Python JWT iat/aud & custodial auth."""
    prs = tuple(STAGE288_PR_GROUPS["PR-11"])
    provider_selected_before_x402_spend = bool(payload.get("provider_selected_before_x402_spend", False))
    jwt_has_iat_claim = bool(payload.get("jwt_has_iat_claim", False))
    empty_aud_omitted = bool(payload.get("empty_aud_omitted", False))
    custodial_create_uses_wallet_auth = bool(payload.get("custodial_create_uses_wallet_auth", True))

    if not provider_selected_before_x402_spend:
        return Stage288GuardVerdict(
            scenario_id="PR-11",
            pr_group="PR-11",
            passed=False,
            decision_code="AGENTKIT_UNVETTED_DOWNSTREAM_X402_SPEND",
            action="REQUIRE_PROVIDER_SELECTION_BEFORE_X402_SPEND",
            confidence=0.99,
            remediation="Verify action provider selection and risk policy before downstream x402 spend per agentkit#1561/#1541/#1538.",
            covered_prs=prs,
        )
    if not jwt_has_iat_claim or not empty_aud_omitted or custodial_create_uses_wallet_auth:
        return Stage288GuardVerdict(
            scenario_id="PR-11",
            pr_group="PR-11",
            passed=False,
            decision_code="CDP_SDK_JWT_CLAIM_OR_CUSTODIAL_WALLET_AUTH_MISUSE",
            action="ENFORCE_CDP_JWT_IAT_OMIT_EMPTY_AUD_AND_SKIP_CUSTODIAL_WALLET_AUTH",
            confidence=0.99,
            remediation="Include iat claim, omit unset aud claim in Python JWTs, and avoid wallet auth on custodial account creation per cdp-sdk#808/#807/#805.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-11",
        pr_group="PR-11",
        passed=True,
        decision_code="AGENTKIT_PRESPEND_AND_CDP_JWT_CLAIMS_VERIFIED",
        action="ALLOW_AGENTKIT_CDP_OPERATION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_tau2_banking_sync_and_model_path_sanitization_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-12: tau2-bench#606/#602/#600/#596/#593 banking sync, lowercase airline user_id, NL-judge cost & tau-bench#72."""
    prs = tuple(STAGE288_PR_GROUPS["PR-12"])
    banking_tasks_synced = bool(payload.get("banking_tasks_synced", False))
    airline_user_id = str(payload.get("airline_user_id", ""))
    nl_judge_cost_separated = bool(payload.get("nl_judge_cost_separated", False))
    checkpoint_filename = str(payload.get("checkpoint_filename", ""))

    if not banking_tasks_synced or not airline_user_id or airline_user_id != airline_user_id.lower():
        return Stage288GuardVerdict(
            scenario_id="PR-12",
            pr_group="PR-12",
            passed=False,
            decision_code="TAU2_BANKING_DRIFT_OR_UPPERCASE_AIRLINE_USER_ID",
            action="SYNC_BANKING_TASKS_AND_LOWERCASE_AIRLINE_USER_ID",
            confidence=0.99,
            remediation="Synchronize aggregate banking task definitions and enforce lowercase airline user_id per tau2-bench#606/#602.",
            covered_prs=prs,
        )
    if not nl_judge_cost_separated or "/" in checkpoint_filename or "\\" in checkpoint_filename:
        return Stage288GuardVerdict(
            scenario_id="PR-12",
            pr_group="PR-12",
            passed=False,
            decision_code="TAU_NL_JUDGE_COST_MERGED_OR_UNSANITIZED_MODEL_PATH",
            action="SEPARATE_NL_JUDGE_COST_AND_SANITIZE_CHECKPOINT_PATH",
            confidence=0.98,
            remediation="Persist NL-judge cost separately and sanitize '/' in model names for checkpoint filenames per tau2-bench#593 & tau-bench#72.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-12",
        pr_group="PR-12",
        passed=True,
        decision_code="TAU2_BANKING_AIRLINE_AND_CHECKPOINT_PATH_VERIFIED",
        action="ALLOW_TAU2_BENCHMARK_EVALUATION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_mcp_ext_auth_sep646_and_servers_fetch_host_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-13: ext-auth#4/#3 SEP-646/990/1046/1502, inspector#2806 mcpdo load thresholds & servers#5241/#5240 fetch host check."""
    prs = tuple(STAGE288_PR_GROUPS["PR-13"])
    enterprise_auth_sep646_verified = bool(payload.get("enterprise_auth_sep646_verified", False))
    load_connections = int(payload.get("load_connections", 0))
    load_max_connections = int(payload.get("load_max_connections", 0))
    connection_host = str(payload.get("connection_host", ""))
    validated_host = str(payload.get("validated_host", ""))

    if not enterprise_auth_sep646_verified:
        return Stage288GuardVerdict(
            scenario_id="PR-13",
            pr_group="PR-13",
            passed=False,
            decision_code="MCP_EXT_AUTH_SEP646_OR_SEP1046_UNVERIFIED",
            action="ENFORCE_ENTERPRISE_MANAGED_AND_CLIENT_CREDENTIALS_AUTH",
            confidence=0.99,
            remediation="Enforce SEP-646/SEP-990 enterprise-managed authorization and SEP-1046/SEP-1502 client credentials per ext-auth#4/#3/#2.",
            covered_prs=prs,
        )
    if load_connections <= 0 or load_max_connections <= 0 or load_connections > load_max_connections:
        return Stage288GuardVerdict(
            scenario_id="PR-13",
            pr_group="PR-13",
            passed=False,
            decision_code="MCP_INSPECTOR_LOAD_THRESHOLD_EXCEEDED",
            action="CAP_MCPDO_LOAD_CONNECTIONS_AT_THRESHOLD",
            confidence=0.98,
            remediation="Enforce --load-connections and --load-max-* thresholds on tools/call --load per inspector#2806/#2791.",
            covered_prs=prs,
        )
    if not connection_host or connection_host != validated_host:
        return Stage288GuardVerdict(
            scenario_id="PR-13",
            pr_group="PR-13",
            passed=False,
            decision_code="MCP_SERVERS_FETCH_CONNECTION_HOST_MISMATCH",
            action="BLOCK_DNS_REBINDING_OR_HOST_MISMATCH_IN_FETCH",
            confidence=0.99,
            remediation="Verify the actual hostname used by the outbound connection in mcp-server-fetch per servers#5240/#5241.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-13",
        pr_group="PR-13",
        passed=True,
        decision_code="MCP_EXT_AUTH_LOAD_THRESHOLDS_AND_FETCH_HOST_VERIFIED",
        action="ALLOW_MCP_SERVER_AND_INSPECTOR_FLOW",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_mcp_ts_sampling_context_and_python_uri_rfc8707_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-14: typescript-sdk#3073/#3072/#3064 sampling.context & cache invalidation + python-sdk#3749/#3741/#3739."""
    prs = tuple(STAGE288_PR_GROUPS["PR-14"])
    include_context = str(payload.get("include_context", "none"))
    has_sampling_context_cap = bool(payload.get("has_sampling_context_cap", False))
    invalidated_cache_discarded = bool(payload.get("invalidated_cache_discarded", False))
    uri_has_non_utf8_percent_escape = bool(payload.get("uri_has_non_utf8_percent_escape", False))
    rfc8707_resource_preserved = bool(payload.get("rfc8707_resource_preserved", False))
    sibling_read_timeout_isolated = bool(payload.get("sibling_read_timeout_isolated", False))

    if include_context in {"thisServer", "allServers"} and not has_sampling_context_cap:
        return Stage288GuardVerdict(
            scenario_id="PR-14",
            pr_group="PR-14",
            passed=False,
            decision_code="MCP_TS_INCLUDE_CONTEXT_WITHOUT_SAMPLING_CAPABILITY",
            action="REFUSE_INCLUDE_CONTEXT_WITHOUT_SAMPLING_CONTEXT",
            confidence=0.99,
            remediation="Refuse includeContext thisServer/allServers when sampling.context is not negotiated per typescript-sdk#3064.",
            covered_prs=prs,
        )
    if not invalidated_cache_discarded or uri_has_non_utf8_percent_escape:
        return Stage288GuardVerdict(
            scenario_id="PR-14",
            pr_group="PR-14",
            passed=False,
            decision_code="MCP_STALE_CACHE_READ_OR_NON_UTF8_URI_PERCENT_ESCAPE",
            action="DISCARD_INVALIDATED_CACHE_AND_REJECT_NON_UTF8_URI",
            confidence=0.99,
            remediation="Discard cache reads invalidated while pending and reject non-UTF-8 percent-escapes in UriTemplate.match() per typescript-sdk#3072 & python-sdk#3749.",
            covered_prs=prs,
        )
    if not rfc8707_resource_preserved or not sibling_read_timeout_isolated:
        return Stage288GuardVerdict(
            scenario_id="PR-14",
            pr_group="PR-14",
            passed=False,
            decision_code="MCP_PYTHON_RFC8707_RESOURCE_DROPPED_OR_TIMEOUT_BLEED",
            action="PRESERVE_RFC8707_RESOURCE_AND_ISOLATE_HTTP_TIMEOUTS",
            confidence=0.98,
            remediation="Preserve RFC 8707 resource indicator in token exchange grants and isolate HTTP read timeouts from sibling requests per python-sdk#3741/#3739.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-14",
        pr_group="PR-14",
        passed=True,
        decision_code="MCP_TS_AND_PYTHON_SDK_GUARDS_VERIFIED",
        action="ALLOW_MCP_TS_PYTHON_SESSION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_mcp_go_oauthex_and_rust_dcr_auth_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-15: go-sdk#1446/#1403/#1386 SSE detach & oauthex parent-path resource + rust-sdk#1359/#1358/#1352 + csharp-sdk#1950."""
    prs = tuple(STAGE288_PR_GROUPS["PR-15"])
    sse_detached_from_connect_ctx = bool(payload.get("sse_detached_from_connect_ctx", False))
    oauthex_resource_valid = bool(payload.get("oauthex_resource_valid", False))
    dcr_auth_method_supported = bool(payload.get("dcr_auth_method_supported", False))
    initial_scope_selected = bool(payload.get("initial_scope_selected", False))
    sampling_stdio_timeout_applied = bool(payload.get("sampling_stdio_timeout_applied", False))

    if not sse_detached_from_connect_ctx or not oauthex_resource_valid:
        return Stage288GuardVerdict(
            scenario_id="PR-15",
            pr_group="PR-15",
            passed=False,
            decision_code="MCP_GO_SSE_CONTEXT_COUPLED_OR_OAUTHEX_RESOURCE_INVALID",
            action="DETACH_SSE_STREAM_AND_VALIDATE_OAUTHEX_RESOURCE_PATH",
            confidence=0.99,
            remediation="Detach SSE client event stream from Connect context and validate origin/parent-path resource identifiers per go-sdk#1403/#1386.",
            covered_prs=prs,
        )
    if not dcr_auth_method_supported or not initial_scope_selected or not sampling_stdio_timeout_applied:
        return Stage288GuardVerdict(
            scenario_id="PR-15",
            pr_group="PR-15",
            passed=False,
            decision_code="MCP_RUST_UNSUPPORTED_DCR_METHOD_OR_CSHARP_STDIO_HANG",
            action="SELECT_SUPPORTED_DCR_AUTH_METHOD_AND_BOUND_STDIO_DISCOVERY",
            confidence=0.98,
            remediation="Select server-supported DCR authentication methods and initial scopes in rust-sdk#1358/#1352 and bound Sampling_Stdio in csharp-sdk#1950.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-15",
        pr_group="PR-15",
        passed=True,
        decision_code="MCP_GO_RUST_CSHARP_GUARDS_VERIFIED",
        action="ALLOW_MCP_SYSTEMS_SDK_EXECUTION",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


def evaluate_mcp_swift_mpp_payment_and_polyglot_stream_guard(payload: dict[str, Any]) -> Stage288GuardVerdict:
    """PR-16: swift-sdk#229 MCPError.paymentRequired (MPP), kotlin-sdk#1091 MCP-Protocol-Version, php-sdk#577/#574 & ruby-sdk#587/#582."""
    prs = tuple(STAGE288_PR_GROUPS["PR-16"])
    mpp_payment_required_typed = bool(payload.get("mpp_payment_required_typed", False))
    negotiated_protocol_header_sent = bool(payload.get("negotiated_protocol_header_sent", False))
    unanswered_request_failed_at_once = bool(payload.get("unanswered_request_failed_at_once", False))
    listen_stream_uris_bounded = bool(payload.get("listen_stream_uris_bounded", False))
    removed_listen_stream_closed = bool(payload.get("removed_listen_stream_closed", False))

    if not mpp_payment_required_typed or not negotiated_protocol_header_sent:
        return Stage288GuardVerdict(
            scenario_id="PR-16",
            pr_group="PR-16",
            passed=False,
            decision_code="MCP_SWIFT_MPP_ERROR_UNTYPED_OR_KOTLIN_VERSION_HEADER_MISSING",
            action="SURFACE_MCP_PAYMENT_REQUIRED_AND_SEND_PROTOCOL_VERSION",
            confidence=0.99,
            remediation="Surface MCPError.paymentRequired for MPP over JSON-RPC in swift-sdk#229 and send negotiated MCP-Protocol-Version in kotlin-sdk#1091.",
            covered_prs=prs,
        )
    if not unanswered_request_failed_at_once or not listen_stream_uris_bounded or not removed_listen_stream_closed:
        return Stage288GuardVerdict(
            scenario_id="PR-16",
            pr_group="PR-16",
            passed=False,
            decision_code="MCP_PHP_UNANSWERED_HANG_OR_RUBY_LISTEN_URI_LEAK",
            action="FAIL_UNANSWERED_RESPONSE_AND_BOUND_SUBSCRIPTION_STREAMS",
            confidence=0.98,
            remediation="Fail unanswered requests immediately in php-sdk#577 and bound/close subscriptions/listen streams in ruby-sdk#587/#582.",
            covered_prs=prs,
        )
    return Stage288GuardVerdict(
        scenario_id="PR-16",
        pr_group="PR-16",
        passed=True,
        decision_code="MCP_POLYGLOT_MPP_VERSION_AND_STREAM_BOUNDS_VERIFIED",
        action="ALLOW_POLYGLOT_MCP_TRANSPORT",
        confidence=0.99,
        remediation="None",
        covered_prs=prs,
    )


STAGE288_SCENARIO_EVALUATORS = {
    "PR-01": evaluate_x402_v2_upto_permit2_and_decimal_value_guard,
    "PR-02": evaluate_mppx_realm_session_and_tempo_aa_nonce_guard,
    "PR-03": evaluate_ap2_trust_compliance_and_erc_credit_guard,
    "PR-04": evaluate_ucp_uri_version_and_variant_union_guard,
    "PR-05": evaluate_acp_intervention_states_and_wba_future_created_guard,
    "PR-06": evaluate_a2a_schema_fallback_and_inspector_dompurify_guard,
    "PR-07": evaluate_a2a_python_compat_and_js_grpc_streaming_guard,
    "PR-08": evaluate_a2a_java_push_id_and_dotnet_event_stream_guard,
    "PR-09": evaluate_stripe_tulip_admission_and_sandbox_boundary_guard,
    "PR-10": evaluate_stripe_multi_sdk_extra_headers_and_pmme_currency_guard,
    "PR-11": evaluate_agentkit_prespend_selection_and_cdp_jwt_claims_guard,
    "PR-12": evaluate_tau2_banking_sync_and_model_path_sanitization_guard,
    "PR-13": evaluate_mcp_ext_auth_sep646_and_servers_fetch_host_guard,
    "PR-14": evaluate_mcp_ts_sampling_context_and_python_uri_rfc8707_guard,
    "PR-15": evaluate_mcp_go_oauthex_and_rust_dcr_auth_guard,
    "PR-16": evaluate_mcp_swift_mpp_payment_and_polyglot_stream_guard,
}


def evaluate_stage288_scenario(scenario_id: str, payload: dict[str, Any]) -> Stage288GuardVerdict:
    evaluator = STAGE288_SCENARIO_EVALUATORS[scenario_id]
    return evaluator(payload)
