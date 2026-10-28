"""Synthetic post-lock assertion expiry, shared history and explicit failures."""

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
from threading import Barrier, Event
from unittest.mock import Mock, patch

from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayError, PoppyReplayScope,
)


NOW = 1700000000
EXPIRY = NOW + 60
JTI = "synthetic_assertion_000001"


class PoppyAdmissionClockTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "replays.sqlite3"
        self.journal = PoppyAssertionJournal(self.path)
        self.scope = PoppyReplayScope(
            "https://auth.company.example", "https://agent.example/client.json",
        )
        self.assertion = SessionAssertionClaims(
            "poppy-session+jwt", self.scope.client_id, "synthetic-private-user",
            self.scope.auth_issuer, NOW, EXPIRY, JTI, "synthetic-private-session",
        )

    def consume(self, *, clock=None, scope=None, assertion=None):
        return self.journal.consume_with_clock(
            self.scope if scope is None else scope,
            self.assertion if assertion is None else assertion,
            clock=(lambda: NOW) if clock is None else clock,
        )

    def rows(self):
        with closing(self.journal._connect()) as db:
            return db.execute("SELECT * FROM poppy_assertion_replays").fetchall()

    def wait_then_sample(self, new_time, *, rejects):
        attempting = Event()
        current = [NOW]
        clock = Mock(side_effect=lambda: current[0])
        connect = self.journal._connect

        def traced_connect():
            db = connect()
            db.set_trace_callback(
                lambda statement: attempting.set() if statement == "BEGIN IMMEDIATE" else None,
            )
            return db

        with closing(sqlite3.connect(self.path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            with patch.object(self.journal, "_connect", side_effect=traced_connect):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.consume, clock=clock)
                    try:
                        self.assertTrue(attempting.wait(timeout=5))
                        clock.assert_not_called()
                        current[0] = new_time
                    finally:
                        blocker.commit()
                    if rejects:
                        with self.assertRaises(PoppyReplayError):
                            future.result(timeout=10)
                    else:
                        self.assertIsNone(future.result(timeout=10))
        clock.assert_called_once_with()

    def test_valid_sample_is_called_once_and_commits(self) -> None:
        clock = Mock(return_value=NOW)
        self.assertIsNone(self.consume(clock=clock))
        clock.assert_called_once_with()
        self.assertEqual(len(self.rows()), 1)

    def test_expiry_while_waiting_rejects_without_consuming_id(self) -> None:
        self.wait_then_sample(EXPIRY, rejects=True)
        self.assertEqual(self.rows(), [])

    def test_valid_after_waiting_consumes_once(self) -> None:
        self.wait_then_sample(EXPIRY - 1, rejects=False)
        self.assertEqual(len(self.rows()), 1)

    def test_exact_expiry_and_future_iat_are_rejected(self) -> None:
        for now in (NOW - 1, EXPIRY, EXPIRY + 1):
            with self.subTest(now=now), self.assertRaises(PoppyReplayError):
                self.consume(clock=lambda: now)
        self.assertEqual(self.rows(), [])
        self.consume(clock=lambda: EXPIRY - 1)

    def test_noncallable_clock_fails_before_opening_connection(self) -> None:
        with patch.object(self.journal, "_connect", side_effect=AssertionError("unexpected open")):
            for value in (None, NOW, "time", True):
                with self.subTest(value=value), self.assertRaises(PoppyReplayError):
                    self.journal.consume_with_clock(self.scope, self.assertion, clock=value)

    def test_invalid_clock_results_have_no_fallback_or_consumption(self) -> None:
        for value in (True, 1.0, "1700000000", None, -1, 2**63):
            with self.subTest(value=value), self.assertRaises(PoppyReplayError):
                self.consume(clock=lambda: value)
        self.assertEqual(self.rows(), [])
        self.consume()

    def test_clock_exception_propagates_without_consuming(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "synthetic clock failure"):
            self.consume(clock=Mock(side_effect=RuntimeError("synthetic clock failure")))
        self.assertEqual(self.rows(), [])
        self.consume()

    def test_busy_lock_never_samples_clock_or_returns_success(self) -> None:
        clock = Mock(return_value=NOW)
        candidate = sqlite3.connect(self.path, timeout=0)
        with closing(sqlite3.connect(self.path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            try:
                with patch.object(self.journal, "_connect", return_value=candidate):
                    with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                        self.consume(clock=clock)
            finally:
                blocker.rollback()
        clock.assert_not_called()
        self.assertEqual(self.rows(), [])

    def test_fixed_now_consumption_is_seen_by_clocked_path(self) -> None:
        self.journal.consume(self.scope, self.assertion, now=NOW)
        with self.assertRaises(PoppyReplayDetected):
            self.consume()
        self.assertEqual(len(self.rows()), 1)

    def test_clocked_consumption_is_seen_by_fixed_now_path(self) -> None:
        self.consume()
        with self.assertRaises(PoppyReplayDetected):
            self.journal.consume(self.scope, self.assertion, now=NOW + 1)
        self.assertEqual(len(self.rows()), 1)

    def test_scope_and_assertion_types_remain_explicit(self) -> None:
        for scope, assertion in ((None, self.assertion), (self.scope, {})):
            with self.assertRaises(PoppyReplayError):
                self.journal.consume_with_clock(scope, assertion, clock=lambda: NOW)
        self.assertEqual(self.rows(), [])

    def test_metadata_policy_and_identifier_bounds_are_reused(self) -> None:
        for field, value in (
            ("typ", "poppy-browser+jwt"), ("iss", "https://other.example"),
            ("aud", self.scope.auth_issuer + "/"), ("iat", True), ("exp", EXPIRY * 1.0),
            ("exp", NOW + 301), ("exp", NOW), ("jti", "a" * 21), ("jti", "a" * 257),
        ):
            with self.subTest(field=field), self.assertRaises(PoppyReplayError):
                self.consume(assertion=replace(self.assertion, **{field: value}))
        self.assertEqual(self.rows(), [])
        self.consume(assertion=replace(self.assertion, exp=NOW + 300))

    def test_signed64_time_endpoints_are_supported(self) -> None:
        for index, (iat, exp) in enumerate(((0, 1), (2**63 - 2, 2**63 - 1))):
            assertion = replace(self.assertion, iat=iat, exp=exp,
                                jti=f"synthetic_boundary_00000{index}")
            self.consume(assertion=assertion, clock=lambda: iat)
        self.assertEqual(len(self.rows()), 2)

    def test_scopes_are_separate_but_subject_and_session_are_not(self) -> None:
        self.consume()
        for change in ({"sub": "other-user"}, {"session_id": "other-session"}):
            with self.subTest(change=change), self.assertRaises(PoppyReplayDetected):
                self.consume(assertion=replace(self.assertion, **change))
        other_client = replace(self.scope, client_id="https://other-agent.example/client.json")
        self.consume(scope=other_client, assertion=replace(self.assertion, iss=other_client.client_id))
        other_company = replace(self.scope, auth_issuer="https://auth.other-company.example")
        self.consume(scope=other_company, assertion=replace(self.assertion, aud=other_company.auth_issuer))
        self.assertEqual(len(self.rows()), 3)

    def test_old_and_new_paths_concurrently_have_one_winner(self) -> None:
        barrier = Barrier(2)

        def act(legacy):
            barrier.wait(timeout=10)
            try:
                if legacy:
                    self.journal.consume(self.scope, self.assertion, now=NOW)
                else:
                    self.consume()
                return "consumed"
            except PoppyReplayDetected:
                return "replay"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(act, (False, True)))
        self.assertCountEqual(results, ["consumed", "replay"])
        self.assertEqual(len(self.rows()), 1)

    def test_commit_failure_observes_insert_then_rolls_back(self) -> None:
        observed = []

        class FailingCommit(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None:
                    observed.append(connection.execute(
                        "SELECT count(*) FROM poppy_assertion_replays",
                    ).fetchone()[0])
                    connection.rollback()
                    raise sqlite3.OperationalError("synthetic commit failure")
                return super().__exit__(exc_type, exc_value, traceback)

        db = sqlite3.connect(self.path, factory=FailingCommit)
        with patch.object(self.journal, "_connect", return_value=db):
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.consume()
        self.assertEqual(observed, [1])
        self.assertEqual(self.rows(), [])
        self.consume()

    def test_failure_after_actual_insert_rolls_back(self) -> None:
        original = self.journal._consume_in_transaction
        observed = []

        def fail(db, key):
            original(db, key)
            observed.append(db.execute("SELECT count(*) FROM poppy_assertion_replays").fetchone()[0])
            raise sqlite3.OperationalError("synthetic post-insert failure")

        with patch.object(self.journal, "_consume_in_transaction", side_effect=fail):
            with self.assertRaisesRegex(sqlite3.OperationalError, "post-insert failure"):
                self.consume()
        self.assertEqual(observed, [1])
        self.assertEqual(self.rows(), [])

    def test_participant_rejects_autocommit(self) -> None:
        key = self.journal._validated_key(self.scope, self.assertion, now=NOW)
        with closing(self.journal._connect()) as db:
            with self.assertRaisesRegex(PoppyReplayError, "active transaction"):
                self.journal._consume_in_transaction(db, key)
        self.assertEqual(self.rows(), [])

    def test_fresh_process_keeps_clocked_consumption(self) -> None:
        self.consume()
        script = """
import sys
from pathlib import Path
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import PoppyAssertionJournal, PoppyReplayScope, PoppyReplayDetected
scope = PoppyReplayScope('https://auth.company.example','https://agent.example/client.json')
assertion = SessionAssertionClaims('poppy-session+jwt',scope.client_id,'other-user',
    scope.auth_issuer,1700000000,1700000060,'synthetic_assertion_000001')
try:
    PoppyAssertionJournal(Path(sys.argv[1])).consume_with_clock(
        scope,assertion,clock=lambda:1700000001)
except PoppyReplayDetected:
    print('replay-rejected')
else:
    raise SystemExit('replay was admitted')
"""
        output = subprocess.run([sys.executable, "-c", script, str(self.path)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(output.stdout.strip(), "replay-rejected")

    def test_clock_and_private_claims_are_not_persisted(self) -> None:
        self.consume()
        self.assertEqual(self.rows(), [
            (self.scope.auth_issuer, self.scope.client_id, hashlib.sha256(JTI.encode()).hexdigest()),
        ])
        with closing(self.journal._connect()) as db:
            dump = "\n".join(db.iterdump())
        for value in (JTI, self.assertion.sub, self.assertion.session_id, str(NOW)):
            self.assertNotIn(value, dump)


if __name__ == "__main__":
    unittest.main()
