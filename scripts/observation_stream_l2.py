#!/usr/bin/env python3
"""CNexus Streaming L2 — rolling window over Observation Bus + legacy streams."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.observation import build_streaming_l2_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Streaming L2 rolling window (read-only)")
    parser.add_argument("--base-dir", required=True, help="BM_MEMORY_DIR")
    parser.add_argument("--window-minutes", type=int, default=60)
    parser.add_argument("--poll", action="store_true", help="Advance tail offset before build")
    parser.add_argument("--watch", action="store_true", help="Poll every N seconds")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval seconds")
    parser.add_argument("--text", action="store_true", help="Human-readable output")
    parser.add_argument("--json-out", help="Write report JSON")
    args = parser.parse_args()

    def run_once() -> dict:
        report = build_streaming_l2_report(
            args.base_dir,
            window_minutes=args.window_minutes,
            poll_new=args.poll or args.watch,
        )
        return report.to_dict()

    if args.watch:
        try:
            while True:
                payload = run_once()
                if args.text:
                    from core.observation.l2_streaming import StreamingL2Window

                    r = StreamingL2Window(args.base_dir, window_minutes=args.window_minutes).build(poll_new=True)
                    print(r.render_text())
                    print("---")
                else:
                    print(json.dumps(payload, ensure_ascii=False))
                time.sleep(max(5, args.interval))
        except KeyboardInterrupt:
            return 0

    payload = run_once()
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.text:
        from core.observation.l2_streaming import StreamingL2Window

        print(StreamingL2Window(args.base_dir, window_minutes=args.window_minutes).build(poll_new=args.poll).render_text())
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
