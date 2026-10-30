"""Synthetic scoped Poppy assertion replay history lookup, not admission authority."""

import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayError, PoppyReplayScope,
)

NOW = 1700000000
ISSUER = "https://auth.company.example"
CLIENT = "https://agent.example/client.json"
JTI = "synthetic_assertion_000001"


class PoppyReplayReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "replays.sqlite3"
        self.journal = PoppyAssertionJournal(self.path)
        self.scope = PoppyReplayScope(ISSUER, CLIENT)
        self.assertion = SessionAssertionClaims(
            typ="poppy-session+jwt", iss=CLIENT, sub="synthetic-user-private",
            aud=ISSUER, iat=NOW, exp=NOW + 60, jti=JTI,
            session_id="synthetic-session-private",
        )

    def rows(self):
        with closing(self.journal._connect()) as db:
            return db.execute("SELECT * FROM poppy_assertion_replays").fetchall()

    def test_absence_returns_false_without_consuming_id(self) -> None:
        self.assertFalse(self.journal.is_consumed(self.scope, JTI))
        self.assertEqual(self.rows(), [])
        self.journal.consume(self.scope, self.assertion, now=NOW)
        self.assertTrue(self.journal.is_consumed(self.scope, JTI))

    def test_fixed_now_consumption_is_observed(self) -> None:
        self.journal.consume(self.scope, self.assertion, now=NOW)
        self.assertTrue(self.journal.is_consumed(self.scope, JTI))
        with self.assertRaises(PoppyReplayDetected):
            self.journal.consume(self.scope, self.assertion, now=NOW + 1)

    def test_clocked_consumption_is_observed(self) -> None:
        self.journal.consume_with_clock(self.scope, self.assertion, clock=lambda: NOW)
        self.assertTrue(self.journal.is_consumed(self.scope, JTI))
        with self.assertRaises(PoppyReplayDetected):
            self.journal.consume_with_clock(self.scope, self.assertion, clock=lambda: NOW + 1)

    def test_reader_survives_reopen_and_fresh_process(self) -> None:
        self.journal.consume(self.scope, self.assertion, now=NOW)
        self.assertTrue(PoppyAssertionJournal(self.path).is_consumed(self.scope, JTI))
        script = (
            "import sys; from pathlib import Path; "
            "from lab.poppy_replay import PoppyAssertionJournal, PoppyReplayScope; "
            "s = PoppyReplayScope('https://auth.company.example','https://agent.example/client.json'); "
            "print(PoppyAssertionJournal(Path(sys.argv[1])).is_consumed(s,'synthetic_assertion_000001'))"
        )
        output = subprocess.run(
            [sys.executable, "-c", script, str(self.path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(output.stdout.strip(), "True")

    def test_every_scope_dimension_is_isolated(self) -> None:
        self.journal.consume(self.scope, self.assertion, now=NOW)
        other_company = replace(self.scope, auth_issuer="https://auth.other-company.example")
        other_client = replace(self.scope, client_id="https://other-agent.example/client.json")
        self.assertFalse(self.journal.is_consumed(other_company, JTI))
        self.assertFalse(self.journal.is_consumed(other_client, JTI))
        self.journal.consume(other_company, replace(self.assertion, aud=other_company.auth_issuer), now=NOW)
        self.journal.consume(other_client, replace(self.assertion, iss=other_client.client_id), now=NOW)
        self.assertTrue(self.journal.is_consumed(other_company, JTI))
        self.assertTrue(self.journal.is_consumed(other_client, JTI))

    def test_distinct_jtis_in_same_scope_remain_independent(self) -> None:
        other_jti = "synthetic_assertion_000002"
        self.journal.consume(self.scope, self.assertion, now=NOW)
        self.assertTrue(self.journal.is_consumed(self.scope, JTI))
        self.assertFalse(self.journal.is_consumed(self.scope, other_jti))
        self.journal.consume(self.scope, replace(self.assertion, jti=other_jti), now=NOW)
        self.assertTrue(self.journal.is_consumed(self.scope, other_jti))

    def test_failed_admission_does_not_mark_jti_consumed(self) -> None:
        for invalid in (
            replace(self.assertion, exp=NOW + 301),
            replace(self.assertion, aud=ISSUER + "/token"),
            replace(self.assertion, typ="poppy-browser+jwt"),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(PoppyReplayError):
                self.journal.consume(self.scope, invalid, now=NOW)
        self.assertFalse(self.journal.is_consumed(self.scope, JTI))

    def test_rolled_back_commit_is_not_reported_consumed(self) -> None:
        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        connection = sqlite3.connect(self.path, factory=FailingCommit)
        with patch.object(self.journal, "_connect", return_value=connection):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.journal.consume(self.scope, self.assertion, now=NOW)
        self.assertFalse(self.journal.is_consumed(self.scope, JTI))

    def test_invalid_scope_rejected_before_opening_connection(self) -> None:
        with patch.object(self.journal, "_connect") as connect:
            for scope in (None, {}, ISSUER, (ISSUER, CLIENT)):
                with self.subTest(scope=scope), self.assertRaises(PoppyReplayError):
                    self.journal.is_consumed(scope, JTI)
            connect.assert_not_called()

    def test_invalid_jti_rejected_before_opening_connection(self) -> None:
        with patch.object(self.journal, "_connect") as connect:
            for jti in (
                None, True, 123, [], "", "a" * 21, "a" * 257,
                "x" * 22 + "\n", " " * 22, "é" * 22, "jti_00000000000000000' OR 1=1",
            ):
                with self.subTest(jti=jti), self.assertRaises(PoppyReplayError):
                    self.journal.is_consumed(self.scope, jti)
            connect.assert_not_called()

    def test_inclusive_jti_length_boundaries_are_accepted(self) -> None:
        for length in (22, 256):
            candidate = "a" * length
            self.assertFalse(self.journal.is_consumed(self.scope, candidate))
            self.journal.consume(self.scope, replace(self.assertion, jti=candidate), now=NOW)
            self.assertTrue(self.journal.is_consumed(self.scope, candidate))

    def test_storage_errors_propagate_instead_of_returning_false(self) -> None:
        with patch.object(self.journal, "_connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                self.journal.is_consumed(self.scope, JTI)

    def test_select_only_does_not_take_writer_lock_or_call_metadata_verifier(self) -> None:
        self.journal.consume(self.scope, self.assertion, now=NOW)
        statements: list[str] = []
        connect = self.journal._connect

        def traced():
            db = connect()
            db.set_trace_callback(statements.append)
            return db

        with patch.object(self.journal, "_connect", side_effect=traced), patch(
            "lab.poppy_replay.verify_poppy_v02_assertion_metadata",
            side_effect=AssertionError("unexpected metadata check"),
        ):
            self.assertTrue(self.journal.is_consumed(self.scope, JTI))
            self.assertFalse(self.journal.is_consumed(self.scope, "synthetic_assertion_absent"))
        self.assertEqual(len(statements), 2)
        self.assertTrue(all(stmt.startswith("SELECT 1 FROM poppy_assertion_replays") for stmt in statements))

    def test_history_lookup_does_not_bypass_stale_admission_rejection(self) -> None:
        self.assertFalse(self.journal.is_consumed(self.scope, JTI))
        with self.assertRaises(PoppyReplayError):
            self.journal.consume_with_clock(self.scope, self.assertion, clock=lambda: NOW + 60)
        self.assertFalse(self.journal.is_consumed(self.scope, JTI))


if __name__ == "__main__":
    unittest.main()
