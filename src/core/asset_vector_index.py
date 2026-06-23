"""Semantic vector index for cognitive assets (text + direct image CLIP)."""

from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


EmbedFn = Callable[[str], List[float]]
ReadBlobFn = Callable[[str, dict], Optional[bytes]]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def hash_embedding(text: str, dim: int = 128) -> List[float]:
    """Deterministic fallback when no embedding backend is available."""
    vec = [0.0] * dim
    tokens = re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", str(text or "").lower())
    if not tokens:
        return vec
    for token in tokens:
        bucket = hash(token) % dim
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


class AssetVectorIndex:
    """Maps asset_id -> embedding vector for semantic retrieval."""

    CLIP_BACKENDS = {"clip_onnx_image", "visual_grid", "visual_bytes"}

    def __init__(
        self,
        index_path: str | Path,
        *,
        embed_fn: Optional[EmbedFn] = None,
        clip_embedder=None,
        read_blob_fn: Optional[ReadBlobFn] = None,
        enabled: bool = True,
    ):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.embed_fn = embed_fn
        self.clip_embedder = clip_embedder
        self.read_blob_fn = read_blob_fn
        self.enabled = enabled
        self._lock = threading.Lock()
        self._rows: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.index_path.exists():
            return {}
        try:
            with open(self.index_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _persist(self):
        with open(self.index_path, "w", encoding="utf-8") as handle:
            json.dump(self._rows, handle, ensure_ascii=False, indent=2)

    def _embed_text(self, text: str) -> Tuple[List[float], str]:
        text = str(text or "").strip()
        if not text:
            return [], "empty"
        if self.clip_embedder and getattr(self.clip_embedder, "unified_space", False):
            try:
                vector, backend = self.clip_embedder.embed_text(text)
                if vector:
                    return vector, backend
            except Exception:
                pass
        if self.embed_fn:
            try:
                vector = list(self.embed_fn(text) or [])
                if vector:
                    return vector, "embed_fn"
            except Exception:
                pass
        return hash_embedding(text), "hash"

    def _embed_image(self, image_bytes: bytes) -> Tuple[List[float], str]:
        raw = bytes(image_bytes or b"")
        if not raw:
            return [], "empty"
        if self.clip_embedder:
            try:
                vector, backend = self.clip_embedder.embed_image(raw)
                if vector:
                    return vector, backend
            except Exception:
                pass
        return [], "clip_unavailable"

    @staticmethod
    def asset_text(meta: dict) -> str:
        kind = meta.get("type")
        filename = str(meta.get("filename") or "")
        if kind == "code":
            return f"{filename} {meta.get('summary') or ''}".strip()
        if kind == "image":
            return filename
        return filename

    def _resolve_image_bytes(self, asset_id: str, meta: dict, image_bytes: Optional[bytes]) -> Optional[bytes]:
        if image_bytes:
            return image_bytes
        if self.read_blob_fn:
            try:
                return self.read_blob_fn(asset_id, meta)
            except Exception:
                return None
        return None

    def index_asset(self, asset_id: str, meta: dict, *, image_bytes: Optional[bytes] = None) -> dict:
        if not self.enabled:
            return {"ok": False, "error": "index_disabled"}
        asset_id = str(asset_id or "").strip()
        if not asset_id:
            return {"ok": False, "error": "missing_asset_id"}

        kind = meta.get("type")
        if kind == "image":
            blob = self._resolve_image_bytes(asset_id, meta, image_bytes)
            if not blob:
                return {"ok": False, "error": "missing_image_bytes"}
            vector, backend = self._embed_image(blob)
            embed_mode = "clip_image"
            text = str(meta.get("filename") or "")
        else:
            text = self.asset_text(meta)
            vector, backend = self._embed_text(text)
            embed_mode = "text"

        if not vector:
            return {"ok": False, "error": "embedding_empty"}

        row = {
            "asset_id": asset_id,
            "type": meta.get("type"),
            "filename": meta.get("filename"),
            "text": text[:320],
            "vector": vector,
            "dim": len(vector),
            "backend": backend,
            "embed_mode": embed_mode,
            "updated_at": time.time(),
        }
        with self._lock:
            self._rows[asset_id] = row
            self._persist()
        return {"ok": True, "asset_id": asset_id, "dim": len(vector), "backend": backend, "embed_mode": embed_mode}

    def rebuild_all(self, metas: List[dict], *, read_blob_fn: Optional[ReadBlobFn] = None) -> dict:
        reader = read_blob_fn or self.read_blob_fn
        indexed = 0
        skipped = 0
        for meta in metas:
            asset_id = str(meta.get("id") or "")
            if not asset_id:
                continue
            image_bytes = None
            if meta.get("type") == "image" and reader:
                try:
                    image_bytes = reader(asset_id, meta)
                except Exception:
                    image_bytes = None
            result = self.index_asset(asset_id, meta, image_bytes=image_bytes)
            if result.get("ok"):
                indexed += 1
            else:
                skipped += 1
        return {"ok": True, "indexed": indexed, "skipped": skipped, "total": len(metas)}

    def search(
        self,
        query: str = "",
        *,
        image_bytes: Optional[bytes] = None,
        kind: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        query_mode = "text"
        if image_bytes:
            query_vec, q_backend = self._embed_image(image_bytes)
            query_mode = "image"
        else:
            query = str(query or "").strip()
            if not query:
                return []
            query_vec, q_backend = self._embed_text(query)

        if not query_vec:
            return []

        unified = bool(self.clip_embedder and getattr(self.clip_embedder, "unified_space", False))
        scored: List[tuple[float, dict]] = []
        with self._lock:
            rows = list(self._rows.values())

        for row in rows:
            if kind and row.get("type") != kind:
                continue
            row_mode = row.get("embed_mode") or "text"
            if query_mode == "image":
                if row_mode != "clip_image":
                    continue
            elif row_mode == "clip_image" and not unified:
                continue

            vector = row.get("vector") or []
            score = cosine_similarity(query_vec, vector)
            if score <= 0:
                continue
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        hits = []
        for score, row in scored[: max(1, limit)]:
            hits.append({
                "asset_id": row.get("asset_id"),
                "type": row.get("type"),
                "filename": row.get("filename"),
                "score": round(score, 4),
                "text": row.get("text"),
                "backend": row.get("backend"),
                "embed_mode": row.get("embed_mode"),
            })
        return hits

    def status(self) -> dict:
        with self._lock:
            count = len(self._rows)
            sample = next(iter(self._rows.values()), {})
            clip_images = sum(1 for row in self._rows.values() if row.get("embed_mode") == "clip_image")
        clip_status = self.clip_embedder.status() if self.clip_embedder and hasattr(self.clip_embedder, "status") else {}
        return {
            "enabled": self.enabled,
            "count": count,
            "clip_image_count": clip_images,
            "dim": sample.get("dim"),
            "backend": sample.get("backend"),
            "embed_mode": sample.get("embed_mode"),
            "clip": clip_status,
        }
