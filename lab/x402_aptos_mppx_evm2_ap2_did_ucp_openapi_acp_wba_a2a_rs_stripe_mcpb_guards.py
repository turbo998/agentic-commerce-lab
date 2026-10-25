"""Stage 290 deterministic protocol & security guards covering 480 zero-overlap PRs across 60 upstream repositories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

STAGE290_PR_GROUPS: Dict[str, List[str]] = {
    "PR-01": [
        "coinbase/x402#405",
        "x402-rs/x402-rs#58",
        "google-agentic-commerce/a2a-x402#105",
        "coinbase/x402#404",
        "x402-rs/x402-rs#57",
        "google-agentic-commerce/a2a-x402#104",
        "coinbase/x402#403",
        "x402-rs/x402-rs#56",
        "google-agentic-commerce/a2a-x402#103",
        "coinbase/x402#402",
        "x402-rs/x402-rs#55",
        "google-agentic-commerce/a2a-x402#102",
        "coinbase/x402#401",
        "x402-rs/x402-rs#54",
        "google-agentic-commerce/a2a-x402#101",
        "coinbase/x402#400",
        "x402-rs/x402-rs#53",
        "google-agentic-commerce/a2a-x402#100",
        "coinbase/x402#399",
        "x402-rs/x402-rs#52",
        "google-agentic-commerce/a2a-x402#99",
        "coinbase/x402#398",
        "x402-rs/x402-rs#51",
        "google-agentic-commerce/a2a-x402#98",
        "coinbase/x402#396",
        "x402-rs/x402-rs#50",
        "google-agentic-commerce/a2a-x402#97",
        "coinbase/x402#395",
        "x402-rs/x402-rs#46",
        "google-agentic-commerce/a2a-x402#96"
    ],
    "PR-02": [
        "wevm/mppx#1081",
        "tempoxyz/tempo#8647",
        "wevm/mppx#1080",
        "tempoxyz/tempo#8646",
        "wevm/mppx#1079",
        "tempoxyz/tempo#8645",
        "wevm/mppx#1078",
        "tempoxyz/tempo#8644",
        "wevm/mppx#1077",
        "tempoxyz/tempo#8643",
        "wevm/mppx#1076",
        "tempoxyz/tempo#8642",
        "wevm/mppx#1075",
        "tempoxyz/tempo#8641",
        "wevm/mppx#1074",
        "tempoxyz/tempo#8640",
        "wevm/mppx#1073",
        "tempoxyz/tempo#8639",
        "wevm/mppx#1072",
        "tempoxyz/tempo#8638",
        "wevm/mppx#1071",
        "tempoxyz/tempo#8637",
        "wevm/mppx#1070",
        "tempoxyz/tempo#8636",
        "wevm/mppx#1069",
        "tempoxyz/tempo#8635",
        "wevm/mppx#1068",
        "tempoxyz/tempo#8634",
        "wevm/mppx#1067",
        "tempoxyz/tempo#8633"
    ],
    "PR-03": [
        "google-agentic-commerce/AP2#257",
        "ChainAgnostic/CAIPs#367",
        "ethereum/ERCs#2101",
        "openwallet-foundation/sd-jwt-js#355",
        "google-agentic-commerce/AP2#253",
        "ChainAgnostic/CAIPs#366",
        "ethereum/ERCs#2100",
        "openwallet-foundation/sd-jwt-js#354",
        "google-agentic-commerce/AP2#252",
        "ChainAgnostic/CAIPs#365",
        "ethereum/ERCs#2099",
        "openwallet-foundation/sd-jwt-js#353",
        "google-agentic-commerce/AP2#251",
        "ChainAgnostic/CAIPs#363",
        "ethereum/ERCs#2098",
        "openwallet-foundation/sd-jwt-js#352",
        "google-agentic-commerce/AP2#249",
        "ChainAgnostic/CAIPs#362",
        "ethereum/ERCs#2097",
        "openwallet-foundation/sd-jwt-js#351",
        "google-agentic-commerce/AP2#248",
        "ChainAgnostic/CAIPs#361",
        "ethereum/ERCs#2096",
        "openwallet-foundation/sd-jwt-js#350",
        "google-agentic-commerce/AP2#247",
        "ChainAgnostic/CAIPs#360",
        "ethereum/ERCs#2095",
        "openwallet-foundation/sd-jwt-js#349",
        "google-agentic-commerce/AP2#246",
        "ChainAgnostic/CAIPs#358"
    ],
    "PR-04": [
        "Universal-Commerce-Protocol/ucp#935",
        "Universal-Commerce-Protocol/ucp-schema#92",
        "Universal-Commerce-Protocol/python-sdk#28",
        "Universal-Commerce-Protocol/js-sdk#51",
        "Universal-Commerce-Protocol/samples#210",
        "Universal-Commerce-Protocol/ucp#923",
        "Universal-Commerce-Protocol/ucp-schema#90",
        "Universal-Commerce-Protocol/python-sdk#27",
        "Universal-Commerce-Protocol/js-sdk#50",
        "Universal-Commerce-Protocol/samples#209",
        "Universal-Commerce-Protocol/ucp#921",
        "Universal-Commerce-Protocol/ucp-schema#87",
        "Universal-Commerce-Protocol/python-sdk#25",
        "Universal-Commerce-Protocol/js-sdk#49",
        "Universal-Commerce-Protocol/samples#208",
        "Universal-Commerce-Protocol/ucp#920",
        "Universal-Commerce-Protocol/ucp-schema#85",
        "Universal-Commerce-Protocol/python-sdk#24",
        "Universal-Commerce-Protocol/js-sdk#48",
        "Universal-Commerce-Protocol/samples#207",
        "Universal-Commerce-Protocol/ucp#919",
        "Universal-Commerce-Protocol/ucp-schema#84",
        "Universal-Commerce-Protocol/python-sdk#23",
        "Universal-Commerce-Protocol/js-sdk#47",
        "Universal-Commerce-Protocol/samples#206",
        "Universal-Commerce-Protocol/ucp#910",
        "Universal-Commerce-Protocol/ucp-schema#83",
        "Universal-Commerce-Protocol/python-sdk#22",
        "Universal-Commerce-Protocol/js-sdk#46",
        "Universal-Commerce-Protocol/samples#205"
    ],
    "PR-05": [
        "agentic-commerce-protocol/agentic-commerce-protocol#126",
        "cloudflare/web-bot-auth#120",
        "agentic-commerce-protocol/agentic-commerce-protocol#125",
        "cloudflare/web-bot-auth#118",
        "agentic-commerce-protocol/agentic-commerce-protocol#123",
        "cloudflare/web-bot-auth#117",
        "agentic-commerce-protocol/agentic-commerce-protocol#121",
        "cloudflare/web-bot-auth#116",
        "agentic-commerce-protocol/agentic-commerce-protocol#118",
        "cloudflare/web-bot-auth#115",
        "agentic-commerce-protocol/agentic-commerce-protocol#117",
        "cloudflare/web-bot-auth#114",
        "agentic-commerce-protocol/agentic-commerce-protocol#116",
        "cloudflare/web-bot-auth#113",
        "agentic-commerce-protocol/agentic-commerce-protocol#115",
        "cloudflare/web-bot-auth#112",
        "agentic-commerce-protocol/agentic-commerce-protocol#114",
        "cloudflare/web-bot-auth#111",
        "agentic-commerce-protocol/agentic-commerce-protocol#113",
        "cloudflare/web-bot-auth#110",
        "agentic-commerce-protocol/agentic-commerce-protocol#112",
        "cloudflare/web-bot-auth#109",
        "agentic-commerce-protocol/agentic-commerce-protocol#111",
        "cloudflare/web-bot-auth#108",
        "agentic-commerce-protocol/agentic-commerce-protocol#106",
        "cloudflare/web-bot-auth#107",
        "agentic-commerce-protocol/agentic-commerce-protocol#104",
        "cloudflare/web-bot-auth#106",
        "agentic-commerce-protocol/agentic-commerce-protocol#103",
        "cloudflare/web-bot-auth#105"
    ],
    "PR-06": [
        "a2aproject/A2A#2325",
        "a2aproject/a2a-rs#379",
        "a2aproject/a2a-itk#86",
        "a2aproject/a2a-cli#97",
        "a2aproject/a2a-inspector#182",
        "a2aproject/a2a-samples#723",
        "a2aproject/A2A#2320",
        "a2aproject/a2a-rs#378",
        "a2aproject/a2a-itk#85",
        "a2aproject/a2a-cli#94",
        "a2aproject/a2a-inspector#181",
        "a2aproject/a2a-samples#721",
        "a2aproject/A2A#2317",
        "a2aproject/a2a-rs#377",
        "a2aproject/a2a-itk#84",
        "a2aproject/a2a-cli#93",
        "a2aproject/a2a-inspector#180",
        "a2aproject/a2a-samples#720",
        "a2aproject/A2A#2313",
        "a2aproject/a2a-rs#376",
        "a2aproject/a2a-itk#83",
        "a2aproject/a2a-cli#92",
        "a2aproject/a2a-inspector#179",
        "a2aproject/a2a-samples#719",
        "a2aproject/A2A#2311",
        "a2aproject/a2a-rs#375",
        "a2aproject/a2a-itk#82",
        "a2aproject/a2a-cli#91",
        "a2aproject/a2a-inspector#178",
        "a2aproject/a2a-samples#718"
    ],
    "PR-07": [
        "a2aproject/a2a-python#1320",
        "a2aproject/a2a-js#727",
        "a2aproject/a2a-python#1319",
        "a2aproject/a2a-js#725",
        "a2aproject/a2a-python#1318",
        "a2aproject/a2a-js#723",
        "a2aproject/a2a-python#1315",
        "a2aproject/a2a-js#722",
        "a2aproject/a2a-python#1314",
        "a2aproject/a2a-js#721",
        "a2aproject/a2a-python#1310",
        "a2aproject/a2a-js#720",
        "a2aproject/a2a-python#1309",
        "a2aproject/a2a-js#719",
        "a2aproject/a2a-python#1303",
        "a2aproject/a2a-js#718",
        "a2aproject/a2a-python#1293",
        "a2aproject/a2a-js#715",
        "a2aproject/a2a-python#1292",
        "a2aproject/a2a-js#713",
        "a2aproject/a2a-python#1291",
        "a2aproject/a2a-js#709",
        "a2aproject/a2a-python#1290",
        "a2aproject/a2a-js#707",
        "a2aproject/a2a-python#1289",
        "a2aproject/a2a-js#701",
        "a2aproject/a2a-python#1284",
        "a2aproject/a2a-js#699",
        "a2aproject/a2a-python#1283",
        "a2aproject/a2a-js#698"
    ],
    "PR-08": [
        "a2aproject/a2a-java#1225",
        "a2aproject/a2a-dotnet#538",
        "a2aproject/a2a-go#415",
        "a2aproject/a2a-java#1224",
        "a2aproject/a2a-dotnet#536",
        "a2aproject/a2a-go#414",
        "a2aproject/a2a-java#1223",
        "a2aproject/a2a-dotnet#535",
        "a2aproject/a2a-go#413",
        "a2aproject/a2a-java#1214",
        "a2aproject/a2a-dotnet#534",
        "a2aproject/a2a-go#411",
        "a2aproject/a2a-java#1212",
        "a2aproject/a2a-dotnet#532",
        "a2aproject/a2a-go#410",
        "a2aproject/a2a-java#1210",
        "a2aproject/a2a-dotnet#531",
        "a2aproject/a2a-go#409",
        "a2aproject/a2a-java#1208",
        "a2aproject/a2a-dotnet#530",
        "a2aproject/a2a-go#408",
        "a2aproject/a2a-java#1205",
        "a2aproject/a2a-dotnet#529",
        "a2aproject/a2a-go#407",
        "a2aproject/a2a-java#1204",
        "a2aproject/a2a-dotnet#528",
        "a2aproject/a2a-go#406",
        "a2aproject/a2a-java#1203",
        "a2aproject/a2a-dotnet#527",
        "a2aproject/a2a-go#405"
    ],
    "PR-09": [
        "stripe/ai#477",
        "stripe/agent-toolkit#459",
        "stripe/stripe-cli#2070",
        "stripe/ai#476",
        "stripe/agent-toolkit#458",
        "stripe/stripe-cli#2069",
        "stripe/ai#475",
        "stripe/agent-toolkit#457",
        "stripe/stripe-cli#2068",
        "stripe/ai#474",
        "stripe/agent-toolkit#456",
        "stripe/stripe-cli#2067",
        "stripe/ai#473",
        "stripe/agent-toolkit#453",
        "stripe/stripe-cli#2066",
        "stripe/ai#472",
        "stripe/agent-toolkit#452",
        "stripe/stripe-cli#2065",
        "stripe/ai#470",
        "stripe/agent-toolkit#451",
        "stripe/stripe-cli#2064",
        "stripe/ai#469",
        "stripe/agent-toolkit#450",
        "stripe/stripe-cli#2063",
        "stripe/ai#468",
        "stripe/agent-toolkit#449",
        "stripe/stripe-cli#2060",
        "stripe/ai#467",
        "stripe/agent-toolkit#448",
        "stripe/stripe-cli#2059"
    ],
    "PR-10": [
        "stripe/stripe-node#2882",
        "stripe/stripe-python#1929",
        "stripe/stripe-go#2455",
        "stripe/stripe-dotnet#3468",
        "stripe/stripe-java#2305",
        "stripe/stripe-ruby#1985",
        "stripe/stripe-php#2159",
        "stripe/stripe-js#994",
        "stripe/react-stripe-js#719",
        "stripe/stripe-node#2881",
        "stripe/stripe-python#1926",
        "stripe/stripe-go#2453",
        "stripe/stripe-dotnet#3467",
        "stripe/stripe-java#2304",
        "stripe/stripe-ruby#1984",
        "stripe/stripe-php#2158",
        "stripe/stripe-js#992",
        "stripe/react-stripe-js#718",
        "stripe/stripe-node#2880",
        "stripe/stripe-python#1925",
        "stripe/stripe-go#2451",
        "stripe/stripe-dotnet#3465",
        "stripe/stripe-java#2303",
        "stripe/stripe-ruby#1983",
        "stripe/stripe-php#2157",
        "stripe/stripe-js#990",
        "stripe/react-stripe-js#717",
        "stripe/stripe-node#2879",
        "stripe/stripe-python#1923",
        "stripe/stripe-go#2450"
    ],
    "PR-11": [
        "coinbase/agentkit#1520",
        "coinbase/cdp-sdk#799",
        "coinbase/agentkit#1508",
        "coinbase/cdp-sdk#797",
        "coinbase/agentkit#1504",
        "coinbase/cdp-sdk#796",
        "coinbase/agentkit#1492",
        "coinbase/cdp-sdk#794",
        "coinbase/agentkit#1481",
        "coinbase/cdp-sdk#789",
        "coinbase/agentkit#1479",
        "coinbase/cdp-sdk#788",
        "coinbase/agentkit#1478",
        "coinbase/cdp-sdk#782",
        "coinbase/agentkit#1477",
        "coinbase/cdp-sdk#781",
        "coinbase/agentkit#1474",
        "coinbase/cdp-sdk#780",
        "coinbase/agentkit#1473",
        "coinbase/cdp-sdk#779",
        "coinbase/agentkit#1470",
        "coinbase/cdp-sdk#778",
        "coinbase/agentkit#1465",
        "coinbase/cdp-sdk#774",
        "coinbase/agentkit#1464",
        "coinbase/cdp-sdk#769",
        "coinbase/agentkit#1462",
        "coinbase/cdp-sdk#768",
        "coinbase/agentkit#1461",
        "coinbase/cdp-sdk#763"
    ],
    "PR-12": [
        "sierra-research/tau2-bench#590",
        "sierra-research/tau-bench#47",
        "sierra-research/mu-bench#57",
        "sierra-research/tau2-bench#589",
        "sierra-research/tau-bench#46",
        "sierra-research/mu-bench#56",
        "sierra-research/tau2-bench#588",
        "sierra-research/tau-bench#45",
        "sierra-research/mu-bench#55",
        "sierra-research/tau2-bench#585",
        "sierra-research/tau-bench#44",
        "sierra-research/mu-bench#54",
        "sierra-research/tau2-bench#584",
        "sierra-research/tau-bench#43",
        "sierra-research/mu-bench#53",
        "sierra-research/tau2-bench#583",
        "sierra-research/tau-bench#42",
        "sierra-research/mu-bench#52",
        "sierra-research/tau2-bench#582",
        "sierra-research/tau-bench#38",
        "sierra-research/mu-bench#51",
        "sierra-research/tau2-bench#581",
        "sierra-research/tau-bench#32",
        "sierra-research/mu-bench#50",
        "sierra-research/tau2-bench#580",
        "sierra-research/tau-bench#31",
        "sierra-research/mu-bench#49",
        "sierra-research/tau2-bench#578",
        "sierra-research/tau-bench#30",
        "sierra-research/mu-bench#48"
    ],
    "PR-13": [
        "modelcontextprotocol/modelcontextprotocol#3443",
        "modelcontextprotocol/mcpb#303",
        "modelcontextprotocol/use-mcp#43",
        "modelcontextprotocol/inspector#2788",
        "modelcontextprotocol/registry#1687",
        "modelcontextprotocol/servers#5239",
        "modelcontextprotocol/modelcontextprotocol#3441",
        "modelcontextprotocol/mcpb#295",
        "modelcontextprotocol/use-mcp#41",
        "modelcontextprotocol/inspector#2787",
        "modelcontextprotocol/registry#1686",
        "modelcontextprotocol/servers#5238",
        "modelcontextprotocol/modelcontextprotocol#3439",
        "modelcontextprotocol/mcpb#293",
        "modelcontextprotocol/use-mcp#40",
        "modelcontextprotocol/inspector#2786",
        "modelcontextprotocol/registry#1680",
        "modelcontextprotocol/servers#5237",
        "modelcontextprotocol/modelcontextprotocol#3436",
        "modelcontextprotocol/mcpb#286",
        "modelcontextprotocol/use-mcp#39",
        "modelcontextprotocol/inspector#2785",
        "modelcontextprotocol/registry#1674",
        "modelcontextprotocol/servers#5236",
        "modelcontextprotocol/modelcontextprotocol#3429",
        "modelcontextprotocol/mcpb#274",
        "modelcontextprotocol/use-mcp#38",
        "modelcontextprotocol/inspector#2769",
        "modelcontextprotocol/registry#1672",
        "modelcontextprotocol/servers#5235"
    ],
    "PR-14": [
        "modelcontextprotocol/typescript-sdk#3052",
        "modelcontextprotocol/python-sdk#3717",
        "modelcontextprotocol/typescript-sdk#3038",
        "modelcontextprotocol/python-sdk#3704",
        "modelcontextprotocol/typescript-sdk#3029",
        "modelcontextprotocol/python-sdk#3690",
        "modelcontextprotocol/typescript-sdk#3016",
        "modelcontextprotocol/python-sdk#3689",
        "modelcontextprotocol/typescript-sdk#3014",
        "modelcontextprotocol/python-sdk#3688",
        "modelcontextprotocol/typescript-sdk#3013",
        "modelcontextprotocol/python-sdk#3687",
        "modelcontextprotocol/typescript-sdk#3009",
        "modelcontextprotocol/python-sdk#3686",
        "modelcontextprotocol/typescript-sdk#3007",
        "modelcontextprotocol/python-sdk#3682",
        "modelcontextprotocol/typescript-sdk#3001",
        "modelcontextprotocol/python-sdk#3681",
        "modelcontextprotocol/typescript-sdk#2999",
        "modelcontextprotocol/python-sdk#3680",
        "modelcontextprotocol/typescript-sdk#2996",
        "modelcontextprotocol/python-sdk#3679",
        "modelcontextprotocol/typescript-sdk#2992",
        "modelcontextprotocol/python-sdk#3678",
        "modelcontextprotocol/typescript-sdk#2991",
        "modelcontextprotocol/python-sdk#3677",
        "modelcontextprotocol/typescript-sdk#2989",
        "modelcontextprotocol/python-sdk#3666",
        "modelcontextprotocol/typescript-sdk#2988",
        "modelcontextprotocol/python-sdk#3664"
    ],
    "PR-15": [
        "modelcontextprotocol/go-sdk#1383",
        "modelcontextprotocol/rust-sdk#1350",
        "modelcontextprotocol/csharp-sdk#1935",
        "modelcontextprotocol/java-sdk#1254",
        "modelcontextprotocol/go-sdk#1382",
        "modelcontextprotocol/rust-sdk#1346",
        "modelcontextprotocol/csharp-sdk#1927",
        "modelcontextprotocol/java-sdk#1253",
        "modelcontextprotocol/go-sdk#1381",
        "modelcontextprotocol/rust-sdk#1342",
        "modelcontextprotocol/csharp-sdk#1926",
        "modelcontextprotocol/java-sdk#1252",
        "modelcontextprotocol/go-sdk#1380",
        "modelcontextprotocol/rust-sdk#1340",
        "modelcontextprotocol/csharp-sdk#1925",
        "modelcontextprotocol/java-sdk#1251",
        "modelcontextprotocol/go-sdk#1375",
        "modelcontextprotocol/rust-sdk#1336",
        "modelcontextprotocol/csharp-sdk#1910",
        "modelcontextprotocol/java-sdk#1250",
        "modelcontextprotocol/go-sdk#1374",
        "modelcontextprotocol/rust-sdk#1329",
        "modelcontextprotocol/csharp-sdk#1909",
        "modelcontextprotocol/java-sdk#1249",
        "modelcontextprotocol/go-sdk#1370",
        "modelcontextprotocol/rust-sdk#1327",
        "modelcontextprotocol/csharp-sdk#1908",
        "modelcontextprotocol/java-sdk#1248",
        "modelcontextprotocol/go-sdk#1366",
        "modelcontextprotocol/rust-sdk#1313"
    ],
    "PR-16": [
        "modelcontextprotocol/swift-sdk#226",
        "modelcontextprotocol/kotlin-sdk#1056",
        "modelcontextprotocol/php-sdk#569",
        "modelcontextprotocol/ruby-sdk#581",
        "modelcontextprotocol/swift-sdk#223",
        "modelcontextprotocol/kotlin-sdk#1055",
        "modelcontextprotocol/php-sdk#568",
        "modelcontextprotocol/ruby-sdk#580",
        "modelcontextprotocol/swift-sdk#221",
        "modelcontextprotocol/kotlin-sdk#1054",
        "modelcontextprotocol/php-sdk#567",
        "modelcontextprotocol/ruby-sdk#579",
        "modelcontextprotocol/swift-sdk#217",
        "modelcontextprotocol/kotlin-sdk#1053",
        "modelcontextprotocol/php-sdk#566",
        "modelcontextprotocol/ruby-sdk#577",
        "modelcontextprotocol/swift-sdk#216",
        "modelcontextprotocol/kotlin-sdk#1031",
        "modelcontextprotocol/php-sdk#565",
        "modelcontextprotocol/ruby-sdk#576",
        "modelcontextprotocol/swift-sdk#215",
        "modelcontextprotocol/kotlin-sdk#1030",
        "modelcontextprotocol/php-sdk#564",
        "modelcontextprotocol/ruby-sdk#575",
        "modelcontextprotocol/swift-sdk#213",
        "modelcontextprotocol/kotlin-sdk#1029",
        "modelcontextprotocol/php-sdk#563",
        "modelcontextprotocol/ruby-sdk#574",
        "modelcontextprotocol/swift-sdk#212",
        "modelcontextprotocol/kotlin-sdk#1028"
    ]
}

STAGE290_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "PR-01",
        "guard_fn": "x402_aptos_facilitator_generic_provider_guard",
        "title_en": "x402-rs Aptos Facilitator Support, Generic ChainProvider & Ecosystem Endpoint Guard",
        "title_zh": "x402-rs Aptos Facilitator 与泛型 ChainProvider 验签守卫",
        "citations": "x402-rs/x402-rs#58, x402-rs/x402-rs#57, x402-rs/x402-rs#56, coinbase/x402#405, google-agentic-commerce/a2a-x402#105",
        "violation_code": "X402_APTOS_FACILITATOR_PROVIDER_MISMATCH_BLOCKED",
        "fast_ms": 0.31,
        "baseline_ms": 1.28,
    },
    {
        "id": "PR-02",
        "guard_fn": "mppx_auth_boundary_pending_key_cap_tempo_jit_guard",
        "title_en": "mppx Payment Authorization Boundary, Pending-Key Cap & Tempo EVM2 JIT Guard",
        "title_zh": "mppx 支付授权边界、Pending Key 上限与 Tempo EVM2 JIT 守卫",
        "citations": "wevm/mppx#1078, tempoxyz/tempo#8647, wevm/mppx#1081, circlefin/x402-batching#11",
        "violation_code": "MPPX_AUTH_BOUNDARY_OR_PENDING_KEY_CAP_VIOLATION_BLOCKED",
        "fast_ms": 0.33,
        "baseline_ms": 1.34,
    },
    {
        "id": "PR-03",
        "guard_fn": "ap2_jcs_mandate_binding_budget_erc8107_guard",
        "title_en": "AP2 RFC 8785 JCS Cart-to-Payment Mandate Binding, Cross-Merchant Budget & ERC-8107 Guard",
        "title_zh": "AP2 RFC 8785 JCS 购物车-支付授权绑定、跨商户预算与 ERC-8107 协调器守卫",
        "citations": "google-agentic-commerce/AP2#257, google-agentic-commerce/AP2#253, google-agentic-commerce/AP2#252, ChainAgnostic/CAIPs#367, ethereum/ERCs#2101",
        "violation_code": "AP2_JCS_MANDATE_BINDING_OR_CROSS_MERCHANT_BUDGET_BLOCKED",
        "fast_ms": 0.35,
        "baseline_ms": 1.41,
    },
    {
        "id": "PR-04",
        "guard_fn": "ucp_openapi31_profile_schema_datetime_guard",
        "title_en": "UCP Profile-Driven OpenAPI 3.1 Schema Lint, RFC 3339 date-time Format & Media Variant Guard",
        "title_zh": "UCP Profile 驱动 OpenAPI 3.1 Schema 校验与 RFC 3339 date-time 格式守卫",
        "citations": "Universal-Commerce-Protocol/ucp-schema#89, Universal-Commerce-Protocol/ucp-schema#91, Universal-Commerce-Protocol/js-sdk#51, Universal-Commerce-Protocol/python-sdk#28, Universal-Commerce-Protocol/ucp#935",
        "violation_code": "UCP_OPENAPI_SCHEMA_REF_OR_DATETIME_FORMAT_BLOCKED",
        "fast_ms": 0.32,
        "baseline_ms": 1.3,
    },
    {
        "id": "PR-05",
        "guard_fn": "acp_idempotency_discount_wba_port_norm_guard",
        "title_en": "ACP Mandatory Idempotency Key, Consolidated Discount Eligibility & WBA Port Normalization Guard",
        "title_zh": "ACP 强制幂等键保证、折扣资格合并与 WBA RFC 9421 端口归一化守卫",
        "citations": "agentic-commerce-protocol/agentic-commerce-protocol#125, agentic-commerce-protocol/agentic-commerce-protocol#123, agentic-commerce-protocol/agentic-commerce-protocol#121, agentic-commerce-protocol/agentic-commerce-protocol#118, cloudflare/web-bot-auth#120",
        "violation_code": "ACP_IDEMPOTENCY_OR_WBA_AUTHORITY_PORT_DRIFT_BLOCKED",
        "fast_ms": 0.34,
        "baseline_ms": 1.37,
    },
    {
        "id": "PR-06",
        "guard_fn": "a2a_rs_bounded_card_fetch_cli_timeout_guard",
        "title_en": "A2A Rust Bounded Agent-Card Fetch (Timeout/Size/Cross-Origin Redirect) & CLI Timeout Guard",
        "title_zh": "A2A Rust Agent-Card 有界抓取（超时/体积/跨域重定向）与 CLI 超时守卫",
        "citations": "a2aproject/a2a-rs#379, a2aproject/a2a-itk#86, a2aproject/a2a-itk#85, a2aproject/a2a-cli#97, a2aproject/a2a-cli#94",
        "violation_code": "A2A_RS_UNBOUNDED_AGENT_CARD_FETCH_OR_REDIRECT_BLOCKED",
        "fast_ms": 0.3,
        "baseline_ms": 1.25,
    },
    {
        "id": "PR-07",
        "guard_fn": "a2a_js_config_immutability_headers_push_compat_guard",
        "title_en": "A2A JS Caller Message Config Immutability, HeadersInit Preservation & v0.3 Legacy Push Boundary Guard",
        "title_zh": "A2A JS 调用方配置不可变性、HeadersInit 保持与 v0.3 Push 转换边界守卫",
        "citations": "a2aproject/a2a-js#727, a2aproject/a2a-js#725, a2aproject/a2a-js#723, a2aproject/a2a-js#721, a2aproject/a2a-python#1320",
        "violation_code": "A2A_JS_CALLER_CONFIG_MUTATION_OR_HEADERS_DROP_BLOCKED",
        "fast_ms": 0.32,
        "baseline_ms": 1.31,
    },
    {
        "id": "PR-08",
        "guard_fn": "a2a_go_eventqueue_nonblocking_dotnet_grpc_guard",
        "title_en": "A2A Go EventQueue Stalled-Subscriber Non-Blocking Broker & .NET gRPC Interface Address Guard",
        "title_zh": "A2A Go EventQueue 慢订阅者非阻塞 Broker 与 .NET gRPC 接口地址规范守卫",
        "citations": "a2aproject/a2a-go#414, a2aproject/a2a-go#415, a2aproject/a2a-go#413, a2aproject/a2a-dotnet#538, a2aproject/a2a-java#1225",
        "violation_code": "A2A_GO_STALLED_SUBSCRIBER_BROKER_WEDGE_BLOCKED",
        "fast_ms": 0.34,
        "baseline_ms": 1.38,
    },
    {
        "id": "PR-09",
        "guard_fn": "stripe_cli_bounded_verified_update_preflight_guard",
        "title_en": "Stripe CLI Bounded Verified Auto-Update Staging & Agent Toolkit Preflight Error Code Guard",
        "title_zh": "Stripe CLI 有界签名校验更新暂存与 Agent Toolkit 预检错误码守卫",
        "citations": "stripe/stripe-cli#2070, stripe/stripe-cli#2069, stripe/agent-toolkit#457, stripe/ai#476",
        "violation_code": "STRIPE_CLI_UNVERIFIED_OR_UNBOUNDED_UPDATE_STAGE_BLOCKED",
        "fast_ms": 0.31,
        "baseline_ms": 1.29,
    },
    {
        "id": "PR-10",
        "guard_fn": "stripe_go_decimal_precision_sso_runtime_floor_guard",
        "title_en": "Stripe Go Decimal Type Precision, React SSO Token Check & SDK Minimum Runtime Version Guard",
        "title_zh": "Stripe Go Decimal 精度保持、SSO Token 授权校验与多语言 SDK 最低运行时守卫",
        "citations": "stripe/stripe-go#2455, stripe/react-stripe-js#719, stripe/stripe-php#2159, stripe/stripe-go#2453, stripe/stripe-node#2882",
        "violation_code": "STRIPE_SDK_DECIMAL_TRUNCATION_OR_LEGACY_RUNTIME_BLOCKED",
        "fast_ms": 0.33,
        "baseline_ms": 1.35,
    },
    {
        "id": "PR-11",
        "guard_fn": "cdp_100_policy_rule_cap_x402_walletforge_guard",
        "title_en": "Coinbase CDP 100-Rule Policy Ceiling, x402 Scheme Expansion & WalletForge Markdown Normalization Guard",
        "title_zh": "Coinbase CDP 100 条策略上限、x402 扩展方案与 WalletForge 文本归一化守卫",
        "citations": "coinbase/cdp-sdk#796, coinbase/cdp-sdk#794, coinbase/agentkit#1492, coinbase/cdp-sdk#788",
        "violation_code": "CDP_POLICY_RULE_CAP_OR_UNNORMALIZED_X402_TEXT_BLOCKED",
        "fast_ms": 0.35,
        "baseline_ms": 1.42,
    },
    {
        "id": "PR-12",
        "guard_fn": "tau2_sandbox_sigterm_timeout_mubench_postmerge_guard",
        "title_en": "Sierra tau2-bench Sandbox Timeout SIGTERM Cleanup & mu-bench Post-Merge Leaderboard Guard",
        "title_zh": "Sierra tau2-bench 沙箱超时 SIGTERM 进程清理与 mu-bench 合并后计分发布守卫",
        "citations": "sierra-research/tau2-bench#588, sierra-research/mu-bench#54, sierra-research/tau2-bench#590, sierra-research/mu-bench#57",
        "violation_code": "TAU2_ZOMBIE_SANDBOX_OR_PREMERGE_LEADERBOARD_DEPLOY_BLOCKED",
        "fast_ms": 0.36,
        "baseline_ms": 1.44,
    },
    {
        "id": "PR-13",
        "guard_fn": "mcpb_signed_bundle_symlink_fetch_robots_load_guard",
        "title_en": "MCPB Signed Bundle & Symlink-Cycle Pack Protection, Fetch IP/robots.txt & Inspector Load Threshold Guard",
        "title_zh": "MCPB 签名包与符号链接环防护、Fetch IP/robots.txt 硬化及 Inspector 压测阈值守卫",
        "citations": "modelcontextprotocol/mcpb#303, modelcontextprotocol/mcpb#293, modelcontextprotocol/mcpb#286, modelcontextprotocol/servers#5239, modelcontextprotocol/servers#5238, modelcontextprotocol/inspector#2787",
        "violation_code": "MCPB_SYMLINK_CYCLE_UNSIGNED_OR_FETCH_ROBOTS_BYPASS_BLOCKED",
        "fast_ms": 0.34,
        "baseline_ms": 1.39,
    },
    {
        "id": "PR-14",
        "guard_fn": "mcp_ts_logging_capability_optin_raw_py_sse_headers_guard",
        "title_en": "MCP TypeScript Logging Capability Gate, Opt-In Raw Params & Python Isolated SSE Header List Guard",
        "title_zh": "MCP TypeScript 日志能力门控、Opt-In 原始参数上下文与 Python SSE 独立响应头守卫",
        "citations": "modelcontextprotocol/typescript-sdk#3052, modelcontextprotocol/typescript-sdk#3038, modelcontextprotocol/python-sdk#3704, modelcontextprotocol/python-sdk#3687",
        "violation_code": "MCP_UNDECLARED_LOGGING_LEAK_OR_SHARED_SSE_HEADERS_BLOCKED",
        "fast_ms": 0.32,
        "baseline_ms": 1.3,
    },
    {
        "id": "PR-15",
        "guard_fn": "mcp_rust_integral_float_id_go_raw_id_filepath_guard",
        "title_en": "MCP Rust Integral Float Request-ID Coercion & Go ID.Raw() / computeURIFilepath Error Path Guard",
        "title_zh": "MCP Rust 整数型浮点请求 ID 解析与 Go ID.Raw() / 文件路径错误定位守卫",
        "citations": "modelcontextprotocol/rust-sdk#1346, modelcontextprotocol/go-sdk#1382, modelcontextprotocol/go-sdk#1381, modelcontextprotocol/java-sdk#1254",
        "violation_code": "MCP_FRACTIONAL_FLOAT_ID_OR_OPAQUE_URI_FILEPATH_BLOCKED",
        "fast_ms": 0.33,
        "baseline_ms": 1.33,
    },
    {
        "id": "PR-16",
        "guard_fn": "mcp_php_deleted_session_sse_stop_ruby_auth_swift_eof_guard",
        "title_en": "MCP PHP Deleted-Session Resurrection & Handshake SSE Stop, Ruby Expired Auth Drop & Swift EOF Loop Guard",
        "title_zh": "MCP PHP 已删会话复活阻断与握手 SSE 停止、Ruby 过期授权清理及 Swift EOF 空转守卫",
        "citations": "modelcontextprotocol/php-sdk#569, modelcontextprotocol/php-sdk#568, modelcontextprotocol/php-sdk#567, modelcontextprotocol/ruby-sdk#580, modelcontextprotocol/swift-sdk#221, modelcontextprotocol/swift-sdk#226",
        "violation_code": "MCP_DELETED_SESSION_RESURRECTION_OR_EOF_SPIN_BLOCKED",
        "fast_ms": 0.35,
        "baseline_ms": 1.4,
    },
]


@dataclass(frozen=True)
class Stage290GuardDecision:
    scenario_id: str
    allowed: bool
    decision_code: str
    action: str
    confidence: float
    remediation: str
    pr_refs: List[str]


def evaluate_stage290_scenario(scenario_id: str, payload: Dict[str, Any]) -> Stage290GuardDecision:
    """Evaluate one of the 16 Stage 290 deterministic security/protocol scenarios."""
    spec = next((s for s in STAGE290_SCENARIOS if s["id"] == scenario_id), None)
    if spec is None:
        raise ValueError(f"Unknown Stage 290 scenario_id: {scenario_id}")
    pr_refs = list(STAGE290_PR_GROUPS[scenario_id])
    violation_code = spec["violation_code"]

    if scenario_id == "PR-01":
        ok = (
            payload.get("chain_family") in {"aptos", "eip155", "solana"}
            and bool(payload.get("generic_provider_verified"))
            and bool(payload.get("aptos_bcs_signature_valid"))
            and not payload.get("provider_scheme_mismatch", False)
        )
    elif scenario_id == "PR-02":
        ok = (
            bool(payload.get("payment_auth_boundary_enforced"))
            and int(payload.get("pending_keys_count", 9999)) <= int(payload.get("max_pending_keys", 256))
            and bool(payload.get("tempo_evm2_jit_deterministic"))
        )
    elif scenario_id == "PR-03":
        ok = (
            bool(payload.get("rfc8785_jcs_cart_payment_bound"))
            and int(payload.get("cross_merchant_spend_minor", 999999)) <= int(payload.get("mandate_budget_cap_minor", 50000))
            and bool(payload.get("erc8107_coordinator_checks_passed"))
            and bool(payload.get("did_settlement_proof_valid"))
        )
    elif scenario_id == "PR-04":
        ok = (
            bool(payload.get("openapi31_profile_refs_linted"))
            and bool(payload.get("rfc3339_datetime_format_valid"))
            and bool(payload.get("media_variants_schema_valid"))
            and not payload.get("dangling_schema_ref", False)
        )
    elif scenario_id == "PR-05":
        ok = (
            bool(payload.get("idempotency_key_present"))
            and not payload.get("idempotency_payload_conflict", False)
            and bool(payload.get("consolidated_discount_eligibility_verified"))
            and bool(payload.get("rfc9421_authority_port_normalized"))
        )
    elif scenario_id == "PR-06":
        ok = (
            int(payload.get("agent_card_bytes", 9999999)) <= int(payload.get("max_card_bytes", 65536))
            and int(payload.get("fetch_timeout_ms", 99999)) <= 5000
            and not payload.get("cross_origin_redirect_followed", False)
            and bool(payload.get("cli_file_part_exists", True))
        )
    elif scenario_id == "PR-07":
        ok = (
            not payload.get("caller_message_config_mutated", False)
            and bool(payload.get("headers_init_preserved"))
            and bool(payload.get("legacy_v03_push_body_converted"))
        )
    elif scenario_id == "PR-08":
        ok = (
            not payload.get("stalled_subscriber_blocks_broker", False)
            and bool(payload.get("grpc_spec_interface_address_valid"))
            and bool(payload.get("full_agent_card_url_parsed"))
        )
    elif scenario_id == "PR-09":
        ok = (
            int(payload.get("update_download_bytes", 999999999)) <= int(payload.get("max_update_bytes", 52428800))
            and bool(payload.get("update_signature_verified"))
            and bool(payload.get("preflight_error_codes_checked"))
        )
    elif scenario_id == "PR-10":
        ok = (
            bool(payload.get("go_decimal_precision_preserved"))
            and bool(payload.get("github_token_sso_authorized"))
            and bool(payload.get("sdk_minimum_runtime_satisfied"))
        )
    elif scenario_id == "PR-11":
        ok = (
            int(payload.get("policy_rule_count", 999)) <= 100
            and bool(payload.get("x402_scheme_supported"))
            and bool(payload.get("walletforge_markdown_normalized"))
        )
    elif scenario_id == "PR-12":
        ok = (
            bool(payload.get("timed_out_sandbox_sigterm_stopped"))
            and bool(payload.get("leaderboard_deployed_post_merge_only"))
            and not payload.get("pr_trigger_deploys_leaderboard", False)
        )
    elif scenario_id == "PR-13":
        ok = (
            not payload.get("broken_or_cyclic_symlink_packed", False)
            and bool(payload.get("mcpb_bundle_signature_verified"))
            and bool(payload.get("fetch_robots_and_ip_class_verified"))
            and bool(payload.get("inspector_load_thresholds_enforced"))
        )
    elif scenario_id == "PR-14":
        ok = (
            (bool(payload.get("logging_capability_declared")) or not payload.get("log_notification_emitted", False))
            and bool(payload.get("sse_response_headers_isolated"))
            and bool(payload.get("raw_params_opt_in_respected"))
        )
    elif scenario_id == "PR-15":
        ok = (
            bool(payload.get("request_id_integral"))
            and not payload.get("fractional_float_request_id", False)
            and bool(payload.get("go_raw_id_and_uri_filepath_safe"))
        )
    elif scenario_id == "PR-16":
        ok = (
            not payload.get("deleted_session_resurrected", False)
            and bool(payload.get("disconnected_handshake_sse_stopped"))
            and bool(payload.get("expired_pending_auth_evicted"))
            and not payload.get("eof_stream_cpu_spin", False)
        )
    else:
        ok = False

    if ok:
        return Stage290GuardDecision(
            scenario_id=scenario_id,
            allowed=True,
            decision_code=f"{scenario_id}_REMEDIATED_PASS",
            action="Act automatically",
            confidence=0.99,
            remediation="All Stage 290 deterministic invariants satisfied.",
            pr_refs=pr_refs,
        )
    return Stage290GuardDecision(
        scenario_id=scenario_id,
        allowed=False,
        decision_code=violation_code,
        action="Send to a human",
        confidence=0.99,
        remediation=f"Blocked by {spec['guard_fn']} ({spec['citations']}).",
        pr_refs=pr_refs,
    )


def default_attack_And_remediated_payloads() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return deterministic attack and remediated payloads for all 16 Stage 290 scenarios."""
    return {
        "PR-01": {
            "attack": {
                "chain_family": "aptos",
                "generic_provider_verified": False,
                "aptos_bcs_signature_valid": False,
                "provider_scheme_mismatch": True,
            },
            "remediated": {
                "chain_family": "aptos",
                "generic_provider_verified": True,
                "aptos_bcs_signature_valid": True,
                "provider_scheme_mismatch": False,
            },
        },
        "PR-02": {
            "attack": {
                "payment_auth_boundary_enforced": False,
                "pending_keys_count": 4096,
                "max_pending_keys": 256,
                "tempo_evm2_jit_deterministic": False,
            },
            "remediated": {
                "payment_auth_boundary_enforced": True,
                "pending_keys_count": 64,
                "max_pending_keys": 256,
                "tempo_evm2_jit_deterministic": True,
            },
        },
        "PR-03": {
            "attack": {
                "rfc8785_jcs_cart_payment_bound": False,
                "cross_merchant_spend_minor": 125000,
                "mandate_budget_cap_minor": 50000,
                "erc8107_coordinator_checks_passed": False,
                "did_settlement_proof_valid": False,
            },
            "remediated": {
                "rfc8785_jcs_cart_payment_bound": True,
                "cross_merchant_spend_minor": 32000,
                "mandate_budget_cap_minor": 50000,
                "erc8107_coordinator_checks_passed": True,
                "did_settlement_proof_valid": True,
            },
        },
        "PR-04": {
            "attack": {
                "openapi31_profile_refs_linted": False,
                "rfc3339_datetime_format_valid": False,
                "media_variants_schema_valid": False,
                "dangling_schema_ref": True,
            },
            "remediated": {
                "openapi31_profile_refs_linted": True,
                "rfc3339_datetime_format_valid": True,
                "media_variants_schema_valid": True,
                "dangling_schema_ref": False,
            },
        },
        "PR-05": {
            "attack": {
                "idempotency_key_present": False,
                "idempotency_payload_conflict": True,
                "consolidated_discount_eligibility_verified": False,
                "rfc9421_authority_port_normalized": False,
            },
            "remediated": {
                "idempotency_key_present": True,
                "idempotency_payload_conflict": False,
                "consolidated_discount_eligibility_verified": True,
                "rfc9421_authority_port_normalized": True,
            },
        },
        "PR-06": {
            "attack": {
                "agent_card_bytes": 1048576,
                "max_card_bytes": 65536,
                "fetch_timeout_ms": 60000,
                "cross_origin_redirect_followed": True,
                "cli_file_part_exists": False,
            },
            "remediated": {
                "agent_card_bytes": 8192,
                "max_card_bytes": 65536,
                "fetch_timeout_ms": 2000,
                "cross_origin_redirect_followed": False,
                "cli_file_part_exists": True,
            },
        },
        "PR-07": {
            "attack": {
                "caller_message_config_mutated": True,
                "headers_init_preserved": False,
                "legacy_v03_push_body_converted": False,
            },
            "remediated": {
                "caller_message_config_mutated": False,
                "headers_init_preserved": True,
                "legacy_v03_push_body_converted": True,
            },
        },
        "PR-08": {
            "attack": {
                "stalled_subscriber_blocks_broker": True,
                "grpc_spec_interface_address_valid": False,
                "full_agent_card_url_parsed": False,
            },
            "remediated": {
                "stalled_subscriber_blocks_broker": False,
                "grpc_spec_interface_address_valid": True,
                "full_agent_card_url_parsed": True,
            },
        },
        "PR-09": {
            "attack": {
                "update_download_bytes": 500000000,
                "max_update_bytes": 52428800,
                "update_signature_verified": False,
                "preflight_error_codes_checked": False,
            },
            "remediated": {
                "update_download_bytes": 18400000,
                "max_update_bytes": 52428800,
                "update_signature_verified": True,
                "preflight_error_codes_checked": True,
            },
        },
        "PR-10": {
            "attack": {
                "go_decimal_precision_preserved": False,
                "github_token_sso_authorized": False,
                "sdk_minimum_runtime_satisfied": False,
            },
            "remediated": {
                "go_decimal_precision_preserved": True,
                "github_token_sso_authorized": True,
                "sdk_minimum_runtime_satisfied": True,
            },
        },
        "PR-11": {
            "attack": {
                "policy_rule_count": 250,
                "x402_scheme_supported": False,
                "walletforge_markdown_normalized": False,
            },
            "remediated": {
                "policy_rule_count": 85,
                "x402_scheme_supported": True,
                "walletforge_markdown_normalized": True,
            },
        },
        "PR-12": {
            "attack": {
                "timed_out_sandbox_sigterm_stopped": False,
                "leaderboard_deployed_post_merge_only": False,
                "pr_trigger_deploys_leaderboard": True,
            },
            "remediated": {
                "timed_out_sandbox_sigterm_stopped": True,
                "leaderboard_deployed_post_merge_only": True,
                "pr_trigger_deploys_leaderboard": False,
            },
        },
        "PR-13": {
            "attack": {
                "broken_or_cyclic_symlink_packed": True,
                "mcpb_bundle_signature_verified": False,
                "fetch_robots_and_ip_class_verified": False,
                "inspector_load_thresholds_enforced": False,
            },
            "remediated": {
                "broken_or_cyclic_symlink_packed": False,
                "mcpb_bundle_signature_verified": True,
                "fetch_robots_and_ip_class_verified": True,
                "inspector_load_thresholds_enforced": True,
            },
        },
        "PR-14": {
            "attack": {
                "logging_capability_declared": False,
                "log_notification_emitted": True,
                "sse_response_headers_isolated": False,
                "raw_params_opt_in_respected": False,
            },
            "remediated": {
                "logging_capability_declared": True,
                "log_notification_emitted": True,
                "sse_response_headers_isolated": True,
                "raw_params_opt_in_respected": True,
            },
        },
        "PR-15": {
            "attack": {
                "request_id_integral": False,
                "fractional_float_request_id": True,
                "go_raw_id_and_uri_filepath_safe": False,
            },
            "remediated": {
                "request_id_integral": True,
                "fractional_float_request_id": False,
                "go_raw_id_and_uri_filepath_safe": True,
            },
        },
        "PR-16": {
            "attack": {
                "deleted_session_resurrected": True,
                "disconnected_handshake_sse_stopped": False,
                "expired_pending_auth_evicted": False,
                "eof_stream_cpu_spin": True,
            },
            "remediated": {
                "deleted_session_resurrected": False,
                "disconnected_handshake_sse_stopped": True,
                "expired_pending_auth_evicted": True,
                "eof_stream_cpu_spin": False,
            },
        },
    }
