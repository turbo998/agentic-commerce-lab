"""Observe public sources; do not infer product releases from content changes."""

import argparse
import hashlib
import json
import re
import socket
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


MAX_BYTES = 2_000_000


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def digest(body: bytes, content_type: str) -> str:
    text = body.decode("utf-8", errors="replace")
    if "html" in content_type:
        parser = VisibleText()
        parser.feed(text)
        text = " ".join(parser.parts)
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        raise ValueError("source contains no visible text")
    return hashlib.sha256(normalized.encode()).hexdigest()


def fetch(source: dict) -> str:
    url = source.get("monitor_url", source["url"])
    if urlsplit(url).scheme != "https":
        raise ValueError("public sources must use HTTPS")
    request = Request(url, headers={"User-Agent": "agentic-commerce-lab-source-monitor/1.0"})
    with urlopen(request, timeout=25) as response:
        if urlsplit(response.url).scheme != "https":
            raise ValueError("source redirected outside HTTPS")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("source exceeds monitoring size limit")
        return digest(body, response.headers.get("Content-Type", "text/plain"))


def observe(sources: list[dict], baseline: dict, fetcher=fetch) -> tuple[list, dict]:
    observations = []
    updated = dict(baseline)
    for source in sources:
        source_id = source["id"]
        try:
            fingerprint = fetcher(source)
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError, ValueError) as exc:
            # Only an error class/code is published, never remote response bodies.
            error = type(exc).__name__
            if isinstance(exc, HTTPError):
                error += f":{exc.code}"
            observations.append({"id": source_id, "status": "error", "error": error})
            continue
        previous = baseline.get(source_id)
        status = "new_baseline" if previous is None else (
            "unchanged" if previous == fingerprint else "changed"
        )
        observations.append({"id": source_id, "status": status, "sha256": fingerprint})
        updated[source_id] = fingerprint
    return observations, updated


def report(day: str, sources: list[dict], observations: list[dict]) -> str:
    by_id = {source["id"]: source for source in sources}
    lines = [
        f"# Daily source observations — {day}", "",
        "> Automated observations, not a completed architecture research report. "
        "Content changes are review candidates, not verified releases.", "",
        "| Source | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for observation in observations:
        source = by_id[observation["id"]]
        evidence = observation.get("sha256", observation.get("error"))
        lines.append(
            f"| [{source['id']}]({source['url']}) | {observation['status']} | `{evidence}` |"
        )
    lines += [
        "", "## Required research follow-through", "",
        "Review changed sources against the last accepted baseline. Verify the publisher, "
        "publication date, version, regional eligibility and preview status. Record an "
        "original Chinese synthesis in research/daily/YYYY-MM-DD.md, including architecture "
        "impact, scenarios, asset changes and unresolved questions. Do not copy source pages "
        "or treat unchanged/failed observations as proof that no announcements occurred.", "",
        "HTML navigation, timestamps or anti-bot pages can affect hashes. A successful HTTP "
        "response alone does not prove that the intended documentation was retrieved. "
        "Errors preserve the previous baseline and cause a nonzero exit status.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=Path("research/sources.json"))
    parser.add_argument("--state", type=Path, default=Path("research/monitor-state.json"))
    parser.add_argument("--output", type=Path, default=Path("research/observations"))
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        parser.error("--date must be YYYY-MM-DD")
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        parser.error("--date must be a valid calendar date")
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    ids = [source["id"] for source in sources]
    if len(ids) != len(set(ids)):
        parser.error("source IDs must be unique")
    baseline = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {}
    observations, updated = observe(sources, baseline)
    args.output.mkdir(parents=True, exist_ok=True)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.date}.json").write_text(
        json.dumps(observations, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / f"{args.date}.md").write_text(
        report(args.date, sources, observations), encoding="utf-8"
    )
    args.state.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = sum(item["status"] == "error" for item in observations)
    print(json.dumps({"sources": len(sources), "errors": errors, "date": args.date}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
