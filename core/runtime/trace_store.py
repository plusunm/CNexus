"""Layer 2 — daily-sharded Σ.T trace store ({base_dir}/traces/YYYY-MM-DD.jsonl)."""

from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_configured_dir: Optional[str] = None
_lock_registry = threading.Lock()
_shard_locks: Dict[str, threading.Lock] = {}


def configure_trace_store(base_dir: str) -> None:
    global _configured_dir
    root = str(base_dir)
    _configured_dir = root
    migrate_legacy_trace_file(root)


def resolve_base_dir(base_dir: Optional[str]) -> Optional[str]:
    return base_dir or _configured_dir


def traces_dir(base_dir: Optional[str] = None) -> Optional[Path]:
    root = resolve_base_dir(base_dir)
    if not root:
        return None
    return Path(root) / "traces"


def shard_path(base_dir: Optional[str], day: date) -> Optional[Path]:
    root_dir = traces_dir(base_dir)
    if root_dir is None:
        return None
    return root_dir / f"{day.isoformat()}.jsonl"


def trace_file_path(base_dir: Optional[str] = None) -> Optional[Path]:
    """Primary shard for today — backward-compatible probe path for callers."""
    return shard_path(base_dir, _today_utc())


def legacy_trace_path(base_dir: Optional[str]) -> Optional[Path]:
    root = resolve_base_dir(base_dir)
    if not root:
        return None
    return Path(root) / "execution_trace.jsonl"


def list_trace_shards(base_dir: Optional[str] = None) -> List[Path]:
    root_dir = traces_dir(base_dir)
    if root_dir is None or not root_dir.is_dir():
        return []
    return sorted(root_dir.glob("????-??-??.jsonl"))


def append_trace_row(base_dir: Optional[str], row: Dict[str, Any]) -> None:
    root = resolve_base_dir(base_dir)
    if not root:
        return
    payload = {
        "ts": time.time(),
        "mono_ms": int(time.monotonic() * 1000),
        **row,
    }
    ts = payload.get("ts")
    day = _day_from_ts(ts if isinstance(ts, (int, float)) else None)
    path = shard_path(root, day)
    assert path is not None
    line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
    lock = _lock_for(path)
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)


def trace_stats(base_dir: Optional[str] = None, *, tail_lines: int = 80) -> Dict[str, Any]:
    """Aggregate probe across daily shards — tail-biased reads, full line counts."""
    root = resolve_base_dir(base_dir)
    shards = list_trace_shards(root)
    legacy = legacy_trace_path(root)
    if not shards:
        if legacy is not None and legacy.exists():
            return _stats_from_single_file(legacy, tail_lines=tail_lines)
        return _empty_stats(primary_path=trace_file_path(root))

    total_lines = 0
    readable = True
    for shard in shards:
        try:
            total_lines += _count_lines(shard)
        except OSError:
            readable = False

    sample = _tail_from_shards(shards, tail_lines) if tail_lines > 0 else _read_all_from_shards(shards)
    metrics = _metrics_from_rows(sample)
    primary = shards[-1]
    now_mono = int(time.monotonic() * 1000)
    recent = metrics["last_tick_ms"] is not None and (now_mono - metrics["last_tick_ms"]) < 60_000
    flow_active = metrics["l3_tick_count"] > 0 and recent

    return {
        "path": str(primary),
        "trace_store_path": str(traces_dir(root)),
        "shard_count": len(shards),
        "exists": True,
        "readable": readable,
        "total_lines": total_lines,
        "trace_total_entries": total_lines,
        "l3_tick_count": metrics["l3_tick_count"],
        "trace_loop_iterations": metrics["l3_tick_count"],
        "interaction_step_count": metrics["interaction_step_count"],
        "last_tick_ms": metrics["last_tick_ms"],
        "trace_last_loop_mono_ms": metrics["last_tick_ms"],
        "last_event_type": metrics["last_event_type"],
        "trace_last_event_type": metrics["last_event_type"],
        "flow_active": flow_active,
        "trace_flow_alive": flow_active,
        "no_flow": metrics["l3_tick_count"] == 0,
        "trace_flow_stopped": metrics["l3_tick_count"] == 0,
    }


