# -*- coding: utf-8 -*-
"""审计后记忆治理 — 噪声清理 + Semantic 注入 + consolidate"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if not os.environ.get("OLLAMA_MODELS") and os.path.isdir(r"D:\ollama_models"):
    os.environ["OLLAMA_MODELS"] = r"D:\ollama_models"

from config_loader import load_plugin_config
from memory_backend import BrainMemoryBackend

SEMANTIC_BLOBS = [
    (
        "semantic",
        """[审计结论 v4.0 — 2026-06-05]
总体评分 7.6/10。核心插件与 v4.0 特性代码完成度高，145 条 episodic 记忆兼容迁移成功。
最大缺口：OpenClaw Host E2E 未验证、记忆语料信噪比低（toolResult JSON 噪声）、Semantic 层空白。
生产必须：Ollama 常驻 + OLLAMA_MODELS=D:\\ollama_models + 定期 brain_consolidate。
审计流程：brain_recall → brain_hyde_recall → brain_provenance → brain_layer_stats → brain_export。""",
        0.92,
    ),
    (
        "semantic",
        """[v4.0 架构决策]
存储：插件目录 memory/lancedb + kuzu_db（非 ~/.openclaw），表名 brain_chat_memory。
检索：HyDE + 图邻居 + Ebbinghaus 衰减 + access 加权 + Provenance。
钩子：on_message(auto_capture) / before_llm_call(auto_recall+HyDE)。
Schema：last_access/access_count/layer 幂等迁移 + access_meta.json sidecar。
发布：scripts/pack_release.py --skip-memory 为干净包；完整包含 memory/。""",
        0.90,
    ),
    (
        "procedural",
        """[ClawHub 发布 Checklist]
1. ollama serve + nomic-embed-text + llama3.2 已拉取
2. python verify.py 通过
3. brain_consolidate 已生成 Semantic 摘要
4. 噪声记忆已清理，Semantic/Procedural 已注入
5. python scripts/pack_release.py --skip-memory
6. OpenClaw plugins.slots.memory = brain-memory
7. E2E：before_llm_call 注入 memory_context
8. 附 README + 演示脚本 scripts/demo_text.py""",
        0.88,
    ),
]


def _is_noise(row: dict) -> bool:
    role = str(row.get("role", "")).lower()
    content = str(row.get("content", "")).strip()
    if role == "toolresult":
        return True
    if content.startswith('{"type":"toolCall"') or content.startswith('{"type": "toolCall"'):
        return True
    if role == "toolresult" and content.startswith("{"):
        return True
    if len(content) > 200 and content.startswith("{") and '"sessions"' in content[:500]:
        return True
    if '"toolCall"' in content[:80] and len(content) < 800:
        return True
    return False


def main() -> None:
    config = load_plugin_config()
    config["scheduler_enabled"] = False
    b = BrainMemoryBackend(config)

    rows = b._rows_from_table(limit=5000)
    noise = [r for r in rows if _is_noise(r)]
    keep_backfill = [
        r for r in rows
        if not _is_noise(r) and "backfill_chat.js" in str(r.get("content", ""))
    ]

    print("=== NOISE PREVIEW ===")
    print(f"total={len(rows)} noise={len(noise)} keep_backfill_js={len(keep_backfill)}")
    for r in noise[:5]:
        print(f"  - {r.get('id')} role={r.get('role')} preview={str(r.get('content',''))[:60]}")

    dropped = 0
    for r in noise:
        if b._delete_memory(str(r.get("id", ""))):
            dropped += 1
    print(f"=== DROPPED {dropped} noise entries ===")

    if keep_backfill:
        text = "\n".join(str(x.get("content", ""))[:400] for x in keep_backfill[:2])
        b.capture(
            "system",
            f"[Semantic] OpenClaw backfill 管道要点（来自历史会话）:\n{text[:800]}",
            layer="semantic",
            metadata={"importance": 0.75},
        )

    for layer, text, imp in SEMANTIC_BLOBS:
        mid = b.capture("system", text, layer=layer, metadata={"importance": imp})
        print(f"stored {layer}: {mid}")

    print("\n=== LAYER STATS ===")
    print(json.dumps(b.get_layer_stats(), ensure_ascii=False, indent=2))

    print("\n=== CONSOLIDATE ===")
    print(b.consolidate())

    print("\n=== FINAL STATS ===")
    print(json.dumps(b.get_stats(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
