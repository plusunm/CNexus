# -*- coding: utf-8 -*-
"""
Brain-Memory Plugin v5.0 — Cognitive Stability Architecture

v4.x: HyDE | Multi-hop | Schema | Reconsolidation | Graph Prune | Semantic Compress
v5.0: Deterministic Router | Attention Half-Life | Belief System | Reflection | Goal Lifecycle
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import kuzu
import lancedb
import numpy as np

logger = logging.getLogger("brain-memory")

try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False

try:
    from apscheduler.schedulers.background import BackgroundScheduler

    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False

import requests


class CaptureFilter:
    """丘脑等效：毫秒级入口过滤 — 在数据进入大脑前丢弃噪声"""

    ROLE_BLOCKLIST = {"toolResult", "tool_error", "system", "debug"}
    MAX_JSON_RATIO = 0.45
    MIN_LEN = 12
    MAX_LEN = 8000
    ENTROPY_THRESHOLD = 6.2

    @staticmethod
    def should_reject(role: str, content: str) -> Tuple[bool, str]:
        if role in CaptureFilter.ROLE_BLOCKLIST:
            return True, f"blocklisted: {role}"
        if len(content) < CaptureFilter.MIN_LEN:
            return True, "too short"
        content = content[: CaptureFilter.MAX_LEN]
        json_ratio = sum(1 for c in content if c in '{}[]":,') / max(len(content), 1)
        if json_ratio > CaptureFilter.MAX_JSON_RATIO:
            return True, "high json"
        freq: Dict[str, int] = {}
        for c in content:
            freq[c] = freq.get(c, 0) + 1
        entropy = -sum(
            (count / len(content)) * math.log2(count / len(content))
            for count in freq.values()
            if count > 0
        )
        if entropy > CaptureFilter.ENTROPY_THRESHOLD:
            return True, "high entropy"
        return False, ""


class DeterministicRouter:
    """Deterministic + Hybrid Router — 关键词 → 嵌入原型 → LLM 兜底"""

    GOAL_KEYWORDS = frozenset({"目标", "计划", "todo", "任务", "长期", "goal", "plan", "intent", "打算", "愿景"})
    SEMANTIC_KEYWORDS = frozenset({"知识", "偏好", "事实", "信念", "习惯", "semantic", "belief", "preference", "原则"})
    ARCHIVE_KEYWORDS = frozenset({"之前", "去年", "archive", "历史", "很久以前", "以前", "当年"})
    REFLECT_KEYWORDS = frozenset({"反思", "总结", "元认知", "meta", "reflect", "复盘", "自我"})
    GRAPH_KEYWORDS = frozenset({"为什么", "how", "why", "关系", "原因", "关联", "推理", "因为"})

    _PROTOTYPE_TEXT = {
        "goal": "用户长期目标 计划 任务 愿景 优先级",
        "semantic": "长期知识 偏好 信念 世界模型 原则",
        "episodic": "具体事件 经历 对话记录 细节",
        "reflect": "自我反思 元认知 总结 矛盾 模式",
    }

    def __init__(self, embedder, llm_caller):
        self.embedder = embedder
        self.llm_caller = llm_caller
        self._prototypes: Dict[str, List[float]] = {}

    def _ensure_prototypes(self) -> None:
        if self._prototypes:
            return
        for intent, text in self._PROTOTYPE_TEXT.items():
            try:
                self._prototypes[intent] = self.embedder(text)
            except Exception:
                self._prototypes[intent] = []

    def classify(self, query: str) -> str:
        q = query.strip()
        ql = q.lower()
        if any(k in ql for k in self.ARCHIVE_KEYWORDS):
            return "archive"
        if any(k in ql for k in self.GOAL_KEYWORDS):
            return "goal"
        if any(k in ql for k in self.REFLECT_KEYWORDS):
            return "reflect"
        if any(k in ql for k in self.SEMANTIC_KEYWORDS):
            return "semantic"
        if len(q) <= 15:
            return "short_term"
        if any(k in ql for k in self.GRAPH_KEYWORDS):
            return "graph_reasoning"

        self._ensure_prototypes()
        try:
            q_vec = self.embedder(q)
            scores: Dict[str, float] = {}
            for intent, proto in self._prototypes.items():
                if proto:
                    scores[intent] = self._cosine_sim(q_vec, proto)
            if scores:
                best = max(scores, key=scores.get)
                if scores[best] >= 0.62:
                    mapped = {
                        "goal": "goal",
                        "semantic": "semantic",
                        "episodic": "episodic",
                        "reflect": "reflect",
                    }
                    return mapped.get(best, "episodic")
        except Exception:
            pass

        try:
            resp = self.llm_caller(
                f"快速分类查询类型，只返回一个词: goal|semantic|episodic|reflect|graph_reasoning\n查询: {q[:220]}"
            ).strip().lower()
            if resp in ("goal", "semantic", "episodic", "reflect"):
                return resp
            if "graph" in resp or "reason" in resp:
                return "graph_reasoning"
            if "archive" in resp:
                return "archive"
        except Exception:
            pass
        return "episodic"

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
        na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))


def _merge_config(config: Optional[Dict]) -> Dict:
    from config_loader import load_plugin_config

    return load_plugin_config(config or {})


def _parse_cron_hour_minute(cron: str) -> tuple[int, int]:
    parts = (cron or "0 3 * * *").split()
    if len(parts) >= 2:
        try:
            return int(parts[1]), int(parts[0])
        except ValueError:
            pass
    return 3, 0


class BrainMemoryBackend:
    """Brain-Memory v5.0 — Cognitive Stability OS"""

    DEFAULT_EMBED_DIM = 768
    VERSION = "5.0.0"
    PROTECTED_LAYERS = frozenset({"schema", "goal", "intent", "plan", "semantic", "meta"})

    def __init__(self, config: Optional[Dict] = None):
        self.config = _merge_config(config)
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(plugin_dir, "memory")
        os.makedirs(self.base_dir, exist_ok=True)

        self.lancedb_path = os.path.join(self.base_dir, "lancedb")
        self.kuzu_path = os.path.join(self.base_dir, "kuzu_db")
        self.meta_path = os.path.join(self.base_dir, "access_meta.json")
        self.provenance_path = os.path.join(self.base_dir, "provenance.json")
        self.summaries_path = os.path.join(self.base_dir, "summaries")
        self.export_path = os.path.join(self.base_dir, "export")

        self.ollama_host = self.config.get("ollama_host", "http://localhost:11434").rstrip("/")
        self.embedding_model = self.config.get("embedding_model", "nomic-embed-text")
        self.llm_model = self.config.get("llm_model", "llama3.2")

        self.recall_top_k = int(self.config.get("recall_top_k", 12))
        self.importance_threshold = float(self.config.get("importance_threshold", 0.52))
        self.forget_alpha = float(self.config.get("forget_alpha", 0.85))
        self.hebbian_strength = float(self.config.get("hebbian_strength", 0.72))
        self.min_capture_len = int(self.config.get("min_capture_len", 8))
        self.reconsolidate_enabled = bool(self.config.get("reconsolidate_enabled", True))
        self.consolidate_enabled = bool(self.config.get("consolidate_enabled", True))
        self.use_hyde_default = bool(self.config.get("use_hyde", True))
        self.deep_reconsolidate_prob = float(self.config.get("deep_reconsolidate_prob", 0.0))
        self.enable_multi_hop = bool(self.config.get("enable_multi_hop", True))
        self.enable_metabolic = bool(self.config.get("enable_metabolic", True))
        self.dedup_similarity = float(self.config.get("dedup_similarity", 0.88))
        self.write_gate_threshold = float(self.config.get("write_gate_threshold", 0.45))
        self.graph_prune_confidence = float(self.config.get("graph_prune_confidence", 0.35))
        self.compress_similarity = float(self.config.get("compress_similarity", 0.90))
        self.attention_half_life = float(self.config.get("attention_half_life", 3600.0))
        self.belief_compat_threshold = float(self.config.get("belief_compat_threshold", 0.72))
        self.reflection_enabled = bool(self.config.get("reflection_enabled", True))

        self._embed_dim = int(self.config.get("embedding_dim", self.DEFAULT_EMBED_DIM))
        self._access_meta: Dict[str, Dict[str, Any]] = {}
        self._provenance: Dict[str, List[Dict]] = {}
        self._edge_meta: Dict[str, Dict[str, Any]] = {}
        self._beliefs: Dict[str, Dict[str, Any]] = {}
        self._goal_lifecycle: Dict[str, Dict[str, Any]] = {}
        self._self_model: Dict[str, Any] = {
            "identity": str(self.config.get("agent_identity", "helpful cognitive agent")),
            "core_values": list(self.config.get("core_values") or []),
            "stability_score": 1.0,
        }
        self._session_last_id: Dict[str, str] = {}
        self._short_term: OrderedDict[str, Dict] = OrderedDict()
        self._short_term_capacity = int(self.config.get("short_term_capacity", 32))
        self._schema_cols: Set[str] = set()
        self._meta_lock = threading.Lock()
        self._scheduler = None
        self._route_stats: Dict[str, int] = {}
        self._stats = {
            "captured": 0,
            "recalled": 0,
            "consolidated": 0,
            "forgotten": 0,
            "compressed": 0,
            "pruned_edges": 0,
            "write_gate_rejected": 0,
            "belief_conflicts": 0,
            "reflections": 0,
            "hyde_calls": 0,
        }

        self.edge_meta_path = os.path.join(self.base_dir, "edge_meta.json")
        self.beliefs_path = os.path.join(self.base_dir, "beliefs.json")
        self.self_model_path = os.path.join(self.base_dir, "self_model.json")
        self.goal_lifecycle_path = os.path.join(self.base_dir, "goal_lifecycle.json")

        self._init_llm_clients()
        self._init_vector_store()
        self._migrate_schema()
        self._init_graph_store()
        self._load_access_meta()
        self._load_provenance()
        self._load_edge_meta()
        self._load_beliefs()
        self._load_self_model()
        self._load_goal_lifecycle()
        os.makedirs(self.summaries_path, exist_ok=True)
        os.makedirs(self.export_path, exist_ok=True)
        self.query_router = DeterministicRouter(self._ollama_embed, self._ollama_chat)
        self._start_scheduler()

        logger.info("Brain-Memory v5.0 Cognitive Stability loaded (ollama=%s)", self.ollama_host)
        if not os.environ.get("BRAIN_MEMORY_QUIET"):
            print("Brain-Memory v5.0 Cognitive Stability OS 已就绪")

    # ==================== 初始化 ====================

    def _init_llm_clients(self) -> None:
        self._embeddings = None
        self._llm = None
        if _HAS_LANGCHAIN:
            try:
                self._embeddings = OllamaEmbeddings(
                    model=self.embedding_model,
                    base_url=self.ollama_host,
                )
                self._llm = ChatOllama(
                    model=self.llm_model,
                    base_url=self.ollama_host,
                    temperature=0.12,
                )
            except Exception as ex:
                logger.warning("langchain-ollama init failed: %s", ex)

    def _init_vector_store(self) -> None:
        self.db = lancedb.connect(self.lancedb_path)
        self.table_name = "brain_chat_memory"
        existing = self.db.list_tables().tables
        if self.table_name not in existing:
            sample = [{
                "id": "__init__",
                "timestamp": "1970-01-01T00:00:00",
                "role": "system",
                "content": "init",
                "importance": 0.0,
                "vector": [0.0] * self._embed_dim,
                "session_id": "init",
                "last_access": "1970-01-01T00:00:00",
                "access_count": 0,
                "layer": "episodic",
            }]
            self.table = self.db.create_table(self.table_name, data=sample)
            self.table.delete('id = "__init__"')
        else:
            self.table = self.db.open_table(self.table_name)
        self._refresh_schema_cols()

    def _refresh_schema_cols(self) -> None:
        try:
            self._schema_cols = set(self.table.schema.names)
        except Exception:
            self._schema_cols = set()

    def _migrate_schema(self) -> None:
        """v3 → v4：安全添加 last_access / access_count / layer"""
        self._refresh_schema_cols()
        additions = {}
        if "last_access" not in self._schema_cols:
            additions["last_access"] = "cast(NULL as string)"
        if "access_count" not in self._schema_cols:
            additions["access_count"] = "cast(1 as int)"
        if "layer" not in self._schema_cols:
            additions["layer"] = "'episodic'"
        if not additions:
            return
        try:
            self.table.add_columns(additions)
            self._refresh_schema_cols()
            print("LanceDB schema migrated:", list(additions.keys()))
        except Exception as ex:
            logger.info("schema migrate skipped (using access_meta sidecar): %s", ex)

    def _init_graph_store(self) -> None:
        self.graph_db = kuzu.Database(self.kuzu_path)
        self.graph_conn = kuzu.Connection(self.graph_db)
        self.graph_conn.execute(
            """
            CREATE NODE TABLE IF NOT EXISTS ChatNode (
                id STRING PRIMARY KEY,
                timestamp STRING,
                role STRING,
                content STRING,
                importance FLOAT,
                session_id STRING,
                layer STRING
            )
            """
        )
        try:
            self.graph_conn.execute("ALTER TABLE ChatNode ADD layer STRING")
        except Exception:
            pass
        self.graph_conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS RELATED (
                FROM ChatNode TO ChatNode,
                weight FLOAT
            )
            """
        )
        try:
            self.graph_conn.execute(
                "CREATE REL TABLE IF NOT EXISTS HEBBIAN (FROM ChatNode TO ChatNode, weight FLOAT, last_coactivate STRING)"
            )
        except Exception:
            pass
        try:
            self.graph_conn.execute(
                "CREATE REL TABLE IF NOT EXISTS PROVENANCE (FROM ChatNode TO ChatNode, contribution FLOAT)"
            )
        except Exception:
            pass
        for rel in ("FOLLOWS", "EXPLAINS", "CONFLICTS", "COMPILED_FROM", "SUPPORTED_BY"):
            try:
                self.graph_conn.execute(
                    f"CREATE REL TABLE IF NOT EXISTS {rel} (FROM ChatNode TO ChatNode, weight FLOAT)"
                )
            except Exception:
                pass

    def _load_access_meta(self) -> None:
        if os.path.isfile(self.meta_path):
            try:
                with open(self.meta_path, encoding="utf-8") as f:
                    self._access_meta = json.load(f)
            except Exception:
                self._access_meta = {}

    def _load_provenance(self) -> None:
        if os.path.isfile(self.provenance_path):
            try:
                with open(self.provenance_path, encoding="utf-8") as f:
                    self._provenance = json.load(f)
            except Exception:
                self._provenance = {}

    def _save_access_meta(self) -> None:
        with self._meta_lock:
            try:
                with open(self.meta_path, "w", encoding="utf-8") as f:
                    json.dump(self._access_meta, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save access_meta failed: %s", ex)

    def _save_provenance(self) -> None:
        with self._meta_lock:
            try:
                with open(self.provenance_path, "w", encoding="utf-8") as f:
                    json.dump(self._provenance, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save provenance failed: %s", ex)

    def _load_edge_meta(self) -> None:
        if os.path.isfile(self.edge_meta_path):
            try:
                with open(self.edge_meta_path, encoding="utf-8") as f:
                    self._edge_meta = json.load(f)
            except Exception:
                self._edge_meta = {}

    def _save_edge_meta(self) -> None:
        with self._meta_lock:
            try:
                with open(self.edge_meta_path, "w", encoding="utf-8") as f:
                    json.dump(self._edge_meta, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save edge_meta failed: %s", ex)

    def _record_edge(self, rel: str, src: str, tgt: str, weight: float, confidence: Optional[float] = None) -> None:
        key = f"{rel}:{src}:{tgt}"
        conf = confidence if confidence is not None else min(1.0, max(0.3, weight))
        with self._meta_lock:
            cur = self._edge_meta.get(key, {})
            self._edge_meta[key] = {
                "rel": rel,
                "src": src,
                "tgt": tgt,
                "weight": float(weight),
                "confidence": max(float(cur.get("confidence", 0)), conf),
                "last_verified": datetime.now().isoformat(),
            }
        self._save_edge_meta()

    def _load_beliefs(self) -> None:
        if os.path.isfile(self.beliefs_path):
            try:
                with open(self.beliefs_path, encoding="utf-8") as f:
                    self._beliefs = json.load(f)
            except Exception:
                self._beliefs = {}

    def _save_beliefs(self) -> None:
        with self._meta_lock:
            try:
                with open(self.beliefs_path, "w", encoding="utf-8") as f:
                    json.dump(self._beliefs, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save beliefs failed: %s", ex)

    def _load_self_model(self) -> None:
        if os.path.isfile(self.self_model_path):
            try:
                with open(self.self_model_path, encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._self_model.update(loaded)
            except Exception:
                pass

    def _save_self_model(self) -> None:
        with self._meta_lock:
            try:
                with open(self.self_model_path, "w", encoding="utf-8") as f:
                    json.dump(self._self_model, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save self_model failed: %s", ex)

    def _load_goal_lifecycle(self) -> None:
        if os.path.isfile(self.goal_lifecycle_path):
            try:
                with open(self.goal_lifecycle_path, encoding="utf-8") as f:
                    self._goal_lifecycle = json.load(f)
            except Exception:
                self._goal_lifecycle = {}

    def _save_goal_lifecycle(self) -> None:
        with self._meta_lock:
            try:
                with open(self.goal_lifecycle_path, "w", encoding="utf-8") as f:
                    json.dump(self._goal_lifecycle, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.warning("save goal_lifecycle failed: %s", ex)

    def _update_belief(self, key: str, content: str, confidence: float, source_id: str = "") -> None:
        key = key.strip()[:80] or "general"
        now = datetime.now().isoformat()
        with self._meta_lock:
            cur = self._beliefs.get(key, {})
            old_conf = float(cur.get("confidence", 0))
            evidence = int(cur.get("evidence", 0)) + 1
            merged_conf = (old_conf + confidence) / 2 if cur else confidence
            self._beliefs[key] = {
                "content": content[:2000],
                "confidence": round(min(1.0, merged_conf), 4),
                "evidence": evidence,
                "updated_at": now,
                "source_id": source_id or cur.get("source_id", ""),
            }
        self._save_beliefs()
        self._enforce_identity_stability()

    def _check_belief_compatibility(self, content: str) -> Tuple[bool, str]:
        """高置信信念冲突检测（轻量关键词 + 可选 LLM）"""
        text = content.strip()
        if len(text) < 20:
            return True, ""
        for key, belief in list(self._beliefs.items())[:12]:
            conf = float(belief.get("confidence", 0))
            if conf < self.belief_compat_threshold:
                continue
            old = str(belief.get("content", ""))
            if not old or len(old) < 12:
                continue
            neg_markers = ("不是", "不再", "取消", "错误", "相反", "never", "not ")
            if any(m in text for m in neg_markers) and any(w in old for w in text.split()[:6] if len(w) > 2):
                prompt = (
                    f"判断新陈述是否与已有信念矛盾（只回答 compatible 或 conflict）：\n"
                    f"信念: {old[:300]}\n新陈述: {text[:300]}"
                )
                try:
                    resp = self._ollama_chat(prompt).strip().lower()
                    if "conflict" in resp and "compatible" not in resp:
                        return False, key
                except Exception:
                    pass
        return True, ""

    def _enforce_identity_stability(self) -> None:
        if not self._beliefs:
            self._self_model["stability_score"] = 1.0
            self._save_self_model()
            return
        confidences = [float(b.get("confidence", 0.5)) for b in self._beliefs.values()]
        spread = max(confidences) - min(confidences) if confidences else 0
        avg = sum(confidences) / len(confidences)
        stability = max(0.0, min(1.0, 0.55 * avg + 0.45 * (1.0 - spread)))
        self._self_model["stability_score"] = round(stability, 3)
        self._save_self_model()
        if stability < 0.68 and self.reflection_enabled:
            logger.warning("Identity stability low (%.2f) — schedule reflection", stability)

    def run_reflection(self) -> str:
        """Meta-Memory 反思引擎"""
        if not self.reflection_enabled:
            return "reflection_disabled"
        rows = sorted(
            [r for r in self._rows_from_table(limit=400) if float(r.get("importance", 0)) > 0.55],
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )[:20]
        if not rows:
            return "no_data_for_reflection"
        prompt = "总结以下记忆的模式、潜在矛盾与可改进点（中文，200字内）：\n"
        for r in rows[:12]:
            prompt += f"- {str(r.get('content', ''))[:180]}\n"
        summary = self._ollama_chat(prompt)
        if not summary:
            return "reflection_failed"
        self.capture(
            "system",
            f"[Meta-Reflection] {summary[:1200]}",
            layer="meta",
            metadata={"importance": 0.92},
        )
        self._update_belief("meta_reflection", summary[:800], 0.78)
        self._stats["reflections"] += 1
        return summary[:600]

    def _register_goal_lifecycle(self, mem_id: str, goal_text: str, status: str, priority: float) -> None:
        now = datetime.now().isoformat()
        self._goal_lifecycle[mem_id] = {
            "text": goal_text[:500],
            "status": status,
            "priority": float(priority),
            "created_at": now,
            "updated_at": now,
        }
        self._save_goal_lifecycle()
        try:
            self.graph_conn.execute(
                """
                MATCH (g:ChatNode {id: $id})
                SET g.layer = 'goal'
                """,
                {"id": mem_id},
            )
        except Exception:
            pass

    def _start_scheduler(self) -> None:
        if not _HAS_APSCHEDULER or not self.consolidate_enabled:
            return
        if self.config.get("scheduler_enabled", True) is False:
            return
        hour, minute = _parse_cron_hour_minute(self.config.get("consolidate_cron", "0 3 * * *"))
        try:
            self._scheduler = BackgroundScheduler(daemon=True)
            self._scheduler.add_job(
                self.consolidate,
                "cron",
                hour=hour,
                minute=minute,
                id="brain_nightly_consolidation",
                replace_existing=True,
            )
            self._scheduler.start()
            print(f"Scheduler started: consolidate daily at {hour:02d}:{minute:02d}")
        except Exception as ex:
            logger.warning("scheduler start failed: %s", ex)

    # ==================== LLM ====================

    def _ollama_embed(self, text: str) -> List[float]:
        try:
            resp = requests.post(
                f"{self.ollama_host}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=90,
            )
            if resp.status_code == 200:
                vec = resp.json().get("embedding") or []
                if vec:
                    self._embed_dim = len(vec)
                    return vec
        except Exception as ex:
            logger.warning("ollama embed failed: %s", ex)
        if self._embeddings is not None:
            try:
                vec = self._embeddings.embed_query(text)
                if vec:
                    self._embed_dim = len(vec)
                    return vec
            except Exception as ex:
                logger.warning("langchain embed failed: %s", ex)
        return [0.0] * self._embed_dim

    def _ollama_chat(self, prompt: str, system: str = "") -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = requests.post(
                f"{self.ollama_host}/api/chat",
                json={"model": self.llm_model, "messages": messages, "stream": False},
                timeout=180,
            )
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "").strip()
        except Exception as ex:
            logger.warning("ollama chat failed: %s", ex)
        if self._llm is not None:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                msgs = []
                if system:
                    msgs.append(SystemMessage(content=system))
                msgs.append(HumanMessage(content=prompt))
                resp = self._llm.invoke(msgs)
                return (resp.content or "").strip()
            except Exception as ex:
                logger.warning("langchain chat failed: %s", ex)
        return ""

    def _get_importance(self, content: str) -> float:
        if len(content.strip()) < self.min_capture_len:
            return 0.3
        resp = self._ollama_chat(
            f"评估这段聊天内容对用户长期价值的重要性 (0.0-1.0，只返回数字):\n{content[:700]}"
        )
        match = re.search(r"0\.\d+|1\.0|1|0", resp or "")
        if match:
            return max(0.1, min(1.0, float(match.group())))
        return 0.65

    def _hyde_generate(self, query: str) -> str:
        """HyDE：生成假设记忆片段以对齐嵌入空间"""
        prompt = (
            "根据以下查询，生成一段详细、具体的「假设用户曾经经历过的相关记忆片段」"
            "（不要直接回答问题，而是像回忆历史一样描述）。\n"
            f"查询: {query}\n\n假设记忆（中文，250字左右）："
        )
        doc = self._ollama_chat(prompt)
        self._stats["hyde_calls"] += 1
        return doc.strip() if doc else query

    def extract_entities_and_relations(self, content: str) -> List[Dict]:
        """LLM 实体+关系抽取（Hebbian 图增强基础）"""
        prompt = (
            "从以下文本抽取重要实体和关系，只返回 JSON 数组，无其他文字：\n"
            f"{content[:1300]}\n\n"
            '格式: [{"entity1":"A","entity2":"B","relation":"描述","strength":0.8}]'
        )
        raw = self._ollama_chat(prompt)
        if not raw:
            return []
        try:
            m = re.search(r"\[[\s\S]*\]", raw)
            data = json.loads(m.group() if m else raw)
            if not isinstance(data, list):
                return []
            return [x for x in data if isinstance(x, dict)]
        except Exception:
            return []

    # 兼容 tools 别名
    _extract_entities_and_relations = extract_entities_and_relations

    # ==================== 工具 ====================

    @staticmethod
    def _row_to_dict(row: Any) -> Optional[Dict]:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if hasattr(row, "_asdict"):
            return row._asdict()
        if hasattr(row, "to_dict"):
            return row.to_dict()
        return None

    def _rows_from_table(self, limit: int = 500) -> List[Dict]:
        try:
            df = self.table.to_pandas()
            if df is not None and len(df) > 0:
                return [r for r in df.head(limit).to_dict("records") if r.get("id") != "__init__"]
        except Exception:
            pass
        try:
            raw = self.table.search([0.0] * self._embed_dim).limit(limit).to_list()
        except Exception:
            return []
        out = []
        for r in raw:
            d = self._row_to_dict(r)
            if d and d.get("id") != "__init__":
                out.append(d)
        return out

    def _parse_ts(self, ts: str) -> datetime:
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00")[:26])
        except Exception:
            return datetime.now()

    def _get_layer(self, mem_id: str, row: Optional[Dict] = None) -> str:
        if row and row.get("layer"):
            return str(row["layer"])
        return str(self._access_meta.get(mem_id, {}).get("layer", "episodic"))

    def _get_access(self, mem_id: str, default_ts: str, row: Optional[Dict] = None) -> Dict[str, Any]:
        if row:
            if "access_count" in row and row.get("access_count") is not None:
                return {
                    "access_count": int(row["access_count"]),
                    "last_access": str(row.get("last_access") or default_ts),
                }
        meta = self._access_meta.get(mem_id, {})
        return {
            "access_count": int(meta.get("access_count", 1)),
            "last_access": meta.get("last_access", default_ts),
        }

    def _touch_access(self, mem_id: str, layer: str = "episodic") -> None:
        now = datetime.now().isoformat()
        with self._meta_lock:
            cur = self._access_meta.get(mem_id, {"access_count": 0, "last_access": now, "layer": layer})
            cur["access_count"] = int(cur.get("access_count", 0)) + 1
            cur["last_access"] = now
            cur["layer"] = layer
            self._access_meta[mem_id] = cur
        self._save_access_meta()
        if "access_count" in self._schema_cols:
            try:
                safe_id = mem_id.replace("'", "''")
                cnt = self._access_meta[mem_id]["access_count"]
                self.table.update(
                    where=f"id = '{safe_id}'",
                    values={"last_access": now, "access_count": cnt},
                )
            except Exception:
                pass

    def _compute_attention_score(self, record: Dict, current_context: str = "") -> float:
        recency = 1.0
        if record.get("timestamp"):
            age_hours = (datetime.now() - self._parse_ts(str(record["timestamp"]))).total_seconds() / 3600
            recency = max(0.05, math.exp(-age_hours * 0.08))
        imp = float(record.get("importance", 0.5))
        content = str(record.get("content", "")).lower()
        emotional = 0.72 if any(x in content for x in ("!", "激动", "生气", "开心", "难过", "重要", "必须")) else 0.5
        goal_rel = 0.65 if any(x in content for x in ("目标", "计划", "goal", "intent")) else 0.45
        ctx_sim = 0.4
        if current_context and record.get("vector"):
            try:
                ctx_vec = self._ollama_embed(current_context[:180])
                ctx_sim = self._cosine_sim(ctx_vec, record["vector"])
            except Exception:
                pass
        return 0.38 * recency + 0.30 * imp + 0.12 * emotional + 0.10 * goal_rel + 0.10 * ctx_sim

    def _decay_attention_field(self) -> None:
        """Dynamic Attention Field — 半衰期衰减"""
        now = time.time()
        half = max(60.0, self.attention_half_life)
        for mid in list(self._short_term.keys()):
            rec = self._short_term[mid]
            last = float(rec.get("_last_focus", now))
            delta = now - last
            rec["_attention"] = float(rec.get("_attention", 1.0)) * math.exp(-delta / half)
            if rec["_attention"] < 0.08:
                self._short_term.pop(mid, None)

    def _add_short_term(self, mem_id: str, record: Dict, context: str = "") -> None:
        self._decay_attention_field()
        record["_attention"] = self._compute_attention_score(record, context)
        record["_last_focus"] = time.time()
        if mem_id in self._short_term:
            self._short_term.move_to_end(mem_id)
            self._short_term[mem_id].update({
                "_attention": record["_attention"],
                "_last_focus": record["_last_focus"],
            })
        else:
            self._short_term[mem_id] = record
            if len(self._short_term) > self._short_term_capacity:
                weakest = min(self._short_term.items(), key=lambda x: x[1].get("_attention", 0))
                self._short_term.pop(weakest[0])

    def _short_term_hits(self, query: str, limit: int = 8) -> List[Dict]:
        self._decay_attention_field()
        q = query.lower()
        hits = []
        for rec in self._short_term.values():
            if q in str(rec.get("content", "")).lower():
                hits.append(rec)
        hits.sort(key=lambda x: x.get("_attention", 0), reverse=True)
        return hits[:limit]

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
        na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))

    def _quick_dedup_and_merge(self, vector: List[float], content: str) -> bool:
        """模式压缩：高相似记忆 Hebbian 强化，不新增记录"""
        try:
            results = self.table.search(vector).limit(3).to_list()
        except Exception:
            return False
        for r in results:
            d = self._row_to_dict(r)
            if not d or not d.get("vector"):
                continue
            if self._cosine_sim(vector, d["vector"]) > self.dedup_similarity:
                self._hebbian_merge_existing(d, content)
                return True
        return False

    def _hebbian_merge_existing(self, existing: Dict, new_content: str) -> None:
        mem_id = str(existing.get("id", ""))
        if not mem_id:
            return
        updated_imp = min(1.0, float(existing.get("importance", 0.5)) * 1.08)
        safe_id = mem_id.replace("'", "''")
        now = datetime.now().isoformat()
        try:
            self.table.update(
                where=f"id = '{safe_id}'",
                values={"importance": updated_imp, "last_access": now},
            )
        except Exception:
            pass
        self._touch_access(mem_id, layer=self._get_layer(mem_id, existing))
        try:
            self.graph_conn.execute(
                "MATCH (n:ChatNode {id: $id}) SET n.importance = $imp, n.last_access = $ts",
                {"id": mem_id, "imp": updated_imp, "ts": now},
            )
        except Exception:
            pass

    def _auto_build_cognitive_relations(self, mem_id: str, content: str, vector: List[float]) -> None:
        """v4 认知图：语义相似节点自动建 RELATED + FOLLOWS"""
        try:
            candidates = self.table.search(vector).limit(8).to_list()
        except Exception:
            return
        now = datetime.now().isoformat()
        for cand in candidates:
            d = self._row_to_dict(cand)
            if not d or str(d.get("id")) == mem_id or not d.get("vector"):
                continue
            sim = self._cosine_sim(vector, d["vector"])
            if sim < 0.72:
                continue
            cid = str(d["id"])
            weight = float(sim * float(d.get("importance", 0.5)))
            try:
                self.graph_conn.execute(
                    """
                    MATCH (a:ChatNode {id: $a}), (b:ChatNode {id: $b})
                    CREATE (a)-[:RELATED {weight: $w}]->(b)
                    """,
                    {"a": mem_id, "b": cid, "w": weight},
                )
                self._record_edge("RELATED", mem_id, cid, weight, confidence=sim)
            except Exception:
                pass
            try:
                t1 = self._parse_ts(str(d.get("timestamp", now)))
                t2 = self._parse_ts(now)
                if abs((t2 - t1).total_seconds()) < 3600:
                    self.graph_conn.execute(
                        """
                        MATCH (a:ChatNode {id: $a}), (b:ChatNode {id: $b})
                        CREATE (a)-[:FOLLOWS {weight: $w}]->(b)
                        """,
                        {"a": mem_id, "b": cid, "w": weight * 0.8},
                    )
                    self._record_edge("FOLLOWS", mem_id, cid, weight * 0.8, confidence=sim * 0.9)
            except Exception:
                pass

    def _get_all_schemas(self) -> str:
        """Schema 层强制注入 recall 上下文"""
        try:
            dummy = [0.0] * self._embed_dim
            rows = self.table.search(dummy).where("layer = 'schema'").limit(10).to_list()
        except Exception:
            rows = []
        if not rows:
            for r in self._rows_from_table(limit=500):
                if self._get_layer(str(r.get("id", "")), r) == "schema":
                    rows.append(r)
        if not rows:
            return ""
        parts = []
        for r in rows[:10]:
            d = self._row_to_dict(r) or r
            parts.append(str(d.get("content", "")))
        return "\n".join(p for p in parts if p)

    # ==================== OpenClaw 钩子 ====================

    def on_message(self, message: Dict) -> None:
        if not self.config.get("auto_capture", True):
            return
        role = message.get("role") or message.get("sender") or "user"
        content = message.get("content") or message.get("text") or ""
        session_id = message.get("session_id") or message.get("channel") or "default"
        layer = message.get("layer") or "episodic"
        if content.strip():
            self.capture(role, content, session_id=session_id, layer=layer)

    def before_llm_call(self, query: str) -> Dict:
        if not self.config.get("auto_recall", True):
            return {}
        detail = self.recall_detail(query, use_hyde=self.use_hyde_default)
        if detail.get("context"):
            return {
                "memory_context": detail["context"],
                "memory_provenance": detail.get("provenance", {}),
                "memory_timestamp": datetime.now().isoformat(),
                "short_term_used": detail.get("short_term_used", False),
                "memory_route": detail.get("route", "unknown"),
            }
        return {}

    # ==================== 编码 ====================

    def capture(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        layer: str = "episodic",
        metadata: Optional[Dict] = None,
    ) -> str:
        if not content or len(content.strip()) < self.min_capture_len:
            return "too_short"

        reject, reason = CaptureFilter.should_reject(role, content.strip())
        if reject:
            return f"filtered: {reason}"

        ts = datetime.now().isoformat()
        memory_id = f"{ts}_{abs(hash(content)) % 1000000:06d}"
        importance = self._get_importance(content)
        if metadata and "importance" in metadata:
            importance = float(metadata["importance"])
        if metadata and "layer" in metadata:
            layer = str(metadata["layer"])

        protected_layer = layer in self.PROTECTED_LAYERS or role == "system"
        if not protected_layer and importance < self.write_gate_threshold:
            self._stats["write_gate_rejected"] += 1
            return "write_gate_rejected"

        if layer == "episodic" and role not in ("system",):
            ok, conflict_key = self._check_belief_compatibility(content)
            if not ok:
                self._stats["belief_conflicts"] += 1
                return f"belief_conflict:{conflict_key}"

        vector = self._ollama_embed(content)
        if self._quick_dedup_and_merge(vector, content):
            return "merged"

        record: Dict[str, Any] = {
            "id": memory_id,
            "timestamp": ts,
            "role": role,
            "content": content,
            "importance": importance,
            "vector": vector,
            "session_id": session_id,
        }
        if "last_access" in self._schema_cols:
            record["last_access"] = ts
        if "access_count" in self._schema_cols:
            record["access_count"] = 1
        if "layer" in self._schema_cols:
            record["layer"] = layer

        self.table.add([record])
        self._touch_access(memory_id, layer=layer)
        self._add_short_term(memory_id, record, content)
        self._graph_insert_node(memory_id, ts, role, content, importance, session_id, layer)
        self._graph_link_sequential(memory_id, session_id, importance)
        self.update_hebbian_edges(memory_id, content)
        self._auto_build_cognitive_relations(memory_id, content, vector)
        if layer in ("semantic", "schema"):
            self._update_belief(f"layer_{layer}", content[:800], importance, memory_id)
        if layer == "goal":
            goal_status = str((metadata or {}).get("status", "active"))
            self._register_goal_lifecycle(memory_id, content, status=goal_status, priority=importance)
        self._stats["captured"] += 1
        return memory_id

    def _graph_insert_node(
        self, mem_id: str, ts: str, role: str, content: str,
        importance: float, session_id: str, layer: str,
    ) -> None:
        try:
            self.graph_conn.execute(
                """
                CREATE (n:ChatNode {
                    id: $id, timestamp: $ts, role: $role,
                    content: $content, importance: $imp, session_id: $sid, layer: $layer
                })
                """,
                {
                    "id": mem_id, "ts": ts, "role": role,
                    "content": content[:2000], "imp": importance,
                    "sid": session_id, "layer": layer,
                },
            )
        except Exception:
            try:
                self.graph_conn.execute(
                    """
                    CREATE (n:ChatNode {
                        id: $id, timestamp: $ts, role: $role,
                        content: $content, importance: $imp, session_id: $sid
                    })
                    """,
                    {
                        "id": mem_id, "ts": ts, "role": role,
                        "content": content[:2000], "imp": importance, "sid": session_id,
                    },
                )
            except Exception as ex:
                logger.debug("graph insert: %s", ex)

    def _graph_link_sequential(self, mem_id: str, session_id: str, importance: float) -> None:
        prev_id = self._session_last_id.get(session_id)
        if not prev_id or prev_id == mem_id:
            self._session_last_id[session_id] = mem_id
            return
        weight = importance * self.hebbian_strength
        now = datetime.now().isoformat()
        try:
            self.graph_conn.execute(
                """
                MATCH (a:ChatNode {id: $from_id}), (b:ChatNode {id: $to_id})
                CREATE (a)-[:RELATED {weight: $w}]->(b)
                """,
                {"from_id": prev_id, "to_id": mem_id, "w": weight},
            )
            self._record_edge("RELATED", prev_id, mem_id, weight)
        except Exception:
            pass
        try:
            self.graph_conn.execute(
                """
                MATCH (a:ChatNode {id: $from_id}), (b:ChatNode {id: $to_id})
                CREATE (a)-[:HEBBIAN {weight: $w, last_coactivate: $ts}]->(b)
                """,
                {"from_id": prev_id, "to_id": mem_id, "w": weight, "ts": now},
            )
            self._record_edge("HEBBIAN", prev_id, mem_id, weight)
        except Exception:
            pass
        self._session_last_id[session_id] = mem_id

    def update_hebbian_edges(self, mem_id: str, content: str) -> None:
        """实体关系 → 图边强化"""
        relations = self.extract_entities_and_relations(content)
        if not relations:
            return
        now = datetime.now().isoformat()
        rows = self._rows_from_table(limit=800)
        for rel in relations[:6]:
            if not isinstance(rel, dict):
                continue
            e2 = str(rel.get("entity2") or rel.get("entity1") or "").strip()
            if len(e2) < 2:
                continue
            w = float(rel.get("strength") or 0.75) * self.hebbian_strength
            for row in rows:
                rid = str(row.get("id", ""))
                if not rid or rid == mem_id:
                    continue
                if e2 in str(row.get("content", "")):
                    try:
                        self.graph_conn.execute(
                            """
                            MATCH (a:ChatNode {id: $a}), (b:ChatNode {id: $b})
                            CREATE (a)-[:HEBBIAN {weight: $w, last_coactivate: $ts}]->(b)
                            """,
                            {"a": mem_id, "b": rid, "w": w, "ts": now},
                        )
                    except Exception:
                        pass
                    self._record_provenance(rid, mem_id, w)

    _update_hebbian_edges = update_hebbian_edges

    def _graph_neighbors(self, mem_ids: List[str]) -> Set[str]:
        found: Set[str] = set()
        for mid in mem_ids[:8]:
            for rel in ("RELATED", "HEBBIAN"):
                try:
                    result = self.graph_conn.execute(
                        f"""
                        MATCH (a:ChatNode {{id: $id}})-[r:{rel}]-(b:ChatNode)
                        RETURN b.id, r.weight
                        LIMIT 12
                        """,
                        {"id": mid},
                    )
                    while result.has_next():
                        row = result.get_next()
                        if row and len(row) >= 2 and float(row[1]) >= 0.15:
                            found.add(str(row[0]))
                except Exception:
                    pass
        return found

    def _hebbian_strengthen_batch(self, mem_ids: List[str]) -> None:
        if len(mem_ids) < 2:
            return
        now = datetime.now().isoformat()
        for i in range(len(mem_ids) - 1):
            a, b = mem_ids[i], mem_ids[i + 1]
            try:
                self.graph_conn.execute(
                    """
                    MATCH (x:ChatNode {id: $a}), (y:ChatNode {id: $b})
                    CREATE (x)-[:HEBBIAN {weight: $w, last_coactivate: $ts}]->(y)
                    """,
                    {"a": a, "b": b, "w": self.hebbian_strength, "ts": now},
                )
            except Exception:
                pass

    def _record_provenance(self, target_id: str, source_id: str, contribution: float) -> None:
        with self._meta_lock:
            chain = self._provenance.setdefault(target_id, [])
            for item in chain:
                if item.get("source_id") == source_id:
                    item["contribution"] = max(float(item["contribution"]), contribution)
                    break
            else:
                chain.append({"source_id": source_id, "contribution": round(contribution, 4)})
        self._save_provenance()
        try:
            self.graph_conn.execute(
                """
                MATCH (a:ChatNode {id: $src}), (b:ChatNode {id: $tgt})
                CREATE (a)-[:PROVENANCE {contribution: $c}]->(b)
                """,
                {"src": source_id, "tgt": target_id, "c": contribution},
            )
        except Exception:
            pass

    def get_provenance(self, mem_id: str) -> List[Dict]:
        """记忆溯源链"""
        out = list(self._provenance.get(mem_id, []))
        try:
            result = self.graph_conn.execute(
                """
                MATCH (a:ChatNode)-[r:PROVENANCE]->(b:ChatNode {id: $id})
                RETURN a.id, r.contribution
                LIMIT 20
                """,
                {"id": mem_id},
            )
            while result.has_next():
                row = result.get_next()
                if row:
                    out.append({"source_id": str(row[0]), "contribution": float(row[1])})
        except Exception:
            pass
        return out

    _get_provenance = get_provenance

    # ==================== 检索 ====================

    def recall(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_hyde: Optional[bool] = None,
    ) -> str:
        return self.recall_detail(query, top_k=top_k, use_hyde=use_hyde).get("context", "")

    def multi_hop_recall(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_hyde: Optional[bool] = None,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """v4 多跳推理：HyDE 向量 + Kuzu 图遍历 + Schema 注入"""
        if top_k is None:
            top_k = self.recall_top_k
        use_hyde = self.use_hyde_default if use_hyde is None else use_hyde
        search_text = query
        if use_hyde:
            search_text = f"{query}\n{self._hyde_generate(query)}"
        query_vec = self._ollama_embed(search_text)

        vector_items: List[Dict] = []
        seen: Set[str] = set()
        try:
            for r in self.table.search(query_vec).limit(top_k * 3).to_list():
                d = self._row_to_dict(r) or {}
                mid = str(d.get("id", ""))
                if mid and mid not in seen:
                    d["hops"] = 1
                    d["_distance"] = float(d.get("_distance", 0.5))
                    vector_items.append(d)
                    seen.add(mid)
        except Exception:
            pass

        for hit in self._short_term_hits(query):
            hid = str(hit.get("id", ""))
            if hid and hid not in seen:
                hit["hops"] = 0
                hit["_short_term_boost"] = 0.25
                vector_items.insert(0, hit)
                seen.add(hid)

        entities = self._extract_query_entities(query)
        graph_items: List[Dict] = []
        for entity in entities[:3]:
            try:
                result = self.graph_conn.execute(
                    f"""
                    MATCH (n:ChatNode)
                    WHERE n.content CONTAINS $entity
                    WITH n
                    MATCH path = (n)-[*1..{max_hops}]-(m:ChatNode)
                    RETURN m.id AS id, m.content AS content, m.importance AS importance,
                           m.layer AS layer, length(path) AS hops
                    ORDER BY m.importance DESC, hops ASC
                    LIMIT {top_k * 2}
                    """,
                    {"entity": entity},
                )
                while result.has_next():
                    row = result.get_next()
                    if not row:
                        continue
                    mid = str(row[0])
                    if mid in seen:
                        continue
                    seen.add(mid)
                    graph_items.append({
                        "id": mid,
                        "content": str(row[1]),
                        "importance": float(row[2] or 0.5),
                        "layer": str(row[3] or "episodic"),
                        "hops": int(row[4] or 1),
                        "_distance": 0.0,
                    })
            except Exception:
                continue

        all_items = vector_items + graph_items
        now = datetime.now()
        for item in all_items:
            mem_id = str(item.get("id", ""))
            ts = str(item.get("timestamp", now.isoformat()))
            age_days = max(0, (now - self._parse_ts(ts)).days)
            decay = self.forget_alpha ** (age_days / 10.0)
            dist = float(item.get("_distance", 0.5))
            imp = float(item.get("importance", 0.5))
            hops = int(item.get("hops", 1))
            acc = self._get_access(mem_id, ts, item)
            item["_score"] = (
                (1.0 - dist) * 0.32
                + imp * 0.28
                + max(0.1, decay) * 0.14
                + min(0.18, acc["access_count"] * 0.02)
                + (1.0 / (hops + 1)) * 0.18
                + float(item.get("_short_term_boost", 0))
            )

        all_items.sort(key=lambda x: x.get("_score", 0), reverse=True)
        top = all_items[:top_k]
        recalled_ids = [str(r.get("id", "")) for r in top if r.get("id")]

        provenance_map: Dict[str, List[Dict]] = {}
        if self.reconsolidate_enabled:
            for r in top:
                rid = str(r.get("id", ""))
                self.full_reconsolidate(rid, str(r.get("content", "")), query)
                provenance_map[rid] = self.get_provenance(rid)

        self._hebbian_strengthen_batch(recalled_ids)
        self._stats["recalled"] += 1

        parts = []
        for r in top:
            mem_id = str(r.get("id", ""))
            hops = int(r.get("hops", 1))
            layer = self._get_layer(mem_id, r)
            hops_display = "→" * max(1, hops)
            parts.append(
                f"[{hops_display} layer:{layer} | score:{float(r.get('_score', 0)):.2f}] "
                f"{r.get('role', '?')}: {r.get('content', '')}"
            )

        schema_ctx = self._get_all_schemas()
        factual = "\n\n".join(parts)
        if schema_ctx:
            context = f"【核心认知图式 (Schema)】\n{schema_ctx}\n\n【多跳关联记忆链】\n{factual}"
        else:
            context = factual

        return {
            "context": context,
            "provenance": provenance_map,
            "short_term_used": bool(self._short_term_hits(query)),
            "items": [{"id": str(r.get("id")), "score": r.get("_score")} for r in top],
            "multi_hop": True,
        }

    def _extract_query_entities(self, query: str) -> List[str]:
        raw = self._ollama_chat(
            f"从以下查询中提取1-3个最核心的概念实体（逗号分隔，不要解释）：\n查询: {query[:400]}"
        )
        if not raw:
            return [query[:20]] if query.strip() else []
        return [e.strip() for e in raw.split(",") if e.strip()]

    def recall_detail(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_hyde: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if top_k is None:
            top_k = self.recall_top_k
        if not query.strip():
            return {"context": "", "provenance": {}, "short_term_used": False, "items": [], "route": "empty"}

        route = self.query_router.classify(query)
        self._route_stats[route] = self._route_stats.get(route, 0) + 1

        if route == "short_term":
            return self._recall_short_term_route(query, top_k, route)
        if route == "reflect":
            return self._recall_reflect_route(query, top_k, route)
        if route == "goal":
            out = self._recall_layer_route(
                query, top_k, use_hyde, {"goal", "intent", "plan", "schema"}, route
            )
            lifecycle_ctx = self._format_goal_lifecycle_context()
            if lifecycle_ctx:
                out["context"] = f"{lifecycle_ctx}\n\n{out.get('context', '')}".strip()
            return out
        if route == "semantic":
            return self._recall_layer_route(
                query, top_k, use_hyde, {"semantic", "schema", "procedural"}, route
            )
        if route == "archive":
            return self._recall_archive_route(query, top_k, route)
        if route == "graph_reasoning" and self.enable_multi_hop:
            out = self.multi_hop_recall(query, top_k=top_k, use_hyde=use_hyde)
            out["route"] = route
            return out
        if self.enable_multi_hop and len(query.strip()) > 12:
            out = self.multi_hop_recall(query, top_k=top_k, use_hyde=use_hyde)
            out["route"] = "episodic_graph"
            return out
        out = self._legacy_recall_detail(query, top_k, use_hyde)
        out["route"] = route
        return out

    def _recall_short_term_route(self, query: str, top_k: int, route: str) -> Dict[str, Any]:
        hits = self._short_term_hits(query, limit=top_k)
        if not hits:
            out = self._legacy_recall_detail(query, top_k, True)
            out["route"] = route
            return out
        parts = [
            f"[WM att={float(h.get('_attention', 0)):.2f}] {h.get('role', '?')}: {h.get('content', '')}"
            for h in hits
        ]
        self._stats["recalled"] += 1
        return {
            "context": "\n\n".join(parts),
            "provenance": {},
            "short_term_used": True,
            "items": [{"id": str(h.get("id")), "score": h.get("_attention")} for h in hits],
            "route": route,
        }

    def _format_goal_lifecycle_context(self) -> str:
        active = [
            g for g in self._goal_lifecycle.values()
            if str(g.get("status", "active")).lower() in ("active", "in_progress")
        ]
        if not active:
            return ""
        active.sort(key=lambda x: float(x.get("priority", 0)), reverse=True)
        lines = ["【Goal Lifecycle — Active】"]
        for g in active[:8]:
            lines.append(
                f"- [{g.get('status', 'active')}|p={float(g.get('priority', 0)):.2f}] "
                f"{str(g.get('text', ''))[:200]}"
            )
        return "\n".join(lines)

    def _recall_reflect_route(self, query: str, top_k: int, route: str) -> Dict[str, Any]:
        parts: List[str] = []
        stability = float(self._self_model.get("stability_score", 1.0))
        parts.append(
            f"【Self-Model】identity={self._self_model.get('identity', '?')} "
            f"stability={stability:.2f}"
        )
        if self._beliefs:
            parts.append("【Beliefs】")
            ranked = sorted(
                self._beliefs.items(),
                key=lambda x: float(x[1].get("confidence", 0)),
                reverse=True,
            )
            for key, b in ranked[:6]:
                parts.append(
                    f"- {key} (conf={float(b.get('confidence', 0)):.2f}): "
                    f"{str(b.get('content', ''))[:160]}"
                )
        meta_rows = [
            r for r in self._rows_from_table(limit=800)
            if self._get_layer(str(r.get("id", "")), r) == "meta"
        ]
        meta_rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        if meta_rows:
            parts.append("【Meta-Reflection】")
            for r in meta_rows[:top_k]:
                parts.append(f"- {str(r.get('content', ''))[:220]}")
        if not meta_rows and self.reflection_enabled:
            summary = self.run_reflection()
            if summary and summary not in ("reflection_disabled", "no_data_for_reflection", "reflection_failed"):
                parts.append(f"【Fresh Reflection】\n{summary[:500]}")
        self._stats["recalled"] += 1
        return {
            "context": "\n".join(parts) if parts else "暂无反思记忆。",
            "provenance": {},
            "short_term_used": False,
            "items": [{"id": str(r.get("id")), "score": r.get("importance")} for r in meta_rows[:top_k]],
            "route": route,
        }

    def _recall_layer_route(
        self,
        query: str,
        top_k: int,
        use_hyde: Optional[bool],
        layers: Set[str],
        route: str,
    ) -> Dict[str, Any]:
        use_hyde = self.use_hyde_default if use_hyde is None else use_hyde
        search_text = query
        if use_hyde:
            search_text = f"{query}\n{self._hyde_generate(query)}"
        qvec = self._ollama_embed(search_text)
        rows = [
            r for r in self._rows_from_table(limit=2500)
            if self._get_layer(str(r.get("id", "")), r) in layers
        ]
        if not rows:
            return {"context": "无相关层记忆。", "provenance": {}, "short_term_used": False, "items": [], "route": route}
        for r in rows:
            vec = r.get("vector")
            dist = 1.0 - self._cosine_sim(qvec, vec) if vec else 0.5
            r["_score"] = (1.0 - dist) * 0.55 + float(r.get("importance", 0.5)) * 0.45
        rows.sort(key=lambda x: x.get("_score", 0), reverse=True)
        top = rows[:top_k]
        schema_ctx = self._get_all_schemas() if "schema" in layers else ""
        parts = [
            f"[layer:{self._get_layer(str(r.get('id')), r)} | score:{float(r.get('_score', 0)):.2f}] "
            f"{r.get('content', '')}"
            for r in top
        ]
        context = "\n\n".join(parts)
        if schema_ctx:
            context = f"【Schema】\n{schema_ctx}\n\n{context}"
        self._stats["recalled"] += 1
        return {
            "context": context,
            "provenance": {},
            "short_term_used": False,
            "items": [{"id": str(r.get("id")), "score": r.get("_score")} for r in top],
            "route": route,
        }

    def _recall_archive_route(self, query: str, top_k: int, route: str) -> Dict[str, Any]:
        now = datetime.now()
        q = query.lower()
        archived = []
        for r in self._rows_from_table(limit=3000):
            mem_id = str(r.get("id", ""))
            if not mem_id or self._get_layer(mem_id, r) in self.PROTECTED_LAYERS:
                continue
            ts = self._parse_ts(str(r.get("timestamp", now.isoformat())))
            if (now - ts).days < 30:
                continue
            if q not in str(r.get("content", "")).lower() and q[:8] not in str(r.get("content", "")).lower():
                continue
            archived.append(r)
        archived.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        top = archived[:top_k]
        parts = [
            f"[archive {str(r.get('timestamp', ''))[:10]}] {r.get('content', '')}"
            for r in top
        ]
        self._stats["recalled"] += 1
        return {
            "context": "\n\n".join(parts) if parts else "无匹配归档记忆。",
            "provenance": {},
            "short_term_used": False,
            "items": [{"id": str(r.get("id"))} for r in top],
            "route": route,
        }

    def _legacy_recall_detail(
        self,
        query: str,
        top_k: int,
        use_hyde: Optional[bool] = None,
    ) -> Dict[str, Any]:
        use_hyde = self.use_hyde_default if use_hyde is None else use_hyde
        st_hits = self._short_term_hits(query)
        search_text = query
        if use_hyde:
            hyde_doc = self._hyde_generate(query)
            search_text = f"{query}\n{hyde_doc}"

        query_vec = self._ollama_embed(search_text)
        try:
            raw = self.table.search(query_vec).limit(top_k * 6).to_list()
        except Exception:
            raw = []

        results: List[Dict] = []
        seen: Set[str] = set()
        for r in raw:
            d = self._row_to_dict(r)
            if d and d.get("id") not in seen:
                results.append(d)
                seen.add(str(d.get("id")))

        for hit in st_hits:
            hid = str(hit.get("id", ""))
            if hid and hid not in seen:
                hit["_short_term_boost"] = 0.25
                results.insert(0, hit)
                seen.add(hid)

        if not results:
            return {"context": "无相关长期记忆。", "provenance": {}, "short_term_used": bool(st_hits), "items": []}

        seed_ids = [str(r.get("id", "")) for r in results[:top_k] if r.get("id")]
        for nid in self._graph_neighbors(seed_ids):
            if nid in seen:
                continue
            for row in self._rows_from_table(limit=1500):
                if str(row.get("id")) == nid:
                    row["_graph_boost"] = 0.15
                    results.append(row)
                    seen.add(nid)
                    break

        now = datetime.now()
        for r in results:
            mem_id = str(r.get("id", ""))
            ts = str(r.get("timestamp", now.isoformat()))
            age_days = max(0, (now - self._parse_ts(ts)).days)
            decay = self.forget_alpha ** (age_days / 10.0)
            acc = self._get_access(mem_id, ts, r)
            dist = float(r.get("_distance", 0.5))
            imp = float(r.get("importance", 0.5))
            r["_score"] = (
                (1.0 - dist) * 0.36
                + imp * 0.30
                + max(0.1, decay) * 0.18
                + min(0.22, acc["access_count"] * 0.02)
                + float(r.get("_graph_boost", 0))
                + float(r.get("_short_term_boost", 0))
            )

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        top = results[:top_k]
        recalled_ids = [str(r.get("id", "")) for r in top if r.get("id")]

        provenance_map: Dict[str, List[Dict]] = {}
        if self.reconsolidate_enabled:
            for r in top:
                rid = str(r.get("id", ""))
                self.full_reconsolidate(rid, str(r.get("content", "")), query)
                provenance_map[rid] = self.get_provenance(rid)

        self._hebbian_strengthen_batch(recalled_ids)
        for r in top[:3]:
            self.update_hebbian_edges(str(r.get("id", "")), str(r.get("content", "")))

        self._stats["recalled"] += 1

        parts = []
        for r in top:
            mem_id = str(r.get("id", ""))
            ts = str(r.get("timestamp", ""))[:19]
            role = str(r.get("role", "?"))
            content = str(r.get("content", ""))
            layer = self._get_layer(mem_id, r)
            score = float(r.get("_score", 0))
            acc = self._get_access(mem_id, ts, r)
            parts.append(
                f"[{ts} | layer:{layer} | score:{score:.2f} | access:{acc['access_count']}] "
                f"{role}: {content}"
            )
            self._record_provenance(mem_id, f"query:{hash(query) % 1000000}", score)

        schema_ctx = self._get_all_schemas()
        context = "\n\n".join(parts)
        if schema_ctx:
            context = f"【核心认知图式 (Schema)】\n{schema_ctx}\n\n【相关事实】\n{context}"

        return {
            "context": context,
            "provenance": provenance_map,
            "short_term_used": bool(st_hits),
            "items": [{"id": str(r.get("id")), "score": r.get("_score")} for r in top],
            "route": "legacy",
        }

    def update_goal_memory(
        self,
        goal_text: str,
        importance: float = 0.88,
        status: str = "active",
    ) -> str:
        goal_text = goal_text.strip()
        if not goal_text:
            return "empty_goal"
        mid = self.capture(
            "system",
            f"[Goal:{status}] {goal_text}",
            layer="goal",
            metadata={"importance": importance, "status": status},
        )
        if mid and not str(mid).startswith(("filtered", "write_gate", "belief", "merged", "too")):
            self._register_goal_lifecycle(mid, goal_text, status=status, priority=importance)
        return mid

    def update_goal(self, goal_text: str, status: str = "active", priority: float = 0.8) -> str:
        return self.update_goal_memory(goal_text, importance=priority, status=status)

    def update_intent_memory(self, intent_text: str, importance: float = 0.82) -> str:
        return self.capture("system", f"[Intent] {intent_text.strip()}", layer="intent", metadata={"importance": importance})

    def update_plan_memory(self, plan_text: str, importance: float = 0.80) -> str:
        return self.capture("system", f"[Plan] {plan_text.strip()}", layer="plan", metadata={"importance": importance})

    def full_reconsolidate(self, mem_id: str, old_content: str, query: str = "") -> None:
        """Retrieval-induced reconsolidation + engram maturation"""
        layer = self._get_layer(mem_id)
        self._touch_access(mem_id, layer=layer)
        if self.deep_reconsolidate_prob > 0 and query and old_content:
            import random
            if random.random() < self.deep_reconsolidate_prob:
                updated = self._ollama_chat(
                    f"基于新查询「{query[:200]}」，轻微补充以下记忆上下文（保持原意，只追加一句）：\n{old_content[:600]}"
                )
                if updated and len(updated) > 10:
                    safe_id = mem_id.replace("'", "''")
                    try:
                        self.table.update(where=f"id = '{safe_id}'", values={"content": updated[:4000]})
                    except Exception:
                        pass

    _full_reconsolidate = full_reconsolidate
    _reconsolidate = full_reconsolidate

    def search_time_range(self, start_iso: str, end_iso: str, top_k: int = 50) -> str:
        filtered = [r for r in self._rows_from_table(limit=3000) if start_iso <= str(r.get("timestamp", "")) <= end_iso]
        filtered.sort(key=lambda x: x.get("timestamp", ""))
        parts = [
            f"[{str(r.get('timestamp', ''))[:19]}] {r.get('role', '?')}: {r.get('content', '')}"
            for r in filtered[:top_k]
        ]
        return "\n\n".join(parts) if parts else "该时间段内无记录"

    # ==================== 巩固 & 遗忘 ====================

    def consolidate(self) -> str:
        if not self.consolidate_enabled:
            return "consolidate_enabled=false，已跳过"

        print("执行多层睡眠巩固 (Episodic → Semantic → Schema)...")
        rows = self._rows_from_table(limit=600)
        important = [r for r in rows if float(r.get("importance", 0)) > self.importance_threshold]
        if len(important) < 5:
            metabolic_msg = self.metabolic_consolidate() if self.enable_metabolic else ""
            return metabolic_msg or "记忆量不足，无需巩固"

        prompt = (
            "执行多层记忆巩固，用中文结构化输出：\n"
            "## Episodic 要点\n## Semantic 知识（偏好/事实）\n"
            "## Procedural 模式（可复用习惯/技能）\n## Schema 图式（用户目标/信念/策略，每行一条）\n\n"
        )
        for r in important[:25]:
            prompt += f"[{str(r.get('timestamp', ''))[:10]}] {r.get('role')}: {str(r.get('content', ''))[:300]}\n"

        summary = self._ollama_chat(prompt)
        if not summary:
            return "巩固失败：LLM 未返回"

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = os.path.join(self.summaries_path, f"consolidation_{stamp}.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Sleep Consolidation v5.0 {stamp}\n\n{summary}\n")

        self.capture("system", f"[Semantic] {summary}", layer="semantic", metadata={"importance": 0.88})
        self._extract_and_store_schemas(summary)
        for r in important[:10]:
            self.update_hebbian_edges(str(r.get("id", "")), str(r.get("content", "")))

        pruned = self._prune_forgetting()
        metabolic_msg = self.metabolic_consolidate() if self.enable_metabolic else ""
        self._stats["consolidated"] += 1
        base = f"多层巩固完成（{len(important)} 条 → Semantic/Schema，遗忘 {pruned} 条）\n\n{summary[:900]}"
        return f"{base}\n{metabolic_msg}".strip()

    def _extract_and_store_schemas(self, consolidation_text: str) -> None:
        """从巩固摘要提炼 schema 层"""
        prompt = (
            "从以下巩固摘要中提取 3-5 条「用户认知图式」（目标/信念/策略/偏好模式），"
            "每行一条，不要编号：\n"
            f"{consolidation_text[:2000]}"
        )
        raw = self._ollama_chat(prompt)
        if not raw:
            return
        for line in raw.splitlines():
            text = line.strip().lstrip("-*·0123456789. ")
            if len(text) > 15:
                self.capture("system", f"[Schema] {text}", layer="schema", metadata={"importance": 0.92})

    def _reconcile_beliefs(self) -> int:
        """信念调和：合并低证据重复键"""
        merged = 0
        keys = list(self._beliefs.keys())
        for i, k1 in enumerate(keys):
            if k1 not in self._beliefs:
                continue
            c1 = str(self._beliefs[k1].get("content", ""))
            if len(c1) < 16:
                continue
            for k2 in keys[i + 1:]:
                if k2 not in self._beliefs or k1 == k2:
                    continue
                c2 = str(self._beliefs[k2].get("content", ""))
                if c1[:40] == c2[:40] or c1 in c2 or c2 in c1:
                    b1, b2 = self._beliefs[k1], self._beliefs[k2]
                    b1["confidence"] = round(min(1.0, (float(b1.get("confidence", 0)) + float(b2.get("confidence", 0))) / 2), 4)
                    b1["evidence"] = int(b1.get("evidence", 1)) + int(b2.get("evidence", 1))
                    self._beliefs.pop(k2, None)
                    merged += 1
        if merged:
            self._save_beliefs()
            self._enforce_identity_stability()
        return merged

    def metabolic_consolidate(self) -> str:
        """v5.0 代谢循环：压缩 + 图剪枝 + 信念调和 + 反思 + 遗忘"""
        if not self.enable_metabolic:
            return ""
        parts = []
        compressed = self.compress_similar_episodics()
        if compressed:
            parts.append(f"语义压缩 {compressed} 组")
        pruned_edges = self._prune_low_confidence_edges()
        if pruned_edges:
            parts.append(f"图剪枝 {pruned_edges} 条边")
        reconciled = self._reconcile_beliefs()
        if reconciled:
            parts.append(f"信念调和 {reconciled} 项")
        conflicts = self._detect_and_resolve_conflicts()
        if conflicts:
            parts.append(f"冲突反思 {conflicts} 条")
        if self.reflection_enabled:
            reflection = self.run_reflection()
            if reflection and reflection not in ("reflection_disabled", "no_data_for_reflection", "reflection_failed"):
                parts.append("Meta-Reflection 完成")
        pruned = self._neuro_forgetting()
        if pruned:
            parts.append(f"代谢遗忘 {pruned} 条")
        return "v5.0 代谢循环: " + "; ".join(parts) if parts else "v5.0 代谢循环完成"

    def compress_similar_episodics(self) -> int:
        """将高度冗余 episodic 压缩为 semantic 并删除冗余"""
        rows = [
            r for r in self._rows_from_table(limit=1200)
            if self._get_layer(str(r.get("id", "")), r) == "episodic" and r.get("vector")
        ]
        if len(rows) < 8:
            return 0
        merged = 0
        seen: Set[str] = set()
        for i, a in enumerate(rows[:120]):
            aid = str(a.get("id", ""))
            if not aid or aid in seen:
                continue
            cluster = [a]
            for b in rows[i + 1 : i + 20]:
                bid = str(b.get("id", ""))
                if not bid or bid in seen:
                    continue
                if self._cosine_sim(a["vector"], b["vector"]) >= self.compress_similarity:
                    cluster.append(b)
                    seen.add(bid)
            if len(cluster) < 3:
                continue
            texts = "\n".join(str(c.get("content", ""))[:200] for c in cluster[:6])
            summary = self._ollama_chat(
                f"将以下相似经历压缩为一条 semantic 知识（中文一句）：\n{texts[:1200]}"
            )
            if summary and len(summary) > 12:
                self.capture(
                    "system",
                    f"[Semantic-Compressed] {summary[:800]}",
                    layer="semantic",
                    metadata={"importance": 0.82},
                )
                for c in cluster[1:]:
                    self._delete_memory(str(c.get("id", "")))
                seen.add(aid)
                merged += 1
                if merged >= 5:
                    break
        self._stats["compressed"] += merged
        return merged

    def _prune_low_confidence_edges(self) -> int:
        now = datetime.now()
        threshold = self.graph_prune_confidence
        to_remove: List[str] = []
        for key, meta in list(self._edge_meta.items()):
            conf = float(meta.get("confidence", 0.6))
            verified = meta.get("last_verified")
            stale = False
            if verified:
                try:
                    stale = (now - self._parse_ts(str(verified))).days > 30
                except Exception:
                    stale = False
            if conf < threshold or (stale and conf < 0.55):
                to_remove.append(key)
        deleted = 0
        for key in to_remove:
            meta = self._edge_meta.get(key, {})
            rel = str(meta.get("rel", "RELATED"))
            src = str(meta.get("src", ""))
            tgt = str(meta.get("tgt", ""))
            if not src or not tgt:
                self._edge_meta.pop(key, None)
                continue
            try:
                self.graph_conn.execute(
                    f"""
                    MATCH (a:ChatNode {{id: $a}})-[r:{rel}]->(b:ChatNode {{id: $b}})
                    DELETE r
                    """,
                    {"a": src, "b": tgt},
                )
                deleted += 1
            except Exception:
                pass
            self._edge_meta.pop(key, None)
        if deleted:
            self._save_edge_meta()
            self._stats["pruned_edges"] += deleted
        return deleted

    def _detect_and_resolve_conflicts(self) -> int:
        count = 0
        try:
            result = self.graph_conn.execute(
                """
                MATCH (a:ChatNode)-[r:CONFLICTS]->(b:ChatNode)
                RETURN a.content, b.content
                LIMIT 5
                """
            )
            while result.has_next():
                row = result.get_next()
                if not row:
                    continue
                resp = self._ollama_chat(
                    f"分析以下两条记忆的冲突并给出融合结论（一句话）：\nA: {row[0]}\nB: {row[1]}"
                )
                if resp:
                    self.capture("system", f"[SELF_REFLECTION] {resp[:500]}", layer="semantic")
                    count += 1
        except Exception:
            pass
        return count

    def _neuro_forgetting(self) -> int:
        """Ebbinghaus + 物理删除（schema 层受保护）"""
        now = datetime.now()
        to_drop: List[str] = []
        for r in self._rows_from_table(limit=3000):
            mem_id = str(r.get("id", ""))
            if not mem_id or mem_id.startswith("__"):
                continue
            if self._get_layer(mem_id, r) in self.PROTECTED_LAYERS:
                continue
            acc = self._get_access(mem_id, str(r.get("timestamp", "")), r)
            idle_days = (now - self._parse_ts(acc["last_access"])).days
            imp = float(r.get("importance", 0.5))
            decay = imp * (self.forget_alpha ** (idle_days / 10.0)) * (1 + acc["access_count"] * 0.02)
            if decay < 0.15 and idle_days > 40 and acc["access_count"] < 4:
                to_drop.append(mem_id)
        dropped = sum(1 for mid in to_drop[:30] if self._delete_memory(mid))
        self._stats["forgotten"] += dropped
        return dropped

    def link_answer_provenance(self, query: str, answer: str, cited_ids: List[str]) -> None:
        """v4 回答溯源：answer → SUPPORTED_BY → 记忆节点"""
        if not cited_ids:
            return
        ans_id = f"answer_{datetime.now().isoformat()}_{abs(hash(answer)) % 100000:05d}"
        try:
            self.graph_conn.execute(
                """
                CREATE (n:ChatNode {
                    id: $id, timestamp: $ts, role: 'assistant',
                    content: $content, importance: 0.7, session_id: 'provenance', layer: 'answer'
                })
                """,
                {
                    "id": ans_id,
                    "ts": datetime.now().isoformat(),
                    "content": answer[:600],
                },
            )
        except Exception:
            return
        for cid in cited_ids[:12]:
            try:
                self.graph_conn.execute(
                    """
                    MATCH (a:ChatNode {id: $aid}), (c:ChatNode {id: $cid})
                    CREATE (a)-[:SUPPORTED_BY {weight: 0.85}]->(c)
                    """,
                    {"aid": ans_id, "cid": cid},
                )
            except Exception:
                continue

    def forget(
        self,
        max_age_days: int = 90,
        min_importance: float = 0.3,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        now = datetime.now()
        candidates = []
        for r in self._rows_from_table(limit=3000):
            mem_id = str(r.get("id", ""))
            if not mem_id or mem_id.startswith("__"):
                continue
            content = str(r.get("content", ""))
            if self._get_layer(mem_id, r) in self.PROTECTED_LAYERS:
                continue
            if "[Semantic]" in content or "[Sleep Consolidation" in content or "[Schema]" in content:
                continue
            ts = self._parse_ts(str(r.get("timestamp", now.isoformat())))
            age_days = (now - ts).days
            imp = float(r.get("importance", 0.5))
            acc = self._get_access(mem_id, str(r.get("timestamp", "")), r)
            idle_days = (now - self._parse_ts(acc["last_access"])).days
            if age_days >= max_age_days and imp < min_importance and idle_days >= max(30, max_age_days // 2):
                candidates.append((mem_id, imp))

        candidates.sort(key=lambda x: x[1])
        to_drop = [c[0] for c in candidates[:50]]
        if dry_run:
            return {"dry_run": True, "would_forget": len(to_drop), "ids": to_drop[:10]}

        dropped = sum(1 for mid in to_drop if self._delete_memory(mid))
        self._stats["forgotten"] += dropped
        return {"forgotten": dropped, "candidates": len(to_drop)}

    def _prune_forgetting(self) -> int:
        return int(self.forget(max_age_days=90, min_importance=0.28, dry_run=False).get("forgotten", 0))

    def _delete_memory(self, mem_id: str) -> bool:
        safe_id = mem_id.replace("'", "''")
        try:
            self.table.delete(f"id = '{safe_id}'")
        except Exception as ex:
            logger.warning("lance delete %s: %s", mem_id, ex)
            return False
        try:
            self.graph_conn.execute("MATCH (n:ChatNode {id: $id}) DETACH DELETE n", {"id": mem_id})
        except Exception:
            pass
        with self._meta_lock:
            self._access_meta.pop(mem_id, None)
            self._provenance.pop(mem_id, None)
            self._short_term.pop(mem_id, None)
        self._save_access_meta()
        self._save_provenance()
        return True

    # ==================== 统计 ====================

    def get_layer_stats(self) -> Dict[str, int]:
        stats: Dict[str, int] = {
            "episodic": 0, "semantic": 0, "procedural": 0,
            "schema": 0, "goal": 0, "intent": 0, "plan": 0, "meta": 0,
        }
        for r in self._rows_from_table(limit=5000):
            layer = self._get_layer(str(r.get("id", "")), r)
            stats[layer] = stats.get(layer, 0) + 1
        return stats

    def get_stats(self) -> Dict[str, Any]:
        rows = self._rows_from_table(limit=10000)
        imp_vals = [float(r.get("importance", 0)) for r in rows]
        return {
            "version": self.VERSION,
            "total_memories": len(rows),
            "avg_importance": round(sum(imp_vals) / len(imp_vals), 3) if imp_vals else 0,
            "high_importance": sum(1 for v in imp_vals if v > 0.7),
            "layer_stats": self.get_layer_stats(),
            "captured": self._stats["captured"],
            "recalled": self._stats["recalled"],
            "consolidated": self._stats["consolidated"],
            "forgotten": self._stats["forgotten"],
            "compressed": self._stats["compressed"],
            "pruned_edges": self._stats["pruned_edges"],
            "write_gate_rejected": self._stats["write_gate_rejected"],
            "belief_conflicts": self._stats.get("belief_conflicts", 0),
            "reflections": self._stats.get("reflections", 0),
            "hyde_calls": self._stats["hyde_calls"],
            "recall_routes": dict(self._route_stats),
            "belief_count": len(self._beliefs),
            "goal_lifecycle_count": len(self._goal_lifecycle),
            "self_stability": float(self._self_model.get("stability_score", 1.0)),
            "attention_half_life": self.attention_half_life,
            "reflection_enabled": self.reflection_enabled,
            "working_memory_attention_avg": round(
                sum(r.get("_attention", 0) for r in self._short_term.values()) / max(len(self._short_term), 1),
                3,
            ),
            "enable_multi_hop": self.enable_multi_hop,
            "enable_metabolic": self.enable_metabolic,
            "embedding_model": self.embedding_model,
            "llm_model": self.llm_model,
            "embedding_dim": self._embed_dim,
            "db_size_mb": self._get_db_size(),
            "short_term_cache": len(self._short_term),
            "scheduler_active": self._scheduler is not None,
            "status": (
                "empty" if len(rows) == 0
                else ("stable" if float(self._self_model.get("stability_score", 1.0)) >= 0.68 else "reflective")
            ),
        }

    def _get_db_size(self) -> float:
        total = 0
        for root, _, files in os.walk(self.base_dir):
            for fn in files:
                try:
                    total += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
        return round(total / (1024 * 1024), 1)

    def backfill_chat_history(self, chat_db_path: str) -> int:
        if not os.path.exists(chat_db_path):
            return 0
        count = 0
        try:
            conn = sqlite3.connect(chat_db_path)
            cur = conn.execute("SELECT role, content, timestamp, channel FROM messages ORDER BY id")
            for role, content, ts, channel in cur:
                if content and len(content.strip()) >= self.min_capture_len:
                    memory_id = f"backfill_{ts}_{abs(hash(content)) % 1000000:06d}"
                    vector = self._ollama_embed(content)
                    record: Dict[str, Any] = {
                        "id": memory_id,
                        "timestamp": (ts or datetime.now().isoformat())[:26],
                        "role": role,
                        "content": content,
                        "importance": 0.5,
                        "vector": vector,
                        "session_id": channel or "unknown",
                    }
                    if "layer" in self._schema_cols:
                        record["layer"] = "episodic"
                    if "last_access" in self._schema_cols:
                        record["last_access"] = record["timestamp"]
                    if "access_count" in self._schema_cols:
                        record["access_count"] = 1
                    self.table.add([record])
                    self._touch_access(memory_id, layer="episodic")
                    self._graph_insert_node(
                        memory_id, record["timestamp"], role, content, 0.5,
                        record["session_id"], "episodic",
                    )
                    count += 1
            conn.close()
        except Exception as ex:
            print(f"backfill failed: {ex}")
        return count

    def export_markdown(self, out_path: Optional[str] = None) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = out_path or os.path.join(self.export_path, f"brain_memory_{stamp}.md")
        rows = self._rows_from_table(limit=2000)
        rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Brain-Memory Export v4.0\n\n导出: {datetime.now().isoformat()}\n总数: {len(rows)}\n\n")
            for r in rows:
                mem_id = str(r.get("id", ""))
                layer = self._get_layer(mem_id, r)
                f.write(
                    f"## [{str(r.get('timestamp', ''))[:19]}] {r.get('role')} "
                    f"(layer={layer}, imp={float(r.get('importance', 0)):.2f})\n\n"
                    f"{r.get('content', '')}\n\n---\n\n"
                )
        return path


if __name__ == "__main__":
    brain = BrainMemoryBackend()
    print(brain.recall_detail("OpenClaw 记忆系统"))
    print(brain.get_stats())
