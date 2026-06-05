# -*- coding: utf-8 -*-
"""
Brain-Memory Plugin v4.0 — 类脑长期记忆系统

HyDE | 多层记忆 | Prefrontal 短期缓存 | 实体 Hebbian | Reconsolidation | Provenance | APScheduler
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union

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
    """类脑记忆后端 v4.0"""

    DEFAULT_EMBED_DIM = 768
    VERSION = "4.0.0"

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

        self._embed_dim = int(self.config.get("embedding_dim", self.DEFAULT_EMBED_DIM))
        self._access_meta: Dict[str, Dict[str, Any]] = {}
        self._provenance: Dict[str, List[Dict]] = {}
        self._session_last_id: Dict[str, str] = {}
        self._short_term: OrderedDict[str, Dict] = OrderedDict()
        self._short_term_capacity = int(self.config.get("short_term_capacity", 32))
        self._schema_cols: Set[str] = set()
        self._meta_lock = threading.Lock()
        self._scheduler = None
        self._stats = {"captured": 0, "recalled": 0, "consolidated": 0, "forgotten": 0, "hyde_calls": 0}

        self._init_llm_clients()
        self._init_vector_store()
        self._migrate_schema()
        self._init_graph_store()
        self._load_access_meta()
        self._load_provenance()
        os.makedirs(self.summaries_path, exist_ok=True)
        os.makedirs(self.export_path, exist_ok=True)
        self._start_scheduler()

        logger.info("Brain-Memory v4.0 loaded (ollama=%s)", self.ollama_host)
        if not os.environ.get("BRAIN_MEMORY_QUIET"):
            print(f"Brain-Memory v4.0 loaded (ollama: {self.ollama_host})")

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

    def _add_short_term(self, mem_id: str, record: Dict) -> None:
        if mem_id in self._short_term:
            self._short_term.move_to_end(mem_id)
        else:
            self._short_term[mem_id] = record
            if len(self._short_term) > self._short_term_capacity:
                self._short_term.popitem(last=False)

    def _short_term_hits(self, query: str, limit: int = 5) -> List[Dict]:
        q = query.lower()
        hits = []
        for rec in reversed(self._short_term.values()):
            if q in str(rec.get("content", "")).lower():
                hits.append(rec)
            if len(hits) >= limit:
                break
        return hits

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

        ts = datetime.now().isoformat()
        memory_id = f"{ts}_{abs(hash(content)) % 1000000:06d}"
        importance = self._get_importance(content)
        if metadata and "importance" in metadata:
            importance = float(metadata["importance"])
        if metadata and "layer" in metadata:
            layer = str(metadata["layer"])

        vector = self._ollama_embed(content)
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
        self._add_short_term(memory_id, record)
        self._graph_insert_node(memory_id, ts, role, content, importance, session_id, layer)
        self._graph_link_sequential(memory_id, session_id, importance)
        self.update_hebbian_edges(memory_id, content)
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

    def recall_detail(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_hyde: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if top_k is None:
            top_k = self.recall_top_k
        if not query.strip():
            return {"context": "", "provenance": {}, "short_term_used": False, "items": []}

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

        return {
            "context": "\n\n".join(parts),
            "provenance": provenance_map,
            "short_term_used": bool(st_hits),
            "items": [{"id": str(r.get("id")), "score": r.get("_score")} for r in top],
        }

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

        print("执行多层睡眠巩固 (Episodic → Semantic)...")
        rows = self._rows_from_table(limit=600)
        important = [r for r in rows if float(r.get("importance", 0)) > self.importance_threshold]
        if len(important) < 5:
            return "记忆量不足，无需巩固"

        prompt = (
            "执行多层记忆巩固，用中文结构化输出：\n"
            "## Episodic 要点\n## Semantic 知识（偏好/事实）\n## Procedural 模式（可复用习惯/技能）\n\n"
        )
        for r in important[:25]:
            prompt += f"[{str(r.get('timestamp', ''))[:10]}] {r.get('role')}: {str(r.get('content', ''))[:300]}\n"

        summary = self._ollama_chat(prompt)
        if not summary:
            return "巩固失败：LLM 未返回"

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = os.path.join(self.summaries_path, f"consolidation_{stamp}.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Sleep Consolidation v4.0 {stamp}\n\n{summary}\n")

        self.capture("system", f"[Semantic] {summary}", layer="semantic", metadata={"importance": 0.88})
        for r in important[:10]:
            self.update_hebbian_edges(str(r.get("id", "")), str(r.get("content", "")))

        pruned = self._prune_forgetting()
        self._stats["consolidated"] += 1
        return f"多层巩固完成（{len(important)} 条 → Semantic 摘要，遗忘 {pruned} 条）\n\n{summary[:900]}"

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
            if "[Semantic]" in content or "[Sleep Consolidation" in content:
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
        stats: Dict[str, int] = {"episodic": 0, "semantic": 0, "procedural": 0}
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
            "hyde_calls": self._stats["hyde_calls"],
            "embedding_model": self.embedding_model,
            "llm_model": self.llm_model,
            "embedding_dim": self._embed_dim,
            "db_size_mb": self._get_db_size(),
            "short_term_cache": len(self._short_term),
            "scheduler_active": self._scheduler is not None,
            "status": "healthy" if len(rows) > 0 else "empty",
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
