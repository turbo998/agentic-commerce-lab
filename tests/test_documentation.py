import json
import re
import unittest
from datetime import date
from pathlib import Path


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        files = [Path("README.md"), *Path("docs").glob("*.md"), *Path("research").rglob("*.md")]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(file=str(path), target=target):
                    self.assertTrue((path.parent / target.split("#")[0]).exists())

    def test_research_reference_definitions_are_complete(self):
        path = Path("research/daily/2026-10-10.md")
        text = path.read_text(encoding="utf-8")
        definitions = set(re.findall(r"^\[([a-z0-9-]+)\]: https://", text, re.MULTILINE))
        used = set(re.findall(r"\[([a-z0-9-]+)\](?![:(])", text))
        self.assertTrue(used.issubset(definitions))

    def test_evidence_dates_and_code_anchors(self):
        sources = json.loads(Path("research/sources.json").read_text(encoding="utf-8"))
        for source in sources:
            with self.subTest(id=source["id"]):
                date.fromisoformat(source["checked_on"])
                if source["published_date"] is not None:
                    self.assertLessEqual(
                        date.fromisoformat(source["published_date"]),
                        date.fromisoformat(source["checked_on"]),
                    )
                if "revision" in source:
                    self.assertRegex(source["revision"], r"^[a-f0-9]{40}$")


if __name__ == "__main__":
    unittest.main()
