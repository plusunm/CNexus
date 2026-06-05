# -*- coding: utf-8 -*-
"""Line-delimited JSON RPC for BrainMemoryBackend (OpenClaw bridge)."""

from __future__ import annotations

import json
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if not os.environ.get("OLLAMA_MODELS") and os.path.isdir(r"D:\ollama_models"):
    os.environ["OLLAMA_MODELS"] = r"D:\ollama_models"

os.environ.setdefault("BRAIN_MEMORY_QUIET", "1")

from config_loader import load_plugin_config
from memory_backend import BrainMemoryBackend

_backend: BrainMemoryBackend | None = None


def _backend_instance() -> BrainMemoryBackend:
    global _backend
    if _backend is None:
        cfg_raw = os.environ.get("BRAIN_MEMORY_CONFIG", "{}")
        try:
            cfg = json.loads(cfg_raw) if cfg_raw.strip() else {}
        except json.JSONDecodeError:
            cfg = {}
        _backend = BrainMemoryBackend(load_plugin_config(cfg if isinstance(cfg, dict) else {}))
    return _backend


def _ok(req_id, result):
    return {"id": req_id, "ok": True, "result": result}


def _err(req_id, message):
    return {"id": req_id, "ok": False, "error": message}


def _dispatch(method: str, params: dict):
    b = _backend_instance()
    p = params or {}

    if method == "ping":
        return b.get_stats()
    if method == "recall":
        return {"text": b.recall(p.get("query", ""), top_k=p.get("top_k"), use_hyde=p.get("use_hyde"))}
    if method == "recall_detail":
        return b.recall_detail(p.get("query", ""), top_k=p.get("top_k"), use_hyde=p.get("use_hyde"))
    if method == "capture":
        mid = b.capture(
            p.get("role", "user"),
            p.get("content", ""),
            session_id=p.get("session_id", "default"),
            layer=p.get("layer", "episodic"),
        )
        return {"memory_id": mid}
    if method == "before_llm_call":
        return b.before_llm_call(p.get("query", ""))
    if method == "on_message":
        b.on_message(p)
        return {"ok": True}
    if method == "consolidate":
        return b.consolidate()
    if method == "stats":
        return b.get_stats()
    raise ValueError(f"unknown method: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req_id = None
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method", "")
            params = req.get("params") if isinstance(req.get("params"), dict) else {}
            result = _dispatch(method, params)
            sys.stdout.write(json.dumps(_ok(req_id, result), ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as ex:
            tb = traceback.format_exc()
            sys.stdout.write(json.dumps(_err(req_id, f"{ex}\n{tb}"), ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
