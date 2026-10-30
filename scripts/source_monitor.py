"""Record public source fingerprints and selected facts, never document bodies."""

import argparse
import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BEIJING = timezone(timedelta(hours=8))
MAX_BYTES = 4 * 1024 * 1024
ALLOWED_HOSTS = frozenset({
    "stripe.com", "docs.stripe.com", "developer.visa.com", "corporate.visa.com",
    "raw.githubusercontent.com", "ucp.dev", "ap2-protocol.org", "modelcontextprotocol.io",
    "a2a-protocol.org", "mpp.dev",
    "learn.microsoft.com",
    "sierra.ai", "personalagentprotocol.org",
})


class VisibleText(HTMLParser):
    """Extract visible text to reduce script and style hash noise."""

    def __init__(self) -> None:
        super().__init__()
        self.hidden_depth = 0
        self.fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.fragments.append(data)


@dataclass(frozen=True)
class Source:
    """An allowlisted primary source and its preferred machine-readable URL."""

    id: str
    url: str
    monitor_url: str


@dataclass(frozen=True)
class Observation:
    """An explicit fetch outcome; errors never count as unchanged content."""

    id: str
    url: str
    fetched_url: str
    status: str
    sha256: str | None
    change: str
    error: str | None = None
    policy_facts: dict[str, object] | None = None
    policy_change: str | None = None
    policy_error: str | None = None


def mcp_policy_facts(body: bytes) -> dict[str, object]:
    """Extract only the reviewed auth notice; changed wording requires human review."""
    lines: list[str] = []
    fence: tuple[str, int] | None = None
    for line in body.decode("utf-8").splitlines():
        line = re.sub(r"^>\s?", "", line)
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence = (marker[1][0], len(marker[1]))
            elif (
                marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                and not marker[2].strip()
            ):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    text = "\n".join(lines)
    headings = list(re.finditer(
        r"(?m)^#### Update API key authentication by ([^\n]+)\n", text
    ))
    if len(headings) != 1:
        raise ValueError("Expected one MCP auth notice; missing or duplicate notice needs review.")
    heading = headings[0]
    section = re.split(r"(?m)^#{1,6} ", text[heading.end():], maxsplit=1)[0]
    notice = re.sub(r"\s+", " ", section).strip()
    deadline = _parse_reviewed_mcp_notice(heading[1].strip(), notice)
    return {
        "parser_version": "stripe-mcp-auth-notice-v1",
        "deadline": deadline.isoformat(),
        "full_access_secret_rejected": True,
        "restricted_without_agent_tag_rejected": True,
        "replacement_oauth": True,
        "replacement_agent_key": True,
        "rejection_http_status": 401,
        "oauth_discovery_challenge": True,
        "cutoff_time": None,
        "cutoff_timezone": None,
    }


def stripe_spt_facts(body: bytes) -> dict[str, object]:
    """Extract stable Stripe SPT contract facts, excluding volatile sample timestamps."""
    text = body.decode("utf-8")
    versions = set(re.findall(r"Stripe-Version:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}\.preview)", text))
    if len(versions) != 1:
        raise ValueError("Expected one Stripe-Version preview marker in Stripe SPT docs.")
    version = next(iter(versions))
    country_codes = _extract_supported_country_codes(text)
    countries_digest = hashlib.sha256(",".join(country_codes).encode("ascii")).hexdigest()
    return {
        "parser_version": "stripe-spt-facts-v1",
        "api_version": version,
        "supported_country_count": len(country_codes),
        "supported_country_codes_sha256": countries_digest,
        "has_recurring_interval": "recurring_interval" in text,
        "forbids_setup_future_usage": (
            "setup_future_usage" in text
            and "are not allowed with shared payment tokens" in text
        ),
        "has_deactivated_webhook_event": "shared_payment.granted_token.deactivated" in text,
    }


def _extract_supported_country_codes(text: str) -> list[str]:
    """Read the published country list block and return its ordered alpha-2 codes."""
    countries_block = re.search(
        r"(?ms)^### View all supported countries\s*\n(?P<items>(?:- [A-Z]{2}\s*\n)+)",
        text,
    )
    if countries_block is None:
        raise ValueError("Stripe SPT docs missing supported-country list block.")
    country_codes = re.findall(r"(?m)^- ([A-Z]{2})\s*$", countries_block.group("items"))
    if not country_codes:
        raise ValueError("Stripe SPT docs supported-country list is empty.")
    return country_codes


