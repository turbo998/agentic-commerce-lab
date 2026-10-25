"""Stage 282 deterministic guard suite: A2A-x402 random nonce & settlement finality,
x402-rs settle retry & URL redaction, MPP atomic stream reservation & Tempo voucher migration,
Visa MCP X-Pay lexicographic token & TAP hybrid ML-DSA-65, AP2 mandate corpus & RFC 9901 SD-JWT,
UCP Web Bot Auth interop & schema twin isolation, ACP delegate auth & Meta governance,
A2A remote attestation & 6-SDK guards, Stripe WIF / API v2 Search / Agent-Toolkit,
Coinbase AgentKit RelayShield / M2M Sentinel & Sierra tau2-bench, and MCP SEP-3246 11-SDK guards.

Covers 356 strictly zero-overlap primary-source PRs across 49 upstream repositories.
"""

from __future__ import annotations

from typing import Any

STAGE282_PR_GROUPS: dict[str, tuple[str, ...]] = {
    "PR-01": (
        "google-agentic-commerce/a2a-x402#190",
        "google-agentic-commerce/a2a-x402#186",
        "google-agentic-commerce/a2a-x402#178",
        "google-agentic-commerce/a2a-x402#172",
        "google-agentic-commerce/a2a-x402#162",
        "google-agentic-commerce/a2a-x402#160",
        "google-agentic-commerce/a2a-x402#158",
        "google-agentic-commerce/a2a-x402#154",
        "google-agentic-commerce/a2a-x402#151",
        "google-agentic-commerce/a2a-x402#148",
        "google-agentic-commerce/a2a-x402#147",
        "google-agentic-commerce/a2a-x402#137",
        "coinbase/x402#316",
        "coinbase/x402#315",
        "coinbase/x402#314",
        "coinbase/x402#313",
        "coinbase/x402#311",
        "coinbase/x402#310",
        "coinbase/x402#309",
        "coinbase/x402#308",
        "coinbase/x402#307",
        "coinbase/x402#305",
    ),
    "PR-02": (
        "x402-rs/x402-rs#142",
        "x402-rs/x402-rs#141",
        "x402-rs/x402-rs#140",
        "x402-rs/x402-rs#138",
        "x402-rs/x402-rs#129",
        "x402-rs/x402-rs#128",
        "x402-rs/x402-rs#118",
        "x402-rs/x402-rs#116",
        "x402-rs/x402-rs#115",
        "x402-rs/x402-rs#109",
        "x402-rs/x402-rs#107",
        "x402-rs/x402-rs#106",
        "x402-rs/x402-rs#103",
        "x402-rs/x402-rs#101",
        "ChainAgnostic/CAIPs#411",
        "ChainAgnostic/CAIPs#410",
        "ChainAgnostic/CAIPs#404",
        "ChainAgnostic/CAIPs#402",
        "ChainAgnostic/CAIPs#400",
        "ChainAgnostic/CAIPs#399",
        "ChainAgnostic/CAIPs#397",
        "ChainAgnostic/CAIPs#395",
    ),
    "PR-03": (
        "wevm/mppx#993",
        "wevm/mppx#992",
        "wevm/mppx#991",
        "wevm/mppx#990",
        "wevm/mppx#989",
        "wevm/mppx#988",
        "wevm/mppx#987",
        "wevm/mppx#986",
        "wevm/mppx#985",
        "wevm/mppx#984",
        "wevm/mppx#983",
        "tempoxyz/tempo#8558",
        "tempoxyz/tempo#8557",
        "tempoxyz/tempo#8556",
        "tempoxyz/tempo#8554",
        "tempoxyz/tempo#8553",
        "tempoxyz/tempo#8552",
        "tempoxyz/tempo#8551",
        "tempoxyz/tempo#8550",
        "tempoxyz/tempo#8549",
        "tempoxyz/tempo#8548",
        "tempoxyz/tempo#8547",
    ),
    "PR-04": (
        "visa/mcp#21",
        "visa/mcp#20",
        "visa/mcp#19",
        "visa/mcp#18",
        "visa/mcp#17",
        "visa/mcp#16",
        "visa/mcp#15",
        "visa/mcp#14",
        "visa/mcp#13",
        "visa/mcp#12",
        "visa/mcp#10",
        "visa/mcp#9",
        "visa/trusted-agent-protocol#19",
        "visa/trusted-agent-protocol#17",
        "visa/trusted-agent-protocol#12",
        "visa/trusted-agent-protocol#11",
        "visa/trusted-agent-protocol#7",
        "visa/trusted-agent-protocol#6",
        "visa/trusted-agent-protocol#5",
        "visa/trusted-agent-protocol#4",
        "visa/trusted-agent-protocol#3",
        "visa/trusted-agent-protocol#1",
    ),
    "PR-05": (
        "google-agentic-commerce/AP2#382",
        "google-agentic-commerce/AP2#379",
        "google-agentic-commerce/AP2#373",
        "google-agentic-commerce/AP2#370",
        "google-agentic-commerce/AP2#369",
        "google-agentic-commerce/AP2#366",
        "google-agentic-commerce/AP2#357",
        "google-agentic-commerce/AP2#352",
        "openwallet-foundation/sd-jwt-js#394",
        "openwallet-foundation/sd-jwt-js#393",
        "openwallet-foundation/sd-jwt-js#392",
        "openwallet-foundation/sd-jwt-js#389",
        "openwallet-foundation/sd-jwt-js#387",
        "openwallet-foundation/sd-jwt-js#386",
        "cloudflare/web-bot-auth#170",
        "cloudflare/web-bot-auth#169",
        "cloudflare/web-bot-auth#167",
        "cloudflare/web-bot-auth#163",
        "cloudflare/web-bot-auth#161",
        "modelcontextprotocol/ext-auth#41",
        "modelcontextprotocol/ext-auth#38",
        "modelcontextprotocol/ext-auth#37",
        "modelcontextprotocol/ext-auth#36",
        "modelcontextprotocol/ext-auth#35",
    ),
    "PR-06": (
        "Universal-Commerce-Protocol/ucp#829",
        "Universal-Commerce-Protocol/ucp#828",
        "Universal-Commerce-Protocol/ucp#825",
        "Universal-Commerce-Protocol/ucp#823",
        "Universal-Commerce-Protocol/ucp#819",
        "Universal-Commerce-Protocol/ucp#818",
        "Universal-Commerce-Protocol/ucp#816",
        "Universal-Commerce-Protocol/ucp#814",
        "Universal-Commerce-Protocol/python-sdk#95",
        "Universal-Commerce-Protocol/python-sdk#81",
        "Universal-Commerce-Protocol/python-sdk#80",
        "Universal-Commerce-Protocol/python-sdk#79",
        "Universal-Commerce-Protocol/python-sdk#77",
        "Universal-Commerce-Protocol/python-sdk#75",
        "Universal-Commerce-Protocol/js-sdk#89",
        "Universal-Commerce-Protocol/js-sdk#86",
        "Universal-Commerce-Protocol/js-sdk#85",
        "Universal-Commerce-Protocol/js-sdk#84",
        "Universal-Commerce-Protocol/js-sdk#83",
        "Universal-Commerce-Protocol/js-sdk#82",
        "Universal-Commerce-Protocol/samples#261",
        "Universal-Commerce-Protocol/samples#260",
        "Universal-Commerce-Protocol/samples#259",
        "Universal-Commerce-Protocol/samples#256",
    ),
    "PR-07": (
        "agentic-commerce-protocol/agentic-commerce-protocol#269",
        "agentic-commerce-protocol/agentic-commerce-protocol#268",
        "agentic-commerce-protocol/agentic-commerce-protocol#267",
        "agentic-commerce-protocol/agentic-commerce-protocol#263",
        "agentic-commerce-protocol/agentic-commerce-protocol#251",
        "agentic-commerce-protocol/agentic-commerce-protocol#240",
        "agentic-commerce-protocol/agentic-commerce-protocol#236",
        "agentic-commerce-protocol/agentic-commerce-protocol#227",
        "agentic-commerce-protocol/agentic-commerce-protocol#226",
        "agentic-commerce-protocol/agentic-commerce-protocol#225",
        "agentic-commerce-protocol/agentic-commerce-protocol#224",
        "agentic-commerce-protocol/agentic-commerce-protocol#223",
        "agentic-commerce-protocol/agentic-commerce-protocol#218",
        "agentic-commerce-protocol/agentic-commerce-protocol#217",
        "agentic-commerce-protocol/agentic-commerce-protocol#216",
        "agentic-commerce-protocol/agentic-commerce-protocol#215",
        "agentic-commerce-protocol/agentic-commerce-protocol#214",
        "agentic-commerce-protocol/agentic-commerce-protocol#213",
        "agentic-commerce-protocol/agentic-commerce-protocol#212",
        "agentic-commerce-protocol/agentic-commerce-protocol#203",
    ),
    "PR-08": (
        "a2aproject/A2A#2092",
        "a2aproject/A2A#2091",
        "a2aproject/A2A#2089",
        "a2aproject/A2A#2088",
        "a2aproject/A2A#2086",
        "a2aproject/A2A#2084",
        "a2aproject/A2A#2083",
        "a2aproject/A2A#2081",
        "a2aproject/a2a-python#1233",
        "a2aproject/a2a-python#1230",
        "a2aproject/a2a-python#1229",
        "a2aproject/a2a-python#1227",
        "a2aproject/a2a-python#1226",
        "a2aproject/a2a-python#1225",
        "a2aproject/a2a-python#1223",
        "a2aproject/a2a-python#1222",
        "a2aproject/a2a-js#796",
        "a2aproject/a2a-js#795",
        "a2aproject/a2a-js#794",
        "a2aproject/a2a-js#793",
        "a2aproject/a2a-js#792",
        "a2aproject/a2a-js#790",
    ),
    "PR-09": (
        "a2aproject/a2a-go#487",
        "a2aproject/a2a-go#486",
        "a2aproject/a2a-go#485",
        "a2aproject/a2a-go#482",
        "a2aproject/a2a-go#481",
        "a2aproject/a2a-go#479",
        "a2aproject/a2a-java#1103",
        "a2aproject/a2a-java#1101",
        "a2aproject/a2a-java#1100",
        "a2aproject/a2a-java#1094",
        "a2aproject/a2a-java#1092",
        "a2aproject/a2a-java#1091",
        "a2aproject/a2a-dotnet#586",
        "a2aproject/a2a-dotnet#585",
        "a2aproject/a2a-dotnet#584",
        "a2aproject/a2a-dotnet#583",
        "a2aproject/a2a-dotnet#582",
        "a2aproject/a2a-inspector#218",
        "a2aproject/a2a-inspector#216",
        "a2aproject/a2a-inspector#215",
        "a2aproject/a2a-inspector#212",
        "a2aproject/a2a-inspector#211",
    ),
    "PR-10": (
        "stripe/ai#579",
        "stripe/ai#578",
        "stripe/ai#576",
        "stripe/ai#569",
        "stripe/ai#567",
        "stripe/ai#560",
        "stripe/ai#557",
        "stripe/ai#552",
        "stripe/agent-toolkit#581",
        "stripe/agent-toolkit#578",
        "stripe/agent-toolkit#559",
        "stripe/agent-toolkit#557",
        "stripe/agent-toolkit#539",
        "stripe/agent-toolkit#538",
        "stripe/agent-toolkit#515",
        "stripe/stripe-cli#2148",
        "stripe/stripe-cli#2146",
        "stripe/stripe-cli#2143",
        "stripe/stripe-cli#2142",
        "stripe/stripe-cli#2140",
        "stripe/stripe-cli#2139",
        "stripe/stripe-cli#2138",
    ),
    "PR-11": (
        "stripe/stripe-python#1955",
        "stripe/stripe-python#1952",
        "stripe/stripe-python#1950",
        "stripe/stripe-python#1949",
        "stripe/stripe-node#2910",
        "stripe/stripe-node#2909",
        "stripe/stripe-node#2904",
        "stripe/stripe-node#2903",
        "stripe/stripe-go#2478",
        "stripe/stripe-go#2475",
        "stripe/stripe-go#2474",
        "stripe/stripe-go#2473",
        "stripe/stripe-java#2320",
        "stripe/stripe-java#2319",
        "stripe/stripe-java#2318",
        "stripe/stripe-dotnet#3483",
        "stripe/stripe-dotnet#3481",
        "stripe/stripe-dotnet#3480",
        "stripe/stripe-ruby#2006",
        "stripe/stripe-ruby#2004",
        "stripe/stripe-ruby#2003",
        "stripe/stripe-php#2179",
        "stripe/stripe-php#2178",
        "stripe/stripe-php#2177",
    ),
    "PR-12": (
        "coinbase/agentkit#1449",
        "coinbase/agentkit#1447",
        "coinbase/agentkit#1446",
        "coinbase/agentkit#1443",
        "coinbase/agentkit#1442",
        "coinbase/agentkit#1441",
        "coinbase/agentkit#1440",
        "coinbase/agentkit#1439",
        "coinbase/agentkit#1438",
        "coinbase/agentkit#1435",
        "coinbase/agentkit#1433",
        "coinbase/agentkit#1432",
        "sierra-research/tau2-bench#682",
        "sierra-research/tau2-bench#681",
        "sierra-research/tau2-bench#679",
        "sierra-research/tau2-bench#676",
        "sierra-research/tau2-bench#675",
        "sierra-research/tau2-bench#670",
        "sierra-research/tau2-bench#669",
        "sierra-research/tau2-bench#657",
        "sierra-research/tau2-bench#656",
        "sierra-research/tau2-bench#651",
    ),
    "PR-13": (
        "modelcontextprotocol/modelcontextprotocol#3256",
        "modelcontextprotocol/modelcontextprotocol#3255",
        "modelcontextprotocol/modelcontextprotocol#3254",
        "modelcontextprotocol/modelcontextprotocol#3251",
        "modelcontextprotocol/modelcontextprotocol#3248",
        "modelcontextprotocol/modelcontextprotocol#3246",
        "modelcontextprotocol/modelcontextprotocol#3245",
        "modelcontextprotocol/modelcontextprotocol#3244",
        "modelcontextprotocol/python-sdk#3595",
        "modelcontextprotocol/python-sdk#3593",
        "modelcontextprotocol/python-sdk#3591",
        "modelcontextprotocol/python-sdk#3587",
        "modelcontextprotocol/python-sdk#3584",
        "modelcontextprotocol/python-sdk#3583",
        "modelcontextprotocol/python-sdk#3582",
        "modelcontextprotocol/typescript-sdk#2954",
        "modelcontextprotocol/typescript-sdk#2953",
        "modelcontextprotocol/typescript-sdk#2952",
        "modelcontextprotocol/typescript-sdk#2951",
        "modelcontextprotocol/typescript-sdk#2950",
        "modelcontextprotocol/typescript-sdk#2948",
        "modelcontextprotocol/typescript-sdk#2947",
    ),
    "PR-14": (
        "modelcontextprotocol/go-sdk#1290",
        "modelcontextprotocol/go-sdk#1287",
        "modelcontextprotocol/go-sdk#1286",
        "modelcontextprotocol/go-sdk#1285",
        "modelcontextprotocol/go-sdk#1283",
        "modelcontextprotocol/go-sdk#1282",
        "modelcontextprotocol/go-sdk#1280",
        "modelcontextprotocol/go-sdk#1279",
        "modelcontextprotocol/rust-sdk#1252",
        "modelcontextprotocol/rust-sdk#1250",
        "modelcontextprotocol/rust-sdk#1249",
        "modelcontextprotocol/rust-sdk#1248",
        "modelcontextprotocol/rust-sdk#1247",
        "modelcontextprotocol/rust-sdk#1246",
        "modelcontextprotocol/rust-sdk#1243",
        "modelcontextprotocol/java-sdk#1149",
        "modelcontextprotocol/java-sdk#1145",
        "modelcontextprotocol/java-sdk#1144",
        "modelcontextprotocol/java-sdk#1143",
        "modelcontextprotocol/java-sdk#1142",
        "modelcontextprotocol/java-sdk#1141",
        "modelcontextprotocol/java-sdk#1139",
    ),
    "PR-15": (
        "modelcontextprotocol/csharp-sdk#1809",
        "modelcontextprotocol/csharp-sdk#1808",
        "modelcontextprotocol/csharp-sdk#1807",
        "modelcontextprotocol/csharp-sdk#1805",
        "modelcontextprotocol/csharp-sdk#1804",
        "modelcontextprotocol/csharp-sdk#1803",
        "modelcontextprotocol/csharp-sdk#1802",
        "modelcontextprotocol/csharp-sdk#1801",
        "modelcontextprotocol/kotlin-sdk#1133",
        "modelcontextprotocol/kotlin-sdk#1128",
        "modelcontextprotocol/kotlin-sdk#1127",
        "modelcontextprotocol/kotlin-sdk#1126",
        "modelcontextprotocol/kotlin-sdk#1125",
        "modelcontextprotocol/kotlin-sdk#1124",
        "modelcontextprotocol/kotlin-sdk#1123",
        "modelcontextprotocol/swift-sdk#308",
        "modelcontextprotocol/swift-sdk#306",
        "modelcontextprotocol/swift-sdk#304",
        "modelcontextprotocol/swift-sdk#299",
        "modelcontextprotocol/swift-sdk#294",
        "modelcontextprotocol/swift-sdk#290",
        "modelcontextprotocol/swift-sdk#289",
    ),
    "PR-16": (
        "modelcontextprotocol/php-sdk#616",
        "modelcontextprotocol/php-sdk#611",
        "modelcontextprotocol/php-sdk#610",
        "modelcontextprotocol/php-sdk#608",
        "modelcontextprotocol/php-sdk#604",
        "modelcontextprotocol/php-sdk#600",
        "modelcontextprotocol/ruby-sdk#631",
        "modelcontextprotocol/ruby-sdk#626",
        "modelcontextprotocol/ruby-sdk#625",
        "modelcontextprotocol/ruby-sdk#622",
        "modelcontextprotocol/ruby-sdk#621",
        "modelcontextprotocol/ruby-sdk#620",
        "modelcontextprotocol/inspector#2610",
        "modelcontextprotocol/inspector#2603",
        "modelcontextprotocol/inspector#2601",
        "modelcontextprotocol/inspector#2600",
        "modelcontextprotocol/inspector#2599",
        "modelcontextprotocol/registry#1732",
        "modelcontextprotocol/registry#1731",
        "modelcontextprotocol/registry#1729",
        "modelcontextprotocol/registry#1728",
        "modelcontextprotocol/registry#1727",
    ),
}


