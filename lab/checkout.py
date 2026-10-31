"""Deterministic authorization and atomic local checkout receipts."""

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

MandateState = Literal["active", "revoked"]
CheckoutPhase = Literal[
    "active_unspent",
    "revoked_unspent",
    "consumed_active",
    "consumed_revoked",
]
CheckoutTimedPhase = Literal[
    "active_unspent",
    "expired_unspent",
    "revoked_unspent",
    "consumed_active",
    "consumed_revoked",
]
CheckoutExecutionDecision = Literal[
    "consume_mandate",
    "replay_receipt",
    "blocked_revoked",
    "blocked_expired",
]


class AuthorizationError(ValueError):
    """The checkout exceeds an approved mandate or reuses its authority."""


@dataclass(frozen=True)
class Checkout:
    """A synthetic merchant quote, including tax and shipping in minor units."""

    merchant: str
    currency: str
    sku: str
    quantity: int
    amount: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.merchant, str)
            or not self.merchant
            or not isinstance(self.sku, str)
            or not self.sku
        ):
            raise ValueError("Checkout requires a merchant and a nonempty SKU.")
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isupper()
        ):
            raise ValueError("Currency must be a three-letter uppercase ASCII code.")
        if not self.currency.isalpha():
            raise ValueError("Currency must contain only letters.")
        for name, value in (("amount", self.amount), ("quantity", self.quantity)):
            if type(value) is not int or not 0 < value <= 2**63 - 1:
                raise ValueError(f"{name} must be a positive signed 64-bit integer.")

    @property
    def digest(self) -> str:
        """Return a local cart binding; this is not a protocol signature."""
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class MandateStatus:
    """Persisted local mandate record state, not live validity or settlement authority."""

    mandate_id: str
    merchant: str
    currency: str
    cart_digest: str
    max_amount: int
    expires_at: int
    state: MandateState

    def __post_init__(self) -> None:
        if not isinstance(self.mandate_id, str) or not self.mandate_id:
            raise AuthorizationError("Stored mandate ID is invalid.")
        if not isinstance(self.merchant, str) or not self.merchant:
            raise AuthorizationError("Stored mandate merchant is invalid.")
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isupper()
            or not self.currency.isalpha()
        ):
            raise AuthorizationError("Stored mandate currency is invalid.")
        if (
            not isinstance(self.cart_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.cart_digest) is None
        ):
            raise AuthorizationError(
                "Stored mandate cart_digest must be a 64-char hex SHA-256 digest."
            )
        if type(self.max_amount) is not int or not 0 < self.max_amount <= 2**63 - 1:
            raise AuthorizationError("Stored mandate max_amount is invalid.")
        if type(self.expires_at) is not int or not 0 < self.expires_at <= 2**63 - 1:
            raise AuthorizationError("Stored mandate expiry is invalid.")
        if not isinstance(self.state, str) or self.state not in ("active", "revoked"):
            raise AuthorizationError("Stored mandate revocation state is invalid.")


@dataclass(frozen=True)
class Receipt:
    """A persisted local outcome with no card or payment token information."""

    order_id: str
    amount: int
    currency: str
    status: str = "simulated"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.order_id, str)
            or re.fullmatch(r"sim_[0-9a-f]{24}", self.order_id) is None
        ):
            raise AuthorizationError("Receipt order_id must be a sim_<24-hex> identifier.")
        if type(self.amount) is not int or not 0 < self.amount <= 2**63 - 1:
            raise AuthorizationError(
                "Receipt amount must be a positive signed 64-bit integer."
            )
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isupper()
            or not self.currency.isalpha()
        ):
            raise AuthorizationError("Currency must be a three-letter uppercase ASCII code.")
        if not isinstance(self.status, str) or self.status != "simulated":
            raise AuthorizationError("Receipt status must be 'simulated'.")


def _execution_fingerprint_for_digest(mandate_id: str, cart_digest: str) -> str:
    return hashlib.sha256(
        json.dumps([mandate_id, cart_digest], separators=(",", ":")).encode()
    ).hexdigest()