def stripe_spt_connect_facts(body: bytes) -> dict[str, object]:
    """Extract stable Connect-tab SPT contract facts without inferring account state."""
    text = body.decode("utf-8")
    country_codes = _extract_supported_country_codes(text)
    countries_digest = hashlib.sha256(",".join(country_codes).encode("ascii")).hexdigest()
    return {
        "parser_version": "stripe-spt-connect-facts-v1",
        "supported_country_count": len(country_codes),
        "supported_country_codes_sha256": countries_digest,
        "has_connect_platforms_section": "# Connect platforms" in text,
        "has_network_business_profile": "seller_details[network_business_profile]" in text,
        "has_shared_payment_granted_token": "payment_method_data[shared_payment_granted_token]" in text,
        "has_stripe_account_header": "Stripe-Account" in text,
        "covers_direct_destination_separate_charges": all(
            marker in text
            for marker in (
                "Direct charge",
                "Destination charge",
                "Separate charges and transfers",
            )
        ),
    }


def _parse_reviewed_date(raw: str) -> date:
    """Parse human-reviewed US ('%B %d, %Y') or UK ('%d %B %Y') calendar dates."""
    for fmt in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("MCP auth notice has an invalid calendar date; review required.")


def _parse_reviewed_mcp_notice(heading_raw: str, notice: str) -> date:
    """Parse only human-reviewed Stripe MCP auth notice grammars and verify date consistency."""
    october_match = re.fullmatch(
        r"Beginning (\d{1,2} [A-Z][a-z]+ \d{4}), Stripe MCP no longer accepts "
        r"full-access secret keys or restricted API keys without the Agent tag\. "
        r"Before then, replace these keys with newly created Agent Keys or reconnect with OAuth\. "
        r"Requests using an unsupported key receive a `401` response with an OAuth discovery challenge\.",
        notice,
    )
    if october_match is not None:
        try:
            deadline = datetime.strptime(october_match[1], "%d %B %Y").date()
            heading_date = datetime.strptime(heading_raw, "%d %B %Y").date()
        except ValueError as error:
            raise ValueError("MCP auth notice has an invalid calendar date; review required.") from error
        if deadline != heading_date:
            raise ValueError("MCP auth notice dates conflict; review required.")
        return deadline

    november_match = re.fullmatch(
        r"Migrate by (\d{1,2} [A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{1,2}, \d{4})\. Starting in ([A-Z][a-z]+), Stripe MCP will stop accepting "
        r"full-access secret keys and restricted API keys without the Agent tag\. "
        r"Replace these keys with newly created agent API keys or reconnect with OAuth\. "
        r"Requests using an unsupported key receive a `401` response with an OAuth discovery challenge\.",
        notice,
    )
    if november_match is not None:
        deadline = _parse_reviewed_date(november_match[1])
        heading_date = _parse_reviewed_date(heading_raw)
        next_day = deadline + timedelta(days=1)
        if (
            november_match[1] != heading_raw
            or deadline != heading_date
            or next_day.day != 1
            or next_day.strftime("%B") != november_match[2]
        ):
            raise ValueError("MCP auth notice dates conflict; review required.")
        return deadline

    raise ValueError("MCP auth notice wording changed; selected facts remain unverified.")


