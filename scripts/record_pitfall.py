#!/usr/bin/env python3
"""Append a verified pitfall to the skill's local or maintainer memory.

The recorder is intentionally small and fail-closed:

* it can only write ``PITFALLS.md`` or ``PITFALLS.local.md`` directly under
  the skill root;
* it never rewrites history and treats an exact duplicate as a no-op;
* it rejects separators, newlines, empty fields, and common secret or personal
  patterns before touching the file;
* it creates ``PITFALLS.local.md`` on first use but never creates a missing
  repository ``PITFALLS.md``.

Exit codes:
    0 = appended, duplicate, or dry-run
    1 = validation, safety, or write error
    2 = usage error
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parent.parent
LOCAL_NAME = "PITFALLS.local.md"
REPO_NAME = "PITFALLS.md"
TAG_LIMIT = 40
MAX_TAGS = 8
FIELD_LIMIT = 600
PARENT_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{2}$")
ENTRY_RE = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)$"
)

LOCAL_HEADER = """# 本地避坑记录 / Local Pitfalls Log

格式：`YYYY-MM-DD | 标签 | 触发场景 | 错误做法 | 正确做法 | 验证方式`

规则：

- 只记录本机使用本技能时核实过的新失败模式；不写目标项目原文、密钥、个人信息或绝对路径。
- 先查重；完全重复不追加。同类下的新失败机制可以新增，并在触发场景里注明父条目。
- 只追加，不删除；升级技能时保留本文件，不覆盖。
"""

SENSITIVE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "Windows user path",
        re.compile(r'(?i)\b[A-Z]:\\Users\\(?!<)[^\\\s"\'`<>]+'),
    ),
    (
        "Windows user path (slash)",
        re.compile(r'(?i)\b[A-Z]:/' + r'Users/(?!<)[^/\s"\'`<>]+'),
    ),
    (
        "Unix home path",
        re.compile(r'(?i)(?<![\w.])/' + r'home/(?!<)[^/\s"\'`<>]+'),
    ),
    (
        "macOS user path",
        re.compile(
            r'(?i)(?<![\w.])/'
            + r'Users/(?!(?:<|Shared\b|Guest\b))'
            + r'[^/\s"\'`<>]+'
        ),
    ),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "GitHub token",
        re.compile(
            r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"
            r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
        ),
    ),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "Assigned secret",
        re.compile(
            r'(?i)["\']?\b(api[_-]?key|secret|token|password|passwd|pwd)\b["\']?'
            r'\s*[:=]\s*["\']?'
            r"(?!<|\$|\{|%|\[|REDACTED|CHANGE_ME|example|placeholder)"
            r"[A-Za-z0-9_\-\.]{12,}"
        ),
    ),
    (
        "Private IPv4",
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
    (
        "Email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
)


@dataclass(frozen=True)
class Entry:
    tag: str
    trigger: str
    wrong: str
    right: str
    verify: str
    parent: Optional[str] = None


@dataclass(frozen=True)
class RecordResult:
    status: str
    path: Path
    line: Optional[str] = None


def _reject_sensitive(name: str, value: str) -> None:
    for pattern_name, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"{name} looks sensitive ({pattern_name}); use a placeholder instead"
            )


def _clean_field(name: str, value: str, limit: int = FIELD_LIMIT) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    if "\n" in text or "\r" in text:
        raise ValueError(f"{name} must be a single line")
    if "|" in text:
        raise ValueError(f"{name} must not contain the '|' separator")
    if len(text) > limit:
        raise ValueError(f"{name} is longer than {limit} characters")
    _reject_sensitive(name, text)
    return text


def _clean_tags(raw: str) -> str:
    tags: List[str] = []
    for part in (raw or "").split(","):
        tag = " ".join(part.strip().split())
        if not tag:
            continue
        if "|" in tag or "\n" in tag or "\r" in tag:
            raise ValueError("tag must not contain separators or newlines")
        if len(tag) > TAG_LIMIT:
            raise ValueError(f"tag is longer than {TAG_LIMIT} characters: {tag}")
        _reject_sensitive("tag", tag)
        tags.append(tag)
    if not tags:
        raise ValueError("at least one tag is required")
    if len(tags) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags are allowed")
    return ", ".join(tags)


def _validate_entry(entry: Entry) -> Entry:
    parent = (entry.parent or "").strip() or None
    if parent is not None and not PARENT_RE.fullmatch(parent):
        raise ValueError("parent must look like CICD-02 or MAC-H01")
    return Entry(
        tag=_clean_tags(entry.tag),
        trigger=_clean_field("trigger", entry.trigger),
        wrong=_clean_field("wrong", entry.wrong),
        right=_clean_field("right", entry.right),
        verify=_clean_field("verify", entry.verify),
        parent=parent,
    )


def _normalise_date(raw: Optional[str]) -> str:
    if raw is None:
        return _datetime.date.today().isoformat()
    try:
        return _datetime.date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc


def build_line(entry: Entry, record_date: Optional[str] = None) -> str:
    clean = _validate_entry(entry)
    date_text = _normalise_date(record_date)
    trigger = clean.trigger
    if clean.parent and clean.parent not in trigger:
        trigger = f"{trigger}（同类新机制，父条目 {clean.parent}）"
    return (
        f"{date_text} | {clean.tag} | {trigger} | {clean.wrong} | "
        f"{clean.right} | {clean.verify}"
    )


def _memory_path(root: Path, scope: str) -> Path:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    if not any((root / name).is_file() for name in ("SKILL.md", "AGENTS.md", REPO_NAME)):
        raise ValueError("root does not look like a project-health skill directory")

    if scope == "auto":
        if (root / LOCAL_NAME).is_file():
            scope = "local"
        elif root.parent.name.casefold() == "skills":
            scope = "local"
        elif (root / ".git").exists():
            scope = "repo"
        else:
            scope = "local"
    if scope not in {"repo", "local"}:
        raise ValueError("scope must be auto, repo, or local")

    path = root / (LOCAL_NAME if scope == "local" else REPO_NAME)
    resolved = path.resolve(strict=False)
    if resolved.parent != root:
        raise ValueError("refusing to write outside the skill root")
    if scope == "repo" and not path.is_file():
        raise ValueError(f"repository memory does not exist: {path}")
    return path


def _normalise_for_compare(value: str) -> str:
    return " ".join(value.split()).casefold()


def _is_duplicate(existing: str, line: str) -> bool:
    target = ENTRY_RE.match(line)
    if target is None:
        return False
    target_fields = tuple(_normalise_for_compare(part) for part in target.groups())
    for raw in existing.splitlines():
        candidate = raw.strip()
        if candidate.startswith("- "):
            candidate = candidate[2:].strip()
        match = ENTRY_RE.match(candidate)
        if match is None:
            continue
        fields = tuple(_normalise_for_compare(part) for part in match.groups())
        if fields == target_fields:
            return True
    return False


def _read_existing(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"refusing to append to a UTF-8 BOM file: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"memory file is not valid UTF-8: {path}") from exc


def _create_local(path: Path) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(LOCAL_HEADER)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return


def _append_line(path: Path, existing: str, line: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def record(
    root: Path,
    entry: Entry,
    scope: str = "auto",
    record_date: Optional[str] = None,
    dry_run: bool = False,
) -> RecordResult:
    line = build_line(entry, record_date)
    path = _memory_path(root, scope)
    existing = _read_existing(path)
    if _is_duplicate(existing, line):
        return RecordResult(status="duplicate", path=path)
    if dry_run:
        return RecordResult(status="dry-run", path=path, line=line)
    if not path.exists():
        _create_local(path)
        existing = _read_existing(path)
    _append_line(path, existing, line)
    return RecordResult(status="appended", path=path, line=line)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="comma-separated tags")
    parser.add_argument("--trigger", required=True, help="when the pitfall occurs")
    parser.add_argument("--wrong", required=True, help="what went wrong")
    parser.add_argument("--right", required=True, help="the verified correct approach")
    parser.add_argument("--verify", required=True, help="how it was verified")
    parser.add_argument(
        "--parent",
        help="parent ID for a new mechanism under an existing class, e.g. CICD-02",
    )
    parser.add_argument("--date", help="record date in YYYY-MM-DD form")
    parser.add_argument(
        "--scope",
        choices=("auto", "repo", "local"),
        default="auto",
        help=(
            "auto uses local if PITFALLS.local.md exists or the skill is under a "
            "skills/ directory, else repo when .git exists"
        ),
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="skill root")
    parser.add_argument("--dry-run", action="store_true", help="validate and print only")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    entry = Entry(
        tag=args.tag,
        trigger=args.trigger,
        wrong=args.wrong,
        right=args.right,
        verify=args.verify,
        parent=args.parent,
    )
    try:
        result = record(
            args.root,
            entry,
            scope=args.scope,
            record_date=args.date,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: could not write memory: {exc}", file=sys.stderr)
        return 1

    print(f"{result.status.upper()}: {result.path}")
    if result.line:
        print(result.line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
