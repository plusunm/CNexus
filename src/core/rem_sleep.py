"""REM deep-sleep engine — weighted memory lifecycle, synthesis, and audit trail."""

from __future__ import annotations

import math
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class RemSleepEngine:
    """Background cognitive cleanup — prune, synthesize, archive with audit safety."""

    def __init__(
        self,
        block_store,
        audit_log=None,
        identity_manager=None,
        *,
        threshold: Optional[float] = None,
        chunk_size: Optional[int] = None,
        active_protect_seconds: Optional[int] = None,
        audit_fn: Optional[Callable[[str, dict], Optional[str]]] = None,
    ):
        self.block_store = block_store
        self.audit_log = audit_log
        self.identity_manager = identity_manager
        self.audit_fn = audit_fn
        self._lock = threading.Lock()
        self.last_cycle_at: float = 0.0
        self.last_report: Optional[dict] = None
        self.running: bool = False

        self.enabled = _env_truthy("CNEXUS_REM_ENABLE", default=True)
        self.threshold = threshold if threshold is not None else _env_float("CNEXUS_REM_THRESHOLD", 0.02)
        self.chunk_size = chunk_size if chunk_size is not None else _env_int("CNEXUS_REM_CHUNK_SIZE", 50)
        self.active_protect_seconds = (
            active_protect_seconds
            if active_protect_seconds is not None
            else _env_int("CNEXUS_REM_ACTIVE_PROTECT", 3600)
        )
        self.idle_seconds = _env_int("CNEXUS_REM_IDLE_SECONDS", 1800)
        self.cooldown_seconds = _env_int("CNEXUS_REM_COOLDOWN", 3600)
        self.active_node_threshold = _env_int("CNEXUS_REM_ACTIVE_THRESHOLD", 20)
        self.node_threshold = _env_int("CNEXUS_REM_NODE_THRESHOLD", 36)
        self.trace_keep = _env_int("CNEXUS_REM_TRACE_KEEP", 12)
        self.compact_window_seconds = _env_int("CNEXUS_REM_COMPACT_WINDOW", 7 * 86400)
        self.max_facts = _env_int("CNEXUS_REM_MAX_FACTS", 5)
        self.watchdog_interval = _env_int("CNEXUS_REM_WATCHDOG_INTERVAL", 60)
        self.cycle_interval = _env_int("CNEXUS_REM_CYCLE_SECONDS", 86400)

    # ── Weight model ────────────────────────────────────────────────────

    def calculate_weight(
        self,
        block: dict,
        *,
        now: Optional[float] = None,
        access_freq: float = 0.0,
        connection_bonus: float = 0.0,
    ) -> float:
        """
        Score = (AccessFreq × 1.5) + RecencyScore − AgePenalty + ConnectionBonus
        """
        now = time.time() if now is None else float(now)
        ts = float(block.get("timestamp") or now)
        age_seconds = max(0.0, now - ts)
        age_days = age_seconds / 86400.0
        recency_score = math.exp(-age_seconds / max(self.compact_window_seconds, 3600))
        age_penalty = age_days * 0.05
        importance = float(block.get("importance", 0.5))
        access = max(access_freq, importance * 0.25)
        return (access * 1.5) + recency_score - age_penalty + connection_bonus

    def is_recently_active(self, block: dict, *, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else float(now)
        ts = float(block.get("timestamp") or 0)
        if not ts:
            return False
        return (now - ts) < self.active_protect_seconds

    def is_protected_block(self, block: dict, protected_ids: Set[str], *, now: Optional[float] = None) -> bool:
        block_id = str(block.get("block_id") or "")
        label = str(block.get("label") or "")
        if self.is_recently_active(block, now=now):
            return True
        if block_id in protected_ids:
            return True
        if block_id.startswith("sem-rem-"):
            return True
        if label in ("semantic", "emotion", "persona"):
            return True
        data = block.get("data") or {}
        if data.get("archived"):
            return True
        return False

    # ── Trigger policy ──────────────────────────────────────────────────

    def should_trigger(self, consolidation: dict, context: dict, *, force: bool = False) -> bool:
        if not self.enabled:
            return bool(force)
        if force:
            return True
        if consolidation.get("rem_running"):
            return False
        now = time.time()
        if now - float(consolidation.get("last_rem_at", 0)) < self.cooldown_seconds:
            return False
        idle = now - float(consolidation.get("last_activity_at", now))
        if idle >= self.idle_seconds:
            return True
        if time.localtime().tm_hour == 3 and idle >= 300:
            return True
        specs = context.get("specs") or []
        scores = context.get("scores") or {}
        activation_threshold = float(context.get("activation_threshold", 0.4))
        active = sum(1 for spec in specs if float(scores.get(spec["id"], 0.0)) > activation_threshold)
        if active >= self.active_node_threshold:
            return True
        if len(specs) >= self.node_threshold:
            return True
        return False

    # ── Audit helper ────────────────────────────────────────────────────

    def _audit_rem(self, details: dict) -> Optional[str]:
        payload = {"action": "REM_SLEEP", "details": details}
        if self.audit_fn:
            return self.audit_fn("rem.sleep", payload)
        if self.audit_log is None or self.identity_manager is None:
            return "audit_skipped"
        try:
            return self.audit_log.log(self.identity_manager, payload)
        except Exception:
            return None

    def _safe_prune_blocks(
        self,
        to_remove: List[dict],
        audit_details: dict,
    ) -> Tuple[int, int]:
        """Audit-first prune; archive recent/low-risk instead of hard delete when protected."""
        if not to_remove:
            return 0, 0
        audit_hash = self._audit_rem({**audit_details, "prune_count": len(to_remove)})
        if self.audit_log and self.identity_manager and not audit_hash:
            return 0, 0

        removed = 0
        archived = 0
        remove_ids = {str(b.get("block_id") or "") for b in to_remove}
        kept = []
        for block in self.block_store.blocks:
            block_id = str(block.get("block_id") or "")
            if block_id not in remove_ids:
                kept.append(block)
                continue
            if self.is_recently_active(block):
                data = dict(block.get("data") or {})
                data["archived"] = True
                data["archive_reason"] = "rem_protect_recent"
                block = dict(block)
                block["data"] = data
                kept.append(block)
                archived += 1
            else:
                removed += 1
        self.block_store.blocks = kept
        return removed, archived

    # ── Chunked scan ────────────────────────────────────────────────────

    def _iter_block_chunks(self) -> List[List[dict]]:
        blocks = list(self.block_store.blocks)
        if not blocks:
            return []
        chunks = []
        for i in range(0, len(blocks), self.chunk_size):
            chunks.append(blocks[i : i + self.chunk_size])
        return chunks

    def synaptic_prune(self, context: dict, report: dict) -> Set[str]:
        specs = context.get("specs") or []
        scores = context.get("scores") or {}
        adjacency = context.get("adjacency") or {}
        protected = set(context.get("protected_ids") or [])
        now = float(context.get("now") or time.time())
        pruned_ids: Set[str] = set()

        for spec in specs:
            nid = spec["id"]
            if nid in protected or nid.startswith("sem-rem-"):
                continue
            degree = len(adjacency.get(nid, set()))
            connection_bonus = min(0.5, degree * 0.08)
            pseudo_block = {
                "block_id": nid,
                "timestamp": spec.get("timestamp", now),
                "importance": spec.get("importance", 0.5),
            }
            weight = self.calculate_weight(
                pseudo_block,
                now=now,
                access_freq=float(scores.get(nid, 0.0)),
                connection_bonus=connection_bonus,
            )
            tag = spec.get("tag", "term")
            if weight >= self.threshold:
                continue
            if tag in ("goal", "identity", "belief", "episode") and degree > 0:
                continue
            if tag in ("term", "insight") and degree <= 1:
                pruned_ids.add(nid)

        to_remove: List[dict] = []
        for chunk in self._iter_block_chunks():
            for block in chunk:
                block_id = str(block.get("block_id") or "")
                if self.is_protected_block(block, protected, now=now):
                    continue
                degree = len(adjacency.get(block_id, set()))
                weight = self.calculate_weight(
                    block,
                    now=now,
                    access_freq=float(scores.get(block_id, 0.0)),
                    connection_bonus=min(0.5, degree * 0.08),
                )
                drop = block_id in pruned_ids
                if not drop and block.get("label") not in ("emotion", "persona", "semantic"):
                    if block_id.startswith("kw-") and weight < self.threshold:
                        drop = True
                    elif weight < self.threshold and block.get("label") == "episodic":
                        drop = True
                if drop:
                    to_remove.append(block)
                    pruned_ids.add(block_id)

        removed, archived = self._safe_prune_blocks(
            to_remove,
            {"phase": "synaptic_prune", "candidate_ids": list(pruned_ids)[:32]},
        )
        report["pruned_nodes"] = len(pruned_ids)
        report["pruned_blocks"] = removed
        report["archived_blocks"] = archived
        return pruned_ids

    def collect_compaction_sources(self, context: dict) -> Tuple[List[dict], List[dict]]:
        now = float(context.get("now") or time.time())
        trace = list(context.get("trace") or [])
        specs = context.get("specs") or []
        scores = context.get("scores") or {}

        keep_recent = max(self.trace_keep, 5)
        to_compact = trace[:-keep_recent] if len(trace) > keep_recent else []
        week_cutoff = now - self.compact_window_seconds
        filtered = []
        for entry in to_compact:
            ts = float(entry.get("timestamp") or 0)
            if ts and ts > week_cutoff:
                filtered.append(entry)
            elif not ts:
                filtered.append(entry)
        to_compact = filtered or to_compact

        sources: List[dict] = []
        for entry in to_compact:
            iteration = int(entry.get("iteration", 0))
            trace_id = entry.get("trace_id") or f"v2-trace-{iteration}"
            inp = str(entry.get("input") or "").strip()
            reply = str(entry.get("reply_text") or entry.get("reply") or "").strip()
            text = "\n".join(x for x in (inp, reply) if x).strip()
            if not text:
                speech = entry.get("speech") or {}
                if isinstance(speech, dict):
                    reply = str(speech.get("text") or speech.get("content") or "")
                    text = "\n".join(x for x in (inp, reply) if x).strip()
            if not text:
                continue
            sources.append({
                "type": "trace",
                "iteration": iteration,
                "trace_id": trace_id,
                "text": text[:600],
            })

        for spec in specs:
            if spec["id"].startswith("sem-rem-"):
                continue
            if spec.get("tag") in ("term", "insight") and float(scores.get(spec["id"], 0.0)) >= 0.5:
                blob = f"{spec.get('title', '')} {spec.get('desc', '')}".strip()
                if blob:
                    sources.append({"type": "node", "id": spec["id"], "text": blob[:240]})
        return sources, to_compact

    def _generate_synthesis(
        self,
        sources: List[dict],
        synthesize_fn: Optional[Callable[[List[dict]], List[str]]],
    ) -> List[str]:
        if not sources:
            return []
        if synthesize_fn:
            try:
                facts = synthesize_fn(sources) or []
                return [str(f).strip() for f in facts if str(f).strip()]
            except Exception:
                pass
        return self._heuristic_facts(sources)

    @staticmethod
    def _heuristic_facts(sources: List[dict]) -> List[str]:
        facts = []
        seen = set()
        for src in sources:
            text = str(src.get("text") or "")
            snippet = text.split("\n", 1)[0].strip()
            if len(snippet) >= 8 and snippet.lower() not in seen:
                seen.add(snippet.lower())
                facts.append(f"经对话沉淀：{snippet[:180]}")
            if len(facts) >= 5:
                break
        return facts or ["近期交互不足以形成新的长期常识节点"]

    def apply_compaction(
        self,
        facts: List[str],
        to_compact: List[dict],
        context: dict,
        report: dict,
        *,
        add_block_fn: Callable[[dict], None],
        remove_traces_fn: Optional[Callable[[List[str], List[int]], int]] = None,
        remove_blocks_fn: Optional[Callable[[Set[int]], int]] = None,
    ):
        if not facts:
            return
        now = float(context.get("now") or time.time())
        batch_id = int(now * 1000)

        for i, fact in enumerate(facts[: self.max_facts], 1):
            block_id = f"sem-rem-{batch_id}-{i}"
            add_block_fn({
                "label": "semantic",
                "block_id": block_id,
                "data": {
                    "content": fact,
                    "label": "REM semantic fact",
                    "keywords": [],
                    "consolidated_at": now,
                    "source_count": len(to_compact),
                    "synthesis": "summary",
                },
                "importance": 0.95,
                "timestamp": now,
            })

        if to_compact:
            trace_ids = [e.get("trace_id") for e in to_compact if e.get("trace_id")]
            iterations = [int(e.get("iteration", 0)) for e in to_compact]
            if remove_traces_fn:
                report["pruned_traces"] = remove_traces_fn(trace_ids, iterations)
            if remove_blocks_fn:
                report["pruned_blocks"] = report.get("pruned_blocks", 0) + remove_blocks_fn(set(iterations))

        report["facts_created"] = min(len(facts), self.max_facts)
        self._audit_rem({
            "phase": "compaction",
            "facts_created": report["facts_created"],
            "compacted_traces": len(to_compact),
        })

    def run_rem_cycle(
        self,
        context: dict,
        *,
        force: bool = False,
        synthesize_fn: Optional[Callable[[List[dict]], List[str]]] = None,
        add_block_fn: Optional[Callable[[dict], None]] = None,
        remove_traces_fn: Optional[Callable] = None,
        remove_blocks_fn: Optional[Callable] = None,
        on_finish: Optional[Callable[[dict], None]] = None,
    ) -> dict:
        consolidation = context.get("consolidation") or {}
        if not self.should_trigger(consolidation, context, force=force):
            return {"ok": True, "skipped": "not_due", "status": self.status(consolidation, context)}

        with self._lock:
            if self.running or consolidation.get("rem_running"):
                return {"ok": True, "skipped": "running", "status": self.status(consolidation, context)}
            self.running = True
            consolidation["rem_running"] = True

        report: Dict[str, Any] = {
            "ok": True,
            "phase": "rem_deep_sleep",
            "started_at": time.time(),
            "pruned_nodes": 0,
            "pruned_blocks": 0,
            "archived_blocks": 0,
            "pruned_traces": 0,
            "facts_created": 0,
            "reanchored": 0,
        }
        try:
            self.synaptic_prune(context, report)
            sources, to_compact = self.collect_compaction_sources(context)
            report["compaction_sources"] = len(sources)
            if sources and add_block_fn:
                facts = self._generate_synthesis(sources, synthesize_fn)
                self.apply_compaction(
                    facts,
                    to_compact,
                    context,
                    report,
                    add_block_fn=add_block_fn,
                    remove_traces_fn=remove_traces_fn,
                    remove_blocks_fn=remove_blocks_fn,
                )
                report["reanchored"] = len(facts)
            else:
                report["skipped_compaction"] = "no_sources"

            consolidation["last_rem_at"] = time.time()
            consolidation["total_pruned"] = int(consolidation.get("total_pruned", 0)) + int(report.get("pruned_nodes", 0))
            consolidation["total_facts"] = int(consolidation.get("total_facts", 0)) + int(report.get("facts_created", 0))
            consolidation["last_rem_report"] = {**report, "finished_at": time.time()}
            self.last_cycle_at = float(consolidation["last_rem_at"])
            self.last_report = dict(consolidation["last_rem_report"])
            self._audit_rem({"phase": "cycle_complete", **report})
            if on_finish:
                on_finish(report)
        except Exception as exc:
            report["ok"] = False
            report["error"] = str(exc)
        finally:
            self.running = False
            consolidation["rem_running"] = False

        report["status"] = self.status(consolidation, context)
        return report

    def status(self, consolidation: Optional[dict] = None, context: Optional[dict] = None) -> dict:
        consolidation = consolidation or {}
        context = context or {}
        specs = context.get("specs") or []
        scores = context.get("scores") or {}
        activation_threshold = float(context.get("activation_threshold", 0.4))
        now = time.time()
        last_at = float(consolidation.get("last_rem_at") or self.last_cycle_at or 0)
        return {
            "enabled": self.enabled,
            "running": bool(self.running or consolidation.get("rem_running")),
            "rem_due": self.should_trigger(consolidation, context) if context else False,
            "threshold": self.threshold,
            "chunk_size": self.chunk_size,
            "last_rem_at": last_at,
            "last_rem_label": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_at)) if last_at else None,
            "last_rem_report": consolidation.get("last_rem_report") or self.last_report,
            "idle_seconds": max(0, int(now - float(consolidation.get("last_activity_at", now)))),
            "node_count": len(specs),
            "active_nodes": sum(
                1 for spec in specs if float(scores.get(spec["id"], 0.0)) > activation_threshold
            ),
            "total_pruned": int(consolidation.get("total_pruned", 0)),
            "total_facts": int(consolidation.get("total_facts", 0)),
            "watchdog_interval_s": self.watchdog_interval,
            "cycle_interval_s": self.cycle_interval,
        }

    def start_watchdog(
        self,
        context_factory: Callable[[], dict],
        *,
        synthesize_fn: Optional[Callable] = None,
        add_block_fn: Optional[Callable] = None,
        remove_traces_fn: Optional[Callable] = None,
        remove_blocks_fn: Optional[Callable] = None,
        on_finish: Optional[Callable] = None,
    ):
        if not self.enabled:
            return

        def _loop():
            while True:
                try:
                    time.sleep(self.watchdog_interval)
                    ctx = context_factory()
                    consolidation = ctx.get("consolidation") or {}
                    if self.should_trigger(consolidation, ctx):
                        self.run_rem_cycle(
                            ctx,
                            synthesize_fn=synthesize_fn,
                            add_block_fn=add_block_fn,
                            remove_traces_fn=remove_traces_fn,
                            remove_blocks_fn=remove_blocks_fn,
                            on_finish=on_finish,
                        )
                except Exception:
                    pass

        threading.Thread(target=_loop, daemon=True, name="cnexus-rem-watchdog").start()
