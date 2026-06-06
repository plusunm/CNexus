#!/usr/bin/env python3
"""Launch Brain-Memory G1 Web UI."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAIN_MEMORY_ROOT", str(ROOT))

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BM_HOST", "127.0.0.1")
    port = int(os.environ.get("BM_PORT", "8080"))
    print(f"\n  Brain-Memory G1 UI → http://{host}:{port}\n")
    uvicorn.run("api.server:app", host=host, port=port, reload=False)