def validate_url(url: str) -> None:
    """Reject credentials, non-HTTPS URLs and hosts outside the source allowlist."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username or parsed.password or parsed.port not in {None, 443}
    ):
        raise ValueError(f"Source URL is not an allowed public HTTPS endpoint: {url!r}")


def _normalize_source_noise(source_id: str | None, text: str) -> str:
    """Remove source-known volatile examples while preserving semantic content."""
    if source_id == "stripe-spt":
        text = re.sub(
            r'("expires_at"\s*:\s*)\d{10,13}',
            r'\1<dynamic-unix-timestamp>',
            text,
        )
    return text


def fingerprint(body: bytes, content_type: str, *, source_id: str | None = None) -> str:
    """Hash normalized source text, not a claim about a new product release."""
    text = body.decode("utf-8")
    if "html" in content_type:
        parser = VisibleText()
        parser.feed(text)
        text = " ".join(parser.fragments)
    text = _normalize_source_noise(source_id, text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("Fetched source contains no usable text; check its monitor URL.")
    return hashlib.sha256(text.encode()).hexdigest()


def observe(
    source: Source, previous_hash: str | None,
    previous_policy: dict[str, object] | None = None,
) -> Observation:
    """Fetch one source with bounded size and report failure with context."""
    validate_url(source.monitor_url)
    request = Request(
        source.monitor_url,
        headers={
            "User-Agent": "AgenticCommerceLab/0.1",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    last_error: Exception | None = None
    fetched_url = source.monitor_url
    body = b""
    digest = ""
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                fetched_url = response.geturl()
                validate_url(fetched_url)
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError("Source exceeds the 4 MiB research fetch limit.")
                digest = fingerprint(
                    body, response.headers.get("Content-Type", "text/plain"),
                    source_id=source.id,
                )
                last_error = None
                break
        except (URLError, HTTPException, OSError, UnicodeError, ValueError) as error:
            last_error = error
            if isinstance(error, (HTTPError, UnicodeError, ValueError)):
                break
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    if last_error is not None:
        return Observation(
            source.id, source.url, source.monitor_url, "error", None, "unknown",
            f"{type(last_error).__name__}: {last_error}",
            policy_change="unknown" if source.id == "stripe-mcp" else None,
            policy_error="MCP auth facts unavailable because source fetch failed."
            if source.id == "stripe-mcp" else None,
        )
    change = "baseline" if previous_hash is None else (
        "unchanged" if digest == previous_hash else "changed"
    )
    facts = None
    policy_change = None
    policy_error = None
    if source.id == "stripe-mcp":
        try:
            if fetched_url != "https://docs.stripe.com/mcp.md":
                raise ValueError("MCP auth extraction requires the reviewed official Markdown URL.")
            facts = mcp_policy_facts(body)
            policy_change = "baseline" if previous_policy is None else (
                "unchanged" if facts == previous_policy else "changed"
            )
        except ValueError as error:
            policy_change = "unknown"
            policy_error = str(error)
    if source.id == "stripe-spt":
        try:
            if fetched_url != source.monitor_url:
                raise ValueError("Stripe SPT fact extraction requires the reviewed seller Markdown URL.")
            facts = stripe_spt_facts(body)
            policy_change = "baseline" if previous_policy is None else (
                "unchanged" if facts == previous_policy else "changed"
            )
        except ValueError as error:
            policy_change = "unknown"
            policy_error = str(error)
    if source.id == "stripe-spt-connect":
        try:
            if fetched_url != source.monitor_url:
                raise ValueError("Stripe SPT Connect fact extraction requires the reviewed connect Markdown URL.")
            facts = stripe_spt_connect_facts(body)
            policy_change = "baseline" if previous_policy is None else (
                "unchanged" if facts == previous_policy else "changed"
            )
        except ValueError as error:
            policy_change = "unknown"
            policy_error = str(error)
    return Observation(
        source.id, source.url, fetched_url, "ok", digest, change,
        policy_facts=facts, policy_change=policy_change, policy_error=policy_error,
    )


def load_sources(path: Path) -> list[Source]:
    """Load the registry and reject ambiguous IDs or nonpublic fetch targets."""
    registry = json.loads(path.read_text(encoding="utf-8"))
    sources = [
        Source(item["id"], item["url"], item.get("monitor_url", item["url"]))
        for item in registry["sources"]
    ]
    if not sources or len({source.id for source in sources}) != len(sources):
        raise ValueError("Source registry must have nonempty, unique source IDs.")
    for source in sources:
        validate_url(source.url)
        validate_url(source.monitor_url)
    return sources


def previous_hashes(directory: Path, *, before_date: str | None = None) -> dict[str, str]:
    """Retain each source's latest successful hash across failed daily fetches."""
    hashes: dict[str, str] = {}
    for path in sorted(directory.glob("*-sources.json")):
        if before_date is not None and path.name[:10] >= before_date:
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        for item in report["observations"]:
            if item["status"] == "ok" and item["sha256"]:
                hashes[item["id"]] = item["sha256"]
    return hashes


def previous_policy_facts(directory: Path, *, before_date: str) -> dict[str, object] | None:
    """Use the last successful fact observation, not today's rerun or a failed parse."""
    return previous_source_facts(
        directory, before_date=before_date,
        source_id="stripe-mcp", parser_version="stripe-mcp-auth-notice-v1",
    )


