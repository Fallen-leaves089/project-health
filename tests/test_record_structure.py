#!/usr/bin/env python3
"""Tests for the schema-driven structural-experience recorder."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "record_structure.py"
SCHEMA = ROOT / "scripts" / "structure-schema.json"


def _load_recorder() -> Any:
    spec = importlib.util.spec_from_file_location("record_structure_under_test", SCRIPT)
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


def _manual(schema: Dict[str, Any], language: str) -> str:
    lines = [
        "# Structural Experience Manual",
        "",
        f"schema-version: {schema['schema_version']}",
        "",
        "Empty is valid.",
        "",
    ]
    labels = schema[f"chapter_labels_{language}"]
    for chapter in schema["chapter_ids"]:
        lines.extend(
            [f"### {chapter}. {labels[chapter]}", "", "<!-- empty -->", ""]
        )
    return "\n".join(lines)


def _root(temp_dir: str, repo: bool = False) -> Path:
    root = Path(temp_dir) / "skill"
    root.mkdir()
    _write(
        root / "SKILL.md",
        "---\n"
        "name: project-health\n"
        "description: structure recorder fixture\n"
        "metadata:\n"
        "  version: 1.5.1\n"
        "license: PolyForm-Noncommercial-1.0.0\n"
        "---\n",
    )
    _write(root / "AGENTS.md", "# agents\n")
    _write(
        root / "PITFALLS.md",
        "# pitfalls\n\n"
        "| ARC-01 | boundaries |\n"
        "| CON-06 | idempotency |\n"
        "| DAT-01 | migration |\n",
    )
    _write(root / "references" / "report-template.md", "# report\n")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    _write(
        root / "references" / "structural-experience.md",
        _manual(schema, "zh"),
    )
    _write(
        root / "references" / "structural-experience.en.md",
        _manual(schema, "en"),
    )
    (root / "scripts").mkdir()
    shutil.copyfile(SCRIPT, root / "scripts" / "record_structure.py")
    shutil.copyfile(SCHEMA, root / "scripts" / "structure-schema.json")
    if repo:
        (root / ".git").mkdir()
    return root


def _entry(**overrides: Any) -> Any:
    values: Dict[str, Any] = {
        "chapter": "A",
        "primary_branch": "A/service/order/api",
        "related_branches": "C/cache/order",
        "status": "待验证",
        "injection": None,
        "trigger": "order API reads a second service's state",
        "mechanism": "ownership is unclear across a runtime boundary",
        "boundary": "not applicable to a single-process module with one owner",
        "verification": "trace both read paths and change one owner's schema",
        "pitfalls": "ARC-01",
        "region_links": "shares-data:C/cache/order; depends-on:ARC-01",
        "language": "zh",
    }
    values.update(overrides)
    return RECORDER.Entry(**values)


class RecordStructureTests(unittest.TestCase):
    def test_schema_defaults_pending_to_soft_and_lists_required_fields(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["status_defaults"]["pending"],
            "soft",
        )
        for field in (
            "trigger",
            "mechanism",
            "boundary",
            "verification",
            "pitfalls",
            "primary_branch",
        ):
            self.assertIn(field, schema["required_fields"])

    def test_schema_uses_powershell_5_1_safe_types(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

        def scalar(value: Any) -> bool:
            return isinstance(value, (str, int, float, bool)) or value is None

        def flat_collection(value: Any) -> bool:
            if isinstance(value, list):
                return all(scalar(item) for item in value)
            if isinstance(value, dict):
                return all(scalar(item) for item in value.values())
            return scalar(value)

        for key, value in schema.items():
            if isinstance(value, dict):
                self.assertTrue(
                    all(flat_collection(child) for child in value.values()),
                    msg=f"{key} contains a nested object",
                )
            else:
                self.assertTrue(
                    flat_collection(value),
                    msg=f"{key} is not a flat value or flat map",
                )

    def test_add_creates_utf8_lf_local_manual_with_region_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            result = RECORDER.record(root, _entry())

            self.assertEqual(result.status, "appended")
            self.assertEqual(result.entry_id, "S-A-001")
            self.assertEqual(result.path.resolve(), (root / "STRUCTURE.local.md").resolve())
            data = result.path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r\n", data)
            text = data.decode("utf-8")
            self.assertIn("| 待验证 | 软提示 |", text)
            self.assertIn("  - 区域关联： shares-data:C/cache/order; depends-on:ARC-01", text)

    def test_english_add_creates_english_local_manual(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            result = RECORDER.record(root, _entry(language="en"))

            self.assertEqual(result.status, "appended")
            self.assertEqual(result.path.resolve(), (root / "STRUCTURE.local.md").resolve())
            text = result.path.read_text(encoding="utf-8")
            self.assertIn("### A. Boundaries and ownership", text)
            self.assertIn("| pending verification | soft hint |", text)
            self.assertIn("  - Region links:", text)

    def test_git_install_under_skills_uses_local_manual(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            original = _root(temp_dir, repo=True)
            root = Path(temp_dir) / "skills" / "project-health"
            root.parent.mkdir()
            original.rename(root)
            repo_manual = root / "references" / "structural-experience.md"
            original_repo = repo_manual.read_bytes()

            result = RECORDER.record(root, _entry())

            self.assertEqual(result.path.resolve(), (root / "STRUCTURE.local.md").resolve())
            self.assertEqual(repo_manual.read_bytes(), original_repo)

    def test_repo_english_add_uses_english_manual(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir, repo=True)
            chinese_manual = root / "references" / "structural-experience.md"
            original_chinese = chinese_manual.read_bytes()

            result = RECORDER.record(root, _entry(language="en"), scope="repo")

            self.assertEqual(
                result.path.resolve(),
                (root / "references" / "structural-experience.en.md").resolve(),
            )
            self.assertEqual(chinese_manual.read_bytes(), original_chinese)
            self.assertIn(
                "| pending verification | soft hint |",
                result.path.read_text(encoding="utf-8"),
            )

    def test_pending_entry_cannot_use_detailed_injection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            with self.assertRaisesRegex(ValueError, "not allowed"):
                RECORDER.record(root, _entry(injection="详细"))

    def test_obsolete_entry_cannot_use_detailed_injection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            with self.assertRaisesRegex(ValueError, "not allowed"):
                RECORDER.record(
                    root,
                    _entry(status="已过时", injection="详细"),
                )

    def test_unknown_or_missing_pitfall_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            with self.assertRaisesRegex(ValueError, "unknown PITFALLS"):
                RECORDER.record(root, _entry(pitfalls="ARC-99"))
            with self.assertRaisesRegex(ValueError, "at least one"):
                RECORDER.record(root, _entry(pitfalls=""))

    def test_region_links_require_relation_type_and_id_and_stay_short(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            with self.assertRaisesRegex(ValueError, "relation-type:ID"):
                RECORDER.record(root, _entry(region_links="order points at the cache"))
            with self.assertRaisesRegex(ValueError, "invalid region link target"):
                RECORDER.record(root, _entry(region_links="depends-on:free text"))
            with self.assertRaisesRegex(ValueError, "longer than"):
                RECORDER.record(root, _entry(region_links="depends-on:" + "a" * 260))

    def test_duplicate_mechanism_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            RECORDER.record(root, _entry())
            with self.assertRaisesRegex(ValueError, "duplicate structural mechanism"):
                RECORDER.record(root, _entry())

    def test_obsolete_entry_id_is_not_reused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            first = RECORDER.record(root, _entry())
            text = first.path.read_text(encoding="utf-8")
            with first.path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    text.replace("| 待验证 | 软提示 |", "| 已过时 | 软提示 |", 1)
                )
            second = RECORDER.record(
                root,
                _entry(
                    trigger="another independent trigger",
                    mechanism="another independent mechanism",
                ),
            )
            self.assertEqual(second.entry_id, "S-A-002")

    def test_path_depth_is_not_capped(self) -> None:
        self.assertEqual(
            RECORDER._validate_branch("A/one/two/three/four/five/six/seven/eight"),
            "A/one/two/three/four/five/six/seven/eight",
        )

    def test_sibling_depth_mismatch_is_not_rejected_by_recorder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            first = RECORDER.record(root, _entry())
            second = RECORDER.record(
                root,
                _entry(
                    primary_branch="A/service/orders",
                    trigger="a sibling has a different level",
                    mechanism="depth is not a storage invariant",
                ),
            )
            self.assertEqual(first.entry_id, "S-A-001")
            self.assertEqual(second.entry_id, "S-A-002")
            self.assertIn("A/service/order/api", second.path.read_text(encoding="utf-8"))
            self.assertIn("A/service/orders", second.path.read_text(encoding="utf-8"))

    def test_check_accepts_empty_manual_and_rejects_missing_region_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            result = RECORDER.check_manual(
                root / "references" / "structural-experience.md",
                root,
            )
            self.assertEqual(result.entry_count, 0)

            appended = RECORDER.record(root, _entry())
            text = appended.path.read_text(encoding="utf-8")
            with appended.path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text.replace("  - 区域关联：", "  - removed note：", 1))
            with self.assertRaisesRegex(ValueError, "missing its region-link note"):
                RECORDER.check_manual(appended.path, root)

    def test_cli_check_uses_schema_and_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            root = _root(temp_dir)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--check",
                    "--path",
                    "references/structural-experience.md",
                    "--root",
                    str(root),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            self.assertIn("CHECK PASSED", completed.stdout)

    def test_cli_check_defaults_to_empty_local_manual_for_git_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="record-structure-") as temp_dir:
            original = _root(temp_dir, repo=True)
            root = Path(temp_dir) / "skills" / "project-health"
            root.parent.mkdir()
            original.rename(root)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--check",
                    "--root",
                    str(root),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            self.assertIn("no local structure manual yet", completed.stdout)


if __name__ == "__main__":
    unittest.main()