def _execution_fingerprint(mandate_id: str, checkout: Checkout) -> str:
    return _execution_fingerprint_for_digest(mandate_id, checkout.digest)


@dataclass(frozen=True)
class CheckoutProvenance:
    """Local coupled mandate-status and idempotency-receipt snapshot, not settlement proof."""

    mandate_id: str
    fingerprint: str
    mandate_status: MandateStatus
    request_key: str | None
    receipt: Receipt | None

    def __post_init__(self) -> None:
        if not isinstance(self.mandate_id, str) or not self.mandate_id:
            raise AuthorizationError("Mandate ID must be a nonempty string.")
        if (
            not isinstance(self.fingerprint, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
        ):
            raise AuthorizationError(
                "Execution fingerprint must be a 64-char hex SHA-256 digest."
            )
        if self.mandate_status is None:
            if self.receipt is not None:
                raise AuthorizationError(
                    "Orphan receipt exists without a recorded mandate."
                )
            raise AuthorizationError("mandate_status must be a MandateStatus.")
        if not isinstance(self.mandate_status, MandateStatus):
            raise AuthorizationError("mandate_status must be a MandateStatus.")
        if self.mandate_status.mandate_id != self.mandate_id:
            raise AuthorizationError("Mandate status differs from the bound mandate.")
        expected_fingerprint = _execution_fingerprint_for_digest(
            self.mandate_id, self.mandate_status.cart_digest
        )
        if self.fingerprint != expected_fingerprint:
            raise AuthorizationError(
                "Execution fingerprint differs from the bound mandate and cart digest."
            )
        if self.request_key is not None and (
            not isinstance(self.request_key, str) or not self.request_key
        ):
            raise AuthorizationError("Idempotency request_key must be a nonempty string.")
        if self.receipt is None:
            if self.request_key is not None:
                raise AuthorizationError(
                    "request_key cannot be set when no receipt is recorded."
                )
        else:
            if not isinstance(self.receipt, Receipt):
                raise AuthorizationError("receipt must be a Receipt or None.")
            if self.request_key is None:
                raise AuthorizationError(
                    "request_key is required when a receipt is recorded."
                )
            if self.receipt.order_id != f"sim_{self.fingerprint[:24]}":
                raise AuthorizationError(
                    "Stored receipt order_id differs from the bound execution fingerprint."
                )
            if self.receipt.currency != self.mandate_status.currency:
                raise AuthorizationError(
                    "Stored receipt currency differs from the recorded mandate."
                )
            if self.receipt.amount > self.mandate_status.max_amount:
                raise AuthorizationError(
                    "Stored receipt amount exceeds the recorded mandate ceiling."
                )

    @property
    def phase(self) -> CheckoutPhase:
        """Return the clock-independent mandate and receipt lifecycle phase."""
        if self.receipt is None:
            if self.mandate_status.state == "revoked":
                return "revoked_unspent"
            return "active_unspent"
        if self.mandate_status.state == "revoked":
            return "consumed_revoked"
        return "consumed_active"

    def phase_at(self, now: int) -> CheckoutTimedPhase:
        """Evaluate the mandate and receipt lifecycle phase at a trusted Unix timestamp."""
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise ValueError("The trusted clock must provide a nonnegative Unix timestamp.")
        if self.receipt is not None:
            if self.mandate_status.state == "revoked":
                return "consumed_revoked"
            return "consumed_active"
        if self.mandate_status.state == "revoked":
            return "revoked_unspent"
        if now >= self.mandate_status.expires_at:
            return "expired_unspent"
        return "active_unspent"


@dataclass(frozen=True)
class CheckoutExecutionPreview:
    """Lock-free single-snapshot preview of CheckoutStore.execute() at a trusted clock."""

    provenance: CheckoutProvenance
    request_key: str
    now: int
    timed_phase: CheckoutTimedPhase
    decision: CheckoutExecutionDecision
    execution_allowed: bool
    will_mutate: bool
    projected_receipt: Receipt | None

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, CheckoutProvenance):
            raise AuthorizationError("provenance must be a CheckoutProvenance.")
        if not isinstance(self.request_key, str) or not self.request_key:
            raise AuthorizationError("Idempotency request_key must be a nonempty string.")
        if type(self.now) is not int or not 0 <= self.now <= 2**63 - 1:
            raise AuthorizationError(
                "The trusted clock must provide a nonnegative Unix timestamp."
            )
        if type(self.execution_allowed) is not bool:
            raise AuthorizationError("execution_allowed must be a bool.")
        if type(self.will_mutate) is not bool:
            raise AuthorizationError("will_mutate must be a bool.")
        expected_phase = self.provenance.phase_at(self.now)
        if self.timed_phase != expected_phase:
            raise AuthorizationError(
                "Preview timed_phase does not match provenance at the supplied clock."
            )
        if self.provenance.receipt is not None:
            if self.provenance.request_key != self.request_key:
                raise AuthorizationError(
                    "Mandate already consumed; retry with the original key."
                )
            expected_decision: CheckoutExecutionDecision = "replay_receipt"
            expected_allowed = True
            expected_mutate = False
        elif expected_phase == "revoked_unspent":
            expected_decision = "blocked_revoked"
            expected_allowed = False
            expected_mutate = False
        elif expected_phase == "expired_unspent":
            expected_decision = "blocked_expired"
            expected_allowed = False
            expected_mutate = False
        else:
            expected_decision = "consume_mandate"
            expected_allowed = True
            expected_mutate = True
        if self.decision != expected_decision:
            raise AuthorizationError(
                "Preview decision is inconsistent with provenance and clock."
            )
        if self.execution_allowed != expected_allowed:
            raise AuthorizationError(
                "Preview execution_allowed is inconsistent with decision."
            )
        if self.will_mutate != expected_mutate:
            raise AuthorizationError(
                "Preview will_mutate is inconsistent with decision."
            )
        if expected_decision == "replay_receipt":
            if self.projected_receipt != self.provenance.receipt:
                raise AuthorizationError(
                    "Replay preview projected_receipt must match the recorded receipt."
                )
        elif expected_decision == "consume_mandate":
            if not isinstance(self.projected_receipt, Receipt):
                raise AuthorizationError(
                    "Consume preview requires a projected Receipt."
                )
            if self.projected_receipt.order_id != f"sim_{self.provenance.fingerprint[:24]}":
                raise AuthorizationError(
                    "Projected receipt order_id differs from the bound execution fingerprint."
                )
            if self.projected_receipt.currency != self.provenance.mandate_status.currency:
                raise AuthorizationError(
                    "Projected receipt currency differs from the recorded mandate."
                )
            if self.projected_receipt.amount > self.provenance.mandate_status.max_amount:
                raise AuthorizationError(
                    "Projected receipt amount exceeds the recorded mandate ceiling."
                )
        else:
            if self.projected_receipt is not None:
                raise AuthorizationError(
                    "Blocked preview cannot include a projected_receipt."
                )


