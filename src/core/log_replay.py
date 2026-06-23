"""Log replay — reconstruct cognitive index from AuditLog events."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _parse_timestamp(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return time.time()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return time.time()


class LogReplayEngine:
    """
    Replay AuditLog into memory blocks + trace summaries.
    Full block content is restored from content_preview when present;
    otherwise placeholders are created for index continuity.
    """

    SKIPPED_EVENTS = frozenset({
        "peer.handshake",
        "peer.sync",
        "peer.negotiate",
    })

    def __init__(self, audit_log=None):
        self.audit_log = audit_log
        self.last_report: Dict[str, Any] = {}

    def count_replayable_events(self, entries: Optional[List[dict]] = None) -> Dict[str, int]:
        rows = entries if entries is not None else self._iter_entries()
        counts: Dict[str, int] = {}
        for entry in rows:
            event = str((entry.get("data") or {}).get("event") or "")
            if event:
                counts[event] = counts.get(event, 0) + 1
        return counts

    def replay(
        self,
        *,
        memory_store,
        engine_state: dict,
        reset: bool = True,
        keep_models: bool = True,
        entries: Optional[List[dict]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        rows = entries if entries is not None else self._iter_entries()
        return self._replay_entries(
            rows,
            memory_store=memory_store,
            engine_state=engine_state,
            reset=reset,
            keep_models=keep_models,
            on_progress=on_progress,
        )

    def _replay_entries(
        self,
        entries: List[dict],
        *,
        memory_store,
        engine_state: dict,
        reset: bool = True,
        keep_models: bool = True,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        report: Dict[str, Any] = {
            "ok": False,
            "entries_total": len(entries),
            "applied": 0,
            "skipped": 0,
            "events": {},
            "memory_blocks": 0,
            "trace_rows": 0,
            "assets_indexed": 0,
            "replayed_at": time.time(),
        }
        if not entries:
            report["ok"] = True
            report["message"] = "empty_audit_log"
            self.last_report = report
            return report

        if reset:
            self._reset_engine(engine_state, memory_store, keep_models=keep_models)

        seen_blocks: Set[str] = set()
        seen_traces: Set[str] = set()
        seen_assets: Set[str] = set()
        if not reset:
            for block in list(getattr(memory_store, "blocks", []) or []):
                block_id = str(block.get("block_id") or "")
                if block_id:
                    seen_blocks.add(block_id)
                asset_id = str((block.get("data") or {}).get("asset_id") or "")
                if asset_id:
                    seen_assets.add(asset_id)
            for row in list(engine_state.get("trace") or []):
                trace_id = str(row.get("trace_id") or "")
                if trace_id:
                    seen_traces.add(trace_id)

        total = len(entries)
        for index, entry in enumerate(entries, start=1):
            data = dict(entry.get("data") or {})
            event = str(data.get("event") or "")
            if not event:
                report["skipped"] += 1
                continue

            report["events"][event] = report["events"].get(event, 0) + 1
            ts = _parse_timestamp(entry.get("timestamp"))

            if event == "memory.block":
                if self._apply_memory_block(data, memory_store, seen_blocks, ts):
                    report["applied"] += 1
                else:
                    report["skipped"] += 1
            elif event == "trace.cycle":
                if self._apply_trace_cycle(data, engine_state, seen_traces, ts):
                    report["applied"] += 1
                else:
                    report["skipped"] += 1
            elif event in ("asset.upload", "asset.received"):
                if self._apply_asset_event(data, memory_store, seen_assets, ts):
                    report["applied"] += 1
                    report["assets_indexed"] += 1
                else:
                    report["skipped"] += 1
            elif event == "memory.clear":
                keep = bool(data.get("keep_models", True))
                self._reset_engine(engine_state, memory_store, keep_models=keep)
                seen_blocks.clear()
                seen_traces.clear()
                seen_assets.clear()
                report["applied"] += 1
            elif event == "rem.sleep":
                self._apply_rem_sleep(data, engine_state, ts)
                report["applied"] += 1
            elif event == "state.checkpoint":
                self._apply_checkpoint(data, engine_state)
                report["applied"] += 1
            elif event == "reflection.meta":
                if self._apply_reflection_event(data, memory_store, ts):
                    report["applied"] += 1
                else:
                    report["skipped"] += 1
            elif event in self.SKIPPED_EVENTS:
                report["skipped"] += 1
            else:
                report["skipped"] += 1

            if on_progress and (index == total or index % 50 == 0):
                on_progress(index, total)

        report["memory_blocks"] = len(memory_store.blocks)
        report["trace_rows"] = len(engine_state.get("trace") or [])
        report["ok"] = True
        report["message"] = "replay_complete"
        self.last_report = report
        return report

    def _iter_entries(self) -> List[dict]:
        if not self.audit_log:
            return []
        reader = getattr(self.audit_log, "iter_entries", None)
        if not callable(reader):
            reader = getattr(self.audit_log, "_read_all_entries", None)
        return list(reader()) if callable(reader) else []

    def _reset_engine(self, engine_state: dict, memory_store, *, keep_models: bool = True):
        registry = dict(engine_state.get("model_registry") or {}) if keep_models else {}
        engine_state["trace"] = []
        memory_store.blocks = []
        engine_state["current_iteration"] = 0
        engine_state["activation"] = {"scores": {}, "wormhole_links": []}
        engine_state["projection"] = {"nodes": {}, "links": []}
        cons = dict(engine_state.get("consolidation") or {})
        cons.update({
            "rem_running": False,
            "last_rem_at": cons.get("last_rem_at", 0),
            "total_pruned": cons.get("total_pruned", 0),
            "total_facts": cons.get("total_facts", 0),
        })
        engine_state["consolidation"] = cons
        if keep_models and registry:
            engine_state["model_registry"] = registry

    def _apply_memory_block(self, data: dict, memory_store, seen: Set[str], ts: float) -> bool:
        block_id = str(data.get("block_id") or "").strip()
        if not block_id or block_id in seen:
            return False
        preview = str(data.get("content_preview") or data.get("content") or "").strip()
        label = str(data.get("label") or "episode")
        keywords = data.get("keywords") or []
        if not preview:
            preview = f"[replayed:{label}] {block_id[:24]}"
        memory_store.blocks.append({
            "block_id": block_id,
            "label": label,
            "data": {
                "content": preview[:2000],
                "keywords": keywords if isinstance(keywords, list) else [],
                "replayed": True,
            },
            "importance": float(data.get("importance", 0.5)),
            "timestamp": ts,
        })
        seen.add(block_id)
        return True

    def _apply_trace_cycle(self, data: dict, engine_state: dict, seen: Set[str], ts: float) -> bool:
        trace_id = str(data.get("trace_id") or "").strip()
        if not trace_id or trace_id in seen:
            return False
        iteration = int(data.get("iteration") or 0)
        row = {
            "iteration": iteration,
            "trace_id": trace_id,
            "timestamp": ts,
            "input": str(data.get("input_preview") or data.get("input") or "")[:2000],
            "replayed": True,
            "intent": data.get("intent"),
        }
        engine_state.setdefault("trace", []).append(row)
        engine_state["current_iteration"] = max(int(engine_state.get("current_iteration") or 0), iteration)
        seen.add(trace_id)
        return True

    def _apply_asset_event(self, data: dict, memory_store, seen: Set[str], ts: float) -> bool:
        asset_id = str(data.get("asset_id") or "").strip()
        if not asset_id or asset_id in seen:
            return False
        block_id = f"asset-{asset_id[:16]}"
        summary = str(data.get("summary") or data.get("desc") or data.get("filename") or asset_id[:16])
        memory_store.blocks.append({
            "block_id": block_id,
            "label": str(data.get("type") or "asset"),
            "data": {
                "content": summary[:2000],
                "asset_id": asset_id,
                "filename": data.get("filename"),
                "asset_type": data.get("type"),
                "replayed": True,
            },
            "importance": 0.72,
            "timestamp": ts,
        })
        seen.add(asset_id)
        return True

    def _apply_rem_sleep(self, data: dict, engine_state: dict, ts: float):
        cons = dict(engine_state.get("consolidation") or {})
        details = data.get("details") or {}
        cons["last_rem_at"] = ts
        cons["last_rem_report"] = details
        cons["total_pruned"] = int(cons.get("total_pruned", 0)) + int(details.get("pruned_blocks") or 0)
        cons["total_facts"] = int(cons.get("total_facts", 0)) + int(details.get("facts_created") or 0)
        engine_state["consolidation"] = cons

    def _apply_checkpoint(self, data: dict, engine_state: dict):
        cons = dict(engine_state.get("consolidation") or {})
        cons["last_checkpoint_at"] = time.time()
        cons["last_checkpoint"] = {
            "memory_blocks": data.get("memory_blocks"),
            "trace_count": data.get("trace_count"),
            "iteration": data.get("iteration"),
            "audit_head": data.get("audit_head"),
        }
        engine_state["consolidation"] = cons

    def _apply_reflection_event(self, data: dict, memory_store, ts: float) -> bool:
        preview = str(data.get("reflection_preview") or "").strip()
        if not preview:
            return False
        block_id = f"meta-replay-{hash(preview) & 0xFFFFFFFF:08x}"
        memory_store.blocks.append({
            "block_id": block_id,
            "label": "reflective",
            "data": {
                "content": preview[:2000],
                "question": data.get("question"),
                "biases": data.get("biases"),
                "replayed": True,
                "metacognitive": True,
            },
            "importance": 0.75,
            "timestamp": ts,
        })
        return True

    @staticmethod
    def export_cognitive_state(memory_store, engine_state: dict) -> Dict[str, Any]:
        return {
            "blocks": [dict(row) for row in list(getattr(memory_store, "blocks", []) or [])],
            "trace": [dict(row) for row in list(engine_state.get("trace") or [])],
            "current_iteration": int(engine_state.get("current_iteration") or 0),
            "activation": dict(engine_state.get("activation") or {"scores": {}, "wormhole_links": []}),
            "projection": dict(engine_state.get("projection") or {"nodes": {}, "links": []}),
            "consolidation": dict(engine_state.get("consolidation") or {}),
            "model_registry": dict(engine_state.get("model_registry") or {}),
        }

    @staticmethod
    def hydrate_cognitive_state(snapshot: dict, memory_store, engine_state: dict, *, keep_models: bool = True):
        cognitive = dict(snapshot or {})
        memory_store.blocks = list(cognitive.get("blocks") or [])
        engine_state["trace"] = list(cognitive.get("trace") or [])
        engine_state["current_iteration"] = int(cognitive.get("current_iteration") or 0)
        engine_state["activation"] = dict(cognitive.get("activation") or {"scores": {}, "wormhole_links": []})
        engine_state["projection"] = dict(cognitive.get("projection") or {"nodes": {}, "links": []})
        engine_state["consolidation"] = dict(cognitive.get("consolidation") or {})
        if keep_models:
            registry = dict(engine_state.get("model_registry") or {})
            registry.update(dict(cognitive.get("model_registry") or {}))
            if registry:
                engine_state["model_registry"] = registry

    def status(self) -> Dict[str, Any]:
        counts = self.count_replayable_events()
        return {
            "enabled": _env_truthy("CNEXUS_REPLAY_ENABLE", True),
            "last_report": dict(self.last_report),
            "audit_events": counts,
            "replayable_total": sum(
                counts.get(k, 0)
                for k in ("memory.block", "trace.cycle", "asset.upload", "asset.received")
            ),
        }

    @staticmethod
    def replay_needed(
        *,
        audit_entry_count: int,
        memory_block_count: int,
        trace_count: int,
        replayable_in_audit: int,
    ) -> bool:
        if audit_entry_count <= 0 or replayable_in_audit <= 0:
            return False
        if memory_block_count == 0 and trace_count == 0:
            return True
        return replayable_in_audit > (memory_block_count + trace_count)


def replay_enabled() -> bool:
    return _env_truthy("CNEXUS_REPLAY_ENABLE", True)


def replay_on_boot() -> bool:
    return _env_truthy("CNEXUS_REPLAY_ON_BOOT", True)


def replay_after_genesis() -> bool:
    return _env_truthy("CNEXUS_REPLAY_AFTER_GENESIS", True)