def evaluate_a2a_x402_nonce_and_settlement_guard(
    *,
    eip3009_nonce_csprng: bool,
    response_deferred_until_settled: bool,
    stepsecurity_workflow_pinned: bool,
) -> dict[str, Any]:
    """PR-01: google-agentic-commerce/a2a-x402 (#190/#186/#172) & coinbase/x402 (#316/#313)."""
    if not eip3009_nonce_csprng:
        return {
            "passed": False,
            "code": "A2A_X402_SEQUENTIAL_NONCE_COLLISION_REJECTED",
            "reason": "EIP-3009 authorization must generate a 32-byte CSPRNG nonce (#190).",
        }
    if not response_deferred_until_settled:
        return {
            "passed": False,
            "code": "A2A_X402_PREMATURE_RESPONSE_BEFORE_SETTLEMENT_BLOCKED",
            "reason": "Paid A2A task completion must wait for facilitator settlement finality (#186).",
        }
    if not stepsecurity_workflow_pinned:
        return {
            "passed": False,
            "code": "X402_UNPINNED_CI_WORKFLOW_REJECTED",
            "reason": "CI workflow actions must apply StepSecurity least-privilege and SHA pinning (#313).",
        }
    return {
        "passed": True,
        "code": "A2A_X402_RANDOM_NONCE_AND_DEFERRED_SETTLEMENT_VERIFIED",
        "reason": "CSPRNG EIP-3009 nonce and post-settlement paid response completion verified.",
    }