@dataclass(frozen=True)
class MandateRevocationPreview:
    """Single-SELECT read-only dry-run preview of CheckoutStore.revoke()."""

    mandate_id: str
    existing_status: MandateStatus
    projected_status: MandateStatus
    would_revoke: bool
    has_consumed_receipt: bool

    def __post_init__(self) -> None:
        if not isinstance(self.mandate_id, str) or not self.mandate_id:
            raise ValueError("Revocation requires a nonempty mandate ID.")
        if not isinstance(self.existing_status, MandateStatus) or not isinstance(
            self.projected_status, MandateStatus
        ):
            raise AuthorizationError(
                "existing_status and projected_status must be MandateStatus instances."
            )
        if self.existing_status.mandate_id != self.mandate_id:
            raise AuthorizationError("Mandate status differs from the bound mandate.")
        expected_projected = MandateStatus(
            mandate_id=self.existing_status.mandate_id,
            merchant=self.existing_status.merchant,
            currency=self.existing_status.currency,
            cart_digest=self.existing_status.cart_digest,
            max_amount=self.existing_status.max_amount,
            expires_at=self.existing_status.expires_at,
            state="revoked",
        )
        if self.projected_status != expected_projected:
            raise AuthorizationError(
                "projected_status must match existing_status with state='revoked'."
            )
        if (
            type(self.would_revoke) is not bool
            or type(self.has_consumed_receipt) is not bool
        ):
            raise AuthorizationError(
                "MandateRevocationPreview flags must be booleans."
            )
        if self.would_revoke != (self.existing_status.state == "active"):
            raise AuthorizationError(
                "would_revoke must be True iff existing_status is active."
            )

    @property
    def existing_phase(self) -> CheckoutPhase:
        if self.has_consumed_receipt:
            return (
                "consumed_revoked"
                if self.existing_status.state == "revoked"
                else "consumed_active"
            )
        return (
            "revoked_unspent"
            if self.existing_status.state == "revoked"
            else "active_unspent"
        )

    @property
    def projected_phase(self) -> CheckoutPhase:
        return "consumed_revoked" if self.has_consumed_receipt else "revoked_unspent"


