from typing import Dict, List, Optional, TYPE_CHECKING

from runtime.attention import DynamicAttentionField

if TYPE_CHECKING:
    from memory.manager import MemoryManager


class ContextAssemblyEngine:
    """分层上下文组装引擎 — 防止 narrative drift 和 identity inconsistency"""

    def __init__(
        self,
        attention_field: DynamicAttentionField,
        memory_manager: Optional["MemoryManager"] = None,
    ):
        self.attention = attention_field
        self.memory_manager = memory_manager

    def set_memory_manager(self, memory_manager: "MemoryManager") -> None:
        self.memory_manager = memory_manager

    def assemble(
        self,
        query: str,
        recall_results: List[Dict],
        memory_manager: Optional["MemoryManager"] = None,
    ) -> str:
        manager = memory_manager or self.memory_manager
        for r in recall_results:
            layer = r.get("_layer", "episodic")
            label = r.get("_label")
            if label == "persona" or layer == "identity":
                r["identity_weight"] = 1.0
            elif label == "intent" or layer == "goal":
                r["goal_weight"] = 0.9
            elif label == "attention_state":
                r["identity_weight"] = max(r.get("identity_weight", 0.0), 0.85)
            self.attention.activate(r, query)

        wm = self.attention.working_memory_snapshot()
        parts: List[str] = []

        if manager is not None:
            attn_block = manager.get_attention_state_block()
            if attn_block is not None and hasattr(attn_block, "to_context_string"):
                parts.append(attn_block.to_context_string())

            typed = self._assemble_typed_episodic(manager)
            if typed:
                parts.append(typed)

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

    def _assemble_typed_episodic(self, manager: "MemoryManager") -> str:
        from memory.block import EPISODIC_TYPE_TO_LABEL, EpisodicMemoryBlock

        sections: List[str] = []
        for episodic_type, title in (
            ("dialogue", "Recent Dialogue Trace"),
            ("event", "Recent Event Graph"),
            ("decision", "Recent Decision Trace"),
        ):
            label = EPISODIC_TYPE_TO_LABEL[episodic_type]
            block = manager.get_active_block(label, touch=False)
            if not isinstance(block, EpisodicMemoryBlock):
                continue
            recent = block.get_recent(2)
            if not recent:
                continue
            sections.append(f"【{title}】")
            for entry in recent:
                summary = entry.get("content_summary") or entry.get("payload") or entry.get("content")
                if isinstance(summary, dict):
                    summary = str(summary)[:180]
                sections.append(f"• {str(summary)[:180]}")
        return "\n".join(sections)
