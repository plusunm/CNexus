#!/usr/bin/env python3
"""CNexus Semantic Safety v4 — semantic firewall CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.semantic_safety.v4 import apply_semantic_firewall, build_semantic_safety_v4_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic Safety v4 firewall")
    parser.add_argument("--text", action="store_true", help="Human-readable summary")
    parser.add_argument("--json-out", help="Write report JSON")
    parser.add_argument("--apply", metavar="REPORT", help="Apply firewall to one JSON file")
    args = parser.parse_args()

    if args.apply:
        payload = json.loads(Path(args.apply).read_text(encoding="utf-8"))
        result = apply_semantic_firewall(payload)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    report = build_semantic_safety_v4_report()
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.text:
        print(report.render_text())
    else:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