def _parse_mandate_row(
    row: sqlite3.Row, *, expected_mandate_id: str, prefix: str = ""
) -> MandateStatus:
    mandate_id = row[f"{prefix}id"]
    if not isinstance(mandate_id, str) or mandate_id != expected_mandate_id:
        raise AuthorizationError("Stored mandate ID is invalid.")
    revoked = row[f"{prefix}revoked"]
    if type(revoked) is not int or revoked not in (0, 1):
        raise AuthorizationError("Stored mandate revocation state is invalid.")
    return MandateStatus(
        mandate_id=mandate_id,
        merchant=row[f"{prefix}merchant"],
        currency=row[f"{prefix}currency"],
        cart_digest=row[f"{prefix}cart_digest"],
        max_amount=row[f"{prefix}max_amount"],
        expires_at=row[f"{prefix}expires_at"],
        state="revoked" if revoked else "active",
    )


def _verify_mandate_binding(status: MandateStatus, checkout: Checkout) -> None:
    if checkout.merchant != status.merchant or checkout.currency != status.currency:
        raise AuthorizationError("Merchant or currency differs from the trusted approval.")
    if checkout.amount > status.max_amount:
        raise AuthorizationError("Checkout exceeds the approved spending limit.")
    if checkout.digest != status.cart_digest:
        raise AuthorizationError("Cart changed after approval; obtain new approval.")


def _parse_receipt_row(
    row: sqlite3.Row,
    *,
    expected_request_key: str | None,
    expected_mandate_id: str,
    expected_fingerprint: str,
    checkout: Checkout,
    prefix: str = "",
) -> tuple[str, Receipt]:
    request_key = row[f"{prefix}request_key"]
    if not isinstance(request_key, str) or not request_key:
        raise AuthorizationError("Stored receipt request_key is invalid.")
    if expected_request_key is not None and request_key != expected_request_key:
        raise AuthorizationError("Stored receipt request_key is invalid.")
    fingerprint = row[f"{prefix}fingerprint"]
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise AuthorizationError("Stored receipt fingerprint is invalid.")
    if fingerprint != expected_fingerprint:
        raise AuthorizationError("Idempotency key conflicts with an earlier checkout.")
    mandate_id = row[f"{prefix}mandate_id"]
    if not isinstance(mandate_id, str) or not mandate_id:
        raise AuthorizationError("Stored receipt mandate_id is invalid.")
    if mandate_id != expected_mandate_id:
        raise AuthorizationError("Stored receipt mandate_id differs from the bound mandate.")
    receipt = Receipt(
        order_id=row[f"{prefix}order_id"],
        amount=row[f"{prefix}amount"],
        currency=row[f"{prefix}currency"],
    )
    if receipt.order_id != f"sim_{expected_fingerprint[:24]}":
        raise AuthorizationError(
            "Stored receipt order_id differs from the bound execution fingerprint."
        )
    if receipt.amount != checkout.amount or receipt.currency != checkout.currency:
        raise AuthorizationError("Stored receipt differs from the bound checkout.")
    return request_key, receipt


