#!/usr/bin/env python3
"""Unit tests for the deterministic pitfall recorder."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "record_pitfall.py"


def _load_recorder() -> Any:
    spec = importlib.util.spec_from_file_location("record_pitfall_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RECORDER = _load_recorder()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _root(temp_dir: str, repo: bool = False) -> Path:
    root = Path(temp_dir) / "skill"
    root.mkdir()
    _write(
        root / "SKILL.md",
        "---\n"
        "name: project-health\n"
        "description: recorder test fixture\n"
        "metadata:\n"
        "  version: 1.4.3\n"
        "license: PolyForm-Noncommercial-1.0.0\n"
        "---\n",
    )
    _write(root / "AGENTS.md", "# test agents\n")
    _write(root / "references" / "report-template.md", "# report\n")
    (root / "scripts").mkdir()
    shutil.copyfile(SCRIPT, root / "scripts" / "record_pitfall.py")
    if repo:
        (root / ".git").mkdir()
        _write(root / "PITFALLS.md", "# maintainer log\n\n")
    return root


def _entry(**overrides: Any) -> Any:
    values: Dict[str, Any] = {
        "tag": "testing, false-green",
        "trigger": "a test runner collects zero tests",
        "wrong": "treat the empty suite as a successful run",
        "right": "fail closed when testsRun is zero",
        "verify": "run the checker and inspect testsRun",
    }
    values.update(overrides)
    return RECORDER.Entry(**values)


class RecordPitfallTests(unittest.TestCase):
    def test_local_memory_is_created_automatically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            result = RECORDER.record(root, _entry(), record_date="2026-11-13")

            self.assertEqual(result.status, "appended")
            self.assertEqual(result.path.resolve(), (root / "PITFALLS.local.md").resolve())
            data = result.path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r\n", data)
            text = data.decode("utf-8")
            self.assertIn("# 本地避坑记录", text)
            self.assertIn(
                "2026-11-13 | testing, false-green | "
                "a test runner collects zero tests |",
                text,
            )

    def test_exact_duplicate_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            first = RECORDER.record(root, _entry(), record_date="2026-11-13")
            second = RECORDER.record(root, _entry(), record_date="2026-11-13")

            self.assertEqual(first.status, "appended")
            self.assertEqual(second.status, "duplicate")
            text = second.path.read_text(encoding="utf-8")
            self.assertEqual(text.count("2026-11-13 |"), 1)

    def test_newer_duplicate_updates_only_the_date(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            first = RECORDER.record(root, _entry(), record_date="2026-11-15")
            second = RECORDER.record(root, _entry(), record_date="2026-11-16")

            self.assertEqual(first.status, "appended")
            self.assertEqual(second.status, "updated")
            text = second.path.read_text(encoding="utf-8")
            self.assertEqual(text.count("testing, false-green"), 1)
            self.assertIn("2026-11-16 | testing, false-green |", text)
            self.assertNotIn("2026-11-15 | testing, false-green |", text)

            older = RECORDER.record(root, _entry(), record_date="2026-11-14")
            self.assertEqual(older.status, "duplicate")
            self.assertIn("2026-11-16 | testing, false-green |", text)

    def test_dry_run_reports_newer_duplicate_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            RECORDER.record(root, _entry(), record_date="2026-11-15")
            memory = root / "PITFALLS.local.md"
            before = memory.read_bytes()

            result = RECORDER.record(
                root,
                _entry(),
                record_date="2026-11-16",
                dry_run=True,
            )

            self.assertEqual(result.status, "dry-run")
            self.assertEqual(memory.read_bytes(), before)

    def test_new_mechanism_under_same_class_uses_parent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            RECORDER.record(
                root,
                _entry(trigger="tests are skipped when a platform is missing"),
                record_date="2026-11-13",
            )
            result = RECORDER.record(
                root,
                _entry(
                    trigger="test discovery matches no files and returns success",
                    parent="CICD-02",
                ),
                record_date="2026-11-13",
            )

            self.assertEqual(result.status, "appended")
            text = result.path.read_text(encoding="utf-8")
            self.assertIn("test discovery matches no files", text)
            self.assertIn("父条目 CICD-02", text)

    def test_existing_history_is_preserved_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            memory = root / "PITFALLS.local.md"
            old = (
                "# existing local log\n\n"
                "2026-01-01 | old, entry | old trigger | old wrong | "
                "old right | old verify\n"
            )
            _write(memory, old)

            RECORDER.record(root, _entry(), record_date="2026-11-13")

            text = memory.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(old))
            self.assertIn("2026-11-13 | testing, false-green |", text)

    def test_repo_scope_uses_baseline_and_never_creates_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir, repo=True)
            result = RECORDER.record(root, _entry(), record_date="2026-11-13")

            self.assertEqual(result.status, "appended")
            self.assertEqual(result.path.resolve(), (root / "PITFALLS.md").resolve())
            self.assertFalse((root / "PITFALLS.local.md").exists())
            self.assertIn(
                "2026-11-13 | testing, false-green |",
                result.path.read_text(encoding="utf-8"),
            )

        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            (root / ".git").mkdir()
            with self.assertRaises(ValueError):
                RECORDER.record(root, _entry(), record_date="2026-11-13")

    def test_existing_local_file_wins_over_repo_detection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir, repo=True)
            _write(root / "PITFALLS.local.md", "# local log\n\n")
            result = RECORDER.record(root, _entry(), record_date="2026-11-13")
            self.assertEqual(result.path.resolve(), (root / "PITFALLS.local.md").resolve())
            self.assertNotIn(
                "2026-11-13 | testing, false-green |",
                (root / "PITFALLS.md").read_text(encoding="utf-8"),
            )

    def test_git_clone_install_under_skills_uses_local_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            skills = Path(temp_dir) / "skills"
            skills.mkdir()
            root = skills / "project-health"
            root.mkdir()
            _write(
                root / "SKILL.md",
                "---\n"
                "name: project-health\n"
                "description: installed skill fixture\n"
                "metadata:\n"
                "  version: 1.4.3\n"
                "license: PolyForm-Noncommercial-1.0.0\n"
                "---\n",
            )
            _write(root / "AGENTS.md", "# installed agents\n")
            _write(root / "references" / "report-template.md", "# report\n")
            (root / "scripts").mkdir()
            shutil.copyfile(SCRIPT, root / "scripts" / "record_pitfall.py")
            (root / ".git").mkdir()
            _write(root / "PITFALLS.md", "# baseline\n\n")

            result = RECORDER.record(root, _entry(), record_date="2026-11-13")

            self.assertEqual(result.path.resolve(), (root / "PITFALLS.local.md").resolve())
            self.assertNotIn(
                "2026-11-13 | testing, false-green |",
                (root / "PITFALLS.md").read_text(encoding="utf-8"),
            )

    def test_invalid_fields_fail_closed(self) -> None:
        cases = [
            _entry(trigger=""),
            _entry(wrong="line one\nline two"),
            _entry(right="contains | separator"),
            _entry(verify="x" * 601),
            _entry(parent="not-an-id"),
            _entry(tag=""),
            _entry(tag=", ,"),
            _entry(tag="a,b,c,d,e,f,g,h,i"),
            _entry(tag="x" * 41),
        ]
        for entry in cases:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                RECORDER.build_line(entry, "2026-11-13")

    def test_sensitive_values_are_rejected(self) -> None:
        cases = [
            "C:" + chr(92) + "Users" + chr(92) + "example-user",
            "C:/" + "Users/example-user",
            "/" + "home/example-user",
            "/" + "Users/example-user",
            "sk-" + "a" * 24,
            "ghp_" + "a" * 24,
            "AKIA" + "A" * 16,
            "-----BEGIN " + "RSA PRIVATE KEY-----",
            "password=" + "abcdefghijklmnop",
            "secret=" + "abcdefghijklmnop",
            "client_secret=" + "abcdefghijklmnop",
            "access_token=" + "abcdefghijklmnop",
            "refresh_token=" + "abcdefghijklmnop",
            "private_key=" + "abcdefghijklmnop",
            "192" + ".168.1.10",
            "person" + "@" + "example.com",
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                RECORDER.build_line(_entry(trigger=value), "2026-11-13")

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            result = RECORDER.record(
                root,
                _entry(),
                record_date="2026-11-13",
                dry_run=True,
            )
            self.assertEqual(result.status, "dry-run")
            self.assertFalse((root / "PITFALLS.local.md").exists())

    def test_root_must_look_like_a_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(ValueError):
                RECORDER.record(root, _entry(), record_date="2026-11-13")

    def test_agents_and_pitfalls_alone_are_not_a_skill_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = Path(temp_dir) / "target-repo"
            root.mkdir()
            _write(root / "AGENTS.md", "# target\n")
            _write(root / "PITFALLS.md", "# target memory\n\n")
            with self.assertRaises(ValueError):
                RECORDER.record(root, _entry(), record_date="2026-11-13")

    def test_fake_skill_frontmatter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            _write(root / "SKILL.md", "---\nname: other-skill\n---\n")
            with self.assertRaises(ValueError):
                RECORDER.record(root, _entry(), record_date="2026-11-13")

    def test_recorder_fingerprint_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            recorder = root / "scripts" / "record_pitfall.py"
            _write(recorder, recorder.read_text(encoding="utf-8") + "\n# changed\n")
            with self.assertRaises(ValueError):
                RECORDER.record(root, _entry(), record_date="2026-11-13")

    def test_repo_scope_requires_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            _write(root / "PITFALLS.md", "# target memory\n\n")
            with self.assertRaises(ValueError):
                RECORDER.record(
                    root,
                    _entry(),
                    scope="repo",
                    record_date="2026-11-13",
                )

    def test_cli_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            base = [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--root",
                str(root),
                "--date",
                "2026-11-13",
                "--tag",
                "testing, false-green",
                "--trigger",
                "a test runner collects zero tests",
                "--wrong",
                "treat the empty suite as a successful run",
                "--right",
                "fail closed when testsRun is zero",
                "--verify",
                "run the checker and inspect testsRun",
            ]
            first = subprocess.run(
                base, cwd=ROOT, capture_output=True, text=True, check=False
            )
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            duplicate = subprocess.run(
                base, cwd=ROOT, capture_output=True, text=True, check=False
            )
            self.assertEqual(
                duplicate.returncode, 0, msg=duplicate.stdout + duplicate.stderr
            )
            self.assertIn("DUPLICATE", duplicate.stdout)

            invalid = base.copy()
            invalid[invalid.index("--verify") + 1] = "bad | value"
            failed = subprocess.run(
                invalid, cwd=ROOT, capture_output=True, text=True, check=False
            )
            self.assertEqual(failed.returncode, 1, msg=failed.stdout + failed.stderr)

            usage = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--root", str(root)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(usage.returncode, 2, msg=usage.stdout + usage.stderr)

    def test_non_utf8_console_does_not_turn_a_write_into_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-pitfall-") as temp_dir:
            root = _root(temp_dir)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "cp936"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--date",
                    "2026-11-13",
                    "--tag",
                    "testing, unicode",
                    "--trigger",
                    "console fixture 😀",
                    "--wrong",
                    "the write succeeds before display fails",
                    "--right",
                    "use a lossy safe display encoding",
                    "--verify",
                    "exit code is zero and the file contains the entry",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            memory = root / "PITFALLS.local.md"
            self.assertIn("console fixture 😀", memory.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
