"""Snapshot + incremental AuditLog replay for cognitive state reconstruction."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class StateReconstructor:
    """
    Load the latest cognitive snapshot, then replay only AuditLog entries after it.
    Falls back to full replay when no valid snapshot exists.
    """

    SNAPSHOT_VERSION = "1.0"

    def __init__(
        self,
        audit_log,
        replay_engine,
        snapshot_dir: str | Path,
        *,
        snapshot_interval: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        self.audit_log = audit_log
        self.replay_engine = replay_engine
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = snapshot_interval if snapshot_interval is not None else _env_int(
            "CNEXUS_SNAPSHOT_INTERVAL", 1000
        )
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_STATE_RECON_ENABLE", True)
        self._lock = threading.Lock()
        self.last_report: Dict[str, Any] = {}
        self.progress: Dict[str, Any] = {
            "phase": "idle",
            "progress": 0.0,
            "message": "",
            "started_at": None,
            "completed_at": None,
        }

    def _snapshot_path(self, entry_index: int, log_hash: str) -> Path:
        suffix = str(log_hash or "0")[:12]
        return self.snapshot_dir / f"snapshot_{entry_index:08d}_{suffix}.json"

    def list_snapshots(self) -> List[Path]:
        rows = sorted(self.snapshot_dir.glob("snapshot_*.json"), key=lambda path: path.stat().st_mtime)
        return rows

    def load_latest_snapshot(self) -> Optional[dict]:
        rows = self.list_snapshots()
        if not rows:
            return None
        for path in reversed(rows):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and data.get("cognitive"):
                    data["_path"] = str(path)
                    return data
            except Exception:
                continue
        return None

    def _snapshot_anchor_valid(self, snapshot: dict) -> bool:
        if not self.audit_log:
            return False
        last_hash = str(snapshot.get("last_log_hash") or "0")
        if last_hash == "0":
            return int(snapshot.get("entry_index") or 0) == 0
        for entry in self.audit_log.iter_entries():
            if str(entry.get("hash") or "") == last_hash:
                return True
        return False

    def save_snapshot(
        self,
        *,
        memory_store,
        engine_state: dict,
        last_log_hash: str,
        entry_index: int,
        reputation: Optional[dict] = None,
    ) -> dict:
        cognitive = self.replay_engine.export_cognitive_state(memory_store, engine_state)
        payload = {
            "version": self.SNAPSHOT_VERSION,
            "created_at": time.time(),
            "last_log_hash": str(last_log_hash or "0"),
            "entry_index": int(entry_index or 0),
            "audit_head": str(getattr(self.audit_log, "last_hash", "0") or "0"),
            "cognitive": cognitive,
            "reputation": dict(reputation or {}),
        }
        path = self._snapshot_path(payload["entry_index"], payload["last_log_hash"])
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self._prune_old_snapshots(keep=5)
        return {"ok": True, "path": str(path), "entry_index": payload["entry_index"]}

    def _prune_old_snapshots(self, *, keep: int = 5):
        rows = self.list_snapshots()
        if len(rows) <= keep:
            return
        for path in rows[:-keep]:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    def _set_progress(self, phase: str, progress: float, message: str, *, done: bool = False):
        with self._lock:
            self.progress["phase"] = phase
            self.progress["progress"] = max(0.0, min(1.0, float(progress)))
            self.progress["message"] = message
            if self.progress.get("started_at") is None and phase != "idle":
                self.progress["started_at"] = time.time()
            if done:
                self.progress["completed_at"] = time.time()

    def reconstruct(
        self,
        *,
        memory_store,
        engine_state: dict,
        reputation_registry=None,
        force: bool = False,
        reset: bool = True,
        reindex_assets: Optional[Callable[[], dict]] = None,
    ) -> Dict[str, Any]:
        if not self.enabled or self.replay_engine is None or self.audit_log is None:
            return {"ok": False, "error": "reconstructor_unavailable"}

        all_entries = self.audit_log.iter_entries()
        total_entries = len(all_entries)
        snapshot = None if force else self.load_latest_snapshot()
        use_snapshot = bool(snapshot and self._snapshot_anchor_valid(snapshot))
        replay_entries = all_entries
        snapshot_index = 0
        incremental = False

        self._set_progress("replay", 0.02, "准备认知重塑…")

        if use_snapshot:
            self.replay_engine.hydrate_cognitive_state(
                snapshot.get("cognitive") or {},
                memory_store,
                engine_state,
                keep_models=True,
            )
            if reputation_registry is not None and snapshot.get("reputation"):
                reputation_registry.import_state(snapshot.get("reputation") or {})
            since_hash = str(snapshot.get("last_log_hash") or "0")
            replay_entries, anchor_found = self.audit_log.get_entries_since(since_hash)
            snapshot_index = int(snapshot.get("entry_index") or 0)
            incremental = anchor_found and bool(replay_entries)
            if not anchor_found:
                replay_entries = all_entries
                snapshot_index = 0
                self.replay_engine._reset_engine(engine_state, memory_store, keep_models=True)
        elif reset:
            self.replay_engine._reset_engine(engine_state, memory_store, keep_models=True)

        mode = "incremental" if incremental else ("full" if not use_snapshot else "snapshot_only")
        report: Dict[str, Any] = {
            "ok": False,
            "mode": mode,
            "entries_total": total_entries,
            "entries_replayed": len(replay_entries),
            "snapshot_used": use_snapshot,
            "snapshot_index": snapshot_index,
            "replayed_at": time.time(),
        }

        if not replay_entries and use_snapshot:
            report.update({
                "ok": True,
                "message": "snapshot_current",
                "memory_blocks": len(memory_store.blocks),
                "trace_rows": len(engine_state.get("trace") or []),
            })
            self.last_report = report
            self._set_progress("alive", 1.0, "快照已是最新认知态", done=True)
            return report

        def _on_progress(done: int, total: int):
            if total <= 0:
                return
            ratio = done / total
            overall = 0.1 + ratio * 0.75
            self._set_progress(
                "replay",
                overall,
                f"记忆重塑 {done}/{total} · 快照后增量" if incremental else f"记忆重塑 {done}/{total}",
            )
            current_index = snapshot_index + done
            if self.snapshot_interval > 0 and current_index > 0 and current_index % self.snapshot_interval == 0:
                entry = replay_entries[done - 1] if done > 0 and done <= len(replay_entries) else None
                last_hash = str((entry or {}).get("hash") or getattr(self.audit_log, "last_hash", "0"))
                rep = None
                if reputation_registry is not None and hasattr(reputation_registry, "export_state"):
                    rep = reputation_registry.export_state()
                self.save_snapshot(
                    memory_store=memory_store,
                    engine_state=engine_state,
                    last_log_hash=last_hash,
                    entry_index=current_index,
                    reputation=rep,
                )

        replay_report = self.replay_engine.replay(
            memory_store=memory_store,
            engine_state=engine_state,
            reset=False if use_snapshot else reset,
            keep_models=True,
            entries=replay_entries,
            on_progress=_on_progress,
        )
        report.update(replay_report)
        report["mode"] = mode

        if replay_report.get("ok"):
            last_entry = all_entries[-1] if all_entries else {}
            rep = None
            if reputation_registry is not None and hasattr(reputation_registry, "export_state"):
                rep = reputation_registry.export_state()
            snap = self.save_snapshot(
                memory_store=memory_store,
                engine_state=engine_state,
                last_log_hash=str(last_entry.get("hash") or getattr(self.audit_log, "last_hash", "0")),
                entry_index=total_entries,
                reputation=rep,
            )
            report["snapshot_saved"] = snap

            self._set_progress("vector_index", 0.9, "神经网络热身…")
            if reindex_assets:
                try:
                    index_report = reindex_assets()
                    report["vector_index"] = index_report
                except Exception as exc:
                    report["vector_index"] = {"ok": False, "error": str(exc)}

            summary = (
                f"共回放 {report.get('entries_replayed', 0)} 条认知记录"
                f"（{'增量' if incremental else '全量'}），"
                f"blocks={report.get('memory_blocks', 0)} trace={report.get('trace_rows', 0)}"
            )
            report["summary"] = summary
            self._set_progress("alive", 1.0, summary, done=True)

        self.last_report = report
        return report

    def status(self) -> Dict[str, Any]:
        latest = self.load_latest_snapshot()
        with self._lock:
            progress = dict(self.progress)
        return {
            "enabled": self.enabled,
            "snapshot_interval": self.snapshot_interval,
            "snapshot_count": len(self.list_snapshots()),
            "latest_snapshot": {
                "entry_index": latest.get("entry_index") if latest else None,
                "last_log_hash": latest.get("last_log_hash") if latest else None,
                "created_at": latest.get("created_at") if latest else None,
            } if latest else None,
            "progress": progress,
            "last_report": dict(self.last_report),
        }
