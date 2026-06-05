# -*- coding: utf-8 -*-
"""Brain-Memory v4.0 验证 — HyDE 对比 + 实体抽取 + 钩子"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if not os.environ.get("OLLAMA_MODELS") and os.path.isdir(r"D:\ollama_models"):
    os.environ["OLLAMA_MODELS"] = r"D:\ollama_models"

from config_loader import load_plugin_config
from memory_backend import BrainMemoryBackend
from brain_skill.tools import get_tools


def test_hyde(backend: BrainMemoryBackend) -> None:
    print("\n=== HyDE 召回对比 ===")
    cases = [
        "OpenClaw 大脑记忆系统",
        "用户偏好和 Windows 开发环境",
        "上次讨论的 AI Agent 长期记忆",
    ]
    for q in cases:
        plain = backend.recall(q, use_hyde=False)
        hyde = backend.recall(q, use_hyde=True)
        print(f"Q: {q}")
        print(f"  plain len={len(plain)}  hyde len={len(hyde)}")
        print("-" * 60)


def main() -> None:
    print("Brain-Memory v4.0 verify\n")
    config = load_plugin_config()
    config["scheduler_enabled"] = False  # 验证时不启定时器
    backend = BrainMemoryBackend(config)
    tools = get_tools(backend)

    stats = backend.get_stats()
    print("stats:", json.dumps(stats, ensure_ascii=False, indent=2))

    backend.capture("user", "验证：Boss 在 Windows 上运行 OpenClaw Brain-Memory v4.0。", layer="episodic")
    test_hyde(backend)

    print("\n=== 实体抽取 ===")
    entities = backend.extract_entities_and_relations("我和李四正在开发 OpenClaw 的 Hebbian 记忆模块。")
    print(entities[:3])

    print("\n=== OpenClaw 钩子 ===")
    backend.on_message({"role": "user", "content": "verify 钩子测试消息", "session_id": "verify"})
    hook = backend.before_llm_call("刚才 verify 说了什么")
    print("before_llm_call keys:", list(hook.keys()))
    if hook.get("memory_context"):
        print(hook["memory_context"][:400])

    print("\n=== layer stats ===")
    print(tools["brain_layer_stats"]())

    print("\n=== forget dry_run ===")
    print(tools["brain_forget"](dry_run=True))

    print("\nOK v4.0 verify passed")


if __name__ == "__main__":
    main()
