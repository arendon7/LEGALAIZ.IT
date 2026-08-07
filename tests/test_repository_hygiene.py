from __future__ import annotations

from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(TestCase):
    def test_version_marker_is_canonical(self) -> None:
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), "M33.0")

    def test_public_documents_declare_current_release(self) -> None:
        for relative in ("README.md", "FINAL_RELEASE_NOTES.md"):
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("M33.0", content, relative)
            self.assertNotIn("M31.8", content, relative)
            self.assertNotIn("v5.0.7", content, relative)

    def test_only_consolidated_workflows_are_active(self) -> None:
        active = sorted(path.name for path in (ROOT / ".github" / "workflows").glob("*.yml"))
        self.assertEqual(active, ["ci.yml", "pages.yml"])

    def test_historical_workflows_are_manifest_only(self) -> None:
        directory = ROOT / ".github" / "manual-workflows"
        files = sorted(path.name for path in directory.iterdir() if path.is_file())
        self.assertEqual(files, ["README.md"])

    def test_no_tracked_temporary_backup_or_local_data_files(self) -> None:
        forbidden_suffixes = {
            ".bak", ".old", ".orig", ".rej", ".tmp", ".log",
            ".sqlite", ".sqlite3", ".db", ".p12", ".pfx",
        }
        excluded_parts = {".git", ".venv", "venv", "node_modules", "__pycache__"}
        offenders: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in excluded_parts for part in path.parts):
                continue
            if path.suffix.casefold() in forbidden_suffixes or path.name.endswith("~"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_no_tracked_local_artifact_directories(self) -> None:
        forbidden = {
            "generated", "uploads", "secrets", "artifacts", "output",
            "rendered", "node_modules", "dist", "build", ".idea", ".vscode",
        }
        present = sorted(name for name in forbidden if (ROOT / name).exists())
        self.assertEqual(present, [])

    def test_runtime_and_audit_are_placeholders_only(self) -> None:
        for relative in ("runtime", "audit"):
            files = sorted(path.name for path in (ROOT / relative).iterdir())
            self.assertEqual(files, [".gitkeep"], relative)

    def test_ignore_files_cover_sensitive_and_generated_state(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        required_git = {
            ".env", ".env.*", "secrets/", "runtime/*", "audit/*",
            "generated/", "uploads/", "artifacts/", "*.log", "*.sqlite",
            "*.db", "node_modules/", "dist/", "build/", ".idea/", ".vscode/",
        }
        required_docker = {
            ".env", ".env.*", "secrets", "runtime", "audit", "generated",
            "uploads", "artifacts", "*.log", "*.sqlite", "*.db",
            "node_modules", "dist", "build", ".idea", ".vscode",
        }
        self.assertTrue(required_git.issubset(set(gitignore)), required_git - set(gitignore))
        self.assertTrue(required_docker.issubset(set(dockerignore)), required_docker - set(dockerignore))

    def test_safe_environment_example_and_security_policy_exist(self) -> None:
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("LEGAL_DEMO_PASSWORD=CHANGE_ME_BEFORE_USE", example)
        self.assertNotIn("LegalAIZDemo2026!", example)
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("Reporte responsable", security)
        self.assertIn("datos sintéticos", security)

    def test_readme_sets_main_as_source_of_truth_and_preserves_limits(self) -> None:
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Rama vigente: `main`", content)
        self.assertIn("No acredita aprobación profesional", content)
        self.assertIn("Solo existen dos workflows activos", content)


if __name__ == "__main__":
    import unittest

    unittest.main()
