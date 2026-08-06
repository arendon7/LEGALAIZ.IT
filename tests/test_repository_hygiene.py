from __future__ import annotations

from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(TestCase):
    def test_version_marker_is_canonical(self) -> None:
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), "M32.9")

    def test_public_documents_do_not_declare_old_release(self) -> None:
        for relative in ("README.md", "FINAL_RELEASE_NOTES.md"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("M32.9", content, relative)
            self.assertNotIn("M31.8", content, relative)
            self.assertNotIn("v5.0.7", content, relative)

    def test_only_consolidated_workflows_are_active(self) -> None:
        active = sorted(path.name for path in (ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertEqual(active, ["ci.yml", "pages.yml"])

    def test_historical_workflows_are_manifest_only(self) -> None:
        directory = ROOT / ".github" / "manual-workflows"
        files = sorted(path.name for path in directory.iterdir() if path.is_file())
        self.assertEqual(files, ["README.md"])

    def test_no_tracked_temporary_or_backup_files(self) -> None:
        forbidden_suffixes = {".bak", ".old", ".orig", ".rej", ".tmp"}
        excluded_parts = {".git", ".venv", "venv", "node_modules", "__pycache__"}
        offenders: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in excluded_parts for part in path.parts):
                continue
            if path.suffix.casefold() in forbidden_suffixes or path.name.endswith("~"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_readme_sets_main_as_source_of_truth_and_preserves_limits(self) -> None:
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Rama vigente: `main`", content)
        self.assertIn("No acredita aprobación profesional", content)
        self.assertIn("Solo existen dos workflows activos", content)


if __name__ == "__main__":
    import unittest

    unittest.main()
