"""Offline Stripe MCP auth inventory: metadata only, never credentials or API calls."""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

PREVIOUS_DEADLINE = date(2026, 10, 31)
DEADLINE = date(2026, 11, 30)
ENFORCEMENT_STARTS = date(2026, 12, 1)
POLICY_CHECKED_ON = date(2026, 10, 17)
SOURCE_URL = "https://docs.stripe.com/mcp"
MAX_BYTES = 64 * 1024
AuthMethod = Literal[
    "oauth", "agent_key", "full_access_secret", "restricted_without_agent_tag"
]
SUPPORTED_AUTH = frozenset({"oauth", "agent_key"})
KNOWN_AUTH = SUPPORTED_AUTH | {"full_access_secret", "restricted_without_agent_tag"}


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
    status: str
    action: str


def unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON without echoing input values."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member; use one value per field.")
        result[key] = value
    return result


def load_inventory(path: Path) -> list[Client]:
    """Accept a small, strict metadata document with no credential fields."""
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


def assess(client: Client, *, as_of: date) -> Finding:
    """Apply the documented date boundary, not a live authentication check."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a calendar date, not a timestamp.")
    if client.auth_method in SUPPORTED_AUTH:
        status = "recorded_supported_unverified"
        action = "Verify permissions, approval rules and environment-scoped revocation separately."
    else:
        status = "migration_required" if as_of < DEADLINE else "blocked_by_documented_policy"
        action = "Use OAuth or a new least-privilege Agent Key; sandbox-test before expiring old keys."
    return Finding(client.client_id, client.environment, client.auth_method, status, action)


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
    args = parser.parse_args()
    try:
        findings = [assess(client, as_of=args.as_of) for client in load_inventory(args.inventory)]
    except (OSError, UnicodeError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) and not isinstance(
            error, (json.JSONDecodeError, UnicodeError)
        ) else f"{type(error).__name__}: cannot read a valid metadata inventory."
        print(json.dumps({"status": "invalid_inventory", "error": message}), file=sys.stderr)
        return 2
    migration_count = sum(item.auth_method not in SUPPORTED_AUTH for item in findings)
    print(json.dumps({
        "kind": "offline-metadata-only",
        "as_of": args.as_of.isoformat(),
        "policy_checked_on": POLICY_CHECKED_ON.isoformat(),
        "policy_source": SOURCE_URL,
        "deadline": DEADLINE.isoformat(),
        "previous_deadline": PREVIOUS_DEADLINE.isoformat(),
        "enforcement_starts": ENFORCEMENT_STARTS.isoformat(),
        "calendar_days_until_deadline": (DEADLINE - args.as_of).days,
        "cutoff_time": "not specified in the reviewed documentation",
        "account_verification": "not_performed",
        "migration_count": migration_count,
        "findings": [asdict(item) for item in findings],
    }, indent=2))
    return int(migration_count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