def evaluate_x402_rs_settle_retry_and_caip_cwp_guard(
    *,
    chain_reconciled_on_store_miss: bool,
    receipt_timeout_returns_pending: bool,
    rpc_url_redacted_in_error: bool,
    caip_cwp_label_valid: bool,
) -> dict[str, Any]:
    """PR-02: x402-rs/x402-rs (#142/#140/#138/#118) & ChainAgnostic/CAIPs (#411/#404/#397)."""
    if not chain_reconciled_on_store_miss:
        return {
            "passed": False,
            "code": "X402_RS_SETTLE_RETRY_DOUBLE_BROADCAST_BLOCKED",
            "reason": "Settle retries with missing store entries must reconcile broadcast tx on-chain (#142/#140).",
        }
    if not receipt_timeout_returns_pending:
        return {
            "passed": False,
            "code": "X402_RS_RECEIPT_TIMEOUT_HASH_LOSS_REJECTED",
            "reason": "Receipt fetch failures must preserve tx hash and return settlement_pending (#138).",
        }
    if not rpc_url_redacted_in_error:
        return {
            "passed": False,
            "code": "X402_RS_PROVIDER_RPC_URL_LEAK_BLOCKED",
            "reason": "On-chain failure details must redact provider RPC URLs and API keys (#118).",
        }
    if not caip_cwp_label_valid:
        return {
            "passed": False,
            "code": "CAIP_CWP_LABEL_SCHEMA_MISMATCH",
            "reason": "CLI Wallet Protocol (CAIP-397) and Label ID (CAIP-411) bindings must validate.",
        }
    return {
        "passed": True,
        "code": "X402_RS_SETTLE_RECONCILIATION_AND_URL_REDACTION_VERIFIED",
        "reason": "x402-rs on-chain settle retry reconciliation, pending state, and RPC redaction verified.",
    }


