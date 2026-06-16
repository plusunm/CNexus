#!/usr/bin/env python3
"""Run CP-1.5 acceptance gates G1–G5 and print JSON report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.governance.gtbs.cp15_gates import run_cp15_gates


def main() -> int:
    parser = argparse.ArgumentParser(description="CP-1.5 gate report (G1–G5)")
    parser.add_argument(
        "--base-dir",
        default=os.environ.get("BM_MEMORY_DIR", str(ROOT)),
        help="Directory containing observability/gtbs_transactions.jsonl",
    )
    args = parser.parse_args()
    report = run_cp15_gates(base_dir=Path(args.base_dir))
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
