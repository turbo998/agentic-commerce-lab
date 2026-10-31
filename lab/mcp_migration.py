"""Offline Stripe MCP auth inventory: metadata only, never credentials or API calls."""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

if __package__:
    from .json_members import unique_members
else:
    from json_members import unique_members

PREVIOUS_DEADLINE = date(2026, 10, 31)
DEADLINE = date(2026, 11, 30)
ENFORCEMENT_STARTS = date(2026, 12, 1)
POLICY_CHECKED_ON = date(2026, 10, 23)
SOURCE_URL = "https://docs.stripe.com/mcp"
MAX_BYTES = 64 * 1024
SOURCE_REPORT_MAX_BYTES = 4 * 1024 * 1024
MCP_FACTS_PARSER_VERSION = "stripe-mcp-auth-notice-v1"
AuthMethod = Literal[
    "oauth", "agent_key", "full_access_secret", "restricted_without_agent_tag"
]
FindingStatus = Literal[
    "recorded_supported_unverified",
    "migration_required",
    "blocked_by_documented_policy",
]
DeadlineWindowPhase = Literal[
    "before_previous_deadline",
    "contradiction_window",
    "on_or_after_deadline",
]
SUPPORTED_AUTH = frozenset({"oauth", "agent_key"})
KNOWN_AUTH = SUPPORTED_AUTH | {"full_access_secret", "restricted_without_agent_tag"}
VALID_FINDING_STATUSES = frozenset({
    "recorded_supported_unverified",
    "migration_required",
    "blocked_by_documented_policy",
})
VALID_WINDOW_PHASES = frozenset({
    "before_previous_deadline",
    "contradiction_window",
    "on_or_after_deadline",
})


@dataclass(frozen=True)
class Client:
    """An operator-declared alias, environment and auth class, not account evidence."""

    client_id: str
    environment: Literal["sandbox", "live"]
    auth_method: AuthMethod

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, str) or not re.fullmatch(
            r"[a-z][a-z0-9-]{0,63}", self.client_id
        ):
            raise ValueError("client_id must be a lowercase alias, not a key or account ID.")
        if not isinstance(self.environment, str) or self.environment not in {"sandbox", "live"}:
            raise ValueError("environment must be sandbox or live.")
        if not isinstance(self.auth_method, str) or self.auth_method not in KNOWN_AUTH:
            raise ValueError("auth_method must be a documented auth class; values are not keys.")


@dataclass(frozen=True)
class Finding:
    client_id: str
    environment: str
    auth_method: str
    status: FindingStatus
    action: str

    def __post_init__(self) -> None:
        Client(self.client_id, self.environment, self.auth_method)  # type: ignore[arg-type]
        if not isinstance(self.status, str) or self.status not in VALID_FINDING_STATUSES:
            raise ValueError("status must be a documented MCP migration finding status.")
        if not isinstance(self.action, str) or not self.action.strip():
            raise ValueError("action must be a nonempty string.")
        if self.auth_method in SUPPORTED_AUTH:
            if self.status != "recorded_supported_unverified":
                raise ValueError(
                    "Supported auth methods must have status recorded_supported_unverified."
                )
        elif self.status == "recorded_supported_unverified":
            raise ValueError(
                "Legacy auth methods cannot have status recorded_supported_unverified."
            )


@dataclass(frozen=True)
class DualDeadlineFinding:
    """Offline dual-deadline evaluation across the 2026-10-31 vs. 2026-11-30 contradiction."""

    client_id: str
    environment: Literal["sandbox", "live"]
    auth_method: AuthMethod
    as_of: date
    previous_deadline: date
    deadline: date
    window_phase: DeadlineWindowPhase
    primary_status: FindingStatus
    strict_previous_status: FindingStatus
    contradiction_exposed: bool
    action: str

    def __post_init__(self) -> None:
        client = Client(self.client_id, self.environment, self.auth_method)
        expected_phase = classify_deadline_window(
            as_of=self.as_of,
            deadline=self.deadline,
            previous_deadline=self.previous_deadline,
        )
        if not isinstance(self.window_phase, str) or self.window_phase != expected_phase:
            raise ValueError("window_phase does not match as_of and deadline boundaries.")
        expected_primary = assess(client, as_of=self.as_of, deadline=self.deadline)
        expected_strict = assess(client, as_of=self.as_of, deadline=self.previous_deadline)
        if self.primary_status != expected_primary.status:
            raise ValueError("primary_status does not match deadline assessment.")
        if self.strict_previous_status != expected_strict.status:
            raise ValueError("strict_previous_status does not match previous_deadline assessment.")
        if type(self.contradiction_exposed) is not bool:
            raise ValueError("contradiction_exposed must be a bool.")
        if self.contradiction_exposed != (expected_primary.status != expected_strict.status):
            raise ValueError(
                "contradiction_exposed must equal (primary_status != strict_previous_status)."
            )
        if not isinstance(self.action, str) or not self.action.strip():
            raise ValueError("action must be a nonempty string.")


