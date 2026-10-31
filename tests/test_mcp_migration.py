"""Date boundaries, strict metadata and honest exit-code regression checks."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.mcp_migration import (
    MAX_BYTES,
    Client,
    DualDeadlineFinding,
    Finding,
    assess,
    assess_dual_deadline,
    classify_deadline_window,
    load_deadline_from_source_report,
    load_inventory,
    main,
)


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "inventory.json"
        self.source_report = Path(self.directory.name) / "source-report.json"

    def write_inventory(self, rows: object) -> None:
        self.path.write_text(json.dumps({"clients": rows}), encoding="utf-8")

    def row(self, auth: str = "oauth", environment: str = "sandbox") -> dict[str, str]:
        return {"client_id": "synthetic-client", "environment": environment, "auth_method": auth}

    def write_source_report(
        self,
        *,
        deadline: str = "2026-11-30",
        checked_at: str = "2026-10-31T01:34:05+08:00",
        parser_version: str = "stripe-mcp-auth-notice-v1",
    ) -> None:
        self.source_report.write_text(json.dumps({
            "checked_at": checked_at,
            "observations": [
                {
                    "id": "stripe-mcp",
                    "status": "ok",
                    "policy_error": None,
                    "policy_facts": {
                        "parser_version": parser_version,
                        "deadline": deadline,
                    },
                }
            ],
        }), encoding="utf-8")

    def run_cli(
        self,
        as_of: str = "2026-10-12",
        source_report: Path | None = None,
        *,
        strict_previous_deadline: bool = False,
    ) -> tuple[int, str, str]:
        output, errors = io.StringIO(), io.StringIO()
        argv = ["migration", "--inventory", str(self.path), "--as-of", as_of]
        if source_report is not None:
            argv.extend(["--source-report", str(source_report)])
        if strict_previous_deadline:
            argv.append("--strict-previous-deadline")
        with (
            patch("sys.argv", argv),
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
        self.assertEqual(report["policy_checked_on"], "2026-10-23")
        code, output, _ = self.run_cli("2026-10-19")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["calendar_days_until_deadline"], 42)
        code, output, _ = self.run_cli("2026-10-23")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["calendar_days_until_deadline"], 38)
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
        self.assertEqual(json.loads(output)["deadline_source"], "hardcoded-reviewed-baseline")
        self.assertIsNone(json.loads(output)["deadline_parser_version"])

    def test_source_report_deadline_override_changes_boundary_status(self) -> None:
        self.write_inventory([self.row("full_access_secret")])
        self.write_source_report(deadline="2026-10-31")
        code, output, errors = self.run_cli("2026-10-31")
        self.assertEqual((code, errors), (1, ""))
        self.assertEqual(json.loads(output)["findings"][0]["status"], "migration_required")
        code, output, errors = self.run_cli("2026-10-31", source_report=self.source_report)
        self.assertEqual((code, errors), (1, ""))
        report = json.loads(output)
        self.assertEqual(report["findings"][0]["status"], "blocked_by_documented_policy")
        self.assertEqual(report["deadline"], "2026-10-31")
        self.assertEqual(report["calendar_days_until_deadline"], 0)
        self.assertEqual(report["policy_checked_on"], "2026-10-31")
        self.assertEqual(report["deadline_source"], "source-monitor-selected-facts")
        self.assertEqual(report["deadline_parser_version"], "stripe-mcp-auth-notice-v1")

    def test_source_report_requires_one_valid_stripe_mcp_fact_row(self) -> None:
        self.write_inventory([self.row("full_access_secret")])
        self.source_report.write_text(json.dumps({
            "checked_at": "2026-10-31T01:34:05+08:00",
            "observations": [
                {
                    "id": "stripe-mcp",
                    "status": "ok",
                    "policy_error": None,
                    "policy_facts": {"parser_version": "other-parser-v1", "deadline": "2026-10-31"},
                }
            ],
        }), encoding="utf-8")
        code, output, errors = self.run_cli("2026-10-31", source_report=self.source_report)
        self.assertEqual((code, output), (2, ""))
        self.assertEqual(json.loads(errors)["status"], "invalid_inventory")

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

    def test_dual_deadline_window_classification_and_contradiction_exposure(self) -> None:
        for auth in ["full_access_secret", "restricted_without_agent_tag"]:
            client = Client(**self.row(auth, "live"))
            for day, expected_phase, expected_primary, expected_strict, expected_contradiction in [
                (date(2026, 10, 30), "before_previous_deadline", "migration_required", "migration_required", False),
                (date(2026, 10, 31), "contradiction_window", "migration_required", "blocked_by_documented_policy", True),
                (date(2026, 11, 1), "contradiction_window", "migration_required", "blocked_by_documented_policy", True),
                (date(2026, 11, 29), "contradiction_window", "migration_required", "blocked_by_documented_policy", True),
                (date(2026, 11, 30), "on_or_after_deadline", "blocked_by_documented_policy", "blocked_by_documented_policy", False),
                (date(2026, 12, 1), "on_or_after_deadline", "blocked_by_documented_policy", "blocked_by_documented_policy", False),
            ]:
                with self.subTest(auth=auth, day=day):
                    self.assertEqual(classify_deadline_window(as_of=day), expected_phase)
                    dual = assess_dual_deadline(client, as_of=day)
                    self.assertEqual(dual.window_phase, expected_phase)
                    self.assertEqual(dual.primary_status, expected_primary)
                    self.assertEqual(dual.strict_previous_status, expected_strict)
                    self.assertEqual(dual.contradiction_exposed, expected_contradiction)
                    if expected_contradiction:
                        self.assertIn("Earlier 2026-10-31 cutoff has elapsed", dual.action)

        for auth in ["oauth", "agent_key"]:
            client = Client(**self.row(auth, "sandbox"))
            for day in [date(2026, 10, 30), date(2026, 10, 31), date(2026, 11, 1), date(2026, 11, 30)]:
                with self.subTest(auth=auth, day=day):
                    dual = assess_dual_deadline(client, as_of=day)
                    self.assertEqual(dual.primary_status, "recorded_supported_unverified")
                    self.assertEqual(dual.strict_previous_status, "recorded_supported_unverified")
                    self.assertFalse(dual.contradiction_exposed)

    def test_cli_strict_previous_deadline_blocks_legacy_keys_on_2026_11_01(self) -> None:
        rows = [
            {**self.row("oauth"), "client_id": "interactive"},
            {**self.row("full_access_secret", "live"), "client_id": "legacy"},
            {**self.row("agent_key"), "client_id": "autonomous"},
            {**self.row("restricted_without_agent_tag"), "client_id": "untagged"},
        ]
        self.write_inventory(rows)
        code, output, errors = self.run_cli("2026-11-01")
        self.assertEqual((code, errors), (1, ""))
        default_report = json.loads(output)
        self.assertEqual(default_report["deadline"], "2026-11-30")
        self.assertEqual(default_report["effective_deadline"], "2026-11-30")
        self.assertFalse(default_report["strict_previous_deadline_enforced"])
        self.assertTrue(default_report["previous_deadline_elapsed"])
        self.assertEqual(default_report["calendar_days_until_previous_deadline"], -1)
        self.assertEqual(default_report["deadline_window_phase"], "contradiction_window")
        self.assertEqual(default_report["contradiction_exposed_count"], 2)
        self.assertEqual(default_report["findings"][1]["status"], "migration_required")
        self.assertEqual(default_report["findings"][3]["status"], "migration_required")

        code, output, errors = self.run_cli("2026-11-01", strict_previous_deadline=True)
        self.assertEqual((code, errors), (1, ""))
        strict_report = json.loads(output)
        self.assertEqual(strict_report["deadline"], "2026-11-30")
        self.assertEqual(strict_report["effective_deadline"], "2026-10-31")
        self.assertTrue(strict_report["strict_previous_deadline_enforced"])
        self.assertEqual(strict_report["findings"][0]["status"], "recorded_supported_unverified")
        self.assertEqual(strict_report["findings"][1]["status"], "blocked_by_documented_policy")
        self.assertEqual(strict_report["findings"][2]["status"], "recorded_supported_unverified")
        self.assertEqual(strict_report["findings"][3]["status"], "blocked_by_documented_policy")

    def test_finding_and_dual_deadline_finding_fail_closed_validation(self) -> None:
        valid_finding = Finding(
            client_id="synthetic-client",
            environment="sandbox",
            auth_method="oauth",
            status="recorded_supported_unverified",
            action="Verify permissions.",
        )
        self.assertEqual(valid_finding.status, "recorded_supported_unverified")

        for kwargs in [
            {"client_id": "BAD_ID"},
            {"environment": "prod"},
            {"auth_method": "unknown"},
            {"status": "unknown_status"},
            {"action": "   "},
            {"auth_method": "oauth", "status": "migration_required"},
            {"auth_method": "full_access_secret", "status": "recorded_supported_unverified"},
        ]:
            merged = {
                "client_id": "synthetic-client",
                "environment": "sandbox",
                "auth_method": "oauth",
                "status": "recorded_supported_unverified",
                "action": "Verify permissions.",
                **kwargs,
            }
            with self.subTest(finding_kwargs=kwargs):
                with self.assertRaises(ValueError):
                    Finding(**merged)  # type: ignore[arg-type]

        base_dual = {
            "client_id": "synthetic-client",
            "environment": "live",
            "auth_method": "full_access_secret",
            "as_of": date(2026, 11, 1),
            "previous_deadline": date(2026, 10, 31),
            "deadline": date(2026, 11, 30),
            "window_phase": "contradiction_window",
            "primary_status": "migration_required",
            "strict_previous_status": "blocked_by_documented_policy",
            "contradiction_exposed": True,
            "action": "Immediate migration required.",
        }
        self.assertTrue(DualDeadlineFinding(**base_dual).contradiction_exposed)  # type: ignore[arg-type]
        for dual_kwargs in [
            {"as_of": datetime(2026, 11, 1)},
            {"previous_deadline": date(2026, 12, 1)},
            {"window_phase": "before_previous_deadline"},
            {"primary_status": "blocked_by_documented_policy"},
            {"strict_previous_status": "migration_required"},
            {"contradiction_exposed": False},
            {"contradiction_exposed": 1},
            {"action": ""},
        ]:
            with self.subTest(dual_kwargs=dual_kwargs):
                with self.assertRaises(ValueError):
                    DualDeadlineFinding(**{**base_dual, **dual_kwargs})  # type: ignore[arg-type]

        for bad_client in [None, "client", {"client_id": "a"}]:
            with self.subTest(bad_client=bad_client):
                with self.assertRaises(ValueError):
                    assess(bad_client, as_of=date(2026, 11, 1))  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    assess_dual_deadline(bad_client, as_of=date(2026, 11, 1))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            load_inventory("not-a-path")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            load_deadline_from_source_report("not-a-path")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
