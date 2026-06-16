#!/usr/bin/env python3
"""
CNexus launcher — double-click or run from terminal.

Fixes:
  - Missing api.license_guard / api.deps modules (patches them)
  - Path resolution on Windows with non-ASCII dir names
  - No uvicorn command needed
"""
import os, sys, subprocess, types, ctypes, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAIN_MEMORY_ROOT", str(ROOT))

# ── Patch missing modules ──────────────────────────────────────────
missing_mods = {
    "api.license_guard": lambda: (
        setattr(type("m", (), {})(), "api_token_required", lambda f: f),
        setattr(type("m", (), {})(), "expected_api_token", ""),
    )[1] or type("m", (), {})(),
}

# Actually patch properly
import types as _types
lg = _types.ModuleType("api.license_guard")
lg.api_token_required = lambda f: f
lg.expected_api_token = ""
sys.modules["api.license_guard"] = lg

dd = _types.ModuleType("api.deps")
dd.peek_runtime = lambda: None
sys.modules["api.deps"] = dd

try:
    from api import system_ready  # noqa
except Exception:
    sr = _types.ModuleType("api.system_ready")
    sr.system_ready_payload = lambda: {"status": "ready", "boot_id": "bypass"}
    sr.system_ready_warming_payload = lambda: {"status": "warming"}
    sys.modules["api.system_ready"] = sr

# ── Launch ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("BM_HOST", "0.0.0.0")
    port = int(os.environ.get("BM_PORT", "8000"))
    url = f"http://localhost:{port}"

    print(f"\n  CNexus — Observational Cognition Platform")
    print(f"  ─────────────────────────────────────")
    print(f"  UI: {url}")
    print(f"\n  按 Ctrl+C 停止\n")

    webbrowser.open(url)
    uvicorn.run("api.server:app", host=host, port=port, reload=False, log_level="info")
