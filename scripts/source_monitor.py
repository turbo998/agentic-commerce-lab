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
    for path in sorted(directory.glob("*-sources.json"), reverse=True):
        if path.name[:10] >= before_date:
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        for item in report["observations"]:
            facts = item.get("policy_facts")
            if (
                item["id"] == "stripe-mcp" and item["status"] == "ok"
                and not item.get("policy_error") and isinstance(facts, dict)
                and facts.get("parser_version") == "stripe-mcp-auth-notice-v1"
            ):
                return facts
    return None


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
    policy = previous_policy_facts(args.output_dir, before_date=str(now.date()))
    with ThreadPoolExecutor(max_workers=min(8, len(sources))) as executor:
        observations = list(
            executor.map(lambda source: observe(source, previous.get(source.id), policy), sources)
        )
    target = args.output_dir / f"{now.date()}-sources.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "checked_at": now.isoformat(),
        "kind": "source-fingerprint-monitor-not-research-conclusions",
        "normalization": "utf8-visible-html-text-or-markdown-whitespace-v2-with-source-noise-filters",
        "policy_scope": "Selected Stripe MCP auth notice facts only; not live access or a release claim.",
        "observations": [asdict(observation) for observation in observations],
    }
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    for observation in observations:
        logging.info(json.dumps(asdict(observation), ensure_ascii=False))
    return int(any(
        observation.status == "error" or observation.policy_error
        for observation in observations
    ))


if __name__ == "__main__":
    raise SystemExit(main())
