#!/usr/bin/env python3
"""Optional behavioral evaluation: does an agent record a genuinely new pitfall?

This is deliberately not part of the default unit-test or CI run. It copies the
skill and a fixture target into a temporary directory, asks a fresh Codex
process to audit the target without mentioning memory or recording, and then
checks whether the agent appended a matching entry to ``PITFALLS.local.md``.

The fixture must be absent from the baseline ``PITFALLS.md``; otherwise the
scenario is not "unseen" and the evaluator fails during setup.

Usage:
    python -B tests/agent_memory_eval.py --codex <codex.exe>
    python -B tests/agent_memory_eval.py --skill-root <installed-skill> --codex <codex.exe>

Exit codes:
    0 = at least --min-passed scenarios passed
    1 = one or more scenarios failed
    2 = usage or environment error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "agent-memory-eval"
PROMPT_PATH = FIXTURE_ROOT / "prompt.txt"
LOCAL_NAME = "PITFALLS.local.md"
BASELINE_NAME = "PITFALLS.md"
CACHE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
}
RUNTIME_ARTIFACTS = {".coverage"}
ENTRY_RE = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)$"
)
PARENT_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{2}\b")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(root: Path, exclude: Optional[Set[str]] = None) -> str:
    """Return a stable hash manifest, ignoring caches and known runtime files."""
    root = root.resolve()
    excluded = {item.replace("\\", "/") for item in (exclude or set())}
    lines: List[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        parts = set(relative.split("/"))
        if parts & CACHE_DIRS:
            continue
        if path.suffix == ".pyc" or path.name in RUNTIME_ARTIFACTS:
            continue
        if relative in excluded or path.name in excluded:
            continue
        lines.append(f"{relative}:{_sha256(path)}")
    return "\n".join(lines)


def load_expect(scenario_dir: Path) -> Dict[str, Any]:
    expect_path = scenario_dir / "expect.json"
    with expect_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    required = {"id", "description", "baseline_forbidden", "required_groups"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"{expect_path} is missing: {', '.join(sorted(missing))}")
    return data


def scenario_dirs() -> List[Path]:
    return sorted(
        path
        for path in FIXTURE_ROOT.iterdir()
        if path.is_dir() and (path / "expect.json").is_file()
    )


def _entries(text: str) -> Iterable[str]:
    for raw in text.splitlines():
        candidate = raw.strip()
        if candidate.startswith("- "):
            candidate = candidate[2:].strip()
        if ENTRY_RE.match(candidate):
            yield candidate


def score_entry(entry: str, required_groups: Sequence[Sequence[str]]) -> bool:
    lowered = entry.casefold()
    for group in required_groups:
        if not any(keyword.casefold() in lowered for keyword in group):
            return False
    return True


def matching_entries(text: str, required_groups: Sequence[Sequence[str]]) -> List[str]:
    return [entry for entry in _entries(text) if score_entry(entry, required_groups)]


def baseline_hits(baseline: str, forbidden: Sequence[str]) -> List[str]:
    lowered = baseline.casefold()
    return [phrase for phrase in forbidden if phrase.casefold() in lowered]


def _safe_cleanup(path: Path) -> None:
    resolved = path.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if resolved.parent != temp_root or not resolved.name.startswith(
        "project-health-agent-eval-"
    ):
        raise RuntimeError(f"refusing to remove unexpected path: {resolved}")
    shutil.rmtree(resolved)


def _copy_skill(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            LOCAL_NAME,
        ),
    )


def _copy_target(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def _default_codex() -> Optional[str]:
    return os.environ.get("CODEX_EXE") or shutil.which("codex")


def _excerpt(text: str, limit: int = 700) -> str:
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def run_scenario(
    scenario_dir: Path,
    skill_root: Path,
    codex: str,
    codex_args: Sequence[str],
    timeout: int,
    keep: bool,
    output_dir: Optional[Path],
    require_scenario_match: bool,
) -> Dict[str, Any]:
    expect = load_expect(scenario_dir)
    scenario_id = str(expect["id"])
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f"project-health-agent-eval-{scenario_id}-")
    )
    result: Dict[str, Any] = {
        "scenario": scenario_id,
        "description": expect["description"],
        "passed": False,
        "temp_dir": str(temp_dir) if keep else None,
    }

    def finish() -> Dict[str, Any]:
        result["temp_dir"] = str(temp_dir) if keep else None
        return result

    try:
        skill = temp_dir / "skill"
        target = temp_dir / "target"
        _copy_skill(skill_root.resolve(), skill)
        _copy_target(scenario_dir / "target", target)

        local_memory = skill / LOCAL_NAME
        baseline = skill / BASELINE_NAME
        baseline_before = _sha256(baseline)
        baseline_text = baseline.read_text(encoding="utf-8")
        hits = baseline_hits(baseline_text, expect["baseline_forbidden"])
        if hits:
            result["error"] = (
                "scenario is already covered by the baseline: " + ", ".join(hits)
            )
            return finish()
        if local_memory.exists():
            result["error"] = "copied skill unexpectedly contains PITFALLS.local.md"
            return finish()

        target_before = manifest(target)
        skill_before = manifest(skill, exclude={LOCAL_NAME, BASELINE_NAME})
        prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        command = [
            codex,
            *codex_args,
            "exec",
            "-C",
            str(temp_dir),
            "--skip-git-repo-check",
            "-s",
            "workspace-write",
            "--ephemeral",
            "--color",
            "never",
            "-o",
            str(temp_dir / "last-message.txt"),
            prompt,
        ]
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        started = time.time()
        try:
            completed = subprocess.run(
                command,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            result["error"] = f"agent timed out after {timeout}s"
            result["elapsed_seconds"] = round(time.time() - started, 1)
            return finish()
        result["elapsed_seconds"] = round(time.time() - started, 1)
        result["codex_returncode"] = completed.returncode

        last_message_path = temp_dir / "last-message.txt"
        last_message = (
            last_message_path.read_text(encoding="utf-8", errors="replace")
            if last_message_path.is_file()
            else ""
        )
        result["last_message_excerpt"] = _excerpt(last_message)
        result["memory_created"] = local_memory.is_file()
        result["target_unchanged"] = manifest(target) == target_before
        result["skill_unchanged"] = (
            manifest(skill, exclude={LOCAL_NAME, BASELINE_NAME}) == skill_before
        )
        result["baseline_unchanged"] = _sha256(baseline) == baseline_before

        if local_memory.is_file():
            memory_text = local_memory.read_text(encoding="utf-8")
            entries = list(_entries(memory_text))
            matched = matching_entries(memory_text, expect["required_groups"])
            result["entry_count"] = len(entries)
            result["matched_entry_count"] = len(matched)
            if matched:
                chosen = matched[0]
                result["matched_entry"] = _excerpt(chosen, 500)
                hint = str(expect.get("parent_hint") or "")
                result["parent_cited"] = bool(
                    hint and hint.casefold() in chosen.casefold()
                )
                result["any_parent_id_cited"] = bool(PARENT_RE.search(chosen))
            else:
                result["entry_excerpt"] = _excerpt(memory_text, 500)
        else:
            result["entry_count"] = 0
            result["matched_entry_count"] = 0

        result["report_mentions_memory"] = bool(
            last_message
            and ("记忆" in last_message or "Memory" in last_message)
            and ("PITFALLS" in last_message or "pitfall" in last_message.lower())
        )
        invariants_ok = bool(
            completed.returncode == 0
            and result["target_unchanged"]
            and result["skill_unchanged"]
            and result["baseline_unchanged"]
        )
        result["any_new_entry"] = bool(result.get("entry_count", 0) > 0)
        result["scenario_match"] = bool(result.get("matched_entry_count", 0) > 0)
        result["invariants_ok"] = invariants_ok
        result["passed"] = bool(
            invariants_ok
            and (
                result["scenario_match"]
                if require_scenario_match
                else result["any_new_entry"]
            )
        )
        return finish()
    except Exception as exc:  # pragma: no cover - diagnostic path for manual runs
        result["error"] = f"{type(exc).__name__}: {exc}"
        return finish()
    finally:
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            if (temp_dir / "last-message.txt").is_file():
                shutil.copy2(
                    temp_dir / "last-message.txt",
                    output_dir / f"{scenario_id}-last-message.txt",
                )
            if (temp_dir / "skill" / LOCAL_NAME).is_file():
                shutil.copy2(
                    temp_dir / "skill" / LOCAL_NAME,
                    output_dir / f"{scenario_id}-PITFALLS.local.md",
                )
        if not keep:
            _safe_cleanup(temp_dir)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    scenarios = [load_expect(path)["id"] for path in scenario_dirs()]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=scenarios,
        help="scenario to run; repeat for multiple; default is all",
    )
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=ROOT,
        help="skill package to copy (default: this repository)",
    )
    parser.add_argument(
        "--codex",
        default=_default_codex(),
        help="Codex executable (default: CODEX_EXE or PATH)",
    )
    parser.add_argument(
        "--codex-arg",
        action="append",
        default=[],
        help="extra argument placed before 'exec' (repeatable; useful for wrappers)",
    )
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--min-passed",
        type=int,
        default=1,
        help="minimum number of scenarios that must pass (default: 1)",
    )
    parser.add_argument(
        "--require-scenario-match",
        action="store_true",
        help="require the recorded entry to match the fixture scenario, not just any new entry",
    )
    parser.add_argument("--keep", action="store_true", help="keep temporary directories")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="copy last messages and local memory files here",
    )
    parser.add_argument("--list", action="store_true", help="list scenarios and exit")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    all_dirs = scenario_dirs()
    if args.list:
        for path in all_dirs:
            expect = load_expect(path)
            print(f"{expect['id']}: {expect['description']}")
        return 0
    if not args.codex:
        print(
            "ERROR: Codex executable not found; pass --codex or set CODEX_EXE.",
            file=sys.stderr,
        )
        return 2
    if not (args.skill_root / "SKILL.md").is_file():
        print(f"ERROR: skill root has no SKILL.md: {args.skill_root}", file=sys.stderr)
        return 2

    selected = [
        path
        for path in all_dirs
        if not args.scenario or load_expect(path)["id"] in set(args.scenario)
    ]
    if not selected:
        print("ERROR: no scenarios selected.", file=sys.stderr)
        return 2
    if args.min_passed > len(selected):
        print(
            f"ERROR: --min-passed {args.min_passed} exceeds selected {len(selected)}.",
            file=sys.stderr,
        )
        return 2

    results: List[Dict[str, Any]] = []
    for scenario_dir in selected:
        expect = load_expect(scenario_dir)
        print(f"RUN: {expect['id']}", file=sys.stderr)
        result = run_scenario(
            scenario_dir,
            args.skill_root,
            args.codex,
            args.codex_arg,
            args.timeout,
            args.keep,
            args.output_dir,
            args.require_scenario_match,
        )
        results.append(result)
        print(
            f"  {'PASS' if result['passed'] else 'FAIL'}: "
            f"{result.get('error', 'new_entry={} scenario_match={} target_unchanged={}'.format(result.get('any_new_entry'), result.get('scenario_match'), result.get('target_unchanged')))}",
            file=sys.stderr,
        )

    passed = sum(1 for result in results if result["passed"])
    summary = {
        "selected": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "scenario_matches": sum(1 for result in results if result.get("scenario_match")),
        "require_scenario_match": args.require_scenario_match,
        "min_passed": args.min_passed,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed >= args.min_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
