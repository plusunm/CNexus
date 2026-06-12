#!/usr/bin/env python3
"""Run P3-A benchmark suite and write docs/benchmarks/BASELINE.md."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "benchmarks" / "BASELINE.md"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/benchmark/", "-q", "--tb=short"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# CNexus Benchmark Baseline

Generated: {datetime.now().isoformat()}

## Suite

- Memory ON/OFF recall delta
- Attention ON/OFF recall delta
- Reflection ON/OFF narrative version delta

## Last run

```
{proc.stdout}
{proc.stderr}
```

Exit code: {proc.returncode}
"""
    OUT.write_text(body, encoding="utf-8")
    print(json.dumps({"baseline": str(OUT), "exit_code": proc.returncode}))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
