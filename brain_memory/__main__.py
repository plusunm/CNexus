"""CLI entry: python -m brain_memory"""

import argparse
import json
import sys

from brain_memory import __version__, create_runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cnexus", description="CNexus CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Print full runtime status (JSON)")
    status_p.add_argument("--root", default=".", help="Project root directory")

    gov = sub.add_parser("governance", help="Run one stability governance cycle")
    gov.add_argument("--root", default=".", help="Project root directory")
    gov.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)
    runtime = create_runtime(project_root=args.root)

    if args.command == "status":
        print(json.dumps(runtime.get_full_status(), ensure_ascii=False, indent=2, default=str))
    elif args.command == "governance":
        report = runtime.run_governance_cycle()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        else:
            score = report["stability_metrics"]["overall_stability_score"]
            print(f"CNexus v{__version__} — stability score: {score:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
