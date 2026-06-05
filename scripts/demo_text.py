# -*- coding: utf-8 -*-
"""1 分钟演示脚本 — recall + consolidate（本地录屏用）"""

from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if not os.environ.get("OLLAMA_MODELS") and os.path.isdir(r"D:\ollama_models"):
    os.environ["OLLAMA_MODELS"] = r"D:\ollama_models"
if not os.environ.get("LLM_MODEL"):
    os.environ["LLM_MODEL"] = "llama3.2:3b"

from config_loader import load_plugin_config
from memory_backend import BrainMemoryBackend

STEPS = [
    ("stats", lambda b: json.dumps(b.get_stats(), ensure_ascii=False, indent=2)),
    ("recall plain", lambda b: b.recall("v4.0 架构决策", use_hyde=False)[:500]),
    ("recall HyDE", lambda b: b.recall("Brain-Memory 发布 checklist", use_hyde=True)[:500]),
    ("layer stats", lambda b: json.dumps(b.get_layer_stats(), ensure_ascii=False, indent=2)),
    ("consolidate", lambda b: b.consolidate()[:600]),
]


def main() -> None:
    print("=== Brain-Memory v4.0 Demo (≈60s) ===\n")
    config = load_plugin_config()
    config["scheduler_enabled"] = False
    backend = BrainMemoryBackend(config)

    for i, (label, fn) in enumerate(STEPS, 1):
        print(f"\n--- [{i}/{len(STEPS)}] {label} ---")
        t0 = time.time()
        out = fn(backend)
        print(out)
        print(f"({time.time() - t0:.1f}s)")
        time.sleep(2)

    print("\n=== Demo complete — stop screen recording ===")


if __name__ == "__main__":
    main()
