"""Import Cursor agent transcript JSONL into CNexus."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain_memory import create_runtime  # noqa: E402

USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
SKIP_PATTERNS = (
    "Briefly inform the user about the task result",
    "<system_notification>",
    "The user has switched",
)


def extract_user_text(raw: str) -> str | None:
    if any(p in raw for p in SKIP_PATTERNS):
        return None
    m = USER_QUERY_RE.search(raw)
    text = (m.group(1) if m else raw).strip()
    if len(text) < 4:
        return None
    return text[:4000]


def extract_assistant_text(raw: str) -> str | None:
    if not raw or len(raw.strip()) < 20:
        return None
    # Skip huge tool-heavy dumps; keep summary-like replies
    if raw.count("tool_call") > 3:
        return None
    return raw.strip()[:6000]


def parse_transcript(path: Path) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    pending_user: str | None = None

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = obj.get("role")
            content = obj.get("message", {}).get("content", [])
            texts = [
                c.get("text", "")
                for c in content
                if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
            ]
            if not texts:
                continue
            raw = "\n".join(texts)

            if role == "user":
                text = extract_user_text(raw)
                if text:
                    pending_user = text
            elif role == "assistant" and pending_user:
                reply = extract_assistant_text(raw)
                if reply:
                    turns.append((pending_user, reply))
                pending_user = None

    return turns


def import_turns(
    transcript_path: Path,
    project_root: Path,
    *,
    meta_source: str = "cursor_chat_import",
) -> dict:
    runtime = create_runtime(project_root=str(project_root))
    turns = parse_transcript(transcript_path)

    imported = 0
    skipped = 0
    for user_msg, assistant_msg in turns:
        preview = user_msg[:120]
        result = runtime.process_interaction(
            user_msg,
            assistant_output=assistant_msg[:3000],
        )
        if result.get("ok"):
            runtime.capture(
                "system",
                f"[chat_import:{meta_source}] {preview}",
                layer="semantic",
                importance=0.72,
                source=meta_source,
            )
            imported += 1
        else:
            skipped += 1

    # Session marker
    runtime.capture(
        "system",
        f"Imported {imported} conversation turns from {transcript_path.name}",
        layer="narrative",
        importance=0.85,
        source=meta_source,
        total_turns=imported,
    )

    return {
        "transcript": str(transcript_path),
        "parsed_turns": len(turns),
        "imported": imported,
        "skipped": skipped,
        "data_dir": runtime.base_dir,
        "self_model_experiences": runtime.self_model.total_experiences,
    }


def main():
    parser = argparse.ArgumentParser(description="Import chat transcript into CNexus")
    parser.add_argument("transcript", type=Path, help="Path to agent transcript .jsonl")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root")
    args = parser.parse_args()

    report = import_turns(args.transcript.resolve(), args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