class CheckoutStore:
    """Persist trusted approvals and receipts; never call a real payment rail."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS mandates (
                    id TEXT PRIMARY KEY,
                    merchant TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    cart_digest TEXT NOT NULL,
                    max_amount INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    request_key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    mandate_id TEXT NOT NULL UNIQUE REFERENCES mandates(id),
                    order_id TEXT NOT NULL UNIQUE,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    @staticmethod
    def _require_scope(mandate_id: str, checkout: Checkout) -> None:
        if not isinstance(mandate_id, str) or not mandate_id:
            raise ValueError("Checkout requires a nonempty mandate ID.")
        if not isinstance(checkout, Checkout):
            raise ValueError("Checkout requires a validated Checkout.")

    def approve(
        self, mandate_id: str, checkout: Checkout, *, max_amount: int, expires_at: int
    ) -> None:
        """Trusted operator entry point, not an agent tool or consent UI."""
        if not isinstance(mandate_id, str) or not mandate_id:
            raise ValueError("Approval requires a nonempty mandate ID.")
        if not isinstance(checkout, Checkout):
            raise ValueError("Approval requires a validated Checkout.")
        if type(max_amount) is not int or not checkout.amount <= max_amount <= 2**63 - 1:
            raise ValueError("Approval limit must cover the quote in signed 64-bit minor units.")
        if type(expires_at) is not int or not 0 < expires_at <= 2**63 - 1:
            raise ValueError("Approval expiry must be a positive signed 64-bit Unix timestamp.")
        with closing(self._connect()) as db, db:
            db.execute(
                "INSERT INTO mandates (id,merchant,currency,cart_digest,max_amount,expires_at)"
                " VALUES (?,?,?,?,?,?)",
                (mandate_id, checkout.merchant, checkout.currency, checkout.digest,
                 max_amount, expires_at),
            )

    def revoke(self, mandate_id: str) -> None:
        """Revoke unspent authority without erasing completed receipts."""
        if not isinstance(mandate_id, str) or not mandate_id:
            raise ValueError("Revocation requires a nonempty mandate ID.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM mandates WHERE id=?", (mandate_id,)).fetchone()
            if row is None:
                raise AuthorizationError(f"Cannot revoke unknown mandate {mandate_id!r}.")
            _parse_mandate_row(row, expected_mandate_id=mandate_id)
            db.execute("UPDATE mandates SET revoked=1 WHERE id=?", (mandate_id,))

    def preview_revoke(
        self, mandate_id: str, checkout: Checkout | None = None
    ) -> MandateRevocationPreview:
        """Preview revoke() in one lock-free SELECT without mutating mandates."""
        if not isinstance(mandate_id, str) or not mandate_id:
            raise ValueError("Revocation requires a nonempty mandate ID.")
        if checkout is not None and not isinstance(checkout, Checkout):
            raise ValueError("Checkout requires a validated Checkout.")
        with closing(self._connect()) as db:
            row = db.execute(
                """SELECT
                    m.id AS m_id,
                    m.merchant AS m_merchant,
                    m.currency AS m_currency,
                    m.cart_digest AS m_cart_digest,
                    m.max_amount AS m_max_amount,
                    m.expires_at AS m_expires_at,
                    m.revoked AS m_revoked,
                    r.request_key AS r_request_key
                FROM (SELECT 1)
                LEFT JOIN mandates m ON m.id = ?
                LEFT JOIN receipts r ON r.mandate_id = ?
                """,
                (mandate_id, mandate_id),
            ).fetchone()
        if row is not None and row["m_id"] is None and row["r_request_key"] is not None:
            raise AuthorizationError("Orphan receipt exists without a recorded mandate.")
        if row is None or row["m_id"] is None:
            raise AuthorizationError(f"Cannot revoke unknown mandate {mandate_id!r}.")
        existing_status = _parse_mandate_row(
            row, expected_mandate_id=mandate_id, prefix="m_"
        )
        if checkout is not None:
            _verify_mandate_binding(existing_status, checkout)
        projected_status = MandateStatus(
            mandate_id=existing_status.mandate_id,
            merchant=existing_status.merchant,
            currency=existing_status.currency,
            cart_digest=existing_status.cart_digest,
            max_amount=existing_status.max_amount,
            expires_at=existing_status.expires_at,
            state="revoked",
        )
        return MandateRevocationPreview(
            mandate_id=mandate_id,
            existing_status=existing_status,
            projected_status=projected_status,
            would_revoke=existing_status.state == "active",
            has_consumed_receipt=row["r_request_key"] is not None,
        )

    def read_mandate(self, mandate_id: str, checkout: Checkout) -> MandateStatus | None:
        """Read local mandate record state without clock sampling or mutation."""
        self._require_scope(mandate_id, checkout)
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM mandates WHERE id=?", (mandate_id,)).fetchone()
        if row is None:
            return None
        status = _parse_mandate_row(row, expected_mandate_id=mandate_id)
        _verify_mandate_binding(status, checkout)
        return status

    def read_receipt(
        self, mandate_id: str, checkout: Checkout, *, request_key: str
    ) -> Receipt | None:
        """Read local idempotency receipt coupled to its parent mandate without mutation."""
        self._require_scope(mandate_id, checkout)
        if not isinstance(request_key, str) or not request_key:
            raise ValueError("Checkout requires a nonempty idempotency key.")
        fingerprint = _execution_fingerprint(mandate_id, checkout)
        with closing(self._connect()) as db:
            row = db.execute(
                """
                SELECT
                    r.request_key AS r_request_key,
                    r.fingerprint AS r_fingerprint,
                    r.mandate_id AS r_mandate_id,
                    r.order_id AS r_order_id,
                    r.amount AS r_amount,
                    r.currency AS r_currency,
                    m.id AS m_id,
                    m.merchant AS m_merchant,
                    m.currency AS m_currency,
                    m.cart_digest AS m_cart_digest,
                    m.max_amount AS m_max_amount,
                    m.expires_at AS m_expires_at,
                    m.revoked AS m_revoked
                FROM receipts r
                LEFT JOIN mandates m ON m.id = r.mandate_id
                WHERE r.request_key = ?
                """,
                (request_key,),
            ).fetchone()
        if row is None:
            return None
        _, receipt = _parse_receipt_row(
            row,
            expected_request_key=request_key,
            expected_mandate_id=mandate_id,
            expected_fingerprint=fingerprint,
            checkout=checkout,
            prefix="r_",
        )
        if row["m_id"] is None:
            raise AuthorizationError("Orphan receipt exists without a recorded mandate.")
        status = _parse_mandate_row(row, expected_mandate_id=mandate_id, prefix="m_")
        _verify_mandate_binding(status, checkout)
        return receipt

    def find_provenance(
        self,
        mandate_id: str,
        checkout: Checkout,
        *,
        request_key: str | None = None,
    ) -> CheckoutProvenance | None:
        """Read coupled mandate and receipt provenance in one read-only SQLite query."""
        self._require_scope(mandate_id, checkout)
        if request_key is not None and (not isinstance(request_key, str) or not request_key):
            raise ValueError("Checkout requires a nonempty idempotency key.")
        fingerprint = _execution_fingerprint(mandate_id, checkout)
        with closing(self._connect()) as db:
            row = db.execute(
                """
                SELECT
                    m.id AS m_id,
                    m.merchant AS m_merchant,
                    m.currency AS m_currency,
                    m.cart_digest AS m_cart_digest,
                    m.max_amount AS m_max_amount,
                    m.expires_at AS m_expires_at,
                    m.revoked AS m_revoked,
                    rm.request_key AS rm_request_key,
                    rm.fingerprint AS rm_fingerprint,
                    rm.mandate_id AS rm_mandate_id,
                    rm.order_id AS rm_order_id,
                    rm.amount AS rm_amount,
                    rm.currency AS rm_currency,
                    rk.request_key AS rk_request_key,
                    rk.fingerprint AS rk_fingerprint,
                    rk.mandate_id AS rk_mandate_id,
                    rk.order_id AS rk_order_id,
                    rk.amount AS rk_amount,
                    rk.currency AS rk_currency
                FROM (SELECT 1)
                LEFT JOIN mandates m ON m.id = ?
                LEFT JOIN receipts rm ON rm.mandate_id = ?
                LEFT JOIN receipts rk ON ? IS NOT NULL AND rk.request_key = ?
                """,
                (mandate_id, mandate_id, request_key, request_key),
            ).fetchone()
        assert row is not None
        if (
            row["m_id"] is None
            and row["rm_request_key"] is None
            and row["rk_request_key"] is None
        ):
            return None
        if row["rk_request_key"] is not None and row["rk_mandate_id"] != mandate_id:
            _parse_receipt_row(
                row,
                expected_request_key=request_key,
                expected_mandate_id=mandate_id,
                expected_fingerprint=fingerprint,
                checkout=checkout,
                prefix="rk_",
            )
        status: MandateStatus | None = None
        if row["m_id"] is not None:
            status = _parse_mandate_row(row, expected_mandate_id=mandate_id, prefix="m_")
            _verify_mandate_binding(status, checkout)
        if row["rk_request_key"] is not None:
            _parse_receipt_row(
                row,
                expected_request_key=request_key,
                expected_mandate_id=mandate_id,
                expected_fingerprint=fingerprint,
                checkout=checkout,
                prefix="rk_",
            )
        recorded_key: str | None = None
        receipt: Receipt | None = None
        if row["rm_request_key"] is not None:
            recorded_key, receipt = _parse_receipt_row(
                row,
                expected_request_key=None,
                expected_mandate_id=mandate_id,
                expected_fingerprint=fingerprint,
                checkout=checkout,
                prefix="rm_",
            )
            if request_key is not None and recorded_key != request_key:
                raise AuthorizationError(
                    "Mandate already consumed; retry with the original key."
                )
        if status is None:
            raise AuthorizationError("Orphan receipt exists without a recorded mandate.")
        return CheckoutProvenance(
            mandate_id=mandate_id,
            fingerprint=fingerprint,
            mandate_status=status,
            request_key=recorded_key,
            receipt=receipt,
        )

    def read_provenance(
        self,
        mandate_id: str,
        checkout: Checkout,
        *,
        request_key: str | None = None,
    ) -> CheckoutProvenance:
        """Read coupled mandate and receipt provenance, failing closed when absent."""
        provenance = self.find_provenance(mandate_id, checkout, request_key=request_key)
        if provenance is None:
            raise AuthorizationError("No trusted approval exists for this mandate.")
        return provenance

    def find_execution_preview(
        self,
        mandate_id: str,
        checkout: Checkout,
        *,
        request_key: str,
        now: int,
    ) -> CheckoutExecutionPreview | None:
        """Preview execute() in one lock-free SELECT query without mutating SQLite."""
        self._require_scope(mandate_id, checkout)
        if not isinstance(request_key, str) or not request_key:
            raise ValueError("Checkout requires a nonempty idempotency key.")
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise ValueError("The trusted clock must provide a nonnegative Unix timestamp.")
        provenance = self.find_provenance(mandate_id, checkout, request_key=request_key)
        if provenance is None:
            return None
        timed_phase = provenance.phase_at(now)
        if provenance.receipt is not None:
            return CheckoutExecutionPreview(
                provenance=provenance,
                request_key=request_key,
                now=now,
                timed_phase=timed_phase,
                decision="replay_receipt",
                execution_allowed=True,
                will_mutate=False,
                projected_receipt=provenance.receipt,
            )
        if timed_phase == "revoked_unspent":
            return CheckoutExecutionPreview(
                provenance=provenance,
                request_key=request_key,
                now=now,
                timed_phase=timed_phase,
                decision="blocked_revoked",
                execution_allowed=False,
                will_mutate=False,
                projected_receipt=None,
            )
        if timed_phase == "expired_unspent":
            return CheckoutExecutionPreview(
                provenance=provenance,
                request_key=request_key,
                now=now,
                timed_phase=timed_phase,
                decision="blocked_expired",
                execution_allowed=False,
                will_mutate=False,
                projected_receipt=None,
            )
        return CheckoutExecutionPreview(
            provenance=provenance,
            request_key=request_key,
            now=now,
            timed_phase=timed_phase,
            decision="consume_mandate",
            execution_allowed=True,
            will_mutate=True,
            projected_receipt=Receipt(
                f"sim_{provenance.fingerprint[:24]}",
                checkout.amount,
                checkout.currency,
            ),
        )

    def preview_execute(
        self,
        mandate_id: str,
        checkout: Checkout,
        *,
        request_key: str,
        now: int,
    ) -> CheckoutExecutionPreview:
        """Preview execute() in one lock-free SELECT query, failing closed when absent."""
        preview = self.find_execution_preview(
            mandate_id, checkout, request_key=request_key, now=now
        )
        if preview is None:
            raise AuthorizationError("No trusted approval exists for this mandate.")
        return preview

    def execute(
        self, mandate_id: str, checkout: Checkout, *, request_key: str, now: int
    ) -> Receipt:
        """Atomically consume one approval; identical retries return the same receipt."""
        self._require_scope(mandate_id, checkout)
        if not isinstance(request_key, str) or not request_key:
            raise ValueError("Checkout requires a nonempty idempotency key.")
        if type(now) is not int or not 0 <= now <= 2**63 - 1:
            raise ValueError("The trusted clock must provide a nonnegative Unix timestamp.")
        fingerprint = _execution_fingerprint(mandate_id, checkout)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT * FROM receipts WHERE request_key=?", (request_key,)
            ).fetchone()
            if previous:
                _, receipt = _parse_receipt_row(
                    previous,
                    expected_request_key=request_key,
                    expected_mandate_id=mandate_id,
                    expected_fingerprint=fingerprint,
                    checkout=checkout,
                )
                mandate = db.execute(
                    "SELECT * FROM mandates WHERE id=?", (mandate_id,)
                ).fetchone()
                if mandate is None:
                    raise AuthorizationError(
                        "Orphan receipt exists without a recorded mandate."
                    )
                status = _parse_mandate_row(mandate, expected_mandate_id=mandate_id)
                _verify_mandate_binding(status, checkout)
                return receipt
            mandate = db.execute(
                "SELECT * FROM mandates WHERE id=?", (mandate_id,)
            ).fetchone()
            if mandate is None:
                if db.execute(
                    "SELECT 1 FROM receipts WHERE mandate_id=?", (mandate_id,)
                ).fetchone() is not None:
                    raise AuthorizationError(
                        "Orphan receipt exists without a recorded mandate."
                    )
                raise AuthorizationError("No trusted approval exists for this mandate.")
            status = _parse_mandate_row(mandate, expected_mandate_id=mandate_id)
            if status.state == "revoked" or now >= status.expires_at:
                raise AuthorizationError("Mandate is revoked or expired; obtain new approval.")
            _verify_mandate_binding(status, checkout)
            consumed = db.execute(
                "SELECT * FROM receipts WHERE mandate_id=?", (mandate_id,)
            ).fetchone()
            if consumed is not None:
                _parse_receipt_row(
                    consumed,
                    expected_request_key=None,
                    expected_mandate_id=mandate_id,
                    expected_fingerprint=fingerprint,
                    checkout=checkout,
                )
                raise AuthorizationError("Mandate already consumed; retry with the original key.")
            receipt = Receipt(f"sim_{fingerprint[:24]}", checkout.amount, checkout.currency)
            db.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?,?)",
                (request_key, fingerprint, mandate_id, receipt.order_id,
                 receipt.amount, receipt.currency),
            )
            return receipt
