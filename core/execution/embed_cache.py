"""Persistent embedding cache — cache hits bypass Inference Scheduler queue."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional


class EmbeddingCache:
    def __init__(self, db_path: str, *, model_version: str = "1"):
        self.db_path = str(db_path)
        self.model_version = model_version
        self._lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embed_cache (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.commit()

    def _key(self, text: str, model: str) -> str:
        digest = hashlib.sha256(
            f"{self.model_version}:{model}:{text}".encode("utf-8")
        ).hexdigest()
        return digest

    def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self._key(text, model)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT vector_json FROM embed_cache WHERE cache_key = ?",
                    (key,),
                ).fetchone()
        if not row:
            return None
        try:
            data = json.loads(row[0])
            if isinstance(data, list):
                return [float(x) for x in data]
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return None

    def set(self, text: str, model: str, vector: List[float]) -> None:
        key = self._key(text, model)
        payload = json.dumps(vector)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO embed_cache (cache_key, model, vector_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        vector_json = excluded.vector_json,
                        model = excluded.model
                    """,
                    (key, model, payload),
                )
                conn.commit()

    def stats(self) -> dict:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM embed_cache").fetchone()
        return {"entries": int(count[0]) if count else 0, "path": self.db_path}
