from typing import Dict, List

from runtime.attention import DynamicAttentionField


class ContextAssemblyEngine:
    """分层上下文组装引擎 — 防止 narrative drift 和 identity inconsistency"""

    def __init__(self, attention_field: DynamicAttentionField):
        self.attention = attention_field

    def assemble(self, query: str, recall_results: List[Dict]) -> str:
        for r in recall_results:
            layer = r.get("_layer", "episodic")
            label = r.get("_label")
            if label == "persona" or layer == "identity":
                r["identity_weight"] = 1.0
            elif label == "intent" or layer == "goal":
                r["goal_weight"] = 0.9
            self.attention.activate(r, query)

        wm = self.attention.working_memory_snapshot()
        parts = []

        block_results = [r for r in recall_results if r.get("_source") == "block"]
        if block_results:
            parts.append("【Structured Memory Blocks】")
            for r in block_results[:6]:
                label = r.get("_label", "block")
                parts.append(f"• [{label}] {r.get('content', '')[:220]}")

        identity_mem = [
            m for m in wm
            if m.get("_layer") == "identity" or m.get("_label") == "persona"
        ]
        if identity_mem:
            parts.append("【Identity Context】")
            for m in identity_mem[:2]:
                parts.append(f"• {m.get('content', '')[:200]}")

        for layer in ["goal", "belief"]:
            layer_mem = [m for m in wm if m.get("_layer") == layer]
            if layer_mem:
                parts.append(f"【{layer.capitalize()} Context】")
                for m in layer_mem[:3]:
                    parts.append(f"• {m.get('content', '')[:180]}")

        for layer in ["relationship", "narrative"]:
            layer_mem = [m for m in wm if m.get("_layer") == layer]
            if layer_mem:
                parts.append(f"【{layer.capitalize()} Context】")
                for m in layer_mem[:2]:
                    parts.append(f"• {m.get('content', '')[:180]}")

        episodic_results = [r for r in recall_results if r.get("_source") != "block"]
        if episodic_results:
            parts.append("【Relevant Episodic & Semantic Recall】")
            for r in episodic_results[:6]:
                layer = r.get("_layer", "episodic")
                parts.append(f"[{layer}] {r.get('content', '')[:220]}")

        return "\n\n".join(parts)