def previous_source_facts(
    directory: Path, *, before_date: str, source_id: str, parser_version: str,
) -> dict[str, object] | None:
    """Return the latest successful selected facts for one source/parser pair."""
    for path in sorted(directory.glob("*-sources.json"), reverse=True):
        if path.name[:10] >= before_date:
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        for item in report["observations"]:
            facts = item.get("policy_facts")
            if (
                item["id"] == source_id and item["status"] == "ok"
                and not item.get("policy_error") and isinstance(facts, dict)
                and facts.get("parser_version") == parser_version
            ):
                return facts
    return None


def spt_country_list_check(observations: list[Observation]) -> dict[str, object]:
    """Compare seller/connect SPT country-list facts without asserting release conclusions."""
    by_id = {item.id: item for item in observations}
    seller = by_id.get("stripe-spt")
    connect = by_id.get("stripe-spt-connect")
    base = {"check_id": "stripe-spt-country-list-parity"}
    if seller is None or connect is None:
        return {**base, "status": "unavailable", "reason": "seller_or_connect_source_missing"}
    if (
        seller.status != "ok" or connect.status != "ok"
        or seller.policy_error or connect.policy_error
        or not isinstance(seller.policy_facts, dict)
        or not isinstance(connect.policy_facts, dict)
    ):
        return {**base, "status": "unavailable", "reason": "required_selected_facts_unavailable"}
    seller_count = seller.policy_facts.get("supported_country_count")
    connect_count = connect.policy_facts.get("supported_country_count")
    seller_hash = seller.policy_facts.get("supported_country_codes_sha256")
    connect_hash = connect.policy_facts.get("supported_country_codes_sha256")
    if None in {seller_count, connect_count, seller_hash, connect_hash}:
        return {**base, "status": "unavailable", "reason": "required_country_fields_missing"}
    if seller_count == connect_count and seller_hash == connect_hash:
        return {
            **base,
            "status": "consistent",
            "supported_country_count": int(seller_count),
            "supported_country_codes_sha256": str(seller_hash),
        }
    return {
        **base,
        "status": "mismatch",
        "seller_supported_country_count": int(seller_count),
        "connect_supported_country_count": int(connect_count),
        "seller_supported_country_codes_sha256": str(seller_hash),
        "connect_supported_country_codes_sha256": str(connect_hash),
    }


def spt_connect_marker_check(observations: list[Observation]) -> dict[str, object]:
    """Verify Connect-tab required SPT markers are present in selected facts."""
    connect = next((item for item in observations if item.id == "stripe-spt-connect"), None)
    base = {"check_id": "stripe-spt-connect-required-markers"}
    if connect is None:
        return {**base, "status": "unavailable", "reason": "connect_source_missing"}
    if (
        connect.status != "ok" or connect.policy_error
        or not isinstance(connect.policy_facts, dict)
    ):
        return {**base, "status": "unavailable", "reason": "connect_selected_facts_unavailable"}
    expected_true_markers = (
        "has_connect_platforms_section",
        "has_network_business_profile",
        "has_shared_payment_granted_token",
        "has_stripe_account_header",
        "covers_direct_destination_separate_charges",
    )
    missing = [
        marker for marker in expected_true_markers
        if connect.policy_facts.get(marker) is not True
    ]
    if missing:
        return {**base, "status": "mismatch", "missing_markers": missing}
    return {**base, "status": "consistent"}


def spt_parser_version_check(observations: list[Observation]) -> dict[str, object]:
    """Ensure seller/connect selected-facts parser versions stay on reviewed grammars."""
    by_id = {item.id: item for item in observations}
    seller = by_id.get("stripe-spt")
    connect = by_id.get("stripe-spt-connect")
    base = {"check_id": "stripe-spt-parser-version-parity"}
    if seller is None or connect is None:
        return {**base, "status": "unavailable", "reason": "seller_or_connect_source_missing"}
    if (
        seller.status != "ok" or connect.status != "ok"
        or seller.policy_error or connect.policy_error
        or not isinstance(seller.policy_facts, dict)
        or not isinstance(connect.policy_facts, dict)
    ):
        return {**base, "status": "unavailable", "reason": "required_selected_facts_unavailable"}
    expected = {
        "stripe-spt": "stripe-spt-facts-v1",
        "stripe-spt-connect": "stripe-spt-connect-facts-v1",
    }
    actual = {
        "stripe-spt": seller.policy_facts.get("parser_version"),
        "stripe-spt-connect": connect.policy_facts.get("parser_version"),
    }
    if actual != expected:
        return {**base, "status": "mismatch", "expected": expected, "actual": actual}
    return {**base, "status": "consistent"}


