"""Offline source-registry and daily-note integrity checks, not fact checking."""

from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def _date(value: str, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        errors.append(f"{label}: date must use YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: invalid calendar date")
        return None


def validate(root: Path = ROOT) -> list[str]:
    registry = json.loads((root / "research" / "sources.json").read_text(encoding="utf-8"))
    errors = []
    reviewed = _date(registry["reviewed_on"], "reviewed_on", errors)
    if reviewed is None:
        return errors
    identifiers = set()
    kinds = {"announcement", "documentation", "specification", "reference-code"}
    for source in registry["sources"]:
        identifier = source["id"]
        if not re.fullmatch(r"S\d{2,}", identifier) or identifier in identifiers:
            errors.append(f"invalid or duplicate source ID: {identifier}")
        identifiers.add(identifier)
        url = urlparse(source["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            errors.append(f"{identifier}: HTTPS source URL required")
        if source["kind"] not in kinds:
            errors.append(f"{identifier}: unknown evidence kind")
        for field in ("publisher", "title", "observation"):
            if not source[field].strip():
                errors.append(f"{identifier}: missing {field}")
        published = source["published_on"]
        if published is not None:
            published_date = _date(published, f"{identifier}: published_on", errors)
            if published_date is not None and published_date > reviewed:
                errors.append(f"{identifier}: publication after review")
        if "revision" in source and not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
            errors.append(f"{identifier}: invalid Git revision")
        if "spec_version" in source:
            version = _date(source["spec_version"], f"{identifier}: spec_version", errors)
            if version is not None and version > reviewed:
                errors.append(f"{identifier}: version after review")
    notes = sorted((root / "research" / "daily").glob("*.md"))
    if not notes:
        errors.append("no daily notes")
    for note in notes:
        note_date = _date(note.stem, note.name, errors)
        if note_date is not None and note_date > reviewed:
            errors.append(f"{note.name}: note after latest review")
        content = note.read_text(encoding="utf-8")
        if not content.startswith(f"# {note.stem}"):
            errors.append(f"{note.name}: heading/date mismatch")
    for note in [*notes, *(root / "docs").glob("*.md")]:
        content = note.read_text(encoding="utf-8")
        references = set(re.findall(r"\bS\d{2,}\b", content))
        for start, end in re.findall(r"\bS(\d{2,})[–-]S(\d{2,})\b", content):
            if int(end) < int(start):
                errors.append(f"{note.name}: reversed source range S{start}-S{end}")
            else:
                references.update(f"S{number:02}" for number in range(int(start), int(end) + 1))
        for identifier in sorted(references):
            if identifier not in identifiers:
                errors.append(f"{note.name}: unknown source {identifier}")
    return errors


def main() -> None:
    try:
        errors = validate()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Research registry cannot be validated: {error}") from error
    if errors:
        raise SystemExit("\n".join(errors))
    print("Research registry and note integrity: OK (offline; not factual verification)")


if __name__ == "__main__":
    main()
