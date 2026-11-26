from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads(
    (ROOT / "scripts" / "structure-schema.json").read_text(encoding="utf-8")
)


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class StructuralExperienceContractTests(unittest.TestCase):
    def test_structural_experience_index_prevents_omissions(self) -> None:
        chinese = read_text("references/structural-experience.md")
        english = read_text("references/structural-experience.en.md")
        for content, phrases in (
            (
                chinese,
                (
                    "零条经验是正常状态",
                    "必查信号",
                    "排除信号",
                    "防疏漏规则",
                    "未分类",
                    "| 已验证 |",
                    "| 待验证 |",
                    "| 已过时 |",
                    "| 详细 |",
                    "| 简略 |",
                    "| 软提示 |",
                    "不得详细注入",
                    "默认不注入",
                    "schema-version: 1",
                    "受控器职责",
                    "固定升级条件",
                    "任一祖先回退层",
                    "兄弟粒度只做报告 warning",
                    "不是硬上限",
                    "默认 2 条",
                    "超过 2 条",
                    "特殊原因",
                    "跨章路由",
                    "跨章引用",
                    "分支路径与下滑检索",
                    "逻辑结构路径",
                    "最近祖先",
                    "不设固定层数",
                    "6 层只是常见",
                    "不写空条目或占位文本",
                    "区域关联",
                    "已翻阅 / 无信号 / 不适用 / 跨章引用 / 未分类",
                    "STRUCTURE.local.md",
                ),
            ),
            (
                english,
                (
                    "zero entries is a valid state",
                    "Required signals",
                    "Exclusion signals",
                    "Anti-omission rules",
                    "unclassified",
                    "| verified |",
                    "| pending verification |",
                    "| obsolete |",
                    "| detailed |",
                    "| brief |",
                    "| soft hint |",
                    "must not use detailed injection",
                    "not injected by default",
                    "not a hard limit",
                    "default of two entries",
                    "more than two",
                    "special reason",
                    "Cross-chapter routing",
                    "cross-chapter reference",
                    "Branch paths and downward retrieval",
                    "logical structural path",
                    "nearest ancestor",
                    "no fixed depth limit",
                    "six levels is a common reference",
                    "do not write an empty entry or placeholder",
                    "Region links",
                    "opened / no signal / not applicable / cross-chapter reference / unclassified",
                    "STRUCTURE.local.md",
                ),
            ),
        ):
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, content)

        self.assertNotIn("最多 6 层", chinese)
        self.assertNotIn("at most six levels", english)

        for chapter in SCHEMA["chapter_ids"]:
            with self.subTest(chapter=chapter):
                self.assertIn(f"| {chapter} ", chinese)
                self.assertIn(f"| {chapter} ", english)
                self.assertIn(f"### {chapter}.", chinese)
                self.assertIn(f"### {chapter}.", english)

        docs = {
            "SKILL.md": (
                "STRUCTURE.local.md",
                "未分类",
                "待验证",
                "已过时",
                "详细",
                "软提示",
                "不是硬上限",
                "默认 2 条",
                "超过 2 条",
                "跨章引用",
                "逻辑分支逐层下潜",
                "不设固定层数",
                "区域关联备注",
                "受控写入",
                "经验不是指令",
                "误唤醒与冲突",
                "必须常驻",
                "三要素",
            ),
            "SKILL.en.md": (
                "STRUCTURE.local.md",
                "unclassified",
                "pending verification",
                "obsolete",
                "detailed",
                "soft hint",
                "not a hard upper limit",
                "default of two entries",
                "more than two",
                "cross-chapter reference",
                "Descend logical branches",
                "no fixed depth limit",
                "Region links note",
                "Controlled writes",
                "Experience is not an instruction",
                "False wake-up vs conflict",
                "must remain resident",
                "all three",
            ),
            "AGENTS.md": (
                "STRUCTURE.local.md",
                "未分类",
                "待验证",
                "已验证",
                "已过时",
                "详细",
                "简略",
                "软提示",
                "不是硬上限",
                "默认 2 条",
                "超过 2 条",
                "跨章引用",
                "逻辑分支下滑",
                "不设固定层数",
                "区域关联备注",
                "受控写入",
                "经验不是指令",
                "误唤醒与冲突",
                "必须常驻",
                "三要素",
            ),
            "README.md": (
                "STRUCTURE.local.md",
                "未分类",
                "已验证 / 待验证 / 已过时",
                "详细 / 简略 / 软提示",
                "不是硬上限",
                "默认 2 条",
                "超过 2 条",
                "跨章引用",
                "逻辑分支",
                "不设固定层数",
                "区域关联",
                "record_structure.py",
                "误唤醒",
                "冲突",
                "显式常驻措辞",
            ),
            "README.en.md": (
                "STRUCTURE.local.md",
                "unclassified",
                "verified / pending verification / obsolete",
                "detailed / brief / soft hint",
                "not a hard limit",
                "default is two entries",
                "when adding more",
                "cross-reference",
                "logical branches",
                "no fixed depth limit",
                "region dependencies",
                "record_structure.py",
                "false wake-up",
                "conflict",
                "explicit resident phrase",
            ),
        }
        for relative, phrases in docs.items():
            content = read_text(relative)
            for phrase in phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertIn(phrase, content)

        self.assertIn("STRUCTURE.local.md", read_text(".gitignore"))

    def test_structural_experience_files_are_packaged_and_linked(self) -> None:
        verifier = read_text("scripts/verify_package.py")
        for required in (
            "references/structural-experience.md",
            "references/structural-experience.en.md",
            "scripts/record_structure.py",
            "scripts/structure-schema.json",
            "tests/test_record_structure.py",
        ):
            with self.subTest(required=required):
                self.assertIn(required, verifier)
        self.assertIn(
            "scripts/verify_package.py",
            read_text("scripts/verify-package.ps1"),
        )

        language_verifier = read_text("scripts/verify_package.py")
        for relative in (
            "references/structural-experience.md",
            "references/structural-experience.en.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(f'"{relative}": (', language_verifier)
        self.assertIn("[中文](structural-experience.md)", language_verifier)
        self.assertIn("[English](structural-experience.en.md)", language_verifier)

    def test_report_templates_cover_all_structural_chapters(self) -> None:
        expectations = {
            "references/report-template.md": (
                "## 结构经验回收",
                "## 常驻隐藏坑覆盖",
                "RES-01",
                "RES-09",
                "未覆盖",
                "用户升级常驻",
                "用户原话最小摘录",
                "撤销/降级条件",
                "M > 12",
                "| 主章 | 最深检索路径 | 章覆盖状态 | 分支结果 | 命中条目 | 条目状态 | 注入级别 | 依据 |",
                "| A | `A/<slug>/...` |",
                "| B | ... |",
                "| C | ... |",
                "| D | ... |",
                "| E | ... |",
                "| F | ... |",
                "A-F 每章至少保留一行",
                "已翻阅 / 无信号 / 不适用 / 跨章引用 / 未分类",
                "已探索无命中（仅报告）",
                "冲突（整组未注入）",
                "主章 `X`；主分支",
                "冲突组：无",
                "兄弟粒度提示",
                "仅报告 warning",
                "超过默认 2 条时",
                "特殊原因",
            ),
            "references/report-template.en.md": (
                "## Structural experience harvest",
                "## Resident hidden-pitfall coverage",
                "RES-01",
                "RES-09",
                "uncovered",
                "User-promoted resident set",
                "Minimal user quote",
                "Revocation/downgrade condition",
                "M > 12",
                "| Primary chapter | Deepest path | Chapter coverage | Branch result | Entry matched | Entry status | Injection | Evidence |",
                "| A | `A/<slug>/...` |",
                "| B | ... |",
                "| C | ... |",
                "| D | ... |",
                "| E | ... |",
                "| F | ... |",
                "Keep at least one row for each A-F chapter",
                "opened / no signal / not applicable / cross-chapter reference / unclassified",
                "explored with no match (report only)",
                "conflict (group not injected)",
                "primary chapter `X`; primary branch",
                "Conflict group: none",
                "Sibling granularity warning",
                "report-only",
                "more than two entries",
                "why it cannot be merged or deferred",
            ),
        }
        for relative, phrases in expectations.items():
            content = read_text(relative)
            for phrase in phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertIn(phrase, content)

    def test_structural_experience_entries_obey_status_and_injection_rules(self) -> None:
        segment = str(SCHEMA["branch_segment_pattern"]).strip("^$")
        branch = rf"[A-F]/{segment}(?:/{segment})+"
        deep_branch = "A/" + "/".join(f"layer-{index}" for index in range(1, 9))
        self.assertRegex(deep_branch, rf"^{branch}$")
        status_labels = sorted(
            (
                label
                for status_key in SCHEMA["status_keys"]
                for label in SCHEMA["status_labels"][status_key]
            ),
            key=len,
            reverse=True,
        )
        injection_labels = sorted(
            (
                label
                for injection_key in SCHEMA["injection_keys"]
                for label in SCHEMA["injection_labels"][injection_key]
            ),
            key=len,
            reverse=True,
        )
        entry_re = re.compile(
            rf"^- (S-([A-F])-\d{{3}}) \| "
            rf"({'|'.join(re.escape(label) for label in status_labels)}) \| "
            rf"({'|'.join(re.escape(label) for label in injection_labels)}) \| "
            rf"({branch}) \| "
            rf"({branch}(?:; {branch})*|无|none) \| "
            rf"([^|\n]+) \| ([^|\n]+) \| ([^|\n]+) \| ([^|\n]+) \| ([^|\n]+)$"
        )
        pending_statuses = set(SCHEMA["status_labels"]["pending"])
        detailed_injections = set(SCHEMA["injection_labels"]["detailed"])

        for relative in (
            "references/structural-experience.md",
            "references/structural-experience.en.md",
        ):
            seen_ids = set()
            current_chapter = None
            lines = read_text(relative).splitlines()
            for line_number, line in enumerate(lines, start=1):
                chapter_match = re.match(r"^### ([A-F])\.", line)
                if chapter_match:
                    current_chapter = chapter_match.group(1)
                    continue
                if line.startswith("## ") and not line.startswith("### "):
                    current_chapter = None
                    continue
                if not line.startswith("- S-"):
                    continue

                match = entry_re.match(line)
                self.assertIsNotNone(
                    match,
                    msg=f"{relative}:{line_number}: malformed structural entry",
                )
                if match is None:
                    continue
                entry_id, chapter, status, injection, primary_branch, related = (
                    match.groups()[:6]
                )
                self.assertNotIn(
                    entry_id,
                    seen_ids,
                    msg=f"{relative}:{line_number}: duplicate structural entry {entry_id}",
                )
                seen_ids.add(entry_id)
                self.assertEqual(
                    current_chapter,
                    chapter,
                    msg=f"{relative}:{line_number}: {entry_id} is outside chapter {chapter}",
                )
                self.assertEqual(
                    primary_branch.split("/", 1)[0],
                    chapter,
                    msg=f"{relative}:{line_number}: primary branch does not match chapter {chapter}",
                )
                if related not in {"无", "none"}:
                    related_branches = related.split("; ")
                    self.assertNotIn(
                        primary_branch,
                        related_branches,
                        msg=f"{relative}:{line_number}: primary branch repeated in related branches",
                    )
                    self.assertEqual(
                        len(related_branches),
                        len(set(related_branches)),
                        msg=f"{relative}:{line_number}: duplicate related branch",
                    )
                if status in pending_statuses:
                    self.assertNotIn(
                        injection,
                        detailed_injections,
                        msg=f"{relative}:{line_number}: pending entry cannot use detailed injection",
                    )
                following_lines = [
                    candidate.strip()
                    for candidate in lines[line_number : line_number + 4]
                    if candidate.strip()
                ]
                self.assertTrue(
                    following_lines
                    and following_lines[0].startswith(("- 区域关联：", "- Region links:")),
                    msg=f"{relative}:{line_number}: entry must be followed by a region-link note",
                )


if __name__ == "__main__":
    unittest.main()
