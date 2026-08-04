from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MASTER_BLUEPRINT = "docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md"
ACTION_PLAN = "docs/ACTION_PLAN_V17_CONTINUATION_2026-07-30.md"
CHANGELOG = "CHANGELOG.md"
CONTINUITY_DOCUMENTS = {
    MASTER_BLUEPRINT,
    ACTION_PLAN,
    CHANGELOG,
}


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _changed_paths() -> set[str]:
    paths: set[str] = set()
    commands = (
        ("diff", "--name-only", "--no-renames"),
        ("diff", "--cached", "--name-only", "--no-renames"),
        ("ls-files", "--others", "--exclude-standard"),
    )
    for command in commands:
        output = _git(*command).stdout
        paths.update(
            line.strip().replace("\\", "/")
            for line in output.splitlines()
            if line.strip()
        )
    return paths


class DocumentationContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        probe = _git("rev-parse", "--is-inside-work-tree", check=False)
        if probe.returncode != 0 or probe.stdout.strip() != "true":
            raise unittest.SkipTest("documentation continuity requires Git metadata")

    def test_continuity_documents_share_latest_commit(self) -> None:
        latest_commits = {
            path: _git("log", "-1", "--format=%H", "--", path).stdout.strip()
            for path in CONTINUITY_DOCUMENTS
        }
        self.assertTrue(
            all(latest_commits.values()),
            f"Missing committed continuity document: {latest_commits}",
        )
        self.assertEqual(
            1,
            len(set(latest_commits.values())),
            "Master blueprint, action plan and changelog must be committed "
            f"together. Latest revisions: {latest_commits}",
        )

    def test_no_implementation_commit_is_newer_than_master(self) -> None:
        master_commit = _git(
            "log",
            "-1",
            "--format=%H",
            "--",
            MASTER_BLUEPRINT,
        ).stdout.strip()
        implementation_commit = _git(
            "log",
            "-1",
            "--format=%H",
            "--",
            ":(glob)**/*.py",
            "requirements.txt",
        ).stdout.strip()
        if not implementation_commit:
            self.skipTest("no committed implementation file is present")

        ancestry = _git(
            "merge-base",
            "--is-ancestor",
            implementation_commit,
            master_commit,
            check=False,
        )
        self.assertEqual(
            0,
            ancestry.returncode,
            "Implementation is newer than the master blueprint. Reconcile "
            "the master, action plan and changelog in the implementation commit.",
        )

    def test_dirty_implementation_requires_all_continuity_documents(self) -> None:
        changed = _changed_paths()
        implementation_changed = any(
            path.endswith(".py") or path == "requirements.txt"
            for path in changed
        )
        continuity_changed = bool(changed & CONTINUITY_DOCUMENTS)

        if not implementation_changed and not continuity_changed:
            return

        missing = sorted(CONTINUITY_DOCUMENTS - changed)
        self.assertFalse(
            missing,
            "Implementation progress or continuity documentation is dirty, "
            "but the complete continuity set is not being updated. Missing: "
            f"{missing}",
        )

    def test_master_contains_authoritative_restart_checkpoint(self) -> None:
        master_text = (REPOSITORY_ROOT / MASTER_BLUEPRINT).read_text(
            encoding="utf-8"
        )
        required_markers = (
            "### 1.2 Living authority and no-translation-loss protocol",
            "## 25. Living development checkpoint",
            "### 25.2 Exact R1 work package",
            "### 25.3 R1 exit evidence required",
            "### 25.4 Explicitly not started",
        )
        missing = [marker for marker in required_markers if marker not in master_text]
        self.assertFalse(
            missing,
            f"Master blueprint is missing restart markers: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