def summarize_cross_source_checks(checks: list[dict[str, object]]) -> dict[str, int | bool]:
    """Count check outcomes and expose whether any mismatch currently blocks the run."""
    summary = {"total": 0, "consistent": 0, "mismatch": 0, "unavailable": 0}
    for check in checks:
        if not isinstance(check, dict):
            continue
        status = check.get("status")
        if status in summary:
            summary[status] += 1
            summary["total"] += 1
    return {**summary, "blocking": summary["mismatch"] > 0}


def index_cross_source_statuses(checks: list[dict[str, object]]) -> dict[str, str]:
    """Build a stable check_id -> status map for machine consumers."""
    statuses: dict[str, str] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        check_id = check.get("check_id")
        status = check.get("status")
        if isinstance(check_id, str) and isinstance(status, str):
            statuses[check_id] = status
    return statuses


def summarize_gate_health(
    observations: list[Observation], cross_source_summary: dict[str, int | bool],
) -> dict[str, int | bool | list[str]]:
    """Expose one machine-readable run gate that combines fetch/policy/check failures."""
    observation_errors = sum(item.status == "error" for item in observations)
    policy_errors = sum(bool(item.policy_error) for item in observations)
    cross_source_mismatch = int(cross_source_summary.get("mismatch", 0))
    blocking_reasons = [
        reason for reason, count in (
            ("observation_errors", observation_errors),
            ("policy_errors", policy_errors),
            ("cross_source_mismatch", cross_source_mismatch),
        )
        if count > 0
    ]
    blocking = bool(
        observation_errors
        or policy_errors
        or cross_source_summary.get("blocking")
    )
    return {
        "observation_errors": observation_errors,
        "policy_errors": policy_errors,
        "cross_source_mismatch": cross_source_mismatch,
        "blocking_reasons": blocking_reasons,
        "blocking": blocking,
    }


def main() -> int:
    """Write a dated report; return nonzero on fetch or selected-fact parse failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("research") / "sources.json")
    parser.add_argument("--output-dir", type=Path, default=Path("research") / "daily")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sources = load_sources(args.registry)
    now = datetime.now(BEIJING)
    previous = previous_hashes(args.output_dir, before_date=str(now.date()))
    previous_facts = {
        "stripe-mcp": previous_policy_facts(args.output_dir, before_date=str(now.date())),
        "stripe-spt": previous_source_facts(
            args.output_dir, before_date=str(now.date()),
            source_id="stripe-spt", parser_version="stripe-spt-facts-v1",
        ),
        "stripe-spt-connect": previous_source_facts(
            args.output_dir, before_date=str(now.date()),
            source_id="stripe-spt-connect", parser_version="stripe-spt-connect-facts-v1",
        ),
    }
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as executor:
        observations = list(
            executor.map(
                lambda source: observe(
                    source, previous.get(source.id), previous_facts.get(source.id),
                ),
                sources,
            )
        )
    target = args.output_dir / f"{now.date()}-sources.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cross_source_checks = [
        spt_country_list_check(observations),
        spt_connect_marker_check(observations),
        spt_parser_version_check(observations),
    ]
    cross_source_statuses = index_cross_source_statuses(cross_source_checks)
    cross_source_summary = summarize_cross_source_checks(cross_source_checks)
    gate_health = summarize_gate_health(observations, cross_source_summary)
    report = {
        "checked_at": now.isoformat(),
        "kind": "source-fingerprint-monitor-not-research-conclusions",
        "normalization": "utf8-visible-html-text-or-markdown-whitespace-v2-with-source-noise-filters",
        "policy_scope": "Selected Stripe MCP auth notice facts plus Stripe SPT seller/connect stable contract facts only; not live access or a release claim.",
        "cross_source_checks": cross_source_checks,
        "cross_source_statuses": cross_source_statuses,
        "cross_source_summary": cross_source_summary,
        "gate_health": gate_health,
        "observations": [asdict(observation) for observation in observations],
    }
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    for observation in observations:
        logging.info(json.dumps(asdict(observation), ensure_ascii=False))
    return int(gate_health["blocking"])


if __name__ == "__main__":
    raise SystemExit(main())
