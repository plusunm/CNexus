#!/usr/bin/env python3
"""CNexus Observation P2 — external runtime ingest (file_tail / jsonl_push / metrics)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.observation import FileTailAdapter, JsonlPushAdapter, MetricsScrapeAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Observation P2 external ingest (append-only)")
    parser.add_argument("--base-dir", required=True, help="BM_MEMORY_DIR")
    sub = parser.add_subparsers(dest="mode", required=True)

    tail = sub.add_parser("file-tail", help="Tail external log/jsonl file")
    tail.add_argument("--path", required=True, help="External file to tail")

    push = sub.add_parser("jsonl-push", help="Push JSONL file into observation bus")
    push.add_argument("--path", required=True, help="JSONL file to ingest")

    metrics = sub.add_parser("metrics", help="Scrape metrics JSON file or URL")
    metrics.add_argument("--file", help="Local metrics JSON file")
    metrics.add_argument("--url", help="HTTP metrics endpoint")

    args = parser.parse_args()
    base = args.base_dir

    if args.mode == "file-tail":
        result = FileTailAdapter(base).poll(args.path)
    elif args.mode == "jsonl-push":
        result = JsonlPushAdapter(base).push_file(args.path)
    else:
        adapter = MetricsScrapeAdapter(base)
        if args.file:
            result = adapter.scrape_json_file(args.file)
        elif args.url:
            result = adapter.scrape_url(args.url)
        else:
            parser.error("metrics mode requires --file or --url")
            return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("error") is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