def evaluate_mppx_atomic_reservation_and_tempo_voucher_guard(
    *,
    stream_reservation_atomic: bool,
    settled_on_close_detected: bool,
    retired_root_key_rejected: bool,
    migrated_voucher_redeemable: bool,
) -> dict[str, Any]:
    """PR-03: wevm/mppx (#992/#991/#990/#989) & tempoxyz/tempo (#8558/#8557/#8554)."""
    if not stream_reservation_atomic:
        return {
            "passed": False,
            "code": "MPPX_NON_ATOMIC_STREAM_RESERVATION_RACE_BLOCKED",
            "reason": "Concurrent MPP stream reservations must share balance atomically (#990).",
        }
    if not settled_on_close_detected:
        return {
            "passed": False,
            "code": "MPPX_UNSETTLED_ACCEPTED_FUNDS_ON_CLOSE_REJECTED",
            "reason": "Session close detection must settle all accepted vouchers (#991).",
        }
    if not retired_root_key_rejected:
        return {
            "passed": False,
            "code": "TEMPO_ZONE_RPC_RETIRED_ROOT_KEY_ACCEPTED",
            "reason": "Tempo Zone RPC must reject auth tokens signed by retired root keys (#8558).",
        }
    if not migrated_voucher_redeemable:
        return {
            "passed": False,
            "code": "TEMPO_MIGRATED_CHANNEL_VOUCHER_STRANDED",
            "reason": "Precompiles must keep funded channel vouchers redeemable after migration (#8557).",
        }
    return {
        "passed": True,
        "code": "MPPX_ATOMIC_STREAM_AND_TEMPO_VOUCHER_GUARD_VERIFIED",
        "reason": "MPP atomic stream reservations, close settlement, and Tempo root-key/voucher guards verified.",
    }


