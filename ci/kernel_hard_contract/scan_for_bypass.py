#!/usr/bin/env python3
"""Scan API routes for forbidden runtime execution bypass paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = [
    ROOT / "brain-memory-ui" / "api" / "routes",
    ROOT / "api",
]

FORBIDDEN = [
    (r"get_runtime\(\)\.(?:capture|recall|process_interaction|run_governance_cycle|trait_based_reflection|run_memory_maintenance|run_validation_suite|process_capture_cognition)", "direct runtime mutation"),
    (r"runtime\.(?:capture|recall|process_interaction|run_governance_cycle|trait_based_reflection|run_memory_maintenance|run_validation_suite|process_capture_cognition)\s*\(", "runtime variable mutation"),
]

ALLOWLIST = {
    ROOT / "brain-memory-ui" / "api" / "routes" / "memory.py": {r"get_runtime\(\)"},  # embedder config only
}


def main() -> int:
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            allowed = ALLOWLIST.get(path, set())
            for pattern, label in FORBIDDEN:
                for match in re.finditer(pattern, source):
                    if any(re.search(a, match.group(0)) for a in allowed):
                        continue
                    violations.append(f"{path.relative_to(ROOT)}: {label}: {match.group(0)}")
    if violations:
        print("KERNEL CONTRACT: bypass scan FAILED")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("KERNEL CONTRACT: bypass scan OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
