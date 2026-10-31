"""Offline durable Session assertion admission, not JWT or OAuth verification."""

import hashlib
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from lab.poppy_guard import (
    URL_SAFE_BASE64_ID_RE,
    SessionAssertionClaims,
    verify_poppy_v02_assertion_metadata,
)


class PoppyReplayError(ValueError):
    """Trusted configuration or decoded assertion metadata violates local policy."""


class PoppyReplayDetected(PoppyReplayError):
    """This Company/client has already consumed the assertion ID."""


@dataclass(frozen=True)
class PoppyReplayScope:
    """Preverified Company issuer and authenticated client, never request-selected."""

    auth_issuer: str
    client_id: str

    def __post_init__(self) -> None:
        for value in (self.auth_issuer, self.client_id):
            if not isinstance(value, str) or not value or value != value.strip():
                raise PoppyReplayError("Canonical trusted issuer and client strings are required.")


@dataclass(frozen=True)
class PoppyConsumedAssertion:
    """One persisted scoped jti digest from poppy_assertion_replays; not token proof."""

    scope: PoppyReplayScope
    jti_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PoppyReplayScope):
            raise PoppyReplayError("A trusted PoppyReplayScope is required.")
        if (
            not isinstance(self.jti_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.jti_sha256) is None
        ):
            raise PoppyReplayError(
                "Consumed assertion digest must be a 64-char lowercase hex SHA-256 string."
            )


def _row_to_consumed_assertion(
    scope: PoppyReplayScope, expected_digest: str, row: tuple[object, ...],
) -> PoppyConsumedAssertion:
    auth_issuer, client_id, jti_sha256 = row
    record = PoppyConsumedAssertion(
        scope=PoppyReplayScope(auth_issuer, client_id),
        jti_sha256=jti_sha256,
    )
    if record.scope != scope or record.jti_sha256 != expected_digest:
        raise PoppyReplayError("Stored replay record does not match the lookup key.")
    return record


@dataclass(frozen=True)
class PoppyConsumptionPreview:
    """Single-SELECT read-only dry-run preview of PoppyAssertionJournal.consume()."""

    scope: PoppyReplayScope
    jti_sha256: str
    now: int
    existing_consumption: PoppyConsumedAssertion | None
    projected_consumption: PoppyConsumedAssertion
    would_consume: bool

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PoppyReplayScope):
            raise PoppyReplayError("A trusted PoppyReplayScope is required.")
        if (
            not isinstance(self.jti_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.jti_sha256) is None
        ):
            raise PoppyReplayError(
                "Consumed assertion digest must be a 64-char lowercase hex SHA-256 string."
            )
        if type(self.now) is not int or not 0 <= self.now <= 2**63 - 1:
            raise PoppyReplayError(
                "Assertion times must be nonnegative signed-64-bit integers."
            )
        expected = PoppyConsumedAssertion(self.scope, self.jti_sha256)
        if not isinstance(self.projected_consumption, PoppyConsumedAssertion):
            raise PoppyReplayError(
                "projected_consumption must be a PoppyConsumedAssertion."
            )
        if self.projected_consumption != expected:
            raise PoppyReplayError(
                "projected_consumption does not match scope and jti_sha256."
            )
        if type(self.would_consume) is not bool:
            raise PoppyReplayError("would_consume must be a boolean.")
        if self.existing_consumption is None:
            if not self.would_consume:
                raise PoppyReplayError(
                    "Unconsumed assertion preview must set would_consume=True."
                )
        else:
            if not isinstance(self.existing_consumption, PoppyConsumedAssertion):
                raise PoppyReplayError(
                    "existing_consumption must be a PoppyConsumedAssertion or None."
                )
            if self.existing_consumption != expected or self.would_consume:
                raise PoppyReplayError(
                    "Consumed assertion preview must match scope/digest and set would_consume=False."
                )

    @property
    def is_replay(self) -> bool:
        return not self.would_consume


