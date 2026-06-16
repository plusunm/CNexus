"""Fast-Path v1 — instant UI snapshot without cluster / replay / CRDT gates."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from core.runtime.boot_protocol import boot_status, get_boot_phase, is_runtime_warming
from core.runtime.system_capability import merge_capability_fields


def fast_boot_mode_enabled(runtime: Optional[Any] = None) -> bool:
    """When true, /v1/system/ready defaults to snapshot path (unless mode=full)."""
    flag = os.environ.get("CNEXUS_FAST_PATH_V1", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if runtime is not None:
        env = getattr(runtime, "env", None)
        if isinstance(env, dict):
            return str(env.get("CNEXUS_FAST_PATH_V1", "1")).strip() not in ("0", "false", "no", "off")
    return True


def should_use_fast_ready(*, mode: str, runtime: Optional[Any]) -> bool:
    normalized = (mode or "default").strip().lower()
    if normalized == "full":
        return False
    if normalized == "stream":
        return False
    if normalized == "fast":
        return True
    from core.runtime.fast_path_v3 import fast_path_v3_enabled
    from core.runtime.streaming_ready import fast_path_v2_enabled

    if fast_path_v3_enabled(runtime) or fast_path_v2_enabled(runtime):
        return False
    return fast_boot_mode_enabled(runtime)


def fast_ready_snapshot(
    runtime: Optional[Any],
    *,
    boot_id: str,
    app_started: bool,
    mono_start: float,
) -> Dict[str, Any]:
    """IO-free first paint payload — cluster / replay / CRDT deferred."""
    uptime_ms = int((time.monotonic() - mono_start) * 1000) if app_started else 0
    boot = boot_status()
    ws_status = "alive" if runtime is not None else "starting"
    http_status = "listening" if app_started else "starting"

    base = {
        "status": "ready_fast",
        "ui": "ok",
        "boot_id": boot_id,
        "boot_phase": get_boot_phase().value,
        "token_valid": True,
        "license_valid": True,
        "ws": ws_status,
        "http": http_status,
        "memory": "deferred",
        "uptime_ms": uptime_ms,
        "version": "0.1.0-alpha",
        "checks": {
            "l3": True,
            "cognitive": "unknown",
            "cluster": "deferred",
            "runtime": {
                "name": "runtime",
                "ok": runtime is not None,
                "detail": "fast_snapshot",
            },
        },
        "render_mode": "fast_path_v1",
        "hydration": "background",
        "boot": boot,
        "isolation": "fast_path_v1",
    }
    memory_ok = runtime is not None
    return merge_capability_fields(
        base,
        app_started=app_started,
        runtime_present=runtime is not None,
        runtime_warming=is_runtime_warming(),
        memory_ok=memory_ok,
    )
