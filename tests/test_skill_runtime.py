from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if (SCRIPT_DIR / "skill_runtime.py").is_file():
    RUNTIME_DIR = SCRIPT_DIR
else:
    RUNTIME_DIR = SCRIPT_DIR.parent / "scripts"
sys.path.insert(0, str(RUNTIME_DIR))
import skill_runtime  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class SkillRuntimeTests(unittest.TestCase):
    def test_frontmatter_accepts_utf8_and_rejects_bom(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-runtime-") as temp:
            path = Path(temp) / "SKILL.md"
            write(path, "---\nname: test\nmetadata:\n  version: 1.0.0\n---\n")
            self.assertEqual(skill_runtime.read_frontmatter(path)["name"], "test")

            path.write_bytes(b"\xef\xbb\xbf---\nname: test\n---\n")
            with self.assertRaisesRegex(ValueError, "without BOM"):
                skill_runtime.read_frontmatter(path)

    def test_scope_prefers_local_for_skills_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-runtime-") as temp:
            root = Path(temp) / "skills" / "project-health"
            (root / ".git").mkdir(parents=True)
            (root / "PITFALLS.md").write_text("# Base\n", encoding="utf-8")
            path = skill_runtime.resolve_memory_path(
                root, "auto", "PITFALLS.local.md", "PITFALLS.md"
            )
            self.assertEqual(path.name, "PITFALLS.local.md")

    def test_atomic_write_and_exclusive_create_preserve_utf8(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-runtime-") as temp:
            path = Path(temp) / "memory.md"
            skill_runtime.write_text_atomic(path, "one\n")
            skill_runtime.write_text_atomic(path, "two\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "two\n")

            created = Path(temp) / "local.md"
            skill_runtime.create_text_exclusive(created, "first\n")
            skill_runtime.create_text_exclusive(created, "second\n")
            self.assertEqual(created.read_text(encoding="utf-8"), "first\n")

    def test_lock_creates_stable_lock_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skill-runtime-") as temp:
            path = Path(temp) / "memory.md"
            with skill_runtime.file_lock(path, "MEMORY.lock"):
                self.assertTrue((Path(temp) / "MEMORY.lock").is_file())


if __name__ == "__main__":
    unittest.main()