def load_inventory(path: Path) -> list[Client]:
    """Accept a small, strict metadata document with no credential fields."""
    if not isinstance(path, Path):
        raise ValueError("Inventory path must be a Path.")
    with path.open("rb") as stream:
        body = stream.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("Inventory exceeds the 64 KiB metadata limit.")
    payload = json.loads(body.decode("utf-8"), object_pairs_hook=unique_members)
    if not isinstance(payload, dict) or set(payload) != {"clients"}:
        raise ValueError("Inventory must contain only a clients array; never include secrets.")
    rows = payload["clients"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Inventory requires a nonempty clients array.")
    clients: list[Client] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"client_id", "environment", "auth_method"}:
            raise ValueError("Each client requires only client_id, environment and auth_method.")
        client = Client(**row)
        identity = (client.client_id, client.environment)
        if identity in seen:
            raise ValueError("Duplicate client alias within the same environment.")
        seen.add(identity)
        clients.append(client)
    return clients


def load_deadline_from_source_report(path: Path) -> tuple[date, date, str]:
    """Load Stripe MCP selected-facts deadline from a source-monitor daily report."""
    if not isinstance(path, Path):
        raise ValueError("Source report path must be a Path.")
    with path.open("rb") as stream:
        body = stream.read(SOURCE_REPORT_MAX_BYTES + 1)
    if len(body) > SOURCE_REPORT_MAX_BYTES:
        raise ValueError("Source report exceeds the 4 MiB metadata limit.")
    payload = json.loads(body.decode("utf-8"), object_pairs_hook=unique_members)
    if not isinstance(payload, dict):
        raise ValueError("Source report must be a JSON object.")
    checked_at_raw = payload.get("checked_at")
    try:
        checked_on = datetime.fromisoformat(checked_at_raw).date()
    except (TypeError, ValueError) as error:
        raise ValueError("Source report checked_at must be an ISO datetime string.") from error
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("Source report observations must be an array.")
    matching: list[dict[str, object]] = []
    for row in observations:
        if not isinstance(row, dict):
            continue
        facts = row.get("policy_facts")
        if (
            row.get("id") == "stripe-mcp"
            and row.get("status") == "ok"
            and not row.get("policy_error")
            and isinstance(facts, dict)
            and facts.get("parser_version") == MCP_FACTS_PARSER_VERSION
        ):
            matching.append(facts)
    if len(matching) != 1:
        raise ValueError("Source report must contain one successful stripe-mcp selected-facts row.")
    deadline_raw = matching[0].get("deadline")
    try:
        deadline = date.fromisoformat(deadline_raw)
    except (TypeError, ValueError) as error:
        raise ValueError("Stripe MCP selected-facts deadline must be ISO yyyy-mm-dd.") from error
    return deadline, checked_on, MCP_FACTS_PARSER_VERSION


