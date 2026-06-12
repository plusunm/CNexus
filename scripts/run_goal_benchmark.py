#!/usr/bin/env python3
"""Record Goal Layer verification baseline."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "benchmarks" / "GOAL_BASELINE.md"


def main() -> int:
    tests = [
        "tests/test_goal_synthesis.py",
        "tests/test_goal_layer.py",
        "tests/benchmark/test_goal_influence.py",
        "tests/test_intent_engine.py",
    ]
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    stamp = datetime.now(timezone.utc).isoformat()

    body = f"""# Goal Layer Baseline

Generated: {stamp}

## Scope

- Goal capture → intent block JSON integrity
- GoalManager mount on capture hot path
- Governance cycle `goal_layer` observation
- BeliefMeta boundary (Belief/Reflection only)
- Goal vs stale episodic recall influence

## Pytest

```
{proc.stdout.strip() or proc.stderr.strip()}
```

Exit code: {proc.returncode}

## v1 Boundary

| In scope | Out of scope (full Mind) |
|----------|--------------------------|
| IntentEngine + GoalManager on capture | Automatic BeliefMeta on every capture |
| Recall intent context + goal ranking boost | Full narrative/working_self sync |
| Governance cycle read-only goal snapshot | Background goal mutation in governance |
"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(json.dumps({"written": str(OUT), "exit_code": proc.returncode}, ensure_ascii=False))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
