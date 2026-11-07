#!/usr/bin/env python3
"""Scan the skill package for personal paths, private addresses, and secret patterns.

The scanner prints only ``file:line [pattern]``. It never prints the matched value,
so a finding cannot leak a secret into a report or terminal scrollback.

Exit codes:
    0 = clean
    1 = findings
    2 = usage error or self-test failure
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parent.parent

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".ps1",
    ".psm1",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".env",
    ".sh",
    ".cmd",
    ".bat",
    ".js",
    ".ts",
    ".py",
    ".fixture",
    ".xml",
    ".properties",
    ".pub",
    "",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "bin",
    "obj",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".vs",
    ".idea",
}

@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]


@dataclass
class ScanResult:
    findings: List[str]
    files_scanned: int


def _patterns(extra: Sequence[str] = ()) -> List[Pattern]:
    patterns = [
        Pattern(
            "Windows user path",
            re.compile(r'(?i)\b[A-Z]:\\Users\\(?!<)[^\\\s"\'`<>]+'),
        ),
        Pattern(
            "Windows user path (slash)",
            re.compile(r'(?i)\b[A-Z]:/Users/(?!<)[^/\s"\'`<>]+'),
        ),
        Pattern(
            "Unix home path",
            re.compile(r'(?i)(?<![\w.])/' + r'home/(?!<)[^/\s"\'`<>]+'),
        ),
        Pattern(
            "Private IPv4",
            re.compile(
                r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
                r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
                r"|192\.168\.\d{1,3}\.\d{1,3})\b"
            ),
        ),
        Pattern("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
        Pattern(
            "GitHub token",
            re.compile(
                r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"
                r"|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
            ),
        ),
        Pattern("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        Pattern("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
        Pattern(
            "Assigned secret",
            re.compile(
                r'(?i)["\']?\b(api[_-]?key|secret|token|password|passwd|pwd)\b["\']?'
                r'\s*[:=]\s*["\']?'
                r"(?!<|\$|\{|%|\[|REDACTED|CHANGE_ME|example|placeholder)"
                r"[A-Za-z0-9_\-\.]{12,}"
            ),
        ),
    ]

    for index, literal in enumerate(extra, start=1):
        patterns.append(Pattern(f"Extra pattern {index}", re.compile(re.escape(literal))))

    return patterns


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def scan(path: Path, extra: Sequence[str] = (), quiet: bool = False) -> ScanResult:
    """Scan one file or a directory and return relative finding locations."""

    root = path.resolve()
    patterns = _patterns(extra)
    findings: List[str] = []
    files_scanned = 0

    for file_path in _iter_files(root):
        files_scanned += 1
        if root.is_file():
            relative = file_path.name
        else:
            relative = file_path.relative_to(root).as_posix()

        data = file_path.read_bytes()
        if b"\x00" in data:
            continue
        text = data.decode("utf-8-sig", errors="replace")

        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                if pattern.regex.search(line):
                    findings.append(f"{relative}:{line_number}  [{pattern.name}]")

    if not quiet:
        for finding in findings:
            print(finding)

    return ScanResult(findings=findings, files_scanned=files_scanned)


def self_test() -> int:
    """Run positive and negative cases against a temporary fixture tree."""

    with tempfile.TemporaryDirectory(prefix="fhc-redaction-") as temp_dir:
        root = Path(temp_dir)
        path_sep = chr(92)
        dirty_windows_path = (
            "Path: C:" + path_sep + "Users" + path_sep + "example-user"
            + path_sep + "work" + path_sep + "project"
        )
        dirty_windows_path_slash = "Path: C:/" + "Users/example-user/work/project"
        dirty_assigned_secret = '{"API_KEY": "' + "abcdefghijklmnopqrstuvwxyz" + '"}'
        dirty_private_ip = "host: " + "192" + ".168" + ".1" + ".10"
        dirty_extra_marker = "marker: ACME-" + "INTERNAL-TOKEN"
        samples: List[Tuple[str, str, Sequence[str], bool, str]] = [
            (
                "clean.md",
                "\n".join(
                    [
                        "# Clean sample",
                        r"Install under C:\Users\<you>\.agent-skills\\",
                        "Use <REDACTED> for secrets.",
                        "Host: 192.168.x.x",
                        "Token: <REDACTED>",
                    ]
                ),
                (),
                False,
                "clean sample passes",
            ),
            (
                "dirty-path.md",
                dirty_windows_path,
                (),
                True,
                "Windows backslash path is caught",
            ),
            (
                "dirty-path-slash.md",
                dirty_windows_path_slash,
                (),
                True,
                "Windows slash path is caught",
            ),
            (
                "dirty-key.md",
                "key: " + "sk-" + ("A" * 32),
                (),
                True,
                "OpenAI-style key is caught",
            ),
            (
                "dirty-json-key.md",
                dirty_assigned_secret,
                (),
                True,
                "quoted JSON secret is caught",
            ),
            (
                "dirty-ip.md",
                dirty_private_ip,
                (),
                True,
                "private IPv4 is caught",
            ),
            (
                "dirty-extra.md",
                dirty_extra_marker,
                ("ACME-INTERNAL",),
                True,
                "extra literal pattern is caught",
            ),
        ]

        ok = True
        for name, content, extra, should_find, label in samples:
            fixture = root / name
            fixture.write_text(content + "\n", encoding="utf-8")
            result = scan(fixture, extra=extra, quiet=True)
            actual = bool(result.findings)
            if actual != should_find:
                print(
                    f"SELF-TEST FAIL: {label} "
                    f"(expected findings={should_find}, got {len(result.findings)})",
                    file=sys.stderr,
                )
                ok = False
            else:
                print(f"SELF-TEST OK: {label} (findings={len(result.findings)})")

        self_scan = scan(SCRIPT_PATH, quiet=True)
        if self_scan.findings:
            print(
                "SELF-TEST FAIL: scanner source contains redaction findings: "
                + ", ".join(self_scan.findings),
                file=sys.stderr,
            )
            ok = False
        else:
            print("SELF-TEST OK: scanner source passes the package scan (findings=0)")

        bootstrap = root / SCRIPT_PATH.name
        bootstrap.write_text(
            SCRIPT_PATH.read_text(encoding="utf-8") + "\n" + dirty_windows_path + "\n",
            encoding="utf-8",
        )
        bootstrap_result = scan(bootstrap, quiet=True)
        if not bootstrap_result.findings:
            print(
                "SELF-TEST FAIL: bootstrap copy was not scanned for sensitive content",
                file=sys.stderr,
            )
            ok = False
        else:
            print(
                "SELF-TEST OK: bootstrap copy is scanned for sensitive content "
                f"(findings={len(bootstrap_result.findings)})"
            )

    if not ok:
        print("SELF-TEST FAIL", file=sys.stderr)
        return 2

    print("SELF-TEST PASS")
    return 0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_ROOT,
        help="file or directory to scan (default: package root)",
    )
    parser.add_argument(
        "--extra-pattern",
        action="append",
        default=[],
        help="additional literal string to flag; may be repeated",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run built-in positive and negative cases, then exit",
    )
    parser.add_argument("--quiet", action="store_true", help="print only the summary")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.self_test:
        return self_test()

    target = args.path.resolve()
    if not target.exists():
        print(f"ERROR: path not found: {target}", file=sys.stderr)
        return 2
    if not target.is_file() and not target.is_dir():
        print("ERROR: path must be a file or directory.", file=sys.stderr)
        return 2

    result = scan(target, extra=args.extra_pattern, quiet=args.quiet)
    print(f"Scanned {result.files_scanned} file(s); {len(result.findings)} finding(s).")
    if result.findings:
        print("REDACTION CHECK FAILED: review the findings above.", file=sys.stderr)
        return 1

    print("REDACTION CHECK PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