def evaluate_visa_mcp_xpay_and_tap_hybrid_mldsa_guard(
    *,
    xpay_query_lexicographically_sorted: bool,
    jwks_chain_and_card_redaction_verified: bool,
    tap_ed25519_mldsa65_hybrid_valid: bool,
) -> dict[str, Any]:
    """PR-04: visa/mcp (#21/#18/#17/#16) & visa/trusted-agent-protocol (#17/#12/#11)."""
    if not xpay_query_lexicographically_sorted:
        return {
            "passed": False,
            "code": "VISA_MCP_XPAY_UNSORTED_QUERY_HMAC_MISMATCH",
            "reason": "X-Pay token canonicalization must sort query parameters lexicographically (#21).",
        }
    if not jwks_chain_and_card_redaction_verified:
        return {
            "passed": False,
            "code": "VISA_MCP_JWKS_OR_PAN_LOG_EXPOSURE_BLOCKED",
            "reason": "Visa MCP must validate JWKS chains, scope token deletion, and redact PAN logs (#17/#16).",
        }
    if not tap_ed25519_mldsa65_hybrid_valid:
        return {
            "passed": False,
            "code": "VISA_TAP_DID_HYBRID_MLDSA65_SIGNATURE_INVALID",
            "reason": "TAP agent registry requires DID key_id resolution and Ed25519+ML-DSA-65 verification (#17).",
        }
    return {
        "passed": True,
        "code": "VISA_MCP_XPAY_AND_TAP_HYBRID_MLDSA65_VERIFIED",
        "reason": "Visa MCP lexicographic X-Pay token, JWKS/PAN redaction, and TAP hybrid PQ signature verified.",
    }


def evaluate_ap2_conformance_sdjwt_rfc9901_and_wba_guard(
    *,
    ap2_dual_lang_mandate_verified: bool,
    sdjwt_rfc9901_vct_audited: bool,
    wba_unique_labels_and_https_directory: bool,
    ext_auth_dpop_jkt_bound: bool,
) -> dict[str, Any]:
    """PR-05: AP2 (#370/#369), sd-jwt-js (#389/#387), cloudflare/web-bot-auth (#169/#163), ext-auth (#41/#35)."""
    if not ap2_dual_lang_mandate_verified:
        return {
            "passed": False,
            "code": "AP2_SECOND_LANGUAGE_MANDATE_CORPUS_MISMATCH",
            "reason": "AP2 mandates must pass both reference and second-language conformance verifiers (#370/#369).",
        }
    if not sdjwt_rfc9901_vct_audited:
        return {
            "passed": False,
            "code": "SDJWT_RFC9901_VCT_AUDIT_FAILURE",
            "reason": "SD-JWT presentations must satisfy RFC 9901 audit and vct claim verification (#389/#387).",
        }
    if not wba_unique_labels_and_https_directory:
        return {
            "passed": False,
            "code": "WBA_DUPLICATE_LABEL_OR_INSECURE_DIRECTORY_REJECTED",
            "reason": "Web Bot Auth must reject duplicate signature labels and require HTTPS Signature-Agent URLs (#169/#163).",
        }
    if not ext_auth_dpop_jkt_bound:
        return {
            "passed": False,
            "code": "MCP_EXT_AUTH_DPOP_JKT_CODE_UNBOUND",
            "reason": "OAuth2 authorization code exchange must bind dpop_jkt and CIMD client_id (#41/#35).",
        }
    return {
        "passed": True,
        "code": "AP2_SDJWT_RFC9901_WBA_DPOP_JKT_VERIFIED",
        "reason": "AP2 dual-verifier mandate corpus, RFC 9901 SD-JWT, WBA HTTPS/unique labels, and DPoP jkt verified.",
    }


def evaluate_ucp_wba_interop_and_schema_twin_isolation_guard(
    *,
    wba_interop_and_payment_finality_defined: bool,
    constrained_schema_twin_isolated: bool,
    local_entity_refs_resolved_before_inline: bool,
) -> dict[str, Any]:
    """PR-06: ucp (#829/#828/#816), python-sdk (#81/#79/#75), js-sdk (#89/#84/#83)."""
    if not wba_interop_and_payment_finality_defined:
        return {
            "passed": False,
            "code": "UCP_CHECKOUT_FINALITY_OR_WBA_INTEROP_MISSING",
            "reason": "UCP checkout must enforce WBA interop (#829) and payment finality reporting (#816).",
        }
    if not constrained_schema_twin_isolated:
        return {
            "passed": False,
            "code": "UCP_JS_CONSTRAINED_SCHEMA_TWIN_POLLUTION",
            "reason": "UCP JS codegen must isolate constrained schemas from unconstrained twins and keep allOf required (#89/#83).",
        }
    if not local_entity_refs_resolved_before_inline:
        return {
            "passed": False,
            "code": "UCP_PYTHON_UNRESOLVED_LOCAL_REF_INLINE_ERROR",
            "reason": "UCP Python schema preprocessor must resolve local entity refs before inlining (#79).",
        }
    return {
        "passed": True,
        "code": "UCP_WBA_FINALITY_AND_SCHEMA_TWIN_ISOLATION_VERIFIED",
        "reason": "UCP WBA interop, payment finality, and Python/JS schema twin isolation verified.",
    }


