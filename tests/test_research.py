import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.check_research import ROOT, validate


class ResearchTests(unittest.TestCase):
    def test_repository_registry(self):
        self.assertEqual(validate(), [])

    def test_duplicate_future_date_and_unknown_reference(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research" / "daily").mkdir(parents=True)
            (root / "docs").mkdir()
            registry = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
            registry["sources"].append(dict(registry["sources"][0]))
            registry["sources"][0]["published_on"] = "2099-01-01"
            (root / "research" / "sources.json").write_text(json.dumps(registry), encoding="utf-8")
            (root / "research" / "daily" / "2026-10-09.md").write_text(
                "# 2026-10-09\nUnknown source S99\n", encoding="utf-8"
            )
            errors = validate(root)
            self.assertTrue(any("duplicate" in error for error in errors))
            self.assertTrue(any("publication after review" in error for error in errors))
            self.assertTrue(any("unknown source S99" in error for error in errors))

    def test_invalid_source_metadata(self):
        mutations = (
            ("url", "http://example.com", "HTTPS"),
            ("url", "https://name:password@example.com", "HTTPS"),
            ("kind", "unverified", "evidence kind"),
            ("revision", "main", "Git revision"),
            ("spec_version", "2099-01-01", "version after review"),
            ("published_on", "20261009", "YYYY-MM-DD"),
            ("published_on", "2026-02-30", "invalid calendar date"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value), TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "research" / "daily").mkdir(parents=True)
                registry = json.loads(
                    (ROOT / "research" / "sources.json").read_text(encoding="utf-8")
                )
                registry["sources"][0][field] = value
                (root / "research" / "sources.json").write_text(
                    json.dumps(registry), encoding="utf-8"
                )
                self.assertTrue(any(message in error for error in validate(root)))

    def test_source_ranges_validate_intermediate_ids(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research" / "daily").mkdir(parents=True)
            registry = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
            registry["sources"] = [
                source for source in registry["sources"] if source["id"] != "S02"
            ]
            (root / "research" / "sources.json").write_text(json.dumps(registry), encoding="utf-8")
            (root / "research" / "daily" / "2026-10-09.md").write_text(
                "# 2026-10-09\nReferences S01-S03; reversed S05-S04\n", encoding="utf-8"
            )
            errors = validate(root)
            self.assertTrue(any("unknown source S02" in error for error in errors))
            self.assertTrue(any("reversed source range" in error for error in errors))

    def test_review_and_note_dates_are_checked(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research" / "daily").mkdir(parents=True)
            registry = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
            registry_path = root / "research" / "sources.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            (root / "research" / "daily" / "2099-01-01.md").write_text(
                "# Wrong heading\n", encoding="utf-8"
            )
            errors = validate(root)
            self.assertTrue(any("note after latest review" in error for error in errors))
            self.assertTrue(any("heading/date mismatch" in error for error in errors))
            registry["reviewed_on"] = "20261009"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            self.assertTrue(any("YYYY-MM-DD" in error for error in validate(root)))


if __name__ == "__main__":
    unittest.main()
