#!/usr/bin/env python3
"""Phase A — full divergence landscape report (instrumentation-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.phase_a.landscape import PhaseALandscapeMapper


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A divergence landscape report")
    parser.add_argument("--base-dir", default="memory", help="BM memory base directory")
    parser.add_argument("--no-anchors", action="store_true", help="Skip frozen anchor recording")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    runtime_state = None
    try:
        from brain_memory import create_runtime

        runtime = create_runtime(base_dir=args.base_dir, config_path="config/default.json")
        runtime_state = runtime.get_current_state()
    except Exception:
        runtime_state = None

    report = PhaseALandscapeMapper(args.base_dir).generate(
        runtime_state=runtime_state,
        record_anchors=not args.no_anchors,
    )
    payload = report.to_dict()
    payload["base_dir"] = str(Path(args.base_dir).resolve())

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("Phase A — Divergence Landscape Mapping")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
