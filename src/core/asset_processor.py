"""Cognitive asset ingestion — content-addressed blobs + AuditLog metadata pointers."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


SummarizeFn = Callable[[str, str], str]
VisionFn = Callable[[bytes, str], str]
AuditFn = Callable[[str, dict], Optional[str]]


class AssetProcessor:
    """Store blobs on disk; index lightweight metadata via AuditLog."""

    META_SUFFIX = ".meta.json"

    def __init__(
        self,
        asset_dir: str | Path,
        *,
        audit_log=None,
        audit_fn: Optional[AuditFn] = None,
        summarize_code_fn: Optional[SummarizeFn] = None,
        vision_fn: Optional[VisionFn] = None,
    ):
        self.asset_dir = Path(asset_dir)
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = audit_log
        self.audit_fn = audit_fn
        self.summarize_code_fn = summarize_code_fn
        self.vision_fn = vision_fn
        self._lock = threading.Lock()

    @staticmethod
    def content_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _meta_path(self, asset_id: str) -> Path:
        return self.asset_dir / f"{asset_id}{self.META_SUFFIX}"

    def _blob_path(self, asset_id: str, kind: str) -> Path:
        suffix = ".code" if kind == "code" else ".img"
        return self.asset_dir / f"{asset_id}{suffix}"

    def _write_meta(self, meta: dict):
        asset_id = str(meta.get("id") or "")
        if not asset_id:
            return
        path = self._meta_path(asset_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, ensure_ascii=False, indent=2)

    def _read_meta(self, asset_id: str) -> Optional[dict]:
        path = self._meta_path(asset_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _audit_index(self, meta: dict) -> Optional[str]:
        if not self.audit_fn:
            return None
        payload = {
            "action": "ASSET_UPLOAD",
            "type": meta.get("type"),
            "asset_id": meta.get("id"),
            "filename": meta.get("filename"),
            "size_bytes": meta.get("size_bytes"),
            "content_hash": meta.get("id"),
        }
        if meta.get("type") == "code":
            payload["summary"] = meta.get("summary")
        elif meta.get("type") == "image":
            payload["desc"] = meta.get("desc")
        return self.audit_fn("asset.upload", payload)

    def _summarize_code(self, content: str, filename: str) -> str:
        if self.summarize_code_fn:
            return self.summarize_code_fn(content, filename)
        return summarize_code_heuristic(content, filename)

    def _describe_image(self, binary: bytes, filename: str) -> str:
        if self.vision_fn:
            return self.vision_fn(binary, filename)
        return f"image asset ({filename}, {len(binary)} bytes)"

    def process_code(self, content: str, filename: str = "snippet.py") -> dict:
        text = str(content or "")
        filename = str(filename or "snippet.py").strip() or "snippet.py"
        if not text.strip():
            return {"ok": False, "error": "missing_content"}

        raw = text.encode("utf-8")
        asset_id = self.content_hash(raw)
        blob_path = self._blob_path(asset_id, "code")
        existing = self._read_meta(asset_id)
        if existing and blob_path.exists():
            return {
                "ok": True,
                "status": "indexed",
                "deduped": True,
                "id": asset_id,
                "type": "code",
                "filename": existing.get("filename", filename),
                "summary": existing.get("summary", ""),
                "size_bytes": existing.get("size_bytes", len(raw)),
            }

        summary = self._summarize_code(text, filename)
        with self._lock:
            with open(blob_path, "w", encoding="utf-8") as handle:
                handle.write(text)
            meta = {
                "id": asset_id,
                "type": "code",
                "filename": filename,
                "summary": summary,
                "size_bytes": len(raw),
                "created_at": time.time(),
            }
            self._write_meta(meta)

        audit_hash = self._audit_index(meta)
        result = {
            "ok": True,
            "status": "indexed",
            "id": asset_id,
            "type": "code",
            "filename": filename,
            "summary": summary,
            "size_bytes": len(raw),
            "audit_hash": audit_hash,
            "meta": meta,
        }
        return result

    def process_image(self, binary_data: bytes, filename: str = "image.jpg") -> dict:
        binary = bytes(binary_data or b"")
        filename = str(filename or "image.jpg").strip() or "image.jpg"
        if not binary:
            return {"ok": False, "error": "missing_image_data"}

        asset_id = self.content_hash(binary)
        blob_path = self._blob_path(asset_id, "image")
        existing = self._read_meta(asset_id)
        if existing and blob_path.exists():
            return {
                "ok": True,
                "status": "indexed",
                "deduped": True,
                "id": asset_id,
                "type": "image",
                "filename": existing.get("filename", filename),
                "desc": existing.get("desc", ""),
                "size_bytes": existing.get("size_bytes", len(binary)),
            }

        desc = self._describe_image(binary, filename)
        with self._lock:
            with open(blob_path, "wb") as handle:
                handle.write(binary)
            meta = {
                "id": asset_id,
                "type": "image",
                "filename": filename,
                "desc": desc,
                "size_bytes": len(binary),
                "created_at": time.time(),
            }
            self._write_meta(meta)

        audit_hash = self._audit_index(meta)
        result = {
            "ok": True,
            "status": "indexed",
            "id": asset_id,
            "type": "image",
            "filename": filename,
            "desc": desc,
            "size_bytes": len(binary),
            "audit_hash": audit_hash,
            "meta": meta,
        }
        return result

    def ingest_remote(self, meta: dict, raw: bytes, *, source_peer: str = "") -> dict:
        """Accept a pushed asset from a trusted peer (dedupe by content hash)."""
        asset_id = str(meta.get("id") or self.content_hash(bytes(raw)))
        kind = meta.get("type") or ("code" if str(meta.get("filename", "")).endswith((".py", ".js", ".ts")) else "image")
        blob_path = self._blob_path(asset_id, kind)
        existing = self._read_meta(asset_id)
        if existing and blob_path.exists():
            return {
                "ok": True,
                "status": "already_present",
                "deduped": True,
                "id": asset_id,
                "type": kind,
            }

        stored_meta = {
            "id": asset_id,
            "type": kind,
            "filename": meta.get("filename") or ("snippet.py" if kind == "code" else "image.jpg"),
            "summary": meta.get("summary"),
            "desc": meta.get("desc"),
            "size_bytes": meta.get("size_bytes", len(raw)),
            "created_at": time.time(),
            "source_peer": source_peer,
        }
        with self._lock:
            if kind == "code":
                blob_path.write_text(raw.decode("utf-8", errors="replace"), encoding="utf-8")
            else:
                blob_path.write_bytes(raw)
            self._write_meta(stored_meta)

        if self.audit_fn:
            self.audit_fn("asset.received", {
                "action": "ASSET_RECEIVED",
                "type": kind,
                "asset_id": asset_id,
                "filename": stored_meta.get("filename"),
                "source_peer": source_peer,
                "summary": stored_meta.get("summary"),
                "desc": stored_meta.get("desc"),
            })
        return {
            "ok": True,
            "status": "received",
            "id": asset_id,
            "type": kind,
            "meta": stored_meta,
        }

    def get_asset(self, asset_id: str, *, include_content: bool = False) -> Tuple[dict, int]:
        asset_id = str(asset_id or "").strip()
        if not re.fullmatch(r"[a-f0-9]{64}", asset_id):
            return {"ok": False, "error": "invalid_asset_id"}, 400

        meta = self._read_meta(asset_id)
        if not meta:
            return {"ok": False, "error": "asset_not_found"}, 404

        kind = meta.get("type") or "code"
        blob_path = self._blob_path(asset_id, kind)
        if not blob_path.exists():
            return {"ok": False, "error": "blob_missing"}, 404

        payload: Dict[str, Any] = {"ok": True, **meta}
        if include_content:
            if kind == "code":
                payload["content"] = blob_path.read_text(encoding="utf-8")
            else:
                payload["content_base64"] = base64.b64encode(blob_path.read_bytes()).decode("ascii")
        return payload, 200

    def read_raw(self, asset_id: str) -> Tuple[Optional[bytes], Optional[dict], int]:
        asset_id = str(asset_id or "").strip()
        meta = self._read_meta(asset_id)
        if not meta:
            return None, None, 404
        kind = meta.get("type") or "code"
        blob_path = self._blob_path(asset_id, kind)
        if not blob_path.exists():
            return None, meta, 404
        return blob_path.read_bytes(), meta, 200

    def list_assets(self, *, kind: Optional[str] = None, limit: int = 50) -> List[dict]:
        rows: List[dict] = []
        for path in sorted(self.asset_dir.glob(f"*{self.META_SUFFIX}"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    meta = json.load(handle)
            except Exception:
                continue
            if not isinstance(meta, dict):
                continue
            if kind and meta.get("type") != kind:
                continue
            rows.append(meta)
            if len(rows) >= limit:
                break
        return rows

    def search(self, query: str, *, kind: Optional[str] = None, limit: int = 20) -> List[dict]:
        query = str(query or "").strip().lower()
        if not query:
            return self.list_assets(kind=kind, limit=limit)

        hits: List[dict] = []
        seen: set[str] = set()

        for entry in self._audit_entries_reversed():
            data = entry.get("data") or {}
            event = str(data.get("event") or "")
            if event != "asset.upload":
                continue
            asset_type = data.get("type")
            if kind and asset_type != kind:
                continue
            asset_id = str(data.get("asset_id") or "")
            if not asset_id or asset_id in seen:
                continue
            haystack = " ".join(
                str(data.get(key) or "")
                for key in ("asset_id", "filename", "summary", "desc", "type", "action")
            ).lower()
            if query not in haystack:
                continue
            seen.add(asset_id)
            meta = self._read_meta(asset_id) or {}
            hits.append({
                "asset_id": asset_id,
                "type": asset_type,
                "filename": data.get("filename") or meta.get("filename"),
                "summary": data.get("summary") or meta.get("summary"),
                "desc": data.get("desc") or meta.get("desc"),
                "audit_hash": entry.get("hash"),
                "timestamp": entry.get("timestamp"),
                "size_bytes": data.get("size_bytes") or meta.get("size_bytes"),
            })
            if len(hits) >= limit:
                break

        if len(hits) < limit:
            for meta in self.list_assets(kind=kind, limit=limit * 2):
                asset_id = str(meta.get("id") or "")
                if asset_id in seen:
                    continue
                haystack = " ".join(
                    str(meta.get(key) or "")
                    for key in ("id", "filename", "summary", "desc", "type")
                ).lower()
                if query not in haystack:
                    continue
                seen.add(asset_id)
                hits.append({
                    "asset_id": asset_id,
                    "type": meta.get("type"),
                    "filename": meta.get("filename"),
                    "summary": meta.get("summary"),
                    "desc": meta.get("desc"),
                    "size_bytes": meta.get("size_bytes"),
                    "timestamp": meta.get("created_at"),
                })
                if len(hits) >= limit:
                    break
        return hits

    def _audit_entries_reversed(self) -> List[dict]:
        if not self.audit_log:
            return []
        reader = getattr(self.audit_log, "iter_entries", None)
        if not callable(reader):
            reader = getattr(self.audit_log, "_read_all_entries", None)
        if not callable(reader):
            return []
        return list(reversed(reader()))


def summarize_code_heuristic(content: str, filename: str) -> str:
    """Lightweight code summary without external AI."""
    text = str(content or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preview = " ".join(lines[:3])[:180]
    symbols: List[str] = []

    if filename.endswith(".py"):
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"def {node.name}()")
                elif isinstance(node, ast.ClassDef):
                    symbols.append(f"class {node.name}")
        except SyntaxError:
            pass

    parts = [f"{filename}: {len(lines)} lines"]
    if symbols:
        parts.append(", ".join(symbols[:6]))
    if preview:
        parts.append(preview)
    return " · ".join(parts)[:320]
