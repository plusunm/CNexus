#!/usr/bin/env python3
"""CNexus Semantic Safety v3 — adversarial perception attack simulator CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.semantic_safety.v3 import build_semantic_safety_v3_report


def main(*, as_json: bool = True) -> int:
    report = build_semantic_safety_v3_report()
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(report.render_text())
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic Safety v3 attack simulator")
    parser.add_argument("--text", action="store_true", help="Render human-readable summary")
    parser.add_argument("--json-out", help="Write report JSON to path")
    args = parser.parse_args()

    report = build_semantic_safety_v3_report()
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.text:
        print(report.render_text())
    else:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    raise SystemExit(0)