def evaluate_acp_delegate_auth_and_discount_extension_guard(
    *,
    delegate_auth_and_cla_verified: bool,
    discount_extension_links_and_changelog_valid: bool,
    stale_pr_governance_active: bool,
) -> dict[str, Any]:
    """PR-07: agentic-commerce-protocol/agentic-commerce-protocol (#269/#267/#263/#251/#236)."""
    if not delegate_auth_and_cla_verified:
        return {
            "passed": False,
            "code": "ACP_DELEGATE_AUTH_OR_TSC_GOVERNANCE_INVALID",
            "reason": "ACP delegate authentication and TSC/CLA governance bindings must be verified (#267/#263/#236).",
        }
    if not discount_extension_links_and_changelog_valid:
        return {
            "passed": False,
            "code": "ACP_DISCOUNT_EXTENSION_OR_CHANGELOG_BROKEN",
            "reason": "ACP discount extension references and dated specification changelogs must resolve (#269/#251).",
        }
    if not stale_pr_governance_active:
        return {
            "passed": False,
            "code": "ACP_SPEC_GOVERNANCE_WORKFLOW_INACTIVE",
            "reason": "ACP specification lifecycle governance workflows must be active (#240).",
        }
    return {
        "passed": True,
        "code": "ACP_DELEGATE_AUTH_AND_DISCOUNT_EXTENSION_VERIFIED",
        "reason": "ACP delegate authentication, discount extension specs, and TSC governance verified.",
    }


def evaluate_a2a_remote_attestation_and_python_js_task_guard(
    *,
    hardware_remote_attestation_and_adr002_valid: bool,
    idle_task_stale_snapshot_dropped: bool,
    a2a_version_minor_validated: bool,
) -> dict[str, Any]:
    """PR-08: A2A (#2088/#2084/#2083), a2a-python (#1233/#1229/#1227/#1225), a2a-js (#796/#795)."""
    if not hardware_remote_attestation_and_adr002_valid:
        return {
            "passed": False,
            "code": "A2A_REMOTE_ATTESTATION_OR_TASK_TIMELINE_INVALID",
            "reason": "A2A requires hardware-rooted remote attestation (#2088) and ADR-002 coherent timeline (#2084).",
        }
    if not idle_task_stale_snapshot_dropped:
        return {
            "passed": False,
            "code": "A2A_PYTHON_STALE_ACTIVE_TASK_SNAPSHOT_REUSED",
            "reason": "Reusing an idle task must drop stale ActiveTask snapshots and compare timestamps numerically (#1233/#1227).",
        }
    if not a2a_version_minor_validated:
        return {
            "passed": False,
            "code": "A2A_VERSION_MINOR_OR_PRODUCER_ERROR_SWALLOWED",
            "reason": "A2A server must validate A2A-Version minor header (#1225) and surface producer errors (#1229).",
        }
    return {
        "passed": True,
        "code": "A2A_REMOTE_ATTESTATION_AND_PYTHON_JS_TASK_GUARD_VERIFIED",
        "reason": "A2A hardware attestation, ADR-002 timeline, numeric timestamp order, and minor version checks verified.",
    }


def evaluate_a2a_go_java_dotnet_inspector_guard(
    *,
    go_head_subscription_rejected: bool,
    go_in_place_artifact_recovered: bool,
    java_omitted_push_config_id_allowed: bool,
    inspector_dompurify_and_go_backend_hardened: bool,
) -> dict[str, Any]:
    """PR-09: a2a-go (#487/#485/#481/#479), a2a-java (#1094/#1092/#1091), a2a-dotnet (#586), a2a-inspector (#218/#215)."""
    if not go_head_subscription_rejected:
        return {
            "passed": False,
            "code": "A2A_GO_HEAD_TASK_SUBSCRIPTION_LEAK_BLOCKED",
            "reason": "a2asrv must reject HTTP HEAD requests before creating task subscriptions (#481).",
        }
    if not go_in_place_artifact_recovered:
        return {
            "passed": False,
            "code": "A2A_GO_IN_PLACE_ARTIFACT_MUTATION_TRUNCATED",
            "reason": "a2aevent must recover the full artifact on in-place mutation and support CR SSE lines (#487/#485).",
        }
    if not java_omitted_push_config_id_allowed:
        return {
            "passed": False,
            "code": "A2A_JAVA_OMITTED_PUSH_CONFIG_ID_NPE",
            "reason": "a2a-java must allow omitted task push config IDs (#1092) and optional FilePart names (#1091).",
        }
    if not inspector_dompurify_and_go_backend_hardened:
        return {
            "passed": False,
            "code": "A2A_INSPECTOR_XSS_OR_STALE_TLS_BUNDLE_REJECTED",
            "reason": "a2a-inspector must enforce DOMPurify 3.4.17 sanitization and hardened Go inspector backend (#218/#215).",
        }
    return {
        "passed": True,
        "code": "A2A_GO_JAVA_DOTNET_INSPECTOR_PARITY_VERIFIED",
        "reason": "A2A Go HEAD-rejection/artifact recovery, Java push-config/FilePart, and Inspector hardening verified.",
    }


