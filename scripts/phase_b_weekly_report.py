#!/usr/bin/env python3
"""Phase B — weekly longitudinal reality-coupling report (instrumentation-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.singularity.longitudinal_report import LongitudinalStudyEngine


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase B weekly longitudinal report (no enforcement)"
    )
    parser.add_argument("--base-dir", default="memory", help="BM memory base directory")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Append current singularity metrics snapshot before report",
    )
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    engine = LongitudinalStudyEngine(args.base_dir)

    snapshot = None
    if args.record:
        snapshot = engine.record_snapshot()

    report = engine.generate_weekly_report().to_dict()
    report["base_dir"] = str(Path(args.base_dir).resolve())
    if snapshot:
        report["snapshot_recorded"] = snapshot

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Phase B — Longitudinal Reality-Coupling Study")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
