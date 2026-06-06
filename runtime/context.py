from typing import Dict, List

from runtime.attention import DynamicAttentionField


class ContextAssemblyEngine:
    """分层上下文组装引擎 — 防止 narrative drift 和 identity inconsistency"""

    def __init__(self, attention_field: DynamicAttentionField):
        self.attention = attention_field

    def assemble(self, query: str, recall_results: List[Dict]) -> str:
        for r in recall_results:
            layer = r.get("_layer", "episodic")
            if layer == "identity":
                r["identity_weight"] = 1.0
            elif layer == "goal":
                r["goal_weight"] = 0.9
            self.attention.activate(r, query)

        wm = self.attention.working_memory_snapshot()
        parts = []

        identity_mem = [m for m in wm if m.get("_layer") == "identity"]
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

        parts.append("【Relevant Episodic & Semantic Recall】")
        for r in recall_results[:6]:
            layer = r.get("_layer", "episodic")
            parts.append(f"[{layer}] {r.get('content', '')[:220]}")

        return "\n\n".join(parts)
