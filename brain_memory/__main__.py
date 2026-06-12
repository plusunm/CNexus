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

    interact_p = sub.add_parser("interact", help="Run one interaction")
    interact_p.add_argument("--root", default=".", help="Project root directory")
    interact_p.add_argument("--user-id", required=True, help="User identifier")
    interact_p.add_argument("--session-id", default=None, help="Session identifier")
    interact_p.add_argument("message", nargs="+", help="User message")

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
    elif args.command == "interact":
        message = " ".join(args.message)
        metadata = {"session_id": args.session_id} if args.session_id else {}
        result = runtime.process_interaction(
            message,
            user_id=args.user_id,
            metadata=metadata,
            use_memory=True,
        )
        attention = result.get("attention_state") or runtime._interaction_attention_state()
        blocks_used = []
        if result.get("emotion_state"):
            blocks_used.append("emotion")
        if result.get("active_intent"):
            blocks_used.append("intent")
        if result.get("ok", True):
            blocks_used.extend(["persona", "working_memory", "attention_state"])
        trace_id = result.get("capture_id") or result.get("grounding_event_id") or ""
        payload = {
            "response": result.get("reply") or result.get("response") or "",
            "provenance": {
                "trace_id": trace_id,
                "blocks_used": sorted(set(blocks_used)),
                "governance": {
                    "values_check": "passed" if result.get("ok", True) else "revised",
                    "cdg_intercept": bool(result.get("cdg")) and not (result.get("cdg") or {}).get(
                        "approved", True
                    ),
                    "revision_note": result.get("reason"),
                },
            },
            "attention_state": attention,
            "reflection_triggered": bool(result.get("reflection_triggered")),
            "user_id": args.user_id,
            "session_id": args.session_id,
            "governance_pass": bool(result.get("ok", True)),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
