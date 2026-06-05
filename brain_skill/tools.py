# -*- coding: utf-8 -*-
"""Brain-Memory v5.0 — Agent 工具层"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from config_loader import load_plugin_config
from memory_backend import BrainMemoryBackend

_backend: BrainMemoryBackend | None = None


def _get_backend() -> BrainMemoryBackend:
    global _backend
    if _backend is None:
        _backend = BrainMemoryBackend(load_plugin_config())
    return _backend


def get_tools(backend: BrainMemoryBackend | None = None) -> dict:
    b = backend or _get_backend()
    return {
        "brain_store": lambda role, content, session_id="default", layer="episodic": b.capture(
            role, content, session_id=session_id, layer=layer
        ),
        "brain_recall": b.recall,
        "brain_hyde_recall": lambda query, top_k=None: b.recall(query, top_k=top_k, use_hyde=True),
        "brain_recall_detail": b.recall_detail,
        "brain_multi_hop_recall": lambda query, top_k=None, use_hyde=None: json.dumps(
            b.multi_hop_recall(query, top_k=top_k, use_hyde=use_hyde),
            ensure_ascii=False,
        ),
        "brain_extract_entities": b.extract_entities_and_relations,
        "brain_hebbian_strengthen": b.update_hebbian_edges,
        "brain_reconsolidate": b.full_reconsolidate,
        "brain_consolidate": b.consolidate,
        "brain_forget": lambda max_age_days=90, min_importance=0.3, dry_run=False: json.dumps(
            b.forget(max_age_days=max_age_days, min_importance=min_importance, dry_run=dry_run),
            ensure_ascii=False,
        ),
        "brain_provenance": b.get_provenance,
        "brain_link_provenance": lambda query, answer, cited_ids: b.link_answer_provenance(
            query, answer, cited_ids if isinstance(cited_ids, list) else []
        ),
        "brain_update_goal": lambda goal, importance=0.88, status="active": b.update_goal_memory(
            goal, importance, status=status
        ),
        "brain_reflect": b.run_reflection,
        "brain_update_intent": lambda intent, importance=0.82: b.update_intent_memory(intent, importance),
        "brain_update_plan": lambda plan, importance=0.80: b.update_plan_memory(plan, importance),
        "brain_compress": lambda: b.compress_similar_episodics(),
        "brain_search_time": b.search_time_range,
        "brain_stats": lambda: json.dumps(b.get_stats(), ensure_ascii=False, indent=2),
        "brain_layer_stats": b.get_layer_stats,
        "brain_backfill": b.backfill_chat_history,
        "brain_export": b.export_markdown,
    }


def brain_recall(query: str, top_k: int = 12, use_hyde: bool = True) -> str:
    return _get_backend().recall(query, top_k=top_k, use_hyde=use_hyde)


def brain_hyde_recall(query: str, top_k: int = 12) -> str:
    return _get_backend().recall(query, top_k=top_k, use_hyde=True)


def brain_recall_detail(query: str, top_k: int = 12, use_hyde: bool = True) -> str:
    return json.dumps(_get_backend().recall_detail(query, top_k=top_k, use_hyde=use_hyde), ensure_ascii=False)


def brain_store(role: str, content: str, session_id: str = "default", layer: str = "episodic") -> str:
    return _get_backend().capture(role, content, session_id=session_id, layer=layer)


def brain_extract_entities(content: str) -> str:
    return json.dumps(_get_backend().extract_entities_and_relations(content), ensure_ascii=False)


def brain_consolidate() -> str:
    return _get_backend().consolidate()


def brain_forget(max_age_days: int = 90, min_importance: float = 0.3, dry_run: bool = False) -> str:
    return json.dumps(
        _get_backend().forget(max_age_days=max_age_days, min_importance=min_importance, dry_run=dry_run),
        ensure_ascii=False,
    )


def brain_provenance(mem_id: str) -> str:
    return json.dumps(_get_backend().get_provenance(mem_id), ensure_ascii=False)


def brain_stats() -> str:
    return json.dumps(_get_backend().get_stats(), ensure_ascii=False, indent=2)


def brain_layer_stats() -> str:
    return json.dumps(_get_backend().get_layer_stats(), ensure_ascii=False)


def brain_search_time(start_iso: str, end_iso: str, top_k: int = 50) -> str:
    return _get_backend().search_time_range(start_iso, end_iso, top_k)


def brain_backfill(chat_db_path: str) -> str:
    return f"已回填 {_get_backend().backfill_chat_history(chat_db_path)} 条"


def brain_export(out_path: str = "") -> str:
    return _get_backend().export_markdown(out_path or None)


def _export_all_memories(backend: BrainMemoryBackend) -> str:
    return backend.export_markdown()


def _get_memory_stats(backend: BrainMemoryBackend) -> dict:
    return backend.get_stats()