def evaluate_stripe_ai_plugin_hooks_and_cli_sandbox_guard(
    *,
    threadless_sync_tool_loop_safe: bool,
    deprecated_actions_key_warned: bool,
    cli_telemetry_optout_and_sandbox_stamped: bool,
) -> dict[str, Any]:
    """PR-10: stripe/ai (#579/#569/#567), stripe/agent-toolkit (#581/#559/#515), stripe/stripe-cli (#2146/#2143)."""
    if not threadless_sync_tool_loop_safe:
        return {
            "passed": False,
            "code": "STRIPE_AGENT_TOOLKIT_NO_EVENT_LOOP_CRASH",
            "reason": "Sync LangChain/CrewAI tool calls must run safely when the worker thread has no event loop (#581).",
        }
    if not deprecated_actions_key_warned:
        return {
            "passed": False,
            "code": "STRIPE_AGENT_TOOLKIT_SILENT_DEPRECATED_ACTIONS_KEY",
            "reason": "stripe-agent-toolkit must warn on deprecated 'actions' config keys (#559).",
        }
    if not cli_telemetry_optout_and_sandbox_stamped:
        return {
            "passed": False,
            "code": "STRIPE_CLI_UNSTAMPED_SANDBOX_OR_FORCED_TELEMETRY",
            "reason": "Stripe AI plugin startup checks must opt out of telemetry (#567) and stamp sandbox changes (#2146).",
        }
    return {
        "passed": True,
        "code": "STRIPE_AI_TOOLKIT_AND_CLI_SANDBOX_GUARD_VERIFIED",
        "reason": "Stripe Agent Toolkit event-loop safety, provider-neutral hooks, and CLI sandbox stamping verified.",
    }


def evaluate_stripe_7sdk_wif_and_v2_search_guard(
    *,
    workload_identity_package_trusted_publishing: bool,
    node_fetch_dispose_and_v2list_exported: bool,
    v2_search_and_cert_bundle_verified: bool,
) -> dict[str, Any]:
    """PR-11: stripe-python (#1955), stripe-node (#2904/#2901/#2896), stripe-ruby (#2002/#2000), java/dotnet/php/go."""
    if not workload_identity_package_trusted_publishing:
        return {
            "passed": False,
            "code": "STRIPE_WIF_UNTRUSTED_PUBLISHING_OR_NAMING_DRIFT",
            "reason": "Workload Identities Package (WIF) must enforce release environment & trusted publishing (#2904/#2002).",
        }
    if not node_fetch_dispose_and_v2list_exported:
        return {
            "passed": False,
            "code": "STRIPE_NODE_FETCH_DISPOSE_LEAK_OR_MISSING_V2LIST",
            "reason": "stripe-node must dispose fetch handles cleanly and export V2List/V2ListPromise (#2901/#2896).",
        }
    if not v2_search_and_cert_bundle_verified:
        return {
            "passed": False,
            "code": "STRIPE_SDK_V2_SEARCH_OR_TLS_CERT_OUTDATED",
            "reason": "Stripe SDKs must support API v2 Search (#3476/#2312/#2171) and updated master TLS certs (#1955).",
        }
    return {
        "passed": True,
        "code": "STRIPE_7SDK_WIF_AND_V2_SEARCH_PARITY_VERIFIED",
        "reason": "Stripe 7-SDK Workload Identity trusted publishing, fetch dispose, and API v2 Search verified.",
    }


def evaluate_agentkit_relayshield_sentinel_and_tau2_voice_guard(
    *,
    relayshield_and_m2m_sentinel_active: bool,
    agent_guild_and_offramp_policy_enforced: bool,
    tau2_voice_provider_dated_and_verified: bool,
) -> dict[str, Any]:
    """PR-12: coinbase/agentkit (#1449/#1447/#1446/#1442) & sierra-research/tau2-bench (#676/#675/#670)."""
    if not relayshield_and_m2m_sentinel_active:
        return {
            "passed": False,
            "code": "AGENTKIT_UNINSPECTED_PROXY_BYTECODE_OR_RELAY_RISK",
            "reason": "Base M2M execution requires RelayShield (#1449) and M2M Sentinel proxy/bytecode inspection (#1447).",
        }
    if not agent_guild_and_offramp_policy_enforced:
        return {
            "passed": False,
            "code": "AGENTKIT_UNBOUNDED_USDC_OFFRAMP_OR_TRUST_BYPASS",
            "reason": "USDC cash-out and task markets require Agent Guild payment safety (#1446) and Offramp guards (#1442).",
        }
    if not tau2_voice_provider_dated_and_verified:
        return {
            "passed": False,
            "code": "TAU2_VOICE_SUBMISSION_UNDATED_OR_UNVERIFIED",
            "reason": "tau2-bench voice/audio-native leaderboard submissions must carry release dates and verification (#676/#675).",
        }
    return {
        "passed": True,
        "code": "AGENTKIT_RELAYSHIELD_SENTINEL_AND_TAU2_VOICE_VERIFIED",
        "reason": "Coinbase AgentKit RelayShield/M2M Sentinel/Agent Guild and Sierra tau2-bench voice guards verified.",
    }


def evaluate_mcp_sep3246_authority_and_py_ts_guard(
    *,
    sep3246_provenance_authority_confined: bool,
    py_validation_input_redacted_and_stdio_clean: bool,
    ts_expected_resource_and_ajv_cached: bool,
) -> dict[str, Any]:
    """PR-13: modelcontextprotocol (#3246), python-sdk (#3595/#3584/#3582), typescript-sdk (#2952/#2950)."""
    if not sep3246_provenance_authority_confined:
        return {
            "passed": False,
            "code": "MCP_SEP3246_DELEGATED_AUTHORITY_ESCALATION_BLOCKED",
            "reason": "Delegated MCP tool calls must enforce SEP-3246 provenance-carrying authority confinement (#3246).",
        }
    if not py_validation_input_redacted_and_stdio_clean:
        return {
            "passed": False,
            "code": "MCP_PY_VALIDATION_SECRET_ECHO_OR_STDIO_HANG",
            "reason": "Python SDK must hide raw input values in validation errors (#3582) and exit cleanly on open stdin (#3595).",
        }
    if not ts_expected_resource_and_ajv_cached:
        return {
            "passed": False,
            "code": "MCP_TS_BEARER_RESOURCE_AUDIENCE_UNCHECKED_OR_AJV_DOS",
            "reason": "TypeScript SDK must enforce expectedResource in requireBearerAuth (#2952) and reuse compiled Ajv (#2950).",
        }
    return {
        "passed": True,
        "code": "MCP_SEP3246_AND_PY_TS_SECURITY_GUARDS_VERIFIED",
        "reason": "MCP SEP-3246 authority confinement, Python validation redaction, and TS bearer resource/Ajv cache verified.",
    }


