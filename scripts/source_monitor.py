"""Record public source fingerprints, never third-party document bodies."""

import argparse
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BEIJING = timezone(timedelta(hours=8))
MAX_BYTES = 4 * 1024 * 1024
ALLOWED_HOSTS = frozenset({
    "stripe.com", "docs.stripe.com", "developer.visa.com", "corporate.visa.com",
    "raw.githubusercontent.com", "ucp.dev", "ap2-protocol.org", "modelcontextprotocol.io",
    "a2a-protocol.org", "mpp.dev",
    "learn.microsoft.com",
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


def validate_url(url: str) -> None:
    """Reject credentials, non-HTTPS URLs and hosts outside the source allowlist."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username or parsed.password or parsed.port not in {None, 443}
    ):
        raise ValueError(f"Source URL is not an allowed public HTTPS endpoint: {url!r}")


def fingerprint(body: bytes, content_type: str) -> str:
    """Hash normalized source text, not a claim about a new product release."""
    text = body.decode("utf-8")
    if "html" in content_type:
        parser = VisibleText()
        parser.feed(text)
        text = " ".join(parser.fragments)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("Fetched source contains no usable text; check its monitor URL.")
    return hashlib.sha256(text.encode()).hexdigest()


def observe(source: Source, previous_hash: str | None) -> Observation:
    """Fetch one source with bounded size and report failure with context."""
    validate_url(source.monitor_url)
    request = Request(source.monitor_url, headers={"User-Agent": "AgenticCommerceLab/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            fetched_url = response.geturl()
            validate_url(fetched_url)
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Source exceeds the 4 MiB research fetch limit.")
            digest = fingerprint(body, response.headers.get("Content-Type", "text/plain"))
    except (URLError, OSError, UnicodeError, ValueError) as error:
        return Observation(
            source.id, source.url, source.monitor_url, "error", None, "unknown",
            f"{type(error).__name__}: {error}",
        )
    change = "baseline" if previous_hash is None else (
        "unchanged" if digest == previous_hash else "changed"
    )
    return Observation(source.id, source.url, fetched_url, "ok", digest, change)


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


def main() -> int:
    """Write a dated fingerprint report; return nonzero on any fetch failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("research") / "sources.json")
    parser.add_argument("--output-dir", type=Path, default=Path("research") / "daily")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sources = load_sources(args.registry)
    now = datetime.now(BEIJING)
    previous = previous_hashes(args.output_dir, before_date=str(now.date()))
    observations = [observe(source, previous.get(source.id)) for source in sources]
    target = args.output_dir / f"{now.date()}-sources.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "checked_at": now.isoformat(),
        "kind": "source-fingerprint-monitor-not-research-conclusions",
        "normalization": "utf8-visible-html-text-or-markdown-whitespace-v1",
        "observations": [asdict(observation) for observation in observations],
    }
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    for observation in observations:
        logging.info(json.dumps(asdict(observation), ensure_ascii=False))
    return int(any(observation.status == "error" for observation in observations))


if __name__ == "__main__":
    raise SystemExit(main())
