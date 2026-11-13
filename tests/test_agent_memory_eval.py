#!/usr/bin/env python3
"""Unit tests for the optional agent-memory evaluation harness."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "agent_memory_eval.py"


def _load_harness() -> Any:
    spec = importlib.util.spec_from_file_location("agent_memory_eval_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EVAL = _load_harness()


class AgentMemoryEvalTests(unittest.TestCase):
    def test_score_entry_accepts_english_and_chinese_mechanisms(self) -> None:
        english = (
            "2026-11-13 | testing | the runner collects 0 tests and prints PASS | "
            "wrong | right | verify"
        )
        chinese = (
            "2026-11-13 | testing | 测试发现收集到 0 个用例，仍输出 PASS | "
            "错误 | 正确 | 验证"
        )
        self.assertTrue(EVAL.score_entry(english, [["0 test"], ["pass"]]))
        self.assertTrue(EVAL.score_entry(chinese, [["0 个用例"], ["pass"]]))
        self.assertFalse(
            EVAL.score_entry(english, [["coverage"], ["threshold"]])
        )

    def test_matching_entries_ignores_headers_and_unrelated_lines(self) -> None:
        text = (
            "# local log\n\n"
            "2026-11-13 | testing | unrelated entry | wrong | right | verify\n"
            "2026-11-13 | testing | coverage 0% still prints PASS | wrong | right | verify\n"
        )
        matched = EVAL.matching_entries(text, [["coverage"], ["0%"]])
        self.assertEqual(len(matched), 1)
        self.assertIn("coverage 0%", matched[0])

    def test_baseline_hits_is_case_insensitive(self) -> None:
        self.assertEqual(
            EVAL.baseline_hits("CI only skips tests today", ["skips tests"]),
            ["skips tests"],
        )
        self.assertEqual(EVAL.baseline_hits("unrelated", ["zero tests"]), [])

    def test_manifest_ignores_caches_and_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-eval-manifest-") as temp_dir:
            root = Path(temp_dir)
            (root / "src.py").write_text("print('one')\n", encoding="utf-8")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "src.pyc").write_bytes(b"cache")
            (root / ".coverage").write_text("runtime\n", encoding="utf-8")
            html = root / "htmlcov"
            html.mkdir()
            (html / "index.html").write_text("report\n", encoding="utf-8")

            before = EVAL.manifest(root)
            self.assertIn("src.py:", before)
            self.assertNotIn("__pycache__", before)
            self.assertNotIn(".coverage", before)
            self.assertNotIn("htmlcov", before)

            (root / "src.py").write_text("print('two')\n", encoding="utf-8")
            self.assertNotEqual(before, EVAL.manifest(root))

    def test_prompt_does_not_reveal_the_memory_answer(self) -> None:
        prompt = EVAL.PROMPT_PATH.read_text(encoding="utf-8").casefold()
        for forbidden in ("record", "pitfall", "memory", "pitfalls"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, prompt)

    def test_every_scenario_has_scoring_groups(self) -> None:
        for scenario_dir in EVAL.scenario_dirs():
            expect = EVAL.load_expect(scenario_dir)
            with self.subTest(scenario=expect["id"]):
                self.assertTrue(expect["required_groups"])
                self.assertTrue(expect["baseline_forbidden"])


if __name__ == "__main__":
    unittest.main()