def migrate_legacy_trace_file(base_dir: Optional[str]) -> bool:
    """Split legacy execution_trace.jsonl into daily shards once."""
    root = resolve_base_dir(base_dir)
    if not root:
        return False
    legacy = legacy_trace_path(root)
    if legacy is None or not legacy.is_file():
        return False
    migrated_marker = legacy.parent / "execution_trace.jsonl.migrated"
    if migrated_marker.exists():
        return False

    store_root = traces_dir(root)
    assert store_root is not None
    store_root.mkdir(parents=True, exist_ok=True)

    moved = False
    try:
        with open(legacy, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                ts = row.get("ts")
                day = _day_from_ts(ts if isinstance(ts, (int, float)) else None)
                target = shard_path(root, day)
                assert target is not None
                lock = _lock_for(target)
                with lock:
                    with open(target, "a", encoding="utf-8") as out:
                        out.write(stripped + "\n")
                moved = True
        legacy.rename(migrated_marker)
    except OSError:
        return False
    return moved


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _lock_registry:
        lock = _shard_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _shard_locks[key] = lock
        return lock


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _day_from_ts(ts: Optional[float]) -> date:
    if ts is None:
        return _today_utc()
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).date()


def _count_lines(path: Path) -> int:
    count = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _tail_from_shards(shards: List[Path], tail_lines: int) -> List[str]:
    if tail_lines <= 0:
        return []
    bucket: List[str] = []
    for shard in reversed(shards):
        need = tail_lines - len(bucket)
        if need <= 0:
            break
        try:
            lines = _read_tail_lines(shard, need)
        except OSError:
            continue
        if lines:
            bucket = lines + bucket
    return bucket[-tail_lines:]


def _read_tail_lines(path: Path, max_lines: int) -> List[str]:
    if max_lines <= 0:
        return []
    chunk_size = 8192
    collected: List[str] = []
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        pos = fh.tell()
        buffer = b""
        while pos > 0 and len(collected) < max_lines:
            read_size = min(chunk_size, pos)
            pos -= read_size
            fh.seek(pos)
            buffer = fh.read(read_size) + buffer
            parts = buffer.split(b"\n")
            buffer = parts[0]
            for part in reversed(parts[1:]):
                line = part.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                collected.append(line)
                if len(collected) >= max_lines:
                    break
        if len(collected) < max_lines and buffer.strip():
            collected.append(buffer.decode("utf-8", errors="replace").strip())
    collected.reverse()
    return collected


def _read_all_from_shards(shards: Iterable[Path]) -> List[str]:
    lines: List[str] = []
    for shard in shards:
        try:
            with open(shard, encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        lines.append(stripped)
        except OSError:
            continue
    return lines


def _metrics_from_rows(rows: List[str]) -> Dict[str, Any]:
    l3_ticks = 0
    interaction_steps = 0
    last_tick_ms: Optional[int] = None
    last_event_type: Optional[str] = None
    for raw in rows:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        last_event_type = str(row.get("type") or last_event_type)
        if row.get("type") == "l3_tick":
            l3_ticks += 1
            mono = row.get("mono_ms")
            if isinstance(mono, (int, float)):
                last_tick_ms = int(mono)
        elif row.get("type") == "interaction_step":
            interaction_steps += 1
    return {
        "l3_tick_count": l3_ticks,
        "interaction_step_count": interaction_steps,
        "last_tick_ms": last_tick_ms,
        "last_event_type": last_event_type,
    }


def _empty_stats(*, primary_path: Optional[Path]) -> Dict[str, Any]:
    return {
        "path": str(primary_path) if primary_path else None,
        "trace_store_path": str(primary_path.parent) if primary_path else None,
        "shard_count": 0,
        "exists": False,
        "readable": True,
        "total_lines": 0,
        "trace_total_entries": 0,
        "l3_tick_count": 0,
        "trace_loop_iterations": 0,
        "interaction_step_count": 0,
        "last_tick_ms": None,
        "trace_last_loop_mono_ms": None,
        "last_event_type": None,
        "trace_last_event_type": None,
        "flow_active": False,
        "trace_flow_alive": False,
        "no_flow": True,
        "trace_flow_stopped": True,
    }


def _stats_from_single_file(path: Path, *, tail_lines: int) -> Dict[str, Any]:
    lines: List[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
    except OSError:
        return {
            "path": str(path),
            "exists": True,
            "readable": False,
            "total_lines": 0,
            "l3_tick_count": 0,
            "last_tick_ms": None,
            "last_event_type": None,
            "flow_active": False,
            "no_flow": True,
        }

    sample = lines[-tail_lines:] if tail_lines > 0 else lines
    metrics = _metrics_from_rows(sample)
    now_mono = int(time.monotonic() * 1000)
    recent = metrics["last_tick_ms"] is not None and (now_mono - metrics["last_tick_ms"]) < 60_000
    flow_active = metrics["l3_tick_count"] > 0 and recent
    return {
        "path": str(path),
        "exists": True,
        "readable": True,
        "total_lines": len(lines),
        "l3_tick_count": metrics["l3_tick_count"],
        "interaction_step_count": metrics["interaction_step_count"],
        "last_tick_ms": metrics["last_tick_ms"],
        "last_event_type": metrics["last_event_type"],
        "flow_active": flow_active,
        "no_flow": metrics["l3_tick_count"] == 0,
    }
