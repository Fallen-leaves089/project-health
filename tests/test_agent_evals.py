from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECORD = "tests/agent-evals/dsh-deepseek-flash-d7-2026-11-23.md"
DECISION_PATH = "tests/agent-evals/dsh-deepseek-flash-d7-decision-path-2026-11-23.md"


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class AgentEvaluationRecordTests(unittest.TestCase):
    def test_dsh_observation_identifies_all_three_objects(self) -> None:
        text = read_text(RECORD)
        for marker in (
            "https://github.com/Fallen-leaves089/project-health",
            "https://github.com/Fallen-leaves089/dsh-grounded-audit",
            "DeepSeek Harness (DSH)",
            "Validation level: observed",
            "19,969,040",
            "Compaction errors: `0`",
        ):
            self.assertIn(marker, text)

    def test_dsh_observation_does_not_claim_validation(self) -> None:
        text = read_text(RECORD)
        self.assertIn("supports `observed`, not `validated`", text)
        self.assertNotIn("Validation level: validated", text)
        self.assertNotIn("Result: validated", text)

    def test_readmes_link_to_the_observation(self) -> None:
        relative_link = RECORD
        self.assertIn(relative_link, read_text("README.md"))
        self.assertIn(relative_link, read_text("README.en.md"))

    def test_changelog_records_the_observation_as_unreleased(self) -> None:
        text = read_text("CHANGELOG.md")
        self.assertIn("## Unreleased", text)
        self.assertIn("observed", text)
        self.assertIn("19,969,040", text)

    def test_decision_path_is_complete_and_sanitized(self) -> None:
        text = read_text(DECISION_PATH)
        for index in range(1, 12):
            self.assertIn(f"### DP-{index:02d}:", text)
        for marker in (
            "Fallen-leaves089/project-health",
            "Fallen-leaves089/dsh-grounded-audit",
            "DeepSeek Harness",
            "500,004",
            "41 entries, 0 differences",
        ):
            self.assertIn(marker, text)
        for forbidden in (
            "D:\\codex",
            "C:\\Users",
            "/mnt/dsec",
            "127.0.0.1:",
            "sk-",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
