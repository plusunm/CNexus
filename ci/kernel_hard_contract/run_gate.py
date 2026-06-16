#!/usr/bin/env python3
"""Run all kernel hard contract gates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

SCANNERS = [
    HERE / "scan_for_bypass.py",
    HERE / "scan_for_dual_truth.py",
]


def main() -> int:
    failed = 0
    for scanner in SCANNERS:
        proc = subprocess.run([sys.executable, str(scanner)], cwd=ROOT, check=False)
        if proc.returncode != 0:
            failed += 1
    if failed:
        print(f"KERNEL CONTRACT GATE: {failed} scanner(s) failed")
        return 1
    print("KERNEL CONTRACT GATE: all scanners passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
