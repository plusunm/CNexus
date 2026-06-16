"""Dedicated runtime conflict monitor — append-only JSONL audit log."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_lock = threading.RLock()
_last_signature: Optional[str] = None
_last_signature_mono: float = 0.0
_ring: list[Dict[str, Any]] = []
_RING_MAX = 400

# Re-log identical capability signatures at most every 60s (avoid probe spam).
_DEDUPE_INTERVAL_SEC = 60.0


def conflict_log_path() -> Path:
    mem = os.environ.get("BM_MEMORY_DIR", "").strip()
    if mem:
        return Path(mem).expanduser().resolve() / "runtime-conflict-monitor.log"
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "CNexus" / "data" / "runtime-conflict-monitor.log"
    return Path(".cnexus-data") / "runtime-conflict-monitor.log"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def log_conflict_event(
    event: str,
    *,
    level: str = "info",
    source: str = "runtime",
    dedupe_key: Optional[str] = None,
    force: bool = False,
    **fields: Any,
) -> Optional[Dict[str, Any]]:
    """Append one JSON line to runtime-conflict-monitor.log."""
    global _last_signature, _last_signature_mono

    now_mono = time.monotonic()
    signature = dedupe_key or f"{event}|{json.dumps(fields, sort_keys=True, default=str)}"

    with _lock:
        if not force and signature == _last_signature and (now_mono - _last_signature_mono) < _DEDUPE_INTERVAL_SEC:
            return None
        _last_signature = signature
        _last_signature_mono = now_mono

        entry: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "level": level,
            "source": source,
            **fields,
        }

        _ring.append(entry)
        if len(_ring) > _RING_MAX:
            del _ring[: len(_ring) - _RING_MAX]

        path = conflict_log_path()
        try:
            _ensure_parent(path)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError:
            return entry
        return entry


def tail_conflict_log(limit: int = 200) -> list[Dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    path = conflict_log_path()
    if not path.is_file():
        with _lock:
            return list(_ring[-limit:])
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        with _lock:
            return list(_ring[-limit:])
    out: list[Dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"ts": None, "event": "PARSE_ERROR", "raw": line[:500]})
    return out


def log_capability_transition(
    *,
    operational_ready: bool,
    full_ready: bool,
    cognitive_status: str,
    boot_phase: str,
    reason: Optional[str],
    progress: Optional[int],
    status: str,
    legacy_status: Optional[str] = None,
) -> None:
    """Log capability state; flag structural conflict patterns."""
    fields = {
        "operational_ready": operational_ready,
        "full_ready": full_ready,
        "cognitive_status": cognitive_status,
        "boot_phase": boot_phase,
        "reason": reason,
        "progress": progress,
        "status": status,
        "legacy_status": legacy_status,
    }

    conflicts: list[str] = []
    if legacy_status in ("ready_fast", "streaming") and not operational_ready:
        conflicts.append("DUAL_REALITY_FAST_NOT_OPERATIONAL")
    if legacy_status in ("ready_fast", "streaming") and full_ready:
        conflicts.append("DUAL_REALITY_FAST_WHILE_FULL")
    if operational_ready and not full_ready and cognitive_status == "warming":
        conflicts.append("OPERATIONAL_AHEAD_OF_FULL")  # expected post Step-1; informational
    if not operational_ready and full_ready:
        conflicts.append("FULL_WITHOUT_OPERATIONAL")
    if reason in ("COGNITIVE_WARMUP", "COGNITIVE_WARMUP_TIMEOUT", "L3_QUEUE_DRAIN") and not full_ready:
        conflicts.append("COGNITIVE_GATE_STALL")

    level = "warn" if any(c.endswith("STALL") or "WITHOUT" in c or "DUAL_REALITY" in c for c in conflicts) else "info"
    if conflicts:
        fields["conflicts"] = conflicts

    log_conflict_event(
        "CAPABILITY_STATE",
        level=level,
        source="capability",
        dedupe_key=f"cap|{operational_ready}|{full_ready}|{cognitive_status}|{boot_phase}|{reason}",
        **fields,
    )


def log_boot_transition(old_phase: str, new_phase: str, *, detail: Optional[str] = None) -> None:
    log_conflict_event(
        "BOOT_PHASE",
        source="boot_protocol",
        dedupe_key=f"boot|{old_phase}|{new_phase}",
        old_phase=old_phase,
        new_phase=new_phase,
        detail=detail,
    )


def log_runtime_warm_failure(error: str) -> None:
    log_conflict_event(
        "RUNTIME_WARM_FAILED",
        level="error",
        source="deps",
        force=True,
        error=error,
    )


def log_client_conflict(
    event: str,
    *,
    level: str = "warn",
    **fields: Any,
) -> None:
    log_conflict_event(event, level=level, source="frontend", force=True, **fields)