def classify_deadline_window(
    *,
    as_of: date,
    deadline: date = DEADLINE,
    previous_deadline: date = PREVIOUS_DEADLINE,
) -> DeadlineWindowPhase:
    """Classify a calendar date against the previous (2026-10-31) and current (2026-11-30) deadlines."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a calendar date, not a timestamp.")
    if type(deadline) is not date:
        raise ValueError("deadline must be a calendar date.")
    if type(previous_deadline) is not date:
        raise ValueError("previous_deadline must be a calendar date.")
    if previous_deadline > deadline:
        raise ValueError("previous_deadline must not be after deadline.")
    if as_of < previous_deadline:
        return "before_previous_deadline"
    if as_of < deadline:
        return "contradiction_window"
    return "on_or_after_deadline"


def assess(client: Client, *, as_of: date, deadline: date = DEADLINE) -> Finding:
    """Apply the documented date boundary, not a live authentication check."""
    if not isinstance(client, Client):
        raise ValueError("client must be a Client instance.")
    if type(as_of) is not date:
        raise ValueError("as_of must be a calendar date, not a timestamp.")
    if type(deadline) is not date:
        raise ValueError("deadline must be a calendar date.")
    if client.auth_method in SUPPORTED_AUTH:
        status: FindingStatus = "recorded_supported_unverified"
        action = "Verify permissions, approval rules and environment-scoped revocation separately."
    else:
        status = "migration_required" if as_of < deadline else "blocked_by_documented_policy"
        action = "Use OAuth or a new least-privilege Agent Key; sandbox-test before expiring old keys."
    return Finding(client.client_id, client.environment, client.auth_method, status, action)


def assess_dual_deadline(
    client: Client,
    *,
    as_of: date,
    deadline: date = DEADLINE,
    previous_deadline: date = PREVIOUS_DEADLINE,
) -> DualDeadlineFinding:
    """Evaluate a client against both the primary notice deadline and the earlier 2026-10-31 cutoff."""
    if not isinstance(client, Client):
        raise ValueError("client must be a Client instance.")
    window_phase = classify_deadline_window(
        as_of=as_of,
        deadline=deadline,
        previous_deadline=previous_deadline,
    )
    primary = assess(client, as_of=as_of, deadline=deadline)
    strict_previous = assess(client, as_of=as_of, deadline=previous_deadline)
    contradiction_exposed = primary.status != strict_previous.status
    action = primary.action
    if contradiction_exposed:
        action = (
            "Earlier 2026-10-31 cutoff has elapsed while 2026-11-30 notice remains active; "
            "treat legacy key as blocked under zero-grace policy and migrate to OAuth or Agent Key immediately."
        )
    return DualDeadlineFinding(
        client_id=client.client_id,
        environment=client.environment,
        auth_method=client.auth_method,
        as_of=as_of,
        previous_deadline=previous_deadline,
        deadline=deadline,
        window_phase=window_phase,
        primary_status=primary.status,
        strict_previous_status=strict_previous.status,
        contradiction_exposed=contradiction_exposed,
        action=action,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory", type=Path,
        default=Path(__file__).with_name("mcp_inventory.example.json"),
    )
    parser.add_argument(
        "--as-of", type=date.fromisoformat,
        default=datetime.now(timezone(timedelta(hours=8))).date(),
        help="Calendar-date simulation; default is today's Beijing date, not Stripe's cutoff time.",
    )
    parser.add_argument(
        "--source-report", type=Path, default=None,
        help="Optional source-monitor daily JSON to override deadline from selected Stripe MCP facts.",
    )
    parser.add_argument(
        "--strict-previous-deadline", action="store_true",
        help="Enforce the earlier 2026-10-31 cutoff instead of granting the 2026-11-30 contradiction window.",
    )
    args = parser.parse_args()
    try:
        deadline = DEADLINE
        policy_checked_on = POLICY_CHECKED_ON
        deadline_source = "hardcoded-reviewed-baseline"
        deadline_parser_version = None
        if args.source_report is not None:
            deadline, policy_checked_on, deadline_parser_version = load_deadline_from_source_report(
                args.source_report
            )
            deadline_source = "source-monitor-selected-facts"
        clients = load_inventory(args.inventory)
        previous_boundary = min(PREVIOUS_DEADLINE, deadline)
        effective_deadline = previous_boundary if args.strict_previous_deadline else deadline
        window_phase = classify_deadline_window(
            as_of=args.as_of,
            deadline=deadline,
            previous_deadline=previous_boundary,
        )
        dual_findings = [
            assess_dual_deadline(
                client,
                as_of=args.as_of,
                deadline=deadline,
                previous_deadline=previous_boundary,
            )
            for client in clients
        ]
        findings = [
            assess(client, as_of=args.as_of, deadline=effective_deadline)
            for client in clients
        ]
    except (OSError, UnicodeError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) and not isinstance(
            error, (json.JSONDecodeError, UnicodeError)
        ) else f"{type(error).__name__}: cannot read a valid metadata inventory."
        print(json.dumps({"status": "invalid_inventory", "error": message}), file=sys.stderr)
        return 2
    migration_count = sum(item.auth_method not in SUPPORTED_AUTH for item in findings)
    contradiction_exposed_count = sum(item.contradiction_exposed for item in dual_findings)
    print(json.dumps({
        "kind": "offline-metadata-only",
        "as_of": args.as_of.isoformat(),
        "policy_checked_on": policy_checked_on.isoformat(),
        "policy_source": SOURCE_URL,
        "deadline": deadline.isoformat(),
        "effective_deadline": effective_deadline.isoformat(),
        "strict_previous_deadline_enforced": bool(args.strict_previous_deadline),
        "deadline_source": deadline_source,
        "deadline_parser_version": deadline_parser_version,
        "previous_deadline": PREVIOUS_DEADLINE.isoformat(),
        "previous_deadline_elapsed": args.as_of >= PREVIOUS_DEADLINE,
        "calendar_days_until_previous_deadline": (PREVIOUS_DEADLINE - args.as_of).days,
        "deadline_window_phase": window_phase,
        "contradiction_exposed_count": contradiction_exposed_count,
        "enforcement_starts": ENFORCEMENT_STARTS.isoformat(),
        "calendar_days_until_deadline": (deadline - args.as_of).days,
        "cutoff_time": "not specified in the reviewed documentation",
        "account_verification": "not_performed",
        "migration_count": migration_count,
        "findings": [asdict(item) for item in findings],
    }, indent=2))
    return int(migration_count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
