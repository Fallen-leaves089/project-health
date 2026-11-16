#!/usr/bin/env python3
"""Scan the skill package for personal paths, private addresses, and secret patterns.

The scanner prints only ``file:line [pattern]``. It never prints the matched value,
so a finding cannot leak a secret into a report or terminal scrollback.

Exit codes:
    0 = clean
    1 = findings or unscannable input
    2 = usage error or self-test failure
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parent.parent

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

BINARY_EXTENSIONS = {
    ".7z",
    ".a",
    ".avi",
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".docx",
    ".dylib",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lib",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".otf",
    ".p12",
    ".pdf",
    ".pfx",
    ".png",
    ".pptx",
    ".pyc",
    ".pyo",
    ".rar",
    ".so",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".tif",
    ".tiff",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".whl",
    ".woff",
    ".woff2",
    ".xlsx",
    ".zip",
}

ASSIGNED_SECRET_FIELD = (
    r"(?:api[_-]?key|"
    r"(?:client|signing|encryption)[_-]?(?:secret|key|token)|"
    r"aws[_-]?secret[_-]?access[_-]?key|"
    r"access[_-]?key(?:[_-]?id)?|"
    r"secret[_-]?key|private[_-]?key|secret|"
    r"(?:access|refresh|session|auth|bearer|id)[_-]?token|"
    r"token|password|passwd|pwd|passphrase)"
)

ASSIGNED_SECRET_RE = re.compile(
    rf'(?i)(?<![A-Za-z0-9_])["\']?{ASSIGNED_SECRET_FIELD}'
    r'(?![A-Za-z0-9_])["\']?\s*[:=]\s*["\']?'
    r"(?!<|\$|\{|%|\[|REDACTED|CHANGE_ME|example|placeholder|"
    r"null|true|false|none|\*+)"
    r"[A-Za-z0-9_\-\.\/+=$]{12,}"
)


def _is_plausible_text(text: str) -> bool:
    """Reject control-heavy or unassigned UTF-16 decodings of binary data."""

    if "\x00" in text:
        return False
    if not text:
        return True
    bad = 0
    for char in text:
        if char in "\r\n\t":
            continue
        category = unicodedata.category(char)
        if category[0] in "LNPSZM" or category == "Cf":
            continue
        bad += 1
    return bad <= max(1, len(text) // 50)


def _decode_utf16_without_bom(data: bytes) -> Optional[str]:
    """Decode no-BOM UTF-16 only when the byte order is unambiguous."""

    if not data or len(data) % 2:
        return None

    candidates: List[Tuple[str, str]] = []
    for encoding in ("utf-16-le", "utf-16-be"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _is_plausible_text(text):
            candidates.append((encoding, text))

    if not candidates:
        return None

    half = len(data) // 2
    even_zero = sum(1 for index in range(0, len(data), 2) if data[index] == 0)
    odd_zero = sum(1 for index in range(1, len(data), 2) if data[index] == 0)
    zero_floor = max(2, half // 4)
    candidate_map = dict(candidates)
    if odd_zero >= zero_floor and odd_zero > (even_zero * 2) and "utf-16-le" in candidate_map:
        return candidate_map["utf-16-le"]
    if even_zero >= zero_floor and even_zero > (odd_zero * 2) and "utf-16-be" in candidate_map:
        return candidate_map["utf-16-be"]
    if len(candidates) == 1:
        return candidates[0][1]

    def ascii_score(text: str) -> int:
        return sum(
            1
            for char in text
            if char in "\r\n\t" or " " <= char <= "~"
        )

    if even_zero == 0 and odd_zero == 0:
        scored = sorted(
            ((ascii_score(text), encoding, text) for encoding, text in candidates),
            reverse=True,
        )
        if scored and scored[0][0] > 0:
            if len(scored) == 1 or scored[0][0] > (scored[1][0] * 2):
                return scored[0][2]
    return None


def _decode_text(data: bytes) -> Optional[str]:
    """Decode UTF-8/UTF-16 text, or return None for an unscannable file."""

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    try:
        utf8_text = data.decode("utf-8")
    except UnicodeDecodeError:
        utf8_text = None

    if utf8_text is not None and "\x00" not in utf8_text:
        return utf8_text

    utf16_text = _decode_utf16_without_bom(data)
    if utf16_text is not None:
        return utf16_text
    return utf8_text


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]


@dataclass
class ScanResult:
    findings: List[str]
    files_scanned: int
    files_skipped_binary: int
    errors: List[str]


def _patterns(extra: Sequence[str] = ()) -> List[Pattern]:
    patterns = [
        Pattern(
            "Windows user path",
            re.compile(r'(?i)\b[A-Z]:\\Users\\(?!<)[^\\\s"\'`<>]+'),
        ),
        Pattern(
            "Windows user path (slash)",
            re.compile(r'(?i)\b[A-Z]:/' + r'Users/(?!<)[^/\s"\'`<>]+'),
        ),
        Pattern(
            "Unix home path",
            re.compile(r'(?i)(?<![\w.])/' + r'home/(?!<)[^/\s"\'`<>]+'),
        ),
        Pattern(
            "macOS user path",
            re.compile(
                r'(?i)(?<![\w.])/'
                + r'Users/(?!(?:<|Shared\b|Guest\b))'
                + r'[^/\s"\'`<>]+'
            ),
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
            ASSIGNED_SECRET_RE,
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
        relative_parent_parts = path.relative_to(root).parent.parts
        if any(part.casefold() in SKIP_DIRS for part in relative_parent_parts):
            continue
        yield path


def scan(path: Path, extra: Sequence[str] = (), quiet: bool = False) -> ScanResult:
    """Scan one file or a directory and return relative finding locations."""

    root = path.resolve()
    patterns = _patterns(extra)
    findings: List[str] = []
    files_scanned = 0
    files_skipped_binary = 0
    errors: List[str] = []

    for file_path in _iter_files(root):
        if root.is_file():
            relative = file_path.name
        else:
            relative = file_path.relative_to(root).as_posix()

        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            files_skipped_binary += 1
            continue

        try:
            data = file_path.read_bytes()
        except OSError:
            errors.append(f"{relative}: [unscannable file: read failed]")
            continue
        text = _decode_text(data)
        if text is None:
            errors.append(f"{relative}: [unscannable file: not UTF-8/UTF-16 text]")
            continue
        if "\x00" in text:
            errors.append(f"{relative}: [unscannable file: anomalous NUL byte]")
            continue
        files_scanned += 1

        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                if pattern.regex.search(line):
                    findings.append(f"{relative}:{line_number}  [{pattern.name}]")

    if not quiet:
        for finding in findings:
            print(finding)

    return ScanResult(
        findings=findings,
        files_scanned=files_scanned,
        files_skipped_binary=files_skipped_binary,
        errors=errors,
    )


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
        dirty_mac_path = "Path: /" + "Users/example-user/private"
        dirty_assigned_secret = '{"API_KEY": "' + "abcdefghijklmnopqrstuvwxyz" + '"}'
        dirty_field_secret = (
            "client_secret=" + "abcdefghijklmnopqrstuvwxyz" + "\n"
            "access_token=" + "abcdefghijklmnopqrstuvwxyz" + "\n"
            "refresh_token=" + "abcdefghijklmnopqrstuvwxyz" + "\n"
            "secret=" + "abcdefghijklmnopqrstuvwxyz"
        )
        dirty_private_ip = "host: " + "192" + ".168" + ".1" + ".10"
        dirty_extra_marker = "marker: ACME-" + "INTERNAL-TOKEN"
        samples: List[Tuple[str, str, Sequence[str], bool, str]] = [
            (
                "clean.md",
                "\n".join(
                    [
                        "# Clean sample",
                        r"Install under C:\Users\<you>\.agent-skills\\",
                        "Install under /Users/<you>/project",
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
                "dirty-mac.md",
                dirty_mac_path,
                (),
                True,
                "macOS user path is caught",
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

        field_secret = root / "config.json"
        field_secret.write_text(dirty_field_secret + "\n", encoding="utf-8")
        field_result = scan(field_secret, quiet=True)
        if len(field_result.findings) < 4:
            print(
                "SELF-TEST FAIL: prefixed secret fields were not all caught "
                f"(findings={len(field_result.findings)})",
                file=sys.stderr,
            )
            ok = False
        else:
            print(
                "SELF-TEST OK: prefixed secret fields are caught "
                f"(findings={len(field_result.findings)})"
            )

        env_local = root / ".env.local"
        env_local.write_text("API_KEY=" + "abcdefghijklmnopqrstuvwxyz" + "\n", encoding="utf-8")
        env_result = scan(env_local, quiet=True)
        if not env_result.findings:
            print("SELF-TEST FAIL: .env.local was not scanned", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: .env.local is scanned")

        pem = root / "server.pem"
        pem.write_text("-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8")
        pem_result = scan(pem, quiet=True)
        if not pem_result.findings:
            print("SELF-TEST FAIL: .pem private key block was not scanned", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: .pem private key block is scanned")

        utf16 = root / "utf16-notes.txt"
        utf16.write_text(
            "password=" + "abcdefghijklmnopqrstuvwxyz" + "\n",
            encoding="utf-16",
        )
        utf16_result = scan(utf16, quiet=True)
        if not utf16_result.findings:
            print("SELF-TEST FAIL: UTF-16 text was not scanned", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: UTF-16 text is scanned")

        utf16_no_bom = root / "utf16-no-bom.txt"
        utf16_no_bom.write_bytes(
            ("password=" + "abcdefghijklmnopqrstuvwxyz").encode("utf-16-le")
        )
        utf16_no_bom_result = scan(utf16_no_bom, quiet=True)
        if not utf16_no_bom_result.findings or utf16_no_bom_result.errors:
            print(
                "SELF-TEST FAIL: unambiguous UTF-16 without BOM was not scanned",
                file=sys.stderr,
            )
            ok = False
        else:
            print("SELF-TEST OK: unambiguous UTF-16 without BOM is scanned")

        utf16_no_bom_emoji = root / "utf16-no-bom-emoji.txt"
        utf16_no_bom_emoji.write_bytes(
            ("password=" + "abcdefghijklmnopqrstuvwxyz" + chr(0x1F512)).encode("utf-16-le")
        )
        utf16_no_bom_emoji_result = scan(utf16_no_bom_emoji, quiet=True)
        if not utf16_no_bom_emoji_result.findings or utf16_no_bom_emoji_result.errors:
            print(
                "SELF-TEST FAIL: UTF-16 without BOM with non-BMP text was not scanned",
                file=sys.stderr,
            )
            ok = False
        else:
            print("SELF-TEST OK: UTF-16 without BOM with non-BMP text is scanned")

        skip_name_dir = root / "skip-name"
        skip_name_dir.mkdir()
        (skip_name_dir / "clean.txt").write_text("clean\n", encoding="utf-8")
        (skip_name_dir / "build").write_text(
            "secret=" + "abcdefghijklmnopqrstuvwxyz" + "\n",
            encoding="utf-8",
        )
        skip_name_result = scan(skip_name_dir, quiet=True)
        if not skip_name_result.findings:
            print(
                "SELF-TEST FAIL: a text file named like a build directory was skipped",
                file=sys.stderr,
            )
            ok = False
        else:
            print("SELF-TEST OK: a text file named build is still scanned")

        binary_dir = root / "binary-only"
        binary_dir.mkdir()
        (binary_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
        binary_result = scan(binary_dir, quiet=True)
        if binary_result.files_scanned != 0 or binary_result.files_skipped_binary != 1:
            print(
                "SELF-TEST FAIL: binary file accounting is wrong "
                f"(scanned={binary_result.files_scanned}, "
                f"skipped={binary_result.files_skipped_binary})",
                file=sys.stderr,
            )
            ok = False
        else:
            print("SELF-TEST OK: known binary files are reported as skipped")

        invalid = root / "invalid.txt"
        invalid.write_bytes(b"\xff\x80not-text")
        invalid_result = scan(invalid, quiet=True)
        if not invalid_result.errors:
            print("SELF-TEST FAIL: invalid text was silently skipped", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: invalid text fails closed")

        invalid_bom = root / "invalid-bom.txt"
        invalid_bom.write_bytes(b"\xef\xbb\xbf\xff")
        invalid_bom_result = scan(invalid_bom, quiet=True)
        if not invalid_bom_result.errors:
            print("SELF-TEST FAIL: invalid UTF-8 after BOM was silently accepted", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: invalid UTF-8 after BOM fails closed")

        nul_text = root / "nul-text.txt"
        nul_text.write_bytes(b"prefix\x00suffix\n")
        nul_result = scan(nul_text, quiet=True)
        if not nul_result.errors:
            print("SELF-TEST FAIL: anomalous NUL text was silently scanned", file=sys.stderr)
            ok = False
        else:
            print("SELF-TEST OK: anomalous NUL text fails closed")

        self_scan = scan(SCRIPT_PATH, quiet=True)
        if self_scan.findings or self_scan.errors:
            print(
                "SELF-TEST FAIL: scanner source contains redaction findings: "
                + ", ".join(self_scan.findings + self_scan.errors),
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
    print(
        f"Scanned {result.files_scanned} file(s); {len(result.findings)} finding(s); "
        f"{result.files_skipped_binary} known binary file(s) skipped."
    )
    if result.errors:
        for error in result.errors:
            print(error, file=sys.stderr)
        print(
            "REDACTION CHECK FAILED: unscannable files were found.",
            file=sys.stderr,
        )
        return 1
    if result.findings:
        print("REDACTION CHECK FAILED: review the findings above.", file=sys.stderr)
        return 1
    if result.files_scanned == 0:
        print(
            "REDACTION CHECK FAILED: no scannable text files were found.",
            file=sys.stderr,
        )
        return 1

    print("REDACTION CHECK PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
