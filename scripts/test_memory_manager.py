#!/usr/bin/env python3
"""Scratch-file tests for memory_manager.py. No third-party packages."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "memory_manager.py"
sys.path.insert(0, str(SCRIPT.parent))


def run_cli(args, check=False):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result


class MemoryManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents = self.root / "AGENTS.md"
        self.agents.write_text(
            "# Hand Written\n\nDo not touch this.\n\n## Other Section\n\n- keep me\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_dedup_and_preserve(self):
        first = run_cli(
            [
                "--action",
                "append",
                "--file",
                str(self.agents),
                "--category",
                "Build & Test",
                "--content",
                "Run linting before committing.",
            ],
            check=True,
        )
        self.assertIn("Saved under", first.stdout)

        dup = run_cli(
            [
                "--action",
                "append",
                "--file",
                str(self.agents),
                "--category",
                "Build & Test",
                "--content",
                "run linting before committing",
            ]
        )
        self.assertIn("Already present", dup.stdout)

        run_cli(
            [
                "--action",
                "append",
                "--file",
                str(self.agents),
                "--category",
                "Security",
                "--content",
                "Always use parameterized SQL queries.",
            ],
            check=True,
        )
        text = self.agents.read_text(encoding="utf-8")
        self.assertIn("Do not touch this.", text)
        self.assertIn("- keep me", text)
        self.assertEqual(text.count("Run linting before committing."), 1)
        self.assertIn("### Security", text)

    def test_multiline_rejected(self):
        result = run_cli(
            [
                "--action",
                "append",
                "--file",
                str(self.agents),
                "--content",
                "line one\nline two",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single line", result.stderr)

    def test_empty_rejected(self):
        result = run_cli(
            ["--action", "append", "--file", str(self.agents), "--content", "   "]
        )
        self.assertNotEqual(result.returncode, 0)

    def test_mid_file_insert(self):
        mid = self.root / "mid.md"
        mid.write_text(
            "# Title\n\nIntro text.\n\n## Learned Rules\n\n### Styling\n"
            "- Use HSL rather than hex.\n\n## Later Section\n\nKeep after.\n",
            encoding="utf-8",
        )
        run_cli(
            [
                "--action",
                "append",
                "--file",
                str(mid),
                "--category",
                "Styling",
                "--content",
                "Prefer rem over px for spacing.",
            ],
            check=True,
        )
        run_cli(
            [
                "--action",
                "append",
                "--file",
                str(mid),
                "--category",
                "Build & Test",
                "--content",
                "Use uv run pytest.",
            ],
            check=True,
        )
        text = mid.read_text(encoding="utf-8")
        styling = text.index("Prefer rem over px")
        later = text.index("## Later Section")
        build = text.index("Use uv run pytest.")
        self.assertLess(styling, later)
        self.assertLess(build, later)
        self.assertGreater(build, styling)

    def test_list_replace_remove(self):
        run_cli(
            [
                "--action",
                "append",
                "--file",
                str(self.agents),
                "--category",
                "Git",
                "--content",
                "Never force-push main.",
            ],
            check=True,
        )
        listed = run_cli(["--action", "list", "--file", str(self.agents)], check=True)
        self.assertIn("Never force-push main.", listed.stdout)
        self.assertNotIn("Do not touch this.", listed.stdout)

        run_cli(
            [
                "--action",
                "replace",
                "--file",
                str(self.agents),
                "--match",
                "Never force-push main.",
                "--content",
                "Never force-push main or master.",
            ],
            check=True,
        )
        text = self.agents.read_text(encoding="utf-8")
        self.assertIn("Never force-push main or master.", text)
        self.assertNotIn("- Never force-push main.\n", text)

        run_cli(
            [
                "--action",
                "remove",
                "--file",
                str(self.agents),
                "--match",
                "Never force-push main or master.",
            ],
            check=True,
        )
        text = self.agents.read_text(encoding="utf-8")
        self.assertNotIn("Never force-push main or master.", text)

    def test_git_root_resolution(self):
        repo = self.root / "repo"
        nested = repo / "pkg" / "inner"
        nested.mkdir(parents=True)
        (repo / ".git").mkdir()
        from memory_manager import find_project_root, get_target_path

        self.assertEqual(find_project_root(nested), repo.resolve())
        target = get_target_path("project", workspace_dir=str(nested))
        self.assertEqual(target, repo.resolve() / "AGENTS.md")

    def test_harness_paths_and_mdc_preamble(self):
        from memory_manager import detect_harness, global_path_for_harness

        fake_home = self.root / "home"
        (fake_home / ".cursor").mkdir(parents=True)
        (fake_home / ".claude").mkdir()
        self.assertEqual(detect_harness(home=fake_home), "cursor")
        self.assertEqual(
            global_path_for_harness("cursor", home=fake_home),
            fake_home / ".cursor" / "rules" / "learned.mdc",
        )
        self.assertEqual(
            global_path_for_harness("neutral", home=fake_home),
            fake_home / ".agents" / "rules.md",
        )

        mdc = self.root / "learned.mdc"
        run_cli(
            [
                "--action",
                "append",
                "--file",
                str(mdc),
                "--category",
                "Editor",
                "--content",
                "Prefer HSL over hex.",
            ],
            check=True,
        )
        text = mdc.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("alwaysApply: true", text)
        self.assertIn("Prefer HSL over hex.", text)

    def test_detect_harness_env(self):
        from memory_manager import detect_harness

        old = os.environ.get("LEARN_SKILL_HARNESS")
        os.environ["LEARN_SKILL_HARNESS"] = "gemini"
        try:
            self.assertEqual(detect_harness(home=self.root / "empty-home"), "gemini")
        finally:
            if old is None:
                os.environ.pop("LEARN_SKILL_HARNESS", None)
            else:
                os.environ["LEARN_SKILL_HARNESS"] = old


if __name__ == "__main__":
    unittest.main()
