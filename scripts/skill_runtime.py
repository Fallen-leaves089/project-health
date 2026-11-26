#!/usr/bin/env python3
"""Shared runtime primitives for Project Health memory tools."""

from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, Iterator


def read_frontmatter(path: Path) -> Dict[str, str]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path.name} must be UTF-8 without BOM: {path}")
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path.name} is not valid UTF-8: {path}") from exc
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


def validate_skill_root(
    root: Path,
    expected_name: str,
    expected_license: str,
    required_files: Iterable[str],
) -> Dict[str, str]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    skill = root / "SKILL.md"
    if not skill.is_file():
        raise ValueError("root does not contain SKILL.md")

    fields = read_frontmatter(skill)
    if fields.get("name") != expected_name:
        raise ValueError(f"SKILL.md name is not {expected_name}")
    if fields.get("license") != expected_license:
        raise ValueError(f"SKILL.md license is not {expected_license}")
    if not fields.get("description", "").strip():
        raise ValueError("SKILL.md is missing a non-empty description")

    for relative in required_files:
        if not (root / relative).is_file():
            raise ValueError(f"root is missing structural file: {relative}")
    return fields


def resolve_memory_path(
    root: Path,
    scope: str,
    local_relative: str,
    repository_relative: str,
) -> Path:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    local = root / local_relative
    repository = root / repository_relative

    if scope == "auto":
        if local.is_file() or root.parent.name.casefold() == "skills":
            scope = "local"
        elif (root / ".git").exists():
            scope = "repo"
        else:
            scope = "local"
    if scope not in {"repo", "local"}:
        raise ValueError("scope must be auto, repo, or local")
    if scope == "repo" and not (root / ".git").exists():
        raise ValueError("repository scope requires a .git entry at the skill root")

    path = local if scope == "local" else repository
    resolved = path.resolve(strict=False)
    if root not in resolved.parents:
        raise ValueError("refusing to write outside the skill root")
    if scope == "repo" and not path.is_file():
        raise ValueError(f"repository memory does not exist: {path}")
    return path


def read_existing_utf8(path: Path, bom_message: str) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{bom_message}: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"memory file is not valid UTF-8: {path}") from exc


@contextmanager
def file_lock(path: Path, lock_name: str) -> Iterator[None]:
    lock_path = path.parent / lock_name
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


def write_text_atomic(path: Path, text: str) -> None:
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


def create_text_exclusive(path: Path, text: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return


def append_text(path: Path, existing: str, text: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass
