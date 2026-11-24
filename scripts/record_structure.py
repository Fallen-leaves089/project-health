#!/usr/bin/env python3
"""Validate or append a structured structural-experience entry.

The recorder is fail-closed and uses ``structure-schema.json`` as the single
source for chapters, statuses, injection levels, branch grammar, relation
types, and required fields.

It controls storage only. It does not decide whether an experience matches,
adjudicate conflicts, establish technical truth, modify PITFALLS, or reuse an
old ID. Writes use an OS file lock and same-directory atomic replacement.

Exit codes:
    0 = check passed, entry appended, duplicate, or dry-run
    1 = validation, safety, or write error
    2 = usage error
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parent.parent
SCHEMA_PATH = SCRIPT_PATH.parent / "structure-schema.json"
SCANNER_PATH = SCRIPT_PATH.parent / "check_redaction.py"
LOCAL_NAME = "STRUCTURE.local.md"
REPO_NAME = "references/structural-experience.md"
PITFALLS_NAME = "PITFALLS.md"
SKILL_NAME = "project-health"
SKILL_LICENSE = "PolyForm-Noncommercial-1.0.0"
REQUIRED_ROOT_FILES = (
    "SKILL.md",
    "AGENTS.md",
    "PITFALLS.md",
    "references/report-template.md",
    "references/structural-experience.md",
    "references/structural-experience.en.md",
    "scripts/record_structure.py",
    "scripts/structure-schema.json",
)
ID_RE = re.compile(r"^S-([A-F])-(\d{3})$")


def load_schema(path: Path = SCHEMA_PATH) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not load structure schema: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported structure schema version")
    return data


SCHEMA = load_schema()
CHAPTER_IDS: List[str] = list(SCHEMA["chapter_ids"])
CHAPTER_LABELS: Dict[str, Dict[str, str]] = {
    "zh": dict(SCHEMA["chapter_labels_zh"]),
    "en": dict(SCHEMA["chapter_labels_en"]),
}
STATUS_BY_LABEL: Dict[str, str] = {}
STATUS_DEFAULTS: Dict[str, str] = {}
STATUS_ALLOWED: Dict[str, set[str]] = {}
INJECTION_BY_LABEL: Dict[str, str] = {}
STATUS_LABELS: Dict[str, Tuple[str, str]] = {}
INJECTION_LABELS: Dict[str, Tuple[str, str]] = {}

for status_key in SCHEMA["status_keys"]:
    labels = tuple(str(label) for label in SCHEMA["status_labels"][status_key])
    if len(labels) < 2:
        raise ValueError(f"status {status_key} needs Chinese and English labels")
    STATUS_LABELS[status_key] = (labels[0], labels[1])
    STATUS_DEFAULTS[status_key] = str(SCHEMA["status_defaults"][status_key])
    STATUS_ALLOWED[status_key] = set(
        SCHEMA["status_allowed_injections"][status_key]
    )
    for label in labels:
        STATUS_BY_LABEL[label.casefold()] = status_key

for injection_key in SCHEMA["injection_keys"]:
    labels = tuple(str(label) for label in SCHEMA["injection_labels"][injection_key])
    if len(labels) < 2:
        raise ValueError(f"injection {injection_key} needs Chinese and English labels")
    INJECTION_LABELS[injection_key] = (labels[0], labels[1])
    for label in labels:
        INJECTION_BY_LABEL[label.casefold()] = injection_key

BRANCH_SEGMENT_RE = re.compile(str(SCHEMA["branch_segment_pattern"]))
RELATION_TARGET_RE = re.compile(str(SCHEMA["relation_target_pattern"]))
PITFALL_ID_RE = re.compile(str(SCHEMA["pitfall_id_pattern"]))
FIELD_LIMIT = int(SCHEMA["field_limit"])
RELATION_LIMIT = int(SCHEMA["relation_max_length"])
RELATION_SEPARATOR = str(SCHEMA["relation_separator"])
RELATION_TYPES = {str(item) for item in SCHEMA["relation_types"]}


@dataclass(frozen=True)
class Entry:
    chapter: str
    primary_branch: str
    related_branches: str
    status: str
    injection: str
    trigger: str
    mechanism: str
    boundary: str
    verification: str
    pitfalls: str
    region_links: str
    language: str = "zh"


@dataclass(frozen=True)
class CheckResult:
    path: Path
    entry_count: int
    missing: bool = False


@dataclass(frozen=True)
class RecordResult:
    status: str
    path: Path
    entry_id: Optional[str] = None
    line: Optional[str] = None


def _load_scanner() -> Any:
    spec = importlib.util.spec_from_file_location("structure_redaction_scanner", SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load redaction scanner: {SCANNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCANNER = _load_scanner()


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass


def _read_frontmatter(path: Path) -> Dict[str, str]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path.name} must be UTF-8 without BOM")
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not valid UTF-8") from exc
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path.name} is missing YAML frontmatter")

    fields: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    raise ValueError(f"{path.name} frontmatter is not closed")


def _validate_skill_root(root: Path) -> None:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    for relative in REQUIRED_ROOT_FILES:
        if not (root / relative).is_file():
            raise ValueError(f"root is missing structural file: {relative}")

    fields = _read_frontmatter(root / "SKILL.md")
    if fields.get("name") != SKILL_NAME:
        raise ValueError("SKILL.md name is not project-health")
    if fields.get("license") != SKILL_LICENSE:
        raise ValueError("SKILL.md license is not the expected project-health license")
    if not fields.get("description", "").strip():
        raise ValueError("SKILL.md is missing a non-empty description")

    if (root / "scripts" / "record_structure.py").read_bytes() != SCRIPT_PATH.read_bytes():
        raise ValueError("root structural recorder does not match this recorder")
    if (root / "scripts" / "structure-schema.json").read_bytes() != SCHEMA_PATH.read_bytes():
        raise ValueError("root structure schema does not match this package")


def _manual_path(root: Path, scope: str, for_write: bool) -> Path:
    root = root.expanduser().resolve()
    _validate_skill_root(root)

    if scope == "auto":
        if (root / LOCAL_NAME).is_file() or not (root / ".git").exists():
            scope = "local"
        else:
            scope = "repo"
    if scope not in {"repo", "local"}:
        raise ValueError("scope must be auto, repo, or local")
    if scope == "repo" and for_write and not (root / ".git").exists():
        raise ValueError("repository scope requires a .git entry at the skill root")

    path = root / (LOCAL_NAME if scope == "local" else REPO_NAME)
    if path.resolve(strict=False).parent not in {
        root,
        (root / "references").resolve(),
    }:
        raise ValueError("refusing to write outside the expected skill paths")
    if scope == "repo" and not path.is_file():
        raise ValueError(f"repository structure manual does not exist: {path}")
    return path


def _clean_field(name: str, raw: str, limit: int = FIELD_LIMIT) -> str:
    text = " ".join((raw or "").split())
    if not text:
        raise ValueError(f"{name} must not be empty")
    if "|" in text:
        raise ValueError(f"{name} must not contain the '|' separator")
    if len(text) > limit:
        raise ValueError(f"{name} is longer than {limit} characters")
    return text


def _canonical_status(raw: str) -> str:
    key = STATUS_BY_LABEL.get((raw or "").strip().casefold())
    if key is None:
        raise ValueError(f"unknown structural status: {raw}")
    return key


def _canonical_injection(raw: Optional[str], status: str) -> str:
    if raw is None or not raw.strip():
        return STATUS_DEFAULTS[status]
    key = INJECTION_BY_LABEL.get(raw.strip().casefold())
    if key is None:
        raise ValueError(f"unknown injection level: {raw}")
    if key not in STATUS_ALLOWED[status]:
        raise ValueError(f"injection {key} is not allowed for status {status}")
    return key


def _label(mapping: Dict[str, Tuple[str, str]], key: str, language: str) -> str:
    labels = mapping[key]
    return labels[1] if language == "en" else labels[0]


def _validate_branch(branch: str, expected_chapter: Optional[str] = None) -> str:
    text = (branch or "").strip()
    parts = text.split("/")
    if len(parts) < 2 or parts[0] not in CHAPTER_IDS:
        raise ValueError(f"invalid structural branch: {branch}")
    if expected_chapter is not None and parts[0] != expected_chapter:
        raise ValueError("primary branch chapter must match --chapter")
    if any(BRANCH_SEGMENT_RE.fullmatch(part) is None for part in parts[1:]):
        raise ValueError(f"invalid branch segment in: {branch}")
    return "/".join(parts)


def _canonical_related_branches(raw: str) -> str:
    text = (raw or "").strip()
    if not text or text.casefold() in {"none", "无"}:
        return ""
    branches: List[str] = []
    for item in text.replace(",", ";").split(";"):
        candidate = item.strip()
        if not candidate:
            continue
        branches.append(_validate_branch(candidate))
    if len(branches) != len(set(branches)):
        raise ValueError("related branches contain duplicates")
    return RELATION_SEPARATOR.join(branches)


def _canonical_region_links(raw: str) -> str:
    text = " ".join((raw or "").split())
    if len(text) > RELATION_LIMIT:
        raise ValueError(f"region links are longer than {RELATION_LIMIT} characters")
    if not text or text.casefold() in {"none", "无"}:
        return "none"
    parts: List[str] = []
    for item in text.split(";"):
        candidate = item.strip()
        if not candidate:
            continue
        if ":" not in candidate:
            raise ValueError("each region link must use relation-type:ID")
        relation, target = candidate.split(":", 1)
        relation = relation.strip()
        target = target.strip()
        if relation not in RELATION_TYPES or relation == "none":
            raise ValueError(f"unknown region relation type: {relation}")
        if RELATION_TARGET_RE.fullmatch(target) is None:
            raise ValueError(f"invalid region link target: {target}")
        parts.append(f"{relation}:{target}")
    if not parts:
        return "none"
    if len(parts) != len(set(parts)):
        raise ValueError("region links contain duplicates")
    return RELATION_SEPARATOR.join(parts)


def _pitfall_ids(root: Path) -> set[str]:
    path = root / PITFALLS_NAME
    text = path.read_text(encoding="utf-8")
    return set(PITFALL_ID_RE.findall(text))


def _canonical_pitfalls(raw: str, root: Path) -> str:
    values = [item.strip().upper() for item in (raw or "").split(",") if item.strip()]
    if not values:
        raise ValueError("at least one related PITFALLS ID is required")
    if len(values) != len(set(values)):
        raise ValueError("PITFALLS IDs contain duplicates")
    for value in values:
        if PITFALL_ID_RE.fullmatch(value) is None:
            raise ValueError(f"invalid PITFALLS ID: {value}")
    known = _pitfall_ids(root)
    missing = [value for value in values if value not in known]
    if missing:
        raise ValueError(f"unknown PITFALLS ID: {', '.join(missing)}")
    return ", ".join(values)


def _scan_text(text: str) -> None:
    with tempfile.TemporaryDirectory(prefix="structure-redaction-") as temp_dir:
        path = Path(temp_dir) / "entry.md"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
        result = SCANNER.scan(path, quiet=True)
    problems = list(result.findings) + list(result.errors)
    if problems:
        raise ValueError("entry failed redaction scan: " + "; ".join(problems))


def build_entry(entry: Entry, entry_id: str, root: Path) -> Tuple[str, str]:
    id_match = ID_RE.fullmatch(entry_id)
    if id_match is None or id_match.group(1) != entry.chapter:
        raise ValueError("entry ID chapter must match the selected chapter")
    status = _canonical_status(entry.status)
    injection = _canonical_injection(entry.injection, status)
    primary_branch = _validate_branch(entry.primary_branch, entry.chapter)
    related = _canonical_related_branches(entry.related_branches)
    trigger = _clean_field("trigger", entry.trigger)
    mechanism = _clean_field("mechanism", entry.mechanism)
    boundary = _clean_field("boundary", entry.boundary)
    verification = _clean_field("verification", entry.verification)
    pitfalls = _canonical_pitfalls(entry.pitfalls, root)
    region_links = _canonical_region_links(entry.region_links)

    line = (
        f"- {entry_id} | {_label(STATUS_LABELS, status, entry.language)} | "
        f"{_label(INJECTION_LABELS, injection, entry.language)} | "
        f"{primary_branch} | {related or ('none' if entry.language == 'en' else '无')} | "
        f"{trigger} | {mechanism} | {boundary} | {verification} | {pitfalls}"
    )
    prefix = "- Region links:" if entry.language == "en" else "- 区域关联："
    display_links = (
        "none"
        if entry.language == "en" and region_links == "none"
        else "无"
        if entry.language == "zh" and region_links == "none"
        else region_links
    )
    note = f"  {prefix} {display_links}"
    _scan_text(line + "\n" + note)
    return line, note


def _parse_entry_line(
    line: str,
    current_chapter: Optional[str],
    root: Path,
    language: str,
) -> Tuple[str, Entry]:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) != 10:
        raise ValueError(f"entry must contain exactly 10 fields: {line}")
    id_field, status_raw, injection_raw, primary_branch, related, trigger, mechanism, boundary, verification, pitfalls = parts
    id_match = ID_RE.fullmatch(id_field.removeprefix("- "))
    if id_match is None:
        raise ValueError(f"invalid structural entry ID: {id_field}")
    entry_id = id_match.group(0)
    chapter = id_match.group(1)
    if current_chapter is not None and chapter != current_chapter:
        raise ValueError(f"{entry_id} is outside chapter {current_chapter}")
    trigger = _clean_field("trigger", trigger)
    mechanism = _clean_field("mechanism", mechanism)
    boundary = _clean_field("boundary", boundary)
    verification = _clean_field("verification", verification)
    entry = Entry(
        chapter=chapter,
        primary_branch=_validate_branch(primary_branch, chapter),
        related_branches=related,
        status=status_raw,
        injection=injection_raw,
        trigger=trigger,
        mechanism=mechanism,
        boundary=boundary,
        verification=verification,
        pitfalls=pitfalls,
        region_links="none",
        language=language,
    )
    _canonical_status(entry.status)
    _canonical_injection(entry.injection, _canonical_status(entry.status))
    _canonical_related_branches(entry.related_branches)
    _canonical_pitfalls(entry.pitfalls, root)
    return entry_id, entry


def _chapter_headings(language: str = "zh") -> Dict[str, str]:
    return {
        chapter: f"### {chapter}. {CHAPTER_LABELS[language][chapter]}"
        for chapter in CHAPTER_IDS
    }


def check_manual(path: Path, root: Path, missing_ok: bool = False) -> CheckResult:
    _validate_skill_root(root)
    if not path.is_file():
        if missing_ok:
            return CheckResult(path=path, entry_count=0, missing=True)
        raise ValueError(f"structure manual does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("structure manual must not be empty")
    version_line = f"schema-version: {SCHEMA['schema_version']}"
    if version_line not in text.splitlines():
        raise ValueError(f"structure manual must declare {version_line}")
    language = "en" if path.name.endswith(".en.md") else "zh"
    headings = _chapter_headings(language)
    for chapter, heading in headings.items():
        if heading not in text:
            raise ValueError(f"structure manual is missing chapter {chapter}")
    _scan_text(text)

    current_chapter: Optional[str] = None
    seen_ids: set[str] = set()
    seen_signatures: set[Tuple[str, str, str]] = set()
    entry_count = 0
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading_match = re.match(r"^### ([A-F])\.", line)
        if heading_match is not None:
            current_chapter = heading_match.group(1)
            continue
        if not line.startswith("- S-"):
            continue
        if current_chapter is None:
            raise ValueError(f"structural entry outside a chapter: {line}")
        entry_id, entry = _parse_entry_line(line, current_chapter, root, language)
        if entry_id in seen_ids:
            raise ValueError(f"duplicate structural entry ID: {entry_id}")
        seen_ids.add(entry_id)
        signature = (
            entry.primary_branch.casefold(),
            " ".join(entry.trigger.split()).casefold(),
            " ".join(entry.mechanism.split()).casefold(),
        )
        if signature in seen_signatures:
            raise ValueError(f"duplicate structural mechanism: {entry_id}")
        seen_signatures.add(signature)

        note = ""
        for candidate in lines[index + 1 : index + 4]:
            if candidate.strip():
                note = candidate.strip()
                break
        if not note.startswith(("- 区域关联：", "- Region links:")):
            raise ValueError(f"{entry_id} is missing its region-link note")
        if "：" in note:
            relation_text = note.split("：", 1)[1].strip()
        elif ":" in note:
            relation_text = note.split(":", 1)[1].strip()
        else:
            relation_text = ""
        if not relation_text:
            raise ValueError(f"{entry_id} has an empty region-link note")
        _canonical_region_links(relation_text)
        entry_count += 1
    return CheckResult(path=path, entry_count=entry_count)


def _local_header() -> str:
    lines = [
        "# 结构经验手册 / Structural Experience Manual",
        "",
        f"schema-version: {SCHEMA['schema_version']}",
        "状态：只记录实际遇到并核实可复用的结构经验；零条是正常状态。",
        "",
    ]
    for chapter, heading in _chapter_headings("zh").items():
        lines.extend([heading, "", "<!-- 没有经验时保持空白。 -->", ""])
    return "\n".join(lines)


def _read_existing(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"refusing to write to a UTF-8 BOM file: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"structure manual is not valid UTF-8: {path}") from exc


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    lock_path = path.parent / "STRUCTURE.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_write(path: Path, text: str) -> None:
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _next_id(text: str, chapter: str) -> str:
    highest = 0
    for match in re.finditer(rf"(?m)^- S-{chapter}-(\d{{3}}) \|", text):
        highest = max(highest, int(match.group(1)))
    if highest >= 999:
        raise ValueError(f"chapter {chapter} has exhausted its structural entry IDs")
    return f"S-{chapter}-{highest + 1:03d}"


def _insert_entry(text: str, chapter: str, block: str, language: str) -> str:
    heading = _chapter_headings(language)[chapter]
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"structure manual is missing chapter {chapter}")
    section_start = start + len(heading)
    next_match = re.search(r"(?m)^### [A-F]\. ", text[section_start:])
    section_end = section_start + next_match.start() if next_match else len(text)
    section = text[section_start:section_end].rstrip()
    replacement = section + "\n\n" + block + "\n\n"
    return text[:section_start] + replacement + text[section_end:]


def record(
    root: Path,
    entry: Entry,
    scope: str = "auto",
    dry_run: bool = False,
) -> RecordResult:
    root = root.expanduser().resolve()
    path = _manual_path(root, scope, for_write=True)
    with _file_lock(path):
        existing = _read_existing(path)
        if not existing:
            existing = _local_header()
        check_manual_text(existing, path, root)
        entry_id = _next_id(existing, entry.chapter)
        line, note = build_entry(entry, entry_id, root)
        updated = _insert_entry(existing, entry.chapter, line + "\n" + note, entry.language)
        if not existing.endswith("\n"):
            updated = updated.rstrip() + "\n"
        check_manual_text(updated, path, root)
        if dry_run:
            return RecordResult(status="dry-run", path=path, entry_id=entry_id, line=line + "\n" + note)
        _atomic_write(path, updated)
        check_manual(path, root)
    return RecordResult(status="appended", path=path, entry_id=entry_id)


def check_manual_text(text: str, path: Path, root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="structure-check-") as temp_dir:
        candidate = Path(temp_dir) / path.name
        with candidate.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        check_manual(candidate, root)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate a structure manual")
    mode.add_argument("--add", action="store_true", help="append a validated entry")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="skill root")
    parser.add_argument("--scope", choices=("auto", "repo", "local"), default="auto")
    parser.add_argument("--path", type=Path, help="manual path for --check")
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    parser.add_argument("--chapter", choices=tuple(CHAPTER_IDS), help="primary chapter")
    parser.add_argument("--branch", help="primary logical branch")
    parser.add_argument("--related-branches", default="", help="semicolon-separated branches")
    parser.add_argument("--status", default="待验证", help="entry status")
    parser.add_argument("--injection", help="soft, brief, or detailed; defaults by status")
    parser.add_argument("--trigger", help="when the structural risk appears")
    parser.add_argument("--mechanism", help="the reusable structural mechanism")
    parser.add_argument("--boundary", help="boundary or counterexample")
    parser.add_argument("--verify", help="verification hook")
    parser.add_argument("--pitfalls", help="comma-separated related PITFALLS IDs")
    parser.add_argument("--region-links", default="", help="relation-type:ID; relation-type:ID")
    parser.add_argument("--dry-run", action="store_true", help="validate and print without writing")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configure_stdio()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        root = args.root.expanduser().resolve()
        if args.check:
            path = args.path.expanduser().resolve() if args.path else _manual_path(root, args.scope, for_write=False)
            missing_ok = args.scope == "local" and args.path is None
            result = check_manual(path, root, missing_ok=missing_ok)
            if result.missing:
                print(f"OK: no local structure manual yet: {result.path}")
            else:
                print(f"CHECK PASSED: {result.entry_count} entry/entries in {result.path}")
            return 0

        required = {
            "--chapter": args.chapter,
            "--branch": args.branch,
            "--trigger": args.trigger,
            "--mechanism": args.mechanism,
            "--boundary": args.boundary,
            "--verify": args.verify,
            "--pitfalls": args.pitfalls,
        }
        missing = [name for name, value in required.items() if value is None or not str(value).strip()]
        if missing:
            raise ValueError("missing required add fields: " + ", ".join(missing))
        entry = Entry(
            chapter=str(args.chapter),
            primary_branch=str(args.branch),
            related_branches=args.related_branches,
            status=args.status,
            injection=args.injection,
            trigger=args.trigger,
            mechanism=args.mechanism,
            boundary=args.boundary,
            verification=args.verify,
            pitfalls=args.pitfalls,
            region_links=args.region_links,
            language=args.language,
        )
        result = record(root, entry, scope=args.scope, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: could not write structure memory: {exc}", file=sys.stderr)
        return 1

    print(f"{result.status.upper()}: {result.path}")
    if result.entry_id:
        print(f"ENTRY: {result.entry_id}")
    if result.line:
        print(result.line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
