"""Offline, metadata-only UCP handler preflight; never authorize or send payments."""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal

POLICY_CHECKED_ON = date(2026, 10, 13)
SOURCE_URL = "https://docs.stripe.com/agentic-commerce/protocols/ucp/stripe-payments-handler"
REVIEWED_UCP_VERSION = "2026-04-08"
REVIEWED_HANDLER_VERSION = "2026-06-25"
STRIPE_HANDLER = "com.stripe.payments"
INSTRUMENTS = frozenset({"card", "apple_pay", "link", "google_pay"})
Environment = Literal["sandbox", "production"]
Relationship = Literal["confirmed", "missing", "unknown"]


def calendar_version(value: str) -> str:
    """Require a canonical date, not a moving latest/main alias or guessed version."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Version must be a YYYY-MM-DD date; aliases are not accepted.")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("Version must be a valid calendar date.") from None
    return value


@dataclass(frozen=True)
class HandlerMetadata:
    """Operator-declared metadata, not a parsed or authenticated UCP wire profile."""

    ucp_version: str
    handler_name: str
    handler_version: str
    environment: Environment
    instruments: tuple[str, ...]

    def __post_init__(self) -> None:
        calendar_version(self.ucp_version)
        calendar_version(self.handler_version)
        if not isinstance(self.handler_name, str) or not re.fullmatch(
            r"[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){2,}", self.handler_name
        ):
            raise ValueError("Handler name must be a reverse-domain metadata name, not a URL.")
        if not isinstance(self.environment, str) or self.environment not in {
            "sandbox", "production",
        }:
            raise ValueError("UCP environment must be sandbox or production, not MCP live.")
        if (
            type(self.instruments) is not tuple
            or any(not isinstance(item, str) or item not in INSTRUMENTS for item in self.instruments)
            or len(set(self.instruments)) != len(self.instruments)
        ):
            raise ValueError("Instruments must be a tuple of unique known metadata categories.")


@dataclass(frozen=True)
class Decision:
    """Compatibility only: even a candidate has no payment authority or verified access."""

    status: Literal["candidate_unverified", "blocked"]
    reasons: tuple[str, ...]
    credential_path: str | None
    payment_authorized: bool = False
    provider_verification: str = "not_performed"


def assess(
    platform: HandlerMetadata, business: HandlerMetadata, *,
    instrument: str, relationship: Relationship,
) -> Decision:
    """Check only the reviewed Stripe handler fixture; reject unknowns without fallback."""
    if not isinstance(platform, HandlerMetadata) or not isinstance(business, HandlerMetadata):
        raise ValueError("Preflight requires platform and business HandlerMetadata.")
    if not isinstance(instrument, str) or instrument not in INSTRUMENTS:
        raise ValueError("Select a known instrument category, never a credential.")
    if not isinstance(relationship, str) or relationship not in {"confirmed", "missing", "unknown"}:
        raise ValueError("Relationship must be confirmed, missing or unknown metadata.")

    reasons: list[str] = []
    if platform.ucp_version != business.ucp_version:
        reasons.append("ucp_version_mismatch")
    if any(profile.ucp_version != REVIEWED_UCP_VERSION for profile in (platform, business)):
        reasons.append("ucp_version_not_reviewed_locally")
    if platform.handler_name != business.handler_name:
        reasons.append("handler_name_mismatch")
    if any(profile.handler_name != STRIPE_HANDLER for profile in (platform, business)):
        reasons.append("handler_not_reviewed_locally")
    if platform.handler_version != business.handler_version:
        reasons.append("handler_version_mismatch")
    if any(profile.handler_version != REVIEWED_HANDLER_VERSION for profile in (platform, business)):
        reasons.append("handler_version_not_reviewed_locally")
    if any(instrument not in profile.instruments for profile in (platform, business)):
        reasons.append("instrument_not_advertised_by_both")
    if instrument == "link":
        reasons.append("link_instrument_not_accepted_by_current_complete")
    if instrument == "google_pay":
        reasons.append("google_pay_requires_separately_reviewed_com_google_pay_handler")
    if instrument == "card":
        if platform.environment != business.environment:
            reasons.append("card_tokenize_environment_mismatch")
        if relationship != "confirmed":
            reasons.append("card_tokenize_commerce_relationship_unconfirmed")
    if reasons:
        return Decision("blocked", tuple(reasons), None)
    path = "card_tokenize_to_spt" if instrument == "card" else "apple_pay_direct_to_complete"
    return Decision("candidate_unverified", (), path)


def main() -> int:
    """Assess synthetic declarations; exit 1 for blocked and 2 for invalid metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instrument", choices=sorted(INSTRUMENTS), default="link")
    parser.add_argument("--platform-environment", choices=["sandbox", "production"], default="sandbox")
    parser.add_argument("--business-environment", choices=["sandbox", "production"], default="sandbox")
    parser.add_argument("--relationship", choices=["confirmed", "missing", "unknown"], default="unknown")
    parser.add_argument("--business-ucp-version", default=REVIEWED_UCP_VERSION)
    parser.add_argument("--business-handler-version", default=REVIEWED_HANDLER_VERSION)
    args = parser.parse_args()
    try:
        platform = HandlerMetadata(
            REVIEWED_UCP_VERSION, STRIPE_HANDLER, REVIEWED_HANDLER_VERSION,
            args.platform_environment, tuple(sorted(INSTRUMENTS)),
        )
        business = HandlerMetadata(
            args.business_ucp_version, STRIPE_HANDLER, args.business_handler_version,
            args.business_environment, tuple(sorted(INSTRUMENTS)),
        )
        decision = assess(
            platform, business, instrument=args.instrument, relationship=args.relationship,
        )
    except ValueError as error:
        print(json.dumps({"status": "invalid_metadata", "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({
        "kind": "offline-synthetic-metadata-preflight",
        "policy_checked_on": POLICY_CHECKED_ON.isoformat(),
        "policy_source": SOURCE_URL,
        "reviewed_versions_are": "documentation examples, not universal latest versions",
        "platform": asdict(platform),
        "business": asdict(business),
        "instrument": args.instrument,
        "relationship": args.relationship,
        "decision": asdict(decision),
        "remaining_checks": [
            "authenticated discovery and merchant configuration",
            "region, account access and provider credentials",
            "customer consent, final quote, limits, expiry and revocation",
            "payment result, reconciliation and fulfillment",
        ],
        "real_payments": False,
    }, indent=2))
    return int(decision.status == "blocked")


if __name__ == "__main__":
    raise SystemExit(main())
