#!/usr/bin/env python3
"""Scan repository for forbidden direct memory write paths (P0-1c)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    re.compile(r"\.memory_manager\.capture_interaction\s*\("),
    re.compile(r"\.memory_manager\.capture_memory\s*\("),
    re.compile(r"\.memory_manager\.create_block\s*\("),
    re.compile(r"\.memory_manager\.update_block\s*\("),
    re.compile(r"\.storage\.capture_memory\s*\("),
]

ALLOWLIST_SUBSTRINGS = [
    "memory/manager.py",
    "storage/manager.py",
    "brain_memory/runtime.py",
    "tests/",
    "scripts/check_write_paths.py",
    "_tmp_cnexus1_compare",
    "experimental/",
    "dist/",
]

SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "web", "dist"}


def is_allowlisted(path: Path) -> bool:
    rel = path.as_posix()
    return any(token in rel for token in ALLOWLIST_SUBSTRINGS)


def scan() -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if is_allowlisted(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    violations.append((path.relative_to(ROOT).as_posix(), idx, line.strip()))
    return violations


def main() -> int:
    violations = scan()
    if not violations:
        print("check_write_paths: OK — no forbidden direct memory writes found.")
        return 0
    print("check_write_paths: FAILED — forbidden direct memory writes:")
    for path, line_no, line in violations:
        print(f"  {path}:{line_no}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