class PoppyAssertionJournal:
    """Consume authenticated Session assertion IDs once in a shared local file.

    The caller verifies discovery, signatures, authenticated client, user/session
    binding and all other proofs before calling. IDs are retained without pruning.
    No token issuance or economic action is performed or atomically coupled here.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS poppy_assertion_replays (
                    auth_issuer TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    jti_sha256 TEXT NOT NULL CHECK(length(jti_sha256)=64),
                    PRIMARY KEY (auth_issuer,client_id,jti_sha256)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def consume(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims, *, now: int,
    ) -> None:
        """Use a fixed caller time snapshot; commit before return.

        For fresh admission time after waiting on a writer, use consume_with_clock.
        """
        key = self._validated_key(scope, assertion, now=now)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._consume_in_transaction(db, key)

    def consume_with_clock(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims, *,
        clock: Callable[[], int],
    ) -> None:
        """Sample fresh trusted time after the write lock, not before waiting.

        The callback must read trusted time when invoked. This checks expiry at
        that sample, not a physical commit/issuance deadline, and issues no token.
        """
        if not callable(clock):
            raise PoppyReplayError("A trusted clock callable is required.")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            key = self._validated_key(scope, assertion, now=clock())
            self._consume_in_transaction(db, key)

    def is_consumed(self, scope: PoppyReplayScope, jti: str) -> bool:
        """Read scoped replay history without consuming an ID or granting authority.

        Presence means only that this local journal previously burned the ID in
        this Company/client scope, not that a token was issued or delivered.
        Absence never substitutes for atomic consume or consume_with_clock.
        """
        key = self._jti_key(scope, jti)
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT 1 FROM poppy_assertion_replays"
                " WHERE auth_issuer=? AND client_id=? AND jti_sha256=?", key,
            ).fetchone()
            return row is not None

    def find_consumed(
        self, scope: PoppyReplayScope, jti: str,
    ) -> PoppyConsumedAssertion | None:
        """Return the persisted scoped digest record if consumed, or None."""
        key = self._jti_key(scope, jti)
        return self._lookup_consumed_key(scope, key)

    def read_consumed(
        self, scope: PoppyReplayScope, jti: str,
    ) -> PoppyConsumedAssertion:
        """Return the persisted scoped digest record or raise PoppyReplayError."""
        record = self.find_consumed(scope, jti)
        if record is None:
            raise PoppyReplayError("Session assertion ID has not been consumed.")
        return record

    def find_assertion_consumption(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims,
    ) -> PoppyConsumedAssertion | None:
        """Validate structural/scope claims (clock-independent) and look up consumption."""
        key = self._validated_assertion_key(scope, assertion)
        return self._lookup_consumed_key(scope, key)

    def read_assertion_consumption(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims,
    ) -> PoppyConsumedAssertion:
        """Validate structural/scope claims and return consumption or raise PoppyReplayError."""
        record = self.find_assertion_consumption(scope, assertion)
        if record is None:
            raise PoppyReplayError("Session assertion ID has not been consumed.")
        return record

    def is_assertion_consumed(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims,
    ) -> bool:
        """Validate structural/scope claims and check whether the assertion ID was consumed."""
        return self.find_assertion_consumption(scope, assertion) is not None

    def preview_consume(
        self, scope: PoppyReplayScope, assertion: SessionAssertionClaims, *, now: int,
    ) -> PoppyConsumptionPreview:
        """Preview consume() in one lock-free SELECT without burning the assertion ID."""
        key = self._validated_key(scope, assertion, now=now)
        existing = self._lookup_consumed_key(scope, key)
        projected = (
            existing
            if existing is not None
            else PoppyConsumedAssertion(scope, key[2])
        )
        return PoppyConsumptionPreview(
            scope=scope,
            jti_sha256=key[2],
            now=now,
            existing_consumption=existing,
            projected_consumption=projected,
            would_consume=existing is None,
        )

    def _lookup_consumed_key(
        self, scope: PoppyReplayScope, key: tuple[str, str, str],
    ) -> PoppyConsumedAssertion | None:
        with closing(self._connect()) as db:
            row = db.execute(
                "SELECT auth_issuer, client_id, jti_sha256"
                " FROM poppy_assertion_replays"
                " WHERE auth_issuer=? AND client_id=? AND jti_sha256=?",
                key,
            ).fetchone()
        if row is None:
            return None
        return _row_to_consumed_assertion(scope, key[2], row)

    @staticmethod
    def _jti_key(scope: PoppyReplayScope, jti: str) -> tuple[str, str, str]:
        if not isinstance(scope, PoppyReplayScope):
            raise PoppyReplayError("A trusted PoppyReplayScope is required.")
        if not isinstance(jti, str) or len(jti) < 22 or not URL_SAFE_BASE64_ID_RE.fullmatch(jti):
            raise PoppyReplayError("Local jti policy requires 22-256 base64url characters.")
        digest = hashlib.sha256(jti.encode("ascii")).hexdigest()
        return scope.auth_issuer, scope.client_id, digest

    @staticmethod
    def _validated_assertion_key(
        scope: PoppyReplayScope, assertion: SessionAssertionClaims,
    ) -> tuple[str, str, str]:
        if not isinstance(scope, PoppyReplayScope) or not isinstance(assertion, SessionAssertionClaims):
            raise PoppyReplayError("A trusted scope and decoded Session assertion are required.")
        if assertion.typ != "poppy-session+jwt" or assertion.iss != scope.client_id:
            raise PoppyReplayError("Session assertion type or authenticated client differs.")
        if any(type(value) is not int or not 0 <= value <= 2**63 - 1
               for value in (assertion.iat, assertion.exp)):
            raise PoppyReplayError("Assertion times must be nonnegative signed-64-bit integers.")
        metadata = verify_poppy_v02_assertion_metadata(
            assertion, auth_issuer=scope.auth_issuer, now=assertion.iat,
        )
        if not metadata.allowed:
            raise PoppyReplayError(f"Assertion metadata rejected: {metadata.error}.")
        return PoppyAssertionJournal._jti_key(scope, assertion.jti)

    @staticmethod
    def _validated_key(
        scope: PoppyReplayScope, assertion: SessionAssertionClaims, *, now: int,
    ) -> tuple[str, str, str]:
        if not isinstance(scope, PoppyReplayScope) or not isinstance(assertion, SessionAssertionClaims):
            raise PoppyReplayError("A trusted scope and decoded Session assertion are required.")
        if assertion.typ != "poppy-session+jwt" or assertion.iss != scope.client_id:
            raise PoppyReplayError("Session assertion type or authenticated client differs.")
        if any(type(value) is not int or not 0 <= value <= 2**63 - 1
               for value in (now, assertion.iat, assertion.exp)):
            raise PoppyReplayError("Assertion times must be nonnegative signed-64-bit integers.")
        metadata = verify_poppy_v02_assertion_metadata(
            assertion, auth_issuer=scope.auth_issuer, now=now,
        )
        if not metadata.allowed:
            raise PoppyReplayError(f"Assertion metadata rejected: {metadata.error}.")
        return PoppyAssertionJournal._jti_key(scope, assertion.jti)

    @staticmethod
    def _consume_in_transaction(
        db: sqlite3.Connection, key: tuple[str, str, str],
    ) -> None:
        if not db.in_transaction:
            raise PoppyReplayError("Assertion consumption requires an active transaction.")
        if db.execute(
            "SELECT 1 FROM poppy_assertion_replays"
            " WHERE auth_issuer=? AND client_id=? AND jti_sha256=?", key,
        ).fetchone():
            raise PoppyReplayDetected("Session assertion ID already consumed.")
        db.execute(
            "INSERT INTO poppy_assertion_replays"
            " (auth_issuer,client_id,jti_sha256) VALUES (?,?,?)", key,
        )