def evaluate_mcp_go_rust_java_transport_guard(
    *,
    go_stream_subscription_cleared_and_null_preserved: bool,
    rust_streamable_http_response_bounded: bool,
    java_roots_capability_and_sse_line_separators_safe: bool,
) -> dict[str, Any]:
    """PR-14: go-sdk (#1290/#1285/#1283), rust-sdk (#1248/#1247/#1246), java-sdk (#1149/#1144/#1142)."""
    if not go_stream_subscription_cleared_and_null_preserved:
        return {
            "passed": False,
            "code": "MCP_GO_ORPHANED_SUBSCRIPTION_OR_NULL_STRIPPED",
            "reason": "Go SDK must clear resource subscriptions on stream end (#1283) and preserve explicit null content (#1285).",
        }
    if not rust_streamable_http_response_bounded:
        return {
            "passed": False,
            "code": "MCP_RUST_UNBOUNDED_HTTP_BUFFER_OOM_BLOCKED",
            "reason": "Rust SDK must bound buffered Streamable HTTP responses (#1246) and keep discover bootstrap-neutral (#1248).",
        }
    if not java_roots_capability_and_sse_line_separators_safe:
        return {
            "passed": False,
            "code": "MCP_JAVA_UNSUPPORTED_ROOTS_CALL_OR_SSE_UNICODE_TRUNCATION",
            "reason": "Java SDK must reject listRoots when unsupported (#1144) and preserve U+2028/U+2029/U+0085 in SSE (#1142).",
        }
    return {
        "passed": True,
        "code": "MCP_GO_RUST_JAVA_TRANSPORT_SAFETY_VERIFIED",
        "reason": "MCP Go subscription cleanup, Rust bounded HTTP buffers, and Java roots/SSE Unicode safety verified.",
    }


def evaluate_mcp_csharp_kotlin_swift_runtime_guard(
    *,
    csharp_degenerate_base64_header_safe: bool,
    kotlin_zod_hono_interop_hardened: bool,
    swift_actor_weak_self_and_codec_cached: bool,
) -> dict[str, Any]:
    """PR-15: csharp-sdk (#1805/#1804/#1803), kotlin-sdk (#1133/#1128/#1126), swift-sdk (#304/#299/#290)."""
    if not csharp_degenerate_base64_header_safe:
        return {
            "passed": False,
            "code": "MCP_CSHARP_DEGENERATE_BASE64_HEADER_THROW",
            "reason": "C# McpHeaderEncoder.DecodeValue must handle degenerate base64 wrappers without throwing (#1805).",
        }
    if not kotlin_zod_hono_interop_hardened:
        return {
            "passed": False,
            "code": "MCP_KOTLIN_INTEROP_DEPENDENCY_OR_API_DRIFT",
            "reason": "Kotlin SDK must enforce hardened Hono 4.13.13 / Zod 4.6.7 integration parity (#1133/#1126).",
        }
    if not swift_actor_weak_self_and_codec_cached:
        return {
            "passed": False,
            "code": "MCP_SWIFT_ACTOR_RETENTION_OR_CODEC_CHURN",
            "reason": "Swift SDK must cache Server JSON encoder/decoder and replace sendAndAwait cleanly (#304/#299).",
        }
    return {
        "passed": True,
        "code": "MCP_CSHARP_KOTLIN_SWIFT_RUNTIME_GUARDS_VERIFIED",
        "reason": "MCP C# base64 header decoder, Kotlin interop, and Swift actor/codec caching verified.",
    }


def evaluate_mcp_php_ruby_inspector_registry_guard(
    *,
    php_fiber_outside_http_and_event_loop_driven: bool,
    ruby_byte_frame_strip_and_unreadable_id_refusal: bool,
    inspector_mrtr_state_chained_and_orphan_secrets_purged: bool,
    registry_retired_k8up_schedule_removed: bool,
) -> dict[str, Any]:
    """PR-16: php-sdk (#616/#599), ruby-sdk (#625/#622/#620), inspector (#2610/#2600/#2597), registry (#1732/#1727)."""
    if not php_fiber_outside_http_and_event_loop_driven:
        return {
            "passed": False,
            "code": "MCP_PHP_NESTED_FIBER_HTTP_DEADLOCK",
            "reason": "PHP SDK must drive handler fibers via event loop (#616) and send HTTP outside request fibers (#599).",
        }
    if not ruby_byte_frame_strip_and_unreadable_id_refusal:
        return {
            "passed": False,
            "code": "MCP_RUBY_MULTIBYTE_FRAME_DESYNC_OR_ID_ECHO",
            "reason": "Ruby SDK must strip stdio frames as bytes (#625) and omit id when refusing unreadable request IDs (#622).",
        }
    if not inspector_mrtr_state_chained_and_orphan_secrets_purged:
        return {
            "passed": False,
            "code": "MCP_INSPECTOR_ORPHAN_SECRET_LEAK_OR_MRTR_BROKEN",
            "reason": "MCP Inspector must purge orphaned secret-store entries (#2600) and chain rotated MRTR requestState (#2610).",
        }
    if not registry_retired_k8up_schedule_removed:
        return {
            "passed": False,
            "code": "MCP_REGISTRY_RETIRED_K8UP_OPERATOR_CRASH",
            "reason": "MCP Registry must remove retired K8up schedules (#1727) and promote v1.8.4 safely (#1732).",
        }
    return {
        "passed": True,
        "code": "MCP_PHP_RUBY_INSPECTOR_REGISTRY_GUARDS_VERIFIED",
        "reason": "MCP PHP fiber loop, Ruby byte framing, Inspector secret purge/MRTR chaining, and Registry v1.8.4 verified.",
    }
