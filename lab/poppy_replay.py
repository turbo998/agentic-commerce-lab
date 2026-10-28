"""Offline durable Session assertion admission, not JWT or OAuth verification."""

import hashlib
import sqlite3
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
        """Commit before return; replay/storage failure never becomes success."""
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
        if not URL_SAFE_BASE64_ID_RE.fullmatch(assertion.jti):
            raise PoppyReplayError("Local jti policy requires 22-256 base64url characters.")
        digest = hashlib.sha256(assertion.jti.encode("ascii")).hexdigest()
        key = scope.auth_issuer, scope.client_id, digest
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM poppy_assertion_replays"
                " WHERE auth_issuer=? AND client_id=? AND jti_sha256=?", key,
            ).fetchone():
                raise PoppyReplayDetected("Session assertion ID already consumed.")
            db.execute(
                "INSERT INTO poppy_assertion_replays"
                " (auth_issuer,client_id,jti_sha256) VALUES (?,?,?)", key,
            )
