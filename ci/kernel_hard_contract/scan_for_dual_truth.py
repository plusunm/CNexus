#!/usr/bin/env python3
"""Detect dual-truth sources that compete with ExecutionRecord."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DUAL_TRUTH_MARKERS = [
    (ROOT / "core" / "spine" / "query" / "builder_v3.py", "spine query as identity truth"),
    (ROOT / "brain-memory-ui" / "api" / "routes" / "ir.py", "IR replay_strict parallel replay"),
]

FRONTEND_ALT_SOURCES = [
    ROOT / "brain-memory-ui" / "frontend" / "lib" / "spine" / "api.ts",
    ROOT / "brain-memory-ui" / "frontend" / "hooks" / "useSpineStream.ts",
]


def main() -> int:
    warnings: list[str] = []
    for path, label in DUAL_TRUTH_MARKERS:
        if path.exists():
            warnings.append(f"{path.relative_to(ROOT)}: {label}")
    for path in FRONTEND_ALT_SOURCES:
        if path.exists():
            warnings.append(f"{path.relative_to(ROOT)}: alternate UI truth source still present")
    if warnings:
        print("KERNEL CONTRACT: dual-truth WARN (observation layer not fully retired)")
        for w in warnings:
            print(f"  - {w}")
        return 0
    print("KERNEL CONTRACT: dual-truth scan OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
