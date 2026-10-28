"""Synthetic durable assertion replay, strict local policy and storage failures."""

import hashlib
import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from lab.poppy_guard import SessionAssertionClaims, verify_poppy_v02_assertion_metadata
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayError, PoppyReplayScope,
)

NOW = 1700000000
ISSUER = "https://auth.company.example"
CLIENT = "https://agent.example/client.json"
JTI = "synthetic_assertion_000001"


class PoppyReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "replays.sqlite3"
        self.journal = PoppyAssertionJournal(self.path)
        self.scope = PoppyReplayScope(ISSUER, CLIENT)
        self.assertion = SessionAssertionClaims(
            typ="poppy-session+jwt", iss=CLIENT, sub="synthetic-user-private",
            aud=ISSUER, iat=NOW, exp=NOW + 60, jti=JTI,
            session_id="synthetic-session-private",
        )

    def consume(self, *, assertion=None, scope=None, now=NOW) -> None:
        self.journal.consume(
            self.scope if scope is None else scope,
            self.assertion if assertion is None else assertion, now=now,
        )

    def rows(self):
        with closing(self.journal._connect()) as db:
            return db.execute("SELECT * FROM poppy_assertion_replays").fetchall()

    def test_consumption_is_durable_and_repeat_is_explicit_error(self) -> None:
        self.assertIsNone(self.consume())
        with self.assertRaises(PoppyReplayDetected):
            self.consume()
        self.assertEqual(len(self.rows()), 1)

    def test_reopening_journal_does_not_forget_consumption(self) -> None:
        self.consume()
        reopened = PoppyAssertionJournal(self.path)
        with self.assertRaises(PoppyReplayDetected):
            reopened.consume(self.scope, self.assertion, now=NOW)

    def test_fresh_process_rejects_consumed_assertion(self) -> None:
        self.consume()
        script = """
import sys
from pathlib import Path
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import PoppyAssertionJournal, PoppyReplayScope, PoppyReplayDetected
s = PoppyReplayScope('https://auth.company.example','https://agent.example/client.json')
a = SessionAssertionClaims('poppy-session+jwt',s.client_id,'different-user',s.auth_issuer,
    1700000000,1700000060,'synthetic_assertion_000001')
try:
    PoppyAssertionJournal(Path(sys.argv[1])).consume(s,a,now=1700000001)
except PoppyReplayDetected:
    print('replay-rejected')
else:
    raise SystemExit('replay was admitted')
"""
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(output.stdout.strip(), "replay-rejected")

    def test_concurrent_independent_journals_have_one_winner(self) -> None:
        barrier = Barrier(8)

        def act(_):
            journal = PoppyAssertionJournal(self.path)
            barrier.wait(timeout=10)
            try:
                journal.consume(self.scope, self.assertion, now=NOW)
                return "consumed"
            except PoppyReplayDetected:
                return "replay"

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(act, range(8)))
        self.assertEqual(results.count("consumed"), 1)
        self.assertEqual(results.count("replay"), 7)
        self.assertEqual(len(self.rows()), 1)

    def test_different_client_has_independent_namespace(self) -> None:
        self.consume()
        scope = replace(self.scope, client_id="https://other-agent.example/client.json")
        self.consume(scope=scope, assertion=replace(self.assertion, iss=scope.client_id))
        self.assertEqual(len(self.rows()), 2)

    def test_different_company_has_independent_namespace(self) -> None:
        self.consume()
        scope = replace(self.scope, auth_issuer="https://auth.other-company.example")
        self.consume(scope=scope, assertion=replace(self.assertion, aud=scope.auth_issuer))
        self.assertEqual(len(self.rows()), 2)

    def test_different_jti_is_not_a_replay(self) -> None:
        self.consume()
        self.consume(assertion=replace(self.assertion, jti="synthetic_assertion_000002"))
        self.assertEqual(len(self.rows()), 2)

    def test_user_or_session_change_does_not_create_new_namespace(self) -> None:
        self.consume()
        for change in ({"sub": "other-user"}, {"session_id": "other-session"}):
            with self.subTest(change=change), self.assertRaises(PoppyReplayDetected):
                self.consume(assertion=replace(self.assertion, **change))
        self.assertEqual(len(self.rows()), 1)

    def test_later_valid_assertion_cannot_reuse_permanently_retained_id(self) -> None:
        self.consume()
        later = replace(self.assertion, iat=NOW + 120, exp=NOW + 180)
        with self.assertRaises(PoppyReplayDetected):
            self.consume(assertion=later, now=NOW + 120)
        self.assertEqual(len(self.rows()), 1)

    def test_exact_client_binding_required_before_consumption(self) -> None:
        with self.assertRaises(PoppyReplayError):
            self.consume(assertion=replace(self.assertion, iss=CLIENT + "/other"))
        self.assertEqual(self.rows(), [])
        self.consume()

    def test_audience_must_be_exact_company_issuer(self) -> None:
        for aud in (ISSUER + "/", ISSUER.upper(), ISSUER + "/token", [ISSUER], None):
            with self.subTest(aud=aud), self.assertRaises(PoppyReplayError):
                self.consume(assertion=replace(self.assertion, aud=aud))
        self.assertEqual(self.rows(), [])

    def test_only_session_assertion_type_is_admitted(self) -> None:
        for typ in ("JWT", "dpop+jwt", "poppy-browser+jwt", "", None):
            with self.subTest(typ=typ), self.assertRaises(PoppyReplayError):
                self.consume(assertion=replace(self.assertion, typ=typ))
        self.assertEqual(self.rows(), [])

    def test_exact_five_minute_lifetime_and_iat_boundary_are_allowed(self) -> None:
        self.consume(assertion=replace(self.assertion, exp=NOW + 300))
        self.assertEqual(len(self.rows()), 1)

    def test_expiry_is_exclusive_and_future_assertion_is_rejected(self) -> None:
        for now in (NOW - 1, NOW + 60):
            with self.subTest(now=now), self.assertRaises(PoppyReplayError):
                self.consume(now=now)
        self.assertEqual(self.rows(), [])

    def test_overlong_zero_and_negative_lifetime_are_rejected(self) -> None:
        for exp in (NOW + 301, NOW, NOW - 1):
            with self.subTest(exp=exp), self.assertRaises(PoppyReplayError):
                self.consume(assertion=replace(self.assertion, exp=exp))
        self.assertEqual(self.rows(), [])

    def test_integer_type_and_range_are_strict(self) -> None:
        for field in ("iat", "exp", "now"):
            for value in (True, 1.0, "1700000000", None, -1, 2**63):
                with self.subTest(field=field, value=value), self.assertRaises(PoppyReplayError):
                    if field == "now":
                        self.consume(now=value)
                    else:
                        self.consume(assertion=replace(self.assertion, **{field: value}))
        self.assertEqual(self.rows(), [])

    def test_local_jti_format_rejects_short_unbounded_and_non_base64url(self) -> None:
        for jti in ("a" * 21, "a" * 257, "x" * 22 + "\n", " " * 22, "é" * 22, None, 123):
            with self.subTest(jti=jti), self.assertRaises(PoppyReplayError):
                self.consume(assertion=replace(self.assertion, jti=jti))
        self.assertEqual(self.rows(), [])

    def test_local_identifier_length_boundaries_are_inclusive(self) -> None:
        for length in (22, 256):
            self.consume(assertion=replace(self.assertion, jti="a" * length))
        self.assertEqual(len(self.rows()), 2)

    def test_invalid_input_does_not_burn_an_otherwise_valid_id(self) -> None:
        with self.assertRaises(PoppyReplayError):
            self.consume(assertion=replace(self.assertion, exp=NOW + 301))
        self.consume()
        self.assertEqual(len(self.rows()), 1)

    def test_scope_and_claim_types_are_explicitly_checked(self) -> None:
        with self.assertRaises(PoppyReplayError):
            self.journal.consume(None, self.assertion, now=NOW)
        with self.assertRaises(PoppyReplayError):
            self.journal.consume(self.scope, {}, now=NOW)
        self.assertEqual(self.rows(), [])

    def test_scope_configuration_rejects_blank_or_noncanonical_text(self) -> None:
        for value in ("", " ", " https://example.com", "https://example.com ", None, True):
            for field in ("auth_issuer", "client_id"):
                with self.subTest(field=field, value=value), self.assertRaises(PoppyReplayError):
                    replace(self.scope, **{field: value})

    def test_only_digest_and_public_namespace_are_persisted(self) -> None:
        self.consume()
        self.assertEqual(self.rows(), [
            (ISSUER, CLIENT, hashlib.sha256(JTI.encode("ascii")).hexdigest()),
        ])
        with closing(self.journal._connect()) as db:
            dump = "\n".join(db.iterdump())
        for private in (JTI, self.assertion.sub, self.assertion.session_id, "poppy-session+jwt"):
            self.assertNotIn(private, dump)

    def test_commit_failure_rolls_back_and_never_returns_success(self) -> None:
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(connection.execute(
                        "SELECT COUNT(*) FROM poppy_assertion_replays",
                    ).fetchone()[0])
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        connection = sqlite3.connect(self.path, factory=FailingCommit)
        with patch.object(self.journal, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.consume()
        self.assertEqual(observed, [1])
        self.assertEqual(self.rows(), [])
        self.consume()

    def test_insert_failure_propagates_without_partial_admission(self) -> None:
        with closing(self.journal._connect()) as db, db:
            db.execute("""
                CREATE TRIGGER fail_insert BEFORE INSERT ON poppy_assertion_replays
                BEGIN SELECT RAISE(ABORT,'synthetic insert failure'); END
            """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "insert failure"):
            self.consume()
        self.assertEqual(self.rows(), [])

    def test_storage_connection_failure_is_not_replay_or_success(self) -> None:
        with patch.object(
            self.journal, "_connect", side_effect=sqlite3.OperationalError("synthetic unavailable"),
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "unavailable"):
                self.consume()
        self.assertEqual(self.rows(), [])

    def test_pure_metadata_validation_does_not_consume_history(self) -> None:
        for _ in range(2):
            result = verify_poppy_v02_assertion_metadata(
                self.assertion, auth_issuer=ISSUER, now=NOW,
            )
            self.assertTrue(result.allowed)
        self.assertEqual(self.rows(), [])
        self.consume()
        with self.assertRaises(PoppyReplayDetected):
            self.consume()


if __name__ == "__main__":
    unittest.main()
