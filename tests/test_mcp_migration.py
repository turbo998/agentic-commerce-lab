"""Date boundaries, strict metadata and honest exit-code regression checks."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.mcp_migration import MAX_BYTES, Client, assess, load_inventory, main


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inventory.json"

    def write_inventory(self, rows: object) -> None:
        self.path.write_text(json.dumps({"clients": rows}), encoding="utf-8")

    def row(self, auth: str = "oauth", environment: str = "sandbox") -> dict[str, str]:
        return {"client_id": "synthetic-client", "environment": environment, "auth_method": auth}

    def run_cli(self, as_of: str = "2026-10-12") -> tuple[int, str, str]:
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("sys.argv", ["migration", "--inventory", str(self.path), "--as-of", as_of]),
            redirect_stdout(output), redirect_stderr(errors),
        ):
            code = main()
        return code, output.getvalue(), errors.getvalue()

    def test_deadline_boundaries_for_both_legacy_classes_and_environments(self) -> None:
        for auth in ["full_access_secret", "restricted_without_agent_tag"]:
            for environment in ["sandbox", "live"]:
                client = Client(**self.row(auth, environment))
                for day, expected in [
                    (date(2026, 10, 16), "migration_required"),
                    (date(2026, 10, 31), "migration_required"),
                    (date(2026, 11, 29), "migration_required"),
                    (date(2026, 11, 30), "blocked_by_documented_policy"),
                    (date(2026, 12, 1), "blocked_by_documented_policy"),
                ]:
                    with self.subTest(auth=auth, environment=environment, day=day):
                        self.assertEqual(assess(client, as_of=day).status, expected)

    def test_supported_metadata_never_claims_verified_access(self) -> None:
        for auth in ["oauth", "agent_key"]:
            for day in [date(2026, 10, 16), date(2026, 11, 30), date(2027, 1, 1)]:
                with self.subTest(auth=auth, day=day):
                    finding = assess(Client(**self.row(auth)), as_of=day)
                    self.assertEqual(finding.status, "recorded_supported_unverified")
                    self.assertIn("Verify permissions", finding.action)

    def test_cli_mixed_inventory_is_nonzero_even_before_deadline(self) -> None:
        rows = [
            {**self.row("oauth"), "client_id": "interactive"},
            {**self.row("full_access_secret", "live"), "client_id": "legacy"},
            {**self.row("agent_key"), "client_id": "autonomous"},
            {**self.row("restricted_without_agent_tag"), "client_id": "untagged"},
        ]
        self.write_inventory(rows)
        code, output, errors = self.run_cli("2026-10-16")
        self.assertEqual(code, 1)
        self.assertEqual(errors, "")
        report = json.loads(output)
        self.assertEqual(report["migration_count"], 2)
        self.assertEqual(report["deadline"], "2026-11-30")
        self.assertEqual(report["previous_deadline"], "2026-10-31")
        self.assertEqual(report["enforcement_starts"], "2026-12-01")
        self.assertEqual(report["calendar_days_until_deadline"], 45)
        self.assertEqual(report["account_verification"], "not_performed")
        self.assertIn("not specified", report["cutoff_time"])
        self.assertEqual(report["policy_source"], "https://docs.stripe.com/mcp")
        self.assertEqual(report["policy_checked_on"], "2026-10-18")
        code, output, _ = self.run_cli("2026-10-18")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["calendar_days_until_deadline"], 43)
        code, output, _ = self.run_cli("2026-10-31")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["calendar_days_until_deadline"], 30)
        self.assertEqual(json.loads(output)["findings"][1]["status"], "migration_required")
        code, output, _ = self.run_cli("2026-11-30")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["calendar_days_until_deadline"], 0)
        self.assertEqual(json.loads(output)["findings"][1]["status"], "blocked_by_documented_policy")

    def test_all_supported_inventory_exit_zero_is_metadata_only(self) -> None:
        self.write_inventory([self.row()])
        code, output, errors = self.run_cli()
        self.assertEqual((code, errors), (0, ""))
        self.assertEqual(json.loads(output)["kind"], "offline-metadata-only")

    def test_invalid_rows_and_unknown_auth_are_rejected(self) -> None:
        for rows in [
            [], {}, [None], [self.row("unknown")], [self.row(environment="production")],
            [{**self.row(), "client_id": True}], [{**self.row(), "client_id": "sk_live_fake"}],
            [{**self.row(), "auth_method": []}], [{**self.row(), "environment": None}],
            [{**self.row(), "api_key": "synthetic-sensitive-value"}],
            [{"client_id": "incomplete"}],
        ]:
            with self.subTest(rows=rows):
                self.write_inventory(rows)
                code, output, errors = self.run_cli()
                self.assertEqual((code, output), (2, ""))
                self.assertEqual(json.loads(errors)["status"], "invalid_inventory")
                self.assertNotIn("synthetic-sensitive-value", errors)

    def test_duplicate_client_is_scoped_to_environment(self) -> None:
        self.write_inventory([self.row(), self.row(environment="live")])
        self.assertEqual(len(load_inventory(self.path)), 2)
        self.write_inventory([self.row(), self.row("agent_key")])
        with self.assertRaisesRegex(ValueError, "Duplicate client"):
            load_inventory(self.path)

    def test_duplicate_json_fields_and_unknown_root_fields_are_rejected(self) -> None:
        for body in [
            '{"clients": [], "clients": []}',
            '{"clients": [{"client_id": "a", "client_id": "b"}]}',
            '{"clients": [], "token": "synthetic-sensitive-value"}',
            '[]',
        ]:
            with self.subTest(body=body):
                self.path.write_text(body, encoding="utf-8")
                self.assertEqual(self.run_cli()[0], 2)

    def test_read_failures_are_explicit_and_do_not_echo_contents(self) -> None:
        self.assertEqual(self.run_cli()[0], 2)
        for body in [b'{"synthetic-sensitive-value": ', b"\xff", b"x" * (MAX_BYTES + 1)]:
            with self.subTest(body=body[:20]):
                self.path.write_bytes(body)
                code, output, errors = self.run_cli()
                self.assertEqual((code, output), (2, ""))
                self.assertNotIn("synthetic-sensitive-value", errors)

    def test_timestamp_cannot_supply_an_ambiguous_cutoff(self) -> None:
        with self.assertRaises(ValueError):
            assess(Client(**self.row()), as_of=datetime(2026, 10, 31))

    def test_example_is_four_synthetic_metadata_records(self) -> None:
        clients = load_inventory(Path("lab") / "mcp_inventory.example.json")
        self.assertEqual(len(clients), 4)
        self.assertTrue(all(client.client_id.startswith("synthetic-") for client in clients))


if __name__ == "__main__":
    unittest.main()
