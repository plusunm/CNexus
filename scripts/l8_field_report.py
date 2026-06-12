#!/usr/bin/env python3
"""CNexus L8 — unified collapse & governance kernel CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.l8 import L8_CONSTRAINTS, build_l8_report


def main() -> int:
    parser = argparse.ArgumentParser(description="L8 unified kernel (observational tensor projection)")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    parser.add_argument("--text", action="store_true", help="Human-readable summary")
    parser.add_argument("--json-out", help="Write report JSON to path")
    parser.add_argument("--jsonl-out", help="Append one JSONL record to path")
    parser.add_argument("--base-dir", help="Observability base dir for L2/L3 coupling")
    parser.add_argument("--l2-coupling", action="store_true", help="Enable L2 coupling when base-dir set")
    args = parser.parse_args()

    report = build_l8_report(
        base_dir=args.base_dir,
        use_l2_coupling=args.l2_coupling,
    )

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(report.export_json() + "\n", encoding="utf-8")

    if args.jsonl_out:
        Path(args.jsonl_out).parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "layer": "L8",
            "constraints": L8_CONSTRAINTS,
            **report.to_dict(),
        }
        with Path(args.jsonl_out).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    if args.text or (not args.json and not args.json_out and not args.jsonl_out):
        print(report.render_text())
    elif args.json:
        print(report.export_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
