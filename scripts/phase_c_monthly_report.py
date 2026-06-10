#!/usr/bin/env python3
"""Phase C — monthly continuity ecology report (instrumentation-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.ecology.monthly_report import EcologyObservatoryEngine


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase C monthly ecology report (no enforcement)"
    )
    parser.add_argument("--base-dir", default="memory", help="BM memory base directory")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Append current ecology metrics snapshot before report",
    )
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    engine = EcologyObservatoryEngine(args.base_dir)

    snapshot = None
    if args.record:
        snapshot = engine.record_snapshot()

    report = engine.generate_monthly_report().to_dict()
    report["base_dir"] = str(Path(args.base_dir).resolve())
    if snapshot:
        report["snapshot_recorded"] = snapshot

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Phase C — Continuity Ecology Observatory")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
